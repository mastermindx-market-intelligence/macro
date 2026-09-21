---
workstream: WS:GREY-DEER-RISK-INTELLIGENCE
session: claude/china-participation-context-20260921-sol
model: sol
ended_because: context_budget
mission: Explain China index versus typical-stock participation and distinguish absolute sector gains from relative outperformance without changing risk authority.
state_before: The China page lacked an aligned display of full-board daily participation, sampled multiday returns, same-cohort trend changes and absolute sector returns.
changed:
  - path: engine/china_participation.py
    what: Add read-only dated price-library, whole-board and sector-ETF context using existing stores; leave the existing classifier and historical tape unchanged.
  - path: scripts/build_china.py
    what: Bind the context to the producer assessment date in the existing page view-model.
  - path: templates/_china_participation_context.html.j2
    what: Add one compact three-column evidence panel and native expandable detail, reusing the deep page and its material system.
  - path: tests/test_china_participation.py
    what: Cover missing/stale/invalid/future data, matched denominators, benchmark absence, absolute-versus-relative returns and bilingual null presentation.
verified:
  - claim: The final affected three-suite run passes with the new context and unchanged neighboring consumers.
    command: python -m pytest tests/test_china_participation.py tests/test_china_archetype_d_s1.py tests/test_china_board_breadth.py -q --tb=short
    result: 134 passed, including 42 added context cases; negative cases were observed failing before their repairs.
  - claim: The real stored-input page builds without live collection.
    command: RENDER_NO_DRIP=1 CHINA_FAST_RENDER=1 python -m scripts.build_china
    result: Full China page and incumbent auxiliary pages emitted; September18 input hashes and denominators recorded in CHINA_PARTICIPATION_REAL_INPUT_20260921.json.
  - claim: Final actual-page and explicitly synthetic degraded-presentation browser cases pass.
    command: python research/grey_deer/capture_china_participation_context.py
    result: Eight full-page theme/locale/viewport captures plus eight native-detail interactions pass; source hash stable, no overflow or capture errors, temporary browser/server closed.
  - claim: Focus styling has actual focus-state evidence rather than only resting screenshots.
    command: python scripts/capture_page_evidence.py --force-state "disclosure-focus:focus(#cnx-participation summary)"
    result: Existing capture owner via explicit Chrome driver recorded 16/16 rest/focus states; final visual-evidence guard passed after its initial missing-focus refusal.
unverified:
  - claim: Current production deployment, fresh collection and release acceptance.
    what_would_verify: Later exact-source CI/integration, accepted release and real production page/input proof; Chairman explicitly deferred CI this turn.
  - claim: Cap-weight contribution, representative equal-weight-index divergence or predictive pullback accuracy.
    what_would_verify: Matched-universe constituent weights/history and separate accepted calibration; this sample is not that evidence.
unresolved:
  - Hosted CI, integration and release remain intentionally deferred; PR7592 stays on its incumbent release carrier without new edits or polls.
  - Current library membership is a descriptive sample, not historical point-in-time constituents or the CSI300 universe.
  - Benchmark observation dates do not certify complete exchange-calendar availability or source publication timestamps.
next_actions:
  - Consume the final current-source browser receipt, then integrate this new context after the existing integrity slice without replaying its repairs.
  - Complete later current-source CI and production acceptance when release work is resumed.
  - Continue source-clock qualification and matched-universe concentration analysis; preserve the held PR6989 calibration work.
do_not_redo:
  - Do not change PR7592 or restart its reviewer or CI as part of this feature slice.
  - Do not lower94 by judgment or infer whole-market collapse, index contributions, forecast probability or trade authority from this context.
  - Do not call the arithmetic sample mean an equal-weight index or relative outperformance an absolute gain.
  - Do not create a new collector, participation tape, queue, scheduler or risk engine.
danger_areas:
  - Missing quotes cannot be filled from earlier observations; every return window needs its own sufficient history.
  - Trend changes must use the same eligible names at both endpoints.
  - Daily traded-board and multiday library samples have different coverage and horizons.
  - Offline builds can alter local generated files; preserve proof and restore only this operation's generated artifacts before committing source.
---

Current intent: Chairman explicitly prioritized the next project capability over waiting for CI.
Protected procedure: Mastermind@c49956d14878bd7b9c001258855e12d547596f13, Skillpack1.0.1/bootstrap1.
Input/base: macro@c48e15193a29fd5eff94e963d0d0c4d6f3104867. Source carrier is the branch in frontmatter.
Source design/result: research/grey_deer/CHINA_PARTICIPATION_CONTEXT_20260921.md.
Numerical receipt: research/grey_deer/CHINA_PARTICIPATION_REAL_INPUT_20260921.json.
No worker, watcher, collector, CI run or production deployment is claimed started by this slice.
No source effect uncertainty is unresolved. CI is deferred, not waived. Parent mission remains incomplete.
FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false

Final browser source 024ae725b32a100224e60331bfb9a46ab72452c4; page SHA256 9567eb67e6ada5a799f349025931bfbdb52ad4d432c247154814e27c293730bc.

Current next-slice PR:7622, Draft/HOLD-FOR-SOL. CI is deferred, not waived.
Final focus/readability proof:mockups/evidence/china-participation-context-20260921/focus-manifest.json.
Next release integration must preserve both this additive panel and PR7592 fixes. No CI result or production acceptance is claimed.
