# 04 — Acceptance, security and continuation

**Purpose:** define what evidence is sufficient to call each layer complete, how failures are represented, and how a future Fable session resumes without redoing the census.

## 0. Acceptance principle

This program has four distinct acceptance domains:

1. **source/storage truth** — are the documents private, current and internally consistent?
2. **intelligence truth** — are literal evidence and model-derived research context grounded and correction-safe?
3. **transport/security truth** — can an authorized client read only what it should, through a bounded MCP contract?
4. **product truth** — does the real intended ChatGPT/Deep Research workflow materially improve research without hidden source/rights/coverage failure?

A green result in one domain does not prove the others.

## 1. Program DONE_WHEN

All required gates below are PASS or an explicitly accepted product-scoped limitation.

### G1 — private storage safety

- Research Vault private production store cannot silently fall back to shared/public R2.
- Explicit dedicated configuration is required.
- Tests prove missing/partial/shared destination refusal.
- No model/tool parameter can select the store.
- Research Intelligence persistence uses the same safe private store owner.

### G2 — live Vault integrity

- live catalog/PDF/corpus/receipt identity sets are measured;
- unexplained set differences are zero or typed with a documented owner/repair;
- current corpus restore identity/size is proven;
- the 1,497 -> 351 excerpt-collapse event is explained;
- no known partial corpus is promoted as healthy.

### G3 — source freshness truth

- source producer health is understood;
- newest source clock is surfaced to consumers;
- stale producer state remains typed;
- a healthy publication timestamp alone cannot make source_status healthy.

A known producer outage can be an accepted degraded state for historical queries only if the product visibly discloses it.

### G4 — full-document retrieval

- at least one real/representative fact beyond the old 60,000-character prefix is searchable;
- the old prefix path demonstrably misses the fact;
- the new path finds the correct document;
- evidence fetch returns the exact source text;
- receipt replay succeeds;
- page range is claimed only where proven.

### G5 — source correction

For a source revision/correction:

- source_content_sha256 changes;
- old text/segments/evidence index become stale or non-current;
- old RIO becomes stale;
- optional derived metadata/embeddings become stale;
- new derivative can be generated;
- historical old evidence is not silently rewritten away.

### G6 — RIO structural correctness

- claim support identity cannot shift through malformed rows;
- all source claims remain exact evidence-grounded;
- derived thesis/assumptions/etc point to valid claim identities;
- invalid model output fails typed;
- broad RIO producer does not proceed on the known #7461 failure mode.

### G7 — RIO producer currentness/cost

For a real Vault report:

- canonical source retrieved;
- full source body/text identity proven;
- W1 RIO generated;
- W2 strict persistence succeeds;
- readback succeeds;
- exact rerun triggers zero duplicate model call;
- correction names exact predecessor;
- EFFECT_UNKNOWN stops dependent writes.

### G8 — Brain consumer

Brain generic report path:

- current RIO -> bounded rights-safe derived context;
- missing RIO -> explicit missing;
- stale RIO -> explicit stale;
- invalid RIO -> explicit invalid;
- unavailable store/body -> explicit unavailable.

Brain evidence query:

- literal evidence from source owner;
- RIO may add state only;
- no literal-evidence substitution.

### G9 — canonical Research Read Service

One service/contract provides:

- status;
- search;
- fetch;
- evidence.

Both Brain and MCP consume it or share its exact domain-layer functions without duplicated retrieval policy.

### G10 — MCP security

- exactly four read tools in MVP;
- schemas closed and bounded;
- read-only/idempotent annotations correct;
- principal/rights not accepted from model arguments;
- auth resource/scope/channel verified according to selected profile;
- entitlement owner enforced;
- invalid/oversized input refused;
- error payloads sanitized;
- no generic file/object/SQL tool;
- no R2 key/bucket/secret leakage.

### G11 — authorized ChatGPT canary

On the real intended ChatGPT surface:

- exact app/server generation known;
- research_status succeeds;
- search succeeds;
- fetch succeeds;
- evidence succeeds;
- answer uses the retrieved evidence correctly;
- source freshness/coverage shown;
- no manual PDF upload;
- no unbounded source reproduction.

### G12 — denied canary

At least one intentionally denied identity/state:

- gets correct typed refusal;
- receives no private report body;
- receives no private RIO;
- receives no storage locator;
- receives no internal error/credential;
- cannot infer another principal's entitlement via side channel beyond accepted public metadata.

### G13 — Deep Research canary

On real Deep Research:

- Research app used through supported read/fetch actions;
- Vault evidence and public web evidence kept distinct;
- exact Vault provenance retained;
- no manual PDF upload;
- no claim that Agent mode uses the app.

### G14 — retrieval benchmark

A frozen benchmark reports:

- Recall@K;
- evidence hit/replay rate;
- tail recall;
- false-source/citation rate;
- coverage-state correctness;
- p50/p95 latency;
- response/context bytes;
- model/RIO cost where relevant.

The benchmark covers long-tail institutions and long reports, not only Goldman/short documents.

### G15 — release/rollout truth

Separately proven:

- source merge;
- deployment;
- app creation/publication where applicable;
- account/workspace connection;
- tool snapshot;
- successful authorized calls;
- denied calls;
- product acceptance.

No “shipped” shorthand hides missing steps.

## 2. Security acceptance matrix

| Threat | Required control | Required evidence |
|---|---|---|
| private research published to shared/public R2 | dedicated private config; shared/public refusal | hermetic tests + deployment config/readback |
| model chooses storage target | no storage fields in tool schemas | schema census |
| unauthorized report body access | auth + entitlement before private read | denied integration test |
| RIO leaks private claim text | exact rights-safe projection whitelist | projection tests + payload inspection |
| stale RIO treated current | exact source-content SHA match | correction/stale test |
| corpus partial but search answers normally | typed corpus health status; fail/degrade honestly | synthetic degraded corpus + live health |
| stale producer hidden by fresh catalog | separate source clock | source_status test |
| source prompt injection grants authority | content treated as data; no content-derived grants | injection fixture |
| MCP error leaks path/token | sanitized error envelope | forced dependency failures |
| output too large / model source dump | response budgets + evidence limits | oversize tests |
| cross-user quota/entitlement confusion | verified principal and canonical entitlement | two-principal test where product profile supports it |
| app tool expansion unnoticed | tool snapshot/digest and app publication generation | deployment receipt |

## 3. Rights acceptance

Third-party research rights are not solved by technical access control alone.

Before broad rollout confirm with the existing operator/product/legal owner:

- which accounts/workspaces may receive full private research context;
- permitted amount of verbatim text in model-visible evidence;
- whether derived summaries may be displayed externally;
- whether customer access should inherit existing Pro-only report rules;
- retention/logging rules for licensed source text;
- whether Deep Research output can reproduce literal source text beyond current bounds.

Technical default until that decision changes:

- source remains private;
- evidence is bounded;
- derived projection does not expose private claim text;
- content is attributed;
- no transformation is assumed to widen rights.

## 4. Retrieval benchmark contract

### Corpus

Freeze a versioned benchmark set with report IDs/source hashes.

Stratify:

- institution: top-volume / medium / small;
- report length: <=10 pages / 11–30 / 31–60 / >60;
- type: single-company / sector / macro / flow / multi-topic;
- text state: full / thin / scan if present;
- age: recent / older archive.

### Query classes

1. exact source phrase;
2. natural paraphrase;
3. company/ticker;
4. institution/date;
5. theme/subtheme;
6. number/forecast;
7. causal thesis;
8. tail-page fact;
9. negative query with no relevant evidence;
10. cross-report chronology.

### Ground truth

Human-verified or deterministic exact target evidence with:

- expected report(s);
- expected source span(s);
- source hash;
- question class.

Do not use the same LLM's answer as both retriever and ground truth.

### Metrics and provisional target framing

Fable must freeze exact numeric thresholds after observing benchmark difficulty, but the following qualitative bars are binding:

- tail retrieval must be materially better than current 60k-only baseline;
- exact-evidence replay should be effectively perfect for byte-replayed passages;
- false attribution/citation must be near-zero and investigated individually;
- source/coverage state must not be falsely upgraded;
- latency must fit an interactive research workflow without whole-archive model context.

Do not tune thresholds after seeing one preferred architecture win.

## 5. Metadata-enrichment acceptance

A derived facet must not become a tool filter without:

- provenance: source vs deterministic vs model-derived;
- version;
- source hash;
- coverage;
- precision estimate;
- known failure cases;
- correction behavior;
- canonical ID resolution;
- abstention.

For ticker/security identity specifically:

- ticker string alone is not historical security identity;
- current aliases must not be backfilled across ticker reuse/rename windows where point-in-time identity matters;
- when exact security identity is unavailable, preserve abstention or lexical match.

## 6. RIO acceptance levels

Use explicit levels:

### RIO-L0 — schema source exists

Code/schema present. No live claim.

### RIO-L1 — hermetic grounding proof

Fixtures prove exact source claim grounding and invalid-output behavior.

### RIO-L2 — private persistence proof

Exact source -> analysis -> immutable artifact -> pointer/readback with correction semantics.

### RIO-L3 — live Vault producer proof

A real admitted Vault report successfully runs through current producer and persistence.

### RIO-L4 — live model consumer proof

Brain / Research Read Service consumes only current rights-safe projection and keeps literal evidence separate.

### RIO-L5 — production research workflow proof

Real ChatGPT/Deep Research benefits from RIO context while source citations remain exact.

Do not call L2 “product integration.”

## 7. MCP/app acceptance levels

### MCP-L0

schemas/source only.

### MCP-L1

hermetic server invocation.

### MCP-L2

deployed server/transport reachable.

### MCP-L3

auth policy/channel accepted.

### MCP-L4

app connected and tools discovered.

### MCP-L5

authorized call proven.

### MCP-L6

denied path proven.

### MCP-L7

real research journey accepted.

This vocabulary is documentation-only and must not become a second lifecycle database.

## 8. Typed operational states

Consumer-facing/domain states should be small and stable.

Recommended families:

### Source health

- SOURCE_FRESH
- SOURCE_PRODUCER_STALE
- SOURCE_CLOCK_INVALID
- SOURCE_UNAVAILABLE

### Corpus health

- CORPUS_HEALTHY
- CORPUS_PARTIAL
- CORPUS_UNAVAILABLE
- CORPUS_GENERATION_MISMATCH

### Text coverage

- FULL_TEXT
- PREFIX_ONLY
- THIN_TEXT
- NO_TEXT_LAYER
- TEXT_UNAVAILABLE

### Evidence

- EVIDENCE_OK
- EVIDENCE_NOT_FOUND
- EVIDENCE_PARTIAL_COVERAGE
- EVIDENCE_UNREPLAYABLE_ADDRESS_ONLY

### RIO

- RIO_AVAILABLE
- RIO_MISSING
- RIO_STALE
- RIO_INVALID
- RIO_UNAVAILABLE

### Auth/rights

- AUTHENTICATION_REQUIRED
- INSUFFICIENT_SCOPE
- NOT_ENTITLED

Do not create dozens of states for every internal exception. Internal diagnostics can be richer than model/client envelopes.

## 9. Failure/effect law

### Read failures

Fail soft only when the caller can still distinguish:

- empty legitimate result;
- dependency unavailable;
- stale source;
- partial coverage.

An empty array with “available=true” is not an acceptable representation of a dead corpus.

### Write failures

For private-store/RIO/index mutations:

- record operation identity;
- distinguish refused-before-effect from failure-after-dispatch;
- EFFECT_UNKNOWN freezes dependent replay;
- inspect original target before retry;
- no alternate account/tool/carrier retry to escape uncertainty.

### Batch failures

One bad report may fail independently where existing ingestion law allows it.

A systemic tool/store failure should abort the affected batch rather than producing thousands of misleading partial artifacts.

## 10. Rollback expectations

### R2 safety change

Rollback must not re-enable unsafe shared fallback. If the new dedicated private configuration is unavailable, safer state is private R2 unavailable, not public fallback.

### Full-text index

Keep current prefix corpus readable until the replacement proves parity/acceptance. Do not destructively migrate the only working search artifact.

### RIO

Old immutable artifacts stay addressable; latest pointer/correction semantics choose current. Rollback means consumer stops using new projection, not delete history.

### MCP/app

A canary can be disconnected/unpublished/disabled without changing Vault source truth. Transport rollback must not mutate the research corpus.

## 11. Performance acceptance

Measure separately:

- source ingest;
- corpus/index build;
- search p50/p95;
- evidence fetch p50/p95;
- MCP overhead;
- model synthesis.

Do not “optimize” by:

- widening report body returned to model;
- caching across source corrections without identity;
- skipping auth/currentness checks;
- omitting health states.

Target architecture should reduce frontier context even if deterministic retrieval does modest extra work.

## 12. Cost acceptance

Report:

- model calls per analyzed report;
- cache hit/currentness rate;
- RIO spend by requested model;
- embedding cost if admitted;
- storage growth;
- R2 transfer growth;
- context bytes per final research answer.

A successful design should make repeated research cheaper through durable exact derivatives, not by downgrading source grounding.

## 13. Current publication ledger

### FACTS at publication

- Mastermind protected source observed at 03f7ca04cd5b0a3abf7166221dd77d403c7f95df.
- Macro main used as branch base: 1b4edfb438f7ff7edca5097f0c90243a49207d1e.
- Catalog count: 2,778.
- Latest admitted report: 2026-09-24T09:28:05Z.
- Completed research-ingest run 37158653683: FAILURE due PRODUCER_STALE.
- Same run: excerpt derivation collapse 1,497 -> 351, write refused.
- Current catalog ticker coverage: 0 / 2,778.
- Current search body cap: 60,000 chars.
- Current Brain report body cap: 12,000 chars.
- #7461/#7354/#7522/#8090 open and unmerged at census time.
- Current Research Vault R2 client still contains shared-env fallback.
- Research Intelligence W2 private persistence and rights-safe projection already exist.
- Mastermind protected repo already contains reusable MCP/auth implementations.

### DECIDED by this masterplan

- P0 Vault truth precedes connector exposure.
- No duplicate Vault/RIO/auth/retrieval owner.
- Full-tail retrieval is required.
- Metadata enrichment is separate/provenance-bearing.
- Four-tool read-only MCP MVP.
- Exact source evidence remains citation authority.
- RIO remains derived context.
- Deployment transport selected at a current-state gate.
- Internal authorized canary precedes broad product rollout.
- Embeddings are conditional on benchmark evidence.

### OPEN for Fable

- exact current root cause of producer staleness;
- exact current root cause of corpus/excerpt collapse;
- current custody/releasability of held PRs;
- physical full-text index architecture after measurement;
- metadata enrichment algorithms/thresholds;
- first canary deployment profile;
- exact rights/verbatim limits for target app/workspace;
- numeric benchmark thresholds after benchmark design.

## 14. DO_NOT_REDO

Unless relevant evidence changes:

- the architectural census in README/01;
- the conclusion that R2 is storage, not API;
- the conclusion that current ticker metadata is absent;
- the existence of prefix truncation;
- W2 Research Intelligence persistence architecture;
- rights-safe projection design;
- source_span receipt primitive;
- MCP/auth foundation;
- held-PR code from memory;
- source freshness guard semantics.

Rechecking current state is not “redo.” Rebuilding an already-owned subsystem without falsifying evidence is.

## 15. Continuation record for receiving Fable

### Read order

1. README
2. 00 assignment
3. 01 census
4. 02 masterplan
5. 03 work packages
6. this section

### First action

Re-pin current protected Mastermind and current Macro main, then compare:

- this branch base;
- open PR heads;
- latest research-ingest state.

### Next decision

If no new source materially invalidates this plan, begin F0 then P0 packages S1/V1/U1/R1.

### Do not start with

- MCP coding;
- vector DB research;
- mass RIO backfill;
- plugin packaging;
- longitudinal belief features;
- Terminal/UI work.

Those all sit downstream of source truth.

## 16. Final product acceptance scenario

The strongest compact program proof should look like this:

1. Source health reports either fresh or an explicit known degraded producer state.
2. A user asks a hard institutional research question.
3. Search finds several relevant reports across institutions.
4. At least one key evidence passage lies beyond the old 60k prefix.
5. Evidence is returned with exact source hash/segment/page/byte receipt.
6. A current RIO adds a derived thesis/falsifier summary without exposing private claim text as source.
7. The answer synthesizes across reports and public evidence.
8. A source correction is introduced in a controlled test and old derivative state becomes stale.
9. A denied principal cannot retrieve private content.
10. The same research app participates in a Deep Research run without manual PDF upload.
11. Benchmark and telemetry show the system did not solve the problem by sending whole PDFs to the model.

When all eleven are proven under the declared rights boundary, the Research Vault has become a genuine institutional intelligence fabric rather than a file repository with an MCP wrapper.
