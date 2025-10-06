// プッシュ通知管理クラス
class PushNotificationManager {
    constructor() {
        this.isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
        this.registration = null;
        this.subscription = null;
    }

    async init() {
        if (!this.isSupported) {
            console.warn('Push notifications not supported');
            return false;
        }

        try {
            // Service Worker登録を取得
            this.registration = await navigator.serviceWorker.ready;
            
            // 既存の購読を確認
            this.subscription = await this.registration.pushManager.getSubscription();
            
            // UIを更新
            this.updateUI();
            
            return true;
        } catch (error) {
            console.error('Push notification init failed:', error);
            return false;
        }
    }

    async requestPermission() {
        if (!this.isSupported) {
            alert('お使いのブラウザはプッシュ通知に対応していません');
            return false;
        }

        try {
            const permission = await Notification.requestPermission();
            
            if (permission === 'granted') {
                console.log('✅ Notification permission granted');
                await this.subscribe();
                return true;
            } else {
                console.log('❌ Notification permission denied');
                alert('プッシュ通知が拒否されました。ブラウザの設定から変更できます。');
                return false;
            }
        } catch (error) {
            console.error('Permission request failed:', error);
            return false;
        }
    }

    async subscribe() {
        try {
            // VAPID公開鍵を取得
            const response = await fetch('/api/push/vapid-public-key');
            const { publicKey } = await response.json();

            // プッシュ購読
            const subscription = await this.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(publicKey)
            });

            // サーバーに送信
            const subscribeResponse = await fetch('/api/push/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(subscription.toJSON())
            });

            if (subscribeResponse.ok) {
                this.subscription = subscription;
                this.updateUI();
                console.log('✅ Push subscription successful');
                return true;
            } else {
                throw new Error('Server subscription failed');
            }
        } catch (error) {
            console.error('Push subscription failed:', error);
            alert('プッシュ通知の登録に失敗しました');
            return false;
        }
    }

    async unsubscribe() {
        if (!this.subscription) {
            return true;
        }

        try {
            // サーバーから削除
            await fetch('/api/push/unsubscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.subscription.toJSON())
            });

            // ブラウザから削除
            await this.subscription.unsubscribe();
            this.subscription = null;
            
            this.updateUI();
            console.log('✅ Push unsubscription successful');
            return true;
        } catch (error) {
            console.error('Push unsubscription failed:', error);
            return false;
        }
    }

    async sendTestNotification() {
        try {
            const response = await fetch('/api/push/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
                console.log('✅ Test notification sent');
                return true;
            } else {
                throw new Error('Test notification failed');
            }
        } catch (error) {
            console.error('Test notification failed:', error);
            alert('テスト通知の送信に失敗しました');
            return false;
        }
    }

    updateUI() {
        const button = document.getElementById('pushNotificationToggle');
        const status = document.getElementById('pushNotificationStatus');
        const testBtn = document.getElementById('testNotificationBtn');
        
        if (button) {
            if (this.subscription) {
                button.textContent = '🔔 通知をオフにする';
                button.classList.remove('btn-primary');
                button.classList.add('btn-secondary');
            } else {
                button.textContent = '🔔 通知を許可する';
                button.classList.remove('btn-secondary');
                button.classList.add('btn-primary');
            }
        }

        if (status) {
            status.textContent = this.subscription ? '有効' : '無効';
            status.className = this.subscription ? 'badge bg-success' : 'badge bg-secondary';
        }

        if (testBtn) {
            testBtn.style.display = this.subscription ? 'block' : 'none';
        }
    }

    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }
}

// グローバルインスタンス
const pushManager = new PushNotificationManager();

// 初期化
document.addEventListener('DOMContentLoaded', async () => {
    await pushManager.init();
});