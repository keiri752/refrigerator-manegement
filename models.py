from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()



# モデル定義
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    ingredients = db.relationship('Ingredient', backref='user', lazy=True, cascade='all, delete-orphan')



# モデル（シンプル化）
class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    category = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# お気に入りレシピ
class FavoriteRecipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    img = db.Column(db.String(500), nullable=True)
    source = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ユーザーとのリレーション
    user = db.relationship('User', backref=db.backref('favorites', lazy=True))

# レシピ閲覧履歴
class RecipeHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    img = db.Column(db.String(500), nullable=True)
    source = db.Column(db.String(50), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ユーザーとのリレーション
    user = db.relationship('User', backref=db.backref('history', lazy=True))

class PushSubscription(db.Model):
    """プッシュ通知の購読情報を管理"""
    __tablename__ = 'push_subscription'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    endpoint = db.Column(db.String(500), nullable=False, unique=True)
    p256dh = db.Column(db.String(200), nullable=False)
    auth = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Userモデルとのリレーション
    user = db.relationship('User', backref=db.backref('push_subscriptions', lazy=True))
    
    def to_dict(self):
        """pywebpushで使用する形式に変換"""
        return {
            'endpoint': self.endpoint,
            'keys': {
                'p256dh': self.p256dh,
                'auth': self.auth
            }
        }
    
    def __repr__(self):
        return f'<PushSubscription {self.id} for User {self.user_id}>'