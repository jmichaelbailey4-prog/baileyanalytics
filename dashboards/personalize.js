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
      // No _emit: prefs have no live listener, and emitting would make the
      // Favorites page re-render (re-fetch every category index) on a dropdown
      // change. Only favorites-list mutations (setFavorites) warrant a re-render.
    },
    _emit: function () { try { document.dispatchEvent(new CustomEvent("ba:changed")); } catch (e) {} }
  };
  self.BAStore = store;
  self.BAPrefs = {
    effectiveRange: function (pageDefault) { return core.effectiveRange(store.getPref("rangeDefault"), pageDefault); },
    setRangeDefault: function (key) { store.setPref("rangeDefault", key); },
    getTheme: function () { return store.getPref("theme"); },
    setTheme: function (key) { store.setPref("theme", key); }
  };

  // --- Theme toggle (injected into nav.top-nav; mirrors the Favorites entry) ---
  var SUN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
  var MOON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';
  var THEME_BG = { dark: "#0A0E14", light: "#F5F5F7" };
  var BANNER = { dark: { bg: "#0F172A", fg: "#F8FAFC", bd: "#1E293B" },
                 light: { bg: "#FFFFFF", fg: "#1D1D1F", bd: "#D2D2D7" } };

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  }
  function syncMeta(theme) {
    var m = document.querySelector('meta[name="theme-color"]');
    if (m) m.setAttribute("content", THEME_BG[theme] || THEME_BG.dark);
  }
  function syncToggle(btn, theme) {
    var toLight = theme === "dark";                 // show the destination icon
    btn.innerHTML = toLight ? SUN : MOON;
    var lbl = "Switch to " + (toLight ? "light" : "dark") + " theme";
    btn.setAttribute("aria-label", lbl); btn.title = lbl;
  }
  function applyTheme(theme, persist) {
    document.documentElement.setAttribute("data-theme", theme);
    if (persist) store.setPref("theme", theme);
    syncMeta(theme);
    try { document.dispatchEvent(new CustomEvent("ba:theme", { detail: { theme: theme } })); } catch (e) {}
  }
  function injectThemeToggle() {
    var nav = document.querySelector("nav.top-nav");
    if (!nav || nav.querySelector("[data-theme-toggle]")) return;
    var btn = document.createElement("button");
    btn.type = "button"; btn.className = "theme-toggle"; btn.setAttribute("data-theme-toggle", "");
    syncToggle(btn, currentTheme());
    btn.addEventListener("click", function () {
      var next = currentTheme() === "light" ? "dark" : "light";
      applyTheme(next, true); syncToggle(btn, next);
    });
    nav.appendChild(btn);
  }
  // Follow the OS until the visitor explicitly picks (no stored pref).
  if (window.matchMedia) {
    try {
      matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function (e) {
        if (store.getPref("theme")) return;
        var theme = e.matches ? "dark" : "light";
        applyTheme(theme, false);
        var btn = document.querySelector("[data-theme-toggle]");
        if (btn) syncToggle(btn, theme);
      });
    } catch (e) { /* old Safari: addListener-only; non-critical */ }
  }

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
      "border:1px solid;border-radius:999px;" +
      "padding:.5rem 1rem;font:500 .8rem -apple-system,BlinkMacSystemFont,'Inter',sans-serif;" +
      "box-shadow:0 4px 16px rgba(0,0,0,.4);display:none";
    document.body.appendChild(b);
    function styleBanner() { var c = BANNER[currentTheme()] || BANNER.dark;
      b.style.background = c.bg; b.style.color = c.fg; b.style.borderColor = c.bd; }
    styleBanner();
    document.addEventListener("ba:theme", styleBanner);
    function upd() { b.style.display = navigator.onLine ? "none" : "block"; }
    window.addEventListener("online", upd);
    window.addEventListener("offline", upd);
    upd();
  }

  function init() { injectNav(); injectThemeToggle(); offlineBanner(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
