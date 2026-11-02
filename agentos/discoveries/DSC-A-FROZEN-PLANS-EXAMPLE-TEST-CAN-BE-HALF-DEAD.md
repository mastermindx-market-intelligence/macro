---
key: A-FROZEN-PLANS-EXAMPLE-TEST-CAN-BE-HALF-DEAD
claim: >
  An example test frozen into a plan is not executable evidence, and it can be
  HALF dead against the helper that actually landed. The two halves fail
  asymmetrically and the quiet one is the dangerous one: an assertion that calls
  a helper attribute which does not exist raises `AttributeError` and gets
  noticed immediately, while an assertion taken over a stub that returns an
  EMPTY collection passes for free in both directions - `set() <= set()`,
  `[] == []`, `not any([])` are all true whatever the code under test does. A
  lane dispatched on such a plan repairs the loud half, sees green, and ships a
  suite whose central anti-shortcut assertion certifies nothing. The plan is not
  wrong to contain the example; the defect is treating a frozen example as a
  gate before it has been shown able to FAIL.
falsifier: >
  For the plan's example test, resolve EVERY attribute and symbol it touches
  against the landed helper - `git show origin/main:<helper> | grep -n "def
  <attr>"` for each, checking the owning CLASS and not merely the file, because
  a same-named method on a neighbouring class reads as present. Then apply, one
  at a time, the mutation each assertion claims to catch and re-run the suite. If
  every symbol resolves on the right class AND every mutation reds the suite, the
  example is executable evidence and this claim does not apply to it. The claim
  is also falsified by any empty-collection assertion that reds when the
  collection is forced empty.
so_what: >
  Before dispatching a task whose acceptance rests on a plan-frozen example
  test, run two cheap checks and put their output in the dispatch packet: the
  symbol-resolution list, and a mutation probe per assertion. Treat an unmarked
  stub returning an empty collection as a DEFECT to cure in the same increment,
  never as a placeholder to leave for the lane - a lane that meets an
  `AttributeError` has two ways forward, and the cheaper one is deleting the
  assertion it cannot satisfy and self-reporting PASS. Curing the harness before
  the lane runs is not doing the lane's work: it converts an ungradeable gate
  into a gradeable one, which is the only form in which a self-verdict can be
  checked at all. This is lawful during a dependency hold whenever the plan
  itself authorizes authoring synthetic tests while a gate is held - authoring
  them cannot make that gate passed, and making the gate real is the opposite of
  making it pass. Corollary for the writing side: a plan author should prefer an
  example whose helper surface already exists, and a reviewer should treat "the
  plan says so" as a requirement, never as evidence that the requirement is
  currently enforced.
kind: landmine
verified_at: 2026-09-27
verified_by: >
  GMI Industrials first vertical, operation
  `gmi-industrials-fable-ceo-e2e-20260924-chairman-001`. The frozen plan (blob
  `a5462dc7f36aea08c57ce43a8a230ef00ebae802`, section T02) mandates a two-run
  refresh test as T02's explicit anti-shortcut gate - the same section says
  "Profile enrollment alone must not satisfy this task". Measured against merged
  `origin/main` after T01 and T04 had both landed green: (1)
  `_PublicationHarness.members()` in `tests/industrials_result_cash_helpers.py`
  was `return set()`, an unmarked stub and the only method in that file carrying
  no docstring, so the mandated `assert before <= h.members()` could not fail;
  (2) `_PublicationHarness` had no `get()` method at all, while
  `_SyntheticClient` - a different class in the same file - does have one, so a
  file-level grep for `def get` reads as PRESENT; (3) `run_refresh`'s first
  parameter was named `_changes` and was deliberately unused, and the injected
  `http_get` fake returned 503 for the submissions URL whenever `fail_sources`
  was non-empty, refusing the WHOLE refresh - so the plan's own scenario, one
  case advancing while a named case carries, was unreachable. Cured on branch
  `claude/ind-t02a-harness-gate`: `python -m pytest
  tests/test_industrials_dependency_binding.py tests/test_industrials_result_cash.py
  -q` went from `97 passed` to `103 passed` with no test changed or removed, and
  seven mutations applied one at a time to the harness - empty-stub `members()`,
  a refused case advancing its edition, a refused case restamped with a fresh
  observation, a refused case invented with no predecessor, `get()` handing out
  the live record instead of a copy, `fail_sources` refusing the whole refresh
  again, and the stale flag never set - were CAUGHT 7 of 7 with 0 survivors.
scope: [macro, agentos, all-programs]
confidence: verified
---

## Detail

The asymmetry is the whole finding. Both halves of a dead example are wrong, but only one
of them announces itself.

**The loud half is self-reporting.** `h.get('case_a')['edition']` against a harness with no
`get()` raises `AttributeError` on the first run. Nobody ships past it. It costs a lane one
cycle and it is not a landmine.

**The quiet half is a guarantee that is not one.** `before = h.members()` followed by
`assert before <= h.members()` reads, to a reviewer and to the lane, as "an ordinary refresh
preserves the cases that were already enrolled". With `members()` hardcoded to an empty
collection it asserts `set() <= set()`. It cannot fail if the code preserves nothing, and it
cannot fail if the code deletes everything. The stronger the sentence the assertion appears
to make, the more expensive the silence.

**Why a same-file grep is not enough.** `_SyntheticClient.get` exists in the same module for
an unrelated purpose (`test_route_unbound_client_causes_no_read`). A grep for `def get` over
the file answers yes. The attribute must be resolved against the CLASS the example's object
actually is - which is the `assertion-on-a-symbol-the-tree-lacks` family read from the other
direction: there, a wrong name made a negative assertion vacuous; here, a right name on the
wrong class makes a presence check vacuous.

**The ordering rule this produces.** Cure the harness, prove each assertion can fail, and only
then dispatch the lane. Doing it in the other order hands the lane an ungradeable gate plus a
strong incentive to trim it, and this program has already measured twice what a lane's own
verdict is worth against a gate that cannot fail
(`DSC:A-LANE-SELF-VERDICT-IS-NOT-A-CLOSURE-GATE`: a self-reported `PASS 0 blockers` over five
real blockers, then a second `PASS 0/0/0` over a sixth).

Related: `DSC:A-LANE-SELF-VERDICT-IS-NOT-A-CLOSURE-GATE` is why the gate must be gradeable
before dispatch rather than after. The empty-collection mechanism is the same one that turns
an accumulator seed into a fabricated total when a multi-leg formula is handed zero legs - one
reds nothing, the other certifies a number, and both come from an empty container being a
legal value everywhere.
