# Q13 — Risk-neutral tail-density estimation with quote-uncertainty bounds — VERDICT

**VERDICT: `INSUFFICIENT_DATA`**

The verdict was fixed by the frozen `PREREG.md` §0 before any outcome was
computed. The single proxy comparison below cannot change it. Every proxy
number in this file is labelled **PROXY — not admitted surface**.

**Measure.** Every probability in this directory is a **risk-neutral (Q,
pricing-measure) probability**. None is a physical (P) probability, crash
odds or a forecast. `engine/options_rn_tail_density.to_physical` raises
`MeasureError` by design.

## 1. Exact missing inputs (PREREG §0)

| Key | Missing input | What the licensed retained data at `cdab6268` holds instead |
|---|---|---|
| M1 | Per-strike executable quotes (bid/ask or NBBO) on a full chain snapshot | `data/polygon_gex/chains/*.parquet` (28 dates) has vendor `iv`, `delta`, `gamma`, `oi`, `volume`, `K`, `T`, `spot` only. It has no bid, ask, mid or price column. |
| M2 | A qualified forward/discount basis with dividends (the Q12 basis) | SOFR only (`data/ofr/FNYR-SOFR-A.parquet`). There is no dividend or borrow feed, so `q = 0` is a declared bias. |
| M3 | European exercise, or a Q02-qualified American-exercise adjustment | SPY/QQQ/IWM/DIA chains only: American, physically settled. No SPX/XSP/NDX. |
| M4 | A Q01-qualified arbitrage-checked surface | No incumbent exists in `_base`. Q13 must not read another brief's directory. |

The quote band used throughout is a **declared** implied-vol half-width of
`δ(k) = 0.005 + 0.05|k|`. It is not an observed spread, because M1 is
missing.

## 2. What was built

### Module: `engine/options_rn_tail_density.py`

Research reference only (`RESEARCH_ONLY = True`). Nothing imports it, and
nothing wires, schedules or gates on it. It provides:

- **One `ForwardBasis`.** `F` and `D` are shared by pricing, parity, the
  forward/moment check and the Breeden–Litzenberger derivative.
- **Static-arbitrage audit and repair:**
  - Arbitrage audit (butterfly, monotonicity, slope floor `-D`, price bounds).
  - Minimal repair: PAVA on slopes clipped to `[-D, 0]`, plus a level shift.
- **Breeden–Litzenberger density** (`f_Q = D^-1 C''`), with:
  - mass accounting: total, negative before and after repair, below and
    above the quoted range, extrapolated, and grid truncation left and right;
  - a forward check on both the raw and the repaired prices.
- **Reintegration** of call prices at quoted strikes, with an excess against
  the declared band.
- **Identified bounds `[L, U]`** for `Q(S_T ≤ K*)`, built from band-edge
  chords.
- **Perturbation interval:** uniform-in-band quote draws with a fixed seed.
- **`classify_identification`** returns `FULL_DENSITY` or
  `PRICE_BOUNDS_ONLY`. `rn_tail_report` withholds the point estimate and the
  perturbation interval under `PRICE_BOUNDS_ONLY`.

### Tests: `tests/test_options_rn_tail_density.py`

27 hermetic tests, all passing, covering the six acceptance requirements (see
`REQUIREMENTS.md`).

## 3. Incumbent refresh and absence (RUN 1)

`evaluate.py --stage absence` scanned 6,384 `.py` files under `_base`
`engine/`, `scripts/` and `tests/`. It found 11 hits, and none is an RN-density
incumbent:

- `rnd` local variables in `engine/flow_velocity.py:324-326`.
- `rnd` local variables in `scripts/research/ptt_w1_persistence_of_fit.py:482-484`
  and `scripts/research/ptt_w1_timing_regrade.py:403-405`.
- Comments about the Kalshi "implied distribution" in `scripts/collect.py:196`
  and `scripts/research/mri_miss_anatomy.py:1117`.

Output: `results/absence.json`, sha256 `9cb7598a…881e4a`. The full hash is in
`RUNS.log`.

## 4. Baseline reproduction (RUN 2 and RUN 3)

`compute_skew` (the incumbent `engine/options_skew.py`, sha256
`8f68ad06…b38dce`) ran on **28/28** chain dates. No reproduction against the
stored ledger was possible.

**The PREREG §15 rule found 0 matches.** It wants a
`source == polygon_gex` SPY row in `options_skew/snapshots.parquet` on the
same date as the chain, and all 28 dates returned `ledger_row_missing`.

**The diagnostic census (RUN 3, amendment A2) shows why.** It changes no
rule. It found:

- All 8 `polygon_gex` SPY rows carry **weekend** dates (Sunday ×6,
  Saturday ×2; 2026-06-21 to 2026-07-26).
- None of those 8 dates has a retained chain file.
- Trading-day SPY rows are `source == thetadata`, and they cover 25 of the 28
  chain dates.
- Cross-source median `|compute_skew − thetadata row|`:
  - `otm_put_iv` 0.0034
  - `atm_call_iv` 0.0061
  - `skew` 0.0086

  This is a different vendor chain, so it is **not** a reproduction and has
  no pass/fail threshold.

**Conclusion.** The absence of a same-source stored baseline is proven. Under
PREREG §15 this is a limitation, not a verdict input.

## 5. The single dependence-aware proxy comparison (RUN 4) — PROXY — not admitted surface

| Item | Value |
|---|---|
| Question (H1) | Does the smile-based estimator C extrapolate `Q(S_T ≤ 0.90F)` closer to the identified interval `[L, U]` than the incumbent two-point skew B1? |
| Split | Chronological: TRAIN W25–W29 (15 dates), TEST W30–W33 (13 dates) |
| Fitting | The `(λ, m)` grid was fitted on TRAIN only |
| Selected configuration | `λ = 0.1`, `m = 12`. All 20 configurations scored a mean distance of 0 with coverage 1 on TRAIN, so the preregistered tie-break (larger `λ`, then larger `m`) made the choice. The grid did not discriminate. |
| Honest N (TEST) | 13 dates in 4 week-blocks, and 5 distinct expiries (2026-08-21, 08-28, 08-31, 09-04, 09-11). The W32 block holds a single date. |
| Attrition | 0 on TRAIN and on TEST (13/13 supported). Support per date: TEST left-truth strikes 22–66 (median 33); truncated-window strikes 86–115. |
| Dependence | Week-block bootstrap: 4 blocks resampled with replacement, `B = 4000`, seed 13013, 4000 valid draws |
| Primary Δ = mean(dist_C − dist_B1) | **0.0**, CI95 **[0, 0]**. Block signs: 0 below, 4 at 0, 0 above. |
| Effect bar | CI upper < 0 **false**; mean C ≤ 0.75 × mean B1 true (0 ≤ 0); improvement ≥ 0.002 **false**. **H1 not supported on the proxy.** |
| Descriptive C vs B0 (flat 50Δ smile) | Δ = −0.00112, CI95 [−0.00218, −0.00034]. Block signs: 3 below, 1 at 0. Coverage: B0 0.538, B1 1.0, C 1.0. |
| Proxy falsifier (PREREG §13) | **FIRES** on median relative width 1.588 > 0.5. C coverage 1.0 (not below 80%); attrition 0 (not above 50%). |
| Output restriction | **`PRICE_BOUNDS_ONLY`.** The module's `rn_tail_report` emits no point estimate and no perturbation interval for the RN tail probability. The harness still computes the per-date C/B1/B0 values in `results/per_date.csv` (`q_C`, `q_B1`, `q_B0`) as comparison inputs for the H1 distance metric. They are PROXY and diagnostic only, never a reported tail estimate. |

**Reading.** On TEST, `[L, U]` for `Q(S_T ≤ 0.90F)` runs from about
0.004–0.012 at the bottom to about 0.044–0.097 at the top. The interval is
about 1.6× its own midpoint wide. Both C (0.014–0.045) and B1 (0.008–0.046)
sit inside it on every TEST date, so H1 cannot be discriminated at this
quote uncertainty. These C and B1 ranges are harness comparison values
(PROXY, diagnostic only). They are not module output, and they are not RN
tail estimates. This is an **indeterminate / negative** result, and it
favours neither estimator. B0, a flat smile, falls below `L` on 6 of 13 TEST
dates: a flat smile under-prices the left tail, as expected.

Outputs (sha256 in `RUNS.log`):

- `results/per_date.csv`
- `results/training_grid.csv`
- `results/compare_summary.json`
- `results/diagnostics.json`

The stop rule now refuses any further `compare` run with exit 4.

## 6. Descriptive diagnostics (PREREG §14; these cannot change the verdict) — PROXY

### §14.1 Band scaling (TEST, fixed supported set)

Coverage stayed 1.0 with 0 inconsistent intervals at every scale.

| Band scale | Median width | Median relative width |
|---|---|---|
| 0.5× | 0.0368 | 1.272 |
| 1× | 0.0595 | 1.588 |
| 2× | 0.0849 | 1.855 |

Even half the declared band leaves the tail interval wider than its
midpoint.

### §14.2 Full-chain module report (TEST, 13 dates)

- **Identification.** 13/13 `PRICE_BOUNDS_ONLY`, reason
  `identified_interval_too_wide`. No errors.
- **Quoted vendor-iv surface (call-equivalent mids).**
  - Arbitrage-free on **0/13** dates.
  - Per date (median): 190 nodes, 39 butterfly violations (range 27–48), 4
    monotonicity violations (2–13).
  - 0 slope-floor violations and 0 price-bound violations.
  - Negative atom mass: median 1.71 (0.79–3.38).
- **Smile-based density (selected configuration).**
  - Total mass 1.0.
  - Negative mass after repair ≤ 7.6e-14.
  - Raw negative mass median 9.1e-6; raw butterfly violations median 1
    (0–3).
  - Repair: max change median 1.86e-6, which is 6.6e-6 of the median band
    half-width. Level shift 0.
- **Mass accounting.**
  - Extrapolated mass median 0.00213 (0.00086–0.00318). Almost all of it
    lies below the quoted range; above the range it is about 1.9e-6.
  - Grid-truncation mass: left median 0.00053, right about 0.
- **Forward check.** Passes on 13/13 dates, for both raw and repaired
  prices, at `1e-3·F`.
- **Reintegration.** Within the declared band on **0/13** dates.
  - A median of 92 of 190 quoted strikes fall outside.
  - The maximum excess is a median of 3.30 band half-widths (2.55–4.55).
  - Tolerance is `1e-6·F` (about 7.4e-4).

  A smoothed single smile cannot pass through the vendor-iv quotes within
  the declared band. One plausible contributor is the call/put iv gap near
  `F` (§14.3), which already exceeds the 0.005 at-the-money half-width. That
  gap points back to M2 and M3. This is a hypothesis, not a measured
  attribution.
- **Perturbation interval** (direct call, diagnostic only; all 13 dates):
  - 1300/1300 finite draws.
  - Width median 0.00117 (range 0.00096–0.00150), measure Q.
  - Example, 2026-07-20: the perturbation interval is 0.0338–0.0353 (width
    0.00148), while `[L, U]` is 0.0100–0.0822 (width 0.0723). This interval
    comes from a direct harness call to `perturbation_interval`, made for
    this diagnostic. `rn_tail_report` does not emit it.

  `[L, U]` is a median of **46×** wider than the perturbation interval
  (range 37–66×). Model-level perturbation of a smoothed smile badly
  understates the quote-level identification uncertainty. That is why `rn_tail_report` withholds both
  the point estimate and the perturbation interval under
  `PRICE_BOUNDS_ONLY`, rather than emitting a false-precision number.

### §14.3 ATM call/put iv gap

Median `|iv_call − iv_put|` at the 3 strikes nearest `F`:

- TRAIN 0.0108
- TEST 0.0136 (maximum 0.060)

This is a forward-basis or exercise inconsistency, consistent with M2 and M3.

### §14.4 TRAIN truncation cuts {0.93, 0.95, 0.97}

| Estimator | Mean distance at 0.93 / 0.95 / 0.97 |
|---|---|
| C | 0 / 0 / 0 |
| B1 | 0.00033 / 0.00033 / 0.00039 |
| B0 | 0.00178 at each cut |

### §14.5 Secondary strike `0.95F` (TEST)

All three estimators fall inside `[L, U]` on 13/13 dates. Median relative
width is 1.33. The estimators see these quotes, so this is not an
extrapolation test.

## 7. Limitations

1. **Sequencing dependency.** Q13 comes after Q01, Q12 and Q02. Their
   admitted outputs (surface, basis, American adjustment) were unavailable
   and were not read. The proxy uses vendor iv, SOFR with `q = 0`, and
   American SPY options instead, so it is not the admitted object.
2. **Declared band, not an observed spread** (M1). Every `[L, U]` scales with
   that declaration (§14.1).
3. **`q = 0` bias** (M2). Ignoring dividends overstates `F` by roughly the
   dividend yield times `T`.
4. **American exercise** (M3). Early-exercise premium is not removed. Puts
   are mapped to call-equivalents by European parity.
5. **Coarse dependence correction.** There are 4 TEST blocks, one with a
   single date, so the bootstrap CI has few distinct resamples. The primary
   CI is degenerate at [0, 0] because every per-date difference is 0.
6. **Selection was all ties.** Training could not discriminate between
   configurations, so `(λ, m)` is a tie-break artefact.
7. **float32 inputs.** Chain columns are stored as float32 and cast to
   float64 (amendment A1.9).
8. **The classifier ignores reintegration.** `classify_identification` does
   not use the reintegration result. On the proxy, the reintegration failure
   (0/13 within band) did not trigger `PRICE_BOUNDS_ONLY` on its own; the
   relative-width rule did. Making reintegration failure a bounds-only
   trigger would be a contract change for a future preregistration. It was
   not made here, because the frozen §13 classifier list omits it.
9. **Amendment A2 was written after RUN 2.** It adds only a diagnostic census
   stage and changes no rule. The `evaluate.py` sha256 changed between RUN 2
   (`d43d7edd…`) and RUN 3 (`7921319d…`). The `compare` code, its constants
   and its stop rule are unchanged. A2 was appended to the same
   `PREREG_AMENDMENT.md` file as A1, so the file's sha256 also changed.
   The custody record is below (Provenance).
11. **The PREREG anchor in `evaluate.py` is the witness log, not a code
    constant.** `evaluate.py` refuses to run when `PREREG.md` does not match
    the sha256 in `FREEZE.log`, but it does not hard-code that sha256, so
    editing both files together would pass its check. The frozen sha256
    `e1da1304…` is independently recorded in `FREEZE.log`, in every
    `RUNS.log` entry, in `_handoff/MANIFEST.json` and in the PR body. The
    code was not changed after the audit: `compare` runs once (exit-4 stop
    rule), so any edit would leave the shipped `evaluate.py` unmatched by
    RUN 4's recorded sha256 `7921319d…`.
10. **Baseline.** No same-source stored baseline exists for any chain date,
    so B1 is reproduced only as code, not against a stored ledger value.

## 8. Standing kills, holds and scope

- No signal, score, rank, size, gate or escalation is produced. No language
  model originated any number. Nothing is wired.
- The work respects:
  - `DNR:KILL-OUTCOME-AUDITION`
  - `DNR:KILL-LLM-ORIGINATION`
  - `DNR:KILL-FUSED-COMPOSITE`
  - `DNR:KILL-POSITIONING-FUSION`
  - `DNR:KILL-REGIME-SCORECARD`
  - `DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR`
  - `DNR:KILL-CAUSAL-DAG-ALPHA`
  - `DNR:HOLD-PSS-AF1-FINRA`
  - `DNR:HOLD-PSS-CD1-CROWDING`
- Historical charm, DOI and skew nulls remain negative evidence. The October
  options research exception grants no production authority.
- Q13 is not MAS-260 physical LOD/HOD/close forecasting. It is not a Risk
  Radar crash probability, and not an options UI.

## 9. What would change the verdict

A new preregistration on admitted inputs:

- M1: full-chain bid/ask or NBBO snapshots;
- M2: the Q12 forward/discount basis with dividends;
- M3: a European index chain, or the Q02 American adjustment;
- M4: the Q01 arbitrage-checked surface.

It should also add reintegration failure as a `PRICE_BOUNDS_ONLY` trigger.
Until then, the honest output of this module on retained data is identified
Q price bounds only.

## Provenance

| Item | Value |
|---|---|
| `PREREG.md` sha256 | `e1da1304507c2755c1c8de627965ad98a49d313fdcdd3b5bd72342bd08facd17` (`FREEZE.log`, 2026-10-09T09:54:31Z) |
| `PREREG_AMENDMENT.md` sha256 | `dad5c7e6971178ce5619f18fe259380be2525629dadff2dbdcdffcb09c66a5ba` (A1 + A2, 10185 B; RUN 3 and RUN 4) |
| A1-only amendment (custody) | The file's first 8259 B are A1 exactly as RUN 1 and RUN 2 hashed it: sha256 `7fd130c2140faef6317b97823f7ce8be553efd599ef1637b3371e1c919eac465`. A2 is the appended remainder (append-only); no A1 byte changed. |
| Module sha256 | `27da892314b6c9b53fb32637f9be60f5a53e43d562634bf3b2d0c6f5d2e54a62` |
| `evaluate.py` sha256 | `7921319d3e53f7237b9f2e15ad9adcf91e120dac6dded4a1f28ff21043a191be` (RUN 3 and RUN 4) |
| Data | `macro-main/data` at `cdab6268`, read-only. Per-file input sha256 values are in `RUNS.log`. |

Mastermind procedure docs (read-only, commit unknown; hashed at write-up):

- `docs/sol_skills/INDEX.md` — `608aebc84a106f4e3c687f020a7f0e69af88f38e014d4664a376e2be2ddfa220`
- `docs/sol_skills/ACTIVE_EXECUTION.md` — `fb6a89101ad75512b971b2457f3f419704eae136afa28bac5a646ae69a6ed0dc`
- `docs/sol_skills/SESSION_RELIABILITY.md` — `817366c630abe31308a09c18caa5249ea4c39c83d74c130496079bb151283076`

Served model: Opus 5.5 (model ID `claude-opus-5-5`), Q13 AUTHOR seat.
