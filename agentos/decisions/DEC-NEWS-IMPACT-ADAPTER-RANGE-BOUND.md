---
key: NEWS-IMPACT-ADAPTER-RANGE-BOUND
question: >
  The frozen news_impact_event.v1 quantity_range has no bound field and forbids extra
  fields, while prophet_evidence.v1 display_quantity requires a bound on both range and
  point forms (bound enum exact, approximately, up_to, at_least). The owner adapter read
  raw["bound"] on a range and raised a bare KeyError on every contract-valid range
  (DSC:NEWS-IMPACT-ADAPTER-RANGE-BOUND). What bound does the adapter project for a v1
  range, and what does it raise on a quantity it cannot project?
answer: >
  (1) A RANGE PROJECTS BOUND "exact". prophet_adapter._project_quantity emits
  RANGE_BOUND = "exact" when the input has no bound key. It is the only value of the
  display enum that adds no hedge the event does not carry, and it is what format_amount
  already assumed when a bound was missing, so the rendered copy is the same low–high
  string with no "about", "up to" or "at least" prefix. A bound key present on the input
  is carried as given and the adapter's output validation judges it, as on a point: a
  null, empty or unknown bound fails SCHEMA_VIOLATION, and a later event version that
  adds a valid one needs no adapter change.
  (2) A MISSING KEY IS A CODED ERROR. Before projecting, the adapter checks the keys it
  reads: form on every quantity; low, high, unit, currency and basis on a range; value,
  bound, unit, currency and basis on a point. A missing key raises
  ProphetAdapterError("MISSING_REQUIRED_FIELD", "<slot>.<key>"), and a form other than
  point, range or absent raises SCHEMA_VIOLATION "<slot>.form". The message holds the
  slot and key only, never a value.
  (3) A RANGE IS HELD TO THE SAME BUDGETS AS A POINT. amount_plain over the
  prophet_evidence.v1 limit of 48 characters raises SLOT_TOO_LONG when the record is
  built, and copy over the copy_templates.v1 word budget raises SLOT_TOO_LONG when
  render_glance_copy renders it. A range repeats its unit per endpoint, so a long unit
  reaches either budget sooner than the same quantity as a point; a compact range format
  is a copy-design question for the A7 owner, not an adapter change.
  (4) ADAPTER_VERSION moves to ni-prophet-adapter-2 because the projection changed. No
  committed record embeds it.
rationale: >
  The event contract is byte-frozen (DEC:NEWS-IMPACT-PHASE0-FREEZE) and stage two must
  not add a bound to events to suit the adapter (DEC:NEWS-IMPACT-W3-PRODUCER-STAGE2), so
  the gap is closed where the two contracts meet. The output schema demands a bound, so
  omitting it is not an option. "exact" says the filing stated a range without a hedge
  word, which is what a v1 range records. Where a filing did hedge a range, the hedge was
  already lost upstream in the v1 shape; restoring it is an event-contract question for a
  later version, not an adapter guess.
alternatives:
  - option: Omit bound on a range.
    why_not: >
      prophet_evidence.v1 display_quantity requires bound when form is range, so every
      such record would fail the adapter's own output validation with SCHEMA_VIOLATION.
  - option: Make bound optional on a range in prophet_evidence.v1.
    why_not: >
      That changes an accepted A7 contract and its byte-identical design copy to fit one
      producer, and every consumer would then have to handle a missing hedge.
  - option: Refuse every range with a coded ProphetAdapterError.
    why_not: >
      About a quarter of the shadow events carry a range, and nearly all of them fit both
      budgets; refusing them all drops Prophet evidence for no reason the contracts give.
      Only a range that overruns a budget is refused, exactly as a point would be.
  - option: Write the unit once on a range so long units fit the budgets.
    why_not: >
      It changes the rendered amount of every range, a copy-design choice that belongs to
      the A7 owner, to fit ranges the shadow events never produced; it is recorded as a
      question for that owner.
  - option: Project "approximately" for every range.
    why_not: >
      It adds a hedge the source may not have used and changes the rendered copy.
evidence:
  - "tests/test_news_impact_prophet_adapter.py: 109 passed. Range tests cover incremental_amount, remaining_authorization, executed_amount (T1_execution), stated_amount on the worked cases W3 and R2 (T2), stated_quantity (T3_milestone), low equal to high, a non-USD unit, negated and negative ranges, a carried and an invalid bound, the build-time and render-time budget refusals, and coded missing or unknown keys; 12 of the 13 first-round tests fail on the previous adapter. These tests are the committed falsifier."
  - "Stage two on the four W3 shadow event files with the repaired adapter: graded fam_a adapter ok 125 and SLOT_TOO_LONG 2 (was ok 91, adapter_crash:KeyError 34, SLOT_TOO_LONG 2); graded fam_b ok 88 (was ok 61, crash 27); queue fam_a ok 12 (was 11, crash 1); queue fam_b ok 7 (was 6, crash 1)."
  - "The repaired runs project 34, 27, 1 and 1 range quantities, all with bound exact; the longest range amount slot is 29 characters against a limit of 48, and render_glance_copy refuses none of the 231 records, 63 of them ranges."
  - "The stage-two figures come from shadow event files held in scratch under DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE; they are not committable and cannot be reproduced from this repository."
  - "An independent read-only fabric review (lane W3R_ADAPTER_RANGE_REVIEW, review class) returned REQUEST_REPAIR with two major and three minor change-attributable defects; the bound, form, test and wording repairs above answer them, and the seat ruled the long-unit refusal a scoped budget refusal rather than an adapter format change."
affects:
  - "WS:PROPHET-NEWS-IMPACT"
  - "engine/news_impact/prophet_adapter.py"
  - "tests/test_news_impact_prophet_adapter.py"
  - "DSC:NEWS-IMPACT-ADAPTER-RANGE-BOUND"
  - "DEC:NEWS-IMPACT-W3-PRODUCER-STAGE2"
confidence: high
reversibility: easy
decided_by: "fable-meta-ceo-seat-0e739467 (recovered fork 959095da) under the Chairman delegation of 2026-10-10"
decided_at: 2026-10-15
---

# The Prophet adapter projects a v1 range with bound "exact" and codes missing keys

The event contract's range has no bound and the Prophet evidence contract requires one,
so the adapter fills the one value that adds no hedge, carries a bound if one is ever
present, and raises a coded error instead of a KeyError when a quantity lacks a key it
reads. On the W3 shadow events every range that used to crash the adapter now becomes
Prophet evidence.
