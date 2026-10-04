# Research Vault AI Intelligence Fabric — Fable orchestration packet

**Date:** 2026-10-04  
**Status:** `EXECUTION_MASTERPLAN / FABLE_ORCHESTRATION_READY / NOT_STARTED`  
**Parent program:** existing `qualitative-intelligence` program — **do not create a new strategic program or control plane**.  
**Macro source pin for this packet:** `ce53dddb28a0718a4ab656a5306ef7293b6c779c`  
**Protected Mastermind procedure pin:** `28be2ce2d481fd542ec869344e178e5cec4d7d75`  
**Chairman intent:** make the existing institutional Research Vault directly usable by authorized ChatGPT / Deep Research sessions through a provenance-preserving, rights-safe, read-only research interface, while repairing the integrity gaps that would otherwise make that interface misleading.

## Start here

Read in this order:

1. [00_FABLE_CEO_ASSIGNMENT.md](00_FABLE_CEO_ASSIGNMENT.md) — principal mission, authority boundary, why Fable, start sequence and non-goals.
2. [01_CURRENT_STATE_CENSUS.md](01_CURRENT_STATE_CENSUS.md) — measured current estate, production failures, source freshness, corpus/search coverage, metadata coverage, Research Intelligence and MCP state.
3. [02_ARCHITECTURE_AND_MASTERPLAN.md](02_ARCHITECTURE_AND_MASTERPLAN.md) — frozen target architecture, ownership, source/text/hash identity, retrieval, segmentation, RIO and MCP design.
4. [03_WORK_PACKAGES_AND_DAG.md](03_WORK_PACKAGES_AND_DAG.md) — dependency graph, collision-safe work packages, delegation envelopes and release sequence.
5. [04_ACCEPTANCE_SECURITY_AND_EVAL.md](04_ACCEPTANCE_SECURITY_AND_EVAL.md) — exact DONE_WHEN, security/rights gates, retrieval benchmark, denial tests and production canaries.
6. [05_SOURCE_AND_COLLISION_MAP.md](05_SOURCE_AND_COLLISION_MAP.md) — exact source anchors, stale PR salvage map, paths that may not be independently rewritten, and DO_NOT_REDO.

Durable organizational continuation lives in:

`agentos/handoffs/RESEARCH-VAULT-AI-FABRIC-2026-10-04.md`

That handoff is **ready-for-orchestration state, not proof of Fable pickup, START, execution, installation or production acceptance**.

---

## One-sentence destination

Turn the existing private Research Vault into the canonical institutional-knowledge interface for frontier reasoning systems:

```text
private institutional PDFs
  -> Research Vault source identity + full text + exact evidence
  -> Research Intelligence derived cognition
  -> one canonical read service
  -> thin authenticated Research MCP
  -> private ChatGPT / Deep Research canary
```

The goal is **not** "give ChatGPT R2 access."

The goal is:

> An authorized frontier model can discover the right institutional reports, retrieve exact source-bound passages including tail pages, distinguish source evidence from Mastermind synthesis, compare revisions and institutions, and cite/replay provenance — without receiving R2 credentials, arbitrary object access, whole-document dumps, or a second research authority.

---

## Architectural ruling

Do **not** build:

```text
R2 -> new vector DB -> new Worker -> new research index -> new auth -> MCP
```

Mastermind already owns almost every layer:

| Capability | Incumbent owner |
|---|---|
| Canonical institutional document/PDF/catalog/search identity | Research Vault |
| Private object bytes | private R2 through Research Vault |
| Derived grounded research cognition | Research Intelligence |
| Exact issuer/security identity | Data OS / `VendorAliasTable` |
| Existing model consumer | Neural Web / Brain |
| OAuth/MCP transport patterns | protected Mastermind integrations |
| Lifecycle/admission | Executive OS |
| Durable organizational continuity | Agent OS |
| Source/PR/CI/evidence | GitHub |

This project fills the **missing seams and integrity gaps**. It creates no competing owner.

---

## Current blocking facts

The plan is based on current measured state, not the old product promise:

- **2,778** reports in the current catalog.
- Newest admitted source report: **2026-09-24 09:28:05 UTC**.
- Latest observed research-ingest source-freshness check, 2026-10-04 18:37 UTC: **249.2 hours stale vs the existing 96-hour source-content freshness limit**.
- Hourly ingest itself completed successfully but admitted **0 new reports**.
- Public excerpt rebuild currently collapses **1,497 -> 351** and is correctly refused by the collapse guard.
- An earlier production census already proved the same underlying defect class: on 2026-08-19, **918 of 1,412 catalog reports were absent from the FTS corpus**. The proposed repair was never implemented.
- Current catalog metadata coverage: **desk 10/2,778; tags 10/2,778; tickers 0/2,778**.
- Current FTS body is capped at **60,000 characters per report**; exact facts deep in long notes are not reliably discoverable.
- Research Intelligence is partly landed but four important continuation PRs remain stale/diverged and must be **salvaged, not wholesale merged**.
- Research Vault private-store construction still permits fallback from `R2_RESEARCH_*` to generic shared `R2_*`; Agent OS records this as a verified private-to-public bucket landmine.
- Adjacent code overloads `content_sha256`: Vault uses it for **PDF bytes**, while Research Intelligence uses it for **extracted UTF-8 body bytes**. The new interface must disambiguate those domains before producing durable citation identities.

These are not reasons to abandon the existing system. They are exactly why this project must harden the incumbent owners before exposing them to frontier models.

---

## Release posture

The first useful product is a **private read-only canary**.

As verified against current OpenAI documentation on 2026-10-04:

- ChatGPT Pro developer mode can connect custom MCPs with read/fetch permissions.
- Deep Research can use custom apps for read/fetch operations.
- ChatGPT does not directly connect to local-only MCP servers.
- OpenAI Secure MCP Tunnel is the preferred private/developer path when the MCP remains behind the firewall.
- Public plugin distribution is a separate release step and requires a stable public HTTPS Streamable HTTP endpoint.
- Authenticated MCP data should use OAuth 2.1 resource-server semantics; Mastermind already has the relevant auth/MCP building blocks.

Current references:
- https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/plugins/build/mcp-server

Do not make public plugin submission a dependency of the private Research Vault canary.

---

## Program-level DONE_WHEN

This packet is fulfilled only when an authorized real ChatGPT session and a real Deep Research run can:

1. discover relevant Research Vault reports;
2. find evidence beyond the old 60k prefix;
3. retrieve bounded literal source evidence with replayable source/text revision identity;
4. distinguish literal evidence from RIO synthesis;
5. observe source-producer and corpus degradation truthfully;
6. respect caller entitlement and licensing/visibility rules;
7. prove denied callers receive no private metadata/body/RIO/object-location leakage;
8. operate without R2 credentials or generic object-store tools;
9. use the same canonical Research Read contract as Brain rather than creating a second retrieval truth;
10. survive source correction/revision with stale derivatives detectably invalidated.

MCP server startup, merged code, green unit tests, app creation, plugin installation and one successful tool call are all **intermediate evidence**, not completion.
