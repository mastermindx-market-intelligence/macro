# T12 Stage1 dependency review — 2026-10-17

Status: **Stage1 source and sample call path reviewed; no blocker found in the supplied Stage1 sample helpers. Full transitive-import qualification is not established by this local bundle.**

Scope: source inspection only. No module import, sample generation, label calculation, hydration, provider operation, feature join, model fit, trial registration or production/repository mutation was performed. This review is the only file written.

## Identities

The local Stage1 file has SHA256 `47ec425821c7a075dc4667171d9e75e8af213e0f088154c5fdb1cad419413714`, matching `stage1_source_receipt.json`; recorded Git blob `76d231d6d12c8693cd07a2540b360c24f6c50b42`. The parent independently compared that blob with original T12 merge `ed1497887c99101bd1b8bc5438e281f02466371b` and reported an exact match. This review verifies the local SHA and reads its semantics; it does not repeat the parent's remote Git comparison.

Original builder blob: `0a0eecb98e743b780db1ee3b0382e268d592fa67`. Original specification blob: `fe68838867982e845297aeb0daf518e0387120f9`.

The admitted SPY receipt is `../research_notes/all_date_census/T13_SPY_INPUT_IDENTITY_2026-10-17.json`: 1,321 RAW rows, 2021-07-06 through 2026-10-07; normalized OHLCV SHA256 `c686f0bc683f3109c1be5431cab99661734f2481fc98e8479320e285507be6fb`. The sample digest remains ungenerated in this review.

## Exact sample call path

`build_sample` calls the original `event_episodes` and `negative_controls` for horizons `(5, 10, 21)` with seed `20261013`, three controls per episode and a 63-session buffer. Both use `_event_origin_indices`, which calls Stage1 `build_labels`.

| Helper | Inspected behavior |
|---|---|
| `build_labels` | Loops over `HORIZONS`; calls `om.forward_max_loss(close, h)` and `om.loss_event(A, threshold=THRESHOLD)`. Constants are `(5, 10, 21)` and `0.05`. It contains no I/O, fitting or ledger call. Label semantics ultimately depend on the two `lib.observed_moves` helpers. |
| `event_clusters` | Sorts integer event indices and joins successive origins whose session-index gap is at most `h`. Pure NumPy/list operations. |
| `cluster_window` | Returns `[first_event_index - EPISODE_PRE, last_event_index + h]`; `EPISODE_PRE` is 21. Pure arithmetic. |
| `merge_episodes` | Time-orders clusters and merges overlapping episode windows, including a shared endpoint. Pure list/dictionary operations. |

The builder clips emitted windows to the supplied series. This path does not call Stage1 `main`, `build_features`, `run_fits`, `evaluate_and_write`, `hydrate`, `load_sample` or `trial_ledger_scope`.

## Import behavior

Stage1's own module-level executable statements comprise imports, constant/container assignments, a `Path(__file__).resolve()` calculation, a process-local `sys.path.insert`, and its guarded `if __name__ == '__main__': main()` entry point. No module-level call to hydration, a collector, trial registration, fitting or result writing was found. Function decorators/defaults contain no custom calls; its two exception classes do not execute their constructors at import.

The collector import is deferred inside `load_sample`. Namespace hydration is confined to `hydrate`. Trial registration is confined to `trial_ledger_scope`, and Stage1's full study enters that scope from `main`. Sample-only use does not traverse them.

However, importing the complete Stage1 module also imports:

- `engine.trial_ledger`
- `engine.vol_forecast.realized_vol`
- `lib.nyse_calendar`
- `lib.observed_moves`
- NumPy, pandas and SciPy

The four project modules and their package initializers were not supplied in the local review bundle. Their import-time behavior was therefore not inspected, and no claim that full transitive import is side-effect-free is made. In particular, the names of `forward_max_loss` and `loss_event` are not enough to verify their implementation identities.

## Recommendation and concrete remaining check

There is no new scientific, rights or trial-registration blocker to the authorized **sample-only freeze** in the supplied Stage1 code. Before executing via a full import, bind the actual `lib.observed_moves` implementation and establish that the project imports above do not invoke a collector, ledger write or production write at import. This is a bounded execution-path qualification, not a request for an absent outside approver.

If the parent uses its existing pure-function AST isolation approach, retain the unmodified original builder/helper ASTs and exact source hashes, bind the actual two `lib.observed_moves` functions and any pure dependencies, and record the isolation method. Do not replace the label definitions with an equivalent-looking implementation. This permits an isolated sample calculation without importing unrelated Stage1 study machinery.

Use the admitted in-memory RAW close series in its existing session order, avoiding a CSV float round trip. Freeze `json.dumps(sample, sort_keys=True).encode('utf-8')`, with no trailing newline. Record its SHA256 separately from the builder's date/close `input_sha256` and the existing OHLCV identity hash.

## Downstream limitations remain unchanged

Freeze the original sample even if it has control shortfalls; do not resample or relax the 63-session buffer. Report controls requested/placed/missing by horizon and episode, month-match counts, final-`h`-session control intersections, pre-warmup origins and cross-horizon overlaps. The builder does not exclude immature tail origins from controls merely because their labels are missing. Nonoverlapping windows do not establish independent episodes. The outcome-conditioned sample does not supply a live daily base rate, calibrated probability or chronological validation design.

This review authorizes no feature–outcome join, model fit, trial, forecast publication or policy change. Those remain separate existing programme gates.
