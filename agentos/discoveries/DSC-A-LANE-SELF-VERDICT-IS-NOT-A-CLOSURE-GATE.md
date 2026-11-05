---
key: A-LANE-SELF-VERDICT-IS-NOT-A-CLOSURE-GATE
claim: >
  An external fabric lane's own review verdict is uninformative in BOTH directions and
  must never close a task. Measured on two consecutive rounds of one artifact: round 1
  self-reported `PASS 0 blockers / 0 major / 1 minor` and carried FIVE blockers and
  two majors; the round-2 repair, commissioned with all seven reproduced inline,
  self-reported `PASS 0/0/0` and carried a SIXTH blocker. The lane is not lying - it re-runs the suite it was
  given, and every one of the eight defects was invisible to that suite, because a
  suite written by the same lane tests the branch the author was thinking about. A
  verdict is therefore evidence that the tests pass, which is the one thing nobody
  needed a reviewer to establish.
falsifier: >
  Re-apply the previous round's surviving mutations to a lane-PASS head and find them
  already CAUGHT by tests the lane wrote unprompted: build the scratch tree, then
  `python3 -m pytest tests/test_industrials_result_cash.py -q -p no:randomly` per
  mutation, expecting a named assertion failure for each without a seat ruling having
  asked for it. Equivalently, an independent READ_ONLY red-team returning zero findings
  against a head carrying only lane commits. The counterexample measured here is #8062:
  round 1 at 365c2666b88a and round 2 at 05ad9c8da019 both self-reported PASS and both
  failed that test; the per-mutation table is in #8070.
so_what: >
  Budget an independent adversarial pass per task round, not per task, and treat the
  lane's STATUS line as delivery (the RUNNING->DELIVERED rung) rather than as CI or
  acceptance. Never branch a dependent task off a lane-PASS head. The cheap decisive
  instrument is mutation, not reading: re-apply every mutation that survived the
  previous round and require each to be CAUGHT, because a repair that adds a test
  adjacent to the defect looks identical in a diff to one that binds it. Corollary for
  rulings: hand the repair lane an explicit "NOT A FINDING - do not fix these" list, or
  it will rewrite the parts that were already correct.
kind: constraint
verified_at: 2026-09-26
verified_by: >
  GMI Industrials first vertical T04, PR #8062. Round 1 head
  365c2666b88a8e0afdae5f294aef3f9553e44ea0, lane self-verdict PASS 0B/0M/1m; an
  independent Opus READ_ONLY red-team plus seat probes found B1 (the production
  comparison-receipt constructor was never fed to its consumer - forcing every
  comparability gate true left the suite green at `48 passed`), B2 (`receipt_id`
  identity asserted nowhere - freezing it to a constant survived), B3 (`receipt_ref`
  never bound), B4 (a zero-segment bridge returned `ready, value="30"` by certifying its
  own `Decimal("0")` accumulator seed), B5 (a typed-absent leg byte-identical to no leg),
  plus M1/M2. Round 2 head 05ad9c8da01960c25ba0e5f3855d2da09eb711af, lane self-verdict
  PASS 0B/0M/0m, `93 passed`: all seven ruled items were genuinely cured (each of the
  five previously surviving mutations re-applied and now CAUGHT; one frozen
  `receipt_ref` site fails 7 tests) and B6 was still live - an OMITTED `checked`
  argument defaulted to all-True, so a quarter compared against a year qualified
  `ready` with no limitations while `checked={}` on the same operands refused
  `duration_mismatch`. Full record and per-cure mutation table:
  research/industrials/first_vertical_program/reviews/OPUS_T04_REDTEAM_2026-09-26.md
  (PR #8070). The same practice is recorded independently by the sibling Mining program,
  whose T04a delivery is explicitly gated on an Opus READ_ONLY red-team rather than the
  lane's report (agentos/handoffs/GMI-MINING-2026-09-24-m1-integration.md).
scope: [macro, external-fabric-lanes, gmi-industrials]
confidence: verified
---

## Detail

The failure is structural, not a quality problem with any particular provider.

A lane receives a packet, writes the module and writes the suite. Both come from one
reading of the spec, so a misreading is reproduced in the test that was supposed to
catch it, and the suite goes green. Then the lane's reviewer step runs that suite and
reports `PASS`. Nothing in the loop is adversarial to the lane's own interpretation, so
the verdict cannot carry information about interpretation errors - which is where the
expensive defects live.

Both round-1 and round-2 verdicts on T04 were wrong in the same way and in opposite
directions of confidence. That matters for how a seat spends its budget: the instinct
after a clean round-2 report is to accept and move on, and that instinct is exactly what
the measurement refutes. The sixth blocker was found by probing a keyword default
nobody had ruled on.

**The instrument that actually worked** was mutation against the current module text,
run in a scratch tree so the checkout is never written: symlink every top-level entry of
the checkout except the package under test, `copytree` that package, mutate the copy, run
pytest with `cwd` pointed at the scratch tree. Two practical notes. First, needles go
stale - five of eight mutations reported NEEDLE-ABSENT after the repair restructured the
module, which reads like "caught" and is not; re-derive every needle from the current
text and print a replace count so a multi-site mutation is explicit. Second, a mutation
that produces a collection ERROR rather than a clean assertion failure is not proof a
test caught it; narrow to a single site until the failure is an assertion.

**Where the reviewer's own framing needed correction too.** Round 1's headline asserted
"a blanket false certification of every comparability gate". A probe disproved it: with
every gate forced true, a currency mismatch is still refused, because that gate is
decided by inspecting the operands. Only gates where the receipt is the sole evidence of
comparability consult the flag - and that is precisely where B6 bit. Had the seat ruled
from the reviewer's framing instead of probing, a false finding would have gone to the
repair lane. Probe before ruling, and name the gate you demonstrated rather than the
class you assume.

Related: DSC:EXTERNAL-REPAIR-LANES-OVER-EDIT-LONG-SPECS-EVEN-WHEN-SURGICAL-CAP-THE-AUDITS-AND-LET-THE-SEAT-CLOSE
(the edit-scope half of the same problem) and
DSC:A-PATH-ONLY-REVIEW-COMMISSION-BUYS-DISCOVERY-NOT-JUDGMENT (why the independent pass
is itself easy to waste).
