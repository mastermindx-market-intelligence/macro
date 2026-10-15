# Prophet product implementation — 15 October 2026

Status: active implementation specification; no design acceptance or release claim.
Commission: Chris's rejection of the deployed replacement cards and request for the complete Paper-informed Prophet system. Original root/parent: 01a11e89-b35d-7a81-9404-5fce2c6170cb.
Canonical programme: macro#6817/comment6107291350. This specification refines the existing R6 mission; it does not replace its research, source, or scientific contracts.

## Outcome and failure being corrected

Prophet must help a person discover an opportunity early, understand its business and price evidence, compare alternatives, identify what must happen before acting, follow the original plan, and learn from actual outcomes. Richness means useful detail and working connections, not bigger rectangles.

The rejected shipped surface enlarged the shared legacy card using _prophet_workspace.css.j2 without supplying Paper's fuller information anatomy. The visible result has blank vertical space, weak separation of identity and context, missing chart/quote explanations, and an isolated Setup detail control. Functional and publication proofs did not establish visual quality. Chris's rejection is a material invalidator of product acceptance; those earlier technical proofs retain their original technical scope.

The replacement must preserve the intricate useful information in the old cards. Do not remove charts, cautions, maturity, price/zone, company context or history merely to produce a cleaner screenshot.

## Evidence and design selection

Paper file: 01M3NT5Y3G5HTJHVR0K5W2MDJM.
All 11 pages inventoried: 176 boards including one empty frame; 175 nonempty board-content reads. The source-only baseline has an oversized tree and invalid 1px screenshot, so its pixel rendering is not accepted evidence. Representative screens across the other ten pages have been visually examined; fetching a board tree does not imply visual acceptance of every variant.

| Paper page | Use in the product | Changes needed |
|---|---|---|
| 07 / p-A-0 Opportunity workspace | Primary card anatomy; Today, mixed strategy cards, mobile, setup, comparison, saved return | Complete real fields; remove empty padding; align card sections; simplify operational copy |
| p-7-0 R3.1–3.9 Setup/Evidence/Playbooks | Chart and timing workspace, supporting/opposing evidence, source inspector, level map and management | One detail shell with task tabs; no duplicate summary; chart controls must operate on real series |
| p-3-0 R2 Today/Setup/Plans | Model plan book and original plan detail; tablet layouts | Compact review queue, original entry/levels and changes; no inference of user holdings |
| p-4-0 Screener | Complete population, grid/table, filters, selection tray | Same identity/order as native population; compact and rich density variants; no separate ranking algorithm |
| p-1-0 Daily Brief / Compare / Changes | Brief summary, aligned comparison, change log, recovery states | Collapse the oversized marketing hero; move builder contracts out of product UI |
| p-8-0 Quote/Assessment review | Independent freshness and correction/return states | Use compact source/health disclosure; avoid turning a quote refresh into a new assessment |
| p-5-0 Shared contracts | Loading/empty/error/access/correction behavior and journey state | Enforce as component behavior, not permanent warning blocks |
| p-2-1 Regions | Market-specific identity, currency, clocks and recovery semantics | Reuse the shared component; region capability follows actual native data, not copied US coefficients |
| p-9-0 R6 flagship study | Case-for/case-against and historical price-map reference only | Not the card grid; prior rejection remains; no automatic approval from a screenshot |
| p-B-0 rejected text-row family | Negative reference and preserved interaction ideas only | Do not revive its text-row direction |
| p-6-0 source-only live baseline | Legacy information/behavior preservation checklist | Never use as a design target |

Concrete starting references: L3E-0 light Today, LPF-0 dark Today, M81-0 Chinese dark, MHC-0/MP1-0 mobile, PCL-0/Q9K-0 mixed strategies, LKU-0 setup, 8OM-0 evidence, A49-1 playbook, 4MM-0/4U6-0 plans, 2Z0-0/3NO-0 screener, G9H-0 comparison. These are selected working references, not a claim of Chris's taste approval.

## Product structure and connected journeys

Keep the existing global product navigation. Prophet-local primary navigation remains Today, Screener, Plans. The strategy selector distinguishes Early Leadership, Earnings and Cycle; it does not assign a strategy from a ticker or technical pattern.

1. Today answers what deserves attention. A compact brief summarizes actual changes and coverage, followed immediately by rich opportunity cards in native selected order. Early Radar is an explicit view of developing observations, not a second action list.
2. Screener preserves the complete supported population, including off-board and excluded candidates with their actual reasons. Grid/table and filters preserve the underlying order and counts. Compare preserves ordered canonical identities.
3. Setup is an instrument-analysis workspace: identity and quote header; Structure & timing, Evidence, Connections, Market Memory, Changes tabs. Previous/next navigates the retained originating selection. Back restores filters, scroll, focus and selection.
4. Evidence distinguishes supporting, challenging and missing observations. A source inspector opens beside the evidence list, then returns to the same item. Reading a caution never resolves it.
5. Compare aligns up to three resolved opportunity identities by strategy, quote, assessment, terms, strongest support and strongest challenge. Different horizons/units remain explicit. Mobile uses two readable columns or an explicit selected-pair control; no whole-page overflow.
6. Plans exposes the original model record, lifecycle, invalidation, targets, next review and material changes. It is separate from an actual brokerage position or fill.
7. Connections reuses current GMI/theme/company intelligence. Market Memory reuses permitted comparable episodes, differences and outcomes. Track record remains a dedicated auditable view; it cannot imply measured alpha from illustrative examples.
8. Save uses the existing list/persistence owner. Save, compare, notes and return context are distinct actions. An uncertain save response stays on its original operation; no duplicate write.

## Visual direction and improvements

Calm, precise investment research. The visual interest comes from chart structure, information hierarchy, deliberate material depth and aligned content—not decorative gradients or an excess of badges.

Dark: existing charcoal canvas and separated panel depths; restrained semantic top rail; lucid text and muted secondary lines; no luminous green border around an entire Featured card.
Light: cool canvas, white card material, fine neutral boundaries and subtle shadow; stronger typographic hierarchy; semantic color confined to status, chart/quote semantics and entry terms.
Use existing theme.css tokens only. These are two deliberate treatments sharing anatomy and behavior, not two unrelated palettes. Preserve the site's EN/ZH color convention and translation semantics.

Opportunity card anatomy, in order:
- Status and quote: short supplied stance, separate supplied strategy/horizon, tabular price/delta. No invented delta, status, probability or horizon.
- A continuous 64–76px chart with its own observation label and compact date. Missing history uses a deliberate neutral chart state, never a fake flat line.
- Ticker/company, industry/sector and the meaning of priority. Do not hide identity behind a decorative initial/avatar.
- A concise supplied setup observation plus the most consequential caution. Do not repeat the badge in a sentence. Detailed cautions expand from a labelled control.
- Maturity/evidence progress, with strategy-native labels. Early maturity cannot be reused as an Earnings or Cycle lifecycle.
- A context link when actually available.
- A structured terms band: dated zone or milestone and its own publication information. Quote freshness must not rewrite it.
- A quiet action footer: compare on the left, View setup on the right; secondary save on detail. No floating isolated button and no full-card link covering other controls.

Content controls height. No minimum-height spacer to force alignment, no blank 100px body reserve, no auto-growing chart that pushes the actions offscreen. Align semantic rows within a rendered grid using actual structure. Four rich cards at wide desktop; three/two/one as space requires. Dense Screener may offer a separate compact variant preserving the same information through deliberate disclosure. Mobile is a complete usable card, not desktop text clipped into a narrow column.

Copy: customer language, not "owner-Featured", "exact source", "native binding", PR IDs or receipt slugs at rest. Missing facts get a short specific label ("Quote unavailable", "Event date unverified") beside the affected fact. One compact health disclosure explains what still works. Detailed mechanics belong in the inspector.

## Backend and algorithm chain

No parallel store, ranker, entitlement system, quote service or lifecycle is authorized by this design.

| Responsibility | Existing implementation to extend | Required proof/remaining work |
|---|---|---|
| Selection and order | scripts/build_stock_library.py, native Today projection | Retain selected identity/order, no UI re-ranking |
| Candidate and clocks | engine/prophet_candidate_state.py and _sources.py | Same generation/episode, immutable native input binding, typed missing state |
| Brief and evidence | engine/prophet_daily_brief.py, _evidence_sources.py, app/prophet_daily_brief.py | Request-scoped composition, bounded cost, actual production identity and response |
| Card presentation | Existing native row -> an explicit presentation adapter -> new opportunity macro | Field provenance table; missing values stay missing; no policy in Jinja/JS |
| Setup/plan relation | Existing setup and Plan readers, original relation contract | No ticker-only Plan join; original levels and distinct management clock |
| Quote/series | Existing quote and chart owners | Separate quote and series timestamps, late-response ordering, no stale relabeling |
| Evidence/Connections | Existing evidence, GMI, EIOS, company intelligence | Actual source identity, observation time, coverage and rights |
| User continuity | Existing view/return state and saved-list owner | Same-user isolation, ordered identity, uncertain operation reconciliation |
| Delivery | Existing protected source/CI/render/API adoption | Exact source -> deployed bytes/process -> authenticated customer journey |

Presentation adapter fields are a read model, not a new authority. For each field record producer symbol/key, identity/clock, units, null behavior, entitlement and UI use. Classify missing work into existing data not rendered, existing endpoint not connected, or genuinely absent production capability. Implement the first two immediately after source qualification; the third needs its actual producer contract, not a placeholder narrative.

Research systems retained from the master plan:
- Early Leadership: source-qualified nominations and original episodes; strategy-native entry validity, risk and next confirmation. No ACTIVE/calendar/horizon-based renewal.
- Earnings: comparable issuer/event periods, actual expectations where licensed, revision and realized response separation, remaining opportunity; D5/Gate E proof retained.
- Cycle: demand, margins, cash generation, financing/dilution, issuer survival, milestones and holding law; coverage/era/rights gates retained.
- Ranking: reuse the incumbent qualified ranking; missing evidence and strategy incompatibility remain explicit. Any challenger requires distinct origin/current-landmark features, held-out eras, honest episode counts, costs, coverage and promotion proof.
- Learning: preserve decisions as known then; classify missed discovery, filtering, ranking, late delivery, infeasible entry and management failures separately. No reconstruction of missing prospective history.

## Implementation sequence and acceptance

A. Build the additive opportunity component against this frozen anatomy and exact Paper references; test complete/missing/long-label/caution/bilingual variants. Do not connect it to production before its data adapter and visual review.
B. Map real producer fields and implement the adapter at the existing consumer boundary: dashboard.html.j2 -> _us_board_cards.html.j2, with scripts/build_site.py rendering the same partial into the premium payload. The unrelated us_stocks_v2.html.j2 is an old unlinked preview, not this delivery target. Preserve old useful fields and all entitlement/selection behavior. Integrate Today and Screener on the same component.
C. Complete the setup/evidence/compare/return slice using existing unfinished carriers where their ownership and effects are clear; do not duplicate lost reviews or overwrite held work.
D. Connect Plans, changes, saved return, Connections and Market Memory; each control must accomplish the advertised task.
E. Complete research-source gaps and actual native runtime adoption. Parallelize nonconflicting Fabric leaves; parent owns composition, visual judgment and integration.
F. Ordinary CI/review/release, actual covering publication, authenticated real-data workflow and explicit visual comparison to selected Paper references. Keep the legacy useful experience until replacement capability is demonstrated.

Required visual matrix: EN/ZH × dark/light × 1440/390, plus 320px stress. Inspect content-rich, missing quote, missing assessment, caution expansion, invalidated/history, empty/filter-empty, loading/error/access, long price/name, comparison selection and return. Desktop 1440×900 shows an immediate answer and at most two supporting modules; no horizontal page scroll; keyboard focus and touch controls work.

A screenshot count is not acceptance. Compare hierarchy, density, material treatment, chart readability, all visible fields and actual interactions. The present product remains rejected until the replacement meets that bar. No source-only or fixture-only completion claim.

## Current concrete constraints

Paper reads work. Paper writes are blocked by UPSTREAM_SCHEMA_UNREVIEWED: actual catalogue 48b2587455d839a57b4b78f5cfdb2e75df8d530ad8059a3ad6af303c0d37224f differs from accepted ac18857df0aa6323646333368e5798e7c28de7b4d5f5dc3cb320276e3535daa9. No retry, alternate connector or pin change. This spec is not a Paper edit.

The recorded Chrome-extension consent gate remains unresolved; no unchanged retry or alternate automation. Build/test/source work proceeds, while native visual/customer verification retains that precise gate.

PR9369's canonical CI has one blocking timeout; its original review is lost/worker-unknown. Existing PR9272/9294 and original ATR recovery retain their exact unresolved review/effect boundaries. They are dependencies to integrate lawfully, not evidence that this entire product must wait.
