const test = require("node:test");
const assert = require("node:assert");
const { loadScript } = require("./load");
const core = loadScript("dashboards/personalize-core.js");

test("effectiveRange: no pref -> page default", () => {
  assert.equal(core.effectiveRange(null, "1Y"), "1Y");
  assert.equal(core.effectiveRange(undefined, "5Y"), "5Y");
});
test("effectiveRange: longer pref wins", () => {
  assert.equal(core.effectiveRange("Max", "1Y"), "Max");
  assert.equal(core.effectiveRange("5Y", "1Y"), "5Y");
});
test("effectiveRange: page default floors a shorter pref (banking stays 5Y)", () => {
  assert.equal(core.effectiveRange("1Y", "5Y"), "5Y");
});
test("effectiveRange: junk -> 1Y / pageDefault", () => {
  assert.equal(core.effectiveRange("bogus", "bogus"), "1Y");
  assert.equal(core.effectiveRange("bogus", "5Y"), "5Y");
});
test("favorites add/dedupe/remove/has", () => {
  let l = core.addFavorite([], { id: "a", title: "A", category: "economic" });
  l = core.addFavorite(l, { id: "b", title: "B", category: "markets" });
  l = core.addFavorite(l, { id: "a", title: "A2", category: "economic" });
  assert.equal(l.length, 2);
  assert.equal(l[0].id, "a");
  assert.equal(l[0].title, "A2");
  assert.ok(core.hasFavorite(l, "b"));
  l = core.removeFavorite(l, "a");
  assert.equal(core.hasFavorite(l, "a"), false);
});
test("parseFavorites tolerates junk", () => {
  assert.deepEqual(core.parseFavorites("not json"), []);
  assert.deepEqual(core.parseFavorites("{}"), []);
  assert.deepEqual(core.parseFavorites('[{"id":"x","title":"X","category":"c"},{"bad":1}]'),
    [{ id: "x", title: "X", category: "c" }]);
});
test("serialize round-trips", () => {
  const l = [{ id: "x", title: "X", category: "c" }];
  assert.deepEqual(core.parseFavorites(core.serializeFavorites(l)), l);
});
test("groupByCategory buckets in first-seen order", () => {
  const g = core.groupByCategory([
    { id: "a", category: "economic" },
    { id: "b", category: "markets" },
    { id: "c", category: "economic" },
  ]);
  assert.deepEqual(Object.keys(g), ["economic", "markets"]);
  assert.equal(g.economic.length, 2);
});
