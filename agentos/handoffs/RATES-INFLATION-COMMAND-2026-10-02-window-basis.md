---
workstream: WS:RATES-INFLATION-COMMAND
session: claude/ssd-regime-window-basis-20261002-f915359b3743a2e4
model: sol
ended_because: ci_handoff
mission: >
  Continue granular regime intelligence under existing parent 7088. Qualify the
  transformation inputs of the existing historical regime builder without making
  a reconstructed label into a historical forecast or changing live numeric policy.
state_before: >
  Existing pit_class described only current source coverage. A lagged payroll
  trend could depend on revised pre-coverage data while the row said pit_vintage.
  Chat context 8257 and readiness 8301 were published; their final CI is now green
  but whole-PR independent acceptance and release remain unproven.
changed:
  - path: scripts/build_regime_v2_pit.py
    what: >
      Added slow-component window-basis annotations to the existing frame, sidecar
      and CLI. Preserved numeric owners, legacy columns and sole output paths.
  - path: tests/test_regime_v2_pit.py
    what: >
      Added lag/smoothing/missingness/prefix and actual builder/CLI regressions,
      including unchanged numeric history and legacy basis verification.
  - path: config/synapse.yml
    what: Documented additive fields on the existing source contract, not a new writer.
  - path: .github/ci/legacy-jobs.yml
    what: Enrolled the old history suite in the existing unrun-scoring-engine code job.
  - path: config/unrun_test_baseline.json
    what: Removed exactly that newly enrolled suite from the shrink-only baseline.
verified:
  - claim: Source-level failure reproduced before implementation.
    command: python3 -m pytest tests/test_regime_v2_pit.py -q -k window_basis
    result: >
      The full recorded discriminating selection had 16 failures before the new
      function and CI enrollment existed; exact selection/log scope is in the receipt.
  - claim: History and seasonality campaign passes within its recorded data scope.
    command: python3 -m pytest tests/test_regime_v2_pit.py tests/test_seasonality_pit_spine.py -q
    result: >
      85 passed, 12 existing full-store skips, 239 warnings. Actual source transport
      fixtures exercise real alignment, axes, classifier, flags, builder and writers.
      No full-store or production qualification is implied.
  - claim: Forbidden mutations are distinguished by consumer tests.
    command: isolated in-memory pytest variants recorded in window_basis_verification_20261002.json
    result: >
      Current-only endpoints caused five failures, omitted smoothing one, and
      disconnected serialization two. Source files were not mutated.
  - claim: Actual saved macro input support exposes the original blind spot.
    command: >
      Exact git-show input capture at b4f95f98ef80b8cbb4636afbd723b5091658e1f1,
      native feature alignment and slow-component calls, macro_window_provenance,
      and prefix equality assertion; full receipt is in the sibling research JSON.
    result: >
      Reduced five-economic-source/SPY-grid diagnostic: 8785 rows, 65 current-vintage
      rows with revised transformation inputs; prefix identical. No outcomes, model
      fit, provider call, canonical data write or complete-market replay.
unverified:
  - claim: Independent exact-source review, current-base CI and release.
    what_would_verify: >
      A non-author semantic verdict plus current candidate checks and integration,
      followed by ordinary authorized release and actual artifact readback.
  - claim: Complete historical regime and predictive utility.
    what_would_verify: >
      Full source/vintage/model/state/issuance qualification and separately
      preregistered explicit-horizon evaluation through existing owners.
unresolved:
  - The new source candidate still requires independent review and current-head checks.
  - Existing 8257/8301 candidates are not deployed; scoped reviews are not whole-PR approval.
  - Initial-release data is not full-vintage information or intraday source availability.
  - 7871 owns activity-series full-vintage collection; no duplicate collector is allowed.
next_actions:
  - Publish and read back this same source branch and Draft/HOLD PR; qualify current-head checks.
  - Obtain exact-source review; preserve both this suite and 8301's suite during CI composition.
  - Continue existing source-vintage and history owners without taking over their source writers.
do_not_redo:
  - Do not repeat the broad census, frozen rejected studies, or the 8257 production capture.
  - Do not rename current input-window support as full replay eligibility or historical issuance.
  - Do not change numeric regimes, capital rules, existing coverage gates, or raw data for this repair.
  - Do not rebuild 7871's collector or copy an API key into this environment.
  - Do not reuse old passing checks for changed semantic code, self-approve, or merge on pending CI.
danger_areas:
  - Sticky-CPI support includes both rolling means and their actual non-null contributors.
  - Missing activity is unknown, not no_active; known absent vintages mean revised fallback.
  - The metadata dependency description is pinned by tests to the actual scoring/smoothing owners.
  - Tests skipped for absent full stores remain skipped; the synthetic CLI is not live proof.
---

# Working continuation

MISSION_COMPLETE: false. Capability: BUILT_NOT_PROVEN.
Operation: regime-window-basis-20261002-astra-001.
Base: b4f95f98ef80b8cbb4636afbd723b5091658e1f1.
Procedure: Mastermind bdf2a972e68a70270c24d4b5d61a4d60edc4f288.
Source workspace was created through the installed external-SSD storage owner.
No prior source writer, active modifier or unknown effect was displaced.
Exact-path PR search returned no competing build_regime_v2_pit.py proposal.
Known adjacent 7015/7165/8133/8303 paths are disjoint; estate-wide clearance is not claimed.

Execution is direct: NO_ELIGIBLE_PRE_EFFECT_WORKER for this bounded source repair;
current Executive read has no running Job and has not supplied a new admission or
reviewer result. No Job, worker START, watcher or background Web execution is claimed.
Existing 8257/8301 source heads remain frozen and clean. The new subset evidence
returned on those PRs is preserved, with their whole-PR review requests still open.

This checkpoint accompanies code and evidence; it does not finish the mission,
transfer custody, authorize a source replay, or release any production/merge hold.
