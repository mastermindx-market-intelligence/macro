# Principal validation update after independent source review

The independent source/CI inverse review passed. This does **not** make the principal's first native validation invocation green.

The principal reported native PID 47111 concluded exit 1. Its actual kernel invocation passed 117 tests in 13.09 seconds, and manifest validation passed. The four existing curated/scope tests returned three passes and one failure in 148.35 seconds. The failing condition was `gmi-source-diagnostic-kernel derives no closure`: the new suite had not yet been staged, so it was absent from the native discovery inventory.

The original failed validation receipt is retained with SHA-256 `7ae2fd0082870f15aad38583c4b2dd066e0508c5f3151baaf4c9ab93146c3ed3`. These execution outcomes are principal-supplied evidence, not independent test executions by this reviewer.

The causal preparation issue is consistent with the actual native code independently inspected by the reviewer in read-only PID 48797: `_tracked_candidates` uses `git ls-files -z`. This inventory deliberately excludes untracked files. The reviewer advised the principal of that requirement before receiving the first validation outcome. The appropriate fix is to stage the intended source, retaining the existing discovery and closure controls.

The principal reported all 93 source/CI pins unchanged and announced the bounded remedy: stage the exact 49 intended paths, run the existing-selector API probe, and rerun only the affected existing closure test. No kernel or policy changes were proposed, and this reviewer performed no additional tests. At this review's freeze, the remedy's result is pending a separate principal execution receipt.

The immutable independent result remains **PASS for source identity and inverse preservation**, with no required source correction. The actual native gate status must be read from the principal's separately concluded validation receipts. Neither this context note nor the independent review waives the initial failure or assumes the follow-up will pass.
