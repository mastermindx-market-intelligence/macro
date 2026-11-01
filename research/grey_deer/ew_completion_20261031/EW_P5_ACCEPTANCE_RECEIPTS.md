# EW-P5 acceptance receipts (seat 00dea969, started 2026-11-01)

Schema: ACCEPTANCE_AND_RELEASE.md §7 (identity, provenance, real checks, independent review, effect claim, held unknowns, rollback).

Rule: a row says only what its primary artifact shows. No pack (S, Q, O, C, U or R) is marked PASS in this file, because EW-P5 has not executed one yet. A later records wave adds pack rows with exact heads and run IDs.

## Merged waves

Every row below reached the MERGED rung. None is PRODUCTION_PROOF or ACCEPTANCE.

| Wave | PR | Reviewed head | Independent review | Merged squash (UTC) | Effect claim | Held unknowns |
|---|---|---|---|---|---|---|
| EW-P0 records and takeover | #10249 | 5db46730 (after the R2 repair) | GD-EW-P0-R2, Fabric, non-author | 1d937d7e2b36 at 2026-10-31T16:09:14Z | Adoption record and handoff on main | None material |
| Records r2 | #10328 | b5b402ff | GD-EW-REC-R3 PASS-WITH-GAPS; the SHA typo was fixed before merge | a46192f7f4dd at 2026-10-31T16:54:21Z | Workstream wave states | None material |
| EW-P2 rotation continuity | #10325 | 697b90ab; review gd-ew-p2-r1 APPROVE on f2532edb, later delta is a main merge plus rig-emitted P0B receipts | Fabric r1 APPROVE | b38935afc1a5 at 2026-10-31T18:29:16Z | Recorder lands default-off; #10104 left open with a pointer | Activation (T2+) has no gate yet; O01-O08 not run |
| CI budget (not a wave) | #10341 | none | Seat-direct CI repair | dbaf1e07bccc at 2026-10-31T20:08:33Z | International job budget 8 to 15 minutes | None |
| EW-P3 forecast prereg (product B) | #10340 | c5f00584 r3 ACCEPT_WITH_FINDINGS, plus the seat sys.path pin 3c986e24 | Fabric r1-r3 | 11e6c98eb8c3 at 2026-10-31T20:37:56Z | Contract v1 blob 5270e309 frozen; prereg registered | Reader NOT_EXECUTABLE until L0 2027-12-31; R01-R08 not run |
| Records r3 (prereg dating) | #10346 | 9e7e9ce490fd | GD-EW-REC3-R1 APPROVE (R1-R9 PASS, ubuntu0, glm-5.3) | f9b070d84100 at 2026-10-31T21:14:36Z | Prereg dated: merge 2026-10-31, start 2026-11-02; two declared_budget rows appended | None |
| EW-P4 descriptive surface (product A) | #10350 | a49a16d52ac2 | gd-ew-p4-r1 REQUEST_CHANGES (F1-F5 repaired), r2 and r3 APPROVE_WITH_NOTES; r3 is on the exact head | 886ab694c947 at 2026-11-01T04:36:16Z | Radar inset and Sector Central observation language, EN/ZH, dark/light, 1280/390/320; 46 shots, receipt source_revision 5bb16bdb | No producer writes latest_observation, so production renders the unavailable state; review notes F-1 to F-3; vision review lane refused |

Real checks for EW-P4 at the exact head: local 539 passed and 2 skipped, node 19/19, contract-delta 0/0, hosted ci-gate, ci-plan and fence-pack SUCCESS. The seat's contact-sheet check passed; it is the seat's own check, not an independent review.

## Open waves

- **EW-P1.** T1 diagnosis is done. T2 is superseded by #10255, which belongs to another owner. Acceptance is two natural nightly `engine: regime update` landings on main after #10255 merges. The seat runs an hourly read-only watcher with a strict match on the carve's own squash subject. Rung today: DELIVERED for the diagnosis; PRODUCTION_PROOF is not recorded.
- **EW-P4 follow-ups.** Tracked as EW-P4-FU in the workstream. They are held unknowns, not regressions.
- **EW-P5 packs.** Run at exact heads:
  - S01-S12 publication and source clocks. These depend on the EW-P1 landings.
  - Q01-Q08 QLedger custody, in the #10079 and #10255 context.
  - O01-O08 recorder behaviour. EW-P2 recording is default-off.
  - C01-C16 consent and outbox. No live send is authorized.
  - U01-U11 EW-P4 UI, EN/ZH by dark/light by desktop/mobile, plus accessibility. A real observation needs an activated producer first.
  - R01-R08 science negatives and prereg reader refusals.

## Rollback (owned mechanisms, per §7.7)

- EW-P2 recorder: the default-off flag; no history rewrite.
- EW-P3: the prereg is immutable and the reader refuses before its window.
- EW-P4: UI only; revert by PR.
- No consent or alert path is live, so no send rollback is needed.

## Release posture (per §8)

This file grants no informational Tier A release, no predictive or trading authority, and no live send. The parent mission stays incomplete until the EW-P1 landings exist and the packs above run with named run IDs.
