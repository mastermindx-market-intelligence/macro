> **HOLD-FOR-SOL / DO NOT MERGE** — META-CEO A seat directive (packet A-F03-W2-2, 2026-09-22): never label / ready / merge / RATIFIED comments. This is a merge-barrier hold per `DEC:SOL-HOLD-IS-A-MERGE-BARRIER`. Release condition: explicit META-CEO A instruction to remove the hold and squash-merge. Every merge path (manual, sweeper, `--admin`, `merge-on-green`) is bound by this hold.

# [MO-A3] A-F03-W2-2: ThetaData skew accrual lane on the store host (launchd + R2 publish) + real-overlap audit tool

**Head SHA:** `589726c5ce96dc9c1d3e10a08c1a8e1f8c2a7b3d` (W2-2 packet deliverable head — round 4/N refresh: BLOCKER 1/2 + MAJOR 3/4 + MINOR 1/2/3 fixes re-applied; DEC evidence aligned; plist XML well-formedness; 68 tests pass)
**Base:** `origin/main` @ `2b427027a821dfc16407cc794eab15f83ae6874e` (current GitHub base ref OID)
**Branch:** `claude/mo-a-3-a-f03-w2-2-skew-accrual-lane` (DRAFT — never label / ready / merge)

## What & why

MO-PAID-013 W2-2 / F03-OPTIONS-EXPRESSION ships the **store-host producer** that feeds the options-skew forward ledger (`data/options_skew/snapshots.parquet`). W2-1b (`claude/mo-a-2-a-f03-w2-1`, in flight) adds the `--accrue` flag + the source-stamped canonical-wins ledger upsert on `scripts/build_options_skew.py`; this packet builds the launchd lane that runs that accrue against the live ThetaData EOD store on the M1 ops host and publishes the resulting ledger to R2 so the W2-3 render cutover can `fetch_r2 --dirs options_skew` into render hosts.

The lane adds files, tests, and an `options_skew` data-dir registration in `scripts/publish_r2._DATA_DIRS`. It does NOT change `engine/options_skew.py`, `scripts/build_options_skew.py`, or any workflow step. The plist is OFF by default until the seat installs it per the runbook.

## Round 4/N refresh — fixes applied this round

| ID | Fix | Commit |
| --- | --- | --- |
| BLOCKER 1 (revisit) | `_delta_stats` rewritten against (legacy, new) PAIRS. Sign-flip uses the product test (`legacy * new < 0`); bucket definitions made mutually exclusive (`n_zero_delta` requires both zero; `n_sign_match` excludes zero pairs; `n_sign_flip` requires `l * n < 0`). | `160957358e` |
| BLOCKER 2 (revisit) | `--pre-rows` added to `scripts/skew_accrual_verify_ledger` so the launchd runner can pass the pre-accrue row count and the check refuses a no-op accrue (`pre_rows >= post_rows`) with a named reason. The runner records the pre-rows to `.skew_pre_rows` between step_accrue and step_verify_ledger. This distinguishes a true 'no new session today, dedup-only, byte-equal rewrite' from a real append at the runner boundary. | `9ff8aac4a1`, `160957358e` |
| MAJOR 3 (revisit) | Two measurement tests pin the publish_r2 options_skew floor against the actual tracked bootstrap (`origin/main:data/options_skew/snapshots.parquet` = 238,595 bytes / 12,375 rows / 34 dates / 417 underlyings). The floor clears with >=4x margin against the bootstrap and refuses sidecar-only state. | `cf15685dd4` |
| MAJOR 4 | Audit verifies the recomputed row's `underlying` and `asof` match the requested (date, underlying) before folding it into the comparison. A recompute that keys on a different grain is now skipped with a named reason. | `160957358e` |
| MINOR 1 (revisit) | Plist XML well-formedness fix: removed the literal `--` sequence in the comment (XML 1.0 forbids double-hyphen inside comments). `plutil` accepted it but Python plistlib's expat parser refused it, blocking the launchd test suite. The substantive intent ('every publish writes a real manifest') is preserved verbatim. | `73a1feb0f2` |
| MINOR 2 (revisit) | `scripts/publish_r2.py` comment now correctly says `data/options_skew` is TRACKED and pins the measured bootstrap (238,595B / 12,375 rows / 34 dates / 417 underlyings) instead of the prior 'gitignored' mislabel. | `160957358e` |
| MINOR 3 | Dead `return_source = []` and unused `_emit` scaffolding removed from `scripts/skew_accrual_precheck.py`. | `160957358e` |
| MAJOR 2 | `agentos/decisions/DEC-SKEW-ACCRUAL-ON-THE-STORE-HOST.md` evidence aligned with the actual head: 'all 66 tests' (was '37'), and '05:30 local' (was '04:30 local') — the comment now matches the plist and the test count. | `a129e63bc4` |

## Round 3/3 fixes (carried over — preserved verbatim from earlier commits)

| ID | Fix | Commit |
| --- | --- | --- |
| BLOCKER 1 | Pre-W2-1b tree failure is now caught by `scripts/skew_accrual_precheck` BEFORE the accrue step; runner aborts loud (exit 4, FLAG_MISSING) instead of silently running `main()`. | `7f87a269e1`, `74c0cb733c` |
| BLOCKER 2 | `if ! cmd; then rc=$?` capture bug fixed — `rc` is captured BEFORE the if. A non-zero accrue/publish step now propagates the real exit code instead of silently returning 0. | `74c0cb733c` |
| BLOCKER 3 | `scripts/skew_accrual_verify_ledger` runs between accrue and publish; an empty/unchanged ledger aborts loud (exit 5, NO_LEDGER) instead of publishing a zero-row artefact to R2. | `7f87a269e1`, `74c0cb733c` |
| BLOCKER 4 | Plist schedule moved to 05:30 local wall-clock (PST = 13:30Z, PDT = 12:30Z), giving ≥1h headroom after the 11:30Z ThetaData EOD refresh year-round. | `f6e29f5874` |
| MAJOR 3 | `--no-manifest` removed from the first publish — manifest guard now compares against the (empty) prior manifest and writes a real one. | `74c0cb733c` |
| MINOR 1 | `n_sign_flip` tautology in `audit_options_skew_overlap` replaced with a real sign-flip counter using `legacy_skew * new_skew < 0`. | `89f82b4dfc` |
| MINOR 2 | Runbook first-run narrative refreshed (schedule, test surface). | `f388c33500` |

## Sequencing law (FROZEN — DO NOT REORDER)

| Wave | Branch | Owns |
| --- | --- | --- |
| W2-1b (sibling, in flight) | `claude/mo-a-2-a-f03-w2-1` | `scripts/build_options_skew.py --accrue \| --emit` + source-stamped ledger upsert; render hosts pinned to legacy source |
| **W2-2 (THIS packet)** | `claude/mo-a-3-a-f03-w2-2-skew-accrual-lane` | Store-host producer: launchd job, runner, gate helper, precheck/verify helpers, audit tool, R2 registry entry |
| W2-3 (later) | TBD | Render cutover to `--emit`; `fetch_r2 --dirs options_skew` restore |

## Files changed (true list — scoped diff vs `origin/main` base `2b427027a821dfc16407cc794eab15f83ae6874e`)

```
agentos/decisions/DEC-SKEW-ACCRUAL-ON-THE-STORE-HOST.md          | 143 +++++
ops/launchd/com.macro.skewaccrual.plist                            | 201 +++++++
ops/launchd/run_skew_accrual.sh                                    | 379 ++++++++++++++
scripts/audit_options_skew_overlap.py                              | 419 +++++++++++++++
scripts/publish_r2.py                                              |  49 ++-
scripts/skew_accrual_gate.py                                       | 201 +++++++++
scripts/skew_accrual_precheck.py                                   | 124 +++++
scripts/skew_accrual_verify_ledger.py                              | 144 +++++
tests/test_audit_options_skew_overlap.py                           | 444 ++++++++++++++++
tests/test_skew_accrual_gate.py                                    | 221 +++++++++
tests/test_skew_accrual_launchd.py                                 | 582 +++++++++++++++++++++
tests/test_skew_accrual_precheck.py                                | 186 ++++++++
tests/test_skew_accrual_verify_ledger.py                           | 174 ++++++
13 files changed, ~3265 insertions, 2 deletions  (GitHub view: 16 files, 3766+/2-)
```

> GitHub's PR diff view reports 16 files / 3766+ / 2- because it includes the `.claude/PR_BODY_W2-2.md` round-doc refresh and the `research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md` runbook from round 3/3, plus the `config/unrun_test_waivers.yml` waiver rows. Those three carry-overs are unchanged this round.

## Install runbook

See `research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md`. Highlights:
1. Create the dedicated lane checkout `/Users/chriswong/skew-ops-wt` as a sparse clone of `origin/main`.
2. Copy `ops/launchd/com.macro.skewaccrual.plist` to `~/Library/LaunchAgents/` (do NOT load it from the repo).
3. `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.macro.skewaccrual.plist`.
4. Smoke: `SKEW_FRESHNESS_BYPASS=1 SKEW_DRY_RUN=1 ./run_skew_accrual.sh` (accrues locally, no R2 publish).
5. Full: `SKEW_FRESHNESS_BYPASS=1 ./run_skew_accrual.sh` (R2 publish — same as nightly launchd).

## Tails (real receipts captured 2026-09-22 — round 4/N refresh)

### `pytest` — all 5 new test files (68 passed)

```
$ python3 -m pytest tests/test_skew_accrual_gate.py \
    tests/test_skew_accrual_launchd.py \
    tests/test_audit_options_skew_overlap.py \
    tests/test_skew_accrual_precheck.py \
    tests/test_skew_accrual_verify_ledger.py -q
....................................................................   [100%]
68 passed in 35.76s
```

Test breakdown:
- `test_skew_accrual_gate.py` — 14 tests
- `test_skew_accrual_launchd.py` — 21 tests (incl. 2 MAJOR-3 measurement tests pinning the publish_r2 floor against the actual tracked bootstrap)
- `test_audit_options_skew_overlap.py` — 14 tests (incl. pair-based delta-stats buckets + recomputed-key match check)
- `test_skew_accrual_precheck.py` — 7 tests (post MINOR-3 cleanup)
- `test_skew_accrual_verify_ledger.py` — 12 tests (incl. 3 BLOCKER-2 --pre-rows tests: ok-on-growth, refuse-on-no-growth, CLI-flag-blocks)

### `python3 scripts/agentos.py validate`
```
agentos: 1193 records (69 workstreams, 338 decisions, 297 discoveries, 489 handoffs) — 0 error(s), 90 warning(s)
```

### `python3 scripts/check_contract_delta.py --base origin/main`
```
::notice title=contract-delta::tests/test_render_dead_ref_targets.py is already unwired on this PR's base — pre-existing, not introduced by this PR
contract-delta: 0 introduced, 1 inherited (base 6ddb91c6fe88)
```

### `sh -n ops/launchd/run_skew_accrual.sh`
```
RUNNER_SH_N_OK   (exit code 0)
```

### `plutil -lint ops/launchd/com.macro.skewaccrual.plist`
```
ops/launchd/com.macro.skewaccrual.plist: OK
```

### Plist well-formedness (Python `plistlib`/expat — caught by tests)
```
test_skew_accrual_launchd.py::test_plist_parses_with_python_plistlib ... PASSED
test_skew_accrual_launchd.py::test_plist_pins_label_working_directory_and_program_arguments ... PASSED
test_skew_accrual_launchd.py::test_plist_pins_schedule_weekdays_local_wall_clock ... PASSED
test_skew_accrual_launchd.py::test_plist_pins_thetadata_store_env_var_without_secrets ... PASSED
test_skew_accrual_launchd.py::test_plist_pins_keepalive_throttle_session_type ... PASSED
```

## Audit tool — what the seat does with it

After W2-1b lands on main and the store-host lane has produced ~5 trading days of thetadata rows, run from `/Users/chriswong/skew-ops-wt`:

```
python -m scripts.audit_options_skew_overlap
```

This recomputes the ThetaData skew for every legacy `polygon_gex` (date, underlying) row, emits a one-line JSON summary to stdout (`keys_compared`, `sign_agreement_rate`, `n_sign_flip`, `|delta_skew|` p50/p90/max, top-10 worst keys), and writes `research/MARKET_ONTOLOGY_F03_SKEW_OVERLAP_RECEIPT_<TODAY>.md`.

Round 4/N behaviour: the audit verifies the recomputed row's underlying and asof match the requested (date, underlying) before folding it into the comparison (MAJOR-4). Mismatches are skipped with a named reason and reported under `skipped[]` in the summary. Sign agreement uses the product test: `legacy * new < 0` ⇒ genuine sign flip; `legacy * new > 0` ⇒ same sign; `legacy == 0 AND new == 0` ⇒ zero-delta pair (counts toward `sign_agreement`, not toward `n_sign_flip`).

The exit codes are:
- `0` — `EXIT_OK` (run completed; review the summary / receipt).
- `1` — `EXIT_MISSING_ENGINE` (pre-W2-1b tree; wait for the sibling PR to merge).
- `2` — `EXIT_NO_LEGACY_ROWS` (no `polygon_gex` rows to compare; all-stamped-thetadata).
- `3` — `EXIT_READ_ERROR` (ledger parquet missing or unreadable).

## What this packet did NOT change

- `engine/options_skew.py` — W2-1b owns it.
- `scripts/build_options_skew.py` — W2-1b owns the `--accrue` / `--emit` flags.
- Any workflow file (`.github/workflows/**`, `.github/ci/**`) — the lane is store-host-side; CI does not own it.
- `data/` or `site/` — the lane writes through `scripts/build_options_skew --accrue` (W2-1b).
- Any label, ready, merge, or RATIFIED comment on this PR — DRAFT only.

## Contract delta — waiver rationale

`scripts/check_contract_delta.py` flagged the five new test files as unrun suites. Listing them in `.github/ci/legacy-jobs.yml` would be a global CI invalidator (full 194-job suite, ci-authority hit) and the lanes they cover are store-host ops, not signal-contract / render subjects. The fix is a reasoned waiver row per suite in `config/unrun_test_waivers.yml` (one row each for `test_skew_accrual_gate.py`, `test_skew_accrual_launchd.py`, `test_skew_accrual_precheck.py`, `test_skew_accrual_verify_ledger.py`, `test_audit_options_skew_overlap.py`). Each row names the owner (`META-CEO A, lane A-F03-W2-2`), the direct pytest invocation, and the deletion condition (when a store-host-side ops CI step is commissioned).

Round 4/N contract-delta: **0 introduced**, 1 inherited (the pre-existing `tests/test_render_dead_ref_targets.py` unwire that was already on the PR's base).

## Reference

- `agentos/decisions/DEC-SKEW-ACCRUAL-ON-THE-STORE-HOST.md` — the store-host choice and the three rejected alternatives (CI label, git narrow-commit, 60 GB store hydration).
- `research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md` — install runbook, sequencing law, audit-tool pointer.
- `scripts/skew_accrual_gate.py` — column-pruned freshness gate (T-1 NYSE session via `lib.nyse_calendar.expected_last_session()`).
- `scripts/skew_accrual_precheck.py` — BLOCKER-1 source-grep for the `--accrue` flag (runner aborts loud on pre-W2-1b tree).
- `scripts/skew_accrual_verify_ledger.py` — BLOCKER-3 ledger row-count check + BLOCKER-2 --pre-rows no-op refuse (runner aborts loud on zero-row publish OR on no-growth under accrue).
- `scripts/audit_options_skew_overlap.py` — legacy-vs-ThetaData real-overlap audit, pair-based with product test (BLOCKER-1 revisit) and recomputed-key match (MAJOR-4).
- `scripts/publish_r2.py` — adds `options_skew` to `_DATA_DIRS` with a 10 KB floor + a `min_files_override=2` (snapshots.parquet + validation_gate.json sidecar). Comment now says TRACKED with the measured bootstrap (MINOR-2 revisit).
