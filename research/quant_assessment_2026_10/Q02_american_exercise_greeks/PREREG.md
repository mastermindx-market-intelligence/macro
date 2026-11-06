# Q02 — American-exercise and discrete-dividend pricing/Greek qualification — PREREGISTRATION

Status: FROZEN on write. The sha256 of this file and a UTC timestamp from `date -u` are
recorded in `FREEZE.log` in this directory before any evaluation outcome is read. This file is
never edited after the freeze; any later change goes only into `PREREG_AMENDMENT.md` (reason,
sha256, written before any new outcome is read).

Author: Opus 5.5 subagent (model ID `claude-opus-5-5`), Q02 AUTHOR role, quant assessment
2026-10 staging. Research only. Nothing here wires, registers, schedules, promotes, gates or
activates anything.

## 0. Pre-freeze disclosure (what was looked at before this file was written)

Before freezing, only inventory and schema facts were examined. No pricing outcome, IV
inconsistency or model comparison was computed on any real contract.

- The brief, its exclusions and dependencies file, and the math-witness file were read.
- `engine/greeks.py` and its call sites in `engine/` and `scripts/` of the pristine `_base`
  snapshot were read.
- Under the read-only licensed retained data root
  (`/Users/chriswong/Documents/Cluade/macro-main/data`, vintage `cdab6268`), the following were
  examined:
  - the file list of `polygon_gex/chains/`;
  - the column names and the first rows of one chain file (2026-07-24: 163,564 rows; columns
    `underlying, strike_ticker, expiry, K, T, is_call, oi, iv, gamma, delta, volume, spot, asof`);
  - the `ofr/FNYR-SOFR-A.parquet` columns;
  - `massive/capability_manifest.json`;
  - a schema-only scan of every parquet file under the data root (25,246 files, 0 read errors)
    for dividend, deliverable, multiplier, exercise-style and settlement field names;
  - the edgar fundamentals panels that carry an annual `dividends` column.
- Inventory finding before freeze:
  - The chains carry no option price (bid/ask/mid/last), no deliverable or multiplier, no
    exercise style and no settlement clock.
  - No point-in-time declared cash-dividend schedule exists anywhere under the data root.
  - `massive/capability_manifest.json` lists a vendor `ref_dividends` endpoint as entitled, but
    nothing from it is retained locally, and fetching it is forbidden here.
  - The edgar `dividends` column is an annual fiscal-year cash-flow aggregate. It has no
    ex-date, amount per share or known-at time, so it is ineligible.
- This inventory determines the expected gate outcome (Section 9). It is disclosed here so the
  gate is not presented as a surprise.

## 1. Question and estimands

The brief asks whether the existing continuous-yield European Black–Scholes path is being applied
to contracts it does not describe, and whether a bounded American / discrete-dividend reference
can be qualified to replace "a correct formula on the wrong contract" with an explicit
applicability decision.

Two estimand families. Only E2 is an empirical trial.

- **E1 — numerical qualification (deterministic, synthetic, no market data).** These are
  absolute and relative errors of the new reference pricer against independent references:
  - the analytic European formula of `engine/greeks.py` (and the standard Black–Scholes–Merton
    price);
  - a Cox–Ross–Rubinstein lattice with Vellekoop–Nieuwenhuis interpolation at the ex-dividend
    step;
  - a Gauss–Hermite quadrature reference for a European call with one cash dividend.

  Each is measured per quantity (price, delta, gamma, vanna, charm) and per grid level (N, 2N,
  4N). Unit: one synthetic contract specification.
- **E2 — empirical call–put consistency (conditional on the data gate in Section 9).**
  - Unit of analysis: an eligible same-underlying, same-expiry, same-strike call–put pair in one
    chain snapshot.
  - For model M, let `g_M = |sigma_call^M - sigma_put^M|`, where `sigma^M` inverts model M to the
    observed option mid price. Units: annualised volatility points (1 vol point = 0.01 decimal).
  - Daily statistic for chain date d:
    `D_d = mean over underlyings u of [ median_pairs(g_EUR) - median_pairs(g_AMER) ]`.
    - `EUR` is the incumbent European continuous-yield model with q = 0, the convention at the
      `engine/greeks.py` call sites.
    - `AMER` is the new American FD model with the point-in-time declared discrete-dividend
      schedule.
  - Estimand: the mean of `D_d` over the test-half dates.

## 2. Clocks

- **Input clock.** Each chain snapshot's `asof` timestamp is the information cutoff. A dividend
  record is usable only if its `known_at <= asof`. The rate is the SOFR fixing for the latest
  date `<= asof` date.
- **Output clock.** All E2 quantities are contemporaneous with the same snapshot (a
  cross-sectional pricing-consistency estimand). There is no forward outcome window, and no
  quantity is a forecast.
- **Expiry clock.** Time to expiry is measured from the snapshot cutoff to the contract's
  declared settlement instant.
  - `AM_OPEN` means the expiry-day opening print; `PM_CLOSE` means the expiry-day close.
  - The year fraction is minutes divided by a declared minutes-per-year (365-day calendar).
  - An unknown settlement clock fails closed. It is never defaulted to the close.
- **Module clock.** The module takes integer minute indexes from an arbitrary origin. It never
  reads a wall clock and contains no calendar date.

## 3. Cohort and source vintages

Data root: `/Users/chriswong/Documents/Cluade/macro-main/data`, read-only, vintage `cdab6268`.

Cohort: every chain snapshot in `polygon_gex/chains/` (28 files, 2026-06-15 to 2026-08-13). It is
restricted to single-name and ETF equity options for E2. Index products are reported in the
support census only.

| input | sha256 |
|---|---|
| polygon_gex/chains/2026-06-15.parquet | b3b64a15a058f60fd3f83e5be23b9c500b720ce9719f2acf67068826fdc98f21 |
| polygon_gex/chains/2026-06-17.parquet | 3b764b176fadd2c0d9018df4b572cd92aa33eba8262c94f8b73c9321e08fc5d2 |
| polygon_gex/chains/2026-06-18.parquet | 91dfe4034235a5d47544ea8ecf69692593a6a1a9224598496b0c256856e561b5 |
| polygon_gex/chains/2026-06-24.parquet | 3425ac28473f3ec53690284bc5b969e33cab2e60dfb7d2ab3a6df0f9b7ccf846 |
| polygon_gex/chains/2026-06-26.parquet | b295c88c375e92809f16e5d0a47ade28ab64ffa47d1bd61defe90255769b504d |
| polygon_gex/chains/2026-06-30.parquet | 475ff75749f18d9250f257af7c8506dc78058b6efe785e55cbd2f6364071c450 |
| polygon_gex/chains/2026-07-01.parquet | 2e5ec91417d811d7282a8de69134d39a19800af4172c25f33849e5de2e786aa7 |
| polygon_gex/chains/2026-07-02.parquet | 27c8f4c9768480b892a3f377e37510b3a1a23156b5389212e1a5b557b7288f06 |
| polygon_gex/chains/2026-07-07.parquet | 0f37eaa140c4a6ad4d1576b93938ac7c829c955e096aee5804ec8c821bacba9d |
| polygon_gex/chains/2026-07-08.parquet | 0e5086480bbd38e0b862c784ee85c6879ad90fdc48432d5c6046d7896366122e |
| polygon_gex/chains/2026-07-09.parquet | f80811096a2e0a5cd6df506c5ada7f600cb9e9901618b4b26302b5fe8d89678c |
| polygon_gex/chains/2026-07-10.parquet | b48992f0b89f58c4b5f9706a89aa51b5b8e33fe41a02a43174fd47bc8a289fe4 |
| polygon_gex/chains/2026-07-13.parquet | e3f4f5bc20863d2add0c7f075f1604b646f4bcba6d5a33d4c98105da9019effa |
| polygon_gex/chains/2026-07-15.parquet | 0dbb288cd3f98c7d0dc4b6139239ff57e6724dc70b5831f04f5046433cd83cf0 |
| polygon_gex/chains/2026-07-17.parquet | 846f60b395c0c16a9d4f45f0c371e05aceefba5b120c7f632e08bfd92ee98c7f |
| polygon_gex/chains/2026-07-20.parquet | 0b5e48eb981fe04a90035f2992444607b59467e085717bef9e948367a75ec25e |
| polygon_gex/chains/2026-07-21.parquet | 22951e0788fd642d49e5096203f3cc99402c70c87c0a716c412a8924dad8f850 |
| polygon_gex/chains/2026-07-22.parquet | d6edd7c50b149857803940894d862dfeecb5c683e56650962ccfc6a18d715deb |
| polygon_gex/chains/2026-07-23.parquet | f018d9506be417001937bee33a95d4007417b3d8ad5919c5be9d9f1bf61e14bf |
| polygon_gex/chains/2026-07-24.parquet | a263ed1a46c52f44d967b4b6ba5cbd69a89b861c3c29262ad3bebdc7411c3117 |
| polygon_gex/chains/2026-07-27.parquet | 7023fde67dda28bd3ab7d4c430e3ca75936f7bad151a514cb22926a962825eb8 |
| polygon_gex/chains/2026-07-28.parquet | dcffd24ecb49d4fb0fd11b19d86fc73b129564d38919256a353de1de97fb408a |
| polygon_gex/chains/2026-07-29.parquet | a77f545f68e2f90674bc32a55c3c94d57b01c5b0c0b30dae140e068176822c07 |
| polygon_gex/chains/2026-07-30.parquet | f941d5ebd512b3df356daaac88365c5892bf1176d7845f8c99dc67609bd30636 |
| polygon_gex/chains/2026-08-06.parquet | d4a486c94b274e9419d09639e51f25d1c4fc1cde759612ab14fc536a05577d92 |
| polygon_gex/chains/2026-08-10.parquet | c2488d33c7ff96c7ffeaa7386fb494794ef13d73998f1187c8b14ca1296ac267 |
| polygon_gex/chains/2026-08-12.parquet | 68782399b571feafa34bdeb5171c4da03f71fa72b57f17e608d63c6d2390153f |
| polygon_gex/chains/2026-08-13.parquet | 846a8f144a3b6315cebabdec7c7eb85d81ea70a2d2a6b064b3beacb0dc84cc28 |
| ofr/FNYR-SOFR-A.parquet | 02dca610d9d4857a002beee07aef0a3f96af943131efba5d0861c0d5b1ddc620 |
| massive/capability_manifest.json (absence evidence only) | a47340db753e5a44566590ca714c3cb2524ab4dd686a676e5d1592b5c4f29051 |
| edgar/fundamentals_panel.parquet (ineligibility evidence only) | 9af85734e4e3ca64500aba8c61e3b5a7080e15f9912beba150e1bafd8b8bebc4 |

Code baseline:

- `engine/greeks.py` sha256 `d471f5ed78183974171127050daae3c83b1438252c758b776394af0955ba8d9c`
  (identical in `_base` and the Q02 staging clone; repository base `d252f919`).

`evaluate.py` re-hashes every input it opens and refuses to proceed past the inventory stage if a
chain file hash differs from this table.

## 4. Hypotheses

- **HN (numerical, E1).** The reference pricer meets every tolerance in Section 7 at the finest
  declared grid. Its refinement report never labels a near-exercise-boundary higher derivative
  as a precise point value.
- **HG (data gate).** The local retained data identify, per contract:
  - exercise style;
  - deliverable/multiplier (including adjusted deliverables);
  - settlement clock;
  - a point-in-time declared dividend schedule complete through expiry;
  - an option price;
  - a rate.

  Support must reach the thresholds of Section 9.
- **H1 (empirical, E2; tested only if HG holds).**
  - H1: the test-half mean of `D_d` is at least 0.5 vol points, and the 95% moving-block-bootstrap
    lower bound is above 0.
  - H0: the true mean reduction is below 0.5 vol points.

## 5. Baseline competitors

- **B1 (incumbent).** European continuous-yield Black–Scholes, `engine/greeks.py` formula,
  q = 0 (the convention at `gex_engine`, `options_surface`, `options_payoff`
  `declared_constant_q_0.0_no_dividend_feed`, `options_hub`, `options_entry_state`, and the other
  call sites).
- **B2 (numerical references for E1).**
  - The analytic formula of B1, with general q.
  - CRR lattice (American and European; discrete dividends by Vellekoop–Nieuwenhuis
    interpolation).
  - Gauss–Hermite quadrature for a one-dividend European call.

## 6. Method under test

`engine/options_american_exercise.py` (new, research reference, not wired):

- **Solver.** Uniform S-grid Crank–Nicolson with a Rannacher start: the first two
  Crank–Nicolson steps after expiry and after each dividend jump are replaced by four
  implicit-Euler half steps. The spot is placed exactly on a grid node.
- **American constraint.** Ikonen–Toivanen operator splitting.
- **Cash dividends.** A declared jump condition at each ex-time:
  - `V(S, t_d^-) = V(max(S - D, 0), t_d^+)` by linear interpolation;
  - for American exercise, the maximum of that and the immediate payoff at `t_d^-`.
- **Dirichlet boundaries.** At S = 0 and at `S_max`, the upper bound carries the present value of
  the remaining dividends.
- **Greeks.**
  - Delta and gamma by central differences at the spot node.
  - Vanna by a fixed-grid sigma bump of +/- 0.01.
  - Charm (per year, `= -d delta / d tau`, same sign and unit as `engine/greeks.py`) by central
    differencing of delta across adjacent time layers.
- **Fail-closed applicability selector.** It decides EUROPEAN_BS_CONTINUOUS_YIELD /
  EUROPEAN_BS_EQUIVALENT / EUROPEAN_FD_DISCRETE_DIVIDEND / AMERICAN_FD / UNAVAILABLE from declared
  contract terms only.
- **Point-in-time dividend filter.**
- **Explicit unit converters** with no default multiplier.

Grid levels: N = 100, 2N = 200 and 4N = 400 space intervals, with at least as many time steps as
space intervals per level (piecewise-uniform in time so every in-window ex-time is a node). These
levels are fixed by this file and are not tuned on any outcome.

## 7. Numerical tolerances (E1; requirement tests use exactly these)

Reference scenario set (synthetic, relative units). They are written here as constants of the
tests:

- **Base parameters.** S = 100, K = 100, T = 0.5 years, sigma = 0.25, r = 0.03, q = 0.01.
- **Variants.**
  - K in {80, 100, 120}.
  - A short-dated case: T = 0.1.
  - One cash dividend D = 2 at 0.25 years (European call vs quadrature).
  - A deep-in-the-money dividend case: S = 100, K = 80, D = 5 at 0.25 years, T = 0.5, r = 0.03,
    q = 0, sigma = 0.2 (American call vs CRR).

Tolerances at the finest grid (4N):

| ID | quantity / check | tolerance |
|---|---|---|
| T1a | European FD price vs analytic, no dividends | abs <= 5e-3 (currency per share) |
| T1b | European FD delta vs analytic | abs <= 2e-3 |
| T1c | European FD gamma vs analytic | abs <= 5e-4 |
| T1d | European FD vanna and charm vs analytic | abs <= 5e-3 + 5e-2 x abs(analytic) |
| T1e | module's own analytic European delta/gamma/vanna/charm vs the `engine/greeks.py` formula | abs <= 1e-12 |
| T1f | refinement: abs error at 4N < abs error at N, for price, delta, gamma (European, ATM) | strict |
| T1g | European FD with one cash dividend vs quadrature | abs <= 1e-2 |
| T2a | American put >= intrinsic at every grid node | >= -1e-10 |
| T2b | American >= European on the same grid and at spot (put and call) | >= -1e-10 |
| T2c | American put <= K, American call <= S (per share) | strict |
| T2d | American call, q = 0, no dividend, r >= 0, vs European call | abs <= 5e-3 |
| T2e | American put FD vs CRR lattice (2,000 steps), K in {80, 100, 120} | abs <= 2e-2 |
| T2f | deep-ITM dividend American call: FD vs CRR-VN lattice (2,000 steps), and an early-exercise premium over the European call | abs <= 5e-2; premium >= 0.5 |
| T3 | point-in-time and expiry-clock changes (Section 8) | exact equality where invariance is required; strict inequality where a change is required |
| T4 | refinement classification rules (Section 8) | as specified |

If a tolerance proves unattainable, it is not loosened silently. The case is reported as failed,
and an amendment with its reason is written before any rerun.

## 8. Qualification rules (frozen) and requirement mapping

**Grid-refinement classification** for each quantity q at levels q1 = q(N), q2 = q(2N),
q3 = q(4N):

- Definitions: `d1 = q2 - q1`, `d2 = q3 - q2`, `tol = atol + rtol * |q3|`.
- Tolerance values:

  | quantity | atol | rtol |
  |---|---|---|
  | price | 1e-3 | 1e-4 |
  | delta | 5e-4 | 0 |
  | gamma | 2e-4 | 1e-2 |
  | vanna and charm | 5e-3 | 2e-2 |

- **CONVERGED** iff all three values are finite, `|d2| <= tol`, and either `|d1| <= tol` or
  `|d2| <= 0.75 |d1|`. The reported value is q3, the error estimate is `|d2|`, and the observed
  order is `log2(|d1|/|d2|)` when both are non-zero.
- **INTERVAL** iff all values are finite but not CONVERGED. Report the interval
  `[min(q1,q2,q3) - |d2|, max(q1,q2,q3) + |d2|]` and no point value.
- **UNAVAILABLE** iff any value is non-finite.
- **Near-exercise-boundary override (American only).**
  - Locate the exercise boundary S* at the valuation layer of the coarsest grid, among interior
    nodes with strictly positive payoff: the largest put node, or the smallest call node, where
    `V - payoff <= 1e-8`. If no such node exists, there is no boundary and no override.
  - If `|S - S*| <= max(3 x coarse dS, 0.02 x S)`, then gamma, vanna and charm may not be
    CONVERGED. They are reported as INTERVAL with reason `near_exercise_boundary`.
  - Price and delta keep their own classification.
- **Ex-dividend charm override.** If any in-window ex-time lies within one finest time step of
  the valuation instant, charm is UNAVAILABLE with reason `ex_dividend_within_charm_stencil`.

**Point-in-time dividend rule:**

- A record is `(record_id, known_at, ex_time, amount, status)`, with status in
  {DECLARED, ESTIMATED, CANCELLED}.
- For each `record_id`, keep the revision with the greatest `known_at <= cutoff`. Revisions first
  known after the cutoff are ignored.
- A record whose latest admissible revision is CANCELLED is removed.
- Only `valuation < ex_time <= expiry` is in window.
- An ESTIMATED latest revision in window fails closed (`dividend_estimated_not_declared`).
- A schedule whose declared `complete_through < expiry`, or is None, fails closed
  (`dividend_schedule_not_complete_through_expiry`).
- `cutoff > valuation` raises (look-ahead).
- A missing schedule (None) is distinct from a declared-complete empty schedule.

**Requirement-to-test mapping.** Tests are named `test_req<k>_...`:

1. **req1** — T1a–T1g.
2. **req2** — T2a–T2f.
3. **req3** — point-in-time behaviour:
   - a post-cutoff record leaves the price bit-identical to the no-dividend price;
   - a pre-cutoff revision changes it;
   - out-of-window records change nothing;
   - a look-ahead cutoff raises;
   - AM_OPEN vs PM_CLOSE changes T and the price;
   - an unknown settlement clock is UNAVAILABLE.
4. **req4** — classification:
   - a smooth European case is CONVERGED;
   - a synthetic non-convergent sequence is INTERVAL;
   - a non-finite sequence is UNAVAILABLE;
   - a near-boundary American put never yields CONVERGED gamma/vanna/charm;
   - a charm stencil straddling an ex-date is UNAVAILABLE.
5. **req5** — discriminating unit tests:
   - per-share to per-contract needs an explicit multiplier (a 10-share adjusted deliverable
     gives a different value than 100);
   - decimal to vol-point is x100, and vega per 1.00 vol to per vol point is /100;
   - annual to daily charm with a declared 365 or 252 basis gives distinct values;
   - unknown unit labels and undeclared bases raise.
6. **req6** — fail-closed selector:
   - unknown exercise style, unknown deliverable, an adjusted root without explicit deliverable,
     missing dividend metadata, an estimated dividend, a missing rate and an unknown settlement
     each give UNAVAILABLE with a named reason;
   - no code path yields a multiplier of 100 that was not supplied.
7. A no-silent-activation test:
   - `RESEARCH_ONLY is True`;
   - the module registers nothing;
   - import and calls leave module globals unchanged;
   - the module imports only stdlib, numpy and scipy.

## 9. Data gate (HG), support and attrition reporting

Per chain row, `evaluate.py` applies the module's selector to terms provided by the data alone.
It reports the attrition at each stage, counted per row and per distinct (date, underlying):

1. rows;
2. parseable OCC/OSI symbol;
3. standard-looking root (root equals underlying and has no digit suffix) vs adjusted-looking;
4. exercise style provided by the data;
5. deliverable/multiplier provided by the data;
6. settlement clock provided by the data;
7. a point-in-time declared dividend schedule (known-at, ex-time, amount) complete through
   expiry;
8. an option price (bid/ask/mid/last) provided by the data;
9. rate available (SOFR on or before the snapshot date).

**Sensitivity arm** (support reporting only, not a trial). It uses a declared OCC product-class
exercise-style map:

- European cash-settled index roots: SPX, SPXW, XSP, NDX, NDXP, RUT, RUTW, MRUT, VIX, VIXW, DJX,
  XEO.
- American: OEX and all equity and ETF roots.

All other criteria stay data-only. The map is an assumption and is labelled as one.

**Gate thresholds (HG passes iff all hold, strict arm):**

- (a) at least 10 distinct chain dates in EACH chronological half have at least one eligible
  call–put pair;
- (b) at least 10 distinct underlyings contribute eligible pairs in the test half;
- (c) every eligible pair has a data-provided option price on both legs.

Vendor `iv`/`delta`/`gamma` columns are outputs of an undeclared vendor model. Reconstructing
option prices from them, or inferring dividends from them, is a manufactured input and is
forbidden.

If HG fails:

- E2 is not run;
- the verdict is INSUFFICIENT_DATA, naming each missing input;
- per the brief's falsifier, only the applicability guard ships (research reference, not wired);
- every model output on real contracts remains UNAVAILABLE.

## 10. Chronological split, trial family, uncertainty, honest N (E2, conditional)

- **Split.** The 28 chain dates are sorted ascending. Train = first 14 dates, test = last 14
  dates. Nothing is fitted on outcomes:
  - the grid is fixed by Section 6;
  - the IV inversion uses a fixed bracket [0.005, 5.0] with Brent root-finding;
  - the only training-half use is the attrition/support diagnostics and a check that the
    inversion success rate is at least 90%.
- **Trial family.** Exactly one primary trial: the test-half mean of `D_d`. No repeated holdout
  search, and no alternative metrics are promoted after the fact. The sensitivity arm is support
  reporting, not a trial.
- **Dependence-aware uncertainty.** Moving block bootstrap over test dates:
  - block length 5 dates, B = 2,000 resamples, fixed integer seed 2002;
  - 95% percentile interval of the mean of `D_d`.
- **Honest N.** Report:
  - the number of distinct test dates;
  - the number of non-overlapping blocks (ceil(n/5));
  - the number of distinct underlyings and eligible pairs.

  Pairs within a date are never treated as independent.
- **Decision.**
  - KEEP (empirical upgrade supported) iff the point estimate is at least 0.5 vol points and the
    lower bound is above 0.
  - REJECT iff the upper bound is below 0.5 vol points.
  - Otherwise INSUFFICIENT_DATA (inconclusive).

## 11. Falsifier and stop rule

- **Falsifier (from the brief).** If the data cannot identify contract terms, ship only the
  applicability guard and keep the model outputs unavailable. A more elaborate solver does not
  cure unknown inputs.
- **Numerical falsifier.** If any Section 7 tolerance fails at 4N, that scenario class is not
  qualified. The module must not emit a CONVERGED point value for it, and the verdict cannot be
  KEEP.
- **Stop rule.**
  - One evaluation run per frozen hash.
  - `evaluate.py` refuses to run if sha256(PREREG.md) differs from the hash recorded in
    `FREEZE.log`.
  - Every run, including a refusal, is appended to `RUNS.log` with command, exit code, and input
    and output sha256s.
  - Runs are capped below 10 minutes, with thread limits of 2 at nice 10.
  - No threshold, grid or split changes after outcomes are read.

## 12. Non-duplication

Collision check performed on `_base` before freeze:

- the module name `options_american_exercise` is absent;
- no American, lattice, PSOR, Crank–Nicolson or discrete-dividend option pricer exists in
  `engine/` or `scripts/`;
- every pricing call site is European continuous-yield with q = 0 or a declared constant q;
- `engine/options_ivspread.py` notes the vendor call/put IV offset from dividends and American
  exercise, and cancels it cross-sectionally rather than modelling it.

Incumbents from the assessment's EXCLUSIONS list that touch this brief, and the narrow relation
kept here:

- **Dealer pressure / LOD-HOD / close intelligence (#8555, #7328, #8684).** Not duplicated. No
  SPX book hedge-target repricing, no dealer-inventory inference, no hedge-execution or
  market-impact claim. Q02 is contract-style pricing and applicability only.
- **Relative options pricing maps (#8577, #8578).** No scatter, trails, percentile or compare
  surface. Q02 produces no cross-sectional ranking.
- **Options matrix / observation source (#7861, #7293, #7327).** No session repair, snapshot
  retention or expiry-field projection. Q02 reads existing chain snapshots read-only for a
  support census.
- **Shared European pricer `engine/greeks.py`, `engine/options_surface.py`,
  `engine/options_skew.py`.** Preserved byte-for-byte. Q02 adds new files only and is a separate
  contract-class numerical qualification against the incumbent European formula. It never
  writes to options_skew or greeks, which honours the option-pricing seam rule "never two
  writers".
- **Option-pricing seam sequence (Q12 <-> Q01, then Q02 for American eligibility, then Q13).**
  - Q02 depends on no sibling brief and reads no sibling directory.
  - Q13 may later consume Q02. The reverse dependency does not exist.
- **Standing kills/holds respected.** Q02 creates no signal, score, composite or regime output:
  - DNR:KILL-OUTCOME-AUDITION
  - DNR:KILL-LLM-ORIGINATION
  - DNR:KILL-FUSED-COMPOSITE
  - DNR:KILL-POSITIONING-FUSION
  - DNR:KILL-REGIME-SCORECARD
  - DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR
  - DNR:KILL-CAUSAL-DAG-ALPHA
  - DNR:HOLD-PSS-AF1-FINRA
  - DNR:HOLD-PSS-CD1-CROWDING

  Historical charm/DOI/skew nulls remain negative evidence. Q02 reports charm only as a model
  sensitivity with declared units, never as a signal.

## 13. Scientific restrictions carried

- No language model originates a signal, score or escalation.
- Inferred dealer inventory is never called observed.
- Conditional hedge-target repricing is not realized market impact.
- Vendor model outputs are not observations of option prices.
- Unknown, invalid, excluded, pending and measured-zero values remain distinct in every output.
