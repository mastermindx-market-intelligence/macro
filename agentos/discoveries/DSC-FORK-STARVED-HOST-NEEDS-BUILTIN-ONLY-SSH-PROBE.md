---
key: FORK-STARVED-HOST-NEEDS-BUILTIN-ONLY-SSH-PROBE
claim: >
  As of 2026-09-29, m1studio is process-starved to the point that ssh authenticates
  but essentially every ordinary remote command dies with
  `bash: fork: Resource temporarily unavailable`, and sshd sometimes cannot spawn a
  shell at all (`exec request failed on channel 0`). This reads exactly like an
  unreachable or broken host and was misdiagnosed as one for most of a session.
  It is not: a remote script written with ONLY bash builtins and glob expansion —
  no command substitution `$(...)`, no pipes, no subshells `(...)`, no external
  binaries — runs to completion there reliably. `echo`, `[[ ]]`, `for`, `while
  read`, `(( ))`, `kill -0`, `printf`, parameter expansion and pathname globbing
  are all fork-free and sufficient to read files, count lines, match substrings,
  measure byte length via `${#var}` under `LC_ALL=C`, test path existence and
  probe process liveness. A single trailing external command (e.g. `shasum -a 256`
  over several files at once) succeeds often enough to be worth placing LAST, after
  all fork-free output has already been emitted, so its failure costs nothing.
  Retry-with-backoff still matters because the fork budget fluctuates.
falsifier: >
  `ssh m1 'echo hi; ls'` completing normally, or a `$(...)`-using probe returning
  its output, would show the constraint has lifted. Conversely, a builtin-only
  probe that still dies on fork would show the host has degraded past this
  technique. Re-check with `ssh m1 'bash -s' < probe.sh` where probe.sh contains
  only builtins.
so_what: >
  A session that needs to observe a fork-starved source host must not conclude the
  host is unreachable and stop, and must not escalate to an operator, until it has
  tried a builtin-only probe. On 2026-09-29 this converted a lane that had been
  blocked all session into a completed read that produced the decisive finding of
  the task (macro #7861: the installed producer's dependency was absent, so a
  file-level install would have failed closed at import). Write the probe to a
  file locally and pipe it in via `ssh host 'bash -s' < probe.sh`; put any
  unavoidable external command last; retry 3-4 times with ~20s backoff.
kind: runtime
verified_at: 2026-09-29
verified_by: "ssh m1 'bash -s' < probe.sh, four successive probes; macro PR #7861 comment 5895153520"
scope:
  - macro
  - mastermind
  - ops/launchd/**
  - hosts/m1studio
confidence: verified
---

# Fork-starved hosts are observable with builtin-only probes

The failure mode is deceptive because the *connection* succeeds. You authenticate, you
get a shell banner, and then the first real command fails — so it looks like the host is
broken or the network is flaky, and the natural response is to give up on it and report
the lane blocked.

What is actually exhausted is the process table, not the link. Every fork the remote shell
attempts may fail, and command substitution is a fork, which is why the most innocuous-looking
probe line — `echo "x=$(hostname)"` — is usually the first thing to die. Strip every fork and
the same shell is perfectly capable of reading files, hashing nothing but measuring everything,
and answering most of the questions a session actually has.

Related: [[MIXED-VINTAGE-INSTALLED-CHECKOUTS-ON-M1]] — the finding this technique made
measurable.
