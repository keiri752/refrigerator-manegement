from flask import session, flash, redirect, url_for, request, render_template, Blueprint
from datetime import datetime
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# ====================
# Blueprintの定義
# ====================
loginout_bp = Blueprint('loginout_app', __name__, url_prefix='/loginout')


# ログイン必須デコレータ
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        username = session.get('username')
        print(f"[AUTH] Session check: user_id={user_id}, username={username}")
        
        if 'user_id' not in session:
            flash('セッションが切れています。再度ログインしてください。')
            return redirect(url_for('loginout_app.login'))
        return f(*args, **kwargs)
    return decorated_function


# ---------- 認証関連ルート ----------
@loginout_bp.route('/register', methods=['GET', 'POST'])
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
            return redirect(url_for('loginout_app.login'))
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] User registration failed: {e}")
            flash('登録中にエラーが発生しました。もう一度お試しください。')
    
    return render_template('register.html')

@loginout_bp.route('/login', methods=['GET', 'POST'])
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
            return redirect(url_for('recipe_app.dashboard'))
        else:
            flash('ユーザー名またはパスワードが正しくありません')
            print(f"[AUTH] Login failed for username: {username}")
    
    return render_template('login.html')

@loginout_bp.route('/logout')
def logout():
    username = session.get('username', 'Unknown')
    user_id = session.get('user_id', 'Unknown')
    session.clear()
    print(f"[AUTH] User logged out: {username} (ID: {user_id})")
    flash('ログアウトしました')
    return redirect(url_for('loginout_app.login'))

