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


## 9. Continuing implementation — 2026-11-07 UTC

Chairman's current instruction is to resume implementation and finish integration. The acceptance ruler in section 1 remains in force. The old first-slice custody fence is not a permanent prohibition on a later independently admitted adoption change.

### Source custody and release reconciliation

- Governing protected Mastermind pin is now `d2f72b2d0d3066502adef103afa847904a70b18d`, compatible Sol 1.0.1/bootstrap 1. The changed delivery law was read; unchanged law blobs were compared at the same pin.
- Mastermind [#2157](https://github.com/mastermindx-market-intelligence/Mastermind/pull/2157) merged from head `21775669516630a183817f1ef334be0ff7d4aba2` into actual merge commit `ad6275a9c4d237bce75e52d0d6a8f41264b4ded5` at 2026-11-06T23:50:42Z. Source integration is proven; runtime deployment and natural dossier availability are not.
- Macro [#10806](https://github.com/mastermindx-market-intelligence/macro/pull/10806), head `5b4962a381711328cc01dbe788f9ca4b5f4f7e4d`, was armed once through the incumbent `merge-on-green` controller. Binding candidate checks passed; the inactive Codex queue pilot is not a gate. Full sweep [42340200527](https://github.com/mastermindx-market-intelligence/macro/actions/runs/42340200527), job 128305957178, deferred this exact PR because main commit `b2780954b1f4` changed check definitions and the global CI workload cap had no free slot. This is a stale-proof refresh dependency, not merge or release acceptance. No cap change, duplicate dispatch or direct merge.
- Terminal [#1332](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1332), head `260002504a80e2ce297cec2a82b2f5c73290816c`, passed all 23 checks and entered the existing native merge queue once. Queue readback: `MQE_lQDOTOzwKM8AAAABNbL2Rc4ABTs-zgPMb78`, QUEUED position 1. Open/unmerged at last readback; no resubmission or deployment.
- Initial source workspaces were already clean and released. The installed owner has no recover-existing-branch path. A new **sequential adoption phase**, operation `persistent-sector-leadership-adoption-20261107-c4`, was acquired from exact input `5b4962a381711328cc01dbe788f9ca4b5f4f7e4d`. Its initial acquisition callback was unqualified while hydration continued; original-owner status subsequently proved the correct lock, branch, base and clean tree. No acquisition retry or replacement. Workspace: `/Volumes/Mastermind/agent-workspaces/macro/web/persistent-sector-leadership-adoption-20261107-c4`; branch `sol/web-persistent-sector-leadership-adoption-20261107-c4`.
- This follow-on branch must reconcile the actual #10806 merge/current main before opening its additive adoption PR. It is not a second publication of the initial dossier contract.

### Producer adoption implemented and verified

The existing `engine/sector_central.py::_measured_read` now requests `include_sector_dossiers=True` from the incumbent pure reader. The established Central document and builder remain the only publication path. The default pure reader, source fixture, raw inputs, existing failure stub and legacy fields remain unchanged.

The existing enrolled test file now checks the real Central seam and `compute()` publication: all eleven identities, literal zero, exact 21/63 values, thin/missing reasons, disabled authority and the provenance limits. Unqualified source metadata keeps its legacy measurements while the new dossier values are withheld. Parent direct work uses **PRINCIPAL_JUDGMENT / LOWER_TOTAL_OVERHEAD** for this small producer integration and its custody-sensitive composition.

Validation: `python3 -m pytest -q tests/test_leadership_measured_read.py tests/test_sector_central_measured_panel.py` → **137 passed in 10.32s**, Studio process 45358 exit 0. `git diff --check` clean. This is local candidate proof; no producer/runtime release has been performed.

### Visible consumer implementation in the original paid Fabric carriers

Two disjoint bounded UI builds were requested through native Fabric AUTO admission. Request/controller creation is not a verified worker START or accepted artifact.

| Surface | Original root / run | Controller | Granted source scope |
|---|---|---|---|
| Terminal detail Overview | root `persistent-sector-leadership-20261106-c4`; run `psl3-visible-dossier-20261107-c4` | PID 23389 | New dossier component/styles, narrow Workspace mount, additive EN/ZH lexicon, focused tests/browser receipts |
| Macro measured selected detail | same root; run `psl4-macro-evidence-20261107-c4` | PID 44523 | Additive evidence rendering/styles in existing template and existing enrolled measured-panel tests |

Parent retains source integration, design adjudication and release. Terminal worker input is head `260002504a80e2ce297cec2a82b2f5c73290816c`; Macro input is `5b4962a381711328cc01dbe788f9ca4b5f4f7e4d`. Neither worker may modify initial release branches, producer code, held writers, runtime, gateway/auth, policy or publication. The original root/run/PID must be reconciled; no duplicate or shadow build while an effect is live or uncertain.

The accepted journey is the existing selected-sector Overview/detail. Show exact native 21/63-session evidence, zeros and native null reasons, coverage, explicit missing explanation/risk, and progressive source details in EN/ZH. Preserve selection/history/back, source withdrawal, all eleven identities including a valid all-null dossier, native tokens and responsive accessibility. Fixture/browser proof and natural authenticated production proof remain distinct.

C3 custody inspection found no blanket Workspace/template exclusion. Preserve Terminal #1232 breadth and #1244 refused shell assets; #1249 History/chart hold; Macro #10703 history/router and unpublished basket-cycle work; #10707 refused compact source and uncertain Paper effects. No held code is copied or publication retried.

### Generation and evidence obligations

The original Macro #10780 publisher status now confirms local/remote published head `334b26b540ea82fc2593ab3a723ceda65be32b3b` with retained dirty source. That worktree was not edited, committed, pushed or released. Published #10780 changes Central to accept captured `rotation_payload`; eventual composition must retain that exact-input argument and add the dossier flag, not restore an ambient read.

Its native-view allowlist currently omits `sector_dossiers`; current raw-document consumers and that future native API must be distinguished. Parent is resolving the actual deployment/read path from current owners before altering any additional consumer or generation seam.

PSL-2 native evidence mappings and clocks remain unqualified unless a specific current native contract proves otherwise. The missingness slots are not a completed fundamental explanation. Forecasts, ranking, gating, sizing, trade and escalation authority remain disabled; LR-W6 and the accepted negative findings remain untouched.

### Immediate continuation

Consume both original UI results and exact source artifacts, integrate only granted changes into the admitted follow-on sources, run the necessary actual-path checks, consume original #10806/#1332 release effects, then publish the additive adoption candidate through its exact-head owner. Advance the existing natural producer/consumer path only when its actual source/runtime gates are satisfied. The mission is **MORE_WORK_EXISTS**, not accepted or completed by this milestone.


## 10. Integrated consumer evidence — 2026-11-07 06:05 UTC

This section supersedes the intermediate source/worker states in section 9. The original acceptance ruler and scientific embargo remain in force. This is an implementation milestone, not product acceptance.

### Terminal visible dossier delivered to its original source carrier

The initial parser [#1332](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1332) actually merged at 2026-11-07T05:09:26Z as `df432b7da0222e0641aa1aff1c05b74cc499b5e7`. The paid Terminal UI result was retrieved from exact worker commit `ed951936e8d9fb4ac783e15207129f8e8cabb3d9`, with verified parent/preimages, and integrated into a sequential workspace based on that actual merge. Parent hardening preserves the valid all-null eleven-sector packet, source-withdrawal behavior, exact availability mode/cutoff, null reasons, bounded disclosure continuity, localized labels and null-name fallback.

The resulting exact source head `ba65c3a1caa4ceffc90ea826b839f806ae457273` is published and read back in Ready [#1333](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1333). Its natural CI is [42343740607](https://github.com/mastermindx-market-intelligence/mastermind-terminal/actions/runs/42343740607); last inspected state was running, without an observed failure. No queue or deploy claim is made for #1333.

Local qualification: seven focused files / **184 tests passed**; Next type generation, TypeScript and ESLint passed; **39 integrated Playwright cases passed** across desktop, tablet, 390px and 320px, EN/dark and ZH/light. Discover/Rotation, detail selection, reload/back, keyboard disclosure, access withdrawal and all-null data are exercised. Three reviewed screenshots and the receipt are [committed with that source](https://github.com/mastermindx-market-intelligence/mastermind-terminal/tree/ba65c3a1caa4ceffc90ea826b839f806ae457273/docs/evidence/persistent-sector-leadership-2026-11-07). These use the incumbent development auth/feed seams and are not authenticated production acceptance.

### Macro visible dossier integrated and qualified

The original paid Macro UI result, commit `e6ed73e8cd42322cbd62fe0098759f2b6c171871`, was retrieved through bounded read-only access to its registered worker host. Exact preimages matched the admitted adoption branch; no worker worktree, identity, refs or process was changed. Parent integration enforces the closed v1 contract, all eleven identities, finite/valid measurements matching the current parent read, actual as-known cutoff, coherent status/counts, and all-null owner behavior. A material source change closes previously opened details even when its compatibility key is unchanged.

Qualification on this candidate:

- **96 measured-panel tests passed** (process 80225).
- The measured-reader/contract/native-shell run passed **227 cases**, with one missing tracked router asset caused solely by the sparse checkout. Materializing that exact tracked asset made the one failed case pass (process 283). This is 228 qualified cases across the original run and the focused repair, not a claim that one clean 228-case run occurred.
- **16 component browser cells passed**: 1440/834/390/320px, EN/ZH, light/dark, visible keyboard focus, 44px disclosure target and no horizontal overflow.
- **Two full-template/native-router journeys passed**, desktop EN/dark and phone ZH/light. Actual deep link, select, browser back/forward/reload, Brief-to-map return, normal-to-all-null eleven-row transition and restored-packet disclosure reset all passed without page exceptions. Other organs use intentionally absent fixture data; retained console/resource boundaries are not whole-page production-health proof.
- The existing canonical capture owner produced **16 accepted visual states**, eight rest plus eight real focus states. The initial fixture boot wrongly left English dynamic text under ZH attributes; it was corrected using the production locale/theme boot and its evidence was regenerated. Only the corrected capture is committed.
- Design-system added-style enforcement, runtime-injection gate (275 JavaScript units, 44 injecting sites/88 hits within baseline), visual-evidence gate and diff check passed. The existing sparse-checkout owner materialized only the needed tracked site/mockups trees; source files were unchanged by that operation.

Evidence is in `mockups/evidence/persistent-sector-leadership-20261107-c4/`, with canonical manifest/smells/EVIDENCE receipt plus the full-router journey receipt and screenshots. The full mobile Chinese detail and representative Terminal/Macro captures were visually reviewed. Both original UI Fabric responses are now accepted on actual deterministic test evidence; that acceptance is neither a formal GitHub approval nor production acceptance.

### Holdings provenance is the next source integration

The original holdings result is complete and retrieved from commit `43d7a09c36c7d0a2c5ab2003bbc629d7d06798ca`, tree `0cc68dedecc5d859f2fef5b02ba9cb9f907a6901`. All four preimages match this source despite the worker's divergent base lineage. It adds scalar capture metadata bound to retained rows and a pure receipt with missing/mixed/malformed/consistent states, while leaving the default published coverage v1 unchanged.

Parent review identified two concrete admission gaps to repair before integration acceptance: require complete, explicitly formatted calendar dates instead of inferred pandas dates; and bind each capture URL to the exact canonical requested source for its fund. No provider was fetched, and no holdings mechanism, historical availability, immutable generation or retained source-body claim is admitted by this prerequisite.

### Existing release and runtime owners

Macro #10806 remains on its once-armed `merge-on-green` carrier. Full sweep [42341802632](https://github.com/mastermindx-market-intelligence/macro/actions/runs/42341802632), job 128310891911, explicitly deferred its stale check-definition refresh under the existing capacity cap. The follow-on adoption PR still waits for actual original merge/current-main reconciliation; there is no duplicate initial-contract PR, manual refresh or capacity override.

Terminal's installed source/marker remains `db06eacd8938cf44588d3906bca95bfd7122b74b`. The original owner adoption attempts 44380 and 66573 are CLOSED65. The later attempt refused an unsupported service-hook shape before build/restart and released its lock. Existing repair [#1331](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1331), head `45cf59a1e999ae77871237d024ebb33df6dba9c0`, has successful exact-head CI and a source-only technical PASS. Its ordinary protected release can advance after a current writer/queue fence. Runtime adoption separately requires a current exact containing-release manifest, actual owner/target composition and lease/effect disposition through the original protected-archive entrance. No closed refusal is replayed; no repair is copied into #1333.

Mastermind #2157 is source-merged; its runtime inclusion was [recorded and exactly read back on the original PBR W1 carrier](https://github.com/mastermindx-market-intelligence/Mastermind/issues/1693#issuecomment-6702638417). That owner specifies the November 9 release-day precheck/s0 and target-freeze/composition gates. A current running installer or attention mechanism is not proven. The production Central baseline still lacks the dossier, and the public Terminal session is unsigned.

No deployment, restart, SQL application, permission/grant change, policy/forecast promotion or trade occurred for this milestone. Original held #10780/#10703/#10707 and Terminal #1232/#1244/#1249 are preserved. Continue holdings integration, original protected source delivery, then exact natural generation and authenticated consumer proof. Mechanisms/falsifiers/risk and Macro-to-Terminal-to-portfolio acceptance remain open until actually demonstrated.


## 11. Native capture hardening and next product journey — 2026-11-07 06:13 UTC

The four-file holdings leaf is integrated on the original Macro adoption workspace. Parent review reproduced eleven meaningful failures in the worker candidate before repairing complete issuer-date parsing and exact source/fund binding. The collector now accepts only complete explicitly formatted calendar dates, refusing inferred components, relative words, undeclared day-first numeric forms and timestamps before stored rows/history are touched. The pure receipt now requires the canonical requested SSGA URL for its supported fund, with a drift test against the collector constant.

Network-blocked qualification passed **95 tests**, including real XLSX parsing and parquet round trips; one retained-data case initially skipped because the sparse checkout omitted the tracked XLK file. Materializing that exact 11,185-byte source blob `b4c56a80b3966225cdff8d8de30c130281f921e9` made the isolated case pass. This is **96 qualified cases across two runs**, not a claimed single clean 96-test run. Default published coverage v1 remains byte-identical with/without capture fields; the fixed six-column history archive and legacy unknown date origin are preserved. No provider acquisition or data-store publication occurred. The original holdings Fabric response is accepted on this deterministic integration evidence.

The Macro UI/evidence commit is locally retained as `5a496270f6a4d38791da403f8b50f213047d4cc4`. Its original typed push returned **EFFECT_UNKNOWN / PUSH_RESULT_UNCERTAIN**, action `a4764ca4e855324291cbb3b548fb76290ef237c0f81f46c749722213ce4aa63e`. Same-owner status and GitHub ref readback still showed prior `65df4b24b255d89f815208f00e4b6e158b85c2c8`; no live push or retained journal was found. That is not proof of a terminal remote effect. The installed C4 publisher lacks the protected recovery capability. No retry, new branch, alternate publisher, fabricated receipt or gateway upgrade was attempted. Local descendant edits/tests/commits preserve the original immutable push payload and can proceed independently; remote publication remains fenced.

Terminal #1331 passed its exact source/control fence and entered the incumbent native protected queue once, head `45cf59a1e999ae77871237d024ebb33df6dba9c0`, queue entry `MQE_lQDOTOzwKM8AAAABNbKmpc4ABTs-zgPMmDs`, observed QUEUED position 1. Neither source queue admission nor later merge supplies runtime adoption clearance. The held Website Beta composition is not a generic prerequisite for a separately qualified PSL production target.

Terminal #1333's natural CI actual checkout `103179b83134fe133726d423f2e940223cbf44cf` passed typegen, tsc and capture, then reported **20,123 passed / 1 failed / 50 skipped / 4 todo** in unit tests. Its single failure is the pre-existing options axis capture's unmocked optional `/api/brain/me` dependency returning 502 twice in desktop-compact. The original retained artifact proves the exact URLs; assertions are preserved. A bounded [same-carrier capture isolation repair](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1333#issuecomment-6703186621) was delivered to paid Fabric run `psl-ci-capture-isolation-20261107-c4`, controller 74224. No CI rerun or duplicate build was initiated.

The scope review confirmed the first slice still owes the useful Terminal-to-Portfolio journey. A [bounded implementation commission](https://github.com/mastermindx-market-intelligence/Mastermind/issues/1202#issuecomment-6703176081) is delivered on original root to paid Fabric `psl6-portfolio-continuity-20261107-c4`, controller 72014: reuse the strict current dossier, authenticated sector API, admitted return state, existing Portfolio Risk section/positions props and cost-cohort owner. Exact directly held sector ETFs may be shown; constituent attribution, price-based causality, trading, positions/targets and held Portfolio Brief paths remain outside the grant. Required cases cover owner/access races, source withdrawal, nulls, currency/cost unknowns, no writes and real local navigation. Controller delivery/lease/launch logs are not yet a root-verified accepted worker result.

The current mission remains **MORE_WORK_EXISTS**. Continue original paid results and exact source integration; qualify the missing same-owner C4 publisher successor if its actual custody admits it; preserve the old unknown push; complete normal protected releases; prove a natural generation and authenticated Macro/Terminal/portfolio path. Qualified mechanisms/falsifiers, incumbent descriptive risk and an earlier admissible cut remain original acceptance requirements.


## 12. Current constituent identity and evidence journey (2026-11-07)

Current candidate owner qualification now resolves both `store/NVDA` and `store/MU` through the incumbent committed reference generation `7308bc1dc500645e4629881b7f306f64211cb05d`. The complete owner receipts and source hashes are retained in `research/evidence/persistent-sector-current-member-identity-20261107.json`; parent recomputed both canonical receipt digests and byte lengths exactly. This is local candidate-source proof, not authenticated deployed HTTP, historical SSGA member identity or private disclosure availability. The frozen Data Workspace reader's earlier refusal is preserved; its different identity dependency is not substituted for the current candidate.

The retained XLK sample includes MU at rank 6 (3.85%) on 2026-10-22. It lacks capture/native-ID provenance. Native C01 planned HBM3E/H200 integration is a **MU-subject** disclosure dated 2024-02-26, with NVDA as object; it must not become an NVDA-subject claim, current planning/shipment/magnitude, or a sector-leadership cause. The exact raw membership, current identity and original disclosure clocks stay separate.

A bounded paid consumer build is commissioned as `psl-member-evidence-20261107-c4`: https://github.com/mastermindx-market-intelligence/Mastermind/issues/1202#issuecomment-6703553476 . It mounts the existing `CompanyIntelligencePrivate` host inside the selected-sector member journey, using the live existing holdings feed and explicit open action. Reuse private auth/entitlement, current-company/issuer/fact controllers and qualified panel; keep closed sector dossier v1 unchanged. Parent owns cumulative Workspace integration with the original Portfolio child and natural authenticated acceptance. M2's fixed private disclosure root is absent; existing deployment-owned current pointer/manifest and entitled live reads remain required.

Terminal #1333 now publishes capture repair `fa79003d23cc08216ced65935e80b0e95a54a285`; six real-browser isolation tests and type/lint checks pass, natural CI run `42347628408` remains separate. The source-only release repair #1331 merged as `b0bda003…`. Its new exact-artifact production attempt `47239` established CLEAN/current source and exact target, then exited with code 65 at the manager PATH guard before reset/build/start. The shared lock was released and serving marker and HEAD remained `db06eacd8938cf44588d3906bca95bfd7122b74b`. Follow-up SSH qualification timed out; no PATH/config change or retry occurred. Original attempts `44380`/`66573` and new attempt `47239` are distinct closed effects.

The C4 publisher successor build remains on original run `psl-c4-publisher-successor-20261107-c4`; it is necessary to add legitimate forward-only recovery for the historical unknown Macro push. Current Macro local source and evidence remain descendants of its immutable attempted commit. Required CI, source/runtime gates and full original DONE_WHEN remain open; no phase or worker return closes the product.


## 13. Exact-window source integrated; natural composition and consumers next

The original adoption carrier now incorporates the qualified optional exact 5/20/63-session producer from f55dda94ca7fe283e7066ceaad2d9438956062d9 (tree e02f5323f418f5333634f3c16e4e970e15b0943a). Closed dossier v1 stays 21/63; its default bytes and legacy projection remain unchanged. The new companion binds its session, benchmark, cohort and total-return basis to the parent generation, validates percentages after scaling, and carries bounded detached attribution without upgrading it into availability proof.

Parent qualification: 124 measurement cases and 261 adjacent contracts passed on the exact return; the integrated adoption context passed 225 cases after preserving the earlier Central adoption tests and assertions. Evidence and source hashes are in research/evidence/persistent-sector-exact-windows-20261107/source-evidence.json. The original uncertain publication effect remains fenced; local source integration is not a push or deployment claim.

Next: bind the existing captured total-return panel and US session reference through Sector document composition; add the separately parsed companion to the existing Terminal dossier/Portfolio surface; integrate the corrected native projector after qualification consistency fixes; then adopt the pure dated-context projection through existing capture and mapping owners. Current data, historical selection/availability, scientific mechanism validation, protected releases and authenticated production journeys remain required. No new history, mapping, acquisition or publication owner is introduced.


## 14. Dated-context correction integrated and qualified

The original adoption workspace now incorporates the exact two-file corrective leaf `6a44d1a961e3109adc5341ed25176e784bff384c`. The pure projector qualifies counts, narrative support, configured roster identities, owner clocks, independent provisional flags, risk subsection references and bounded detached outputs. The accepted legacy test preimage is unchanged: all 62 existing top-level definitions retain identical ASTs, with no removed lines.

Parent qualification on the integrated source passed all 107 contract cases using a private temporary directory, including the pinned primary-source output. Its 9,566-byte primary result remains byte-identical across correction, SHA256 `db9d0aef9895a49f83aade7b3dee645ca98580ff630902dae05aa6f354ebf1d6`. The source/effect manifest is `research/evidence/persistent-sector-dated-context-20261107.json`. Fabric acceptance records source qualification, not current-sector, historical, release or product acceptance.

The projector remains dormant pending the existing capture and consumer integration. Current-sector usability and historical admissibility remain false; original availability remains unknown, native theme-to-sector mapping unavailable and authority display-only. The previous original publication uncertainty and CI-registration action fences remain in force. Continue exact captured composition and native/UI integration on their original source carriers, followed by the protected releases and authenticated natural product journey.
