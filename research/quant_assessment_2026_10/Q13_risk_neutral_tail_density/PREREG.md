# Q13 — Risk-neutral tail-density estimation with quote-uncertainty bounds — PREREGISTRATION

Status: FROZEN at the timestamp recorded in `FREEZE.log`, sha256 of this file
recorded there. Never edited after the freeze; changes go to
`PREREG_AMENDMENT.md`.

Author seat: Q13 AUTHOR (served model Opus 5.5, model ID `claude-opus-5-5`).
Code base: `_base` snapshot at `d252f919`. Data vintage: `macro-main/data` at
`cdab6268` (read-only licensed retained data).

Module under test: `engine/options_rn_tail_density.py` (research reference,
`RESEARCH_ONLY = True`, never wired). Harness: `evaluate.py` in this
directory.

---

## 0. Pre-declared verdict rule (written before any outcome is read)

The brief asks for a risk-neutral (Q) tail density estimated from an
*admitted* option surface. An admitted surface needs four inputs, and
schema inspection before this freeze showed that the licensed retained data
at `cdab6268` lacks all four:

- **M1 — per-strike executable quotes (bid/ask or NBBO) on a full chain
  snapshot.** `data/polygon_gex/chains/*.parquet` (28 dates) carries only
  vendor `iv`, `delta`, `gamma`, `oi`, `volume`, `K`, `T`, `spot`. It has no
  bid, ask, mid or price columns. `data/thetadata_eod` holds manifests only.
  `data/flow_signals/ledger.parquet` carries NBBO statistics for sparse flow
  prints, not a full-chain quote snapshot. A schema scan of 25,246 parquet
  files found no other per-strike option quote column.
- **M2 — a qualified forward/discount basis that includes dividends (the
  Q12-qualified basis).** No dividend or borrow feed exists for the chain
  underlyings. The only rate input is SOFR (`data/ofr/FNYR-SOFR-A.parquet`).
- **M3 — European exercise, or an American-exercise adjustment qualified by
  Q02.** The chain universe holds SPY/QQQ/IWM/DIA (American, physically
  settled ETF options). No SPX/XSP/NDX (European, cash-settled) chain is
  present.
- **M4 — a Q01-qualified arbitrage-checked surface.** No such incumbent
  exists in `_base`. Q13 is sequenced after Q01/Q12/Q02, and this brief must
  not read another brief's directory.

**Therefore the verdict is `INSUFFICIENT_DATA`, naming M1–M4, whatever the
proxy comparison below shows.** The proxy comparison is the single
dependence-aware empirical comparison the commission requires. It is labeled
`PROXY — not admitted surface` everywhere and cannot promote, rank, size,
gate or wire anything. A later re-run on admitted inputs needs a new
preregistration.

## 1. Estimand

The risk-neutral left-tail probability

    q*(d) = Q_d( S_T <= K* ),   K* = 0.90 * F_d

at one snapshot `d`, for the cohort expiry `T` (Section 3), together with
its quote-uncertainty interval. The Breeden–Litzenberger identity gives
`Q(S_T <= K) = 1 + D^{-1} dC/dK`, with the discount factor `D` and forward
`F` taken from one `ForwardBasis` object.

Secondary (descriptive only): the same quantity at `K = 0.95 F`.

`q*` is a **pricing-measure quantity**. It is not a physical (P) probability,
not crash odds, and not a forecast (Fed note 2014 [L12]; Malz 2014 [L11]).
Q-to-P conversion needs a pricing-kernel model, and this brief never
attempts it. The module raises `MeasureError` if asked.

## 2. Unit, input clock and output clock

- **Unit:** one (snapshot date, expiry) surface for one underlying.
- **Input clock:** the chain file's snapshot (`asof` column, one file per
  date). The SOFR fixing is the latest one dated **strictly before** the
  snapshot date.
- **Output clock:** the same snapshot. **There is no forward outcome
  window.** The quantity is a same-clock price functional. No realized-return
  or realized-crash evaluation is done or implied, because Q is not P.

## 3. Cohort, tenor and settlement class

- **Underlying:** SPY only. Settlement class is ETF option, American exercise,
  physically settled (the "American-proxy"; see M3).
- **Tenor:** one expiry per date, chosen by the incumbent rule
  `engine.options_skew._nearest_expiry`: the listed expiry whose tenor
  (`T*365`) is closest to 30 calendar days among expiries of at least 7 days.
- **Dates:** all 28 polygon chain snapshot dates (Section 5).
- **Legs:** out-of-the-money only. Puts have `K < F`; calls have `K >= F`.
  Usable rows have finite `iv` in `[0.02, 2.5]` and finite `K > 0`.
  Duplicate `(K, is_call)` rows collapse to the median `iv`.
- **Windows:**
  - Truth window: OTM puts with `K/F` in `[0.75, 1.00)`.
  - Estimator (truncated) window: OTM legs with `K/F` in `[0.95, 1.10]`.
  - Full-chain diagnostic window: OTM legs with `K/F` in `[0.75, 1.25]`.

## 4. Basis (one basis for pricing, normalization and moment checks)

- `r = SOFR/100`. The SOFR fixing is in percent, and is treated as a
  continuously compounded rate. The declared approximation bias is below
  1bp·T.
- `q = 0`. This is a **declared bias**: SPY's dividend yield is about 1.2%,
  so `F` is overstated by about 0.1% at 30 days. This is part of M2.
- `T` is the chain's `T` column (years).
- `F = spot * exp((r - q) T)` and `D = exp(-r T)`.
- Every price, parity conversion, density normalization and forward/moment
  check uses this same `(F, D)` (requirement 3).

## 5. Source vintages (sha256)

Data root: `/Users/chriswong/Documents/Cluade/macro-main/data`, vintage
`cdab6268`.

`polygon_gex/chains/`:

| file | sha256 |
|---|---|
| 2026-06-15.parquet | b3b64a15a058f60fd3f83e5be23b9c500b720ce9719f2acf67068826fdc98f21 |
| 2026-06-17.parquet | 3b764b176fadd2c0d9018df4b572cd92aa33eba8262c94f8b73c9321e08fc5d2 |
| 2026-06-18.parquet | 91dfe4034235a5d47544ea8ecf69692593a6a1a9224598496b0c256856e561b5 |
| 2026-06-24.parquet | 3425ac28473f3ec53690284bc5b969e33cab2e60dfb7d2ab3a6df0f9b7ccf846 |
| 2026-06-26.parquet | b295c88c375e92809f16e5d0a47ade28ab64ffa47d1bd61defe90255769b504d |
| 2026-06-30.parquet | 475ff75749f18d9250f257af7c8506dc78058b6efe785e55cbd2f6364071c450 |
| 2026-07-01.parquet | 2e5ec91417d811d7282a8de69134d39a19800af4172c25f33849e5de2e786aa7 |
| 2026-07-02.parquet | 27c8f4c9768480b892a3f377e37510b3a1a23156b5389212e1a5b557b7288f06 |
| 2026-07-07.parquet | 0f37eaa140c4a6ad4d1576b93938ac7c829c955e096aee5804ec8c821bacba9d |
| 2026-07-08.parquet | 0e5086480bbd38e0b862c784ee85c6879ad90fdc48432d5c6046d7896366122e |
| 2026-07-09.parquet | f80811096a2e0a5cd6df506c5ada7f600cb9e9901618b4b26302b5fe8d89678c |
| 2026-07-10.parquet | b48992f0b89f58c4b5f9706a89aa51b5b8e33fe41a02a43174fd47bc8a289fe4 |
| 2026-07-13.parquet | e3f4f5bc20863d2add0c7f075f1604b646f4bcba6d5a33d4c98105da9019effa |
| 2026-07-15.parquet | 0dbb288cd3f98c7d0dc4b6139239ff57e6724dc70b5831f04f5046433cd83cf0 |
| 2026-07-17.parquet | 846f60b395c0c16a9d4f45f0c371e05aceefba5b120c7f632e08bfd92ee98c7f |
| 2026-07-20.parquet | 0b5e48eb981fe04a90035f2992444607b59467e085717bef9e948367a75ec25e |
| 2026-07-21.parquet | 22951e0788fd642d49e5096203f3cc99402c70c87c0a716c412a8924dad8f850 |
| 2026-07-22.parquet | d6edd7c50b149857803940894d862dfeecb5c683e56650962ccfc6a18d715deb |
| 2026-07-23.parquet | f018d9506be417001937bee33a95d4007417b3d8ad5919c5be9d9f1bf61e14bf |
| 2026-07-24.parquet | a263ed1a46c52f44d967b4b6ba5cbd69a89b861c3c29262ad3bebdc7411c3117 |
| 2026-07-27.parquet | 7023fde67dda28bd3ab7d4c430e3ca75936f7bad151a514cb22926a962825eb8 |
| 2026-07-28.parquet | dcffd24ecb49d4fb0fd11b19d86fc73b129564d38919256a353de1de97fb408a |
| 2026-07-29.parquet | a77f545f68e2f90674bc32a55c3c94d57b01c5b0c0b30dae140e068176822c07 |
| 2026-07-30.parquet | f941d5ebd512b3df356daaac88365c5892bf1176d7845f8c99dc67609bd30636 |
| 2026-08-06.parquet | d4a486c94b274e9419d09639e51f25d1c4fc1cde759612ab14fc536a05577d92 |
| 2026-08-10.parquet | c2488d33c7ff96c7ffeaa7386fb494794ef13d73998f1187c8b14ca1296ac267 |
| 2026-08-12.parquet | 68782399b571feafa34bdeb5171c4da03f71fa72b57f17e608d63c6d2390153f |
| 2026-08-13.parquet | 846a8f144a3b6315cebabdec7c7eb85d81ea70a2d2a6b064b3beacb0dc84cc28 |

Other inputs:

| file | sha256 |
|---|---|
| ofr/FNYR-SOFR-A.parquet | 02dca610d9d4857a002beee07aef0a3f96af943131efba5d0861c0d5b1ddc620 |
| options_skew/snapshots.parquet (baseline reproduction only) | 18a16c9f72a3f6ac1548a22efaaebaa348265fe783d93ca29da1a8d4c2a53b56 |
| `_base/engine/options_skew.py` (incumbent code) | 8f68ad06c29ff9e05d6f4a710912b12a8523344d3b84a22524867e4711b38dce |

`evaluate.py` re-hashes every input before use and refuses on any mismatch.

## 6. Declared quote band (stand-in for M1; no observed spreads exist)

Implied-vol half-width

    delta(k) = 0.005 + 0.05 * |k|,   k = ln(K/F)   (vol units)

This gives a price band `[Black76(iv - delta), Black76(iv + delta)]`, with
the lower vol floored at 1e-4. A put band converts to a call-equivalent band
by parity on the same basis: `C = P + D (F - K)`.

The band is an assumption, not an observation. Its scaling is reported
descriptively at 0.5×, 1× and 2×; the verdict ignores it.

## 7. Model-free identified interval ("truth" for the proxy comparison)

For each date, compute the no-arbitrage identified interval `[L, U]` for
`Q(S_T <= K*)` from the truth-window put bands (call-equivalent).

- Left chords run over `K_a < K_b <= K*`. They include the exact anchor
  `(K = 0, C = D F)`.
- Right chords run over `K* <= K_c < K_d`.

        L = 1 + max_{left chords} (C_lo(K_b) - C_hi(K_a)) / (K_b - K_a) / D
        U = 1 + min_{right chords} (C_hi(K_d) - C_lo(K_c)) / (K_d - K_c) / D

- Both are clipped to `[0, 1]`.
- With no left chord, `L = 0`; with no right chord, `U = 1`.
- `L > U` means the band is inconsistent with static no-arbitrage. The date
  is then counted as **arbitrage-inconsistent attrition**.

## 8. Hypotheses, competitors and protocol (wing-truncation extrapolation test)

Each estimator sees only the truncated window (`K/F >= 0.95`) and must
extrapolate to `K* = 0.90F`. Its estimate `q_hat` is scored against the
interval `[L, U]` built from the held-out wing quotes.

All three estimators produce prices on one grid and pass through the same
module pipeline:

- grid of 1601 nodes, uniform in K, on
  `[F * min(exp(-8 s_ref sqrt(T)), 0.6), F * max(exp(8 s_ref sqrt(T)), 1.4)]`,
  where `s_ref` is the estimator's smile at `k = 0`;
- Black-76 call prices;
- static-arbitrage report;
- slope-isotonic repair: weighted PAVA on chord slopes with weights ΔK,
  clipped to `[-D, 0]`, re-integrated with the L2-optimal level, then shifted
  up to meet `C(K_N) >= 0` and `C(K_0) >= D (F - K_0)`;
- discrete-atom density;
- `q_hat = 1 + s(K*)/D`, clipped to `[0, 1]`. `s(K*)` is the chord slope
  linearly interpolated at `K*` from segment midpoints.

The estimators:

- **C (module, `fit_smile`):**
  1. Whittaker smoothing of `iv` over the normalized coordinate
     `u = (k - k_min)/(k_max - k_min)`. The penalty is
     `lam * sum_i w_i (D2 s)_i^2`, where `D2` is the divided second difference
     and `w_i = (u_{i+1} - u_{i-1})/2`.
  2. PCHIP interpolation inside the data range.
  3. Linear-in-k wings beyond the data range. The slope is the least-squares
     slope over the `m` outermost smoothed points (all points if fewer than
     `m`).
  4. In the wings, `iv = min(max(lin, 0.01), max(sqrt(2|k|/T), 0.01))` (Lee
     moment cap). Inside the data range, `iv >= 0.01`.
- **B1 (incumbent one-number skew):**
  1. `engine.options_skew._iv_selection_at_delta` on the truncated rows picks
     the 25Δ put iv and the 50Δ call iv.
  2. The smile is linear in `k` through those two points (flat if their `k`
     coincide).
  3. It uses the same floor and Lee cap, and runs through the same pipeline.
- **B0 (flat):** flat smile at the incumbent's 50Δ call iv, through the same
  pipeline.

Each date gets one distance per estimator: `dist_e(d)` is the distance from
`q_hat_e(d)` to `[L(d), U(d)]` (0 if inside).

- **H1 (primary):** C extrapolates the RN left tail closer to the identified
  interval than the incumbent skew B1.
- **H0:** no practical improvement.

**Primary statistic:** `Delta = mean over supported test dates of
(dist_C - dist_B1)`.

**Practical effect bar.** H1 is supported only if all three hold:

1. the 95% CI upper bound of `Delta` is below 0;
2. `mean dist_C <= 0.75 * mean dist_B1`;
3. `mean dist_B1 - mean dist_C >= 0.002` (absolute probability units).

C vs B0 is descriptive only.

## 9. Trial family

- **Training grid for C:** `lam` in {0, 1e-4, 1e-3, 1e-2, 1e-1} × `m` in
  {3, 5, 8, 12} = 20 configurations. They are scored on TRAIN only by mean
  train `dist_C`. Ties go to the larger `lam`, then the larger `m`.
- **Primary test comparison:** exactly one (selected C vs B1), evaluated once.
- **Descriptive comparison:** C vs B0.
- B0 and B1 have no free parameters.
- No other configuration, window, band or cut is tried on TEST.

## 10. Chronological split and honest N

The split falls at an ISO-week boundary. Blocks are ISO weeks:

| block | dates |
|---|---|
| W25 | 06-15, 06-17, 06-18 |
| W26 | 06-24, 06-26 |
| W27 | 06-30, 07-01, 07-02 |
| W28 | 07-07, 07-08, 07-09, 07-10 |
| W29 | 07-13, 07-15, 07-17 |
| W30 | 07-20, 07-21, 07-22, 07-23, 07-24 |
| W31 | 07-27, 07-28, 07-29, 07-30 |
| W32 | 08-06 |
| W33 | 08-10, 08-12, 08-13 |

- **TRAIN = W25–W29:** 15 dates, 5 blocks.
- **TEST = W30–W33:** 13 dates, 4 blocks.
- Preprocessing is rule-based with no fitted parameters. The only fitted
  hyperparameters (`lam`, `m`) are chosen on TRAIN only.
- Honest N: 4 test week-blocks and 13 test dates. The number of distinct
  test expiries is also reported, because adjacent dates can share an expiry.

## 11. Dependence-aware uncertainty

- Week-block bootstrap on TEST: resample the 4 test ISO-week blocks with
  replacement, B = 4000, seed 13013. The statistic is the pooled mean of
  per-date `(dist_C - dist_B1)` over the resampled dates. The CI is the 95%
  percentile interval.
- Also reported: the block-level sign count (blocks where the mean diff is
  below 0, at 0, and above 0).
- With 4 blocks the CI is coarse. That coarseness is part of the result, not
  something to tune away.

## 12. Support gates and attrition

A date enters the primary comparison only if all of these hold:

- **Truth support:** at least 2 usable OTM puts in `[0.75F, K*]` and at least
  2 in `[K*, F)`, and `L <= U`.
- **Truncated support:** at least 4 usable strikes, with at least 2 puts and
  at least 2 calls.
- **Estimator success:** all of C, B1 and B0 return a finite `q_hat`.

Attrition is reported per reason and per split. The comparison uses the
intersection of supported dates.

## 13. Falsifier (bounds-only) and stop rule

**Proxy falsifier.** On TEST, the falsifier fires if any one holds:

- C coverage (`q_hat_C` inside `[L, U]`) is below 80% of supported dates;
- the median relative width `(U - L) / ((U + L)/2)` is above 0.5;
- attrition is above 50% of test dates.

When it fires, the output is restricted to identified central/tail price
bounds: the module reports `PRICE_BOUNDS_ONLY` with no point estimate.

The module also classifies each surface:

- `PRICE_BOUNDS_ONLY` applies when any of these holds:
  - fewer than 2 quoted strikes lie at or below `K*` (weak wing support);
  - `K*` lies in the extrapolated region;
  - the raw (pre-repair) negative atom mass exceeds 0.01 (unstable
    curvature);
  - the identified interval is inconsistent (`L > U`);
  - the identified relative width exceeds 0.5.
- `FULL_DENSITY` applies otherwise.

**Stop rule.**

- The `compare` stage runs once.
- A code crash before results are written allows at most 2 reruns. Each is
  logged in RUNS.log, and the fix is recorded in `PREREG_AMENDMENT.md` with
  no change to metrics, windows, grids, bands or split.
- A PREREG hash mismatch makes `evaluate.py` refuse (exit 2).
- No result-dependent re-runs.

## 14. Descriptive diagnostics (cannot change the verdict)

1. **Band scaling:** 0.5×, 1× and 2× band scaling on TEST, with interval
   widths and C coverage at each.
2. **Full-chain module report on TEST,** using the full-chain window and the
   selected config:
   - raw butterfly negativity;
   - repair size (max |ΔC| relative to the band half-width);
   - reintegration excess against the band at quoted strikes;
   - forward check;
   - extrapolation mass and grid-truncation mass;
   - perturbation interval (100 uniform-in-band draws, seed 13013);
   - identification mode.
3. **ATM call/put iv discrepancy:** the median of `|iv_call - iv_put|` at the
   3 strikes nearest F that have both legs, as a forward-basis inconsistency
   measure (relevant to M2 and M3).
4. **TRAIN-only sensitivity:** the full 20-config training grid, plus
   truncation cuts {0.93, 0.95, 0.97} with the selected config.
5. **Secondary strike `K = 0.95F`:** C/B1/B0 estimates and identified
   intervals on TEST. Note that the estimators *see* this strike's quotes,
   so it is not an extrapolation test.

## 15. Baseline reproduction (before the comparison)

`evaluate.py --stage baseline` reproduces the incumbent display-only skew
(`engine.options_skew.compute_skew`). It runs on each date's SPY rows and
compares the result with the `options_skew/snapshots.parquet` SPY rows that
have the same date and `source == polygon_gex`.

- The comparison covers `otm_put_iv`, `atm_call_iv` and `skew` at 1e-4
  absolute.
- The import uses an in-memory stub for `lib.config`, because importing the
  real module reads `ROOT/.env` at import time, and this brief never reads
  credential files.
- Matches, mismatches and missing rows are logged.
- A failed reproduction is reported as a limitation. It does not change the
  verdict rule in Section 0.

`evaluate.py --stage absence` records the absence of any in-repo RN-density
incumbent. It is a Python scan of `_base` `engine/`, `scripts/` and `tests/`
for density terms.

## 16. Non-duplication

**Incumbent refresh and collision check (done before this freeze).**

- `_base` (`engine/`, `scripts/`, `tests/`) contains no Breeden–Litzenberger,
  risk-neutral density or tail-density implementation. Every grep hit for the
  density terms was a false positive.
- `engine/options_rn_tail_density.py` and
  `tests/test_options_rn_tail_density.py` do not exist.

**EXCLUSIONS incumbents and the narrow relation.** Q13 consumes nothing from
these and replaces none of them:

- `engine/options_skew.py` — display-only one-number 25Δ−50Δ skew. Q13 uses
  its expiry/delta selection as baseline B1 and reproduces it. It never
  edits it.
- `engine/options_surface.py`, `engine/options_matrix.py`,
  `engine/options_scenario_surface.py`, `engine/options_payoff.py` (research
  expression only), `engine/options_structure.py`,
  `engine/options_ivspread.py`, `engine/options_dislocation.py`,
  `engine/options_nbbo_cohort.py`, `engine/options_focused_quote.py`,
  `engine/btc_options.py`, `engine/options_hub.py`,
  `engine/neuralweb/options_plane.py` — surface, matrix, observation, NBBO,
  payoff and relative-pricing owners. Q13 neither reads nor writes their
  outputs.

**Distinct from:**

- the relative-pricing lanes (#8577, #8578);
- the dealer-pressure lanes (#8555, #7328, #8684);
- the matrix/observation-source lanes (#7861, #7293, #7327);
- MAS-260 physical LOD/HOD;
- any Risk Radar crash probability (Q ≠ P);
- any options UI (none built).

**Sequence:** Q12↔Q01 → Q02 → Q13. Q13 is a second-order consumer whose
admitted inputs (M2, M3, M4) belong to those briefs. Q13 adds no second
writer against `options_skew` or greeks.

**Standing kills/holds respected:**

- `DNR:KILL-OUTCOME-AUDITION` (no outcome window, no audition of return
  predictors);
- `DNR:KILL-LLM-ORIGINATION` (no language model originates any number);
- `DNR:KILL-FUSED-COMPOSITE` and `DNR:KILL-POSITIONING-FUSION` (no fusion
  with positioning or other signals);
- `DNR:KILL-REGIME-SCORECARD` and
  `DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR` (no regime scoring);
- `DNR:KILL-CAUSAL-DAG-ALPHA`;
- `DNR:HOLD-PSS-AF1-FINRA` and `DNR:HOLD-PSS-CD1-CROWDING` (not touched).

Historical charm/DOI/skew nulls remain negative evidence. The October
options research exception grants no production authority.

## 17. Literature anchors

- [L11] Malz, A. (2014). *A Simple and Reliable Way to Compute
  Option-Based Risk-Neutral Distributions.* FRB New York Staff Report 677.
- [L12] Federal Reserve note (2014): option-implied tail probabilities are
  risk-neutral and must not be read as physical crash odds.
- [L01] Gatheral, J. and Jacquier, A. (2014). *Arbitrage-free SVI
  volatility surfaces.* Quantitative Finance. This is the static-arbitrage
  conditions reference; SVI itself is not fitted here.
- Breeden, D. and Litzenberger, R. (1978). *Prices of state-contingent
  claims implicit in option prices.* Journal of Business.
- Lee, R. (2004). *The moment formula for implied volatility at extreme
  strikes.* Mathematical Finance.
