# Sector and theme allocation intelligence — architecture and research

Existing programme: `sector-rotation-intelligence`; workstream: `LEADERSHIP-ROTATION-INTELLIGENCE`. Accountable principal: Sol under the current Chairman research-first commission. Same carrier: Macro PR #9507, branch `sol/rotation-intelligence-architecture-20261016-c1`. Production integration, native outcome reads and investment authority remain unqualified.

## R6 — source-readiness adapter, implemented and tested

The Chairman has assigned the current Sol receiver to execute source-readiness work rather than wait for a named historical source owner. [R6 native source-consumer record](R6_NATIVE_SOURCE_CONSUMER.md) documents the new [pure Tiingo EOD projection](tiingo_allocation_adapter_r6.py) and [21 negative/positive tests](test_tiingo_allocation_adapter_r6.py). The code consumes thirteen **already-returned native Data OS history objects**, verifies exact sessions, clock/basis/revision and BIL coverage, and withholds all PIT/rank/gate/size/trade authority. Tests ran red then green on invented data; three targeted guard mutations were caught. It does not acquire private source data or retry the blocked archive read. The actual licensed source-consumer read and real native-host integration are still unqualified; this is executable code and contract proof, not a live empirical result.

## Earlier result: R5 information speed versus trading speed

Read [DECISION_SPEED_RESULTS_R5.md](DECISION_SPEED_RESULTS_R5.md) and its [frozen design](DECISION_SPEED_DESIGN_R5.md). This independent synthetic diagnostic separates signal memory, source lag, review cadence, confirmation and next-close execution. Routine rebalancing is held constant, so daily review does not force daily weight maintenance when the accepted target is unchanged.

The complete [64-cell grid](decision_speed_grid_r5.csv),512 paths per cell, is retained. In the fixed durable-change example the shorter signal shifts exposure earlier but incurs more churn and produces lower net wealth than the slower control. Three distinct-review confirmations reduce churn but add delay; they do not establish optimal timing or a qualified real-world advantage. A faster refresh cannot remove the mathematical memory of a slow trailing signal.

[Source](decision_speed_r5.py), [27 reference tests](test_decision_speed_r5.py), and [seven intentional counterfactuals](check_speed_mutations_r5.py) were executed locally and again from published source on M2. The nine-decimal grid reproduced exactly after line-ending normalization only. The vectorized cost math matched the unchanged R2 scalar function on384 invented comparisons. This is author verification of a controlled experiment, not independent final review, native statistical qualification or a market backtest.

**New child status is unresolved.** The independent arithmetic-fixture task `rotation-r5-20261017-c1-cadence-fixtures` was submitted once under original root/parent `rotation-intelligence-census-20261016-sol-c1`; its status is `ACTIVE_OR_WAITING`, lineage/worker state unverified, no result. Supported original-owner observation did not establish execution or completion. It was not canceled, duplicated or re-identified, and its result was not used. See the [exact reconciliation record](https://github.com/mastermindx-market-intelligence/macro/pull/9507#issuecomment-6234112703). Do not carry forward R4's now-historical statement that all children are terminal; no durable-running or background-Web claim is made.

## Current real-data and release boundary

The R4 source/metadata-inspection operation remains blocked before dispatch and unretried; its cause is unestablished. No new source-owner disposition was received in this continuation. A successful independent research/tool action does not clear that exact refusal. The separate original final-package reviewer403 still has no substantive verdict and was not replayed through another provider.

The highest-value real-data step remains qualification of the already-existing thirteen-series Data OS archive and its consumer: payload integrity, actual session/value coverage, adjustment revisions, source-use mapping and the BIL date gap. The current synthetic studies do not perform those acts or permit held native outcomes to be reopened.

The new child needs an actually supported same-run binding/return reconciliation. Final design acceptance and exact-head CI also remain required before this draft can be released. No new scheduler, source registry, evaluator, retry loop, risk veto, portfolio execution or data acquisition is introduced. Do not add another synthetic grid merely to avoid these real dependencies.

## R4 — regime and uncertainty research, preserved

- [REGIME_ESTIMATION_RESULTS_R4.md](REGIME_ESTIMATION_RESULTS_R4.md):54 fixed cells ×12,000 replications, four oracle-parameter estimators,216 analytical-risk checks and20 passing tests; all adverse cases retained.
- [REGIME_ESTIMATION_DESIGN_R4.md](REGIME_ESTIMATION_DESIGN_R4.md), [source](regime_conditioning_r4.py), [tests](test_regime_conditioning_r4.py) and [complete grid](regime_conditioning_grid_r4.csv).
- [UNCERTAINTY_METHOD_REVIEW_R4.md](UNCERTAINTY_METHOD_REVIEW_R4.md): target-specific uncertainty, selection, dependence, delayed feedback and version-sensitive method guarantees.

Thin hard-regime cells can amplify noise. Shrinkage can reduce error without improving rankings and can worsen choices under a wrong prior. Reversed economic relationships remain adverse even with correct covariance algebra. Mean confidence, realized-outcome probability and top-set probability are different claims. Corrected subagent subsets and original negative evidence remain preserved; no stock/sector forecast has earned authority from these synthetic results.

## R3 — executable baseline rehearsal and existing-source discovery

[EXISTING_ARCHIVE_REUSE_R3.md](EXISTING_ARCHIVE_REUSE_R3.md) records37 original Tiingo receipts and37 materialized views across all thirteen required instruments. Receipt/context and footer metadata were checked, not complete raw/value/revision/PIT qualification. Deep histories exist; later sector/SPY slices reach October15,2026 while the inspected BIL history ends October9. Existing special commercial rights must not be presumed absent because provisional flags remain, and exact source/consumer use is not invented from those flags. Reuse the existing reader before proposing reacquisition; never forge a Yahoo receipt from a Tiingo source.

[SOURCE_READER_REHEARSAL_R3.md](SOURCE_READER_REHEARSAL_R3.md), [its verification](rehearsal_verification_r3.json), [reference](allocation_rehearsal.py), [tests](test_allocation_rehearsal.py) and [counterfactuals](check_rehearsal_mutations.py) cover the earlier full invented-input baseline sequence. Its35 tests/eight mutations,46 unchanged incumbent reader tests and12 calendar/cutoff checks remain evidence for those exact bytes—not generic production or independent review approval.

## R2 — fixed target, source constraints and accounting

- [TARGET_SCOPE_AND_BASELINES_R1.md](TARGET_SCOPE_AND_BASELINES_R1.md):eleven sector ETF instruments plus SPY/BIL, exact cutoff/next-close/holding geometry and five frozen comparators. The R5 cadence grid is a separately labelled diagnostic; it does not rewrite these baselines.
- [SOURCE_READINESS_AUDIT_R2.md](SOURCE_READINESS_AUDIT_R2.md):local-cache metadata, short flow history and differing date tails; not current production freshness.
- [EXISTING_READER_INTEGRATION_R1.md](EXISTING_READER_INTEGRATION_R1.md):preserve the incumbent nine-node/26-session/09:00/63-price contract; the new study requires its own thirteen-input/20-session/08:00/64-price-return adaptation.
- [POLICY_ACCOUNTING_SPEC_R1.md](POLICY_ACCOUNTING_SPEC_R1.md), [accounting witness](policy_accounting_witness.py) and [results](policy_accounting_results.json):self-financing holdings, costs and turnover.
- [BroadFlowAdapter probe](probe_broad_flow_contract.py) and [results](broad_flow_probe_results.json):fake-provider witnesses for price-versus-NAV and source-date ambiguity. No live incidence or collector repair is claimed.

## Original architecture and literature

- [ASSESSMENT.md](ASSESSMENT.md):unchanged44,909-byte original report, SHA-256 `4ba6241675c3f3528706f7c859019dd8e6f2ce390bd31199e7a4254bf1e26c4c`.
- [ARCHITECTURE.md](ARCHITECTURE.md):measurement → forecasting → policy → instrument/stock expression; total risk distinct from opportunity granularity.
- [DATA_CONTRACTS.md](DATA_CONTRACTS.md):as-known clocks, memberships, corporate actions, return basis and allowed use.
- [RESEARCH_DESIGN.md](RESEARCH_DESIGN.md) and [NATIVE_PROTOCOL_CROSSWALK.md](NATIVE_PROTOCOL_CROSSWALK.md):native seven-pair H1/H2/H3 remain distinct from the broader ETF/industry/theme/cash questions. Preserve their read restrictions and original failures.
- [LITERATURE.md](LITERATURE.md):primary research with actual review depth and transfer limits.
- [READINESS_AND_DELEGATION.md](READINESS_AND_DELEGATION.md):mechanism research and bounded later implementation packets, not dispatched jobs.
- [REVIEW_AND_VERIFICATION.md](REVIEW_AND_VERIFICATION.md), [original mathematical script](synthetic_design_checks.py) and [results](synthetic_design_results.json):historical exact-artifact evidence; newer source/worker/verification facts above supersede only their status, not their recorded results.

## Recovery and allowed scope

Same compatible protected procedure pin: Mastermind `50107c31531d3b4ab5a18b5acf5e77954a0549e3`. Same original research root and GitHub publication carrier. Preserve current source writers, source-use denials, native look accounting, DNR constructions and unresolved effects. GitHub/Agent OS/Fabric keep their established responsibilities; this directory is research, not another authority or lifecycle registry.

**DRAFT/HOLD FOR SOL.** Do not ready, auto-merge, apply merge-on-green or merge without the actual independent review and required checks at the accepted head. No production deployment is needed for this research-only PR. The broader predictive allocation programme is incomplete; no live capture, original-source read, Trial/Vault act, production engine change, score/rank/size promotion, trade or deployment occurred in R5.
