# Research Hub R6 — models, cohorts and source readings

Status: DESIGN CANDIDATE / IMPLEMENTATION NOT STARTED  
Date: 14 November 2026  
Parent: [Research Explore migration record](../RESEARCH_EXPLORE_SHARED_SHELL_2026-11-14.md)  
Architecture: [Engine blueprint](ENGINE_AND_IMPLEMENTATION_BLUEPRINT_2026-11-14.md)  
Native identities and screenshots: [Design index](PAPER_DESIGN_INDEX_2026-11-14.md), [inventory](PAPER_INVENTORY_2026-11-14.json)

## 1. User outcome

A researcher can inspect what a named model actually displayed, understand why one company appeared in one section but not another, assess outcomes for a precisely defined historical population, and follow conflicting desk readings to their original evidence. Existing owner ranks and named model outputs remain visible. The shared shell adds no new fused score or independent evaluation authority.

Eight new R6 pages extend the existing Research R5 discovery, Following, directory and history views in Paper file 01M2VWK62FA5S4VVF6G7SBPE5J.

| Page | Root | View |
|---|---|---|
| p-V-1 | BGD-1 | Models and recorded cohort membership |
| p-W-1 | BNQ-1 | Cohort evaluation and graded coverage |
| p-X-1 | BV0-1 | Four desk readings plus separate Policy context |
| p-Y-1 | C1L-1 | Mobile desk readings and source inspection |
| p-Z-1 | C3Y-1 | Evaluation method at 1024px |
| p-10-1 | C6Y-1 | Availability, negative evidence and snapshot-change states |
| p-11-1 | C9J-1 | Advanced Build contract |
| p-12-1 | CMM-1 | Small-cohort evaluation limit on mobile |

All names, version EX-V6/EX-V7, sample counts, values and timestamps are synthetic design fixtures. The intraday snapshot and filtered-cohort evaluation require the owner extensions below; no existing API or runtime acceptance is implied.

## 2. Source owners and verified gaps

All inspected product sources bind to Macro e856ef0200a0c508c78ef9a6666116020e4835d1. Keep Terminal AppShell, authentication, entitlement, routing and incumbent source owners.

| Source | Exact blob | Role |
|---|---|---|
| [engine/intel_hub.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/intel_hub.py) | 87ce7bdf6daf41a3d5946c2e16e3ec6bdd8b48e0 | Dossiers, owner ranking, section membership, directions and recorded exclusion reasons |
| [scripts/build_intel_hub.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/scripts/build_intel_hub.py) | cf63882c00342281b1023d83cd2f4ff3c3b4f26a | Existing build, ledger snapshot and publication |
| [engine/hub_track_record.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/hub_track_record.py) | 5f328793944151267da644c5fa8b9eea073718bb | Legacy calendar-day evaluator |
| [engine/desk_grader.py](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/desk_grader.py) | 2f40df4bacf4805bd6bbb727f5e28b5e5911099b | Unified trading-day evaluator and level/velocity evidence |

The Hub consumes published News, Alternative Data, Radar, Standout, Policy and Special Situations owners. Its generated_utc is build time; it is not the freshness of every contributing source.

The build writes data/hub/signal_snapshots.jsonl through the existing snapshot owner. It strips track_rows before publishing hub.json. The desk grader adapter further drops cohorts and source and sets rank to None. Neither evaluator currently publishes the complete cohort/date/version-filtered daily statistics shown in R6. Add a bounded projection over the existing ledger and evaluator functions. Do not create another collector, ledger, grader, queue or publication lifecycle.

## 3. Recorded membership and named model outputs

A membership selection binds model ID, snapshot identity, engine version and cohort ID. The real stamped sections are command_top5, command_30, emerging_panel, discovery_shown and catalyst_shown. They represent displayed membership after selection; they overlap and their counts cannot be added as disjoint populations.

Preserve owner ordering. The fixture's ranks 1–5 belong to Command top 5; each also belongs to Command 30. The selected MU is Early but was not shown in Emerging because its recorded hero_reason is not_eligible. “Entry criteria not met” is a presentation of that recorded reason. Do not infer an exclusion from current state or treat missing reason as a negative gate.

Other source reasons preserve their priority: rolling_over precedes gate checks, then no_gate_verdict, flat_sell and not_eligible. A null reason may mean not excluded or a stage never eligible for the panel; it is not sufficient alone to reconstruct historical membership.

Expose Hub opportunity as a **score**. The inspected calculation caps opportunity at 100 before a downward-only governor; the fixture therefore shows 67.4 / 100. Its Method disclosure explains the named owner formula and version, not a probability of success. Composite conviction, edge remaining, lifecycle, entry gate and trajectory are available behind “All model outputs,” preserving their separate meanings.

The current snapshot ledger has day/ticker identity, not immutable intraday editions. The displayed 14:00 snapshot needs an additive artifact/version envelope from the existing owner. Never fabricate an intraday history from current rows or overwrite a prior snapshot under a reused identity. Old unstamped records display “Membership was not recorded,” not “Not a member.”

## 4. Evaluation population and units

A result identity must include model, cohort, observation window, model version, evaluator/version, horizon value and basis, benchmark, evidence cutoff, price cutoff and original artifact references. Filtering changes the complete population and all derived metrics together. Cancelling a method change leaves the applied result unchanged; applying it cancels or ignores stale requests and updates every bound panel atomically.

| Evaluator | Horizons | Basis |
|---|---|---|
| intel_hub.track_record.v1 | 5, 10, 21, 63 | Calendar-day offsets |
| desk_grader.v1 | 5, 10, 20, 30, 60, 90 | Trading-day bars |

The old template's trading-day wording for legacy results must not be carried forward. A legacy 21-calendar-day result is a different selection from a unified 20-trading-day result. Its provisional pooled correlation pools observations within that horizon; it does not pool across horizons.

R6's evaluation fixture selects Command 30, 1 September–31 October, EX-V6, unified 20 trading days and SPY. All counts and metrics must be computed from that same frozen selection. The existing engine_versions breakdown contains pooled summaries; combining it with overall daily/HAC metrics would misrepresent the selected version.

### Denominators and sample limits

The unified grader's coverage.eligible is a calendar-age prefilter and can include immature trading-day windows. Label it **Rows considered**. Show graded/ok, no_price, immature and no_bench separately. “Pending maturity” refers to the considered subset, not every younger observation in the entire date window.

The synthetic coverage reconciles: 864 graded + 48 price missing + 32 pending maturity + 16 benchmark missing = 960 considered; graded coverage is 90%. It is coverage, not accuracy.

Daily level IC +0.08 uses 31 valid evaluation dates and HAC t=1.2, producing Measuring. Velocity IC +0.03 has its own 29 valid daily samples and 620 rows with score history. velocity_n is not the final count of usable signed pairs; preserve any additional exclusions. Neither 864 rows nor 620 history rows is an independent-date sample.

_daily_ic requires at least ten usable signed score/return pairs per date, nonconstant values and enough valid dates. Consequently Command top 5 cannot by itself produce a daily IC under that method, however many historical rows accumulate. The mobile specimen has 120 graded rows but zero usable daily samples. Offer a broader cohort or explicitly provisional pooled inspection; never display zero correlation or silently relax the owner's threshold.

A rank correlation is not success probability, accuracy or campaign hit rate. Keep statistical explanation behind How to read this and Full statistics, with mean IC, n_days, horizon-aware HAC t/lag, paired counts, exclusions and pooled fallback identified precisely. Preserve the overlap correction. A large row count alone does not satisfy the owner's evidence threshold.

### Evidence status and historical price availability

Map existing measuring/proven/alarm to Measuring / Evidence threshold met / Negative evidence. Do not let the friendlier middle label imply trading or sizing authority; the owner remains context-only. The negative specimen assumes a valid significant negative daily result with adequate sample and retains evidence access.

No rows ready, missing prices, unavailable evaluation, zero usable daily samples and negative evidence are different states. Both evaluators currently catch errors and return accruing-like empty payloads with an error note. Add typed availability and reason before reliably distinguishing honest collection from computation failure.

Historical evaluation must prove the price cutoff. Reading complete price series and filtering dates by a calendar age alone does not establish that every selected end bar existed at the historical evaluation time. Bind prices/adjustments/benchmark to a reproducible cutoff and reject unsupported retrospective results.

## 5. Source readings and disagreement

News, Alt Data, Radar and Standout form the four voting desks. Policy is separate contextual evidence. Directional counts mean desk readings, not independent underlying confirmations; no new fused score is allowed.

The fixture contains News positive, Alt neutral, Radar negative and Standout positive. Alt's “Neutral score range” denotes a source score inside the neutral range with no AVOID action; it does not mean missing direction. The display preserves None/unavailable separately from zero/neutral. A missing source must not become a neutral vote or disappear from coverage.

Each reading carries original owner/artifact identity, source clock, first observation when established, horizon when specified, method/version and evidence link. Different clocks and horizons remain visible. An unspecified source horizon stays “Not specified.” Hub build time must not be copied into every row.

Selecting Radar opens its exact negative-divergence evidence while leaving all other readings visible. “Open Radar evidence” routes to the existing Radar owner; “Inspect source record” opens the exact source artifact. Back restores cohort, snapshot, selected company and reading plus scroll/focus.

Policy context retains proposal/legal-stage meaning and its own time. On mobile a compact Policy Watch context disclosure remains reachable below the selected desk; it is outside the four-reading tally. On expansion show the proposal/title, direction, original source time, legal stage and evidence action.

The code excludes Policy from _VOTING_DESKS, but a fallback base calculation includes usable Policy through len(present), and composite is a rank tie-breaker. This is a concrete static concern, not a reproduced production failure. Verify invariance where the intended policy requires it before asserting Policy can never influence ordering. Preserve existing owner ranks until that owner change is authorized and validated.

## 6. Interaction, responsiveness and recovery

Models & cohorts is reached from the accepted Research discovery composition. Members and Evaluation are sibling tasks. Preserve compatible model/cohort context when switching; explicitly expose when evaluation uses a historical window rather than a single snapshot.

The 1024px method view uses the canonical 72px rail and keeps the applied population beside the editable method. Trading-day horizon controls belong only to the selected unified evaluator. Switching to legacy exposes its own calendar-day choices; it cannot retain an unsupported value or mix a new method with old metrics.

At 390px desk readings become a compact selectable list and the chosen evidence follows below it. Policy context is a disclosure, not a dropped feature. Small-cohort evaluation has its own readable mobile state and an explicit recovery action.

Router state includes applied selection, pending method edit, source selection and return anchor. A newer model version offers Keep recorded snapshot or Open newer snapshot. It never silently changes the saved result. If an artifact expires or entitlement changes, display the scoped recovery state rather than relabel a newer response as the requested one.

Keyboard controls need real semantics, selected states, accessible names, focus return and touch hit targets. Method editing must support cancellation; source navigation must preserve Back/Forward and source context. Reduced motion and EN/ZH layout remain part of cross-product design/implementation acceptance.

## 7. Implementation sequence and proof

1. Extend the existing ledger projection with original membership, rank, source, hero_reason and version; add immutable artifact/cut identity without duplicating the snapshot owner.
2. Add typed evaluator/source availability and bound historical price evidence.
3. Compute cohort/window/version projections using existing evaluator functions and unchanged statistical semantics. Preserve all denominators and rejected rows.
4. Implement AppShell routes, compact membership/source panels, method selection, disclosures and stable navigation state.
5. Prove source-to-consumer paths for overlapping membership, missing stamps, Early-but-excluded, source neutral versus unavailable, Policy context, sparse Top 5 daily samples, a negative outcome, failed evaluation with prior result, evaluator change and version restoration.
6. Verify 390/1024/1440 layouts, full theme/locale behavior, keyboard/touch, authenticated source return and persistence. Production acceptance requires the actual producer → consumer → source → return path and deployed evidence under incumbent release gates.

Design-phase closure across the original Explore scope precedes product implementation. These compositions and source contracts make the next build reviewable; they do not claim the engines have been repaired, evaluated for trading, deployed or accepted in production.
