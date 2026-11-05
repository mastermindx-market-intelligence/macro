# Native review-set consumer — implementation and verification receipt

Date: 2026-10-09 UTC  
Lane: /root/native_adoption_frontier  
Operation: gmi-economic-network-native-reader-20261009-pro-002  
Status: IMPLEMENTED, NATIVE TESTS PASS, TWO-PATH SOURCE FROZEN, NOT ADMITTED

## Outcome and exact source

The closed v1 review-set API and explicit file-list CLI have been added to the existing Company Intelligence manual relationship inspector. Every usable case delegates to the unchanged inspect_candidate implementation and retains its complete result. Missing or malformed supplied files remain visible per-case refusals. The aggregate reports processing of the caller's supplied inputs and unresolved review annotations; it does not admit relationships or grant rank, gate, size, trade, prediction, identity, rights, or production authority.

Native workspace:

/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-network-native-reader-20261009-pro-002

Branch: sol/web-gmi-economic-network-native-reader-20261009-pro-002  
Base HEAD: 7abc73b9496035b5b391ce65fa8c92197ef380d6  
Common Git: /Users/chriswong/Documents/Cluade/Macro Dashboard/.git

Exactly these two authorized source paths were written:

| Path relative to workspace | Bytes | Final SHA-256 |
| --- | ---: | --- |
| engine/company_intelligence/relationship_candidates.py | 45,473 | a558922c0586a5532f3912524b48f3cf592c3c6c9c21f689e3d416976e9cae55 |
| tests/test_company_relationship_review_set.py | 35,165 | 67636cc6eca4f9be84b383bb44b4835a3dc8447f6b288e2e99073f61182ce212 |

These are exactly the independently reviewed and accepted v4 artifacts at:

/workspace/scratch/9fd3d58c239a/lanes/review_set_v4/

No source corrections were needed after native application. Native final hashes were checked again after both test runs. The pure-reader builder's six source/test paths and the root-reserved reader_builder_evidence copy target were not written by this lane. Root owns shared CI enrollment, composition, real-source replay, and Git release. This lane did not stage, commit, push, create a PR, run a CI controller, acquire sources, invoke a model/provider, or alter a registry or native admission.

## Frozen interface

API: inspect_review_set(review_set, *, as_of=None, registry=None, include_support_text=False).

Closed API envelope:

    {
      "schema": "company_intelligence.relationship_review_set/v1",
      "review_set_id": "opaque-review-id",
      "cases": [
        {"case_id": "opaque-case-id", "candidate": {}, "source": "original UTF-8 source"}
      ]
    }

Closed file envelope:

    {
      "schema": "company_intelligence.relationship_review_files/v1",
      "review_set_id": "opaque-review-id",
      "cases": [
        {"case_id": "opaque-case-id", "candidate_file": "explicit.json", "source_file": "explicit.txt"}
      ]
    }

CLI: python -B -m engine.company_intelligence.relationship_candidates --review-set FILE.

The new --review-set mode is mutually exclusive with --candidate and forbids --source. Existing valid single-case input handling, inspection results, and exit behavior remain intact. The new mode uses the existing --as-of, --registry, and --include-support-text options. When supplied, the native registry loader is invoked once for the request. No PRODUCED registry row is created or borrowed.

Review and case IDs are unique opaque ASCII identifiers, 1–128 characters, matching [A-Za-z0-9][A-Za-z0-9._:-]{0,127}. Cases are processed in canonical case-ID order. An empty set is a typed refusal, not a successful zero-case review. Duplicate case IDs refuse the outer request before case-file reads.

| Limit | Value |
| --- | ---: |
| Cases | 64 |
| Raw review manifest | 256 KiB |
| Candidate per file / canonical API payload | 256 KiB |
| Source per file / API UTF-8 source | 4 MiB |
| Aggregate candidate input | 8 MiB |
| Aggregate source input | 64 MiB |
| Aggregate output | 8 MiB |

Existing candidate nesting, node, scalar, and finite-number controls apply. Canonical candidate serialization streams encoder chunks and stops at the candidate cap. Aggregate preparation checks occur after each individually bounded case; crossing a cap refuses the whole request before subsequent cases are read. Peak preparation can therefore include the individually bounded case that first crosses the aggregate threshold.

The output schema is company_intelligence.relationship_review/v1. It includes complete per-case inspections, opaque input bindings, honest processing counts, processing denominators, unresolved reconciliation, explicit content/rights limitations, and permanent NOT_ADMITTED/null/false authority boundaries.

Raw candidate file byte hashes are separate from canonical candidate payload hashes. API candidate bindings identify canonical payloads and do not claim original file bytes. Source bindings identify supplied bytes, with a UTF-8 validity marker; even an invalid-UTF-8 source file remains countable as supplied bytes. Host paths and raw loader exceptions are not added to output by the new loader.

content_sha256 identifies canonical review content: frozen options, canonical case order, input bindings, and results. The raw review manifest digest/length is retained separately in input_manifest and excluded from canonical content identity. A different manifest order or whitespace may change that raw witness while preserving content_sha256. Neither identity is native history, production custody, a registry attestation, or a rights receipt.

The processing denominators are requested cases, supplied-source cases, unique supplied-source byte digests, inspectable cases, refused cases, unavailable cases, and not-known-as-of cases. They do not measure universe coverage, precision, recall, relationship count, or independent support. Whole-request refusal withholds case results and semantic reconciliation while retaining honest nonsemantic work counters.

## Review and temporal behavior

Only actual INSPECTABLE results returned by inspect_candidate contribute semantic aggregate annotations. Raw candidate inputs from NOT_KNOWN_AS_OF or temporal-refused cases never establish candidate IDs, revision target presence, identities, support, or revision payloads in reconciliation.

The consumer reports, without choosing a winner:

- The same visible candidate ID paired with different canonical payload digests.
- Repeated identical candidate-payload and source-byte input references.
- Explicit corrects and contradicts annotations with absent, ambiguous, or present-but-unresolved visible targets.

A visible revision annotation that points at an excluded case remains absent from the inspectable target set. No excluded raw candidate resolves it. Repeated source bytes do not become independent corroboration. No parties are coalesced, no original candidate is erased, and no contradictions are inferred from prose.

The default omission of dedicated support text retains the existing manual-annotation content caveat. Manual annotations may themselves contain source text. Neither support mode establishes quote-free, public-safe, training-eligible, export-authorized, or commercially licensed content.

## Regular-file and source-boundary handling

The new file mode uses descriptor-relative parent traversal with O_NOFOLLOW and O_DIRECTORY, and final-file open with O_NOFOLLOW and O_NONBLOCK. It fstats the opened descriptor, requires a regular file, enforces the byte cap, and checks file metadata/length consistency across the read.

Symlinks in any path component, nonregular files, FIFO replacements, and parent traversal are rejected with stable codes. The meaningful race regression swaps a candidate path to a FIFO at open time and verifies nonblocking descriptor refusal. This mechanism performs no recursive discovery, network access, or subprocess invocation.

The no-follow behavior means real-source callers should supply authorized physical paths when a cache alias contains a symlink component. This is regular-file input validation, not a filesystem sandbox or a grant of source rights.

## Independent review and corrected findings

The accepted v4 bytes preserve all earlier frozen versions for audit. Two independent review findings were corrected before application:

1. The initial canonical candidate serialization could materialize an approximately 256 MiB expansion of a small object containing repeated large strings before checking its 256 KiB cap. The implementation now streams and bounds encoded chunks. A sentinel regression fails if the encoder remainder is consumed beyond the first over-budget portion.
2. The initial content identity included raw input-manifest provenance. The canonical identity now excludes it, and the actual CLI permutation/whitespace regression verifies stable content identity with distinct raw-manifest witnesses.

Subsequent in-scope resource-shape fixes check envelope cardinality before creating a key set and require exact string keys/schema before shape comparisons. The final independent prepared-source review was PASS. No further arbitrary-Python sandboxing or Registry-subclass hardening was added beyond the closed JSON-shaped contract.

## Native verification

Authorized carrier: Remote Desktop Commander on explicit device 3f5ce987-e3eb-40a3-af9f-4b0ae54919cc, verified by root as the same m2studio host. Python: /opt/homebrew/Caskroom/miniconda/base/bin/python3, version 3.12.4; pytest 9.1.0.

Before application, this lane asserted the exact workspace, branch, base HEAD, unchanged manual-module SHA-256 27543f4a37202820f34071607b5cbdb1e48a04c30577a876ba1f803e1c41891d, and absence of the new test.

After application, all existing manual functions, including inspect_candidate and every existing helper, were compared against base and remained byte-for-byte identical. The existing single-case execution tail is identical except for one terminal blank line. That final newline caused a strict pretest text comparison to stop before pytest on the first attempt; the failed pretest receipt is retained. No test ran during that attempt, and no source correction was necessary.

All actual test commands used PYTHONDONTWRITEBYTECODE=1, Python -B, pytest -p no:cacheprovider, and task-cache basetemp paths outside the repository.

### Existing manual suite plus new review-set suite

Command, from the canonical workspace:

    PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/Caskroom/miniconda/base/bin/python3 -B -m pytest -p no:cacheprovider tests/test_company_relationship_candidates.py tests/test_company_relationship_review_set.py -q --basetemp=/private/tmp/gmi-economic-network-native-reader-20261009-pro-002-review-set/run-002/pytest-temp

Result: 171 passed in 3.50 seconds; exit 0. RDC PID 9561 completed and was reconciled.

Full log: /private/tmp/gmi-economic-network-native-reader-20261009-pro-002-review-set/run-002/pytest.log  
Log SHA-256: 110a64280e4b840e4985d704fe38b496c6e50c667acce85ba3c865a713a4d456  
Receipt SHA-256: c672d0f5057678c49a588435ab02e3311f05589777c409c9650d7e90b462e258

The suite covers mixed positive/missing/malformed/invalid-source cases and exact denominators; complete replay delegation and original refusal preservation; closed shapes, duplicate JSON, constants, Unicode, byte limits and bounded expansion; aggregate/output refusal; one cutoff and one native registry load; deterministic API/second-process CLI behavior; raw versus canonical identity; collision/revision handling; temporal semantic suppression; all authority boundaries; support mode; single-case compatibility; and regular-file/symlink/FIFO/race refusal.

### Existing pinned-adapter suite

The pinned adapter is a concrete downstream caller of the shared manual inspector, so its suite was run once after the extension.

    PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/Caskroom/miniconda/base/bin/python3 -B -m pytest -p no:cacheprovider tests/test_company_pinned_relationship_candidates.py -q --basetemp=/private/tmp/gmi-economic-network-native-reader-20261009-pro-002-review-set/run-003-pinned/pytest-temp

Result: 44 passed in 2.06 seconds; exit 0. RDC PID 10929 completed and was reconciled.

Full log: /private/tmp/gmi-economic-network-native-reader-20261009-pro-002-review-set/run-003-pinned/pytest.log  
Log SHA-256: a740da298aac1a8dc98e3d2a6011cef26f78ba77b6d0767aab78da4c927273ba  
Receipt SHA-256: cf20ea42ec673d8c11f5bc0451f1a16b28508bc7d0283d7e91c50cdc243b6fcc

Combined authorized suite runs: 215 tests passed. No broader test or CI controller was run by this lane.

### Process reconciliation and receipts

| Native RDC PID | Purpose | Reconciled result |
| --- | --- | --- |
| 2925 | Read-only baseline preflight | Exit 0 |
| 6467 | Strict text-preservation precheck; stopped before tests | Exit 1; one terminal blank line only |
| 7906 | Diagnose/preserve the precheck result | Exit 0 |
| 9561 | Manual and new review-set suites | Exit 0; 171 passed |
| 10929 | Pinned-adapter compatibility suite and final hashes | Exit 0; 44 passed |
| 12710 | Read-only receipt export | Exit 0 |

The two source writes returned completed success responses and their actual bytes were verified. There is no unresolved process or ambiguous write effect in this lane. Root's separate old Studio Direct evidence-copy operation remains outside this lane's work.

A scratch export contains the exact five native receipt/log contents, native paths, byte counts, and SHA-256 witnesses:

/workspace/scratch/9fd3d58c239a/lanes/review_set_native_receipts.json

## Evidence limits and root-owned next step

These passing tests establish the bounded consumer's synthetic contract behavior and compatibility with its existing manual and pinned callers. They do not establish economic precision, representative relationship coverage, real-source correctness, independent corroboration, native production adoption, a historical identity graph, legal counterparty identity, source custody, rights, or predictive eligibility.

No production row, native capture, registry revision, latest pointer, canonical identity, evidence custody receipt, or rights authorization was created. The API continues to treat supplied registry and annotation inputs as caller-supplied and unverified, within the existing inspector's checks.

Root can now compose the independently frozen pure-reader repair with this source-only review consumer, run the authorized real Micron/NVIDIA harness, reconcile current source collisions, and perform the owning CI/Git release. Real replay must keep the original NOT_ADMITTED and null/false authority boundaries and must describe supplied-input counts without promotion.

STOP — this bounded two-path implementation lane is complete and source-frozen.

