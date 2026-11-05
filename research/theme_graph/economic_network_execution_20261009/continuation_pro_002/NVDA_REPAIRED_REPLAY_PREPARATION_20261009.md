# Independent retained NVIDIA replay: prepared, not executed

**Status: PREPARED_NOT_EXECUTED.** The principal must supply a frozen, independently verified source receipt and explicitly authorize the real replay. No current builder source bytes were read or frozen while preparing the harness. Both prior failed strict runs remain failed.

## Prepared artifact

`/workspace/scratch/9fd3d58c239a/lanes/replay_nvda_repaired_reader_prepared.py`

- Bytes: 28,986
- Lines: 576
- SHA-256: `42ffb74613ec7d5be9beb8b4c8a7a5e7a868580c84f72e73355b8736585b0940`
- This is a scratch-only standalone harness intended for native fresh `python3 -B` stdin execution. It writes no file, invokes no Git, launches no child process and creates no capture or credential factory.
- Preparation validation parsed its Python AST only. The new harness and application code were not executed.

The original script remains byte-identical at SHA-256 `6f728fea586f13f2ae9f8af037c1dae3e2aeedfdf338f3a193e43cc55bc57e89`. The original diagnostic script and both historical failure receipts remain separate artifacts. No criterion or historical outcome was rewritten.

## Inputs and preserved checks

The new script pins the original capture, complete witness, both private candidate files, and immutable source-snapshot descriptor to their existing exact SHA-256 digests. The pinned descriptor supplies the five retained object keys, lengths and digests. Every object is verified before consumer import, every path is nonsymlink/bounded, and all verified file identities/digests are checked again before imports and after replay.

The five actual API calls and full-output comparisons are preserved: current candidate, historical cutoff, candidate metadata mismatch, missing document selector and unsupported source labels. The two private files remain private inputs. Successful output publishes only outcome status/refusal, complete-output digests and null/false leaf counts, not source bodies or candidate annotations.

All five result comparisons, `NOT_ADMITTED`, null Graph1, all false authority flags, null refusal bindings and null historical current view/provenance/support are required. Existing task/store directory checks and absence of `latest.json` remain required.

An AST comparison confirmed that the network/process audit function, filesystem event set, write flags, five API-call expressions and fixed input digest map are identical to the original strict script. The filesystem guard still starts immediately after the existing LocalStore constructor and its directory-identity check. The script does not claim that this constructor never attempts `mkdir(exist_ok=True)`.

## Fresh imports and exact executing source bytes

The script rejects preloaded first-party modules and any preloaded forbidden package, then installs the import boundary before importing the consumer. `collectors.sec_document_spine`, `requests` and `urllib3`, including their submodules, are explicitly denied. Every denied import is recorded and must leave the process failed, even if application code catches its exception. No dependency is prewarmed and no event list is cleared.

First-party modules use a small verified source loader that compiles the exact digest-checked `.py` bytes under the fixed new canonical workspace. This matters because `-B` prevents `.pyc` writes but does not itself prove that an existing bytecode cache was not loaded. The loader does not stub or modify application source and does not hide its imports. First-party paths outside the supplied verified inventory fail closed. Third-party runtime packages are not claimed to be fully pinned.

The existing network/process audit predicates remain unchanged. All denied events must be empty for PASS. Failures emit a sanitized `FAIL` JSON receipt and exit 1; partial output equality or unchanged files cannot relabel them PASS.

## Separate current-code binding

Historical acquisition-code hashes are never required to equal repaired reader hashes. The immutable capture and witness still preserve their original code-head/hash provenance. A separate principal-generated verification receipt binds the current replay source.

The CLI requires three arguments:

| Argument | Required actual value |
|---|---|
| `--source-receipt` | Absolute existing nonsymlink JSON path under `/Users/chriswong/Library/Caches/Mastermind/economic-network-native-reader-20261009` |
| `--source-receipt-sha256` | Exact nonzero SHA-256 of that completed receipt, independently checked by root before invocation |
| `--phase` | `PREMERGE_FROZEN_CANDIDATE` or `POSTMERGE_ACCEPTED_SOURCE`, matching the receipt |

A SHA-shaped accepted-merge argument is deliberately insufficient. The script takes the receipt's phase and Git observations as **principal evidence** and explicitly reports `github_merge_independently_verified_by_this_harness: false`. Its independent observations are source-byte equality, actual local reader behavior, immutable inputs and the guards. No phase grants fact, custody, rights, product or predictive authority.

### Common required receipt fields

This extends the existing delivery-receipt shape for the new operation; it is a verification artifact, not a new source/fact admission schema. Root must record real observations, not populate a success template.

| Field | Required meaning/value |
|---|---|
| `schema` | Phase-specific value below |
| `phase` | Same exact enum as CLI |
| `status` | `PASS`, supported by root's completed source verification |
| `repository` | `mastermindx-market-intelligence/macro` |
| `operation_id` | `gmi-economic-network-native-reader-20261009-pro-002` |
| `code_root` | `/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-network-native-reader-20261009-pro-002` |
| `working_tree_clean` | `true`, actually verified by root |
| `reviewed_head` | Exact frozen 40-character Git commit |
| `execution_workspace_head` | Same exact frozen reviewed commit |
| `verified_at` | Original offset timestamp of verification; cannot be in the future |
| `owned_file_count`, `owned_files` | Exact distinct owned-file inventory and count |
| `dependency_count`, `dependencies` | Exact distinct declared dependency inventory and count |
| `native_fact_admission`, `production_reader_custody`, `historical_system_replay`, `rights_admission`, `served_product_proof`, `predictive_authority` | All explicitly `false` |

Every inventory row needs a canonical safe relative `path`, exact current `sha256`, and the phase-specific equality field below set true by the actual verifier. Duplicate paths within a list are rejected; owned/dependency overlaps must have identical digests.

The required minimum is the previously verified **68 dependency paths plus `tests/test_sec_document_spine.py` and `tests/test_fundamental_forensics_attestation.py`**, totaling 70 unique paths. The full exact set is in `REQUIRED_PATHS` in the prepared script. Root may include additional actually verified owned/dependency files; all supplied rows will be checked. No current hash was inferred from the historical dependency list.

The new review-set worker's `relationship_candidates.py` bytes and additional test must receive root's final composed-source verification before they can support a replay receipt. This preparation does not review or freeze that concurrent source.

### Premerge form

- `schema`: `economic_network.frozen_source_candidate.v1`
- `phase`: `PREMERGE_FROZEN_CANDIDATE`
- Each owned row: `reviewed_workspace_equal: true`, supported by exact commit/workspace byte comparison.
- Each dependency row: `all_locations_equal: true`, meaning equality between the frozen reviewed commit and executing workspace in this phase.
- `accepted_merge_sha`, `fresh_upstream_sha`, `merged_at`: present and null.
- `upstream_contains_merge`: false.

A passing replay with this input remains a premerge frozen-candidate replay. It cannot support accepted-main, deployed, served-product or production-custody language.

### Postmerge form

- `schema`: `economic_network.accepted_source_delivery.v1`
- `phase`: `POSTMERGE_ACCEPTED_SOURCE`
- Each owned row: `all_four_locations_equal: true`, for reviewed commit, actual accepted merge, freshly fetched upstream and executing workspace.
- Each dependency row: `all_locations_equal: true`, for the same verified locations.
- `accepted_merge_sha`: actual merge commit recorded through the existing release path.
- `fresh_upstream_sha`: actual freshly fetched upstream commit.
- `upstream_contains_merge`: true, verified by root.
- `merged_at`: actual offset merge timestamp, at or before `verified_at`.
- `pr`: actual `https://github.com/mastermindx-market-intelligence/macro/pull/<number>` carrier.

The old #8667 delivery receipt is a historical example of the accepted-source inventory shape. It is not a current repaired-code receipt and lacks the new explicit operation/root/phase fields. The builder's six-file `source-verification.json` is likewise a source-delta ledger, not automatically this completed frozen-commit or accepted-upstream proof.

## Root execution gate

1. Finish and freeze the composed source, including the separately changing manual-review-set work if it is included in this operation. Complete the necessary independent source review and retain both earlier failed strict replay outcomes.
2. Verify the exact current source and dependency bytes against the actual frozen commit, or against all four accepted-source locations after merge. Produce the above receipt from those checks and verify its digest.
3. Review this prepared script and verify its exact digest before feeding those bytes to a fresh native Python `-B` process. Use a safe foreign working directory; do not import the fixture producer or prewarm dependencies in that process.
4. Explicitly authorize this independent replay against that receipt. Until then: no real invocation.
5. Preserve actual process exit, stdout and any failure as a new run. A later postmerge invocation needs the actual accepted-source receipt and separately dated result. Neither invocation rewrites capture provenance or the original failed run.

The script does not execute filing-package materialization, create a new store root, acquire a new source, use a latest pointer, publish source text, or prove all-host/network isolation. The narrow capability is exact retained NVIDIA candidate replay through the repaired native reader.

**Preparation complete. Real replay NOT_RUN.**
