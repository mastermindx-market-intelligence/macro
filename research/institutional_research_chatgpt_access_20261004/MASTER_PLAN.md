# Master Plan — Institutional Research Vault to ChatGPT / Deep Research

**Program:** qualitative-intelligence  
**Capability:** institutional research intelligence access  
**Plan date:** 2026-10-04  
**Plan state:** EXECUTION_READY_RECORD / NOT_STARTED  
**Protected procedure source at final architecture freeze:** Mastermind@17b9fa1363db6071d338be3373a4fdb11fc0076d  
**Planning branch base:** Macro@bd118c69cc031b33d73b756f95eb5d3723a9dceb

## 0. Executive decision

Mastermind already owns most of the system needed to give frontier models institutional-research access.

Do not build a new R2 research platform.

Do not mirror the entire research estate into Google Drive.

Do not build a parallel vector database as the first move.

Do not expose S3/R2 primitives to ChatGPT.

Do not create a second Research Intelligence store, document identity, entitlement database, OAuth system, lifecycle, queue, retry plane, or memory service.

The build should extend four incumbent owners:

1. Research Vault — canonical source identity, private PDF/body, catalog, corpus, access and literal evidence.
2. Research Intelligence — private grounded source interpretation and correction-safe derived cognition.
3. a new thin canonical Research Read Service inside the existing Research Vault domain — one model/consumer-safe interface over source retrieval and RIO state.
4. Mastermind's existing authenticated MCP transport — a separate read-only Research app/resource that adapts the Research Read Service for ChatGPT and Deep Research.

Brain and the Research MCP become sibling consumers of the same Research Read Service. Neither becomes the other's authority.

## 1. North Star

An authorized frontier model should be able to ask:

- What institutional reports discuss a company, subtheme or economic mechanism?
- What exactly did each source say?
- Which source said it first?
- What changed between reports?
- Which assumptions or forecasts differ?
- Is the evidence literal source text or Mastermind model synthesis?
- When was the source published, ingested and analyzed?
- Is the Vault current, partially covered, scanned, stale or degraded?
- Can the exact evidence be replayed against the same document revision?

A useful final answer should be built from a small, bounded set of exact source evidence rather than from dumping dozens of PDFs into context.

The system should support a research workflow like:

query
-> deterministic/hybrid candidate retrieval
-> bounded candidate metadata
-> exact source-evidence retrieval
-> optional rights-safe RIO context
-> multi-source frontier synthesis

The model should never need R2 credentials or arbitrary object-store access.

## 2. Product acceptance target

The first production target is an internal/authorized read-only Mastermind Research app for ChatGPT.

The same read contract should subsequently serve:
- ChatGPT Pro custom MCP use;
- Deep Research read/fetch;
- Mastermind Brain;
- later native Mastermind agents;
- later customer/agent API products only after rights and entitlement review.

The initial app is not a trading tool. It is research/context infrastructure.

## 3. Canonical architecture

Target logical architecture:

~~~text
MarketDesk / other admitted institutional sources
        |
        v
Private Research R2
        |
        v
Research Vault
  - document identity
  - canonical PDF
  - catalog metadata
  - source clocks
  - existing FTS corpus
  - entitlements
  - literal evidence
        |
        +-----------------------------+
        |                             |
        v                             v
Canonical full-text derivative    Research Intelligence
NEW bounded derivative            existing private RIO
  - exact source SHA                - grounded claims
  - page boundaries                 - thesis / assumptions
  - extractor version               - forecasts / catalysts
  - full text                       - falsifiers / implications
        |                            - correction-safe persistence
        v                             |
Deterministic research segments      |
NEW bounded derivative               |
  - stable segment ID                |
  - page range                       |
  - byte range                       |
  - segment text SHA                 |
  - replayable receipt               |
        |                             |
        +-------------+---------------+
                      v
             Research Read Service
             one canonical read port
                      |
             +--------+---------+
             |                  |
             v                  v
          Brain             Research MCP
                            thin adapter
                                |
                                v
                      ChatGPT / Deep Research
~~~

## 4. Ownership law

### 4.1 Research Vault remains source authority

Research Vault owns:
- report identity;
- source PDF;
- source-content hash;
- publication/ingestion state;
- metadata;
- source retrieval;
- literal source evidence;
- private object-store location;
- access/entitlement semantics.

No Research MCP component may create a new document identity or independently decide source correction/currentness.

### 4.2 Research Intelligence remains derived-cognition authority

Research Intelligence owns:
- model-derived source interpretation;
- grounding against exact source body;
- source-claim versus model-synthesis distinction;
- correction-safe RIO history;
- rights-safe projections;
- longitudinal research cognition when later admitted.

Research MCP may expose approved projections. It must not copy or fork RIO logic.

### 4.3 Research Read Service is an interface, not a new owner

The read service should be a deterministic SDK-free domain adapter.

It may compose:
- catalog;
- corpus/full-text search;
- exact source-evidence selector;
- report metadata;
- RIO availability/currentness;
- entitlement/rights result supplied by the trusted caller context.

It must not own:
- credentials;
- OAuth;
- R2 client selection;
- model routing;
- retries;
- lifecycle;
- task queues;
- new persistence.

### 4.4 MCP owns transport only

The Mastermind Research MCP should own:
- static tool schemas;
- authenticated caller adaptation;
- bounded input/output;
- transport;
- tool annotations;
- sanitized errors;
- final request authorization checks required by current MCP law.

It must not implement research semantics that belong in Macro.

## 5. Current-state capability ledger

Research Vault ingestion: PARTIAL
- ingestion engine and publication are live;
- current source inflow is PRODUCER_STALE.

Research Vault catalog: PROVEN_LIVE for publication
- 2,778 rows;
- catalog can republish hourly.

Research Vault corpus: PARTIAL
- current corpus publishes;
- only first 60k characters per body are indexed;
- current excerpt derivation collapse indicates an unresolved corpus/body completeness issue.

Literal source evidence: BUILT / merged, production degree to re-prove on current corpus
- R1B source-bound evidence is merged;
- evidence coverage is limited by current stored body.

Full-document source retrieval: PARTIAL
- canonical private PDFs exist;
- #7354 already contains a bounded full-PDF deep-read implementation;
- no general canonical full-tail search/segment service is merged.

Research Intelligence W1/W2: BUILT_NOT_PROVEN as a broad live estate
- source implementation merged;
- live corpus-wide persistence coverage is not established.

Brain RIO consumer: BUILT_NOT_PROVEN / open carrier #7522.

ChatGPT Research MCP: NOT_BUILT.

ChatGPT Research app production canary: NOT_BUILT.

Deep Research Vault canary: NOT_BUILT.

## 6. Critical-path separation

There are three related but separable tracks.

### Track A — source integrity and external-read safety

This is the hard blocker for external exposure:
- private R2 fail-closed;
- live R2 census;
- source-freshness truth;
- corpus/body completeness;
- full-document search/evidence.

### Track B — derived institutional cognition

This improves answer quality but does not block basic source access:
- #7461 claim identity;
- #7354 top-N RIO production;
- #7522 Brain RIO consumption;
- later W5/W6 longitudinal and panel cognition.

### Track C — external ChatGPT transport

This can begin contract/source work in parallel after the read-service shape is frozen:
- Research read schemas;
- Mastermind MCP adapter;
- OAuth resource/scope;
- Secure MCP Tunnel deployment;
- ChatGPT app canary;
- Deep Research canary.

Do not serialize Track B ahead of every Track A/C capability.

A useful first ChatGPT canary can retrieve literal Research Vault evidence even if only a subset of reports has RIOs.

## 7. P0 — private Research R2 must fail closed

### Problem

Current canonical store supports research-specific credentials but falls back to shared R2 variables when absent.

That is incompatible with expanding access to licensed/private institutional content.

### Required change

The production Research Vault store must require a complete dedicated private research configuration.

The exact environment names already exist:
- R2_RESEARCH_ENDPOINT
- R2_RESEARCH_ACCESS_KEY_ID
- R2_RESEARCH_SECRET_ACCESS_KEY
- R2_RESEARCH_BUCKET

The canonical builder must distinguish:
- dedicated private research store configured;
- explicit local/test store;
- no research store configured.

It must not silently reinterpret missing private config as the shared public delivery store.

### Required refusal tests

Prove:
1. all research variables present -> configured private client can be built;
2. zero research variables -> production private store refuses;
3. partial research variables -> refuses;
4. private endpoint/bucket aliases a known shared/public delivery binding -> refuses;
5. shared variables alone -> cannot construct a production research store;
6. errors never expose access key/secret/endpoint credentials;
7. explicit test/local stores remain available through their existing deliberate path rather than implicit env fallback.

### Migration constraint

Because existing legitimate deployments may rely on old fallback behavior, implement a deliberate compatibility/migration step:
- census current GitHub Actions and macro-api deployments;
- confirm dedicated research vars are present before enforcing fail-closed;
- if an intended same-account private bucket exists, configure it explicitly as research-specific variables rather than relying on fallback.

Do not leave an “allow_shared_fallback=true” model-visible or ambient production escape hatch.

### P0 acceptance

P0 closes when:
- code structurally refuses shared fallback;
- tests prove it;
- the real hourly Research Vault workflow still reaches the intended private bucket;
- the real API read path still reaches the intended private bucket;
- no public/shared R2 path can serve a private Research object through the new app.

## 8. P0 — live Vault ID-set census

Use the existing workflow-dispatch census.

Do not build a new script.

Run the existing research-ingest workflow with:
- run_census = true

Retrieve the uploaded JSON artifact.

Classify:
- catalog minus PDF;
- PDF minus catalog;
- receipt minus catalog;
- catalog minus corpus;
- corpus minus catalog;
- duplicate or malformed identities where the census reports them.

Also capture:
- private PDF count;
- private PDF bytes if available;
- corpus.sqlite bytes;
- processed-receipt count;
- any read/list errors.

### Required rule

Do not repair a mismatch until its owner and correction semantics are understood.

Examples:
- a receipt outside catalog may be stranded publication state;
- a catalog row without a PDF is not equivalent to a PDF outside catalog;
- a corpus row outside catalog must not become model-discoverable merely because search can see it.

### Acceptance

Every non-empty set difference is either:
- repaired through the canonical owner; or
- typed, explained, bounded and intentionally preserved.

## 9. P0/P1 — diagnose source staleness

Current evidence:
- newest source is September 24;
- hourly publication is alive;
- no new reports are being admitted.

Investigate the source pipeline from the upstream producer to Research Vault inbox.

Distinguish:
- MarketDesk acquisition stopped;
- producer can acquire but cannot publish;
- credentials/auth expired;
- scheduler stopped;
- extractor state wedged;
- source itself intentionally stopped;
- R2 inbox route changed;
- a safety/rights gate is intentionally holding publication.

Do not increase RESEARCH_VAULT_SOURCE_MAX_AGE_HOURS as a substitute for diagnosis.

The existing outage acknowledgement is acceptable only as an explicit operational degradation signal when the producer outage is known.

### Acceptance

Either:
- current reports resume and freshness passes naturally; or
- source remains intentionally unavailable with a durable typed outage and the Research app displays that exact degradation.

No production claim of “current institutional research” is allowed while the source is stale.

Historical-research capability may still be canaried if the app reports currentness honestly.

## 10. P0/P1 — diagnose excerpt/corpus collapse

Current guard observes 1,497 committed excerpts versus 351 derivable.

This is a valuable failure signal.

### Diagnostic ladder

1. Run live ID-set census.
2. Inspect corpus document count.
3. Inspect body non-empty count.
4. Inspect text_layer distribution:
   - full
   - thin
   - none
   - unavailable
5. Compare current body-bearing IDs against committed excerpt IDs.
6. Sample:
   - IDs that still derive excerpts;
   - IDs that lost excerpt derivation;
   - long/short reports;
   - known historical repair cohort from the pdftotext outage.
7. Establish whether the cause is:
   - missing corpus rows;
   - empty/truncated body state;
   - corpus restore/version mismatch;
   - extraction regression;
   - text-layer reality;
   - excerpt derivation regression.
8. Repair the canonical owner.
9. Re-run exact census and excerpt snapshot.

Do not lower the 50% collapse floor.

### Acceptance

A fresh current corpus produces a non-collapsed excerpt snapshot or a documented intentional count reduction supported by source identity/correction evidence.

## 11. P1 — resolve RIO claim-identity correctness

PR #7461 reproduced a semantic integrity defect.

This is a narrow but important gate before broad RIO production.

### Required action

Reconcile #7461 against current main and incumbent path custody.

Adjudicate the intended rule:
- structurally malformed/blank claim rows are rejected before positional support can shift;
- structurally valid claims continue to use the existing grounding/remap behavior.

### Acceptance

- exact-head/current-base tests green;
- independent owner review accepts the semantic rule;
- merged through normal release;
- a valid RIO remains valid;
- a malformed claim array cannot silently change support identity.

Do not bulk-generate new RIOs before this is closed.

## 12. P1 — canonical full-document text derivative

The current corpus body is intentionally capped.

Do not simply change BODY_MAX_CHARS from 60,000 to a huge constant without measuring deployment effects.

Create a canonical full-document extraction derivative bound to the source PDF.

Proposed logical contract:

research_document_text.v1

Required fields:
- report_id;
- source_content_sha256;
- extractor identity/version;
- extraction timestamp;
- extracted_text_sha256;
- page count;
- page-boundary map;
- text_layer state;
- byte/character count;
- full extracted text or content-addressed reference;
- correction/source-revision identity.

### Extraction law

- identical source bytes + same extractor generation should produce stable identity;
- do not silently normalize away source differences that matter to evidence replay;
- preserve form-feed/page boundaries where pdftotext supplies them;
- no OCR-derived text is labeled byte-replayable source text;
- failures are typed;
- source correction creates a new derivative identity.

### Backfill

Backfill all eligible canonical PDFs incrementally.

The process must:
- be restartable/idempotent;
- skip exact-current derivatives;
- not rewrite source PDFs;
- not use model calls;
- preserve old derivative versions when source revision changes.

### Acceptance

For a representative long report, a sentence located beyond the old 60k corpus prefix is available through the full-text derivative and is bound to the exact source PDF hash.

## 13. P1 — deterministic research segments and receipts

Build stable source-bound segments over canonical full text.

Proposed logical contract:

research_segment.v1

Fields:
- report_id;
- source_content_sha256;
- text_artifact_sha256;
- extractor_version;
- segmenter_version;
- segment_index;
- page_start;
- page_end;
- start_byte;
- end_byte;
- segment_text_sha256;
- text;
- receipt/replay state.

### Design law

Borrow the existing source_span.v1 discipline.

Segment parameters should be chosen by benchmark, not habit.

The segmentation must be:
- deterministic;
- stable for identical source bytes;
- page aware;
- bounded;
- replayable;
- correction safe;
- independently addressable.

Do not use random chunk IDs.

Do not make model-generated headings or summaries part of segment identity.

### Tests

Include:
- ASCII;
- Unicode/UTF-8;
- page boundaries;
- segment spanning page boundary when allowed;
- malformed form-feed layout;
- source revision;
- text-artifact revision;
- segmenter version bump;
- scan/no-text document;
- duplicate report body under distinct document IDs;
- exact byte replay.

## 14. P1/P2 — choose the physical full-text search architecture by measurement

Before selecting infrastructure, measure:
- total extracted UTF-8 bytes;
- compressed bytes;
- current 60k corpus.sqlite size;
- projected full-body FTS size;
- write/build duration;
- cold download duration;
- warm search latency;
- process memory;
- R2 transfer volume;
- update cost for one new report;
- query quality on a fixed benchmark.

Candidate physical implementations:

### A. one expanded SQLite FTS artifact

Use if full corpus remains small enough for current read-through deployment.

### B. persistent synchronized local FTS replica

Use if full corpus is too large to download per process generation but fits comfortably on the API host.

R2 remains authoritative; local replica is a retrievable derivative.

### C. sharded index behind one service

Use only if size/latency actually demands it.

No consumer sees shard identities.

### Rejected first move

A vector database is not the default architecture.

Lexical full-text + metadata + RIO may already satisfy most research questions.

## 15. P2 — canonical retrieval benchmark

Build a fixed internal benchmark before adding semantic retrieval.

Cases must include:
- exact title/institution queries;
- ticker/security queries where metadata exists;
- head-of-document source evidence;
- tail evidence beyond 60k;
- paraphrase queries;
- theme/mechanism queries;
- report-specific evidence queries;
- negative/no-match queries;
- corrected-source queries;
- long multi-section reports;
- multi-report candidate retrieval;
- stale-source behavior;
- scanned/no-text documents;
- rights-denied requests.

Metrics:
- Recall@K;
- MRR or nDCG where useful;
- evidence replay rate;
- false-source rate;
- tail recall;
- latency;
- result bytes;
- model-context bytes;
- source coverage state correctness.

### Embeddings admission rule

Only add embeddings if the benchmark shows a material deficiency that full-text lexical + metadata + RIO cannot solve economically.

If admitted, embedding identity must bind:
- source_content_sha256;
- segmenter_version;
- segment_id;
- embedding_model_version.

Embeddings are candidate-retrieval derivatives, never evidence.

## 16. P2 — Research Read Service

Create one canonical SDK-free model/consumer read port inside the Research Vault domain.

Exact file placement should be chosen after current collision census; a likely shape is an engine/research_vault read-service module plus focused tests.

### Service operations

Logical operation 1: status

Returns bounded:
- catalog generated time;
- latest source publish time;
- source freshness state;
- report count;
- searchable report count;
- full-text coverage counts;
- text-layer coverage;
- RIO coverage/currentness count if cheaply available;
- known degraded planes.

Logical operation 2: search

Inputs:
- query;
- date range;
- institution;
- desk;
- ticker/company/security when supported;
- tags/theme fields when supported;
- limit;
- cursor.

Outputs:
- report ID;
- title;
- institution;
- desk where known;
- published_at;
- supported metadata;
- match excerpt;
- source/full-text coverage state;
- RIO state;
- pagination cursor.

Logical operation 3: fetch

Inputs:
- report_id;
- bounded selector such as pages/segments/summary mode.

Outputs:
- exact document identity;
- metadata;
- source-content SHA;
- coverage;
- bounded source content;
- optional rights-safe RIO projection.

Logical operation 4: find evidence

Inputs:
- report_id;
- query;
- bounded max passages.

Outputs:
- literal passages;
- report/source identity;
- source-content SHA;
- page range;
- segment/span receipt;
- exact text hash;
- coverage/tail state.

### Service invariants

- no R2 keys in outputs;
- no credentials;
- no filesystem paths;
- no generic SQL;
- no model routing;
- no arbitrary body dumps;
- no consumer-selected entitlement;
- no consumer-selected bucket;
- no consumer-selected source root;
- no private RIO claim text unless the approved projection explicitly allows it;
- deterministic failures.

### Typed states

Recommended vocabulary:
- OK
- AUTHORIZATION_REQUIRED at external layer
- REPORT_NOT_FOUND
- REPORT_NOT_ENTITLED
- SOURCE_STALE
- SOURCE_BODY_UNAVAILABLE
- TEXT_LAYER_NONE
- TEXT_EXTRACTION_UNAVAILABLE
- FULL_TEXT_NOT_MATERIALIZED
- EVIDENCE_NOT_FOUND
- EVIDENCE_COVERAGE_PARTIAL
- RIO_MISSING
- RIO_STALE
- RIO_INVALID
- RETRIEVAL_UNAVAILABLE

Do not overload an empty array to mean five different failure states.

## 17. P2 — revive the institutional RIO producer

PR #7354 already contains much of the correct bounded producer.

After #7461 and private-store safety:
- recover #7354;
- rebase/reapply minimally against current main;
- preserve full-PDF source-body read;
- preserve bounded top-N;
- preserve exact-current no-model-call optimization;
- preserve exact predecessor correction;
- preserve stop-on-EFFECT_UNKNOWN;
- run one real authorized private report end-to-end;
- prove exact rerun produces zero duplicate model work.

### Role in the architecture

RIO is an optional cognition layer.

The Research app must still return source evidence when no RIO exists.

## 18. P2/P3 — finish Brain rights-safe RIO consumption

Reconcile #7522.

Required semantic contract:
- generic report view may include rights-safe RIO summary state;
- specific evidence query always uses literal source evidence;
- RIO state may never substitute for missing literal evidence;
- blank/unavailable source body must not become a fake current hash;
- output whitelist prevents future projection widening from leaking private fields;
- one existing quota/entitlement contract remains authoritative.

After merge, consider moving Brain retrieval mechanics behind the same Research Read Service so Brain and MCP do not drift.

Do not force that convergence as a huge rewrite if a narrow adapter can preserve current Brain behavior.

## 19. P2/P3 — Mastermind Research MCP

Implement in the Mastermind repository, reusing current production-proven MCP/OAuth patterns.

Suggested package boundary:

integrations/mastermind_research_mcp/

Prefer the established separation:
- schemas.py — static SDK-free schemas/limits;
- adapter.py — trusted read-service binding;
- server.py — only MCP SDK import;
- service/deployment module only if current incumbent deployment owner requires it;
- focused tests.

### External tool surface

Expose four read-only tools:

research_status
research_search
research_fetch
research_find_evidence

These names are a Mastermind semantic choice. They are not an assertion that OpenAI requires exact search/fetch names.

### Input constraints

Models may provide research query intent.

Models may not provide:
- OAuth subject;
- account ID as authority;
- entitlement;
- bucket;
- R2 endpoint;
- R2 key;
- filesystem root;
- credential;
- internal service URL;
- raw SQL;
- arbitrary file path.

Trusted caller identity and rights come from authenticated server context.

### Output limits

Freeze explicit:
- max request bytes;
- max response bytes;
- per-tool max items;
- per-passage max chars;
- pagination rules;
- maximum report-context chars;
- allowed output fields.

Prefer a small response with a cursor to one giant result.

### Tool annotations

All four tools:
- readOnlyHint = true
- destructiveHint = false
- idempotentHint = true
- openWorldHint = false where current SDK semantics fit.

## 20. P3 — dedicated Research OAuth resource/app

Do not piggyback on the existing Executive MCP resource or authority.

Reuse:
- integrations/business_mcp_auth;
- existing resource policy patterns;
- JWT verification;
- protected resource metadata;
- PKCE/resource binding;
- existing ChatGPT Business production deployment precedent.

Create a dedicated read-only Research resource and scope through the current owner.

Proposed semantic scope:
- mastermind.research.read

The exact URI and policy identifiers are not frozen by this plan. The implementation owner must harmonize them with current production conventions.

### Security acceptance

Prove:
- wrong audience refused;
- missing scope refused;
- expired token refused;
- wrong resource refused;
- authenticated but non-entitled report body refused;
- metadata exposure matches approved policy;
- no source body appears in auth errors;
- no secret appears in logs/errors.

## 21. P3 — transport and deployment

OpenAI custom MCP requires remote reachability.

Use the incumbent Mastermind private-MCP deployment pattern unless current source proves a better accepted owner.

Secure MCP Tunnel is the preferred path for a private/local Mastermind service.

Do not expose a raw unauthenticated Cloudflare Worker merely because R2 is already on Cloudflare.

Deployment proof sequence must remain separate:

source
-> built service
-> service installed
-> tunnel/reachability
-> app publication
-> OAuth connection
-> app installed/selected
-> successful tool discovery
-> successful authorized read
-> denied-path proof
-> Deep Research proof
-> production acceptance

No single step substitutes for later steps.

## 22. P3 — ChatGPT canary

First canary: normal ChatGPT read-only custom app.

Use an internal authorized account/workspace that current product policy supports.

### Positive journey

Ask a question that requires:
1. search;
2. select multiple reports;
3. fetch one report;
4. find exact evidence;
5. compare at least two institutions;
6. disclose current Vault freshness.

Acceptance:
- returned report IDs exist;
- evidence text replays against exact source revision;
- result remains bounded;
- source/RIO epistemic layers are distinguishable;
- no R2 locator/credential/path leaks;
- source staleness is visible.

### Negative journey

Test:
- disconnected user;
- authenticated user with missing research scope;
- non-entitled body request;
- unknown report;
- stale RIO;
- no-text report;
- no evidence match.

No private body or locator leakage.

## 23. P3 — Deep Research canary

Run a real mixed-source research assignment.

Recommended benchmark problem:

“Reconstruct when the optical-networking / datacenter-photonics earnings thesis became discoverable during the last several months. Search our institutional research, identify the earliest source changes in demand/earnings expectations, cite exact institutional evidence, then reconcile with public company, filing, government and web evidence. Distinguish what was internally licensed research from public evidence.”

Required behavior:
- Deep Research searches the Research app;
- retrieves exact institutional reports;
- fetches bounded evidence;
- searches public web sources;
- distinguishes evidence families;
- preserves dates;
- makes no claim that internal and public sources are independent when they are not;
- no manual PDF upload.

## 24. Rights and licensing control

Third-party institutional research requires explicit rights discipline.

Rules:
- derived representations never widen rights;
- an embedding is still derived from licensed source;
- an RIO is not automatically public because it is model-generated;
- literal excerpts remain bounded;
- public-safe catalog remains a distinct projection from private body;
- internal model context and user-visible response may have different permitted fields;
- external/customer distribution requires the current product/legal owner to affirm the projection.

The internal Fable build must not silently reinterpret “technically readable by ChatGPT” as “redistributable to every user.”

## 25. Correction and point-in-time law

For every derivative:

minimum identity =
report_id + source_content_sha256

A corrected source must make old:
- full-text artifact;
- segments;
- evidence;
- embeddings;
- RIO;
- transition comparisons

detectably historical/stale.

Never overwrite history to make current state look clean.

Preserve distinct clocks:
- published_at — source publication;
- ingested_at / first seen — Mastermind acquisition;
- computed_at — derived processing;
- query/request time — consumer observation.

Do not use current metadata to rewrite what was knowable historically.

## 26. Observability

Use the existing logging/metrics owner where practical.

Useful bounded fields:
- tool;
- caller digest, not raw identity/token;
- request class;
- result count;
- report IDs when policy permits;
- source revision;
- source freshness state;
- full-text coverage state;
- RIO state;
- duration;
- bytes returned;
- typed failure code.

Do not log:
- raw bearer tokens;
- refresh tokens;
- R2 keys;
- source body by default;
- arbitrary full model prompts containing licensed report text;
- credentials;
- secrets.

## 27. Cost model

The economics should be retrieval-first.

Cheap deterministic layer:
- metadata;
- lexical search;
- filters;
- hashes;
- full-text segment retrieval;
- currentness;
- source evidence.

Cached derived cognition:
- RIOs;
- later longitudinal transitions;
- later embeddings if admitted.

Frontier model:
- cross-report synthesis;
- difficult reconciliation;
- research conclusions.

Target context pattern:

all reports
-> 10–30 bounded candidates
-> 3–8 highly relevant sources
-> 10–30 exact evidence passages
-> frontier synthesis

Do not pay a frontier model to discover relevant sentences inside 50 whole PDFs.

## 28. Delegation architecture

Fable is justified as principal orchestrator, not default coder.

Routing classification:

TASK_COMPLEXITY: C3_FRONTIER_JUDGMENT  
BUSINESS_IMPACT: critical  
EXECUTION_RISK: elevated, with critical privacy/rights substeps  
AMBIGUITY: medium-high  
TOPOLOGY: coordinator  
FRONTIER_WITNESS: cross-repository source/auth architecture, private licensed-data boundary, multiple held source carriers, and production ChatGPT canary integration

WHY FABLE:
The parent requires sustained principal-level reconciliation across Research Vault, Research Intelligence, Brain, Mastermind MCP/OAuth, existing open carriers, and live data defects. A routine worker should not adjudicate those system boundaries independently.

### Delegate bounded work

Use the least-scarce capable worker after Fable freezes each slice.

Good independent lanes:

A. Vault privacy/integrity
- R2 fail-closed;
- live census;
- corpus/excerpt diagnosis.

B. Full-text/retrieval
- size measurements;
- full-text derivative;
- segment receipts;
- benchmark.

C. RIO recovery
- #7461;
- #7354;
- #7522.

D. MCP/auth
- Research Read Service contract;
- Research MCP package;
- dedicated resource/scope;
- transport tests.

E. Verification
- adversarial rights/privacy review;
- ChatGPT canary;
- Deep Research canary.

### One-writer rule

Do not assign two active modifiers to:
- r2_store.py;
- corpus.py;
- Research Intelligence schema/store;
- Brain path;
- shared CI manifest;
- MCP auth policy;
- the same open PR.

Reviewers remain read-only unless a separate repair commission is admitted.

## 29. Dependency DAG

Hard dependency:

P0 private R2 safety
-> external Research body access

Live census
-> trustworthy integrity diagnosis
-> full-text backfill acceptance

Corpus/excerpt diagnosis
-> trustworthy “full source coverage” claim

#7461
-> broad RIO production/backfill
-> #7354 live cognition wave

Canonical full text
-> deterministic segments
-> full-tail search/evidence
-> high-quality Research Read Service

Research Read Service
-> Research MCP

Research MCP + dedicated OAuth + private transport
-> ChatGPT canary
-> Deep Research canary

Independent/parallel where safe:

#7522 Brain RIO consumer can progress while MCP transport is built.

#8090 W5 longitudinal selector is downstream and should not block the connector.

Source-freshness recovery is operationally important but does not need to block a clearly labeled historical-source canary.

## 30. Wave plan and exact acceptance

### W0 — current-state/custody reconciliation

Fable:
- re-pin current protected procedure;
- re-pin Macro;
- read this packet;
- inspect #7354/#7522/#7461/#8090 current heads, comments, reviews and path collisions;
- verify no newly merged Research MCP/read service supersedes this plan.

Exit:
- one current collision/ownership map;
- DO_NOT_REDO list preserved;
- exact first child carrier selected.

### W1 — private-store isolation

Implement P0 R2 fail-closed.

Exit:
- tests;
- real workflow private-store proof;
- API private-store proof;
- no shared fallback.

### W2 — live Vault census and integrity repair

Run existing read-only census.

Diagnose excerpt/body collapse.

Exit:
- exact set-difference receipt;
- source/body completeness understood;
- repair merged or intentional degradation documented.

### W3 — source freshness recovery

Diagnose upstream MarketDesk/source intake.

Exit:
- producer restored or typed outage durable;
- no dishonest currentness.

### W4 — RIO correctness

Finish #7461.

Exit:
- semantic review + merge.

### W5 — full-document derivative

Backfill canonical text.

Exit:
- all eligible PDFs have current derivative or typed failure;
- long-tail source proof.

### W6 — deterministic research segments

Implement receipts.

Exit:
- replay suite green;
- page/tail cases green.

### W7 — retrieval benchmark + physical index

Measure and choose physical architecture.

Exit:
- fixed benchmark;
- full-tail retrieval;
- documented latency/size;
- no unjustified vector dependency.

### W8 — Research Read Service

Implement domain interface.

Exit:
- status/search/fetch/evidence contract tests;
- rights and bounded-output tests;
- source correction tests.

### W9 — institutional RIO producer recovery

Finish #7354 after correctness/security gates.

Exit:
- live real report;
- RIO persisted/read back;
- rerun no extra model call;
- correction path proven.

### W10 — Brain RIO consumer

Finish #7522.

Exit:
- generic report uses rights-safe RIO when current;
- exact evidence remains literal;
- negative states typed.

### W11 — Research MCP source

Build Mastermind adapter.

Exit:
- exact four-tool discovery;
- closed schemas;
- auth policy tests;
- zero generic storage/file/shell tools.

### W12 — Research app deployment/canary

Deploy behind current private MCP pattern.

Exit:
- authorized ChatGPT read;
- denied-path proof;
- no secret/locator leaks.

### W13 — Deep Research canary

Exit:
- mixed internal/public research task completed;
- exact institutional citations/evidence;
- source-family distinction;
- no manual PDFs.

### W14 — production acceptance

Independent adversarial review across:
- security;
- rights;
- retrieval quality;
- correction;
- staleness;
- cost;
- observability;
- rollback.

Exit only when DONE_WHEN below is proven.

## 31. Rollback strategy

Every new derivative is additive.

Rollback should normally mean:
- disable Research app publication/connection;
- stop MCP service/tunnel;
- revert consumer wiring;
- leave canonical source and derivative history intact.

Do not “rollback” by deleting licensed source history or overwriting RIO/currentness receipts.

If an external-response leak is found:
- disable external Research app first;
- preserve evidence;
- identify exact projection/tool/version;
- repair canonical projection;
- re-canary.

## 32. Security/adversarial test matrix

At minimum:

Auth:
- missing token;
- expired token;
- wrong issuer;
- wrong audience;
- wrong resource;
- missing scope;
- correct auth but no research entitlement.

Input:
- unknown fields;
- oversized query;
- path traversal-shaped report ID;
- SQL-shaped query;
- prompt-injection strings inside source document;
- model attempts to pass bucket/key/credential/root.

Output:
- R2 key must not appear;
- endpoint must not appear unless explicitly approved public metadata;
- filesystem path must not appear;
- credentials/tokens must not appear;
- private RIO fields cannot hitchhike through extra dictionary keys;
- error exceptions sanitized.

Source:
- corrected PDF;
- stale derivative;
- missing PDF;
- missing full text;
- scanned PDF;
- unsupported extraction;
- stale RIO;
- malformed RIO;
- no evidence match.

Concurrency:
- source correction while read is in flight;
- authorization expiry around awaited read if current auth owner requires final revalidation;
- corpus refresh while search is in flight.

## 33. Performance targets

Freeze exact numerical SLOs after measurement, not before.

The design intent:
- metadata/status reads should be cheap;
- warm search should be interactive;
- evidence fetch should return bounded text, not megabytes;
- one cold corpus/index event should not happen for every tool call;
- Deep Research should be able to make many bounded reads without repeatedly fetching the whole corpus from R2.

If the current per-process corpus-download architecture stops meeting this after full-text expansion, change the physical deployment while preserving one logical Research Vault search owner.

## 34. Explicit non-goals

Not in this program:
- trading signal promotion;
- portfolio sizing;
- automatic trades;
- new qledger;
- new graph authority;
- new narrative detector;
- new sentiment brain;
- new Market Cognition store;
- new task/lifecycle system;
- new OAuth issuer;
- new token database;
- raw R2 plugin;
- generic filesystem access;
- generic SQL;
- broad customer launch before rights review;
- W5/W6 longitudinal cognition as a prerequisite to first Research MCP.

## 35. DONE_WHEN

The project is complete only when all are true.

### Source/privacy
- Research Vault private store cannot fall back to shared/public R2.
- Live catalog/PDF/corpus/receipt integrity is reconciled or explicitly typed.
- External Research tools cannot expose private bucket locators or credentials.

### Retrieval
- a fact beyond the old 60k prefix is discoverable.
- the exact literal evidence can be replayed against the correct source revision.
- no-text/partial-tail states are honest.

### Correction
- source revision changes invalidate the affected full text, segments, evidence, RIO and optional embeddings.
- history is preserved.

### Derived intelligence
- current RIO can enrich a report when available.
- missing/stale/invalid RIO never substitutes for literal evidence.

### ChatGPT
- a real authorized ChatGPT session connects to the dedicated Research app.
- it discovers the reviewed read-only tools.
- it searches, fetches, and finds evidence.
- an unauthorized/under-entitled caller receives no private source content.

### Deep Research
- a real run combines Research Vault and public sources without manual PDF upload.
- internal licensed sources and public sources remain distinguishable.
- citations/evidence are source-bound.

### Freshness
- current source producer health is surfaced honestly.
- no catalog-generated timestamp is presented as proof of current research inflow.

### Rights
- model-facing output is within approved rights/entitlement policy.
- derived artifacts do not silently widen redistribution rights.

### Operational proof
- source merge;
- service deployment;
- app publication;
- app installation/connection;
- OAuth;
- tool discovery;
- authorized call;
- denied call;
- Deep Research call;
- acceptance

are all proven separately.

## 36. Stop/escalation conditions for Fable

Return to Chairman/Sol only for a genuine reserved decision such as:
- new paid data/subscription;
- legal/rights policy change;
- a need to expose institutional source content beyond current authorized product rights;
- a proposed new canonical owner/store/control plane;
- destructive source migration;
- irreconcilable conflict with another active source owner;
- a new external public endpoint/authority materially broader than this read-only app.

Do not return for routine:
- implementation detail;
- tests;
- refactor;
- benchmark;
- current-main rebase/reconciliation;
- choosing bounded worker lanes;
- fixing a clearly owned bug.

## 37. Exact first execution sequence

Fable should begin:

1. Re-pin current protected Mastermind procedure and Macro main.
2. Read README, EVIDENCE_LEDGER, MASTER_PLAN, FABLE_CEO_HANDOFF.
3. Reconcile open carrier/path state for #7354/#7522/#7461/#8090.
4. Inspect r2_store and real deployment variables without exposing secret values.
5. Commission one bounded private-store fail-closed implementation.
6. In parallel, run the existing read-only Research Vault census through workflow dispatch if current authority/tooling permits.
7. Diagnose excerpt collapse from the census/body/text-layer evidence.
8. Diagnose source producer staleness as a separate lane.
9. Freeze the canonical full-text/read-service contract.
10. Continue through the next safe dependency rather than returning merely because one lane is waiting.

The first useful production capability is not “a new MCP exists.”

It is:

**an authorized frontier model can retrieve exact institutional evidence from the existing Mastermind Research Vault safely, efficiently, completely enough to cover long reports, and with provenance/rights/freshness truth preserved.**
