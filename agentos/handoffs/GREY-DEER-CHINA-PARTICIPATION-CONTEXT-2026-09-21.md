---
workstream: WS:GREY-DEER-RISK-INTELLIGENCE
session: claude/china-participation-context-20260921-sol
model: sol
ended_because: context_budget
mission: 'Deliver a coherent China macro page: trustworthy breadth inputs, truthful
  risk/null interpretation, dated participation and constituent evidence; no invented
  forecast authority.'
state_before: The China page lacked an aligned display of full-board daily participation,
  sampled multiday returns, same-cohort trend changes and absolute sector returns.
changed:
- path: engine/china_participation.py
  what: Add read-only dated price-library, whole-board and sector-ETF context using
    existing stores; leave the existing classifier and historical tape unchanged.
- path: scripts/build_china.py
  what: Bind the context to the producer assessment date in the existing page view-model.
- path: templates/_china_participation_context.html.j2
  what: Add one compact three-column evidence panel and native expandable detail,
    reusing the deep page and its material system.
- path: tests/test_china_participation.py
  what: Cover missing/stale/invalid/future data, matched denominators, benchmark absence,
    absolute-versus-relative returns and bilingual null presentation.
- path: scripts/build_china.py + templates/china.html.j2
  what: Qualified legacy CN rendering copy identifies historical stress and sampled
    breadth without changing raw model, odds or policy fields.
- path: collectors/china_breadth.py + engine/china_tier1.py + templates/china.html.j2
  what: Integrate existing PR7592 safeguards into PR7622 without changing its original
    branch/controller; preserve both code histories and both test groups.
- path: collectors/china_universe.py + engine/china_participation.py + templates/_china_participation_context.html.j2
  what: Qualify the official dated close-weight file and consume it as a fixed-start
    basket with explicit retrospective scope; automatic ingestion is not enabled.
verified:
- claim: Integrated source and neighboring consumers pass together.
  command: python -m pytest tests/test_china_participation.py tests/test_china_archetype_d_s1.py
    tests/test_china_breadth_coverage.py tests/test_china_board_breadth.py tests/test_risk_radar_dlg_country_wiring.py
    tests/test_risk_radar_dlg_partial.py tests/test_build_china_risk_state.py tests/test_market_heatmap.py
    tests/test_breadth_constituents_repair.py tests/test_breadth_split_seam.py -q
    --tb=short
  result: 389 passed; three added integration cases; extreme integer bug reproduced
    as two failures before bounds-check repair. Earlier proof remains in committed
    research/evidence.
- claim: The final normalized combined page retains both repair streams and works
    through its real browser controls.
  command: RENDER_NO_DRIP=1 CHINA_FAST_RENDER=1 python -m scripts.build_china; existing
    lib.pages normalization; python research/grey_deer/capture_china_risk_reading.py
    --integrated
  result: Final16 rest/focus captures and8 integrated interactions pass after auxiliary-output
    cleanup; page0d75fe73 unchanged; source/input/asset fingerprints verified; offline
    only.
- claim: Official-weight parser, arithmetic and optional page consumer
  command: python -m pytest tests/test_china_universe_index_constituents.py tests/test_china_participation.py
    tests/test_china_archetype_d_s1.py -q --tb=short
  result: 220 passed,31 added cases,10 inherited warnings. Source90e9e9eae2c6; no
    clock/recovery repair is counted.
- claim: Actual builder consumes manually injected genuine official-file data and
    renders the new detail
  command: python research/grey_deer/probe_china_index_weights.py <operation-local
    official workbook>
  result: 8 captures and8 interactions passed. Page27296118..., source90e9e9eae2c6.
    Source table not written;27 generated outputs restored after evidence preservation;
    no production claim.
unverified:
- claim: Current production deployment, fresh collection and release acceptance.
  what_would_verify: Later exact-source CI/integration, accepted release and real
    production page/input proof; Chairman explicitly deferred CI this turn.
- claim: Cap-weight contribution, representative equal-weight-index divergence or
    predictive pullback accuracy.
  what_would_verify: Matched-universe constituent weights/history and separate accepted
    calibration; this sample is not that evidence.
- claim: Independent settled-session freshness and official weighted index attribution.
  what_would_verify: Resolve the exact platform-refused clock edit before implementing/passing
    its15 pending cases. Attribution additionally needs an accepted historical-membership
    and official starting-weight source; neither is manufactured from library caps.
- claim: Automatic official-weight source supply
  what_would_verify: Resolve the exact protective refresh-test append refusal, then
    implement and verify the existing-source refresh without bypass. The current reader
    has explicit absent-state behavior.
unresolved:
- Hosted CI, source-current-main qualification and release remain intentionally deferred;
  PR7592 retains its unchanged external release carrier.
- Current library membership is a descriptive sample, not historical point-in-time
  constituents or the CSI300 universe.
- Benchmark observation dates do not certify complete exchange-calendar availability
  or source publication timestamps.
next_actions:
- Resolve the exact official-weight supply verification gate on its original carrier;
  do not recreate the blocked test or refresh through another actor.
- Preserve the15 pending clock cases and the separately refused7029 comparison; resume
  those exact lanes only under a lawful changed gate.
- When release work resumes, reconcile current main and prove CI/publication/live
  behavior; preserve the combined accuracy page and all existing source owners.
do_not_redo:
- Do not change PR7592 or restart its reviewer or CI as part of this feature slice.
- Do not lower94 by judgment or infer whole-market collapse, index contributions,
  forecast probability or trade authority from this context.
- Do not call the arithmetic sample mean an equal-weight index or relative outperformance
  an absolute gain.
- Do not create a new collector, participation tape, queue, scheduler or risk engine.
- Do not re-fetch or redistribute the official workbook to repeat this accepted retrospective
  result; do not call the basket official index attribution or treat its later observation
  as PIT evidence.
danger_areas:
- Missing quotes cannot be filled from earlier observations; every return window needs
  its own sufficient history.
- Trend changes must use the same eligible names at both endpoints.
- Daily traded-board and multiday library samples have different coverage and horizons.
- Offline builds can alter local generated files; preserve proof and restore only
  this operation's generated artifacts before committing source.
prs:
- 7622
- 7592
---



# Current cumulative continuation
Operation:china-participation-context-20260921-sol-001; same PR7622 carrier, Sol custody.
Procedure:Mastermind@9a7ed19091dd82609f8ee405687f16c861c4d8c1; compatible1.0.1/bootstrap1.
Chairman continues capability work; hosted CI/release remain deferred. No worker/watcher.
Starting candidate40845b5ddb2e91a7777868d1b218d1ea6c63e51e integrates main72bb997548453c8954c09306d8944b458c7e8088.
This is a real generated-page conflict and accepted shared-Lens dependency update,
not an ancestry-only refresh. Earlier combined page and official-weight research remain DO_NOT_REDO.
PR7592 and recovery#7029 source/controller were not modified or restarted.

New observed case:September21 data have297/300 complete CSI300 members;601059.SS,
601238.SS and601995.SS lack September21 stored closes. No cause is inferred.
The full300 return remains withheld. Per-window coverage diagnostics name the
excluded members and missing observations without changing any original metric.
Visible rows are bounded to5 with the full excluded count retained.
Twelve cases RED; final477 tests/10 inherited warnings across11 suites, including14
new cases. One fixture frequency mistake was repaired by comparing after setup;
no product threshold was loosened. Pending clock cases remain outside this count.

Actual builder now uses committed September21 inputs; no new collector or weight
injection. Source-current normalization and browser proof are recorded next under
mockups/evidence/china-source-current-20260922; do not claim browser PASS yet.
Current worktree MERGE_HEAD is the exact main pin until the integration commit.
No ambiguous modifying effect is unresolved; do not create another branch/carrier.

Frozen gates:participation clock implementation, protective weight-refresh runner
append, old#7029 compound review, optional weight English-name/residual augmentation.
Do not retry or delegate those refused operations. Weight supply remains absent;
no score/probability/force/sizing or historical ledger change is authorized here.
15 pending clock cases are not included among477 passing tests.
Next:commit this tested same-carrier source/page, complete actual current-source
browser acceptance including shared Lens and real missing-member UI, preserve/read
back evidence, then retain Draft until normal CI/release and exact gates are cleared.
MISSION_COMPLETE:false
