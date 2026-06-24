const test = require("node:test");
const assert = require("node:assert");
const { loadScript } = require("./load");
const sw = loadScript("sw.js");

test("navigations -> html (network-first + offline fallback)", () => {
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/x", { mode: "navigate", sameOrigin: true }), "html");
});
test("same-origin data json -> data (network-first)", () => {
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/data/lenses/index.json", { sameOrigin: true }), "data");
});
test("static assets -> asset (stale-while-revalidate)", () => {
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/dashboards/lens.css", { sameOrigin: true }), "asset");
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/icons/icon-192.png", { sameOrigin: true }), "asset");
});
test("cross-origin (Chart.js CDN) -> asset", () => {
  assert.equal(sw.routeStrategy("https://cdn.jsdelivr.net/npm/chart.js@4/x.js", { sameOrigin: false }), "asset");
});
test("other same-origin -> network passthrough", () => {
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/something", { sameOrigin: true }), "network");
});
test("non-/data json is not treated as data route", () => {
  // only /data/*.json is network-first data; a stray .json elsewhere is just an asset
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/x/y.json", { sameOrigin: true }), "network");
});
test("constants present", () => {
  assert.ok(sw.CACHE.startsWith("ba-cache-"));
  assert.ok(Array.isArray(sw.PRECACHE) && sw.PRECACHE.includes("/offline.html"));
});
