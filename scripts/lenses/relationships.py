"""The curated cross-category relationship map — the authored content behind the
relationship narrative (synthesis.compose_relationships renders it; the grammar
is gated by each edge's strength tier so the common dishonest forms fail CI; the
map is also human-reviewed — the diff is the review).

WHY CURATED, NOT DATA-MINED: empirical macro relationships are not reliably
derivable from this site's handful of series, and an auto-mined correlation
presented as a relationship would be the exact "black box" the site rejects. A
version-controlled list of plain-English edges, each with a strength tier and a
`note` justifying it, is the most transparent possible form — reviewed the same
way Michael reviews the state.py / today.py copy banks (the diff is the review).

STATUS (2026-06-16): the engine + honesty tests are complete; the MAP CONTENT is
deferred to the next session (Michael's economist-curated authoring — spec §6).
The two edges below are PLACEHOLDERS: honest, valid, tier-correct examples that
document the schema and exercise the engine. They are NOT yet fed to the live
brief — today.py emits an empty `relationships` list until the map is authored.

EDGE SCHEMA
  source / target : lens ids (validated against config in test_synthesis.py)
  strength        : "definitional" | "empirical" | "co-occurrence"
                    definitional -> may state causation (it is an identity)
                    empirical    -> MUST hedge ("historically"/"tends to"/...)
                    co-occurrence-> MUST state neither cause nor probability
  link            : the sentence shown to readers (tier grammar enforced)
  note            : why this edge exists — the human-readable justification

REVIEW CHECKLIST — what the substring linter CANNOT enforce (so a human, and an
LLM honesty-reviewer at authoring time, MUST check every edge for these):
  1. SCOPE OF THE HEDGE (the linter's blind spot): an empirical edge must hedge the
     CAUSAL CLAIM ITSELF, not merely contain a hedge word somewhere. BANNED even
     though the linter passes it: a general hedge followed by a present-tense
     assertion of the specific mechanism — e.g. "rates have historically cooled
     demand, and are cooling it now". Make ONE hedged general claim; never assert the
     mechanism as a current fact.
  2. SUBTLE CAUSATION the high-precision linter intentionally lets through (it favors
     near-zero false positives): bare verbs like "cools"/"lowers"/"slows"/"erodes" in
     a co-occurrence edge still assert a cause — downgrade the wording to pure
     conjunction ("alongside", "at the same time as") or re-tier honestly.
  3. TIER HONESTY: definitional must be a true identity (real = nominal − inflation),
     not a strong empirical claim dressed up as definitional. When unsure between
     empirical and co-occurrence, choose co-occurrence.
"""

RELATIONSHIPS = [
    {
        "source": "cost-of-living",
        "target": "consumer-income-savings",
        "strength": "definitional",
        "link": ("Real income is pay measured after inflation, so a hotter cost "
                 "of living lowers it by definition."),
        "note": ("PLACEHOLDER (illustrative). An accounting identity: real = "
                 "nominal minus inflation. Safe to state as fact."),
    },
    {
        "source": "housing-affordability",
        "target": "housing-home-prices",
        "strength": "empirical",
        "link": ("Mortgages near 7% have historically cooled buyer demand, and "
                 "affordability is already stretched."),
        "note": ("PLACEHOLDER (illustrative). A well-established but not "
                 "deterministic empirical link — hedged with 'historically'."),
    },
]
