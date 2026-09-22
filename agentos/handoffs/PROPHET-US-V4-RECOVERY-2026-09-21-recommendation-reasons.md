---
workstream: "WS:PROPHET-US-V4-RECOVERY"
session: theme-recommendation-reasons-20260921-sol
model: sol
ended_because: ci_handoff
prs: [7669, 7478, 7650]
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
    what: Seventy-two gate, parity, native JavaScript, missingness, translation and native-entry attribution cases.
  - path: research/sector_pulse/recommendation_reasons_20260921/
    what: Source-bound policy replay, original-versus-candidate browser evidence and exact limitations.
  - path: .github/ci/legacy-jobs.yml
    what: Register the original theme scoring suite and new reason suite in the existing owner job.
  - path: .github/workflows/ci.yml
    what: Trigger that job for the reason tests and frozen test-only control fixture.
verified:
  - claim: Theme, reason, native consumer and detail contracts pass locally.
    command: python3 -m pytest -q tests/test_theme_recommendation_reasons.py tests/test_theme_scoring.py tests/test_theme_scoring_conflicted.py tests/test_theme_scoring_leadership_split.py tests/test_basket_detail_glance_copy.py
    result: 169 passed.
  - claim: Python 3.12 core and native consumer subset passes.
    command: python3.12 -m pytest -q tests/test_theme_recommendation_reasons.py tests/test_theme_scoring.py tests/test_theme_scoring_conflicted.py tests/test_theme_scoring_leadership_split.py
    result: 161 passed.
  - claim: Frozen incumbent policy is preserved and real source explanations reproduce existing final verbs.
    command: python3 research/sector_pulse/recommendation_reasons_20260921/prove.py --source-ref 7c6e35163c9f67087ffe174a7ab3810f47ce6a45 --out /tmp/mmx-theme-reasons-proof-20260921
    result: 10584 policy cases unchanged; 49 of 49 stored themes reproduced; non-explanation data unchanged.
  - claim: Real stored input and native original/candidate templates render the new reasons across the required viewport/theme/language combinations.
    command: python3 research/sector_pulse/recommendation_reasons_20260921/browser_proof.py --source-ref 7c6e35163c9f67087ffe174a7ab3810f47ce6a45 --out /tmp/mmx-theme-reasons-browser-final-20260921
    result: 48 captures; all 24 candidate reasons visible; zero JavaScript page errors and zero page-level horizontal overflow.
  - claim: Paired plain-copy assets are synchronized.
    command: python3 scripts/check_template_site_sync.py
    result: 99 pairs checked successfully.
  - claim: The native clean-entry flag and quality reproduce for every dated theme, isolating three constructive themes blocked solely by relative strength.
    command: python3 research/sector_pulse/recommendation_reasons_20260921/audit_entry.py --source-ref f98f57f4ec7c2cc30cbd90d9a7a759d5ea69144c --output /tmp/theme-entry-attribution.json
    result: 49 reproduced, zero unavailable; seven constructive themes comprise three entry-clear, three relative-strength-only vetoes and one other-condition veto. No live policy changed.
unverified:
  - claim: Exact-head hosted CI, independent approval and production publication of this new slice.
    what_would_verify: Source-carrier concluded checks and review, then authorized deployed producer-to-consumer evidence.
  - claim: Broader Prophet ranking, current-session CPU leadership and full-page design recovery.
    what_would_verify: Existing owner releases and their stated live/input/behavioral acceptance; this reason repair does not substitute.
unresolved:
  - Original clock PR 7650 has successful full CI but no independent approval. The Vercel gate dependency is resolved by approved merge 7478; original source review and production proof remain owed.
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
under existing source law. The Vercel dependency was subsequently resolved by
independently approved PR #7478, not a session-local bypass. Independent review
and all actual repository CI/authority checks remain binding.

The next phase is release/integration and the separate behavior-bearing rank/input
frontier, not more rewriting of the accepted reason projection. Actual release and
broader mission completion remain explicitly unproven.

## Accepted release dependency and exact continuation

The existing Vercel cleanup #7478 was merged by one expected-head squash, without
admin or auto-merge, at `111eb086380b36fcb4afa69add59877d1a939441` on
2026-09-22T01:54:53Z. Its exact head `bf55ed9e969344b746e995d1ead9701dfd7bb168`
had concluded successful repository checks and non-author approval 5273319511.
The production merge-control owner then ran sweep 35677588845 successfully at
the exact merge SHA, including the real sweep step. Verification comments:
#7478 5770156918 and #7650 5770157042. This source/publisher dependency is
DO_NOT_REDO; it does not establish production feature acceptance.

The sweep disclosed an independent shared baseline/capacity backlog: 75
baseline-blocked PRs, no workload slots available, and an existing semantic-main
proof in progress. Do not duplicate runners, queues or baseline dispatches.

New source PR #7669 is DRAFT / HOLD-FOR-SOL. Its complete implementation and
browser proof are at `01a7996bacb018f5fa1f1b08ac8379fff2038c20`. The current
cumulative record binds the subsequent docs-only head in the PR's checkpoint.
A formal review request to mastermindx-3 exists for both #7669 and #7650, but
neither has independent approval at this observation. No worker execution is
inferred from these requests. #7669 contract-delta/fences/active-authority have
passed; its full CI packs are still running, not accepted.

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false

The verified chunk is the policy-preserving explanation producer plus real
consumer/browser proof, and completion of the approved release dependency. The
next unit is source review/release and production proof, followed by the separate
behavior-bearing two-gate evaluation; source custody stays with these exact PRs.
Resume on a lawful CEO continuation with fresh procedure and same-carrier
reconciliation. No autonomous wake or background reasoning is asserted.


## Latest continuation: source-scoped explanation and native entry attribution

Protected procedure: `Mastermind@ce18ed4f1eaa28e65a616a90aecca5c5ce1c5a2e`.
Input/code compatibility observation: `macro@f98f57f4ec7c2cc30cbd90d9a7a759d5ea69144c`.
Current same-carrier modification advances #7669; #7650 and all other source
writers remain untouched. No worker, watcher, alternate review identity or
production operation was started here. Direct work reason: PRINCIPAL_JUDGMENT /
LOWER_TOTAL_OVERHEAD for exact-source attribution and correction of its user claim.

The main new capability is executable **native clean-entry attribution** in
`research/sector_pulse/recommendation_reasons_20260921/audit_entry.py`, consumed by
its CLI report and 32 new tests in the existing hosted suite. It replays the actual
native clean-entry owner, requires the stored flag AND quality to match, and isolates
a single relative-strength-input change in a copied research call. The CLI also
requires the native owner bytes to match the immutable input revision. The
independently date/count-matched extension artifact remains context without
atomic-generation or identical-roster proof and receives no trade authority.

`entry-attribution.json`: 49 native rows reproduced, zero unavailable. Of seven
existing Enter/Accumulate themes, three are already clean-entry, three are blocked
only by the relative-strength veto (AI Semiconductors, Memory/Storage, AI
Infrastructure), and one fails other conditions (AI Software). Actual own-price
extension context is not uniformly absent or benign: the source calls Cybersecurity
and Crypto Rails stretched. Accordingly, the prior global wording 'price stretch
is not established' was corrected to say what this relative-strength filter does
NOT measure. Other evidence is not denied or overwritten.

The frozen 10,584-case recommendation comparison still has zero verb changes.
Updated local suites pass 169 tests on Python 3.14 and 161 overlapping tests on
Python 3.12. A fresh 48-cell original/candidate browser run completed with every
candidate reason visible and no page errors or page-wide horizontal overflow.
The original held implementation, hypothesis limitations and release dependency
receipts above remain historical evidence, not current-head CI or live proof.

Current boundary: source correction and one-snapshot diagnosis are proven locally;
full exact-head CI, independent review, production publication and multi-episode
model comparison remain owed. The earlier #7650 CI is green but its requested
independent reviewer has not returned approval. #7669 remains DRAFT/HOLD; no
self-review or old-head check is a substitute for new semantic acceptance.

Next action: consume this same-carrier review/CI and integrate the tested reason
contract through the existing publisher. The next separate model experiment must
freeze and compare the .75 entry versus .85 recommendation gates against own-price
risk on a same-decision-time population using existing calibration/evaluation
owners. Do not change live thresholds from this single snapshot, relabel it a
forward-return study, hard-code CPUs, or redo the already merged #7478 cleanup.

MISSION_COMPLETE: false
CAPABILITY_STATE: BUILT_NOT_PROVEN
FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION

Final pre-push compatibility read: `origin/main` and GitHub main both returned
`912feaa2b13959a6cca4d3f1472188b4a4d702bb`. The first fetch encountered a shared
remote-ref race; it was reconciled by reading the same ref, not re-running or
resetting it. No material differences from the input pin were found in AGENTS,
CLAUDE, theme_scoring, basket_score, theme_extension or the two template consumers.
Agent OS validation returned 0 errors / 125 existing warnings; paired assets
remain identical across 99 checked pairs. Current source-proof SHA-256 is
`13259397082e95ca50466074ef6a3cfe31588fbf83c781a2de7daa4132bdee06`;
entry-attribution SHA-256 is
`5ce749aa1810d7e0aa66a73c779980e4fc6d4b94a846d3fb51e28e7fce443049`.
The exact final source head and new CI identity belong in the same PR's read-back
checkpoint comment, avoiding an ancestry-only or self-referencing docs commit.
