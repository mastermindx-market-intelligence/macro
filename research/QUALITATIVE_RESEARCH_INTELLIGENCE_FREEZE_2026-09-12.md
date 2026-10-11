# Qualitative Research Intelligence — Architecture Freeze

**Date:** 2026-09-12
**Owner:** Qualitative Intelligence program
**Status:** frozen for bounded vertical implementation; no trading authority

## Outcome

Mastermind should not merely summarize institutional notes or fast qualitative articles. It should retain what each source actually claims, the evidence for those claims, the source's causal thesis, assumptions, forecasts, catalysts, falsifiers and implications, then synthesize disagreement and change over time without confusing model inference with source fact.

The primary machine job is:

`lawful source body -> grounded source claims -> supported analysis -> cross-source context -> Neural Web consumer`

The primary user job is to ask what high-quality sources believe, why they believe it, what changed, where they disagree, what would falsify the thesis, and how that qualitative state relates to Mastermind's quantitative evidence.

## Canonical ownership

This capability extends the **existing `qualitative-intelligence` program**. It is not a new intelligence program or state plane.

- **Research Vault** owns institutional report identity, private PDF/body, catalog/corpus, search, entitlements and report opening.
- **qkernel/qbus** remain the canonical qualitative item/event identity and event-context substrate.
- **`qual_extraction.v1`** remains the canonical verbatim-quote verification machinery for body-bearing LLM extraction.
- **qledger / Eval OS** remain the only path by which a qualitative claim can earn measured predictive authority.
- **Neural Web** may consume descriptive projections; consumption transfers no score, rank, gate, sizing or trade authority.
- **Research Factory** may receive explicitly commissioned hypotheses derived from research; it does not own source-document identity or RIO lifecycle.

## What exists versus what is missing

The source side is already mature. MarketDesk discovery, quota-aware prioritization, authenticated PDF retrieval, Markdown/PDF archival and Research Vault publication are real capabilities. Research Vault supplies catalog/search/body retrieval. qbus/qkernel/qledger and `qual_extraction.v1` already establish the qualitative evidence, event, citation and evaluation laws.

The missing layer is **long-form document understanding**. Existing `summary_points` are useful browse metadata; Brain full-body access is retrieval. Neither persists a grounded reconstruction of an important paper's thesis and causal mechanism or makes institutional view changes recoverable across sessions.

Capability ledger at this freeze:

- institutional acquisition/publication: `PROVEN_LIVE`
- Research Vault catalog/search/body access: `PROVEN_LIVE` with neighboring repair/retrieval PRs still active
- qualitative qbus/qledger substrate: `PROVEN_LIVE` / operating owner
- citation-verified event extraction: built and used on body-bearing lanes
- long-form Research Intelligence Object: `BUILT_NOT_PROVEN` in the current bounded wave
- durable per-document RIO persistence: `NOT_BUILT`
- longitudinal institution belief memory: `NOT_BUILT`
- ZeroHedge long-form research adapter: `NOT_BUILT`
- cross-document research synthesis clusters: `NOT_BUILT`

## Research Intelligence Object v1

RIO is a **private derived enrichment** keyed to an existing source identity and exact body hash. It is not another document, event, corpus or search authority.

The contract separates two epistemic layers:

1. `claims[]` — source-attributed claims. Each surviving claim requires at least one short verbatim `quote_span` verified against the source body by the existing `qual_extraction` citation machinery.
2. `analysis` — model synthesis. Thesis, assumptions, forecasts, catalysts, falsifiers, counterarguments, implications and belief/consensus relationships must reference `support_claim_indices`; unsupported synthesis is dropped or fails closed.

Numbers are retained only when they occur inside a verified evidence span. Document identity and content hash are caller-owned and must match exactly; model output cannot rewrite them. `authority` is forced to `descriptive_research_only`.

## Storage and correction freeze

RIO detail derived from licensed institutional research remains in the existing **private Research Vault object store**. This is a rights boundary, not a competing qualitative store.

Persistence must use the existing `StrictConditionalWriteStore` primitives:

- immutable, versioned artifact bytes containing exact report id, source content hash, RIO, serving provider/model, requested model and prompt fingerprints;
- content-addressed or analysis-identity-addressed immutable keys;
- exact-byte readback on uncertain immutable writes;
- one bounded CAS `latest` projection per report, committed last;
- no overwrite of an immutable artifact;
- no blind retry after an ambiguous write;
- no stale pointer rewind;
- corrected/re-extracted source content produces a new immutable artifact while prior versions remain inspectable.

qbus stays the qualitative item/event store. It may receive a bounded metadata projection or reference for lawful cross-source clustering, but private institutional claim text is not copied into public/committed qbus artifacts merely for convenience.

## Source adapters

### Institutional research

Use the existing MarketDesk -> Research Vault producer. Deterministic triage decides which reports deserve expensive reading. RIO consumes the existing report id and existing body/Markdown; it does not redownload, recatalog, or invent a second queue.

### ZeroHedge

ZeroHedge already has a canonical source identity and publisher RSS lane. Long-form research treatment therefore begins from that existing identity. A later adapter may acquire lawful article body content, classify it as `qualitative_article`, run the same grounded RIO contract, and project safe event metadata into qbus. It must not create another RSS watcher or duplicate news lifecycle.

Institutional and ZeroHedge claims may cluster around the same topic while preserving source class, source name, timestamp, evidence and explicit-vs-derived semantics. Cross-source synthesis never erases provenance.

## Model architecture

Do not replace local Qwen wholesale and do not bind research understanding to one subscription vendor.

The intended cascade is:

1. deterministic parser/normalizer on every document;
2. economical/local model for broad structured extraction and pre-screening where quality is adequate;
3. stronger model for the deterministically ranked important head;
4. strongest reasoning tier for the small set requiring cross-document synthesis or reconciliation with quantitative Mastermind context.

All serving goes through the existing provider/routing surface. The extraction receipt records both requested and actually served model, because provider fallback is not provenance-preserving unless the serving model is explicit.

Model promotion is empirical. A frozen real-corpus benchmark scores numerical fidelity, key-claim recall, quote grounding, causal reconstruction, assumption/falsifier quality, cross-document synthesis, hallucination, latency and effective cost. Qwen, GLM, Alibaba-accessible models, MiniMax/Kimi and frontier models compete on the same schema. Interactive coding-plan credentials are not treated as unattended backend licenses.

## Authority and learning

RIO is cognition context. It does not originate a score, rank, forecast authority, portfolio gate, size or trade.

If a future RIO-derived proposition is meant to earn predictive authority, it becomes an explicit registered qledger/Eval-OS claim with point-in-time source identity, horizon, falsifier/control and forward outcome. It then follows the existing display -> shadow -> confirmer/scored promotion law. A model's conviction wording is never a substitute for this process.

## Bounded implementation waves

**W1 — grounded RIO contract.** Real report body -> canonical identity -> quote-verified source claims -> claim-supported analysis -> deterministic summary/claim projections. Stop before persistence or product wiring.

**W2 — private durable RIO.** Persist a versioned RIO beside the canonical Research Vault identity using existing strict object-store semantics; ship a real read consumer/CLI and prove correction/idempotency behavior.

**W3 — Research Vault/Brain consumer.** After neighboring ownership collisions clear, make an existing report/Brain path consume the latest lawful RIO with explicit degraded states; no second search/corpus.

**W4 — ZeroHedge qualitative adapter.** Existing ZeroHedge source identity -> lawful body acquisition -> same RIO contract -> safe qbus metadata projection -> one real cross-source topic cluster with provenance intact.

**W5 — longitudinal belief memory.** Compare successive source documents by institution/desk/topic and persist explicit prior-view/current-view deltas grounded in their respective RIO claims.

**W6 — research synthesis clusters.** Synthesize consensus, dissent, changing assumptions, mechanisms, catalysts and falsifiers across documents; every synthesis edge retains source/claim support.

**W7 — Neural Web and quantitative reconciliation.** Expose descriptive research context to the existing Neural Web/Brain and explicitly label which qualitative theses are corroborated, contradicted or not measurable by current quantitative state.

**W8 — prospective learning.** Register only deliberately selected, falsifiable research propositions into the existing evaluation substrate; measure institution/topic track records and lead/lag without retroactively granting authority.

## No-rebuild boundaries

Do not create a second Research Vault, corpus, FTS/vector service, qbus, qledger, entity resolver, model router, lifecycle, queue, retry plane, correction plane, graph authority or source identity system.

Do not publish proprietary note bodies or detailed quote evidence to public surfaces. Do not let ZeroHedge or an institutional source's brand imply factual authority merely because it is represented in the system.

Do not call schema/ingestion infrastructure completion. The program is complete only when real documents create grounded understanding, users/Brain can consume it, source changes are recoverable, cross-source synthesis is useful, and any claimed predictive value has prospective evidence.

## W1 acceptance boundary

W1 may be accepted as `BUILT_NOT_PROVEN` only when the exact semantic head passes its wired tests and hosted gates, citation grounding is inherited from the existing qualitative owner rather than reimplemented, model/document provenance is exact under fallback, and the changed-path set remains collision-safe.

W1 does **not** make durable RIO storage, Brain consumption, ZeroHedge deep reading, clustering, Neural Web context, predictive learning or production proof true. Those are separate observable waves above.
