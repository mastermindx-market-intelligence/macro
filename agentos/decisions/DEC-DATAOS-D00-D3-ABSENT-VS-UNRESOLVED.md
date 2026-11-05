---
key: DATAOS-D00-D3-ABSENT-VS-UNRESOLVED
question: >
  The Q01 numerical oracle (verification wave, PR #9273) pre-registered that a window whose only
  split observation is INFERRED has oracle factor 1, while the SUT (price_views.split_factor,
  sadj_view, total_return_view) refuses it with the typed NOT_CONFIRMED. D00.D3 says the product
  S(t; v) runs over qualified events but does not say what an unqualified observation does to the
  window. Which reading binds: compute factor 1, or refuse?
answer: >
  Refuse. D00.D3 distinguishes ABSENT (no split observation at all — empty product, factor 1, the
  oracle's reading stands) from UNRESOLVED (the revision set CONTAINS an observation whose
  qualification is INFERRED). An UNRESOLVED window cannot assert its share basis either way, so
  split_factor, sadj_view and total_return_view refuse with the typed NOT_CONFIRMED under D00.D4
  (context may be shown, computation refuses); RAW is untouched. Recorded as D00.A2 in
  research/data_os_completion/2026-10-13/D00_SEMANTIC_DECISIONS.md; the oracle pin
  test_Q01_06_not_confirmed_pre_registered_oracle_factor (strict xfail) was replaced by
  test_Q01_06_not_confirmed_is_a_typed_refusal_by_ruling in PR #9273 commit b1ca917a0b7d. No
  library change was needed — the SUT already behaved this way at first run.
rationale: >
  Computing factor 1 over an INFERRED observation states "no split happened" without a qualified
  receipt, which is exactly the false consensus C03 exists to prevent; applying the inferred ratio
  would admit an unqualified event against P01.02. A typed refusal is the only answer that keeps
  the declared share basis honest, and it is already the implemented behaviour, so the ruling
  changes the oracle's pre-registration, not the SUT.
alternatives:
  - option: Keep the oracle's pre-registration (factor 1) and change the SUT to compute it.
    why_not: >
      It asserts a share basis the evidence cannot support and silently drops the INFERRED
      observation; the strict-xfail pin would have become a production change made to satisfy a
      test rather than a decision.
  - option: Apply the inferred ratio as if confirmed.
    why_not: P01.02 forbids admitting a discontinuity-inferred action as a confirmed event.
  - option: Leave F1 open as an UNRESOLVED finding in the verification return.
    why_not: >
      The ambiguity is in D00's text, which only the seat can amend; leaving it open would carry a
      strict-xfail pin that contradicts the implemented and intended behaviour into C00.
evidence:
  - "PR #9273 commit b1ca917a0b7d (tests/verification/test_oracle_q01.py: pin renamed and inverted; research/data_os_completion/2026-10-13/Q01_ORACLE.md FINDING F1 CLOSED-BY-RULING)"
  - "ORCH-4 return packet (scratchpad returns/ORCH-4_RETURN_20261014T0801Z.md) §GAPS Q01-F1: 'D00.D3 is ambiguous here and needs a D00 clarification (seat or owner)'"
  - "lib/dataos/price_views.py NOT_CONFIRMED refusal path (P02, PR #9152 squash 0f8ecf0bd6be) — unchanged by this decision"
affects:
  - WS:DATA-OS-COMPLETION
  - lib/dataos/price_views.py
  - tests/verification/test_oracle_q01.py
  - research/data_os_completion/2026-10-13/D00_SEMANTIC_DECISIONS.md
  - research/data_os_completion/2026-10-13/Q01_ORACLE.md
confidence: high
reversibility: costly
decided_by: coo-fable
decided_at: 2026-10-17
---

## Context

The verification wave's numerical oracle was written independently of the SUT from D00's text
(ORCH-4, M2 fabric lane, 2026-10-14). Fifty of fifty oracle cases agreed with the SUT except one
pre-registered reading: a window carrying only an INFERRED split. The seat ruled on 2026-10-17
that the SUT's typed refusal is the correct reading and amended D00 (D00.A2) so the next reader of
D00.D3 does not reproduce the ambiguity.

## What this does not change

No library code, no refusal vocabulary, no action-qualification rule (P01.02) and no RAW view.
The ruling is scoped to the oracle's pre-registration and D00's prose.
