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
      Verifies the exact per-user WSL distribution and holds one inert foreground
      keepalive so the distro remains resident. Microsoft documents that systemd
      services do not keep WSL alive; if the keepalive exits, the wrapper retries indefinitely with a bounded delay
      and writes status-only recovery logging. It does not register,
      relabel, supervise or dispatch a GitHub runner.
  - path: ops/runner-host/pc/windows/Install-MastermindWslBootRecovery.ps1
    what: >
      Adds an elevated installer for AtStartup plus AtLogOn fallback triggers under
      the exact Windows identity that owns the WSL distro. It uses S4U so the password
      is not stored, IgnoreNew to prevent duplicate keepalives, an unlimited execution
      window for the resident task, and refuses installation if the requested distro
      is not visible to that identity.
  - path: tests/test_ci_canary_tools.py
    what: >
      Pins the long-lived WSL residency contract, forbids the false-green one-shot
      no-op wake, and proves the Windows layer cannot contain pc-ci-4, ci-linux,
      runner registration or Runner.Listener lifecycle logic.
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
  - claim: "A one-shot owner-context WSL wake is insufficient even though it temporarily restores CI."
    command: "Chairman ran wsl.exe -e true; GitHub/Remote Desktop/Tailscale were re-censused from M2"
    result: >
      pc-ci-1/2/3 returned online and busy and pc-render-1 returned online/idle, then
      all four returned offline after the WSL instance stopped. The WSL remote agent
      checked in briefly at 04:46:20Z. This matches Microsoft's documented rule that
      systemd services do not keep a WSL instance alive.
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
    Immediate host recovery is narrowed to WSL residency: Windows is online but the
    Windows remote-command agent did not auto-start, and the WSL agent disappears when
    the distro exits. One owner-session `wsl` shell kept open is needed to hold the
    guest resident long enough for Sol to inspect service state and install/prove the
    corrected recovery task.
  - >
    MarketDesk/earnings/Qwen placement is intentionally not changed in this carrier.
    The Chairman reports heavy PC lag while WSL/local inference is active; live process
    and resource evidence must decide whether existing model-router/external compute
    should replace resident Qwen before deciding pc-ci-4.
next_actions:
  - >
    Re-enter the Windows owner session once with a persistent `wsl` shell and leave it
    open; use that residency window to re-census pc-ci-1/2/3, systemd, Tailscale and
    the remote command agent before installing the corrected recovery task.
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
prs: [7188]
---

# Status

Source recovery is **BUILT_NOT_PROVEN**. The real Windows host still needs one
owner-context re-entry because the update reboot also removed every authenticated
noninteractive control path into Windows. No host mutation, runner registration,
label change, slot-4 activation, MarketDesk change, model change or production proof
has been claimed in this carrier.


## 2026-09-15 correction — WSL residency is the missing layer

The first source revision used a one-shot `/bin/true` launch. Live evidence proved that
shape false: it temporarily restored all three trusted CI listeners and the render
listener, but WSL later terminated and stranded them again. Microsoft Learn independently
documents that systemd services do not keep a WSL instance alive. PR #7188 now holds one
inert foreground keepalive from Task Scheduler, adds an AtLogOn fallback to AtStartup,
uses IgnoreNew to keep exactly one resident task, and removes the five-minute execution
limit. This remains **BUILT_NOT_PROVEN** until the real Windows task is installed and a
controlled reboot proves unattended recovery.

The same archaeology also found that MarketDesk extraction is deterministic and merely
emits a manifest for downstream LLM work. The resident Qwen dependency is the earnings
qualitative producer. A Mac fallback appliance already exists and can route directly to
DeepSeek when no local endpoint is configured, but its current launch environment exits
1 because the required R2 variable names and DEEPSEEK_API_KEY are absent. Therefore Qwen
must not be removed until an external-compute producer is made live and proves R2
publication plus output-quality/parity.

## 2026-09-19 incident confirmation — finite retry budget is unsafe

The production discriminator is now exact. Windows itself did not reboot at the outage boundary:
LastBootUpTime remained 2026-09-16, while the installed S4U recovery task kept WSL resident for
roughly 39 hours and then observed the foreground keepalive exit at 2026-09-18T23:40Z. The wrapper
retried through attempt 12, repeatedly received failed WSL launches, logged its terminal
failed-attempts=12 edge, and exited. WSL stayed down until the Chairman manually started the
distribution on 2026-09-19.

This falsifies the bounded-retry assumption without changing ownership: Task Scheduler still owns
only WSL residency, Linux systemd still owns runner lifecycle, and GitHub still owns scheduling.
The same carrier therefore removes the finite attempt budget, retries indefinitely with bounded
backoff, makes status logging fail-soft, revalidates WSL/distro visibility on every attempt, and
raises Task Scheduler's process-crash restart budget as defense in depth. Production acceptance
still requires installation of the exact merged bytes plus a real failure/restart or controlled
reboot witness; source tests alone do not prove self-healing live.
