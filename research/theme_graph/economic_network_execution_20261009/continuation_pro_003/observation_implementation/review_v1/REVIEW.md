# Independent C01 observation implementation review — frozen v1

## Verdict and boundary

**CHANGES REQUIRED: three P2 findings, all accepted for correction by the principal.** The complete new module and its complete test file were reviewed. No additional definite P1/P2 issue was found in that full read. The proposed operation provides useful immutable evidence retention beyond the existing inspector: it preserves the seven original inputs, seals the internally computed inspection, publishes a verified chunk closure through a small commit manifest, and returns a reference that a separate reader can resolve and inspect again.

This is a source-level implementation review, not execution evidence. Application imports, pytest, native store operations, network capture, provider calls, and Git operations were **NOT RUN by this reviewer**. Builder compilation is not a test result. Root owns native application, real retained-source witnesses, CI, integration, and release. The earlier six-path pure-reader repair was authored by this reviewer and is expressly excluded from this independent review.

The v1 artifacts remain immutable historical evidence. Corrections belong in separately frozen v2 files and a separate corrective receipt; this report does not silently upgrade its v1 verdict.

## Exact reviewed inputs

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `lanes/relationship_observations_v1/relationship_observations.py` | 42,432 | `4239285b177d2947173404f96f1672394b6f246e70ea4a82885e25ca8990196b` |
| `lanes/relationship_observations_v1/test_company_relationship_observations.py` | 43,659 | `80acae7aadcecec3214fe86d77c99da841d2544629d35380ec11b5d9cc94d67e` |
| Applied decision, `lanes/pro003_control/DEC-GMI-ECONOMIC-RELATIONSHIP-OBSERVATION-MATERIALIZATION.md` | 12,462 | `f362b947460477b808d9aa50f7b6557cc9b738af9280da0ef014da6901fcd091` |
| Frozen storage adjudication, `lanes/NATIVE_OBSERVATION_STORAGE_ADJUDICATION.md` | 45,586 | `e4966d1e38fe0c5cc495982b74600ab77860fdf0d807db1129d70638bba67543` |
| Required first retained-byte judgment | 6,032 | `3a9ce686a0593f9731c89ef63c20afb92dce810681aa3d0039bd72ce0f4d6408` |
| Required principal retained-byte judgment | 3,732 | `96c5a97fd64a3c4330bba160310e5ade8babb211fd61d567fc5b119346837d9a` |

Both v1 files are 813 lines and were read end to end. The applied decision and both actual judgment JSON files were read in full. The original retained private source was not recaptured or read by this implementation-review lane. Its prior readers' source and context claims remain distinctly attributed.

Root reports that the decision was applied on pro-003 at `a48d5c0c078bc531cfc0f6b37643f44f77c2e937`, and that parent PR #8705 merged at `c63a92576a43247bb8c43dc275f827b8871fda3b`. These are integration facts reported by root; they are not additional native observations by this lane. The applied decision supersedes the earlier adjudication's optional single-addendum sketch: both retained-byte judgments are mandatory, alongside the original candidate, source, source record, pilot JSONL, and independent web-review JSON.

## Findings

### OBS-V1-001 — P2: an unchanged request can bypass complete replay comparison

**Source:** `read_relationship_observation`, v1 lines 780–801. **Test:** forged-package case, v1 lines 565–577.

After loading the committed bytes, the reader calls the real inspector. If that fresh result is not `INSPECTABLE`, lines 783–786 immediately return `ABSTAINED` / `FRESH_REQUEST_ABSTAINED`. The unchanged-request check and complete fresh-versus-sealed comparison occur only afterward at lines 796–801. An unchanged request whose previously sealed positive now becomes a refusal therefore never receives `INSPECTION_REPLAY_MISMATCH`.

A concrete source-derived witness is already present in the test: alter the stored candidate to an unsupported subject label, preserve the old positive inspection, and recompute the package and manifest digests. The fresh inspector refuses the candidate. The v1 test explicitly expects `ABSTAINED`, thereby accepting the bypass. An inspector implementation change producing the same transition would follow the same branch; no forged authentication is needed to explain the defect.

The fresh result is still returned, and saved review provenance is withheld. Consequently this does not promote the old positive or grant decision authority. Its defect is the lost distinction between a changed historical request and drift under an unchanged current request, which the applied decision expressly requires.

**Required correction:** determine request equality and compare complete fresh and sealed results before returning on non-inspectable outcomes. For unchanged mismatches, return the actual fresh result with `INSPECTION_REPLAY_MISMATCH`, no saved review provenance, and an explicit unchanged-request mismatch label. Changed historical requests must continue to return their actual abstention normally.

**Required regression:** preserve the unsupported-label actual-inspector witness, but require mismatch classification and the complete actual `SOURCE_LOCAL_LABEL_UNSUPPORTED` result. Retain the natural historical-refusal tests to prove request changes remain distinct.

### OBS-V1-002 — P2: the fresh-process import fence omits the real acquisition root

**Source:** embedded child program in the test file, v1 lines 724–737.

The test blocks transport roots and guessed `engine.collectors.*` / `engine.captures.*` prefixes, but omits the actual top-level `collectors` package. Both `collectors` and `collectors.sec_document_spine` pass the literal predicate. The exact `tests` package also passes the `tests.` prefix check, and `pytest` is not blocked if the proof is described as free of test and fixture imports.

The actual source owner established in the earlier pinned reader/storage inspection is top-level `collectors`, including `collectors.sec_document_spine`, `collectors.fundamental_forensics_acquisition`, `collectors.fundamental_forensics_companyfacts`, and `collectors.edgar_forensics`. Blocking a later `requests` import does not establish that the acquisition module itself was rejected before its loader could execute.

The new observation module's own import tree, as written, does not introduce a collector import. The finding concerns the advertised negative proof, not an observed production capture. Network/process/filesystem audit denial remains a separate useful guard and must not be confused with complete acquisition-import coverage.

**Required correction:** block the real `collectors` root and all its children. For a child described as test/fixture-free, block exact `tests`, its descendants, and `pytest`. Keep the required pure `lib.dataos.registry` available. Do not invent a ban on arbitrary registry names or claim an unperformed universal capture inventory.

**Required regression:** attempt the actual prohibited import names under the installed guard and demonstrate rejection before a later finder/loader. Keep intentional controls in their own receipt, and require zero unexpected denied events from actual consumer execution. Preserve the before-import network/process denial, write denial, existing-root check, narrow constructor event, complete parent/child output equality, and actual historical refusal.

### OBS-V1-003 — P2: a final modifying exception followed by absence loses effect uncertainty

**Source:** `_create_only`, v1 lines 662–677; append result mapping, lines 745–752.

The conditional create is attempted once, but its exception is discarded. A readback error produces effect-unknown for the final manifest, while a `None` readback produces ordinary `MANIFEST_NOT_AVAILABLE_AT_READBACK`. Thus a modifying timeout followed by an absence observation returns `REFUSED`, even though the unresolved write can complete after that observation. Different readback bytes also lose the modifying exception's uncertainty marker.

This is directly derivable without runtime execution: the `except Exception` branch executes `pass`, `_exact_read` returns `None`, and `_require` raises a refusal without `effect_unknown=True`. Append therefore takes its ordinary refusal branch. Existing tests cover timeout with matching bytes and timeout with unreadable readback, but not timeout followed by `None`.

The result retains an expected reference and states that a manifest was attempted without proving a commit. It does not falsely report success or no write. Nevertheless the required first-class `EFFECT_UNKNOWN` state is lost. The accepted Research Intelligence immutable-create precedent preserves a modifying cause until exact expected-byte readback resolves it; absence or mismatch after that cause remains uncertain.

**Required correction:** retain whether the final conditional write raised. Exact matching complete bytes may reconcile success. If the final modifying attempt raised and final readback is absent, different, or unreadable, return `EFFECT_UNKNOWN` with only the expected reference and safe fixed code. Never repair mismatching predecessors or retry the modifying operation blindly.

**Required regression:** an actual LocalStore-backed fault fixture must raise on the final write, return an actual absent readback, and later complete the pending create; the initial outcome must remain unknown. Cover a different-byte predecessor after the exception and prove later refusal without repair. Retain the matching-readback reconciliation control.

## Complete contract assessment

### Evidence identity and semantic restraint

The module accepts the seven role-specific exact byte inputs and computes the incumbent `inspect_candidate` output internally. The public append API has no precomputed-inspection parameter. The private `_inspection` path is used only by the reader after its own actual fresh inspection; it is not a public producer-authentication channel.

Every original input is retained as exact UTF-8 text with its raw hash and byte count. Candidate raw-file identity and canonical candidate-payload identity remain separate. The package seals the complete internally computed inspection, not a selected success label. Source record, pilot, web review, retained reviews, candidate, document, source, span and context bindings are checked together. Duplicate JSON keys, nonfinite numbers, invalid UTF-8, excessive depth/node counts, malformed identifiers and size violations are refused before storage writes.

The reviewer labels and review hashes remain untrusted content. The binding summary explicitly marks authorship, independence, source custody and semantic truth as not authenticated. The original web-review representation remains distinct from the new retained-byte reviews. The first retained review declares context byte coordinates and digest, which the implementation verifies; the principal review declares a character range, whose corresponding byte range and digest are derived and labeled rather than retroactively presented as a supplied principal digest. External receipt paths/hashes are preserved as unloaded claims.

The reviewed actual judgment fields fit the pilot-specific shape checks. H200 is required in the checked target and actual support value text; matching but broadened target labels are refused. The source-local planned integration remains a dated announcement. Candidate-native dataset/temporal/canonical-identity annotations must remain absent. Every result remains `NOT_ADMITTED`, Graph 1 projection null, and all downstream authority flags false. The module does not authenticate a reviewer, establish present commercial supply, resolve legal parties, grant publisher rights, or promote predictive eligibility.

The tests' Aurora/Boreal/Widget/H200 fixture is a synthetic stand-in for the same closed artifact shape. Permitting internally consistent supplied labels while declaring them unauthenticated is intentional; this review does not require hardcoded private Micron hashes or imply that JSON consistency proves semantics.

### Existing store API conformance

The incumbent `engine/research_vault/r2_store.py` at pinned main `4d736c55adb630a4a8eb11b261e31acd0f6dc48b` was previously inspected for the frozen adjudication: 47,498 bytes, SHA-256 `7ba42eb8f74c034413997707a35156e67342fb9a30ca2b80dde0f11d1dc7e2bd`. The relevant calls used here match its implemented contract:

```python
store.get_bytes_strict_bounded(
    key, expected_byte_length=length, max_byte_length=16384
)
store.validate_strict_conditional_write_capability()
store.put_bytes_strict_conditional(
    key, raw, expected_version=None, content_type=content_type
)
```

The keyword exact-length reader is essential: it checks bounded regular-file data under the incumbent native path discipline. The generic positional maximum-length read is not substituted. `expected_version=None` is create-only; this module never supplies an overwrite token. The reader does not validate write capability or construct a store. No factory, credential/configuration selection, listing, latest pointer, automatic registry entry or shared-store modification is introduced.

The store's existing predecessor-version cap is 16 KiB. This implementation uses at most 16 KiB chunks and manifest, avoiding a large-first-write/small-repeat inconsistency. Ordered per-chunk content hashes in the manifest bind sequence and package identity. This differs from an earlier illustrative package-hash-plus-index key sketch, but stays within the applied content-addressed namespace contract and is not a defect.

The immutable-create comparison for OBS-V1-003 is pinned `engine/research_intelligence/store.py`, SHA-256 `e06c21ac60f8ebbb07153bcc8fad3a9616d303b34ef931f6d8ab8b3cba844e33`, `_reconcile_immutable_create` / `_ensure_immutable_artifact`. That domain's producer and registry paths are not adopted.

### Bounds, publication and corruption

The full canonical serialized package is capped at 1 MiB, including escaping, with at most 64 chunks of 16 KiB and a 16 KiB closed manifest. Per-candidate/review/inspection bounds and structural JSON limits are separate. The canonical encoder accounts for escaped UTF-8 bytes before materializing the full serialized output. The focused sentinel test checks expansion refusal before full-package serialization.

Append validates inputs and output size before store effects, probes existing chunks for corruption, creates only missing components, rereads every chunk, reconstructs the complete expected package, and only then attempts the manifest. The manifest itself and full committed closure are read back after publication. Repeat probes the existing commit and verifies its entire exact closure before returning the same reference. No invocation clock or local path is added to identity; frozen timestamps already contained in supplied evidence remain part of those input bytes.

References bind a closed manifest digest and exact byte count, and do not accept caller-selected storage keys. The reader validates canonical manifest bytes, exact chunk sizes, every chunk digest, complete package digest/length, exact original components, and canonical package encoding. Correction links preserve older records, are never resolved automatically, and do not trigger target reads.

There is no repair path. Missing, corrupt, symlinked, nonregular or inconsistent objects cause refusal; an incomplete precommit leaves uncommitted components. Concurrent same-content creation is reconciled by exact readback. The remaining uncertain-final-write gap is specifically OBS-V1-003, not a justification for retries or overwrites.

### Fresh inspection and current-only handling

The reader calls the real incumbent inspector using the requested `as_of`, registry and support-text option. A request change is visible. Historical refusal returns the complete actual inspector result while omitting saved positive labels, support, prior-link semantics and retained-review provenance. Required source strings are explicitly checked absent from those historical outputs by the tests.

The current reader still compares all derived package-envelope fields before returning saved review provenance. It does not turn a sealed result into a historical success. The unchanged-refusal classification defect is precisely OBS-V1-001. Claims of current-only private inspection remain distinct from source chronology, registry availability, publisher permission and product acceptance.

## Test-source coverage and remaining execution gate

The 23 v1 test functions were read in full, including parametrized cases and the embedded child program. Useful actual-LocalStore test designs cover multichunk append/repeat/read, lost acknowledgement with matching readback, final/closure read uncertainty, two-thread convergence, absent/corrupt chunks and manifests, symlinks/FIFOs/directories, manipulated references, malformed self-hashed manifests, metadata/scope/authority mismatches, structural and escaped-size bounds, actual inspector refusal, forged saved positives, support-option changes, natural historical refusals, purpose holds, raw-versus-canonical identity, unresolved correction links, and exact-reader refusal without fallback.

The fresh child design uses Python `-B`, disables bytecode through the environment, constructs no source acquisition client, verifies the existing absolute LocalStore root, installs import/network/process/mutation denial before application imports, records the incumbent constructor's one already-existing-directory mkdir separately, and requires two complete child outputs to equal each other and the parent expectation. The v1 acquisition-root coverage gap must be corrected before treating that guard as sufficient.

Native execution remains pending. Source review cannot establish LocalStore filesystem behavior on the target host, actual import closure under native dependencies, execution time, R2 availability, hosted CI, complete private retained-source fit, or accepted integration. Root must run the bounded scoped native suites and the actual original-byte positive/repeat/fresh-history witness, preserve all unexpected-denial events, and verify the final source hashes independently. No remote store runtime permission or release is implied by this receipt.

## Final disposition

The next action is a separately frozen corrective delta review of OBS-V1-001, OBS-V1-002 and OBS-V1-003, followed by root-owned native validation of that exact corrected composition. No additional module redesign, shared-store change, registry row or broad source acquisition is warranted by this review. Frozen v1 remains **CHANGES REQUIRED** with native execution **NOT RUN**.
