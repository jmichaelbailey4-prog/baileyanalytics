/* Bailey Analytics service worker. A daily-data site must never serve frozen
   content while online: HTML + /data/*.json are network-first; static assets are
   stale-while-revalidate; the cache is busted by CACHE_VERSION each deploy. The
   pure router (routeStrategy) is exported for node:test; the SW wiring is guarded
   so the file loads cleanly under test (no self/caches present there). */
var CACHE_VERSION = "v1";                 // bump on deploy to purge old caches
var CACHE = "ba-cache-" + CACHE_VERSION;
var PRECACHE = ["/offline.html", "/manifest.webmanifest",
  "/dashboards/lens.css", "/dashboards/lens.js", "/dashboards/hub.js",
  "/dashboards/personalize-core.js", "/dashboards/personalize.js",
  "/icons/icon-192.png", "/icons/icon-512.png", "/favicon.svg"];

// Pure: classify a request into a caching strategy. Exported for tests.
function routeStrategy(reqUrl, opts) {
  opts = opts || {};
  var u;
  try { u = new URL(reqUrl); } catch (e) { return "network"; }
  if (opts.mode === "navigate") return "html";
  if (opts.sameOrigin && u.pathname.indexOf("/data/") === 0 &&
      u.pathname.indexOf(".json") === u.pathname.length - 5) return "data";
  if (/\.(css|js|png|svg|webmanifest|woff2?)$/.test(u.pathname)) return "asset";
  if (!opts.sameOrigin) return "asset";   // CDN (Chart.js) — cache opaquely
  return "network";                       // default: browser passthrough
}

function networkFirst(req, fallbackUrl) {
  return fetch(req).then(function (res) {
    if (res && res.ok) {
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

function staleWhileRevalidate(req) {
  return caches.open(CACHE).then(function (c) {
    return c.match(req).then(function (hit) {
      var net = fetch(req).then(function (res) {
        if (res && (res.ok || res.type === "opaque")) c.put(req, res.clone());
        return res;
      }).catch(function () { return hit; });
      return hit || net;
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
    else if (strat === "data") e.respondWith(networkFirst(req, null));
    else if (strat === "asset") e.respondWith(staleWhileRevalidate(req));
    // "network": no respondWith -> default browser fetch
  });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { routeStrategy: routeStrategy, CACHE_VERSION: CACHE_VERSION, CACHE: CACHE, PRECACHE: PRECACHE };
}
