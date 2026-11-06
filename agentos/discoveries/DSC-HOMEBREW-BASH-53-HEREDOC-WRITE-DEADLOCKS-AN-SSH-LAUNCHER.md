---
key: HOMEBREW-BASH-53-HEREDOC-WRITE-DEADLOCKS-AN-SSH-LAUNCHER
claim: >
  Under Homebrew GNU bash 5.3.9 on macOS (arm64), a launcher that feeds a remote script to
  `ssh <host> bash -s -- <args> <<'REMOTE' … REMOTE` hangs indefinitely when it is invoked as
  `bash ./g2lane.sh …` from a Claude Code Bash-tool shell: the forked child sits in
  `do_redirections -> heredoc_write -> write(2)`, ssh is never exec'd, nothing is printed, and
  no remote process starts (seat-measured 2026-10-12 04:33Z, 12+ min with no progress on a
  ~1.6 KB quoted here-document). The identical, unchanged script invoked as
  `/bin/bash ./g2lane.sh … </dev/null` (Apple bash 3.2.57, stdin detached) completed every
  launch in seconds — 20 consecutive `LAUNCHED` lines across four hosts the same night. The
  two changes (interpreter and stdin) were applied together and were NOT isolated from each
  other; the mechanism (bash 5.x pipe-backed here-documents vs. the tool shell's inherited
  stdin) is probable, not proven.
falsifier: >
  From a Claude Code Bash-tool shell, run the unchanged launcher as
  `/opt/homebrew/bin/bash ./g2lane.sh <alias> <label> <prompt>` with no stdin redirect and see
  it print `LAUNCHED …` within the ssh ConnectTimeout; or `sample <child-pid> 2` on a hung
  invocation showing the child anywhere other than `heredoc_write`. Either disproves the claim
  as stated. Isolating the fix — `/opt/homebrew/bin/bash … </dev/null` succeeding, or
  `/bin/bash …` without the redirect hanging — refines it rather than disproving it.
so_what: >
  Any ssh-fed here-document launcher run from a tool shell (Claude Code Bash, Codex exec,
  cron-less sentinels) pins `/bin/bash` explicitly and detaches stdin with `</dev/null`; never
  write `bash <script>` where PATH resolves Homebrew bash first, and never rely on a
  `#!/bin/bash` shebang that a `bash ./script` invocation bypasses. When a launcher prints
  nothing and no remote pid appears, check the LOCAL child with `ps -o stat,command` /
  `sample` for `heredoc_write` BEFORE blaming the remote host, GitHub, or ssh — the 04:33Z
  hang was first misread as a remote fetch stall. A future session that needs to know which
  half is load-bearing isolates the two changes first instead of generalising this record.
kind: landmine
scope: [macro, mastermind, "fleet ssh launchers (g2lane.sh and descendants)", "Claude Code Bash-tool shells on macOS"]
confidence: verified
verified_at: 2026-10-12
verified_by: >
  Crypto-intelligence Fable seat 2a56019d, 2026-10-12: `bash ./g2lane.sh mmx-ubuntu0
  cx-t01-20261012 prompts/cx-t01-20261012.md …` hung from ~04:21Z to 04:33Z with the child in
  `heredoc_write` (local `sample`); relaunched as `/bin/bash $S/g2/g2lane.sh … </dev/null`
  the same script printed `LAUNCHED label=cx-t01-20261012 host=ubuntu0-MS-A2 pid=3509103 …`
  and 19 further LAUNCHED lines (ubuntu0/ubuntu1/ubuntu2/ubuntu3) by 05:00:45Z. Versions:
  `/bin/bash --version` = 3.2.57(1)-release arm64-apple-darwin25;
  `/opt/homebrew/bin/bash --version` = 5.3.9(1)-release aarch64-apple-darwin24.6.0.
  Launch logs are reproduced in agentos/handoffs/CRYPTO-INTELLIGENCE-2026-10-12-grok-fanout.md.
affects:
  - WS:CRYPTO-INTELLIGENCE
---

## Why this is a landmine and not a log line

The failure is silent in every direction a session normally looks. The launcher prints
nothing (the `LAUNCHED` echo is after the heredoc), the remote host shows no new process,
`ssh` itself never ran so there is no connection to inspect, and the Bash tool simply does
not return. Every one of those symptoms also matches "the remote host cannot reach GitHub",
which is exactly what the seat spent twelve minutes diagnosing on 2026-10-12 before sampling
the local child. The fix is one line of invocation discipline and costs nothing; the miss
costs a whole fan-out window.

## What was and was not established

- Established: the hang reproduces under Homebrew bash 5.3.9 invoked as `bash ./g2lane.sh`
  from a Claude Code Bash-tool shell; the same bytes run clean under
  `/bin/bash … </dev/null`, 20 for 20.
- Not established: whether Apple bash 3.2 alone (no redirect) or the redirect alone (Homebrew
  bash) is sufficient. bash 5.x backs small here-documents with a pipe instead of a temp file,
  and the Bash tool's inherited stdin is itself a pipe, so an fd/pipe interaction is the
  leading hypothesis — treat it as a hypothesis.
- Not in scope: the earlier `ssh` stdin-consumption bug in the same kit (`while read` loop
  over a TSV where an un-`-n` ssh ate the remaining lines). That one is ordinary and is fixed
  with `ssh -n`; it is mentioned only because both bugs present as "the loop launched one
  lane and stopped".
