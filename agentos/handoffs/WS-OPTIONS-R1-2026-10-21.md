---
workstream: "WS:OPTIONS-R1"
session: "claude/options-r1 seat (worktree fable-handoff-commission-4c333e, Claude desktop Code tab)"
model: fable
ended_because: ci_handoff
mission: >
  Operator commission 2026-10-21 (FABLE_HANDOFF.md): take "Mastermind Options:
  Rotation, Positioning and Research Continuity" end to end — one continuous journey
  on existing Terminal owners that surpasses GammaPulse — through commit → PR → CI →
  merge-on-green → git-gated VPS deploy → live verification, orchestrating fabric
  lanes for bounded labour and keeping judgment, integration and browser proof on
  the seat.
state_before: >
  No Options R1 record existed. The Terminal carried the nine owners the handoff
  named (Sector Central, Options exposure/structure/volatility/flow desks, the EOD
  belt, the investigation workspace, the alerts engine) with no origin carried from
  Sector Central into Options, no observed book changes, no relative-trend rotation
  method, no evidence continuity for options reads, no per-print inspector, no
  published expected-move band in the volatility comparison and no condition watch
  or review history on saved investigations.
changed:
  - path: terminal (PR 1096, merged 5bf7c6755, deployed)
    what: >
      W1 — Sector Central → holding → "Open options exposure" carries a typed origin
      (roster, method, benchmark, content hash); Exposure shows the origin strip,
      closed-bar snapshot references and Market Memory observed book changes; the
      truthful failure state when a holding's exposure source is unpublished.
  - path: terminal (PR 1103, branch claude/options-r1-w2-term-1021)
    what: >
      W2 — relative-trend rotation map with method switch, axes, trail and receipt;
      holdings coverage line; options evidence continuity on saved investigations
      (migration 0039, claimed in the ledger, applied only through
      scripts/supabase_apply.py with a receipt after the merge).
  - path: macro (PRs 9991 W2B, 9992 W2A)
    what: >
      Producers: scripts/build_sector_holdings_coverage.py and
      engine/rotation_relative_trend.py as curated scope: exclusive legacy jobs with
      measured import closure, ancestor inits and the two lib modules declared. W2B
      also carries the merge of main (both exclusive scopes kept in test_ci_pack.py),
      the G7 shared-nav guard recovery (main has carried the reviewed All-tools host
      since #7949, so the byte-for-byte check strips it from both sides) and each
      job's paths widened with the other producer's hook now imported by
      scripts/build_sector_central.py.
  - path: terminal (#1104 (draft, stacked on `claude/options-r1-w2-term-1021`), branch claude/options-r1-w3-term-1021)
    what: >
      W3 — flow print inspector (W3A), volatility comparison with the published band
      and constant tenor (W3B), condition watches and review history on saved
      investigations with migration 0040 (W3C), the band's method stated beside the
      EOD belt Expected Move cell and in the ChartPanel options-level legend (W3S);
      seat fixes: belt statement wrapping, the inspector card's width in the ≤999px
      strip, the print inspector moved inside the card's scroller, the selected-print
      card at 55% of the column, strip reveal on selection; three sha-locked packets
      recaptured truthfully and the W3 crop packet captured.
verified:
  - claim: W1 journey live on production at 5bf7c6755 (origin strip, snapshot references, observed changes, truthful unpublished state).
    command: "/opt/terminal/terminal-build.sh --target-sha 5bf7c6755 then a signed-in walk in the operator's browser; see terminal/docs/OPTIONS_R1_PROGRAM.md checkpoint"
    result: SERVED; BUILD_ID build-TfctsWXpff2fKS; journey as described in the checkpoint
  - claim: W3 integrated tree gates green.
    command: "cd terminal && npx tsc --noEmit && npx vitest run && node scripts/check_plain_language.mjs; OPTIONS_R1_CROPS=1 npx playwright test e2e/options-r1-w3-crops.spec.ts --project=desktop --workers=1"
    result: "merged-tree gates at 905d76fc0: full vitest 15,281 passed / 3 failed (Node-26-only onboardingOAuthContext) / 4 todo over 908 files with every evidence lock green; tsc 0; eslint no new error against the W2 head on the 41 changed source files; plain-language guard exit 0 (three legacy findings on master's files); the three ChartPanel packets and the W3 crop packet recaptured on the merged tree with pixel accounting in their commits; PR-mode namespace check shows only 0039 OPEN_PR_STATE_STALE until #1103 merges and the row is flipped"
unverified:
  - claim: "W2 (#1103) journey live on production: rotation map, coverage line and an options evidence save that survives a reload."
    what_would_verify: "/opt/terminal/terminal-build.sh --target-sha <1103 squash> after 0039 is applied with a receipt, then a signed-in walk that saves an options read on an investigation and reloads it."
  - claim: "The only red on #1104 ('Ingest + signal-layer tests') is the ledger's OPEN_PR_STATE_STALE finding on 0039, whose row names #1103 as open."
    what_would_verify: "The local PR-mode probe returns exactly [('OPEN_PR_STATE_STALE','0039')]; the context goes green on the stacked head once flip-0039 records the applied row, with no other change."
  - claim: "Macro #9991 goes green after the pushed repair (merge of main, G7 guard recovery, closure widening)."
    what_would_verify: "ci-pack-6 and ci-gate SUCCESS on the pushed head; the controller drops merge-blocked and merges on the merge-on-green label." 
unresolved:
  - "Macro #9991's remote head is still 342c76e55 (conflicting, ci-pack-6 red) until the local merge + G7 guard repair + closure-widening commits are pushed; the G7 defect is main-wide since #7949."
  - Migrations 0039 and 0040 are unapplied; 0040 is claimed for #1104 and must follow 0039, each through scripts/supabase_apply.py with a retained receipt.
  - The W5 integrated live journey proof (Sector Central → holding → expiry/strike → chart → matched change → save → watch → review) has not run on production yet.
next_actions:
  - "On the #1103 merge notice: apply 0039 with its receipt, post and retain the receipt, run flip-0039.py for #1104, deploy the squash with --target-sha and verify an options evidence save live."
  - "Stack-merge master into claude/options-r1-w3-term-1021 with the explicit base 6f1ccb48b (merge-tree --write-tree, commit-tree, reset; never rebase after a recapture), push, mark #1104 ready, add merge-on-green and arm gh pr merge --auto --squash --delete-branch."
  - "After #1104 merges: apply 0040 with a receipt, deploy, verify the belt method line, the volatility band, and watch → review live; run the W5 integrated journey proof; record the outcome here and in terminal/docs/OPTIONS_R1_PROGRAM.md."
  - Push the Macro #9991 repair once its local pack run is green and observe only (label, never native auto-merge).
do_not_redo:
  - The W1–W3 census lanes and the owner maps in the three freeze files.
  - Applying 0039/0040 by any path other than scripts/supabase_apply.py with a receipt, 0040 after 0039.
  - Arming Macro producer PRs with native auto-merge; the merge-on-green label only.
  - Describing a recaptured packet from an RGBA getbbox diff; measure in RGB.
danger_areas:
  - "Macro `main` is unprotected: `gh pr merge --auto` merges at once."
  - Next 16 holds one dev-server lock per project directory; crop tools and Playwright runs in one worktree go one at a time.
  - The primary checkouts (`charting-app`, `Macro Dashboard`) are shared and dirty; never touch their git state — fresh SSD worktrees only.
  - The Mastermind CI wait guard's REDUNDANT POLL is a cooldown: one bounded read at a real boundary, never a sleep/retry loop.
---

## Pointers

- Programme record: `terminal/docs/OPTIONS_R1_PROGRAM.md` (current checkpoint + prior checkpoints).
- Freezes: `terminal/docs/OPTIONS_R1_W1_FREEZE.md`, `_W2_`, `_W3_` (dated amendments at the end of each).
- Crop packets: `terminal/docs/pr-crops/options-r1-w2/`, `options-r1-w3/` (EVIDENCE.yml carries capturedAtHead and the layout-file shas).
