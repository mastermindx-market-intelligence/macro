# Persistent Sector Leadership — master plan

Recorded: 2026-11-06. Editorial implementation plan; not a runtime registry, scientific promotion, release approval or trading mandate.

## 1. Assignment, source and completion ruler

Chairman asks this session to create the master plan and proceed directly into implementation of the [Persistent Sector Leadership census](https://github.com/mastermindx-market-intelligence/Mastermind/issues/1202#issuecomment-6695716256). The parent is Mastermind #1202. Reuse Macro WS:LEADERSHIP-ROTATION-INTELLIGENCE and its Sector Central journey; preserve the wider MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT programme and its accepted packages.

Operation: `persistent-sector-leadership-20261106-c4`.
Procedure: Mastermind protected master `fa46c271b23902555c5f3c83592edc2cf77069c6`, compatible `mastermind.sol_skillpack.v1` 1.0.1, bootstrap-major 1.
Source base: Macro main `26946d4f7b921a0940eef016c9d81fcf1adbeeda`.
Terminal inspection pin: `3095319891bb557ba41f6c6fb5ec99a8aeaac0fc`.
Source carrier: Macro `sol/web-persistent-sector-leadership-20261106-c4`; one managed Studio workspace, one branch, one PR.

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

| Node | Depends on | Deliverable and acceptance | Initial state |
|---|---|---|---|
| PSL-0 | current source | Freeze this plan, ownership/negative-evidence map, exact carrier and source readback | in_progress |
| PSL-1 | PSL-0 | Pure bounded dossier composition integrated into incumbent measured-group read; no I/O; exact windows, identity, nulls, clocks, source roots and disabled authority; adversarial contract tests | ready |
| PSL-2 | PSL-1 | Qualify existing fundamental/risk source mappings and PIT clocks; compose one real per-sector explanation with alternatives/falsifiers; no fabricated context when unavailable | proposed |
| PSL-3 | PSL-1, trusted generation | Adopt the same dossier in existing Sector Central and Terminal detail paths; shared content, source inspector, responsive accessible states; coordinate active UI/generation writers | blocked: #10780 freshness and source collisions |
| PSL-4 | PSL-2, PSL-3 | Mastermind portfolio read-only consumer parity and inspectable attribution; no policy mutation | proposed |
| PSL-5 | qualified evidence | Prospective research specification and existing outcome-store accrual; incremental OOS, honest episode N, leakage/cost checks, invalidation tests; no outcome peeking or model promotion | proposed |
| PSL-6 | PSL-1–4 | Required CI/release, natural producer evidence, authenticated browser/API/portfolio read-path proof, correction/failure matrix; cumulative continuity | proposed |
| PSL-7 | accepted native mappings | Extend to themes/subsectors and other markets using incumbent owners and separately qualified data/science | proposed |

### First implementation slice: PSL-1

Source scope: new pure dossier helper if needed, `engine/leadership_rotation_context.py`, focused existing/follow-on tests and this plan. Reuse `measured_group_read` so every existing reader can receive the exact same dossier; avoid a standalone producer or publication file. Keep the existing schema's required fields and ordering compatible.

Freeze the minimum useful object after reviewing actual source: measured profile plus data availability and explicit unqualified mechanism/risk slots, not invented fundamental claims. If optional source inputs are admitted, they must be explicitly mapped and dated. The first implementation must be reachable through the existing public Python reader, not a disconnected schema/demo.

Discriminating proof: preserve zero; reject boolean/nonfinite/malformed values; missing member not zero; wrong cohort/benchmark/session cannot join; no 21→20 relabel; later information cannot enter an earlier decision cut; duplicates cannot inflate coverage; retracted evidence cannot remain active; output deterministic, JSON-safe and bounded; caller inputs unchanged; all trade/rank authority disabled; existing measured-reader tests remain valid. Synthetic fixtures prove these semantics, not live scientific validity or production.

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

- Bootstrap and exact source census completed; no overlapping Persistent Sector Leadership PR found by exact GitHub search.
- First workspace acquisition: NOT_APPLIED / REPOSITORY_SOURCE_UNAVAILABLE. Normal origin/main fetch completed (PID 60296, exit 0), fixing missing exact base.
- Second acquisition callback was unqualified. Reconciled through original `studio_git_publish_status`: same operation/branch, clean local head exactly equal to the pinned Macro base, remote absent. Registered worktree carries the operation lock. No retry or replacement workspace.
- Existing accepted work is not reopened. No worker has been dispatched; no production or publication effect yet.
- Next: commit/read back this plan; commission bounded PSL-1 against its frozen contract while the parent adjudicates fundamental and cross-consumer architecture; inspect exact returned bytes, repair concrete defects, and advance the next safe phase.
