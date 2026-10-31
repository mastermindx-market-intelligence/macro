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
  - DEC:LEADERSHIP-ROTATION-PREREG-V2-NOISE-REFERENCED-H1
landmines:
  - "Three objects are never substitutable: group_measurement, transition_observation, research_estimate."
  - "Reconstructed coordinates carry mode='reconstructed_price_history' and naturally_observed=false; never attached to an original event as if recorded then."
  - "Relative wealth is (1+R_g)/(1+R_b)-1, not R_g-R_b; breadth bounds [k/N,(k+N-n)/N] are identification bounds, not CIs; unmeasured != zero != ranked."
  - "Never invoke the real rotation builder merely because it accepts a scratch art_dir (acceptance case A39)."
  - "No rotation x cycle confluence, no LLM detection, no connect-flow gating, no parallel schedule (DNR)."
do_not_redo:
  - "#8470 merged (bb7847a3): accepted; Trend Persistence C2 closed; Flow Observatory V2 complete."
  - "Wave 1 MERGED+LANDED: #9240 (1b43a994), #9224 (6f566dbd), #9225 (3af7a7be), records #9245, heal #9288 (152f5018)."
  - "Wave 2 MERGED+LANDED: #9251 T10 prereg V1 (68fc4170), #9250 T07 (77896be1), #9258 T09 (86138988), #9293 T11-T14 harness (f1d83479), prereg V2 #9327 (6e056dc6), fleet heal #9332 (de5587f5), T20 counter-cases #9345 (40568df0)."
  - "Wave 3 MERGED+LANDED: #9257 T17 (9ab95cb6), #9271 T18 (3e4d7560), Terminal #1000 (87004fe4 on master)."
  - "Challenge repair packets MERGED+LANDED 2026-10-14: A #9371 (422012b5), B #9372 (0c38aafe), C #9368 (56ea4f18, CI-authority), Terminal D #1003 (73a935e0 on master) with VPS PRODUCTION_PROOF 18:52Z (served data-dpl-id at app.mastermind-x.com/terminal)."
  - "H1 scientific disposition: P0 DEVELOPMENT_FAIL MIS-SIZED under prereg V1 is a RECORDED result, never re-run to look better; the repair is prereg V2 (noise-referenced surrogate p) + V2.1 clause/class table, then re-size/power under the F9 gate."
  - "Carriers #8412 (replay isolation), #8476 (rs_history.v1), Terminal #881 (journey) are prior drafts: qualify against current main then integrate via programme lanes; never push to their branches."
  - "#8299 / #7976 / #9035 / #7455 are Sol or theme-owner carriers: read-only; their refusals stand. #7060 and #8713 are holds: never arm, ready or merge."
artifacts:
  - research/ROTATION_COMMAND_MASTERPLAN_BY_FABLE.md
  - research/ROTATION_EVENTS_V2_MASTERPLAN_BY_FABLE.md
  - research/SECTOR_ROTATION_CONTINUATION.md
  - research/sector_theme_factor_intelligence/MASTERPLAN.md
waves:
  - id: LR-W1
    title: T01 frontier + T02 source qualification + T03–T05/T08 contract projection + T06 evidence modes + T16 replay isolation
    status: done
    prs: [9224, 9225, 9240, 9245, 9288]
  - id: LR-W2
    title: T07 early-context receipt + T09–T14 science protocol, baselines, adjudications (O3/O4/O5)
    status: done
    prs: [9250, 9251, 9258, 9293, 9327, 9332, 9345]
    depends_on: [LR-W1]
  - id: LR-W3
    title: T17 bounded measured read + T18 journey + T21 asset adoption + T22 access/interface states (O7)
    status: done
    prs: [9257, 9271]
    depends_on: [LR-W1]
  - id: LR-W4
    title: T19/T20/T23 independent challenge + repair packets A–D + independent fabric re-review
    status: done
    prs: [9345, 9368, 9371, 9372]
    depends_on: [LR-W2, LR-W3]
  - id: LR-W5
    title: V2 §2–§6 harness repair (F9 size gate, real look_count, prereg V2.1 clause/class table) + T12R/T13R re-size/power + T26 four-state closeout
    status: done
    prs: [9380, 9386]
    depends_on: [LR-W4]
  - id: LR-W6
    title: Follow-on (outside the 2026-10-13 masterplan T-graph) — prereg V3 re-registering H1/H2/H3 statistics with fresh size/power before any P1 read; T18 natural-consumption proof from the first nightly; T24 conditional issuance chain; T25 operator readback (human gap)
    status: todo
    depends_on: [LR-W5]
    next_action: Author a dated PREREG V3 (own blob pin; never edit V1/V2/V2.1) re-registering the statistics, re-run T12/T13 size+power under it, and only on SIZED+POWERED issue a P1 read. T25 is a human act.
next_action: >
  Masterplan T-graph closed (T26 recorded: MEASURED_PRODUCT_COMPLETE = COMPLETE on main baseline
  38627611213; SCIENTIFIC_DISPOSITION_COMPLETE; PREDICTIVE_CAPABILITY_QUALIFIED = NO;
  ORIGINAL_PROGRAMME_COMPLETE = NOT COMPLETE; repair #9380 → c55b54dab056). Follow-on LR-W6: author
  PREREG V3 re-registering the statistics before any P1 read; T18 natural proof waits on the first
  nightly (never dispatch daily.yml); T25 operator readback is a human act.
---

# Leadership Migration & Sector/Theme Rotation Intelligence

Programme completion seat opened 2026-10-14 under the Chairman's masterplan zip
(`Leadership_Rotation_Fable_Masterplan_2026-10-13.zip`): task graph T01–T26,
eight native Opus domain coordinators (O1–O8) administrating M2 fabric lanes.
T26 reports four separate states — MEASURED_PRODUCT_COMPLETE,
SCIENTIFIC_DISPOSITION_COMPLETE, PREDICTIVE_CAPABILITY_QUALIFIED,
ORIGINAL_PROGRAMME_COMPLETE — and never marks one complete from another.
Continuation homes: Mastermind #1194, macro issue #7646 (Sector Central).
