**Verdict**
All six proposed points PASS against the supplied source text on numbers, units, date horizons and attribution. No numeric correction is required. Caveats below are additive (missing qualifications), not source changes.

**Point 1 — PASS**
- Physical page 1, release line: "Released October 13, 2026, by the National Agricultural Statistics Service (NASS)".
- Physical page 2, "Corn Harvested – Selected States", bracket row: "[These 18 States harvested 93% of the 2025 corn acreage]"; row "18 States" → Oct 11, 2025 = (NA); Oct 4, 2026 = 23; Oct 11, 2026 = 33; 2021-2025 Average = 39.
- All four claimed values (33 / 23 / 39 / 93% of 2025 acreage) match, and 2026 progress is correctly kept distinct from the 2025 coverage share.

**Point 2 — PASS**
- Physical page 3, "Soybeans Harvested – Selected States", bracket row: "[These 18 States harvested 96% of the 2025 soybean acreage]"; row "18 States" → (NA) | 25 | 46 | 50.
- Matches 46 / 25 / 50 / 96%.

**Point 3 — PASS (arithmetic confirmed)**
- Physical page 2, "Corn Condition – Selected States: Week Ending October 11, 2026", bracket row: "[These 18 States planted 91% of the 2025 corn acreage]".
- Row "18 States": VP 5, P 12, F 27, G 44, E 12 → 44 + 12 = 56; row check 5+12+27+44+12 = 100.
- Row "Previous week": VP 6, P 12, F 28, G 42, E 12 → 42 + 12 = 54; row check 6+12+28+42+12 = 100. Claimed 56 vs 54 is exact.
- "Previous year" row is (NA), consistent with Point 6.

**Point 4 — PASS (arithmetic confirmed)**
- Physical page 4, "Soybean Condition – Selected States: Week Ending October 11, 2026", bracket row: "[These 18 States planted 96% of the 2025 soybean acreage]".
- Row "18 States": 4, 10, 29, 46, 11 → 46 + 11 = 57; sums to 100. "Previous week": 4, 10, 29, 46, 11 → identical, 57. "Unchanged" is exact for every category, not just G+E.

**Point 5 — PASS**
- Physical page 2, Corn Harvested, row "Iowa": (NA) | 7 | 14 | 34 → 14% current, 34% average (prior week 7% unclaimed, harmless).
- Physical page 3, Soybeans Harvested, row "Iowa": (NA) | 5 | 31 | 59 → 31% current, 59% average.
- Tables are percent-of-acreage harvested (completion), so the "not yield/production/price/company forecast" disclaimer is correct; the source contains no yield, price or company data.

**Point 6 — PASS**
- Physical page 1, Special Note: cancellation of reports "for the weeks ending October 5, 2025, through November 9, 2025"; "previous year estimates for the corresponding weeks will not be available"; five-year averages "reflect the years 2021-2025 using published estimates for 2021-2024 and imputed estimates for 2025".
- Corroborated by (NA) in every "October 11, 2025" column and every "Previous year" condition row (pages 2, 4, 5, 6, 7, 10).
- Observation horizon: physical page 14 methodology — respondents "report for the entire week ending on Sunday"; Oct 11, 2026 and Oct 4, 2026 are both Sundays, Oct 13, 2026 is the printed release date, so publication does not move the observation date.

**Missing Caveats To Carry**
- Weighted, not averaged: 18-States rows are acreage-weighted (harvest weighted by average harvested acres over the previous three crop years; condition/planting by average planted acres — page 14). Simple means of the 18 state rows do not reproduce them: corn harvest mean 40.7% vs published 33%; soybean harvest mean 50.2% vs published 46%.
- Panels differ by crop: corn's 18 states include CO, PA, TX; soybeans' 18 include AR, LA, MS. "18 selected states" is not one fixed panel across Points 1–4.
- G+E is derived: the source publishes only the five categories; 56% and 57% are computed sums, not printed figures.
- Imputed-2025 qualifier belongs on Point 5 too: its "five-year average" is the 2021-2025 Average column (published 2021-2024 + imputed 2025).
- Cancellation cause omitted: source attributes it to "a lapse in federal funding in October and November 2025", and scopes unavailability to "the corresponding weeks", not to all prior-year comparisons generally.
- Revision exposure: page 14 states estimates are "subject to revision the following week"; no point carries this.
- Coverage-metric distinction: 93% (corn harvested share of 2025 acreage) vs 91% (corn planted share), and 96% harvested vs 96% planted for soybeans, are different metrics that partly coincide.
- Date-label nuance: prior-year columns are labeled "October 11, 2025" (a Saturday) while the Special Note is phrased in "weeks ending" (Sunday) terms; (NA) is consistent under either reading.
- Out-of-source: the supplied text contains no WASDE reference and no October 9 event material, so the "distinct from the held October 9 WASDE" framing is not evidenced by this source and should stay attributed to parent context only.

**Basis And Scope**
- Verified solely against the supplied source text; no network calls, no repository or provider mutations, nothing staged or published.
- The retained PDF was not present on this host (searched `/home/longr` and `/home/longr/lanes` for `prog4126*`, crop/USDA/NASS filenames, and the literal hash `ecdbbb59…968c`), so the SHA256 identity and the pages 1–4 visual check rest on parent custody and were not independently reconfirmed here. Page citations use the report's own printed page numbers, which match physical pages 1–14 plus an unnumbered final contacts page.
