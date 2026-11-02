---
key: EVIDENCE-CORPUS-IS-A-GATED-SURFACE
question: "Should mockups/evidence/** and mockups/refs/** (the TP-0 receipt corpus) be a CI-gated surface, and if so how is the gate made startable without breaking the records-only exemplar?"
answer: "Yes. The design-governance job carries a declared 9-path floor over the receipt corpus (legacy-jobs.yml, directly after gate: code, deliberately NOT scope: exclusive) and ci.yml carries two trigger entries (mockups/evidence/**, mockups/refs/**) so the declared scope is startable; tests/test_ci_pack.py pins that an evidence-only edit selects design-governance. The incident-7958 records-only exemplar in tests/test_merge_on_green.py is re-pointed at handoff-only files (R4), because by design that test fails whenever a new path-filtered gate covers its fixture."
rationale: "Before #8287 an evidence-only diff ran only ci-pack-0 + ci-gate: design-governance's scope was DERIVED (templates/builders) plus runtime discovery, so the corpus it actually tests was never in its startable scope. #8278 (MO-PAID-008 proof, final head 4d79d52d696e) landed a receipt whose EVIDENCE.yml pointed at an ad-hoc manifest and turned main red on ci-pack-6 for every sibling (healed by #8285 0c7c9a2f591c). A declared scope must be startable by ci.yml (test_derived_scopes_are_startable_by_the_ci_workflow), hence BOTH the paths floor AND the trigger entries; a job's own tests file is wired only if some job's run line names it (the contract-delta job reds a PR otherwise, measured on #8284 R1)."
alternatives:
  - option: "Drop the trigger entries and keep the paths floor only"
    why_not: "the declared scope is then not startable by ci.yml and the planner test fails; it also re-opens the #8278 path where an evidence-only PR runs no corpus test at all"
  - option: "Make design-governance scope: exclusive"
    why_not: "four planner tests fail (measured in the R3 lane); exclusivity would also stop the pack from running alongside template edits that need it"
  - option: "A mockups/** blanket trigger"
    why_not: "not startable as declared (mockups/ holds non-evidence design files) and it would pull every mockup edit into the receipt gate"
  - option: "Keep the 7958 exemplar's evidence fixture and whitelist the new gate"
    why_not: "the test's whole point is 'this fixture owns no path-filtered gate'; a whitelist would make the exemplar silently vacuous (R4 re-exemplar instead)"
evidence:
  - "PR #8287 (CI_DESIGN_GOVERNANCE_EVIDENCE_SCOPE R3 head 149e6c156c94, R4 head cb6656f0369c) MERGED 6f9937a94481 2026-10-02T19:43:07Z by hand with --match-head-commit; blob-verified against bare-fetched origin/main"
  - "R3 lane gates: test_ci_pack 144 passed / 2 skipped; derived-scope startability 46 passed; contract-delta 0 introduced; 2528 triggers startable"
  - "incident: #8278 4d79d52d696e malformed receipt -> main red ci-pack-6 -> heal #8285 0c7c9a2f591c (README 17 lines == frozen spec, EVIDENCE.yml removed)"
  - "contract-delta on #8284 R1: 'tests/test_build_sanctions_map_no_path_stamp.py is a new pytest suite named by no run: step' (run 37021529030 job 110885543268)"
  - "program file research/MARKET_ONTOLOGY_CEO_A_CONTINUATION_HANDOFF_2026-10-02.md rulings D37, D40, D42, D44"
affects:
  - "WS:MARKET-OS"
  - ".github/ci/legacy-jobs.yml"
  - ".github/workflows/ci.yml"
  - "tests/test_ci_pack.py"
  - "tests/test_merge_on_green.py"
  - "mockups/evidence/**"
  - "mockups/refs/**"
confidence: high
reversibility: easy
decided_by: "CEO A seat 587e986f-b055-4df2-a9ed-ca3a709fcc5b (Claude Fable 5.1), single F00 writer under the Astra handoff on macro#6819"
decided_at: 2026-10-02
---

## Why this is a decision, not a heal

The heal (#8285) fixed one malformed receipt. The decision is that the receipt corpus is a
*gated surface*: any PR that adds or edits a TP-0 receipt runs the receipt-corpus test, and
the exemplar that asserts "records-only PRs own no path-filtered gate" must stay honest by
excluding evidence captures from its fixture. Standing packet rule derived from D37: a
packet that CREATES a `tests/*.py` file wires it into the owning legacy-jobs.yml job
(`paths:` + `run:`) in the SAME commit.
