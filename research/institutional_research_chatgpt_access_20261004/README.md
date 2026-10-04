# Institutional Research Intelligence Access — Fable Takeover Packet

**Date:** 2026-10-04  
**Parent program:** qualitative-intelligence  
**State:** PREPARED_FOR_DELIVERY / NOT_STARTED  
**Planning carrier:** this branch only  
**Production authority:** unchanged  
**New Agent OS workstream:** none

## Mission

Turn the existing Mastermind Research Vault into a canonical, provenance-preserving institutional-research interface that authorized ChatGPT and Deep Research sessions can query directly, without manual PDF uploads and without creating a second Research Vault, corpus, identity system, authorization system, intelligence store, queue, retry plane, or control plane.

The desired user journey is:

1. search institutional research by query, institution, date, security, theme, or other supported metadata;
2. identify the most relevant reports;
3. fetch bounded report context;
4. retrieve literal source evidence with exact document/revision provenance;
5. optionally consume rights-safe Research Intelligence Objects;
6. synthesize across institutional research and public sources;
7. know when source coverage is stale, partial, scanned, corrected, or unavailable.

The desired machine outcome is a single read contract shared by Brain, ChatGPT, Deep Research, and later agents, with Research Vault remaining the source/retrieval authority and Research Intelligence remaining the derived-cognition authority.

## Read this first

This packet is a current-source execution plan, not a replacement architecture.

The census found that most of the hard system already exists:

- Research Vault already owns private R2 ingestion, canonical PDFs, catalog identity, an FTS5 corpus, source-bound evidence retrieval, product entitlements, and report serving.
- Research Intelligence v1 already owns grounded claims, derived thesis/forecast/catalyst/falsifier structure, exact source-body binding, private versioned persistence, and rights-safe projections.
- Brain already has a model-facing Research Vault path and literal evidence mode.
- Company/Earnings Intelligence already has a mature document-revision -> segment -> exact span -> replayable receipt pattern that should guide research-paper segmentation.
- Mastermind already has production-proven ChatGPT Business MCP/OAuth/Secure-MCP-Tunnel infrastructure through the Executive app. The Research app must reuse that pattern while remaining a separate read-only resource and scope.

Therefore the correct architecture is not:

R2 -> new Cloudflare research system -> new index -> new auth -> ChatGPT

It is:

institutional source producer
-> private R2
-> existing Research Vault
-> canonical full-text / source-bound segment derivatives
-> existing Research Intelligence where useful
-> one canonical Research Read Service
-> sibling consumers: Brain and Mastermind Research MCP
-> ChatGPT / Deep Research

## Critical live findings

The current Research Vault has 2,778 reports.

At the planning freeze:

- summary_points: 2,751 / 2,778
- pages: 2,673 / 2,778
- desk: 10 / 2,778
- tags: 10 / 2,778
- tickers: 0 / 2,778
- median report length: 9 pages
- p90: 24 pages
- p95: 31 pages
- p99: 67 pages
- maximum: 279 pages
- reports over 25 pages: 233
- reports over 50 pages: 48
- reports over 100 pages: 12

The current FTS corpus stores only the first 60,000 characters of each body, so full-document tail retrieval is not guaranteed.

The latest scheduled Research Vault run observed for this packet:

- ingested 0 new reports;
- skipped all 2,778 known reports;
- successfully republished the corpus and catalog;
- failed its source-freshness gate because the newest admitted report is still 2026-09-24T09:28:05Z;
- observed source age was approximately 239.7 hours against a 96-hour source-anchored ceiling;
- typed state: PRODUCER_STALE.

A second independent defect is also live:

- the committed public excerpt snapshot contains 1,497 documents;
- the currently derived snapshot contains only 351;
- the collapse guard correctly refuses to overwrite the good snapshot.

Do not merge those two defects into one diagnosis. Source inflow freshness and corpus/excerpt completeness are distinct planes.

## Hard P0 security gate

The private Research Vault store still permits research credentials to fall back to shared R2 credentials when the research-specific variables are absent.

That behavior was originally intentional for same-account compatibility, but the repository now has a verified discovery that it can violate the intended private-store boundary.

Before any external Research MCP exposure, the canonical Research Vault storage owner must fail closed when the dedicated private research plane is missing or aliases a shared/public delivery plane.

Do not hide this inside the MCP adapter.

## Existing carriers — preserve and reconcile

Do not rebuild accepted work:

- RIO W1: merged PR #7101.
- RIO W2 versioned persistence: merged PR #7230 / canonical merge 204541291571ad6012a535621437c608489f2526.
- source-bound Brain evidence R1B: merged PR #7079 / canonical merge 0d352926c4ec9c4e5c972bee524b732d3308c617.
- rights-safe belief-context projection W4: merged PR #8027 / merge 563362aea7d9b532fcd834d44a82b456952c278c.

Open carriers to reconcile rather than duplicate:

- #7354 — institutional top-N full-PDF deep-read producer.
- #7522 — Brain consumes rights-safe current RIO.
- #7461 — RIO claim-index identity repair.
- #8090 — longitudinal predecessor selector; downstream Market Cognition work, not an MCP critical-path dependency.
- issue #7997 — parent Market Cognition research carrier; explicitly converges on existing Qualitative Research Intelligence rather than creating a second psychology/research system.

## Packet contents

- MASTER_PLAN.md — end-to-end build program, dependency DAG, interface contracts, wave acceptance, routing, security, rights, evaluation, and DONE_WHEN.
- EVIDENCE_LEDGER.md — current-source census, live run evidence, carrier inventory, unknowns, and falsifiers.
- FABLE_CEO_HANDOFF.md — orchestration-ready takeover instructions and delegation law.
- INITIAL_WORK_PACKETS.md — dispatch-ready bounded first-wave packets for security, live census, freshness, corpus repair, RIO correctness, and full-text measurement.
- AUTHORING_QA.md — structural handoff-compiler receipt; explicitly unbound and non-authorizing.
- ../../agentos/handoffs/QUALITATIVE-RESEARCH-CHATGPT-ACCESS-2026-10-04.md — durable Agent OS handoff into the existing qualitative-intelligence parent.

## First action

The first source-modifying implementation wave is not “build the MCP.”

It is:

1. reconcile custody on the current Research Vault store path;
2. make private Research Vault R2 selection fail closed;
3. run the existing read-only live Research Vault ID-set census against real R2;
4. classify the source-freshness and excerpt-collapse defects independently;
5. only after the private/source substrate is understood, begin external read-surface implementation.

## Completion standard

The project is complete only when an authorized real ChatGPT session and a real Deep Research run can search the Vault, retrieve bounded report context, obtain replayable literal evidence from full-document coverage, consume rights-safe derived intelligence when available, and see honest freshness/coverage states — while an unauthorized caller receives no private content, locator, object-store key, credential, or source-body leakage.

Source merge, MCP server startup, app publication, app installation, OAuth success, and one tool call are all intermediate facts. They are not interchangeable with production acceptance.
