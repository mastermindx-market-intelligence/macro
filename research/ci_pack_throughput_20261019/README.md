# CI pack throughput: October 19, 2026

Commission: `/Users/chriswong/Desktop/MASTERMIND-CI-PACKS-CODEX-ASTRA-HANDOFF-2026-10-19.md`, directly assigned to Codex chat `01a153e8-3c85-7bb2-af63-7f477b570512`.
Source: Macro `168c96bf9ca68427749bc70664902c343d968d9c`; protected procedure: Mastermind `5469f12de01158b0e495d616d2be6f56c03cf8a8`, skillpack 1.0.1/bootstrap 1.

Status: **three bounded optimizations merged with full hosted proof; a fourth parser trial passed local validation; fleet throughput outcome not yet proven**.

## Decision

Keep twelve as the current maximum. Trial removal of duplicate dependency-closure traversal before changing partitioning, runner count, or checkout materialization. A named suite is analyzed in the suite-reference pass and again in the generic path-reference pass of `infer_job_scopes`. The second traversal adds no ownership: the same command has already passed the ambiguity check and both paths undergo the same final peer-test fallback filter. Skip that already-processed path within that command. No persistent cache is introduced.

The September test-setup reuse in PR #8126 is already on main. Do not rebuild it. Open PR #8094 owns a different optimization: limiting the population inferred by `curated_exclusive_closure_findings`. This trial changes only duplicate work inside `infer_job_scopes`; it does not adopt, replace, or release #8094.

## Baseline and measurement limits

`baseline.json` retains all 40 recent concluded `ci.yml` PR runs and exact URLs, candidate/base/plan identities where available. The raw job, plan, and selected log captures are retained at `/Volumes/Mastermind/ci-pack-throughput-20261019/`. GitHub job/step timestamps and the existing runner's group boundaries supply timings; no new timer or service was added.

The primary cohort is **22 noncancelled first attempts**: 15 successful and 7 failed. Seventeen cancelled runs remain a separate stratum. One successful rerun, 39228626106 attempt 2, is excluded from primary metrics because reused jobs expose negative job-created-to-start intervals; its original run creation also predates its retry. The original inclusive calculations remain visible in the JSON, explicitly separate from `primary_strata`.

| Metric | Population | p50 | p95, nearest rank |
|---|---:|---:|---:|
| Run creation to ci-gate completion | 15 successful first attempts | 53.3 min | 67.9 min |
| Run creation to ci-gate completion | 7 failed first attempts | 68.5 min | 119.1 min |
| First failed-step completion | 7 failed first attempts | 43.9 min | 69.6 min |
| Summed job wall time | 15 successful first attempts | 227.15 runner-min | 321.97 runner-min |
| Recorded pack queue interval | 264 pack jobs | 595.5 sec | 1172 sec |
| Pack checkout step | 264 pack jobs | 198 sec | 319 sec |
| Pack execution wrapper | 264 pack jobs | 731 sec | 2068 sec |

These are descriptive recent-traffic statistics, not causal treatment estimates. Run creation is a proxy for push time, not an exact push timestamp. A failed-step completion can trail the actionable error printed within it; base replay can extend that delay. Job creation can precede dependency readiness. Summed job wall minutes are neither billed rounded minutes nor an invoice. Hosted quota and invoice rate are not established by the repository runner API. The broad/global subgroup has only four runs, including just one success, so its p95 is an extreme observation with weak precision. The sample conditions on completion and excludes jobs still running at collection time.

The repository configuration currently selects `CI_EXECUTION_ROUTE=hosted`, `CI_SCOPE_MODE=active`. The repository runner endpoint returned four Mac builders; that is not an organization-wide hosted concurrency quota or permission to promote home CI. Issue #6351 remains the separate self-hosted promotion carrier. No runner registration, labels, capacity controls, routing variables, or organization settings were changed.

## Critical-path findings

The handoff's 1400-second control-plane job is important, but not the sole floor. Logs from each noncancelled run's last-finishing pack and pack zero show:

- `ci-control-plane-contracts` packing-contract step: median about **848 seconds** across 20 observed group intervals. Its other steps add census, trigger, and policy work.
- `fif-kernel-guards` kernel pytest step: median about **1618 seconds** across nine group intervals. This growing workload is still estimated by the manifest's generic weight heuristic.
- Checkout is repeated on every pack; a single observed checkout reached **2504 seconds** in run [39228917299](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39228917299).
- Large queue delays affect the planner, packs, and final gate. More matrix entries do not create more admitted capacity.

The logical-step sample is intentionally biased toward critical packs; it is not a population-wide job-duration estimate. Group intervals must not be mistaken for complete job wall time or source-independent execution digests. Existing `--emit-timing-observations`, `capture_ci_canary_receipt.py`, and `compare_ci_canary_receipts.py` remain the instrumentation to use for prospective controlled evidence.

A diagnostic partial Python 3.14 cProfile run was deliberately interrupted after 23 tests and 523.97 seconds; **it is not a passing full-suite result or Linux runtime qualification**. It recorded 2,638,942 stat calls, 2,882 suite-closure calls, and 496 seconds in scope inference. This identifies a mechanism, not a hosted speedup. Acceptance measurements use Python 3.12.13 separately and require result parity and actual hosted execution.

## Ranked architectures

1. **Minimal execution optimization, chosen first.** Remove duplicate traversal of a named suite inside a command. Keep selection, job/proof identities, dependency isolation, exact merge/base identity, replay, and gate reconciliation intact. Reversible one-function change; expected savings are limited to scope derivation and its repeated contract-test callers. It cannot remove checkout, queueing, FIF execution, or the entire 1400-second floor. Downside: a modest improvement may not move fleet p95; measure before expanding.
2. **Measured semantic-job decomposition and packing.** Qualify independent subdivisions of the two long logical jobs, retain every command and proof, then rebalance on execution-digest-bound timings with startup and dependency costs. This can lower an indivisible job floor while retaining twelve outer packs. Downside: more proof identities, potential shared-state/order dependencies, changed contract ceilings, and cold starts; requires an explicit equivalence corpus and hosted proof. It is viable but larger than the first trial.
3. **Planner-produced sparse execution materialization.** Keep full tracked-path identity while materializing only proven reads and write baselines. Potentially saves roughly three minutes per pack and substantial aggregate minutes. Downside: source/runtime/static reads are not a complete write inventory; omitted baseline files can cause false failures or data truncation. It requires per-job materialization contracts, missing-byte refusal, and qualification of base replay. Not a safe first edit based only on `paths:`.

`shard-simulation.json` replays current declared weights over the actual eligible job IDs at 8/12/16/24/32 packs, excluding candidate-only jobs missing from the current manifest. This is a counterfactual packing simulation, not a promise that 32 hosted runners start concurrently. The heavy-job floor often remains unchanged. Twenty additional checkouts at the primary median alone would add approximately **66 runner-minutes per run**, before setup or queue effects. Do not promote 24/32 based on matrix size.

Exact-base result reuse remains a later alternative for hermetic jobs only. It needs trusted evidence bound to the exact base, job execution digest and proof identity, with live replay on missing/corrupt/expired/shifted evidence. This trial adds no cache. Cheap preflight remains viable only as an earlier evaluation of existing canonical contracts, never a second selector or gate.

## Correctness and release boundary

Before modification, the existing workflow/semantic/fragment/trusted-route corpus passed **200 tests** on Python 3.12.13. It covers no-work, planner failure, main dispatch, cancellation/supersession, fork/hosted routing, missing fragments, and exact tested-tree/base mismatches.

The new deterministic regression failed on original source because a repeated named suite was traversed three times; the repaired code traverses it once while still analyzing the separate script and retaining the same scope/fallback contents. An opaque pytest directory target still refuses narrow inference. Both focused tests pass. Complete real-manifest scope equality and ten plan replays passed; closure calls fell from 1352 to 697 with identical scope hash `b6509bbd711065dcff26d0ed20658bf58e4adafee0bd4c6745cf7897af195ea8`. The affected suite passed 327 tests with two existing sparse-only mockups skips, and the post-change authority/negative corpus passed 200 tests. The bounded independent Fabric review passed and its assumptions were verified. Hosted full-suite execution and the binding gate then passed.

Rollback is a normal revert of the duplicate-traversal change through the existing source/CI route. There is no runtime configuration, stored cache, migration, or admission state to unwind. Do not claim the >=30% p95 target, fleet acceptance, or production improvement from local tests, an open PR, or one green run.

The next exact action is to collect naturally concluded post-merge first attempts under `natural-comparison-method.md`. Expand only if comparable coverage, measured bottleneck and cost justify another slice; do not dispatch artificial CI to populate a treated cohort.


## First hosted result and current decision

[PR 9722](https://github.com/mastermindx-market-intelligence/macro/pull/9722) merged at 2026-10-19T13:13:09Z as `7736fd72895fc24e55bf2d4bbc7b1f4e94203414`. Source/test blobs were verified on main, and the remote feature branch is absent. [Run 39247388552](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39247388552) passed all twelve packs and complete semantic reconciliation over 255 eligible jobs. The latest authority and fence checks passed. The original observer is settled and consumed. `trial-result.json` retains exact identities, timings, local CPU samples and the first post-merge observation.

The full-suite trial took **78.1 minutes** from run creation to gate completion and **337.38 summed job wall minutes**. Pack 0 took 1604 seconds, including 141 seconds checkout and 1440 seconds in the execution wrapper. Its packing-contract group took **740.414 seconds**, with 694 passed and one existing skip, versus a **847.738-second median across 20 historical group observations** (range 460.665–925.303). The 12.7% difference is descriptive: the historical sample is biased toward critical packs and varies in source, workload and retry strata. It is not a controlled speedup or fleet p95 result. The warmed local process-CPU experiment showed 51.6% lower median inference CPU time; it measures a different level of work.

Pack 8 finished last at 12:53:16Z. The gate began at 13:07:01Z and finished at 13:07:13Z: **825 seconds of waiting for a 12-second aggregate job**. Packs 5 and 8, not the optimized control-plane pack, remained the final execution floor. These observations reject treating local inference savings or larger shard counts as sufficient evidence for the 30% fleet target.

At 13:46Z, all five naturally occurring PR runs created after merge were still queued. No completed treated fleet cohort exists yet. Use exact tested implementation bytes and canonical plan coverage to establish eligibility; creation time alone is insufficient. Keep twelve packs and the current proof/isolation controls. Investigate further partitioning only after comparable timing evidence identifies a useful reduction in the remaining floor and its queue/cost consequence.


## Natural traffic, 16:50Z

The snapshot contains **57 runs: 9 pending, 9 cancelled, 2 completed reruns excluded, and 37 verified first-attempt completions (30 success, 7 failure)**. Every eligible tested-tree planner blob matches the landed first optimization and its base descends from the merge. There are 36 scoped completions and one global success (257 jobs, 3067 seconds). Two scoped runs now match a baseline selected-job set, but **none matches its execution/step-proof signature**. `natural-comparison.json` retains identities, canonical signatures, eligibility and strata; `natural-comparison-method.md` fixes the method.

The 29 scoped successes have run-to-gate p50/p95 **1920/3511 seconds**, versus **3265.5/4074 seconds** for fourteen historical scoped successes. Summed job wall minutes have p50/p95 **145.37/216.80**, versus **223.02/257.63**. The seven scoped failures have first-failed-step-completion p50/p95 **1768/2686 seconds**, versus **3118/4178 seconds** for four historical scoped failures. These are different-work, completion-conditioned descriptive strata with nine pending observations, not a causal estimate or proof of the 30% target. The single new global success also differs in coverage from the earlier full trial.

## Second bounded trial: calibrate two heavy-job weights

The full hosted log covers command groups for all **255 logical jobs**, totaling **14219.792 command seconds**. FIF consumed **1428.794 seconds** against heuristic weight **161**; nine historical kernel observations have median **1617.655 seconds**, plus about thirteen seconds of other guards. Earnings economic dossier consumed **1070.867 seconds** against heuristic weight **59**, with only one observed full run. Control-plane commands totaled **1431.118 seconds**, already represented by weight 1400.

The next slice sets only FIF's balancing estimate to **1630** and earnings' to **1070**, retaining the existing twelve-pack algorithm. Replaying the exact tested manifest and selected jobs reproduces the original assignment first, then produces:

| Weight scenario | Maximum modeled command time | Difference |
| --- | ---: | ---: |
| Existing heuristic | 2085.4 seconds | baseline |
| FIF only | 2018.1 seconds | -3.2% |
| FIF and earnings | 1532.3 seconds | -26.5% |
| Conservative pair: 1400 / 900 | 1532.3 seconds | -26.5% |
| All measured weights, diagnostic only | 1431.1 seconds | -31.4% |

`weight-calibration.json` records all costs, exact trial manifest/plan identity, assignments and replay results. Across **42 captured historical and early treated scopes**, the pair improves modeled command maxima in 13 and worsens none; median change is zero. Scopes containing jobs absent from the trial inventory are explicitly excluded. Job membership, multiplicity and measured total work remain constant. The all-measured scenario is a diagnostic ceiling, not a proposed broad calibration.

This model does not predict a 26.5% gate improvement. Dependency installation and environment reuse, checkout/setup, queue pickup and artifact time are excluded, and repacking may change installation reuse. Earnings has one observation. The new test checks unchanged selected jobs and execution/step proofs, twelve nonempty packs, complete disjoint coverage, separated heavy jobs, and a changed plan hash binding the new assignment. Existing authority tests and normal hosted full-suite checks remain release gates. Compare actual command, install, checkout, queue and total wall cost after the trial; reject a cost or isolation regression even if command balance improves.

The optional Fabric review attempt `ci-pack-20261019-01a153e8-weight-review` ended before reviewer execution with `admission_denied reason=canonical_source_unreadable` (rc 78). No review verdict was established, no alternate provider was used, and the prior deduplication review does not cover this calibration. This reversible estimate-only change is directly verified under the standing proportionate-review policy; required repository release checks remain binding.

Rollback is a normal revert of the two weight entries. No command, selector, proof contract, runner route, shard count or external runtime configuration changes.

Candidate validation: **7 targeted packing/coverage/hash/curation tests passed** in 135.76 seconds, and **200 authority/negative controls passed** in 58.43 seconds. Both runs emitted 42 existing pytest temporary-directory cleanup warnings. No packing ceiling was raised.

## Second hosted trial: base timeout, then landed-fix recovery

[Run 39282678531](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39282678531) tested head `aebcbe276560553b306ada6b467444cd2d446fe9` at merge tree `0e42e3232b0bc9b297ab8e6d7114df2ae6a30c4f`. Its authoritative plan selected all 256 code jobs and reproduced the calibrated assignment exactly; all job execution and step proofs matched the exact tested manifest. Relative to the first full trial, main added `research-codegen-runtime-qualification` and changed seven other job definitions. These are material comparability limits, preserved in `weight-failed-trial.json`.

Eleven packs, authority, fences and contract-delta passed. Pack 7 and the semantic gate failed because **defense-rail-laws exhausted its eight-minute deadline on both candidate and isolated base replay**, at 16:26:24Z and 16:52:46Z respectively. The run is a failed observation containing extra replay work, not a comparable successful throughput sample. Its observer settled with exit 1 and was consumed; all logs are retained.

The independently owned [PR 9758](https://github.com/mastermindx-market-intelligence/macro/pull/9758) had already diagnosed this expanded battery, passed its required hosted checks, and merged as `bee22730967cf12d6aabbc18b79a37135f9b3c01` at 16:46:22Z. Its only manifest change raises that logical job's deadline from eight to twelve minutes while keeping all commands. Recovery incorporates this landed fix through a normal main merge into PR 9763, preserving the two-weight trial unchanged. The new source receives normal CI; no blind rerun, gate suppression or duplicate repair is used. Hosted success on the refreshed source remains required.

## Recovery run: repair the schema identifier without weakening validation

[Run 39290075936](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39290075936), head `67377ec633cf3e797ebe61a0453ccd2b44b18b35`, passed the Defense job but failed `research-price-panel`. Three population tests failed on both candidate and isolated base replay because the schema introduced by PR 9765 omitted `$id`. The existing registry loads every Market Memory schema by this identifier; its first load failed with `KeyError: '$id'`, leaving the population manifest unavailable to later tests. Main still had the same defect, and the open-PR/path check found no repair touching the schema.

The repair adds only `https://mastermind-x.com/contracts/market_memory/e0_reviewer_plan.v1.schema.json` as that schema's canonical identifier, following its peers. Removing this one field reproduces the original parsed schema exactly: all payload constraints, validation logic and authority boundaries remain unchanged. All 52 Market Memory schema identifiers are complete and unique. The existing three failing tests reproduced locally before repair; all 181 population/reviewer-plan tests pass after repair. The exact full owning pytest command then passed **1345 tests and 429 subtests** in 116.29 seconds (45 inherited warnings). Required hosted checks remain binding; neither failed run is a successful throughput sample.

The passed heavy-job groups in this failed run further illustrate timing variability: FIF's kernel group took 1955.4 seconds, while earnings took 577.1 seconds. FIF also had a long checkout and finished as the 47-minute pack. These observations do not validate the original command-only counterfactual or justify another weight change; retain them separately while completing the current trial.

## Weighted trial landed; performance remains a measured open question

[PR 9763](https://github.com/mastermindx-market-intelligence/macro/pull/9763) merged at **2026-10-19T18:49:48Z** as `38d2dac36faabfff04f8efe5ee28e5c8dfa1c5ae`. [Run 39298424658](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39298424658) passed all twelve packs and complete reconciliation of **257 logical jobs**, plus contract-delta, fences and active main authority. Its tested head is `996a22e7e5acebc5fd883068f04fa803d7a1aab7`, tested merge tree `a111b2f49b0d46b06d8a2d4f22dec9bf4d6acd6c`, and plan hash `3f62b28f67c5a17df6094debca5aa845ebf562c605cf5ce454798aeac5dfa4cb`. The merged planner/schema blobs match the candidate; the exact new regression is present alongside independently landed test edits. Observer 50933 is settled and consumed. `weight-success-result.json` retains the identities, stage costs and comparability limits.

| Observed metric | First full trial | Successful weighted trial |
| --- | ---: | ---: |
| Logical jobs | 255 | 257 |
| Run creation to binding gate | 78.08 min | 48.82 min |
| Summed job wall time | 337.38 min | 371.70 min |
| Last pack end to gate start | 825 sec | 3 sec |
| Pack checkout total | 2520 sec | 2735 sec |
| Command groups total | 14219.79 sec | 15630.72 sec |
| Dependency install groups / total | 175 / 1737.74 sec | 174 / 1902.65 sec |

The 37.5% shorter single-run latency is **not a demonstrated 30% fleet p95 gain**. Aggregate job time increased 10.2%; cost neutrality is unproven. Main added `research-codegen-runtime-qualification` and `research-vault` and changed seven existing execution definitions, while source inputs and runner conditions also differ. The final-gate wait alone fell by 822 seconds. Neither these observations nor the broader unmatched natural cohort isolate the treatment effect.

The successful run's critical pack was pack 7: **2833 seconds wall**, including **245 seconds checkout**, **2266.33 seconds command groups**, and **220.33 seconds dependency installation**. Its largest groups were dashboard rendering (442.75 seconds), the newly added Research Vault battery (370.49), and a Defense command (305.33). FIF ran alone in pack 0 with **2035.11 command seconds**; earnings ran alone in pack 2 with **550.89 seconds**. Workload growth and heterogeneous execution times remain material.

Replaying this exact tested manifest reproduces the hosted assignment. Holding all 257 realized command costs fixed, removing only the two calibration overrides raises the modeled maximum from **2266.33 to 2694.53 seconds** (a 15.9% command-only difference). This supports retaining the bounded calibration, but excludes installation/environment reuse, checkout, queueing and artifacts. It does not establish causal total cost or justify further weight changes. The single FIF job already imposes a 2035-second command floor, limiting what additional balancing alone can save on this observation.

**Next decision:** retain twelve packs and both measured overrides while collecting naturally concluded first attempts after the second merge. Require planner blob `f5e4e9c3202c35c9b29c6d038e1d077661fe6375` and base ancestry from `38d2dac36faabfff04f8efe5ee28e5c8dfa1c5ae`; separate this cohort from deduplication-only traffic. At 18:53Z the first post-merge snapshot contains one pending run and no completed observations. No new shard, routing, timeout, caching or test-decomposition change is justified by that sample. The previous 37-run cohort and all cancellation/failure strata remain available; do not reclassify failed base replays as successful cost samples.

## Weighted natural traffic, 20:48Z: retain the trial, do not expand

The fixed post-weight window now contains **32 runs: 19 verified first-attempt completions (14 successes, 5 failures), 9 pending and 4 cancelled**. All completed observations use the landed weighted planner blob and a base descending from its merge. None matches the original baseline's complete selected-job set or execution/step-proof signature. One success and one failure are global; the remaining seventeen are scoped. `weighted-natural-comparison.json` retains every included run, eligibility, comparison signature, stage observations and the analyses below.

| Scoped metric | Original baseline | Weighted cohort |
| --- | ---: | ---: |
| Successful run-to-gate p50 / p95 | 54.43 / 67.90 min, N=14 | 35.10 / 65.68 min, N=13 |
| Successful summed job wall p50 / p95 | 223.02 / 257.63 min, N=14 | 215.68 / 399.37 min, N=13 |
| First failed-step completion p50 / p95 | 51.97 / 69.63 min, N=4 | 27.83 / 35.08 min, N=4 |

These are unmatched, completion-conditioned descriptive statistics. The early six-success p95 of 40.43 minutes became 65.68 minutes as slower observations completed: do not promote a partial cohort's apparent gain. The larger wall-time tail is also not an attributable calibration regression. Scope sizes vary from 3 to 258 jobs, source/command definitions changed, nine runs are still pending, and runner labels do not establish immutable image parity. Excluding this commission's report run leaves scoped-success N=12, run-to-gate p50/p95 36.31/65.68 minutes and summed wall 223.70/399.37 minutes; the decision is unchanged.

An **exploratory exposure split**, added after inspecting this cohort, shows that **nine of nineteen completions selected neither calibrated job**. Their partition cannot change from these two overrides. Among scoped successes, the eight unexposed runs have p50/p95 22.46/37.52 minutes; the five selecting FIF have 40.87/65.68 minutes. Both global runs selected FIF and earnings. Do not attribute the aggregate median change to weights when it mixes exposed and unexposed work. The original predefined aggregate remains visible.

A separately labeled exploratory adjacent control window (16:50:00Z through 18:49:48Z) contains 35 runs, including 22 concluded noncancelled first attempts whose plans were screened. One exact selected/execution-proof pair was found and its old planner blob/base ancestry verified: control [39300382055](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39300382055) and weighted [39306252071](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39306252071), both 91 jobs. Neither selected a calibrated job; the control failed and the weighted run succeeded. This is **not a valid estimate of calibration speedup**. It neither replaces the original baseline nor relaxes proof matching. Other selected-set matches differ in command/step definitions, including the always-on research-factory authority battery.

The successful tail [39311574352](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39311574352) selected 159 jobs after a 476-file change with 27 selected job definitions changed. Its critical pack 6 took 3610 seconds: 377 seconds checkout and 3205 seconds execution wrapper. Planner-to-pack and last-pack-to-gate intervals were only 2 and 3 seconds. A different failed run's critical checkout took 1993 seconds. This variability does not support more runners as a general remedy. The first full-log acquisition failed with a transport stream cancellation; one same-carrier read at the next eligible integration boundary recovered it, without a CI rerun or reader bypass.

The naturally occurring global success [39309256542](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39309256542) covered 258 jobs in 2517 seconds and 373.43 summed wall minutes. Its complete command groups include FIF 1989.85 seconds, control-plane 1269.95, earnings 779.43 and nw-lobe 681.92. The last pack spent 479 seconds checking out and 1918 seconds in the execution wrapper. Together with the earlier successful weighted trial, this confirms a substantial indivisible FIF floor and material checkout variation; it does not establish a fleet p95 gain or justify changing shard count.

**Decision:** keep twelve packs and the two bounded estimates. The 30% p95 target and cost neutrality remain unproven. Trial the exact-ancestry reuse fix below, keeping all identity checks and fallback behavior; retain failures, pending observations, cancellations and source differences. Do not broaden shards or turn an exploratory comparison into a causal claim.

## Third bounded slice: preserve already-complete exact ancestry

The tail's complete log contains only **1525.04 seconds of logical command groups** inside its 3205-second execution wrapper. Two intervals from the notice “ancestry incomplete at depth 8; deepening to 32” to the next fetch response took **691.30 and 725.67 seconds**, both for tested tree `f1608086524cc8e494d8df1b8b1a8a738561d0c6`. They precede the `signal-gate-pair-coherence` and `ruling-graph` consumers. These are observed elapsed intervals, including Git transport/client work, not CPU or invoiced cost.

`_prepare_provided_actions` unconditionally begins at depth2 for each fetch-depth-zero consumer. A later invocation can therefore make already-complete history shallow again and repeat the2/8/32 acquisition. The bounded change checks the existing `_tested_tree_ancestry_ready` predicate **before** fetching. It rechecks the current repository and exact tested SHA on every invocation; there is no process-wide cache. If incomplete, every existing bounded-fetch and legacy recovery step remains. Trusted Git environment, replacement-object refusal, exact tree/parent/merge-base checks, isolated base replay, commands, semantic proofs and twelve-pack assignment remain intact. A notice records when local ancestry satisfies the contract.

A real local Git regression builds a two-parent merge with divergent20-commit histories and two independent shallow clones. Original source fetches three extra times for the second consumer and fails the regression. The candidate retains complete ancestry without a second fetch, while the separate shallow clone must still fetch and prove its own ancestry. All nine fetch/recovery tests pass. The proof/authority corpus passed199 tests; its one mock assuming unconditional fetch was corrected to model missing-then-ready ancestry, and that remaining test passed independently. Manifest validation passes for329 legacy jobs across both gate classes. All runs retain42 inherited pytest temporary-directory cleanup warnings. Hosted normal CI remains the release gate.

The first deepening may be necessary; the two intervals must not both be advertised as savings. Intervening job commands can change local ancestry, in which case the new precheck correctly falls through. The hosted trial must show actual reuse and cost before claiming a fleet improvement. Rollback is a normal revert of this precheck and its notice, with no cache, configuration or runtime state to unwind.


## Exact-ancestry trial landed with hosted reuse

[PR9791](https://github.com/mastermindx-market-intelligence/macro/pull/9791) merged at **2026-10-19T21:52:31Z** as `c3c67487f42e1c54986b2e95dca327946fdc5ed0`. [Run39324251115](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39324251115) passed all **258 logical jobs / 554 semantic proof units**, with zero infrastructure findings and all active authority/fence checks. All eight intended source, test and report blobs match the landed commit. `ancestry-success-result.json` retains exact plan, source and stage identities.

The hosted runner emitted **one** `exact tested-tree ancestry already complete; retaining local history` notice before `ruling-graph` in pack10. Five other consumers still deepened incomplete history from depth2 to8. This demonstrates both real reuse and continued recovery when needed. It does not measure the counterfactual cost of the skipped fetch, nor prove that the historical 726-second interval was saved here.

The full trial took **2527 seconds / 42.12 minutes** from run creation to gate, **362.57 summed job wall minutes**, and **3 seconds** from last pack completion to gate start. Pack checkout totaled2945 seconds; command groups totaled15075.19 seconds;177 dependency-install groups totaled1679.59 seconds. FIF alone was critical: pack0 took2396 seconds, including229 seconds checkout and2120.20 seconds of commands. Pack5 followed at2379 seconds. The ancestry reuse occurred in noncritical pack10 (1837 seconds), so this observation does not establish an end-to-end benefit from reuse.

Compared with natural global run39309256542, both select258 jobs, but FIF, prelaunch-hardening and research-vault have changed execution definitions. Compared with the previous successful weighted full trial, the selected population also changed. The apparent latency decrease is descriptive, not a causal gain or cost-neutrality proof. Keep twelve packs and both calibrated weights; no further source expansion is justified yet.

The next natural cohort starts at this merge, requires tested planner blob `f92be10fc37455fd427829f0f964c5ef581b3a80` and base ancestry from the merge, and remains separate from the prior weighted cohort. At21:54Z one first-attempt run was in progress and none had completed. Preserve exact selected/execution-proof matching and pending/failure/cancellation strata. Batch its comparison with this result when informative; do not create a report PR for each wake.


## First natural ancestry cohort: real reuse, no matched gain estimate

At **2026-10-19T23:56Z**,29 post-merge first attempts comprise **12 successful completions,13 pending and4 cancelled**; no reruns or completed failures. All12 completed runs verify the exact planner blob and merge ancestry. The previously missing metadata for run39332378137 is now retained. `ancestry-natural-comparison.json` includes the rows, exposure/critical-stage summaries and source/matching limitations.

| Metric | Original scoped successes | Ancestry scoped successes |
| --- | ---: | ---: |
| N | 14 | 11 |
| Run-to-gate p50 / p95 | 54.43 / 67.90 min | 33.02 / 47.72 min |
| Summed job wall p50 / p95 | 223.02 / 257.63 min | 196.25 / 278.23 min |

The sole global success39336503626 took52.17 minutes and329.15 summed job wall minutes for258 jobs. There are no completed failures from which to estimate actionable-red latency. Thirteen pending observations can materially change the tail; atN11 nearest-rank p95 is simply the largest scoped success. These different-work summaries prove neither the30% target nor cost neutrality.

One scoped selected-set match exists: run39341997524 and original control39235580372 both select105 jobs, but `dataos-identity-seams` and `research-factory-authority` execution definitions differ. There are **zero full execution-proof matches** to the original baseline or the retained19 weighted completions. The global run shares a selected set with two weighted observations but also lacks a full proof match. Do not relax these identities to manufacture a causal estimate.

Eight of12 plans put multiple fetch-depth-zero consumers in one pack; in only two runs does such a pack finish last (39336610321 and39333873303). This is potential exposure, not evidence of reuse. The inspected natural log for [39330880213](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39330880213) actually shows five incomplete-history deepening notices and one retained-history notice in pack8. Its critical pack11 has no such consumer and takes1588 seconds including217 seconds checkout and1349 seconds wrapper execution. Actual reuse therefore does not establish end-to-end latency savings in this observation.

**Decision:** publish the landed trial and this first natural comparison as one batch. Retain twelve packs, the two calibrated weights and the exact ancestry precheck. Before considering another implementation slice, inspect the two naturally exposed critical packs and extend the same cohort, preserving pending/cancelled/failure strata. Do not rerun CI, broaden shards or claim a causal improvement from an unmatched p95.


## Fixed31-completion snapshot and critical-path reuse

Report [PR9801](https://github.com/mastermindx-market-intelligence/macro/pull/9801) merged at2026-10-20T00:22:12Z as `368c4c3a660215a0bf4809c9b8ff5e65098f413a`; all active checks passed and all six report blobs match the candidate. The new00:55Z snapshot is held fixed for failure classification rather than continually moving the observation window. It contains45 discovered runs:31 eligible first-attempt completions (29successes,2failures),7pending,7cancelled. All31 satisfy the exact implementation blob and base-ancestry checks.

Scoped successes N27 have run-to-gate p50/p951966/2863 seconds (32.77/47.72 minutes) and summed job wall186.47/278.23 minutes. Two scoped failures have first-failed-step completion p50/p951435.5/1564 seconds; their run-to-gate range is2681–2751 seconds and summed wall range262.35–274.88 minutes. Two global successes have run-to-gate p50/p952873/3130 seconds and summed wall318.22/329.15 minutes. Excluding this commission's report run leaves scoped-success N26 p50/p951969.5/2863 seconds and wall188.52/278.23 minutes. These remain different-work descriptive metrics with seven pending observations; no causal gain or cost neutrality is established.

There is one original-baseline selected-set match and four selected-set matches to the retained weighted cohort, but **zero full execution-proof matches to either**. Run39342972042 (PR9479,pack11) fails biocatalyst-deploy-integration on missing API-import/schema restart coverage; isolated base replay passes289 tests and the semantic gate classifies pr_regression. Run39342630438 (PR9797,pack4) fails market-memory-e0-contract with unsafe_metadata_ancestor in an installed allocator-byte test; isolated base replay passes505 tests and the semantic gate classifies pr_ci_contract_change. Both full logs are retained. These are candidate-specific failures on existing carriers, not observed ancestry-precheck failures; no duplicate repair or rerun was introduced.

The two targeted natural logs now confirm actual reuse in critical packs, beyond potential plan exposure. Run39336610321 reuses complete ancestry in critical pack5 and noncritical pack8; critical commands total635.75 seconds, installs103.17, checkout197, wrapper781. Run39333873303 reuses ancestry in critical pack9; commands1622.43 seconds, installs175.35, checkout205, wrapper2039. Its largest command groups are government-revenue candidate projection586.43 seconds, dashboard rendering434.58 and signal-gate-pair coherence204.52. Neither log supplies the counterfactual fetch cost, so no saved-seconds estimate is assigned.

Across31 completions, the last-finishing pack contains FIF alone in9 runs, control-plane contracts alone in8, and mixed jobs in14. Nineteen plans co-locate ancestry consumers; only three do so in the critical pack, including this commission's report run. This supports rejecting speculative outer-shard expansion: it cannot shorten those17 single-job critical paths. Keep the current implementation. Failure classification is complete. The next justified work is exact-source localization and bounded profiling of the dominant FIF interval, preserving its active writers and full test/proof contracts; no split or optimization is authorized by the progress timestamps alone. Do not rerun CI or expand the cohort merely to find a favorable match.

The six slowest scoped successes all finish on FIF alone, with2187–2346-second execution wrappers,195–307-second checkout and2–3-second final-gate wait. The existing full-trial log places760.67 seconds between67% and71% pytest progress (ordinals1441–1512 under that run's output). This is a bounded localization lead, not per-test timing: exact collection order and source identity must be bound before attributing cost or proposing a fix. Active FIF mapping/coverage carriers9761,9794 and9799 are preserved; no competing source edit was made.


## Fourth trial: avoid repeated parser scans inside FIF

The exact-source 72-test interval passed locally in 403.73 seconds. Its slowest publisher case took 42.37 seconds. A focused cProfile run of that case passed and recorded 52 SEC parses consuming 60.24 cumulative seconds, including profiler overhead. It exposed 67.5 million Python generator calls for ASCII validation and 36,618 direct-text calls scanning entire event streams. These overlapping profiler totals are a localization tool, not hosted timing.

The candidate makes two small changes in the existing parser: `bytes.isascii()` replaces the equivalent per-byte predicate, and `_direct_text` uses the existing source-order bisect index before retaining the same owner-identity filter. Direct excluded text is still included; nested text is still distinguished from direct text. Plain-list callers keep their old scan. Limits, refusal conditions, source spans, parsed-output schema/version, producer state, and CI proof/selection/sharding contracts remain unchanged. The known active FIF carriers #9761, #9794 and #9799 do not touch these parser paths and retain their source ownership.

All 214 parser tests pass. A new mixed-content regression covers multibyte text, entity expansion, CDATA, comments, nested/excluded text, empty elements, and unrelated siblings; it fails against the original full-stream scan. The publisher differential run exercised 52 parses of two distinct large filing documents and produced identical complete outputs. Three alternating local samples of those two parses plus canonical output serialization reduced median CPU time from 0.8960 to 0.6836 seconds (23.7%); wall time was 0.9044 versus 0.6890 seconds. The unprofiled publisher case passed in 29.41 seconds versus the earlier 42.37 seconds, a single-case descriptive comparison.

The same 72 tests pass after the change in 335.45 seconds versus 403.73 seconds before (16.9% lower); the slowest case in the group is 31.17 seconds. Both runs retain 42 inherited pytest cleanup warnings. This is one local before/after observation, with no controlled fleet estimate. The local evidence alone did not establish hosted proof. `parser-trial.json` retains identities, full-output hashes, benchmark samples and limitations. No fleet p95, cost-neutrality, or 30% mission-target claim follows from these local results. Rollback is a normal source revert of the two parser optimizations; there is no cache, stored state or runtime configuration to unwind.


## Parser trial landed; hosted variation remains material

[PR9813](https://github.com/mastermindx-market-intelligence/macro/pull/9813) merged at **2026-10-20T04:57:13Z** as `9c7df3786fc3856fbb692da301584b4b443ab66d`. All seven intended source/test/report blobs match fresh main. Final [run39364786931](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39364786931) passed **96 selected logical jobs / 299 semantic proof units**, with zero infrastructure findings and all active authority/fence checks. The tested tree, base, head, plan and evidence digests are retained in `parser-trial.json`. Twelve packs and the two calibrated weights remain unchanged.

Two GitHub main refreshes triggered normal replacement proof runs while all seven trial blobs remained identical. No artificial CI was dispatched. FIF's four command groups took **1581.75, 2093.14 and 1573.07 seconds** across the three successful runs. The final primary suite passed2681 tests with1skip in1552.58 seconds. The three runs took34.45,42.68 and34.55 minutes to gate, with225.78,225.90 and222.45 summed job-wall minutes and2-second final gate waits. The final critical pack0 spent220 seconds in checkout and1593 seconds in its execution wrapper (1838 seconds total job wall time). These are individual trial observations, not a fleet comparison. The59 intervening main paths and changing shared/transitive inputs prevent treating repeated command text and test counts as a controlled experiment. The prior ancestry trial also had560 fewer primary tests and no later G-pack command.

**Decision:** retain the bounded parser optimization on its equivalence and correctness evidence, without claiming a causal hosted gain, cost neutrality or the30% p95 target. Collect a separate natural cohort after the parser merge with both exact parser and planner blobs and base ancestry verified. The earlier00:55 cohort remains fixed. Batch the post-merge comparison into this report when it is informative; do not increase shards or select another optimization merely because local CPU improved. Rollback remains a normal revert of the parser optimization and its regression test.


### Initial parser natural cohort: failure mechanisms remain visible

The05:54Z snapshot contains16 natural first-attempt runs after the parser merge: three successes, two failures and eleven pending. All five completions satisfy both exact parser/planner blobs and base ancestry. The successes took1716,2218 and1860 seconds to gate, with163.02,252.18 and228.50 summed job-wall minutes respectively. Only one of these three selected FIF; all three selected collector-registry. These are sparse, differently scoped observations, not a fleet benefit estimate.

Failed [39374315686](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39374315686), PR9216, matches the94 selected jobs and full execution-proof definition signature of pre-parser success39341912215. Its FIF suite passed2681 tests with1skip in1514.96 seconds, but pack6 failed to upload its semantic artifact after GitHub ArtifactService request timeouts. The retained full log has no final reconciled semantic verdict. A passed suite is not complete CI proof; retain this as a failed infrastructure observation, not a successful speed comparison or evidence of a parser regression.

Failed [39372741047](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39372741047), PR9831, selects only three jobs and does not select FIF or collector-registry. Candidate AgentOS validation rejected a discovery falsifier lacking a runnable token. Exact-base replay then failed a different Git-derived-date assertion. The authoritative verdict remains `unknown` for that proof unit because head and base failure signatures differ; five other units passed. Its exact selected/execution-proof match to weighted success39317389150 is unexposed to the parser and uses a different planner version. The existing PR9831 carrier has already advanced beyond the observed failed head; no duplicate repair was made. Zero completed runs in this initial snapshot match the original baseline's full proof signature.

The completed fixed snapshot is retained in `parser-natural-comparison.json`. Scoped success N=3 has run-to-gate p50/p95 **1860/2218 seconds** and summed job-wall p50/p95 **228.50/252.18 minutes**. Scoped failure N=2 has failed-step-completion p50/p95 **950.5/1002 seconds**, run-to-gate **1458/2000 seconds**, and summed job-wall **117.63/201.85 minutes**. The failed-step proxy can include base replay; it is not the timestamp when the first log error appeared. Nearest-rank p95 at these sample sizes is simply the maximum.

Metadata confirms that both failed runs reached a failing `ci-gate`; PR9216's failing pack step is semantic-fragment publication. The historical scoped-success baseline N=14 has3265.5/4074-second p50/p95 and223.02/257.63 summed wall minutes, but none of the five treated completions matches its complete execution-proof set. These different-work figures are descriptive, with11pending observations retained at the fixed cutoff,0cancellations and0reruns. No global observation is available. Do not interpret the numerical contrast as causal improvement or cost neutrality.

**Acceptance decision:** the parser source trial is merged with complete hosted correctness proof; the throughput claim is still unproven. Keep twelve packs and the two calibrated weights. The next acceptance step is a bounded natural-traffic comparison with exact source, execution-proof and exposure qualification, retaining infrastructure and candidate failures. No new optimization or outer-shard expansion follows from this sample. Existing PR9216 and PR9831 retain their repair carriers; their failures are not grounds to rerun accepted implementation proof.


## Fixed second parser cohort — October20,07:54Z

Report #9850 merged as6793c010048996193d3d98876b486910c7982e3c with75 selected jobs and every active check passing; all six authored blobs match fresh main. The first parser cohort remains fixed separately. The second snapshot has57 runs:36 qualified first-attempt completions (29success,7failure),18pending and3cancelled. Both implementation blobs and base ancestry are verified for every completion. See `parser-natural-comparison-0754.json`.

Scoped successesN24 have run-to-gate p50/p951895/2553sec and summed job-wall177.675/253.95min. Global successesN5 have2723/3156sec and352.6/360.1min. Scoped failuresN7 have first failed-step-completion p50/p95578/1853sec, including replay. Pending runs remain excluded by the fixed cutoff; these completion-conditioned strata are descriptive. There are still zero original-baseline full-proof matches.

A secondary comparison now has three FIF-selected successful treatments with the same103 selected jobs, execution-proof definitions and pack assignment as ONE successful pre-parser control39346152272. That control is reused, not three independent controls. Control latency is2007sec and summed job-wall232.533min; treated runs39384839986/39378857695/39374295130 take2066/2581/2553sec and220.833/228.15/228.067min. All take longer to gate despite lower summed job-wall. The control ends onpack7; all three treatments end onFIF-alonepack0. FIF wrapper execution is1347sec control versus1616/2172/2113sec treated, while checkout is199sec versus201/197/197sec. The critical-path difference is predominantly inside execution, not checkout.

The control's retained full log reports2680 passed/1 skipped in1311.39sec and1329.857sec across four FIF commands. The three treated logs are now complete:

| Run | FIF primary test time | Four FIF commands | Primary result |
| --- | ---: | ---: | --- |
| Control39346152272 | 1311.39sec | 1329.857sec | 2680pass,1skip |
| Treated39384839986 | 1573.45sec | 1594.096sec | 2681pass,1skip |
| Treated39378857695 | 2126.72sec | 2151.041sec | 2681pass,1skip |
| Treated39374295130 | 2065.02sec | 2089.544sec | 2681pass,1skip |

All three treated runs report runner2.337.0, provisioner20261012.601, ubuntu-24.04 image20261012.334.1 and Python3.12.13. These labels do not measure physical CPU performance or contention. The primary command accounts for almost all FIF execution time; checkout and pack-wrapper overhead do not explain the difference. The extra passing test and unqualified transitive input differences prevent treating equal execution definitions as a controlled experiment. No causal speedup, cost neutrality or30percent mission target is established.

**Decision:** retain twelve packs, both calibrated weights and the accepted parser optimization. Its local equivalence and focused CPU evidence remain valid, while fleet benefit remains unproven. Reject additional outer shards as a remedy for FIF's single-job critical path. Do not infer a revert from one reused control or implement another optimization from undifferentiated suite duration. The next engineering slice requires a discriminating residual profile on qualified current source and a fresh check of active FIF repair custody; reuse the completed profiling and output-parity evidence where applicable. Source delivery of this fixed comparison is the current acceptance step, with earlier cohorts and failure carriers intact.
