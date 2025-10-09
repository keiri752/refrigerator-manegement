from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date, timedelta
import urllib.parse
import requests
from bs4 import BeautifulSoup
import os
from models import db, User, Ingredient, FavoriteRecipe, RecipeHistory
from functions import (
    get_expiry_notifications, 
    fetch_nadia_recipes,
    fetch_kurashiru_recipes, 
    fetch_rakuten_recipes, 
    get_favorite_urls, 
    migrate_database,
)
from middleware.cathe import cathe_bp
from middleware.debug import debug_bp
from middleware.https_redirect import https_bp, IS_HTTPS
from middleware.login_out import loginout_bp
from middleware.pwa import pwa_bp
from middleware.recipe import recipe_bp
from config import Config
# 既存のインポートの後に追加
from middleware.push_notification import push_bp

app = Flask(__name__)
app.config.from_object(Config)

# ====================
# Blueprintの登録
# ====================
app.register_blueprint(cathe_bp)
app.register_blueprint(debug_bp)
app.register_blueprint(https_bp)
app.register_blueprint(loginout_bp)
app.register_blueprint(pwa_bp)
app.register_blueprint(recipe_bp)
# 既存のapp.register_blueprint()の後に追加
app.register_blueprint(push_bp)



# Service Workerをルート直下で配信（PWA Blueprintとは別）
@app.route('/sw.js')
def service_worker_root():
    response = send_from_directory('static', 'sw.js', mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response


# ====================
# dbとappの接続
# ====================
db.init_app(app)


with app.app_context():
    db.create_all()

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