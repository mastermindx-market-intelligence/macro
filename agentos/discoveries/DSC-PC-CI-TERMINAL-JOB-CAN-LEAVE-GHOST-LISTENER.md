---
key: PC-CI-TERMINAL-JOB-CAN-LEAVE-GHOST-LISTENER
claim: >
  A GitHub terminal failure is not sufficient evidence that a persistent PC CI
  runner stopped its local work. On 2026-09-18 all three production pc-ci
  registrations became offline after GitHub reported lost communication, while
  their systemd --once services, Runner.Worker processes, run_ci_pack.py
  processes, and pytest descendants remained alive and continued consuming the
  three-slot pool.
falsifier: >
  Disprove by showing that the exact affected GitHub jobs were not terminal
  while their local process trees remained alive, that the corresponding
  organization runners were still online, or that the local services had
  received a normal completion/deactivation edge before the observed offline
  state. A future occurrence where terminal server state reliably tears down
  the service cgroup without an operator restart also falsifies the persistence
  part of this incident class.
so_what: >
  Runner health and queue recovery must reconcile the exact GitHub job identity
  against the exact local Runner.Listener identity. Do not infer slot release
  from a terminal check alone, do not treat an active systemd unit as proof of
  GitHub connectivity, and do not solve this with a blind wall-clock timeout.
  The accepted recovery shape must preserve GitHub scheduling authority and the
  existing systemd KillMode=control-group / Restart=always lifecycle.
kind: runtime
verified_at: 2026-09-18
verified_by: >
  GitHub organization runner census, exact run/job records and check
  annotations for jobs 105415913581 / 105136067731 / 105136067709, plus WSL
  systemd journals and process trees on the production PC host. GitHub marked
  each job completed/failure with the annotation "The self-hosted runner lost
  communication with the server" while the corresponding local step-14 pack
  process remained active. pc-render-1 on the same WSL host stayed online; no
  OOM event or cache-updater contention coincided with the failure.
scope:
  - macro
  - ops/runner-host/common/runner_admission_hook.js
  - ops/runner-host/common/runner_terminal_watchdog.py
  - ops/runner-host/pc/actions-runner-ci.service.template
  - WS:RUNNER-FLEET-RESILIENCE
confidence: verified
---

The incident is a split-brain lifecycle failure, not merely a long queue. GitHub
owns job terminality and runner registration; systemd owns local listener
lifecycle. The missing seam was reconciliation after the server has already made
the exact bound job terminal but the local Listener has not exited.

The source repair stays inside those existing owners: a root-owned ephemeral
job-start helper binds the public run, exact runner name, exact active job id,
and the Listener PID plus kernel start-time ticks. It never assigns work and
carries no GitHub token. Only two confirmed terminal reads for that exact bound
job may signal the same Listener; every API ambiguity, identity drift, or read
failure is a no-op. A normal --once service exit removes the helper with the
existing cgroup.

This discovery does not claim the source patch is merged or installed. The live
three-slot pool remains offline until its current ghost services are restarted
under host administrator authority, and production acceptance still requires
exact merged-byte installation plus a natural recurrence/recovery proof.
