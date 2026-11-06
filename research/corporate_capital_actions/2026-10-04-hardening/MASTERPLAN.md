# Commission 13 — Corporate Capital Actions & Share-Count Intelligence

## Hardened research masterplan · 2026-10-04

**Disposition: recommend acceptance of the research architecture, with construction and publication conditional on incumbent gates. Research only; no implementation or financial authority is granted.**

This is a complete replacement research recommendation for the supplied Commission 13 report, not a replacement of the existing Capital Structure V2 program. [AUDIT_AND_RECENSUS.md](AUDIT_AND_RECENSUS.md) records the corrections and evidence limits. [SOURCES.md](SOURCES.md) provides primary sources and exact repository references. [VALIDATION.md](VALIDATION.md) provides the proposed test specification and worked arithmetic oracles. Numerical gates, budgets and examples below are **proposals**, not observed production performance.

---

## A. Executive conclusion

### Build an accounting-grade capital history, not a new score

Mastermind should finish the **existing capital-structure-intelligence owner's point-in-time capital event/state capability**, adding typed economic movements, a defensible security-specific share basis, and transparent capital-structure scenarios. The strongest initial business justification is denominator correctness, explainability, solvency context and prevention of false inference. Predictive alpha is a separate hypothesis that must earn promotion.

The minimum useful product answers:

1. What was announced, legally authorized, executed, delivered, canceled or corrected?
2. What share/cash/debt/preferred claim actually changed, and what remains only capacity or contingency?
3. At a particular knowledge cutoff, what reported share count is defensible, for which security class, on which adjustment basis, and how incomplete is the bridge from that observation to today?
4. Under explicitly dated financing and settlement assumptions, how could outstanding shares, cash, debt, common EPS and the original shareholder's claim change?
5. What new information survives controls for existing payout, valuation, earnings, leverage, price and ownership evidence?

The answer should remain inspectable by mechanism. Neither a new opaque dilution score nor automatic ranking/sizing/Prophet authority belongs in this program.

### The hardening changes the plan materially

The original owner choice was sound. Its execution sequence and several calculations were not sufficiently safe. This version makes six corrections central to acceptance:

- **Respect existing phase gates.** The current workstream still records W2C/W2D as `BUILT_NOT_PROVEN`, holds W3/W4, and puts share basis/corporate actions in W6 after W4. This commission cannot authorize a parallel P0 route around that dependency. [R02](SOURCES.md#R02)
- **Count economic movements exactly once.** Treasury acquisition reduces outstanding shares; later retirement of the same treasury shares does not reduce them again. Employee options and SBC cannot occupy overlapping bridge buckets. ASR initial and final deliveries are incremental legs, not repeated total repurchases.
- **Separate actual shares from accounting denominators.** Reported outstanding shares, weighted-average basic shares, diluted-EPS equivalents, registered shares, authorized shares and scenarios are different objects. Public-float dollars are not float shares. [R04](SOURCES.md#R04), [S04](SOURCES.md#S04)
- **Separate actual-system history from public reconstruction.** An old filing fetched and parsed today is not evidence that Mastermind possessed the extracted signal years ago. Actual as-run, public historical reconstruction and latest-restated views must never be blended.
- **Couple financing claims and cash.** Issuance adds claims and proceeds; debt refinancing has draw and repayment legs; restricted cash is not automatically available. Enterprise recovery is not original-shareholder recovery. Reuse existing `capital_need` and the adjacent recovery owner rather than rebuilding them. [R09](SOURCES.md#R09), [R10](SOURCES.md#R10)
- **Make proof falsifiable.** Reconciliation residuals, abstention coverage, finite-sample error bounds, correction replay and simple forecast baselines precede return prediction. Scenario envelopes are not calibrated probability intervals merely because they have low/base/high labels.

### What should be accepted now

Accept the economic semantics, reuse map, proposed validation program and the bounded follow-on commission in Section L. Do **not** infer that research acceptance closes W2, enables default-off share publication, accepts a `company_event.v1` migration, licenses vendor content or promotes evidence to trading use.

**Priority:** high for accounting and risk correctness; conditional and unproven for incremental market prediction. The smallest valuable first slice is a transparent **reported-share anchor plus known changes and unresolved residuals**, not a falsely precise real-time fully diluted denominator for every issuer.

---

## B. Current-state census and reconciliation with existing programs

### B1. Fresh repository pins

| Estate | Resolved repository | Default branch | Audit revision | Protection observed |
|---|---|---|---|---|
| Mastermind | `mastermindx-market-intelligence/Mastermind` | `master` | `521720b09be2921e996d9396b522b1c4ca62041c` | true |
| Capital Structure / macro | `mastermindx-market-intelligence/macro` | `main` | `79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f` | false |
| Charting / terminal | `mastermindx-market-intelligence/mastermind-terminal` | `master` | `1c708450187755160e1a5889b69598a2fcb1f0d1` | true |
| Research Vault | `mastermindx-market-intelligence/executive-dr-vault` | `main` | `ea422c92bd29800d1f7fb3ae850236cc44d8c890` | false |

These are observations, not durable promises about branch heads. Repository identity/protection came from current metadata, not local-directory guesses. No private Vault contents are published. Same-pin Mastermind bootstrap/source law was consumed. [R01](SOURCES.md#R01)

The macro audit pin is one commit after the original report's `d2904d45...`; the four changed paths concern China THS collection/CI, not Capital Structure. The capital-state findings below are therefore mostly **missing audit depth, semantic corrections and existing unclosed dependencies**, not invented new implementation since the original report. [R12](SOURCES.md#R12)

### B2. Capability census

| Capability / owner | Current evidence | Defensible status for this commission | Consequence |
|---|---|---|---|
| Capital Structure evidence identity, retention and event publication | Current workstream records W1 and W2A/W2B natural production receipts | Recorded `PROVEN_LIVE` for those bounded historical capabilities; current runtime not re-certified | Preserve occurrence/byte identity and closed-bundle append rules |
| W2C incremental document terms and W2D discovery clocks | Merged #6415/#6424, current workstream still awaits joint natural proof | `BUILT_NOT_PROVEN`; W2 in progress | No invented proof run and no bypass to held W3/W4 |
| Company Facts direct observations | Existing v1/v2 contracts, truth/materialization/publication machinery | Built substrate; publication described as default-off/unprovisioned | Do not describe it as a live selected common-share denominator |
| Current selected security-specific share basis | Observation contract preserves ambiguity; product capability gaps remain | Not established as a complete authoritative consumer product | Add an owner-approved selector/read model only after prerequisites |
| Registration lifecycle and instrument candidates | Existing modules and contracts under incumbent owner | Code exists; complete remaining-capacity/instrument projection not established | Extend, do not replace source/identity/registration owners |
| Capital allocation interpretation | Existing `engine/capital_allocation.py` | Bounded existing calculation layer; not canonical movement ledger | Feed better facts underneath it; retain interpretation ownership |
| Cash/funding need, runway, maturities | Existing `capital_need.py`, `cash_runway.py`, `debt_maturity.py` | Native adjacent source/calculation owners | Capital-action legs feed these owners, not a new liquidity model |
| Mastermind held-risk | Deterministic `solvency_dilution` lane and missing filing-artifact sub-check | Existing proxy consumer; canonical cutover not established | Shadow adapter, no portfolio policy change |
| Mastermind fundamentals | PIT-row selection and shareholder-yield factor code | Existing code; underlying historical source receipts not re-certified here | Preserve experiment law; compare missingness and denominator semantics |
| Original-equity recovery | PR #8308, head `446ffd0f...` | Open draft, `BUILT_NOT_PROVEN`, not merged | Reuse its boundary; do not duplicate its scenario authority |
| Fresh system observability | Static census still generated July 16 | Dated generated inventory | Do not present its job/flag counts as today's runtime census |

Sources: [R02–R11](SOURCES.md). None of these classifications asserts that tests, a schema, a successful collection, and a currently served user experience are interchangeable.

### B3. Gaps that must be closed, rather than new projects launched

The gaps are typed share/cash/claim movements; cross-document transaction deduplication; current-class and adjustment-basis selection; overlap-safe share bridges; program constraint accounting; correction-safe state queries; explicit scenario assumptions; and consumption by existing risk/fundamental owners.

There are two additional concrete audit findings. First, Mastermind's shareholder-yield path converts missing repurchases/dividends to zero. That may be a deliberate legacy modeling convention, but it is not canonical evidence of no activity. Second, held-risk documents an `ni/debt_lt` proxy; it must not become a silently relabeled true interest-coverage ratio during integration. Both require discrepancy reporting and a separately approved consumer-policy decision, not an unannounced cleanup. [R06](SOURCES.md#R06), [R07](SOURCES.md#R07)

The original report's September 26 telemetry and October 1 adapter-review date remain **prior-report observations**, not newly reproduced runtime truth. An expired review date triggers reconciliation; it does not approve migration to `company_event.v1`. The current workstream explicitly forbids silently claiming that contract. [R02](SOURCES.md#R02)

The wider repository scan resolved actual terminal/Vault identities and inspected relevant macro code/docs/test subtrees. It did not certify every branch, every consumer, all private research or a live API response. Original assertions about a mature analyst-revision history, dynamic subtheme identity and institutional-flow history are not promoted to fresh findings in this commission. Where such controls are unavailable, the empirical design records missingness rather than fabricating them.

---

## C. State-of-the-art research and implications

### C1. Institutional design separates issuer economics from operational event processing

Issuer filings are primary evidence for legal/economic terms; exchange and depository messages are useful for operational dates, options and lifecycle updates; normalized vendors can improve coverage and reconciliation. None is universally authoritative for every field. A conflict between a filed consideration ratio and an operational effective-date update is not resolved by blindly choosing one whole record or the latest ingestion timestamp.

The proposed system therefore adjudicates **claims at field/event-version level**, retains contradictions, and records why a source was preferred for that particular question. An event can have reliable cash consideration but unresolved effective date, or a reliable exchange effective date but incomplete issuer instrument terms. [S01](SOURCES.md#S01), [S05](SOURCES.md#S05), [S06](SOURCES.md#S06)

Current vendor diligence changes the original recommendation. S&P's MCA catalogue explicitly marks PIT as absent; it is not a demonstrated historical-vintage feed. Nasdaq's current product page describes history from 1999, while an older notice gives more granular 1998/1999 starts. Product-specific archive manifests, not the oldest marketing date, must control research admission. [S07](SOURCES.md#S07), [S08](SOURCES.md#S08)

### C2. The research literature argues for mechanisms and strong controls

| Research | What can be carried into this design | What cannot be inferred |
|---|---|---|
| Boudoukh et al., payout yield | Compare against total and net payout, not just dividends or a buyback indicator | Historical results establish neither present alpha nor advantage over Mastermind's existing factors |
| Pontiff–Woodgate, issuance | Test issuance information separately by era and issuer characteristics | Issuance is not universally bearish and repurchases universally bullish |
| Bens et al. and Larcker's discussion | Distinguish award dilution, EPS incentives and alternative explanations | An observed pattern proves neither managerial intent nor destruction of value |
| Almeida–Fos–Kronlund | Local EPS-threshold evidence motivates explicit financing/investment channels | A local causal design is not a broad causal verdict from an ordinary event study |
| Innovation Under Pressure | Innovation responses can differ by prior efficiency and resource allocation | Lower spending or higher EPS alone reveals neither improved nor impaired innovation |
| El Ghoul et al. | Funding source, financial maturity and repurchase persistence matter | All repurchases crowd out productive investment |

Primary references and precise review depth are in [A01–A07](SOURCES.md). One publisher article's substantive text was reviewed; several other entries were available only as primary abstracts/introduction or coauthor explanation. Those limits are explicit. No paper's reported coefficient is imported into Mastermind, and no empirical replication is claimed.

### C3. A ledger is not itself a causal or forecasting model

The accounting question is whether an observation changes an issuer's shares or claims. The forecast question is whether a model improves a future denominator or funding prediction. The pricing question is whether that information was unexpected and not already absorbed by prices. These require different outcomes, baselines and gates.

An announcement may be largely priced before Mastermind's first usable receipt. Later disclosed execution may improve historical accounting without creating a new trading opportunity. A buyback financed by excess cash and one financed through constrained borrowing can have similar share arithmetic but different balance-sheet implications. A recapitalization can improve survival while harming the old common-equity cohort. The architecture must preserve these distinctions rather than force one sign.

### C4. Regulatory and accounting evidence must retain time and scope

The SEC's vacatur announcement and actual Item 703 structure support monthly disclosed execution and authorization fields, not an assumed continuous daily public repurchase tape. A current Company Facts response is a delivery object; it is not proof that the same parsed facts were available historically. [S01–S03](SOURCES.md)

Filed ASR examples show separate initial treasury-share delivery and forward settlement. Filed convertible examples include cash-only and cash-principal/net-share settlement. Accounting adoption can also revise comparative columns. These justify instrument-specific, versioned semantics; they do not substitute for qualified accounting review of every jurisdiction and instrument. [I01–I04](SOURCES.md)

---

## D. Source landscape and procurement recommendation

### D1. Comparative source matrix

Cost classes are **planning categories**, not verified prices: free public access still incurs collection/review costs; commercial costs require a quote including identifiers, storage, derived use and redistribution. No purchase is recommended under this commission.

| Source | Coverage / history | Latency | PIT quality | Corrections | Rights / cost class | Best use |
|---|---|---|---|---|---|---|
| SEC filings, submissions and XBRL | U.S. issuer evidence; depth varies by form, structured taxonomy and issuer | Public APIs plus nightly bulk; own receipt lag matters | Strong source-based potential with original version/availability; current aggregate response alone insufficient | Amendments, source changes and parser changes must retain separate lineage | Public access, fair-access obligations; filing content is not blanket public-domain material / free access | Economic terms, reported shares, program and execution evidence [S01–S04] |
| Issuer investor-relations releases | Announcements and terms before or alongside filings; archive completeness varies | Event-driven; pages can change | Conditional on retained publication/version evidence | Silent edits and removed releases possible | Per-site content/use terms / public access | Candidate discovery and corroboration, not unverified historical timestamps |
| SEC dissemination subscription | Dedicated filing dissemination candidate | Product-specific, not tested here | Unknown until received-message and historical retention evidence | Must prove original/corrected message history | Subscription / quote required | Evaluate only if measured EDGAR polling delay is economically important |
| DTCC CA 20022 | Depository operational distributions/redemptions/reorganizations | Near-real-time product description | Operational lifecycle strength; research as-was archive unproved | Require samples of amendments/cancellations and receive timestamps | Licensed, including derived/persistent use / commercial | Operational reconciliation and difficult events [S05] |
| NYSE Market Event Feed | Exchange event information and historical query product | Real-time API description | Historical query is not automatically notice-vintage PIT | Require sequence/revision/retraction semantics | Exchange agreement / commercial | Effective dates/status and listing transitions [S06] |
| Nasdaq Daily List | Current page: history from 1999; older file-specific starts differ | Scheduled/advance event notices | Retained releases can support operational timing | Exact revised-file behavior must be tested | Licensed, identifier-version choices / commercial | Splits, dividends, symbols and listing events [S07] |
| S&P MCA | Global operational normalized actions; catalogue history 2003/significant 2010 | Intraday | Catalogue explicitly says PIT No | Operational updates do not prove historical as-was archives | Proprietary / commercial quote | Shadow reconciliation only unless a separate qualified vintage product is shown [S08] |
| LSEG | Broad global events; earliest history is product/field-specific | Varies by region/product | Unverified event-vintage suitability | Need exact update and deletion audit samples | Proprietary / commercial quote | Global normalization after benchmark [S09] |
| Bloomberg Data License | Corporate-action content; package scope must be specified | Delivery/product-specific | Do not transfer a PIT claim from adjusted financials to event notices | Unverified exact-event revisions | Proprietary / commercial quote | RFP candidate, not presumed historical truth [S10] |
| FactSet | Candidate corporate-action/price content; relevant schema not inspected | Unknown | Unknown | Unknown | Proprietary / commercial quote | Diligence candidate only [S11] |
| CRSP | Historical securities, delistings, returns and share data; market-specific history | Research releases, not assumed live | Useful benchmark; event as-was and publication vintages must be separately established | Inspect release/vintage methodology | Institutional license / commercial-academic | Survivorship-safe return and identity benchmarks [S12] |
| Compustat / CRSP-Compustat links | Financial history and historical security/company links | Periodic/product-specific | Current restated fundamentals are not automatically as-was | A revision/vintage product requires explicit qualification | Product entitlements / commercial-academic | Fundamental cross-check and benchmark links, not raw event truth [S12] |
| OpenFIGI | Identifier mapping, not corporate-action economics | API | Mapping snapshot does not supply effective-dated economic history | Retain observed mapping changes | Public mapping service; other identifier rights separate / free access | Optional identity bridge, never canonical event authority [S13] |
| Specialty equity-plan / governance data | Potential awards, plan/governance enrichment | Not investigated at sample level | Unknown | Unknown | Proprietary / quote required | Defer until a measured employee-equity coverage gap justifies it |

Source IDs resolve in [SOURCES.md](SOURCES.md). Unknowns are intentional. Broad coverage claims have not been treated as independently audited counts.

### D2. Form and mechanism qualification docket

Start with retained sources already admitted by the incumbent collector. Proposed additions require owner approval and family-specific tests, not an unrestricted form crawl.

| Mechanism | Candidate primary evidence to qualify | What a filing does not establish by itself |
|---|---|---|
| Repurchases/ASRs | Periodic equity notes, Item 703 tables, material agreements and exhibits | Announcement or authorization does not prove execution; cash total may include unsettled amounts or fees |
| ATM/follow-on | Registration statements, prospectus supplements, sales/underwriting agreements, periodic actual-sales disclosures | Registered maximum is not issued shares; a selling-holder resale is not issuer financing |
| SBC/options/RSUs | Award rollforwards, plan/proxy documents, S-8 registration and periodic equity notes | Grant expense, plan capacity and registration are not share issuance |
| Converts/warrants/preferred | Indentures/designations, pricing terms, amendments, settlement notices | Face amount and conversion rate alone may not determine actual shares or accounting dilution |
| Debt/tender/refinancing | Credit agreements, issuance/redemption notices, offer/exchange documents, maturity notes | New proceeds without repayment/redemption legs misstate cash and leverage |
| M&A/spin | Merger/combination filings, S-4/F-4 where applicable, separation documents, close/distribution notices | Announced ratio does not prove closing or shareholder entitlement completion |
| Dividends/splits | Board/issuer announcement plus qualified exchange operational notice | Record, ex, effective and payment dates are not interchangeable |

S-8, S-4/F-4 and further prospectus families were identified as gaps in the original report's dated policy telemetry. This pass does not falsely certify their present collection coverage. The follow-on owner must produce a form-by-family coverage manifest before expanding them. Foreign issuers and jurisdictions need their own form/accounting mapping rather than a U.S. template with renamed fields.

### D3. Vendor bake-off contract

Use a common, blinded adjudicated event set with ordinary and adversarial cases, including corrected, withdrawn, delisted and acquired issuers. Require the vendor to return the original notice and every subsequent version, each timestamp's meaning/timezone, identifiers, availability lag, raw-to-normalized trace, field-specific history and an explanation of absent records.

Rights diligence must cover retained originals, historical replays, model inputs, derived artifacts, customer display, redistribution, third-party identifiers, post-termination retention, region restrictions and deletion obligations. A vendor refusing the required historical/derived use is not eligible merely because its dashboard is accurate today.

Compare against the existing public-source workflow on incremental event recall, material-term precision, latency distribution, revision replay, manual review burden and total cost per usable issuer-quarter. Buy only a demonstrated improvement. No vendor gets independent decision authority, no vendor event ID replaces internal identity, and no proprietary corpus is copied into research documentation.

---

## E. Canonical data model and temporal semantics

### E1. Minimum logical model; reuse existing physical contracts

The following are **logical requirements**, not permission to create five new services, stores, identity authorities or public schema names. The implementation owner must map them onto approved `capital_structure.*` contracts or an explicitly accepted successor. Existing observation IDs, source receipts, manifest relationships, publication heads and correction machinery remain authoritative. [R02–R05](SOURCES.md)

| Logical object | Minimum purpose | Minimum content |
|---|---|---|
| Source claim/observation | What a retained source version says | Receipt/hash/span; issuer/security scope; raw value/unit; source version; extraction version; availability and rights |
| Economic event and movement legs | What occurred, distinct from its repeated descriptions | Stable event identity; program/instrument links; family/subtype/stage; affected claims; signed share/cash/debt legs; evidence; constraints and contradictions |
| Program/instrument state | Continuing capacity, obligation or contingent claim | Effective/knowledge intervals; authorization/terms; executions already consumed; settlement alternatives; expiry, covenants, seniority and constraint groups |
| Selected share basis | Defensible denominator at a requested cutoff | Selected direct observation; class/basis; competing observations; observed date; bridge coverage; unexplained residual; no fabricated currentness |
| Capital snapshot/scenario | Recomputable consumer projection | Knowledge cutoff, target date, mode, exact source generations, deterministic policy versions, state, scenario assumptions and coverage/authority flags |

A new source observation may support an existing event without creating a new economic occurrence. An event's identity must not change because it was re-fetched, a different mirror was used, a query cutoff changed or a parser's phrasing changed. Conversely, an amendment changing economic terms is a new version or typed amending event, not an overwrite.

### E2. Identity and scope

Use the existing internal issuer/security/instrument/program/event identities. CIK identifies the reporting entity, not every listed class or economic security. Ticker is an effective-dated alias, never the join key for mergers, reorganizations, class conversions or spin-offs. ADR/GDR ratios, share-class voting/economic rights and old/new security lineage need explicit mappings before quantities can be compared.

A Company Facts observation marked not-security-specific or ambiguous must not be coerced into a class-specific denominator. The selector can return `AMBIGUOUS_CLASS`, `REPORTED_ISSUER_TOTAL_ONLY` or `UNAVAILABLE`. These are useful truthful outputs, not implementation failures to conceal. [R04](SOURCES.md#R04)

Do not insert query `as_of`, ingestion clocks or whole-snapshot metadata into immutable economic identity. Do include cutoff, target time, scenario version, adjustment basis and source-generation set in the **derived snapshot cache key/hash**. This preserves both idempotent truth identity and reproducible read models.

### E3. All required clocks, with separate public and system eligibility

| Field | Semantics and rule |
|---|---|
| `event_time` | Economic/legal occurrence time or interval; precision and timezone required; announcement may be a different event |
| `as_of` | Requested knowledge/materialization cutoff, not immutable fact identity |
| `observed_at` | First observed receipt of this source version by the relevant collection process |
| `source_public_available_at` | Earliest defensible public availability for these exact bytes/terms; may be unknown or interval-censored |
| `known_at` / `available_at` | Eligibility time under the explicitly named replay mode; never a convenient period-end date |
| `ingested_at` | Durable retention of the exact evidence/version |
| `canonical_available_at` | First accepted availability of this canonical version to the consumer, including required validation/publication steps |
| `effective_from` / `effective_to` | Economic/legal validity interval, represented as half-open; source-specific uncertainty preserved |
| `correction_generation` | Immutable correction lineage under the existing owner's ordering, with source correction and parser/policy version distinguished |

For **actual-system replay**, an observation is eligible only after the required source version, canonical artifact and consumer availability existed. Preserve the existing canonical retention-clock law; an earlier public press release is not permission to backdate canonical `first_known_at`. A fresh extraction today cannot claim historical system availability simply because its source was filed years ago. [R02](SOURCES.md#R02)

For **public historical reconstruction**, retained original filing/notice versions may support a hypothetical strategy with a declared availability assumption and processing lag. The mode must say that the current extraction algorithm was applied retrospectively. Report source coverage, survival of original bytes, precision of publication clocks and latency assumptions. Do not call this an actual as-run Mastermind backtest.

A **latest-restated convenience view** may aid reconciliation but is ineligible as a historical feature source. A correction learned after cutoff T must not affect an as-run snapshot at T. A later correction can change today's interpretation of a past economic state; it cannot change what an earlier decision knew.

Date-only disclosure is not midnight availability. Retain uncertainty or use a deliberately conservative session rule in reconstruction mode. Missing availability remains unavailable for strict replay. A generic period-end-plus-45-days approximation is not accepted as an exact clock.

### E4. Canonical movement legs and conservation rules

Represent a transaction as non-overlapping signed legs with explicit unit, currency, security/instrument, economic date/interval, certainty and source. The minimum dimensions are:

`issued_common_delta`, `treasury_common_delta`, `outstanding_common_delta`, `cash_gross_in`, `cash_out`, `fees_and_taxes`, `debt_principal_delta`, `debt_carrying_value_delta` where known, `preferred_claim_delta`, and `contingent_claim_delta`.

These are accounting/reconciliation dimensions, not a claim that the ledger reconstructs the full general ledger. Unknown legs are unknown, not balancing plugs. Cash and principal values must not be interchanged; a debt discount or issuance cost can make carrying value differ from face amount.

For a single common class, on one basis:

`Outstanding = Issued − Treasury`.

| Action | Issued delta | Treasury delta | Outstanding delta |
|---|---:|---:|---:|
| Buy 8 shares into treasury | 0 | +8 | −8 |
| Retire those same 8 treasury shares | −8 | −8 | 0 |
| Issue 5 new shares | +5 | 0 | +5 |
| Reissue 3 treasury shares | 0 | −3 | +3 |

A split changes the unit basis of eligible quantities; it is not evidence of economically dilutive financing. Treasury retirement is not a second buyback. Employee-share withholding must be represented consistently as either a net delivery or gross delivery plus return legs, never both. Shareholder secondary sales have zero issuer share delta unless a distinct exercise/conversion/primary issuance actually creates shares.

### E5. Lifecycle semantics by family

| Family | Required distinctions and conservative treatment |
|---|---|
| Repurchase | Board capacity, public announcement, amendment, period execution, delivery/settlement, expiry and termination. Unannounced/non-program purchases remain separate from program consumption. |
| ASR | Agreement, cash funding, initial shares delivered, forward component, final incremental shares or cash adjustment. Never add initial shares to an already-total final number. |
| ATM | Shelf/registration parent, sales agreement, authorized program capacity, actual sold shares/gross proceeds/fees, amendments/termination. Shared shelf limits constrain multiple programs. |
| Follow-on/secondary | Primary versus selling-holder shares, price, underwriting/fees, exercise of overallotment option, pricing versus closing. Classify actual issuance, not the headline deal total. |
| Employee equity | Plan capacity, grants, unvested/outstanding awards, vest/exercise, cash exercise proceeds, withholding, forfeiture/expiry, treasury reissue versus new issue. Expense is a separate financial fact. |
| Warrants/converts | Outstanding claim, exercise/conversion formula, trigger conditions, repricing/anti-dilution, cash versus share settlement, call/expiry, amendments. Unsupported exotic formulas are deferred. |
| Debt | Commitment versus draw, gross proceeds, costs, face/carrying value, secured priority, repayment, refinance, maturity, covenant changes and contingent obligations. |
| Tender/exchange | Issuer repurchase versus third-party offer, election window, participation/proration, conditions, results and settlement. Announcement alone cannot reduce shares. |
| M&A | Acquirer/target identities, cash/stock mix, fixed ratio versus collar, contingency, financing and fees, closing/termination, old-to-new security entitlement. |
| Spin-off | Parent and child identities, distribution ratio, operational dates, debt/cash allocation where disclosed, when-issued securities, fractional treatment. Parent O/S need not change merely because value is distributed. |
| Dividends | Declaration, type, currency, amount, ex/record/pay dates, cancellation/change, cash versus stock or elective distribution. Price adjustment is not payment or return by itself. |
| Preferred | Liquidation preference, dividend/arrears, cumulative/participating features, conversion, redemption/call and ranking. Preferred issuance is not common dilution unless/when terms imply it. |
| Split/class transformation | Exact ratio, direction, legal effective date, class mapping, fractional/cash-in-lieu treatment and evidence of already-adjusted comparative values. |

### E6. Capacity is a constrained state, not a forecast

Do not add shelf, ATM, authorized common stock and resale registration into one dollar capacity total. They constrain different actions and often overlap. A scenario must satisfy all applicable, source-qualified constraints: legal shares authorized, active registration coverage, program limits, applicable rolling issuance restrictions, shareholder approvals and contractual conditions.

Keep `reported_remaining_capacity`, `derived_remaining_capacity`, `constraints_unknown`, `capacity_unit` and `constraint_group_id` distinct. If an issuer gives an aggregate remaining amount for several programs but program attribution is unknown, retain an aggregate observation and do not fabricate a per-program rollforward. Expiry or withdrawal of registration does not retire outstanding shares.

Legal availability and economic feasibility are also separate: being permitted to issue does not mean an issuer can raise that amount at the modeled price. A financing-availability probability remains outside the P0 ledger and belongs only to a separately admitted model under existing owners.

### E7. Selection and reconciliation algorithm

For requested knowledge cutoff T and economic target date U:

1. Filter observations by replay mode, rights, accepted version and T. Resolve class/unit/basis compatibility before comparing values.
2. Group repeated disclosures and amendment lineages; retain incompatible candidates rather than averaging them.
3. Select the defensible **reported anchor**, prioritizing direct class-compatible evidence and economic observation date, with a versioned tie-break policy. Filing recency alone does not make a stale economic observation current.
4. Bridge only movements demonstrably after the anchor and through U. Exclude actions already contained in that anchor. Interval totals crossing the anchor are not arbitrarily allocated to days.
5. Normalize comparisons to an explicit basis once. A later comparative column already reflecting a split must not receive the split again.
6. Reconcile against the next direct observation when it becomes eligible. Expose the signed residual and explanation status; never disguise the residual as inferred SBC or an `other` issuance fact.
7. Publish the anchor's date, bridged-through date, coverage and unresolved components. Emit `estimated_from_reported_anchor`, not `current_observed_shares`, unless the required evidence genuinely supports currentness.

Every selection has an explanation, eligible competing observations, exclusion reasons, deterministic policy version and source generations. This can be useful with incomplete coverage without pretending the missing activity is zero.

---

## F. Derived intelligence and deterministic-first computation

### F1. Non-overlapping share bridge

For security class c and basis b, use an admitted reported anchor O0 and **unique incremental movement legs**:

`O(c,b,U | T) = adjust(O0,b) + Σ unique outstanding-share deltas after anchor through U known by T`.

The bridge groups movements for display into repurchases, primary/ATM issuance, net employee delivery, non-employee warrant/conversion settlement, M&A/class transformations and explicitly evidenced other actions. Categories are mutually exclusive at the movement level. An employee option exercise cannot count again in SBC; one convertible cannot be both fully stock-settled and cash-principal/net-share-settled in the same scenario.

When execution timing is only a disclosed month or quarter, preserve the interval. Exact daily weighted-average shares cannot be reconstructed by inventing transaction dates. An interval-based bound or unavailable daily bridge is preferable.

### F2. Three denominator products, not one “fully diluted” number

**Reported outstanding shares** is a dated stock of legal shares. **Projected outstanding shares** is a conditional future state. **Weighted-average basic/diluted shares** is a period accounting denominator with its own eligibility and weighting rules. Store and label all three separately.

For a fully specified basic-share path over a period of D days:

`WA_basic = Σ(O_j × duration_j) / D`.

For illustration, 100 million shares for 30 days followed by 90 million for 60 days yields a 90-day weighted average of 93.333333 million, not 90 million. If dates are unknown within intervals, compute defensible bounds rather than report the exact illustration as a reconstruction.

Diluted-EPS calculations require a reviewed accounting-policy module, appropriate numerator adjustments, loss/anti-dilution treatment, participating securities and instrument-specific settlement terms. The familiar treasury-stock expression for a simple eligible option, `N × max(0, 1 − K/P_avg)`, is an illustrative accounting-equivalent calculation under simplifying assumptions, **not** actual issued shares and not a universal employee-award formula. Actual exercise can issue N shares and bring in exercise cash. Unknown unrecognized compensation, tax or contingent terms must not be silently assumed away.

For a stylized convertible principal F, conversion price K and settlement price P: all-share settlement might deliver F/K shares; a contract requiring principal in cash and only the positive spread in shares might deliver `max(0, F/K − F/P)` shares and require F cash. These are conditional contractual illustrations, not a general GAAP diluted-EPS engine. Historical filed examples demonstrate the distinction; exact treatment must follow admitted terms and accounting policy. [I03](SOURCES.md#I03)

### F3. Cash and claims must move together

A funding path should expose dated gross financing proceeds, fees/taxes, cash repurchase/dividend payments, debt repayments and new outstanding claims. Distinguish cash committed, accrued and settled. Reconciliation across cash-flow statements and event legs must detect overlap rather than add both representations.

For an explicitly bounded scenario:

`Cash_U = Cash_0 + net operating/investing scenario flows + financing cash inflows − financing/distribution cash outflows`.

`Debt_face_U = Debt_face_0 + draws/issues − principal repayments − principal legally converted/extinguished`.

Restricted or trapped cash remains separately classified. Net debt uses the approved available-cash definition; a missing restriction assessment cannot default to all cash being spendable. Maturity/coverage/runway calculations stay under their native owners. Do not compute a meaningless net-debt/EBITDA ratio when the required denominator or economic interpretation is invalid. [R09](SOURCES.md#R09), [R10](SOURCES.md#R10)

### F4. EPS effects: separate arithmetic accretion from value creation

Let NI_common,0 already mean income attributable to common holders under an explicit basis. A denominator-only comparison holds that numerator fixed and changes only the appropriate period denominator:

`EPS_denominator_only = NI_common,0 / WA_basic_or_diluted_scenario`.

A pro-forma common-income bridge then adds incremental operating earnings and subtracts relevant financing costs, lost positive interest income on cash spent, incremental preferred claims on income, transaction costs and other explicitly modeled effects. Tax shields apply only where the assumption is justified. Do not subtract preferred dividends twice if the starting numerator already excludes them. Do not add “lost interest” with a positive sign.

Report denominator-only effect, numerator/financing effects and combined effect separately. If no admitted earnings baseline exists, publish the share-denominator change and conditional algebra, not an invented forward EPS forecast. Historical analyst-revision data must come from its qualified owner, not be fabricated to fill this feature.

EPS accretion alone is not evidence of investment quality or fair value. In loss periods, denominator changes and anti-dilution accounting can behave differently. A debt-funded buyback can shrink shares and worsen liquidity at the same time.

### F5. Ownership, float and original-holder outcomes

Ownership percentage is meaningful only after matching the numerator and denominator's security class, economic date and share basis. A holdings report learned later describes a past holdings date; dividing it by today's share count does not recover historical ownership. Changed percentages do not prove trading flows.

Do not equate `dei:EntityPublicFloat` with freely tradable shares. Keep `public_float_market_value`, source date, affiliate convention and currency separate from a qualified `free_float_shares` observation. Dividing that old value by today's price is not a valid float reconstruction. [S04](SOURCES.md#S04)

For a continuing original holder, report the change in the holder's proportionate claim and any cash/new-security entitlement. Mergers/spins require an entitlement basket, not simply a replacement ticker. Reorganizations can cancel old common equity while a successor business continues. The existing Cycle recovery work is the adjacent owner for conditional recovery analysis; this ledger should supply inputs and lineage rather than copy its engine. [R09](SOURCES.md#R09)

### F6. Supply/demand and liquidity descriptors

Useful observations include executed repurchase shares and dollars, net common-share issuance, primary issuance relative to starting shares, the proportion of issuance freely tradable under known constraints, authorization utilization, debt/refinance cash consequences, and divergence between repurchase spending and realized share-count reduction.

`EquitySupplyDays = qualified incremental tradable shares / contemporaneously available average daily share volume` can describe supply scale. The same construction can describe disclosed repurchase demand. The volume window, session calendar and adjustment basis must match; missing or unreliable volume makes the measure unavailable. These ratios are not price-impact coefficients. Issuer repurchases may be disclosed well after the trades occurred, and dealer hedging or shareholder secondary sales must not be invented from the corporate-action label.

Keep dollar payout measures and actual share movements separate. `(repurchase dollars − SBC expense) / market cap` is an interpretation of cash/accounting burden, not a physical net-share count. Preserve that distinction when improving the existing allocation consumer. [R10](SOURCES.md#R10)

### F7. Scenarios and expectation deltas

Publish a committed/observed continuation, an explicitly parameterized central scenario where support exists, and feasible stress alternatives. A missing base forecast is acceptable. Do not label an arbitrary midpoint calibrated, or a maximum legal-capacity scenario probable.

Scenario dimensions include future prices, discretionary execution, financing access, vest/exercise behavior, conversion triggers, settlement election and transaction completion. Joint paths must be coherent: the same dollars cannot fund both a buyback and a debt repayment, and one shelf cannot independently support mutually incompatible maximum issuances.

Any probability or prediction interval requires calibration evidence. Before that, label outputs **conditional scenario envelopes**. A proposed execution-surprise feature must compare newly known execution with a forecast frozen before its disclosure, not with an analyst's hindsight narrative. Track whether prices already moved between first public information and Mastermind's own usable receipt.

### F8. Appropriate LLM roles

| Task | Deterministic owner | Cheap model role | Frontier model role |
|---|---|---|---|
| Identity, units, time, hashes, arithmetic | Exclusive | None | None |
| Structured fact extraction and lifecycle validation | Exclusive or rule-based candidate routing | None for authoritative values | Exception explanation only |
| Locate relevant unstructured passages | Retrieval and source-span indexing | Bounded candidate extraction | Rare complex retrieval disputes |
| Classify routine terms | Rules and typed validation | Propose fields with evidence | Review unusual instrument/transaction terms |
| Contradictions | Detect and preserve alternatives | Summarize source disagreement | Propose adjudication for human/authorized review |
| Forward scenarios | Existing deterministic model and assumptions | Explain already-computed cases | Design or critique hypotheses; not silently set probabilities |
| Consumer narrative | Exact artifact receipt and coverage | Describe observations and uncertainty | High-stakes interpretation review |

Model outputs are untrusted proposals until validated/adjudicated. Source text is data, never instructions. No model may manufacture a timestamp, resolve a security solely from a familiar ticker, close a cash gap, infer missing issuance as zero, or obtain trade authority. Keep model/version/prompt provenance and exact evidence spans; reject unsupported fields. A frontier model should handle genuinely difficult bounded exceptions, not reread every filing continuously.

---

## G. Mastermind integration and ownership map

| Producer | Canonical artifact / owner | Evidence dimension | Consumer / boundary |
|---|---|---|---|
| Existing SEC/Company Facts collectors | Existing retained source and receipt owner | Observed filing facts | Existing event/share compilers; no new filing scraper in portfolio code |
| Existing event/instrument/registration compilers | Capital Structure owner | Typed occurrence, terms, capacity constraints | Capital-state compiler and review queue |
| Approved class/basis selector | Existing share observation owner plus derived read model | Reported denominator and bridge completeness | Fundamentals, allocation, ownership denominator adapters |
| Approved movement/scenario compiler | Capital Structure projection; exact input generations | Share supply, cash/debt/preferred changes | Native capital_need/cash_runway/debt_maturity and bounded display |
| Optional exchange/depository/vendor adapter | Same source/event owner | Operational confirmation, correction or contradiction | Field-level reconciliation, not a competing event truth store |
| Existing capital_allocation | Existing interpretation owner | Capital-allocation context | Research/display; source extraction progressively replaced only by approved migration |
| Existing Mastermind held-risk | Existing portfolio risk owner | Solvency/dilution evidence and coverage | Shadow discrepancy first; existing authority/policy unchanged |
| Research desk / single-name / Decision Snapshot consumers | Their incumbent artifact/decision owners | Inspectable capital evidence with dependency graph | Admit only via existing contracts; no new score or decision service |
| Cycle/original-equity recovery | Existing adjacent owner, including draft #8308 as applicable | Conditional original-holder outcome | Input integration only; no duplicate recovery engine |
| Terminal/charting | Existing presentation/security-history owners | Dates, quantities, explanation and source links | Display not independent financial truth or calculation authority |

A snapshot must include a stable `economic_event_group`/dependency relation so buyback execution, shareholder yield, EPS denominator changes and ownership percentages from the same event are not counted as independent corroborating evidence. Source multiplicity improves provenance only when appropriate; it does not multiply predictive information.

Consumer migration is **shadow first**. Compare old/new source choice, missingness, units, dates, basis, values and resulting coverage labels. A disagreement caused by missing-to-zero legacy behavior is not automatically an improvement to merge: quantify and explain it, then obtain the consumer owner's approval. Do not remove `dilution_events.parquet` fallback behavior or activate a live replacement inside this research commission.

---

## H. Empirical validation program

### H1. Four separate acceptance layers

**Ledger truth:** discover events, extract terms, resolve identities, deduplicate and replay exact versions.

**Accounting/fundamental usefulness:** improve share, cash, debt, preferred and ownership reconciliation, including correct abstention.

**Forecast usefulness:** improve future denominator/capital-path predictions against simple baselines, with calibration and failure analysis.

**Incremental market information:** improve out-of-sample outcomes after existing evidence and realistic information delays. Passing an earlier layer does not imply passing a later one. Failure to predict returns need not kill a useful accounting ledger.

### H2. Gold set and material errors

Build a preregistered, independently adjudicated sample across issuer size, liquidity, class complexity, missingness and action families. Include negative controls, withdrawn offerings, zero-activity periods, amendments, reverse splits, overlapping disclosures, acquired/delisted firms and actions that straddle observation dates. Sample by issuer-event cluster, not many correlated fields from the same filing counted as independent evidence.

Start with a **240-event diagnostic pilot**: 60 each for basis transformations, repurchases/ASRs, ATM programs/sales and primary/secondary offerings. This is a proposed defect-finding pilot, not a claim of 99.5% accuracy. Cover later mechanisms in separately admitted sets before promotion.

Measure event precision/recall, critical identity/unit/date/quantity error, program linkage, duplicate economic effect rate, correction replay, missingness/abstention, share-bridge residual and reproducibility. Report denominators, confidence intervals and performance by family. A perfect result on a tiny or selectively accepted sample is not broad certification.

### H3. Forward-share and financial validation

Freeze knowledge at each forecast origin, predict the next directly observed class-compatible shares and selected horizon states, and record the actual future observation date and publication date separately. Corporate actions and later revisions in **outcome labels** may be used to measure what eventually happened, but cannot leak into the input snapshot.

Baselines: last reported compatible O/S; last O/S with known mechanical actions only; trailing net-issuance extrapolation; and the existing panel's share trend where admissible. Report bias, absolute error as a fraction of initial shares, WAPE, mechanism error decomposition, interval coverage/width when probabilistic, abstention and subgroup stability. Do not compare forecasts against another model's estimates as though those estimates were observed truth.

Accounting scenarios must separately reconcile share effects and cash/claims. A lower share forecast error that drops financing proceeds or erases a pre-funding cash-floor breach fails usefulness. EPS evaluation must use the correct period denominator and an admitted numerator baseline, not just match endpoint outstanding shares.

### H4. Market-information design

Use time-blocked out-of-sample evaluation with historical membership and security lineage, failures/delistings, appropriate event clustering, overlapping-horizon protection and frozen information modes. No random filing-row split. Preserve existing Mastermind outcome/holdout authority; this packet does not authorize touching protected outcomes or rerunning existing experiments. [R07](SOURCES.md#R07)

Controls include market/industry context, size, valuation, liquidity, momentum, profitability/investment, leverage/distress, existing payout/allocation features, and earnings/ownership/options evidence **only where historically admissible**. Report models with and without unavailable controls and their changed populations; do not fill missing PIT analyst revisions with today's values.

Separate market reaction before Mastermind's receipt from returns after usable receipt. A source can improve explanation without adding tradable surprise. Execution disclosure should not be time-stamped at the start of the quarter in which trades occurred.

Proposed confirmatory budget: seven mechanism families × two primary horizons (21 and 63 trading sessions), plus two joint-model comparisons = **16 comparisons** per accepted experiment version. Initial P0 may activate only the two qualified families (repurchases and primary/ATM supply) plus the joint comparisons: **6 active, 10 reserved**, not 16 automatically authorized runs. Other horizons, transformations and subgroup searches are exploratory and must not be silently promoted after outcome inspection.

Evaluate paired out-of-sample loss/forecast improvement, information coefficients where appropriate, calibration for genuine probabilities, abnormal returns with suitable uncertainty, stability, turnover/liquidity/cost sensitivity and family ablations. Use multiplicity control and report effect sizes with uncertainty, not only p-values. Causal language requires a defensible causal design; an incremental predictive association is not one.

### H5. Falsifiers and promotion boundaries

Kill a family's live accounting promotion if identity/units/availability cannot be defended, material terms are unreliable, duplicate effects survive reconciliation, corrections overwrite history, rights fail, or review burden is uneconomic. Withhold a forecast claim if it does not outperform appropriate simple baselines or its intervals are uncalibrated. Withhold a prediction claim if incremental effects disappear under PIT-safe controls, timing, lineage, costs or out-of-sample evaluation.

A vendor fails when it adds no material quality/coverage/latency value after total cost, or cannot supply the needed as-was/retention rights. A source family subsumed by existing evidence should not get an additional vote. Negative results must be published, not converted into a new unexplained aggregate score.

Detailed proposed thresholds, leakage cases and arithmetic oracles are in [VALIDATION.md](VALIDATION.md). No historical market-outcome run or production validation was executed for this research.

---

## I. Risks, failure modes and mitigations

| Risk | Failure signature | Required treatment |
|---|---|---|
| Authorization mistaken for execution | Maximum buyback/ATM amount directly changes forecast shares | Separate capacity, observed movement and conditional scenario |
| Anchor overlap | Actions already embedded in a reported count are applied again | Explicit bridge interval and overlap proof; otherwise defer |
| Treasury double count | Retirement reduces O/S after repurchase already did | Issued/treasury/outstanding conservation invariant |
| SBC double count | Employee options counted in both option and SBC buckets | Unique movement IDs and exclusive source cohorts |
| Public-float unit error | USD field treated as share count | Unit/population/date guards; separate float concepts |
| Split double adjustment | Later restated comparative facts adjusted a second time | Basis lineage and once-only transformation |
| Daily false precision | Quarterly total spread across days without evidence | Interval facts and bounds, not invented execution history |
| Cash/claim asymmetry | Dilution without proceeds or debt draw without repayment | Dated paired legs; explicit fees/restrictions and residuals |
| Accounting-method drift | A current diluted-EPS rule rewrites historical comparatives | Accounting-policy and source-version lineage; mode labels |
| Correction leakage | Later amendment changes earlier snapshot | Immutable versions, knowledge intervals and adversarial replay |
| Correlated “independent” evidence | Same financing appears in five lanes and three feeds | Economic dependency graph and family ablations |
| Missingness masquerading as zero | Empty filing/extraction yields no issuance or payout | Explicit unavailable/confirmed-zero distinction |
| Survival/identity bias | Acquired or canceled old shares vanish from evaluation | Historical universes and old-holder entitlement lineage |
| Vendor lock-in | Only proprietary ID can rebuild a state | Internal identities, exportable provenance and rights-aware adapters |
| LLM false certainty | Unsupported term/clock presented as accepted | Evidence spans, deterministic validation and review state |
| Governance bypass | C13 declares held W6 foundation ready despite W2/W4 | Preserve incumbent gate dependency and separate acceptance decisions |

The implementation should budget review cost as part of quality, not as an invisible subsidy. If a mechanism needs sustained expert review at an uneconomic rate, narrow automated scope rather than lowering truth standards. A review queue must have capacity, aging, owner and expiry semantics; “queued” is not reliable coverage.

---

## J. Build priorities

| Priority | Recommendation | Gate / dependency |
|---|---|---|
| P0 | Research acceptance; reconcile owner, W2 proof state, adapter decision and source/rights scope | Read-only G0; no runtime mutation |
| P0 | Approved logical movement model, time modes, unit/class/basis policy and adversarial fixtures | Map to incumbent contracts; no parallel schema authority |
| P0 | Selected reported-share anchor and basis transformations | Existing share-substrate enablement and W2/W4 prerequisites |
| P0 | Repurchase/ASR and primary/ATM movements with deduplication | Mechanism-specific evidence, capacity constraints and quality gate |
| P0 | Shadow discrepancies for allocation/fundamental/held-risk consumers | No live policy/cutover; compare missingness and arithmetic |
| P1 | Employee equity, warrants, converts, preferred and debt/refinancing | Instrument terms, accounting review, existing W5/W6 sequencing |
| P1 | M&A, tenders, spins, dividends and original-holder lineage | Transaction/identity/entitlement source qualification |
| P1 | Operational exchange reconciliation and consumer cutover proposal | Rights, shadow performance and separate owner acceptance |
| P2 | DTCC/commercial bake-off; international expansion | Demonstrated incremental value and jurisdiction-specific contracts |
| Defer | Financing probabilities, broad predictive deployment, complex contingent valuation | Mature qualified history and separate empirical authority |
| Defer | Universal fully diluted real-time number; continuous frontier extraction | Unnecessary precision/cost and missing terms |
| Reject | Parallel capital-allocation/source/security control plane; opaque score; guessed clocks; authorization-as-execution; ticker-only identity | Violates semantic/authority foundations |

These priorities are importance rankings, **not permission to leap over the incumbent dependency graph**.

---

## K. Proposed implementation phases and stop conditions

### G0 — Read-only reconciliation and owner acceptance

Re-pin current source law and all four repositories; classify movement since this audit. Read the current workstream, latest natural-proof receipts, share enablement gates and any adapter migration ruling. Map each logical requirement into the existing owner's contracts/phases. Return a bounded design/admission decision. If W2/W4 remain held, stop construction and return the exact missing evidence; independently useful research/fixture design may proceed only within existing authorization.

### G1 — Economic contracts and evidence fixtures

After appropriate owner acceptance, freeze exclusive movement legs, identity/basis/time semantics, parser versus source corrections, rights tags and missingness states. Qualify the diagnostic pilot and arithmetic/adversarial oracles. No new collector, publication head, source store or portfolio authority. Existing closed-bundle/retention/concurrency rules remain intact.

### G2 — Share basis and core action shadow

Only after incumbent W2/W4 and share-publication prerequisites are satisfied, implement the minimal reported-anchor selector, basis transformations and core repurchase/primary/ATM read models in the appropriate W6-related scope. Preserve withheld fields. Run offline/shadow comparisons; report unexplained residuals and coverage, not a perfect current denominator inferred from absence.

### G3 — Instrument and transaction expansion

Use the W5/W6 owner sequence to add employee awards, warrants, converts, preferred, debt and corporate reorganization terms. Qualify accounting policy, cash/claims symmetry and old-holder lineage before reporting forecasts. Bring new forms only through the existing source owner. A failed family may remain deferred while others qualify.

### G4 — Separately accepted publication/consumer migration

Obtain native source/publication/consumer approvals after objective quality and shadow gates. Produce clean-runner, natural production and served-artifact evidence under current house law. Do not manufacture natural proof by dispatching a special daily run where the incumbent workstream forbids it. Rollback is consumer-disable/revert to known prior projection, not deletion of immutable observations.

### G5 — Independently governed forecasting/market validation

Run only the admitted experiment budget and modes; prospectively collect new as-run history where old history is insufficient. Family-specific predictive promotion remains separate from accounting publication and outside this commission's default implementation wave. No ranking/sizing/entry/veto/Prophet/trading changes follow automatically from a successful ledger.

---

## L. Exact bounded follow-on implementation commission

> **Issue only after research acceptance. This text is a proposed later commission, not one executed by the research author.**

### CORPORATE CAPITAL ACTIONS — INCUMBENT-OWNER FOUNDATION THROUGH SHADOW

**Mission.** Deliver the smallest auditable extension of the existing macro `capital-structure-intelligence` program that explains a security-specific reported-share basis and known corporate-capital changes without creating another truth/control plane or changing financial authority.

**Authority.** This commission authorizes no purchase, portfolio/ranking/sizing/entry/veto/trading change, Prophet promotion, live consumer cutover or unapproved source expansion. It does not override current source law or existing W2/W4/W5/W6 prerequisites. Canonical ownership is not a mandate to use any particular expensive implementation worker: route bounded work under the current capable-worker/fabric policy. Do not launch a duplicate program or use a separate security master, event store, retention clock, publish journal or lifecycle owner.

**Mandatory first gate — G0, read-only.**

1. Resolve and pin then-current Mastermind protected master, macro, terminal and Research Vault identities and consume the exact current bootstrap/source-law procedures. Record the immutable research packet revision consumed.
2. Re-census the incumbent workstream, actual contracts, source policies, publication gates, tests and natural-proof receipts. Distinguish code from recorded proof and current runtime.
3. Explicitly resolve whether W2C/W2D joint natural proof has closed W2; whether W4 prerequisites allow the proposed W6 scope; and whether Company Facts/share-count enablement is authorized. Do not dispatch a daily run merely to manufacture proof.
4. Resolve the adapter/successor-contract decision. An overdue review date is not acceptance of `company_event.v1`. Preserve existing IDs and version law unless an authorized migration decision says otherwise.
5. Identify overlap with `capital_allocation`, `capital_need`, `cash_runway`, `debt_maturity`, BioCatalyst and the current original-equity recovery owner, including the current status of PR #8308. Do not overwrite another owner's in-progress branch.
6. Return an explicit `GO_FOR_BOUNDED_SHADOW` or `HOLD` with exact dependencies. If HOLD, stop construction; name the missing proof/decision and retain useful research results. Do not substitute outcome access or a parallel implementation to keep a worker busy.

**Scope after the gate actually clears.**

Map the accepted logical model to incumbent physical contracts. Implement only: direct class-compatible reported-share selection; split/reverse-split and required basis transformations; authorization versus actual repurchase/ASR delivery; ATM capacity versus actual sales; primary versus selling-holder offering shares; immutable event/program relationships; and an as-of read model with shadow adapters. Instrument work is limited to what these mechanisms require under the accepted existing architecture. Broader employee/convertible/M&A prediction belongs to later waves.

**Required semantics.**

Preserve event time/precision, query as_of, observed_at, public availability, canonical/system known_at, ingested_at, effective intervals and correction generation. Actual-system replay, public historical reconstruction and latest-restated views must be separate modes. No source or parser correction may backdate actual-system availability. Query cutoffs belong in derived snapshot identity, not immutable economic occurrence identity.

Preserve source bytes/receipts and exact spans, raw and normalized units, currency, issuer/security/class, adjustment basis, program/instrument/event links, source/parser/policy versions, contradiction state and rights scope. Honor existing closed-bundle, concurrency and retention protocols. Never rewrite historical manifest IDs or add a parallel compiled-root truth store.

Use mutually exclusive movement legs. Treasury retirement after treasury acquisition has zero additional outstanding-share effect. Employee-option and SBC movements cannot overlap. Selling-holder shares do not create issuer proceeds or O/S. Maximum shelf/ATM/board capacity is not a forecast. Source monetary public float is not float shares. Do not apply a split to a comparative value already on that split basis. Unknown activity is not zero.

**Output.**

For an explicit cutoff and target date, expose the selected reported anchor, its observation date/class/basis, all material competing observations, selection/exclusion reasons, admitted incremental movements, bridge coverage and unexplained residual, active capacity constraints, observed executions, exact source generations and authority flags. Label estimates and scenarios correctly. Unsupported current, float, fully diluted, financing-probability or forward-EPS fields remain unavailable with reasons.

**Deterministic/LLM boundary.**

Deterministic code owns identity, clocks, units, arithmetic, eligibility, versioning, selection, lifecycle and conservation. Models may only propose bounded unstructured term candidates or summarize contradictions with retained evidence spans. Models cannot fabricate numeric terms, compute authoritative financial values, set known_at or grant authority. Complex unresolved terms enter a bounded review queue rather than a confident fallback.

**Shadow integration.**

Read canonical projections through existing consumer boundaries; do not crawl filings inside portfolio code. Preserve existing live behavior. Produce discrepancy artifacts including legacy missing-to-zero behavior, shareholder-yield definitions, the held-risk filing gap and its documented financial proxies. A semantic improvement must be accepted by the consumer owner before changing decisions or replacing a legacy path.

**Acceptance evidence.**

Provide schema/invariant checks; exact source/parser correction replay; no-future-evidence tests; class/unit/basis rejection; treasury acquisition/retirement distinction; split-once tests; authorization/execution/settlement and ASR increment tests; primary/secondary and shared-capacity tests; employee-leg exclusion where relevant; cash/proceeds/fees consistency; deterministic same-input hashes; explicit abstention and bridge residuals; and legacy-versus-canonical shadow discrepancies.

Use the proposed validation docket only after its sample/budget is accepted. Report measured precision with denominators and uncertainty; do not claim production reliability from a few synthetic fixtures. Do not touch protected market outcomes or expand the experiment family without the existing research/evaluation owner's permission.

**Release and stop boundary.**

End this wave after the bounded foundation and shadow evidence, with all new rank/sizing/entry/veto/Prophet/trading authority false. Live publication or consumer cutover requires a separate acceptance decision, applicable clean-runner/natural/served proof and an explicit rollback plan. Preserve immutable records on rollback. P1 expansion and predictive promotion require later commissions.

**Return package.**

Return exact source pins and consumed research revision; ownership/migration decision; current-state delta; accepted schemas and semantic mappings; source/rights admission; changed paths; tests and receipts distinguished from unrun proposals; sample/coverage/precision results; PIT replay and adversarial cases; deterministic artifact hashes; shadow discrepancies; observability and rollback design; unresolved blockers; and an explicit statement of which capabilities are built, proven, held or unavailable.

**Terminal rule:** a truthful partial-capability snapshot with intact gates is acceptable; a complete-looking denominator produced by guessed history, double counting, hidden missingness or unauthorized authority is not.
