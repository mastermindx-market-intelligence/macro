## Independent source verdict

**ACCEPT for the four named data/source findings at immutable Macro head `14ed4f12f31b71c63bbabd969aebbf9c4305ccaa`.**

This is a **new independent adjudication by `/root/intl_release_gate_review`**, based on exact-pin GitHub source reads and inspection of the relevant regression bodies. It is not a reconstruction of the old reviewer’s missing return. I executed no repository tests, acquisitions, writes or publication actions.

**The additional CI-integration check has one precise outstanding evidence question:** whether another active workflow runs `tests/test_intl_build.py`. The inspected legacy manifest does not enroll it. This limits the integration verdict; it does not reopen a product-source defect already repaired below.

## Findings disposition

| Original finding | Disposition | Current source evidence |
|---|---|---|
| **FX-CUSTODY — P1** | **Closed in source** | The actual Yahoo invocation records request/return clocks. `_collect()` clears prior invocation state and attaches row-bound receipts to FX observations. Receipts bind ticker, provider date, exact hexadecimal quote, request settings and fixed request-start exclusion date. `country_currency_inputs()` reads quote and receipt from the same frame. Selection and serialized-view validation require matching receipts and exclude the acquisition day even during later renders. Receipt-free legacy rows cannot qualify; a changed quote cannot reuse an old receipt. |
| **FORECAST-CUSTODY — P2** | **Closed in source** | The normal page loader calls `merge_country_inputs(..., preserve_custody=True)`. Reconstruction requires retained clocks, chooses one complete acquisition record, preserves one complete withdrawal event and reconciles supersession against accepted correction ancestry. Missing custody is withheld. The live-admission branch stamps new operational knowledge and discards incoming supersession claims; it does not reuse the reconstruction privilege. |
| **BIS-COMPARABILITY — P2** | **Closed in source** | The actual BIS ZIP/CSV parser retains compilation definitions, source hashes, acquisition identity and matching daily observations. Qualification derives the applicable instrument era, qualifier, period convention and conservative comparison date. The normal merge preserves whole qualified evidence, retains stronger daily proof and represents same-period contradictions explicitly. The policy consumer compares matching instruments/qualifiers and effective timing; it does not invent a final business day. |
| **OPTIONAL-STOCK-FAILURE — P2** | **Closed in source** | `intl_stocks.panel()` is caught at the optional-input boundary and replaced by empty stock frames while country assessment proceeds. Primary engine, country-dashboard and main page-render failures return nonzero. Successful primary rendering returns zero. Regression bodies exercise actual corrupt Parquet bytes and controlled primary engine/render failures. |

The real call chains inspected include adapter → validation/store → country engine → assessment; collector → retained country loader → forecast selector; BIS parser → qualifier/reconciliation → national-policy consumer; and builder → optional stock handling → primary publisher/exit status. [FX producer](https://github.com/mastermindx-market-intelligence/macro/blob/14ed4f12f31b71c63bbabd969aebbf9c4305ccaa/collectors/intl_prices.py) · [FX validation](https://github.com/mastermindx-market-intelligence/macro/blob/14ed4f12f31b71c63bbabd969aebbf9c4305ccaa/lib/intl_currency_observation.py) · [Forecast lifecycle](https://github.com/mastermindx-market-intelligence/macro/blob/14ed4f12f31b71c63bbabd969aebbf9c4305ccaa/lib/intl_forecast_vintages.py) · [BIS producer](https://github.com/mastermindx-market-intelligence/macro/blob/14ed4f12f31b71c63bbabd969aebbf9c4305ccaa/collectors/intl_country_sources.py) · [Policy consumer](https://github.com/mastermindx-market-intelligence/macro/blob/14ed4f12f31b71c63bbabd969aebbf9c4305ccaa/lib/intl_policy_evidence.py) · [Builder](https://github.com/mastermindx-market-intelligence/macro/blob/14ed4f12f31b71c63bbabd969aebbf9c4305ccaa/scripts/build_intl.py)

## Integration judgment

**Declared custody CI: accepted within inspected scope.** The foundation job selects the relevant collectors, helpers and engine/store dependencies. Its explicit country-evidence command includes the currency, forecast and policy regression suites, and its dependency command includes `yfinance>=0.2.50` and `openpyxl>=3.1`.

**Build-failure regression enrollment: NEED_EVIDENCE.** Across the inspected 39,401-line legacy manifest, `tests/test_intl_build.py` has no literal enrollment or matching International/whole-test-suite command. The apparent bare `pytest -q` entries are folded commands listing unrelated suites. The concrete tests requiring a run owner are:

- `test_primary_country_build_survives_corrupt_optional_stock_cache`
- `test_primary_render_failure_is_not_reported_as_success`
- `test_primary_engine_failure_is_not_reported_as_success`

Root should check other actual workflow enrollment once. If none exists, enroll the existing suite, its real dependencies and trigger paths in the appropriate International job. Historical local success is separate from current hosted regression coverage. [Manifest](https://github.com/mastermindx-market-intelligence/macro/blob/14ed4f12f31b71c63bbabd969aebbf9c4305ccaa/.github/ci/legacy-jobs.yml) · [Build regressions](https://github.com/mastermindx-market-intelligence/macro/blob/14ed4f12f31b71c63bbabd969aebbf9c4305ccaa/tests/test_intl_build.py)

**Access integration: accepted as source configuration.** The nine International presentation assets are explicitly listed in the policy and all four relevant Caddy matchers. The inspected boundary test requires exact filenames, preserves API-owned authorization, rejects neighboring data/source-map/private paths and checks source/site asset equality. I did not run that test or exercise a live authenticated boundary. [Access test](https://github.com/mastermindx-market-intelligence/macro/blob/14ed4f12f31b71c63bbabd969aebbf9c4305ccaa/tests/test_site_access_boundary.py)

## Exact source identities

SHA-256 values below were computed from the exact-pin GitHub-decoded UTF-8 contents. Hashing the whole file does not imply that unrelated portions received exhaustive review.

| Read path | SHA-256 |
|---|---|
| `collectors/intl_prices.py` | `51269d0c848fba48bc4bc502ec694add836a30ff20efdff076801e0f2182f9ce` |
| `lib/intl_currency_observation.py` | `0d8f17822dd84e96e65a1c314d63c19c1b5fb0a7fb5c6cbcd155e2c96555e2b4` |
| `engine/intl_inputs.py` | `705a4fe7c0b0d4e816dfe28f060b446dd0adb5dc0ac84de677cb0b608959ab5b` |
| `engine/intl_run.py` | `611d106bfbd4159bad79b4f573af89c15e6a3281e55d37dba8512c415ea1f89f` |
| `collectors/base.py` | `2e17b5a2bd0b15d8c99d2bf73113e41429628230337b64e16d03e3a052b49965` |
| `lib/store.py` | `7424b19d2a418d6611c6346b20764a89d6ffe34ad9e6f3a115ec78e6a45b826b` |
| `collectors/intl_country_sources.py` | `9e51a27575659140fed98b7d5cc88d11e1812e8994b7b24c0dab13f1ae82b5c7` |
| `lib/intl_country_inputs.py` | `a7d9205597b960e72da41c640fc725ddb59716c60b40226f8e3fb79598065108` |
| `lib/intl_forecast_vintages.py` | `78a32fd42b52f1353ca275c5f53536031685ebda42a40e119ce07e8bd4e24d91` |
| `collectors/intl_weo.py` | `18ee3594029a1d17a827de7d491a1bd29b683f840e86def00f239a1745799775` |
| `lib/intl_country_outlook.py` | `bb5de24540aeeb8d9229499ad50ab125b5a6b385bc9cd79d1ef6dfe2ada4b914` |
| `collectors/intl_policy_sources.py` | `08e48a54bdfedf006aaad7ded702582368d32cd297bf5e51d3dac11e206c9c84` |
| `collectors/intl_macro.py` | `e2765426a3fd4c235dc546782b0984942e8223b02a6486d1cdf29f377d95abad` |
| `lib/intl_policy_evidence.py` | `94d1ea5ae4aa10d2b38a9b446dcf1173cfc7ea5b5afd026a72fbfd5fdb3f1e32` |
| `lib/intl_country_assessment.py` | `34be50dc9ddda218deeb265aa7090c209a04ddbb00c9b548668ab8041a897919` |
| `scripts/build_intl.py` | `41e2d7c791c4022f9165c267d31fc5cc4b22b188fbfba2c48a9a1980742a61f0` |
| `tests/test_intl_build.py` | `52d2d882f862307f76920ff04504ca4c0d34c29fe304dc7e99c7dacac0b563d6` |
| `tests/test_intl_currency_observation.py` | `18ca169153f7768a764d834e24de752cb2fa4bd1367f67527f27aa77aa954297` |
| `tests/test_intl_forecast_vintages.py` | `6a8a222c54992d542ed8a7b891d87b1b2b1c0b70685ee2a19251dc33cdcec74c` |
| `tests/test_intl_policy_evidence.py` | `d985dfcbd5149cb2a259a3c9f7926ba3d4635df4f45de6afeaeced0ca0bda5c8` |
| `.github/ci/legacy-jobs.yml` | `b9c7feb06f5f76ea9fbab5707a770e8b46adaaa6797ef28051a060ad2f7e40fa` |
| `app/deploy/Caddyfile` | `dbf8ea2ce1ba906884da95021fed4debcb92247019a5feede4df4a8129ce45ad` |
| `config/site_access.yml` | `e4385c7a281d23530936ec7b77c1db7db46a60d305b5ddd112ab82bbb0116be2` |
| `tests/test_site_access_boundary.py` | `dab5253ef57fa8797d08fc310db8acf0f95200d940d625795d64bf943a70f22b` |

## Limits and continuation

This verdict establishes source-contract closure of the four named findings. It does **not** establish production full-history FX acquisition or canonical-store custody, ordinary collector latency, current-head hosted CI success, served adoption, authenticated/public production journeys, or complete shared-shell acceptance. The known focus-restoration and transport-query defects remain outside this review and are not waived.

The earlier four-file source-trace PASS and frozen reference approval retain their separate identities. A later candidate requires an explicit applicability binding to these reviewed bytes and relevant integration changes.

**STOP — read-only review complete.**
