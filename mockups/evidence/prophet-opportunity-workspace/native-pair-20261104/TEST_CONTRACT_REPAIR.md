# Prophet #9495 — closed-plan and Priority test-contract repair receipt

Date: 2026-11-04 UTC. Original Draft PR #9495 branch `claude/ssd-prophet-opportunity-system-20261015-5ba805642dd9aece`.

## Why the follow-on code commit was required

The native pair publication reached `7eda300acfa67a0a51d3e40c777800e5a7c71230` with 12/12 generation/protection guards and 16 offline anonymous captures. Its focused 11-suite test census exposed **9 failures** already reproduced on pristine source head `e5c288011f026cb74b2a2e265d6dfc767359565d` (they were not created by the native pair).

Follow-on commit `94bb0c06cfb8376f8285148cfda4688f03efc611` changes **exactly two test files**, without altering entitlement, ranking, published data, Paper design or production code:

1. `tests/test_prophet_w1_intake_repair.py`: a closed plan's pulse must not show a growing holding age. Age and horizon clock remain in raw row fields. The synthetic test's purported LIVE fixture previously hit the mock rising price panel's ordinary 115/130 targets, so it legitimately closed even without a forward-ledger row. The explicitly-live fixture now uses targets beyond that synthetic range; blocked, closed and open tests retain their separate controls. Live pulse checks the correct horizon clock rather than signal age.
2. `tests/test_us_board_priority_ui.py`: legacy copy called a higher rank more ready to trade and not more likely to win. The current safer production copy says Priority is a published **ordering score**, not entry permission or a win probability. The tests now assert that precise EN/ZH warning; the stage-tip test checks all five rendered tips, not a vacuous sentence appearing only in the footer. Featured shelf and runway notes are checked against the current honest wording.

## Actual local test proof

An isolated, detached worktree at parent `7eda300a` on the authorized Ubuntu0 host was edited and tested with the pre-existing `/home/ubuntu0/lanes/venv/bin/python` environment. Two affected suites: `tests/test_prophet_w1_intake_repair.py::TestIndexHygieneEndToEnd` and `tests/test_us_board_priority_ui.py`: **48 passed, 22 skipped, 0 failures** (63.63 s). Strengthened five-stage EN/ZH tooltip test was rerun separately: **1 passed** (3.41 s). `git diff --check` was clean; staged delta only 2 files, 44 insertions / 17 deletions. Non-force push verified by original branch CAS/fast-forward and GitHub compare.

## Hosted CI distinction and remaining acceptance

Exact head `94bb0c06` has successful `ci-authority` run `41904483842`. The full hosted `ci` and `fences` runs were **not present** for that head at the last census. Draft status alone is not established as the cause: separate Draft D03 PR #10617 does receive these workflows. A connector-identity or event-delivery difference is a hypothesis, not a verified cause. This note is a durable evidence receipt, not permission to weaken required checks or mark Ready. Treat any new exact-head CI as new evidence only after its actual completion.

Still unproved: updated Save screenshot on a public Featured card (the coherent Nov 3 board has public Featured count 0), authenticated Save/list readback/reopen, signed-in Sources → Plan → same-candidate return, native source/backend acceptance and all release/production/browser obligations. The historical Save receipt is preserved. No merge, Ready/un-draft, queue, deploy, purchase, account or trade effect was performed here.
