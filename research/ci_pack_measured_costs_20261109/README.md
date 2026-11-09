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

## Follow-up (2026-11-09, same branch): measured queue delay and the width decision

The parent adjudication (PR comment 6742621098) accepted the cost model, the
ingest tool, the exact-ceiling convention and the review receipts, and held
only the width change: narrowed lanes 7 → 12 packs buys ~26 min of *predicted*
wall for ~25 runner-minutes per narrowed PR, assuming runners are available
on demand. Live evidence said they are not. This follow-up measured the queue
for real, then re-based the width on that measurement.

### Census method

Natural runs only; nothing was dispatched, re-run or cancelled. Window
2026-11-07T14:36Z..2026-11-09T14:36Z (48 h). `gh api` reads: all 905
`ci.yml` runs in the window (890 `pull_request` — `ci.yml` has no `push`
runs in this window; main merges ride the merge-ref PR event — plus 15
other events, excluded), per-job `created_at`/`started_at`/`completed_at`
for all 10,499 jobs of those 890 runs (jobs endpoint = latest attempt);
run lists for `ci-authority.yml` (1,674 runs), `fences.yml` (1,026) and
`merge-on-green.yml` (2,122, API caps a listing at 1,000 per query; fetched
as two 24 h halves) with job-level detail from the saturation block below;
and a live snapshot at 14:36–14:37Z (macro 71 queued / 14 in-progress;
Mastermind 45 / 26; mastermind-terminal 43 / 10). Pickup = job
`started_at − created_at`; the job-level `created_at` is when the job
became pending (needs satisfied), so pickup measures runner-queue wait, not
dependency wait — idle-hour pickup p50 of 2 s confirms the reading.
Denominators accompany every number below.

### Queue delay by job class (890 ci runs, 10,499 jobs; jobs of the latest attempt)

| class | n | pickup p50 | p90 | max | share ≥300 s | share ≥600 s | exec p50/p90 |
|---|---:|---:|---:|---:|---:|---:|---|
| pack jobs (`ci-pack-*`) | 7,091 | 2 s | 430 s | 2,084 s | 14% | 7% | 1,224 / 3,176 s |
| small controls (`ci-plan`, `contract-delta`, `ci-admission`) | 1,724 | 2 s | 274 s | 2,379 s | 9% | 6% | 283 / 908 s |

Regime split (pack jobs): **saturated hours** 2026-11-09T01–14Z — n=1,926,
p50 160 s / p90 965 s; **idle hours** 2026-11-08T02–13Z — n=1,634, p50 2 s
/ p90 3 s. The fleet is bimodal: genuinely on demand overnight, deeply
backlogged through the working day.

Control jobs inside the saturated block 04:00–14:00Z (job-level, all macro
workflows): `ci-authority` n=406 p50 345 s / p90 1,314 s / max 2,588 s
(54% ≥5 min, 29% ≥10 min); `ci-plan` n=174 171/1,164/2,379;
`contract-delta` n=174 179/1,164/1,846; `fence-pack` n=194 96/1,123/1,767;
MOG `sweep` n=375 0/519/1,736. Every job in the census ran on the hosted
`GitHub Actions` runner group (n=9,249 with a group set); the org's 8
self-hosted runners (m1-light-1, m1-nightly-1/2, pc-ci-1..4, pc-render-1)
are not in these jobs' graphs.

Pickup by hour (UTC, bucketed on job `created_at`), pack and small classes:

| hour (UTC) | pack n | pack p50/p90/max | small n | small p50/p90/max |
|---|---:|---|---:|---|
| 11-07T14 | 48 | 2/103/152 | 8 | 2/39/39 |
| 11-07T15 | 111 | 259/673/1062 | 21 | 130/193/371 |
| 11-07T16 | 150 | 3/167/253 | 30 | 2/55/127 |
| 11-07T17 | 214 | 3/181/322 | 40 | 2/63/161 |
| 11-07T18 | 132 | 212/718/1388 | 21 | 90/215/614 |
| 11-07T19 | 72 | 260/747/964 | 10 | 98/224/278 |
| 11-07T20 | 205 | 4/355/774 | 40 | 2/111/283 |
| 11-07T21 | 131 | 21/153/208 | 28 | 14/97/135 |
| 11-07T22 | 159 | 65/687/971 | 26 | 3/52/65 |
| 11-07T23 | 246 | 2/186/504 | 44 | 2/2/68 |
| 11-08T00 | 168 | 2/392/592 | 28 | 2/2/65 |
| 11-08T01 | 210 | 2/277/501 | 40 | 2/35/119 |
| 11-08T02 | 198 | 2/3/36 | 40 | 2/3/20 |
| 11-08T03 | 111 | 2/3/7 | 36 | 2/2/3 |
| 11-08T04 | 155 | 2/3/12 | 35 | 2/2/3 |
| 11-08T05 | 155 | 2/3/3 | 40 | 2/2/3 |
| 11-08T06 | 111 | 2/2/3 | 30 | 2/2/2 |
| 11-08T07 | 171 | 2/3/7 | 41 | 2/2/3 |
| 11-08T08 | 113 | 2/3/3 | 34 | 2/2/5 |
| 11-08T09 | 106 | 2/2/3 | 35 | 2/2/2 |
| 11-08T10 | 140 | 2/80/140 | 42 | 2/2/92 |
| 11-08T11 | 104 | 2/3/10 | 28 | 2/2/4 |
| 11-08T12 | 128 | 2/2/3 | 37 | 2/3/3 |
| 11-08T13 | 142 | 2/2/48 | 32 | 2/15/73 |
| 11-08T14 | 210 | 10/212/364 | 40 | 16/114/139 |
| 11-08T15 | 118 | 2/19/129 | 30 | 2/2/3 |
| 11-08T16 | 138 | 2/2/3 | 42 | 2/2/7 |
| 11-08T17 | 131 | 2/2/3 | 32 | 2/2/2 |
| 11-08T18 | 140 | 2/2/3 | 44 | 2/2/3 |
| 11-08T19 | 146 | 2/17/75 | 50 | 2/3/47 |
| 11-08T20 | 187 | 2/93/219 | 44 | 2/2/49 |
| 11-08T21 | 118 | 2/3/15 | 32 | 2/2/3 |
| 11-08T22 | 196 | 2/3/44 | 50 | 2/2/3 |
| 11-08T23 | 113 | 2/3/69 | 26 | 2/2/3 |
| 11-09T00 | 188 | 2/73/281 | 48 | 2/3/38 |
| 11-09T01 | 248 | 14/290/609 | 58 | 13/110/250 |
| 11-09T02 | 197 | 300/1002/1324 | 48 | 121/339/575 |
| 11-09T03 | 148 | 279/652/873 | 40 | 97/285/491 |
| 11-09T04 | 145 | 324/839/1211 | 28 | 323/537/734 |
| 11-09T05 | 89 | 71/515/723 | 24 | 133/513/630 |
| 11-09T06 | 139 | 38/323/725 | 40 | 26/138/187 |
| 11-09T07 | 123 | 278/711/1055 | 36 | 98/428/520 |
| 11-09T08 | 166 | 2/347/823 | 44 | 2/172/315 |
| 11-09T09 | 193 | 318/859/1451 | 43 | 127/370/780 |
| 11-09T10 | 80 | 409/741/993 | 18 | 294/514/667 |
| 11-09T11 | 79 | 679/1718/2084 | 39 | 822/1433/1513 |
| 11-09T12 | 129 | 1024/1666/2004 | 30 | 840/1212/1318 |
| 11-09T13 | 88 | 811/1676/1991 | 44 | 1125/1636/2379 |
| 11-09T14 | 102 | 0/1346/1891 | 28 | 0/1686/1871 |

### Fleet saturation (reconstruction, 06:00–14:00Z Nov 9)

From per-job intervals of every run created 04:00–14:00Z across the org's
three repos (macro 1,236 runs incl. a separately fetched 04–06Z piece;
Mastermind 1,000; mastermind-terminal 848; 11,756 jobs with created+started;
macro's 04–06Z remainder beyond the 1,000-run API cap was fetched whole, so
06–14Z is complete for runs created from 04Z):

- concurrent in-progress hosted jobs: p50 183 / p90 211 / max 237
- queued jobs waiting for a runner: p50 108 / p90 293 / max 338
- demand (in-progress + queued): p50 296 / max 551

Hourly (in-progress p50/max, queued p50/max): 06h 178/180, 18/53 · 07h
179/181, 48/98 · 08h 173/184, 2/82 · 09h 185/204, 93/143 · 10h 183/201,
118/145 · 11h 188/225, 229/290 · 12h 203/225, 256/338 · 13h 201/237,
289/332. The hosted pool sustains ~180–210 concurrent jobs and no more;
from 11Z the backlog is 230–330+ deep. Undercount is possible for runs
created before 04Z still running in-window; the bias is downward, i.e.
saturation is if anything understated.

### The on-demand assumption, tested directly

Within-run pack START spread (time between a run's first and last pack
job starting; runs with ≥4 started pack jobs):

- idle hours (Nov 8 02–13Z): n=169 runs, p50 1 s / p90 1 s — packs start
  together; the on-demand model holds.
- saturated hours (Nov 9 01–14Z): n=220 runs, p50 274 s / p90 971 s /
  max 39,790 s — a wide lane's extra packs queue behind other work, so the
  predicted wall saving of width does not materialize when the org is
  busiest.

### Width decision

Policy: **a narrowed PR lane activates at most 7 packs — the legacy width —
and measured seconds balance those packs** (`NARROWED_PR_MAX_ACTIVE_PACKS`).
Same population (the three probe selections, 137/137/131 jobs, weights
14,099/14,575/13,380 s), three configurations, walls via
`predicted_pack_walls_seconds` (setup + measured seconds):

| lane | config | packs | predicted wall | runner-total | queue-adj. wall (saturated*) |
|---|---|---:|---:|---:|---:|
| templates/index.html | legacy model | 7 | 3,092 s | 16,220 s | 4,109 s |
| templates/index.html | PR as pushed (12) | 12 | 1,482 s | 17,735 s | 2,717 s |
| templates/index.html | **adopted (7)** | 7 | 2,319 s | 16,220 s | 3,336 s |
| scripts/build_free_content.py | legacy model | 7 | 2,745 s | 16,696 s | 3,762 s |
| scripts/build_free_content.py | PR as pushed (12) | 12 | 1,521 s | 18,211 s | 2,756 s |
| scripts/build_free_content.py | **adopted (7)** | 7 | 2,389 s | 16,696 s | 3,406 s |
| engine/prophet/plan_book.py | legacy model | 7 | 2,921 s | 16,001 s | 3,938 s |
| engine/prophet/plan_book.py | PR as pushed (12) | 12 | 1,461 s | 17,516 s | 2,696 s |
| engine/prophet/plan_book.py | **adopted (7)** | 7 | 2,290 s | 16,001 s | 3,307 s |

\* optimistic for wide lanes: predicted wall + bootstrap E[max pickup of P
packs] from the saturated-hour pool (P=7: 1,017 s; P=12: 1,235 s; 4,000
draws), treating pickups as independent. Even under that optimism the 12-pack
edge shrinks from the claimed ~26 min to ~10 min in the saturated regime —
and the start-spread evidence above says it is smaller still, because the
extra packs' pickups are not independent: they serialize behind the same
backlog.

Why 7 wins:

1. **Runner-minutes never grow** (the adjudication's criterion): the 12-pack
   lane spends +1,515 s (5 × 303 s setup ≈ 25.3 min) per narrowed PR — pure
   overhead executing no tests — versus identical-to-legacy totals
   (16,220/16,696/16,001 s) at 7.
2. **The wall benefit is regime-dependent and mostly evaporates**: idle, 12
   packs would save 808–870 s; saturated (13+ of 48 observed hours, both
   snapshot times, and worsening at census close), pack starts serialize
   (spread p90 971 s) and first pickup alone is p50 160 / p90 965 s.
3. **It taxes every other author**: +5 packs × (303 s + exec) of demand into
   a fleet pinned at ~200 concurrent with a 230–330 backlog deepens
   everyone's queue; small controls were already waiting p90 ~20 min.
4. **The accepted model still pays**: measured balancing within the legacy
   seven cuts the probe critical paths 3,092/2,745/2,921 → 2,319/2,389/2,290 s
   (−12–21%) at zero additional runner-minutes.

Full manifest (main baseline): unchanged — twelve named packs, max wall
5,496 s, fif-bound (PR #10788 owns the split). The narrowed-lane plan
document still describes all twelve fleet packs; only the active count and
matrix obey the budget. Alternatives rejected: adaptive width (a new
admission system, out of scope by the adjudication); fewer than 7 (saves
runner-minutes but lengthens the lane's wall past the legacy lane's on
every regime, for a shared fleet saving of at most 5 min per PR);
width-by-admission-capacity (the twelve-pack fleet cap alone reproduces the
rejected 12).

### Implementation of the follow-up

- `scripts/run_ci_pack.py`: `NARROWED_PR_MAX_ACTIVE_PACKS = 7`;
  `build_plan`'s narrowed lane compacts under `min(pack_count, 7)` and pads
  the document back to the fleet's twelve slots;
  `packing_probe_measurements`' packs axis mirrors the grant
  (`min(NARROWED_PR_MAX_ACTIVE_PACKS, ceil(weight/600))`).
- `tests/test_ci_pack.py`: `PACKING_PROBE_MAX_PACKS` 12 → 7 (exact measured
  value of the new axis: all three probes read 7); provenance updated; job
  and weight ceilings unchanged.
- `scripts/check_contract_delta.py`: the base-worker bootstrap fallback
  mirrors the new axis with `getattr(pack, "NARROWED_PR_MAX_ACTIVE_PACKS",
  12)` so pre-budget bases keep their historical twelve-pack cap.
- `tests/test_ci_pack_measured_costs.py`: +3 tests (lane holds the budget
  through `build_plan` with no lost/duplicated jobs; capped lane never
  exceeds the uncapped lane's runner-seconds; probe packs axis mirrors the
  grant and still follows demand below it).
- `tests/test_contract_delta.py`: bootstrap parity re-based (7), plus the
  pre-budget base pinned at the historical 12.

### Sampling limits

48 h ending 2026-11-09T14:36Z; one org, three repos, hosted `ubuntu-latest`
jobs. Pickup is from the latest attempt's jobs; re-runs of a run replace
earlier attempts (unstarted jobs at fetch time: 0). The by-hour buckets are
by job `created_at`; hours with few jobs (e.g. 11-09T10 small n=18) are
correspondingly noisy. The saturation reconstruction sees only runs created
from 04Z (downward bias stated above). `merge-on-green.yml` run counts are
2,122 over 48 h; its `sweep` pickup here is the 04–14Z block only. Run-level
`run_started_at` proved unusable for control-workflow pickup (set at run
creation); control numbers above are job-level. No conclusions rest on any
single hour; the regime split is stable across the whole window.
