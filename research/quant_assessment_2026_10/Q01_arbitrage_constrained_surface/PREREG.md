# Q01 — Bid/ask-aware, arbitrage-constrained volatility surface: pre-registration

Status: FROZEN on the timestamp in `FREEZE.log`. Never edited after freeze. Any later change goes only to
`PREREG_AMENDMENT.md` (reason + sha256), written before reading any new outcome.

Brief: `Q01_arbitrage_constrained_surface.md` (macro quant assessment 2026-10-08, assessment source
Macro `main@094097a5`). Staging snapshot: repo at `d252f919`; licensed retained data root
`/Users/chriswong/Documents/Cluade/macro-main/data` at vintage `cdab6268` (read only).
Reference implementation: `engine/options_arbfree_surface.py` (RESEARCH REFERENCE — NOT WIRED,
`RESEARCH_ONLY = True`, schema `options_arbfree_surface.research.v1`). Evaluation driver: `evaluate.py`
in this directory. Author model: Opus 5.5 (`claude-opus-5-5`).

## 1. Question

Given one same-session snapshot of European index-option quotes (bid/ask per contract, per expiry
forward F and discount D supplied by a trusted owner), does a constrained raw-SVI surface fitted to
the bid/ask bands reconstruct held-out quotes no worse than a convex piecewise-linear (PL)
normalized-call-price benchmark that is admissible by construction, and is it stable under
perturbations inside the quote bands? If not, the benchmark plus its quality diagnostic is the
retained research artifact and the fitted surface is not described as reliable.

## 2. Non-duplication

Collision check run against the pristine snapshot `_base` before freeze:

* `find _base -name "*arbfree*" -o -name "*arbitrage*" -o -name "*svi*"` → no files. New module and
  test names (`engine/options_arbfree_surface.py`, `tests/test_options_arbfree_surface.py`) are absent
  in `_base`.
* `grep -rli "arbitrage\|arbfree\|svi_\|gatheral\|no_arbitrage" _base/engine` → three files. Only
  `engine/options_skew.py` is on topic: `compute_skew_projection` lists `no_arbitrage_receipt` as a
  MISSING input of the projection (lines ~264 and ~287). `commodity_supply_context.py` and
  `darkpool_signals.py` use the word "arbitrage" in unrelated prose.
* `grep -rli "arbitrage-free\|arbitrage_free\|butterfly arbitrage\|calendar arbitrage\|raw svi\|ssvi"`
  over `_base/{engine,scripts,tests,app}` → no match (exit 1). Over `_base/{research,docs}` → only
  `research/market_microstructure/commission15/SOURCE_REGISTER.md` row O32, a literature citation of
  Gatheral & Jacquier with caveats; no implementation.

Incumbents from `EXCLUSIONS_AND_DEPENDENCIES.md` that touch this brief, and the relation kept:

| Incumbent | Exclusion | Q01 relation |
|---|---|---|
| Relative options pricing maps #8577, #8578 | no scatter/trails/percentile or compare-page build | Q01 is a derived numerical measurement with its own research contract; no map, page, comparison view or percentile output. |
| Dealer pressure / LOD-HOD / close intelligence #8555, #7328, #8684 | no duplicate dealer-book repricing or physical forecasting | Q01 reprices nothing for dealers, infers no inventory, forecasts nothing. |
| Options matrix / observation source #7861, #7293, #7327 | no session repair, snapshot retention or expiry-field projection duplicated | Q01 owns no data source, retains no snapshot, repairs no session; it consumes caller-supplied records only. |
| Option pricing sequencing Q12 ↔ Q01; Q02 for American eligibility; then Q13 | Q01 may start with a trusted owner forward; no two writers on options_skew/greeks | Q01 takes F and D as inputs (Q12 / trusted owner) and fits no forward; American style is rejected (`AMERICAN_EXCLUDED`) until Q02; Q01 edits neither `engine/options_skew.py` nor `engine/greeks.py` nor `engine/options_ivspread.py`. |

Narrow relation: Q01 is a research-only, unwired reference for the concept that
`options_skew.compute_skew_projection` names as a missing `no_arbitrage_receipt`. It adds new files
only, is imported by nothing, and changes no incumbent payload. It keeps a private normalized Black-76
call (needed only to convert SVI total variance to normalized prices for band and dense checks); it is
not a second shared pricing kernel and must not be adopted as one (limitation L3).

## 3. Estimand, unit, clocks

* Unit of observation: one (session, root) surface snapshot. Honest N = distinct sessions (and the
  number of 5-session blocks), never quotes or rows.
* Primary estimand: mean over holdout sessions of the paired difference
  `D_s = L_svi(s) − L_bench(s)`, where `L_m(s)` is the mean held-out out-of-band distance in spread
  units: for each held-out node with band `[lo, hi]`, spread `hi − lo` (floored at 1e-6) and fitted
  normalized call `v`, distance `max(0, lo − v, v − hi) / spread`, averaged over the session's
  held-out nodes. Lower is better; `D_s > 0` means SVI is worse.
* Missing-value rule: a session whose training-node benchmark fit is not `ADMISSIBLE` (or fails the
  dense check) is dropped from the paired comparison and counted under attrition by state. A held-out
  node lying in an SVI slice that is not `ADMITTED` contributes a distance of 1.0 spread unit to
  `L_svi` (conservative against the challenger) and counts toward the SVI failure-rate bar.
* Input clock: integer session-relative clocks `session`, `session_open`, `as_of`, `quote_ts`,
  `expiry_ts`. Only quotes with `session_open ≤ quote_ts ≤ as_of` and `expiry_ts > as_of` are
  eligible. Output clock: the fit is stamped with the screen's `as_of`; nothing is forward-looking.
* Outcome window: the same snapshot (held-out strikes of the same session). There is no market-return
  outcome and no future window.

## 4. Cohort and eligibility

Eligible record: `product == INDEX_OPTION`, root in the declared index-root set (SPX, SPXW, XSP, NDX,
RUT, …), `style == EUROPEAN`, `condition == REGULAR`, finite `bid ≥ 0`, `ask > 0`, `bid ≤ ask`, a
per-contract quote timestamp, exact expiry timestamp and settlement convention, an owner-supplied
per-expiry forward and discount, retained rights. American, unknown style, other products, crossed,
future, out-of-session, duplicate-conflicting or forward-mismatched records are excluded by
`screen_quotes` with an explicit reason; earlier same-coordinate quotes are `SUPERSEDED`.

Eligible session: at least one root with ≥ 2 expiries, each with ≥ 6 screened strikes after
put→call parity conversion (call band ∩ parity-converted put band; `PARITY_CONFLICT` nodes excluded).

Data gate (pre-registered): ≥ 100 eligible sessions in chronological order, giving ≥ 40 holdout
sessions (≥ 8 blocks of 5). Below the gate the verdict is `INSUFFICIENT_DATA` naming the exact
missing input; no comparison is run and no effect size is reported.

## 5. Source vintages (sha256, at freeze)

Data root `/Users/chriswong/Documents/Cluade/macro-main/data`, vintage `cdab6268`:

Baseline-reproduction inputs (incumbent `engine/options_skew.py`, sha256
`8f68ad06c29ff9e05d6f4a710912b12a8523344d3b84a22524867e4711b38dce`, identical in `_base` and `Q01`):

* `options_skew/snapshots.parquet` 18a16c9f72a3f6ac1548a22efaaebaa348265fe783d93ca29da1a8d4c2a53b56
* `polygon_gex/chains/2026-06-15.parquet` b3b64a15a058f60fd3f83e5be23b9c500b720ce9719f2acf67068826fdc98f21
* `polygon_gex/chains/2026-06-17.parquet` 3b764b176fadd2c0d9018df4b572cd92aa33eba8262c94f8b73c9321e08fc5d2
* `polygon_gex/chains/2026-06-18.parquet` 91dfe4034235a5d47544ea8ecf69692593a6a1a9224598496b0c256856e561b5
* `polygon_gex/chains/2026-06-24.parquet` 3425ac28473f3ec53690284bc5b969e33cab2e60dfb7d2ab3a6df0f9b7ccf846
* `polygon_gex/chains/2026-06-26.parquet` b295c88c375e92809f16e5d0a47ade28ab64ffa47d1bd61defe90255769b504d
* `polygon_gex/chains/2026-06-30.parquet` 475ff75749f18d9250f257af7c8506dc78058b6efe785e55cbd2f6364071c450
* `polygon_gex/chains/2026-07-01.parquet` 2e5ec91417d811d7282a8de69134d39a19800af4172c25f33849e5de2e786aa7
* `polygon_gex/chains/2026-07-02.parquet` 27c8f4c9768480b892a3f377e37510b3a1a23156b5389212e1a5b557b7288f06
* `polygon_gex/chains/2026-07-07.parquet` 0f37eaa140c4a6ad4d1576b93938ac7c829c955e096aee5804ec8c821bacba9d
* `polygon_gex/chains/2026-07-08.parquet` 0e5086480bbd38e0b862c784ee85c6879ad90fdc48432d5c6046d7896366122e
* `polygon_gex/chains/2026-07-09.parquet` f80811096a2e0a5cd6df506c5ada7f600cb9e9901618b4b26302b5fe8d89678c
* `polygon_gex/chains/2026-07-10.parquet` b48992f0b89f58c4b5f9706a89aa51b5b8e33fe41a02a43174fd47bc8a289fe4
* `polygon_gex/chains/2026-07-13.parquet` e3f4f5bc20863d2add0c7f075f1604b646f4bcba6d5a33d4c98105da9019effa
* `polygon_gex/chains/2026-07-15.parquet` 0dbb288cd3f98c7d0dc4b6139239ff57e6724dc70b5831f04f5046433cd83cf0
* `polygon_gex/chains/2026-07-17.parquet` 846f60b395c0c16a9d4f45f0c371e05aceefba5b120c7f632e08bfd92ee98c7f
* `polygon_gex/chains/2026-07-20.parquet` 0b5e48eb981fe04a90035f2992444607b59467e085717bef9e948367a75ec25e
* `polygon_gex/chains/2026-07-21.parquet` 22951e0788fd642d49e5096203f3cc99402c70c87c0a716c412a8924dad8f850
* `polygon_gex/chains/2026-07-22.parquet` d6edd7c50b149857803940894d862dfeecb5c683e56650962ccfc6a18d715deb
* `polygon_gex/chains/2026-07-23.parquet` f018d9506be417001937bee33a95d4007417b3d8ad5919c5be9d9f1bf61e14bf
* `polygon_gex/chains/2026-07-24.parquet` a263ed1a46c52f44d967b4b6ba5cbd69a89b861c3c29262ad3bebdc7411c3117
* `polygon_gex/chains/2026-07-27.parquet` 7023fde67dda28bd3ab7d4c430e3ca75936f7bad151a514cb22926a962825eb8
* `polygon_gex/chains/2026-07-28.parquet` dcffd24ecb49d4fb0fd11b19d86fc73b129564d38919256a353de1de97fb408a
* `polygon_gex/chains/2026-07-29.parquet` a77f545f68e2f90674bc32a55c3c94d57b01c5b0c0b30dae140e068176822c07
* `polygon_gex/chains/2026-07-30.parquet` f941d5ebd512b3df356daaac88365c5892bf1176d7845f8c99dc67609bd30636
* `polygon_gex/chains/2026-08-06.parquet` d4a486c94b274e9419d09639e51f25d1c4fc1cde759612ab14fc536a05577d92
* `polygon_gex/chains/2026-08-10.parquet` c2488d33c7ff96c7ffeaa7386fb494794ef13d73998f1187c8b14ca1296ac267
* `polygon_gex/chains/2026-08-12.parquet` 68782399b571feafa34bdeb5171c4da03f71fa72b57f17e608d63c6d2390153f
* `polygon_gex/chains/2026-08-13.parquet` 846a8f144a3b6315cebabdec7c7eb85d81ea70a2d2a6b064b3beacb0dc84cc28

Eligibility-census candidates:

* `thetadata_eod/_manifest.json` c13b9d3af019c1cb7605fd435f2b739e39fa5c572bf09a6492018f232a0444a1
* `thetadata_eod/_backfill_state.json` 913b6737af0a732a4fc4e586b327b7216b9568f9f1062676ad7baf3d89690354
* `options_surface/index_etf.parquet` 1f291b835829546783389e33e605e2a6bdbb2b86eb7b4254dbe83dd0d33b5817
* `cboe/gex_SPX.parquet` 2082b2bb6159ad8090f52dcb1b5056b5679ce1b535ce7f9166a43c7831f85ab5
* `deribit/options_structure.parquet` 23be29d69fb954571bc5f7d50817c903dff912919ef52ff49cac0a82a8fd6486
* `options_session/ledger.parquet` 9867c4a05f29a8da9161edd67ac66fa82700af2e8ee1cc2d24719322e91685ef
* `options_ivspread/snapshots.parquet` e4e5fa9d701f1727a7894affb85aa49052978218b114780b07d3a77775056ed9
* `options_dislocation/snapshots.parquet` ed5d7876e46539f8617319fcde47789b41c6d0d4639d02e3db9287a27c6f4c94
* Staging `DATA_MAP.md` 2a0e0d1c8644f890d00229bc2c30e1cce4c90279f7129fd16079a1b25e71896a

Seams read (not edited): `_base/engine/greeks.py` d471f5ed78183974171127050daae3c83b1438252c758b776394af0955ba8d9c;
`_base/engine/options_ivspread.py` 66dace74833889f44a5288ae9ede7a80d287be164608175161fcf48b4463c35d.

`evaluate.py` re-hashes every input it opens and records the hashes in `RUNS.log`; a hash that
differs from this list is reported, not silently accepted.

## 6. Hypotheses

* H0 (benchmark sufficiency): the constrained SVI challenger is not non-inferior to the convex PL
  benchmark on held-out out-of-band distance, or it is unstable (fit failures or state changes under
  in-band perturbation above the bars in §8).
* H1 (challenger admissible as a reliable surface): SVI passes every bar in §8 on the holdout.
* Mechanical claims (tested by the hermetic suite, not by the empirical comparison): screening rejects
  ineligible records before fitting; infeasible bands return explicit states; admitted fits pass
  dense-grid strike and calendar checks; eligibility is invariant to future quotes, input order and
  duplicates; perturbation sensitivity and tail flags are reported; outputs carry no authority.

## 7. Competitors

1. Convex PL benchmark (`fit_benchmark`): joint LP over all expiries (HiGHS, tolerances 1e-10).
   Stage 1 minimizes spread-weighted band violation subject to bounds `(1−κ)^+ ≤ c ≤ 1`, anchor
   `c(0) = 1`, monotone non-increasing, convex chords, and calendar `c(κ,T2) ≥ c(κ,T1)` at the union of
   breakpoints in the overlap (deterministic proportional carry assumed). Stage 2 minimizes weighted
   distance to the target (mid) with stage-1 violation capped. Admissible only if max node violation
   ≤ 1e-6 spread units AND the dense check passes; otherwise `BANDS_INFEASIBLE`, `FAILED_CHECK`,
   `SOLVER_FAILED` or `NO_DATA`.
2. Constrained raw SVI challenger (`fit_svi_surface`): per expiry from the shortest, objective =
   mean squared out-of-band distance (spread units) + λ·mean squared mid deviation + penalties
   (minimum variance, Lee wing bound, `g < 1e-6`, calendar floor gap vs earlier admitted slices);
   seeded multi-start L-BFGS-B (seed 0, 6 starts, maxiter 400). States `FAILED_FIT`, `FAILED_CHECK`,
   `ADMITTED`; `inside_bands` reported separately.
3. Incumbent exact-leg baseline (`engine/options_skew.skew_map`): not a surface competitor; it is the
   observed-output reference that must stay byte/semantic compatible (requirement 6) and whose
   reproduction is step S1.

## 8. Practical effect bar (KEEP rule for the SVI challenger)

All of, on the holdout only:

* SVI `FAILED_FIT`/`FAILED_CHECK` slice rate ≤ 5% of holdout slices;
* benchmark dense-check pass rate ≥ 99% of benchmark-admissible holdout surfaces;
* upper end of the 95% block-bootstrap CI of mean `D_s` ≤ 0.10 spread units (non-inferiority margin);
* median per-session perturbation state-change fraction (8 seeded in-band draws) ≤ 10%.

Failing any bar → REJECT the challenger as a reliable surface (falsifier); the benchmark and its
quality diagnostic are retained as the research artifact. Below the data gate → INSUFFICIENT_DATA.

## 9. Trial family, split, uncertainty

* Trial family: exactly one primary trial (SVI vs benchmark on `D_s`). λ ∈ {0.01, 0.1, 1.0} is chosen
  inside training only (minimum median training `L_svi`); no other hyperparameter is searched; the
  holdout is evaluated once.
* Held-out nodes: within each slice, sorted by strike, interior node indices `i` (1 ≤ i ≤ n−2) with
  `i % 3 == 1` are held out; both methods are fitted on the remaining nodes of every slice and
  evaluated at the held-out κ (interior, so supported for both methods).
* Chronological split: eligible sessions sorted by session date; first 60% training, last 40%
  holdout; no shuffling, no reuse, no second holdout look.
* Uncertainty: moving block bootstrap over holdout sessions in chronological order, block length 5
  sessions, B = 2000 resamples, seed 101; 95% percentile interval. Report honest N = holdout
  sessions, number of blocks, and slices/nodes only as support counts.
* Attrition/support: counts by exclusion reason from `screen_quotes`, parity conflicts, sessions
  dropped by reason (below strike/expiry minimum, `BANDS_INFEASIBLE`, solver failures), and the share
  of evaluation points flagged `UNAVAILABLE`/`EXTRAPOLATED`.

## 10. Procedure (`evaluate.py`)

* S0: refuse to run (exit 2, recorded in `RUNS.log`) if sha256(`PREREG.md`) ≠ the `PREREG_SHA256` in
  `FREEZE.log`.
* S1: reproduce the inspected baseline: for each of the 28 chain files above, `skew_map(chain)` vs the
  `options_skew/snapshots.parquet` rows with `source == polygon_gex` and `asof` date equal to the chain
  date, on `otm_put_iv`, `atm_call_iv`, `skew`, `spot`, `tenor_days` (abs tol 1e-9) and `n_strikes`
  (exact). Also check `skew_map` output bytes are identical before and after importing the Q01
  module. Pre-disclosed expectation from one pre-freeze probe (2026-08-13: 330/330 rows match).
* S2: eligibility census of every candidate in §5: per source, presence of per-contract bid, ask,
  quote timestamp, quote condition, exact expiry/settlement, contract style, forward/discount, and
  European index roots; count of eligible sessions.
* S3: apply the §4 data gate. Below gate → `INSUFFICIENT_DATA`, write the exact missing input, skip S4.
* S4: the §8–§9 comparison, only if S3 passes.
* S5: NON_EVIDENTIAL synthetic mechanics: the S4 code path executed on seeded synthetic SVI sessions
  (known truth) to show the pipeline runs end to end; never reported as market evidence.
* Every run appends one JSON line to `RUNS.log`: command, exit code, PREREG sha256, input and output
  sha256s. No wall-clock values are read by `evaluate.py`.

## 11. Falsifier and stop rule

* Falsifier (from the brief): if constrained fitting is unstable, unsupported or materially worse than
  the convex benchmark, retain the benchmark/quality diagnostic and do not ship the fitted surface as
  reliable.
* Stop rule: one run of S0–S5 on the frozen inputs. If S3 fails, stop with INSUFFICIENT_DATA. A rerun
  is allowed only for a crash or a hash mismatch (recorded), never to change an outcome. No new data
  source is fetched, purchased or requested by this study.

## 12. Tolerances

Node/price tolerance 1e-8; butterfly `g` tolerance 1e-8 (dense check `min g ≥ −1e-8`); calendar
tolerance 1e-8; LP admissibility 1e-6 spread units; minimum spread 1e-6 (normalized units); dense grid
401 points per slice (tests also exercise 2001).

## 13. Pre-freeze disclosure

Before this freeze the author (a) inspected column schemas and row counts of the candidate sources
(no eligible European index-option quote chain was found, so no evaluation outcome exists to read),
(b) ran one baseline probe on the 2026-08-13 chain (330/330 incumbent rows reproduced), and (c) ran
synthetic smoke checks and the hermetic test suite of the reference module. None of these is an
evaluation outcome of the §8 comparison.

## 14. Standing kills, holds and scientific restrictions

No outcome audition (DNR:KILL-OUTCOME-AUDITION); no language-model origination of any signal, score or
escalation (DNR:KILL-LLM-ORIGINATION); no fused composite (DNR:KILL-FUSED-COMPOSITE); no positioning
fusion (DNR:KILL-POSITIONING-FUSION); no regime scorecard or composite reliability monitor
(DNR:KILL-REGIME-SCORECARD, DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR); no causal-DAG alpha
(DNR:KILL-CAUSAL-DAG-ALPHA); holds DNR:HOLD-PSS-AF1-FINRA and DNR:HOLD-PSS-CD1-CROWDING untouched.
Historical charm/DOI/skew nulls remain negative evidence; the October options research exception grants
no production authority. Q01 infers no dealer inventory, measures no market impact, and claims no alpha.

## 15. Limitations (declared at freeze)

* L1: Forward/discount are inputs (Q12 dependency); calendar constraints assume deterministic
  proportional carry. A wrong forward shifts κ and can create or hide calendar arbitrage.
* L2: European style only; American contracts are rejected until Q02 is independently qualified.
* L3: private normalized Black-76 call inside the module (SVI → price conversion only); a shared
  kernel owner (F03) would supersede it at integration.
* L4: PL benchmark is exact between nodes and unavailable outside the observed support; SVI
  extrapolates and flags `EXTRAPOLATED`. Neither supplies tail density outside support.
* L5: the empirical comparison cannot run on the retained data at this vintage (see §4 gate); any
  conclusion beyond the mechanical suite waits for an eligible cohort.
