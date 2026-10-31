# GLT T23 — operational cost of the bounded nightly refresh

Task T23 (WS:GLOBAL-LIQUIDITY-TRANSMISSION), lane H2, 2026-10-17. The builder
`scripts/build_global_liquidity_transmission.py` now runs atomically, is
idempotent, refuses stale or backdated promotion with a visible receipt, and
bounds `--asof` replay so stored history can never be rewritten. This note
measures what that costs on the render budget and records how to read it.

## Measured cost (two consecutive runs, full tree, real data)

`/usr/bin/time -v` on the lane venv, tree `e38026e9f4e` + T23 changes:

1. First run — outcome `written` (inputs had moved since the nightly):
   wall clock 1.01 s, CPU 2.86 user + 0.05 sys (multi-core import/compile),
   max RSS 136,012 kB (≈132.8 MiB), 376 blocks written, exit 0.
   Receipt: `::notice title=glt-nightly::asof=2026-10-09
   source_snapshot_hash=7911bcab…9dc6ee first_known_at=2026-10-16T18:16:51.754201Z
   wall_s=0.81 outcome=written`.
2. Second run, same command — outcome `unchanged` (equal asof + snapshot
   hash): wall clock 1.01 s, CPU 2.88 user + 0.11 sys, max RSS 135,248 kB
   (≈132.1 MiB), **0 blocks written** (nothing touched, mtimes preserved),
   exit 0.

Artifact sizes after a written run: contract
`site/liquiditydata/global_liquidity_transmission.json` 31,185 B; history
`data/global_liquidity_transmission/state_history.parquet` 146,249 B; history
meta 2,266 B; frozen comparison 7,154 B.

Render budget is ≈67 min (4,020 s). A 1.01 s step is **0.025 %** of it. For
scale, the T06 receipt (research/GLOBAL_LIQUIDITY_TRANSMISSION_LIVENESS_2026-10-13.md,
§4) measured `2.54 s real (1.92 user, 0.17 sys), max RSS 142,491,648 B (≈136 MiB)`
on the M2 runner at tree `84e177a2` — the same class of cost; the guardrails
added no measurable overhead (the refusal ladder is pure in-memory dict work
before any write).

## Where the nightly runs it

`grep -rn build_global_liquidity_transmission` finds exactly two workflow
callers, both no-arg and identical to the pre-T23 shape:

- `.github/workflows/daily.yml:4341` — `run: python -m
  scripts.build_global_liquidity_transmission || echo "::warning::…"` (the
  non-fatal sibling idiom; the last committed artifact stands on failure),
  after the plumbing step that produces its `regime/latest.json` input.
- `config/dag.yml:1420-1421` — `id: build_global_liquidity_transmission`,
  `module: scripts.build_global_liquidity_transmission`.

`.github/ci/legacy-jobs.yml:14606` lists the script for the CI test lane only.
No workflow was edited by T23.

## Why a nightly no-op (`unchanged`) is the common case

Source cadences in `config/global_liquidity_transmission_v1.yml`: Fed and ECB
balance-sheet legs are weekly (as-of-Wednesday, stale after 10–12 days), BoJ
is monthly (end-of-period, stale after 45 days); the USD funding legs
(broad dollar, 10y real yield, HY OAS) are business-daily. The state `asof`
sits on the weekly grid, so on most nights the upstream snapshot hash is
unchanged; the second measured run above is the ordinary nightly: the
builder detects equal `state.asof` + `source_snapshot_hash` against the
stored contract, writes nothing at all (bytes and mtimes preserved), and
prints `outcome=unchanged` in the notice. Consumers keep reading the
committed artifact; freshness ageing is the reader's law (C11), not a rewrite
trigger.

## Refusal rules, receipts, and their tests

All refusals keep the previous artifact untouched, exit 0, and emit one
line-start GitHub annotation (never through a logger). The future-clock rule
is the one exception to "untouched": a clock later than now is not inherited,
so the artifact is rewritten with fresh clocks, even at an equal asof and
source hash (it is never kept as `unchanged`):

| Rule | `::warning` title | Test |
| --- | --- | --- |
| Future clock not inherited (C11) | `glt-future-clock-refused` | `test_t23_future_clock_not_inherited_c11`, `test_t23_same_hash_future_clocked_artifact_is_rewritten_not_kept_c11` |
| Stale source (evidence clock or asof regressed) | `glt-stale-source-refused` | `test_t23_stale_source_promotion_refused` |
| Backdated leg receipt / generated_at | `glt-backdated-receipt-refused` | `test_t23_backdated_receipt_refused_keeps_previous` |

Matching guards: atomic write `test_t23_atomic_write_leaves_no_partial_artifact`,
idempotence `test_t23_idempotent_same_asof_and_hash_writes_nothing`,
first-known carry `test_t23_new_hash_same_evidence_carries_first_known_at`,
aged rerun `test_t23_aged_rerun_keeps_first_known_and_reads_stale_c11`,
replay bounds `test_t23_replay_asof_bounded_and_never_rewrites_store`,
one-notice law `test_t23_exactly_one_notice_per_run`. Every run ends with
exactly one `::notice title=glt-nightly::… outcome=written|unchanged|refused|replayed`.
The notice and the printed result describe the artifact of record after the
run. An `unchanged` or `refused` run wrote nothing, so it reports the kept
artifact's `asof`, `source_snapshot_hash` and `first_known_at`, never the
unwritten candidate's freshly stamped clock
(`test_t23_unchanged_and_refused_notice_reports_the_kept_artifact`).

## Recovery path

Every refusal is self-healing by construction: the previous artifact stands,
and the next nightly re-run is the recovery — once upstream evidence catches
up, the same step promotes normally. The only automatic re-dispatcher of the
nightly is `scripts/prophet_rescue.py`; never dispatch it by hand. A refused
run is visible in the Actions summary via its `::warning` and costs 0 writes.

## Replay deviation (B3)

The producer config carries no date key, so the `--asof` replay window cannot
be read from configuration; it is bounded by the **stored history span**
instead — `first_asof` from `data/global_liquidity_transmission/state_history_meta.json`
up to today (UTC), inclusive. If that meta is missing, replay is refused
(exit 2). `--out` is mandatory for a replay, must not resolve under the
repo's `site/` or `data/`, and a replay writes only that file — the four
stored artifacts are byte-identical (sha256) before and after, so
`first_known_at` history can never be rewritten by a replay.

No second daemon, cron, lane or service was added.
