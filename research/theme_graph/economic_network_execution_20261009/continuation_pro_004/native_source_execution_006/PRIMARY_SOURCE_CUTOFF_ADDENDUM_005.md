# Primary-source cutoff and adjustment findings for the native US slice

Observed on 2026-10-09. This supplements the accepted WP02 sourcing work and the current-source native route review. It records completed documentation/source analysis. The actual provider call and native store proof, if executed, have their own separate receipt; this document supplies neither an acquisition nor source admission.

## A current supported endpoint already exists in the estate

Massive documents `/stocks/v1/splits` as its current split endpoint and marks `/v3/reference/splits` deprecated, without a removal date on the inspected page. The current endpoint supplies execution dates, ratios and adjustment classification, with pagination. Its documented maximum page size is 5,000. The incumbent source uses the current endpoint, a stricter 1,000-row page request and its own total limits. No endpoint migration is required for the proposed native call.

Sources: [current endpoint](https://massive.com/docs/rest/stocks/corporate-actions/splits); [deprecated endpoint](https://massive.com/docs/rest/stocks/corporate-actions/reference-splits). Independently read native source: [massive_split_evidence.py at 87b01101](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/engine/close_pass/massive_split_evidence.py), Git blob `f7123e761ea83011f603a8e3cd37d4240ab5d59b`.

## Effective date, observed vintage and public knowledge differ

The split schema describes the execution date as the date the share change takes effect. The inspected response-attribute list supplies no original-publication or provider-correction timestamp. That is a statement about this documented endpoint, not proof that Massive has no other historical-version product. The current native capture records producer-created acquisition/page clocks and IDs; those establish observations at F, not publication at K.

The proposed call's `basis_date=D` is retained request metadata. Its actual query is `execution_date.gte=D`, ordered ascending, without an upper bound. Thus a row after D is not evidence of an incorrect response to that query. It remains in the actual capture and is ineligible for an unqualified D-basis inference. The collector's existing `basis_eligible=False` is preserved.

Source: [current response schema](https://massive.com/docs/rest/stocks/corporate-actions/splits), plus the native `_request`, `_row` and `acquire_split_history` implementations at the immutable commit above.

## An adjustment factor is not an arbitrary historical share-basis bridge

The provider's split explanation says its cumulative factor expresses earlier prices on today's share basis, and the classification may be revised after the event. A later observed factor therefore does not certify what was known or delivered at an earlier cutoff. Empty results are a normal range-specific response; the provider also notes that retail plan history windows can affect emptiness. The accepted enterprise grant is not reopened by that retail-plan note, but actual product coverage still requires observed evidence.

Source: [split and reverse-split explanation](https://massive.com/knowledge-base/article/does-massive-support-normal-and-reverse-splits).

Separately, Massive describes aggregate bars as split-adjusted by default, with `adjusted=false` selecting raw prices. Its explanation warns that adjusted history can change when later splits occur. Dividend-adjusted total-return modeling remains a separate convention. Consequently WP02 must name the actual raw price basis, operative class/share basis and K-eligible action chain; a field labelled adjusted cannot satisfy all three.

Source: [price-adjustment semantics](https://massive.com/knowledge-base/article/is-massives-stock-data-adjusted-for-splits-or-dividends).

## A release schedule does not authenticate the bytes of a historical vintage

The flat-file overview describes unadjusted US market data generated after the full trading session, with approximate availability the next day. The day and minute dataset pages independently describe an 11:00 a.m. ET update schedule. Those current schedule statements make a possible acquisition route more concrete. They cannot authenticate that today's downloaded file has the exact content released on an earlier date, or prove a complete correction history through K.

Sources: [flat-file overview](https://massive.com/docs/flat-files/stocks/overview), [day aggregates](https://massive.com/docs/flat-files/stocks/day-aggregates), [minute aggregates](https://massive.com/docs/flat-files/stocks/minute-aggregates).

The overview's general timestamp wording and its dataset descriptions are not a substitute for field-specific clock units. An adapter must use the actual endpoint/file schema and checked values. This review did not acquire flat files or establish their complete field schema; no generic seconds/nanoseconds conversion is adopted here.

## Exact native retention limits and useful falsifiers

The current source API observes bounded decoded response bytes but persists their hashes/counts and parsed rows, not original response bodies. It drops unselected wire fields during normalization. A successful native generation read can therefore reproduce the stored acquisition object and its custody receipts; it cannot rerun the original parser over retained raw response bytes. This is a loss to record, not a reason to replace the existing source kernel or label a hash full forensic closure.

The real operation should preserve each of the following possible outcomes:

- Missing credentials: the existing public function refuses before transport. Record no acquisition and no provider request; do not transform this into a licence denial.
- Complete empty response: capture the actual request range and response evidence. Do not claim complete historical absence of corporate actions.
- Future, partial or failed evidence: preserve actual rows/pages and refusal reasons. No automatic retry, truncation-to-success or callback-created evidence.
- Optional provider fields absent but required by the native parser: preserve the native refusal. Any proposed change to strict native validation requires its own owner review.
- Successful current capture/read: retain actual producer F, generation/receipt identities and idempotent repeat result. K-publication, D-close price, complete issuer/class history and global pool completeness remain unproved.

The selected MU route is a real-issuer acquisition-path investigation. It is not a disclosed supplier/customer relationship, thematic similarity, market correlation, eligible diagnostic cohort member or predictive result. It does not fill Graph1 or enable rank/gate/size/trade/prediction. The accepted Massive enterprise record permits relevant research/corporate-action use; it does not confer signal authority or validate these missing facts.

Existing owners remain the CorpActions producer, the Market Memory source kernel/reader, Data OS identity/time/source policies and the economic-network research consumer. No new registry, credential resolver, transport factory, public product surface or production activation is introduced by this finding.
