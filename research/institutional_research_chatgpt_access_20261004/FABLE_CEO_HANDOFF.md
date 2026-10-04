# Fable CEO Handoff — Institutional Research Intelligence Access

**Handoff state:** PREPARED_FOR_DELIVERY / NOT_PICKED_UP / NOT_STARTED  
**Parent program:** qualitative-intelligence  
**New workstream:** none  
**Primary repositories:** mastermindx-market-intelligence/macro and mastermindx-market-intelligence/Mastermind  
**Planning carrier:** sol/qual-research-chatgpt-fable-masterplan-20261004

This document is an orchestration brief. It does not itself assign a runtime, start a worker, transfer source custody, install an app, or grant production authority.

## 1. Role

Act as the principal CEO orchestrator for the Institutional Research Intelligence Access program.

Your job is to carry the project from the current Research Vault / Research Intelligence estate to a production-proven read-only institutional-research interface for ChatGPT and Deep Research.

You are responsible for:
- architecture continuity;
- critical-path selection;
- source-custody reconciliation;
- bounded delegation;
- worker-return adjudication;
- security/rights boundary decisions inside existing authority;
- integration;
- real-path acceptance.

You should heavily delegate bounded implementation and verification work through the existing authorized fabric when economical.

You should not personally perform every mechanical edit.

You should not delegate the system-boundary decisions that require principal judgment.

## 2. Why Fable is the preferred avenue

TASK_COMPLEXITY: C3_FRONTIER_JUDGMENT  
BUSINESS_IMPACT: CRITICAL  
EXECUTION_RISK: ELEVATED, with CRITICAL private-data/auth substeps  
AMBIGUITY: MEDIUM_HIGH  
TOPOLOGY: COORDINATOR

FRONTIER_WITNESS:
- two repositories and several incumbent owners must converge without duplication;
- licensed/private institutional source data is involved;
- canonical R2 configuration contains a verified privacy landmine;
- live source freshness and corpus/excerpt degradation are separate faults;
- several high-value Research Intelligence carriers remain open and stale;
- production acceptance requires a real ChatGPT app, OAuth/tunnel, authorized/denied calls and a Deep Research journey.

WHY FABLE:
This is sustained principal orchestration across source, cognition, transport, rights and production proof. The bounded implementation units themselves should usually route to less-scarce workers.

## 3. Mission

Deliver one canonical capability:

An authorized ChatGPT or Deep Research session can search Mastermind's institutional Research Vault, retrieve bounded report context, obtain exact literal evidence from the correct full document revision, optionally consume current rights-safe Research Intelligence, and understand source freshness/coverage — without manual PDF uploads and without access to raw R2/S3 primitives.

The finished interface must be useful to Brain and later Mastermind agents as well.

## 4. User journey

The target user can ask:

“Find the institutional research that first identified an earnings inflection in optical networking. Compare Goldman, JPMorgan, UBS and Morgan Stanley, tell me what assumptions changed, cite the exact source evidence, and reconcile it against public company evidence.”

The system should:
1. search institutional research;
2. return bounded candidates;
3. fetch selected reports;
4. retrieve literal source evidence with provenance;
5. expose current/stale/missing RIO context when useful;
6. synthesize across sources;
7. disclose source freshness and partial coverage;
8. avoid flooding model context with whole PDFs.

## 5. Machine outcome

The machine-facing end state is:

private Research R2
-> existing Research Vault
-> source-hash-bound full-text + deterministic segment derivatives
-> existing Research Intelligence
-> one canonical Research Read Service
-> Brain and Research MCP as sibling consumers
-> ChatGPT / Deep Research

No duplicate owner is allowed.

## 6. Current protected and source references

Before first effect, re-pin current protected source.

Planning evidence was frozen against:
- Mastermind protected source: 17b9fa1363db6071d338be3373a4fdb11fc0076d
- Macro planning branch base: bd118c69cc031b33d73b756f95eb5d3723a9dceb

These are evidence references, not a command to ignore later source movement.

Start by reading:
- docs/sol_skills/INDEX.md
- required current protected companions
- this packet's README.md
- EVIDENCE_LEDGER.md
- MASTER_PLAN.md
- research/QUALITATIVE_RESEARCH_INTELLIGENCE_FREEZE_2026-09-12.md
- research/RESEARCH_VAULT_MASTERPLAN.md

Then inspect only material invalidators.

## 7. Canonical owner map

Research Vault owns:
- document identity;
- canonical PDF/body;
- R2 source storage;
- catalog;
- corpus/search;
- source evidence;
- entitlements/report opening.

Research Intelligence owns:
- RIO schema;
- grounded source claims;
- model synthesis;
- RIO persistence;
- correction-safe RIO currentness;
- rights-safe projections;
- later longitudinal research cognition.

Brain owns:
- one model-facing research consumer.

Mastermind MCP/Auth owns:
- OAuth resource-server mechanics;
- MCP transport;
- Secure MCP Tunnel pattern;
- ChatGPT app operational precedent.

Agent OS owns organizational continuity.

GitHub owns source/PR/CI/evidence.

Do not create another:
- lifecycle;
- workstream merely for neatness;
- research corpus authority;
- identity system;
- entitlement database;
- OAuth issuer;
- retry queue;
- task database;
- model router;
- Research Intelligence store;
- memory store.

## 8. DO_NOT_REDO

Treat these as existing source work unless current source proves they were superseded:

### Merged
- PR #7101 — Research Intelligence Object v1.
- PR #7230 — private versioned RIO persistence; canonical merge 204541291571ad6012a535621437c608489f2526.
- PR #7079 — source-bound literal Brain evidence; canonical merge 0d352926c4ec9c4e5c972bee524b732d3308c617.
- PR #8027 — rights-safe belief-context projection; merge 563362aea7d9b532fcd834d44a82b456952c278c.

### Existing Research Vault
Do not rebuild:
- hourly R2 ingestion;
- private PDF promotion;
- public-safe catalog;
- corpus.sqlite;
- existing FTS;
- existing report API;
- existing view/download entitlements;
- existing source-freshness guard;
- existing read-only Vault ID-set census.

### Mastermind transport
Do not build a second OAuth stack.

The production-proven Executive app is precedent for:
- authenticated ChatGPT app;
- OAuth;
- Secure MCP Tunnel;
- exact tool discovery.

Research must receive a separate read-only resource/scope.

## 9. Existing open carriers — reconcile before writing

### PR #7461 — RIO claim identity

Current planning head:
cb844c90d162077e5518061d9932af93a914cda9

Paths:
- engine/research_intelligence/schema.py
- tests/test_research_vault_strict_store.py

Purpose:
Reject malformed/blank claim rows before support indices can silently shift.

Disposition:
High priority before broad RIO generation.

### PR #7354 — institutional deep-read head

Current planning head:
b8833c40cb4c9541cc4449e72f5c5f8be8308d1a

Already implements:
- canonical private PDF read;
- full pdftotext source body;
- top-N deterministic head;
- model-spend currentness guard;
- W1/W2 persistence;
- stop on EFFECT_UNKNOWN.

Disposition:
Recover and finish. Do not reimplement.

### PR #7522 — Brain RIO consumer

Current planning head:
59a677cc6e899c37eae12364a1cb7d29276238a9

Disposition:
Recover and finish after current custody/release review. Do not build another RIO-to-Brain path.

### PR #8090 — W5 predecessor selector

Current planning head:
eee2a086d0bdcbfc437bc07d3dbf00ab0855496c

Disposition:
Downstream. Keep path custody intact. Do not put it on the MCP critical path.

### Issue #7997

Market Cognition parent research carrier.

Key ruling:
Market Cognition converges on incumbent Qualitative Research Intelligence and must not become a parallel psychology/research system.

## 10. Live estate facts you must preserve

At planning freeze:
- reports: 2,778
- summary coverage: 2,751
- pages coverage: 2,673
- desk: 10
- tags: 10
- tickers: 0
- latest report: 2026-09-24T09:28:05Z
- current source age observed: approximately 239.7 hours
- source freshness limit: 96 hours
- state: PRODUCER_STALE

Report length:
- p50 9 pages
- p90 24
- p95 31
- p99 67
- max 279
- 233 reports over 25 pages
- 48 over 50
- 12 over 100

Current corpus:
- 60,000-character body ceiling.

Current excerpt plane:
- committed excerpts: 1,497
- currently derivable: 351
- guard refuses collapse.

These facts make full-tail search and corpus integrity real critical-path concerns.

## 11. P0 security problem

Current Research Vault R2 builder can fall back from R2_RESEARCH_* to shared R2_*.

Existing repository evidence records this as a private/public boundary landmine.

Before exposing Research Vault through an external MCP:
- remove implicit shared fallback for the production Research store;
- require explicit dedicated private Research configuration;
- refuse partial config;
- refuse a binding that aliases a shared/public delivery plane;
- confirm current workflow and macro-api are explicitly configured.

Do not solve this in the MCP.

## 12. First orchestration wave

Do not start by asking a worker to build ChatGPT tools.

The first wave is:

### Lane A — Vault security

Mission:
Make the canonical private Research store fail closed.

Worker:
least-scarce strong backend/security implementer.

One writer:
r2_store owner path.

Return:
- exact PR/head;
- tests;
- current deployment configuration census without secret values;
- real workflow/API proof;
- remaining deployment gate.

### Lane B — live integrity census

Mission:
Run the existing read-only Research Vault census against real R2 and classify differences.

This may be executed by Fable directly if workflow-dispatch/readback overhead is lower than delegation.

Do not create new census code.

Return:
- exact workflow run;
- artifact identity;
- catalog/PDF/corpus/receipt counts;
- set differences;
- corpus object size where observed.

### Lane C — source producer freshness

Mission:
Find why 0 new reports have arrived since September 24.

Keep independent from Lane B.

Return:
- actual source producer state;
- failure layer;
- repair or typed outage;
- no guard weakening.

### Lane D — excerpt/corpus collapse

Start after or with census evidence.

Mission:
Explain why current corpus yields 351 excerpts versus committed 1,497.

Return:
- causal diagnosis;
- affected IDs/states;
- canonical repair;
- re-run evidence.

Fable retains integration and privacy judgment.

## 13. Second orchestration wave

After P0 substrate truth:

### RIO correctness
Finish #7461.

### Full-text derivative
Build source-hash-bound untruncated text artifacts.

### Segment receipts
Build deterministic page/byte-bound segments using the source_span precedent.

### Retrieval benchmark
Measure before choosing index technology.

The worker must not assume a vector database.

## 14. Third orchestration wave

### Research Read Service

Freeze one SDK-free domain contract for:
- status;
- search;
- fetch;
- find evidence.

It should consume incumbent owners.

The service is the convergence seam.

### Recover #7354
Use canonical full text where appropriate while preserving its bounded top-N/cost behavior.

### Recover #7522
Keep literal evidence authoritative.

## 15. Fourth orchestration wave

In Mastermind:

Build a separate Mastermind Research MCP.

Tool set:
- research_status
- research_search
- research_fetch
- research_find_evidence

All read-only.

Do not expose:
- r2_list
- r2_get
- arbitrary file read
- raw SQL
- shell
- presign arbitrary object
- model-selectable bucket or key.

Reuse business_mcp_auth and current production MCP patterns.

## 16. Auth/resource law

Research gets a dedicated resource/scope.

Do not reuse Executive's resource merely because its app is proven.

Proposed semantic scope:
mastermind.research.read

The exact name/URI is subject to current auth owner conventions.

Authenticated caller context selects authority.

Model arguments never select:
- principal;
- entitlement;
- workspace authority;
- bucket;
- source root;
- credential.

## 17. Rights law

Institutional research may be licensed/private.

Every output class must declare its permitted projection.

Model reasoning does not erase source rights.

Never assume:
- summary = public;
- embedding = public;
- RIO = public;
- ChatGPT-connected = redistributable.

Initial canary can remain internal/authorized.

Broader customer exposure requires rights-owner acceptance.

## 18. Research Read Service acceptance

A report beyond the current 60k prefix must be discoverable.

For a selected literal passage, return:
- report ID;
- source content SHA;
- page/segment identity;
- exact text hash;
- literal bounded text;
- coverage state.

Replay must succeed.

A correction must make the previous derivative stale.

## 19. MCP acceptance

Source-level:
- exact static tool list;
- strict schemas;
- bounded input/output;
- sanitized errors;
- no private fields through projection widening;
- no raw storage primitives.

Auth:
- wrong audience/resource/scope refused;
- expired token refused;
- body entitlement enforced.

Transport:
- private service reachable through current accepted private-MCP pattern;
- no direct public unauthenticated endpoint.

## 20. ChatGPT acceptance

Prove one real authorized journey and one denied journey.

Authorized:
search -> fetch -> evidence -> multi-report comparison.

Denied:
no/private body leakage.

The response must disclose current Research Vault freshness state.

## 21. Deep Research acceptance

Run one real mixed internal/public research task.

Deep Research must:
- use the Research app;
- find internal institutional sources;
- find public sources;
- separate those evidence families;
- cite exact institutional passages;
- not require manual PDF upload.

## 22. Delegation packet standard

Every child receives:
- mission;
- why;
- exact source ref;
- proposed write paths;
- incumbent owner/dependencies;
- non-goals;
- time/null/correction behavior;
- deterministic vs model method;
- failure semantics;
- acceptance;
- stop conditions;
- return location.

Do not give children the entire CEO transcript.

Children do not inherit every parent integration or production permission.

## 23. Suggested worker routing

Use current Capacity/Model Router truth, not these labels as hard-coded provider assignments.

Backend/security code:
- economical strong coding worker where admitted.

Data/retrieval benchmark:
- capable data/backend worker.

Adversarial privacy/rights review:
- independent strong reviewer.

MCP/auth integration:
- strong backend worker with current Mastermind MCP source access.

Fable retains:
- architecture;
- privacy boundary adjudication;
- collision/custody reconciliation;
- worker-return integration;
- release/production proof judgments.

## 24. Checkpoint law

Persist material decisions and exact source/effect state through existing owners.

Checkpoints are saves, not turn-ending events.

After each accepted phase:
1. verify;
2. persist;
3. reassess parent mission;
4. begin the next safe ready phase.

Do not return to the Chairman merely because:
- a PR was opened;
- a test suite passed;
- a worker was dispatched;
- a phase ended;
- one lane is waiting.

## 25. Stop conditions

Stop and escalate only for:
- new legal/rights decision;
- new spend/subscription;
- destructive source migration;
- new canonical owner/control plane;
- irreconcilable source custody;
- unresolved modifying EFFECT_UNKNOWN that blocks all useful dependent work;
- production admin ceremony only the Chairman/operator can perform after all independent useful work is exhausted.

Otherwise continue.

## 26. Acceptance law

Never conflate:
- planned;
- source built;
- PR open;
- CI green;
- merged;
- installed;
- service reachable;
- app published;
- app connected;
- OAuth succeeded;
- tool called;
- Deep Research used it;
- production accepted.

Report each separately.

## 27. Exact first action

After current-source repin:

1. inspect current r2_store.py and open path writers;
2. confirm dedicated research env is present in workflow/API configuration without retrieving secret values;
3. commission the fail-closed private-store patch;
4. run the existing workflow-dispatch Vault census;
5. continue useful integration work while those independent lanes execute.

Do not spend the first Fable turn re-researching the entire Research Vault.

This packet has already done the broad architecture census.

Re-open broad architecture only when a material current-source falsifier appears.
