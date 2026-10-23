# Commodity publication dependency — deterministic retry-policy proof

Operation: `commodities-release-jitter-proof-20260917-sol-001`. Parent mission: asset-first commodities repair, #7198 / #7224.
Dependency unlocked: #7215's pack-6 failure in the existing `push-retry-policy` unit.
Current procedure: Mastermind `eec5324c5205e8bad206512e0a936898e50b2408`, Skillpack 1.0.1.
Source writer: Sol via the existing attended Studio / Remote Desktop / gh carrier.
Direct execution reason: CRITICAL_PATH_SHORTCUT; no eligible independent worker has
started this test repair. This is not authority to bypass independent review.

## Mission and scope

Make the existing policy test prove its intended contention-versus-conflict wait
expectation without rejecting correct behavior through sampling noise. Preserve
real jitter, the 1.5x comparison, retry budgets/caps, classification, and all
runtime implementation. Change only `tests/test_push_retry.py` and these records.
No service, queue, retry engine, CI workflow, provider, live data or trading policy
is added or changed. No retry was sent for the original failed CI run.

## Root cause and observable falsifier

The old test compared 60 independent random draws per class. The existing real
Bash function at attempt 1, with seeds 57 and 7976, produced sums 308 and 462.
Its unchanged inequality `mean_c * 1.5 < mean_x` therefore fails on a legal draw.
This is a reproducible demonstration of stochastic-test instability, not a claim
that the lost original CI random seed has been recovered. The CI semantic artifact
already names this exact failing unit; its base replay was unavailable and was not
misrepresented as proof of an inherited green baseline.

The test now enumerates the complete intended jitter residue support for both
classes at attempts 1, 3, 5 and 8. The source library runs unmodified. `RANDOM` is
an ordinary input only inside disposable test shells; the test clock is fixed so
wall-clock budget clipping cannot censor this distribution test. Separate tests
still check real jitter and deadline enforcement. All endpoint/count checks are
explicit; no tolerance or threshold is weakened and no retry-until-green is used.

## Exact-source proof

Base: `3daf739affa12a43a6b3a0feb3b4c57154587756`. Test preimage: `8b288c5361e1167e2fadffd5bee62809709c3477`.
Production library preimage: `15dcf175576e4453dc2570c2977ecbafd8ad15c4`; unchanged at observed main `12b655150582d9be39bfd2779b33338d154c565f`.
The exact workflow/body dependency snapshot includes 98 workflow files and 16
referenced step bodies, not a partial empty-workflow fixture.

- New contract baseline: 9 expected failures, 70 deselected.
- Bounded backoff checks: 14 passed, 65 deselected.
- Entire existing test file plus new cases: 79 passed, zero failures.
- Six deliberate policy defects are detected: slow contention, fast conflict,
  no runtime jitter, lost upper endpoint, raised contention cap, and removed
  deadline cap. No unexpected harness error counted as detection.
- Real Git-race/lane tests remain in the complete suite. Their remotes are local
  disposable repositories; no production source/data/remote is written.

Reproduce: `python3 -m pytest tests/test_push_retry.py -q` on this candidate.
The accompanying JSON retains the original reproduction, source identities,
full test output and per-mutation failures. No fresh market or model claim is made.

## Release and continuation boundary

DRAFT / HOLD-FOR-SOL / BUILT_NOT_PROVEN. A local green is not hosted acceptance.
Independent review, concluded applicable CI and current-main compatibility are
still required before merging; no Ready, auto-merge, bypass or deployment occurs.
After this test repair is accepted through the normal owner, reconcile #7215's
existing source with that repair and obtain the appropriate current test proof.
Do not fork another parser or rewrite production retry logic. Keep #7198/#7224
and the existing HK #7163 dependency on their original branches and owners.

The calibration-origin disclosure on #7224 remains a separate blocked edit; this
change neither implements that refusal nor routes it through another actor.
Next action is review/CI for this test-only dependency and the same release chain.
Do not repeat the original stochastic test until lucky or weaken release checks.
