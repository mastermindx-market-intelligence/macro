---
workstream: "WS:PROPHET-US-V4-RECOVERY"
session: 01a11e89-b35d-7a81-9404-5fce2c6170cb
model: sol
ended_because: ci_handoff
prs: [8444]
mission: Repair the candidate-pool public preview boundary on the existing P1a carrier within the full Prophet Daily Desk mission.
state_before: >
  Main-board and candidate-pool previews used independent ordering. A name
  withheld by the board could appear with its main-list score in the public pool.
  The P1a shared coverage macro also called a translation macro outside its scope.
changed:
  - path: scripts/build_site.py
    what: Both actual render passes supply the board-withheld rows; the pool preview stops before the first withheld identity and protected hydration preserves source order.
  - path: templates/_prophet_coverage.html.j2
    what: Import the existing Prophet card bilingual macro so independent coverage rendering works.
  - path: tests/test_us_board_gate.py
    what: Sixteen regressions cover actual initial/refreshed calls, panel gate combinations, population/order/count/digest preservation, normalization and bilingual escaping.
verified:
  - claim: The access regression failed for the actual disclosure before the splitter repair.
    command: python -m pytest tests/test_us_board_gate.py -k 'candidate_coverage_renders or candidate_pool_render_paths_respect_actual_board_boundary' -q
    result: Before splitter repair, eight access cases failed on public PAID identity; the separately repaired coverage case passed. After repair all nine passed.
  - claim: Adjacent source suites pass except the unchanged committed public page exposure.
    command: python -m pytest tests/test_us_board_gate.py tests/test_us_candidate_lanes.py tests/test_prophet_leader_observation_shelf.py tests/test_us_leader_observation_projection.py tests/test_dashboard_template_render.py -q
    result: 338 passed; one failure in unchanged test_shipped_shell_leaks_no_locked_ticker against the unrebuilt shipped artifact. No skipped tests.
  - claim: Real retained P1a source remains lossless through the repaired split.
    command: python /Volumes/Mastermind/evidence/prophet-r6-local-20261008-01a11e89/p1a-preview-review-capsule-20261011/probe.py /Volumes/Mastermind/evidence/prophet-r6-local-20261008-01a11e89/p1a-preview-review-capsule-20261011
    result: Eight actual-call-path fixture cases passed; separate committed-artifact probe preserved all 154 October 2 rows, counts, digest and order, with zero board-withheld identities in the public pool.
  - claim: Styling guards were preserved.
    command: python3 scripts/check_design_system.py --mode enforce-added --diff-file /Volumes/Mastermind/evidence/prophet-r6-local-20261008-01a11e89/p1a-preview-boundary-repair-20261011.diff; python3 scripts/check_runtime_style_injection.py; python3 scripts/check_ui_visual_evidence.py --diff-file /Volumes/Mastermind/evidence/prophet-r6-local-20261008-01a11e89/p1a-preview-boundary-repair-20261011.diff
    result: Zero new design findings, runtime style budget unchanged, mechanical visual guard passed. Not taste approval.
unverified:
  - claim: Independent review and current-main integration, qualified full visual proof and production acceptance.
    what_would_verify: Verified bounded review return, lawful reconciliation of the held integration operation, concluded checks, qualified combined screenshots and authenticated source-to-user journey.
unresolved:
  - The original same-workspace merge was explicitly refused before execution in PR8444 comment6029541334; this source-only repair does not retry or clear it.
  - The committed site has not been regenerated; its existing access test remains red and unchanged.
next_actions:
  - Finish the bounded source review on this original carrier and resolve concrete findings.
  - Reconcile the original integration boundary, then validate the combined source and visual evidence before normal release and HK/China adoption.
do_not_redo:
  - Do not fork the P1a programme, duplicate its PR, reroute the refused integration, or alter the access test to exempt the pool.
  - Do not drop or reorder entitled candidates, mutate source scores or manufacture entry/episode authority.
  - Do not poll already consumed B03 CI or merged B06 delivery again.
danger_areas:
  - Workspace manager PRESERVED_DIRTY is accounted for by 36 ignored caches while tracked Git status was clean; the caches were retained.
  - The retained October 2 artifact is local source evidence, not current production freshness or user acceptance.
---

This bounded repair continues Macro #6817 and #6805 on original P1a PR #8444,
starting from `60a494ed8c647c45712a13c8919e6d51c8b60905`. No merge,
producer recomputation, runtime installation or site regeneration was performed.
Full Prophet completion remains open. GitHub's current programme checkpoint
supersedes older pending-review states; this handoff records only this source delta.

Detailed logs and `p1a-preview-committed-artifact-probe-20261011.json` are retained
under the existing external-SSD Prophet evidence root. The declared dependency
environment gained Plotly, BeautifulSoup and lxml for the builder/template tests;
initial missing-dependency and undefined-translation runs are retained separately.
