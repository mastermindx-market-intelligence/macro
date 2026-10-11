# Defensive nested washouts V8 — leading-candle correction and causal identifiability

**Research date 2026-10-10. Mission incomplete: real-stock strategy validation remains unproven.** Research-only source fork, not Macro production code, live signal, trade, allocation, deployment or order.

## Current assignment and authority
User requested further depth on weekly/two-week StochRSI washout followed by shorter native RSI-MACD bullish entry, retaining macro/issuer causal context. Protected Mastermind INDEX, COLD_START, ACTIVE_EXECUTION and SESSION_RELIABILITY were reloaded from the same protected master SHA `326c8469a21d7f50fc9ecb1848196bf1c6e66685` (skillpack1.0.1/bootstrap1 compatible). Previous V7 research revision verified `81681b3255dcfbb8bc35f832eef4ee65194a8153`.

The V3 result-table read and V4 composite remote earlier/native price-data acquisition were previously refused. **No retry, replacement acquisition/export, carrier switch or equivalent computation was attempted.** Local work used only uploaded V5/V6/V7 research scripts and manufactured input fixtures; independent M2 Studio work was mathematical/calendar checking only, no market history. No active child or pending risky modification.

## Main new verified defect and repair

Two research paths treated an *initial truncated native candle* as fully complete.

1. The V4 research `native_bars` could accept a Tuesday-start initial W or 2W candle though its nominal period began Monday, and could commit a shortened first phase-shifted 3D bucket.
2. The V5/V6 daily-close `clock_engine.snapshots` could likewise commit a phase-shifted initial 2W fragment as a genuine completed native candle.

**New fork behavior:** for phase-shifted 2D/3D groups the first group must have the required calendar-session count; for weekly/two-week groups the supplied calendar must establish the native nominal Monday at the front. Unverifiable leading native bars are discarded, not used to seed RSI, StochRSI, MACD-RSI or confirmations. Committed later groups preserve their end-session timestamps. The pre-V8 batch source is preserved unmodified as `source/v4_original_snapshot.py`.

Six constructed regression tests failed before the respective code repairs (three batch, three native-snapshot), and passed after. One inherited test explicitly asserting the old V4 fragment was updated to *compare preserved-old against fixed-new* rather than deleting the evidence. Final full inherited/new test command `python -m unittest discover -s tests -v` returned **117 tests OK**. This is mechanical evidence, not measured impact on any real stock.

**Limit:** a true exchange holiday on an opening Monday may make a Tuesday start legitimate. Without an authoritative extended exchange session calendar, the fork is intentionally conservative and may drop that genuine initial candle. TradingView chart anchor/phase parity remains UNKNOWN. No production changes have been made or authorized by this research.

## Ex-ante identifiability demonstration — SYNTHETIC ONLY

Using the prior manufactured input and a genuine declared W+2W washout with daily RSI-MACD bullish confirmation at manufactured index2093, January10,2008:

- Two constructed data paths are identical through the full observed signal date. Weekly/2W context, lower MACD-RSI crossover, boundary price and ATR are identical, maximum prior numerical difference **zero**.
- They share the same following-session synthetic open **121.43213160195904 units**.
- Only after that signal do *unobserved* +0.17% daily versus -0.17% daily log-drift branches diverge, using identical independently generated subsequent noise.
- Over the common126-session future the manufactured marked entry returns are **+23.5656% versus -19.4907%**, before cost.

This is a mathematical counterexample to *guaranteed* pivot correctness from past prices alone; it **does not refute** a conditional probabilistic signal. Dated fundamentals, issuer events, real-yield/credit and sector/index environment remain candidate causal covariates, not validated gates. Never label those futures as actual MCD/WMT/WM/COST/PG outcomes.

## Statistical evidence budget — exact independent Bernoulli illustrations ONLY

For **pre-fixed** one-sided 5% exact binomial significance and 80% power, assuming **independent Bernoulli events, fixed null hit probability and no post-hoc selection**, the approximate minimum samples are:

| Null positive probability | True alternative | Minimum independent events |
| --- | --- | ---: |
| 55% | 65% | **150** |
| 55% | 70% | **70** |
| 60% | 70% | **143** |

An illustrative 10/12 positive-outcome rate (83.3%) has a two-sided exact 95% interval of **51.586%–97.914%** before any cross-asset dependence or familywise multiple-search adjustment. Actual sequential washout episodes share market regimes and are not independent Bernoulli draws; the table is **not** a capital-allocation or alpha power calculation. Simple hit-rate comparisons ignore lost winners, losses' severity, exposure and timing costs.

An independent M2 Studio Python/SciPy check confirmed the two-week phase boundary and the first design's n=150 critical threshold=93, exact type-I tail0.0497256 and power0.8045954. No real-stock input was used.

## Qualification next action

The key missing experiment remains the corrected native-price **real-equity** replay on MCD/WMT/WM/COST/PG under legitimately accessible inputs and chart-setting parity:

- Fixed W/2W long-washout episodes and first daily/2D RSI-MACD cross; also compare developing versus completed W/2W data without lookahead.
- Prespecify whether a short StochRSI filter gates the same first cross or waits for a later cross; retain declined and unfinished episodes.
- Compare equal-calendar-time account returns, stock buy/hold, cash, arm-immediate entry, unfiltered crosses, and relevant sector/index exposure; include spread/gap, dividends, cycle-stop and at most-two tries.
- Test issuer/rates/credit effects only with source-available point-in-time covariates and a separate fresh prospective time segment. **Do not** move a price-MACD or standalone RSI(2) result onto this different method or infer certainty from a best-looking ticker.

No chart parity, historical performance, optimized exit, forecasting alpha, portfolio covariance, real rate sensitivity or recommended sizing has been proven. Data/permission restrictions remain. The independent V8 method/math portion is delivered; the real-market lane is genuinely blocked pending legitimately available original data/chart evidence, not a user ceremony or implied account-mode override.

## Deliverables and verification

- Conversation attachment: `/mnt/data/Defensive_Nested_Washout_V8_Causal_Boundary_Research_2026-10-10.zip`; SHA256 **`be4b63016ce029dc69669167a8bb5980a20e7a1ac075bfdcdc64c2a036c17dd7`**.
- ZIP CRC all entries OK;35 manifest-member SHA matches across36 ZIP entries including manifest. No vendor bars, secrets, brokers, or network acquisition source.
- Detailed report `/mnt/data/defensive_nested_v8/RESEARCH_FINDINGS.md` SHA256 `f4340273d8098288bd005a30803acb938de158e7be07667929b8f6732a8ed4b8`.
- V8 batch `v4_reference.py` SHA256 `b7472c5dee372a83f12d56cf186084890dc8b107bacc853807ab267533d3d3b1`.
- V8 clock `clock_engine.py` SHA256 `fa946995a7ec883582a106372e6e5aa811a34822d1b8effc02a0d8a3aeac3a29`.
- Manufactured counterfactual JSON SHA256 `9ae22a0a683952800e85ff35f24546c7c87ec9c9a1dc482fd73348c9fd1e030f`.
- Inherited V7 null research remains at preceding commit; V8 does not overwrite or rerun it.

Primary method references: https://www.tradingview.com/support/solutions/43000502333-stochastic-rsi-stoch-rsi/ ; https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/ ; https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/ ; https://escholarship.org/uc/item/4w1110bb . These support definitions and overfitting controls, not empirical profits.

**Final state:** method fixes verified; full mission incomplete. The remaining empirically decisive lane lacks accepted native-price access and chart-parity evidence. No active child, watcher, unresolved write or execution-uncertain effect; no unattended continuation armed.