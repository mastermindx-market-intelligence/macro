# Finance source-rights, refresh and provenance plan — 23 September 2026

**Operation:** `gmi-finance-sector-research-20260923-sol-001`  
**Carrier:** Macro Draft/HOLD PR #7786, `sol/finance-sector-research-20260923`  
**State:** SOURCE / RIGHTS / REFRESH DESIGN PROPOSAL / DRAFT-HOLD  
**Mission complete:** false  
**Authority:** research and planning only. This artifact does not admit a source, authorize credential use, create a collector, start a watcher, write accepted evidence, publish private content, or grant ranking/trading authority.

## 0. Source and ownership boundary

- Protected procedure: `mastermindx-market-intelligence/Mastermind@bf764f494b9cd0ecede6234bb472c3344c8e77cc`, Skillpack 1.0.1/bootstrap major 1.
- Prior Finance product-design head: `c34c6e575c391e613a8f31007af8f4ac5b9ad14f`.
- Original Macro research base: `668237947e016f679782e41e61c91c9133a5ea99`.
- Existing source, Research Vault, evidence, identity, publication and scheduler owners remain canonical.
- This design creates no new source registry, document store, crawler, retention bucket, event bus, queue, watcher, scheduler, evidence ledger or publication path.
- Principal-duty reason: `PRINCIPAL_JUDGMENT`. No worker, Fable receiver, Executive Attempt or watcher was started.

## 1. Outcome

Every user-visible Finance statement should answer:

```text
What source said this?
What exact object/business/metric did it describe?
When was it published, effective, observed and reviewed?
What population, unit and denominator apply?
What does the source prove and not prove?
Can the content legally be retained, derived and shown to this user?
Has it been corrected or superseded?
Which owner transformed it into the current product view?
```

The machine must preserve source-native facts and clocks while enabling useful synthesis without copying proprietary reports or laundering model interpretation into fact.

## 2. Executive rulings

### R-FIN-SRC-1 — Source truth and house interpretation remain separate

A source assertion records what a source establishes. House synthesis records the interpretation, mechanism or comparison derived from one or more assertions. They use separate identities and review states.

### R-FIN-SRC-2 — Public availability is not unlimited publication permission

A public URL may support citation, parsing or lawful short quotation. It does not automatically authorize:

- committing the full document;
- republishing tables or paywalled text;
- exposing current private research payload publicly;
- retaining third-party personal or restricted data;
- ignoring site terms or robots/access controls.

### R-FIN-SRC-3 — Licensed research stays private and source-bound

Institutional/vendor research may support internal synthesis according to the accepted license and Research Vault owner. It does not automatically become redistributable company-level evidence or a public seed.

Use:

- source identifier and lawful metadata;
- original house paraphrase;
- short lawful excerpt only where allowed;
- explicit rights state;
- private authenticated display where permitted.

### R-FIN-SRC-4 — Models extract candidates, not accepted facts

Model extraction must preserve source span/locator and uncertainty. It cannot self-ratify identity, metric mapping, relationship, valuation, materiality or current state.

### R-FIN-SRC-5 — Retrieval date is not publication or business-effective date

Preserve at least:

- upstream publication/filing/acceptance time;
- business effective or period/as-of time;
- first observed/retained time;
- curation/review/admission time;
- correction/supersession time.

### R-FIN-SRC-6 — Source-native definition controls

Issuer/regulator definitions remain authoritative for the fact. The Finance metric dictionary maps to a normalized family but cannot rewrite the native meaning.

### R-FIN-SRC-7 — Current full-fidelity Finance evidence is private by default

No current accepted detailed payload in:

- public Git or Pages;
- public R2/static artifacts;
- anonymous HTML;
- source maps;
- service-worker caches;
- localStorage/IndexedDB;
- downloadable fixtures/evidence screenshots.

### R-FIN-SRC-8 — Refresh uses incumbent owners

Event-driven and scheduled refresh run through existing collectors, issuer/company intelligence, Research Vault, GMI evidence admission and publishers. Do not build a Finance watcher service.

### R-FIN-SRC-9 — Missing rights or retention fails closed

A useful research candidate may remain in internal research, but it cannot enter accepted current product as a fully qualified claim without the required rights, retention and review states.

### R-FIN-SRC-10 — Provenance is necessary but not sufficient

A source list alone is not intelligence. Product value requires mechanism, comparison, rerating/economic bridge, conflicts and watch conditions.

## 3. Source classes

### 3.1 U.S. regulatory and statutory sources

Examples:

- SEC filings and datasets;
- FDIC QBP/institution data;
- FFIEC Call Reports and UBPR;
- Federal Reserve payment, bank, credit, flow and survey data;
- OCC trading/derivatives and supervisory publications;
- CFTC market/clearing/repository data;
- NAIC statutory/market/AI materials;
- FHFA/Fannie/Freddie mortgage data;
- CFPB rules/data;
- Treasury/FinCEN/OFAC;
- FSOC/OFR;
- state insurance departments.

Typical rights state:

- public official source;
- factual data reusable with source and method;
- document/table retention subject to owner policy and storage controls;
- current authenticated synthesis preferred for detailed product.

### 3.2 Issuer filings and IR materials

- 10-K/10-Q/8-K/proxy/registration statements;
- statutory filings;
- earnings releases and supplements;
- investor presentations;
- fee schedules/rulebooks/product documentation;
- participant directories and operating statistics.

Requirements:

- filing/accession/document identity;
- exact table/note/section locator;
- issuer/segment/product scope;
- GAAP/non-GAAP and reconciliation;
- publication/period/as-of clocks;
- subsequent restatement/supersession.

### 3.3 Market and infrastructure operators

- exchanges, clearinghouses, depositories, payment operators, networks, index/ratings bodies and associations;
- volume, value, open interest, custody, settlement, participation, operating statistics;
- rulebooks/fee schedules/service definitions.

Company-reported system scale must be labeled as company/operator reported rather than regulator-certified moat or market share.

### 3.4 Public economic and industry statistics

- ICI fund/ETF statistics;
- Nacha ACH statistics;
- catastrophe/economic official data;
- public industry associations where method and rights are clear.

Association data remains source-attributed and method-bound.

### 3.5 Licensed vendor/consensus/market data

- market prices and fundamentals;
- analyst estimates/revisions;
- alternative data;
- paid institutional research;
- proprietary holdings, flow or market-share data.

Requirements:

- accepted entitlement and workspace/tenant binding;
- rights profile and display restriction;
- source/provider/version;
- retention policy;
- no public fixture or evidence leakage;
- no inference that technical access grants organizational permission.

### 3.6 Company product/catalog pages

Useful for:

- product capability;
- supported workflow;
- announced service;
- customer or network claims where source-attributed.

Not sufficient alone for:

- live use;
- exclusivity;
- current procurement/relationship;
- volume/revenue/materiality;
- market share;
- security identity.

### 3.7 News and secondary research

Use as:

- discovery/candidate generation;
- attributed context;
- event pointer;
- disagreement source.

Material factual claims should resolve to primary evidence where available. Secondary-only facts remain clearly attributed and lower-confidence/held.

### 3.8 Model and house interpretation

- extraction candidate;
- normalization candidate;
- mechanism hypothesis;
- comparison/derived metric;
- synthesis/watch condition.

Every derived fact preserves formula/input refs. Every interpretation states its evidence and limitations.

## 4. Rights-state vocabulary

Proposed closed research vocabulary:

- `PUBLIC_OFFICIAL_FACT`
- `PUBLIC_ISSUER_FACT`
- `PUBLIC_OPERATOR_FACT`
- `PUBLIC_ATTRIBUTED_SECONDARY`
- `PUBLIC_COPY_LIMITED`
- `LICENSED_PRIVATE_DISPLAY_ALLOWED`
- `LICENSED_PRIVATE_INTERNAL_ONLY`
- `TENANT_OR_USER_SCOPED`
- `PERSONAL_OR_SENSITIVE_RESTRICTED`
- `RIGHTS_UNKNOWN_HELD`
- `SOURCE_WITHDRAWN_OR_UNAVAILABLE`

This vocabulary is proposal-only until the incumbent rights owner accepts it or maps it to an existing vocabulary.

## 5. Source-document identity

A source record should preserve:

```text
source_document_id
publisher
source_family
title
canonical_url_or_filing_id
accession_or_native_id
version / amendment
publication_at
accepted_at_optional
period_start/end_optional
as_of_date_optional
observed_at
retained_at_optional
retention_pointer_optional
content_digest_state
rights_profile
language
geography
supersedes / amended_by
```

A changed document at the same URL creates a new source version when content materially changes.

## 6. Source locator

Closed initial locators:

- filing form/accession/item/note/table/row/column;
- page/section/paragraph;
- HTML selector or source-native anchor;
- dataset series/table/query key;
- API endpoint plus immutable parameters/vintage;
- transcript speaker/section/time;
- product page section and observed version;
- rule section and effective date.

A URL alone is insufficient for a multi-claim document.

## 7. Finance assertion lineage

```text
source document/version
→ source-native assertion
→ reviewed normalized metric/relationship mapping
→ owner observation/state
→ Finance page view
→ user-visible synthesis/conflict/watch condition
→ evaluation outcome context
```

Each link remains inspectable.

### 7.1 Source-native assertion

Contains:

- subject/object labels;
- optional validated canonical bindings;
- exact predicate/assertion type;
- statement mode;
- scope;
- native measurement;
- clocks;
- limitations;
- source locator;
- review/correction state.

### 7.2 Normalization mapping

Contains:

- normalized metric/relationship family;
- mapping rationale;
- comparability key;
- basis match/refusal;
- reviewer/admission state.

### 7.3 Owner observation

Retains owner-specific method, generation, freshness and authority.

### 7.4 Product synthesis

Names every supporting owner/source and never upgrades authority.

## 8. Statement-mode vocabulary

- `STATUTORY_OR_REGULATORY_FACT`
- `AUDITED_REPORTED_FACT`
- `UNAUDITED_REPORTED_FACT`
- `ISSUER_NON_GAAP_REPORTED_FACT`
- `OPERATOR_REPORTED_STATISTIC`
- `CATALOG_CAPABILITY`
- `ANNOUNCED_ARRANGEMENT`
- `FORWARD_TARGET_OR_GUIDANCE`
- `DERIVED_MEASURE`
- `ATTRIBUTED_SECONDARY_CLAIM`
- `HOUSE_INTERPRETATION`
- `MODEL_EXTRACTION_CANDIDATE`

A forward target remains a source statement, not a realized future fact.

## 9. Assertion-review states

- `EXTRACTED_UNREVIEWED`
- `RESEARCH_CANDIDATE`
- `SOURCE_LOCATOR_PENDING`
- `IDENTITY_PENDING`
- `METRIC_MAPPING_PENDING`
- `RIGHTS_PENDING`
- `REVIEWED_HELD`
- `ACCEPTED_CURRENT`
- `ACCEPTED_HISTORICAL`
- `WITHDRAWN`
- `SUPERSEDED`
- `REJECTED`

These are evidence-review states, not Executive lifecycle states.

## 10. Refresh classes

### 10.1 Market/session

Examples:

- prices, volume, relative strength, sector/subtheme tape.

Owner/cadence:

- existing market/session owners;
- completed-session semantics;
- current/stale health.

### 10.2 Daily

Potential:

- payment/exchange/operator volumes where official daily data exists;
- fund flows where licensed/accepted;
- regulatory notices;
- material issuer filings/events.

Do not poll unavailable daily facts or manufacture daily freshness from undated pages.

### 10.3 Weekly

Potential:

- selected volume/flow/crowding/credit statistics;
- issuer/operator updates;
- research-source ingestion.

### 10.4 Monthly

- AUM/flow disclosures;
- payment/transaction statistics;
- credit performance/vintages;
- insurance rate/claims proxies;
- advisor/participant/account statistics where available;
- regulatory reporting.

### 10.5 Quarterly

- earnings, segment and operating metrics;
- bank call reports;
- insurance statutory/issuer metrics;
- private fund/regulatory statistics;
- consensus/valuation snapshots;
- evaluation outcomes.

### 10.6 Annual

- audited financials;
- long-tail reserve triangles;
- statutory capital/insurance schedules;
- annual participant/fund/system reports;
- taxonomy and source-right review.

### 10.7 Event-driven

- M&A/ownership/control;
- product/service launch/retirement;
- license/rule/exemption/effective date;
- capital raise/buyback/dividend;
- reserve/credit/cyber/fraud incident;
- source correction/restatement;
- metric-definition/taxonomy change.

## 11. Refresh triggers

A refresh candidate is generated when an accepted owner observes:

- new source version;
- later filing/amendment;
- material operating/financial event;
- ownership/business-scope change;
- metric-definition change;
- relationship launch/termination;
- rule status/effective-date change;
- evidence expiry/review window;
- source withdrawal/rights change;
- identity mapping change;
- publication generation change.

Candidates enter incumbent review/admission. They do not auto-write graph relationships or current assertions.

## 12. Finance-specific review windows

Review window is source/business dependent:

- regulatory status: review on rule/authorization/effective-date change;
- product capability: review on product replacement/retirement or periodic stale check;
- commercial relationship: review on termination/change or bounded periodic check;
- quarterly metric: current through next comparable report subject to event invalidator;
- annual reserve/vintage table: historical truth remains, current interpretation updates with newer development;
- undated catalog page: observed date shown, publication unavailable, shorter review window;
- valuation/consensus/market state: owner-specific session freshness;
- rights/entitlement: review on license/workspace/provider change.

Expiry never deletes historical evidence. It changes current usability.

## 13. Correction and supersession

### 13.1 Corrections

Preserve:

- original assertion/source version;
- correcting source/version;
- reason;
- affected fields;
- knowledge/observation time;
- effective/period scope;
- current/historical disposition.

### 13.2 Restatements

Do not overwrite historical research states. A retrospective restatement may be available in “as restated” analysis, but point-in-time evaluation uses the vintage known then.

### 13.3 Business reorganizations

Segment changes require:

- prior/new segment taxonomy;
- recast-history availability;
- acquisition/disposal effective date;
- comparability state;
- no silent backfill.

### 13.4 Metric-definition changes

Examples:

- AUM scope;
- organic flow exclusions;
- adjusted earnings;
- combined-ratio method;
- transaction population.

Definition version is part of the assertion comparison key.

## 14. Retention and integrity

### 14.1 Retention states

- `NATIVE_IMMUTABLE_RETAINED`
- `OWNER_RETAINED_VERSIONED`
- `SOURCE_URL_ONLY_NOT_IMMUTABLE`
- `LICENSED_REFERENCE_ONLY`
- `RETENTION_PENDING`
- `RETENTION_PROHIBITED`

Do not claim immutable retention from URL availability alone.

### 14.2 Digest

Digest only bytes actually retained under the owner’s lawful process. Do not invent a digest from incomplete web text or metadata.

### 14.3 Raw versus assertion

Raw documents and structured house assertions remain separate. Source retention does not itself admit the assertion.

## 15. Access and publication

### 15.1 Current product payload

Authenticated, private/no-store. Existing entitlement owner determines access.

### 15.2 Static/public shell

May contain:

- approved product explanation;
- deliberately public examples;
- no current private data;
- no source-protected excerpts or hidden JSON.

### 15.3 Browser/evidence screenshots

Use anonymized/synthetic or rights-cleared data unless production evidence process is explicitly private and protected. Screenshots must not become a public data leak.

### 15.4 Exports/downloads

No new export is authorized. Any future export requires rights, tenant, source and redistribution controls.

## 16. Source-quality dimensions

Expose separately:

- source authority;
- directness;
- identity certainty;
- locator precision;
- time precision;
- measurement completeness;
- comparability;
- retention integrity;
- rights usability;
- review state.

No fused source-confidence score is required.

## 17. Disagreement handling

When sources disagree, preserve:

- each assertion and source;
- population/basis/clock;
- whether one supersedes another;
- genuine contradiction versus scope/time split;
- review resolution or unresolved state.

Do not choose the “most recent” when periods/populations differ.

## 18. Data and rights matrix by Finance family

### 18.1 Banks/credit

Primary:

- Call Reports/UBPR/FDIC/Fed/OCC;
- issuer filings/supplements;
- accepted market/consensus sources.

Critical rights/comparison issues:

- institution/legal-entity versus holding company;
- average/end balances;
- vintage-level data;
- confidential supervisory data excluded;
- consensus entitlements.

### 18.2 Payments/market infrastructure

Primary:

- issuer/operator statistics;
- Federal Reserve/Nacha/DTCC/SEC/CFTC;
- rulebooks/fee schedules.

Issues:

- branded versus processed;
- gross volume versus net revenue;
- participant/customer confidentiality;
- licensed market share and consensus.

### 18.3 Asset/wealth/retirement

Primary:

- issuer filings;
- fund/adviser regulatory data;
- ICI/operator data;
- accepted flow/market/consensus sources.

Issues:

- AUM/AUA/client/linked population;
- end/average;
- acquired/recruited/organic;
- proprietary fund/participant data;
- user-scoped portfolio information.

### 18.4 Insurance/reinsurance

Primary:

- issuer/statutory/NAIC/state filings;
- catastrophe/economic official data;
- accepted market/consensus.

Issues:

- statutory redistribution and licensing;
- accident/policy-year detail;
- gross/ceded/net;
- actuarial estimates and proprietary models;
- personally sensitive claims data excluded.

### 18.5 Brokers/data/software

Primary:

- issuer filings;
- product definitions;
- contract/ACV/subscription metrics;
- accepted consensus/market.

Issues:

- organic adjustment definitions;
- customer confidentiality;
- acquired annualized versus recognized revenue;
- proprietary datasets/models.

### 18.6 Structural disruption

Primary:

- laws/rules/orders/exemptions;
- operator production statistics;
- issuer reported adoption/revenue;
- incidents and official disclosures.

Issues:

- proposal/final/effective status;
- pilot versus production;
- company membership in working groups not equal revenue;
- fast-changing legal/technical state.

## 19. Source-admission checklist

Before accepting a Finance source/assertion:

1. exact source family and owner;
2. rights/entitlement;
3. raw retention state;
4. source version and locator;
5. publication/effective/period/observation clocks;
6. identity/business scope;
7. native metric/relationship definition;
8. unit/denominator/basis;
9. statement mode;
10. limitations;
11. correction/supersession;
12. review/admission receipt;
13. public/private display policy;
14. refresh/expiry trigger;
15. authority caps.

## 20. Refresh-pipeline design

Conceptual only:

```text
existing collector / Research Vault / issuer event owner
→ source document/version receipt
→ model/deterministic extraction candidate
→ identity + metric + rights validation
→ human/accepted review and curation revision
→ incumbent GMI evidence admission
→ downstream owner recomputation
→ pure Finance view composition
→ authenticated publication
→ existing evaluation accrual
```

No browser-time internet crawler. No automatic relationship edge from model extraction.

## 21. Monitoring without a duplicate watcher

Finance freshness is achieved by:

- existing collector schedules;
- filing/event ingestion;
- source-owner update triggers;
- publication-generation checks;
- page-level stale/coverage health;
- operator review queues already accepted.

A chat session is not a daemon. This plan does not arm a background watcher.

## 22. Deterministic validation

Reject/hold when:

- source or locator missing;
- publication/period/as-of unknown but presented as known;
- business/issuer/security identity guessed;
- native definition missing;
- normalized mapping lacks basis;
- gross/net/stock/flow/average/end ambiguous;
- rights unknown for intended display;
- retention falsely claimed;
- source correction overwrites history;
- licensed/private content appears in public artifact;
- model extraction self-accepts;
- assertion implies materiality not established by source;
- authority fields permit ranking/trading.

## 23. Product provenance display

Glance tier:

- source family;
- as-of/publication date;
- coverage and stale/held state.

Evidence drawer:

- full source/version/locator;
- native definition;
- clocks/basis/denominator;
- rights/display class;
- review/admission;
- correction/supersession;
- derivation/formula;
- owner and authority.

## 24. Source-rights proof for first vertical

Before Money Movement + Securities Infrastructure enters production, prove:

- each issuer/operator/regulatory source is legally retained/referenced;
- full current response is private/authenticated;
- no proprietary consensus or market data leaks into public shell/evidence;
- exact source locators and curation revisions exist;
- identity links are validated;
- definitions and bases pass the metric dictionary;
- update triggers and stale behavior work;
- withdrawn/corrected source behavior is visible.

## 25. Current research packet disposition

The two research assertion packets on PR #7786 are deliberately:

- `RESEARCH_ONLY_NON_CANONICAL`;
- identity hints unvalidated;
- source locators/review incomplete for production;
- zero graph/basket/rank/trade authority.

They are implementation inputs, not admitted evidence.

## 26. Explicit non-claims

This plan does not claim:

- source rights are accepted for every listed source;
- raw documents are immutably retained;
- a production source registry or collector exists;
- accepted Finance assertions have been admitted;
- current data are published;
- any source grants predictive or trade authority.

## 27. Exact next action

Use this plan in the whole-program gap review. Before implementation, Fable/current owners must reconcile the existing rights vocabulary, retention paths, GMI evidence extension and first-vertical source list against current main. Do not create the final Fable handoff until the remaining research gaps are explicitly classified.
