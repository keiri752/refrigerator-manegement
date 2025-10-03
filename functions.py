from models import db, Ingredient, FavoriteRecipe
from datetime import date
from bs4 import BeautifulSoup
import requests
import urllib.parse
import  os


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








# 期限切れが近い食材の名前を取得するヘルパー関数（追加）
def get_priority_ingredient_names(user_id):
    """期限切れ・間近の食材名をリストで返す"""
    notifications = get_expiry_notifications(user_id)
    priority_ingredients = notifications.get('expired', []) + notifications.get('expiring_soon', [])
    return list(set([ing.name for ing in priority_ingredients[:5]]))  # 最大5つ、重複排除













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

def migrate_recipe_features():
    """お気に入り・履歴テーブルを作成"""
    try:
    # テーブルを作成（存在しない場合のみ）
        db.create_all()
        print("[MIGRATION] Recipe features tables checked/created")
    except Exception as e:
        print(f"[MIGRATION ERROR] {e}")







# 【3】ヘルパー関数（検索結果でお気に入り状態を確認するため）

def get_favorite_urls(user_id):
    """ユーザーのお気に入りレシピのURLリストを取得"""
    favorites = FavoriteRecipe.query.filter_by(user_id=user_id).all()
    return [fav.url for fav in favorites]






# HTTPS環境の自動検出
def is_https_environment():
    if os.environ.get('HTTPS') == 'on':
        return True
    if os.environ.get('HTTP_X_FORWARDED_PROTO') == 'https':
        return True
    if os.environ.get('HTTP_X_FORWARDED_SSL') == 'on':
        return True
    return False