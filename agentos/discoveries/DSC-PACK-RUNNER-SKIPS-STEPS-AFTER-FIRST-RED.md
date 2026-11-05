---
key: PACK-RUNNER-SKIPS-STEPS-AFTER-FIRST-RED
claim: >
  scripts/run_ci_pack.py skips every remaining `run` step of a legacy job
  once one step fails, and supports no per-step `if`/`continue-on-error`, so
  a job that hosts several independent gates only ever reports its FIRST red;
  and a job with no `paths:` is not always-on — infer_job_scopes derives a
  scope from its commands, and mockups/ is outside every opaque scan root.
falsifier: >
  Read the step loop in scripts/run_ci_pack.py (`if failure is not None:`
  marks later steps skipped; ALLOWED_STEP_KEYS has no `if`), or replay ci run
  36036232964 pack-3: design-governance's forward-only design ratchet exited 1
  and the p0b receipt-closure step never executed. For the scope half, run
  `run_ci_pack.py --plan-only --changed-from origin/main` with a changed list
  of only mockups/evidence/prophet-p0b-zero-fouc/rendered-fixture.json on the
  pre-fix manifest: 3/158 jobs, design-governance skipped.
so_what: >
  Give every independent gate its own legacy job (curated `scope: exclusive`
  paths naming the roots its subject lives under, bound to the subject by a
  test), never trailing steps on a sibling gate; and never describe a job
  without `paths:` as "always-on" — measure its selection on the diff shapes
  it must catch. #6872 (2026-09-24) merged with the p0b receipt gap unreported
  and put ci-pack-9 red on main for hours; the gate now lives in
  `p0b-receipt-closure`.
kind: landmine
verified_at: 2026-09-24
verified_by: >
  ci run 36036232964 job ci-pack-3 log (design-governance step 'forward-only
  design ratchet' exited 1; no p0b step group followed); local planner
  reproduction on the pre-fix manifest; scripts/run_ci_pack.py step loop and
  ALLOWED_STEP_KEYS.
scope:
  - macro
  - scripts/run_ci_pack.py
  - .github/ci/legacy-jobs.yml
  - scripts/check_p0b_receipt_closure.py
confidence: verified
---

The pack runner emulates a GitHub Actions job: steps run in order and the
job stops at the first failing step. Two gates in one job therefore report
sequentially across PR pushes, and the second one is invisible whenever the
first is red — which is exactly when a session is least likely to look for
it. Selection is a separate trap: "unscoped" in the manifest means
"inferred", and inference reaches only the roots in OPAQUE_IO_ROOTS.
