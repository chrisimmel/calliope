/**
 * App-shell service worker. Caches the static Clio shell (HTML, JS, CSS, fonts,
 * icons) under /clio/ with a stale-while-revalidate strategy so the app opens
 * offline. Story data and media (/v3/*) always go to the network — stories need
 * connectivity and must never be served stale.
 */

const CACHE = 'calliope-shell-v1';
const SHELL_ROOT = '/clio/';

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE).then(cache => cache.add(SHELL_ROOT)));
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches
      .keys()
      .then(keys =>
        Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // media/CDN → network
  if (url.pathname.startsWith('/v3/')) return; // API → network
  if (!url.pathname.startsWith('/clio/')) return;

  // SPA navigations: serve the cached shell when offline.
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).catch(() => caches.match(SHELL_ROOT, { ignoreSearch: true }))
    );
    return;
  }

  // Static assets: stale-while-revalidate. Match on the full URL (search
  // included) so the `main.js?<cuid>` cache-buster works — a new build's query
  // misses the cache and is fetched fresh. Hashed CSS/font filenames have no
  // query, so they still hit on exact match.
  event.respondWith(
    caches.open(CACHE).then(async cache => {
      const cached = await cache.match(req);
      const network = fetch(req)
        .then(res => {
          if (res && res.ok) cache.put(req, res.clone());
          return res;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
