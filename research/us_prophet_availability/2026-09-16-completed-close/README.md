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

## Cross-session coordination and Boolean-price correction

Current procedure pin: `Mastermind@8ba7deedde164c90298d3e88785d98e02fa5e2d2`. At the 09:11 UTC coordination read, our #7200 remained on `5f1bed28965db3cbf0ba88a72d409529b7ac85d4`; the peer deep-stock repair #7206 was on `6159410678619d148531ba3e2ecbb1ad7a537d04`. These repairs implement different producer boundaries. Their only shared changed path is `.github/ci/legacy-jobs.yml`. This session retains the S&P breadth carrier and nonmutating source-composition review; the peer retains its deep-stock carrier and already-named Russell continuation. No source-custody transfer or peer receipt is inferred.

The targeted review reproduced an additional malformed-input defect in both helpers: Boolean True can be converted to price 1. Our completed-close count accepted Python and NumPy booleans; the peer helper rejected Python bool but accepted the NumPy/Pandas bool scalar. This is a newly found validation defect, not a proven cause of the original outage.

Our same-carrier correction masks Python/NumPy booleans before numeric conversion. Five new assertions failed on the predecessor source; the full four-suite battery now passes **65 tests**. Ordinary integer/float price 1 remains valid. The actual fetch tests cover bool, object and nullable-boolean columns, consume the existing retry budget, and preserve every seeded cache byte on failure.

The earlier real-provider receipt remains immutable historical evidence of source `2ecf3db94d131cf8c59fe685ce7d1aca2e3509c2`; it has NOT been relabeled as a new live run. `boolean-validation-compatibility.json` is fresh, read-only validation of those exact preserved real-input files under the corrected helper: the same 500/503, 599/602 and 400/400 valid closes remain accepted, with no provider calls or production writes. This is recorded-input compatibility, not another live collection, full-board proof or deployment.

Peer correction handoff: on #7206, reject Python and NumPy boolean scalars before `float(value)` in `_has_completed_stock_close`; add dtype=bool/object/nullable-boolean regression and positive numeric-one controls. Preserve its separate 70% coverage rule and source retention. Do not copy our 80% panel floor into the deep-stock producer. This session does not edit the peer module or worktree.

Other collision boundaries remain: #7187 has an incumbent local maintainer and must not be overwritten; #7060 independently changes `collectors/breadth.py`; #7163 has an existing #7018-first integration ruling and a stale HK byte-pin finding. Coordinate shared CI/renderer/collector hunks with their owners. The B3/B4 File Library plans are a separate downstream product-state proposal, not proof those modules are shipped.

## Partial-coverage output correction

A subsequent actual-fetch probe exposed a remaining failure on `cdc6a5bdfe53a1028b9791a0cf15a750ec09abde`: four valid closes meet the intentional 80% universe floor, but the invalid fifth cell was still persisted. Boolean True round-tripped through parquet as 1.0; infinities, zero and a negative close also survived. Validating the count alone did not keep the invalid remainder out of breadth computation. This was reproduced in the real fetch/store path, not inferred from a helper.

The same source carrier now uses one shared exact-session value predicate for counting and masking. Invalid expected-session cells stay missing before accumulation/seam analysis and after seam repair before persistence. Only those invalid current cells change; prior history, constituent columns, actual positive price 1, partial-coverage floors, caller interfaces, regional calendars, Russell behavior and trading/source authority remain unchanged. No full-board builder or another session's module was edited.

Seven new regressions failed on the predecessor. The expanded four-suite battery passes **74 tests**. Two additional forbidden mutations independently expose a removed pre-seam mask and a removed pre-persistence mask. The real computed breadth counts four members, not five, for an accepted four-valid/one-invalid fixture. Valid history remains byte-value intact and input frames are not mutated.

`partial-price-publication-replay.json` records a bounded reconstruction from the preserved real-price matrices through the actual fetch, run_adapter, store, and alpha consumers. It is NOT a raw-provider-response replay or a new provider run. All three adapters reported current successful health with 500/503, 599/602 and 400/400 actual closes. Complete Close values matched the recorded matrices by ticker/date; current High/Low/Volume values also matched. Per-ticker alpha values, sector rankings and top member/value sets were exactly equal. The final strict ordered-output assertion failed because the reconstructed column order swapped SNDK and SPHR in the top list. That difference remains explicit in the receipt; no byte-identical/ordered-alpha or production claim is made, and rank code is not changed in this collector repair. The earlier fixture attempts incorrectly unioned unequal final-matrix indices and then assumed provider column order; these are recorded test-harness limitations, not hidden product passes.

Direct execution rationale: PRINCIPAL_JUDGMENT / CRITICAL_PATH_SHORTCUT — close the proven current-price publication leak on this session's existing branch before asking an independent reviewer to accept it. The peer retains #7206/Russell ownership; final shared production publication still requires one acknowledged owner.


## Same-session cache finality correction

Adversarial review found one more merge-boundary defect at exact preimage `e3c87afae3e42e79f615d3219092c8869305d4e6`: when a fresh completed-session response supplied four valid closes and omitted the fifth, the intentional 80% floor admitted the batch, then `fresh.combine_first(cached)` refilled the missing fifth close from a finite value already cached under the same date. The cache has no per-cell finality stamp, so an earlier intraday observation could impersonate the completed close.

The US fetch now quarantines the expected-session cache cells for the requested universe before historical merge. Fresh source bytes exclusively own that completed-session row; all prior history, non-current columns, regional calendars, Russell behavior, the 80% availability floor, retry budget and ranking rules remain unchanged. The new regression failed with cached `EEE=102.0` before the repair and passes afterward. The owning four-suite battery now reports **75 passed**. `same-session-cache-quarantine-receipt.json` records the RED/GREEN boundary; it used no provider request and performed no production write.


## Same-session High/Low/Volume finality correction

The completed-session quarantine must cover every field persisted from the accepted response, not only Close. At exact preimage `7355c03b6ba8919ed52f0147861777051cc64c29`, fresh valid closes could be accepted while one name's fresh High, Low, or Volume was missing; the later extras-cache `combine_first` then restored a finite same-date intraday cache value. RED fixtures reproduced all three cases (`999.0` High, `1.0` Low, `999999.0` Volume).

The existing quarantine helper is now applied to cached extras before merge for the three US completed-session groups. Valid fresh historical extras still override cached history; only requested names on the expected completed-session row are denied same-date cache substitution. Regional calendars, Russell, the close-coverage floor, retries, rank logic, and prior history are unchanged. Focused GREEN is **3 passed**; the four-suite owner battery is **78 passed**. Evidence: `same-session-extra-cache-quarantine-receipt.json`.


## Same-response OHLCV coherence correction

A valid partial batch can meet the 80% close floor while one requested name still lacks a completed close. At exact preimage `1a64c60bd64c41568cb51bb69fe5093630094fe2`, the same accepted response could nevertheless persist that name's current-session High, Low, and Volume, creating an independently current-looking OHLCV row without settlement. The RED fixture reproduced `EEE` with no completed close but current High `104.0` and companion extras.

Before a provider attempt becomes accepted, the three US groups now mask expected-session High/Low/Volume for exactly the names whose Close is missing or invalid. Valid partial coverage, other names, all prior rows, regional calendars, Russell, retries, and ranking remain unchanged. Focused GREEN is **1 passed**; the four-suite owner battery is **79 passed**. Evidence: `same-response-ohlcv-coherence-receipt.json`.


## Whole-field extra omission correction

Independent verification comment `5696266993` found the omission branch the cell-level repair did not cover: when an otherwise healthy accepted response omits the entire High, Low, or Volume field, that key is absent from `_last_extras`, so the old current-session cache file was never visited and retained all requested values. Three REDs reproduced High `999.0`, Low `1.0`, and Volume `999999.0` surviving unchanged.

For the US completed-session groups, persistence now considers every existing High/Low/Volume cache even when the fresh response omitted that field. The requested universe is quarantined on the expected-session row; prior history remains. The already-passing missing-cell controls remain GREEN. Focused result: **6 passed**; owner battery: **82 passed**. Evidence: `whole-field-extra-omission-receipt.json`.
