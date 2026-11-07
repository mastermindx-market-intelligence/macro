# Q10 — Condition-adjusted abnormal off-exchange participation: VERDICT

**VERDICT: KEEP** — as a research-tier, descriptive **explanatory calibration correction**
for the incumbent own-history participation anomaly. This is **not** an alpha signal, carries
no direction, and nothing imports or wires the module
(`engine/offexchange_conditional_residual.py`, `RESEARCH_ONLY = True`).

Served model: Claude Opus 5.5 (`claude-opus-5-5`).

## What was tested (frozen PREREG, sha256 `249e8748f7b758dcfbeb877c9469178c354f60029e5ab66222a43892b1a68339`)

Daily participation `p = FINRA total off-exchange volume / vendor consolidated volume` for the
374-issuer deep cohort is scored against a predictive distribution conditioned only on
information available at that session's cutoff: the issuer's trailing level (empirical
logit), a leave-one-out cross-sectional market factor, and same-session relative volume.
The model is fitted on training sessions (through 2025-06-30). It was evaluated ONCE on the
chronological holdout 2025-07-01..2026-10-08 against:

* **B0**: the incumbent robust median/MAD construction with normal quantiles;
* **B1**: B0 with training-fitted empirical quantiles of its z.

Primary metric: the 90% interval score, `R = 1 − ΣA/ΣB` over per-session means on common
support. Uncertainty comes from a moving-block bootstrap over sessions (block 20; sensitivity
10/40; 2000 reps; seed 20261008).

Bar: `R ≥ 0.05`, CI lower bound `> 0`, and `|cov90 − 0.90| ≤ 0.03`. KEEP requires both H1 and H2 to pass.

## Result (single run, `evaluate.py evaluate --stamp 2026-10-09T09:41:35Z`, exit 0)

| Comparison | R (90% interval score) | 95% CI block 20 | block 10 | block 40 | pass |
|---|---|---|---|---|---|
| H1 model vs B0 | **0.139** | 0.078 .. 0.182 | 0.080 .. 0.196 | 0.087 .. 0.172 | yes |
| H2 model vs B1 | **0.139** | 0.082 .. 0.182 | 0.083 .. 0.193 | 0.088 .. 0.174 | yes |

| Held-out coverage (common support) | 50% | 90% | 98% |
|---|---|---|---|
| model | 0.505 | **0.906** (block CI 0.900..0.912) | 0.982 |
| B0 (incumbent normal) | 0.476 | 0.860 | 0.946 |
| B1 (incumbent empirical) | 0.503 | 0.903 | 0.980 |

**Honest N:**
* 321 test sessions;
* 17 non-overlapping 20-session blocks;
* 372 issuers on common support;
* median 355 issuers per session;
* 105,551 common rows (rows are not independent; the sessions and blocks carry the inference).

**Ablation (pre-registered):** removing the market factor gives `R = 0.135` in the model's
favour, and the no-market variant's own cov90 is 0.906. Nearly all of the gain is therefore
the leave-one-out market factor. The volume terms are small:
* market loading 1.02;
* relative-volume slope 0.067;
* positive-volume hinge 0.020.

## Interpretation, including the falsifier

* **Market-wide adjustment.** Conditioning moves the predictive distribution with
  market-wide shifts, and the resulting intervals are sharper and still calibrated. The B0
  normal intervals under-cover (0.860 at 90%). B1 fixes coverage but not sharpness. The
  model fixes both.
* **About half the incumbent flags are explained.** About half (52.1%) of the incumbent
  "heavy" rows (z ≥ 1.5) are *not* upper-tail rows under the conditional model (PIT < 0.95).
  Conditioning attributes them to market-wide or volume-driven movement. This is the
  "explanatory correction" in the brief's falsifier.
* **Flag counts on shift sessions.** The model's upper-tail rows sit disproportionately on
  the 13 test "shift sessions":
  * these sessions hold 3.9% of rows but 10.9% of model upper-tail rows;
  * for B0 the figure is 2.2%;
  * equivalently, the model's PIT ≥ 0.95 rate on those sessions is about 12.4% (514 of
    4,143 rows) against a nominal 5%, versus about 4.1% off them. On the same sessions B0
    (z ≥ 1.645) flags about 3.5% and incumbent "heavy" (z ≥ 1.5) about 4.2%.

  The model is therefore **conditionally over-dispersed on shift sessions**: its aggregate
  coverage holds, but its upper tail is not calibrated session by session. This is
  consistent with one pooled market loading (1.02) applied to issuers whose sensitivity to
  the common shift is heterogeneous; that explanation was not tested. Removing a common
  shift re-ranks issuers *relative to the market* on those sessions, so a flag there means
  "high relative to the same-session cross-section", not "abnormal in its own history".
  The sign mix of these shifts was not examined, and no causal reading is offered. Figures
  are derived from the flag counts already in `results.json`; no new analysis was run.
* **No information content was tested.** No forward-return, alpha or information-content
  test was run, and none was licensed (`DNR:KILL-OUTCOME-AUDITION`). KEEP therefore means
  *the conditional residual is a better-calibrated description of participation than the
  incumbent's*. It does not mean the residual predicts anything. The falsifier's clause
  ("retain as explanatory correction, not a new alpha signal") binds in either case.

## Measurement facts

* Invalid ratios (FINRA total > vendor volume): 1,320 rows overall, 277 in the test window.
  They are excluded as bad measurement and never clipped.
* Zero denominator: 1 row.
* Valid `p = 0` or `p = 1` rows in this vintage: 0. The contract supports them and the
  synthetic tests cover them.
* Split-excluded rows: 13,943 overall, 2,421 in test. These come from the incumbent break
  rule on the full-vintage series and apply to both arms.
* Thin (POOLED) tier in test: 603 rows over 21 issuers, cov90 0.892. The incumbent abstains
  on every one of these rows (needs 40 observations), so pooling adds disclosed support where
  B0 has none. These rows are outside the common-support comparison.
* Abstentions in test: 200 rows with no support.

## Limitations

1. **Q03 dependency.** Split handling is the incumbent level-break rule. It is not
   corporate-action records. The break location is computed on the full-vintage series. That
   is a mild look-ahead in *exclusion*, though not in scoring, and it is applied identically
   to every arm.
2. **Survivorship.** The cohort is fixed at backfill time.
3. **Invalid-ratio rows are dropped in both arms.** The incumbent `darkpool_signals` keeps
   ratios above one. Both arms here drop them, so B0 is the incumbent arithmetic on the
   valid-measurement subset (reproduction: 1122/1122 exact on its own inputs).
4. **What the inputs are.**
   * The FINRA total is a reporting-category count (ATS/non-ATS is a venue category, not
     owner intent).
   * The vendor denominator is vendor-adjusted.
   * Neither identifies owners, intent, inventory or buy/sell direction.
   * FINRA short volume is not short interest and is not used.
5. **Bootstrap scope.** Session-level block bootstrap; block-40 sensitivity is reported.
   Only 17 non-overlapping 20-session blocks, so the CI widths are themselves uncertain.
6. **Single vintage and single split.** There is no repeated holdout search; the bar was
   fixed before the run.

## Reproduce

```
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2 nice -n 10 \
  /opt/homebrew/bin/python3.12 research/quant_assessment_2026_10/Q10_conditional_offexchange_anomalies/evaluate.py evaluate --stamp <utc>
```

The script refuses (exit 2) when the PREREG.md hash differs from FREEZE.log, and refuses
(exit 3) when an input hash differs from the recorded vintage.

| Item | sha256 |
|---|---|
| results.json | `e430c57028b3cd8930e8bf390576ede0a62b14157b22bddc54a1e61772cfaa8c` |
| Module, evaluated | `5513dd006c66a312e39f2d1b3dfe980d4e9a223dccf1f754b87c76c1da391b8d` |
| Module, shipped | `bf988d0c77f3b570e799a3b111a54488b2d59e6b506854a4ecd4af47c0168ef3` |

The shipped module differs from the evaluated one in its docstring VERDICT paragraph. The
evaluated `5513dd00` bytes were not retained, so instead of a hash reconstruction the
shipped module was re-run end to end (independent-audit fix):

* `evaluate.py evaluate --stamp 2026-10-09T09:57:09Z` with module `bf988d0c` exited 0 and
  wrote a `results.json` byte-identical to the recorded one (`e430c570…`). This run is the
  third line of `RUNS.log`.
* Recomputing the baseline reproduction against the shipped module gives bytes identical
  to `baseline_repro.json` (`7e32c690…`; a check that writes nothing and is not logged).

`evaluate.py` enforces the PREREG and input-data hashes but **does not enforce the module
hash**. Module provenance rests on the `RUNS.log` record plus this reproduction run.
