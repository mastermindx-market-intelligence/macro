# Prophet Timing State Engine — end-to-end implementation masterplan

Prepared 2026-10-03 after ordinary-session audit. Parent: [Macro #7925](https://github.com/mastermindx-market-intelligence/macro/issues/7925). Existing architecture carrier: [#8325](https://github.com/mastermindx-market-intelligence/macro/pull/8325). Frozen C1 research carrier: [#7929](https://github.com/mastermindx-market-intelligence/macro/pull/7929).

Status: **proposed execution amendment for incorporation and owner acceptance; no runtime or predictive authority granted**. Read the [audit](AUDIT_AND_RECENSUS.md), [contracts/evaluation specification](CONTRACTS_AND_EVALUATION.md), [evidence ledger](EVIDENCE_LEDGER.md) and [Astra handoff](ASTRA_CEO_HANDOFF.md). Source references G/L/W in this plan resolve in the ledger.

## 1. Mission, product value and honest end states

Turn the orphaned Market Tide research into a useful, defensible action-context capability within the existing Mastermind Daily Desk. The user should be able to understand the market environment, see what materially changed, inspect the evidence and contradictions, and understand the implications for the **particular candidate, strategy, action and horizon** under consideration. Existing candidate research, watchlist/portfolio saves, plans, alerts and next-day learning retain their canonical identities and owners.

The primary machine job is a derived, point-in-time **action-conditioned evidence adapter**, not a second market-regime service. It may eventually carry validated transition/outcome estimates, but it begins by consuming incumbent facts and preserving provenance. The correct winning model could be a simple price/volatility baseline, a direct conditional model, an existing-state-conditioned model, or no sufficiently useful predictive model at all. A six-state HMM, a universal score and an OPEX timer are not preselected destinations.

The full product contract covers `NEW_ENTRY`, `CONTINUATION`, `PULLBACK_BUY`, `ADD`, `REENTRY` and `DERISK`. Initial evidence admission is deliberately narrower: US daily H5 market benchmark plus read-only NEW_ENTRY context for one existing eligible Prophet strategy. Implement the full action/status contract from the start, but activate each action estimate only when its own cohort, outcome and economic assumptions are valid. Forecast horizon, strategy holding horizon and execution eligibility are independent.

### 1.1 Separate completion axes

| Axis | Evidence required | What it does not establish |
|---|---|---|
| Research specification | Accepted scope, owner map, exact registered study/data/outcome definitions | A fitted model or qualified inputs |
| Source/observation capability | Real owner evidence → immutable observation → actual consumer, with unavailable/late cases | Predictive value |
| Research execution | Reproducible actual-data studies and complete trial/coverage/null accounting | Causal policy benefit or prospective performance |
| Forecast qualification | Proper source eligibility, protected evaluation, calibration and prospective evidence at the target population/horizon | Permission to alter decisions |
| Product acceptance | Useful, accessible real workflow over the same canonical artifact, with provenance and honest status | Forecast or trading authority merely because the page looks finished |
| Decision authority | Explicit bounded owner ruling plus policy-positive prospective evidence and rollback | Universal ranking, allocation, leverage or trading control |

A bounded context release may be accepted while forecasts remain unqualified. Do not claim the full parent mission complete merely because the context UI ships. A scientifically negative result is valid and must not provoke endless threshold mining. If evidence falsifies the proposed predictive product, return an explicit scientific stop/re-scope recommendation with all useful completed capabilities and residual obligations. The current mission does not silently shrink itself to “we wrote a report.”

## 2. Non-negotiable boundaries

Keep #7925 as the existing mission and reconcile #8325 before adding competing architecture records. This review package does not transfer #8325 or #7929 writer custody. Preserve all existing unknown-effect and action-specific refusal boundaries. A read-only runtime failure does not mean a worker is gone or a worktree is free.

Do not create another source registry, data collector, calendar, event store, candidate database, lifecycle, forecast/outcome ledger, queue, scheduler, retry service, generic research database or market-state authority. Use existing owner APIs and append-only/correction semantics. Preserve existing flow `market_tide` fields and the separate MAS-260 intraday Outlook namespace. Do not duplicate Terminal's Greek/scenario computations [G14,G20,L03].

Current DNR amendments are scoped, not blanket. The October 2 Options revival permits its named research constructions and successors while preserving negative evidence and production restrictions [G07–G09]. A new global fused regime/action score is not legalized by calling it context or a shadow. Where an experiment needs the existing Prophet Conditional Fusion or Options research exception, conduct it through that exact admitted arena and current contract. No renaming to evade Signal Foundry or other controls.

Do not turn missing optional timing inputs into a universal Prophet veto. No unqualified score/rank, admission, entry gate, plan mutation, alert escalation, sizing, portfolio, execution or trade effect. No LLM-originated numerical market signal, probability or confidence. LLM explanation may describe supplied evidence without originating facts or overriding policy.

Keep data rights and budgets explicit. Do not upload raw entitled quote/chain corpora or credentials. Do not purchase subscriptions, capacity or credits as an implied dependency repair. Do not invoke Codex/work without separate authorization. Use existing admitted workers and current resource controls; a failed connector is not permission to bypass a refusal. Deploy through the existing non-Vercel release path only after its normal approvals.

## 3. Ownership and exact integration map

The following is a **starting owner map**, not a claim that every live field binding was verified by this audit. W0 must replace unresolved field/call-path entries with exact current receipts before editing their consumers.

| Concern | Incumbent owner / known source anchor | PTSE relationship |
|---|---|---|
| Parent mission and durable recovery | #7925; original operation `market-tide-research-20260924-sol-001`; #8325 architecture | Reconcile and extend existing mission records; no new parent |
| C1 scientific benchmark | #7929; `research/options_estate/market_tide_c1*.py`, event binding and measurement modules | Preserve experiment identity; use accepted pure primitives or a separately versioned runner |
| Source prices/adjustments/rights | Existing Data OS/source owners; concrete dated store inventory in G21 | Obtain source-qualified panel and per-field clocks; do not substitute MAS-94 Todo as an estate-wide readiness verdict |
| Breadth/membership/leadership | Existing breadth/PIT, GMI/Theme and related price owners | Consume versioned facts and membership denominators; do not rebuild breadth/themes |
| Macro release/calendar | MAS-204/F1 and existing release/calendar APIs; `engine/release_actuals.py` referenced by owner | Request exact known-at/revision/negative-coverage contract; no duplicate event calendar |
| Risk/fragility | Risk Radar, Grey Deer/Risk Envelope; `engine/market_state.py` and `engine/regime_vector.py` inspected | Trace actual field/authority graph; consume rather than reclassify incumbents |
| Options data/science | WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY; existing Options Hub/Theta/live-flow/stamping/research owners | Use admitted observations, current result receipts and existing trial/evaluation paths |
| Intraday exposure forecasts | MAS-260 | Preserve independent horizon/model/custody; no reimplementation inside PTSE |
| Candidate identity/strategy/lifecycle | Prophet V4/common candidate-episode owners and strategy architecture G17 | Attach typed context at exact decision/episode/strategy; no population merge or new lifecycle |
| Execution eligibility | `engine/prophet_entry_policy.py` and actual B4 Availability consumers; WS-PROPHET-US-ENTRY-TIMING owns `engine/prophet_*.py` | Do not duplicate session/risk/NBBO/gap gates or silently widen them |
| Plans and Portfolio | Existing candidate plan, position, risk budget and exposure owners | Reference existing plan/position IDs; no auto-exit or allocation ownership |
| Outcomes and prospective evidence | Existing candidate graders, Eval/qledger and Market Memory owners | Issue decision evidence first, attach matured outcomes later; no PTSE ledger |
| UI/transport | Existing Macro publication path; existing Prophet/Terminal consumer and cache owners | One canonical artifact, shared identity, current transport and schema validation |

For every integration edge, acceptance requires: producer symbol/file and revision; emitted field/schema; source/availability semantics; consumer symbol/file and revision; behavior affected; current authority; absence/failure behavior; test path; runtime/publication receipt. “Risk Radar owns risk” alone is not a sufficient implementation contract.

## 4. Dependency graph and parallel work

The plan is gate-based, not a calendar promise. Observation capture and useful read-only presentation should not wait for every historical study or a model winner.

```text
W0 owner/architecture reconciliation
 ├─ W1 C1 review and delivery repair ──────────────── C1 run inside W5 when its sources qualify
 ├─ W2 machine/identity/outcome contracts
 │    └─ W3 independent source admission + natural observation capture
 │         ├─ W4 price-only B0 actual-data benchmark
 │         │    └─ W5 admitted family comparisons ── W6 model/interaction/representation arena
 │         └─ W7 observation artifact + existing consumer seam
 │              └─ W8 candidate/action joins ── W9 real workflow/browser acceptance
 └──────────────────────────── W10 prospective accrual, maturity and scientific review
                                  └─ W11 bounded decision authority, only if earned
```

W3 has independent price, participation, event, options, liquidity and cross-asset readiness. C1/event absence blocks C1/B2, not price-only B0. W7 observation-only work can proceed before W5/W6 finish. W10 observation accrual begins as soon as its accepted source/contract path exists; qualified forecast accrual starts separately when the model can lawfully issue. Neither is claimed running until a real runtime receipt exists.

Use bounded parallel work where current custody and tool access permit: source manifest/availability, C1 independent review, contract/consumer implementation, and scientific-method review are natural separate lanes. One integration owner coordinates shared files. Assign workers through existing Executive/Agent OS mechanisms only; do not invent a parallel task lifecycle. Group coherent tested changes to avoid unnecessary CI churn.

## 5. Universal work-package acceptance contract

Each wave records its exact base/head, owner concurrence, changed files, input/output schema, source and outcome grade, tests, applicable normal CI, independent review, actual consumer proof where relevant, rollback and residual gate. A research wave additionally records protocol/input hashes, all trial counts, missingness, actual executable command, dependency/runtime versions and reproducibility evidence.

The paths proposed below are candidates, not an assertion that those modules already exist or are unowned. Prefer extending a current accepted primitive when W0 finds one. No path edit begins before a fresh collision/custody check. Avoid modifying the C1 scientific target while extracting common code; prove old behavior with compatibility tests.

## W0 — Reconcile the existing program and freeze the correct interfaces

**Capability:** a single coherent execution map, not another masterplan beside #8325. Read the complete package, current protected Mastermind procedure, #7925/#7929/#8325, the October 2 decision/charter, current owning workstreams and current source/PR occupancy. Incorporate the review's accepted amendments into #8325 or its current successor under that owner's control. Preserve authorship and explicit supersession; do not simply declare this unreviewed package the new authority.

**Owners/paths:** existing #8325 architecture document `research/PROPHET_TIMING_STATE_ENGINE_MASTERPLAN_2026-10-03.md`; existing Agent OS handoff/decision records as appropriate; entry, Options, event, Risk and source owners in §3. No new organizational root.

**Inputs/dependencies:** current exact source pins and actual incumbent responses/records. The review observed Mastermind `20adcaf...`, Macro `9d3fb88...`, Terminal `41b8af2...`; refresh rather than deploy these by assumption.

**Tests/proof:** reconcile every machine-contract field with a real producer and consumer; find the actual served Prophet context/episode/Availability path, complete Grey Deer/Risk Envelope mapping, distinguish the two Terminal `marketStructure.ts` files and the existing flow Market Tide. Run existing schema/Agent OS validation for any changed records. Resolve #8325's mergeability separately through its owner; do not force-push it.

**Exit:** accepted ownership/field map and a finite issue/gate list. Unresolved live custody blocks the affected write, not independent read-only audit or contract design. Rollback is records-only narrow supersession; no source or runtime authority changes.

## W1 — Independently qualify and salvage C1 without changing its question

**Capability:** trustworthy benchmark infrastructure, with software acceptance separated from source/scientific acceptance.

**Owners/paths:** same #7929 carrier and source writer; `research/options_estate/market_tide_c1.py`, `_prepare.py`, diagnostics, event binding, measurement checks, existing tests/proofs. Shared CI enrollment through its incumbent owner, not an unrelated CI-wide repair.

**Work:** review the exact current candidate, distinguish the 89 historical test receipt from a current run, inspect the visible failed ci-gate and C1 enrollment, and arrange non-author review under current policy. Audit feature/outcome clocks, complete training history, invalid calendar/negative-event evidence, bootstrap and scoring. Reproduce a defect before asserting one. Preserve old artifacts and version any scientific change explicitly.

**Tests:** legal/illegal source fixtures, history-boundary and label-maturity cases, round-trip provenance, finite values, calendar completeness at the qualified owner boundary, deterministic fits and row ordering. A changed/refactored runner must reproduce frozen legal C1 outputs and exclusions. The earlier refused multi-year stress action and parked C2 effect are not replayed by this work package.

**Proof/exit:** exact tested head, non-author findings, applicable current CI, ownership-safe source acceptance or a precise HOLD. Green software tests do not imply a market result. Real C1 execution still needs admitted event/price evidence. No production/browser proof is claimed for this research-only wave. Rollback returns to the preserved benchmark revision; it never deletes failed results.

## W2 — Implement the typed observation and action contract

**Capability:** a closed, versioned data shape that can safely represent known facts, estimates, abstentions and action applicability without granting authority.

**Owners/paths:** current schema/identity utilities and existing research family. Proposed bounded additions: `research/options_estate/ptse_contract.py` and matching existing-style tests/fixtures, or a narrower accepted seam found in W0. Production `engine/prophet_*.py` changes require Entry Timing/common Prophet owner pairing.

**Work:** implement the contract in the companion specification: source/observation/assessment identities, decision/issuance/session/horizon clocks, independent holding-law references, optional estimates, six action records, typed missingness and correction lineage. Observation issuance must not require a future label. Preserve the existing outcome owner instead of adding an embedded mutable “results” record.

**Tests:** canonical identity/idempotency, duplicate keys, invalid units, unknown schema, NaN/Infinity, future-known input, source precision, unsupported horizon, null versus zero, side/coverage semantics, empty estimates and forbidden authority bits. Consumer mode must reject an attempt to self-upgrade context authority.

**Exit/proof:** reviewed contract and hermetic tests at exact head; synthetic fixtures are labeled synthetic. No market, live producer or calibration claim. Rollback is disabling the new optional contract reader; incumbent behavior remains byte-for-byte/equivalently unchanged.

## W3 — Qualify independent source lanes and begin lawful observation capture

**Capability:** measured data feasibility and a reproducible eligible panel/observation stream, not another collector or global blocker.

**Owners/paths:** existing price/Data OS, breadth/PIT, release truth, Options, liquidity/cross-asset, Theme and Market Memory/Eval owners. Start from concrete existing store/adapter references in G09,G13,G21,L01,L02, not guessed paths or new vendor downloads. Reuse existing source manifests/correction receipts.

**Work:** perform bounded metadata/rights/availability reads before outcome access: min/max sessions, missing observations, per-era/root coverage, source version, adjustment basis/vintage, first-known precision, PIT membership and delisting coverage. Separate inherited July inventory counts from new measurements. Request/consume the existing MAS-204 and price-owner returns. Do not repair MAS-94's entire source vertical merely because C1 needs history.

**Tests:** source artifact/readback identity, legal late-arrival classification, genuine negative-event evidence, multiple same-day revisions, price/activity session mismatch, OI publication clock, root/settlement scope, current-versus-PIT membership, missing denominator and stale source. Unknown provenance remains unknown even when values look plausible.

**Proof/exit:** one eligibility disposition per family; B0 receives its own price-qualified panel or an explicit blocker. Where permission allows retrospective PIT-unproven exploration, label it separately. Begin immutable natural-session observation capture through an accepted existing owner as soon as eligible; record actual clock and persistence receipts. No natural-time claim from replay. Rollback disables only the new registration/consumer; existing source history and incidents remain intact.

## W4 — Execute the real event-independent B0 vertical

**Capability:** the first actual baseline measurement on lawfully eligible data, with reproducible counts, uncertainty and failure accounting.

**Owners/paths:** existing research/evaluation owners; proposed `research/options_estate/ptse_baseline.py` or an accepted compatible runner. Import accepted measurement primitives, not a new price/calendar/outcome engine. Store reports under the existing research artifact convention.

**Dependencies:** W2 and the price lane of W3. Event truth, full Options history and completion of W5 are not dependencies. Any use of #7929 primitives must respect their current acceptance/custody; pure new runner work does not authorize a denied action on that carrier.

**Work:** register PTSE-B0-H5-v1 before protected outcomes, reconcile prior data exposure, run the source-qualified price-only mean/P-vector benchmark, and disclose whether the run is PIT-qualified or retrospective. Emit full eligible and matched-cohort counts, matured outcomes, missingness and model/target identities. Compare to C1 P only on the exact lawful overlap when available.

**Tests/proof:** synthetic null/injected-effect discrimination, same-date pairs, calendar gaps, train-only transforms, inclusive boundary purge, label availability and no event-required dependency. Then an actual command/receipt on real admitted observations. No index-prediction result becomes a candidate-action or portfolio result.

**Exit:** reproducible measured baseline, including negative/inconclusive findings, or precise source-based NON_EVALUABLE with all source-independent software complete. Do not call NON_EVALUABLE empirical validation. Rollback is model/assessment withdrawal; source observations remain for attribution.

## W5 — Run C1 and incremental feature comparisons on matched populations

**Capability:** a family-level incremental evidence ledger, not one enormous composite model.

**Owners/paths:** C1 through #7929 when accepted and source-ready; Options through its existing admitted gauntlet/charter; breadth/event/liquidity/cross-asset through their current research/data owners. Extend existing result artifacts and trial accounting, not a separate experiment-control service.

**Dependencies:** W4 baseline plus the specific admitted family. The unchanged C1 requires its own qualified historical event/price panel and W1 acceptance. Each family can finish independently; do not wait for the least mature source.

**Work:** execute the finite comparisons and matched B0/control arms in the contract. Preserve all omitted/missing dates and report selection cost. Consume the already completed October 2 Options study rather than treating it as missing or rerunning without a new question [G10–G11]. Compare old/new Options findings by exact target and construction; the old volatility vanna-relief finding is not directly retested by the new SPY-excess-return cell. Retain signed-versus-magnitude and opposite-sign controls for any legitimate successor.

**Tests/proof:** source-family ablations, null/negative controls, era/root-class slices, correlated-instrument handling, complete trial accounting, true out-of-time evaluation and reproducibility. Numeric result readback must bind protocol, input and result hashes. Independent review checks both arithmetic and source eligibility.

**Exit:** every registered slot has an explicit measured or non-evaluable disposition. A nonrejection is not zero effect; a research-pass is not calibrated production authority. Rollback removes a rejected feature from proposed estimates while preserving its observations and result history.

## W6 — Compare representations, interactions and calibration

**Capability:** an evidence-based choice of representation, including the option not to add a latent state model.

**Owners/paths:** existing research arena and applicable Conditional Fusion/Options exceptions; no new global regime classifier. Proposed bounded research modules for direct GLM, event hazard or one latent/changepoint challenger only after W0 resolves overlap and scope. Existing Risk/market-state observations are controls and inputs, not replaced owners.

**Dependencies:** registered target and W4; W5 qualified inputs where applicable. The one mechanism-registered interaction may include marginally null components, with its nulls preserved and trial charged. Do not require every feature to “survive” an unconditional screening stage, and do not allow unrestricted interaction fishing.

**Work:** compare direct continuous outcome predictions, explicit-event hazards, incumbent dimensions and a limited challenger. Fit state maps and transformations inside folds, use filtered rather than smoothed history, separate calibration fit/evaluation, and test independent observable transition outcomes. Reject models whose usefulness is entirely in-sample narration or post-break detection mislabeled early warning.

**Tests/proof:** look-ahead mutation, state-label stability, censoring/competing-event logic, signed lead times, false-warning episodes, missingness sensitivity and exact fit/forecast reproducibility. Apply finite multiplicity/support/materiality gates from the preregistration. Explain why complexity is justified relative to the simple alternative.

**Exit:** selected research candidate with its limitations, or no qualifying challenger. No forced six-state vocabulary. Public probabilities remain closed until their distinct prospective/consumer gates. Rollback to observed context or the retained simpler forecast, with model version and withdrawn qualification explicit.

## W7 — Deliver the canonical read-only artifact and consumer seam

**Capability:** a real observation-led vertical before statistical completion: owner evidence → canonical observation/assessment → existing API → a read-only consumer.

**Owners/paths:** accepted Macro publication and current Prophet/Terminal transport/cache owners located in W0. Proposed production composer `engine/prophet_timing_context.py` only if the shared Prophet owner admits that path; otherwise use the narrower existing context composer. No new polling service, source store, or second “latest state” directory.

**Dependencies:** W2 and at least one accepted W3 observation lane. W5/W6 are **not prerequisites** for observed context. Fitted estimates are optional and clearly unqualified/absent until their gates are met.

**Work:** wire exact source identities and available dimensions, preserve contradictions/missingness, publish once through the incumbent owner, and validate at the real consumer. Distinguish observation changes from revisions and from model changes. No source timestamps generated by the UI. No reuse of existing flow Market Tide or Outlook keys.

**Tests/proof:** schema/version enforcement, identity readback, atomic publication/generation coherence, stale source, unavailable route, partial dimensions, correction lineage, cache invalidation and late-response races. Demonstrate context on/off produces unchanged incumbent decisions. Record a real source→artifact→consumer receipt rather than only a fixture.

**Exit:** BUILT_NOT_PROVEN until the actual accepted publication/consumer path is demonstrated; then observed-context capability can be accepted independently. Rollback disables the new optional projection and preserves baseline Prophet/Terminal operation; old evidence is retained.

## W8 — Integrate candidate lifecycle and all six action contexts

**Capability:** timing evidence is useful before admission and after an existing opportunity changes, without becoming the candidate's lifecycle or execution gate.

**Owners/paths:** common Prophet candidate/episode/strategy, Availability, plan and grading owners; `engine/prophet_entry_policy.py` remains its own deterministic policy source. Existing plan/Portfolio IDs identify holdings/adds/de-risk/re-entry episodes. No new position manager or candidate ledger.

**Dependencies:** W7, exact owner joins from W0 and valid action-specific populations. Estimated action consequences depend on appropriate research, not merely W6 having a market forecast. Unavailable actions are typed and explained rather than fabricated.

**Work:** start with identical CURRENT and SHADOW_TIMING candidate populations/timestamps. Add pre-admission context without changing the board's population or sorting. Add post-admission reassessment when an existing source revision/event/state fact genuinely changes; preserve the original decision record. Extend through continuation, pullback/add and a **paired complete de-risk/re-entry policy** with pre-decision action applicability. Strategy/horizon/market differences remain explicit.

**Tests/proof:** exact episode joins, strategies sharing a ticker, already-held versus fresh entry, stale plan/position, duplicate events, revision after a decision, immature outcomes, rejected/unfilled candidates and complete baseline-cohort accounting. Toggle/context mutation must not change ranks, admissions, eligibility, plans, alerts or exposure. Use actual existing saved watchlist/portfolio identities for read-only display; do not create another save destination.

**Exit:** six action/status contracts implemented, supported action workflows proven, and each unsupported evidence lane explicitly tracked. A completed NEW_ENTRY slice does not close the other action obligations. Rollback removes only the new context/assessment join; original candidate records and plans are unchanged.

## W9 — Accept the real user workflow and degraded cases

**Capability:** a clear, trustworthy Daily Desk experience, not another crowded dashboard or giant market dial.

**Owners/paths:** existing Prophet board/detail/plan monitoring, Terminal market-context views and associated localization/design system. Exact files from W0 consumer inventory. Do not create a standalone Market Tide page unless actual workflow evidence later justifies it. Do not redesign unrelated navigation or replace accepted Options interfaces.

**Experience:** show a compact current-context summary and material change, then the action relevant to this candidate/holding. An evidence drawer exposes independent dimensions, source times, drivers, contradictions, expected catalysts, missingness and reassessment conditions. Separate descriptive context from research estimates and calibrated probabilities. Show maturity and uncertainty at the actual horizon. Historical replay uses an eligible past observation/model vintage, not today's recomputation or cherry-picked analogues. Preserve the original candidate research, plan and canonical save journey.

**Tests/proof:** actual production-equivalent browser path at desktop/tablet/mobile, supported EN/ZH/locales and light/dark modes, keyboard navigation, focus restoration, contrast, non-color status cues, no horizontal overflow, no stale-root substitution, unavailable/partial/conflicted/late/corrected data and version mismatch. Test server/API data as well as screenshots. Use existing browser/performance standards; record measured latency/response sizes without inventing a new SLO to declare success.

**Exit:** exact accepted producer/API/UI generation with useful real data and all degraded states; authorization/paywall/cache boundaries preserved. Local screenshots are not deployed proof. Rollback through the existing feature flag/release mechanism removes only optional timing context and leaves existing workflows intact.

## W10 — Accrue prospective evidence and judge calibration/action value

**Capability:** learning from genuine issued decisions, not post-hoc narrative validation.

**Owners/paths:** existing Market Memory/Eval/candidate-grade and scheduler/attention owners. One source of truth for observations, forecasts and outcomes through their existing relations. No new PTSE forecast ledger or automatic chat watcher is created by this plan.

**Dependencies:** lawful W3 observation path as early as possible; W6 registered model for forecast accrual; W8 exact candidate/action cohorts for policy accrual. Source first-seen, forecast issuance and outcome maturity are separate proofs.

**Work:** preserve the CURRENT control, exact policy/model/strategy versions and all abstentions. Issue before outcomes, attach mature labels later, measure calibration/proper loss, lead time, false alarms, action regret and full cost/exposure consequences. Predeclare review windows and minimum information, rather than stopping the clock at the first attractive result. Historical inspected data remains a control; it does not count as fresh confirmation.

**Tests/proof:** natural-session issuance receipt, no duplicate opportunity, late source refusal, truly future outcome attachment, original-ID/correction isolation, model change across cohorts, dependency-aware uncertainty, calibration-fit/eval separation and drift. Publish measured counts and precision, not “months of data” as a substitute for effective support.

**Exit:** independently reviewed qualifying, negative or inconclusive prospective result per action/horizon/population. Inadequate information leaves that gate open with a precise next review condition. Rollback withdraws model estimates or downgrades them to research context; no rewriting old predictions or turning missed windows into admissions.

## W11 — Earn a bounded decision change, or retain context with an honest final ruling

**Capability:** only where supported, one attributable useful decision modification under the existing authority owner; otherwise a finished evidence package and explicit no-promotion result.

**Owners/paths:** the incumbent Prophet decision/Conditional Fusion authority and, for exposure consequences, Portfolio/Risk. No universal timing gate, forced de-risk, automatic exit or allocation router. The first change is scoped to **one action × strategy/population × exact horizon × model version**, with an explicit promotion receipt and rollback.

**Dependencies:** source qualification, relevant scientific/forward-policy gates, W9 real-path acceptance, adequate calibration/utility, non-author scientific and code review, current DNR scope and normal release checks. No promotion from a backtest, a screenshot, an LLM recommendation or green unit tests alone.

**Work:** present the complete paired benefit/cost/uncertainty evidence and exact proposed consumer effect to the owner. Implement only the accepted effect. Enforce source/coverage/model-version admission and revocation. On loss of a promotion precondition, revert that bounded effect to the agreed incumbent behavior; missing optional context must never disable unrelated strategies. Escalation or trade effects outside this scope remain closed.

**Tests/proof:** pre/post behavioral difference exactly matches the ruling and nowhere else; wrong population/action/horizon/model cannot activate; revoked authority fails safely; same baseline capital/exposure accounting; rollback rehearsal; exact protected release and real consumer/source readback. Explain what materially changed in the user decision, not just which files merged.

**Exit:** either a proven bounded capability with immutable acceptance evidence, or a no-promotion/negative/inconclusive disposition with the useful context product and all unfinished obligations clearly classified. Full parent completion or scientific stop requires the existing mission owner's acceptance; a failed hypothesis is not permission to quietly cancel remaining lanes.

## 6. Release strategy and operational failure behavior

Use small coherent vertical PRs under current owners; contracts and producers precede consumers, and mixed generations must be impossible or fail to unavailable context. Do not merge unrelated source repairs merely to unblock a nominal deadline. No bulk rebase of #7929 or overwriting #8325's accepted/amended document without its owner. Current main drift is reconciled at each write, not assumed harmless from a prior pin.

Initial release uses an opt-in/read-only context feature under the existing product feature-control mechanism. The writer does not alter risk/rank policy. Verify a natural source observation through actual publication and consumer before calling it live. A deployed page with fixture data is a demonstration, not acceptance. Models and UI releases carry separate version/qualification identities.

On source failure, publish explicit stale/partial/unavailable context under the accepted owner rules; do not default to a safe or permissive signal. On model failure, continue truthful observed context where available. On consumer schema mismatch, fall back to incumbent behavior and surface bounded diagnostics. On a rights violation or provenance mismatch, quarantine the affected input/assessment through the existing correction owner, retaining evidence rather than rewriting it clean.

Set performance budgets from current product/source standards during W0/W7. Batch or reuse existing fetches/caches; do not add one request per candidate for the same market observation. The same observation should be reusable across many candidates while action assessments retain independent strategy/episode keys. Record throughput/latency and storage growth in real acceptance evidence.

## 7. What Astra must not confuse with completion

A 89-test historical receipt is not a current suite run. A passing source validator is not historical PIT qualification. An issue's Todo status is not proof a whole data family does not exist. A source file is not deployed software. An active timer is not a successful natural-session issuance. An observation captured prospectively is not a forecast issued prospectively. A forecast issued prospectively is not a mature calibrated forecast. A calibrated forecast is not a useful de-risk/re-entry policy. A good shadow policy simulation is not causal live uplift. A research-only exception is not production authority.

The new October 2 Options study must be consumed with its exact target, uncertainty and PIT caveat. Do not reinterpret its nonrejections as proven zeros, or transport a volatility finding to a directional return claim. Do not repeat previously completed empirical work merely to generate new activity.

## 8. Mandatory acceptance and durable handoff record

Before any wave or mission is called complete, record:

1. The user/machine capability before and after, with exact action/horizon/population.
2. Accepted owner and current source/PR/commit identities, plus actual served release where owed.
3. Input eligibility, first-known clocks, source/model/target/strategy versions, and immutable data/protocol/result references.
4. Actual tests, mutation results, normal CI and independent review; distinguish inherited receipts from this wave's executions.
5. Research cell counts, outcomes, nulls, uncertainty, multiplicity, coverage and policy costs where relevant.
6. Real source→artifact→API→consumer→maturity proof, plus degraded cases and rollback.
7. Remaining unsupported features/actions/markets, exact blockers, accountable owner and next action.
8. Explicit completion axes and parent `MISSION_COMPLETE`, never inferred from a child merge.

Use current Agent OS/Executive/GitHub continuation owners and existing Linear projection rules after source evidence is known. Do not manufacture a new progress database or claim an automatic continuation from a saved document. Reconcile uncertain effects on the same carrier before retrying. When a true natural-time gate remains, record its evidence condition and continue every independent authorized lane instead of repeatedly redoing the blocked probe.

## 9. Exact first execution frontier

First reconcile #8325 with this package and the current source/authority owners. Then proceed in parallel on **C1 independent review**, **typed observation/action contracts**, and **fresh price/source eligibility plus prospective observation readiness**. Resolve the exact served Prophet/Terminal seams before touching them.

The first actual new market computation is the separately registered **event-independent B0 H5 baseline** when its price evidence qualifies. The unchanged C1 follows on its own event-qualified cohort. Options and other families are independent measured challengers under their current owners, not prerequisites for B0 or an observation-only product. Capture real future evidence early, retain every negative result, and earn additional complexity and authority only when the comparison justifies them.

This is an end-to-end execution program, not an instruction to run Deep Research again or spend another session restating the thesis.
