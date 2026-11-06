---
key: ROBOTICS-SHARED-TYPE-MIRROR-IS-REUSE-NOT-CROSS-MOUNT
question: "The Robotics composer imports its shared types from `semiconductor_theme_research` and defines a local frozen mirror on the `except ImportError` branch. Is that the Semiconductor cross-mount the directive forbids, and is the mirror's fidelity guarded?"
answer: >
  It is REUSE, not a cross-mount, and it must be PRESERVED. The import direction follows
  contract ownership -- #7870 owns the shared composition types -- and the shared envelope is
  the whole point: the Robotics composer answers on the same envelope as
  `semiconductor_theme_research.v1` so one generic route and one client serve both verticals.
  Re-implementing the types inside Robotics would mint exactly the parallel shell the directive
  forbids.
  Two things are nonetheless true and neither was recorded. First, the `except ImportError`
  mirror is a SECOND definition of the shared types, and its fidelity is UNPINNED: zero of the
  17 tests in the Robotics temporal suite names the mirror, `SHARED_TYPES`, `OwnerBundle`,
  `ResearchQuery` or field order. Second, 8 of the 11 imported names are underscore-PRIVATE
  names of a sibling vertical, with a public export still pending from that seat.
  Ruling: keep the import, keep the mirror, keep the fallback. Add ONE equivalence pin, on the
  re-land base -- the only base where it can be written at all. Do not re-implement the types,
  do not fork them, and do not delete the fallback to make the seam look tidier.
rationale: >
  A cross-mount is a route, registry or mount answering another vertical's content. This is a
  compile-time type dependency pointing at the contract's owner, which is what "reuse its
  shared contract, registry, private route and client" requires. The census is unambiguous
  about the absence of the thing actually forbidden: `nuclear`, `energy`, `R-ENE`, `mining`,
  `defence`, `biotech` and a bare `semis?` all occur ZERO times in the Robotics composer, and
  `semiconductor` occurs exactly twice -- the docstring envelope note and this import. So no
  sibling vertical's review contract is imported and no second mount is touched.
  The mirror earns its place for a reason specific to this operation: it keeps the module
  importable, and its tests green, on a base WITHOUT #7870 -- which is precisely the base the
  re-land starts from. A hard import in this app closure has already failed four other teams'
  packs once; the `try`/`except` is the mitigation, not a shortcut.
  What the mirror does not have is a guard. Both mirrored types are `@dataclass(frozen=True)`,
  so positional construction is field-ORDER sensitive: if the owner reorders or renames a
  field, the mirror misbinds silently and nothing fails. Today it is faithful and that is
  measured, not assumed -- but "faithful today" is a measurement, not a contract.
  The pin is structurally impossible on either base ALONE, which is why its absence is not
  simple neglect. On a base without #7870 there is nothing to compare the mirror against. On a
  base with #7870 the `except` branch never executes, so the mirror classes are shadowed by the
  successful import and cannot be introspected. It becomes writable only by forcing the
  ImportError (patching `sys.modules`), re-importing the composer to capture the mirror
  classes, and comparing `__dataclass_fields__` against the owner imported normally. That test
  needs BOTH modules present -- it can exist only on the base the re-land creates, which is why
  it belongs to the re-land wave and not to a follow-up.
alternatives:
  - option: "Rule the sibling import a forbidden Semiconductor cross-mount and re-implement the shared types inside Robotics."
    why_not: >
      That builds the parallel shell the directive forbids, and it would create a THIRD
      definition of the shared contract. Mirroring a shared contract's shape from a local
      source is the wrong-oracle class that has already hit this very module twice -- once on
      authority flags, once on temporal keys. The import direction is correct because #7870
      owns the types.
  - option: "Delete the `except ImportError` mirror and let the composer hard-fail on a base without #7870."
    why_not: >
      A single hard third-party import in this app closure has already failed four other teams'
      packs. More narrowly, the mirror is what keeps the Robotics suite runnable on the
      re-land's STARTING base; removing it makes the re-land unable to prove itself until after
      the dependency lands, inverting the ordering this operation already ruled on.
  - option: "Rule the mirror DESIGNED and require no pin, since a contract is stated in both the docstring and the import comment."
    why_not: >
      Ruling 11's test needs BOTH a contract statement AND a pin whose NAME states the
      behaviour. The contract leg passes -- docstring and comment both state the mirror, its
      purpose and the pending public export. The pin leg fails at zero of 17 test names.
      Ratifying on the contract leg alone is how a defect acquires a certificate, which is the
      same error the `known_revisions` record rejects in its own first alternative.
evidence:
  - "engine/market_ontology/robotics_theme_research.py at 36efe9c92b96, 60749 B, sha256 7dcdbee913af67d7c33f0d62...: :122-137 is `try:  # pinned to #7870 c6c67c87` / `from engine.market_ontology.semiconductor_theme_research import (OwnerBundle, ResearchQuery, ResearchRefusal, _canonical_text, _is_instant, _is_retrospective, _le, _parse_clock, _parse_day, _passes_time_mode, _validate_query)` / `SHARED_TYPES = True`, then :138-139 `except ImportError:  # pragma: no cover - carrier base fallback` / `SHARED_TYPES = False`. 11 names imported, of which 8 are underscore-private. The comment at :118-119 states the contract: 'Shared types -- imported when the shared owner is on this base, mirrored locally (frozen, same field order) when it is not.'"
  - "Docstring :28-32 states the dependency and its pending resolution verbatim: private names 'are imported from the shared owner rather than re-implemented; a public export has been requested of that seat and is pending. A local frozen mirror of the shared types keeps this module importable (and its tests green) on a base without #7870.' Docstring :5-8 states the reuse requirement: the module 'Consumes the shared assertion contract and composition types from #7870 (c6c67c87) and answers on the SAME envelope as ``semiconductor_theme_research.v1`` so one generic route and client serve both verticals.'"
  - "No drift since authoring, and the comparison is not degenerate. `gh api repos/.../commits/<ref> --jq .sha` resolves c6c67c87 -> c6c67c878b86ebb02782e1dfd394809d8f724426 and a0d7b054ff23 -> a0d7b054ff2334739f8bd2abcfdc5943dd60ee74, two distinct commits. engine/market_ontology/semiconductor_theme_research.py fetched at BOTH with `-H 'Accept: application/vnd.github.raw'`: 47856 B each, sha256 722369b33d10753b5c9c814236667a79... IDENTICAL. So the owner's types have not moved between the commit Robotics pins and #7870's current head."
  - "Mirror fidelity TODAY, field by field: owner ResearchQuery = [anchor_theme_id, slice_key, view, time_mode, source_cutoff, recorded_cutoff, offset, limit, expected_generation] and mirror ResearchQuery is the same 9 names in the same order; owner OwnerBundle = [revision_tuple, rights_revision, assertions, identity_results, event_workspaces, financial_packets, interpretation_blocks, native_refs, omissions] and mirror OwnerBundle is the same 9 names in the same order. Both mirrors are @dataclass(frozen=True), so ORDER is load-bearing for positional construction."
  - "The fidelity is unpinned. In tests/test_robotics_research_temporal.py at 36efe9c92b96 (20345 B), `grep -cF` returns SHARED_TYPES=0, mirror=0, OwnerBundle=0, ResearchQuery=0, field_order=0, with ImportError=1 (the suite's own import guard). All 17 `def test_` names are temporal, replay, interpretation or identity cases; none names the mirror or the shared types. A never-written sentinel string in the same batch also returned 0, so the instrument fires rather than silently matching nothing."
  - "Cross-mount negative control, same file and same instrument: case-insensitive counts in the Robotics composer are nuclear=0, energy=0, R-ENE=0, mining=0, defen[sc]e=0, biotech=0, bare `semis?`=0, and semiconductor=2 at exactly :7 (docstring envelope note) and :123 (this import). CTRL_POS in the same run found 1 top-level class and 19 methods, so the file was genuinely scanned."
affects:
  - "WS:GMI-THEME-GRAPH"
  - "engine/market_ontology/robotics_theme_research.py"
  - "engine/market_ontology/semiconductor_theme_research.py"
  - "tests/test_robotics_research_temporal.py"
confidence: high
reversibility: easy
decided_by: "session 17c9f82c-8981-43d5-bf95-307691cb27cd (principal seat, operation gmi-robotics-fable-ceo-e2e-20260923-chairman-001)"
decided_at: 2026-09-29
---

The directive asked for one correct Robotics mount with no Semiconductor cross-mount. Reading
the composer for that answer surfaced a seam nobody had ruled on, and the two halves of the
answer point in opposite directions, so both are recorded here rather than only the reassuring
one.

**The import is the reuse, not the violation.** The forbidden thing is a Robotics route,
registry or mount answering Semiconductor content, or a second shell minted beside the shared
one. What exists is the opposite: Robotics consumes the owner's types and answers on the owner's
envelope so that one generic route and one client serve both verticals. Deleting the import to
make the vertical look self-contained would create the violation, not cure it.

**The mirror is a second definition of the shared types, and it is unguarded.** It is faithful
today -- 9 of 9 fields, in order, for both types, against an owner module proven byte-identical
at the commit Robotics pins and at #7870's current head. That is the strongest form the claim
can take and it is still a measurement of one moment. Both mirrored types are frozen
dataclasses, so a reordered or renamed field in the owner misbinds positionally with no import
error, no type error and no failing test.

**Why the pin is missing is more interesting than that it is missing.** It cannot be written on
either base alone. Without #7870 there is no owner to compare against; with #7870 the `except`
branch never runs, so the mirror is shadowed and uninspectable. The pin requires forcing the
ImportError, re-importing the composer to capture the mirror classes, and comparing
`__dataclass_fields__` against the owner imported normally -- which needs both modules present
at once. That is the re-land base. So this obligation belongs inside the re-land wave, in the
same way the CI job block and the restart-set enrolment do, and not to a follow-up that a green
merge would quietly retire.

**The private-name dependency is the part with no local remedy.** Eight of the eleven imported
names are underscore-private in the owner: `_canonical_text`, `_is_instant`,
`_is_retrospective`, `_le`, `_parse_clock`, `_parse_day`, `_passes_time_mode`,
`_validate_query`. Private names carry no compatibility promise by convention, and the composer's
own docstring records that a public export "has been requested of that seat and is pending."
Robotics cannot close that itself; the equivalence pin is what converts a silent future break
into a named failing test while the request is outstanding.

Falsifier: a base on which the owner's `ResearchQuery` or `OwnerBundle` differs from the
Robotics mirror in field set or field order, or a test whose name states the mirror's fidelity.
The first would move this from "unpinned but faithful" to "already drifted"; the second would
mean the pin leg of ruling 11's test is satisfied and only the private-name request remains.

So-what: get this wrong in the permissive direction and the two type definitions drift in
silence until a positional construction misbinds a field. Get it wrong in the strict direction
and someone re-implements the shared contract inside Robotics, which is the parallel shell the
directive exists to prevent and the third instance of a wrong-oracle defect in this one module.
