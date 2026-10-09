# Defensive compounders — deeper strategy study v2

## Current milestone: design and execution-engine audit

Current Chairman instruction: deeper assessment, indicator testing, methodology checks and stock-specific strategies. Research only; no broker action, live sizing, alert installation or production change.

Protected source remains Mastermind `326c8469a21d7f50fc9ecb1848196bf1c6e66685`, compatible skillpack 1.0.1/bootstrap 1, verified unchanged. Recover the predecessor dossier at macro `71011b7cc9235b478cac9c45550985a2e34b3c8c`. The 44-file original snapshot manifest remains `69703435b594cca35ea7f8e26673dc719c0ec9b3db3dc802df9ca531e0ce6ed3`. Original files are unchanged and must not be overwritten. Existing research branch readback equals that predecessor; no displaced writer or uncertain effect is observed. Direct work is retained for intertwined method design and adjudication (PRINCIPAL_JUDGMENT); no child was dispatched.

## Frozen extension

Same 18 equities; data through October 8, 2026. New designs are exploratory chronological replays: 2023–2026 was already inspected in the predecessor and cannot be called a fresh blind holdout.

Twelve families, three levels, four frames (1D/2D/3D/calendar week), two stock-context gates (unrestricted or above 200-day average with rising 50-day average), three exits: 288 signal specifications and 864 complete policies per stock, 15,552 stock-policy trials. Families: support failure/reclaim, negative MACD crossover, earlier volatility-normalized MACD reversal, RSI(2) dip, RSI(14) recovery, Bollinger reentry, EMA pullback, Donchian breakout, StochRSI, MFI, low-anchored daily-bar volume-weighted proxy and confirmed bullish divergence. The volume-weighted proxy is not trade-level VWAP. Volume rules quarantine 260 sessions after a split to avoid unverified volume-unit transitions.

Completed bars, following-open entries, five basis points cost per side, no leverage, zero interest on idle cash, one fully funded paper position at a time. Exits: initial three-ATR stop plus 20-session next-open timeout; same plus daily RSI >=60 next-open exit; closing-price three-ATR trail plus 63-session next-open timeout. Stops breached by gaps fill at the opening price. Trailing stops are never raised using an unfinished candle. Policies liquidate at calendar year-end to make annual selection explicit; this is an actual rule, not hidden event deletion.

Static selection uses only 2011–2022. Eligibility: 40 trades, eight active years, positive cumulative return in each six-year half, seven profitable years. Rank by mean annual return minus half its standard deviation minus 0.10 times worst annual drawdown magnitude. Six-year rolling annual selection from 2017 uses 20 trades, four active years, four profitable years and positive returns in both three-year halves. No qualifying policy means cash; gates will not be weakened. Report annualized return, drawdown, exposure and trade economics against same-stock buy-and-hold and causal 200-day timing, not win rate alone.

Disclosed stress tests: neighboring settings, bar-start phase, 20/50-basis-point costs, delayed execution, precomputed opening limits, alternative exits, regime and pivot-proximity diagnostics, earlier historical stress where data permits, and random-entry/multiplicity diagnostics with limitations. Extra tests do not retroactively become blind evidence or authorize live changes.

## Verified delta and frontier

The portable engine passed 19 local mechanical tests, including independent known-value RSI, prefix invariance, scale invariance, completed weekly/multiday bars, divergence confirmation timing, next-open execution, gap stops, entry-day stops, nonanticipating trails, round-trip fees, opening limits, no overlapping trades and year-bounded policy selection. A benchmark timeout defect was caught by a dedicated failing test and corrected before any research result was evaluated. Tests prove these mechanics, not profitability.

Public secondary-vendor Stooq retrieval returned a browser-verification page rather than prices; no cross-vendor validation is claimed. Existing licensed Tiingo documentation identifies adjusted OHLC/dividend/split fields, but no credential was read or entitlement assumed. Original snapshots remain the research basis.

NEXT: execute the frozen registry on the existing snapshots, adjudicate the full portfolio results, then perform targeted falsification/stability tests. This is a checkpoint, not a completion statement. Remote analysis has not started at this checkpoint; there is no active external worker or unresolved modifying effect.
