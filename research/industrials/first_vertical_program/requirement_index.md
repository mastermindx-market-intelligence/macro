# Industrials first vertical — requirement index (recovered)

The frozen implementation plan lives only on a research branch: its section 6
traceability table has never existed on `main`, so no test, guard or reviewer
could resolve a requirement id against it.  This file is that table, recovered
verbatim from plan blob `a5462dc7f36aea08c57ce43a8a230ef00ebae802` (`scratchpad/ind_plan.md`,
section 6 "Requirement-to-task and test mapping"), plus ONE added column.

## What the added column is for

`anchor_basis` names the authority that would justify an anchor row in
`tests/industrials_result_cash_helpers.py::PLAN_REQUIREMENT_ANCHORS`.  An anchor
row asserts that a named test discriminates the requirement's compliant case from
its violating one.  That claim needs the obligation's text, and **the plan's table
does not contain it** — it carries an id, an owning task and a planned test *name*.
The requirement texts are inherited "unchanged from r1/r2/W12", and those
specifications are not in this repository.

- `RULING` — a program ruling states the compliant and violating case in prose.
  Source: `rulings/R-IND-2026-09-27-requirement-anchors.md`.
- `LANDED_BEHAVIOUR` — the module and suite are merged on `main`, so the pair can
  be read off the code itself.
- `NO_SOURCE` — **neither exists.**  The obligation's text is not reachable from
  this repository or from the program carrier, so an anchor row for it would be
  inventing the requirement rather than enforcing it.
- `RECOVERED_ORIGINAL` — the obligation's **exact original wording** is readable at
  a named blob.  Added 2026-09-29 after Sol's CONTINUE ruling (#7789 comment
  `5894127980`) recovered the corpus from the original branch history at commit
  `40d91e50a38c604e26255c1451eda5ddc95fb9cc` on
  `sol/industrials-sector-research-20260923`.  This is the STRONGEST basis of the
  four: `RULING` and `LANDED_BEHAVIOUR` both reconstruct the pair from something
  downstream of the obligation, while this one quotes the obligation itself.
  - r1 blob `40fd1e3783102c28fe748fe35b927484d4f3dddb` — `IND-D01`–`IND-D30`
  - r2 blob `9c98e106b954d0a48610afad418de2a9eeb1e58b` — `IND-R201`–`IND-R218`
  - W12 blob `b343cbd7bc1f52cfc6fbb5e18ab8d9e9f9392f6c` — `IND-SF01`–`IND-SF08`

  None of the three is vendored at any path on `main`, which is what made a
  main-only path lookup read as absence.  Verified by reading each blob directly:
  30 + 18 + 8 = 56 unique ids, zero missing and zero extra.

## Measured 2026-09-29 (historical — superseded the same day)

Two independent instruments (one grep per id, and a single-pass alternation)
agree: of the 56 ids this table names, **15 appear anywhere in the tree and 41
appear nowhere** — no spec, no doc, no fixture, no test.  The 15 are exactly the
T01 and T04 rows, and they are present only *because* landed code cites them.
Carrier #7789 carries 4 ids, all posted by this seat.

**That measurement is still accurate about this repository and is no longer the
whole picture.**  It measured presence *in the tree*, and Sol's CONTINUE ruling
later the same day recovered the obligation texts from the original branch history
— so "appears nowhere in the tree" turned out to mean *not vendored on `main`*, not
*lost*.  The conclusion drawn from it at the time, that 41 obligations have no
retrievable authority, is superseded; the count itself is unchanged.  Rows migrate
from `NO_SOURCE` to `RECOVERED_ORIGINAL` one substantive change at a time, never in
a bulk edit, because the basis column is a claim that something enforces the row.

```
task   reqs  anchored  id-in-tree
T01       3         3           3
T02       3         0           0
T03       6         0           0
T04      12        12          12
T05       9         0           0
T06       9         0           0
T07       9         0           0
T08       2         0           0
T09       3         0           0
```

**The consequence is a different blocker than the one this program recorded.**
T02-T09 were tracked as waiting on #7870 and #7905.  Those are real gates for
*landing* shared-seam code, but they are not what prevents the work: even with
both merged, no seat could write an honest test for 41 of these requirements,
because the obligation each test must enforce has no retrievable text.  The
unblock is not a merge — it is the r1/r2/W12 requirement corpus (a path, or blob
shas), which only the commissioning authority can supply.

## Index

Requirement, owning task and planned exact test are verbatim from the plan.
`anchor_basis` is this file's own column.

| Requirement | Task | Planned test file | Planned test | anchor_basis |
|---|---|---|---|---|
| IND-D02 | T01 | `tests/test_industrials_dependency_binding.py` | `test_ind_d02` | LANDED_BEHAVIOUR |
| IND-D06 | T01 | `tests/test_industrials_dependency_binding.py` | `test_ind_d06` | LANDED_BEHAVIOUR |
| IND-SF07 | T01 | `tests/test_industrials_dependency_binding.py` | `test_ind_sf07` | LANDED_BEHAVIOUR |
| IND-D04 | T02 | `tests/test_industrials_issuer_enrollment.py` | `test_ind_d04` | NO_SOURCE |
| IND-D05 | T02 | `tests/test_industrials_issuer_enrollment.py` | `test_ind_d05` | NO_SOURCE |
| IND-R210 | T02 | `tests/test_industrials_issuer_enrollment.py` | `test_ind_r210` | NO_SOURCE |
| IND-D01 | T03 | `tests/test_industrials_source_facts.py` | `test_ind_d01` | NO_SOURCE |
| IND-R203 | T03 | `tests/test_industrials_source_facts.py` | `test_ind_r203` | NO_SOURCE |
| IND-R204 | T03 | `tests/test_industrials_source_facts.py` | `test_ind_r204` | NO_SOURCE |
| IND-R205 | T03 | `tests/test_industrials_source_facts.py` | `test_ind_r205` | NO_SOURCE |
| IND-R206 | T03 | `tests/test_industrials_source_facts.py` | `test_ind_r206` | NO_SOURCE |
| IND-R207 | T03 | `tests/test_industrials_source_facts.py` | `test_ind_r207` | NO_SOURCE |
| IND-D07 | T04 | `tests/test_industrials_result_cash.py` | `test_ind_d07` | LANDED_BEHAVIOUR |
| IND-D08 | T04 | `tests/test_industrials_result_cash.py` | `test_ind_d08` | RULING |
| IND-D09 | T04 | `tests/test_industrials_result_cash.py` | `test_ind_d09` | RULING |
| IND-D10 | T04 | `tests/test_industrials_result_cash.py` | `test_ind_d10` | RULING |
| IND-D11 | T04 | `tests/test_industrials_result_cash.py` | `test_ind_d11` | LANDED_BEHAVIOUR |
| IND-D12 | T04 | `tests/test_industrials_result_cash.py` | `test_ind_d12` | LANDED_BEHAVIOUR |
| IND-D13 | T04 | `tests/test_industrials_result_cash.py` | `test_ind_d13` | LANDED_BEHAVIOUR |
| IND-D14 | T04 | `tests/test_industrials_result_cash.py` | `test_ind_d14` | LANDED_BEHAVIOUR |
| IND-D15 | T04 | `tests/test_industrials_result_cash.py` | `test_ind_d15` | LANDED_BEHAVIOUR |
| IND-D16 | T04 | `tests/test_industrials_result_cash.py` | `test_ind_d16` | LANDED_BEHAVIOUR |
| IND-R208 | T04 | `tests/test_industrials_result_cash.py` | `test_ind_r208` | RULING |
| IND-SF01 | T04 | `tests/test_industrials_result_cash.py` | `test_ind_sf01` | LANDED_BEHAVIOUR |
| IND-D17 | T05 | `tests/test_industrials_source_history.py` | `test_ind_d17` | NO_SOURCE |
| IND-D18 | T05 | `tests/test_industrials_source_history.py` | `test_ind_d18` | NO_SOURCE |
| IND-D19 | T05 | `tests/test_industrials_source_history.py` | `test_ind_d19` | NO_SOURCE |
| IND-D20 | T05 | `tests/test_industrials_source_history.py` | `test_ind_d20` | NO_SOURCE |
| IND-D21 | T05 | `tests/test_industrials_source_history.py` | `test_ind_d21` | NO_SOURCE |
| IND-D24 | T05 | `tests/test_industrials_source_history.py` | `test_ind_d24` | NO_SOURCE |
| IND-R209 | T05 | `tests/test_industrials_source_history.py` | `test_ind_r209` | NO_SOURCE |
| IND-SF02 | T05 | `tests/test_industrials_source_history.py` | `test_ind_sf02` | NO_SOURCE |
| IND-SF03 | T05 | `tests/test_industrials_source_history.py` | `test_ind_sf03` | NO_SOURCE |
| IND-D03 | T06 | `tests/test_industrials_financial_dossier.py` | `test_ind_d03` | NO_SOURCE |
| IND-D22 | T06 | `tests/test_industrials_financial_dossier.py` | `test_ind_d22` | NO_SOURCE |
| IND-D23 | T06 | `tests/test_industrials_financial_dossier.py` | `test_ind_d23` | RECOVERED_ORIGINAL |
| IND-R201 | T06 | `tests/test_industrials_financial_dossier.py` | `test_ind_r201` | NO_SOURCE |
| IND-R213 | T06 | `tests/test_industrials_financial_dossier.py` | `test_ind_r213` | NO_SOURCE |
| IND-R214 | T06 | `tests/test_industrials_financial_dossier.py` | `test_ind_r214` | RECOVERED_ORIGINAL |
| IND-R215 | T06 | `tests/test_industrials_financial_dossier.py` | `test_ind_r215` | RECOVERED_ORIGINAL |
| IND-R218 | T06 | `tests/test_industrials_financial_dossier.py` | `test_ind_r218` | NO_SOURCE |
| IND-SF04 | T06 | `tests/test_industrials_financial_dossier.py` | `test_ind_sf04` | NO_SOURCE |
| IND-D25 | T07 | `tests/test_industrials_private_publication.py` | `test_ind_d25` | NO_SOURCE |
| IND-D26 | T07 | `tests/test_industrials_private_publication.py` | `test_ind_d26` | NO_SOURCE |
| IND-D27 | T07 | `tests/test_industrials_private_publication.py` | `test_ind_d27` | NO_SOURCE |
| IND-D28 | T07 | `tests/test_industrials_private_publication.py` | `test_ind_d28` | NO_SOURCE |
| IND-R211 | T07 | `tests/test_industrials_private_publication.py` | `test_ind_r211` | NO_SOURCE |
| IND-R212 | T07 | `tests/test_industrials_private_publication.py` | `test_ind_r212` | NO_SOURCE |
| IND-R216 | T07 | `tests/test_industrials_private_publication.py` | `test_ind_r216` | NO_SOURCE |
| IND-R217 | T07 | `tests/test_industrials_private_publication.py` | `test_ind_r217` | NO_SOURCE |
| IND-SF06 | T07 | `tests/test_industrials_private_publication.py` | `test_ind_sf06` | NO_SOURCE |
| IND-R202 | T08 | `tests/test_industrials_theme_research_view.py` | `test_ind_r202` | NO_SOURCE |
| IND-SF05 | T08 | `tests/test_industrials_theme_research_view.py` | `test_ind_sf05` | NO_SOURCE |
| IND-D29 | T09 | `tests/test_industrials_result_cash_journeys.py` | `test_ind_d29` | NO_SOURCE |
| IND-D30 | T09 | `tests/test_industrials_result_cash_journeys.py` | `test_ind_d30` | NO_SOURCE |
| IND-SF08 | T09 | `tests/test_industrials_result_cash_journeys.py` | `test_ind_sf08` | NO_SOURCE |

## How this file is enforced

`tests/test_industrials_dependency_binding.py` reads this table and refuses an
anchor map that disagrees with it: every anchored requirement must appear here,
its suite and test name must equal the plan's, and a requirement whose
`anchor_basis` is `NO_SOURCE` may not be anchored at all.  Adding an anchor for
one of the 41 `NO_SOURCE` rows therefore requires editing this file to name a
real source in the same change — a declared act, not a one-line drift.

This file and the ruling named above are both in the `industrials-result-cash`
job's `paths:`, so editing either one schedules the job that runs the guard.
That registration is not bookkeeping and was not optional: the suite READS both
files, so `tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure`
fails without it -- correctly, because an unregistered index could be edited
without the guard ever running on the file it reads.  The cost is that the merged
head counts as a CI-authority change (`.github/ci/**`), so a red on it cannot be
excused by candidate-era evidence and needs a green `ci.yml` run on a main
descendant.

