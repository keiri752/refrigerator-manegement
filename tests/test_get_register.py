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
    
    # blueprintを登録
    app.register_blueprint(loginout_bp)
    
    return app

@pytest.fixture
def client(app):
    """テストクライアントを作成"""
    return app.test_client()


class TestRegister:
    
    @patch('middleware.login_out.render_template')
    def test_register_get(self, mock_render, client):
        """GET リクエストで登録ページが表示されること"""
        mock_render.return_value = 'register page'
        response = client.get('/loginout/register')
        assert response.status_code == 200
        mock_render.assert_called_with('register.html')
    
    @patch('middleware.login_out.generate_password_hash')
    @patch('middleware.login_out.db')
    @patch('middleware.login_out.User')
    @patch('middleware.login_out.render_template')
    def test_register_success(self, mock_render, mock_user_class, mock_db, mock_hash, client):
        """正常な登録処理が成功すること"""
        # モックの設定
        mock_render.return_value = 'register page'
        mock_hash.return_value = 'hashed_password'
        mock_user_class.query.filter_by.return_value.first.return_value = None
        
        # Userインスタンスのモック
        mock_user_instance = Mock()
        mock_user_instance.id = 1
        mock_user_instance.username = 'testuser'
        mock_user_class.return_value = mock_user_instance
        
        # POSTリクエストを送信
        response = client.post('/loginout/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=False)
        
        # 検証
        assert response.status_code == 302
        assert '/loginout/login' in response.location
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()
    
    @patch('middleware.login_out.User')
    @patch('middleware.login_out.render_template')
    def test_register_missing_fields(self, mock_render, mock_user, client):
        """必須項目が欠けている場合のテスト"""
        mock_render.return_value = 'register page'
        
        response = client.post('/loginout/register', data={
            'username': '',
            'email': 'test@example.com',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        mock_render.assert_called_with('register.html')
    
    @patch('middleware.login_out.User')
    @patch('middleware.login_out.render_template')
    def test_register_short_username(self, mock_render, mock_user, client):
        """ユーザー名が短すぎる場合のテスト"""
        mock_render.return_value = 'register page'
        
        response = client.post('/loginout/register', data={
            'username': 'ab',
            'email': 'test@example.com',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        mock_render.assert_called_with('register.html')
    
    @patch('middleware.login_out.User')
    @patch('middleware.login_out.render_template')
    def test_register_short_password(self, mock_render, mock_user, client):
        """パスワードが短すぎる場合のテスト"""
        mock_render.return_value = 'register page'
        
        response = client.post('/loginout/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '12345'
        })
        
        assert response.status_code == 200
        mock_render.assert_called_with('register.html')
    
    @patch('middleware.login_out.User')
    @patch('middleware.login_out.render_template')
    def test_register_duplicate_username(self, mock_render, mock_user_class, client):
        """既に存在するユーザー名の場合のテスト"""
        mock_render.return_value = 'register page'
        
        mock_existing_user = Mock()
        mock_user_class.query.filter_by.return_value.first.side_effect = [
            mock_existing_user,
            None
        ]
        
        response = client.post('/loginout/register', data={
            'username': 'existinguser',
            'email': 'test@example.com',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        mock_render.assert_called_with('register.html')
    
    @patch('middleware.login_out.User')
    @patch('middleware.login_out.render_template')
    def test_register_duplicate_email(self, mock_render, mock_user_class, client):
        """既に存在するメールアドレスの場合のテスト"""
        mock_render.return_value = 'register page'
        
        mock_existing_user = Mock()
        mock_user_class.query.filter_by.return_value.first.side_effect = [
            None,
            mock_existing_user
        ]
        
        response = client.post('/loginout/register', data={
            'username': 'testuser',
            'email': 'existing@example.com',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        mock_render.assert_called_with('register.html')
    
    @patch('middleware.login_out.generate_password_hash')
    @patch('middleware.login_out.db')
    @patch('middleware.login_out.User')
    @patch('middleware.login_out.render_template')
    def test_register_database_error(self, mock_render, mock_user_class, mock_db, mock_hash, client):
        """データベースエラーが発生した場合のテスト"""
        mock_render.return_value = 'register page'
        mock_hash.return_value = 'hashed_password'
        mock_user_class.query.filter_by.return_value.first.return_value = None
        
        mock_user_instance = Mock()
        mock_user_class.return_value = mock_user_instance
        
        mock_db.session.commit.side_effect = Exception('Database error')
        
        response = client.post('/loginout/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        mock_db.session.rollback.assert_called_once()
        mock_render.assert_called_with('register.html')
