# Q14 PREREG amendment A1 — post-audit receipt and consistency fixes (no spec change)

Status: written BEFORE the single post-audit re-run of `evaluate.py --mode compare`
and before reading any new outcome. `PREREG.md` (sha256
`97ec3b0439a46cd9de225a993730114e196c916918c89818a7db70fc32c4ff56`) is unchanged and remains
the frozen specification; `FREEZE.log` is unchanged.

Trigger: independent audit verdict PASS_WITH_FIXES (blockers 0, majors 0, minors 5).

## What does NOT change

Estimand (h = 30 calendar days, calendar365 basis), inputs (`_GSPC.parquet`, `VIXCLS.parquet`,
`_VIX.parquet` at data vintage cdab6268), cohort and attrition rules, train end 2011-12-31,
31-day embargo, controls `[1, IV2, RV_trail]`, augmented `[1, IV2, RV_trail, premium_hat]`,
moving-block bootstrap (block 63, B = 2000, seed 14), Newey-West lags 42, the 5 % practical bar,
the three-part KEEP rule, and the decision-bearing status of trial Q14-T1. No new trial is
opened: this is not a re-specification and spends no additional comparison.

## Changes (code and metadata only)

| Audit item | Change | Can it move a decision number? |
|---|---|---|
| M3 | `evaluate.py` gives the forecast leg its own coverage receipt: `demeaned: true`, `returns: simple_pct`, estimator description (rolling std ddof=0, equal-weight HAR lags 2/5/22/66, x252x30/365). The label leg keeps `realized_coverage("close_to_close")` (`demeaned: false`, log returns). | No: receipts are metadata; `premium_hat` values are unchanged. |
| M4 | `engine/vol_horizon_variance_premium.py`: `trading252` is defined consistently as expected trading days `252*h/365` via a new `HorizonBasis.basis_days` property; `atm_proxy_leg` uses `basis.year_fraction`; `PremiumRecord.annualized_vol_view` uses `basis_days`. A test pins both day counts. | No: the study uses `calendar365` and never calls `atm_proxy_leg`; calendar365 numbers are identical by construction. |
| M5 | Module-level docstring of `evaluate.py` and of the test file assigned to `__doc__` explicitly (it sat after `from __future__` and was not `__doc__`). | No. |
| M1 | Disclosure appended to `RUNS.log` (see below). | n/a |
| M2 | Disclosure appended to `RUNS.log`; a unified diff of every post-audit edit is kept as `POST_AUDIT_EDITS.diff`, and the pre-edit T1 result as `result_compare_T1_original.json`. | n/a |

## Disclosures

- M1: `evaluate.py` changed after the freeze from `793d1ceff662…` (13850 B, 10:16:21Z) to
  `6b65b3b6…3164` (13936 B, 10:18:22Z). The earlier bytes are not recoverable, so the diff and
  reason cannot be reconstructed. The witness copy of `RUNS.log` at 10:18:22Z (850 B) holds
  exactly one entry, the baseline run, already recorded with `evaluate.py` `6b65b3b6…`; no run of
  `793d1c…` is recorded, so `793d1c…` produced no outcome.
- M2: the earlier "docstring-only" module change `149d83b6…` → `c7906612…` cannot be checked
  byte-for-byte (pre-edit bytes unrecoverable). Mitigation: the post-audit re-run below
  re-derives every decision-bearing number from the current module; equality with the T1 record
  is the empirical check that no numeric behaviour moved.

## Expected re-run outcome (stated in advance)

Every numeric field under `result`, `support`, `attrition`, `diagnostics` and `decomposition`
in the re-run `result_compare.json` must equal `result_compare_T1_original.json`
(sha256 `a865f22047c75e90c32e5083077c76bd34cb30fa2f4f25407ead19e011cb674e`) exactly. Only
`inputs_sha256` (new code hashes) and `receipt_example_last_holdout_row.physical_coverage`
(the M3 receipt) may differ. Any other difference is reported in `VERDICT.md` and the T1
original remains the decision-bearing record; the verdict is not re-derived from a changed run.

The baseline mode is not re-run: its code path does not touch any edited function, and its
RUNS.log entry 1 stays accurate for the inputs it records.
