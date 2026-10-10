# Defensive nested washouts V4 — correction and verified frontier

Date: October 10, 2026. Research only. **Source audit complete; offline reference mechanics tested; new market-performance experiment NOT EXECUTED.** No order, allocation, production change, child, watcher or autonomous retry.

## Current assignment and interpretation

The Chairman asks to test extreme long-timeframe washouts, weekly and two-week StochRSI bottoms, and shorter-timeframe MACD-RSI bullish crossovers. That is a sequential, conditional setup. It is not a standalone daily price-MACD crossover, weekly oscillator, or daily RSI(2) dip strategy.

## Material correction to the previous studies

The already-delivered V2 archive was inspected locally. Its `source/deep_engine.py` defines price-MACD variants using `c = f.close` and EMA sets 8/17/5, 12/26/9 and 16/35/9. Its timeframe list is exactly 1D/2D/3D/1W. The registry has 288 signal specifications and three exits across 18 stocks: 15,552 stock-policy trials, **zero with a 2W timeframe and zero with joint W+2W washout followed by lower RSI-MACD confirmation**. A daily stock-trend gate does not supply that missing higher-timeframe context.

Earlier V1 work did include standalone 2W StochRSI ladder observations. It is incorrect to say no 2W study ever occurred. Those separate observations still do not test the requested sequence. PG's phase-sensitive V2 winner used RSI(2), not the requested nested RSI-MACD setup.

Therefore withdraw the implication that the earlier experiments establish the user's approach is ineffective, that weekly/two-week confluence cannot improve entries, or that their stock ranking is the best ranking for this method. The prior numerical results continue to describe their actual proxy rules; they cannot be transferred to a different indicator, context, trigger and exit policy.

Daily pivot RSI near 44–45 is not a rebuttal of a StochRSI washout. An RSI of 45 at the minimum of a 45–65 lookback range gives raw StochRSI zero. The indicators encode different properties. Correlated oscillators also need not be useless together: conditional incremental information must be tested rather than assumed, without multiplying dependent signals as independent probabilities.

## Exact indicator identity

Live connected reads of `engine/canon.py` at macro `9bcdbb4d887f1e2a082e1743cb84af6261fb25b4`, lines 311–365 and 417–445, establish:

- native RSI(14), SMA-seeded Wilder smoothing;
- MACD-RSI = EMA14(RSI14) minus EMA60(RSI14);
- signal = EMA5(MACD-RSI);
- StochRSI = 14-period stochastic normalization of native RSI14, then SMA3 K and SMA3 D;
- closed-bar bullish crossover = current line above signal after prior line at/below signal.

Other similarly named helpers have different defaults. A function name is not an adequate parameter contract. No production source was modified. The local reference explicitly treats one-way RSI paths as 100/0 and fully flat paths as 50; canon's zero-loss-denominator handling can instead produce NaN. This disclosed edge difference means no universal byte/golden-vector or exact chart parity claim.

## Corrected working experiment

Primary causal model: **long washout arms an episode; first shorter recovery triggers a candidate; follow-through or failure determines subsequent management.** Do not require all timeframes to cross on the same candle, and do not retrospectively choose only the last successful lower cross.

Working, unoptimized reference settings:

1. Weekly K reached 20 or lower within three completed W bars; 2W K reached 20 or lower within two completed 2W bars. Require 200 completed native bars before arming and current 2W K below60. Calendar weeks, not an automatic ten-session substitute.
2. First completed 1D or 2D RSI-MACD bullish cross within42 decision sessions. Compare 3D/W as slower controls. Entry is next open; missing next-open data remains pending.
3. Separately evaluate recent daily StochRSI washout and deeper slow-MACD exhaustion. The latter uses negative 2W RSI-MACD below its own earlier20th percentile over104 preceding native bars; no full-sample percentile.
4. One initial candidate per episode. Preserve untriggered episodes. A reset/expiry and explicit clearing interval define rearming; follow-on reloads are a different strategy.

The episode reference implements initial arming, one first confirmation, expiry, pending entry and paired fixed-endpoint accounting. Full dynamic exit, add/reload, calibrated regime classification and broker simulation remain unimplemented/unvalidated; no full strategy-completion claim.

Compare lower crosses alone, weekly-only context, 2W-only context, joint context, joint-plus-short-washout, and independently slow-stabilization/deeper-washout additions. Also compare immediate entry at the same washout arm with delayed 1D/2D/3D/W confirmation. Count missed winners and avoided losses; do not discard episodes lacking confirmation. Common arm-anchored endpoints and entry-anchored horizons answer different questions.

Long-cycle outcome studies should include63/126/252-session horizons and distinct fast/intermediate/slow-cycle exit candidates, not rely only on the former20-session policy. Initial risk, gaps and reentries must be evaluated with the exit policy. No forced annual liquidation in the primary long-cycle experiment merely for convenience. No hardwired above200SMA gate that silently excludes the deep-reset population; label intact-trend and broken-trend episodes separately.

Test both2W calendar phases and all2D/3D session phases, source-price conventions, warm-up sensitivity and availability timestamps. Future completed higher-timeframe values must not be placed at the start of the period. Recent history has already been seen; any corrected retrospective results remain exploratory rather than fresh blind evidence. Cluster inference by time and common market washout, not by correlated stock rows alone.

## Regime linkage

Keep the prior issuer/rates/credit hypotheses as contextual labels and possible failure explanations, not validated V4 filters. A negative slow oscillator is not automatically a veto. Improvements in the rate of deterioration may be more relevant than requiring every operating/technical level to be positive. Source-known issuer impairment, required-return pressure and broad funding stress must remain distinct. Do not generate a regime after seeing losses to justify excluding them.

No new stock ranking, correlation coefficient, entry accuracy, payoff or allocation is reported. The proper empirical next deliverable is a per-stock episode ledger for the corrected indicator and sequence, including failed/late/missed candidates.

## Verified work and current access boundary

33 local synthetic/mechanical tests passed. Coverage includes RSI-MACD formula and scale invariance, StochRSI formula, native-vs-downsampled RSI, partial W/2W bars, immutable session/calendar phases, missing data, prefix invariance, nontrivial synthetic end-to-end episodes, first confirmation only, expiry, pending next-open fills, missed opportunities and incomplete horizons. Native first computable signal occurs at bar78 on a nondegenerate test series; K at30 and D at32. These are mechanics, **not real-stock performance tests**.

Local deliverable root: `/mnt/data/defensive_nested_v4`; report `RESEARCH_CORRECTION.md`, offline `source/nested_washout.py`, tests, source-audit CSV and integrity records. No market-data downloader or broker code. The local reference file SHA256 is `25e0e91dc69e91e870f49e44ec05dcbdf636b79eaca3737fc58e2f4ec2895fd9`; tests SHA256 `34fff11c98295700fc631d6829d031813eb1413665637b9a00a2584daffc6d7b`.

A new Studio Direct workspace/earlier-price acquisition call was blocked by OpenAI before execution. EFFECT_NONE for that action. It was not retried, rephrased, rerouted or reconstructed through another carrier. The earlier V3 denied result outputs were not read or recomputed. Permitted independent work used delivered local source, repository definitions and synthetic inputs.

**Unfinished obligation / next action:** only with legitimately permitted price-data analysis access, execute the frozen nested episode comparisons and audit each actual-stock result before giving any performance conclusion. No access override, alternate-carrier permission or autonomous retry is implied. The source correction and local reference are delivered; empirical validation is incomplete because that lane is blocked, not because the hypothesis was rejected.

Protected procedure remained `326c8469a21d7f50fc9ecb1848196bf1c6e66685`, compatible skillpack1.0.1/bootstrap1; ACTIVE_EXECUTION/SESSION_RELIABILITY retained. Previous research branch head was verified at `25e42ac11788df07d180be761a02208cdc053e53`. Direct source adjudication and method repair retained as PRINCIPAL_JUDGMENT; no incumbent writer displaced. Preserve this correction and no-retry fence across continuation.

Primary explanatory sources: TradingView Stochastic RSI support; TradingView Pine Other Timeframes and Data / Repainting docs; exact connected repository indicator source. Those definitions do not independently prove profitable signals.
