# nextSignals Gold Debasement Transfer — Frozen Replication

**Date:** 2026-09-13  
**Status:** PREREG FROZEN BEFORE OUTCOME READ; final direct-portability ruling `REJECTED_BY_DESIGN`
**Authority:** research only; no signal, portfolio, Prophet, Neural Web, Risk Radar, or execution authority

## 1. Mission

Test whether the publicly disclosed nextSignals “Gold Regime Tracker” idea adds durable information to Mastermind rather than copying a branded surface or creating a second commodity system. Public disclosures describe a 40-day gold–2Y correlation state machine with +0.10 / -0.10 hysteresis, plus dollar/yen context. This replication uses Mastermind-owned/licensed inputs and original analysis.

The user job is to know whether a gold/yield decoupling regime deserves a place inside Mastermind’s existing Commodity Vector. The machine job is to falsify portability and incrementality before any product or authority change. A successful result still earns only a separately gated research follow-up; it does not self-promote.

Protected Sol Skillpack pin: `9ed16bf0fcc5b47e870350ff2413ff5c8c73b447` (`mastermind.sol_skillpack.v1`, v1.0.1).  
Macro base frozen before analysis: `be6d1122e16da5e81fb26dd4205157f8e3ee4de6`.

## 2. Public disclosure facts being tested

The corpus records a current tracker that labels a “debasement-regime detector” as a 40-day gold–2Y correlation, enters at `+0.10`, exits at `-0.10`, and treats the ordinary inverse regime as non-debasement. Separate public panels use falling DXY and yen/Gold differential context, but the exact yen confirmation formula is not fully disclosed. Those auxiliary rules are **not** part of the primary test.

Relevant private-corpus evidence IDs are `2097298079288369551`, `2098378157912928630`, and `2098760589312921828`. Raw posts/media remain outside Git; this memo stores only the testable disclosed mechanics and independent findings.
## 3. Frozen inputs and provenance

**Pre-outcome provenance correction:** the first prereg commit accidentally hashed the separate mutable main checkout instead of the branch-base worktree. No candidate forward outcome had been computed at discovery. The analysis is frozen to the exact files tracked in Macro base `be6d1122e16da5e81fb26dd4205157f8e3ee4de6`; corrected fingerprints follow. Thresholds, horizons, splits, statistics, and acceptance law are unchanged.

Primary candidate inputs:

- Gold: `data/yahoo/GC_F.parquet`, daily `close`, 2000-08-30 → 2026-09-11, SHA-256 `63d0f4727bbca61076ecb26c677910ecdfa84e7f8f862275a7958d695f2a0eb9`.
- US 2Y yield: `data/fred/DGS2.parquet`, daily `us2y`, 1976-06-01 → 2026-09-10, SHA-256 `c25dab2b52f7ce8d06684b5a982c4e986ce873d8a9764f4cdcbf3ca6ad56a52f`.

Existing-Mastermind incrementality controls:

- DXY: `data/yahoo/DX-Y.NYB.parquet`, through 2026-09-11, SHA-256 `2db98e28390ac240cfecc20ce0335dc8ce2a799303570d66c242da0a5d8960fc`.
- 10Y real yield: `data/fred/DFII10.parquet`, 2003-01-02 → 2026-09-10, SHA-256 `b4ef75c5a0c6a7f67b762ccd2ef19d34b628a3932be2665b03a03ad5883712fc`.
- Current Commodity Vector implementation: `engine/commodity_signals.py`; gold residual drivers are real yield + DXY, with causal expanding-fit residuals and a separate driver axis.

No future/revised value is back-filled into an earlier decision date. A candidate correlation updates only on dates on which both a gold close and a DGS2 observation exist. Its decision timestamp is after those dated observations; every forward outcome starts on the **next** gold session. FRED vintage timestamps are not stored, so the study cannot claim exact intraday/as-published replay and will state that limitation explicitly.

## 4. Frozen candidate construction

For each common observation date `t`:

- `g_t = log(GC_t / GC_{t-1})` on consecutive gold sessions;
- `dy2_t = DGS2_t - DGS2_{t-1}` on consecutive published DGS2 observations;
- `c40_t = Corr(g, dy2)` over the latest 40 valid co-dated observations.

The return/change formulation is the primary portability approximation because it matches the disclosed recent tracker values materially better than correlating raw gold/yield levels. Exact source-contract differences mean numerical equality to the publisher is **not** expected.
State machine (frozen from the public disclosure):

1. Before 40 valid pairs: `UNAVAILABLE`.
2. Starting state after warm-up: `NORMAL_INVERSE` unless the first valid `c40 >= +0.10`.
3. Enter `DEBASEMENT` when `c40 >= +0.10`.
4. Exit to `NORMAL_INVERSE` when `c40 <= -0.10`.
5. Hold the prior state inside `(-0.10, +0.10)`.

No threshold, window, horizon, or state rule may be changed after forward outcomes are read. Raw-level correlation is a specification-sensitivity diagnostic only and cannot rescue the primary test.

## 5. Frozen outcomes, splits, and statistics

Primary horizons are 21 and 63 gold sessions. For each eligible decision date we measure next-session-to-horizon total return and path max drawdown. We evaluate both (a) all `DEBASEMENT` state dates versus valid `NORMAL_INVERSE` dates and (b) discrete entry dates versus eligible non-entry dates.

Temporal robustness is frozen as four eras: `2003–2009`, `2010–2016`, `2017–2022`, and `2023–latest`. The common 2003 start is chosen before outcomes because Mastermind’s 10Y-real-yield control begins in 2003.

Inference: 20-session moving-block bootstrap, 5,000 resamples, deterministic RNG seed `20260913`; family-wise multiple testing uses Benjamini–Hochberg FDR `q=0.10`. The primary family is the 8 state/entry × return/drawdown × 21/63 contrasts plus the two incremental 21/63 regression coefficients below.

Incrementality test: reproduce the current Commodity Vector gold features from the frozen Macro base and estimate `forward_return_h ~ 1 + debasement_active + shock_z + driver_score + ts_momentum` for `h ∈ {21,63}`. The `debasement_active` coefficient is the only candidate coefficient judged for incrementality; standard errors use Newey–West/HAC with lag equal to the horizon.
## 6. Frozen acceptance law

A direct transfer passes only if all are true:

- the `DEBASEMENT` effect is directionally favorable for forward gold return at 21 **and** 63 sessions in the full sample;
- at least one primary return contrast survives BH-FDR `q <= 0.10` without a contradictory primary drawdown result;
- the return-effect sign is the same in at least 3 of 4 eras **and** in the `2023–latest` era;
- the incremental `debasement_active` coefficient remains positive at both horizons after current Mastermind gold controls, with at least one horizon surviving BH-FDR `q <= 0.10`;
- results do not depend on changing the +0.10/-0.10 bands, the 40-observation window, or selecting a different correlation definition after seeing outcomes.

Failure means `REJECTED_BY_DESIGN` for the **direct portability claim**: do not add a second gold regime engine and do not threshold-sweep to manufacture a winner. A failed direct transfer does not invalidate Mastermind’s existing commodity residual/driver-decoupling work.

A pass still does **not** authorize trading or production scoring. It would justify one later bounded wave that extends the existing Commodity Vector, display/research tier first, with point-in-time and production proof.

## 7. Held / non-goals

The yen differential, DXY 5-day confirmation, SOFR overlays, war/event labels, and any options positioning are held out. They may be tested only under a new frozen hypothesis after this core gold–2Y question is adjudicated. BTC ETF-flow mechanics are also a separate family; existing Mastermind BTC Farside + Coinbase-Premium work is not modified here, and current `WS-CRYPTO-INTELLIGENCE` authority blocks unscheduled ETH promotion.
## 8. Results — frozen test executed

The frozen formulation produced 6,443 eligible paired dates from 2000-10-27 through 2026-09-10, including 1,070 `DEBASEMENT` dates and 25 discrete entries. On the latest paired date, `c40 = -0.386` and the state is `NORMAL_INVERSE`. That is close to the publisher’s contemporaneous disclosed reading near -0.36 despite different source contracts; the raw-level 40-observation correlation is only `+0.007`. This supports the preregistered return-vs-yield-change interpretation rather than rescuing the test with a post-hoc formula change.

Primary full-sample contrasts (effect = candidate minus control; positive return is favorable, positive drawdown effect means **less** severe drawdown):

| Contrast | Horizon | n candidate | Effect | 95% block-bootstrap CI | raw p | BH q |
|---|---:|---:|---:|---:|---:|---:|
| active state → return | 21d | 1,070 | +1.24 pp | [+0.08, +2.38] pp | 0.0376 | 0.188 |
| active state → max drawdown | 21d | 1,070 | **-0.65 pp** | [-1.43, +0.10] pp | 0.0892 | 0.288 |
| active state → return | 63d | 1,070 | +1.55 pp | [-0.55, +3.69] pp | 0.1520 | 0.304 |
| active state → max drawdown | 63d | 1,070 | **-0.88 pp** | [-2.01, +0.21] pp | 0.1152 | 0.288 |
| entry → return | 21d | 25 | +0.78 pp | [-1.37, +2.80] pp | 0.4784 | 0.598 |
| entry → max drawdown | 21d | 25 | -0.21 pp | [-1.55, +0.98] pp | 0.7864 | 0.874 |
| entry → return | 63d | 25 | +1.29 pp | [-1.62, +4.24] pp | 0.3768 | 0.538 |
| entry → max drawdown | 63d | 25 | -0.02 pp | [-1.56, +1.46] pp | 0.9876 | 0.988 |
### Incrementality versus current Commodity Vector controls

The active-state coefficient remains positive after conditioning on current gold `shock_z`, `driver_score`, and `ts_momentum`, but only at the short horizon does it survive the frozen FDR family:

| Horizon | n | active coefficient | HAC s.e. | raw p | BH q |
|---|---:|---:|---:|---:|---:|
| 21d | 5,310 | +1.80 pp | 0.70 pp | 0.0099 | **0.099** |
| 63d | 5,272 | +2.15 pp | 1.68 pp | 0.1995 | 0.332 |

This is a real short-horizon research finding, not a pass. The preregistered direct-transfer law requires both temporal robustness and a surviving unconditioned primary return contrast; neither condition is satisfied.

### Temporal robustness

| Era | 21d active-state effect | 63d active-state effect |
|---|---:|---:|
| 2003–2009 | +1.24 pp | +0.46 pp |
| 2010–2016 | +1.20 pp | +4.35 pp |
| 2017–2022 | +0.92 pp | +2.86 pp |
| 2023–latest | +1.70 pp | **-4.96 pp** |

The 21-day sign is stable in all four eras. The 63-day sign flips sharply negative in the current era, violating the predeclared “latest era must agree” condition. The state also carried mildly worse full-sample drawdown paths at both horizons, although those drawdown contrasts did not survive FDR.
### Relationship to existing Mastermind gold intelligence

Only 29.6% of candidate-active dates are simultaneously marked `decoupled` by Mastermind’s current gold driver-decoupling logic; 17.7% of existing decoupled dates are candidate-active. The public rule is therefore not merely a relabel of the existing decoupling flag. Even so, distinctness is not enough: the frozen rule fails the required robustness and unconditioned-evidence gates.

## 9. Adjudication

**Direct portability: `REJECTED_BY_DESIGN`.** Do not add the +0.10/-0.10 40-observation gold–2Y state machine as a second gold regime engine, and do not retune its bands/window or add the held DXY/yen conditions to rescue this result.

Why:

- no unconditioned primary return contrast survives the frozen BH-FDR family;
- discrete entries are only 25 and are not independently predictive at either horizon;
- the current 2023+ era reverses the 63-day return effect to -4.96 pp;
- full-sample drawdown effects lean the wrong way at both horizons;
- the only surviving incremental evidence is the 21-day controlled coefficient, while 63-day incrementality fails.

The existing Commodity Vector gold residual/driver-axis architecture remains the canonical system. The 21-day controlled effect is retained as a research discovery, not product authority; any future use would require a **new original frozen hypothesis** rather than threshold-mining this public rule family.

Private reproducibility artifacts: `/Users/chriswong/nextsignals_corpus_staging/analysis/gold_debasement_replication/results.json`, `decision_panel.csv`, and `/Users/chriswong/nextsignals_corpus_staging/analysis/gold_debasement_transfer.py`. Raw corpus/media remain private and are not committed.
## 10. Acceptance and exact next action

This research slice is complete when this record is merged with green repository validation. It establishes no new gold feature and changes no production signal or authority. The existing Commodity Vector gold residual/driver-axis system remains canonical.

Do **not** spend the next wave retuning this 40-observation tracker. The public yen/dollar confirmation mechanics are not specified precisely enough for a direct formula replication, so that branch stays held unless a source-complete rule is recovered or Mastermind deliberately preregisters a new original hypothesis before outcomes.

Exact next action in the corpus program: perform current-owner/collision archaeology for the **BTC ETF-flow intelligence** family, compare the public concept set against Mastermind's existing Farside/Coinbase-Premium/crypto owners, and freeze one non-duplicative point-in-time incrementality hypothesis before reading forward outcomes. If the concept is already subsumed by an existing owner, record that as a no-build result rather than creating another crypto signal plane. Keep PR #7104's acquisition carrier separate and do not alter `WS-CRYPTO-INTELLIGENCE` product/trade authority from a research transfer test.
