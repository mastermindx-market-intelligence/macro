# PB-B source ledger

As of 2026-10-07 UTC. 89 source records. Records are sources, not independent observations or event counts.

## Evidence and clock policy

BOJ/Fed/Treasury/MOF records anchor actions and instrument rules. Statistics Bureau, MHLW, Cabinet Office and Rengo provide separate domestic-data origins. Reuters syndications share their original reporting lineage; multiple anonymous sources within one report are not multiple independent publications. Bank research is interpretation.

Date-only public clocks use a conservative end of the publisher’s civil day; Japanese dates use UTC+9 and U.S. Treasury dates America/New_York. A public-by bound is not a fictional midnight first release. Public-before-cut is computed separately in each episode. The current body of the September18-updated private-pressure report is not admitted before that date’s decision.

Dated official PDFs and publisher edition metadata establish practical research assurance, not forensic historical hashes. The FOMC directive’s effective date is distinct from first public posting, so it is used only for the as-of mechanism audit. The latest August CPI PDF is explicitly identified by its printed September18 release date.

## Material corrections and access limits

| Issue | Treatment |
|---|---|
| January rate check | Quote inquiry, not funded FX intervention; later official zeros retained. |
| Joint-operation date | July31 confirmed by on-record wire. U.S.Eastern qualifier comes from indexed MOF primary; English and one Japanese full-page retrieval failed. |
| July size | ¥15,399.3bn is Japan’s July30–August26 period total. U.S. size and Japan July31 daily amount remain null. |
| FIMA usage claim | Preserve contemporaneous reported utilization as disputed; later H.4.1 daily-average and Wednesday zeros reject material reported borrowing in the intervention week. |
| FIMA rule | $60bn total outstanding per counterparty; specified subcommittee delegation. Not a daily cap or proof of enlargement. |
| Private conditionality | September reconstruction is later mechanism evidence. Original header Sep17 23:04UTC does not certify current updated body before Sep18 decision. |
| Domestic vintages | June2025 preliminary wages before Aug13, revised only Aug22; Q2GDP2025 only Aug15. June2026 revised wages available Aug24, Q2 first GDP Aug17; Sep8 revisions are later. |
| CPI exclusions | Japanese ex-fresh-food-and-energy retains processed food; do not substitute U.S.-style all-food-and-energy exclusion. |
| Missing records | Q3 NYFed/daily MOF release not available by cutoff; original Bessent letter not retrieved; exact U.S. amount, access condition and pre-May BOJ plan remain unresolved. |

## CPI_2025_06

**[Consumer Price Index, Japan, June 2025, original 2020-base release](https://www.e-stat.go.jp/stat-search/file-download?fileKind=2&statInfId=000040293364)**

- Origin: Statistics Bureau of Japan; classification: `primary`; family: `statistics_bureau_cpi`.
- Publication date: 2025-07-18; exact/minute UTC clock: null; relevant edition public-by bound: 2025-07-18T14:59:59Z.
- Version basis: Printed July 18 release date and June 2025 title in archived PDF; opened turn81view0/turn95view1. Exact exclusion row verified in turn90view1/turn89view3 and local PDF extraction.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Unadjusted year-over-year rates. Japanese ex-fresh-food-and-energy CPI still includes processed food. Preserve 2020 base; do not substitute 2026 rebased history. Intraday release time not verified in notes.
- Bounded extraction: Headline CPI 111.7 (2020=100), +3.3% y/y. CPI excluding fresh food 111.4, +3.3% y/y. CPI excluding fresh food and energy 110.3, +3.4% y/y. CPI excluding food other than alcoholic beverages and energy 105.3, +1.6% y/y; weight 6781/10000. Food CPI +7.2% y/y; food excluding fresh food +8.2% y/y.

## WAGES_2025_06_P

**[Monthly Labour Survey, Japan, June 2025, preliminary](https://www.mhlw.go.jp/toukei/itiran/roudou/monthly/r07/2506p/dl/pdf2506p.pdf)**

- Origin: Ministry of Health, Labour and Welfare; classification: `primary`; family: `mhlw_monthly_labour`.
- Publication date: 2025-08-06; exact/minute UTC clock: null; relevant edition public-by bound: 2025-08-06T14:59:59Z.
- Version basis: Dated original preliminary PDF and corresponding release HTML; opened turn82view0/turn85view1. Intraday release clock not verified.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: All employment types; establishments with five or more employees; average per-person monthly cash earnings. Standard real series uses CPI excluding imputed owner-occupied rent; the alternative uses headline CPI. MHLW preserves publication-time archive figures but later benchmark/sample revisions can change historical rates.
- Bounded extraction: Total nominal cash earnings JPY 511,210, +2.5% y/y. Basic contractual pay excluding overtime +2.1% y/y. Total real earnings with CPI excluding imputed owner-occupied rent -1.3% y/y. Total real earnings with headline CPI -0.7% y/y. Eligible before August 13, 2025; August 22 revision was not yet public.

## WAGES_2025_06_R

**[Monthly Labour Survey, Japan, June 2025, final/revised](https://www.mhlw.go.jp/toukei/itiran/roudou/monthly/r07/2506r/dl/pdf2506r.pdf)**

- Origin: Ministry of Health, Labour and Welfare; classification: `primary`; family: `mhlw_monthly_labour`.
- Publication date: 2025-08-22; exact/minute UTC clock: null; relevant edition public-by bound: 2025-08-22T14:59:59Z.
- Version basis: Dated original final/revised PDF and corresponding release HTML; opened turn82view1/turn86view0/turn87view2. Intraday release clock not verified.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: All employment types; establishments with five or more employees; average per-person monthly cash earnings. Standard real series uses CPI excluding imputed owner-occupied rent; the alternative uses headline CPI. MHLW preserves publication-time archive figures but later benchmark/sample revisions can change historical rates.
- Bounded extraction: Total nominal cash earnings JPY 514,106, +3.1% y/y. Basic contractual pay excluding overtime +2.0% y/y. Total real earnings with CPI excluding imputed owner-occupied rent -0.8% y/y. Total real earnings with headline CPI -0.1% y/y. Released after August 13, 2025; cannot be an August 13 pre-event feature.

## CPI_2026_07

**[Consumer Price Index, Japan, July 2026, original 2025-base release](https://www.e-stat.go.jp/stat-search/file-download?fileKind=2&statInfId=000040491312)**

- Origin: Statistics Bureau of Japan; classification: `primary`; family: `statistics_bureau_cpi`.
- Publication date: 2026-08-21; exact/minute UTC clock: 2026-08-20T23:30:00Z; relevant edition public-by bound: 2026-08-20T23:30:59Z.
- Version basis: Printed August 21 date in archived July PDF; opened turn94view0/turn95view0. Official e-Stat calendar turn83view2/turn86view5 line1136 records 08:30 JST: https://www.e-stat.go.jp/release-calendar?endDay=31&endMonth=12&endYear=2028&startDay=1&startMonth=11&startYear=2025
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Unadjusted year-over-year rates; 2025 base differs from June 2025 original 2020 base. Latest CPI webpage/zenkoku.pdf are overwritten and now display August 2026 published September 18. Use archived July PDF.
- Bounded extraction: Headline CPI 102.0 (2025=100), +1.9% y/y. CPI excluding fresh food 102.1, +1.8% y/y. CPI excluding fresh food and energy 102.1, +1.9% y/y. CPI excluding food other than alcoholic beverages and energy 101.6, +1.4% y/y; weight 6609/10000. 2025-base CPI rebase/backseries release occurred August 7, 2026, 16:00 JST and was public before August 30.

## WAGES_2026_06_P

**[Monthly Labour Survey, Japan, June 2026, preliminary](https://www.mhlw.go.jp/toukei/itiran/roudou/monthly/r08/2606p/dl/pdf2606p.pdf)**

- Origin: Ministry of Health, Labour and Welfare; classification: `primary`; family: `mhlw_monthly_labour`.
- Publication date: 2026-08-05; exact/minute UTC clock: 2026-08-04T23:30:00Z; relevant edition public-by bound: 2026-08-04T23:30:59Z.
- Version basis: Dated original preliminary PDF and corresponding release HTML; opened turn82view2/turn86view1/turn87view0; calendar turn86view4 line1108. 08:30 JST clock corroborated by official e-Stat release calendar https://www.e-stat.go.jp/release-calendar?endDay=31&endMonth=12&endYear=2028&startDay=1&startMonth=11&startYear=2025
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: All employment types; establishments with five or more employees; average per-person monthly cash earnings. Standard real series uses CPI excluding imputed owner-occupied rent; the alternative uses headline CPI. MHLW preserves publication-time archive figures but later benchmark/sample revisions can change historical rates.
- Bounded extraction: Total nominal cash earnings JPY 531,677, +3.4% y/y. Basic contractual pay excluding overtime +3.4% y/y. Total real earnings with CPI excluding imputed owner-occupied rent +1.6% y/y. Total real earnings with headline CPI +1.7% y/y.

## WAGES_2026_06_R

**[Monthly Labour Survey, Japan, June 2026, final/revised](https://www.mhlw.go.jp/toukei/itiran/roudou/monthly/r08/2606r/dl/pdf2606r.pdf)**

- Origin: Ministry of Health, Labour and Welfare; classification: `primary`; family: `mhlw_monthly_labour`.
- Publication date: 2026-08-24; exact/minute UTC clock: 2026-08-23T23:30:00Z; relevant edition public-by bound: 2026-08-23T23:30:59Z.
- Version basis: Dated original final/revised PDF and corresponding release HTML; opened turn82view3/turn86view2/turn87view1; calendar turn83view2 line1140. 08:30 JST clock corroborated by official e-Stat release calendar https://www.e-stat.go.jp/release-calendar?endDay=31&endMonth=12&endYear=2028&startDay=1&startMonth=11&startYear=2025
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: All employment types; establishments with five or more employees; average per-person monthly cash earnings. Standard real series uses CPI excluding imputed owner-occupied rent; the alternative uses headline CPI. MHLW preserves publication-time archive figures but later benchmark/sample revisions can change historical rates.
- Bounded extraction: Total nominal cash earnings JPY 534,823, +4.0% y/y. Basic contractual pay excluding overtime +3.5% y/y. Total real earnings with CPI excluding imputed owner-occupied rent +2.2% y/y. Total real earnings with headline CPI +2.3% y/y. Contractual cash earnings (including overtime) +3.4% y/y. Revised June vintage was available before August 30 and September 1, 2026.

## GDP_2025_Q1_2

**[Quarterly Estimates of GDP, January–March 2025, Second Preliminary Estimates](https://www.esri.cao.go.jp/en/sna/data/sokuhou/files/2025/qe251_2/pdf/gaiyou2512_e.pdf)**

- Origin: Cabinet Office, Economic and Social Research Institute; classification: `primary`; family: `cabinet_office_gdp`.
- Publication date: 2025-06-09; exact/minute UTC clock: null; relevant edition public-by bound: 2025-06-09T14:59:59Z.
- Version basis: PDF page1 printed Released: 2025.6.9; opened turn81view2/turn95view2. 2025 release archive opened turn73view5/turn74view1.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Real seasonally adjusted quarter-on-quarter rates, chained 2015 yen. Preserve this vintage rather than the later 2020-benchmark revision. Intraday release clock not verified.
- Bounded extraction: Q1 2025 real GDP -0.0% q/q (rounded), -0.2% annualized. May 16 first estimate was -0.2% q/q, -0.7% annualized. Q2 2025 first estimate was released August 15, 2025, after August 13; cannot be an August 13 pre-event feature.

## GDP_2026_Q2_1

**[Quarterly Estimates of GDP, April–June 2026, First Preliminary Estimates](https://www.esri.cao.go.jp/en/sna/data/sokuhou/files/2026/qe262/pdf/gaiyou2621_e.pdf)**

- Origin: Cabinet Office, Economic and Social Research Institute; classification: `primary`; family: `cabinet_office_gdp`.
- Publication date: 2026-08-17; exact/minute UTC clock: 2026-08-16T23:50:00Z; relevant edition public-by bound: 2026-08-16T23:50:59Z.
- Version basis: PDF page1 printed Monday August17/Released2026.8.17; opened turn74view2/turn88view1. Official e-Stat calendar turn83view2 line1125 corroborates 08:50 JST: https://www.e-stat.go.jp/release-calendar?endDay=31&endMonth=12&endYear=2028&startDay=1&startMonth=11&startYear=2025
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Real seasonally adjusted quarter-on-quarter rates, chained 2020 yen. GDP headline growth and domestic-demand growth are distinct. September 8 second estimate was unavailable at August 30/September 1 cuts.
- Bounded extraction: Q2 2026 real GDP +0.3% q/q, +1.1% annualized. Domestic demand -0.2% q/q; contribution -0.2 percentage points. Private consumption -0.0% q/q (rounded). Private nonresidential investment -1.2% q/q. Net exports contribution +0.5 percentage points.

## GDP_2026_Q2_2

**[Q2 2026 GDP second preliminary estimates](https://www.esri.cao.go.jp/en/sna/data/sokuhou/files/2026/qe262_2/pdf/gaiyou2622_e.pdf)**

- Origin: Cabinet Office, Economic and Social Research Institute; classification: `primary`; family: `cabinet_office_gdp`.
- Publication date: 2026-09-08; exact/minute UTC clock: null; relevant edition public-by bound: 2026-09-08T14:59:59Z.
- Version basis: Original PDF opened by late_2026_pressure; official archive corroborates September8 release.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Revised vintage after late-August/September1 cuts; annualized rate not calculated from rounded q/q.
- Bounded extraction: Real GDP+0.4% q/q, +1.4% annualized.

## WAGES_2026_07_P

**[July2026 Monthly Labour Survey preliminary](https://www.mhlw.go.jp/toukei/itiran/roudou/monthly/r08/2607p/dl/pdf2607p.pdf)**

- Origin: e-Stat government statistics portal / Ministry of Health, Labour and Welfare; classification: `primary`; family: `mhlw_monthly_labour`.
- Publication date: 2026-09-08; exact/minute UTC clock: 2026-09-07T23:30:00Z; relevant edition public-by bound: 2026-09-07T23:30:59Z.
- Version basis: Original PDF opened by late_2026_pressure; official calendar verifiesSeptember8 08:30JST.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Preliminary; establishments5+; sample effects; standard real uses CPI excluding imputed rent.
- Bounded extraction: Total nominal+4.7% y/y; basic/scheduled excluding overtime+4.1%; real+2.4%; same-establishment total+2.8%.

## RENGO_2024_FINAL

**[2024 Spring Wage Negotiations, Seventh/Final Tally](https://www.jtuc-rengo.or.jp/activity/roudou/shuntou/2024/yokyu_kaito/kaito/press_no7.pdf)**

- Origin: Japanese Trade Union Confederation (Rengo); classification: `primary`; family: `rengo_wage_agreements`.
- Publication date: 2024-07-03; exact/minute UTC clock: null; relevant edition public-by bound: 2024-07-03T14:59:59Z.
- Version basis: Root opened original PDF, page1 prints July3 2024; values and publication date directly verified.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Negotiated union pay including seniority increments, not economywide realized wage growth.
- Bounded extraction: Final weighted total negotiated increase including regular increments 5.10%, across 5,284 unions. SME negotiated total increase 4.45%. Identifiable base-pay increase 3.56%.

## RENGO_2025_FIRST

**[2025 Spring Wage Negotiations, First Tally](https://www.jtuc-rengo.or.jp/activity/roudou/shuntou/2025/yokyu_kaito/kaito/press_no1.pdf)**

- Origin: Japanese Trade Union Confederation (Rengo); classification: `primary`; family: `rengo_wage_agreements`.
- Publication date: 2025-03-14; exact/minute UTC clock: null; relevant edition public-by bound: 2025-03-14T14:59:59Z.
- Version basis: Primary PDF opened turn35view7 and announcement transcript turn35view5: https://www.jtuc-rengo.or.jp/info/rengotv/kaiken/20250314_kaito01.html. Data tally10:00 JST is not a verified public-release minute.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Changing first-tally union sample; negotiated pay not realized economywide earnings. Total includes seniority increments. Post-January24 information must not enter January24 pre-event set.
- Bounded extraction: First weighted total negotiated increase including regular increments 5.46%. SME (<300 employees) negotiated total increase 5.09%. 760 unions, approximately 1.53 million members; tally as of March14 10:00 JST.

## RENGO_2026_FIRST

**[2026 Spring Wage Negotiations, First Tally](https://www.jtuc-rengo.or.jp/activity/roudou/shuntou/2026/yokyu_kaito/kaito/press_no1.pdf)**

- Origin: Japanese Trade Union Confederation (Rengo); classification: `primary`; family: `rengo_wage_agreements`.
- Publication date: 2026-03-23; exact/minute UTC clock: null; relevant edition public-by bound: 2026-03-23T14:59:59Z.
- Version basis: Primary PDF opened turn81view1/turn82view5/turn83view1. Publication date March23 independently recorded in Rengo archive opened turn73view2: https://www.jtuc-rengo.or.jp/activity/roudou/shuntou/2026/yokyu_kaito/. Graphpage3 confirms percentages and seniority-increment definition.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Data tally March23 10:00 JST is not public-release time. Changing union sample; do not infer fixed-cohort deceleration from first versus final tally. Negotiated increases are not realized economywide wages.
- Bounded extraction: First weighted total negotiated increase including regular/seniority increments 5.26%. SME (<300 employees) negotiated total increase 5.05%. Data as of March23, 2026, 10:00 JST.

## RENGO_2026_FINAL

**[2026 Spring Wage Negotiations, Seventh/Final Tally](https://www.jtuc-rengo.or.jp/activity/roudou/shuntou/2026/yokyu_kaito/kaito/press_no7.pdf)**

- Origin: Japanese Trade Union Confederation (Rengo); classification: `primary`; family: `rengo_wage_agreements`.
- Publication date: 2026-07-03; exact/minute UTC clock: null; relevant edition public-by bound: 2026-07-03T14:59:59Z.
- Version basis: Primary PDF opened turn74view4/turn79view0, printed July3 publication date; archive turn73view2 confirms July3.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Data tally July1 10:00 JST is not publication time. Total includes seniority increments. Identifiable base-pay subset differs from full sample. Archive notes correction to individual-pay-method other-category union/membership counts, other numbers unchanged, correction date unspecified.
- Bounded extraction: Weighted total negotiated increase 5.01%, JPY16400, 5368 unions. SME (<300 employees) negotiated total increase 4.69%. Identifiable base-pay improvement 3.50%, 3732 unions. Data as of July1, 2026, 10:00 JST.

## BOJ_2024_03

**[BOJ decision 2024-03-19](https://www.boj.or.jp/en/mopo/mpmdeci/state_2024/k240319a.htm)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2024-03-19; exact/minute UTC clock: 2024-03-19T03:35:00Z; relevant edition public-by bound: 2024-03-19T03:35:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Exit from negative-rate/YCC framework; pre-pressure domestic-policy context.
- Bounded extraction: Call-rate target 0–0.1%; vote majority. Release clock is announcement, not latent internal decision.

## BOJ_2024_07

**[BOJ decision 2024-07-31](https://www.boj.or.jp/en/mopo/mpmdeci/state_2024/k240731a.htm)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2024-07-31; exact/minute UTC clock: 2024-07-31T03:56:00Z; relevant edition public-by bound: 2024-07-31T03:56:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Effective August1. Simultaneous JGB purchase-reduction plan confounds yield reaction.
- Bounded extraction: Call-rate target 0.25%; vote 7–2. Release clock is announcement, not latent internal decision.

## BOJ_2025_01

**[BOJ decision 2025-01-24](https://www.boj.or.jp/en/mopo/mpmdeci/state_2025/k250124a.htm)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2025-01-24; exact/minute UTC clock: 2025-01-24T03:23:00Z; relevant edition public-by bound: 2025-01-24T03:23:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Effective January27; wage/labor-shortage and price pass-through rationale.
- Bounded extraction: Call-rate target 0.5%; vote 8–1. Release clock is announcement, not latent internal decision.

## BOJ_2025_05

**[BOJ decision 2025-05-01](https://www.boj.or.jp/en/mopo/mpmdeci/state_2025/k250501a.htm)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2025-05-01; exact/minute UTC clock: 2025-05-01T03:02:00Z; relevant edition public-by bound: 2025-05-01T03:02:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: No additional material caveat identified beyond general version/clock limitations.
- Bounded extraction: Call-rate target 0.5%; vote unanimous. Release clock is announcement, not latent internal decision.

## BOJ_2025_06

**[BOJ decision 2025-06-17](https://www.boj.or.jp/en/mopo/mpmdeci/state_2025/k250617a.htm)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2025-06-17; exact/minute UTC clock: null; relevant edition public-by bound: 2025-06-17T14:59:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: JGB runoff slows from April2026; separate instrument from policy-rate hold.
- Bounded extraction: Call-rate target 0.5%; vote unanimous. Release clock is announcement, not latent internal decision.

## BOJ_2025_07

**[BOJ decision 2025-07-31](https://www.boj.or.jp/en/mopo/mpmdeci/state_2025/k250731a.htm)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2025-07-31; exact/minute UTC clock: 2025-07-31T02:57:00Z; relevant edition public-by bound: 2025-07-31T02:57:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: No additional material caveat identified beyond general version/clock limitations.
- Bounded extraction: Call-rate target 0.5%; vote unanimous. Release clock is announcement, not latent internal decision.

## BOJ_2025_09

**[BOJ decision 2025-09-19](https://www.boj.or.jp/en/mopo/mpmdeci/state_2025/k250919a.htm)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2025-09-19; exact/minute UTC clock: 2025-09-19T03:47:00Z; relevant edition public-by bound: 2025-09-19T03:47:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Two hike dissents; ETF/J-REIT disposal announcement concurrent, not a pure rate event.
- Bounded extraction: Call-rate target 0.5%; vote 7–2. Release clock is announcement, not latent internal decision.

## BOJ_2025_10

**[BOJ decision 2025-10-30](https://www.boj.or.jp/en/mopo/mpmdeci/state_2025/k251030a.htm)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2025-10-30; exact/minute UTC clock: 2025-10-30T03:15:00Z; relevant edition public-by bound: 2025-10-30T03:15:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: No additional material caveat identified beyond general version/clock limitations.
- Bounded extraction: Call-rate target 0.5%; vote 7–2. Release clock is announcement, not latent internal decision.

## BOJ_2025_12

**[BOJ decision 2025-12-19](https://www.boj.or.jp/en/mopo/mpmdeci/state_2025/k251219a.htm)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2025-12-19; exact/minute UTC clock: 2025-12-19T03:19:00Z; relevant edition public-by bound: 2025-12-19T03:19:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Effective December22.
- Bounded extraction: Call-rate target 0.75%; vote unanimous. Release clock is announcement, not latent internal decision.

## BOJ_2026_01

**[BOJ decision 2026-01-23](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260123a.pdf)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2026-01-23; exact/minute UTC clock: 2026-01-23T03:07:00Z; relevant edition public-by bound: 2026-01-23T03:07:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Announcement clock verified in the official PDF release-schedule appendix.
- Bounded extraction: Call-rate target 0.75%; vote 8–1. Release clock is announcement, not latent internal decision.

## BOJ_2026_03

**[BOJ decision 2026-03-19](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260319a.pdf)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2026-03-19; exact/minute UTC clock: 2026-03-19T02:46:00Z; relevant edition public-by bound: 2026-03-19T02:46:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Announcement clock verified in the official PDF release-schedule appendix.
- Bounded extraction: Call-rate target 0.75%; vote 8–1. Release clock is announcement, not latent internal decision.

## BOJ_2026_06

**[BOJ decision 2026-06-16](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260616a.pdf)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2026-06-16; exact/minute UTC clock: 2026-06-16T03:19:00Z; relevant edition public-by bound: 2026-06-16T03:19:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Announcement clock verified in the official PDF release-schedule appendix.
- Bounded extraction: Call-rate target 1.0%; vote 7–1. Release clock is announcement, not latent internal decision.

## BOJ_2026_07

**[BOJ decision 2026-07-31](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260731a.pdf)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2026-07-31; exact/minute UTC clock: 2026-07-31T03:11:00Z; relevant edition public-by bound: 2026-07-31T03:11:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Announcement clock verified in the official PDF release-schedule appendix.
- Bounded extraction: Call-rate target 1.0%; vote 8–1. Release clock is announcement, not latent internal decision.

## BOJ_2026_09

**[BOJ decision 2026-09-18](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260918a.pdf)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2026-09-18; exact/minute UTC clock: 2026-09-18T02:54:00Z; relevant edition public-by bound: 2026-09-18T02:54:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Announcement clock verified in the official PDF release-schedule appendix.
- Bounded extraction: Call-rate target 1.25%; vote 7–2. Release clock is announcement, not latent internal decision.

## OUTLOOK_2025_01

**[BOJ Bank’s View 2025-01-24](https://www.boj.or.jp/en/mopo/outlook/gor2501a.pdf)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2025-01-24; exact/minute UTC clock: 2025-01-24T03:23:00Z; relevant edition public-by bound: 2025-01-24T03:23:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Bank’s View vintage only. Full Outlook Report published later and not substituted. Forecasts are conditional BOJ assessments, not realized data.
- Bounded extraction: FY2025/26 core CPI median forecasts 2.4%/2.0%.

## OUTLOOK_2025_04

**[BOJ Bank’s View 2025-05-01](https://www.boj.or.jp/en/mopo/outlook/gor2504a.pdf)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2025-05-01; exact/minute UTC clock: 2025-05-01T03:02:00Z; relevant edition public-by bound: 2025-05-01T03:02:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Bank’s View vintage only. Full Outlook Report published later and not substituted. Forecasts are conditional BOJ assessments, not realized data.
- Bounded extraction: FY2025 GDP 0.5%, FY2026 0.7%; core CPI 2.2%/1.7%.

## OUTLOOK_2025_07

**[BOJ Bank’s View 2025-07-31](https://www.boj.or.jp/en/mopo/outlook/gor2507a.pdf)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2025-07-31; exact/minute UTC clock: 2025-07-31T02:57:00Z; relevant edition public-by bound: 2025-07-31T02:57:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Bank’s View vintage only. Full Outlook Report published later and not substituted. Forecasts are conditional BOJ assessments, not realized data.
- Bounded extraction: FY2025 core CPI forecast 2.7%; food effects and sluggish underlying inflation distinguished.

## OUTLOOK_2025_10

**[BOJ Bank’s View 2025-10-30](https://www.boj.or.jp/en/mopo/outlook/gor2510a.pdf)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2025-10-30; exact/minute UTC clock: 2025-10-30T03:15:00Z; relevant edition public-by bound: 2025-10-30T03:15:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Bank’s View vintage only. Full Outlook Report published later and not substituted. Forecasts are conditional BOJ assessments, not realized data.
- Bounded extraction: FY2025 GDP 0.7%, core CPI 2.7%.

## OUTLOOK_2026_01

**[BOJ Bank’s View 2026-01-23](https://www.boj.or.jp/en/mopo/outlook/gor2601a.pdf)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2026-01-23; exact/minute UTC clock: 2026-01-23T03:07:00Z; relevant edition public-by bound: 2026-01-23T03:07:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Bank’s View vintage only. Full Outlook Report published later and not substituted. Forecasts are conditional BOJ assessments, not realized data.
- Bounded extraction: Conditional further normalization based on domestic outlook.

## OUTLOOK_2026_07

**[BOJ Bank’s View 2026-07-31](https://www.boj.or.jp/en/mopo/outlook/gor2607a.pdf)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2026-07-31; exact/minute UTC clock: 2026-07-31T03:11:00Z; relevant edition public-by bound: 2026-07-31T03:11:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Bank’s View vintage only. Full Outlook Report published later and not substituted. Forecasts are conditional BOJ assessments, not realized data.
- Bounded extraction: FY2026 GDP forecast 0.6%, core CPI 2.5%; energy relief lowers near-term CPI forecast.

## BOJ_OPINIONS_2025_07

**[July 2025 Summary of Opinions, released August8](https://www.boj.or.jp/en/mopo/mpmsche_minu/opinion_2025/opi250731.htm)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2025-08-08; exact/minute UTC clock: 2025-08-07T23:50:00Z; relevant edition public-by bound: 2025-08-07T23:50:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Opinions are individual views without speaker/vote attribution, not a board commitment. Meeting date July31 is not publication date.
- Bounded extraction: Public discussion of resuming hikes by year-end after assessing tariff effects.

## BOJ_OPINIONS_2026_09

**[September 2026 Summary of Opinions, released October1](https://www.boj.or.jp/en/mopo/mpmsche_minu/opinion_2026/opi260918.pdf)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2026-10-01; exact/minute UTC clock: 2026-09-30T23:50:00Z; relevant edition public-by bound: 2026-09-30T23:50:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Ex-post mechanism evidence only for September18.
- Bounded extraction: Greater resilience cited for shorter interval; domestic-data rationale and government cautions both present.

## RX_2024_07_PRE

**[Pre-BOJ market pricing July30](https://www.reuters.com/markets/currencies/dollar-yen-hold-tight-ranges-ahead-boj-fed-2024-07-30/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2024_07_pre`.
- Publication date: 2024-07-30; exact/minute UTC clock: 2024-07-30T11:09:00Z; relevant edition public-by bound: 2024-07-30T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: 55% concerns 10bp, not 25bp. Last edition used; earlier63% snippet is not simultaneous.
- Bounded extraction: Final text 19:15UTC: 55% probability of a 10bp hike; USDJPY153.29.

## RX_2024_07_POST

**[Japan yields and bank shares after July2024 hike](https://www.reuters.com/markets/asia/japan-yields-scale-15-year-peaks-bank-shares-surge-boj-hikes-rates-2024-07-31/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2024_07_post`.
- Publication date: 2024-07-31; exact/minute UTC clock: 2024-07-31T06:45:00Z; relevant edition public-by bound: 2024-07-31T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Extrema and later FX quote, not synchronized minute-window endpoints; simultaneous QT, leaks and Fed meeting.
- Bounded extraction: 2y maximum0.455% (+8.5bp); 10y1.06% (+6.5bp); later USDJPY150.61.

## RX_2025_01_PRE

**[January23 pre-BOJ pricing](https://www.reuters.com/markets/asia/global-markets-view-asia-graphic-2025-01-23/)**

- Origin: Reuters; classification: `commentary`; family: `reuters_rx_2025_01_pre`.
- Publication date: 2025-01-23; exact/minute UTC clock: 2025-01-23T21:48:00Z; relevant edition public-by bound: 2025-01-23T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Reuters market commentary reporting prices; not an independently downloaded OIS curve.
- Bounded extraction: Market pricing around95% for quarter-point hike.

## RX_2025_01_POST

**[Yen and JGB response January24](https://www.reuters.com/world/japan/yen-gains-bond-yields-rise-after-boj-hikes-rates-2025-01-24/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2025_01_post`.
- Publication date: 2025-01-24; exact/minute UTC clock: 2025-01-24T06:47:00Z; relevant edition public-by bound: 2025-01-24T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Article prices extend to07:42GMT; statement and press-conference windows differ.
- Bounded extraction: 2y maximum0.725% (+3bp), later0.715%; USDJPY154.845 then155.56.

## RX_2025_05_POST

**[Yen and JGB response to May1 growth forecast cuts](https://www.streetinsider.com/Reuters/Yen%2Bslides%2Bwith%2BJGB%2Byields%2Bafter%2BBOJ%2Bcuts%2Bgrowth%2Bforecasts/24720875.html)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2025_05_post`.
- Publication date: 2025-05-01; exact/minute UTC clock: 2025-05-01T05:20:00Z; relevant edition public-by bound: 2025-05-01T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Reuters syndication, same origin; qualitative hold expectation reported after event.
- Bounded extraction: 10y yield1.26%; yen down as much as0.6%.

## RX_2025_07_PRE

**[July23 economist survey and futures pricing](https://www.reuters.com/sustainability/sustainable-finance-reporting/boj-hike-rates-this-year-despite-uncertainties-economists-predict-2025-07-23/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2025_07_pre`.
- Publication date: 2025-07-23; exact/minute UTC clock: 2025-07-23T04:06:00Z; relevant edition public-by bound: 2025-07-23T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Survey July11–22, many responses before July20 election; economist shares are not market probabilities.
- Bounded extraction: 60/72 economists expected no July/September change; rate futures14bp additional tightening by year-end.

## RX_2025_08_PRESSURE

**[Bessent Bloomberg interview: BOJ behind inflation curve](https://www.streetinsider.com/Reuters/Bessent%2Bsays%2BBOJ%2Bis%2Bbehind%2Bthe%2Bcurve%2Bon%2Binflation%2C%2Blikely%2Bto%2Bhike%2Brates%2C%2Bin%2BBloomberg%2Binterview/25198471.html)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2025_08_pressure`.
- Publication date: 2025-08-13; exact/minute UTC clock: null; relevant edition public-by bound: 2025-08-14T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Reuters reporting an interview. Exact broadcast, first dissemination and private Ueda exchange clocks unverified; conservative edition bound used.
- Bounded extraction: Bessent called BOJ behind the curve and expected hikes after speaking with Ueda.

## RX_2025_08_JGB

**[JGBs fall after Bessent comments](https://economictimes.indiatimes.com/markets/bonds/jgbs-fall-as-bessents-behind-the-curve-comments-drive-boj-rate-hike-bets/articleshow/123297096.cms)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2025_08_jgb`.
- Publication date: 2025-08-14; exact/minute UTC clock: 2025-08-14T06:20:00Z; relevant edition public-by bound: 2025-08-14T06:20:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Reuters syndication; weak auction and thin holiday liquidity concurrent; observation after remarks, not pre-event OIS.
- Bounded extraction: 5y yield1.10% (+3.5bp), 10y1.545% (+3bp); swaps62% December25bp hike, under50% before then.

## MUFG_2025_08

**[FX Daily Snapshot August14 2025](https://www.mufgresearch.com/fx/fx-daily-snapshot-14-aug-2025/)**

- Origin: MUFG; classification: `research`; family: `mufg_research`.
- Publication date: 2025-08-14; exact/minute UTC clock: null; relevant edition public-by bound: 2025-08-14T22:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Contemporaneous bank interpretation; not independent proof of policy causation.
- Bounded extraction: Yen strength accompanied BOJ signals and rising U.S. easing expectations.

## RX_2025_10_PRE

**[October22 survey and market pricing](https://www.reuters.com/world/asia-pacific/boj-poised-hike-interest-rates-q4-majority-economists-say-2025-10-22/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2025_10_pre`.
- Publication date: 2025-10-22; exact/minute UTC clock: 2025-10-22T04:13:00Z; relevant edition public-by bound: 2025-10-22T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Different probability and survey objects; old observation, not immediately pre-October29.
- Bounded extraction: Markets roughly40% chance of hike by year-end; 45/75 economists expect Q4 hike.

## RX_2025_10_PRESSURE

**[Bessent urges Japan government to allow BOJ policy space](https://www.reuters.com/world/asia-pacific/us-treasurys-bessent-urges-japan-government-allow-boj-policy-space-2025-10-29/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2025_10_pressure`.
- Publication date: 2025-10-29; exact/minute UTC clock: null; relevant edition public-by bound: 2025-10-29T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Can enable BOJ against domestic political restraint; no guaranteed next-day rate decision.
- Bounded extraction: U.S. asked government to permit BOJ policy space; USDJPY151.59 in report.

## RX_2025_10_POST

**[October30 hold after raised hawkish expectations](https://www.reuters.com/world/asia-pacific/boj-seen-keeping-rates-hold-yen-pressure-looms-2025-10-29/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2025_10_post`.
- Publication date: 2025-10-29; exact/minute UTC clock: null; relevant edition public-by bound: 2025-10-30T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Current post-decision body unavailable to October29 cut; original URL date does not license leakage.
- Bounded extraction: Report links hawkish expectations to Bessent; BOJ held, Ueda sought wage evidence; USDJPY153.56.

## RX_2025_12_PRE

**[Markets price December hike](https://www.reuters.com/sustainability/sustainable-finance-reporting/markets-anxious-over-japans-risk-negative-spiral-top-bank-mufg-exec-says-2025-12-09/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2025_12_pre`.
- Publication date: 2025-12-09; exact/minute UTC clock: null; relevant edition public-by bound: 2025-12-10T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Not the separate90%=63/70 economist survey.
- Bounded extraction: December10 edition reports90% market-implied chance of December hike.

## RX_2025_12_POST

**[Global markets December19](https://www.reuters.com/world/china/global-markets-global-markets-2025-12-19/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2025_12_post`.
- Publication date: 2025-12-19; exact/minute UTC clock: 2025-12-19T21:45:00Z; relevant edition public-by bound: 2025-12-19T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Full-session move, not a minute-window causal estimate.
- Bounded extraction: USDJPY157.69, dollar+1.38% for session despite BOJ hike.

## RX_2026_01_CHECK

**[NYFed dollar/yen rate checks](https://www.reuters.com/world/asia-pacific/ny-fed-carried-out-dollaryen-rate-checks-source-says-2026-01-23/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_01_check`.
- Publication date: 2026-01-23; exact/minute UTC clock: 2026-01-23T22:30:00Z; relevant edition public-by bound: 2026-01-23T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Reported quotes, not executed intervention. Tokyo movement before NY midday is a separate window.
- Bounded extraction: One source reports NYFed indicative quote inquiries around New York midday; USDJPY157.50 to155.66, later155.85.

## RX_2026_01_FX

**[January23 two yen spikes](https://www.reuters.com/world/asia-pacific/dollar-set-worst-week-year-yen-pressured-ahead-boj-2026-01-23/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_01_fx`.
- Publication date: 2026-01-23; exact/minute UTC clock: 2026-01-23T20:50:00Z; relevant edition public-by bound: 2026-01-23T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Whole-day return cannot isolate U.S. involvement.
- Bounded extraction: Tokyo USDJPY157.3 after press conference; later New York strengthening.

## RX_2026_01_HURDLE

**[Analysts discuss hurdles to coordinated yen action](https://www.reuters.com/world/asia-pacific/us-rate-check-masks-stiff-hurdle-coordinated-yen-intervention-2026-01-26/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_01_hurdle`.
- Publication date: 2026-01-26; exact/minute UTC clock: null; relevant edition public-by bound: 2026-01-27T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: January27 refile; analyst interpretation of preferences is not government veto, legal prohibition or evidence of Treasury sales.

## RX_2026_02_INITIATIVE

**[Nikkei account of U.S.-initiated January checks](https://www.reuters.com/world/asia-pacific/us-took-initiative-january-yen-rate-checks-nikkei-reports-2026-02-23/)**

- Origin: Reuters; classification: `independent_reporting`; family: `nikkei_january_ratecheck`.
- Publication date: 2026-02-23; exact/minute UTC clock: 2026-02-23T23:58:00Z; relevant edition public-by bound: 2026-02-24T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Reuters relays Nikkei; one underlying reporting lineage. Ex-post January mechanism only.
- Bounded extraction: Later anonymous-source account says no Japanese request for January checks; joint purchases contemplated if requested.

## RX_2026_04_ACTION

**[Japan April30 intervention reported](https://www.reuters.com/business/finance/japan-yen-surges-2-officials-issue-strongest-intervention-warning-yet-2026-04-30/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_04_action`.
- Publication date: 2026-04-30; exact/minute UTC clock: 2026-04-30T11:14:00Z; relevant edition public-by bound: 2026-04-30T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Amount unknown then; absence of U.S. participation not established until later official accounting.
- Bounded extraction: Anonymous government and market sources report intervention; USDJPY160.725 to155.5, later156.355.

## RX_2026_04_WARNING

**[Japan warns decisive FX action nearing](https://www.reuters.com/world/asia-pacific/japan-says-decisive-fx-action-nearing-strongest-warning-yet-yen-spikes-2026-04-30/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_04_warning`.
- Publication date: 2026-04-30; exact/minute UTC clock: 2026-04-30T09:58:00Z; relevant edition public-by bound: 2026-04-30T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Warning and report of action must retain distinct states.
- Bounded extraction: Katayama declined to identify possible action as solo or joint.

## RX_2026_08_JOINT

**[Japan and U.S. confirm joint yen intervention](https://www.reuters.com/world/asia-pacific/japan-vow-coordination-with-us-weak-yen-historic-battle-2026-08-02/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_08_joint`.
- Publication date: 2026-08-02; exact/minute UTC clock: 2026-08-02T21:01:00Z; relevant edition public-by bound: 2026-08-03T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Current Aug3 edition used, not original Aug2 body. FIMA-utilized sentence is disputed and not admitted as verified draw. Actual U.S. amount unknown.
- Bounded extraction: On-record MOF/Bessent confirmation of Friday joint action; euro sales attributed to three sources.

## RX_2026_08_ORIGIN

**[How the U.S.–Japan intervention pact came together](https://www.reuters.com/world/asia-pacific/how-us-japan-pact-hit-yen-speculators-came-together-2026-08-03/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_08_origin`.
- Publication date: 2026-08-03; exact/minute UTC clock: 2026-08-03T09:23:00Z; relevant edition public-by bound: 2026-08-03T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Retrospective sourced reconstruction. A photographed $5–10bn plan is not execution amount.
- Bounded extraction: Months of talks; July30 Japanese action followed by joint July31 action; BOJ guidance concurrent.

## RX_2026_08_FIMA_FIRST

**[Bessent seeks larger backstop and stands ready for more intervention](https://www.reuters.com/world/asia-pacific/bessent-ready-repeat-joint-yen-intervention-urges-bigger-fed-backstop-2026-08-03/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_08_fima_first`.
- Publication date: 2026-08-03; exact/minute UTC clock: 2026-08-03T00:40:34Z; relevant edition public-by bound: 2026-08-03T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Exact X clock unverified; August4 interview is a reiteration.
- Bounded extraction: Reports August2 X proposal to enlarge FIMA.

## RX_2026_08_FIMA_REPEAT

**[Bessent CNBC reiteration on upsizing FIMA](https://www.streetinsider.com/Reuters/US%2BTreasurys%2BBessent:%2BReasonable%2Bfor%2BFed%2Bto%2Bconsider%2Bupsizing%2BFIMA/26862443.html)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_08_fima_repeat`.
- Publication date: 2026-08-04; exact/minute UTC clock: 2026-08-04T12:33:00Z; relevant edition public-by bound: 2026-08-04T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Reuters syndication of CNBC remarks; interview start not verified.
- Bounded extraction: Treasury advocacy for Fed consideration; no approval or draw receipt.

## RX_2026_08_SUPPORT

**[Bessent support remarks and yen response August4](https://www.reuters.com/world/asia-pacific/us-treasury-secretary-bessent-will-do-whatever-it-takes-support-japan-2026-08-04/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_08_support`.
- Publication date: 2026-08-04; exact/minute UTC clock: 2026-08-04T13:19:00Z; relevant edition public-by bound: 2026-08-04T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Broad reported before/after observations; no synchronized tick window.
- Bounded extraction: USDJPY around158 before remarks and157.55 after.

## RX_2026_08_PRICING

**[September hike pricing after intervention](https://www.reuters.com/world/asia-pacific/rate-hike-bets-leave-yens-post-intervention-gains-bojs-mercy-2026-08-13/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_08_pricing`.
- Publication date: 2026-08-13; exact/minute UTC clock: 2026-08-13T08:01:00Z; relevant edition public-by bound: 2026-08-13T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: 52 percentage-point composite repricing is not an estimate of U.S. causality; broker1.75% terminal forecast is not OIS.
- Bounded extraction: Tokyo Tanshi September-hike probability76% versus24% July30.

## RX_2026_08_LETTER

**[Bessent explains intervention assets and disorderly-market concerns](https://www.reuters.com/business/finance/bessent-says-disorderly-yen-moves-can-destabilize-global-markets-2026-08-29/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_08_letter`.
- Publication date: 2026-08-29; exact/minute UTC clock: null; relevant edition public-by bound: 2026-08-29T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Original letter not retrieved; do not treat report as primary transaction ledger or infer size.
- Bounded extraction: Reports August27 letter posted August28: ESF foreign-currency assets exchanged for yen, not direct U.S. dollar sale or loan.

## RX_2026_08_31

**[Bessent selective-information warning about Japan action](https://www.reuters.com/world/asia-pacific/bessent-says-he-believes-japan-will-take-action-leading-stronger-yen-2026-08-31/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_08_31`.
- Publication date: 2026-08-31; exact/minute UTC clock: 2026-08-31T15:05:53Z; relevant edition public-by bound: 2026-08-31T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Claim of private information is rhetoric; content and decisiveness unknown.
- Bounded extraction: Public CNBC statement precedes September1 readout; USDJPY159.75; September hike nearly priced.

## RX_2026_09_READOUT

**[Bessent/Ueda meeting readout reported September1](https://www.investing.com/news/economy-news/bessent-meets-bojs-ueda-calls-for-sound-policy-to-avoid-currency-volatility-treasury-says-4884388)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_09_readout`.
- Publication date: 2026-09-01; exact/minute UTC clock: 2026-09-01T16:18:00Z; relevant edition public-by bound: 2026-09-02T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Retrieved edition updatedSeptember2: full current wire excluded at September2 00UTC cut. Only primary readout fact confirmed by September1 dissemination bound enters that cut.
- Bounded extraction: Treasury support for sound monetary policy; September hike already nearly priced.

## RX_2026_09_BONDS

**[September1 global bond rout](https://www.reuters.com/world/asia-pacific/global-bond-rout-deepens-japan-yield-hits-key-threshold-2026-09-01/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_09_bonds`.
- Publication date: 2026-09-01; exact/minute UTC clock: 2026-09-01T07:27:00Z; relevant edition public-by bound: 2026-09-02T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Early headline predates16:18 readout. Current later prices not a synchronized UST-control series.
- Bounded extraction: 10y JGB reached3% amid global bond rout.

## RX_2026_09_PRIVATE

**[Later reconstruction of U.S. conditionality](https://www.reuters.com/world/asia-pacific/how-bessent-americas-bond-salesman-cornered-japan-big-spending-2026-09-17/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_09_private`.
- Publication date: 2026-09-17; exact/minute UTC clock: 2026-09-17T23:04:00Z; relevant edition public-by bound: 2026-09-18T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Retrieved edition includes September18 outcome; excluded from all earlier decision-time inputs, including September18. Officials did not confirm specific private discussions; Treasury says Japan makes monetary decisions.
- Bounded extraction: Anonymous-source reconstruction of May pressure and June22 requested assistance with fiscal/monetary-consistency conditions.

## RX_2026_09_MARKET

**[Early September18 market reaction](https://www.thestandard.com.hk/finance/article/343180/Yen-sinks-sending-Japan-stocks-surging-as-BOJ-hike-draws-two-dissents)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_09_market`.
- Publication date: 2026-09-18; exact/minute UTC clock: 2026-09-18T06:57:00Z; relevant edition public-by bound: 2026-09-18T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Reuters syndicated stale early edition: page posted after06:30 presser while body says upcoming. Use body price clock, not page time; FX quote not explicitly at04:42.
- Bounded extraction: 2y JGB1.835% (-2.5bp) at04:42UTC; USDJPY157.085, yen roughly0.7% weaker; two dissents.

## TREASURY_2025_06

**[June2025 Treasury FX report](https://home.treasury.gov/system/files/136/June-2025-FX-Report.pdf)**

- Origin: U.S. Treasury; classification: `primary`; family: `us_treasury_fx`.
- Publication date: 2025-06-05; exact/minute UTC clock: null; relevant edition public-by bound: 2025-06-06T03:59:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Policy preference, not command; release day confirmed by sb0157 press release.
- Bounded extraction: BOJ tightening should continue in response to domestic growth/inflation; exchange-rate intervention exceptional with consultation.

## TREASURY_2025_09

**[U.S.–Japan finance minister joint statement](https://home.treasury.gov/news/press-releases/sb0245)**

- Origin: U.S. Treasury / Japan MOF; classification: `primary`; family: `us_japan_joint_fx`.
- Publication date: 2025-09-11; exact/minute UTC clock: null; relevant edition public-by bound: 2025-09-12T03:59:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Monthly FX disclosure and consultation; not blanket approval for any intervention.
- Bounded extraction: Market-determined exchange rates; monetary/fiscal policy for domestic objectives; intervention against disorderly appreciation or depreciation.

## TREASURY_2026_08_READOUT

**[Bessent/Ueda Asheville meeting readout](https://home.treasury.gov/news/press-releases/sb0619)**

- Origin: U.S. Treasury; classification: `primary`; family: `us_treasury_bilateral`.
- Publication date: 2026-08-30; exact/minute UTC clock: null; relevant edition public-by bound: 2026-09-01T16:18:00Z.
- Version basis: Official readout body and September1 wire dissemination bound; exact first-public clock unresolved.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Page dateline identifies meeting/date, not verified first publication. Public by September1 Reuters dissemination; no BOJ rate-number commitment.
- Bounded extraction: August30 meeting; support for sound monetary formulation/communication, inflation anchoring and yen stability.

## MOF_2026_01

**[Japan monthly FX intervention January30](https://www.mof.go.jp/english/policy/international_policy/reference/feio/monthly/20260130e.html)**

- Origin: Japan Ministry of Finance; classification: `primary`; family: `japan_mof_fx`.
- Publication date: 2026-01-30; exact/minute UTC clock: null; relevant edition public-by bound: 2026-01-30T14:59:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: No additional material caveat identified beyond general version/clock limitations.
- Bounded extraction: JPY0 intervention December29–January28.

## MOF_2026_05

**[Japan monthly FX intervention May29](https://www.mof.go.jp/english/policy/international_policy/reference/feio/monthly/20260529e.html)**

- Origin: Japan Ministry of Finance; classification: `primary`; family: `japan_mof_fx`.
- Publication date: 2026-05-29; exact/minute UTC clock: null; relevant edition public-by bound: 2026-05-29T14:59:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: No additional material caveat identified beyond general version/clock limitations.
- Bounded extraction: JPY11734.9 billion April28–May27.

## MOF_2026_Q2

**[Japan daily Q2 intervention release August7](https://www.mof.go.jp/english/policy/international_policy/reference/feio/quarter/2026_2Qe.html)**

- Origin: Japan Ministry of Finance; classification: `primary`; family: `japan_mof_fx`.
- Publication date: 2026-08-07; exact/minute UTC clock: null; relevant edition public-by bound: 2026-08-07T14:59:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Rounded daily entries sum11734.8bn. Daily allocations unavailable beforeAugust7.
- Bounded extraction: April30 JPY6278.7bn; May4 JPY780.2bn; May6 JPY4675.9bn; official total JPY11734.9bn.

## MOF_2026_08

**[Japan monthly FX intervention August28](https://www.mof.go.jp/english/policy/international_policy/reference/feio/monthly/20260828e.html)**

- Origin: Japan Ministry of Finance; classification: `primary`; family: `japan_mof_fx`.
- Publication date: 2026-08-28; exact/minute UTC clock: null; relevant edition public-by bound: 2026-08-28T14:59:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Not July31-only amount, not U.S. amount; Q3 daily allocation unavailable by cutoff.
- Bounded extraction: Japan intervention JPY15399.3bn during July30–August26.

## MOF_2026_08_STATEMENT

**[MOF joint-intervention statement, indexed primary](https://www.mof.go.jp/english/public_relations/statement/others/20260803073000.html)**

- Origin: Japan Ministry of Finance; classification: `primary`; family: `japan_mof_fx`.
- Publication date: 2026-08-03; exact/minute UTC clock: null; relevant edition public-by bound: 2026-08-03T14:59:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: indexed_primary_only; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Full primary fetch failed, including one alternate Japanese path. Indexed primary text only; on-record Reuters announcement supplies independent access fallback, not an independent event.
- Bounded extraction: Indexed text dates joint yen buying July31 U.S.Eastern time and describes future FIMA utilization.

## NYFED_2026_Q1

**[NYFed Q12026 Treasury/Fed FX operations report](https://www.newyorkfed.org/medialibrary/media/newsevents/news/markets/2026/q1-2026-fx-quarterly-report.pdf)**

- Origin: Federal Reserve Bank of New York; classification: `primary`; family: `nyfed_fx_operations`.
- Publication date: 2026-05-14; exact/minute UTC clock: null; relevant edition public-by bound: 2026-05-15T03:59:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Later official operational confirmation, not contemporaneous January/April input.
- Bounded extraction: No U.S. Treasury or Federal Reserve FX intervention in covered quarter. January indicative quotes solely for Treasury fiscal agency; yen appreciated1.7% on report day.

## NYFED_2026_Q2

**[NYFed Q22026 Treasury/Fed FX operations report](https://www.newyorkfed.org/medialibrary/media/newsevents/news/markets/2026/q2-2026-fx-quarterly-report.pdf)**

- Origin: Federal Reserve Bank of New York; classification: `primary`; family: `nyfed_fx_operations`.
- Publication date: 2026-08-13; exact/minute UTC clock: null; relevant edition public-by bound: 2026-08-14T03:59:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Later official operational confirmation, not contemporaneous January/April input.
- Bounded extraction: No U.S. Treasury or Federal Reserve FX intervention in covered quarter. Japan intervention appreciation peak-to-trough up to3.5%, more than fully retraced.

## NYFED_REPORT_INDEX

**[NYFed quarterly FX report publication index](https://www.newyorkfed.org/markets/quar_reports.html)**

- Origin: Federal Reserve Bank of New York; classification: `primary`; family: `nyfed_fx_operations`.
- Publication date: null; exact/minute UTC clock: null; relevant edition public-by bound: null.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Current index snapshot, not historical input.
- Bounded extraction: Q1 publishedMay14, Q2August13; Q3 report not listed as of research cutoff.

## FIMA_FAQ

**[FIMA repo FAQ, February2024 version](https://www.federalreserve.gov/monetarypolicy/fima-repo-facility-faqs.htm)**

- Origin: Federal Reserve Board; classification: `primary`; family: `fed_fima_rules`.
- Publication date: 2024-02-21; exact/minute UTC clock: null; relevant edition public-by bound: 2024-02-22T04:59:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Mechanism/availability, not proof of Japan access or draw.
- Bounded extraction: Dollar repo against U.S.Treasuries; public usage via H.4.1; no exchange-rate risk to Fed.

## FOMC_2026_DIRECTIVE

**[FOMC continuing directives effective January27 2026](https://www.federalreserve.gov/monetarypolicy/files/FOMC_AuthorizationsContinuingDirectivesOMOs.pdf)**

- Origin: Federal Open Market Committee; classification: `primary`; family: `fed_fima_rules`.
- Publication date: null; exact/minute UTC clock: null; relevant edition public-by bound: null.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Effective date is not separately verified initial public posting date. Used for as-of legal mechanism audit only, not certified August decision inputs. Neither proves approved enlargement.
- Bounded extraction: USD60bn total outstanding per counterparty; overnight SRP rate or7-day OIS+25bp; Foreign Currency Subcommittee may alter counterparty limit/access/rate/maturity.

## H41_2026_07_30

**[Federal Reserve H.4.1 2026-07-30](https://www.federalreserve.gov/releases/h41/20260730/)**

- Origin: Federal Reserve Board; classification: `primary`; family: `fed_balance_sheet`.
- Publication date: 2026-07-30; exact/minute UTC clock: 2026-07-30T20:30:00Z; relevant edition public-by bound: 2026-07-30T20:30:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Million-dollar resolution; not a zero-to-the-cent assertion. Liability-side foreign reverse-repo pool is a different instrument.
- Bounded extraction: Foreign-official asset repos rounded USD0m daily-average week ending2026-07-29 and on that Wednesday.

## H41_2026_08_06

**[Federal Reserve H.4.1 2026-08-06](https://www.federalreserve.gov/releases/h41/20260806/)**

- Origin: Federal Reserve Board; classification: `primary`; family: `fed_balance_sheet`.
- Publication date: 2026-08-06; exact/minute UTC clock: 2026-08-06T20:30:00Z; relevant edition public-by bound: 2026-08-06T20:30:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Million-dollar resolution; not a zero-to-the-cent assertion. Liability-side foreign reverse-repo pool is a different instrument.
- Bounded extraction: Foreign-official asset repos rounded USD0m daily-average week ending2026-08-05 and on that Wednesday.

## H41_2026_08_13

**[Federal Reserve H.4.1 2026-08-13](https://www.federalreserve.gov/releases/h41/20260813/)**

- Origin: Federal Reserve Board; classification: `primary`; family: `fed_balance_sheet`.
- Publication date: 2026-08-13; exact/minute UTC clock: 2026-08-13T20:30:00Z; relevant edition public-by bound: 2026-08-13T20:30:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Million-dollar resolution; not a zero-to-the-cent assertion. Liability-side foreign reverse-repo pool is a different instrument.
- Bounded extraction: Foreign-official asset repos rounded USD0m daily-average week ending2026-08-12 and on that Wednesday.

## BOJ_2025_03

**[BOJ decision 2025-03-19](https://www.boj.or.jp/en/mopo/mpmdeci/state_2025/k250319a.htm)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2025-03-19; exact/minute UTC clock: 2025-03-19T02:25:00Z; relevant edition public-by bound: 2025-03-19T02:25:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Domestic wage/price mechanism and explicit trade-policy uncertainty before the May decision.
- Bounded extraction: Call-rate target 0.5%; vote unanimous. Release clock is announcement, not latent internal decision.

## BOJ_2026_04

**[BOJ decision 2026-04-28](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260428a.pdf)**

- Origin: Bank of Japan; classification: `primary`; family: `boj_policy`.
- Publication date: 2026-04-28; exact/minute UTC clock: 2026-04-28T03:04:00Z; relevant edition public-by bound: 2026-04-28T03:04:59Z.
- Version basis: Dated official release opened; not a cryptographically archived historical download.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Three dissents proposed1%; predates the May private-pressure episode.
- Bounded extraction: Call-rate target 0.75%; vote 6–3. Release clock is announcement, not latent internal decision.

## RX_2026_04_POLL

**[April16 pre-May BOJ expectations survey](https://www.reuters.com/world/asia-pacific/boj-hike-rates-by-june-war-fuelled-inflation-risks-mount-2026-04-16/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_04_poll`.
- Publication date: 2026-04-16; exact/minute UTC clock: 2026-04-16T04:07:00Z; relevant edition public-by bound: 2026-04-16T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Economist share, not OIS probability. Predates May12 but follows earlier U.S. involvement; cannot establish a wholly untreated baseline.
- Bounded extraction: April7–14 survey:46/71 economists (65%) expected1%byend-June.

## RX_2026_04_BOJ

**[April28 hawkish hold and June anticipation](https://www.reuters.com/world/asia-pacific/bank-japan-set-keep-rates-steady-iran-war-clouds-outlook-2026-04-27/)**

- Origin: Reuters; classification: `independent_reporting`; family: `reuters_rx_2026_04_boj`.
- Publication date: 2026-04-27; exact/minute UTC clock: 2026-04-27T21:05:00Z; relevant edition public-by bound: 2026-04-28T23:59:59Z.
- Version basis: Publisher publication/update metadata for retrieved edition; no contemporaneous content hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Current body includes April28 decision and press conference; cannot enter an April27 cut. No numeric June OIS provided.
- Bounded extraction: Three hike dissents; yen rose as investors anticipated possible June hike.

## CPI_2026_08

**[August2026 national CPI, September18 original release](https://www.stat.go.jp/data/cpi/sokuhou/tsuki/pdf/zenkoku.pdf)**

- Origin: Statistics Bureau of Japan; classification: `primary`; family: `statistics_bureau_cpi`.
- Publication date: 2026-09-18; exact/minute UTC clock: 2026-09-17T23:30:00Z; relevant edition public-by bound: 2026-09-17T23:30:59Z.
- Version basis: Dated original PDF opened by japan_domestic; official e-Stat release calendar line1226 establishes September18 08:30JST. No historical byte hash.
- Access: opened_full; accessed 2026-10-07 UTC; input eligibility requires the row’s additional time gate.
- Caveat: Latest PDF is mutable: retrieved datedSeptember18 August vintage explicitly preserved here. Official e-Stat calendar gives08:30JST; not eligible for August30/September1.
- Bounded extraction: Headline1.9%, ex-fresh-food1.7%, ex-fresh-food-and-energy1.9% y/y, 2025 base.

