---
key: F07-EVENT-PROPOSES-DIRECTION-MODEL-OWNS-MAGNITUDE
question: >
  F07 needs a source-grounded event to produce a proposed valuation-assumption change.
  The merged B-F07-3 bridge forbids magnitude outright ("no magnitude, no probability,
  no confidence"). Does adding a proposed VALUE violate that, and if not, where may the
  number come from?
answer: >
  The B-F07-3 prohibition is preserved and is the right rule for what it governs: a
  CLASS carries no number, so deriving a magnitude from "Acquisitions" is fabrication.
  A proposal may carry a value only under an explicit split — the EVENT supplies the
  DIRECTION, and the MODEL supplies the NUMBER. `proposed_value` must be exactly one of
  B-F07-1's already-published preset values (engine.valuation_scenario.SCENARIOS) for
  that input, selected as the adjacent scenario in the event's direction, and is stamped
  `magnitude_source: "model_preset"`. The literal `"event"` is unrepresentable. An
  assertion in engine.valuation_event_proposal._build enforces this, and the panel
  prints, alongside every proposed figure, that the number is the page's own scenario
  and not one the company gave.
rationale: >
  An event is evidence; an assumption is a model input. Preserving that distinction is
  the whole point of the bridge, and it is preserved exactly when no number crosses from
  the evidence side to the input side. Selecting among scenario points the model has
  already published invents nothing — it is the same act as a user clicking the
  "Upbeat" preset, which B-F07-2 already ships. This unblocks a real before/after delta
  without a second valuation math and without any new rights.
alternatives:
  - option: "Read a magnitude out of the filing text (e.g. 'raising guidance to $8.40')."
    why_not: "Converts qualitative prose into a model input — the exact laundering the F07 do_not_redo forbids, and unbounded: the figure's units rarely match the control's."
  - option: "Keep direction only and never show a number."
    why_not: "Then the scenario engine can never be exercised and the commission's before/after delta is unreachable; the abstention path alone cannot prove the seam works."
  - option: "Let an LLM size the delta."
    why_not: "Fleet law A7 — LLMs never originate market facts, scores, or estimates."
evidence:
  - "engine/valuation_event_proposal.py: assert proposed_value in published preset set (invariant 1)"
  - "tests/test_valuation_event_proposal.py::test_magnitude_never_comes_from_the_event_even_when_the_phrase_has_a_number"
  - "CTVA 8-K 2026-07-30 accession 0001755672-26-000022 contains 'raising our full-year guidance' (HTTP 200, phrase verified in the filed document)"
  - "DEC:F07-VALUATION-SOURCE-IS-SEC-COMPANYFACTS-V1 (base stays SEC companyfacts)"
affects:
  - "WS:MARKET-OS"
  - "F07 lane"
  - "engine/valuation_event_proposal.py"
  - "engine/valuation_assumptions.py"
confidence: high
reversibility: easy
decided_by: "session bb5e1c7a-9f68-438a-8e84-656f8ac0d61b (Opus orchestrator child, F07 event->AssumptionChange commission)"
decided_at: 2026-09-22
review_by: 2026-11-22
---

Consequence for the panel: a proposed figure is always one of the three V1 presets, so a
reader who clicks "Upbeat" lands on exactly the number the proposal showed. The event
never moves anything; it only points at which of the model's own cases it argues for.
