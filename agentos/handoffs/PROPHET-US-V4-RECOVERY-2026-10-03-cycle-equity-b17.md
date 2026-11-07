---
workstream: "WS:PROPHET-US-V4-RECOVERY"
session: sol/prophet-cycle-equity-v1-20261001
model: sol
prs: [8308]
ended_because: ci_handoff
mission: >
  Implement B17/Q08 funding, dilution and original-equity recovery mechanics on
  top of existing capital_need/share-count owners, with honest missingness and
  no stock-ranking or trading authority. MISSION_COMPLETE:false.
state_before: >
  B17/Q08 was specified but not built. Existing capital_need.v1 exposed validated
  annual cash/debt context and Capital Structure owned share-count/event truth,
  while the Cycle macro diagnostic and ALFRED producer were separate draft lanes.
changed:
  - path: engine/prophet_cycle_equity.py
    what: >
      NEW pure Cycle funding/original-equity engine: dated funding path, cash-floor
      breaches, equity/debt financing transmission, recovery price hurdles,
      canceled-security distribution handling, inventory-vs-sales diagnostic, and
      bounded user explanation. All financial authority false.
  - path: tests/test_prophet_cycle_equity.py
    what: >
      NEW focused regression suite covering restricted cash, maturity-before-recovery,
      dilution/proceeds, cohort subscriptions, debt conversion, canceled old shares,
      purchase-price hurdles, inventory/sales counterexample, native capital_need.v1
      consumption, and explanation boundaries.
  - path: .github/ci/legacy-jobs.yml
    what: >
      Register the new suite in the existing render/engine guard lane beside
      capital_need/cash_runway. No new job or dependency.
  - path: research/prophet_v4/cycle_equity_v1/README.md
    what: >
      Exact mechanism, source-owner reuse, source gaps, hypothetical discriminating
      case, capability limits and next native source/adoption step.
  - path: research/prophet_v4/cycle_equity_v1/fault_discrimination.json
    what: >
      Three mutation receipts proving tests catch discarded equity proceeds,
      erased interim funding breaches and dilution-blind purchase hurdles.
verified:
  - claim: New Cycle engine and incumbent finance stack pass together.
    command: >
      python3.12 -m pytest tests/test_prophet_cycle_equity.py
      tests/test_capital_need.py tests/test_cash_runway.py -q
    result: "292 passed, 4 unrelated pytest cleanup warnings, 0 failures; log SHA256 b59584053f07278a52f69d8a6ac02c2c3eb92da5ca625804e2b7fdb3f55854f9."
  - claim: Existing capital_need.v1 output is consumed without rederiving its cash/debt facts.
    command: TestNativeCapitalNeedIntegration
    result: >
      assemble_capital_need output with exact cash/debt source contract reaches
      FUNDED_TO_RECOVERY under an explicit complete no-event schedule.
  - claim: Critical mechanics are discriminated by tests.
    command: local bounded mutation driver
    result: >
      3/3 intended assertion failures; source restored. Receipts in
      research/prophet_v4/cycle_equity_v1/fault_discrimination.json.
unverified:
  - claim: Real source-qualified financing events and restricted-cash coverage.
    what_would_verify: >
      Exact admitted issuer financing/obligation records from the incumbent
      Capital Structure source owner, including clocks, proceeds, claims and
      restricted-cash semantics.
  - claim: User-facing production Cycle dossier.
    what_would_verify: >
      Existing Prophet/D5/product consumer wired to one source-qualified B17 case,
      authenticated served proof, and a normal refresh/correction-history witness.
  - claim: Improved Cycle selection or customer returns.
    what_would_verify: >
      Existing Evaluation owner runs the same-population source-qualified study,
      preserving failed firms, dilution, canceled securities, costs and timing.
unresolved:
  - "Current Capital Structure projection explicitly withholds active instruments, remaining capacity, fully diluted shares and financing probability; do not infer them from filing presence."
  - "No native restricted-cash join for B17 was found at the implementation source base."
  - "Financing events in this engine are scenario assumptions unless an incumbent source owner supplies exact admitted facts."
  - "Cycle macro PRs #7868/#7871 retain their original custody; this path is distinct."
next_actions:
  - "Commit/push this B17 source carrier and consume exact-head CI."
  - "Bind one real issuer's existing capital_need/share-count facts plus exact source-qualified financing/obligation terms; do not create a new financing store."
  - "Project that case into the incumbent Prophet/D5/product path and prove the authenticated ordinary refresh."
  - "Only after source readiness, register the same-population Q08/B17 incremental evaluation under the existing Evaluation owner."
do_not_redo:
  - "Do not reopen or reinterpret protected Cycle macro outcomes from #7868/#7871."
  - "Do not replace capital_need, cash_runway, debt_maturity, share-count truth or Capital Structure with a second owner."
  - "Do not treat a financing filing, shelf registration, assumed raise, or high recovered enterprise value as proof the original shares recover."
  - "Do not splice replacement-security performance onto canceled old shares."
  - "Do not convert scenario arithmetic into a probability, rank, size, automatic average-down rule or buy permission."
danger_areas:
  - "Restricted cash must be established as included/excluded from reported cash before liquidity claims."
  - "A later financing event cannot cure a prior cash-floor breach retroactively."
  - "Equity proceeds and new shares must both be included; debt proceeds and debt claims must both be included."
  - "Original-holder participation in later financing requires its additional cash contribution in the denominator."
  - "Incomplete schedules remain unavailable even when listed events reconcile."
---

# B17 / Q08 Cycle original-equity continuation

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false

This handoff records a built-not-proven source unit only. It transfers no source
lease, worker operation, trial budget, market permission or automatic wake.
