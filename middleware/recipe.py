from flask import session, Blueprint, render_template, request, flash, redirect, url_for
from middleware.login_out import login_required
from datetime import datetime, date
from models import db, Ingredient, FavoriteRecipe, RecipeHistory
from functions import(
    get_expiry_notifications, 
    fetch_nadia_recipes,
    fetch_kurashiru_recipes,
    fetch_rakuten_recipes,
    get_favorite_urls,
)




# ====================
# Blueprintの定義
# ====================
recipe_bp = Blueprint('recipe_app', __name__, url_prefix='')





PREDEFINED_CATEGORIES = [
    '野菜', '肉類', '魚介類', '乳製品', '穀類', '調味料', 'その他'
]


# ---------- メインアプリケーション（ページ分離） ----------

# トップ（ダッシュボード）
# app.pyのダッシュボードルート部分を以下に置き換え

import random

# ダッシュボードルート（修正版）
@recipe_bp.route('/')
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

# 冷蔵庫（食材一覧）
@recipe_bp.route('/refrigerator')
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
@recipe_bp.route('/search', methods=['GET', 'POST'])
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
    favorite_urls = get_favorite_urls(user_id)
    
    return render_template('search.html', 
                         ingredients=ingredients, 
                         results=results,
                         favorite_urls=favorite_urls, 
                         date=date)



# ---------- お気に入り機能 ----------

@recipe_bp.route('/add_favorite', methods=['POST'])
@login_required
def add_favorite():
    """お気に入りに追加"""
    user_id = session.get('user_id')
    title = request.form.get('title', '').strip()
    url = request.form.get('url', '').strip()
    img = request.form.get('img', '').strip()
    source = request.form.get('source', '').strip()
    
    if not title or not url or not source:
        flash('レシピ情報が不完全です')
        return redirect(request.referrer or url_for('recipe_app.search'))
    
    # 重複チェック（同じURLが既に登録されているか）
    exists = FavoriteRecipe.query.filter_by(
        user_id=user_id, 
        url=url
    ).first()
    
    if exists:
        flash('このレシピは既にお気に入りに登録されています')
    else:
        try:
            favorite = FavoriteRecipe(
                user_id=user_id,
                title=title,
                url=url,
                img=img,
                source=source
            )
            db.session.add(favorite)
            db.session.commit()
            print(f"[FAVORITE] Added: '{title}' by user {user_id}")
            flash(f'「{title}」をお気に入りに追加しました')
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Add favorite failed: {e}")
            flash('お気に入りの追加中にエラーが発生しました')
    
    return redirect(request.referrer or url_for('recipe_app.search'))


@recipe_bp.route('/favorites')
@login_required
def favorites():
    """お気に入り一覧"""
    user_id = session.get('user_id')
    favorites = FavoriteRecipe.query.filter_by(user_id=user_id)\
        .order_by(FavoriteRecipe.created_at.desc()).all()
    
    print(f"[FAVORITES] User {user_id} has {len(favorites)} favorites")
    return render_template('favorites.html', favorites=favorites)


@recipe_bp.route('/remove_favorite/<int:id>')
@login_required
def remove_favorite(id):
    """お気に入りから削除"""
    user_id = session.get('user_id')
    favorite = FavoriteRecipe.query.filter_by(id=id, user_id=user_id).first_or_404()
    
    title = favorite.title
    try:
        db.session.delete(favorite)
        db.session.commit()
        print(f"[FAVORITE] Removed: '{title}' by user {user_id}")
        flash(f'「{title}」をお気に入りから削除しました')
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Remove favorite failed: {e}")
        flash('お気に入りの削除中にエラーが発生しました')
    
    return redirect(url_for('recipe_app.favorites'))


@recipe_bp.route('/toggle_favorite', methods=['POST'])
@login_required
def toggle_favorite():
    """お気に入りのトグル（追加/削除を切り替え）- AJAX用"""
    user_id = session.get('user_id')
    url = request.form.get('url', '').strip()
    
    if not url:
        return {'status': 'error', 'message': 'URLが指定されていません'}, 400
    
    # 既存のお気に入りをチェック
    favorite = FavoriteRecipe.query.filter_by(user_id=user_id, url=url).first()
    
    try:
        if favorite:
            # 削除
            db.session.delete(favorite)
            db.session.commit()
            return {'status': 'removed', 'message': 'お気に入りから削除しました'}, 200
        else:
            # 追加
            title = request.form.get('title', '').strip()
            img = request.form.get('img', '').strip()
            source = request.form.get('source', '').strip()
            
            favorite = FavoriteRecipe(
                user_id=user_id,
                title=title,
                url=url,
                img=img,
                source=source
            )
            db.session.add(favorite)
            db.session.commit()
            return {'status': 'added', 'message': 'お気に入りに追加しました'}, 200
            
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Toggle favorite failed: {e}")
        return {'status': 'error', 'message': 'エラーが発生しました'}, 500


# ---------- 閲覧履歴機能 ----------

@recipe_bp.route('/record_view', methods=['POST'])
@login_required
def record_view():
    """閲覧履歴に記録（レシピリンククリック時に自動実行）"""
    user_id = session.get('user_id')
    title = request.form.get('title', '').strip()
    url = request.form.get('url', '').strip()
    img = request.form.get('img', '').strip()
    source = request.form.get('source', '').strip()
    
    if not title or not url or not source:
        return '', 400
    
    try:
        # 同じURLの履歴が既に存在する場合は更新（最新の閲覧日時に）
        existing = RecipeHistory.query.filter_by(user_id=user_id, url=url).first()
        if existing:
            existing.viewed_at = datetime.utcnow()
            existing.title = title  # タイトルも更新
            existing.img = img
            existing.source = source
        else:
            # 新規追加
            history = RecipeHistory(
                user_id=user_id,
                title=title,
                url=url,
                img=img,
                source=source
            )
            db.session.add(history)
        
        db.session.commit()
        
        # 履歴が50件を超えたら古いものを削除
        history_count = RecipeHistory.query.filter_by(user_id=user_id).count()
        if history_count > 50:
            old_records = RecipeHistory.query.filter_by(user_id=user_id)\
                .order_by(RecipeHistory.viewed_at.asc())\
                .limit(history_count - 50).all()
            for record in old_records:
                db.session.delete(record)
            db.session.commit()
            print(f"[HISTORY] Cleaned up old records for user {user_id}")
        
        print(f"[HISTORY] Recorded: '{title}' by user {user_id}")
        return '', 204  # No Content (成功)
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Record view failed: {e}")
        return '', 500


@recipe_bp.route('/history')
@login_required
def history():
    """閲覧履歴一覧"""
    user_id = session.get('user_id')
    history = RecipeHistory.query.filter_by(user_id=user_id)\
        .order_by(RecipeHistory.viewed_at.desc()).all()
    
    print(f"[HISTORY] User {user_id} has {len(history)} history records")
    return render_template('history.html', history=history)


@recipe_bp.route('/clear_history')
@login_required
def clear_history():
    """閲覧履歴を全てクリア"""
    user_id = session.get('user_id')
    
    try:
        deleted_count = RecipeHistory.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        print(f"[HISTORY] Cleared {deleted_count} records for user {user_id}")
        flash(f'{deleted_count}件の閲覧履歴をクリアしました')
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Clear history failed: {e}")
        flash('閲覧履歴のクリア中にエラーが発生しました')
    
    return redirect(url_for('recipe_app.history'))


@recipe_bp.route('/remove_history/<int:id>')
@login_required
def remove_history(id):
    """閲覧履歴から個別に削除"""
    user_id = session.get('user_id')
    history_item = RecipeHistory.query.filter_by(id=id, user_id=user_id).first_or_404()
    
    title = history_item.title
    try:
        db.session.delete(history_item)
        db.session.commit()
        print(f"[HISTORY] Removed: '{title}' by user {user_id}")
        flash(f'「{title}」を閲覧履歴から削除しました')
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Remove history failed: {e}")
        flash('閲覧履歴の削除中にエラーが発生しました')
    
    return redirect(url_for('recipe_app.history'))


@recipe_bp.route('/add', methods=['GET', 'POST'])
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
            return redirect(url_for('recipe_app.refrigerator'))
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Adding ingredient failed: {e}")
            flash('食材の追加中にエラーが発生しました')
    
    return render_template('add_ingredient.html', categories=PREDEFINED_CATEGORIES)

# 食材削除
@recipe_bp.route('/delete_ingredient/<int:id>')
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
    
    return redirect(request.referrer or url_for('recipe_app.refrigerator'))

# 食材数量変更
@recipe_bp.route('/change_quantity/<int:id>/<action>', methods=['POST'])
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
    
    return redirect(request.referrer or url_for('recipe_app.refrigerator'))


# app.pyに以下のルートを追加

@recipe_bp.route('/bulk_delete', methods=['POST'])
@login_required
def bulk_delete():
    user_id = session.get('user_id')
    ingredient_ids = request.form.getlist('ingredient_ids[]')
    
    if not ingredient_ids:
        flash('削除する食材を選択してください')
        return redirect(url_for('recipe_app.refrigerator'))
    
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
    
    return redirect(url_for('recipe_app.refrigerator'))


@recipe_bp.route('/bulk_change_category', methods=['POST'])
@login_required
def bulk_change_category():
    user_id = session.get('user_id')
    ingredient_ids = request.form.getlist('ingredient_ids[]')
    new_category = request.form.get('new_category', '').strip()
    
    if not ingredient_ids:
        flash('カテゴリを変更する食材を選択してください')
        return redirect(url_for('recipe_app.refrigerator'))
    
    if new_category not in PREDEFINED_CATEGORIES:
        flash('無効なカテゴリです')
        return redirect(url_for('recipe_app.refrigerator'))
    
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
    
    return redirect(url_for('recipe_app.refrigerator'))


@recipe_bp.route('/bulk_change_quantity', methods=['POST'])
@login_required
def bulk_change_quantity():
    user_id = session.get('user_id')
    ingredient_ids = request.form.getlist('ingredient_ids[]')
    action = request.form.get('action', 'set')  # 'set', 'add', 'subtract'
    quantity_value = request.form.get('quantity_value', 1)
    
    if not ingredient_ids:
        flash('数量を変更する食材を選択してください')
        return redirect(url_for('recipe_app.refrigerator'))
    
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
    
    return redirect(url_for('recipe_app.refrigerator'))



@recipe_bp.route('/edit_category/<int:id>', methods=['POST'])
@login_required  
def edit_category(id):
    user_id = session.get('user_id')
    ingredient = Ingredient.query.filter_by(id=id, user_id=user_id).first_or_404()
    
    new_category = request.form.get('category', '').strip()
    
    # カテゴリが定義済みのリストに含まれているか検証
    if new_category not in PREDEFINED_CATEGORIES:
        flash('無効なカテゴリです')
        return redirect(request.referrer or url_for('recipe_app.refrigerator'))
    
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
    
    return redirect(request.referrer or url_for('recipe_app.refrigerator'))

