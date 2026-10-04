# Initial Work Packets — Fable Wave 1

**Purpose:** Give the Fable CEO immediately dispatchable, bounded first-wave assignments after current-source/custody reconciliation.

These are authoring packets, not worker admission or source grants. Fable must bind each packet to the current eligible worker/carrier through the existing routing/admission owner.

## Packet A — Research Vault private-store isolation

### Role
Backend/security engineer.

### Mission
Make the canonical production Research Vault R2 store fail closed so private institutional research cannot silently use shared/public R2 credentials or bucket bindings.

### Why
This is the hard external-exposure blocker. A Research MCP must not widen access while the canonical private store can resolve through an ambiguous shared delivery plane.

### Primary source
- engine/research_vault/r2_store.py
- existing Research Vault store tests
- .github/workflows/research-ingest.yml only if configuration-contract tests or comments must be updated

### Existing evidence
- R2_RESEARCH_* currently falls back to R2_*.
- Agent OS discovery DSC:RESEARCH-VAULT-FALLS-BACK-TO-SHARED-PUBLIC-BUCKET records the risk.
- Merged #3321 is the historical origin of the fallback.
- Open #6625 is a precedent for fail-closed dedicated private evidence storage, not an owner of this path.

### Proposed change
- introduce explicit private-research configuration validation in the canonical Research Vault store owner;
- require complete research endpoint/key/secret/bucket for production R2;
- reject partial config;
- reject shared/public alias where the deployment can identify it;
- preserve deliberate local/test stores without ambient shared fallback;
- preserve secret redaction.

### Non-goals
- no new R2 client abstraction for the company;
- no new bucket;
- no MCP code;
- no auth change;
- no credential retrieval into PR comments/logs;
- no migration of source PDFs.

### Required tests
1. research-specific complete config accepted;
2. no research config refuses production R2;
3. partial research config refuses;
4. shared-only config cannot build Research production store;
5. shared/private alias refuses when detectable;
6. error strings contain no secrets;
7. existing test/local backend remains usable intentionally.

### Production/config preflight
Before enforcing the new rule, establish without exposing values that:
- research-ingest receives all dedicated Research variables;
- macro-api production Research read path receives all dedicated Research variables.

If either is missing, separate configuration repair from source semantics.

### Acceptance
- focused tests green;
- current-base compatibility;
- independent security review;
- one real research-ingest run uses the intended private plane;
- one real API/read-service read uses the intended private plane;
- no shared fallback.

### Stop/return
Return to Fable for:
- evidence that current production intentionally uses a shared but private bucket classification that requires an architecture ruling;
- unknown modifying effect on production configuration;
- source-custody conflict.

Otherwise own build/test/repair loop.

---

## Packet B — Live Research Vault ID-set census

### Role
Verifier / backend-data operator.

### Mission
Run the incumbent read-only Research Vault census on the live private store and produce an exact integrity report.

### Why
The planning census can see committed catalog state but not live R2 object-set truth. This is required before full-text backfill or external-access acceptance.

### Existing mechanism
Use:
- .github/workflows/research-ingest.yml
- workflow_dispatch input run_census=true
- scripts/research_vault_census.py

Do not create another census utility.

### Mutation boundary
The workflow itself performs its normal hourly-style ingest/publication behavior in addition to the read-only census. Treat workflow dispatch according to current source/effect law. If Fable wants a strictly no-publication observation, first determine whether the existing script can be run safely through an already-authorized host/read path without creating a new tool.

### Required output
- workflow/run identity;
- exact source head;
- census artifact identity;
- catalog count/set;
- promoted PDF count/set;
- corpus count/set;
- processed receipt count/set;
- catalog-PDF differences;
- catalog-corpus differences;
- receipt-catalog differences;
- any read/list errors;
- corpus.sqlite object bytes if the tool reports it.

### Non-goals
- no repair in the census operation;
- no delete;
- no reingest by guessing;
- no object copy;
- no new store.

### Acceptance
A durable artifact and a short classification of every non-empty difference.

### Stop/return
Return if the workflow effect is ambiguous or live R2 cannot be read through the incumbent path.

---

## Packet C — Research source freshness root cause

### Role
Backend/data reliability investigator.

### Mission
Determine why no new institutional reports have been admitted since 2026-09-24 while hourly Research Vault publication remains active.

### Why
Current typed state is PRODUCER_STALE. The app can be historically useful while stale, but no one may claim current institutional coverage until this is resolved.

### Evidence
Latest observed run:
- ingested=0
- skipped=2778
- corpus_published=true
- catalog_published=true
- newest report age ~239.7h
- limit 96h
- PRODUCER_STALE

### Investigation boundary
Trace the source producer to the Research Vault inbox.

Separate:
- acquisition;
- auth;
- schedule;
- parsing;
- producer DB/state;
- sidecar/PDF publish;
- R2 inbox;
- Research Vault admission.

### Required answer
One causal failure layer with direct evidence, or a bounded uncertainty list with the next discriminating probe.

### Forbidden fixes
- increasing freshness limit to make green;
- removing the guard;
- fabricating publication timestamps;
- reusing old reports with new timestamps.

### Acceptance
Either:
- new current report flows end to end; or
- a durable typed outage is accepted by the appropriate owner and the app surfaces it.

### Stop/return
New credentials/account/spend or external vendor human action.

---

## Packet D — Excerpt/corpus collapse diagnosis

### Role
Backend/data engineer or verifier.

### Mission
Explain and repair, through the canonical owner, why the current excerpt derivation produces 351 documents when the protected committed snapshot contains 1,497.

### Why
The safety floor is protecting users from a likely incomplete corpus/body state. Full-document work must not build on an unexplained degraded substrate.

### Source
- engine/research_vault/excerpt.py
- engine/research_vault/corpus.py
- engine/research_vault/ingest.py
- scripts/ingest_research.py
- data/research_vault/excerpts.json
- live census artifact from Packet B when available

### Diagnostic steps
1. compare current corpus IDs to catalog;
2. count non-empty bodies;
3. count text_layer full/thin/none/unavailable;
4. compare current body-bearing IDs to 1,497 committed excerpt IDs;
5. inspect representative lost IDs;
6. verify whether lost rows still have canonical PDFs;
7. determine whether the cause is corpus restore, extraction, publication, or excerpt derivation;
8. repair the owning layer;
9. re-run derivation without weakening the collapse floor.

### Non-goals
- do not lower 50% floor;
- do not delete the committed good snapshot;
- do not mass OCR scans as a shortcut;
- do not call a partial corpus “full.”

### Acceptance
Fresh derivation is non-collapsed or the remaining reduction is intentionally explained by exact source changes.

---

## Packet E — RIO claim identity release reconciliation

### Role
Research Intelligence owner/reviewer.

### Mission
Adjudicate and, if valid, finish PR #7461 rather than recreating its fix.

### Candidate
Planning head:
cb844c90d162077e5518061d9932af93a914cda9

### Semantic question
Should malformed/blank structural claim rows be rejected before positional support indices are normalized, while existing grounding/remapping remains unchanged for structurally valid claims?

### Required work
- re-pin current source;
- inspect current PR head/review state;
- verify path custody;
- re-run only affected/current-base evidence;
- independent semantic review;
- release through normal expected-head path.

### Non-goals
- no new RIO schema version unless truly required;
- no historical artifact rewrite without evidence;
- no W2 persistence redesign;
- no #7522 Brain changes.

### Acceptance
Malformed claim arrays cannot silently redirect support; valid existing RIOs preserve semantics.

---

## Packet F — Full-text footprint measurement

### Role
Backend/data engineer.

### Mission
Measure the full extracted-text estate before Fable chooses the physical full-tail search architecture.

### Inputs
- live canonical PDFs;
- current extraction primitive;
- current corpus.sqlite;
- page counts.

### Required metrics
- full extracted UTF-8 bytes across eligible reports;
- compressed text bytes;
- report text size percentiles;
- current corpus.sqlite bytes;
- estimated/actual full-body FTS bytes on a disposable benchmark;
- cold load time;
- warm query latency;
- rebuild/update cost;
- memory;
- representative long-tail query behavior.

### Constraints
- read-only/disposable benchmark;
- no production corpus replacement;
- no vector database;
- no model calls;
- no permanent new index owner.

### Acceptance
Decision-ready evidence for:
A. expanded SQLite FTS;
B. persistent local synced replica;
C. logical sharding behind one owner.

Return the smallest architecture that meets requirements.

---

# Orchestration notes

Packets A, B, and C are largely independent after current custody checks.

Packet D benefits strongly from B but can begin source/code analysis while B runs.

Packet E is independent of the source-freshness defect and should advance rather than wait.

Packet F can begin after private read access is safely available and should not block Packet A.

Fable should keep one principal integration task while children run:
- freeze the canonical Research Read Service contract and source/derived/rights boundaries;
- do not duplicate active child implementations.

Every child return must include:
- exact source/head;
- actual checks;
- what was not proven;
- current effect state;
- unresolved collision;
- next dependency.
