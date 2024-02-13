let cacheName = 'v1';

self.addEventListener('install', (event) => {
  console.log('[Service Worker ' + cacheName + '] installing');
  event.waitUntil(async function() {
    const cache = await caches.open(cacheName);
    await cache.addAll(
      [
        './',
        './heater.html',
        './common.css',
        './common.js',
        './site.webmanifest',
        './assets/icon-192.png',
        './assets/icon-512.png',
        './fa/selection.min.js'
      ]
    );
    console.log('[Service Worker ' + cacheName + '] installed');
  }());
});

self.addEventListener('activate', event => {
  console.log('[Service Worker ' + cacheName + '] activating');
  var cacheKeeplist = [cacheName];

  event.waitUntil(async function() {
    const keyList = await caches.keys();
    const deletes = await Promise.all(keyList.map(function(key) {
      if (cacheKeeplist.indexOf(key) === -1) {
        return caches.delete(key);
      }
    }));
    console.log('[Service Worker ' + cacheName + '] activated');
    return deletes;
  }());
});

// https://redfin.engineering/how-to-fix-the-refresh-button-when-using-service-workers-a8e27af6df68
addEventListener('message', messageEvent => {
  if (messageEvent.data === 'skipWaiting') {
    console.log('[Service Worker ' + cacheName + '] doing skipWaiting');
    return skipWaiting();
  }
});

self.addEventListener('fetch', event => {
  event.respondWith((async () => {
    if (event.request.mode === "navigate" &&
      event.request.method === "GET" &&
      registration.waiting &&
      (await clients.matchAll()).length < 2
    ) {
      console.log('[Service Worker ' + cacheName + '] triggering skipWaiting');
      registration.waiting.postMessage('skipWaiting');
      console.log('[Service Worker ' + cacheName + '] redirecting to new version');
      return Response.redirect(event.request.url);
    }
    // https://developers.google.com/web/ilt/pwa/caching-files-with-service-worker#cache_falling_back_to_the_network
    const cachedResponse = await caches.match(event.request);
    console.log('[Service Worker ' + cacheName + '] ' + (cachedResponse ? 'HIT' : 'MISS') + ' ' + event.request.mode + ' ' + event.request.method + ' ' + event.request.url);
    return cachedResponse || fetch(event.request);
  })());
});
