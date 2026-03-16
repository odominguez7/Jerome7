// Jerome7 Service Worker — offline support + caching
// Version updated by deploy process — change to bust cache
const CACHE_NAME = 'jerome7-v3';

// Static assets only — HTML pages are network-only
const STATIC_ASSETS = [
  '/static/favicon.svg',
  '/static/manifest.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Clean up old caches on activate
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // HTML pages and navigation: network-only (no caching, no stale content)
  if (event.request.mode === 'navigate' ||
      url.pathname === '/' || url.pathname === '/timer') {
    event.respondWith(fetch(event.request));
    return;
  }

  // API calls: network-only
  if (url.pathname.startsWith('/api/') || url.pathname.includes('/stats') ||
      url.pathname.includes('/pledge') || url.pathname.includes('/log/') ||
      url.pathname.includes('/voice/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Static assets: cache-first
  event.respondWith(
    caches.match(event.request).then((cached) =>
      cached || fetch(event.request).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
    )
  );
});
