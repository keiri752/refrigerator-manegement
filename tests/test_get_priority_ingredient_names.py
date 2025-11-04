# ターミナルで「pytest -v」で起動
# pytest　テスト用フレームワーク
# fixtureの定義やassertを使ってのテスト用
import pytest
# timedelta 日付の加減算に使用
from datetime import date, timedelta
# patch　モック（仮のオブジェクト）を使って、テスト対象の外部依存（データベースなど）を使用しないようにする
from unittest.mock import Mock, patch


# functions.pyがある親フォルダを指定
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from functions import get_expiry_notifications
from functions import get_priority_ingredient_names  # モジュール名を適宜変更してください


class TestGetPriorityIngredientNames:
    """get_priority_ingredient_names関数のテストクラス"""
    
    @patch('functions.get_expiry_notifications')
    def test_expired_and_expiring_soon_ingredients(self, mock_get_notifications):
        """期限切れと期限間近の食材が正しく取得できるケース"""
        # モックの食材オブジェクトを作成
        ing1 = Mock()
        ing1.name = 'トマト'
        ing2 = Mock()
        ing2.name = 'レタス'
        ing3 = Mock()
        ing3.name = '牛乳'
        
        mock_get_notifications.return_value = {
            'expired': [ing1, ing2],
            'expiring_soon': [ing3]
        }
        
        result = get_priority_ingredient_names(user_id=1)
        
        assert len(result) == 3
        assert 'トマト' in result
        assert 'レタス' in result
        assert '牛乳' in result
        mock_get_notifications.assert_called_once_with(1)
    
    @patch('functions.get_expiry_notifications')
    def test_only_expired_ingredients(self, mock_get_notifications):
        """期限切れ食材のみのケース"""
        ing1 = Mock()
        ing1.name = '卵'
        ing2 = Mock()
        ing2.name = 'バター'
        
        mock_get_notifications.return_value = {
            'expired': [ing1, ing2],
            'expiring_soon': []
        }
        
        result = get_priority_ingredient_names(user_id=2)
        
        assert len(result) == 2
        assert '卵' in result
        assert 'バター' in result
    
    @patch('functions.get_expiry_notifications')
    def test_only_expiring_soon_ingredients(self, mock_get_notifications):
        """期限間近の食材のみのケース"""
        ing1 = Mock()
        ing1.name = 'チーズ'
        
        mock_get_notifications.return_value = {
            'expired': [],
            'expiring_soon': [ing1]
        }
        
        result = get_priority_ingredient_names(user_id=3)
        
        assert len(result) == 1
        assert 'チーズ' in result
    
    @patch('functions.get_expiry_notifications')
    def test_no_ingredients(self, mock_get_notifications):
        """食材がないケース"""
        mock_get_notifications.return_value = {
            'expired': [],
            'expiring_soon': []
        }
        
        result = get_priority_ingredient_names(user_id=4)
        
        assert len(result) == 0
        assert result == []
    
    @patch('functions.get_expiry_notifications')
    def test_duplicate_ingredient_names(self, mock_get_notifications):
        """重複する食材名がある場合、重複が除去されるケース"""
        ing1 = Mock()
        ing1.name = 'りんご'
        ing2 = Mock()
        ing2.name = 'りんご'  # 同じ名前
        ing3 = Mock()
        ing3.name = 'バナナ'
        
        mock_get_notifications.return_value = {
            'expired': [ing1, ing2],
            'expiring_soon': [ing3]
        }
        
        result = get_priority_ingredient_names(user_id=5)
        
        assert len(result) == 2  # 重複が除去されている
        assert 'りんご' in result
        assert 'バナナ' in result
    
    @patch('functions.get_expiry_notifications')
    def test_limit_to_five_ingredients(self, mock_get_notifications):
        """6個以上の食材がある場合、最初の5個から重複除去して返すケース"""
        # 7個の異なる食材を作成
        ingredients = []
        for i in range(7):
            ing = Mock()
            ing.name = f'食材{i}'
            ingredients.append(ing)
        
        mock_get_notifications.return_value = {
            'expired': ingredients[:4],
            'expiring_soon': ingredients[4:]
        }
        
        result = get_priority_ingredient_names(user_id=6)
        
        # 最初の5個のみが処理される（重複がなければ5個）
        assert len(result) <= 5
        # 食材0-4が含まれているはず
        expected_names = [f'食材{i}' for i in range(5)]
        for name in result:
            assert name in expected_names
    
    @patch('functions.get_expiry_notifications')
    def test_limit_with_duplicates(self, mock_get_notifications):
        """5個制限で重複がある場合"""
        # 最初の5個に重複を含む
        ing1 = Mock()
        ing1.name = 'A'
        ing2 = Mock()
        ing2.name = 'A'  # 重複
        ing3 = Mock()
        ing3.name = 'B'
        ing4 = Mock()
        ing4.name = 'C'
        ing5 = Mock()
        ing5.name = 'D'
        ing6 = Mock()
        ing6.name = 'E'  # 6個目は処理されない
        
        mock_get_notifications.return_value = {
            'expired': [ing1, ing2, ing3],
            'expiring_soon': [ing4, ing5, ing6]
        }
        
        result = get_priority_ingredient_names(user_id=7)
        
        # 最初の5個: A, A, B, C, D → 重複除去: A, B, C, D
        assert len(result) == 4
        assert 'A' in result
        assert 'B' in result
        assert 'C' in result
        assert 'D' in result
        assert 'E' not in result  # 6個目は含まれない
    
    @patch('functions.get_expiry_notifications')
    def test_return_type_is_list(self, mock_get_notifications):
        """戻り値がリスト型であることを確認"""
        ing1 = Mock()
        ing1.name = 'テスト食材'
        
        mock_get_notifications.return_value = {
            'expired': [ing1],
            'expiring_soon': []
        }
        
        result = get_priority_ingredient_names(user_id=8)
        
        assert isinstance(result, list)