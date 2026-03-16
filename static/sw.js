// Jerome7 Service Worker — offline support + caching
const CACHE_NAME = 'jerome7-20260316';

// Static assets: cache-first (rarely change)
const STATIC_ASSETS = [
  '/static/favicon.svg',
  '/static/manifest.json',
];

// HTML pages: network-first (content changes daily)
const HTML_PAGES = ['/', '/timer'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll([...STATIC_ASSETS, ...HTML_PAGES]))
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

  // API calls: network-only (no caching)
  if (url.pathname.startsWith('/api/') || url.pathname.includes('/stats') ||
      url.pathname.includes('/pledge') || url.pathname.includes('/log/') ||
      url.pathname.includes('/voice/')) {
    event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
    return;
  }

  // HTML pages (/, /timer): network-first so daily session updates propagate
  if (event.request.mode === 'navigate' || HTML_PAGES.includes(url.pathname)) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => caches.match(event.request))
    );
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
