# Execution DAG and work packages — Research Vault AI Intelligence Fabric

**Parent program:** existing `qualitative-intelligence`  
**Orchestration owner:** Fable principal integrator when lawfully picked up/started.  
**Execution principle:** architecture and cross-owner judgments stay with the principal; bounded implementation goes to least-scarce qualified workers.

No child described here is automatically dispatched by this document.

---

# 1. Dependency DAG

```text
F0 CURRENT-SOURCE / CUSTODY RECONCILIATION
 |
 +--> F1 PRIVATE R2 FAIL-CLOSED BOUNDARY
 |       |
 |       +--> F2 LIVE VAULT ID-SET + SIZE CENSUS
 |                 |
 |                 +--> F3 CORPUS COMPLETENESS / EXCERPT REPAIR
 |                 |       |
 |                 |       +--> F5 FULL-TEXT + SEGMENT ARTIFACTS
 |                 |                 |
 |                 |                 +--> F7 FULL-TAIL RETRIEVAL
 |                 |
 |                 +--> F4 SOURCE-PRODUCER FRESHNESS REPAIR
 |
 +--> F6 METADATA / IDENTITY ENRICHMENT
 |       |
 |       +----------------------------------+
 |                                          |
 +--> F8 RIO STRUCTURAL CORRECTNESS          |
         |                                   |
         +--> F9 RIO DEEP-READ PRODUCER      |
                     |                       |
                     +-----------------------+
                               |
                               v
                    F10 CANONICAL RESEARCH READ PORT
                         |                 |
                         v                 v
                    F11 BRAIN         F12 RESEARCH MCP
                       CONVERGENCE          |
                                           v
                                  F13 PRIVATE CHATGPT CANARY
                                           |
                                           v
                                  F14 DEEP RESEARCH CANARY
                                           |
                                           v
                                  F15 RETRIEVAL / RIGHTS EVAL
                                           |
                                           +--> F16 LONGITUDINAL W5
                                           |      (optional later)
                                           |
                                           +--> F17 SEMANTIC INDEX
                                                  only if benchmark proves need
```

F4 source-freshness repair may proceed independently once F1/F2 establish safe observation.

F6 metadata work may begin read-only earlier but must not publish authoritative derived identity until its owner contract is frozen.

F8 can be salvaged independently because it is a local structural correctness fix. Broad RIO production waits for the full-text/hash contract.

---

# 2. Shared source-custody rule

Before each modifying work package:

- current Macro main must be pinned;
- current protected Mastermind law must be pinned where relevant;
- exact writer custody for affected paths must be recovered;
- overlapping stale PRs are read/salvage evidence;
- one source writer owns a shared path at a time;
- a lost modifying response is reconciled on that same carrier before replay.

Do not make every lane wait for unrelated paths or unrelated main movement.

---

# 3. F0 — current-source and carrier reconciliation

## Outcome

One collision-free execution map against current source.

## Read scope

```text
engine/research_vault/
engine/research_intelligence/
engine/neuralweb/brain_market_intel.py
app/research.py
scripts/research_vault_census.py
.github/workflows/research-ingest.yml
agentos/discoveries/DSC-RESEARCH-VAULT-FALLS-BACK-TO-SHARED-PUBLIC-BUCKET.md
PRs 7354, 7461, 7522, 8090
protected Mastermind MCP/auth paths
```

## Required output

A small path/custody matrix:

```text
path
current main blob/head
active writer?
salvage PR?
allowed next writer
dependency
```

## Acceptance

No modifying package begins on a path with an unresolved current writer/effect.

## Stop/return

Return to Fable only if two active modifications truly collide or source law changed materially.

---

# 4. F1 — private R2 fail-closed boundary

## Why first

No new external read adapter should rely on a factory whose effective private-plane isolation is configuration-dependent. Current `build_store()` requires an explicit research bucket, but endpoint/key/secret may inherit generic `R2_*` values and no canonical assertion rejects a research bucket that aliases the shared/public bucket.

## Proposed source owner

`engine/research_vault/r2_store.py` plus its owning tests/deployment configuration.

## Requirements

Production/private Research Vault construction must:

1. require an explicit research bucket;\n2. reject partial research configuration;\n3. reject equality/alias with the configured shared/public delivery bucket where that can be established;\n4. make endpoint/credential inheritance an explicit security-owner decision rather than silent generic `R2_*` fallback;\n5. prove the effective production Research Vault plane is private/distinct under the deployed configuration;\n6. never print credentials;\n7. preserve explicit `LocalStore` / test usage as a deliberate mode;\n8. preserve existing strict compare-and-swap semantics used by RIO/private publication.

## Tests

At minimum:

- no research bucket + generic shared vars -> refuse private store;\n- partial research configuration -> refuse;\n- research bucket == shared/public bucket -> refuse;\n- generic endpoint/credential inheritance -> either refuse or pass only under an explicitly qualified security policy; never silently imply dedicated isolation;\n- dedicated complete research plane -> construct;
- local explicit store -> works;
- exception/public error contains no secret;
- private RIO/store tests remain green.

## Acceptance

Readback proves the active private deployment still resolves a dedicated Research Vault plane.

Source change alone is not deployment proof.

---

# 5. F2 — real Vault integrity and capacity census

## Outcome

Replace historical/indirect corpus assumptions with current canonical counts and storage measurements.

## Use incumbent tooling

`scripts/research_vault_census.py`

Extend only if it cannot report a required deterministic fact without mutation.

## Required census

```text
catalog count
vault PDF count
receipt count
corpus row count

catalog - pdf
pdf - catalog
receipt - catalog
catalog - corpus
corpus - catalog

repo mirror generation vs canonical catalog

corpus.sqlite bytes\ncorpus nonempty-body / empty-body counts\nbody character distribution\nvalid PDF content-hash coverage\nsource-char-count vs stored-body-char consistency\npage-separator / page-count coverage\nexcerpt-derivable row count\ncatalog rows with a corpus ID but no usable body\ncanonical PDF total bytes\nfull extracted-text sample/estimated total\ntext-layer distribution\nreport char/page distribution
```

Where total full text requires expensive extraction, use a reproducible stratified measurement first; do not pretend sample estimates are exact whole-estate values.

## Acceptance

The census operation itself is proven read-only, and every mismatch direction has a typed disposition.

## No-go

No receipt deletion, no blind re-ingest, no corpus reset just to make counts equal.

---

# 6. F3 — corpus completeness + excerpt collapse repair

## Trigger\n\nProceed if current `catalog - corpus` is non-zero, the excerpt collapse is reproduced, or F2 proves that corpus IDs exist but usable body/text health is materially degraded.

## Implementation

Build the bounded self-quiescing missing-row repair the 2026-08-19 handoff already recommended.

Candidate algorithm:

```text
missing_ids = catalog_ids - corpus_ids\nbroken_body_ids = evidence_backed_body_health_candidates\n\nfor id in bounded deterministic batch over missing_ids + broken_body_ids:\n    load catalog identity\n    strict-read canonical research_vault/<id>.pdf\n    verify nonempty source bytes + PDF hash\n    canonical extract\n    insert missing row OR repair only the proven-broken body/facts\ncommit local DB\nverify pre/post ID + body-health distributions\npublish through incumbent corpus publication owner\nreport repaired/failed/remaining
```

A repaired row must leave the candidate set.

## Important distinction

The committed public excerpt snapshot is **not** the corpus authority. It is a public derivative and collapse guard.

Repair corpus first, then recompute excerpts.

## Acceptance

- current live census shows the intended searchable population restored or every excluded ID is typed (scan/no text/rights/known exclusion);\n- body-health census shows no unexplained body collapse even when ID sets match;\n- excerpt snapshot regeneration no longer collapses unexpectedly;
- search finds a seeded restored document;
- no catalog/PDF/receipt regression;
- hourly runtime remains within an accepted bounded operating shape or backfill is moved to an explicit operator process rather than hiding unbounded work inside the hourly job.

---

# 7. F4 — upstream source freshness repair

## Outcome

New institutional reports advance again, or an explicit upstream outage is truthfully documented.

## Diagnose from producer outward

```text
source acquisition process
 -> local producer output
 -> R2 research_inbox PDF/sidecar
 -> ingest listing
 -> admission
```

Check where the latest new source actually stops.

## Acceptance

A genuinely new post-2026-09-24 report moves through:

```text
producer
 -> inbox
 -> canonical PDF
 -> catalog
 -> corpus/full text
 -> receipt
```

and source freshness returns inside the existing guard without changing the guard merely to pass.

If the source is intentionally unavailable, product/model status must expose that typed outage.

---

# 8. F5 — canonical full-text artifact and segment map

## Outcome

Every eligible canonical PDF has a versioned full-text derivative that can support exact tail retrieval.

## Proposed artifacts

`research_vault.extracted_text.v1`

`research_vault.segment.v1`

See architecture freeze for fields.

## Physical placement

Use the incumbent private Research Vault store/prefix family. Do not create a new bucket because text is "AI data."

Exact object paths should be chosen by the Research Vault owner after collision check; identity must be content/revision bound, not mutable-title bound.

## Extraction qualification

Test:

- normal born-digital PDF;
- two-column layout;
- sparse cover;
- very long 100+ page report;
- Unicode;
- form-feed/page separation;
- malformed PDF;
- scan/no text;
- same source bytes rerun;
- corrected PDF same logical report ID.

## Segmentation qualification

Test exact replay from UTF-8 byte offsets and page locators.

## Acceptance

A tail sentence past the old 60,000-char boundary can be addressed and replayed exactly.

---

# 9. F6 — derived metadata / exact identity enrichment

## Outcome

Useful search facets without corrupting source claims.

## Inputs

- source catalog fields;
- title/summary/full text;
- `engine/entity_resolver.py` candidate methods;
- Data OS `VendorAliasTable`;
- existing institution canonicalizer;
- optionally deterministic taxonomy/topic rules;
- later RIO-derived topics with explicit epistemic layer.

## Output

A derived metadata projection keyed to exact source/text revision.

## Validation

Construct a labeled sample across:

- explicit `$TICKER`;
- title `Company (TICKER)`;
- company name only;
- macro note with ticker-like acronyms;
- multi-company sector report;
- non-US/security aliases;
- renamed/reused ticker;
- ambiguous company name.

Measure precision/abstention. Do not optimize recall by weakening exact identity law.

## Acceptance

Ticker/security filters operate over provenance-bearing resolved identities, and unresolved/ambiguous reports remain searchable by text rather than silently mis-tagged.

---

# 10. F7 — canonical full-tail retrieval

## Outcome

Research Vault search operates over full eligible text, not only the 60k prefix.

## Steps

1. Measure physical index footprint.
2. Select monolithic/persistent/sharded physical form.
3. Extend canonical search service.
4. Preserve title/summary/institution weighting unless benchmark shows a better deterministic ranking.
5. Add metadata filters.
6. Keep existing public-safe catalog gates.
7. Return coverage/currentness.

## Acceptance

Fixed benchmark includes tail-only questions where the relevant phrase is beyond 60k; Recall@K materially improves and exact evidence replay succeeds.

No consumer sees shards/index paths.

---

# 11. F8 — RIO structural correctness salvage

## Source

PR #7461 at `cb844c90d162077e5518061d9932af93a914cda9`.

## Action

Port the small fail-closed malformed-claim validation onto current main after checking current schema movement.

Do not cherry-pick an ancient branch blindly.

## Acceptance

A malformed/blank claim cannot shift support indices to a different surviving claim.

Mutation/adversarial tests prove the failure mode.

---

# 12. F9 — RIO deep-read producer salvage

## Source

Unique useful concepts/code from PR #7354, especially:

- `vault_head.py`;
- one-shot operator;
- focused tests.

## Required adaptation

- use current W2 store already on main;
- use explicit `source_pdf_sha256` + `extracted_text_sha256`;
- consume canonical full-text artifact if available, rather than re-running extraction per model request;
- preserve deterministic triage selection;
- preserve idempotent "already current";
- preserve `EFFECT_UNKNOWN` stop semantics;
- preserve bounded head size.

## Acceptance

Real private report:

```text
canonical source
 -> full text
 -> W1 grounded RIO
 -> W2 persist
 -> readback
 -> identical rerun
 -> zero duplicate model call
```

plus one corrected-source test.

---

# 13. F10 — canonical Research Read port

## Owner

Research/Qualitative service boundary in Macro.

## Required operations

```text
status
search
fetch
find_evidence
```

## Key principle

Brain and MCP call this same semantic owner.

Do not make the first implementation a network API solely to satisfy MCP. A pure/service interface is fine if the MCP runtime is colocated or has a governed internal client.

## Tests

- same query through Brain adapter and MCP adapter gets same source candidates/coverage semantics;
- entitlement difference is server-context driven;
- evidence result is literal;
- RIO absent cannot change evidence into success;
- stale producer state visible.

---

# 14. F11 — Brain convergence

## Source evidence

PR #7522 contains a useful rights-safe RIO consumer prototype.

## Preferred target

Refactor the relevant Brain report/evidence behavior to consume the canonical Research Read port.

Do not simply copy #7522's direct store reads if the shared port now owns currentness/visibility.

## Acceptance

Generic report intent may include a rights-safe RIO summary.

Specific evidence intent is grounded in literal evidence passage(s).

No-evidence remains no-evidence.

---

# 15. F12 — authenticated Research MCP

## Suggested protected-repo source family

A new bounded domain integration adjacent to existing MCP integrations, after cross-repo owner review.

Likely shape:

```text
schemas/contracts
adapter/read port client
server (only module importing MCP SDK, where house pattern calls for it)
service/deployment composition using existing auth owners
tests
runbook
```

The exact repo placement must follow the current protected integration owner; do not duplicate auth code into Macro just because Vault code lives there.

## External tools

- `research_status`
- `research_search`
- `research_fetch`
- `research_find_evidence`

## Acceptance

MCP Inspector / protocol tests prove:

- exact tool census;
- closed schemas;
- read-only annotations;
- auth challenge/linking behavior;
- invalid input bounds;
- output bounds;
- no generic store/root arguments;
- sanitized failure;
- no write operation.

---

# 16. F13 — private ChatGPT canary

## Transport

Use current OpenAI Secure MCP Tunnel for the private/developer-mode canary unless current source/owner proves a better accepted private route.

Do not open a public Research Vault listener merely for this test.

## Real user task

Use an actual institutional-research question requiring multiple reports and at least one tail evidence item.

## Acceptance

A new authorized ChatGPT session:

- discovers the four tools;
- authenticates/links;
- searches;
- fetches;
- finds literal evidence;
- sees coverage/freshness;
- synthesizes without manual PDF upload.

Also run denied/non-entitled path.

---

# 17. F14 — Deep Research canary

Suggested case:

> Reconstruct when the optical-networking / datacenter-photonics thesis became discoverable. Use internal institutional research and public external evidence, identify earliest changes in demand/earnings expectations, and separate internal licensed evidence from public evidence.

## Acceptance

Deep Research actually invokes the internal Research tools for read/fetch, uses external sources independently, and keeps provenance classes distinct.

No manually uploaded PDF stands in for the connector.

---

# 18. F15 — retrieval/rights evaluation

Run the fixed benchmark described in `04_ACCEPTANCE_SECURITY_AND_EVAL.md`.

This gate decides:

- whether lexical/facet retrieval is sufficient;
- whether semantic index work is justified;
- whether context/latency budgets are acceptable;
- whether rights projections are safe;
- whether source currentness/revision behavior is honest.

Do not self-promote from unit tests.

---

# 19. F16 — W5 longitudinal intelligence

Only after metadata identity and current RIO coverage are usable.

Salvage #8090's exact predecessor selector.

Then build grounded delta comparison as a new bounded derivative rather than weakening predecessor identity.

---

# 20. F17 — semantic/vector index, conditional

Entry gate:

A fixed benchmark shows a named retrieval failure class that lexical/facet/alias/RIO retrieval does not meet.

If admitted:

- use source-bound segments;
- pin embedding model/version;
- store as derivative;
- no vector result without literal evidence resolution;
- measure incremental recall/cost/latency;
- preserve lexical fallback.

If no material improvement, reject the component.

---

# 21. Parallelization policy

Safe early parallel lanes after F0:

```text
F1 private storage hardening
F4 producer diagnosis (read-only portion)
F6 metadata research/benchmark design
F8 RIO claim-index salvage
MCP protected-owner architecture census
retrieval benchmark fixture construction
```

Do not parallel-write:

- `r2_store.py` from multiple lanes;
- `corpus.py/ingest.py` from multiple repair lanes;
- `brain_market_intel.py` while F10 semantic contract is still being rewritten;
- the same stale PR salvage paths from separate agents.

One principal integrates before widening the next interface.

---

# 22. Worker return contract

Every bounded child returns:

```text
source pin
paths changed/read
capability delta
tests/checks actually run
real-path proof or absence
known effect state
unresolveds
what must not be redone
exact next dependency
```

"Implemented" without source identity and evidence is not a usable return.

---

# 23. Program continuation rule

After each accepted package:

```text
integrate
 -> verify against parent journey
 -> persist concise delta
 -> select next critical dependency
 -> continue
```

A clean package boundary is not a program stop while another safe dependency is ready.
