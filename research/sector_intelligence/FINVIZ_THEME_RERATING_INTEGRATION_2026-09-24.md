# Finviz theme/subtheme → Sector Intelligence re-rating integration

Date: 2026-09-24
Owner/parent: #7749 `sector-strength-measurement-20260922-sol-001`
This note is research + architecture, not trading authority.

## Executive finding

Finviz themes are **not fully integrated** into Sector Intelligence.

The estate already has a strong source-local Finviz plane:
- 40 themes
- 268 source subthemes
- ~941 unique tickers
- current multi-horizon subtheme/member performance
- PIT subtheme-performance history
- PIT tree-change history
- whole-market subtheme rotation / turn computation

What is missing is the higher-order interpretation the Chairman is asking for:
1. explicit single-stock vs narrow vs broad re-pricing shape;
2. a universal leader read that distinguishes raw price leadership from validated alpha;
3. cross-subtheme diffusion / rotation inside a broad theme;
4. fundamental/event/valuation confirmation of whether a price move is a durable re-rating;
5. a validated exit / rotate-out framework;
6. full semantic promotion from source-local Finviz concepts into the canonical GMI theme graph;
7. one coherent Sector Central workflow spanning Sector → Theme → Subtheme → Stock.

The implementation must extend existing owners. It must not mint another membership store,
rotation engine, theme-state plane, event system, ranking plane, or trade-authority plane.

## Current-source census

Observed code/source base for this slice:
`macro@1c58ce366754998c02a34109196ab1a7be8586ba`.
Later main movement through `5600bb63b27978031769eb428911fe9b46572a92`
did not touch this slice's owned paths when reconciled.

Existing source/owner chain:
- `scripts/fetch_finviz_themes.py`
  - source-local tree → `data/themes_heatmap/themes_tree.json`
  - current perf → `data/themes_heatmap/perf_snapshot.json`
  - PIT subtheme perf → `data/themes_heatmap/subsector_perf_history.jsonl`
  - PIT tree changes → `data/themes_heatmap/tree_history.jsonl`
- `engine/themes_heatmap.py`
  - owner projection → `site/marketdata/themes_heatmap.json`
- `engine/subsector_rotation.py` + `engine/subsector_turn.py`
  - owner rotation state → `site/marketdata/subsector_rotation.json`
- GMI source-local graph
  - Finviz local nodes exist at `ltheme:finviz:<subtheme_key>`
  - company → Finviz-local-theme membership exists with provenance

Important PIT limitation:
- member horizon returns are **not archived** in git.
- the collector intentionally archives only subtheme aggregates; member returns are
  reconstructable from the whole-market store.
- historical participation/concentration must reconstruct member returns against PIT tree
  membership rather than pretending today's member snapshot was historical truth.
- theme historical rollups in the incumbent rotation engine currently use today's subtheme
  membership when replaying the subtheme archive; `tree_history.jsonl` exists, so PIT
  re-derivation is possible but is a separate repair.

A stale collector module header incorrectly said `member_perf_history.jsonl` existed;
this slice corrects that documentation to the actual `subsector_perf_history.jsonl` contract.

## Rights boundary

`config/theme_sources.yml` marks `finviz_themes` as
`rights_class: unresolved` for NEW GMI public emission. Internal GMI computation is
allowed; new public GMI surfaces must fail closed until the rights decision is resolved.

Two owner products predate GMI and are explicitly grandfathered by path:
- `site/marketdata/themes_heatmap.json`
- `site/marketdata/subsector_rotation.json`

This first slice enriches the existing owner heatmap projection rather than creating a
new GMI public dataset. Future canonical semantic work remains internal until the rights
gate permits public emission.

## External research: why the hierarchy matters

### 1. Finviz itself has moved from sectors toward structural themes

Finviz's 2026-01-23 launch note says its Themes Map organizes stocks by structural themes
instead of sectors and exposes theme + sub-theme screening. Its AI example breaks the
theme into narrower categories such as Databases, DevOps, Compute and Models.

Source:
https://finviz.com/blog/new-stock-market-maps-for-market-cap-52-week-highs-lows-themes-and-insider-trading/

Finviz's 2026-09-08 Matrix launch makes the participation question explicit: the product
is designed to show whether strength is concentrated in the largest names or spreading
to smaller companies inside the same market area.

Source:
https://finviz.com/blog/the-finviz-matrix-market-breadth-visualized/

Implication for Mastermind:
taxonomy alone is not enough. A subtheme state needs participation and concentration
alongside return.

### 2. Group / industry momentum is economically meaningful

Moskowitz & Grinblatt (1999), "Do Industries Explain Momentum?", documents a strong
industry component to momentum and finds individual-stock momentum is substantially
reduced after controlling for industry momentum.

Sources:
https://www.jstor.org/stable/798005
https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00146

Implication:
a stock leader should be evaluated relative to its subtheme, parent theme and market.
Raw stock return alone confounds stock-specific leadership with a group beta tailwind.

### 3. Relatedness is richer than static sectors

Cohen & Frazzini, "Economic Links and Predictable Returns", documents delayed information
incorporation across economically linked customer/supplier firms.

Source:
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2758776

Ali & Hirshleifer, "Shared Analyst Coverage: Unifying Momentum Spillover Effects", finds
a connected-stock relation that subsumes several industry/geographic/customer/
supplier/technology momentum effects in their tests and interprets the pattern through
linked-firm information diffusion.

Source:
https://www.nber.org/papers/w25201

Hoberg & Phillips' TNIC work uses firm-centric product-similarity networks whose composition
updates over time; their data library argues that static fixed classifications miss dynamic
product-market relationships.

Source:
https://hobergphillips.tuck.dartmouth.edu/

Implication:
Finviz source-local subthemes are a strong observable taxonomy but should sit inside the
existing GMI relationship graph, not replace it. The graph needs multi-membership and typed
relations (product peers, supply chain, common bottleneck, customer exposure, technology,
competition) with vintage/provenance.

### 4. A price re-rating is not automatically a durable fundamental re-rating

Kovacs (2016) finds subsequent peer earnings announcements matter when they confirm an
initial earnings surprise and the industry has positive common-effect information transfer.

Source:
https://onlinelibrary.wiley.com/doi/10.1111/1911-3846.12210

Koo, Wu & Yeung (2017) finds the direction of peer information transfer depends on the
economic attribution: industry-wide trends / structural changes can transfer positively,
while competitive moves can transfer negatively.

Source:
https://onlinelibrary.wiley.com/doi/abs/10.1111/1911-3846.12308

Implication:
"peers went up too" is evidence of diffusion, not proof of durable earnings power.
Mastermind should join price participation to explicit event, revisions, earnings,
orders/backlog/capex and valuation evidence before calling a move fundamentally confirmed.

### 5. Leader detection should separate residual leadership from factor/group beta

Blitz, Huij & Martens' residual-momentum research reports stronger risk-adjusted performance
for momentum built from residual rather than total returns in their sample.

Source:
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2319883

Implication:
the eventual validated leader layer should estimate leader residuals vs market, sector,
theme and subtheme—not just pick the highest raw return.

### 6. Rotation/exit must be regime-aware

Daniel & Moskowitz documents momentum crashes concentrated in panic/high-volatility rebound
states.

Source:
https://www.nber.org/papers/w20439

Implication:
relative-strength rollover and breadth deterioration should be conditioned by macro/tape
regime. A violent rebound can punish simplistic continuation/exit logic.

## Desired product model

The user should be able to traverse:

`Sector → Theme → Subtheme → Stock`

and answer five different questions without conflating them:

1. **Strength** — what is already outperforming?
2. **Formation** — where is acceleration / diffusion beginning?
3. **Durability** — is price confirmation supported by fundamentals/events/revisions?
4. **Leader** — which stock is leading after removing group/market tailwind?
5. **Exit / handoff** — is breadth narrowing, leadership breaking, or relative strength
   migrating to an adjacent subtheme?

Those are separate evidence axes. Do not collapse them into one opaque score before
point-in-time evaluation proves that doing so improves decisions.

## Repricing state model

First deterministic descriptive states:

- `single_name_impulse`
  - positive subtheme aggregate but one positive member dominates the positive-return
    magnitude and participation is weak.
- `narrow_leadership`
  - positive group move with limited participation and/or high move concentration.
- `early_diffusion`
  - broad 1-week participation, but 1-month participation/history has not confirmed.
- `broad_price_repricing`
  - broad participation across 1-week and 1-month with no single-name domination.
- `mixed_positive`
- `mixed_negative`
- `leadership_break`
  - recent group weakness + participation break after positive 1-month group trend.
- `fading`
- `range`
- `insufficient_data`

These labels are descriptive. Thresholds are interpretable, not fitted.

## Leader model

### Now: price leader

The first slice exposes `price_leader`:
- observed horizons;
- number of horizons above member median;
- number of positive horizons;
- horizon returns.

It deliberately does **not** call this an `alpha_leader`.

### Required before "alpha leader"

A validated leader layer should add:
- market residual return;
- broad-sector residual return;
- parent-theme residual return;
- subtheme residual return;
- multi-horizon persistence;
- leadership breadth context (is the leader dragging or riding the cohort?);
- earnings/revision surprise vs peers;
- event/catalyst specificity;
- valuation re-underwriting vs earnings delivery;
- liquidity / tradability / coverage quality;
- forward walk-forward evaluation.

Only the evaluation ledger can promote the word "alpha".

## Durable re-rating evidence

Do not create a monolithic buy score. Keep named legs:

**Price**
- relative strength vs market/sector/theme/subtheme
- acceleration / turn state
- breadth and diffusion
- move concentration
- leader persistence / leadership handoff

**Fundamental**
- earnings surprise breadth
- estimate-revision breadth and acceleration
- revenue / bookings / orders / backlog
- capex / capacity / utilization
- gross-margin / operating-leverage inflection
- customer / supplier read-through

**Catalyst / structure**
- product cycle
- policy/regulatory
- supply bottleneck
- channel or pricing evidence
- customer capex / deployment evidence
- structural vs competitive event attribution

**Valuation**
- multiple change decomposed from earnings change
- peer-relative valuation
- own-history valuation
- implied growth / estimate delivery

**Crowding / fragility**
- extension
- options/call-skew/speculation
- concentration
- correlation spike
- liquidity/short-interest where owned
- regime risk

Evidence state can be:
`forming | confirming | mixed | fragile | weakening | insufficient`.

That state is still context-only until validated.

## Exit / rotate-out evidence

A rotate-out watch should fire evidence, not an order:

- participation deteriorates while group price remains elevated;
- top-name move concentration rises;
- leader residual turns down;
- incumbent turn engine moves to topping / turn-down;
- revisions breadth rolls over;
- peer earnings stop confirming;
- event narrative becomes competitive rather than industry-wide;
- valuation expands while earnings delivery stalls;
- crowding/extension rises;
- adjacent subtheme RS turns up while the current subtheme RS rolls over.

The existing relationship graph should identify plausible adjacent recipient subthemes;
the system must not infer "capital flowed from A to B" merely because A fell and B rose.

## Semantic integration

Current GMI fact:
Finviz local themes exist as `ltheme:finviz:<subtheme_key>`, but the Finviz plane has
zero accepted `local_theme → canonical_theme` expression edges. THS owns the currently
accepted local→canonical mappings.

Required path:
1. use the existing probation/adjudication owner;
2. propose Finviz local→canonical relationships with evidence;
3. permit unmapped as a legal state;
4. never fuzzy-map labels mechanically;
5. preserve PIT membership vintages;
6. expose public canonical derivatives only after the rights gate permits the intended use.

Do not create another crosswalk or theme identity plane.

## This PR slice

Carrier: `sol/sector-theme-rerating-shape-20260924`

Owned changes:
- new pure `engine/theme_repricing_context.py`
- existing `engine/themes_heatmap.py` consumes it
- new `tests/test_theme_repricing_context.py`
- stale collector PIT-header correction
- this research note

Projection:
`site/marketdata/themes_heatmap.json` remains the only output path. Each existing subtheme
tile gains a nested `repricing` context, and the payload gains theme-level repricing
summaries. No new store, scheduler, publication plane or UI path is created.

Authority:
- context/display only
- no rank authority
- no gate authority
- no sizing authority
- no trade authority
- price leader != validated alpha leader
- price participation confirmation != fundamental investment durability
- move concentration != market-cap contribution

## Real-snapshot smoke read

Against the committed 2026-09-24 Finviz snapshot at the slice base:
- 40 themes
- 268 subthemes
- shape counts:
  - 59 broad_price_repricing
  - 41 early_diffusion
  - 43 narrow_leadership
  - 12 single_name_impulse
  - 9 leadership_break
  - 65 fading
  - 18 mixed_positive
  - 21 mixed_negative
- theme rollups:
  - 16 broad_subtheme_diffusion
  - 13 isolated_subtheme_move
  - 7 mixed
  - 4 theme_fading

Semiconductors specifically:
- advancing subtheme share (1W): 1.00
- 7/9 subthemes = `broad_price_repricing`
- 1/9 = `early_diffusion`
- 1/9 = narrow/single-name
- theme state = `broad_subtheme_diffusion`

Examples:
- Memory: broad_price_repricing, 1W +18.77%, 100% observed members up.
- Design Tools: broad_price_repricing, 1W +18.02%, 100% observed members up.
- Packaging: broad_price_repricing, 1W +17.11%, 100% observed members up.
- Compute: broad_price_repricing, 1W +14.34%, 100% observed members up.
- Foundries: narrow_leadership, 1W +11.41%; current price leader = INTC.

These are diagnostics from descriptive thresholds, not a historical claim of alpha and not
a recommendation.

## Evaluation gate

Before any of these fields influence ranking, gating, sizing, or a buy/exit recommendation:

1. reconstruct member horizon returns from the whole-market price store;
2. join to PIT Finviz tree membership by each decision date;
3. replay the cohort-shape labels without leakage;
4. define forward outcomes separately:
   - group relative return 5/10/21/63 sessions
   - max drawdown / adverse excursion
   - breadth persistence
   - leader persistence / handoff
   - earnings/revision confirmation
5. compare:
   - incumbent rotation alone
   - incumbent + cohort shape
   - residual-leader features
   - fundamental confirmation legs
   - regime-conditioned variants
6. publish coverage, abstentions, confidence intervals and failure slices;
7. only then request authority promotion, if warranted.

## Next bounded verticals

1. PIT breadth replay from whole-market returns + `tree_history.jsonl`, consumed by the
   incumbent subsector track-record ledger.
2. residual price-leader context that reuses existing market/sector/theme owners.
3. fundamental durability join (revisions, earnings/event read-through, valuation) as named
   evidence legs, no fused trade score.
4. internal GMI Finviz semantic-probation expansion; no public emission while rights remain
   unresolved.
5. Sector Central consumer integration once the active redesign/heatmap PRs reconcile,
   preserving the Sectors / Themes / Subsectors hierarchy and avoiding collided UI paths.


## Continuation 2 — PIT breadth replay + revision durability

The next implementation slice closes two more gaps without touching the active
subsector-rotation carriers.

### PIT membership / price replay

New `engine/theme_repricing_pit.py` reuses the existing Finviz vintage owner
(`engine.theme_graph.local_sources`) rather than creating another membership history.
For any archived Finviz session it:

- chooses only the newest structure vintage known on or before that session;
- refuses dates before the first observed vintage;
- requires an actual NYSE session date;
- reconstructs 1W/1M/3M member returns on exact exchange-session endpoints;
- never forward-fills a missing member close;
- feeds those PIT members/returns back through the same repricing classifier.

New `scripts/replay_theme_repricing_pit.py` is a read-only harness over the canonical
`data/massive_stock_day` store. It uses the existing
`scripts.replay_standout_pipeline.split_adjust` repair and truncates the raw store at
the replay study's maximum date before adjustment. It checks local-mirror freshness and
refuses a missing/stale heavy store by default. No ledger or publication path is created.

A controlled end-to-end fixture includes a synthetic 10:1 split and proves the replay
uses the repaired price series, the correct structure vintage and exact session endpoints.

### Current real-data limitation

The MacBook worktree and the checked M1 Studio mirror contain the committed Massive
manifest but **zero local Massive parquet files**. The M1 manifest reports 21,593 tickers,
coverage 2021-07-06 through 2026-09-21 and zero recent missing runs, but that manifest is
not the R2 data itself. A real historical breadth replay is therefore deliberately
**not claimed** in this continuation.

The harness is now buildable and fail-closed; the real replay requires a legitimate
R2-restored runner/mirror. Do not substitute a stale or manifest-only checkout.

### Revision durability — named leg, not fused score

New `engine/theme_rerating_durability.py` generalizes the incumbent
`engine.theme_revisions.theme_revisions_for` rollup to the Finviz subtheme roster and
joins it to price participation without inventing a score.

The revision owner remains authoritative for:
- analyst coverage floors;
- revision breadth;
- coverage-normalized breadth where available;
- PIT broadening state;
- proxy broadening disclosure when history is insufficient;
- 90-day estimate drift.

The new join emits named two-axis states such as:
- `price_and_revisions_confirming`
- `price_leads_positive_revisions`
- `price_revision_divergence`
- `revisions_ahead_of_price_diffusion`
- `joint_weakening`
- `fragile_price_unconfirmed`

Every state remains display/context only. "Divergence" means the two observed axes
disagree; it is not a short/sell call.

The existing `scripts/build_themes_heatmap.py` now attaches this revision leg to the
same grandfathered owner heatmap payload when the revision store is present. When the
revision store is absent the join is an honest no-op and the price heatmap still builds.
No new public path or publisher exists.

### Real 2026-09-24 revision + price read

Read-only reconstruction used current Macro main
`773be812b89ccff610a248f187f8ac98b057fbbf` with exact tracked blobs:

- revisions latest: `2440f5dc809eafec7522aa061fd8d4993cd8565e` (1,542 rows)
- revisions history: `aae9bb4132da65b0faf512c02e9fb88dc216a4ca` (20,347 rows)
- Finviz perf snapshot: `d1a3ea82c4730684e8680122646473f390ff19d0`
- Finviz tree: `65b0e9e3f5f938aaf224130f0af14cd6922aafed`

Across all 268 source subthemes the revision states were:
- 98 broadening_confirmed
- 80 positive_but_rolling
- 23 negative
- 19 flat
- 37 insufficient
- 5 positive_level
- 6 positive_level_proxy_broadening

This immediately demonstrates why one sector score is too coarse: the same broad price
tape can contain confirming, rolling, flat and unmeasured fundamental revision states.

Semiconductor subthemes on that same snapshot:

| Subtheme | Price shape | Revision state | Revision breadth | Revision coverage | Joint read |
|---|---|---:|---:|---:|---|
| Compute | broad_price_repricing | positive_but_rolling | +0.364 | 6/8 | price_revision_divergence |
| Memory | broad_price_repricing | positive_but_rolling | +0.575 | 5/5 | price_revision_divergence |
| Analog | broad_price_repricing | positive_but_rolling | +0.829 | 6/7 | price_revision_divergence |
| Wireless | broad_price_repricing | flat | +0.041 | 6/6 | mixed |
| Foundries | narrow_leadership | insufficient | +0.600 raw level | 1/4 | fragile_price_unconfirmed |
| Design Tools | broad_price_repricing | positive_but_rolling | +0.698 | 5/6 | price_revision_divergence |
| Lithography | early_diffusion | broadening_confirmed | +0.644 | 3/5 | price_and_revisions_confirming |
| Packaging | broad_price_repricing | positive_level | +0.958 | 3/6 | price_leads_positive_revisions |
| Next-Gen | broad_price_repricing | positive_but_rolling | +0.784 | 7/14 | price_revision_divergence |

Interpretation guard: `positive_but_rolling` is still a positive revision level whose
PIT breadth derivative has rolled over. It is **not** "fundamentals are bad." Conversely,
Lithography's current price/revision agreement is confirmation evidence, not a buy call.

This is the granularity the Chairman asked for: Semiconductors can be broadly repricing
while the most durable evidence differs materially by Compute, Memory, Foundries,
Lithography, Packaging and the other subthemes.


### Group-relative leader candidate — still not alpha

The current repricing payload now also reports a `group_residual_leader_candidate`.
For each member/horizon it subtracts the Finviz subtheme return, then prefers leadership
that stays above the group across multiple horizons. This solves a narrower problem than
factor alpha: it distinguishes "highest raw return" from "persistently beating its own
subtheme."

The contract is explicit:
- group-relative only;
- not market-neutral;
- not sector-neutral;
- not factor-neutral;
- not forward-validated alpha.

On the same 2026-09-24 semiconductor snapshot, the group-relative candidates are:
- Compute: AMD, +5.58pp / +13.49pp / +17.53pp vs subtheme over 1W/1M/3M;
- Memory: SNDK, +0.74pp / +5.00pp / +5.53pp;
- Analog: MPWR, +8.74pp / +0.98pp / +12.11pp;
- Foundries: INTC, +9.92pp / +20.51pp / +8.63pp;
- Design Tools: ARM, +18.29pp / +25.22pp / +5.19pp;
- Packaging: COHU, +9.17pp / +10.72pp / +10.62pp;
- Next-Gen: AMD, +6.31pp / +24.52pp / +33.16pp.

Lithography's raw/group-relative candidate is ASML, but its 1W residual is negative while
1M/3M residuals are positive; the payload preserves that disagreement instead of calling
ASML a universal leader.

This is the correct intermediate rung before "alpha leader." The next promotion requires
market + sector + parent-theme residualization and forward evaluation; do not rename this
field to alpha merely because the candidate looks economically plausible.


## Continuation 3 — earnings / guidance confirmation

The durability join now consumes the incumbent **Group Earnings** owner rather than
inventing another event classifier.

`engine.group_earnings.member_event_context` is a public roster adapter over the same:
- earnings-season clock;
- Nasdaq surprise resolution;
- resolution-conditioned denominator / minimum-report floor;
- 8-K reaction-date matching;
- `guidance_gap` classifier and distinct-filer floor.

The Finviz adapter precomputes report events once across the full source-local universe,
then projects the same event map into each subtheme roster. It deliberately does **not**
compute Group Earnings' drift or sympathy legs unless a separately-qualified price matrix
and benchmark are supplied. Missing earnings/guidance evidence stays unavailable; it is
never treated as negative.

The durability contract keeps this as a separate `events` leg with states such as
`earnings_positive`, `guidance_positive`, or
`earnings_and_guidance_positive`. The existing `joint_state` remains explicitly
`price_plus_revisions_only`; adding event evidence does not silently change its meaning
or fuse three inputs into an opaque score.

### Current semiconductor earnings evidence (2026-09-24)

Using the tracked current earnings, Item-2.02 and guidance artifacts and the incumbent
Group Earnings rules:

| Subtheme | Classified current-season results | No-data members | Guidance band |
|---|---:|---:|---|
| Compute | 4 beat / 1 miss / 0 inline | 3 | unavailable (0 qualifying filers) |
| Memory | 5 beat / 0 miss | 0 | unavailable (0 qualifying filers) |
| Analog | 6 beat / 0 miss | 1 | unavailable (0 qualifying filers) |
| Wireless | 3 beat / 1 miss | 2 | unavailable (0 qualifying filers) |
| Foundries | 4 beat / 0 miss | 0 | unavailable (0 qualifying filers) |
| Design Tools | 3 beat / 1 miss | 2 | unavailable (0 qualifying filers) |
| Lithography | 5 beat / 0 miss | 0 | unavailable (0 qualifying filers) |
| Packaging | 6 beat / 0 miss | 0 | unavailable (0 qualifying filers) |
| Next-Gen | 7 beat / 2 miss | 5 | unavailable (0 qualifying filers) |

Memory also has MU on the tracked upcoming calendar for 2026-09-30 after-hours.

The correct interpretation is narrow: current classified earnings results are positively
skewed across these semiconductor subthemes, while the source does **not** currently
provide enough qualifying guidance-language breadth to claim management-guidance
confirmation at subtheme grain. This is stronger than a sector-only read because it
separates "earnings results confirm" from "guidance confirms" instead of blending them.
It remains context-only and is not a buy recommendation.


## Continuation 4 — leadership continuity vs leader replacement

The price layer now distinguishes **theme/subtheme health from leader continuity**.
A new `leadership` block compares the raw return leader at 1W, 1M and 3M and surfaces:

- `stable_multihorizon`
- `stable_recent_leader`
- `leader_rotation`
- `handoff_candidate`
- `fragmented`
- `insufficient`

`handoff_candidate` is intentionally narrow: the 1W leader differs from the 1M leader,
the new leader is beating the subtheme over 1W, and the former 1M leader is no longer
beating the subtheme over 1W. That is **price leadership continuity evidence**, not proof
that capital literally flowed from the old name to the new name and not a rotate/exit order.

This directly addresses a key failure mode of sector-only intelligence: a healthy theme can
keep re-rating while leadership rotates internally. A leader failing is therefore not the
same fact as a theme failing.

On the 2026-09-24 semiconductor snapshot:
- **Compute:** fragmented — 1W ARM / 1M INTC / 3M AMD.
- **Memory:** fragmented — 1W RMBS / 1M SNDK / 3M MU.
- **Analog:** handoff candidate — recent MPWR vs prior-medium STM; STM is now ~0.22pp
  below the Analog subtheme over 1W.
- **Wireless:** handoff candidate — recent MRVL vs prior-medium SWKS; SWKS is ~0.51pp
  below the Wireless subtheme over 1W.
- **Lithography:** handoff candidate — recent AMAT vs prior-medium KLAC; KLAC is ~0.47pp
  below the Lithography subtheme over 1W.
- **Foundries:** stable recent leader = INTC (3M leader remains TSM).
- **Design Tools:** stable recent leader = ARM (3M leader KEYS).
- **Packaging:** stable recent leader = COHU (3M leader ASX).
- **Next-Gen:** stable recent leader = INTC (3M leader NVEC).

This is the beginning of an honest "rotate inside the theme vs rotate out of the theme"
workflow: leader turnover is now machine-visible separately from breadth, revisions and
earnings confirmation. The eventual decision layer still needs PIT validation and the
existing rotation/turn owner before any action authority is considered.


## Continuation 5 — crowding / extension / valuation fragility

The durability read now carries a separate **fragility** leg rather than treating
"price is up" as equivalent to "there is still attractive runway."

Owner reuse is explicit:

- current price panel: engine.equity_factors._closes plus engine.baskets._basket_extras;
- market residuals: engine.narrative_rotation._market_residuals;
- member extension: engine.extension.extension_signals;
- group crowding: engine.theme_crowding.basket_crowding;
- per-name valuation blocks: engine.stock_fundamentals.valuation_context_for_tickers;
- valuation bands: engine.valuation.read.

No crowding formula, extension formula or valuation formula was copied into a new owner.

### Authority boundary

The fragility leg is display/context only.

theme_crowding's incumbent owner describes its own result as asymmetric size_down_only
texture. This Finviz durability contract does **not** adopt even that sizing authority:
the owner payload is evidence only, with may_rank=false, may_gate=false, may_size=false,
may_escalate=false, may_trade=false, and explicit can_support_exit_decision=false /
can_support_rotate_decision=false.

Likewise, valuation is a distribution of the incumbent per-name bands, never a new
subtheme valuation score. Missing names remain missing; they are not imputed cheap,
fair or expensive.

### Important PIT limitation

The live crowding/extension leg is a **current-roster historical texture**. It answers
"how the subtheme as constituted today looks against its own recent price history."

It is **not** the historical experiment. The PIT experiment continues to require
tree_history.jsonl + exact decision-date roster + point-in-time price reconstruction.
The output stamps current_finviz_roster_historical_texture_not_pit_backtest so the
live diagnostic cannot be mistaken for forward-validation evidence.

### Current-source runtime / coverage read

Read-only current-source probe against Macro main
90704bbea8f0fd3aabf28d07c315737d4caa8838 and the tracked 2026-09-24 Finviz /
valuation inputs:

- 268 subthemes processed;
- 256 / 268 had a usable crowding read;
- 52 / 268 met the incumbent crowding owner's crowded threshold;
- 242 / 268 had valuation coverage for at least three members;
- 66 subthemes had at least one currently parabolic member;
- 61 additional subthemes had stretched members without a parabolic member;
- the shared, once-per-universe computation completed in ~17.1 seconds on the local
  development Mac, materially faster than the earlier per-subtheme ~50s probe.

The extension owner also emitted its existing marginal-anchor warning: the 2026-09-23
shared anchor had 62.2% coverage versus its 60% floor. That warning is preserved rather
than hidden.

### Semiconductors — fragility is not uniform

On the same current snapshot:

| Subtheme | Crowding | Extension texture | Valuation coverage / distribution |
|---|---:|---|---|
| Compute | z 0.98, not crowded | no stretched/parabolic members in covered set | 6/8 covered: 1 cheap, 2 fair, 2 stretched, 1 extreme; 5 forward-P/E names, median 38.6x |
| Memory | z 0.66, not crowded | not extended | 3/5: 2 cheap, 1 fair; forward-P/E median 6.8x on 2 names |
| Analog | z 0.31, not crowded | not extended | 6/7: 1 cheap, 1 fair, 4 stretched |
| Wireless | z 0.87, not crowded | **20% parabolic / 20% stretched** among covered members | 6/6: 3 cheap, 2 fair, 1 stretched |
| Foundries | crowding unavailable — only 1/4 names had sufficient history in this price panel | unavailable | valuation only 1/4, that one extreme; insufficient for a group claim |
| Design Tools | z 0.42, not crowded | not extended | 5/6: 3 fair, 2 stretched |
| Lithography | z -0.23, not crowded | not extended | 4/5: 1 cheap, 2 fair, 1 stretched |
| Packaging | **z 1.81, crowded** | extension breadth unavailable at the owner floor | 4/6: 1 cheap, 2 stretched, 1 extreme |
| Next-Gen | **z 1.22, crowded** | not extended | 7/14: 1 cheap, 4 stretched, 2 extreme; 4 forward-P/E names, median 39.0x |

This is precisely why "Semiconductors is risk-on" is too coarse. Packaging and
Next-Gen currently carry materially more crowding/valuation fragility than Memory or
Lithography, while Wireless has a different hazard: per-name parabolic extension
without the basket-level crowding flag.

### Rotation / exit interpretation law

The eventual rotate-out workflow should not fire because any one fragility leg is high.

The defensible evidence sequence to evaluate is:

1. **theme/subtheme health** — participation and relative-strength shape;
2. **leader continuity** — stable leader, internal handoff, fragmented leadership;
3. **fundamental confirmation** — revisions + earnings/guidance;
4. **late-cycle fragility** — crowding, extension, valuation;
5. **incumbent turn/rotation owner** — topping / turn-down / adjacent relative-strength
   improvement;
6. **macro/tape regime** — because momentum failure behaves differently in rebound /
   panic regimes.

That creates the distinction the product needs:

- **healthy theme + leader handoff** → possible rotate *within* the theme;
- **healthy theme + high fragility** → late-cycle / do-not-chase context, not automatic exit;
- **theme weakening + revisions/events weakening + fragility elevated** → candidate
  de-escalation evidence;
- **adjacent subtheme strengthening** may identify a relative-performance handoff watch,
  but never proves literal capital flow.

No action authority is promoted until those combinations are evaluated point-in-time
against forward returns, drawdown and false-exit cost.
