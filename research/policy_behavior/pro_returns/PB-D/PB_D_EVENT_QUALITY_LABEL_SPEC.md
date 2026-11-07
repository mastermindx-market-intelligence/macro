# PB-D event-quality label specification — v1.0

Operation `PB-D-T2-EVENT-QUALITY-20261007`. Status: **FROZEN_DESIGN_NOT_ENROLLED**. Research labels convey no ranking, entry, position-size, alert, or trading authority. The containing final Git commit is the design freeze; activation requires a separate, prospective receipt.

## 1. Object and existing ownership

Label an **issuer × focal economic event × decision cut**, using the event, document, claim, source-span, revision and correction objects already assigned to Company Intelligence. This specification is a research view over those objects, not a second event store. Reuse existing ingestion, qbus/qkernel deduplication and clustering, revisions, and qledger evaluation ownership. The architectural and economic semantics come from [PR8533's pinned masterplan](https://github.com/mastermindx-market-intelligence/macro/blob/cde0219b1040c66cbc8647f86352a25794488528/research/prophet_v4/news_to_business_impact_20261006/package/MASTERPLAN.md) and its [Company Intelligence contract](https://github.com/mastermindx-market-intelligence/macro/blob/cde0219b1040c66cbc8647f86352a25794488528/research/earnings_intelligence/E0_E1_E2_CONTRACT_FREEZE.md).

An article is a manifestation of evidence, a claim is a proposition, and an event groups the propositions that describe an economic change. Distinct URLs, publishers, managers, feature families or model annotations do not establish independent originating evidence. A filing can contain several distinct facts from one origin; a company release can be copied by many outlets. Source-family count is always scoped to a named proposition or mechanism, never an unrestricted sum of favorable facts about a ticker.

The historical `news_burst`, `sue_fresh`, and `smartmoney_add` fields are retained under their old names for reproduction. They are not relabeled as certified evidence roots. Their numerical count is `legacy_leg_count` in discussion and `leg_count` in the reproduction output. New labels must never overwrite these historical features.

## 2. Required receipt and three-valued logic

Every research exposure receipt must contain:

| Field group | Required content |
|---|---|
| Identity | Canonical issuer ID; ticker at cut; existing event ID; focal proposition ID/text; event version; source-document and claim IDs; stable root-family IDs |
| Clock | Decision cut in UTC and America/New_York; economic occurrence time if known; source publication time and precision; first observed/ingested time; availability time; annotation completion time; event correction time |
| Evidence | Immutable content digest or accession/version; exact supporting span or permitted stored excerpt; retrieval/rights status; explicit issuer relevance; origin and dependency links; conflicting evidence |
| Economics | What changed; mechanism; affected revenue/cost/cash-flow/capital/risk/option dimension; direction; magnitude and denominator where supported; horizon; contingency; alternative explanation; falsifier |
| Expectation | Prior baseline ID and vintage; period; accounting basis; units/currency; consensus/guidance/analyst/model type; current value; comparability checks; delta |
| Research process | Provider coverage receipt; missing/stale reasons; annotator IDs; disagreement/adjudication record; label-spec version; source and classifier versions; immutable original receipt plus correction links |

Every tag takes `TRUE`, `FALSE`, or `UNKNOWN`, with reason and evidence references. `FALSE` requires completed, adequately covered review that establishes the tag's absence under the frozen rubric. `UNKNOWN` covers insufficient retrieval, ambiguous root relationships, absent expectation baselines, stale inputs, uncertain clocks or unfinished review. A null is never converted to false for convenience. Truth of an official announcement verifies that the announcement occurred; it does not verify fulfillment of a forecast, execution of a contract, or realization of projected earnings.

For primary-cohort eligibility, both independent raters and any adjudicator must finish by the decision cut, using only evidence available by that cut. Later research may reconstruct an event for an explicitly retrospective secondary audit, but cannot create a prospectively available label. An automated draft alone is not an adjudicated label.

## 3. Orthogonal taxonomy

| Tag | Positive rule | False/unknown boundaries and examples |
|---|---|---|
| `ATTENTION_ONLY` | Raw attention is true, coverage review is complete, and no verified new material economic delta is found in that issuer's reviewed event set. | An issuer mention, roundup or recycled release can qualify as attention only. Incomplete retrieval is unknown, not attention only. Positive tone is unnecessary. |
| `VERIFIED_MATERIAL_EVENT` | A new or newly corrected, source-backed fact, commitment or realized milestone has a documented mechanism that can materially alter the issuer's economics or risk. The assertion, magnitude/context, horizon and contingency are separately recorded. | A headline's adjectives, stock-price move or a large industry TAM does not satisfy the rule. Promotional estimates require substantiation. Verification of allegations is distinct from verification of the alleged conduct. |
| `EXPECTATION_CHANGE` | A current economic value or outlook differs from an admissible, preexisting baseline matched on issuer, period, units, currency and accounting basis. Both vintages were captured at admissible times. | Without a usable prior baseline, return unknown. A fiscal-period rollover or GAAP/non-GAAP mismatch is not a revision. A forecast change can be negative, positive or mixed. |
| `STRATEGIC_OPTION` | A credible new option has identifiable resources or funding, a causal path to an economic opportunity, a milestone and a falsifier; near-term earnings need not be measurable. | An unfunded aspiration, partnership slogan or announcement lacking a plausible path is insufficient. Financing need not be new in the same window, but its source and continuing validity must be documented. |
| `GOVERNMENT_LINKED` | A specific government action is a causal input to the event: e.g., an award, enacted restriction, procurement, permission or funding decision. | A politician's mention or general political coverage is insufficient. The tag does not imply favorable direction or enacted status. Record proposed/approved/effective separately. |
| `FINANCING_LINKED` | New funding availability, financing terms, dilution, refinancing, liquidity or capital structure causally changes the issuer's event or option. | A fund's secondary-market 13F purchase is not automatically financing for the issuer. Record committed versus conditional funding and material covenants. |
| `INDEPENDENT_EVIDENCE_2PLUS` | At least two admissible originating evidence families independently support the named focal economic proposition or causal mechanism; their origin, dependence test and availability clocks are documented. | Two articles citing one release, a model reading that release, and a later roundup remain one origin. Uncertain source lineage is unknown. See Section 4. |
| `SYNDICATED_SINGLE_ROOT` | At least two retained manifestations in the focal scope trace to one originating evidence family, with no additional independent family in that scope. | One original article alone is not syndicated. Syndication can carry a real material event. An independent second root makes this tag false in the same focal scope. |
| `NO_MATERIAL_EVENT` | Completed coverage and evidence review finds no new material economic delta in the specified window. | This concerns new information in the window, not whether the issuer has economically important businesses or older material events. Missing coverage is unknown. |

These are not nine exclusive classes. An event may be material, expectation-changing, government-linked and financing-linked at once. It contributes one economic observation. `ATTENTION_ONLY` and `VERIFIED_MATERIAL_EVENT` cannot both be true at the same issuer/window scope; nor can `NO_MATERIAL_EVENT` and materiality. `INDEPENDENT_EVIDENCE_2PLUS` and `SYNDICATED_SINGLE_ROOT` cannot both be true for the same focal proposition and evidence scope. If one issuer has a syndicated event and a different independently corroborated event, retain separate event IDs and report both tags at issuer level with explicit scope.

Here, attention-only means no **material** new economic delta. A verified but immaterial expectation change may coexist with it and must be disclosed; the term does not assert that literally no numerical forecast changed.

Materiality is a structured, blinded research judgment, not a universal dollar threshold. Require a documented mechanism plus issuer-relative scale, duration or risk significance. Reviewers must record why the delta is consequential for this issuer. Unsupported magnitude or timing must remain unknown; plausibility alone does not certify materiality. This rubric is fixed before outcomes and is never calibrated to maximize historical returns.

## 4. Independence and freshness

For each candidate root, ask who generated the observation, what proposition it supports, whether it relies on another candidate, and whether both could be wrong for the same evidentiary reason. Record the answer; publisher count is only a reporting-breadth statistic.

| Evidence combination | Counting decision |
|---|---|
| Release, wire rewrite, syndicated newspaper and LLM summary | One origin for the release's claim |
| Two analyst notes based on the same management guidance | Usually one factual origin for that guidance; distinct analyst opinions do not independently prove it |
| Issuer announcement and independently issued counterparty/regulator document | Potentially two, only if independently generated and each supports the relevant proposition; a jointly authored release remains one |
| Earnings release and its exhibit filed on EDGAR | One origin for the same reported result |
| Independent operational measurement and a separately generated official record | Potentially two after method, clock, issuer linkage and shared-input review |
| T2 plus news plus old earnings plus old ownership | Technical state plus legacy categories; no automatic evidence-root count |
| Multiple managers reporting separately | Distinct position-report origins may establish their own holdings claims; they do not independently prove an unrelated contract, earnings revision or issuer financing |

For the **primary fresh-quality exposure**, at least two supporting roots must have a reliable public release or substantive revision containing genuinely new supporting information in the three decision-cut intervals ending at the current cut: `(cut[d−3], cut[d]]`. Each must also be locally observed by the cut. The usable time is the maximum of reliable public availability and local observation, but late ingestion of an old public fact does not renew its freshness. Date-only, contradictory, suspiciously backdated, or missing public clocks are ineligible for the primary fresh count. Material new information must also be within that window. Older admissible evidence can provide context, a prior expectation or a still-valid funding basis, but is not a newly arrived independent root for this exposure.

The two roots need not be two restatements of one sentence. They may establish distinct links in the same named mechanism, provided those links were independently generated and together support the focal economic change. Unrelated facts about the same ticker cannot be aggregated to reach two. The event-root graph and rationale must be reviewed without future prices.

Existing qbus title similarity, item identity, novelty scores and echo statistics are useful retrieval aids. They are not a certificate of semantic independence. In particular, a normalized-title-plus-host identity can preserve mirrors under distinct IDs, and a calendar-date cutoff does not establish an intraday decision cut. Preserve the underlying clocks and root graph in the research receipt. These limitations follow the [existing qkernel](https://github.com/mastermindx-market-intelligence/macro/blob/cde0219b1040c66cbc8647f86352a25794488528/engine/qkernel.py) and [qbus](https://github.com/mastermindx-market-intelligence/macro/blob/cde0219b1040c66cbc8647f86352a25794488528/engine/qbus.py) ownership; this specification does not replace their current behavior.

## 5. Expectation baseline hierarchy

Prefer a licensed, versioned consensus with matched period and basis. Otherwise use prior company guidance or a contractual baseline; then a previously captured analyst forecast; then an explicitly frozen research model; then a disclosed historical base rate. Record the baseline type rather than silently pooling them. None may be created from the future outcome or revised consensus after the event.

The prior baseline must be available before the new economic information, and the delta receipt must be complete by the decision cut. A consensus value without its timestamp, units, fiscal period, rights or accounting basis is not automatically admissible. A model-implied surprise is labeled as such and is not a reported analyst revision. `STRATEGIC_OPTION` can be true while expectation change is unknown. A large reported surprise is not necessarily independent evidence if it derives from the same earnings release.

## 6. Annotation, aggregation and correction

Two independent raters see source packets and historical context up to the cut, but no post-cut returns, grader outcomes, future commentary or cell performance. They record labels independently before reconciliation. A third reviewer resolves disagreements from the same admissible packet; unresolved cases are unknown. Report raw agreement, per-tag confusion counts and adjudication rate, including unknowns. Agreement is a process diagnostic, not proof of truth.

For issuer-level aggregation, collect every candidate event in the fixed window and apply the coverage/resolution gate first. If coverage is incomplete, or any candidate has unresolved materiality or fresh-root status, primary Q is unknown. The resolution gate concerns those primary fields; an unknown expectation baseline or other secondary tag does not itself block Q. Among records passing the gate, `Q=1` means at least one event has materiality and fresh independent-evidence-2plus both true; `Q=0` means none does. A fully reviewed empty event set has Q=0. Apply the same gate to both groups. Do not select only a favorable-looking event. If several Q=1 events exist, retain all event IDs and select the earliest first-usable event, then lexical existing event ID, as the display anchor; the exposure remains one issuer observation.

Retain the immutable original decision receipt. A later source correction appends a revision with its own available/observed time and links to the original claim. It changes subsequent research context; it does not rewrite the primary as-known exposure. Report a secondary corrected-truth analysis and the direction/rate of corrections. A discovered time-travel or mapping error is a data-integrity exception: quarantine with the original record preserved, show included/excluded sensitivity, and never silently turn a historical false into a true exposure.

## 7. Historical disposition

The existing grade dataset has no certified root graph, expectation baseline or audited economic materiality labels. All historical primary-quality labels remain **UNKNOWN**. The archived NVDA, INTC, PRIM and holdings probes in `PB_D_SOURCE_AUDIT.json` demonstrate why retained articles and feature categories are insufficient; they do not establish that every legacy burst was economically empty. In particular, the Sep10 archive cannot label every earlier PRIM/TSLA observation, and later manager grades cannot be backdated to an earlier T2 decision.

PB-G may implement missing receipts and owner adapters only through the existing owners after separate authorization. Historical event-quality estimation remains blocked until exact decision-cut archives, source bodies/claims, root lineage and real earnings/ownership clocks are available. No replacement of unknown with synthetic hindsight labels is permitted.
