# A39 lane receipts ledger

Captured at 2026-10-13T09:33Z. Schema version 1.

## Summary

| rung | count |
| --- | ---: |
| NOT_STARTED | 12 |
| RUNNING_OR_UNKNOWN_AT_CAPTURE | 4 |
| EXITED_NO_RESULT | 24 |
| EXITED_NONZERO | 1 |
| DELIVERED | 20 |
| CI | 0 |
| MERGED | 0 |
| PRODUCTION_PROOF | 0 |
| ACCEPTANCE | 0 |

| host | count |
| --- | ---: |
| ubuntu0 | 17 |
| ubuntu1 | 16 |
| ubuntu2 | 17 |
| ubuntu3 | 11 |

| rc | count |
| --- | ---: |
| 0 | 44 |
| 1 | 1 |
| 75 | 10 |
| 76 | 2 |
| empty | 4 |

Rows: 61. INT1-integrated (PR 9120 unmerged at capture): 15.

This ledger records launcher receipts for 61 delegated Grok lanes captured at 2026-10-13T09:33Z. Counts at capture: 12 NOT_STARTED, 4 RUNNING_OR_UNKNOWN_AT_CAPTURE, 24 EXITED_NO_RESULT, 1 EXITED_NONZERO, 20 DELIVERED. 15 rows carry an INT1 cherry-pick annotation; INT1 PR 9120 was open and unmerged at capture, so those rows remain DELIVERED. A launched lane is not a delivered lane, and a delivered lane is not a merged lane. No row is at CI, MERGED, PRODUCTION_PROOF, or ACCEPTANCE. A lane_claim of PASS or PARTIAL is the lane's own printed line. Two INT1 cherry-picks have no launcher receipt and are listed as integration gaps. This file does not cover orchestrator-native work, lanes launched by other seats, or events after capture.

## Ladder and rules

A delegated lane passes through these rungs in order. None implies the next:

1. ACK
2. QUEUED
3. START
4. RUNNING
5. DELIVERED
6. CI
7. MERGED
8. PRODUCTION_PROOF
9. ACCEPTANCE

Rules, applied in this order:

1. `never_started`: rc in {75, 76} -> NOT_STARTED. highest ladder rung: QUEUED if reserved_at is present, else ACK Launcher refused or failed before the remote CLI started. The lane never started. START and every later rung stay unclaimed even if launched_at or native_started is present.
2. `at_least_start`: launched_at is present and native_started is true -> START. This is a floor, not a skip to DELIVERED. Rule never_started still wins for rc 75/76.
3. `running_or_unknown`: rc is empty and done_at is empty -> RUNNING_OR_UNKNOWN_AT_CAPTURE. Capture ended with no DONE event. This is never DELIVERED.
4. `delivered`: rc is 0 and output_complete is true and a parseable final line is present (lane, status, lane_head) -> DELIVERED
5. `exited_no_result`: rc is 0 and no parseable final line is present -> EXITED_NO_RESULT. This is never DELIVERED.
6. `exited_nonzero`: rc is 1 -> EXITED_NONZERO
7. `int1_annotation`: int1_commit is non-empty -> integrated_into: INT1 (PR 9120, unmerged at capture). The rung stays DELIVERED. Integration into an unmerged PR is not CI, MERGED, PRODUCTION_PROOF, or ACCEPTANCE.
8. `capture_ceiling`: always in this ledger -> forbids CI, MERGED, PRODUCTION_PROOF, ACCEPTANCE

## Table

| run_id | host | rung | lane | lane_claim | tokens | INT1 |
| --- | --- | --- | --- | --- | ---: | --- |
| sni-a1-20261012 | ubuntu0 | EXITED_NO_RESULT |  |  | 839163 |  |
| sni-a1r1-20261012 | ubuntu1 | EXITED_NO_RESULT |  |  | 631542 |  |
| sni-a1r2-20261013T0336Z | ubuntu1 | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-a2-20261012 | ubuntu1 | EXITED_NO_RESULT |  |  | 943340 |  |
| sni-a20-1013a | ubuntu0 | DELIVERED | A20 | PASS | 2188554 | 8334e401eb2c6993dc2099441c1e3ef1b4b3ddbf |
| sni-a2r1-20261012 | ubuntu0 | EXITED_NO_RESULT |  |  | 1361207 |  |
| sni-a2r2-20261013T0336Z | ubuntu3 | EXITED_NO_RESULT |  |  | 1325331 |  |
| sni-a3-20261012 | ubuntu2 | EXITED_NO_RESULT |  |  | 1218686 |  |
| sni-a3r1-20261013T0215Z | ubuntu0 | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-a3r1-20261013T0230Z | ubuntu0 | EXITED_NO_RESULT |  |  | 1224779 |  |
| sni-a4-20261012-r2 | ubuntu0 | EXITED_NO_RESULT |  |  | 1130808 |  |
| sni-a4-20261012 | ubuntu3 | NOT_STARTED |  |  |  |  |
| sni-a4r1-20261012 | ubuntu2 | NOT_STARTED |  |  |  |  |
| sni-a4r1b-20261012 | ubuntu2 | EXITED_NO_RESULT |  |  | 1157518 |  |
| sni-a4r2-20261013 | ubuntu2 | DELIVERED | A4R2 | PASS | 1860913 |  |
| sni-a4v-1013a | ubuntu3 | DELIVERED | A4V | PASS | 1346900 | 97d7f25f6e42e67e30a3d3051e63fb4e61aedf79 |
| sni-a4x-1013a | ubuntu2 | DELIVERED | A4X | PASS | 973854 | 2e5d616afb7a0b36cb036c8a548811922a6fa70b |
| sni-a5-20261012 | ubuntu0 | EXITED_NO_RESULT |  |  | 2268417 |  |
| sni-a5r1-1013a | ubuntu0 | NOT_STARTED |  |  |  |  |
| sni-a5r1-1013b | ubuntu3 | NOT_STARTED |  |  |  |  |
| sni-a5r1-1013c | ubuntu1 | NOT_STARTED |  |  |  |  |
| sni-a5r1-1013d | ubuntu2 | DELIVERED | A5R1 | PASS | 1825295 | dadd3fcd69d51766eb3716a3efa1d26849ea1490 |
| sni-a6-20261012-r2 | ubuntu0 | EXITED_NO_RESULT |  |  | 1704793 |  |
| sni-a6-20261012 | ubuntu3 | NOT_STARTED |  |  |  |  |
| sni-a7-20261012 | ubuntu2 | EXITED_NO_RESULT |  |  | 1354796 |  |
| sni-a8-20261013T0302Z | ubuntu0 | EXITED_NO_RESULT |  |  | 2142022 |  |
| sni-a8r1-20261013 | ubuntu1 | DELIVERED | A8R1 | PASS | 1019344 |  |
| sni-b1-20261012 | ubuntu1 | EXITED_NO_RESULT |  |  | 712607 |  |
| sni-b2-20261012 | ubuntu2 | EXITED_NO_RESULT |  |  | 540653 |  |
| sni-b3-20261012-r2 | ubuntu1 | EXITED_NO_RESULT |  |  | 1141762 |  |
| sni-b3-20261012 | ubuntu3 | NOT_STARTED |  |  |  |  |
| sni-b4-20261012 | ubuntu0 | EXITED_NO_RESULT |  |  | 1028702 |  |
| sni-b4r1-20261013 | ubuntu0 | DELIVERED | B4R1 | PASS | 1767275 |  |
| sni-doc-1013a | ubuntu1 | DELIVERED | DOC | PASS | 2546466 | 33235514d19be52a00a018e683023b2de8cd2120 |
| sni-eq-1013a | ubuntu0 | NOT_STARTED |  |  |  |  |
| sni-eq-1013b | ubuntu2 | DELIVERED | EQ | PASS | 2919714 | 00291933daed3f75f1124bb58d496867bee68d12 |
| sni-inv-1013a | ubuntu1 | DELIVERED | INV | PASS | 2988953 | a534abec77cce7e64a991f913598a2a3e2c0d2e5 |
| sni-pub-1013a | ubuntu1 | DELIVERED | PUB | PASS | 1416135 | d843c9d30ab564bbe2d6f548d3d571ddff62220b |
| sni-qf-1013a | ubuntu0 | DELIVERED | QF | PASS | 6090856 | 59e26380271d0fdaaa81522b904146eedac648f1 |
| sni-repro-1013a | ubuntu3 | DELIVERED | REPRO | PASS | 3496064 | d89ff8d474af9321581eb178390788459d392b55 |
| sni-rpr-1013a | ubuntu3 | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-rpr-1013b | ubuntu2 | NOT_STARTED |  |  |  |  |
| sni-rpr-1013c | ubuntu0 | NOT_STARTED |  |  |  |  |
| sni-rpr-1013d | ubuntu1 | DELIVERED | RPR | PASS | 2354446 | d149bff07420e50626c996d11ba2173748ec9789 |
| sni-s0d-20261013T0302Z | ubuntu3 | EXITED_NO_RESULT |  |  | 1879470 |  |
| sni-s0dr1-20261013 | ubuntu3 | DELIVERED | S0DR1 | PASS | 1307791 |  |
| sni-s1h1-20261012 | ubuntu0 | EXITED_NO_RESULT |  |  | 5924709 |  |
| sni-s1h2-20261013T0336Z | ubuntu0 | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-s1h3-20261013 | ubuntu2 | DELIVERED | S1H3 | PASS | 1092645 |  |
| sni-s2h1-20261012 | ubuntu1 | NOT_STARTED |  |  |  |  |
| sni-s2h1b-20261012 | ubuntu2 | EXITED_NO_RESULT |  |  | 6771812 |  |
| sni-schk-1013a | ubuntu2 | DELIVERED | SCHK | PASS | 2985416 | 519444d349bd13d1eac6168bc79ef1f3612143c9 |
| sni-x1-20261012-r2 | ubuntu1 | EXITED_NO_RESULT |  |  | 2996332 |  |
| sni-x1-20261012 | ubuntu3 | NOT_STARTED |  |  |  |  |
| sni-x2-20261012 | ubuntu2 | EXITED_NO_RESULT |  |  | 2474479 |  |
| sni-x3-20261012 | ubuntu1 | EXITED_NO_RESULT |  |  | 1658358 |  |
| sni-x4-20261013T0335Z | ubuntu1 | EXITED_NO_RESULT |  |  | 3359308 |  |
| sni-x5-20261013T0335Z | ubuntu2 | EXITED_NONZERO |  |  |  |  |
| sni-x6-1013a | ubuntu2 | DELIVERED | X6 | PASS | 3435017 | 6a70fa4ab378a06aebe08924d24fffb8aaa9020b |
| sni-x6r-1013a | ubuntu1 | DELIVERED | X6R | PASS | 4048676 | edb06011c0a91517314d9f2a7541baace2d8951c |
| sni-xrep-1013a | ubuntu2 | DELIVERED | XREP | PASS | 3131076 | 1fd7e88085cc09d55969eea87a1d9b2b4a2ff332 |

## Never-started runs

rc 75 or 76: the launcher refused or failed before the remote CLI started.

| run_id | host | rc | reserved_at |
| --- | --- | ---: | --- |
| sni-a4-20261012 | ubuntu3 | 75 | 2026-10-12T04:35Z |
| sni-a4r1-20261012 | ubuntu2 | 75 | 2026-10-12T05:19Z |
| sni-a5r1-1013a | ubuntu0 | 75 | 2026-10-13T06:07Z |
| sni-a5r1-1013b | ubuntu3 | 75 | 2026-10-13T06:08Z |
| sni-a5r1-1013c | ubuntu1 | 75 | 2026-10-13T06:10Z |
| sni-a6-20261012 | ubuntu3 | 76 | 2026-10-12T05:01Z |
| sni-b3-20261012 | ubuntu3 | 75 | 2026-10-12T04:36Z |
| sni-eq-1013a | ubuntu0 | 75 | 2026-10-13T06:07Z |
| sni-rpr-1013b | ubuntu2 | 75 | 2026-10-13T07:04Z |
| sni-rpr-1013c | ubuntu0 | 75 | 2026-10-13T07:05Z |
| sni-s2h1-20261012 | ubuntu1 | 75 | 2026-10-12T05:29Z |
| sni-x1-20261012 | ubuntu3 | 76 | 2026-10-12T05:01Z |

## Runs without a result

These rows have no parseable final line, so they are not DELIVERED.

| run_id | host | rung | rc |
| --- | --- | --- | ---: |
| sni-a1-20261012 | ubuntu0 | EXITED_NO_RESULT | 0 |
| sni-a1r1-20261012 | ubuntu1 | EXITED_NO_RESULT | 0 |
| sni-a1r2-20261013T0336Z | ubuntu1 | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |
| sni-a2-20261012 | ubuntu1 | EXITED_NO_RESULT | 0 |
| sni-a2r1-20261012 | ubuntu0 | EXITED_NO_RESULT | 0 |
| sni-a2r2-20261013T0336Z | ubuntu3 | EXITED_NO_RESULT | 0 |
| sni-a3-20261012 | ubuntu2 | EXITED_NO_RESULT | 0 |
| sni-a3r1-20261013T0215Z | ubuntu0 | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |
| sni-a3r1-20261013T0230Z | ubuntu0 | EXITED_NO_RESULT | 0 |
| sni-a4-20261012-r2 | ubuntu0 | EXITED_NO_RESULT | 0 |
| sni-a4r1b-20261012 | ubuntu2 | EXITED_NO_RESULT | 0 |
| sni-a5-20261012 | ubuntu0 | EXITED_NO_RESULT | 0 |
| sni-a6-20261012-r2 | ubuntu0 | EXITED_NO_RESULT | 0 |
| sni-a7-20261012 | ubuntu2 | EXITED_NO_RESULT | 0 |
| sni-a8-20261013T0302Z | ubuntu0 | EXITED_NO_RESULT | 0 |
| sni-b1-20261012 | ubuntu1 | EXITED_NO_RESULT | 0 |
| sni-b2-20261012 | ubuntu2 | EXITED_NO_RESULT | 0 |
| sni-b3-20261012-r2 | ubuntu1 | EXITED_NO_RESULT | 0 |
| sni-b4-20261012 | ubuntu0 | EXITED_NO_RESULT | 0 |
| sni-rpr-1013a | ubuntu3 | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |
| sni-s0d-20261013T0302Z | ubuntu3 | EXITED_NO_RESULT | 0 |
| sni-s1h1-20261012 | ubuntu0 | EXITED_NO_RESULT | 0 |
| sni-s1h2-20261013T0336Z | ubuntu0 | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |
| sni-s2h1b-20261012 | ubuntu2 | EXITED_NO_RESULT | 0 |
| sni-x1-20261012-r2 | ubuntu1 | EXITED_NO_RESULT | 0 |
| sni-x2-20261012 | ubuntu2 | EXITED_NO_RESULT | 0 |
| sni-x3-20261012 | ubuntu1 | EXITED_NO_RESULT | 0 |
| sni-x4-20261013T0335Z | ubuntu1 | EXITED_NO_RESULT | 0 |
| sni-x5-20261013T0335Z | ubuntu2 | EXITED_NONZERO | 1 |

## Integration gaps

INT1 cherry-picks for which the seat holds no local launcher receipt. No run row is fabricated for them.

- `12eade4b` — S2 v1.1 reprint. Cherry-picked into INT1 (PR 9120, unmerged at capture). The seat holds no local launcher receipt. No run row is fabricated for this commit.
- `5f09242e` — S2 v1.1 repair X2-01..08, A7-F1/F2/F5. Cherry-picked into INT1 (PR 9120, unmerged at capture). The seat holds no local launcher receipt. No run row is fabricated for this commit.

## Bounds

- Orchestrator-native work is not covered.
- Lanes launched by other seats are not covered.
- Launcher receipts captured at 2026-10-13T09:33Z are the only source.
- Rows past DELIVERED need the PR merge receipts, which come later.
- INT1 PR 9120 was open with CI running at capture and was not merged.
- INT1 cherry-pick shas will not exist on main after a squash merge.
- A lane_claim of PASS or PARTIAL is the lane's own printed claim, not program closeout.
- No row in this ledger is at CI, MERGED, PRODUCTION_PROOF, or ACCEPTANCE.
- This draft consumes owner-supplied receipt values. It does not mint issuer or security identifiers.
- This module does not feed a ranker, gate, sizer, escalation, or trade path.
