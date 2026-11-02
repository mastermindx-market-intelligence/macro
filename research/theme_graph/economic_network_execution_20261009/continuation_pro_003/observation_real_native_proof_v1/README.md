# Real retained-C01 private observation proof — prepared for principal execution

**Status: PREPARED, syntax-compiled only. No application import, test, store operation, native write, source acquisition or Git operation was run by this preparation lane.** The principal owns review, source reconciliation, native execution, outcome adjudication and durable delivery. This package is not a native PASS or release authorization.

The standalone [prove_retained_c01_observation.py](prove_retained_c01_observation.py) exercises the actual Company Intelligence observation APIs with the seven exact retained Micron inputs. It then reconstructs the observation in two fresh processes that receive only its store root, exact reference, verified code manifest and harness identity. It uses no synthetic candidate, test fixture, substitute inspector, storage factory, acquisition path or producer-supplied successful result.

## Principal inputs and invocation

The required code root is:

```text
/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-observations-20261009-pro-003
```

Both output locations must be new direct children of:

```text
/Users/chriswong/Library/Caches/Mastermind/economic-network-20261009
```

The store directory name and private receipt name must start with `c01-observation-`; the receipt must end in `.json`. Every existing path component must be a real directory. A pre-existing output or store, including a dangling symlink, fails before the append. There is no replace, cleanup, resume or automatic repair mode.

The principal first binds and reviews the actual source manifest, verifies the materialized harness bytes, selects unused private names, and records the authorized native parent process. The example below is a command template, not an action performed by this lane. Replace the two digest placeholders and actual manifest path with independently verified values.

```bash
/opt/homebrew/Caskroom/miniconda/base/bin/python3 -I -B \
  /Users/chriswong/Library/Caches/Mastermind/economic-network-20261009/prove_retained_c01_observation.py \
  --source-manifest /Users/chriswong/Library/Caches/Mastermind/economic-network-20261009/c01-observation-source-manifest.json \
  --source-manifest-sha256 ACTUAL_MANIFEST_SHA256 \
  --harness-sha256 ACTUAL_HARNESS_SHA256 \
  --store-root /Users/chriswong/Library/Caches/Mastermind/economic-network-20261009/c01-observation-pro-003-store-v1 \
  --private-output /Users/chriswong/Library/Caches/Mastermind/economic-network-20261009/c01-observation-pro-003-private-proof-v1.json
```

The parent prints one public JSON receipt containing metadata, digests, statuses, actual child PIDs and proof limits. It exits `0` only for a completed PASS, otherwise `2`. The private output is created exclusively with mode `0600` before any store operation. The incumbent `LocalStore` constructor creates the store leaf under a temporary process umask of `0077`, restored immediately; the resulting root must have no group/other permission bits. The seven original inputs and all reviewed code remain read-only.

Do not invoke hidden `--child` mode directly into a public log. Its complete JSON output, including full current/support results and review contents, belongs only in the parent's private pipe and receipt. Child stdin is a bounded closed request with exactly these six keys:

```text
source_manifest, source_manifest_sha256, harness_path,
harness_sha256, store_root, reference
```

The child request contains no source/candidate/review body, original-input location, precomputed inspection, parent fixture, test import, output path or factory selection. The fixed harness knows the public role/digest inventory and can deny an attempted original source read; it never opens an original evidence file in a child. Reading stored components is the intended source of all child inspection evidence.

## Exact source-manifest contract

[source_manifest.example.json](source_manifest.example.json) illustrates the closed schema and four hard pins. **It is intentionally not an executable manifest:** its reviewed-head placeholder is invalid, and the four rows alone omit the import closure. The principal must supply all needed initializers and transitive first-party Python sources, with actual lengths and SHA-256 values from the independently reviewed source set. Do not fabricate missing source rows or widen the boundary merely to make an import succeed.

| Field | Required value or interpretation |
|---|---|
| `schema` | `economic_network.observation_native_source_manifest/v1` |
| `repository` | `mastermindx-market-intelligence/macro` |
| `operation_id` | `gmi-economic-observations-20261009-pro-003` |
| `workspace` | Exact code root above |
| `reviewed_head` | Actual nonzero lowercase 40-hex reviewed commit; principal-attributed |
| `phase` | `PREMERGE_FROZEN_CANDIDATE` or `POSTMERGE_ACCEPTED_SOURCE` |
| `files` | 4–256 unique closed rows: `path`, `byte_length`, `sha256` |

Rows must be safe repository-relative `.py` paths under the existing `engine`, `lib`, `collectors`, `scripts`, `tests` or `config` roots. File lengths may include a legitimately empty initializer; each file is at most 4 MiB and the complete declared set is at most 32 MiB. Evidence JSON, HTML, YAML, caches, credentials and URLs do not belong in this code manifest. A declared code superset is allowed. Every actual first-party import must have a row; the exact observed compiled paths are reported separately. Declaring a test or collector file does not authorize its import.

All four hard pins must match:

| File | Bytes | SHA-256 |
|---|---:|---|
| `engine/company_intelligence/relationship_observations.py` | 42,756 | `85c07b309ff7b7220ec12f2b3f25c924a2ef4c9ab495ce9030f61038cbb9e8c7` |
| `engine/company_intelligence/relationship_candidates.py` | 45,473 | `a558922c0586a5532f3912524b48f3cf592c3c6c9c21f689e3d416976e9cae55` |
| `engine/research_vault/r2_store.py` | 47,498 | `7ba42eb8f74c034413997707a35156e67342fb9a30ca2b80dde0f11d1dc7e2bd` |
| `lib/dataos/registry.py` | 16,599 | `b57ec16a61086b8d35beb2f81af30efc4af55f1ac07ec95cfcfd87beefeef0a5` |

The assigned test identity is separately preserved as 49,406 bytes, SHA-256 `a73700e639c8e97a4ff84951b48358abe63b1f5048560d03b0e40f2310ac44da`. This harness does not import or execute that file. The supplied worktree head at assignment was `dfa8533b07f1f603ef9f9bb6fbf957e4b1c112a1`; it is not hardcoded as current or accepted. A later reviewed commit can be supplied without changing these frozen application pins.

The harness verifies source bytes and reports the manifest's reviewed-head/phase attribution. It does not run Git, inspect holds, certify a clean worktree or upstream containment, or infer source acceptance from a manifest label. Those checks remain principal-owned.

## Seven exact original inputs

The first two are fixed private cache paths. The remaining five are fixed repository-relative paths below `research/theme_graph/economic_network_execution_20261009/`.

| Role | Original file | Bytes | SHA-256 |
|---|---|---:|---|
| `source` | Cache: `micron-hbm3e-a7efabf9cec581ba684688368118e3e13df6a3043aff56667927e24df97e8b2e.html` | 504,119 | `a7efabf9cec581ba684688368118e3e13df6a3043aff56667927e24df97e8b2e` |
| `candidate` | Cache: `micron-manual-candidate.json` | 1,930 | `5e2a2c789599e5e146b6e2969ccc243ee5c85b7d74c67af76b7c437857c4383c` |
| `source_record` | `MICRON_SOURCE_CASE.json` | 1,588 | `dd72d31afce12ca727a171e6f635d7085c8c2d6bff6bea2750f9c29a04fe101b` |
| `pilot_adjudications` | `native_adoption_pilot_v1/case_adjudications.jsonl` | 23,612 | `039cfbfa04738612457e5ed04be4b20864c088103bb5a8309ff7839938830b25` |
| `semantic_review` | `native_adoption_pilot_v1/supporting_evidence/independent_semantic_judgments.json` | 10,309 | `4357ab18cd8dddafd944b30641bf4c9168f755e1da60059a6ee5d8ded9192652` |
| `retained_first_review` | `retained_micron_semantic_addendum_v1/first_reader_judgment.json` | 6,032 | `3a9ce686a0593f9731c89ef63c20afb92dce810681aa3d0039bd72ce0f4d6408` |
| `retained_independent_review` | `retained_micron_semantic_addendum_v1/principal_independent_judgment.json` | 3,732 | `96c5a97fd64a3c4330bba160310e5ade8babb211fd61d567fc5b119346837d9a` |

The parent preflight checks length, SHA-256, exact UTF-8 round trip, `lstat`, regular-file status, every parent directory and stable file identity across a descriptor-relative no-follow read. It retains a baseline of device, inode, size, mtime, ctime, mode and digest for all seven inputs, the code manifest, harness and every declared source file. It never compares access time, which ordinary reads may change.

## What a completed PASS must actually demonstrate

1. **Direct actual inspection.** Import the reviewed real modules through a source loader that re-reads and hashes each pinned `.py`, then compiles those exact bytes. Call the incumbent `inspect_candidate` directly for current, support-inclusive and historical requests. The entire canonical current inspection must hash to `6bbb39a463030c992760fb3309006f94bc10c37126894f0ae76a1288e46fb8b4`. No `.pyc` can satisfy a first-party import.
2. **One real append.** Construct the actual `LocalStore` at the new private root. Pass all seven original byte inputs to `append_relationship_observation`, with `case_id=C01`, `review_set_id=retained-micron-C01-observation-v1`, no predecessor and no registry. Require `COMMITTED`, the exact traced manifest reference, and complete equality to the direct current inspector. The harness does not calculate a replacement successful inspection or call the module's private preparation function.
3. **Actual persisted closure.** Independently read the exact content-addressed manifest and each declared chunk from the filesystem. Verify canonical encoding, all lengths and hashes, at most 1,048,576 package bytes, at most 64 chunks and at most 16,384 bytes per chunk and manifest. Reconstruct the complete package and compare each of its seven components byte-for-byte with the parent originals. The stored inspection must equal the entire direct actual inspector. Preserve the checked review scope and all unauthenticated provenance labels.
4. **Manifest last.** The traced proxy delegates only the incumbent capability check, exact-length bounded read and create-only conditional write APIs. Every write uses `expected_version=None`. Before the final manifest put, trace evidence must show successful reads of all manifest-declared chunks after the last chunk put. The manifest must be the final write. Denominators distinguish declared chunks from unique content-addressed chunks. The final file inventory is exactly the unique chunks, one manifest and the incumbent empty `.strict-conditional-write.lock`; no latest pointer, temporary file or unrelated object is accepted.
5. **Repeat without writes.** A second actual append with identical retained inputs must return `REPEATED` and the complete original output with only that status changed. It must perform no conditional write, no allowed filesystem mutation, and no change to the store snapshot, seven original files or code/proof inputs. The repeat executes under the read-only guard.
6. **Current, support and historical reads.** Call the actual reader three times and compare each complete nested inspection with its corresponding direct actual inspector. Current must report sealed-request equality. Support inclusion must report changed-request fresh computation and actually include the dedicated replayed support. Historical `as_of=2024-02-26T12:00:00Z` with a real `Registry([])` must report outer `ABSTAINED`, actual inner `REFUSED` / `AS_OF_DATASET_REQUIRED`, no current candidate view, no source provenance, no support, no review provenance and no prior-observation semantics.
7. **Two fresh store-only processes.** Spawn two separate `-I -B` processes with a minimal credential-free environment and explicit private pipes. Each independently verifies its code/harness manifest, installs guards before app import, and calls the real reader for current/support/history. It has no parent original byte buffers. Its one constructor `mkdir` attempt is allowed only for the already existing real root; all subsequent filesystem mutations are denied. Every child result must match the parent's complete results, and the complete child stdout bytes must be identical between the two distinct PIDs. Child timestamps and PIDs are intentionally kept outside that deterministic payload.
8. **Final immutability and private receipt.** Repeat the store and immutable-file snapshots after reads and children. Require no unexpected guard attempt and zero post-append mutations. Record each child termination status and PID. Write the complete private receipt through the one previously reserved descriptor, fsync, re-read it exactly, and publish only its path, byte count and digest with the public proof metadata.

The package's scope check retains the planned **24GB 8H HBM3E → NVIDIA H200 Tensor Core GPUs** assertion. It does not turn production commencement into completed H200 delivery or continuing bilateral commerce. The actual inspector's unknown legal-party IDs, shipments, revenue, economic weight and theme membership remain null. All outputs remain `NOT_ADMITTED`, Graph1 projection remains null, rank/gate/size/trade/prediction authority stays false, and source-purpose permission remains unestablished.

## Guard design and positive controls

The harness installs import and Python audit guards before any first-party import. It performs real named import attempts for 18 prohibited acquisition/test/client names, verifies each denial, verifies no prohibited module entered `sys.modules`, and uses a later finder to detect fallthrough. It separately attempts a real `socket.socket`, a forbidden file creation and an original-source file read. Each must fail at the guard before effects. A real permitted `urllib.parse` import and URL parse supplies the positive pure-import control. Expected controls remain separate from unexpected denials and are never cleared to manufacture PASS.

The ordinary Python filesystem guard attributes `os.open` calls to tracked directory descriptors, because the audit `open` event does not itself expose `dir_fd`. It tracks `dup`, closes, reads, writes, fsyncs and subprocess pipe descriptors. The append allowance is restricted to the current exact content-addressed key: its required parent directories, the incumbent lock, its create-only temporary file and the exact final publication path. Existing destination replacement is refused. It allows the incumbent lock/temp behavior and does not substitute a store implementation. Legacy read, list, existence, unbounded write and factory methods are not exposed by the proxy.

Parent application stdout/stderr is captured privately; any unexpected content fails the witness and the public receipt exposes only stream length/hash. Direct descriptor writes outside the active store/private-receipt/child-pipe scopes are denied. Child stdout/stderr is captured by the parent, never inherited by a public console. Runtime library reads are allowed under the interpreter installation; first-party files must be explicitly pinned. Parent original-file rechecks are allowed only in named harness snapshot phases, with the application idle. Fresh children have no such allowance.

The guard's `unique_permitted_file_open_paths_by_phase` counts deduplicated paths admitted by the pre-open audit callback. It is **not** a count of successful reads; an admitted open can still fail at the filesystem. The private receipt preserves those path/phase pairs for diagnosis. Actual store read success and object digest/length are independently recorded by the delegating proxy.

These controls are a witness over reviewed Python execution, not an adversarial operating-system sandbox. They do not establish cloud-provider equivalence, resistance to malicious native extensions, global machine immutability, reviewer authenticity or independent semantic truth. Those limits are carried into the public receipt.

## Failure, unknown effects and recovery boundary

The proxy captures the expected manifest reference from the actual append's first manifest lookup and again immediately before its final conditional put. A refused, unknown, changed or failed append never triggers another append in this harness. An `EFFECT_UNKNOWN`, failed readback, harness error after a modifying attempt, timeout or result mismatch produces a failure receipt with the captured expected reference and completed private evidence where available. A first successful commit followed by a later proof failure remains visible as that actual observed commit; the harness does not erase or overwrite it.

The two child processes have a 60-second communicate bound. The parent records their PIDs as soon as they are returned, kills/reaps a still-running owned child during cleanup, and records whether termination was reconciled. An unreconciled termination is a failure requiring principal reconciliation; it cannot be hidden by a success label. No child can append or invoke a factory.

**Do not blindly rerun the command after failure or unknown effect.** The new-root check intentionally blocks it. The principal must inspect the exact expected reference and private receipt through a separately authorized read-only reconciliation, decide what actually happened, and choose any subsequent action. This package supplies no repair command, automatic retry, reference substitution or cleanup operation.

## Preparation provenance and limits

The applied decision read for this task was `lanes/pro003_control/DEC-GMI-ECONOMIC-RELATIONSHIP-OBSERVATION-MATERIALIZATION.md`. The complete frozen observation source was read from `lanes/relationship_observations_v2/relationship_observations.py`; the complete incumbent inspector was available at `lanes/review_set_v4/relationship_candidates.py`. Existing public proof patterns and selected owner-test sections were read without importing or executing them.

One bounded native source-only read was necessary to inspect the incumbent store's actual descriptor/write primitives. **Native PID 51140 exited 0 and was reconciled.** At `2026-10-09T11:11:00.912206Z`, it read the 47,498-byte store file at the exact native root above and confirmed SHA-256 `7ba42eb8f74c034413997707a35156e67342fb9a30ca2b80dde0f11d1dc7e2bd`. It used only standard-library file reads, no application import, factory, tests, store action or Git. [incumbent_store_read.json](incumbent_store_read.json) preserves that source and its metadata. Its prep read proved the no-follow regular leaf and stable file state, not a complete parent-chain proof; the executable harness requires the stronger parent-chain checks at actual execution.

A separately delegated static reviewer checked the harness against the actual LocalStore source and observation API. The review found a pinned-code parent-directory allowance omission, which was repaired and re-read. It also corrected an audit field that overstated permitted open attempts as successful reads. No additional deterministic store/subprocess blocker was found in that bounded static review. The review used AST parsing only on an intermediate 61,484-byte revision (`5293b84f986d288031ea524860afa5def00147e1fcb76d393cb8f618818b7ccf`). Final edits added accurate labels, explicit child-PID cleanup records, private stdout/stderr capture and an immediate post-append unexpected-guard check; prohibited imports remain scoped to acquisition, network-client and test paths so ordinary runtime support imports are not needlessly excluded. The final identity and compile-only verification are in the preparation receipt and artifact manifest; do not attribute native execution or complete final-revision independent certification to the earlier review.

Registry source bytes were pinned from the principal's supplied identity but were not independently re-read by the static sub-reviewer. Actual `Registry([])`, transitive import closure, platform audit event behavior, current digest, repeat result, persisted package, fresh-process results and immutable snapshots remain to be verified by the principal's real execution. No synthetic runtime exercise was substituted for that proof. No native process remains pending in this preparation lane.

The principal should save the harness, usage, manifest and sanitized execution receipt through the already authorized repository-backed paths. Full original source bodies, persisted package and full runtime outputs remain only in the authorized private cache/store. This package changes no accepted application source, frozen CI report, release rule, ownership map, rights state, production dataset, historical eligibility or predictive authority.
