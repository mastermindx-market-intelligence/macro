# Uploaded indicator binding: three formulas, not three independent votes

Parent: WS:RATES-INFLATION-COMMAND / PR 7909.
Operation: rates-direction-20260924-sol-001; same original Studio records carrier.
Authority: Chairman requested testing both uploaded indicator families on September 24.
Procedure: Mastermind 2a7681601a419532a47f0d24029b55b37bfe2b5c; Skillpack 1.0.1/bootstrap1.
Direct reason: PRINCIPAL_JUDGMENT for formula/experiment identity; LOWER_TOTAL_OVERHEAD for synthetic probes.

## Source binding

The raw uploads remain unmodified in the conversation. This record publishes hashes and
formula descriptions, not raw third-party source or a new production indicator owner.

| Upload | Raw bytes | SHA256 |
|---|---:|---|
| macd-rsi.rtf | 54434 | 485ab6ebd54a2b8a30e2e73196d8d6338d09b51d53387139fa8fa39896aa1994 |
| stoch-rsi 1.rtf | 32026 | 6e0527482794e81800c6247142c46cf84b13a59dcf2298a86fcfd9a41b74f1ad |
| stoch rsi 2.rtf | 3099 | 26b8e029bd9b4d8345b9f69580a2e5f8efd562ac7aa6ac442f22896bb935d0d7 |

unrtf --text extraction, removing conversion preamble and normalizing trailing newline,
produced identical 213-line source text for the first two files. Extracted-text SHA256:
2feb43b778e09f102f187a4c12346be8875f867fe534a5a06f9fd3cb1bc3499b.
Both contain TH_RSIMACD+ plus an interleaved CM_Stochastic_MTF study declaration;
MACD histogram alerts resume after that second block. Treat them as mixed source material,
not one verified compilable Pine script. No TradingView compilation was performed.

M: TH_RSIMACD+ / user's MACD-RSI. RSI(close,14), then EMA14(RSI)-EMA60(RSI),
EMA5 signal, histogram=line-signal. Both SMA toggles default false. Header calls this
an independent public-description recreation; original protected-script parity is unproven.
P: CM_Stochastic_MTF. SMA3 of the 14-bar close position within HIGH/LOW range;
D=SMA3(K). This is price stochastic, not stochastic of RSI. 80/20 bands; current
chart timeframe defaults on; optional second timeframe plot defaults off.
R: Stochastic RSI v6. RSI(close,14), 14-bar stochastic of RSI, SMA3 K and SMA3 D.
The supplied R script plots lines/bands only; it defines no native buy/sell trigger.

## Trigger identity that the experiment must preserve

M line/signal crosses and histogram-zero crosses are mathematically the same event,
not two independent confirmations. M line crossing its own zero baseline is different.
P's any-cross rule requires STRICT previous K<D (or K>D), unlike equality-inclusive
crossover/crossunder. Its filtered rule tests PREVIOUS K<20 (or K>80), not current K.
R crossover/zone/curl triggers are proposed research rules, not claimed source alerts.
M and R both start with RSI14(close); agreement is dependent information, not independent votes.

## Executed source tests and their ceiling

A separate sandbox research reference passed 14 synthetic unit tests: duplicate event
identity, baseline distinction, high/low sensitivity, strict-equality differences,
previous-bar zone semantics, future-mutation/prefix invariance, SMA variants, missing/
invalid OHLC, zero ranges, and first-passage up/down/both/neither/censored behavior.
The 1200 generated two-hour labels are synthetic, not Treasury market observations.
No market outcomes were read, no empirical configurations evaluated, no win rate claimed.
Reference SHA256: 4122df2907292172cdc38b9d917089a810dfdbb07a6fef51e0610beb59d291d5.
The attached conversation package retains that reference, its tests, source extracts,
and receipt. Native Pine compilation/golden-vector parity is NOT established.

The smaller reproducible source recipe in uploaded_formula_probe.py checks the eleven
formula/input invariants without depending on the local attachment paths. It is a
research probe, not a parallel production implementation or a registered signal.
Existing engine/canon.py remains the production formula owner. Its numerical seed,
warmup and missing-value policies must be compared with native Pine output before
claiming exact platform parity. No canonical math or golden vector is changed here.

## Initial comparison to register only after data qualification

Compare M, P and R individually; then M+P, M+R, P+R and M+P+R against the same
trend/volatility baseline, common qualified origins and unchanged path endpoint.
Seven combinations are a proposed ablation layout, NOT seven completed trials or
seven independent votes. Confluence recency, reset rules and calibration must be
frozen before registration/evaluation. Do not select them from the motivating chart.
Keep early histogram curl, confirmed cross and extreme-zone rules separate so earlier
warnings must earn their additional false alarms. Use the exact uploaded defaults
first; custom settings are a separately registered variant, not assumed chart settings.
Primary source target remains two-hour closed TVC:US10Y bars plus prior closed daily
context; proposed forward window is twelve completed bars, not 24 continuous hours.
Grade first-passage direction, no-hit/ambiguous/censored status, remaining bp after
confirmation, adverse excursion, alert coverage and the separate incremental equity
forecast. Bullish YIELD momentum is not automatically a bullish equity signal.

## Existing source lane located, but not yet qualified as research input

Terminal current master 1d2ac1e64a21c957b229e2e2567fcc248d557a64,
terminal/lib/intradaySources.ts has fetchYahooMacroIntraday and already routes ^TNX.
The code requests 60-minute source bars for 2h and uses the existing resampler.
This avoids creating another collector. It is a different source/symbol from TVC:US10Y.
The chart adapter can synthesize missing O/H/L from close/open, converts true epochs
to home-market DISPLAY epochs, and returns Bar6 without those origin flags. That is
not a certified OHLC/UTC research receipt. A price-stochastic study must retain actual
high/low flags; a first-passage study must not grade reconstructed extrema as observed.
At that code-inspection checkpoint, live availability had not yet been tested.
The subsequent source preflight is recorded below. No feed was modified.
Extend that owner on separate admitted source custody.

## Subsequent live-source preflight (not a strategy evaluation)

After the source-contract checkpoint, one bounded request used the incumbent Yahoo
chart endpoint on the original Studio: ^TNX, interval=60m, range=3mo, includePrePost=true.
HTTP 200, no chart error. Request/capture: 2026-09-24T12:51:02Z / 12:51:03Z.
Raw response SHA256: 687b93d52beeb141dbfc3ea3eff787b67da7b36daa8effedc19568cbe544d070.
Native evidence location (not a new store or collector):
/Volumes/Mastermind/evidence/rates-direction-20260924-sol-001/uploaded-formula-source-probe-20260924/.

450 timestamped observations, source metadata granularity=1h, timezone America/Chicago;
first 2026-06-24T12:20:00Z, last 2026-09-24T12:35:54Z. There are 64 UTC dates with
seven observations and one partial date with two. This captured batch has ZERO
null O/H/L/C fields, so the chart adapter's missing-field fallback was not needed
for these rows. That does not qualify all future/vendor rows.
The non-hour-aligned latest timestamp and partial day must not be declared completed
hourly or two-hour bars by appearance. Native timestamps, session anchoring, partial-
bar policy and any proxy scaling require qualification before a first-passage study.
The source-quality receipt hash is
4c6f5eda2698053e5738661a786476aef11e30caa78d0593c74c2da4b8db47b0.

This demonstrates a real existing intraday SOURCE route, not TVC symbol identity,
point-in-time historical knowledge, exact chart parity, a forecast or a win rate.
Only coverage/field metadata were inspected; no strategy outcomes were graded.
The existing source's US-day coverage must not silently replace the screenshot's
possibly different hours. Keep a TNX-proxy pilot distinct from TVC replication.
Next: qualify source/session/closed-bar semantics and native indicator output; then
freeze/register the comparison before opening its performance outcomes. Do not
rerun RD1, alter HS1 or install these reference functions as another production owner.
