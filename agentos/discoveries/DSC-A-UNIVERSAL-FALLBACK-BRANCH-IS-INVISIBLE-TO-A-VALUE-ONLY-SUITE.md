---
key: A-UNIVERSAL-FALLBACK-BRANCH-IS-INVISIBLE-TO-A-VALUE-ONLY-SUITE
claim: >
  A suite that asserts only the VALUES a module computes cannot observe WHICH branch
  produced the prose around them, so a fallback selected for 100% of inputs ships green.
  Measured in Consumer Cyclical V1-CORE: `_build_explanation` tested the `FACT_KEY_*`
  constants (`total_revenue`, `advertising_revenue`, `advertising_expense`) for
  membership in the set of emitted RESULT keys (`*_change`, `advertising_net_change`,
  ...). Those two vocabularies are disjoint by construction, so the condition was
  unsatisfiable, the R6 advertising-flow lead was unreachable on EVERY input, and the
  document always emitted the neutral fallback sentence. All six R6 §7.1 golden values
  were exact and 61 tests passed on the merged tree — the numbers were right and the
  sentence explaining them was missing. Only re-running from `main` after the merge and
  reading the rendered lead exposed it.
falsifier: >
  `project_economic_change(<the committed valid fixture>)["explanation"]["lead"]`
  returning the neutral fallback rather than the advertising-flow sentence; or
  `{FACT_KEY_TOTAL_REVENUE, FACT_KEY_ADVERTISING_REVENUE, FACT_KEY_ADVERTISING_EXPENSE}`
  intersecting the set of `RESULT_KEY_*` constants in
  `engine/sector_intelligence/consumer_cyclical_projection.py`; or
  `tests/test_consumer_cyclical_projection.py::test_result_keys_and_fact_keys_are_never_interchangeable`
  ceasing to exist or to assert disjointness.
so_what: >
  Three things change. (1) For any module that computes values AND selects prose about
  them, a value assertion is not coverage — at least one test must pin WHICH branch was
  taken for the canonical case, because the fallback is the branch that fails silently.
  (2) Where two identifier vocabularies read alike (fact keys vs result keys, request vs
  response fields, input vs output units), never spell one by string-concatenating onto
  the other: here `FACT_KEY_ADVERTISING_REVENUE + "_change"` and
  `RESULT_KEY_ADVERTISING_REVENUE_CHANGE` are equal TODAY, so the concatenation worked
  and a later rename would have retargeted it with no test failing. Name the constant.
  (3) This is the second independent instance of the family in this repo — see
  DSC:REFUSAL-BRANCH-HIDES-A-DEAD-LOOKUP, where an except-to-refusal branch fired for
  every episode and the refusal census was the camouflage. Both were found by driving
  the PRODUCTION path and reading its output, neither by the suite. Applies to every
  projection-plus-narrative module here: `engine/sector_intelligence/*_projection.py`,
  `engine/earnings_narrative/**`, and any builder whose explanation has a default arm.
kind: landmine
verified_at: 2026-09-24
verified_by: >
  Reproduced from `origin/main` after PR #7942 squash-merged as `6e3e8987c5c6`:
  `project_economic_change` on the committed fixture
  `data/sector_intelligence/fixtures/consumer_cyclical_intelligence_read_model.v1.valid.json`
  returned all six golden values exact (24344 / 10141 / 10145 / -4 / 0 / 41.66),
  `availability: ready`, `degraded: []`, 0 schema errors — with the neutral fallback as
  the lead. 61 tests were green at that commit. Repaired on PR #7945 by comparing
  `RESULT_KEY_*` constants; the same head then re-verified with the R6 advertising-flow
  sentence present. Mutation control both directions plus the disjointness invariant in
  tests/test_consumer_cyclical_projection.py (65 tests).
scope: [macro, engine/sector_intelligence/, research/consumer_cyclical/v1/]
confidence: verified
---

## Detail

The defect and its own camouflage were the same property. `_build_explanation` asks
"did the advertising results get emitted?" — a reasonable question — but asked it with
the wrong vocabulary, and the honest answer to the question it actually asked is always
"no". A `no` here is not an error: it is the neutral lead, which is a legitimate output
for a case with no advertising facts. So the module degraded exactly as designed, for
every input, forever.

Nothing in the suite looked at `explanation.lead` for the populated case. The tests were
built around the golden oracle — the part that is hard to get right and easy to assert —
and the prose was treated as decoration. That is backwards: the numbers had an exact
external oracle (R6 §7.1) and were therefore the SAFE part; the sentence had no oracle
at all and was the part that needed pinning.

A same-class audit after the repair (two defects, one root cause: comparing the wrong
KIND of identifier) found two further latent instances — the `"_change"` concatenations
and a `by_key` local named for a grouping that had moved to `metric`. Neither was live.
Both are now impossible.
