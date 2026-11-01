# Independent WP02 UTC correction review — v2

## Verdict and scope

**PASS for the exact bounded correction of v1 finding R1.** The new parser rejects unsupported fractional precision before datetime conversion. The two original public-API failures no longer admit post-K premises. Supported UTC instants continue to behave correctly, with complete old outputs preserved where required.

This is a corrective source/replay verdict for the existing structural research kernel. It does not approve real-source admission, a historical issuer population, actual cohort selection, source rights, production use, or the unexercised8MiB whole-output branch. The original v1 review remains frozen with its historical `REQUEST_CORRECTION` verdict and failure evidence; this separate package records the later resolution.

## Bound source and unchanged method

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Corrected `source_diagnostic.py` | 77,602 | `f9814c8e65a155ae8273b4127661b5568e97a45c135b679f1db2eb84f36afdb6` |
| Corrected contract | 19,420 | `2806f32cd4367a4b9d6974ccea6ceaa2f2649794c35d256f0b6c5ccae781d0b5` |
| Author suite; delta read, not run by this reviewer | 50,961 | `d7f8dc3ebaf7adafe164e3a370c017ac4bb26e509e35ccf2ba5978429d915082` |
| Unchanged fixture helper; not imported | 7,312 | `37db957fff940f2e9557e36586c07ee4a1a3ea534d9b3e36a5c96630b1a5aa78` |
| Exact unchanged policy | 60,312 | `d41422d76219b1c5d3a3c9cbb19a1bc3124433031200b09499033bd4dc30d522` |
| Exact unchanged principal adoption | 9,593 | `645a20a39842d9c5a03b4ff39a37280d1aa02c32ef545c061d0aa959f06e0016` |

The source diff adds one `UTC_INSTANT` regex constant and changes `_instant`. A complete AST comparison, excluding only that new constant and changed function, found all remaining source nodes identical to reviewed v1. The exact source, suite and contract diffs are retained. The helper is byte-identical. No policy, quota, D, K, seed, numeric-domain rule, selection algorithm, I/O capability or trust interface was added or changed.

The full timestamp form is now `YYYY-MM-DDTHH:MM:SS[.fraction]Z`. The optional fraction contains one through six ASCII digits. More precision receives `UTC_TIMESTAMP_PRECISION_UNSUPPORTED`; even seven zero digits are refused. Other shapes receive `EXPLICIT_UTC_BOUND_REQUIRED`; datetime still validates actual calendar and clock values. The existing40-byte string bound also remains. The parser never rounds, truncates or converts an alternative offset into a supposedly exact K instant.

The contract documents that narrowed form. The author added27 public-path regressions, whose full diff was read. Its reported117-test run is principal-attributed author evidence and is **not counted as this independent execution**. This lane neither imported that test suite/helper nor repeated the old41-case or729-matrix work merely to generate another receipt.

## Actual independent public replay

`RUN_CORRECTIVE_PUBLIC_REPLAY.py` made **26 actual `diagnose` calls** against the exact v2 module and original policy/adoption bytes. All26 met their explicit oracles, with zero unexpected exceptions and zero observed named filesystem-mutation/process/socket audit events during import and calls.

The original four cutoff requests were replayed byte-for-byte from the frozen v1 review:

| Original input | v2 outcome |
|---|---|
| Anchor K+1µs | `POST_CUTOFF_ANCHOR`; complete response identical to v1 |
| Anchor K+100ns | `UTC_TIMESTAMP_PRECISION_UNSUPPORTED`; no modeled selection |
| Correcting assertion/link K+1µs | Prior1.9b cap retained; complete response identical to v1 |
| Correcting assertion/link K+100ns | `UTC_TIMESTAMP_PRECISION_UNSUPPORTED`; whole affected cap null and no modeled selection |

For each of the **six other public timestamp consumers**—membership event, share assertion, price assertion, FX assertion, correction relation and corporate action—the reviewer used a paired input. The valid member has six fractional digits at K, completes the artificial120-member model and returns its expected exact cap. The other changes only that public timestamp to seven digits after K; its intended precision refusal is reached and model selection is withheld. Membership-event source bytes were rebound to the changed event array. Thus no source-array mismatch, bridge error or unrelated shape refusal substitutes for checking the corrected consumer.

Additional controls prove that supported behavior remains usable: exact/before-K corrections produce2.1b, exact-second and one-fraction-digit anchors at K succeed, and the last supported microsecond before K succeeds. Comma fractions and a Unicode digit receive the documented shape refusal; seven zero fractional digits receive the precision refusal.

The original complete balanced model and whole-second post-K revision were also replayed unchanged. Together with the two original microsecond controls, **four complete outputs matched their v1 saved bytes exactly**. No field was normalized away for these comparisons. The exact request/response files and their individual SHA-256 bindings are preserved in `requests/` and `outputs/`.

The actual command was:

```text
PYTHONDONTWRITEBYTECODE=1 python -B lanes/source_diagnostic_kernel_review_v2/RUN_CORRECTIVE_PUBLIC_REPLAY.py > lanes/source_diagnostic_kernel_review_v2/CORRECTIVE_PUBLIC_REPLAY_RUN_001.log 2>&1
```

Execution initially yielded tool session37708 and was reconciled to exit0. The observed scratch process-local PID was5; this is not a native/global host liveness identity. The output log reports all26 calls and the aggregate result. The complete execution receipt is174,212 bytes, SHA-256 `c584811ba09ba1285db0c789f6ba68545acc217d1ffecd09eef880915c990a0e`.

## Preserved evidence and remaining boundary

The original v1 review manifest, SHA-256 `8e5a2712a8eafadb37fc52950e99ed55ef6bebe33eb7652d3583fd44609dc3b9`, and every one of its listed artifacts were verified unchanged. The original independent vector manifest and all listed files were also reverified. Neither old failure outputs nor the initially incorrect recipe preconditions were rewritten or reclassified.

All observed v2 outputs retain `STRUCTURAL_ONLY`, `NOT_READY`, `NOT_ADMITTED`, false authority flags and null real population, capitals, quantiles, cohort, F and INT-flow results. Synthetic validity cannot authenticate a source, an owner, a reviewer, rights, history or economic truth. A real-source adapter still requires a principal-bound existing trusted owner-review/admission interface; this correction supplies none.

This lane wrote only `lanes/source_diagnostic_kernel_review_v2/`. It made no native application/store/Git/source-acquisition/provider or production effect. Named audit guards are bounded Python-event observations, not a universal sandbox proof. No private kernel helper or author test/fixture was called. The source-delta script checked ASTs, hashes and frozen manifests; it made zero API calls.

The corrective composite receipt binds the prior finding, exact corrected source/contract, unchanged method and new independent replay evidence. Its digest is a review-content identity, not a signature, source-admission receipt or architectural adoption decision. The principal retains integration, execution and publication ownership.

**R1 is resolved for this exact corrective composite. No new definite P1/P2 was found in the delta. STOP.**
