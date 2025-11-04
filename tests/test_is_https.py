import pytest
import os
from unittest.mock import patch

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from functions import is_https_environment


def is_https_environment():
    if os.environ.get('HTTPS') == 'on':
        return True
    if os.environ.get('HTTP_X_FORWARDED_PROTO') == 'https':
        return True
    if os.environ.get('HTTP_X_FORWARDED_SSL') == 'on':
        return True
    return False


class TestIsHttpsEnvironment:
    
    def test_https_on(self):
        """HTTPS環境変数が'on'の場合、Trueを返すこと"""
        with patch.dict(os.environ, {'HTTPS': 'on'}, clear=True):
            assert is_https_environment() is True
    
    def test_http_x_forwarded_proto_https(self):
        """HTTP_X_FORWARDED_PROTOが'https'の場合、Trueを返すこと"""
        with patch.dict(os.environ, {'HTTP_X_FORWARDED_PROTO': 'https'}, clear=True):
            assert is_https_environment() is True
    
    def test_http_x_forwarded_ssl_on(self):
        """HTTP_X_FORWARDED_SSLが'on'の場合、Trueを返すこと"""
        with patch.dict(os.environ, {'HTTP_X_FORWARDED_SSL': 'on'}, clear=True):
            assert is_https_environment() is True
    
    def test_no_https_environment(self):
        """HTTPS関連の環境変数がない場合、Falseを返すこと"""
        with patch.dict(os.environ, {}, clear=True):
            assert is_https_environment() is False
    
    def test_https_off(self):
        """HTTPSが'off'の場合、Falseを返すこと"""
        with patch.dict(os.environ, {'HTTPS': 'off'}, clear=True):
            assert is_https_environment() is False
    
    def test_http_x_forwarded_proto_http(self):
        """HTTP_X_FORWARDED_PROTOが'http'の場合、Falseを返すこと"""
        with patch.dict(os.environ, {'HTTP_X_FORWARDED_PROTO': 'http'}, clear=True):
            assert is_https_environment() is False
    
    def test_http_x_forwarded_ssl_off(self):
        """HTTP_X_FORWARDED_SSLが'off'の場合、Falseを返すこと"""
        with patch.dict(os.environ, {'HTTP_X_FORWARDED_SSL': 'off'}, clear=True):
            assert is_https_environment() is False
    
    def test_multiple_https_indicators(self):
        """複数のHTTPS指標が設定されている場合、Trueを返すこと"""
        with patch.dict(os.environ, {
            'HTTPS': 'on',
            'HTTP_X_FORWARDED_PROTO': 'https',
            'HTTP_X_FORWARDED_SSL': 'on'
        }, clear=True):
            assert is_https_environment() is True
    
    def test_mixed_https_indicators(self):
        """一つでもHTTPS指標があればTrueを返すこと（混在パターン）"""
        with patch.dict(os.environ, {
            'HTTPS': 'off',
            'HTTP_X_FORWARDED_PROTO': 'https',  # これだけTrue
            'HTTP_X_FORWARDED_SSL': 'off'
        }, clear=True):
            assert is_https_environment() is True
    
    def test_empty_string_values(self):
        """環境変数が空文字列の場合、Falseを返すこと"""
        with patch.dict(os.environ, {
            'HTTPS': '',
            'HTTP_X_FORWARDED_PROTO': '',
            'HTTP_X_FORWARDED_SSL': ''
        }, clear=True):
            assert is_https_environment() is False
    
    def test_case_sensitive_https(self):
        """HTTPSの値が大文字の'ON'の場合、Falseを返すこと（大文字小文字を区別）"""
        with patch.dict(os.environ, {'HTTPS': 'ON'}, clear=True):
            assert is_https_environment() is False
    
    def test_case_sensitive_proto(self):
        """HTTP_X_FORWARDED_PROTOの値が大文字の'HTTPS'の場合、Falseを返すこと"""
        with patch.dict(os.environ, {'HTTP_X_FORWARDED_PROTO': 'HTTPS'}, clear=True):
            assert is_https_environment() is False
    
    def test_priority_https_first(self):
        """HTTPS='on'が最初にチェックされ、Trueを返すこと"""
        with patch.dict(os.environ, {
            'HTTPS': 'on',
            'HTTP_X_FORWARDED_PROTO': 'http',
            'HTTP_X_FORWARDED_SSL': 'off'
        }, clear=True):
            assert is_https_environment() is True


