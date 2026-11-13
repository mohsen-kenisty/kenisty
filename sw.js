/* Kenisty - offline-first service worker.
   Bump VERSION on every deploy so users get the new files. */
const VERSION = 'kenisty-v18';
const SHELL = VERSION + '-shell';   // our own files
const LIBS  = VERSION + '-libs';    // CDN scripts, fonts, Firebase SDK

const SHELL_FILES = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png'];
const CDN_PRECACHE = [              // best effort: install never fails because of these
  'https://cdn.tailwindcss.com/3.4.17',
  'https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&family=Cairo:wght@400;600;700&family=Almarai:wght@400;700;800&family=Amiri:wght@400;700&display=swap',
  'https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js',
  'https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js',
  'https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js'
];
// Only these hosts are ever cached. Firestore, Auth and Google APIs go straight to the network.
const CDN_HOSTS = ['cdn.tailwindcss.com', 'fonts.googleapis.com', 'fonts.gstatic.com', 'www.gstatic.com', 'cdnjs.cloudflare.com'];
const cacheable = u => u.origin === self.location.origin || CDN_HOSTS.includes(u.hostname);

async function grab(cache, url) {            // download one URL into a cache (never throws)
  const same = new URL(url).origin === self.location.origin;
  let res;
  try { res = await fetch(url, same ? { cache: 'reload' } : { mode: 'cors' }); }
  catch (_) {
    if (same) return;
    try { res = await fetch(url, { mode: 'no-cors' }); } catch (_) { return; }
  }
  if (res.ok || res.type === 'opaque') await cache.put(url, res);
}

self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const shell = await caches.open(SHELL);
    await shell.addAll(SHELL_FILES.map(f => new Request(f, { cache: 'reload' }))); // must succeed
    const libs = await caches.open(LIBS);
    await Promise.all(CDN_PRECACHE.map(u => grab(libs, u)));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const keep = [SHELL, LIBS];
    for (const k of await caches.keys()) if (!keep.includes(k)) await caches.delete(k);
    await self.clients.claim();
  })());
});

// Page HTML: serve the cached app instantly, refresh it in the background.
async function navigate(e) {
  const cache = await caches.open(SHELL);
  const cached = await cache.match('index.html', { ignoreSearch: true });
  const net = fetch(e.request).then(r => { if (r.ok) cache.put('index.html', r.clone()); return r; }).catch(() => null);
  e.waitUntil(net);
  if (cached) return cached;
  return (await net) || new Response('Offline - open the app once with internet first.',
    { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
}

// Everything else: stale-while-revalidate.
async function swr(e, cacheName) {
  const req = e.request, cache = await caches.open(cacheName);
  const hit = await cache.match(req);
  const net = fetch(req).then(r => {
    if (r.ok || (r.type === 'opaque' && req.mode === 'no-cors')) cache.put(req, r.clone());
    return r;
  }).catch(() => null);
  e.waitUntil(net);
  return hit || (await net) || new Response('', { status: 504 });
}

self.addEventListener('fetch', e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || !cacheable(url)) return;          // let the browser handle it
  if (req.mode === 'navigate') return e.respondWith(navigate(e));
  e.respondWith(swr(e, url.origin === self.location.origin ? SHELL : LIBS));
});

// The page lists everything it loaded, so the very first visit is cached too
// (requests made before the worker took control are otherwise missed).
self.addEventListener('message', e => {
  if (!e.data || e.data.type !== 'CACHE_URLS') return;
  e.waitUntil((async () => {
    const shell = await caches.open(SHELL), libs = await caches.open(LIBS);
    const urls = [...new Set(e.data.urls || [])].filter(u => { try { return cacheable(new URL(u)); } catch (_) { return false; } });
    await Promise.all(urls.map(u => grab(new URL(u).origin === self.location.origin ? shell : libs, u)));
  })());
});

// Tapping a notification opens (or focuses) the app.
self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil((async () => {
    const list = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const c of list) { if ('focus' in c) return c.focus(); }
    return self.clients.openWindow('./');
  })());
});
