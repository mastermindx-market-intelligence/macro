---
key: GMI-THEME-GRAPH-SUITES-RUN-ONLY-IN-THE-DATA-HEALTH-LANE
claim: >
  The theme-graph hierarchy, probation-hierarchy, crosswalk, hierarchy-population and
  identity suites live in the legacy job `unrun-intl-libraries`, which is `gate: data` in
  .github/ci/legacy-jobs.yml. ci.yml merge packs run `scripts/run_ci_pack.py --gate code` and
  never select it. Only data-health.yml (`--gate data`) runs it, and its red goes to the
  standing data-health issue (#5979) without blocking any merge. A legacy job stops at its
  first failing step, so once an earlier step (the identity-resolution suite) went red, the
  later steps (local_plane, rights_use, probation_hierarchy, theme_sources_registry) stopped
  running at all. A data-health "success" can also be vacuous: run 38119256612 skipped its
  data-pack matrix. By contrast `gmi-classification-axes` is `gate: code` and runs on every
  merge.
falsifier: >
  The YAML gate of `unrun-intl-libraries` in legacy-jobs.yml reads `code`; or a ci.yml
  ci-pack log lists it under "Selected jobs:"; or a data-health job log shows steps after the
  first `##[error]unrun-intl-libraries: step '<name>' exited 1` still executing.
so_what: >
  A green merge gate says nothing about these suites. Before claiming a theme-graph change is
  tested, run the suites yourself on a composed tree (main + head). Read data-health job logs,
  not run conclusions, and check that the matrix actually ran. A red identity step hides every
  step after it.
kind: landmine
verified_at: 2026-10-12
verified_by: >
  GMI Meta-CEO seat 6f14c2da: YAML parse of legacy-jobs.yml on origin/main d89fdf72f85d
  (unrun-intl-libraries gate=data, gmi-classification-axes gate=code); scripts/run_ci_pack.py
  DISABLED_IF (:83) and GATE_VALUES (:99-103); ci.yml `--gate code`; data-health.yml
  `--gate data`; data-health job 114639390187 log; run 38119256612 jobs API.
scope:
  - macro
  - .github/ci/legacy-jobs.yml
  - scripts/run_ci_pack.py
  - .github/workflows/data-health.yml
  - tests/
confidence: verified
cited_by:
  - WS:GMI-THEME-GRAPH
---

Moving the hermetic theme-graph suites onto a code-gate job is an open question for the
workstream. It needs a whole-pack weight check and the contract-delta literal-match rules
(DSC:CONTRACT-DELTA-UNRUN-SUITE-GATE-IS-LITERAL-MATCH) before anyone tries it.
