from models import db, Ingredient, FavoriteRecipe
from datetime import date
from bs4 import BeautifulSoup
import requests
import urllib.parse
import  os
from pywebpush import webpush, WebPushException
import json
from models import PushSubscription
from datetime import datetime

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







def send_push_notification(user_id, title, body, url=None, icon=None):
    """ユーザーにプッシュ通知を送信"""
    try:
        from flask import current_app
        
        # ユーザーの全購読を取得
        subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
        
        if not subscriptions:
            print(f"[PUSH] No subscriptions found for user {user_id}")
            return False
        
        # 通知ペイロード
        payload = {
            'title': title,
            'body': body,
            'icon': icon or '/static/icon-192x192.png',
            'badge': '/static/icon-192x192.png',
            'url': url or '/',
            'timestamp': datetime.now().isoformat()
        }
        
        success_count = 0
        failed_subscriptions = []
        
        # 各購読に通知を送信
        for subscription in subscriptions:
            try:
                webpush(
                    subscription_info=subscription.to_dict(),
                    data=json.dumps(payload),
                    vapid_private_key=current_app.config['VAPID_PRIVATE_KEY'],
                    vapid_claims=current_app.config['VAPID_CLAIMS']
                )
                success_count += 1
                print(f"[PUSH] Sent to subscription {subscription.id}")
                
            except WebPushException as e:
                print(f"[PUSH ERROR] Failed to send: {e}")
                # 無効な購読（404, 410エラー）を記録
                if e.response and e.response.status_code in [404, 410]:
                    failed_subscriptions.append(subscription)
        
        # 無効な購読を削除
        for sub in failed_subscriptions:
            db.session.delete(sub)
            print(f"[PUSH] Removed invalid subscription {sub.id}")
        
        if failed_subscriptions:
            db.session.commit()
        
        return success_count > 0
        
    except Exception as e:
        print(f"[PUSH ERROR] send_push_notification failed: {e}")
        return False


def check_and_send_expiry_notifications():
    """全ユーザーの賞味期限をチェックして通知を送信"""
    try:
        from models import User
        users = User.query.all()
        
        for user in users:
            notifications = get_expiry_notifications(user.id)
            
            # 賞味期限切れ通知
            if notifications['expired']:
                ingredient_names = ', '.join([ing.name for ing in notifications['expired'][:3]])
                count = len(notifications['expired'])
                more = f'など{count}個' if count > 3 else f'{count}個'
                
                send_push_notification(
                    user.id,
                    '⚠️ 賞味期限切れの食材があります',
                    f'{ingredient_names}{more}の食材が期限切れです',
                    url='/refrigerator'
                )
            
            # 3日以内通知
            elif notifications['expiring_soon']:
                ingredient_names = ', '.join([ing.name for ing in notifications['expiring_soon'][:3]])
                count = len(notifications['expiring_soon'])
                more = f'など{count}個' if count > 3 else f'{count}個'
                
                send_push_notification(
                    user.id,
                    '⏰ 賞味期限が近づいています',
                    f'{ingredient_names}{more}の食材が3日以内に期限切れになります',
                    url='/search'
                )
        
        print(f"[PUSH] Checked {len(users)} users for expiry notifications")
        return True
        
    except Exception as e:
        print(f"[PUSH ERROR] check_and_send_expiry_notifications failed: {e}")
        return False