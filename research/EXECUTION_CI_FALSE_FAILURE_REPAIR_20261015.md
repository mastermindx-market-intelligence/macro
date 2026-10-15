# Remove two reproduced CI false failures from the async-delivery path

## Scope and consumer
This is a bounded upstream test-contract repair serving existing async-CI PR #8413, not a second implementation of its quota/Stop/native-hook policy. The parent assignment is execution throughput and robustness; parent acceptance remains an actual task advancing after its initiating Web turn ends.

Operation `execution-ci-fixture-contract-20261015-c3-9e1c`; base `7b61e274a4392584fcf3dff6fe9d9bf361eda2ed`; branch `sol/web-execution-ci-fixture-contract-20261015-c3-9e1c`. Source was acquired through the installed `mmx-workspace` owner with one writer. Protected procedure pin `78388ac29f7e54c9dfe7799a8e4769fb46d4aed6` is retained. No source custody was transferred from #8413 or the separate Mastermind sampler operation.

## Exact failing evidence
Macro #8413 head `7c541a2dc416bb9c56ffb4efa7c2e4aecf4d7562`, workflow `37237485957`, ci-pack-5 job `111539884333`:
1. `tests/test_gh_quota_guard.py::test_no_gh_command_is_denied_merely_because_a_pull_request_is_armed` rejected the generic substring `handoff`. The actual hook at that immutable head contains it only in line 766's `Codex native background-terminal handoff` diagnostic. That phrase is not the retired `CI HANDOFF IN EFFECT` denial.
2. `tests/test_prophet_rescue.py::test_the_repo_slug_matches_the_git_remote` compared the real GitHub fallback slug with `/home/runner/work/_temp/ci-base-replay-m6pc803n/origin`. The exact-base runner deliberately creates a private pinned local origin and does not supply GITHUB_REPOSITORY to the replay child. A local filesystem path is not a GitHub repository identity.

## Repair and verification
Changes are confined to the two already CI-wired test suites plus this evidence. Production quota-hook behavior, Prophet rescue code, dispatch/cancellation/rate limits, CI planner, exact-base isolation and release authority are unchanged.

The quota source pin now rejects the actual retired denial marker while its existing subprocess permission matrix still runs. New positive/negative cases prove benign native-return wording is accepted and the old deny marker remains rejected in either case.

The remote-identity pin recognizes explicit GitHub HTTPS/SCP/SSH forms and still rejects a different repository or lookalike domain. It now explicitly skips only its external-GitHub-origin comparison when the origin is a local path/file transport; it does not claim that identity was verified. The new deterministic transport matrix and every watchdog behavior test still execute in replay. The pre-existing no-origin skip remains unchanged. No blanket waiver or suite skip is introduced.

Before repair the motivating cases returned **3 failed / 8 passed**: benign handoff wording and two local-origin variants. After repair the complete `tests/test_gh_quota_guard.py tests/test_prophet_rescue.py` run returned **238 passed, zero failures/errors/skips** on the actual GitHub-origin source workspace (24.46s test time, process exit 0). A local-origin replay is expected to report precisely the one inapplicable checkout-identity assertion as skipped, while the full behavior/identity matrix still runs.

## Independent review and remaining delivery
The original independent native Codex reviewer (thread `01a13e09-8360-7110-9c5f-850ae9687ed7`) found a real regression in the first parser: authenticated HTTPS was rejected and failure output could expose userinfo. Two new tests reproduced both failures. Hostname/path parsing now uses urlsplit independently of userinfo and diagnostics omit raw URLs. The full affected suites then passed **240/240** (zero failures/errors/skips). The same reviewer resumed, verified 11 focused origin cases plus eight additional in-memory cases, confirmed the source hash before/after, and returned no remaining substantive defect. The unchanged quota analysis was reused rather than commissioned again. Exact source/test/review hashes are in `research/execution-ci-contract-verification-20261015.json`.

The local contract-delta census returned zero introduced and zero inherited findings (exit 0); it began before the final parser repair, so it is supporting evidence rather than exact-head hosted qualification. The exact #8413 hook also passed the repaired static contract without executing or changing that production hook.

Exact-head hosted CI, deliberate integration into #8413 and actual native hook activation/continuation proof remain. This source-only repair requires no production service restart. The separate #9438 instruction repair remains open at its disclosed adjacent-paragraph refusal and is not silently fixed or rerouted here. The Mastermind sampler workspace remains collision-held; none of its refused edits or other writer's changes are replayed by this operation.
