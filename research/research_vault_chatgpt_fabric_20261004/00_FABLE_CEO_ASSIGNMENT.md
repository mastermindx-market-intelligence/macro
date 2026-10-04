# 00 — Fable CEO assignment and operating brief

**State:** authoring-ready handoff / no pickup claimed  
**Primary role:** Fable principal orchestrator after deliberate assignment  
**Program:** Research Vault -> ChatGPT Intelligence Fabric  
**Current branch publication carrier:** docs/research-vault-chatgpt-fable-masterplan-20261004

## 1. Mission

Lead the existing institutional Research Vault through the smallest safe set of repairs and integrations required to make it a first-class, provenance-preserving source for authorized ChatGPT and Deep Research sessions.

The outcome is not “ChatGPT can access R2.” The outcome is:

> Mastermind can answer what institutional sources believed, what exact evidence supported the belief, what changed, who changed first, and when Mastermind could have known — using bounded retrieval and exact provenance rather than flooding frontier models with PDFs.

Carry the project end to end until the declared acceptance gates are proven, while preserving current source ownership and delegating bounded implementation/research work through the existing fabric.

## 2. WHY FABLE

**TASK_COMPLEXITY:** C3_FRONTIER_JUDGMENT  
**BUSINESS_IMPACT:** critical  
**EXECUTION_RISK:** critical for private research, rights and storage boundaries; otherwise bounded per wave  
**AMBIGUITY:** high at program start, expected to fall after P0  
**TOPOLOGY:** principal/orchestrator  
**FRONTIER_WITNESS:** the project crosses multiple canonical owners and currently contains conflicting/unsafe live state that requires continuous adjudication: private-R2 configuration can fall back to a shared/public plane; the latest ingest exposed a corpus-restore anomaly; source admission is stale; Research Intelligence correctness/producer/consumer work is split across held PRs; and the final MCP/auth deployment must reuse protected Mastermind owners without duplicating them.

This is a valid use of scarce Fable principal capacity. Routine code, measurements, tests, extraction and review should still be delegated to the least-scarce capable workers after each bounded package is frozen.

Fable is not commissioned because the project is merely “important” or “large.” It is commissioned because the initial architecture/custody/security state cannot yet be safely reduced to one routine implementation packet.

## 3. Primary user journey

An authorized researcher asks a question such as:

> Over the last 90 days, when did institutional research begin to imply that 1.6T optical networking and higher optical intensity would materially change earnings for the leading suppliers? Which institutions moved first, what literal evidence supports that chronology, and what public evidence corroborates it?

The finished journey is:

1. ChatGPT asks the Research app for source health.
2. The app reports current catalog/source/corpus state rather than silently answering from stale or partial data.
3. ChatGPT searches the canonical Research Vault.
4. Retrieval finds relevant reports using source-owned full-document search and metadata that actually exists.
5. ChatGPT asks for exact evidence from selected reports.
6. The evidence service returns bounded literal passages with document revision/content hash and replayable location.
7. If a current Research Intelligence Object exists, a rights-safe projection adds thesis/assumption/falsifier context while clearly remaining model synthesis.
8. ChatGPT or Deep Research reconciles multiple institutional sources and external public evidence.
9. The answer cites literal source evidence, labels derived synthesis as synthesis and discloses partial/stale/absent coverage.
10. No raw bucket path, credential, filesystem path, SQL surface, unbounded PDF body or self-selected entitlement crosses the MCP boundary.

## 4. Machine outcome

One canonical read path:

~~~
institutional producer
    |
    v
private Research Vault storage
    |
    +--> catalog/admission/source freshness
    |
    +--> canonical PDF + extracted text + full-document evidence segments
    |
    +--> canonical retrieval service
              |
              +--> Brain
              |
              +--> Research Intelligence currentness/persistence
              |
              +--> Mastermind Research MCP
                         |
                         +--> ChatGPT
                         +--> Deep Research
~~~

The MCP is an adapter. It is not the corpus, rights engine, identity system or intelligence store.

## 5. Source and authority map

### Research Vault — Macro

Canonical owner for:

- report/document identity;
- private PDF;
- public-safe catalog;
- FTS corpus;
- source admission;
- source-content freshness;
- server-side report access;
- entitlements/rate limits for current product routes;
- exact source body facts.

Primary source:

- engine/research_vault/
- app/research.py
- scripts/ingest_research.py
- scripts/research_vault_census.py
- scripts/check_research_vault_source_freshness.py
- .github/workflows/research-ingest.yml

### Research Intelligence — Macro

Canonical owner for:

- grounded source claims;
- derived thesis/assumptions/forecast/catalyst/falsifier context;
- exact source-body and prompt binding;
- immutable artifacts and correction-safe latest pointer;
- rights-safe projections.

Primary source:

- engine/research_intelligence/

### Brain — Macro

Canonical model-facing product owner for incumbent research retrieval semantics:

- engine/neuralweb/brain_market_intel.py

Do not build a separate “MCP search brain” whose behavior diverges from the product.

### Evidence receipt precedent — Macro

Reuse the lower-level receipt discipline from:

- engine/company_intelligence/documents.py
- engine/earnings_narrative/contracts.py
- engine/earnings_transcript_intake.py

The canonical primitive is document revision + segment + exact byte span + source hash + replay verification. Do not invent an incompatible evidence hash.

### MCP/Auth — protected Mastermind

Reuse:

- integrations/business_mcp_auth/
- integrations/workbench_read_mcp/
- integrations/executive_mcp/
- current app/tunnel/remote-MCP runbooks

Do not implement another JWT verifier, authorization server, credential database, workspace identity system or tool-approval plane.

### Lifecycle / continuity

Executive OS, Capacity, RuntimeBinding and existing worker owners retain their responsibilities. Agent OS remains the durable continuity owner when a real continuing workstream/handoff exists. This research packet is not a replacement.

## 6. Current red facts Fable must inherit, not rediscover vaguely

### 6.1 Source feed stale

Completed research-ingest run 37158653683:

- ingest itself: rc 0;
- reports ingested: 0;
- reports skipped as already present: 2,778;
- source freshness: PRODUCER_STALE;
- latest admitted report: 2026-09-24T09:28:05Z;
- evaluation time: 2026-10-03T22:41:23Z;
- source age: 229.2 hours;
- fixed source-anchored limit: 96 hours;
- final job: failure.

Do not “fix” this by weakening freshness checks. Diagnose the upstream producer/source path.

### 6.2 Corpus restore/integrity anomaly

The same run attempted to derive the public excerpt snapshot and observed:

- committed excerpt documents: 1,497;
- new derivable excerpt documents: 351;
- collapse floor: 50%;
- write: refused;
- existing snapshot: preserved.

The guard explicitly told the operator to investigate corpus restore.

Do not infer that there are exactly 351 corpus rows; excerpt derivation can omit image-only/empty-body documents. Establish the actual corpus id set, row count, body/text-layer distribution and relationship to catalog/PDF/receipts.

### 6.3 Metadata enrichment is mostly absent

Current 2,778-report catalog:

- summary_points: 2,751 / 2,778;
- pages: 2,673 / 2,778;
- desk: 10 / 2,778;
- tags: 10 / 2,778;
- tickers: 0 / 2,778.

Therefore ticker/theme/subtheme/desk filtering is not an already-built MCP feature.

### 6.4 Full-tail search is absent

Current corpus:

- searchable body cap: 60,000 characters per document;
- evidence selector: at most 3 passages;
- evidence window: 900 characters;
- Brain full-report body cap: 12,000 characters.

Current long-document population among measured reports:

- median pages: 9;
- p90: 24;
- p95: 31;
- p99: 67;
- maximum: 279;
- >50 pages: 48;
- >100 pages: 12.

Do not call the current corpus “full-document retrieval.”

### 6.5 Private-store fallback landmine

Current Research Vault R2 client still allows research-specific endpoint/access key/secret to fall back to shared R2 values.

The repo already records this in:

- agentos/discoveries/DSC-RESEARCH-VAULT-FALLS-BACK-TO-SHARED-PUBLIC-BUCKET.md

A useful design precedent is open HOLD PR #6625 for Radar private evidence. Reuse the pattern — dedicated configuration required, shared/public plane structurally refused — but do not adopt #6625 as authority or merge it as part of this program.

## 7. Existing Research Intelligence carriers

Fable must first classify custody and salvageability of these exact carriers.

### #7461 — claim identity correctness

Purpose: reject malformed/blank model claim rows before support-index compaction can silently rebind derived analysis to a different claim.

Publication-time state:

- OPEN
- DRAFT
- unmerged
- exact head cb844c90d162077e5518061d9932af93a914cda9

This is on the critical path before broad RIO generation.

### #7354 — institutional deep-read head

Purpose: use deterministic research triage to select a bounded top-N set, read canonical private PDFs, extract full text, run W1 Research Intelligence and persist through W2 with exact currentness/model-spend guards.

Publication-time state:

- OPEN
- DRAFT
- unmerged
- exact head b8833c40cb4c9541cc4449e72f5c5f8be8308d1a

Do not rebuild its producer path before reviewing the carrier.

### #7522 — Brain rights-safe RIO consumer

Purpose: let existing Brain report mode consume current W2 Research Intelligence while keeping literal evidence selection source-owned.

Publication-time state:

- OPEN
- DRAFT
- unmerged
- exact head 59a677cc6e899c37eae12364a1cb7d29276238a9

This is the correct consumer pattern if its current-base/custody gates can be satisfied.

### #8090 — longitudinal predecessor selector

Purpose: select a strictly earlier report for exact institution/desk/security stream using identity-safe historical security resolution.

Publication-time state:

- OPEN
- non-draft
- unmerged
- exact head eee2a086d0bdcbfc437bc07d3dbf00ab0855496c

This is strategically valuable but not on the connector MVP critical path.

## 8. Decisions already frozen by this handoff

Fable should not spend another research cycle debating these unless source or authority materially changes.

**D1 — one Research Vault.** No second R2/corpus/document identity owner.

**D2 — one Research Intelligence store.** Extend current RIO contracts; do not create “ChatGPT analysis blobs.”

**D3 — exact evidence before synthesis.** Model-generated analysis never becomes literal citation evidence.

**D4 — MCP is thin and read-only for the first product vertical.**

**D5 — no raw object-store model tools.**

**D6 — full-tail retrieval is required before claiming institutional full-text access.**

**D7 — physical full-text indexing is chosen only after measuring corpus/full-text size and latency.**

**D8 — metadata enrichment is a separate admitted derivative capability; zero ticker coverage cannot be hidden behind an API filter.**

**D9 — source freshness and corpus integrity are model-visible health states.**

**D10 — source correction invalidates dependent text/segments/RIO/optional embeddings by exact source identity.**

**D11 — first production proof is an internal/authorized research canary; broad customer productization is a separate rollout decision.**

**D12 — transport choice is a deployment decision gate, not a new authority plane.**

## 9. Explicit non-goals

Do not create:

- another Research Vault;
- another R2 bucket control plane;
- a generic vector database as a new source of truth;
- another report ID scheme;
- another OAuth or entitlement database;
- another Research Intelligence store;
- a ChatGPT-specific memory database;
- a generic raw R2/filesystem/SQL MCP;
- a new model router;
- a new lifecycle/queue/retry owner;
- automatic trading authority from institutional research synthesis.

Do not broaden third-party redistribution rights.

Do not let an MCP argument select bucket, object key, credentials, filesystem root, principal, entitlement, tier or authorization scope.

## 10. Orchestration law

Fable remains principal for:

- architecture/custody decisions;
- security and rights boundary adjudication;
- held-carrier acceptance/rejection;
- integration decisions;
- final real-path acceptance.

Delegate bounded work such as:

- corpus measurement;
- live id-set census tooling/execution;
- targeted private-store repair implementation;
- retrieval benchmark construction;
- deterministic segmentation implementation;
- MCP schema/server implementation after architecture freezes;
- tests;
- independent review.

Before each actual dispatch:

- check current Capacity/router eligibility;
- issue one bounded mission with source, paths, non-goals, proof and stop condition;
- preserve single-writer custody;
- reserve independent review where material;
- do not assume a model/provider/host is available because this document names a task class.

A worker return is evidence, not automatic acceptance.

## 11. First execution sequence

After deliberate pickup:

1. Read current protected procedure from current Mastermind master.
2. Re-read Macro current main and compare this packet's source pins.
3. Inspect exact current state, review, comments and changed files for #7461/#7354/#7522/#8090.
4. Reconcile any current modifying effects before reusing or replacing a carrier.
5. Run/read the latest Research Vault pipeline and determine whether the producer-stale state changed.
6. Execute the P0 live Vault id-set/corpus census.
7. Fix or formally refuse the private-store shared fallback through the canonical Research Vault owner.
8. Diagnose the corpus restore/excerpt-collapse anomaly.
9. Diagnose source producer staleness.
10. Only when P0 truth is sufficient, freeze the full-tail retrieval physical design and implementation packages.
11. Resolve #7461 before broad RIO production.
12. Reconcile/finish #7354 and #7522 rather than duplicating them.
13. Build the thin Research MCP only after the read contract is canonical and healthy.
14. Prove real ChatGPT + Deep Research canaries.
15. Continue to benchmark/rollout; do not return merely because a source PR merged.

## 12. Stop/escalate conditions

Return to the Chairman/current principal decision owner on:

- conflicting source custody that cannot be reconciled;
- EFFECT_UNKNOWN from a modifying operation;
- new money/account authority;
- a rights/legal decision that would broaden third-party use;
- a material OpenAI platform-contract change;
- a proposal to change a canonical owner rather than consume it;
- evidence that the North Star requires a strategic product change rather than implementation.

A blocked lane blocks that lane, not safe independent work.

## 13. Expected Fable return

A final Fable completion record must state separately:

- source changes and exact commits/PRs;
- Vault safety/integrity state;
- source freshness state;
- full-tail retrieval proof;
- RIO producer/consumer state;
- MCP server state;
- app publication/enrollment state;
- authorized canary proof;
- denied canary proof;
- Deep Research proof;
- benchmark results;
- remaining obligations;
- actual stop reason.

Never compress “built,” “merged,” “deployed,” “installed,” “selected,” “called,” and “accepted” into one word.
