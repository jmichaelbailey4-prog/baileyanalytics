"""Single source for the PWA head fragment + web manifest. Imported by the head
stamper (tools/pwa_head.py) and briefpage.py so baked + hand-written pages emit
byte-identical tags (avoids the re-bake flip-flop the beacon work hit)."""
import json

THEME_COLOR = "#0A0E14"
THEME_COLOR_LIGHT = "#F5F5F7"


def theme_head():
    """Inline, render-blocking pre-paint setter: applies the saved theme (or the
    OS preference) to <html data-theme> BEFORE first paint, so there is no flash
    of the wrong theme. Logic mirrors personalize-core.resolveTheme (cannot import
    in an inline pre-paint context). Callers add the `<!-- theme:head -->` marker."""
    return (
        '  <script>(function(){try{var p=(JSON.parse(localStorage.getItem("ba:prefs"))||{}).theme;'
        'var d=p==="light"||p==="dark"?p:(window.matchMedia&&matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");'
        'document.documentElement.setAttribute("data-theme",d);}catch(e){}})();</script>'
    )


def head_tags():
    """The <head> block stamped into every page (no leading marker; callers add
    the `<!-- pwa:head -->` marker line above this)."""
    return (
        '  <link rel="manifest" href="/manifest.webmanifest">\n'
        f'  <meta name="theme-color" content="{THEME_COLOR}">\n'
        '  <link rel="apple-touch-icon" href="/apple-touch-icon.png">\n'
        '  <script defer src="/dashboards/personalize-core.js"></script>\n'
        '  <script defer src="/dashboards/personalize.js"></script>'
    )


def manifest_dict():
    return {
        "name": "Bailey Analytics",
        "short_name": "Bailey",
        "description": "Daily, plain-English dashboards on the U.S. and global economy.",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "any",
        "background_color": THEME_COLOR,
        "theme_color": THEME_COLOR,
        "icons": [
            {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/icons/icon-192-maskable.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable"},
            {"src": "/icons/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }


def manifest_json():
    return json.dumps(manifest_dict(), indent=2) + "\n"


if __name__ == "__main__":
    print(manifest_json())
