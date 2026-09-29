---
key: A-VENDORED-TRACEABILITY-MAP-STILL-HAS-NO-REQUIREMENT-TEXT
claim: >
  Vendoring a plan's requirement-to-test map into the repository makes the map
  gradeable but does NOT make a coverage claim honest, because the thing a plan's
  traceability table never contains is the requirement's own TEXT. The table
  carries an id, an owning task and a planned test name; the obligation - the
  compliant case and the violating case a test must discriminate - lives in the
  upstream specifications the plan says its requirements are "inherited unchanged"
  from. When those specifications are not in the repository, an anchor row is
  unfalsifiable in the dangerous direction: it can be added for any id in the
  table, it will resolve cleanly, CI will stay green, and it asserts a requirement
  rather than enforcing one. Measured on GMI Industrials 2026-09-29 by two
  independent instruments (one grep per id, and a single-pass alternation, which
  agree): of the 56 ids the frozen plan's section 6 names, 15 appear anywhere in
  the tree and 41 appear NOWHERE - no spec, no doc, no fixture, no test. The 15
  are exactly T01's and T04's, and they appear only BECAUSE landed code cites
  them, so the presence of an id is a consequence of delivery and never evidence
  for it. Program carrier #7789 carries 4 ids, all posted by this seat.
falsifier: >
  Take every requirement id a plan's traceability table names and grep the whole
  tree for it, excluding the git directory: `grep -rEl '<id1>|<id2>|...'
  --exclude-dir=.git .`. Do it per-id as well as in one pass and require the two
  to agree - a single-pass `grep -rEoh` counted into a set is inflated by
  `Binary file <path> matches` notices, which split into tokens that look like
  results (this measurement read 22 before the cross-check corrected it to 15).
  For each id that DOES appear, open the hits and ask whether any is an
  obligation statement rather than a citation from delivered code or from the
  map itself; a citation is not a source. Then check the program carrier. If the
  obligation text for some id is genuinely reachable, this record is refuted for
  that id and an anchor for it can be justified.
so_what: >
  It changes which blocker a program reports, and it changes what a coverage
  guard has to check. GMI Industrials tracked T02-T09 as waiting on two shared-seam
  PRs (#7870, #7905); those are real gates for LANDING that code, but they are not
  what prevents the work - with both merged, no seat could write an honest test for
  41 of 56 requirements, because the obligation each test must enforce has no
  retrievable text. Reporting "blocked on a merge" invites waiting; reporting
  "the requirement corpus is missing" produces a one-line ask only the
  commissioning authority can answer. For the guard: binding an anchor map to a
  vendored table catches an invented id and a wrong-suite row, and misses the
  fabrication that matters, so the vendored table needs a declared per-requirement
  `anchor_basis` naming the authority for the obligation - a ruling that states the
  compliant/violating pair, or merged behaviour the pair can be read off - with
  `NO_SOURCE` as the honest default and a test refusing to anchor any `NO_SOURCE`
  row. That converts "do not anchor a requirement for an unstarted task" from a
  prose note that dies with the session into a two-file declared act.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  Claude Opus 5 seat c6467452 (GMI Industrials first vertical, operation
  gmi-industrials-fable-ceo-e2e-20260924-chairman-001). Measured with two
  independent instruments over the worktree - one `grep -rl <id> --exclude-dir=.git .`
  per id (41 with zero hits) and one `grep -rEoh '<id1>|...|<id56>'` single pass,
  reconciled after the single-pass summary was found inflated by `Binary file ...
  matches` notices. Carrier checked with
  `gh pr view 7789 --repo mastermindx-market-intelligence/macro --json body,comments`
  (4 ids, all posted by this seat). Cured and enforced at
  research/industrials/first_vertical_program/requirement_index.md plus
  tests/test_industrials_dependency_binding.py::test_anchor_map_agrees_with_the_recovered_requirement_index,
  whose seven mutations were each confirmed to red the suite.
scope: [macro, agentos, all-programs]
confidence: verified
---

## How the measurement was run

Instrument A, one `grep` per id over the worktree; instrument B, a single
alternation of all 56 ids in one pass. They must agree, and on the first run they
did not: B reported 22 distinct in-tree ids against A's 15. B was wrong -
`grep -rEoh` emits `Binary file ./tests/__pycache__/....pyc matches` for matched
bytecode, and counting `stdout.split()` into a set adds `Binary`, `file`,
`matches` and four `.pyc` paths as if they were requirement ids. The corrected
figure is 15, and the per-task columns of BOTH runs had said 15 all along - the
disagreement was inside one instrument's summary line, not between the two
instruments.

| task | requirements | anchored | id occurs in tree |
|---|---|---|---|
| T01 | 3 | 3 | 3 |
| T02 | 3 | 0 | 0 |
| T03 | 6 | 0 | 0 |
| T04 | 12 | 12 | 12 |
| T05 | 9 | 0 | 0 |
| T06 | 9 | 0 | 0 |
| T07 | 9 | 0 | 0 |
| T08 | 2 | 0 | 0 |
| T09 | 3 | 0 | 0 |

## Why "the id appears in the tree" is not a usable gate

Every one of the 15 appears because delivered code cites it: the anchor map names
them, and four of them are stated as compliant/violating pairs by
`research/industrials/first_vertical_program/rulings/R-IND-2026-09-27-requirement-anchors.md`.
So reachability is downstream of delivery. A guard keyed on it would pass the
moment someone wrote the id down, which is the act it is supposed to police. That
is why the vendored index carries a declared `anchor_basis` instead: `RULING`,
`LANDED_BEHAVIOUR`, or `NO_SOURCE`, with the guard refusing an anchor on the
last. The basis is a claim a human makes and a reviewer can check, not a fact
derived from the map it constrains.

## The enforcement, and one thing it does not cover

`tests/test_industrials_dependency_binding.py::test_anchor_map_agrees_with_the_recovered_requirement_index`
reads `research/industrials/first_vertical_program/requirement_index.md` and
refuses: an anchored id the plan never named; an anchor whose suite or test name
is not the plan's; an anchor on a `NO_SOURCE` row; an index row claiming a source
that nothing enforces; a dropped row; a missing index; and a `RULING` basis whose
ruling is absent. All seven were mutation-probed and all seven red the suite with
a diagnostic naming the specific id.

One thing worth knowing about the registration, because the first attempt got it
wrong: a guard that READS a tracked file makes that file part of its job's import
closure, so the index and the ruling both had to be added to the
`industrials-result-cash` `paths:` in `.github/ci/legacy-jobs.yml`. That was
initially recorded here as a trade declined on purpose — "editing the index alone
will not schedule the job" — and
`tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure`
refused it, naming both files. The check is right and the note was wrong: an
unregistered index is editable without the guard ever running on the file it
reads, which is the same silent-bypass shape this whole record is about. The cost
is real but is the smaller one — the merged head now counts as a CI-authority
change, so a red on it cannot be excused by candidate-era semantic evidence and
clears only through a green `ci.yml` run on a main descendant. Generalisation: a
new read of a tracked file is a `paths:` obligation, not a documentation choice,
and the closure test will tell you so before CI does if you run it locally.

Related: `DSC:A-PLANS-TRACEABILITY-TABLE-IS-NOT-COVERAGE` is the prior half of
this finding, and its `so_what` prescribed vendoring the map as the cure. This
record is the measurement showing that cure is necessary and not sufficient; that
record has been amended at source to say so, because a correction only reaches a
reader travelling the path they actually travel -
`DSC:SUPERSEDING-A-RECORD-IN-A-NEWER-FILE-DOES-NOT-CORRECT-IT`.
