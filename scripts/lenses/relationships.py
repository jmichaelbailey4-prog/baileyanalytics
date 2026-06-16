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

STATUS (2026-06-16): AUTHORED — the map is now populated with ~22 economist-
curated edges across the macro spine (spec §6; branch synthesis-relationship-map).
Every edge passed (a) the high-precision substring gate (relationship_sentence
raises on a tier violation), (b) a self-red-team during authoring, and (c) an
INDEPENDENT LLM honesty-review at authoring time (the primary semantic gate — it
judges scope/tier/smuggled-causation the substring matcher cannot). The map is
WIRED into the brief but ships only on Michael's per-edge sign-off — it is the
contested causal content, so do NOT deploy without it.

EDGE SCHEMA
  source / target : lens ids (validated against config in test_synthesis.py)
  strength        : "definitional" | "empirical" | "co-occurrence"
                    definitional -> may state causation (it is an identity)
                    empirical    -> MUST hedge ("historically"/"tends to"/...)
                    co-occurrence-> MUST state neither cause nor probability
  link            : the sentence shown to readers (tier grammar enforced)
  note            : why this edge exists — the human-readable justification

ORDERING IS PRIORITY: compose_relationships(cap=1) renders the FIRST edge whose
both endpoints are active today, so the list is ordered definitional -> empirical
-> co-occurrence (and by macro centrality within each tier). The lead sentence is
therefore always the most defensible connection available on the day.

REVIEW CHECKLIST — what the substring linter CANNOT enforce (so a human, and an
LLM honesty-reviewer at authoring time, MUST check every edge for these):
  1. SCOPE OF THE HEDGE (the linter's blind spot): an empirical edge must hedge the
     CAUSAL CLAIM ITSELF, not merely contain a hedge word somewhere. BANNED even
     though the linter passes it: a general hedge followed by a present-tense
     assertion of the specific mechanism — e.g. "rates have historically cooled
     demand, and are cooling it now". Make ONE hedged general claim; never assert the
     mechanism as a current fact. (A present-tense CO-OCCURRING FACT beside the hedged
     claim is fine — e.g. "...have historically cooled demand, AND affordability is
     already stretched" — because the second clause states a current state, not the
     mechanism.)
  2. SUBTLE CAUSATION the high-precision linter intentionally lets through (it favors
     near-zero false positives): bare verbs like "cools"/"lowers"/"slows"/"erodes" in
     a co-occurrence edge still assert a cause — downgrade the wording to pure
     conjunction ("alongside", "at the same time as") or re-tier honestly.
  3. TIER HONESTY: definitional must be a true identity (real = nominal - inflation),
     not a strong empirical claim dressed up as definitional. When unsure between
     empirical and co-occurrence, choose co-occurrence.
"""

RELATIONSHIPS = [
    # ------------------------------------------------------------------ #
    # DEFINITIONAL — identities. May state causation because they are     #
    # true by construction, not empirical claims.                         #
    # ------------------------------------------------------------------ #
    {
        "source": "cost-of-living",
        "target": "consumer-income-savings",
        "strength": "definitional",
        "link": ("Real income is pay measured after inflation — so when the cost "
                 "of living climbs faster than wages, real incomes fall by definition."),
        "note": ("Accounting identity: real income = nominal income deflated by "
                 "prices. The 'faster than wages' condition is exactly what makes "
                 "the fall definitional, not empirical. Safe to state as fact."),
    },
    {
        "source": "energy-oil-fuels",
        "target": "cost-of-living",
        "strength": "definitional",
        "link": ("Fuel is one of the items the inflation basket is built from, so "
                 "swings in gasoline and diesel prices show up in the cost-of-living "
                 "reading as one of its components."),
        "note": ("COMPOSITIONAL identity, deliberately narrow: energy is literally "
                 "a CPI component, so its price moves are part of the inflation "
                 "number by construction. The WIDER claim that energy drives core "
                 "or wage inflation would be empirical and is NOT made here. (The "
                 "definitional-vs-empirical call is the one most worth Michael's "
                 "scrutiny.)"),
    },
    # ------------------------------------------------------------------ #
    # EMPIRICAL — well-established but not deterministic. MUST hedge, and  #
    # the hedge must govern the causal claim (no bare present-tense        #
    # mechanism). Ordered by macro centrality.                            #
    # ------------------------------------------------------------------ #
    {
        "source": "cost-of-living",
        "target": "cost-of-money",
        "strength": "empirical",
        "link": ("When inflation runs hot, the Fed has historically responded by "
                 "holding policy rates higher for longer."),
        "note": ("The Fed's reaction function — empirical and well-documented, but "
                 "a policy choice, not a mechanical rule. Hedged with 'historically'."),
    },
    {
        "source": "recession-watch",
        "target": "job-market",
        "strength": "empirical",
        "link": ("An inverted yield curve has historically preceded weakening in "
                 "the job market, though the lead time has varied widely and it is "
                 "no guarantee."),
        "note": ("The classic recession signal. Hedged hard ('historically "
                 "preceded', 'varied widely', 'no guarantee') because the curve has "
                 "also given false signals — the honesty caveat is the point."),
    },
    {
        "source": "housing-affordability",
        "target": "housing-home-prices",
        "strength": "empirical",
        "link": ("When affordability is stretched, home-price gains have "
                 "historically tended to slow."),
        "note": ("REVISED after the independent honesty-review (B-5): the original "
                 "hedged a claim about buyer DEMAND while the target lens is home "
                 "PRICES, so it never argued to its own target. Now the hedge "
                 "('historically tended') governs a PRICE claim directly. "
                 "Well-established but not deterministic."),
    },
    {
        "source": "cost-of-money",
        "target": "housing-affordability",
        "strength": "empirical",
        "link": ("Mortgage rates tend to track Treasury yields and the Fed's policy "
                 "path, so affordability has typically tightened when the cost of "
                 "money rises."),
        "note": ("Two-step empirical link (policy/Treasury -> mortgage rates -> "
                 "affordability). Hedged twice ('tend to', 'typically'); the "
                 "pass-through is real but not one-for-one."),
    },
    {
        "source": "global-dollar-currencies",
        "target": "global-trade-supply",
        "strength": "empirical",
        "link": ("A stronger dollar buys more abroad, so it has typically made "
                 "imports cheaper for U.S. buyers and U.S. exports pricier overseas."),
        "note": ("DIRECTION CORRECTED from the common slip: a stronger dollar "
                 "LOWERS import prices (more foreign goods per dollar), it does not "
                 "raise them. The FX arithmetic premise is near-definitional; the "
                 "trade-flow response is empirical, hence 'typically'."),
    },
    {
        "source": "global-trade-supply",
        "target": "cost-of-living",
        "strength": "empirical",
        "link": ("When global supply chains are stressed, goods inflation has "
                 "historically tended to follow with a lag."),
        "note": ("Supply-chain pressure (the NY Fed's GSCPI) has led goods prices "
                 "in past episodes; hedged with 'historically'/'tended', no "
                 "present-tense mechanism asserted."),
    },
    {
        "source": "consumer-income-savings",
        "target": "consumer-spending",
        "strength": "empirical",
        "link": ("Real incomes and consumer spending have historically tended to "
                 "move together."),
        "note": ("Income is the largest fuel for spending, but credit and savings "
                 "buffers loosen the link — so empirical, not definitional. Hedged "
                 "with 'historically'/'tended'; the income-funds-spending rationale "
                 "is kept here in the note, out of the reader sentence."),
    },
    {
        "source": "cost-of-money",
        "target": "business-credit",
        "strength": "empirical",
        "link": ("When the Fed keeps policy rates elevated, the cost of business "
                 "borrowing has typically risen alongside them."),
        "note": ("Policy rates set a floor under most business borrowing costs; "
                 "hedged with 'typically' since spreads and demand also move the "
                 "final rate."),
    },
    {
        "source": "cost-of-money",
        "target": "bank-profitability",
        "strength": "empirical",
        "link": ("Banks' net interest margins have historically widened when policy "
                 "rates rise — at least until the rates they pay on deposits catch up."),
        "note": ("Higher rates lift asset yields faster than funding costs early on; "
                 "the 'until deposits catch up' caveat is the honest other half. "
                 "Hedged with 'historically'."),
    },
    {
        "source": "cost-of-money",
        "target": "fiscal-health",
        "strength": "empirical",
        "link": ("When borrowing rates stay high, the federal interest bill has "
                 "historically climbed as older, cheaper debt rolls over at today's "
                 "rates."),
        "note": ("Interest cost = rate x debt is near-mechanical, but the AVERAGE "
                 "rate on existing debt reprices only gradually (via new issuance), "
                 "so it is framed empirically with 'historically' rather than as an "
                 "instant identity."),
    },
    {
        "source": "consumer-credit",
        "target": "bank-asset-quality",
        "strength": "empirical",
        "link": ("Rising consumer-loan delinquencies have historically shown up in "
                 "banks' asset quality, since those loans sit on bank balance sheets."),
        "note": ("Structural grounding (consumer loans ARE bank assets — an "
                 "accounting fact, not a behavioral mechanism) plus an empirical "
                 "timing claim; hedged with 'historically'."),
    },
    {
        "source": "housing-affordability",
        "target": "housing-supply-construction",
        "strength": "empirical",
        "link": ("When mortgage rates climb, homebuilders have historically pulled "
                 "back on new construction, though incentives can cushion the effect."),
        "note": ("Higher financing costs weigh on buyers and builders alike; hedged "
                 "with 'historically' plus the honest 'incentives can cushion' "
                 "caveat."),
    },
    {
        "source": "cost-of-money",
        "target": "business-investment",
        "strength": "empirical",
        "link": ("Higher borrowing costs have historically weighed on business "
                 "investment, though strong demand can offset them."),
        "note": ("Rates raise the hurdle rate for projects; hedged with "
                 "'historically' and the 'demand can offset' caveat. 'Weighed on' "
                 "is causal but hedged, which the empirical tier permits."),
    },
    {
        "source": "business-profitability",
        "target": "business-investment",
        "strength": "empirical",
        "link": ("Corporate profits and business investment have historically moved "
                 "together."),
        "note": ("Profits fund capex, but firms also borrow and hold cash, so "
                 "empirical, not definitional. Hedged with 'historically'; the "
                 "retained-earnings rationale stays in the note."),
    },
    {
        "source": "global-uncertainty",
        "target": "business-investment",
        "strength": "empirical",
        "link": ("Spikes in policy uncertainty have historically tended to coincide "
                 "with firms delaying investment until the picture clears."),
        "note": ("The 'wait-and-see' effect — empirical, hedged with "
                 "'historically'/'tended'. 'Coincide with' avoids asserting strict "
                 "one-way causation."),
    },
    {
        "source": "consumer-sentiment",
        "target": "consumer-spending",
        "strength": "empirical",
        "link": ("Consumer sentiment has historically been a noisy guide to "
                 "spending — confidence has often sagged in stretches when "
                 "households kept spending anyway."),
        "note": ("Deliberately states the link is WEAK (honest anti-overclaim): "
                 "sentiment and spending diverge frequently. Hedged with "
                 "'historically'/'often'. On-brand for a site whose edge is honesty."),
    },
    {
        "source": "energy-natural-gas",
        "target": "energy-electricity",
        "strength": "empirical",
        "link": ("Natural gas powers a large share of U.S. electricity generation, "
                 "so gas and power prices have historically moved together."),
        "note": ("Gas is the marginal fuel for much of U.S. power; the link is real "
                 "but not one-for-one (fuel mix, regulation, contracts), so "
                 "empirical. Hedged with 'historically'."),
    },
    # ------------------------------------------------------------------ #
    # CO-OCCURRENCE — pure conjunction. States NEITHER cause NOR a         #
    # probabilistic hedge: two things observed together, full stop.       #
    # ------------------------------------------------------------------ #
    {
        "source": "market-risk-sentiment",
        "target": "business-credit",
        "strength": "co-occurrence",
        "link": ("Corporate credit spreads and broader market risk appetite both "
                 "reflect how investors are pricing risk, and move largely in step."),
        "note": ("REVISED after the honesty-review (B-20): scoped to the SPREAD/"
                 "appetite components (business-credit also tracks lending "
                 "standards, delinquency and loan growth, which are not risk-"
                 "appetite gauges). Co-movement by construction -> co-occurrence, "
                 "no cause, no hedge."),
    },
    {
        "source": "global-uncertainty",
        "target": "market-risk-sentiment",
        "strength": "co-occurrence",
        "link": ("Bouts of policy uncertainty and market risk-aversion frequently "
                 "show up at the same time."),
        "note": ("Two stress gauges that co-move; stated as pure co-occurrence "
                 "('at the same time'). 'Frequently' is a frequency word, not a "
                 "probabilistic causal hedge, and claims no direction."),
    },
    {
        "source": "job-market",
        "target": "consumer-income-savings",
        "strength": "co-occurrence",
        "link": ("A strong job market and rising household incomes move largely "
                 "in step."),
        "note": ("REVISED after the honesty-review (B-22): dropped the 'so' that "
                 "smuggled a mechanism into a co-occurrence edge. The rationale "
                 "(labor income is the largest single source of household income, "
                 "so the two co-move) lives here in the note, not the reader line. "
                 "Not a pure identity (transfers, capital income), so co-occurrence."),
    },
]
