import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from functions import get_favorite_urls, FavoriteRecipe


@patch('functions.FavoriteRecipe')  # パッチ対象のパスを明確に
def test_get_favorite_urls(mock_favorite_recipe):  # selfを削除
    # データベースなし、高速、簡単
    fav = Mock()
    fav.url = 'https://example.com/recipe'
    
    mock_query = Mock()
    mock_query.filter_by.return_value.all.return_value = [fav]
    mock_favorite_recipe.query = mock_query
    
    result = get_favorite_urls(user_id=1)
    assert result == ['https://example.com/recipe']