# Execution entry reconciliation — October 15, 2026

## Scope and source
Part of the Chairman's execution-throughput implementation assignment. This source-only slice removes obsolete task-entry instructions; it does not modify provider permissions, release checks, hook trust or runtime ownership.

Operation: `execution-instruction-reconcile-20261015-c3-b72e`.
Base: `39d00535d992abc7b707b5b53695cbef0ae907ee`.
Branch: `sol/web-execution-instruction-reconcile-20261015-c3-b72e`.
Workspace: the exact isolated Macro worktree returned by installed `mmx-workspace acquire --repository macro`; no primary checkout was changed.

## Changes and verification
`AGENTS.md` and `CLAUDE.md` no longer direct every new task to fast-forward a shared administrative checkout and stop when that fails. They point to the existing accepted harness/workspace owner, distinguish a repairable administrative condition from real custody/permission/effect boundaries, and retain the fact that a new workspace does not transfer a started operation.

`AGENTS.md` recovers the current cumulative checkpoint and task-relevant source before old handoff chains; reading the entire historical CLAUDE document and several account-local memory entries is no longer a universal prerequisite. Account memory is advisory, not source/authority/liveness proof.

The nine new entry-contract tests were observed failing before the edits. The combined new entry tests, existing execution-continuation tests and existing ship-loop-hold-wrapper tests then completed successfully (77 cases, process exit 0). These are instruction-source and existing guard regression tests, not proof that every account/host has loaded the edited files.

## Existing adjacent implementation
Macro #8413, `claude/ssd-ci-async-continuation-3138859aac36f06b`, remains the existing async CI/ship-loop candidate, inspected at `7c541a2dc416bb9c56ffb4efa7c2e4aecf4d7562`. It owns the broader quota/Stop advice, native hook and Fable fallback changes. Do not create a competing async guard. Its body explicitly distinguishes source implementation from actual Codex hook trust and activation. Current entry changes require a deliberate path-level composition with it; this slice does not silently adopt or release it.

Mastermind #1341's earlier execution-friction work is merged. Do not redo its accepted native principal instruction installation merely to create another checkpoint.

## Remaining limitations and effects
A further edit to the adjacent legacy workspace/branch-default paragraph in AGENTS was blocked before dispatch. That paragraph remains unchanged and must be adjudicated before claiming all entrypoint contradictions resolved. It was not retried through another tool or identity.

The independent read-only native Codex review on this exact workspace completed through its original process 32677 (exit 0; 193.21 seconds). Its final artifact `/tmp/mmx-instruction-review-b72e.txt` was subsequently created and consumed. The earlier refused compound progress-log inspection was not repeated. The reviewer found P1: the new test had no CI execution owner; and P2: the adjacent legacy workspace mandate still contradicted reuse. P1 was reproduced with the canonical unrun-suite classifier, given a failing regression, and repaired in the existing `self-mod-fence` job's run step and trigger paths. The combined entry/continuation/hold-wrapper/unrun-audit tests now pass 132/132 with no failures or skips; one unrelated prior Chromium cleanup warning remains. P2 remains open at the already-recorded correcting-edit refusal. The review is substantive negative evidence, not a formal GitHub approval. Its exact subject was `d63a5ad5bbe699af3ecdc57a2cb2e463f612b018`; current source/test and review-artifact hashes are in `research/execution-entry-verification-20261015.json`. No duplicate reviewer or implementation worker was started.

The related Mastermind CI sampler work remains in operation `execution-throughput-20261015-c3-001`. It connected real GitHub input to the existing classifier and foreground wait consumer. A live read of #1201 succeeded, but two new pagination-fixture defects remain disclosed after a refused correction. Subsequent source changes were observed in that workspace from another active writer, including `tests/test_github_ci_candidate_generation.py` and the reader's workflow-job handling. This session froze that source lane rather than overwrite or publish a moving candidate. Its earlier test receipt is not proof of the later changed bytes.

No source-only change in this slice requires an application restart. Publication, exact-head CI, independent review, integration of the remaining entry wording, installation/selection and behavior across supported clients remain distinct. The parent goal—a real delivery advancing after the initiating Web turn ends—remains incomplete.
