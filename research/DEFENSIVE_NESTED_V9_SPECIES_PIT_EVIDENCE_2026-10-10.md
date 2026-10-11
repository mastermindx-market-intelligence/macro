# Defensive nested washouts V9 — RSI-MACD species, two-week anchors, and ex-ante depth

**October 10, 2026. Research checkpoint. MISSION_COMPLETE=false: no validated real-stock W+2W-to-lower-RSI-MACD strategy.** This is an additive source/math audit, not a production change, deployment, broker action or live allocation.

## Parent intent and provenance
The Chairman's requested study is weekly + 2-week StochRSI long washout followed by shorter RSI-MACD bullish crossover, with real economic/rates/market-regime explanations, false-entry avoidance and appropriate long-cycle exits. Ordinary price-MACD V2 results do not test it. V8 protected law remained Mastermind `326c8469a21d7f50fc9ecb1848196bf1c6e66685`, skillpack1.0.1/bootstrap1. INDEX, COLD_START, ACTIVE_EXECUTION, SESSION_RELIABILITY, CLOSEOUT were reloaded from that one commit. V8 predecessor research branch head independently checked: `e6d20224c8db4a865515e8d880875fac72802385`.

Source audit pinned to current accessible macro main `41b20190831bea6413b3e85c7a436fd9af6252f9`. **No denied action was retried.** Earlier V3 result read / V4 composite raw equity acquisition remain blocked. The audit used approved source-file reads, an independently mounted *synthetic-only* previous offline research package and manufactured local inputs. No remote M2 vendor price history was read, no blocked result was reproduced via an alternate carrier and no account, permission, watcher, worker or production runtime effect occurred.

## Material discoveries: exact source identity matters
The Macro repository has multiple distinct RSI-MACD species:

| Consumer | Oscillator | RSI/EMA treatment | Evidence |
|---|---|---|---|
| `engine/canon.py` and the Entry Radar's canonical reference | RSI14 -> EMA14(RSI)-EMA60(RSI) -> EMA5 signal | SMA-seeded Wilder RMA; `ewm(adjust=False)` | Canonical reference, **not proof this is every served chart** |
| `engine/technicals.py` + `engine/confluence_tiers.py` / `engine/signal_quality.py` | RSI14 -> EMA14-EMA60 -> EMA5 | `ewm` default `adjust=True` for RSI/EMA, different startup | Served confluence path documented in October 4 A1 parity dossier |
| `engine/mag7_washout.py` | RSI14 -> **EMA12-EMA26 -> EMA9** | `engine.technicals.rsi` plus default `adjust=True` | Distinct house `TH_RSIMACD+`-analog washout organ |

Both the canonical and served RSI source have a zero-average-loss to NaN edge (as V7 warned), but its real-stock frequency remains unknown. The October 4 parity dossier reports that canonical, independent Pine-formula and served 14/60/5 methods had **zero bullish crossover-date discrepancies after 400 warmup bars** on SPY daily, and canonical vs served on SPY 3D, despite meaningful initialization differences. This is existing report evidence, not recalculated now. It does not establish 12/26/9 chart identity.

The Mag-7 source's 2W bar method is `weekly=close.resample('W-FRI').last().dropna(); weekly.iloc[::2]`: phase is **tied to the first observed week**. On the deliberately oscillatory manufactured 3,250-session input, dropping exactly one initial week flipped all 2W closing-Friday parity; dropping two weeks preserved parity. With a synthetic 2W StochRSI comparison, the changed phase produced median **5.08 K points** of absolute difference and **10/252** recent daily oversold-state disagreements in twelve closely related manufactured paths. Fixed absolute-week phase produced identical shared closing bars after the same edit. **Not a statement that the current Mag-7 store is changing phase live**, just a reproducible source-vintage sensitivity requiring chart-native parity.

The same manufactured input yielded 14/14 coincident bullish crosses for canonical versus served 14/60/5 after bar400, versus 14/16 and **zero exact-date overlap** with the 12/26/9-on-RSI variant. Twelve almost-identical synthetic path variants preserved that behavior. Such paths are not independent stock backtests and these numbers are not forecasts of real markets. A standalone V9 unit regression reproduced and repaired accidentally using pandas DataFrame `.hist` method in place of its `['hist']` column; the comparison is tested.

**Adjudication:** Two MACD-RSI definitions must be pinned as explicit alternative hypotheses for chart/source parity. Choose *which one matches the user's original dated chart signals before inspecting stock returns*. Do not expand hundreds of settings to find a post-hoc winner.

## Recovered existing, nonduplicative studies
The actual Macro owner's July 6 G-HTF1 Phase-0 examined 224 U.S. names under completed 3D+2W RSI-MACD/StochRSI *confluence-active* criteria. S1 FW1 had 423 historical fires, 27.2% 20d close-only −5% stop-out, and mean21d excess +0.90% versus SPY (as reported). S1 FW2 had 641 fires, 27.0% close-only stop-out and +0.68% 21d excess. Same-panel, same-ruler T1 baseline had 30.4% close-based stop-out, **not** the older unrelated 38.3% intraday-low measure. The report estimates ~35% intraday-stop S1 versus ~37.5% T1. S1 also entered *later* than T1, and at a higher premium over the preceding low. S2's predeclared premium gate failed, 21d/63d excess was negative-to-null, and two-week historical repaint was explicitly UNMEASURED (a reported 0.0% from retrospective final candles was misleading). The author's grade is a display sponsorship badge, **not** a universal early-entry alpha claim. This S1/S2 method is not identical to the user's W+2W washout, first 1D/2D RSI-MACD cross and long-cycle exit.

The August 5 `MCD_MISS_EVIDENCE` recorded a July31 2026 weekly 14/60/5 RSI-MACD bullish crossover at a historical ~6th-percentile oscillator depth. Its descriptive `n=31` deep-cross census reported median +5.5% at13 weeks (67% positive) and +7.9% at26 weeks (70% positive), with major-bear failures. **This is not a validated W+2W traded strategy.**

## Crucial correction: MCD historical depth used future observations
A new read of `engine/washout_turn.py` explicitly confirms its **whole-sample** historical `depth_pctile` uses oscillator readings after past crossovers. The source labels those older percentile/base-rate summaries *descriptive*, with right-censored events excluded. At the current final bar, the current historic depth is knowable; at any past event, future observations are not. The code also documents a history-deepening splice for MCD that affects percentile/base-rate context without modifying the recent signal input.

V9 added `point_in_time_depth.py` which ranks a weekly oscillator's current value relative only to prior finite observations, requires a declared minimum of200 past native bars, preserves unavailable states as unknown, and never changes an earlier signal because of future data. A constructed history with 200 earlier values produced a current depth of **24.5%**; adding high future readings made the past depth appear **less than15%** using the whole-sample calculation, falsely qualifying that old event after the fact. On twelve closely related manufactured 650-week trajectories, out of162 native bullish crosses,108 had sufficient PIT history, and a fixed15% rule qualified36 PIT vs39 whole-sample historical events (3 disagreements). These are **synthetic tests**, not a corrected count or return for MCD. The user's MCD historical success rate must not be presented as a PIT-strategy statistic without a genuine readout under legitimate data access.

## Verification and delivery
- Local V8 baseline re-executed: **117 tests pass** (24.37s), earlier material unmodified.
- New V9: **11/11 tests pass**, including red/green regression, source species and phase-prefix tests, PIT historical-depth and future-perturbation invariants. Combined total **128 passing checks over two separately verified suites**, not a claim of 128 independent models.
- Full V9 report: `/mnt/data/defensive_nested_v9/RESEARCH_FINDINGS.md`, SHA256 `16a44a142924f10958f284a33e27f7c3bcb5009b997ae87acb33079d10db150f`.
- ZIP `/mnt/data/Defensive_Nested_V9_Indicator_Parity_and_PIT_Depth_2026-10-10.zip`, SHA256 `0dba77bb2f4e2918f7086241fd86f3a72b1d480faa53f7432a125adb6912a41d`;22 included premanifest files verified by SHA; ZIP CRC passed. No market prices or credentials.
- Two main source files: offline `species_audit.py` and `point_in_time_depth.py`, synthetic manifests, tests and logs.

## Next empirical frontier and stop
Do NOT build another parallel production indicator/queue. Once **legitimately provided** chart/price input becomes permitted, compare the user's native RSI-MACD species/2W calendar with the existing owners' definitions at dated example events. Then freeze master W+2W washout episodes and compare immediate-watch, first 1D/2D cross, fast/weekly/slow exit and reasonable reentry, preserving all missed/lost/incomplete opportunities, stop/gap/capital opportunity and clustered uncertainty. Recompute historical deep-cross labels using a **prior-only oscillator distribution**. Causal rates/issuer/market context must be timestamped independently; no retrospective veto fitting. Recent price history is already inspected and not a fresh blind holdout.

Current state: **SOURCE_AND_SYNTHETIC_RESEARCH_VERIFIED, REAL_MARKET_ALPHA_UNPROVEN**. Requested empirical completion cannot be claimed because inherited market-data access remains denied. This is a scoped partial result with a precise next action; not a production-ready rule, recommended allocation, alert or background run. Pro mode would not clear the refused data access.

### Exact source links
- [Macro code at pinned main](https://github.com/mastermindx-market-intelligence/macro/tree/41b20190831bea6413b3e85c7a436fd9af6252f9)
- [July G-HTF1 original results](https://github.com/mastermindx-market-intelligence/macro/blob/41b20190831bea6413b3e85c7a436fd9af6252f9/research/signal_engine/HTF_SUPER_TIERS_PHASE0.md)
- [October served/canon/chart-date parity](https://github.com/mastermindx-market-intelligence/macro/blob/41b20190831bea6413b3e85c7a436fd9af6252f9/research/prophet_v4/astra_regime_indicator_handoff_20261004/results/A1/parity.md)
- [MCD August historical receipt](https://github.com/mastermindx-market-intelligence/macro/blob/41b20190831bea6413b3e85c7a436fd9af6252f9/research/washout_turn_name_lane/MCD_MISS_EVIDENCE_2026-08-05.md)
- [MCD whole-sample-percentile source](https://github.com/mastermindx-market-intelligence/macro/blob/41b20190831bea6413b3e85c7a436fd9af6252f9/engine/washout_turn.py)
- [Mag-7 species/2W phase source](https://github.com/mastermindx-market-intelligence/macro/blob/41b20190831bea6413b3e85c7a436fd9af6252f9/engine/mag7_washout.py)

