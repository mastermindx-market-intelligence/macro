---
workstream: WS:PROPHET-US-V4-RECOVERY
session: claude/prophet-lab-earnings-view-20260917
model: sol
ended_because: blocked
mission: Make the existing private Lab episode and earnings evidence discoverable
  inside the U.S. Prophet board, preserving source generation and access boundaries.
state_before: 'PR #7264 at 3ec7646978a9a5d8527ed26a8ea26d8dec4508e6 had the native
  private readers but no functioning browser consumer; four incomplete drafts were
  preserved.'
changed:
- path: templates/_prophet_earnings_browser.js.j2
  what: Complete lazy authenticated directory/detail consumer; server-authored presentation;
    generation pairing; cancellation and stale-return rejection; clear private DOM
    on close, account/access update, hidden page and denied reads.
- path: templates/dashboard.html.j2
  what: Mount exactly one data-free shell inside the existing U.S. Prophet panel;
    preserve the principal Candidates/Plans grids.
- path: templates/_prophet_earnings_browser.html.j2
  what: Use existing details/form/buttons with EN/ZH controls and no-JavaScript explanation;
    no source records baked into HTML.
- path: templates/_prophet_earnings_browser.css.j2
  what: Governed stylesheet reuses the native evidence CSS and existing tokens; no
    runtime stylesheet or new palette.
- path: tests/test_prophet_lab_earnings_browser.py
  what: 36 source/native-presentation/runtime cases; Node fixture exercises the actual
    controller without browser or provider dependencies.
- path: .github/ci/legacy-jobs.yml
  what: Register the consumer, fixtures and tests in the existing prophet-lab job;
    declare Node20 and Jinja2. No new runner, scheduler or workflow.
prs:
- 7264
verified:
- claim: Native Lab, new consumer and incumbent complete dashboard/candidate renders
    pass.
  command: python3 -m pytest -q -p no:cacheprovider tests/test_prophet_lab.py tests/test_prophet_lab_api.py
    tests/test_prophet_lab_earnings_view.py tests/test_prophet_lab_earnings_browser.py
    tests/test_company_intelligence_workspace_chain.py tests/test_prophet_lab_timeparse.py
    tests/test_prophet_lab_commissioning.py tests/test_caddy_hub_boundary.py tests/test_dashboard_template_render.py
    tests/test_p0_prophet_candidate_board.py --tb=short --junitxml /Volumes/Mastermind/agent-evidence/prophet-d5-view-20260917/release/frontend-completion/09_native_final.xml
  result: 624 passed, 0 failed/errors/skips; 10 existing framework/OpenAPI warnings.
    Missing sparse site/theme.js input was restored from exact HEAD before the final
    run.
- claim: The UI guards distinguish three forbidden regressions.
  command: Node fixture against isolated controller copies with request epoch, generation
    pairing or error purge removed.
  result: All three produce intended AssertionError; source bytes unchanged.
- claim: Added design lines and CI manifest structure validate.
  command: check_design_system.py --mode enforce-added; run_ci_pack.py --validate-only;
    git diff --check
  result: 0 added blocking design findings; 214 jobs validate; whitespace clean.
unverified:
- claim: The new interaction and both visual themes work in actual Chromium.
  what_would_verify: Run the existing frontend-completion/browser_proof.py using synthetic
    native source/access fixtures and inspect new screenshots; its execution was platform-blocked
    and has no result.
- claim: Production users can use the upgrade.
  what_would_verify: Independent exact-head review, concluded applicable CI/security,
    ordinary release/deployment, and genuine entitled covered/unavailable/corrected
    browser proof.
- claim: Estate-wide runtime-style guard passes.
  what_would_verify: Full-checkout CI; local checker refused the sparse worktree,
    not a pass.
unresolved:
- Original expectation-revision compiler archive, B-17/identity/rights and separate
  Evaluation OS requirements remain independent; no model or outcome evaluation opened.
- 'The existing MastermindX1 review request is not a STARTed reviewer. The CI-owner
  escalation remains #6351 comment5723347088.'
next_actions:
- 'Keep PR #7264 and this source worktree. Finish actual browser/visual proof when
  execution is permitted; repair only observed defects.'
- Consume real independent review and exact-head CI/security; preserve Draft/HOLD
  until explicit expected-head release.
- Use the normal deployment owner, then verify entitled user journeys and source generation-change
  behavior.
do_not_redo:
- Do not rebuild B1, D5, authentication, the expectation compiler or the existing
  source stores.
- Do not re-run the completed collector investigation, literature synthesis or source-composition
  audit without an invalidator.
- Do not create a replacement branch or PR; these source files supersede the four
  incomplete drafts recorded in comment5723374916.
danger_areas:
- Node uses a minimal DOM fixture, not Chromium; 624 tests do not imply production/browser
  acceptance.
- The source/render fixture names and prices are synthetic, never live picks.
- No ticker-only identity joins, complete B-17 population claim, scoring, entry/hold
  instruction or persistence is added.
---

# Native earnings browser

BUILT_NOT_PROVEN. This continues the same exact source carrier. It does not complete the separate expectation-revision species or its trial.
