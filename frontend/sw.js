const CACHE_NAME = 'fitai-v2.0.2';
const STATIC_CACHE = 'fitai-static-v2.0.2';
const DYNAMIC_CACHE = 'fitai-dynamic-v2.0.2';

 
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  'https://cdn.jsdelivr.net/npm/chart.js'
];

 
self.addEventListener('install', event => {
  console.log('[SW] Installing service worker');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

 
self.addEventListener('activate', event => {
  console.log('[SW] Activating service worker');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

 
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

   
  if (request.method !== 'GET' || !url.origin.includes(self.location.origin) && !url.origin.includes('cdn.jsdelivr.net') && !url.origin.includes('unpkg.com')) {
    return;
  }

   
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/activities') || url.pathname.startsWith('/stats') || url.pathname.startsWith('/sessions') || url.pathname.startsWith('/recovery/')) {
    event.respondWith(
      fetch(request)
        .then(response => {
           
          if (response.ok) {
            const responseClone = response.clone();
            caches.open(DYNAMIC_CACHE).then(cache => {
              cache.put(request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
           
          return caches.match(request).then(cachedResponse => {
            if (cachedResponse) {
              return cachedResponse;
            }
             
            if (url.pathname.includes('/stats')) {
              return new Response(JSON.stringify({
                max_speed: 0,
                total_sessions: 0,
                session_distance_km: 0
              }), {
                headers: { 'Content-Type': 'application/json' }
              });
            }
            return new Response(JSON.stringify({ error: 'Offline - please check connection' }), {
              status: 503,
              headers: { 'Content-Type': 'application/json' }
            });
          });
        })
    );
  } else {
     
    event.respondWith(
      caches.match(request)
        .then(cachedResponse => {
          if (cachedResponse) {
            return cachedResponse;
          }
          return fetch(request).then(response => {
             
            if (response.ok) {
              const responseClone = response.clone();
              caches.open(DYNAMIC_CACHE).then(cache => {
                cache.put(request, responseClone);
              });
            }
            return response;
          });
        })
    );
  }
});

 
self.addEventListener('sync', event => {
  console.log('[SW] Background sync triggered:', event.tag);

  if (event.tag === 'sync-recovery-data') {
    event.waitUntil(syncRecoveryData());
  }
});

async function syncRecoveryData() {
  try {
    const cache = await caches.open(DYNAMIC_CACHE);
    const keys = await cache.keys();

     
    const pendingRequests = keys.filter(request =>
      request.url.includes('/recovery/log') &&
      request.method === 'POST'
    );

    for (const request of pendingRequests) {
      try {
        const response = await fetch(request);
        if (response.ok) {
          await cache.delete(request);
          console.log('[SW] Synced recovery data');
        }
      } catch (error) {
        console.log('[SW] Failed to sync recovery data:', error);
      }
    }
  } catch (error) {
    console.log('[SW] Background sync error:', error);
  }
}

 
self.addEventListener('push', event => {
  if (!event.data) return;

  const data = event.data.json();
  const options = {
    body: data.body,
    icon: '/icon-192x192.png',
    badge: '/icon-192x192.png',
    vibrate: [100, 50, 100],
    data: data.data || {},
    actions: data.actions || []
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

 
self.addEventListener('notificationclick', event => {
  event.notification.close();

  event.waitUntil(
    clients.openWindow(event.notification.data.url || '/')
  );
});