---
key: COMMODITY-RELEASE-JITTER-PROOF
claim: >-
  Candidate d5d57998ee53e5187664e5e953eb81146474c700 replaces a stochastic retry-policy mean test with a complete
  jitter-support comparison; the runtime policy and 1.5x inequality are unchanged.
  Seventy-nine tests pass and six deliberate runtime regressions are detected.
  The candidate is unmerged and not hosted or production acceptance.
falsifier: >-
  Run python3 -m pytest tests/test_push_retry.py -q on the exact candidate,
  then reproduce a failed stated support/mean or an undetected supplied mutant.
so_what: >-
  Obtain independent review and concluded CI for this test-only dependency before
  using it to repair #7215 proof. Do not rerun the original random sample until
  lucky, waive ci-gate, change retry budgets, or claim #7198/#7224 deployed.
kind: landmine
verified_at: 2026-09-17
verified_by: >-
  Source d5d57998ee53e5187664e5e953eb81146474c700; COMMODITIES_RELEASE_JITTER_PROOF_2026-09-17.json:
  79 passed, six of six mutant policies detected; actual Bash seeded counterexample.
scope: [macro, tests/test_push_retry.py, scripts/ci/push_retry.sh]
confidence: verified
---

# Commodity release test repair — not a runtime retry change

Operation: commodities-release-jitter-proof-20260917-sol-001. Parent delivery: commodity safety #7198 / asset read #7224.
Shared parser dependency #7215 failed in this exact push-retry-policy test; its base
replay was unavailable, not known green. The seed demonstration establishes one
real failure of the former sampled expectation on a correct library. It does not
recover the historical CI random state or certify all possible failure causes.

Observed local shell: GNU bash, version 5.3.9(1)-release (aarch64-apple-darwin24.6.0).
The full suite uses local disposable Git remotes, the unchanged runtime library,
and exact pinned workflow/body dependencies. Production is not written.

Next: independent exact-head review, current integration and concluded CI, then
reconcile #7215 through existing release owners. R1/R2 remain draft/held. The
calibration-origin edit remains blocked on its original operation; do not retry it
through this test branch, a different actor, or another tool.

Current source law: Mastermind eec5324c5205e8bad206512e0a936898e50b2408, Skillpack 1.0.1.
No new worker, queue, reviewer lifecycle, retry service, permissions, provider,
calibration, portfolio position or trade authority was created.
