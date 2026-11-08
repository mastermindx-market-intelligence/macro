# Architecture freeze and masterplan — Research Vault AI Intelligence Fabric

**Status:** architecture candidate frozen for Fable execution; current source must still be re-pinned at START.  
**Parent owner:** existing `qualitative-intelligence` program.  
**Authority class:** descriptive/context-only. Nothing here grants ranking, sizing, gating or trading authority.

---

# 1. North Star

Build one institutional research intelligence fabric that answers:

- What did the source actually say?
- Which exact document/revision did it come from?
- Where in the document is the supporting evidence?
- What does Mastermind infer from it?
- Which other sources agree or disagree?
- What changed from the prior institutional view?
- When could Mastermind have known it?
- Is the evidence current, partial, stale or unavailable?

The model-facing experience should feel like a high-quality internal institutional research API, not a folder of PDFs.

---

# 2. Target architecture

```text
UPSTREAM INSTITUTIONAL SOURCES
          |
          v
PRIVATE R2 SOURCE PLANE
  canonical PDFs + inbox/receipts
          |
          v
RESEARCH VAULT
  document identity
  catalog / entitlements
  full extracted text
  deterministic segment map
  FTS / retrieval
  exact evidence replay
          |
          +----------------------+
          |                      |
          v                      v
RESEARCH INTELLIGENCE        METADATA / IDENTITY
 private grounded RIO         source + derived facets
          |                      |
          +----------+-----------+
                     |
                     v
          CANONICAL RESEARCH READ PORT
          status / search / fetch / evidence
                     |
         +-----------+-----------+
         |                       |
         v                       v
   NEURAL WEB / BRAIN       RESEARCH MCP
                                 |
                         Secure MCP Tunnel
                           private canary
                                 |
                      +----------+----------+
                      |                     |
                      v                     v
                   ChatGPT             Deep Research
```

## Ownership

| Layer | Canonical owner | New work allowed |
|---|---|---|
| Original institutional PDF / source admission | Research Vault | repair/harden only |
| R2 physical storage | Research Vault storage owner | no model-facing S3 API |
| Catalog/public-safe metadata | Research Vault | additive compatible fields/projections only |
| Extracted text | Research Vault derivative | build full-text materialization |
| Segment/evidence receipt | Research Vault / shared evidence law | build deterministic address layer |
| Exact security identity | Data OS | consume only |
| Derived entity/theme metadata | Research Vault qualitative projection | build with provenance |
| Grounded model synthesis | Research Intelligence | finish/salvage current W1/W2/W5 |
| Brain research UX | Neural Web | consume shared read port |
| MCP auth/transport | protected Mastermind integration owners | thin research adapter |
| ChatGPT plugin/app | product transport/package | no data authority |

---

# 3. Canonical document and text identity

The most important new contract is explicit byte-domain identity.

## 3.1 Original source identity

For every canonical report revision:

```text
report_id
source_pdf_sha256
source_byte_length
published_at
ingested_at
canonical_pdf_key (server-side only)
```

`source_pdf_sha256` is SHA-256 of the original canonical PDF bytes.

It is never overloaded to mean extracted text.

## 3.2 Extracted-text identity

Create a deterministic full-text artifact bound to:

```text
schema: research_vault.extracted_text.v1
report_id
source_pdf_sha256
extractor_name
extractor_version
extracted_text_sha256
char_count
byte_count
page_count
page_boundaries
text_layer_state
created_at/computed_at
```

`extracted_text_sha256` is SHA-256 of the exact canonical UTF-8 representation used downstream.

The same source PDF + extractor/version + normalization contract must reproduce the same text bytes or fail qualification.

Do not silently change whitespace/page-separator normalization under the same extractor version.

## 3.3 Compatibility with RIO v1

Existing `mastermind.research_intelligence.v1` calls its extracted-body SHA `document.content_sha256`.

Do not reinterpret that field in place.

During v1 compatibility:

```text
RIO document.content_sha256 == extracted_text_sha256
```

The outer Research Read envelope additionally carries:

```text
source_pdf_sha256
extracted_text_sha256
```

If RIO schema is later versioned, rename the field explicitly rather than changing v1 meaning.

---

# 4. Deterministic full-document segmentation

Borrow the earnings/company evidence receipt law, not its domain vocabulary.

Proposed contract:

```text
schema: research_vault.segment.v1

report_id
source_pdf_sha256
extracted_text_sha256
extractor_version
segmenter_version
segment_index

page_start
page_end

start_byte
end_byte
segment_text_sha256

section_hint?          # derived, optional
replay_state
```

The segment text itself may be stored in the private derivative/index but does not need to ride every identity response.

## Required properties

- deterministic for identical source/text/version;
- exact UTF-8 byte replay;
- page aware when page boundaries are available;
- stable ordering;
- no LLM-generated text;
- bounded segment size;
- correction-safe;
- versioned segmentation policy;
- scan/no-text state explicit;
- source text remains the only evidence authority.

## Segment-size tuning

Do not freeze a token count from convention.

Benchmark representative short, medium, long, table-heavy and multi-column reports first.

The acceptance criterion is retrieval quality + context efficiency + stable evidence replay, not adherence to a framework default.

---

# 5. Full-text materialization strategy

Do not blindly inflate the current R2-downloaded monolithic `corpus.sqlite`.

First measure:

```text
current corpus.sqlite bytes
total canonical extracted text bytes
compressed full-text bytes
full FTS index bytes
report chars/pages p50/p90/p95/p99
cold process load latency
warm query latency
R2 transfer per refresh
incremental update cost
memory footprint
```

Then choose the simplest physical implementation that satisfies the logical contract.

## Allowed physical outcomes

### A. One full FTS SQLite remains cheap enough
Use it. Remove the prefix ceiling only after measured safety.

### B. Full FTS is too heavy for read-through R2 download
Run one persistent synchronized local FTS/search replica on the existing API/research host, with R2 still authoritative for source/derivative artifacts.

### C. Physical sharding is required
Shard under one Research Vault search service. Consumers never select a shard.

## Not allowed

- consumer-specific FTS copies;
- Brain-specific search index;
- MCP-specific vector store;
- plugin-owned cache as authority;
- semantic index that becomes source identity.

---

# 6. Corpus completeness repair

Before full-text expansion, restore one row for every catalog-admitted searchable text source that can lawfully be materialized.

Implement a bounded, resumable/self-quiescing repair roughly equivalent to the old Wave-5 proposal:

```text
missing = catalog_ids - corpus_ids

for bounded batch in missing:
    read canonical promoted PDF
    verify source identity
    extract using canonical extractor
    INSERT/UPSERT derivative
    record bounded result
publish corpus through incumbent publication law
report remaining
```

No receipt deletion.
No inbox replay.
No whole-vault destructive rebuild unless separately proved necessary.
No silent claim that the backlog is drained when the cap was reached.

---

# 7. Source-producer freshness

Preserve two health planes:

## Publication plane

Is Mastermind serving a coherent current publication generation?

Existing catalog `generated_at` semantics belong here.

## Source-content plane

Is new institutional research continuing to arrive?

Current existing guard uses newest admitted report and a 96-hour source-anchored ceiling.

The Research Read status envelope should expose both, e.g.:

```text
publication_state
catalog_generated_at
source_content_state
latest_source_published_at
source_age_hours
known_degradation[]
```

A fresh republish of stale source material must never be described as "research is current."

---

# 8. Derived metadata / identity projection

Current source sidecars do not supply useful ticker/desk/tag coverage.

Do not mutate source claims with guessed labels.

Build a derivative, e.g.:

```text
research_vault.metadata.v1

report_id
source_pdf_sha256
extracted_text_sha256

source_declared:
  institution
  desk
  tags
  tickers
  language

resolved_entities:
  observed_text
  candidate_symbol
  security_id
  issuer_id?
  method
  confidence?
  identity_state
  as_of_date

derived_topics:
  topic
  method
  version
  epistemic_layer

computed_at
```

### Identity rules

1. Source-declared ticker survives as source data.
2. Deterministic `engine/entity_resolver.py` may produce candidate observed symbols.
3. Exact identity maps through Data OS `VendorAliasTable` / incumbent issuer-security owner.
4. Ambiguous/unresolved candidates remain typed unresolved.
5. A model may add topic/synthesis labels only as a derived epistemic layer, never source metadata.
6. Historical resolution uses report observation date, not today's issuer mapping.

### First useful facets

Prioritize:

- institution;
- date;
- exact security/ticker identity where supported;
- source type/side;
- topic/theme family;
- language;
- text-layer/coverage state;
- RIO availability/currentness.

Desk can become useful when source/derivation supports it; do not fabricate desk names from institution.

---

# 9. Retrieval architecture

## 9.1 Default retrieval stack

Start with:

```text
metadata/facet narrowing
 + BM25 full text
 + title/summary weighting
 + deterministic entity/topic aliases
 + optional RIO-derived discovery hints
```

Then resolve literal source evidence from exact segments.

## 9.2 Hybrid/semantic retrieval

Do **not** introduce embeddings at P0 merely because research products commonly use them.

Create a fixed retrieval benchmark first.

If lexical + facets + entity aliases + RIO hints miss a material class of relevant reports, add embeddings as a **derived Research Vault index**.

Embedding identity must bind:

```text
report_id
source_pdf_sha256
extracted_text_sha256
segmenter_version
segment_index
embedding_model/version
```

Vector similarity may rank candidates.

It may never become evidence.

The final evidence response always resolves literal source spans/segments.

---

# 10. Evidence retrieval contract

Proposed model-visible evidence item:

```text
schema: research.evidence_passage.v1

report_id
title
institution
published_at

source_pdf_sha256
extracted_text_sha256
extractor_version
segmenter_version
segment_index

page_start
page_end
start_byte
end_byte
passage_text_sha256

text
coverage_state
replay_state
open_source_ref
```

The returned `text` is literal source text.

### Coverage must be explicit

Examples:

```text
FULL_TEXT
PREFIX_ONLY_LEGACY
NO_TEXT_LAYER
EXTRACTION_UNAVAILABLE
SEGMENT_INDEX_PENDING
PARTIAL_CORPUS
SOURCE_REVISION_CHANGED
```

Never return an empty array and force the model to infer whether nothing matched or the body was unavailable.

---

# 11. Research Intelligence integration

RIO enriches retrieval; it does not replace source evidence.

Correct flow:

```text
user question
 -> search candidates
 -> literal evidence passages
 -> current RIO if useful
 -> synthesis
```

For generic "summarize this report" intent, an entitled model may receive a rights-safe RIO projection plus bounded source context.

For "what does the report say about X?" intent, literal source evidence remains primary.

## RIO currentness

RIO is current only when its exact extracted-text identity matches the current canonical extracted text and its prompt/model/version requirements are satisfied.

A PDF correction must make prior text segments, RIO and embeddings detectably stale.

---

# 12. RIO salvage program

Order is important.

## RIO-1 — structural claim safety
Salvage #7461's fail-closed structural claim validation first.

## RIO-2 — full-PDF deep-read producer
Salvage only the unique current-worthy #7354 deep-read head/operator code onto current main.

Adapt it to the new explicit PDF/text hash names.

Do not re-land already-current W2 store code from the stale branch.

## RIO-3 — rights-safe Brain consumer
Salvage #7522 after the canonical Research Read port and text-hash contract freeze.

Prefer Brain consuming the shared read port rather than independently reconstructing store logic.

## RIO-4 — longitudinal predecessor
Salvage #8090 after metadata identity coverage is sufficient to make its abstention rate useful.

Do not weaken its exact identity rules simply to increase coverage.

---

# 13. Canonical Research Read port

This is the key integration seam.

It is a normal internal service/module contract, not necessarily a network service.

It owns the model-consumer semantics for both Brain and MCP.

Minimal operations:

## status

Returns bounded corpus/source/intelligence health.

## search

Inputs may include:

```text
query
institution?
security/ticker?
date_from?
date_to?
topic?
language?
limit
cursor?
```

The internal engine decides lexical/vector/hybrid mechanics.

## fetch

Fetch one report's bounded authorized representation.

Selectors may request:

- metadata;
- rights-safe RIO summary;
- bounded text sections;
- coverage/currentness.

Never whole document by default.

## find_evidence

Inputs:

```text
report_id
query
max_passages
```

Returns literal replayable passage objects.

### Caller context

The trusted caller context supplies principal/entitlement/visibility policy.

The model does not supply:

- user ID;
- plan/tier;
- OAuth scope;
- bucket;
- root;
- R2 key;
- credential;
- source visibility.

---

# 14. Research MCP

The MCP is a thin authenticated adapter around the Research Read port.

External tool surface:

```text
research_status
research_search
research_fetch
research_find_evidence
```

Do not expose internal implementation knobs such as `fts=true`, `vector_top_k`, shard names, R2 keys or corpus paths.

### Tool properties

All four:

```text
readOnlyHint: true
destructiveHint: false
idempotentHint: true
```

Use closed JSON schemas, bounded input/output bytes, explicit pagination, sanitized errors and the existing protected auth/resource-server primitives.

### Forbidden tools

Never expose:

```text
r2_list_objects
r2_get_object
s3_request
sql
run_shell
read_path
presign_object
set_bucket
set_endpoint
select_credential
```

---

# 15. Authentication and connectivity

Private first.

Reuse protected Mastermind OAuth/resource-server contracts rather than implementing auth in Macro from memory.

Expected boundary:

```text
ChatGPT
 -> OpenAI-hosted tunnel endpoint
 -> Secure MCP Tunnel outbound client
 -> private Research MCP
 -> authenticated Research Read port
 -> Research Vault
```

The private MCP must verify caller authentication/authorization on every request.

OAuth/linking metadata, resource audience and tool-level security schemes should follow the current protected Mastermind patterns and current OpenAI MCP authorization contract.

Public plugin distribution is a later, separately reviewed release because it changes exposure/deployment requirements.

---

# 16. Rights and visibility

Third-party institutional research has separate concerns:

```text
source possession
user entitlement
model processing
verbatim quote exposure
derived summary exposure
redistribution/publication
```

Do not collapse them.

Rule:

> A derivative may never widen the rights of its source.

Every Research Read result should be built from a visibility decision made by trusted server-side policy.

Possible result layers:

### public-safe
Catalog/title/institution/date/approved teaser where current product already permits it.

### entitled source
Bounded literal evidence/text for authorized research use.

### private derived
RIO and hashes/lineage under the approved projection.

### non-exportable
Internal state that may guide retrieval but must not be returned.

The MCP must not make "the model saw it" equivalent to "the model may reproduce it."

---

# 17. Correction and temporal law

For every derivative preserve:

```text
published_at   # when source made it knowable
ingested_at    # when Mastermind received it
computed_at    # when derivative was built
```

Source correction creates a new source/text identity.

Old derivatives remain historical evidence but lose `current` status.

Do not delete old RIO or segment history merely to make currentness easy.

---

# 18. Failure grammar

At minimum distinguish:

```text
AUTHENTICATION_REQUIRED
INSUFFICIENT_SCOPE
NOT_ENTITLED
REPORT_NOT_FOUND

PUBLICATION_STALE
SOURCE_PRODUCER_STALE
CORPUS_INCOMPLETE
CORPUS_UNAVAILABLE

FULL_TEXT_NOT_MATERIALIZED
TEXT_LAYER_NONE
EXTRACTION_UNAVAILABLE
SOURCE_REVISION_CHANGED

EVIDENCE_NOT_FOUND
EVIDENCE_COVERAGE_PARTIAL

RIO_MISSING
RIO_STALE
RIO_INVALID
RIO_UNAVAILABLE
```

Do not leak internal exception text, credentials, object keys or filesystem paths inside these errors.

---

# 19. Observability

Log bounded metadata sufficient to investigate quality and abuse:

```text
tool
pseudonymous caller digest
request class
query digest where lawful/useful
report ids where policy permits
source/text revision ids
coverage state
result count
latency
bytes returned
RIO state
source/publication health
typed error
```

Do not log:

- bearer/refresh tokens;
- R2 credentials;
- raw auth headers;
- whole licensed report bodies;
- unbounded tool output;
- arbitrary full model prompts containing institutional text.

---

# 20. Cost/context architecture

The target research interaction:

```text
deterministic/hybrid search
 -> 10–30 candidates

metadata + RIO + segment ranking
 -> 3–8 reports

literal evidence fetch
 -> tens of KB, not hundreds of pages

frontier synthesis
```

Frontier reasoning should spend tokens on reconciliation and thesis change, not on scanning every page of every PDF.

Expensive RIO generation should be cached/idempotent by exact source/text/prompt/model identity.

---

# 21. Later longitudinal capability

When metadata identity coverage and #8090 salvage are ready:

```text
institution
+ desk
+ historical security_id
 -> prior eligible report
 -> current eligible report
 -> grounded claim/RIO delta
```

This can answer:

- Which house changed its thesis first?
- Which forecast was added/removed?
- Which assumption changed?
- Did target/earnings language move before price?
- Where did institutional disagreement widen?

This is a major downstream product, but it must not delay the first source-grounded ChatGPT vertical.

---

# 22. Visual evidence later

Many institutional reports carry important evidence in charts/tables.

Text-first MVP must not pretend to solve this.

Later add a page/region address layer that distinguishes:

```text
byte-replayed text evidence
vs
address-only visual evidence
```

OCR/model interpretation is derived evidence, not equivalent to literal text replay.

---

# 23. Final architecture test

Any proposed component should answer:

1. Which incumbent owner is this extending?
2. Which user capability does it unlock?
3. What is its source/revision identity?
4. Is it evidence, derived cognition or transport?
5. Can a correction invalidate it correctly?
6. Does it widen rights?
7. Does it create a second lifecycle/search/identity/auth/publication authority?
8. Can the real ChatGPT consumer use it?

If the answer to #7 is yes, redesign it.
