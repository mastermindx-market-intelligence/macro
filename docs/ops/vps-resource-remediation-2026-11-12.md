# VPS resource remediation - 2026-11-12

## Assignment and boundaries

Current user commission: implement as many safe fixes as possible for the DigitalOcean VPS without rebooting the VPS. Operation: `vps-resource-pressure-20261112`. Protected procedure pin: Mastermind `81c08810fbacad1391a0dde32893e18fc5207272` (skillpack 1.0.1, bootstrap major 1). Implementation branch: `fix/vps-resource-pressure-20261112`, based on macro `a07e3fe4ce0c465eaddc8845633d9eab9af9674e`.

No VPS reboot, resize/spend change, credential/security-policy change, broad process kill, swapoff, deletion of production data, or disabling of source/freshness safeguards. Targeted service recovery is in scope after live-state and restart preflight; preserve concurrent deployments and in-flight work. Source release uses the normal repository protections and deployment path. No worker has been dispatched. Principal executes directly for UNIQUE_APPROVED_ACCESS and LOWER_TOTAL_OVERHEAD for coupled live diagnosis/recovery.

## Outcome and acceptance

Reduce avoidable memory/CPU pressure while keeping public APIs, admin, Terminal and live-data producers functional. Acceptance requires measured before/after host/service counters, unchanged host boot identity, service HTTP/consumer checks, affected tests for source changes, and exact deployment status. A restart is stabilization, not proof of fixing a leak. Each unresolved cause stays explicit.

## Bounded task tree

- P1: Revalidate host, source generation, concurrent operations, health endpoints and API restart safety. Capture resource baseline. Reduce the excessive API memory footprint using an eligible targeted action and verify consumer recovery.
- P2: Isolate the API's retained-memory cause. Implement a bounded source correction when causally supported; otherwise record a precise remaining profiling gap, without claiming a leak fixed.
- P3: Reduce measured recurring CPU overhead without changing financial calculations, source clocks, freshness cadence, publisher ownership or delivery semantics. Test equivalence and measure the affected workload.
- P4: Inspect the already-identified failing sentinel/resource observability paths; repair safe, bounded defects and expose truthful resource measurements. Avoid unrelated Market Memory redesign or runtime activation.
- P5: Qualify owned changes for protected release, verify actual deployment/consumer behavior, and retain reproducible evidence and rollback guidance here.

## Initial evidence (read-only)

At 2026-11-12T12:33:21Z, same verified M2 Studio -> existing VPS SSH alias: API PID 3552857 active since November 9, no restarts; cgroup memory 302,477,312 bytes resident and 10,946,818,048 bytes swap. Host has 2 vCPUs, approximately 3.8 GiB RAM and 16 GiB swap; load 1.57/1.41/1.23. Deployed checkout `ee015364e5a5069e7f81b7811b27c864f11735a9` (not necessarily the running API process revision). No production changes have yet been made by this operation.

The prior investigation measured repeated live-fast work and historical high load, but did not identify an exact allocation stack. Existing configuration loader is already cached; do not introduce a redundant config cache. `/health` is not the API health endpoint (404); resolve the actual route before restart. No active TCP connection to port 8000 was observed in that one sample, which is not sufficient alone to prove no in-flight background work.

PLAN_NOT_ORG_LINKED: no existing organizational workstream identity has been established for this bounded incident. This file is the implementation/evidence record, not an Executive job, lease or new lifecycle registry.

## Current frontier

P1 restart/consumer preflight and P2 targeted source inspection. Preserve the live API until restart eligibility and baseline health are established. Record each material effect and readback below; no unattended execution claim.
