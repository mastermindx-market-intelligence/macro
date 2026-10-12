---
workstream: WS:MARKET-OS
session: claude/intelligence-network-demand-audit-20260919-sol-001
model: sol
ended_because: ci_handoff
mission: Advance the Chairman's Intelligence Hub/root intelligence-network modernization through existing owners; deliver a reproducible real-data demand-coverage and availability diagnostic without changing production scoring or creating duplicate planes.
state_before: The initial research masterplan identified static app-demand rules and presentation caps, but had no reproducible frozen-data coverage measurement. Existing sponsorship, Hub UX and Defense Intelligence carriers were already open.
changed:
  - path: research/intelligence_network/demand_audit.py
    what: Added an aggregate-only local-Git audit calling the incumbent app rule and distinguishing availability, cohort changes, counter decreases and invalid/conflicting inputs.
  - path: research/intelligence_network/demand_audit_feed_cutoff_2026-09-18.json
    what: Real retained-data proof at the feed cutoff, including exact data and baseline-function hashes.
  - path: research/intelligence_network/demand_audit_latest_observed_2026-09-19.json
    what: Separate later-cutoff proof; no later observations are injected into the earlier result.
  - path: research/intelligence_network/CONTINUATION_2026-09-19.md
    what: Froze measured findings, rights limitations, incumbent ownership, graph/model/data-use obligations and the context-only product successor's negative tests.
  - path: tests/test_intelligence_network_demand_audit.py
    what: Added 24 adversarial research-contract tests; no live provider fixture is required.
  - path: .github/ci/legacy-jobs.yml
    what: Added the suite to the existing qledger/altdata test owner; its normal import exposes the research dependency; no new job, workflow, runner or schedule.
verified:
  - claim: Initial missing diagnostic reproduced 20 expected test failures, followed by 20 passing implementation tests.
    command: python3 -m pytest tests/test_intelligence_network_demand_audit.py -q --tb=short
    result: Red due to the explicit missing-auditor assertion; green after implementation.
  - claim: New and incumbent altdata intelligence suites pass together.
    command: python3 -m pytest tests/test_intelligence_network_demand_audit.py tests/test_altdata_intel.py -q --tb=short
    result: 44 passed; six warnings including unrelated old shared-pytest cleanup permissions and the intentionally invalid infinite-counter baseline case.
  - claim: The exact expanded registered CI test step passes locally.
    command: python3 -m pytest tests/test_altdata_reboot_families.py tests/test_altdata_ledger_lane_gate.py tests/test_intelligence_network_demand_audit.py -q
    result: 101 passed; one RuntimeWarning from the incumbent baseline on the deliberate infinite-counter negative fixture.
  - claim: Availability-screened real observations reproduce the 312 strong, 15 displayed, 297 excluded app-rule split.
    command: python3 research/intelligence_network/demand_audit.py --git-repo . --source-ref a1334a1a6c154b9b49664ee892d9710742fc6018 --observed-by 2026-09-18T18:41:09.971423Z
    result: 177035 available rows; 1810 later-observed rows excluded; latest source date Sep 17; 732 eligible provider ticker keys. JSON receipt preserves hashes.
unverified:
  - claim: Hosted CI, independent review and protected-main acceptance of this research delivery.
    what_would_verify: Concluded exact-head checks and accepted review on this same branch/PR; do not claim a queued job is executing.
  - claim: Any new customer-facing app-data permission or deployed product behavior.
    what_would_verify: Specific written commercial-use scope under the existing rights owner, followed by native producer/consumer and authenticated production proof on an approved successor.
unresolved:
  - No scope-specific Quiver commercial agreement was established. A narrow mailbox search with no match is not proof no agreement exists.
  - The public Hub read redirected to sign-in and the Opera connector was disconnected; no authenticated product acceptance was attempted.
  - Macro 7305, 7361 and 7175 remain incumbent carriers; their current gates must be reconciled before integration. No workers or watchers were created here.
  - Root data/synthesis/graph/model/product completion is still owed; this is a research capability and source-grounded continuation, not parent acceptance.
next_actions:
  - Finish the same research carrier's validation/publication and consume exact-head review without rebuilding the audit or changing existing production scores.
  - Reconcile 7305's current merge and natural SEC-source proof; reuse its named-evidence path instead of opening a rival sponsorship implementation.
  - After app-source rights and custody are clear, implement the existing per-ticker context-path expansion with the negative tests in CONTINUATION_2026-09-19.md; broader context must not alter admitted convergence votes or rankings.
  - Advance the federal-demand and relationship requirements through incumbent 7175 and GMI/K3-D/F04 owners; preserve their existing holds and source identities.
do_not_redo:
  - Do not replay the initial research history or reconstruct this pinned census without a material invalidator; use the two hashed receipts and executable audit.
  - Do not create replacement insider, procurement, graph, identity, outcome, retry, runtime or publication planes.
  - Do not reinterpret 297 excluded app-rule keys as 297 missed trades or promote the static rule as learned predictive quality.
  - Do not remove the display cap by feeding new unvalidated voting channels into production.
danger_areas:
  - Source Time and first-seen clocks differ; later observations cannot be backfilled into an earlier decision.
  - Provider labels are not resolved issuer/app identities; absent apps, counter decreases and corrections are not automatically business demand changes.
  - The current collector preserves first values but discards later same-key corrections; zero retained conflicts does not prove zero source corrections.
decisions: [DEC:INTELLIGENCE-NETWORK-FEDERATED-CONTINUATION-2026-09-19]
discoveries: [DSC:ALTDATA-APP-ANALYTICAL-CAP-2026-09-19]
---
