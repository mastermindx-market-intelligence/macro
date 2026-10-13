# Independent review: frozen native SEC reader relocation

**Verdict: PASS_SCOPED_SOURCE_REVIEW. No blocking source finding was identified in the six frozen paths.** The implementation repairs the acquisition import boundary by relocating the existing pure native contract once and preserving its legacy aliases. This is a six-file source review, not final composed-operation acceptance, accepted-main verification, a real NVIDIA replay, or production admission.

Reviewer: `/root/reader_boundary_readiness`. Route: review. Assessment date: 2026-10-09. Root retains source, composition and release ownership. The reviewer authored neither the six-file source patch nor its repository tests; the separately prepared independent NVIDIA harness is not implementation acceptance evidence.

## Exact reviewed source

Base: Macro `7abc73b9496035b5b391ce65fa8c92197ef380d6`.

Frozen patch:

- Native path: `/Users/chriswong/Library/Caches/Mastermind/economic-network-native-reader-20261009/pro-002-builder/native-reader.patch`
- SHA-256: `0e037e87d4cd3b1c7a14e8c574c90d6e0813fbd149d9a61104bed650cf21ccea`
- Size: 35,124 bytes, 759 lines. All lines were read.

Builder source ledger:

- Native path: `/Users/chriswong/Library/Caches/Mastermind/economic-network-native-reader-20261009/pro-002-builder/source-verification.json`
- SHA-256: `a7de97b6bdabbc7347f2d815985e1ab2c5cbc1f3537d5853a53450cb4fc0b145`
- Size: 2,866 bytes.

Executing source workspace supplied by root:

`/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-network-native-reader-20261009-pro-002`

The reviewer independently checked all six file digests, reproduced the exact cached six-file patch using a read-only diff against the stated base, and rechecked all six digests at the end. The source identity is the immutable patch/file digest set below; no later whole-branch commit or merged source is implied.

| Reviewed path | Bytes | SHA-256 |
|---|---:|---|
| `engine/fundamental_forensics/sec_document_spine.py` | 48,206 | `ee240863943823e598083f45164c6a288e9098292a47a454cc70898c2bdf8366` |
| `collectors/sec_document_spine.py` | 42,289 | `1c6fec647373372858f4ad5fc0b6a88d9da84d605f5d14e8e148ac2ee7e8a3e5` |
| `engine/fundamental_forensics/filing_attestation.py` | 76,795 | `1b2693a9bbff66761a573a8c1bd5d32b352a2d43719407e2864fda6e725d0a47` |
| `engine/company_intelligence/pinned_relationship_candidates.py` | 11,962 | `afafacb978face2775c769844a2773e04a5cb5b755aacd6c9724d7e51eb07cb7` |
| `tests/test_sec_document_spine.py` | 50,400 | `050022e3e0d39ec644763d4b9377a3386bde7a81e33dbcf4495f5cc4cbd8f4bb` |
| `tests/test_company_pinned_relationship_candidates.py` | 27,799 | `08fa9e22f7c35681b2fd97ccd97796a01a98988b05b8d047c8368ff24f6eb669` |

The seventh original regression surface, `tests/test_fundamental_forensics_attestation.py`, was not changed by this patch. Its ledger digest remains `7a059d848d875929c665a716934ce58ff2c4accc94ac024f670d1b5f6e098d30`.

**Explicit exclusion:** another worker is changing `engine/company_intelligence/relationship_candidates.py` and adding `tests/test_company_relationship_review_set.py`. This review does not read, freeze, approve or attribute test proof to those changing bytes. The final composed operation needs its own exact-source verification after that work is settled.

## Findings by severity

| Severity | Finding |
|---|---|
| Critical / P0 | None identified in the six-file patch. |
| High / P1 | None identified in the six-file patch. |
| Medium / P2 | None identified in the six-file patch. |
| Nonblocking compatibility qualification | `ArchiveReceipt` and `ArchiveStoreError` now originate in the engine module, so their Python `__module__` changes. The legacy collector names alias the exact same class objects. The native persisted contract is canonical JSON; external reliance on a former Python module path is not exhaustively proven absent. |
| Evidence qualification | Existing fixture tests support the repaired source path. The original strict real-source NVIDIA runs remain failures; the new independent retained replay remains prepared and NOT_RUN. |
| Scope qualification | Remaining lazy collector imports in filing-package materialization are outside this correction. No all-Forensics acquisition-free claim is accepted. |

No further source change or test expansion is requested by this review. The qualifications above must remain truthful in final delivery language and source-binding receipts.

## Behavioral and canonical preservation

The reviewer independently compared the AST of every relocated definition against the original collector at the exact base. All twelve are identical, including decorators, signatures, annotations, docstrings and executable bodies:

`ArchiveReceipt`, `ArchiveStoreError`, `_decode_receipt`, `_http_metadata`, `_receipt_bytes`, `_receipt_id`, `_utc_text`, `archive_receipt_from_json_bytes`, `content_storage_key`, `manifest_storage_key`, `read_archive_object_bytes`, `receipt_storage_key`.

The complete existing declarations also match after removing only the intended collector imports:

| Production module | Preserved existing definitions/classes |
|---|---:|
| Engine SEC spine | 38 |
| Collector SEC spine, excluding the relocated definitions | 33 |
| Filing attestation | 37 |
| Pinned candidate adapter | 4 |
| **Total** | **112** |

This comparison includes the complete native reader and attestation-builder bodies, not only the changed import statements. The collector's public `__all__` list is exactly unchanged. Both moved safety-bound assignments are AST-identical. A fresh static symbol-table pass found no remaining unresolved collector globals after removal of the now-unneeded `parse_utc`, `stable_id` and `utc_text` imports.

Consequently, the source correction preserves the existing:

- canonical manifest validation, retained storage key, manifest identity and clocks;
- canonical receipt JSON and exact field set;
- stable receipt IDs and content/receipt keys;
- signed-64-bit JSON integer parsing and boolean rejection for byte lengths;
- 64 KiB receipt cap, 32 MiB document cap and compressed-content bound;
- canonical UTC validation and bounded, injection-safe HTTP metadata;
- strict `type(receipt) is ArchiveReceipt` and subclass refusal;
- trusted-length-plus-one bounded inflation, exact raw length and SHA-256 verification;
- original exception classes through their compatibility aliases, error messages and catch boundaries;
- source selector, full sidecar equality, raw/stored limits, temporal refusals and private candidate output shape.

The collector now imports the engine's exact public and private objects. It retains transport, pacing, capture, retention and publication behavior. Its writer still calls the same helper implementations through aliases. `ChecksumMismatch` and `ArchiveResponseTooLarge` retain the relocated exception as their exact base. There is no copied second decoder, receipt class, timestamp normalizer or gzip contract.

The engine's existing `manifest_content_key` is unchanged and remains the separate clock-excluding content-deduplication identity. It is not substituted for `manifest_storage_key`.

## Corrected import topology

The patch addresses all three collector imports inside its production scope:

1. The candidate adapter obtains `manifest_storage_key` from the engine spine at module load.
2. `PinnedSourceAuthority.read_archive_document` obtains canonical receipt decoding, receipt addressing and bounded gzip replay from the engine spine.
3. `build_filing_attestation` obtains the same canonical manifest key from the engine spine; its previous line-1162 collector import is removed.

The attestation receipt cap is now imported from the same engine owner with the same value, avoiding an additional independently defined bound. The package initialization sequence already imports the spine before exposing attestation, so these engine-owned imports remove the prior acquisition cycle instead of shifting it to another runtime phase.

The direct pinned-reader capability can therefore execute without loading its acquisition collector. The unchanged filing-package materializer and other filesystem/acquisition consumers still have their own dependencies. They are preserved rather than silently included in this source claim.

## Fresh-process regression assessment

The new repository test `test_fresh_reader_replays_without_acquisition_imports_or_side_effects` is meaningful for the actual defect:

- Only the parent process invokes existing synthetic writers and creates the expected positive result.
- The child is a new Python process, launched with `-B`, with the synthetic payload delivered through stdin and a foreign fixture working directory.
- Before consumer import it rejects preloaded acquisition dependencies and installs an import finder denying collector and transport modules.
- The network/process audit is installed before application imports. The filesystem guard begins after the already-existing LocalStore constructor and an exact fixture-state check, preserving the original constructor distinction.
- The child invokes the actual native authority and candidate API, requires the complete positive result, and checks all admission/authority boundaries.
- Attempted blocked imports and side effects remain recorded even if the adapter catches their exceptions. Empty lists are mandatory for success.
- Files and directories are checked by identity, timestamp and content digest; no latest pointer may appear.
- The parent requires exit 0, empty stderr, exact complete JSON output and unchanged fixture files.

The new compatibility test requires object identity through both public and private import paths, checks public exports, and verifies the exact transport exception bases. Existing tests already exercise the canonical receipt, malformed metadata, bounded inflate, native attestation and refusal behavior.

Both modified test modules retain every pre-existing top-level statement unchanged and append exactly one new test function each. No old assertion was removed or weakened.

This synthetic regression proves the import property under its actual execution setup. It does not pin all third-party packages or constitute real historical/source-custody proof. The separately prepared real-source harness adds digest-pinned execution-source binding and exact retained five-output comparison; that harness was not executed by this reviewer.

## Existing builder execution evidence inspected

These are existing builder-produced receipts/logs read independently by the reviewer. The reviewer did not rerun them. Root must not project their counts onto the subsequently changing manual review-set source.

All files below are in the same native `pro-002-builder` cache directory as the source ledger.

| Evidence | Actual result | Receipt SHA-256 | Log SHA-256 |
|---|---|---|---|
| `red-current.json` / `.log` | Exit 1; one failed regression. Denied collector import at `inspect_pinned_candidate`, original line 119. | `a012395403c14232ad373c703ab569e4e918f9167dd9899e0911e19babbe3fdc` | `2972b4e2f5f2a91030d7c4943d87771b30c4912ca94a5112d24577c37ed3b89f` |
| `red-key-only.json` / `.log` | Exit 1; one failed regression. Denied collector import in `read_archive_document`, original line 457, reached from candidate replay. | `f3b8f9aac20cfefe75186c64684e5472482e3d3538b5113a91142cacf3fb5129` | `ae2e746562cdcbc36da30f0457bdbc43ecc5be92ff797f2a2e84db07c43a4929` |
| `green-reader.json` / `.log` | Exit 0; three focused tests passed. | `88e5d95064fc6b2f483730240eb9eb833d8e33e2c22e372c9b6e842226e4602b` | `3183d614c5a5c034edd0987c7414018d93bfa366f0c10413498f56dec89c08a6` |
| `scoped-regression.json` / `.log` | Exit 0; **213 passed** across manual candidate, pinned candidate, SEC spine and attestation suites. | `0b28630ee9a8894fa2a78982412948becdb562c6749262af814cf478e6416a3d` | `cd4dba8b47c4ed62f30c956201394a2c01a36163d3756442877be0d7d73a5d69` |

The partial-key-only source ledger has SHA-256 `2edeb92f79c52a91f4e2e80cd0c362982b45a03cc4cb1d1d5493c033c0830b4e`. Its separate failed test is the decisive falsifier showing that moving only the adapter's manifest-key import is insufficient. Neither failed RED case is relabeled a success.

The log digests and byte lengths match their JSON receipts. The four-suite count remains builder execution evidence rather than an independently executed reviewer test. The test runs used native Python 3.14; final selected hosted CI and any other runtime coverage remain separate delivery gates.

## Real NVIDIA proof remains separate

The previously failed strict NVIDIA processes and their diagnostic remain untouched. All five outputs having matched during those runs did not satisfy their zero-denied-attempt criterion.

Prepared new harness:

`/workspace/scratch/9fd3d58c239a/lanes/replay_nvda_repaired_reader_prepared.py`

SHA-256 `42ffb74613ec7d5be9beb8b4c8a7a5e7a868580c84f72e73355b8736585b0940`.

Required source receipt and execution gate:

`/workspace/scratch/9fd3d58c239a/lanes/NVDA_REPAIRED_REPLAY_PREPARATION_20261009.md`

SHA-256 `8c2dfb870dbd04777a89ca7c271218607b723b0c342b94d2b9e8e811a7779001`.

**Real replay status: NOT_RUN.** Source capture hashes remain historical; repaired execution bytes must be bound through a new principal verification receipt. Premerge fixture/source review is not an accepted-merge or production claim.

## Return and required next step

Accept this review only for the exact six-file digest set above. Preserve the disjoint manual review-set writer, then freeze and review the actual composed source. Use normal exact-head selected hosted CI and release verification. Execute the prepared retained NVIDIA harness only after root supplies the required exact source receipt and explicitly authorizes that run.

No candidate/admission schema, Data OS dataset, canonical identity, Graph1 projection, source rights, production store custody, source acquisition, publication, served-product behavior or predictive authority is introduced by this correction.

No source/Git mutation, test execution, real replay, cleanup or owner message was performed by this reviewer. Native analysis processes were read-only. All preceding analysis processes were reconciled to exit 0; the final process, PID 64264, returned its full expected analysis output, but the subsequent completion read failed with Studio Direct `McpServerError: Connection timed out` (`UNAVAILABLE`, `mcp_network_error`). Its final exit status is therefore unverified. No same-route retry or inference of exit 0 was made. This carrier limitation does not erase the already returned, digest-checked source and log evidence, and does not establish any replay or release success. Only scratch review/preparation artifacts were written.

**STOP.**
