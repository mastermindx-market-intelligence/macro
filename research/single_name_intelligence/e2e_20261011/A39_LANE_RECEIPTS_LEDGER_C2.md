# A39 lane receipts ledger — capture 2

Captured at 2026-10-14T07:11Z. Schema version 1. Capture id C2.

## Summary

| rung | count |
| --- | ---: |
| ACK | 0 |
| QUEUED | 0 |
| START | 0 |
| RUNNING | 0 |
| NOT_STARTED | 207 |
| RUNNING_OR_UNKNOWN_AT_CAPTURE | 23 |
| EXITED_NO_RESULT | 3 |
| EXITED_NONZERO | 18 |
| DELIVERED | 92 |
| CI | 0 |
| MERGED | 0 |
| PRODUCTION_PROOF | 0 |
| ACCEPTANCE | 0 |

| host | count |
| --- | ---: |
| bm1 | 1 |
| bmb | 2 |
| mb | 6 |
| mini1 | 1 |
| mini3 | 1 |
| ubuntu0 | 84 |
| ubuntu1 | 109 |
| ubuntu2 | 72 |
| ubuntu3 | 67 |

| rc | count |
| --- | ---: |
| 0 | 95 |
| 1 | 17 |
| 124 | 1 |
| 75 | 183 |
| 76 | 1 |
| 78 | 23 |
| empty | 23 |

| model | count |
| --- | ---: |
| cursor-grok-4.6-high-fast | 19 |
| empty | 210 |
| grok-4.6 | 114 |

| signal | count |
| --- | ---: |
| admission | 183 |
| empty | 23 |
| ok | 95 |
| other | 41 |
| timeout | 1 |

Rows: 343. integrated_on_main annotated: 54. usage_total_tokens present: 52. combined_with_prior rows: 404 (disjoint=True).

This ledger records launcher receipts for 343 delegated lanes captured at 2026-10-14T07:11Z. Counts at capture: 207 NOT_STARTED, 23 RUNNING_OR_UNKNOWN_AT_CAPTURE, 3 EXITED_NO_RESULT, 18 EXITED_NONZERO, 92 DELIVERED. 54 rows carry an integrated_on_main annotation and stay DELIVERED. A launched lane is not a delivered lane, and a delivered lane is not a merged lane. No row is at CI, MERGED, PRODUCTION_PROOF, or ACCEPTANCE. A status of PASS or PARTIAL is the lane's own printed line. This file does not cover orchestrator-native work, lanes launched by other seats, or events after capture.

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

1. `never_started`: rc in {75, 76, 78} → NOT_STARTED
2. `running_or_unknown`: rc is None and done_at is None → RUNNING_OR_UNKNOWN_AT_CAPTURE
3. `exited_nonzero`: rc in {1, 124} → EXITED_NONZERO
4. `delivered`: rc == 0 and lane, status, lane_head are all present and output_complete is not False → DELIVERED
5. `exited_no_result`: rc == 0 and any of lane, status, lane_head is missing → EXITED_NO_RESULT
6. `capture_ceiling`: always in this ledger → never claim CI, MERGED, PRODUCTION_PROOF, ACCEPTANCE
7. `integrated_annotation`: integrated_on_main is non-empty → annotation only

## Rows

| run_id | host | rc | rung_reached | lane | status | lane_head | integrated_on_main |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| sni-a39-1013a | ubuntu1 | 0 | DELIVERED | A39 | PASS | fbaaf30eaeda | 2e2943ae49c8 |
| sni-l129-1013a | ubuntu2 | 0 | DELIVERED | L129 | PASS | ff4c1fe79902 | 2e2943ae49c8 |
| sni-p03u-1013a | ubuntu0 | 0 | DELIVERED | P03U | PASS | 31defdc9c561 | 2e2943ae49c8 |
| sni-a33-1013a | ubuntu1 | 0 | DELIVERED | A33 | PASS | 16be4922057d | 2e2943ae49c8 |
| sni-cg-1013a | ubuntu0 | 0 | DELIVERED | CG | PARTIAL | 492f4c4455d3 | 2e2943ae49c8 |
| sni-tkx-1013a | ubuntu2 | 0 | DELIVERED | TKX | PARTIAL | 1a2a700fb2e5 | 2e2943ae49c8 |
| sni-clk-1013a | ubuntu0 | 0 | DELIVERED | CLK | PASS | 396e8faddadb | 2e2943ae49c8 |
| sni-idr-1013a | ubuntu2 | 0 | DELIVERED | IDR | PARTIAL | 282c51821ac7 | 2e2943ae49c8 |
| sni-mnz-1013a | ubuntu1 | 0 | DELIVERED | MNZ | PARTIAL | f0ee30a2f179 | 2e2943ae49c8 |
| sni-tbs-1013a | ubuntu1 | 0 | DELIVERED | TBS | PASS | f7b6d0d825c3 | 2e2943ae49c8 |
| sni-dcp-1013a | ubuntu2 | 0 | DELIVERED | DCP | PASS | 210effcbdc78 | 2e2943ae49c8 |
| sni-irp-1013a | ubuntu1 | 0 | DELIVERED | IRP | PARTIAL | 9ab8f68a8b9e | 2e2943ae49c8 |
| sni-lgp-1013a | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-mut1-1013a | ubuntu1 | 124 | EXITED_NONZERO |  |  |  |  |
| sni-mut2-1013a | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-tck-1013a | ubuntu2 | 0 | DELIVERED | TCK | PASS | d1759928f052 | 2e2943ae49c8 |
| sni-lgp-1013b | ubuntu1 | 0 | DELIVERED | LGP | PASS | 23eb3bede433 | 2e2943ae49c8 |
| sni-mut2-1013b | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-mut2-1013c | mb | 78 | NOT_STARTED |  |  |  |  |
| sni-mut2-1013d | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-mut2-1013e | ubuntu1 | 0 | DELIVERED | MUT2 | PASS | b867f6b26c93 | 2e2943ae49c8 |
| sni-mut1a-1013c | ubuntu1 | 0 | DELIVERED | MUT1A | PASS | 83e33a44c6de | 2e2943ae49c8 |
| sni-mut1b-1013c | mini1 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-mut1b-1013d | ubuntu2 | 0 | DELIVERED | MUT1B | PASS | 34866f25152a | 2e2943ae49c8 |
| sni-mut1c-1013c | mini3 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-mut1c-1013d | ubuntu0 | 0 | DELIVERED | MUT1C | PASS | 9df2b1c039a4 | 2e2943ae49c8 |
| sni-clkhd-1013a | ubuntu3 | 0 | DELIVERED | CLKHD | PARTIAL | 01cb004fb84d | 2e2943ae49c8 |
| sni-idrfix-1013a | ubuntu2 | 0 | DELIVERED | IDRFIX | PASS | 403cdf213434 | 2e2943ae49c8 |
| sni-irpg4-1013a | ubuntu0 | 0 | DELIVERED | IRPG4 | PASS | 78b143652b82 | 2e2943ae49c8 |
| sni-mut3a-1013a | ubuntu1 | 0 | DELIVERED | MUT3A | PASS | 394abfb31f27 | 2e2943ae49c8 |
| sni-mut3b-1013a | ubuntu2 | 0 | DELIVERED | MUT3B | PASS | 631fcb8eab01 | 2e2943ae49c8 |
| sni-s1fix-1013a | ubuntu1 | 0 | DELIVERED | S1FIX | PARTIAL | c03492869e27 | 2e2943ae49c8 |
| sni-s2fix-1013a | ubuntu0 | 0 | DELIVERED | S2FIX | PASS | b6ed8848ea44 | 2e2943ae49c8 |
| sni-mut3c-1013a | ubuntu3 | 0 | DELIVERED | MUT3C | PASS | 78d91c506a28 | 2e2943ae49c8 |
| sni-mut4a-1013a | ubuntu0 | 0 | DELIVERED | MUT4A | PASS | 4339611f5d4d | 2e2943ae49c8 |
| sni-mut4b-1013a | ubuntu1 | 0 | DELIVERED | MUT4B | PASS | 3ba552bf9d85 | 2e2943ae49c8 |
| sni-mut4c-1013a | ubuntu2 | 0 | DELIVERED | MUT4C | PASS | bc4cb7901cd4 | 2e2943ae49c8 |
| sni-mut4d-1013a | ubuntu3 | 0 | DELIVERED | MUT4D | PASS | af8479290886 | 2e2943ae49c8 |
| sni-mut4e-1013a | ubuntu0 | 0 | DELIVERED | MUT4E | PASS | 46a989bb0491 | 2e2943ae49c8 |
| sni-mut4f-1013a | ubuntu1 | 0 | DELIVERED | MUT4F | PASS | 409999897cd2 | 2e2943ae49c8 |
| sni-a09jg-1013a | ubuntu2 | 0 | DELIVERED | A09JG | PASS | 13edd5ea505f | 2e2943ae49c8 |
| sni-a20b-1013a | ubuntu3 | 0 | DELIVERED | A20B | PASS | 75ec34b1dbc3 | 2e2943ae49c8 |
| sni-a20f-1013a | ubuntu3 | 0 | DELIVERED | A20F | PASS | 4ff6a894f201 | 2e2943ae49c8 |
| sni-jgmut-1013a | ubuntu2 | 0 | DELIVERED | JGMUT | PASS | 5192768635ea | 2e2943ae49c8 |
| sni-matrix-1013a | ubuntu0 | 0 | DELIVERED | MATRIX | PASS | 179fdda28687 | 2e2943ae49c8 |
| sni-mut5a-1013a | ubuntu0 | 0 | DELIVERED | MUT5A | PASS | d2a073392d34 | 2e2943ae49c8 |
| sni-mut5b-1013a | ubuntu1 | 0 | DELIVERED | MUT5B | PASS | 19bd4f7e7130 | 2e2943ae49c8 |
| sni-mut5c-1013a | ubuntu2 | 0 | DELIVERED | MUT5C | PASS | ef1cdc24d872 | 2e2943ae49c8 |
| sni-mut5d-1013a | ubuntu3 | 0 | DELIVERED | MUT5D | PASS | 228c47bb57f8 | 2e2943ae49c8 |
| sni-mut5e-1013a | ubuntu0 | 0 | DELIVERED | MUT5E | PASS | 019f2a9376db | 2e2943ae49c8 |
| sni-mut5f-1013a | ubuntu1 | 0 | DELIVERED | MUT5F | PASS | 7c08e871ddd2 | 2e2943ae49c8 |
| sni-x7-1013a | ubuntu1 | 0 | DELIVERED | X7 | PASS | 0f7eb7e7cc75 | 2e2943ae49c8 |
| sni-a11g-1013a | ubuntu2 | 0 | DELIVERED | A11G | PASS | 3313b030009d | 2e2943ae49c8 |
| sni-a13g-1013a | ubuntu3 | 0 | DELIVERED | A13G | PASS | 563c05f54c8c | 2e2943ae49c8 |
| sni-cov-1013a | ubuntu2 | 0 | DELIVERED | COV | PASS | dfcf0940201c | 2e2943ae49c8 |
| sni-a01g-1014a | ubuntu0 | 0 | DELIVERED | A01G | PARTIAL | 66acf1ccf314 | 4f303e074e44 |
| sni-a02g-1014a | ubuntu1 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-a03g-1014a | ubuntu2 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-a07g-1014a | ubuntu3 | 76 | NOT_STARTED |  |  |  |  |
| sni-a10g-1014a | ubuntu0 | 0 | DELIVERED | A10G | PASS | dfac33774c13 | 4f303e074e44 |
| sni-a12g-1014a | ubuntu1 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-a14g-1014a | ubuntu2 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-a16g-1014a | ubuntu2 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-a18g-1014a | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a31g-1014a | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a33g-1014a | ubuntu1 | 0 | DELIVERED | A33G | PARTIAL | 1588941a86d3 | 4f303e074e44 |
| sni-behav-1014a | ubuntu1 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-jgfix-1014a | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6a-1014a | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6b-1014a | ubuntu1 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-m6c-1014a | ubuntu2 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-m6d-1014a | ubuntu3 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-m6e-1014a | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6f-1014a | ubuntu1 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-m6g-1014a | ubuntu2 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-m6h-1014a | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014a | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6j-1014a | ubuntu1 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-s2adj-1014a | ubuntu2 | 0 | DELIVERED | S2ADJ | PASS | f08ffbc82a35 | 4f303e074e44 |
| sni-schk2-1014a | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-wire-1014a | ubuntu3 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-a18g-1014b | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-a18g-1014r1 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-a31g-1014b | ubuntu1 | 0 | DELIVERED | A31G | PASS | 4a02858c897a | 4f303e074e44 |
| sni-jgfix-1014b | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-jgfix-1014r1 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6a-1014b | bmb |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-m6a-1014r1 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6e-1014b | bmb |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-m6e-1014r1 | ubuntu1 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-m6h-1014b | bm1 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-m6h-1014r1 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014b | ubuntu1 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-schk2-1014b | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-schk2-1014r1 | ubuntu1 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-a18g-1014r2 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a18g-1014r3 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-a18g-1014r4 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-jgfix-1014r2 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-jgfix-1014r3 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-jgfix-1014r4 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6a-1014r2 | ubuntu1 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-m6h-1014r2 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6h-1014r3 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6h-1014r4 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-jgfix-1014mb1 | mb | 78 | NOT_STARTED |  |  |  |  |
| sni-m6h-1014r5 | ubuntu3 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-a18g-1014mb1 | mb | 78 | NOT_STARTED |  |  |  |  |
| sni-m6h-1014mb1 | mb | 78 | NOT_STARTED |  |  |  |  |
| sni-a18g-1014s1 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-jgfix-1014s1 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6h-1014s1 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-a18g-1014s2 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-jgfix-1014s2 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6h-1014s2 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a18g-1014s3 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-jgfix-1014s3 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-jgfix-1014s4 | ubuntu1 | 1 | EXITED_NONZERO |  |  |  |  |
| sni-m6h-1014s3 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6h-1014s4 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a18g-1014s4 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-a02g-1014g1 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-a02g-1014g2 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a07g-1014g1 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a07g-1014g2 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a07g-1014g3 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-a12g-1014g1 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-a12g-1014g2 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a12g-1014g3 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a12g-1014g4 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-a14g-1014g1 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a16g-1014g1 | ubuntu1 | 0 | DELIVERED | A16G | PASS | 7818db4a2f49 | dd59d1320d0a |
| sni-behav-1014g1 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-behav-1014g2 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-jgfix-1014g1 | ubuntu1 | 0 | DELIVERED | JGFIX | PASS | 2f8b6eded825 | dd59d1320d0a |
| sni-m6d-1014g1 | ubuntu1 | 0 | DELIVERED | M6D | PASS | ff31a0ca5457 |  |
| sni-m6i-1014g1 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014g2 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-schk2-1014g1 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-schk2-1014g2 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-a02g-1014g3 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a02g-1014g4 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-a14g-1014g2 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a14g-1014g3 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-a14g-1014g4 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-a18g-1014g1 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-a18g-1014g2 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6a-1014g1 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6a-1014g2 | ubuntu1 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-m6b-1014g1 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6b-1014g2 | ubuntu3 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-m6c-1014g1 | ubuntu3 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-m6e-1014g1 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6e-1014g2 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6f-1014g1 | ubuntu1 | 0 | DELIVERED | M6F | PASS | 4a42b61221b4 |  |
| sni-m6g-1014g1 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6g-1014g2 | ubuntu3 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-m6h-1014g1 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014g3 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014g4 | ubuntu3 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-m6j-1014g1 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6e-1014g3 | ubuntu2 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-m6h-1014g2 | ubuntu2 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-a12g-1014g5 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-a14g-1014g5 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6a-1014m1 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6a-1014m2 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6a-1014m3 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6a-1014m4 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6b-1014m1 | ubuntu1 | 0 | DELIVERED | M6B | PASS | 8023e02bb4a3 |  |
| sni-m6c-1014m1 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6c-1014m2 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6c-1014m3 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6c-1014m4 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6e-1014m1 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6e-1014m2 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6e-1014m3 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6g-1014m1 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6g-1014m2 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6g-1014m3 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6h-1014m1 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6h-1014m2 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m1 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m2 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m3 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m4 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6e-1014m4 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6g-1014m4 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6h-1014m3 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6h-1014m4 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-schk2-1014g3 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-a07g-1014g4 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-behav-1014g3 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6a-1014m5 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6a-1014m6 | ubuntu1 | 0 | DELIVERED | M6A | PASS | 40016dd4d256 |  |
| sni-m6c-1014m5 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6c-1014m6 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6c-1014m7 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6c-1014m8 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6e-1014m5 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6e-1014m6 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6e-1014m7 | ubuntu1 | 0 | DELIVERED | M6E | PASS | 7ed7faa284a4 |  |
| sni-m6g-1014m5 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6g-1014m6 | ubuntu1 | 0 | DELIVERED | M6G | PARTIAL | a06bde81d19f |  |
| sni-m6h-1014m5 | ubuntu1 | 0 | DELIVERED | M6H | PASS | 1c99f6c64cb0 |  |
| sni-m6i-1014m5 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m6 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m7 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m8 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-a02g-1014g5 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m10 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m9 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6c-1014m10 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6c-1014m11 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6c-1014m12 | ubuntu1 | 0 | DELIVERED | M6C | PARTIAL | 02cc9ad23ad2 |  |
| sni-m6c-1014m9 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m11 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m12 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m13 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m14 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m15 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m16 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-a02g-1014g6 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a02g-1014g7 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a02g-1014g8 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-a12g-1014g6 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a12g-1014g7 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a12g-1014g8 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-a14g-1014g6 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a14g-1014g7 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-a14g-1014g8 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-a18g-1014g3 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a18g-1014g4 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-behav-1014g4 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6j-1014g2 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6j-1014g3 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6j-1014g4 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-schk2-1014g4 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m17 | ubuntu2 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m18 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m19 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6i-1014m20 | ubuntu1 | 0 | DELIVERED | M6I | PASS | b871a9cadd4b |  |
| sni-a02g-1014g9 | ubuntu2 | 0 | DELIVERED | A02G | PASS | 4166f47ea6cd |  |
| sni-a07g-1014g5 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a07g-1014g6 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a07g-1014g7 | ubuntu1 | 0 | DELIVERED | A07G | PASS | 0a0752a4abef |  |
| sni-a12g-1014g9 | ubuntu2 | 0 | DELIVERED | A12G | PARTIAL | 64148329058b |  |
| sni-a14g-1014g10 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a14g-1014g9 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a18g-1014g5 | ubuntu2 | 0 | DELIVERED | A18G | PASS | 587f4216b9d4 |  |
| sni-behav-1014g5 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-behav-1014g6 | ubuntu1 | 0 | DELIVERED | BEHAV | PASS | 39c783fd6509 |  |
| sni-m6j-1014g5 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m6j-1014g6 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-schk2-1014g5 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-schk2-1014g6 | ubuntu1 | 0 | DELIVERED | SCHK2 | PASS | d295b3ae0a6f |  |
| sni-a14g-1014g11 | ubuntu1 | 0 | DELIVERED | A14G | PASS | 32a354a68dbc |  |
| sni-m6j-1014g7 | ubuntu1 | 0 | DELIVERED | M6J | PASS | 0c287cb8c409 |  |
| sni-a08g-1014i51 | ubuntu2 | 78 | NOT_STARTED |  |  |  |  |
| sni-a08g-1014i52 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a29b-1014i51 | ubuntu2 | 78 | NOT_STARTED |  |  |  |  |
| sni-a29b-1014i52 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a36g-1014i51 | ubuntu2 | 78 | NOT_STARTED |  |  |  |  |
| sni-a36g-1014i52 | ubuntu0 | 0 | EXITED_NO_RESULT |  |  |  |  |
| sni-compose-1014i51 | ubuntu2 | 78 | NOT_STARTED |  |  |  |  |
| sni-compose-1014i52 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-gfam-1014i51 | ubuntu2 | 78 | NOT_STARTED |  |  |  |  |
| sni-gfam-1014i52 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m7a-1014i51 | ubuntu1 | 78 | NOT_STARTED |  |  |  |  |
| sni-m7a-1014i52 | ubuntu0 | 0 | DELIVERED | M7A | PASS | 7e1d0ab80d99 |  |
| sni-m7b-1014i51 | ubuntu1 | 78 | NOT_STARTED |  |  |  |  |
| sni-m7b-1014i52 | ubuntu0 | 0 | EXITED_NO_RESULT |  |  |  |  |
| sni-m7c-1014i51 | ubuntu1 | 78 | NOT_STARTED |  |  |  |  |
| sni-m7c-1014i52 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m7c-1014i53 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m7d-1014i51 | ubuntu1 | 78 | NOT_STARTED |  |  |  |  |
| sni-m7d-1014i52 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m7d-1014i53 | ubuntu0 | 0 | DELIVERED | M7D | PASS | 8ac0cc5932b1 |  |
| sni-m7e-1014i51 | ubuntu1 | 78 | NOT_STARTED |  |  |  |  |
| sni-m7e-1014i52 | ubuntu0 | 0 | DELIVERED | M7E | PASS | 59157948d94e |  |
| sni-m7f-1014i51 | ubuntu1 | 78 | NOT_STARTED |  |  |  |  |
| sni-m7f-1014i52 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m7g-1014i51 | ubuntu1 | 78 | NOT_STARTED |  |  |  |  |
| sni-m7g-1014i52 | ubuntu0 | 0 | DELIVERED | M7G | PASS | 5277e6690917 |  |
| sni-x8a-1014i51 | mb |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-x8a-1014i52 | ubuntu2 | 78 | NOT_STARTED |  |  |  |  |
| sni-x8b-1014i51 | mb |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-x8c-1014i51 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a04h-1014i51 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a04h-1014i52 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a07p-1014i51 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a07p-1014i52 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a08g-1014i53 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a08g-1014i54 | ubuntu1 | 0 | DELIVERED | A08G | PASS | d27c0d7a335a |  |
| sni-a12p-1014i51 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a12p-1014i52 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a29b-1014i53 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a29b-1014i54 | ubuntu1 | 0 | DELIVERED | A29B | PASS | f7a9904cfbcc |  |
| sni-compose-1014i53 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-compose-1014i54 | ubuntu1 | 0 | DELIVERED | COMPOSE | PASS | f712c183d6af |  |
| sni-gfam-1014i53 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-m7c-1014i54 | ubuntu1 | 0 | EXITED_NO_RESULT |  |  |  |  |
| sni-m7f-1014i53 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-m7f-1014i54 | ubuntu1 | 0 | DELIVERED | M7F | PASS | d58f6bcafa53 |  |
| sni-x8a-1014i53 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-x8a-1014i54 | ubuntu1 | 0 | DELIVERED | X8A | PASS | fa42c8a61cd0 |  |
| sni-x8b-1014i52 | ubuntu2 | 78 | NOT_STARTED |  |  |  |  |
| sni-x8b-1014i53 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-x8c-1014i52 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-x8c-1014i53 | ubuntu1 | 78 | NOT_STARTED |  |  |  |  |
| sni-x8c-1014i54 | ubuntu1 | 0 | DELIVERED | X8C | PASS | bef4201ad254 |  |
| sni-xrep5-1014i51 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a04h-1014i53 | ubuntu2 | 78 | NOT_STARTED |  |  |  |  |
| sni-a04h-1014i54 | ubuntu1 | 0 | DELIVERED | A04H | PASS | 064c952a3ff6 |  |
| sni-a07p-1014i53 | ubuntu2 | 78 | NOT_STARTED |  |  |  |  |
| sni-a07p-1014i54 | ubuntu1 | 75 | NOT_STARTED |  |  |  |  |
| sni-a12p-1014i53 | ubuntu2 | 78 | NOT_STARTED |  |  |  |  |
| sni-a12p-1014i54 | ubuntu1 | 0 | DELIVERED | A12P | PASS | b3ef19875d07 |  |
| sni-gfam-1014i54 | ubuntu1 | 0 | DELIVERED | GFAM | PASS | aebbfdb9595a |  |
| sni-x8b-1014i54 | ubuntu1 | 0 | DELIVERED | X8B | PASS | b76d0c61a8cc |  |
| sni-xrep5-1014i52 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-xrep5-1014i53 | ubuntu1 | 78 | NOT_STARTED |  |  |  |  |
| sni-xrep5-1014i54 | ubuntu1 | 0 | DELIVERED | XREP5 | PASS | 30e7ad4bf06a |  |
| sni-x8arep-1014i61 | ubuntu1 | 0 | DELIVERED | X8AREP | PARTIAL | e820cd9cb525 |  |
| sni-x8crepb-1014i61 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-x8crepb-1014i62 | ubuntu1 | 0 | DELIVERED | X8CREPB | PASS | af271b225edd |  |
| sni-x8crepc-1014i61 | ubuntu1 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-cglrep-1014i61 | ubuntu1 | 0 | DELIVERED | CGLREP | PASS | 402967665a1e |  |
| sni-famj-1014i61 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-x8brep-1014i61 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-x8brep-1014i62 | ubuntu1 | 0 | DELIVERED | X8BREP | PASS | e59f3bba0467 |  |
| sni-famdc-1014i61 | ubuntu1 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-famj-1014i62 | ubuntu1 | 0 | DELIVERED | FAMJ | PARTIAL | 03642767faad |  |
| sni-famvcc-1014i61 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-famvcc-1014i62 | ubuntu1 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-a07p-1014i61 | ubuntu1 | 0 | DELIVERED | A07P | PASS | 5f55aea277bf |  |
| sni-x8arep2-1014i61 | ubuntu1 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-x8brep2-1014i61 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-famj2-1014i61 | ubuntu2 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-x8brep2-1014i62 | ubuntu1 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |
| sni-a20c-1014i61 | ubuntu0 | 75 | NOT_STARTED |  |  |  |  |
| sni-a20c-1014i62 | ubuntu3 | 75 | NOT_STARTED |  |  |  |  |
| sni-a20c-1014i63 | ubuntu1 |  | RUNNING_OR_UNKNOWN_AT_CAPTURE |  |  |  |  |

## Bounds

- Launcher receipts captured at 2026-10-14T07:11Z are the only source.
- Orchestrator-native work is not covered.
- Lanes launched by other seats are not covered.
- Rows past DELIVERED need per-row CI and merge receipts, which this capture does not hold.
- integrated_on_main records a cherry-pick trailer on main and is not acceptance.
- A PASS status is the lane's own claim, judged separately by the seat.
- Usage tokens are absent for non-native launcher modes.
- rc 78 is a launcher admission refusal.
- No row in this ledger is at CI, MERGED, PRODUCTION_PROOF, or ACCEPTANCE.
- This draft consumes owner-supplied receipt values; it does not mint issuer or security identifiers.
- This module does not feed a ranker, gate, sizer, escalation, or trade path.
