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
owner: ceo-opus
class: build
blast_radius: user_facing
ambiguity: scoped
waves:
  - id: E01
    title: "Full-universe timeframe technical screening"
    status: in_progress
  - id: E02
    title: "Period-aware fundamental screening (fractions; unknown never passes)"
    status: todo
    depends_on: [E01]
  - id: E03
    title: "Cross-market industry/currency discovery"
    status: todo
    depends_on: [E01]
  - id: E04
    title: "Versioned smart screens (preserve #884)"
    status: in_progress
  - id: E05
    title: "Watchlist notes/flags sync (preserve #639)"
    status: in_progress
  - id: E06
    title: "Multiple indicator instances (layout v2, stable ids)"
    status: in_progress
  - id: E07
    title: "Portable study templates"
    status: todo
    depends_on: [E06]
  - id: E08
    title: "Anchored benchmark compare"
    status: in_progress
  - id: E09
    title: "Chart link groups (extend paneSync; no second bus, #821)"
    status: in_progress
  - id: E10
    title: "Time-aware Data Inspector"
    status: in_progress
  - id: E11
    title: "Metric workbench"
    status: in_progress
  - id: E12
    title: "Transcript compare"
    status: in_progress
  - id: E13
    title: "News catch-up"
    status: todo
  - id: E14
    title: "Event planner"
    status: todo
  - id: E15
    title: "Options contract shortlist"
    status: todo
  - id: E16
    title: "Watchlist review itinerary"
    status: todo
  - id: E17
    title: "Alert dry run (no writes, no notifications)"
    status: in_progress
  - id: E18
    title: "Alert bulk pause/resume"
    status: todo
  - id: E19
    title: "Chart capture with provenance + privacy preview"
    status: todo
  - id: E20
    title: "Command palette"
    status: todo
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
    0029 (watchlist_annotations, additive, unapplied at claim time).
next_action: >
  Program CEO session drives per-feature Opus builders and read-only Opus reviewers;
  arm merge-on-green only after an ACCEPT review at the exact head, then deploy merged
  origin/master with --target-sha and verify live. Kickoff and per-feature PR links are
  on Terminal issue 916.
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
