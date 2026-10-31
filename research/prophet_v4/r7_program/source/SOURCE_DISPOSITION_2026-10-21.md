# ORCH-SOURCE disposition — Prophet R7 Stage 2 / Stage 3 / Stage 6 (2026-10-21)

Author: ORCH-SOURCE (Opus, fable-mode) under Fable Meta-CEO seat 69eb9a1c. Base for every fact and lane:
macro main `e5dd30c6344e4b62a0beba054ac4da97e00bab36` (BASE). Inputs: masterplan
`Prophet_End_to_End_Masterplan_Fable_2026-10-20.md` (A1 :836-866, A3 :905-916, Stage 3 :438), R6 effective
`BUILD_PROGRAM.json` / `DECISION_REGISTER.json` at BASE, census E (`$S/ret/CENSUS_E_B4_ENTRY_SUBSTRATE_2026-10-21.md`,
sha256 e5a09708bd1c), census J (`$S/ret/CENSUS_J_JOURNEY_ALERTS_2026-10-21.md`, 6c13943f5bde), B23 harness
design (this directory, fe6b9188ed21), INTEL disposition F5 (`../intel/INTEL_DISPOSITION_2026-10-21.md:395-398`).
This document is a disposition, not an acceptance: every verdict below is a recommendation to the seat.
Every R6 row at BASE is `SPECIFIED_NOT_DISPATCHED` (BUILD_PROGRAM) / `OPEN_TECHNICAL_DECISION_FABLE_AUTHORIZED_TO_RESOLVE`
(DECISION_REGISTER); "status" below is the observed source state, not the catalog flag.

Verdict vocabulary: READY · READY-AFTER-DESIGN-SPEC · BLOCKED-CUSTODY · BLOCKED-DATA · NEEDS-FABLE-DECISION.
A unit can carry two verdicts when it has separable halves; each half names its own next lane.

## 1. Units

### B00 — Bind and review the integrated master specification (D10)
- Evidence: R6 effective package is in tree (`research/prophet_v4/r6_fable_meta_ceo_handoff/effective/*`). The R7
  masterplan that this program executes is NOT in tree at BASE (only `/Users/chriswong/Downloads/…`); the B23 lane
  independently hit the same gap ("the 2026-10-20 masterplan file is not in-tree at BASE"). Masterplan A1 :838:
  "Adopt this convergence contract over #6805/#6817; bind custody and independent scope review."
- Owner/custody: seat (Fable). Independent scope review = DESIGN orchestrator's design disposition + a reviewer lane.
- DO_NOT_REDO: R6 effective package; the seat's #6817 ack 6306863736.
- Blocking: masterplan bytes are not source-published, so lanes cannot cite it by path@sha.
- Verdict: **NEEDS-FABLE-DECISION** (seat act). Next: seat commits the masterplan (or a pinned excerpt of A1/A3/§6/§7.3-7.4)
  under `research/prophet_v4/r7_program/` in its next records PR; no lane.

### B01 — Complete owed-session and source-bound delivery (D10)
- Evidence: seat Stage 1 lane `pro-receipt-truth-20261021-r1` returned → PR #9921 (`claude/prophet-r7-receipt-truth`)
  with review lane; clock census `../CLOCK_PROVENANCE_REFUSAL_CENSUS_2026-10-21.md` (seat lane `pro-clockprov`).
- Owner/custody: seat Stage 1 (sole writer of #9921).
- DO_NOT_REDO: both seat lanes; this orchestrator was told not to duplicate them.
- Verdict: **BLOCKED-CUSTODY** (correctly held by the seat; not a defect). Next: none from SOURCE. B23/B05 consume B01's
  next-refresh proof only after #9921 lands.

### B02 — Preserve canonical episodes and qualify extra anchors (D02, D10)
- Evidence (canonical half, DONE at BASE): B1 plane `engine/us_candidate_episode.py`; durable writer
  `scripts/reconcile_us_candidate_episodes.py` (#6405, 2026-08-25) runs nightly-only (`daily.yml:6204` schedule-only,
  `config/dag.yml:1899-1901` `args: [--nightly]`). Its durable run stamps write-time `recorded_at` from `_now()`
  (`:624-629`, `:74`) and preserves committed clocks on re-run (`engine/us_candidate_episode.py:837`). See §3 item R2.
- Evidence (anchor half): D02 open (register `blocked_consumers` B02/B10/B12/B14/B17).
- Owner/custody: B1/Stock Identity owners; no open PR in the top-100 open-PR file census touches the reconciler or
  `engine/us_candidate_episode.py`.
- DO_NOT_REDO: the B1 plane, reconciler, generation manifest; no surrogate ticker/date episodes.
- Verdict: canonical half **READY** for one hardening build (packet `pro-source-b1recordedat-20261021`, §3 R2);
  anchor half **NEEDS-FABLE-DECISION** (D02).

### B03 — Deliver the lossless searchable opportunity field (D10)
- Evidence: B3 `engine/prophet_candidate_state.py` (`prophet.candidate_state/v1`); masterplan A1 :841 "Reuse accepted
  pool proof; finish complete entitled owner-visible search and displaced-name consumer paths."
- Owner/custody: `engine/prophet_candidate_state.py` is touched by #9369 (`claude/ssd-prophet-native-batch-20261014`,
  draft 858e11a4 — head not on host, diff unread). Search/board surfaces collide across #9495/#8444
  (`scripts/build_site.py` old :5680 both; `templates/_us_board_cards.html.j2` :286-313 vs :288; census J §2).
- Verdict: **BLOCKED-CUSTODY**. Next: none until #9369 and #9495 land or hand back; census J §2 is the rebase map.

### B05 — Close B4 source validity and mandatory-fact integration (D01, D04, D08, D10)
- Evidence: D01 is on main (`engine/signal_gate.py:707` emits `signal_gate.validity/v1`; consumer
  `engine/prophet_entry_availability_sources.py:232-301`; strategy identity `next_session_only/v1`
  `engine/prophet_strategy_definition.py:153`; `tests/test_signal_gate_validity_contract.py`). The same-read join does
  not exist: `build_native_factual_assessment_result` (pcs:1092) → `verified_pair()` (:739) and
  `read_native_b4_owner_inputs` (sources:786) have no common caller; `evaluate_runtime_entry_availability` (:660) has
  test callers only; `scripts/build_stock_library.py:1604-1612, 2013-2017` passes `entry_availability=None`.
  Quote contract is closed: `_QUOTE_KEYS` (availability:84) carries no bid/ask/NBBO.
- Owner/custody: B4 sources/policy files unheld in the open-PR census; `engine/prophet_entry_availability.py` held by
  #9731 (sol/*, armed); `build_stock_library.py` held by #9495/#9369; `engine/live_quotes.py` NBBO = #7734
  (sol/*, draft, mastermindx-3) and #9639.
- Verdict: same-read composition **DONE (lane), ACCEPTED at source level by ORCH-SOURCE** — lane
  `pro-source-b05sameread-20261021-r1`, ubuntu1, rc=0 04:24Z, commit `39b2767ffe21` on
  `~/lanes/wt/pro-source-b05sameread-20261021-r1`; diff = `engine/prophet_b4_same_read.py` (+411),
  `tests/test_prophet_b4_same_read.py` (+582), `.github/ci/legacy-jobs.yml` (+1, job `prophet-anticipation-intake`, which is `gate: data`
  (legacy-jobs.yml:27085) — packed only by nightly/scheduled `data-health.yml`, NOT by PR CI; §4 item 7); lane-run suites 256 passed (same_read 30, strategy_definition 143, candidate_state 64, validity 19).
  Copies: `$S/ret/b05/`. Spec 1-8 each has a named test (key set/determinism :156; one read + no projector :195;
  happy = direct evaluator, not ENTRY_OPEN :247; binding :299; passthrough :350; bytes changed :382; retraction :405;
  D01 x4 :462-498; `classify_nbbo` 7 outcomes + boundary :532-548; early close :564). No wall-clock read
  (`datetime` used only for `fromisoformat`, module :109/:160); `decision_at` = owner `clocks.live_pass_ts`.
  Review notes for the independent lane: (a) six module-raised `RuntimeOwnerFactError` on a *qualified* read with
  no binding/clocks/attestation/live clock (:344, :347, :190, :194, :375, :379) propagate uncaught — fail-loud, which
  contradicts the docstring's "every absent mandatory owner fact types UNAVAILABLE_DATA"; the reviewer rules whether
  to route them through the existing catch; (b) `read_native_b4_owner_inputs` is not inside a try (it returns typed
  refusals at BASE); (c) D01/happy tests monkeypatch the evaluator to inject geometry/metric fixtures and assert the
  module itself passed `{}` — confirm that assertion; (d) GAP: `lib/nyse_calendar.py:10-13` models no early close —
  2026-11-27 13:00 ET half day is an ordinary session; only `engine/prophet_entry_policy.py:68-74` knows it. Independent
  review DONE: `pro-source-b05review-20261021-r1`, ubuntu1, commit `e4433f5713d6`, **PASS_WITH_NOTES** — spec 1-8
  PASS; A1 NOTE: the six raises (note a) are correct fail-loud reader-contract guards, unreachable at BASE, but the
  docstring (:282-285) overstates coverage; A8 NOTE: the CI line is data-gated, not per-PR. Report:
  `B05_SAME_READ_REVIEW_2026-10-21.md` (this folder). Ships via a seat claude/* PR with the test moved to a PR-gated
  job (§4 item 7). Wiring into the builder **BLOCKED-CUSTODY** (#9495/#9369). Any positive (non-UNAVAILABLE) B4 state
  **BLOCKED-DATA**: no native geometry/metric owner exists (sources docstring, census E Q2). NBBO **BLOCKED-CUSTODY**
  on #7734 plus a D08 decision (§4).
- #7734 review finding to route (not ours to fix): its diff drops `early_close`/`is_session` from
  `_us_settle_window`; `tests/test_live_quotes.py` is not in any CI job (census E Q8). `lib.nyse_calendar` models no
  early closes, so D01's "shortened-session case" has no source fact at BASE.

### B07 — Ship the first research-to-watch journey (D05, D09)
- Evidence: masterplan A1 :845 "Compose #9495/#8444/#9294, real watch readback and truthful unavailable-entry
  branch." Depends B03/B04/B05/B20. Watch persistence owners: WatchStore/`lib/user_prefs.py` (held by #9774).
- Owner/custody: #9495 (mastermindx-2), #8444 (sol/*), #9294 hold the journey surfaces; collision fence written.
- Verdict: **READY-AFTER-DESIGN-SPEC** + D05 **NEEDS-FABLE-DECISION** for the saved-state receipt. Packet
  `$S/pk/pro-source-b07journey-20261021.md` (placeholders `__DESIGN_SPEC__`, `__OWNED_FILES__`), unlaunched.

### B20 — Build the shared flagship workspace and design system views (D09, D10)
- Evidence: masterplan A1 :858. DESIGN orchestrator owns the spec (`research/prophet_v4/r7_design/`).
- Owner/custody: shared files are hot — `templates/_prophet_workspace.css.j2` (#9495 rewrites 1-232, #9566 merged same
  region, #9294 appends after 236), `templates/theme.js` (#9495/#9294 :5980-6325, also #9650, #9599).
- Verdict: **READY-AFTER-DESIGN-SPEC**; owned files must be new partials or wait for #9495. Packet
  `$S/pk/pro-source-b20workspace-20261021.md`, unlaunched.

### B21 — Integrate meaningful alerts and durable user actions (D05, D11)
- Evidence (census J §4-§8): opt-in lives in `lib/user_prefs.py` (held by #9774) with `ALERT_CATEGORIES`; the drain
  enforces eligibility and dedupe with at-most-once delivery and quarantine; there is no correction or revocation of
  a sent alert; no Prophet module produces or enqueues a user alert today.
- Owner/custody: alert drain/delivery = existing alerts owner (unheld); user_prefs = #9774.
- Contract DONE: lane `pro-source-b21contract-20261021-r1` (ubuntu3, commit 6eed43cb, STATUS DONE) →
  `B21_ALERT_STATE_MACHINE_CONTRACT_2026-10-21.md` (465 lines, sha256 3f75cf6b3403), accepted by ORCH-SOURCE with
  the notes below. Contract: eligible kinds are B1/B3 lifecycle events only (`episode_terminal`,
  `emergence_triggered`, `corrected_material`, `retracted`, `superseded`; `episode_opened` optional, recency-gated);
  never a quote refresh, freshness change, UNESTIMABLE/UNAVAILABLE side or B4 transition; id
  `prophet|<kind>|<episode_id>|<from>-><to>|<b1_event_id>|<user_id>`; subscription (a) = one `ALERT_CATEGORIES`
  member + a designated named watchlist (fif precedent), new store forbidden; corrections are NEW outbox rows with
  `corrects_fire_event_id`; drain stale guard `not_after` → `mandatory_fact_stale`.
- ORCH-SOURCE notes on acceptance: (1) the contract's reason for excluding B4 transitions ("a same-read caller would
  be a new store") is too strong — the B05 same-read composer is pure and stores nothing; the exclusion still holds
  on the two other grounds it gives (ENTRY_OPEN alert = price alert in disguise; nothing persists a B4 series, and D11
  rule 3 forbids persisting ENTRY_OPEN). (2) U1 (`lib/user_prefs.py`, `tests/test_alert_prefs.py`) is
  **BLOCKED-CUSTODY** on #9774 (`claude/cs-v2-u2-ship`, the cs-v2 lane whose head 9807f906 appends
  `cs_saved_scenario` to the same tuple), not READY; U3's `config/dag.yml` row is held by #9852/#9774/#9590 and is a
  seat placement act. (3) U4 (producer PATCH of its own unsent `alert_outbox` rows to `suppressed`) and U5 (drain
  `decide_row` change) touch delivery infrastructure — out of this orchestrator's scope (contracts only) and
  consequential enough for one independent review. (4) the quarantined-original correction copy is an open ruling.
- Verdict: contract **DONE**; build U2 (pure producer core, new file) is technically READY but **NEEDS-FABLE-DECISION**
  (D05 + D11, and the BUILD_PROGRAM dependency on B07/B20 that the contract proposes to waive for U1–U7); U1
  BLOCKED-CUSTODY (#9774); U8 end-to-end proof BLOCKED on human-only gates (`ALERT_DRAIN_ENABLE`, recipient,
  entitlement, copy ratification).

### B22 — Deliver a truthful unified track record (D11)
- Evidence: masterplan A1 :860 "Finish #7399 truthful effective-ledger record". #7399 is sol/* draft 41ca9354, head
  not on host; depends B06 (INTEL-owned). This orchestrator's lanes are barred from outcome data.
- Verdict: record content **BLOCKED-CUSTODY** (#7399 + B06/INTEL); UI **READY-AFTER-DESIGN-SPEC** — packet
  `$S/pk/pro-source-b22record-20261021.md`, unlaunched.

### B23 — Qualify reliability and operating budgets (D11)
- Evidence: B23 harness design returned (`B23_LATENCY_RELEASE_HARNESS_DESIGN_2026-10-21.md`, lane commit
  4490397b on ubuntu2, STATUS DONE). Key facts: no field metric exists in served code (zero
  PerformanceObserver/LCP/INP/CLS hits); owner A `scripts/capture_page_evidence.py` measures no timing and has no
  320/768 viewport; owner B `ux-evidence/_tools/*` supports arbitrary width + real-session CDP auth; incumbent beacon
  `templates/theme.js` mmTrack → `POST /api/collect` (`app/main.py:520`) is the only lawful field path. The
  80.420 s / 197-object diagnostic is not in tree (only the masterplan holds it). Masterplan A1 :861 also names #9369's
  real-consumer latency evidence (2.770 s → 1.552 s), unread because #9369's head is not on host.
- Build units from the design: BU1 timing + 320/768 on owner A **READY**; BU4 local-serve request journal **READY**;
  BU5 journey/report generator **READY**; BU2 code READY, entitled run **BLOCKED** on a live CDP session (D11-a);
  BU3 field `web_vitals` wire **NEEDS-FABLE-DECISION** (D11) and touches `templates/theme.js` (held by
  #9495/#9294/#9650/#9599).
- BU1 lane DONE: `pro-source-b23bu1-20261021-r1`, ubuntu2, rc=0 04:35Z, commit `155769840281` (BASE e5dd30c6); diff =
  `scripts/capture_page_evidence.py` (+206/-2), `tests/test_capture_page_evidence.py` (+220), no CI edit (extends
  an existing suite); 85 passed; `--self-check` ok; default run = BASE manifest + 73 null timing keys only
  (12 states x 6 + `timing_basis`); TOOL_VERSION 1.4.0; viewports `narrow-320` (320x720), `tablet-768` (768x1024).
  ACCEPTED source-level by ORCH-SOURCE (no independent review owed: dev tooling, not a consequential change).
  Lane GAP: the design file is not at BASE (it lives only on the seat branch) — heights fell back to the packet's.
- BU4+BU5 lane launched 04:38Z stacked on the BU1 commit (`pro-source-b23bu45-20261021-r1`, ubuntu2), design facts
  inlined because the design file is absent at BASE; ships after BU1 in the same or a follow-on seat PR.
- Verdict: harness **READY** (BU1 DONE; BU4/5 RUNNING); B23 UI surface
  **READY-AFTER-DESIGN-SPEC** — packet `$S/pk/pro-source-b23ui-20261021.md` (`__HARNESS_DESIGN__` now fillable).

### B26 — Execute phased flagship cutover and rollback proof (D10, D11)
- Evidence: depends B25 (not started). B23 design Q7 maps the eight release rungs to incumbent controls
  (`app/deploy/live-rollback.sh:1-48`, render receipt, `?v=` stamps, `/api/health`, `prophet/health.json`).
- Verdict: **NEEDS-FABLE-DECISION** (D11 shape) and dependency-blocked on B25. Next: none now.

### B28 — Accept US program scope and prepare market-native reuse (D11, D12)
- Evidence: depends B26 + B27 (INTEL draft `../intel/B27_RETAINED_SLEEVES_DISPOSITION_DRAFT_2026-10-21.md`).
- Deviation: the commission called the latency harness "B28"; masterplan A1 and the register assign latency to B23
  and scope acceptance to B28. The harness was run as B23.
- Verdict: **NEEDS-FABLE-DECISION** (terminal Fable acceptance act), dependency-blocked on B26.

## 2. Decisions

### D01 — Source-session validity and revocation
- Status: DECIDED and IMPLEMENTED on main (DEC-PROPHET-US-D01-CONFLUENCE-VALIDITY-CONTRACT; files in B05). Register
  completion artifact still owed: "exact source/head, independent review and real owner-chain evidence" plus the
  return to #7581 finding 5789777976.
- Open sub-facts: v1 has no revocation beyond retraction; shortened sessions are not modelled (`lib.nyse_calendar`).
- Verdict: **READY** to close — B05 lane DONE (39b2767ffe21): four D01 cases through the real composer (prior
  completed session valid next session; late emit UNKNOWN not FAIL; expired window UNKNOWN; lineage mismatch UNKNOWN).
  Independent review DONE (e4433f5713d6, PASS_WITH_NOTES). Remaining: seat PR, then the seat posts the closure on #7581's carrier
  (seat act). Shortened-session sub-fact stays an open calendar-owner GAP (B05 note d).

### D02 — Independent anchors and episode admission (register meaning)
- Verdict: **NEEDS-FABLE-DECISION**; no SOURCE consumer needs a new anchor species in this wave. The commission
  glossed D02/D03 as "entry-language rules"; the register and masterplan A3 :906-907 define them as anchors and source
  rights. Entry language is addressed in §4 under its real owners (B4 state vocabulary + D09).

### D03 — Source histories and rights (register meaning)
- Verdict: **NEEDS-FABLE-DECISION**, owned in practice by INTEL (B04/B08/B09/B16/B18 consumers). SOURCE's only
  dependency: NBBO rights for #7734's feed-only bid/ask (census E Q3), which must be a D03 matrix row before any
  NBBO fact enters B4.

### D05 — Durable user decision/thesis mapping
- Evidence: WatchStore + `lib/user_prefs.py` (#9774); census J: alert opt-in is per-category in user_prefs.
- Verdict: **NEEDS-FABLE-DECISION**; the B21 contract lane supplies the subscription-option evidence (Q3) the
  decision needs.

### D08 — Fill, costs, latency and capacity
- Evidence: B4 has no NBBO and fails fillability to UNKNOWN; #7734 adds feed-only NBBO; register forbids "missing
  quote treated as zero cost". Masterplan A3 :913 "preserve B4's floor until measured-range adjudication."
- Verdict: **NEEDS-FABLE-DECISION** (whether and how a qualified NBBO enters the closed `_QUOTE_KEYS`). The commission
  glossed D08 as "latency acceptance method"; D08 latency is decision/observation latency for fills. Page latency
  acceptance is D11/B23.

### D11 — Release, telemetry and rollback
- Evidence: B23 design Q5/Q7/Q8; D11 rule `SEAT_RULING_R6-D11-01_2026-09-23.md:19` "ENTRY_OPEN is never persisted.
  Today no producer writes the B4 state to site/ or data/."
- Verdict: **NEEDS-FABLE-DECISION** (release-proof shape, field wire, and the ENTRY_OPEN persistence conflict in §3 R1).

## 3. ROUTED-FROM-INTEL (seat routing F5, 03:5xZ) — owner = SOURCE

### R1 — Nightly caller of the #7581/#7738 B4 runtime library
- Facts: library merged, no caller (B05 evidence). B4 prereg `B4_ENTRY_POLICY_CALIBRATION_PREREG_2026-09-23.md:33`
  requires decision-time bid/ask and NBBO timestamp; `:64` "After #7734 and #7584 are accepted … extend the existing
  prospective evaluation path … append-only decision-time stamps … must not create a new outcome authority. The first
  run is capture-only." `PREREG.json` `reuse_law.outcome_store`: "reuse an incumbent prospective evaluation ledger".
- Conflict: D11 rule 3 (above) forbids persisting ENTRY_OPEN; prereg capture needs the evaluated state recorded.
- Collisions: placement files `daily.yml` / `config/dag.yml` are held by #9852, #9774, #9677, #9639, #9590, #9574,
  #9450 — a lane must not edit them; the seat adds the workflow step. `build_stock_library.py` = #9495/#9369.
  #7734 (`engine/live_quotes.py`) gates the NBBO capture. #9714 (`engine/group_flow.py`,
  `research/prophet_v4/leadership_evidence_v1/*`, head ed974b3b not on host): no file overlap. #9821
  (cac29b29, sol/*, mastermindx-2: `engine/sue.py`, `tests/test_us_prophet_fusion.py`, `tests/test_ci_pack.py`,
  `.github/ci/legacy-jobs.yml`, earnings_semantics research): no overlap beyond the shared CI file (disjoint
  insertions). #7929: not found in tree (census E Q7); no overlap.
- Verdict: **BLOCKED** — BLOCKED-DATA (every row would be UNAVAILABLE_DATA until geometry/metric owners exist),
  prerequisite B05 lane return, #7734 acceptance (BLOCKED-CUSTODY), and **NEEDS-FABLE-DECISION** on the capture
  target. Packet `$S/pk/pro-source-b4nightly-20261021.md` written, unlaunched (placeholders `__SAME_READ_HEAD__`,
  `__CAPTURE_TARGET__`, `__FROZEN_SPEC_AFTER_FABLE_RULING__`, `__TESTS_AFTER_FABLE_RULING__`): report mode by default,
  durable append only with `--nightly` + `nightly_advance_enabled()`, off the render path, consumer-fence test.

### R2 — Write-time `recorded_at` episode writer (prospective only, no backfill)
- Facts: already exists at system level. `scripts/reconcile_us_candidate_episodes.py:1` "Nightly-only immutable-
  generation writer"; `:624-629` durable = nightly and not replay, refuses without `nightly_advance_enabled()`
  (`engine/ledger_lane.py:24-36`), `run_clock = _canonical_recorded_at(recorded_at if recorded_at is not None else
  _now())`. No caller passes `--recorded-at` (daily.yml:6204, dag.yml:1899-1901). Residual: the CLI still accepts
  `--recorded-at` (`:650`) in durable mode — an override path for a write-time clock. D07 draft S3 :65 ("caller-
  supplied … not stamped by the writer at write time") is accurate for `reconcile()` but stale at system level.
- Collisions: none — reconciler, `engine/us_candidate_episode.py` and their tests are unheld; #9714/#9821/#7734/#7929
  do not touch them.
- Verdict: **READY** — packet `$S/pk/pro-source-b1recordedat-20261021.md` (C1, `main()` only: refuse `--nightly`
  without `--replay` plus `--recorded-at` via the existing `ReconcileRefused`, before any read/write). Unlaunched per
  the seat's "no new lanes beyond budget". B10 also needs a committed episode-store generation pin — registration act
  for INTEL/B10, not SOURCE.

## 4. Decisions for Fable (recommendations)
1. **D01 wording.** Keep `signal_gate.validity/v1` + `next_session_only/v1` as the accepted contract; close the register
   row on: B05 same-read tests through the real composer, one independent review lane (DONE, PASS_WITH_NOTES), seat note on #7581. Record two
   explicit v1 limits instead of inventing rules: no revocation beyond retraction; shortened sessions not modelled, so a
   half-day decision session keeps confluence UNKNOWN until a calendar owner models early closes.
2. **D02/D03 vs "entry-language rules".** Rule on the register meaning (anchors; rights). For entry language: the only
   user-facing B4 vocabulary is the B4 state/refusal enum; UNAVAILABLE_DATA renders as "entry unavailable — <owner
   reason>", never a maturity stage and never a Buy; a quote refresh never relabels an assessment. Bind that as a D09
   design constraint for B07/B20 rather than a new decision.
3. **D05 alert semantics.** Adopt the B21 contract: subscription (a) (one `ALERT_CATEGORIES` member, merged after
   #9774, plus the designated named watchlist; no new store); eligible change = the closed B1/B3 lifecycle set, never
   a quote refresh, freshness flip, UNAVAILABLE/UNESTIMABLE side or B4 transition; corrections are new outbox rows
   carrying `corrects_fire_event_id`; a sent original is never edited; an effect-unknown original gets no correction
   row (typed count only). Rule separately: (i) whether the B07/B20 dependency is waived for the producer core,
   (ii) the producer's own-row PATCH to `suppressed` (U4), (iii) the drain `not_after` guard (U5) — both with one
   independent review — and (iv) the copy for a correction whose original is effect-unknown.
4. **D08 NBBO.** Do not extend `_QUOTE_KEYS` until #7734 is accepted (with its early-close regression fixed and
   `tests/test_live_quotes.py` in CI) and NBBO rights sit in the D03 matrix. Until then fillability stays UNKNOWN and
   `classify_nbbo` (B05) is evidence only.
5. **D08 "latency acceptance method" (the commission's sense) → D11.** Accept the B23 design: lab p75 over N=25 cold
   loads per cell (4 widths × EN/ZH × light/dark), labelled `lab_p75_*`, never reported as field; field p75 only via a
   `web_vitals` wire on the existing beacon (BU3), which D11 must accept or explicitly decline.
6. **D11 release-proof shape + ENTRY_OPEN.** Allow R1 capture to record the evaluated B4 state only in a
   research-capture-only append ledger reused from the incumbent prospective evaluation path, with no product reader,
   never under `site/`, guarded by a consumer-fence test; D11 rule 3 continues to bind every served surface.
7. **CI placement (material, affects shipped work).** The COMMON lane rule appends new tests to
   `prophet-anticipation-intake`, which is `gate: data` (`.github/ci/legacy-jobs.yml:27085`): `scripts/run_ci_pack.py`
   packs it only from `data-health.yml --gate data` (nightly `workflow_run`, 13:30 UTC schedule, dispatch), never on a
   PR. #9921's `tests/test_prophet_whynot_receipts.py` sits in the same job (main legacy-jobs.yml:27234), so #9921's
   new cases were never PR-gated. Recommendation: when shipping, put pure-code suites in a `gate: code` job —
   B05 → `signal-gate-pair-coherence` (code, no `paths:`) or `washout-turn-organ` (code; extend `paths:` to the new
   module); B23 BU1/BU4/BU5 → `product-experience-capture` (code, no `paths:`, already runs
   `test_capture_page_evidence.py`); consider the same move for the whynot suite. Amend `$S/pk/common_build_rules.md`
   before the next build wave. This is a placement change, not a guard change.

## 5. Packet set returned for seat acceptance
| Packet (`$S/pk/`) | Class | State | Trigger |
| --- | --- | --- | --- |
| pro-source-b05sameread-20261021 | build C2 | DONE r1 ubuntu1 39b2767ffe21 (3 files, 256 passed); ACCEPTED source-level; review PASS_WITH_NOTES | seat claude/* PR, CI line moved to a PR-gated job (§4 item 7) |
| pro-source-b05review-20261021 | review C1 | DONE r1 ubuntu1 e4433f5713d6 (1 file) **PASS_WITH_NOTES**; report copied to `source/B05_SAME_READ_REVIEW_2026-10-21.md` | independent review of B05 (spec 1-8 + attack surfaces A1-A8); report `source/B05_SAME_READ_REVIEW_2026-10-21.md` on the lane branch |
| pro-source-b23harness-20261021 | census | DONE r1 ubuntu2, 4490397b | accepted by ORCH-SOURCE; report here |
| pro-source-b21contract-20261021 | census | DONE r1 ubuntu3, 6eed43cb | accepted with notes; report here |
| pro-source-b1recordedat-20261021 | build C1 | unlaunched, READY | seat acceptance (R2) |
| pro-source-b4nightly-20261021 | build | unlaunched, BLOCKED | B05 return + #7734 + Fable ruling (R1) |
| pro-source-b23bu1-20261021 | build C1 | DONE r1 ubuntu2 155769840281 (2 files, 85 passed); ACCEPTED source-level | seat claude/* PR (no independent review owed) |
| pro-source-b23bu45-20261021 | build C1 | RUNNING r1 ubuntu2 (BASE = BU1 lane commit 15576984, launched 04:38Z) | BU4 lab-serve journal + BU5 report generator; design facts inlined |
| pro-source-b07journey / b20workspace / b22record / b23ui | build | unlaunched | design spec acceptance |
