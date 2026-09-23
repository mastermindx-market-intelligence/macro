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
  - path: engine/basket_score.py
    what: Expose native stock-entry reasons and complete member diagnostics while preserving admission and fixing contradictory watch explanations.
  - path: tests/test_basket_entry_explanations.py
    what: Twenty-four producer, frozen-parity, complete-roster, native JavaScript and escaping cases; prior non-stock functions remain source-hash frozen.
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
    what: Source-bound replay, native entry attribution, frozen historical five-arm comparison and exact limitations.
  - path: tests/test_theme_entry_gate_comparison.py
    what: Thirty-six causality, veto-isolation, date, forward-outcome and fixed-denominator regression cases.
  - path: data/trial_ledger.jsonl
    what: Append five study configurations through the existing native trial owner; preserve all prior records.
  - path: .github/ci/legacy-jobs.yml
    what: Register the original theme scoring suite and new reason suite in the existing owner job.
  - path: .github/workflows/ci.yml
    what: Trigger that job for the reason tests and frozen test-only control fixture.
verified:
  - claim: Frozen historical comparison and existing theme consumers pass the expanded owner suite.
    command: python3 -m pytest -q tests/test_theme_entry_gate_comparison.py tests/test_theme_recommendation_reasons.py tests/test_theme_scoring.py tests/test_theme_scoring_conflicted.py tests/test_theme_scoring_leadership_split.py tests/test_basket_detail_glance_copy.py
    result: 205 passed on Python 3.14; 197 overlapping core tests passed on Python 3.12.
  - claim: Five fixed arms were compared on the same immutable sector-price population after pre-outcome registration.
    command: python3 research/sector_pulse/recommendation_reasons_20260921/compare_entry_gates.py --source-ref 1e767a2f5b43f302b0e1068c9a7e60b12aeb98ee --prereg-commit 59bf08ca81632451165ac2423637181d536ab9e4 --output /tmp/theme-entry-gate-comparison
    result: 8937 valid decision rows; 434 common 21-session assessment dates; 14 added unbounded and seven price-bounded observations; no primary multiple-testing-adjusted significance or promotion.
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


## September 22 continuation — frozen historical two-gate comparison

Procedure was re-pinned to protected `Mastermind@9a7ed19091dd82609f8ee405687f16c861c4d8c1`;
same-pin Skillpack 1.0.1/bootstrap 1 compatibility and unchanged loaded-skill digests
were verified. Original #7650 and #7669 had concluded successful full repository
CI at recovery, but still had no independent approval. The existing #7478 release
cleanup remains DO_NOT_REDO. No reviewer account, worker or alternate release
carrier was invented to bypass the unconsumed review request.

A pre-outcome protocol was committed and pushed at
`59bf08ca81632451165ac2423637181d536ab9e4` before computing the historical comparison.
The new pure research CLI `compare_entry_gates.py` reuses native calibration,
entry, recommendation, extension, calendar and statistical owners. Its five fixed
arms are registered with the existing native `data/trial_ledger.jsonl`: five
append-only records, no separate ledger, no earlier record change. The .75 entry
veto is relaxed only at already-sufficient ORIGINAL quality; no .20 counterfactual
quality bonus is granted. The .85 recommendation veto is evaluated separately.

Input pin `macro@1e767a2f5b43f302b0e1068c9a7e60b12aeb98ee` binds the nine native
core sector ETF close archives plus SPY, December 1998 through September 18, 2026.
The study produced 8,937 valid decision-time asset rows. Decisions use only causal
features, hypothetical entry is NEXT-session close, costs total 20 basis points,
and 5/21/63-session outcomes remain null when future paths are incomplete.
The fixed pre-2018 / 2018-onward partition excludes crossing development outcomes.

Primary 2018-onward result on 434 fully observed common decision dates:
- Entry-veto-only and both-veto alternatives add 14 observations; mean added
  21-session net absolute return +1.73%, net relative return +1.14 percentage
  points, six negative outcomes. Date-level corrected q=0.6437.
- Recommendation-veto-only adds zero observations: the stricter clean-entry path
  remains. This does not make the .85 rule globally irrelevant to theme portrayal.
- Native-price-bounded additional admission retains seven extra observations;
  mean net +3.01%, relative +4.34 points, two negative outcomes, q=0.5348.
- None of the four primary comparisons passes the frozen significance screen.
  Small positive cohorts are not a promoted live entry algorithm.

The companion REPORT states the earlier-period instability, weak baseline proxy,
fixed-slot non-compounded event-budget estimand, and six archive/calendar mismatch
dates. Those mismatches are not filled or silently treated as corrected calendar
history. They excluded 2,727 potential decision rows under the complete-prefix
rule and are an exact independent calendar-owner follow-up.

Evidence: `research/sector_pulse/recommendation_reasons_20260921/gate-comparison/`
contains the full source-bound result, deterministic compressed event rows,
readable report and test receipts. New test suite has 36 discriminators; 205 full
Python 3.14 owner/consumer/detail tests and 197 overlapping Python 3.12 tests pass.
Original 10,584-case recommendation parity is retained. The new suite is wired
into the existing hosted job and trigger list. No runtime engine, UI, quote,
rank, entry permission or sizing policy changed in this continuation.

Ruling: no blanket production gate removal; the .85-only adjustment is not a
solution for this clean-entry path. Continue source release review, preserve
leadership/candidate visibility, then use the existing #7572 entry/selection owner
for a same-decision-time stock-level comparison. Do not tune this proxy experiment
until it turns green, claim portfolio returns, label it prospective/PIT availability
validation, or redo the completed freeze/run without a material invalidator.

This bounded research comparison is complete; the parent product mission is not.
Final source head, source/data hashes and hosted run identities are recorded by
read-back comments on the same PR, without a self-referential commit loop.
MISSION_COMPLETE: false
PRODUCTION_POLICY_CHANGED: false


## Latest continuation — stock-level entry workflow, 2026-09-22

Protected procedure: `Mastermind@0471cea4f891da1ec0c9fbeff10a9391f9cdd90f`,
same-pin Skillpack 1.0.1/bootstrap 1. Current Chairman intent is to advance the
actual product and stock-entry path, not accumulate another historical study.
Source before this unit: `4e01f20e2dc5ee66634ed51ec127ba8b8630b860` on the same
#7669 branch. Direct reason: PRINCIPAL_JUDGMENT / LOWER_TOTAL_OVERHEAD.

**Implemented capability:** the theme hero now opens a complete stock-by-stock
entry-check disclosure in the existing detail page. The native stock admission
owner returns a deciding reason alongside the unchanged admission; buy and watch
projections share that same result. No score, entry threshold, price/target,
portfolio allocation or new trade authority was introduced. No duplicate state,
candidate or publication owner. Missing conviction remains unavailable, not a
negative price verdict. Every member remains visible even beyond the existing
12-row actionable presentation cap. Qualified legacy records no longer appear
simultaneously in the non-actionable fast-turn watch; a low-score rejection cannot
print BUY as its own blocking reason.

Proof: 242 Python 3.14 owner/consumer/research regression tests pass; 37 stock-owner
and JavaScript consumer tests pass on Python 3.12. A 2,160-case frozen native
comparison preserves status/buys/uncovered exactly. All 49 existing US detail pages
replay their original status, buy rows and missing coverage (1,017 member rows,
including repeated stocks across different baskets, not 1,017 distinct securities).
All pre-existing basket-score functions other than the stock projection are
source-hash unchanged. Frozen historical research artifacts remain tied to their
old commits; do not rerun them against a changed module by weakening hash guards.

The final browser proof contains 48 original/candidate viewport/theme/language
captures plus 24 interactive entry-disclosure captures. All candidate reasons and
stock link targets pass, the 40px action targets pass, and keyboard focus/open state
survive a real rerender. A real anchor-default focus defect was found and repaired
before the accepted rerun. Zero page errors and page-level horizontal overflow.
This is stored-input local browser proof, NOT a current market or deployed proof.
Source engine SHA-256: `4a34515ec6ec790e9fc69b97efa2281999774c2f82770a4dec46ec2080f15bb0`.
Browser proof SHA-256: `c88a937d1dfbba2804d850b716bc91e0153167bdd30c1852117cda3dcfb93c57`.
The complete workflow/proof boundaries are in `STOCK_ENTRY_WORKFLOW.md` beside the
source-bound `stock-entry-proof.json` and updated existing browser evidence.

**Release reconciliation:** #7650 is now independently approved and fully green
at integrated head `e0e996381af1494e3c201078fddb472ad75b8061`, but OPEN. Its one
integration update is accepted history, DO_NOT_REDO. Shared source-main failure
remains with incumbent #7693 at `9e74c33d3f6c22b1e41f4dc7f100baf32a050734`;
comments 5774384105/5774440956 bind the current inherited hub-marker/theme-receipt
repairs. No competing main-red PR, threshold waiver or writer takeover occurred.
#7478 cleanup remains complete. No Vercel action, deployment, trade or watcher.

A bounded invocation of the existing native Opus reviewer was BLOCKED by the
platform before a process receipt. No review execution was proven; no retry,
other-provider/account route or self-approval was used. The existing GitHub review
request remains with mastermindx-3. #7669 stays Draft/HOLD pending actual review,
current exact-head checks and lawful normal production publication. Source writes
and browser work remained available and advanced independently.

Primary continuation: consume same-carrier source review and release gates, then
obtain normal deployed producer → reason → stock-navigation proof. The next
behavioral model decision must use the revealed stock-cycle/conviction/entry
conditions, not assume the basket .75 gate was every CPU stock's only blocker.
No new historical threshold sweep is needed to accept this product correction.
MISSION_COMPLETE: false. CAPABILITY_STATE: BUILT_NOT_PROVEN.
FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION.

## 2026-09-23: compiled artifact repair and focused-publication data loss

Current protected procedure is Mastermind@c18ea2ca779f042702a63a78bf1f10f5a1e0c0f6.
The original #7650/#7520 and shared #7693 are MERGED and DO_NOT_REDO.
#7669's latest real failure was its own missing compiled template helpers, not
those retired blockers. Main d34993def9fa00e88c930f39a498b6ecad97455b was integrated
once at 9c81d664d1337b5214e249151ab0c343b4047dab, without changing feature blobs.

Existing renderer/writer/finalizer interfaces now materialized 121 pages from
exactly their existing source data (1,917 member rows); dates, original generated
stamps, non-explanation data and status/buys/coverage remain identical. No old Sep18
snapshot was restored over current Sep21/Sep22 evidence. The actual failing
compiled-page test passes unchanged. Expanded tests:302 Python3.14,302 overlapping
Python3.12. Canonical 40-cell captures and10 interaction checks bind actual compiled
files. Evidence:research/sector_pulse/recommendation_reasons_20260921/publication_20260923/.

The attempted new build_theme_detail helper/CLI source change was platform-refused;
readback proved the script unchanged. It was not retried. Native existing-renderer
page materialization was independent; no new publication or retry control exists.
No independent reviewer was restarted or impersonated. #7669 remains DRAFT/HOLD.

New critical-path invalidator: the focused #7211 publisher rewrote the Sep21
semiconductor detail from11 available member assessments at e77ddcedfe9f to zero
at f8bc00fe1532. It calls the stock-detail builder without rebuilding/hydrating the
required gitignored dossier tree. Current output now explicitly exposes that gap.
Prevent this lightweight lane from overwriting full stock-detail evidence; don't
copy earlier isolated scores into the newer frame or bypass private-data gates.
#7749's unpublished mixed-technical-date candidate remains separate and held.

## Independent review consumed; bounded source repair — 2026-09-23

Current Chairman continuation. Protected compatible Skillpack remains
Mastermind@a5aa42d15c3e5cbfe785b415511de188cff66bd0. The source remains on the
original #7669 carrier; no model/entry/score policy promotion or new publisher.

Native review capability was successfully requalified on the materially changed
source, on the original reviewer carrier and included account. #7669's reviewer
session d8f2dc35-3019-4fb4-80a3-68932c42ae44 returned PARTIAL after a capped read-only
investigation plus one tool-disabled terminal-report turn. It verified core
recommendation/stock-admission equivalence and all121 compiled hashes, but found
incomplete opened-state visual coverage plus four source/translation edge cases.
This is NOT source approval. The native report is retained, not erased.

Repairs in this source revision:
- Both existing basket consumers translate the native rollover conditions. Timing
  cards reuse the same RS formatter instead of reintroducing price-extension copy.
- Unavailable stock evidence has its own row reason even under a globally blocked
  theme; global theme admission is unchanged.
- Malformed summary input has a real, focusable status target rather than a dead
  hero anchor. Native refresh state preserves focus for this failure target too.
- All121 generated pages were refreshed from their own existing embedded data.
  All1,917 member rows, canonical status/buys/coverage, other non-explanation fields,
  observation dates and original generation stamps were checked and preserved.
- The opened component now has all eight dark/light, EN/ZH, desktop/mobile cells
  on five actual regional pages (40 real states), plus16 visibly labeled synthetic
  validation-failure and mixed theme-blocked/unavailable states. All56 pass
  keyboard/link/open-state/focus and page-overflow checks; no page exceptions.
  Separate DARK TREATMENT / LIGHT TREATMENT and artifact caveats are documented.
- Seven new regression cases were RED before repair and GREEN after; final owner
  suite309pass on Python3.14 and the same309pass on Python3.12 (overlapping counts).

Evidence: research/sector_pulse/recommendation_reasons_20260921/review_20260923/.
Older publication/browser evidence remains the historical reviewed baseline, not
current-template proof. Independent repair re-review, new-head hosted CI and
production acceptance remain owed. Do not convert this PARTIAL into approval.

Separate preservation fix#7769: native reviewer session
cbe9be03-e539-48d5-8879-0a12d43acf88 returned PASS, independently ran48tests and
confirmed the parent-source mutation. Sol accepted its bounded source at exact
11c89b3c5074f6fe60bbb32d1220145d3cb64d35 and released the hold in comment5790591847.
The existing merge-on-green path is armed; native auto-merge is null. This was not
an impersonated GitHub approval and does not claim the PR has already merged.
Its nonblocking source-comment/staging-test-hardening notes are preserved there.
Do not edit that source while its existing release owner is consuming it.

Full stock-aware restoration is already being attempted by the EXISTING renderer:
run35709199694/job106740198741, pc-render-1, actual start2026-09-23T05:08:42Z,
re-render step started05:10:03Z. Dossier/publication steps were still pending at
observation; earlier queued engine-render35808507754 was not the only lawful owner.
No cancellation, duplicate dispatch, relabel or restoration claim. The old Sep22
run-wrapper start must not be confused with the actual current job start.

Next: commit/push this repair on the original carrier, consume an exact-source
independent repair return, and complete actual CI/release. Verify deployed
source/input/result only through the existing publisher. Parent MISSION_COMPLETE
remains false; #7749's held source and denied publication are not imported.
