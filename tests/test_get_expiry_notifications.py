# ターミナルで「pytest -v」で起動
# pytest　テスト用フレームワーク
# fixtureの定義やassertを使ってのテスト用
import pytest
# timedelta 日付の加減算に使用
from datetime import date, timedelta
# patch　モック（仮のオブジェクト）を使って、テスト対象の外部依存（データベースなど）を使用しないようにする
from unittest.mock import patch


# functions.pyがある親フォルダを指定
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from functions import get_expiry_notifications





# --------------------------------------------------------
# モック用（テスト用の）の食材クラス
# 賞味期限（expiry_date）を持つ構造
class MockIngredient:
    def __init__(self, expiry_date):
        self.expiry_date = expiry_date




# --------------------------------------------------------
# 状態ごとに分割した fixture
# @pytest.fixture　テストの処理を関数として定義して、テスト関数に渡せる

# 消費期限が過ぎている（昨日）
@pytest.fixture
def is_expired_yesterday():
    return MockIngredient(date.today() - timedelta(days=1))

# 消費期限当日
@pytest.fixture
def is_expired_today():
    return MockIngredient(date.today()) 

# 消費期限、2日後
@pytest.fixture
def is_expiring_in_2_days():
    return MockIngredient(date.today() + timedelta(days=2))

# 消費期限、3日後
@pytest.fixture
def is_expiring_in_3_days():
    return MockIngredient(date.today() + timedelta(days=3))

# 消費期限、6日後
@pytest.fixture
def is_expiring_in_6_days():
    return MockIngredient(date.today() + timedelta(days=6))

# 消費期限、7日後
@pytest.fixture
def is_expiring_in_7_days():
    return MockIngredient(date.today() + timedelta(days=7))

# 消費期限、10日後
@pytest.fixture
def is_expiring_in_10_days():
    return MockIngredient(date.today() + timedelta(days=10))





# --------------------------------------------------------
"""
テストケース
functions.Ingredientをモック（テスト用）に置き換え。
functions.pyの中にはIngredientモデルは無くmodels.pyにそのモデルはありインポートして使っているが、
functions.pyでIngredientが使われている限り 「functions.Ingredient」のように呼び出せる
"""

# 下記の場合、「is_expired_yesterday」の単体でテストしたければほかの関数は不要
# 他の食材も複数ある中で正しいかテストする場合には下記の書き方でよい

@patch('functions.Ingredient')
# テスト関数。昨日の消費期限の食材が 「expired（消費期限切れ）」のリストに入るか確認
def test_is_expired_yesterday(
    MockIngredientModel,
    is_expired_yesterday,
):
    # 7パターンの消費期限の食材をリストとして返すように設定。
    # このリストをfunctions.pyの「get_expiry_notifications」を使って分類する
    MockIngredientModel.query.filter_by.return_value.all.return_value = [
        is_expired_yesterday,
    ]
    
    # テスト対象の関数を実行
    # user_id=1は仮のユーザーID
    result = get_expiry_notifications(user_id=1)

    # expired_ingresientが「expired」に正しく分類されるか検証。
    # 「expired」はfunctions.pyのget_expiry_notifications関数内の　expired=[]の空のリスト
    assert is_expired_yesterday in result['expired']
    assert is_expired_yesterday not in result['expiring_soon']
    assert is_expired_yesterday not in result['expiring_week']






@patch('functions.Ingredient')
# テスト関数。今日の消費期限の食材が 「expired_soon（3日以内に消費期限切れ）」のリストに入るか確認
def test_is_expired_today(
    MockIngredientModel, 
    is_expired_today,
):
    MockIngredientModel.query.filter_by.return_value.all.return_value = [
        is_expired_today,
    ]
    result = get_expiry_notifications(user_id=1)
    assert is_expired_today not in result['expired']
    assert is_expired_today in result['expiring_soon']
    assert is_expired_today not in result['expiring_week']





@patch('functions.Ingredient')
# テスト関数。2日後の消費期限の食材が 「expired_soon（3日以内に消費期限切れ）」のリストに入るか確認
def test_is_expiring_in_2_days(
    MockIngredientModel, 
    is_expiring_in_2_days,
):
    MockIngredientModel.query.filter_by.return_value.all.return_value = [
        is_expiring_in_2_days,
    ]
    result = get_expiry_notifications(user_id=1)
    assert is_expiring_in_2_days not in result['expired']
    assert is_expiring_in_2_days in result['expiring_soon']
    assert is_expiring_in_2_days not in result['expiring_week']







@patch('functions.Ingredient')
# テスト関数。3日後の消費期限の食材が 「expired_soon（3日以内に消費期限切れ）」のリストに入るか確認
def test_is_expiring_in_3_days(
    MockIngredientModel, 
    is_expiring_in_3_days,
):
    MockIngredientModel.query.filter_by.return_value.all.return_value = [
        is_expiring_in_3_days,
    ]
    result = get_expiry_notifications(user_id=1)
    assert is_expiring_in_3_days not in result['expired']
    assert is_expiring_in_3_days in result['expiring_soon']
    assert is_expiring_in_3_days not in result['expiring_week']





@patch('functions.Ingredient')
# テスト関数。6日後の消費期限の食材が 「expired_soon（7日以内に消費期限切れ）」のリストに入るか確認
def test_is_expiring_in_6_days(
    MockIngredientModel, 
    is_expiring_in_6_days,
):
    MockIngredientModel.query.filter_by.return_value.all.return_value = [
        is_expiring_in_6_days,
    ]
    result = get_expiry_notifications(user_id=1)
    assert is_expiring_in_6_days not in result['expired']
    assert is_expiring_in_6_days not in result['expiring_soon']
    assert is_expiring_in_6_days in result['expiring_week']





@patch('functions.Ingredient')
# テスト関数。7日後の消費期限の食材が 「expired_soon（7日以内に消費期限切れ）」のリストに入るか確認
def test_is_expiring_in_7_days(
    MockIngredientModel, 
    is_expiring_in_7_days,
):
    MockIngredientModel.query.filter_by.return_value.all.return_value = [
        is_expiring_in_7_days,
    ]
    result = get_expiry_notifications(user_id=1)
    assert is_expiring_in_7_days not in result['expired']
    assert is_expiring_in_7_days not in result['expiring_soon']
    assert is_expiring_in_7_days in result['expiring_week']





@patch('functions.Ingredient')
# テスト関数。10日後の消費期限の食材がどのリストにも入らないか確認
def test_is_expiring_in_10_days(
    MockIngredientModel, 
    is_expiring_in_10_days,
):
    MockIngredientModel.query.filter_by.return_value.all.return_value = [
        is_expiring_in_10_days,
    ]
    result = get_expiry_notifications(user_id=1)
    assert is_expiring_in_10_days not in result['expired']
    assert is_expiring_in_10_days not in result['expiring_soon']
    assert is_expiring_in_10_days not in result['expiring_week']