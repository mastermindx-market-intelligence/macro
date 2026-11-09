STATUS: COMPLETE

# 1. STATUS + SCOPE

This is the Rule 4 era-treatment record for Cycle candidate (a), records only. It creates no window, return, outcome, ledger, pilot, or relabeling.

**Why in scope.** `R6-B16-01` §1 admits `NEWORDER` (order flow), `ISRATIO` (inventory cycle), and `AWHMAN` (manufacturing labor utilization) as the three independent mechanisms, and puts `AMTMUO` and `AMTMVS` in the same order-book family (`research/prophet_v4/r6_program/rulings/R6-B16-01_ADMISSION_2026-09-23.md:10` via PR #7842 because it is absent at `origin/main`). `R6-B16-01` §3 item 2 orders this record for those five legs (`...:26`).

The other three are in scope because `config.yml` configures them for the candidate (a) cycle/bottleneck maps: `CMRMTSPL` at `config.yml:368`; `INDPRO` at `config.yml:127`; and `MNFCTRIRSA` at `config.yml:155`. The candidate-(a) semantic constraints are recorded at `research/prophet_v4/r6_program/wave2/D03_SOURCE_READINESS_MATRIX_2026-09-23.md:85`–`:90` (via PR #7842): broad capital-goods and manufacturing series are macro inputs, never machinery subthemes.

**Evidence kinds (verbatim from this lane's law):**

1. `RECORDED (an in-repo record states it: quote path:line)`
2. `DETERMINED-FROM-PUBLISHED-NOTES (you fetched the series' own published notes/methodology page with curl -sL <url> at a stated UTC time and quote ≤ 25 words with the URL)`

Rule 4 itself is quoted verbatim at `research/prophet_v4/r6_program/rulings/R6-D03-01_SOURCE_READINESS_SCOPE_2026-09-23.md:19`: "every NAICS/benchmark/reclassification/seasonal-method/discontinuity is dated and handled by era split, declared diagnostic-only splice, or exclusion. Broad series may never be relabeled as granular subthemes."

# 2. ONE SECTION PER SERIES

## NEWORDER — Manufacturers' New Orders: Nondefense Capital Goods Excluding Aircraft

| Date | Break kind | Evidence | Rule-4 handling | Effect on 1997-04-15 → latest |
|---|---|---|---|---|
| 2001-05-21 | NAICS/SIC reclassification + benchmark revision + seasonal-method change | `DETERMINED-FROM-PUBLISHED-NOTES`, https://fred.stlouisfed.org/series/NEWORDER fetched 2026-09-23T20:10:55Z–20:11:02Z: "Effective May 21, 2001, data were reconstructed to reflect the switch from the Standard Industrial Classification (SIC) system to the North American Industry Classification System (NAICS)." Supporting agency quote, https://www.census.gov/manufacturing/m3/historical_data/summary.pdf fetched 2026-09-23T20:12:10Z–20:12:16Z: "Benchmarking... Updating the seasonal adjustment factors for all series." | Era split on publication clock: 1997-04-15–2001-05-20 (pre-reconstruction) and 2001-05-21 onward. Do not splice levels across the split. | Yields two NEWORDER eras. |
| 2025-05-16 | Benchmark revision + seasonal-method change + reclassification corrections | `DETERMINED-FROM-PUBLISHED-NOTES`, https://www.census.gov/manufacturing/m3/bench/pdf/text.pdf fetched 2026-09-23T20:12:36Z–20:12:43Z: "Benchmarking... Correcting... reclassifications... Updating the seasonally adjusted data." | Era split on publication clock: 2001-05-21–2025-05-15 and 2025-05-16 onward; within the source-clock record, use initial-release rows rather than back-casting the 2025 benchmark across old eras. | Splits the long post-2001 era; no broad-to-machinery relabeling. |
| No break found in the fetched notes | Definition/source-agency change | `UNKNOWN`: https://fred.stlouisfed.org/series/NEWORDER (fetched 2026-09-23T20:10:55Z–20:11:02Z) identifies Census M3, and https://fred.stlouisfed.org/release?rid=95 (fetched 2026-09-23T20:14:15Z–20:14:18Z) states no definitional or source-agency break beyond the rows above. | No action for this break kind. | No additional era. |

## ISRATIO — Total Business: Inventories to Sales Ratio

| Date | Break kind | Evidence | Rule-4 handling | Effect on 1997-04-15 → latest |
|---|---|---|---|---|
| 2001-06-14 | NAICS/SIC reclassification | `DETERMINED-FROM-PUBLISHED-NOTES`, https://fred.stlouisfed.org/series/ISRATIO fetched 2026-09-23T20:10:55Z–20:11:02Z: "Effective June 14, 2001, data were reconstructed to reflect the switch from the Standard Industrial Classification (SIC) system to the North American Industry Classification System (NAICS)." | Era split on publication clock: 1997-04-15–2001-06-13 and 2001-06-14 onward. | Yields two ISRATIO eras. |
| 2025-05-16 | Benchmark revision + seasonal-method change + reclassification corrections | `UNKNOWN`: https://www.census.gov/manufacturing/m3/bench/pdf/text.pdf fetched 2026-09-23T20:12:36Z–20:12:43Z revises M3 monthly data with benchmark, reclassification, and seasonal updates, but the fetched ISRATIO notes do not bind that M3 benchmark to this total-business ratio. | UNKNOWN: do not date or split this series on M3 benchmark evidence alone. | No ISRATIO action from the 2025 row until its own MTIS release states it. |
| No break found in the fetched notes | Benchmark, seasonal-method, definitional, discontinuity, source-agency | `UNKNOWN`: https://fred.stlouisfed.org/series/ISRATIO and https://fred.stlouisfed.org/release?rid=25 fetched 2026-09-23T20:10:55Z–20:11:02Z and 20:14:15Z–20:14:18Z state no further dated break. | No further action; do not infer benchmark dates from M3. | Only the 2001-06-14 split is established. |

## AWHMAN — Average Weekly Hours of Production and Nonsupervisory Employees, Manufacturing

| Date | Break kind | Evidence | Rule-4 handling | Effect on 1997-04-15 → latest |
|---|---|---|---|---|
| No dated break found | Any of the six break kinds | `UNKNOWN`: https://fred.stlouisfed.org/series/AWHMAN fetched 2026-09-23T20:10:55Z–20:11:02Z states the definition and CES source but no NAICS/benchmark/seasonal/discontinuity date. BLS notes at https://www.bls.gov/web/empsit/cesnaics.htm, https://www.bls.gov/ces/cesnaics.htm, and https://download.bls.gov/pub/time.series/ce/ce.txt returned HTTP 403 at 2026-09-23T20:13:29Z–20:13:30Z and 20:14:30Z–20:14:31Z. | Treat the fetched-note break status as UNKNOWN. Do not split, splice, or claim an unbroken 1997–latest definition from this record. | No AWHMAN era boundary can be ratified from fetched notes. |
| No break found in the fetched notes | Definitional or source-agency change | `UNKNOWN`: https://fred.stlouisfed.org/series/AWHMAN fetched 2026-09-23T20:10:55Z–20:11:02Z states, "The series comes from the 'Current Employment Statistics (Establishment Survey).'" It states no date at which the source changed. | Retain the stated source; no dated source-agency break. | No additional era. |

## AMTMUO — Manufacturers' Unfilled Orders: Total Manufacturing

| Date | Break kind | Evidence | Rule-4 handling | Effect on 1997-04-15 → latest |
|---|---|---|---|---|
| 2001-05-21 | NAICS/SIC reclassification + benchmark revision + seasonal-method change | `DETERMINED-FROM-PUBLISHED-NOTES`, https://www.census.gov/manufacturing/m3/historical_data/summary.pdf fetched 2026-09-23T20:12:10Z–20:12:16Z: "revised monthly data for January 1992 through March 2001"; the same release retabulated SIC to NAICS, benchmarked unfilled orders, and updated seasonal factors. | Era split on publication clock: 1997-04-15–2001-05-20 and 2001-05-21 onward. | Splits the nominal backlog series; do not level-splice. |
| 2010-04 | Definitional change / discontinuity (semiconductor exclusion) | `DETERMINED-FROM-PUBLISHED-NOTES`, https://fred.stlouisfed.org/series/AMTMUO fetched 2026-09-23T20:10:55Z–20:11:02Z: "Data on Unfilled Orders for the Semiconductor Industry are not available." Agency page https://www.census.gov/manufacturing/m3/historical/timeseries.html fetched 2026-09-23T20:11:12Z–20:11:17Z: "Starting with the April 2010 Reports, estimates for the semiconductor industry will no longer be available separately." | Era split at 2010-04: 2001-05-21–2010-03 and 2010-04 onward. | Adds an order-book-era boundary. |
| 2025-05-16 | Benchmark revision + seasonal-method change + reclassification corrections | `DETERMINED-FROM-PUBLISHED-NOTES`, https://www.census.gov/manufacturing/m3/bench/pdf/text.pdf fetched 2026-09-23T20:12:36Z–20:12:43Z: revisions spanned "January 2012 through March 2025" and incorporated unfilled-orders benchmark information, reclassifications, and seasonal-model review. | Era split on publication clock: 2010-04–2025-05-15 and 2025-05-16 onward. | Splits the 2010-era observations. |

## AMTMVS — Manufacturers' Value of Shipments: Total Manufacturing

| Date | Break kind | Evidence | Rule-4 handling | Effect on 1997-04-15 → latest |
|---|---|---|---|---|
| 2001-05-21 | NAICS/SIC reclassification + benchmark revision + seasonal-method change | `DETERMINED-FROM-PUBLISHED-NOTES`, https://www.census.gov/manufacturing/m3/historical_data/summary.pdf fetched 2026-09-23T20:12:10Z–20:12:16Z: the M3 release revised January 1992–March 2001, retabulated SIC to NAICS, benchmarked shipments, and updated seasonal factors. | Era split on publication clock: 1997-04-15–2001-05-20 and 2001-05-21 onward. | Splits the nominal shipment series; do not level-splice. |
| 2010-04 | Definitional change / discontinuity (semiconductor aggregation) | `DETERMINED-FROM-PUBLISHED-NOTES`, https://fred.stlouisfed.org/series/AMTMVS fetched 2026-09-23T20:10:55Z–20:11:02Z: "Estimates of Shipments for the semiconductor industry are no longer shown separately." Agency page https://www.census.gov/manufacturing/m3/historical/timeseries.html fetched 2026-09-23T20:11:12Z–20:11:17Z states the change begins with the April 2010 reports. | Era split at 2010-04: 2001-05-21–2010-03 and 2010-04 onward. | Adds an order-book-era boundary. |
| 2025-05-16 | Benchmark revision + seasonal-method change + reclassification corrections | `DETERMINED-FROM-PUBLISHED-NOTES`, https://www.census.gov/manufacturing/m3/bench/pdf/text.pdf fetched 2026-09-23T20:12:36Z–20:12:43Z: "Benchmarking the M3 shipments... Updating the seasonally adjusted data." | Era split on publication clock: 2010-04–2025-05-15 and 2025-05-16 onward. | Splits the 2010-era observations. |

## CMRMTSPL — Real Manufacturing and Trade Industries Sales

| Date | Break kind | Evidence | Rule-4 handling | Effect on 1997-04-15 → latest |
|---|---|---|---|---|
| 1997-01 | Definitional change / declared constructed splice boundary | `DETERMINED-FROM-PUBLISHED-NOTES`, https://fred.stlouisfed.org/series/CMRMTSPL fetched 2026-09-23T20:10:55Z–20:11:02Z: "Before January 1997... After December 1996 CMRMTSPL= CMRMT." | Declared diagnostic-only splice: if used at all, label the pre-1997 constructed formula separately; for this window, use only the post-1996 CMRMT branch. | 1997-01 onward is one source-defined branch inside the diagnostic window. |
| No break found in the fetched notes | NAICS/SIC, benchmark, seasonal-method, discontinuity, source-agency | `UNKNOWN`: https://fred.stlouisfed.org/series/CMRMTSPL and https://fred.stlouisfed.org/release?rid=282 fetched 2026-09-23T20:10:55Z–20:11:02Z and 20:14:15Z–20:14:18Z state no other dated break. | No further action. | No extra era from fetched notes. |

## INDPRO — Industrial Production: Total Index

| Date | Break kind | Evidence | Rule-4 handling | Effect on 1997-04-15 → latest |
|---|---|---|---|---|
| 2002-12 | NAICS/SIC reclassification | `DETERMINED-FROM-PUBLISHED-NOTES`, https://www.federalreserve.gov/releases/g17/current/default.htm fetched 2026-09-23T20:12:36Z–20:12:43Z: "In December 2002, the Federal Reserve reclassified all of its industrial output data from the SIC system to NAICS." | Era split on publication clock: 1997-04-15–2002-11 and 2002-12 onward. | Yields a pre/post NAICS-conversion era boundary. |
| 2025-11-24 | NAICS 2017→2022 reclassification + benchmark revision + seasonal-method change | `DETERMINED-FROM-PUBLISHED-NOTES`, https://www.federalreserve.gov/releases/g17/revisions/Current/DefaultRev.htm fetched 2026-09-23T20:12:58Z: the revision incorporates the 2022 Economic Census, "a conversion... to the 2022 North American Industry Classification System (NAICS)," and updated seasonal factors. | Era split on publication clock: 2002-12–2025-11-23 and 2025-11-24 onward; within the source-clock record, retain initial releases before the conversion. | Splits the post-2002 era. |
| No break found in the fetched notes | Definitional or source-agency change | `UNKNOWN`: https://fred.stlouisfed.org/series/INDPRO and https://fred.stlouisfed.org/release?rid=13 fetched 2026-09-23T20:10:55Z–20:11:02Z and 20:14:15Z–20:14:18Z state the Board of Governors G.17 source but no dated source-agency change. | No action. | No additional era. |

## MNFCTRIRSA — Manufacturers: Inventories to Sales Ratio

| Date | Break kind | Evidence | Rule-4 handling | Effect on 1997-04-15 → latest |
|---|---|---|---|---|
| No dated break found | Any of the six break kinds | `UNKNOWN`: https://fred.stlouisfed.org/series/MNFCTRIRSA fetched 2026-09-23T20:10:55Z–20:11:02Z defines the ratio but states no dated NAICS, benchmark, seasonal, discontinuity, or source-agency break. https://fred.stlouisfed.org/release?rid=25 fetched 2026-09-23T20:14:15Z–20:14:18Z states none. The M3 2001 document governs M3 shipments/orders history; it does not state that this MTIS ratio was reconstructed. | UNKNOWN: do not split, splice, exclude, or claim unbroken history from this record. | No MNFCTRIRSA era boundary can be ratified from fetched notes. |

# 3. ERA MAP

This table uses publication-clock split dates and is the input for seat ratification. "All three mechanisms" means `NEWORDER`, `ISRATIO`, and `AWHMAN`. Since the diagnostic-window source clock begins 1997-04-15, only boundaries at/after that date appear. Measured first-realtime coverage is recorded by the matrix: AWHMAN and INDPRO 1997-01; NEWORDER 1997-03; ISRATIO 1997-04; AMTMUO and AMTMVS 2011-07; CMRMTSPL 2013-06; MNFCTRIRSA 2013-07 (`D03_SOURCE_READINESS_MATRIX...:36`–`:44`).

| Era start | Era end | Series in era | Handling | Usable for macro-only diagnostic? |
|---:|---:|---|---|---|
| 1997-04-15 | 2001-05-20 | NEWORDER, ISRATIO, AWHMAN, INDPRO | Pre-2001 M3 reconstruction / pre-June MTIS reconstruction / pre-G.17-NAICS conversion; AWHMAN break status UNKNOWN. Order-book/MTIS additional series begin later in measured source clock. | NO: all three mechanism series are present by source clock, but AWHMAN's definition continuity is UNKNOWN. |
| 2001-05-21 | 2001-06-13 | NEWORDER, ISRATIO, AWHMAN, INDPRO | Transition: M3 reconstructed, MTIS not yet. | NO: mixed reconstruction regimes; not a coherent all-mechanism era. |
| 2001-06-14 | 2002-11 | NEWORDER, ISRATIO, AWHMAN, INDPRO | Census reconstruction regimes; G.17 still pre-NAICS. | NO: all three mechanism series are present, but AWHMAN continuity is UNKNOWN and INDPRO crosses a later conversion. |
| 2002-12 | 2010-03 | NEWORDER, ISRATIO, AWHMAN, INDPRO | Post-SIC→NAICS reconstruction; pre-2010 M3 semiconductor aggregation. | NO: all three mechanism series are present, but AWHMAN continuity is UNKNOWN. |
| 2010-04 | 2025-05-15 | NEWORDER, ISRATIO, AWHMAN, INDPRO; AMTMUO/AMTMVS from first realtime 2011-07; CMRMTSPL/MNFCTRIRSA from 2013 | Post-2010 M3 semiconductor treatment; pre-2025 M3 benchmark. | NO: all three mechanism series are present, but AWHMAN continuity is UNKNOWN. |
| 2025-05-16 | 2025-11-23 | NEWORDER, ISRATIO, AWHMAN, INDPRO, AMTMUO, AMTMVS, CMRMTSPL, MNFCTRIRSA | Post-2025 M3 benchmark; ISRATIO/MNFCTRIRSA benchmark applicability UNKNOWN. | NO: transition/benchmark regimes are mixed and AWHMAN continuity is UNKNOWN. |
| 2025-11-24 | latest fetched | NEWORDER, ISRATIO, AWHMAN, INDPRO, AMTMUO, AMTMVS, CMRMTSPL, MNFCTRIRSA | Post-2025 M3 benchmark and post-G.17 2022-NAICS conversion. | NO: all three mechanism series are present by source clock, but AWHMAN continuity is UNKNOWN and the span is not yet observed to a useful diagnostic length. |

**Era-map result: no usable macro-only era can be ratified until AWHMAN's definition-treatment record is closed.** That is a rule-4 result, not an admission or market verdict.

# 4. EVIDENCE

## In-repo reads

```text
2026-09-23T20:08:17Z
git rev-parse HEAD
9030377baa34fdd6b30ed3b0b5c05a8b60f91499

2026-09-23T20:08:17Z
git cat-file -e HEAD:<each mandated path>
Result: R6-D03 ruling and cycle census present at origin/main; R6-B16 ruling and matrix absent.

2026-09-23T20:09:24Z
git fetch origin refs/pull/7842/head:refs/remotes/pr/7842
Result: created refs/remotes/pr/7842; both fallback records present.

git show pr/7842:research/prophet_v4/r6_program/rulings/R6-B16-01_ADMISSION_2026-09-23.md
§1:10 names NEWORDER, ISRATIO, AWHMAN and the AMTMUO/AMTMVS order-book family.
§3:26 orders the rule-4 record; §3:27 names the 1997-04-15 diagnostic-clock floor.

git show pr/7842:research/prophet_v4/r6_program/wave2/D03_SOURCE_READINESS_MATRIX_2026-09-23.md
§2:36–44 records source-clock spans; §5:83–90 records candidate-(a) unit and no-relabel constraints.

research/prophet_v4/r6_program/wave2/D03_CYCLE_SOURCE_READINESS_CENSUS_2026-09-23.md:85–91
Records the 2001 M3 reclassification/benchmark/seasonal break and broad-series no-relabel rule.
```

## Public fetches

```text
2026-09-23T20:10:55Z–20:11:02Z
curl -sL https://fred.stlouisfed.org/series/{NEWORDER,ISRATIO,AWHMAN,AMTMUO,AMTMVS,CMRMTSPL,INDPRO,MNFCTRIRSA}
All eight returned HTTP 200. Series-note excerpts are quoted in §2.

2026-09-23T20:11:12Z–20:11:17Z
curl -sL https://www.census.gov/manufacturing/m3/historical/timeseries.html
HTTP 200. "Starting with the April 2010 Reports, estimates for the semiconductor industry will no longer be available separately."

2026-09-23T20:12:10Z–20:12:16Z
curl -sL https://www.census.gov/manufacturing/m3/historical_data/summary.pdf
HTTP 200. May 21, 2001 release reconstructed January 1992–March 2001, benchmarked shipments/inventories/unfilled orders, and updated seasonal factors.

2026-09-23T20:12:36Z–20:12:43Z
curl -sL https://www.census.gov/manufacturing/m3/bench/pdf/text.pdf
HTTP 200. May 16, 2025 revisions span January 2012–March 2025 and update benchmarks, reclassifications, and seasonal models.

2026-09-23T20:12:36Z–20:12:43Z
curl -sL https://www.federalreserve.gov/releases/g17/current/default.htm
HTTP 200. "In December 2002, the Federal Reserve reclassified all of its industrial output data from the SIC system to NAICS."

2026-09-23T20:12:58Z
curl -sL https://www.federalreserve.gov/releases/g17/revisions/Current/DefaultRev.htm
HTTP 200. Release date 2025-11-24; converts indexes to 2022 NAICS, incorporates 2022 Economic Census benchmarks, and updates seasonal factors.

2026-09-23T20:14:15Z–20:14:18Z
curl -sL https://fred.stlouisfed.org/release?rid={95,25,282,13,50}
All HTTP 200; no additional dated breaks beyond those recorded above.
```

# 5. GAPS + MUST-NOTS REFUSED

- **AWHMAN:** all three named BLS notes/pages and the alternate CES time-series endpoint returned HTTP 403, so no dated NAICS/reclassification, benchmark, seasonal-method, discontinuity, or source-agency break could be determined. The cell is UNKNOWN; the era map therefore proposes **no usable macro-only era**.
- **ISRATIO and MNFCTRIRSA:** the fetched notes state no benchmark or seasonal-method date. The May 2025 M3 benchmark PDF does not establish applicability to the Manufacturing and Trade Inventories and Sales release, so those cells remain UNKNOWN.
- **Historical methodology archives:** the fetched current notes and linked 2001/2025 documents do not exhaust every historical benchmark or seasonal review. No unlisted date is inferred.
- **Record scope:** this file records only breaks and handling; it does not ratify a diagnostic window, admit a domain, or produce a diagnostic.
- **MNFCTRIRSA 2001 treatment:** the M3 reconstruction document does not state that this MTIS ratio was reconstructed, so it is not assigned the June 14, 2001 date.
- **MUST-NOTS REFUSED:** no keyed/authenticated call; no `data/` read or write; no return, outcome, or ledger artifact; no modeled lag; no relabeling of `NEWORDER`, `INDPRO`, `AMTMUO`, `AMTMVS`, `CMRMTSPL`, or `MNFCTRIRSA` as machinery; no broad aggregate used as a granular subtheme; no unseen break inferred from memory.
