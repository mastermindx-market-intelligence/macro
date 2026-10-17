# Data, product, operations and interface contract

This chapter specifies the proposed implementation. It does not declare any source licensed, any runtime active, or any latency achieved. Sources are listed in `06_EVIDENCE_REGISTER.md`.

## 1. Source strategy and procurement decision

Use a free/open and already-licensed foundation first, then measure the missing information before buying a feed. The initial market advantage sought is attention and synthesis over minutes to sessions, not an assumed ability to outrun institutional headline systems.

| Source family | Intended role | Admission and clock treatment |
|---|---|---|
| GDELT 2.0 event/mentions/GKG | Broad discovery, source references, coverage-adjusted narrative changes | Fifteen-minute publication cadence; preserve batch and actual receipt. Dataset openness is not a license to republish underlying article bodies. [X01, X02] |
| UKMTO/MARAD and other official notices | Maritime incident, warning and correction evidence | Treat notices as attributed reports; retain version, precision and event versus publication time. A stale advisory is background, not a new escalation. [X04] |
| Government and issuer releases | Public policy, sanctions, procurement and company developments | Use owner-approved collectors, source terms and actual first observation. Not every official claim establishes the underlying event independently. |
| Existing licensed financial news | Fast ticker/event discovery and revisions | Inspect exact source, product, transport and permitted audiences. Ingestion, storage, model processing and display are separate rights. [I05, I06] |
| SEC filings and company fundamentals | Company events, expectations, financial/economic evidence | Consume corporate-disclosure/FIF owners; preserve acceptance, public availability, observation and fiscal basis separately. Respect shared fair-access limits. [X05] |
| EIA and energy statistics | Supply/demand, inventories, refinery/power context and exposure | Preserve true release cadence and vintage; weekly statistics are not minute-by-minute supply observations. [X06, X07] |
| Existing equity trade/bar/quote provider | Theme participation, causal technical structure, execution evidence | Plan-specific rights, sessions, adjustment basis, late trades/corrections, halts and missing bars must be tested. [X19, X20] |
| Futures/commodity feeds | WTI, gold, equity-futures and other admitted cross-asset witnesses | Verify each venue and contract; WTI access does not prove Brent coverage. Retail access is not a business redistribution quote. |
| UCDP | Selected independent historical/outcome labels | Monthly candidate cadence; match the study's target definition, geography and coverage. Not the live sentinel. [X03] |
| ACLED | Optional richer conflict context/labels | Contract-specific permission required for product, retention and derivative use. Not assumed freely redistributable. [X21] |
| AI-GPR / original GPR | Benchmark/context and methodological comparison | Index vintage and update clock retained. An intensity index is not a calibrated attack probability. [X08, X09] |
| LSEG enterprise news/analytics | Optional benchmark or future licensed coverage | Desktop Workspace rights prohibit server-side use/redistribution for that service. Evaluate the appropriate enterprise contract, not a desktop workaround. [X14, X15] |

The GDELT manifest was accessible during research. A bounded packet-download attempt from the analytical container failed with a DNS-resolution error. This establishes an environment-specific acquisition limitation, not a provider outage or a successful ingest. Historical October availability and completeness were not tested.

### What not to acquire for the first release

Do not make satellite imagery, paid AIS, L2/L3 order books, alternative military data or a costly all-purpose geopolitical subscription critical-path dependencies. They can become separately evaluated enhancements only after the basic source/market/user loop operates and a specific missing field justifies the cost. No source can be acquired by bypassing an access denial, an expired entitlement or a publisher's permitted-use restrictions.

## 2. Rights and data-governance contract

For every source/product/field, record internal ingestion, historical retention, derivative/model processing, headline/link/teaser/body/image display, user audience, jurisdiction if relevant, expiry/review boundary and source-owner evidence. Unknown is not approved. A key, a paid personal subscription, an accessible website or a cached copy does not establish these permissions.

The existing ticker-news runbook requires explicit ingestion, retention and headline-display rights and treats derivative processing separately. Reuse that owner's receipt semantics. Never manufacture an approved receipt from this plan. If the required retention is unavailable, redesign the feature's persistence and evaluation policy; do not silently keep the data anyway. [I05]

Current access permission is evaluated at read time, even for historical views. Historical economic facts remain as-known evidence; current rights can lawfully restrict what the user may see. Revocation must invalidate customer caches and model-processing eligibility according to the actual contract, without pretending the original observation never occurred.

Raw copyrighted source text stays only in permitted private storage. Public GitHub evidence contains identifiers, timestamps, hashes, counts, source URLs and appropriately bounded paraphrases, not a corpus of article bodies or credentials. Broker/portfolio information and individual user behavior remain tenant-scoped and private.

## 3. Time, identity and revision invariants

### 3.1 Required clocks

A derived record must distinguish event/effective time, source publication time, provider update/version time, actual receipt time, feature window end, assessment cutoff, actual issuance/registration time, user delivery time, and outcome maturity. Each has a precision indicator and an owner.

The earliest eligible assessment time is constrained by every dependency's actual availability and the method's computation requirements. Source publication alone does not prove Mastermind had the information. A record first acquired during backfill cannot be assigned an earlier observation clock. Date-only evidence is represented as an interval or conservatively restricted; it is not assigned artificial midnight precision to pass an intraday test.

A historical query first filters all raw evidence, identity relationships, membership, model versions and coverage observations by eligibility, then computes the derived result. Redacting a future field after it already changed a relationship, rank or reason is insufficient.

### 3.2 Identity hierarchy

Keep source-item/revision, incident, program/project/trial/transaction, legal entity, issuer, security, listing and ticker distinct. A ticker is a display alias, not a global identity. Preserve time-valid ticker changes, ADR/share-class relationships, corporate actions and delisting outcomes.

An incident may affect many securities. A security may have several unrelated catalysts. A single investment thesis can refer to multiple incidents without merging their source truth. CompanyEvent remains the corporate event owner; its existing fiscal identity must not be forced onto an unrelated global incident. [I07]

The proposed opportunity-case identifier is a **derived presentation key** over owner-native incident/company/market-episode references, eligible exposure relation and policy family. Its generation/version changes as the view changes. It does not replace the source IDs or become a new event registry. If two discovery paths later converge, retain their provenance and an explicit linkage rather than deleting one historical case.

### 3.3 Corrections and reproducibility

Append correction/supersession relationships. Preserve original emitted payload, model/prompt version, inputs and policy version, with current entitlement controls. Rebuilds may create a new generation but cannot retroactively improve a forecast, erase a false alarm or move its issue time.

Outcomes have separate evidence and resolution policy. The same LLM-generated assessment cannot create its own ground truth. An unresolved outcome is not negative, and an unavailable price is not a zero return.

## 4. Exact integration seams

### 4.1 qbus revisions

The current schema is `qbus.news_revision.v1`. Its fields include source/source-item identity, transport/message, action, publication/update/event clocks, received/version clocks, title/link/teaser, provider ticker tags, hashes, revision ID and clock anomalies. It is a pure normalization contract. [I06]

Current transports are `benzinga_ws`, `benzinga_rest`, `massive_benzinga_v2`, `alpaca_rest`, and `alpaca_ws`. An official-source or GDELT adapter must be admitted as its true transport by the qbus owner, with backward compatibility and tests. Until then, consume the existing news-vector/source output as a referenced input. Do not relabel an official notice as Benzinga, dual-write a parallel cursor, or start another writer to evade the closed enum.

The source cursor, source revision and delivery receipt must be committed through the existing transactional owner. Consumers are idempotent. A timeout triggers reconciliation of the original receipt, not a blind replacement fetch/write operation.

### 4.2 Company events and incident relation

The inspected `company_event.v1` identity is a function of issuer, fiscal period and event type. Its date parser's accepted input forms must not be mistaken for evidence of intraday precision. A non-fiscal catalyst/incident relationship uses the admitted extension or a reference composition, not an invented fiscal year/quarter. [I07]

An issuer-level exposure assertion must include a source-backed identity/role witness. A thematic association alone cannot create a company-event economic claim or a portfolio holding join.

### 4.3 Radar nominations

Preserve the **exact thirteen fields** in the current nomination contract:

```text
ticker, source_id, source_family, reason_code, reason_text,
observed_at, source_asof, source_rank, source_value, source_horizon,
ttl_until, evidence_ref, data_quality
```

Canonical security/issuer/incident witnesses can be referenced through `evidence_ref`; do not casually add fields to the frozen record. The source's own raw rank/value may be preserved as provenance, not promoted into a Radar trade opinion. The Probe Set has no new score, rank or bullishness field. [I12]

For a theme-member expansion, both `source_family=membership_expansion` and a `membership_expansion.` reason prefix are required. For an actual resolved issuer catalyst, a news-catalyst nomination needs its distinct issuer-specific evidence. A basket's strength must not be laundered into a claim that every member has its own catalyst.

`observed_at >= source_asof`, TTL, availability, durable spool-before-consume and correlated-family disclosure remain intact. Research nominations carry no ranking, sizing, gating, signal-origination or escalation authority. A later qualified decision consumer is a different permission boundary.

### 4.4 Derived opportunity read model

Propose an owner-reviewed versioned view with: derived case/generation key; native source references; origin path; topic/event family; covered entities; assertion status; what changed; alternatives/counterevidence; exposure witnesses; source and market freshness; observed market/technical state; next event/window; existing qualification status; user-permitted actions; and revision lineage.

The frontend does not compute financial sensitivities, fusion scores, probabilities or identity resolution. It renders the server's eligible generation. List, detail, search, alerts and saved views must reference compatible generations and display consequential partial/stale states.

Do not promise a specific new API route before reconciling Terminal #811, the current BFF and auth contracts. Fable's interface package records the actual chosen route and schema; changing a path is an implementation detail, changing rights or model authority is not. [I13]

## 5. Market-data design

Retain the original as-observed bars/trades used for a decision and later corrected versions separately where rights permit. Historical vendor aggregates can contain later corrections unavailable to a live consumer. Massive documents differences between real-time trade messages and historical correction information; this must be reflected in the replay, not hand-waved away. [X19, X20]

A missing aggregate may reflect no eligible trade. Distinguish an empty but healthy interval from transport failure, stale subscription, market closure, halt or unsupported symbol. Resolve session, timezone and daylight-saving rules through the market calendar. Align benchmark timestamps and corporate-action basis before computing returns.

Use raw executable prices for fill simulation; use the declared total-return/adjusted basis for the relevant return study. Do not simulate buying an adjusted price or interpret a split as a crash. Store futures contract and roll policy explicitly; a continuous synthetic series is not necessarily a tradable instrument at that price.

Model premarket, regular and after-hours behavior separately. If reliable overnight quotes/history are unavailable, label that coverage missing and limit the entry claim. Twenty-four-hour aspirations must not silently imply uniform liquidity or accessible retail execution.

## 6. Product experience

### 6.1 Default surface

The first screen is a small, prioritized **What Matters Now** feed within the existing Terminal navigation. It is not another full website. Each card answers:

- What changed and why it reached me now?
- Which companies or themes are exposed, through what mechanism?
- What evidence supports or challenges the interpretation?
- Is a causal setup forming, already extended, invalidated or unavailable?
- What is the next observable development and what would change the view?

The feed includes unheld and unfollowed sectors within the declared universe. Personalization can reduce irrelevant alerts without turning the system into a mirror of the current watchlist. Users can inspect or change the discovery scope.

A card's strongest headline describes the actual observation: for example, broad defense outperformance with a verified shipping-risk update. It must not say an attack is imminent or a stock is a buy unless the relevant evidence and qualification support that statement.

### 6.2 Case detail

Open a dossier with an event timeline, source/correction lineage, economic exposure, market response, technical observations, expectations, alternative explanations and qualification history. Progressive disclosure keeps the initial view concise while allowing expert inspection.

Show event risk and setup quality separately. An incident can be important while the equity is too extended. A price anomaly can be worth watching while the reason is unknown. A confirmed source can have unresolved issuer exposure. These are legitimate useful states, not errors to conceal.

### 6.3 User actions

Permit saving/following a case, adding a security to an existing watchlist, opening the chart/dossier, setting supported alerts, recording a thesis or dismissing with a reason. Use the existing user-consent and thesis-revision semantics. News must not silently rewrite the user's thesis, place an order or change portfolio weights.

A notification opens the exact case/generation or an explicit corrected successor. Track delivery, display and user acknowledgment separately. User acknowledgment is not trading acceptance or evidence that a setup was executable.

### 6.4 Notification policy

Emit on material transitions, not every rebuild or price tick. Group correlated names under the incident; preserve per-security timing in the expanded view. Deduplicate retries using the existing notification owner. Corrections and invalidations must survive suppression rules; quiet-hour and user-preference behavior remains explicit.

Research default: aim to expose only a handful of materially distinct review cases per day for a typical user, but measure actual relevance and burden before making a fixed service claim. A full market shock may require a grouped incident digest rather than arbitrary truncation that hides a material risk.

### 6.5 UX acceptance

Use the existing design system, shared navigation and native components, not a new token root or header. Preserve English/Chinese semantics, dark/light support, mobile layouts, keyboard interaction and accessible status language. No status relies on color alone. Long source titles, missing fields and mixed-generation states are included in browser tests.

Production proof must use the deployed backend and an authorized real session. Test principals, mocked API payloads and a Paper mockup do not establish production entitlement or live data operation.

## 7. Runtime and reliability

The real product must run in the existing service/deployment owners, not inside a perpetually open chat. Reuse the qbus runtime and normal market-data producers. The ticker-news design assigns a single source writer to the Macro API VPS and gives the API read-only access to its store/rights receipt. Actual activation must be verified rather than inferred from that runbook. [I05]

No Kafka, new workflow engine, duplicate process supervisor or replacement retry framework is required by this plan. Add capacity only after profiling a named bottleneck. A material new infrastructure service needs its own explicit decision and migration rationale.

### Failure behavior

| Failure | Required behavior |
|---|---|
| One source unavailable | Preserve its last known eligible facts with age; expose incomplete coverage; continue independent market/source lanes. |
| Rights expire or are revoked | Stop unauthorized processing/display through the incumbent receipt gate; do not switch providers to repeat a refused use. |
| Duplicate delivery or process restart | Reconcile existing cursor/revision/notification identities; no duplicate case or alert. |
| Late source or market correction | Append revision, recompute eligible current views and preserve original issued record. |
| Partial publish | Keep the previous compatible served generation or an explicit partial state; never a mixed generation falsely labeled fresh. |
| Model failure or budget exhaustion | Use the accepted cheap/factual path and state unavailable deeper analysis; never fabricate a probability. |
| Burst traffic | Preserve corrections and material risk updates; bound enrichment work through existing queues/budgets; record defer/drop reasons. |
| Unknown modifying effect | Reconcile the original operation and carrier before retry; no replacement worker or second write. |

### Design latency objectives

Initial engineering objectives, to be measured rather than claimed: after receipt of an eligible completed market observation, a cheap discovery update should reach the read model within 60 seconds at the 95th percentile under the declared load; after a source is actually received, a factual event update should not wait for deep reasoning; deep case analysis may have a separate minutes-scale budget. Provider delay, processing delay, publication delay and notification delay are reported separately.

A fifteen-minute upstream batch cannot support a one-minute source-to-world claim. A date-only source cannot establish an intraday lead. Browser refresh frequency does not establish source freshness.

## 8. Security and model boundaries

Treat retrieved articles, filings, source metadata and model outputs as untrusted data. They cannot alter tools, credentials, prompts, budgets, file paths or authorization. Normalize URLs, bound payload sizes and decompression, reject unexpected formats, and prevent untrusted URLs from reaching internal network addresses through enrichment services.

The extraction service receives only the minimum permitted content and has no trading credentials or deployment authority. Structured outputs pass deterministic schema, number/unit, source-span and identity checks. High-impact ambiguity triggers adjudication or abstention, not a silent fallback to free text.

Tenant authorization belongs to the existing API/BFF. Cache keys include the relevant entitlement/audience context. Sign-out or account changes invalidate in-flight protected reads. Public and entitled caches do not share private portfolio or source data. Review consequential auth/rights/exactly-once changes independently; do not multiply ceremonial review stages for routine formatting.

## 9. Capacity and cost model

The following is a transparent planning scenario, not observed usage or a price quote.

Assume 2,500 covered equities and 390 regular-session minutes on a full session. That is 975,000 one-minute symbol rows per day. At 250-750 bytes per normalized row, the uncompressed base is approximately 243.75-731.25 MB/day, or 61.425-184.275 GB across 252 sessions, before indexes, replicas, raw messages, corrections or compression. Extended-hours and multiple feeds increase it. A measured schema/retention benchmark replaces these assumptions before provisioning.

Assume 20,000 raw articles/day, 40% unique case-processing items after safe deduplication, 1,500 input tokens and 250 output tokens per cheap pass: 12 million input and 2 million output tokens/day. If 1% of the 8,000 items require a 6,000-input/1,000-output deeper analysis, add 480,000 input and 80,000 output tokens/day. These estimates omit retrieval, cache writes/reads, repairs, audit and orchestration; actual receipts must include them.

The existing news-impact benchmark demonstrates why nominal per-document estimates can be misleading: its retained record reports substantial context/token consumption and an unmeasured family cost. Reuse the evidence but do not assume those costs transfer directly to a redesigned production extractor. [I11]

Use the existing Model Router/Capacity Fabric to select the least-scarce qualified route. Cache by immutable input versions. Deduplicate before reasoning. Reserve budget for corrections, validation and repair. Never multiply the root allowance across suborchestrators. Business data licensing, external display and redistribution costs remain unknown until a contract-specific quote; a retail subscription figure is not a SaaS operating budget.

## 10. Operating acceptance and handover

A release must identify the installed code, service instance, source universe, rights receipt, observation generation, API response, browser result, notification receipt, recovery path and rollback. Observe ordinary recurring runs and real material revisions, not just a manual happy-path canary. Source health, dropped/withheld reasons, latency and cost must be attributable to the correct owner.

A model can be downgraded without disabling truthful factual discovery. A single unavailable data family does not blank the whole product. Conversely, a stale source must not be cosmetically hidden behind a recent UI render time. This distinction is central to both trustworthy investor intelligence and maintainable operations.
