# Reuse validated price snapshots during Options session outcome accrual

## Summary
- **Head sha**: `d95bc0a45f37caafd626611e08813a444793d63a`
- **Branch**: `codex/options-alpha-session-derivation-cost-20261003`
- **Base**: `main`
- **State**: DRAFT (no CI checks read, no merge-on-green armed)

## Files changed (6 files, +1043 / −11)
```
 engine/options_signal_episode.py                                                | 125 +++++-
 research/MO_EXT_FIX_OPTIONS_PRODUCT_20261003/PROFILE_NOTE.md                    |  51 +++
 research/MO_EXT_FIX_OPTIONS_PRODUCT_20261003/profile_session_derivation_seam.json |  43 ++
 scripts/_profile_session_derivation_seam.py                                     | 269 ++++++++++++
 scripts/build_options_signal_episode.py                                         |  78 +++-
 tests/test_options_signal_episode.py                                            | 488 +++++++++++++++++++++
 6 files changed, 1043 insertions(+), 11 deletions(-)
```

## What changed
Adds a per-run typed `_PreparedPriceBars` dataclass plus a public
`prepare_price_bars` factory. The factory invokes `normalize_price_bars`
exactly once per ticker after the snapshot's immutable-bytes / readback /
hash / receipt checks pass. The H+60 and session derivation phases share the
prepared wrapper for the same snapshot; legacy raw `DataFrame` callers keep
their existing normalize-once path.

| pass                | normalize_calls | derive_calls |
|---------------------|----------------:|-------------:|
| raw-baseline (old)  |           1 600 |        1 600 |
| prepared-seam (new) |              20 |         1 600 |

Same number of derived outcomes, identical bytes; only the redundant
`normalize_price_bars` work is removed.

## Spec item → what I did
| Spec item | What was done |
|---|---|
| Typed per-run prepared price-bars seam | New `_PreparedPriceBars` frozen dataclass in `engine/options_signal_episode.py` |
| Factory invokes normalizer once | `prepare_price_bars(raw_frame, *, ticker)` calls `normalize_price_bars` exactly once and freezes the result |
| Reused by H60/session consumers of same snapshot | Per-run `prepared_price_cache: dict[str, _PreparedPriceBars]` shared by both phases; same key as the legacy `price_cache` |
| Preserve legacy raw DataFrame callers | `_price_snapshot` keeps returning `(frame, receipt)`; raw callers keep their existing normalize-once path |
| Avoid boolean bypass / unchecked public factory input | All construction is gated through `prepare_price_bars`; private `_frame` field is underscored; the factory rejects `None`, non-DataFrame input, empty ticker, empty normalized frame |
| Frozen dataclass, read-only frame, no global cache | `@dataclass(frozen=True, slots=True)` + `frame.values.setflags(write=False)` + per-run `prepared_price_cache` lives only inside `run()` |
| Snapshot uses prepared normalized frame for receipt row_count/first/last validation | `_price_snapshot` now calls `prepare_price_bars` after all immutable-bytes/readback/hash/receipt checks pass; row_count/first/last compare against `prepared.row_count` / `prepared.first_time` / `prepared.last_time` |
| Per-outcome `_validated_session_price_receipt` retained | Untouched — unchanged in both `derive_h60_outcome` and `derive_session_outcome` |
| Never cache episode-specific selected paths or final outcomes | `prepared_price_cache` holds only the normalized OHLC frame + receipt-derived bounds; no path/evidence persistence |
| No change to economic/calendar/population/denominator semantics | Calendar session selection, NYSE closed/holiday logic, premium/contract math untouched |
| Streamed diagnostics every 250 attempts | `options_episode_h60_progress` and `options_episode_session_progress` log lines every 250 attempts; both include attempted/unresolved_total/complete/terminal_incomplete/pending/snapshot_tickers/prepared_tickers/elapsed_seconds |
| Diagnostic clocks never become receipt/availability clocks | Diagnostics use `_perf_counter()` and live counters; receipts still use `_canonical_utc` / `_as_utc` |
| No new output ledger or scheduler | Log lines only; no new JSONL / ledger writes |

## Tests run
```
tests/test_options_signal_episode.py  242 passed, 2 skipped, 19 deselected in 7.03s
```
(19 deselected are sparse-worktree `data/`-fixture tests unrelated to this change.)

Targeted new tests (all pass):
- `test_prepare_price_bars_factory_invokes_normalizer_exactly_once`
- `test_prepare_price_bars_factory_rejects_unchecked_inputs`
- `test_prepared_wrapper_is_frozen_and_internal_frame_is_read_only`
- `test_prepared_path_matches_raw_path_full_canonical_bytes` (parametrized × 5 horizons)
- `test_prepared_path_normalizes_once_per_ticker_not_per_horizon`
- `test_h60_path_reuses_prepared_frame_without_mutation`
- `test_legacy_raw_caller_path_remains_unaffected`
- `test_invalid_ohlc_keeps_prepared_path_pending`
- `test_unknown_bar_cadence_with_prepared_path_stays_pending`
- `test_empty_normalization_factory_fails_closed`
- `test_cached_failure_replays_exact_pending_and_clocks`
- `test_torn_receipt_fails_closed_with_original_pending_or_error`
- `test_toctou_receipt_flip_fails_closed`
- `test_builder_progress_logs_fire_every_250_attempts`
- `test_seam_does_not_share_across_runs`

```
242 passed, 2 skipped in 7.03s
```

## Limitations / known boundaries
- This is a **bounded source performance fix**. No live builder rerun, no
  `data/` ledger mutation, no time-budget increase, no checkpoint / append /
  lock reordering, no scientific-rule change.
- The 80× counter reduction is a **floor**: synthetic profile, no R2 I/O,
  no parquet readback, no LedgerLock. Production speedup is bounded below by
  the I/O share, not by normalize calls alone.
- H+60 still calls `derive_h60_outcome` per-episode; the prepared seam saves
  one normalize call per ticker, not per episode, on that path. The session
  phase is where the dominant savings come from (1 vs H = 5 normalize calls
  per ticker).
- Profile script (`scripts/_profile_session_derivation_seam.py`) prints JSON
  to stdout and writes no data. Re-run by hand; CI does not invoke it.
- Profile artifact committed under
  `research/MO_EXT_FIX_OPTIONS_PRODUCT_20261003/profile_session_derivation_seam.json`
  with the matching human-readable note in `PROFILE_NOTE.md`.

## CI state
- PR is **DRAFT**; no checks have been polled.
- `merge-on-green` is **NOT** armed.
- `gh pr merge --auto --squash` is **NOT** armed.
- Root owns independent review/release and any future natural observability.

## Owner (operator, independent)
This lane is delivered but not merge-eligible from this seat — independent
Sol review + Chairman/CEO merge authorization required per the existing
seam (Meta-CEO authority for Options Alpha source-recovery; reference
PR #7889 / #8310 / #8342).