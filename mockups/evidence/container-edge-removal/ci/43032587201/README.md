# CI attempt 1: native dependency-acquisition failure

- Delivery PR: https://github.com/mastermindx-market-intelligence/macro/pull/10654
- Subject head: `0d26e84a15a0578d15bc1521021676d547d2aaf2`.
- Run: `43032587201`; failed pack 9 job: `130564015729`.
- Actual tested commit: `ec7b17cd016092d7bd7a57750fb33b3ad3b3ebd0`; tested base: `7d0326771ea7761adfbd271552820ed0f04ebdf1`.
- Original artifact: https://github.com/mastermindx-market-intelligence/macro/actions/runs/43032587201/artifacts/13862009460
- The adjacent ZIP and JSON preserve the original artifact without changing its classification. ZIP SHA256: `59e1694fd823af9123cadafbe1e4966f635b29ce084a6cfcc45d71bd2ae5fc85`; extracted JSON SHA256: `fe28606d4076e2bf1d6b52f7dc54d25b488d62e3b37bac88a842d177a3d8379e`.

## Observation

Ontology browser setup ran from 14:00:33.688 to 14:10:33.690 UTC on 2026-11-11. Native APT download tasks 0, 1, 3 and 4 each returned 100 with sanitized FETCH errors. The supported native transaction-completion path then reached its finite deadline without a proven completion response: NATIVE_COMPLETION_RESPONSE_UNKNOWN; completion=failed/unknown; installation=never_started. The receipt retains the original temporary transaction path and handles.

All six ontology proof commands were unrun and classified infrastructure_blocked. Twenty-two subsequent logical jobs were withheld because original command settlement was unknown. No failing pytest assertion is identified. Exact-base replay and workspace restoration were withheld. This is not a proved inherited test failure.

The native browser setup helper is byte-identical between the subject head and actual tested base (Git blob `3e400c1691b5be2825237004bce42d881f2d230b`). The observed Playwright distribution/driver-version difference is not the failure signature; source qualification preceded native APT acquisition.

## Recovery boundary at this checkpoint

The original hosted job completed with failure, finished post-job cleanup and reached “Cleaning up orphan processes” at 14:10:35 UTC. Only the semantic fragment was uploaded for this pack; no retained native APT transaction receipt appeared in the workflow artifact inventory inspected afterwards. The original receipt remains unknown; it is not rewritten as a successful installation or proved no-effect operation.

GitHub documents that the VM for a GitHub-hosted job is decommissioned when the job finishes: https://docs.github.com/en/actions/how-tos/manage-runners/github-hosted-runners/use-github-hosted-runners . Any proposed retry must separately reconcile the original target and use the existing GitHub job owner, preserving this artifact and the exact candidate. No mirror, version, timeout, test or gate change is justified by this evidence alone.

At this checkpoint no retry or source repair has been performed. The original workflow's other packs are still running; merge-on-green is not armed. Production acceptance remains outstanding.
