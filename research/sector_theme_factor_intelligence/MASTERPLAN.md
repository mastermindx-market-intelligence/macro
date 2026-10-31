# Sector & Theme Factor Intelligence — source-bound implementation masterplan

Recorded: 2026-10-30 (America/Cancun). Status: **proposed source-only extension**, not an Agent OS acceptance or released product.
Task tree: `research/sector_theme_factor_intelligence/MASTERPLAN.md`, owning repository `mastermindx-market-intelligence/macro`.
Protected Mastermind procedure: `bb85b429f2ffffd38408080ce4df7d6378c34100`; `mastermind.sol_skillpack.v1` / version `1.0.1` / bootstrap-major `1`.
Initial Macro source census: `6f60f9c75328996fbd43e4472d8890283de165fc`.
Existing organizational parent: `WS:LEADERSHIP-ROTATION-INTELLIGENCE` (not a new workstream); canonical theme-data dependency: `WS:GMI-THEME-GRAPH`.
Existing task trees: `research/ROTATION_COMMAND_MASTERPLAN_BY_FABLE.md`, `research/SECTOR_ROTATION_CONTINUATION.md`. This document specifies an additive extension; it does not replace their accepted nodes or the W1–W5 delivery.
Current source carrier: `sol/sector-theme-factor-intelligence-20261030`. Organizational handoff/artifacts linkage **not yet accepted or written**; the incumbent Agent OS writer must reconcile this source proposal.

## Chairman outcome and 10/10 completion ruler

One user journey from **market -> sector -> theme -> subtheme -> constituent -> evidence -> history -> conditional candidate**, with replay at intraday, daily, weekly, monthly and multi-year horizons. The user can determine (a) measured relative leaders and laggards, (b) breadth, trend quality, concentration, acceleration/deterioration, (c) plausible stage and historical analogs rather than fictional guaranteed "room to run", (d) correlated/inverse asset and credit stress, and (e) the exact known-at evidence and failure/null reasons. Individual leaders remain visible even when their sector or entry gate says HOLD.

10/10 acceptance requires all: current qualified canonical constituents including overlap and correction lineage; factual same-clock multi-timeframe measurements; factor-by-factor decompositions; intraday-to-daily state continuity; historical replay of what was *knowable*, distinct from reconstructed contexts; robust and independently reviewed predictive research before any predictive promotion; genuine permitted market feed and rights; well-designed EN/ZH responsive experience; exact-head CI and independent review; signed-in full producer -> canonical artifact -> API -> browser -> alert/return path proof where applicable. Green tests or a pretty page are not production proof.

## Incumbents, boundaries and anti-duplication

- `engine/theme_scoring.py` already blends trend (.26), breadth (.18), impulse (.07), macro (.18), MTF (.16), volhole (.05) and crowding (.10). Its forward-return efficacy is NOT established. Do not silently change these weights, enter/trim verbs, or invalidate its source-clock rules.
- `engine/leadership_rotation_context.py` already owns `relative_wealth`, `breadth` with coverage bounds, measurement vs transitions vs research estimates, cohort and evidence modes. Reuse these pure methods: relative wealth = `(1+R_g)/(1+R_b)-1`; coverage bounds = `[k/N,(k+N-n)/N]` (identification bounds, not confidence intervals).
- `engine/live_breadth.py` and existing VPS poller are market-wide DISPLAY-tier on the current lawful feed; no new poller/stream or feed entitlement. The 15-minute delayed basis must never render as instantaneous.
- `WS:GMI-THEME-GRAPH` is the canonical node, membership/PIT, rights, identity, ThemeState owner. Its W3B qualified owner receipts and W3C rights-gated cohorts are NOT fully accepted. Never fill unknown identities, populations or qualifications with current-roster assumptions.
- `engine/sector_cycles.py`, `engine/group_flow.py`, `engine/basket_mtf.py`, `engine/rotation_events.py`, existing Factor Atlas (Macro issue #8679; Terminal draft #928), and qualified credit/bonds/flow owners are inputs or consumers, not systems to recreate.
- Existing `WS:LEADERSHIP-ROTATION-INTELLIGENCE` recorded `MEASURED_PRODUCT_COMPLETE` for its bounded T01–T26 sector journey but `PREDICTIVE_CAPABILITY_QUALIFIED=NO` and original program not complete. Preserve its prereg V1/V2/V2.1 scientific results, W6 continuation, and do-not-redo holds. This extension may not relabel them as successful.
- No new entity master, ticker graph, data collector, event publisher, theme score authority, trading/portfolio authority, lifecycle, scheduler, experiment registry, alert outbox or separate learning store.

## Product semantics: five noninterchangeable analytical layers

**L0 data and eligibility**: point-in-time `security_id` and issuer; sector/theme/subtheme membership revision and known-at; optional dual memberships with overlap; eligible universe N vs sampled n; calendar, RTH/overnight basis, price adjustment basis, current-roster vs PIT; source, rights, observed_at, available_at, correction ID, first-seen, stale and null reasons. Different clocks never get joined as if simultaneous.

**L1 observed ticker and group state**: 1/5/15/60min; RTH session; 1/5/20/63/126/252 sessions; multi-year contextual history where source permits. Ticker-level return, logarithmic slope when robust, MA20/50/200 eligibility, 52-week range, normalized RSI/ROC, volatility/ATR, drawdown and distance from own historically conditioned run distribution. Group equal-weight, weighted only with complete lagged genuine weights, median, dispersion, tail share, positive-return breadth, % above MAs, positive RS/beta-residual breadth, new-high/low and up/down volume only where entitled. Report factor numerator/eligible n/expected N/bounds. No null-as-zero.

**L2 transitions and mechanism diagnostics**: paired-identity same-member 2x2 strength transitions; cohort-entry/exit separated from true state flips; cross-horizon alignment/conflict; acceleration = change in predeclared smoothed relative-return slope with exact windows and volatility normalization; concentration/HHI and leadership turnover; rising aggregate with shrinking breadth; falling cap-weighted group while median and equal-weight strengthen; intra-group leader vs laggard participation gap; sector/theme rank migration. Endpoint changes are not a record of every intrawindow crossing.

**L3 cross-asset and credit context**: observe pairwise relative strength vs SPY and parent, cross-sectional sector spread, defensives vs cyclicals, RSP/SPY, IWM/SPY, short/long duration, USD, gold, volatility and HY/IG spread where permitted and published. A putative inverse leg is an empirical rolling relationship with dated lookback, sample count, lower-tail/bear-market conditional estimate and instability flag. Never assume gold/TLT/XLU remain negatively correlated or treat simultaneous opposite moves as proven flows. Compare liquidity/funding, credit widening, risk-on leadership and risk-off oversold/turning states; differentiate market observation from a causal explanation. Daily published credit OAS is not an intraday tick. FRED ICE BofA OAS display began limiting available observations to 3 years in April 2026; historical sourcing/redistribution needs explicit rights and vintage review.

**L4 researched hypotheses**: prior-run analog conditional distributions (MFE/MAE, continuation frequency, survival/hazard, reversals) and pairwise factor interaction hypotheses for defined next 1/5/20/63-session outcomes. "Room to run" is an empirical *distribution with sample, limits and regime*, never a forecast from an RSI percentile alone. Until genuinely validated: research estimate only, not score/rank/promotion/position size.

**L5 consumer/action boundary**: descriptive frame may feed Macro/Terminal sector detail, rotation research, AI Briefs/Risk Radar as explicitly named observations. Existing signal/risk/entry/portfolio/outbox owners independently decide if and how an alert is permitted; no direct trading or position sizing. Natural-language explanation uses measured fields and cites as-of/basis and nulls; LLM may summarize but may not author numbers, identities or causality.

## One canonical read-only frame, version 1

```text
sector_theme_factor_frame/v1
  group: {canonical_group_id, kind, parent_ids, membership_revision, overlap_policy}
  horizon: {bar_interval, session_basis, start, end, close_kind}
  evidence: {source_id, source_revision, observed_at, available_at, correction_id,
             evidence_mode, rights_use, cohort_id, membership_mode, stale_reason}
  universe: {expected_n, eligible_n, sampled_n, missing_by_reason}
  observations: {constituent_states, group_returns, rs_vs_benchmark, rs_vs_parent,
                 breadth_metrics, breadth_identification_bounds, divergence, dispersion,
                 concentration, transitions, extension_context, cross_asset_context}
  interpretation: {current_strength, breadth_direction, acceleration, deterioration,
                   disagreement_flags, unmeasured_reasons}
  research: {hypothesis_id, pre_registration, eligible_horizons, evaluation_status}
  authority: {display_only=true, predictive_promoted=false,
              entry_gate_owner, alert_owner}
```

No invented one-dimensional score. If a weighted composite is later justified, its sign/weights, missing-leg treatment, benchmark and horizons require frozen experiment, versioned definition and separate owner approval; any missing high-impact factor must not silently renormalize to false confidence.

## Ordered task tree (source evidence, not Executive Jobs)

- **P0 [implementation_complete / source census only]** Reconcile Macro source `6f60f9c`, `WS:LEADERSHIP-ROTATION-INTELLIGENCE`, `WS:GMI-THEME-GRAPH`, Factor Atlas issue #8679, and incumbent breadth/theme scoring. Evidence: pinned source and current workstream reads. **DO_NOT_REDO** accepted W1–W5, graph D2C/D2D and previous score tests. Outstanding: current signed-in/production and source-writer custody proof, so acceptance not claimed.
- **P1 [implementation_complete / source candidate, not accepted]** Implemented `engine/sector_theme_factor_intelligence.py` and `engine/sector_theme_regime_fingerprint.py`: pure typed factor projection, 12-axis descriptive vector, true same-member breadth transitions, per-name divergence, coverage bounds and strict no-score/no-prediction/no-trade flags. Prior exact head `73db860f5ebd495ce3950254f9296d29dbd99949` ran `leadership-rotation-contract` with **134 passed in 4.60s** (actual CI pack4 job 124324232107); its aggregate CI was later cancelled by same-branch continuation, so this is targeted test proof, **not** current full-head green or review acceptance. Later P1a semantics distinguish nonpositive from negative and not-above from below; current-head retest is owed.
- **P2 [in_progress / source-only preview, owner qualification blocked]** Added `engine/sector_theme_owner_bridge.py` and hermetic `tests/test_sector_theme_owner_bridge.py` to consume already-owned U.S. basket membership, identity, source-use claims and same-clock ticker/benchmark evidence, explicitly distinguishing current roster and PIT. It projects a **RESEARCH_PREVIEW_ONLY** frame and refuses historical prediction/customer rights even for apparently valid inputs. P2b also binds `engine.group_flow.fingerprint_at` original acceleration/broadening/cohesion/persistence with a cohort/time/window check and **owner-reported unqualified** status, discarding its flow score. P2c added `engine/sector_theme_regime_explain.py` and corresponding tests for deterministic numeric EN/ZH explanations; neither mockup text nor owner-reported fields gain publication/forecast authority. **Required P2 completion**: actual original receipt authenticated by GMI/rights/price owner, real same-source inputs (not synthetic fixtures), exact source-use purpose and vintage, strict PIT/identity eligibility, user-path consumer; current CI and independent review owed. No raw feed, collection, public publication or data-retention introduced.
- **P3 [in_progress / source-only, not admitted]** Added pure `engine/sector_theme_regime_comparison.py` plus tests as an aligned-sector/theme research scanner: requires equal benchmark identity, price adjustment, RTH/overnight/session basis, observation start/end and decision cutoff, shows raw RS/participation/coverage and overlaps of security *and* issuer IDs; explicit no performance rank or independent overlap votes. Added `engine/sector_theme_regime_timeline.py` plus tests to compose a sequence of retained owner-preview observations, reusing incumbent `breadth_change` for true same-measured-member endpoint flips and distinguishing population/correction changes from measurement changes. Positive breadth delta bounds are `[lo_after-hi_before,hi_after-lo_before]` (logical identification, not confidence interval), so a direction is asserted only when guaranteed. Difference between trailing-window RS levels is explicitly *not acceleration*. **P3c now implemented as source-only preview:** `engine/sector_theme_multi_horizon_view.py` with 19 contract tests composes two or more independent P2 horizon frames through the same P1a fingerprint owner, requiring exact group/issuer identity, membership revision/known-at, endpoint/decision clock, benchmark/parent, price/session basis. It keeps differing horizon starts and returns separate; recalculates numeric facets and EN/ZH descriptions, never invents probabilities or publishability. A 750-case malformed-input stress check had zero uncaught exceptions; 201 P1–P3c synthetic tests passed on the M2 isolated exact source snapshot. This is neither native market-vintage validation nor customer acceptance. **Outstanding original P3 acceptance**: actual owner-authenticated/source-rights-qualified intraday quote and market clocks, no-lookahead as-issued retained snapshots, exchange-calendar/holiday and 24h/RTH regression, existing publisher/API/browser proof, exact-head CI and independent review; there is no new collector, event bus, store or forecast owner.
- **P4 [proposed; depends P1/P2]** Cross-asset/credit read-only evidence adapters and conditional relationship stability. Same-as-of only; ICE OAS history and redistribution licensing gate; preserve source vintage, publication latency and missingness. Acceptance: prove no intraday credit-spread front-running; regime-correlation inversion tests and date-mismatch refusal.
- **P5 [proposed; depends P1/P2/P3]** Paper-designed Macro Sector Central + Theme Detail and compatible Terminal panel: group matrix, ticker ladder, breadth trend heatmap, leader/laggard divergence, cross-asset stress, historical analogs, clear evidence badges, EN/ZH, keyboard, responsive, dark/light. Use canonical source frame, no duplicate backend. Acceptance: desktop/mobile and failure/null/rights-gated browser states; real signed-in input→view path.
- **P6 [proposed; depends P1/P2/P4]** Pre-registered, chronology-respecting scientific race. Explicit outcomes next 1/5/20/63 sessions; classify rather than promise future performance. Compare current theme scoring, momentum-only, breadth-only, SPY/parent baselines, and variants without inverse/credit legs. Purge/embargo overlapping labels; calendar-age and listing-survivorship checks; untouched chronological/era holdouts; clustered/block bootstrap; feature dependence, multiple tests, costs, turnover, missed-upside, false alarms, capture/latency. Prespecified promotion requires independent skeptical review and a prospective shadow audit, with negative findings retained.
- **P7 [proposed; depends P5/P6]** Read-only observation adoption in existing Risk Radar/AI Brief/Prophet/alerts and optional *validated* predictive research later, never direct score/rank/size/trade authority from this plan. Acceptance: one prospective observation→approved consumer→user return trace and explicit opt-in gates for real alerts.
- **P8 [proposed; depends P1–P7]** Exact-head CI, independent non-author Fabric review, rights/security/entitlement validation, normal release, seeded replay, live data lineage, multi-session production browser acceptance and operator rollback. Completion only when the full 10/10 ruler is observed and documented by the canonical owners.

## Immediate implementation contract and collision fences

The original P1-only implementation boundary is historical: this same draft now contains the P1-P3c pure research consumers described above. The current recovery scope is to qualify and repair those existing modules and their tests, preserve their single incumbent CI owner, and obtain independent source review. This is not acceptance of P1-P3c or permission to expand data effects. No changes to `engine/theme_graph/`, `engine/theme_scoring.py`, `engine/live_breadth.py`, incumbent rotation source, deployed data, `site/`, `templates/`, CI scheduling or publisher. P4-P8 retain their dependencies and original acceptance criteria. Real producer integration requires actual owner admission; a synthetic packet or this plan cannot grant it. Paper work requires the exact qualified target and carrier; a disconnected connector is not canvas proof.

External research anchors: Moskowitz & Grinblatt (1999), `https://doi.org/10.1111/0022-1082.00146`; Moskowitz/Ooi/Pedersen (2012), `https://doi.org/10.1016/j.jfineco.2011.11.003`; Gu/Kelly/Xiu (2020), `https://doi.org/10.1093/rfs/hhaa009`; FRED/ALFRED `BAMLH0A0HYM2` source/restrictions. These support hypotheses and feature selection, **not** validated performance for our particular model or data.

## Current recovery boundary

GitHub source proposal: eligible branch above; **not** Agent OS source-linked/accepted, merged, deployed, reviewed, or production proven. Before claiming an organizational milestone, an eligible Agent OS writer must add the appropriate task-tree artifact pointer and a valid dated handoff under existing `WS:LEADERSHIP-ROTATION-INTELLIGENCE`, preserving live writers, DO_NOT_REDO and external W6 obligations. No duplicate workstream or Job is created by this file.


## 2026-10-30 recovery qualification delta

The Chairman assigned the recovering session to lead this existing additive programme;
source carrier and task IDs remain unchanged. Cumulative recovery and child/effect
state stay in `agentos/handoffs/LEADERSHIP-ROTATION-FACTOR-BREADTH-2026-10-30.md`,
not in another task registry. The parent W1-W5 and separate W6 scientific scope are preserved.

- Exact recovered head `a469f858a8bda9dc3168abb151835ae9c5c7e60d` passed full hosted CI
  run `41141643577` and fences `41141643321`. The authoritative plan binds tested
  merge `4b0b5fe69ab01f5b62da0a6943989c2906a0bf64` to base
  `fd8d61c07261fd3a0f747aa8899f9638bc0a73cc`. Its owning
  `leadership-rotation-contract` job actually executed in pack 5, job
  `124358219887`: **268 passed in 9.92s**. This corrects the old unresolved-CI
  description only for that exact recovered head, not a later repair head.
- P2 recovery found a reproducible UTC normalization overflow in parseable extreme
  timestamps, plus malformed fingerprint member IDs reaching sorting. The small
  repair keeps invalid clocks/populations held. Invalid optional flow clocks hold
  that context without discarding otherwise valid base observations. No clock is
  clamped and no missing observation becomes zero or publishable.
- The 58 new parameterized cases discriminated the prior source: **57 failed,
  1 passed**, with 60 unrelated cases deselected. After repair, all seven focused
  suites passed: **259 passed in 0.27s** in an isolated M2 source copy whose 15
  original engine/test blobs matched the recovered head. This is focused source
  execution, not independent review, native full-repository or product acceptance.
  The repair must receive its own exact-head CI and independent review.
- Current GMI W3B/W3C owner records still require authentic membership/identity,
  purpose-specific rights and original producer proof. The direct Paper connector
  returned a transport 404; no Paper target, edit, screenshot or product proof exists.

No node is promoted to `accepted` by this recovery evidence.


## 2026-10-30 returned independent P3 audit and focused repair

The frozen `a469f858…` P3-only Fabric audit
`stfi-p3-consumer-audit-a469-20261030-r1` returned `CHANGES_REQUIRED`,
not a whole-PR approval. Its source counterexamples cover unhashable frame
population, duplicated physical windows under different horizon labels,
caller-forged explanation tags, cross-parent timeline comparison, unverified
issuer/quote counts and fingerprint/frame identity drift. The repaired P3
comparison, timeline and multihorizon consumers add fail-closed validations;
P3c also catches UTC normalization overflow in parseable extreme timestamps.

Twelve new targeted regressions failed on the unrepaired P3 source; after repair
all seven isolated suites passed **271** cases. This is evidence for the pure
source boundary only. CI/fences on the new immutable repair head, separate
independent review covering repairs/P1/P2, authentic GMI identity/rights/vintage,
Paper design and a signed-in producer-to-user path remain required. P4-P8 and
W6 scientific qualification retain their original HOLD/dependency contracts.


## 2026-10-30 additional P3 self-consistency qualifications

A second isolated source-only mutation audit produced 1,170 changed
P3-consumer input cases with 0 uncaught errors or authority promotion.
It exposed a distinct evidence-integrity hole: callers could alter
fingerprint RS/breadth numerics after P2's factor frame existed, causing
a supposedly same-source timeline or cross-theme scanner to accept
contradictory values. Also some bounded `measured_return_n` counts were
not reconciled with actual observed members; theme parent IDs could be
absent; and chronology group kinds were not checked. The follow-on
repair re-projects exactly one horizon through incumbent P1
`compose_regime_fingerprint` to bind numeric/evidence content to the
retained frame; recomputes actual measured-return count from typed
constituent return observations; and requires a parent on non-sector
themes and a supported group kind. It deliberately changes two prior
tests from permissive corrupted-input degradation to the stronger
whole-composition HELD contract. Five additional counterexamples
were red on pre-repair 46792c6; all **278** source-focused cases pass
after correction.

The only accepted mutation output deltas in the follow-on audit were
arbitrary, syntactically nonempty `comparison_basis.parent_id`
strings. P1 frame does not carry an independently authenticated
parent-ID receipt; P2's owner-reported identity cannot elevate this
label from **unverified**. P3 still allows labeled research previews
only and cannot claim a genuine source-bound parent benchmark,
publication, score, alert or trade. The authenticated producer path
must prove this ID (and quote/basis/source rights), not infer it.
Frozen-head CI/review from 46792c6 is not exact-head proof of any
new follow-on commit. This strengthens P3 only, does not start P4-P8.
