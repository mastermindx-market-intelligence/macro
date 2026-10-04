# Source and collision map — Research Vault AI Intelligence Fabric

This is a navigation/custody document. It does not grant write authority to any child.

**Packet Macro base:** `ce53dddb28a0718a4ab656a5306ef7293b6c779c`  
**Protected Mastermind procedure pin used for publication:** `28be2ce2d481fd542ec869344e178e5cec4d7d75`

At execution START, re-pin current heads and perform bounded compatibility on these exact paths.

---

# 1. Canonical program owner

`config/mastermind_programs.yml`

Program: `qualitative-intelligence`

Current contract:

- lifecycle `operating`;
- owns qualitative evidence, narrative context and provenance;
- does not own deterministic ranks, gates, sizes or trades;
- Macro is implementation owner;
- feeds context to Neural Web/thematic intelligence;
- canonical program doc `research/QUALITATIVE_INTELLIGENCE_MASTERPLAN.md`.

Do not mint a new Research-Vault-AI workstream merely because this is a large project.

Use the existing program and Agent OS handoff.

---

# 2. Research Vault source anchors

## Product/architecture

`research/RESEARCH_VAULT_MASTERPLAN.md`

Use for original product/access/storage decisions.

## Publication-integrity history

`research/RESEARCH_VAULT_WAVE4_CONTINUATION_HANDOFF_2026-08-19.md`

High-value facts:

- catalog/PDF/receipt equality was proven at 1,412;
- corpus only 494;
- 918 reports missing from search;
- exact root cause;
- safe bounded backfill recommendation;
- do not delete receipts to force re-ingest.

Do not treat its 2026 counts as current.

## Core engine

```text
engine/research_vault/__init__.py
engine/research_vault/catalog.py
engine/research_vault/corpus.py
engine/research_vault/ingest.py
engine/research_vault/r2_store.py
engine/research_vault/sidecar.py
engine/research_vault/probe.py
engine/research_vault/excerpt.py
engine/research_vault/view_ratelimit.py
engine/research_vault/download_quota.py
engine/research_vault/watermark.py
```

### Hot collision group A

```text
r2_store.py
ingest.py
corpus.py
excerpt.py
```

Treat changes across these as one Research Vault publication/search owner. Do not assign independent writers that can invalidate the same corpus-generation semantics.

## Serving/API

`app/research.py`

Contains entitlement/catalog/view/download/search product behavior.

Do not copy its route code into MCP.

## Workflow

`.github/workflows/research-ingest.yml`

Do not casually change its source-freshness semantics or publication order.

## Census/freshness

```text
scripts/research_vault_census.py
scripts/check_research_vault_source_freshness.py
```

Prefer these owners before creating new integrity scripts.

---

# 3. Current generated evidence anchors

```text
data/research_vault/catalog.json
data/research_vault/excerpts.json
```

These are evidence/projections, not source-of-truth substitutes for R2.

Do not hand-edit generated snapshots to make a test pass.

---

# 4. Private R2 landmine

`agentos/discoveries/DSC-RESEARCH-VAULT-FALLS-BACK-TO-SHARED-PUBLIC-BUCKET.md`

Current main still contains the fallback behavior the discovery names.

The structural fix belongs to Research Vault.

Do not solve this only inside the MCP adapter.

---

# 5. Research Intelligence current-main anchors

```text
engine/research_intelligence/__init__.py
engine/research_intelligence/extractor.py
engine/research_intelligence/schema.py
engine/research_intelligence/store.py
engine/research_intelligence/projection.py
engine/research_intelligence/vault_adapter.py
research/QUALITATIVE_RESEARCH_INTELLIGENCE_FREEZE_2026-09-12.md
```

### Hot collision group B

```text
schema.py
extractor.py
store.py
vault_adapter.py
```

Claim-array semantics, prompt/source identity and persistence all bind together.

F8/F9 must integrate serially or under one writer.

---

# 6. PR #7461 — structural claim identity

**State at packet publication:**

```text
OPEN
DRAFT
mergeable=false
head=cb844c90d162077e5518061d9932af93a914cda9
updated=2026-09-20
```

## Salvage

The conceptual/source delta in `engine/research_intelligence/schema.py`:

- malformed claim row fails;
- blank claim statement fails;
- no silent compaction before support-index interpretation.

And its focused tests.

## Do not salvage blindly

Old branch test additions to `tests/test_research_vault_strict_store.py` must be reconciled against current test ownership; do not overwrite current additions.

## Priority

Early. This is a correctness precondition for broad RIO generation.

---

# 7. PR #7354 — deep-read deterministic institutional head

**State:**

```text
OPEN
DRAFT
mergeable=false
head=b8833c40cb4c9541cc4449e72f5c5f8be8308d1a
updated=2026-09-19
```

The branch is extremely stale relative to current main.

## Current main already has

- Research Intelligence W2 store;
- projection;
- vault adapter;
- strict-store infrastructure.

Do not replay those old branch versions.

## Unique high-value missing pieces

```text
engine/research_intelligence/vault_head.py
scripts/research_intelligence_vault_head.py
tests/test_research_intelligence_vault_head.py
```

## Concepts to preserve

- reuse deterministic research triage;
- selection independent of publishing quota;
- default head 20 / max 50;
- canonical private PDF, not FTS prefix;
- bounded PDF/body;
- latest RIO currentness check;
- skip duplicate model call;
- exact predecessor for CAS;
- immediate abort on effect unknown.

## Concepts to modify

- replace ambiguous source/body hash naming with explicit PDF/text identity;
- prefer canonical full-text artifact after F5 rather than repeated extraction;
- use current W2 store API;
- use current model/provider routing contract;
- do not introduce scheduler/queue.

---

# 8. PR #7522 — Brain rights-safe RIO consumer

**State:**

```text
OPEN
DRAFT
mergeable=false
head=59a677cc6e899c37eae12364a1cb7d29276238a9
updated=2026-09-21
```

## Useful intent

- latest RIO can enrich generic report mode;
- exact body hash must match;
- RIO states available/missing/stale/invalid/unavailable;
- rights-safe summary projection;
- evidence-specific request still gets literal source passages;
- no-evidence remains no-evidence.

## Preferred integration

Do not transplant the direct store logic unchanged if F10 has created the shared Research Read port.

Port its tests/intended behavior to the canonical consumer.

### Hot collision group C

`engine/neuralweb/brain_market_intel.py`

F11 owns this path after F10 contract freezes.

Do not run an independent Brain rewrite concurrently.

---

# 9. PR #8090 — longitudinal W5 predecessor

**State:**

```text
OPEN
mergeable=false
head=eee2a086d0bdcbfc437bc07d3dbf00ab0855496c
updated=2026-09-27
```

Unique missing path:

`engine/research_intelligence/longitudinal.py`

## Good architecture

- Research Vault institution canonicalization;
- nonempty exact desk;
- exact source ticker observation;
- historical identity through Data OS `VendorAliasTable`;
- stream key institution + desk + security_id;
- strictly earlier predecessor;
- fail closed on ambiguity/ties/conflicting records.

## Current blocker

Current metadata:

```text
desk:    10 / 2778
tickers:  0 / 2778
```

Therefore high abstention is expected and correct.

Do not weaken identity law to make W5 look productive.

Salvage after F6 metadata/identity projection exists.

---

# 10. Exact evidence precedent — earnings/company intelligence

Read for contract precedent, not direct code dependency:

```text
engine/company_intelligence/documents.py
engine/company_intelligence/qa_exchange.py
engine/earnings_transcript_intake.py
engine/earnings_narrative/context_packets.py
```

Borrow:

- document revision;
- body digest;
- segment index;
- exact UTF-8 byte spans;
- text digest;
- replay status;
- bounded packet.

Do not import earnings event/quarter semantics into institutional reports.

---

# 11. Exact identity owners

## Data OS

`lib/dataos/identity.py`

`VendorAliasTable` owns time-scoped symbol -> security identity.

Do not create `research_security_map.json` as a second exact identity master.

## Context resolver

`engine/entity_resolver.py`

May propose candidates/method/confidence.

It is not the exact identity master.

## Institution normalization

`engine/research_vault/sidecar.py::canon_institution`

Reuse before inventing a bank-name map.

---

# 12. Existing qualitative program context

`research/QUALITATIVE_INTELLIGENCE_MASTERPLAN.md`

This broader program contains shared-entity/outcome/qualitative architecture.

The Research Vault AI fabric should extend it where useful but must not absorb the entire qualitative intelligence roadmap.

Keep scope on institutional research retrieval/cognition/access.

---

# 13. Protected MCP/auth owner — Mastermind repo

At execution, pin protected Mastermind `master`.

High-value precedents:

```text
integrations/workbench_read_mcp/app.py
integrations/workbench_read_mcp/service.py
integrations/business_mcp_auth/
integrations/executive_mcp/
integrations/mastermind_company_mcp/
docs/runbooks/workbench-read-r0-production-canary.md
```

## Consume patterns

- strict static tool definitions;
- SDK import isolation;
- OAuth resource policy;
- token verifier;
- final authorization recheck;
- bounded synchronous work;
- read-only annotations;
- loopback/private process owner;
- transport-security allowlists;
- sanitized errors;
- no model root/authority inputs.

## Do not assume

That Workbench project-root semantics directly apply to Research Vault.

Reuse the infrastructure/contract patterns, not the domain arguments.

---

# 14. OpenAI upstream references

Recheck before deployment because product interfaces can change:

- Developer mode/custom MCP:
  https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- Secure MCP Tunnel:
  https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- Plugin/MCP authentication:
  https://developers.openai.com/plugins/build/auth
- MCP deployment:
  https://developers.openai.com/plugins/build/mcp-server

As of 2026-10-04, private read/fetch developer-mode + Deep Research canary is supported; public distribution remains a separate deployment class.

---

# 15. Generated/public product text collision

Existing product/navigation copy includes phrases equivalent to:

> Search every published research note.

Current measured corpus state makes this stronger than proven.

Do not immediately edit marketing copy as a substitute for repair.

First restore/measure retrieval coverage.

If acceptance shows exclusions remain, product copy/coverage disclosure must be reconciled deliberately.

---

# 16. CI collision hotspots

Be cautious with:

`.github/ci/legacy-jobs.yml`

It is a global/concurrent hot path and several stale RIO PRs touched it.

Do not add a new test file/job reflexively without checking the current CI ownership/wiring law.

Prefer existing relevant suites when appropriate, but do not hide meaningful test coverage merely to avoid CI changes.

---

# 17. Exact DO_NOT_REDO

1. Do not build another Research Vault.
2. Do not create a Research MCP-specific document database as canonical state.
3. Do not create a vector DB before benchmark admission.
4. Do not create a new exact ticker/security identity table.
5. Do not create a second RIO persistence path.
6. Do not create plugin-owned entitlements.
7. Do not implement a new OAuth server merely for this project if incumbent auth can serve it.
8. Do not expose arbitrary R2 object operations.
9. Do not delete receipts to rebuild missing corpus rows.
10. Do not use the public excerpt snapshot as the private corpus authority.
11. Do not treat catalog `generated_at` as proof new institutional content is arriving.
12. Do not treat newest report `published_at` as the serving publication generation clock.
13. Do not change RIO v1 `content_sha256` meaning in place.
14. Do not let RIO/model summaries become literal evidence.
15. Do not merge stale RIO PRs wholesale.
16. Do not weaken W5 identity rules to overcome missing metadata.
17. Do not call a source merge "ChatGPT connected."
18. Do not call app creation "installed for every account."
19. Do not expose a public MCP endpoint solely because a private tunnel canary needs connectivity.
20. Do not broaden this project into the entire qualitative/news intelligence program.

---

# 18. Collision-safe salvage order

Recommended integration order:

```text
F1/F2/F3 Research Vault integrity
        |
        +---- F8 #7461 structural claim repair (path-disjoint enough to proceed early)
        |
        v
F5 source/text identity freeze
        |
        v
F9 #7354 unique deep-read salvage
        |
        v
F10 Research Read port
        |
        +---- F11 #7522 Brain behavior salvage
        |
        +---- F12 MCP adapter
        |
        v
F6 identity coverage sufficient
        |
        v
F16 #8090 longitudinal salvage
```

Fable owns the integration decisions at each join.

---

# 19. Current source evidence that must be refreshed at START

Refresh only these decision-changing facts, not the entire company census:

- protected Skillpack pin;
- Macro main pin;
- current open/merged state of #7354/#7461/#7522/#8090;
- current `r2_store` fallback behavior;
- current latest Research Vault workflow and source age;
- current live id-set census once available;
- current protected MCP/auth public contracts;
- current OpenAI developer-mode/tunnel/auth contract before real canary.

Everything else in this packet is a starting map, not a reason to redo accepted archaeology.


---

# 20. Planning-carrier collision ruling

The 2026-10-04 census found three overlapping documentation carriers for this same project:

```text
#8389  docs: Research Vault -> ChatGPT Intelligence Fabric Fable masterplan
#8430  [PLAN/HANDOFF] Fable: institutional Research Vault -> ChatGPT / Deep Research
#8438  docs(research): Fable-ready Research Vault AI intelligence fabric masterplan
```

They are not three independent programs and none proves a Fable START.

**Canonical planning candidate: #8438.**

Reason:

- newest live production evidence;
- explicit historical corpus-gap evidence;
- PDF-byte vs extracted-text-byte identity split;
- F0-F17 dependency DAG;
- body-health hardening addendum;
- current OpenAI private-tunnel/read-only canary contract;
- current protected Mastermind procedure pin;
- explicit stale-PR salvage map;
- authoring QA receipt.

Do not merge all three plans.

Before publication/merge of #8438, inspect #8389/#8430 for any unique accepted evidence not yet represented here, then close or explicitly supersede them under normal GitHub custody.

Their existence is a documentation collision, not source-writer custody over Research Vault implementation paths.

---

# 21. Current packet hardening delta

Post-publication review added:

```text
06_HARDENING_ADDENDUM_AND_FABLE_START_GATE.md
07_FABLE_ORCHESTRATOR_BRIEF_QA.md
```

The addendum controls where earlier text is less precise, particularly:

- current private-R2 bucket vs endpoint/credential fallback semantics;
- ID-set completeness vs body/text retrieval health;
- missing-row vs existing-row/broken-body repair;
- #8438 planning-carrier precedence.

The QA file records a successful non-authoritative Mastermind Craft orchestrator compilation and intentionally does not claim runtime binding or execution authority.
