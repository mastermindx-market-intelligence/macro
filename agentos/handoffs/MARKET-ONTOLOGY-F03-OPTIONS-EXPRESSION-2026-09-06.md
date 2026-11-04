---
workstream: "WS:MARKET-OS"
session: claude/mo-a-2-a-f03-w2-1
model: local
ended_because: complete
prs:
  - 6923
mission: >
  W2-1b ships the options-skew ledger upsert, the accrue/emit split, and an
  explicit legacy-chain pin on the render hosts, with zero live behavior change.
  W2-2 (M1 ThetaData accrual) and W2-3 (cutover to --emit) are not this packet.
state_before: >
  DRAFT PR 6923 at efe0abec5e13 computed skew from ThetaData with no fallback.
  Render hosts have no ThetaData store, so merging that head would publish a
  null skew over the live polygon surface. The ledger rewrite was a non-atomic
  concat of the whole parquet.
changed:
  - path: engine/options_skew.py
    what: UPSERT keyed by (date, underlying), source column polygon_gex or thetadata, canonical-wins, atomic os.replace.
  - path: scripts/build_options_skew.py
    what: --accrue and --emit. No flag runs both. Unresolved ThetaData skips the ledger write. Emit reads the ledger and never opens a chain.
  - path: .github/workflows/engine-render.yml
    what: OPTIONS_SKEW_LEGACY_CHAIN=1 around the options_skew brun and the narrow gex run_py, unset immediately after.
  - path: .github/workflows/closing-bell.yml
    what: OPTIONS_SKEW_LEGACY_CHAIN=1 around the options_skew brun, unset immediately after.
  - path: .github/workflows/render.yml
    what: Same legacy export around the options_skew brun and the scope-gex run_py. Round 2. These two calls were still unpinned.
  - path: scripts/ci/daily_engine_regional_desk_builders.sh
    what: Same legacy export around the nightly brun options_skew. Round 2. daily.yml job engine runs this script.
  - path: .github/ci/legacy-jobs.yml
    what: Removed the options-skew step from flow-surface. Added gate:code job options-skew-engine.
  - path: tests/test_options_skew.py
    what: Upsert, canonical-wins, atomic write, accrue skip, emit-from-ledger, legacy flag, workflow pin.
  - path: tests/test_ci_pack.py
    what: Registered options-skew-engine in CURATED_EXCLUSIVE.
verified:
  - claim: Upsert, canonical-wins, atomic replace, accrue-skip, emit-from-ledger, and the legacy pin tests pass, and the entry-state consumer still reads the ledger.
    command: python -m pytest tests/test_options_skew.py tests/test_options_entry_state.py -q
    result: 46 passed
  - claim: options-skew-engine is in CURATED_EXCLUSIVE and its exclusive paths cover the import closure. flow-surface no longer needs the skew suite for its own closure.
    command: python -m pytest tests/test_ci_pack.py -k curated_exclusive -q
    result: 2 passed, 119 deselected
  - claim: With OPTIONS_SKEW_LEGACY_CHAIN=1 the branch builder matches the pre-packet builder at 98df3cf31eb7, including a two-strike expiry. latest.json is equal apart from generated_utc and the five additive keys. Ledger rows are equal apart from source=polygon_gex.
    command: python comparison of git show 98df3cf31eb7:engine/options_skew.py against the branch builder, synthetic polygon chain AAA/BBB (4 strikes) plus THIN (2 strikes), temp dirs only
    result: JSON_STRIPPED_EQUAL True. Names AAA, BBB, THIN. THIN skew 0.1, n_strikes 2. LEDGER_NINE_EQUAL True, rows 3, source polygon_gex.
  - claim: The legacy-jobs manifest still validates, and this PR introduces no contract-delta closure miss.
    command: python scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-index 1 --pack-count 12 --validate-only && python scripts/check_contract_delta.py --base origin/main
    result: Validated 221 legacy jobs. contract-delta 0 introduced, 1 inherited (base 59c07595d287). That base id is origin/main at the moment the script resolved it. Main kept moving after the merge.
  - claim: GitHub annotation warnings in this tree still start at column 0.
    command: python -m pytest tests/test_gh_annotation_line_start.py -q
    result: 4 passed
unverified:
  - claim: GitHub Actions on the pushed head is green.
    what_would_verify: gh pr checks 6923 after the push. This packet does not claim that.
unresolved:
  - GitHub checks on the pushed head are not claimed green.
  - W2-2 M1 launchd ThetaData accrual — RESOLVED 2026-09-23 (#7737 merged, lane live on m1; see agentos/handoffs/MARKET-OS-2026-09-23-skew-lane-live.md).
  - W2-3 cutover (drop the legacy flag, switch render to --emit) — RESOLVED 2026-09-23 (#7743 merged as b2d43b3a; same handoff).
  - This record's workstream is WS:MARKET-OS (the F03 lane's owner per the F00C granular closure ledger, MO-PAID-013 `current_owner`); an earlier draft cited a non-existent WS:MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION, which agentos validate rejected as a dangling-ref (seat cure 2026-09-22).
next_actions:
  - W2-2 installs the M1 launchd ThetaData accrual. The store host accrues and commits the parquet ledger. Do not do that on a render host.
  - W2-3 removes OPTIONS_SKEW_LEGACY_CHAIN=1 from engine-render.yml, closing-bell.yml, render.yml, and scripts/ci/daily_engine_regional_desk_builders.sh, and switches those calls to --emit.
do_not_redo:
  - Sequencing law. W2-1b is code with zero live behavior change. W2-2 is the M1 ThetaData accrual lane. W2-3 is the render cutover. Do not install launchd or switch render hosts to --emit in W2-1b.
  - Do not add a second chain or skew engine. Reuse engine.thetadata_store.make_chain_provider.
  - Do not touch scripts/validate_options_skew.py. The gate stays closed. DNR:KILL-SKEW-DECELERATION is display only.
danger_areas:
  - The non-atomic concat-and-rewrite of data/options_skew/snapshots.parquet is retired. snapshot() now writes a temp file and os.replace in the same directory. Do not put the concat back.
  - A polygon_gex row must never replace a thetadata row for the same (date, underlying). A missing source column reads as polygon_gex.
  - Render hosts still have no ThetaData store. Removing the legacy export before W2-2 lands publishes null skew.
  - A four-strike floor in compute_skew drops names the polygon builder still publishes. Do not put that floor back.
  - config/dag.yml names the module but does not launch it. The live launches are engine-render.yml, closing-bell.yml, render.yml, and scripts/ci/daily_engine_regional_desk_builders.sh. A new launch without the export is a live regression.
---

# Handoff — MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION (A-F03-W2-1)

date: 2026-09-06
packet: A-F03-W2-1 — Skew source migration to the ThetaData chain store
ledger row: MO-PAID-013
branch: claude/mo-a-2-a-f03-w2-1
PR: opened DRAFT (see PR link in the calling session's report)

## What happened

`engine/options_skew.py` now sources its per-strike chain from
`engine/thetadata_store.chain()` via `make_chain_provider()` instead of the
legacy `data/polygon_gex/chains/*.parquet` glob. The legacy glob is retired
into `_legacy_chain()`, reachable only behind the explicit
`OPTIONS_SKEW_LEGACY_CHAIN=1` env flag (off by default) — never an automatic
fallback. `build_snapshot()` gained additive `source`/`source_state`/
`source_detail` keys; a non-`ok` state publishes `names={}` (never a 0.0)
and prints a `::warning` GitHub annotation.

`tests/test_options_skew.py` extended from 6 to 12 tests (all pass locally).
`.github/ci/legacy-jobs.yml`'s `flow-surface` job gained the `run:` step and
paths-trigger entry that actually execute this test file — it had zero CI
coverage before this PR.

## Verified (falsifiable claims)

- `verified: python -m pytest tests/test_options_skew.py -q` → 12 passed,
  run on this checkout 2026-09-06.
- `verified: python -m scripts.build_options_skew` → exit 0, writes
  `site/options_skew/latest.json` with
  `names={}, n=0, source=None, source_state="thetadata_store_unresolved"`
  and a `::warning title=options-skew-source::` line on stdout — this host's
  ThetaData store genuinely does not resolve (`data/thetadata_eod/` holds
  only `_backfill_state.json`/`_manifest.json`).
- `verified: grep -n polygon_gex engine/options_skew.py` → hits only in the
  module docstring/comments and inside `_legacy_chain()` — no automatic path
  reaches the glob.

## do_not_redo

- Do not add a second chain/surface/Greeks adapter — reuse
  `engine.thetadata_store.make_chain_provider` (F03 standing do_not_redo,
  `agentos/handoffs/MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION-FABLE-COO-2026-08-26.md:31-33`).
- Do not touch `scripts/validate_options_skew.py` — the gate stays closed
  (`DNR:KILL-SKEW-DECELERATION`, `research/DO_NOT_REBUILD.md:88`).

## danger_areas / open items for the next session

- `python3 scripts/check_contract_delta.py --base origin/main` was launched
  against this diff but was still running (>2 min CPU) when this worker's
  tool-call budget ran out — its PASS/FAIL was not observed before the PR was
  opened. The `.github/ci/legacy-jobs.yml` diff is minimal (one `run:` line +
  one paths entry) and should be low-risk, but the ship/review stage should
  re-run this check before arming `merge-on-green`.
- No ThetaData store resolves on this host, so the real-store overlap
  acceptance line (§9 line 4 of the frozen spec) is discharged only via the
  synthetic `test_thetadata_and_legacy_overlap` test — the PR body states
  this explicitly rather than claiming a real measurement that doesn't exist.
- Per the frozen spec, `merge-on-green` must NOT be armed on this PR until an
  Opus PASS review — the ship stage should arm it after that review, not
  before.

## W2-1b (2026-09-22)

Code only. No live behavior change on the render hosts.

The ledger upsert is keyed by (date, underlying). Each row carries `source`
of `polygon_gex` or `thetadata`. A row written before that column existed is
read as `polygon_gex`. A thetadata row replaces a polygon row for the same
key. A polygon row never replaces a thetadata row. The write is a temp file
plus `os.replace` in the same directory. The old concat-and-rewrite is retired.

`scripts/build_options_skew.py` takes `--accrue` and `--emit`. No flag runs
both, so today's callers stay on both legs. When the ThetaData store is
unresolved, accrue prints the existing `::warning title=options-skew-source::`
line and does not write the ledger. Emit reads the ledger and writes
`site/options_skew/latest.json` with `ledger_asof` and `accrual_state`
(`accrued_today` or `ledger_only`). Emit does not construct a chain provider.

`engine-render.yml` and `closing-bell.yml` export `OPTIONS_SKEW_LEGACY_CHAIN=1`
on the options_skew brun line and unset it immediately after. The first merge
of `origin/main` was a real two-parent merge. Its second parent was
`98df3cf31eb7bbca79f1e1cdcb6b3f1fc30edacc`.

### W2-1b round 2 (2026-09-22)

The first pin did not cover every live caller, and a four-strike floor dropped
names the polygon builder still publishes. Both are fixed in this round.

`render.yml` exports the legacy flag on its `brun options_skew` line and on
its scope-`gex` `run_py` line. `scripts/ci/daily_engine_regional_desk_builders.sh`
does the same for the nightly engine job (`daily.yml` only calls that script).
Each export is unset on the next line. `compute_skew` no longer returns before
the put-minus-call formula when the chosen expiry has fewer than four rows.

A second two-parent merge brought `origin/main` in at
`a1a4c0d561a1b9fbbc8b06467ec75bf92cdb5ad9`. Pre-merge
`git diff --stat 98df3cf31eb7 HEAD` and post-merge
`git diff --stat origin/main...HEAD` were the same eight files, 1067 insertions,
55 deletions. None were dropped. Main moved again after that merge (hot-tape
and `#7295`); this round does not chase those commits.

### do_not_redo

Sequencing law, unchanged: W2-1b is this code, with the legacy flag still on.
W2-2 is the M1 launchd ThetaData accrual. W2-3 is the cutover. Do not do W2-2
or W2-3 here.

### danger_areas

The non-atomic concat-and-rewrite of `data/options_skew/snapshots.parquet` is
what this packet retires. Putting that rewrite back races every reader that
opens the ledger while it is being replaced. A four-strike floor, or a live
caller without `OPTIONS_SKEW_LEGACY_CHAIN=1`, changes the published surface.
