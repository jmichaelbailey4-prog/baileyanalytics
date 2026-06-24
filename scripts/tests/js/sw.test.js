const test = require("node:test");
const assert = require("node:assert");
const { loadScript } = require("./load");
const sw = loadScript("sw.js");

test("navigations -> html (network-first + offline fallback)", () => {
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/x", { mode: "navigate", sameOrigin: true }), "html");
});
test("same-origin data json -> networkfirst", () => {
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/data/lenses/index.json", { sameOrigin: true }), "networkfirst");
});
test("same-origin assets -> networkfirst (fresh online, cached for offline)", () => {
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/dashboards/lens.css", { sameOrigin: true }), "networkfirst");
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/icons/icon-192.png", { sameOrigin: true }), "networkfirst");
});
test("cross-origin (Chart.js CDN) -> passthrough (browser HTTP cache owns it)", () => {
  assert.equal(sw.routeStrategy("https://cdn.jsdelivr.net/npm/chart.js@4/x.js", { sameOrigin: false }), "passthrough");
});
test("any same-origin non-navigation -> networkfirst", () => {
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/something", { sameOrigin: true }), "networkfirst");
});
test("malformed url -> passthrough (no throw)", () => {
  assert.equal(sw.routeStrategy("::::", { sameOrigin: true }), "passthrough");
});
test("constants present", () => {
  assert.ok(sw.CACHE.startsWith("ba-cache-"));
  assert.ok(Array.isArray(sw.PRECACHE) && sw.PRECACHE.includes("/offline.html"));
});
