# Market Ontology R1 — post-MO-J1 parity/workflow research

Research identity: `marketontology-parity-workflow-research-20260926-sol-r1`
Parent: `macro#6819`
Revision: `20260926-sol-r1`
Status: decision-ready research return; `accepted:false`
Sources last accessed: 2026-09-26

## Executive decision

After MO-J1, the material remaining parity gaps are continuity gaps across existing Mastermind owners, not missing ontology, portfolio-risk, valuation, Thesis, monitoring, or ranking systems.

Keep MO-J1 first. After it is accepted, the two strongest implementation candidates are:

1. **Portfolio transmission-change continuity** — extend the existing `portfolio_changes` retention spine so a user can see that a held name entered/left an armed transmission chain since the prior review.
2. **Valuation-event → Thesis amendment continuity** — project existing F07 source-grounded event/assumption deltas into K1-compatible evidence pointers and compose them into the existing propose-only Thesis amendment workflow. Human publication authority remains unchanged.

Issuer-event → Company Intelligence → Thesis → monitor → later reopen is proof-first after MO-J1, not a new feature family.

## Source pins

- Protected Mastermind: `f3bd2ca266fb3752ea1cd561758a5189b28aae2d`; Skillpack `mastermind.sol_skillpack.v1` v1.0.1, bootstrap major 1 compatible.
- Macro source observed: `810cdf78428f79b6e60850d2787fafc429ba54e0`.
- Terminal source observed: `61d55a7e1d12a9104f90d17bfa2cd8b16982ac6f`.
- Active carriers at report creation:
  - Terminal #746 head `6859bc01a9292848b24ba6b677f23a4cc4fcb9e5`, current-base; hosted E2E CI running.
  - Macro #7781 head `30fce96fe4765488d4e828c78f2ef35df70e85d6`, current-main; hosted CI-pack matrix running.

Those carrier tests are parent-program evidence, not R1 tests.

## Competitor workflow observed

Current public Market Ontology pages present continuity across development/event → affected assets → assumptions/scenarios → holdings → saved research/decision → monitoring/change → later review. That supports a product-shape conclusion only; it does not independently validate numeric impact, confidence, priced, probability, or valuation outputs.

The parity target is therefore the customer job:

`event/development → affected asset → evidence → assumption/research consequence → retained object → condition/change → reopen same work`.

## False-gap traps resolved

### Portfolio Risk / Scenario Lab is not a missing plane

Mastermind already has canonical authenticated `portfolio_positions`, Terminal portfolio UX, Macro Portfolio/Watchlist risk, factor exposure/risk contribution/concentration, scenario shocks, portfolio briefs, and Scenario Lab. `templates/watchlist_risk.js` already renders transmission-chain exposure for held names and links to the Cascade Monitor.

**Ruling:** no second portfolio-risk/scenario engine. The residual is continuity/proof across existing owners.

### Opportunity Map is not permission for a new calibrated ranker

Mastermind already has `mastermind.research_priority_ordering.v1` with `authority_ceiling=research_priority_only`.

**Ruling:** do not copy vendor direction/confidence/expected-impact/priced fields into MarketOntology merely for visual parity. Promotion remains with the accepted Alpha/Eval chain.

### Valuation/event logic already exists

Macro already owns `valuation_scenario.v1`, `valuation_scenario_controls.v1`, `assumption_change_proposal.v1`, `assumption_change_scenario.v1`, event-class → valuation-input mapping, abstention, rights, and double-count controls. The current ticker assumption UI states that interactive user adjustments are not saved or sent anywhere.

Terminal already owns immutable Thesis versions, evidence-backed `thesis_amendment_proposals`, human-only publication, and condition monitoring. The Thesis content schema intentionally has no arbitrary valuation/model fields.

**Ruling:** no second valuation store and no hidden model database inside Thesis.

## Scenario S1 — macro/transmission

Current state: F04 WTI Live Path is shipped; TXI owns transmission; current MO-J1A packet already specifies Data OS alias resolution + exact round trip → bounded affected-company continuation → Terminal Company Intelligence. Company Intelligence is generation-pinned and context-only. Thesis/version/change/monitor primitives exist.

Classification: **DISCONNECTED / BUILT_NOT_PROVEN** pending MO-J1.

Missing contract/proof: normal signed-in joined journey and fail-closed negative states. No post-MO-J1 build should pre-empt this proof.

## Scenario S2 — issuer event

Current state: Company Intelligence already provides event/evidence lineage. F07 already produces typed source-grounded event→assumption proposal/scenario or abstention. Terminal Thesis versions are immutable. `thesis_amendment_proposals` already supports propose-only assistant write-back using K1 evidence pointers; acceptance does not publish a Thesis revision.

Classification: **DISCONNECTED** between F07 proposal output and the Terminal Thesis amendment path.

Admission mapping:
- `MO-PAID-022` Valuation Finder / event-to-assumption;
- `MO-PAID-046` Thesis Builder;
- `MO-PAID-054` propose-only Workspace Chat amendment binding;
- `MO-PAID-047` existing monitor continuation after human publication.

Smallest later packet:
1. Current-owner F07 preflight + closed read projection containing proposal/abstention identity, source/model revision, clocks, rights/authority, and K1-compatible evidence pointers.
2. Terminal composition into an existing amendment proposal against the current Thesis version.
3. Human accepts into editor and publishes through ordinary revise.
4. Negative proof for abstention, stale/corrected source, stale Thesis version, wrong company/user, malformed pointer, rights block.

Forbidden: copied source payload, confidence/probability/rank/size/target/score, automatic Thesis mutation, new DB table, second valuation store.

Falsifier: if post-MO-J1 source already exposes F07 through Company Intelligence/K1 and binds it into evidence refs, reduce to proof/UX only. If K1 cannot represent source/correction identity, stop at the K1 owner.

## Scenario S3 — portfolio / decision review

Current state:
- canonical signed-in positions exist;
- `portfolio_ctx.v2` already carries per-ticker armed transmission-chain membership;
- `templates/watchlist_risk.js` already renders the Transmission lane and portfolio-level chain continuation;
- `portfolio_brief.v2` already composes holdings over nightly context;
- `/api/portfolio/changes` already computes a private “since last visit” diff from a client-held state digest and stores no per-user server snapshot.

Concrete gap: `portfolio_state_digest.v1` tracks stage, entry read, sector class, earnings window, and regime, but not chain membership. A held name can be downstream of an armed chain now while the retained change spine cannot say that it entered/left the chain since last visit.

Classification: **PARTIAL / DISCONNECTED**.

Admission mapping: existing F04 private Portfolio/Watchlist overlay + `MO-PAID-085` portfolio digest/change-delivery continuation.

Smallest later packet:
- additive digest schema version;
- bounded display-only chain membership already present in `portfolio_ctx.v2`;
- neutral entered/left/state-changed chain diffs;
- preserve TWO-ORGANISMS privacy boundary: no shares, cost basis, weights, account ids, or user-activity timestamps; never log the digest;
- missing/stale chain state must not become false “cleared” state;
- reuse existing brief/digest consumers; no new alert engine.

Immediate preflight must re-census the ordinary consumer because the current Macro endpoint/digest owner is clear while a Terminal consumer was not found in current source search.

Falsifier: if current post-MO-J1 source already retains chain membership under another canonical digest, skip. If privacy rejects bounded chain ids in the client-held digest, keep live risk continuation and make this proof/UX only.

## Beyond parity

Mastermind can be better through:
- source/revision/correction continuity across transitions;
- evidence-backed suggestions without silent Thesis mutation;
- retained “what changed” explanations over canonical user context;
- fail-closed Data OS identity routing;
- explicit observed/inferred/unsupported distinctions;
- no promotion of marketing-style numeric confidence into decision authority without validation.

## Recommended post-MO-J1 sequence

1. Portfolio transmission-change continuity.
2. F07 valuation-event → Thesis amendment continuity.
3. Issuer-event → Thesis → monitor real-user proof/repair.

Do not create a new ontology graph, portfolio-risk engine, opportunity ranker, valuation store, Thesis store, evidence store, scheduler, or monitoring engine for these jobs.

## Inaccessible / unproven evidence

- No authenticated Market Ontology account was used; public pages prove product shape/claims, not paid persistence/backend behavior.
- No proprietary formulas/datasets were inspected or inferred.
- No live signed-in Mastermind Thesis proof or entitled F04 proof was run as R1.
- #746/#7781 hosted CI was still running at report creation.

## R1 test statement

R1 is read-only research/source analysis. **No product tests were executed as R1 acceptance tests.** Separate parent-program verification is recorded on #746 and #7781.

`accepted:false`
