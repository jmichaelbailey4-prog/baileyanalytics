/* Renders the Favorites page: saved lenses as hub tiles (reusing hub.js), an
   empty state, a default-range preference, the local-only disclosure, and
   per-tile remove. All client-side; degrades to the empty state without data. */
(function () {
  "use strict";
  var core = self.BACore, store = self.BAStore;
  var INDEX = {
    economic: "/data/lenses/index.json", consumer: "/data/consumer/index.json",
    banking: "/data/banking/index.json", business: "/data/business/index.json",
    markets: "/data/markets/index.json", energy: "/data/energy/index.json",
    housing: "/data/housing/index.json", global: "/data/global/index.json"
  };

  function esc(s) { var d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }

  var INDEX_CACHE = {};   // per-session: toggling a favorite shouldn't re-fetch every category index

  function loadCategory(cat) {
    if (INDEX_CACHE[cat]) return Promise.resolve(INDEX_CACHE[cat]);
    return fetch(INDEX[cat], { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw 0;
      return r.json();
    }).then(function (d) {
      var m = {};
      (d.lenses || []).forEach(function (l) { m[l.id] = l; });
      var res = { ok: true, map: m };
      INDEX_CACHE[cat] = res;   // cache successes only; a transient failure retries next render
      return res;
    }).catch(function () { return { ok: false, map: {} }; });  // failed fetch != "lens gone"
  }

  function disclosure() {
    return '<p class="fav-note">Your favorites and preferences live only in this browser, on this ' +
      "device — there&rsquo;s no account. Clearing your browser&rsquo;s site data will reset them, and " +
      "they won&rsquo;t sync to your other devices. Account sync is on the roadmap.</p>";
  }

  function prefsBlock() {
    var cur = (store && store.getPref("rangeDefault")) || "";
    function opt(v, label) {
      return '<option value="' + v + '"' + (cur === v ? " selected" : "") + ">" + label + "</option>";
    }
    return '<section class="fav-prefs"><h2 class="fav-h2">Preferences</h2>' +
      '<label class="fav-pref-row">Default chart range ' +
      '<select id="fav-range"><option value="">Auto (1Y, longer where needed)</option>' +
      opt("1Y", "1 year") + opt("5Y", "5 years") + opt("Max", "Max") + "</select></label>" +
      '<button type="button" id="fav-clear" class="fav-clear">Clear all favorites</button>' +
      "</section>";
  }

  function emptyState() {
    return '<div class="fav-empty"><p class="fav-empty-lead">You haven&rsquo;t saved any lenses yet.</p>' +
      '<p class="fav-empty-sub">Browse the dashboards and tap the &#9734; on any lens to pin it here ' +
      'for quick access.</p><a class="cta" href="/dashboards/">Browse dashboards &rarr;</a></div>' +
      prefsBlock() + disclosure();
  }

  function wirePrefs() {
    var sel = document.getElementById("fav-range");
    if (sel) sel.addEventListener("change", function () {
      store.setPref("rangeDefault", sel.value || null);
    });
    var clr = document.getElementById("fav-clear");
    if (clr) clr.addEventListener("click", function () {
      if (confirm("Remove all saved favorites? This can’t be undone.")) store.setFavorites([]);
    });
  }

  // A per-tile remove (x), correlated to `lenses` by render order (renderHubTiles
  // preserves order). The button goes in a positioned WRAPPER beside the card —
  // a <button> inside the <a class="hub-card"> would be nested-interactive
  // (invalid HTML; fails the site's axe gate).
  function wireRemove(grid, lenses) {
    Array.prototype.slice.call(grid.querySelectorAll(".hub-card")).forEach(function (card, i) {
      var lens = lenses[i];
      if (!lens) return;
      var wrap = document.createElement("div");
      wrap.className = "fav-tile";
      card.parentNode.insertBefore(wrap, card);
      wrap.appendChild(card);
      var x = document.createElement("button");
      x.type = "button";
      x.className = "fav-remove";
      x.setAttribute("aria-label", "Remove " + (lens.title || "lens") + " from Favorites");
      x.title = "Remove from Favorites";
      x.innerHTML = "&times;";
      x.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        store.setFavorites(core.removeFavorite(store.favorites(), lens.id));
      });
      wrap.appendChild(x);   // sibling of the anchor, inside the positioned wrapper
    });
  }

  // Favorites whose category index loaded but no longer contains the id (lens
  // renamed/retired): show a removable row so they aren't a permanent phantom.
  function missingBlock(missing) {
    if (!missing.length) return "";
    var rows = missing.map(function (f) {
      return '<div class="fav-gone"><span>' + esc(f.title || f.id) + " &mdash; no longer available</span>" +
        '<button type="button" class="fav-gone-rm" data-gone-id="' + esc(f.id) + '">Remove</button></div>';
    }).join("");
    return '<section class="fav-prefs"><h2 class="fav-h2">Unavailable</h2>' +
      '<p class="fav-gone-sub">These saved lenses no longer exist (renamed or retired). Remove them to tidy up.</p>' +
      rows + "</section>";
  }
  function wireMissing() {
    document.querySelectorAll(".fav-gone-rm[data-gone-id]").forEach(function (b) {
      b.addEventListener("click", function () {
        store.setFavorites(core.removeFavorite(store.favorites(), b.getAttribute("data-gone-id")));
      });
    });
  }

  function render() {
    var root = document.getElementById("fav-root");
    if (!root) return;
    var favs = store ? store.favorites() : [];
    if (!favs.length) { root.innerHTML = emptyState(); wirePrefs(); return; }
    // Only known, non-empty categories have an index to fetch.
    var needed = [];
    favs.forEach(function (f) {
      if (f.category && INDEX[f.category] && needed.indexOf(f.category) < 0) needed.push(f.category);
    });
    Promise.all(needed.map(loadCategory)).then(function (results) {
      var byCat = {};
      needed.forEach(function (c, i) { byCat[c] = results[i]; });
      var lenses = [], catById = {}, missing = [];
      favs.forEach(function (f) {
        var res = byCat[f.category];
        if (res && res.map[f.id]) { catById[f.id] = f.category; lenses.push(res.map[f.id]); }
        else if (!f.category || !INDEX[f.category]) missing.push(f);  // empty/unknown category -> removable
        else if (res && res.ok) missing.push(f);                      // known + loaded, id gone -> removable
        // known category but fetch failed: keep silently (transient), render nothing this load
      });
      if (!lenses.length && !missing.length) { root.innerHTML = emptyState(); wirePrefs(); return; }
      root.innerHTML = '<div class="hub-grid" id="fav-grid"></div>';
      var grid = document.getElementById("fav-grid");
      window.renderHubTiles(grid, lenses, function (id) { return window.lensHref(catById[id], id); });
      wireRemove(grid, lenses);
      root.insertAdjacentHTML("beforeend", missingBlock(missing) + prefsBlock() + disclosure());
      wireMissing();
      wirePrefs();
    });
  }

  document.addEventListener("DOMContentLoaded", render);
  document.addEventListener("ba:changed", render);   // re-render after toggle / remove / clear
})();
