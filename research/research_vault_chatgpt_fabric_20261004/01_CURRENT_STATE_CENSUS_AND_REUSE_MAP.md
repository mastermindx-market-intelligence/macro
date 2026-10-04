# 01 — Current-state census and reuse map

**Observed protected Mastermind:** 03f7ca04cd5b0a3abf7166221dd77d403c7f95df  
**Observed Macro main before branch:** 1b4edfb438f7ff7edca5097f0c90243a49207d1e  
**Evidence date:** 2026-10-04 UTC / 2026-10-03 ET

This chapter exists so the receiving Fable session does not spend its opening hours re-censusing the entire estate. It is a source map and evidence snapshot, not permission to skip fresh reconciliation at effect boundaries.

## 1. Research Vault estate

Primary package:

- engine/research_vault/catalog.py
- engine/research_vault/corpus.py
- engine/research_vault/ingest.py
- engine/research_vault/r2_store.py
- engine/research_vault/sidecar.py
- engine/research_vault/probe.py
- engine/research_vault/excerpt.py
- engine/research_vault/download_quota.py
- engine/research_vault/view_ratelimit.py
- engine/research_vault/watermark.py

Product/API:

- app/research.py

Operations:

- scripts/ingest_research.py
- scripts/research_vault_census.py
- scripts/check_research_vault_source_freshness.py
- .github/workflows/research-ingest.yml
- .github/workflows/vps-live-heartbeat.yml

Historical architecture owner:

- research/RESEARCH_VAULT_MASTERPLAN.md

## 2. Current catalog census

Current committed catalog:

- schema: research_vault.catalog.v1
- generated_at: 2026-10-03T22:30:21.232044+00:00
- declared count: 2,778
- actual item count: 2,778
- newest admitted source: 2026-09-24T09:28:05Z
- oldest admitted source: 2026-07-20T20:50:56Z

### Field coverage

| Field | Filled | Total | Coverage |
|---|---:|---:|---:|
| summary_points | 2,751 | 2,778 | 99.0% |
| pages | 2,673 | 2,778 | 96.2% |
| desk | 10 | 2,778 | 0.4% |
| tags | 10 | 2,778 | 0.4% |
| tickers | 0 | 2,778 | 0.0% |
| top_pick=true | 56 | 2,778 | 2.0% |

This is a load-bearing finding. The sidecar schema contains desk/tags/tickers, but the production estate effectively does not.

Consequences:

- Do not expose an MCP ticker filter and imply it searches an authoritative ticker field.
- Do not use desk/tags/tickers as primary retrieval features until a derivative enrichment owner earns coverage.
- Do not let a model silently infer ticker membership and persist it as source fact.
- Search can still find ticker strings lexically in title/summary/body, but that is not equivalent to a source-owned ticker facet.

### Page-depth distribution

Among the 2,673 reports with measured page counts:

| Metric | Pages |
|---|---:|
| minimum | 1 |
| p50 | 9 |
| p75 | 14 |
| p90 | 24 |
| p95 | 31 |
| p99 | 67 |
| maximum | 279 |

Long tail:

- >25 pages: 233 reports
- >50 pages: 48
- >100 pages: 12

Therefore the 60,000-character body cap is economically material, even if many reports are short enough to fit.

### Institution concentration

Largest current institution labels:

- Goldman Sachs: 1,088
- S&T: 307
- J.P. Morgan: 241
- UBS: 222
- Other: 139
- Bank of America: 99
- Deutsche Bank: 99
- Morgan Stanley: 73
- Societe Generale: 34
- TS Lombard: 30
- Citi: 27
- Rabobank: 25
- ING: 24
- Mizuho: 22
- MUFG: 17

This concentration matters for retrieval evaluation: an unstratified random benchmark could look good while failing smaller institutions or long reports.

## 3. Ingestion and publication contract

Current ingest is stronger than the original “R2 PDFs” mental model.

Per new PDF:

1. private inbox PDF + sidecar read;
2. sidecar normalization/fallback;
3. pdftotext -layout extraction;
4. measured facts from bytes;
5. title repair;
6. canonical PDF promotion;
7. corpus/catalog upsert;
8. processed receipt.

Important current law:

- a failed canonical PDF promotion fails the item;
- publication order is corpus -> catalog -> receipts;
- catalog is the visibility commit;
- receipted rows are not simply re-ingested;
- repair passes separately heal title, late summary metadata and prior body-extraction failures.

The hourly workflow has a pdftotext preflight because a past runner move created 127 bodyless reports before that dependency was guarded.

Do not replace this pipeline for the MCP build.

## 4. Live source-freshness failure

Completed research-ingest run:

- run ID: 37158653683
- head at run start: e98092e6fa2727666b04b5830ccb4a5be524fa76
- created: 2026-10-03T22:30:06Z
- completed: 2026-10-03T22:41:30Z
- conclusion: FAILURE

The ingest stage itself reported:

- ingested=0
- skipped=2778
- failed=0
- summaries_recovered=0
- bodies_reextracted=0
- corpus_published=True
- catalog_published=True

The source-freshness guard reported:

- status=PRODUCER_STALE
- latest_report_at=2026-09-24T09:28:05Z
- age_hours=229.222
- limit_hours=96.0
- source_deadline_at=2026-09-28T09:28:05Z
- count=2778
- invalid_published_at=0
- served_stale=false

No stale-only outage acknowledgement softened the result.

Interpretation:

- the hourly publication mechanism can run;
- it is not admitting new research;
- the system correctly distinguishes that from a fresh source feed.

P0 must identify whether the upstream MarketDesk/producer stopped, the R2 inbox is empty, credentials/source collection failed, or another upstream boundary is responsible. Do not broaden the downstream plan to compensate for an upstream outage.

## 5. Corpus restore / excerpt integrity anomaly

The same run emitted:

> excerpt snapshot collapsed 1497 -> 351 (floor 50%) — refusing to write. The committed snapshot is kept; investigate the corpus restore before re-running.

Current committed data/research_vault/excerpts.json contains 1,497 report entries.

The new snapshot derived only 351 non-empty report excerpts from the corpus available in that run.

engine/research_vault/excerpt.py deliberately treats this as a corruption/degradation signal. Its comments record a prior incident where a partial corpus overwrote a much larger snapshot before the collapse floor existed.

Important epistemic boundary:

- this does **not** prove the corpus contains exactly 351 rows;
- scanned/no-text documents can fail excerpt derivation;
- the actual corpus.sqlite row/id/body distribution must be measured.

Required P0 read-only proof:

- catalog ID count/set;
- canonical PDF ID count/set;
- corpus document ID count/set;
- receipt ID count/set;
- corpus text-layer distribution;
- corpus body-empty/body-nonempty count;
- excerpt-derivable count;
- corpus object byte size and local restored byte size/hash where possible;
- differences between all identity sets.

scripts/research_vault_census.py already owns much of this id-set work. Extend only if necessary; do not create a second standing census.

## 6. Current corpus/retrieval architecture

Canonical file:

- engine/research_vault/corpus.py

Important constants:

- BODY_MAX_CHARS = 60,000
- EVIDENCE_PASSAGE_LIMIT = 3
- EVIDENCE_WINDOW_CHARS = 900
- CORPUS_KEY = research_vault/corpus.sqlite
- CORPUS_TTL = 300 seconds

Current FTS:

- SQLite FTS5
- title / summary / institution / body
- BM25 weighting
- institution/date facets
- body prefix capped at 60k

Current process-local access pattern:

1. corpus.sqlite lives in R2;
2. API/Brain share one local cached copy per process;
3. a cold process downloads the whole file;
4. a stale local copy is served while one background refresh downloads a replacement.

This makes full-text physical architecture a decision gate. Removing the 60k cap might be the simplest correct solution, but it may also make cold downloads or recurring refreshes unnecessarily large.

Before implementation, measure:

- current corpus.sqlite bytes;
- total extracted full-text bytes;
- compressed full-text bytes;
- projected full FTS bytes;
- document text-size percentiles;
- cold download/open latency;
- warm query latency;
- query p95 over representative workloads;
- hourly/incremental rebuild/publish cost;
- host memory/disk impact.

Possible implementation outcomes:

- keep one full SQLite FTS if economics remain good;
- keep R2 canonical but maintain a persistent synchronized API-host replica;
- physically shard while keeping one logical retrieval service.

None of these outcomes is permission to create a second retrieval authority.

## 7. Brain research path

Current owner:

- engine/neuralweb/brain_market_intel.py

Current modes:

- search;
- clusters;
- report.

Search is deterministic and catalog-oriented.

Clusters deliberately use title terms rather than desk/tags/tickers because those fields have historically been dead. The comments document measured failures from naïve bag-of-words “street convergence” clustering.

Report mode:

- returns one attributed report;
- may read the R2-backed corpus;
- exposes body text only under a bounded cap;
- uses the current view-meter path;
- has rights-oriented instructions for the model;
- current body cap is 12,000 characters.

Evidence queries delegate to the Research Vault corpus owner.

Architectural implication:

The new MCP should not grow an independent research-search implementation. Converge Brain and MCP on a canonical read service once that service exists.

## 8. Public excerpt layer

Owner:

- engine/research_vault/excerpt.py
- data/research_vault/excerpts.json

This is a **public** first-pages SEO sample, not the private evidence corpus.

Current dials:

- max published excerpt characters: 4,200;
- normal page sample: first 2;
- sparse expansion: up to first 4.

Do not use the public excerpt snapshot as a substitute for entitled report evidence.

## 9. Research Intelligence estate

Package:

- engine/research_intelligence/schema.py
- engine/research_intelligence/extractor.py
- engine/research_intelligence/store.py
- engine/research_intelligence/projection.py
- engine/research_intelligence/vault_adapter.py

### Schema

mastermind.research_intelligence.v1

Source claims carry:

- statement;
- exact quote_span evidence;
- numbers;
- entities;
- horizon;
- explicit flag.

Derived analysis carries:

- thesis;
- assumptions;
- forecasts;
- catalysts;
- falsifiers;
- counterarguments;
- implications;
- belief_delta;
- consensus_relation;
- uncertainties.

Authority:

- descriptive_research_only

Correct architectural separation:

- source claim is evidence-bearing;
- model analysis points back to source claims;
- model analysis is not literal source evidence.

### Persistence

Current root:

- research_vault/intelligence/v1

Current constraints include:

- exact source body required;
- SOURCE_BODY_MAX_BYTES = 8 MiB;
- RIO max = 128 KiB;
- artifact max = 160 KiB;
- exact source SHA;
- exact prompt version/contract hash/prompt hash;
- provider/model/requested-model receipt;
- immutable artifact objects;
- mutable latest pointer through strict compare-and-swap;
- exact predecessor/correction behavior;
- EFFECT_UNKNOWN classification rather than blind replay.

Do not replace this with another “analysis chunks” store.

### Rights-safe projection

projection.py already:

- projects derived thesis summary;
- withholds literal private source-claim text;
- keeps claim/evidence hashes for lineage;
- preserves source document/content hash;
- labels epistemic layer;
- labels authority descriptive_research_only.

This is the correct boundary for general model-visible RIO context.

## 10. Current RIO correctness risk

Open #7461 documented a concrete validator failure mode:

- malformed/blank claim rows can be skipped during normalization;
- support_claim_indices are then interpreted against the compacted surviving claim array;
- a support index can therefore point at the wrong surviving claim.

At this current main census, schema.py still follows the skip/compact pattern.

Treat #7461 as a critical correctness carrier to adjudicate before broad RIO generation.

Do not claim this proves live customer corruption occurred. It proves a reproducible structural failure mode in the current validator path.

## 11. Existing held Research Intelligence carriers

| PR | Mission | Publication state | Critical path |
|---|---|---|---|
| #7461 | preserve claim identity during RIO validation | open draft, unmerged | yes, before broad RIO generation |
| #7354 | deterministic institutional top-N full-PDF deep read -> W1 -> W2 | open draft, unmerged | yes, producer path |
| #7522 | Brain reads current rights-safe W2 RIO | open draft, unmerged | yes, consumer path |
| #8090 | identity-safe longitudinal predecessor selector | open, non-draft, unmerged | no for MCP MVP; yes for later belief-change |

Do not assume mergeability=false means source is bad; read reviews, dependency stacks and current-base collisions.

Do not rewrite these branches merely to make them look current if their semantic source remains valid. Use normal current-base reconciliation and the repo's review/release law.

## 12. Evidence receipt primitive to reuse

Canonical precedent:

- engine/company_intelligence/documents.py
- engine/earnings_narrative/contracts.py

source_document.v1 provides document revision identity.

source_span.v1 provides:

- span_id;
- document_id;
- document_version;
- locator;
- receipt_state;
- text_sha256;
- rights_profile;
- exact receipt or an explicit unreplayable reason.

Two distinct states:

- byte_replayed — exact text can be replayed from held source bytes;
- address_only — exact page/table/slide address exists but byte-level text proof is not claimed.

text_span() delegates to the earnings receipt_for_span primitive, which binds:

- source body SHA;
- segment index;
- segment SHA and bytes;
- byte start/end;
- cited text SHA.

verify_span() replays the bytes and refuses drift.

Institutional research full-document segments should reuse this receipt discipline, either by generalizing the lower-level owner or projecting an equivalent Research Vault segment object through the same primitive. Do not create incompatible citation hashes.

## 13. Private R2 landmine

Current Research Vault R2 client still does:

- R2_RESEARCH_ENDPOINT or R2_ENDPOINT
- R2_RESEARCH_ACCESS_KEY_ID or R2_ACCESS_KEY_ID
- R2_RESEARCH_SECRET_ACCESS_KEY or R2_SECRET_ACCESS_KEY

The verified discovery:

- agentos/discoveries/DSC-RESEARCH-VAULT-FALLS-BACK-TO-SHARED-PUBLIC-BUCKET.md

states that a missing research-specific configuration can bind private Research Vault operations to the shared delivery plane.

The handoff found no open PR directly fixing the Research Vault owner.

Design precedent only:

- PR #6625, Radar private evidence spool

Useful pattern from that carrier:

- require all dedicated private config;
- fail closed if absent/partial;
- structurally prevent shared/public evidence writes;
- distinguish explicit authenticated legacy reads from fallback writes;
- test delivery-plane classification.

Research Vault should implement the equivalent through its own owner.

## 14. Mastermind MCP/auth reuse map

Protected Mastermind already has production-grade source patterns for:

- OAuth ResourcePolicy;
- JWT/JWKS verification;
- protected-resource metadata;
- MCP token adapters;
- exact input/output schemas;
- bounded payloads;
- read-only annotations;
- transport security / host allowlists;
- auth audit;
- final authorization revalidation;
- loopback HTTP services;
- stdio Secure MCP Tunnel services;
- separate app publication/enrollment proof.

Primary references:

- integrations/business_mcp_auth/
- integrations/workbench_read_mcp/app.py
- integrations/workbench_read_mcp/service.py
- docs/runbooks/workbench-read-r0-production-canary.md
- docs/runbooks/business-sol-installation-enrollment.md
- docs/EXECUTIVE_MCP.md
- docs/WORKBENCH_ACTION_MCP.md

No new auth stack is justified.

## 15. Current external platform facts

Rechecked against official OpenAI documentation during this authoring pass:

- Pro developer mode can connect MCPs with read/fetch permissions.
- Deep Research can use custom apps for read/fetch.
- Agent mode does not use custom apps.
- Local/private MCP needs the supported private-network path.
- Authenticated MCP uses the MCP OAuth 2.1/resource-server model.
- OAuth metadata/resource propagation/PKCE/tool-level security and WWW-Authenticate behavior are part of the current contract.
- Server-side authorization is mandatory; model instructions are not an authorization boundary.

Revalidate at deployment. Platform facts are current dependencies, not permanent Mastermind law.

## 16. What already exists vs what is genuinely missing

### Already exists — consume it

- private Vault document admission;
- PDF promotion;
- catalog;
- prefix FTS;
- public excerpts;
- report view/download entitlement logic;
- source freshness guard;
- Vault id-set census;
- bounded evidence selector;
- Brain research tool;
- grounded RIO schema;
- RIO private persistence;
- RIO rights-safe projection;
- exact span receipt primitive;
- MCP/OAuth/auth libraries;
- app/tunnel/remote-MCP precedents.

### Genuine missing capability

- proven healthy current corpus/id-set state;
- structural Research Vault private-R2 refusal;
- restored source producer freshness;
- full-document materialized text/retrieval beyond 60k;
- stable page-aware replayable research segment map;
- metadata enrichment for tickers/themes/desks if product requires facets;
- resolved RIO claim-identity correctness;
- accepted/live institutional RIO producer;
- accepted/live Brain RIO consumer;
- one canonical read service shared by Brain/MCP;
- bounded Research MCP adapter;
- real ChatGPT/Deep Research canary;
- retrieval evaluation and rollout gate.

## 17. DO_NOT_REDO unless evidence changes

- Do not rebuild Research Vault ingestion.
- Do not replace SQLite/FTS before measuring its full-tail economics.
- Do not create a second RIO persistence format.
- Do not create a second source-span hasher.
- Do not create a second OAuth/JWT stack.
- Do not copy Brain search code into the MCP.
- Do not mass-run frontier RIO analysis across 2,778 reports before currentness/cost/correctness gates.
- Do not recreate #7354/#7522/#7461/#8090 from memory; inspect their exact carriers.
- Do not treat the public excerpt store as the private corpus.
- Do not remove source-freshness failure because it is noisy.

## 18. Open questions that require measured answers

These are legitimate research/engineering questions for the program:

1. What exactly caused the 1,497 -> 351 excerpt derivation collapse?
2. What are current corpus.sqlite row count, body coverage, text-layer distribution and byte size in the live store?
3. How large would full-document text and full FTS actually be?
4. Is one full SQLite FTS still operationally cheap enough?
5. Which metadata enrichment can be deterministic versus model-derived, and what coverage/precision is attainable?
6. Which held RIO PRs can be accepted/rebased as-is versus need repair?
7. Which MCP deployment profile best fits the first authorized internal canary under current OpenAI/Mastermind platform state?
8. What literal third-party text limits and rights projections should the Research MCP reuse from existing Brain/Vault decisions for the target account/workspace?
9. What retrieval benchmark demonstrates that adding embeddings is necessary, if ever?
10. What current upstream producer owns the source-feed outage?

Everything else in the architecture should be treated as frozen unless these answers materially falsify it.
