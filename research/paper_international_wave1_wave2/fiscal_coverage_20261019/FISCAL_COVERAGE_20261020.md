# International Markets — complete fiscal coverage and design proof

Recorded on 20 October 2026 UTC for the existing International Markets build. This increment remains in the working tree after frozen local HEAD `11c83bb5dfb0c8199a0fb0cb2c6e70452c724984`. It is not yet present in the remote draft PR or the live site.

## Product outcome

The country assessment now has a complete external and fiscal view for all seven covered economies. Korea, Taiwan, India and Australia gain qualified government-balance and gross-debt projections alongside their existing current-account, growth and inflation paths. Japan, the United Kingdom and the Euro Area keep their previously accepted fiscal coverage.

The page describes the direction and meaning of each projection. A smaller deficit is still a deficit; an unchanged surplus is not described as a deterioration; a lower debt-to-GDP ratio does not assert a fall in nominal debt. Units explicitly say **% GDP · FORECAST**, with Chinese equivalents. India's values retain April–March fiscal-year labels.

The main experience remains country interpretation: the current economic position, the projected path, the policy decision, measured market conditions, the transmission channel, and developments that would change the assessment. Saved research, comparisons and alerts remain subordinate.

## Newly admitted fiscal evidence

These are the October 2026 IMF World Economic Outlook projections. They are not current observed budget results, trading signals or a claim that definitions are identical across countries.

| Economy | Periods | Government balance, % GDP | Gross government debt, % GDP | Coverage and accounting |
| --- | --- | --- | --- | --- |
| South Korea | 2026 → 2027 | −1.3 → +1.4 | 47.3 → 46.2 | Central and local government, social security; accrual |
| Taiwan | 2026 → 2027 | +0.3 → +0.3 | 21.1 → 20.0 | Central and local government; cash |
| India | FY2026/27 → FY2027/28 | −7.5 → −7.2 | 83.1 → 81.3 | Central and state government; cash |
| Australia | 2026 → 2027 | −3.2 → −3.0 | 52.6 → 53.2 | Central, state and local government; accrual |

The two primary data responses are:

- [IMF general-government net lending/borrowing, GGXCNL_NGDP](https://www.imf.org/external/datamapper/api/v2/GGXCNL_NGDP/KOR/TWN/IND/AUS?periods=2026,2027).
- [IMF general-government gross debt, GGXWDG_NGDP](https://www.imf.org/external/datamapper/api/v2/GGXWDG_NGDP/KOR/TWN/IND/AUS?periods=2026,2027).

Both responses returned HTTP 200 over ordinary TLS on 19 October at 23:23:16 UTC. Their original bytes are preserved losslessly in `raw_api/`, with SHA-256 identities in [source_acquisition.json](source_acquisition.json). The response metadata identifies World Economic Outlook (October 2026), dataset WEO, percent-of-GDP units and projection year 2026.

The observed API response did not honor the requested country/year filtering: it returned broader country and year coverage. The parser therefore explicitly selects only the reviewed four economies and two years. It also permits the observed empty-key null placeholder, while rejecting non-null empty-key content, wrong indicators, duplicate keys, non-finite values, missing cells and incompatible metadata. [API documentation](https://www.imf.org/external/datamapper/api/help) and [indicator metadata](https://www.imf.org/external/datamapper/api/v2/indicators) have separate acquisition receipts.

### Information-cutoff correction

The October WEO information cutoff is **30 September 2026**, not 1 October.

The [Statistical Appendix](https://www.imf.org/-/media/files/publications/weo/2026/october/english/statsappendix.pdf) establishes the cutoff and supplies the fiscal-year and government-coverage definitions. Its original PDF acquisition returned HTTP 200; its byte identity is retained in [documentation_acquisition.json](documentation_acquisition.json).

The [October WEO Database Appendix](https://data.imf.org/-/media/iData/External-Storage/Documents/C4182C5C54794FC48892DE8F6C74FF82/en/October-2026-WEO-Database-Appendix.pdf) separately confirms the database cutoff. That document was read through web retrieval. The connected-host byte acquisition returned HTTP 403 and HTML, so this record does not claim a successful original PDF acquisition or PDF hash for it. The failure remains in [database_documentation_acquisition.json](database_documentation_acquisition.json). Country-specific update clocks and HTTP Last-Modified are not substituted for the edition's information cutoff.

The prior Australian Article IV candidate remains unadmitted. Its older fiscal-year values were not mixed into these WEO calendar-year projections.

## Backend behavior and historical integrity

One reviewed admission completed at **2026-10-19 23:39:17.696032 UTC**. The archive grew from 37 to 73 records:

- Eight new fiscal publication records: balance and debt for each of the four economies.
- Twenty-eight explicit metadata corrections that supersede the original October WEO records' cutoff.

All 37 original record identities and contents are preserved. Each of the 28 superseded originals gains the expected superseded_at lifecycle timestamp at the actual admission time; no other original field changes. The correction records retain the original values, periods, source URLs, source hashes and retrieval clocks. Their new first-observed and admission clocks reflect the actual correction admission; they do not rewrite history.

The baseline's official observations, CPI series, legacy forecasts, source/error fields and seven policy decisions/reviews are preserved. The accepted baseline SHA-256 after admission is `43e16a0f1dfc20aec4efc3b866437063e28da2ffadfd57465428973b92daba27`. The original baseline is retained in [baseline_before.json.gz](baseline_before.json.gz); [admission.json](admission.json) identifies every new and superseded record.

The ordinary registered collector owns both fiscal endpoints. It enforces payload bounds, edition/indicator/unit identity, country coverage, period basis and source provenance. Each release can fail independently without destroying the other accepted family.

An ordinary sequence-zero refresh can recognize the latest accepted semantically identical correction. It preserves the actual accepted record identity and withdrawal state; it does not create an alias, backdate custody or bypass ordered correction handling.

Joint economic interpretation requires aligned provider, family, edition, cutoff and exact current/next periods. A growth projection from one vintage cannot silently combine with a fiscal projection from another. The world brief permits the two explicitly reviewed original/corrected world record identities, not arbitrary revised values or future editions.

Source disclosures expose country coverage in both languages. Partial withdrawal changes the section title to the evidence actually present, and the missing-data note identifies only the absent fiscal series.

## Frontend and Paper

The [existing R12 Paper page](https://app.paper.design/file/01M3P1TW5Y3XWQC37ADDS8K5AG/p-G-0) is updated on its six owned boards:

- Four desktop/mobile, dark/light overview references now show Korea's government balance and gross debt below its current account.
- The United Kingdom detail has the corrected cutoff and forecast-unit wording.
- The Taiwan detail includes current account, balance and debt, with appropriate light-theme text and divider tokens.

All **56 text checks and 16 style-property checks pass** against fresh native JSX. Six boards were finished. Seven native operations, including finish, were observed applied. Six original operation responses are retained. The layer-renaming response was lost across an app-context refresh before persistence; its twelve names were subsequently read back without replaying the edit. That distinction is explicit in the [Paper receipt](paper_fiscal_coverage_receipt.json).

Six native screenshots and six JSX exports are retained with hashes. Image bytes were decoded from native transport without image editing. Tall Paper overviews are downscaled by the native screenshot tool; focused browser captures provide readable detail.

Two concrete visual defects were corrected during review. An open source disclosure could expand a 320px layout to 444px; the country grid item now has `min-width: 0`, and the expanded ledger fits. Taiwan's cloned detail initially inherited dark-theme text colors; it now uses the proper light-theme tokens.

Paper source labels are design references. Working URL targets, disclosure behavior and browser navigation are established by the actual HTML tests, not by a claimed Paper click-through.

## Verification

| Scope | Result | Retained evidence |
| --- | --- | --- |
| Four affected country/forecast/policy/interpretation suites, normal International build and shared public HTML checks | **208 passed**, two existing cleanup warnings | [Run](final_country_and_public_tests_v2.json), [log](final_country_and_public_tests_v2.log) |
| Country browser matrix | **84 of 84 passed** | [Browser receipt](browser_verification.json) |
| Canonical screenshots | **12 of 12 captured** | `mockups/evidence/intl-fiscal-coverage-20261020/manifest.json` |
| Browser history | Two back/forward journeys passed | [Browser receipt](browser_verification.json) |
| JavaScript page exceptions | Zero | [Browser receipt](browser_verification.json) |
| Paper text/style verification | **56/56 and 16/16 passed** | [Readback](paper_final_readback_verification.json) |
| Existing design and visual-evidence gates | Passed; zero introduced design blockers | [Gate receipt](gates/verification.json) |
| Tracked-source whitespace | Passed | [Gate receipt](gates/verification.json) |

The browser matrix spans seven economies × 1440/390/320 widths × English/Chinese × dark/light. It checks all three balance rows, values, periods, interpretations, forecast labels, source links, translated coverage, one open country, disclosure expansion and actual document width.

The final test run completed at 01:50:18 UTC on 20 October. The final render followed at 01:50:18.278522 UTC, and the final browser verification completed at 01:51:52 UTC.

The first browser run's disclosure-overflow failures remain in `browser_attempt1/`. Earlier failed test receipts also remain, including the three policy test fixtures whose wall-clock use was exposed by the UTC date rollover. Those fixtures now use their intended historical test time; no production timing rule was loosened.

The browser-tested HTML is retained losslessly as gzip with exact decompressed hashes:

| Preview | SHA-256 |
| --- | --- |
| Country | `3e62af20ca56918a3c18366da1218effe5a85f919e128288306ea0c06a6f5f9a` |
| Integrated International | `d0ff3bd36a67377213d353e4d6399a53ae4ab6a27086ce1a31e8e5ac0b11ef32` |
| Integrated stocks compatibility | `3230ccec0584627c8d58afff0a175d178c47b582cce4066d95a9f8d7c6381287` |

The market replay still has its **15 October** clock. A new render is not new market evidence. Paper's header remains 19 October while the final fixture render is dated 20 October UTC.

The anonymous canonical fixture records its missing `live_config.js` and blocked analytics request. Authenticated and synthetic degraded states remain uncaptured. Hidden legacy DOM has wider-element counters on mobile, while document-level and visible-country overflow checks pass. The two Python warnings concern existing Chrome.app temporary cleanup. These limitations remain in the raw receipts.

## Release state and next work

The draft PR is [macro #9596](https://github.com/mastermindx-market-intelligence/macro/pull/9596). The local HEAD is frozen at `11c83bb5dfb0c8199a0fb0cb2c6e70452c724984`; the last observed remote PR head is `88b6f192c3e2a7a94f5cf7ff4d9d06bc225324a4`.

The original push action `d07df7c6e45d35c54338808701350ece97c605401ad69a0fd28bb415d05a5a56` remains **EFFECT_UNKNOWN / PUSH_RESULT_UNCERTAIN**. The 20 October 01:52 UTC recovery check found no new original-action reconciliation evidence. Current unequal refs do not settle an earlier attempted write.

No commit, replay, alternate publisher, Ready transition, merge, deployment or restart was performed. The existing publisher owner must resolve that original action. Exact combined-head hosted CI, the real Sector Central Full RIG approvals and independent release review remain required, followed by the ordinary render/updater path and real served-page acceptance. Earlier PR8754 obligations remain separate.

The previously verified nine-asset access repair is unchanged against all three recorded source-file hashes. No background release watcher is armed.

The next independent product frontier is the missing three-month currency observation: determine whether it is a replay clock gap or an ordinary pipeline gap, then repair the existing feed/provenance seam if justified. Fiscal completion does not manufacture currency coverage or release acceptance.
