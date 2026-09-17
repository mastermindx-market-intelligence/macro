# SPY 0DTE Credit-Spread Prereg Amendment 3 — causal A1 stock-bar + VWAP semantics

**Date:** 2026-09-16
**Status:** FROZEN PRE-OUTCOME AMENDMENT — **NO TRADE / SCORE / SIZING AUTHORITY**
**Parent prereg:** `research/SPY_0DTE_CREDIT_SPREAD_FORENSIC_PREREG_2026-09-16.md`
**Amendments 1–2:** sample split / forensic quarantine; source-present zero-bid long exits.
**Research branch before this amendment:** `03413cd0d5a5c5200a3f624a33b2018301440eba`

## 1. Why this amendment exists

The parent prereg already requires A1 to contain causal opening-path price state, 5m/15m opening ranges, VWAP state, short-horizon realized volatility/range expansion, reversal-versus-continuation state, ATM IV, expected-move containment and scheduled-event state. The first A1 implementation incorrectly used the option-IV response's repeated `underlying_price` as the price path and therefore could not implement OHLC range or VWAP features. No development/validation strategy outcomes have been opened.

This amendment freezes the missing source and exact feature semantics before A0/A1 economic evaluation. It does not add a new strategy family.

## 2. Frozen underlying source + causal clock law

Use ThetaData v3 `/stock/history/ohlc` for SPY with `interval=1m` and `venue=utp_cta` (merged UTP/CTA SIP). A bar timestamp denotes the **opening** of that interval, so an exact decision timestamp may consume only bars whose interval has completed strictly before the decision:

- 09:35 decision: 09:30–09:34 bars;
- 09:45 decision: 09:30–09:44 bars;
- 10:00 decision: 09:30–09:59 bars.

The 09:35, 09:45 and 10:00 bars themselves are future relative to those exact decision instants and are forbidden. Rows opening at or after the decision are discarded **before** value/schema validation, so future corruption cannot poison an earlier feature row.

Inside the causal window, absent rows or non-finite/non-positive OHLC/VWAP values make that minute unavailable/null. Structural source contradictions instead fail the source audit: schema drift, cross-session or non-minute timestamps, malformed/negative volume or count, inconsistent OHLC, conflicting duplicate rows, or cumulative VWAP outside the cumulative traded range. Nothing is interpolated or repaired from later bars.

## 3. VWAP source semantics

ThetaData's current v3 reference (`https://docs.thetadata.us/operations/stock_history_ohlc.html`) states that bar timestamps are bar opening times, `utp_cta` is merged UTP + CTA, and stock-history OHLC `vwap` is the volume-weighted average price of the trading session. The current public sample bundle (`https://docs.thetadata.us/sample_data.zip`) was inspected before economic unblinding:

- sample ZIP SHA-256: `ca4bfc48ac90fb1a7a109e32baf779ed279ae558bdf017e40b08f1e5fc571849`;
- stock `ohlc.csv` sample date: 2025-08-19;
- 391 populated rows parsed;
- 373/391 row VWAPs fall outside that **current minute's** low/high;
- 0/391 row VWAPs fall outside the cumulative session low/high through that row.

Example: 09:32 trades 642.09–642.63 while reported VWAP is 642.80. At 15:59 the bar trades 639.38–639.91 while reported VWAP remains 640.71. Therefore the row VWAP is treated as **session-to-date cumulative VWAP**, not a per-bar VWAP.

Frozen implementation:

- `session_vwap_to_decision` = VWAP from the **last completed bar** before the decision;
- `vwap_distance_frac` = decision price / session VWAP − 1;
- `vwap_slope_5m_frac_per_min` = normalized linear slope of the last up-to-five completed cumulative-VWAP observations;
- cumulative VWAP is never re-volume-weighted a second time.

## 4. Frozen A1 opening-state feature semantics

From completed bars only:

- `opening_price`: 09:30 consolidated bar open;
- 5m/15m/30m return: opening price to close of the final completed bar in that horizon;
- elapsed opening range: high, low, fractional width and decision-price location;
- fixed 5m and 15m opening ranges: high, low, fractional width and decision-price location when that horizon has completed, otherwise null;
- realized volatility: root-sum-square of causal one-minute log returns from opening price through completed-bar closes;
- range expansion: elapsed range width / first-5m range width;
- gap reversal/continuation: let `L = (decision_price - elapsed_low) / (elapsed_high - elapsed_low)`. For an up-gap, reversal score is `1-L`; for a down-gap it is `L`. `score > 0.5` sets the reversal flag, `score < 0.5` sets the continuation flag, and exactly `0.5` sets neither. Flat/no-gap or unavailable range state remains null. This is descriptive opening-state context, not a hard-coded directional trade rule.

Optional pre-session gap normalizers are frozen as signed ratios when their source is independently available: `gap_return / prior_realized_vol` and `gap_return / prior_implied_move`. If either positive fractional scale is unavailable, its feature remains null.

## 5. Frozen expected-move envelope

At the decision timestamp, with point-in-time same-day ATM annualized IV `sigma`, last completed-bar price `S`, and regular-session minutes remaining `m = 390 - elapsed_minutes`:

`expected_move_1sigma_frac = sigma * sqrt(m / (365 * 24 * 60))`

`expected_move_1sigma_abs = S * expected_move_1sigma_frac`

`lower/upper = S ± expected_move_1sigma_abs` (lower floored at zero).

This is a transparent containment-scale feature, not a forecast calibration claim. Any alternative volatility-time convention would be a separate preregistered robustness family rather than silent retuning.

## 6. What remains blocked

This amendment grants no economic, gamma, signal, sizing, order or production authority. Panel-level consolidated bar coverage must still be published, repaired ATM-IV coverage must be reconciled, entry/close-path source coverage must be frozen, and the finite A0/A1 development/validation selection policy must be complete before economic outcomes are opened. The final holdout remains sealed.

The implementation must also satisfy a causal-isolation falsifier: deliberately malformed stock/IV observations strictly after a frozen decision timestamp may not change or refuse that earlier A1 row.
