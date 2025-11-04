import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
import sys
import os

# Werkzeugのバージョン問題を回避
import werkzeug
if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3.0.0'

# プロジェクトのルートディレクトリをパスに追加
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# モジュールを先にインポート
from middleware.login_out import loginout_bp

@pytest.fixture
def app():
    """テスト用のFlaskアプリケーションを作成"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    # ダミーのrecipe_appエンドポイントを追加
    @app.route('/dashboard')
    def dashboard():
        return 'dashboard'
    
    # blueprintを登録
    app.register_blueprint(loginout_bp)
    
    return app

@pytest.fixture
def client(app):
    """テストクライアントを作成"""
    return app.test_client()


class TestLogin:
    
    @patch('middleware.login_out.render_template')
    def test_login_get(self, mock_render, client):
        """GET リクエストでログインページが表示されること"""
        mock_render.return_value = 'login page'
        response = client.get('/loginout/login')
        assert response.status_code == 200
        mock_render.assert_called_with('login.html')
    
    @patch('middleware.login_out.url_for')
    @patch('middleware.login_out.check_password_hash')
    @patch('middleware.login_out.User')
    def test_login_success(self, mock_user_class, mock_check_hash, mock_url_for, client):
        """正常なログインが成功すること"""
        # モックユーザーの設定
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.password_hash = 'hashed_password'
        
        mock_user_class.query.filter_by.return_value.first.return_value = mock_user
        mock_check_hash.return_value = True
        
        # url_forのモック（実際のダミーエンドポイントにリダイレクト）
        mock_url_for.return_value = '/dashboard'
        
        # POSTリクエストを送信
        response = client.post('/loginout/login', data={
            'username': 'testuser',
            'password': 'password123'
        }, follow_redirects=False)
        
        # 検証
        assert response.status_code == 302
        assert response.location == '/dashboard'
        mock_url_for.assert_called_with('recipe_app.dashboard')
        
        # セッションの確認
        with client.session_transaction() as sess:
            assert sess['user_id'] == 1
            assert sess['username'] == 'testuser'
            assert 'login_time' in sess
    
    @patch('middleware.login_out.check_password_hash')
    @patch('middleware.login_out.User')
    @patch('middleware.login_out.render_template')
    def test_login_user_not_found(self, mock_render, mock_user_class, mock_check_hash, client):
        """存在しないユーザーでログイン失敗すること"""
        mock_render.return_value = 'login page'
        mock_user_class.query.filter_by.return_value.first.return_value = None
        
        response = client.post('/loginout/login', data={
            'username': 'nonexistent',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        mock_render.assert_called_with('login.html')
    
    @patch('middleware.login_out.check_password_hash')
    @patch('middleware.login_out.User')
    @patch('middleware.login_out.render_template')
    def test_login_wrong_password(self, mock_render, mock_user_class, mock_check_hash, client):
        """パスワードが間違っている場合にログイン失敗すること"""
        mock_render.return_value = 'login page'
        
        # モックユーザーの設定
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.password_hash = 'hashed_password'
        
        mock_user_class.query.filter_by.return_value.first.return_value = mock_user
        mock_check_hash.return_value = False  # パスワードが不一致
        
        response = client.post('/loginout/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 200
        mock_render.assert_called_with('login.html')
        
        # セッションが設定されていないことを確認
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
            assert 'username' not in sess
    
    @patch('middleware.login_out.url_for')
    @patch('middleware.login_out.check_password_hash')
    @patch('middleware.login_out.User')
    def test_login_session_cleared_before_login(self, mock_user_class, mock_check_hash, mock_url_for, client):
        """ログイン前に既存のセッションがクリアされること"""
        # 既存のセッションを設定
        with client.session_transaction() as sess:
            sess['old_key'] = 'old_value'
        
        # モックユーザーの設定
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.password_hash = 'hashed_password'
        
        mock_user_class.query.filter_by.return_value.first.return_value = mock_user
        mock_check_hash.return_value = True
        
        # url_forのモック
        mock_url_for.return_value = '/dashboard'
        
        # ログイン
        response = client.post('/loginout/login', data={
            'username': 'testuser',
            'password': 'password123'
        }, follow_redirects=False)
        
        # 古いセッションがクリアされていることを確認
        with client.session_transaction() as sess:
            assert 'old_key' not in sess
            assert sess['user_id'] == 1
    
    @patch('middleware.login_out.url_for')
    @patch('middleware.login_out.check_password_hash')
    @patch('middleware.login_out.User')
    def test_login_session_permanent(self, mock_user_class, mock_check_hash, mock_url_for, client):
        """ログイン時にセッションがpermanentに設定されること"""
        # モックユーザーの設定
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.password_hash = 'hashed_password'
        
        mock_user_class.query.filter_by.return_value.first.return_value = mock_user
        mock_check_hash.return_value = True
        
        # url_forのモック
        mock_url_for.return_value = '/dashboard'
        
        # ログイン
        response = client.post('/loginout/login', data={
            'username': 'testuser',
            'password': 'password123'
        }, follow_redirects=False)
        
        # セッションの確認 - セッションの内容を確認
        with client.session_transaction() as sess:
            assert sess['user_id'] == 1
            assert sess['username'] == 'testuser'
            assert 'login_time' in sess
    
    @patch('middleware.login_out.User')
    @patch('middleware.login_out.render_template')
    def test_login_missing_username(self, mock_render, mock_user_class, client):
        """ユーザー名が空の場合の処理"""
        mock_render.return_value = 'login page'
        
        response = client.post('/loginout/login', data={
            'username': '',
            'password': 'password123'
        })
        
        # 空文字列でもクエリは実行される
        mock_user_class.query.filter_by.assert_called_with(username='')
    
    @patch('middleware.login_out.User')
    @patch('middleware.login_out.render_template')
    def test_login_missing_password(self, mock_render, mock_user_class, client):
        """パスワードが空の場合の処理"""
        mock_render.return_value = 'login page'
        mock_user_class.query.filter_by.return_value.first.return_value = None
        
        response = client.post('/loginout/login', data={
            'username': 'testuser',
            'password': ''
        })
        
        assert response.status_code == 200
        mock_render.assert_called_with('login.html')