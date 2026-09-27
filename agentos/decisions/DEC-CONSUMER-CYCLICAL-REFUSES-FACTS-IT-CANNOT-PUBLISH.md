---
key: CONSUMER-CYCLICAL-REFUSES-FACTS-IT-CANNOT-PUBLISH
question: >
  When a source fact reaching the Consumer Cyclical projection cannot be expressed
  under the contract the projection authors — a thousands-separated `value_text`, an
  absent `period_start`, a `period_kind` outside the vocabulary — does the module
  repair the value, pass it through, or refuse to publish the fact?
answer: >
  Refuse, and declare the refusal. The fact is withheld from pairing and from
  `facts[]`, and its metric is recorded in `degraded_dependencies` with a specific
  reason (`fact_value_text_unparseable`,
  `fact_period_start_missing_or_malformed`, `fact_period_kind_outside_vocabulary`,
  `fact_period_end_missing_or_malformed`). The module never normalises a separator,
  never derives a period boundary, and never publishes a field it knows the contract
  rejects. A runtime self-check re-reads the assembled document against the
  contract's pattern-bearing constraints and raises `CaseShapeError` rather than
  returning a document that violates them.
rationale: >
  The projection is the sole author of
  `consumer_cyclical_intelligence_read_model.v1` documents, so a document that fails
  that schema is the module lying about its own output — the one failure mode no
  downstream consumer can defend against. Two of the three repair options make the
  module an authority it was never granted. Normalising `"365,223"` to `365223`
  decides that the comma is a thousands separator rather than a decimal mark, which
  is a source-semantics ruling this seat does not hold and R15 forbids inventing.
  Deriving `period_start` from `period_end` is worse: the removed fallback snapped to
  a calendar boundary, and Consumer Cyclical is the retail sector, whose fiscal
  periods are offset from the calendar by design — a 4-5-4 quarter ending 2025-02-01
  derived 2025-01-01, a valid-looking date describing a 32-day "quarter". Refusal is
  also the option already in the module's vocabulary: `_coerce_decimal_text` had been
  treating these same values as unparseable for *computation* since T2 merged, so the
  gate makes publication agree with computation instead of publishing what it could
  not use. Finally, refusal is loud. A degraded dependency with a named reason sends
  the defect upstream to whoever built the case; a normalised value hides it forever.
alternatives:
  - option: Normalise the value (strip separators, coerce formats) and publish.
    why_not: >
      Reading a separator is a source-semantics decision the projection has no
      authority to make, and a wrong reading is unrecoverable downstream because the
      published value looks clean. Violates the standing rule that no model prose or
      module heuristic originates a source fact.
  - option: Derive the missing period boundary from `period_end` and `period_kind`.
    why_not: >
      This is what the code did, unreachably, and it was wrong wherever it was
      reachable. Even month-subtraction (a strict improvement over calendar-snapping)
      is a guess for 52/53-week retail calendars, and a guessed period boundary is
      indistinguishable from a sourced one once published.
  - option: Publish the fact as-is and let the consumer validate.
    why_not: >
      No consumer exists yet (V1 legs 6-7 are owner-gated), so there is nothing to
      catch it; and the contract is the module's own promise, not the consumer's
      problem. This is the status quo that shipped the defect.
  - option: Raise `CaseShapeError` on the whole case when any fact is unpublishable.
    why_not: >
      Too coarse. One malformed advertising fact would suppress a perfectly good
      total-revenue change. The existing withholding machinery already degrades
      dependent results correctly once the bad fact is withheld from pairing.
evidence:
  - "Reproduced on pristine origin/main @90f9fcbe31ff: value_text '365,223' (the ordinary
     human spelling) -> 9 schema violations, availability 'unavailable'."
  - "Reproduced: fact missing period_kind -> facts[*].period_start '' and period_kind ''
     -> 18 schema violations."
  - "Reproduced: non-positive ratio denominator (a flat retail quarter) -> withheld
     result emitted with empty period_end / period_start / event -> 3 violations;
     _withheld_result had been discarding the provenance facts it was already given."
  - "Line-coverage audit under the full owned suite: 110/723 executable lines never
     executed; _envelope_period_end_internal and _fact_native_ref_or_default had zero
     callers anywhere in the repository."
  - "Golden oracle preserved after the change on both cases: 24344 / 10141 / 10145 /
     -4 / 0 / 41.66 exact, R6 advertising-flow lead still rendered."
  - "Mutation control: 9 mutants applied to the real module; 8 killed by the new tests
     (admission gate, period_start derivation, withheld provenance, schema mirror,
     refusal declaration, and all three self-check loops). The 9th — reverting the
     dedup guard to the non-existent `fact_key` field — SURVIVED, which is correct:
     that repair is behaviour-neutral today because the two sides use disjoint
     vocabularies. It is recorded as hygiene, not as a fix."
affects:
  - "WS:CONSUMER-CYCLICAL-V1"
  - "engine/sector_intelligence/consumer_cyclical_projection.py"
  - "contracts/sector_intelligence/consumer_cyclical_intelligence_read_model.v1.schema.json"
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-09-26
---

## Scope note

This decision governs the Consumer Cyclical projection only. It is written so the
Finance, Industrials, Energy and Healthcare projections can adopt it, but it does not
bind them: each is owned by its own seat, and `engine/sector_intelligence/finance_*.py`
was not inspected here. The shared observation — that a projection authoring a contract
must not publish documents that violate it — is recorded separately as
DSC:THE-CASE-A-SUITE-USES-MOST-IS-THE-ONE-IT-NEVER-VALIDATES so the other verticals can
check themselves cheaply.

What this decision does NOT settle: whether the synthetic `_plnt_case()` should be
reconciled with the contract in full. It currently retains 102 violations on fields the
admission gate does not police (`definition`, `display_quantum`, `kind`, `perimeter`,
`source_records`, `subject`, and duplicate `input_refs`). That reconciliation is real
work with real ripple into ~40 assertions and is left open in the workstream rather than
rushed in behind this change.
