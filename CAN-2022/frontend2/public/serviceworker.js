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

self.addEventListener("fetch", (event) => {
  if (event.request.url.indexOf('/socket.io') >= 0) {
    return;
  } else {
    event.respondWith(
      caches.open("dynamic-cache").then(async (cache) => {
        try {
          // Try to fetch from network first
          const networkResponse = await fetch(event.request);

          // If the response is an image and it fails, retry
          if (
            !networkResponse.ok &&
            event.request.destination === "image"
          ) {
            console.warn(`Image fetch failed: ${event.request.url}, retrying...`);
            return fetch(event.request, { cache: "reload" });
          }

          // Cache successful responses
          cache.put(event.request, networkResponse.clone());
          return networkResponse;
        } catch (error) {
          console.error("Fetch failed; returning cached resource if available:", error);

          // Fallback to cache if available
          return cache.match(event.request) || new Response("", { status: 404 });
        }
      })
    );
  }
});

self.addEventListener('activate', event => {
  caches.delete(CACHE_NAME);
});