from flask import request, Blueprint
from datetime import datetime
from middleware.https_redirect import IS_HTTPS


# ====================
# Blueprintの定義
# ====================
cathe_bp = Blueprint('cathe_app', __name__, url_prefix='')

# キャッシュ制御
@cathe_bp.after_request
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

