# Independent final International data, logic and integration review

Reviewer: /root/intl_gs_composition_advice. Returned 22 October 2026, 20:01 UTC.

**Subject:** immutable source `9bf7161b6c856a8df5eaa18a0b9ef8fbb1e206bb`.

**Verdict: ACCEPT** within the International data/logic and inspected GS, build, access and CI-enrollment source scope. No additional actionable source blocker was found. This is a new broad independent source disposition, rather than reuse of the earlier narrow artifact review.

The reviewer used exact-pin GitHub reads and inspected the producer, loader, selector, consumer, builder and CI paths. It performed no tests, processes, Studio operations, source edits, acquisitions, workflow dispatches, publications or deployments. The incumbent writer captures the return here; this record transfers no custody.

## Source identity

The reviewer compared all 24 paths from the original data review at `14ed4f12f31b71c63bbabd969aebbf9c4305ccaa` with the subject. Nineteen Git blobs are identical, including the currency, forecast and BIS producer/store/loader/consumer chains and the four named suites. The five changed dependents received a fresh review:

| Path | Original blob | Subject blob |
|---|---|---|
| scripts/build_intl.py | 272d70b03caa913c21e0eedc187bdeed9eb4b8e8 | a8319302b6598b9ff2cd151324d8f36a9bb28e1b |
| .github/ci/legacy-jobs.yml | 45fd66c8c06c2b1c14fa68b355947e0738962797 | d6fe8eb05d10e9ed4d460a1d0fb1c70ae707338a |
| app/deploy/Caddyfile | 7e13fc89817725188ba37d2550acca21056e0130 | fc0217af93e2243baff870c42471c97744f64687 |
| config/site_access.yml | 995545210c4aac2612fa6554b44aa78fc32e57b2 | 9629776fa2da6792b332e9d33ba55bb925b237e8 |
| tests/test_site_access_boundary.py | db31917adcfafe95b5c4d5fa6dcc650c4bb2aaef | 079edb201b91be9238e51474569aef80ad24e39e |

Three production files also equal frozen source `442042e591d255dd24b540ff240edb4c0410c297`: lib/intl_country_inputs.py, lib/intl_country_assessment.py and engine/intl_equity_risk.py. The fourth source-trace file, the builder, received the fresh GS composition review. Historical execution evidence remains historical.

## Findings

**Currency source custody and arithmetic — ACCEPT.** The real yf.download call records request and return clocks. Each invocation clears prior request state and attaches quote-bound receipts. Quote and receipt come from the same canonical frame. Qualification checks ticker, date, exact hexadecimal quote, request settings, digest and original request-start exclusion date. Intraday rows cannot become eligible merely through a later render, and changed quotes cannot borrow old receipts. Three-calendar-month selection uses month-end clamping and an actual observation on or before the target, at most seven days earlier. It excludes same-day, future and conflicting selected endpoints. The consumer independently checks identity, arithmetic, dates, provenance and digest. Local-per-USD pairs use reciprocal return; USD-per-local pairs use direct return.

**Forecast lifecycle — ACCEPT.** The normal loader explicitly reconstructs retained custody and withholds missing custody. Duplicate records select one complete acquisition record and withdrawal event. Correction ancestry links admitted predecessors in admission order. Live admission stamps newly learned content and discards incoming supersession claims. Selection respects publication age, fiscal period, knowledge clocks, withdrawal and supersession.

**BIS comparability — ACCEPT.** The real ZIP/CSV parser preserves compilation definitions, source identity, acquisition clocks, source digest and matching daily reference rows. Qualification derives the applicable instrument era and qualifier. Policy comparison honors effective timing and matching instrument semantics; it invents no final business day. Reconstruction preserves stronger daily proof and retains same-period contradictions as conflicts.

**Optional stocks and primary status — ACCEPT.** Failure of intl_stocks.panel yields empty optional stock frames while country assessment continues. Primary engine, canonical country-dashboard and main page-render failures return nonzero. The unchanged suite includes actual corrupt-Parquet and primary-failure controls.

**GS integration — ACCEPT within foundation scope.** It reuses the admitted frame, source snapshot, incumbent return records, qualification outputs, evidence and same EOD rights object as the page. It introduces no replacement numerical qualifier. Missing publication evidence withholds observations; missing clocks abstain; hedged basis stays unsupported. Observation and mount failures are isolated from the primary country page.

These nine files exactly match incorporated main `2d33475adef502ab6b00b8003356c1b0ad1673c0`:

- lib/intl_gs_display.py
- lib/intl_gs_observations.py
- lib/intl_surveillance_mount.py
- engine/intl_global_observation.py
- engine/intl_global_universe.py
- lib/intl_global_observation_adapter.py
- lib/intl_eod_publication.py
- templates/intl_workspace/shell.html.j2
- templates/intl_workspace/_gs_macros.html.j2

The contract orders observation, source-publication, ingestion and computation clocks. The collector check is accurately labeled a source-publication upper bound, not a directly observed vendor instant. USD returns require the multiplicative identity. Seven new view builders are absent, and tabs remain disabled without available payloads. This establishes foundation integration, not completed GS views or qualified coverage for every jurisdiction.

**Access — ACCEPT as source configuration.** The exact surveillance CSS asset is enrolled in policy, all four relevant Caddy matchers and the explicit test set. API-owned authorization and neighboring protected-file assertions remain. Inherited moved-page redirects retain their trusted-shell conditions.

**CI enrollment — ACCEPT as declared integration.** The foundation job directly runs tests/test_intl_build.py and preserves numerical/custody commands, yfinance>=0.2.50 and openpyxl>=3.1 dependencies. The browser job explicitly runs GS foundation/browser suites and preserves the canonical-base failure check. Hosted completion is a separate fact.

## Applicability to the pending correction

This acceptance does not make the subject release-ready while the known pending-Scenario issue remains. The final query repair requires its separate independent review and an exact unchanged data/integration binding. DATA_LOGIC_APPLICABILITY.json records that binding when produced. Any material later CI composition needs separate assessment. Two comment wording corrections in the paired workspace scripts do not alter executable behavior.

## Production conditions

**RELEASE-INTL-FX-CUSTODY remains open.** After accepted source reaches protected main, the ordinary full-history intl_prices acquisition must actually execute. A warm shallow refresh or copied stores cannot qualify unreceipted three-month anchors.

The collector's generic 70% core-coverage threshold is not the all-seven release criterion. Existing production_fx_acceptance.py requires 7/7 current endpoints, matching same-frame receipts within the actual run-clock interval, a receipt-free negative control and unchanged canonical stores during inspection. The supplied interval is a correlation bound: actual workflow identity, full-history execution, renderer consumption and served adoption require separate evidence. GS qualification does not close this condition.

**RELEASE-INTL-SERVED remains open.** Required evidence is final-head hosted CI, accepted query repair and applicability, protected-main adoption, a covering ordinary International render, normal updater adoption, source-bound served HTML/assets and actual desktop/mobile, EN/ZH, light/dark, navigation/history, Library focus, assistant, public-resource and protected-refusal journeys. Local matrices, HTTP 200, manual BIS acquisition or shared render PR9894 do not substitute. The historical manual BIS acquisition also does not prove the ordinary collector's latency budget.

Source acceptance is recorded; production acceptance is not claimed.
