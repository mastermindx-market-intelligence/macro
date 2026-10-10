# Q01 — Bid/ask-aware, arbitrage-constrained volatility surface: verdict

**VERDICT: INSUFFICIENT_DATA**

The preregistered surface comparison (PREREG §8–§9) did not run. The retained licensed local data at
vintage `cdab6268` holds **zero** eligible sessions; the PREREG §4 gate requires at least 100 sessions,
with at least 40 in the holdout. The challenger is **not** described as a reliable surface, and neither
method has an empirical edge. The research artifact is the reference module, its hermetic invariant
suite and this record.

**Exact missing input.** The study needs a same-session European cash-settled index-option quote chain
(roots SPX/SPXW/XSP/NDX/RUT) with:

* per-contract bid, ask, quote timestamp and quote condition;
* exact expiry timestamp and AM/PM settlement convention;
* an owner-supplied per-expiry forward and discount (Q12 or another trusted forward owner);
* retained rights;
* at least 100 chronologically ordered sessions.

This wording is the `exact_missing_input` in `verdict.json`.

| Item | Value |
|---|---|
| Brief | Q01, rank 1/20, options mathematics |
| Author model (served) | Opus 5.5, model ID `claude-opus-5-5` (Claude Code, workflow-harness AUTHOR role) |
| Module | `engine/options_arbfree_surface.py` (sha256 `cff9f58d38579f01bcdab0eb10eea16a82a237e4b828cd7ebdf4f9260109d194`; the author's run-1 version was `6bb3fae8…`) |
| Tests | `tests/test_options_arbfree_surface.py` (sha256 `c03147b826e822b30fa3eb389b39d661b784a96b1c6e4a4d4a2236f2bc3be016`), 18 tests (the author's run-1 version was `4a791ce9…` with 17 tests) |
| PREREG | sha256 `9e152194440979b96b9ee80658c844b699ce065bd9f6c25e2a610c03c568f60b`, frozen in `FREEZE.log` before any outcome was read |
| Amendment A1 | `PREREG_AMENDMENT.md`, sha256 `fd5bbe42ab0b7fd007b399bcbe6bb642531b524304d389ccc637180af56f9801`. It adds an exhaustive schema sweep and was recorded in `FREEZE.log` before the first `evaluate.py` run. |
| Amendment A2 | `PREREG_AMENDMENT_A2.md`, sha256 `e203ce79b3f200f15a7046476529180f2a70b968dbdb76de04d9643e789a886f`, recorded in `FREEZE_A2.log`. This finisher amendment binds any **future** S4 run: it adds an absolute `L_svi` bar, a population-wide holdout and session counting. It was written after runs 1 and 4 and before any further outcome. The current `evaluate.py` does not implement it, and it changes no result here. |
| Evaluation runs | `RUNS.log` line 1 (`"run": 1`, author): exit code 0, stage S5, 174.40 s wall time. `RUNS.log` line 4 (`"run": 4`, finisher re-run after the audit code fixes): exit code 0, stage S5, all four outputs byte-identical to run 1. |

## Evidence: the preregistered evaluation (S0–S5)

`evaluate.py` produced the same result twice:

* **Run 1:** the author's run, described below.
* **Run 4:** a re-run by the finisher after two audit-driven code fixes (see "Independent audit and
  finisher fixes"). It uses module `cff9f58d…`, tests `c03147b8…` and `evaluate.py` `3441d20a…`, and
  records 0 input-hash mismatches. Its four output sha256s are identical to run 1's, so every number
  below holds for both runs.

Invocation (thread caps and `nice -n 10` per the commission; wall time 174.40 s, exit 0):

```
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2 nice -n 10 \
  /opt/homebrew/bin/python3.12 \
  <staging>/Q01/research/quant_assessment_2026_10/Q01_arbitrage_constrained_surface/evaluate.py
```

`RUNS.log` records the resolved interpreter path (`/opt/homebrew/opt/python@3.12/bin/python3.12`), the
absolute script path and the thread environment.

`RUNS.log` line 1 records the following.

**Command and environment**
* The argv.
* The thread environment.

**Hashes**
* PREREG sha256, frozen and observed (equal).
* Amendment sha256, frozen and observed (equal).
* `FREEZE.log` sha256 `c3d1f6a33ad62cc2d836b801e09eafb3e7aa0421744726f648696e56ea5e56b3`.
* Code sha256s for the module, the tests and `evaluate.py` (`f092e1ec773e4169d300b4eecb2915594e51c3bde6af2ae4f9f0b1815a10f399`).

**Inputs**
* All 41 declared input sha256s, with zero hash mismatches.
* The data root and vintage.

**Outputs**
* `baseline_reproduction.json` `0ed64f4524725c7845cd8a44ce2c473f287accee3ecea524ef02641e67267d66`
* `eligibility_census.json` `be7c5ef12125c8ea9005a928e3c2406a959b200e579500601cb7093f1d4959b0`
* `synthetic_mechanics.json` `0ebff8d669ce60537510ad89c4f81d0a089b4af09bebda675da298ee519cd867`
* `verdict.json` `6ab992a779ea8e82211e64129d6b187f6d6dcafe1f1e36bc939836770ef7c4de`

### S0 — freeze check

The sha256 of `PREREG.md` equals `PREREG_SHA256` in `FREEZE.log`, and the amendment hash equals
`AMENDMENT_SHA256`. `evaluate.py` exits 2 (logged) on any mismatch.

### S1 — incumbent baseline (`engine/options_skew.skew_map`): NOT_FULLY_REPRODUCED under the frozen rule

The frozen rule (PREREG §10 S1) compares each of the 28 declared polygon_gex chain files with the
`options_skew/snapshots.parquet` rows whose `source == polygon_gex` and whose `asof` date equals the
chain date. It checks five fields at abs tol 1e-9 plus `n_strikes` exactly.

| Total | Rows |
|---|---|
| Snapshot rows on chain dates | 4,171 (18 dates; 10 chain dates have no snapshot rows) |
| Exact match | 661 (2026-08-12 331/331, 2026-08-13 330/330; the pre-disclosed probe expectation for 08-13 was met) |
| Mismatch | 3,502 |
| Missing in recompute | 8 |
| Recomputed underlyings absent from the same-date snapshot | 5,349 (the snapshot stores a subset) |

**Disclosed post-run diagnostic** (`diagnose_baseline.py`, `RUNS.log` lines 2–3, `kind=post_run_diagnostic`):

* It is not an evaluation run, not a trial, and it does not change the verdict or the frozen S1 state.
* It reads only the S1 inputs declared in PREREG §5 and records their hashes.
* Diagnostic run 1 reported a tie-break "best chain" on zero-match dates, which was misleading. Run 2
  reports `None` there and adds a previous-declared-chain comparison. Both runs are logged.
* Output: `baseline_divergence.json` sha256 `c88c9f81c22dfdc0488ffdce037f98730992a6fd845f73cfa47ef998461b0d80`.

| Snapshot dates | Rows | Reproduced exactly by |
|---|---|---|
| 2026-08-12, 2026-08-13 | 661 | the **same-date** chain file |
| 2026-07-02, 07-10, 07-21, 07-22, 07-28, 07-29, 07-30 | 1,946 | the **immediately preceding declared** chain file (100% of rows on every one of these dates) |
| 2026-06-24, 06-26, 06-30, 07-01, 07-07, 07-13, 07-20, 07-27, 08-06 | 1,564 | **no** declared chain file (0 rows on every date) |

Reading:

* The incumbent code reproduces the stored output **exactly** on 9 of 18 snapshot dates (2,607 of
  4,171 rows, 62.5%) once source-date alignment is taken into account.
* Up to 2026-07-30 the stored snapshot stamped D was built from the chain file of the previous
  available date. By 2026-08-12 the convention is same-date. The divergence is therefore an
  input/date-alignment property of the stored ledger, not a change in `skew_map`'s arithmetic.
* For 8 of the 9 unexplained dates, the declared file before date D is not the adjacent session file,
  which is consistent with (but not proof of) a lagged source file absent from the declared set.
  2026-07-01 is the exception: its preceding declared file is 2026-06-30 and still reproduces 0 of 6
  rows.
* The frozen S1 state stays **NOT_FULLY_REPRODUCED**. No PREREG rule was changed after the fact to
  turn it into a pass.

**Exact-leg compatibility (requirement 6, empirical leg):** passes. The `skew_map` digest on the
2026-08-13 chain is `a60bf3354098c5da1cee07ba1f36b9cfbaec0969a7dc4d0d48947e40ab09b18c` both before and
after importing the Q01 module, so `byte_identical=true`. In addition:

* `options_skew` module variables and callables are unchanged.
* `options_skew.py` sha256 is `8f68ad06c29ff9e05d6f4a710912b12a8523344d3b84a22524867e4711b38dce`,
  the same before and after.
* The import loads only `engine.options_arbfree_surface` as a new engine/lib module.
* `RESEARCH_ONLY=True`, and `authority()` is all False (display/rank/alert/score/deploy).

### S2 — eligibility census, including amendment A1's exhaustive sweep

* **Sources declared in PREREG §5:** none is contract-complete, and every one lacks per-contract bid
  and ask.
  * `options_skew/snapshots.parquet` and `options_surface/index_etf.parquet` carry SPX/SPXW roots,
    but they are derived IV/skew records, not quotes.
  * The 28 `polygon_gex/chains/*.parquet` files share one column set: `underlying, strike_ticker,
    expiry, K, T, is_call, oi, iv, gamma, delta, volume, spot, asof`. They have no index roots, no
    bid/ask, no quote clock, no style or settlement, and only date-level `asof`.
  * `thetadata_eod/_manifest.json` holds zero roots.
* **A1 sweep of the whole data root, without following symlinks:**

  | Category | Files |
  |---|---|
  | Total | 71,672 |
  | Parquet schemas read | 25,246 (0 unreadable) |
  | Text heads sniffed | 39,156 (0 unreadable) |
  | Text over the size limit | 19 |
  | Other | 7,251 |
  | Symlinks | 0 |

  * The candidate rule is a bid-like AND an ask/offer-like AND a strike-like AND an expiry-like field.
  * 3 candidates qualify, and **none is contract-complete**:
    * `flow_signals/ledger.parquet` (`c14b99cf…`): 115 roots, none of them a European index root.
      It lacks condition, discount, forward, quote timestamp, settlement and style. These are
      aggregated prints, not a quote chain.
    * `macro/news_rss_cache/news_rss_v2_2026-08-06.json` (`e1b9ecf3…`): a news cache; the matches
      are keyword collisions.
    * `options_flow/signing_gate.json` (`13bf08a8…`): a 4 KiB gate config with no index roots.
  * Non-candidate listing digest: `f4fd0bbd…` (71,669 entries).
* **Eligible sessions: 0.** No candidate needed manual review (exit 3 was not triggered).
  * The S2 count is 0 by construction when no source is contract-complete.
  * When a source is complete or undeterminable, S2 sets the count to `None`, and S3 stops with exit 3
    before the value is used.
  * The gate therefore fails closed rather than passing silently.
  * Amendment A2.4 requires the adapter amendment that admits such a source to define the real session
    count (audit finding 3).

### S3 — data gate: FAIL

0 eligible sessions against the requirement of ≥ 100 sessions with ≥ 40 in the holdout. The
verdict is therefore INSUFFICIENT_DATA, and S4 was skipped.

### S4 — primary comparison: NOT RUN

* No `D_s`, confidence interval, effect size or honest N exists for market data.
* The falsifier (PREREG §11) is **NOT_EVALUATED**. Consistent with the stop rule, the constrained SVI
  challenger is **not** shipped or described as a reliable surface.

### S5 — synthetic mechanics: NON_EVIDENTIAL (not market evidence, not a verdict input)

Design: 20 seeded synthetic raw-SVI sessions with known truth, two expiries, and 13 strikes.

| Quantity | Value |
|---|---|
| Split | 12 train / 8 holdout |
| λ (chosen in training) | 0.01; all three λ tie at a median training `L_svi` of 0 |
| Benchmark states | 8/8 `ADMISSIBLE` |
| SVI fit failures | 0/16 slices |
| Perturbation state-change fraction | 0 |
| Mean `D` | −3.485 spread units |
| Moving-block bootstrap CI | [−3.522, −3.457] (block 5, B 2000, seed 101, n = 8, 2 blocks) |

The mechanics decision is `KEEP`, which shows only that the S4 code path runs end to end.

**Design limitation revealed by S5 (L6, post-run, no PREREG change).** On held-out interior nodes the
piecewise-linear benchmark is a chord between retained nodes. For a convex call curve, a chord
overprices, so `L_bench` (≈ 3.3–3.7 spread units here) can far exceed `L_svi` (≈ 0) when the truth is
smooth. The non-inferiority margin `mean D_s ≤ 0.10` is therefore easy for a smooth parametric
challenger to pass, and on real data it would mostly test smoothness, not out-of-band fidelity. Any
future run on an eligible cohort should, through a new amendment frozen **before** data is read:

* also report `L_bench` and `L_svi` separately;
* add a node-retention sensitivity, for example holding out every 4th node;
* consider a convex smoothing benchmark (for example a convex spline LP) as a second competitor.

This study does not change its frozen bars after reading the S5 output.

The finisher amendment A2 (`PREREG_AMENDMENT_A2.md`, recorded in `FREEZE_A2.log`) turns the correction
into binding terms for any future S4 run:

* **A2.1:** the upper end of the CI of mean `L_svi` must be ≤ 0.10 spread units. This is joined to
  the `D_s` bar by AND.
* **A2.2:** that bar is computed over all cohort holdout sessions, whatever the benchmark state.
* **A2.3:** `L_bench` and `L_svi` are reported separately, plus an `i % 4 == 1` node-retention
  sensitivity that does not affect the verdict.

A2 only makes KEEP harder. No market outcome existed when it was written, and it changes nothing in
this verdict.

## Requirements (detail in `REQUIREMENTS.md`)

All six brief requirements are pinned by the hermetic suite (18 tests, exit 0). Only requirement 6
also has an empirical leg on real local data, the byte-identity check above. Requirements 1–5 are
mechanical properties of the reference. Their market-data behaviour remains unproven because no
eligible quote chain exists.

## Limitations

* **L1:** Forwards and discount factors are inputs (Q12 dependency, or a trusted owner forward).
  Calendar constraints assume deterministic proportional carry, so a wrong forward shifts κ and can
  create or hide calendar arbitrage.
* **L2:** European style only. American contracts are rejected until Q02 is independently qualified.
  That rules out every local chain.
* **L3:** The module has a private normalized Black-76 helper, used only for SVI→price conversion. At
  integration the single incumbent kernel owner would supersede it.
* **L4:** The PL benchmark is unavailable outside observed support. SVI extrapolates and flags
  `EXTRAPOLATED`. Neither supplies tail density.
* **L5:** The empirical comparison could not run at this vintage.
* **L6:** Chord bias of the PL benchmark at held-out convex points (above). Amendment A2 corrects
  this for any future run.
* **L7:** The stored `options_skew` polygon_gex ledger uses a mixed date-alignment convention (above).
  Any consumer joining that ledger to chain files by date must account for it. This is a
  **diagnostic finding**, not a repair, and no incumbent file was edited.
* **L8:** Absence findings cover the local data root at vintage `cdab6268` only. They do not show that
  no licensed vendor feed exists elsewhere, and no network source, R2 object or vendor was queried.

## Non-claims and standing law

The study makes none of these claims:

* no alpha, signal, score, rank, alert or escalation;
* no inferred dealer inventory;
* no realized market impact.

The verdict was originated by `evaluate.py` and the frozen rules, not by a language model
(DNR:KILL-LLM-ORIGINATION). No outcome audition took place (DNR:KILL-OUTCOME-AUDITION).

Standing kills that do not apply here:
* DNR:KILL-FUSED-COMPOSITE
* DNR:KILL-POSITIONING-FUSION
* DNR:KILL-REGIME-SCORECARD
* DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR
* DNR:KILL-CAUSAL-DAG-ALPHA

Holds DNR:HOLD-PSS-AF1-FINRA and DNR:HOLD-PSS-CD1-CROWDING are untouched. Historical charm/DOI/skew
nulls remain negative evidence. The October options research exception grants no production
authority.

## What would change this verdict, and the next owner action

The input named at the top must become available under retained rights, with the forward supplied by
Q12 or a trusted forward owner. The options owner would then:

1. update the §5 hashes through a new amendment frozen before reading outcomes, including the L6
   additions;
2. run S0–S5 once, unchanged.

Until then the reference module stays unwired (`RESEARCH_ONLY=True`). No integration into
`engine/options_skew.py`, `engine/options_ivspread.py` or `engine/greeks.py` is proposed.

## Process disclosures

* PREREG §13 lists the pre-freeze activity: schema inspection, one baseline probe on the 08-13 chain,
  synthetic smoke checks and the hermetic suite.
* **Pre-run S5 smoke (audit finding 6).** Before evaluation run 1, a smoke script outside this
  directory exercised the synthetic S5 path.
  * Script: `_fabric/Q01-scratch/smoke_s5.py`, sha256
    `37dee675f06c7b6981307928aedd76691f2d11be532674d22b7cb40914c77d72`, 1,129 bytes, kept in staging
    and not shipped.
  * It imports `evaluate.py` and the module, then calls only `stage_s5`, which uses seeded synthetic
    raw-SVI sessions with known truth.
  * It read no licensed data and wrote no `RUNS.log` entry.
* **Pre-run `evaluate.py` drafts (audit finding 5).** The witness log records two earlier `evaluate.py`
  versions, both written after the PREREG and A1 freeze and before run 1. Their bytes were not kept.
  Neither has a `RUNS.log` entry.

  | Witness time (UTC) | sha256 | Bytes |
  |---|---|---|
  | 2026-10-09 10:13:21 | `b1815cf22640d05510ac306897265dbfeddeb6f13c8593183e8b57561e3d2585` | 34,771 |
  | 2026-10-09 10:15:51 | `294312e69ac0b4e446375f053c64b8fb722371b4fde490065376a78eb78b31c7` | 35,729 |

  * The run-1 version `f092e1ec…` (35,843 bytes) was witnessed at 10:16:21.
  * The first witnessed `RUNS.log` (10:21:52, 6,484 bytes) holds only the run-1 record.
  * The smoke script above may have imported one of these drafts, but only for the synthetic S5 path.
  * None of these versions produced a data outcome.
* **Replaced diagnostic script and output (audit finding 4).** `diagnose_baseline.py` was edited
  between its two logged runs, and the first script and its output were not kept. Their hashes,
  archived from `RUNS.log` line 2, are:
  * script `f93deba35f55c01775f22c7967ca0abbce44dcaa2c003ee4714facd777be96c3`;
  * output `baseline_divergence.json` `d16dbb7d760905412da6ad7246d40bf7ea3d316c81b2dd27f150fdf54305fd21`.

  The shipped versions are script `3eb322cd…` and output `c88c9f81…` (`RUNS.log` line 3). The edit
  changed only how zero-match dates are reported (`None` instead of a tie-break "best chain") and
  added the previous-declared-chain comparison. The diagnostic never feeds the verdict.
* **Evaluation runs.** `evaluate.py` ran twice: run 1 by the author, and run 4 by the finisher after
  the audit code fixes, with byte-identical outputs. Run 4 is numbered 4 because `RUNS.log` numbers
  every entry, including the two diagnostics labelled `post_run_diagnostic` at lines 2 and 3.

## Independent audit and finisher fixes

An independent read-only audit (Opus 5.5) found 0 blockers, 0 majors and 8 minors, with the verdict
PASS_WITH_FIXES. None of the findings changes the verdict.

| # | Finding | Resolution |
|---|---|---|
| 1 | If the stage-2 LP failed, the stage-1 solution was used silently and could still be reported `ADMISSIBLE`. | **Fixed in code.** A stage-2 failure now returns state `SOLVER_FAILED`, never admitted, with `stage2_fallback=True`, `stage1_state` and `stage2_status` recorded. A new test forces the failure with a monkeypatched `linprog` (`test_req2_stage2_solver_failure_is_flagged_and_never_admitted`). |
| 2 | A mismatch between a declared input hash and the frozen §5 hashes was recorded but did not stop the run. | **Fixed in code.** `evaluate.py` now refuses at S0 with exit 4, logged, before S1 reads any input. |
| 3 | `eligible_sessions` is hard-coded rather than counted. | **Fails closed, made binding.** S3 stops with exit 3 on any complete or undeterminable source before the value is used. A2.4 requires the adapter amendment to define the real count. |
| 4 | The replaced diagnostic script and output were not kept. | **Disclosed.** A hash archive is above. The bytes cannot be recovered. |
| 5 | Two pre-run `evaluate.py` versions were not disclosed. | **Disclosed** above, with witness hashes. |
| 6 | The pre-run smoke script was not hashed. | **Disclosed** above, with sha256 and synthetic-only scope. |
| 7 | Chord bias makes the §8 non-inferiority bar easy for SVI, and `D_s` counts only benchmark-admissible sessions. | **Amendment A2**, frozen in `FREEZE_A2.log` and binding on any future S4 run. `PREREG.md` is unedited. |
| 8 | The CI suite does not itself prove that `options_skew` output is byte-identical. | **Documented** here, in `REQUIREMENTS.md` and in the PR body. The hermetic suite may import only the standard library, numpy, scipy, pandas and the module, so it cannot import `options_skew`. The proof is `evaluate.py` S1, digest `a60bf335…b18c`, before and after import, in runs 1 and 4. |

Because findings 1 and 2 changed code that feeds results, `evaluate.py` was re-run once (run 4), and
its outputs were byte-identical to run 1. The focused suite now has 18 tests and exits 0.
