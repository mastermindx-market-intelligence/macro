# US Prophet: completed price rows, not successful HTTP responses

## Proven incident

Daily run `35041133038`, collect job `104621037120`, wrote collection commit `6a930b613598` with September 15 date rows but **zero valid closing prices** in all three tracked US breadth panels. High was also missing; Volume was populated. The collector logged success while computed breadth still ended September 14. Engine job `104658157677` then built September 14 alpha and a 50-name mixed-vintage candidate board. The public shell continued serving the September 11 board. The original vendor-side reason for the empty adjusted-price fields is not established; the missing successful-response validation is established.

## Bounded repair

The three S&P US collectors capture one reference from the existing NYSE calendar. They require finite positive closes on that exact completed session, using the existing 80% breadth coverage floor. Empty/stale/volume-only responses consume the existing configured batch retry/backoff budget before any response is accepted. The best same-call partial response may be kept if a batch exhausts, but the entire requested universe must pass the same floor. Response extras stay with their selected Close response. A missing Close field cannot be relabeled as a close matrix. The final panel is checked again after seam repair and before any cache writes.

Failure preserves previous cache bytes and propagates through the existing `run_adapter` failure/health consumer. The existing circuit breaker and half-open probe remain unchanged. There is no new scheduler, provider, retry budget, market calendar, freshness registry, ranking rule or trade authority. Regional calendars and Russell’s existing two-argument/partial-cache behavior remain unchanged. No adjusted/unadjusted substitution or fabricated values are permitted.

## Exact evidence

`live-source-receipt.json` binds semantic source head `2ecf3db94d131cf8c59fe685ce7d1aca2e3509c2`, source-code SHA-256, exact seed commit/files, actual output hashes, requested populations and the real alpha result. The unchanged final collector source recovered 500/503 large-cap, 599/602 small-cap and 400/400 mid-cap completed closes. All three breadth outputs and real `build_alpha_data` reached September 15; alpha contained 1,460 names and 11 sectors. These are the isolated S&P panel consumers, NOT a rebuilt full Prophet board. Curated extra/Russell stores, plan origination, publication and user acceptance were not exercised by this probe.

The experiment runs the real adapters and real alpha builder against the real provider with only `config.data_dir` and `config.site_dir` redirected to an isolated `.pytest_cache/live-final-source/` tree. It seeds the committed close/high/low/volume/constituent parquets and SPY bytes; configuration, symbol corrections and the exit ledger are the source-controlled versions. It does not write any production store or runner checkout. Raw prices are not copied into this evidence packet.

`python -m pytest -q tests/test_us_breadth_completed_close.py tests/test_breadth_split_seam.py tests/test_russell_breadth.py tests/test_universe_split_seam.py` passed **56 tests** after the final health-consumer test was added. Three targeted forbidden mutations (missing calendar binding, removed response validation, removed post-seam validation) were detected. The original null-row and missing-Close-field failures were observed before their repairs. The new hermetic suite is explicitly registered under **gate: code** in the existing CI manifest, not merely a nightly data gate.

## Release boundary

Capability remains **BUILT_NOT_PROVEN** until exact-head CI/security and independent review, integration with #7180/#7187/#7163, and a real completed-session source → alpha → candidate/plan → published browser path. Source freshness is not candidate/plan freshness; a fixture, provider probe, successful job or merged PR cannot replace served-output proof. The natural nightly must be reconciled before any additional recovery dispatch.
