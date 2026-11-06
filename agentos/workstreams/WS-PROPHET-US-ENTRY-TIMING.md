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
artifacts:
  - research/signal_engine/BOTTOM_PIVOT_DELIVERY_2026_11_05.md
  - research/evidence/bottom_pivot_delivery_20261105/verification.json
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
landmines:
  - "A first bake after any backfill looks anomalous by construction — do not read run #1 as steady state."
do_not_redo:
  - "Queue drain was root-caused and fixed in #5370 — do not re-diagnose the queue."
next_action: >-
  Continue Chairman-assigned bottom-pivot delivery on PR 10785: qualify source release,
  then authenticated real-path proof and existing research integration. Preserve the
  separate historical W1 bake verification; no wave completion inferred.
---

## Context

One of five active company P0 objectives (`US_PROPHET_ENTRY_TIMING` in Mastermind
`config/strategic_state.yml`). The backfill completed and the queue drained on 2026-08-11;
the open question is whether the first post-backfill bake is clean.


## November 5 Chairman-directed bottom-pivot increment

The active assigned Web principal owns `bottom-pivot-delivery-20261105` / PR10785 and
its continuation, not an archived author session. The source plan and latest dated
handoff describe a built, locally tested evidence/replay/AI-context vertical whose
release, live proof and predictive extension remain incomplete. Existing W0/W1/W2
are not retroactively completed or replaced. No new workstream, runtime, collector,
outcome ledger, ranking or trading authority is created. This source linkage is not
protected-release acceptance.
