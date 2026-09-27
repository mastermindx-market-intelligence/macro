# Hong Kong Intraday Cross-Session Handoff — Tencent Development Results

Date: 2026-09-26  
State: DEVELOPMENT_EVIDENCE / SOURCE-GATED SECONDARY ENDPOINT / PRODUCTION_INERT / NO TRADING AUTHORITY  
Operation: `geopolitical-relief-event-study-20260924-sol-001`  
Carrier: Macro PR #8012 / `sol/geopolitical-relief-event-study-20260924`

## Evidence ordering

The target prices in this result were first read only after all of the following had been
frozen on the branch:

1. source change from degraded AkShare/Eastmoney to the incumbent Terminal Tencent HK owner:
   `research/HK_INTRADAY_HANDOFF_SOURCE_AMENDMENT_V2_2026-09-26.json`
   at commit `d3168c0e4802df0950d3ff1e09eb16eb1a18543c`;
2. timestamp-only inclusion/coverage for the frozen two-name target basket and both frozen
   benchmarks:
   `research/HK_INTRADAY_HANDOFF_COVERAGE_MANIFEST_V2_2026-09-26.json`
   at commit `0c253591637d2378d140b1e9c3b269123abf020d`;
3. non-target HSBC proof that Tencent historical `day/query`'s terminal 16:00 row is the
   provider-normalized session-close representation of the live closing-auction terminal print:
   `research/HK_INTRADAY_TENCENT_CLOSE_BASIS_RECEIPT_2026-09-26.json`
   at commit `c35d85e8cab8ac34a594fed8fee7061a0e318ccf`.

No target return, residual or sign was used to select the source, target names, benchmark,
coverage dates, or measurement clocks.

## Frozen construction

Targets:
- SMIC / `0981.HK`;
- Hua Hong Semiconductor / `1347.HK`.

Target basket:
- equal weight across every frozen target that passed timestamp coverage;
- both passed all required clocks.

Primary benchmark:
- Tracker Fund of Hong Kong / `2800.HK`.

Sensitivity benchmark:
- CSOP Hang Seng TECH ETF / `3033.HK`.

Primary target-region measurement:
- provider-normalized previous HK cash-session close;
- next HK cash session 09:35 HKT price;
- target equal-weight return minus 2800 return on the same geometry.

Secondary:
- 09:35 -> 10:00 HKT continuation;
- same close -> 09:35 target residual versus 3033.

Price basis:
- raw Tencent minute last-price points only;
- synthesized OHLC highs/lows are not used.

## Results

All values are basis points.

| Event | Next HK session | SMIC close→09:35 | Hua Hong close→09:35 | Target EW | 2800 | **Residual vs 2800** | 3033 | Residual vs 3033 | Target 09:35→10:00 | Continuation residual vs 2800 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-22 Iran could open Hormuz in seven days | 2026-09-23 | -15.55 | +79.09 | +31.77 | -69.93 | **+101.70** | -55.12 | +86.89 | +51.85 | +75.32 |
| 2026-09-23 Iran reviewing U.S. response | 2026-09-24 | -70.53 | -201.40 | -135.97 | -31.45 | **-104.52** | -23.36 | -112.60 | -72.31 | -56.53 |
| 2026-09-24 phased Hormuz-blockade relief | 2026-09-25 | -219.44 | -153.99 | -186.71 | -157.60 | **-29.11** | -243.45 | +56.74 | -10.98 | -10.98 |

Continuation residual versus 3033:
- Sep 22 -> Sep 23: **+98.03 bp**
- Sep 23 -> Sep 24: **-44.20 bp**
- Sep 24 -> Sep 25: **-20.58 bp**

## Descriptive reading

Primary residual versus 2800:
- positive: **1 / 3**
- negative: **2 / 3**
- mean: approximately **-10.64 bp**
- median: **-29.11 bp**

The target-region first-five-minute semiconductor residual therefore does **not** show a stable
same-direction development pattern across the three recoverable events. The +5->+30 continuation
is also mixed.

The 3033 sensitivity comparison does not rescue the construction:
- close->09:35 target residual vs 3033 is positive on 2/3 rows but changes sign versus the
  primary broad-HK benchmark on Sep 24;
- continuation residual vs 3033 is positive on only 1/3 rows.

This is a useful falsifier. It reinforces the existing specificity ruling that the surviving
cross-session development signal should **not** be described as a Hong-Kong-semiconductor or
semiconductor-specific handoff.

## What this does and does not prove

This result proves only that:

- the existing Terminal Tencent HK source is currently sufficient for bounded recent-session
  1-minute research on the frozen symbols;
- the previously blocked secondary HK intraday endpoint can be measured without a new data plane;
- on the three recoverable development events, the frozen HK semiconductor basket response is mixed
  rather than a clean continuation pattern.

It does **not** prove:
- prospective generalization;
- a forecast or probability;
- alpha;
- source-corpus completeness;
- a causal mechanism;
- a product state;
- an alert, ranking, sizing, portfolio or execution right.

The rows are development evidence. Existing daily HSI outcomes were already open, and the
prospective V1/V1.1 clocks begin later. None of these rows count toward the prospective cohort.

## Source capability ruling

For **future prospective events**, Tencent may satisfy the secondary HK intraday endpoint only while:

- the exact existing Terminal source owner remains compatible;
- the required prior close / next-session 09:35 / 10:00 clocks are present;
- the result is labeled with the source's delayed/research basis;
- no forward fill or benchmark substitution occurs;
- source failure remains DATA_GAP.

The source offers only roughly five recent sessions, so measurement must occur while the relevant
session remains available. This is an operational retention constraint, not permission to build a
new regional minute store in this research carrier.

## Disposition

**DEVELOPMENT FALSIFIER / SOURCE CAPABILITY UNBLOCKED / PROSPECTIVE RESULT UNCHANGED.**

Preserve:
- V1 primary: SMH-minus-QQQ +5->+35;
- V1.1 challenger: QQQ-minus-SPY +5->+35;
- HSI next-cash-open as the primary accepted target-region endpoint;
- HK semiconductor intraday as a secondary capability-gated diagnostic only.

No further development predictor search is authorized from these target outcomes.
