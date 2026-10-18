# International Markets — country analysis rebuild

## Chairman mandate and product outcome

The Chairman’s October 17 rebrief rejects the R10 feature-led hierarchy. The primary product now explains each country’s economic condition, relevant policy and market evidence, published growth path, transmission channels, and developments that could change the view. Comparison, Saved and other legacy research tools remain subordinate.

The implemented hierarchy is World Brief → Country Assessments → Global Connections → Data & research tools. Seven economies are covered: Japan, South Korea, Taiwan, India, Australia, the United Kingdom and the Euro Area. All country headers expose both forecast years before expansion. India retains its fiscal-year basis. The Euro Area identifies STOXX Europe 600 as a wider European equity proxy.

A country’s economic outlook does not determine its equity trend. Realized observations, source forecasts and conditional interpretations remain separate. There are no invented country investment scores, scenario probabilities or price targets.

## Source and execution ownership

- Repository base: macro main `1ed4b870a426ff3cafb439152072c5bf47858551`.
- Operation: `intl-country-cockpit-20261018`, lane `web`, repository `macro`.
- Branch: `sol/web-intl-country-cockpit-20261018`.
- Workspace: `/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018`.
- Mastermind bootstrap pin: `ebe2de8f0d94310241362874ec9262ba572a63d2`.
- Original PR #8754 and its preserved worktree remain untouched. Its release, rights, migration, browser and review holds are not cleared by this work.

The research-only Fabric summon `intl-country-analysis-input-audit-20261018` returned INVALID_ARGUMENT before any job or attempt handle. It was not retried and does not prove global Fabric unavailability. Native consultations supplied principal product and publication judgments; they were not used as routine implementation or research workers or as formal release reviewers.

## Implementation

`lib/intl_country_assessment.py` builds an immutable, dated presentation model. It separates equity observation dates from document generation dates, withholds undated currency readings, requires a complete 200-observation trend window, and discloses the 252-observed-close high reference. Malformed numbers, future or expired source vintages, duplicate country identifiers and unsupported units cannot become current readings.

`collectors/intl_country_sources.py` parses bounded public BIS archives and fixed official forecast vintages. It streams the large policy CSV, rejects private/estimated/wrong-unit observations, and measures changes over three calendar months. Independent source errors and malformed refresh payloads retain last good values and their original dates. The existing `IntlMacroAdapter` owns refresh and atomic publication; the renderer makes no network requests.

`lib/intl_country_inputs.py` combines the attributed initial baseline with later successful collector output. Checked-in country commentary supplies dated BOJ, BOK, RBA and ECB interpretations; other countries use the available observations and attributed forecast with explicit conditional mechanisms.

The new Jinja/CSS/JavaScript composition renders through the existing International publisher. Native disclosures provide the complete reading path without JavaScript. Country selection, keyboard focus, URL history, legacy deep links and the existing tools state owner are retained. Stock mode remains outside the new page class.

The International-specific shell prevents legacy double insets and decorative heading rails from distorting the research layout. The existing assistant launcher stays in normal footer flow, preserving its own loader, events, authentication, dialog and focus ownership. No separate assistant or Saved store was created.

## Official source evidence and limitations

- BIS consumer prices and central-bank policy rates: public monthly observations, each with source, period, units and retrieval hash. The two acquired source archives are recorded in the preview manifest.
- IMF July 8 2026 WEO update: six country paths, with India explicitly on fiscal years. The first official workbook read succeeded; its bytes were not retained. The initial values are transcribed from that observed table output. A later automated fetch failed and is recorded as such.
- Taiwan DGBAS August 14 2026 forecast: the official indexed release excerpt supports 11.05% for 2026 and 6.04% for 2027. Direct HTML retrieval failed. The baseline records excerpt-transcription provenance; successful automated Taiwan refresh has not been claimed.
- BOJ July 31, BOK September 10, RBA August 11 and ECB September 10 publications support the attributed country narratives. Narrative dates and forecast-source dates are shown separately.
- Prior GDP/unemployment observations from the existing macro series remain dated and identified in the source ledger. Missing Taiwan macro observations and currency clocks are not manufactured.
- The new source model is implemented and locally tested; production data admission, independent source/release review and automated-refresh acceptance remain separate gates.

## Paper design — applied

The rejected R10 source file was recovered. Four new R11 boards were created without changing its old boards:

| Board | Native ID |
|---|---|
| Country Intelligence · Desktop Dark | DMX-0 |
| Country Intelligence · Desktop Light | DW7-0 |
| Country Intelligence · Mobile Dark | E4D-0 |
| Country Intelligence · Mobile Light | EC2-0 |

File: [International Markets Paper designs](https://app.paper.design/file/01M3P1TW5Y3XWQC37ADDS8K5AG/p-2-0).

The selected Paper connection initially had a catalog mismatch; no writes were dispatched while that mismatch existed. The runtime owner subsequently upgraded the selected connection. Catalog `1b9afff4c9bcf6f11f5ca2db301bf25ccdc442025344e2ec402459cedcd6a2db` then matched and was accepted for writes. All recorded R11 effects returned APPLIED_RESPONSE_OBSERVED. Native screenshots were inspected during construction and `finish_working_on_nodes` completed for the four named boards. `paper_r11_receipt.json` retains the operation ledger and explicit file/node scope.

Paper provides the composition reference. The implementation uses the existing shared site navigation and the repository’s active theme values. The integrated screenshots are the rendering acceptance evidence; no pixel-identical shared-shell claim is made.

## Verification

- 77 targeted Python cases pass: country source/model/presentation, equity risk, existing International builder, Library mount, workspace composition and session as-of behavior.
- 12 integrated Chrome states pass: 1440/390/320px × dark/light × EN/ZH, with seven countries, the expected open assessment, closed subordinate tools, no page errors and no horizontal page overflow.
- Six journey families pass: country selection/history/keyboard/source disclosure, legacy fragment navigation, legacy query navigation, readable core with all nine legacy assets returning 401, incumbent assistant lazy load/open/close/keyboard reopen from footer flow, and country/source reading with JavaScript disabled.
- The final visual product review accepted the desktop dark and mobile light states and confirmed that the assistant no longer covers the analysis. It is a bounded product judgment, not data, security, release or institutional-coverage certification.
- `git diff --check` passes. Hosted CI, a merged source commit and served production checks have not occurred.

Canonical integrated receipts are in `country_cockpit_preview/integrated_receipts.json`; the matching `integrated_*.png` images are the final implementation captures. Older standalone captures are earlier construction evidence.

## Publication and live status

The single typed publication precheck
`studio_git_publish_status({operation_id:"intl-country-cockpit-20261018"})`
returned `TYPED_GIT_PRECHECK_REFUSED`, `INVALID_ARGUMENT`, effect `NOT_APPLIED`. No commit, push or alternate source-publication carrier was attempted. The canonical workspace status recognizes this owned Macro workspace. Read-only diagnosis proves the installed C2 Personal publisher is the legacy single-repository implementation: its source repository and sole allowed origin are Mastermind. It invokes workspace status without a repository selector, so it cannot select this correctly registered Macro operation. Under the publisher’s exact sanitized environment, the canonical Macro status succeeds and Mastermind/Terminal return the expected typed non-registration receipts. Registry recreation is unnecessary. Installed publisher SHA-256: `9d50cd828e51d0c08a7be0ca7b18c89bfd8fb767a548bb1e4deaddaf185225ae`. See `country_publication_diagnosis.json`.

The live /intl.html and its nine previously denied workspace assets have not been redeployed by this operation. The existing accepted exact-path asset repair belongs to the preserved PR #8754 release chain. New country SSR resilience under simulated 401 responses is verified; it is not proof that those live assets or the legacy tools have been repaired.

Next authorized delivery sequence: obtain the installer owner’s accepted migration for the C2 Personal publisher, publish this owned branch through the accepted carrier, obtain independent source/publisher review and hosted CI, then complete the existing release and served-browser acceptance. Do not mark this work live from local tests or Paper completion alone.
