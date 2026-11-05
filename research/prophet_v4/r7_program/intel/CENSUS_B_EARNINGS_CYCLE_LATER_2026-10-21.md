# Census B — Earnings and Cycle sleeves, portfolio context, retained later sleeves (2026-10-21)

ROUTE: research / CLASS C1. Read-only evidence census at BASE `e5dd30c6344e4b62a0beba054ac4da97e00bab36`
(HEAD of `lane/pro-intel-censusB-20261021-r1`, clean worktree; worktree is sparse in `data/`, `site/`,
`mockups/`, `verify_shots/` — no `data/` path was read). No file outside this report was modified.
Open PR heads were read only via `git show <sha>:<path>` / `git cat-file -e <sha>^{commit}`.
PR #9821 head `cac29b2909`: **not available on host** (`git cat-file -e cac29b2909^{commit}` → fatal),
so its `PROFITABILITY_INGRESS_2026-10-19.md` could not be read; no network fetch was attempted.

Line numbers for in-repo files are line numbers at BASE. PR-head line numbers are line numbers in the
`git show` output for that head.

---

## B08 — Expand comparable event and expectation sources

**1. What exists at BASE (quoted).**
- The earnings-semantics carrier (research docs merged at BASE; code carrier PR #8189): the versioned
  extraction `numeric-sue-compat-v1.1` with "Default remains `legacy`" and "No consensus claim is
  created" — `research/prophet_v4/earnings_semantics_v1/README.md:27-34`; the pure evidence functions
  list (comparable reported changes, true expectation surprise, fixed-contributor revisions,
  per-share transmission, dossier) — `README.md:97-116`. Implemented in `engine/sue.py` at BASE:
  `SUE_COMPAT_VERSION = "numeric-sue-compat-v1.1"` (`engine/sue.py:102`), `reported_change`
  (`:339`), `factual_dossier` (`:819`), `class IssuerGuidance` (`:967`), `guidance_delivery`
  (`:1004`), `guidance_change` (`:1106`), `earnings_evidence_brief` (`:1173`), `profitability_bridge`
  (`:1439`), `earnings_valuation_scenario` (`:1521`), `cash_flow_reconciliation` (`:1670`).
- Q06 source work: `Q06-SCR-01/v0.1` "comparable quarterly GAAP revenue growth =
  ((current-quarter total net sales / same-quarter-prior-year total net sales) - 1) * 100" —
  `research/prophet_v4/r6_program/wave3/Q06_SEC_COMPARABLE_REVENUE_PROSPECTIVE_CAPTURE_2026-09-26.md:20-24`;
  "the AAPL case is an exact source-construction exemplar; public-information replay is diagnostic
  only; confirmatory evidence begins with prospective capture after registration" — `:159-162`.
  Gate states in the JSON contracts: `q06_sec_comparable_revenue_source_contract.v0_2.json`
  `state = "GATE_S_REPAIRED_PENDING_PARENT_ACCEPTANCE"`, `next_action = "Parent reviews Gate S v0.2…"`
  (key path `.state`, `.next_action`); `q06_sec_comparable_revenue_capture_manifest.v0_1.json`
  `state = "FIRST_SOURCE_UNIT_COMPLETE"`, `.evidence_class.registered_value = null`,
  `.evidence_class.basis = "D07_OPEN_PR_7856_UNMERGED"`, `.held.cycle_pr_7868 = "REQUEST_CHANGES;
  no run or workaround"`.
- D5 readiness: allowlist is exactly three revenue lanes, "The allowlist intersects the real event
  population at exactly ONE issuer" — `research/prophet_v4/r6_program/wave0/C_EARNINGS_D5_READINESS_CENSUS_2026-09-23.md:121`
  (blocker 2), and "Consensus estimates are unlicensed, so beat/miss is permanently ABSENT" — `:122`
  (blocker 3).
- Issuer/event source census: "licensed consensus NOT FOUND" —
  `research/prophet_v4/r6_program/wave2/D03_ISSUER_EVENT_SOURCE_READINESS_CENSUS_2026-09-23.md:68`.

**PR-head only:** #7264 `214e0eda8c` private-Lab earnings presentation
(`engine/prophet_lab/earnings_view.py` — "Stateless presentation of the incumbent native D5
Earnings vector" docstring `:1-4`; copy keys `'entry':'New entry'` / `'entry_note':'Not asserted.
Earnings evidence cannot grant entry permission.'`). #9821 head not available on host. #8308 is
B17, not B08.

**Ruled:** `research/prophet_v4/r6_program/rulings/SEAT_RULING_R6-C-01_2026-09-23.md:7` — "One
real, source-backed dossier is deliverable today — AAPL FY2026 Q3 … as display/reference work
only." Sequencing at `:25` — "B14 (dossier surface) before B08 (production admission): the AAPL
reference dossier is the first bounded unit and is display-tier; B08's production gate waits on
blocker 1's external clock." `R6-D03-01_SOURCE_READINESS_SCOPE_2026-09-23.md:67` — consensus
estimates "PERMANENTLY ABSENT (`R6-C-01`); beat/miss forbidden".

**2. Program status.** `BUILD_PROGRAM.json` `units[]` `id="B08"` → `status:
"SPECIFIED_NOT_DISPATCHED"`, `depends_on: ["B00","B04"]`, `research_packets: ["Q01","Q06","Q14"]`,
`decision_ids: ["D03","D07"]`. `RESEARCH_DOCKET.json` `packets[]` `id="Q06"` → `status:
"SPECIFIED_NOT_REGISTERED_OR_DISPATCHED"`, `protected_outcomes_may_be_opened_by_this_packet:
false`, `build_consumers: ["B08","B14","B15"]`. `DECISION_REGISTER.json` `decisions[]` `id="D03"`
→ `status: "OPEN_TECHNICAL_DECISION_FABLE_AUTHORIZED_TO_RESOLVE"`, `blocked_consumers:
["B04","B08","B09","B16","B18"]`.

**3. Remaining closure named open.** Q06 v0.2: "Gate S parent acceptance is the next decision.
After that acceptance, the existing Earnings/D5 owner may implement the factual field. Gate E
remains separately owned by Evaluation and must be complete before outcome access." —
`wave3/Q06_SEC_COMPARABLE_REVENUE_SOURCE_METHOD_REPAIR_2026-09-29.md:158`. D5 consumer frontier:
"ordinary site UI wiring, deployment and signed-in browser/normal-refresh proof remain unfinished" —
`earnings_semantics_v1/D5_CONSUMER_2026-09-30.md:110-113`.

**4. DO_NOT_REBUILD / do_not_redo constraints.**
- `agentos/workstreams/WS-PROPHET-US-V4-RECOVERY.md:121-125` — "Do not read Earnings decision-time
  evidence through read_event_workspace / read_current_event_workspace… Decision-time access is
  read_event_source_revisions / read_all_event_source_revisions only."
- `:126-131` — "Do not admit an Earnings revision on source_available_at alone. Admission is the
  CONJUNCTION source_available_at <= cut AND observed_at <= cut…"
- `:139-142` — "Do not build a second cross-family ranker, second theme graph, second earnings
  store…"
- `research/DO_NOT_REBUILD.md:173` `HOLD-PSQ-TILT-CLOCK` — the EC hold-leash promotion clock is
  frozen; "Do **not** 'revive' by re-pointing the EC join at `data/earnings_calls/scores.parquet`"
  (a different sentiment construction).
- `research/DO_NOT_REBUILD.md:39` `KILL-POSITIONING-FUSION` (Amendment 2, 2026-10-02) — options
  positioning research interactions permitted research-only under
  `DEC:OPTIONS-HISTORICAL-REVIVAL-RESEARCH-ONLY`; production restrictions remain.

**5. Data/rights/custody blockers (quoted).**
- Consensus: `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md:189-193` — every
  dimension "not a source"; posture summary `:231` "Permanently absent".
- Nasdaq: `:129-131` — storage/model use/redistribution all "not a source" ("alter, store for
  subsequent use" prohibited; AI use prohibited).
- Yahoo expectations: `:142-143` — model use and redistribution "not a source".
- Transcripts: `:201-205` — all five dimensions UNKNOWN; "internal-only/context-only".
- Two earnings planes: C-census blocker 8, `C_EARNINGS_D5_READINESS_CENSUS…:127` — the #7294
  EquityDesk plane "shares no code path with `event_workspace.v1` or the D5 adapter".

---

## B14 — Deliver the Earnings research journey

**1. What exists at BASE.**
- Authenticated consumer: route `GET /api/prophet/lab/v1/episodes/{episode_id}/earnings` exists at
  BASE — `app/prophet_lab.py:326`, projecting through `engine/prophet_lab/earnings_dossier.py`
  (import at `app/prophet_lab.py:342`); module exists (`engine/prophet_lab/earnings_dossier.py`).
  "The detail preserves the original decision cut and source projection ID… It never substitutes
  consensus, forecasts, current entry permission or new scores." — `earnings_semantics_v1/D5_CONSUMER_2026-09-30.md:26-30`.
- Explanation layer: "the already-authenticated `/api/prophet/lab/v1/episodes/{episode_id}/earnings`
  response now includes the explanation" — `earnings_semantics_v1/EVIDENCE_BRIEF_AND_PROFITABILITY_2026-09-30.md:16-18`.
- Continuation handoff at BASE: `agentos/handoffs/PROPHET-US-V4-RECOVERY-2026-09-30-earnings-d5-consumer.md`
  (`ended_because: blocked`, `prs: [8189]`).
- User-action owners: durable-actions census — Pass + reason "**NONE.** No route in `app/` accepts
  a user disposition" — `wave0/D05_USER_ACTION_OWNER_CENSUS_2026-09-23.md:26`; thesis/milestone
  note has "no in-repo writer → the write path is UNKNOWN" (`:27`).

**PR-head only:** #7264 `214e0eda8c` — `engine/prophet_lab/earnings_view.py` (EN/ZH copy, all
authority false: `'authority':'All source and view authorities remain false…'`), plus the two
handoffs: `agentos/handoffs/PROPHET-US-V4-RECOVERY-2026-09-17-native-earnings-view.md` (37 native
tests; unverified: "A user can open the evidence in the entitled production frontend") and
`…2026-09-18-earnings-browser.md` (browser consumer; 624 tests passed; unverified: "The new
interaction and both visual themes work in actual Chromium").

**Ruled:** `SEAT_RULING_R6-C-01_2026-09-23.md:25` — "B14 (dossier surface) before B08 (production
admission)". `SEAT_RULING_R6-D05-01_2026-09-23.md:15-16` — Q3 alerts and Q4 thesis: "`public.trade_episodes`
extension with a new `source` enum value is the least-new-surface route"; "Production DDL =
operator-ratified step (EXACT_HUMAN_GATE); until ratified, thesis capture stays DISABLED, not
local-only."

**2. Program status.** `BUILD_PROGRAM.json` `id="B14"` → `status: "SPECIFIED_NOT_DISPATCHED"`,
`depends_on: ["B03","B04","B08","B20"]`, `decision_ids: ["D02","D09"]`. Q06 docket (shared) as in
B08; Q24 not extracted (out of packet list).

**3. Remaining closure named open.** `D5_CONSUMER_2026-09-30.md:125-131` — "Next critical actions:
consume exact-head CI; close the canonical Q06 source release dependency; wire the existing
front-end earnings detail…; prove one ordinary paid read/refresh. Then qualify comparable
expectations/revisions…". #7264 handoff `unresolved`: "Existing Macro Pick Lab is not Operator Lab.
Current Terminal plan types do not expose a B1 episode binding; do not invent a ticker-to-episode
join." D05 ruling open items D05-b/D05-c (`SEAT_RULING_R6-D05-01…:24-25`).

**4. Constraints.** do_not_redo `WS-PROPHET-US-V4-RECOVERY.md:117-120` (unbuilt adapter emits no
family envelope; D5 requires B1 canonical episode identity — never alias the Radar live episode);
`DO_NOT_REBUILD.md:63` `KILL-PARALLEL-KNOWLEDGE-BASE` matched the keyword grep only via the phrase
"survives as guidance" (word-sense false positive; no earnings-journey constraint).

**5. Blockers.** B1 natural nightly clock: C-census blocker 1 `:120` — "No real B1 episode
generation is reachable… A11 is MERGED / BUILT_NOT_PROVEN, clearing only on natural-production
acceptance… never by dispatch". Q06 #8069 release: `D5_CONSUMER…:54-57` — "#8069's source-method
acceptance is separate from release. Its outstanding suite-registration/CI and actual source
release remain deployment prerequisites."

---

## B15 — Qualify Earnings models, entry and holding

**1. What exists at BASE.**
- Design amendment: `earnings_semantics_v1/information_time_research/EARNINGS_TIMING_AND_B15_DESIGN_2026-10-01.md`
  — three cohorts (A guidance-update, B reported-number, C later-language, `:82-97`), model
  proposal "The first candidate is a parsimonious regularized model of benchmark-relative return at
  the existing declared sleeve horizon" (`:115-116`), and "This document is not the missing
  experiment registration and allocates no new trial budget." (`:128-129`).
- Empirical scaffolding (public baselines, descriptive only):
  `earnings_semantics_v1/public_profitability_baseline/README.md:3` — "COMPLETED EXPLORATORY
  BASELINE, NOT A PROPHET MODEL PROMOTION"; `public_value_quality/README.md:3` — "Completed
  exploratory public diagnostic; no native ranking or policy promotion."
- Sleeve catalog entry (see Q8 below for quotes).
- Engine at BASE: `engine/sue.py` functions listed under B08; no B15 model/trial code exists.

**PR-head only:** none (B15-specific); #7264's view asserts entry/hold NOT asserted (copy quoted
under Q8).

**Ruled:** no unit-specific ruling found; D04 gates it: `DECISION_REGISTER.json` `id="D04"` →
`blocked_consumers: ["B05","B12","B13","B15","B19"]`, forbidden shortcut "horizon-as-hold
inference". D08 similarly lists B15 (`blocked_consumers` includes `"B15"`).

**2. Program status.** `BUILD_PROGRAM.json` `id="B15"` → `status: "SPECIFIED_NOT_DISPATCHED"`,
`depends_on: ["B05","B06","B14"]`, `research_packets: ["Q06","Q09","Q11","Q13","Q15","Q16","Q20"]`.
Docket: Q11/Q16/Q20 all `status: "SPECIFIED_NOT_REGISTERED_OR_DISPATCHED"`,
`protected_outcomes_may_be_opened_by_this_packet: false`.

**3. Remaining closure named open.** `EARNINGS_TIMING_AND_B15_DESIGN…:174-176` — "the next
empirical unit is the admitted same-population incremental comparison, not another unregistered
strategy run." Q06 Gate E: "Gate E remains NOT_REGISTERED / UNCOMPUTED" —
`wave3/Q06_SEC_COMPARABLE_REVENUE_SOURCE_METHOD_REPAIR_2026-09-29.md:6`; the Evaluation-owner
freeze list at `:99-112`.

**4. Constraints.** `DO_NOT_REBUILD.md:46` `KILL-OFFHORIZON-VERDICTS` — "Signal-engine verdicts at
non-pre-declared horizons | FORBIDDEN". Catalog: "The Earnings H42/H21/H63 and Cycle H252/H126/H504
values are retained only as research proposals. They do not create a hold law." —
`research/prophet_v4/PROPHET_STRATEGY_CATALOG_V1_2026-09-30.md:49`.

**5. Blockers.** Licensed expectations absent (rights register `:185-193`); Massive price basis
"`H42 absolute or relative return: BLOCKED`" — `wave3/Q06_SEC_COMPARABLE_REVENUE_PROSPECTIVE_CAPTURE_2026-09-26.md:316-324`
(unadjusted consolidated aggregates; corporate-action factor owner missing).

---

## B16 — Qualify a Cycle source-readiness pilot

**1. What exists at BASE.**
- The full wave2 D03 Cycle evidence chain: `D03_CYCLE_SOURCE_READINESS_CENSUS_2026-09-23.md`
  (five-rule readiness rule `:129-135`; verdict per candidate `:139-160` "NOT PILOT-READY"),
  `D03_SOURCE_READINESS_MATRIX_2026-09-23.md` (measured 17-series vintage table `:34-52`;
  candidate × rule verdicts `:160-164` — rules 2/3/5 FAIL for all three candidates),
  `CYCLE_A_ERA_TREATMENT_RECORD_2026-09-23.md` (era map `:84-93`; "no usable macro-only era can be
  ratified until AWHMAN's definition-treatment record is closed" `:94`), receipt
  `wave2/alfred_depth_b16a.json`, and `CYCLE_A_MACRO_DIAGNOSTIC_PREREG_2026-09-23.md`
  (frozen hypotheses H1–H3, primary endpoint, window 2002-12→2025-05-15 `:54`).
- Adjacent: `US_PROPHET_PHASE22_FAST_CYCLE_REGIME_PROSPECTIVE_PREREG_2026-09-19.md` (a different,
  Radar C2/C4 prospective prereg; "FROZEN_WAITING_FOR_PROSPECTIVE_SOURCE" `:237-238`).

**PR-head only:** none for B16.

**Ruled (deciding sentences quoted).**
- `rulings/R6-B16-01_ADMISSION_2026-09-23.md:21` — "**Ruling: no Cycle proving domain is admitted.
  B16 closes NOT PILOT-READY.** … **B18 stays BLOCKED**: failure-inclusive Cycle policy research
  requires an issuer universe with failure coverage, which no source provides at any cut."
- `rulings/R6-B16-01a_ERA_RATIFICATION_2026-09-23.md:9` — "The seat therefore substitutes
  **`INDPRO` (industrial production: an output mechanism)** for `AWHMAN`…"; `:18` — era
  **2002-12 → 2025-05-15** "RATIFIED macro-only diagnostic window"; `:25` — "**Admits, once the
  rights register (#7843) is merged:** a **macro-only, internal-only, retrospective diagnostic**…
  It is not a pilot, not public, not a B16 selection, and does not unblock B18."
- `rulings/R6-D03-01_SOURCE_READINESS_SCOPE_2026-09-23.md:22` — "readiness is decided on source
  clocks, vintage depth, definition continuity, mapping/coverage and rights — never on returns";
  `:47-48` — "B16-b (gated on B16-a): if and only if a domain passes all five rules… Otherwise B16
  closes as 'NOT PILOT-READY — prospective collection started'… B18 … is BLOCKED".

**2. Program status.** `BUILD_PROGRAM.json` `id="B16"` → `status: "SPECIFIED_NOT_DISPATCHED"`
(the effective-handoff snapshot predates the rulings); the ruling record supersedes operationally:
"B16: CLOSED / NOT PILOT-READY. B18: BLOCKED." — `R6-B16-01…:33`. Docket `id="Q07"` → `status:
"SPECIFIED_NOT_REGISTERED_OR_DISPATCHED"`, `protected_outcomes_may_be_opened_by_this_packet: false`.

**3. Remaining closure named open.** `R6-B16-01…:25-28` — rule 5 rights rows for FRED legs and
Census M3; the rule-4 era record (done, PR #7845); the macro-only diagnostic; the Chairman provider
question "is not yet askable: its precondition… waits on items 1 and 2".

**4. Constraints.** `DO_NOT_REBUILD.md:43` `KILL-ROTATION-CYCLE-CONFLUENCE` (DON'T-TEST); `:62`
`KILL-REGIME-SCORECARD`; `:85` `KILL-WASHOUT-TURN`; `:128`
`KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR`. Era law: "Broad series may never be relabeled as
granular subthemes." — `R6-D03-01…:19` (rule 4).

**5. Blockers.** Rules 2–3 mapping/failure: "first genuine membership cut is 2026-08-13" and
"satisfiable cuts = 0" — `D03_SOURCE_READINESS_MATRIX…:162`. Rule 5: FRED model use "not a source"
(register `:100`); Census M3 storage/model/redistribution UNKNOWN (`:109-111`).

---

## B17 — Deliver funding and per-share Cycle dossiers

**1. What exists at BASE: nothing unit-specific.** `git ls-files research/prophet_v4` shows no
`cycle_equity_v1/` at BASE; no `engine/prophet_cycle_equity.py` at BASE. Pre-existing owners the PR
reuses: `engine/cash_runway.py`, `engine/capital_need.py`,
`engine/capital_structure/share_count_truth.py` (named in the PR README's "Existing source
capability" section).

**PR-head only: #8308 `446ffd0f10` (held for Sol per commissioning packet).**
- `research/prophet_v4/cycle_equity_v1/README.md:3` — "BUILT_NOT_PROVEN / MISSION_COMPLETE:false.
  B17/Q08 source implementation; no live rank, sizing, policy, trade, or portfolio authority."
- `engine/prophet_cycle_equity.py` docstring `:3-14`: "Pure, network-free consumer over existing
  source-qualified finance facts… It deliberately does NOT collect filings, infer financing
  availability, estimate probabilities, rank candidates, size positions, create trades, or splice a
  replacement security into the historical return of a cancelled security." Public names:
  `build_funding_path` (`:301`), `recovery_scenario` (`:478`), `inventory_sales_diagnostic`
  (`:639`), `build_cycle_equity_case` (`:679`), `cycle_equity_brief` (`:743`); `_AUTHORITY` all
  false (`:27-34`); schemas `prophet.cycle_equity_case/v1`, `prophet.cycle_funding_path/v1`,
  `prophet.cycle_equity_recovery/v1`, `prophet.cycle_inventory_sales_diagnostic/v1` (`:17-20`).
- Handoff `agentos/handoffs/PROPHET-US-V4-RECOVERY-2026-10-03-cycle-equity-b17.md` —
  `ended_because: ci_handoff`, `prs: [8308]`, "FINALIZATION_CLASSIFICATION:
  CHECKPOINTED_CONTINUATION / MISSION_COMPLETE: false".

**Ruled:** no B17-specific ruling found; B16/B18 rulings gate the sleeve (B17 depends_on B16 in
the build program).

**2. Program status.** `BUILD_PROGRAM.json` `id="B17"` → `status: "SPECIFIED_NOT_DISPATCHED"`,
`depends_on: ["B03","B04","B16","B20"]`, `research_packets: ["Q07","Q08","Q24"]`. Docket
`id="Q08"` → `status: "SPECIFIED_NOT_REGISTERED_OR_DISPATCHED"`,
`protected_outcomes_may_be_opened_by_this_packet: false`, `build_consumers: ["B17","B18","B19"]`.

**3. Remaining closure named open (handoff `unverified`).** "Real source-qualified financing
events and restricted-cash coverage." / "User-facing production Cycle dossier." / "Improved Cycle
selection or customer returns." — each with a `what_would_verify` field; plus `unresolved`:
"Current Capital Structure projection explicitly withholds active instruments, remaining capacity,
fully diluted shares and financing probability; do not infer them from filing presence."

**4. Constraints.** Handoff `do_not_redo`: "Do not splice replacement-security performance onto
canceled old shares." / "Do not convert scenario arithmetic into a probability, rank, size,
automatic average-down rule or buy permission." / "Do not replace capital_need, cash_runway,
debt_maturity, share-count truth or Capital Structure with a second owner."

**5. Blockers.** "Repository search at this source base found no native exact `gross_proceeds +
issue_price + shares_issued` financing consumer and no restricted-cash join for B17." (PR README,
"Existing source capability and the exact gap"); rights: no debt/funding source family exists in
the rights register (see Q7).

---

## B18 — Run failure-inclusive Cycle policy research

**1. What exists at BASE:** the rulings and their evidence only (wave2 chain under B16). No B18
artifact, engine, or study exists at BASE; `research/prophet_v4` inventory shows none.

**Ruled:** `R6-B16-01…:21` — "**B18 stays BLOCKED**: failure-inclusive Cycle policy research
requires an issuer universe with failure coverage, which no source provides at any cut."
`R6-D03-01…:48` — "B18 (failure-inclusive Cycle policy research) is BLOCKED until B16-b admits a
domain. No Cycle strategy return may be computed or cited under this program before that
admission." Q06 manifest `.held.cycle_pr_7868 = "REQUEST_CHANGES; no run or workaround"`.

**2. Program status.** `BUILD_PROGRAM.json` `id="B18"` → `status: "SPECIFIED_NOT_DISPATCHED"`,
`depends_on: ["B06","B16"]`, `research_packets: ["Q07","Q08","Q09","Q11","Q12","Q17","Q20"]`.
Docket Q17 → `status: "SPECIFIED_NOT_REGISTERED_OR_DISPATCHED"`,
`protected_outcomes_may_be_opened_by_this_packet: false`.

**3. Remaining closure named open.** `R6-B16-01a…:26` — the macro-only diagnostic "does not
unblock B18"; `D03_SOURCE_READINESS_MATRIX…:371` — "A licensed historical mapping/failure source
remains the exact human/provider question".

**4. Constraints.** Q08 falsifier — "Recovery value vanishes for original shares, or outcomes
improve only after failed firms and canceled securities are excluded." (docket `id="Q08"`
`.falsifier`); Q17 falsifier — "Policy mainly extends permanent impairment, averages down
mechanically or benefits from survivor-only recovery histories."

**5. Blockers.** Rules 2–3 failure coverage at every cut (matrix `:162-164`); delisted registry has
six names only — "Six curated exits do not constitute general failure coverage." (`:75`).

---

## B19 — Qualify Cycle core/add/exit behavior

**1. What exists at BASE.**
- Entry/ladder/core-tactical/leverage/exit law: `PROPHET_STRATEGY_PLATFORM_AND_CYCLE_CAPTURE_ARCHITECTURE_FREEZE_2026-08-30.md`
  §6.6–§6.10 — "Only B4 may publish current entry/add geometry." (`:420`); ladder
  research-watch→core-hold (`:424-434`); "CORE_HOLD may remain valid while a new add is
  RAN_DONT_CHASE" (`:451-456`); leverage boundary "Prophet has zero sizing or leverage authority
  at sleeve birth" (`:458-470`); exit law (`:474-488`).
- `PROPHET_STRATEGY_PLATFORM_OWNER_BOUNDARY_AND_CROSS_MARKET_IDENTITY_AMENDMENT_2026-08-30.md:60-74`
  — "`CORE_HOLD` is projection semantics only… creates no append-only lifecycle or position ledger
  of its own; cannot originate size, leverage, trim, hedge or exit orders."
- Strategy catalog Cycle sleeve requirements — `PROPHET_STRATEGY_CATALOG_V1_2026-09-30.md:78`
  ("Requires evidence of liquidation, base/pivot repair, genuine cycle economics,
  survivability/funding/dilution, price incorporation and residual opportunity."); engine catalog
  row `CYCLE_CAPTURE_WASHOUT_ACCUMULATION` with constraint "equity/future/ETF/producer contracts
  remain distinct" — `engine/prophet_strategy_definition.py:382`.

**PR-head only:** #8308 supplies the B17 funding/per-share mechanics B19 would consume (dated
events; no core/add state machine — see Q10).

**Ruled:** D04/D05/D08 list B19 as blocked consumer (`DECISION_REGISTER.json` `id="D04"` /
`"D05"` / `"D08"` `blocked_consumers` each include `"B19"`).

**2. Program status.** `BUILD_PROGRAM.json` `id="B19"` → `status: "SPECIFIED_NOT_DISPATCHED"`,
`depends_on: ["B05","B17","B18"]`, `research_packets: ["Q08","Q15","Q17"]`; release limit "No
leverage, automatic add/trim or transfer of holdings outside accepted Portfolio/Risk authority."

**3. Remaining closure named open.** B19 inputs require "accepted D04 Cycle entry/hold versions
and real source milestones" (`.inputs`); none exist — D04 is
`OPEN_TECHNICAL_DECISION_FABLE_AUTHORIZED_TO_RESOLVE`.

**4. Constraints.** CW0 charter `:167` — "B4 alone owns current entry/add geometry; `CORE_HOLD`
can coexist with `WAIT_PULLBACK` or `RAN_DONT_CHASE` for a new add; tactical add/trim state cannot
silently liquidate the core…"; `DO_NOT_REBUILD.md:40` `KILL-LLM-ORIGINATION`.

**5. Blockers.** Upstream B16 (not pilot-ready) and B18 (blocked) per the rulings; Portfolio/Risk
retains sizing authority (Q12).

---

## B24 — Expose coherent portfolio context across sleeves

**1. What exists at BASE.**
- Owner module for read-only holdings context: `app/main.py:2028` `_portfolio_load_holdings(uid)`,
  `:2097` `@app.get("/api/portfolio/brief")`, `:2191` `@app.post("/api/portfolio/changes")` — the
  changes route "computes a diff, writes nothing" per the census
  (`wave0/D05_USER_ACTION_OWNER_CENSUS_2026-09-23.md:28`). Watchlist vs portfolio are separate
  stores with a tested never-cross law (`:34-56`).
- Strategy-side law: catalog `cross_sleeve_law.portfolio_allocation_owner = "Portfolio/Risk"` —
  `engine/prophet_strategy_definition.py:695`; owner matrix "What does the user actually hold, at
  what basis and exposure? | Portfolio/Risk | no ownership by Prophet" and "What size,
  concentration, financing or leverage is permitted? | Portfolio/Risk | no authority" —
  `PROPHET_STRATEGY_PLATFORM_OWNER_BOUNDARY…:90-91`.

**PR-head only:** none for B24.

**Ruled:** `SEAT_RULING_R6-D05-01_2026-09-23.md:16` — trade_episodes extension is "ACCEPT as
candidate owner"; DDL is an "EXACT_HUMAN_GATE"; open items D05-b (alert producer-or-disable) and
D05-c (Pass/thesis/milestone owner mapping "blocked on the DDL gate above") at `:24-25`.

**2. Program status.** `BUILD_PROGRAM.json` `id="B24"` → `status: "SPECIFIED_NOT_DISPATCHED"`,
`depends_on: ["B07","B13","B14","B17"]`, `research_packets: ["Q21"]`; outputs "Read-only combined
context…; exposure counted once"; release limit "No implicit order, allocation, hedge or parallel
position ledger." Docket `id="Q21"` → `status: "SPECIFIED_NOT_REGISTERED_OR_DISPATCHED"`,
population "…no user position mutation".

**3. Remaining closure named open.** D05-c owner mapping (above); B24 depends on B07/B13/B14/B17
none of which are dispatched.

**4. Constraints.** do_not_redo `:139-142` (no second position ledger via the "second forward
grader/publication truth" family of bans); D05 forbidden shortcut "turning a watch into a position"
(`DECISION_REGISTER.json` `id="D05"` `.forbidden_shortcut`).

**5. Blockers.** DDL operator gate for the thesis owner (`SEAT_RULING_R6-D05-01…:16`); no
Prophet-held sizing authority anywhere (Q12 quotes).

---

## B27 — Disposition retained sleeves and instrument roadmap

**1. What exists at BASE.**
- Catalog entries (all five): `engine/prophet_strategy_definition.py` — `POLICY_EVENT_SWING`
  (`:513-544`), `CATALYST_DISLOCATION` (`:545-576`), `LIQUIDITY_DEBASEMENT_REAL_ASSETS`
  (`:577-608`), `RANGE_MEAN_REVERSION` (`:609-640`), `DEFENSIVE_AVOIDANCE_HEDGE_RESEARCH`
  (`:641-676`); each `definition_status: "SPEC_ONLY_RETAINED_B27"`, `horizon_status:
  "OWNER_SPEC_REQUIRED"`. Catalog md: "The later five are retained B27 research obligations; catalog
  inclusion does **not** make them live." — `PROPHET_STRATEGY_CATALOG_V1_2026-09-30.md:22`; "The
  five later sleeves have no numeric horizon copied from Early Leadership." (`:51`).
- Research docs: no sleeve-dedicated research doc exists at BASE (inventory grep under Q11 below);
  the architecture freeze carries the family list and shared law — "Early Rotation, Quality
  Earnings, Policy/Event, Dislocation, Liquidity/Real Assets, Range Reversion and Defensive
  Research follow the same architecture rather than creating new platforms." —
  `…ARCHITECTURE_FREEZE…:727-729`.
- Engine modules: none per sleeve beyond the catalog spec. Existing estate modules the sleeves'
  evidence families would touch (registry rows): options flow `engine/options_flow.py` ("licensed,
  verify redistribution before UI") and gamma exposure `engine/gex_engine.py` ("licensed-derived")
  — `research/prophet_v4/SOURCE_RIGHTS_AND_COVERAGE_REGISTRY.md:36-37`.
- DO_NOT_REBUILD kill/hold rows per sleeve (row id + path `research/DO_NOT_REBUILD.md`):
  - Policy/Event Swing: `:53` `KILL-POLICY-TIMING-PREDICTOR` ("intent unfalsifiable;
    conditions-framing only"); `:91` `KILL-ELECTION-CYCLE`; `:124` `KILL-FORCED-CALLS`
    ("operator conviction may seed a display-tier watch item or a prereg, never pin an
    un-gauntleted call to a signal surface").
  - Catalyst/Dislocation: `:125` `KILL-PHASE3-START-WEIGHT` (scored catalyst leg killed; display
    chip lawful); `:130` `KILL-LIQUIDITY-SHOCK-REVERSAL-CLASSIFIER` (construction-scoped; tape-grade
    features "blocked on entitlement, not effort"); `:115` `KILL-MCO-THRUST`; `:121`
    `KILL-ONSET-FINGERPRINTS` (catalyst-rung counts).
  - Liquidity/Debasement/Real Assets: `:123` `KILL-COMMODITY-XSEC-MOM` ("long-only EW commodity
    exposure is the surviving baseline"); `:42` `KILL-BTC-MIDTERM-BLACKOUT-AUTHORITY` (RETIRED as
    authority; "election-cycle history is context-only").
  - Range/Mean Reversion: `:130` `KILL-LIQUIDITY-SHOCK-REVERSAL-CLASSIFIER` (mean-reversion
    candidates named in its scope); `:76` `KILL-OUTCOME-AUDITION` (per-name timing selection).
  - Defensive/Avoidance/Hedge: `:45` `KILL-DIRECTIONAL-SHORTING`; `:72`
    `KILL-DEFENSIVE-FLOOR-BUNDLE`; `:62` `KILL-REGIME-SCORECARD` and `:128`
    `KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR` (regime fusion bans); options family rows `:86`
    `KILL-CHARM-NARRATIVES`, `:87` `KILL-DOI-FAMILY`, `:88` `KILL-SKEW-DECELERATION`, `:160`
    `HOLD-THETA-TAPE`, `:164` `HOLD-WF-OPTIONS` — each now carrying "Research exception:
    DEC:OPTIONS-HISTORICAL-REVIVAL-RESEARCH-ONLY; production restrictions retained" (Chairman
    2026-10-02).

**PR-head only:** none for B27.

**Ruled:** no sleeve-specific ruling; `DECISION_REGISTER.json` `id="D12"` → `blocked_consumers:
["B25","B27","B28"]`, status `OPEN_TECHNICAL_DECISION_FABLE_AUTHORIZED_TO_RESOLVE`.

**2. Program status.** `BUILD_PROGRAM.json` `id="B27"` → `status: "SPECIFIED_NOT_DISPATCHED"`,
`research_packets: ["Q23"]`, `decision_ids: ["D12"]`; discriminating cases "Renamed killed species;
copied EL horizon; stock result treated as option alpha; assumed borrow; automatic leverage."
Docket `id="Q23"` → `status: "SPECIFIED_NOT_REGISTERED_OR_DISPATCHED"`, `build_consumers:
["B27","B28"]`.

**3. Remaining closure named open.** Catalog next step — "disposition the five retained B27
sleeves with source/readiness research" — `PROPHET_STRATEGY_CATALOG_V1_2026-09-30.md:143`; Q23
method — "rank its readiness; reject unsupported variants explicitly rather than copying EL
coefficients".

**4. Constraints.** As listed per sleeve above plus catalog-level: "Defensive/Hedge research
explicitly retains `DNR:KILL-DIRECTIONAL-SHORTING`. No short or option authority is created."
(`PROPHET_STRATEGY_CATALOG_V1…:72`).

**5. Blockers.** Instrument-native owners absent — each later sleeve's `entry_owner` is "future
accepted … policy + B4" (`engine/prophet_strategy_definition.py:533,565,597,629`); rights for
borrow/options payoff semantics unproven (`:674`).

---

## Cross-cutting answers

### 6. Earnings semantics: specified vs implemented

- **Comparable period/metric — specified:** same-table current vs same-quarter-prior-year GAAP
  revenue (`wave3/Q06_…CAPTURE_2026-09-26.md:20-24,57-69`); refusing reversed/identical/overlapping
  intervals (`earnings_semantics_v1/PERIOD_COMPARABILITY_AND_VALUATION_2026-09-30.md:13-24`).
  **Implemented:** `engine/sue.py:339 reported_change`; the D5 adapter projects current revenue
  only — prior revenue is the typed absence `no_span_addressable_evidence`
  (`wave3/Q06_…CAPTURE…:71-74`), so the comparable field is "a source-supported construction, not a
  currently materialized production field".
- **Revisions — specified:** decision-time admission conjunction and clock-ordered selection
  (`wave0/C_EARNINGS_D5_READINESS_CENSUS…:45`, quoting CELL_F A7 clauses 3–5); Q06 correction
  classes `SOURCE_BYTES_CHANGED/ECONOMIC_FIELDS_UNCHANGED`, `ECONOMIC_FIELDS_CHANGED`,
  `CLOCK_ONLY_CHANGE`, `UNESTIMABLE` (`wave3/Q06_…CAPTURE…:114-129`). **Implemented:** the chain
  readers `read_all_event_source_revisions`
  (`engine/neuralweb/company_intelligence_reader.py:1200-1230`, one bounded walk, oldest-first) and
  `read_event_source_revisions` (`:1309-1332`, thin wrapper); `DEFAULT_MAX_CHAIN_HOPS = 500`
  (`:917`); typed failures `WorkspaceChainNotPublished` (`:890`) and `WorkspaceChainIntegrityError`
  (`:898`). Current-generation (non-PIT) readers exist alongside: `read_event_workspace` (`:586`),
  `read_current_event_workspace` (`:753`), `load_current_workspace` (`:1011`),
  `load_workspace_with_disposition` (`:1027`).
- **Source spans — specified and bound:** exact UTF-8 byte spans and text hashes for both values
  (`wave3/Q06_…CAPTURE…:62-63`); field-provenance identity binding spans + statement title +
  period role (`wave3/Q06_…REPAIR_2026-09-29.md:60-79`).
- **Revenue/profit/margin/cash interpretation:** profitability bridge symmetric identity
  `change(P) = change(R)*average(m) + change(m)*average(R)` — "an arithmetic decomposition, NOT a
  causal estimate" (`EVIDENCE_BRIEF_AND_PROFITABILITY…:58-67`); cash reconciliation
  `operating cash = net income + disjoint signed reported adjustments` with COMPLETE/PARTIAL/
  UNRECONCILED states (`CASH_RECONCILIATION_AND_TIMING_2026-10-01.md:27-40`); valuation scenario
  price identity and scenario-only assumptions (`PERIOD_COMPARABILITY…:40-57`). Implemented in
  `engine/sue.py:1439/:1670/:1521`.
- **Corrections:** `correction_lineage_state` closed over `OBSERVED|NONE_IN_CHAIN|NOT_OBSERVABLE`
  (`wave0/C_EARNINGS_D5_READINESS_CENSUS…:35`); 8-K/A supersede links in the release-binding plane
  (`wave2/D03_ISSUER_EVENT_SOURCE_READINESS_CENSUS…:39`); the M1 repair reclassifying ten distinct
  envelope hashes as `UNEXPLAINED_SUPPLIED_ENVELOPE_IDENTITY` with the
  `sec_suffix_delivery_script_v1` normalization rule (`wave3/Q06_…REPAIR…:10-52`).

### 7. Rights per source family (quoted from `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md`)

- **Filings (SEC EDGAR)** `:117-121`: acquisition "considered public information"; processing/
  storage "may be copied or further distributed"; model use user-facing; redistribution
  "user-facing, citation-and-trademark-limited".
- **Issuer guidance**: no standalone family; guidance arrives via SEC release bodies (EDGAR row)
  or transcripts — the transcript profile `rp_public_primary_v1` grants nothing (`:197-205`, all
  UNKNOWN, "internal-only/context-only"); the AAPL guidance field is "excluded from the
  confirmatory feature set until a source-specific rights record admits persistence/model use"
  (`wave3/Q06_…CAPTURE…:84-86`).
- **Transcripts**: as above — `:201-205`.
- **Licensed consensus/estimates**: consensus `:189-193` — "not a source" on every dimension,
  "beat/miss is 'permanently ABSENT'"; Yahoo/yfinance expectations `:139-143` — acquisition
  recorded, processing/storage UNKNOWN/internal-only, model use and redistribution "not a source".
  **Is any licensed consensus source present at BASE? No** — posture summary `:231` "Permanently
  absent | A future explicit reversal of R6-C-01 plus a full licensed entitlement."
- **Prices**: Massive `massive_stock_day` `:16-20` — all five dimensions RECORDED, posture
  "user-facing" / "user-facing, feed-conditional"; Basket/SPY closes `:149-153` —
  `vendor_terms_personal_use` adverse label, model use/redistribution "not a source".
- **FRED** `:97-101`: acquisition internal-only ("View, download, and print FRED content");
  processing UNKNOWN; storage prohibited-terms UNKNOWN; **model use UNKNOWN — "not a source"**
  (legal page: "development or training of any software program", "machine learning");
  redistribution UNKNOWN/internal-only. Per-series tags: e.g. `NEWORDER`/`ISRATIO`/`AWHMAN`/
  `AMTMUO`/`AMTMVS`/`INDPRO` "public domain: citation requested" (`:55,60,64,79,80,41`);
  `CMRMTSPL` "copyrighted: citation required" (`:62`).
- **Census M3** `:107-111`: acquisition/processing internal-only ("You may use the Census Bureau
  API to develop a service"; "search, display, analyze, retrieve, view"); storage, model use,
  redistribution UNKNOWN — internal-only.
- **Debt/funding sources**: **not found** — the register's family list (`:8`) has no debt, funding,
  or corporate-actions family; searches run: full read of the register (255 lines) and the
  wave2/`licenses` filename inventory (no matching filename).

### 8. Earnings entry/hold definitions and Early-Leadership reuse

- Earnings sleeve entry/hold in the catalog: `entry_owner = "B4 after source-qualified event and
  strategy-specific policy acceptance"`, `hold_law = "event/revision-native review; next material
  revision/report matters, but horizon is not yet frozen"` — `engine/prophet_strategy_definition.py:490-491`;
  horizons `primary_horizon="H42"`, `supporting_horizons=["H21","H63"]` with
  `horizon_status="RESEARCH_PROPOSAL_NOT_POLICY"` (`:459-462`).
- Reuse of Early Leadership entry/hold semantics: **explicitly refused, not present** — "Only one
  strategy has a frozen control definition… `EARLY_LEADERSHIP_SECTOR_ROTATION`… The five later
  sleeves have no numeric horizon copied from Early Leadership." —
  `PROPHET_STRATEGY_CATALOG_V1_2026-09-30.md:45-52`; engine tests pin "later sleeves do not inherit
  `2_15_SESSIONS`" (`:124-126`). The #7264 earnings view keeps both entry and hold explicitly
  unasserted: `'entry_note':'Not asserted. Earnings evidence cannot grant entry permission.'`,
  `'hold_note':'Not supplied. An earnings observation does not establish a hold instruction.'`
  (`engine/prophet_lab/earnings_view.py` COPY block, PR head `214e0eda8c`).

### 9. Cycle: R6-B16-01/01a verdicts, open paths, diagnostic status, FRED/M3 rows

- Verdicts quoted under B16. Open paths they name: rule-5 rights rows (FRED legs, Census M3), the
  rule-4 era record, the macro-only internal-only retrospective diagnostic (admitted once the
  rights register merged), and the Chairman provider question once rules 1/4/5 are otherwise
  satisfiable (`R6-B16-01…:25-28`; `R6-B16-01a…:25-26`).
- **Macro-only diagnostic after 2026-09-23:** the prereg exists and its RUN CONTRACT names the
  result path `research/prophet_v4/r6_program/wave2/CYCLE_A_MACRO_DIAGNOSTIC_RESULT_2026-09-23.md`
  (`CYCLE_A_MACRO_DIAGNOSTIC_PREREG…:95`). **No RESULT artifact exists at BASE**: `git ls-files
  research | grep -i CYCLE_A_MACRO_DIAGNOSTIC` returns only the prereg; repo grep for
  `CYCLE_A_MACRO_DIAGNOSTIC_RESULT` matches only the prereg's own line 95; `git log --all
  --diff-filter=A -- '*CYCLE_A_MACRO_DIAGNOSTIC_RESULT*'` is empty. The Q06 manifest records the
  diagnostic's carriers as held: `.held.cycle_pr_7868 = "REQUEST_CHANGES; no run or workaround"`,
  `.held.cycle_pr_7871 = "unaccepted producer; no data consumed"`. (Per packet rules, had a RESULT
  existed only its path/date would be reported.)
- FRED and M3 rights rows now covering them: register FRED/ALFRED section `:95-101` (model use
  "not a source") and Census M3 `:105-111` (storage/model/redistribution UNKNOWN) — i.e. the rule-5
  gap the ruling named is recorded, not resolved.

### 10. #8308 B17 dossier fields and separations

- Fields present: **funding** (dated funding-path events with kinds at
  `engine/prophet_cycle_equity.py:36-44`, `build_funding_path:301`); **debt** (draw/repayment/
  conversion events; disclosed debt ladder completeness required — README "Implemented mechanisms"
  §1 conditions 1–5); **restrictions** (restricted-cash states `observed|not_applicable|unknown`,
  `:46`; "Unknown restricted cash is not silently zero"); **maturities** (via `capital_need.v1`
  "cash + maturity composition" reuse and the "maturity-before-recovery" test in the handoff's
  `changed` note for `tests/test_prophet_cycle_equity.py`); **dilution** (equity raise carries
  proceeds AND new shares; ending share count; per-share transmission — README §1–2); **per-share
  economics** (ending value per common share, original-cohort terminal value, scenario return on
  contributed capital, EV required to recover the original purchase — README §2 and the
  discriminating example: "scenario return on original contributed capital = −16.67%").
  **Milestones: not found** — no milestone field appears in the README, the engine's public names,
  or the handoff; B19's "real source milestones" input remains unimplemented.
- **Company survival vs original-equity recovery: separated** — README §2 "Business recovery
  versus original-share recovery" plus "This is the central B17 distinction: a recovering business
  is not automatically a recovered stock."; engine `recovery_scenario` (`:478`) vs
  `build_funding_path` (`:301`).
- **Core-hold vs tactical-add: not in this PR** — `git show 446ffd0f10:…README.md | grep -n -i
  'core\|tactical\|milestone'` returns no core/tactical hits; that separation is owned by the
  architecture freeze §6.8 (`…ARCHITECTURE_FREEZE…:438-456`) and the OWNER_BOUNDARY amendment §1.2
  (`:60-74`), i.e. B19 scope, not B17 mechanics.

### 11. B27 sleeve-by-sleeve inventory and instrument expressions

Sleeve evidence rows are in the B27 section above. The scoped inventory command
(`git ls-files research | grep -i -E 'cycle|earning|guidance|consensus|dilution|funding|portfolio|catalyst|liquidity|mean.?revers|hedge|defensive|policy.?event'`
restricted to `research/prophet_v4/` and `research/licenses/`) returns 33 paths, all listed with
first heading lines here:

- `CYCLE_CAPTURE_WASHOUT_CW0_ESTATE_SOURCE_AND_SCIENCE_CHARTER_2026-08-30.md` — "# CYCLE CAPTURE /
  WASHOUT CW0 — ESTATE, SOURCE, AND SCIENCE CHARTER"
- `PROPHET_STRATEGY_PLATFORM_AND_CYCLE_CAPTURE_ARCHITECTURE_FREEZE_2026-08-30.md` — "# PROPHET
  STRATEGY PLATFORM AND CYCLE-CAPTURE ARCHITECTURE FREEZE"
- `US_PROPHET_PHASE22_FAST_CYCLE_REGIME_PROSPECTIVE_PREREG_2026-09-19.md` — "# US Prophet Phase 22
  — prospective fast-cycle × hidden-fragility preregistration"
- `earnings_semantics_v1/CASH_FLOW_CASE_2026-10-01.json` (keys: schema, issuer, cik, public_date,
  source_url, retrieved_body_sha256, …)
- `earnings_semantics_v1/CASH_RECONCILIATION_AND_TIMING_2026-10-01.md` — "# Prophet: cash-flow
  evidence and investable information time"
- `earnings_semantics_v1/D5_CONSUMER_2026-09-30.md` — "# Prophet Earnings: source-qualified D5
  detail consumer"
- `earnings_semantics_v1/EVIDENCE_BRIEF_AND_PROFITABILITY_2026-09-30.md` — "# Prophet earnings
  evidence brief and profitability mechanism"
- `earnings_semantics_v1/ISSUER_GUIDANCE_2026-09-30.md` — "# Issuer guidance: revision before
  results, delivery against the right version"
- `earnings_semantics_v1/MICRON_GUIDANCE_VINTAGE_CASE_2026-09-30.json` (keys: schema, issuer, cik,
  fiscal_period, period_end, measure, basis, sources, …)
- `earnings_semantics_v1/PERIOD_COMPARABILITY_AND_VALUATION_2026-09-30.md` — "# Reporting-period
  integrity and price-implied earnings hurdle"
- `earnings_semantics_v1/PROFITABILITY_CASE_2026-09-30.json` (keys: schema, scope, issuer,
  source_url, source_publication_date, …)
- `earnings_semantics_v1/README.md` — "# Prophet Earnings Semantics v1 — source repair and
  research seam"
- `earnings_semantics_v1/information_time_research/EARNINGS_TIMING_AND_B15_DESIGN_2026-10-01.md`
  — "# Earnings information time: research result versus a usable recommendation"
- `earnings_semantics_v1/information_time_research/counterexamples.json` (keys: schema,
  source_formula_ref, formula_scope, neutrality_counterexample, …)
- `earnings_semantics_v1/information_time_research/synthetic_timing_checks.py` — "Synthetic
  arithmetic checks, NOT a reproduction of either earnings study."
- `earnings_semantics_v1/public_profitability_baseline/README.md` — "# Profitability selection is
  not market protection — public baseline"
- `earnings_semantics_v1/public_profitability_baseline/public-profitability-protocol.json` (keys:
  schema, question, scope, created_at, data, source_page, download, start, …)
- `earnings_semantics_v1/public_profitability_baseline/public-profitability-result.json` (keys:
  schema, protocol_sha256, source, sample, results, matched_size_results, high_minus_low, checks,
  …) — keys only; values not opened
- `earnings_semantics_v1/public_profitability_baseline/public_profitability_baseline.py` — "Fixed
  public research-portfolio comparison, not a Prophet model or execution test."
- `earnings_semantics_v1/public_profitability_baseline/reproduction_receipt.json` (keys:
  result_sha256, archive_sha256, script_sha256, protocol_sha256, exact_result_reproduced, …)
- `earnings_semantics_v1/public_value_quality/README.md` — "# Value × profitability: joint
  support, not two automatic conviction bonuses"
- `earnings_semantics_v1/public_value_quality/count-diagnostic.json` (keys: schema,
  archive_sha256, observed_after_return_result, purpose, corner_cells, limitations)
- `earnings_semantics_v1/public_value_quality/protocol.json` (keys: additional_descriptive_contrasts,
  arms, created_at, data_url, falsifiers, fixed_eras, primary_contrast, primary_estimand, …)
- `earnings_semantics_v1/public_value_quality/result.json` (keys: archive_bytes, archive_sha256,
  checks, column_identities, contrasts, primary, protocol_sha256, results, …) — keys only; values
  not opened
- `earnings_semantics_v1/public_value_quality/value_quality_interaction.py` — "Fixed public
  diagnostic; never a native Prophet ranker or promotion test."
- `r6_fable_meta_ceo_handoff/baseline_r5/inputs/PROPHET_US_EARNINGS_CYCLE_R4.md` — "# Prophet US
  R4 — Earnings/Expectation Revision and Cycle Capture"
- `r6_program/wave0/C_EARNINGS_D5_READINESS_CENSUS_2026-09-23.md` — "# Prophet US R6 wave-0
  census C — Earnings/D5 dossier readiness (read-only)"
- `r6_program/wave2/CYCLE_A_ERA_TREATMENT_RECORD_2026-09-23.md` — first line "STATUS: COMPLETE"
- `r6_program/wave2/CYCLE_A_MACRO_DIAGNOSTIC_PREREG_2026-09-23.md` — first line "STATUS: COMPLETE"
- `r6_program/wave2/D03_CYCLE_SOURCE_READINESS_CENSUS_2026-09-23.md` — "# D03 Cycle
  Source-Readiness Census — 2026-09-23"
- `us_prophet_phase22_fast_cycle_regime_prereg_v1.json` (keys: schema, operation, status,
  authority, source_base, phase21_development_evidence, population, fast_cycle, …)

No filename in `research/licenses/` matches the keyword set. **No dedicated research doc exists
for any of the five later sleeves**; their entire BASE footprint is the catalog (md + engine), the
freeze/amendment family law, and the DO_NOT_REBUILD rows listed under B27.

Instrument-expression mentions in the strategy catalog (md + engine):
- md `:98` — "Requires instrument-specific transmission. Futures, ETFs and producers cannot share
  one payoff contract. Carry/roll, producer financing, dilution and hedging matter where
  applicable." (Liquidity/Debasement/Real Assets)
- engine `engine/prophet_strategy_definition.py`: `:382` "equity/future/ETF/producer contracts
  remain distinct" (Cycle sleeve constraint); `:422` `qualified_options_context` (Early Leadership
  optional context); `:439` "US common-stock control first; other markets require native clocks
  and policy"; `:504` "common-stock evidence first; option expression requires separate
  payoff/IV/execution proof" (Earnings); `:531` `options_path_context` (Policy/Event optional
  context); `:542` "instrument must match event exposure; options need separate validation";
  `:563` `dark_pool_or_options_context` (Catalyst); `:574` "liquidity/fillability and
  event-specific instrument proof"; `:605` constraints "no futures/ETF/producer equivalence", "no
  automatic leverage", "no copied US-stock constants"; `:606` "curve/carry/roll or producer
  financing/hedging as applicable"; `:627` `options_pin_context` (Range); `:638` "session/liquidity
  rules specific to instrument"; `:659` `options_path_risk` (Defensive); `:661` entry_owner
  "Portfolio/Risk and separately [source word elided per packet rule] hedge-instrument owner";
  `:674` "borrow/options/hedge payoff and loss semantics required before any expression";
  `:255` `"can_activate_options": False` (catalog authority block).

### 12. B24 portfolio context owner and capital/sizing authority

- Owner module: `app/main.py:2028` `_portfolio_load_holdings`, `:2097` `GET /api/portfolio/brief`
  (Pro-only personalized brief), `:2191` `POST /api/portfolio/changes` (diff view; writes nothing)
  — verified present at BASE. Accepted read contract: the D05 census/ruling pair (2026-09-23)
  accepts watchlist/portfolio separation and rules the thesis candidate owner `public.trade_episodes`
  with a DDL operator gate (`SEAT_RULING_R6-D05-01…:16`).
- Capital/sizing authority: "downstream Portfolio/Risk: sizing, concentration, capital allocation
  and leverage" — `…ARCHITECTURE_FREEZE…:652`; "Prophet has zero sizing or leverage authority at
  sleeve birth" (`:464`); owner matrix rows quoted under B24; catalog
  `cross_sleeve_law.portfolio_allocation_owner = "Portfolio/Risk"` (`engine/prophet_strategy_definition.py:695`);
  B24 release limit "No implicit order, allocation, hedge or parallel position ledger"
  (BUILD_PROGRAM `id="B24"`).

---

## Absent / not found

- `research/prophet_v4/r6_program/wave2/CYCLE_A_MACRO_DIAGNOSTIC_RESULT_2026-09-23.md` — not found
  (searches: `git ls-files research | grep -i CYCLE_A_MACRO_DIAGNOSTIC`; repo grep for
  `CYCLE_A_MACRO_DIAGNOSTIC_RESULT`; `git log --all --diff-filter=A` on the glob).
- `research/prophet_v4/earnings_semantics_v1/PROFITABILITY_INGRESS_2026-10-19.md` — absent at BASE
  (not in `git ls-files research/prophet_v4/earnings_semantics_v1`); exists only on PR #9821 whose
  head `cac29b2909` is not available on host.
- Debt/funding source-rights family — not found in the rights register (full 255-line read; family
  list at `:8`).
- Licensed consensus source at BASE — not found (register `:185-193`, `:231`).
- Sleeve-dedicated research doc or engine module for any of the five B27 sleeves — not found
  (inventory grep above; engine grep for sleeve ids returns only `engine/prophet_strategy_definition.py`
  and its tests).
- B17/B19 content at BASE (`cycle_equity_v1/`, `engine/prophet_cycle_equity.py`, milestone fields)
  — not found; exists only on PR #8308 head.
- BUILD_PROGRAM/DOCKET entries for Q14, Q24, Q09, Q12, Q13, Q15 — Q14/Q24 were outside the
  packet's JSON filter (units B08/B14 name them as research packets; their docket bodies were not
  extracted). Q09/Q12/Q13/Q15 likewise not in the packet's filter list and not extracted.
- `research/prophet_v4/earnings_view/` — not found at BASE (the #7264 proof JSON lives on the PR
  head).

## Outcome files avoided

- `research/prophet_v4/earnings_semantics_v1/public_profitability_baseline/public-profitability-result.json`
  and `.../public_value_quality/result.json` — opened for **top-level keys only** per the packet's
  JSON scope; result values were not read. Their READMEs (in scope as `.md`) were read as research
  records.
- No file under `data/prophet/ledger*`, `*scoreboard*`, `*track_record*`, `*outcome*` or
  `*returns*` was opened; no Cycle macro diagnostic RESULT file was opened (none exists).

## Deviations from packet

- None in substance. Notes: (a) PR #9821 head not available on host — recorded rather than
  fetched (no network permitted); (b) where a quoted source sentence contains a word the packet
  forbids writing, the quote is elided at that word and marked (one instance, Q11 `:661`);
  (c) BUILD_PROGRAM/DOCKET JSON entries were extracted exactly for the packet's filter lists
  (B-units, Q06/Q07/Q08/Q11/Q16/Q17/Q20/Q21/Q23, D03/D04/D05/D08/D12) and key paths are given in
  place of line numbers for JSON.
