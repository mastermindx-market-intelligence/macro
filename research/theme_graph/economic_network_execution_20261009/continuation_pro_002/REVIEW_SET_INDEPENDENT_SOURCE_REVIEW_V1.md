# Relationship review-set consumer: independent frozen-source review, v1

**Verdict: REQUEST_CHANGES. One P1 resource-bound defect and one P2 content-identity defect were established from the exact frozen source. Both were reported promptly to the principal and author, and the principal accepted them for correction before native application. Native application, native tests, and integration execution are NOT_RUN for this artifact.**

Reviewer: `/root/pure_reader_builder`, acting here solely as the independent reviewer of the review-set consumer authored by `/root/native_adoption_frontier`. The reviewer's own six-file pure-reader relocation is excluded from this independent review and verdict.

Date: 2026-10-09 UTC. Parent operation: `gmi-economic-network-native-reader-20261009-pro-002`.

## Exact reviewed artifacts and proof scope

| Artifact | Bytes | Lines read | SHA-256 |
|---|---:|---:|---|
| `lanes/review_set_prepared/relationship_candidates.py` | 44,241 | All 891 | `651925acd44a156993d07ada73907ee94e069ec39545659cc6d75c5dae4115d1` |
| `lanes/review_set_prepared/test_company_relationship_review_set.py` | 31,492 | All 618 | `83a0255d0a786bc559f3a09f486fdf9f9532915ea9b169fb44b27d60a8e524ef` |

Both digests were verified before inspection. The existing 444-line manual inspector was separately read in full from pinned `macro@7abc73b9496035b5b391ce65fa8c92197ef380d6`; its original file SHA-256 was `27543f4a37202820f34071607b5cbdb1e48a04c30577a876ba1f803e1c41891d`.

This review read the implementation and tests, traced actual source control flow, parsed the exact files with Python AST, and executed only explicitly extracted standard-library-only pure helpers for the two counterexamples below. It did not import the engine module, replace its native dependencies, execute fixture substitutes as application proof, run the pytest suite, access retained sources, load a registry, or retry the blocked native carrier. No source artifact, Git state, registry, store, or capture was changed.

The supporting script is `lanes/review_set_source_counterexamples.py`. Its saved output is `lanes/REVIEW_SET_SOURCE_COUNTEREXAMPLES.json`. The output explicitly labels its scope as exact pure-helper extraction and source-level arithmetic, with native application and integration execution `NOT_RUN`.

## R1 — P1: API candidate serialization exceeds its bound before the bound is checked

**Location:** frozen `relationship_candidates.py:518–539`, especially lines 528–530; shared serializer at lines 418–420.

`_review_candidate_binding` first runs `_bounded_json(candidate)`, then calls `_review_json_bytes(candidate)`, and only after the complete JSON string has been serialized and UTF-8 encoded checks the 256 KiB candidate cap.

The existing structural guard bounds depth, nodes, and individual scalar lengths. It does not bound the aggregate serialized byte length. In particular, a list containing 4,095 references to one 65,536-character string uses exactly 4,096 structural nodes and passes this preflight. The same scalar object can be shared by every list element, so the input need not already occupy the resulting serialized size.

The independent probe ran the exact extracted `_bounded_json` on that shared-object input and confirmed acceptance. The large JSON allocation was deliberately **not** performed. Exact JSON-size arithmetic gives:

| Scalar contents | Complete canonical JSON bytes before the late cap check |
|---|---:|
| 65,536 ASCII `x` characters, repeated 4,095 times | **268,382,206** |
| 65,536 NUL characters, repeated 4,095 times; each expands to a six-character JSON escape | **1,610,231,806** |
| Declared candidate cap | **262,144** |

This source path can therefore expand a small shared Python object into hundreds of megabytes or more before returning `INPUT_LIMIT`. The fact that the candidate is ultimately structurally invalid as a relationship does not remove the requirement for a bounded refusal. An exhausted process might fail before emitting the intended refusal, and `MemoryError` is not a bounded result branch here.

The same full-materialization helper is also used for review hashing and output-cap checking at lines 755–756. A repair should preserve the canonical encoding while applying an explicit bound during serialization, rather than allocating the entire encoded representation and checking afterward.

**Smallest repair:** a bounded canonical serialization/preflight path with exact UTF-8 and JSON escaping accounting. Preserve the existing individual inspector; enforce the new review boundary before unrestricted aggregate materialization. Do not merely reduce the already accepted node count or silently truncate data.

**Required regression:** an over-limit input should demonstrate that the serializer stops consuming/encoding once its finite budget is exceeded. A sentinel after the over-limit prefix is useful because a test that only asserts the eventual `INPUT_LIMIT` result would pass the defective implementation. Include escaping/multibyte expansion and preserve deterministic canonical bytes for admitted inputs.

**Status:** established from source and exact pure preflight; principal accepted for correction. No native allocation or native application was attempted.

## R2 — P2: CLI content identity includes the manifest byte order it claims to exclude

**Location:** `_review_identify`, lines 461–464; `_review_finish`, lines 717–720 and 755; `_review_files_cli`, lines 810–811 and 827–828.

The CLI records the original manifest's raw SHA-256 and byte length in `input_manifest`. `_review_finish` includes that provenance in the result. `_review_identify` hashes every result field except `content_sha256`, so it also hashes the raw manifest binding.

Reordering otherwise identical manifest cases changes the raw manifest digest, even though `_review_envelope` and `_review_finish` canonicalize the case order and the complete case results/reconciliation are unchanged. The declared `content_identity_scope` says the canonical content identity is not manifest-byte-order identity, and the approved interface requires that distinction.

The exact extracted `_review_identify` and `_review_json_bytes` helpers were applied to two minimal, explicitly synthetic dictionaries with identical canonical case arrays and different raw manifest provenance. These dictionaries are helper inputs, not claimed inspector or CLI outputs. Both raw manifests were 235 bytes and differed only in their two case entries' order.

| Value | Order A | Order B |
|---|---|---|
| Raw manifest SHA-256 | `5b489435425900c7b84921357daae9a7d6b76ccacb2918e0b6710c460a77111b` | `8976945e8e9717c4a152cbd03b03f5eddd545c3ead227f050cac223fd7b7df1c` |
| Content SHA from the exact helper | `0ea8bdd3f2d284db91957f5cae1682006ade1e9525b6dbf36df0e12767c5c63a` | `18f51871815bb77486336996ff7e0cc90f548662f0c335b797a68d509ba9ec9f` |

The existing API permutation test does not catch this because the API's `input_manifest` is null. The existing separate-process CLI test repeats identical manifest bytes and likewise does not exercise the defect. The candidate-JSON-whitespace test correctly distinguishes raw candidate-file bytes from canonical candidate identity; that separate behavior should remain intact.

**Smallest repair:** retain original manifest-byte provenance in the returned result while excluding it from the explicitly canonical content-identity preimage. Make the identity scope precise and continue binding options and actual returned content. Do not remove the raw provenance or misrepresent the content hash as a registry/history/rights attestation.

**Required regression:** invoke the actual CLI using the same candidate/source files and two manifest encodings with reversed case order. Require matching canonical content identity and case/reconciliation content while preserving distinct original-manifest byte hashes. A separate whitespace-only manifest rewrite is another useful instance of the same condition.

**Status:** established from source and exact pure identity helper; principal accepted for correction. Actual CLI integration is still `NOT_RUN` for the prepared artifacts.

## Other consequential boundaries inspected

No additional P1/P2 defect was established in the remaining frozen code. The following are source-review findings, not claims of passing native execution:

| Boundary | Source evidence and disposition |
|---|---|
| Closed schemas and unique case IDs | Exact outer/case key sets, ASCII bounded IDs, schema separation, case count, and duplicate case-ID rejection are present at 477–507. A later author-identified improvement to bound dictionary cardinality before set construction is being separately prepared; this review does not relabel that author finding as its own. |
| Actual inspection | 729–738 construct a bounded per-input failure only when preparation failed; all prepared valid cases call the existing `inspect_candidate`. Supplied inspector results are not accepted as substitutes. |
| Input-processing denominators | 721–752 retain per-case results, classify unavailable/refused/excluded/inspectable cases separately, and distinguish requested, prepared, processed, called, and retained counts. Registry failure occurs after the validated requested count is recorded. Aggregate and output refusals explicitly withhold semantic results and retain processing facts. |
| Native temporal exclusion | The individual inspector's existing temporal path remains ahead of semantic-view construction. Reconciliation at 659–700 selects only actual `INSPECTABLE` results and reads IDs/revisions from their current views. Excluded targets remain absent from the inspectable target set. |
| Revision/collision handling | Canonical candidate payload collisions, repeated canonical candidate/source input references, absent targets, and multiple target references remain explicit and unresolved. No winner, economic edge, original erasure, canonical legal-party mapping, or evidence multiplication is introduced. |
| File path and descriptor behavior | 565–608 require no-follow, directory, and nonblocking capabilities; traverse parent directories by descriptor with no-follow checks; open the final leaf nonblocking; require a regular file; cap size and bounded read; compare device/inode/size/mtime/ctime before/after; and redact paths/errors. This is stronger than `lstat` followed by ordinary `open`. |
| Per-file refusal behavior | 625–656 keep candidate/source preparation failures visible per case, distinguish invalid UTF-8 from original-byte availability, and withhold false canonical candidate hashes when JSON loading failed. |
| Aggregate admission and rights | Both aggregate and individual base results remain `NOT_ADMITTED`, null Graph1, all-false authority, public-export unauthorized, and public-safe/quote-free certification absent. Counts and unique digests are explicitly not coverage, precision, or independent corroboration. |
| Single-case compatibility | The original individual inspection flow and single-case processing/error/exit branches remain present. CLI mode exclusivity and conditional source-argument requirements are explicit at 837–886. Actual old/new native invocation equivalence remains a future execution gate. |

The test artifact includes cases for delegated complete results, exact counts, invalid/recursive inputs, duplicate IDs, 64/65 cases, aggregate/output refusal, correction ambiguity, repeated references, temporal exclusion, missing registry, support/rights boundaries, malformed/missing files, nonregular and symlink paths, FIFO swap, per-file caps, input-mode exclusivity, and separate-process CLI behavior. Reading those tests does not establish that they passed.

## Existing CI owner

The separate prepared ownership check inspected the incumbent `company-relationship-candidates` job. Its current manifest SHA-256 was `62598df9610b898e182abfae61da60bb06e417416125314d72379f9dd2706a64`. Removing exactly the new `tests/test_company_relationship_review_set.py` path entry and its addition to the existing pytest command reproduced the entire pinned baseline CI manifest byte for byte. The same job is already registered in pinned `tests/test_ci_pack.py`; no job-inventory edit was needed.

This establishes the intended CI owner/scope change. It does not establish hosted selection, a hosted run, or native test success for the new code.

## Required continuation

Preserve these v1 files and this REQUEST_CHANGES disposition. Review the separately versioned final corrections at their supplied hashes, reusing the unchanged semantic review rather than restarting it. The principal has separately requested review of bounded candidate serialization, manifest-provenance exclusion from canonical identity, and the author's dictionary-cardinality preflight hardening.

After final source review, the principal still owns native source application, combined suites, real-source CLI/replay proof, hosted CI, release, and accepted-source verification. There is no new production fact/identity/time/rights/admission authority in this review-set boundary.

**STOP for v1: no further reads of changing source or native-route retries. Final revised-source review will bind the separately supplied artifact hashes.**
