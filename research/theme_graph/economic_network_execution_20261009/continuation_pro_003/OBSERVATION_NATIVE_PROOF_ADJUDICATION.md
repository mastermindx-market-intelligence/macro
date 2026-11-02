# Private relationship observation: principal native-proof adjudication

**2026-10-09, 11:36 UTC — PREMERGE NATIVE PASS; hosted CI and normal release remain pending.**

The principal executed the real observation append/read implementation at committed and pushed source `6b58f15adae3b1d402d9993c52609d00083f1453`. All seven retained C01 inputs survived storage byte-for-byte. A repeat performed no writes, the actual reader reproduced the complete current inspector result, and two distinct fresh processes returned identical complete output bytes. A historical request with an actual empty `Registry([])` abstained with `AS_OF_DATASET_REQUIRED`. These observations satisfy the bounded private-store witness in the [applied decision](../../../../agentos/decisions/DEC-GMI-ECONOMIC-RELATIONSHIP-OBSERVATION-MATERIALIZATION.md). They do not admit a native relationship dataset or confer production or predictive authority.

## Source and independent review

The [principal source reconciliation](native_validation/c01-source-reconciliation-premerge-001.json) compared all 53 declared first-party Python files against both materialized files and exact committed Git bytes. All matched. The worktree was clean, with no ignored paths, before and after the proof. The [source manifest](native_validation/c01-observation-source-premerge-001.json) has SHA-256 `e955ec0f462369f42b0d3689360682d1a30dcbcea63bf090d935db73b2c9d293`. It is a permitted superset; the guard observed 19 first-party files actually compiled from verified bytes. No first-party `.pyc` satisfied an import.

The observation source is 42,756 bytes, SHA-256 `85c07b309ff7b7220ec12f2b3f25c924a2ef4c9ab495ce9030f61038cbb9e8c7`. The module, test and CI owner changes were already independently reviewed; the [v1 findings](observation_implementation/review_v1/REVIEW.md), [v2 corrective review](observation_implementation/review_v2/CORRECTIVE_REVIEW.md) and [CI enrollment review](ci_enrollment_review_v1/REVIEW.md) are retained separately. V1's three P2 findings remain visible alongside their closure.

The [frozen harness](observation_real_native_proof_v1/prove_retained_c01_observation.py) is 62,960 bytes, SHA-256 `871b539f94fb3b55de9c12e11fadd78c99920ea034503e755eb6bb7f1ea57b74`. The principal read the entire final source. A [separate final source review](observation_real_native_proof_review_v1/final_source_review.json) checked the consequential final guard, stdio and subprocess changes against the incumbent adapter. That review is a bounded static result, distinct from the actual native execution below. Its precursor preparation package accurately retains `PREPARED` / `NOT_RUN` labels for work the preparation lane itself did not execute.

## Observed real execution

The [execution receipt](native_validation/c01-observation-premerge-execution-001.json) records wrapper PID 19227, harness PID 19244, and execution from `2026-10-09T11:34:41.662963Z` to `2026-10-09T11:34:49.929352Z`. Both completed with exit 0. Harness stderr and captured application stdout/stderr were empty. The [complete public proof](native_validation/c01-observation-premerge-public-001.json) is 8,373 bytes, SHA-256 `85aca2ac1e822349b287b0ac54b2e5d94513d4cd97c70ce0e5d5908d1bb108e9`.

| Requirement | Actual result |
|---|---|
| Exact retained components | 7/7 reconstructed bytes equal the originals, including the retained HTML, candidate, source record, pilot adjudications, web semantic judgments and both retained-byte judgments |
| New private append | `COMMITTED`, `COMMITTED_OBSERVED`, complete closure verified |
| Package | 580,751 bytes; SHA-256 `345b7259d9de4461eb60ccd82c663b46851af09fd5a9211e51076cfb546fb91c` |
| Bounded objects | 36 unique chunks, largest 16,384 bytes; one 3,770-byte manifest |
| Publication order | 37 create-only conditional writes; all chunks read back before the final manifest put |
| Exact inventory | 38 regular files: 36 chunks, one manifest, one incumbent empty lock; no latest pointer or leftover temporary file |
| Identical repeat | `REPEATED`, complete result equal except status; zero conditional writes or store mutation |
| Actual reader | Current, support-inclusive and historical nested inspections each equal the corresponding complete direct inspector result |
| Historical request | Outer `ABSTAINED`, inner `REFUSED` / `AS_OF_DATASET_REQUIRED`; no saved current view, source provenance, support, review provenance or predecessor semantics released |
| Two fresh processes | PIDs 19331 and 19410, both exit 0, both reconciled; each complete output 87,563 bytes and byte-identical |
| Fresh output identity | SHA-256 `ccb6394c940366386e220b702bf4fc96cd13d64719ed638f559db89ea7b100e6` |
| Immutability | Original inputs, code, harness and manifest unchanged; store bytes and metadata unchanged throughout repeat/read/child phases |
| Guard evidence | 21 actual intentional import/network/read/write denials separated from zero unexpected attempts; no factory, test fixture or acquisition import |

The exact returned reference is:

```json
{"byte_length":3770,"schema":"company_intelligence.relationship_observation_reference/v1","sha256":"3ba9795892a3a1340bc9f8a100551c36dce1fb40fa43946f9ba2aeb62ce8f7d0"}
```

The complete canonical current inspector remains `6bbb39a463030c992760fb3309006f94bc10c37126894f0ae76a1288e46fb8b4`; support-inclusive and historical digests are in the public receipt. The 542,999-byte complete private receipt was created exclusively, fsynced and verified by exact readback, SHA-256 `af1d2117ee18f38de30376b149898c7704b8c844c44cf3ca0570d1c698b0f284`. Its contents and the persisted source package remain in the authorized private cache. This repository contains public proof metadata and code, not those private bodies.

## Scientific and product meaning

The accepted observation is a replayable source-bound record of the narrow planned **24GB 8H HBM3E → NVIDIA H200 Tensor Core GPUs** assertion. The original case's configuration, lifecycle and date precision remain explicit. It supplies no completed-delivery inference, current continuing supplier claim, exclusivity, shipment or revenue quantity, edge weight, theme membership or canonical legal-party identity. The hashes bind bytes; they do not authenticate reviewer identity, review independence, source custody, semantic truth or licensing.

This implementation resolves an evidence-preservation dependency: later readers can reconstruct the reviewed observation without the original seven files being available to their application process. Each reader still invokes the actual inspector on the stored components. A changed historical request is recomputed and can refuse; a saved positive cannot become historical knowledge merely because it was persisted.

The witness uses the incumbent `LocalStore` through injected exact-length bounded reads and strict conditional writes. It does not establish R2/cloud-provider equivalence, service deployment, an operating-system sandbox or cross-platform determinism. The two child processes share the same Python installation and verified code. Child stdout bounds are checked after `communicate`; no hard streaming-memory cap is claimed by the harness review. Permitted-open-path counters count pre-open audit admission, not successful file reads. These limits are retained explicitly.

## Validation and remaining release work

The four native application suites passed **275 tests**. The run's eight warnings concern pytest cleanup of pre-existing temporary browser-test garbage; those warnings remain in the saved log and were not repaired or hidden. Five targeted native CI contract tests passed, including the actual manifest's scope coverage and curated import closure. AgentOS validation reported **1,593 records, zero errors and 143 existing warnings**. See [the 11:20 execution checkpoint](EXECUTION_CHECKPOINT_20261009_1120.md) and its exact native logs for the earlier source/application/test receipts.

Only the new observation module/test and its existing Company Intelligence CI enrollment change runtime scope. Existing adapter, registry, theme, propagation, neural graph, K3-D, F04, source-owner and publication contracts retain their owners. No new dataset row, capture job, latest pointer, factory, cloud credential path or public product surface is introduced.

Next release steps are to preserve this exact proof, submit the normal PR, inspect concluded hosted CI and owner-path evidence, reconcile current protected procedures and integration source, and merge only through the ordinary permitted route. A postmerge accepted-source check and a fresh-store witness must bind the accepted code. No premerge label in this document should be read as a merge or production acceptance claim.

The broader source diagnostic remains unfinished. The [measured frame audit](source_diagnostic_frame_v1/WP02_SAMPLING_FRAME_ASSESSMENT.md) found missing historical identity, listing and cap evidence, so no 120-issuer cohort was selected. The [independent policy review](source_diagnostic_policy_review_v1/METHOD_REVIEW.md) identifies two P2 corrections: a historical roster completeness receipt and explicit conflicts versus proved revisions for cap components. A versioned correction is underway; v1 is not adopted. Frame feasibility, permitted source use and subsequent empirical/predictive gates remain evidence requirements in the accepted masterplan.
