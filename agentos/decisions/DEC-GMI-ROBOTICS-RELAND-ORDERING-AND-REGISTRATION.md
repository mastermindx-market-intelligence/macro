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
  import, with the composer itself staying free of third-party imports. (7)
  Merge is not acceptance, and a green main is not acceptance either. (10) No
  split re-land: the carrier re-lands whole, behind the shared foundation PR
  #7870, or not at all. Read-only retrieval of the reverted paths for
  measurement is permitted and does not violate ruling 10; adding any subset of
  them to main does. TWO AMENDMENTS, verified 2026-09-28 from the reverted
  carrier's own CI rather than from this record's prior reasoning. First, #7870
  is a HARD COMPILE DEPENDENCY, not a sequencing preference: four first-party
  symbols the Robotics modules import do not exist on main and all four exist at
  #7870's head, so ruling 10 is mechanically forced rather than merely prudent.
  Precisely, and corrected on review because an earlier draft said all four
  execute at import time: THREE do (composer :45 and :123, owner bundle :162),
  and the FOURTH is a DEFERRED, function-level site - owner bundle :197,
  engine.theme_graph.rights.load_registry_snapshot. The static AST sweep flags it
  anyway, which is the load-bearing point: deferring an import does not exempt it
  from tests/test_first_party_import_names.py, so the compile dependency is not
  escapable by moving a site inside a function. That is also why the slicing
  alternative below fails. Second, the re-land manifest is NOT the 35 reverted
  paths - it is those 35 paths PLUS CI wiring naming all six Robotics test
  suites by full relative path, because on the merged carrier all six were
  wired into no job and therefore never executed. Restoring only what the
  revert removed reproduces that defect exactly. THIRD AMENDMENT, 2026-09-28,
  and it makes the manifest three components rather than two: the carrier must
  also ENROL both Robotics modules in the deploy restart set. Ruling 6's lazy
  loader wrapper is precisely what removes them from the machine-checked import
  closure, so rulings 6 and 13 are a PAIR - satisfying 6 while skipping 13 ships
  a Robotics change that deploys and never goes live. Measured: the restart ERE
  at app/deploy/update.sh:1261 matches theme_research_registry.py,
  semiconductor_theme_research.py, theme_graph/rights.py and
  theme_graph/curation_assertion.py, and matches NEITHER
  engine/market_ontology/robotics_theme_research.py NOR
  engine/market_ontology/robotics_owner_bundle.py; and no MUST_RESTART list in
  tests/test_deploy_update_self_heal.py contains the string "robotics" at all.
rationale: >
  The revert exists because the carrier was merged 2m22s into its own CI run,
  before a single job had concluded, and that run then went red on the defects
  that mattered. Measured per job on 2026-09-28: run 36107534349 (ci,
  pull_request, attempt 1) started 2026-09-25T07:25:12Z on head d259ec08d58c;
  the PR merged at 07:27:34Z with ZERO jobs concluded and contract-delta alive
  for six seconds; contract-delta then failed at 07:37:21Z (+9m47s), ci-pack-4
  at 07:55:09Z (+27m35s), and the ci-gate adjudicator at 08:28:10Z (+1h00m36s).
  So merge-on-green merged on essentially no adjudicated evidence, and the run
  it outran found TWO independent defects rather than one. D1: ci-pack-4's
  failing step is
  tests/test_first_party_import_names.py::test_every_first_party_import_resolves,
  a static AST guard, and it names four absences - curation_assertion,
  semiconductor_theme_research, theme_research_binding, and
  rights.load_registry_snapshot - each present at #7870's head a0d7b054ff23 and
  absent on main. That sweep is deliberately not softened by a try/except,
  because its own guard synthesises a try-wrapped import to catch exactly that
  evasion, so the two try-wrapped sites get no exemption. D2: contract-delta
  reported all six Robotics suites as "a new pytest suite named by no run: step
  in any workflow", so 3729 lines of tests never executed; the revert's 35-path
  manifest contains no .github/ file, and that absence WAS the defect. Hence
  the ordering constraint is not stylistic AND the re-land manifest is not the
  revert inverted: both are measured causes of the revert. Ruling 10 follows because the dependent top-level import is the
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
      Measured and rejected. Counting carefully, because "three" and the four
      flagged symbols above are two different counts of two different things: CI
      flagged FOUR symbols across TWO modules (composer :45, :123; owner bundle
      :162, :197), of which THREE are import-time and one deferred, and they name
      THREE distinct #7870 modules (curation_assertion,
      semiconductor_theme_research / theme_research_binding, rights). The
      dependent subset is therefore not separable: one of the three modules is the
      shared assertion vocabulary imported at the composer's top level. Removing
      it leaves no semantics, and a function-level import would still be flagged
      by the static AST sweep - :197 is the proof, being exactly such a site and
      flagged regardless.
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
  - option: "Re-land exactly the 35 paths the revert removed - that restores the reverted change byte for byte."
    why_not: >
      REFUTED by measurement, and this is the most likely re-land mistake. The
      revert e5512ef66a74 is additions: 0 / deletions: 14404 over 35 paths,
      top-level split {agentos: 1, contracts: 1, engine: 2, research: 1,
      tests: 30}, with no .github/ entry anywhere. On the merged carrier all six
      new suites were named by no run: step, contract-delta failed on exactly
      that, and 3729 lines of tests never ran. Restoring the manifest verbatim
      restores the hole verbatim. The re-land must add CI wiring the original
      never had.
  - option: "Clear the unrun-suite gate by adding the six suites to the audit baseline, or by filing waivers for them."
    why_not: >
      Both are escape hatches that make the tests permanently unrun.
      gated_unrun_suites() is census minus baseline minus waivers
      (scripts/audit_unrun_tests.py:745), so either one turns contract-delta
      green while the 3729 lines stay dead - which is precisely the state that
      was reverted. Rejected on the record: the gate is correct and the carrier
      was wrong.
  - option: "Wire the suites with one glob, e.g. `python -m pytest tests/test_robotics_*.py`."
    why_not: >
      Does not satisfy the gate. Coverage is _named_by_a_run_step
      (scripts/audit_unrun_tests.py:591), a plain substring match of each
      suite's FULL relative path against the concatenated body of every
      workflow run: step, with the basename fallback disabled for basenames two
      suites share. A glob matches none of the six. All six full paths must
      appear literally - in a workflow file or in .github/ci/legacy-jobs.yml,
      which is explicitly appended to the scanned set (:450-451, :127).
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
  - "Macro run 36107534349 (ci, pull_request, attempt 1) on head d259ec08d58c: created/started 2026-09-25T07:25:12Z, completed/FAILURE 08:28:11Z. Per job via actions/runs/36107534349/jobs?per_page=100 --paginate: contract-delta failure 07:27:28Z->07:37:21Z, ci-pack-4 failure 07:31:23Z->07:55:09Z, trusted-ci skipped, ci-gate failure 08:28:01Z->08:28:10Z. pulls/7908 merged_at 07:27:34Z - 2m22s after the run started, with zero jobs concluded."
  - "Deploy restart coverage, measured 2026-09-28 at a0d7b054ff23 and main. Extracted the 2994-byte ERE literally from app/deploy/update.sh:1261 and tested paths with grep -E, the same engine the deploy uses. MATCH: engine/market_ontology/theme_research_registry.py, engine/market_ontology/semiconductor_theme_research.py, engine/theme_graph/rights.py, engine/theme_graph/curation_assertion.py, app/theme_research.py - five matches serving as the instrument's positive control, so the non-matches are meaningful. NO MATCH: engine/market_ontology/robotics_theme_research.py, engine/market_ontology/robotics_owner_bundle.py, and also semiconductor_owner_bundle.py, semiconductor_witness_scope.py, workspace_projection.py. Separately, grep -c robotics on tests/test_deploy_update_self_heal.py at main = 0, across MUST_RESTART (:248), ADMIN_MUST_RESTART (:479) and PRESS_MUST_RESTART (:595). The division is DESIGNED and the repo states it: the guard's own comment above _TRACKED_ROOTS says load-time imports are machine-checkable while request-time imports 'need human judgement ... and stay in MUST_RESTART', and _load_time_closure's docstring (:755-761) says deeper function-level imports 'live in the MUST_RESTART lists instead'. _load_time_closure seeds from every import in app/*.py then expands through MODULE-LEVEL imports only; the registry's lazy loader lives in engine/, so a module reached only through it is outside the machine-checked closure by construction. Ruling 11's design test applies and returns DESIGNED - stated contract plus named pins - so the gap is a missing manifest entry of mine, not a repo defect. Independently reported first by the Energy seat on #7870 comment 5866433049 for three semiconductor paths; I reproduced those three and extended the measurement to both Robotics modules."
  - "ci-pack-4 job 107985021309 via gh run view --repo {o}/{r} --job 107985021309 --log: the failing step is tests/test_first_party_import_names.py::test_every_first_party_import_resolves, reporting robotics_theme_research.py:45 engine.theme_graph.curation_assertion absent, :123 engine.market_ontology.semiconductor_theme_research absent, robotics_owner_bundle.py:162 engine.market_ontology.theme_research_binding absent, :197 engine.theme_graph.rights defines no load_registry_snapshot. Each probed at ?ref=a0d7b054ff23 (present) and ?ref=main (absent) by EXIT CODE, with agentos/README.md as positive control at both refs."
  - "contract-delta job 107983974666 via gh run view --log with terminal colour stripped: each of the six Robotics suites reported as '<suite> is a new pytest suite named by no run: step in any workflow - wire it into the job that owns its scope'; summary 'contract-delta: 6 introduced, 4 inherited (base 92e2f19513fb)'. Corroborated in pack4.log: zero pytest invocations of any Robotics suite."
  - "scripts/audit_unrun_tests.py at ref=main: :591 _named_by_a_run_step is a substring match of the full relative path with the shared-basename fallback disabled; :450-451 scans WORKFLOWS.glob('*.yml') plus an explicit append of CI_MANIFEST (:127) = .github/ci/legacy-jobs.yml; :745 gated_unrun_suites = census minus baseline minus waivers. main carries 237 legacy jobs, 165 gate:code / 72 gate:data, 160 code-gate jobs naming an explicit tests path."
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
The 2026-09-28 amendments add a fifth trap of the same shape, and it is the one I walked into
myself: treating the revert's own file list as the re-land manifest. Inverting a revert looks like
the definition of a faithful re-land, and it is exactly how the second defect gets restored -
because what the carrier was missing was never in the carrier to be removed.

# The falsifier

Ruling 6 and ruling 10 both stop applying the moment #7870's modules are on `main`. At that point
the ordering constraint is discharged, the re-land is a normal carrier, and the registration
becomes a normal additive commit - still subject to the lazy-wrapper requirement, which is
independent of #7870 and outlives it. The CI-wiring requirement also outlives #7870 and is
falsified differently: it is discharged the moment contract-delta reports 0 introduced unrun
suites on the re-land head, and it would be refuted as a requirement only by evidence that the
six suites are named by a run: step somewhere I did not scan - which means outside THREE surfaces,
not the two an earlier draft named: .github/workflows/*.yml, .github/ci/legacy-jobs.yml, and - added
after the theme-graph guard's own wiring turned out to hide there - the scripts/ci/*.sh shell sources
that those workflows' step bodies invoke. A suite named only inside a shell script a `run:` step
calls IS wired and would refute this requirement, while being invisible to a scan of the workflow
YAML alone. Any such find must be re-checked at the re-land head rather than at main, since the
census subtracts an evolving baseline. Ruling 7 has no expiry: it is discharged only by the real-path acceptance
evidence, not by any merge.
