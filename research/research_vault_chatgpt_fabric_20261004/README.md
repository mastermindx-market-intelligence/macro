# Research Vault -> ChatGPT Intelligence Fabric — Fable takeover packet

**Status:** PRE-START / EXECUTION MASTERPLAN PUBLISHED  
**Purpose:** durable source-grounded handoff for a later deliberate Fable orchestration pickup.  
**This publication does not claim:** Fable pickup, Executive admission, worker START, deployment, app enrollment, plugin installation, production acceptance, or authority beyond the Chairman request that caused this packet to be authored.

## 0. Start here

This packet supersedes the earlier conversational masterplan as the execution reference for the Research Vault -> ChatGPT / Deep Research project.

Read in this order:

1. [00_FABLE_CEO_ASSIGNMENT.md](00_FABLE_CEO_ASSIGNMENT.md) — mission, WHY FABLE, source ownership, non-goals and first actions.
2. [01_CURRENT_STATE_CENSUS_AND_REUSE_MAP.md](01_CURRENT_STATE_CENSUS_AND_REUSE_MAP.md) — current evidence, quantitative Vault census, live failure state, open carriers and reuse map.
3. [02_ARCHITECTURE_AND_PRODUCT_MASTERPLAN.md](02_ARCHITECTURE_AND_PRODUCT_MASTERPLAN.md) — target architecture, contracts, wave DAG, product behavior and decision gates.
4. [03_FABLE_WORK_PACKAGES_AND_WAVE_DAG.md](03_FABLE_WORK_PACKAGES_AND_WAVE_DAG.md) — bounded orchestration packages, dependency order, delegation/review rules and expected returns.
5. [04_ACCEPTANCE_SECURITY_AND_CONTINUATION.md](04_ACCEPTANCE_SECURITY_AND_CONTINUATION.md) — DONE_WHEN, security/rights acceptance, real-path canaries, failure law and exact continuation frontier.

## 1. Why a hardened revision was necessary

The first paper got the high-level direction right: do not create a second Research Vault; join the existing Vault, Research Intelligence, Brain and Mastermind MCP/auth owners.

It was not yet sufficient to initiate a principal-led build. The additional census changed the critical path in five important ways:

1. **The current source feed is actively stale.** The completed research-ingest run 37158653683 reported PRODUCER_STALE: the newest admitted report was 229.2 hours old against a 96-hour source-anchored limit. The publisher itself was still able to run, so publication freshness and source-content freshness must remain separate.
2. **The same run exposed a corpus-integrity anomaly.** Public excerpt derivation collapsed from the committed 1,497 reports to 351; the Vault guard refused to overwrite the good snapshot and explicitly said to investigate the corpus restore. This makes a live id-set/corpus census a P0 gate before any model connector.
3. **The metadata plane is much thinner than the sidecar schema suggests.** Current 2,778-report coverage is: summary_points 2,751; pages 2,673; desk 10; tags 10; tickers 0. Ticker/theme/desk filtering is therefore a new enrichment capability, not a switch the MCP can simply expose.
4. **Full-document search is not current behavior.** The canonical corpus truncates every searchable body to 60,000 characters, while Brain report exposure caps body text at 12,000 characters. The full archive contains long documents: among 2,673 reports with page counts, p95 is 31 pages, p99 is 67, the maximum is 279, 48 reports exceed 50 pages and 12 exceed 100 pages.
5. **The implementation is split across held existing carriers.** Four open Research Intelligence PRs already own substantial parts of the required path. A new implementation must reconcile them, not silently replace or duplicate them.

The hardened program therefore starts with Vault truth and custody, not MCP code.

## 2. Exact source pins used for this publication

Protected Mastermind procedure and reusable MCP/auth source:

- mastermindx-market-intelligence/Mastermind
- protected master observed: 03f7ca04cd5b0a3abf7166221dd77d403c7f95df
- Skillpack 1.0.1 / bootstrap major 1
- ACTIVE_EXECUTION and WEB_CEO_DELEGATION enrolled
- SESSION_RELIABILITY not enrolled at this pin

Macro source:

- mastermindx-market-intelligence/macro
- main observed before this branch: 1b4edfb438f7ff7edca5097f0c90243a49207d1e

This branch was created from that exact Macro commit. A receiving Fable session must re-pin both repositories before effects; these pins are evidence for this authoring operation, not permanent authority.

## 3. North Star

An authorized ChatGPT or Deep Research session should be able to ask a real institutional-intelligence question and get:

- truthful source-plane health;
- canonical report discovery;
- exact source-bound evidence, including evidence beyond the current 60k searchable prefix;
- correction-aware document identity;
- bounded, rights-safe Research Intelligence context when current;
- cross-report synthesis that never impersonates literal evidence;
- no raw R2, filesystem, SQL, credential or entitlement-selection authority.

Example end-state question:

> Which institutions identified the optical-interconnect / 1.6T networking inflection first, what exactly changed in their assumptions, when could Mastermind have known it, which literal passages support the chronology, and which public company/government evidence corroborated it?

The correct answer path is deterministic retrieval -> exact evidence -> optional RIO -> frontier synthesis. It is not “download a folder of PDFs into the model.”

## 4. Canonical owner ruling

This program adds no new control plane.

- **Research Vault** owns report identity, private PDF/body, catalog, corpus, ingestion, document admission, entitlement-aware report access and source freshness.
- **Research Intelligence** owns grounded private derived analysis and its correction-safe persistence.
- **Company/Earnings evidence contracts** provide the reusable exact-span receipt discipline.
- **Brain** owns model-facing research semantics inside the Macro product.
- **Mastermind MCP/Auth** owns app transport, token/resource validation and MCP hardening patterns.
- **GitHub** owns implementation, PRs, review and CI evidence.
- **Agent OS** may own durable organizational continuation only after a real program assignment/continuation requires it; this authoring packet does not manufacture a new workstream.
- **Executive OS / Capacity / existing worker owners** retain lifecycle, admission, placement and execution authority.

## 5. Current P0 blockers

Do not expose a new Research MCP to real private content until the receiving program has adjudicated all four:

1. **Private-store isolation:** research-specific R2 configuration currently falls back to shared R2 credentials/endpoint. Existing discovery DSC-RESEARCH-VAULT-FALLS-BACK-TO-SHARED-PUBLIC-BUCKET records the resulting public-plane risk.
2. **Live corpus integrity:** the 1,497 -> 351 excerpt-collapse event must be explained through a real R2/corpus/id-set census before the new read path trusts the corpus.
3. **Producer freshness:** current source admission is stale even though the hourly publisher still runs.
4. **RIO claim identity:** open PR #7461 documents a structural claim-index compaction bug in current Research Intelligence validation. Broad RIO backfill must not outrun that correctness decision.

These block the affected production lanes. They do not require pausing safe architecture, measurement, held-PR review, or transport-source work.

## 6. Existing carriers that must be reconciled

- **#7461** — preserve RIO claim identity during validation.
- **#7354** — deterministic institutional cognition head; canonical PDF full-read -> W1 analysis -> W2 persistence.
- **#7522** — Brain consumes current rights-safe Research Intelligence while literal evidence remains sourced from the Vault.
- **#8090** — identity-safe longitudinal predecessor selector for later belief-change work.

At publication time all four were open and unmerged. Their exact heads and state are recorded in 01.

## 7. External platform boundary

Current OpenAI platform behavior was rechecked during this authoring pass. The implementation owner must recheck it again at deployment:

- Pro developer-mode custom MCP connections support read/fetch tools.
- Deep Research can use custom apps for read/fetch.
- Agent mode does not use custom apps.
- A local/private MCP requires the supported private-network path; Mastermind also has an existing hardened authenticated remote-HTTPS precedent.
- Authenticated MCP uses OAuth/resource-server semantics; authorization belongs in the server, not in model prose.

Official references at authoring time:

- https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt
- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/plugins/mcp-server

The packet intentionally leaves the final Tunnel-vs-authenticated-remote deployment selection behind an explicit implementation gate. Transport is not research authority.

## 8. Mastermind Craft authoring receipt

The orchestrator brief for this packet was compiled with the installed Mastermind Craft compiler.

- input_sha256: 2c453a01acb62966a17c460601116d1dfe24e156d6873818f0487d46165879e9
- method_sha256: 1ad99fbeddee07cd3c4b6996448a190f570a80ac32c52c2c47b8948c6fec6a5b
- markdown_sha256: 0f95a7fc5a566913ad33f84d202ca837d03a9b01bff7c11a23cd1f5b2a20f534
- binding_observation: UNBOUND_AUTHORING
- execution_authority: false
- runtime_admission: NOT_REQUESTED

That receipt checks handoff structure only. It is not Fable START, source authentication, deployment approval or production acceptance.

## 9. Completion meaning

The project is not complete when:

- the document bundle merges;
- R2 is reachable;
- a full-text index exists;
- an MCP server starts;
- a ChatGPT app is created;
- the app appears in a tool list;
- a unit-test suite is green.

It is complete when the acceptance ledger in 04 proves, on real paths, that a healthy authorized session can retrieve tail-page institutional evidence with exact provenance and current rights-safe intelligence, an unauthorized session cannot learn private material, corrections invalidate dependent state, Deep Research can use the source without manual PDF upload, and the system reports degraded source/corpus health truthfully.

## 10. Immediate continuation frontier

On deliberate Fable pickup:

1. re-pin protected Mastermind and Macro;
2. reconcile path/custody of #7461/#7354/#7522/#8090;
3. inspect the currently active/latest research-ingest run and live Research Vault store;
4. execute the P0 private-store + live-corpus-integrity + producer-freshness wave;
5. only then admit implementation waves whose prerequisites are proven.

Continue across phase boundaries while safe, useful work remains. A checkpoint is a save, not a stop.
