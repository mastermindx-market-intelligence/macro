# Healthcare R12 — shared extension specification and economic witnesses

**Status:** principal-authored semantic specification and original synthetic research. The shared-owner return is consumed; this file does not claim native v1.1 implementation, independent approval, live admission, or Healthcare worker execution.

**Date:** 24 September 2026. **Operation:** `gmi-healthcare-deep-research-20260923-sol-001`. **Research carrier:** Macro #7788, `claude/healthcare-theme-research-20260923`. **Pickup:** `1bc212cf8d72d93b004b9b59a0c60efc895a2158`. **Protected procedure:** Mastermind `4fe4d25e3ee268e24162f33c35d176ebf9ab02e6`, compatible Skillpack 1.0.1/bootstrap 1. **Shared source observation:** #7870 at `d5b0c00d772e5034ed8c109b5990b1f3b91e0be5`, draft/unmerged. The assertion schema is still blob `ff3928f0c54aa164ef8283d9da45af67e6a0d971`.

## 1. What actually changed

The existing Semiconductor B receiver explicitly acknowledged the operative R4 ruling in #7780 comment **5808981293**. It adopted the qualifications on native ownership, private publication, known-existing-object privacy proof, entitlement continuity and source rights. R4 is now decided **and acknowledged**. Neither receipt proves the private reader, stored body, live admission or deployed user path.

The shared owner separately answered Healthcare request 5808534349 in #7870 comment **5808981043**. Native identity/mint and cross-domain preservation were accepted; shared routes/policy were accepted as intent, not implementation. The Healthcare predicates and signed/non-numerical measurement needs were **held outside Semiconductor B**, pending a properly scoped additive shared revision. This is a scope boundary, not a rejection of Healthcare's user need.

Native review submissions and later #7788 discussion returned no review in this turn. The existing requests to the shared maintainer and independent Healthcare reviewer remain outstanding. This specification is author-side analysis, not a fabricated independent verdict.

### Principal decision

Preserve the Semiconductor B build and its v1 baseline. Healthcare must consume a **versioned extension of the same native assertion owner**, not require B to absorb new domain semantics during its accepted release and not create a Healthcare validator, ledger, source-rights system or publication service.

Select `theme_graph.curation_assertion.v1.1` as the explicit candidate wire discriminator for new extended records. The exact extension is a separately gated common-owner dependency of Healthcare Task T03. It is not enrolled or dispatched by naming it. Product implementation and a source-writer assignment require the normal shared-owner release/custody and review gates. The current B operation remains unchanged.

Reject the tempting alternative of simply adding every failing R9 enum value to v1. Some of those values were semantically misplaced: **net sales is a payment denominator, not a gross/net flag; not disclosed is a disclosure state, not estimation provenance; qualitative is a non-numerical fact, not decimal precision.** R12 supersedes that literal enum-expansion reading of R9/R10 while preserving the underlying research requirements.

## 2. User outcome, ambition and alternatives

The user must understand a Healthcare development through five questions: what changed; which business mechanism could transmit the change; which participants have evidenced rights or operating roles; what could offset the benefit; and what evidence should be checked next. The first existing GLP-1 journey is the proving case, not a sector-wide completion claim.

The full twelve-family research program, subsequent therapeutic and services depth, global access differences, contemporary expectations, actual security bridges and point-in-time evaluation remain owed. The first current-evidence release cannot claim a valuation anomaly, target price, stock ranking, calibrated probability or trading authority without the separate accepted evidence those conclusions require.

Three options were considered:

| Option | Benefit | Failure or cost | Disposition |
|---|---|---|---|
| Widen B's existing v1 fields opportunistically | Small apparent change | Couples Healthcare to B's freeze; conceals semantic mistakes; risks changing legacy validation and revisions | Rejected |
| Create a Healthcare-local representation/validator | Local implementation freedom | Second grammar and authority; cross-sector evidence becomes incompatible | Rejected |
| Add a common version-aware branch with immutable legacy behavior | One owner, explicit compatibility, truthful domain meaning | Requires a bounded shared amendment, a profile consumer and independent review | Selected |

The shared amendment is not an infrastructure-only release. Its useful proof includes a Healthcare economic explanation using the native version plus an unchanged Robotics/Semiconductor legacy witness through the existing protected path.

## 3. Compatibility contract: preserve v1 bytes, meaning and identity

The existing `schema` field is the dispatch discriminator. Keep `theme_graph.curation_assertion.v1` byte-for-byte meaningful under its original branch. New records that need the extension declare the new version. Do not add an implicit default version, auto-upgrade old rows, fill new fields into v1 objects, reinterpret old quantities, or re-mint historical evidence for a schema rollout.

The same `engine/theme_graph/curation_assertion.py` remains the public native entry point. The future implementation may dispatch internally by an explicit supported schema value. It does not introduce a second exported mint, hash prefix, source-reference resolver or revision authority. Preserve the incumbent algorithm: canonical validated content excluding only `curation_revision`; all retained source/review/meaning fields still contribute. New wire-version content naturally differs. Unknown versions refuse; they do not fall back to v1.

Before implementation is accepted, pin actual legacy input bytes, encoded output, native revision and source reference from the accepted shared implementation. Then prove identical outputs after the extension for at least the frozen Robotics payload, a source-only company, a Semiconductor industrial-context payload, a null legacy evidence cell, and a correction. This is **owed native testing**, not established by the symbolic version witnesses here.

A correction into a new schema version is a new reviewed assertion with an explicit predecessor where justified. It is not a rewrite of the predecessor. Versioning does not reset observation time or make a newly disclosed fact historically knowable. Source changes, analyst interpretation changes, source-rights withdrawal and business-contract amendments remain distinct events.

No live protected current body enters public Parquet, Git, static HTML or client persistence. Native storage, K1 references, private serving and correction eligibility must support the new version before admission. Validating JSON alone does not satisfy this dependency.

## 4. Observation semantics: numbers and non-numbers are different branches

### 4.1 Non-numerical observation

The selected candidate `observation` union has a non-numerical branch. Its minimum research notation is:

```json
{"kind":"non_numeric","state":"not_disclosed","source_text":"The source reports a royalty but does not disclose its numerical terms."}
```

Closed states: `not_disclosed`, `qualitative`, `not_applicable`, `source_missing`. No numerical value, range, zero, currency or quantity basis is allowed in this branch. These states must stay distinct in the consumer. A missing number is not evidence of zero, and a source explicitly saying an amount is undisclosed is not identical to the collector failing to find it.

For a qualitative tier description, preserve the source wording. Do not manufacture numerical endpoints from adjectives, a midpoint, a distribution, an expected effective rate or a confidence percentage. Source publication/retention/rights stay in the native envelope; the small example is not a complete native assertion.

### 4.2 Exact-as-reported numerical observation

The numerical branch separates measure class, value representation, unit, economic basis and source provenance. The witness notation uses bounded base-ten decimal strings rather than accepting binary floats as though they were the source's exact decimal. It preserves lexical precision such as `5.00` without claiming that a reported decimal is an infinitely precise estimate of the real world.

Candidate classes are `physical_count`, `physical_quantity`, `financial_amount`, `financial_change`, `ratio_level`, `ratio_change`, `unit_price`, and `royalty_rate`. Physical counts are non-negative integers. Physical quantities are non-negative and may be fractional. Financial amounts/changes and relevant ratios can be signed; a negative financial result must not require dropping the row or altering its sign. A decline in a physical count is a separate change observation, not a negative count of existing objects; additional physical-change semantics need an explicit shared rule rather than misuse of a financial tag.

Point values have one decimal. Intervals have ordered lower/upper decimals and explicit inclusivity; an interval is not a point estimate. No infinite endpoints are smuggled through NaN or an enormous exponent. The first candidate bounds strings to 30 integral digits and 12 fractional digits, no exponent/plus/whitespace/grouping syntax, and explicitly separates currency scale (0, 3, 6, 9) from the value. This is a conservative wire limit, not a statement that every upstream source uses this notation. Out-of-range source values are held, not rounded into compliance.

A source-scoped unit label names the physical unit (for example, kilogram or procedure); the broad quantity class alone is insufficient. The basis includes metric, reporting entity/business scope, applicable period, denominator where relevant, gross/net status and stock/flow. A rate, ratio, percentage change or unit price needs its denominator. `gross_net` remains `gross`, `net` or null. `net product sales` belongs in the denominator/payment-base description. Source origin remains `reported`, `derived` or `target`; disclosure is handled separately. Targets never become reported outcomes because time passes.

The first royalty-rate branch admits an explicit percent in [0,100]. A fee exceeding a sales base, contingent clawback, or another more complex commercial arrangement is not forced into that percentage branch. Retain its stated mechanism or hold the unsupported structure. Do not interpret all Healthcare financial ratios as probabilities or constrain all ratios to [0,100].

Percentage and percentage-point units must remain distinct. A rate from 10% to 12% is +2 percentage points and +20% relative; neither equals +2% relative. A 20% volume change and a -10% comparable price change produce +8% revenue in the simplified multiplicative example, not +10%. These are invented arithmetic witnesses, not calibrated company models.

### 4.3 Native mapping, not a new microservice

The future shared schema expresses the version and union discriminator with closed branches. All variant-specific fields are required or forbidden by the corresponding branch. Implementation must reject a new predicate without its branch, an economic-right body with a supply predicate, unknown keys, conflicting scalar/range values and booleans masquerading as numbers. All authority flags remain literal false.

The generated witness packet also contains two complete, unstamped candidate envelopes: an economic right and a supply-status observation. Their source facts, timestamps and parties are deliberately synthetic; review disposition is held, canonical company identity and native retention remain null. They specify candidate field layout, not proof that a deployed native validator accepts it. The `economic_right` field belongs only to its economic-right predicate and `supply_status` only to its supply predicate; neither appears on unrelated assertions. The executable research witness notation below checks selected semantic decisions only. It is **not** a substitute for the closed native schema, source-envelope validation, JSON decoder limits, temporal checks, K1 parity, native mint or storage. It must not be imported by production modules. The shared owner implements and tests its own one version-aware contract.

## 5. Economic rights: one relationship can contain several cash-flow mechanisms

`REPORTED_ECONOMIC_RIGHT` describes what the source reports about a defined grant or payment obligation. Required semantic groups are:

| Group | Required meaning | Must not imply |
|---|---|---|
| Parties and direction | Source-scoped payer, recipient, grantor/grantee as appropriate; source-only parties remain usable | Resolved issuer/security, parent attribution or controlled subsidiary |
| Asset and use scope | Named source asset/platform, indication where given, territory and granted activities | Every product of either party or every geography |
| Arrangement state | Reported operative terms versus announcement, contingency or termination | Automatic closing or authorization merely because a date passed |
| Payment components | Royalty, profit participation, upfront, milestone, service fee or cost share described separately | One generic percentage applied to all revenue |
| Denominator and tier method | Net sales/profit/units and flat/marginal/whole-base/unknown method as disclosed | A midpoint or effective blended rate without the required inputs |
| Costs and losses | Which party bears which costs; whether loss participation is included, excluded or unknown | Profit-sharing automatically proves symmetric loss-sharing |
| Triggers and timing | Business-effective dates, thresholds, deductions, expiry and conditions as actually given | A new disclosure is necessarily a new economic agreement |
| Source and limitations | Native source locator, review, retention and qualification; missing material terms | Clinical success, product approval, realizable earnings or underpricing |

A single contract can contain several components. The same sales base flowing through a royalty and then a profit share is not several independent end markets. Components need source-local selectors and explicit bases; those selectors are not global product IDs. Public-company totals and look-through exposure need actual ownership, consolidation and security evidence from existing owners.

### Worked synthetic waterfall

Assume a hypothetical product has 1,000 gross sales, 200 defined deductions and 600 cash operating cost, all in the same invented period/currency. Assume a disclosed 5% royalty on net sales and, for a different participant, a disclosed 25% share of profit **after** that royalty and the defined costs. These are arbitrary demonstration assumptions, not a description of any named company.

- Net sales: 1,000 - 200 = 800.
- Royalty: 800 × 5% = 40.
- Defined profit before the second participation: 800 - 600 - 40 = 160.
- Partner share: 160 × 25% = 40.
- Commercializer residual under these assumptions: 120.

Applying the royalty to gross sales would incorrectly produce 50. Applying the profit share to sales would produce 200 instead of 40. The two correct payments happen to be equal; that numerical equality does not make their contractual bases interchangeable. This residual is not GAAP net income, free cash flow or an EPS forecast. Tax, financing, working capital, depreciation and other contract details have deliberately not been modeled.

Replace the disclosed rate with `not_disclosed` and payout is unavailable. Replace positive profit with a loss and do not allocate that loss until the loss-participation clause is evidenced. The oracle's separate negative-profit example refuses unknown loss participation; with an explicit included 25% share of a -40 base, the signed allocation is -10, not evidence of a positive cash receipt.

### Tier method can matter as much as the headline percentage

For hypothetical sales of 800, a threshold of 100, 5% below the threshold and 8% above it, a marginal schedule yields 5 + 56 = 61. A whole-base schedule at the upper rate yields 64. If the contract does not disclose which method applies, neither number is the current estimate. A scenario may label its assumptions, but the current reported-right view must not silently select one.

The valuable output is therefore not “company participates at 8%.” It is “the evidence identifies these economic rights; this denominator and tier method control the effect; these missing terms prevent a reliable payout estimate.”

## 6. Supply status: preserve scope and acquisition without inventing economics

`REPORTED_SUPPLY_STATUS` keeps jurisdiction, product/presentation identity strength, regulator status, manufacturer availability, effective/source/capture clocks, native acquisition receipt and completeness distinct. It consumes the incumbent FDA source owner rather than creating another collector or history service.

FDA's current FAQ distinguishes manufacturer availability from the agency's shortage determination. Its listed resolution definition does not measure industry excess capacity or supplier margins. The same FAQ describes time-limited retention of resolved and discontinued entries on the **webpage**; that is not a measured promise about the openFDA endpoint's history. Consequently, disappearance alone cannot be promoted into a new resolution event or complete historical knowledge. See S4; no current shortage census was acquired here.

The first native supply consumer must distinguish complete interval observations from atomic snapshots, incomplete attempts from successful empty observations, source freshness from fetch freshness, current versus resolved versus discontinued records, and missing stable source identity from a proven cross-generation deletion. A complete page sweep with matching counts still does not prove upstream snapshot isolation. Incomplete refresh leaves the earlier qualified observation available with its original dates and a separate failed-refresh state; it cannot silently replace current truth.

Nine local witnesses cover Current+Available, current and resolved records across products, resolution, discontinuation, empty success, incomplete candidate, unknown source freshness, unrecognized status and mixed jurisdictions. The oracle deliberately returns no economic conclusion for every supply-status-only input. A future economic conclusion requires separately evidenced demand, capacity, utilization, pricing, cost and contractual exposure, with an explicit attribution/inference boundary.

An unrecognized status alongside a current record may still establish that the observation contains a current record, but the aggregate must retain its unresolved status coverage. The compact witness label `MIXED_WITH_CURRENT` is not a national all-products statement. Production output needs per-record provenance and the full native missingness states, not only that small research label.

## 7. Shared URL is not a shared domain payload

The shared owner's response names `semiconductor_theme_research.v1` behind POST `/api/themes/v1/research/query` and `/evidence`. Reusing those endpoints does not authorize passing a Healthcare explanation as a Semiconductor payload or populating semiconductor-specific fields with empty values to satisfy validation.

The existing API/entitlement/rights/client owner must enroll an explicit Healthcare profile and its own domain response shape through the same transport family. Preserve the accepted Semiconductor request/response bytes and tests. Unsupported profiles return the accepted unavailable/unsupported result; no fallback to another sector, renamed Semiconductor object, new API service or unauthenticated public payload. The exact Healthcare wire response remains an owner integration gate, not an installed endpoint declared by this document.

The profile has to retain the actual five-part explanation, source participation, counterevidence and next observation. Its required evidence withdrawal invalidates the dependent current conclusion. Source-only businesses can remain attributed text; price, valuation or portfolio enrichment cannot be attached through guessed ticker identity. Public navigation can show the breadth of the twelve families without exposing current detailed private assertions.

## 8. Surgical changes to the R9 task plan

R1–R11 source files remain immutable research history. This section supersedes only the conflicting T03/T05 interpretation, not the whole plan.

| Task | Current disposition |
|---|---|
| T01–T02 / D1 | Existing FDA repair remains independent of the new contract after its own commission, source custody, acquisition and release gates. Do not wait for every later profile test. |
| T03 | Consume the frozen shared v1; require the single additive version branch for new meanings. Do not widen B's v1 enums or implement a Healthcare hash. Pin legacy native golden outputs; implement exact numeric/non-numeric semantics plus complete domain branches and intended refusals under the shared owner. |
| T04 | Consume acknowledged R4. Existing native GMI/private Research Vault, source-rights and publication identity remain authoritative. No second writer/selector. Qualification must precede real protected admission. |
| T05 | Reuse common POST transport, but require an actual typed Healthcare profile. B's response schema is not a generic medical schema. Preserve the shared auth, current source rights, errors and private headers. |
| T06 | Prove the five-part economic explanation with real reviewed sources and actual identity only where needed. The synthetic waterfall is a test/educational artifact, never a replacement for that evidence. |
| T07 | Prove real correction, unaffected cross-sector preservation and a non-metabolic case through the same profile architecture. |
| T08 | Independently adjudicate the relevant release and combined outcome. Local witness success, architecture acceptance and a native review request are not product acceptance. |

### Exact implementation-review order

1. Consume the existing shared return and this semantic specification on the original shared discussion. Preserve B's scoped execution and current source writer.
2. Accept/revise the bounded version/profile design through the existing shared and independent review responsibilities. Freeze exact wire branches, legacy reference outputs and accepted native interfaces before source changes.
3. Use the one lawful shared extension carrier after custody/acceptance reconciliation. No successor operation is silently self-originated by this research packet; no duplicate feature writer acts on #7870.
4. Write discriminating native tests first: unchanged v1 output/revision; new version refusal on an old reader; signed financial/non-negative physical separation; unknown rate; denomination/tier/loss semantics; profile mismatch; source correction and rights withdrawal.
5. Implement through the same native module/store/K1/private transport. Complete one Healthcare visible consumer and unchanged legacy visible consumer; a schema-only result is insufficient.
6. Return exact source/review/qualification identities and scope-limited proof. Then perform the pending independent Healthcare package adjudication and release the mature Fable execution packet without requiring Fable to redo the research.

The last ordering does not require independent plan review to wait for implementation; review can run now against this exact design. Implementation acceptance and plan acceptance remain distinct. New fundamental findings are reviewed, not patched around with convenience coercions.

## 9. What was tested here, and what remains unproved

`verify_r12_semantics.py` is a standalone research oracle. It constructs 46 invented witnesses and checks selected numerical, disclosure, payout, supply, version-selection and profile-selection behavior. Eight corrupted research packets must be refused. It uses no production imports, native IDs, private bodies, network or worker runtime. Its local output files are reproducibility aids, not a new canonical evidence or requirement store.

The version/profile checks are symbolic boundary checks. They do not execute the actual native validator, actual schema, API, source collector, policy or storage implementation. The numeric/financial examples are exact calculations under invented inputs, not empirical validation of a named company, commercial contract or investment rule. The small measurement checker is not a complete hostile-input security validator.

All original **60 application requirements** remain preserved and NOT_EXECUTED. The 46 research witnesses are a separate denominator, not 46 product passes and not a new claim of 106 application cases. The twelve-family coverage remains selective, not complete. The final receipt records actual executed counts and immutable file hashes; a code example being present is not a run.

Native full-payload round-trip, unchanged legacy golden outputs, rights/private admission, corrected source ingestion, typed Healthcare serving, current source-to-security bindings, browser proof, independent review and investment evaluation remain owed. The current shared branch is unmerged and no Healthcare build was started by this session.

## 10. Source register and provenance boundaries

S1. Shared owner's exact disposition, #7870 comment 5808981043: https://github.com/mastermindx-market-intelligence/macro/pull/7870#issuecomment-5808981043 . Read live in this turn. Reports accepted, held and not-yet-implemented items; not independent Healthcare review.

S2. R4 consumption, #7780 comment 5808981293: https://github.com/mastermindx-market-intelligence/macro/pull/7780#issuecomment-5808981293 . Read live. Operative prior ruling: comment 5808854275. Acknowledgment is not a private-object receipt.

S3. Shared schema at `d5b0c00d772e5034ed8c109b5990b1f3b91e0be5`, `contracts/theme_graph/curation_assertion.v1.schema.json`, blob `ff3928f0c54aa164ef8283d9da45af67e6a0d971`: https://github.com/mastermindx-market-intelligence/macro/blob/d5b0c00d772e5034ed8c109b5990b1f3b91e0be5/contracts/theme_graph/curation_assertion.v1.schema.json . Selected measurement/authority source read; no full native execution.

S4. FDA, Frequently Asked Questions about Drug Shortages: https://www.fda.gov/drugs/drug-shortages/frequently-asked-questions-about-drug-shortages . Read 24 September 2026. Relevant sections: national scope; status definitions; manufacturer availability; webpage retention of resolved/discontinued entries. No PDF, patient information or live drug census acquired.

S5. Python official Decimal documentation: https://docs.python.org/3/library/decimal.html . Read 24 September 2026. Supports exact decimal construction from text and explicit arithmetic context; does not prescribe our data model or validate the economics.

S6. JSON Schema official conditional-validation documentation: https://json-schema.org/understanding-json-schema/reference/conditionals . Read 24 September 2026. Supports explicit discriminator/required-branch validation; the selected wire version is our design choice, not a JSON Schema standard for finance.

The original company/clinical research remains in R1–R6 and is not repeated or freshly revalidated here. Current consumer admission must use its actual source rights, retention, time and review evidence; a public research document is not a native source-retention receipt.
