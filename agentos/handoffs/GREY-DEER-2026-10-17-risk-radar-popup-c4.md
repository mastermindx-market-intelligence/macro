---
workstream: WS:GREY-DEER-RISK-INTELLIGENCE
session: sol/web-risk-radar-popup-20261017-c4
model: sol
ended_because: ci_handoff
mission: >
  Deliver the Chairman-authorized Macro Risk Radar popup replacement from the
  Paper redesign through normal release and served verification. This is the
  source-implementation checkpoint; the same session retains release custody.
state_before: >
  The existing popup stacked the risk brief, probabilities, internals, drivers,
  signal ladder and secondary research. Paper improved the visual hierarchy but
  still overloaded the first view with explanatory text.
changed:
  - path: templates/_risk_radar_workspace.html.j2
    what: Add the inert overview/inspector shell and a guarded display projection of existing US/SPY odds and matched history.
  - path: templates/risk_radar_workspace.js; site/risk_radar_workspace.js
    what: Enhance the existing dialog, move native evidence and live-hook nodes, add horizon/driver/context navigation and accessible return behavior.
  - path: templates/risk_radar_workspace.css; site/risk_radar_workspace.css
    what: Add scoped Macro token styling, responsive layouts, visible focus and reduced-motion treatment.
  - path: templates/dashboard.html.j2
    what: Add three Macro-only asset/partial hooks and fix the absent-scare conditional closing boundary.
  - path: tests/test_risk_radar_workspace.py; tests/risk_radar_workspace_browser.py
    what: Add template boundaries and a reproducible isolated full-page interaction and anonymous component evidence harness.
  - path: .github/ci/legacy-jobs.yml
    what: Register the new suite and partial in the existing dashboard-render-contract code gate, including its execution step.
  - path: tests/test_recurring_briefs.py
    what: Repair the sole remaining CI failure with exact complete-translation contracts and source-faithful partial-translation checks; leave producer and generated data unchanged.
  - path: mockups/evidence/risk-radar-workspace-20261017
    what: Preserve canonical theme/language/viewport and hover/focus captures, source hashes and browser results.
verified:
  - claim: All affected template and Risk Radar tests pass.
    command: python -m pytest tests/test_risk_radar_workspace.py tests/test_risk_envelope_radar_integration.py tests/test_dashboard_template_render.py -q --disable-warnings --maxfail=1
    result: 133 passed, 2 warnings in 134.62 seconds using /tmp/rkw-verify-20261017/bin/python.
  - claim: The isolated browser covers first-open priority, native modal return, source-node identity, navigation, missing odds, mobile geometry and reduced motion.
    command: python tests/risk_radar_workspace_browser.py --source-ref d7c2316d1626b980cd17224bb090a4b6f17d6141 --output /tmp/rkw-final-preview-20261017
    result: 49 checks passed; zero JavaScript exceptions.
  - claim: The canonical anonymous component matrix is captured.
    command: python scripts/capture_page_evidence.py --registry /tmp/rkw-final-preview-20261017/page_registry.json --site-dir /tmp/rkw-final-preview-20261017 --routes /risk-radar-component.html --repo macro --output-dir mockups/evidence/risk-radar-workspace-20261017 --manifest mockups/evidence/risk-radar-workspace-20261017/manifest.json --smells mockups/evidence/risk-radar-workspace-20261017/smells.json --viewports desktop,mobile --locales en,zh --themes dark,light --force-state 'driver_hover:hover(.rkw-driver:first-child)' --force-state 'horizon_focus:focus(button[data-rkw-horizon="21"])' --settle-ms 450
    result: 24/24 captures; the fixture uses actual Macro CSS and rendered source snapshots without a saved session or production route.
  - claim: The recurring-briefs suite distinguishes complete and partial source translations without masking missing rows.
    command: python -m pytest tests/test_recurring_briefs.py -q --disable-warnings --maxfail=1
    result: 78 passed on the carrier artifact and again with immutable main artifact 1aeaf6874e4d3ed8d4f76205c236994ec7a3bcb9; both original failures reproduced on CI baseline 4cb9007a6 and current main. Two translation-loss/index-shift mutations were caught. Exact receipts are in ci-repair.json.
unverified:
  - Updated PR checks, merge, normal rendered main output and served production bytes remain release steps at this checkpoint.
  - No authenticated production visual session is available through the connected Browser extension in this conversation.
  - Editable Paper boards were not updated; the connector's current write catalog is unapproved.
unresolved:
  - Complete final staged guards, source convergence, PR/CI and the covering normal render; do not call source completion live delivery.
  - Held pullback/recovery/alert architecture remains with its existing owners and acceptance gates.
next_actions:
  - Commit and push the owned carrier, create the ordinary PR, then wait for concluded binding checks before normal merge.
  - Observe the existing render lane and verify a successful covering main descendant plus served macro.html hooks and asset bytes.
  - Record the exact release evidence on the same PR and report the Paper and authenticated-browser limitations honestly.
do_not_redo:
  - Do not acquire another carrier or retry the explicitly refused Fabric child through another pool; this source workspace is already owned and usable.
  - Do not rebuild a second risk score, forecast engine, live poller or alert authority in the browser.
  - Do not re-fetch the Paper archive or copy its illustrative future drawdown numbers into production data.
danger_areas:
  - Native risk state, stance, probability calibration and missing-data warnings remain source-owned; partial internals must not suppress a known warning.
  - Preserve existing registration, modal controller and live DOM IDs. A registered view must remain secondary on first open; unknown owner panels remain visible.
  - Parallel owner work includes Macro PR 9428; reconcile actual overlapping source without taking over or merging held sibling work.
  - Use the owned SSD worktree and the normal render/VPS path; no occupied primary checkout, shared stash, Vercel or duplicate active render dispatch.
---

# Risk Radar implementation checkpoint

Paper source: https://app.paper.design/file/01M38EVF74SJWG1GANN5VP380Z
(`Mastermind · Market Dashboard Popups · Redesign`). The primary US and mobile
Risk Radar boards informed the layout; native accepted source readings drive
the implementation.

Workspace: `/Volumes/Mastermind 2/agent-workspaces/macro/web/risk-radar-popup-20261017-c4`.
Initial source/data reference: `d7c2316d1626b980cd17224bb090a4b6f17d6141`.
Native thread: `01a1487f-fc7b-7068-a24a-3e3f91a910e6`.

The overview prioritizes state, reason and current stance; separates the signal
index from SPY ≥5% pullback probability; and keeps thin-history qualifications
adjacent to odds. Four comparable drivers open one inspector. Sentiment,
leadership, volatility, signals and source/method views preserve native content.
Calendar's illustrative numeric bars are removed while its seasonal evidence
remains available.

A final fresh-open visual inspection caught the unknown-panel safeguard
mistaking registered evidence for a future source panel. The fix excludes
registered view identities, with explicit first-open regression checks.
