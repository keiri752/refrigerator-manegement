from flask import Blueprint, request, jsonify, session
from models import db, PushSubscription
from functools import wraps

push_bp = Blueprint('push', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@push_bp.route('/api/push/subscribe', methods=['POST'])
@login_required
def subscribe_push():
    """プッシュ通知の購読登録"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        # 既存の購読を確認
        existing = PushSubscription.query.filter_by(
            user_id=user_id,
            endpoint=data['endpoint']
        ).first()
        
        if existing:
            # 更新
            existing.p256dh = data['keys']['p256dh']
            existing.auth = data['keys']['auth']
        else:
            # 新規作成
            subscription = PushSubscription(
                user_id=user_id,
                endpoint=data['endpoint'],
                p256dh=data['keys']['p256dh'],
                auth=data['keys']['auth']
            )
            db.session.add(subscription)
        
        db.session.commit()
        print(f"[PUSH] User {user_id} subscribed successfully")
        
        return jsonify({'success': True, 'message': 'プッシュ通知を有効にしました'})
        
    except Exception as e:
        print(f"[PUSH ERROR] subscribe failed: {e}")
        return jsonify({'error': str(e)}), 500

@push_bp.route('/api/push/unsubscribe', methods=['POST'])
@login_required
def unsubscribe_push():
    """プッシュ通知の購読解除"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        subscription = PushSubscription.query.filter_by(
            user_id=user_id,
            endpoint=data['endpoint']
        ).first()
        
        if subscription:
            db.session.delete(subscription)
            db.session.commit()
            print(f"[PUSH] User {user_id} unsubscribed")
        
        return jsonify({'success': True, 'message': 'プッシュ通知を無効にしました'})
        
    except Exception as e:
        print(f"[PUSH ERROR] unsubscribe failed: {e}")
        return jsonify({'error': str(e)}), 500

@push_bp.route('/api/push/test', methods=['POST'])
@login_required
def test_push():
    """テスト通知を送信"""
    try:
        from functions import send_push_notification
        user_id = session.get('user_id')
        
        success = send_push_notification(
            user_id,
            '🔔 テスト通知',
            'プッシュ通知が正常に動作しています！',
            url='/'
        )
        
        if success:
            return jsonify({'success': True, 'message': 'テスト通知を送信しました'})
        else:
            return jsonify({'error': '通知の送信に失敗しました'}), 500
            
    except Exception as e:
        print(f"[PUSH ERROR] test failed: {e}")
        return jsonify({'error': str(e)}), 500

@push_bp.route('/api/push/vapid-public-key', methods=['GET'])
def get_vapid_public_key():
    """VAPID公開鍵を取得（認証不要）"""
    from flask import current_app
    return jsonify({
        'publicKey': current_app.config['VAPID_PUBLIC_KEY']
    })