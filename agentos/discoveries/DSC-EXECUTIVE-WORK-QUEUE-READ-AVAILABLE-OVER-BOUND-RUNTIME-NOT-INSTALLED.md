---
key: EXECUTIVE-WORK-QUEUE-READ-AVAILABLE-OVER-BOUND-RUNTIME-NOT-INSTALLED
claim: >
  At Mastermind #943 head 98e9de09 the workspace work-queue read (operation "work") returns
  availability AVAILABLE over a REAL read-bound Runtime with no fakes: an actual SQLite Runtime,
  Runtime.at(root, create=False, read_binding=RuntimeReadBinding(namespace)), the default
  acquirer control_plane/fabric_job_view.list_roots_v2_from_runtime and the default composer
  control_plane/work_queue_projection.compose_work_queue_v1. A submitted CEO intent projects as
  one QUEUED row, the runtime observation half finalizes SAME, the namespace is entered and exited
  exactly once, provenance is PARTIAL with the root listed as unjoined, and every per-row
  producer (next_actor, capacity, effect) is UNKNOWN with reason no_producer. The production
  composition that would serve this path exists in scripts/executive_os_phase1c.py
  (workspace_provider_factory bound through the service's namespace custody) and the web edge in
  ops/executive_os/executive_mcp_entry.py (CeoIngressWorkspaceClient), but it is NOT live on the
  Mac Studio: the control LaunchDaemon plist exists and is not bootstrapped, so no installed
  AVAILABLE read has ever been served.
falsifier: >
  A tests-only reproduction (real Runtime, real RuntimeReadBinding, default acquirer and composer)
  returning UNAVAILABLE for a submitted intent; or launchctl print system/com.mastermind.executive.control
  reporting the service loaded while no installed work read has been served; or a per-row
  producer value other than UNKNOWN/no_producer without an accountability, placement or effects
  producer being wired.
so_what: >
  The read seam is proven at source level, so the next backend work is producers and the install
  ceremony, not more projection repair. Wire real accountability/placement/effect producers behind
  the composer's typed inputs; do not fake them in the edge. Installed proof waits on the ruled
  exact-generation install (after #942 and the same-owner readiness invalidation repair). Test
  harness trap: the namespace capability compares the exact database path, so on macOS a /var
  temporary directory must be resolved to /private/var or the bound read refuses and the acquirer
  swallows it into a runtime_observation_not_same refusal.
kind: runtime
verified_at: 2026-09-24
verified_by: >
  Fable delivery principal, 2026-09-24 06:10Z, scratch reproduction over
  tests/test_workspace_source_join.py's fixture pattern against #943 head 98e9de09
  (control_plane/workspace_read_service.py::_read_work, control_plane/fabric_job_view.py:1795-1850,
  control_plane/work_queue_projection.py:818-930); production composition read at
  scripts/executive_os_phase1c.py:1670-1725 and ops/executive_os/executive_mcp_entry.py:212-217;
  host state: /Library/LaunchDaemons/com.mastermind.executive.control.plist present,
  launchctl print system/com.mastermind.executive.control = not found. Tests-only proof
  commissioned as WQ-E2E-1 (branch claude/work-queue-e2e-binding-20260924).
scope:
  - Mastermind
  - agent-fabric-end-to-end-fable-integration-20260913-sol-001
  - control_plane/workspace_read_service.py
  - control_plane/work_queue_projection.py
confidence: verified
---

# The work-queue read is AVAILABLE over a bound Runtime, but nothing installed serves it

The #943 projection is not the blocker: over a real read-bound SQLite Runtime the `work`
operation composes a QUEUED row for a submitted intent with a SAME runtime observation and a
balanced namespace entry/exit. What is missing is (a) the three per-row producers, which all
report `no_producer`, and (b) the installed control service on the Studio, whose LaunchDaemon
plist exists but is not bootstrapped. The first is source work on the composer's typed inputs;
the second is the ruled install ceremony.
