---
workstream: "WS:MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION"
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
  - path: .github/ci/legacy-jobs.yml
    what: Removed the options-skew step from flow-surface. Added gate:code job options-skew-engine.
  - path: tests/test_options_skew.py
    what: Upsert, canonical-wins, atomic write, accrue skip, emit-from-ledger, legacy flag, workflow pin.
  - path: tests/test_ci_pack.py
    what: Registered options-skew-engine in CURATED_EXCLUSIVE.
verified:
  - claim: Upsert, canonical-wins, atomic replace, accrue-skip, emit-from-ledger, and the legacy pin tests pass, and the entry-state consumer still reads the ledger.
    command: python -m pytest tests/test_options_skew.py tests/test_options_entry_state.py -q
    result: 44 passed
  - claim: options-skew-engine is in CURATED_EXCLUSIVE and its exclusive paths cover the import closure. flow-surface no longer needs the skew suite for its own closure.
    command: python -m pytest tests/test_ci_pack.py -k curated_exclusive -q
    result: 2 passed, 119 deselected
  - claim: With OPTIONS_SKEW_LEGACY_CHAIN=1 the branch builder matches the pre-packet builder at 98df3cf31eb7. latest.json is equal apart from generated_utc and the five additive keys. Ledger rows are equal apart from source=polygon_gex.
    command: python comparison of git show 98df3cf31eb7:scripts/build_options_skew.py plus engine/options_skew.py against the branch builder, synthetic polygon chain, temp dirs only
    result: JSON_EQUAL_MODULO_GENERATED_UTC_AND_FIVE_ADDITIVE_KEYS and LEDGER_EQUAL_MODULO_SOURCE rows 2
  - claim: The legacy-jobs manifest still validates, and this PR introduces no contract-delta closure miss.
    command: python scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-index 1 --pack-count 12 --validate-only && python scripts/check_contract_delta.py --base origin/main
    result: Validated 221 legacy jobs. contract-delta 0 introduced, 1 inherited (base 0d7b6fb14d2f).
  - claim: GitHub annotation warnings in this tree still start at column 0.
    command: python -m pytest tests/test_gh_annotation_line_start.py -q
    result: 4 passed
unverified:
  - claim: GitHub Actions on the pushed head is green.
    what_would_verify: gh pr checks 6923 after the push. This packet does not claim that.
unresolved:
  - GitHub checks on the pushed head are not claimed green.
  - W2-2 M1 launchd ThetaData accrual is not installed.
  - W2-3 cutover (drop the legacy flag, switch render to --emit) is not done.
  - agentos validate reports one dangling-ref. No workstream record exists for WS:MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION, and this packet does not invent one.
next_actions:
  - W2-2 installs the M1 launchd ThetaData accrual. The store host accrues and commits the parquet ledger. Do not do that on a render host.
  - W2-3 removes OPTIONS_SKEW_LEGACY_CHAIN=1 from engine-render.yml and closing-bell.yml and switches those calls to --emit.
do_not_redo:
  - Sequencing law. W2-1b is code with zero live behavior change. W2-2 is the M1 ThetaData accrual lane. W2-3 is the render cutover. Do not install launchd or switch render hosts to --emit in W2-1b.
  - Do not add a second chain or skew engine. Reuse engine.thetadata_store.make_chain_provider.
  - Do not touch scripts/validate_options_skew.py. The gate stays closed. DNR:KILL-SKEW-DECELERATION is display only.
danger_areas:
  - The non-atomic concat-and-rewrite of data/options_skew/snapshots.parquet is retired. snapshot() now writes a temp file and os.replace in the same directory. Do not put the concat back.
  - A polygon_gex row must never replace a thetadata row for the same (date, underlying). A missing source column reads as polygon_gex.
  - Render hosts still have no ThetaData store. Removing the legacy export before W2-2 lands publishes null skew.
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
on the options_skew brun line and unset it immediately after. That is the
zero-regression pin. MAIN_AT_START for the merge was `98df3cf31eb7bbca79f1e1cdcb6b3f1fc30edacc`.

### do_not_redo

Sequencing law: W2-1b is this code, with the legacy flag still on. W2-2 is
the M1 launchd ThetaData accrual (the store host accrues and pushes the
parquet). W2-3 is the cutover (render hosts drop the flag and switch to
`--emit`). Do not do W2-2 or W2-3 here.

### danger_areas

The non-atomic concat-and-rewrite of `data/options_skew/snapshots.parquet`
is what this packet retires. Putting that rewrite back races every reader
that opens the ledger while it is being replaced.
