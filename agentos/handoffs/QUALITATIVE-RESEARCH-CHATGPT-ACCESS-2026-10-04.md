# Agent OS Handoff — Qualitative Research / ChatGPT Institutional Research Access

**Date:** 2026-10-04  
**Parent program:** qualitative-intelligence  
**State:** PREPARED_FOR_DELIVERY / NOT_STARTED  
**Authority effect:** none from this file  
**Planning carrier:** sol/qual-research-chatgpt-fable-masterplan-20261004  
**New workstream:** NOT CREATED

## Mission

Extend the incumbent Research Vault + Qualitative Research Intelligence system so authorized ChatGPT and Deep Research sessions can perform bounded, provenance-preserving institutional-research retrieval without manual PDF uploads.

The intended final capability is:

Research Vault source truth
-> full-document source coverage
-> replayable evidence
-> optional current rights-safe RIO cognition
-> canonical Research Read Service
-> read-only Mastermind Research MCP
-> real ChatGPT + Deep Research use

This handoff deliberately does not create a second organizational parent. The existing qualitative-intelligence program remains the program owner.

## Why this handoff exists

The current system is much closer to the desired end state than a new R2 connector design would suggest.

Already built:
- private Research Vault R2 ingestion;
- canonical institutional PDFs;
- 2,778-report catalog;
- FTS5 corpus;
- existing Research API and entitlements;
- literal source-evidence retrieval;
- Research Intelligence Object v1;
- private versioned RIO persistence;
- rights-safe RIO projections;
- Brain research tools;
- production-proven Mastermind ChatGPT MCP/OAuth/tunnel precedent.

The remaining job is integration, full-document retrieval, source/security repair, and real external read-path acceptance.

## Current source evidence

Protected Mastermind procedure at architecture freeze:
17b9fa1363db6071d338be3373a4fdb11fc0076d

Planning branch base:
bd118c69cc031b33d73b756f95eb5d3723a9dceb

Primary packet:
research/institutional_research_chatgpt_access_20261004/

Read:
- README.md
- EVIDENCE_LEDGER.md
- MASTER_PLAN.md
- FABLE_CEO_HANDOFF.md

## Capability state

Research Vault catalog publication:
PROVEN_LIVE for existing catalog publication.

Research Vault source inflow:
BROKEN/PARTIAL — current typed state PRODUCER_STALE.

Research Vault complete body/search coverage:
PARTIAL — 60k body ceiling plus current excerpt/body degradation.

Literal evidence:
BUILT and merged; current coverage depends on body completeness.

Research Intelligence W1/W2:
BUILT; broad production coverage not established.

Research Intelligence Brain consumer:
BUILT_NOT_PROVEN on open #7522.

Full-document canonical research segments:
NOT_BUILT as a general Vault capability.

Research MCP:
NOT_BUILT.

ChatGPT institutional-research app:
NOT_BUILT.

Deep Research internal-Vault canary:
NOT_BUILT.

## Current live Research Vault findings

Catalog:
- 2,778 reports
- 2,751 with summary points
- 2,673 with page count
- 10 with desk
- 10 with tags
- 0 with tickers

Document length:
- p50 9 pages
- p90 24
- p95 31
- p99 67
- max 279
- 233 reports >25 pages
- 48 reports >50 pages
- 12 reports >100 pages

Current source freshness:
- latest admitted report: 2026-09-24T09:28:05Z
- latest observed source age: ~239.7h
- fixed source deadline: 96h
- state: PRODUCER_STALE

Current excerpt/corpus symptom:
- committed excerpts: 1,497
- fresh derivation: 351
- safety floor correctly refuses overwrite.

## Security discovery

Current Research Vault store can fall back from dedicated R2_RESEARCH_* variables to shared R2_* variables.

Repository records already identify this as a privacy landmine.

Before external Research MCP exposure:
- production Research store must require explicit private research configuration;
- shared/public fallback must be structurally unreachable;
- current real workflow and API deployment must be proven on the intended private store.

## Existing source carriers

### Merged / DO_NOT_REDO

#7101 — Research Intelligence Object v1.

#7230 — versioned RIO persistence.
Canonical merge:
204541291571ad6012a535621437c608489f2526

#7079 — Brain source-bound literal report evidence.
Canonical merge:
0d352926c4ec9c4e5c972bee524b732d3308c617

#8027 — rights-safe belief-context projection.
Merge:
563362aea7d9b532fcd834d44a82b456952c278c

### Open / reconcile

#7461 — RIO claim-index integrity repair.
Head at planning freeze:
cb844c90d162077e5518061d9932af93a914cda9

#7354 — institutional deterministic top-N full-PDF RIO head.
Head:
b8833c40cb4c9541cc4449e72f5c5f8be8308d1a

#7522 — Brain consumes rights-safe current RIO.
Head:
59a677cc6e899c37eae12364a1cb7d29276238a9

#8090 — W5 predecessor selector.
Head:
eee2a086d0bdcbfc437bc07d3dbf00ab0855496c
This is downstream longitudinal Market Cognition and does not block external source retrieval.

Issue #7997 remains the Market Cognition research carrier and explicitly converges on Qualitative Research Intelligence.

## Architecture decision

Do not build:

R2 -> new Cloudflare Worker corpus -> new vector DB -> new auth -> ChatGPT.

Build:

private R2
-> existing Research Vault
-> new canonical untruncated text derivative
-> new deterministic source-bound research segments
-> existing Research Intelligence
-> new thin Research Read Service
-> Brain + separate Mastermind Research MCP
-> ChatGPT / Deep Research

Research Read Service is not a new state owner. It is a read interface over incumbent owners.

## First execution frontier

1. Re-pin current protected procedure and current Macro main.
2. Reconcile source custody around engine/research_vault/r2_store.py.
3. Implement private Research-store fail-closed.
4. Run existing read-only Research Vault live census through research-ingest workflow_dispatch run_census=true.
5. Diagnose the excerpt/corpus collapse.
6. Diagnose source-producer staleness independently.
7. Continue full-document/read-service design while independent diagnostics run.
8. Adjudicate #7461 before broad RIO production.
9. Recover #7354 and #7522 rather than replacing them.
10. Build read-only Research MCP only after the canonical read-service contract is stable.

## Fable routing receipt

PREFERRED_AVENUE: Fable

TASK_COMPLEXITY: C3_FRONTIER_JUDGMENT  
BUSINESS_IMPACT: critical  
EXECUTION_RISK: elevated / private-data-critical substeps  
AMBIGUITY: medium-high  
TOPOLOGY: coordinator

WHY FABLE:
The project spans two repositories, private/licensed source storage, existing open carriers, current source defects, auth/tunnel integration, and production consumer proof. It requires sustained principal adjudication rather than one bounded implementation.

Fable should delegate path-disjoint bounded implementation and verification to the least-scarce admitted workers.

## Source-custody cautions

One modifier per shared owner/path.

High-collision paths include:
- engine/research_vault/r2_store.py
- engine/research_vault/corpus.py
- engine/research_intelligence/schema.py
- engine/research_intelligence/store.py
- engine/neuralweb/brain_market_intel.py
- tests/test_research_vault.py
- tests/test_research_vault_strict_store.py
- .github/ci/legacy-jobs.yml

Do not land implementation on this records-only planning branch.

Each actual source wave should use its existing carrier where one exists or one bounded new implementation carrier after current collision qualification.

## Acceptance

The parent capability is not complete until:

- private Research R2 cannot fall back to shared/public R2;
- live Vault catalog/PDF/corpus/receipt differences are reconciled or explicitly typed;
- a fact beyond the old 60k prefix is searchable;
- exact evidence is replayable against the source revision;
- source corrections invalidate derivatives;
- RIO currentness is explicit;
- literal evidence remains source truth;
- a dedicated read-only Research MCP exists;
- a real authorized ChatGPT session successfully searches/fetches/finds evidence;
- a denied caller leaks no private body/locator/credential;
- a real Deep Research run uses the Vault together with public sources;
- current source staleness is disclosed truthfully;
- rights policy for the exposed projection is accepted.

## Non-goals

No trading authority.

No new signal score.

No Market Cognition replacement.

No new research lifecycle.

No raw R2 tools.

No generic filesystem or SQL tools.

No vector database until a fixed benchmark justifies it.

No broad customer redistribution without rights review.

## Continuation

Durable record owner:
- GitHub for this packet and implementation evidence;
- existing qualitative-intelligence / Agent OS records for organizational continuity.

Exact next action:
Fable or the current principal should reconcile the private Research R2 owner/custody and start the fail-closed private-store wave while the existing live Vault census is run through its canonical workflow.

Do not redo the broad census in this handoff unless current source movement materially invalidates it.
