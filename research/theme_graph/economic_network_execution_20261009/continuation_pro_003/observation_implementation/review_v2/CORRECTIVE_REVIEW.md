# Independent C01 observation corrective review — frozen v2

## Verdict

**PASS for the bounded prepared-source review.** All three accepted v1 P2 findings are corrected in the exact v2 bytes below. No remaining definite P1/P2 finding was identified in the complete delta or its affected context. The unchanged portions reuse the full v1 source/test review; this receipt does not claim a second unrelated full review or certify the reviewer's own earlier pure-reader repair.

**Native application, pytest, store operations, private retained-source witnesses, CI and release are NOT RUN by this reviewer.** This verdict permits the principal to proceed with the already authorized native application and validation of these bytes. It is not a runtime PASS, producer authentication, source admission, product acceptance or predictive promotion.

## Exact artifact binding and review reuse

| Artifact | Bytes | Lines | SHA-256 |
| --- | ---: | ---: | --- |
| `lanes/relationship_observations_v2/relationship_observations.py` | 42,756 | 818 | `85c07b309ff7b7220ec12f2b3f25c924a2ef4c9ab495ce9030f61038cbb9e8c7` |
| `lanes/relationship_observations_v2/test_company_relationship_observations.py` | 49,406 | 918 | `a73700e639c8e97a4ff84951b48358abe63b1f5048560d03b0e40f2310ac44da` |
| Preserved full v1 review, `lanes/relationship_observations_review_v1/REVIEW.md` | 18,677 | — | `6d2e452fadff42bbf3b25928bbed8795fb5bc3a6e32c1f58f494f1df360ed51c` |
| Preserved v1 findings, `lanes/relationship_observations_review_v1/FINDINGS.json` | 5,201 | — | `64e05e70521f4654fcfc6e25562868cb3c777f3518531e1dff2546b8e3acbe8a` |

The v1 source SHA remains `4239285b177d2947173404f96f1672394b6f246e70ea4a82885e25ca8990196b`; v1 tests remain `80acae7aadcecec3214fe86d77c99da841d2544629d35380ec11b5d9cc94d67e`. Their verdict stays CHANGES REQUIRED as historical evidence.

The governing applied decision remains SHA `f362b947460477b808d9aa50f7b6557cc9b738af9280da0ef014da6901fcd091`, and the original storage adjudication remains SHA `e4966d1e38fe0c5cc495982b74600ab77860fdf0d807db1129d70638bba67543`. The decision's mandatory seven inputs, both retained-byte judgments, internally computed inspection, 1 MiB complete serialized package, 16 KiB storage objects, manifest-last publication and unadmitted current-only semantics remain unchanged.

The entire unified source/test diff was read. A standard-library-only AST comparison independently confirmed that the module changes exactly `_create_only` and `read_relationship_observation`, adds no functions or classes, and removes none. Test changes add one parametrized function and modify exactly the forged-saved-positive test and the fresh-process test. The embedded child string and both modules parse as AST. AST parsing and literal extraction do not execute the application or its tests.

## OBS-V1-001 resolved: complete comparison precedes refusal return

In v2 `read_relationship_observation` lines 764–818, the unchanged-request predicate and full canonical fresh-versus-sealed comparison now run immediately after the actual fresh inspection and its bound check. They precede the non-`INSPECTABLE` return. Therefore an unchanged request cannot bypass replay comparison by becoming refused.

Mismatch returns `REFUSED`, `INSPECTION_REPLAY_MISMATCH` and `UNCHANGED_REQUEST_MISMATCH`, carries the complete actual fresh result, and includes no retained-review provenance. It claims only verified component bytes, not verified semantic provenance. A changed historical request still reaches the actual abstention branch and withholds saved positive/review semantics.

The revised `test_forged_saved_positive_cannot_override_actual_refusal_or_replay_mismatch` at lines 598–625 now requires the concrete unsupported-subject case to return mismatch, asserts the full result equals an actual incumbent `inspect_candidate` call, and checks `SOURCE_LOCAL_LABEL_UNSUPPORTED`. The existing natural historical-refusal test remains unchanged. This corrects the original counterexample without substituting a mocked positive/refusal or weakening temporal behavior.

Moving the comparison earlier means a forged package whose current inspector differs can be refused before complete semantic-review binding reconstruction. That is appropriate for the returned scope: the result exposes the actual inspector outcome, verifies bytes, withholds saved review provenance, and makes no complete-closure semantic claim. Positive verified results still perform the derived-envelope checks before exposing review provenance.

## OBS-V1-003 resolved: the modifying exception remains visible until exact reconciliation

V2 `_create_only`, lines 655–682, preserves a `write_raised` marker. An exact expected-byte readback still reconciles a successful commit after a lost response. A final modifying exception followed by any nonmatching readback now raises `MANIFEST_EFFECT_UNKNOWN` with `effect_unknown=True`. This includes `None` and different bytes; an unreadable readback already takes the same uncertainty path.

The correction changes no create-only key, payload, predecessor token or retry law. A preexisting different object is still refused before any write. A race followed by exact matching bytes may still succeed. Corrupt data are never overwritten or repaired. No new clock, path or invocation-dependent field enters content identity.

The new parametrized `test_final_put_timeout_with_no_matching_readback_remains_effect_unknown` uses the real LocalStore behind a traced final-response fault. The absent case performs an actual exact read that returns `None`, requires the initial effect-unknown outcome with expected reference only, then explicitly completes the pending create and requires later verification. The different-byte case writes a same-length corrupt manifest, raises a simulated timeout, requires effect-unknown, and verifies that later read refuses its digest without altering stored inventory. Safe fixed codes, no source/path leakage, no inspection/review provenance and all authority boundaries are asserted.

These are meaningful source-level regression designs; they have not been executed by this lane. They complement the retained matching-byte lost-ack and read-error tests rather than replacing them.

## OBS-V1-002 resolved: actual import resolution exercises the real collector fence

The expanded fresh-process test, lines 748–918, blocks top-level `collectors` and descendants; exact `tests` and descendants; `pytest`; the existing transport roots; and the specifically named `urllib.request`, `http.client`, capture script and capture aliases. The allowed pure `lib.dataos.registry` remains available. The test explicitly imports `urllib.parse` after installing the fence and checks a pure parse result.

There are 18 intentional import-resolution controls, covering the collector root and four real collector modules, test root/module and pytest, six transport roots, both standard-library transport modules, the named capture script and the parent test module. Each requested name is asserted absent from `sys.modules`, passed to real `import_module`, and required to fail with the guard's import-denial exception. A later meta-path finder traps fallthrough before a prohibited loader could be reached. A child import may be rejected at its prohibited root; that is correctly sufficient to prevent the child loader from executing.

Intentional denials are recorded separately from unexpected application events. The unexpected-event list is never cleared. The successful consumer output must contain all 18 requested controls, no fallthrough, and zero unexpected denied events. The scope of this proof is exactly the named import fence plus its independent audit guards; it does not claim an exhaustive inventory of every possible acquisition or registry namespace.

The important earlier safeguards remain: Python `-B` and disabled bytecode writes; existing absolute non-symlinked LocalStore root; audit denial installed before application imports; network/process/write/mutation denial; only the incumbent constructor's already-existing-root mkdir temporarily permitted and recorded; two independently launched child processes; complete equality of both outputs and the parent expectation; unchanged store inventory; actual historical `AS_OF_DATASET_REQUIRED` with no saved positive labels or review semantics.

## Static checks actually performed

The reviewer used only scratch file reads, hashing, unified diff generation, AST parsing and AST literal extraction. The exact files were rehashed before verdict. AST comparison found:

| Area | Result |
| --- | --- |
| Module function changes | `_create_only`; `read_relationship_observation` |
| Module functions/classes added or removed | None |
| Test function added | `test_final_put_timeout_with_no_matching_readback_remains_effect_unknown` |
| Existing test functions changed | `test_forged_saved_positive_cannot_override_actual_refusal_or_replay_mismatch`; `test_second_process_reads_repeat_exactly_under_import_network_and_mutation_guards` |
| V1/v2 top-level test function counts | 23 / 24 |
| AST parsing, both module/test versions and v2 embedded child | PASS |
| Application import, pytest, native store, network capture, Git | NOT RUN |

These checks are source-review evidence. They do not prove the native adapter or installed import closure ran successfully.

## Bounded next execution gate

Root should apply exactly these frozen bytes to the already acquired canonical workspace and run the new suite together with the incumbent manual, pinned and review-set suites under native Python 3.12. The existing CI owner should enroll the two new paths and the new test file while preserving concurrent shared-manifest changes. No new job, store implementation or `PRODUCED` registry row is needed.

The narrow targeted regressions are the three functions named above. The full new observation suite then covers the existing corruption, repeat, concurrent create, escaped-size, fresh-history and actual-LocalStore paths. Root's real retained C01 witness must additionally demonstrate that the actual source plus seven required inputs fit the complete serialized bound and reproduce positive/repeat/fresh-process/historical outcomes under the intended private store. Those observations must bind the exact applied source and distinguish deliberate guard controls from unexpected events.

After native validation, all publisher-purpose, identity, historical availability, reviewer authentication, product-adoption and predictive gates remain unchanged. This receipt authorizes no public export, training use, graph projection or financial action. It records an independently reviewed private evidence-retention implementation ready for its native proof.
