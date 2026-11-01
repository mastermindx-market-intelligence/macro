# WP02 independent output-bound review

## Verdict

**REACHED REFUSAL — the corrected public API enforces the whole-output byte limit on the independently constructed escaped-ID witness. No application defect is indicated by this bounded investigation.**

The third and final authorized `diagnose` call supplied exactly 2,097,152 bytes and returned `model_state: OUTPUT_REFUSED`, `receipt_structure_state: OUTPUT_BUDGET_REFUSAL`, and `OUTPUT_BYTE_LIMIT` at scope `output`. The complete actual response is 3,300 bytes, with SHA-256 `92ed605dc8d74f562eb59c89eaf3dced6930c1645d2a22c4528c68b19bff4e09`. `synthetic` is null; the real-source authority, rights and history holds remain present; every real-input result remains null; admission remains `NOT_ADMITTED`; every other authority flag remains false. There was no unexpected exception or named effect-guard event.

This packet adds **three actual public-API calls**: one ordinary control, one dense printable-ID construction, and one escaped-ID construction. The initial two calls did not reach output refusal. Their original plans, exact requests, complete results and receipts remain unchanged. The principal separately reopened one additional call after the escaped-wire construction made output expansion concrete. That call reached the intended public branch. No old suite, private kernel helper, altered constant, serializer mock or application source edit was used.

This is scratch verification of the exact corrected source. It does not assert native execution, Git release, real-source readiness, an eligible issuer population, a lawful historical frame, or financial predictive validity.

## Exact code and method binding

All paths below are relative to `/workspace/scratch/9fd3d58c239a`.

| Subject | Path | Bytes | SHA-256 |
|---|---|---:|---|
| Corrected public kernel | `lanes/source_diagnostic_kernel_v2/source_diagnostic.py` | 77,602 | `f9814c8e65a155ae8273b4127661b5568e97a45c135b679f1db2eb84f36afdb6` |
| Corrected input contract | `lanes/source_diagnostic_kernel_v2/INPUT_CONTRACT.md` | 19,420 | `2806f32cd4367a4b9d6974ccea6ceaa2f2649794c35d256f0b6c5ccae781d0b5` |
| Adopted v2 policy bytes | `lanes/source_diagnostic_policy_v2/RECOMMENDED_SELECTION_POLICY.json` | 60,312 | `d41422d76219b1c5d3a3c9cbb19a1bc3124433031200b09499033bd4dc30d522` |
| Principal adoption bytes | `lanes/source_diagnostic_policy_adoption_v1/POLICY_ADOPTION.json` | 9,593 | `645a20a39842d9c5a03b4ff39a37280d1aa02c32ef545c061d0aa959f06e0016` |

The effective policy content identity remains `90bec6078348af6e41c9538e12e0443dd37d671c85a7089c64c547f5ce5e7714`. D is 2026-09-30, K is 2026-10-09T00:00:00Z, and the fixed seed is `GMI-WP02-20261009-v1`. No date, seed, quota or method byte was changed for this test.

Source inspection located the output accounting in `canonical_bytes`, the refusal envelope in `_finish`, and the actual public path in `diagnose`. The caller used only `diagnose(request_bytes, *, policy_bytes, adoption_bytes)`. A reviewer-owned standard-library JSON encoder serialized the returned dictionary for exact result retention. The application serializer and its limits were neither called directly nor changed.

## Actual calls and outcomes

Sizes and hashes in this section identify uncompressed canonical JSON bytes. The retained `.json.gz` files are deterministic gzip containers; their separate compressed hashes are in the execution receipts and final manifest.

| Call | Exact request bytes | Lexical tokens | Records / assertions / sources | Actual returned bytes | Actual public result |
|---|---:|---:|---|---:|---|
| `ORDINARY_CONTROL` | 340,085 | 40,940 | 152 / 306 / 8 | 1,080,114 | `ARTIFICIAL_MODEL_COMPLETE`; 120 selected; 16 infeasible-completion exclusions |
| `DENSE_FILLED_BOUNDARIES` | 2,097,152 | 159,997 | 512 / 1,543 / 10 | 7,342,831 | `ARTIFICIAL_MODEL_COMPLETE`; 120 selected; 372 infeasible-completion exclusions |
| `ESCAPED_ASSERTION_IDS` | 2,097,152 | 159,997 | 512 / 1,543 / 10 | 3,300 | `OUTPUT_REFUSED`; `OUTPUT_BYTE_LIMIT`; null synthetic result |

All three requests have maximum JSON nesting depth 9. The first two retained complete models have no hold beyond the three unconditional real-source holds. Every exact constructed capitalization in those two results matched the independent fixture arithmetic. The dense selection was additionally recounted from its saved result against all 120 positions, five buckets of 24, six activities of four per bucket, the 2L/1M/1S cell requirement, and the UK/JP/EU counts of eight each. These are artificial-model checks, not issuer eligibility or economic validity findings.

| Case | Request SHA-256 | Actual response SHA-256 |
|---|---|---|
| Ordinary | `88b5870b53fb37445edd15858658ff7c86817470939b3f36eb86a5543acfc322` | `895693a788e3466bbfcf959a0cdd5c59e6e613187446b9b88be6d39c1b13dd6d` |
| Dense printable IDs | `ae06938825d9638c3386c8acc414f3285b2c46dde239328bfd69c2b4a34f14da` | `ad94dc10061b7630f58e16961a825f1a194967bc375bde9664c6ad52bbd9fdab` |
| Escaped assertion IDs | `1d561f1f0708d70b8749b412d01e6012021b918d9c42ef7864dc1e871c2ecad4` | `92ed605dc8d74f562eb59c89eaf3dced6930c1645d2a22c4528c68b19bff4e09` |

The preliminary `DENSE_FORCED_INT` request was constructed but never passed to the API. Its 1,791,482 bytes and preparation receipt are retained to make that distinction explicit. The source-derived calculations and saved-result checks also made zero API calls.

## Why the public output branch is reachable

The source admits an input of at most 2 MiB, at most 160,000 lexical tokens, depth at most 24, and at most 512 records. Individual source bytes, record classes, assertion bundles, events and exact rational arithmetic have their own limits. These constraints compete for the same input budget; their separate maxima cannot be added as though all were simultaneously attainable.

The initial construction combined several permitted expansion mechanisms. It used fixed-seed artificial issuer identifiers to make the INT selector encounter many candidates that cannot complete the residual quota problem. It retained equivalent assertions whose IDs appear in several receipt fields. It also used exact long decimal factors, with a common factor preserving the price and capitalization ratios 4:3:2:1. No real-source premise, policy constant or hash seed changed.

That initial dense call produced 7,342,831 bytes, leaving 1,045,777 bytes below the 8 MiB limit. Its `modeled_cap_receipts` accounted for 5,069,698 serialized bytes; its INT trial list accounted for 1,697,278. It was a substantial near-limit sample, but it did not prove that larger legal results were impossible.

The consequential distinction is between an ID's decoded UTF-8 byte length and its JSON wire spelling. The contract bounds the former at 256 bytes. It does not prohibit control characters in an opaque ID. A U+0000 character occupies one decoded UTF-8 byte and six bytes when serialized as `\u0000`. A string of 256 such characters therefore needs 1,538 JSON bytes including quotation marks, rather than the 258 bytes of a 256-character printable ASCII spelling.

For this specific resolved-equivalent assertion construction, each changed assertion ID occurs four times in the complete receipt: once in the supplied assertion, once in `all_assertion_ids`, once in `active_assertion_ids`, and once in the corresponding `active_values` ID list. The reviewer verified those four occurrences for every changed ID in the actual saved printable-ID response. This is not an assertion that every arbitrary failed or excluded assertion has the same expansion.

The phase-two request reallocated the existing wire budget:

| Transformation | Request byte effect | Analytically projected complete-response effect |
|---|---:|---:|
| Shorten 512 class IDs from 256 printable characters to `c`, including the corresponding input class-ID lists | −261,120 | −391,680 |
| Collapse the extended publisher labels to `p` | −305,670 | −305,670 |
| Replace 113,358 assertion-ID padding characters with escaped U+0000, retaining the distinct opaque prefixes | +566,790 | +2,267,160 |
| Recompute affected bundle content bindings | Input bytes already accounted for | +22 from byte-length decimal spelling |
| **Net** | **0** | **+1,569,832** |

The resulting request remains exactly 2,097,152 bytes. It has 1,543 globally unique assertion IDs, of which 465 changed; the maximum decoded ID length is still 256 UTF-8 bytes. It has the same 159,997 lexical tokens and depth 9. Numeric source bytes, evidence spans, quantities, issuer IDs, priority ordering, source list, chronology, actions and relations are unchanged. Class IDs remain consistent within each issuer. Publisher labels remain unauthenticated labels.

An independent transformation of the earlier actual response, updating only the identified string occurrences and content bindings, projected an unbounded canonical response of **8,912,663 bytes**, or 524,055 above 8 MiB. Its projection hash is `5fa0f43441b7702caf81dd34f2ec1225cc37c1869b409a1eae21c4664b46e221`. The projected body was not saved and is not an actual API output. The later `VERIFY_SAVED_WIRE_DERIVATION.py` check reproduced this projection using retained inputs and the prior result, without importing the application or making an API call.

The actual third call returned the small typed refusal instead. Its response binds the exact raw and canonical request bytes, retains the exact policy/adoption binding, and withholds the model. `OUTPUT_REFUSED` with `OUTPUT_BYTE_LIMIT` is the actual branch evidence; the analytical 8,912,663-byte value is supporting arithmetic, not a measured pre-refusal application buffer or a response the application emitted.

## Two explicit corrections to the initial reviewer derivation

### Predicted 376 exclusions became 372

The initial fixture marked 376 early JP/EU rows in the four critical activities as forced large-band competitors. Adding 90 price-4 rows to each affected JP pool changes the relative thresholds. Each such pool contains 94 rows: 91 at price 4, and one each at prices 3, 2 and 1. Both k1=47 and k2=71 fall at price 4. The four original price-3 rows therefore fall in S and may legitimately be included.

Those four rows are r105, r109, r113 and r117, respectively in `SEMICONDUCTOR_CLOUD`, `INDUSTRIALS`, `CONSUMER` and `ENERGY_MATERIALS`. The saved actual result labels each S and records `INCLUDE`. The remaining 372 critical L competitors produce the observed infeasible-completion trials. This is a correction to the independent fixture prediction, not an application defect.

The first `SAVED_RESULT_CHECK.json` draft correctly recorded these four rows and their outcomes but mistakenly described the pool as 92 high-price rows plus two lower rows. That file remains byte-identical. `SAVED_RESULT_CHECK_002.json` explicitly supersedes only that narrative with the independently recounted 91-plus-three composition and retains the original binding. The pre-execution plans also retain their original 376 prediction.

### The initial per-trial byte estimate was ASCII-only

`DERIVATION.json` used a deliberately loose 8,959-byte trial-object estimate with a 258-byte quoted issuer ID. That is an estimate for printable ASCII identifiers, not a universal bound under the decoded-ID contract. Replacing that term with the maximum 1,538-byte JSON spelling adds 1,280 bytes, producing a corrected loose trial estimate of 10,239 bytes and a 392-trial product of 4,013,688 bytes.

The structural terms underlying this loose estimate are three INT countries, 18 activity/band cells, a 54-entry country/cell capacity matrix, and at most 75 graph edges. A complete 120-selection fixture needs at least 96 non-INT records, leaving at most 416 INT candidates within 512 total records; selecting 24 of them leaves at most 392 failed trials. The bounding object includes graph entries that cannot all describe one real cut, so it is intentionally loose. It is not a global combined output maximum or a standalone feasibility theorem. The original bound remains archived and its ASCII-only restriction is explicit in the phase-two derivation and final receipt.

## Actual execution and effect accounting

The public runs used these exact commands from `/workspace/scratch/9fd3d58c239a`:

```bash
PYTHONDONTWRITEBYTECODE=1 python -B lanes/source_diagnostic_output_bound_review_v1/RUN_OUTPUT_PROBES.py > lanes/source_diagnostic_output_bound_review_v1/OUTPUT_PROBES_RUN_001.log 2>&1
PYTHONDONTWRITEBYTECODE=1 python -B lanes/source_diagnostic_output_bound_review_v1/RUN_PHASE2_OUTPUT_PROBE.py > lanes/source_diagnostic_output_bound_review_v1/PHASE2_OUTPUT_PROBE_RUN_001.log 2>&1
```

| Run | Actual API calls | Observed process identity | Tool completion | Exit |
|---|---:|---|---|---:|
| Initial ordinary and printable-ID run | 2 | Scratch process-local PID 5; tool session 30874 | Initial chunk `ac2027`; completion chunk `f36c59` | 0 |
| Authorized escaped-ID run | 1 | Scratch process-local PID 5 in a separate invocation | Chunk `b1562e`; no outstanding tool session | 0 |

Repeated process-local PID values do not identify one continuing process or a native machine process. The phase-two receipt records its start at 2026-10-09T13:38:56.104703Z and completion at 13:38:56.919646Z. Its measured call duration was 0.715393 seconds in that scratch invocation; no production latency claim follows.

Preparation, compile-only inspection, saved-result arithmetic, manifest checks and report generation are separate zero-API operations. The phase-two runner contains exactly one `diagnose` call site and had a successful compile-only check before execution. Both public runs used the already frozen reviewer audit guard for named filesystem-mutation, process and socket events during application import and `diagnose`. Both recorded zero guard events. The guard's limited Python audit scope is stated in the receipts; it is not an authentication, host-containment or universal dependency proof.

There were no native, Git, store, provider, source acquisition or authority-registry actions in this lane. The application module, policy, adoption, prior requests and prior results were not edited. `SOURCE_PRESERVATION.json` additionally verifies every member of the original independent-vector packet and both frozen kernel-review packets: 55, 144 and 61 manifest members respectively, plus their three exact manifests. The source and method pins above were reverified after execution.

## Limits and decisive falsifiers

The branch is now exercised for one exact permitted escaped-ID request. The evidence would fail if the request exceeded the input/token/ID limits, if an earlier input refusal were substituted for the output refusal, if the source or policy hash differed, if a private helper or changed constant supplied the result, or if any authority was promoted. The retained inputs, runner, exact public output, source inspection and receipts address those falsifiers.

No mathematical worst-case output size, maximum resident memory or minimum branch-triggering request has been established. The serializer budget bounds serialized output; the application constructs a result object before `_finish`, so this is not proof of an 8 MiB total-memory ceiling. The sample does not test exact acceptance at 8,388,608 output bytes versus refusal at 8,388,609, nor does it explore every combination of classes, relations, persistent histories, actions, rational lengths or escaped strings. No additional calls were made to enlarge this bounded result.

Synthetic completion or byte integrity does not establish historical roster completeness, independent source truth, legal rights, canonical identity, genuine stress-case review or economic predictive value. Those unresolved interfaces remain the principal's real-source gate. This review supplies a concrete public-path budget witness and preserves the earlier review history; it does not change the research-only boundary.

## Artifact guide

- `PHASE2_PLAN.json` and `PHASE2_DERIVATION.json` are the frozen pre-third-call plan and analytical derivation. Their zero-call fields describe that earlier freeze and are intentionally unchanged.
- `EXECUTION_RECEIPT.json` retains the two original calls. `PHASE2_EXECUTION_RECEIPT.json` records the third separately.
- `*.request.json.gz` and `*.result.json.gz` retain exact compressed requests and actual outputs. `DENSE_FORCED_INT` has no output because it was never called.
- `SAVED_WIRE_VERIFICATION.json` binds the zero-API projection and label-transformation check. `SAVED_RESULT_CHECK_002.json` records the transparent narrative correction.
- `COMMAND_EFFECT_RECEIPT.json`, `SOURCE_PRESERVATION.json`, `FINAL_RECEIPT.json` and `MANIFEST.json` bind execution, preserved inputs, final outcome and package contents.

**STOP. No further application calls, changes or reviews are included in this assignment.**
