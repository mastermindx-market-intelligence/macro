# Q12 verdict — INSUFFICIENT_DATA

Brief: Q12, robust option-implied forward and carry-consistency estimates.
Author: Claude Opus 5.5 (model ID claude-opus-5-5). PREREG.md sha256
b6bfe4b12e07056dd229b8d181a220b0bc6f1403e71e7b071683d6f57fa200b3, frozen 2026-10-09T10:07:38Z.

## Verdict

**INSUFFICIENT_DATA.** The single pre-registered empirical comparison (H2, leave-one-strike-out
against the incumbent mid-parity point, with a moving-block day bootstrap) was **not run**,
because eligibility rule E found **0** eligible stores. That covered 25,246 parquet schemas
and 39,175 json/jsonl/csv heads under macro-main/data at vintage cdab6268, with 0 census
errors. The alias pass added after the independent audit (PREREG_AMENDMENT.md A2) also
found 0 candidates.

**Exact missing input:** synchronized, same-timestamp call/put two-sided bid/ask quotes, each
leg carrying strike, expiry, deliverable/multiplier and settlement/exercise identity
(preferably European cash-settled index options such as the SPX/XSP class), plus a dated
discount curve interpolated to expiry.

## Closest retained stores and why they do not qualify

| Store | Has | Missing |
|---|---|---|
| data/polygon_gex/chains/*.parquet (28 files) | strike, expiry, right, vendor IV, greeks, OI, asof | any bid/ask or option price; contract identity beyond ticker. Vendor IVs use an unknown r/q, so inverting them to prices would manufacture the precision under test. |
| data/flow_signals/ledger.parquet | one-sided trade-print events with avg_price, spread_median_usd, quote age | bid/ask LEVELS; two-sided quotes; settlement/exercise identity |
| data/tape_flow/** | bid-SIDE / ask-SIDE premium flow aggregates | quotes of any kind |
| data/thetadata_eod | manifest only (no retained rows) | everything |
| options_ivspread / options_skew / options_dislocation / options_surface | aggregates | per-contract quotes; options_dislocation itself records price-space parity as `structurally_absent` |
| options signal episode/campaign outcomes | — | they record `no_executable_nbbo_quote_path` |

Descriptive diagnostic D1 (never a verdict input): in flow_signals, 7,611 (session, root,
expiry, strike) keys have both call and put prints. The nearest call/put print gap has a
median of 0.073 s, and 74.3% of keys have a gap of 1 s or less. Timing alone would therefore
not block a future study. The missing piece is the two-sided quote levels and the contract
identity.

## Baseline reproduction (results/baseline_repro.json)

The incumbent was run on synthetic controls, with D = 0.98, T = 0.5 and r set so that
e^{-rT} = D:

| Case | Incumbent B1 point | Q12 |
|---|---|---|
| European witness, true F = 101 | 101.0 | consistent [100.83673469387755, 101.16326530612245] (matches the MATH_RESULTS witness) |
| crossed call quote | 101.0714 (returned silently) | unavailable (crossed_call) |
| stale put leg | 101.0 (it cannot see clocks) | unavailable (stale_put, asynchronous_legs) |
| incompatible strikes (101 vs ~101.88) | 101.0 (no flag) | incompatible, reported, not averaged |
| American pair | 101.0 | unavailable (requires Q02 American adjustment) |

The incumbent price-space baseline B2 (`options_dislocation`) is reproduced as absent: the
store has no option price column.

This is a contract demonstration on synthetic data, not empirical evidence about markets.

## What this does and does not establish

* It does establish that the reference implementation satisfies the six acceptance
  requirements on hermetic synthetic tests (50 passed). It also establishes that no local
  store could support an honest empirical comparison.
* It does not establish whether quote-implied forwards are stable or informative in real
  markets. It grants no production authority, it is not an executable arbitrage and it is
  not a spot forecast. Carry remains jointly identified (r - q - borrow).

## Independent audit and finisher changes

The independent audit returned PASS_WITH_FIXES: 0 blockers, 0 majors, 9 minors. The finisher
changed or disclosed the following.

* **Exact D-band combination (PREREG_AMENDMENT.md A1).** The original code widened each
  pair over the discount band and then intersected. That is an outer bound and could report
  a forward that no single D supports. `combine_intervals` now takes the union over D of
  the per-D intersections, computed exactly. With u = 1/D every bound is linear in u, so
  convex-hull envelopes give O(n log n). Tests:
  `test_dband_pairs_need_a_common_discount_factor` (the 82 / 83.5 counterexample),
  `test_dband_exact_matches_brute_force_grid` (24 seeds against a 20,001-point u grid,
  covering consistent, no-common-D and disjoint cases) and
  `test_dband_point_band_equals_plain_intersection`. Point-band results are unchanged,
  including the witness interval and results/baseline_repro.json.
* **Conservative intersection, not robust consensus.** One valid but mispriced pair can make
  an otherwise consistent group incompatible. The method surfaces that pair in `conflicts`
  and never outvotes it. Whether that is too fragile on real chains is untested here.
* **Census heuristic.** The exact-name column sets could miss renamed columns. An alias
  pass now tokenizes names and keys (PREREG_AMENDMENT.md A2) and found 0 candidates. The
  census is still schema- and head-based: it cannot see quote fields that live in
  undocumented nested blobs.
* **Test hardening.** The req3 injection test now covers stale, future, async, crossed and
  locked pairs. The no-silent-activation test pins the exact public callable surface.
* **Provenance.** results/*.json are rewritten by each evaluate.py run. RUNS.log is the
  sole provenance record and lists every run with its input and output sha256s: one crash,
  the original run and the finisher re-run at 2026-10-09T10:38:33Z. The hash-guard claim
  was rechecked on a tampered scratch copy of PREREG.md, which exited 3 with
  `REFUSED: PREREG.md sha256 differs from FREEZE.log`.

## Unblocking path (not authorized here)

Retain a licensed same-timestamp NBBO snapshot store for a European index option chain, with
contract metadata. Then write a PREREG_AMENDMENT.md fixing the column mapping before any
outcome is read, and run evaluate.py. American single-name use additionally waits on Q02.
