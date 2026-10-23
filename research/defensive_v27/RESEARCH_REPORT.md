# V27 — October 13, 2026 After-Close Paper-Only RSI-MACD/W+2W Observation Freeze
**Published research status: PARTIAL. No trading signal adoption, broker order, fill or allocation.**

## Why this phase matters

Prior V11–V26 research established a historical association between **long weekly/two-week StochRSI washouts** and later recovery in five original defensive compounders, but also identified nonindependent crossovers, low incremental stock-selection precision, strong sensitivity to chart phase and extreme model-selection uncertainty. The missing scientific requirement is observation of genuinely **future** outcomes under settings and data actually frozen before those outcomes exist.

**V27 provides a first dated, after-market paper-only observational starting point on October 13, 2026, 5:43 p.m. Eastern.** It does not make the previous 2018–October8 research a prospective holdout and does not guarantee that the vendor's after-close snapshot is exchange-final. It does not install or schedule a watcher. Future observations require a separately admitted task or an existing authorized market-data consumer.

## Source custody and chronology

- Frozen study-method specification authored at **2026-10-13 21:37:42 UTC**; an initial erroneous assumption of four, rather than **three**, equity sessions after October8 was corrected **before acquisition** using the earlier accepted NYSE session tail (October9,12,13).
- One separately dated public Yahoo daily-chart vendor vintage was obtained at approximately **2026-10-13 21:38–21:40 UTC**. All **19 symbols** (18 original equities plus SPY) passed explicit OHLC/adjusted-close/session-date verification, with **4,220 common sessions January4 2010–October13 2026**. The original 4,217-date input prefix and three new date suffix agreed with prior accepted records. Source URLs, fetch times, per-symbol SHA-256s, counts and errors (none) were journaled.
- The observed SPY source after-close collection was **21:38:35 UTC**, and the final full multi-name manifest was acknowledged **21:40:35 UTC**.
- The paper observation itself was frozen at **2026-10-13 21:43:09 UTC / 5:43 p.m. Eastern**, before the following October14 U.S. equity session. No prices or outcomes from Oct14 or later are present.
- The new vendor's historical adjusted-price ratios differ from the previously inspected same-provider V12 vintage by a maximum of about **1.1 × 10^-6** over overlapping daily closes for the equities; the original data were **not overwritten** or spliced.
- The new price source remains **the same vendor as prior V11/V12**, **not independent market data**. The label **AFTER_CLOSE_VENDOR_UNATTESTED** explicitly means the daily bar was available after close, but the exchange-finality, dividend-accounting fidelity, tradable price/slippage and the user's chart-native phase are not independently proven.

No earlier restricted 1985-history V4 acquisition, V3 result-table read or denied cache change was attempted. No private brokerage data or credentials are involved. Raw vendor OHLC files stay on the M2 and are **excluded from the deliverable archive and GitHub**.

## Model definition kept fixed

The source uses the preexisting V11 formula: native RSI14 (Wilder), RSI-MACD = EMA14(RSI)-EMA60(RSI) with EMA5 signal, StochRSI14/14/3/3. The long watch requires K<=20 in the latest three **completed W** bars and latest two **completed 2W** bars, with 200 completed native warmup bars; the watch expires after42 daily sessions or K>=60 and waits10 clear sessions for rearm. The primary lower trigger is the first fresh completed daily or two-day RSI-MACD bullish line cross. Every individual lower bar has its native calendar phase; a forming two-week candle is not finalized early.

A second, explicitly labeled **daily-close developing W+2W** view is produced for comparison. No Phase0/Phase1 backtest return optimization, altered threshold or multi-signal vote was conducted in this paper observation. User-chart exact phase, split adjustment and developing-bar setting are still **UNVERIFIED**; these are house-study definitions only.

## October13 as-of classifications, not October14 buy recommendations

All 18 names × 2 lower frames × 2 long-state conventions = **72 dated ledger rows**. The confirmed W+2W view contains:

| State | Count over 36 stock/frame pairs | Interpretation |
|---|---:|---|
| No currently active historical watch | 24 | The last watch is expired or absent at the cutoff |
| Active watch where first bullish lower cross fired on an earlier date | 9 | This is not a new signal or automatically an open position |
| Active W+2W watch, no qualifying fresh lower cross yet | 3 | Research watch only; no order or risk sizing |
| New first lower cross on October13 with following open not yet observed | **0** | No confirmed-model fresh last-bar trigger in this 18-name/2-frame panel |

For the **original core five**:

- **MCD:** daily watch armed September11 and previously crossed October8; by October13 its following opening price is now present in the vendor dataset, **but no broker fill is established**. Its two-day model still has an active watch without a fresh confirming 2D cross.
- **WM:** daily earlier cross October5 and 2D earlier cross October7 remain inside their model watch. Neither represents a **new** October13 entry.
- **WMT, COST and PG:** no active watch at the October13 cutoff in the completed-bar model.
- **Other active unconfirmed 2D watches:** PEP (armed September25) and HSY (armed September25). Their future crossover behavior is unknown.
- Existing active *earlier* watch crosses for PEP, CL, CHD and HSY are source-status labels, not actual holdings or order suggestions.

Across the full ledger, relative to the dated **October8** historical reconstruction, only **2 of 36 confirmed** and **3 of 36 developing** stock/frame states changed their coarse active/inactive categories by October13. This is not a measurement of invariant native raw indicator values: three new trading bars, native candle rolling, and a separately dated vendor snapshot all changed.

**No order, paper-broker fill, allocation, or current chart-parity claim was emitted.** An observable next-open market price is only a market-data record, not an executed trade. The paper status can be inspected retrospectively without identifying the next-day outcome in advance.

## Verification and delivery

- **15 fresh local tests passed:** six malformed-provider/calendar/adjusted-OHLC tests and nine paper-cutoff/time/fill-semantics tests.
- **19/19** source symbol histories verified with identical **4,220-session** dates; explicit manifest hashes and fetch times.
- All output labels have observed-cutoff and actual freeze timestamps, per-frame and confirmed/developing states, source finality status, native indicator levels and whether an unobserved next open is required.
- Original historical V11/V12 input files and results were untouched. A new dated M2 folder contains the raw-vintage data, but the published research ZIP includes only **code, tests, specifications, source hashes, event classifications, and provenance/verification receipts**, never original OHLC bars.

## Unfinished genuine proof

A **future** market-data bar beyond October13 and a still-binding, externally auditable paper ledger update are required for actual prospective return evidence. User TradingView chart parity is the immediate technical prerequisite for making these exactly the user's RSI-MACD/StochRSI strategy. Missing: independent vendor, earnings/consensus release-vintages, a neutral stock panel that includes delisted companies, real execution slippage, conditional market-regime calibration and prospective selection-adjusted performance.

If future monitoring is authorized, use an **existing** market-data/Entry Radar/Executive scheduler rather than creating a duplicate autonomous queue or watcher. This report does **not** claim unattended monitoring or a live deployment.

### Prior research and authority
- [Merged original V11 study #9034](https://github.com/mastermindx-market-intelligence/macro/pull/9034)
- [V12 separate follow-up #9064](https://github.com/mastermindx-market-intelligence/macro/pull/9064)
- [V13–V20 portfolio and recovery audit #9129](https://github.com/mastermindx-market-intelligence/macro/pull/9129)
- [V21–V23 dated historical watch and context #9174](https://github.com/mastermindx-market-intelligence/macro/pull/9174)
- [V24–V26 overlap and phase falsification #9176](https://github.com/mastermindx-market-intelligence/macro/pull/9176)
