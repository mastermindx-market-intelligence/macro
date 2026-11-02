---
key: THE-SWEEPERS-FOUR-DAY-NON-START-WAS-AN-UNLOADED-AGENT-NOT-A-CRASH
claim: >
  The worktree-GC launchd job's 4-day non-start window is 2026-09-18 through 2026-09-21 inclusive,
  and its cause is that the LaunchAgent was NOT LOADED during it — not a crash, not a slow sweep,
  and not a powered-off host. Measured 2026-09-29: `launchctl print gui/<uid>/com.macro.worktree-gc`
  reports `runs = 7`, and the run log contains exactly 7 starts (2026-09-22 … 2026-09-28). launchd
  resets that counter when a service is re-bootstrapped, so the agent was re-loaded on 09-22; had
  it been loaded continuously since its first run on 2026-08-13 the counter would read ~45. The
  host was NOT rebooted — `last reboot` shows continuous uptime since 2026-08-29 10:58 — so a
  power cycle is excluded. This is a SECOND, independent availability failure mode alongside the
  13 timeout crashes, and `DSC:A-RAISED-TIMEOUT-MAKES-THE-DEGRADATION-PATH-WRITTEN-FOR-IT-DEAD-CODE`
  / PR #8176 does not address it: a receipt written by the wrapper cannot record a run that launchd
  never started.
falsifier: >
  `launchctl print gui/$(id -u)/com.macro.worktree-gc | grep runs` against
  `grep -c '^== worktree-gc 2026-' ~/Library/Logs/macro_worktree_gc/launchd.out.log` bucketed by
  date. If `runs` ever materially exceeds the count of starts since the last suspected reload, the
  agent was not re-bootstrapped and this is false. Run starts are the `== worktree-gc <ISO> ==`
  markers; do NOT count `== worktree-gc done rc=N ==`, which are COMPLETION markers (29 rc=0 +
  1 rc=2 on 2026-09-29) and would inflate a naive grep by 30. Do NOT use
  `~/Library/Logs/macro_worktree_gc/ledger.jsonl` to answer this: it records one row per DELETED
  worktree, so a run that deleted nothing leaves no trace and its gaps cannot distinguish
  "did not run" from "ran and found nothing".
so_what: >
  The availability programme has TWO failure modes and W12/#8176 closed only one. Full census as
  of 2026-09-29: **45 starts, 30 completions, 15 that started and never completed** (13 of them
  uncaught `subprocess.TimeoutExpired` — 9 at `RUN_TIMEOUT_S=3000`, 4 at `GIT_TIMEOUT_S=120`),
  **plus 4 days with no start at all**. A wrapper-side receipt is structurally blind to the second
  mode, so detecting it needs an EXTERNAL check that compares expected daily runs against actual
  starts — the sweeper cannot witness its own absence. Note also that fixing either mode on this
  host requires re-running `scripts/install_worktree_gc_launchd.sh`, because the installed wrapper
  at `~/Library/Application Support/macro-worktree-gc/worktree_gc_launchd.py` is **4,611 bytes
  dated 2026-08-12** against **10,957 bytes** on `origin/main` — a merge reaches the repo and never
  the host.
kind: runtime
verified_at: 2026-09-29
verified_by: >
  `launchctl print gui/<uid>/com.macro.worktree-gc` (`runs = 7`, `last exit code = 1`,
  `job state = exited`); `~/Library/Logs/macro_worktree_gc/launchd.out.log` run-start markers
  bucketed by date (daily and unbroken 2026-08-13 → 2026-09-17, absent 09-18 → 09-21, daily again
  09-22 → 09-28); `grep -c '^subprocess.TimeoutExpired:' launchd.err.log` = 13, of which 9 name
  2999s and 4 name 120s; `last reboot` (no reboot since 2026-08-29 10:58);
  `~/Library/LaunchAgents/com.macro.worktree-gc.plist` (`StartCalendarInterval` 05:17 local,
  `RunAtLoad` false, plist mtime 2026-08-12 — so 09-22 was a re-load, not a re-install).
scope:
  - macro
  - scripts/worktree_gc_launchd.py
  - scripts/install_worktree_gc_launchd.sh
  - research/WORKTREE_GC_POLICY.md
confidence: verified
---

## Two failure modes, one of them invisible to the fix

| mode | runs affected | what it looks like | addressed by #8176 |
|---|---:|---|---|
| Sweep or git call exceeds its timeout | 13 | traceback in `launchd.err.log`, no completion marker | **yes** — rc=124 + receipt |
| Agent not loaded at all | 4 days | *nothing anywhere* | **no** |

The second row is the dangerous one precisely because it is quiet. Every instrument this programme
owns is written BY the wrapper, and the wrapper did not run. The deletion ledger shows a gap, the
run log shows a gap, the receipt file would show a gap — and a gap is exactly what a healthy
"nothing to collect" night also produces. Only an external expectation ("there should be a start
every day at 05:17") can tell those apart.

## Why the counter is trustworthy here

`runs` is maintained by launchd per bootstrapped service instance and resets on re-bootstrap. It
reads **7** against **7** logged starts since 09-22 — an exact match — while the service has 45
logged starts in its lifetime. The plist's own mtime is 2026-08-12, so nothing re-INSTALLED it on
09-22; it was re-LOADED. The host never rebooted in the window, so this was not a boot-time
reload either.

Related: `DSC:A-RAISED-TIMEOUT-MAKES-THE-DEGRADATION-PATH-WRITTEN-FOR-IT-DEAD-CODE` (mode 1, and
why the timeout was deliberately not raised).
