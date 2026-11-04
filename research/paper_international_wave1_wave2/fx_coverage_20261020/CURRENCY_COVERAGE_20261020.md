# International country currency coverage — 20 October 2026

## Outcome and scope

The country cockpit now has a qualified, independently dated three-month currency return for all seven economies in the retained preview. The normal international engine assembles the same contract from its existing FX store; the country assessment validates it before rendering. The change completes the previously unavailable currency reading while keeping the country thesis, economic path, policy and fiscal position as the primary experience.

This increment is implemented and locally verified in the existing International workspace. Its source and evidence remain uncommitted after frozen local HEAD `11c83bb5dfb0c8199a0fb0cb2c6e70452c724984`. Remote PR9596 still points to `88b6f192c3e2a7a94f5cf7ff4d9d06bc225324a4`. The original uncertain push remains the publication fence. The new data qualifier did not populate the canonical store or establish production adoption.

Review references:

- [R12 country research design](https://app.paper.design/file/01M3P1TW5Y3XWQC37ADDS8K5AG/p-G-0)
- [Existing draft implementation carrier, PR9596](https://github.com/mastermindx-market-intelligence/macro/pull/9596)

## Useful behavior on the page

Each country shows the local currency's value change against USD, its actual observation date and a link to its source history in the existing disclosure. The main caption explicitly identifies USD and the three-month window. The source table includes both endpoint dates; a concise method disclosure explains appreciation, quote orientation and the calendar reference.

Currency and equity clocks remain independent. The qualified currency window ends on **19 October**; the retained equity replay remains dated **15 October**. The country heading now says “Equity observations” so it cannot imply that the equity date also dates the currency reading.

Values remain available but visibly dated after four days. They disappear after fourteen days or when source identity, endpoint validity or reference coverage is insufficient. A current page build cannot refresh an older observation. Missing data remains unavailable rather than using the legacy regime strength scalar.

Visual review also found inherited desktop and mobile caption selectors that reduced the size and state color of translated trend values. Both caption rules now apply to direct label elements, allowing English and Chinese values to inherit the intended value typography. The final browser verification follows both repairs and confirms the value and translated text use 17px on desktop and 15px at the mobile and narrow widths in all 84 country states.

## Retained source result

The acquisition used the incumbent Yahoo Finance source and the already configured seven tickers. Each ordinary TLS request returned HTTP200 once. The original response bodies, requested/final URLs, receipt times, byte lengths and SHA-256 values are retained under this directory. No alternate provider was introduced.

All seven responses contain **133 timestamps, 132 valid daily quotes and one missing quote**. The qualifier checks instrument type, quoted currency, ticker/registered alias, daily granularity and timezone. Native timestamps are interpreted in UTC and converted to the provider's London quote dates. Timestamps after actual receipt are rejected.

| Economy | Currency | 3-month USD-value change | Actual quote dates |
|---|---|---:|---|
| Japan | JPY | +2.90% | 17 July → 19 October 2026 |
| South Korea | KRW | +10.91% | 17 July → 19 October 2026 |
| Taiwan | TWD | −0.38% | 17 July → 19 October 2026 |
| India | INR | +1.76% | 17 July → 19 October 2026 |
| Australia | AUD | −0.39% | 17 July → 19 October 2026 |
| United Kingdom | GBP | −1.06% | 17 July → 19 October 2026 |
| Euro Area | EUR | −1.92% | 17 July → 19 October 2026 |

The calendar reference date is **19 July**; the last available quote on or before it is **17 July**. The two-day gap is retained explicitly. Exact quotes, unrounded 40-digit Decimal results, original response hashes and source URLs are in `source_qualification.json`. These are snapshot results, not a claim about prices after the recorded acquisition.

The source history URLs use the incumbent instruments:
[JPY](https://finance.yahoo.com/quote/JPY%3DX/history/),
[KRW](https://finance.yahoo.com/quote/USDKRW%3DX/history/),
[TWD](https://finance.yahoo.com/quote/USDTWD%3DX/history/),
[INR](https://finance.yahoo.com/quote/USDINR%3DX/history/),
[AUD](https://finance.yahoo.com/quote/AUDUSD%3DX/history/),
[GBP](https://finance.yahoo.com/quote/GBPUSD%3DX/history/) and
[EUR](https://finance.yahoo.com/quote/EURUSD%3DX/history/).
The mutable history pages are source references; the retained response archives establish this exact observation.

## Calculation and backend decisions

`lib/intl_currency_observation.py` owns the display contract. For quotes in local currency per dollar, the currency return is `100 × (start / end − 1)`. For quotes in dollars per local currency, it is `100 × (end / start − 1)`. The inverse conversion matters: a quote moving from 25 to 30 represents a 16.67% loss of local-currency value, not a 20% loss.

The window is three calendar months, with month-end clamping. The producer selects actual observations, accepts a reference quote up to seven days before the calendar target, and withholds an end quote older than fourteen days. Identical duplicates collapse; conflicting selected observations are withheld. Invalid prices, dates, oversized numerics and malformed serialized values cannot escape into the display.

Captured responses retain their acquisition cutoff. An intraday quote captured on 20 October cannot become eligible merely because that same response is replayed on 21 October. Both producer and consumer enforce the earlier of the evaluation day and recorded UTC capture day. Freshness continues to age against the evaluation day.

The existing store has no retained retrieval receipt on these frames, so configured-store source context leaves retrieval/hash fields null. The UI describes dated daily quotes; it does not assert finalized official closes. Source URLs and self-digests do not masquerade as external authentication. The qualification script separately binds the calculation to original response bytes and the complete normalized history.

The normal engine adds `currency_observation` at the existing store assembly boundary. The legacy 63-observation strength scalar, macro clock and regime history are preserved. The assessment's default day now uses UTC, matching the engine. The existing preview helper accepts an optional currency replay through the same display validator. No new collector, API service, comparison owner, Saved store or controller was introduced.

## Verification

| Gate | Recorded result |
|---|---|
| Selected country, forecast, policy, currency, legacy component, build and shared navigation/footer suite | 298 passed; two existing pytest cleanup warnings |
| New currency contract cases within that suite | 80 passed |
| Qualified retained source histories | 7 of 7; independent endpoint selection and Decimal arithmetic |
| Final integrated country browser matrix | 84 of 84; seven countries × three widths × two themes × two languages |
| Explicit ageing controls | 8 of 8; same retained record evaluated later, across narrow dark/light and EN/ZH |
| Browser history | Back to India and forward to Korea pass |
| Page errors in the final browser matrix | 0 |
| Existing design, visual-evidence and tracked-whitespace gates | Pass |
| Paper | Six applied effects; 20 text nodes, 12 style properties and 4 node orders verified; four boards finished |

The final browser matrix ran **04:50:31–04:51:56 UTC on 20 October**. It verifies displayed values, currency basis, separate dates, source links, quote orientation, accordion behavior and visible document width down to 320px. It also checks that dated values use the muted presentation and stale values disappear. The time-shifted ageing controls are explicitly test controls; none changes a source quote or acquisition clock.

The local suite ran before the final CSS-only caption correction. Its financial and template source remained unchanged afterward; the final browser and design gates verify that last CSS delta. The initial overflow and capture-boundary failures are retained with their pre-fix source snapshot. The two earlier passing browser runs and their source/captures are retained in `browser_before_typography_fix.tar.gz` and `browser_before_mobile_typography_fix.tar.gz`; final evidence follows both breakpoint repairs and is separately bound.

The existing CI catalogue is extended for the new currency contract, its tests and the retained fixture. All seven jobs that explicitly name `engine/intl_run.py` now also name the currency helper; the foundation job explicitly includes and executes the new test and includes its fixture. The canonical shared `curated_exclusive_closure_findings` and `gated_unrun_suites` functions ran **04:58:54–05:01:21 UTC**, with **zero uncovered import closures and zero unwired suites**. Their actual current-working-tree result and unchanged source fingerprints are retained in `ci_dependency_coverage.json`. This is not hosted PR-versus-base contract-delta.

## Paper and evidence custody

The revised overview boards are desktop dark `DMX-0`, desktop light `DW7-0`, mobile dark `E4D-0` and mobile light `EC2-0`, on the existing R12 page. They show KRW +10.91%, the 19 October currency date, the 15 October equity date and the 20 October design reference date. The UK and Taiwan detail boards remain covered by the unchanged fiscal parent receipt.

Every Paper mutation has its original observed response retained. Original native JPEG bytes, before/final JSX and focused currency captures are bound by `paper_currency_coverage_receipt.json`. Paper normalized the footer's line-height to 12px after applying the 10px token font; that observed single-line result was visually accepted and recorded. The browser implementation uses its own responsive token rules.

Final country, integrated International and integrated stock HTML are retained losslessly with checksums. The integrated fixture uses the real existing templates in a fresh anonymous Chrome context, with external requests blocked. Its shared missing live configuration, blocked analytics, authenticated/degraded-state gaps and hidden legacy width counters remain fixture limitations. Actual visible country geometry and document widths pass.

The completed fiscal checkpoint and its exact snapshot of 13 source files remain unchanged. The corrected September 30 IMF information cutoff, 73-record publication archive, policy admissions and public-asset repair retain their prior custody. This increment does not rewrite their historical verification results.

## Release continuation

The original push action `d07df7c6e45d35c54338808701350ece97c605401ad69a0fd28bb415d05a5a56` remains `EFFECT_UNKNOWN / PUSH_RESULT_UNCERTAIN`. The installed publication surface still exposes status rather than an action-bound recovery operation; no new resolution was obtained and no push was replayed. The last owner recovery check remains 20 October 01:52 UTC.

Continue on PR9596 only after the existing publisher owner canonically resolves that original action. Then publish the complete reviewed increment, satisfy the actual combined-source hosted CI and independent release review, consume the genuine Sector Central Full RIG approvals, resolve the Session Bridge through its owner, and use the normal main render and updater path. Served acceptance must confirm the actual new source, public assets, ordinary country records and user journeys. PR8754's separate rights, browser, Saved and release obligations remain independent.

The complete source and evidence inventory is bound in `CURRENCY_COVERAGE_20261020.json`. PR metadata maintenance is recorded separately and does not advance source refs or establish release acceptance.
