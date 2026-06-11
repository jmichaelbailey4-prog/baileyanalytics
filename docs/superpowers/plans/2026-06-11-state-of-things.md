# The State of Things — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the consolidated current-state summary — an overall verdict (status token + one assembled plain-English sentence), Pressure Points, Holding Steady, and a Today's-Brief pointer — baked to `data/state/today.json` and rendered on three surfaces.

**Architecture:** A pure-synthesis module `scripts/lenses/state.py` (mirroring `brief.py`: data in → data out, no I/O) consumes the per-category `index.json` files plus the baked brief, and `refresh_lenses.py` wires it in after `refresh_brief` with content-aware writes. A shared client renderer `dashboards/state.js` fills a new `dashboards/state.html` page, a panel atop `dashboards/index.html`, and a one-line verdict on the home hero.

**Tech Stack:** Stdlib-only Python 3 + `unittest` (no third-party deps, no build step), hand-written HTML/CSS/JS. Spec: `docs/superpowers/specs/2026-06-11-state-of-things-design.md`.

**House rules that apply to every task:**
- Run all commands from the parent directory using absolute paths (never `cd <repo> &&`). Git: `git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" …`.
- The full test command is:
  `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"`
- Work happens on the existing `state-of-things` branch. Commit per task; **never push or merge** — Michael gates that.
- `refresh_lenses.py --dry-run` **overwrites `data/`** — only the final verification task runs it, followed by cleanup.

---

### Task 1: `util.status_score` — expose the un-banded RMS

The verdict needs the raw RMS both for the overall blend-of-blends and for ranking pressure categories. Extract the score from `status_blend` so there is exactly one RMS implementation.

**Files:**
- Modify: `scripts/lenses/util.py:71-89` (the `status_blend` function)
- Test: `scripts/tests/test_status_blend.py` (extend the existing file)

- [ ] **Step 1: Write the failing tests**

Append to `scripts/tests/test_status_blend.py` (inside the module, as a new TestCase class before the `if __name__` block if one exists, otherwise at the end):

```python
class TestStatusScore(unittest.TestCase):
    def test_empty_and_non_severity_is_none(self):
        self.assertIsNone(util.status_score([]))
        self.assertIsNone(util.status_score(["neutral", "info", "unknown"]))

    def test_known_values(self):
        self.assertEqual(util.status_score(["ok"]), 0.0)
        self.assertEqual(util.status_score(["alert"]), 3.0)
        self.assertAlmostEqual(util.status_score(["ok", "watch"]), 0.5 ** 0.5)
        # today's energy lenses: alert, ok, elevated, alert -> sqrt(22/4)
        self.assertAlmostEqual(util.status_score(["alert", "ok", "elevated", "alert"]),
                               (22 / 4) ** 0.5)

    def test_blend_is_banded_score(self):
        # status_blend must be exactly the banded status_score (one implementation).
        for statuses in (["ok"], ["ok", "watch"], ["alert", "ok", "ok", "ok"],
                         ["alert", "alert", "elevated", "elevated"]):
            score = util.status_score(statuses)
            expected = ("ok" if score < 0.6 else "watch" if score < 1.5
                        else "elevated" if score < 2.5 else "alert")
            self.assertEqual(util.status_blend(statuses), expected)
```

(Match the existing file's import style — it already does `from lenses import util` or similar; check the top of the file and reuse it.)

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_status_blend.py" -v`
Expected: the three new tests ERROR with `AttributeError: module 'lenses.util' has no attribute 'status_score'`; all pre-existing tests still pass.

- [ ] **Step 3: Implement `status_score` and refactor `status_blend`**

In `scripts/lenses/util.py`, replace the body of `status_blend` (keep its docstring verbatim) and insert `status_score` directly above it:

```python
def status_score(statuses):
    """The un-banded severity behind status_blend: the quadratic mean (RMS) of
    the severity values, ignoring neutral/info/unknown. None when nothing
    severity-graded is present."""
    sev = [STATUS_ORDER[s] for s in statuses if STATUS_ORDER.get(s, -1) >= 0]
    if not sev:
        return None
    return (sum(v * v for v in sev) / len(sev)) ** 0.5


def status_blend(statuses):
    """Category-level status: the quadratic mean (RMS) of lens severities, banded
    back to a token. Squaring makes bad readings count more than good ones offset,
    without letting a single stressed lens brand the whole category (that's the
    worst-lens callout's job on the home tile). One watch among four ok lenses
    stays ok (0.5 < 0.6); a category reads alert only when stress is broad
    (e.g. alert+alert+elevated+elevated ≈ 2.55). neutral/info/unknown are
    excluded; with no severity lenses at all the category is 'neutral'."""
    score = status_score(statuses)
    if score is None:
        return "neutral"
    if score < 0.6:
        return "ok"
    if score < 1.5:
        return "watch"
    if score < 2.5:
        return "elevated"
    return "alert"
```

- [ ] **Step 4: Run the full suite to verify everything passes**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"`
Expected: OK (~270+ tests, zero failures).

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/util.py scripts/tests/test_status_blend.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "refactor: expose status_score behind status_blend"
```

---

### Task 2: `state.py` — copy bank, `_join`, `classify_shape`

**Files:**
- Create: `scripts/lenses/state.py`
- Create: `scripts/tests/test_state.py`

- [ ] **Step 1: Write the failing tests**

Create `scripts/tests/test_state.py`:

```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import state  # noqa: E402


class TestJoin(unittest.TestCase):
    def test_join(self):
        self.assertEqual(state._join([]), "")
        self.assertEqual(state._join(["a"]), "a")
        self.assertEqual(state._join(["a", "b"]), "a and b")
        self.assertEqual(state._join(["a", "b", "c"]), "a, b, and c")


class TestClassifyShape(unittest.TestCase):
    def test_partition(self):
        self.assertEqual(state.classify_shape("alert", True), "broad-stress")
        self.assertEqual(state.classify_shape("elevated", True), "spreading-stress")
        self.assertEqual(state.classify_shape("elevated", False), "spreading-stress")
        self.assertEqual(state.classify_shape("watch", True), "contained-pressure")
        self.assertEqual(state.classify_shape("watch", False), "mixed-watch")
        self.assertEqual(state.classify_shape("ok", False), "all-clear")


class TestCopyBank(unittest.TestCase):
    CATEGORIES = ["economic", "consumer", "banking", "business",
                  "markets", "energy", "housing", "global"]

    def test_every_category_has_copy(self):
        for cid in self.CATEGORIES:
            self.assertIn(cid, state.NOUN)
            self.assertIn(cid, state.STEADY_CLAUSES)
            self.assertIn(cid, state.ANCHOR_PRIORITY)
            self.assertEqual(set(state.PRESSURE_CLAUSES[cid]), {"elevated", "alert"})

    def test_fragments_splice_cleanly(self):
        # Fragments are clauses: lowercase start, no terminal punctuation.
        frags = (list(state.NOUN.values()) + list(state.STEADY_CLAUSES.values())
                 + [c for d in state.PRESSURE_CLAUSES.values() for c in d.values()])
        for f in frags:
            self.assertFalse(f[0].isupper(), f)
            self.assertNotIn(f[-1], ".;,", f)

    def test_every_shape_has_three_variants(self):
        for shape in ("all-clear", "mixed-watch", "contained-pressure",
                      "spreading-stress", "broad-stress"):
            self.assertEqual(len(state.SKELETONS[shape]), 3)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_state.py" -v`
Expected: `ModuleNotFoundError`/`ImportError` (`lenses.state` does not exist).

- [ ] **Step 3: Create `scripts/lenses/state.py`**

```python
"""The State of Things: one consolidated read over the per-category indexes —
an overall verdict (status token + one assembled plain-English sentence),
pressure points, a holding-steady roll-up, and a pointer into Today's Brief.
Pure synthesis like brief.py — callers pass data in and get data out (no
network, no disk I/O). Editorial rules and the copy bank are specified in
docs/superpowers/specs/2026-06-11-state-of-things-design.md."""

import zlib
from datetime import datetime, timezone

from . import brief, config, util

PRESSURE_STATUSES = ("elevated", "alert")

# Display titles come from the pipeline's single source of truth.
TITLES = {c["id"]: c["title"] for c in config.CATEGORIES}

# --- Copy bank (reviewed by Michael with the spec; edit there first) ---

# Short noun phrases for naming a category mid-sentence (watch lists).
NOUN = {
    "economic": "the core economy",
    "consumer": "household finances",
    "banking": "the banks",
    "business": "business health",
    "markets": "markets",
    "energy": "energy costs",
    "housing": "housing",
    "global": "the global backdrop",
}

# Clause naming a category under pressure, keyed by its blended status. These
# describe the CATEGORY badge (the precise lens headlines appear verbatim in
# the Pressure Points block, so the sentence stays at category altitude).
PRESSURE_CLAUSES = {
    "economic": {"elevated": "the core economy is under real strain",
                 "alert": "the core economy is flashing serious warnings"},
    "consumer": {"elevated": "household finances are stretched thin",
                 "alert": "households are in real distress"},
    "banking": {"elevated": "cracks are showing in the banking system",
                "alert": "the banking system is under serious stress"},
    "business": {"elevated": "business health is deteriorating",
                 "alert": "corporate America is in real trouble"},
    "markets": {"elevated": "financial markets are under stress",
                "alert": "financial markets are in turmoil"},
    "energy": {"elevated": "energy and commodity costs are squeezing budgets",
               "alert": "energy and commodity costs are surging"},
    "housing": {"elevated": "the housing market is out of balance",
                "alert": "the housing market is in serious trouble"},
    "global": {"elevated": "the global backdrop is turning hostile",
               "alert": "the global economy is in serious stress"},
}

# Clause naming a steady category (the sentence's reassurance).
STEADY_CLAUSES = {
    "banking": "banks are solid",
    "markets": "markets are calm",
    "economic": "the core economy is steady",
    "business": "business health is holding up",
    "consumer": "households are keeping pace",
    "housing": "housing is balanced",
    "energy": "energy costs are behaving",
    "global": "the global backdrop is quiet",
}

# Most-reassuring-first order for picking the steady anchors named in the sentence.
ANCHOR_PRIORITY = ["banking", "markets", "economic", "business",
                   "consumer", "housing", "energy", "global"]

# Skeletons per shape, 3 rotating variants each. Slots: {p} pressure clauses,
# {a} anchor clause, {w} watch nouns ({thing}/{is}/{lone} agree in number).
# Shapes whose slot can be empty carry a fallback template; the rotation picks
# the variant, the data picks the template within it.
SKELETONS = {
    "all-clear": [
        {"watch": "The economy reads broadly healthy: {a}, with {w} the only {thing} worth watching.",
         "no_watch": "The economy reads broadly healthy: {a} — nothing on the board is flashing."},
        {"watch": "A calm read across the board — {a}; the only {thing} worth watching {is} {w}.",
         "no_watch": "A calm read across the board — {a}; nothing is flashing."},
        {"watch": "Most everything reads steady right now: {a}; {w} {is} {lone}.",
         "no_watch": "Most everything reads steady right now: {a}, with no watch items on the board."},
    ],
    "mixed-watch": [
        {"a": "Nothing is flashing red, but several corners bear watching — {w} — while {a}.",
         "no_a": "Nothing is flashing red, but several corners bear watching: {w}."},
        {"a": "A wait-and-see picture: {a}, but {w} all bear watching.",
         "no_a": "A wait-and-see picture: {w} all bear watching."},
        {"a": "Steady on the surface with caution underneath — {a}, while {w} warrant attention.",
         "no_a": "Caution across the board — {w} all warrant attention."},
    ],
    "contained-pressure": [
        {"a": "The economy is holding up, but not without strain: {p}, while {a}.",
         "no_a": "The economy is holding up, but not without strain — {p}, and the rest bears watching."},
        {"a": "Pressure is real but contained: {p}; meanwhile {a}.",
         "no_a": "Pressure is real but contained: {p}; the rest of the board bears watching."},
        {"a": "Most of the economy is on solid footing — {a} — but {p}.",
         "no_a": "Little of the board is fully in the clear — {p}, and the rest bears watching."},
    ],
    "spreading-stress": [
        {"a": "Stress is spreading: {p}; {a}.",
         "no_a": "Stress is spreading: {p}, and little of the board reads steady."},
        {"a": "The strain is no longer contained — {p} — and the steady list is getting shorter; for now {a}.",
         "no_a": "The strain is no longer contained — {p} — and the steady list has run out."},
        {"a": "More of the economy is under strain than not: {p}; the relative bright spots: {a}.",
         "no_a": "More of the economy is under strain than not: {p}, with no real bright spots."},
    ],
    "broad-stress": [
        {"p": "Serious stress across the economy: {p}."},
        {"p": "The board is mostly red — {p} — and safe harbors are scarce."},
        {"p": "A genuinely bad stretch: {p}, and almost nothing on the board reads steady."},
    ],
}


def _join(items):
    """Oxford-comma list join: a / a and b / a, b, and c."""
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def classify_shape(overall, has_pressure):
    """Map the overall token (+ whether any category is elevated/alert) to the
    sentence shape. Complete partition: overall ok mathematically excludes any
    pressure category (one elevated among eight already blends to watch)."""
    if overall == "alert":
        return "broad-stress"
    if overall == "elevated":
        return "spreading-stress"
    if overall == "watch":
        return "contained-pressure" if has_pressure else "mixed-watch"
    return "all-clear"
```

(The `zlib`/`datetime`/`brief`/`util` imports are used by Tasks 3–4; leaving them now avoids churn.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_state.py" -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Amend the spec with the new fallback templates**

While drafting the assembly it emerged that `contained-pressure` and `mixed-watch` can also occur with **zero ok categories** (e.g. elevated+watch+watch+watch → RMS ≈ 1.32 → watch), so the spec's "no-ok fallback" endings (previously only on spreading-stress) must exist for those shapes too. In `docs/superpowers/specs/2026-06-11-state-of-things-design.md`, section "Skeletons", update the **mixed-watch** and **contained-pressure** lists to include the `no_a` fallbacks exactly as written in the `SKELETONS` dict above (one ` / no-ok fallback: "…"` suffix per variant, same format the spreading-stress entries already use).

- [ ] **Step 6: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/state.py scripts/tests/test_state.py docs/superpowers/specs/2026-06-11-state-of-things-design.md
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat: state-of-things copy bank, shape classification (+ spec no-anchor fallbacks)"
```

---

### Task 3: `state.py` — sentence assembly and rotation

**Files:**
- Modify: `scripts/lenses/state.py` (append)
- Test: `scripts/tests/test_state.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `scripts/tests/test_state.py`:

```python
class TestVariant(unittest.TestCase):
    def test_deterministic_and_in_range(self):
        for shape in state.SKELETONS:
            v = state._variant("2026-06-11", shape)
            self.assertEqual(v, state._variant("2026-06-11", shape))
            self.assertIn(v, (0, 1, 2))

    def test_varies_across_dates(self):
        dates = [f"2026-06-{d:02d}" for d in range(1, 31)]
        variants = {state._variant(d, "all-clear") for d in dates}
        self.assertGreater(len(variants), 1)


class TestSentence(unittest.TestCase):
    P2 = ["energy and commodity costs are squeezing budgets",
          "household finances are stretched thin"]
    A = "banks are solid and markets are calm"

    def test_contained_with_anchor_every_variant(self):
        for v in range(3):
            s = state._sentence("contained-pressure", v, self.P2, self.A, [])
            self.assertIn(self.P2[0], s)
            self.assertIn(self.P2[1], s)
            self.assertIn(self.A, s)
            self.assertTrue(s[0].isupper())
            self.assertTrue(s.endswith("."))
            self.assertNotIn("..", s)

    def test_contained_without_anchor_falls_back(self):
        s = state._sentence("contained-pressure", 0, self.P2, "", [])
        self.assertIn("the rest bears watching", s)
        self.assertNotIn("{", s)

    def test_pressure_order_is_preserved(self):
        s = state._sentence("contained-pressure", 0, self.P2, self.A, [])
        self.assertLess(s.index(self.P2[0]), s.index(self.P2[1]))

    def test_broad_stress_uses_three_clauses(self):
        p3 = self.P2 + ["cracks are showing in the banking system"]
        s = state._sentence("broad-stress", 0, p3, "", [])
        for clause in p3:
            self.assertIn(clause, s)

    def test_all_clear_number_agreement(self):
        one = state._sentence("all-clear", 1, [], self.A, ["business health"])
        self.assertIn("the only thing worth watching is business health", one)
        two = state._sentence("all-clear", 1, [], self.A,
                              ["business health", "housing"])
        self.assertIn("the only things worth watching are business health and housing",
                      two)

    def test_all_clear_no_watch_ending(self):
        s = state._sentence("all-clear", 0, [], self.A, [])
        self.assertIn("nothing on the board is flashing", s)

    def test_mixed_watch_with_and_without_anchor(self):
        w = ["the core economy", "household finances", "housing"]
        with_a = state._sentence("mixed-watch", 0, [], self.A, w)
        self.assertIn("the core economy, household finances, and housing", with_a)
        self.assertIn(self.A, with_a)
        no_a = state._sentence("mixed-watch", 0, [], "", w)
        self.assertIn("bear watching", no_a)
        self.assertNotIn("{", no_a)

    def test_spreading_no_ok_fallback(self):
        s = state._sentence("spreading-stress", 0, self.P2, "", [])
        self.assertIn("little of the board reads steady", s)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_state.py" -v`
Expected: new tests ERROR with `AttributeError: … has no attribute '_variant'` (and `_sentence`); Task 2's tests still pass.

- [ ] **Step 3: Append the assembly functions to `scripts/lenses/state.py`**

```python
def _variant(iso_date, shape):
    """Deterministic daily rotation: same sentence all day (no intraday commit
    churn), varies across days, reproducible for any given date."""
    return zlib.crc32(iso_date.encode("utf-8")) % len(SKELETONS[shape])


def _sentence(shape, variant_idx, p_clauses, anchor, watch_nouns):
    """Fill the chosen skeleton. p_clauses/watch_nouns are ordered lists of
    lowercase fragments; anchor is a pre-joined clause ('' when no category is
    ok, which selects the variant's fallback template)."""
    tpl = SKELETONS[shape][variant_idx]
    p = _join(p_clauses)
    w = _join(watch_nouns)
    if shape == "broad-stress":
        return tpl["p"].format(p=p)
    if shape in ("contained-pressure", "spreading-stress"):
        return tpl["a"].format(p=p, a=anchor) if anchor else tpl["no_a"].format(p=p)
    if shape == "mixed-watch":
        return tpl["a"].format(w=w, a=anchor) if anchor else tpl["no_a"].format(w=w)
    # all-clear: an ok category always exists (RMS < 0.6 forces at least one 0),
    # so the anchor is never empty here — only the watch slot varies.
    if not watch_nouns:
        return tpl["no_watch"].format(a=anchor)
    n = len(watch_nouns)
    fields = {"a": anchor, "w": w,
              "thing": "thing" if n == 1 else "things",
              "is": "is" if n == 1 else "are",
              "lone": "the lone watch item" if n == 1 else "the watch items"}
    return tpl["watch"].format(**fields)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_state.py" -v`
Expected: PASS (all tests so far).

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/state.py scripts/tests/test_state.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat: state-of-things sentence assembly with daily rotation"
```

---

### Task 4: `state.py` — `build_state`

**Files:**
- Modify: `scripts/lenses/state.py` (append)
- Test: `scripts/tests/test_state.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `scripts/tests/test_state.py`:

```python
def cat_index(lens_statuses, *, status=None, prefix="lens"):
    """Minimal category index: one lens per status, optional baked blend."""
    lenses = [{"id": f"{prefix}-{i}", "title": f"Lens {i}", "status": s,
               "headline_read": f"Read {i}."} for i, s in enumerate(lens_statuses)]
    out = {"last_updated": "2026-06-11T00:00:00Z", "lenses": lenses}
    if status is not None:
        out["status"] = status
    return out


def todays_indices():
    """Mirror of the real 2026-06-11 data: energy/consumer elevated, three
    watch, three ok. Energy's lens mix (two alerts) outscores consumer's one."""
    return {
        "economic": cat_index(["ok", "ok", "ok", "elevated", "elevated"],
                              status="watch", prefix="economic"),
        "consumer": cat_index(["ok", "watch", "elevated", "alert"],
                              status="elevated", prefix="consumer"),
        "banking": cat_index(["ok", "ok", "ok", "watch"], status="ok", prefix="bank"),
        "business": cat_index(["ok", "ok", "ok", "watch"], status="ok", prefix="business"),
        "markets": cat_index(["ok", "neutral", "ok", "neutral"], status="ok", prefix="market"),
        "energy": cat_index(["alert", "ok", "elevated", "alert"],
                            status="elevated", prefix="energy"),
        "housing": cat_index(["ok", "elevated", "elevated", "ok"],
                             status="watch", prefix="housing"),
        "global": cat_index(["ok", "ok", "elevated", "elevated"],
                            status="watch", prefix="global"),
    }


class TestBuildState(unittest.TestCase):
    def build(self, indices, brief_today=None):
        orig = state._now
        state._now = lambda: "2026-06-11T12:00:00Z"
        try:
            return state.build_state(indices, brief_today)
        finally:
            state._now = orig

    def test_todays_picture(self):
        out = self.build(todays_indices(), {"transitions": [1, 2]})
        self.assertEqual(out["verdict"]["status"], "watch")
        self.assertEqual(out["verdict"]["shape"], "contained-pressure")
        s = out["verdict"]["sentence"]
        # Energy (RMS 2.35) outranks consumer (1.87); both clauses present, in order.
        e = "energy and commodity costs are squeezing budgets"
        c = "household finances are stretched thin"
        self.assertIn(e, s)
        self.assertIn(c, s)
        self.assertLess(s.index(e), s.index(c))
        self.assertIn("banks are solid", s)  # top anchor by priority
        self.assertEqual([p["category"] for p in out["pressure_points"]],
                         ["energy", "consumer"])
        # Steady: watch categories first (canonical order), then the rest.
        self.assertEqual([c_["category"] for c_ in out["steady"]],
                         ["economic", "housing", "global", "banking", "business", "markets"])
        self.assertEqual(out["changed"], {"transitions": 2,
                                          "href": "/dashboards/brief.html"})
        self.assertEqual(len(out["categories"]), 8)
        self.assertEqual(out["categories"][0]["href"], "/dashboards/economic/")

    def test_pressure_lens_cards(self):
        out = self.build(todays_indices())
        energy = out["pressure_points"][0]
        self.assertEqual(energy["title"], "Energy & Commodities")
        self.assertEqual(energy["href"], "/dashboards/energy/")
        lenses = energy["lenses"]
        self.assertEqual(len(lenses), 2)  # capped, worst first
        self.assertEqual([l["status"] for l in lenses], ["alert", "alert"])
        self.assertEqual(lenses[0]["headline"], "Read 0.")
        self.assertEqual(lenses[0]["href"], "/dashboards/energy/0.html")

    def test_blend_falls_back_when_index_has_no_status(self):
        indices = todays_indices()
        del indices["energy"]["status"]  # stale/fixture-style index
        out = self.build(indices)
        # recomputed from lenses: sqrt(22/4) ~ 2.35 -> elevated, still ranked first
        self.assertEqual(out["pressure_points"][0]["category"], "energy")
        self.assertEqual(out["pressure_points"][0]["status"], "elevated")

    def test_clause_cap_contained_is_two_but_block_shows_three(self):
        indices = todays_indices()
        indices["housing"] = cat_index(["elevated", "elevated", "ok", "ok"],
                                       status="elevated", prefix="housing")
        out = self.build(indices)
        self.assertEqual(out["verdict"]["shape"], "contained-pressure")
        self.assertEqual(len(out["pressure_points"]), 3)
        # housing (RMS 1.41) ranks below energy and consumer -> not in the sentence
        self.assertNotIn("housing market", out["verdict"]["sentence"])

    def test_rank_tie_falls_to_canonical_order(self):
        indices = {
            "economic": cat_index(["ok"], status="ok", prefix="economic"),
            "consumer": cat_index(["elevated"], status="elevated", prefix="consumer"),
            "banking": cat_index(["ok"], status="ok", prefix="bank"),
            "energy": cat_index(["elevated"], status="elevated", prefix="energy"),
        }
        out = self.build(indices)
        # equal RMS (2.0) -> brief.CATEGORIES order: consumer before energy
        self.assertEqual([p["category"] for p in out["pressure_points"]],
                         ["consumer", "energy"])

    def test_insufficient_categories(self):
        indices = {"economic": cat_index(["ok"], status="ok"),
                   "energy": cat_index(["alert"], status="alert")}
        out = self.build(indices, {"transitions": []})
        self.assertEqual(out["verdict"]["status"], "unknown")
        self.assertEqual(out["verdict"]["shape"], "insufficient")
        self.assertEqual(out["pressure_points"], [])
        self.assertEqual(len(out["categories"]), 2)
        self.assertEqual(out["changed"]["transitions"], 0)

    def test_missing_brief_omits_changed(self):
        out = self.build(todays_indices(), None)
        self.assertNotIn("changed", out)

    def test_missing_copy_degrades_not_crashes(self):
        saved = state.PRESSURE_CLAUSES.pop("energy")
        try:
            out = self.build(todays_indices())
            self.assertIn("energy costs is under real stress",
                          out["verdict"]["sentence"])
        finally:
            state.PRESSURE_CLAUSES["energy"] = saved

    def test_all_ok_is_all_clear(self):
        indices = {cid: cat_index(["ok", "ok"], status="ok", prefix=cid)
                   for cid in ["economic", "consumer", "banking", "business",
                               "markets", "energy", "housing", "global"]}
        out = self.build(indices)
        self.assertEqual(out["verdict"]["status"], "ok")
        self.assertEqual(out["verdict"]["shape"], "all-clear")
        self.assertEqual(out["pressure_points"], [])
        self.assertEqual(len(out["steady"]), 8)
```

Note on `test_missing_copy_degrades_not_crashes`: the expected generic clause is
`"energy costs is under real stress"` — the fallback concatenates the noun
phrase with a fixed verb phrase and accepts imperfect agreement in this
never-should-happen path (a new category whose copy wasn't authored yet).

Note on `test_pressure_lens_cards`: lens ids are `energy-0`, `energy-1`, … and
`brief.lens_href("energy", "energy-0")` strips the category prefix →
`/dashboards/energy/0.html`. The href value looks odd but proves the shared
slug logic is used.

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_state.py" -v`
Expected: new tests ERROR with `AttributeError: … has no attribute 'build_state'`.

- [ ] **Step 3: Append `build_state` to `scripts/lenses/state.py`**

```python
MIN_CATEGORIES = 4
INSUFFICIENT_SENTENCE = "Not enough data to read the overall picture right now."
PRESSURE_CAP = 3          # categories in the Pressure Points block
LENSES_PER_PRESSURE = 2   # worst lenses quoted per pressure category
CLAUSE_CAP = {"contained-pressure": 2, "spreading-stress": 3, "broad-stress": 3}
ANCHOR_CAP = 2            # steady clauses named in the sentence
WATCH_NOUN_CAP = 4        # watch categories named in mixed-watch sentences
BRIEF_HREF = "/dashboards/brief.html"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _categories(category_indices):
    """Flatten {category: index_json} into canonical-order records. The blend
    is recomputed from lens statuses when an index lacks the baked category
    status (stale index or fixture) — mirrors the home page's fallback."""
    cats = []
    for cid in brief.CATEGORIES:
        index = category_indices.get(cid)
        if not index:
            continue
        lenses = [l for l in index.get("lenses", []) if l.get("id")]
        statuses = [l.get("status", "unknown") for l in lenses]
        cats.append({
            "category": cid,
            "title": TITLES.get(cid, cid),
            "status": index.get("status") or util.status_blend(statuses),
            "href": f"/dashboards/{cid}/",
            "score": util.status_score(statuses) or 0.0,
            "lenses": lenses,
        })
    return cats


def _public(cat):
    return {"category": cat["category"], "title": cat["title"],
            "status": cat["status"], "href": cat["href"]}


def _worst_lenses(cat):
    """The lens cards a pressure category wears: worst first, capped, with the
    verbatim headline_read and the shared slug logic for hrefs."""
    sev = [l for l in cat["lenses"] if util.STATUS_ORDER.get(l.get("status"), -1) >= 0]
    sev.sort(key=lambda l: -util.STATUS_ORDER[l["status"]])  # stable: config order ties
    return [{"id": l["id"], "title": l.get("title", ""), "status": l["status"],
             "headline": l.get("headline_read", ""),
             "href": brief.lens_href(cat["category"], l["id"])}
            for l in sev[:LENSES_PER_PRESSURE]]


def _steady(cats, pressure_ids):
    """Everything not under pressure — watch first (most interesting), then the
    rest, canonical order within each group."""
    rest = [c for c in cats if c["category"] not in pressure_ids]
    return ([_public(c) for c in rest if c["status"] == "watch"]
            + [_public(c) for c in rest if c["status"] != "watch"])


def _pressure_clause(cat):
    clause = PRESSURE_CLAUSES.get(cat["category"], {}).get(cat["status"])
    # Unauthored copy (a brand-new category) degrades to generic copy, never a crash.
    return clause or f"{NOUN.get(cat['category'], cat['title'].lower())} is under real stress"


def _steady_clause(cat):
    return (STEADY_CLAUSES.get(cat["category"])
            or f"{NOUN.get(cat['category'], cat['title'].lower())} is steady")


def build_state(category_indices, brief_today):
    """Assemble the State of Things JSON from per-category index data and
    today's brief (or None). Pure — no network, no disk I/O."""
    generated = _now()
    cats = _categories(category_indices)
    overall = util.status_blend([c["status"] for c in cats])

    if len(cats) < MIN_CATEGORIES or overall not in brief.SEVERITY:
        out = {"generated_at": generated,
               "verdict": {"status": "unknown", "shape": "insufficient",
                           "sentence": INSUFFICIENT_SENTENCE},
               "pressure_points": [],
               "steady": _steady(cats, set())}
    else:
        pressure = sorted([c for c in cats if c["status"] in PRESSURE_STATUSES],
                          key=lambda c: -c["score"])[:PRESSURE_CAP]
        shape = classify_shape(overall, bool(pressure))
        by_id = {c["category"]: c for c in cats}
        anchors = [cid for cid in ANCHOR_PRIORITY
                   if cid in by_id and by_id[cid]["status"] == "ok"][:ANCHOR_CAP]
        anchor = _join([_steady_clause(by_id[cid]) for cid in anchors])
        p_clauses = [_pressure_clause(c) for c in pressure[:CLAUSE_CAP.get(shape, 0)]]
        watch_nouns = [NOUN.get(c["category"], c["title"].lower())
                       for c in cats if c["status"] == "watch"][:WATCH_NOUN_CAP]
        sentence = _sentence(shape, _variant(generated[:10], shape),
                             p_clauses, anchor, watch_nouns)
        out = {"generated_at": generated,
               "verdict": {"status": overall, "shape": shape, "sentence": sentence},
               "pressure_points": [dict(_public(c), lenses=_worst_lenses(c))
                                   for c in pressure],
               "steady": _steady(cats, {c["category"] for c in pressure})}
    if brief_today and isinstance(brief_today.get("transitions"), list):
        out["changed"] = {"transitions": len(brief_today["transitions"]),
                         "href": BRIEF_HREF}
    out["categories"] = [_public(c) for c in cats]
    return out
```

- [ ] **Step 4: Run the full suite**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"`
Expected: OK, zero failures.

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/state.py scripts/tests/test_state.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat: build_state — verdict, pressure points, steady roll-up, changed link"
```

---

### Task 5: Extend the brief fixture to 6 categories

The dry-run path feeds `build_state` from `brief_indices_sample.json`, which has only 3 categories — below `MIN_CATEGORIES`, so dry-run would always produce the degraded "insufficient" verdict. Extend it to 6. The added lenses use **flat 4-point sparklines** (`move_score` returns `None`) and ids absent from any seeded prior state, so existing brief tests are unaffected. The added indices deliberately omit the top-level `status` key (like the existing entries) — they exercise `build_state`'s blend fallback.

**Files:**
- Modify: `scripts/tests/fixtures/brief_indices_sample.json`

- [ ] **Step 1: Replace the fixture content**

Replace the whole file with (the first three categories are unchanged):

```json
{
  "economic": {
    "last_updated": "2026-06-10T13:00:00Z",
    "lenses": [
      {"id": "recession-watch", "title": "Recession Watch", "accent": "#F87171",
       "status": "ok", "headline_read": "The economy looks steady.",
       "key_stats": [{"k": "Yield curve", "v": "0.40%", "d": "0.04%", "dir": "up"}],
       "sparkline": [0.30, 0.36, 0.30, 0.36, 0.40]},
      {"id": "fiscal-health", "title": "Fiscal Health", "accent": "#F87171",
       "status": "elevated", "headline_read": "Debt and interest costs are climbing.",
       "key_stats": [{"k": "Debt-to-GDP", "v": "124.50%", "d": "13.50%", "dir": "up"}],
       "sparkline": [110.0, 111.0, 110.0, 111.0, 124.5]}
    ]
  },
  "markets": {
    "last_updated": "2026-06-10T13:00:00Z",
    "lenses": [
      {"id": "crypto-structure", "title": "Crypto Market Structure", "accent": "#818CF8",
       "status": "neutral", "headline_read": "Bitcoin dominance is rising.",
       "key_stats": [{"k": "BTC dominance", "v": "56.00%", "d": "5.00%", "dir": "up"}],
       "sparkline": [50.0, 51.0, 50.0, 51.0, 56.0]}
    ]
  },
  "consumer": {
    "last_updated": "2026-06-10T13:00:00Z",
    "lenses": [
      {"id": "consumer-sentiment", "title": "Consumer Sentiment", "accent": "#E879F9",
       "status": "watch", "headline_read": "Confidence is softening.",
       "key_stats": [{"k": "Sentiment", "v": "61.00", "d": "1.50", "dir": "down"}],
       "sparkline": [63.0, 62.5, 63.0, 62.5, 61.0]}
    ]
  },
  "banking": {
    "last_updated": "2026-06-10T13:00:00Z",
    "lenses": [
      {"id": "bank-asset-quality", "title": "Asset Quality", "accent": "#FBBF24",
       "status": "ok", "headline_read": "Bank loan quality is strong.",
       "key_stats": [{"k": "Noncurrent rate", "v": "0.90%", "d": "0.02%", "dir": "down"}],
       "sparkline": [0.9, 0.9, 0.9, 0.9]},
      {"id": "bank-profitability", "title": "Bank Profitability", "accent": "#FBBF24",
       "status": "ok", "headline_read": "Banks are solidly profitable.",
       "key_stats": [{"k": "ROA", "v": "1.20%", "d": "0.01%", "dir": "up"}],
       "sparkline": [1.2, 1.2, 1.2, 1.2]}
    ]
  },
  "energy": {
    "last_updated": "2026-06-10T13:00:00Z",
    "lenses": [
      {"id": "energy-oil-fuels", "title": "Oil & Fuels", "accent": "#FB923C",
       "status": "alert", "headline_read": "Fuel costs are spiking.",
       "key_stats": [{"k": "Gasoline", "v": "$4.10", "d": "$0.30", "dir": "up"}],
       "sparkline": [4.1, 4.1, 4.1, 4.1]},
      {"id": "energy-natural-gas", "title": "Natural Gas", "accent": "#FB923C",
       "status": "ok", "headline_read": "Natural gas costs are stable.",
       "key_stats": [{"k": "Henry Hub", "v": "$2.90", "d": "$0.01", "dir": "down"}],
       "sparkline": [2.9, 2.9, 2.9, 2.9]}
    ]
  },
  "housing": {
    "last_updated": "2026-06-10T13:00:00Z",
    "lenses": [
      {"id": "housing-home-prices", "title": "Home-Price Stability", "accent": "#F472B6",
       "status": "ok", "headline_read": "The housing market looks balanced.",
       "key_stats": [{"k": "Case-Shiller YoY", "v": "3.10%", "d": "0.10%", "dir": "down"}],
       "sparkline": [3.1, 3.1, 3.1, 3.1]}
    ]
  }
}
```

Resulting dry-run state (worth knowing for Task 6's tests): blends are economic watch (√(4/2)≈1.41), markets neutral (excluded), consumer watch, banking ok, energy **elevated** (√(9/2)≈2.12), housing ok → 6 present ≥ 4; overall √(6/5)≈1.10 → **watch**; shape **contained-pressure**; pressure = [energy]; anchors = banking, housing → "banks are solid and housing is balanced".

- [ ] **Step 2: Run the full suite to confirm existing brief/feed tests still pass**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"`
Expected: OK. If a brief/feed test fails on counts, it means it asserted exact `status_counts` — fix the test's expectation, not the fixture (the new lenses are flat-sparkline and transition-free by construction).

- [ ] **Step 3: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/tests/fixtures/brief_indices_sample.json
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "test: extend brief fixture to six categories for state dry-runs"
```

---

### Task 6: Wire `--state` into `refresh_lenses.py`

**Files:**
- Modify: `scripts/refresh_lenses.py` (import at line 18, constants near line 38, functions near `refresh_brief` at line 640, CLI in `main` at lines 674-737)
- Create: `scripts/tests/test_refresh_state.py`

- [ ] **Step 1: Write the failing tests**

Create `scripts/tests/test_refresh_state.py` (mirrors `test_refresh_brief.py`):

```python
import sys
import json
import pathlib
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses


class TestStateDryRun(unittest.TestCase):
    def setUp(self):
        # Redirect output dirs so tests never touch real repo files; the brief
        # dir is redirected too because refresh_state reads today.json from it.
        self._td = tempfile.TemporaryDirectory()
        tmp = pathlib.Path(self._td.name)
        self._orig_state = refresh_lenses.STATE_OUT_DIR
        self._orig_brief = refresh_lenses.BRIEF_OUT_DIR
        self._orig_feed = refresh_lenses.FEED_PATH
        refresh_lenses.STATE_OUT_DIR = tmp / "state"
        refresh_lenses.BRIEF_OUT_DIR = tmp / "brief"
        refresh_lenses.FEED_PATH = tmp / "feed.xml"

    def tearDown(self):
        refresh_lenses.STATE_OUT_DIR = self._orig_state
        refresh_lenses.BRIEF_OUT_DIR = self._orig_brief
        refresh_lenses.FEED_PATH = self._orig_feed
        self._td.cleanup()

    def read_today(self):
        return json.loads((refresh_lenses.STATE_OUT_DIR / "today.json")
                          .read_text(encoding="utf-8"))

    def test_state_flag_writes_today(self):
        rc = refresh_lenses.main(["--state", "--dry-run"])
        self.assertEqual(rc, 0)
        today = self.read_today()
        self.assertEqual(today["verdict"]["status"], "watch")
        self.assertEqual(today["verdict"]["shape"], "contained-pressure")
        self.assertEqual([p["category"] for p in today["pressure_points"]], ["energy"])
        self.assertIn("energy and commodity costs are squeezing budgets",
                      today["verdict"]["sentence"])
        # no brief written by --state alone -> changed block absent
        self.assertNotIn("changed", today)

    def test_state_after_brief_carries_transition_count(self):
        refresh_lenses.main(["--brief", "--dry-run"])
        refresh_lenses.main(["--state", "--dry-run"])
        today = self.read_today()
        self.assertIn("changed", today)
        self.assertEqual(today["changed"]["href"], "/dashboards/brief.html")
        self.assertIsInstance(today["changed"]["transitions"], int)

    def test_unchanged_rerun_does_not_rewrite(self):
        import itertools
        stamps = (f"2026-06-10T00:00:{n:02d}Z" for n in itertools.count(1))
        orig_now = refresh_lenses.state._now
        refresh_lenses.state._now = lambda: next(stamps)
        try:
            refresh_lenses.main(["--state", "--dry-run"])
            first = (refresh_lenses.STATE_OUT_DIR / "today.json").read_text(encoding="utf-8")
            refresh_lenses.main(["--state", "--dry-run"])
            second = (refresh_lenses.STATE_OUT_DIR / "today.json").read_text(encoding="utf-8")
        finally:
            refresh_lenses.state._now = orig_now
        self.assertEqual(first, second)

    def test_failure_keeps_previous_file(self):
        refresh_lenses.main(["--state", "--dry-run"])
        before = (refresh_lenses.STATE_OUT_DIR / "today.json").read_text(encoding="utf-8")
        orig = refresh_lenses.state.build_state
        refresh_lenses.state.build_state = lambda *a: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            rc = refresh_lenses.main(["--state", "--dry-run"])
        finally:
            refresh_lenses.state.build_state = orig
        self.assertEqual(rc, 0)  # a state failure never breaks the run
        after = (refresh_lenses.STATE_OUT_DIR / "today.json").read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_full_dry_run_includes_state(self):
        # No flag = everything; the brief+state tail must both run.
        rc = refresh_lenses.main(["--brief", "--state", "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertTrue((refresh_lenses.STATE_OUT_DIR / "today.json").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_refresh_state.py" -v`
Expected: ERROR — `AttributeError: module 'refresh_lenses' has no attribute 'STATE_OUT_DIR'`.

- [ ] **Step 3: Implement the wiring**

In `scripts/refresh_lenses.py`:

a) Line 18, add `state` to the package import (keep alphabetical):
```python
from lenses import brief, build, coingecko, config, eia, epu, fdic, feed, fred, imf, nyfed, state, util, yahoo
```

b) Next to `BRIEF_OUT_DIR` (line 38), add:
```python
STATE_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "state"
```

c) After `refresh_brief` (line 672), add:
```python
def _load_brief_today():
    path = BRIEF_OUT_DIR / "today.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return None


def refresh_state(dry_run):
    """Build + write data/state/today.json (The State of Things) from the
    per-category index.json files plus today's brief. Additive — never raises;
    runs after refresh_brief so the 'what changed' count is fresh."""
    try:
        indices = _load_brief_indices(dry_run)
        today = state.build_state(indices, _load_brief_today())
        wrote = build.write_lens_file(STATE_OUT_DIR / "today.json", today)
        print(f"Wrote {STATE_OUT_DIR / 'today.json'}" if wrote
              else "No state changes — The State of Things is up to date.")
    except Exception as exc:  # noqa: BLE001 - never break the run on a state failure
        print(f"WARN: state build failed ({exc}); keeping previous state", file=sys.stderr)
```

d) In `main`: add the flag after `--brief` (line 687):
```python
    parser.add_argument("--state", action="store_true",
                        help="rebuild only The State of Things from existing indices")
```
extend `any_flag` (line 692-693) with `or args.state`, add
```python
    do_state = args.state or not any_flag
```
next to `do_brief`, and after the `if do_brief:` block (line 735-736) add:
```python
    if do_state:
        refresh_state(args.dry_run)
```

- [ ] **Step 4: Run the full suite**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"`
Expected: OK, zero failures.

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/refresh_lenses.py scripts/tests/test_refresh_state.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat: --state flag bakes data/state/today.json after the brief"
```

---

### Task 7: Workflow steps

**Files:**
- Modify: `.github/workflows/refresh-fred.yml:74-76` (after the brief step)
- Modify: `.github/workflows/refresh-banking.yml:32-33` (after the brief step)

- [ ] **Step 1: Add the state step to both workflows**

In `refresh-fred.yml`, after the "Rebuild Today's Brief" step (the commit step's `git add data/` already covers `data/state/`):

```yaml
      - name: Rebuild The State of Things (no network)
        if: ${{ success() || failure() }}
        run: python scripts/refresh_lenses.py --state
```

In `refresh-banking.yml`, the same block after its `--brief` step.

- [ ] **Step 2: Sanity-check the YAML**

Run: `python -c "import pathlib; [print(p, 'ok') for p in ['.github/workflows/refresh-fred.yml', '.github/workflows/refresh-banking.yml'] if pathlib.Path('C:/Users/jmich/Documents/Business/Repositories/baileyanalytics', p).read_text(encoding='utf-8').count('--state') == 1]"`
Expected: both paths print `ok`. (No YAML lib in stdlib — indentation must match the sibling steps exactly: 6 spaces before `- name:`.)

- [ ] **Step 3: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add .github/workflows/refresh-fred.yml .github/workflows/refresh-banking.yml
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "ci: rebuild The State of Things after the brief in both refresh workflows"
```

---

### Task 8: `dashboards/state.js` + `lens.css` styles

No JS test framework exists in this repo (zero-build convention) — these are verified manually in Task 12.

**Files:**
- Create: `dashboards/state.js`
- Modify: `dashboards/lens.css` (append)

- [ ] **Step 1: Create `dashboards/state.js`**

```javascript
/* Shared renderer for The State of Things.
   loadState("state-panel", { mode: "panel" }) -> hub strip (badge + sentence + link)
   loadState("state-line",  { mode: "line" })  -> home one-liner (the element IS the link;
                                                  uses the home page's .pill badge classes)
   loadState(null,          { mode: "page" })  -> fills the state.html sections */
(function () {
  function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

  function verdict(v, badgeClass, withLink) {
    return `<span class="${badgeClass} ${esc(v.status)}">${esc(v.status)}</span>
      <span class="state-sentence">${esc(v.sentence)}</span>` +
      (withLink ? ` <a class="state-link" href="/dashboards/state.html">The full picture &rarr;</a>` : "");
  }

  function pressureCard(p) {
    const lenses = (p.lenses || []).map(l => `
      <a class="state-lens" href="${l.href}">
        <span class="badge ${esc(l.status)}">${esc(l.status)}</span>
        <span class="state-lens-title">${esc(l.title)}</span>
        <span class="state-lens-read">${esc(l.headline)}</span></a>`).join("");
    return `<div class="state-card">
      <a class="state-cat" href="${p.href}">${esc(p.title)}
        <span class="badge ${esc(p.status)}">${esc(p.status)}</span></a>${lenses}</div>`;
  }

  function steadyChip(c) {
    return `<a class="state-steady" href="${c.href}">
      <span class="badge ${esc(c.status)}">${esc(c.status)}</span>${esc(c.title)}</a>`;
  }

  function renderPage(data) {
    document.getElementById("verdict").innerHTML =
      `<div class="state-verdict">${verdict(data.verdict, "badge", false)}</div>`;
    const stamp = data.generated_at && new Date(data.generated_at);
    if (stamp && !isNaN(stamp)) {
      document.getElementById("asof").textContent = "As of " +
        stamp.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
    }
    const pp = data.pressure_points || [];
    if (pp.length) {
      document.getElementById("pressure-sec").hidden = false;
      document.getElementById("pressure").innerHTML = pp.map(pressureCard).join("");
    }
    const st = data.steady || [];
    if (st.length) {
      document.getElementById("steady-sec").hidden = false;
      document.getElementById("steady").innerHTML = st.map(steadyChip).join("");
    }
    if (data.changed) {
      const n = Number(data.changed.transitions);
      document.getElementById("changed-sec").hidden = false;
      document.getElementById("changed").innerHTML = n
        ? `<a class="state-link" href="${esc(data.changed.href)}">${n} lens${n === 1 ? "" : "es"} changed status today — see Today&rsquo;s Brief &rarr;</a>`
        : `Quiet day — no status changes. <a class="state-link" href="${esc(data.changed.href)}">Today&rsquo;s Brief &rarr;</a>`;
    }
  }

  window.loadState = async function (elId, opts) {
    opts = opts || {};
    const el = elId ? document.getElementById(elId) : null;
    if (elId && !el) return;
    try {
      const res = await fetch("/data/state/today.json", { cache: "no-cache" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      if (!data.verdict || !data.verdict.sentence) throw new Error("no verdict");
      if (opts.mode === "page") { renderPage(data); return; }
      el.innerHTML = opts.mode === "line"
        ? verdict(data.verdict, "pill", false)
        : `<div class="state-verdict">${verdict(data.verdict, "badge", true)}</div>`;
      el.hidden = false;
    } catch (err) {
      // The state is additive — never block the page it sits on.
      if (opts.mode === "page") {
        document.getElementById("verdict").innerHTML =
          `<div class="status-msg error">The State of Things is still being refreshed. Check back shortly.</div>`;
      } else if (el) {
        el.hidden = true;
      }
      console.error(err);
    }
  };
})();
```

- [ ] **Step 2: Append the styles to `dashboards/lens.css`**

```css
/* --- The State of Things (panel, page cards, steady chips) --- */
.state-panel{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:1rem 1.15rem;margin-bottom:1.5rem}
.state-verdict{display:flex;align-items:baseline;gap:.7rem;flex-wrap:wrap}
.state-sentence{font-size:1.02rem;font-weight:600;line-height:1.45}
.state-link{color:var(--blue);text-decoration:none;font-size:.85rem;white-space:nowrap}
.state-link:hover{text-decoration:underline}
.state-card{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:1rem 1.15rem;margin-bottom:.85rem}
.state-cat{display:flex;align-items:center;gap:.6rem;font-weight:600;font-size:1.05rem;color:var(--text);text-decoration:none;margin-bottom:.55rem}
.state-cat:hover{color:var(--blue)}
.state-lens{display:flex;align-items:baseline;gap:.6rem;flex-wrap:wrap;padding:.35rem 0;color:var(--text);text-decoration:none}
.state-lens:hover .state-lens-read{text-decoration:underline}
.state-lens-title{color:var(--muted);font-size:.85rem;flex:none}
.state-lens-read{font-size:.95rem}
.state-steady{display:inline-flex;align-items:center;gap:.5rem;background:var(--panel);border:1px solid var(--border);border-radius:999px;padding:.4rem .9rem;margin:0 .5rem .5rem 0;color:var(--text);text-decoration:none;font-size:.9rem}
.state-steady:hover{border-color:var(--blue)}
```

- [ ] **Step 3: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/state.js dashboards/lens.css
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat: shared State of Things renderer and styles"
```

---

### Task 9: `dashboards/state.html` — the full page

**Files:**
- Create: `dashboards/state.html`

- [ ] **Step 1: Create the page** (conventions mirror `dashboards/brief.html`):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The State of Things — Bailey Analytics</title>
  <meta name="description" content="Where things stand across the U.S. economy right now — one overall verdict, the pressure points behind it, what's holding steady, and what changed today.">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Bailey Analytics">
  <meta property="og:title" content="The State of Things — Bailey Analytics">
  <meta property="og:description" content="Where things stand across the U.S. economy right now — one overall verdict, the pressure points behind it, what's holding steady, and what changed today.">
  <meta property="og:url" content="https://baileyanalytics.com/dashboards/state.html">
  <meta name="twitter:card" content="summary">
  <link rel="alternate" type="application/rss+xml" title="Bailey Analytics — Today&#39;s Brief" href="/feed.xml">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="/dashboards/lens.css">
  <style>
    .sec-head { font-size: 1.4rem; font-weight: 600; letter-spacing: -0.01em; margin: 2.25rem 0 0.3rem; scroll-margin-top: 1rem; }
    .sec-sub { color: var(--muted); font-size: .92rem; max-width: 42rem; margin-bottom: 1.15rem; }
    #verdict .state-sentence { font-size: 1.15rem; }
  </style>
  <noscript><style>.js-only{display:none}</style></noscript>
</head>
<body>
  <nav class="wordmark"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav"><a href="/dashboards/">Dashboards</a><a href="/about.html">About</a></nav>

  <main>
    <a class="back" href="/dashboards/">&larr; Dashboards</a>
    <h1>The State of Things</h1>
    <p class="lede">Where things stand overall, right now — one verdict blended from every dashboard category, the pressure points behind it, and what&rsquo;s holding steady. For what <em>changed</em> today, see <a href="/dashboards/brief.html" style="color:var(--blue);text-decoration:none">Today&rsquo;s Brief</a>.</p>
    <div class="hub-fresh" id="asof"></div>

    <section class="state-panel" id="verdict"><div class="status-msg"><span class="js-only">Loading&hellip;</span><noscript>The interactive dashboards require JavaScript.</noscript></div></section>

    <section id="pressure-sec" hidden>
      <h2 class="sec-head">Pressure points</h2>
      <p class="sec-sub">The categories carrying the most stress right now, with the lenses driving each one.</p>
      <div id="pressure"></div>
    </section>

    <section id="steady-sec" hidden>
      <h2 class="sec-head">Holding steady</h2>
      <p class="sec-sub">Everything else — categories on watch are listed first.</p>
      <div id="steady"></div>
    </section>

    <section id="changed-sec" hidden>
      <h2 class="sec-head">What changed today</h2>
      <div class="sec-sub" id="changed"></div>
    </section>

    <div class="foot">
      Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">FRED</a> (St. Louis Fed), the <a href="https://banks.data.fdic.gov/" target="_blank" rel="noopener">FDIC</a>, the <a href="https://www.eia.gov/opendata/" target="_blank" rel="noopener">U.S. EIA</a>, the <a href="https://www.imf.org/en/Publications/WEO" target="_blank" rel="noopener">IMF</a>, the <a href="https://www.newyorkfed.org/research/policy/gscpi" target="_blank" rel="noopener">NY Fed</a>, <a href="https://www.policyuncertainty.com/" target="_blank" rel="noopener">policyuncertainty.com</a>, and <a href="https://www.coingecko.com/" target="_blank" rel="noopener">CoinGecko</a>. Public data, refreshed regularly.
    </div>
  </main>

  <script defer src="/dashboards/state.js"></script>
  <script>document.addEventListener("DOMContentLoaded", () => {
    loadState(null, { mode: "page" });
  });</script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/state.html
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat: State of Things page"
```

---

### Task 10: Panel atop `dashboards/index.html`

**Files:**
- Modify: `dashboards/index.html:33` (panel) and `:72-75` (scripts)

- [ ] **Step 1: Add the panel section**

Directly above the existing `<section class="brief-panel" …>` line (33), insert:

```html
    <section class="state-panel" id="state-panel" hidden></section>
```

- [ ] **Step 2: Load and invoke the renderer**

Add the script include before `brief.js` (line 73):

```html
  <script defer src="/dashboards/state.js"></script>
```

and inside the `DOMContentLoaded` handler, as the first call (before `loadBrief`):

```javascript
    loadState("state-panel", { mode: "panel" });
```

- [ ] **Step 3: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/index.html
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat: State of Things verdict panel atop the dashboards hub"
```

---

### Task 11: Home hero one-liner

**Files:**
- Modify: `index.html` (hero block ~line 313-318, style block, script ~line 337 and ~line 427)

- [ ] **Step 1: Add the hero element**

Inside `<div class="hero">`, between the `<a class="email" …>` line and the `<div class="asof" …>` line, insert:

```html
            <a class="state-line" id="state-line" href="/dashboards/state.html" hidden></a>
```

- [ ] **Step 2: Add its styles**

In the home page's `<style>` block (next to the `.brief-strip` rules at the end), append:

```css
        .state-line {
            display: block; margin: 1.1rem auto 0; max-width: 44rem;
            color: var(--text); text-decoration: none;
            font-size: 0.95rem; font-weight: 500; line-height: 1.5;
        }
        .state-line:hover .state-sentence { text-decoration: underline; }
        .state-line .pill { margin-right: 0.5rem; vertical-align: middle; }
```

(The badge renders via the home page's existing `.pill` classes — `state.js` mode `"line"` emits `pill`, not `badge`, for exactly this reason.)

- [ ] **Step 3: Load and invoke**

Add next to the existing brief include (line 337):

```html
    <script defer src="/dashboards/state.js"></script>
```

and in the inline IIFE, as its **first statements** (before the `Promise.allSettled` line), the same race-safe pattern the brief uses:

```javascript
            const showState = () => { if (typeof loadState === "function") loadState("state-line", { mode: "line" }); };
            if (typeof loadState === "function") showState();
            else window.addEventListener("DOMContentLoaded", showState);
```

Note: the hero line sits inside `.hero`, **outside** the `#lenses` section, and the call runs before the tile fetches and their `if (!tiles.length) return;` early-exit — so a tile failure can't skip it. If `/data/state/today.json` is missing, the element simply stays `hidden`.

- [ ] **Step 4: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add index.html
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat: State of Things verdict line on the home hero"
```

---

### Task 12: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Full test suite**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"`
Expected: OK, zero failures.

- [ ] **Step 2: Dry-run build + inspect**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/refresh_lenses.py" --brief --state --dry-run`
Expected output includes `Wrote …data\state\today.json`. Inspect it: verdict.status `watch`, shape `contained-pressure`, pressure_points `[energy]`, `changed` present, sentence reads cleanly.

- [ ] **Step 3: Serve and eyeball all three surfaces**

```powershell
python -m http.server 8000 -d "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics"
```

Check (e.g. with a browser or `curl`-equivalent fetches):
- `http://localhost:8000/dashboards/state.html` — badge + sentence, pressure cards with lens headlines and working deep links, steady chips (watch first), changed line.
- `http://localhost:8000/dashboards/` — verdict strip above the brief panel.
- `http://localhost:8000/` — hero one-liner with pill, links to the state page.
- Sanity: temporarily rename `data/state/today.json` and confirm all three surfaces degrade silently (page shows the refreshing message; panel and hero line stay hidden). Restore it.

- [ ] **Step 4: Clean up dry-run artifacts**

The dry-run overwrote `data/` from fixtures. Restore and remove the fixture-built state file (the live one is created by the first workflow run after deploy — all surfaces hide until then):

```powershell
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" checkout -- data/
Remove-Item -Recurse -Force "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/data/state"
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" status --short
```

Expected: clean tree (only committed work on the branch).

- [ ] **Step 5: Request code review**

Per the delivery workflow: run `/code-review` on the branch, fix findings, then hand to Michael for the merge/push decision. Do not merge or push.

---

## Plan self-review notes

- **Spec coverage:** rules §1 → Tasks 1-4; copy bank §2 → Task 2 (+ spec amendment); pipeline §3 → Tasks 5-7; JSON §4 → Task 4; surfaces §5 → Tasks 8-11; testing §6 → Tasks 1-6, 12. The §4 example's `steady` href for economic is `/dashboards/` in the spec but `/dashboards/economic/` here — the uniform per-category hub href is used everywhere (the economic hub page exists); this was confirmed against `dashboards/index.html`'s own "Overview →" links.
- **Known divergences from spec, both additive:** no-anchor fallbacks for contained/mixed shapes (Task 2 Step 5 amends the spec); `WATCH_NOUN_CAP = 4` bounds mixed-watch sentences (spec didn't cap; 8 nouns is unreadable).
- **Type consistency:** `build_state(category_indices, brief_today)` matches `refresh_state`'s call; `state._now` patching mirrors `brief._now` precedent; `loadState(elId, {mode})` is invoked with `"panel"`/`"line"`/`"page"` in Tasks 10/11/9 respectively.
