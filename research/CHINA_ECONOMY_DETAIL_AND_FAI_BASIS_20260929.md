# China economy: acquired detail and investment measurement correction

Status: **BUILT_NOT_PROVEN; PR #8196 remains DRAFT / release HOLD.**
Operation: `china-macro-evidence-upgrade-20260929-sol-001`, Sol, original Studio_Direct worktree.
Starting implementation: `47010d95a47bc9412f9d3077bd0b2ad76f336d94`.
Protected Mastermind procedure: `1405c634d8a0b0d3b05305fdd8d62e7b0b520e93`.

## Material capability delta

The existing source pipeline now admits 31 additional current-period catalog readings from four already supported primary release families: industrial composition and product volumes, industry/product breadth, monthly retail mix, cumulative investment composition and regional variation, and PMI firm-size/services/construction detail. They extend the original 128-series catalog; they do not add 31 independent signals or growth-domain votes.

The first actual installed collector run increased current coverage from 53 to 83. It reported `blocked`, not `ok`: seven sources acquired, no acquisition failures, but one legacy FAI value conflict. That refusal was correct for the then-shared column. A further source investigation showed that two different measurements had been conflated. After separating them within the same owner table and qualifying the official reading, the actual reader and page export contain **84/128 current readings**. Domain-direction coverage remains **2/6**. Whole-economy direction is still withheld; a current observation does not provide a six-month trend.

## Investment: source basis, not just stale data

The existing Eastmoney mapping put `RPT_ECONOMY_ASSET_INVEST.BASE_SAME` in `china_macro/fai.fai_yoy` and described it as cumulative YoY. Three inspected months instead match the percentage change of the provider's SINGLE-MONTH nominal amounts to the corresponding prior-year amounts:

| Month | Current monthly amount | Prior-year monthly amount | Computed monthly YoY | Provider BASE_SAME |
|---|---:|---:|---:|---:|
| 2026-08 | 32,764 | 37,882 | -13.51% | -13.51% |
| 2026-07 | 33,958 | 39,575 | -14.19% | -14.19% |
| 2026-06 | 47,858 | 56,707 | -15.60% | -15.60% |

Amounts are in the provider's CNY100m convention. Each current monthly amount also equals the difference between successive current-year cumulative amounts; its `BASE_SEQUENTIAL` matches the corresponding monthly-amount sequential calculation. These arithmetic checks establish the mismatch for the observed rows. They are not a substitute for provider documentation across every historical definition.

The NBS August release reports cumulative investment of 293,092 CNY100m and **-7.2% comparable-scope year-to-date growth**. Its footnote states that prior-year data are revised and growth is calculated on a comparable basis. The provider's raw cumulative totals produce -10.13%, not that official comparable growth rate. Neither -13.51% nor the unrevised-total ratio may replace the NBS -7.2% measure.

Primary NBS source: https://www.stats.gov.cn/sj/zxfb/202609/t20260915_1965309.html
Existing provider source: `https://datacenter-web.eastmoney.com/api/data/v1/get`, report `RPT_ECONOMY_ASSET_INVEST`.
Observed request/row/arithmetic records: `research/china_economy_integration_20260929/r3/fai-origin-comparison.json` and `fai-period-basis-proof.json`.

## Repair and compatibility

- Preserve **all legacy `fai_yoy` values**. Do not rewrite the provider series, weaken the conflict guard, or claim that monthly and cumulative observations are the same series.
- Store the distinct official measure in **`china_macro/fai.fai_ytd_yoy`**, the same existing table and collector owner. The live catalog binding is now `investment_ytd.nbs_comparable.v2`. Historical review fixtures retain their original identity and are not production fallbacks.
- The original macro dialog's stable metric ID `macro_fai_yoy` now reads this NBS measure through the SAME value/definition/source/publication/acquisition receipt admission as the economy overview. Its source path, unit and definition explicitly identify the corrected basis. Missing official evidence does not fall back to legacy monthly values.
- The original field and any legacy consumers remain preserved. This changes descriptive evidence, not a strategy's weights, ranking, entry, sizing or trade permission.
- Standard upsert initially changed the table index NAME (`REPORT_DATE` to `date`) while preserving every date and value. The original effect was inspected, its index name restored through the same owner, and the qualifier now preserves existing index metadata. No source data refetch or blind retry was used for that repair.

## Additional detail admission

Growth columns are selected from the publisher's exact period/unit header, not a guessed position. Monthly retail cannot become YTD retail, a price-volume figure cannot become value-added growth, and amounts cannot become growth rates. The investment parser requires a cumulative reporting period. Zero is retained; malformed, suppressed, ambiguous or impossible observations carry null reasons.

The existing publisher-copy check still requires desktop/mobile articles to agree. Duplicate tables or rows inside an article are not silently deduplicated. The 41-industry and 626-product denominators must match their catalog definitions; a changed denominator is withheld rather than drawn as the old population. Services, manufacturing firm-size and construction PMI are current levels; reported prior-month changes do not create historical observations.

Valid seasonal/survey histories survive a missing supplemental table. Every admitted additional value uses the same actual response hash and source publication/acquisition metadata as its release. The parser version is `china-economy-acquisition.v1.1`. Neither new scheduling nor render-time HTTP is introduced.

## Executed evidence

- First installed detail collector: **2,573 total adapter rows**, no acquisition failures, one correctly held FAI conflict. Coverage 53 -> 83. This was an instance-local qualification, not production enrollment.
- Corrected FAI measurement: one verified captured NBS response reprocessed into the distinct column using the existing qualifier and store; no fresh network request. Legacy values AND index metadata preserved, official value -7.2 agrees in overview and macro dialog. Coverage 84/128.
- Final focused repository suite: **482 passed, zero failures/errors/skips**. It includes the new exact-period, denominator, receipt, legacy-preservation and cross-view parity tests and prior consumers.
- Both actual China pages rebuilt with `RENDER_NO_DRIP=1 CHINA_VM_DUMP=1`; exit 0. Static readback verifies every client chart value/unit/definition against the complete JSON and the corrected FAI table row. Both pages have no duplicate DOM IDs. This is NOT browser, accessibility, theme/viewport, signed-in transport or production acceptance.
- Existing structural contract checker passed against exact base `be0ca1fa3aaf64eec16d89edbd992f5025d2b823`: **0 introduced / 0 inherited findings**. This is local structural proof, not a new GitHub run or release approval.
- Python compilation and scoped diff checks pass. The original 434 tests and prior acquisition/build evidence remain historical results, not newly claimed work.

Actual local receipts and their immutable manifest are under `research/china_economy_integration_20260929/r3/`. Temporary raw HTML and full local logs remain under the existing `/private/tmp/china-economy-public-acquisition-20260929-r1` and `/private/tmp/china-economy-release-20260929-r3` locations. Source-value rows, response hashes and acquisition times are recorded; this is not an original-vintage historical store or a publisher signature.

## Remaining release gates

Exact-head run 36601967474 for the starting commit completed. Structural contract, old failing consumer packs and most CI packs passed. Remaining failures include shared-theme pinned mobile receipts, missing visual EVIDENCE.yml receipts, research-screener fresh-bake drift, and the macro credit/funding capture-fixture test. The last two are not labeled inherited without proof. Main authority/security passed; the inactive alternate merge-base context is not release permission.

A compound UI/CI/palette/browser-source READ was refused before dispatch because OpenAI could not determine its safety status. It was not retried, rephrased or routed through another profile/tool/account. The prior administrator-blocked browser-preview action remains separate. This independent data work does not clear either boundary. No screenshot, visual waiver, browser acceptance, production enrollment, merge or deployment is claimed.

Continue the same branch and operation. First consume exact-head results after this source patch, and preserve true code/data failures. Once the original browser/acceptance permissions are restored, use the existing canonical capture and pinned-receipt owners, complete independent review and actual authenticated gateway verification, then the normal protected non-Vercel release. Fiscal/source-history expansion, external-trade basis reconciliation and publishing-rights checks remain open. Do not lower domain coverage thresholds merely to produce a broad economic headline.
