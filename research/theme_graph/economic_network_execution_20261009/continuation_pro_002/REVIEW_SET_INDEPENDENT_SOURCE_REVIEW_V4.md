# Independent prepared-source correction review: relationship review set v4

## Verdict and boundary

**Prepared-source PASS** for the exact v4 consumer and test artifacts identified below. The two blocking findings from the preserved v1 review are corrected. No additional P1 or P2 issue was found within the approved closed JSON-shaped review-set contract. This is a source-review verdict and a bounded pure-helper correction receipt. **Native application, native consumer pytest, full native CLI execution, and hosted CI are NOT_RUN by this reviewer.** Those remain separate evidence gates before an execution or integration pass can be claimed.

Review date: 2026-10-09. Reviewer: `/root/pure_reader_builder`. Consumer author: `/root/native_adoption_frontier`. Principal and source-finalization owner: `/root`.

Independence is limited deliberately: this review covers the new review-set consumer and its test file, authored by another worker, and the previously reviewed bounded CI registration. It does **not** independently review this reviewer's own six-file pure-reader relocation. Those six files remain frozen. This reviewer made no application source, native workspace, registry, retained store, source capture, Git, or CI edits during this assignment.

The original v1 REQUEST_CHANGES verdict and failing counterexamples remain preserved unchanged. This separate receipt records correction; it does not relabel the earlier failure as a pass.

## Exact reviewed artifacts

All paths in this report are under `/workspace/scratch/9fd3d58c239a/lanes/` unless stated otherwise. Digests are SHA-256 of complete file bytes.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `review_set_v4/relationship_candidates.py` | 45,473 | `a558922c0586a5532f3912524b48f3cf592c3c6c9c21f689e3d416976e9cae55` |
| `review_set_v4/test_company_relationship_review_set.py` | 35,165 | `67636cc6eca4f9be84b383bb44b4835a3dc8447f6b288e2e99073f61182ce212` |
| `review_set_v3/relationship_candidates.py` | 45,325 | `d1ab71e67169cd0fd701503f296061ef339604e6803c3e03210702fb8fead082` |
| `review_set_v3/test_company_relationship_review_set.py` | 34,245 | `b7fd864bbb35454dcc7927d32cf9865bb14f475a61113c3650d792e0a7e0cc97` |
| `review_set_prepared/relationship_candidates.py` (v1) | 44,241 | `651925acd44a156993d07ada73907ee94e069ec39545659cc6d75c5dae4115d1` |
| `review_set_prepared/test_company_relationship_review_set.py` (v1) | 31,492 | `83a0255d0a786bc559f3a09f486fdf9f9532915ea9b169fb44b27d60a8e524ef` |
| `REVIEW_SET_INDEPENDENT_SOURCE_REVIEW_V1.md` | 13,310 | `27553a1f4a926699e06084d867e236239385a6c5596d6e26d89f2d446a99eda0` |

The v1 consumer's complete 891 lines and test file's complete 618 lines were reviewed. The entire v1-to-v3 source/test correction diff and the complete v3-to-v4 source/test delta were reviewed. Final v4 has 916 consumer lines and 702 test lines. Semantic review of unchanged portions is reused from v1, bounded by direct diff inspection and AST comparison, rather than represented as a second independent full read.

An exact AST comparison of v1 and v4 top-level declarations, excluding positional attributes, found only these changed or added declarations: `_review_identify`, `_review_envelope`, `_review_candidate_bytes`, and `_review_candidate_binding`. The v3-to-v4 production delta is confined to `_review_envelope`. No consumer inspection, reconciliation, temporal filtering, file reader, count, CLI routing, or single-case behavior change was introduced by these corrections.

## Approved contract retained in this review

The API is `inspect_review_set(review_set, *, as_of=None, registry=None, include_support_text=False)` with the closed `company_intelligence.relationship_review_set/v1` envelope. The mutually exclusive CLI mode accepts a closed `company_intelligence.relationship_review_files/v1` manifest. The result remains `company_intelligence.relationship_review/v1`.

The review boundary includes the declared limits: 64 cases; 256 KiB manifest and individual candidate; 4 MiB individual source; 8 MiB aggregate candidates; 64 MiB aggregate sources; and 8 MiB output. Malformed outer structure, empty input, aggregate overflow, and output overflow are whole refusals. Individual missing or malformed files retain a visible per-case processing result. Paths and private source text must not leak through errors; nonregular files and symlinks are refused by the reviewed reader.

Existing actual inspector execution, one registry load, temporal refusal behavior, and complete per-case results remain required. Reconciliation is restricted to actual INSPECTABLE current views. Repeated bytes do not constitute independent evidence. Candidate-ID collisions and correction or contradiction links do not establish a preferred truth or automatic winner. Counts describe input processing. Cases and aggregate remain NOT_ADMITTED, with null Graph1 and false admission and predictive authority.

This contract is not a sandbox for arbitrary Python objects or hostile Registry subclasses. The exact-type checks below enforce the declared JSON-shaped input boundary; they do not establish isolation from arbitrary code supplied by an in-process caller.

## Corrected findings

### R1 — P1: candidate serialization could expand before enforcing the byte limit

The v1 `_review_candidate_binding` performed complete canonical `json.dumps` and UTF-8 encoding before checking the individual 262,144-byte candidate cap. Its existing node and scalar limits did not prevent a shallow list of 4,095 references to the same 65,536-character string. This passed the exact bounded-JSON preflight while permitting a calculated canonical expansion of 268,382,206 bytes for ASCII, or 1,610,231,806 bytes for NUL characters escaped by JSON. The original proof did not allocate those large serialized outputs.

The correction in v4 `_review_candidate_bytes`, lines 523–542, preserves the existing bounded-JSON preflight and canonical encoder configuration, then iterates the real standard-library encoder. Each chunk is encoded to UTF-8 and added to the running byte count. The helper refuses with INPUT_LIMIT before appending a chunk that would exceed the candidate cap. It joins retained chunks only after the entire bounded candidate has passed. `_review_candidate_binding`, lines 545–564, now consumes this helper instead of the unbounded materializing operation.

Independent exact-helper probes establish the following bounded observations. These measurements include the refused current chunk in `encoded_bytes_consumed`; they do not assert that every measured byte was retained.

| Shared scalar in the 4,095-item input | Encoder chunks consumed before refusal | Encoded bytes consumed through refusal | Result |
|---|---:|---:|---|
| 65,536 ASCII characters | 4 | 262,156 | INPUT_LIMIT |
| 65,536 NUL characters, escaped by JSON | 1 | 393,219 | INPUT_LIMIT |
| 65,536 four-byte UTF-8 characters | 1 | 262,147 | INPUT_LIMIT |

The probes also verified byte-for-byte parity with the existing canonical encoder for a bounded candidate, acceptance at exactly 262,144 canonical bytes, and refusal at 262,145 bytes. They use the real JSON encoder with an observation/sentinel wrapper; unmodified chunks are delegated to the exact extracted helper. A sentinel prevents consuming more than eight chunks, so the original amplification is not recreated in scratch.

**R1 disposition: resolved at prepared-source level.** The correction limits retained canonical candidate bytes and stops proportional expansion of the repeated input before full materialization. A single encoder chunk can transiently exceed the cap, especially for escaped or multibyte text; the existing scalar cap bounds that chunk, and it is refused before retention. This is not a claim that the entire process heap never exceeds 256 KiB. The separate bounded output path remains as reviewed in v1; no new concrete blocking defect in it was established during the correction review.

### R2 — P2: canonical content identity depended on raw manifest order

The v1 `_review_identify` included `input_manifest` in the hash preimage. Consequently, reordering or reformatting a file manifest changed the advertised canonical content identity even when the canonical case order, inspected results, candidate bytes, source bytes, and options were unchanged. The original API permutation regression did not cover this CLI-specific raw provenance binding.

The correction in v4 `_review_identify`, lines 461–467, excludes only `content_sha256` and `input_manifest` from the identity preimage. The result still returns the raw manifest byte count and SHA-256 as provenance. Canonical content and raw input representation are therefore separately observable. Other result fields, including effective options, remain in the content preimage.

The independent exact-helper probe supplied the same canonical result content with two raw manifests differing in case order and whitespace. Their raw representations remain distinct:

| Raw provenance | Bytes | SHA-256 |
|---|---:|---|
| First manifest | 251 | `2cdbb229dd621084496ec2a2f7bf69cd02293474b575bee97943ed3616af7d2f` |
| Permuted/reformatted manifest | 319 | `87a1c6b81da17b9e2c3abf70b47de36d468ef0c618aaec4e9fffc436043b9f29` |

Both exact-helper content hashes are `50c7814a0611f2ffa3a0481defc805a6761ec74c25c1548ba4702b1229eeb872`. Both original raw bindings remain in their respective result dictionaries. Changing effective options changes the identity. This probe tests the exact hash helper on explicit minimal dictionaries; it is not a manufactured successful inspector result or substitute proof of a full CLI call.

The author's added regression invokes the actual CLI for permuted and reformatted manifests, checks equal canonical content identity, and checks differing retained raw provenance. Its source was reviewed, but it has not been executed natively by this reviewer.

**R2 disposition: resolved at prepared-source level.** The content hash covers the canonical returned content and declared options. It does not claim native history, registry attestation, original manifest byte identity, rights, custody, or source truth beyond its explicit bound values.

## Additional correction delta

The author identified and corrected the exact-cardinality issue before finalization. Version 3 requires an exact dictionary and exactly three members for the outer envelope and every case before converting keys to a set. The probe places 10,000 keys in each position and instruments the set conversion to assert that oversized mappings are refused before key-set copying. Both positions return REVIEW_INPUT_INVALID. The author's corresponding regression was reviewed.

Version 4 adds exact-string checks for every outer/case key before set conversion, and an exact-string schema check before equality. Short-circuit ordering is correct: dict type and cardinality precede key traversal; key type precedes set conversion; schema type precedes schema comparison.

The author adds three test cases: a schema object whose equality raises, and hostile key hashing for outer and case mappings. The independent exact-helper probe additionally uses nonstring keys that collide with the expected schema or case-ID key hashes, with armed hashing and equality callbacks. All are rejected without invoking those callbacks after construction. These probes establish the concrete short-circuit behavior and do not extend the API's authority or advertise general in-process isolation.

No unrelated production declaration changed in v4. No additional P1 or P2 finding arose from this final delta.

## Evidence and commands

The local probe commands completed with exit status 0:

```text
python -B lanes/review_set_source_counterexamples.py > lanes/REVIEW_SET_SOURCE_COUNTEREXAMPLES.json
python -B lanes/review_set_v3_correction_probe.py > lanes/REVIEW_SET_V3_CORRECTION_PROBE.json
python -B lanes/review_set_v4_correction_probe.py > lanes/REVIEW_SET_V4_CORRECTION_PROBE.json
```

Each correction probe pins the complete source digest, extracts only the named pure helpers and required constants by AST, and uses standard-library dependencies. It imports no engine module and executes no source reader, native registry, acquisition transport, retained capture, or native test fixture. Both outputs explicitly label their proof scope as `exact_pure_helper_extraction_only_not_native_application_or_integration` and native application/integration as NOT_RUN. The small script and JSON outputs are preserved for reproduction and inspection; their successful execution must not be counted as a native suite or real-data proof.

| Evidence artifact | Bytes | SHA-256 |
|---|---:|---|
| `review_set_source_counterexamples.py` | 4,150 | `ed6ac629cf2081913ba9850b0c68dab54f02909cbc6c7d1b4489eb09f2aa2eaa` |
| `REVIEW_SET_SOURCE_COUNTEREXAMPLES.json` | 1,283 | `24c5a0b315b43e3bbe98feb0d743f2bca14557a355c04cc8cd55ae5e612bb729` |
| `review_set_v3_correction_probe.py` | 5,769 | `9376875ab7caa8faa47a1c45b24bae643b8d9373a5791bd6b0ff72715ed2f678` |
| `REVIEW_SET_V3_CORRECTION_PROBE.json` | 1,729 | `458ae0219ead11440299e8f8653409c37763a340d42cb996367f84ee078a86b6` |
| `review_set_v4_correction_probe.py` | 7,350 | `179b70b88b600ab3b2576617fbb9ebfd48b90c198daaeccd4353e83c3d3de216` |
| `REVIEW_SET_V4_CORRECTION_PROBE.json` | 1,787 | `dde4c44c6a7ba5398ece4459ceaac4b7ef351c6045212a93f859a15d55ae4df7` |

The v1 report, original source/test artifacts, v3 source/test artifacts, and v4 source/test artifacts were rehashed during finalization. Their hashes match the recorded values. Original failures and intermediate correction evidence are preserved separately.

## CI ownership and remaining execution gates

The existing `company-relationship-candidates` CI job already has curated registration. Root alone added the new test path to that job's path inventory and pytest command. The read-only comparison established that removing exactly those two additions reproduces the whole baseline manifest. There is no new job and no `tests/test_ci_pack.py` edit is required. This bounded ownership assessment is reused unchanged from the v1 report; hosted execution has not been observed by this reviewer.

Reviewed root CI artifact: `.github/ci/legacy-jobs.yml`, SHA-256 `62598df9610b898e182abfae61da60bb06e417416125314d72379f9dd2706a64`. The retained command includes the existing manual and pinned candidate suites plus the new review-set suite. The legacy representation's pre-existing `if: ${{ false }}` is not evidence that the curated job is unregistered. The registration source was read at its existing location in the baseline `tests/test_ci_pack.py`, whose SHA-256 is `96582f4ef8db62c68c550e6f3bfd51c3847f564f16ec8987fe7c3b32acb1ca70`.

Read-only review PIDs 59090, 60243, and 60468 were reconciled to completion with exit status 0. PID 63338 returned the complete successful CI comparison and registration output, but the final exit-status read timed out. Root owns connection recovery and that completion reconciliation. This report does not invent a confirmed exit status for it. No source mutation occurred in that read-only process, and this reviewer made no further native retry.

The source-review pass permits the principal's next authorized step: apply the exact frozen consumer/test bytes to the already verified canonical M2 workspace and obtain native author test evidence. Native regression execution must establish that actual imports, inspector execution, file handling, temporal behavior, registry use, and CLI output cooperate in that workspace. Root separately owns real retained-source replay, exact application/hash verification, final combined-diff review, hosted CI, and any publication or integration decision.

This reviewer has not staged, committed, pushed, published, merged, released, changed admission status, or altered any production registry or source rights. The six-file pure-reader implementation remains frozen and outside this independent verdict. This receipt is ready for root's authorized durable publication with the earlier failure report.

**STOP: review complete. No further source edits, native tests, or route retries by this reviewer without a new bounded assignment from root.**
