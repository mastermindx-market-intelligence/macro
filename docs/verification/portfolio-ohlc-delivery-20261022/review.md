# Independent review dispositions

These notes record independent native read-only reviews accepted by the root
owner. Reviewers did not edit, execute tests, publish, dispatch workflows, inspect
credentials, or access provider data.

## Helper and synthetic regressions — PASS

Reviewer: `/root/portfolio_treasury_merge_readiness`.

The reviewer read the complete helper, reconstructed its SHA-256, then read the
complete new regression file and reconstructed that SHA-256. The reviewer also
consumed the actual core test receipt and complete log from
2026-10-22T11:43:56.657853Z through 11:44:00.401397Z: exit 0, 78 passed,
source unchanged during execution.

| File | Qualified SHA-256 |
|---|---|
| scripts/publish_ohlc.py | ead2884ce3d462043ebffc55a71c6e6079b0eea363e13e75bbd14193bbcaa4c8 |
| tests/test_publish_ohlc.py | 4ae3fb590a8894690d6030e5a3867a890fae4642b6c08cdb09d3c6a305c1a483 |
| scripts/build_chart_data.py | 41d7cba6d3465cd6b707bab753623e53ee6c3531b14680c4cca99fbcf8629719 |
| tests/test_build_chart_data.py | 7d2200b2054eb334eec965e1ccedb7c13c7b69586eb29227c32eb5d4ba99fcf0 |

No remaining assigned helper findings. The five corrected blockers were:
upload lock occupancy; archive extension-body allocation before rejection;
unbound repeat acknowledgments after manifest drift; generic lost-ack or local
receipt-write failures permitting resend; and a missing watermark in a used or
rolled-back store.

Additional reviewed tests distinguish a concurrent selection during staging,
rollback/predecessor digest conflicts, borrowed-lock body exceptions, maximum
USTAR filenames and prefix traversal, and producer receipt invalidation and
failed-switch recovery.

## Rebased updater and workflow integration — PASS

Reviewer: `/root/portfolio_combined_ci_triage`.

The reviewer inspected current updater blocks and tests, the daily tail, DAG
inventory, producer/workflow identity, publisher entrypoint, and documentation.
Updater SHA-256 supplied by the root receipt:
`970a5008950ffcc7ffecc2d495c5aa88fa853c009f53b812c203cff37f0432e1`.
The reviewer did not independently recompute the entire updater hash.

The inherited descriptor-9 lock and Movers guard remain in order. OHLC
reconciliation precedes the main rsync, the root OHLC path is excluded from
deletion, and reconciliation also runs outside the Git-change branch. A recorded
OHLC failure survives later success while unrelated deployment work continues;
an earlier failure from another lane is preserved.

First payload publication remains conditional on successor-updater installation.
No new retained-only daily dispatch mode was reviewed or implemented in this PR.

## Final CI declarations — PASS

Reviewer: `/root/portfolio_combined_ci_triage`.

The reviewer found and confirmed the original data-gate coverage defect, then
reviewed the dedicated code-gated exclusive job, exact import closure, ancestor
initializers, unchanged dependencies/commands of inherited jobs, and curated
registration.

The 25 dependency additions across 13 existing jobs exactly match the failing
closure census. The subsequent nine `app/__init__.py` additions exactly match
the introduced ancestor rows. No broad glob, checker change, allowlist change,
or ceiling relaxation is present. The app initializer is empty.

Final manifest SHA-256:
`94df276ae0f0f464b80aa6db9615683fa59333e4ee5baae08b09fd446da6678b`.

The final ancestor-ratchet receipt records exit 0, one passing test, unchanged
source, 2026-10-22T12:04:23.447770Z through 12:04:30.907123Z. Other focused CI
registration cases passed on the immediately preceding manifest; the only
subsequent delta is the reviewed additive initializer declarations.

## Limits

These dispositions establish the inspected source and focused local evidence.
They do not establish whole protected CI, deployment, generation delivery,
authenticated Portfolio price coverage, or current Treasury observation dates.
Those release stages require their own receipts.
