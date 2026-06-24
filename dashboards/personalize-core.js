/* Pure, DOM-free personalization helpers. A global (self.BACore) in the browser,
   a CommonJS module under node:test. No localStorage/DOM here — keep it testable. */
(function (root) {
  "use strict";
  var RANGE_RANK = { "1Y": 1, "5Y": 2, "Max": 3 };

  // The remembered default range never shortens a page below its own minimum
  // (quarterly pages declare "5Y"): effective = the longer of pref and pageDefault.
  function effectiveRange(userPref, pageDefault) {
    var pd = RANGE_RANK[pageDefault] ? pageDefault : "1Y";
    if (!RANGE_RANK[userPref]) return pd;
    return RANGE_RANK[userPref] >= RANGE_RANK[pd] ? userPref : pd;
  }

  // Theme resolution: an explicit stored choice ("light"/"dark") wins; otherwise
  // follow the OS (prefersDark). Mirrors the inline pre-paint head script.
  function resolveTheme(pref, prefersDark) {
    if (pref === "light" || pref === "dark") return pref;
    return prefersDark ? "dark" : "light";
  }

  function hasFavorite(list, id) {
    return Array.isArray(list) && list.some(function (f) { return f && f.id === id; });
  }
  // newest-first, deduped by id
  function addFavorite(list, fav) {
    var out = (Array.isArray(list) ? list : []).filter(function (f) { return f && f.id !== fav.id; });
    out.unshift({ id: fav.id, title: fav.title, category: fav.category });
    return out;
  }
  function removeFavorite(list, id) {
    return (Array.isArray(list) ? list : []).filter(function (f) { return f && f.id !== id; });
  }
  // tolerant: bad input -> []
  function parseFavorites(raw) {
    try {
      var v = JSON.parse(raw);
      if (!Array.isArray(v)) return [];
      return v.filter(function (f) { return f && typeof f.id === "string"; })
              .map(function (f) {
                return { id: f.id, title: String(f.title || f.id), category: String(f.category || "") };
              });
    } catch (e) { return []; }
  }
  function serializeFavorites(list) {
    return JSON.stringify(Array.isArray(list) ? list : []);
  }
  // group favorites by category, preserving first-seen order -> { category: [fav, ...] }
  function groupByCategory(list) {
    var g = {};
    (Array.isArray(list) ? list : []).forEach(function (f) {
      if (!f || !f.category) return;
      (g[f.category] = g[f.category] || []).push(f);
    });
    return g;
  }

  var api = {
    effectiveRange: effectiveRange, resolveTheme: resolveTheme, hasFavorite: hasFavorite,
    addFavorite: addFavorite, removeFavorite: removeFavorite, parseFavorites: parseFavorites,
    serializeFavorites: serializeFavorites, groupByCategory: groupByCategory, RANGE_RANK: RANGE_RANK
  };

  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.BACore = api;
})(typeof self !== "undefined" ? self : this);
