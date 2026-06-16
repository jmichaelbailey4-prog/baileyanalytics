# Decisions pending Michael's review

Running log from the autonomous session of **2026-06-15** (branch
`autonomous-polish-predictions`). Each item: the fork, the options, **my pick + why**, and what
I did in the meantime. Nothing here is deployed. Reversible work proceeded on the assumption of
the recommended option; contested work is stubbed/flag-gated so a different call is cheap.

---

> **Update 2026-06-15 (Michael's review):** approved all "done & ready" items. Decided
> **#1 = predict everything, even neutral / info-only** (overriding my "keep excluded" lean) and
> **#1b = yes, split the edge stat**. Both are now **implemented on the branch** (see "RESOLVED"
> notes inline). #2 (banking) stays a next increment; #3 (hero copy) deferred unless trivial; #4
> Cloudflare receive-routing **done by Michael**. Branch is being fully prepared before any merge.

## #1 — Predict asset/market prices? (the crux of the predictions phase) — RESOLVED: predict them

**Fork.** Should the prediction system cover tradeable prices — the markets scoreboard (S&P, oil,
gold, BTC, ETH), crypto structure, FX (EUR/JPY/CNY), and commodity-price indices (copper, broad
commodities)? Full design + tradeoffs in `specs/2026-06-15-predictions-coverage-design.md` §4.

**Options.**
- **C1 — keep excluded (my pick, for now).** Predict every macro/physical *quantity*; don't
  predict tradeable *prices*. Tier A (done) + Tier B (banking) already reaches ~82% coverage —
  honestly "nearly all" — without the third rail. Keeps the credibility narrative and the headline
  accuracy stat clean.
- **C2 — predict them as segregated "typical-range" volatility envelopes.** Full coverage, walled
  off from the macro accuracy stat, asset-specific disclaimer, framed as "we don't call direction."
  On-brand ("0 skill on prices, by design — here's the proof") but a real mini-project + screenshot
  risk + reverses public copy.
- **C3 — predict them like everything else.** Rejected (dilutes the macro record; highest
  perception risk).

**My recommendation:** **C1 now; C2 as a fast-follow only if you want literal 100% coverage.**
**Note the existing inconsistency:** we *already* predict energy fuel prices (WTI, gasoline, diesel,
Henry Hub) under severity rules — so "we don't predict prices" isn't currently true; it's really
"not the scoreboard/crypto." Whatever you choose, we should reconcile the public copy to match.

**RESOLVED — implemented (the honest "C2-lite" form Michael chose):** every reachable series is
now forecast, including the **scoreboard (S&P/oil/gold/BTC/ETH), FX, and commodities** (roster
59→**92**). They are flagged `market_price`, which (a) attaches a *"a market price — the band is the
range history suggests around today's level, not a directional call or investment advice"* note on
the prediction block, and (b) holds them **out of the headline skill/direction edge stat** (#1b) so
coin-flips never dilute the macro record — while their **bands are still graded** for calibration,
which is honest and on-brand. Track Record copy rewritten to describe this. Still **not** predicted
(need fetch plumbing / infeasible, not integrity): banking (FDIC), computed spreads,
crypto-structure (CoinGecko/accumulated history), IMF (annual), GSCPI/EPU.

## #1b — Should descriptive (info) forecasts count toward the headline skill stat? — RESOLVED: split out

**Fork.** Tier A adds 23 *descriptive* forecasts (Fed balance sheet, inventories, etc.). These are
smooth — the naive guess is hard to beat — so each scores ~0 *skill* (though ~80% *calibration*,
honestly). When the next CI run grades them, they'll blend into the **Track Record headline skill
number**, dragging it toward 0 and **understating our genuine edge on the badge-driving signal
series**. (Calibration — % inside band — is unaffected; it stays ~80% by construction.)

**Options.** (a) Include them in the headline (simplest; honest but conservative — undersells the
macro edge). (b) **Compute the headline skill/calibration over *signal* (non-descriptive) series
only, and show descriptive forecasts in their own labeled group + count** (most representative of
what "skill" means here). (c) Drop the skill stat entirely (overcorrection).

**RESOLVED — implemented (b).** `descriptive` + `market_price` are plumbed `open.json` → graded
ledger → `track-record.json`. **skill / direction / status** are now computed over **signal**
(badge-driving) series only; **calibration and the graded count span all** (band coverage is honest
for everything); a new **`coverage`** count records how many graded rows were descriptive/market.
`track-record.js` shows skill as "pending" until a signal series grades, and the skill stat's note
says it excludes market prices. Result: adding 33 descriptive/market forecasts no longer drags the
headline edge number toward a coin flip.

## #2 — Banking & computed series (Tier B) — next increment?

**Fork.** Predict the 9 banking (quarterly FDIC) and 3 computed (rate-expectations spread,
profit-share, hp-share) series? Integrity is fine; both need `predict.py` to fetch beyond FRED/EIA
(FDIC fetch path; reconstruct injected series), and banking needs a per-series history-length
viability gate (quarterly → ~9yrs min).

**My recommendation:** **yes, as the next increment after you sign off the §2 direction** — it's
the difference between 82% and ~94% coverage. Not in this branch because it touches the fetch layer
(more than "reversible polish"). I can implement on a follow-up branch on your word.

**RESOLVED — shipped + deployed 2026-06-16.** Implemented on branch
`predictions-coverage-banking`, **not** via a new FDIC/EIA fetch path but by reading each
indicator's **already-baked** lens-JSON observation history (`data/<out>/<lens>.json`
`indicators[].observations`, full depth — banking = 81 quarters back to 2006). Roster
**92 → 107** (+9 banking, +3 computed, +GSCPI, +2 EPU): `roster.BAKED_SOURCES` + a `baked`
flag; `runner._baked_history` (degrades to `[]` like `refresh_lenses._prior_obs`, kept
local to avoid the heavy import); `_prepared_series` **skips `ind.derive`** for baked (the
obs are already post-derive/post-thin — the double-derive trap); banking's `BankingIndicator`
(no `series_id`/`derive`/`market_price`) read via `getattr`. Banking is badge-driving
**signal**. FF-merged `534eb9b` to main, Pages-deployed, 640 tests green; extensive
/code-review found no bugs. **Still out (correctly, not integrity):** IMF (annual — too few
backtest origins for an empirical 80% band) and crypto-structure (short history + outside
`config.CATEGORIES`). No data re-baked — coverage activates on the next CI tournament/daily.

## #3 — Home hero verdict vs. brief verdict (audit quick win — editorial)

**Fork.** The home hero sentence and the brief's verdict are currently **identical** (a reader who
clicks through reads the same sentence twice). The audit suggested "home = short form, brief = full
form." Producing a good short form is editorial, not mechanical.

**Options.** (a) Author a distinct short-form verdict in the copy bank (`state.py`/`today.py`) —
best result, but it's writing, and I shouldn't invent your editorial voice unreviewed. (b) Mechanically
shorten (first clause / before the colon) — cheap but can read clipped. (c) Leave identical — the
duplication is minor; arguably fine.

**My recommendation:** **(a), but it needs your voice.** I've left it identical (option c) rather
than ship a mechanical truncation that might read worse. If you want, I'll draft 2–3 short-form
options in `state.py`'s copy bank for you to pick. Low urgency.

## #4 — Contact email inbox (action is yours; see batch section C)

**Fork.** `michael@baileyanalytics.com` is a live mailto on home + About, the Buttondown reply-to,
and in the home JSON-LD — but no inbox exists, so mail to it **bounces**.

**Options.** (a) **Cloudflare Email Routing** — free, receive-only, forward
`michael@baileyanalytics.com` → `jmichaelbailey4@gmail.com`. (b) Contact form (Formspree / a CF
Worker) — adds a surface + spam handling for no real gain on a personal-brand site. (c) Drop the
address — loses a credibility/contactability touch and contradicts the distribution-phase design.

**My recommendation:** **(a) Cloudflare Email Routing.** It's free, zero-code, preserves the
branded address, and the distribution-phase spec already chose it as the receive path. No code
change is needed (the mailto already works once the route exists), so I built **no** contact form
— that would be unused, contested surface. Exact setup steps are in the batch (section C). Optional
later: Gmail "Send mail as" to *reply* from the branded address (needs an SMTP relay; note only).

---

## #5 — What's the highest-value next bet? (general-improvement assessment)

Not a blocking decision — a recommendation for where the *next* session's effort goes, toward the
north star (a standalone resource with a regular audience). I weighed the candidates rather than
defaulting to the backlog:

- **Synthesis / the "why" layer (audit item #4) — my pick.** The audit's single biggest *content*
  gap: the site states 33 isolated facts; the connections (energy costs → inflation →
  sentiment is one story, not three reads) and a one-line *why* per mover are left to the reader.
  Every daily product people actually read (Axios Macro, Chartr, the Daily Shot) leads with one
  human sentence of context. Now that distribution shipped, this is what makes the daily habit
  *worth* having. **High value, high effort, and genuinely creative** — it needs a brainstorm with
  you (editorial voice, how much causal claim is honest), so the right next step is a *spec*, not
  code. I can draft it on your word.
- **Perspective slicer (3-role)** — defer (audit agrees): deepens engagement for an audience that
  doesn't exist yet. After synthesis + distribution traction.
- **Deeper data coverage (Treasury/Census/BLS)** — defer (audit agrees): breadth is complete at 8
  categories; no evidence more coverage is the gap, strong evidence distribution/synthesis is.
- **Finish the distribution loop** — highest *latent* value but **blocked on you**: the email digest
  can't send until Buttondown approves the account (section C). Nothing for me to build there.

**Recommendation:** once you've cleared the Buttondown + Cloudflare actions, point the next session
at a **synthesis-layer spec** (cross-category narrative + per-mover "why"). It's the highest-value
buildable bet and the natural successor the roadmap and audit both name. I deliberately built none
of it now — it's creative work that needs your input first.

---

# Decisions pending — autonomous session of 2026-06-16 (branch `synthesis-why-layer`)

The synthesis / "why" layer (#5 above, now built). Spec:
`specs/2026-06-16-synthesis-why-layer-design.md`. I built the **uncontested, honest** subset
(per-mover why + structural co-occurrence + the relationship-map *scaffolding*), logged the
contested forks below, built on the recommended option for each (reversible — it's a branch),
and **deferred** the authored relationship-map content + the map-driven causal narrative to the
next session (your editorial/economist call). The five forks:

> **Update 2026-06-16 (Michael's review):** approved **D1–D5** (house voice, silent quiet-day,
> the chosen surface placement, **no LLM**, and the theme groupings). The built subset was
> **FF-merged + deployed to `main` (`6be2801`)** — the per-mover why + co-occurrence go live on
> the next `refresh-fred` cron bake. **D6 (author the relationship map + wire/render it) is the
> next session's task** and must NOT be deployed without per-edge sign-off (it's the causal content).

## D1 — Editorial voice of the why/synthesis copy
**Fork.** What voice do the new lines speak in? **Options.** (a) **Match the existing house voice**
(plain, specific, colon-phrasing for plural-agnostic subjects à la `explain.py`, em-dash used
sparingly) — *my pick*. (b) A terser, headline-style clip ("Food — 7th straight gain, record"). (c)
A chattier newsletter voice. **Pick + why:** (a). The site already has a consistent, trusted voice;
a second voice on the same page would read bolted-on. **Built on (a).** Easy to retune — the copy is
a handful of templates in `synthesis.py`.

## D2 — How much the layer says on a quiet day
**Fork.** Most days are quiet; manufacturing drama would be the worst failure here. **Options.** (a)
**Silent unless there's a real, countable pattern** (per-mover why omitted when nothing clears the
bar; co-occurrence omitted unless ≥2 pressure points share a theme) — *my pick*. (b) Always emit at
least one calm framing line. **Pick + why:** (a) — honesty + "never manufacture drama" (memory:
the audit praised the honest quiet-day instinct). Verified on real data: today the Dollar mover
correctly gets **no** why line. **Built on (a).**

## D3 — Surface placement
**Fork.** Where do the new reads appear? **Options.** (a) **Per-mover why inside each mover card on
the brief + as a muted line in the email; co-occurrence as one line under the verdict panel** —
*my pick*; defer lens-page placement and the relationship lead-sentence. (b) A single synthesis
lead paragraph at the top of "What changed today" only. (c) Push the why onto the 33 lens pages too
(the `#baked-read` block). **Pick + why:** (a) — the movers are exactly where the site shows "what"
without "why"; the verdict panel is where a one-line synthesis belongs; lens-page placement is a
separate baked surface best done once the voice is signed off. **Built on (a).**

## D4 — LLM or rules/curated? (you flagged this one explicitly)
**Fork.** Generate any of this copy with an LLM? **Options.** (a) **No LLM — rules + curated map
only** — *my strong pick*. (b) LLM constrained to *rephrasing already-grounded facts*, human-flagged
for review, never inventing causation. (c) LLM free-form (rejected outright). **Pick + why:** (a).
"No black box" is load-bearing for this exact feature — it's the credibility centerpiece. Every line
is deterministic and traceable to a rule or a reviewed edge. If you ever want (b), it must stay a
rephrasing layer over grounded facts with a human gate — never a source of new claims. **Built on (a).**

## D5 — Theme tags are mild editorial — author them now or defer?
**Fork.** The structural co-occurrence count needs a `lens_id → theme` map (e.g. fuel/food/electricity/
CPI = "the cost of living"). A theme tag is a *categorization*, not a causal edge — but it's still a
light editorial judgment. **Options.** (a) **Author a minimal, conservative theme map now** (prices,
housing-market, credit clusters only) and flag it for your review — *my pick*; the co-occurrence count
is explicitly in-scope and needs it. (b) Defer co-occurrence entirely until you review themes. **Pick
+ why:** (a) — it's reversible, the groupings are uncontroversial (a fuel-price and a food-price lens
*are* both cost-of-living), and it's what makes today's strongest worked example ("four of today's
pressure points are about the cost of living") possible. **Built on (a)** — the map is
`synthesis.THEMES`; please sanity-check the groupings.

## D6 (deferred, not a fork to decide now) — authoring the relationship map
The relationship *engine* + honesty tests are built and green; the **map content** (the authored
edges in `relationships.py`) is deliberately near-empty (2 marked placeholders). Authoring ~15–30
economist-curated edges is the next session's main task — it's content entry, not engineering, and
it needs your domain judgment + voice on how much causal language each edge earns. Mockups of the
intended voice are in spec §8.
