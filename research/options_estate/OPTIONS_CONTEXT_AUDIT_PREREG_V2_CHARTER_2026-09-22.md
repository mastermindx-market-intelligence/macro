# Options Context Audit preregistration v2 charter

Status: `CHARTER ACCEPTED FOR IMPLEMENTATION PLANNING / IMPLEMENTATION HELD`
Workstream: `WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2`
Mission: design a complete-population successor to the byte-pinned v1 context audit. This packet freezes the implementation boundary and acceptance contract; it does not implement or activate v2.

## Exact source and incumbent boundaries

This packet was designed against Macro `origin/main` at:

`dea0a794ac63df21d5dcdceef90b427de0f6b62a`

The source identity was refreshed after the initial charter commit. The v1 and adjacent artifact byte hashes and row counts were re-read at this head; the h60 digest above is corrected to its full 64-hex value. No implementation claim follows from this refresh.

The protected Mastermind procedure used for the commissioning and review boundary was Skillpack commit:

`0471cea4f891da1ec0c9fbeff10a9391f9cdd90f`

The Skillpack index at that commit is `mastermind.sol_skillpack.v1`, version `1.0.1`, minimum bootstrap major `1`. The v1 context validator remains byte-pinned. Its `_MAX_REFERENCES` is still `4_096`; the independent auditor retains its historical unpinned `25_000` row / `48 MiB` read ceiling; the service remains `TimeoutStartSec=180` and `CPUQuota=50%`.

PR #6691 remains the incumbent records-only carrier at head `8b4136575be759a53c9f6fe7d7d104cc9c2af572`. It is open, non-draft, unstable, and has no submitted review. This packet does not edit its files, replace it, or duplicate its owner correction.

No implementation PR, shadow validator, second audit authority, trusted-context recoupling, owner eviction, window, truncation, timeout increase, CPU increase, or v1 byte change is authorized by this packet.

## Current corpus census

The census was performed from immutable blobs at the exact Macro source SHA above. These are measurements, not a future growth forecast.

| v1 input or adjacent artifact | rows | bytes | SHA-256 | v1 treatment |
|---|---:|---:|---|---|
| `data/options_signal_episode/episodes.jsonl` | 9,641 | 15,013,207 | `20120ddeff5983248ec404afaa65d3414c36ed1011936638c84e4ada52f50940` | consumed |
| `data/options_signal_episode/outcomes_h60.jsonl` | 7,843 | 15,886,486 | `18fb5dd5deb5114b1d55778eb6c3a4632207d58fa0aead63154653b4f7d7d67e` | consumed |
| `data/options_signal_episode/campaigns.jsonl` | 8 | 10,492 | `db326f5c772ab417c43b8579ad50abb0434916922bda3a13c2da5b8303813910` | frozen legacy campaign input |
| `config/market_memory_canary.v1.json` | — | 1,650 | `5e7823e48866b2c0828122b65f684ed5872c6816a6224f61e44db4c03d129b33` | consumed |
| `data/options_signal_episode/outcomes_session.jsonl` | 30,327 | 100,471,221 | measured, not bound here | adjacent artifact; explicit exclusion required |
| `data/options_signal_campaign/campaigns.jsonl` | 8,385 | 17,571,990 | `0c242957703d4a3a0031f0bf7322195c6d41f665391380e30626aea31bf95514` | separate campaign-v2 selector artifact; not a v1 context source |

The v1 context audit therefore sees approximately 29.48 MiB of source bytes and approximately 9,649 owner references (9,641 episode owners plus eight frozen campaign owners), already 2.36 times the pinned 4,096-reference ceiling. The old handoff measurement of 3,897 episode rows is stale.

The corpus is bursty: episode `available_at` spans 15 calendar days with a maximum daily burst of 2,197 rows; h60 computation spans 12 days with a maximum daily burst of 1,853 rows. A linear forecast from this snapshot is not defensible. Resource limits must be established by a bounded benchmark and a stated growth envelope.

The two campaign paths are semantically distinct. The legacy eight-row path is frozen and consumed by v1. The larger `data/options_signal_campaign/campaigns.jsonl` path is used by the v2 selector machinery. Its companion `data/options_signal_campaign/outcomes.jsonl` is also an adjacent owner ledger (28,423 rows / 67,324,077 bytes) and is not in the v1 source set. A v2 audit must carry a same-snapshot source manifest that explicitly classifies every owner-producing artifact as consumed, superseded, or excluded with a reason and contract reference. It may not silently omit either live campaign-v2 artifact or silently merge them into the legacy path.

### Frozen source-manifest decision

The v2 context-audit owner population is the complete set of episode owners plus the context references reachable from the registered campaign contract. `data/options_signal_episode/episodes.jsonl` is the owner ledger; `data/options_signal_episode/campaigns.jsonl` is the frozen legacy campaign reference ledger. `data/options_signal_episode/outcomes_h60.jsonl` and `config/market_memory_canary.v1.json` are consumed dependency artifacts.

`data/options_signal_campaign/campaigns.jsonl`, `data/options_signal_campaign/outcomes.jsonl`, `data/options_signal_episode/outcomes_session.jsonl`, and `data/options_signal_campaign/checkpoint.json` are adjacent derivation/dependency artifacts, not independent context owners. They must nevertheless be included in the immutable source-generation manifest with path, digest, bytes, rows, checkpoint identity, and an explicit exclusion reason. Any change to one of these excluded inputs between the bound source snapshot and validation forces a new generation or a typed refusal; an excluded artifact may never mutate silently while the audit reports healthy. The live campaign-v2 path is therefore not silently enumerated as complete and is not silently merged with the frozen legacy path.

The current live campaign output is stale: its durable checkpoint binds an 8,872-row episode prefix while the episode ledger contains 9,641 rows, its campaign writer commit predates the latest episode writer by four days, and 769 current episodes have no campaign member. The v2 audit must return `CAMPAIGN_OUTPUT_STALE` / `DERIVATION_PENDING` for that state rather than re-deriving campaigns or manufacturing owner coverage.

## Existing algorithm and measured lower bound

The current v1 path performs these stages:

1. Read complete JSONL ledgers and the canary configuration.
2. Decode and validate every episode and outcome row.
3. Authenticate the frozen eight-row legacy campaign ledger.
4. Resolve episode and campaign context references.
5. Sort references by owner schema and owner identifier.
6. Canonicalize JSON with stable key ordering, hash the reference set, and write immutable reference-set and audit objects followed by an atomic receipt HEAD.

Measured local timings over the current source snapshot were approximately 0.034 seconds to parse the legacy campaign ledger, 0.796 seconds to parse episodes, 0.840 seconds to parse h60 outcomes, 1.972 seconds for episode contract validation, and 13.478 seconds for campaign replay. The full context-store resolution and final receipt timing were not measurable because the W1A/trusted context stores are not present in the sparse checkout.

A complete-population audit has a hard lower bound of Ω(N) input work and Ω(bytes) hashing work. Every governed row and every bound source artifact must be read, parsed, identity-checked, clock-checked, and authenticated. An index-only or sampled path cannot prove completeness. The v2 objective is bounded memory and truthful I/O, not sublinear full-corpus work.

The current campaign replay is itself a refusal input: it derives 110 campaigns with seven pending from the current episode/outcome corpus and does not equal the frozen eight-row legacy ledger. The live campaign checkpoint binds only an 8,872-row episode prefix while the episode ledger has 9,641 rows; 769 episodes therefore have no campaign member, and the latest campaign formation (2026-09-03) trails the latest episode (2026-09-04). v2 must bind a same-snapshot checkpoint and preserve missing/latest-prefix rows as a typed source/replay refusal until a separately accepted campaign contract resolves them; it must not silently rewrite the legacy ledger or treat replay equality as a best-effort warning.

Current append writers provide canonical-byte idempotency and reject conflicting IDs or semantic keys under an inode lock and fsync. They do not provide correction or revision lineage. That missing lineage is a v2 contract requirement.

## Chosen v2 construction strategy

The implementation child must use bounded streaming with deterministic external-memory canonicalization:

1. **Freeze the source snapshot.** Record source commit/ref, exact path manifest, source device/inode identity where available, byte size, row count, source hash, required append-prefix hash, freshness clock, generation, and the future NYSE session boundary before reading.
2. **Enumerate without sampling.** Enumerate every source path declared by the governed source manifest. For each path, either consume it or emit an explicit contract-backed exclusion. Missing, unexpected, or unclassified owner sources fail closed.
3. **Stream each input once.** Parse JSONL in bounded chunks while computing the full source hash, validating schema, clocks, identity and append-prefix invariants. The scanner must detect shrink, reorder, backdated insertion, in-place mutation, malformed rows, duplicate semantic keys, and source drift between start and end.
4. **Emit bounded sorted runs.** Write content-addressed temporary runs keyed by canonical owner/group key with stable tie-breakers `(available_at, episode_id, source_row)` or the exact schema-defined equivalent. Run metadata includes digest, row count, byte count, ordering identifier, and source generation.
5. **Deterministically merge.** Perform a k-way merge with stable run-digest/path tie-breaking. Reject duplicate semantic owners with conflicting payloads. Validate one-to-one source/reference counts and exact legacy/v2 owner joins during the merge.
6. **Stream the final set.** Emit canonical reference bytes in the frozen owner order, compute the complete reference-set hash, and write the receipt only after all validation passes. Publish the receipt atomically; no partial receipt or health claim is valid.

If a source is proven append-ordered by a checked invariant, a one-pass fast path may avoid external sorting. The same invariant must be verified on every run; otherwise the implementation must use the external merge path or refuse. The fast path is an optimization, not a separate authority.

The strategy costs O(N) input and output I/O and O(N log N) comparisons in the external-sort path. Peak memory is bounded by the configured run chunk. Temporary disk is bounded by the run manifest and high-water limit. No row, owner, correction, or source may be evicted to satisfy those limits.

## v2 receipt and schema contract

The new v2 schema, builder, and receipt are a new preregistration triad. v1 remains byte-frozen and independent. The receipt must bind:

- schema and preregistration version;
- operation ID and immutable source commit/ref;
- future NYSE session boundary and freshness policy;
- complete source manifest, including consumed and explicitly excluded artifacts;
- per-artifact path, digest, byte count, record count, generation, and prefix digest where required;
- canonical owner/reference ordering identifier;
- algorithm identifier and source parser/validator contract digests;
- run manifest with run digests, run count, rows, bytes, ordering and temporary-disk high-water;
- observed peak RSS, CPU seconds, wall seconds, input/output bytes, and receipt bytes;
- reference-set digest and canonical count;
- correction/replay lineage (`supersedes`, old/new source hashes, and generation IDs);
- typed refusal code when no receipt is emitted.

The future NYSE boundary resets the forward cohort. Rows before that boundary are retrospective or abstain according to the frozen contract; delayed observation cannot make them prospective. A rule, source, validator, or schema change requires a new version and a new forward cohort.

## Corrections, replay, and session boundary

A successful receipt is immutable. A correction that changes already committed source bytes creates a new generation with an explicit supersedes link and exact old/new hashes; it never overwrites the old receipt. A backdated insertion, source shrink, reorder, prefix mismatch, conflicting duplicate, or source mutation during a scan discards uncommitted runs and returns a typed refusal.

A crash before receipt commit may replay the same operation against the same immutable source snapshot. The replay must produce byte-identical runs, reference bytes, and receipt content. A changed source or changed operation/session identity is a new generation, not a retry of the old effect.

The implementation must define the freshness clock, stale-source policy, session-start and session-end checks, and the exact relationship between the source generation and the future NYSE boundary before implementation begins. The boundary rule is frozen as: the first NYSE session open after the complete v2 schema, builder, validator, receipt triad, and its exact source-generation contract are accepted on `origin/main`; no row may be backdated into that cohort.

A cross-file snapshot is mandatory. Stable-read checks on individual files are insufficient: the implementation must bind one source generation/checkpoint across episodes, outcomes, campaign ledgers, campaign outcomes, and canary/config inputs, then refuse if any file or checkpoint moves between reads.

## Resource envelope and refusal contract

The implementation child must benchmark the current 9,641/7,843 corpus and a declared growth envelope before freezing numeric limits. The benchmark must measure at least:

- input rows and bytes per source;
- JSON parse and validation CPU seconds;
- reference construction CPU seconds;
- sorting/merge CPU seconds and run count;
- peak RSS;
- temporary-disk high-water and available-space floor;
- canonical reference-set bytes, audit bytes, receipt bytes and HEAD bytes;
- wall time under the actual service class.

Limits must include measured headroom and separate row and byte ceilings for episodes and h60. The historical eight-megabyte h60 ceiling cannot be reused blindly because the current h60 artifact is already approximately 15.9 MB. Numeric limits are implementation acceptance inputs, not chosen in this charter without the missing benchmark.

The implementation must fail closed, emit no receipt, and leave no accepted health claim on:

- incomplete or unclassified owner population;
- missing, malformed, stale, mutated, reordered, shrunk, or hash-mismatched source;
- legacy/v2 campaign contract mismatch;
- duplicate semantic owner or conflicting duplicate;
- source/reference count mismatch;
- nondeterministic run or merge output;
- context-generation or source-prefix drift;
- correction without a new generation;
- RSS, CPU, wall-time, input-byte, output-byte, or temporary-disk limit breach;
- receipt/reference-set/HEAD size overflow;
- replay that is not byte-identical.

Refusal codes must be machine-readable, stable, and included in the implementation acceptance tests. Failures must not be swallowed, windowed, sampled, truncated, evicted, or converted into a healthy empty result.
The initial refusal vocabulary is frozen: `SOURCE_MANIFEST_INCOMPLETE`, `SOURCE_SNAPSHOT_UNSTABLE`, `SOURCE_MUTATED`, `MALFORMED_ROW`, `PREFIX_MISMATCH`, `CHECKPOINT_STALE`, `CAMPAIGN_OUTPUT_STALE`, `DERIVATION_PENDING`, `CAMPAIGN_REPLAY_MISMATCH`, `OWNER_MISSING`, `DUPLICATE_OWNER_CONFLICT`, `CORRECTION_LINEAGE_MISSING`, `DEPENDENCY_MISMATCH`, `BOUNDARY_INVALID`, `NONDETERMINISTIC_OUTPUT`, `REPLAY_MISMATCH`, `RESOURCE_LIMIT`, `RECEIPT_OVERFLOW`, and `AUTHORITY_VIOLATION`. Each refusal records the operation ID, source-generation ID, per-source digests/counts, checkpoint IDs, and the first failing stage.

## Acceptance tests for the implementation child

The later implementation PR is acceptable only when an independent reviewer can verify all of the following against its exact source head:

1. **Complete-population coverage:** the source manifest names every governed owner artifact; every current owner row is represented exactly once or is accompanied by a contract-backed abstain/refusal reason; the live campaign-v2 path and the legacy campaign path cannot be silently conflated.
2. **Anti-vacuity:** nonempty current fixtures exercise the path; an empty result is accepted only when the manifest and source census prove an empty governed population; removing one owner or one source makes the coverage test fail.
3. **Determinism:** input reorder, chunk-size changes, run partition changes, and repeated replay produce identical canonical references, set hash, and receipt bytes; same-byte duplicates are idempotent and conflicting duplicates refuse.
4. **Correction safety:** append correction creates a new generation and preserves the prior receipt; backdated insertion, shrink, reorder, prefix mutation, and in-place edit refuse without publishing a partial receipt.
5. **Freshness/session law:** pre-boundary rows cannot enter the forward cohort; stale or drifted source refuses; source start/end identity and hash checks are enforced.
6. **Resource truth:** benchmark receipts include measured RSS, CPU, wall, I/O, run and disk high-water; limits are enforced under a current-corpus and growth-envelope fixture; exceeding any limit refuses without truncation.
7. **Authority isolation:** v1 files and bytes remain unchanged; no shadow validator or second audit authority exists; trusted-context publication remains decoupled; all authority, scoring, ranking, selection, execution, trade, and publication flags remain false.
8. **Receipt integrity:** reference, audit, receipt, and HEAD schemas validate; hashes and counts reconcile; atomic publication occurs only after final validation; no failed run leaves a misleading healthy receipt.

## Independent review findings and open gates

The measurement and strategy lanes agree that the stale 3,897-row and 25,000-row/48-MiB assumptions cannot be used as current capacity proof. The complete-population algorithm is bounded only by streaming/external-memory construction; the full input scan remains linear.

A disposable benchmark over the current v1 inputs (9,641 episodes, 7,843 h60 rows, eight legacy campaigns, and canary config) produced: streaming parse/hash `0.186 s`; all-at-once JSON materialization `0.231 s`; 1,000-row external sorted-run prototype `0.663 s`, 18 runs, 30,910,185 run bytes; peak RSS `274,907,136` bytes as reported by macOS `ru_maxrss`. This is a sizing receipt for the current host and source snapshot, not a production limit: it excludes live context-store resolution, final receipt serialization, and the adjacent campaign-v2 ledgers. The implementation child must repeat the benchmark with those inputs and a declared growth envelope before freezing numeric limits.

The independent adversarial review added these make-or-break requirements: cross-file snapshot mutation tests; stale checkpoint and missing latest-prefix refusal; explicit inclusion/exclusion of campaign-v2 ledgers and `outcomes_session.jsonl`; correction lineage or explicit refusal; deterministic replay under shuffled maps, chunk sizes, run partitions, and interrupted writes; and resource tests beyond the historical 25k/48 MiB assumptions.

The charter decision is now frozen for implementation planning. The bounded benchmark, adversarial review, source-manifest classification, stale-campaign refusal, correction/replay requirements, deterministic session rule, anti-vacuity tests, and refusal vocabulary are part of the implementation contract. Numeric production limits remain a mandatory implementation precondition: the implementation child must attach a benchmark receipt covering the current corpus, campaign/session growth, context-store resolution, and the declared growth envelope before code limits are accepted.

The implementation child is therefore separately admitted and remains held. This packet does not claim v2 implementation, merge, installation, deployment, production proof, or live acceptance.
