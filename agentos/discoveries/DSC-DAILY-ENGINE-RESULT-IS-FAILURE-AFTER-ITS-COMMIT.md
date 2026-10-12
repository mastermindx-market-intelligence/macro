---
key: DAILY-ENGINE-RESULT-IS-FAILURE-AFTER-ITS-COMMIT
claim: >
  The `engine` job of `.github/workflows/daily.yml` concluded `failure` on all five daily.yml
  runs from 2026-10-03 to 2026-10-06 (three scheduled, two dispatched). In each, the only
  failing step is the job's last one, "OIP PIT — fail closed after unrelated rendering
  completes" (daily.yml:4892, `if: always()`, running
  `bash scripts/ci/options_signal_nightly.sh assert-integrity`), and it runs after "commit
  engine outputs" has succeeded. The engine's outputs are committed, yet `needs.engine.result`
  reads `failure`, so any step or job gated on `needs.engine.result == 'success'` is skipped
  every night.
falsifier: >
  A real nightly where
  `gh run view <id> --json jobs --jq '.jobs[]|select(.name=="engine")|.conclusion'` prints
  `success`; or the OIP PIT step is removed, moved before the commit step, or passes.
so_what: >
  Never gate nightly work on `needs.engine.result`. Downstream jobs on main use `needs` plus
  the job-level `if: always() && needs.et_gate.outputs.run != 'false'` idiom with a fresh
  checkout of main; new work should copy it. A red engine job means an OIP options-signal
  integrity failure owned by the OIP lane, not a failed render or commit, so read the failing
  step before treating it as a pipeline outage. G1 (#8539) carried such a gate at c7d700f6,
  and repair RC1-R1 removed it before merge.
kind: landmine
verified_at: 2026-10-06
verified_by: >
  `gh run view <id> --json jobs` for runs 37404125352 (schedule, 10-06 02:26Z), 37402815092
  (dispatch, 10-06 02:10Z), 37250261879 (schedule, 10-05 01:08Z), 37122052286 (dispatch, 10-03
  12:11Z) and 37085692173 (schedule, 10-03 01:20Z). In each, the engine conclusion is failure,
  and the only failed step is "OIP PIT — fail closed after unrelated rendering completes"
  (step 155, or 154 on the two oldest runs), after a successful "commit engine outputs" (step
  151, or 150). `git grep -n "needs.engine.result" origin/main -- .github/workflows/` at
  0e33f448e54e returned nothing, and all nine engine-dependent jobs use the always() idiom.
scope:
  - macro
  - .github/workflows/daily.yml
  - scripts/ci/options_signal_nightly.sh
confidence: verified
---

Found on 2026-10-06 while repairing gate #8 G1 (#8539). Its first design ran the shadow write
only when the engine job succeeded, which would have skipped it on every recent night without
raising an error. No owner issue was found for the OIP integrity failure. It is routed to the
OIP lane and not fixed here.
