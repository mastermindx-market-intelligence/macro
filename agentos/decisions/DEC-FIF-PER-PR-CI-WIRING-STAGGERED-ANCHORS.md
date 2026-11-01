---
key: FIF-PER-PR-CI-WIRING-STAGGERED-ANCHORS
question: >
  Eight FIF lane PRs each add new pytest suites in one night against one
  shared CI manifest (`.github/ci/legacy-jobs.yml`, `engine-render-guards`).
  Wire the suites in one integration PR, via a glob in the run step, via
  waiver rows, or per-lane with staggered anchors?
answer: >
  Per-lane wiring: every lane PR carries its own final commit "FIF <lane>:
  wire <suite> into engine-render-guards (unrun-suite gate)" inserting its
  suite path(s) as LITERAL lines into the engine-render-guards folded run
  list, each after a DIFFERENT anchor neighbor, anchors at least 3 lines
  apart, so all eight merge without text conflicts.
rationale: >
  The unrun-suite gate is literal-match only
  (DSC:CONTRACT-DELTA-UNRUN-SUITE-GATE-IS-LITERAL-MATCH), so a new suite MUST
  be named literally in the owning run step in the same PR that adds it or
  contract-delta is red regardless of base freshness. Per-lane wiring keeps
  each PR independently green and independently revertable; the staggered
  anchors turn eight simultaneous edits of one 24k-line YAML file from a
  serial rebase train into eight conflict-free merges. One integration PR
  would couple eight lanes' merge fates and enlarge the blast radius of a
  red pack; a glob is invisible to the audit; waivers mean the tests never
  run.
alternatives:
  - option: one integration PR wiring all new suites after the lanes merge
    why_not: >
      Couples eight lanes' merge fates into one PR (a red pack or conflict
      blocks all eight), and every lane PR sits contract-delta red until the
      integrator lands — the opposite of independent, same-night merges.
  - option: a glob in the run step (e.g. pytest tests/test_fif_*.py)
    why_not: >
      The unrun-suite audit cannot see it — `_named_by_a_run_step` matches
      only a literal path substring of a run: scalar
      (scripts/audit_unrun_tests.py:604-607), so contract-delta stays red
      while the tests quietly do run; the audit is the point of the wiring.
  - option: waiver rows in config/unrun_test_waivers.yml
    why_not: >
      Waivers silence the gate, they do not run the tests — the suites would
      be dark in CI, and every future lane adds conflict-prone rows to one
      shared waiver file.
evidence:
  - "git diff hunk headers vs base 5267c66846e7 — insertion lines into .github/ci/legacy-jobs.yml engine-render-guards run list: e0=4385, t2=4390, x1=4394, c1=4397, d3=4403, s1=4406, s0=4409 — seven distinct anchors, minimum separation 3 lines"
  - "per-branch wiring commits: 8a233c4809 (T2), 471703401f (S0), 8e26477525 (S1-a), 06e0062862 (E0), 94d8f26487 (C1), de6ee6a2dd3c (D3, wires both suites), a6cff7a77c (X1) — each titled 'FIF <lane>: wire <suite> into engine-render-guards (unrun-suite gate)'"
  - "T1 (d4dcaba967d6) wires nothing: its suite tests/test_fundamental_forensics_cross_filing_lineage.py pre-exists on main (merged with #7518) and is already named at .github/ci/legacy-jobs.yml:4409 on main, so the unrun-suite gate does not apply to it"
  - "scripts/audit_unrun_tests.py:591-607 — _named_by_a_run_step literal-substring law; scripts/check_contract_delta.py:203,262 — contract-delta consumes gated_unrun_suites"
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - .github/ci/legacy-jobs.yml
  - scripts/audit_unrun_tests.py
confidence: high
reversibility: easy
decided_by: coo-fable (FIF e2e seat; wave-1 lane branches claude/fif-*-20261012, base 5267c66846e7)
decided_at: 2026-10-12
---

# FIF wave 1 — per-PR CI wiring on staggered anchors

Eight lanes, one shared CI manifest, one night. The shape that worked: each
PR carries its own suites' literal wiring, each after a distinct neighbor
line (measured insertions 4385/4390/4394/4397/4403/4406/4409 — ≥3 lines
apart), so the eight merges are textually independent. The eighth seat PR
(T1) extends a suite that already runs on main, so it needs no wiring commit
— the gate fires only on NEW suites. A future multi-lane night should copy
this exact pattern: assign each lane a distinct anchor region in the
engine-render-guards list BEFORE opening PRs, and wire literally, never by
glob.
