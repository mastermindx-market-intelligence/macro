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
artifacts:
  - research/prophet_v4/PROPHET_US_ENTRY_TIMING_COMPLETION_BRIEF_2026-10-31.md
  - research/prophet_v4/PROPHET_US_ENTRY_TIMING_SOURCE_CENSUS_2026-10-31.md
  - agentos/handoffs/PROPHET-US-ENTRY-TIMING-2026-10-31.md
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
      Adjudicate the missed August 11 22:30Z bake against the outage disclosure and the
      separate August 12/13 origination controls. Verify later ordinary protected-reader
      delivery and record W1 disposition. Keep reconstructed rows out of prospective W2.
  - id: W2
    title: Entry-timing delta measurement on held-out episodes
    status: todo
    depends_on: [W1]
landmines:
  - "A first bake after any backfill looks anomalous by construction — do not read run #1 as steady state."
do_not_redo:
  - "Queue drain was root-caused and fixed in #5370 — do not re-diagnose the queue."
next_action: >
  Reconcile W1 using the October 31 handoff. In parallel qualify the prospective
  same-read identity and denominator before opening any W2 outcome.
---

## Context

One of five active company P0 objectives (`US_PROPHET_ENTRY_TIMING` in Mastermind
`config/strategic_state.yml`). The backfill completed and the queue drained on 2026-08-11;
the October 31 audit records the missed bake and the later source receipts separately.
