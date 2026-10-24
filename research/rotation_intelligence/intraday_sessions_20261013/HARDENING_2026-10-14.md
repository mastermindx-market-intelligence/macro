# Rotation comparison reliability increment, 2026-10-14

Same operation and PR #9196. Published predecessor d5e076c247d993fe39b8ad9b9ef89b4ff80ff9f0 remains unmerged. This increment is built locally; no deployment or market performance claim.

## Reproduced and repaired

- Older source snapshots, older build clocks, and a missing benchmark could overwrite a newer transient baseline. Three chronological regression controls fail on the predecessor and pass after retaining the newer baseline.
- The grounding consumer admitted stale intraday comparisons indefinitely if dates were parseable. It now enforces the existing 45-minute quote budget, source/evaluation timezone awareness, same regular session through the shared calendar owner, exact elapsed duration, permitted source skew, and arithmetic consistency. Historical test controls now inject evaluation time explicitly.
- Equal-source-timestamp price corrections now reset the transient baseline without emitting a new interval. Two controls show that a subsequent unchanged price has zero incremental return, instead of treating the corrected price as a new move.
- Last-good persistence now atomically replaces the one existing sidecar. Simulated replace failure preserves the prior complete bytes and removes the temporary file. No new ledger, store, scheduler or runtime owner.

## Evidence

The first baseline/consumer counterexample run had 10 failures and 1 pass; correction controls had 2 failures. The eight-module focused suite subsequently passed 505 tests. These are synthetic/source proofs. The complete predecessor CI run 38511271812 concluded contract-delta success and 11 successful test packs, with pack 3 failing on tests/test_sni_injection_safety_ext.py:601. Its base comparison reproduced the identical lint defect; current main 05ea40d5557939bf557d7ce3b74f7f5c2a74aa50 already uses path.relative_to(SNI_ROOT).parts. No CI waiver is requested. Relevant application and calendar blobs are unchanged between the operation base and that main revision; the CI manifests changed materially and require actual integration proof.

Independent paid review request rotation9196-semantic-review-r1 was submitted via installed M2 fabric_task.py on the original attended Web operation root/parent rotation-intraday-session-research-20261013, after exact-ID NOT_FOUND. Router selected Bailian/Qwen on ubuntu2. The reviewed packet binds predecessor d5e076c247d9 and has SHA256 a4e16ed86ac29832dc50d2ed05f0739866c657e4eb49eed06df70a667bbcc581. Controller launch and admission are recorded; no completed review or acceptance is yet claimed. This is not a native Codex thread or a Runtime Job identity. Retain the same child and reconcile its result before any replacement.

## Remaining

Finish independent review, adjudicate its exact findings, bind final changed source to follow-up review, integrate the already-fixed current base, run required checks and verify the real consumer. No SSH retry, credential change, new provider source, alert or production effect occurred. Terminal #881/#847 shared-path custody remains unchanged.

## Integrated final source increment

Current main 05ea40d5557939bf557d7ce3b74f7f5c2a74aa50 was merged into the original branch without source conflicts (integration commit f2e58641ec339052484758ce16a5481435e4f8bf). The exact tracked basket-pulse fixture was restored after sparse checkout removed its working copy; its SHA256 is 9ffbe879ca70f5b5de304a0dc36978cb17b55291b4642b9782ff2c22d044a314 and it has no Git diff. The integrated nine-module suite passed 508 tests, including the formerly failing path-prune lint.

The complete contract check then detected one newly reachable dependency, engine/session_digest.py, in the exclusive regime-outlook-mapping job. Commit d75b9d8248843e2d70f24e9c7a675fe43a188ca6 adds that exact dependency to the job scope. The subsequent complete contract check passed with 0 introduced / 0 inherited findings. No CI waiver or permission gate was changed.

An additional probe found that the new atomic-write temporary file reset a pre-existing 0640 sidecar to 0600. The final implementation preserves existing reader permissions and uses normal OS umask handling for a new file, while retaining exclusive temporary-file creation, fsync, atomic replacement and cleanup. The mode is a data-file property; no credential, account, service authorization or access safeguard was changed. The final eight-module functional suite passed 507 tests (two mode tests added); the separately accepted three lint tests are not inflated into another independent functional suite.

The hardened actual-module replay still reports the hidden 30-minute movements -1.960784% and +1.010101% while both daily group changes are zero, and rejects a repeated source snapshot as benchmark_nonadvancing. producer_grounding_replay_hardened.json binds the exact new producer/consumer hashes. This remains synthetic-source proof, not live product or financial validation.

## Independent review and source evidence

The original independent review request remains ACTIVE_OR_WAITING with no retained result at the latest local status inspection. A same-run observe-run diagnostic returned REFUSED / original_run_observation_unconfirmed. No other identity, host or carrier was used to get that refused observation; no replacement reviewer was submitted, no verdict was invented, and no acceptance was recorded. Controller admission/launch messages are not substituted for a completed review. The original request, root and parent must be preserved until reconciliation.

SOURCE_COVERAGE_2026-10-14.md and its two JSON receipts record independent authorized public-display and GitHub full-snapshot schema/coverage reads. No market prices are exported in those census reports. Full-snapshot quote records cover 700 of 702 active basket members and all 12 SPY/sector anchors; the branch stores only one orphan snapshot. This does not establish the private VPS source's actual coverage, historical knowability, regular-session freshness, opening-anchor semantics or intended-use rights.

## Next exact actions

Consume the original review via fabric_task.py status/result for rotation9196-semantic-review-r1. Do not re-submit under a different ID or claim reviewer acceptance. After it returns, adjudicate the predecessor-specific findings and obtain final changed-source review before release. Consume new-head CI, then use normal release and actual production consumer proof. Current source remains BUILT_NOT_PROVEN. The new Terminal/Macro UI, overnight decomposition, retained historical issuance and alert-quality studies remain unfinished; no parent mission completion is claimed.
