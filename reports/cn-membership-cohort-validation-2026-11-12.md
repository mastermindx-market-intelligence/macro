# CN persisted-membership cohort validation — 2026-11-12

## Result

The two recorded real-store failures reproduce before the repair. The corrected affected suite and existing guard/tenure regressions pass **58 cases, with zero failures, errors, skips or recorded network attempts**.

The committed board contains **7,183 rows**. The old four-category partition accounted for only 5,797 because 1,386 legitimately persisted more-actionable membership rows had no registered category. The repair registers the current producer's exact membership stamp and gives those rows their own partition.

## Actual committed-store partition

| Category | Rows |
|---|---:|
| Prior legacy era | 1,082 |
| Current featured board | 1,013 |
| Superseded headline eras | 240 |
| Parallel Watch cohorts | 3,462 |
| Current visible membership | 1,386 |
| **Total** | **7,183** |
| Unmatched rows | **0** |
| Overlapping rows | **0** |

The actual 297,159-byte Parquet was present, Git-blob verified and read by the existing module fixture. The original and corrected tests did not use the absent-store skip. The source remains byte-identical after execution: Git blob `f33dab5b5c5ff9eb83752764056f92b391f09c20`, SHA256 `3075c1b5e6bce0942d7a2004a0d2eb529df8b124a30ff67f1e9897db4d746bc2`.

## Source correction

A private `_cn_more_actionable_stamp(board_definition)` constructor preserves the existing string construction and is reused at the real append site and in `_cn_known_cohort_stamps()`. The registry resolves the current `china_board_rank.BOARD_DEFINITION` at call time. A separate test partition mask uses the same producer definition.

Membership remains outside `WATCH_DEFINITIONS`, the superseded-era constants and the sequential headline chronology. The emitter already serialized each non-headline cohort separately; the new registration changes only whether the known current membership triggers the unknown-stamp warning. It does not pool records, change grading or rewrite historical rows.

The actual append retains its zero-featured guard, membership-before-featured order, current lane authority and keep-first semantics.

## Native consumer proof

| Suite | Passed cases |
|---|---:|
| `tests/test_cn_track_ledger_eras.py` | 40 |
| Existing more-actionable append guard | 5 |
| Existing CN tenure subset | 13 |
| **Total** | **58** |

Eight new cases establish the distinct behavioral boundaries:

- The registry follows a changed current producer at runtime and rejects an unrelated future stamp.
- The actual emitter serializes current membership as its own `extra_records` block, retains its ticker/date row and `closed=False`, preserves the separate Watch block, and emits no false warning.
- A future `cn_prophet_v999_more_actionable` stamp remains independently visible and emits the line-start unknown-definition warning. A wildcard suffix allowlist would fail.
- The actual tenure adapter includes featured and membership rows while excluding Watch and legacy; the existing demote-to-membership/return-to-featured tenure regression also passes.
- Controlled execution of the exact guarded block in `main()` and its following featured append calls the real `append_board` against isolated temporary storage. It persists membership first, then featured, and the real headline resolver selects the featured definition. Zero featured rows, an unnamed lane and a daily lane produce no stored rows. The pending-replay directory is separately redirected to an empty temporary directory.

The emitter uses deterministic prices and benchmark fixtures with the actual grading/serialization code, explicit non-advancing lane and isolated data/site paths. Its output records and captured warning are retained in JSON evidence. There are 22 emitted consumer artifacts across the existing and added cases. No full nightly, collector, provider, historical replay, production writer or browser action was run.

## Source and execution integrity

Builder preimage `8a5d239cbca2bfa20bea002a738552f0f509ef09`; candidate `d5c05d59518c70e5f7dd8b5899c0b7e8ea5364fc`. Test preimage `4f87b0ce984d9c6b8ffbcc1d1939f5a642a35c1c`; publication candidate `68fd5270b6cdb65866eaa7081299f64b67c2ab7b`.

Native proof used the owner's Python 3.12.13 and declared dependencies, normal conftest and unchanged authority checks. All 1,488 staged source files were verified before and after; only the two intended source files differ. The committed data and staged site had no unexpected changes or new files.

The initial isolated preflight exposed an incomplete source checkout (`engine/confluence_latch.py` was absent). The original preflight terminated before tests; completing the 70-file immutable Python import closure fixed it. Runtime dependencies and repository guards were not bypassed. The subsequent native preflight and both original pytest processes terminated normally.

Root's final self-check corrected one non-executable test comment from `render()` to the actual enclosing function `main()`. The exact single-comment replacement and equal executable AST are recorded separately; the 58 accepted cases were retained without replay. No executable code changed after native qualification.

## Source, custody and CI

Source pin: `e7f8565ca26b74b9ae0d637b336e9985d513ff9d`; receiving main at initial qualification: `5b0c3030c245256f7d9a81597369635e202bbf43`. Their seven changed paths are disjoint from this repair. [Original failure run/job](https://github.com/mastermindx-market-intelligence/macro/actions/runs/43095023859/job/130781492930) · [Owned pickup](https://github.com/mastermindx-market-intelligence/macro/issues/5979#issuecomment-6815226894). The separate membership producer was intentionally introduced in [#6719 / 4327fcd6](https://github.com/mastermindx-market-intelligence/macro/commit/4327fcd6242037edf810412a2f2d082c5d74c9e3).

The retained finite custody qualification covers 605 complete PR inventories and 56 exact head/merge-base comparisons (661 recorded identities). The only three existing builder carriers (#6992, #7696, #10642) change different hunks. Their owners and release/effect holds remain in force. The final publication delta and report-path absence qualification are included in the companion JSON.

The unchanged `unrun-picks-boards` DATA owner already selects this builder, suite and consumer dependencies. Its planning weight is the pinned observed value **245**, not the number of pytest cases. No catalog, selector, installer, timeout, packing limit or controller change is indicated. Ordinary CODE PR checks do not certify execution of this DATA suite.

## Evidence and limits

The companion JSON retains both original failures, all 58 candidate cases, real partition counts, actual emitter documents, warning and append-call records, source/diff/runtime bindings, isolated-preflight reconciliation, comment-only equivalence and finite publication custody.

Native proof SHA256: `7f2f6f156419e967bf62318ffde3db647b19775b63e098691642910fa8cd551f`. Complete input receipt: `8711aefa198d6531f847568c0391e72ba00a04e4e2993c512ef29446e21f9ab8`. Comment-only reconciliation: `ed2c530837c9880a543314580e3a1947450b778ab6dd4b92bf87b67cf78bd413`. CI-scope reasoning: `28e277a67b62d403d02ff8a2e99d78199b86a59fdf7e50118352d5e75de56459`.

This is a bounded cohort-classification repair. It does not close the broader #5979 issue, certify full scheduled DATA health, or release any held CN feature or production/browser obligation. Protected law pin: `c42e812e4a754d7a95efd954441d3f01607a7fb5`.
