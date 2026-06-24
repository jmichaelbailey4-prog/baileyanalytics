"""Cloudflare Web Analytics beacon — the single source of truth for the snippet, so
the baked-page head (briefpage.py) and the hand-written-page injector
(tools/cf_beacon.py) can never drift.

The token is **public** by design — it ships in every page's HTML for any visitor to
read — so it lives in the repo, not in a secret. (We use Cloudflare's *manual* setup,
baking the beacon ourselves, because automatic edge injection never worked for this
GitHub-Pages-behind-Cloudflare setup.) `defer` means it never blocks rendering.
"""

CF_BEACON_TOKEN = "c8d0e387f9b84507b1557117c4396452"

# Cloudflare's standard comment delimiters; they also serve as the injector's
# idempotency guard and make the baked snippet obvious in page source.
BEACON_START = "<!-- Cloudflare Web Analytics -->"
BEACON_END = "<!-- End Cloudflare Web Analytics -->"


def beacon_tag(token=CF_BEACON_TOKEN):
    """The full Cloudflare Web Analytics snippet, ready to drop into a page head."""
    return (
        f"{BEACON_START}"
        f'<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
        f'data-cf-beacon=\'{{"token": "{token}"}}\'></script>'
        f"{BEACON_END}"
    )
