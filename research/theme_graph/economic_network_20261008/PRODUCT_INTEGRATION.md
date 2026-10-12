# Product integration specification

Research specification for Sol and incumbent product owners, 2026-10-08. No routes, interfaces, renders or runtime state were changed in this commission.

## 1. Product outcome

Make economic connections inspectable from the user's current company, theme or event workflow. A user should be able to distinguish a disclosed role, a comparable business, an observed market relationship and a conditional operating hypothesis without understanding the underlying graph implementation.

The first useful release is evidence-backed context: what is connected, why, when, how strongly the source supports that meaning, and what remains unknown. A market signal is not required for this release. Numeric impact stays absent where the source or accepted model does not support it.

## 2. Incumbent seams and boundaries

| Surface | Inspected seam | Preserve | Proposed addition |
|---|---|---|---|
| Theme Fabric / theme navigation | Accepted semantic hierarchy and sole ThemeState lineage | Category/theme/micro distinctions; lifecycle and membership qualification; one producer | Role-filtered economic context drawn from eligible native facts |
| MarketOntology F04 | engine/market_ontology/exposure_map.py; market_ontology.exposure_map/v1 | Research-display authority, exact identity, rights/null gates; hierarchy is display context | Source-backed economic path detail, conditions, magnitudes and abstentions |
| Macro transmission view | Existing F04 transmission parent | Existing path identity and ownership | Originating event, scope, shared allocations and competing explanations |
| Terminal Company Intelligence | terminal/app/api/company-theme-context/[symbol]/route.ts | Server authentication, symbol normalization, current generation/event alignment, no-store | Accepted economic-context fields or sidecar within the owner-chosen versioned contract |
| Terminal navigation | terminal/lib/marketOntologyContext.ts | Closed transient mo_* vocabulary; no identity/auth authority | Reuse return context; keep precise research cuts in validated server receipts |
| Earnings / NeuralWeb | Existing ThemeState adapter and held K3-D composition lineage | Source ownership, typed Graph1/2/3 evidence, zero trading authority | Conditional read-through briefing with visible evidential differences |

These seams were inspected at Macro 7e6ce338a9f88aaa60834bdeaf5ee2fe90dab477 and Terminal 54f97dda68a76a55ba0813afc9433ef54aaf401c. They are evidence of code contracts, not proof of a new economic-context production emitter.

Sources: [F04 composer](https://github.com/mastermindx-market-intelligence/macro/blob/7e6ce338a9f88aaa60834bdeaf5ee2fe90dab477/engine/market_ontology/exposure_map.py), [Terminal context route](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/54f97dda68a76a55ba0813afc9433ef54aaf401c/terminal/app/api/company-theme-context/%5Bsymbol%5D/route.ts), [navigation helper](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/54f97dda68a76a55ba0813afc9433ef54aaf401c/terminal/lib/marketOntologyContext.ts), [ThemeState adapter](https://github.com/mastermindx-market-intelligence/macro/blob/7e6ce338a9f88aaa60834bdeaf5ee2fe90dab477/engine/neuralweb/theme_state_adapter.py).

## 3. Six user journeys

### 3.1 Theme → economic context

A user opens an AI infrastructure theme and requests “economic connections.” The view retains the accepted semantic hierarchy. It then offers separately labeled views of suppliers/customers, capabilities and constraints, end-market demand, and comparable companies.

Only owner-admitted role-specific relationships appear as ordinary economic connections. Theme membership alone may place a company in the comparison view; it does not place the company in a supply chain. The result includes the coverage boundary and the time of the underlying evidence.

The default view emphasizes a small, readable neighborhood with a supporting table. Expansion is deliberate and bounded; a high-degree cloud of nodes is not the primary product. Hierarchical PARENT_OF edges never become transmission paths, weights or counts of economic exposure.

### 3.2 Company → why connected

From a company, the user opens a relationship. The detail panel shows:

| Information | Example behavior |
|---|---|
| Role and direction | Supplier to customer, or ownership interest; no generic “related” badge hiding the role |
| Scope | Specific product, agreement, facility, geography and reporting perimeter |
| Source | Issuer/filing/vendor identity, exact section and original language |
| Time | Disclosed date, effective/contract period and precise-time availability |
| Magnitude | Measured amount with denominator and unit, or “not disclosed” |
| Evidential state | Disclosed, candidate, contradicted, historical, stale or otherwise qualified |
| What this supports | A concise factual relationship statement |
| What would be needed next | Order allocation, capacity, qualification, current renewal or another specific observation |

For CATL/Tesla, the view presents the disclosed framework and its term, explains that quantities depend on orders, and treats the two buyer parties as a shared agreement. It does not display a current contract merely because historical evidence exists.

### 3.3 Event → operating read-through

An earnings announcement or disruption enters through its incumbent event owner. The user sees why each candidate was retrieved: an economic path, comparable operations, market evidence, or a combination with labels retained.

A supported operating hypothesis includes target variable, conditional direction, horizon, conditions and falsifiers. A Graph 2-only or Graph 3-only result cannot receive an economic transmission claim. A known but unusable Graph 1 object should say why it is unusable rather than “no relationship.”

The product must not translate “operating margin may deteriorate” into “sell” or infer a price forecast from realized revenue growth. Current K3-D's authority remains research/display only.

### 3.4 Dependency → bottleneck investigation

The user asks which input constrains a production system. The view presents an evidence table for demand, qualified capacity, inventories, substitution and lead times. An unmeasured capacity is unknown, not zero. The result can state that a dependency is documented while bottleneck status is unestablished.

Where an accepted scenario is available, the user can change explicitly labeled assumptions and inspect the resulting output and limiting input. Observed facts remain fixed; scenario assumptions are visually distinct. An assumed production function cannot be displayed as an empirical forecast.

The synthetic witness in this package supplies a specification example, not a production scenario for any named issuer.

### 3.5 Earnings briefing → differentiated peer evidence

The briefing groups an event's economic paths, operating comparables and market observations into distinct sections. Each result retains its generator's original admission reason. A sympathy move or broad participation state cannot retroactively supply missing economic evidence.

The briefing should be concise enough to use, with full provenance one action away. The same underlying compiled object supplies the visual summary and machine-readable answer. A generated summary cannot introduce unsupported entities, amounts or chronology.

### 3.6 Research queue → evidence needed

An analyst can filter for unresolved identity, unsupported role, missing magnitude, stale contract, conflicting disclosure or insufficient instant proof. Ordering here measures research work, such as an expiring source or missing required field. It is not financial attractiveness, alpha rank or portfolio priority.

No automated review queue was established by this census. The incumbent owner should adopt the minimal workflow needed, reusing existing review/receipt mechanisms. New research interfaces must not become an independent decision ledger.

## 4. Response contract and server behavior

### 4.1 One content contract

The owner should extend the accepted Company Intelligence/F04 context lineage through a reviewed compatible field addition or version change. The route choice must be adjudicated against the current validators; this specification does not authorize stuffing extra properties into closed v1 contracts or starting a parallel economic API.

The candidate economic-context section needs:

- Canonical subject and historical resolution receipt.
- Owner generation/event identifiers and exact compilation/input revisions.
- Query scope, purpose and temporal eligibility receipt.
- Documented relationships with roles, scopes and original evidence references.
- Separate comparability and market-evidence references.
- Mechanism/path references with conditions, alternatives and falsifiers.
- Magnitudes with units, denominators, status and null reasons.
- Coverage/freshness/contradiction/truncation information.
- Entitlement-filtered display content.
- Explicit authority and accepted model/promotion reference, if one ever exists.

The existing content hash/receipt convention should cover canonical serialized content. Human and machine clients using the same accepted query and artifact must receive the same evidence and authority. If a summary is regenerated, it must be tied to the same immutable source object and cannot change its substantive claims.

### 4.2 Illustrative response, not an adopted schema

The following object shows required semantics. Its placeholder version and example IDs are deliberately not production identifiers:

~~~json
{
  "contract_status": "PROPOSED_OWNER_VERSION_REQUIRED",
  "subject_resolution_ref": "<existing native identity receipt>",
  "generation_ref": "<current accepted owner generation>",
  "query_receipt_ref": "<native temporal and purpose-scoped query>",
  "economic_context": {
    "mode": "evidence_only",
    "relationship_refs": ["<owner-admitted scoped relationship revision>"],
    "hypothesis_refs": [],
    "magnitude": null,
    "magnitude_reason": "NOT_DISCLOSED",
    "precise_historical_use_proven": false,
    "coverage": {
      "basis": "reviewed source subset",
      "population_recall": null,
      "truncated": false
    },
    "authority": {
      "research_display": true,
      "grade": false,
      "rank": false,
      "size": false,
      "trade": false
    }
  }
}
~~~

These candidate labels require an explicit crosswalk into the adopted wrapper. Existing K3-D closed enums must remain exact; unknown new reasons cannot be forwarded as if v1 already supported them.

### 4.3 Existing server guarantees

The inspected Terminal route authenticates on the server, normalizes and rejects noncanonical symbols, verifies current Company Intelligence generation/event alignment, and uses no-store responses. Its status mapping includes 400 invalid symbol, 401 unauthorized, 404 missing company, 502 invalid payload, 503 unavailable upstream and 429 rate limit.

Preserve those guarantees for any accepted extension. Restricted native evidence must never be published in a public object merely because the existing context route can fetch public projections. The server must resolve the actual entitlement and permissible use before retrieving or summarizing restricted material.

Generation mismatch is an availability failure, not permission to combine the latest theme view with an older company event. Corrupt evidence should not become an empty successful result.

### 4.4 Navigation is context, not authority

The existing mo_* query vocabulary carries transient navigation context and a safe return path. It does not confer identity, permission or historical proof. It permits strict dates for mo_asof and mo_kc, not arbitrary instants.

Reuse the current validated fields. Do not smuggle an instant into a date field or add unvalidated parameters expecting current clients to honor them. A precise cutoff should be represented through an accepted server-side query/receipt contract. On symbol change, preserve the existing clearing behavior so one company's path context is not applied to another.

## 5. Presentation rules that matter economically

### Labels and visual meaning

Use arrows with explicit role labels. An economic goods-flow arrow and a hypothetical demand-shock direction may differ; show that distinction rather than reversing the fact. Edge thickness must not imply economic weight when magnitude is unknown. Color should identify evidence family or status, not unapproved buy/sell direction.

Use numbers only with units and denominators. A share should read “share of supplier's FY2024 revenue from this customer,” not “exposure 20%.” Ranges disclose whether they are source ranges, scenarios or statistical intervals. Unknown is readable text, not a zero-width edge or zero score.

A default compact relationship table is useful alongside the graph. It can sort by role, source freshness or a measured field where permitted. Display count is not a forecast or a measure of systemic importance.

### Bilingual evidence

Preserve original Chinese and English source text and provide a marked translation. Legal entity names remain those resolved by the identity owner. A translation should not turn uncertainty, a future plan or a framework into a stronger statement.

Normalize units with a recorded conversion. For example, a Chinese monetary unit such as 万元 requires its explicit scale; a currency conversion additionally needs exchange-rate date, source and purpose. Keep original values available for audit. Translated copies of one document are not independent corroboration.

### Responsive and accessible use

Desktop can show a graph with a detail panel. Mobile should default to a readable ordered relationship list and a focused path rather than a miniature full network. Keyboard navigation, focus management, labels independent of color and source links are part of acceptance. Dark/light and Chinese/English states should preserve the same meaning and numeric formatting.

These are future product acceptance requirements. This research did not implement or render a UI, so no visual or browser validation is claimed.

## 6. Failure and empty states

| State | User-facing meaning | Required behavior |
|---|---|---|
| No eligible economic evidence | Sources inspected do not support a role-specific path for this query | Show coverage boundary; keep comparability separate |
| Role unknown | A counterparty is known but the economic role is not supported | Do not label supplier/customer |
| Historical term | The cited agreement covers a past interval | Offer historical evidence; no invented continuation or global termination |
| Exact time unavailable | Source precision cannot prove the requested intraday cutoff | Explain the date-level limitation |
| Magnitude unknown | The connection is supported but its size is undisclosed | Keep numeric impact absent |
| Conflict | Eligible sources disagree or revise prior facts | Show the conflict and revisions |
| Restricted | The requested evidence or use is not permitted | Withhold affected content; do not leak it through counts or summaries |
| Stale or superseded | Current-use eligibility failed | Show historical context only if permitted |
| Incomplete page | Query limits truncate the neighborhood | Preserve snapshot-aware continuation and mark incompleteness |
| Outside model scope | No accepted forecast applies | Return evidence-only context |

Do not replace these with a generic “no data” response. The difference determines the next useful action.

## 7. Product acceptance witnesses

Before accepting a release, the incumbent owners should produce:

1. A real source-backed positive Graph 1 path, admitted under native identity/time/rights contracts, served through the actual consumer route.
2. A financing-agent or trustee example that cannot become a supplier/customer path.
3. A Graph 2/3-only example that remains economically abstained.
4. A same-day date example that cannot prove an exact intraday cut.
5. A source with a supported relationship and undisclosed magnitude that remains numerically null.
6. A correction that changes the present view while leaving an earlier served/replay view intact.
7. A restricted source blocked for the requested purpose, including derived content.
8. A generation-mismatch and upstream-failure example with the proper failure state.
9. A human/machine comparison of the same artifact and authority.
10. A bilingual, responsive, keyboard-usable visual review on the actual implementation.

The current package contains source cases and isolated logic witnesses useful for preparing these tests. It does not contain a positive live Graph 1 consumer proof. That distinction is a release gate, not a reason to misstate the research result.
