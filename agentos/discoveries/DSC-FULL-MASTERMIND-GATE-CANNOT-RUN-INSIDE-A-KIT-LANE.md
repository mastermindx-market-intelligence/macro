---
key: FULL-MASTERMIND-GATE-CANNOT-RUN-INSIDE-A-KIT-LANE
claim: >
  The full Mastermind repository gate `python scripts/ci_pytest.py` (632 modules) cannot complete inside a kit
  worker lane on the Mac Studio: the lane venv lacks fastapi/claude_agent_sdk/reportlab/lib (17 collection
  errors), `vendor/macro` is a dangling symlink locally (hosted CI checks out macro at
  256c757b3c4f0ec759571c29a30a71387d0a18f8 sparse engine+lib into `vendor/macro_src` and runs
  `pip install -e ".[dev]"`), and the lane session cap killed a run at 18% (1471 s) — one writer lane died
  silently mid-task (no effect; the patch was preserved).
falsifier: >
  A kit lane completing `python3 scripts/ci_pytest.py` green within its cap on this host. Concretely: run the
  gate in a kit worker lane on the Mac Studio and read the final exit code and elapsed wall time before the
  lane cap fires; rc=0 inside the cap refutes the claim.
so_what: >
  Writer lanes must not treat the full repository gate as a local acceptance step: run RED/GREEN, focused
  suites and `compileall`, commit and push, and let the hosted required `test` check be the authoritative
  real-gate run. Any attempt to build a local replica must check out the pinned macro source plus dev extras
  and must run detached — macOS has no `setsid`, so use `nohup`.
kind: constraint
verified_at: 2026-09-17
verified_by: >
  Child-session lane receipts, NOT re-run by this fold: `python3 scripts/ci_pytest.py` inside a kit worker
  lane was killed at 18% (1471 s) by the lane session cap; the lane venv produced 17 collection errors
  (fastapi, claude_agent_sdk, reportlab, lib); `vendor/macro` was observed as a dangling symlink in that
  lane. Re-checked by this fold on 2026-09-17:
  `gh api repos/mastermindx-market-intelligence/Mastermind/contents/scripts/ci_pytest.py?ref=e878878c9a4ae2dd50a48d825e031e07e8211708`
  returns the gate file (type file, size 16904), and
  `gh api repos/mastermindx-market-intelligence/macro/commits/256c757b` returns
  `256c757b3c4f0ec759571c29a30a71387d0a18f8` (2026-08-09), so the hosted checkout pin the hosted lane uses
  exists.
scope:
  - mastermind
  - macro
  - scripts/ci_pytest.py
confidence: probable
---

## Why `probable` and not `verified`

The mechanical sub-facts are observations from a real lane run (a killed process at a measured 18% / 1471 s,
specific missing distributions, a dangling symlink), and the gate's entry point plus the hosted macro pin
were re-checked by this fold. The claim as phrased is nevertheless an induction over lanes and hosts from a
single lane's failure. The falsifier above is cheap and untested: one kit lane finishing the gate green
inside its cap would refute it, and no such run has been attempted since the observation.

## The two failure modes are different, and both are lane-local

1. **Missing distributions.** The lane venv is not the dev environment Mastermind's gate expects, so 17
   modules fail at collection before any test runs. This is not a source defect and not a test failure: it is
   an environment gap that a lane cannot fix by re-running.
2. **Wall-clock versus the lane cap.** Even with the venv repaired the run needs longer than the lane cap
   allows on this host, so the failure mode becomes a silent kill mid-run. One writer lane died this way
   without reporting; the patch it held survived, so the loss was time and signal, not work.

## What a local replica would actually require

A faithful local replica needs the pinned macro checkout materialised at `vendor/macro_src` (hosted CI checks
out `256c757b3c4f0ec759571c29a30a71387d0a18f8` sparsely — engine and lib only) plus
`pip install -e ".[dev]"` for the dev extras, and it must run detached because macOS has no `setsid`; the
portable form is `nohup`. Without those, a lane's local result is a statement about the lane, not about the
repository.

## Consequence for how writer lanes report

The authoritative real-gate run is the hosted required `test` check on the pushed head. A lane's own evidence
is RED/GREEN on the changed behaviour, focused suites around the change, `compileall`, and the commit plus
push; anything stronger claimed from inside a lane needs the replica above or the hosted run.
