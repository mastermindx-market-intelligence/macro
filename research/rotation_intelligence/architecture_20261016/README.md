# Sector and theme allocation intelligence — architecture and research

Existing programme: `sector-rotation-intelligence`. Existing workstream: `LEADERSHIP-ROTATION-INTELLIGENCE`. Accountable principal for this supplement: Sol under the current Chairman commission. Carrier: Macro PR #9507, branch `sol/rotation-intelligence-architecture-20261016-c1`.

## Current result: R2 research continuation

The original assessment and architecture are published. R2 has now **specified the first study's population, timing and baselines; inspected real source-cache metadata; reproduced two broad-flow contract weaknesses; and resolved self-financing policy accounting with executable mathematical checks**. These are research results, not a trained model, source repair, native protocol amendment, deployment or investment qualification.

Start with the latest additions:

1. [TARGET_SCOPE_AND_BASELINES_R1.md](TARGET_SCOPE_AND_BASELINES_R1.md): eleven-sector ETF population plus SPY/BIL; precise distinction from the failed member-stock group-persistence construction; as-known cutoff, next-session close proxy, twenty-session blocks, five baselines and declared cost scenarios.
2. [SOURCE_READINESS_AUDIT_R2.md](SOURCE_READINESS_AUDIT_R2.md): timestamp/schema-only inspection of 25 local Parquet files; short sector-flow history; mismatched date tails; existing default-off nine-sector capture; source-owner extension/qualification requirements.
3. [POLICY_ACCOUNTING_SPEC_R1.md](POLICY_ACCOUNTING_SPEC_R1.md): exact proportional-cost budget equation, uniqueness argument, independent algebraic comparison and settlement-cash versus security-turnover distinction.
4. [probe_broad_flow_contract.py](probe_broad_flow_contract.py) and [broad_flow_probe_results.json](broad_flow_probe_results.json): exact-source extraction and fake-provider reproduction of market-price-in-NAV, retrieval-date indexing and weekend-date behavior.
5. [policy_accounting_witness.py](policy_accounting_witness.py) and [policy_accounting_results.json](policy_accounting_results.json): seven closed-form cases, 512 algebraic comparisons, 128 cost-monotonicity checks and eight bad-input refusals.

The flow probe establishes behavior at **BroadFlowAdapter.fetch**, not the entire production ingestion pipeline. Its supplied `regularMarketTime` is a market-price clock, **not a qualified NAV timestamp**. A later repair must not copy that field into a NAV date and claim the problem solved. Downstream calendar filtering and actual live incidence were not established by this probe.

The new scripts and recorded scientific outputs were retrieved from GitHub at `169413291d684e945bd57fb7f83d93e28ed16796` and reproduced on M2. All four script/result hashes matched the originally executed bytes; all eleven pre-existing file blobs were unchanged at that boundary. Final navigation/diff/CI state after this README update is recorded in the PR receipt rather than predicted here.

## Original foundation — retained, not rewritten

- [ASSESSMENT.md](ASSESSMENT.md): original 44,909-byte report with 35-source register. SHA-256 `4ba6241675c3f3528706f7c859019dd8e6f2ce390bd31199e7a4254bf1e26c4c` remains unchanged.
- [ARCHITECTURE.md](ARCHITECTURE.md): measurement, forecasting, portfolio policy and stock/instrument expression; incumbent system boundaries; horizon and model ladder.
- [DATA_CONTRACTS.md](DATA_CONTRACTS.md): as-known identity, availability, revisions, corporate actions, group indices and allowed use.
- [RESEARCH_DESIGN.md](RESEARCH_DESIGN.md): candidate economic estimands, selection/dependence/multiplicity, maturity and confirmatory conditions. It is not canonical V3.
- [NATIVE_PROTOCOL_CROSSWALK.md](NATIVE_PROTOCOL_CROSSWALK.md): seven-pair native H1/H2/H3 versus the broader allocation question, preserving source/holdout/negative-evidence restrictions.
- [LITERATURE.md](LITERATURE.md): 16 primary-source method entries with actual review depth and transfer limits.
- [READINESS_AND_DELEGATION.md](READINESS_AND_DELEGATION.md): industry-mechanism research book, dependency sequence and six later bounded implementation packets.
- [REVIEW_AND_VERIFICATION.md](REVIEW_AND_VERIFICATION.md): prior verification and review dispositions, supplemented by the new R2 documents/PR receipt.
- [synthetic_design_checks.py](synthetic_design_checks.py) and [synthetic_design_results.json](synthetic_design_results.json): the original twelve synthetic design witnesses and known-covariance demonstration. They are unchanged and were not rerun unnecessarily.

## Mission and design decisions

The user wants reliable exposure selection across sectors, industries and themes as regimes and breadth change; group beta followed by residual stock alpha; and a bill alternative when equity risk is unattractive. The target is measurable economic precision with uncertainty and abstention, not a guaranteed winner at every instant.

Keep measurement, prediction and policy distinct. Separate total equity risk from opportunity granularity: narrower breadth may justify fewer candidate groups and less aggregate risk. Keep macro, industry supply, earnings and price cycles on their own evidence clocks. Use incumbent identity, data, regime, rotation, evaluation, portfolio, Prophet and Terminal owners—no replacement director, graph, data store, model registry, publisher or queue.

Track A is the existing native seven-pair study and its LR-W6 repair. Track B is the explicitly broader ETF allocation study, followed by separately qualified industry/theme and stock-expression work. Track B cannot reopen Track A's held outcomes or the killed C1 member-stock construction by changing names. Native P2 is falsification-only. Previously inspected history is not made untouched by a new split or new family identifier.

## Source identities and evidence limits

Compatible protected procedure pin: Mastermind `50107c31531d3b4ab5a18b5acf5e77954a0549e3`, Skillpack 1.0.1 / bootstrap 1. The initial assessment retains its Macro `460e3015...` observations; the architecture began at `4ae7f2ac4c58e6e93945a6f09313bcaadba5709e`. R2 source-interface inspection is pinned to `3ab3382af89242c7b7fe8c65360bd883a7dd3504`. Unrelated master movement does not invalidate unchanged research.

The local M2 metadata observation at 2026-10-17T04:58:33.581812Z is a research-cache observation, not production freshness, a locked dataset snapshot or original historical availability. Parquet schema/counts and timestamp statistics were read; price/return/volume columns were not decoded. The broad-flow and policy experiments use invented inputs. No native market-outcome study was run.

The existing [workstream](../../../agentos/workstreams/WS-LEADERSHIP-ROTATION-INTELLIGENCE.md), Mastermind #1194, Macro #7646 and precursor #9035/#9134 remain the continuity homes. Existing source writers and independent natural-consumption, issuance, operator/visual and scientific obligations remain intact.

## Next actionable dependency

Qualify the **existing thirteen-series source and reader path** for the declared study. The dormant capture currently covers nine sectors, not XLC/XLRE/SPY/BIL, and its source acceptance expressly leaves rights, original availability and other qualification fields unresolved. The next source integration must extend that incumbent capability with verified clocks, cohort and rejecting consumer; it must not build another capture service or invent missing timestamps.

Carry the reproducible BroadFlowAdapter findings into its exact source-owner repair/acceptance scope. The accounting specification supplies a checked primitive for the incumbent evaluator, but no production code has been wired. Only after the actual source/protocol/evaluation conditions are ready should the admitted historical development or prospective experiment run.

## Release and effect state

Native GitHub remains the sole publication carrier for this branch. The earlier local managed-workspace acquisition was NOT_APPLIED; no shared checkout was changed. The new local files are bounded research evidence, not another source workspace or data owner.

The earlier head `5d68fe...` now has successful main ci-gate and all twelve CI packs. Its inactive pilot-base authority context remains distinct. Those checks are not copied onto later commits. The final independent package-review attempt from R1 failed with provider 403 and no substantive verdict; it was not retried or routed through another provider. No new child or watcher was started in R2, and the earlier children are terminal.

The PR remains **Draft/HOLD** pending the real independent review and repository release conditions. No market-outcome read, source acquisition, live capture activation, collector repair, scoring/ranking/sizing promotion, trade, credential change or deployment is claimed. Research continuation is published and recoverable; the broader predictive allocation programme is incomplete.
