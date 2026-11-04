# International Markets R12 — country outlook and research contract

- Date: 19 October 2026
- Source owner: `intl-country-cockpit-20261018`
- Branch: `sol/web-intl-country-cockpit-20261018`
- Delivery: [Macro PR 9596](https://github.com/mastermindx-market-intelligence/macro/pull/9596)
- Design: [Country Intelligence · R12](https://app.paper.design/file/01M3P1TW5Y3XWQC37ADDS8K5AG/p-G-0)

## Product decision

The main job is to explain a country's economy and markets: the current mechanism, the published path ahead, what market observations show, and which developments would change the reading.

The page opens with the actual world forecast and a seven-country research rail. Each country has a concise thesis, growth and annual-inflation paths, dated policy evidence, external and fiscal context where verified, market observations, transmission channels, and two conditional paths. Detailed source tables are available within the country. Existing comparison, history and saved-research tools sit beneath the analysis.

Reviewed national mechanisms lead when their evidence is eligible. The numerical forecast remains adjacent, with its own institution and publication date. For example, the UK leads with the energy–labour policy tension; Taiwan leads with AI demand and the high comparison base. A dated national assessment does not replace the IMF's separately dated forecast.

The incumbent International builder and page publisher remain the integration points. This increment adds collector and interpretation code to that existing path.

## Verified October quantitative baseline

The October IMF Statistical Appendix was published with the [13 October WEO](https://www.imf.org/en/publications/weo/issues/2026/10/13/world-economic-outlook-october-2026). Its report information cutoff is 1 October. The parser reads the [official statistical tables](https://www.imf.org/-/media/files/publications/weo/2026/october/english/tablea.pdf), retaining table and row identity.

| Economy | Real GDP growth, 2026 → 2027 | Annual-average CPI, 2026 → 2027 |
|---|---:|---:|
| Japan | 0.7% → 0.7% | 2.0% → 2.6% |
| South Korea | 3.3% → 2.8% | 2.7% → 2.3% |
| Taiwan | 10.7% → 4.3% | 2.0% → 1.8% |
| India | 7.0% → 7.0% | 5.0% → 4.4% |
| Australia | 1.9% → 1.6% | 3.9% → 3.1% |
| United Kingdom | 1.3% → 1.2% | 3.3% → 2.8% |
| Euro Area | 1.1% → 1.2% | 3.1% → 2.8% |

India's labels are FY2026/27 and FY2027/28 for the admitted GDP, inflation and current-account series. Fiscal-year interpretation is attached to each series.

The world GDP record is 3.1% → 3.4%. Its AI/energy explanation is bound to the exact reviewed world record. A corrected record, a missing following period, or a later edition cannot inherit that explanation automatically. The heading follows the selected numerical path.

The archive contains 37 publications: seven earlier GDP records, 28 October WEO records including the world aggregate, and two September CBC forecasts. Historical points are called published history unless the source establishes actual status. The chart distinguishes that history from projections.

## Policy and independent national forecasts

The [Bank of England September decision](https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2026/september-2026) records a 6–3 vote to hold Bank Rate at 3.75%; the meeting ended on 16 September and the decision was published on 17 September. The three dissenters preferred 4%. The reading preserves the documented energy-price risk and soft-labour trade-off without predicting the next vote.

The [CBC's 17 September decision](https://www.cbc.gov.tw/en/cp-448-192883-c5fa1-2.html) holds the discount rate at 2%. It also provides annual GDP forecasts of 11.48% and 5.82%, and headline CPI forecasts of 2.03% and 1.83%. These are separate CBC views. Their differences from the October IMF path are not revisions by either institution.

National decisions retain their instrument names, previous and effective settings, action, publication date, effective date, material vote information and rationale. BIS monthly history remains separate. An unchanged rate can be freshly verified at a new meeting. Monthly averages are not treated as contradictory end-of-period observations.

## Collector and interpretation implementation

- `collectors/intl_weo.py` reads the registered October tables. It checks table identity, units, annual columns and row structure. Quarterly growth, end-period inflation and gross/net debt columns cannot silently substitute for the configured measure.
- `config/intl_country_releases.json` explicitly registers the supported WEO edition. A future release requires a reviewed parser contract.
- `collectors/intl_policy_sources.py` checks the two registered national releases. Revised statements, ambiguous annual figures or changed votes fail qualification independently.
- `collectors/intl_country_sources.py` combines those records with the existing official inputs, preserves source receipts across partial refreshes, and retains accepted evidence when one source fails.
- `lib/intl_forecast_vintages.py` maintains an immutable publication archive, ordered corrections, withdrawal custody, provider-specific revisions, reporting periods and strict knowledge cutoffs.
- `lib/intl_policy_evidence.py` qualifies the national instrument and reconciles known versions before deciding whether an announcement is effective.
- `lib/intl_country_outlook.py` derives evidence-linked propositions for growth, inflation, balances, policy and macro–market divergence.
- `lib/intl_country_assessment.py` selects the visible thesis and binds its conditions to the evidence identities. Each build requalifies them. Conflicting policy rationale or newer contradictory policy evidence cannot leave the old national thesis active.
- The existing `collectors/intl_macro.py` refresh path and `scripts/build_intl.py` carry the result into the production International template.

The annual-inflation policy mechanism is explicitly labeled as interpretation. When a verified national decision exists, its own sourced policy section supplies the visible trade-off. A lower annual CPI forecast alone does not establish the central bank's policy room.

Market explanation states the index's measured position relative to its 50- and 200-observation averages. It does not infer slope, improvement, an unbroken trend, or causation from that static position. Fiscal-balance and debt conclusions remain in shares of GDP; they do not infer nominal borrowing or refinancing amounts.

## Admission and acquisition evidence

The verified October tables are 437,719 bytes, SHA-256:

`201e6b671bb7deb6da3065976f8020b50831da1aa9ea57edd9a2ab7458c215c8`

The successfully downloaded Bank of England HTML is 124,687 bytes, SHA-256:

`c083950372d3fddc124d4089753e4178d32bcfb1f755260e2a1a37ef520ec2c1`

The CBC decision and annual forecasts were verified from the full official public page. The connected-host HTML download failed certificate validation. TLS verification was retained. The baseline admission therefore has no claimed CBC raw-byte hash. The CBC parser test is explicitly a minimal contract fixture, not a recorded successful retrieval.

The new national decisions were admitted at `2026-10-18T23:56:41.276358+00:00`. Source publication dates, acquisition clocks and first-known/admission clocks have different meanings. A fresh download does not make an old economic period current.

Source receipts, errors and their observation clocks remain in the baseline and generated manifest. Existing failures from older source attempts are retained as dated diagnostics, not presented as fresh failures.

## Failure behavior and coverage limits

The currently verified national-decision set is the UK and Taiwan. Other countries retain their eligible, dated bank assessments and monthly history. A newer RBI decision was not admitted without adequate primary evidence.

Fiscal balance and gross government debt were verified for Japan, the UK and the Euro Area. They remain unverified for Korea, Taiwan, India and Australia in this increment. The country disclosure identifies that missing coverage. The Japanese gross-debt series retains its nonconsolidated-coverage note. The Euro Area current account uses the adjusted series; its equity proxy is still the wider STOXX Europe 600.

The archive rejects malformed values, ambiguous corrections, impossible periods and conflicting same-release records. Strict operational replay excludes evidence not yet known at its cutoff, including monthly policy observations. Announced future-effective decisions do not become today's setting.

The full WEO database and investigated Fiscal Monitor/DataMapper download routes were not successfully qualified. No substitute current fiscal figures were fabricated. Their absence does not erase the verified growth, inflation, current-account or national-policy records.

## Design and verification

Paper R12 has six completed references: desktop and mobile in both themes, plus UK policy/fiscal and Taiwan policy/independent-forecast detail states. Its 67 observed effects and final visual reviews are recorded in `paper_r12_receipt.json`. The design uses the existing Mastermind tokens and Inter. Data paths, labels, dates, contrast, repeated rows and artboard fit were reviewed.

The affected Python suite passes **160 tests** across nine files. The four warnings concern three existing Pandas deprecations and an unrelated historical pytest temporary-directory cleanup. The new claim tests cover world corrections, national-thesis dependency changes, conflicting rationale across official URLs and bank-name aliases, stale commentary, conditional policy wording, fiscal-ratio wording, and CBC annual-versus-half-year/core-inflation parsing.

The integrated Chrome verification covers **12 viewport/theme/language states and 10 journeys**. It checks all seven country paths, world aggregation, fiscal-year labels, independent forecasts, named national decisions, narrow-screen chart labels, keyboard/history behavior, legacy links, source disclosures, assistant focus, denied legacy assets and JavaScript-disabled reading.

Generated evidence uses the real International template and local asset routing in an isolated browser. It is not authenticated production evidence. Current HTML hashes, screenshots, commands and results are recorded in the final verification receipt. Paper completion and local browser success do not stand in for hosted CI, release review or served production acceptance.

## Delivery ownership

The repaired repository-aware publisher has already established the branch and draft PR 9596 at parent `9eb408279e7ea8de99a667e296c4b0ddebfd799b`. This increment remains on that original registered operation and typed commit/push path. The earlier PR8754 carrier and its independent unresolved obligations remain separate historical work.

Next gates are publication of the exact verified contents, hosted CI and any required independent release review, followed by the real served page and source/asset checks. The adjacent evidence records are the authoritative account of what was actually observed.
