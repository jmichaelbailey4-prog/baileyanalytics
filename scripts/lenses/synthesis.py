"""The synthesis / 'why' layer: connect the day's signals and explain each
mover — honestly. Pure functions of already-built brief data (no network, no
disk I/O), in the spirit of predictions/explain.py.

Honesty is the gating constraint (spec 2026-06-16-synthesis-why-layer §2). Three
signals, one wall:

  * mover_why     — DESCRIPTIVE. One mover's own series only (streak / fresh
                    extreme / outsized step). Never names another series, never
                    asserts a cause. -> INV-1.
  * cooccurrence  — STRUCTURAL. A count over theme-tagged pressure points. States
                    co-movement, never causation. -> INV-2.
  * relationships — RELATIONAL. Renders ONLY from a curated, tier-tagged map
                    (relationships.py); the grammar is gated by each edge's
                    strength so an empirical claim must hedge and a co-occurrence
                    claim may not assert. -> INV-3.

The causal-token / hedge-token linters below are the backbone of the honesty
tests — a template that violates an invariant fails CI.
"""

import statistics

from . import util

# --- honesty primitives ---------------------------------------------------

# Verbs/phrases that assert a specific causal mechanism. This is a HEURISTIC
# BACKSTOP, not a proof — and deliberately HIGH-PRECISION / LOW-RECALL: it catches
# the *unambiguous* causal phrasings with near-zero false positives, and leaves the
# subtle/semantic cases (e.g. "does the hedge actually govern the causal verb?") to
# the human review of the curated map AND an LLM honesty-reviewer at authoring time
# (a substring matcher structurally can't judge scope or grammar). We do NOT add
# ambiguous bare stems like "lower"/"cool"/"slow"/"raise"/"squeeze"/"erode" — those
# read as honest *descriptive* co-occurrence far more often than as a cause ("prices
# cooled while supply rose"), so flagging them would wrongly reject honest copy and
# push an author to mis-tier an edge. Two other deliberate non-entries:
#  * bare "fuel"/"fuels" — a domain noun the co-occurrence sentence names; we ban
#    only the verb participles "fueled"/"fueling".
#  * bare "as" — it is the *good* co-occurrence connector ("at the same time as").
CAUSAL_TOKENS = (
    # explicit causal connectives (unambiguous)
    "driv", "drove", "because", "due to", "caused", "causing", "causes", "cause of",
    "leads to", "led to", "leading to", "results in", "result of", "as a result",
    "thanks to", "owing to", "behind the", "on the back of", "blamed", "blame",
    "reason for", "responsible for", "a function of", "knock-on",
    # unambiguous transitive / passive causal phrases (multiword where a bare stem
    # would collide with honest descriptive copy)
    "fueled", "fueling", "fuelled", "fuelling", "spurred", "spurring", "pushes",
    "pushing", "pushed", "triggered", "triggering", "sparked", "sparking",
    "propelled", "lifted by", "boosted by", "weighed on", "weighs on", "weigh on",
    "weighs down", "weigh down", "dragged", "dragging", "drag on", "drag down",
    "eat into", "eats into", "eating into", "saps", "sapping", "props up", "prop up",
    "propped up", "pass through", "passes through", "passed through", "pass-through",
    "spill over", "spills over", "spilled over", "spills into", "ripple through",
    "ripples through", "rippled through", "translate into", "translates into",
    "translated into", "feed into", "feeds into", "feeds inflation", "stem from",
    "stems from", "chokes", "choking", "choke off", "juices", "juiced", "hammers",
    "hammered",
)

# Probability hedges that turn an empirical claim into an honest one. Kept narrow
# and unambiguous: everyday phrases with non-probabilistic readings ("can ",
# "over time", "in the past", "associated with") were removed — they let real
# causation pass AND wrongly tripped honest co-occurrence copy.
HEDGE_TOKENS = (
    "tend", "tends", "historically", "often", "typically", "usually",
    "has preceded", "have preceded", "on average",
)


def find_causal_tokens(text):
    """Causal tokens present in `text` (lowercased substring match)."""
    t = (text or "").lower()
    return [tok for tok in CAUSAL_TOKENS if tok in t]


def find_hedge_tokens(text):
    t = (text or "").lower()
    return [tok for tok in HEDGE_TOKENS if tok in t]


# --- signal helpers (over a numeric series) -------------------------------

MIN_STREAK = 3      # consecutive same-direction steps to count as a run
OUTSIZE_SIGMA = 2.0  # latest |step| vs prior-steps stdev to count as outsized


def _nums(values):
    return [float(v) for v in (values or []) if isinstance(v, (int, float))]


def _streak(values):
    """('up'|'down', n) for the trailing run of strictly same-sign steps, or
    None when shorter than MIN_STREAK. Mirrors predictions.explain.streak."""
    vals = _nums(values)
    if len(vals) < MIN_STREAK + 1:
        return None
    direction, n = None, 0
    for prev, cur in zip(reversed(vals[:-1]), reversed(vals[1:])):
        step = "up" if cur > prev else "down" if cur < prev else None
        if step is None or (direction and step != direction):
            break
        direction = step
        n += 1
    return (direction, n) if direction and n >= MIN_STREAK else None


def _fresh_extreme(values):
    """'high' / 'low' / None — whether the latest value is a fresh extreme of the
    shown series, reached by an actual up/down move (a flat tie is not 'fresh')."""
    vals = _nums(values)
    if len(vals) < 2:
        return None
    last = vals[-1]
    if last >= max(vals[:-1]) and last > vals[-2]:
        return "high"
    if last <= min(vals[:-1]) and last < vals[-2]:
        return "low"
    return None


def _outsized(values):
    """True when the latest step is large versus the variation of the prior
    steps (the same z-logic that makes a series a 'mover', surfaced as prose).
    Keep the volatility definition (pstdev of the PRIOR steps) aligned with
    brief.move_score, so the per-mover 'why' and the mover ranking agree on what
    counts as outsized."""
    vals = _nums(values)
    if len(vals) < 4:
        return False
    steps = [vals[i] - vals[i - 1] for i in range(1, len(vals))]
    latest = steps[-1]
    if latest == 0:
        return False
    prior = steps[:-1]
    vol = statistics.pstdev(prior)
    if vol == 0:  # a perfectly steady cadence: outsized iff the latest breaks it
        return latest != prior[-1]
    return abs(latest) / vol >= OUTSIZE_SIGMA


# --- signal 1: the per-mover / per-indicator 'why' (INV-1) -----------------
# mover_why (brief) and indicator_why (lens pages) share one body: streak /
# fresh-extreme / outsized over a SINGLE series, closed vocabulary out — so they
# structurally cannot name another series or assert a cause. They differ only in
# the window phrase: 'this view' where a chart is shown (the brief), 'recent
# readings' on the static #baked-read, which renders no chart for no-JS readers.

def _why_body(values, scope):
    """The shared self-grounded 'why' body for a numeric series. `scope` is the
    window phrase used wherever a claim is window-relative. '' when nothing clears
    the bar. A fresh extreme reached BY a streak needs no scope word (the streak
    already reads as recent); a fresh extreme without a streak is scoped."""
    vals = _nums(values)
    if len(vals) < MIN_STREAK + 1:
        return ""
    st = _streak(vals)
    ext = _fresh_extreme(vals)
    out = _outsized(vals)
    rising = vals[-1] > vals[-2]
    if st:
        direction, n = st
        lead = f"{direction} {n} readings in a row"
        if ext == "high" and direction == "up":
            return lead + ", to a fresh high"
        if ext == "low" and direction == "down":
            return lead + f", to its lowest in {scope}"
        if out:
            return lead + f" — its sharpest move in {scope}"
        return lead
    if ext == "high" and rising:
        return f"a fresh high in {scope}" + (f" — its sharpest jump in {scope}" if out else "")
    if ext == "low" and not rising:
        return f"its lowest in {scope}" + (f" — its sharpest drop in {scope}" if out else "")
    if out:
        return f"its sharpest {'jump' if rising else 'drop'} in {scope}"
    return ""


def _why_with_label(label, body):
    """Prefix the body with its stat/indicator label (the plural-agnostic colon
    convention from explain.py); capitalize when there is no label. '' stays ''."""
    if not body:
        return ""
    label = (label or "").strip()
    if label:
        return f"{label}: {body}."
    return body[0].upper() + body[1:] + "."


def mover_why(mover):
    """A one-line, self-grounded 'why' for a brief mover, from its OWN
    primary-indicator sparkline + stat label. '' = honest silence (INV-1)."""
    return _why_with_label(mover.get("stat_label"),
                           _why_body(mover.get("sparkline"), "this view"))


def indicator_why(label, values):
    """Lens-page sibling of mover_why: a self-grounded 'why' for ONE indicator's
    own recent observation values, with period-neutral wording for the static
    #baked-read (crawlers/no-JS see no chart 'view'). '' = honest silence (INV-1)."""
    return _why_with_label(label, _why_body(values, "recent readings"))


# --- signal 2: structural co-occurrence (INV-2) ---------------------------

# Theme tags group lenses by the SUBJECT they measure (a categorization,
# reviewable — NOT a causal edge). lens_id -> (theme, short colloquial noun).
# Conservative on purpose; unlisted lenses simply don't participate. Reviewed
# under DECISIONS-PENDING D5.
THEMES = {
    # the cost-of-living cluster: prices households pay
    "energy-oil-fuels": ("prices", "fuel"),
    "energy-natural-gas": ("prices", "natural gas"),
    "energy-electricity": ("prices", "electricity"),
    "energy-commodities": ("prices", "food and commodities"),
    "cost-of-living": ("prices", "overall inflation"),
    "housing-rent-shelter": ("prices", "rents"),
    # the housing-market cluster
    "housing-home-prices": ("housing-market", "home prices"),
    "housing-affordability": ("housing-market", "affordability"),
    "housing-supply-construction": ("housing-market", "housing supply"),
    # the credit cluster
    "consumer-credit": ("credit", "consumer credit"),
    "business-credit": ("credit", "business credit"),
    "bank-asset-quality": ("credit", "bank loan quality"),
    # the labor/earnings cluster: jobs and the income they produce (D5 follow-up,
    # 2026-06-16). income-savings sits here, not under "prices" — its SUBJECT is
    # earnings; the inflation->real-income link is a relationship edge, not a theme.
    "job-market": ("labor", "the job market"),
    "consumer-income-savings": ("labor", "household incomes"),
}
THEME_LABELS = {
    "prices": "the cost of living",
    "housing-market": "the housing market",
    "credit": "credit conditions",
    "labor": "jobs and incomes",
}
MIN_THEME = 2  # members needed before a cluster is worth a sentence

_SEV = {"watch": 1, "elevated": 2, "alert": 3}
_NUM = {2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight"}


def cooccurrence(pressure_rows):
    """One honest co-occurrence sentence: the largest theme-cluster among today's
    pressure points, named with a count. '' when no theme reaches MIN_THEME.
    A count over a shared subject — never a cause (INV-2). Deterministic."""
    clusters = {}
    for r in pressure_rows or []:
        meta = THEMES.get(r.get("lens_id"))
        if not meta:
            continue
        theme, noun = meta
        clusters.setdefault(theme, []).append((noun, _SEV.get(r.get("status"), 0)))
    best = None  # (rank_key, theme, nouns)
    for theme, members in clusters.items():
        if len(members) < MIN_THEME:
            continue
        # most members first, then most-severe, then theme name for a stable tie-break
        key = (len(members), sum(s for _, s in members))
        nouns = [n for n, _ in members]
        if best is None or key > best[0] or (key == best[0] and theme < best[1]):
            best = (key, theme, nouns)
    if not best:
        return ""
    _, theme, nouns = best
    count = _NUM.get(len(nouns), str(len(nouns)))
    label = THEME_LABELS.get(theme, theme)
    return f"{count} of today's pressure points are about {label} — {util.oxford_join(nouns)}."


# --- signal 3: the relationship engine (INV-3) ----------------------------
# Renders ONLY from the curated map in relationships.py — there is no path to a
# relational claim without a human-authored, tier-tagged edge. The grammar is
# gated by each edge's strength tier, which catches the common dishonest forms;
# the substring linter is a backstop, not a proof, so the map is also reviewed.

_TIERS = ("definitional", "empirical", "co-occurrence")


def relationship_sentence(edge):
    """Render one relationship edge to its sentence, enforcing the tier<->grammar
    invariant (INV-3). Raises ValueError when the authored link violates its tier
    (empirical without a hedge, or co-occurrence with a causal verb) — so the
    common dishonest forms fail loudly rather than shipping."""
    tier = edge.get("strength")
    link = edge.get("link", "")
    if tier not in _TIERS:
        raise ValueError(f"unknown relationship strength: {tier!r}")
    causal = bool(find_causal_tokens(link))
    hedged = bool(find_hedge_tokens(link))
    if tier == "empirical" and not hedged:
        raise ValueError(
            f"empirical relationship must hedge (e.g. 'historically'/'tends to'): {link!r}")
    if tier == "co-occurrence" and (causal or hedged):
        raise ValueError(
            f"co-occurrence relationship must state neither cause nor probability: {link!r}")
    return link


def active_keys(today_json):
    """The lens ids 'in play' today: anything under pressure, moving, or
    transitioning — the endpoints a relationship edge may connect."""
    keys = set()
    for r in today_json.get("pressure", []) or []:
        if r.get("lens_id"):
            keys.add(r["lens_id"])
    for m in today_json.get("top_moves", []) or []:
        if m.get("lens_id"):
            keys.add(m["lens_id"])
    for t in today_json.get("transitions", []) or []:
        if t.get("lens_id"):
            keys.add(t["lens_id"])
    return keys


def active_relationships(edges, active):
    """Edges whose BOTH endpoints are in play today."""
    return [e for e in edges if e.get("source") in active and e.get("target") in active]


def compose_relationships(edges, active, cap=1):
    """Up to `cap` honest relationship sentences for edges active today. []
    when none are active (quiet-day silence)."""
    out = []
    for e in active_relationships(edges, active):
        out.append(relationship_sentence(e))
        if len(out) >= cap:
            break
    return out


def _valid_lens_ids():
    """Every lens id the pipeline can emit — for the relationship-map integrity
    test (catches typos when the map is authored). Read-only import of config."""
    from . import config
    ids = {lens.id for cat in config.CATEGORIES for lens in cat.get("lenses", [])}
    ids.add("crypto-structure")  # built separately (build.build_crypto_lens)
    return ids
