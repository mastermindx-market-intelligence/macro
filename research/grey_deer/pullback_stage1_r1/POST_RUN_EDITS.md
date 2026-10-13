# Stage-1 runner edits after the frozen run (2026-10-12)

The payload in this directory records `script_blob_sha` `9eeba12d9f668dbe8940f4f25109a3da1cbe75be`.
That blob is the runner that produced this output. It is the file at commit `80d8a9fc76d2` on
PR #8938 (`refs/pull/8938/head` keeps it after the squash merge).

One edit landed afterwards, before merge:

| Edit | Why | Effect on computation |
|---|---|---|
| The module-load repo pin became unconditional: `if str(ROOT) not in sys.path:` was removed, `sys.path.insert(0, str(ROOT))` stays | `tests/test_check_script_import_pinning.py` accepts only an unconditional `__file__`-derived pin as a strong pin | None. It changes which directory wins import resolution, not any function, constant, seed or draw count |

So a rerun at main records a different `script_blob_sha`, while every other field is unchanged. Do not
read that difference as a code change in the estimator.

To check: `git diff 9eeba12d9f668dbe8940f4f25109a3da1cbe75be <main blob> --` shows the pin hunk
and nothing else.

## 2026-10-12 — red-team repairs RT-01/02/04/05 (W4 G-FIX-RT)

The published r1 payload's `script_blob_sha` `9eeba12d9f668dbe8940f4f25109a3da1cbe75be` still names the runner that produced that output. This repair does not re-run that payload and does not edit it. A new run records the new script blob.

RT-01's path was not taken by the published run. In `pullback_stage1_r1/PULLBACK_STAGE1_RESULTS_2026-10-11.json`, every binary configuration including `M3-ALL` and `M3-ALL-C0.1` has `abstained: 0` at h = 5, h = 10 and h = 21 (issued 1001 / 996 / 985). The sensitivity indexer never saw a shorter comparison set. Quantile crossings (Q3-ALL, 1 at h = 5 and 5 at h = 10) are a different family and do not take this path.

What changed in the runner, development only. No frozen constant, seed, horizon, threshold, fold rule, gate or verdict word:

- RT-01. The M3-ALL C=0.1 sensitivity mask and probability are stored on the comparison-set axis (`issued[common]`, `p[common]`). The row is scored on the comparison-set origins where C=0.1 also issued, and that count is `sensitivity.n`. Nothing is imputed. With no abstention the metrics match the previous indexing.
- RT-02. INC native-label metrics use the P-all evaluation-origin union intersected with INC coverage. The early-warning table stays on the comparison set. The horizon record carries `evaluation_origins` and `comparison_set_origins`. With no binary abstention the two counts are equal, which is the published run.
- RT-04. The results note and the JSON, including a BLOCKED artifact, carry manifest version, `subframe_content_sha256`, the prereg git blob, the commit sha, the script blob sha and the test blob sha. A value not established on a blocked path is `UNKNOWN: <reason>`, never omitted.
- RT-05. Each census row gains `typed_exclusions` with `PRE_ENTITLEMENT`, `WARMUP`, `IMMATURE` and `TRAINING_FOLD_THIN`. The existing lowercase keys stay. `TRAINING_FOLD_THIN` is the number of thin blocks summed over horizons, the same count as the entries of `folds.thin_blocks` (a block, not a block times a configuration). It is merged when the payload is assembled. The pre-fit census call records 0. The published run's `thin_blocks` lists are empty, so that count would have been 0.
