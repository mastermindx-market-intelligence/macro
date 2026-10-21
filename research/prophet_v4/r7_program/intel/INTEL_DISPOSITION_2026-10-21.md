# Prophet R7 — Stage 3/4 intelligence disposition (US sleeves)

Orchestrator: ORCH-INTEL (Opus 5.5, ROUTE orchestration, fable-mode), commissioned by Fable seat
69eb9a1c under the Chairman masterplan of 2026-10-20 (Stage 4: Early Leadership, Earnings, Cycle
sleeves, plus the gating Stage 3 units). Base: `e5dd30c6344e4b62a0beba054ac4da97e00bab36`.
Status: DRAFT for the seat. It proposes verdicts and routes. It accepts nothing, removes no
scope, and makes no quantitative claim beyond quoted registered records.

Evidence: two read-only census lanes on the external fabric (glm-5.3), plus targeted checks by
the orchestrator at BASE:
- A = `pro-intel-censusA-20261021-r1`, host ubuntu2, lane commit `1b5114fb32b`, report
  `research/prophet_v4/r7_program/intel/CENSUS_A_EARLY_LEADERSHIP_B4_2026-10-21.md` (lane branch).
- B = `pro-intel-censusB-20261021-r1`, host ubuntu2, lane commit `d166114c595`, report
  `research/prophet_v4/r7_program/intel/CENSUS_B_EARNINGS_CYCLE_LATER_2026-10-21.md` (lane branch).
- PR states were read with one aliased GraphQL query on 2026-10-21 ~03:2xZ/03:3xZ.

Census citations of the form `file:line` are at BASE unless marked as a PR head. The PR heads
#9714 `ed974b3b09` and #9821 `cac29b2909` were not available on the lane host. Content that
exists only on those heads is unread.

## 1. Verdict summary

| Unit | Name | Verdict | Smallest next lane |
|---|---|---|---|
| B04 | Episode evidence dossier | NEEDS-FABLE-DECISION (B04-A custody collision); B04-D BLOCKED-DATA | Ratify the B04-A0/A1 split (F2). Then build lane `pro-intel-b04a0-20261021` (packet written, not launched) |
| B06 | Policy capture, decision-clean labels | BLOCKED-CUSTODY + BLOCKED-DATA | Route to the #8091/#8192 owner: freeze the numeric D06 fields (F4). A source-blind D06 proposal lane is possible after F4 |
| B08 | Comparable event and expectation sources | NEEDS-FABLE-DECISION (Q06 Gate S v0.2 acceptance) | `pro-intel-b08gates-20261021-r1` (launched): acceptance-readiness record |
| B09 | Group history and peer evidence | BLOCKED-DATA + BLOCKED-CUSTODY; depends on B04 | None now. Dated theme history accrues forward-only |
| B10 | Early Leadership research comparisons | BLOCKED-DATA (D07 S3); depends on B06/B09 | Route the write-time `recorded_at` episode writer to the B1 owner (F5) |
| B12 | Genuinely earlier entry | BLOCKED-DATA (no live B4 capture; D02 gated) | Route the B4 runtime wiring to its owner (F5). No study |
| B14 | Earnings research journey | BLOCKED-CUSTODY (#7264) + BLOCKED-DATA (B1 natural clock, Q06 release) | After F1: the incumbent D5 owner wires the comparable field; #7264 owner owns the Lab view |
| B15 | Earnings models, entry, holding | BLOCKED-DATA (no registration; H42 price basis blocked) | None. A prereg draft waits on the corporate-action factor owner |
| B16 | Cycle source-readiness pilot | CLOSED NOT PILOT-READY (R6-B16-01, DO_NOT_REDO); diagnostic BLOCKED-CUSTODY | Repair #7868 per its B1/B2 review (F3). Packet `pro-intel-b16diag-20261021` withheld |
| B17 | Funding and per-share Cycle dossiers | BLOCKED-CUSTODY (#8308, Sol hold) + BLOCKED-DATA | Route to #8308 / Sol (F6) |
| B18 | Failure-inclusive Cycle policy research | BLOCKED-DATA by ruling (R6-B16-01:21) | None. A licensed failure/mapping source is the provider question |
| B19 | Cycle core/add/exit | BLOCKED (B17/B18; D04 Cycle versions; no milestones) | None |
| B24 | Portfolio context across sleeves | BLOCKED (B07/B13/B14/B17 undispatched; D05 DDL human gate) | None |
| B27 | Retained sleeves and instrument roadmap | READY (research only) | `pro-intel-b27-20261021-r1` (launched): disposition draft |

No unit is READY for a build lane at BASE without a seat decision. That conclusion is itself
the main Stage 4 finding (§4).

## 2. Per-unit disposition

### B04 — episode evidence dossier

- **Evidence.**
  - Contract R6-B04-01 is adopted, and amendment R6-B04-01a was ratified by root `01a11e89`
    (`research/prophet_v4/r6_program/rulings/R6-B04-01a_DOSSIER_CONTRACT_AMENDMENT_DRAFT_2026-09-24.md:5`).
  - The amended build order is A → B → C → D (`:361-367`).
  - `agentos/decisions/DEC-PROPHET-US-B04-EVIDENCE-DOSSIER-CONTRACT.md:56` says B04-A "is
    commissioned on the external fabric as the first unit". No B04-A PR exists: a PR search on
    "B04 dossier" finds only the merged records #7850/#7869/#7855 and draft #8004.
  - The wrapper configs (`config/prophet_dossier_reason_map.v1.json`,
    `config/prophet_dossier_lane_families.v1.json`) are absent at BASE (A).
  - Six-case census: 2 COVERED, 2 PARTIAL, 2 BLIND. The blind cases are the missing historical
    event set and the unlicensed-fact rights gate (A §B04).
- **Custody.** The ratified B04-A scope collides with two incumbents:
  - It needs a new route `GET /api/prophet/lab/v1/episodes/{episode_id}/dossier` in
    `app/prophet_lab.py` (`R6-B04-01a:99`). Draft #7264 (claude/, mastermindx-2) edits
    `app/prophet_lab.py` (+258).
  - It needs `IdentityBindingConflict` raised from `_validate_owner_workspace_binding` in
    `engine/prophet_lab/intelligence_vector.py` (`:101-105`). That file is edited by draft #8004
    (claude/ `prophet-p4-d5-identity-binding-20260925`, mastermidx4, idle since 2026-09-25, +13)
    and by #7426 (sol/, held, +97).
  - Ratification sentence (`:5`): "This ruling does not transfer the held #7426/#8004 source
    effects or commission B04-A over them."
- **DO_NOT_REDO.**
  - `agentos/workstreams/WS-PROPHET-US-V4-RECOVERY.md:119-131`: never alias
    `mastermind.live_entry_episode.v1`; use decision-time revision readers only; admission needs
    `source_available_at <= cut AND observed_at <= cut`.
  - D07 S1 ×14 rows each block B04-D (`wave3/D07_EVIDENCE_CLASS_REGISTER_DRAFT_2026-09-24.md:47-60`).
- **Blocking facts.**
  - B04-A collides with the held effects above.
  - B04-D: D07 S1 rows are class null (BLOCKED-DATA).
  - B04-B owes the route-boundary rights gate before any user-facing transcript-derived lane
    (`R6-B04-01a:364`).
- **Verdict.** NEEDS-FABLE-DECISION. See F2: split B04-A into A0 (new module, no collision) and
  A1 (route plus typed identity conflict, after #8004/#7426/#7264 resolve).

### B06 — policy capture and decision-clean labels

- **Evidence.**
  - Grader `engine/us_prophet_grades.py`.
  - The corporate-action adapter returns UNAVAILABLE with blocker
    `complete_point_in_time_security_and_corporate_actions_contract`.
  - The CTVA −86% synthetic mark across a 100→14 discontinuity is unresolved (A §B06,
    PROOF_AND_FRONTIER.md:145-150).
  - The #7751 B4 prereg is merged, with `research/prophet_v4/b4_entry_policy_calibration/PREREG.json`
    in status REGISTERED_OUTCOMES_UNREAD.
  - R20 on the #8091 head says `trial_may_start=false`, with seven gates open. One of them
    (`:98`) reads "numeric D06 worthwhile-gain/tail-harm fields are not frozen". R21 lists 9 gates open.
- **Custody.**
  - "#8192/#8091 retain grading/intake custody" (PROOF_AND_FRONTIER.md:151-152). Both are sol/
    branches and OPEN/ready.
  - #7983 changes the shared grader (OPEN, merge-blocked).
  - #7218 is a HOLD-FOR-SOL draft.
- **DO_NOT_REDO.**
  - KILL-FRESH-TICKS-WINDOW, KILL-STAGE-WIN-GATE and KILL-S10-MARGIN-RECLAIM count as prior
    looks (R6-PREREG-01:30).
  - Do not create a parallel outcome authority (PREREG.json `reuse_law.outcome_store`).
- **Blocking facts.**
  - The corporate-action contract is unavailable.
  - The numeric D06 fields are unfrozen.
  - The QLedger control leg was never populated on 46,630 claims (WS:108-110), so V4 grading is
    not control-matched.
- **Verdict.** BLOCKED-CUSTODY + BLOCKED-DATA. The next act belongs to the #8091/#8192 owner (F4).

### B08 — comparable event and expectation sources

- **Evidence.**
  - `engine/sue.py` has `numeric-sue-compat-v1.1` (`:102`) and `reported_change` (`:339`)
    through `cash_flow_reconciliation` (`:1670`). Code carrier #8189 is MERGED (2026-10-05).
  - The Q06 contract v0.2 (#8069, merged 2026-10-05) records
    `.state = "GATE_S_REPAIRED_PENDING_PARENT_ACCEPTANCE"`, with next action "Parent reviews Gate
    S v0.2".
  - `earnings_semantics_v1/EVIDENCE_BRIEF_AND_PROFITABILITY_2026-09-30.md:157`: "Q06#8069's
    source method remains separately accepted in substance, but its source CI/release is
    unfinished."
  - The capture manifest `.evidence_class.basis = "D07_OPEN_PR_7856_UNMERGED"` is stale: #7856
    MERGED 2026-09-27.
- **Custody.** The factual field belongs to the incumbent Earnings/D5 owner. #8189 was a sol/
  branch. Open #9821 (sol/, mastermindx-2, "revalidate profitability evidence") touches the same
  family; coordinate, never edit.
- **DO_NOT_REDO.**
  - WS:121-131 (revision readers, clock conjunction) and WS:139-142 (no second earnings store).
  - `HOLD-PSQ-TILT-CLOCK` (DO_NOT_REBUILD.md:173).
- **Blocking facts.**
  - Consensus is "Permanently absent" (rights register `:189-193,231`).
  - The D5 allowlist intersects the real event population at exactly one issuer
    (`wave0/C_EARNINGS_D5_READINESS_CENSUS_2026-09-23.md:121`).
  - B1 natural clock: no real B1 episode generation is reachable (`:120`).
  - Nasdaq and Yahoo expectations are "not a source" for model use.
- **Verdict.** NEEDS-FABLE-DECISION on the Gate S acceptance (F1). Production admission stays
  BLOCKED-DATA. Lane `pro-intel-b08gates-20261021-r1` prepares the acceptance-readiness record.

### B09 — group history and peer evidence

- **Evidence.** `engine/group_flow.py` `independent_peer_observation` /
  `independent_peer_continuity` are BUILT_NOT_PROVEN and display-only (A §B09).
- **Custody.** Existing carriers #7455, #7508 and #7604 are all OPEN drafts. #7604 is sol/
  (mastermindx-2). #8240 is the EL evidence carrier (sol/, draft). #9714 (sol/, ready,
  merge-on-green) is unread on host.
- **DO_NOT_REDO.**
  - KILL-PSS-SR2-PEER-DIFFUSION (DNR:83) and KILL-PSS-SR3-PARTICIPATION (:84).
  - KILL-RS-DISPERSION-GATES (:44).
  - HOLD-PSS-RH1/CR1 are prospective-only (:155-156).
- **Blocking facts.**
  - Dated theme-level ex-issuer history is absent. Sector PIT covers only the 11 GICS sectors
    and is not survivorship-free.
  - #7455 current-membership windows are non-PIT (`PROPHET_US_EARLY_LEADERSHIP_R3.md:65`).
  - Depends on B04.
- **Verdict.** BLOCKED-DATA + BLOCKED-CUSTODY. Current theme context is not dated ex-issuer
  evidence. No lane.

### B10 — Early Leadership research comparisons

- **Evidence.**
  - The R3 design is PROPOSED_FOR_OWNER_REVIEW / NOT_REGISTERED.
  - Q03/Q05/Q09/Q10/Q12 are all SPECIFIED_NOT_REGISTERED_OR_DISPATCHED.
- **Custody.** #7772 RQ1 matrix (sol/, draft, updated 2026-10-20 by mastermindx-3, active).
- **DO_NOT_REDO.** The kills above count as prior looks. A missing or unbuilt adapter is never
  zero or neutral (WS:115-118).
- **Blocking facts.**
  - D07 S3 rows: episode registry `null` ("no store generation is pinned for the B10 decision",
    D07 draft:65), and macro-join inputs RETROSPECTIVE (:66).
  - No episode writer stamps `recorded_at` at write time (D07 GAPS:87).
  - R20 gates 1–7 are open.
  - OPUS_SCIENCE_SEAMS_AUDIT:158: "None of D03, D06, D07 or D08 can be closed honestly from the
    current docket."
- **Verdict.** BLOCKED-DATA. Prospective-only once a write-time episode writer exists (F5).

### B12 — genuinely earlier entry

- **Evidence.**
  - `ANCHOR_KINDS` is closed (`turn_watch_reset_low`).
  - D02 is resolved in principle, but admission is gated because Radar `forward.parquet` was
    never committed (B02 census:185-189).
- **Orchestrator check at BASE.** #7581 (`engine/prophet_entry_availability_sources.py`, commit
  `127fd876f1c`) and #7738 (`engine/prophet_entry_policy.py`, `c35013f2d48`) are merged library
  code. `git grep` finds no caller in `scripts/`, `.github/workflows/` or `app/`.
  - So no live B4 prospective capture accrues.
  - R6-PREREG-01:9 "No live B4 runtime" still holds in substance; its "are Draft" wording is stale.
- **DO_NOT_REDO.**
  - KILL-FRESH-TICKS-WINDOW (DNR:126), KILL-STAGE-WIN-GATE (:120) and KILL-S10-MARGIN-RECLAIM (:109).
  - KILL-WASHOUT-TURN (:85).
  - KILL-ROTATION-CYCLE-CONFLUENCE (:43).
- **Blocking facts.**
  - D02/D08 are open.
  - #7734/#7738 constants are uncalibrated (R6-PREREG-01:28).
  - Depends on B02/B05/B06.
- **Verdict.** BLOCKED-DATA. Nothing to study until the B4 runtime accrues natural observations.

### B14 — Earnings research journey

- **Evidence.**
  - `GET /api/prophet/lab/v1/episodes/{episode_id}/earnings` exists (`app/prophet_lab.py:326`),
    projecting `engine/prophet_lab/earnings_dossier.py`.
  - The explanation layer is included (EVIDENCE_BRIEF…:16-18).
  - The handoff `…2026-09-30-earnings-d5-consumer.md` ended blocked.
- **Custody.** #7264 (claude/, mastermindx-2, draft, 2026-10-06) owns the Lab earnings view
  (`engine/prophet_lab/earnings_view.py`, `episode_directory.py`, `app/prophet_lab.py`).
- **DO_NOT_REDO.** WS:117-120: D5 needs B1 canonical episode identity; never alias the Radar
  live episode.
- **Blocking facts.**
  - B1 natural nightly clock (C-census:120).
  - #8069 source release and CI (D5_CONSUMER:54-57).
  - Thesis capture DDL is an EXACT_HUMAN_GATE (SEAT_RULING_R6-D05-01:16).
- **Verdict.** BLOCKED-CUSTODY + BLOCKED-DATA. After F1, the D5 owner wires the comparable field.

### B15 — Earnings models, entry, holding

- **Evidence.**
  - The timing/B15 design (`information_time_research/EARNINGS_TIMING_AND_B15_DESIGN_2026-10-01.md:128-129`)
    says it "is not the missing experiment registration".
  - The public baselines are exploratory only.
- **DO_NOT_REDO.**
  - KILL-OFFHORIZON-VERDICTS (DNR:46).
  - Earnings H42/H21/H63 are "research proposals" with no hold law (CATALOG_V1:49).
  - D04 bans horizon-as-hold inference.
  - Early Leadership entry/hold is not inherited (catalog:45-52; engine tests pin later sleeves
    away from `2_15_SESSIONS`).
- **Blocking facts.**
  - Massive price basis: "H42 absolute or relative return: BLOCKED". Aggregates are unadjusted
    and the corporate-action factor owner is missing (Q06 capture:316-324).
  - Licensed expectations are absent.
  - Q06 Gate E is NOT_REGISTERED.
- **Verdict.** BLOCKED-DATA. No lane.

### B16 — Cycle source-readiness pilot

- **Ruled.** R6-B16-01:21: "no Cycle proving domain is admitted. B16 closes NOT PILOT-READY …
  B18 stays BLOCKED." This is DO_NOT_REDO.
- **Residual: the macro-only diagnostic.**
  - It was admitted by R6-B16-01a:25 once #7843 merged (merged).
  - The v1 prereg is merged (#7847). Its pins were checked with scipy: LB(12,10)=0.5619 passes;
    LB(12,9)=0.4727 fails.
- **Custody.**
  - #7868 (prereg v3, claude/, chriswong6031-creator) has an independent REQUEST_CHANGES "before
    diagnostic execution" (2026-09-27):
    - B1: "N_eff=N and an exact binomial confidence claim are not established" (serial
      dependence, overlapping windows).
    - B2: per-hypothesis support/censoring is inconsistent.
  - #7871 (vintage producer) has REQUEST_CHANGES (2026-10-03).
  - The Q06 manifest records `.held.cycle_pr_7868 = "REQUEST_CHANGES; no run or workaround"`.
- **Rights.** The rule-5 gap is recorded, not resolved. FRED model use is "not a source"
  (register:100). Census M3 storage, model use and redistribution are UNKNOWN (:109-111).
- **Verdict.** B16 CLOSED. The diagnostic run is withheld; its packet was written but not
  launched (§5).

### B17 — funding and per-share Cycle dossiers

- **Evidence.**
  - Nothing exists at BASE.
  - #8308 head `446ffd0f10` (sol/, mastermindxryan, HOLD-FOR-SOL) carries
    `engine/prophet_cycle_equity.py`, which separates business recovery from original-share
    recovery.
  - Milestone fields are not present on #8308 (B §10).
- **DO_NOT_REDO (handoff).**
  - No replacement-security splice.
  - No probability, rank or size from scenario arithmetic.
  - No second capital owner.
- **Blocking facts.**
  - No native `gross_proceeds + issue_price + shares_issued` consumer.
  - No restricted-cash join.
  - No debt/funding rights family in the register.
  - Depends on B16 (closed not-ready).
- **Verdict.** BLOCKED-CUSTODY + BLOCKED-DATA (F6).

### B18 / B19 / B24

- **B18.** BLOCKED by ruling (R6-B16-01:21; R6-D03-01:48: "No Cycle strategy return may be
  computed or cited"). "Six curated exits do not constitute general failure coverage"
  (matrix:75).
- **B19.** BLOCKED.
  - Depends on B05/B17/B18.
  - Inputs need "accepted D04 Cycle entry/hold versions and real source milestones"; none exist.
  - Only B4 may publish entry/add geometry (ARCHITECTURE_FREEZE:420).
- **B24.** BLOCKED.
  - Depends on B07/B13/B14/B17, none dispatched.
  - Portfolio/Risk holds all sizing authority (`engine/prophet_strategy_definition.py:695`;
    ARCHITECTURE_FREEZE:464,652).
  - The D05-c thesis owner waits on the DDL EXACT_HUMAN_GATE.
- None of these three has a lane.

### B27 — retained sleeves and instrument roadmap

- **Evidence.**
  - Five catalog entries carry `definition_status: "SPEC_ONLY_RETAINED_B27"` and
    `horizon_status: "OWNER_SPEC_REQUIRED"` (`engine/prophet_strategy_definition.py:513-676`).
  - No sleeve has a dedicated research doc or module.
  - Per-sleeve kill rows are listed in B §B27.
  - D12 is open.
- **Verdict.** READY for a research-only disposition draft. Lane `pro-intel-b27-20261021-r1`
  proposes; scope removal stays with the true authority (D12).

## 3. Decisions for Fable (recommendation first)

- **F1 — Accept Q06 Gate S v0.2 (unblocks the B08 factual field and B14 wiring).**
  - Recommend ACCEPT if the readiness lane reports verifier exit 0, an unchanged rights blob
    pin, and every prior finding answered.
  - Then open one seat records PR:
    - set the contract state to accepted;
    - replace the manifest's stale D07 basis with the class under the merged #7856 register;
    - correct the "Draft" wording in R6-PREREG-01.
  - Route the factual comparable-revenue field to the incumbent Earnings/D5 owner, coordinating
    with #9821.
  - Gate E stays with Evaluation.
- **F2 — Split B04-A.**
  - Recommend ratifying:
    - **B04-A0:** new-module dossier wrapper, A9 reason map, A12 closed shape, A7 clock split, A8
      projection skeleton, historical-event-set absence, and function-level fixtures. It consumes
      the inner vector read-only and touches neither `app/prophet_lab.py` nor
      `engine/prophet_lab/intelligence_vector.py`.
    - **B04-A1:** route plus `IdentityBindingConflict`, after #8004 lands or closes and #7426 is
      dispositioned by Sol, coordinated with #7264.
  - Ask #8004's owner once to land or close it. Its "bind episode security before issuer
    evidence" fix is A1's precondition.
  - Packet `pro-intel-b04a0-20261021` is written, not launched.
- **F3 — Cycle diagnostic.**
  - Recommend keeping it held and never running v1 (#7847). Doing so is the forbidden
    workaround, and v1 carries the same B1 inference defect.
  - Repair #7868 per B1 (report counted anchors; predeclare a dependence treatment or label the
    inference unestablished) and B2 (explicit required-row/support/censoring sets per H1–H3).
  - Re-review, then run once.
  - #7868 is a claude/ branch idle since 2026-09-27.
  - GitHub read on 2026-10-21 ~03:4xZ:
    - #7868: last commit `3ad50f9d` at 2026-09-24, last update was the 09-27 review.
    - #8004: last commit `f5898f9b` at 2026-09-25, no update since.
    - #7871: last commit 2026-09-24; review 2026-10-03.
  - GitHub idleness is not proof that no local writer exists. If the seat's own custody
    check (Agent OS / live leases) finds no writer, the seat may adopt the #7868 repair as a
    seat lane; otherwise route it to the owner.
  - #7871 is needed only if v3 keeps the full-vintage source.
- **F4 — Numeric D06 fields for H1 (worthwhile gain / tail harm).**
  - D06 is FABLE_AUTHORIZED_TO_RESOLVE.
  - Recommend that the seat commission a source-blind numeric proposal (no outcome reads),
    rule on it, and route the frozen numbers to the #8091/#8192 owner.
  - Definition is not admission.
- **F5 — Prospective-only Early Leadership capture.**
  - Recommend recording that B10/B12 are prospective-only. Route the B4 runtime wiring (a nightly
    caller of the #7581/#7738 library) and the write-time `recorded_at` episode writer to their
    owners.
  - No retrospective study is admissible (D07).
- **F6 — #8308 B17.** Leave it with Sol. Record for Sol that milestones are absent and B19 needs them.
- **F7 — Chairman provider question (Cycle).** Recommend not asking yet. R6-B16-01:25-28 makes it
  not askable until rules 1/4/5 are otherwise satisfiable. FRED model use remains "not a source".
- **F8 — B27 dispositions.** The seat rules on the lane's proposals. Scope removal is not decided
  by this orchestrator (D12).

## 4. Findings

1. Every Stage 4 unit is gated by a held incumbent, a missing source clock, or an open seat
   decision. The cheapest unlocks are two seat decisions (F1 and F2), not new research.
2. Two recorded premises are stale at BASE:
   - The Q06 D07 basis ("#7856 unmerged"; it is merged).
   - The R6-PREREG-01 "#7581/#7738 are Draft" (they are merged). Its substance still holds,
     because the merged code has no nightly caller.
3. The Cycle macro diagnostic is admitted by ruling but blocked by review. The review's B1
   finding applies equally to the merged v1 prereg's exact binomial endpoint, so running v1
   would not be decision-grade even ignoring custody.
4. B04 is the hub: B08, B09, B14 and B17 depend on it. Its first unit collides with two drafts,
   one idle since 2026-09-25. The split in F2 preserves the ratified contract and avoids the
   held effects.

## 5. Lanes and packets

| Run id | Kind | Host | Status | Report (lane branch) |
|---|---|---|---|---|
| pro-intel-censusA-20261021-r1 | census | ubuntu2 | DONE rc=0, `1b5114fb32b` | intel/CENSUS_A_EARLY_LEADERSHIP_B4_2026-10-21.md |
| pro-intel-censusB-20261021-r1 | census | ubuntu2 | DONE rc=0, `d166114c595` | intel/CENSUS_B_EARNINGS_CYCLE_LATER_2026-10-21.md |
| pro-intel-b27-20261021-r1 | research | ubuntu0 | RUNNING | intel/B27_RETAINED_SLEEVES_DISPOSITION_DRAFT_2026-10-21.md |
| pro-intel-b08gates-20261021-r1 | research | ubuntu3 | RUNNING | intel/B08_Q06_GATE_S_ACCEPTANCE_READINESS_2026-10-21.md |

Written, not launched. The packets are in the orchestrator scratchpad `pk/` directory and are
listed here by name:
- `pro-intel-b16diag-20261021`: withheld; see F3.
- `pro-intel-b04a0-20261021`: awaits F2.
