# CENSUS A — Early Leadership sleeve + B4 entry-policy calibration (read-only evidence census)

- Census date: 2026-10-21. BASE: `e5dd30c6344e4b62a0beba054ac4da97e00bab36` (branch `lane/pro-intel-censusA-20261021-r1`; working tree clean at BASE, so working-tree line numbers == BASE line numbers).
- Method: read-only. PR-head files were read only as `git show <sha>:<path>`; heads used: #8240 `6d920952dc`, #8091 `410965bd24`, #8192 `07136c56ec`, #7772 `2c198dd2cd`, #7604 `abcf15fad3`. #9714 head `ed974b3b09` is **not available on host**.
- Citation conventions: `path:line` = BASE working tree; `path:line@<sha>` = that PR head's copy of the file. JSON cites give the key path.
- Elision note: where a source sentence contains one specific word prohibited by this census packet, it is quoted as «elided». Nothing else is altered inside quote marks.
- No outcome data was opened; `data/` was never read (see "Outcome files avoided").

---

## B04 — episode evidence dossier

### 1. What exists at BASE, on PR heads, and what is ruled

**At BASE.**
- The intelligence-vector projection the dossier wraps exists and is pinned by tests (census of 2026-09-23 at `research/prophet_v4/r6_program/wave2/B04_EVIDENCE_DOSSIER_CONTRACT_CENSUS_2026-09-23.md`): `build_earnings_intelligence_vector` at `engine/prophet_lab/intelligence_vector.py` ("`build_earnings_intelligence_vector` accepts the episode, an exact `peg:<64 hex>` generation id…" — census:9); schema guard at `engine/prophet_lab/intelligence_vector.py:1044` (`if str(episode.get("schema") or "") != "prophet.candidate_episode/v1":`) and `:1681`; B3-side guard at `engine/prophet_candidate_state.py:328`.
- The route exists at BASE: `GET /api/prophet/lab/v1/episodes/{episode_id}/intelligence` at `app/prophet_lab.py:254-322` (cited in R6-B04-01a:99).
- The six discriminating cases were censused (census:86-97); "Status count: 2 COVERED · 2 PARTIAL · 2 BLIND." (census:97); the two BLIND cases are "3. Missing historical event set … **BLIND** — no typed 'event set unavailable at the historical cut' lane exists; this is a B04 blocker." (census:92) and "5. Unlicensed fact … **BLIND** — an internal-only family's derived fact is not blocked at the detail boundary; this is the top rights blocker." (census:94).
- The dossier wrapper itself does NOT exist at BASE: `git cat-file -e HEAD:config/prophet_dossier_reason_map.v1.json` → absent; `config/prophet_dossier_lane_families.v1.json` → absent; `config/prophet_source_rights_postures.yml` → absent (all three named as B04-A/B04-B artifacts in the rulings).
- Rulings at BASE: `research/prophet_v4/r6_program/rulings/R6-B04-01_DOSSIER_CONTRACT_2026-09-24.md` — deciding sentence, :1: "the episode evidence dossier contract (B04) is adopted with amendments; build order fixed"; :18: "Build order (each a separate fabric lane; each PR carries its own tests; no unit self-merges)" with B04-A/B04-B/B04-C/B04-D at :19-22, incl. :22 "**B04-D** (blocked on D07) = class propagation once a registration artifact exists".
- `research/prophet_v4/r6_program/rulings/R6-B04-01a_DOSSIER_CONTRACT_AMENDMENT_DRAFT_2026-09-24.md` — ratified as R6-B04-01a: :5 "The accountable successor root `01a11e89-b35d-7a81-9404-5fce2c6170cb` ratifies this reviewed amendment as R6-B04-01a. … This ruling does not transfer the held #7426/#8004 source effects or commission B04-A over them."; amended build order at :361-367, incl. :363 "**B04-A** … It does not commission until this draft is ratified without repairs that alter its contract." and :366 "**B04-D** — evidence-class propagation, still gated on D07. D07's block on B04 is narrowed to B04-D because A8 moves `evidence_class` to the wrapper; the seat must ratify that narrowing."
- D07 adoption ruling: `research/prophet_v4/r6_program/rulings/R6-D07-01_EVIDENCE_CLASS_REGISTER_ADOPTION_2026-09-27.md:36` — consumer disposition row: "B04-D | S1 ×14 | BLOCKED | B04-D (per-family identity/route/capture/correction)".

**Open PR heads only.** None of B04's artifacts live on the six heads read: `git show <sha>:engine/prophet_early_leadership_evidence.py` etc. show no dossier wrapper, reason map, lane-families map or posture map on #8240/#8091/#8192/#7772/#7604 (each named file probed; see "Absent / not found").

**Ruled (summary).** Contract adopted 2026-09-24 (R6-B04-01), amended A7–A12 and ratified (R6-B04-01a); B04 closes at JSON detail + renderer sentences with the user-readable visual matrix moved to B20/B07 (:367); D07's block narrowed to B04-D, subject to seat ratification (:366).

### 2. Program status
- `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/BUILD_PROGRAM.json` → `units[] (id="B04") → status` = `"SPECIFIED_NOT_DISPATCHED"`; `research_packets` = ["Q01","Q13","Q14"]; `decision_ids` = ["D03","D07","D10"].

### 3. Remaining closure the sources name as open
- R6-D07-01:36 — B04-D "BLOCKED" pending per-family remedies; D07 draft:78: "B04-D consumes all fourteen S1 rows. Their proposed class is null, so the disposition is `BLOCKED pending the per-family identity, route, capture, and correction remedies named above`."
- R6-B04-01a:366 — "the seat must ratify that narrowing"; :363 — B04-A does not commission until ratification "without repairs that alter its contract".
- R6-B04-01a:364 — B04-B's route-boundary rights gate is owed "before any user-facing render of transcript-derived lanes … The static `ALLOWED` transcript guidance noted by the census is a pre-existing defect that B04-B closes; until then it is not user-facing dossier evidence."

### 4. DO_NOT_REBUILD / do_not_redo rows that constrain it
- `agentos/workstreams/WS-PROPHET-US-V4-RECOVERY.md:119-120` (do_not_redo): "Runtime D5 requires the owner-issued canonical prophet.candidate_episode/v1 from B1. **Never alias mastermind.live_entry_episode.v1 or mint ticker/date surrogate episodes.**"
- Same file :121-125: "Do not read Earnings decision-time evidence through read_event_workspace / read_current_event_workspace. … Decision-time access is read_event_source_revisions / read_all_event_source_revisions only."
- Same file :126-131: admission is the conjunction `source_available_at <= cut AND observed_at <= cut`; "admitting it is lookahead. That case is NOT_CAPTURED_AT_DECISION".
- D07 register rows S1 ×14 (`research/prophet_v4/r6_program/wave3/D07_EVIDENCE_CLASS_REGISTER_DRAFT_2026-09-24.md:47-60`): each S1 row's prospective_remedy ends "this row blocks B04-D."

### 5. Data / rights / custody blockers named
- Rights: census:115 lists register postures (user-facing Massive; internal-only FRED/Census/Yahoo/transcripts/press; not-a-source Nasdaq/S&P Kensho/consensus), and census:113: "an internal-only family's derived fact must not enter a user-facing observation. Today nothing performs that source-family check."
- Custody: R6-B04-01a:5 — the held #7426/#8004 source effects are not transferred; B04-A is not commissioned over them.
- Historical event set: census:92 (BLIND case 3); binding rule quoted at census:205: "`R6-D03-01_SOURCE_READINESS_SCOPE_2026-09-23.md:73`" — history admissible only where a source-dated point-in-time row exists.

---

## B06 — policy capture and decision-clean labels

### 1. What exists at BASE, on PR heads, and what is ruled

**At BASE.**
- The grader exists: `engine/us_prophet_grades.py:1-30` (docstring: "Full-population forward grader over the US Context Vector store (PROPHET US §W7). Grades **every stamped candidate row** … across the **H=10/21/42/63 session ladder, excess vs SPY**"); `HORIZONS = (10, 21, 42, 63)` (:121); `BENCH = "SPY"` (:122); `GRADE_KEY = ("stamp_date", "ticker", "board_definition", "horizon")` (:126).
- The chronology clock boundary exists (2026-10-08 rescue, merged by BASE): `research/prophet_v4/r6_rescue_20261008/PROOF_AND_FRONTIER.md:24-32` — "`scripts/audit_prophet_plan_chronology.py` now carries an explicit clock-evidence boundary … Accepted publication, first user exposure and executable fill remain UNRESOLVED because this audit has not joined those owners' evidence."; real retained evidence read at :75-80 (CRI run date 2026-10-06, price basis 2026-10-05, `stale_price_basis` unchanged).
- `research/prophet_v4/r6_rescue_20261008/SCOPED_REVIEW.md:18` — "**PASS** — C1_ROUTINE_BOUNDED audit-interpretation review of the pinned chronology clock slice"; :39 — "**What this does not prove.** Full B06 or R6. User exposure, accepted publication, or an executable fill for any plan…".
- `research/prophet_v4/r6_rescue_20261008/B06_ECONOMIC_SOURCE_QUALIFICATION.md:28-29` — "This independently confirms why the handoff's CTVA discontinuity must stay **UNRESOLVED** as an economic outcome. No corrected percentage is published here."; defects table at :36-43 (native mark vs shareholder wealth; corporate-action coverage UNAVAILABLE; benchmark forward-fill; immutable outcome revision).
- The #7751 preregistration (B4 calibration) exists at BASE with amendment A1: `research/prophet_v4/b4_entry_policy_calibration/PREREG.json:26-34` and the companion md `research/prophet_v4/B4_ENTRY_POLICY_CALIBRATION_PREREG_2026-09-23.md:68-82`.
- Ruled: `research/prophet_v4/r6_program/wave0/SEAT_RULING_R6-PREREG-01_2026-09-23.md:32` — "Verdict adopted: D03/D06/D07/D08 are NOT closed. They close only through registration artifacts carrying the rows above, each accepted by an independent external reviewer before the first formal read." (B4-audit item, line 19: "`PUBLIC_INFO_REPLAY` … is never pooled with observed-as-run rows").
- D01 ruled: `research/prophet_v4/r6_program/rulings/SEAT_RULING_R6-D01-01_2026-09-23.md:7` — "**D01 is resolved by composition (a): an explicit, versioned validity contract on the last-completed-session receipt, with a hard freshness ceiling.** (b) intraday re-emission is REJECTED — `engine/signal_gate.py` is a close-only statistic and running it on a partial bar changes what was «elided»."; consumer law at :32-33; versioned field at :35: "`engine/prophet_strategy_definition.py` gains `owner_confluence_source_session_rule = "next_session_only/v1"`" (present at BASE, `engine/prophet_strategy_definition.py:153`).

**Open PR heads only.**
- #8192 `07136c56ec`: `research/prophet_v4/S0_CAPTURE_INTEGRITY_R2_20261005.json` (keys only, per packet) — top-level keys include `h1_admitted`, `claim_limit`, `model_fit_executed`, `independent_review_accepted`, `production_nightly_verified`, `mutation_verification.*`, `release_integration.*` (incl. `release_integration.protected_outcome_read`, `release_integration.native_writer_consumer_guard.native_cli.h1_admitted`), `test_results.{native,coherence-green,coherence-red}`; `scripts/check_prophet_h1_prospective_accrual.py:2-11` — "Pre-outcome Prophet H1 prospective-accrual verifier. This tool verifies whether a specific ordinary US nightly candidate/context capture exists and reports only source/coverage metadata. It never reads the forward-grade store, model outputs, return fields, rankings after fitting, or trade outcomes. … A successful S0 receipt proves candidate capture exists; it does not admit H1…". `FORBIDDEN` column set at :50-53.
- #8091 `410965bd24`: `R6-Q05-H1-R20_OWNER_CONSOLIDATION_2026-09-27.md:57-65` — the additive exact benchmark-calendar witness (`bench_calendar_state`, `bench_inserted_session_count`, `bench_missing_sessions`), "Existing grades are not rewritten and old rows without this witness remain unknown."; R21 `R6-Q05-H1-R21_RELEASE_RECONCILIATION_2026-09-27.md:45-57` — same-night cycle-label precedence repair, prospective only: "Prior PIT rows remain null under the no-backfill law."

### 2. Program status
- BUILD_PROGRAM.json → `units[] (id="B06") → status` = `"SPECIFIED_NOT_DISPATCHED"`; `existing_carriers` = [7751, 7218]; `decision_ids` = ["D06","D08","D10"].
- RESEARCH_DOCKET.json → `packets[] (id="Q18") → status` = `"SPECIFIED_NOT_REGISTERED_OR_DISPATCHED"`; same for Q04 and Q15.

### 3. Remaining closure the sources name as open
- PROOF_AND_FRONTIER.md:145-150 — "B06 economic outcome qualification remains open: the shared grader emits a -86% synthetic price mark across a 100-to-14 discontinuity without entitlement inputs. The registered corporate-action adapter returns UNAVAILABLE with blocker `complete_point_in_time_security_and_corporate_actions_contract`."
- B06_ECONOMIC_SOURCE_QUALIFICATION.md:45-48 — "The economic source work does not rerun the frozen study … Split, distribution, delisting terminal value, revision timing, intrabar ambiguity and actual next-available execution remain required B06 cases."
- R20@410965bd24:93-101 — "`trial_may_start=false`. Required gates still open:" (7 numbered gates, incl. :98 "Chronological partitions, test count/power and the numeric D06 worthwhile-gain/tail-harm fields are not frozen."); R21:80-90 lists 9 gates still open.

### 4. DO_NOT_REBUILD / do_not_redo rows that constrain it
- R6-PREREG-01:30 (m1–m3): "DNR kills (`FRESH-TICKS-WINDOW`, `STAGE-WIN-GATE`, `S10-MARGIN-RECLAIM`) checked for equivalence and counted as prior looks" — the rows are `research/DO_NOT_REBUILD.md` KILL-FRESH-TICKS-WINDOW (line 126: "KILLED (construction-scoped, THIRD look) … FRESH_TICKS=2 stands"), KILL-STAGE-WIN-GATE (line 120: "KILLED (construction-scoped) … Stage/EC as a win-rate authority on the timing entry"), KILL-S10-MARGIN-RECLAIM (line 109: "FALSIFIED phase-0 — construction-scoped kill").
- WS do_not_redo :132-135 — "Do not spend a PR removing the bridge candidate cap…".
- PREREG.json `reuse_law.outcome_store`: "reuse an incumbent prospective evaluation ledger; do not create a parallel outcome authority" (:225).

### 5. Data / rights / custody blockers named
- PROOF_AND_FRONTIER.md:151-152 — "#8192/#8091 retain grading/intake custody and their original review/effect gates. #7983 also changes the shared grader; preserve its separate source boundary."
- WS:108-110 (do_not_redo-adjacent note) — "QLedger's control leg has never been populated on any of 46,630 claims (`DSC:NO-QLEDGER-CLAIM-EVER-CARRIED-A-CONTROL-LEG`); the plan ledger has no benchmark column. Do not describe V4 grading as control-matched until wired."
- Corporate-action blocker named above (`complete_point_in_time_security_and_corporate_actions_contract`).

---

## B09 — group history and peer evidence

### 1. What exists at BASE, on PR heads, and what is ruled

**At BASE.**
- Two pure observations exist in the group owner: `research/prophet_v4/leadership_evidence_v1/README.md:12-15` — "This change adds two pure observations to the existing `engine/group_flow.py` owner instead of creating a new peer engine or second ThemeState: 1. `independent_peer_observation` — fixed-roster, leave-issuer-out peer values; 2. `independent_peer_continuity` — who remained, entered, exited or became unknowable…"; status :6 — "**Status:** BUILT_NOT_PROVEN / DISPLAY_AND_RESEARCH_ONLY. No live rank, entry, policy, sizing, execution or trade authority."
- Engine at BASE: `engine/group_flow.py:146` `PEER_CONTEXT_SCHEMA = "prophet.peer_context/v1"`; :148-155 `_PEER_AUTHORITY` (all six authority flags false); :168-228 `_independent_peer_roster` (focal + same-issuer exclusion, unknown identities kept in denominator — :176-178 "Known alternate listings of the focal issuer are excluded with the focal ticker. … This is conservative by construction: missing identity"); :230 `independent_peer_observation`, :316 `independent_peer_continuity`; :650-660 `_pit_sector_frames` — "The 11 GICS sectors as POINT-IN-TIME groups … NOT fully survivorship-free — the universe is still bounded by names present in the current close cache and classified by the current GICS map".
- Module boundary: `engine/group_flow.py:1-23` docstring — "Thematic flow-shift detector (DISPLAY-ONLY) … DISCIPLINE: display-only, NEVER scored".
- Ruled: R6-PREREG-01:26 (M7) — "Current-only group membership = retrospective diagnostic with zero confirmatory credit; unit = group-episode; N_eff(theme) ≥ 5."
- Non-redo boundary: README:58 — "This is **not** PSS-SR2 or PSS-SR3. Those frozen constructions conditioned on recovery after systemic fresh lows and used peer diffusion / synchronized short-horizon positive participation as a directional recovery label. They were rejected on the inspected history and remain closed."

**Open PR heads only.**
- #8240 `6d920952dc`: `engine/prophet_early_leadership_evidence.py:23-28` — `SCHEMA = "prophet.early_leadership_evidence/v1"`, `PEER_SCHEMA = "prophet.peer_ex_candidate/v1"`, plus candidate/exposure/setup/geometry schemas; `_AUTHORITY` all-false (:36-46); `_PROHIBITED_INPUTS` (:47-50); `build_early_leadership_evidence` (:422). Docstring :9-11: "It creates no ThemeState, candidate episode, score, rank, entry verdict, plan, or trade authority. Its job is to bind source-qualified observations into a comparable research feature envelope for B10/H1-style evaluation." Companion `research/prophet_v4/PROPHET_EARLY_LEADERSHIP_EVIDENCE_V1_2026-09-30.md@6d920952dc:30-41` (anti-self-confirmation peer receipt: candidate + all same-issuer aliases excluded; dated membership vintage; singleton = UNAVAILABLE).
- #7604 `abcf15fad3`: `engine/prophet_subtheme_funnel.py:1-19` — "Zero-authority subtheme leadership funnel for Prophet miss attribution. … The current Finviz tree is current-only structure. It is never backdated here. This observer is prospective ops telemetry only and has no rank, gate, size, membership, plan, or trade authority." `SCHEMA = "prophet_miss_audit.subtheme_funnel/v1"` (:30).

### 2. Program status
- BUILD_PROGRAM.json → `units[] (id="B09") → status` = `"SPECIFIED_NOT_DISPATCHED"`; `existing_carriers` = [7455, 7508, 7604]; `decision_ids` = ["D03"]; `release_limit` = "No parallel ThemeState, automatic group bonus or current-membership historical feature."
- RESEARCH_DOCKET.json → `packets[] (id="Q05") → status` = `"SPECIFIED_NOT_REGISTERED_OR_DISPATCHED"`.

### 3. Remaining closure the sources name as open
- README:87-94 — "Bind one dated source roster plus existing identity mapping and group observations to a real Prophet candidate dossier. Compare: incumbent C1; transparent company residual momentum; group-only state; company + independent peer continuity. … The group-only comparator is mandatory so sector timing cannot be misreported as stock-selection skill."
- README:64-68 — "Curated thematic baskets still have a historical-membership limitation where their past aggregation can use a current tree. That limitation is not repaired by this source slice. PIT sector membership is a stronger existing owner path. A research consumer must bind the exact dated roster/source before describing a historical theme feature."
- PROOF_AND_FRONTIER.md:153-154 — "B09/B04 reuse #7455/#7508 and the existing group owners. No coarse Travel proxy, current-membership backfill, self-driven peer metric or automatic group bonus."

### 4. DO_NOT_REBUILD / do_not_redo rows that constrain it
- `research/DO_NOT_REBUILD.md` KILL-PSS-SR2-PEER-DIFFUSION (line 83): "KILLED — … Peer-state research remains open only as a genuinely new preregistered species that does not condition on the subject lagging recovered peers".
- KILL-PSS-SR3-PARTICIPATION (line 84): "KILLED — … A future species must measure an orthogonal source of durable absorption or selective leadership—not another contemporaneous sector-breadth relief label".
- KILL-RS-DISPERSION-GATES (line 44): "DON'T-TEST — rs is zero-sum tautology (R-4)".
- HOLD-PSS-RH1-RELIEF-HAZARD (line 155) / HOLD-PSS-CR1-CHALLENGE (line 156): "PROSPECTIVE-ONLY ACCRUAL" — historical rows count as zero.
- R6-PREREG-01 M7 ruling (above) caps current-only cohorts at retrospective diagnostic.

### 5. Data / rights / custody blockers named
- Dated historical membership absent at theme level (README:64-68; R3 §2.5 below); `PROPHET_US_EARLY_LEADERSHIP_R3.md:65` — "#7455 … Its current-membership historical windows are explicitly non-PIT, and its reported price-basis qualification has limits."
- B09 `depends_on: ["B00","B04"]` (BUILD_PROGRAM.json) — B04's dossier is a dependency.
- WS wave d4 ("V4-D4 — peer and transmission features") is `status: todo` (`agentos/workstreams/WS-PROPHET-US-V4-RECOVERY.md:594-597`).

---

## B10 — Early Leadership research comparisons

### 1. What exists at BASE, on PR heads, and what is ruled

**At BASE.**
- The design packet exists: `research/prophet_v4/r6_fable_meta_ceo_handoff/baseline_r5/inputs/PROPHET_US_EARLY_LEADERSHIP_R3.md` — :5 "**Status: PROPOSED_FOR_OWNER_REVIEW / NOT_REGISTERED.**"; §5.1 populations N/E (:98-104); §6.2 leave-one-out peer ablation (:147-157, "Propose a leave-one-out peer-strength and breadth ablation through the existing group owner."); §6.1 group-vs-member decomposition (:137-145); delivery graph EL0–EL8 (:306-322).
- The leadership evidence README (BASE) names B10 as consumer: README:62 — "A later B10/H1-compatible experiment must establish whether continuity improves selection on a common eligible population before any score authority."
- Q cards at BASE: `work_cards/Q03.md:44` "Build Consumers: B02, B03, B10, B12"; Q05:44 "B09, B10, B11"; Q18:44 "B05, B06, B12".
- Ruled: R6-D07-01:39 — consumer disposition "B10 | S3 ×2 | BLOCKED | B10 (pinned episode generation + write-time `recorded_at`)"; D07 draft:80 — "B10 consumes S3-episode-registry (null) and S3-macro-join-inputs (`RETROSPECTIVE`). The disposition is `BLOCKED pending a pinned episode store generation and a write-time recorded_at stamp`."
- Ruled: R6-PREREG-01:17 (B2) — "D06 step 1 binds Cell G as the governing measurement law." and :18 (B3) — "Every 'better/earlier than' claim registers its control arms as same-tape computations built by B06: cash; SPY on the same clock with NO forward-fill; a point-in-time sector comparator frozen at decision time or declared `UNAVAILABLE_FIELD`; incumbent V3 on the identical field."
- The incumbent control is frozen at BASE: `engine/prophet_strategy_definition.py:20-24` (SCHEMA `prophet.strategy_definition/v1`, `DEFINITION_ERA = "prophet-strategy-definition-v1-2026-09-20"`, `STRATEGY_ID = "EARLY_LEADERSHIP_SECTOR_ROTATION"`, `STRATEGY_VERSION = "1"`, `ENTRY_POLICY_VERSION = "early-leadership-sector-rotation-entry-v1"`).

**Open PR heads only.**
- #8240: `PROPHET_EARLY_LEADERSHIP_EVIDENCE_V1_2026-09-30.md@6d920952dc:132-146` — "Next scientific step: Do **not** put these features into the live score because this source module exists. The existing B10/H1 scientific owner should compare, on a common eligible population: 1. incumbent selection; 2. transparent stock residual-momentum control; 3. group-only control; 4. incumbent + source-qualified independent peer/group evidence; 5. later, the parsimonious full Early Leadership challenger."; 2026-10-02 repair at :149-162 (issuer_id/security_id joins; B1 lineage tuple `identity_epoch`/`episode_id`/`candidate_generation_id`, `setup_lineage.state=BOUND`).
- #8091: R20/R21 — the H1 source vertical (see B06 above); R20:87 — "The two current source-qualified examples are BKSY / `space_economy` and MAR / `travel`. They are not selected winners, recommendations or backtest results."
- #7772 `2c198dd2cd`: `engine/prophet_research_matrix.py:1-35` — "Point-in-time research matrix spine for Prophet North-Star RQ1. This module is a read-only research projection over existing canonical owners. It never writes B1, Radar, Evaluation/QLedger, candidate, Availability, plan, or publication state."; `DEFINITION = "prophet-north-star-rq1-pit-matrix-2026-09-23"`; `POPULATION_SCOPE = "ACTIVE_CANONICAL_B1_EPISODES_AS_OF_DECISION"`.

### 2. Program status
- BUILD_PROGRAM.json → `units[] (id="B10") → status` = `"SPECIFIED_NOT_DISPATCHED"`; `research_packets` = ["Q03","Q05","Q09","Q10","Q12"]; `decision_ids` = ["D02","D06","D07"].
- RESEARCH_DOCKET.json → Q03/Q05/Q09/Q10/Q12 all `"SPECIFIED_NOT_REGISTERED_OR_DISPATCHED"`.

### 3. Remaining closure the sources name as open
- D07 draft GAPS:87 — "No episode writer is cited that stamps `recorded_at` from the wall clock at write time, and no committed B10 generation manifest pins the acquired registry."
- R20:95-101 — gates 1-7 (B1 identity binding; corporate-action basis; rights/correction lineage; D06 numeric fields; source-blind prereg review; known-answer smoke; natural nightly accrual).
- OPUS_SCIENCE_SEAMS_AUDIT_2026-09-23.md:158 — "None of D03, D06, D07 or D08 can be closed honestly from the current docket."

### 4. DO_NOT_REBUILD / do_not_redo rows that constrain it
- DECISION_REGISTER.json → `decisions[] (id="D02") → blocked_consumers` includes B10; D06 and D07 likewise list B10 (both `OPEN_TECHNICAL_DECISION_FABLE_AUTHORIZED_TO_RESOLVE`).
- DO_NOT_REBUILD KILL rows named as prior looks for this family: KILL-PSS-SR2/SR3 (peer constructions), KILL-FRESH-TICKS-WINDOW / KILL-STAGE-WIN-GATE / KILL-S10-MARGIN-RECLAIM (via R6-PREREG-01:30 m2), KILL-OUTCOME-AUDITION (line 76, per-name timing-tool selection), KILL-FUSED-COMPOSITE (line 51, research/shadow-tier exception for the conditional-fusion challenger only).
- WS do_not_redo :115-118 — "An unbuilt D5 adapter emits no evidence-family envelope. Adapter readiness may accrue outside evidence_families[], but missing/unbuilt is never zero or neutral."

### 5. Data / rights / custody blockers named
- D07 S3 rows: S3-episode-registry `null` (D07 draft:65 — "no store generation is pinned for the B10 decision"); S3-macro-join-inputs `RETROSPECTIVE` (:66).
- D02 OPEN blocks new expert species (see B12); Q03's union depends on it.
- #8240 md:169-171 — "source-owned ThemeState and H1 evaluation/rights admission are separate. No numerical feature definitions, rank, B1/B4, plan, sizing or trading authority are changed."

---

## B12 — genuinely earlier entry

### 1. What exists at BASE, on PR heads, and what is ruled

**At BASE.**
- The binding design law: `PROPHET_US_EARLY_LEADERSHIP_R3.md:217-221` (§8.2 "Earlier discovery does not yet create an earlier licensed entry") — "A genuine earlier-entry experiment needs a declared expert/species policy, accepted geometry, current-data validity, and R2's same-origin cohort design. Its method may differ from the incumbent, but it must be a versioned research challenger and pass the standing construction-equivalence review. It cannot be introduced as an adapter refactor."; EL6 slice at :318 — "EL6 — earlier-entry policy | An actually earlier species-specific entry can earn authority | EL0/EL4, existing expert/geometry/policy owners; no confluence refactor waiver | Same-origin comparison and separately accepted B4/strategy version".
- The entry-availability engine exists at BASE: `engine/prophet_entry_availability.py:511-513` — the validator pins `build_early_leadership_sector_rotation_definition()`; closed output fields (:500-506); `pea:` content id (:527).
- D01 ruled (the confluence seam B4 composition consumes): SEAT_RULING_R6-D01-01:27-36 (contract `signal_gate.validity/v1`; consumer law; caller obligation :34 "load the artifact from its single canonical path at decision time").
- D02 ruled in principle, gated: SEAT_RULING_R6-B02-01:15 — "**D02 — RESOLVED IN PRINCIPLE, admission GATED.** The first extra species is `entry_radar_expert_fire`, anchored ONLY on Radar-owned fields already in `mastermind.entry_event.v1` … It may be admitted only when BOTH hold: (a) `WS:LIVE-ENTRY-RADAR` has frozen and «elided» the forward-projection contract so the B1-consumed relation key is the exact immutable `event_id` (the legacy fallback must be refused, not tolerated), and (b) a committed `forward.parquet` exists. Until then no code for step 2 is written…".
- The anchor vocabulary is closed at BASE: `engine/us_candidate_episode.py:34` — `ANCHOR_KINDS = frozenset({"turn_watch_reset_low"})`, enforced at :216 and :949; `SUPPRESSION_REASONS` (:62-72) includes `ANCHOR_KIND_NOT_REGISTERED` (:63).
- The incumbent B4 policy calibration (the Q18 study B12 consumes) is frozen at BASE (see §6 below).

**Open PR heads only.** No B12-specific artifact exists on the five readable heads; the H1 timing study that shares B12's search family is named at BASE in PREREG.json:170-172 and built as a source vertical on #8091 (R20/R21, `trial_may_start=false`).

### 2. Program status
- BUILD_PROGRAM.json → `units[] (id="B12") → status` = `"SPECIFIED_NOT_DISPATCHED"`; `depends_on` = ["B02","B05","B06"]; `research_packets` = ["Q03","Q04","Q15","Q18"]; `decision_ids` = ["D01","D02","D04","D06","D08"]; `release_limit` = "No adapter-only waiver, tuning on protected outcomes or force-included named winner."
- RESEARCH_DOCKET.json → Q04/Q15/Q18 all `"SPECIFIED_NOT_REGISTERED_OR_DISPATCHED"`; Q04 `decision` = "Identify a bounded species/timeframe policy worth qualification, with exact availability requirements; do not grant confluence waiver via adapter."

### 3. Remaining closure the sources name as open
- R3:333-338 (§13 unresolved decisions) — e.g. :332-333 "Which additional experts may supply structural anchors, and how do pre-B1 observations remain visible without inventing identity? What owner-defined validity permits completed technical evidence to be evaluated during a later session, and what event revokes it?"
- R6-PREREG-01:9 — "No live B4 runtime exists on main (#7581/#7738 are Draft), so no prospective observation has been captured: the amendment below is pre-capture by construction".
- B02 census:185-189 (NOT_ESTABLISHED 4-6): forward.parquet never committed; Radar anchor geometry absent; D02 still open.

### 4. DO_NOT_REBUILD / do_not_redo rows that constrain it
- KILL-FRESH-TICKS-WINDOW (DO_NOT_REBUILD line 126) — closes admission-window widening; "FRESH_TICKS=2 stands".
- KILL-STAGE-WIN-GATE (line 120) — "Stage-2 (and Stage-2∩EC) as a WIN-RATE gate or ranking bonus on the T1/T2 confluence timing entry … KILLED (construction-scoped)".
- KILL-S10-MARGIN-RECLAIM (line 109) — falsified phase-0; "revival needs a NEW species version + fresh prereg".
- KILL-WASHOUT-TURN (line 85) — "KILLED — operator seed dies in test".
- KILL-ROTATION-CYCLE-CONFLUENCE (line 43) — "Rotation × cycle-position entry-confluence | DON'T-TEST".
- All three FRESH-TICKS/STAGE-WIN/S10 kills are expressly prior looks the Q04 study must count (R6-PREREG-01:30).

### 5. Data / rights / custody blockers named
- DECISION_REGISTER.json D02/D08 both list B12 in `blocked_consumers`; both `OPEN_TECHNICAL_DECISION_FABLE_AUTHORIZED_TO_RESOLVE`.
- SEAT_RULING_R6-B02-01:20-21 (open items) — "B02-a: today's HEAD-selected generation and live counts (sparse lane could not read `data/`) — verify from the next nightly receipt, not by dispatch."
- #7734/#7738 constants uncalibrated until measured (R6-PREREG-01:28, M9: "the 50/300 constants get used as costs"; #7738 "Operation constants remain uncalibrated").

---

## Cross-cutting answers

### 6. The Early Leadership frozen control definition and the narrow H1 and B4 freezes

**Early Leadership frozen control definition (at BASE).**
- Path: `engine/prophet_strategy_definition.py`. Version strings: :20 `SCHEMA = "prophet.strategy_definition/v1"`; :21 `DEFINITION_ERA = "prophet-strategy-definition-v1-2026-09-20"`; :22 `STRATEGY_ID = "EARLY_LEADERSHIP_SECTOR_ROTATION"`; :23 `STRATEGY_VERSION = "1"`; :24 `ENTRY_POLICY_VERSION = "early-leadership-sector-rotation-entry-v1"`. Status literals at :67-68: `"scientific_status": "CONTROL_ONLY"`, `"authority_tier": "SHADOW_ONLY"`. All-false authority block :26-36. Builder `build_early_leadership_sector_rotation_definition` :189-197 (content id `psd:<sha256>`); validator refuses any divergence :200-229. Confluence fields at :152-153: `"owner_confluence_gate_may_be_waived": False`, `"owner_confluence_source_session_rule": "next_session_only/v1"`.
- The definition itself carries **no numeric thresholds**; its numeric pre-outcome parameters live in the B4 calibration prereg (below) and in the #7738 constants it mirrors (`B4_ENTRY_POLICY_CALIBRATION_PREREG_2026-09-23.md:11`: "#7738 correctly marks the first B4 `liquidity_fillability` and `gap_velocity` constants as `INITIAL_OPERATION_CONSTANT_NOT_CALIBRATED`"; C1 mirrors them at PREREG.json:69-70 — 50 bps / 300 s; 1.5 / 1.0 / 1.5 ATR).

**Narrow B4 freeze (at BASE).**
- Path: `research/prophet_v4/b4_entry_policy_calibration/PREREG.json`. Version strings: :2 `"schema": "prophet.b4_entry_policy_calibration_prereg.v1"`, :3 `"registered_date": "2026-09-23"`, :4 `"status": "REGISTERED_OUTCOMES_UNREAD"`; amendment A1 pre-capture :26-34. Companion prose: `research/prophet_v4/B4_ENTRY_POLICY_CALIBRATION_PREREG_2026-09-23.md:68-82`.
- Numeric pre-outcome parameters live at (locations only): `population` :42-59; `cells` :61-101 (C0–C7); `outcomes.primary_horizons_sessions` [5,10] / secondary [3,15] :104-105; `evidence_floor` :139-143 (300/50/100); `alias_map`/`distinct_configurations`/`distinct_cell_ids` :144-156; `primary_endpoint`/`primary_horizon_sessions` :157-158; `multiplicity` :159-173 (Holm, family C1–C5, search family includes the EL H10 timing study); `non_inferiority` :174-178; `cost_floor_bps_round_trip` :179-182; `looks`/`futility` :183-194; `decision_law` :195-222. Clock law: cohort start `FIRST_PROSPECTIVE_B4_OBSERVATION_AFTER_PREREG_MERGE`, `historical_backfill: false` (:35-41). No outcome value appears in the file; none was sought.

**Narrow H1 freeze.**
- No frozen numeric H1 registration exists at BASE. What the sources record:
  - The H1 study is named as a search-family member inside the B4 freeze: PREREG.json:170-172 `"search_family_includes": ["EL_H10_timing_study_registered_under_D06"]`.
  - Unit id: `Q05-H1-PEER-PARTICIPATION-ACCELERATION-V1` (R20@410965bd24:6); status `SOURCE_VERTICAL_BUILT_NOT_PROVEN / HISTORICAL_CONFIRMATORY_RUN_BLOCKED` (R20:8, R21:9).
  - Its frozen primary (stated, not yet numeric): R21:92 — "The primary remains paired date-level C2-minus-C1 top-five H10 SPY-excess mark utility on one frozen, source-qualified MOMENTUM population".
  - Its numeric freeze is explicitly NOT done: R20:98 — "the numeric D06 worthwhile-gain/tail-harm fields are not frozen"; R21:88 — "chronological partitions, test count/power and numeric D06 worthwhile-gain/tail limits" still open.
  - Pre-outcome control plane lives on #8192 only: `scripts/check_prophet_h1_prospective_accrual.py@07136c56ec` ("Pre-outcome Prophet H1 prospective-accrual verifier", :2) and the S0 receipt `research/prophet_v4/S0_CAPTURE_INTEGRITY_R2_20261005.json@07136c56ec` (keys only: `h1_admitted`, `claim_limit`, `model_fit_executed`, `production_nightly_verified`, …). Neither file exists at BASE.

### 7. Honest N — every recorded population count (quoted with source and date; nothing computed here)

- **467 episodes / 915 events / 5,435 suppressions** — 2026-08-28 natural acceptance, recorded at BASE in `agentos/workstreams/WS-PROPHET-US-V4-RECOVERY.md:225-226` ("467 lawful episodes / 915 events / 5,435 suppressions"), generation `peg:c025bb50c45f…` (:223); mirrored in SEAT_RULING_R6-B02-01:11 and B02 census:66 ("The 467 / 915 / 5,435 figures are the 2026-08-28 acceptance record, not a 2026-09-23 measurement", census:185).
- **9 committed generation directories (+HEAD.json) = 65 paths** under `data/us_prophet_rank/episodes` — B02 census:64,126-130 (git-tree census only, 2026-09-23; HEAD.json blob not read; which generation is HEAD-selected is UNKNOWN, census:184-186).
- **14 CRI suppressions, reason IDENTITY_UNRESOLVED, first session 2026-08-27, last 2026-10-05**, HEAD `peg:99b34095d177…` — `research/prophet_v4/r6_rescue_20261008/PROOF_AND_FRONTIER.md:94-97` (2026-10-08; "counted only under the active HEAD generation").
- **713 legacy seed keys, no CRI** in the security-master builder — PROOF_AND_FRONTIER.md:87-88 (2026-10-08).
- **R20 source census (2026-09-27, #8091 head)** — R20:73-85: "Curated candidate rows | 2,928 / Eligible curated rows | 249 / Canonical identity resolved | 97 / Owner-labelled momentum | 8 / Sole active equal-weight group | 40 / Ambiguous overlap | 14 / No active membership | 195 / Exact pre-decision SPY calendar witness | 215 / Calendar source unavailable | 34 / Rows clearing all implemented source gates | **2** / Implemented-source coverage | **0.803213%**"; R21:57 restates "2/249 rows, or 0.803213%".
- **H1 prospective accrual counts**: the only recorded figure is the 2 rows / 0.803213% above (R20/R21). The S0 receipt's `h1_admitted` / `claim_limit` keys were read as **keys only** per this packet; their values were not read and are not reported.
- **D07 register population (2026-09-24, adopted 2026-09-27)** — D07 draft:22-29 (S0=3, S1=14, S2=4, S3=2, S4=3, S5=2, S6=3, total 31) and class histogram :35-38 ("OBSERVED_AS_RUN 0 / PUBLIC_INFO_REPLAY 4 / RETROSPECTIVE 5 / null 22"); R6-D07-01:14-15 — "The histogram 0 / 4 / 5 / 22 is the honest current state".
- **B04 six-case census**: "2 COVERED · 2 PARTIAL · 2 BLIND" — B04 census:97 (2026-09-23).
- **Fixture counts** (not live): `tests/fixtures/us_candidate_episode/all_candidates.json` coverage episodes=2, event_count=3 — B02 census:62,139-140.
- **QLedger control leg**: "never been populated on any of 46,630 claims" — WS:108-109.

### 8. Expert union, suppression and displacement accounting

- **Where specified.** Q03 card (:12,16) — "Do additional registered nomination species reveal useful opportunities earlier at the same review burden?" with population "Frozen supported universe and source-defined observation times, including nominees that never originate B1 or never confirm."; R3 §2.2 (:35-41) — "We cannot claim every independent expert can currently originate a candidate."; R3 §5.1 (:98-104) — Population N (owner-native nominations/suppressions) vs Population E (canonical B1 episodes); seams audit m3 (:150) — "Q03 does not register a `positive_label_id` … Repair: register both before any read."
- **Where implemented (BASE).** Four intakes in `engine/us_candidate_episode_intake.py` — `turn_watch_observations` :177 (sole anchor builder), `candidate_observations` :361, `door_observations` :382, `radar_observations` :398; `_unanchored_batch` :321 hard-codes the non-anchor path; closed vocabulary `ANCHOR_KINDS` engine/us_candidate_episode.py:34 with fail-closed refusal (:216, :949) and 10 closed suppression reasons (:62-72). Source accounting must balance — "input == mapped + suppressed … or the run aborts" (B02 census:13, citing scripts/reconcile_us_candidate_episodes.py:429-432@aba2c115bafa).
- **What the sources say is missing.** (a) No second anchor producer exists ("no second anchor producer exists anywhere in the tree", B02 census:34); Radar's store is absent — "`git ls-tree -r --name-only HEAD data/entry_radar` returns only `data/entry_radar/ledger_state.json`, no `forward.parquet`" (census:32,132); D02 admission gated (SEAT_RULING_R6-B02-01:15). (b) Pre-B1 sightings have no persisted plane of their own — R3:100-104 proposes Population N; nothing at BASE implements it (search: `git grep -l -E 'early_leadership|candidate_episode/v1|issuer_excluded|ex_issuer' -- engine scripts` returns no intake-side pre-B1 ledger). (c) Identity coverage: 97 of 249 eligible rows resolved (R20:77). (d) Knowledge-clock seam — "A synthetic identity first ingested `2026-10-09T00:00:00Z` still resolves an observation with `known_at=2026-10-05T20:00:00Z`" (PROOF_AND_FRONTIER.md:110-113; counterexample fixture `b02-identity-knowledge-clock-counterexample.json`). (e) Displacement: the dashboard "episode chip" is a per-ticker plan-book ordinal, NOT a B1 episode (B02 census:50 — "Four distinct 'episode' notions live in this tree…; B03/B04 UI work must not conflate them"); an unscored displaced row stays unscored (R3:110).
- **Displacement accounting in grading**: none at BASE — "Grading has zero episode coupling: `scripts/grade_us_prophet_candidates.py` and `engine/us_prophet_grades.py` contain no `episode` reference at all; the grader's frozen grain is `(stamp_date, ticker, board_definition, horizon)`" (B02 census:50; confirmed at BASE `engine/us_prophet_grades.py:126`).

### 9. Issuer-excluded group breadth/acceleration

- **Where implemented.** At BASE in the existing group owner: `engine/group_flow.py` — `_independent_peer_roster` :168-228 (excludes the focal ticker AND every known alternate listing of the same issuer via caller-supplied `issuer_by_ticker`; peers with unknown identity stay in the denominator), `independent_peer_observation` :230 (lower/upper breadth bounds; no survivor renormalization — README:21-25), `independent_peer_continuity` :316 (retention with `UNAVAILABLE_PRIOR_LEADER_TRANSITION` / `NO_KNOWN_PRIOR_LEADERS` typing, README:38-51). Output schema `prophet.peer_context/v1` (:146), all-false authority (:148-155). On open PR #8240 only: `prophet.peer_ex_candidate/v1` peer receipt inside `prophet.early_leadership_evidence/v1` (engine/prophet_early_leadership_evidence.py@6d920952dc:24; anti-self-confirmation contract md:30-41).
- **Does dated historical ex-issuer group history exist at BASE, or only current theme context?** Sector-level PIT exists; theme/basket-level dated ex-issuer history does not. Evidence:
  - `engine/group_flow.py:650-660` — PIT frames exist ONLY for "The 11 GICS sectors", sourced from `data/breadth/sp1500_pit_membership.parquet`, and are explicitly "NOT fully survivorship-free — the universe is still bounded by names present in the current close cache and classified by the current GICS map".
  - Theme level is current-only: leadership README:66-68 ("Curated thematic baskets still have a historical-membership limitation where their past aggregation can use a current tree… A research consumer must bind the exact dated roster/source before describing a historical theme feature."); R3:65 ("Its current-membership historical windows are explicitly non-PIT"); B09 release_limit ("No … current-membership historical feature", BUILD_PROGRAM.json units[] id=B09); #7604 subtheme funnel docstring ("The current Finviz tree is current-only structure. It is never backdated here.").
  - Forward-only dated membership capture exists only on #8091: R20:49-55 — "the active PIT membership set under `added <= decision_date < removed`" … "Prior rows do not acquire these fields retroactively."

### 10. Every mention of `7772` or "unknown effect" in the files above

- `7772`: **not found** in any scoped file. Searches run: `grep -rn '7772' research/prophet_v4 research/DO_NOT_REBUILD.md agentos/workstreams/WS-PROPHET-US-V4-RECOVERY.md` (all hits are unrelated substring collisions in `news_to_business_impact_20261006/`, `astra_regime_indicator_handoff_20261004/` hashes and a CIK — none is the PR number, and none is in a scoped file); plus `git show <sha>:<path> | grep -n -E '7772|unknown effect'` across every scoped PR-head file (0 hits on all five heads). Note: the inventory hit `research/prophet_v4/r6_program/wave1/RV_7572_5e43db462b5f_2026-09-23.md` is PR **#7572** ("# Independent Exact-Head Review of PR #7572", "STATUS: IN_PROGRESS"), a different PR.
- "unknown effect": two hits, both in scoped program JSONs but under entries outside this census's ID set:
  - `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/DECISION_REGISTER.json:271` — decisions[] (id="D10") → `forbidden_shortcut`: "A plan mistaken for dispatch, replacing a STARTed/unknown effect, Fable default placement or raw provider-spawn fallback."
  - `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/BUILD_PROGRAM.json:1072` — units[] (id="B26") → `release_limit`: "Do not delete original grades/plans, waive unknown effects or claim current production from local files."
  - (Adjacent, not in the scoped file set: `baseline_r5/DECISION_REGISTER.json:169`, `baseline_r5/BUILD_PROGRAM.md:543`, `REVIEW_RELEASE_AND_RECOVERY.md:57,70`, `AUTHORITY_DELEGATION.json:25`, work_cards `*.md:60`.)

---

## Absent / not found

- **#9714 head `ed974b3b09` — not available on host** (`git cat-file -e ed974b3b09^{commit}` fails). Its scoped file `research/prophet_v4/leadership_evidence_v1/source_readiness_20261019/README.md` could not be read; `git cat-file -e HEAD:research/prophet_v4/leadership_evidence_v1/source_readiness_20261019` shows it is absent at BASE too.
- Absent at BASE (probed with `git cat-file -e HEAD:<path>`): `engine/prophet_early_leadership_evidence.py`; `research/prophet_v4/PROPHET_EARLY_LEADERSHIP_EVIDENCE_V1_2026-09-30.md`; `config/prophet_dossier_reason_map.v1.json`; `config/prophet_dossier_lane_families.v1.json`; `config/prophet_source_rights_postures.yml`; `scripts/check_prophet_h1_prospective_accrual.py`; `engine/prophet_research_matrix.py`; `engine/prophet_subtheme_funnel.py`; the whole `research/prophet_v4/r7_program/` tree (this report's directory is new).
- No frozen numeric H1/D06 registration found at BASE (searches: the H1 greps above; PREREG.json read in full; R20/R21 read in full — both state the numeric freeze is outstanding).
- Pattern searches with no hits in the three named engine files: `git grep -E 'early_leadership|candidate_episode/v1|issuer_excluded|ex_issuer' -- engine/group_flow.py engine/us_candidate_episode_intake.py engine/us_prophet_grades.py` → 0 (the issuer-exclusion concept is expressed as `focal`/`issuer_by_ticker`/`excluded_same_issuer` in group_flow.py:168-228, and the episode schemas live in us_candidate_episode.py).
- `7772` not found in scoped files (searches listed in §10).
- Which episode generation `HEAD.json` selects today, and today's live counts — not established (B02 census:184-186 names the missing artifacts; this census did not read `data/`).
- Research inventory search `git ls-files research/prophet_v4 | grep -i -E 'leader|emerg|h1|b4|q03|q04|q05|q18|entry|suppress|displace'` returned exactly 10 paths; all were read and their first heading lines captured: `B4_ENTRY_POLICY_CALIBRATION_PREREG_2026-09-23.md` ("# Prophet B4 Entry-Policy Calibration — Prospective Same-Tape Preregistration"), `b4_entry_policy_calibration/PREREG.json` (JSON, no heading; schema key at :2), `leadership_evidence_v1/README.md` ("# Prophet Leadership / Sector Rotation Evidence v1"), `r6_fable_meta_ceo_handoff/baseline_r5/inputs/PROPHET_US_EARLY_LEADERSHIP_R3.md` ("# Prophet US R3 — Early Leadership: first end-to-end vertical"), `work_cards/Q03.md` ("# Q03 — High-recall expert union and independent origination"), `Q04.md` ("# Q04 — Same-origin daily/multi-day/intraday entry timing"), `Q05.md` ("# Q05 — Group leadership, member selection and self-confirmation"), `Q18.md` ("# Q18 — Incumbent B4 policy calibration"), `r6_program/wave1/RV_7572_5e43db462b5f_2026-09-23.md` ("# Independent Exact-Head Review of PR #7572"; path matched the grep only via the `b4` substring inside its embedded hex id `5e43db462b5f`).

## Outcome files avoided

- No file under `data/` was listed or read; no ledger, scoreboard, track-record, returns, forward-grade or outcome artifact was opened; no S0 JSON values were read (keys only, per packet).
- Files read that sit nearest the boundary, for the record: `research/prophet_v4/r6_rescue_20261008/cri-chronology-clock-read.json` (a clock-evidence read carrying one matched close price and `integrity_status: stale_price_basis` — read because the packet scopes `r6_rescue_20261008/` in full; it contains no realized return, grade or trial result) and `research/prophet_v4/b4_entry_policy_calibration/PREREG.json` (pre-outcome registration only; `status: REGISTERED_OUTCOMES_UNREAD`). No read had to be abandoned mid-file.
