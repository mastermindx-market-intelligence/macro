---
workstream: "WS:PROPHET-US-V4-RECOVERY"
session: theme-recommendation-reasons-20260921-sol
model: sol
ended_because: ci_handoff
prs: []
mission: >
  Continue the Chairman's concentrated-leadership recovery by making the existing
  recommendation engine and real basket consumers explain their actual constraint,
  without changing ranking, entry permission, position sizing or trading policy.
state_before: >
  The previous clock correction 7650 reached successful hosted CI but remained
  unreleased. Theme HOLD reasons were generic, positive theme reasons could claim
  room to add without a clean entry, and basket renderers replaced explanations
  with an unsupported assertion that no constituent had an entry.
changed:
  - path: engine/theme_scoring.py
    what: Return the existing verb with its actual deciding reason; explain the final safeguard and entry-quality state.
  - path: templates/baskets_desk.js
    what: Consume safe bilingual reasons, preserve honest legacy fallback, and distinguish relative strength from price stretch.
  - path: site/baskets_desk.js
    what: Paired byte-identical published asset for the existing desk renderer.
  - path: templates/basket_detail.html.j2
    what: Same reason contract on the real detail route; shorter non-entry badge fixes observed mobile wrapping.
  - path: tests/test_theme_recommendation_reasons.py
    what: Forty new gate, parity, native JavaScript, missingness and translation cases.
  - path: research/sector_pulse/recommendation_reasons_20260921/
    what: Source-bound policy replay, original-versus-candidate browser evidence and exact limitations.
  - path: .github/ci/legacy-jobs.yml
    what: Register the original theme scoring suite and new reason suite in the existing owner job.
  - path: .github/workflows/ci.yml
    what: Trigger that job for the reason tests and frozen test-only control fixture.
verified:
  - claim: Theme, reason, native consumer and detail contracts pass locally.
    command: python3 -m pytest -q tests/test_theme_recommendation_reasons.py tests/test_theme_scoring.py tests/test_theme_scoring_conflicted.py tests/test_theme_scoring_leadership_split.py tests/test_basket_detail_glance_copy.py
    result: 137 passed.
  - claim: Python 3.12 core and native consumer subset passes.
    command: python3.12 -m pytest -q tests/test_theme_recommendation_reasons.py tests/test_theme_scoring.py tests/test_theme_scoring_conflicted.py tests/test_theme_scoring_leadership_split.py
    result: 129 passed.
  - claim: Frozen incumbent policy is preserved and real source explanations reproduce existing final verbs.
    command: python3 research/sector_pulse/recommendation_reasons_20260921/prove.py --source-ref 7c6e35163c9f67087ffe174a7ab3810f47ce6a45 --out /tmp/mmx-theme-reasons-proof-20260921
    result: 10584 policy cases unchanged; 49 of 49 stored themes reproduced; non-explanation data unchanged.
  - claim: Real stored input and native original/candidate templates render the new reasons across the required viewport/theme/language combinations.
    command: python3 research/sector_pulse/recommendation_reasons_20260921/browser_proof.py --source-ref 7c6e35163c9f67087ffe174a7ab3810f47ce6a45 --out /tmp/mmx-theme-reasons-browser-final-20260921
    result: 48 captures; all 24 candidate reasons visible; zero JavaScript page errors and zero page-level horizontal overflow.
  - claim: Paired plain-copy assets are synchronized.
    command: python3 scripts/check_template_site_sync.py
    result: 99 pairs checked successfully.
unverified:
  - claim: Exact-head hosted CI, independent approval and production publication of this new slice.
    what_would_verify: Source-carrier concluded checks and review, then authorized deployed producer-to-consumer evidence.
  - claim: Broader Prophet ranking, current-session CPU leadership and full-page design recovery.
    what_would_verify: Existing owner releases and their stated live/input/behavioral acceptance; this reason repair does not substitute.
unresolved:
  - Original clock PR 7650 has successful full CI but no independent approval; Vercel quota failure remains nonpassing and was not bypassed.
  - Clean-entry separately requires relative-strength percentile below .75; that percentile is within the theme's own rolling relative-price history, not a sector cross-section. Policy remains unchanged.
  - Shared action-board blanket extension and lane-copy work belongs to incumbent 7076, not this new writer.
  - Live quote/API paths are unavailable by fixture in the browser evidence, never replaced with old Git-tracked quotes.
next_actions:
  - Publish this source carrier with its evidence, consume exact-head CI and independent review, and verify normal production publication.
  - Continue original clock release 7650 on its same carrier only when its real release gates close.
  - Converge the unchanged recommendation reason identities with the existing action-board and Prophet visibility owners; do not duplicate their writers.
do_not_redo:
  - Preserve clock 7650, hottest-desk 7520, candidate visibility 7572 and action-board 7076 source custody.
  - Do not remove the US relative-strength veto or change any rank or entry policy as a side effect of explaining it.
  - Do not describe local stored-input browser evidence as live September 21 or authenticated production proof.
danger_areas:
  - Snapshot replay uses rounded published inputs and is not a full nightly or logged-at availability reconstruction.
  - Existing descriptor and thesis translations are inherited; only changed reason text is claimed bilingual, not a whole-page redesign.
---

# Cumulative continuation

MISSION_COMPLETE: false
CAPABILITY_STATE: BUILT_NOT_PROVEN

Protected procedure: Mastermind@4ca1b97e65de9d4ba8c868b9d708fb7620a8a76f.
Base: macro@7c6e35163c9f67087ffe174a7ab3810f47ce6a45.
Source carrier: claude/theme-recommendation-reasons-20260921-sol.
The initial implementation checkpoint 78e1d01f4ea9 was pushed before browser work;
this record and final evidence belong to the subsequent same-carrier commit.
The publishing PR and its latest checkpoint comment resolve the exact current head.

The action-authoritative intent is the current Chairman continuation. Direct work
was retained for PRINCIPAL_JUDGMENT / LOWER_TOTAL_OVERHEAD. The legacy `sol` record
enum identifies the CEO lane, not an attestation of model transport or runtime.
No worker, new provider session, watcher, trade or production deploy was started.

The original #7650 reviewer request to mastermindx-3 exists, but request is not
approval or execution. Its inactive pilot-authority check is nonbinding on main
under existing source law; no binding Vercel or independent-review gate was waived.

The next phase is release/integration and the separate behavior-bearing rank/input
frontier, not more rewriting of the accepted reason projection. Actual release and
broader mission completion remain explicitly unproven.
