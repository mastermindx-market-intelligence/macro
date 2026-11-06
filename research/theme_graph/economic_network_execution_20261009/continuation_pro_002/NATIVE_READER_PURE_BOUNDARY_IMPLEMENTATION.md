# GMI native reader: pure retained-source boundary implementation

**Disposition: source and tests frozen for independent review. The fresh guarded native-reader regression passes, and the four scoped existing suites pass: 213 tests. No Git stage, commit, push, PR, merge, workspace release, real-source replay, or production admission was performed by this builder.**

Builder: `/root/pure_reader_builder`. Principal/source-finalization owner: `/root`. Work date: 2026-10-09 UTC. The Chairman's resumed end-to-end execution mission authorized this separately bounded engineering increment; it does not rewrite either strict NVIDIA postmerge audit failure from the previous increment.

## Source and custody

| Field | Observed or supplied value |
|---|---|
| Native host, independently read | `m2studio` |
| Canonical operation | `gmi-economic-network-native-reader-20261009-pro-002` |
| Workspace | `/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-network-native-reader-20261009-pro-002` |
| Branch, supplied by principal | `sol/web-gmi-economic-network-native-reader-20261009-pro-002` |
| Native HEAD, independently verified before edits | `7abc73b9496035b5b391ce65fa8c92197ef380d6` |
| Initial tracked/untracked status | Clean |
| Protected procedure pin, reconciled by principal | `Mastermind@7d82b9adb839d54e4ab25378ca333e498dd83fcc` |
| Skillpack/bootstrap, supplied by principal | `1.0.1 / 1` |
| Source instructions | Principal verified current AGENTS/CLAUDE bytes against the already-read accepted instructions; no nested instructions under the assigned paths. |
| Collision clearance | Principal's fresh bounded census covered all 34 discovered candidate open-PR inventories and the active build map; no overlap among the seven allowed paths. This builder did not extend that clearance. |

The old `pro-001` workspace and retained private NVIDIA capture were not touched. All source edits used the assigned existing workspace through Studio Direct. No raw worktree, clone, checkout, reset, clean, stash, owner message, credential operation, acquisition, store factory, or background watcher was introduced.

Native builder evidence is under:

`/Users/chriswong/Library/Caches/Mastermind/economic-network-native-reader-20261009/pro-002-builder`

Baseline bytes for all seven allowed files, source digests, full patch, full test logs, exact command receipts, and the structural preservation ledger are retained there. These are task evidence, not another runtime or data authority.

## Capability delivered

An actual positive `inspect_pinned_candidate` replay can now execute in a fresh Python reader process without importing the SEC acquisition collector or the guarded acquisition transport packages. The native reader still selects the exact snapshot/manifest/document, reads the canonical receipt sidecar, bounds gzip inflation, validates digest/length, and returns the entire native inspection result.

The implementation moves the existing pure contracts into their incumbent engine owner, `engine/fundamental_forensics/sec_document_spine.py`. The collector imports and re-exports those exact objects. There is no wrapper, copied dataclass, second decoder, key substitute, new fetcher, new store, new schema, or relaxed archive validation.

Three consumer imports were repaired:

1. The candidate adapter's canonical `manifest_storage_key` import.
2. `PinnedSourceAuthority.read_archive_document`'s sidecar decoder, bounded gzip reader, and receipt-key imports.
3. `build_filing_attestation`'s later `manifest_storage_key` import in the same attestation file.

The separate `filing_package.py` consumer remains outside this increment. This change does not certify every Fundamental Forensics operation as acquisition-free.

## Exact relocation and compatibility

The following twelve class/function bodies were relocated without structural changes:

- `ArchiveStoreError` and the frozen `ArchiveReceipt` dataclass.
- `manifest_storage_key`, `content_storage_key`, and `receipt_storage_key`.
- `archive_receipt_from_json_bytes` and `read_archive_object_bytes`.
- The complete private canonical closure: `_utc_text`, `_http_metadata`, `_receipt_id`, `_receipt_bytes`, and `_decode_receipt`.

The shared 32 MiB document bound and 64 KiB receipt bound now live with those pure contracts and are imported by the collector. The attestation receipt cap uses that same native bound. Existing 8 KiB HTTP metadata validation remains intact. `manifest_content_key` remains the separate clock-excluding deduplication identity and was not substituted for an object address.

The class/function AST bodies, including canonical JSON/ID computation, integer checks, exact receipt-type rejection, UTC normalization, metadata restrictions, and one-extra-byte bounded inflation, matched the original collector definitions exactly. Existing definitions outside the relocation were also compared structurally: 38 engine declarations, 33 remaining collector declarations, 37 attestation declarations, and four adapter declarations. For the two consumers, the comparison removed only the specifically relocated collector imports from the old AST before equality comparison.

The collector's existing `__all__` list is unchanged. A new compatibility regression requires collector and engine public functions/classes, the five private helpers, and the shared bounds to be the same Python objects. It also verifies the collector's transport-specific error subclasses still inherit the exact shared `ArchiveStoreError` class.

**Python module identity qualification:** the moved classes/functions now have the engine module as their implementation home. No `__module__` spoofing shim was added. A bounded actual-use search across `engine`, `collectors`, `tests`, and `scripts` found four files using `ArchiveReceipt` or the archive receipt/read APIs; none contained a pickle or `__module__` consumer for these objects. The legacy collector import attributes resolve to the same current objects through aliases. This is not a blanket pickle-compatibility guarantee: a newly generated pickle would identify the engine implementation, and an older deployment without the new engine exports is not certified to load it. The native persisted contract exercised here remains canonical JSON, not pickle. Runtime monkeypatching of a collector module's formerly defining globals is also not asserted as a supported compatibility contract.

## Fresh-process regression and falsifiers

The regression is `test_fresh_reader_replays_without_acquisition_imports_or_side_effects` in `tests/test_company_pinned_relationship_candidates.py`.

The pytest parent builds a wholly synthetic native retained snapshot using the existing writers and computes the complete positive expected output. It sends only synthetic candidate/selectors/expected output and explicit filesystem/import roots to a separately spawned Python child via standard input. The child does not import pytest, the test module, or any fixture writer.

Before consumer imports, the child:

- Disables bytecode writes and rejects prewarmed acquisition modules.
- Installs an import finder rejecting `collectors`, `requests`, `urllib3`, `httpx`, `aiohttp`, `boto3`, `botocore`, `urllib.request`, and `http.client`, including their submodules.
- Installs the same network/process audit denial and filesystem mutation event/open-flag rules as the previously reviewed strict replay harness.
- Checks the complete existing store directory chain is nonsymlink directories and records the synthetic fixture's file hashes, inode/device/mtime/size, and directory identities.

The existing `LocalStore` constructor's `mkdir(exist_ok=True)` occurs only against that independently checked existing store. Full fixture-state equality is required immediately afterward, then the full filesystem mutation guard is enabled at the same boundary as the earlier reviewed harness. The child performs the real `PinnedSourceAuthority` and candidate API replay, requires a positive complete result equal to the parent expectation, verifies `NOT_ADMITTED`/null Graph1/all false authority, checks that retained state and latest-pointer absence remain unchanged, and requires zero blocked imports and zero denied audit events. A swallowed exception or refused candidate cannot satisfy the regression.

Two actual red runs established that the test detects both required failure modes:

| Source state | Actual pytest result | Denied acquisition import's native caller |
|---|---|---|
| Original production bytes at `7abc73b9496035b5b391ce65fa8c92197ef380d6`; new test only | **1 failed**, pytest exit 1, 2.11 s | `engine.company_intelligence.pinned_relationship_candidates.inspect_pinned_candidate:119` |
| Only the exact canonical manifest-key helper moved and adapter import repaired | **1 failed**, pytest exit 1, 1.31 s | `engine.fundamental_forensics.filing_attestation.read_archive_document:457`, reached from the candidate adapter |
| Complete shared relocation and all three consumer imports | **3 passed**, pytest exit 0, 2.40 s | Fresh guarded reader, exact collector aliases, and existing sidecar/bounded-inflate test all passed. |

Neither original failed process was reclassified. The separate preexisting real NVIDIA postmerge failures also remain failed historical evidence. No dependency warming, event-list clearing, permission exception, guard suppression, or shifted acquisition import was used to get the new test through.

## Validation actually run

All commands used the native interpreter `/opt/homebrew/opt/python@3.14/bin/python3.14`, `-B`, `PYTHONDONTWRITEBYTECODE=1`, `pytest -p no:cacheprovider -q --tb=short`, the assigned workspace as `cwd`, and a distinct `--basetemp` beneath the native builder cache. No local `run_ci_pack --execute` was run.

Exact argument arrays, elapsed wall time, child exit status, log length, and log hash are in the matching `.json` command receipts. The wrapper processes themselves exited zero after saving the real pytest result; the expected red pytest children exited one.

| Receipt/log prefix | Pytest selectors | Result | Full log SHA-256 |
|---|---|---|---|
| `red-current` | `tests/test_company_pinned_relationship_candidates.py::test_fresh_reader_replays_without_acquisition_imports_or_side_effects` | 1 failed; child exit 1 | `2972b4e2f5f2a91030d7c4943d87771b30c4912ca94a5112d24577c37ed3b89f` |
| `red-key-only` | Same fresh-reader selector | 1 failed; child exit 1 | `ae2e746562cdcbc36da30f0457bdbc43ecc5be92ff797f2a2e84db07c43a4929` |
| `green-reader` | Fresh-reader selector; `tests/test_sec_document_spine.py::test_collector_reexports_the_exact_native_reader_contracts`; `tests/test_sec_document_spine.py::test_source_readback_helpers_validate_receipt_sidecar_before_bounded_inflate` | 3 passed; child exit 0 | `3183d614c5a5c034edd0987c7414018d93bfa366f0c10413498f56dec89c08a6` |
| `scoped-regression` | Complete files `tests/test_company_relationship_candidates.py`, `tests/test_company_pinned_relationship_candidates.py`, `tests/test_sec_document_spine.py`, `tests/test_fundamental_forensics_attestation.py` | **213 passed in 6.68 s**, child exit 0, no warnings | `cd4dba8b47c4ed62f30c956201394a2c01a36163d3756442877be0d7d73a5d69` |

The full scoped run reused the existing malformed receipt, canonical encoding, digest/size, bounded inflate, missing receipt, retention, clock, historical refusal, native attestation, and candidate-admission checks. Only two new tests were added; no mirror set of existing validation tests was created.

`git diff --check` passed. The final tracked/untracked status contained exactly the six intended modified files and no untracked files. `tests/test_fundamental_forensics_attestation.py`, the seventh allowed path, remained unchanged.

## Frozen source hashes

| Path | Bytes | SHA-256 |
|---|---:|---|
| `engine/fundamental_forensics/sec_document_spine.py` | 48,206 | `ee240863943823e598083f45164c6a288e9098292a47a454cc70898c2bdf8366` |
| `collectors/sec_document_spine.py` | 42,289 | `1c6fec647373372858f4ad5fc0b6a88d9da84d605f5d14e8e148ac2ee7e8a3e5` |
| `engine/fundamental_forensics/filing_attestation.py` | 76,795 | `1b2693a9bbff66761a573a8c1bd5d32b352a2d43719407e2864fda6e725d0a47` |
| `engine/company_intelligence/pinned_relationship_candidates.py` | 11,962 | `afafacb978face2775c769844a2773e04a5cb5b755aacd6c9724d7e51eb07cb7` |
| `tests/test_sec_document_spine.py` | 50,400 | `050022e3e0d39ec644763d4b9377a3386bde7a81e33dbcf4495f5cc4cbd8f4bb` |
| `tests/test_company_pinned_relationship_candidates.py` | 27,799 | `08fa9e22f7c35681b2fd97ccd97796a01a98988b05b8d047c8368ff24f6eb669` |
| `tests/test_fundamental_forensics_attestation.py` — unchanged | 20,222 | `7a059d848d875929c665a716934ce58ff2c4accc94ac024f670d1b5f6e098d30` |

Frozen complete patch: `native-reader.patch`, **35,124 bytes**, SHA-256 `0e037e87d4cd3b1c7a14e8c574c90d6e0813fbd149d9a61104bed650cf21ccea`.

Additional machine-readable evidence: `baseline.json`, `partial-key-only.json`, `relocation-ast.json`, and `source-verification.json` beneath the same builder cache. Baseline snapshots preserve the seven pre-edit file bodies.

Native PIDs reconciled to explicit completion: `35619`, `36285`, `40095`, `45559`, `46857`, `47371`, `47472`, `50349`, `51232`, `52489`, and `53335`. All outer processes exited zero; red child statuses are preserved above. One tool-side JavaScript template construction failed before native invocation while preparing the relocation command; no native process or source effect occurred from that failed tool expression, and the preimage-checked command was subsequently constructed correctly.

## Remaining scope and exact next action

This source change does not adopt production source-reader custody, native relationship facts, canonical legal identity, historical Data OS profiles, rights/entitlements, Graph1 admission, served product routes, rank/size/trade authority, or predictive promotion. No actual retained private source was read or recaptured by this builder.

The principal should independently review the frozen six-file diff and the exact guard regression, run the authorized existing real retained-source replay under the unchanged strict audit criteria, and complete ordinary CI/release through the current native owner procedure. CI selectors/workflows/inventory were deliberately not changed by this lane; actual hosted selection remains a principal integration responsibility. Independent review may also decide whether any narrowly relevant additional native consumer regression is needed for the shared-contract relocation.

**STOP: code and tests are frozen. The builder will not edit further unless explicitly asked by the principal.**
