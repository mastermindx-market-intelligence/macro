# Defensive compounders — deeper strategy study v2

## Milestone: frozen registry executed; falsification continues

Current Chairman instruction: deeper stock-specific strategy assessment, indicator testing and methodology checks. Research only: no broker, live sizing, alert installation or production effects. Predecessor report is macro `71011b7cc9235b478cac9c45550985a2e34b3c8c`. Compatible protected source remains Mastermind `326c8469a21d7f50fc9ecb1848196bf1c6e66685`, skillpack 1.0.1/bootstrap 1. Original snapshot manifest `69703435b594cca35ea7f8e26673dc719c0ec9b3db3dc802df9ca531e0ce6ed3` was reverified across all 44 files without changing the originals.

The expanded study completed 288 signal specifications × three exits × 18 stocks = **15,552 stock-policy trials**, each replayed through 16 calendar-year segments. These are correlated trials, not independent evidence. Nineteen mechanical tests passed on both local and research-host runtimes. No real worker was dispatched; method design and adjudication remain directly owned as PRINCIPAL_JUDGMENT. The main analysis process completed normally, with exit code 0.

## Method frozen before evaluating the expanded results

Same 18 equities and October 8, 2026 cutoff. Twelve families, three levels, four frames (1D/2D/3D/calendar week), two stock-context gates (unrestricted or above 200-day average with rising 50-day average). Families: failed low-break/reclaim, negative MACD crossover, earlier volatility-normalized MACD reversal, RSI(2) dip, RSI(14) recovery, Bollinger reentry, EMA pullback, Donchian breakout, StochRSI, MFI, low-anchored daily-bar volume-weighted proxy and causally confirmed divergence. Volume rules quarantine 260 sessions after splits. The volume-weighted proxy is not trade-level VWAP.

Completed-bar information, next-opening-price entries, five basis points per side, one fully funded paper position, no leverage and zero yield on cash. Exits: initial 3 daily ATR stop plus 20-session next-open timeout; same plus daily RSI >=60 next-open exit; prior-completed-close 3 ATR trailing stop plus 63-session next-open timeout. Opening gaps through stops fill at the opening price. Year-end liquidation is an explicit part of every annually selected policy; the final research endpoint is liquidated at close.

Static selection uses only 2011–2022, requires 40 trades, eight active years, seven profitable years and positive cumulative returns in each six-year half. Eligible candidates are ranked by mean annual return minus half annual-return standard deviation minus 0.10 times worst annual drawdown magnitude. Annual rolling selection uses the preceding six completed years, 20 trades, four active/profitable years and positive cumulative returns in both three-year halves. Selection never consumes the current year's returns. A failed gate means cash, never a loosened threshold.

New designs are **exploratory chronological replays**, not a fresh blind 2023–2026 test: the earlier session already inspected those dates. Benchmark, exposure, drawdown and trial counts are mandatory interpretation context.

## Material new results, 2023–October 8, 2026

Annualized results below are portfolio-path returns with costs, not the predecessor's average 20-session event returns. Max drawdowns are close-marked with modeled stop/gap executions. They are not live guarantees or position recommendations.

| Stock | Training-selected policy | Annualized return | Max drawdown | Trades | Same-stock buy-and-hold annualized |
|---|---|---:|---:|---:|---:|
| MCD | Daily StochRSI cross from below 30; 3ATR trail/63-session cap | -10.01% | -43.46% | 39 | -0.50% |
| WMT | Daily 20-bar low-anchored volume-weighted proxy reclaim; 3ATR trail | -0.35% | -19.55% | 13 | +26.66% |
| WM | Daily 10EMA pullback/reclaim; initial 3ATR stop/20-session cap | +4.48% | -16.49% | 33 | +9.70% |
| COST | Daily StochRSI cross from below 30; 3ATR trail/63-session cap | +19.07% | -27.63% | 29 | +22.85% |
| PG | RSI(2)<10 on three-day bars; 3ATR trail/63-session cap | +5.81% | -12.86% | 21 | +2.55% |

Useful peer results from the same frozen selection: CTAS +18.98% annualized (24 trades, -25.06% drawdown) versus +17.52% buy-and-hold; RSG +11.56% versus +16.04%; KO +10.12% versus +12.19%; ADP +7.72% versus +5.60%; MDLZ +4.20% versus +0.36%. These are candidates for further falsification, not selection-adjusted proof. Other static winners include several negative results; do not hide them.

### Bar-alignment fragility is material

PG's nominal three-day winner produced +5.81% annualized in the anchor phase, but -3.63% when grouping began one trading session later and +2.09% in the third phase. RSG's two-day setup changed from +11.56% to +1.86%. KO's three phases were +10.12%, +9.00% and +2.83%. Selecting the favorable phase would be another optimization, not a repair. PG cannot currently be promoted as having a stable three-day optimum.

### Adaptive selection did not solve recent instability

Annual six-year rolling selection produced latest-period annualized results of MCD -0.70%, WMT -0.96%, WM +1.53%, COST +13.69% and PG -0.32%. An older-period positive annualized return is not enough to establish current strategy stability. The same daily StochRSI family selected for COST and MCD produced very different later paths; a common indicator label is not a transferable trading edge.

## Methodology evidence and limitations

All 18 stocks' dividend adjustment-factor checks found no discrepancy above ten basis points against the dividend amount/preceding-close identity. This is an internal corporate-action consistency check, not a second-vendor audit. Stooq's attempted secondary download returned a browser-verification page, not market data. No credential was read or licensed entitlement assumed.

Engine SHA256 `42e2d9900d43a1121a155c325e7aaecb58970873ba67e25089500c8292326e29`; runner `3b05439644f7673f2ba7654071622d59d50c9411cd208a4051978afe6b4a7d44`; tests `279dc7346317c61eb88043563aea784651feb9f93edc8a31b1b7213ba439e5ff`. Full annual trial grids and curated selected results are retained in the existing research artifact workspace `/tmp/mmx_defensive_deep_v2_20261009/results`; raw quote data are not being published.

## Continuation frontier

DO_NOT_REDO: original snapshots; full frozen registry replay; verified engine tests; acknowledged initial phase-instability findings. Next: independent indicator/cash-flow audit, original-candidate full-policy comparisons, post-selection stress/placebo diagnostics, earlier 2000–2009 stress history and final stock-by-stock adjudication. An earlier-history acquisition is a bounded research process, not a background worker; its manifest must be reconciled before use. No unresolved modifying effect or delegated child exists. This checkpoint is a save, not completion; continue safe in-scope testing.
