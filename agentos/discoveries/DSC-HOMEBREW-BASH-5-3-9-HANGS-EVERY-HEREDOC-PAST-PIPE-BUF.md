---
key: HOMEBREW-BASH-5-3-9-HANGS-EVERY-HEREDOC-PAST-PIPE-BUF
claim: >
  On the m2 seat host, Homebrew bash 5.3.9 (/opt/homebrew/bin/bash, the PATH
  `bash`) hangs forever in heredoc_write -> write() on any here-document whose
  body is 512 bytes or longer, so every kit lane launched as `bash
  ext/sub.sh ...` wedges silently before admission (no slot, no lease, no ledger
  row), while the same script under /bin/bash 3.2.57 (its own shebang) runs.
falsifier: >
  Run `/opt/homebrew/bin/bash -c "python3 - <<'X'\nprint('ok')\n<650 bytes of
  comment lines>\nX"` with an 8 s timeout on m2 and see it print ok; or run the
  identical command under /bin/bash and see it hang. Either result refutes the
  claim (measured 2026-10-02: 5.3.9 hangs >8 s, 3.2.57 prints ok in 0.04 s;
  bodies <=492 B pass under both, >=572 B hang under 5.3.9).
so_what: >
  Never spell a kit lane `bash $K/ext/sub.sh ...` or run large heredocs under
  PATH bash on m2: invoke the script directly (its shebang is /bin/bash) or as
  `/bin/bash $K/ext/sub.sh ...`. A lane whose log stops after the launch line
  with no ECONOMIC_POLICY / FLOCK_ACQUIRED / LEASE_ACQUIRED line is this, not a
  slow worker: confirm with `sample <pid> 1` (stack execute_disk_command ->
  do_redirections -> heredoc_write -> write), `pgrep -P <pid>` empty, `lsof -p`
  showing fds 3/4 PIPE held only by the writer. Audit the 3 of 43 kit scripts
  that carry `#!/usr/bin/env bash` (they resolve to Homebrew bash) for heredocs
  >=512 B. Upgrading or pinning bash fleet-wide is an OPERATOR / B-kit act, not
  a seat edit; report it, do not take it.
kind: landmine
verified_at: 2026-10-02
verified_by: >
  Standalone repro 2026-10-02 ~10:05Z on m2 (python subprocess, timeout 8 s):
  652 B heredoc body under /opt/homebrew/bin/bash 5.3.9(1)-release HUNG; under
  /bin/bash 3.2.57(1)-release rc=0 'ok' in 0.04 s; `command -v bash` ->
  /opt/homebrew/bin/bash. Earlier the same session: lanes r1 and r2 of the
  Mastermind headless-control item-3 build (sub.sh grok) sampled with
  `sample <pid> 1` showing heredoc_write -> write on the 1,465 B host-policy
  heredoc at sub.sh:152; r3 under /bin/bash admitted and delivered. Receipts:
  Mastermind research/MASTERMIND_HEADLESS_CONTROL_CONTINUATION_HANDOFF_2026_10_02.md
  (09:45Z checkpoint, PR #1148/#1149).
scope:
  - macro
  - mastermind
  - host m2 (seat)
  - ~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08/ext/sub.sh
  - .claude/hooks (any hook or wrapper that shells out through PATH bash with a long heredoc)
confidence: verified
---

The defect is in the shell, not the kit: sub.sh's own shebang is `/bin/bash`, so
`./sub.sh` and `/bin/bash sub.sh` are unaffected, and only callers that spell
`bash sub.sh` (the recipe account-local memory carried until 2026-10-02) or
scripts resolving `#!/usr/bin/env bash` through PATH hit it. The 512-byte
boundary is PIPE_BUF: the heredoc writer blocks on a pipe write that nothing
drains, with no child ever spawned. A kill-and-relaunch under the same `bash`
reproduces it deterministically, so two "wedged lanes" in a row are the shared
assumption, not a host transient.
