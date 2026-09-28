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
- claim: Canonical screenshot evidence is bound to an immutable committed page and driver.
  command: Capture from committed source; compare target SHA and git-show bytes before/after; verify every
    PNG digest.
  result: 24/24 browser cells at1440/820/390, EN/ZH, dark/light, rest/focus; source c5030870e1d60663210540d479762c1fc7065ea5;
    no page exceptions or local HTTP failures. External network blocked.
unverified:
- New-head hosted CI and independent rereview; merge, deployment, full visual/accessibility and live acceptance.
- 'Whole repository suite not green: previously observed missing marketdesk_extractor package at collection.'
- Research-case attachment/persistence remains Slice B, not implemented.
unresolved:
- Current cached EIA observation lacks publication and receipt timestamps; do not synthesize them.
- Shared assistant-launcher overlay is inherited global UI; not part of this slice.
next_actions:
- Push the source and evidence commits on the same branch with exact remote readback; answer review findings
  and request head-scoped independent rereview.
- Consume new-head required CI and review. Complete release/live proof before Research persistence Slice
  B.
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

Current protected Mastermind: dcc4829a811d3f6e4fe8c16a103f813c3501f48e. Integrated main: f6dae649ee6d32ec65a95ccea411b205d0b0bc45.
Capture source commit: c5030870e1d60663210540d479762c1fc7065ea5. PR #8125; cumulative checkpoint Macro #8049 comment5862072495.
MISSION_COMPLETE:false; BUILT_NOT_PROVEN. Evidence-only follow-up must preserve source/page/driver blobs at the capture source. No unresolved effect, Paper change or autonomous wake.

## Current dual-theme review repair

Current source/capture commit `c3d048cef470f0b4d223daea3c4e41af05ae2fc9`, main integration `dea858959c6f37122fd500dd673c44b271f19fa9`. Supersedes earlier visual-review counts and focus-image acceptance claims only. See VERIFICATION.md and DESIGN_ADJUDICATION.md for exact24-cell self-adjudication, capture keyboard repair,959 registered-owner tests,25 rights tests and direct-EIA summary correction. Same previously generated Sep25 page retained after proving incoming page movement was clock-only; out-of-scope Sep27 rebuild outputs were archived rather than published. No whole-repository, independent-review, merge, deployment or live acceptance is claimed. MISSION_COMPLETE:false. Continue via #8049 comment5862072495 and PR #8125; keep independent review and live acceptance separate.
