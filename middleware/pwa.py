from flask import send_from_directory, Blueprint

# ====================
# Blueprint
# ====================
pwa_bp = Blueprint('pwa_app', __name__, url_prefix='/pwa')


# PWA用のルート
@pwa_bp.route('/manifest.json')
def manifest():
    response = send_from_directory('static', 'manifest.json')
    response.headers['Cache-Control'] = 'public, max-age=604800'
    return response

@pwa_bp.route('/sw.js')
def service_worker():
    response = send_from_directory('static', 'sw.js')
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response