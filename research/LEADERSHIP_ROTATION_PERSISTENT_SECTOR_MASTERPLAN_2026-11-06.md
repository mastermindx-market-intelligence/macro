# Persistent Sector Leadership — master plan

Recorded: 2026-11-06. Editorial implementation plan; not a runtime registry, scientific promotion, release approval or trading mandate.

## 1. Assignment, source and completion ruler

Chairman asks this session to create the master plan and proceed directly into implementation of the [Persistent Sector Leadership census](https://github.com/mastermindx-market-intelligence/Mastermind/issues/1202#issuecomment-6695716256). The parent is Mastermind #1202. Reuse Macro WS:LEADERSHIP-ROTATION-INTELLIGENCE and its Sector Central journey; preserve the wider MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT programme and its accepted packages.

Operation: `persistent-sector-leadership-20261106-c4`.
Procedure: Mastermind protected master `fa46c271b23902555c5f3c83592edc2cf77069c6`, compatible `mastermind.sol_skillpack.v1` 1.0.1, bootstrap-major 1.
Source base: Macro main `26946d4f7b921a0940eef016c9d81fcf1adbeeda`.
Terminal inspection pin: `3095319891bb557ba41f6c6fb5ec99a8aeaac0fc`.
Source carriers: Macro `sol/web-persistent-sector-leadership-20261106-c4` / #10806; Terminal `sol/web-persistent-sector-dossier-parser-20261106-c4` / #1332; Mastermind `sol/web-persistent-sector-portfolio-projection-20261106-c4` / #2157. Each has its own original managed Studio workspace and exact-head publisher; no replacement carrier.

User job: understand which sector is leading, whether leadership is broad or concentrated, why it might persist, what evidence contradicts that explanation, what would change the view, and how the existing portfolio policy treats the risk. Machine job: supply the same dated, bounded, source-qualified dossier through incumbent Macro, Terminal and Mastermind readers.

DONE_WHEN: a real source generation yields the same sector identity, measurements, explanation, missingness and risk context in Sector Central, Terminal and the portfolio intelligence reader; the user can inspect evidence and clocks, compare sectors and revisit an earlier admissible cut; stale/conflicting/revised input cannot become current or historical truth; all predictive outputs remain unavailable until separately qualified; exact source, CI, authorized release, production API/browser and consumer-parity evidence are retained. A source slice or green CI does not complete this ruler.

## 2. Product thesis and hard boundaries

The differentiator is a coherent explanation backed by dated evidence, not another composite score. Four separate lenses answer four questions:

1. **Observed leadership:** absolute and benchmark-relative returns, participation, concentration and the existing measured group/transition state.
2. **Mechanism:** earnings/revisions, margins, supply constraints, demand and economic transmission, with competing causes and falsifiers.
3. **Risk:** uncertainty, crowding, invalidation evidence and the incumbent Risk Envelope's independently defined state/policy.
4. **Portfolio context:** relevant held/watchlist exposure and the existing policy source; no dossier-generated admission, sizing, leverage or orders.

Start with the existing 11 US sector ETF cohort. Preserve ETF-proxy versus constituent membership identity. Theme/subsector/country expansion requires its native membership, source clocks and benchmark contracts, not relabelled US outputs.

Source facts, descriptive transformations, model hypotheses and validated forecasts remain distinguishable. An LLM may summarize admissible evidence with citations; it cannot author dates, identifiers, returns, confidence probabilities, weights, gates or allocations. No new model pool, scheduler, ledger, event bus, taxonomy, thesis lifecycle, publisher, auth boundary or portfolio engine.

## 3. Incumbents and collision map

| Surface | Reuse | Boundary |
|---|---|---|
| Measured sector read | `engine/leadership_rotation_context.py::measured_group_read` | Pure composition over supplied inputs; no producer or network invocation |
| Sector inputs and native views | `engine/sector_cycles.py`, `sector_central.py`, `sector_pulse.py` | Macro #10779 / PR #10780 owns coherent runtime generation/freshness; do not edit its active paths in the first slice |
| Lifecycle/flow | rotation_events, subsector_rotation, group_flow, sector_signals | Preserve each owner's units, clock, evidence mode and scientific status |
| Fundamental explanation | group_earnings, theme_revisions, bottleneck, foresight_cascade, subsector_scan, market_drivers | Explicit sector/theme mapping and point-in-time availability required |
| Semantics and causal evidence | theme_graph; neuralweb causal schema/targets/audit and existing ledger | Existing causal targets are regime_risk and entry_quality, not sector dwell/return forecasts |
| Risk | risk_envelope, market_state, risk_radar, narrative_rotation | Separate measured, hazard and policy; #10489 remains its original repair carrier |
| Product | Sector Central / Macro #7646; Terminal sectorIntelligence reader and native dossier | The 92-capability migration crosswalk is draft; #10777 and #10703/#10707 retain their design/source holds |
| Portfolio | Mastermind portfolio_intelligence, neural_web_context, context_gate, entry_quality, held_risk | Read-only advisory seam; no new ranking/portfolio rules |
| Early pivots | Macro #10785 | Independent early-turn/false-bounce carrier; no duplicated detection |

Freshness PR #10780 inspected at `334b26b540ea82fc2593ab3a723ceda65be32b3b`, open, unmerged. Its changed paths include Sector Central, Pulse and native generation. The dossier can be built and tested against immutable supplied evidence while live-generation adoption remains dependent on that carrier.

Existing LR-W1–W5 results and T26 disposition remain accepted as recorded; LR-W6 and its unread P1/P2/P3 scientific gates are not reopened by this plan. The source handoff has historical unresolved entries; the current WS and actual artifacts outrank those stale lifecycle descriptions.

## 4. Contract and semantic decisions

### Identity and clocks

Each dossier binds schema/version, group_id, group_kind, cohort_id, benchmark, source generation, price basis, source/session dates, computed/read time where actually known, availability mode and source references. Do not fabricate a receipt timestamp to upgrade historical availability.

Keep published, first-seen/available, effective/session, computed and decision-cut clocks distinct. Current descriptive data lacking an original availability clock may be displayed as current/reconstructed evidence with its limitation; it must not become as-known historical evidence. Future, undated, stale, mismatched-generation, conflicting identity and retracted evidence have explicit null reasons. No current-only reader in historical replay.

### Measurements

Keep absolute return separate from relative wealth `(1+R_group)/(1+R_benchmark)-1` and return difference. Units are explicit; booleans, NaN/infinity and malformed values are not numbers. Preserve zero.

The motivating brief requests 5/20/63-session views. The incumbent measured read currently exposes **21 and 63 sessions**; do not rename 21 to 20 or synthesize missing 5/20-session values. Display exact available windows; add 5/20 only through the accepted price owner with correct endpoints and basis.

Show observed breadth and eligible/covered denominators; identification bounds are not confidence intervals. Missing constituents are not nonparticipants. Sector ETF leadership is not by itself a stock-selection forecast. Correlated windows, sector/ETF/member overlap and repeated source roots do not count as independent votes.

### Evidence and explanation

Every mechanism item needs stable evidence identity, source/owner reference, exact group/cohort binding, epistemic class, source/availability clocks, coverage, source roots and a supported claim. Preserve correction/supersession/retraction lineage. Summaries may not invent economic mechanisms from coincident price moves.

An explanation presents supported mechanisms, alternative causes, contradictory evidence, falsifiers and the next observable check. If source evidence is absent or cannot be mapped safely, show unavailable with reason; a generic narrative is not a substitute.

### Risk and prediction

Risk remains a source-qualified pointer/projection of the existing risk owner. Distinguish market-global risk from sector-specific evidence. Expose conflict; do not average it away.

Always carry explicit authority: may_rank=false, may_gate=false, may_size=false, may_trade=false, may_escalate=false. No new conviction/expected-return/dwell probability or allocation weight. Forecast fields are null with `not_qualified`; model qualification and downstream policy admission are separate later gates.

## 5. Delivery tree

Editorial task IDs below are not Executive Job or Agent OS wave IDs. Status is source/evidence status only.

| Node | Depends on | Deliverable and acceptance | Current state |
|---|---|---|---|
| PSL-0 | current source | Freeze this plan, ownership/negative-evidence map, exact carrier and source readback | published in Draft PR #10806; Agent OS linkage proposed in the same carrier |
| PSL-1 | PSL-0 | Pure bounded dossier composition integrated into incumbent measured-group read through explicit opt-in; no I/O; exact windows, identity, nulls, clocks, source roots and disabled authority; adversarial contract tests | implemented; 236 focused tests passed; hosted CI and consumer activation pending |
| PSL-2 | PSL-1 | Qualify existing fundamental/risk source mappings and PIT clocks; compose one real per-sector explanation with alternatives/falsifiers; no fabricated context when unavailable | bounded source audit completed; native mapping/clock/rights obligations recorded; no evidence adapter admitted |
| PSL-3 | PSL-1, trusted generation | Adopt the same dossier in existing Sector Central and Terminal detail paths; shared content, source inspector, responsive accessible states; coordinate active UI/generation writers | typed standalone Terminal consumer implemented in #1332, 80 tests/typegen/typecheck/lint passed; native generation and visible UI adoption pending custody reconciliation |
| PSL-4 | PSL-2, PSL-3 | Mastermind portfolio read-only consumer parity and inspectable attribution; no policy mutation | explicit existing-tool dossier projection implemented in #2157; 65 new tests, 123 combined passes/1 live-data skip; fixture and retained-native transport parity proven locally; exposure/production parity pending |
| PSL-5 | qualified evidence | Prospective research specification and existing outcome-store accrual; incremental OOS, honest episode N, leakage/cost checks, invalidation tests; no outcome peeking or model promotion | proposed |
| PSL-6 | PSL-1–4 | Required CI/release, natural producer evidence, authenticated browser/API/portfolio read-path proof, correction/failure matrix; cumulative continuity | focused local proof and source readbacks retained; required hosted checks/protected release and production proof remain distinct outstanding effects |
| PSL-7 | accepted native mappings | Extend to themes/subsectors and other markets using incumbent owners and separately qualified data/science | proposed |

### First implementation slice: PSL-1

Source scope: private pure dossier helpers inside `engine/leadership_rotation_context.py`, `tests/test_leadership_measured_read.py`, this plan and Agent OS continuity. The public seam is `measured_group_read(..., include_sector_dossiers=True)`. Its default remains byte-identical to the frozen v1 producer/parser fixture; this slice does not silently activate consumers. The optional addendum is versioned `leadership_rotation_context.sector_dossiers/v1`. No standalone producer, publication file or new exported core-contract API is introduced.

The existing `leadership-measured-read` and `leadership-rotation-countercases` jobs already enroll the incumbent module/test paths. The helper stays in that module because #10780 also owns `.github/ci/legacy-jobs.yml`; a new import-closure file without path enrollment would weaken future CI selection. This implementation leaves that live writer's manifest unchanged. The nominal expanded fixture fits 32 KiB; the original default 16 KiB test and frozen bytes remain unchanged. This is fixture qualification, not a production latency/size SLA.

Freeze the minimum useful object after reviewing actual source: measured profile plus data availability and explicit unqualified mechanism/risk slots, not invented fundamental claims. If optional source inputs are admitted, they must be explicitly mapped and dated. The first implementation must be reachable through the existing public Python reader, not a disconnected schema/demo.

Discriminating proof: preserve zero; reject boolean/nonfinite/malformed values; missing member not zero; wrong cohort/benchmark/session cannot join; no 21→20 relabel; later information cannot enter an earlier decision cut; duplicates cannot inflate coverage; explicit malformed provenance and relative wealth below -100% are withheld; no active mechanism/retraction claims are admitted in this slice; output deterministic, JSON-safe and bounded; caller inputs unchanged; all trade/rank authority disabled; existing measured-reader tests remain valid. Synthetic fixtures prove these semantics, not live scientific validity or production.

### Consumer seams and source qualification discovered during implementation

- Macro already publishes `measured_read` from `engine/sector_central.py::_measured_read`. Enabling the new flag there is an integration change held behind the current #10780 generation writer; no new endpoint is needed.
- Terminal's incumbent `sectorMeasuredRead` remains unchanged. New separate `terminal/lib/sectorDossiers.ts` validates and preserves the full optional native dossier, including all eleven identities and unavailable states. The existing gateway already passes the source payload. #1232 owns the shared parser, #1244 the gateway/shell, and #1249 the cycle/Workspace design; those paths were left byte-identical to the source base. Visible detail/source-inspector adoption still requires the reconciled accepted journey.
- Mastermind's default `sector_rotation(limit=6)` remains the existing legacy top-N packet. Its explicit `projection="sector_dossiers"` and the same selector on `brain/autonomous_mcp.py::get_sector_rotation` now offer a separate bounded all-eleven projection. No second tool or policy is created. The serializer is unchanged; schema/coverage/reasons are qualified after actual serialization.
- The legacy `generation.id` is `session|benchmark|cohort`, a compatibility key. It is not an immutable generation, revision or original-availability receipt. The dossier names it accordingly and leaves those stronger claims unavailable.
- `group_earnings` is keyed by basket identity and computes dated membership; `theme_revisions` is keyed by configured themes. Neither is a sector-ETF mapping. A build timestamp or latest source date does not prove original availability for a historical cut.
- Cross-sector ETF positive counts are distinct from within-sector constituent participation and concentration. Those two constituent fields remain unavailable until native membership/weights are admitted.
- Native Sol architecture judgment found malformed supplied row provenance and below-domain relative wealth as concrete risks; both were repaired and tested. This advisory work is not a formal GitHub approval.

### Science gate (PSL-5)

Preserve these negative findings by name:
- group_flow validation is display_only; forecast weights zero.
- Pulse heating/hot did not demonstrate a forward-return edge; broken has a separate risk-timing finding.
- Trend Persistence Wave C sector/group constructions are C1-NULL; no C2 and no resurrection as a built predictive field (DNR:KILL-TREND-PERSISTENCE-SECTOR-GROUP-PERSISTENCE).
- Defensive/sector rotation-to-vol-shock lead failed OOS.
- US absolute-trend result is drawdown control, not directional alpha; China is distinct.
- No rotation × cycle confluence or parallel schedule (DNR:KILL-ROTATION-CYCLE-CONFLUENCE; DNR:KILL-ROTATION-SCHEDULE).

A genuinely new hypothesis needs a new pre-registration defining target, horizon, formation/availability, membership, episodes, exclusions, primary metric, nested baselines, multiple-testing budget, size/power and held-out/future splits. Baselines include own trailing return/volatility and existing sector/risk information. Measure incremental explanatory/forecast value and costs; inspect motivating examples without treating them as independent validation. Qualification needs frozen forward-ledger maturity and a separate downstream policy decision. Null results remain publishable results.

## 6. Product and operational acceptance

Extend the existing Sector Central/detail workflow; no third navigation or parallel ranking screen. Default view should answer the four lenses concisely, with source details progressively disclosed. Reuse current design tokens and accepted Paper/migration contracts. Dark and light receive deliberate hierarchy; EN/ZH meaning matches; desktop/mobile support keyboard, visible focus, reduced motion and complete loading/empty/stale/partial/denied/error states. Do not add decorative container accent stripes.

Evidence drawer: exact source, native dates, units/window, membership/coverage, dependencies, corrections and scientific status. History view labels reconstructed versus naturally observed/as-known evidence. Compare states without conflating magnitude, breadth and persistence.

Use the existing scheduler, artifact/generation owner, auth and observability. Track source age, missingness, generation mismatch and reader latency through those owners. Establish a baseline before setting latency/size budgets; do not claim a low-latency SLA from static files. Rendering failures must preserve the rest of the existing journey. Rollback removes the additive dossier projection; never rewrites source history or policy state.

Final proof spans one real dated sector (including a motivating concentrated technology/semiconductor case where data supports it), at least one contradictory/unavailable case, source→Macro→Terminal→portfolio equivalence, authenticated and denied routes, and correct revision behavior. Preserve all eleven sectors including nulls; cherry-picked available examples cannot establish coverage.

## 7. Execution, review and continuity

The assigned parent retains architecture, source integration and acceptance. Eligible bounded build work uses admitted paid Fabric with the original root/parent identities; native children, if used, are architecture/adversarial judgment only. No silent native labor fallback. Direct source work is allowed for documented PRINCIPAL_JUDGMENT, LOWER_TOTAL_OVERHEAD, CRITICAL_PATH_SHORTCUT or NO_ELIGIBLE_PRE_EFFECT_WORKER with nonconflicting custody. The Web session review waiver applies; real GitHub/release/security holds remain.

No live trade, new credential/provider, service activation, forced push, protected direct merge or duplicate release carrier is authorized by this plan. Macro release uses its incumbent merge-on-green checks when the candidate is qualified and release is permitted. CI, merge, deployment and production acceptance remain distinct.

Milestones update this same plan's evidence table and the lawful Agent OS handoff/WS linkage with readback. Do not change LR-W6 science state or a sister programme's ongoing wave. Initial plan may be committed before organization linkage (`PLAN_NOT_ORG_LINKED`); that does not block disjoint source work.

## 8. Evidence and next action

Source qualification and consumer admission details: [source audit](LEADERSHIP_ROTATION_PERSISTENT_SECTOR_SOURCE_AUDIT_2026-11-06.md). Retained native read: [proof receipt](LEADERSHIP_ROTATION_PERSISTENT_SECTOR_NATIVE_READ_2026-11-06.json). Negative transport probe and qualified compact consumer proof: [transport receipt](LEADERSHIP_ROTATION_PERSISTENT_SECTOR_TRANSPORT_PROBE_2026-11-06.json).

- Bootstrap and exact source census completed; no overlapping Persistent Sector Leadership PR found by exact GitHub search. This source candidate is [Macro Draft PR #10806](https://github.com/mastermindx-market-intelligence/macro/pull/10806).
- Initial plan commit `d213d0ee71d8b0736b1f58f35dbfe185cfc76889` was published through the original Studio source carrier and read back byte-identically from GitHub.
- First workspace acquisition: NOT_APPLIED / REPOSITORY_SOURCE_UNAVAILABLE. Normal origin/main fetch completed (PID 60296, exit 0), fixing the missing exact base.
- The subsequent acquisition callback was unqualified. Original publisher status and registered worktree receipt reconciled the same operation/branch/base. No replacement worktree or blind retry occurred.
- Fabric request `psl1-dossier-build-20261106-c4`, controller PID 79844, was retained and returned `REQUEST_REFUSED_BEFORE_LAUNCH / EXECUTION_NOT_ELIGIBLE`; native status reported execution absence and controller exit 75. No worker START or source result exists. No retry/failover/native build substitute was launched. Parent direct work uses `NO_ELIGIBLE_PRE_EFFECT_WORKER` in the verified source workspace.
- Local verification after the two hardening repairs: `python3 -m pytest -q tests/test_leadership_measured_read.py tests/test_leadership_rotation_contract.py tests/test_sector_central_measured_panel.py tests/test_group_read_surface.py` → **236 passed in 11.58s**, Python 3.14.7, process 1136 exit 0. Existing frozen fixture and assertions were preserved. This is local proof, not a hosted CI or production receipt.
- Implementation commit `378e289b180b90ed2902a7689e960932a8a26fe6` was pushed through the same carrier; GitHub readback matched the plan/handoff and confirmed the opt-in code. Local and remote heads matched. Agent OS validation: 0 errors, two pre-existing prefix-style `owns_paths` warnings; diff check clean.
- Native-shape proof: retained 2026-10-22 Sector Cycles artifact, SHA-256 `46a7b95a11446f12028a90cb071955710d516accd68f49db5ad99bab111194fa`, produced all eleven measurements through the new public opt-in; original file and legacy projection stayed unchanged; dossier remained partial and freshness/as-known availability unqualified. The retained risk artifact was from 2026-10-23 and DEGRADED, so no cross-session risk join was admitted. See the linked audit/receipt for precise scope.
- Terminal consumer #1332 is Ready at `260002504a80e2ce297cec2a82b2f5c73290816c`: 80 focused tests, installed Next route type generation, full TypeScript check and lint passed. Only five new files were added; the gateway, shared parser, Workspace and frozen fixture remained byte-identical. It is a dormant parser, not a visible UI claim.
- Mastermind consumer #2157 is Ready at `21775669516630a183817f1ef334be0ff7d4aba2`: 65 dossier cases and 123 combined passes/1 incumbent live-vendor skip through actual MCP handler/unchanged serializer. Qualified and unavailable fixture responses are 4,323 and 4,943 UTF-8 bytes with all eleven groups and no truncation. Native retained 2026-10-22 input gives 4,298 bytes and identical measurements/shared qualifications; this was composed locally, not naturally published or served in production.
- The raw passthrough probe exposed real transport loss: legacy six-sector/six-basket packet plus dossier kept only three of eleven rows; unavailable standalone native dossier kept ten. The new selected projection has a 7,200-byte ceiling and an explicit all-eleven unavailable fallback. Never equate the native 32 KiB fixture allowance with the MCP transport budget.
- Source publication/readback is verified for all three original carriers. Sector Central generation, visible Terminal adoption, native source-clock/correction contracts, mechanism/risk qualification, required release and production/browser proof remain unverified. Existing held legacy-reader, serializer, snapshot and design repairs were not replayed.
- Existing LR-W1–W5 acceptance and LR-W6 scientific embargo remain unchanged. There are no live child workers or watcher loops. No merge, release, deployment or production-acceptance claim is made.
- Next material action: qualify the exact current heads of #10806, Terminal #1332 and Mastermind #2157 through their existing required checks and protected release paths; repair concrete findings on those same carriers. Then reconcile #10780 native generation and the accepted Sector Central/Terminal design writers, adopt the already-qualified dossier through those incumbent paths, and prove one natural generation at all consumers. Source mapping/clock/rights obligations from the audit still precede mechanism/history admission. The current receiver owns these actions; no archived author or invented review ceremony is a dependency.
