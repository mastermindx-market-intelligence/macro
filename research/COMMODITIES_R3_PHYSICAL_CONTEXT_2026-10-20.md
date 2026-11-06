# Commodities R3 — physical and regional context continuation

## Current owner recovery status — 2026-10-20

Git publication is recovered. The original publisher's owner-approved command budget is 45 seconds; repository grants, installed modules and Paper capabilities are preserved. Its installed code already seeded the private index from the real index. The historical 15-second timeout was not reproduced in the bounded isolated staging probe; no index corruption or missing seeding code was established.

The interrupted push and PR update landed at `8d7212be4264ddccf78d5d5fa3f087c12218791b`. Subsequent published head `b08ece31c517cc95b87b053540218bad17d18c63` passed all twelve CI packs, contract-delta, ci-gate and fences. CI run [39450879542](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39450879542) completed successfully at 16:11 UTC. The ordinary SHA-pinned squash was rejected with GitHub 405 after main advanced through other accepted work and two render publications. [PR #9878](https://github.com/mastermindx-market-intelligence/macro/pull/9878) remains authoritative for the latest published head and its checks.

This revision integrates accepted main `fe5093cc4ebab5f4a041f4d35430cb7164bd96d3`. Its only content conflict was the generated `site/commodities.html`. The review renderer now pairs the unchanged R3 component with the complete current accepted legacy HTML, including the existing USGS section. All 341 accepted CI jobs are preserved beside the Commodities job; the combined manifest has 342 total jobs and 271 code jobs. The curated registry union passes its closure, startability and narrow-selection checks. No packing ceiling, safety guard or gate was weakened.

All 17 research input blobs are identical to the previous qualified snapshot, including five publisher JSON files, ten EIA series, company aliases and configuration. Payload values are identical after excluding source identity fields. Component markup is byte-identical after excluding its JSON payload and the fingerprint printed inside Methodology; canonical theme, R3 CSS and JavaScript are unchanged. Exact legacy preservation, input comparisons and CI-job union are recorded in `mockups/evidence/commodities-r3/source/late-main-integration.json`.

Physical observations remain **2026-10-09**, seven days before the **2026-10-16** price research snapshot, with release vintage unknown. The inventory classification is **broad tightness**. Crude stocks are 415.6 million barrels (seasonal z -0.59; exact 28-day change -7.9 million; stock/flow 25.1 days); gasoline 208.3 (-1.20; +0.5; 24.0 days); distillate 102.6 (-1.94; -5.2; 25.8 days). Four-week changes use September 11 to October 9; flow averages use September 18 to October 9. A tight US inventory buffer does not establish global supply loss or a supply-shock cause. The independent inflation condition is unmet. Older October 2 values below are historical.

Fresh local qualification passes **188 Python tests plus 35 subtests, six pure Node contracts, 27 DOM journeys, 26 Chromium checks, four CI registration/closure/startability/selection checks and validation of all 271 code jobs**. Source-language, design, runtime-style, UI-evidence and PR-diff whitespace gates pass. Six pytest temporary-directory cleanup warnings are preexisting and contain no failed assertion.

The **56 active visual cells** remain qualified by the component/style equivalence above: 24 Overview, 16 Gold Explore/Relationships and 16 WTI Explore/Relationships cells across EN/ZH, dark/light and desktop/mobile. The WTI captures in `weekly-update` supersede their older counterparts. Current-main functional journeys were rerun; these retained captures do not claim a new production screenshot.

Projection revision remains 6 with 17 assets and 30 source-qualified company links. Current review fingerprint is `2d3d68280a023930ac7cf9a8c2ece1cfeda609ea9b297c3b954a56fa34c88d47`; current paired-page SHA-256 is `4fc0a17403b47bd4344ab37f7bbca4c97508c8218bc47c8b879cafcb509fbb82`. Historical source evidence remains distinct from live prices and the legacy publishers' own clocks.

An adjacent, separately scoped Terminal repair preserves the selected company, research query and nested Commodities return URL through Google OAuth. It is being qualified in the fresh `claude/commodities-oauth-context-20261020` worktree; existing password PR #1045 remains separately owned. Callback redirect admission and beta signup behavior are unchanged. Local provider fixtures do not establish a real Google authentication transaction or deployed authenticated continuation.

Next release gates are the updated head's CI, ordinary SHA-pinned squash and landed-byte verification, then a normal render whose source watermark contains that squash and actual served-page acceptance. The real Terminal destination still requires sign-in in the existing selected Chrome tab. M1 Paper is parked independently. PR #9862 remains a separate petroleum-flow lane with a distinct clock and CI dependency closure.

## Historical implementation record

The account below preserves the earlier snapshots and failure evidence. Its old HEAD, fingerprint, test counts, capture references and publication-blocker statements are historical and superseded by the current status above.

## Verified local source · 20 October 2026

This record describes the source completed after recovery of the original “Upgrade commodities dashboard” session. It is an implementation and method record, not production acceptance. The original branch and worktree remain authoritative.

- Operation: `commodities-intelligence-r3-20261018a`
- Branch: `sol/web-commodities-intelligence-r3-20261018a`
- Accepted base: `654bbd3797ffe36b12410acbd6648184af6a1a9d`
- Review price snapshot: **2026-10-16**
- Projection revision: **5**
- Physical method revision: `eia-seasonal-balance-20261020-r2`
- Workspace evidence fingerprint: `e272f5d3492c9b91cc4b416281224c2eff79fd036f96c8a4f59f27bebba83497`

## Product result

WTI now presents US petroleum balance in the main Explore investigation and a compact Relationships continuation. Gold now presents its already published China premium context in those same paths. The panels connect evidence to questions about inflation, rates and business effects without promoting a selected explanation into a proven cause.

The former source-only description “no economic recomputation” is superseded for this slice: the review reconstructs **display-only petroleum measurements from exact accepted EIA series** through the existing owner. Gold, price, rate, FX, transmission and company-alias publications are consumed as accepted bytes. No collector, scoring, calibration, forecast or alert job ran.

## One petroleum owner

`engine/commodity_supply_context.py` owns both the legacy flat supply fields and the new dated context. `scripts/build_commodities.py::_oil_supply_read` remains a thin cache reader. The normal builder passes the selected price-series cutoff; legacy no-argument callers use the latest stored crude observation rather than the wall clock. The projection and review renderer call the same pure owner. The new context is not added to `latest.json` and does not feed conviction, alerts, scoring or forecasts.

The review renderer reads ten accepted EIA parquet blobs and accepted `config.yml` from the base commit. The render receipt records their exact file hashes, configuration identity, method revision and reconstruction scope. It also preserves the accepted company-alias isolation and canonical theme behavior repaired during recovery.

### Four-week change

The stock change is:

`stock at t − stock at exactly t−28 calendar days`.

Both endpoint observations must exist. Four available rows are not a four-week interval, and two nearby rows cannot substitute for the requested endpoint. Intermediate observations are not required for this endpoint difference.

### Stock divided by daily flow

The displayed days value divides the stock level by the mean of the configured number of positive, finite weekly observations of daily flow, ending on the stock observation date. Crude uses refinery net inputs; gasoline and distillate use product supplied. For the accepted four-observation setting, the required dates are 2026-09-11, 09-18, 09-25 and 10-02.

Every requested weekly date must exist. Future, stale, missing, zero or negative flow values cannot be borrowed to fill a denominator. The result is a stock-to-average-flow context measure, not a guarantee of supply duration or a global balance.

EIA describes product supplied as a consumption proxy derived from petroleum movements in the primary supply chain. It is not a direct reading of final retail purchases. Source: [EIA explanation of product supplied](https://www.eia.gov/todayinenergy/detail.php?id=63184).

### Existing seasonal method, now disclosed

For the trailing `years × 53` observations, the owner subtracts each observation's same-ISO-week mean. The latest anomaly is divided by the population standard deviation of those anomalies. The latest observation remains included, as in the existing method.

The accepted configuration targets five years and contains **265 observations from 2021-09-10 through 2026-10-02**, with six observations in the latest ISO-week group. This is the owner's descriptive seasonal anomaly; it is not EIA's published five-year range or a calibrated prediction. Short history, insufficient same-week coverage and zero/nonfinite variance yield no qualified anomaly.

### Dates and failure behavior

Observation date, analysis cutoff and release availability remain separate. The cache contains no release/vintage proof. Filtering observations to a date therefore does not establish that a historical reader could have known every revision at that date.

The projection accepts older, explicitly dated physical calculations; it refuses future calculation cutoffs or future observations/releases. A stock interpretation needs both a qualified nonnegative level and seasonal anomaly for the same date, correct units and adequate reference coverage. Conflicting duplicate dates, malformed dates, negative stock history or missing series degrade the affected evidence. A broad inventory conclusion needs the three relevant stock comparisons on the same observation week.

The descriptive stock states distinguish broad tightness, product-specific tightness, crude-specific tightness, near-normal stocks, ample stocks, mixed conditions and incomplete evidence. They do not count indicators as confidence. The legacy display average remains a separate compatibility field.

## Accepted WTI example

All values below belong to **week ending 2026-10-02**, fourteen days before the price snapshot. Release vintage is unavailable.

| Evidence | Commercial crude | Gasoline | Distillate |
| --- | ---: | ---: | ---: |
| Stocks, million barrels | 424.1 | 204.7 | 105.1 |
| Seasonal anomaly | −0.15 z | −2.03 z | −2.01 z |
| Exact 28-day stock change, million barrels | +0.1 | −2.2 | −1.1 |
| Stock / aligned average daily flow | 25.4 days | 23.3 days | 27.9 days |

The main interpretation is **“Product stocks tight; crude less constrained.”** It focuses the investigation on product supply, refinery operations and trade. It does not establish a crude supply disruption.

The separate inflation-expectation check remains unmet. The physical inventory reading cannot fill this missing transmission stage. If the price direction is absent or zero, a direction-specific inflation sequence remains unassessed.

Business consequences are conditional: product tightness makes refining margins and fuel pass-through worth checking; refiners still need product prices to outpace crude and operating costs; fuel users still need evidence about hedges and pricing power. No company recommendation is created.

## Gold regional context

The Gold view consumes the existing `data/commodity/latest.json` field `gold_context.china_physical_premium` directly. It does not introduce a premium collector or recompute the spread.

The accepted published observation is:

| Field | Published evidence |
| --- | --- |
| Method | `close_proxy` |
| Premium | +0.2795508933%, displayed **+0.28%** |
| Source time | **2026-10-14 07:30 UTC** |
| Published five-observation average | +0.2562922797%, displayed +0.26% |
| Published thirty-observation range | −0.1792775538% to +0.3826438861% |
| Official canonical benchmark available | false |
| Context-only qualification | true |
| Comparison currency | CNY |

The proxy converts SGE Au99.99 CNY per gram into CNY per troy ounce and compares it with the owner's aligned global XAU/CNY observation at the Shanghai close. It is indicative regional relative pricing, not an official canonical benchmark or a simultaneous executable trade.

The owner requires the relevant five or thirty observations for its statistics. The view uses those published values and labels observation counts; it does not relabel them calendar days. Intraday context does not borrow historical statistics from the canonical benchmark.

The visible proxy label, source clock and unavailable official benchmark survive the closed methodology disclosure. A positive regional premium can coexist with a falling global Gold price. Its sign does not prove stronger global demand, settle the existing conflicting rate readings or create a miners/equity signal.

Qualification checks cover method, units/currency, finite values, explicit context-only status, parent source date, metric source time and the owner's freshness field. Future timestamps, a source time after its parent publication, naive timestamps, unsupported methods and malformed/stale data degrade this context locally. Other Gold evidence remains usable.

## Investigation and export behavior

Both panels appear in Explore before the deeper evidence continuations. Relationships shows compact commodity-specific context. “Inspect physical” for WTI keeps the selected explanation and moves focus to the main physical panel. Gold's history link continues to its existing legacy owner panel.

Physical and regional evidence are retained in research exports and their fingerprint. Oil exports contain the dated petroleum context; Gold exports contain its regional context and exclude petroleum. Imported records preserve their original evidence and exact condition. An old fingerprint cannot silently adopt the changed semantics. The final DOM export is 74,842 bytes, within the existing 131,072-byte import limit.

A CSS descendant selector had styled numeric values as captions. Narrowing it to direct caption children restores main and session return size and color. The horizontal commodity strip now scrolls the selected chip into view without scrolling the page.

## Evidence and verification

| Check | Final result |
| --- | --- |
| Petroleum and decision-workspace Python suites | **41 tests and 25 subtests passed** |
| Rendered DOM journeys | **20 passed** |
| Anonymous Chromium journey | **22 checks passed** |
| WTI/Gold Explore captures | **16/16** |
| WTI/Gold Relationships captures | **16/16** |
| Earlier unchanged Overview matrix | **24/24 retained** |
| Design-system enforce-added | 0 blocking findings |
| Runtime style injection | Passed within existing allowances |
| Visual-evidence integrity | Passed |
| Whitespace | Passed |

The Python run emitted two preexisting pytest cleanup warnings for an old temporary Chromium directory. No source assertion failed. The tests cover exact calendar endpoints, aligned flow windows, date/ref qualification, negative/duplicate/missing inputs, stock classifications, inflation independence, Gold units/method/time failures, export semantics and strict template degradation.

The final browser confirms actual download/import, inactive monitoring, hypothesis preservation, partial-coverage switching, failed assistant load/retry, keyboard return focus, numeric hierarchy, mobile light/Chinese layout and no uncaught errors. Twenty overview returns were unobstructed at both representative viewport sizes. Twenty-four company continuations rendered; only the first link's exact routing contract was exercised, and its authenticated target was not opened.

The capture matrices cover desktop 1440×900 and mobile 390×844, EN/ZH, dark/light, anonymous access. No page-level horizontal overflow or console errors were recorded. Wider children inside bounded scroll containers are counted separately. The final Explore capture manifest is generated at 2026-10-20T11:50:23Z. Relationships was captured before the final Explore-only typography/strip correction; its visible layout is unaffected. Overview was retained rather than recaptured.

Independent native principal judgment accepted these actual final content-addressed samples:

- WTI desktop EN dark: `physical/evidence/2f1f43716953e039.png`
- WTI mobile ZH light: `physical/evidence/f81f1ddfb2171e7d.png`
- Gold desktop EN dark: `physical/evidence/d5ec268ecf1b0229.png`
- Gold mobile ZH light: `physical/evidence/f918ca0f704e2833.png`

An initial final-review request accidentally referenced historical content-addressed images. That evidence mismatch was reconciled against the final manifest before acceptance. Do not treat old PNG filenames as mutable “latest” paths.

Durable receipts are under `mockups/evidence/commodities-r3/`: `source/review-receipt.json`, `source/validation-receipt.json`, `source/dom-receipt.json`, `source/python-tests.txt`, `browser-journey.json`, and each page family's `EVIDENCE.yml`, `manifest.json` and `smells.json`. The validation receipt binds the implementation and evidence file hashes.

## Native Paper continuation, ready for the qualified owner

Continue the original [Paper file and page](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-L-0), using M1. Preserve the existing Overview board `6JKF-0`, WTI board `6K5V-0`, R2 and North Star material.

For the WTI board, use the accepted source composition: prominent price result; independent inflation interpretation; the dated petroleum conclusion; three equal stock columns on desktop or stacked sections on mobile; paired inflation/business implications; expandable activity, reference-window and source detail. Keep “14 days before the price snapshot” and unavailable release vintage above the numbers. Carry the selected explanation into Relationships without confirming it.

Gold's continuation uses a prominent price result, the existing unresolved rate interpretation, a neutral regional premium value, close-based proxy label, source clock and unavailable official benchmark, followed by owner-defined comparisons and method/history access. No new Paper board was created and no destination board is invented here.

Canonical tokens, bilingual strings and verified hierarchy are already represented by the source and final captures. Apply these to native Paper only after the protected M1 catalog is qualified, then inspect native output. These browser captures do not prove native Paper completion.

## Remaining release work

The source slice is complete locally. The original typed publisher and M1 Paper catalog remain held. See `research/COMMODITIES_R3_RECOVERY_2026-10-20.md` for the exact failures, exhausted retry boundary, original identities and required current-main integration. No commit, push, PR, merge, deployment or Paper edit occurred in this continuation.
