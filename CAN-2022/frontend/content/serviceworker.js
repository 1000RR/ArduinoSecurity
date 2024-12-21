const CACHE_NAME = 'bobik-pwa-v1';
const urlsToCache = [
  '/',
  'manifest.json',
  'icon192.png',
  'icon512.png',
];

self.addEventListener('install', event => {
  caches.delete(CACHE_NAME);
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        return response || fetch(event.request);
      })
  );
});