---
key: REUSED-PYTEST-TEMPROOT-MANUFACTURES-CROSS-SUITE-REGRESSIONS
claim: >
  Reusing one `PYTEST_DEBUG_TEMPROOT` directory across runs manufactures failures that look
  exactly like real order-dependent regressions in suites the change never touched. pytest
  numbers tmp directories sequentially within a temproot, so adding tests shifts which
  directory each later test receives, and a test inherits a PREVIOUS run's persisted store
  state. Measured 2026-09-25 in the Mastermind IAC-P1 lane: a reused temproot produced
  `StateConflict: requester answer obligation identity drifted` at
  `control_plane/persisted_wake_carrier.py:622` inside `tests/test_w6c2_consultation_runtime.py`
  - a suite the change under review does not touch - and the FAILING TEST MOVED as the suite
  list changed (`..._refuses_consumed_projection` on a 6-suite run,
  `..._stays_sticky_after_consumption` on 14). The same commit on the same interpreter with a
  fresh `mktemp -d` temproot gave 685 passed, 0 failed.
falsifier: >
  Same commit, same interpreter, two runs: reused temproot produces a domain-level failure in
  an untouched suite whose identity changes with the suite list; a fresh `mktemp -d` temproot
  produces a clean run. If a fresh temproot still failed, the regression is real and this
  record does not apply.
so_what: >
  Every gate invocation gets its own directory - `T=$(mktemp -d $HOME/lanes/pytest-tmp-XXXXXX);
  PYTEST_DEBUG_TEMPROOT=$T <pytest ...>` - and that line belongs verbatim in every dispatched
  worker brief, not just in the reviewer's own runs. Do NOT delete or clean a shared temproot to
  fix this: other lanes may be mid-run inside it. Two corollaries that cost real time here: a
  baseline is a baseline only for the EXACT suite list that produced it (comparing a 6-suite run
  against a remembered 14-suite number invents a second phantom regression), and a failure whose
  identity moves between runs of the same commit is evidence of harness state, not of a code
  defect - treat a moving failure as a instrument problem until a fresh temproot says otherwise.
kind: landmine
verified_at: 2026-09-25
verified_by: >
  Reused `$HOME/lanes/pytest-tmp` run: StateConflict at persisted_wake_carrier.py:622 in
  test_w6c2_consultation_runtime.py, failing test differing between the 6-suite and 14-suite
  invocations of the same commit. Fresh `mktemp -d` temproot on the same commit and interpreter:
  685 passed, 0 failed. The shared temproot was deliberately left in place because concurrent
  lanes were using it.
scope:
  - mastermind test gates
  - any dispatched worker brief that runs pytest
  - PYTEST_DEBUG_TEMPROOT
confidence: verified
---

The reason this is dangerous rather than merely annoying is that the symptom is
domain-shaped, not infrastructure-shaped. A `StateConflict` naming an obligation-identity
drift reads as a genuine contract violation, in a file the reviewer has good reason to care
about. The tell is not the message but the instability: the same commit failing a DIFFERENT
test depending on which suites ran alongside it. That signature cost one near-miss - a
cross-suite regression report against a clean commit, one step from publication.
