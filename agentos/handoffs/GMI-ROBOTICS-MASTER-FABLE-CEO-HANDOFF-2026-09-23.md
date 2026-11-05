---
schema: mastermind.agent_handoff.v1
title: "GMI Robotics — Master Fable CEO End-to-End Handoff"
operation_key: gmi-robotics-fable-ceo-e2e-20260923-chairman-001
parent_operation: gmi-robotics-bom-research-20260923-sol-001
program: gmi-theme-graph
repository: mastermindx-market-intelligence/macro
preferred_avenue: Fable
receiver_binding_mode: CAPACITY_SELECTABLE
placement_state: WAITING_CAPACITY
needs_placement: true
mission_complete: false
finalization_classification: CHECKPOINTED_CONTINUATION
---

# GMI Robotics — Master Fable CEO End-to-End Handoff


## 2026-09-24 SUPERSEDING COORDINATION AMENDMENT — Semiconductor shared foundation

**READ THIS SECTION BEFORE THE ORIGINAL EXECUTION WAVES BELOW.** It is a material dependency invalidator, not a new Robotics thesis.

Robotics itself still has **no concrete Fable receiver, PICKUP_ACK or START evidence**. Its operation remains `gmi-robotics-fable-ceo-e2e-20260923-chairman-001` in `WAITING_CAPACITY / needs_placement=true` until deliberate live delivery/placement to one eligible Fable session.

Meanwhile, Semiconductor B **has** been concretely assigned and STARTed under operation `gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001` on implementation PR #7870. At this amendment's current read:

- #7870 exact head: `45eb37bbf832e007e67ce2594674d6bfeeb3b880`, Draft/HOLD, not merged.
- Receiver: Claude Fable 5.1 CEO/orchestrator, Claude Desktop Code session `f6dd4b82-d319-4daf-99a4-ef4fe7dfd9ec`.
- The ONE shared `theme_graph.curation_assertion.v1` contract/module is implemented on #7870 and was independently reviewed twice after a rejecting first review.
- Current shared contract blobs:
  - `contracts/theme_graph/curation_assertion.v1.schema.json` → `ff3928f0c54aa164ef8283d9da45af67e6a0d971`
  - `engine/theme_graph/curation_assertion.py` → `23a25614782b8b1cb76ce7e3f292b64d35bfb4f6`
  - `contracts/theme_graph/evidence.v1.schema.json` → `8f909df8ee4c5858512035d2dfef21eac982a34d`
- The shared contract pins the frozen Robotics minimum payload and preserves the Robotics-required null semantics for `review.review_due_at` and `source.native_digest`.
- It adds one compatible strengthening: `published_at_grain_mismatch`. `published_at_grain=unknown` requires `published_at=null`; date and instant grains require matching values. The frozen Robotics unknown/null case passes. **Robotics accepts this strengthening; do not fork it.**
- `source_ref_for` is generic over `scope.canonical_theme_id`; Robotics consumes it unchanged.
- The optional Semiconductor `industrial_context` extension is additive; Robotics need not emit it.

### Shared work that Robotics must now CONSUME, not re-author

The original Robotics implementation plan remains the product/acceptance map, but its shared-infrastructure tasks are superseded as follows:

1. **Original Task 1 — shared curation assertion contract: DO_NOT_REDO.** Consume the accepted #7870 implementation or its merged successor. Robotics must not create `robotics_curation_assertion`, a second schema/module, or a divergent enum.
2. **Original Task 2 — evidence-store round-trip: SHARED / STILL GATED.** #7870 added the optional `curation_assertion` property to `evidence.v1`, but the `engine/theme_graph/store.py` `EVIDENCE_COLUMNS` append remains frozen under #7462 custody. Robotics does not open a second store patch. Consume the eventual accepted shared store change after #7462 reconciliation.
3. **Original Task 3 — K1 curation subtype: SHARED / IN FLIGHT on #7870.** Semiconductor T04 is the current shared implementation lane. Robotics consumes the accepted result; no Robotics-specific K1 subtype.
4. **Original Task 5 transport: coordinate around the ONE generic paid theme-research transport.** #7870's accepted plan uses `/api/themes/v1/research/query` and `/api/themes/v1/research/evidence` under the existing paid/private boundary. T09 is not accepted yet. Do not create a parallel `/api/themes/v1/robotics` route unless the shared owner explicitly rejects the generic route and a new architecture ruling authorizes a distinct surface.
5. **Original Task 6 client/mount: coordinate around the ONE generic `theme-research.js/css` client and generic hidden mounts.** Semiconductor T10 is the current shared implementation lane. The Theme Tracker part returned but required review/fix; the basket-detail mount was originally frozen under #7669. #7669 subsequently released the shell-only hunk to the shared carrier. Robotics must consume/extend the accepted generic client/mount, not create `robotics-theme-research.js/css` as a competing surface.
6. **Private publication remains UNRESOLVED.** #7870 has qualified candidate reuse of the incumbent private publication owner, but its R4 decision remains open and real live admission is still blocked. Robotics must follow the same eventual shared ruling. No second private store/bucket/table/publisher.

### Shared work that is NOT yet accepted

Do not convert in-flight Semiconductor work into Robotics truth merely because a lane returned:

- K1 subtype T04: in flight at the current checkpoint.
- F04 Semiconductor composer T07/T08: returned and under independent review, not yet a generic Robotics dossier.
- Generic theme-research client T10: returned; initial independent review required fixes; shared fix lane is in flight.
- Generic paid API T09: queued after composition.
- Full-fidelity private live admission: blocked on the R4 ruling.
- `store.py` optional evidence-column persistence: blocked on #7462 custody.
- Nothing on #7870 is merged or production-proven yet.

### Revised Fable CEO job for Robotics

Once Robotics is actually delivered to a Fable receiver, that Fable principal must **start by reconciling and consuming the latest accepted shared foundations from #7870 (or its merged/successor carrier)** before commissioning any child.

The Robotics-specific implementation focus becomes:

1. confirm the accepted shared assertion/K1/store/private/API/client contracts and exact revisions;
2. build only the Robotics-specific F04/dossier composition needed for Precision Motion + Perception, preserving the 32 RBV cases and the approved Robotics research semantics;
3. curate/qualify the Robotics real evidence cases (Orbbec/Twinny, Parker, Schaeffler/Hexagon, Zebra/PTC, Sanhua/HDS as applicable) through the accepted shared admission path;
4. extend the generic theme-research response/client with Robotics facets rather than forking the infrastructure;
5. preserve existing Robotics basket/ThemeState/ranking/entry/sizing outputs;
6. perform the Robotics-specific paid/private/browser/mirror acceptance end to end.

### Revised first-turn sequence

After concrete Robotics Fable delivery/ACK:

1. Re-pin current protected procedure.
2. Read this amendment + approved Robotics spec/plan + current #7870 checkpoint + current #7462/#7669 state.
3. Verify the exact Robotics operation still has no competing START/EFFECT_UNKNOWN writer.
4. **Do not commission original Task 1.**
5. Consume the accepted shared contract revision and explicitly record any incompatible Robotics requirement as a bounded shared-contract amendment request on the existing shared owner; do not fork.
6. Determine which of original Tasks 2/3/5/6 are already accepted upstream and mark those portions `DO_NOT_REDO`.
7. Create the fresh Robotics implementation carrier from then-current main only for the remaining Robotics-specific work.
8. Commission the first truly Robotics-specific unblocked child, normally the Robotics F04/dossier composition once its shared dependencies are accepted.
9. Keep real admission held until the one shared private-publication ruling is accepted and proven.
10. Complete the unchanged Robotics production/browser/non-regression completion law.

### Precedence

This amendment supersedes any older handoff instruction that tells Robotics Fable to independently author:
- `theme_graph.curation_assertion.v1`;
- the K1 curation subtype;
- a Robotics-only paid API route;
- a Robotics-only theme-research JS/CSS framework;
- a second private publication mechanism.

It does **not** supersede the approved Robotics domain research, the Precision Motion/Perception first vertical, the RBV acceptance cases, the no-ranking/trading law, or the real-path completion law.


## 0. Chairman directive and receiver semantics

The live Chairman directive is to place **Fable in CEO-level ownership of the remaining Robotics program end to end**, with Fable acting as the coordinating principal/orchestrator and using the existing subagent fabric as aggressively as is useful.

This repository artifact is a **durable commission packet, not receiver assignment by discovery**. No exact Fable provider session is bound at file creation time.

**PREFERRED_AVENUE: Fable**

**RECEIVER_BINDING_MODE: CAPACITY_SELECTABLE**

**PLACEMENT_STATE: WAITING_CAPACITY / needs_placement=true**

When the Chairman, canonical Capacity owner, or an already-authorized Sol direct-handoff path deliberately delivers this exact operation to one concrete eligible Fable session, **that live delivery is the receiver assignment for `gmi-robotics-fable-ceo-e2e-20260923-chairman-001`**. The concrete Fable receiver must then:

1. emit `PICKUP_ACK gmi-robotics-fable-ceo-e2e-20260923-chairman-001` with its actual receiver/session identity;
2. read the sources in `2 rather than replaying prior chat/tool history;
3. establish the required continuation/checkpoint path;
4. reconcile current source/custody/runtime gates;
5. emit a separate truthful `START gmi-robotics-fable-ceo-e2e-20260923-chairman-001` only when execution gates are clear;
6. then carry the parent mission through integration, review, real-path proof and closeout.

Before `START`, lawful `PRESTART_REBIND` to another eligible Fable session is allowed only while no modifying effect, `EFFECT_UNKNOWN`, conflicting active pickup or prior START exists. After START, binding is sticky until canonical reconciliation.

Do not ask the Chairman to “claim” this operation again after deliberate live delivery to a concrete Fable session.

## 1. Routing receipt — why this is a Fable principal mission

**ROUTE: Fable as principal CEO/orchestrator + existing Subagent/Capacity Fabric for bounded execution**

**WHY:** the remaining work spans Theme Graph evidence contracts, Evidence Foundation clock/identity semantics, MarketOntology/F04 composition, paid private API transport, shared Themes UI, incumbent source-writer collisions, privacy/publication architecture and final production/browser acceptance.

**WHY FABLE:** this is not simply eight coding tasks. It requires sustained principal continuity across multiple existing authorities, live collision adjudication with #7462/#7669, a consequential privacy/storage boundary because the current Theme Graph evidence parquet is Git-tracked publicly, and end-to-end acceptance where infrastructure/schema success must not be mistaken for a usable product. These are architecture-sensitive integration and continuity demands. Ordinary bounded workers are sufficient for most implementation labor **after Fable freezes each task boundary**, but no one bounded worker should own the cross-system decisions or final acceptance.

Fable is therefore **not the routine builder**. Fable personally owns:
- architecture/canonical-owner adjudication;
- collision/custody decisions;
- sequencing and dependency control;
- subagent decomposition/placement requests;
- consuming/reviewing worker returns;
- deciding when repair or stronger review is necessary;
- preserving one-carrier/effect law;
- the private-publication gate;
- integration across tasks;
- real-path/browser acceptance;
- the final completion ruling.

The subagent fabric owns the repeatable engineering/research/test work wherever a bounded packet can state an objective and proof.

At concrete placement, the runtime/Capacity owner must record the actual cognition/surface receipt required by current routing law. **Do not infer an included, Pro, API, metered, Claude, Chat, Codex, or other concrete surface from this handoff.** Provider/surface/model economics are separate from the organizational decision that Fable is the principal.

## 2. Canonical sources and precedence

Read the smallest sufficient frontier. Do not replay the original research crawl.

### A. Current protected procedure — highest procedural authority

Mastermind protected `master` at handoff creation:

`c917a75b0168a524a51b2ba0603a99118e93ef1f`

Compatible Skillpack: `mastermind.sol_skillpack.v1`, v1.0.1, bootstrap major 1.

Required files from that SAME commit:
- `docs/sol_skills/INDEX.md`
- `docs/sol_skills/ACTIVE_EXECUTION.md`
- `docs/sol_skills/WEB_CEO_DELEGATION.md`
- `docs/sol_skills/COMMISSION_WAVE.md`
- `docs/sol_skills/WORKER_AVENUE_ROUTING.md`
- `docs/AGENT_DIALOGUE_SESSION_CLOSE_LAW.md`
- `docs/EXECUTIVE_WORKER_ROUTING_CHAIRMAN_ADDENDUM.md`

Re-pin before effectful execution if protected `master` materially changes.

### B. Chairman-approved Robotics architecture and plan — do not redesign by default

Draft/HOLD PR #7773:
- branch: `sol/robotics-bom-research-20260923`
- exact head at handoff creation: `7efdd6cdc6401b5caf8f7fd34aa683b39e108686`
- PR remains draft/HOLD; **do not merge automatically**.

Approved written spec:
- `docs/superpowers/specs/2026-09-23-robotics-theme-evidence-vertical-design.md`
- blob: `d248fd1b4c9b48df8f5c95c3bdd742c2a8ef7007`

Implementation plan selected for execution:
- `docs/superpowers/plans/2026-09-23-robotics-theme-evidence-vertical-implementation.md`
- blob at plan self-review: `d0a04e96c874395ae51cf44281039c99527dcd86`
- 8 executable tasks
- all RBV-01 … RBV-32 acceptance cases mapped
- no placeholder work items
- plan explicitly separates contract/store/K1/F04/API/UI/privacy/real-path proof.

Research foundation:
- `research/robotics/ROBOTICS_RESEARCH_FOUNDATION_2026-09-23.md`
- `research/robotics/ROBOTICS_DESIGN_EVIDENCE_AND_ACCEPTANCE_2026-09-23.md`

Cumulative pre-Fable checkpoint:
- `agentos/handoffs/GMI-ROBOTICS-RESEARCH-2026-09-23.md`

These artifacts are `DO_NOT_REDO` unless a material invalidator changes the selected architecture or a current owner contract.

### C. Current Macro owner state at handoff creation

Macro current `main`:

`c159115451e5dd5f33a2565dac2c7e9221b03ee1`

GMI Theme Graph workstream:
- `agentos/workstreams/WS-GMI-THEME-GRAPH.md`
- current blob `cd2067041dc441bf5bc44302ee8c458bdfd42b45`
- GMI remains one canonical semantic/evidence spine.
- Standalone GMI W4/W5/W6 revival remains rejected; do not create a rival relationship/propagation/product plane.
- F04 remains downstream product composition; relationship/propagation owners remain distinct.

STSI architecture:
- `docs/superpowers/specs/2026-09-20-sector-theme-subtheme-intelligence-system-design.md`
- current blob `d3bb8a03d4e571a058a499bd35a1a94c7c8e8971`
- preserve owner federation and the existing Theme Tracker/detail hierarchy.

### D. Live collision frontier at handoff creation

Refresh these exact carriers before touching their paths. The numbers below are navigation, not a promise they remain unchanged.

- PR #7462 — head `31706d7322af55696dc7b2e746ec511b08bd51d7`
  - OPEN / draft
  - directly overlaps `engine/theme_graph/store.py`
  - Task 2 may not take that path until source-writer/custody is reconciled.

- PR #7669 — head `2c28d950aa9448fc878bb64d92b228a8f1952bde`
  - OPEN / non-draft
  - includes `templates/basket_detail.html.j2`
  - Task 6 waits for the accepted current template/custody.

- PR #7664 — head `be14ee173f720baf189b303eae841aa1f8969901`
  - OPEN / non-draft
  - owns `scripts/build_state_of_themes.py`
  - the approved plan intentionally avoids that path by paid client-side hydration.

- PR #7455 — head `fdd731f18a7634c57cdc83fc80cbe13811ec745e`
  - OPEN / draft
  - no planned write-path overlap at handoff creation.

- PR #7633 — head `f7f1001acb6322da781632ac5fd67e0076ddb4c2`
  - OPEN / non-draft
  - no planned write-path overlap at handoff creation.

Main moved after the plan was written. Fable must build from **fresh current main**, not by turning the 11+-commit-behind #7773 research branch into the product implementation carrier.

## 3. Outcome Fable owns

Deliver the first **production-proven granular Robotics theme vertical** inside the existing Mastermind Themes workflow.

The investor must be able to:

`Theme Tracker → Robotics → Precision Motion / Perception → company/business/product assertion → source + clocks + limitations → existing stock/theme workflow`

and truthfully distinguish:
- catalog capability;
- documented product inclusion;
- announced development/supply arrangement;
- future deployment target;
- reported deployment;
- ownership event;
- reported financial observation;
- reported operating observation.

The machine must preserve:
- source scope and locator;
- product/configuration scope;
- quantity basis;
- business-valid versus publication/observation/review clocks;
- corrections/supersession;
- company/security identity uncertainty;
- rights/privacy state;
- explicit limitations;
- unchanged decision authority.

### Mission completion law

The mission is **not complete** when:
- the schema exists;
- an evidence column round-trips;
- K1 accepts a fixture;
- the F04 composer returns fixture JSON;
- the API returns 200;
- page shells render;
- unit tests pass;
- CI is green;
- a PR merges.

The first Robotics vertical is complete only when:
1. at least one accepted real documented-inclusion assertion and one accepted real catalog-capability assertion traverse the lawful native/private path;
2. the existing Theme Tracker and existing `basket/robotics_automation.html` show the correct paid research result;
3. predicate, configuration, quantity basis, source/observation/business clocks and limitations are visible and correct;
4. anonymous/free/public mirrors cannot recover full-fidelity current research;
5. the incumbent basket/theme/member recommendation/ranking/entry/sizing outputs remain unchanged for the frozen comparison set;
6. exact-head tests and independent review pass;
7. the deployed browser path is proven at desktop/mobile, EN/ZH and dark/light where specified;
8. final evidence is persisted under existing owners and the parent mission is explicitly closed.

## 4. Architectural laws Fable must preserve

1. **No second graph.** Extend/consume the incumbent Theme Graph owner only as accepted.
2. **No global product master in v1.** Products/configurations/business units remain source-scoped descriptions until a proper existing owner supports stronger identity.
3. **No automatic SUPPLIES/BOTTLENECK promotion from research membership/capability.** Relationship edges remain governed by their current owners.
4. **No Evidence Foundation warehouse.** K1 stays a pointer/reference contract over owner-native evidence.
5. **No new identity plane.** Company/security/listing joins use existing GMI/Data-OS identity resolution only.
6. **No new correction plane.** Corrections append/supersede through the accepted owner.
7. **No new publisher/store/scheduler merely for Robotics.**
8. **No public full-fidelity paid payload.**
9. **No ranking/trade authority.** Every Robotics research authority bit stays false.
10. **No fake completeness.** Missing publication date, unresolved identity, undisclosed revenue, rights restriction, stale review and unavailable private binding remain explicit null/degraded states.
11. **No universal robot BOM.** Quantities/costs/dependencies bind to the evidenced product/configuration.
12. **No double counting.** Parent integrated assembly and contained children cannot both count in one cost boundary.
13. **No statement-mode collapse.** A target is not deployment; capability is not inclusion; announcement is not completed ownership.
14. **No source-date laundering.** Observation/review/curation time never fills an unknown upstream publication date.
15. **No evidence independence laundering.** Syndicated/copied statements remain shared-source evidence.
16. **No redesign of the approved user journey unless a material current-source contradiction forces return to the principal decision.**

## 5. Critical privacy/storage gate

At handoff creation, `data/theme_graph/evidence.parquet` is Git-tracked in the public Macro repository.

Therefore:
- code/contracts may add an optional assertion column/codec;
- tests may use fixtures/temp parquets;
- **real full-fidelity paid Robotics assertion bodies may NOT be committed to the public repository-backed evidence parquet**.

The approved plan deliberately treats this as a real implementation gate.

Fable personally owns this ruling:
1. identify and prove an **existing approved private owner/publication binding** that can carry the accepted current assertion body while preserving the incumbent evidence identity/reader/publication semantics; or
2. if no lawful incumbent binding exists, hold real live admission and return to the architecture owner with exact evidence.

Do **not** solve the gate by creating:
- `data/robotics_research/`;
- a second R2 bucket;
- a new database/table;
- a new evidence log;
- a second “latest” file;
- another scheduler/publisher;
- a public-row exception.

Infrastructure work is warranted only if the current owner explicitly requires a compatible extension and that extension unlocks the named user capability.

## 6. Fable operating model — orchestrate, do not become the default coder

### Principal-only responsibilities — Fable keeps these

Fable should personally retain:
- protected-source re-pin and active-frame recovery;
- current-main and collision reconciliation;
- deciding the exact implementation carrier;
- Task 2 #7462 custody ruling;
- Task 6 #7669 template ruling;
- K1/Theme Graph/F04 owner-boundary adjudication;
- private-publication architecture and admission decision;
- dependency sequencing/fanout;
- consumption of worker returns;
- architecture-sensitive repair decisions;
- selection of independent reviewers;
- real-path/deployment acceptance;
- final parent closeout.

### Fabric responsibilities — delegate these aggressively

Use the current Capacity/Subagent Fabric to the fullest **within lawful availability, budget, custody and review capacity**. Delegate independently testable outcomes, not command-by-command labor.

Preferred decomposition:

#### Wave A — native assertion contract
**Task 1** from the implementation plan.

Preferred bounded avenue: **Codex/Terra** (Luna only if the schema/TDD work is demonstrably mechanical).

Deliverable: contract + codec + hostile tests + exact commit.

Independent review: Terra/Opus/Auditor Sol; not the builder.

Fable acceptance question: does the representation preserve source/configuration/time/correction distinctions without becoming a product master?

#### Wave B — two branches after Task 1 acceptance

**Task 2 — Theme Graph store round-trip**
- preferred avenue: Codex/Terra;
- **HELD on #7462 path custody** until Fable reconciles it;
- do not touch `engine/theme_graph/store.py` on a conflicting carrier.

**Task 3 — Evidence Foundation subtype**
- preferred avenue: Terra/Sonnet/Codex;
- may proceed while Task 2 is held if Task 1 interface is frozen and paths remain disjoint;
- no generic K1 redesign unless a discriminating red proves it necessary.

Independent review should be different from each builder.

#### Wave C — F04 composer
**Task 4**

Preferred avenue: **Terra or Opus/Codex** depending on actual complexity.

This is reasoning-heavy but bounded. Fable supplies the accepted Task1–3 interfaces and the hostile cases. Worker implements deterministic composition only.

Fable acceptance focuses on:
- source-only versus resolved identity;
- statement-mode distinction;
- quantity/configuration safety;
- arithmetic/basis refusal;
- deterministic ordering;
- zero trade/ranking keys.

#### Wave D — paid transport
**Task 5**

Preferred avenue: **Luna/Terra/Codex**.

Use the established paid FastAPI pattern. Keep private headers/entitlement ordering exact. No new auth or caching architecture.

Independent review: a different worker focusing on auth/privacy failure cases.

#### Wave E — existing-page UI
**Task 6**

Preferred avenue: **Cursor/Terra/Sonnet** with browser/visual capability.

**HELD on #7669 template custody** until Fable reconciles the accepted current template.

The worker receives the accepted API contract and must not calculate owner intelligence in browser JS.

Independent review: accessibility/browser reviewer distinct from UI builder.

#### Wave F — non-regression / privacy adversarial gate
**Task 7**

Preferred avenue: **Opus/Terra/Auditor Sol**, independent of the primary builders.

This reviewer should attempt to break:
- public mirror isolation;
- entitlement-before-byte-open;
- legacy decision invariance;
- typed nulls;
- statement-mode handling;
- source-clock distinctions.

Fable consumes and adjudicates every substantive finding before live admission.

#### Wave G — real-path acceptance
**Task 8**

Fable is the principal.

Use bounded helpers for:
- real assertion qualification/retention;
- browser proof;
- EN/ZH + light/dark/mobile evidence;
- public-mirror probes;
- deployed-byte verification;
- final exact-head independent review.

Fable alone decides whether the parent mission is `PROVEN_OUTCOME` or remains nonterminal.

## 7. Subagent commission law

For each bounded worker:
- mint one stable child operation identity;
- use one logical modifying carrier until reconciled;
- state exact source revision and allowed paths;
- define non-goals and authority ceiling;
- require PICKUP_ACK separately from START;
- establish source-continuity checkpoint before long CI/review/context exposure when the child has STARTed modifying work;
- demand compact return evidence: exact head, changed files, focused/full tests, CI, review findings, unresolved effects and next dependency;
- do not paste full parent transcripts;
- do not allow a child to merge/release unless separately authorized;
- do not use the same builder as its independent reviewer when practical;
- no blind retry/failover of a STARTed or EFFECT_UNKNOWN operation;
- two equivalent no-delta repair cycles trigger a changed hypothesis, lane or owner.

Fable should keep multiple children active only when paths/authority are genuinely disjoint and Fable has review capacity to consume their returns.

## 8. First-turn Fable sequence

After concrete Fable delivery/ACK:

1. Re-pin current protected Mastermind procedure.
2. Read only:
   - this handoff;
   - #7773 approved spec;
   - #7773 implementation plan;
   - current `WS-GMI-THEME-GRAPH.md`;
   - current Macro `main`;
   - current #7462/#7669 collision state.
3. Verify no existing STARTed Robotics implementation child or EFFECT_UNKNOWN writer exists.
4. Create/recover **one fresh implementation carrier from then-current Macro main**, Draft/HOLD.
5. Persist a source-continuity checkpoint before large fanout.
6. Commission Wave A Task 1 to the least-scarce capable worker.
7. In parallel, Fable resolves:
   - #7462 Task 2 custody;
   - #7669 Task 6 custody;
   - the Task 7 private-publication owner question.
8. When Task 1 returns, perform principal acceptance, then start eligible Wave B children.
9. Continue through the dependency graph without waiting on a blocked lane when an independent one is ready.
10. Never stop merely because one plan task or PR is complete while the parent capability remains unfinished.

## 9. Failure and blocker behavior

A blocker freezes its lane first.

Examples:
- #7462 still owns store path → hold Task 2; continue Task 3 or privacy-owner investigation.
- #7669 still owns template → hold Task 6; continue Task 5/non-template work.
- private publication owner absent → hold real admission; complete code/contract/private-gate evidence that is safely independent.
- one worker quota unavailable → Capacity owner selects another eligible route before START; do not make Chairman route routine accounts.
- a STARTed worker becomes ambiguous → reconcile same carrier; no replacement child until effect state is known.
- missing credential/admin ceremony → exhaust independent work first, then surface the exact HUMAN_AUTH step.

Do not send routine implementation choices back to the Chairman.

Return to the Chairman only for:
- an exact credential/admin/physical ceremony;
- a genuinely new authority/scope choice;
- an architectural contradiction where all lawful current owners refuse the approved design;
- a material product tradeoff not settled by the approved spec.

## 10. Acceptance checklist Fable must enforce

The implementation plan is authoritative for detailed TDD steps. The following are principal acceptance invariants:

### Native/contract
- [ ] `theme_graph.curation_assertion.v1` closed schema exists.
- [ ] deterministic revision changes with locator/source/retention/correction changes.
- [ ] invalid/non-finite/basis-free quantity refuses.
- [ ] legacy evidence rows still validate.
- [ ] optional assertion survives actual owner round-trip without new evidence key/path/writer.

### K1
- [ ] explicit curation subtype binding exists.
- [ ] source publication / observation / retention / review / business-valid clocks remain distinct.
- [ ] unknown value uses existing explicit unknown state, not a fake grain/date.
- [ ] no company/security cross-type bridge is invented.
- [ ] all authority bits false.

### F04
- [ ] catalog capability ≠ supply contract.
- [ ] target ≠ deployment.
- [ ] ownership announcement ≠ completed ownership.
- [ ] unresolved identity gets no stock enrichment.
- [ ] component quantity stays configuration-scoped.
- [ ] parent/child cost double counting refuses.
- [ ] backlog/sales is not lead time.
- [ ] deterministic output and no trade/rank/alpha keys.

### API/privacy
- [ ] entitlement denial occurs before private owner bytes are opened.
- [ ] all success/error responses are private/no-store.
- [ ] API mounted fail-loudly.
- [ ] no static/public full-fidelity fallback exists.

### UI
- [ ] existing Theme Tracker shows Robotics research summary.
- [ ] existing Robotics detail shows Motion/Perception research module.
- [ ] no new dashboard or competing detail route.
- [ ] relation type is textual, not color-only.
- [ ] accessible table is complete when visual map is unavailable.
- [ ] EN/ZH and light/dark/mobile preserve exact quantities/status/sources.
- [ ] incumbent timing/holdings sections are unchanged.

### Decision non-regression
- [ ] basket members/weights unchanged.
- [ ] Theme Tracker lane/stage/recommendation unchanged.
- [ ] member ordering/Prophet presence/entry/sizing unchanged.
- [ ] research coverage never counts as an extra legacy signal confirmation.

### Real production path
- [ ] Orbbec/Twinny accepted as `DOCUMENTED_PRODUCT_INCLUSION`, quantity 2 cameras per robot for the described configuration only.
- [ ] Parker K-Series accepted as `PRODUCT_CAPABILITY`, publication date unknown/observed date explicit, no named humanoid customer invented.
- [ ] paid real API returns owner-qualified data.
- [ ] anonymous/free cannot retrieve it.
- [ ] browser proof on deployed site.
- [ ] exact-head independent review after final repair.
- [ ] release identity and production bytes verified.

## 11. DO NOT REDO

Unless materially invalidated:
- do not repeat the 46-source broad robotics research sweep;
- do not repeat the current Themes architecture archaeology;
- do not rewrite the approved spec;
- do not rewrite the 8-task implementation plan;
- do not re-litigate standalone GMI W4/W5/W6;
- do not invent a global product identity system;
- do not turn THS/Finviz vendor structure into house truth;
- do not infer supplier relationships from theme membership;
- do not recalculate ThemeState/ranking/entry in the Robotics client;
- do not treat CI/merge as product acceptance;
- do not treat the #7773 research branch as the implementation base.

## 12. Durable continuity and return contract

Fable owns one cumulative durable checkpoint under existing Agent OS/repository owners.

Checkpoint after:
- implementation carrier creation;
- each material accepted child;
- architecture/privacy ruling;
- major repair;
- before long CI/review/deployment;
- before any context/session rotation.

Preserve only:
- parent mission;
- Fable receiver/runtime identity once assigned;
- protected procedure SHA;
- implementation repo/branch/PR/base/head;
- accepted task commits and DO_NOT_REDO;
- active children + exact carriers;
- EFFECT_UNKNOWN if any;
- #7462/#7669 collision state;
- private-publication gate state;
- test/review/CI/deploy receipts;
- exact next critical action.

A fresh Fable session does not inherit writer custody automatically. Reconcile RuntimeBinding/source writer before continuing any STARTed modifying operation.

### Parent return to Sol/Chairman

Return only a compact CEO packet containing:
- exact implementation PR / final head;
- protected source pin used for final acceptance;
- completed task matrix;
- child/reviewer summary with exact heads;
- CI/security/adversarial review receipts;
- private-publication proof;
- browser/deployment proof;
- decision-non-regression proof;
- unresolved items, if any;
- explicit final classification;
- explicit `MISSION_COMPLETE: true|false`;
- exact next action if incomplete.

Do not return worker transcripts or raw logs by default.

## 13. Stop condition

Fable may stop the end-to-end operation only at one of the current ACTIVE_EXECUTION finalization states with exact evidence.

Target state:

`FINALIZATION_CLASSIFICATION: PROVEN_OUTCOME`
`MISSION_COMPLETE: true`

Anything short of the completion law in `3 stays nonterminal.

If a worker-facing reciprocal dialogue is terminal, Fable must send an explicit terminal STOP/ACCEPTED edge and disarm/close its temporary watcher path per current dialogue law. A child result is not terminal merely because the worker posted `RESULT`.

---

## Compact launch block for the concrete Fable receiver

When this packet is deliberately delivered to one eligible Fable session, the Chairman/placement edge may be accompanied by:

> You are the principal CEO/orchestrator for `gmi-robotics-fable-ceo-e2e-20260923-chairman-001`. This live delivery is your receiver assignment. PICKUP_ACK it, re-pin current procedure, reconcile current main/#7462/#7669, create one fresh implementation carrier, and drive the approved #7773 specification and implementation plan end to end. Delegate routine engineering/research/test work through the existing subagent/capacity fabric; retain architecture, integration, collision/privacy rulings and final acceptance personally. Do not ask the Chairman to route routine workers. Do not stop at infrastructure, CI, merge or a partial page; finish only on the declared production/browser/private-path completion law or an exact terminal gate.
