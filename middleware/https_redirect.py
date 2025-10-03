from flask import request, redirect, Blueprint
from functions import is_https_environment
import os


# ====================
# Blueprintの定義
# ====================
https_bp = Blueprint('https_app', __name__, url_prefix='')



IS_HTTPS = is_https_environment()
FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'False').lower() == 'true'



# HTTPS強制リダイレクト
@https_bp.before_request
def force_https():
    if FORCE_HTTPS and not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
        return redirect(request.url.replace('http://', 'https://'), code=301)

