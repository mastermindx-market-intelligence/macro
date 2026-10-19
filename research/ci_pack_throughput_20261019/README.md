# CI pack throughput: October 19, 2026

Commission: `/Users/chriswong/Desktop/MASTERMIND-CI-PACKS-CODEX-ASTRA-HANDOFF-2026-10-19.md`, directly assigned to Codex chat `01a153e8-3c85-7bb2-af63-7f477b570512`.
Source: Macro `168c96bf9ca68427749bc70664902c343d968d9c`; protected procedure: Mastermind `5469f12de01158b0e495d616d2be6f56c03cf8a8`, skillpack 1.0.1/bootstrap 1.

Status: **two bounded optimizations merged with full hosted proof; fleet throughput outcome not yet proven**.

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
