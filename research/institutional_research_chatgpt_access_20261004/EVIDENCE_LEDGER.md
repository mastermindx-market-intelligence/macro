# Evidence Ledger — Institutional Research Intelligence Access

**Evidence freeze date:** 2026-10-04  
**Protected Mastermind procedure pin:** 17b9fa1363db6071d338be3373a4fdb11fc0076d  
**Planning branch base:** bd118c69cc031b33d73b756f95eb5d3723a9dceb  
**Parent program:** qualitative-intelligence

This ledger records observed source and runtime facts used to construct the master plan. It is evidence, not execution authority.

## 1. Canonical ownership recovered

### Research Vault

Primary source:
- engine/research_vault/
- app/research.py
- scripts/ingest_research.py
- scripts/research_vault_census.py
- scripts/check_research_vault_source_freshness.py
- .github/workflows/research-ingest.yml
- research/RESEARCH_VAULT_MASTERPLAN.md

Research Vault already owns:
- institutional report identity;
- private source PDF storage;
- public-safe catalog;
- server-side search corpus;
- PDF/body extraction;
- source metadata probing;
- public excerpts;
- entitlements, report view, and downloads;
- R2 persistence and conditional-write substrate;
- report-level source evidence retrieval.

It remains the canonical source/retrieval owner for this project.

### Research Intelligence

Primary source:
- engine/research_intelligence/schema.py
- engine/research_intelligence/extractor.py
- engine/research_intelligence/store.py
- engine/research_intelligence/projection.py
- engine/research_intelligence/vault_adapter.py
- research/QUALITATIVE_RESEARCH_INTELLIGENCE_FREEZE_2026-09-12.md

It already owns:
- mastermind.research_intelligence.v1;
- source-bound grounded claims;
- thesis / assumptions / forecasts / catalysts / falsifiers / counterarguments / implications;
- exact source-content SHA binding;
- prompt/model receipts;
- versioned immutable RIO artifacts;
- exact-predecessor correction semantics;
- EFFECT_UNKNOWN handling;
- rights-safe derived projections;
- descriptive_research_only authority.

It is an enrichment inside qualitative-intelligence, not a second Vault.

### Brain

Primary source:
- engine/neuralweb/brain_market_intel.py

Brain already exposes:
- research search;
- street-cluster retrieval;
- bounded report retrieval;
- source-bound evidence queries.

Brain is a consumer, not the canonical source owner.

### Source-span precedent

Primary source:
- engine/company_intelligence/documents.py
- engine/company_intelligence/qa_exchange.py
- engine/earnings_transcript_intake.py
- engine/earnings_narrative/context_packets.py

The mature reusable primitive is not a generic embedding chunk. It is:

document revision
-> deterministic segment
-> exact source span
-> replayable receipt

Company Intelligence treats source_span.v1 as the fundamental evidence receipt. This is the preferred law for future Research Vault segment evidence.

## 2. Current Research Vault estate

Observed current catalog:
- schema: research_vault.catalog.v1
- count: 2,778
- latest admitted report: 2026-09-24T09:28:05Z

Coverage:
- summary_points: 2,751 / 2,778 = 99.0%
- pages: 2,673 / 2,778 = 96.2%
- desk: 10 / 2,778 = 0.4%
- tags: 10 / 2,778 = 0.4%
- tickers: 0 / 2,778 = 0%

Page distribution among rows with page count:
- n = 2,673
- minimum = 1
- p50 = 9
- p90 = 24
- p95 = 31
- p99 = 67
- maximum = 279
- over 25 pages = 233
- over 50 pages = 48
- over 100 pages = 12

Interpretation:
- the Vault is not a small short-note corpus;
- a meaningful long-report tail exists;
- the current 60,000-character body ceiling can materially truncate searchable tails;
- full-document retrieval is a real missing capability, not speculative future work.

## 3. Current corpus behavior

engine/research_vault/corpus.py currently defines:
- BODY_MAX_CHARS = 60,000
- EVIDENCE_PASSAGE_LIMIT = 3
- EVIDENCE_WINDOW_CHARS = 900
- CORPUS_TTL = 300 seconds

The FTS document includes title, summary, institution, and body with weighted lexical retrieval.

The corpus lives in private R2 as:
- research_vault/corpus.sqlite

The API/Brain path uses one process-local read-through copy. A cold process may download the corpus; a stale copy is refreshed asynchronously.

Material consequence:
- body search does not guarantee access beyond the stored 60k prefix;
- existing evidence selection is exact within the stored body, but its coverage can be partial;
- this is why the project needs a canonical full-document derivative and explicit coverage state rather than simply increasing the Brain context cap.

## 4. Current Brain exposure

Brain report mode currently uses a much smaller model-facing exposure ceiling:
- REPORT_BODY_MAX_CHARS = 12,000

That is intentional for rights/context control.

The project must preserve the difference between:
- internal searchable source coverage; and
- model-visible response size.

The correct answer is not to send full reports into model context. It is to search full source coverage and return bounded source evidence.

## 5. Latest live Research Vault workflow evidence

Latest observed scheduled run:
- GitHub Actions run: 37190468008
- workflow: research-ingest
- status: completed
- conclusion: failure
- run created: 2026-10-04T08:55:10Z
- run completed: 2026-10-04T09:07:27Z

The ingestion step itself succeeded.

Observed:
- ingested = 0
- skipped = 2,778
- failed = 0
- corpus_published = true
- catalog_published = true
- catalog_state = valid

Therefore the current red state is not accurately described as “Research Vault ingest is broken.”

It is a multi-plane degradation.

### 5.1 Source-content freshness plane

The same run reported:
- newest report: 2026-09-24T09:28:05Z
- age: approximately 239.7 hours
- source-anchored limit: 96.0 hours
- status: PRODUCER_STALE
- source deadline: 2026-09-28T09:28:05Z

The publisher is able to republish existing state, but the upstream source producer has admitted no newer reports.

Do not weaken or remove the freshness guard merely to make CI green.

### 5.2 Excerpt/corpus derivative plane

The same run reported:
- committed public excerpt count: 1,497
- newly derived excerpt count: 351
- collapse floor: 50%
- result: write refused; committed snapshot retained

The guard is working correctly.

The defect to diagnose is why only 351 current corpus rows yield public excerpts when 1,497 were previously derivable.

Potential hypotheses include, but are not limited to:
- corpus restore contains fewer usable bodies than the committed snapshot;
- extraction/content state regressed for a large subset;
- current corpus materialization has partial/old rows;
- another corpus-publication mismatch exists.

Do not assume the cause from the symptom. Run the existing live ID-set census and then inspect body/text-layer distribution.

## 6. Existing live ID-set census

scripts/research_vault_census.py compares:
- catalog IDs;
- promoted Vault PDF IDs;
- corpus IDs;
- processed receipt IDs.

The existing workflow supports a manual read-only census through:
- workflow_dispatch
- input run_census = true

The workflow uploads a census artifact.

This is the preferred first live R2 investigation because it uses the canonical deployment secrets and existing read-only census rather than requiring a new R2 ChatGPT connector merely to inspect state.

Required first live evidence:
- catalog count/set;
- PDF count/set;
- corpus count/set;
- receipt count/set;
- every non-empty set difference;
- corpus object size;
- relevant body/text-layer counts if available.

## 7. Private R2 boundary defect

Current engine/research_vault/r2_store.py still allows:
- R2_RESEARCH_ENDPOINT to fall back to R2_ENDPOINT;
- R2_RESEARCH_ACCESS_KEY_ID to fall back to R2_ACCESS_KEY_ID;
- R2_RESEARCH_SECRET_ACCESS_KEY to fall back to R2_SECRET_ACCESS_KEY.

Historical origin:
- merged PR #3321 added separate-account research credentials while deliberately preserving same-account fallback compatibility.

Current contrary evidence:
- merged PR #7902 records DSC:RESEARCH-VAULT-FALLS-BACK-TO-SHARED-PUBLIC-BUCKET;
- Agent OS discovery records that the store can silently bind to the shared publication plane when research-specific config is absent.

Security judgment for this project:
- this is a P0 hard gate before external Research MCP exposure;
- the canonical store must fail closed rather than rely on deployment convention;
- the external MCP must not grow its own bucket guard as a workaround.

Useful precedent:
- open PR #6625 implements a dedicated-store/shared-bucket-refusal shape for another private evidence plane. Reuse the structural idea, not its ownership or exact implementation.

## 8. Research Intelligence source state

### DO_NOT_REDO — merged

PR #7101 — Research Intelligence Object v1
- merged
- establishes the RIO contract and grounded analysis boundary.

PR #7230 — versioned Research Intelligence persistence
- merged
- canonical merge: 204541291571ad6012a535621437c608489f2526
- existing private strict store;
- immutable artifacts;
- exact-current predecessor corrections;
- effect-unknown handling.

PR #7079 — Brain source-bound report evidence
- merged
- canonical merge: 0d352926c4ec9c4e5c972bee524b732d3308c617
- literal source evidence path exists.

PR #8027 — rights-safe belief context
- merged
- merge: 563362aea7d9b532fcd834d44a82b456952c278c
- later cognition may reuse it.

### OPEN — reconcile rather than recreate

PR #7461 — preserve claim identity during RIO validation
- open / draft
- head: cb844c90d162077e5518061d9932af93a914cda9
- exact paths:
  - engine/research_intelligence/schema.py
  - tests/test_research_vault_strict_store.py
- reproduced defect: malformed/blank claim rows can cause positional support indices to shift onto a different surviving claim.
- exact-head test evidence was strong.
- still needs owner/release reconciliation.
- broad RIO backfill should not run before this semantic defect is adjudicated.

PR #7354 — institutional deep-read deterministic head
- open / draft
- head: b8833c40cb4c9541cc4449e72f5c5f8be8308d1a
- reads canonical private PDF;
- uses full pdftotext -layout, not the 60k corpus prefix;
- bounded top-N cognition head: default 20, hard max 50;
- exact-current RIO/model spend guard;
- stops batch on EFFECT_UNKNOWN;
- original W2 dependency is now merged.
- requires current-main resurrection/review/live proof rather than reimplementation.

PR #7522 — Brain consumes rights-safe RIO
- open / draft
- head: 59a677cc6e899c37eae12364a1cb7d29276238a9
- paths:
  - .github/ci/legacy-jobs.yml
  - engine/neuralweb/brain_market_intel.py
  - tests/test_brain_market_intel.py
  - tests/test_brain_research_evidence.py
- implements explicit available/missing/stale/invalid/unavailable RIO states;
- preserves literal evidence path as source truth;
- had strong source-level proof but remains unmerged.
- do not write a duplicate Brain/RIO consumer.

PR #8090 — W5 predecessor selector
- open
- head: eee2a086d0bdcbfc437bc07d3dbf00ab0855496c
- only:
  - engine/research_intelligence/longitudinal.py
  - tests/test_research_vault.py
- downstream longitudinal cognition;
- live corpus currently lacks sufficient desk/ticker metadata for broad use;
- not a blocker for the external Research Vault read interface.

Issue #7997 — Market Cognition
- remains open;
- explicitly converges Market Cognition into incumbent Qualitative Research Intelligence;
- forbids a parallel psychology/research brain;
- downstream W5/W6/W7/W8 work should remain separate from this connector critical path.

## 9. Metadata debt

The live catalog materially under-populates:
- desk;
- tags;
- tickers.

That limits:
- security-filtered retrieval;
- desk-level institutional history;
- longitudinal belief streams;
- some high-quality faceting.

However it does not block:
- report ID;
- institution;
- publication time;
- title;
- summary;
- full body retrieval;
- lexical source evidence;
- initial ChatGPT/Deep Research integration.

Do not make W5 metadata repair a serial dependency of the basic MCP.

The master plan should allow metadata repair to proceed as a parallel source-quality lane.

## 10. Mastermind MCP/Auth evidence

The protected Mastermind repository already owns reusable MCP/OAuth infrastructure:
- integrations/business_mcp_auth/
- integrations/executive_mcp/
- integrations/workbench_read_mcp/
- integrations/mastermind_company_mcp/

Useful design patterns:
- SDK-free contract/schema modules;
- one narrow SDK server module;
- closed JSON schemas;
- bounded request/response bytes;
- model arguments cannot select trusted binding identity;
- token/resource/scopes come from authenticated request context;
- sanitized failures;
- exact tool lists;
- read-only annotations;
- no new token database;
- no new retry queue;
- no model-selected root/bucket/credential.

Most important production precedent:
- research/EXECUTIVE_MCP_CHATGPT_BUSINESS_PRODUCTION_PROOF_2026-09-16.md
- state: PROVEN_LIVE for the exact Executive app path;
- a real ChatGPT Business conversation authenticated through the installed app;
- Secure MCP Tunnel was used;
- OAuth worked;
- exact tool discovery and calls were proven.

Boundary:
- the Research app must not borrow Executive authority/resource/scope;
- reuse the code/operational pattern with a separate read-only Research resource and scope.

## 11. Current OpenAI external-consumer contract

Official OpenAI documentation rechecked for this planning pass establishes the following product boundary:

- ChatGPT custom MCP apps use remote MCP.
- Private/local services can be reached through Secure MCP Tunnel.
- Pro developer mode can connect read/fetch MCP capability.
- Deep Research can use custom apps for read/fetch.
- OAuth 2.1/resource metadata/PKCE/resource binding are the current authenticated custom-MCP pattern.

The Research MCP generation should therefore be read-only.

Do not delay the first useful canary waiting for write support.

## 12. Rights boundary

The original Research Vault masterplan explicitly states that third-party distribution rights remain an operator/legal responsibility while the system enforces access and traceability.

For this project:

- source entitlement never widens merely because the consumer is a model;
- model-derived summaries do not automatically become unrestricted content;
- derived artifacts retain source identity/rights class;
- literal evidence returned through MCP must be bounded and entitled;
- model-visible outputs must never accidentally leak private RIO claim text through an expanded projection.

A legal/rights review is required before broader multi-user distribution beyond the existing authorized internal/subscriber boundary.

## 13. Material unknowns to resolve during execution

Unknowns are not failures and must not be replaced with assumptions:

1. Exact cause of the 1,497 -> 351 excerpt derivation collapse.
2. Exact catalog/PDF/corpus/receipt set differences in live R2 now.
3. Total untruncated extracted-text byte footprint for all 2,778 reports.
4. Full-FTS database size if the 60k limit is removed.
5. Whether persistent local full-text replica or sharding is necessary.
6. Current deployment ownership/location for the future Research Read Service.
7. Exact OAuth resource URI/scope naming for Research; must be harmonized with current Mastermind auth conventions.
8. Licensing/rights policy for model-facing literal excerpts outside existing product entitlements.
9. Number of current RIO artifacts actually persisted in private R2.
10. Whether #7354/#7522/#7461 current source can be revived intact or needs minimal reapplication against current main.

These are execution investigations. They do not justify another broad architecture restart.

## 14. Falsifiers for the proposed architecture

Re-open the architecture only if current evidence proves one of the following:

- Research Vault cannot be made a reliable source owner without replacing its storage/identity model.
- The full extracted corpus is too large for every reasonable single-owner search deployment and an incumbent canonical index owner already exists elsewhere.
- Existing Mastermind OAuth/MCP infrastructure cannot legally/technically isolate a separate Research read resource.
- Rights prohibit any model-facing use of the licensed source corpus even for the intended authorized internal/subscriber context.
- A current merged implementation already provides the exact canonical full-document Research Read Service and Research MCP, making this packet duplicative.

Absent one of those falsifiers, execution should reuse and extend the existing owners rather than start a new platform.
