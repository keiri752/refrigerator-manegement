# app.pyから移動
import sys
import os
from functions import is_https_environment
from datetime import timedelta


"""
getattr(get attribute)：属性を取得


構文 getattr(object, attribute_name, default_value)
    attribute：属性を取得する対象のオブジェクト
    attirbute_name：取得したい属性の名前（frozenとすると、exe化されているかを判定できる）
    default_value：指定した値が無い場合に返される値
"""
if getattr(sys, 'frozen', False):
    # exe化された場合
    # sys.excutable で今動いているexeファイルのパスを取得
    base_dir = os.path.dirname(sys.executable)
else:
    # 通常のpythonで実行された場合
    base_dir = os.path.abspath(os.path.dirname(__file__))


# instanceフォルダの場所
instance_dir = os.path.join(base_dir, 'instance')


"""
instanceフォルダが無ければ作成、すでにあれば何もしない
os.makedirs：フォルダを作成する
instance_dir：「instance」の部分はフォルダ名、「_dir」の部分はこれはフォルダだと明示している
exist_ok=True：既にフォルダがあれば何もしない、通常は「True」を使用する
"""


os.makedirs(instance_dir, exist_ok=True)


db_path = os.path.join(instance_dir, 'ingredients.db')



IS_HTTPS = is_https_environment()
FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'False').lower() == 'true'

class Config():
    SQLALCHEMY_DATABASE_URI= f'sqlite:///{db_path}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # セッション設定
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-very-secure-secret-key-change-this-in-production')
    SESSION_COOKIE_SECURE = IS_HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)