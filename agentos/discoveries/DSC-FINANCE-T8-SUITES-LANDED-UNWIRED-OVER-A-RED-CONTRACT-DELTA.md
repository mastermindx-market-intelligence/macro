---
key: FINANCE-T8-SUITES-LANDED-UNWIRED-OVER-A-RED-CONTRACT-DELTA
claim: >-
  Finance T8 (#7952, merged 2026-09-24T16:11Z) was merged while contract-delta was
  FAILURE. Its two ::error annotations named the PR's own new suites,
  tests/test_finance_intelligence_page.py and tests/test_finance_intelligence_hydration.py,
  as suites named by no run: step, and ci-gate was also FAILURE. Every later
  contract-delta then classed both suites as "inherited", so the gate went quiet and
  neither suite ran in any CI until #8010 added a run step and paths: entries to the
  finance-intelligence job.
falsifier: >-
  Read gh api repos/mastermindx-market-intelligence/macro/check-runs/107730270902/annotations,
  which must show the two failure annotations. Then, on main after #8010, run python3 -c
  "from scripts.audit_unrun_tests import gated_unrun_suites; print([s for s in
  gated_unrun_suites() if 'finance' in s])", which must print [].
so_what: >-
  Before any hand or --admin merge of a Finance PR, read every red check's annotations,
  not its name. A red contract-delta is never spurious by default, because it names the
  exact suites. Any new tests/test_finance_*.py must be named in the finance-intelligence
  job's run: step AND its paths: in the same PR.
kind: landmine
verified_at: 2026-09-25
verified_by: "check-run 107730270902 annotations; gated_unrun_suites() at 034d73be (#8010) lists no finance suite"
scope:
  - macro
  - .github/ci/legacy-jobs.yml
  - tests/test_finance_intelligence_*.py
confidence: verified
---
