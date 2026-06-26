"""The scoring methodology surface (score-explain-order follow-up, 2026-06-26).

`build_methodology()` turns the band specs + taxonomy + curated 'why these bands'
prose into one data structure; `render_methodology()` bakes it into a static page
(like briefpage.py). The in-context scale strip (scoring.js) reads the same
data/methodology.json, so the page and the strip can never disagree.

Pure: data in, HTML/dict out; refresh_lenses owns disk I/O.
"""

import functools
from datetime import datetime, timezone
from html import escape

from . import analytics, bands, build, config, narrative, pwa, reasons

SITE = "https://baileyanalytics.com"

_PWA_HEAD = "<!-- pwa:head -->\n" + pwa.head_tags()
_THEME_HEAD = "<!-- theme:head -->\n" + pwa.theme_head()

DEFAULT_NOTE = ("Tracked for context — shown without a good-or-bad badge, because no "
                "single level of it is simply better or worse.")

# How each decision axis reads in one phrase (shown under a severity signal's bands).
AXIS_LABEL = {
    "level": "the latest reading",
    "yoy": "the year-over-year change",
    "yoy_computed": "the year-over-year change",
    "delta_from_low": "the rise above the trailing-12-month low",
    "custom": "",
}

# Taxonomy explainer — the four kinds of signal (mirrors the status model in CLAUDE.md).
TAXONOMY = {
    "intro": ("Every signal on the site is read by a fixed, documented rule applied to "
              "the latest numbers — never a human judgement call. Here is exactly how "
              "each reading becomes the badge you see. There are four kinds of signal:"),
    "severity": ("Severity — most signals. A reading maps to one of four badges: "
                 "ok, watch, elevated, or alert. The thresholds below are the real "
                 "numbers the code uses; the marker on each lens page shows where the "
                 "latest reading falls."),
    "info": ("Descriptive — tracked for context, not scored. A higher or lower reading "
             "isn't itself better or worse, so there's no badge — just the number and "
             "its direction."),
    "momentum": ("Momentum — a few market signals show which way a price is moving "
                 "(up / down / flat) rather than a good-or-bad verdict."),
    "neutral": ("Neutral scoreboards — two lenses (the asset-class scoreboard and crypto "
                "market structure) summarise how things are moving without aggregating to "
                "a good-or-bad verdict."),
}

# crypto-structure is injected (built outside config.CATEGORIES); list it for coverage.
_CRYPTO = [("btc-dominance", "Bitcoin Dominance", "BTC dominance"),
           ("crypto-rotation", "Large-vs-Small Rotation", "Alt rotation"),
           ("btc-eth-ratio", "Bitcoin / Ether Ratio", "BTC/ETH")]


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _signal_entry(cat, lens, ind):
    rule = ind.rule
    neutral = lens.id in narrative.NEUTRAL_LENSES
    taxonomy = "neutral" if neutral else narrative.rule_kind(rule)  # severity/momentum/info
    entry = {
        "category": cat["id"], "category_title": cat["title"],
        "lens_id": lens.id, "lens_title": lens.title,
        "indicator_id": ind.id, "title": ind.title, "short": ind.short,
        "taxonomy": taxonomy,
    }
    spec = getattr(rule, "band_spec", None)
    if taxonomy == "severity" and spec:
        entry["why"] = reasons.BAND_WHY.get(getattr(rule, "band_tag", ""), "")
        entry["axis"] = {"kind": spec.kind, "unit": spec.unit,
                         "value_format": spec.value_format,
                         "label": AXIS_LABEL.get(spec.kind, "")}
        if spec.kind != "custom":
            entry["edges"] = list(spec.edges)
            entry["segments"] = bands.segment_ranges(spec)
    else:
        entry["note"] = getattr(ind, "no_severity_reason", "") or DEFAULT_NOTE
    return entry


def build_methodology():
    """The full methodology data: ordered signals + the taxonomy explainer."""
    signals = {}
    for cat in config.CATEGORIES:
        for lens in cat["lenses"]:
            for ind in lens.indicators:
                signals[f"{lens.id}::{ind.id}"] = _signal_entry(cat, lens, ind)
        if cat["id"] == "markets":  # keep the injected crypto lens grouped under Markets
            for id_, title, short in _CRYPTO:
                signals[f"crypto-structure::{id_}"] = {
                    "category": "markets", "category_title": cat["title"],
                    "lens_id": "crypto-structure", "lens_title": "Crypto Market Structure",
                    "indicator_id": id_, "title": title, "short": short,
                    "taxonomy": "neutral", "note": reasons.NEUTRAL_CRYPTO}
    return {"generated_at": _now(), "taxonomy": TAXONOMY, "signals": signals}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _ind_map():
    return {(lens.id, ind.id): ind
            for cat in config.CATEGORIES for lens in cat["lenses"]
            for ind in lens.indicators}


def static_bands(lens_id, indicator_id):
    """For staticread.py's no-JS fragment: {anchor, rows:[(status, range_text)]} for a
    scored signal with a static axis, or None (custom/info/momentum/unknown)."""
    ind = _ind_map().get((lens_id, indicator_id))
    if not ind or narrative.rule_kind(ind.rule) != "severity":
        return None
    spec = getattr(ind.rule, "band_spec", None)
    if not spec or spec.kind == "custom":
        return None
    rows = [(seg["status"], _range_text(seg, spec.unit, spec.value_format))
            for seg in bands.segment_ranges(spec)]
    return {"anchor": f"{lens_id}--{indicator_id}", "rows": rows}


def _range_text(seg, unit, vf):
    """Human range for one band, e.g. 'below 5.50%', '5.50–6.50%', '7.50% and up'."""
    lo, hi = seg["lo"], seg["hi"]
    if lo is None:
        return f"below {build._fmt(hi, unit, vf)}"
    if hi is None:
        return f"{build._fmt(lo, unit, vf)} and up"
    return f"{build._fmt(lo, unit, vf)}–{build._fmt(hi, unit, vf)}"


def _bands_html(sig):
    axis = sig.get("axis", {})
    unit, vf = axis.get("unit", ""), axis.get("value_format", "decimal")
    rows = "".join(
        f'<li><span class="badge {escape(seg["status"])}">{escape(seg["status"])}</span>'
        f'<span class="method-range">{escape(_range_text(seg, unit, vf))}</span></li>'
        for seg in sig["segments"])
    label = axis.get("label", "")
    scored_on = (f'<p class="method-axis">Scored on {escape(label)}.</p>'
                 if label else "")
    return scored_on + f'<ul class="method-bands">{rows}</ul>'


def _signal_html(sig):
    anchor = f'{sig["lens_id"]}--{sig["indicator_id"]}'
    parts = [f'<div class="method-signal" id="{escape(anchor, quote=True)}">',
             f'<h4>{escape(sig["title"])}</h4>']
    if sig["taxonomy"] == "severity" and "segments" in sig:
        parts.append(_bands_html(sig))
    if sig.get("why"):
        parts.append(f'<p class="method-why">{escape(sig["why"])}</p>')
    if sig.get("note"):
        kind = {"info": "Tracked, not scored", "momentum": "Momentum, not scored",
                "neutral": "Neutral scoreboard"}.get(sig["taxonomy"], "Tracked, not scored")
        parts.append(f'<p class="signal-note"><strong>{escape(kind)}:</strong> '
                     f'{escape(sig["note"])}</p>')
    parts.append("</div>")
    return "".join(parts)


def _taxonomy_html(tax):
    items = "".join(
        f'<li><strong>{escape(label)}</strong> {escape(tax[key])}</li>'
        for key, label in (("severity", "Severity."), ("info", "Descriptive."),
                           ("momentum", "Momentum."), ("neutral", "Neutral scoreboards.")))
    return (f'<p class="lede">{escape(tax["intro"])}</p>'
            f'<ul class="method-taxonomy">{items}</ul>')


def render_methodology(data):
    """The full static methodology page (chrome mirrors briefpage.py)."""
    title = "How We Score — Methodology — Bailey Analytics"
    desc = ("Exactly how every Bailey Analytics signal becomes a badge: the real "
            "thresholds behind ok / watch / elevated / alert, plus why each band sits "
            "where it does.")
    canonical = f"{SITE}/dashboards/methodology.html"

    body = []
    cur_cat = cur_lens = None
    for sig in data["signals"].values():
        if sig["category"] != cur_cat:
            if cur_cat is not None:
                body.append("</section>")
            body.append(f'<section><h2 class="method-cat">{escape(sig["category_title"])}</h2>')
            cur_cat, cur_lens = sig["category"], None
        if sig["lens_id"] != cur_lens:
            body.append(f'<h3 class="method-lens">{escape(sig["lens_title"])}</h3>')
            cur_lens = sig["lens_id"]
        body.append(_signal_html(sig))
    if cur_cat is not None:
        body.append("</section>")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(desc, quote=True)}">
  <link rel="canonical" href="{escape(canonical, quote=True)}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Bailey Analytics">
  <meta property="og:title" content="{escape(title, quote=True)}">
  <meta property="og:description" content="{escape(desc, quote=True)}">
  <meta property="og:url" content="{escape(canonical, quote=True)}">
  <meta property="og:image" content="{SITE}/og/site.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="/dashboards/lens.css">
  {analytics.beacon_tag()}
  {_THEME_HEAD}
  {_PWA_HEAD}
</head>
<body>
  <nav class="wordmark" aria-label="Bailey Analytics home"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav" aria-label="Primary"><a href="/dashboards/brief.html">Today&#39;s Brief</a><a href="/dashboards/">Dashboards</a><a href="/dashboards/track-record.html">Track Record</a><a href="/about.html">About</a></nav>
  <main>
    <a class="back" href="/dashboards/">&larr; Dashboards</a>
    <h1>How we score</h1>
    {_taxonomy_html(data["taxonomy"])}
    {''.join(body)}
    <div class="foot">
      The thresholds shown here are generated directly from the rule code, so this page
      can never show a number the site doesn&rsquo;t actually use. This explains how a
      reading becomes a badge — not how the next-print forecasts are made.
    </div>
  </main>
</body>
</html>
"""
