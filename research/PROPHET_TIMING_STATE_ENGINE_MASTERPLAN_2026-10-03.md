# Prophet Timing State Engine — Research Audit and Implementation Masterplan

Status: architecture/research freeze; zero runtime authority  
Prepared: 2026-10-03  
Macro pin: 5f20adbd6be6b136b2efe41585bd4ef964b5bf2e  
Protected Mastermind pin: 20adcaf65c2dd1bb734ab06e215feb1a0eb65659  
Parent: #7925  
C1 salvage: Draft/HOLD #7929, head e1a6524ecfcdfee0f0cad251e0d502f2660c32a7; tested code head 2687deb19598d6a90d996d346fc2d6b52ce45863

## Executive ruling

Market Tide should become the **Prophet Timing State Engine (PTSE)**: a point-in-time, provenance-rich layer estimating orthogonal market-state dimensions, transition hazards, and action-specific consequences for NEW_ENTRY, CONTINUATION, PULLBACK_BUY, ADD, REENTRY and DERISK across explicit horizons.

PTSE is not another market-regime score, Risk Radar, Prophet ranker, candidate-population gate, calendar, options engine, data store, forecast ledger or portfolio allocator. The incumbent risk_radar → market_state → regime_vector authority remains intact. PTSE starts with rank/gate/size/trade authority false.

The deep-research thesis is good enough to freeze product architecture, but **not empirically complete enough to justify a timing model or production authority**.

## Research audit

What is correct:
- Reframe OPEX/calendar rules into state transitions and action value.
- Separate observed dimensions, state representation, transition estimates and action implications rather than one bull/bear score.
- Preserve #7929 as PIT/source-clock machinery; 89 focused tests are software evidence, not market efficacy.
- Preserve nulls: transferable GEX promotion failure, calendar-only OPEX, charm confounding, liquidity-shock reversal, breadth PIT/survivorship limits.
- Separate forecast quality from policy value including false warnings, missed upside and re-entry cost.
- Require chronology, purge/embargo, era analysis, calibration, missingness and source vintages.
- Compose beside Risk Radar, Prophet and Options Intelligence.

Fresh corrections:
1. The report missed the 2026-10-02 **Options Historical Revival**. OPTIONS-HISTORICAL-REVIVAL-V1 and DEC:OPTIONS-HISTORICAL-REVIVAL-RESEARCH-ONLY permit preregistered research-only replication/successors/interactions while retaining production restrictions.
2. The newest Theta EOD retrospective evaluated 60/60 registered cells under one BH family. Only three rejected the null: normalized GEX→future realized volatility in 2017–2019 at H5/H21; CW IV-spread level→SPY-excess in 2023–2025 at H21. No contrast survived all three eras. Vanna, Charm, vanna relief, IV-spread change, skew acceleration, term slope and DOI had no family-adjusted rejection. PIT remains unproven. This strengthens the case for era-conditioned path/volatility research and against universal options direction rules.
3. Prophet continued changing: nightly ledgers accrued through 2026-10-03, independent peer-continuity evidence landed, and an eight-sleeve strategy catalog landed. PTSE must be strategy/horizon/action conditioned.
4. Named latent states are UX hypotheses until the arena proves discrete states add value over continuous dimensions/hazards.
5. The prior research did not persist an implementation-ready owner/path masterplan or durable CEO handoff.

Audit verdict: **good enough to freeze thesis and architecture; not good enough to claim empirical completion or production readiness.**

## Fresh capability ledger

| Capability | State | Disposition |
|---|---|---|
| #7925 Market Tide | PARTIAL; product NOT_BUILT | Keep parent; this doc is implementation freeze |
| #7929 C1 | BUILT_NOT_PROVEN; zero market observations evaluated | Preserve benchmark/PIT conformance carrier; independent review + CI owed |
| C1 H5 event/downside question | benchmark only | Keep control, not ontology |
| Options OA-2R retrospective | completed bounded retrospective | B4 prior only; no PIT/production authority |
| Options measured NBBO | PARTIAL/BUILT_NOT_PROVEN | Consume only after owner acceptance |
| risk_radar→market_state→regime_vector | incumbent authority | Never duplicate |
| Prophet rank/candidates/grades | live/active | Consume cohorts; do not replace |
| Prophet B4 entry policy | bounded deterministic/shadow controls | Keep execution eligibility separate |
| WS:PROPHET-US-ENTRY-TIMING | active; held-out W2 pending | Coordinate evaluation philosophy |
| Prophet Conditional Fusion | research/shadow + narrow earned-authority exception | Reuse discipline; no second ranker |
| Breadth/live breadth | existing owners; PIT caveats | Consume qualified owner facts |
| Liquidity-shock reversal | KILLED exact construction | Never rebuild |
| Calendar-gated Risk Radar | FORBIDDEN | Event context only |
| Composite regime scorecard | FORBIDDEN/redundant | Dimensions/hazards/action evidence, no one score |
| Market Memory/qledger/grades | existing learning owners | Reuse; no PTSE ledger |
| Theme/GMI | existing owner | Consume leadership/concentration |
| Release/Event Truth | existing owner; historical qualification needed | Consume accepted clocks/revisions |
| Dedicated Market Tide page | NOT_BUILT | Defer until shadow value exists |

## Machine job and representation

At each decision timestamp/horizon PTSE asks: **given only evidence lawfully available now, how is the market environment changing the outcome distribution and regret for a specific contemplated action, and what transition is becoming more or less likely?**

Mandatory separation: PTSE=market timing context; Prophet/Opportunity Lifecycle=candidate quality/lifecycle; Grey Deer/Risk Radar=fragility; Options Intelligence=options observations; Prophet B4=strategy execution eligibility; Portfolio=exposure consequence; Market Memory/Eval=qledger/outcomes.

Arena candidates: continuous orthogonal dimensions; action-specific calibrated probabilities; discrete latent states; transition hazards; hybrids.

Dimensions: trend_health, participation, volatility_stress, liquidity_stress, catalyst_path, options_structure, cross_asset, leadership_concentration.

Actions: NEW_ENTRY, CONTINUATION, PULLBACK_BUY, ADD, REENTRY, DERISK.

First horizons: 1–3, 3–10 and 10–21 sessions. Intraday is later/separate because clocks, economics and owners differ.

Stable Advance / Fragile Advance / Deteriorating / Dislocation / Recovery / Ambiguous are display hypotheses only until validated.

## Machine contract v0.1

market_timing_state/v0.1-research contains decision/session/instrument/horizon/model/feature identity; observed dimensions with owner receipts; optional state distribution and state age; deterioration/dislocation/stabilization/recovery hazards; six action records; drivers; contradictions; missing inputs; quality/coverage/uncertainty; reassessment and invalidation conditions; source receipts; authority flags all false.

Missing is never neutral. Contradictions stay visible.

## Feature contract and empirical ladder

Every feature declares economic_time, known_at, source_version, revision lineage, calculation_version, adjustment basis/vintage where relevant, session/venue, membership-as-of, root class, positioning-side semantics, rights, coverage and exact refs.

B0 = price/trend/realized-vol baseline.  
B1 = PIT participation/breadth/dispersion/concentration.  
B2 = catalyst sequence with no surprise-before-known leakage.  
B3 = qualified market liquidity; exact LSR-P0 excluded.  
B4 = root-aware Options observations; newest priors are era-specific and PIT-unproven.  
B5 = incremental cross-asset/financial conditions.  
B6 = preregistered interactions/state using only survivors.

E0: freeze eligibility, outcomes, splits, multiplicity, falsifiers and trial budget before outcomes.  
E1: B0 + unchanged C1 on same eligible dates; C1 NON_EVALUABLE if sources remain unqualified.  
E2: add B1, primary transition lead/calibration/action value.  
E3: add B2; calendar proximity alone is a negative control, never a risk gate.  
E4: add B3; never resurrect LSR-P0.  
E5: add B4 conditionally (options×breadth/liquidity/vol state/post-event repair), using 2026-10-02 receipt as prior/negative-control evidence.  
E6: add B5 only if incremental.  
E7: model arena: regularized GLM/hazard first; changepoint, HMM/regime switching, dynamic/state-space, tree challenger. Deep temporal deferred until effective transition N warrants it.

Evaluation: chronological train/dev/calibration/final OOS; inclusive purge + separate embargo; dependence-aware inference; era/root stability; calibration; trial accounting; negative controls; adversarial mutations; coverage/missingness.

Winner criteria include log loss/Brier, calibration, transition lead, false-alarm duration, tail recall, era stability, action regret, missing behavior, complexity and interpretability—not AUROC alone.

Era reporting: 2017–2019, 2020–2022, 2023–qualified-current plus mechanism boundaries (COVID/ZIRP, tightening/inflation, 0DTE, concentration, product/exchange changes).

## Outcome contract

State targets: deterioration/dislocation/stabilization/recovery, persistence/time-to-transition, lead before obvious price break, false-alarm duration.

Path targets: signed returns, MFE/MAE, realized volatility/path instability, tail severity.

Action targets:
- NEW_ENTRY: follow-through, MFE/MAE, invalidation, liftoff, risk-adjusted return.
- CONTINUATION: trend survival, drawdown hazard, remaining MFE, recoverable vs structural break.
- PULLBACK_BUY/ADD: recovery probability/time, breakdown probability, adverse depth.
- DERISK: downside/tail/vol avoided vs upside forfeited, carry, false alarms, re-entry delay/penalty.
- REENTRY: false repair, recovery captured, whipsaw, delay cost.

Primary policy measure is net decision regret/utility versus CURRENT Prophet with the full cost vector printed.

## Prophet and cross-system integration

P0 context: join PTSE to candidate episodes by decision timestamp; no mutations.  
P1 paired shadow: identical cohorts/timestamps CURRENT vs CURRENT+PTSE. Measure timing delta, false-positive cost, missed upside, avoided MAE, re-entry delay, abstention.  
P2 calibrated shadow: display prospective calibrated probabilities/maturity; no mutation.  
P3 bounded authority: one adjudicated action×horizon×population may alter one bounded decision only after prospective policy-positive evidence. No universal market gate.

Any Prophet score/rank authority must use the existing Conditional Fusion promotion gate and narrow DNR exception.

Opportunity Lifecycle says where the opportunity is; PTSE says market permissiveness for the next action. Preserve disagreement.

Risk Radar/Grey Deer facts are consumed, not recomputed. Options Intelligence owns collection/Greeks/GEX/OI/flow/NBBO/root/side. Gross OI never becomes dealer inventory. Market Memory/Eval owns outcomes. Theme Intelligence owns theme state. Portfolio owns exposure. Terminal/Product reads one canonical artifact.

## Product

Do not build a dedicated page first. Initial consumers: Prophet candidate/detail Timing Context; post-admission/plan monitoring; Terminal market context; operator historical replay. Dedicated workspace only after shadow evidence demonstrates repeated workflow value.

UI shows dimensions/state, what changed, drivers, contradictions, uncertainty, missingness, catalysts, action implications, invalidation and calibration maturity. No giant traffic-light score.

## Promotion ladder

RESEARCH_ONLY → SHADOW_CONTEXT → CALIBRATED_SHADOW → BOUNDED_CONDITIONAL_AUTHORITY → later stronger authority only by separate ruling.

Software health, statistical acceptance, publication health and product proof are separate gates.

## Implementation waves

**W0 records/source freeze:** this masterplan, owner/path/DNR map, feature/action/outcome contracts, experiment registry. Records only.

**W1 #7929 salvage:** independent review exact head; current CI enrollment through incumbent CI owner; preserve scientific question. No merge until source/review/CI truth is explicit.

**W2 research contract:** pure schemas/validators/eligibility manifest. Tests for known-at, revisions, vintages, membership, root/side semantics, missingness, determinism.

**W3 B0 vertical:** accepted price owner → PIT panel → baseline transition/path/action labels → reproducible report.

**W4 B1/B2:** qualified breadth and event sequence separately, with ablations/negative controls. Block only unqualified family.

**W5 B3/B4/B5:** liquidity/options/cross-asset separately. B4 imports 2026-10-02 prior and prints era/PIT caveats. No production composite.

**W6 state/model arena:** transparent baseline vs challengers under frozen splits/trials; select representation on OOS calibration/transition/action evidence.

**W7 shadow artifact:** market_timing_state/v0.1-shadow, immutable decision receipts, authority false, existing outcome-grade joins.

**W8 Prophet shadow:** read-only candidate/post-admission context; same population/ranking; CURRENT vs SHADOW cohorts in existing grader.

**W9 product:** shared artifact in Prophet/Terminal with stale/partial/unknown states; desktop/mobile, light/dark, supported-locale browser proof.

**W10 prospective maturity:** accrue independent transitions/action episodes; evaluate calibration and policy regret; independent scientific/code review.

**W11 first bounded authority if earned:** one narrow action×horizon×population; explicit rollback to context-only; fail closed on missing/stale; no trade authority.

## #7929 salvage

Preserve unchanged: C1 target/question/model ladder; decision/outcome clocks; split-adjusted vs total-return separation; adjustment vintages; session/venue/rights refs; event-known-at and explicit negative evidence; monthly chronology; label maturity/purge; bootstrap/diagnostics; complete-history guard; preparation bridge.

Generalize later by importing accepted primitives, not mutating #7929 into the whole engine. Retain C1 as benchmark/control. Supersede only its role as product thesis. Keep Draft/HOLD until independent review, current CI and source qualification are resolved.

## Acceptance law and exact frontier

PTSE is not complete when a model trains or a page renders. First production mission requires qualified PIT inputs; reproducible ladder including nulls; representation beating B0 on declared OOS/calibration/action criteria; prospective shadow issuance and matured grading; no duplicate authority/store/calendar/ledger; real Prophet/Terminal consumer proof; and explicit adjudication before any decision mutation.

**Immediate frontier:** freeze market_timing_state/v0.1-research + feature eligibility + action/outcome contracts; independently review #7929; qualify the B0 price panel; execute B0 and unchanged C1 where eligible. In parallel, prepare B1/B2 adapters without outcome access. Do not wait for B4. Do not build UI before the canonical artifact.

## Astra CEO handoff target

Astra should take this programme end to end as principal orchestrator, delegate bounded source qualification/implementation/testing, preserve current owners and DNR law, continue across phase boundaries, and stop only at proven mission outcome or a real gate after all independent work is exhausted.
