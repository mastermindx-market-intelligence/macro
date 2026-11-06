---
key: A-PLANS-TRACEABILITY-TABLE-IS-NOT-COVERAGE
claim: >
  A frozen plan's requirement-to-test table is an assignment of intent, not
  evidence of coverage, and a task can merge CI-green while NONE of the exact
  test ids that table named exists. The table is prose in a document on another
  branch, so nothing in the repository ever resolves it: pytest cannot fail for
  a test that was never written, and a reviewer reading "one owning test row is
  assigned per requirement" has no reason to suspect the rows are unbuilt.
  Coverage-by-NAME and coverage-by-BEHAVIOUR are two independent facts and a
  green suite proves neither - the behaviour may be exercised under a
  descriptive name (traceability lost, safety intact) or not at all (both lost),
  and the two look identical from the outside. Measured on GMI Industrials
  2026-09-27: T01 and T04 were both merged and green, their plan named 15 exact
  anchors `tests/<file>::test_ind_<req>`, and only the 2 whose bodies the plan
  also froze VERBATIM existed - the other 13 were absent, with zero `IND-*`
  requirement ids appearing anywhere in either landed suite.
falsifier: >
  For every row of the plan's requirement-to-test table belonging to a task you
  believe delivered, run the named node id: `python3 -m pytest
  "<file>::<test>"`. An id that does not exist reports `ERROR: not found` and
  `no tests ran` - it does NOT report a failure, which is why a suite run over
  whole FILES can never surface it. Then, separately, grep the suite for the
  requirement id itself; zero hits means no alternative traceability mechanism
  exists either. Only after both do you ask whether some differently-named test
  discriminates the required behaviour, which is a per-requirement judgement and
  not answerable from names.
so_what: >
  It decides what a program may TELL its commissioning authority. "15 of 56
  requirements delivered" was about to be reported from a table that assigned 15
  rows, when 13 of those rows named tests that do not exist - a claim sourced
  from the plan's intent rather than from the repository. It also decides what a
  later lane may safely change: with no anchor and no requirement id in the
  suite, any refactor can delete the only assertion protecting a requirement and
  no gate anywhere notices. The cure is cheap and belongs in the same increment
  as the delivery: vendor the requirement-to-owning-test map INTO the repo and
  have a test assert every named owner still resolves, so the table stops being
  prose on a branch and becomes something CI can fail on.
kind: landmine
verified_at: 2026-09-27
verified_by: >
  Claude Opus 5 seat c6467452 (GMI Industrials first vertical, operation
  gmi-industrials-fable-ceo-e2e-20260924-chairman-001). Measured with
  `python3 -m pytest "tests/test_industrials_result_cash.py::test_ind_d08"` and the
  other 14 plan-named node ids (13 reported `no tests ran`), plus
  `grep -c "IND-" tests/test_industrials_result_cash.py tests/test_industrials_dependency_binding.py`
  (zero). Cured and enforced at
  tests/industrials_result_cash_helpers.py:65 (`PLAN_REQUIREMENT_ANCHORS`).
scope: [macro, agentos, all-programs]
confidence: verified
---

## Detail

The frozen plan for this program says, in the section that carries the table:

> All requirements below are inherited unchanged from r1/r2/W12. Tests are planned and
> **NOT_EXECUTED**. [...] One owning test row is assigned per requirement; additional
> cross-cutting checks can support several requirements without multiplying test counts.

`NOT_EXECUTED` is doing real work in that sentence and is easy to read past. It means the table
is a PLAN, and the plan's own convention for the anchor name (`test_ind_<requirement>`) is
honoured verbatim in the handful of places where the plan additionally freezes a test BODY. For
this program that was 2 of 15 rows for the delivered tasks; both of those anchors exist, and
they exist *because the body was frozen*, not because the table named them. Wherever only the
table named the test, the implementing lane wrote descriptive names instead and the anchor
silently never came into being.

Why no instrument catches it:

* A suite run names FILES, so a missing test is not a failing test. `pytest
  path::test_that_does_not_exist` exits with `ERROR: not found` and the line `no tests ran` -
  a shape that looks like a typo in the command rather than a coverage hole, and one that never
  occurs at all in normal CI because CI runs whole files.
* The table lives in a document on a research branch, not on `main`. No test, hook, or CI job
  reads it, so it cannot fail.
* `grep` for the requirement id finds nothing either, because nothing obliged the lane to write
  the id into the test. There is no second, weaker traceability mechanism standing behind the
  table - the absence is total.
* The suites are large and green (103 tests here), and green is exactly what a coverage claim
  gets read against.

The asymmetry worth remembering: a missing anchor whose behaviour IS covered elsewhere costs
only traceability, and is invisible; a missing anchor whose behaviour is NOT covered costs the
requirement itself, and is equally invisible. You cannot tell which you have without reading
every candidate test and asking whether any assertion distinguishes compliance from violation.
Judging that from test names is how a weak owner gets counted as a delivered requirement -
related: [[an-assertion-on-a-symbol-the-tree-lacks-passes-for-free]].

Ordering rule that follows: measure coverage before reporting it, report the count you measured
rather than the count the plan assigned, and land the map plus its enforcing test in the same
increment as the requirement work - otherwise the next lane inherits the same silence.

Related: `DSC:A-FROZEN-PLANS-EXAMPLE-TEST-CAN-BE-HALF-DEAD` (the same plan's frozen example
bodies can be present but vacuous - this record is the case where the named test is not there at
all).

## Amendment 2026-09-29 - the cure named above is necessary and NOT sufficient

The `so_what` and the ordering rule tell you to vendor the requirement-to-owning-test map into
the repo and have a test assert every named owner resolves. Do that - it is still right - but do
not read it as closing the hole. A vendored map makes a row GRADEABLE without making it HONEST,
because the one thing a plan's traceability table never carries is the requirement's own text:
the obligation lives in the upstream specifications the plan says it inherits "unchanged", and
on this program those are not in the repository at all. Measured 2026-09-29 by two agreeing
instruments: of the 56 ids the table names, 41 appear NOWHERE in the tree, and the 15 that do
appear only because delivered code cites them. So an anchor row can be added for any id in the
table, will resolve cleanly, and will assert a requirement rather than enforce one.

What closes it is a declared `anchor_basis` per requirement in the vendored table - `RULING`,
`LANDED_BEHAVIOUR`, or `NO_SOURCE` - with the guard refusing to anchor a `NO_SOURCE` row, so
extending coverage requires naming a real source in the same change. See
`DSC:A-VENDORED-TRACEABILITY-MAP-STILL-HAS-NO-REQUIREMENT-TEXT` for the measurement, the
per-task table, and the seven mutations that prove the guard discriminates.
