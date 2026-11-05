---
key: FIF-S0-RAGGED-LAYOUT-FAIL-CLOSED
question: >
  When a displayed SEC statement table's cell grid is ragged, overlapping, or
  spans past the captured table, should the statement reconstruction infer a
  best-effort layout or refuse?
answer: >
  Refuse, fail-closed, with the typed error prefix
  `displayed statement layout unsupported:` followed by the specific detail
  (overlapping cell at row/column, span exceeds the supported bound, span
  past the captured table, or hole after grid expansion). Never infer.
rationale: >
  A displayed statement is the composition the user reads
  (DEC:FIF-3A1-DISPLAYED-TABLE-IS-THE-COMPOSITION); a silently padded or
  best-effort realigned grid would emit cells at coordinates no source cell
  occupies, manufacturing statement structure the filing does not show. The
  supported layouts (rowspan carry, colspan spacer groups — the AAPL pattern)
  are exactly the ones the grid expansion can place without invention; every
  other shape names itself in the refusal so a future widening is a
  deliberate, tested extension rather than silent tolerance.
alternatives:
  - option: best-effort alignment (shift or clamp overlapping/out-of-range cells onto the grid)
    why_not: >
      Fabricates a plausible-looking statement the filing does not display —
      the worst failure class for a forensic surface, because the wrong grid
      is still internally consistent and reaches users as fact.
  - option: silent column padding (fill holes with empty placeholders and continue)
    why_not: >
      A hole after expansion means a slot no source cell claims; padding
      hides a capture/parsing defect behind a rendered table instead of
      surfacing it as a typed refusal.
evidence:
  - "engine/fundamental_forensics/statement_graph.py:502 (branch claude/fif-s0-statement-grid-20261012, head 471703401f68) — _DISPLAYED_LAYOUT_UNSUPPORTED = \"displayed statement layout unsupported:\""
  - "engine/fundamental_forensics/statement_graph.py:505-506 — _layout_unsupported() builds StatementGraphError with that prefix"
  - "engine/fundamental_forensics/statement_graph.py:519-543 — _expand_displayed_statement_grid(): overlap raise at place(), span_overflow and span-past-table raises; docstring names overlap/span-overflow/hole as the refusal classes"
  - "tests/test_fundamental_forensics_statement_grid.py:120-122 — pytest.raises(StatementGraphError, match=r\"^displayed statement layout unsupported:\") and str().startswith() pin the exact prefix"
  - "synthetic fixtures tests/fixtures/fundamental_forensics/synthetic_statement_tables/syn_a09_* (8 files) prove the supported rowspan/colspan/repeat-row layouts; golden AAPL statement bytes unchanged (commit 7f41264999 'golden bytes unchanged')"
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - engine/fundamental_forensics/statement_graph.py
  - tests/test_fundamental_forensics_statement_grid.py
confidence: high
reversibility: easy
decided_by: coo-fable (FIF e2e seat; branch claude/fif-s0-statement-grid-20261012, head 471703401f68)
decided_at: 2026-10-12
---

# FIF S0 — ragged/overlapping displayed layouts refuse, never infer

S0 generalized source-faithful statement reconstruction to rowspan/colspan
grids (repeated rows, rowspan label carry, colspan spacer groups) while
keeping the accepted AAPL golden statement bytes unchanged. The decision is
the failure posture: any grid the expansion cannot place exactly — overlap,
span overflow, span past the captured table, or a hole after expansion — is
`displayed statement layout unsupported:` with the specific detail, not a
repaired guess. Widening support later means adding a new explicit layout
case plus fixtures, and the refusal detail already names which case fired.
