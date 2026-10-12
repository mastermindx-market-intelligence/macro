---
key: NEWS-IMPACT-PHASE0-FREEZE
question: >
  Which template set, shared definitions and boundary rules does the Prophet
  news-to-business-impact program freeze at Phase 0, and how are the four
  owner-contract conflicts found in review resolved?
answer: >
  Freeze the D1r fact-integrity design (three templates T1 capital_allocation_event.v1,
  T2 demand_guidance_contract_event.v1, T3 strategic_product_partnership_event.v1)
  plus the accepted review grafts as one contract file
  contracts/news_impact/news_impact_event.v1.schema.json. Evidence is the owner
  source_span.v1 payload or field_absence.v1, never a rival span store. Rulings:
  R1/R2 the excerpt cap and URL patterns are consumer projection rules (the projector
  nulls display_excerpt; text_sha256, locator and receipt carry the proof);
  R3 document_version minimum 1 is an owner invariant; R4 closed per-kind locators
  stand and an unknown locator key rejects at the boundary as locator_key_not_in_contract.
rationale: >
  D1r is the only candidate whose every object is closed, whose critical numerics
  bind to owner spans, and whose worked cases and counterexamples replay under an
  independent suite; D2 and D3 served as judge-panel diversity and contributed the
  period and quantity shapes. The owner excerpt is uncapped and nullable
  (engine/company_intelligence/documents.py lines 316 and 429), so a projection rule
  is the only reading that avoids a rival evidence object; span_id derives from the
  full locator (lines 369-371), so keys are never stripped. Revision below 1 raises
  in the owner (lines 189-190). Closed objects are gate 3 of the freeze.
alternatives:
  - option: Freeze D2 (labeler-first) or D3 (consumer-first) as the base.
    why_not: >
      D2 leaves 61 conditional fragments open and makes period_kind mandatory;
      D3 leaves 16 quantity fragments open and its build script was not executed
      in the read-only review; neither replays a counterexample battery.
  - option: Widen the locator key sets or strip unknown keys in the projector.
    why_not: >
      Stripping changes span_id; widening without a real owner caller admits
      unbounded address keys and breaks the closed-object gate.
  - option: Relax the excerpt cap and URL patterns to match the owner excerpt.
    why_not: >
      Admits instruction-bearing text into the display tier (masterplan section 3.5).
evidence:
  - "macro:research/prophet_v4/news_to_business_impact_20261006/PHASE0_FREEZE_2026-10-11.md on PR #8873."
  - "Fabric review lane R_D1r_remote_r1 (glm-5.3, read-only, ubuntu2): sentinel R_D1r_remote_r1: PASS 57f3041e22; 8/8 owner payloads accept, 4 conflict probes reject in base and copy."
  - "Fabric verification lane V_D2D3_remote_r1: sentinel V_D2D3_remote_r1: PASS 57f3041e22; D2 object_nodes=76 closed=15, D3 object_nodes=47 closed=31."
  - "Owner facts read at freeze worktree HEAD 81f1d5f03588: documents.py:316,:429 (excerpt nullable, defaults to full text), :189-190 (revision >= 1), :369-371 (span_id from full locator); resolution.py:134-144 (address unconstrained)."
  - "DNR:KILL-LLM-CONFIDENCE and DNR:KILL-CAUSAL-DAG-ALPHA: no confidence, score, target or rating field in any template."
  - "Fabric review record orch/fabric/reviews/PROPHET_NI_W1c_r1.md (sha256 prefix 0408ba017da3f8a8): R copy 3b7346f668d0ed18 of D1r; adversarial battery 443 rows, base admits 356, R copy 0; benign 154 rows, 0 false rejects on both."
  - "Grafts applied before freeze: G-OC1 (locator table index integer >= 0 or text-safe string, owner test shape tests/test_company_intelligence_spine.py:414), F3 (basis const on T2 stated_amount), harness promoted to the freeze gate."
  - "Final contract bytes: contracts/news_impact/news_impact_event.v1.schema.json sha256 prefix 3edc7139; tests/test_news_impact_contracts.py 46 passed in the freeze worktree."
affects:
  - "contracts/news_impact/news_impact_event.v1.schema.json"
  - "engine/news_impact/*"
  - "tests/test_news_impact_contracts.py"
  - "research/prophet_v4/news_to_business_impact_20261006/*"
confidence: high
reversibility: costly
decided_by: fable-meta-ceo-seat-0e739467 under the Chairman delegation of 2026-10-10
decided_at: 2026-10-12
---

## Do not redo

Do not re-run the D1/D2/D3 judge panel, re-open the four conflict rulings without a
new owner fact, or mint a second span, absence or evidence object beside the owner's
source_span.v1 and field_absence.v1. Do not repair, rebase, arm or comment on PR #6514.
Widening a locator key set is a versioned contract amendment driven by a real owner
caller, never a projector strip.
