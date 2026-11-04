---
key: PROPHET-US-ENTRY-TIMING
title: US Prophet structural late-entry diagnosis and reduction
objective: >
  Diagnose and materially reduce structural late-entry behavior in US Prophet without
  unacceptable false-positive cost. Done = a measured entry-timing delta on held-out
  episodes with the false-positive cost printed alongside it.
status: active
program: prophet-us
p0: US_PROPHET_ENTRY_TIMING
repos: [macro]
owner: coo-fable
class: research
blast_radius: reversible
ambiguity: open
owns_paths:
  - engine/prophet_*.py
waves:
  - id: W0
    title: Queue drain + backfill
    status: done
    pr: 5370
  - id: W1
    title: Verify the 22:30Z bake lands clean after backfill
    status: in_progress
    depends_on: [W0]
    next_action: >
      Read the 22:30Z bake log for the first post-backfill run. First-run-bomb law applies:
      a first run after a backfill is not evidence of steady state.
  - id: W2
    title: Entry-timing delta measurement on held-out episodes
    status: todo
    depends_on: [W1]
  - id: W3
    title: Granular 3H/30m pivot observation checklist in the existing Stocks live path
    status: in_progress
    pr: 10715
    next_action: >
      Reconcile the original core and health Fabric runs through their existing
      carrier; integrate verified returns, complete owner-input wiring and source
      CI/release, then prove actual deployed monitoring. Draft source is partial;
      this editorial wave state does not prove a running worker or live service.
landmines:
  - "A first bake after any backfill looks anomalous by construction — do not read run #1 as steady state."
do_not_redo:
  - "Queue drain was root-caused and fixed in #5370 — do not re-diagnose the queue."
artifacts:
  - research/prophet_v4/INTRADAY_PIVOT_CHECKLIST_2026-11-03.md
  - docs/PROPHET_INTRADAY_PIVOT_CHECKLIST.md
  - agentos/handoffs/PROPHET-US-ENTRY-TIMING-2026-11-04-intraday-pivot.md
next_action: >
  Continue the Chairman-assigned W3 addition from PR10715 by reconciling the
  original uncertain core result. Preserve W0 and the existing W1/W2 scientific
  completion contract; granular display work does not satisfy that contract.
---

## Context

One of five active company P0 objectives (`US_PROPHET_ENTRY_TIMING` in Mastermind
`config/strategic_state.yml`). The backfill completed and the queue drained on 2026-08-11;
the open question is whether the first post-backfill bake is clean.


## 2026-11-04 bounded implementation addition

The current Chairman request assigns granular live 3H/30m pivot observations to
W3. Web Sol operation `prophet-us-intraday-pivot-checklist-20261104-c3` owns this
bounded source/delivery addition. The existing owner field is an accountable-seat
record, not evidence of a live session or a historical-author approval gate.

PR10715 contains partial collector, integration and UI implementation with synthetic
proof. The original causal-core and health returns remain unverified; production
monitoring and entry efficacy are not established. The dated handoff and source
plan contain the exact effect custody and next actions. Older waves retain their
existing evidence and acceptance boundaries.
