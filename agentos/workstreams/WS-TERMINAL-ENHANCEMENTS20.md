---
key: TERMINAL-ENHANCEMENTS20
title: Terminal 20 feature upgrades (2026-10-11 Web Meta-CEO package)
objective: >
  Deliver the 20 Terminal feature upgrades E01-E20 end to end. Done means every item is
  either merged, deployed through the git-gated terminal-build.sh and verified live on
  app.mastermind-x.com with a per-AC pass/fail/not-run report, a falsifier shown to fail
  and an independent review, or recorded redundant against an accepted equivalent.
status: done
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
  - "DSC:TERMINAL-L01A02-CHECKER-DROPS-WRITES-AFTER-A-THEN-CALLBACK"
  - "DSC:BUILD-WRITTEN-IGNORED-FILE-REFUSES-NEXT-TERMINAL-DEPLOY-AT-GATE-ZERO"
  - "DSC:MASSIVE-VX-FINANCIALS-SUNSET-LEAVES-NO-AS-FILED-HISTORY"
  - "DSC:SEC-COMPANYFACTS-KEEPS-EVERY-FILING-OF-A-PERIOD"
waves:
  - id: E01
    title: "Full-universe timeframe technical screening"
    status: done
    pr: [951, 960]
    next_action: "Landed on train 3 (PR 960, squash 98b9e664a, CI run 39138389065 13/13 green), deployed through the git-gated build and verified live 2026-10-18; both scan files are live (complete, 9,209 rows). Technical observed rows appear after the first nightly slice rebuild with the cutoff stamp (21:30Z 2026-10-18)."
  - id: E02
    title: "Period-aware fundamental screening (fractions; unknown never passes)"
    status: done
    pr: [950, 960]
    depends_on: [E01]
    next_action: "Landed on train 3 (PR 960, squash 98b9e664a, CI run 39138389065 13/13 green), deployed through the git-gated build and verified live 2026-10-18; fundamental scan live with 8,901 observed of 9,209 rows (producers run once by hand after the deploy)."
  - id: E03
    title: "Cross-market industry/currency discovery"
    status: done
    pr: [937, 960]
    depends_on: [E01]
    next_action: "Landed on train 3 (PR 960, squash 98b9e664a, CI run 39138389065 13/13 green), deployed through the git-gated build and verified live 2026-10-18."
  - id: E04
    title: "Versioned smart screens (preserve #884)"
    status: done
    pr: [926, 930]
  - id: E05
    title: "Watchlist notes/flags sync (preserve #639)"
    status: done
    pr: 927
    next_action: "Landed solo at squash 857a5076f with migration 0033 applied under receipt and verified live; the 0033 ledger follow-up PR 957 landed on train 3 (squash 98b9e664a); the deployed ledger records 0033 taken and applied."
  - id: E06
    title: "Multiple indicator instances (layout v2, stable ids)"
    status: done
    pr: [925, 930]
  - id: E07
    title: "Portable study templates"
    status: done
    pr: [954, 1053]
    depends_on: [E06]
    next_action: "Landed solo (PR 954, squash 3816d3926) with an E20 x E07 seam e2e. Its first deploy stopped at gate 0 on a missing scan-bundle allowance; PR 1053 (squash 3e0be25bf) added it and shipped through the documented first-adoption path, which deployed master e1c66d0b1 on 2026-10-18; E07 was confirmed live on 2026-10-19 (DSC:BUILD-WRITTEN-IGNORED-FILE-REFUSES-NEXT-TERMINAL-DEPLOY-AT-GATE-ZERO); live 2026-10-19. AC-03's signed-in two-device leg on production is an operator step, because the seat never signs in; the two-context fixture e2e passes."
  - id: E08
    title: "Anchored benchmark compare"
    status: done
    pr: [924, 960]
    next_action: "Landed on train 3 (PR 960, squash 98b9e664a, CI run 39138389065 13/13 green), deployed through the git-gated build and verified live 2026-10-18."
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
    pr: [922, 930, 1067, 1074]
    next_action: "Landed on train 1. AC-03 restatement lineage: Massive vX financials answer 410 since 2026-10-09 and v1 keeps one row per period (DSC:MASSIVE-VX-FINANCIALS-SUNSET-LEAVES-NO-AS-FILED-HISTORY), so PR 1067 stamps statement columns from SEC companyfacts (ingest/annotate_sec_lineage.py, run by nightly_fund.sh after gen_fund_us.py with warn-and-continue; DSC:SEC-COMPANYFACTS-KEEPS-EVERY-FILING-OF-A-PERIOD). Landed on train 6 (PR 1074, squash d943b0c12). Production probe 2026-10-31 after the 2026-10-30 nightly: 8/10 mega-caps stamped from sec_companyfacts, 63 columns, 2 restated; AC-03 is pass."
  - id: E12
    title: "Transcript compare"
    status: done
    pr: [919, 930, 1071, 1074]
    next_action: "Landed on train 1. The slow-connection recovery proposed on issue 916 landed as PR 1071 on train 6 (squash d943b0c12): each transcript-archive request has a named 15 s deadline; a stalled optional ticker index falls back to the committed global archive with a notice and Retry; a stalled commit marker is an error with Retry. Merged green 2026-10-20T06:33Z and inside release 683eea62b; live transcript fallback not re-probed by the seat."
  - id: E13
    title: "News catch-up"
    status: done
    pr: [933, 936]
  - id: E14
    title: "Event planner"
    status: done
    pr: [934, 960]
    next_action: "Landed on train 3 (PR 960, squash 98b9e664a, CI run 39138389065 13/13 green), deployed through the git-gated build and verified live 2026-10-18."
  - id: E15
    title: "Options contract shortlist"
    status: done
    pr: [938, 936]
  - id: E16
    title: "Watchlist review itinerary"
    status: done
    pr: [932, 960, 1052, 1069]
    next_action: "Landed on train 3 (PR 960, squash 98b9e664a), deployed and verified live 2026-10-18. The review-rows palette follow-up PR 1052 landed on train 5 (PR 1069, squash e8a25a202), deployed 2026-10-19 09:59Z; the live probe passed 48 checks at 1440x900, 820x1180 and 390x844 in EN and ZH with no writes and no page errors, after failing on the pre-deploy build."
  - id: E17
    title: "Alert dry run (no writes, no notifications)"
    status: done
    pr: [918, 936, 1060, 1069, 1073, 1074]
    next_action: "Landed on train 2. Follow-ups: the request byte-limit fix PR 1060 (train 5, squash e8a25a202; live unauthenticated and oversize POSTs answer 401) and the duration-independent dry-run recovery PR 1073 (train 6, squash d943b0c12): Cancel settles at once, eligibility is part of the request identity, input changes reset to idle, the input-change cleanup releases only its own request, and there is no client deadline or retry. Merged 2026-10-20 and inside release 683eea62b; unauthenticated dry-run POST answers 401 on 2026-10-31."
  - id: E18
    title: "Alert bulk pause/resume"
    status: done
    pr: [949, 960]
    next_action: "Landed on train 3 (PR 960, squash 98b9e664a, CI run 39138389065 13/13 green), deployed through the git-gated build and verified live 2026-10-18."
  - id: E19
    title: "Chart capture with provenance + privacy preview"
    status: done
    pr: [952, 960]
    next_action: "Landed on train 3 (PR 960, squash 98b9e664a, CI run 39138389065 13/13 green), deployed through the git-gated build and verified live 2026-10-18; live capture probe PASS at 1440x900 and 390x844 with no upload."
  - id: E20
    title: "Command palette"
    status: done
    pr: [953, 960]
    next_action: "Landed on train 3 (PR 960, squash 98b9e664a, CI run 39138389065 13/13 green), deployed through the git-gated build and verified live 2026-10-18, together with the chart-pane close repair PR 959."
artifacts:
  - "agentos/decisions/DEC-TERMINAL-E20-LANDING-TRAINS-ONE-CI-ONE-SQUASH.md"
  - "agentos/decisions/DEC-TERMINAL-MIGRATION-PR-LANDS-SOLO-WITH-LEDGER-FOLLOWUP.md"
  - "agentos/decisions/DEC-TERMINAL-E2E-SHARD-AT-CAP-SPLITS-NEVER-RAISES.md"
  - "agentos/decisions/DEC-TERMINAL-PAGE-SCROLL-LOCK-IS-ONE-REF-COUNTED-LOCK.md"
  - "agentos/discoveries/DSC-TERMINAL-OPEN-LEDGER-ROW-ON-MASTER-REDS-EVERY-OTHER-PR.md"
  - "agentos/discoveries/DSC-TERMINAL-CONTROLLER-REFRESH-RUN-IS-HELD-FOR-APPROVAL.md"
  - "agentos/discoveries/DSC-TERMINAL-E2E-CAP-CANCEL-IS-RED-WITHOUT-A-FAILED-TEST.md"
  - "agentos/discoveries/DSC-TERMINAL-PLAYWRIGHT-RUNS-REWRITE-TRACKED-PROOF-PNGS.md"
  - "agentos/discoveries/DSC-TERMINAL-L01A02-CHECKER-DROPS-WRITES-AFTER-A-THEN-CALLBACK.md"
  - "agentos/discoveries/DSC-BUILD-WRITTEN-IGNORED-FILE-REFUSES-NEXT-TERMINAL-DEPLOY-AT-GATE-ZERO.md"
  - "agentos/discoveries/DSC-MASSIVE-VX-FINANCIALS-SUNSET-LEAVES-NO-AS-FILED-HISTORY.md"
  - "agentos/discoveries/DSC-SEC-COMPANYFACTS-KEEPS-EVERY-FILING-OF-A-PERIOD.md"
  - "agentos/handoffs/WS-TERMINAL-ENHANCEMENTS20-2026-10-14.md"
  - "agentos/handoffs/WS-TERMINAL-ENHANCEMENTS20-2026-10-19.md"
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
    0033 (0033_watchlist_annotations.sql, additive; its row named PR 927 and stayed open
    until the ledger follow-up PR 957 landed on train 3). While such a row is open on
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
  None for the seat. All twenty upgrades are merged and deployed, and the
  per-AC report is on Terminal issue 916 (issuecomment-6538904273). E11 AC-03 is pass on the 2026-10-31 production probe. Five rows stay partial behind
  controls the seat may not pass: E13 AC-06 (a news rights receipt), E14 AC-02 (the
  date-only producer; the spec forbids a new one) and E07 AC-03, E15 AC-06, E18 AC-06
  (signed-in production checks). The closing step for each is in
  agentos/handoffs/WS-TERMINAL-ENHANCEMENTS20-2026-10-19.md.
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
applied under receipt), train 3 (PR 960, squash 98b9e664a: E14 E18 E01 E03 E02 E08 E19
E16 E20, plus the 0033 ledger docs PR 957, the CI shard split PR 963 and the chart-pane
close repair PR 959), E07 solo (PR 954, squash 3816d3926) with the release-preflight
allowance PR 1053 (squash 3e0be25bf, first adoption), train 5 (PR 1069, squash e8a25a202:
1052 E16 review rows, 1060 E17 byte limit, 989 merge-on-green held-run fix) and train 6
(PR 1074, squash d943b0c12: 1071 E12 transcript deadline, 1067 E11 SEC lineage, 1073 E17
dry-run recovery; merged 2026-10-20, carried live by release 683eea62b on 2026-10-25). No PR was opened as train 4. All are deployed; live verification is per the 916 report.
