# Current-state census — Research Vault AI Intelligence Fabric

**Census date:** 2026-10-04  
**Macro reference:** `ce53dddb28a0718a4ab656a5306ef7293b6c779c` plus bounded compatibility check from the immediately prior research-path pin.  
**Protected Mastermind procedure reference:** `28be2ce2d481fd542ec869344e178e5cec4d7d75`.

This document separates **observed source facts**, **historical production evidence**, and **proposed changes**. It is intentionally not a design wishlist.

---

# 1. Capability ledger

| Capability | Current state | Evidence / consequence |
|---|---|---|
| Private institutional PDF/catalog product | `PROVEN_LIVE` historically, currently source-stale | Existing Research Vault UI/API/R2 ingest; current hourly publication works but source intake has stopped |
| Catalog publication | `PROVEN_LIVE` | Current catalog 2,778 rows; hourly republish succeeds |
| Canonical PDFs | `PROVEN_LIVE / CURRENT COUNT UNRECONCILED` | Historical census had catalog=PDF=receipt; current live census not yet rerun |
| Search corpus | `BROKEN / INCOMPLETE` | historical 918-row gap; current excerpt derivation sees only 351 useful rows vs 1,497 committed excerpts |
| Full-document search | `NOT_BUILT` | corpus caps body at 60k chars |
| Query-centered exact evidence | `PARTIAL` | deterministic 3x900-char passage selector exists, but only over stored prefix |
| Catalog metadata facets | `PARTIAL / SEVERELY SPARSE` | 0 ticker rows; 10 desk; 10 tags |
| Full Research Intelligence schema/store | `BUILT_NOT_PROVEN` for broad Vault population | RIO schema/store/projection landed; producer/consumer continuations are stale open PRs |
| Deterministic deep-read head | `BUILT_NOT_PROVEN / UNMERGED` | unique useful code exists on stale PR #7354 |
| RIO structural claim-index safety | `BROKEN ON MAIN / FIX EXISTS UNMERGED` | #7461 prevents malformed claim filtering from shifting support indices |
| Brain rights-safe RIO consumer | `BUILT_NOT_PROVEN / UNMERGED` | #7522 |
| Longitudinal predecessor selector | `BUILT_NOT_PROVEN / UNMERGED` | #8090; current metadata makes most rows ineligible |
| Generic authenticated Research MCP | `NOT_BUILT` | protected repo has reusable MCP/auth infrastructure, not research domain adapter |
| ChatGPT private Research Vault connection | `NOT_BUILT` | no Research MCP/tunnel canary yet |
| Deep Research internal-vault use | `NOT_BUILT` | depends on Research MCP read path |
| Private R2 isolation | `BROKEN BY DESIGN` | Research-specific environment variables silently fall back to shared R2 plane |

---

# 2. Current Research Vault population

Current committed catalog:

```text
schema:        research_vault.catalog.v1
items:         2,778
latest source: 2026-09-24T09:28:05Z
oldest source: 2026-07-20T20:50:56Z
```

The catalog currently spans sell-side, buy-side and independent institutional/research sources. Raw institution labels include large coverage from Goldman Sachs, J.P. Morgan, UBS, Bank of America, Deutsche Bank, Morgan Stanley and others.

The raw facet also contains spelling/alias variants. That is not a reason to build a new institution identity service: `engine/research_vault/sidecar.py::canon_institution` already owns known Research Vault spelling normalization.

## Page-depth distribution

Measured over the 2,673 catalog rows with a numeric page count:

| Metric | Pages |
|---|---:|
| min | 1 |
| p50 | 9 |
| p75 | 14 |
| p90 | 24 |
| p95 | 31 |
| p99 | 67 |
| max | 279 |
| >25 pages | 233 |
| >50 pages | 48 |
| >100 pages | 12 |

This matters because the current FTS body cap is 60,000 characters. Tail retrieval is not an edge case: dozens of reports are long enough that materially important tables/arguments may occur far beyond the stored prefix.

---

# 3. Metadata coverage

Measured directly from the current catalog:

| Field | Filled | Coverage |
|---|---:|---:|
| summary_points | 2,751 / 2,778 | 99.0% |
| pages | 2,673 / 2,778 | 96.2% |
| language | 2,673 / 2,778 | 96.2% |
| desk | 10 / 2,778 | 0.4% |
| tags | 10 / 2,778 | 0.4% |
| tickers | 0 / 2,778 | 0.0% |
| top_pick=true | 56 | 2.0% |

The current hourly workflow independently prints the same core coverage numbers and warns that `tickers` is empty on all 2,778 items.

## Consequence

A new MCP that advertises high-quality `ticker`, `theme`, `desk` or `tag` filters on top of this catalog would be dishonest.

The project needs a **derived metadata/identity projection** with provenance, not merely more MCP parameters.

Source-declared metadata and derived metadata must remain distinct.

---

# 4. Ingestion and publication topology

Canonical Research Vault flow today:

```text
upstream producer
  -> private R2 research_inbox/<id>.pdf + <id>.json
  -> hourly research-ingest workflow
  -> pdftotext + measured PDF facts
  -> canonical private research_vault/<id>.pdf
  -> research_vault/corpus.sqlite
  -> research_vault/catalog.json
  -> processed receipt
  -> repo catalog/excerpt mirror
  -> API / web Research Vault / Brain
```

Important incumbent semantics:

- one bad document may fail soft;
- publication authority fails closed;
- canonical publication order is corpus -> catalog -> receipts -> repo mirror;
- catalog membership gates user-visible search/read;
- a published corpus row ahead of catalog is hidden from users;
- serving/catalog publication freshness uses the catalog publication clock;
- upstream source-content freshness is a separate health question.

Do not collapse those clocks in the new service.

---

# 5. Current source-producer outage

Latest observed scheduled Research Vault run:

```text
run:        37224411920
observed:   2026-10-04T18:37Z
ingested:   0
skipped:    2778
failed:     0
corpus_published:  true
catalog_published: true
catalog_state:     valid
```

The publication path itself succeeded.

The separate source-content guard then reported:

```text
status:              PRODUCER_STALE
latest_report_at:    2026-09-24T09:28:05Z
age_hours:           249.152
existing limit:      96.0h
source_deadline_at:  2026-09-28T09:28:05Z
```

The workflow therefore ended red for source freshness, correctly preserving its catalog salvage.

## Ruling

This is not evidence that the Research Vault publication engine is dead.

It is evidence that **the upstream content producer/input plane has stopped advancing**.

The repair owner must investigate producer -> inbox delivery. Do not make the source-freshness guard more permissive just to get a green workflow.

---

# 6. Search-corpus integrity — historical proof

The production acceptance census recorded in:

`research/RESEARCH_VAULT_WAVE4_CONTINUATION_HANDOFF_2026-08-19.md`

measured:

```text
CATALOG_IDS     1,412
VAULT_PDF_IDS   1,412
RECEIPTED_IDS   1,412
CORPUS_IDS        494

catalog - pdf       0
receipt - catalog   0
corpus - catalog    0
pdf - catalog       0
catalog - corpus  918
```

Thus **65% of the Vault was openable but not searchable** at that time.

The handoff identified the exact mechanism:

- `corpus_mod.upsert` occurs only on new unreceipted inbox ingestion;
- once a document is receipted, it no longer re-enters that path;
- title/sidecar/body repair passes update existing corpus rows but do not insert a missing row;
- a corpus reset can therefore orphan older receipted reports indefinitely;
- a bounded self-quiescing `_backfill_corpus_rows` repair was recommended but never implemented.

Current-main search confirms that repair function still does not exist.

This is an incumbent defect, not a new MCP problem.

---

# 7. Search-corpus integrity — current symptom

Current committed public excerpt snapshot contains:

**1,497 document excerpts.**

The latest hourly ingest derives excerpts from the current corpus body rows. On both the October 3 and October 4 observed runs, it generated only:

**351 excerpts.**

The existing protective guard correctly refused:

```text
excerpt snapshot collapsed 1497 -> 351
```

instead of overwriting a known-better committed snapshot.

This does **not** prove current `CORPUS_IDS == 351`; excerpt derivation can omit rows for text-layer/content reasons.

It **does** prove the body/search derivative plane is materially degraded and requires a current live id-set census before the AI interface is trusted.

---

# 8. FTS/search behavior today

`engine/research_vault/corpus.py` is a standalone SQLite/FTS5 corpus.

Current weighting:

```text
title        4
summary      3
institution  2
body         1
```

Supported filters currently include institution and date bounds.

Important bounds:

```text
BODY_MAX_CHARS           = 60,000
EVIDENCE_PASSAGE_LIMIT   = 3
EVIDENCE_WINDOW_CHARS    = 900
CORPUS_TTL               = 300 seconds
```

The API/Brain can fetch an individual stored body projection. Brain further clamps generic report exposure to 12,000 chars.

## Consequence

Existing evidence selection is useful and should be reused, but:

```text
query -> current FTS prefix -> passage
```

cannot satisfy institutional full-report discovery.

The full-tail corpus/segment layer is genuine new work.

---

# 9. Existing Brain Research Vault consumer

`engine/neuralweb/brain_market_intel.py` already owns model-facing Research Vault semantics.

Modes include:

- search;
- clusters;
- report.

The report path already contains:

- Pro gating assumptions;
- public excerpt fallback;
- stored-body access;
- hourly view-rate accounting;
- scan/unavailable/source-unverified disclosures;
- query-centered passage selection;
- explicit rights instructions;
- output field whitelists.

This is valuable precedent.

The new Research MCP must **converge with Brain onto a shared canonical Research Read service**, not copy this file into a new server and let behavior drift.

---

# 10. Research Intelligence estate

Current main contains:

```text
engine/research_intelligence/
  extractor.py
  projection.py
  schema.py
  store.py
  vault_adapter.py
```

The RIO schema is:

`mastermind.research_intelligence.v1`

It separates:

### source claims
Grounded by literal quote spans.

### analysis
Derived thesis, assumptions, forecasts, catalysts, falsifiers, counterarguments, implications, belief delta, consensus relation and uncertainties.

### authority
Literal:

`descriptive_research_only`

The store already provides:

- private versioned artifacts;
- immutable object identity;
- one latest pointer;
- strict compare-and-swap semantics;
- exact source-body re-grounding;
- prompt/model/provenance binding;
- typed conflict/correction/effect-unknown behavior;
- rights-safe derived projections.

Do not create another "AI analysis store."

---

# 11. Research Intelligence correctness defect on main

Current `engine/research_intelligence/schema.py` silently skips malformed or blank submitted claim rows before validating `support_claim_indices`.

That means:

```text
submitted claim[0] malformed
submitted claim[1] valid
analysis support_claim_indices: [1]
```

can be normalized into a shorter claims array before support interpretation and risk attaching synthesis to the wrong surviving claim.

PR #7461 changes this structural behavior to fail closed before grounding/remapping.

The fix remains unmerged and must be salvaged before broad RIO production.

---

# 12. Stale Research Intelligence carriers

## PR #7354 — deep-read deterministic institutional head

State:

```text
OPEN / DRAFT / DIVERGED
head: b8833c40cb4c9541cc4449e72f5c5f8be8308d1a
thousands of current-main commits behind
```

Much of its original W2 persistence implementation has since landed elsewhere.

Unique useful missing deltas include:

- `engine/research_intelligence/vault_head.py`
- `scripts/research_intelligence_vault_head.py`
- its focused tests.

Its good design:

- reuse canonical deterministic research triage;
- default head 20, max 50;
- fetch canonical private PDF;
- full `pdftotext` rather than 60k prefix;
- skip model if exact source/model/prompt artifact already current;
- persist through W2 CAS;
- stop dependent writes on `EFFECT_UNKNOWN`.

Salvage these ideas/code against current owners; do not merge the branch wholesale.

## PR #7461 — claim identity

```text
OPEN / DRAFT / DIVERGED
head: cb844c90d162077e5518061d9932af93a914cda9
```

Small, still-relevant correctness repair. Salvage early.

## PR #7522 — Brain rights-safe RIO consumption

```text
OPEN / DRAFT / DIVERGED
head: 59a677cc6e899c37eae12364a1cb7d29276238a9
```

Current main has no RIO integration in Brain.

The branch correctly preserves:

- generic report may receive rights-safe derived RIO context;
- specific evidence queries still resolve literal source passages;
- RIO may not fill an evidence absence.

Salvage only after the new text/hash contract freezes.

## PR #8090 — W5 predecessor selector

```text
OPEN / DIVERGED
head: eee2a086d0bdcbfc437bc07d3dbf00ab0855496c
```

Useful exact longitudinal identity:

```text
canonical institution
+ desk
+ historical security_id
+ strictly earlier timestamp
```

using Data OS `VendorAliasTable`.

But current Vault metadata has only 10 desks and zero declared tickers, so this selector will abstain on almost the entire estate.

It is a later consumer of metadata repair, not an MVP dependency.

---

# 13. Existing earnings/company evidence primitive

The user recollection that earnings already had "chunking" is directionally correct.

The reusable primitive is not a generic vector chunk DB.

It is:

```text
source document revision
 -> deterministic segment
 -> exact byte span
 -> text digest
 -> replayable evidence receipt
 -> bounded context packet
```

Relevant owners:

- `engine/company_intelligence/documents.py`
- `engine/company_intelligence/qa_exchange.py`
- `engine/earnings_transcript_intake.py`
- `engine/earnings_narrative/context_packets.py`

The research program should reuse the **receipt law**:

- document/revision binding;
- source text hash;
- segment index;
- start/end byte;
- exact text digest;
- typed replayability;
- bounded context projection.

Do not import earnings-specific semantics into the Vault.

---

# 14. Hash-domain ambiguity

This is a newly identified integration hazard.

Research Vault measured facts use `content_sha256` to mean the canonical **PDF byte hash**.

Research Intelligence `extractor._identity()` assigns `document.content_sha256` as:

```text
sha256(extracted body UTF-8)
```

and W2 verifies the same body-byte identity.

The stale #7354 deep-read code likewise calls the full extracted body hash `source_content_sha256`.

## Consequence

A future unified citation envelope cannot safely emit one ambiguous `content_sha256`.

The target contract must separate:

```text
source_pdf_sha256
extracted_text_sha256
extractor_version
segmenter_version
```

Existing RIO v1 legacy semantics must remain compatible until a separately versioned migration is admitted.

---

# 15. Private R2 isolation landmine

Agent OS discovery:

`DSC-RESEARCH-VAULT-FALLS-BACK-TO-SHARED-PUBLIC-BUCKET`

verified that current Research Vault construction has a **mixed isolation contract**:

```text
R2_RESEARCH_BUCKET         required explicitly by build_store()
R2_RESEARCH_ENDPOINT       or R2_ENDPOINT
R2_RESEARCH_ACCESS_KEY_ID  or R2_ACCESS_KEY_ID
R2_RESEARCH_SECRET...      or R2_SECRET...
```

So the historical discovery's broad "everything falls back to the public bucket" wording is stale in one important respect: current `build_store()` no longer constructs an R2 store without an explicit research bucket.

The remaining defect is still P0. Endpoint/credentials may inherit generic shared values, and the factory does not itself reject `R2_RESEARCH_BUCKET == R2_BUCKET` when both are configured. Therefore the code does not structurally prove that the effective Research Vault plane is private and distinct from the shared/public delivery plane.

The API deployment workflow currently supplies the dedicated `R2_RESEARCH_*` family, which mitigates the normal deployed path. It does **not** make unsafe fallback/alias semantics acceptable in the canonical factory.

F1 must establish provable private-plane isolation before a new external read surface is admitted. Whether same-account shared credentials are permissible is a security-owner decision; silent inheritance is not.

---

# 16. Existing exact identity owners

Do not infer "no tickers in catalog" as "we need a new ticker identity database."

Current owner:

`lib/dataos/identity.py::VendorAliasTable`

is the estate's exact time-scoped issuer/security/listing identity authority.

There is also an existing context-only free-text resolver:

`engine/entity_resolver.py`

It can emit high-precision US/CN ticker candidates with method/confidence.

Correct enrichment shape:

```text
source-declared entity
OR deterministic resolver candidate
 -> Data OS exact identity resolution
 -> typed RESOLVED / AMBIGUOUS / UNRESOLVED
 -> derived Research metadata projection
```

Never silently write a guessed ticker into the source sidecar field.

---

# 17. Existing MCP/auth substrate

Protected Mastermind already contains reusable patterns in:

- `integrations/workbench_read_mcp/`
- `integrations/business_mcp_auth/`
- `integrations/executive_mcp/`
- `integrations/mastermind_company_mcp/`

The existing read MCP pattern includes:

- OAuth token verification;
- resource/audience/scope validation;
- bounded closed JSON schemas;
- read-only/destructive/idempotent annotations;
- DNS-rebinding/host controls;
- sanitized errors;
- request-local caller context;
- late/final authorization revalidation;
- no model-selected root/grant.

The Research MCP is a **domain adapter** over this substrate.

---

# 18. Current OpenAI product fit

Verified against current official docs on 2026-10-04:

- Pro developer mode supports custom MCP read/fetch connections.
- Deep Research can consume custom apps for read/fetch actions.
- Agent mode does not use custom apps.
- ChatGPT cannot directly connect to a local-only MCP.
- Secure MCP Tunnel is supported for private developer-mode MCP connectivity.
- Public plugin submission is separate and requires stable public HTTPS Streamable HTTP.
- authenticated MCP servers should enforce OAuth 2.1 resource-server semantics.

This is enough to ship the first private read-only research vertical without waiting for a public plugin.

---

# 19. Unknowns Fable must measure, not assume

The current session did **not** have direct R2 object access. Therefore these remain explicitly unknown until Fable/owner runs the real census:

- current `VAULT_PDF_IDS` count;
- current `CORPUS_IDS` count;
- current `RECEIPTED_IDS` count;
- exact current mismatch sets;
- current corpus **body-health**: non-empty/empty body counts, body-size distribution, `text_layer` distribution, valid PDF hash coverage, source-vs-stored char consistency, page-boundary coverage and excerpt-derivable count;
- canonical `corpus.sqlite` byte size;
- total full extracted text bytes;
- compressed full-text footprint;
- count of PDFs with no/thin/unavailable text layer across the full estate;
- exact reason upstream input stopped after September 24;
- number of current RIO artifacts;
- current RIO coverage by report/institution/date;
- real private-store/tunnel/runtime installation state outside source.

No plan step may manufacture these numbers.

---

# 20. Census conclusion

The Research Vault is mature enough to reuse and incomplete enough that exposing it directly would be misleading.

The critical path is:

```text
privacy
 -> live corpus integrity
 -> source liveness
 -> unambiguous source/text identity
 -> full-tail evidence
 -> metadata identity
 -> RIO correctness
 -> one canonical read port
 -> thin MCP
 -> real ChatGPT / Deep Research proof
```

That ordering is the basis of the execution DAG.
