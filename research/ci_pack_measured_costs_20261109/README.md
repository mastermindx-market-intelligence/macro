# CI pack measured costs: November 9, 2026

Commission: Mastermind CI Lightning (Macro #6351, Mastermind #1607), lane B —
GLM 5.3 sub-orchestrator; Opus parent owns integration, review adjudication,
release and acceptance. This receipt is the migration record for the pack
planner's cost model moving from the mixed heuristic scale to measured
seconds. Machine-readable data: `analysis.json`.

## What changed

Before: `_job_weight` returned hosted seconds for ~30 hand-entered dominators
(`OBSERVED_COMMAND_SECONDS`) and text-shape "units" for every other job — two
scales mixed into one balancing input, so the planner could not see that
1,412 modeled units once executed 5,038 hosted seconds.

After: balancing weights are **conservative observed seconds** from
`.github/ci/measured-job-seconds.json` (committed table, SCHEMA 1), consumed
by an estimator with a freshness window (120 days), upper-tail policy (max
fresh sample of test + dependency-install) and 10% headroom. Jobs without a
fresh sample plan at `UNOBSERVED_JOB_COST_SECONDS = 150` — just above the
measured p90 (128.8 s) — never at the legacy 1-unit floor. Per-pack setup is
modeled separately (`PACK_SETUP_OVERHEAD_SECONDS = 303`, the measured median
non-execution share) because every pack pays it once regardless of grouping:
it belongs to wall prediction, not balancing. Weights never gate selection
or proof; they only balance grouping.

The table is written only by `scripts/update_measured_job_seconds.py`
(fail-closed on unknown artifact shape; merges by run identity; 180-day
sample retention; byte-deterministic output). The first table carries 341
jobs: 325 natural samples from run 42559449303 plus the frozen
`OBSERVED_COMMAND_SECONDS` values seeded as dated legacy samples so 16
data-gated heavyweights (engine-render-guards 875 s et al.) keep their known
costs; 59 of 400 manifest jobs remain at the bound.

## Measurement provenance

Natural run [42559449303](https://github.com/mastermindx-market-intelligence/macro/actions/runs/42559449303)
attempt 1 (ci.yml), observed 2026-11-08; the twelve per-pack
`ci-pack-timing-42559449303-1-*` JSONL artifacts (ids 13652118354 /
13652121837), one `{logical_job_id, phase, status, duration_ns}` record per
logical job and phase. No synthetic traffic was dispatched. Downloads are
untrusted data: parsed only, never executed.

Per-pack table (test_s / dep_s deduplicated to max per job and phase):

| pack | jobs | test_s | dep_s | wall_s | non-exec_s |
|---:|---:|---:|---:|---:|---:|
| 0 | 1 | 4700.5 | 20.2 | 5026 | 305 |
| 1 | 1 | 731.7 | 4.0 | 1049 | 313 |
| 2 | 1 | 543.4 | 2.9 | 870 | 324 |
| 3 | 30 | 688.4 | 162.2 | 1148 | 297 |
| 4 | 36 | 1286.8 | 261.3 | 1804 | 256 |
| 5 | 35 | 1994.2 | 298.7 | 2683 | 390 |
| 6 | 36 | 1859.3 | 366.6 | 2529 | 303 |
| 7 | 37 | 1809.2 | 325.4 | 2329 | 194 |
| 8 | 37 | 1727.4 | 245.1 | 2266 | 294 |
| 9 | 37 | 1214.8 | 248.7 | 1679 | 215 |
| 10 | 37 | 1503.2 | 292.9 | 2143 | 347 |
| 11 | 37 | 2059.6 | 279.2 | 2641 | 302 |

Per-job test distribution (n=325, nearest rank): min 1.3 / p50 9.0 / p75 33.8
/ p85 75.3 / p90 128.8 / p95 258.5 / max 4700.5. Totals: 20,118.6 test-s and
2,507.1 dep-s; 226 jobs have a dependency-install observation. Non-execution
share per pack (queue, checkout, setup-python, wrapper, teardown): min 194 /
median 303 / max 390 / mean 295.1.

## The fif tail is not a grouping problem

Pack 0 ran `fif-kernel-guards` alone at 4,700.5 test-s: one logical job,
`scope: exclusive`, whose "FIF kernel suites (class A, hermetic)" step is a
single pytest invocation over an explicit list of 120 test files, plus three
further suites/steps. The timing phase wraps the whole command list, so the
planner sees one indivisible ~4.7 ks item; no grouping can balance it.
Splitting that job is a manifest change owned by the LIVE fif-split carrier
(PR #10788), not this lane. Under either cost model the full-manifest max
wall stays 5,496 s for exactly this reason.

## Before / after (same workloads, both groupings evaluated in measured seconds)

Full 400-job manifest: the frozen-estimator grouping leaves non-fif packs at
2,606–4,538 s (1,932 s spread); the measured grouping lands them at
3,352–3,355 s (3 s spread). Max wall 5,496 s both — fif-bound.

Narrowed PR lanes (partition + scoped compaction):

| probe (jobs) | legacy: packs / max wall / runner-min | measured: packs / max wall / runner-min |
|---|---|---|
| templates/index.html (143) | 7 / 3117 s / 275.8 | 12 / 1507 s / 301.0 |
| scripts/build_free_content.py (144) | 7 / 2863 s / 286.2 | 12 / 1558 s / 311.4 |
| engine/prophet/plan_book.py (138) | 7 / 3073 s / 274.6 | 12 / 1504 s / 299.9 |

Time-to-green critical path drops 46–52%; total runner-minutes rise ~9%.
That trade is the point: the old model's fake-small weights collapsed
narrowed lanes into too few packs, serializing real seconds behind one
runner.

## Contract migration (PACKING_PROBES)

Job ceilings unchanged (137 / 138 / 131 — selection is untouched). The
weight axis changed scale; new ceilings are the exact
`packing_probe_measurements` outputs on this source: 14,099 / 14,575 /
13,880. `PACKING_PROBE_MAX_PACKS` moves 10 → 12: under true seconds these
selections need twelve 600 s packs, so the packs axis now saturates at the
fleet cap and the weight axis carries growth sensitivity. Full history:
`tests/test_ci_pack.py` provenance paragraphs.

## Guards

Replay parity over the real manifest (tests/test_ci_pack_measured_costs.py,
14 tests): no lost or duplicated logical jobs or commands, per-job proof-id
uniqueness, identical semantic digests, unchanged dependency/venv surface,
main baseline keeps all twelve named packs and plan fields, and the measured
grouping never lengthens the predicted critical-path wall. The legacy
estimator is frozen in `_legacy_heuristic_weight` for exactly this test.
