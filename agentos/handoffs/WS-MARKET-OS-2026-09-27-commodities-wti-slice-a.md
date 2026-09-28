---
workstream: WS:MARKET-OS
session: claude/commodities-wti-eia-slice-a-20260927
model: sol
ended_because: ci_handoff
mission: >-
  Implement the first frozen Commodities R2/North Star convergence slice: existing
  WTI/EIA physical evidence with truthful clocks, degraded states and source
  inspection in the current commodity detail view. Continue Macro issue 8049.
state_before: >-
  Paper convergence was frozen. Interrupted local implementation existed but was
  uncommitted and had invalid/future-date qualification, nonfinite-value and
  bilingual-attribute defects; the generated page had not passed responsive proof.
changed:
  - path: scripts/build_commodities.py
    what: >-
      Bind oil-only physical evidence into sector detail. Keep quote, analysis,
      observation and evaluation clocks separate. Publication/receipt instants
      remain unknown when absent. Reject invalid/future/mismatched-source evidence,
      preserve real zero, withhold mixed-period composite and isolate read errors.
  - path: templates/_commodity_oil_physical.html.j2
    what: >-
      Add bilingual physical reading, truthful stale/partial/absent/error states,
      native source/method disclosure and direct EIA attribution link.
  - path: templates/commodities.html.j2
    what: >-
      Oil-only include and shared-token styling. Fix incumbent warning-row mobile
      overflow without hiding content or changing scores or shared navigation.
  - path: agentos/decisions/DEC-EIA-SPR-RIGHTS.md
    what: >-
      Record the narrow direct EIA-authored petroleum reuse basis and translation,
      attribution and third-party exclusions. Other vendor rights remain untouched.
  - path: mockups/evidence/commodities-wti-slice-a
    what: >-
      Canonical eight rest and eight actual keyboard-focus browser cells, selected
      visual crops, source/effect boundaries and exact verification command report.
verified:
  - claim: Date/value and unsafe-evidence failures reproduced before correction.
    command: python3 -m pytest tests/test_commodities_r2_wti_physical.py -q
    result: First red run 17 failed; second withholding red run 2 failed; subsequent focused integration passed 843 tests with 3 existing covariance warnings.
  - claim: Real generated WTI page works in both themes and languages.
    command: python3 scripts/capture_commodities_wti_slice_a.py --site-dir site --routes /commodities.html --force-state 'focus:focus(.oil-phys-receipt summary)'
    result: 16 of 16 cells captured; actual Oil selection and keyboard disclosure; no page overflow or observed page exceptions. External network blocked, not live-feed proof.
  - claim: Source implementation guard checks passed.
    command: See mockups/evidence/commodities-wti-slice-a/VERIFICATION.md.
    result: Python compilation, actual-diff design guard, visual evidence, runtime style, paired assets and whitespace checks passed.
unverified:
  - Whole-repository suite blocked at collection by missing marketdesk_extractor package; no all-suite pass.
  - Exact-head hosted CI, independent review, merge, deployment and live acceptance.
  - Research-case attachment/persistence belongs to Slice B and is not implemented here.
unresolved:
  - Current cached EIA observation lacks publication and receipt timestamps; do not synthesize them.
  - Shared assistant-launcher overlay is inherited global UI; not part of this slice.
next_actions:
  - Review the published Slice A candidate and exact-head CI; resolve relevant failures without taking over unrelated owners.
  - Reconcile generated-page and source inputs on current main before release; prove live output.
  - Only then implement evidence attachment into the existing Research-case owner, preserving original receipts.
do_not_redo:
  - Do not rebuild Paper R2 or North Star 50–56 or convergence spec 07.
  - Do not recreate the continuing worktree, duplicate the EIA producer, or refresh model authority.
  - No new quote, alert, workspace, evidence-store or lifecycle owner.
danger_areas:
  - Preserve Macro 7596 Gold publication/receipt and 7601 shared-navigation ownership.
  - Local browser tests block external network and prove neither live quotes nor account synchronization.
  - MISSION_COMPLETE remains false; BUILT_NOT_PROVEN is not deployed or accepted.
prs: []
supersedes: []
---

Current protected source law: Mastermind `aebb2ed19e68bda072e38221638925d674b656dc`.
Base: Macro `46963311ba19fe8167553774be506bae43d3460b`.
Continuing Studio worktree: `/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/commodities-wti-eia-slice-a-20260927`.
Cumulative checkpoint: Macro #8049 comment 5862072495. Read its latest revision before continuing.

The existing Agent OS model enum records the Sol role; system-exposed model identity for this session is GPT-6 Astra Pro. Turn disposition: CHECKPOINTED_CONTINUATION, MISSION_COMPLETE:false. The repository enum ci_handoff denotes the upcoming code/CI review boundary, not worker delivery or production acceptance.
