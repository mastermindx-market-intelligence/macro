# Risk Radar Replay-Parity Rerun — Corrected Results

Rerun protocol: `e9ff3d234df1f50137bfa38a50995a70f06c1164`.
Evaluator invalidator/fix: PR #7632, merged as `7c6e35163c9f67087ffe174a7ab3810f47ce6a45`.

The same committed market-input hashes and the same forward price-outcome populations were used. The only semantic change was replacing the stale replay transition with the shipped live state transition.

## Executive result

The corrected replay strengthens the core Risk Radar architecture while narrowing several prior claims.

- The **broad-market loud gate still earns its role**: modern gated H21 precision rises from 39.3% in the stale replay to **42.0%**, recall remains **36.7%**, and fire rate falls from 16.5% to **15.4%**. The gate remains selective and expensive in recall by design.
- **Five-session caution persistence remains context, not a new alert.** Since 2020 its 5%-within-21 event rate rises from 22.7% to **24.0%** and lift from 1.29x to **1.36x**, but it is still active on **68.8%** of eligible sessions.
- The corrected **modern state ladder is point-monotonic at H5, H10, and H21**. The biggest correction is H21 elevated: stale replay **11.1% (n=36)** -> exact replay **30.3% (n=33)**. Risk-off is **43.8% (n=224)**. Elevated remains thin, so the correction restores directional ordering without proving a precise 30.3% probability.
- Four of five fixed historical warning-path examples are unchanged. The **SVB example weakens materially**: T-1 moves from caution to watch, caution-or-higher sessions in T-21..T0 fall 18 -> **14**, loud sessions 2 -> **1**, and the caution streak ending at T0 falls 10 -> **1**. The prior “persistent into the peak” characterization for SVB was overstated.

No live parameter or authority changed.

## Gate selectivity / latency

Same target: >=5% SPY loss within 21 native observations.

### Full history

| Metric | Pre-parity | Corrected |
|---|---:|---:|
| Raw precision | 20.6% | **21.0%** |
| Raw recall | 70.9% | **68.1%** |
| Raw fire rate | 60.6% | **57.1%** |
| Gated precision | 41.0% | **41.9%** |
| Gated recall | 28.7% | **28.3%** |
| Gated fire rate | 12.3% | **11.9%** |
| False-positive windows removed | 3,344 | **3,132** |
| True-positive windows lost | 610 | **576** |

### 2020+

| Metric | Pre-parity | Corrected |
|---|---:|---:|
| Raw precision | 23.2% | **24.5%** |
| Raw recall | 90.8% | **88.1%** |
| Raw fire rate | 69.0% | **63.4%** |
| Gated precision | 39.3% | **42.0%** |
| Gated recall | 36.7% | **36.7%** |
| Gated fire rate | 16.5% | **15.4%** |
| False-positive windows removed | 716 | **648** |
| True-positive windows lost | 159 | **151** |

Distinct-event gated recall by T0 changes 38.2% -> **37.3%**. Median gate latency remains **3 sessions**; p75 shortens 27.5 -> **23 sessions**. The gate conclusion survives the parity repair.

## Caution persistence

### Full history

Persistent-five event rate: 20.3% -> **20.8%**.
Lift vs base: 1.15x -> **1.18x**.
Recall: 72.8% -> **72.1%**.
Fire rate: 63.4% -> **61.2%**.

### 2020+

Persistent-five event rate: 22.7% -> **24.0%**.
Lift vs base: 1.29x -> **1.36x**.
Recall: 94.6% -> **93.5%**.
Fire rate: 73.3% -> **68.8%**.

The condition becomes somewhat more discriminating, but a condition active on roughly seven in ten modern sessions is not a sparse warning. Product use stays limited to neutral duration/context wording.

## State ladder

Corrected modern realized rates:

| Horizon | Calm | Watch | Caution | Elevated | Risk-off | Point ordered? |
|---|---:|---:|---:|---:|---:|---|
| H5 | 0.0% | 0.0% | 2.2% | **12.1% (n=33)** | **14.3% (n=224)** | yes |
| H10 | 0.0% | 0.0% | 6.3% | **24.2% (n=33)** | **27.7% (n=224)** | yes |
| H21 | 0.0% | 4.6% | 16.5% | **30.3% (n=33)** | **43.8% (n=224)** | yes |

The full-history and 2006+ ladders are still not strictly monotonic at every adjacent step because calm/watch are close and H21 elevated/risk-off are nearly tied. Those adjacent differences are not evidence for five independently precise bins.

The correct interpretation is therefore:
1. calm/watch = low-risk zone with weak separation;
2. caution = genuine “risk building” tier near the H21 unconditional base;
3. elevated = higher-risk transition tier, but modern n is thin;
4. risk-off = robust high-risk tier.

This supports preserving the plain-language ladder while showing evidence depth rather than manufacturing confidence.

## Fixed warning-path examples

2018Q4, COVID-2020, 2022 bear market, and Aug-2024 are unchanged under exact replay.

SVB March-2023 changes:
- T-21: risk-off -> risk-off;
- T-5: caution -> caution;
- T-1: caution -> **watch**;
- T0: caution -> caution;
- caution-or-higher sessions in T-21..T0: 18 -> **14**;
- elevated-or-higher sessions: 2 -> **1**;
- consecutive caution-or-higher sessions ending at T0: 10 -> **1**.

This is precisely why component “EARLY” timestamps cannot stand in for actual headline persistence.

## What this does not authorize

This rerun does not change `_PROB_CAL`, conjunction bumps, bands, scare weights, context-gate thresholds, gross factors, Market State authority, rankings, sizing, or capital policy.

The next model-quality study should evaluate the **complete displayed probability surface (state + conjunction count)** on the corrected replay, with fixed bins and calibration/error metrics, before any candidate probability retune. Issued/prospective forecast evidence remains the higher-authority path for eventual promotion.
