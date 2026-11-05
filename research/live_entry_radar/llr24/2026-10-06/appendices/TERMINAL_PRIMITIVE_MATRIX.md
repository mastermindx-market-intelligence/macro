# Appendix — Terminal primitive qualification matrix

Exact source version: `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`. Observation: 2026-10-06 UTC session. This is static source analysis, not a live incident finding, empirical model result, or a grant of research admission.

All listed defaults are implementation variants at this pin. The paired JSON preserves one row per reviewed primitive/variant with formula, grain, session behavior, event availability, history and incremental-evidence status. Every candidate remains BUILT_NOT_PROVEN until the incumbent qualifier admits its input and a chronological experiment establishes its use.

The shared history statement is repeated in the machine-readable matrix. It does not imply every source file was physically re-audited today. The physical inventory is the dated Oct 2 source report (T07).

## F01 — Session VWAP and volume-weighted bands

**Formula/version.** TP=(H+L+C)/3; VWAP=sum(V*TP)/sum(V); sigma=sqrt(max(0,sum(V*TP^2)/sum(V)-VWAP^2)); default multipliers 1/2/3; nonpositive V ignored; includePm=false. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Intraday OHLCV; bar-volume approximation, not trade VWAP. Resets calendar display day; skips before 09:30 US when includePm=false, but does not stop at 16:00. No 20:00 economic-day reset.

**Causality and emission.** Trailing endpoint conditional on completed qualified bars; partial first session produces partial VWAP.

**Research status.** BUILT_NOT_PROVEN; candidate after input/session qualification.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse pure arithmetic; bind explicit session policy and completeness, do not silently reinterpret as 24H VWAP.

**Sources.** [T14](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayMath.ts#L1-L173); [T15](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayMath.ts#L175-L401).

## F02 — Opening range and extensions

**Formula/version.** Default 15-minute window; high=maxH, low=minL for bars whose start minute is in [open,open+15); extensions 1x/2x range height. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Intraday; exact 15-minute range requires bars not straddling end. Calendar display day and market open; does not independently consult early-close calendar.

**Causality and emission.** Final range available after window complete. Returned historical rectangle starts at range start; final values visually backfill. Coarse bars can include post-window prices because membership uses bar start.

**Research status.** PRODUCT_GEOMETRY; endpoint feature only after completed-window qualification.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Store range formation end/available time separately from geometric start; reject straddling grain.

**Sources.** [T15](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayMath.ts#L175-L401).

## F03 — Slot and cumulative RVOL

**Formula/version.** Default baselineSessions=10, minimum 3 prior session slices; mean V at same minute slot and mean cumulative V through same slot; current V or cumulative V divided by those means. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Intraday; same slot must mean same grain/session. Skips before market open, but no explicit regular close cutoff; session slices are display dates and no completeness check.

**Causality and emission.** STATIC_CODE_FINDING: one baseline relative to the LAST session is applied to ALL historical sessions, so append changes earlier values. Latest endpoint can be causal with qualified prior sessions.

**Research status.** HISTORICAL_SERIES_NOT_PREFIX_CAUSAL; endpoint candidate.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Extract only then-known endpoint under frozen prior-session baselines; do not use full-array historical output as a research column.

**Sources.** [T15](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayMath.ts#L175-L401).

## F04 — TTM squeeze and momentum

**Formula/version.** 20-bar BB using population SD, BBmult2; Keltner SMA20 +/- RMA(TR,20)*1/1.5/2. Tightest containment => squeeze 3/2/1; none0. Momentum: last fitted regression value over 20 of C-(((HH20+LL20)/2+SMA20)/2). Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any bar grain; settings are bars, not clock minutes. No session reset.

**Causality and emission.** Trailing computation; available at last input bar close. No data-arrival contract in function.

**Research status.** BUILT_NOT_PROVEN; candidate arithmetic.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse named exact variant; do not conflate with different BB SD convention or normalized momentum.

**Sources.** [T16](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayMath.ts#L408-L641).

## F05 — ADX / DI

**Formula/version.** Default len10. Wilder RMA TR and positive/negative directional movement; DI=100*DM/TR; DX=100*abs(DI+-DI-)/(DI++DI-); ADX=RMA(DX). Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any bar grain. No session reset.

**Causality and emission.** Trailing, conditional on closed input; warmup depends RMA seed.

**Research status.** BUILT_NOT_PROVEN.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse explicit ADX10; techRating ADX14 is a different feature.

**Sources.** [T16](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayMath.ts#L408-L641); [T25](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/techRating.ts#L565-L634).

## F06 — Intraday CVD approximation

**Formula/version.** Per-bar delta=V*(2C-H-L)/(H-L); zero-range bar uses sign(C-previous C)*V; sum from display-day start. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** OHLCV bars, not aggressor trades. Calendar display-day reset; zero-range comparison can use previous-day close.

**Causality and emission.** Trailing endpoint with completed bars; not real cumulative signed trade delta.

**Research status.** PROXY_ONLY; BUILT_NOT_PROVEN.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Name OHLCV close-location volume imbalance; preserve volume provenance and avoid claims of observed buying/selling.

**Sources.** [T16](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayMath.ts#L408-L641).

## F07 — Classic/Camarilla/Fibonacci prior-day pivots

**Formula/version.** Classic P=(H+L+C)/3; R1=2P-L/S1=2P-H; R2/S2=P+/-range; R3=R1+range/S3=S1-range. Camarilla C+/-1.1*range/(12,6,4,2); Fib P+/-(.382,.618,1)*range. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Prior completed daily HLC projected into intraday. Caller supplies prior-day OHLC; helper itself has no clock or holiday validation.

**Causality and emission.** Available only after source daily bar complete and known.

**Research status.** BUILT_NOT_PROVEN; conditional candidate.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse deterministic transforms of qualified prior-session data; variants and basis must be named.

**Sources.** [T17](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayMath.ts#L654-L793).

## F08 — Session and prior-week levels

**Formula/version.** PDH/PDL/PDC from latest daily date strictly before current intraday display date; previous ISO-week high/low; first bar >= open; premarket high/low from bars before US open. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Daily plus intraday; requires aligned clocks. Display calendar dates; US premarket branch has no >=04:00 lower bound if raw overnight were passed.

**Causality and emission.** Past daily selection avoids same-day close, but depends on upstream basis/availability; current-session levels evolve.

**Research status.** BUILT_NOT_PROVEN.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse reference-level display and source dates; qualify economic-session mapping.

**Sources.** [T17](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayMath.ts#L654-L793).

## F09 — DayStats gap/range/VWAP/HOD/LOD

**Formula/version.** Gap uses first RTH open vs prior daily close. Range used=(today H-L)/mean prior daily TR; implementation uses last14 daily rows => at most13 TR and accepts short history. Delta VWAP uses F01. HOD/LOD uses all loaded today bars. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Intraday plus daily. Badge is time-of-day PRE/RTH/AH/CLOSED, fixed US16:00, no date/holiday input; range may include extended hours.

**Causality and emission.** Display statistics, incomplete sessions/history affect denominator and numerator.

**Research status.** PRODUCT_ONLY until exact definitions and completeness frozen.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse strip/component, not an assumed Wilder ATR14 or exchange session authority.

**Sources.** [T18](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/DayStatsStrip.tsx#L1-L112).

## F10 — SMA/EMA/RMA/ATR/percentile helpers

**Formula/version.** RMA Wilder with SMA seed; EMA alpha2/(n+1) SMA-seeded; some SMA implementations substitute missing with0; ATR RMA of TR; indicatorMath percentile counts <= over full finite window. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any supported bar grain. None.

**Causality and emission.** Trailing but warmup/missing semantics differ among classic, intraday and suite code. Suite percentile returns50 for fewer than10 samples; missing normalized observations may become0.

**Research status.** BUILT_NOT_PROVEN; exact implementation must be frozen.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse one named implementation per feature; preserve unavailable/neutral distinction before research ingestion.

**Sources.** [T19](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicatorMath.ts#L1-L105); [T31](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/shared/oscUtils.ts#L55-L287); [T23](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/ChartPanel.tsx#L408-L417).

## F11 — Anchored VWAP

**Formula/version.** TPV/V from fixed numeric anchor or default swing_low over final lookback252; swing_low/high actually global lowest low/high in that final window; vol_spike=maxV with latest tie; max_history begins max(0,n-lookback), not necessarily all history. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any bars; common daily use. No economic-session awareness; index anchor depends supplied history start.

**Causality and emission.** STATIC_CODE_FINDING: automatic anchor selected using whole final window, then historical series recomputed from it; later extreme changes old values/availability. Fixed previously declared anchor can be causal.

**Research status.** AUTO_ANCHOR_HISTORY_NOT_PREFIX_CAUSAL; fixed-anchor candidate.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Freeze anchor rule, event/confirmation time and source revision at decision time; endpoint snapshot only for dynamic anchor.

**Sources.** [T20](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicatorMath.ts#L264-L469).

## F12 — Rolling and week-anchored VWAP

**Formula/version.** Rolling20 TPV/V over last20 bars. Weekly TPV/V resets W-FRI calendar grouping. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any grain with supported time encoding. Weekly calendar group, not 20:00 economic day.

**Causality and emission.** Trailing endpoint; loaded-window truncation and bar approximations remain.

**Research status.** BUILT_NOT_PROVEN.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse after explicit time/volume basis; daily VWAP remains an OHLCV approximation.

**Sources.** [T20](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicatorMath.ts#L264-L469).

## F13 — Generic volume profile and rolling prior POC

**Formula/version.** vprofile default126 bars/24 bins over final minL/maxH; whole bar V assigned to TP bin, optional shelf weights close-location buyShare; POC maxV; 70% VA greedy adjacent expansion. rollingPoc separately recomputes profile on prior126 bars, excludes current. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any bars; price-bin and OHLCV approximation. No session policy.

**Causality and emission.** Final profile is an as-of snapshot, not a historic feature for all earlier bars. rollingPoc is explicitly per-bar trailing prior-window calculation.

**Research status.** SNAPSHOT_PRODUCT plus separate candidate prior-POC series.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse rollingPoc as named candidate; store snapshots when using final profile. Do not call bins traded-at-price volume.

**Sources.** [T20](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicatorMath.ts#L264-L469).

## F14 — Classic RSI

**Formula/version.** Wilder RSI14 default, OB70/OS30; classic ChartPanel loss==0 returns100, including flat all-zero gains/losses. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Chart current timeframe. No reset.

**Causality and emission.** Trailing; defined flat-series and SMA/EMA warmup differ from suite.

**Research status.** BUILT_NOT_PROVEN.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Freeze classic variant or deliberately specify research variant; no blind key-based import.

**Sources.** [T22](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicators.ts#L157-L244); [T23](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/ChartPanel.tsx#L408-L417); [T24](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/ChartPanel.tsx#L1327-L1382).

## F15 — Classic key stochrsi / label Stochastic RSI

**Formula/version.** Documented actual PRICE stochastic: rawK=100*(C-LL14)/(HH14-LL14), flat range50; K=SMA3(rawK), D=SMA3(K). It is not stochastic of RSI. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Current chart timeframe, despite CM_Stochastic_MTF source name. None.

**Causality and emission.** Trailing; classic SMA zero-fills null warmup positions, so early smoothed outputs need separate warmup admission.

**Research status.** PRODUCT_FORMULA_IDENTITY_CAVEAT; BUILT_NOT_PROVEN.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse only under price_stochastic_14_3_3 identity; registry comment explicitly explains label.

**Sources.** [T22](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicators.ts#L157-L244); [T23](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/ChartPanel.tsx#L408-L417); [T24](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/ChartPanel.tsx#L1327-L1382).

## F16 — Classic MACD-RSI

**Formula/version.** RSI(close,14); line=EMA(RSI,14)-EMA(RSI,60); signal=EMA(line,5); hist=line-signal. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Current chart timeframe. None.

**Causality and emission.** Trailing with classic RSI and moving-average semantics.

**Research status.** BUILT_NOT_PROVEN.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Keep separate from conventional price MACD and premium MACDX.

**Sources.** [T22](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicators.ts#L157-L244); [T23](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/ChartPanel.tsx#L408-L417); [T24](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/ChartPanel.tsx#L1327-L1382).

## F17 — Technical summary votes

**Formula/version.** Separate RSI14, Stoch14/3/3, CCI20, ADX14, AO, momentum10, price MACD12/26/9, StochRSI14/14/3/3, Williams14, Bull/Bear13, UO7/14/28; MA votes across EMA/SMA10/20/30/50/100/200,VWMA20,HMA9,Ichimoku. Mean oscillator votes and mean MA votes then equal group average. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Supplied bars; _tf argument ignored in aggregate helper. None.

**Causality and emission.** Trailing constituents conditional on complete input; score is a deterministic vote.

**Research status.** PRODUCT_HEURISTIC; uncalibrated and correlated inputs.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse constituent definitions and display vocabulary; no conversion of vote into entry probability or independent confirmations.

**Sources.** [T25](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/techRating.ts#L565-L634).

## F18 — Confirmed fractal pivots

**Formula/version.** findPivotsHL(left,right,wick/body); default wing fallback5, cap200; plateau tie keeps first; confirmedAt=i+right. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain. No calendar, session or arrival inputs.

**Causality and emission.** Geometric pivot at i becomes available at i+right close; future-confirmed geometry is legitimate only when confirmation time respected.

**Research status.** BUILT_NOT_PROVEN; strong reusable timing primitive.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Retain anchor and confirmedAt separately; do not emit at geometric pivot time.

**Sources.** [T33](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/pivots.ts#L1-L89); [T29](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicator-canvas/types.ts#L200-L213).

## F19 — BOS / CHoCH / CISD / swing geometry

**Formula/version.** Internal wing5, swing50 default; absorb confirmed pivots then close break only at j>confirmedAt. Break against chain trend=CHoCH, otherwise BOS; one fire/level. CISD failure window10. Alternating same-kind pivots can replace prior geometry with a more extreme pivot. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain. None; OHLCV delta labels are proxies.

**Causality and emission.** Break events can be causal at break close. Live zigzag/pending rays explicitly unconfirmed; final alternating geometry can change.

**Research status.** EVENT_CANDIDATE; drawings PRODUCT_ONLY.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse dated event tape after prefix audit, not reconstructed final zigzag or visual survivors.

**Sources.** [T34](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/marketStructure.ts#L105-L209); [T29](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicator-canvas/types.ts#L200-L213).

## F20 — Swing failure pattern

**Formula/version.** Default pivot wing20 (5–50), minVolumePct0, filter none; optional EMA20/50 alignment; sweep confirmed swing and close back same bar or next. Strength=.7*prior200 volume percentile+.3*(100 same-bar /60 next-bar); min10 samples else neutral. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain. None.

**Causality and emission.** event.i=confirmation bar; armed only j>pivot confirmedAt; later invalidation separate event. Default showInvalid=false hides failed historical visuals; event cap80.

**Research status.** EVENT_CANDIDATE; final rendering is survival-selected.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse formation/confirmation/invalidation events, not only final visible patterns or heuristic strength as probability.

**Sources.** [T35](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/sfp.ts#L221-L396).

## F21 — Order blocks: default volume / priceAction

**Formula/version.** Default volume: impulse range >=1.6*ATR14 plus prior200 volume percentile>=60. PriceAction variant internal pivot5 close-break. Anchor last opposing candle 1..5 before impulse; default full-range zone. Formation buy fraction from close location; grade averages volume, imbalance-share and impulse percentiles. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Current grain; optional macro4x is synthetic fixed-index grouping. No session reset.

**Causality and emission.** Default volume and priceAction conditions use then/current or confirmed prior data. Anchor is earlier geometry; creation belongs at impulse close. Lifecycle touch/break events and rendering caps are separate.

**Research status.** BUILT_NOT_PROVEN; default method candidate after prefix/closed-bar qualification.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Freeze method, mitigation mode (default close), zone/body basis and grade. Treat buy/sell as OHLCV proxies.

**Sources.** [T36](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/orderBlocks.ts#L159-L426).

## F22 — Order blocks: optional peak method

**Formula/version.** Requires candidate volume greater than volume[i-1] and volume[i+1] plus impulse conditions. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain, optional method only. None.

**Causality and emission.** STATIC_CODE_FINDING: reads i+1 at lines307–318 but ob_created has i and no confirmedAt at395–405. Earliest observation is i+1 close although stamp remains i.

**Research status.** NOT_ADMISSIBLE_AS_CURRENTLY_STAMPED for research.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Exclude peak variant until an owner-qualified event-time contract exists; no production repair commissioned. Default volume is not implicated by this specific lookahead.

**Sources.** [T36](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/orderBlocks.ts#L159-L426).

## F23 — Smart support/resistance

**Formula/version.** Confirmed pivot clusters within0.3*ATR14 of fixed first anchor; sensitivity wing5/8/12; score=touches*mean five-bar reaction ATR*0.5^(bars since last/250); track cap48. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain. None.

**Causality and emission.** Five-bar reaction sits within confirmation lag >=5, so known when published. Pivot conditioning already forces one adverse leg to zero: reaction score is not independent forward validation. Current role/visibility/rank changes.

**Research status.** GEOMETRY_CANDIDATE; heuristic score uncalibrated.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse point-in-time cluster state and age/touch features, not retrospective final ranking or score as hold probability.

**Sources.** [T37](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/smartSR.ts#L1-L160).

## F24 — Liquidity levels/grabs/bubbles

**Formula/version.** Equal confirmed pivots clustered by ATR tolerance; grab=wick penetration >= sensitivity*ATR followed by close reclaim; age heat and volume-percentile bubbles. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain. None.

**Causality and emission.** Events conditional on confirmation and closed input; evolving clusters and rendering caps need prefix qualification.

**Research status.** OHLCV_PROXY_ONLY; no measured book liquidity.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse named equal-high/low and sweep geometry; do not label displayed pools as observed resting orders.

**Sources.** [T38](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/liquidity.ts#L1-L140).

## F25 — Fair value gap

**Formula/version.** Bull L[j]>H[j-2]; bear H[j]<L[j-2]; region geometrically anchored j-1; later touch/fill/inversion lifecycle. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain. None.

**Causality and emission.** Gap first knowable at j close, despite geometric middle-bar anchor.

**Research status.** GEOMETRY_CANDIDATE; no execution-imbalance proof.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse event timing and gap distance/state; do not equate with actual L2 imbalance.

**Sources.** [T39](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/fvg.ts#L1-L135).

## F26 — Premium/discount, golden zone and OTE

**Formula/version.** Latest confirmed swing H/L pair; top/bottom30%, midpoint50%, golden.618–.65, OTE.786 of range. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain. None.

**Causality and emission.** Active from completing pivot confirmation; latest selected range can move with future pivots.

**Research status.** PRODUCT_RANGE_GEOMETRY.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Freeze range ID and availability; labels are geometric conventions, not fair-value or edge estimates.

**Sources.** [T40](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/premiumDiscount.ts#L1-L135).

## F27 — Automatic chart patterns

**Formula/version.** Least-squares trend lines from at least2 confirmed pivots; max residual0.4*ATR14; parallel slope tolerance15%; pattern-specific breakout/lifecycle. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain. None.

**Causality and emission.** Confirmed inputs help, but later fits can resegment drawings; full event-prefix audit not performed.

**Research status.** PRODUCT_ONLY until formation snapshots and causal event audit.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse bounded drawing primitives and pattern definitions for hypothesis registration; do not train on final fitted drawings.

**Sources.** [T41](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/autoPatterns.ts#L1-L165).

## F28 — Premium money-flow profile / POC events

**Formula/version.** Default final400 bars (100–1000),24 bins (10–40), volume spread uniformly by H–L overlap; doji whole V at C; buyShare close location; moneyFlow=bin midprice*V. POC default moneyFlow, optional delta/strength; VA70%. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain. No session reset.

**Causality and emission.** STATIC_CODE_FINDING: lines293–316 scan earlier closes against single final-window POC to emit historical mfp_poc_touch. POC can change after future bars or bin bounds change.

**Research status.** ENDPOINT_SNAPSHOT_ONLY; historical events not prefix-causal.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse source-qualified as-of profile snapshot; exclude historical POC event output from research without owner-qualified redesign.

**Sources.** [T42](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/moneyFlowProfile.ts#L116-L316).

## F29 — Trend Engine (autoOpt OFF)

**Formula/version.** Sensitivity s1–10 maps ATR period round(7+1.5s), multiplier1.2+.28s (default5=>15,2.6); HL2 +/- ATR ratchet and close flip. ROC10 percentile200>=70 strong tier; RSI14 recovery through25/75 within10 gives power. Dynamic TP1.5/2.5/3.5/5/6.5/8 ATR at flip; selectable stop display. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain. No session reset.

**Causality and emission.** Fixed sensitivity state machine can be causal at closed-bar flip; stops/targets are deterministic geometry, not validated policy.

**Research status.** BUILT_NOT_PROVEN; candidate fixed-parameter features.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Freeze sensitivity and producer parameters, qualify dated flip/state; do not inherit TP/SL as successful exit rule.

**Sources.** [T43](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/trend/trendEngine.ts#L1-L305).

## F30 — Trend Engine optional autoOpt

**Formula/version.** Default OFF. Test all10 sensitivity settings on final2000 bars; score=flip-to-flip net-percent plus0.5*winrate-percent; choose max then redraw entire supplied history. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain. None.

**Causality and emission.** Explicit documented repaint: final-sample selected parameter applied to past. In-sample optimizer also creates model-selection multiplicity.

**Research status.** PRODUCT_OPTIMIZER; not historical research column.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Exclude in-sample redraw. A separately preregistered nested chronological selection protocol would be a different experiment.

**Sources.** [T43](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/trend/trendEngine.ts#L1-L305).

## F31 — FlowBand / Voltix / candle painter

**Formula/version.** FlowBand HMA=WMA(2*WMA(C,n/2)-WMA(C,n),sqrt(n)) +/- ATR14 multiple; slope hysteresis0.1ATR. Voltix centerEMA(HL2,n), halfwidth=max(mult*ATR(n),prevHalf*.97). Candle painter EMA20/50 or RSI14 thresholds60/40 and volume percentile100. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain; FlowBand2x/4x groups synthetic. None.

**Causality and emission.** Trailing fixed formulas; retest scores heuristic and visuals revised with current inputs.

**Research status.** BUILT_NOT_PROVEN, painter PRODUCT_ONLY.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse named arithmetic/features; declare synthetic aggregation alignment.

**Sources.** [T44](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/trend/flowBand.ts#L1-L125); [T45](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/trend/voltixBands.ts#L1-L140); [T46](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/trend/marketDashboard.ts#L1-L170).

## F32 — Market dashboard

**Formula/version.** ATR14/C percentile252; BB20/2 compression inverted0–10; TrendScore5*TrendEngine +3*EMA20/50 +2*C/EMA200; 20-bar volume close-location pressure percentile252 =>(p-50)/5; rating votes. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Current chart bars. None.

**Causality and emission.** Trailing; copied sensitivity map ignores autoOpt; dashboard is not independent evidence from underlying suites.

**Research status.** PRODUCT_HEURISTIC.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse source labels/condition explanation; avoid stacking correlated votes as independent confirmations.

**Sources.** [T46](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/trend/marketDashboard.ts#L1-L170).

## F33 — RSIX RSI producer/channels

**Formula/version.** Wilder RSI14 close default; suite flat gains=losses=0 yields50; EMA14 smoothing; OB65/OS35/mid50. Channels in RSI space: BB SMA/popSD, Keltner EMA+RMA(abs delta RSI), Donchian extrema. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain. None.

**Causality and emission.** Trailing producer; channel warmup and source mapping must be fixed.

**Research status.** BUILT_NOT_PROVEN.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse separate rsix_rsi14 identity, not classic RSI flat semantics; freeze settings from producer.

**Sources.** [T31](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/shared/oscUtils.ts#L55-L287); [T47](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/rsix/rsiEngine.ts#L1-L170); [T52](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/rsix/rsiChannels.ts#L1-L180).

## F34 — MACDX producer

**Formula/version.** Default raw=EMA(price,10)-EMA(price,20); normalizeSigned by trailing max(abs(raw),250)*100; signal defaultEMA9 on NORMALIZED line; hist=line-signal. Selectable MA/source. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain. None.

**Causality and emission.** Trailing normalization; scale changes reflect rolling extrema, and missing may be neutralized to0 by helper.

**Research status.** BUILT_NOT_PROVEN.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Freeze normalization/source/MA/window; differs from standard12/26/9 and classic MACD-RSI.

**Sources.** [T31](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/shared/oscUtils.ts#L55-L287); [T48](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/macdx/macdEngine.ts#L1-L180).

## F35 — Pulse wave

**Formula/version.** EMA(EMA(delta C,long25),short13), normalized by trailing max abs200; default signal9, companionEMA18; extreme thresholds +/-60. Scalper15/7/6; swing40/21/13. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain. None.

**Causality and emission.** Trailing normalization conditional on completed inputs.

**Research status.** BUILT_NOT_PROVEN.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse explicit preset and normalization; no generic momentum interchangeability.

**Sources.** [T49](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/pulse/pulseWave.ts#L1-L160).

## F36 — Pulse MFI / CVD / volume mapping

**Formula/version.** MFI14 typical-price*V positive/negative flow =>2*MFI-100. CVD sums close-location volume imbalance, demeans200, max-abs normalizes200; no day reset. Volume mapping V/trailingmax window height; buyFrac>.58/<.42 color, five-bar weighted buy-share .55/.45 hysteresis. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** OHLCV bars. Pulse CVD differs from intraday day-reset CVD; no economic session.

**Causality and emission.** Trailing approximations with then-known bars; neither is actual aggressor flow or bid/ask depth.

**Research status.** PROXY_ONLY; BUILT_NOT_PROVEN.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse under unambiguous OHLCV names; do not pool daily-reset and cumulative variants.

**Sources.** [T50](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/pulse/flows.ts#L1-L180); [T51](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/pulse/volumeMapping.ts#L1-L130).

## F37 — RSIX/MACDX/Pulse divergence

**Formula/version.** Shared consecutive oscillator pivots, not price pivots; compares price H/L at those pivot indices, regular/hidden strict inequalities; default wing5,maxspan60; confirmedAt=second pivot+wing. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Any SuiteBar grain. None.

**Causality and emission.** Geometric event back-anchored but confirmedAt future wing; NaN neighbor invalidates; lookback/render caps can prune.

**Research status.** EVENT_CANDIDATE.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse confirmed event tape after complete-bar gate; never use future-confirmed mark at pivot bar.

**Sources.** [T32](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/shared/divergence.ts#L1-L98); [T29](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicator-canvas/types.ts#L200-L213).

## F38 — Suite multi-timeframe dashboards

**Formula/version.** Chart,2x,4x from sequential index0 OHLCV groups; complete groups only, projected at group end; underlying settings from shared producer. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Multiples of input bar COUNT; not independent exchange-aligned2h/4h feeds. No economic-session alignment; input truncation shifts index0 grouping.

**Causality and emission.** Closed groups prevent some future leakage but endpoint/live-bar and alignment rules vary by consumer.

**Research status.** PRODUCT_CONTEXT; research only after canonical aggregation contract.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Reuse visual table and producer ownership. Derive higher grains with incumbent event-time/session owner, not a second implicit clock.

**Sources.** [T53](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/rsix/mtfDash.ts#L1-L140); [T27](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/compute.ts#L1-L113).

## F39 — Relative performance / strength views

**Formula/version.** Heatmap RS=tile one-day change minus current universe average change. Sector rotation consumes21/63-session percent change in sector/SPY ratio and sign quadrants. Structure Relative Strength label is a pivot-delta percentile. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Heatmap1d cross-section; sector21/63daily; pivot bar-grain. No shared 24H normalization in inspected consumers.

**Causality and emission.** PIT membership, benchmark freshness and common cutoffs not proven in these displays.

**Research status.** PRODUCT_CONTEXT; separate candidate definitions.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN: no conditional incremental OOS evidence located in inspected primitive/source.

**Concrete reuse.** Keep all three meanings distinct; research market/sector/beta residuals need own then-known benchmark and membership qualification.

**Sources.** [T68](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/heatmap/HeatmapTable.tsx#L222-L236); [T69](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/sector-intelligence/SectorRotationMap.tsx#L76-L120); [T34](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/marketStructure.ts#L105-L209).

## F40 — Options levels (walls/flip/abs gamma/EM)

**Formula/version.** Consumes options_hub.gex/v1, moves/v1, and options_structure.gex_state/v1 fallback. Flip nearest repricing crossing within30% spot else scalar; absolute-gamma strike=max abs ladder; expected move edges upstream. Signed walls/flip labeled TierB; abs-gamma/EM TierA arithmetic. Version `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Grain/session.** Dated upstream option snapshots projected on any chart. ET source dates; sessionsOldEt uses weekdays proxy, not holiday calendar.

**Causality and emission.** Root validated, oldest contributing asof used; missing date remains unknown. Inspected chart fetch uses current SWR root sources; draw function has no local replay-asof guard. Historical joined overlay correctness UNKNOWN.

**Research status.** PRODUCT_OVERLAY; snapshot lineage reusable; incremental edge UNKNOWN.

**Historical support.** INPUT_DEPENDENT: no primitive-specific qualified archive established. Inherited Oct 2 census: 680 five-minute / 4,108 hourly files; uneven coverage, no available_at history or PIT membership. 1m durable publication UNKNOWN; 20:00–04:00 candles absent from inspected route; seconds short-window only. T01–T07.

**Incremental evidence.** UNKNOWN incremental OOS value. Inherited code comment reports call-wall hold49% [47.1,50.9], n=2599; underlying measurement artifact not independently reopened here, so this is inherited adverse context, not a new verified result.

**Concrete reuse.** Reuse owner data/qualification/UI. Do not treat gamma walls as hold probabilities; separately qualify as-of replay overlay visibility.

**Sources.** [T54](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/optionsLevels.ts#L1-L252); [T55](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/ChartPanel.tsx#L1933-L1964); [T56](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/ChartPanel.tsx#L9186-L9267).

## Exact Txx source register

The Txx identifiers below are unchanged. All source anchors address Terminal protected-master pin `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`; a static implementation fact is not current runtime or entitlement proof. Full-file SHA256 values are in the JSON appendix; excerpt-only full-file hashes remain null.

| ID | Exact pinned source | Role |
|---|---|---|
| T01 | [terminal/lib/intradayShared.ts:117-136](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayShared.ts#L117-L136) | US extended filter and calendar-derived regular filter |
| T02 | [terminal/lib/intradaySources.ts:111-270](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradaySources.ts#L111-L270) | Polygon minute/second acquisition and display epoch conversion |
| T03 | [terminal/lib/intradayStore.ts:1-87](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayStore.ts#L1-L87) | 1h/5m store reuse, resampling and return cap |
| T04 | [terminal/app/api/intraday/route.ts:33-190](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/app/api/intraday/route.ts#L33-L190) | Cache, permission gate and second-band isolation |
| T05 | [terminal/lib/intradayEvidence.ts:1-84](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayEvidence.ts#L1-L84) | Descriptive assembly evidence is not research admission |
| T06 | [ingest/intraday_qualification.py:90-251](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/ingest/intraday_qualification.py#L90-L251) | Canonical observation and cutoff/session qualification |
| T07 | [docs/research/INTRADAY_DISLOCATION_R0_DATA_CENSUS_2026-10-02.md:1-117](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/docs/research/INTRADAY_DISLOCATION_R0_DATA_CENSUS_2026-10-02.md#L1-L117) | Inherited Oct 2 physical-store census; no new physical audit |
| T08 | [terminal/lib/usEquitySessionClock.ts:1-54](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/usEquitySessionClock.ts#L1-L54) | Macro-derived calendar projection validation |
| T09 | [hub/lib/extfeed.js:735-985](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/hub/lib/extfeed.js#L735-L985) | Extended snapshot validation, overnight basis and fallback policy |
| T10 | [hub/lib/extfeed.js:242-413](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/hub/lib/extfeed.js#L242-L413) | Alpaca overnight stream: trade messages, not quote book |
| T11 | [terminal/app/api/ext-quote/route.ts:1-94](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/app/api/ext-quote/route.ts#L1-L94) | Hub-only extended quote route |
| T12 | [terminal/app/api/quote/route.ts:1-177](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/app/api/quote/route.ts#L1-L177) | Regular quote lane, batching and visible-chart cadence |
| T13 | [docs/DATABENTO_INTEGRATION_DESIGN.md:1-170](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/docs/DATABENTO_INTEGRATION_DESIGN.md#L1-L170) | UTC and provider adapter design; specification status |
| T14 | [terminal/lib/intradayMath.ts:1-173](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayMath.ts#L1-L173) | Time assumptions and shared intraday helpers |
| T15 | [terminal/lib/intradayMath.ts:175-401](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayMath.ts#L175-L401) | Session VWAP, opening range and RVOL |
| T16 | [terminal/lib/intradayMath.ts:408-641](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayMath.ts#L408-L641) | TTM, ADX and OHLCV CVD approximation |
| T17 | [terminal/lib/intradayMath.ts:654-793](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayMath.ts#L654-L793) | Prior-period pivot/session levels |
| T18 | [terminal/components/DayStatsStrip.tsx:1-112](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/DayStatsStrip.tsx#L1-L112) | Day statistics and session badge |
| T19 | [terminal/lib/indicatorMath.ts:1-105](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicatorMath.ts#L1-L105) | Moving-average, ATR and percentile semantics |
| T20 | [terminal/lib/indicatorMath.ts:264-469](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicatorMath.ts#L264-L469) | AVWAP, rolling/week VWAP and two POC implementations |
| T21 | [terminal/lib/indicatorMath.ts:487-697](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicatorMath.ts#L487-L697) | Volbox, RSI stack, accumulation, BB and ribbon |
| T22 | [terminal/lib/indicators.ts:157-244](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicators.ts#L157-L244) | Classic registry deliberately names price stochastic Stochastic RSI |
| T23 | [terminal/components/ChartPanel.tsx:408-417](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/ChartPanel.tsx#L408-L417) | Classic chart actual RSI/stochastic/RSI-MACD math; local excerpts |
| T24 | [terminal/components/ChartPanel.tsx:1327-1382](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/ChartPanel.tsx#L1327-L1382) | Classic pane build functions; local excerpts |
| T25 | [terminal/lib/techRating.ts:565-634](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/techRating.ts#L565-L634) | Separate conventional technical summary formulas and votes |
| T26 | [terminal/lib/suites/registry.ts:1-48](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/registry.ts#L1-L48) | Suite metadata façade |
| T27 | [terminal/lib/suites/compute.ts:1-113](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/compute.ts#L1-L113) | Lazy runtimes and shared producer parameter ownership |
| T28 | [terminal/lib/indicator-canvas/types.ts:25-54](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicator-canvas/types.ts#L25-L54) | Input context lacks bar-closed, source, arrival and revision fields |
| T29 | [terminal/lib/indicator-canvas/types.ts:200-213](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicator-canvas/types.ts#L200-L213) | SuiteEvent geometry index and confirmation index contract |
| T30 | [terminal/lib/indicator-canvas/host.ts:299-373](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/indicator-canvas/host.ts#L299-L373) | Compute input and render budgeting; caller owns bar admissibility |
| T31 | [terminal/lib/suites/shared/oscUtils.ts:55-287](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/shared/oscUtils.ts#L55-L287) | Suite RMA/EMA/RSI and percentile/normalization semantics |
| T32 | [terminal/lib/suites/shared/divergence.ts:1-98](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/shared/divergence.ts#L1-L98) | Confirmed oscillator pivot divergence |
| T33 | [terminal/lib/suites/structure/pivots.ts:1-89](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/pivots.ts#L1-L89) | Confirmed fractal pivots and plateau rules |
| T34 | [terminal/lib/suites/structure/marketStructure.ts:105-209](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/marketStructure.ts#L105-L209) | BOS/CHoCH chain and pivot geometry |
| T35 | [terminal/lib/suites/structure/sfp.ts:221-396](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/sfp.ts#L221-L396) | SFP defaults, formation, confirmation, invalidation and rendering |
| T36 | [terminal/lib/suites/structure/orderBlocks.ts:159-426](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/orderBlocks.ts#L159-L426) | OB methods, optional peak lookahead, event stamps and grade |
| T37 | [terminal/lib/suites/structure/smartSR.ts:1-160](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/smartSR.ts#L1-L160) | Confirmed pivot clustering, reaction score and recency |
| T38 | [terminal/lib/suites/structure/liquidity.ts:1-140](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/liquidity.ts#L1-L140) | Liquidity geometry is a price/volume approximation |
| T39 | [terminal/lib/suites/structure/fvg.ts:1-135](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/fvg.ts#L1-L135) | Three-bar gap geometry and forward lifecycle |
| T40 | [terminal/lib/suites/structure/premiumDiscount.ts:1-135](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/premiumDiscount.ts#L1-L135) | Latest confirmed range segmentation |
| T41 | [terminal/lib/suites/structure/autoPatterns.ts:1-165](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/autoPatterns.ts#L1-L165) | Confirmed pivot line fitting and pattern constraints |
| T42 | [terminal/lib/suites/structure/moneyFlowProfile.ts:116-316](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/structure/moneyFlowProfile.ts#L116-L316) | Final-window bin profile and retrospective POC event scan |
| T43 | [terminal/lib/suites/trend/trendEngine.ts:1-305](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/trend/trendEngine.ts#L1-L305) | Trend formulas, parameter map and optional in-sample autoOpt |
| T44 | [terminal/lib/suites/trend/flowBand.ts:1-125](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/trend/flowBand.ts#L1-L125) | HMA channel and fixed-index higher-grain groups |
| T45 | [terminal/lib/suites/trend/voltixBands.ts:1-140](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/trend/voltixBands.ts#L1-L140) | EMA/ATR band and decaying width floor |
| T46 | [terminal/lib/suites/trend/marketDashboard.ts:1-170](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/trend/marketDashboard.ts#L1-L170) | Heuristic condition dashboard |
| T47 | [terminal/lib/suites/rsix/rsiEngine.ts:1-170](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/rsix/rsiEngine.ts#L1-L170) | Premium RSI producer |
| T48 | [terminal/lib/suites/macdx/macdEngine.ts:1-180](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/macdx/macdEngine.ts#L1-L180) | Premium normalized MACD producer |
| T49 | [terminal/lib/suites/pulse/pulseWave.ts:1-160](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/pulse/pulseWave.ts#L1-L160) | Double-smoothed price-change wave |
| T50 | [terminal/lib/suites/pulse/flows.ts:1-180](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/pulse/flows.ts#L1-L180) | MFI and normalized cumulative OHLCV imbalance |
| T51 | [terminal/lib/suites/pulse/volumeMapping.ts:1-130](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/pulse/volumeMapping.ts#L1-L130) | Volume-height and buy-share heuristic |
| T52 | [terminal/lib/suites/rsix/rsiChannels.ts:1-180](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/rsix/rsiChannels.ts#L1-L180) | RSI-space BB, KC and Donchian channel |
| T53 | [terminal/lib/suites/rsix/mtfDash.ts:1-140](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suites/rsix/mtfDash.ts#L1-L140) | Synthetic 2x/4x bar grouping rather than independent feed |
| T54 | [terminal/lib/optionsLevels.ts:1-252](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/optionsLevels.ts#L1-L252) | Options source qualification, formulas and oldest contributing date |
| T55 | [terminal/components/ChartPanel.tsx:1933-1964](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/ChartPanel.tsx#L1933-L1964) | Options level drawing has symbol/readiness checks; no local as-of check |
| T56 | [terminal/components/ChartPanel.tsx:9186-9267](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/ChartPanel.tsx#L9186-L9267) | Episode and current options-source consumption effects |
| T57 | [terminal/lib/replayEngine.ts:1-230](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/replayEngine.ts#L1-L230) | Options snapshot replay reducer |
| T58 | [terminal/lib/suiteAlerts.ts:156-325](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/suiteAlerts.ts#L156-L325) | Confirmation timing, alert freshness and watermark behavior |
| T59 | [terminal/lib/dislocations/source.ts:1-255](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/dislocations/source.ts#L1-L255) | Macro-owned Radar consumer and availability/freshness |
| T60 | [terminal/components/dislocations/DislocationsView.tsx:1-180](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/dislocations/DislocationsView.tsx#L1-L180) | Existing market/watchlist states and stale/unavailable UI |
| T61 | [terminal/lib/dislocations/episodeMarks.ts:1-180](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/dislocations/episodeMarks.ts#L1-L180) | Episode identity and event-time mark projection |
| T62 | [terminal/lib/precisionEntry.ts:1-160](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/precisionEntry.ts#L1-L160) | Existing temporal roles and preset intent |
| T63 | [terminal/components/workspaces/DiscoverWorkspace.tsx:1-91](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/workspaces/DiscoverWorkspace.tsx#L1-L91) | Existing discovery workspace |
| T64 | [terminal/lib/analysisRoute.ts:1-87](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/analysisRoute.ts#L1-L87) | Company/research/thesis route ownership |
| T65 | [terminal/lib/companyIntelligence.ts:1-180](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/companyIntelligence.ts#L1-L180) | Canonical company intelligence reader |
| T66 | [terminal/lib/washoutTurn.ts:1-119](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/washoutTurn.ts#L1-L119) | Existing Macro consumer; weekly context not a new daily engine |
| T67 | [terminal/lib/sessionBars.ts:1-165](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/sessionBars.ts#L1-L165) | Close-time versus display-time and anchored grouping |
| T68 | [terminal/components/heatmap/HeatmapTable.tsx:222-236](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/heatmap/HeatmapTable.tsx#L222-L236) | Relative performance versus current universe mean; excerpts |
| T69 | [terminal/components/sector-intelligence/SectorRotationMap.tsx:76-120](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/sector-intelligence/SectorRotationMap.tsx#L76-L120) | Sector/SPY ratios 21/63 sessions; excerpts |
