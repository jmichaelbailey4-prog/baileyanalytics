# Site Audit & Next-Steps Recommendation — June 12, 2026

**Scope:** full critical review of the live site (https://baileyanalytics.com) the day after the
revamp deployed (merged Today's Brief, 4-item nav, V2 home tiles, slim hub) and predictions went
live. Method: headless Playwright walk of 23 pages at 1440px and 390px (screenshots in
`%TEMP%\ba-audit\shots-live\`), per-page metrics (page weight, console errors, meta tags),
axe-core accessibility scans on five key pages, raw-HTML crawlability checks, live JSON state
inspection, and a search-visibility test. No production code was changed.

---

## Part 1 — The Review

### Verdict up front

The product is good. The revamp landed: the site now has a coherent shape (one daily surface,
one drill-down tree, one accountability page, one about page), the visual language is consistent
and professional, performance is excellent, and the plain-English-verdict + public-predictions
combination is genuinely differentiated — no mainstream competitor does both.

The problem is no longer the product. **The site has no way to be found and no way to be
remembered.** It is invisible to search (zero results for its own name + topic), shared links
unfurl with no preview image, the daily brief has no permalink and no email/push channel, and
the only subscription mechanism is an RSS link in a footer. A standalone resource that intends
to build a regular audience currently has no acquisition channel and no retention channel. That
is the gap this phase should close.

---

### Eyes 1 — The first-time visitor

*Evidence: `home--desktop.png`, `home--mobile.png`, `about--desktop.png`, `track-record--desktop.png`*

**What works (and it mostly works):**
- The 10-second test passes on desktop. Wordmark, one-line mission ("Daily, plain-English
  dashboards… built from public data"), a verdict sentence with a WATCH badge, "Live data —
  updated June 12, 2026," then eight live tiles. A new visitor understands what this is, that
  it's alive, and that it has a point of view.
- The verdict sentence is the best thing on the page — "Most of the economy is on solid footing…
  but energy and commodity costs are squeezing budgets" is exactly the editorial product a
  visitor can't get from FRED or Finviz.
- The About page is the strongest-written page on the site. "If you check one page a day to stay
  oriented on the economy, this site intends to be that page" is the mission statement; the
  Michael-Bailey-VP-of-Data-Analytics credential and the no-paywall/no-spin/no-black-box framing
  are credible and human.

**What undercuts it:**
1. **Track Record is a flagship nav item with nothing in it.** `track-record.json` shows
   `graded: 0`. The empty state is gracefully written ("pending" cards + a genuinely good "How
   this works"), but a skeptical first-timer who clicks the site's boldest credibility claim
   finds no record. Meanwhile 59 open predictions exist in `open.json` and the page shows none
   of them — the cheapest possible fix is to list what the site is currently on the record for,
   which turns "nothing here yet" into "here are 59 timestamped calls awaiting grades."
2. **The verifiability claim never links to the proof.** Track Record says "the ledger lives in
   this site's public git history; the timestamps are independently verifiable" — with no link
   to the GitHub repo anywhere on the site. An extraordinary claim with the receipt omitted.
3. **No reason-to-return mechanism is offered.** The visitor who likes it has exactly one
   retention option: remember the URL. No email capture, no "get this daily" anywhere above the
   footer RSS link. First-visit goodwill is being thrown away daily.
4. Smaller credibility nits: the contact email sits in hero position on the home page (prime
   space spent on something that belongs in the footer/About); the 8 tiles in a 3-column grid
   leave a lopsided final row; category accent colors fight financial semantics on home tiles —
   "Markets are calm — OK" with VIX rendered in red, "Business health is holding up — OK" with
   the Baa spread in red (red = alarm to any finance-literate reader; here it's just a palette
   accent). *Evidence: `home--mobile.png` bottom half.*

### Eyes 2 — The returning daily reader (primary persona)

*Evidence: `brief--desktop.png`, `brief--mobile.png`, `brief-rendered.txt`, lens pages*

**What works:**
- The brief's structure is right: verdict → what changed → biggest movers (z-scored against each
  indicator's own typical swing — a genuinely sophisticated touch) → watching next → pressure
  list → category strip. It reads top-to-bottom in under two minutes. That's the correct shape
  for a daily product.
- The watching section with consequence-ranked predictions ("we expect 18.97¢/kWh — which would
  tip Electricity & the Grid to WATCH") is the most newsletter-like, forward-looking content on
  the site and the clearest "come back tomorrow" hook that exists today.
- Lens pages reward the click-through: prediction blocks under each chart, honest reads,
  journey-aware back links.

**What's missing from the daily loop:**
1. **On a quiet day, the flagship section says nothing happened.** Today's lead read: "No status
   changes today — a quiet day on the board." Honest — and the right instinct — but most days
   are quiet days, so the daily reader's first impression most mornings is an empty headline
   slot. The movers partially rescue it, but there's no daily narrative thread: nothing says
   *why* food costs are surging or connects today to yesterday. Every sentence on the site says
   *what*; none says *why*. This is the single biggest content gap vs. the products people
   actually read daily (Axios Macro, Chartr, The Daily Shot all lead with one human sentence of
   context).
2. **The brief has no memory.** Each day overwrites the last — no archive, no permalink, no "what
   did it say Monday?", nothing to share or cite. For a daily editorial product this is a real
   loss: a year of operation should produce 365 dated, indexable, linkable pages and produces
   zero.
3. **No push channel.** The daily loop depends entirely on the reader's self-discipline. RSS
   (footer-only) is a power-user channel; everyone else needs email. Every successful daily
   macro product is email-first for exactly this reason.
4. **Repetition reads templated.** The home hero sentence and the brief verdict are identical
   (the reader who clicks "Today's Brief" from home reads the same sentence twice within five
   seconds), and "Commodity costs are surging." appears verbatim twice on the brief itself
   (movers tile + pressure list). The copy bank is good; its reuse pattern is visible.

### Eyes 3 — The benchmark reader

Against what people actually use to stay informed:

| Benchmark | What they do that BA doesn't | What BA does that they don't |
|---|---|---|
| Axios Macro / Morning Brew / Chartr | Daily **email**; one human sentence of *why* per item; archive of every issue | Live badges, rules-based consistency, zero paywall/ads |
| The Daily Shot / Apollo's Daily Spark | Curated charts with editorial framing; brand distribution via LinkedIn/X | Plain-English verdicts a non-economist can read |
| Trading Economics / Finviz / Koyfin | Breadth, real-time quotes, screeners, **SEO dominance** (they own every indicator search) | Interpretation; "is this OK?" answered in words |
| FRED itself | Authority, permalinks for every series | A point of view; FRED tells you nothing about what a number means |
| Kalshi / prediction markets | Skin-in-the-game forecasts, social sharing of calls | Free, systematic, every-indicator coverage with public grading |

The differentiated core — **plain-English verdicts + published, publicly-graded predictions —
is real and worth defending.** Nobody in that table does both. But every one of them has
distribution BA lacks: email lists, social presence, link-preview cards, search rankings, or all
four. The benchmark conclusion is blunt: BA has built a better daily product than most of these
for its niche, and none of their audience.

---

### Dimension findings

**Content & insight quality — strong, one structural gap.** Reads are honest, specific, and
calibrated (two-sided housing, consumer-cost energy framing, banking quarterly cadence handled
correctly). The structural gap is the missing *why* layer and cross-category synthesis — the
About page itself names synthesis as the roadmap, correctly. Today the site states 33 isolated
facts; the connections (energy alert → cost-of-living elevated → sentiment alert is one story,
not three) are left to the reader.

**Editorial voice — distinctive and consistent**, occasionally exposed as templated (verdict
duplication, repeated sentences within one page, em-dash-heavy rhythm in every single read).

**Visual design & polish — professional, dark-theme, consistent.** The lens/hub/brief system
looks like one product. Nits: lopsided 8-tile home grid; accent-color-vs-semantic-color conflict
on home stats; clamped tile sentences truncate mid-word on mobile ("…parts of the…"); no
favicon-level brand mark beyond the SVG (no apple-touch-icon, no PWA manifest).

**Mobile — good, slightly verbose.** Static centered header works; charts are readable; the
hero stack (4-line mission + email + 5-line verdict) pushes live data well below the fold;
two-line nav wrap is acceptable but eats space. *Evidence: `home--mobile.png`,
`lens-recession-watch--mobile.png`, `brief--mobile.png`.*

**Information architecture — the revamp's clear win.** Four destinations, breadcrumbs,
journey-aware back links, slim hub with status-dot chips: it all scans correctly and the
hierarchy is learnable in one visit. One semantic nit: category hub `<h1>`s concatenate the
badge text ("Economic Lenses watch" is the actual h1 string — affects SEO snippets and screen
readers).

**Performance — excellent.** Home: 104 KB / 13 requests. Hub: 61 KB. Lens pages: 300–600 KB,
dominated by Chart.js from CDN (205 KB, cached across pages). Worst data file:
`market-scoreboard.json` at 332 KB (8 daily series; thinning is less aggressive than it could
be). `predictions/open.json` (53 KB) loads on every lens page. Nothing urgent.

**Accessibility — minor, fixable.** axe-core: `link-in-text-block` (serious; home-page footer
source links distinguishable only by color), `landmark-unique` (moderate; duplicated `.wordmark`
landmark on most pages). Charts have no text alternative per se, but every chart is paired with
a prose read, which is a reasonable equivalent. Status badges carry text, not just color. Good
bones.

**SEO & discoverability — the weakest dimension on the site. Effectively invisible.**
- A web search for "baileyanalytics.com economic dashboard" returns nothing from the site —
  Trading Economics, Bloomberg, and Russell Investments own the results.
- **No sitemap.xml** (404). No repo-owned robots.txt (Cloudflare's content-signals default is
  served). **No canonical URL on any page. No JSON-LD on any page. No og:image on any page** —
  every link shared to Slack/iMessage/X/LinkedIn unfurls as a bare text stub. `twitter:card`
  is `summary` with no image.
- **Raw HTML is a skeleton.** Lens pages serve 164 characters of static text ("Loading… The
  interactive dashboards require JavaScript"); the home page serves ~565. All reads, verdicts,
  and numbers are client-rendered from JSON. Google renders JS, but ranking on thin static HTML
  with zero inbound links and no structured data is a losing position — and non-rendering
  consumers (link unfurlers, AI answer engines, RSS readers' preview fetchers) see nothing at
  all. The irony: the pipeline *bakes* all this content into the repo daily as JSON; baking it
  into the HTML too is mechanically the same move.
- Per-page titles and meta descriptions are actually **good and unique** (someone did this
  right) — the foundation exists; the infrastructure above it doesn't.
- No custom 404 page.

**Trust & credibility — strong story, missing receipts.** Real name + employer + plain
disclaimers + primary sources + "first print frozen forever" methodology is a strong package.
Missing: the GitHub repo link (the entire verifiability argument depends on it), an empty Track
Record at launch (resolves itself within weeks as grades land — but can show open predictions
today), and zero external presence (no LinkedIn/X account, no other site linking in).

**Engagement & retention — the second-weakest dimension.** Channels by which a reader could
ever be reminded this site exists: an RSS link in two footers. That's the complete list. No
email, no notifications, no social accounts, no archive links that circulate, no share buttons,
no preview cards when links are shared manually. The daily product is built; the daily *habit*
has no delivery mechanism.

### What the revamp specifically got right / wrong

**Right:** the merge (one daily surface instead of two competing ones), the slim hub, V2 tiles
with sentences, journey-aware back links, the persistent 4-nav, honest empty states.

**Wrong / unfinished:** Track Record promoted to top-level nav before it has content and without
showing open predictions; home-hero/brief-verdict duplication; counts strip ("3 alert · 8
elevated · 3 on watch") rendered as inert text — it begs to be a link into the pressure list;
no share/subscribe affordance added anywhere during a revamp whose stated purpose was making
the site a daily destination.

---

## Part 2 — Ranked next steps

Ranking principle: the north star is a **regular audience**. Audience = acquisition × retention.
The product is ready; both loops are missing. Build the loops before deepening the product.

### 1. Make the brief subscribable — daily email digest (HIGH value / MODERATE effort)
The single highest-value move. The brief is already composed daily by `today.py` into
`today.json`; an email rendering of it (verdict → changes → movers → watching) is one pipeline
step plus an email-service integration (e.g., Buttondown — API-driven, free tier, handles
signup/unsubscribe/deliverability) plus a visible subscribe form on home + brief. Every
successful daily macro product is email-first because email is the only channel that reliably
creates a daily habit. This converts every future visitor from "hope they remember" into "lands
in their inbox at 7am." Without this, all acquisition work leaks.

### 2. Make the brief shareable & findable — distribution foundation pack (HIGH value / LOW–MODERATE effort)
Mechanical, one-time, compounding:
- **og:image cards** — bake a branded verdict-card PNG daily in the pipeline (Pillow; the
  stdlib-only rule is retired). Every shared link unfurls into a daily-fresh chart card instead
  of a text stub. This is the difference between links that circulate and links that don't.
- **Brief archive + permalinks** — bake `/brief/2026-06-12.html` daily. Creates shareable,
  citable, dated pages; 365 indexable pages/year of exactly the content Google has none of;
  enables "what did it say last week."
- **Static-render the reads** — the pipeline already knows every headline and key stat at bake
  time; patch them into the HTML it commits. Pages become meaningful to every non-JS consumer.
- **sitemap.xml** (pipeline-generated), **canonical tags**, **JSON-LD** (WebSite + Dataset),
  **custom 404**, repo-owned robots.txt, **GitHub repo link** on Track Record/About.
Items here are independently shippable; together they take the site from invisible to findable.

### 3. Quick wins sweep (MEDIUM value / LOW effort — bundle into either phase above)
Show open predictions on Track Record (kills the empty-flagship problem today); make the home
counts strip link to the brief's pressure section; differentiate home hero copy from brief
verdict (home = short form, brief = full form); fix accent-vs-semantic stat colors on home
tiles; fix `h1` badge concatenation on category hubs; axe items (`link-in-text-block`,
`landmark-unique`); thin `market-scoreboard.json`.

### 4. The "why" layer — synthesis & context (HIGH value / HIGH effort — the *next* phase after distribution)
The biggest *content* gap: connecting categories into one story ("energy costs → inflation →
sentiment" is one narrative, not three lens reads) and giving movers one line of why. This is
the roadmap's synthesis phase and it's the right successor — but it makes the product better
for an audience that currently has no way to arrive or return. Distribution first, then give
them this.

### 5. PWA-lite (LOW effort now, LOW value until there's an audience)
Manifest + apple-touch-icon + installability: an afternoon, worth doing inside item 2. Push
notifications: defer — notifications without an audience notify nobody.

### Honest weighing of the existing backlog
- **Perspective slicer (3-role)** — still V2. It deepens engagement for readers the site doesn't
  yet have. Defer behind distribution and synthesis.
- **Neutral-lens prediction exhibit** — right idea, wrong moment. Revisit when the track record
  has graded entries and the predictions section has earned attention worth spending on an
  educational exhibit.
- **Treasury/Census/BLS sources** — breadth is complete at 8 categories; the audit found zero
  evidence that more coverage is what's missing, and strong evidence that distribution is. Add
  sources when a synthesis or prediction feature needs them, not before.
- A note on sequencing luck: the first prediction grades land within weeks. That's a natural
  marketing moment ("we called 12 of 14 prints inside our bands") — but only if subscribe and
  share mechanisms exist when it happens. Another argument for items 1–2 now.

---

## Top recommendation

**Build the distribution phase: the daily email digest (item 1) plus the shareability/SEO
foundation pack (item 2), shipped together as one phase.**

Why this over everything else: the audit's central finding is that the site's weakest dimensions
are no longer product dimensions. Content, design, IA, performance, and credibility mechanics
all range from solid to excellent — while discoverability is near zero and retention has no
mechanism at all. The north star is explicitly an *audience*, and an audience requires exactly
two loops the site lacks: a way for new readers to find and share it (og:image cards, archive
permalinks, static-rendered content, sitemap) and a way for found readers to come back without
remembering to (the email digest). Both loops are cheap relative to everything already built —
the pipeline already composes the entire daily product into `today.json`; this phase mostly
*re-emits existing content* into the channels where audiences actually live. And the clock
matters: the first prediction grades land within weeks, the single best credibility moment the
site will have this year — the subscribe button should exist before that story is ready to tell.
