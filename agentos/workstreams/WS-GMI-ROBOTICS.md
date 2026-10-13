---
key: GMI-ROBOTICS
title: Robotics Theme Intelligence — implementation carrier (merged, reverted, to re-land)
objective: >
  Re-land the Robotics theme intelligence vertical on main without breaking repo-wide
  import resolution. Done = the #7908 capability re-landed on the accepted #7870 base,
  ci-pack-10 green, served with browser proof, and the Robotics R1 corpus available
  for cross-vertical rights qualification.
status: active
program: gmi-theme-graph
repos: [macro]
owner: fable-meta-ceo
class: build
blast_radius: user_facing
ambiguity: scoped
depends_on:
  - WS:GMI-SEMICONDUCTORS
decisions:
  - DEC:CHAIRMAN-INDUSTRY-INTELLIGENCE-META-CEO-CONSOLIDATION-2026-10-11
landmines:
  - "Robotics is NOT on main. #7908 merged 2026-09-25T07:27Z (70b3c9f1f8f0) and #8013 reverted it at 11:01Z (e5512ef66a74): 11 unresolved first-party imports blocked ci-pack-10 repo-wide. Any record or memory saying Robotics is live is stale."
  - "The revert touched 35 paths at 36efe9c92b96; re-landing is a fresh carrier on the accepted base, not a revert-of-the-revert."
do_not_redo:
  - "Do not re-merge #7908's tree as-is; the import graph it shipped resolves only against #7870's shell, which was not on main."
waves:
  - id: ROB-W1
    title: "First carrier #7908 merged then reverted by #8013"
    status: done
    pr: [7908, 8013]
  - id: ROB-W2
    title: "Re-land on the accepted #7870 base with resolved imports"
    status: todo
    depends_on: [ROB-W1]
    next_action: >
      After #7870 releases: new carrier from the #7908 tree rebased onto main, imports
      resolved against the landed shell, ci-pack-10 green at the exact head, independent
      review, then merge. Packet Robotics-1.
next_action: >
  Hold until WS:GMI-SEMICONDUCTORS SB-W1 releases; ROB-W2 is second in the post-release
  order after Option A. The Robotics R1 corpus also gates Semiconductor rights
  qualification (WS:GMI-SEMICONDUCTORS SB-W3).
---

## Carrier history

- #7908 `claude/ssd-gmi-robotics-impl-17c9f82c-d191559b616f5c67` @d259ec08d58c, merged
  2026-09-25T07:27:34Z as 70b3c9f1f8f0.
- #8013 `claude/robotics-main-heal-import-resolution` @24e97104ac1c, merged
  2026-09-25T11:01:34Z as e5512ef66a74: "Revert #7908: heal main — 11 unresolved
  first-party imports block ci-pack-10 repo-wide".
- Record created at consolidation (2026-10-11).
