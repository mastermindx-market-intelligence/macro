# CI attempt 1: terminal failure classification and source repair

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

## Second independent native-acquisition failure in the same attempt

Pack 11 job `130564015311` later completed with failure at 14:37:38 UTC. Its Brain native browser setup ran from 14:27:34 to 14:37:34 and reported the same four exit 100 / FETCH downloads followed by NATIVE_COMPLETION_RESPONSE_UNKNOWN. Its three preceding Brain proof groups passed; the final browser group and thirteen downstream logical jobs were withheld.

Original artifact: https://github.com/mastermindx-market-intelligence/macro/actions/runs/43032587201/artifacts/13863744332 . Adjacent `pack-11-attempt-1.zip` SHA256: `863f03586198a08b0d75e45301c397b60f5279ad4de4d0f4326fb96c7808f5fe`; extracted JSON SHA256: `88fa22bb68dd6fa86e9897f5fbf82680a90ca1db95464eace19111fa885a71a2`.

Its runner was GitHub Actions 1000581498, group GitHub Actions, label ubuntu-latest. Raw-artifact upload, checkout post-cleanup and Complete job succeeded; the log reached orphan cleanup at 14:37:35.687. The original acquisition outcome remains unknown. The same hosted-VM termination boundary applies; no old /tmp transaction is reused.

The recurrence is recorded separately from the earlier matching-helper success in PR #11036 / run 43030400365. That comparison completed browser setup in 21.8 seconds and then 169 browser tests; it supports a host/network-dependent hypothesis but does not prove DNS as the cause of either sanitized FETCH failure here.

No retry has been dispatched at this checkpoint. Recovery must preserve both originals, classify the failed packs, and use one bounded same-owner retry of the justified infrastructure failures. The updated recovery-decision.json distinguishes terminal failed-job disposal from the original service's whole-run eligibility check; the service's actual refusal or acceptance remains binding.

## Pack 4: demonstrated Ubuntu mirror DNS failure

Pack 4 / job 130564015402 failed the unchanged bot-session-recovery-browser installer before its required browser contract. The log first reports DNS resolution failure for azure.archive.ubuntu.com at 14:22:23, then APT exits 100 and Playwright exits 1 at 14:30:07. Seventy-eight semantic steps passed; one installer step failed and its dependent test did not run. The exact-base replay encountered the same DNS failure but exhausted its budget with descendant settlement unknown, so inherited semantic proof was not established. The completed hosted job published its artifact and reached checkout/orphan cleanup at 14:51:55.

Original artifact 13865592060 is retained as pack-4-attempt-1.zip/json. ZIP SHA256: 6b4038266261226eb36b5d67763331333c6dd889f90858f5d1b53fa023da022c. JSON SHA256: 4690115c1aeecf058501132ecd354150bb58f7c38bec4549851b23ee36714c89. The root read the decisive failure lines from the completed job log.

## Pack 0: hosted runner communication loss; no test verdict

GitHub marked job 130564015585 completed/failure at 14:51:09, but its pack step remains recorded in_progress and upload/post-job steps remain pending. No semantic fragment was uploaded, and the log blob is absent. The original GitHub check annotation explicitly reports that the hosted runner lost communication with the server. This is not attributed to APT and gives no attributable failing test assertion. CPU, memory and network are possible explanations in GitHub's generic annotation, not established causes here.

The exact job metadata, two annotations and zero-artifact response are retained alongside this document. The annotations endpoint was unsupported by the connector (schema limitation, no authorization denial), so the same GitHub object was read through the already-authorized host CLI after verifying its logged-in identity. No credential was exposed and no GitHub mutation was performed by that read.

Recovery must preserve this execution uncertainty. GitHub's authoritative terminal hosted-job record and its disposable-VM contract support requesting normal service-owned recovery; they do not invent a successful cleanup or completed FIF test result. No original workspace or process is resumed or reused.

## Targeted recovery scope

Four terminal failed packs are now classified: 9/11 native package acquisition; 4 ordinary installer DNS failure; 0 hosted runner communication loss. Five other packs have passed, and 5/7/10 were still running at the last preflight. The PR remains head 0d26e84a15a0578d15bc1521021676d547d2aaf2, unmerged and unarmed.

The concrete next action is one normal targeted retry through the original GitHub Actions owner. GitHub must enforce eligibility for its active run. A service-state refusal is retained and may be reconsidered only after the relevant state changes; a permission or safety denial ends that action. No source, test expectation, mirror, package version, deadline or release gate has changed. No retry has been dispatched at this checkpoint.

## Terminal aggregate and source correction

The completed run has five passing packs (1, 2, 3, 6, 8) and seven failed packs (0, 4, 5, 7, 9, 10, 11). The final gate records 593 passed and 121 unknown semantic classifications, four infrastructure findings, and evidence digest `cc5b6d8159d43bea3202a218b55d39d68de73bbfce03c6ddb36893c3f4e41c4d`. Its original ZIP and JSON are retained here as `gate-attempt-1.*`; the remaining pack artifacts and hashes are in `remaining-artifact-manifest.json`.

Pack 5 failed two browser installers with explicit `azure.archive.ubuntu.com` DNS errors. The International exact-base installer reproduces that error; Catalyst's replay expires with descendant settlement unknown. Pack 7 combines a Prophet installer DNS failure with BEA native completion unknown. Neither supplies a product assertion or permits reclassifying unrun tests as passes. Their completed owners uploaded receipts and reached post-job cleanup.

Pack 10 is different: alongside two installer DNS failures, `public-render-fastlane` reports an actual assertion at `tests/test_glossary_contract.py:299`: `test_site_pair_matches_a_fresh_render_of_the_template`. The test and its contract are unchanged. The candidate page had raw inline styles; after isolated CSS externalization the assertion additionally exposed a preload in the wrong position. A full render from the committed public-page builder in a temporary root, followed by the existing injection, externalization and optimization owners, restores canonical output. Only the glossary page and the new `dfb3c710.css` asset enter the product tree. Main content, scripts and the daily alert banner are preserved; CSS block bytes are identical in their fingerprinted assets.

The initial reproducer and intermediate unsuccessful check remain in `../../glossary-output-repair/`. The corrected owning suite passes **333 tests**, with the existing one-test deselection unchanged, and the separate US Regime History proof passes **1 test**. No assertion or gate was weakened.

This new source evidence supersedes the earlier infrastructure-only retry proposal. No retry was ever dispatched. The next action is to publish the real repair with current main integrated, require fresh candidate CI, and use the existing merge controller only when its binding conditions pass. No merge, deployment, or production acceptance is claimed.
