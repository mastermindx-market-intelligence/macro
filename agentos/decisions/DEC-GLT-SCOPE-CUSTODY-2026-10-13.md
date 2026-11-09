---
key: GLT-SCOPE-CUSTODY-2026-10-13
question: >
  When the Global Liquidity Transmission programme restarts under the 2026-10-13
  Chairman masterplan, what is execution truth for its scope and custody? The
  candidates are: the closed architecture PR Mastermind #117, the stale
  WS:GLOBAL-LIQUIDITY-TRANSMISSION prose, open sibling carriers (#7191, #124), or
  merged source plus the current seat commission.
answer: >
  Merged source plus the seat's current commission is execution truth. Merged source
  means macro #6296, merged 2026-09-04 as 38fd57a676de, and Mastermind #914, merged
  2026-09-22 as 08597860fbce. The commission is the W-LIQ.7 DAG T01-T28 from the
  2026-10-13 masterplan, held by claude-fable-seat-10c41bc9.
  Mastermind #117 closed unmerged and is historical architecture only; it is never
  cited as merged or protected law. The pre-2026-10-13 workstream prose is
  superseded where it contradicts merge metadata.
  The open carriers keep their own custody:
  - #124 stays its original writer's PR. GLT delivery uses only the T02 carve-out,
    the 19 owned paths on fresh master.
  - #7191 is not merged over the refreshed record. Its facts are absorbed with
    attribution.
  - #7245 and #9102 are not GLT-owned.
rationale: >
  Several authored sources disagreed. The workstream said #6296 was "not merged" and
  awaiting Sol review, but GitHub merge metadata shows it merged on 2026-09-04. #117
  reads like a frozen architecture, but it closed unmerged on 2026-09-24. #124 shows
  1,239 changed paths, but 1,220 of them are stale-base master bytes; replaying them
  would revert 304 later master changes. Acting on any of those authored narratives
  would rebuild merged work or ship collateral damage.
  Merge metadata and the current commission are the only sources that are both
  observable and current. Absorbing #7191's facts, rather than overwriting or merging
  its stale-based record, preserves another carrier's work without letting a
  2026-09-16 base clobber 2026-10-13 truth.
alternatives:
  - option: Treat Mastermind #117 as the governing architecture law.
    why_not: >
      It closed unmerged; citing it as law launders an unaccepted document into
      authority. The masterplan package (S04) says the same.
  - option: Merge or rebase macro #7191 first, then refresh on top of it.
    why_not: >
      The commission forbids pushing to #7191. Its branch is based on a 2026-09-16
      tree and is merge-blocked. Its two-file content is absorbed with attribution
      instead, and closing it remains a seat act.
  - option: Merge Mastermind #124 wholesale to land the lab.
    why_not: >
      Its stale base would revert 304 master paths, measured against true merge-base
      8de062fb3b5a. The 19 owned paths are byte-identical in the T02 carve-out.
  - option: Leave the workstream prose as-is and record truth only in the handoff.
    why_not: >
      The workstream record is what every next session reads first. Leaving "not
      merged" and "Sol reviews" there would re-trigger already-settled work.
evidence:
  - "git log -1 38fd57a676de + git merge-base --is-ancestor 38fd57a676de 84e177a2b9b2 (macro main): commit 2026-09-04 W-LIQ.1 producer (#6296), ancestor of main (S05)."
  - "git log -1 08597860fbce + git merge-base --is-ancestor 08597860fbce 28e3c692b3d9 (Mastermind master): commit 2026-09-22 W-LIQ.2 sole reader (#914), ancestor of master (S06)."
  - "gh pr view 117 -R mastermindx-market-intelligence/Mastermind --json state,closedAt: CLOSED 2026-09-24T06:25:54Z, draft head 140b90112f25, mergeCommit null."
  - "gh pr view 124 -R mastermindx-market-intelligence/Mastermind: OPEN DRAFT, head 23f97360131d05123acc440da15780b0bb200e82, branch codex/mas120-wliq3-20260822."
  - "gh pr view 7191 -R mastermindx-market-intelligence/macro: OPEN, labels merge-on-green + merge-blocked, head c8088b8a73a9f85aeae96a1584b76f524d3b4398, files = this workstream + a 2026-09-16 handoff."
  - "gh pr view 7245: OPEN DRAFT, head 6fd11eb40630, files engine/neuralweb/liquidity_plumbing.py + tests/test_liquidity_plumbing.py."
  - "gh pr view 9102: MERGED 2026-10-13T09:39:27Z, head a2767be332e5, mergeCommit a49e7d419ecf."
  - "Mastermind docs/liquidity_lab/MAS120_PR124_SCOPE_DISPOSITION_2026-10-13.md at branch head 8e906193a15e99c9090e3debea9647c7216bf914: 1,239-path census sha256 486b0de58e2d06775c421d747d1fae8238faa660e596dda764c188457e5c5d45; 19 owned paths; 304 would revert."
  - "Procedure pin 252ac93de7696fea861161d4686d6fb47014e6d0 (S01); macro audit pin bb8da347eca15e480a1f423f4905e2a6f452bf62 (S02)."
affects:
  - WS:GLOBAL-LIQUIDITY-TRANSMISSION
  - policy-transmission-intelligence
  - agentos/workstreams/WS-GLOBAL-LIQUIDITY-TRANSMISSION.md
confidence: high
reversibility: easy
decided_by: "seat: claude-fable-seat-10c41bc9 (recorded by GLT W1 ORCH-A under its T01 commission)"
decided_at: 2026-10-13
---

## Note

This is a custody and scope ruling, not a science or release ruling. It gives no
artifact authority, and it does not claim that any producer run, reader consumption
or deployment happened. Reverse it by a later DEC record if a carrier's merge state
changes, for example if #124 is closed or #7191 merges.
