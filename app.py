from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date, timedelta
import urllib.parse
import requests
from bs4 import BeautifulSoup
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ingredients.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# HTTPS環境の自動検出
def is_https_environment():
    if os.environ.get('HTTPS') == 'on':
        return True
    if os.environ.get('HTTP_X_FORWARDED_PROTO') == 'https':
        return True
    if os.environ.get('HTTP_X_FORWARDED_SSL') == 'on':
        return True
    return False

IS_HTTPS = is_https_environment()

# セッション設定
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-very-secure-secret-key-change-this-in-production')
app.config['SESSION_COOKIE_SECURE'] = IS_HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'False').lower() == 'true'

db = SQLAlchemy(app)


# モデル定義
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    ingredients = db.relationship('Ingredient', backref='user', lazy=True, cascade='all, delete-orphan')

PREDEFINED_CATEGORIES = [
    '野菜', '肉類', '魚介類', '乳製品', '穀類', '調味料', 'その他'
]

# モデル（シンプル化）
class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    category = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

with app.app_context():
    db.create_all()


# HTTPS強制リダイレクト
@app.before_request
def force_https():
    if FORCE_HTTPS and not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
        return redirect(request.url.replace('http://', 'https://'), code=301)


# キャッシュ制御
@app.after_request
def after_request(response):
    # ユーザー固有データを含むエンドポイント
    user_specific_endpoints = ['dashboard', 'refrigerator', 'search', 'add_ingredient']
    
    if request.endpoint in user_specific_endpoints:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Last-Modified'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        response.headers['Vary'] = 'Cookie, Authorization'
        response.headers['X-No-Cache'] = 'user-specific-data'
        
        if 'ETag' in response.headers:
            del response.headers['ETag']
    
    # セキュリティヘッダー
    if IS_HTTPS:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self'"
        )
    
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response


# PWA用のルート
@app.route('/manifest.json')
def manifest():
    response = send_from_directory('static', 'manifest.json')
    response.headers['Cache-Control'] = 'public, max-age=604800'
    return response

@app.route('/sw.js')
def service_worker():
    response = send_from_directory('static', 'sw.js')
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response


# ログイン必須デコレータ
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        username = session.get('username')
        print(f"[AUTH] Session check: user_id={user_id}, username={username}")
        
        if 'user_id' not in session:
            flash('セッションが切れています。再度ログインしてください。')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# 賞味期限チェック関数
def get_expiry_notifications(user_id):
    ingredients = Ingredient.query.filter_by(user_id=user_id).all()
    today = date.today()
    
    expired = []
    expiring_soon = []
    expiring_week = []
    
    for ing in ingredients:
        if ing.expiry_date:
            days_left = (ing.expiry_date - today).days
            if days_left < 0:
                expired.append(ing)
            elif days_left <= 3:
                expiring_soon.append(ing)
            elif days_left <= 7:
                expiring_week.append(ing)
    
    return {
        'expired': expired,
        'expiring_soon': expiring_soon,
        'expiring_week': expiring_week
    }


# ---------- レシピ取得関数 ----------
def fetch_nadia_recipes(query):
    encoded_query = urllib.parse.quote_plus(query)
    url = f'https://oceans-nadia.com/search?q={encoded_query}'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10, verify=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        recipes = []
        for item in soup.select('li.recipeList-fullwidth')[:15]:
            title_tag = item.select_one('p.recipe-title a.recipe-titlelink')
            img_tag = item.select_one('div.photo-frame a img')
            if title_tag and img_tag:
                title = title_tag.get_text(strip=True)
                link = title_tag.get('href')
                if not link.startswith('http'):
                    link = f"https://oceans-nadia.com{link}"
                img_url = img_tag.get('src')
                recipes.append({'title': title, 'url': link, 'img': img_url, 'source': 'Nadia'})
        return recipes
    except Exception as e:
        print(f"[ERROR] Nadia fetch error: {e}")
        return []

def fetch_kurashiru_recipes(query):
    encoded_query = urllib.parse.quote_plus(query)
    url = f'https://www.kurashiru.com/search?query={encoded_query}'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10, verify=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        recipes = []
        for item in soup.select('li.DlyMasonry-content')[:15]:
            title_tag = item.select_one('p.dly-video-item-title-root')
            link_tag = item.select_one('a.DlyLink[href]')
            noscript_tag = item.select_one('noscript')
            if title_tag and link_tag:
                title = title_tag.get_text(strip=True)
                link = link_tag.get('href')
                if not link.startswith('http'):
                    link = f"https://www.kurashiru.com{link}"
                img_url = ''
                if noscript_tag:
                    img_soup = BeautifulSoup(noscript_tag.decode_contents(), 'html.parser')
                    img_tag = img_soup.select_one('img')
                    if img_tag:
                        img_url = img_tag.get('src')
                recipes.append({'title': title, 'url': link, 'img': img_url, 'source': 'クラシル'})
        return recipes
    except Exception as e:
        print(f"[ERROR] Kurashiru fetch error: {e}")
        return []

def fetch_rakuten_recipes(query):
    encoded_query = urllib.parse.quote_plus(query)
    url = f'https://recipe.rakuten.co.jp/search/{encoded_query}'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10, verify=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        recipes = []
        for item in soup.select('li.recipe_ranking__item')[:15]:
            link_tag = item.select_one('a.recipe_ranking__link')
            title_tag = item.select_one('span.recipe_ranking__recipe_title')
            img_tag = item.select_one('img')
            if link_tag and title_tag and img_tag:
                title = title_tag.get_text(strip=True)
                link = link_tag.get('href')
                if not link.startswith('http'):
                    link = f"https://recipe.rakuten.co.jp{link}"
                img_url = img_tag.get('src')
                recipes.append({'title': title, 'url': link, 'img': img_url, 'source': '楽天レシピ'})
        return recipes
    except Exception as e:
        print(f"[ERROR] Rakuten fetch error: {e}")
        return []


# ---------- 認証関連ルート ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if not username or not email or not password:
            flash('すべての項目を入力してください')
            return render_template('register.html')
        
        if len(username) < 3:
            flash('ユーザー名は3文字以上で入力してください')
            return render_template('register.html')
            
        if len(password) < 6:
            flash('パスワードは6文字以上で入力してください')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('このユーザー名は既に使用されています')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('このメールアドレスは既に登録されています')
            return render_template('register.html')
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            print(f"[USER] New user registered: {username} (ID: {user.id})")
            flash('登録が完了しました。ログインしてください。')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] User registration failed: {e}")
            flash('登録中にエラーが発生しました。もう一度お試しください。')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session.permanent = True
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            session['login_time'] = datetime.utcnow().isoformat()
            
            print(f"[AUTH] Login successful: {username} (ID: {user.id})")
            flash(f'ログインしました。ようこそ、{username}さん！')
            return redirect(url_for('dashboard'))
        else:
            flash('ユーザー名またはパスワードが正しくありません')
            print(f"[AUTH] Login failed for username: {username}")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    username = session.get('username', 'Unknown')
    user_id = session.get('user_id', 'Unknown')
    session.clear()
    print(f"[AUTH] User logged out: {username} (ID: {user_id})")
    flash('ログアウトしました')
    return redirect(url_for('login'))


# ---------- メインアプリケーション（ページ分離） ----------

# トップ（ダッシュボード）
# app.pyのダッシュボードルート部分を以下に置き換え

import random

# ダッシュボードルート（修正版）
@app.route('/')
@login_required
def dashboard():
    user_id = session.get('user_id')
    print(f"[DASHBOARD] Accessed by user {user_id}")
    
    # 賞味期限通知を取得
    notifications = get_expiry_notifications(user_id)
    
    # 統計情報
    total_ingredients = Ingredient.query.filter_by(user_id=user_id).count()
    
    # 期限切れ間近の食材からおすすめレシピを取得
    recommended_recipes = []
    
    # 期限切れと3日以内期限切れの食材を組み合わせる
    priority_ingredients = notifications.get('expired', []) + notifications.get('expiring_soon', [])
    
    if priority_ingredients:
        # 最大3つの食材を選択（重複排除）
        selected_ingredients = list(set([ing.name for ing in priority_ingredients[:3]]))
        
        # 各食材でレシピ検索を実行
        all_recipes = []
        for ingredient_name in selected_ingredients:
            try:
                print(f"[RECIPE_FETCH] Searching recipes for: {ingredient_name}")
                
                # 各レシピサイトから検索
                nadia_recipes = fetch_nadia_recipes(ingredient_name)
                kurashiru_recipes = fetch_kurashiru_recipes(ingredient_name)
                rakuten_recipes = fetch_rakuten_recipes(ingredient_name)
                
                # 結果を統合
                site_recipes = nadia_recipes + kurashiru_recipes + rakuten_recipes
                
                # 各食材につき最大2つのレシピを選択
                if site_recipes:
                    selected = random.sample(site_recipes, min(2, len(site_recipes)))
                    for recipe in selected:
                        recipe['ingredient_used'] = ingredient_name  # どの食材で検索したかを記録
                    all_recipes.extend(selected)
                    
            except Exception as e:
                print(f"[ERROR] Recipe fetch failed for {ingredient_name}: {e}")
                continue
        
        # 全レシピから最大3つをランダム選択
        if all_recipes:
            recommended_recipes = random.sample(all_recipes, min(3, len(all_recipes)))
            print(f"[RECIPE_RECOMMEND] Selected {len(recommended_recipes)} recipes")
    
    return render_template('dashboard.html', 
                         notifications=notifications,
                         total_ingredients=total_ingredients,
                         recommended_recipes=recommended_recipes,
                         date=date)

# 期限切れが近い食材の名前を取得するヘルパー関数（追加）
def get_priority_ingredient_names(user_id):
    """期限切れ・間近の食材名をリストで返す"""
    notifications = get_expiry_notifications(user_id)
    priority_ingredients = notifications.get('expired', []) + notifications.get('expiring_soon', [])
    return list(set([ing.name for ing in priority_ingredients[:5]]))  # 最大5つ、重複排除

# 冷蔵庫（食材一覧）
@app.route('/refrigerator')
@login_required
def refrigerator():
    user_id = session.get('user_id')
    sort = request.args.get('sort')
    category_filter = request.args.get('category')
    
    query = Ingredient.query.filter_by(user_id=user_id)
    
    # カテゴリフィルタリング
    if category_filter and category_filter in PREDEFINED_CATEGORIES:
        query = query.filter_by(category=category_filter)
    
    ingredients = query.all()
    
    # ソート処理
    if sort == "expiry":
        ingredients = sorted(
            ingredients,
            key=lambda ing: (
                (ing.expiry_date - date.today()).days if ing.expiry_date else 9999
            )
        )
    elif sort == "name":
        ingredients = sorted(ingredients, key=lambda ing: ing.name)
    elif sort == "quantity":
        ingredients = sorted(ingredients, key=lambda ing: ing.quantity, reverse=True)
    elif sort == "category":
        ingredients = sorted(ingredients, key=lambda ing: ing.category)
    
    # 実際に使用されているカテゴリのみ取得
    used_categories = db.session.query(Ingredient.category).filter_by(user_id=user_id).distinct().all()
    used_categories = [cat[0] for cat in used_categories if cat[0]]
    
    # カテゴリごとにグループ化
    grouped = {}
    for ing in ingredients:
        grouped.setdefault(ing.category, []).append(ing)
    
    return render_template(
        'refrigerator.html', 
        ingredients=ingredients,
        grouped=grouped,
        sort=sort, 
        categories=used_categories,
        all_categories=PREDEFINED_CATEGORIES,  # フィルター用
        current_category=category_filter,
        date=date
    )
# レシピ検索
@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    user_id = session.get('user_id')
    results = []
    
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        selected_ingredients = request.form.getlist('selected_ingredients')
        
        print(f"[SEARCH] Request from user {user_id}: query='{query}', ingredients={selected_ingredients}")
        
        combined_query = " ".join(selected_ingredients + ([query] if query else []))
        
        if combined_query:
            try:
                print(f"[SEARCH] Querying with: '{combined_query}'")
                nadia_recipes = fetch_nadia_recipes(combined_query)
                kurashiru_recipes = fetch_kurashiru_recipes(combined_query)
                rakuten_recipes = fetch_rakuten_recipes(combined_query)

                results.extend(nadia_recipes)
                results.extend(kurashiru_recipes)
                results.extend(rakuten_recipes)

                print(f"[SEARCH] Nadia recipes: {len(nadia_recipes)}")
                print(f"[SEARCH] Kurashiru recipes: {len(kurashiru_recipes)}")
                print(f"[SEARCH] Rakuten recipes: {len(rakuten_recipes)}")
                print(f"[SEARCH] Total recipes fetched: {len(results)}")

            # ここで取得した結果を出力
                print(f"[SEARCH] Sample results: {results[:3]}") # 最初の3件を出力
        # ...
            except Exception as e:
                print(f"[ERROR] Recipe fetching failed: {e}")
                flash('レシピ検索中にエラーが発生しました')
                results = []
    
    ingredients = Ingredient.query.filter_by(user_id=user_id).all()
    
    return render_template('search.html', 
                         ingredients=ingredients, 
                         results=results, 
                         date=date)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_ingredient():
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        name = request.form.get('ingredient', '').strip()
        expiry_date_str = request.form.get('expiry_date')
        quantity = request.form.get('quantity', 1)
        category = request.form.get('category', '').strip()
        
        # カテゴリ検証
        if category not in PREDEFINED_CATEGORIES:
            category = 'その他'  # デフォルトにフォールバック
        
        print(f"[ADD] Request from user {user_id}: name='{name}', category='{category}'")
        
        if not name:
            flash('食材名を入力してください')
            return render_template('add_ingredient.html', categories=PREDEFINED_CATEGORIES)
        
        expiry_date = None
        if expiry_date_str:
            try:
                expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
            except ValueError:
                flash('日付の形式が正しくありません')
                return render_template('add_ingredient.html', categories=PREDEFINED_CATEGORIES)
        
        try:
            quantity_int = max(1, int(quantity))
        except (ValueError, TypeError):
            quantity_int = 1
        
        ingredient = Ingredient(
            name=name,
            expiry_date=expiry_date,
            quantity=quantity_int,
            category=category,
            user_id=user_id
        )
        
        try:
            db.session.add(ingredient)
            db.session.commit()
            print(f"[ADD] Success: '{name}' (category: {category})")
            flash(f'食材「{name}」を追加しました')
            return redirect(url_for('refrigerator'))
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Adding ingredient failed: {e}")
            flash('食材の追加中にエラーが発生しました')
    
    return render_template('add_ingredient.html', categories=PREDEFINED_CATEGORIES)

# 食材削除
@app.route('/delete_ingredient/<int:id>')
@login_required
def delete_ingredient(id):
    user_id = session.get('user_id')
    ingredient = Ingredient.query.filter_by(id=id, user_id=user_id).first_or_404()
    
    ingredient_name = ingredient.name
    try:
        db.session.delete(ingredient)
        db.session.commit()
        print(f"[DELETE] Success: '{ingredient_name}' deleted by user {user_id}")
        flash(f'食材「{ingredient_name}」を削除しました')
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Deleting ingredient failed: {e}")
        flash('食材の削除中にエラーが発生しました')
    
    return redirect(request.referrer or url_for('refrigerator'))

# 食材数量変更
@app.route('/change_quantity/<int:id>/<action>', methods=['POST'])
@login_required
def change_quantity(id, action):
    user_id = session.get('user_id')
    ingredient = Ingredient.query.filter_by(id=id, user_id=user_id).first_or_404()
    
    old_quantity = ingredient.quantity
    if action == "plus":
        ingredient.quantity += 1
    elif action == "minus" and ingredient.quantity > 1:
        ingredient.quantity -= 1
    
    try:
        db.session.commit()
        print(f"[QUANTITY] Success: {ingredient.name} {old_quantity} -> {ingredient.quantity}")
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Quantity change failed: {e}")
        flash('数量の変更中にエラーが発生しました')
    
    return redirect(request.referrer or url_for('refrigerator'))


# app.pyに以下のルートを追加

@app.route('/bulk_delete', methods=['POST'])
@login_required
def bulk_delete():
    user_id = session.get('user_id')
    ingredient_ids = request.form.getlist('ingredient_ids[]')
    
    if not ingredient_ids:
        flash('削除する食材を選択してください')
        return redirect(url_for('refrigerator'))
    
    try:
        # 選択された食材IDを整数に変換
        ids = [int(id) for id in ingredient_ids]
        
        # ユーザーの食材のみを削除
        deleted_count = Ingredient.query.filter(
            Ingredient.id.in_(ids),
            Ingredient.user_id == user_id
        ).delete(synchronize_session=False)
        
        db.session.commit()
        
        print(f"[BULK_DELETE] User {user_id} deleted {deleted_count} ingredients")
        flash(f'{deleted_count}件の食材を削除しました')
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Bulk delete failed: {e}")
        flash('一括削除中にエラーが発生しました')
    
    return redirect(url_for('refrigerator'))


@app.route('/bulk_change_category', methods=['POST'])
@login_required
def bulk_change_category():
    user_id = session.get('user_id')
    ingredient_ids = request.form.getlist('ingredient_ids[]')
    new_category = request.form.get('new_category', '').strip()
    
    if not ingredient_ids:
        flash('カテゴリを変更する食材を選択してください')
        return redirect(url_for('refrigerator'))
    
    if new_category not in PREDEFINED_CATEGORIES:
        flash('無効なカテゴリです')
        return redirect(url_for('refrigerator'))
    
    try:
        # 選択された食材IDを整数に変換
        ids = [int(id) for id in ingredient_ids]
        
        # ユーザーの食材のみを更新
        updated_count = Ingredient.query.filter(
            Ingredient.id.in_(ids),
            Ingredient.user_id == user_id
        ).update({'category': new_category}, synchronize_session=False)
        
        db.session.commit()
        
        print(f"[BULK_CATEGORY] User {user_id} updated {updated_count} ingredients to {new_category}")
        flash(f'{updated_count}件の食材のカテゴリを「{new_category}」に変更しました')
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Bulk category change failed: {e}")
        flash('一括カテゴリ変更中にエラーが発生しました')
    
    return redirect(url_for('refrigerator'))


@app.route('/bulk_change_quantity', methods=['POST'])
@login_required
def bulk_change_quantity():
    user_id = session.get('user_id')
    ingredient_ids = request.form.getlist('ingredient_ids[]')
    action = request.form.get('action', 'set')  # 'set', 'add', 'subtract'
    quantity_value = request.form.get('quantity_value', 1)
    
    if not ingredient_ids:
        flash('数量を変更する食材を選択してください')
        return redirect(url_for('refrigerator'))
    
    try:
        quantity_value = int(quantity_value)
        ids = [int(id) for id in ingredient_ids]
        
        ingredients = Ingredient.query.filter(
            Ingredient.id.in_(ids),
            Ingredient.user_id == user_id
        ).all()
        
        updated_count = 0
        for ing in ingredients:
            if action == 'set':
                ing.quantity = max(1, quantity_value)
            elif action == 'add':
                ing.quantity += quantity_value
            elif action == 'subtract':
                ing.quantity = max(1, ing.quantity - quantity_value)
            updated_count += 1
        
        db.session.commit()
        
        print(f"[BULK_QUANTITY] User {user_id} updated {updated_count} ingredients")
        flash(f'{updated_count}件の食材の数量を変更しました')
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Bulk quantity change failed: {e}")
        flash('一括数量変更中にエラーが発生しました')
    
    return redirect(url_for('refrigerator'))



@app.route('/edit_category/<int:id>', methods=['POST'])
@login_required  
def edit_category(id):
    user_id = session.get('user_id')
    ingredient = Ingredient.query.filter_by(id=id, user_id=user_id).first_or_404()
    
    new_category = request.form.get('category', '').strip()
    
    # カテゴリが定義済みのリストに含まれているか検証
    if new_category not in PREDEFINED_CATEGORIES:
        flash('無効なカテゴリです')
        return redirect(request.referrer or url_for('refrigerator'))
    
    old_category = ingredient.category
    ingredient.category = new_category
    
    try:
        db.session.commit()
        print(f"[CATEGORY] Updated: {ingredient.name} {old_category} -> {new_category}")
        flash(f'「{ingredient.name}」のカテゴリを「{new_category}」に変更しました')
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Category update failed: {e}")
        flash('カテゴリの変更中にエラーが発生しました')
    
    return redirect(request.referrer or url_for('refrigerator'))


# デバッグ用ルート
@app.route('/debug')
@login_required
def debug():
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    ingredients = Ingredient.query.filter_by(user_id=user_id).all() if user_id else []
    notifications = get_expiry_notifications(user_id) if user_id else {}
    
    # カテゴリ統計を追加
    category_stats = {}
    for ing in ingredients:
        cat = ing.category or '未分類'
        category_stats[cat] = category_stats.get(cat, 0) + 1
    
    debug_info = {
        'system_info': {
            'https_detected': IS_HTTPS,
            'session_secure': app.config['SESSION_COOKIE_SECURE'],
            'cache_prevention': 'enabled',
            'category_feature': 'enabled'  # 追加
        },
        'user_data': {
            'ingredients_count': len(ingredients),
            'category_distribution': category_stats,  # 追加
            'notifications': {
                'expired': len(notifications.get('expired', [])),
                'expiring_soon': len(notifications.get('expiring_soon', [])),
                'expiring_week': len(notifications.get('expiring_week', []))
            }
        }
    }
    
    import json
    return f"<pre>{json.dumps(debug_info, indent=2, ensure_ascii=False)}</pre>"

# データベースマイグレーション関数
# データベースマイグレーション関数
def migrate_database():
    """既存データベースにcategoryカラムを追加"""
    try:
        from sqlalchemy import text, inspect
        
        # インスペクタを使用してカラムの存在を確認
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('ingredient')]
        
        if 'category' not in columns:
            # text()を使用してSQL文を実行
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE ingredient ADD COLUMN category VARCHAR(20)'))
                conn.commit()
            print("[MIGRATION] categoryカラムを追加しました")
        else:
            print("[MIGRATION] categoryカラムは既に存在します")
            
    except Exception as e:
        print(f"[MIGRATION ERROR] {e}")


# データベース初期化時に実行
with app.app_context():
    db.create_all()
    migrate_database()  

if __name__ == '__main__':
    print("=" * 60)
    print("🍳 Recipe Search App (Multi-Page Version) Starting...")
    print("=" * 60)
    print(f"HTTPS Environment: {IS_HTTPS}")
    print("📱 Pages: Dashboard, Refrigerator, Search, Add")
    print("🔔 Notifications: Expiry alerts enabled")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)