---
workstream: "WS:RUNNER-FLEET-RESILIENCE"
session: "Sol:pc-windows-update-reboot-recovery-20260915"
model: sol
ended_because: blocked
mission: >
  Recover the trusted PC CI pool after an involuntary Windows Update reboot and make
  the reboot path self-healing without creating a second scheduler or silently
  activating pc-ci-4. Separately preserve the Chairman request to audit MarketDesk,
  earnings and local Qwen resource use before any fourth-slot capacity decision.
state_before: >
  Windows host winpc returned on Tailscale after the update reboot, but winpc-wsl,
  Remote Desktop Commander on winpc/WSL, pc-ci-1/2/3 and pc-render-1 all remained
  offline. Windows TCP/3389, 135, 139 and 445 were reachable; SSH and WinRM were not,
  SMB required credentials, and there was no authenticated noninteractive carrier
  from the M2 into Windows. GitHub therefore had zero online trusted PC CI slots.
changed:
  - path: ops/runner-host/pc/windows/Start-MastermindWslBootRecovery.ps1
    what: >
      Adds a bounded Windows-side recovery action that verifies the exact per-user
      WSL distribution, starts only that existing distro, confirms it remains in the
      running census, retries boundedly and writes status-only recovery logging.
      It does not register, relabel, supervise or dispatch a GitHub runner.
  - path: ops/runner-host/pc/windows/Install-MastermindWslBootRecovery.ps1
    what: >
      Adds an elevated installer for an AtStartup Task Scheduler entry under the
      exact Windows identity that owns the WSL distro. It uses S4U so the password is
      not stored, starts immediately for verification, and refuses installation if
      the requested distro is not visible to that identity.
  - path: tests/test_ci_canary_tools.py
    what: >
      Pins that Windows recovery only starts WSL and cannot contain pc-ci-4,
      ci-linux, runner registration or Runner.Listener lifecycle logic.
  - path: docs/CI_SELFHOSTED_WAVE_BC_RUNBOOK.md
    what: >
      Records the Windows/WSL two-layer recovery law and requires a controlled real
      reboot proving no-login WSL plus exact runner recovery before acceptance.
verified:
  - claim: "Focused source invariants for boot recovery and existing PC runner isolation pass."
    command: "python3 -m pytest -q tests/test_ci_canary_tools.py -k 'windows_boot_recovery or runner_service_seals_runtime or ci_slice'"
    result: "10 passed, 110 deselected; inherited pytest cleanup warnings only"
  - claim: "Agent OS remains structurally valid."
    command: "python3 scripts/agentos.py validate"
    result: "0 errors; 49 pre-existing warnings"
  - claim: "The Windows host is back but WSL and trusted runners did not auto-recover."
    command: "Tailscale/Remote Desktop Commander/GitHub live census from M2"
    result: >
      winpc reachable on Tailscale; winpc-wsl and Windows/WSL Remote Desktop Commander
      offline; pc-ci-1/2/3 and pc-render-1 offline.
unverified:
  - claim: "The new startup task works under the real Windows owner identity after a reboot."
    what_would_verify: >
      Restore one authenticated Windows carrier, install from exact merged source with
      the exact WSL distro name, perform a controlled reboot, and prove the distro plus
      exact pc-ci-1/2/3 identities return without interactive login.
  - claim: "A fourth PC CI slot is safe with current desktop/MarketDesk/earnings load."
    what_would_verify: >
      After WSL recovery, capture host/guest CPU, RAM, swap, GPU and cgroup pressure,
      identify MarketDesk/earnings/local-model processes and compare headroom against
      the separately frozen C3R-B four-slot gates. Do not activate pc-ci-4 before this.
unresolved:
  - >
    Immediate host recovery is blocked at the Windows control boundary: the host is
    online but the previously authorized remote-command agent did not auto-start and
    there is no current SSH/WinRM session. One owner-session Windows action is needed
    to start WSL or restore the command agent before Sol can install/prove the task.
  - >
    MarketDesk/earnings/Qwen placement is intentionally not changed in this carrier.
    The Chairman reports heavy PC lag while WSL/local inference is active; live process
    and resource evidence must decide whether existing model-router/external compute
    should replace resident Qwen before deciding pc-ci-4.
next_actions:
  - >
    Re-enter the Windows owner session once, start the production WSL distro, then
    immediately re-census pc-ci-1/2/3 and the remote command agent before any retry.
  - >
    Install the reviewed boot-recovery task under the exact distro-owning Windows
    identity and execute one controlled reboot acceptance. Keep pc-ci-4 absent.
  - >
    With WSL live, audit MarketDesk/earnings/Qwen deployment and measured resources;
    prefer the existing router/provider plane over a new inference control plane if
    remote inference satisfies the product latency/cost/privacy contract.
danger_areas:
  - >
    Task Scheduler principal identity is part of correctness because WSL distributions
    are per Windows user. Real-host acceptance must prove the task sees the exact
    production distro before relying on unattended recovery.
  - >
    A Windows Update reboot can simultaneously remove WSL capacity and the remote
    command carrier. Recovery acceptance therefore includes both runner liveness and
    restoration of an authenticated management path; neither implies the other.
  - >
    The PC is also reported to carry interactive Windows work and possibly resident
    local-model inference. Do not infer fourth-slot headroom from WSL limits alone.
do_not_redo:
  - >
    Do not create another CI scheduler, runner registry, service supervisor or queue.
    GitHub Actions and the existing Linux systemd services remain canonical.
  - >
    Do not run the WSL startup task as LocalSystem: production WSL distributions are
    per Windows user and may be invisible to a different principal.
  - >
    Do not activate pc-ci-4 as part of reboot recovery. C3R-B and current resource
    proof remain separate gates.
prs: []
---

# Status

Source recovery is **BUILT_NOT_PROVEN**. The real Windows host still needs one
owner-context re-entry because the update reboot also removed every authenticated
noninteractive control path into Windows. No host mutation, runner registration,
label change, slot-4 activation, MarketDesk change, model change or production proof
has been claimed in this carrier.
