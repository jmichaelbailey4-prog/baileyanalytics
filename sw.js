/* Bailey Analytics service worker. A daily-deployed, daily-data site must never
   serve stale content to an ONLINE visitor, so everything same-origin is
   network-first: fresh when online, the cached copy only as an offline fallback.
   The version-pinned Chart.js CDN is left to the browser's own HTTP cache
   (passthrough). This avoids the classic "new HTML + stale cached JS" breakage on
   deploy without content-hashed filenames. The pure router is exported for
   node:test; the SW wiring is guarded so the file loads cleanly under test. */
var CACHE_VERSION = "v1";                 // bump to force-drop old caches on activate
var CACHE = "ba-cache-" + CACHE_VERSION;
var PRECACHE = ["/offline.html", "/manifest.webmanifest",
  "/dashboards/lens.css", "/dashboards/lens.js", "/dashboards/hub.js",
  "/dashboards/personalize-core.js", "/dashboards/personalize.js",
  "/icons/icon-192.png", "/icons/icon-512.png", "/favicon.svg"];

// Pure: classify a GET request. Exported for tests.
//   "html"         -> network-first; offline fall back to cache then offline.html
//   "networkfirst" -> network-first; offline fall back to cache (assets + /data/*.json)
//   "passthrough"  -> not handled (cross-origin CDN: the browser HTTP cache owns it)
function routeStrategy(reqUrl, opts) {
  opts = opts || {};
  try { new URL(reqUrl); } catch (e) { return "passthrough"; }
  if (opts.mode === "navigate") return "html";
  return opts.sameOrigin ? "networkfirst" : "passthrough";
}

// Network-first: the fresh response wins and refreshes the cache; on a network
// failure fall back to the cached copy, then (for navigations) offline.html.
// Redirected and non-OK responses are never cached — a cached redirect can't
// satisfy a navigation, and caching an error would poison the offline copy.
function networkFirst(req, fallbackUrl) {
  return fetch(req).then(function (res) {
    if (res && res.ok && !res.redirected) {
      var copy = res.clone();
      caches.open(CACHE).then(function (c) { c.put(req, copy); });
    }
    return res;
  }).catch(function () {
    return caches.match(req).then(function (hit) {
      if (hit) return hit;
      if (fallbackUrl) return caches.match(fallbackUrl);
      return Response.error();
    });
  });
}

if (typeof self !== "undefined" && self.addEventListener && typeof caches !== "undefined") {
  self.addEventListener("install", function (e) {
    e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(PRECACHE); })
      .then(function () { return self.skipWaiting(); }));
  });
  self.addEventListener("activate", function (e) {
    e.waitUntil(caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; })
        .map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); }));
  });
  self.addEventListener("fetch", function (e) {
    var req = e.request;
    if (req.method !== "GET") return;
    var sameOrigin = new URL(req.url).origin === self.location.origin;
    var strat = routeStrategy(req.url, { sameOrigin: sameOrigin, mode: req.mode });
    if (strat === "html") e.respondWith(networkFirst(req, "/offline.html"));
    else if (strat === "networkfirst") e.respondWith(networkFirst(req, null));
    // passthrough: no respondWith -> default browser fetch (+ its HTTP cache)
  });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { routeStrategy: routeStrategy, CACHE_VERSION: CACHE_VERSION, CACHE: CACHE, PRECACHE: PRECACHE };
}
