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
