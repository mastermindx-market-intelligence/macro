---
key: TERMINAL-ENHANCEMENTS20
title: Terminal 20 feature upgrades (2026-10-11 Web Meta-CEO package)
objective: >
  Deliver the 20 Terminal feature upgrades E01-E20 end to end. Done means every item is
  either merged, deployed through the git-gated terminal-build.sh and verified live on
  app.mastermind-x.com with a per-AC pass/fail/not-run report, a falsifier shown to fail
  and an independent review, or recorded redundant against an accepted equivalent.
status: active
program: terminal-user-services
repos: [terminal]
owner: coo-fable
class: build
blast_radius: user_facing
ambiguity: scoped
decisions:
  - "DEC:TERMINAL-E20-LANDING-TRAINS-ONE-CI-ONE-SQUASH"
  - "DEC:TERMINAL-MIGRATION-PR-LANDS-SOLO-WITH-LEDGER-FOLLOWUP"
  - "DEC:TERMINAL-E2E-SHARD-AT-CAP-SPLITS-NEVER-RAISES"
  - "DEC:TERMINAL-PAGE-SCROLL-LOCK-IS-ONE-REF-COUNTED-LOCK"
  - "DEC:SUPABASE-MIGRATION-NAMESPACE-TERMINAL-LEDGER-2026-09-06"
discoveries:
  - "DSC:TERMINAL-OPEN-LEDGER-ROW-ON-MASTER-REDS-EVERY-OTHER-PR"
  - "DSC:TERMINAL-CONTROLLER-REFRESH-RUN-IS-HELD-FOR-APPROVAL"
  - "DSC:TERMINAL-E2E-CAP-CANCEL-IS-RED-WITHOUT-A-FAILED-TEST"
  - "DSC:TERMINAL-PLAYWRIGHT-RUNS-REWRITE-TRACKED-PROOF-PNGS"
  - "DSC:TERMINAL-HAS-NO-MIGRATION-LEDGER"
waves:
  - id: E01
    title: "Full-universe timeframe technical screening"
    status: awaiting_ci
    pr: [951, 960]
    next_action: "Rides landing train 3 (PR 960, head b22034d78, CI run 38524184229); AC-06 live proof needs the scan producers run after the deploy (e20-seat/recovered/deploy/post_train3_scan.sh)."
  - id: E02
    title: "Period-aware fundamental screening (fractions; unknown never passes)"
    status: awaiting_ci
    pr: [950, 960]
    depends_on: [E01]
    next_action: "Rides landing train 3; if the deployed build script predates it, bundle scripts/dist/gen_fundamental_scan.mjs once by hand before the AC-06 live proof."
  - id: E03
    title: "Cross-market industry/currency discovery"
    status: awaiting_ci
    pr: [937, 960]
    depends_on: [E01]
    next_action: "Rides landing train 3."
  - id: E04
    title: "Versioned smart screens (preserve #884)"
    status: done
    pr: [926, 930]
  - id: E05
    title: "Watchlist notes/flags sync (preserve #639)"
    status: done
    pr: 927
    next_action: "Landed solo at squash 857a5076f with migration 0033 applied under receipt and verified live; the 0033 ledger follow-up is PR 957, riding landing train 3."
  - id: E06
    title: "Multiple indicator instances (layout v2, stable ids)"
    status: done
    pr: [925, 930]
  - id: E07
    title: "Portable study templates"
    status: in_progress
    pr: 954
    depends_on: [E06]
    next_action: "Review r1 ACCEPT at 8435ee53f. After the train 3 squash: merge master into the branch, apply e20-seat/e07/seam.patch (hand-resolve TerminalShell.tsx), recapture its evidence packets on macOS with the playwright webServer env, run the gates, arm auto-merge, deploy, verify live."
  - id: E08
    title: "Anchored benchmark compare"
    status: awaiting_ci
    pr: [924, 960]
    next_action: "Rides landing train 3; its compare series now goes through the lib/chart-engine contract token after the PR 992 fold."
  - id: E09
    title: "Chart link groups (extend paneSync; no second bus, #821)"
    status: done
    pr: [920, 930]
  - id: E10
    title: "Time-aware Data Inspector"
    status: done
    pr: [923, 936]
  - id: E11
    title: "Metric workbench"
    status: done
    pr: [922, 930]
  - id: E12
    title: "Transcript compare"
    status: done
    pr: [919, 930]
  - id: E13
    title: "News catch-up"
    status: done
    pr: [933, 936]
  - id: E14
    title: "Event planner"
    status: awaiting_ci
    pr: [934, 960]
    next_action: "Rides landing train 3."
  - id: E15
    title: "Options contract shortlist"
    status: done
    pr: [938, 936]
  - id: E16
    title: "Watchlist review itinerary"
    status: awaiting_ci
    pr: [932, 960]
    next_action: "Rides landing train 3; the review-rows palette follow-up (e20-seat/e16/e16palette.patch, 7 files, applies cleanly on b22034d78) gets its own PR after the squash."
  - id: E17
    title: "Alert dry run (no writes, no notifications)"
    status: done
    pr: [918, 936]
  - id: E18
    title: "Alert bulk pause/resume"
    status: awaiting_ci
    pr: [949, 960]
    next_action: "Rides landing train 3."
  - id: E19
    title: "Chart capture with provenance + privacy preview"
    status: awaiting_ci
    pr: [952, 960]
    next_action: "Rides landing train 3; captureScene reads the visible range through the chart-engine handle (M01 ratchet repair c7de3686a)."
  - id: E20
    title: "Command palette"
    status: awaiting_ci
    pr: [953, 960]
    next_action: "Rides landing train 3 at its accepted head 27df75b81, together with the chart-pane close repair PR 959 (F04 resize sequence falsified cross-host, accepted at 332944f02)."
artifacts:
  - "agentos/decisions/DEC-TERMINAL-E20-LANDING-TRAINS-ONE-CI-ONE-SQUASH.md"
  - "agentos/decisions/DEC-TERMINAL-MIGRATION-PR-LANDS-SOLO-WITH-LEDGER-FOLLOWUP.md"
  - "agentos/decisions/DEC-TERMINAL-E2E-SHARD-AT-CAP-SPLITS-NEVER-RAISES.md"
  - "agentos/decisions/DEC-TERMINAL-PAGE-SCROLL-LOCK-IS-ONE-REF-COUNTED-LOCK.md"
  - "agentos/discoveries/DSC-TERMINAL-OPEN-LEDGER-ROW-ON-MASTER-REDS-EVERY-OTHER-PR.md"
  - "agentos/discoveries/DSC-TERMINAL-CONTROLLER-REFRESH-RUN-IS-HELD-FOR-APPROVAL.md"
  - "agentos/discoveries/DSC-TERMINAL-E2E-CAP-CANCEL-IS-RED-WITHOUT-A-FAILED-TEST.md"
  - "agentos/discoveries/DSC-TERMINAL-PLAYWRIGHT-RUNS-REWRITE-TRACKED-PROOF-PNGS.md"
  - "agentos/handoffs/WS-TERMINAL-ENHANCEMENTS20-2026-10-14.md"
do_not_redo:
  - >
    Do not rebuild a feature that already has an equivalent accepted implementation;
    adopt it or mark the item redundant (package rule).
  - >
    Do not touch the excluded families: Pine, replay, drawing, cache, SSE, options math,
    portfolio currency, deployment repairs, heatmap cap, Copilot evidence, Payoff Lab.
  - >
    Do not add a second chart-sync bus for E09; extend paneSync (Terminal issue 821).
  - >
    Do not recapture the b-pl-6-batch-1, terminal-visual-intelligence or
    options-level-axis-labels packets again unless a pinned source changes; the locks on
    train 3 head b22034d78 are real captures, and the options-axis failure without the
    playwright webServer env is environmental, not a product defect.
  - >
    Do not redo fold rounds 4-5 of train 3 or the M01/G01 ratchet repair (c7de3686a);
    both are reviewed ACCEPT and bundled at e20-seat/train3/fold5.bundle.
landmines:
  - >
    Builders branch claude/e20-eXX-slug; E02/E03 stack on E01 and E07 on E06. Merge the
    dependency first, then merge master into the stacked PR before arming auto-merge.
  - >
    Supabase DDL prefixes are claimed in supabase/migrations/RESERVATIONS.json; E05 holds
    0033 (0033_watchlist_annotations.sql, additive; its row names PR 927 and stays open
    until the ledger follow-up PR lands after the squash). While that row is open on
    master every other PR's Ingest check is red for a structural reason
    (DSC:TERMINAL-OPEN-LEDGER-ROW-ON-MASTER-REDS-EVERY-OTHER-PR).
  - >
    A capture dev server started without the playwright.config.ts webServer env renders
    the Terminal as an anonymous free-tier guest: the MAX_ANON_IND clamp rewrites the
    seeded indicator set and Option Levels stays gated, which looks like a broken overlay
    with zero console errors. Copy the env block verbatim and remove .next/dev before a
    restart.
  - >
    Any ChartPanel.tsx change rots the three evidence-packet source locks; the fix is a
    real recapture, never a hand-edited hash
    (DSC:TERMINAL-PLAYWRIGHT-RUNS-REWRITE-TRACKED-PROOF-PNGS).
next_action: >
  Landing train 3 (PR 960: E14 E18 E01 E03 E02 E08 E19 E16 E20 plus 963, 957, 959) is
  pushed at b22034d78 with auto-merge and merge-on-green armed; CI run 38524184229 is in
  progress. Then: close the constituents, deploy the squash with --target-sha, run the
  scan producers, verify live and post on Terminal issue 916 (promised to CEO A) ->
  E07 PR 954 refresh with the seam patch and recapture, auto-merge, deploy, verify ->
  E16 review-rows follow-up PR -> close PR 971 once PR 989 lands -> final per-AC report
  on issue 916 -> closing handoff and this record to done. Current frontier detail:
  agentos/handoffs/WS-TERMINAL-ENHANCEMENTS20-2026-10-14.md.
---

## Program record

Source package: `terminal_feature_upgrades_2026-10-11.zip` (20 briefs E01-E20, domain
handoffs OPUS_A-D, exclusions/dependency matrix). Program id
`terminal-enhancements20-20261011-opus`. Assessment and kickoff live on Terminal issue
916 (comment 6106589945).

Domains: A Discovery (E01-E05), B Chart workbench (E06-E10), C Company/event/contract
evidence (E11-E15), D Review/safe actions (E16-E20). First priorities: E01, E02, E04,
E05, E08, E10, E17. Hard dependencies: E02 and E03 need E01's interface; E07 needs E06.

Production identity at kickoff: master caf202fd5 (Terminal 914); production running
34d52545 (Terminal 833). The first program deploy is a descendant and carries 913/914.

Landed so far: train 1 (PR 930, squash 0e8de334d: E04 E06 E09 E11 E12), train 2 (PR 936,
squash 85ad93866: E10 E13 E15 E17), E05 solo (PR 927, squash 857a5076f, migration 0033
applied under receipt). All three are deployed and verified live. Train 3 (PR 960) is
in CI; E07 (PR 954) and the E16 review-rows follow-up land after it.
