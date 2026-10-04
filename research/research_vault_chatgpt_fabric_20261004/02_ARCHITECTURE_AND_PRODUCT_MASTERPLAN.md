# 02 — Architecture and product masterplan

## 0. Program exit gate

The program is complete only when Mastermind has one healthy, correction-aware, rights-safe institutional research read path that:

1. proves the underlying Vault is private and internally consistent;
2. reports source freshness and retrieval coverage truthfully;
3. finds source evidence beyond the old 60,000-character prefix;
4. returns replayable literal evidence bound to exact source identity;
5. can add a current Research Intelligence projection without confusing model synthesis with source fact;
6. is consumed through one canonical service by existing Brain and the new Research MCP;
7. is reachable by an authorized ChatGPT custom app and Deep Research read/fetch path;
8. refuses unauthorized calls without private leakage;
9. passes a representative retrieval/rights/correction benchmark;
10. distinguishes source merge, deployment, app publication, connection, tool discovery, successful calls and product acceptance.

Anything less is an intermediate capability, not program completion.

## 1. Architectural thesis

Mastermind should build a **Research Intelligence Fabric**, not an R2 connector.

The target is:

~~~
SOURCE PRODUCER
    |
    v
RESEARCH VAULT
    |  canonical report identity / PDF / catalog / source clocks / rights
    |
    +-------------------------+
    |                         |
    v                         v
CANONICAL TEXT           CATALOG / METADATA
full extraction          public-safe metadata
page boundaries          source facets
source hashes            admission
    |                         |
    +-----------+-------------+
                |
                v
CANONICAL RETRIEVAL SERVICE
BM25 / filters / full-tail evidence / coverage
                |
        +-------+--------+
        |                |
        v                v
RESEARCH           RESEARCH INTELLIGENCE
LITERAL EVIDENCE   current private RIO
        |                |
        +-------+--------+
                |
                v
RIGHTS-SAFE RESEARCH READ CONTRACT
                |
        +-------+--------+
        |                |
        v                v
BRAIN             MASTERMIND RESEARCH MCP
                          |
                   +------+------+
                   |             |
                   v             v
                ChatGPT      Deep Research
~~~

Storage, text, retrieval, analysis and transport are separate layers.

The model may choose what research question to ask. It may not choose its bucket, credentials, entitlement, source revision, rights profile or evidence truth.

## 2. Frozen architectural decisions

### D1 — Research Vault remains source owner

No second report database or “ChatGPT Vault.”

### D2 — R2 is storage, not the model API

R2 keys and credentials never enter model-callable schemas.

### D3 — one logical retrieval authority

Physical storage may remain one SQLite file, become a persistent replica or shard internally after measurement. Consumers still call one canonical retrieval service.

### D4 — exact source evidence is the citation layer

Citation-bearing output resolves to held source bytes/addresses, not a model summary.

### D5 — Research Intelligence is enrichment

RIOs explain thesis, assumptions, forecasts, catalysts, falsifiers and belief/consensus relationships. They do not replace literal evidence or gain trading authority.

### D6 — existing MCP/auth owners are reused

Research code does not implement a parallel OAuth/JWT/resource-server system.

### D7 — source health is part of the answer contract

A fresh catalog timestamp cannot hide a stale producer. A live app cannot hide a partial corpus.

### D8 — correction is first-class

Every derivative is bound to exact source identity and becomes stale on correction.

### D9 — metadata enrichment is derivative

Tickers/themes/desks may be useful, but enriched values must carry provenance and cannot masquerade as publisher-supplied fields.

### D10 — embeddings are conditional

No vector database is admitted until benchmark evidence shows lexical/metadata/RIO retrieval materially underperforms and embeddings improve it.

### D11 — internal authorized canary precedes broad productization

Prove the private research workflow with an authorized internal seat first; customer distribution/quotas are a later product decision.

### D12 — product truth before “AI cleverness”

The first objective is correct source discovery and evidence. Expensive cross-report cognition is useful only after the retrieval substrate is proven.

## 3. Wave DAG

Critical path:

~~~
W0 custody/source reconciliation
        |
        v
W1 P0 Vault privacy + live integrity + source freshness
        |
        v
W2 full-text economics + canonical text decision
        |
        v
W3 replayable research segments + full-tail retrieval
        |
        +----------------------+
        |                      |
        v                      v
W4 metadata enrichment     W5 RIO correctness/producer
        |                      |
        +----------+-----------+
                   v
             W6 canonical read service
                   |
             +-----+------+
             |            |
             v            v
          Brain        Research MCP
                           |
                           v
                    W7 app/canary
                           |
                           v
                    W8 benchmark/rollout
                           |
                           v
                    W9 longitudinal intelligence
                      (#8090 and successors)
~~~

W4 and W5 may progress partly in parallel after P0 if source/path custody is independent. W9 is deliberately not on the connector MVP critical path.

## 4. W0 — current-source and carrier reconciliation

### Objective

Establish one truthful starting frontier before new implementation.

### Work

- re-pin current protected Mastermind;
- re-pin current Macro main;
- compare source movement since this packet;
- read current state/reviews/comments/checks/changed paths for #7461/#7354/#7522/#8090;
- establish path custody for:
  - engine/research_intelligence/schema.py
  - engine/research_intelligence/store.py
  - engine/research_intelligence/projection.py
  - engine/research_intelligence/vault_adapter.py
  - engine/neuralweb/brain_market_intel.py
  - engine/research_vault/*
  - relevant shared CI manifests;
- determine whether any prior modifying operation is EFFECT_UNKNOWN;
- recover current Research Vault producer/operator source.

### Acceptance

A written custody map names:

- canonical owner;
- exact carrier;
- exact head;
- current dependency;
- state: reuse / repair / superseded / independent;
- DO_NOT_REDO items.

No code change starts on a path with unresolved conflicting custody.

## 5. W1 — P0 Vault safety and truth

This wave precedes the model connector.

### W1A — private R2 isolation

Modify the canonical Research Vault store owner so production private storage cannot silently use the shared/public delivery configuration.

Desired production behavior:

- all required research-private config must be explicitly present;
- partial config refuses;
- a known shared/public bucket/endpoint binding refuses for private publication;
- no private write falls back to shared R2 variables;
- no credential appears in client-visible errors;
- local hermetic test stores remain explicit, not accidental env fallbacks.

Use PR #6625 as a design precedent only.

#### Tests

At minimum:

- no research env + shared env present -> refuse private R2 construction;
- partial research env -> refuse;
- identical research/shared destination under a public classification -> refuse;
- explicit private research destination -> construct;
- local test store -> still works explicitly;
- Research Intelligence strict store does not gain a bypass;
- no secret values in exceptions/log projections.

### W1B — live id-set/corpus census

Run the existing Research Vault census against the actual store.

Required sets:

- catalog IDs;
- canonical PDF IDs;
- corpus IDs;
- receipt IDs.

Add targeted observations only if the current census lacks them:

- corpus row count;
- empty/non-empty body count;
- text_layer distribution;
- content_sha256 population;
- page/char_count population;
- excerpt derivable count;
- corpus object bytes/hash;
- local restored bytes/hash.

#### Required classifications

Every mismatch is named, not silently repaired:

- catalog_without_pdf;
- catalog_without_corpus;
- corpus_ahead_of_catalog;
- receipt_without_catalog;
- pdf_without_catalog;
- duplicate/colliding source identity;
- body_unavailable;
- text_layer_none;
- restore/integrity failure.

A correction action is separate from census observation.

### W1C — excerpt-collapse diagnosis

Explain the observed 1,497 -> 351 event.

Possible falsifiable hypotheses include:

- partial/corrupt corpus restored from R2;
- local restore/read truncated or wrong generation;
- large subset of body rows empty/unavailable;
- excerpt derivation behavior changed;
- catalog/corpus generation skew;
- store read returned another object/generation.

Do not treat the hypothesis list as conclusions.

Acceptance:

- reproduce or falsify the event from retained/current artifacts;
- identify exact affected owner;
- prove post-repair excerpt derivation does not collapse;
- preserve good committed snapshot until the replacement is proven.

### W1D — source producer freshness

Trace newest report admission upstream.

Do not merely observe catalog publication.

Acceptance:

- identify producer/source owner;
- explain why no report newer than 2026-09-24 entered;
- restore source admission or preserve an explicit acknowledged outage state;
- keep freshness guard semantics intact.

### W1 exit gate

No real private Research MCP data canary until:

- private store binding is structurally safe;
- live corpus/canonical PDF/catalog/receipt state is understood;
- corpus restore is not known-degraded;
- source freshness state is explicit and model-visible.

The system may still be source-stale during an acknowledged producer outage, but the model must not call it current.

## 6. W2 — canonical full-text economics and text artifact

### Objective

Create one exact, reusable full-text representation per source revision without prematurely selecting an expensive retrieval backend.

### Measurement before design freeze

For the real corpus measure:

- PDF count and bytes;
- extracted full-text bytes per doc and total;
- UTF-8 text p50/p90/p95/p99/max;
- form-feed/page boundary retention;
- extraction duration distribution;
- current corpus.sqlite bytes;
- projected full-body SQLite/FTS bytes;
- compression ratio;
- cold R2 transfer time;
- warm/open/query latency;
- host disk/memory.

### Canonical text artifact

Recommended logical contract:

**research_document_text.v1**

Fields should include:

- schema;
- report_id;
- source_content_sha256;
- extractor;
- extractor_version;
- text_sha256;
- text_bytes;
- page_count;
- page_boundaries;
- extraction_state;
- extraction/recorded clock;
- optional source facts required to prove currentness.

States must distinguish:

- full_text;
- thin_text;
- no_text_layer;
- extractor_unavailable;
- extraction_failed;
- source_missing;
- oversize/refused if a hard safety bound is reached.

The artifact is derivative and invalidates on exact source-content change.

### Storage rule

Do not create one object per model call.

Materialize once per source revision.

Possible physical storage:

- R2 object per document text artifact;
- compact page/segment artifact;
- canonical extraction manifest plus index.

Choose based on measured economics.

## 7. W3 — replayable research segments and full-tail retrieval

### Objective

Make all eligible report text searchable and citeable with stable provenance.

### Segment contract

Recommended logical contract:

**research_segment.v1**

Fields:

- schema;
- report_id;
- document_version / source revision identity;
- source_content_sha256;
- text_artifact_sha256;
- segmenter_version;
- segment_index;
- page_start;
- page_end;
- segment_start_byte;
- segment_end_byte;
- segment_text_sha256;
- rights_profile;
- text or internal object reference according to storage design.

A segment must be deterministic for identical source bytes + segmenter version.

### Receipt contract

Reuse the existing receipt_for_span / source_span.v1 law:

- source SHA;
- segment SHA;
- segment byte length;
- exact span byte bounds;
- text SHA;
- replay verification.

Do not silently invent page numbers from character offsets when form-feed/page boundaries are unavailable.

For non-replayable visual/table regions, use address_only semantics rather than claiming byte proof.

### Segmenting research question

Do not freeze arbitrary token windows without measurement.

Benchmark candidate approaches on representative reports:

- page-aware paragraph accumulation;
- heading-aware section chunks where deterministic;
- fixed maximum byte/token windows with small overlap;
- preservation of tables/figure captions as separate or tagged regions.

Choose for:

- recall;
- stable identity;
- replay simplicity;
- context efficiency;
- correction behavior;
- low fragmentation of meaningful claims.

### Full-tail search

The canonical retrieval service must be able to find a known fact deliberately placed beyond the old 60k prefix.

### Physical index decision

Choose one after W2 measurement:

**A — one full SQLite FTS.**
Use if size/cold-refresh economics remain comfortably bounded.

**B — persistent synchronized API-host full FTS.**
Use if R2 remains canonical but whole-file request-time refresh is too expensive.

**C — physical sharding under one service.**
Use if archive growth demands it.

Do not make callers choose a shard.

### Search semantics

Keep deterministic lexical retrieval as the baseline:

- BM25/FTS;
- exact phrase where useful;
- institution/date filters;
- current source admission gate;
- coverage state;
- bounded result count.

Optional semantic retrieval remains a later benchmark-driven derivative.

## 8. W4 — metadata enrichment

### Problem

The producer does not currently provide useful ticker/theme/desk facets at scale.

### Goal

Earn high-quality structured facets without rewriting source history.

### Contract separation

Never overwrite source/publisher fields with model guesses.

Keep two namespaces conceptually distinct:

- source_metadata — what the publisher/sidecar actually supplied or what is byte-measured;
- derived_metadata — Mastermind enrichment with method/version/evidence/confidence/abstention.

Suggested derivative:

**research_metadata_enrichment.v1**

Possible fields:

- report_id;
- source_content_sha256;
- enrichment_version;
- security identifiers / ticker aliases;
- company entities;
- theme/subtheme IDs;
- desk/topic family;
- geographic tags;
- method;
- evidence spans/hash;
- state/confidence;
- computed_at.

### Methods

Prefer deterministic resolution first:

- exact issuer/ticker mentions;
- canonical security alias table;
- existing theme ontology aliases;
- title/institution patterns.

Use a cheap model only when deterministic methods abstain and benchmark evidence supports it.

The model may propose entities/themes; deterministic resolver must map them to canonical IDs or abstain.

### Acceptance

Before exposing a facet:

- coverage reported;
- precision measured on stratified hand-labeled sample;
- source-vs-derived distinction visible internally;
- corrections invalidate enrichment;
- no current-ticker history used as a fake historical identity when point-in-time identity matters.

Ticker filter is not “done” because every report was assigned some ticker. Abstention is valid.

## 9. W5 — Research Intelligence correctness, producer and consumer

### W5A — resolve #7461

Required before broad RIO generation.

Acceptance:

- malformed structural claim rows cannot shift support identity;
- valid claims retain exact evidence grounding;
- old well-formed artifacts remain compatible where intended;
- no silent support-index remap;
- owner review and current-base CI pass.

### W5B — reconcile/finish #7354

Retain its strongest decisions:

- deterministic cognition-head selection;
- selection independent of editorial Top Picks quota;
- canonical private PDF full-read;
- full extraction, not the 60k corpus prefix masquerading as full text;
- bounded maximum report count;
- exact-currentness guard;
- no model call on exact rerun;
- W2 strict persistence;
- immediate stop on EFFECT_UNKNOWN.

Evolve #7354 to consume the new canonical full-text artifact if W2/W3 make that cleaner than repeated pdftotext.

Acceptance real path:

- one real Vault report;
- exact canonical source;
- full extraction/current text artifact;
- W1 grounded RIO;
- W2 private persistence;
- readback;
- exact rerun with zero duplicate model call;
- one source/metadata correction path.

### W5C — reconcile/finish #7522

Required behavior:

- Brain computes exact source-body identity through the canonical owner;
- current RIO projection only when artifact source hash matches;
- available/missing/stale/invalid/unavailable remain separate;
- generic report mode may show rights-safe derived summary;
- evidence query gets literal source passages from the evidence owner;
- RIO cannot substitute text when evidence is absent;
- quota/auth denial occurs before private data access.

### W5D — RIO coverage strategy

Do not precompute frontier RIOs for all 2,778 reports by default.

Use:

- deterministic relevance/triage;
- user-demand cache;
- current research priorities;
- bounded top-N deep-read head.

Track:

- reports eligible;
- reports analyzed;
- current RIOs;
- stale RIOs;
- failed/invalid analyses;
- model spend.

## 10. W6 — canonical Research Read Service

### Purpose

Prevent Brain, MCP and future agents from independently implementing retrieval/rights/currentness.

Create a narrow service/adapter boundary whose underlying owners remain unchanged.

Logical operations:

1. status
2. search
3. fetch bounded report context
4. find literal evidence

### status result

Must include, within rights limits:

- catalog generated_at;
- report count;
- latest source published_at;
- source freshness verdict/deadline;
- corpus availability/health;
- retrieval coverage mode: prefix/full;
- full-text eligible/materialized counts;
- RIO available/current counts if cheap enough;
- typed degradation list.

### search contract

Initial safe inputs:

- query;
- institution;
- date_from;
- date_to;
- limit;
- optional cursor if needed.

Add ticker/theme/desk filters only when W4 has accepted facets.

Result item:

- report_id;
- title;
- institution;
- published_at;
- source-vs-derived facets explicitly typed;
- summary;
- retrieval match excerpt;
- source/retrieval coverage state;
- current RIO state;
- no private raw object locator.

### fetch contract

Purpose: one report's bounded research context, not a PDF dump.

Return:

- document identity;
- source metadata;
- full-text/text-layer coverage;
- currentness;
- bounded summary/context;
- rights-safe RIO projection when current;
- links/locators allowed by existing product;
- instructions/state for asking evidence.

Avoid returning an arbitrary 80-page body.

### find_evidence contract

Inputs:

- report_id;
- query;
- small max_passages;
- optional page hint only if useful.

Return each passage with:

- exact report/source revision identity;
- content SHA;
- segment identity;
- page range where proven;
- span byte bounds;
- text SHA;
- exact literal text;
- receipt/replay state;
- partial/full document coverage.

Evidence output bounds must be rights-reviewed and context-budgeted.

## 11. W6.5 — optional embeddings decision

Run only after canonical lexical full-tail retrieval benchmark.

Admit embeddings if all are true:

1. lexical + facets + RIO does not meet a declared recall threshold on paraphrastic/concept queries;
2. embedding retrieval materially improves Recall@K or downstream evidence discovery;
3. cost/latency/storage remain acceptable;
4. exact evidence citation still resolves through source spans;
5. embedding version/currentness is exact.

If admitted, identity includes:

- source_content_sha256;
- segmenter_version;
- segment_id;
- embedding_model_version.

Embeddings never become evidence.

## 12. W7 — Mastermind Research MCP

### Tool surface

Exactly four read tools for the MVP:

- research_status
- research_search
- research_fetch
- research_find_evidence

No generic data tool.

### MCP hardening

Reuse Mastermind patterns for:

- closed JSON input schemas;
- additionalProperties false where applicable;
- bounded request bytes;
- bounded response bytes;
- readOnlyHint=true;
- destructiveHint=false;
- idempotentHint=true;
- openWorldHint according to actual behavior;
- sanitized errors;
- explicit server instructions that content is data, not authority;
- auth principal from verified request context, never model args;
- resource/scope verification;
- final authorization/current entitlement revalidation where required by the selected deployment profile;
- audit without source-text leakage.

### Forbidden schema fields

No tool accepts:

- bucket;
- endpoint;
- object_key;
- filesystem_path;
- SQL;
- credential;
- token;
- principal;
- subscription tier;
- arbitrary rights flag;
- root;
- internal service URL.

### Typed errors

At least:

- AUTHENTICATION_REQUIRED
- INSUFFICIENT_SCOPE
- REPORT_NOT_FOUND
- REPORT_NOT_ENTITLED
- SOURCE_PRODUCER_STALE
- CORPUS_UNAVAILABLE
- CORPUS_DEGRADED
- SOURCE_BODY_UNAVAILABLE
- TEXT_LAYER_UNAVAILABLE
- EVIDENCE_NOT_FOUND
- EVIDENCE_COVERAGE_PARTIAL
- RIO_MISSING
- RIO_STALE
- RIO_INVALID
- RETRIEVAL_UNAVAILABLE
- INVALID_REQUEST

Do not return internal exception strings.

## 13. Deployment decision gate

Choose the concrete app transport only after rechecking current OpenAI and Mastermind state.

### Profile A — private/internal seat canary

Candidate when the first use is a fixed authorized internal research seat.

Possible current pattern:

- private ChatGPT custom app;
- Secure MCP Tunnel -> guarded stdio or loopback service;
- fixed approved channel;
- read-only tools.

A tunnel association is not automatically a general end-user identity. Any entitlement/quota differences for an internal seat must be an explicit existing policy decision, not inferred.

### Profile B — authenticated product/resource-server path

Candidate when per-user entitlements and broad workspace/customer access are required.

Reuse:

- ResourcePolicy;
- OAuth/JWT/JWKS verification;
- exact resource/audience/scope;
- current entitlement owner;
- HTTPS or supported private transport according to current accepted deployment.

Do not build a custom authorization server when the existing IdP/resource stack suffices.

### Gate outputs

Record separately:

- server build identity;
- transport profile;
- auth policy identity;
- app generation;
- workspace/account enrollment;
- tool snapshot;
- connection state;
- first successful call.

## 14. W8 — ChatGPT and Deep Research canaries

### Authorized ChatGPT journey

Use a real institutional-research question.

Required steps:

1. call research_status;
2. search;
3. fetch one or more reports;
4. ask evidence;
5. synthesize with exact citations/attribution;
6. preserve source freshness/coverage caveats;
7. optionally use current RIO derived context;
8. confirm no full-document dump occurred.

### Denied journey

Test:

- no credential/channel;
- wrong scope;
- non-entitled identity where applicable;
- unknown report;
- stale/invalid RIO;
- corpus degraded.

Verify absence of:

- private titles if policy forbids them;
- body text;
- private RIO;
- R2 key;
- bucket;
- credentials;
- internal path;
- exception trace.

### Deep Research journey

Use one cross-source chronology task.

Deep Research must:

- use Research app only for read/fetch;
- search public sources independently;
- separate Mastermind Vault evidence from external evidence;
- attribute/cite literal Vault evidence within rights limits;
- not require manual PDF upload.

Do not claim Agent mode integration; current platform behavior differs.

## 15. W8.5 — retrieval evaluation

Build a frozen benchmark before rollout.

Strata:

- short vs long reports;
- large vs small institutions;
- head evidence vs evidence beyond 60k;
- exact lexical query;
- paraphrase/concept query;
- ticker/company;
- theme/subtheme;
- date/institution facet;
- corrected document;
- scanned/no-text document;
- false-positive negative queries;
- multi-report chronology;
- current vs stale RIO;
- rights-denied case.

Metrics:

- Recall@K;
- MRR/nDCG where useful;
- evidence hit rate;
- exact receipt replay rate;
- tail-evidence recall;
- false-source/citation rate;
- partial-coverage disclosure accuracy;
- query p50/p95 latency;
- response bytes;
- model context bytes;
- RIO/model cost.

No benchmark claim should use same-question tuning without disclosing it.

## 16. W9 — longitudinal institutional belief intelligence

After MVP acceptance, reconcile #8090 and successors.

Target:

~~~
institution + desk + canonical security
              |
              v
     newest strictly earlier report
              |
              v
grounded claim/RIO comparison
              |
              v
belief transition
~~~

Possible derived outputs:

- forecast introduced/removed;
- assumption changed;
- catalyst added;
- risk/falsifier changed;
- direction reversed;
- target/estimate language changed;
- consensus relationship changed.

Preserve point-in-time security identity and source clocks.

This later capability can feed Theme Intelligence, company dossiers, earnings, Prophet context and news prioritization. It remains context until those consumers earn separate authority.

## 17. Rights and redistribution law

Existing Research Vault product law already recognizes third-party copyright/rights as a material boundary.

This program must preserve:

- access control;
- attribution;
- bounded literal excerpts;
- private storage;
- derived-vs-verbatim distinction;
- existing download/view policy;
- no source-rights widening through transformation.

A model-generated summary is not a legal permission layer.

If a target app/workspace changes who can receive the content, that is a rights/product decision gate before rollout.

## 18. Time and correction contract

Every response/artifact must keep these clocks conceptually separate where available:

- published_at — when the source made the information knowable;
- ingested/recorded_at — when Mastermind received/recorded it;
- computed_at — when a derivative was produced;
- catalog generated_at — when the current projection was published.

Do not use catalog generated_at as a substitute for source freshness.

Minimum derivative identity:

- report_id;
- source_content_sha256;
- derivative method/version.

Source correction invalidates:

- canonical text artifact;
- research segments;
- evidence index;
- derived metadata;
- RIO currentness;
- optional embeddings;
- longitudinal comparisons that consumed the changed revision.

Preserve prior evidence/history; do not overwrite away the fact that an old analysis once existed.

## 19. Context economics

Target request pattern:

~~~
deterministic search
    -> 10-30 candidates
metadata / RIO state
    -> 3-8 reports
literal evidence fetch
    -> bounded evidence packet
frontier synthesis
~~~

Avoid:

~~~
download dozens of PDFs
    -> megabytes of context
frontier model searches for sentences itself
~~~

Reserve expensive models for:

- thesis reconstruction;
- contradiction;
- cross-report synthesis;
- belief changes;
- causal integration with public evidence.

Use deterministic systems for:

- identity;
- currentness;
- filtering;
- literal retrieval;
- receipt validation;
- entitlement;
- correction detection.

## 20. Observability

Record bounded operational telemetry without storing unnecessary licensed text:

- tool;
- principal/channel digest;
- query class/hash where policy permits;
- result count;
- report IDs where allowed;
- source revision;
- retrieval mode;
- full/partial coverage;
- source freshness state;
- RIO state;
- latency;
- response bytes;
- typed failure.

Never log:

- bearer/refresh tokens;
- R2 secrets;
- raw authorization headers;
- arbitrary full report bodies;
- unbounded evidence packets;
- hidden model chain of thought.

## 21. Cost controls

No mass frontier backfill.

Use exact-currentness cache keys including:

- source body/content SHA;
- document metadata identity;
- prompt version;
- requested model/version.

Top-N cognition head stays bounded.

Metadata enrichment should prefer deterministic/cheap paths.

Embedding backfill happens only after admission.

## 22. Program pre-mortem

### Failure 1 — connector built on a partial corpus

Tripwire: id-set/corpus/excerpt health P0 gate.

### Failure 2 — private content routes to shared/public R2

Tripwire: canonical store refuses fallback and public-equivalent destinations.

### Failure 3 — “ticker filter” looks impressive but is fabricated

Tripwire: source vs derived metadata separation; coverage/precision reported; abstention allowed.

### Failure 4 — RIO analysis cites the wrong claim

Tripwire: #7461 correctness gate before broad producer rollout.

### Failure 5 — RIO prose substitutes for absent evidence

Tripwire: literal evidence service remains separate; Brain/MCP tests fail closed.

### Failure 6 — full-text expansion makes every API process download a huge SQLite file

Tripwire: W2 size/latency measurement before physical architecture freeze.

### Failure 7 — vector search becomes the source of truth

Tripwire: evidence always resolves through source span; embeddings are optional derivative.

### Failure 8 — ChatGPT app “works” but bypasses rights/entitlements

Tripwire: principal/channel binding and entitlement owner tested independently from tool discovery.

### Failure 9 — source feed stays dead while AI reports look fresh

Tripwire: research_status surfaces producer freshness; acceptance uses source clock.

### Failure 10 — Fable becomes routine code labor and loses principal bandwidth

Tripwire: 03 decomposes bounded work and reserves Fable for judgment/integration.

## 23. Final architecture invariant

The system must be able to answer two questions independently:

1. **What does Mastermind believe this source means?**
2. **What did the source actually say, and can we replay the evidence?**

If either answer can silently replace the other, the architecture is not accepted.
