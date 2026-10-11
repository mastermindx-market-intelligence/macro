# Nested defensive washouts V5 — causal-clock and execution audit

## Current mission and result boundary

Current user instruction: resume heavy research on the W/2W StochRSI washout followed by shorter RSI-MACD recovery. The V4 correction remains controlling: price-MACD and standalone RSI(2) results do not test this sequence. This is research, not trade authorization, live allocation, deployed code or an alpha claim.

Protected Mastermind source was reverified unchanged at `326c8469a21d7f50fc9ecb1848196bf1c6e66685`, compatible skillpack1.0.1/bootstrap1. Research branch predecessor was verified at `bcd05af9779634c9b8071c02181e9be4b008ec58`. Source correction reference remains macro `9bcdbb4d887f1e2a082e1743cb84af6261fb25b4` canon RSI14 -> EMA14-EMA60 -> EMA5.

The V3 result-table read and V4 compound remote workspace/earlier-price acquisition remain denied. No retry, equivalent export, replacement acquisition, recomputation or alternate-carrier attempt occurred. Existing uploaded local artifacts contain reference source and derived reports, not the native equity histories for this corrected strategy. No new actual-stock result has been produced. Current direct work is independently permitted local source/math/synthetic research (PRINCIPAL_JUDGMENT); no child was dispatched.

## Material progress

1. A committed-state native RSI-MACD/StochRSI engine now produces both completed-bar and daily-close developing W/2W snapshots. Developing snapshots replace only the current native close, starting each time from the last committed native state. They do not append each intermediate day as a new week, and do not backfill a future completed value. Native closed outputs match the delivered V4 batch reference on synthetic nondegenerate inputs. Explicit RSI edge conventions are retained; exact user-chart parity remains unknown.
2. An exact conditional next-native-close crossover threshold was derived and implemented. Let af=2/15 and al=2/61, F/L be prior EMA14/EMA60 of RSI14, and S be prior EMA5 signal. Required current RSI is `(S-(1-af)F+(1-al)L)/(af-al)`. Current MACD exceeds its updated signal exactly when current MACD exceeds prior S. With previous Wilder average gain/loss, the RSI requirement is inverted to a price boundary. This is an algebraic observation threshold, not a price forecast, target, executable fill or profitability result. A prior nonpositive histogram is separately required for a fresh native crossover. Flat/saturated cases are explicitly classified rather than given fabricated roots.
3. An offline single-position policy replay now models following-open entries/exits, known initial stops, entry-day/gap stop-outs, trailing updates after the current session's stop check, lower/weekly/slow-cycle exit clocks, one versus at most two attempts per fixed episode, reset/cooldown requirements, and open/pending end-of-sample states. Failed first attempts remain in the account. Annual liquidation is not automatic. No broker, network, dividend ledger, cash yield or portfolio allocation is present.

## Verified milestone

42 local tests passed in one full run: 20 native-clock/boundary tests and 22 execution-policy tests. They cover native/batch formula identity, immutable previews, native-clock prefix invariance, calendar coverage/phase, future perturbations, numeric boundary inversion, stop chronology, costs, pending orders and bounded retries. These prove only their observed mechanics.

Current source hashes:
- clock_engine.py: `77b66fdab95c3c4239d98332b55407b0ae8517df61bf77bb350679ef566bce95`
- policy_engine.py: `1f6b378142919f32f26c4eebaa961a598790e9db9e3082fee154faa4249eeebe`
- unchanged V4 reference: `25e0e91dc69e91e870f49e44ec05dcbdf636b79eaca3737fc58e2f4ec2895fd9`

## Next phase in this turn

Create nontrivial causal counterexamples for disappearing developing-bar crosses and stochastic-window normalization; connect fixed master episodes to the new policy replay; test same-opportunity comparison and chart-export parity checks; deliver a documented offline research package. No synthetic performance may be reported as equity evidence. Later empirical work remains gated on legitimately permitted native-price inputs and verified chart/session semantics; the user has not supplied exact dated defensive trade examples or a developing-versus-confirmed convention.

This is a verified save, not a completion claim or autonomous execution. No uncertain effect, active worker or background process remains. Continue the safe independent local phase now.

## Primary explanatory sources

TradingView Pine Execution Model: https://www.tradingview.com/pine-script-docs/language/execution-model/
TradingView Other Timeframes and Data: https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/
TradingView Stochastic RSI: https://www.tradingview.com/support/solutions/43000502333-stochastic-rsi-stoch-rsi/
TradingView Strategies: https://www.tradingview.com/pine-script-docs/concepts/strategies/
