# Prophet R7 — Stage 3/4 intelligence disposition (US sleeves)

Orchestrator: ORCH-INTEL (Opus 5.5, ROUTE orchestration, fable-mode), commissioned by Fable seat
69eb9a1c under the Chairman masterplan of 2026-10-20 (Stage 4: Early Leadership, Earnings, Cycle
sleeves, plus the gating Stage 3 units). Base: `e5dd30c6344e4b62a0beba054ac4da97e00bab36`.
Status: DRAFT for the seat. It proposes verdicts and routes. It accepts nothing, removes no
scope, and makes no quantitative claim beyond quoted registered records.
Update 2026-10-21 ~04:1xZ: the seat ruled F1–F8 (§3). Wave 2 lanes run on BASE
`c5ee0941b4e4b2132caabd4d43a4b419d46ec22e` (origin/main at launch); see §5.

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
| B04 | Episode evidence dossier | F2 RULED (A0 now, A1 deferred); V1 RULED: A0 builds without the CI registry line; B04-D BLOCKED-DATA | A0 DONE and consumed: `31baf83179d1` on ubuntu3 lane branch (BASE `4623f0f7`), 25 owned files, 390 tests pass; the seat lands it by fetch + cherry-pick and adds the `prophet-anticipation-intake` registration line (§3 F2) |
| B06 | Policy capture, decision-clean labels | BLOCKED-CUSTODY + BLOCKED-DATA | F4 RULED: source-blind numeric D06 proposal DONE and consumed (`be899fa17f3a`, ubuntu1 lane branch; seat lands by fetch + cherry-pick); all numbers PROPOSED; the seat rules on them (one PASS-form/power inconsistency flagged, §3 F4) and routes frozen numbers to the #8091/#8192 owner |
| B08 | Comparable event and expectation sources | F1 RULED: Sol's recorded Gate S acceptance ratified; records hygiene in lane `pro-intel-b08records-20261021-r1`; production admission BLOCKED-DATA; Gate E closed | Seat lands/reviews the records lane (manifest + append-only prereg note + companion record); D07 exemplar row DEFERRED |
| B09 | Group history and peer evidence | BLOCKED-DATA + BLOCKED-CUSTODY; depends on B04 | None now. Dated theme history accrues forward-only |
| B10 | Early Leadership research comparisons | PROSPECTIVE-ONLY (F5 RULED); BLOCKED-DATA (D07 S3); depends on B06/B09 | `recorded_at` episode writer ROUTED-TO-SOURCE (Source orchestrator Stage 3). No lane here |
| B12 | Genuinely earlier entry | PROSPECTIVE-ONLY (F5 RULED); BLOCKED-DATA (no live B4 capture; D02 gated) | B4 runtime caller ROUTED-TO-SOURCE (Source orchestrator Stage 3). No study, no lane here |
| B14 | Earnings research journey | BLOCKED-CUSTODY (#7264) + BLOCKED-DATA (B1 natural clock; thesis DDL human gate) | D5 consumer already built (BUILT_NOT_PROVEN); #7264 owner owns the Lab view; production proof waits on B1 |
| B15 | Earnings models, entry, holding | BLOCKED-DATA (no registration; H42 price basis blocked) | None. A prereg draft waits on the corporate-action factor owner |
| B16 | Cycle source-readiness pilot | CLOSED NOT PILOT-READY (R6-B16-01, DO_NOT_REDO); diagnostic HELD (F3 RULED) | #7868 repair queued for Stage 4, not launched; never run v1 (#7847); packet `pro-intel-b16diag-20261021` withheld |
| B17 | Funding and per-share Cycle dossiers | BLOCKED-CUSTODY (#8308 stays with Sol, F6 RULED) + BLOCKED-DATA | None. Milestone-absence note for Sol carried to the Stage 6 records PR (§3 F6); no post |
| B18 | Failure-inclusive Cycle policy research | BLOCKED-DATA by ruling (R6-B16-01:21) | None. A licensed failure/mapping source is the provider question |
| B19 | Cycle core/add/exit | BLOCKED (B17/B18; D04 Cycle versions; no milestones) | None |
| B24 | Portfolio context across sleeves | BLOCKED (B07/B13/B14/B17 undispatched; D05 DDL human gate) | None |
| B27 | Retained sleeves and instrument roadmap | DISPOSITIONED (F8 RULED): all five sleeves SPEC_ONLY_RETAINED_B27; no scope removal (D12) | §8 order 1→5 accepted; gated on B00/B06; read-only census only until B06; no live/qualified/ranked claims; shorting barred (DNR:45), options research-only |

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
  - The Q06 contract v0.2 (#8069, merged 2026-10-05) still records
    `.state = "GATE_S_REPAIRED_PENDING_PARENT_ACCEPTANCE"` and
    `.gate_s.state = "REPAIRED_PENDING_PARENT_ACCEPTANCE"`, with next action "Parent reviews Gate
    S v0.2".
  - **But the acceptance is already recorded at BASE.** `earnings_semantics_v1/README.md:81-84`:
    parent Sol independently reproduced the repaired Gate S contract on #8069 head `ae9409bc`
    and accepted the factual source field only, in #8069 comment `5894923827`. I re-hashed the
    contract at BASE: sha256 `a0790967…a177d`, which is byte-identical to the SHA that the D5
    consumer pins (`D5_CONSUMER_2026-09-30.md`). The test fixture copy carries the same hash.
  - The verifier asserts `gate_s.state == "REPAIRED_PENDING_PARENT_ACCEPTANCE"`
    (`verify_q06_…py:100`), and the D5 consumer pins the contract SHA-256. A byte edit to the
    contract would therefore break both. Its state field is stale by design-constraint, not
    by an open acceptance.
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
- **Lane result.** `pro-intel-b08gates-20261021-r1` (ubuntu3, DONE rc=0, `42547cfd885a`, +190).
  - Verifier exit 0; `feature_value_pct` 16.356501765281383 = (109417/94036 - 1) x 100.
  - Six review findings (M1-M3, m1-m3) are repaired; blockers `[]`.
  - The rights blob `a9ee6f28…` equals the pin. The register has a single commit (#7843). SEC
    EDGAR is user-facing, with citation limits.
  - D07: PUBLIC_INFO_REPLAY is PROPOSED, not registered. The register has no AAPL/Q06 row.
  - It lists ten stale companion records (A-J), including the manifest basis/next_action, the
    contract state fields, `d5_adapter_edit_authorized:false`, and the v0.1 terminology.
  - Offline gaps: comment `5894923827` and live PR state cannot be verified from the lane host.
- **Verdict.** NEEDS-FABLE-DECISION, now narrowed to F1: ratify the recorded acceptance and
  approve a manifest-only records PR. No fresh acceptance is needed. Production admission stays
  BLOCKED-DATA (consensus absent; one issuer in the D5 allowlist ∩ events; no B1 natural
  clock).

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
  - The source-qualified D5 consumer is already built: `D5_CONSUMER_2026-09-30.md` is
    "BUILT_NOT_PROVEN". It reads the canonical #8069 contract path and pins its SHA-256 and
    rights blob. Its carrier #8189 is MERGED.
  - The explanation layer is included (EVIDENCE_BRIEF…:16-18).
  - The handoff `…2026-09-30-earnings-d5-consumer.md` ended blocked.
- **Custody.** #7264 (claude/, mastermindx-2, draft, 2026-10-06) owns the Lab earnings view
  (`engine/prophet_lab/earnings_view.py`, `episode_directory.py`, `app/prophet_lab.py`).
- **DO_NOT_REDO.** WS:117-120: D5 needs B1 canonical episode identity; never alias the Radar
  live episode.
- **Blocking facts.**
  - B1 natural nightly clock (C-census:120).
  - D5_CONSUMER:54-57 names #8069's suite registration/CI and source release as prerequisites.
    #8069 is MERGED (2026-10-05), so that blocker is stale at BASE. Release to production is
    still unproven.
  - Thesis capture DDL is an EXACT_HUMAN_GATE (SEAT_RULING_R6-D05-01:16).
- **Verdict.** BLOCKED-CUSTODY + BLOCKED-DATA. The comparable-field consumer exists. The
  remaining gaps are production proof on a real B1 episode, the B1 natural clock, the DDL human
  gate, and the #7264 Lab view (incumbent custody).

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
- **Verdict.** READY for a research-only disposition draft.
- **Lane result.** `pro-intel-b27-20261021-r1`, host ubuntu0, DONE rc=0, lane commit
  `be515d3c0df`. The report is 215 lines:
  `research/prophet_v4/r7_program/intel/B27_RETAINED_SLEEVES_DISPOSITION_DRAFT_2026-10-21.md`
  on lane branch `lane/pro-intel-b27-20261021-r1`.
- **Proposed dispositions.** It removes no scope:
  - Policy/Event Swing, Catalyst/Dislocation, Liquidity/Debasement/Real Assets and
    Range/Mean Reversion: RETAIN-RESEARCH-NEXT.
  - Liquidity/Debasement/Real Assets is readiness-first. Its futures/commodity data leg
    waits on a rights row, since the registry has none at BASE.
  - Defensive/Avoidance/Hedge: RETAIN-DEFERRED, triggered by a Portfolio/Risk decision
    contract plus a hedge-instrument owner.
- **Other content.** An instrument × sleeve roadmap, where every short expression is barred
  (`KILL-DIRECTIONAL-SHORTING`, DNR:45) and options are research-only. A sequencing
  proposal. No sleeve is claimed live, qualified or ranked at BASE.
- **Orchestrator adjudication.** I spot-checked 15 citations at BASE and all matched:
  - `engine/prophet_strategy_definition.py:517/549/581/613/645/597/607`;
  - DNR:45/53/117/123/130;
  - catalog:22.
- **Accepted as a DRAFT for the seat, with one qualification.** Each "smallest first research
  step" is admissible only as a read-only source/kill-equivalence census. Any
  preregistration or study waits on B06 (B27 depends on B00/B06; B06 is BLOCKED above). The
  draft says the same in its §8.

## 3. Decisions for Fable — RULED 2026-10-21 ~04:0xZ

All eight were ruled by the seat (Fable 69eb9a1c). The recommendation text is kept short; the
ruling is binding.

- **F1 — Gate S records hygiene. RULED: ACCEPTED.**
  - Seat confirmed comment `5894923827` on #8069 exists: author mastermidx4 (Sol),
    2026-09-29T17:05:28Z, marker `SOL_Q06_GATE_S_ACCEPTANCE_20260929`, "SOL ACCEPTED / CONTINUE —
    Gate S factual field accepted; Gate E remains closed". Not re-accepted.
  - Build lane `pro-intel-b08records-20261021-r1` (manifest edits only, BASE `c5ee0941`):
    manifest `.evidence_class.basis` → `D07_REGISTER_V1_ADOPTED_R6-D07-01_2026-09-27_509ffb5a6a5c`;
    `.next_action` and `.feature` → the accepted factual field citing README:81-84 and the
    comment; R6-PREREG-01 Draft wording → merged-but-uncalled; one companion record.
  - FROZEN: the contract JSON and its fixture are never byte-edited; sha256 `a0790967…a177d`
    unchanged and the verifier exits 0 are acceptance conditions.
  - Interpretation (flagged to the seat): R6-PREREG-01 line 9 was true on 2026-09-23, so the lane
    appends a dated status note instead of rewriting it.
  - D07 exemplar register row: DEFERRED. Gate E stays with Evaluation.
- **F2 — Split B04-A. RULED: ACCEPTED (A0 now, A1 later). A0 RESULT: BLOCKED, NOT LAUNCHED.**
  - Fresh collision check (one aliased GraphQL read of #8004/#7426/#7264 file lists; a first
    call against the wrong repository returned no data):
    - #8004 OPEN `f5898f9b0b`, 3 files; #7426 OPEN `7bc0487674`, 20 files; #7264 OPEN
      `214e0eda8c`, 64 files.
    - A0 owned files: `engine/prophet_lab/evidence_dossier.py`,
      `config/prophet_dossier_reason_map.v1.json`, `tests/fixtures/prophet_lab_dossier/`,
      `tests/test_prophet_lab_dossier_b04a.py` (name fixed by R6-B04-01a:113), and one
      registration line in `.github/ci/legacy-jobs.yml` (mandatory: `test_ci_pack` checks that
      every test file is registered).
    - Intersection = `.github/ci/legacy-jobs.yml`: in #7426, #7264 and the seat fence #9821.
      Non-empty, so per the ruling the lane is not launched. None of the other A0 paths exist at
      BASE or in any listed PR.
  - Hunk evidence (local objects, each PR diffed against its own merge-base): #7264 hunks at
    @@ -2071/3032/3053/3064/3069/7411; #7426 at 3160–3200; #9821 at 8474/8569. None touches the
    `prophet-anticipation-intake` job (BASE line 27185; whynot run line 27234) where A0 adds
    its line.
  - Options for the seat:
    - **V1 (recommended):** relaunch A0 as `-r2` without the CI line; the lane's acceptance
      runs the new test file directly, and the seat adds the single registration line in its own
      landing commit. The hunk is disjoint from every incumbent hunk, so the textual conflict is
      nil and the custody touch is one line the seat owns.
    - **V2:** defer A0 until #7426 and #7264 land or close.
  - **V1 RULED by the seat (~04:1xZ).** Relaunched as `pro-intel-b04a0-20261021-r2` on BASE
    `4623f0f74184ff41debdeb2ca86e225506a05911` (main after #9921 merged). `.github/` is out of
    scope for the lane; a `test_ci_pack` failure naming only the unregistered new test is
    expected and reported under GAPS. The A0 inputs (amendment, `engine/prophet_lab/`,
    `app/prophet_lab.py`, the listed tests) are byte-unchanged between `c5ee0941` and `4623f0f7`.
  - **A0 r2 consumed 04:4xZ (orchestrator).** DONE rc=0 04:40Z on ubuntu3; commit
    `31baf83179d145de507467544c521fdb1e6dbeed` on `lane/pro-intel-b04a0-20261021-r2`, one commit
    on BASE `4623f0f7`, 25 files (+3502), owned paths only: the reason map, `evidence_dossier.py`
    (822 lines), 22 fixtures and `tests/test_prophet_lab_dossier_b04a.py` (57 tests). No change to
    `.github/`, `app/prophet_lab.py` or `engine/prophet_lab/intelligence_vector.py`.
  - **Orchestrator verification.** The reason map sha256 is
    `8fe54266710a11390a9cd8a07ccf00c5173700dac93728d91e294e84c4079645`, equal to an independent
    extraction of amendment lines 163-303 at `4623f0f7` (lines 162 and 304 are the fence markers).
    Re-run with the lane venv: the four named suites give 390 passed (57 new + 333 existing).
    The bare system python on ubuntu3 lacks `pyarrow`, so that run gives a collection error; this
    is an environment fact, not a code defect. The new test's third-party import closure is
    numpy, pandas, pyarrow, requests and yaml, all on the intake job's pip line. Spot-checked:
    `view_decision_admissible` is a literal-false check, and `NOT_CAPTURED_AT_DECISION` is
    returned only when `observed_at_attests_capture` is true (default false). The typed
    `IdentityBindingConflict` was not added, as the packet froze it to A1.
  - **The expected `test_ci_pack` red did not occur** (201 passed, 2 skipped). The manifest
    allows dark suites, so the new suite is not executed in CI until registered. Seat landing
    act, one line in `.github/ci/legacy-jobs.yml` at `4623f0f7` line 27234 (job
    `prophet-anticipation-intake`, no `paths:` scope, executed by `scripts/run_ci_pack.py`):
    `        run: python -m pytest tests/test_prophet_whynot_receipts.py tests/test_prophet_lab_dossier_b04a.py -q`
  - **Two declared readings for the seat to note.** (1) The wrapper runs its own closed input
    checks and the `_FORBIDDEN_KEYS` scan rather than `validate_intelligence_vector`, because
    wrapper-level bases such as `conflicting_source_spans` are outside the vector vocabulary;
    real builder vectors are exercised in tests. (2) In `resolve_display_code`, an explicit
    coverage basis outranks an explicit lane when both could match. The amendment fixes only
    lane specificity. All 33 committed map rows have `lane: null`, so the choice is unobservable
    today; rule it before any lane-specific row is added (B04-B).
  - **A0 scope bounds (lane GAPS, not defects):** `trajectory`/`correction` stay outside the A8
    touch list until B04-B; `views.current` is ABSENT unless a caller supplies `current_vector`
    (B04-C); `explanation_facts` are swept wholesale when any lane is gated (v1 families emit
    none); the pre-inception distinction is caller-side.
  - A1 and the #8004 owner ask stay deferred until A0 merges.
- **F3 — Cycle diagnostic. RULED: ACCEPTED (hold).** Never run v1 (#7847). The #7868 B1/B2
  repair is queued for Stage 4 and not launched. Packet `pro-intel-b16diag-20261021` stays withheld.
- **F4 — Numeric D06 fields for H1. RULED: ACCEPTED.** Research lane
  `pro-intel-d06num-20261021-r1`: a source-blind numeric proposal for
  Q05-H1-PEER-PARTICIPATION-ACCELERATION-V1, no outcome reads, report
  `intel/D06_H1_NUMERIC_PROPOSAL_2026-10-21.md` (lane branch). Every number is PROPOSED until the
  seat rules. Definition is not admission.
  - **Consumed 04:2xZ (orchestrator).** DONE rc=0 04:18Z; commit `be899fa17f3a` on ubuntu1
    `~/lanes/wt/pro-intel-d06num-20261021-r1`, one file, +261. Status line reads "PROPOSED — NOT
    RULED, NOT REGISTERED, NOT ADMITTED". Source-blind: the report states no `data/` or `site/`
    path was opened; R20/R21 read at PR head `410965bd`, the #8192 script (code only) and S0
    (keys only) at `07136c56`. R20:101 and R21:84 record zero prospective accrual.
  - **Proposed fields (all PROPOSED).** F1 materiality 50 bps per decision date, net of the 50 bps
    round-trip cost floor. F2 non-inferiority: one-sided 95% LCB of paired C2−C1 ≥ −25 bps. F3
    ES10 guardrail, UNESTIMABLE below 100 matured dates. F4 HAC lag 9 (H−1) or block ≥ 10. F5
    cohort starts at the first S0-verified session after registration. F6 one fixed look, floors
    50 dates and N_eff ≥ 20, N OPEN. F7 futility at ceil(N/2) if UCB < 50. F8 Holm family of 6
    (C1–C5 primary + H1), FWER 0.05 one-sided OPEN in {0.025, 0.05, 0.10}, planning α 0.008333.
    F9 prior looks named, species-equivalence left to the seat. F10–F11 population freeze K=5,
    refused rows at cash. F12 σ OPEN on the grid {50, 100, 200, 400}. F13 PASS = Holm rejection
    AND point estimate ≥ 50 bps AND F2/F3 hold.
  - **Citation spot-check at `c5ee0941` (orchestrator): all match.** PREREG.json:174-180
    (`lower_bound_margin_bps: -25`, `cost_floor_bps_round_trip: 50` as a floor); R6-PREREG-01
    ruling :41 (Holm across C1–C5; search family includes the EL H10 timing study) and :43 (the
    50 bps floor; a lower floor invalidates the read); Cell G law :273-279 (ES10 `tail_n < 10` →
    UNESTIMABLE) and :369 (HAC lag H−1 under the owning registration's convention); Decision
    Register :151 (required evidence includes a user economic-loss budget, still absent).
  - **Arithmetic check: consistent.** With z(1−0.008333) = 2.394 and z(0.80) = 0.842, the normal
    N at σ/δ = 1, 2, 4, 8 is 10.5, 42, 168, 670. This matches the lane's 11/42/168/671 (normal)
    and 14/45/171/673 (exact t). The block-10 ×10 column (about 140 to 6,730) is a crude
    conservative bound and is labelled as an assumption, not an estimate.
  - **Finding for the seat (rule before freezing).** The F13 PASS form and the power table are
    inconsistent. Power is computed for rejecting μ ≤ 0 at a true μ of 50 bps. PASS also requires
    a point estimate ≥ 50 bps, which at a true μ of 50 holds only about half the time. The
    effective PASS power at the planning effect is therefore about 50%, not 80%. Two remedies,
    the seat's call: (a) power the test against the PASS form, for example plan at δ above
    50 bps or test H0: μ ≤ 50 directly, which raises N; or (b) drop or relax the point-estimate
    leg and let the F1 materiality ride on the hypothesis being tested. Never resolve it by
    lowering the 50 bps floor (D06; the ruling :43 floor binds).
  - **OPEN, not resolvable by the lane:** FWER, σ, N, the PASS form, the unmeasured nightly
    accrual rate, and the missing user economic-loss budget (DR:151). Definition is not
    admission. The report stays on the lane branch; the seat lands it.
- **F5 — Prospective-only Early Leadership capture. RULED: ACCEPTED.** B10/B12 are
  prospective-only; no retrospective study is admissible (D07). The B4 runtime caller (nightly
  caller of the merged #7581/#7738 library) and the write-time `recorded_at` episode writer are
  ROUTED-TO-SOURCE (Source orchestrator, Stage 3). Not launched here.
- **F6 — #8308 B17. RULED: ACCEPTED.** #8308 stays with Sol. Note for Sol, to be carried in the
  Stage 6 records PR (no post now):
  - Milestone-absence note: the Cycle per-share/funding dossier (B17) has no registered
    milestone set at BASE, and B19 (core/add/exit) cannot be specified without one. When #8308
    resumes, it should name the milestone source, its clock and its absence state (D07: an
    unknown milestone clock stays diagnostic), so B19 can be registered against it.
- **F7 — Chairman provider question (Cycle). RULED: ACCEPTED (not asked).** R6-B16-01:25-28
  keeps it unaskable until rules 1/4/5 are otherwise satisfiable. FRED model use remains
  "not a source".
- **F8 — B27 dispositions. RULED: B27 draft ACCEPTED as the retained-sleeves disposition.**
  - All five sleeves stay SPEC_ONLY_RETAINED_B27. No scope removal (D12).
  - §8 sequencing 1→5 accepted. Everything is gated on B00/B06; first steps are read-only
    census only until B06.
  - §9 "no live/qualified/ranked claims" accepted. Shorting barred (DNR:45); options are
    research-only.
  - B27 is DISPOSITIONED.

## 4. Findings

1. Every Stage 4 unit is gated by a held incumbent, a missing source clock, or an open seat
   decision. The cheapest unlocks are two seat decisions (F1 and F2), not new research.
2. Several recorded premises are stale at BASE:
   - The Q06 D07 basis ("#7856 unmerged"; it is merged).
   - The Q06 contract and manifest state "pending parent acceptance", although README:81-84
     records Sol's acceptance. The contract cannot be byte-edited without breaking the D5 SHA pin
     and the verifier, so the fix belongs in companion records.
   - The D5 consumer's "#8069 release/CI outstanding" (#8069 is merged).
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
| pro-intel-b27-20261021-r1 | research | ubuntu0 | DONE rc=0, `be515d3c0df`, consumed + spot-checked | intel/B27_RETAINED_SLEEVES_DISPOSITION_DRAFT_2026-10-21.md |
| pro-intel-b08gates-20261021-r1 | research | ubuntu3 | DONE rc=0, `42547cfd885a`, consumed; acceptance hash + verifier assert re-checked at BASE | intel/B08_Q06_GATE_S_ACCEPTANCE_READINESS_2026-10-21.md |

| pro-intel-b08records-20261021-r1 | build | ubuntu1 | DONE rc=0 04:09Z, `524dcfdc3f1e`, consumed; contract sha + verifier + fixture sha re-checked on host | manifest + prereg status note + `wave3/Q06_GATE_S_ACCEPTANCE_RECORD_2026-10-21.md` (3 files, +69/−3) |
| pro-intel-d06num-20261021-r1 | research | ubuntu1 | DONE rc=0 04:18Z, `be899fa17f3a`, consumed (F4; citations spot-checked; PASS-form power finding), BASE `c5ee0941` | intel/D06_H1_NUMERIC_PROPOSAL_2026-10-21.md (lane branch; seat cherry-picks) |
| pro-intel-b04a0-20261021-r2 | build | ubuntu3 | DONE rc=0 04:40Z, `31baf83179d1`, consumed (F2/V1; reason map sha verified; 390 tests re-run), BASE `4623f0f7` | `engine/prophet_lab/evidence_dossier.py`, reason map, fixtures, `tests/test_prophet_lab_dossier_b04a.py` |

Written, not launched. The packets are in the orchestrator scratchpad `pk/` directory and are
listed here by name:
- `pro-intel-b16diag-20261021`: withheld (F3 RULED: hold).
- `pro-intel-b04a0-20261021-r1`: never launched (BLOCKED by the `.github/ci/legacy-jobs.yml`
  collision); superseded by r2 under V1. The run id stays retired.

## 6. Seat rulings on the consumed returns — 2026-10-21 ~05:0xZ (seat 69eb9a1c)

The INTEL orchestrator returned `STATUS: DONE` at ~04:5xZ with both remaining lanes consumed
(B04-A0 `31baf831`, d06num `be899fa1`). Landing is the seat's act; the rulings it asked for
are made here so no later wave has to re-derive them.

- **F13 — d06num PASS-form power (RULED).** The PASS test as drafted is underpowered: the
  power table rejects μ ≤ 0 at a true gain of 50 bps, but PASS also demands a point estimate
  ≥ 50 bps, which holds about half the time at that true gain, so real PASS power is ~50%.
  Ruling: adopt the lane's option (a) in the form *test the cost floor as the null* —
  H0: μ ≤ 50 bps (the PREREG cost floor, `PREREG.json:174-180`), one-sided, powered at 80%
  against a planned true gain that revision r2 of the proposal must set and justify from the
  nightly accrual budget. The separate point-estimate condition is dropped as redundant
  (rejecting μ ≤ 50 implies the estimate exceeds 50). The 50 bps floor is never lowered.
  N rises; r2 recomputes the table. Still OPEN and unchanged by this ruling: family-wise
  error level, σ, N, the nightly accrual rate, and the user economic-loss budget DR:151
  requires. The proposal lands as PROPOSED in the records PR; nothing in it is frozen.
- **F14 — reason-map precedence (RULED).** When an explicit coverage basis and an explicit
  lane could both match, the lane implemented basis-outranks-lane. All 33 committed rows
  carry `lane: null`, so the precedence has no effect today. Ruling: specificity first — a
  row matching both basis and lane outranks a row matching either alone; among single-key
  rows basis outranks lane (the current implementation). B04-B must add the precedence test
  before it adds the first lane-specific row; until then no lane-specific row is admitted.
- **F15 — wrapper validation surface (ACCEPTED).** The wrapper runs its own closed input
  checks plus the `_FORBIDDEN_KEYS` scan rather than `validate_intelligence_vector`, because
  wrapper-level conditions such as `conflicting_source_spans` are outside the vector's
  vocabulary. Accepted; B04-B/C must not duplicate vector validation inside the wrapper, and
  wrapper-level vocabulary stays wrapper-owned. `IdentityBindingConflict` stays in A1.
- **CI registration (seat landing act).** The lane could not touch `.github/`; the seat
  registers `tests/test_prophet_lab_dossier_b04a.py` as its own step in job
  `prophet-anticipation-intake` of `.github/ci/legacy-jobs.yml` on the ship branch
  `claude/prophet-r7-b04a0-evidence-dossier` (placed after the leader-observation shelf step
  so it merges cleanly beside the Asia carve-out's edit of the why-not line). An independent
  fabric review lane (`pro-intel-b04a0-review-20261021-r1`, seven attack surfaces incl. the
  `return {}` mutation experiment) runs against the pushed head before any merge.
- **Landing route.** B04-A0 → its own PR (code; review + green → `--match-head-commit`
  merge). d06num → the next records PR with this disposition, the INTEL worklog and the
  regional review reports. Neither is merged at the time of writing.
