/* Client glue for personalization + PWA. Pure logic lives in personalize-core.js
   (self.BACore). DOM/browser wiring only here. Degrades silently without
   localStorage / serviceWorker. */
(function () {
  "use strict";
  var core = self.BACore || {};
  var FAV_KEY = "ba:favorites", PREF_KEY = "ba:prefs";

  var store = {
    _get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    _set: function (k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } },
    favorites: function () { return core.parseFavorites(this._get(FAV_KEY)); },
    setFavorites: function (l) { this._set(FAV_KEY, core.serializeFavorites(l)); this._emit(); },
    toggle: function (fav) {
      var l = this.favorites();
      l = core.hasFavorite(l, fav.id) ? core.removeFavorite(l, fav.id) : core.addFavorite(l, fav);
      this.setFavorites(l);
      return core.hasFavorite(l, fav.id);
    },
    getPref: function (name) {
      try { return (JSON.parse(this._get(PREF_KEY)) || {})[name] || null; } catch (e) { return null; }
    },
    setPref: function (name, val) {
      var p = {};
      try { p = JSON.parse(this._get(PREF_KEY)) || {}; } catch (e) {}
      p[name] = val;
      this._set(PREF_KEY, JSON.stringify(p));
      this._emit();
    },
    _emit: function () { try { document.dispatchEvent(new CustomEvent("ba:changed")); } catch (e) {} }
  };
  self.BAStore = store;
  self.BAPrefs = {
    effectiveRange: function (pageDefault) { return core.effectiveRange(store.getPref("rangeDefault"), pageDefault); },
    setRangeDefault: function (key) { store.setPref("rangeDefault", key); }
  };

  // --- Service worker ---
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js", { updateViaCache: "none" }).catch(function () {});
    });
  }

  // --- Favorites nav entry (injected; avoids hand-editing 78 navs) ---
  function injectNav() {
    var nav = document.querySelector("nav.top-nav");
    if (!nav || nav.querySelector("[data-fav-nav]")) return;
    var a = document.createElement("a");
    a.href = "/dashboards/favorites.html";
    a.textContent = "Favorites";
    a.setAttribute("data-fav-nav", "");
    if (location.pathname === "/dashboards/favorites.html") a.setAttribute("aria-current", "page");
    var after = null;
    nav.querySelectorAll("a").forEach(function (l) {
      if (/\/dashboards\/?$/.test(l.getAttribute("href") || "")) after = l;  // place after "Dashboards"
    });
    if (after && after.nextSibling) nav.insertBefore(a, after.nextSibling);
    else nav.appendChild(a);
  }

  // --- Lens-page star (bound on lens:rendered; lens.js emits the button) ---
  function syncStar(btn) {
    var on = core.hasFavorite(store.favorites(), btn.getAttribute("data-fav-id"));
    btn.setAttribute("aria-pressed", String(on));
    btn.innerHTML = on ? "&#9733;" : "&#9734;";   // ★ / ☆
    var lbl = on ? "Saved to Favorites" : "Save to Favorites";
    btn.setAttribute("aria-label", lbl);
    btn.title = lbl;
  }
  document.addEventListener("lens:rendered", function () {
    var btn = document.querySelector(".fav-star[data-fav-id]");
    if (!btn || btn._bound) return;
    btn._bound = true;
    syncStar(btn);
    btn.addEventListener("click", function () {
      store.toggle({
        id: btn.getAttribute("data-fav-id"),
        title: btn.getAttribute("data-fav-title"),
        category: btn.getAttribute("data-fav-category")
      });
      syncStar(btn);
    });
  });

  // --- Offline indicator (styled inline so it works on pages without lens.css) ---
  function offlineBanner() {
    if (document.getElementById("ba-offline")) return;
    var b = document.createElement("div");
    b.id = "ba-offline";
    b.textContent = "Offline — showing last saved data";
    b.setAttribute("role", "status");
    b.style.cssText = "position:fixed;left:50%;bottom:1rem;transform:translateX(-50%);z-index:50;" +
      "background:#0F172A;color:#F8FAFC;border:1px solid #1E293B;border-radius:999px;" +
      "padding:.5rem 1rem;font:500 .8rem -apple-system,BlinkMacSystemFont,'Inter',sans-serif;" +
      "box-shadow:0 4px 16px rgba(0,0,0,.4);display:none";
    document.body.appendChild(b);
    function upd() { b.style.display = navigator.onLine ? "none" : "block"; }
    window.addEventListener("online", upd);
    window.addEventListener("offline", upd);
    upd();
  }

  function init() { injectNav(); offlineBanner(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
