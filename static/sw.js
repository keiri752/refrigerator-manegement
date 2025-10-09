const CACHE_NAME = 'recipe-app-multipage-v3'; // バージョンアップ
const STATIC_CACHE = 'static-multipage-v3';
const DYNAMIC_CACHE = 'dynamic-multipage-v3';

// 静的リソースのみキャッシュ（ユーザーデータを含むページは除外）
const urlsToCache = [
  '/static/style.css',
  '/static/icon-192x192.png',
  '/pwa/manifest.json',  // ← manifestはpwa配下のまま
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'
];

// ユーザー固有データを含むため、絶対にキャッシュしないパス
// /search を削除して、静的な検索ページはキャッシュ可能にする
const excludeFromCache = [
  '/', // ダッシュボード（通知データを含む）
  '/refrigerator', // 食材一覧
  '/add', // 食材追加
  '/add_ingredient',
  '/delete_ingredient',
  '/change_quantity',
  '/debug',
  '/health',
  '/logout'
];

// POST リクエストや動的データのパスは除外
const dynamicDataPaths = [
  '/search' // POST時のレシピ検索結果は動的
];

// インストール時にキャッシュを作成
self.addEventListener('install', function(event) {
  console.log('🔧 Service Worker (Multi-page v2): Installing...');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(function(cache) {
        console.log('📦 Service Worker: Caching static assets (multi-page version v2)');
        return cache.addAll(urlsToCache);
      })
      .then(function() {
        console.log('✅ Service Worker (Multi-page v2): Installation complete');
        return self.skipWaiting();
      })
      .catch(function(error) {
        console.error('❌ Service Worker: Installation failed', error);
      })
  );
});

// アクティベーション時に古いキャッシュを削除
self.addEventListener('activate', function(event) {
  console.log('🔄 Service Worker (Multi-page v2): Activating...');
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          // 古いバージョンのキャッシュを削除
          if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
            console.log('🗑️ Service Worker: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
    .then(function() {
      console.log('✅ Service Worker (Multi-page v2): Activation complete');
      return self.clients.claim();
    })
  );
});

// フェッチイベントの処理
self.addEventListener('fetch', function(event) {
  const requestUrl = new URL(event.request.url);
  
  // POST リクエストの場合は常にネットワークから取得（検索結果等）
  if (event.request.method !== 'GET') {
    console.log('📤 Service Worker: Bypassing cache for POST request:', requestUrl.pathname);
    event.respondWith(fetch(event.request));
    return;
  }
  
  // ユーザー固有データを含むパスはキャッシュしない
  const shouldExcludeFromCache = excludeFromCache.some(path => 
    requestUrl.pathname === path || requestUrl.pathname.startsWith(path + '/')
  );
  
  if (shouldExcludeFromCache) {
    console.log('🚫 Service Worker: Bypassing cache for user data:', requestUrl.pathname);
    event.respondWith(
      fetch(event.request)
        .then(function(response) {
          if (response.headers.get('X-No-Cache')) {
            console.log('✅ Service Worker: Server confirmed no-cache for user data');
          }
          return response;
        })
        .catch(function(error) {
          console.log('📡 Service Worker: Network failed for user data, serving offline message');
          return handleOfflineResponse(event.request);
        })
    );
    return;
  }
  
  // 検索ページ（GET）は条件付きでキャッシュ
  if (requestUrl.pathname === '/search' && event.request.method === 'GET') {
    console.log('🔍 Service Worker: Handling search page (GET)');
    event.respondWith(
      fetch(event.request)
        .then(function(response) {
          // 成功時はキャッシュして返す
          if (response && response.status === 200) {
            const responseToCache = response.clone();
            caches.open(DYNAMIC_CACHE).then(function(cache) {
              console.log('📦 Service Worker: Caching search page');
              cache.put(event.request, responseToCache);
            });
          }
          return response;
        })
        .catch(function(error) {
          // ネットワーク失敗時はキャッシュから取得
          console.log('📡 Service Worker: Network failed for search page, trying cache');
          return caches.match(event.request).then(function(cachedResponse) {
            return cachedResponse || handleOfflineResponse(event.request);
          });
        })
    );
    return;
  }
  
  // 静的リソースのキャッシュ戦略
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        if (response) {
          console.log('💾 Service Worker: Serving from cache:', event.request.url);
          return response;
        }
        
        console.log('🌐 Service Worker: Fetching from network:', event.request.url);
        return fetch(event.request).then(function(response) {
          if (!response || response.status !== 200) {
            return response;
          }

          if (response.type !== 'basic' && response.type !== 'cors') {
            return response;
          }

          // 静的リソースのみキャッシュ
          if (shouldCacheResource(event.request)) {
            const responseToCache = response.clone();
            caches.open(DYNAMIC_CACHE)
              .then(function(cache) {
                console.log('📦 Service Worker: Caching new resource:', event.request.url);
                cache.put(event.request, responseToCache);
              })
              .catch(function(error) {
                console.log('⚠️ Service Worker: Cache put failed:', error);
              });
          }

          return response;
        })
        .catch(function(error) {
          console.error('❌ Service Worker: Fetch failed:', error);
          return handleOfflineResponse(event.request);
        });
      })
  );
});

// オフライン時の応答を処理
function handleOfflineResponse(request) {
  if (request.mode === 'navigate') {
    return caches.match('/login').then(function(response) {
      if (response) return response;
      
      return new Response(`
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>オフライン - レシピ検索アプリ</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                       text-align: center; padding: 40px 20px; background: #f8f9fa; }
                .offline-message { background: white; padding: 40px; border-radius: 12px; 
                                 box-shadow: 0 2px 15px rgba(0,0,0,0.1); max-width: 400px; margin: 0 auto; }
                .offline-icon { font-size: 3rem; margin-bottom: 20px; }
                h1 { color: #495057; margin-bottom: 15px; }
                p { color: #6c757d; margin-bottom: 20px; }
                .btn { background: #007bff; color: white; padding: 10px 20px; 
                       border: none; border-radius: 6px; text-decoration: none; display: inline-block; }
            </style>
        </head>
        <body>
            <div class="offline-message">
                <div class="offline-icon">📡</div>
                <h1>オフラインです</h1>
                <p>インターネット接続を確認してください。<br>接続が復旧したら自動的に更新されます。</p>
                <button class="btn" onclick="location.reload()">再試行</button>
            </div>
        </body>
        </html>
      `, {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'text/html; charset=utf-8' }
      });
    });
  }
  
  return new Response('オフラインです', {
    status: 503,
    statusText: 'Service Unavailable'
  });
}

// リソースをキャッシュすべきかどうかを判定
function shouldCacheResource(request) {
  const url = new URL(request.url);
  
  // GETリクエストのみキャッシュ
  if (request.method !== 'GET') {
    return false;
  }
  
  // 静的リソース（CSS, JS, 画像）はキャッシュ
  const staticExtensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf'];
  const pathname = url.pathname.toLowerCase();
  
  if (staticExtensions.some(ext => pathname.endsWith(ext))) {
    return true;
  }
  
  // CDNリソースはキャッシュ
  if (url.hostname === 'cdn.jsdelivr.net' || url.hostname === 'fonts.googleapis.com') {
    return true;
  }
  
  // manifest.jsonもキャッシュ
  if (pathname.endsWith('/manifest.json')) {
    return true;
  }
  
  return false;
}

// 残りのイベントリスナーは元のコードと同じ
self.addEventListener('message', function(event) {
  console.log('📨 Service Worker: Message received:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    console.log('⏭️ Service Worker: Skip waiting requested');
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({version: CACHE_NAME, type: 'multipage-v2'});
  }
  
  if (event.data && event.data.type === 'CLEAR_USER_CACHE') {
    console.log('🧹 Service Worker: Clearing user-specific caches');
    caches.keys().then(function(cacheNames) {
      cacheNames.forEach(function(cacheName) {
        if (cacheName.includes('user-') || cacheName.includes('recipe-app-v')) {
          caches.delete(cacheName);
          console.log('🗑️ Service Worker: Deleted user cache:', cacheName);
        }
      });
    });
  }
});

console.log('🚀 Service Worker (Multi-page v2): Script loaded successfully');
console.log('📋 User data cache prevention: ENABLED');
console.log('🔍 Search page caching: CONDITIONAL (GET only)');
console.log('📱 Multi-page navigation support: ENABLED');
// レシピお気に入り機能追加予定


// ==============================================
// プッシュ通知機能
// ==============================================

// プッシュ通知受信
self.addEventListener('push', function(event) {
  console.log('📬 Push notification received:', event);
  
  let data = {
    title: 'レシピ検索アプリ',
    body: '新しい通知があります',
    icon: '/static/icon-192x192.png',
    badge: '/static/icon-192x192.png',
    url: '/'
  };
  
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      console.error('Failed to parse push data:', e);
    }
  }
  
  const options = {
    body: data.body,
    icon: data.icon,
    badge: data.badge,
    data: {
      url: data.url,
      timestamp: data.timestamp || Date.now()
    },
    vibrate: [200, 100, 200],
    tag: 'recipe-app-notification',
    requireInteraction: false,
    actions: [
      {
        action: 'open',
        title: '開く',
        icon: '/static/icon-192x192.png'
      },
      {
        action: 'close',
        title: '閉じる'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// 通知クリック処理
self.addEventListener('notificationclick', function(event) {
  console.log('🖱️ Notification clicked:', event);
  
  event.notification.close();
  
  if (event.action === 'close') {
    return;
  }
  
  const urlToOpen = event.notification.data.url || '/';
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncloned: true })
      .then(function(clientList) {
        // 既に開いているウィンドウがあればフォーカス
        for (let i = 0; i < clientList.length; i++) {
          const client = clientList[i];
          if (client.url.includes(urlToOpen) && 'focus' in client) {
            return client.focus();
          }
        }
        // なければ新しいウィンドウを開く
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

// 通知を閉じた時の処理
self.addEventListener('notificationclose', function(event) {
  console.log('❌ Notification closed:', event);
});

console.log('🔔 Push notification handlers registered');