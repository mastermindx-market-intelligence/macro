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
  - "DEC:SUPABASE-MIGRATION-NAMESPACE-TERMINAL-LEDGER-2026-09-06"
discoveries:
  - "DSC:TERMINAL-OPEN-LEDGER-ROW-ON-MASTER-REDS-EVERY-OTHER-PR"
  - "DSC:TERMINAL-HAS-NO-MIGRATION-LEDGER"
waves:
  - id: E01
    title: "Full-universe timeframe technical screening"
    status: awaiting_ci
    pr: 951
    next_action: "Rides landing train 3 at the r1 ACCEPT head a12d3d69b; AC-06 live proof needs the nightly scan producer run after the deploy."
  - id: E02
    title: "Period-aware fundamental screening (fractions; unknown never passes)"
    status: awaiting_ci
    pr: 950
    depends_on: [E01]
    next_action: "Rides landing train 3 at the r2 ACCEPT head 6ef74e292; the first deploy runs the old build script, so bundle scripts/dist/gen_fundamental_scan.mjs once by hand before the AC-06 live proof."
  - id: E03
    title: "Cross-market industry/currency discovery"
    status: awaiting_ci
    pr: 937
    depends_on: [E01]
  - id: E04
    title: "Versioned smart screens (preserve #884)"
    status: done
    pr: [926, 930]
  - id: E05
    title: "Watchlist notes/flags sync (preserve #639)"
    status: in_progress
    pr: 927
    next_action: "Review r2 ACCEPT at 2c9fde9a9. Lands SOLO (migration 0033): apply with receipt, arm only when no train is mid-CI, then the immediate ledger follow-up PR."
  - id: E06
    title: "Multiple indicator instances (layout v2, stable ids)"
    status: done
    pr: [925, 930]
  - id: E07
    title: "Portable study templates"
    status: in_progress
    pr: 954
    depends_on: [E06]
    next_action: "Review r1 ACCEPT at 8435ee53f; rides landing train 4 with E20."
  - id: E08
    title: "Anchored benchmark compare"
    status: awaiting_ci
    pr: 924
  - id: E09
    title: "Chart link groups (extend paneSync; no second bus, #821)"
    status: done
    pr: [920, 930]
  - id: E10
    title: "Time-aware Data Inspector"
    status: awaiting_ci
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
    status: awaiting_ci
    pr: [933, 936]
  - id: E14
    title: "Event planner"
    status: awaiting_ci
    pr: 934
  - id: E15
    title: "Options contract shortlist"
    status: awaiting_ci
    pr: [938, 936]
  - id: E16
    title: "Watchlist review itinerary"
    status: awaiting_ci
    pr: 932
  - id: E17
    title: "Alert dry run (no writes, no notifications)"
    status: awaiting_ci
    pr: [918, 936]
  - id: E18
    title: "Alert bulk pause/resume"
    status: awaiting_ci
    pr: 949
  - id: E19
    title: "Chart capture with provenance + privacy preview"
    status: awaiting_ci
    pr: 952
  - id: E20
    title: "Command palette"
    status: in_progress
    pr: 953
    next_action: "Review r1 REQUEST_CHANGES (focus leaks to the symbol search while the palette is open); repair r1 in flight at the owning agent; review r2 on the pushed head, then landing train 4."
artifacts:
  - "agentos/decisions/DEC-TERMINAL-E20-LANDING-TRAINS-ONE-CI-ONE-SQUASH.md"
  - "agentos/decisions/DEC-TERMINAL-MIGRATION-PR-LANDS-SOLO-WITH-LEDGER-FOLLOWUP.md"
  - "agentos/discoveries/DSC-TERMINAL-OPEN-LEDGER-ROW-ON-MASTER-REDS-EVERY-OTHER-PR.md"
do_not_redo:
  - >
    Do not rebuild a feature that already has an equivalent accepted implementation;
    adopt it or mark the item redundant (package rule).
  - >
    Do not touch the excluded families: Pine, replay, drawing, cache, SSE, options math,
    portfolio currency, deployment repairs, heatmap cap, Copilot evidence, Payoff Lab.
  - >
    Do not add a second chart-sync bus for E09; extend paneSync (Terminal issue 821).
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
next_action: >
  Landing order: train 2 (#936, armed) -> train 3 (E14 E18 E01 E03 E02 E08 E19 E16) ->
  E05 #927 solo with the DDL applied through scripts/supabase_apply.py and the receipt
  posted on the PR -> immediate 0033 ledger follow-up PR -> train 4 (E07 + E20 after its
  repair and review r2). Each squash is deployed with --target-sha and verified live;
  the first deploy carrying E01/E02 needs the scan producers run before their AC-06 live
  proof. Final per-AC report on Terminal issue 916.
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
