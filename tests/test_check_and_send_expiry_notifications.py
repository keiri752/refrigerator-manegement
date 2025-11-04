import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import date, timedelta
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestCheckAndSendExpiryNotifications:
    
    @patch('models.User')  # functions.UserではなくmodelsユーザーをパッチModels
    @patch('functions.get_expiry_notifications')
    @patch('functions.send_push_notification')
    def test_send_notification_for_expired_ingredients(self, mock_send_push, mock_get_expiry, mock_user):
        """期限切れ食材がある場合に通知が送信されること"""
        from functions import check_and_send_expiry_notifications
        
        # モックユーザーの設定
        user1 = Mock()
        user1.id = 1
        mock_user.query.all.return_value = [user1]
        
        # 期限切れ食材のモック
        expired_ing1 = Mock()
        expired_ing1.name = 'トマト'
        expired_ing2 = Mock()
        expired_ing2.name = 'レタス'
        
        mock_get_expiry.return_value = {
            'expired': [expired_ing1, expired_ing2],
            'expiring_soon': [],
            'expiring_week': []
        }
        
        # 実行
        result = check_and_send_expiry_notifications()
        
        # 検証
        assert result == True
        mock_send_push.assert_called_once_with(
            1,
            '⚠️ 賞味期限切れの食材があります',
            'トマト, レタス2個の食材が期限切れです',
            url='/refrigerator'
        )
    
    @patch('models.User')
    @patch('functions.get_expiry_notifications')
    @patch('functions.send_push_notification')
    def test_send_notification_for_expiring_soon_ingredients(self, mock_send_push, mock_get_expiry, mock_user):
        """3日以内に期限切れになる食材がある場合に通知が送信されること"""
        from functions import check_and_send_expiry_notifications
        
        # モックユーザーの設定
        user1 = Mock()
        user1.id = 1
        mock_user.query.all.return_value = [user1]
        
        # 期限間近食材のモック
        expiring_ing1 = Mock()
        expiring_ing1.name = '牛乳'
        expiring_ing2 = Mock()
        expiring_ing2.name = 'ヨーグルト'
        
        mock_get_expiry.return_value = {
            'expired': [],
            'expiring_soon': [expiring_ing1, expiring_ing2],
            'expiring_week': []
        }
        
        # 実行
        result = check_and_send_expiry_notifications()
        
        # 検証
        assert result == True
        mock_send_push.assert_called_once_with(
            1,
            '⏰ 賞味期限が近づいています',
            '牛乳, ヨーグルト2個の食材が3日以内に期限切れになります',
            url='/search'
        )
    
    @patch('models.User')
    @patch('functions.get_expiry_notifications')
    @patch('functions.send_push_notification')
    def test_no_notification_when_no_expired_ingredients(self, mock_send_push, mock_get_expiry, mock_user):
        """期限切れ・期限間近な食材がない場合は通知を送信しないこと"""
        from functions import check_and_send_expiry_notifications
        
        # モックユーザーの設定
        user1 = Mock()
        user1.id = 1
        mock_user.query.all.return_value = [user1]
        
        mock_get_expiry.return_value = {
            'expired': [],
            'expiring_soon': [],
            'expiring_week': []
        }
        
        # 実行
        result = check_and_send_expiry_notifications()
        
        # 検証
        assert result == True
        mock_send_push.assert_not_called()
    
    @patch('models.User')
    @patch('functions.get_expiry_notifications')
    @patch('functions.send_push_notification')
    def test_expired_takes_priority_over_expiring_soon(self, mock_send_push, mock_get_expiry, mock_user):
        """期限切れと期限間近の両方がある場合、期限切れの通知のみ送信されること"""
        from functions import check_and_send_expiry_notifications
        
        # モックユーザーの設定
        user1 = Mock()
        user1.id = 1
        mock_user.query.all.return_value = [user1]
        
        # 期限切れと期限間近の両方を設定
        expired_ing = Mock()
        expired_ing.name = 'トマト'
        expiring_ing = Mock()
        expiring_ing.name = '牛乳'
        
        mock_get_expiry.return_value = {
            'expired': [expired_ing],
            'expiring_soon': [expiring_ing],
            'expiring_week': []
        }
        
        # 実行
        result = check_and_send_expiry_notifications()
        
        # 検証 - 期限切れの通知のみ送信される（elifのため）
        assert result == True
        mock_send_push.assert_called_once()
        call_args = mock_send_push.call_args
        assert '期限切れ' in call_args[0][1]
    
    @patch('models.User')
    @patch('functions.get_expiry_notifications')
    @patch('functions.send_push_notification')
    def test_handle_multiple_users(self, mock_send_push, mock_get_expiry, mock_user):
        """複数ユーザーの通知を処理できること"""
        from functions import check_and_send_expiry_notifications
        
        # 複数ユーザーの設定
        user1 = Mock()
        user1.id = 1
        user2 = Mock()
        user2.id = 2
        mock_user.query.all.return_value = [user1, user2]
        
        # 各ユーザーで異なる食材を設定
        expired_ing1 = Mock()
        expired_ing1.name = 'トマト'
        expired_ing2 = Mock()
        expired_ing2.name = 'レタス'
        
        def get_expiry_side_effect(user_id):
            if user_id == 1:
                return {'expired': [expired_ing1], 'expiring_soon': [], 'expiring_week': []}
            else:
                return {'expired': [expired_ing2], 'expiring_soon': [], 'expiring_week': []}
        
        mock_get_expiry.side_effect = get_expiry_side_effect
        
        # 実行
        result = check_and_send_expiry_notifications()
        
        # 検証
        assert result == True
        assert mock_send_push.call_count == 2
        
        # 各ユーザーへの呼び出しを確認
        calls = mock_send_push.call_args_list
        assert calls[0][0][0] == 1  # user1
        assert calls[1][0][0] == 2  # user2
    
    @patch('models.User')
    @patch('functions.get_expiry_notifications')
    @patch('functions.send_push_notification')
    def test_limit_ingredient_names_to_three(self, mock_send_push, mock_get_expiry, mock_user):
        """食材名が3個以上の場合は最初の3個だけ表示されること"""
        from functions import check_and_send_expiry_notifications
        
        # モックユーザーの設定
        user1 = Mock()
        user1.id = 1
        mock_user.query.all.return_value = [user1]
        
        # 4個の期限切れ食材
        expired_ings = []
        for i, name in enumerate(['トマト', 'レタス', '牛乳', 'ヨーグルト'], 1):
            ing = Mock()
            ing.name = name
            expired_ings.append(ing)
        
        mock_get_expiry.return_value = {
            'expired': expired_ings,
            'expiring_soon': [],
            'expiring_week': []
        }
        
        # 実行
        result = check_and_send_expiry_notifications()
        
        # 検証
        assert result == True
        call_args = mock_send_push.call_args
        message = call_args[0][2]
        assert 'トマト, レタス, 牛乳' in message
        assert 'など4個' in message
    
    @patch('models.User')
    @patch('functions.get_expiry_notifications')
    @patch('functions.send_push_notification')
    def test_return_false_on_exception(self, mock_send_push, mock_get_expiry, mock_user):
        """例外が発生した場合にFalseを返すこと"""
        from functions import check_and_send_expiry_notifications
        
        # 例外を発生させる
        mock_user.query.all.side_effect = Exception('Database error')
        
        # 実行
        result = check_and_send_expiry_notifications()
        
        # 検証
        assert result == False
        mock_send_push.assert_not_called()
    
    @patch('models.User')
    @patch('functions.get_expiry_notifications')
    @patch('functions.send_push_notification')
    def test_return_true_when_no_users(self, mock_send_push, mock_get_expiry, mock_user):
        """ユーザーが存在しない場合でもTrueを返すこと"""
        from functions import check_and_send_expiry_notifications
        
        # ユーザーなし
        mock_user.query.all.return_value = []
        
        # 実行
        result = check_and_send_expiry_notifications()
        
        # 検証
        assert result == True
        mock_get_expiry.assert_not_called()
        mock_send_push.assert_not_called()