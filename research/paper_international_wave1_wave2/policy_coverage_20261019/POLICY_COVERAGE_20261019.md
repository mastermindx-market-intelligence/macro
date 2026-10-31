# International Markets — seven-bank policy coverage and completed design update

Recorded for the existing International Markets release on 19 October 2026. This record describes the additional working-tree implementation after local commit `11c83bb5dfb0c8199a0fb0cb2c6e70452c724984`; it does not describe a production deployment.

## Product outcome

Country analysis remains the primary experience. The page leads with a World Brief and seven country assessments, then exposes the growth and inflation path, monetary-policy decision, external and fiscal conditions, observed market context, transmission channels, and the evidence that could change each assessment. Country comparison, history and saved research remain secondary.

This increment fills the largest remaining gap in the country assessment: qualified monetary-policy decisions now cover Japan, Korea, Australia, the Euro Area and India in addition to the existing UK and Taiwan decisions. Each decision names the actual instrument, distinguishes announcement from effectiveness, explains the bank's reasoning, and exposes the primary and supporting sources. The implementation preserves uncertainty and conditional language.

Four national headlines were revised in both languages and in the four primary Paper layouts:

| Economy | Revised English headline |
| --- | --- |
| Japan | Wage inflation keeps normalization in play |
| Australia | Inflation persists as demand cools |
| Euro Area | Resilient growth faces an energy constraint |
| India | Strong demand meets renewed inflation pressure |

Korea's existing export-and-rates assessment remains in place. UK and Taiwan research retains its previously qualified publication and observation clocks.

## Newly qualified policy evidence

Rates are percentages; each newly admitted change is 25 basis points. These are bank decisions, not a rate forecast or an investment recommendation.

| Economy | Instrument | Prior → new setting | Decision / publication | Effective |
| --- | --- | --- | --- | --- |
| Japan | Uncollateralized overnight call-rate target | Around 1.00 → around 1.25 | 18 September 2026 | 24 September 2026 |
| Korea | BOK Base Rate | 2.75 → 3.00 | 27 August 2026 | 27 August 2026 |
| Australia | Cash rate target | 4.35 → 4.60 | 29 September 2026 | 30 September 2026 |
| Euro Area | Deposit facility rate | 2.25 → 2.50 | 10 September 2026 | 16 September 2026 |
| India | Policy repo rate | 5.25 → 5.50 | 7 October 2026 | 7 October 2026, immediate |

The five main documents and six supporting documents were acquired as original bytes over normal TLS on the connected host between 09:33:51 and 09:33:57 UTC. All eleven returned HTTP 200. The acquisition record preserves exact URLs, byte lengths, SHA-256 hashes and retrieval clocks. The temporary byte custody remains under `/tmp/intl-policy-coverage-20261019`; the repository stores qualification metadata and hashes without republishing the full official articles.

The qualification pass completed at 09:42:39.585914 UTC. Normal ingestion assigned the five baseline records first observation at 09:46:23.036453 UTC. Five verified review events were subsequently added at 09:59:11.274191 UTC. The intermediate qualification record retains its own earlier evaluation timestamp; it is not substituted for the baseline's ingestion clock.

The existing GB and TW decision identities remain unchanged. No new successful Taiwan byte acquisition or new UK/Taiwan verification timestamp is asserted. The 37-record forecast archive, official observation series, and earlier IMF/Taiwan acquisition failures retain their existing identities and clocks.

### Primary sources and the facts they establish

- **Japan:** [BOJ decision](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260918a.pdf) and [decision reference](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260918b.pdf). The displayed current and prior settings retain “around.” The rationale preserves the 7–2 proposal result without inventing a structured vote breakdown.
- **Korea:** [BOK decision](https://www.bok.or.kr/eng/bbs/E0000634/view.do?depth=400423&depth2=400417&depth3=400423&menuNo=400423&nttId=11064193&oldMenuNo=400423&pageIndex=1&pageUnit=10&programType=newsDataEng&searchCnd=1&searchKwd=) and [official rate-change history](https://www.bok.or.kr/portal/singl/baseRate/list.do?menuNo=200761). The history establishes the actual rate-change date; six members supported the increase and one preferred a hold.
- **Australia:** [RBA decision](https://www.rba.gov.au/media-releases/2026/mr-26-27.html) and [cash-rate history](https://www.rba.gov.au/statistics/cash-rate/). The decision is described as unanimous; no unreported numeric vote count is added.
- **Euro Area:** [ECB decision](https://www.ecb.europa.eu/press/pr/date/2026/html/ecb.mp260910~314e508016.en.html), [key-rate history](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html), and [press-conference statement and questions](https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2026/html/ecb.is260910~6a45359cfc.en.html). The deposit facility is the named instrument. The separate question-and-answer source supports unanimity; an attendance count is not treated as a vote count.
- **India:** [RBI decision](https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=63742) and [implementation circular](https://www.rbi.org.in/scripts/BS_CircularIndexDisplay.aspx?Id=13727). The rate vote is 6–0, while the stance vote is 4–2; they remain separate. This increment does not admit the release's fiscal-year forecasts into the forecast archive.

Machine evidence: [acquisition](source_qualification/acquisition.json), [body contracts](source_qualification/body_contracts.json), [qualification results](source_qualification/admission_attempt.json), and [qualified records](source_qualification/qualified_policy.json). The current accepted baseline remains `config/intl_country_baseline.json`.

## Backend behavior and correction handling

The ordinary International collector, input loader, assessment builder and page builder own this work. There is no separate ingestion or publication service.

The policy normalizer accepts only the seven named official providers and their exact instruments. It validates HTTPS source identities, decision/publication/effective dates, support roles, hashes and observation clocks. Japan's qualified target cannot silently become an exact rate. Monthly comparisons require a matching instrument, end-of-period convention and qualifier.

HTML qualification binds stable decision and rationale content while excluding navigation. The two Japan PDF identities are byte-bound and subject to size, page and extracted-text limits. Primary and supporting documents have distinct acquisition receipts.

A failed download preserves prior evidence and reports a download failure. A successfully downloaded source that no longer qualifies creates a dated review event. That event can withdraw the visible setting, rationale and dependent national commentary. A failed first qualification is represented even when there is no previously accepted decision; it cannot leave the dependent commentary silently eligible.

Current effective decisions and future-effective announcements are qualified separately. An accepted future announcement cannot restore an earlier effective decision whose own evidence was withdrawn. A different official release URL likewise cannot certify the selected release.

Historical reconstruction uses the earliest valid complete record for an identical policy identity, preserving its own hash and supporting receipts together with its observation timestamp. Ordinary ingestion still prevents incoming records from backdating themselves. Same-instant failure wins over success; event selection respects the knowledge cutoff.

National interpretation is retired when superseded by a newer selected or announced bank publication. Conditional mechanisms remain conditional: persistent import costs could require more Japanese tightening, and broader price pressures could prolong Indian tightening. The page does not promise either response.

### Consumed principal findings and regression proof

The final independent static review identified three concrete failures: a future announcement masking withdrawal of the current setting, baseline-first reconstruction discarding earlier valid custody, and a failed first qualification leaving national commentary eligible.

Seven focused regressions were run before the fixes, and all seven failed. They cover those failures, announcement qualification, release-URL binding, and retirement of old national commentary. The repaired implementation then passed the full affected suite selection. This is advisory principal review plus executable verification, not formal release approval.

## Frontend and Paper evidence

The existing [Paper R12 Country Intelligence page](https://app.paper.design/file/01M3P1TW5Y3XWQC37ADDS8K5AG/p-G-0) now contains the four revised national headlines and an expanded Korean policy section in desktop/mobile and dark/light.

The policy section sits directly after the growth path. It shows the BOK instrument, 3.00% setting, 25-basis-point move from 2.75%, decision and effective dates, a concise explanation, and source labels. Existing policy tiles were moved and expanded; the old monthly policy tile no longer occupies a duplicate vital-statistics slot.

The native Paper app returned **14 observed applied effects**, including a final finish operation on the four owned boards. The update contains 32 existing text-node replacements, four new rationale sections and four new source rows. All 16 country-headline readbacks passed. Four actual JSX extractions and three native returned images are saved. The root visually inspected the updated dark desktop, mobile policy section and full light mobile layout.

The original six-board R12 receipt remains immutable. The new [Paper update receipt](paper_policy_coverage_receipt.json) describes only this additional scope. Paper's legacy file display name still contains R10; the edited page and boards are the explicitly identified R12 references. No design-host identity is claimed. Paper JSX renders source labels as styled divs; functional source URL rendering is established by the browser evidence, not by claimed Paper link-click tests.

### Fresh verification

| Scope | Result | Evidence |
| --- | --- | --- |
| Six policy/country/forecast/interpretation suites | 263 passed | [Run receipt](tests/policy_country_tests_v3.json), [log](tests/policy_country_tests_v3.log) |
| Normal International build and shared public HTML | 10 passed | [Run receipt](public_html_tests.json), [log](public_html_tests.log) |
| Canonical rest-state captures | 12 of 12 captured | [Canonical manifest](../../../mockups/evidence/intl-policy-coverage-20261019/manifest.json) |
| Country browser checks | 84 of 84 passed | [Browser receipt](browser_verification.json) |
| History navigation | Back to JP and forward to KR passed | [Browser receipt](browser_verification.json) |
| Paper country-headline readbacks | 16 of 16 passed | [Readback](paper/country_copy_readback.json) |

The 12 display states are 1440/390/320 widths × dark/light × English/Chinese. The 84 checks cover all seven countries in each state: exactly one country open, current setting and clocks visible, actual source URLs rendered, Japan's current/prior qualifier retained in both languages, and no visible country-policy overflow. No JavaScript page exception occurred.

Both Python runs reported the same two unrelated existing Chrome.app temporary-cleanup warnings. The canonical anonymous fixture records a missing `live_config.js` and a blocked external analytics request. Authenticated free/essential/pro states and synthetic loading/empty/stale/error states were not captured. The generic observer counts some wider elements inside hidden legacy DOM on narrow viewports; document-level horizontal overflow is false, and the 84 visible country checks fit. These limitations remain in the raw manifest.

The integrated preview was rendered at **10:52:46.415903 UTC**. Its HTML bytes were preserved after browser verification. The two integrated snapshots are stored as lossless `.html.gz` archives so their inherited legacy whitespace does not create source-diff noise. Their exact decompressed hashes are verified against the browser-tested content. The manifest records the archives and the additional Paper-reference receipt.

To restore the two original HTML snapshots for a local replay, run `gzip -dk preview/intl_integrated_preview.html.gz preview/intl_stocks_integrated_preview.html.gz` from this evidence directory. Decompression recreates the exact original bytes; it does not render a new page.

| Preview | SHA-256 |
| --- | --- |
| Country preview | `88befdc1844728e0c9ab2c022ebcbbbe9bd9a9833acbbbf1b88518659a284cf6` |
| Integrated International preview | `3c72e6b3f8e01095e5eecafad4ce2ee91fec89d011aca7a3dda21b5256820d74` |
| Integrated stocks compatibility preview | `f811c34d59e599ac29919fcba6c88cd6527f479c8c6b1b9f15903eb7f309a3a1` |

The frozen market replay still has its October 15 market clock. A newly rendered page does not make that market data current. The repository's design ratchet and canonical visual-evidence gate both pass on the working-tree UI delta; the design check reports zero introduced blockers. Tracked-source whitespace passes. The new text-evidence check also passes after lossless archiving of the two raw integrated HTML snapshots and preservation of the original render log. These results and the final file fingerprints are bound separately by `POLICY_COVERAGE_20261019.json`.

## Fiscal research still pending

A new official Australia Article IV route was investigated. Table 1 provides candidate fiscal-year values for general-government net lending/borrowing and gross debt. The original PDF-byte acquisition returned HTTP 403, and Table 2 plus debt-coverage reconciliation remains incomplete. The Article IV candidate remains separate from WEO, with explicit June fiscal-year ends and a null precise fiscal information cutoff.

The [candidate qualification record](australia_fiscal_candidate.json), [research explanation](australia_fiscal_candidate.md), and [actual acquisition receipt](australia_fiscal_acquisition.json) preserve the usable findings and exact obstacles. No candidate value was admitted. Missing fiscal balance and gross debt for KR/TW/IN/AU remain missing.

## Release identity and remaining acceptance

| State | Identity |
| --- | --- |
| Existing draft PR | [macro #9596](https://github.com/mastermindx-market-intelligence/macro/pull/9596) |
| Last observed remote head | `88b6f192c3e2a7a94f5cf7ff4d9d06bc225324a4` |
| Frozen local head | `11c83bb5dfb0c8199a0fb0cb2c6e70452c724984` |
| Current increment | Uncommitted working-tree changes after the frozen local head |
| Original uncertain push | `d07df7c6e45d35c54338808701350ece97c605401ad69a0fd28bb415d05a5a56` |

The original typed push remains `EFFECT_UNKNOWN / PUSH_RESULT_UNCERTAIN`. The subsequent read-only status shows the different local and remote heads; that observation does not settle the original attempted write. The inspected publisher-owner record still lacks a post-install or original-action resolution receipt. No commit, retry, alternate publisher, Ready transition, merge, deployment or restart was performed.

The previously verified public-asset repair remains in the same working tree: nine exact CSS/JS dependencies admitted to the existing serving rules, with 28 passing boundary tests and real Caddy adaptation proving only the intended additions. Its three source-file hashes are rechecked against the immutable [asset repair receipt](../PUBLIC_ASSET_REPAIR_R12_20261019.json).

Once the original publisher action is resolved by its owner, publish the actual combined head through the existing lane, satisfy its CI and required review dependencies, merge through the normal protected flow, observe a covering render, and prove adoption by the existing macro-update owner. Final acceptance requires the repaired anonymous versioned assets, served page, cache behavior and actual country cockpit to work. Updater success alone does not prove that acceptance. The inherited Full RIG and Session Bridge review boundaries remain separate; native advice does not replace them.

The completed local implementation, evidence and Paper update are concrete. The live International page remains unaccepted until that release and served-path proof completes.
