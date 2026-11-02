# QLedger continuity: source-only compatibility plan

**Operation:** `rotation-risk-qledger-continuity-source-plan-20261009`  
**Status:** design only; every proposed implementation, recovery, and promotion action below is unexecuted.  
**Immutable source pin:** [`94a20f53cdb2d866d07089df50567f059bf1073e`](https://github.com/mastermindx-market-intelligence/macro/tree/94a20f53cdb2d866d07089df50567f059bf1073e).  
**Admission:** `UNKNOWN_NOT_EXPIRED`; prior failed effects remain `UNRECONCILED`. This design neither acquires custody nor establishes that incumbent writers are absent or drained.

The source supports extending the existing QLedger into a bounded native segmented representation while preserving one logical claims stream, its current ownership, and existing publication paths. A storage repair must preserve more than unique claim IDs: raw row order, intentional duplicate occurrences, caller-specific interpretation, grade links, issue clocks, and the existing fill-null rewrite all affect current behavior. Reader compatibility must ship before format activation. Lossless promotion additionally requires reconciliation of the unpublished failed-run tails and old writer versions; protected main alone cannot prove continuity.

This review examined 112 immutable source files. The companion JSON records exact paths, source blob identities, URLs, and relevant line hits. Indexed search was discovery, not proof of an exhaustive runtime or cross-repository census. No financial ledger body, host runtime, working-tree state, test, producer, migration, or refused diagnostic operation was accessed or executed.

## Existing source facts

| Native seam | Established behavior and implication |
|---|---|
| [`engine/qledger.py::register`](https://github.com/mastermindx-market-intelligence/macro/blob/94a20f53cdb2d866d07089df50567f059bf1073e/engine/qledger.py#L2026) | Preparation precedes the existing-ID lookup; registration returns the first matching existing claim. Only newly appended claims trigger control-clock starts. Keep these results and side effects. |
| [`register_batch`](https://github.com/mastermindx-market-intelligence/macro/blob/94a20f53cdb2d866d07089df50567f059bf1073e/engine/qledger.py#L2064) | Keeps first existing and first in-batch occurrences, preserves per-input result order and preparation-error slots, and supports `dedupe=False`. Storage migration must not re-register history. |
| [`_read_jsonl` / `load_claims`](https://github.com/mastermindx-market-intelligence/macro/blob/94a20f53cdb2d866d07089df50567f059bf1073e/engine/qledger.py#L2357) | Reads raw ordered rows, skips malformed legacy lines, and does not globally deduplicate. First-claim registration is not permission to deduplicate every reader. |
| [`backfill_regime_stamps`](https://github.com/mastermindx-market-intelligence/macro/blob/94a20f53cdb2d866d07089df50567f059bf1073e/engine/qledger.py#L2119) | Existing atomic whole-file rewrite fills only missing regime stamps from persisted historical vectors, protects non-null values, and writes `recomputed_history` provenance. The nightly maintenance exception is real; additive-only metadata is incomplete. |
| [`scripts/grade_qledger.py`](https://github.com/mastermindx-market-intelligence/macro/blob/94a20f53cdb2d866d07089df50567f059bf1073e/scripts/grade_qledger.py#L667) | Grades use `(claim_id, horizon_d)` keys and separate append storage, with existing clock/coverage decisions. Claims repair does not require changing grading equations or segmenting grades. |
| [`engine/qledger_evidence_clock.py`](https://github.com/mastermindx-market-intelligence/macro/blob/94a20f53cdb2d866d07089df50567f059bf1073e/engine/qledger_evidence_clock.py#L10) | Family starts are write-once; one file per family avoids whole-JSON writer races. Preserve existing IDs, timestamps, `check_by`, horizon units, market clocks, and grade links. |
| [`config/synapse.yml`](https://github.com/mastermindx-market-intelligence/macro/blob/94a20f53cdb2d866d07089df50567f059bf1073e/config/synapse.yml#L483) | Existing artifact is `qledger-claims`, producer `engine/qledger.py`, owner program `qualitative-intelligence`, daily-engine cadence, Git storage, context/shadow role, and no weights. Physical members must extend this artifact, not create another business authority. |
| [`.gitattributes`](https://github.com/mastermindx-market-intelligence/macro/blob/94a20f53cdb2d866d07089df50567f059bf1073e/.gitattributes#L23) | Claims and grades use `merge=union` to preserve separate-clone appends. It is neither same-workspace locking nor a global claim-deduplication guarantee. |

**Actual writers.** Direct registration entrypoints occur in US/CN/intel-hub backfills, placebo and importance-shadow samplers, White House and special-situations extraction, missing-tape, flip-confirmation, communique-diff, China special situations, source calls/flare states, basket-turn cohorts, and entry-radar reconciliation. Stock, thematic, and demand desks route through `engine/qledger_desk_adapter.py::register_prospective`. The companion inventory names their exact functions and pinned code. All should retain the current public registration APIs; desk-specific replacement stores are unnecessary. The linked #8042 batching work retains separate custody; this proposal adopts none of its unpublished changes.

**Direct reader compatibility scope.** These consumers bypass `load_claims` and therefore require deliberate adaptation; changing the central reader alone is insufficient.

| File / function | Compatibility requirement |
|---|---|
| `scripts/backfill_qledger_us.py::_thesis_ids_with_placebos` | Its emit-once guard must see the complete logical history, or it can emit duplicate placebos. |
| `engine/neuralweb/query.py::adapt_qledger` | Preserve grade joins and its stricter parsing/gap policy. |
| `engine/neuralweb/evidence_clock.py::_adapt_qledger` | Preserve desk rollups and explicit read-failure gaps. |
| `engine/qledger_falsifier.py::evaluate_falsifiers` | Preserve absence qualification and the existing evaluations output. |
| `engine/operator_grading.py::_load_claims` | Its dictionary comprehension selects the last occurrence. Preserve source order and this existing caller behavior. |
| `engine/metabolism/til_fitness.py::_read_live_leg_quality` | Continue joining QLedger claims with falsifier evaluations. |
| `scripts/audit_claim_accountability.py::run` | Read the whole logical stream with existing reporting semantics. |
| `scripts/audit_grading_closure.py::audit_entry` | Extend physical-source inventory without changing closure meaning. |
| `scripts/check_qledger_metric_validity.py::main` | Preserve its comment-aware and malformed-line policy. |
| `scripts/build_intelligence_registry.py::_load_qledger` / `read_tracked` | Preserve source diagnostics and sparse-checkout Git fallback, binding catalog and all parts to one coherent snapshot. |

The similarly named metabolism and marketing claims stores are separate and excluded. Existing consumers already using `load_claims`, including reporting and source-registry paths, should receive compatibility through that native API.

**Publication ownership.** Existing daily, Asia-close, White House sentinel, and backfill workflows can stage QLedger data; weekly broad data publication also requires size-guard consideration. `scripts/ci/daily_engine_commit_outputs.sh` stages the existing data/site/reports outputs and uses the shared `scripts/ci/push_retry.sh` rebase/push owner. The render workflow is not a QLedger writer. Preserve these lanes and their recovery ownership; no new scheduler, publishing service, or parallel data plane is proposed.

## Proposed native representation and protocol

The exact accepted published `claims.jsonl` becomes a byte-preserved base and integrity anchor. Bounded immutable continuation parts could live under `data/qledger/claims.parts/`. Their logical append-only catalog must also be bounded physically: a single ever-growing `claims.parts.jsonl` is not an acceptable implementation. Names and a proposed conservative 64 MiB data-part ceiling remain design choices requiring native publication-owner acceptance. Catalog descriptors contain storage transaction identities, ordered part references, hashes, byte/row counts, and revision references—not new business claims, grades, or evidence votes.

The proposed catalog representation uses immutable bounded leaf pages and bounded-fanout index pages, reached from a small fixed-shape root record. The root holds the format/base identity and one index-root reference, never an accumulating list of every part or page. Each page has explicit byte, entry-count, and descriptor-size limits; for design review, a 1 MiB metadata-page limit and maximum index fanout of 128 are provisional choices. A full leaf rolls to another leaf; a full index rolls or splits through copy-on-write ancestors. Only the affected index path and root change, while the logical descriptor sequence remains append-only and ordered. Revision records use the same bounded representation. An explicit supported depth/capacity limit must fail before mutation if exhausted; no oversized emergency root, page, or descriptor is allowed.

Rollover publication includes every new data part and metadata node before activating the new root in the same accepted Git tree. Readers pin that root and resolve all descendants from the same immutable tree or coherent local transaction snapshot. Missing or corrupt nodes, cycles, invalid depth, and a root pointing to an incomplete generation fail completeness. Existing publishers must enforce limits on every physical member—base, data parts, descriptors/pages, index nodes, and root—and on newly reachable blobs, not just the largest claims file. Final limits, rollover/recovery mechanics, and concurrent-root reconciliation are blocking source-design requirements before format activation; these provisional values are not an implemented or validated protocol.

The logical raw stream is the base followed by accepted append descriptors in published order. Retrying an identical storage transaction is idempotent. Identical business-row payloads intentionally emitted with `dedupe=False` remain distinct occurrences: storage occurrence identity must be separate from content hash. Do not sort or deduplicate by claim ID, issue date, or timestamp. Hashes identify integrity/revision, not business authority.

A private storage-only seam, optionally `engine/qledger_store.py`, should expose ordered raw lines plus a completeness/integrity receipt. `engine/qledger.py` remains the logical owner and retains public APIs. The absence of a catalog preserves exact legacy behavior. In the new format, missing or corrupt catalog members cannot silently become empty history. Each reader keeps its current parse, count, order, and absence policy, with explicit storage-integrity failure taking precedence over a false successful zero-count result.

The registry's sparse Git fallback needs a snapshot-aware source adapter: all catalog and part reads must resolve against one immutable Git tree or one coherent local transaction generation. It must not mix a working-tree catalog with unrelated `HEAD` parts. Descriptors must reject path escape, unexpected order, duplicate transaction conflicts, and mismatched base/part identities.

Registration retains preparation, first-existing lookup, in-batch behavior, error slots, statuses, return ordering, and clock hooks. Extend its read/deduplicate/append transaction over the logical stream. Either prove the incumbent single-writer guarantee for a local workspace or add a native local filesystem lock around this transaction; no distributed lease service is implied.

The regime backfill requires an explicit storage-native compare-and-replace exception. A rewrite transaction targets exact prior segment digests and row positions; replacement immutable parts occupy the same logical positions while retaining earlier raw bytes/history, including the base anchor. Only the already permitted null fills and provenance changes may differ. It must not generate new claim IDs or restamp clocks. Conflicting revisions fail or reconcile through the existing owner; they are not resolved by generic last-writer overwrite. Legacy whole-file behavior remains intact until activation.

Parts must be complete and durable before committed catalog references. Crash states—temporary or orphaned part, partial descriptor, missing referenced part, changed hash, stale base, incomplete batch or clock hook—must be distinguishable and preserved for existing recovery ownership. They must not trigger deletion, zero-history success, or unqualified replay.

## Lossless admission and mixed-version promotion

Before freezing any published prefix for a real cutover, the original publication/recovery owner must classify both failed-run tails and commits: already published, preserved unpublished, genuinely unrecoverable, or still unknown. Published main is not evidence that runner-only rows survived. Recoverable rows retain their original IDs and clocks; the repair must not recreate historical first issuance by calling registration. This plan provides no authority to retrieve denied captures, inspect stores, or repurpose refused audit material.

The rejected oversized blob may remain in unpublished ancestry. Splitting or deleting a file in a later commit does not remove that earlier object from the proposed push. Existing publishers therefore need staged/candidate and newly reachable blob guards. A literal GH001 rejection should be classified as nonretryable by unchanged push attempts; recovery must preserve the real suffix under the existing owner without force push, truncation, excluded history, or guessed clocks.

Reader-compatible source should be released first. Actual older writers must then be reconciled, drained, or fenced at activation through existing ownership. Adding a catalog does not make old executables safe: they may append or rewrite the frozen legacy file. No current drain or compatible fleet is established by this source review.

Separate-clone writers retain the existing Git publication plane. Logical catalog union alone is insufficient, and root/index files must not use blind line-union merging. Each rebase must validate immutable members against the exact remote tree, preserve the exact already-published logical descriptor prefix, then reconcile pending local transactions in their original order and rebuild the affected bounded index paths. Both append suffixes survive; conflicting rewrites stop for incumbent reconciliation. Timestamp sorting and whole-file `theirs` replacement are not substitutes. A same-ID/different-payload race must preserve raw occurrences and the existing first-registration interpretation rather than invent a global dedup rule. This proposal does not retroactively establish a global exactly-once or linearizable registration guarantee across independent clones: it preserves the current observed ordering and duplicate semantics. Storage-transaction retry identity is a narrower property, not a new business-level uniqueness promise.

## Bounded implementation sequence and tests

| Wave | Proposed source work | Required exit evidence |
|---|---|---|
| A | Pure compatible reader seam; all bypass readers; synthetic fixtures. No data output. | Independent source review and existing code CI; exact legacy and complete segmented reads. |
| B | Native registration/rewrite storage protocol and existing publisher guards; activation disabled. | Synthetic concurrency, interruption, rebase, and size-boundary tests; complete dependency gates. |
| C | Admitted owner reconciles failed effects, binds base/tails and compatible writers, and performs one native format cutover. | Actual preservation and ownership evidence. No unknown competing writer displaced and no denied operation reused. |
| D | Normal non-skipped daily plus other admitted writer lanes publish through existing owners. | Exact final accepted pushed SHA, source clocks, logical-reader and grade continuity. A gate-only green run or fixture pass cannot establish this. |

Proposed source scope is `engine/qledger.py`, an optional private storage module, the ten direct-reader paths above, and focused existing publication seams. Metadata/guard updates may include `config/synapse.yml`, `config/dag.yml`, the intelligence-registry overlay only if needed, registry/append-only checks, `.gitattributes`, and existing CI suite/dependency registration. Every edit requires fresh exact-path source custody; this list does not acquire it. No grading equations, risk-state math, unrelated claims stores, canonical data/site bodies, or held capture/validation paths are included.

The synthetic acceptance set must cover:

1. Legacy byte/row order, malformed-line policies, unknown fields, duplicates, first-existing/first-in-batch registration, rejected claims, error slots, and `dedupe=False` parity.
2. Unchanged IDs, grade links, issue/check clocks, horizons, market clock, provenance, and family-clock files; migration invokes no registration or clock start.
3. Two synthetic failed-run tails with overlapping base and distinct suffixes: complete reconciliation or explicit unknown, never fabricated first-issue receipts.
4. Separate-clone append/rebase races, same-ID different-payload occurrences, and preservation of the published prefix; incompatible rewrites fail while compatible append and fill-null maintenance preserve all rows.
5. Interruption at temporary part, seal, catalog, stage, commit, push, and clock-hook boundaries; retry idempotence belongs to storage transactions.
6. Missing, corrupt, hash-mismatched, reordered, path-escaping parts and partial catalogs; new-format completeness fails explicitly.
7. Legacy preactivation binaries retain behavior; postactivation old writers cannot publish a changed frozen base. Actual deployment fencing remains a separate runtime gate.
8. Sparse Git single-tree reads and caller-specific diagnostics; regime rewrite positional and field-level parity with history retained.
9. Oversized staged and newly reachable objects, including rejected ancestors, receive a nonretryable classification without unstaging history, truncation, or force push.
10. Grader, falsifier, operator, NeuralWeb, registry, and fitness output parity against synthetic legacy fixtures. Runtime promotion requires real owner/publication evidence beyond these fixtures.
11. Many one-row registration batches generate enough descriptors to cross multiple leaf-page and index-level boundaries. At each rollover, every physical member stays below its byte/count limit, the root stays fixed-shape, and raw order and duplicate occurrences are unchanged. Concurrent-clone rollover, interrupted index publication, missing/corrupt index pages, and supported-capacity exhaustion must fail or recover explicitly without losing the published prefix, mixing snapshots, or creating an unbounded fallback blob. The test must not claim global exactly-once or linearizable registration.

**Next action.** Root may commission bounded source-only reader/compatibility implementation in a disjoint admitted workspace after fresh exact-path custody checks. Data-format activation remains separately gated on the missing native claim binding, actual writer/version disposition, unresolved effects and failed tails, compatible publisher deployment, independent review, and accepted continuity evidence. The prior `UNKNOWN_NOT_EXPIRED` receipt and diagnostic-refusal distinction remain intact. This source-design operation ends here; it authorizes no migration, successor operation, or watcher.
