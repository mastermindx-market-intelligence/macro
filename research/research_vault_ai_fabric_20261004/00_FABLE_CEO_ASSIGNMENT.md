# Fable CEO assignment — Research Vault AI Intelligence Fabric

**Role:** principal integrator / orchestration CEO  
**Assignment posture:** current Chairman-directed program handoff; source publication alone does not prove runtime pickup or START.  
**Parent program:** `qualitative-intelligence`  
**Repositories:** `mastermindx-market-intelligence/macro` + read/consume protected MCP/auth contracts from `mastermindx-market-intelligence/Mastermind`.  
**Source pins for intake:** Macro `ce53dddb28a0718a4ab656a5306ef7293b6c779c`; protected Mastermind `28be2ce2d481fd542ec869344e178e5cec4d7d75`.

## Mission

Lead this project end to end until Mastermind has a production-proven, private, read-only institutional research interface that authorized ChatGPT and Deep Research sessions can use directly.

You are the principal integrator. Maintain the architecture and adjudicate cross-system contradictions. Delegate bounded implementation, measurement, review and verification work to the least-scarce capable workers through current Capacity/Fabric owners when available. Do not personally turn into the default mechanical coding lane.

### WHY FABLE

This mission justifies Fable because its critical path crosses several existing authorities whose current state is inconsistent:

- a production Research Vault with known historical and current corpus-integrity defects;
- a verified private/public R2 boundary landmine;
- four materially useful but stale/diverged Research Intelligence carriers whose deltas must be selectively salvaged onto current main;
- two different content-hash meanings across adjacent evidence systems;
- incomplete source metadata that makes the obvious product API dishonest unless the identity/enrichment contract is designed correctly;
- a protected cross-repo MCP/OAuth owner that must be reused rather than forked;
- licensing/rights constraints where exact evidence, derived summaries and public-safe metadata have different visibility.

The hard job is not typing an MCP server. It is preserving one coherent source/evidence/rights/identity architecture while repairing and integrating these systems. Once a bounded contract is frozen, route implementation to cheaper qualified workers.

## Primary user journey

The Chairman or another authorized research user should be able to ask, from a normal ChatGPT session or Deep Research:

> Find all institutional reports from the last 90 days relevant to optical networking, 1.6T, Lumentum, Coherent and hyperscaler optical intensity. Reconstruct when the Street thesis changed, identify which institutions moved first, retrieve the exact source passages, distinguish source statements from Mastermind interpretation, and reconcile them with external evidence.

The system should return a small, source-bound evidence set — not dozens of PDF uploads and not free-floating LLM recollection.

## Machine outcome

A canonical Research Read service must support bounded:

```text
status
search
fetch
find_evidence
```

over the existing Vault/RIO estate. Brain and MCP become consumers of the same contract.

R2 remains storage. Research Vault remains source authority. Research Intelligence remains derived cognition. Data OS remains exact security identity. MCP remains transport.

## Intake law

Before any modification:

1. Re-pin current protected Mastermind `master`; load current compatible procedure from one exact commit.
2. Re-pin current Macro `main`.
3. Reconcile only material movement affecting this packet's named paths.
4. Inspect live custody/open PR state for #7354, #7461, #7522 and #8090.
5. Treat these PRs as **evidence/salvage sources**, not merge candidates. They are thousands of commits behind current main.
6. Preserve any live writer/effect found on overlapping paths. Do not duplicate a started modifier.
7. Keep one modifying carrier per logical source change until reconciled.

## First critical dependency

**Repair and prove the private Research Vault substrate before exposing any new external MCP read path.**

The first implementation wave is therefore:

```text
fail-closed private R2 binding
  + real read-only Vault id-set census
  + exact classification of corpus/excerpt loss
```

This unlocks a trustworthy retrieval baseline. Do not start by writing MCP schemas.

## Required start sequence

### A. Reconcile the private store boundary

Inspect `engine/research_vault/r2_store.py` and the verified Agent OS discovery:

`agentos/discoveries/DSC-RESEARCH-VAULT-FALLS-BACK-TO-SHARED-PUBLIC-BUCKET.md`

Implement a structural fail-closed private-store contract for production Research Vault use.

Production private research must require the dedicated research configuration and refuse silent fallback/alias to the shared public delivery plane. Preserve explicit local/test stores as explicit modes; do not break legitimate hermetic tests to achieve the safety property.

Prove the refusal path without exposing credentials.

### B. Run the real id-set census

Use the existing read-only `scripts/research_vault_census.py` against the actual private Vault.

Capture:

```text
CATALOG_IDS
VAULT_PDF_IDS
CORPUS_IDS
RECEIPTED_IDS
catalog - pdf
receipt - catalog
corpus - catalog
catalog - corpus
pdf - catalog
repo mirror vs canonical catalog
```

Do not mutate receipts to "repair" a mismatch before classifying it.

The August 19 production evidence showed 918 `catalog - corpus` rows. Current excerpt generation proves only 351 body-bearing rows can currently produce excerpts. Measure the current truth rather than extrapolating either count.

### C. Repair missing corpus rows through canonical promoted PDFs

If the historical defect is confirmed, implement the previously documented but still absent bounded self-quiescing backfill:

```text
catalog id missing from corpus
 -> canonical promoted Research Vault PDF
 -> exact extraction
 -> corpus INSERT / derivative materialization
 -> row stops being a candidate
```

Never delete/replay a receipt just to force re-ingestion.

Report remaining backlog explicitly.

### D. Separate source-producer health from publication health

The latest observed hourly run successfully republished the current catalog/corpus but admitted zero new reports. Source-content freshness was 249.2 hours against the existing 96-hour guard.

Diagnose the upstream intake independently:

```text
producer stopped?
inbox empty?
source authentication?
scheduler?
sidecar/PDF emitter?
intentional outage?
```

Do not relax the freshness guard to turn CI green. Product/API publication freshness and upstream research-source freshness are separate clocks and must remain separate.

## Delegation shape

Use Fable for principal judgment and integration. Suggested bounded lanes, subject to current Capacity eligibility:

| Lane | Work profile | Preferred class |
|---|---|---|
| RV-PRIVACY | private R2 binding + tests | bounded engineering; Codex/Terra or equivalent |
| RV-CENSUS | live id-set/size/freshness measurement | deterministic operator/data lane |
| RV-CORPUS | corpus restoration + full-text materialization | backend/data engineering |
| RV-METADATA | entity/ticker/theme derivation contract | data/research engineering |
| RIO-CORRECTNESS | salvage #7461 + exact-hash contract | strong bounded engineering + independent review |
| RIO-DEEPREAD | salvage unique #7354 head logic | backend/model integration |
| BRAIN-CONSUMER | salvage #7522 after retrieval contract freezes | bounded model-consumer integration |
| MCP-ADAPTER | Research Read port + authenticated four-tool server | backend/auth integration |
| RETRIEVAL-EVAL | fixed benchmark / tail recall / denial set | data scientist / adversarial reviewer |
| REALPATH | ChatGPT + Deep Research canaries | production verifier |

Do not pre-assign exact provider/model/account identities merely from this table. Current routing/Capacity owns placement.

### Reserved Fable duties

Do not delegate these decisions away:

- source-of-truth ownership changes;
- hash/revision identity contract;
- rights visibility boundary;
- whether full-text physical storage stays monolithic SQLite or requires a persistent/sharded implementation after measurement;
- whether semantic embeddings are actually needed after benchmark;
- cross-repo MCP/auth integration boundary;
- adjudicating stale PR salvage conflicts;
- final product acceptance.

## Required architecture invariants

1. **No second Research Vault.**
2. **No second exact security identity authority.**
3. **No second RIO store.**
4. **No new OAuth or entitlement database.**
5. **No generic R2/S3 tools for models.**
6. **No "vector DB" as evidence authority.**
7. **No model-defined bucket, endpoint, object key, credential, filesystem root or principal.**
8. **No RIO prose masquerading as literal source evidence.**
9. **No silent source correction overwrite.**
10. **No wholesale merge of stale #7354/#7461/#7522/#8090 branches.**
11. **No public Internet exposure merely because private ChatGPT canary needs connectivity; use the current supported private tunnel path first.**
12. **No claim of production completion from source merge, tunnel creation, app creation or installation alone.**

## Decision escalation to Chairman

Return only for a true reserved question, such as:

- legal/rights approval to expose a new class of licensed content;
- new spend/vendor/account authority;
- public plugin publication or new public ingress;
- material change to research distribution policy;
- destructive data migration with no reversible safe path;
- a strategy change that makes this packet's end state wrong.

Routine architecture-compatible repair/build/test/review does not require another Chairman approval.

## Principal stop condition

The project is complete only when the end-to-end acceptance in `04_ACCEPTANCE_SECURITY_AND_EVAL.md` is proven on a real authorized ChatGPT session and a real Deep Research run, with denied-path and stale/correction cases also proven.

If an individual lane blocks, preserve it and advance independent dependencies. A completed PR, checkpoint, test suite or MCP endpoint is not by itself a reason to stop the parent program.

## Durable return

Implementation/evidence -> GitHub.  
Organizational continuation -> existing Agent OS under `qualitative-intelligence`.  
Runtime lifecycle/admission -> Executive OS if/when used.  
Transport/hot dialogue -> the exact commissioned carrier if one is later established.

Do not create a separate project status database for this program.
