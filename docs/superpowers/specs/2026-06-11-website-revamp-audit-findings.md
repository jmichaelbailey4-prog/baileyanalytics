# Website Revamp — Visual & Navigation Audit Findings

**Date:** 2026-06-11 · **Method:** site served locally (`python -m http.server 8000`), walked with headless-Chromium screenshots at desktop (1440×900) and mobile (390×844) widths, as a first-time visitor and a returning daily reader. All 4 synthesis surfaces, the hub, all 8 category hubs, and 7 representative lens pages captured; nav links extracted from the DOM of every audited page. Screenshots: `%TEMP%\ba-audit\seg\` (not committed).

This is the input to the revamp brainstorm. Findings only — no solutions prescribed here.

---

## A. Role overlap between surfaces (the core problem)

**A1. The same content renders on up to four surfaces.** The verdict sentence ("Pressure is real but contained: …") appears verbatim on (1) the home hero, (2) the hub's top panel, (3) The State of Things. The lens headline "Inflation is still hot — well above the Fed's target" appears on the home ECONOMY tile, the hub's Economic section card, the economic category hub card, and the Brief's "Elevated" card. A reader clicking through the synthesis layer reads the same sentences three or four times before reaching a chart.

**A2. State and Brief both cross-reference each other to explain their own roles.** State's subtitle says "For what *changed* today, see Today's Brief" and its final section is one line: "1 lens changed status today — see Today's Brief →". The split is confusing enough that each page spends copy disclaiming it. (Michael has already decided: merge them.)

**A3. The Brief is mostly *standing state*, not *change*.** Of the Brief's four sections, only "Status changes today" (1 item today) and "Biggest movers" (4 cards) are about change. "On alert" / "Elevated" / "On watch" (~15 cards, the bulk of the page) list every currently-stressed lens — the same standing information as State's pressure points, the home tiles, and the hub badges. The Brief's change-content is ~5 items; the page is 3,558px tall.

**A4. Duplicate cards within the Brief itself.** A lens that is both a big mover and on alert appears twice with identical cards (today: Commodities & Materials, Electricity & the Grid, Household Income & Savings, Consumer Sentiment region overlap). Same headline, same sparkline, same stats, a few hundred pixels apart.

**A5. Category hubs duplicate the main hub's sections.** `/dashboards/banking/` shows exactly the four cards that the Banking section of `/dashboards/` already shows, plus a description paragraph. The main hub (6,114px desktop / 10,500px+ mobile) already lists all 33 lenses grouped by category — so the category layer adds a second, near-identical surface between hub and lens. The hub is both "index of categories" and "index of every lens," which is why it scrolls forever.

**A6. The State page is thin.** Verdict box + 2 pressure-point cards + 6 "holding steady" chips + a one-line pointer to the Brief ≈ 1,340px. Its unique content (assembled verdict sentence, pressure points grouping, watching block when predictions exist) would fit comfortably inside another surface.

## B. Navigation dead-ends & journey breaks

**B1. Back links are hierarchy links, not journey links.** Every lens page hardcodes "← <category>". The flagship daily journey — Brief → lens → back — strands the reader on a category hub they've never visited. Same for State → lens → back, and home → (tile) → category hub → lens → back works, but home → hero → State → lens → back does not return through State.

**B2. The economic lens back link is mislabeled.** Economic lens pages (flat files like `/dashboards/recession-watch.html`) say "← Economic Lenses" but link to `/dashboards/` (the main hub), even though `/dashboards/economic/` exists. The other seven categories link to their real category hubs. Legacy artifact of economic lenses predating the category-hub pattern.

**B3. Three different back-link conventions on the synthesis surfaces.** Brief → "← Dashboards"; State → "← Dashboards"; Track Record → "← The State of Things". There is no convention; each page picked one.

**B4. Track Record is near-orphaned.** Its only inbound link is inside State's "What we're watching next" block — which renders only when `data/predictions/open.json` exists (it degrades silently otherwise, taking the only path to Track Record with it). It is in no nav, no footer, not on home. A prediction-curious visitor cannot find the site's most differentiating feature.

**B5. The top nav is two links: DASHBOARDS and ABOUT.** State, Brief, and Track Record — the surfaces a returning daily reader visits — have no persistent nav entry anywhere. They are reachable only through inline links on home/hub.

**B6. Home never names its destinations.** The hero verdict links to State and the "3 alert · 8 elevated · 4 on watch" strip links to Brief, but the words "The State of Things" and "Today's Brief" never appear on the home page. A first-time visitor has no way to learn these surfaces exist or what they're called; a returning reader has no labeled affordance to tap.

**B7. Home tile click target mismatch.** A tile shows the *worst lens's* headline and stat ("Inflation is still hot…", CPI 4.17%) but clicking it lands on the *category hub*, where the reader must re-find the lens that headline came from. The most interesting sentence on the tile is not a link to its own subject.

## C. Confusing reads (status & copy)

**C1. The two-badge tile contradicts itself.** Home tiles stack a blended category badge and a worst-lens callout: "BANKING **OK** / Concentrations & Funding **WORST: WATCH** / 'Some concentration and funding risks are building.'" The OK badge and the risk-warning headline directly conflict; "ECONOMY **WATCH** / WORST: **ELEVATED**" requires knowing the RMS-blend logic to reconcile. The headline sentence always describes the *worst lens*, so the tile's words systematically read one notch more alarming than its badge. (Michael's instinct confirmed on screen: the callout as rendered is not intuitive.)

**C2. Mobile tiles already drop the callout — and lose the story instead.** At 390px a tile is "ECONOMY WATCH / **4.17%** / CPI": a bare worst-lens stat with no sentence explaining why CPI is the number shown. Desktop over-explains; mobile under-explains.

**C3. "Holding steady" includes categories on WATCH.** State's holding-steady section leads with four WATCH chips. A category that is "on watch" is, by the section's own title, holding steady — the words pull in opposite directions.

**C4. The Live Now strip is counts without context.** "3 alert · 8 elevated · 4 on watch" links to the Brief but doesn't say so, and the counts are lens-counts (out of an unstated 33), so the denominator — and whether 8 elevated is a lot — is unknowable from the strip.

## D. Visual defects & polish (smaller, but seen on screen)

**D1. Mobile home header overlap (bug).** At 390px the "Bailey Analytics" H1 renders on top of the DASHBOARDS/ABOUT nav links.

**D2. Hub page length.** 6,114px desktop, >10,500px mobile. As the all-lenses index it's a scroll wall; categories 7 and 8 are effectively invisible.

**D3. Duplicate x-axis year labels on 5Y charts.** Banking asset-quality 5Y axis reads "2021 2021 2022 2023 2024 2024 2025" — tick labels repeat years (quarterly data + year-granularity labels).

**D4. Track Record empty state.** With no graded predictions the two stat cards render an em-dash over "of actuals landed inside our stated range" — reads as broken rather than "first grades pending," even though the subtitle explains it. (Production will fill this within weeks; the empty state still ships first.)

**D5. State pressure-point row layout is inconsistent.** When a lens read is short it sits inline after the lens name; when long it wraps to its own line (Consumer card today) — same component, two visual patterns.

**D6. Lens pages with missing predictions data log 404s** (`open.json`/`recent.json`) — silent for users, by design, but noted for completeness.

## E. What's working (don't break it)

- **Lens pages are the strongest layer.** Scoreboard → lead chart with verdict → "What it is" / "The read right now" per indicator is clear, self-explanatory, and renders well on mobile. The revamp problem is *above* the lens layer, not in it.
- The verdict sentence + WATCH badge as a hero is compelling — the problem is its triplication, not its existence.
- Category hub *descriptions* (one paragraph of "why this category matters") are good orientation copy that the main hub lacks.
- Status-badge color language (ok/watch/elevated/alert) is consistent everywhere; the vocabulary works.
- Hub "Data last changed N hours ago" stamps and per-stat ▲/▼ deltas read well.

## F. Surface inventory (for the brainstorm)

| Surface | Unique content (not shown elsewhere) | Everything else on it |
|---|---|---|
| Home | hero identity, contact, footer sources | verdict (=State), alert counts (=Brief), 8 tiles (=hub badges + worst-lens headlines) |
| Hub `/dashboards/` | none | verdict panel (=State), Brief panel (=Brief), all 33 lens cards (=category hubs) |
| State | pressure-points grouping, holding-steady chips, watching block (predictions) | verdict (=home/hub), pointers to Brief |
| Brief | status changes, biggest movers (z-ranked), RSS feed | alert/elevated/watch standing lists (=State pressure points / home tiles / hub badges) |
| Track Record | hit rate, skill score, methodology, ledger | — |
| Category hubs ×8 | description paragraph | lens cards (=hub sections) |
| Lens pages ×33 | everything on them | — |

Reading of the table: the site has ~5 genuinely distinct content blocks above the lens layer (verdict sentence, pressure/standing summary, change list, predictions/track record, lens index) spread across 12 navigable surfaces (home, hub, state, brief, track-record, 8 category hubs minus overlap).
