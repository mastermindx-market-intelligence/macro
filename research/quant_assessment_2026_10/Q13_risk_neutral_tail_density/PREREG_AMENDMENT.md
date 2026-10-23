# Q13 — PREREG amendment A1 (implementation tie-downs)

Frozen preregistration: `PREREG.md`, sha256
`e1da1304507c2755c1c8de627965ad98a49d313fdcdd3b5bd72342bd08facd17`
(`FREEZE.log`, frozen 2026-10-09T09:54:31Z). `PREREG.md` is not edited.

**Timing.** A1 was written after the freeze and **before any `evaluate.py`
stage ran**. No evaluation outcome (no identified interval, estimate,
distance, coverage, baseline match or attrition count) had been computed or
read when it was written. `RUNS.log` shows that its first entry comes after
this file existed: the sha256 of this file is recorded in every `RUNS.log`
block.

**Scope.** A1 only pins choices the frozen text left implicit, so that one
fixed program can run. It changes **no** metric, window, cut, grid, band,
split, block, bootstrap setting, gate threshold, effect bar, falsifier
threshold or verdict rule. Where A1 and `PREREG.md` might be read
differently, `PREREG.md` governs.

## A1.1 Basis inputs per date

- `spot` is the first row's `spot` of the selected expiry's rows. This is
  the incumbent `compute_skew` rule.
- `T` is the median of the selected expiry's `T` column (years).
- The SOFR fixing is the last row of `ofr/FNYR-SOFR-A.parquet` (datetime
  index, column `sofr`, percent) whose index date is strictly before the
  snapshot date. If none exists, the date is attrition `no_rate`.
- `F` and `D` follow PREREG §4. **`F` (not spot) classifies OTM legs and
  defines every window and `K*`.**

## A1.2 Rows, expiry and windows

- The expiry is chosen by the incumbent `_nearest_expiry` on all SPY rows of
  the date, before any usability filter. This is the incumbent behavior.
- Usable rows (PREREG §3) are rows with finite `iv` in `[0.02, 2.5]` and
  finite `K > 0`. OTM puts are `is_call == False` with `K < F`. OTM calls are
  `is_call == True` with `K >= F`.
- Duplicate `(K, is_call)` usable rows collapse to the median `iv`. The truth
  window and the estimator C use these collapsed rows.
- A put exactly at `K*` counts toward both truth-support counts
  (`[0.75F, K*]` and `[K*, F)`). This matches the module's chord sets.
- The truncated-support count of "usable strikes" counts distinct collapsed
  OTM strikes in `[0.95F, 1.10F]`.

## A1.3 Estimator details

- **C:** `fit_smile(k, iv, T, lam, m)` on the collapsed truncated rows, then
  `q_tail_probability(smile, basis, K*, 1601)`.
- **B1:** input is the **raw** (pre-collapse) usable OTM rows in the
  truncated window, passed unchanged to the incumbent
  `_iv_selection_at_delta`.
  - Put leg: target `-0.25`, `want_call=False`. Call leg: target `0.50`,
    `want_call=True`. These are the incumbent constants.
  - The smile is `two_point_smile(ln(K_put/F), iv_put, ln(K_call/F),
    iv_call, T)`: Lee-capped and flat if the two `k` coincide (PREREG §8).
  - If either selection returns `None`, B1 fails and the date is attrition
    `estimator_failure`.
  - Known property, disclosed and not changed: the Lee cap
    `sqrt(2|k|/T)` is asymptotic. Within `|k| < iv^2 T / 2` of `k = 0` it can
    bind on the right wing when the 50Δ call sits at `k ≈ 0`. At 30 days this
    region is a few basis points of `F` (at most about 1–2 grid nodes) and
    lies on the right side, away from `K* = 0.90F`.
- **B0:** `flat_smile(iv_call_50Δ, T)`. It is a constant smile with no Lee
  cap, because a flat smile has no data range and the cap would otherwise
  bind near `k = 0`.
- An estimator whose code raises, or returns a non-finite `q_hat`, fails.

## A1.4 Training selection

- **Scoring set:** TRAIN dates that pass the truth-support and
  truncated-support gates (PREREG §12).
- A configuration that yields a non-finite `q_hat_C` on any scoring date
  scores `+inf`.
- Ties mean scores equal within `1e-12` absolute. Ties break to the larger
  `lam`, then the larger `m` (PREREG §9).
- B1 and B0 have no parameters and play no part in selection.

## A1.5 TEST comparison and bootstrap

- The supported TEST set is the intersection in PREREG §12, using the
  selected configuration.
- Coverage and median relative width for the falsifier are computed over
  supported TEST dates. Attrition is `1 - n_supported/13`.
- **Bootstrap:**
  - All 4 TEST blocks (W30–W33) are resampled with replacement, B = 4000,
    `numpy.random.default_rng(13013)`.
  - Each draw's statistic is the pooled mean of the per-date
    `dist_C - dist_B1` over the supported dates of the drawn blocks. A draw
    with zero supported dates is dropped and counted.
  - The CI uses `numpy.quantile` at 0.025 and 0.975 (default linear method).
- **Block sign count:** for each block with at least one supported date, the
  sign of its mean diff is counted. Values within `1e-12` of 0 count as 0.

## A1.6 Module checks

- The forward check uses a relative tolerance of `1e-3 * F`. It runs on the
  raw prices **and** the repaired prices, and `forward_ok` requires both.
  The reason: the repair's level shift enforces `C(K_0) >= D (F - K_0)` and
  would otherwise hide a basis mismatch.
- `rn_tail_report` withholds the point estimate and the perturbation
  interval under `PRICE_BOUNDS_ONLY` (PREREG §13).
  - For the §14.2 diagnostic, the harness also calls
    `perturbation_interval` directly (100 uniform-in-band draws, seed 13013,
    1× band, selected configuration) for every TEST date with a full-chain
    report. This is recorded as diagnostic only. It is never a point
    estimate.
- §14.2 "raw butterfly negativity" is reported two ways:
  - `static_arbitrage_report` on the call-equivalent mid prices at the quoted
    full-window strikes (the vendor-iv surface itself);
  - the smile-grid `raw_negative_mass` from the module report.

## A1.7 Diagnostics scope

- §14.1 band scaling uses the fixed supported TEST set from the primary
  comparison. Only `[L, U]` changes with scale; `q_hat` does not.
- §14.3 uses collapsed usable rows of **both** legs at the selected expiry
  (not only OTM rows). Strikes with both a call and a put are ranked by
  `|K - F|`, and the 3 nearest are used. It is reported for every date with
  at least one such strike, per split.
- §14.4 truncation cuts `{0.93, 0.95, 0.97}` use the selected configuration
  on TRAIN only. Each cut moves the estimator window's lower edge (upper edge
  `1.10F` unchanged), and the gates are recomputed for each cut.
- §14.5 uses the supported TEST set, the same three smiles, and truth-window
  put bands at `K = 0.95F`.

## A1.8 Baseline and absence stages

- Baseline: `compute_skew` per date on all SPY rows of that date's chain
  file, matched to `options_skew/snapshots.parquet` rows with the same `date`
  string, `underlying == "SPY"` and `source == "polygon_gex"`. A field
  matches if `|a - b| <= 1e-4 + 1e-9`.
- Absence: a scan of `*.py` files under `engine/`, `scripts/` and `tests/` of
  the scan root (default: the pristine `_base` snapshot when it exists,
  otherwise the repository root). The two Q13 files are excluded. The scan
  is case-insensitive for these regexes:
  - `breeden`
  - `litzenberger`
  - `risk[-_ ]?neutral[-_ ]?(density|distribution|pdf)`
  - `state[-_ ]?price[-_ ]?density`
  - `\brnd\b`
  - `rn[-_]density`
  - `tail[-_ ]density`
  - `implied[-_ ](density|distribution|pdf)`

  Hits are listed with path and line number for manual classification.

## A1.9 Run mechanics

- The UTC stamp comes from `date -u +%Y-%m-%dT%H:%M:%SZ` and is passed in as
  `--utc-stamp`. The harness reads no wall clock.
- The incumbent `engine/options_skew.py` is hash-checked against PREREG §5,
  then loaded from its file path with an in-memory `lib`/`lib.config` stub
  (PREREG §15). `sys.dont_write_bytecode` is set.
- The module under test is also loaded from its file path, and its sha256 is
  recorded in `RUNS.log`.
- The chain columns `K`, `T`, `iv` and `spot` are stored as float32. The
  harness casts them to float64 before any arithmetic. The incumbent
  functions get the raw frame unchanged.
- Exit codes:
  - `0`: success.
  - `1`: crash. Logged, with at most 2 reruns, each recorded here.
  - `2`: PREREG hash mismatch.
  - `3`: input hash mismatch, or a missing input.
  - `4`: stop-rule refusal. Either a `compare` run already finished with
    exit 0, or 3 `compare` attempts have already crashed (PREREG §13).

# A2 — baseline ledger census (added after RUN 2)

**Timing.** A2 was written **after `RUNS.log` RUN 1 (absence) and RUN 2
(baseline)** and **before any `compare` run**. At that point no primary or
diagnostic comparison outcome (identified interval, estimate, distance,
coverage, attrition or bootstrap) had been computed or read. The only
outcomes seen were RUN 1's absence hits and RUN 2's baseline result:
`ledger_row_missing` on all 28 dates.

**What RUN 2 showed and why A2 exists.** RUN 2 ran the PREREG §15 rule
unchanged and reported no `polygon_gex` SPY ledger row on any of the 28
chain dates. A read-only look at `options_skew/snapshots.parquet` (same
sha256 as PREREG §5) found:

- all 8 `polygon_gex` SPY rows carry weekend `date`/`asof` values;
- every SPY row on a chain trading date has `source == thetadata`.

A2 adds one **diagnostic** stage that records this census reproducibly in
`RUNS.log`. It does not change the §15 rule or its result.

**`--stage baseline_census`** (diagnostic only):

- Writes `results/baseline_ledger_census.json`.
- Lists every SPY ledger row with `source`, `date`, `asof`, weekday name and
  whether a retained chain file exists for that date.
- Counts the chain dates that have a ledger row, per source.
- Records each chain file's distinct `asof` values.
- For chain dates that have a `thetadata` row, reports `|compute_skew - row|`
  for `otm_put_iv`, `atm_call_iv` and `skew`. This is labelled a
  **cross-source diagnostic**: those rows were built from a different vendor
  chain, so the comparison is not a reproduction and has no pass/fail
  threshold.
- It changes no verdict rule. PREREG §15 still governs: a baseline that
  cannot be reproduced is a limitation.
- The `compare` stage code, its constants and its stop rule are unchanged
  by A2. Only the stage table and the new function are added, and
  `evaluate_sha256` in `RUNS.log` records the new file hash.
