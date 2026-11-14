# Risk Radar legs mapped to risk-on/off types (for the RD's Slate v3 typing; one page)

Written from `engine/risk_radar.py` `leading_signals()` as coded. Every leg is a trailing 504-session
causal percentile of the transform shown, except corr_floor_break, which is a 0/1 flag. **Scored** marks
the 12 legs in the rr- catalogue reads. This page proposes no taxonomy; the type names are the
Principal's, pending the RD's addendum.

| Leg | Transform (inputs) | Channel it sees | Scored |
|---|---|---|---|
| credit_oas_roc | 21-session change in HY OAS (FRED, PIT) | credit/liquidity: spread widening | yes |
| credit_hyg_tlt | −20-session return of HYG/TLT | credit vs duration (also moves with rates) | yes |
| rates_move | MOVE index level | rate volatility | yes |
| rates_realrate | 5-session change in 10y real yield (DFII10, PIT) | rate-driven: real-rate shock | yes |
| bubble_ext | SPY vs its 200-day average | cap-weighted index extension (froth) | yes |
| bubble_leadership | SMH/SPY 63-session relative return | semis leadership concentration | yes |
| growth_defensives | 20-session return of XLU/SPY | defensive rotation (vs cap-weighted SPY) | yes |
| growth_cyc_def | −20-session return of XLY/XLP | cyclical/defensive rolldown | yes |
| vol_term | VIX9D (or VIX)/VIX3M | front-end vol stress (term inversion) | yes |
| global_breadth | − share of country ETFs above their 200-day average | **international** breadth only | yes |
| jpy_carry | −10-session USD/JPY change, gated (DEXJPUS, PIT) | carry-unwind liquidity | yes |
| corr_floor_break | COR1M at a low floor, then spiking (0/1) | implied correlation (a dispersion-regime *exit*) | yes |
| nh_contraction | US new-high share contracting at index highs | **US breadth** | no (41% D coverage) |
| ai_breadth_divergence | AI vs non-AI share above 50-day | narrow-leadership breadth | no (from 2025) |
| vol_putcall, vol_gex | equity put/call; dealer net GEX | hedging flow / gamma | no (from 2026-06) |

## By type

- **Rate-driven risk-off:** rates_realrate, rates_move, and in part credit_hyg_tlt. Well covered.
- **Credit/liquidity risk-off:** credit_oas_roc, credit_hyg_tlt and jpy_carry; vol_term for the stress
  spike. Covered.
- **Washout:** no leg measures capitulation (breadth thrust, the share of members at lows, a volume or
  put/call spike). The Radar's all-clear is the loud state decaying, which is not washout detection.
  The exit_v1 candidate adds a price lift-off and a credit stop, but still no breadth.
- **Broad vs narrow/masked risk-on, and masked risk-off:** **blind on the scored set.**
  - No scored leg measures US breadth, equal- vs cap-weight (RSP/SPY), dispersion, or high-beta vs
    low-beta (SPHB/SPLV).
  - Every equity price leg uses cap-weighted SPY or sector ETFs: bubble_ext, growth_defensives,
    bubble_leadership. A sell-off in breadth and high beta, under an index held up by a few large caps,
    leaves those legs quiet.
  - The two breadth legs that exist are not scored. nh_contraction has 41% coverage on D and a NULL
    phase-0 result; ai_breadth_divergence starts in 2025. global_breadth measures country ETFs, not US
    stocks. corr_floor_break sees the end of a low-correlation (high-dispersion) regime, not the
    dispersion itself.
- **The Principal's expectation is confirmed**, with one refinement. The Radar has no scored US breadth
  or dispersion leg, so a masked risk-off is invisible to it unless it also moves credit, rates or the
  cap-weighted index. The desk catalogue already holds the series that would see it as turn targets
  (RSP/SPY, IWM/SPY, SPHB/SPLV, CYC/DEF in U5). They are scored against the Radar but are not inputs to it.

## Candidate input (Principal ruling 3)

A US breadth/dispersion leg goes through the same history-availability page as put/call and GEX
(research/risk_radar/inputs_1b/). Candidates are RSP/SPY relative return, SPHB/SPLV relative return,
and cross-sectional dispersion of S&P members. Each is a forward candidate only, with no live-engine
change. RSP and SPHB/SPLV have daily history from the 2000s or 2011, so a D-block and PRE read is
possible, unlike put/call and GEX. That availability must be checked on the page.
