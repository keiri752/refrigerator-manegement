from flask import session, Blueprint, current_app
from models import User, Ingredient
from functions import get_expiry_notifications
from middleware.https_redirect import IS_HTTPS
from middleware.login_out import login_required
from config import Config

# ====================
# Blueprintの定義
# ====================
debug_bp = Blueprint('debug_app', __name__, url_prefix='')



# デバッグ用ルート
@debug_bp.route('/debug')
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
            'session_secure': current_app.config.get('SESSION_COOKIE_SECURE'),
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

