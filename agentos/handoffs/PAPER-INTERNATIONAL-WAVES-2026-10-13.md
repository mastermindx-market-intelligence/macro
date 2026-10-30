---
workstream: WS:PAPER-INTERNATIONAL-WAVES
session: sol/manual-paper-waves-01a1101f-release-r2
model: codex
ended_because: ci_handoff
mission: Complete the International programme through its existing owners while preserving release and effect holds.
state_before: Preparation documents were complete, the broader programme remained incomplete, and Terminal PR804 execution custody belonged to IW2.
changed:
- path: templates/intl_workspace.js
  what: Restore native research controls from committed state when Scenario refuses a context change during reset confirmation.
- path: site/intl_workspace.js
  what: Exact derived copy of the repaired canonical controller.
- path: site/intl_workspace.css
  what: Replace an inherited stale derived copy with the unchanged canonical Overview CSS.
- path: tests/intl_workspace_history_controller.test.cjs
  what: Six real-browser regressions cover horizon, basis and market rollback before reset cancellation and confirmation.
- path: research/paper_international_wave1_wave2/J07_RESET_ROLLBACK_ACCEPTANCE.json
  what: Bind exact source and retained red/green, full-page, live and independent-review evidence with acceptance limits.
verified:
- claim: The initial source carrier was clean and still bound to the existing draft PR8754.
  command: git status --short; git log -1 --format=%H; gh pr view 8754 --json headRefOid,isDraft,state,autoMergeRequest.
  result: Clean at 1c4b124b8d67ea8e277709831e2c3fc3b601d62e; OPEN/Draft with no auto-merge request.
- claim: The live reset/context mismatch is reproducible through visible browser controls.
  command: CUA existing Chrome profile; calculate5/-3, request reset, select3m, cancel reset with Escape.
  result: Selector displayed3m while Scenario and URL retained1m. Signed-in existing-profile calculation and recovery otherwise worked. Fresh anonymous context separately returned401 for five controllers.
- claim: New tests distinguish the faulty and repaired behavior.
  command: NODE_PATH=<existing inspector/node-test-deps> PLAYWRIGHT_CHROMIUM_CHANNEL=chrome node --test --test-name-pattern='reset confirmation restores a refused' tests/intl_workspace_history_controller.test.cjs, before the repair.
  result: Six expected assertion failures on original source; initial missing-module environment error was separately retained and resolved using the existing Python Playwright driver package.
- claim: The affected controller, draft and arithmetic tests pass after repair.
  command: Same environment; node --test tests/intl_workspace_history_controller.test.cjs tests/intl_workspace_scenario_draft.test.cjs tests/intl_workspace_scenario_math.test.cjs.
  result: 119 passed, zero failed or skipped. Counts overlap the broader browser suite and are not additive.
- claim: The complete existing International browser regression closure passes locally.
  command: Same environment; node --test --test-concurrency=2 over the eleven controller/page test files listed in the international workspace browser job in .github/ci/legacy-jobs.yml.
  result: 184 passed, zero failed or skipped. No retired CI run was queried.
- claim: The actual full-page composition preserves reset confirmation and restores all three controls.
  command: python3 <evidence>/j07-live-20261013-r1/local_reset_rollback.py.
  result: Twelve cases passed across EN/dark1440 and ZH/light320 with doubled text. This is synthetic local rendering, not native zoom or deployed repair acceptance.
- claim: Canonical and derived presentation copies agree after synchronization.
  command: python3 scripts/check_template_site_sync.py.
  result: All114 pairs match. The inherited stale site/intl_workspace.css was replaced byte-for-byte from the unchanged canonical template.
- claim: Both new bounded Fabric reviews were consumed and parent-adjudicated.
  command: Same-id fabric_task.py result, then accept --by reviewer and status for paper-01a1101f-j07-browser-review-20261013-r1 and paper-01a1101f-j07-reset-rollback-review-20261013-r1.
  result: Both terminalrc0/REMOTE_CLEANED and ACCEPTED/VALIDATED_OUTCOME. Usage receipts missing. Parent corrected speculative source claims; worker reviews did not execute browsers.
unverified:
- claim: Deployed reset rollback, complete Paper/live parity and accessibility acceptance.
  what_would_verify: Lawful publication after retained release gates, followed by fresh served journeys, full theme/locale matrix, native zoom and behavioral accessibility proof.
- claim: Genuine International Saved and current source qualification.
  what_would_verify: Real existing-owner admission, trusted caller context, lawful qualified inputs and same-owner save/readback/reopen evidence.
unresolved:
- Original qualifier/proc2217592/environ EFFECT_UNKNOWN, three pre-START reviews and T03k fifth platform refusal remain frozen.
- Original asset-access review remains frozen pending supported same-run recovery; new reviews do not replace it.
- Release5989604142, migrations0030/0031/0032, source-rights and current Saved admission holds remain.
- Initial served ZH option labels were English until language roundtrip; current served theme.js differs from the local candidate. Full bilingual parity is not accepted.
next_actions:
- Complete publication and genuinely new exact-head CI for this accepted Macro source repair on the same draft branch; preserve no-ready/no-merge/no-autoarm/no-deploy holds.
- Use only new authorized material evidence to resolve the original frozen review, qualifier and source-rights boundaries; never retry or replace uncertain effects.
- After lawful release, verify the repaired reset/context interaction and anonymous asset serving in the appropriate real sessions.
do_not_redo:
- Do not regenerate the completed mission-acceptance-20261013-r1 preparation package.
- Do not query retired Macro CI38128192510 or retired Terminal CI runs to support this new source.
- Do not repeat the eight-case120-assertion pre-repair page run, completed184-test regression or twelve-case full-page check absent relevant change.
- Do not consume or accept either new review result a second time.
danger_areas:
- IW2 thread01a104c8-6e11-7e52-93c1-6b8dbc45bb9c exclusively owns Terminal PR804 source/capture/server/push/CI; no handback occurred.
- Existing signed-in browser success does not establish anonymous delivery or isolate authentication from cached-asset effects.
- Local text scaling is not native browser zoom; historical screenshot matrices do not prove this whole programme complete.
- Native03342a8d remains DO_NOT_DELIVER; existing Desktop consent and original uncertain-effect boundaries remain.
prs:
- 8754
---

Evidence is retained at `/Volumes/Mastermind/evidence/paper-waves-20261006-01a1101f/j07-live-20261013-r1`.
The original root is `01a1101f-2a37-7320-9a9b-5df3ce1b890d`. This is a knowledge-plane checkpoint,
not a lease, handback, review replacement or release decision. No Terminal checkout/PR/CI, Paper canvas,
database, migration or frozen operation was changed. Browser test assumptions were cleared and the
original explicit Dark/Chinese settings and browser viewport restored.
