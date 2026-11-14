# CI shared-cache contention repair implementation plan

> **Owner:** Mastermind CI fleet. Execute test-first and ship through the repository's full commit → PR → CI → merge → live-host acceptance chain.

**Goal:** Stop the root-owned PC shared Git-cache updater from consuming double-digit GiB every few minutes while preserving a fail-closed, immutable validation boundary for the three trusted CI runners.

**Root cause:** The timer runs a full `rev-list` plus `cat-file --batch-check` over roughly 7.4 million reachable objects on every activation. On the production 93 GiB cache this peaked at 14.2 GiB and ran for 70–120 seconds every three minutes outside the CI resource slice, contending with all three pack runners and render. The runner pool itself remained live; explicit cancellation sweeps and normal per-PR supersession explained the apparent whole-matrix deaths.

**Design:**

1. Fetch `main` into a staging ref, never directly over the active cache ref.
2. Record the last validated boundary as a private Git ref and update it atomically with `refs/heads/main` and `refs/remotes/origin/main`.
3. On an ordinary fast-forward, validate only objects newly reachable from the candidate and not the validated boundary. Refuse non-fast-forward drift rather than falling back to a full-estate scan.
4. Treat `.last-update-ok` as liveness only. Create the durable boundary explicitly after reconciling the supervised legacy full-scan receipt with the exact active/remote refs; a new or recovered cache must pass the same out-of-band bootstrap proof.
5. Bound the updater with low scheduling priority, a one-CPU quota, a 2/4 GiB memory envelope, and a five-minute timeout. Space timer activations from service completion.
6. Install the merged bytes on the PC host, re-enable the timer, force one candidate update, and prove low memory, bounded duration, exact refs, healthy runner throughput, and no new cancellation sweep.

**Verification:**

- Behavioral updater tests: legacy-marker refusal, explicit bootstrap, no-op, fast-forward delta, atomic publication, missing trust boundary refusal, non-fast-forward refusal, and simulated missing-object validation leaving active refs untouched.
- Unit policy tests for service and timer resource bounds.
- Existing CI canary and runner-policy suites.
- Production host systemd and Git receipts before and after one scheduled cycle.
