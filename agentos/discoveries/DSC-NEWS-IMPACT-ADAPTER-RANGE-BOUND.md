---
key: NEWS-IMPACT-ADAPTER-RANGE-BOUND
claim: >
  The frozen news_impact_event.v1 quantity_range has no bound field and forbids extra
  fields, while prophet_evidence.v1 display_quantity requires a bound on a range, so the
  two contracts do not meet on their own. Up to ni-prophet-adapter-1 the owner adapter
  read raw["bound"] on its range branch and raised a bare KeyError on every
  contract-valid range: 34 of 127 graded fam_a events, 27 of 88 graded fam_b events and
  1 event in each queue run of the W3 shadow data. From ni-prophet-adapter-2 the adapter
  projects a range with bound "exact" unless the input carries one, a quantity missing a
  key it reads raises ProphetAdapterError MISSING_REQUIRED_FIELD with the slot and key
  only, and a range that overruns the 48-character amount or the copy word budget is
  refused SLOT_TOO_LONG exactly as a point is (DEC:NEWS-IMPACT-ADAPTER-RANGE-BOUND).
falsifier: >
  PYTHONPATH=. python3.12 -m pytest tests/test_news_impact_prophet_adapter.py -q -k
  "range or missing_key or form" builds T1, T2 and T3 events whose quantities are v1
  ranges, confirms validate.validate_event accepts them, and asserts the adapter projects
  bound "exact", codes every missing or unknown key, and refuses an over-budget range as
  it would a point. A KeyError, a SCHEMA_VIOLATION or any other bound on a bound-less
  range would refute the claim; so would a v1 schema that now admits a bound on
  quantity_range.
so_what: >
  (1) Never add a bound to range events to suit the adapter; the v1 event contract is
  byte-frozen (DEC:NEWS-IMPACT-PHASE0-FREEZE) and the gap is closed in the adapter.
  (2) A rendered range carries no hedge word; where a filing hedged a range, that hedge
  was lost upstream in the v1 shape, and restoring it is an event-contract question for
  a later version. (3) The stage-two producer counts any owner adapter crash as
  adapter_crash:<class>; on the shadow events that count is now zero, so a non-zero value
  is a new defect, not this one.
kind: constraint
verified_at: 2026-10-15
verified_by: >
  tests/test_news_impact_prophet_adapter.py (109 passed; 12 of the 13 first-round range
  and missing-key tests fail on ni-prophet-adapter-1) and stage two on the four W3 shadow
  event files: adapter_crash:KeyError 34, 27, 1 and 1 before the repair and 0 after,
  with 34, 27, 1 and 1 range quantities projected with bound exact.
scope:
  - "engine/news_impact/prophet_adapter.py"
  - "engine/news_impact/producer_facts.py"
  - "contracts/news_impact/"
confidence: verified
---

# The event range has no bound; the Prophet adapter supplies "exact"

The two frozen contracts disagree about a range's bound. The adapter used to crash on
every contract-valid range; it now projects bound "exact", carries one if present, and
codes a missing key instead of raising a KeyError. The stage-two producer's crash count
on the shadow events is zero.
