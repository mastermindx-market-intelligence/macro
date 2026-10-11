# PB-G architecture freeze

**Operation:** `PB-G-POLICY-BEHAVIOR-INTEGRATION-20261007`  
**Disposition:** research/architecture freeze; proposed builds remain **UNLAUNCHED**.  
**Source census:** Macro [`c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05`](https://github.com/mastermindx-market-intelligence/macro/commit/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05).  
**Procedure:** protected Mastermind [`ee120e80f5d5e0344c453dd7cbf4108b9c429b38`](https://github.com/mastermindx-market-intelligence/Mastermind/blob/ee120e80f5d5e0344c453dd7cbf4108b9c429b38/docs/sol_skills/INDEX.md), `mastermind.sol_skillpack.v1` / `1.0.1` / bootstrap major 1.

This document freezes the architecture proposed by the PB-G integration return. It does not authorize implementation, production collection, source enrollment, deployment, prospective enrollment or any increase in decision authority. Existing implementation, source custody and release owners remain unchanged. Companion `PB_G_NO_DUPLICATION_MAP.md` records exact owner paths, functions, evidence limits and occupied dependency carriers.

## 1. User capability and architectural decision

Mastermind should let a user inspect what a policy actor said, what legal or financial instrument actually changed, what was executed, which constraints and market conditions were observed, and which interpretations remain uncertain. The same qualified facts and limitations must reach machine consumers. A readable explanation must not silently acquire ranking, sizing, entry, gating or live-alert authority.

The proposed architecture extends existing owners along this chain:

**Observed source facts → owner-typed events and financial facts → constraints and measured transmission → context-only synthesis → existing consumer outputs.**

These are stages of a composition, not five new services or stores. Policy Watch/Intent retains policy items and lifecycle. Company Intelligence retains issuer/event evidence. Capital Structure retains financing-event and document-term evidence. GovRev retains government award/support facts and reviewed recipient identity. CCW/RIC retain their measured market context. Data OS retains identity and temporal rules. GMI and MarketOntology retain their existing graph/projection roles. No PB-G policy operating system, event bus, source database, graph, evaluator or clock is created.

### The admitted composition

| Stage | Existing route | What may be emitted | What must remain distinct |
|---|---|---|---|
| Source observation | Official Fed cache/statement owner; White House/Treasury sentinel; Federal Register; qbus; SEC and government-revenue source owners | Original/source-family reference, owner record ID, source bytes or permitted digest/reference, actual publication/acquisition clocks, coverage and rights state | Publisher claim versus independently established fact; new document versus successful no-new check; original versus syndicated echo |
| Typed event/fact | Policy lifecycle; Company Intelligence event/workspace; Capital Structure event spine; GovRev award/action/outlay contracts | Legal or instrument state, typed financial amount, issuer/party identity, correction/supersession, event/effective/observation clocks | Proposal, authorization, effective law, execution, enforcement; ceiling, commitment, financing proceeds, revenue, cash paid |
| Constraint/transmission | Existing policy-item projection plus RIC, Treasury Watch, CCW and owner-backed company facts | Observed feasible instrument restrictions, documented conditions, measured price/rate/credit movement, explicit causal alternatives | Actor objective versus constraint; market repricing versus causal shock; association versus induced effect |
| Synthesis | `engine/policy_intent_desk.py::gather_state/synthesize` and established dossier composition | Source-qualified explanation, alternative hypotheses, falsifier, bounded research disposition | Deterministic fact versus interpretation; historical reconstruction versus prospective evidence; direction versus validated decision authority |
| Consumer | Policy Watch, policy JSON, Intel Hub display facet, RIC context, Company Dossier and independently verified Terminal route | The same retained facts, clock qualification and typed limitations | Rendering versus source admission; internal receipt versus rights-safe display; source implementation versus live acceptance |

The current source already supplies much of this structure: [Policy Intent/lifecycle](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/policy_intent_desk.py), [Company event workspace](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/company_intelligence/event_workspace.py), [Capital Structure event spine](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/capital_structure/event_spine.py), [GovRev amount semantics](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/government_revenue/amount_semantics.py). The cross-owner adapters above are proposed; this table does not claim they are already wired.

## 2. PBG-01: retain evidence clocks through the existing Policy Intent route

### Source defect established by this census

At the frozen Macro commit, [`data/policy/intel.json`](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/data/policy/intel.json) is dated **2026-07-13**. [`site/policy_intent.json`](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/site/policy_intent.json) carries **2026-09-30T12:10:29.919889+00:00** as `generated_at` and **2026-09-30** as `state_asof`.

`gather_state()` deliberately uses the run date as `as_of` and separately supplies `intel_asof`. `synthesize()` retains the run/synthesis clocks but drops `intel_asof`. `_append_ledger()` also omits the source vintage and identity from new thesis rows. `run()` determines reuse from the prior `generated_at`, so a model refresh cadence does not establish source currentness. These are direct observations of the [pinned source](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/policy_intent_desk.py), not inferred live runtime behavior.

**Policy Watch already has separate clock labels.** Its [builder](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/scripts/build_policy_watch.py) derives analysis labels from desk `state_asof` and background verification labels from intel `as_of`. Preserve those. The first change is retained machine provenance and qualified consumption, not a replacement page.

### Proposed minimum contract

Keep `generated_at` as synthesis time and `state_asof` as the existing analysis/run date. Preserve `intel_asof` and the exact source identities in the brief, consumer projection and **new rows of the existing thesis ledger**. Represent the following facts through the incumbent owner's compatible extension/version path; this list specifies required semantics, not a new canonical schema:

- owner record ID and immutable source/artifact revision or content binding;
- source family, jurisdiction and declared coverage scope;
- source publication/availability, actual first acquisition/observation, and effective/event dates where independently supplied;
- last successful source check and its coverage/result, including successful no-new, partial, unavailable and failed checks;
- synthesis and serving clocks plus retained input cutoffs;
- rights, correction/supersession and explicit absence reasons;
- a deterministic qualification of what may be described as current evidence versus dated background.

**Source freshness is not oldest-event age.** An old enacted instrument can remain operative after a successful current check. Conversely, a new model timestamp cannot refresh the source set, and a recent fetch timestamp cannot establish coverage without a successful source-family receipt. The existing [`policy_watch_current.py::_headlines_from_blob`](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/policy_watch_current.py) already distinguishes acquisition age, feed health, `no_new`, stale input, outage and invalid newest receipts. Reuse those distinctions; use each source owner's budget or an explicitly admitted budget, not an invented universal TTL.

Clock ownership stays with [Data OS `TemporalProfile`, `known_at`, `as_of_filter`](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/lib/dataos/temporal.py). A generic DERIVED latest object is not automatically PIT-readable. INTELLIGENCE replay uses its serving clock and input-cutoff/expiry obligations. Public-source reconstruction and actual system possession remain separately named. Historical ledger rows must not be backfilled with fictional first-known/source-qualified status.

### Failure and correction behavior

Malformed, future, unavailable, rights-blocked or failed-check inputs must not produce affirmative source-current status. Preserve readable historical background and independent qualified sections when appropriate. Do not replace uncertainty with zero or an empty complete result. A model may explain a typed limitation, but it cannot override it.

Corrections enter through the relevant source/event owner, preserve the original observation and invalidate affected dependent conclusions. Current synthesis can be regenerated from corrected inputs; an earlier first-known thesis remains tied to the evidence it actually used. No new retry, source-health or correction store is required.

## 3. PBG-02: behavioral evidence inside Policy Watch

The proposed behavioral view attaches source-backed observations to existing policy item IDs. Its useful fields distinguish public statement, legal/instrument action, actual implementation, observed constraint, measured transmission, supported beneficiary/burden, competing explanation and next falsifier. The model can summarize these fields but cannot supply missing legal state, source precision or causal identification.

The existing policy owner already has `lifecycle_events()`, `ingest_lifecycle()`, `fold_lifecycle()` and `lifecycle_view()`, with append-only events, item-level store precedence, operator-signed seed/substrate fallback and correction links. **Its current ingestion is not an already-proven automatic White House/FR admission path.** A later build must qualify a minimal adapter from those source owners rather than treating model-activated White House alerts as the complete factual source denominator. [Policy lifecycle owner](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/policy_intent_desk.py); [White House sole-writer builder](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/scripts/build_whitehouse.py); [Federal Register collector](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/collectors/federal_register.py).

Keep the following distinctions visible:

- a statement is not a legal decision; a proposal is not an in-force instrument;
- a facility request is not approved access, and access is not borrowing;
- an announced commitment is not execution or cash;
- an institution's available instruments are not proof of another actor controlling its objective;
- rate or FX movement is measured transmission context, not proof of policy causation;
- a plausible beneficiary is a hypothesis unless the specific economic right/exposure is evidenced.

RIC remains deterministic measured context. Do not turn its [board/stance owner](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/rates_inflation_command.py) into an intent classifier. The [Intel Hub `_dirs`/`_VOTING_DESKS` boundary](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/intel_hub.py) keeps policy in display context; adding a source-qualified behavioral explanation must preserve that exclusion from scored aggregation.

## 4. PBG-03: financing/support/execution dossier composition

Use owner-native facts to show how a particular issuer's financing and government support progress toward operating execution and cash conversion. A Company Dossier projection can join references to these facts; it does not become their new source of truth.

| Fact class | Retained owner | Hard boundary |
|---|---|---|
| Financing documents, immutable events, terms and amendments | Capital Structure event/source/term owners | Registration is not issuance or cash. Canonical system-as-known and explicit public historical views remain separate. |
| Government instrument, award/action, authorized ceiling and cash outlay | GovRev | Its four current amount classes cannot silently absorb every tax credit, equity instrument, price guarantee or contingent offtake. Unsupported classes need owner admission or remain typed/held. |
| Issuer event, reported operations and source-backed economic values | Company Intelligence | Exact source spans, fiscal period, unit, currency and accounting basis survive the join. Missing expectation evidence cannot become an expectation-change number. |
| Observed credit spread, maturity exposure and funding-window state | CCW | Public bond holdings do not measure a complete private/SPV financing network or ultimate customer cash. |
| Relationship or propagation hypothesis | Accepted relationship owner where one exists; otherwise explicit research-only/held evidence | Theme membership, disclosed agreement and residual co-movement cannot mint supplier/financing/control roles. |

The financial firewall prevents aggregation of cumulative awards with transaction deltas, ceilings with cash, revenue with financing proceeds, repeated source originals, or contingent backstops with current funding. Unknown external-customer cash remains unknown. Keep cancellation, staging, dilution, conditionality, counterparty identity, related-party ambiguity and benign alternatives visible. [GovRev amount guards](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/government_revenue/amount_semantics.py); [Financial Dossier `assemble_evidence_view`](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/company_intelligence/financial_dossier.py); [CCW `snapshot`](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/corp_credit.py).

## 5. Closed-contract and graph boundaries

These proposals must use each owner's compatible extension or versioned contract. For example, Company Intelligence validates exact keys and event lineage, and the workspace retains closed field sets plus immutable generation manifests. A PB-G builder must not smuggle new evidence fields into a closed `event_workspace.v1` object. A new accepted version must preserve existing readers, event identity and generation/correction rules. [Company contracts](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/company_intelligence/contracts.py); [workspace contracts](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/company_intelligence/event_workspace.py).

Main's [GMI materializer](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/theme_graph/materialize.py) explicitly produces membership/expression/proxy relations. Main's [MarketOntology exposure composer](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/market_ontology/exposure_map.py) reads owner edges, takes caller-supplied shock mappings and prohibits generic `RELATED` traversal or ranking by magnitude. Neither becomes a new economic relationship originator through PB-G.

Unmerged research [#8406 at `4f4e80ca…`](https://github.com/mastermindx-market-intelligence/macro/commit/4f4e80ca9ba9309ccb8bb211ff4d0a1ecff00272) and [#8399 at `e66c8382…`](https://github.com/mastermindx-market-intelligence/macro/commit/e66c8382a4b8f04100df7c2f7c0e3493f132f1ca) argue for separate economic/similarity/market graphs, owner-backed identity, Data OS temporal ownership and a governed semantic crosswalk. **They are research proposals, not protected governing law or accepted production.** PB-G adopts their no-duplication reasoning as a proposed architecture decision, grounded separately in the inspected owners; it does not promote those PRs to law. The older D0 suggestion to start economic edges through standalone GMI W4 is therefore not adopted as a PB-G build instruction.

Held K3-D [#6514 at `74b6426c…`](https://github.com/mastermindx-market-intelligence/macro/commit/74b6426c8be71adec27df00f2f98172f8528c2b2) already occupies the hypothesis-contract/compiler territory. It is not installed or accepted here. A future earnings/financing propagation composition must reconcile that carrier and its acceptance state, not create another mechanism schema while it is held.

## 6. Existing consumer and incumbent implementation obligations

PB-D's [#8576 checkpoint at `401d5125…`](https://github.com/mastermindx-market-intelligence/macro/blob/401d51258afc44c9c5cbd21c04586e2c575024a2/research/policy_behavior/pro_returns/PB-D/PB_D_IMPLEMENTATION_CHECKPOINT.md) is a separate incumbent implementation for strict event-quality receipts, first-T2 cohorts, controls and research evaluation. PB-G does not take over those paths or launch a parallel evaluator. Consume a later accepted interface with its exact source/review/cohort identities and zero-authority limits; research completion does not prove prospective enrollment.

**Exact-path admission gap for later Prophet/evaluation handoffs:** this bounded census did not establish the incumbent's final event-quality producer, cohort writer or evaluator callable paths. At the observed #8576 head the PR changed-files response listed only the implementation checkpoint. Known reusable inputs are `engine/company_intelligence/events.py`, `event_workspace.py`, `economic_observations.py`, and `engine/qbus.py`; they are not evidence that a particular evaluation interface is already installed. A later PBG-05/PBG-07 handoff must obtain the incumbent's exact accepted contract/producer/consumer paths before assignment or wiring. No generic replacement evaluator is proposed.

RIC #7521/#7923/#7940 and Company Intelligence K4-G #7426 remain held source work at the observed heads recorded in the no-duplication map. Do not consume their intended behavior as released merely because the source or tests exist. A GovRev contextual annotation may follow the existing [post-selection `annotate_selected_plans()` pattern](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/government_revenue/prophet_annotation.py); Prophet selection and its decision fingerprint must remain unchanged.

The inspected Macro [company continuation adapter](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/transmission_company_continuation.py) proves only its outgoing identity-qualified URL contract to `https://app.mastermind-x.com/analysis`. **Current Terminal receiver implementation, source custody and entitled consumer behavior were not verified.** No Terminal file path or cross-app production acceptance is asserted.

**Country-owner scope:** the verified UK wiring is separate from the Fed-only current-source composer. [`scripts/build_whitehouse.py::main`](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/scripts/build_whitehouse.py) imports `engine.uk_policy_brain` on the shared sentinel path; [`scripts/build_policy_watch.py::main/_uk_desk_view`](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/scripts/build_policy_watch.py) reads `site/uk_policy.json`. The UK engine's full body and current runtime were not re-inspected here. No Japan-specific policy producer, source enrollment or consumer path was established. A U.S.–Japan projection must resolve that exact international owner at admission; the UK receipt is not authority to invent a Japanese counterpart.

## 7. Proof scope and future-build order

The [current main closure ledger](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv) records the deterministic policy lifecycle as **PROVEN_LIVE** on its **2026-09-19** receipt and a later country-policy sentinel acceptance on **2026-10-02**, including run `37007365383`. Preserve those dated accepted scopes. This census performed no fresh production HTTP/browser check and cannot extend those receipts to the proposed PB-G adapters.

| Priority | Future build | Dependency and proof required |
|---|---|---|
| **PBG-01** | Policy evidence freshness and provenance retention | Ordinary source receipt→gathered input→published JSON→existing nightly row→same consumer readback; stale/no-new/outage/correction cases; unchanged scored authority |
| **PBG-02** | Policy Watch rhetoric/action/constraint view | PBG-01 qualification plus one existing policy item and a real later stage/correction through the incumbent store and page; an honest unresolved/undated case |
| **PBG-03** | Financing/support/execution dossier projection | Qualified native owner facts for one complex case and one benign/weak-circularity control; exact typed numbers and limitations in the existing dossier route; receiver verification if Terminal is included |

All three are **SPEC_ONLY / UNLAUNCHED** in this return. Their detailed commissions and acceptance tests belong to the root PB-G roadmap/handoffs. Source tests must prove meaningful discriminators and serialization, followed by the separately authorized normal production/consumer path. Passing fixtures, a source merge, a fresh model run or a source-only canary cannot substitute for the required real-path proof.
