---
key: LEADERSHIP-ROTATION-INTELLIGENCE
title: Leadership Migration & Sector/Theme Rotation Intelligence — programme completion
objective: >
  Complete the existing Rotation Command / Sector Central programme so Mastermind
  explains which sectors, industries and themes are gaining or losing leadership,
  how early that was observable, participation breadth, durability versus false
  start, and what the system knew and displayed at each earlier time. Done means
  the measured US sector journey (map/list/detail/history) is live for real users
  with evidence modes stated, the scientific disposition is recorded with frozen
  protocols, and any predictive claim is separately qualified or explicitly not.
status: active
program: sector-rotation-intelligence
repos: [macro, terminal, mastermind]
owner: meta-ceo-fable
class: build
blast_radius: user_facing
ambiguity: scoped
owns_paths:
  - engine/leadership_rotation_context.py
  - tests/test_leadership_rotation_contract.py
  - tests/test_rotation_evidence_modes.py
  - research/LEADERSHIP_ROTATION_
  - agentos/handoffs/LEADERSHIP-ROTATION-INTELLIGENCE-
depends_on: []
decisions:
  - DEC:SOL-HOLD-IS-A-MERGE-BARRIER
landmines:
  - "Three objects are never substitutable: group_measurement, transition_observation, research_estimate."
  - "Reconstructed coordinates carry mode='reconstructed_price_history' and naturally_observed=false; never attached to an original event as if recorded then."
  - "Relative wealth is (1+R_g)/(1+R_b)-1, not R_g-R_b; breadth bounds [k/N,(k+N-n)/N] are identification bounds, not CIs; unmeasured != zero != ranked."
  - "Never invoke the real rotation builder merely because it accepts a scratch art_dir (acceptance case A39)."
  - "No rotation x cycle confluence, no LLM detection, no connect-flow gating, no parallel schedule (DNR)."
do_not_redo:
  - "#8470 merged (bb7847a3): accepted; Trend Persistence C2 closed; Flow Observatory V2 complete."
  - "Carriers #8412 (replay isolation), #8476 (rs_history.v1), Terminal #881 (journey) are prior drafts: qualify against current main then integrate via programme lanes; never push to their branches."
  - "#8299 / #7976 / #9035 / #7455 are Sol or theme-owner carriers: read-only; their refusals stand. #7060 and #8713 are holds: never arm, ready or merge."
artifacts:
  - research/ROTATION_COMMAND_MASTERPLAN_BY_FABLE.md
  - research/ROTATION_EVENTS_V2_MASTERPLAN_BY_FABLE.md
  - research/SECTOR_ROTATION_CONTINUATION.md
waves:
  - id: LR-W1
    title: T01 frontier + T02 source qualification + T03–T05/T08 contract projection + T06 evidence modes + T16 replay isolation
    status: in_progress
    prs: [9224, 9225, 9240]
    next_action: PRs #9224 (T16), #9225 (T06), #9240 (T03–T05/T08) are READY and armed merge-on-green; on merge blob-verify against origin/main, run ONE main ci.yml baseline over a clear field, close #8412/#8476 as superseded.
  - id: LR-W2
    title: T07 early-context receipt + T09–T14 science protocol, baselines, adjudications (O3/O4/O5)
    status: in_progress
    depends_on: [LR-W1]
  - id: LR-W3
    title: T17 bounded measured read + T18 journey + T21 asset adoption + T22 access/interface states (O7)
    status: in_progress
    depends_on: [LR-W1]
  - id: LR-W4
    title: T19/T20/T23 independent challenge + T24 conditional prospective + T25 release/natural consumption + T26 closeout
    status: todo
    depends_on: [LR-W2, LR-W3]
next_action: >
  Land wave 1 (#9224/#9225/#9240 armed), blob-verify, one main baseline; consume the running
  wave-2 (science) and wave-3 (product) orchestrator returns; then challenge wave (T19/T20/T23),
  T24 conditional, T25 release/natural-consumption proof, T26 four-state closeout.
---

# Leadership Migration & Sector/Theme Rotation Intelligence

Programme completion seat opened 2026-10-14 under the Chairman's masterplan zip
(`Leadership_Rotation_Fable_Masterplan_2026-10-13.zip`): task graph T01–T26,
eight native Opus domain coordinators (O1–O8) administrating M2 fabric lanes.
T26 reports four separate states — MEASURED_PRODUCT_COMPLETE,
SCIENTIFIC_DISPOSITION_COMPLETE, PREDICTIVE_CAPABILITY_QUALIFIED,
ORIGINAL_PROGRAMME_COMPLETE — and never marks one complete from another.
Continuation homes: Mastermind #1194, macro issue #7646 (Sector Central).
