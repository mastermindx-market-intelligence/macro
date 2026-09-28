---
workstream: WS:MARKET-OS
session: claude/commodities-wti-eia-slice-a-20260927
model: sol
ended_because: ci_handoff
mission: 'Implement the first frozen Commodities R2/North Star convergence slice: existing WTI/EIA physical
  evidence with truthful clocks, degraded states and source inspection in the current commodity detail
  view. Continue Macro issue 8049.'
state_before: Published b19a3b2 implemented WTI/EIA Slice A. Independent review returned an invalid-score
  categorical-label defect and missing persisted screenshot/page binding; hosted contract-delta identified
  the new test suite as unwired.
changed:
- path: scripts/build_commodities.py
  what: Bind oil-only physical evidence into sector detail. Keep quote, analysis, observation and evaluation
    clocks separate. Publication/receipt instants remain unknown when absent. Reject invalid/future/mismatched-source
    evidence, preserve real zero, withhold mixed-period composite and isolate read errors.
- path: templates/_commodity_oil_physical.html.j2
  what: Add bilingual physical reading, truthful stale/partial/absent/error states, native source/method
    disclosure and direct EIA attribution link.
- path: templates/commodities.html.j2
  what: Oil-only include and shared-token styling. Fix incumbent warning-row mobile overflow without hiding
    content or changing scores or shared navigation.
- path: agentos/decisions/DEC-EIA-SPR-RIGHTS.md
  what: Record the narrow direct EIA-authored petroleum reuse basis and translation, attribution and third-party
    exclusions. Other vendor rights remain untouched.
- path: mockups/evidence/commodities-wti-slice-a
  what: Canonical eight rest and eight actual keyboard-focus browser cells, selected visual crops, source/effect
    boundaries and exact verification command report.
- path: .github/ci/legacy-jobs.yml
  what: Register the WTI suite in the incumbent unrun-macro-panels command and subject paths; no new job,
    dependencies, or waiver.
- path: scripts/capture_commodities_wti_slice_a.py
  what: Validate actual HTTP response bytes and page stability against the bound generated file. Do not
    rely on arbitrary observed metadata that the canonical serializer drops.
verified:
- claim: Independent-review categorical defect reproduced then repaired through the incumbent balance
    method.
  command: python3 -m pytest tests/test_commodities_r2_wti_physical.py -q
  result: 'Selected review cases: 9 failed/1 passed before changes; full WTI suite51 passed afterward.
    Finite valid scores map via the existing owner; invalid/missing scores cannot retain Tight.'
- claim: The introduced unwired-suite finding is removed without a waiver.
  command: scripts.audit_unrun_tests.gated_unrun_suites()
  result: Before one finding (WTI); after no findings. Existing owner command had947 passing tests before
    the ten additional review cases; final serialized rerun pending at source-commit preparation.
unverified:
- Fresh canonical capture must be made after this repaired source and generated page are committed; historical
  screenshot target did not bind the integrated page.
- New-head hosted CI and independent rereview; merge, deployment, full visual/accessibility and live acceptance.
- 'Whole repository suite not green: previously observed missing marketdesk_extractor package at collection.'
- Research-case attachment/persistence remains Slice B, not implemented.
unresolved:
- Current cached EIA observation lacks publication and receipt timestamps; do not synthesize them.
- Shared assistant-launcher overlay is inherited global UI; not part of this slice.
next_actions:
- Finish serialized owner/CI checks and commit the repaired source plus regenerated page on this same
  branch.
- Capture canonical16-cell evidence from that immutable source commit; verify source/page/driver identities
  and commit evidence-only follow-up.
- Push non-force with exact readback; request head-scoped rereview for the two findings and consume required
  CI before release.
do_not_redo:
- Do not rebuild Paper R2 or North Star 50–56 or convergence spec 07.
- Do not recreate the continuing worktree, duplicate the EIA producer, or refresh model authority.
- No new quote, alert, workspace, evidence-store or lifecycle owner.
danger_areas:
- Preserve Macro 7596 Gold publication/receipt and 7601 shared-navigation ownership.
- Local browser tests block external network and prove neither live quotes nor account synchronization.
- MISSION_COMPLETE remains false; BUILT_NOT_PROVEN is not deployed or accepted.
prs:
- 8125
supersedes: []
---

Protected source law: Mastermind `dcc4829a811d3f6e4fe8c16a103f813c3501f48e`; INDEX `94d1af402598894372858793a5b1931019c5fa77`.
Integrated main for this repair: `f6dae649ee6d32ec65a95ccea411b205d0b0bc45`.
Previous published head: `b19a3b2ee956005db9f2084319f7754f274aadbe`.
Source carrier: `/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/commodities-wti-eia-slice-a-20260927`.
Cumulative checkpoint: Macro #8049 comment5862072495. Independent review5333803932; findings4118419745 and4118419749. No release approval.

MISSION_COMPLETE:false; BUILT_NOT_PROVEN. Same source/effect carrier; no Paper edits, new worker, watcher or automatic wake. Do not restore the old capture-binding claim: arbitrary observed hashes were discarded. The planned recapture must bind a committed source candidate.
