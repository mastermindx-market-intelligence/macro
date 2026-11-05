---
workstream: WS:NATIVE-CHART-ENGINE
session: claude/ce-close-1013 (Terminal seat worktree mastermind-chart-engine-3465e2)
model: opus
ended_because: complete
mission: >
  Complete the Native Chart Engine programme end to end (P2-P4 of the 2026-10-11 masterplan):
  the owned Canvas2D engine behind the portable contract, ChartPanel on that contract,
  preserved workflows, production dark launch with a proven one-flag rollback, and the
  acceptance close. Every merged master is deployed through the git-gated build and live-proven.
state_before: >
  At the 2026-10-14 pause, master carried the PR 998 cadence instruments. PR 999 (boundary
  closure), PR 1027 (Q03b protocol v2 instrument), PR 993 (GAPS) and PR 997 (census follow-ups)
  were open. The official v2 receipt was a VALID FAIL on the zoom half.
changed:
  - path: terminal/components/ChartPanel.tsx
    what: >
      PR 999: the forced-lwc fallback is removed, so ?engine=mm mounts the owned engine. There are
      no direct lightweight-charts imports and no .unwrap( calls.
  - path: terminal/bench/chart-engine.cadence.bench.ts
    what: >
      PR 1027: the protocol v2 instrument (no receipt). PR 1028: a harness-only readiness
      retry for the navigation race.
  - path: terminal/lib/__tests__/
    what: >
      PR 993 pins 31 acceptance-ledger rows and fixes 4 defects. PR 997 adds the census
      follow-up tests C01-A01..A03.
  - path: docs/chart-engine-completion/acceptance-ledger.md
    what: >
      The acceptance ledger (102 ACCEPTED / 31 UNRESOLVED / 3 EXCLUDED of 136 rows), generated
      against the final master. Every UNRESOLVED row names its gate.
prs: [999, 1027, 993, 997, 1028, 1036]
verified:
  - claim: Production serves the final master, and the engine selector and rollback behave as ruled.
    command: >
      deploy_verify.sh verify 3e6e9591d21b849227de3633b4322d7d3b0d3b37; live_proof_cases.sh <out> mm 3e6e9591d21b849227de3633b4322d7d3b0d3b37 --probe
    result: >
      VERIFY OK (deployment-id == gitsrc HEAD == served dpl); P01-A01 impl=mm with no
      warning, P01-A02a/b lwc with storage untouched, P01-A03 engineProbe=refuse -> lwc; MERGED allOk = True
  - claim: The ledger's citations resolve against the final master.
    command: python3 -I gen_ledger.py <filled> <repo> 3e6e9591d21b849227de3633b4322d7d3b0d3b37 acceptance-ledger.md --late late.json --final
    result: rows=136, allowlist census = LWC_IMPORT_ALLOWLIST (9), unwrap budget 7, PROBLEMS none
unverified: []
discoveries:
  - DSC:CHART-ENGINE-Q03B-FIRST-WHEEL-IS-RENDERER-IDLE-WAKEUP
  - DSC:CHART-ENGINE-Q03B-V2-FIRST-WHEEL-ELEVATION-PERSISTS-WITH-HEARTBEAT
unresolved:
  - >
    The Q03 zoom half is HELD. The v2 mm receipt is a VALID FAIL (p95 21.655 / p99 42.429 ms against
    <= 20 / <= 33.4), and lwc fails the same budgets. The P03 default flip (branch
    claude/ce-p03-1013 @ 9576169f9) and P04 LWC retirement stay held.
  - >
    lightweight-charts attribution: attributionLogo is false at 7 mount sites, and the app has no
    NOTICE text or tradingview.com link. This needs a licence-owner decision.
  - >
    ChartPanel still reaches LWC types through lib/chartTimeAxis (TickMarkType) and
    lib/sessionShading (ISeriesPrimitive). P04 must cut both.
next_actions:
  - >
    The Chairman decides whether to commission a prospective Q03b protocol v3 with a new
    falsifiable diagnosis: a stage breakdown of the first wheel, and per-frame mm zoom cost at equal
    phase. The budgets and workload stay fixed. Only a passing v3 mm receipt releases P03.
  - >
    If P03 is released, rebase claude/ce-p03-1013 onto master, recapture the ChartPanel evidence
    crops, ship it through the standing chain, and keep lwc selectable for at least one release
    before P04.
do_not_redo:
  - >
    The v1 and v2 official receipts are adjudicated VALID FAILs. Never re-run them or amend them
    after the result (D10).
  - >
    PRs 969-999, 1027, 993, 997 and 1028 are merged, deployed and live-proven. Do not
    re-run their lanes.
danger_areas:
  - >
    master is strictly protected, so every merge puts the other armed PRs BEHIND. A controller
    bot refresh holds the pull_request run as action_required; approve it only on your own head.
    Refreshing with your own token (PUT pulls/<n>/update-branch with expected_head_sha) creates a
    run that is not held.
---

## §0 State — what is true right now

Production serves master `3e6e9591d21b`. The owned Canvas2D engine ("mm") is opt-in via
`?engine=mm` or `mm.engine`, and lwc is the default. Both rollback paths are re-proven at every
deploy. The acceptance ledger is closed at 102 ACCEPTED / 31 UNRESOLVED / 3 EXCLUDED of 136
rows, with each UNRESOLVED row gated.

## §1 What is LEFT — in order

1. The Chairman's v3 decision for the Q03 zoom half (see next_actions).
2. P03 default flip, then P04 LWC retirement, at least one release later.

## §2 What will bite you

ChartPanel edits need the three evidence-packet recaptures on a Mac. Official bench receipts
need load1 < 24 on the reference M2 Studio.

## §3 What was decided and found

The two first-wheel DSC records above, plus DEC:CHART-ENGINE-Q03B-PROTOCOL-V2-WALL-CLOCK-INPUT.

## §4 Not in scope — do not adopt

Options-suite LWC consumers and the native app shells stay on lwc by ruling D9.
