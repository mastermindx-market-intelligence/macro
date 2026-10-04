# Narrative Repricing V2 — Clock-Clean Wave 2 Results

Date: 2026-09-26
State: TRAINING_EVIDENCE / RESEARCH_ONLY / PRODUCTION_INERT / NO TRADING AUTHORITY
Operation: geopolitical-relief-event-study-20260924-sol-001
Carrier: Macro PR #8012 / sol/geopolitical-relief-event-study-20260924
Wave-2 source freeze: f87c6a13bc109bf09125f0db61f7bd83e03304ad
Extraction head: ca379cd74f6986df1bce87ec7af183927c507660
Mastermind protected procedure pin: 58c842d5ab99e29785ec9b4d16ccee67e85e19c4
Skillpack index blob: 94d1af402598894372858793a5b1931019c5fa77
ACTIVE_EXECUTION blob: 9fed10f7cc7a2f4323d039b406f7c0715445e22e

## 1. Evidence boundary

Wave 2 was frozen source-side before this outcome extraction. No timestamp, event role,
threshold, response horizon, symbol mapping, or missing-data rule was changed after observing
returns.

The exact current PR head passed the focused research suites before vendor access:

- tests/test_event_microstructure_study.py
- tests/test_event_microstructure_replay.py
- tests/test_cross_session_source_census.py

Result: 26 passed. Existing unrelated pytest temp-browser cleanup warnings remained warnings only.

The extraction reused the incumbent Massive/Polygon U.S.-stocks minute entitlement and wrote
no minute data. USO remains an explicit oil-price proxy; SMH is the response cohort and QQQ
the benchmark.

Frozen first-pass law:
- signed USO return over trailing 60m and 240m where available;
- signed USO move from available_at to +5m;
- SMH minus QQQ residual from +5m to +20/+35/+65m;
- no re-anchoring on missing bars;
- missingness remains visible.

For relief events, positive signed causal values mean USO moved in the expected lower-oil direction.

## 2. Primary Wave-2 rows

| Event | USO pre-60m signed | USO 0→+5m signed | SMH-QQQ +5→+20 | +5→+35 primary | +5→+65 |
|---|---:|---:|---:|---:|---:|
| 2026-06-15 senior U.S. official: signed MoU / immediate Hormuz opening | -61.67 bp | -0.42 bp | -7.36 bp | **+4.79 bp** | +4.63 bp |
| 2026-06-17 Trump: Hormuz open in next day or two | -17.54 bp | +13.13 bp | -19.28 bp | **-19.05 bp** | -28.92 bp |

The two primary 30-minute residuals are:

+4.788 bp, -19.045 bp.

Descriptive summary only:
- mean: **-7.13 bp**
- median: **-7.13 bp**
- positive rate: **1/2 = 50%**
- range: **-19.05 to +4.79 bp**

This wave does not support a general positive semiconductor-continuation effect.

## 3. June 15 interpretation

The June 15 event was deliberately retained as an official confirmation with material
execution detail rather than mislabeled as first disclosure.

Despite the high-resolution content:
- signed pre-60m USO state was -61.67 bp, meaning oil had already moved opposite the expected
  relief direction over the prior hour;
- the first five minutes after the exact headline produced only -0.42 bp of signed causal
  relief movement, effectively no new oil confirmation;
- the primary +5→+35 SMH-vs-QQQ residual was only +4.79 bp.

This is consistent with substantial prior information already being priced before the official
confirmation. It does not validate the September 24 continuation mechanism.

## 4. June 17 interpretation

The June 17 official follow-up produced:
- signed pre-60m USO state: -17.54 bp;
- first-five-minute signed USO relief move: +13.13 bp;
- +5→+35 SMH-vs-QQQ residual: **-19.05 bp**;
- +5→+65 residual: **-28.92 bp**.

A later official statement with modest oil confirmation therefore did not produce positive
semiconductor continuation.

This strengthens the distinction between:
- information novelty / market surprise;
- authoritative confirmation;
- physical-channel specificity;
- and downstream equity continuation.

Authority and specificity alone are not sufficient.

## 5. Weak mediation control

Frozen control:
2026-07-30 09:14Z — mediators working toward a ceasefire, explicitly "no tangible results yet."

Measured partial row:
- signed pre-60m USO: +18.60 bp;
- signed USO 0→+5m: +45.50 bp;
- +5→+35 SMH-vs-QQQ residual: **-9.73 bp**;
- +5→+65 residual: +10.28 bp.

The overall first-pass status is DATA_GAP because the exact event-clock response/benchmark
observations required for the complete first-impulse record were not jointly available.
The later +5-based response window is retained as a partial diagnostic only, not promoted to
a complete primary row.

Importantly, even this larger oil move did not imply positive 30-minute semiconductor residual.

## 6. Combined read with Wave 1

Wave 1 complete primary +5→+35 residuals:
+22.86, -29.55, -10.76, -20.32, -12.60 bp.

Wave 2 adds:
+4.79, -19.05 bp.

Across the seven complete clock-clean training rows measured so far:
- positive rows: 2/7;
- negative rows: 5/7;
- the simple broad claim "credible relief + oil confirmation => positive semiconductor
  continuation" remains unsupported.

No pooled significance claim is made here because feature families, event-role strata,
calendar availability, and source-side taxonomy remain under active preregistered study.

## 7. Capability delta

The research now has multiple independent falsifiers spanning:
- first disclosure;
- authoritative execution confirmation;
- later official confirmation;
- weak/unconfirmed mediation;
- generic diplomatic optimism;
- and the exceptional September 24 pilot.

The useful surviving question is not whether a peace headline mechanically causes semis to rally.
It is which *source-side and market-state interactions* distinguish the rare large repricing
episodes from the many events that do not propagate.

The frozen candidate dimensions remain:
- source novelty;
- execution credibility;
- physical-channel specificity;
- pre-event causal risk-premium state;
- first synchronized equity impulse;
- broad-market breadth;
- competing semiconductor-specific news;
- volatility-normalized causal reversal;
- session / regional handoff state.

None is a trading rule yet.

## 8. Current disposition

- V1 one-minute oil-leads-semis lag: falsified at the earliest September 24 distribution clock.
- V2 broad risk-premium-unwind continuation: not supported as a sufficient rule by Waves 1-2.
- September 24 remains an outlier that requires explanatory interactions, not threshold tuning.
- No development/holdout threshold is selected.
- Prospective holdout remains untouched.
- No product, ranking, alert, sizing, portfolio, or execution authority is granted.

## 9. Exact continuation

1. Keep source-side feature taxonomy frozen before any model/threshold selection.
2. Continue clock-clean source corpus expansion and opposite-direction controls.
3. Use the already-added first-synchronized-impulse output and source census firewall.
4. Repair #8012 CI contract ownership by wiring the new research test suites into the existing
   CI plan; do not waive them merely to obtain green.
5. After CI ownership is repaired, measure Wave-3/control outcomes only under their frozen
   source manifest and preregistered direction law.
6. Keep cross-session timing-frequency research separate from same-session V2 outcomes.
