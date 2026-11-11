# CI run 43057303734 — current candidate

Subject `bf7de965767cdfc2cd82d976bac3dd0243e56d50`, tested merge `69b6d7dbc7a369bc0424a14f78d6812990f0a031`, base `fc2dffe6a9e564ac8c4338418afe585afd5afad2`, attempt 1. The complete plan schedules 329 logical jobs in 12 packs. Canonical-main runner changes select the full suite.

## First terminal failure

Pack 9 / job 130651318176 failed in the ontology browser setup. The existing 600-second deadline expired after four settled exit-100/FETCH download failures and the built-in completion attempt. Its response is `NATIVE_COMPLETION_RESPONSE_UNKNOWN`; that unknown is preserved. `native_children=[]` is not affirmative descendant-settlement proof, and terminal hosted-job cleanup does not rewrite the original completion transaction as known/no-effect. Installation never started through this path; inherited completion hooks prevent treating download-only as proof of no effects.

The log exposes no selected endpoint or transfer cause. Caller timeout/retry and image mirror-list diagnostics do not establish DNS, endpoint selection or a mirror failure. No source assertion failure was observed in this group. The exact helper blobs are unchanged from the original failed run. No retry, mirror change, relaxed deadline or weakened gate has been applied.

The ZIP and semantic JSON are retained byte-for-byte. The focused log excerpt binds the full original log digest in `initial-failure-receipt.json`. The original GitHub job is https://github.com/mastermindx-market-intelligence/macro/actions/runs/43057303734/job/130651318176 .

This is an intermediate diagnosis while other original packs run, not the final workflow outcome. One existing observer remains responsible for exact-head terminal returns. Source qualification and the verified site tree remain intact; release is still pending.
