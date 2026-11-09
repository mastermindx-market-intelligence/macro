# PBG-03 — Typed financing and support in the company dossier

**Status: PROPOSED_UNLAUNCHED.** Incorporates the [shared handoff contract](../PB_G_IMPLEMENTATION_HANDOFF_INDEX.md). Domain contract admission and source-clock compatibility precede implementation.

## Capability and division of ownership

A company reader can trace a financing/support arrangement from announcement and legal commitment to funding, deployment, recognized revenue and collected cash where evidenced. They can identify the legal obligor, economic beneficiary, counterparty roles, outstanding conditions and counterexamples without treating every relationship as outside demand.

Company Intelligence owns issuer/event identity, economic observations, dossier projection and corrections. Capital Structure owns financing source/event terms. CCW owns observed public credit conditions. GovRev owns qualified public award/support facts under its admitted amount semantics. Existing graph/exposure composition may join admitted owner facts; PB-E research edges are not a parallel graph or production fact store.

Candidate paths: [company events](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/company_intelligence/events.py), [event workspace](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/company_intelligence/event_workspace.py), [economic observations](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/company_intelligence/economic_observations.py), [financial dossier](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/company_intelligence/financial_dossier.py), [views](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/company_intelligence/views.py); [capital event spine](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/capital_structure/event_spine.py), [terms](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/capital_structure/document_terms.py), [projection](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/capital_structure/projection.py); [GovRev amount semantics](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/government_revenue/amount_semantics.py), [award events](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/government_revenue/award_events.py), [dossiers](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/government_revenue/dossiers.py). Read CCW through its existing artifacts. Recheck exact-path custody and closed contracts before allocating writes.

## Minimum fact and projection contract

Require source spans and version; entity/SPV identity and consolidation perimeter; transaction group; legal instrument and state; obligor/beneficiary; amount, currency, unit, period and whether gross/net; conditionality and expiration; source/local clocks; and relationship role actually supported by evidence. Keep financing inflow, announced commitment, capacity, guarantee cap, project spend, recognized revenue and customer cash separate.

Only sum compatible observed flows within an explicitly declared boundary after eliminating duplicate transfers and transfers internal to the declared boundary. A dollar of financing is not automatically customer cash; successive recognized revenues at different supply-chain stages are not automatically fictitious. An absent cash disclosure is unknown. A future contingent cap is not cash paid or expected loss. A bond coupon differs from effective accounting interest and all-in incremental cost.

GovRev's existing cumulative-award/transaction-delta/ceiling/outlay classes cannot silently absorb tax credits, equity or contingent offtake. Hold unsupported terms pending owner-reviewed typed extension. Preserve CoreWeave's August 11 press-release versus August 12 source/filing distinction and null first-public clocks before admission. All 112 PB-E edges are research-only until individually qualified.

## User output and consumer boundary

Show a dossier evidence section: commitment/execution status; funding and external-cash boundary; supported relationships; risks/conditions; beneficiaries/burdens; alternative explanations; and last qualified evidence. Examples must include both financing-intensive expansion and substantive counterexamples, not only a selected “loop.”

Expectation change is separate and requires a matched pre-event baseline; a missing baseline withholds that conclusion. Technical-state context remains a post-selection annotation, never a new candidate or rank factor.

The inspected Macro continuation path is [engine/transmission_company_continuation.py](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/transmission_company_continuation.py). The receiving Terminal implementation/runtime was not inspected in PB-G. A Terminal claim requires current exact receiver ownership, entitled data route and UI proof at future admission. Do not invent a Terminal filename or call an outgoing link an implemented receiving experience.

## Tests and real-path proof

Demonstrate announcement versus execution; registration versus issuance; cash versus capacity; conditional cap versus draw; source correction; duplicate transaction; original agreement versus an amendment that states an increment or cumulative total; changed consolidation perimeter; unsupported instrument; ambiguous role; missing amount/period/rights; and positive operating-cash counterevidence. Refuse incompatible sums. Verify actual selected-plan fingerprints remain unchanged if an existing Prophet annotation is consumed.

Trace a retained real filing/program record through its owner, event version, dossier projection and existing visible consumer. Show a withheld unsupported case as well as a valid fact. Terminal proof is separately required if included in the admitted scope.

## Stop and non-goals

Stop at the typed dossier capability with exact provenance and real consumer proof. No universal circularity score, industry financed-demand percentage without a denominator, causal WACC discount, guaranteed equity upside, automatic economic-role graph or duplicate economic-propagation contract. Held K3-D/#6514 and event-workspace/#7426 remain occupied dependencies; newer unmerged exposure research is not accepted production law.

