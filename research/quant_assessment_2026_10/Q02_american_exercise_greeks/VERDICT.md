# Q02 — American-exercise and discrete-dividend pricing/Greek qualification — VERDICT

**VERDICT: INSUFFICIENT_DATA.** The single empirical trial (E2) was not run.

Research only. `engine/options_american_exercise.py` is a reference module with
`RESEARCH_ONLY = True` and `VERDICT = "INSUFFICIENT_DATA"`. Nothing imports, wires, registers,
schedules, promotes, gates or activates it. Every model output on a real contract stays
UNAVAILABLE.

Author: Opus 5.5 (model ID `claude-opus-5-5`), Q02 AUTHOR role.

## 1. Why: the exact missing inputs

The data gate HG (PREREG section 9) needs these terms per contract. The licensed retained data
root (`/Users/chriswong/Documents/Cluade/macro-main/data`, vintage `cdab6268`, read-only) does
not supply five of them for any row of the 28 frozen chain snapshots:

| PREREG stage | input | rows with support (of 4,418,705) | any joinable source elsewhere under the data root |
|---|---|---|---|
| 4 | exercise style per contract | 0 | none (no key matches `exercis`, `option_style`, `american` or `european`) |
| 5 | deliverable / multiplier per contract (incl. adjusted deliverables) | 0 | none real. The 3 name-only candidates are false positives: `index_gex_history/_manifest.json` `contract_multiplier` is a GEX scaling constant; `regime/latest.json` and `signal_archive/us_regime.parquet` carry `vol_match_multipliers` (yield-curve PCA) |
| 6 | settlement clock (AM_OPEN / PM_CLOSE) | 0 | none |
| 7 | point-in-time declared cash-dividend schedule (known-at, ex-time, amount) complete through expiry | 0 | none: no key anywhere matches an ex-date or a dividend-amount pattern |
| 8 | option price (bid / ask / mid / last) | 0 | none in the chains. The vendor `iv` column is a vendor-model output, never used as a price (PREREG section 9) |
| 9 | rate | 4,418,705 (SOFR on or before the snapshot date) | n/a: present |

More detail on what is missing:

- **Dividend schedule.** `massive/capability_manifest.json` (sha256 `a47340db…f29051`) lists a
  vendor `ref_dividends` endpoint as entitled, but nothing from it is retained locally, and
  fetching it is out of scope (no network, no vendor downloads).
- **edgar.** `edgar/fundamentals_panel.parquet` (sha256 `9af85734…8bebc4`) carries an annual
  fiscal-year `dividends` cash-flow aggregate with no ex-date, per-share amount or known-at
  time, so it is ineligible.
- **Rate.** Rate shows 0 rows in the cumulative attrition only because every earlier stage
  already reached 0. On its own, every row has a SOFR fixing.

To make E2 runnable, the following must be retained locally under the licence and joined
point-in-time to the chain rows, while vendor-model `iv`/`delta`/`gamma` stay excluded:

- per-contract exercise style;
- deliverable and multiplier, with adjusted-deliverable terms;
- settlement clock;
- an observed option price (bid/ask or mid) for both legs;
- a declared dividend schedule with known-at, ex-date and amount.

## 2. Gate HG (both arms)

Run 3 under amendment A2 (`results/gate.json`, byte-identical to run 2 under A1):

| criterion | threshold | strict arm | sensitivity arm (ASSUMPTION) |
|---|---|---|---|
| (a) dates with ≥ 1 eligible call–put pair, train half | ≥ 10 of 14 | 0 | 0 |
| (a) same, test half | ≥ 10 of 14 | 0 | 0 |
| (b) test-half underlyings with eligible pairs | ≥ 10 | 0 | 0 |
| (c) eligible pairs priced on both legs | all | vacuous (0 pairs) | vacuous (0 pairs) |
| **HG** | all hold | **false** | **false** |

- Structural same-underlying, same-expiry, same-strike call–put pairs across all dates:
  1,829,760. Pairs priced on both legs: 0.
- Strict arm: fails first at stage 4 (exercise style).
- Sensitivity arm: fails first at stage 5 (deliverable/multiplier).

The sensitivity arm is the labelled ASSUMPTION "declared OCC product-class exercise-style map,
support reporting only, not a trial".

- It maps SPX, SPXW, XSP, NDX, NDXP, RUT, RUTW, MRUT, VIX, VIXW, DJX and XEO to European, and
  everything else to American.
- No European-mapped root occurs in the retained chains (`european_roots_seen = []`), so the
  arm maps all 4,418,705 rows to American.
- Stages 5–8 then remove every row.

## 3. Attrition census

28 chain dates:

- train: the first 14 dates (2026-06-15 … 2026-07-15);
- test: the last 14 dates (2026-07-17 … 2026-08-13).

Counts are `[rows, distinct (date, underlying)]`, from `results/attrition.json`.

| stage | marginal | cumulative, strict | cumulative, sensitivity |
|---|---|---|---|
| 1 rows | 4,418,705 / 9,550 | 4,418,705 / 9,550 | 4,418,705 / 9,550 |
| 2 parseable OCC/OSI | 4,418,705 / 9,550 | 4,418,705 / 9,550 | 4,418,705 / 9,550 |
| 3 standard-looking root | 4,404,397 / 9,550 | (partition, carried) | (partition, carried) |
| 3 adjusted-looking root | 14,308 / 224 | (partition, carried) | (partition, carried) |
| 4 exercise style | 0 / 0 (map: 4,418,705 / 9,550) | 0 / 0 | 4,418,705 / 9,550 |
| 5 deliverable/multiplier | 0 / 0 | 0 / 0 | 0 / 0 |
| 6 settlement clock | 0 / 0 | 0 / 0 | 0 / 0 |
| 7 PIT dividend schedule | 0 / 0 | 0 / 0 | 0 / 0 |
| 8 option price | 0 / 0 | 0 / 0 | 0 / 0 |
| 9 rate | 4,418,705 / 9,550 | 0 / 0 | 0 / 0 |

OCC consistency (rows):

- call/put matches `is_call` for 4,418,705;
- expiry matches for 4,418,705;
- the symbol strike matches `K` for 4,404,201;
- root relation unknown: 0.

The 14,504 strike mismatches are close to the adjusted-looking-root count. That is consistent
with adjusted deliverables, which is exactly why an explicit deliverable is required.

SOFR: 2,128 fixings, declared unit percent, converted as percent / 100; 100 % lie within the
module's rate bounds.

## 4. Fail-closed selector on real rows

The module's `select_model` was applied to terms from the data alone (`results/selector.json`).
Vendor `iv` is never used as sigma; dividends are None; valuation = cutoff = the `asof` minute.

- **Strict arm:** 4,418,705 rows → UNAVAILABLE. Reasons: `exercise_style_unknown`,
  `deliverable_unknown`, `multiplier_unknown`, `settlement_clock_unknown`,
  `market_input_missing`.
- **Sensitivity arm:** 4,418,705 rows → UNAVAILABLE, with the same reasons minus
  `exercise_style_unknown`.
- Rows decided as anything other than UNAVAILABLE: 0 in both arms. Rows without a valuation
  clock: 0.

No multiplier of 100 was assumed anywhere.

## 5. Baselines

**Code baseline (incumbent `engine/greeks.py`, sha256 `d471f5ed…a8d9c`): reproduced.**

- Over 28 cases, the module's analytic European delta, gamma, vanna and charm equal
  `bs_greeks` with max abs diff 0.0 for every Greek (tolerance 1e-12).
- A degenerate input returns NaN in both.

**Empirical baseline B1 (European continuous-yield BS, q = 0, inverted to observed mid): not
reproducible, and its absence is proven.**

- The union of the 28 chains' columns is `K, T, asof, delta, expiry, gamma, is_call, iv, oi,
  spot, strike_ticker, underlying, volume`.
- No price column exists, so B1 cannot be computed on these data.
- Treating the vendor `iv` as an inverted price would be a manufactured input.

## 6. E1 numerical qualification (synthetic, PREREG section 7): all pass

85 checks, 0 failed, at the finest grid 4N = 400 (`results/e1_numerical.json`). Worst-case values
against tolerance:

| ID | check | worst value | tolerance |
|---|---|---|---|
| T1a | European FD price vs analytic | 1.57e-3 | 5e-3 |
| T1b | European FD delta vs analytic | 1.07e-4 | 2e-3 |
| T1c | European FD gamma vs analytic | 2.55e-5 | 5e-4 |
| T1d | European FD vanna / charm vs analytic | 1.11e-3 / 4.16e-4 | 5e-3 + 5e-2·abs(analytic) |
| T1e | module analytic vs `engine/greeks.py` | 0.0 | 1e-12 |
| T1f | 4N error < N error (price, delta, gamma; ATM) | strict, 6/6 | strict |
| T1g | one-dividend European FD vs Gauss–Hermite quadrature | 3.68e-4 | 1e-2 |
| T2a | American put ≥ intrinsic at every node | min 0.0 | ≥ −1e-10 |
| T2b | American ≥ European on the same grid | min 0.0 | ≥ −1e-10 |
| T2c | put ≤ K, call ≤ S | strict, 3/3 | strict |
| T2d | American call (q = 0, no dividend) vs European | 1.46e-3 | 5e-3 |
| T2e | American put FD vs CRR (2,000 steps), K ∈ {80, 100, 120} | 1.13e-3 | 2e-2 |
| T2f | deep-ITM D = 5 American call FD vs CRR-VN | 2.32e-4 | 5e-2 |
| T2f | early-exercise premium, American − European | 3.83 | ≥ 0.5 |

Grid-refinement classification over 16 cases × 5 quantities (80 classifications):

- 74 CONVERGED and 6 INTERVAL.
- The 6 INTERVAL are all prices: the European call and put at K = 100 for T = 0.5 and T = 0.1,
  the European call at K = 120, T = 0.5, and the American put at K = 100, T = 0.5.
- No case is near the exercise boundary.
- The price rule (atol 1e-3, rtol 1e-4) is stricter than the payoff kink at the strike lets the
  N → 2N → 4N sequence settle. These prices are therefore reported as intervals with no point
  value, which is the conservative behaviour PREREG section 8 asks for.
- Their accuracy against the analytic value still meets T1a.
- `test_req4_european_atm_price_interval_brackets_the_analytic_value` pins that the interval
  contains the analytic price.

## 7. Absence scan (names and keys only)

Scope:

- file names, parquet schemas, CSV header lines, and JSON/JSONL/gz keys within the first
  8,388,608 bytes of each file;
- no row values were read.

Coverage:

- 25,246 parquet, 39,180 JSON-like and 11 CSV files;
- 14 spreadsheets left unscanned (all under `release_forecast/cpi_truth/`, the CPI table
  archive);
- inventory 71,672 files, inventory digest sha256 `d8ec7a5f…a2cc`, read errors 0.

Candidates:

- `dividend_schedule` (ex-date AND amount key): 0 files.
- `option_terms` (contract id AND exercise/deliverable/settlement key): 3 files, all name-only
  false positives (section 1).
- `option_quote` (contract id AND quote key): 23 files. These are:
  - biocatalyst clinical-trial fixtures (8);
  - `options_flow/signing_gate.json`;
  - `options_signal_campaign/campaigns.jsonl`;
  - `options_signal_episode/*` (episode and outcome logs with option-trade-price-like keys);
  - the two regime files.

Even if a price from `options_signal_episode` were joined to the chains, stages 4, 6 and 7
have zero joinable sources, so HG cannot be lifted by any local source.

## 8. Honest N and the trial family

- E2 was NOT_RUN.
- Eligible pairs: 0. Test dates with eligible pairs: 0. Underlyings: 0. Bootstrap blocks
  (block 5): 0.
- No point estimate, interval or decision exists, and none is implied.
- The trial family stays at exactly one unspent primary trial: the test-half mean of `D_d`.

## 9. Run history and amendment

`RUNS.log` holds every run and is append-only.

1. **Run 1** (`evaluate`, evaluate.py sha256 `4fc136ee…1ccd15`): exit 1,
   `FAILED KeyError: 'date'`, 1.9 s.
   - Its `RUNS.log` block does not carry the evaluate.py hash, because hash logging was added
     by A1. The hash above is recorded in A1 and cross-referenced in A2 (audit finding M3).
     The log itself is append-only and was not edited.
   - The SOFR parquet stores `date` as the pandas index.
   - It failed before the census, so no census, gate or E2 outcome was read.
   - Its three outputs are preserved in `results/run1_failed/`. They are byte-identical to the
     run-2 `inventory.json`, `baseline.json` and `e1_numerical.json`.
2. **Amendment A1** (`PREREG_AMENDMENT.md` sha256 `1842d4ae…3509`, frozen in
   `AMENDMENT_FREEZE.log` before the rerun).
   - It fixes the SOFR read (`ignore_metadata=True`), makes the summary reason data-driven,
     adds the amendment-aware one-run guard and logs evaluate.py's own hash.
   - It changes no threshold, grid, tolerance, split, gate, bootstrap or decision rule.
   - The module and test are byte-identical.
   - It authorizes exactly one run.
3. **Run 2** (`evaluate`, evaluate.py sha256 `80b0f449…4553`): exit 0, COMPLETED, 91.8 s,
   verdict INSUFFICIENT_DATA. It used the single A1 run.
4. **Pytest runs** (two logged blocks, A1): exit 0, `73 passed` each.
5. **Amendment A2** (`PREREG_AMENDMENT.md` sha256 `25dcc233…7221`, frozen in
   `AMENDMENT_FREEZE.log` before run 3; written before any run-3 output existed).
   - It answers the independent audit (PASS_WITH_FIXES, 0 blockers, 0 majors, 4 minors).
   - M1: the vanna vol bump used `min(0.01, 0.5·sigma)`, and near SIGMA_BOUNDS the bumped
     solve raised ValueError. The bump is now always the frozen 0.01; when sigma ± 0.01 leaves
     (0.01, 5.0), vanna is UNAVAILABLE with reason `vol_bump_out_of_bounds` and nothing
     raises. 8 tests were added (73 → 81). Module sha256 `ba222da9…7cc7fe1` → `0b27f323…eb38a`;
     test sha256 `439a0428…65d7d5` → `df981930…e1f6`.
   - M2, M3 and M4 are disclosure and documentation fixes (section 10).
   - It changes no threshold, grid, tolerance, split, gate, bootstrap or decision rule, and
     evaluate.py is byte-identical (`80b0f449…4553`). It authorizes exactly one run.
6. **Run 3** (`evaluate`, evaluate.py sha256 `80b0f449…4553`): exit 0, COMPLETED, 84.0 s,
   verdict INSUFFICIENT_DATA. As A2 predicted, only `inventory.json` changed (it records the
   new module and test hashes: `145a64c0…` → `11e349c8…9c4f`). Baseline, E1, attrition,
   selector, absence scan, gate and summary are byte-identical to run 2. It used the single
   A2 run; any further run needs amendment A3.
7. **Pytest run** (logged, A2): exit 0, `81 passed`.

## 10. Disclosures and limitations

- **Pre-freeze inventory.** Before PREREG was frozen, inventory and schema facts were examined
  (PREREG section 0), including the first rows of one chain file. The expected gate failure was
  disclosed in PREREG section 0 before any run.
- **Post-run-1 probe.** It read schema metadata only (parquet footers and pandas metadata, no
  row values) for SOFR and the 28 chains, to diagnose the run-1 failure. It is disclosed in A1.
- **Root heuristic.** "Standard-looking root" (root equals underlying, no digit suffix) is a
  heuristic partition, not a contract-term source. It feeds no eligibility decision.
- **Scan caps.** The absence scan is name/key based:
  - a source whose keys use names outside the declared token groups would be missed;
  - JSON keys beyond the first 8 MB of a file were not seen;
  - the 14 CPI spreadsheets were not opened.

  None of these could supply a per-contract options schedule given their directories, but this
  is a judgement, not a scan result.
- **Guard exercise (audit M2).** A1 reported that its amendment-aware guard was exercised on a
  synthetic data root (exits 2, 0, 3, 2, 0, 2), but those runs were not retained and cannot be
  recovered. A2 re-exercises the same guard decisions in a retained harness,
  `guard_check/guard_check.py`, with its transcript in `guard_check/transcript.json` (all
  steps pass). Two differences from A1's description: the synthetic data root is empty, so an
  admitted run stops at the stage-1 inventory with exit 4 instead of 0; and the one-run step
  seeds one labelled synthetic COMPLETED block, because an empty root cannot produce one. The
  harness never touches the real `RUNS.log`, `results/` or data root.
- **Inlined incumbent formula (audit M4).** The test inlines `engine/greeks.py`'s Black-Scholes
  formula pinned to greeks.py sha256 `d471f5ed…ba8d9c`, because hermetic tests may not open
  repository files. CI therefore cannot see drift in greeks.py. If greeks.py changes, the
  inlined copy must be re-pinned by hand; evaluate.py's stage-1 inventory refuses (exit 4) on
  the mismatch, so an evaluation cannot silently run against a drifted incumbent.
- **Vendor fields.** Vendor `iv`, `delta` and `gamma` were excluded on purpose (PREREG section
  9). No option price or dividend was reconstructed from them.
- **Scope of E1.** E1 qualifies the numerical method on synthetic relative-unit scenarios only.
  It says nothing about whether real contracts are mispriced by the incumbent, which is the open
  E2 question.
- **No signal.** Charm and the other Greeks are model sensitivities with declared units, never a
  signal. Historical charm/DOI/skew nulls remain negative evidence.
- **Standing restrictions.** No language model originated any signal, score or escalation.
  Standing kills and holds are untouched.

## 11. What ships (falsifier branch, PREREG section 11)

Per the brief's falsifier, only the applicability guard and the qualified reference ship, as
research reference, not wired:

- the fail-closed selector;
- the point-in-time dividend filter;
- the explicit unit converters;
- the refinement classifier;
- the numerical reference pricer.

The incumbent `engine/greeks.py` is unchanged.

The open question for the incumbent's call sites stays open: is a European continuous-yield
q = 0 formula being applied to American, discrete-dividend or adjusted-deliverable contracts?
Every real-contract output of the new module is UNAVAILABLE until the missing inputs in
section 1 exist locally.

## 12. Independent audit

An independent read-only audit returned PASS_WITH_FIXES: 0 blockers, 0 majors, 4 minors.

| finding | what it found | resolution |
|---|---|---|
| M1 | The vol bump `min(0.01, 0.5·sigma)` pushed `fd_solve` outside SIGMA_BOUNDS near the edges, which raised ValueError | Fixed under A2: the bump stays 0.01, vanna fails closed (`vol_bump_out_of_bounds`), 8 new tests; run 3 reproduced every result |
| M2 | A1's synthetic guard runs were not retained | Disclosed; re-exercised and retained in `guard_check/` (transcript all-pass) |
| M3 | Run 1's `RUNS.log` block lacks the evaluate.py hash | Cross-referenced (A1, A2, section 9); the append-only log is not edited |
| M4 | The inlined greeks.py formula is hash-pinned, so CI cannot see drift | Documented in the test file, A2 and section 10; re-pin by hand on a greeks.py change |

The verdict is unchanged: INSUFFICIENT_DATA. Gate HG fails on both arms, E2 was not run, and E1
passes 85 of 85 numerical checks.
