# C01 observation append/read — prepared v2 correction return

## State and exact artifacts

This is the complete scratch-only v2 replacement source and test pair for independent review. It resolves the three P2 findings against frozen v1. **No application import, test execution, native operation, store construction/invocation, Git operation, provider call or source acquisition occurred in this continuation.** The checks below are syntax and byte-identity checks only.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `relationship_observations.py` | 42,756 | `85c07b309ff7b7220ec12f2b3f25c924a2ef4c9ab495ce9030f61038cbb9e8c7` |
| `test_company_relationship_observations.py` | 49,406 | `a73700e639c8e97a4ff84951b48358abe63b1f5048560d03b0e40f2310ac44da` |

Intended native paths remain exactly `engine/company_intelligence/relationship_observations.py` and `tests/test_company_relationship_observations.py`. The source and test were frozen and sent to the principal and independent reviewer before this return was written. Further corrections require a separate version and new hashes.

Frozen v1 remains unchanged. Its module still hashes to `4239285b177d2947173404f96f1672394b6f246e70ea4a82885e25ca8990196b` and its test to `80acae7aadcecec3214fe86d77c99da841d2544629d35380ec11b5d9cc94d67e`. Its implementation description and prepared tests are historical artifacts containing the reviewed gaps; they are not accepted native proof.

## Correction 1 — unchanged drift includes a fresh refusal

**Finding:** v1 returned `ABSTAINED` whenever the fresh inspection was not `INSPECTABLE`, before checking whether the request was unchanged. A saved positive followed by a refusal under the same current request therefore failed to expose replay drift explicitly.

**v2 change:** `read_relationship_observation` computes the unchanged-request condition immediately after computing and bounding the actual fresh result. It compares the complete fresh and sealed canonical outcomes before any non-inspectable early return. An unchanged mismatch returns:

- outer status `REFUSED` and refusal `INSPECTION_REPLAY_MISMATCH`;
- replay status `UNCHANGED_REQUEST_MISMATCH`;
- the complete actual fresh inspector result, including its original refusal code;
- no saved review provenance or prior-link semantics.

A genuinely changed historical request still returns its actual fresh non-inspectable result as `ABSTAINED`, without manufacturing a different temporal refusal or exposing the sealed positive. The existing historical/support tests remain in the complete test file. The forged-candidate regression now requires explicit drift while preserving the real `SOURCE_LOCAL_LABEL_UNSUPPORTED` inspector refusal.

## Correction 2 — exercise the actual import boundary

**Finding:** v1's guard blocked `engine.collectors.*` but omitted the actual top-level `collectors` namespace. Its `tests.*` predicate also omitted the exact `tests` root. The prior positive-current test did not demonstrate that these forbidden imports would be stopped.

**v2 change:** the installed child-process fence blocks `collectors` and all children, `tests` and all children, `pytest`, and the named transport roots `requests`, `urllib3`, `httpx`, `aiohttp`, `boto3`, and `botocore`. It also blocks `urllib.request`, `http.client`, the named capture harness `capture_one_native_sec_filing`, and the test fixture module name. The existing specifically named engine capture/collector bans remain. This describes a precise fence; it does not claim an inventory of every possible acquisition module.

Before application imports, the test child calls real `import_module` for 18 prohibited names: the `collectors` root and its `sec_document_spine`, `fundamental_forensics_acquisition`, `fundamental_forensics_companyfacts`, and `edgar_forensics` children; the test root and named test child; pytest; the six transport roots; the two named standard-library network modules; and the named capture and test harnesses. A later finder raises if resolution gets past the guard for any of those control names. The controls must be rejected before a prohibited loader runs.

Intentional guard-control events are retained separately from unexpected import/effect events. They are not silently erased. The control context is reset before application imports; the unexpected-event list must stay empty. The two actual fresh-process outputs must include the same complete current/historical results, the same control receipts and no loader fallthrough.

`urllib.parse` remains allowed and is actually imported and used in the prepared child test. `lib.dataos.registry` remains allowed because it supplies the actual pure registry contract needed for the historical refusal. No invented broad registry namespace ban was added. Network/process denial and filesystem mutation denial remain independent of the import name list. The incumbent constructor's narrowly allowed attempt to mkdir the already-existing root remains separately recorded.

These are **prepared guard controls**. They have not been run by this lane; a syntax check cannot prove a working import fence.

## Correction 3 — absence after an ambiguous final write is still unknown

**Finding:** v1 discarded the modifying exception. A final put exception followed by a `None` readback became an ordinary refusal. An in-flight request could still complete after that earlier absence observation.

**v2 change:** `_create_only` preserves whether the put raised. Following a final modifying exception, only exact matching manifest bytes reconcile success. An absent, nonmatching or unreadable readback returns `MANIFEST_EFFECT_UNKNOWN` with outer `EFFECT_UNKNOWN`, the expected reference, and no positive inspection/review provenance. There is no blind retry, repair or overwrite. A successfully acknowledged conditional conflict with known absent readback remains a separate refusal path.

The new parameterized test uses fault instrumentation over the actual LocalStore API. In the absent case, real chunk writes succeed, the final response times out, and the actual store initially returns `None`. The result must be unknown. The fixture then explicitly completes the pending final creation; a later normal reader must verify the exact committed closure. In the nonmatching case, the fault fixture leaves different same-length bytes at the attempted manifest key; the immediate result remains unknown, and a later normal read refuses the bad digest without repair. The pre-existing matching lost-ack, unreadable final-effect and authoritative non-write controls remain.

This models the acknowledgment/observation distinction using a local fault fixture. It is not a remote R2 timing or bucket capability proof.

## Contract retained in v2

The public APIs and storage/result schema versions are unchanged. Append accepts an injected incumbent store, seven exact UTF-8 artifacts, review/case IDs and optional unresolved prior reference/registry. It computes `inspect_candidate` internally; no caller positive-result argument exists. Read accepts only an exact digest-plus-length manifest reference and explicit inspection options/purpose. No factory, loader, client, source acquisition, listing, latest pointer or publisher was added.

The C01 pilot-specific contract still requires planned product integration into the explicit H200 target, retains the component configuration, exact source/span/reviews and date precision, and does not broaden a planned inclusion to current supply or deliveries. Matching hashes and content bindings still do not authenticate authorship, independence, custody or semantic truth.

The final serialized package cap remains 1 MiB including escaping; at most 64 chunks of 16 KiB and a manifest of at most 16 KiB. References carry the required length before exact reads. Every object is verified, the manifest is published last, identical repeats do not rewrite objects, corruption is terminal, and all sizes are preflighted before writes.

All results retain `NOT_ADMITTED`, null Graph1 and false rank/gate/size/trade/prediction. Production/public-export/training remain false and purpose permission unestablished. Historical knowledge, canonical legal identities, authenticated source custody, commerce and predictive promotion remain unsupported by this slice.

## Verification observed and next execution

The complete module and test files passed `compile(raw, path, 'exec')` under `PYTHONDONTWRITEBYTECODE=1 python -B`, without importing or executing either. The new embedded child script also passed separate compilation: 5,510 characters, SHA-256 `a7daa01bd00787fa88d24399854dd3e02e993eb7e5cc24c9b9e6048cbe655a04`. The full v2 test file has 24 test functions, several parameterized. These are not 24 passing tests.

The module diff is limited to the write-exception marker/unknown decision and moving unchanged-result comparison before the early abstention. The test diff adds the two final-timeout fault scenarios, updates the refusal-drift expectation and expands/exercises the fresh-process fence. The frozen v1 source/test hashes were rechecked in the same compile-only inspection. No new native PID or runtime receipt exists for v2.

The earlier actual dependency read of Research Vault source was PID 30946, exit 0; it remains a historical read-only receipt and was not rerun. The dependency pins remain store SHA-256 `7ba42eb8f74c034413997707a35156e67342fb9a30ca2b80dde0f11d1dc7e2bd` and inspector SHA-256 `a558922c0586a5532f3912524b48f3cf592c3c6c9c21f689e3d416976e9cae55`. The independent storage adjudication remains SHA-256 `e4966d1e38fe0c5cc495982b74600ab77860fdf0d807db1129d70638bba67543`.

The principal owns independent acceptance, exact native application, focused tests and composition gates, all seven retained C01 bindings/final package sizing, the private store append/read/repeat and independent fresh-process real-source proof. In particular, the actual native test run must establish that the 18 intentional controls reject and that no unexpected effects occur. Native tests and real evidence execution remain **NOT_RUN_BY_THIS_LANE**.

**STOP.**
