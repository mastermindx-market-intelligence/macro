# Narrative Handoff Pilot Replay Receipt — 2026-09-25

State: PILOT_EVIDENCE / RESEARCH_ONLY / PRODUCTION_INERT / NOT_ALPHA_PROOF
Operation: geopolitical-relief-event-study-20260924-sol-001
Carrier: Macro PR #8012 / sol/geopolitical-relief-event-study-20260924
Research code head used for live replay: 235602a19c5d6ad09add26d06bd8b7640333906a
Mastermind procedure pin: 605cd056c3463c992d85ba76dbcc90fbb758da75
Skillpack: mastermind.sol_skillpack.v1 1.0.1 / bootstrap major 1

## 1. Purpose and evidence boundary

This receipt records the first real, bounded replays of the frozen research.event_microstructure_study.v1 calculator and the no-persistence Massive/Polygon minute adapter. It is a pilot, not a promotion result.

No minute data was persisted. Each replay used one declared session and a small symbol set through the incumbent Massive/Polygon stocks REST entitlement. The adapter stamped each minute close at vendor bar-start + 60 seconds so a close was never treated as knowable at the beginning of its minute.

Direct WTI/Brent minute authority remains unresolved. USO is an explicit oil-price proxy; XLE is a secondary energy-equity check.

The v1 preregistration remains frozen. Findings in sections 5-7 are post-hoc hypotheses and must not be retroactively turned into v1 acceptance rules.

## 2. Exact verification before replay

Exact branch head 235602a19c5d6ad09add26d06bd8b7640333906a was fetched into an isolated M2 Studio worktree and the two focused suites ran against the real Macro environment:

- tests/test_event_microstructure_study.py
- tests/test_event_microstructure_replay.py

Result: 16 passed. Existing unrelated pytest cleanup warnings from browser-runtime temp directories remained warnings only.

The canonical Macro config loader confirmed the existing Massive credential was available; no credential value was printed or copied.

## 3. September 24 motivating event — source-clock sensitivity

Public-source reconciliation found multiple publication/distribution clocks. FinancialJuice's market-moving feed exposed the headline at 16:15 UTC. Reuters republications appeared around 16:16-16:17 UTC. Because market dissemination and article publication clocks differ, the 16:15 replay is the controlling pilot read and later clocks are sensitivity reads only.

### 16:15 UTC controlling pilot clock

USO:
- baseline 154.99 at 16:15
- first >=25 bp downside confirmation at 16:16
- move at confirmation: -127.75 bp

XLE:
- baseline 63.28 at 16:15
- downside confirmation at 16:16
- move: -45.83 bp

SMH:
- baseline 593.30 at 16:15
- >=25 bp upside response at 16:16
- move: +27.14 bp
- causal-to-response threshold lag: 0 seconds

Therefore the simple 'oil moves first, semis lag' hypothesis is not supported by the earliest recovered public distribution clock. The first impulse was effectively synchronous at one-minute resolution.

However, from the 16:16 causal-confirmation minute, SMH continued to outperform QQQ:

| Horizon | SMH return | QQQ return | SMH residual |
|---|---:|---:|---:|
| 5m | +55.22 bp | +22.02 bp | +33.19 bp |
| 15m | +34.88 bp | +22.77 bp | +12.11 bp |
| 30m | +75.64 bp | +36.73 bp | +38.91 bp |
| 60m | +79.84 bp | +47.98 bp | +31.87 bp |

### 16:16 sensitivity clock

USO downside confirmation: 16:17, -87.58 bp. SMH response threshold also 16:17. Lag: 0 seconds. SMH residual: +30.53 bp at 30m and +22.50 bp at 60m.

### 16:17 sensitivity clock

USO downside confirmation: 16:19, -27.69 bp. SMH threshold: 16:37. Apparent lag: 1,080 seconds. SMH residual: +21.19 bp at 30m and +14.64 bp at 60m.

The 18-minute lag is not accepted as evidence of a causal lead-lag because the 16:17 anchor occurs after the first synchronized market move. It is a re-anchoring artifact candidate. The continuation residual is the more robust observation across all three clocks.

## 4. Prior-event falsifiers

### 2026-07-20 Reuters ceasefire proposal

Timestamp sensitivity used 11:44 UTC and 11:47 UTC Reuters-linked republication clocks.

At both clocks:
- USO failed to cross the frozen 25 bp downside threshold within 10 minutes.
- XLE also failed confirmation.
- No downstream signal was eligible.

Classification: UNCONFIRMED / NO SIGNAL.

### 2026-09-22 'momentum for a deal'

Timestamp sensitivity used 20:34 UTC and 20:35 UTC public market-feed clocks.

At both clocks:
- USO did not confirm lower.
- XLE did not confirm lower.
- SMH did not confirm higher.

Classification: UNCONFIRMED / NO SIGNAL.

### 2026-09-14 'step-by-step agreement'

Newsquawk live-feed timestamp: 16:48 UTC. Newsquawk contemporaneously described the next-minute cross-asset state as geopolitical risk-on: oil and dollar down, stocks and Treasuries up.

Replay:
- XLE confirmed lower at 16:49, -29.30 bp.
- USO confirmed lower at 16:53, -34.87 bp.
- SMH never crossed the frozen +25 bp response threshold.
- SMH residual vs QQQ after USO confirmation:
  - 5m: -6.08 bp
  - 15m: -6.49 bp
  - 30m: -13.12 bp
  - 60m: -15.39 bp

Classification: CAUSAL PROXY CONFIRMED / SEMICONDUCTOR CONTINUATION FAILED.

This falsifies the broad claim that credible geopolitical relief plus oil confirmation is sufficient for a semiconductor continuation trade.

## 5. Name-level September 24 diagnostic

This section is exploratory and was performed after seeing the event-level result.

At the 16:15 event clock, previous-close damage was:
- ARM: -801.7 bp
- NVDA: -134.8 bp
- SMH: -129.8 bp
- QQQ: -66.7 bp
- AMD: -37.1 bp
- INTC: +57.1 bp

Thirty-minute residual return versus QQQ after USO confirmation at 16:16:
- ARM: +215.4 bp
- AMD: +125.0 bp
- INTC: +59.6 bp
- NVDA: +11.7 bp

ARM was the clearest damaged-name catch-up case. AMD and INTC show that previous-close damage alone is not a complete explanation.

A fixed 12-name semiconductor diagnostic set (AMD, ARM, INTC, NVDA, AVGO, MU, QCOM, MRVL, AMAT, LRCX, KLAC, TSM) produced on Sep 24:
- Spearman correlation between previous-close damage rank and 30m residual rank: -0.14 (weak).
- Most-damaged quartile mean 30m residual: +91.9 bp.
- Least-damaged quartile mean 30m residual: +69.4 bp.
- Quartile spread: +22.5 bp.

On the Sep 14 control:
- Spearman: +0.252.
- Most-damaged quartile mean residual: -32.5 bp.
- Least-damaged quartile mean residual: -27.3 bp.
- Spread: -5.2 bp.

Conclusion: the pilot does not support a monotonic 'buy the biggest semiconductor losers' rule. Pre-event damage may be one interaction, but it is not sufficient.

## 6. Stronger post-hoc separator: pre-event oil risk premium

The largest qualitative difference between Sep 24 and Sep 14 is upstream.

Sep 24 before the 16:15 event:
- USO from U.S. regular-session open: +257.4 bp.
- First confirmed relief minute: -127.75 bp.
- SMH 30m residual after confirmation: +38.91 bp.

Sep 14 before the 16:48 event:
- USO from U.S. regular-session open: -195.1 bp.
- Confirming downside move by 16:53: -34.87 bp.
- SMH 30m residual after confirmation: -13.12 bp.

This suggests a more specific mechanism:

> a material geopolitical risk premium is already embedded in oil -> a genuinely incremental relief headline causes a large oil reversal -> the first equity impulse is synchronous -> high-beta/risk-sensitive equities may continue repricing for tens of minutes as the macro risk-premium unwind propagates.

This is materially different from the original 'oil moves first and semis lag' story.

## 7. Proposed v2 research hypothesis — NOT retrospectively promoted

Do not change v1 thresholds based on this pilot.

Register a new v2 family before assembling the larger outcome-bearing sample: Geopolitical Risk-Premium Unwind Continuation.

Candidate pre-event state:
- geopolitical/oil risk premium elevated relative to the same session and recent baseline;
- relief headline is incremental, source-credible, and not merely recycled optimism;
- causal oil or admitted oil-proxy reversal is large relative to its recent intraday volatility;
- broad equity first impulse confirms risk-on rather than contradicting it.

Candidate research endpoint:
- residual return of high-beta / geopolitically sensitive equity cohorts from the end of the first synchronized impulse to +15/+30/+60 minutes.

Candidate falsifiers:
- oil already falling before the headline;
- no causal reversal;
- equity response leads without a credible source clock;
- conflicting escalation headline;
- continuation disappears after matched-time controls, spread/slippage, or event-clustered holdout;
- effect is carried by one event or one name.

Do not freeze numeric v2 thresholds from Sep 24. Thresholds must be specified from training-only history or source-independent economic units before the chronological holdout is inspected.

## 8. What this changes for the proposed Mastermind product

Rename the conceptual product from a simple 'lag radar' to Narrative Repricing Radar.

Candidate read-only states:
1. NARRATIVE DETECTED
2. SOURCE CREDIBILITY / NOVELTY ESTABLISHED
3. PRE-EVENT RISK PREMIUM MEASURED
4. CAUSAL ASSET CONFIRMED
5. FIRST IMPULSE COMPLETE
6. SECOND-STAGE REPRICING / NO CONTINUATION
7. LAG CLOSED / THESIS FAILED / DATA GAP

The product should display, not trade:
- exact source ladder and clocks;
- pre-event oil-risk state;
- causal reversal magnitude and intraday-volatility normalization;
- broad-index first impulse;
- sector and name residual continuation;
- dispersion and prior damage;
- matched historical analogues and failures;
- freshness/missingness/confounders;
- explicit falsifier.

No ranking, alerting, sizing, execution, or portfolio authority is granted by this pilot.

## 9. Next evidence wave

1. Freeze v2 hypothesis wording and pre-event feature definitions without looking at new event outcomes.
2. Build a source-only event manifest of at least 20 independent event clusters spanning multiple geopolitical/narrative subfamilies.
3. Add matched non-event windows and failed-rumor controls.
4. Measure pre-event oil-risk premium and first-impulse magnitude in source-independent units.
5. Run chronological/event-clustered train/development/holdout analysis.
6. Only after holdout evidence may a read-only Narrative Repricing Radar be wired into the existing Market Memory/Terminal consumer path.
7. Trading promotion remains a separate later decision with costs, slippage, false-positive and portfolio-risk evidence.
