---
key: MACRO-G7-SHARED-NAV-GUARD-RED-ON-MAIN-SINCE-SHARED-SHELL
claim: >
  Since the Shared Shell integration (#7949, `ccc3242ef`) put the reviewed default-off
  All-tools include into `templates/_site_nav.html.j2` on `origin/main` itself, the G7
  guard `tests/test_macro_command_shell.py::test_shared_chrome_files_only_add_the_reviewed_default_off_host`
  (local nav minus that one include must equal `origin/main` byte-for-byte) fails on
  main's own bytes, so every pull request whose nav matches main goes red on ci-pack-6
  and ci-gate without touching the nav.
falsifier: >
  Check out `origin/main` at or after `ccc3242ef`, fetch `origin/main`, and run that one
  test; if it passes while `templates/_site_nav.html.j2` is byte-identical to
  `origin/main` and contains the include, the guard is not red on main.
so_what: >
  A ci-pack-6 red naming this test on a branch that did not touch the shared nav is
  the main-wide defect, not the branch's; repair the guard (strip the include from both
  sides before comparing, keep the exactly-once check on the local side and the
  negative case on a foreign mutation) rather than editing the nav, re-running CI or
  relabelling the pull request.
kind: landmine
verified_at: 2026-10-21
verified_by: >
  Macro worktree on `claude/options-r1-w2b-macro-1021` at `342c76e55` (nav and test
  byte-identical to `origin/main` `88afbdae82`): the test fails locally with
  `assert b'…</nav>\n' == b'…{% endif %}\n'`, the same assertion as ci-pack-6 job
  119420333078 on #9991; after the repair in `9dbf9b753` it passes on the unchanged
  template and still fails when a stray line is appended to it.
scope:
  - macro
  - tests/test_macro_command_shell.py
  - templates/_site_nav.html.j2
  - .github/ci/legacy-jobs.yml
  - WS:OPTIONS-R1
confidence: verified
---

The guard's docstring describes the Macro Command branch state ("removing that one
additive include must recover current origin/main"); once the include merged, the only
reading that keeps the guard's purpose is to strip it from both sides. The repair rides
on #9991 because that pull request was the first one blocked by it.
