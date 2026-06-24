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

  function loadCategory(cat) {
    return fetch(INDEX[cat], { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw 0;
      return r.json();
    }).then(function (d) {
      var m = {};
      (d.lenses || []).forEach(function (l) { m[l.id] = l; });
      return m;
    }).catch(function () { return {}; });
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

  // Inject a small remove (x) control into each rendered hub-card, correlated to
  // `lenses` by render order (renderHubTiles preserves order).
  function wireRemove(root, lenses) {
    root.querySelectorAll(".hub-card").forEach(function (card, i) {
      var lens = lenses[i];
      if (!lens) return;
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
      card.style.position = "relative";
      card.appendChild(x);
    });
  }

  function render() {
    var root = document.getElementById("fav-root");
    if (!root) return;
    var favs = store ? store.favorites() : [];
    if (!favs.length) { root.innerHTML = emptyState(); wirePrefs(); return; }
    var groups = core.groupByCategory(favs);
    var cats = Object.keys(groups);
    Promise.all(cats.map(loadCategory)).then(function (maps) {
      var lenses = [];
      cats.forEach(function (cat, i) {
        groups[cat].forEach(function (f) {
          var l = maps[i][f.id];
          if (l) { l = Object.assign({}, l); l._cat = cat; lenses.push(l); }
        });
      });
      if (!lenses.length) { root.innerHTML = emptyState(); wirePrefs(); return; }
      root.innerHTML = '<div class="hub-grid" id="fav-grid"></div>';
      var grid = document.getElementById("fav-grid");
      window.renderHubTiles(grid, lenses, function (id) {
        var l = lenses.find(function (x) { return x.id === id; });
        return window.lensHref(l._cat, id);
      });
      wireRemove(grid, lenses);
      root.insertAdjacentHTML("beforeend", prefsBlock() + disclosure());
      wirePrefs();
    });
  }

  document.addEventListener("DOMContentLoaded", render);
  document.addEventListener("ba:changed", render);   // re-render after toggle / remove / clear
})();
