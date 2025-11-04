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


class TestLogout:
    
    def test_logout_with_logged_in_user(self, client):
        """ログイン済みユーザーがログアウトできること"""
        # セッションにユーザー情報を設定
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
            sess['login_time'] = '2024-01-01T00:00:00'
        
        # ログアウトリクエスト
        response = client.get('/loginout/logout', follow_redirects=False)
        
        # 検証
        assert response.status_code == 302
        assert '/loginout/login' in response.location
        
        # セッションがクリアされていることを確認
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
            assert 'username' not in sess
            assert 'login_time' not in sess
    
    def test_logout_without_logged_in_user(self, client):
        """ログインしていないユーザーもログアウトできること"""
        # セッションなしでログアウトリクエスト
        response = client.get('/loginout/logout', follow_redirects=False)
        
        # 検証
        assert response.status_code == 302
        assert '/loginout/login' in response.location
        
        # セッションが空であることを確認
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
            assert 'username' not in sess
    
    def test_logout_clears_all_session_data(self, client):
        """ログアウト時にすべてのセッションデータがクリアされること"""
        # 複数のセッションデータを設定
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
            sess['login_time'] = '2024-01-01T00:00:00'
            sess['extra_data'] = 'some_value'
        
        # ログアウトリクエスト
        response = client.get('/loginout/logout', follow_redirects=False)
        
        # すべてのセッションデータがクリアされていることを確認
        with client.session_transaction() as sess:
            # _flashesは残る可能性があるため、それ以外が空であることを確認
            session_keys = [key for key in sess.keys() if not key.startswith('_')]
            assert len(session_keys) == 0
    
    def test_logout_flash_message(self, client):
        """ログアウト時にフラッシュメッセージが表示されること"""
        # セッションにユーザー情報を設定
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        # ログアウトリクエスト（follow_redirects=Falseに変更）
        response = client.get('/loginout/logout', follow_redirects=False)
        
        # リダイレクトが成功していることを確認
        assert response.status_code == 302
        
        # フラッシュメッセージがセッションに追加されていることを確認
        with client.session_transaction() as sess:
            flashes = sess.get('_flashes', [])
            # フラッシュメッセージが存在するか確認
            flash_messages = [message for category, message in flashes]
            assert 'ログアウトしました' in flash_messages
    
    def test_logout_redirects_to_login(self, client):
        """ログアウト後にログインページにリダイレクトされること"""
        # セッションにユーザー情報を設定
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        # ログアウトリクエスト
        response = client.get('/loginout/logout', follow_redirects=False)
        
        # リダイレクト先がloginであることを確認
        assert response.status_code == 302
        assert response.location.endswith('/loginout/login')
    
    def test_logout_handles_missing_username(self, client):
        """usernameがセッションにない場合でもログアウトできること"""
        # user_idのみ設定（usernameなし）
        with client.session_transaction() as sess:
            sess['user_id'] = 1
        
        # ログアウトリクエスト（エラーが発生しないことを確認）
        response = client.get('/loginout/logout', follow_redirects=False)
        
        assert response.status_code == 302
        assert '/loginout/login' in response.location
    
    def test_logout_handles_missing_user_id(self, client):
        """user_idがセッションにない場合でもログアウトできること"""
        # usernameのみ設定（user_idなし）
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        # ログアウトリクエスト（エラーが発生しないことを確認）
        response = client.get('/loginout/logout', follow_redirects=False)
        
        assert response.status_code == 302
        assert '/loginout/login' in response.location
    
    def test_logout_multiple_times(self, client):
        """連続してログアウトしてもエラーが発生しないこと"""
        # 1回目のログアウト
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        response1 = client.get('/loginout/logout', follow_redirects=False)
        assert response1.status_code == 302
        
        # 2回目のログアウト（セッションが空の状態）
        response2 = client.get('/loginout/logout', follow_redirects=False)
        assert response2.status_code == 302
        assert '/loginout/login' in response2.location