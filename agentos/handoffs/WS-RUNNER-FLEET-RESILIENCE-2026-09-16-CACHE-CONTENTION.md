---
workstream: "WS:RUNNER-FLEET-RESILIENCE"
session: "claude/ci-cache-contention-fix-20260916"
model: sol
ended_because: ci_handoff
mission: >
  Remove the trusted PC CI pool's shared Git-cache contention source end to end:
  diagnose the apparent whole-matrix deaths, preserve the existing runner/semantic
  authority planes, repair the live host, encode the fail-closed source contract, and
  carry the one source carrier through CI, merge and exact merged-byte production proof.
state_before: >
  pc-ci-1/2/3 were online and still completing jobs, but the root cache-update timer ran
  a full reachable-estate `rev-list | cat-file --batch-check` roughly every three minutes
  against a 93-GiB cache with about 7.4 million in-pack objects. One production cycle
  consumed 1 minute 22.539 seconds of CPU and peaked at 14.2 GiB outside the CI slice,
  contending with all three pack listeners and render. Explicit cancellation sweeps and
  normal PR supersession, not runner death or cgroup OOM, explained the cancelled matrices.
changed:
  - path: ops/runner-host/pc/mastermind_ci_cache_update.sh
    what: >
      Requires an explicit validated-main Git ref equal to active main; stages origin main
      at a private ref with `--refmap=`; refuses drift/non-fast-forward/missing objects;
      validates only candidate-minus-boundary objects with lazy fetch disabled; and
      atomically publishes active main, origin/main and the durable boundary while deleting
      the candidate. `.last-update-ok` is liveness only.
  - path: ops/runner-host/pc/mastermind-ci-cache-update.service
    what: >
      Adds low CPU/I/O priority, a one-CPU quota, 2-GiB MemoryHigh, 4-GiB MemoryMax and a
      five-minute timeout so disposable cache acceleration cannot jam CI or render again.
  - path: ops/runner-host/pc/mastermind-ci-cache-update.timer
    what: >
      Schedules from service inactivity with three-minute spacing plus 30-second jitter,
      preventing a slow or refused updater from creating back-to-back activations.
  - path: tests/test_ci_cache_update.py
    what: >
      Adds twelve behavioral and policy regressions covering explicit bootstrap,
      legacy-marker refusal, fast-forward publication, ref drift, missing-object and
      non-fast-forward refusal, no-op scan avoidance, maintenance prohibition, service
      bounds and timer spacing.
  - path: .github/ci/legacy-jobs.yml
    what: >
      Adds the isolated gate:code `trusted-ci-cache-update` job so these infrastructure
      contracts run in ordinary PR merge packs rather than remaining dark in gate:data.
  - path: .github/workflows/ci.yml
    what: >
      Adds the new suite to the existing Wave B/C trigger closure without creating a new
      workflow or check name.
  - path: docs/CI_SELFHOSTED_WAVE_BC_RUNBOOK.md
    what: >
      Records the incident, explicit validation-boundary law, atomic publication model,
      live measurements, resource envelope and separation from the three-slot capacity gate.
  - path: agentos/discoveries/DSC-PC-CI-CACHE-FULL-ESTATE-SCAN-JAMS-TRUSTED-POOL.md
    what: >
      Preserves the falsifiable common-cause discovery and the operating consequence for
      future queue incidents.
  - path: agentos/workstreams/WS-RUNNER-FLEET-RESILIENCE.md
    what: >
      Reconciles current capability state, owned paths, discovery, landmines and do-not-redo
      law while keeping pc-ci-4 activation separately gated.
verified:
  - claim: "The new updater's focused behavioral and resource-contract suite passes under the CI interpreter."
    command: "python3.12 -m pytest -q tests/test_ci_cache_update.py"
    result: "12 passed; only inherited pytest temporary-directory cleanup warnings on the Mac host."
  - claim: "The complete existing trusted-CI policy/canary/production-route battery remains green."
    command: "python3.12 scripts/check_runner_policy.py && python3.12 -m pytest -q tests/test_ci_cache_update.py tests/test_runner_policy.py tests/test_ci_canary_tools.py tests/test_ci_canary_workflows.py tests/test_trusted_ci_executor_workflow.py tests/test_trusted_ci_production_route.py"
    result: "Policy OK; 260 passed with inherited pytest cleanup warnings only."
  - claim: "The amended code-gate manifest is structurally valid and the curated exclusive scope covers its inferred closure."
    command: "python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --gate code --pack-count 12 --validate-only; curated_exclusive_closure_findings(.github/ci/legacy-jobs.yml)"
    result: "142 code jobs validated; trusted-ci-cache-update has no uncovered closure and all exclusive findings are zero."
  - claim: "The branch introduces no CI contract regression or dark test suite."
    command: "python3.12 scripts/check_contract_delta.py --base origin/main; python3.12 scripts/audit_unrun_tests.py"
    result: "contract-delta: 0 introduced, 0 inherited; unrun audit exit 0 with zero strictly dark suites (inherited stale-baseline warnings only)."
  - claim: "Agent OS records remain schema-valid."
    command: "python3 scripts/agentos.py validate"
    result: "0 errors; inherited repository warnings only."
  - claim: "The live candidate repair reduced ordinary updater work by about two orders of magnitude without losing ref integrity."
    command: >
      winpc/WSL `/usr/bin/time -v` candidate runs plus `git rev-parse` of
      refs/heads/main, refs/remotes/origin/main and refs/mastermind/cache-validated-main
    result: >
      43-object migration: 1.85s / 246636 KiB; unchanged cycle: 1.10s / 120624 KiB;
      subsequent scheduled cycles about 1.8s CPU; all three refs identical and candidate
      ref absent after publication.
  - claim: "The cancellation sweep did not recur after the live repair and the trusted listeners remained healthy."
    command: >
      `gh api orgs/mastermindx-market-intelligence/audit-log?phrase=action:workflows.cancel_workflow_run+created:>=2026-09-16T11:00:00Z`;
      `gh api orgs/mastermindx-market-intelligence/actions/runners`
    result: "Zero cancellation audit rows; pc-ci-1/2/3 online and busy."
unverified:
  - claim: "The final source carrier has concluded exact-head CI and squash-merged."
    what_would_verify: >
      Open the PR from the exact committed head, wait for all binding checks to conclude
      green without cancellation or bypass, and observe the squash merge on main.
  - claim: "The production PC host runs byte-for-byte the final merged source rather than the earlier live candidate."
    what_would_verify: >
      After merge, install script/service/timer from the exact main merge commit, compare
      SHA-256 values, run one immediate service cycle and one scheduled cycle, then prove
      aligned refs, absent candidate ref, timer cadence and healthy listeners.
unresolved:
  - >
    The repository delivery chain remains to be completed: commit, push, PR, exact-head CI,
    merge and exact merged-byte production installation.
  - >
    The queue can remain non-empty after this repair because live trusted capacity is still
    exactly three slots. Fourth-slot registration/promotion remains a separate authorized
    C3R-B journey and is not part of this carrier.
next_actions:
  - >
    Freeze and push the exact source head, open one ordinary PR, arm the canonical merge
    path and wait for concluded checks without cancelling queued work or dispatching a
    duplicate main baseline.
  - >
    Repair any genuine exact-head failure on the same carrier; after all binding checks
    conclude green, squash-merge without bypass.
  - >
    Install exact merged bytes on winpc/WSL from main and collect immediate plus scheduled
    service receipts, ref equality, hashes, runner liveness and cancellation-audit proof.
do_not_redo:
  - >
    Do not restore a full reachable-estate scan to the hot timer, trust `.last-update-ok`
    as commit authority, fetch directly over active refs, or publish before local delta proof.
  - >
    Do not create another cache, scheduler, queue, retry service, runner registry or semantic
    evidence plane; this repair extends the existing root cache updater and Git ref authority.
  - >
    Do not mass-cancel the queue or treat a remaining backlog as proof of runner death. The
    three-slot capacity gate is separate, and pc-ci-4 requires its own authorized ceremony.
danger_areas:
  - >
    `--refmap=` is load-bearing. Without it, a normal remote fetch refspec advances
    origin/main before validation and breaks atomic fail-closed publication; this exact
    production-shaped defect was caught during the live candidate test.
  - >
    The durable validation ref, active main and origin/main are one invariant. Manual movement
    of any one ref makes the updater refuse; reconcile under the updater lock rather than
    weakening the equality gate.
  - >
    The updater runs outside mastermind-ci.slice, so removing its own systemd resource bounds
    silently restores a shared physical-host failure domain even when runner receipts stay green.
prs: [7222]
discoveries:
  - "DSC:PC-CI-CACHE-FULL-ESTATE-SCAN-JAMS-TRUSTED-POOL"
---

# Continuation

The product-facing capability unlocked is reliable PR proof throughput: cache freshness no
longer repeatedly consumes the host's memory and CPU while pack candidates execute. The
remaining work is release and exact-byte reconciliation, not another diagnosis or architecture.
