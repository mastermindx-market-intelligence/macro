# Q10 — Condition-adjusted abnormal off-exchange participation: PREREGISTRATION

Status: written and frozen BEFORE any evaluation outcome (interval, coverage, score,
flag rate or comparison) was computed. The only data facts read before this file was
frozen are support counts from `support_census.py` (cohort size, date range, invalid-ratio
and split-break counts) and input file hashes. The freeze hash and UTC time are in
`FREEZE.log`. After freezing, this file is never edited; changes go to
`PREREG_AMENDMENT.md`.

Research tier only. Nothing evaluated here is wired, registered, scheduled, promoted,
gated or fused. No buy/sell direction, no beneficial-owner inference and no dealer-
inventory claim is made anywhere: FINRA short volume is not short interest or net buying,
and ATS/non-ATS is a venue/reporting category, not owner intent.

## 1. Question and estimand

Is a daily off-exchange participation reading that looks unusual against the issuer's own
trailing norm (the incumbent `engine/darkpool_signals.py` construction) still unusual
once you condition on (a) the market-wide participation shift that session and (b) the
issuer's same-session consolidated volume?

**Estimand.** For issuer i on session t, the conditional predictive distribution of
off-exchange participation

    p_it = X_it / V_it,  X = FINRA facility total off-exchange volume (`total_vol`),
                          V = consolidated volume (vendor `volume`),

given the information set
`F_it = { own valid history strictly before t } ∪ { V_it } ∪ { p_jt : j ≠ i }`.
The incumbent conditions on own history only. The quantity scored is how well a 90%
central predictive interval for p_it, built from F_it, scores against the realised p_it
(interval score, §6).

**Unit.** One issuer-session (issuer i, session t). The INDEPENDENT unit for uncertainty is
the session (the whole cross-section of a date moves together), resampled in contiguous
blocks of sessions (§8).

**Input clock.** FINRA daily short-sale volume file for session t (published after the
close of t) and the vendor's consolidated daily volume for session t, joined on the exact
date (inner join, never forward-filled). Other issuers' same-session participation is in
the same file. **Output clock.** After publication of the session-t FINRA file: a
same-session descriptive residual for t. It is NOT a forecast of any later return or
participation and makes no directional claim.

## 2. Non-duplication (incumbent refresh and collision check)

Grep of the pristine snapshot `_base` (engine/, scripts/, tests/, research/) for the
concept (`offex`, `off_exchange`, `conditional`, `fractional`, `market factor`,
`participation`) and for the module name `offexchange_conditional_residual`: no module of
that name or concept exists. Incumbents and the narrow relation this work stays inside:

| Incumbent | What it owns | Relation here |
|---|---|---|
| `engine/darkpool_signals.py` (`trailing_z`, `share_break_index`, `usable_history`, `HEAVY_Z`=1.5) | The served per-name participation z (median/MAD over 252 prior sessions, min 40) and the split-break truncation | **Baseline competitor** only. Its arithmetic is reproduced and compared against; it is not changed, replaced or re-parameterised. |
| `engine/darkpool_context.py` (v2 conjunction tags, `STANDOUT_Z`, `STANDOUT_PART`) | Display-tier context tags | Untouched; no new tag, no new page section. |
| PSS-AF1 (DNR:HOLD-PSS-AF1-FINRA) | Frozen FINRA activity baseline | Untouched. Venue analysis never enters frozen PSS-AF1; `panel_deep` is read only. |
| #8659 intraday pressure/response model | Intraday pressure | Out of scope: this is daily, venue-share only, no pressure/response or price model. |
| #8660 TP1 | Separate program | Out of scope. |
| Dark Pool page / desk (`scripts/build_darkpool_desk.py`) | UI | No UI of any kind; no new page; no alternate actor-intent score. |
| Q03 (split-affected histories) | Corporate-action correction rules | Dependency. The incumbent break rule is used (§4); Q03's eventual rules are a disclosed limitation. |

Standing kills/holds respected: DNR:KILL-OUTCOME-AUDITION (one preregistered comparison,
no outcome-driven re-specification), DNR:KILL-LLM-ORIGINATION (no language model
originates anything), DNR:KILL-FUSED-COMPOSITE and DNR:KILL-POSITIONING-FUSION (no fused
score; the output is one descriptive residual with its support), DNR:KILL-REGIME-SCORECARD
and DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR (no regime scorecard or monitor),
DNR:KILL-CAUSAL-DAG-ALPHA (no causal claim, no alpha claim), DNR:HOLD-PSS-AF1-FINRA and
DNR:HOLD-PSS-CD1-CROWDING (not touched).

## 3. Sources and vintages (read-only licensed data, vintage cdab6268)

| Input | sha256 |
|---|---|
| `macro-main/data/finra_short_volume/panel_deep.parquet` | `12cc30a28547c30d7effd0991c6dab773b419f36b2fc4cc2133069fc444d5d9f` |
| `macro-main/data/finra_short_volume/panel.parquet` | `63c69080d88baf4bbc039d1906995e37fa7c5078f6370cac46d1a03a7df4f6f4` |
| `macro-main/data/yahoo/<TICKER>.parquet` for the 374 cohort tickers — aggregate = sha256 of the newline-joined sorted lines `"<TICKER> <file sha256>"` | `4bed622113b18ee0050db4dc436a29aec75c928b6638568a9062149ec0d6c648` |
| `_base/engine/darkpool_signals.py` (incumbent, git blob `29f24ae394fd37cac587e70e908d8dd75b6c9100` per brief R02) | recorded by evaluate.py at run time |
| Mastermind `docs/sol_skills/INDEX.md` (commit unknown) | `608aebc84a106f4e3c687f020a7f0e69af88f38e014d4664a376e2be2ddfa220` |
| Mastermind `docs/sol_skills/ACTIVE_EXECUTION.md` (commit unknown) | `fb6a89101ad75512b971b2457f3f419704eae136afa28bac5a646ae69a6ed0dc` |
| Mastermind `docs/sol_skills/SESSION_RELIABILITY.md` (commit unknown) | `817366c630abe31308a09c18caa5249ea4c39c83d74c130496079bb151283076` |

`evaluate.py` recomputes the three data hashes and REFUSES to run on any mismatch.

## 4. Cohort, construction and attrition

* **Issuers:** the 374 tickers of `panel_deep.parquet` (chosen at backfill time;
  survivorship of that list is disclosed and not corrected). Rows of `panel.parquet` for
  those tickers are unioned in with collector rows winning on duplicate (date, ticker),
  exactly as `scripts/build_darkpool_desk.py::_load_panel` does.
* **Issuer-session in cohort** iff both a FINRA row and a vendor volume row exist on that
  exact date. Support census (pre-freeze, counts only): 282,826 joined rows,
  2023-08-01..2026-10-08, 801 sessions.
* **Measurement validity (requirement 1).** `X > V` (ratio above one; 1,320 rows), `X < 0`
  and `V <= 0` (1 row) are INVALID and excluded from every statistic and from scoring on
  both arms; they are counted, never clipped. `p = 0` and `p = 1` are valid (empirical
  logit is finite at both ends). Note: the incumbent keeps ratio-above-one rows in its
  history; both arms here drop them identically, a disclosed deviation that favours
  neither arm.
* **Split / denominator changes (requirement 3).** The incumbent level-break rule
  (`share_break_index`: 20-session rolling median, ratio ≥ 1.8 or ≤ 1/1.8, last break)
  applied to each issuer's full valid participation series at this vintage; rows before
  the last break are EXCLUDED_SPLIT for both arms (census: 29 issuers have a break). This
  uses the full-vintage series (a measurement-unit filter, not an outcome), and is
  disclosed as such. Q03 owns real corporate-action rules; the module also accepts an
  explicit caller-supplied event mask for that future seam.
* **Attrition reported:** rows invalid, rows split-excluded, rows abstained for support,
  rows abstained for market factor, rows scored full, rows scored pooled, and the
  common-support rows of the primary comparison.

## 5. Methods (all fitted on TRAINING sessions only; no hyperparameter search)

Constants are fixed in advance (module `engine/offexchange_conditional_residual.py`):

* `z_it = log((X + 0.5) / (V − X + 0.5))` (empirical logit, valid rows only).
* Issuer level `L_it` = median of z over the issuer's prior 252 valid sessions (current
  excluded); `n_level` = that count. `n_level < 10` → ABSTAIN_NO_SUPPORT; `10 ≤ n_level <
  40` → POOLED (thin) tier; `n_level ≥ 40` → FULL tier.
* Deviation `d_it = z_it − L_it`.
* Market factor `m_it` = exact leave-one-out median of `d_jt` over FULL-tier issuers j ≠ i
  on session t; fewer than 30 contributors → ABSTAIN_NO_MARKET.
* Relative volume `v_it = log V_it − median(log V)` over the prior 60 valid sessions
  (min 10).
* Huber regression (c = 1.345, IRLS, MAD scale) on training FULL-tier rows:
  `d = a + γ·m + β1·v + β2·max(v, 0) + e`.
* Residual scale: issuer trailing 1.4826·MAD of prior residuals (window 252), shrunk
  toward the session's pooled median scale (median over issuers with ≥ 40 prior
  residuals; ≥ 30 such issuers, else the training pooled scale):
  `s² = (n·s_own² + 40·s_pool²)/(n + 40)`, then inflated by `sqrt(1 + π/(2·n_level))`.
  Pooling weight `40/(n+40)` is disclosed per row (requirement 4).
* Standardised residual `u = e/s`; interval endpoints use the TRAINING empirical
  quantiles of u (FULL tier), mapped back to the p scale exactly through the inverse
  empirical logit; bounds (never observations) are clipped to [0, 1].

**Competitors (both on identical rows):**

* **B0 incumbent:** `trailing_z` arithmetic on the valid, split-truncated p series
  (median/MAD × 1.4826 over prior 252, min 40; mean/σ fallback when MAD = 0). Interval =
  centre ± Φ⁻¹(1 − α/2)·scale, bounds clipped to [0, 1].
* **B1 recalibrated incumbent (H2 ablation):** the same centre and scale with TRAINING
  empirical quantiles of the incumbent z in place of normal quantiles. Separates the
  gain from recalibration alone from the gain from conditioning.
* **Secondary (descriptive, not gating):** the model without the market factor
  (`use_market=False`).

## 6. Hypotheses, primary metric and practical bar

**Primary metric:** 90% interval score (Gneiting–Raftery, α = 0.10) on the p scale,
lower is better, on the PRIMARY COMMON SUPPORT: test issuer-sessions that are valid,
not split-excluded, model FULL tier, and B0/B1 defined. Per session t, `A_t` = mean
model score over that session's common-support rows and `B_t` = mean competitor score.
Relative reduction `R = 1 − Σ_t A_t / Σ_t B_t`.

* **H1 (vs B0):** R ≥ 0.05 AND the 95% block-bootstrap CI of R excludes 0 (lower bound
  > 0) AND model 90% coverage on common support within ±0.03 of 0.90.
* **H2 (vs B1):** the same three conditions with B1 as competitor.

**Practical effect bar:** 5% relative interval-score reduction, as above.

**Trial family:** exactly one primary comparison, the conjunction H1 ∧ H2 (an
intersection–union test: both must pass, so no multiplicity correction is needed and
none can help). Everything else is descriptive.

**Secondary diagnostics (descriptive only, never gates):** coverage at 50/90/98% for
model, B0, B1; thin-tier (POOLED) coverage at 50/90/98% and its row/issuer counts (B0/B1
abstain there); upper one-sided flag rate (model PIT ≥ 0.95 vs B0 z ≥ Φ⁻¹(0.95) and
incumbent `HEAVY_Z` z ≥ 1.5); share of each method's flags falling on market-shift
sessions (|session median d| ≥ the TRAINING 95th percentile of that quantity); share of
incumbent `HEAVY_Z` flags the model scores below PIT 0.95; fitted coefficients; the
no-market-factor ablation's interval score; block-length sensitivity (10 and 40).

## 7. Chronological split and outcome windows

* Training sessions: 2023-08-01 .. 2025-06-30 (includes warm-up; trailing statistics need
  history, so early sessions are abstentions by construction).
* Test (held-out) sessions: 2025-07-01 .. 2026-10-08. Scoring of test rows uses trailing
  realised data only (online), with coefficients, quantiles and the market-shift
  threshold frozen from training.
* Outcome window: the same session (same-session residual); no forward window.
* One holdout, read once. No repeated holdout search.

## 8. Dependence-aware uncertainty

Moving-block bootstrap over test SESSIONS (whole cross-section resampled together),
block length 20 sessions primary (10 and 40 sensitivity), 2000 replicates, seed
20261008, percentile 95% CI. **Honest N** = number of test sessions on common support
and the number of non-overlapping 20-session blocks they span; issuer-session row counts
are reported but are not the N.

## 9. Verdict rule, falsifier, stop rule

* **KEEP** iff H1 and H2 both pass.
* **REJECT** otherwise (negative result reported as is).
* **INSUFFICIENT_DATA** iff common support has fewer than 100 test sessions or fewer
  than 50 issuers on the median test session.
* **Falsifier (from the brief):** if conditioning removes the apparent anomaly without
  adding reliable incremental information (H1 or H2 fails), the condition adjustment is
  retained only as an explanatory correction (it explains which incumbent flags are
  market-wide or volume-driven), not as a new alpha signal. Even under KEEP the output is
  research-tier, descriptive, with no direction.
* **Stop rule:** `evaluate.py` runs the holdout once. A crash before any holdout outcome
  is computed may be fixed and re-run, with the fix recorded in `PREREG_AMENDMENT.md`. A
  bug found after outcomes are read is fixed in an amendment that reports BOTH runs; the
  specification above (constants, split, metric, bar) is never changed after the freeze.

## 10. Limitations known at freeze

* Q03 dependency: split handling is the incumbent break rule on the full-vintage series,
  not corporate-action records.
* Cohort survivorship: issuers fixed at backfill time.
* The FINRA facility total is a reporting-category count; the vendor denominator is
  vendor-adjusted. Neither identifies owners, intent or inventory.
* Session-level block bootstrap ignores dependence across blocks beyond 20 sessions
  (sensitivity 40 reported).
