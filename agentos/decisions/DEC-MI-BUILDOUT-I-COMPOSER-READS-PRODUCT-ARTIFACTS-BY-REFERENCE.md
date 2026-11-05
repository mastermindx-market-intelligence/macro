---
key: MI-BUILDOUT-I-COMPOSER-READS-PRODUCT-ARTIFACTS-BY-REFERENCE
question: >
  I1 §8 Q9 (Mastermind #1258 package I): may the integrated-answer composer read the rendered
  product artifacts site/basketdata/baskets.json and site/neuralwebdata/theme_state.json before
  an Agent OS owner is recorded for those paths?
answer: >
  Yes, by reference only. The composer may load both artifacts by route with as_of and a
  content hash, must surface stale or absent data as a refused leg, may never copy rows into a
  second warehouse, and must record itself as a consumer in the workstream record so an owner
  can later be named.
rationale: >
  Both files are rendered PRODUCT artifacts, which is exactly what chat and composer context is
  allowed to read (CXI-R23: product artifacts, never repo internals). The L3 leadership receipt
  (#8519, engine/leadership_receipt.py) already consumes theme_state.json the same way — a
  freshness ceiling (_THEME_STATE_MAX_AGE_DAYS = 5) and an honest unavailable state — so the
  pattern has a merged precedent on this program. Waiting for an owner record before reading a
  served JSON would block composition on paperwork while the artifact is already public.
alternatives:
  - option: Wait until an Agent OS workstream claims site/basketdata/ and site/neuralwebdata/.
    why_not: Ownership of a served artifact is a knowledge-plane fact, not a permission; Agent OS is never a control plane (invariant I1), so the absence of a record cannot gate a read.
  - option: Snapshot the two JSON files into a composer-owned table.
    why_not: That is the second canonical warehouse the package forbids; it would drift from the nightly producer and hide staleness.
evidence:
  - "engine/leadership_receipt.py on PR #8519 head 0a59999b: _THEME_STATE_MAX_AGE_DAYS = 5 (line 9), _load_theme_state_payload reads site/neuralwebdata/theme_state.json (lines 78-81), stale/absent -> unavailable block"
  - "research/product_intelligence_local_delivery/I1_INTEGRATED_ANSWER_COMPOSITION_SPEC_2026-10-06.md (merged #8517 f1cd5d9cbd5f): consumption law (route + as_of + hash), §8 Q9"
  - "CLAUDE.md §Neural Web + Mastermind chat: chat context reads product artifacts only, never repo internals (CXI-R23)"
affects:
  - WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
  - WS:GMI-THEME-GRAPH
  - site/basketdata/**
  - site/neuralwebdata/**
confidence: high
reversibility: easy
decided_by: "session fd47d431 (Fable Meta-CEO seat, Chairman handoff 2026-10-05 on Mastermind #1258)"
decided_at: 2026-10-06
---

If a workstream later mints an owner for either path with a different contract, the composer
adopts that contract; this record does not pre-empt it.
