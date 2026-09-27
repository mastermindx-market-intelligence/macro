---
key: GMI-ROBOTICS-RELAND-ORDERING-AND-REGISTRATION
question: "After the Robotics implementation carrier merged and was reverted, how does it re-land, in what order, and when may its mount registration be added?"
answer: >
  Four rulings govern the re-land. (5) The Robotics mount partial is RETIRED:
  Robotics mounts by REGISTERING in the shared theme-research shell, never by
  shipping a vertical-specific partial. (6) Mount registration is POST-MERGE,
  because the shared registry imports a vertical's composer eagerly at
  registry-import time; and the registry entry MUST use a lazy loader wrapper
  that defers the owner-bundle import inside a function body, never a top-level
  import, with the composer itself staying free of third-party imports
  imports. (7) Merge is not acceptance, and a green main is not acceptance
  either. (10) No split re-land: the carrier re-lands whole, behind the shared
  foundation PR #7870, or not at all. Read-only retrieval of the reverted paths
  for measurement is permitted and does not violate ruling 10; adding any subset
  of them to main does.
rationale: >
  The revert exists because a carrier was merged while its correct CI run was
  still in flight - that run had been created 2m22s earlier against the correct
  base and failed four minutes later on exactly the defect. Eleven first-party
  import sites became unresolvable on a main lacking #7870's modules, and the
  repository's static import sweep is deliberately not softened by a
  try/except, because its own guard synthesises a try-wrapped import to catch
  that. So the ordering constraint is not stylistic: it is the measured cause of
  the revert. Ruling 10 follows because the dependent top-level import is the
  composer's assertion vocabulary - strip it and the carrier has no semantics
  left, so "land without the dependent modules" is void here rather than a
  standing escape hatch. Ruling 6's lazy-wrapper requirement is not defensive
  style either: the shell owner took 4-of-7 pack failures from exactly one hard
  top-level `import jsonschema` in that same app.main import closure, and
  repaired it by deferring the import behind an accessor. Post-merge the
  Robotics composer joins that closure, so a top-level import in the registry
  entry would reproduce a failure mode already observed on another team's lane.
  Ruling 7 is what keeps a merge from being read as completion: the operation's
  acceptance criterion is the real-path law in the master packet section 3, and
  a fixture-green composer, a 200 from the shared route, or a rendered shell is
  not the vertical.
alternatives:
  - option: "Re-land the carrier in slices, landing the parts that do not depend on #7870 first."
    why_not: >
      Measured and rejected. The dependent subset reduces to three sites on
      three modules, but one of them is a top-level import of the shared
      assertion vocabulary in the composer. Removing it leaves no semantics, and
      a function-level import would still be flagged by the static AST sweep.
      Slicing buys nothing and multiplies review surface.
  - option: "Land the registry entry now so the route is ready when the carrier re-lands."
    why_not: >
      The shared registry imports a vertical's composer eagerly at
      registry-import time, so an entry naming absent modules breaks every
      importer of that registry, including scripts/ and templates/ producers.
      Registration is strictly downstream of the carrier's modules being on main.
  - option: "Keep a Robotics-specific mount partial as the interim rendering path."
    why_not: >
      It had zero code referrers, re-emitted assets the shared partial now owns
      once, lacked a key the shared render gate requires, and gated on a context
      variable that exists nowhere on the merged tree - so it could never have
      rendered. It is also the partial-copying the shared-shell architecture
      ruling forbids.
  - option: "(none considered) treat the revert as a signal to rebuild the work."
    why_not: >
      All 35 reverted paths are retrievable at 36efe9c92b96, verified 35 of 35
      by exit-code test with a positive control. Rebuilding is duplicated work.
evidence:
  - "Macro PR #7908 MERGED 2026-09-25T07:27:34Z, merge commit 70b3c9f1f8f0"
  - "Macro PR #8013 revert e5512ef66a74, sole parent 36efe9c92b96, 35 paths removed"
  - "gh api repos/{o}/{r}/pulls/8013/files --paginate; then contents/<path>?ref=36efe9c92b96 and ?ref=main by EXIT CODE for each: retrievable=35, not_retrievable=0, present_on_main=0, instrument positively controlled"
  - "engine/market_ontology/theme_research_mounts.py:135 anchor_theme_id=\"ai_semiconductors\" (the only literal DECLARED anchor) and engine/market_ontology/theme_research_registry.py:169 _MOUNTS[\"ai_semiconductors\"] (the only ENROLMENT), both at #7870 head a0d7b054ff23"
  - "engine/theme_graph/curation_assertion.py 27838B at 1e38d5c955dc to 28610B at a0d7b054ff23: module-level import jsonschema plus eager Draft202012Validator replaced by a deferred _validator() accessor, pinned by test_unprovisioned_app_import_defers_biocatalyst_contract_runtime"
  - "Import audit of the Robotics modules at 36efe9c92b96, re-measured by AST walk 2026-09-27 after a column-anchored grep undercounted it: the composer (60749B) has 8 stdlib/__future__ imports plus TWO first-party ones that execute at import time - engine.theme_graph.curation_assertion at :45 and engine.market_ontology.semiconductor_theme_research at :123 inside a module-level try at :122 - and defers engine.theme_graph.identity at :68. The owner bundle (12407B) has 3 stdlib plus TWO import-time first-party - engine.market_ontology.robotics_theme_research at :156 and engine.market_ontology.theme_research_binding at :162 inside a module-level try at :161 - and defers engine.theme_graph.rights at :197. THIRD-PARTY imports anywhere in either file, deferred sites included: zero. A try-wrapped import still executes at import time and is not exempt from the repo static sweep; the two sites this audit first missed are named in #8013 own body among the four absences that broke main. Classify by AST parent chain, never by a line-anchored grep."
  - "agentos/handoffs/GMI-THEME-GRAPH-2026-09-27-robotics-reland-hold.md"
affects:
  - "WS:GMI-THEME-GRAPH"
  - "engine/market_ontology/robotics_*"
  - "engine/market_ontology/theme_research_registry.py"
confidence: high
reversibility: easy
decided_by: "session 17c9f82c-8981-43d5-bf95-307691cb27cd (principal seat, operation gmi-robotics-fable-ceo-e2e-20260923-chairman-001)"
decided_at: 2026-09-25
---

# Why this record exists separately from the handoff

The handoff that carried these rulings was itself removed from `main` by the revert, so the
rulings had no durable home. Sibling verticals in this program record their carrier-and-ordering
decisions as DEC records (`DEC-IND-FIRST-VERTICAL-CARRIER-AND-ORDERING`); Robotics had none among
the 368 on `main`. This closes that gap for the four rulings a successor is most likely to
violate, because each of them forbids something that looks locally reasonable: slicing a blocked
re-land, pre-staging a registry entry, shipping an interim partial, and reading a merge as done.

# The falsifier

Ruling 6 and ruling 10 both stop applying the moment #7870's modules are on `main`. At that point
the ordering constraint is discharged, the re-land is a normal carrier, and the registration
becomes a normal additive commit - still subject to the lazy-wrapper requirement, which is
independent of #7870 and outlives it. Ruling 7 has no expiry: it is discharged only by the
real-path acceptance evidence, not by any merge.
