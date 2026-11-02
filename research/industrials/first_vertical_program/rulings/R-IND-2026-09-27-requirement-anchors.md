# R-IND-2026-09-27 — Requirement anchors, and the four enforcement gaps building them exposed

Operation `gmi-industrials-fable-ceo-e2e-20260924-chairman-001`. Seat: Claude Opus 5 under the
Chairman's Meta-CEO delegation. Carrier: #7789.

## 1 — Why this ruling exists

Preparing the first delivery report on #7789, this seat set out to measure — rather than assert —
how many of the 56 inherited requirements T01 and T04 actually deliver. The frozen plan's §6
traceability table assigns one owning test per requirement and names it
`tests/<suite>::test_ind_<requirement>`. Running those exact node ids produced this:

> of the 15 anchors the table named for T01 and T04, **2 existed and 13 did not**, and the string
> `IND-` appeared **zero** times in either landed suite.

Both tasks were merged, both suites were green (103 tests), and nothing in the repository could
resolve a single row of that table. The two anchors that did exist (`test_ind_sf01`,
`test_ind_sf07`) exist because the plan additionally froze their BODIES verbatim — not because the
table named them. Wherever only the table named the test, the implementing lane wrote a
descriptive name and the anchor silently never came into being.

The mechanism is worth stating plainly because it defeats every instrument in normal use: a pytest
run names FILES, so a missing test is not a failing test — `pytest path::absent` reports
`ERROR: not found` and `no tests ran`, a shape that never occurs in CI because CI runs whole files.
The table itself lives in a document on a research branch, so no test, hook or job reads it. And
`grep` for the requirement id finds nothing either, because nothing obliged the lane to write the
id into the test: there was no second, weaker traceability mechanism standing behind the table.
Recorded fleet-wide as `DSC:A-PLANS-TRACEABILITY-TABLE-IS-NOT-COVERAGE`.

**Ruling 1.** "15 of 56 requirements delivered" may not be reported from a table that assigns 15
rows. A program reports the coverage it MEASURED, and measurement is per requirement: does some
assertion distinguish this requirement's compliant case from its violating one? Coverage-by-NAME
and coverage-by-BEHAVIOUR are independent facts and a green suite proves neither.

## 2 — Method: build the anchors rather than audit for them

Auditing the landed suites by name was tried first and is the wrong instrument — it answers "is
there a test that looks related", which is exactly the judgement that lets a weak owner be counted
as a delivered requirement. This seat inverted it: **construct each missing anchor from the
requirement's own text.** Then coverage is demonstrated by tests that can be pointed at, and any
requirement whose anchor cannot be made to pass honestly is a genuine gap found by construction.

Four were.

Two method notes that cost time and are worth carrying:

- **The permissive-receipt trap.** The synthetic helper `comparison(purpose, cells)` sets every
  `checked` flag `True`, so a probe built on it legitimately excuses every comparability mismatch.
  A first probe suite "found" D07/D08/D15 gaps that were artifacts of the probe's own receipt. The
  landed idiom — used by `test_qualify_operands_refuses_duration_mismatch` — is to build the
  receipt and then set the ONE flag under test `False`; the anchors carry it as `_unchecked()`.
- **`metric` encodes the period ROLE in this corpus** (`revenue_current` / `revenue_prior`), not
  measure semantics. A first attempt at the D09 guard compared `metric` equality and broke eight
  landed tests. Those tests were right and the cure was wrong: the MEASURE lives in
  `quality.definition`. Corrected before anything was committed.

## 3 — The four gaps, each invisible because its anchor never existed

Every one was `ready` with an empty `limitations` list before the cure — not a wrong number behind
a warning, but a clean answer to a question the module should have refused.

| Req | Situation | Landed behaviour | Cure |
|---|---|---|---|
| **IND-D08** | USD thousands against USD millions | `ready`, `value="30"` | compare `unit`, refuse `unit_mismatch` unless the receipt declares the magnitude **and** carries the conversion |
| **IND-D09** | total revenue against net-of-reimbursement revenue | `ready`, `value="10"`, `label="reported"` | refuse `definition_mismatch` when the two `quality.definition` values disagree |
| **IND-D10** | matched legs of 5 and 7 | `ready`, `label="company_adjusted"`, `pretax_after_pairing="92"` vs the matched pair's `"90"` | refuse `matched_pair_unequal` |
| **IND-R208** | a receipt declaring `same_period` fed to a year-over-year derivation | `ready`, `value="10"` | compare the receipt's declared purpose with the purpose being qualified, refuse `purpose_mismatch` |

D08 is the sharpest of the four and shows why name-based auditing could never have found it. T01's
`cell()` fixes `scale` at 1 and lets `unit` carry the reporting magnitude, so `_scales_compatible`
only ever sees `{1}` — a scale check existed, read as the guard for this requirement, and was
structurally incapable of seeing the situation the requirement names. The anchor asserts that
`scale_mismatch` is **not** raised, so the reason the old guard was blind is now pinned by a test.

D10 is the one found purely by construction: the module already enforced both-or-neither on
operand PRESENCE, which reads like the requirement. It never compared the two legs' AMOUNTS, so an
unmatched pair was netted and the result attributed to the issuer as `company_adjusted`.

**Ruling 2.** All four cures land. Blast radius measured at zero: 103 landed tests unchanged, and
the suites go 103 → 118.

## 4 — Two named follow-ons this ruling does NOT close

Stated as scope lines rather than left implicit, because both are places where the module trusts a
declaration it does not re-derive:

1. **A declared unit conversion is trusted, not applied.** With a factor of `0.001`, 130 thousands
   against 100 millions honestly grows about **-99.87%**; the module returns `"30"` — it compares
   raw decimal text and takes the receipt's word that magnitudes were reconciled upstream. That is
   a deliberate boundary (this module is the arithmetic surface and does not own unit algebra) and
   is now asserted by `test_ind_d08_conversion_receipt_is_trusted_not_applied`, so implementing the
   conversion FAILS that test and forces the anchor to be updated on purpose rather than drifting.
2. **A declared comparable duration is trusted, not re-derived.** D07 refuses quarter-against-half
   only while the receipt leaves `duration` undeclared. That is IND-R208's rule working as
   written — "different dates allowed only under a declared comparable-duration purpose" — and the
   declaration is the authority. Whether the module should also re-derive duration from the period
   bounds belongs to whoever owns the receipt producer, not to T04.

Neither is a defect against the frozen requirements. Both are recorded so a later lane does not
have to rediscover them.

## 5 — The cure for the table itself

A ruling that only fixed four formulas would leave the next lane inheriting the same silence. So
the table stops being prose on a branch:

- `PLAN_REQUIREMENT_ANCHORS` in `tests/industrials_result_cash_helpers.py` vendors the 15 T01/T04
  rows into the repository.
- `test_every_plan_named_requirement_anchor_exists` resolves every row by AST — not by import or
  `getattr`, so a row cannot be satisfied by a name that merely happens to be reachable — and
  asserts the map's own size, since an empty map would pass every loop inside it.
- Both suites are already on the exclusive `industrials-result-cash` (`gate: code`) job's `paths:`
  and run line, so this needs no `.github/ci/**` edit. Deleting or renaming an anchor now reds that
  job.

**Ruling 3.** Adding a row is a CLAIM: it asserts the named test discriminates the requirement's
compliant case from its violating one, not merely that some test touches the same code. Rows for
requirements owned by tasks that have not started do not belong in the map — their absence is the
honest signal. T02's `tests/test_industrials_issuer_enrollment.py` is still deliberately not
created for the same reason.

## 6 — Evidence

```
MACRO_MASTERMIND_REPO=/nonexistent MACRO_TERMINAL_REPO=/nonexistent \
  python3 -m pytest tests/test_industrials_dependency_binding.py \
                    tests/test_industrials_result_cash.py -q
118 passed
```

Mutation matrix, 17 mutations over the four cures and the enforcing test:
**17 caught, 0 survivors**, each by its intended anchor, suites clean before and after restore.
Six mutations were caught by the new anchor **only** — no landed test failed for them — which is
the measurement that the D08 unit check, the D09 definition-agreement check, the D10 unequal-pair
guard, D12's metric-based operand selection, D13's computed-value discipline and R208's purpose
comparison were genuinely unprotected before this increment.

Coverage after this increment, stated as measured: **15 of 56 inherited requirements carry a named,
mutation-proved owning anchor** (3 in T01, 12 in T04). The remaining 41 belong to T02, T03, T05–T09,
which are unstarted and gated behind #7870 and #7905.

## 7 — Corrections this seat made to its own earlier statements

Recorded because a ruling that hides them is less useful:

- A subagent that died at its turn limit left the module mutated in the working tree, and this seat
  raised an alarm that a mutation marker had reached `main`. Verified against `origin/main`: it had
  not. **The alarm was wrong**; the mutation was working-tree only, was restored with
  `git checkout --`, and every probe was re-run against clean code with identical results.
- The first D09 cure compared `metric` equality and broke eight landed tests. The tests were right.
- `git ls-tree` presence was briefly read as evidence that a PR touches a file. It is not — every
  commit's tree contains every tracked file, and `ls-tree` exits 0 on no match. Contestedness is
  measured with `git diff --name-only origin/main...<head>`.

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
