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
