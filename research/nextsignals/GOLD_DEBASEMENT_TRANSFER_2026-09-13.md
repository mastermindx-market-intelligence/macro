# nextSignals Gold Debasement Transfer — Frozen Replication

**Date:** 2026-09-13  
**Status:** PREREG FROZEN BEFORE OUTCOME READ  
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

Primary candidate inputs:

- Gold: `data/yahoo/GC_F.parquet`, daily `close`, 2000-08-30 → 2026-09-08, SHA-256 `d6d1ea4abeccaca6194bacd1e73b743a40c10e3574a3ad2945fab7b6a8f7bf87`.
- US 2Y yield: `data/fred/DGS2.parquet`, daily `us2y`, 1976-06-01 → 2026-09-04, SHA-256 `9e4c50032f664317734c78759b3e4fb400dd8358d63062ceb30b30ae69175e0b`.

Existing-Mastermind incrementality controls:

- DXY: `data/yahoo/DX-Y.NYB.parquet`, SHA-256 `c0fea173785d9e9fe5969039e1dacfff9597bdd4ac1adbec5411dc3e90db7223`.
- 10Y real yield: `data/fred/DFII10.parquet`, 2003-01-02 → 2026-09-04, SHA-256 `be55d7c4218c6c80ea933a86f2f22271b364b65b0b74274bf7e7086ba01d8f4d`.
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