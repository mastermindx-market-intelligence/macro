---
key: PC-CI-CACHE-FULL-ESTATE-SCAN-JAMS-TRUSTED-POOL
claim: >
  The root-owned PC Git-cache timer was a fleet-wide contention source: every roughly
  three minutes it re-enumerated about 7.4 million reachable objects outside the CI
  slice, with a measured 14.2 GiB memory peak and 1 minute 22.539 seconds of CPU time,
  while the three trusted pack runners and render shared the host.
falsifier: >
  Disprove with `journalctl -u mastermind-ci-cache-update.service`, `systemctl show
  mastermind-ci-cache-update.service`, the cache's `git count-objects -vH`, and a
  cgroup/process census: if the updater is not the high-RSS full-estate process during
  runner pressure, or if the bounded incremental updater still takes comparable time
  and memory on ordinary fast-forwards, this diagnosis is wrong.
so_what: >
  On trusted-PC queue congestion, inspect the root cache updater before cancelling runs
  or adding runners. Keep validation incremental from an explicit commit-bound Git ref,
  stage fetches away from active refs, atomically publish only after local object proof,
  and keep systemd CPU/memory/I/O bounds; never restore a full reachable-estate scan to
  the hot three-minute timer or treat `.last-update-ok` as commit authority.
kind: runtime
verified_at: 2026-09-16
verified_by: >
  Production winpc/WSL receipts: `journalctl -u mastermind-ci-cache-update.service`
  recorded the legacy cycle at 1m22.539s CPU and 14.2G peak; `/usr/bin/time -v` on the
  incremental candidate recorded 43 checked objects in 1.85s at 246636 KiB and an
  unchanged-main cycle in 1.10s at 120624 KiB; subsequent scheduled cycles completed
  in about 1.8s CPU while all pc-ci-1/2/3 listeners remained online.
scope:
  - macro
  - "ops/runner-host/pc/mastermind_ci_cache_update.sh"
  - "ops/runner-host/pc/mastermind-ci-cache-update.service"
  - "ops/runner-host/pc/mastermind-ci-cache-update.timer"
  - WS:RUNNER-FLEET-RESILIENCE
confidence: verified
---

The trusted runner pool and its shared cache are different resource actors. The runner
listeners stayed healthy; the root updater repeatedly consumed double-digit GiB outside
the CI slice. The accepted shape is an explicit validated commit boundary, private
candidate ref, fast-forward delta proof, atomic publication, and a bounded service.
