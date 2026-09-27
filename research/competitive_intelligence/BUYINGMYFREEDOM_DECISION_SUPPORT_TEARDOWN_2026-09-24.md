# BuyingMyFreedom Decision-Support Teardown — 2026-09-24

## Scope and source
This is a product-intelligence synthesis from the Chairman-authorized @BuyingMyFreedom archive crawl.
It is evidence for product design, not a trading authority, lifecycle owner, ranker, signal source, or claim that the public archive is complete.

Recovered corpus:
- 13,521 unique authored X posts;
- April 2019 through 2026-09-19;
- 3,001 represented media items;
- profile status counter was materially higher, so archive classification remains PARTIAL_ARCHIVE;
- full corpus mechanically classified; 1,687 unique high-information posts surfaced for bounded deep review.

External implementation assets/branding/corpora are not to be copied. Preserve the user jobs and lawful workflows with original implementation and Mastermind-owned data.

## External product model
The useful product is not primarily a newsletter, chart pack, autonomous AI agent, or novel indicator suite.
It is a human-led persistent market-decision workflow:

```text
regime / thesis
-> opportunity lane
-> scenario map
-> action zone
-> confirmation / invalidation
-> risk expression
-> WAIT / do nothing
-> evidence change
-> manage / exit / re-entry
-> outcome / correction
```

The subscriber job is compressed:
**tell me what matters, where the important decision area is, what would change the answer, and when I should stop touching the position.**
## Evidence-backed product characteristics
Recurring durable mechanisms:
1. one thesis survives many updates instead of becoming disconnected alerts;
2. zones and time windows are preferred to false exact-tick precision;
3. other instruments become explicit “North Stars” for thesis health;
4. WAIT / WATCH / UNKNOWN are valid states;
5. the same market thesis can imply a different expression for a different person;
6. existing-position management is different from new-entry timing;
7. self-quoted before/after chains provide continuity and proof;
8. communication becomes louder near inflection points and quieter when nothing changed;
9. exit logic is tied to objectives rather than pretending the exact top is knowable;
10. mental capital / user behavior is treated as part of the product.

Repeated input families in recent original/quote posts were approximately:
- technical structure: 20%;
- cross-asset / relative confirmation: 16%;
- time / cycle logic: 15%;
- macro / policy: 8%;
- sentiment / behavior: 6%;
- personal portfolio / goal planning: 5%;
- company fundamentals: 5%;
- positioning / flow: 3%.

These are lexical occurrence rates, not weights or win-rate evidence.
The strongest repeated combination was technical structure + cross-asset confirmation.

## Important calibration caveat
The public feed is not an unbiased performance ledger.
Explicit public “called it / target hit / mapped it” language appeared roughly five times as often as explicit “I was wrong” language in the bounded recent-core classification.
The workflow does publish corrections and uncertainty, but public proof naturally over-selects successful calls.

Mastermind must not copy that bias.
Every eligible lifecycle should accrue outcomes, including misses, invalidations, no-fills, RAN_DONT_CHASE, avoided bad entries, successful waits, corrections, and unavailable-data episodes.
## What Mastermind already has that is stronger
Mastermind already owns a materially richer estate than the reference workflow:
- canonical PIT identity and correction boundaries;
- Prophet candidate episodes and plan lifecycle;
- Live Entry Radar tactical-event ownership;
- Prophet Management phase/action/confidence/geometry;
- structured Prophet entry zones and no-chase ceilings;
- Foresight / Theme intelligence and falsifiers;
- Market OS `security_state.v1`;
- Evidence Foundation and Opportunity Evidence Vector;
- Alerts delivery / quiet hours / receipts;
- Portfolio, Watchlist, Thesis Objects and Portfolio Targets;
- options evidence and Options Alpha;
- outcome/replay/evaluation infrastructure.

The main product gap is therefore **composition and attention**, not raw indicator count.

## Current canonical product discovery — Decision Spine already exists
Fresh current-source + production proof on 2026-09-24 establishes that Mastermind already has the correct public composition surface:
**Security State — the Decision Spine**.

It is live on the public AAPL and MSFT dossier paths and currently renders:
- Overview / where it stands;
- What changed;
- Opportunity context;
- What could go wrong;
- What to watch next / next observable;
- Evidence;
- owner/model receipts.

A real six-case browser check over AAPL + MSFT at 1440, 820 and 390 widths showed zero horizontal document overflow.
MSFT evidence drilldowns opened and closed successfully at desktop/tablet/mobile.
Production-served AAPL/MSFT `security_state.v1` objects both reproduce their own `content_sha256`, carry PROVEN identity and retain all-false authority.
Bounded Market OS issue #6824 was production-accepted and closed on this proof.
## Decision Spine sub-capability gaps — current truth
The live public surface also makes the missing owner joins explicit.

Current Opportunity Context:
- Prophet outlook: UNAVAILABLE / `PROPHET_OWNER_OUTPUT_ABSENT`;
- Entry read: current incumbent entry read;
- priced-in / market incorporation: NOT_COVERED;
- dislocation / mispricing: NOT_COVERED.

Current Personal Impact:
- public page is deliberately `NO_USER_CONTEXT / NOT_APPLICABLE`;
- private Portfolio / Watchlist / Thesis state must not be written into public Macro artifacts.

Therefore: **do not invent another Decision Spine.**
Successor work should integrate existing owners into the existing spine.

Recommended architecture:
- public Macro Decision Spine = market/security context only;
- authenticated Terminal = private overlay over that same market truth;
- B4 = authoritative NEW ENTRY only after B4 is accepted and production-proven;
- Prophet Management = EXISTING POSITION management;
- Portfolio/Thesis/Targets = user-owned relevance/objective overlay;
- Alerts = existing event-driven transport;
- Opportunity Evidence Vector = existing display-only evidence composition primitive.

NEW ENTRY and EXISTING POSITION must remain separate axes.
A new buyer can truthfully be RAN_DONT_CHASE while an existing holder is HOLD.
## Concrete product defects found in current Prophet composition
### Live desk mixes resolved history into current attention
On the current 2026-09-24 Prophet payload:
- 426 plan rows;
- 190 RESOLVED;
- 148 ENTERED;
- 61 READY;
- 27 INVALIDATED;
- 236 unresolved/open.

Terminal master still computes Active Plans as `phase != invalidated`.
On the same payload this yields 349 “ACTIVE PLANS”, pulling 140 RESOLVED rows into the live count.

### BEST is not best-current-opportunity
Terminal `BEST` sorts by Prophet Management confidence.
The same product defines management confidence as trade-state confidence, not pick rank.

On the observed 2026-09-24 payload the first 18 BEST rows are RESOLVED history before the first current ENTERED row.
This is a composition defect, not a request for another ranker.

### Historical campaigns appear as duplicate live-stream rows
The unresolved/open population is identity-clean.
Duplicate ticker rows arise from resolved prior campaigns being mixed into the same plan stream.
History should remain accessible without being indistinguishable from current opportunity.

Canonical follow-up owner:
- Terminal issue #691 — separate current attention from resolved history;
- preserve #668 writer custody on `ProphetView.tsx`; do not race that branch.
## Material implementation effects already created from this research
### Opportunity Box
Terminal PR #689 is MERGED (merge `c025b82ab8de84d9fd9e0a45f350fb5038a6e708`).
It projects existing producer-owned live WAIT entry geometry into Prophet SignalCard:
- opportunity band;
- WAIT stance;
- no-chase ceiling;
- remaining session window;
- plan entry relabelled as Plan anchor when a live zone exists.

It does not derive ENTRY_OPEN and does not reinterpret filled/converted/HOLD/TRAIL/INVALIDATED bands.
The current production Terminal host contains the #689 merge, but authenticated end-user browser proof remains a separate acceptance obligation.

### Producer plan status / human-readable path state
Macro already publishes bilingual `pulse / pulse_zh` on every current Prophet plan row.
Terminal previously dropped it.

Terminal PR #741 now projects this as quiet `Plan status / 计划状态` context.
Local proof:
- 54 focused Prophet tests green;
- TypeScript green;
- focused ESLint green;
- forward-only plain-language guard green;
- desktop/tablet/mobile EN/ZH responsive browser proof green.

#741 is currently HOLD / merge-blocked because the required mobile CI shard reproduced the shared marker-tooltip nondeterminism owned by #485.
No retry-to-green and no marker-code copy was performed.

### Do-less event delivery
Terminal issue #692 records the successor requirement:
existing owner state -> material transition -> existing Alerts outbox/delivery.
No second watcher, queue, alert store, or outbox may be created.
## Product sequence from here
1. Finish the shared responsive-CI reliability owner so #741 can obtain lawful hosted release proof.
2. Reconcile #668, then fix #691 so the Prophet desk is an attention desk rather than a mixed historical ledger.
3. Integrate current Prophet owner truth into the existing Security State Opportunity Context; distinguish NO CURRENT PLAN from owner UNAVAILABLE.
4. Complete B4 owner/dependency reconciliation; consume B4 for NEW ENTRY only after production proof.
5. Connect selective evidence / “North Stars” through existing evidence and theme/macro owners; no universal opportunity score.
6. Route material changes through existing Alerts (#692) so unchanged opportunities become a calm “nothing material changed” state.
7. In authenticated Stock Intelligence, overlay private Portfolio / Thesis / Targets on the public Decision Spine instead of creating another state system.
8. Attach complete outcome learning to every opportunity episode; consume existing #668/evaluation owners instead of building a second ledger.

## Do-not-redo / authority guard
- no second candidate episode registry;
- no second entry-event store;
- no second Decision Spine / security-state store;
- no second Thesis DB;
- no second Alerts outbox;
- no second theme engine;
- no universal score made from Opportunity Evidence;
- no LLM-originated rank/gate/size/ENTRY_OPEN;
- no Watchlist treated as Portfolio ownership;
- no private user state persisted into public Macro artifacts;
- no management confidence reused as pick rank;
- no claim that CI green, merge, deployment, or local fixtures equal production acceptance.

## Current capability classification
- external archive method model: PROVEN_OUTCOME (bounded, partial archive);
- public AAPL/MSFT Security State Decision Spine surface: PROVEN_LIVE;
- #689 Opportunity Box code: merged/deployed; authenticated live user proof still owed;
- #741 Plan status: BUILT_NOT_PROVEN / release-held behind #485;
- #691 current-attention lifecycle repair: NOT_BUILT;
- #692 do-less alerts: SPEC_ONLY;
- B4 authoritative new-entry Availability: BUILT_NOT_PROVEN / dependency-owner held;
- private user-objective overlay over Decision Spine: NOT_BUILT.

This artifact is a product-intelligence record. It does not supersede source-owner contracts or accepted workstream authority.
