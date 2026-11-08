# PCE Release Bridge — architecture and delivery contract

## 0. Acceptance gates

**Owner:** CEO Sol. **Chairman direction:** take leadership of the CPI/PPI-to-PCE assessment and Calendar Release Radar proposal. **Existing parent:** WS:RATES-INFLATION-COMMAND. **Evidence projection:** Macro #7030. **Operation:** `release-radar-pce-bridge-20260910-sol-001`.

This document records an approved product direction and an architecture baseline. It is **SPEC_ONLY**, not an admitted numerical model, source implementation, deployment or Executive Job. The detailed numerical source map and model preregistration remain open entrance work. All eventual outputs are descriptive/display-only until separately admitted; no rank, size, gate, trade or fixed policy-probability authority is conferred.

The program is not complete unless a user can move through the real existing calendar and Release Radar from a scheduled CPI/PPI release to accepted component information, a separately identified PCE estimate and explanation of its change, the relevant policy context, and later official-release reconciliation. The existing machine/assessment consumers must receive the same versioned interpretation. A schema, data store, mockup, historical backtest or green CI alone does not satisfy this.

Every product wave needs real inputs, deterministic failure states, exact input/model/target/version receipts, a visible consumer, responsive browser evidence and published machine readback. Final learning evidence must show source availability, update latency, estimate changes, exact-cohort errors and user investigation behavior without counting repeated renders as independent forecasts.

### Pins and authority

- Procedure: `mastermindx-market-intelligence/Mastermind@dd553d1b0b8eed9511da2d3d5ec02cc9cd8edca1`, Skillpack 1.0.1, bootstrap-major 1. INDEX, COLD_START, COMMISSION_WAVE, WORKER_AVENUE_ROUTING, routing addendum, chat-native hierarchy, dialogue-close and CLOSEOUT read from that commit.
- Initial implementation archaeology: Macro `ea9ab6da455d8a31ec9a5323a37cb06bcd271b0f`.
- Records branch base: freshly observed main `74b144bc10b00df23d87f5dd1846627ebd9b0ee1`; no older shared checkout was advanced.
- Current protected law, current Chairman direction, source-owner boundaries and `DEC:RIC-CANONICAL-COMPOSITION-BOUNDARIES` govern. Retrieved packets supply evidence, not independent authority.
- Relevant DNR boundaries read at the archaeology pin: `DNR:KILL-POLICY-TIMING-PREDICTOR`, `DNR:KILL-CALENDAR-GATED-RISK`, and `DNR:KILL-CPI-REVISION-MODEL`. This program does not revive those constructions.

## 1. Product thesis and enduring advantage

The user job is to understand what a newly released report changes about the next important macro decision, rather than receive another disconnected headline. The machine job is to maintain a correction-safe chain from source fact through mapped component and estimated target to downstream descriptive context.

The proposed advantage is a longitudinal, versioned record of incremental information: which source mattered, at which stage, for which target, under which measurement method, and whether the explanation and estimate proved useful. Faster collection may help, but being faster than professional markets is not assumed. Neither a social post nor an LLM summary constitutes a calibrated signal.

The full ambition includes core and headline PCE, successive release stages, policy context, actual market-reaction comparison, historical/forward learning and useful research navigation. Delivery begins with one vertical at a time. Core first is sequencing, not permanent exclusion of headline.

## 2. Capability ledger and no-rebuild map

The classifications below concern the proposed bridge. Existing-source presence is not an assertion of present production liveness.

| Capability | Observed state | Exact reuse boundary |
|---|---|---|
| Unified event schedule | Existing source; bridge linkage PARTIAL | `engine/event_calendar.py`; retain its event identity and context-only tier |
| PCE forecasts | Existing source; detailed bridge NOT_BUILT in inspected feature path | `engine/release_targets_v11.py`; preserve current numerical models and historical identities |
| Official publication detection | Existing source; intraday derived-PCE consumer NOT_PROVEN | `scripts/watch_release_publications.py`, `scripts/official_release_parsers.py` |
| Canonical actuals, corrections, forecast and score records | Existing families; proposed detail extension PARTIAL | `engine/release_actuals.py`, target-truth family, `scripts/build_release_forecast.py` |
| Release Radar selected-model semantics | A1 specification/current receiver; not claimed accepted here | #6868 and its actual producer/renderer seam |
| PPI broad component truth | D0 SPEC_ONLY in recovered issue | #6883 covers broad Table 1 partitions, not a complete PCE mapping |
| PCE-to-policy calendar | Existing source; dynamic bridge join PARTIAL | Merged #499; `scripts/build_policy_watch.py` and `templates/policy_watch.html.j2` retain catalyst-spine handling |
| Detailed current BEA method map | PARTIAL research seed | Source-method review below; no machine admission yet |
| Proposed product/assessment update | SPEC_ONLY | Extend existing output/consumers after owner reconciliation |
| Predictive or trading advantage | NOT_PROVEN | Matched cohorts, PPI ablation, forward evidence; trading is outside this program |

Current inspected Policy Watch builder reads `intel.catalysts.spine`, computes date countdown/past flags and passes that block to its template. It is not evidence of a live CPI/PPI component bridge. The current #7017 changed-file list includes `scripts/build_policy_watch.py`, `templates/policy_watch.html.j2`, `engine/policy_watch_current.py` and associated tests; that is an actual overlap, not a reason to create a parallel spine.

The Release Radar producer already has upcoming-item construction, provenance attachment, shadow attachment, forecast rows, scoring, enrichment and publication. Its `build` entry point and `data/release_forecast/latest.json` remain the producer/artifact home. A new leaf must feed that family; no second public forecast JSON or alternate scoring store is proposed.

## 3. Source-method research: confirmed seed and unresolveds

Source citations are research references, not first-observed numerical receipts. Raw first-print component bytes, exact series codes, seasonal transforms, vintage weights and historical availability still require admission.

The December 2024 BEA handbook's Table 5.B identifies physician, hospital/nursing and domestic scheduled passenger-air PPIs for relevant price methods. Its dental row names CPI, while the BLS healthcare factsheet lists dental PPI among PCE inputs. Those documents do not establish a reconciled current dental mapping. [S1, S2]

BEA's announced September 30, 2026 update changes portfolio-management/investment-advice measurement and selected legal/software price methods. The old portfolio PPI method cannot be assumed valid for that publication vintage; the announced employment input is a quantity extrapolator, not a price index. [S3]

### R0 source-review return: closed eight-row scope

Return one table for: (1) physician services; (2) hospital services; (3) nursing services; (4) dental services; (5) domestic scheduled passenger air transport; (6) portfolio management/investment advice; (7) legal services; (8) computer software/accessories.

For each row identify the official PCE category, price versus quantity versus nominal role, exact BLS/BEA source codes where the primary sources actually identify them, seasonal status, available publication/vintage history, required composite or adjustment, publication-method applicability, and current disposition. Dispositions are `verified_direct_mapping`, `verified_composite_requires_inputs`, `historical_only`, `source_conflict`, or `unavailable`. A plausible proxy is not a verified direct mapping.

The reviewer must resolve the dental discrepancy with applicable primary-source evidence or retain it explicitly. It must distinguish the old and newly announced portfolio/legal/software methods without choosing a method from retrieval date alone. A list of source titles is insufficient when numerical implementation requires unpublished composite details. Search failure is reported, not replaced by a guessed coefficient or source code.

For admission later, preserve exact permitted source bytes or accepted existing-family receipts and hashes. Public document re-fetches are retrospective observations. Never assert that a document retrieved after release was captured before release.

### Weight, aggregation and coverage rules

CPI/PPI relative importance is not the PCE aggregation denominator. PCE's formula, weights and coverage differ from CPI. [S4] Each model must declare its own PCE expenditure-share source, effective period, core exclusions and aggregation approximation before a result is inspected.

An approximate weighted contribution bridge may be useful, but it must disclose aggregation and seasonal residuals rather than claim exact Fisher-chain replication. An exact replication claim requires the corresponding exact price/quantity inputs and demonstrated reconciliation. Do not force residuals to zero.

Observed-source coverage, legally usable-source coverage, economic-basket coverage, modeled/prior share, model attribution, interval coverage and empirical accuracy have different denominators. They must not share a synthetic confidence percentage. A missing/conflicting leg may retain an explicitly preregistered prior and its true weight, or make the candidate unavailable; it may never disappear through renormalization.

## 4. Time, identity, null and correction contract

Use existing economic release identities. Require explicit reference month and target basis: headline/core, month-on-month percentage change, seasonal basis and intended publication version. Calendar proximity or the first row in a queue is not sufficient identity.

Preserve these clocks separately: scheduled release time, source-declared publication time when available, first successful observation, acceptance/verification, frozen model cutoff, compute completion and publication/readback. A rebuilt file is not fresher source evidence. Date-only data cannot support invented intraday precision.

Source-stage labels derive from eligible input receipts, not assumptions about order. Support before both, CPI-only, PPI-only, both, official PCE and corrections. A release being published does not imply every detailed series needed by the bridge has arrived.

A forecast freezes input receipts, target month/basis, method/model epochs, decision cutoff, stage, weight vintage and code receipt. Newly arriving or revised evidence creates a distinct update under the existing identity/version convention. Identical replay is idempotent. A correction is not a second independent economic surprise.

Separate publisher revision, our parser/mapping correction, method change and late observation. Retain the first forecast and first accepted actual. Unsupported conflicts are quarantined under the existing correction owner; neither newest-ingested nor a matching numerical value chooses truth.

Valid zero is data. Absent, stale, unavailable, future-dated, wrong-month, malformed, Boolean/nonfinite numeric and conflicting input states remain distinct. No source time, point, quantile, consensus, PCE weight or policy probability may be invented to fill a blank.

## 5. User experience and machine contract

Use the existing Release Radar card and calendar detail, with an optional deep link to the existing Policy Watch catalyst context. No new top-level navigation or second dashboard.

**Glance:** target month; a plain-language readiness/outlook state; what changed; next relevant source; source freshness. Before numerical admission, say that the estimate is not available rather than displaying a placeholder value.

**Detail:** linked CPI/PPI/PCE event identities; source components observed versus pending; methodology-change warning; current/prior derived estimate and contribution explanation only when supported; explicit prior/unmodeled remainder; benchmark basis and timestamp; official first print and subsequent corrections when available.

**Assessment:** transmit one existing-family descriptive context block that distinguishes official facts, model-derived change, conditional policy interpretation and actual market repricing. A language model may narrate that block and disclose gaps, not manufacture the numeric bridge. A future reaction study must timestamp market observations and isolate overlapping announcements.

The future additive item field may be named `pce_context`; final naming and integration belong to the accepted current producer/consumer owner. Required semantics are fixed: target identity, component/source-stage states, method applicability, verified clocks, unavailable reasons, descriptive-only authority and references to existing receipts. In P1 there are no new estimate, quantile or policy-probability fields. P2 adds model-owned values only after preregistration.

Dark treatment must reuse current command-center card materials, restrained emphasis and instrument hierarchy. Light treatment must reuse the corresponding research-workspace materials, white/cool surfaces and hairlines, not a token-only inversion. EN/ZH meaning, ordering, interactions and state behavior are identical. Desktop 1440, tablet 768 and mobile 390 layouts must preserve legibility; overflow/raw internal identifiers are failures. Exact markup/tokens are selected against the current A1/Macro Command owner baseline before a builder changes shared UI. No runtime stylesheet injection, private palette or copied branding.

## 6. Single-writer and no-rebuild freeze

The existing watcher may discover source facts. It does not obtain research-ledger or model writer authority from this proposal. Current Macro law keeps nightly as sole forward-ledger advancer. Any future intraday path requires a separately accepted extension of that same owner and its publication contract before enabling it.

The desired eventual sequence is: accepted canonical source receipt -> affected existing PCE target -> one frozen input set -> deterministic/pre-registered candidate calculation -> existing forecast receipt -> existing product publication -> served browser/machine readback. There is no newly invented scheduler, queue, watcher, event system, correction ledger, forecast truth store or learning service.

A partial HTTP/table update must not trigger a complete-looking estimate. Freeze only eligible accepted inputs; display remaining gaps. If a run fails or its publication effect is unknown, use existing same-carrier reconciliation. Do not originate an independent fallback run with the same identity. A latency target is an engineering objective measured from actual acceptance/readback clocks, not a claim of market advantage.

## 7. Vertical execution sequence

### R0 — method/source review and integration freeze

Sol owns the thesis and accepts the eight-row source review. Terra is the preferred bounded primary-source research avenue; no Fable allocation is needed. This research can proceed while F1/A1 shared paths remain held. A placed researcher returns evidence and unresolveds, not code or a model.

In parallel, Sol obtains owner-compatible read contracts and exact changed-path/hunk compatibility for the first product slice. No conflicting source operation is reissued. R0 is not complete merely because this document exists.

### P1 — release-dependency and measurement-risk context

Observable result: an existing PCE card and its linked release detail explain which source events have arrived, which are pending, and whether method change/conflict limits interpretation, using real accepted facts and honest unavailable states.

Expected integration family after current-owner release: one narrow context leaf under `engine/release_*`, additive enrichment in `scripts/build_release_forecast.py`, the existing Release Radar rendering section and executed consumer tests. Policy Watch may initially be linked without modifying its owned source. Do not edit generated site output by hand.

Order: bind current source/consumer interfaces and design baseline; write discriminating RED tests; implement pure context leaf without IO or source mutation; wire existing producer and real renderer together; run numerical-invariance tests on old payload fields; canonical build; real-input machine/browser readback. One independently useful PR, not a schema-only PR.

Entrance conditions: exact target/source identity is available or explicit unavailable can be represented; source owner releases the additive seam; current UI owner accepts the small composition. No numerical forecast accuracy gate blocks this descriptive slice. A mapping conflict can be displayed honestly without waiting for the full bridge.

### P2 — core-PCE shadow bridge

A different, narrowly named candidate consumes the accepted map and frozen input snapshots. Existing PCE model points and primary selection stay unchanged. Before backtest, preregister target first-print basis, source stages/horizons, component methods, prior/residual treatment, weight and aggregation method, training/normalization cutoffs, sample minima, missingness behavior, uncertainty method or point-only status, benchmarks and kill criteria.

No parameter search follows outcome inspection under the same attempt. A proxy method remains a proxy. An unresolved composite is not filled with an LLM estimate. A numerical candidate may be point-only; a point is not automatically a distribution median and missing error scale is not zero variance.

Deliver one real-input prediction through the existing evidence, selected-model detail and machine consumer. Source completion is BUILT_NOT_PROVEN until real production and the exact target release resolve it. Headline PCE follows as its own useful slice.

### P3 — release-triggered assessment and first-print reconciliation

Extend the accepted single-writer mechanism, not the publication watcher by stealth. Test duplicate/reordered receipts, partial releases, source correction, restart, unknown publication result, outdated method and delayed table availability. Publish estimate revisions with component explanations and same-input lineage; after official PCE, grade the frozen target against the accepted first print and show revisions separately.

### P4 — empirical admission and learning

Matched candidates: current PCE baseline, persistence, CPI-only bridge and CPI+PPI bridge, with identical target, cutoff/stage and actual basis. Cleveland may be a timestamped external benchmark, never independent internal alpha or Street consensus. [S5] Removing the PPI inputs is mandatory to measure incremental PPI value.

Report exact sample sizes, bias, absolute/squared errors, availability, era/method splits and properly supported interval scores. Never pool first/latest actuals, pre/post-input stages or incompatible model/method epochs. Backfilled archives are retrospective evidence. Multiple updates for one monthly release are not independent monthly trials. Genuine forward receipts begin only after their actual freeze; no backdating today's events.

Track meaningful investigations opened, evidence drilldowns, stale/failed updates and whether users can answer what changed. Trading profitability and execution-cost validation are separate future work, not implied by improved forecast error.

## 8. Current owners and stop conditions

F1: `ric-f1-release-event-20260828-sol-001`, MAS-204, Slack `C0BSBM78V1N/1787975946.019219`, retained native task `01a04bde-8ce8-7903-ae91-6c38c63ac4cf`. Full thread was read. Its latest recovered edge retains an idle exact task with one pending read-only continuation; no duplicate input or replacement writer is authorized. Its prior seam release covered A1 display diagnostics only.

A1 #6868 has an incumbent Claude8 native task `local_fccca4ce-1d6f-4bda-b043-a0d96987af4a`; recovered comments do not establish source START/RESULT or effect-free local state. A2 #6879 and C0/D0 #6884/#6883 remain distinct dependencies. Do not take over those operations.

Preserve #6593's workstream file and #6870's records. Read current changed paths/hunks and native owners before editing the dashboard shared with #6685 and Macro Command #6930/#6937/#6982/#6983/#6985. #7017 owns current Policy Watch recovery source. A full open-PR metadata census and native worktree list were read, but they are not a blanket path-release receipt.

No P1/P2 implementation receiver is currently bound. Ordinary eligible work stays WAITING_CAPACITY / needs_placement until the existing placement path selects a concrete receiver. Neither this document nor a Slack mention is ACK, START or execution. No receiver-specific watcher exists before placement.

Stop a particular numerical leg on source/method ambiguity, not the entire descriptive product. Stop source edits on actual ownership collision or missing authority; continue disjoint source research. Stop promotion on insufficient forward evidence, not construction of honest context. Stop any plan that requires duplicate truth/control planes or invents precision.

## 9. Exact continuation

First, place one Terra researcher for the eight-row R0 source-method return, using one exact transport root and no implementation effects. Sol then accepts or retains each explicit disposition and releases an owner-compatible P1 producer/consumer packet. Independently, Sol coordinates the A1/F1/Macro Command seam without redelivering their retained work. No Chairman account allocation is required.

The next cold start reads Macro #7030, `DEC:RIC-PCE-RELEASE-BRIDGE`, the unique PCE handoff in this records branch and fresh current source/carrier returns. It must not interpret this records PR as completed R0, implemented P1 or production forecasting.

## Primary references

- [S1] BEA, NIPA Handbook Chapter 5, December 2024; Table 5.B screenshots inspected at PDF indexes 19, 20, 22 and 28: https://www.bea.gov/resources/methodologies/nipa-handbook/pdf/chapter-05.pdf
- [S2] BLS, Health Care Services in the Producer Price Index: https://www.bls.gov/ppi/factsheets/producer-price-index-healthcare-factsheet.htm
- [S3] BEA, August 17, 2026 annual-update announcement: https://www.bea.gov/news/blog/2026-08-17/annual-update-gdp-industry-and-state-stats-publicly-available-starting-sept-30
- [S4] BEA, CPI/PCE reconciliation methodology: https://www.bea.gov/help/faq/555
- [S5] Cleveland Fed inflation-nowcasting methodology and update policy: https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting

All external references were retrieved during the September 10, 2026 investigation. They establish the cited research findings only, not first-published numeric history, licensed consensus availability or current production liveness.
