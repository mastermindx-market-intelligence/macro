---
key: SECTOR-INTELLIGENCE-COMPLETION
title: Sector Intelligence + Sector Cycles completion — backend, editable Paper design, both Macro surfaces, production proof
objective: >
  Finish macro #7646 (operation sector-central-redesign-20260921-sol-001) end to end: complete the
  backend contracts (B01–B12), complete the actual editable Paper design including a full Sector
  Cycles workspace, replace both /sector_central.html and /sector_cycles.html with the accepted
  design while retaining every mapped capability and unique engine, and prove one complete user
  investigation on production plus the next natural scheduled update. Done means backend, Paper,
  Macro implementation, normal release, operational consumption and scientific disposition each
  carry their own accepted evidence across journeys J01–J15 and the 134-row capability matrix.
status: active
program: sector-rotation-intelligence
repos: [macro, mastermind]
owner: meta-ceo-fable
class: build
blast_radius: user_facing
ambiguity: scoped
owns_paths:
  - research/sector_completion_20261021/
  - agentos/handoffs/SECTOR-INTELLIGENCE-COMPLETION-
depends_on:
  - WS:LEADERSHIP-ROTATION-INTELLIGENCE
decisions:
  - DEC:SOL-HOLD-IS-A-MERGE-BARRIER
landmines:
  - "Candidate 4fd82658 lives on local-only sol/web-sector-central-macro-paper-pivot-20261020-sol-001 (Studio workspace); never touch that branch — it is an ancestor of the PR branch via --no-ff merge 3d8d14ac."
  - "Studio managed publisher is NOT_APPLIED for this carrier and reconciles against PR #9917; never re-publish the candidate. Terminal #1055 is closed unmerged; never revive it."
  - "Scientific fences: hazard 4/6 qualified with up/3m and up/6m PRIOR; sizing multipliers 1.0; lead-lag STOP; nightly is the sole advancer (never dispatch daily.yml); grader ~0.274 is a conditional hit rate, never a win rate."
  - "Paper file 01M2WGNCX9475G79JRKJTCM08P: one admitted writer; record only node ids the tool returned; page p-Z-0 is an archive to preserve; the Oct 18 design packet is unadmitted."
  - "Donor lane trees under ~/lanes/wt/<run> are sparse cone checkouts; a lane that needs site/ or data/ must sparse-add a directory, never commit a profile change."
do_not_redo:
  - "P01–P03 ACCEPTED: merge 3d8d14acdc8de99fa2c17316aa22de6177364dbc (parents e5dd30c6 + 4fd82658) pushed; draft PR #9917 opened against main; packing test funded; non-site suites green locally."
  - "Reuse Leadership Rotation LR-W1–W5 and the accepted replay/measurement repairs (WS:LEADERSHIP-ROTATION-INTELLIGENCE); do not restart the 26-task plan."
artifacts:
  - research/sector_completion_20261021/LAUNCH_BRIEF_2026-10-21.md
  - research/sector_completion_20261021/MASTERPLAN_2026-10-21.md
  - research/sector_completion_20261021/CAPABILITY_MATRIX_2026-10-21.csv
  - research/sector_completion_20261021/CONTINUATION_HANDOFF_2026-10-21.md
waves:
  - id: P01-P03
    title: Reconcile custody and the completion contract; carry the candidate onto main
    status: done
    pr: 9917
  - id: P04-P06
    title: Backend packets B01–B12 (generation, membership, metrics, phase age, grader, contracts, adapters, history, engine upgrades)
    status: done
    depends_on: [P01-P03]
    next_action: ""
  - id: P07-P08
    title: Complete editable Paper boards (desktop/mobile, both themes, all states) + dedicated Sector Cycles workspace
    status: done
    depends_on: [P01-P03]
    next_action: "ORCH-PAPER returned PLATFORM_FAILURE r2 (file-wide size warning); seat decision (c): items 2/4/5 + 8 axis cells PAPER_CAPACITY_LIMITED, acceptance via rendered-product browser proof under the Full RIG."
  - id: P09
    title: Genuine design/reference admission and the applicable Full RIG scope record
    status: done
    depends_on: [P07-P08]
    next_action: "RIG sector-intelligence-cycles-20261021 APPROVE_WITH_CONDITIONS at frozen 4161d404 (verdict 9, approval.yml; SIC-APR-01..05 bind the P19-P23 production proof). Reference law only — not a merge, deployment or acceptance."
  - id: P10-P13
    title: One complete Macro investigation (Brief → Rotation → Dossier → Cycles → dated members → stock/Prophet/Research → restored origin)
    status: in_progress
    depends_on: [P04-P06, P07-P08]
    next_action: "Sector Central legs candidate-accepted at P19 (verifiers A/B: 81 of 92 R3A rows CONFIRMED; residuals in proposal.yml p19_p20_dispositions_20261102). The Cycles leg is BLOCKED: no in-shell Cycles workspace exists on HEAD (Verifier C). Complete only after the Cycles build wave lands."
  - id: P14-P18
    title: Lenses, comparisons, history, Cycles depth, watches/saved investigations, compatibility, bounded scientific disposition
    status: in_progress
    depends_on: [P10-P13]
    next_action: "Commission the Cycles build wave (SIC-I03/I09B against the approved design_refs/sector-paper-20261021/cycles_ia.md): rail Explore -> Cycles, Dossier Cycle tab (U07), overdue/phase_v2_age/doctrine_stance/estimate_kinds/series_provenance/hazard parity rendering, C19 MODEL-badge qualification by model_cell_current_claim, typed states, light/ZH/1440/390 cells. Opus orchestrator (ROUTE: ORCHESTRATION) + Fabric/builder lanes; fresh review; never a seat self-merge."
  - id: P19-P20
    title: Independent integrated acceptance and targeted repair
    status: done
    depends_on: [P14-P18]
    next_action: "P19 returns stored byte-exact under research/sector_completion_20261021/p19/ (A 42/46 CONFIRMED, B 39/46, C 0/42 with J04 BLOCKED); 134-row CSV filled; P20 repairs: subsectors.js basket denominator (SC-066), trackBox Measured/已实测 (SIC-APR-04), four sector-paper suites wired into reference-integrity, ceilings funded +9. Fresh READ_ONLY review of the P20 source diff pending."
  - id: P21-P23
    title: Normal release, served user journeys, next natural update or qualified no-change, explicit closeout
    status: in_progress
    depends_on: [P19-P20]
    next_action: "P21 = PARTIAL release only (Sector Central half + CI wiring) after the P20 review and binding CI; squash-merge with --match-head-commit; never described as completion. P22 on both served surfaces after the Cycles wave lands; P23 separate acceptances + matrix *_to_record fill."
next_action: "P20 CI repairs are committed on #9917 (442713973f2a, 8d1fe9324402) and main 838a69c08deb is merged (b6b4743f534d; the inherited gmi-explorer red arrives fixed from main #10541/#10556). Reviewer D (fresh READ_ONLY, receipt p19/verifier_D_P20_source_review.md) returned ACCEPT-WITH-NOTES and its one MAJOR (subsectors.js +3 lines shifted four state-matrix citations) is repaired line-neutral. Next: binding CI green on the new head -> squash-merge #9917 as a PARTIAL release (Sector Central half; the Cycles replacement is NOT DELIVERED) -> commission the Cycles build wave -> P22 production + natural-update proof -> P23 separate acceptances."
---

# Sector Intelligence + Sector Cycles completion

## Why this workstream exists

The Chairman's 2026-10-21 commission continues macro #7646 with a finite masterplan (P01–P23),
fifteen acceptance journeys and a 134-row capability contract. The programme already had a
committed Macro candidate (`4fd82658`) on a local-only Studio branch; the first accepted act of this
workstream carried it forward onto `main` as a `--no-ff` merge so every later packet builds on one
reviewable base (PR #9917).

## Operating shape

- The Fable seat owns direction, dependencies, budgets, adjudication, carrier posts and release
  acts, and is the only writer of the PR branch.
- Two Opus suborchestrators (ROUTE: orchestration, fable-mode, no native children) own "Data and
  engines" (B01–B12) and "Paper and product" (P07–P08); both commission bounded labour on GLM-5.3
  Subagent Fabric lanes and return accepted refs or node ledgers.
- The seat launches the Macro-integration and verification lanes itself and ends with one Opus
  READ_ONLY auditor before P19.

## Evidence standard

A rung on the ladder ACK → QUEUED → START → RUNNING → DELIVERED → CI → MERGED →
PRODUCTION_PROOF → ACCEPTANCE is reported only with its own evidence. A finite negative or
underpowered scientific result completes the research disposition; it never creates a predictor.
