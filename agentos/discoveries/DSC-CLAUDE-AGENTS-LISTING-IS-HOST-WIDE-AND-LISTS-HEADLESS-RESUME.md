---
key: CLAUDE-AGENTS-LISTING-IS-HOST-WIDE-AND-LISTS-HEADLESS-RESUME
claim: >
  On Claude Code 2.1.275, `claude agents --json` returns the same host-wide row set
  regardless of the cwd it is run from, and a headless `claude -p --resume <uuid>`
  process appears in that listing for its whole lifetime, so a listing-based writer
  exclusion covers both interactive and headless writers of a session transcript.
falsifier: >
  Run `claude agents --json` from two unrelated cwds while a known interactive
  session is live and find the row missing from one of them; or start a headless
  `-p --resume` for a known uuid and poll the listing at ~1 s until it exits without
  ever seeing a row for that uuid.
so_what: >
  A Wake transport may use the listing as a fail-closed exclusion check (any row for
  the exact handle refuses delivery) and need not add a lock or registry for the
  headless case; the only unguarded interval is the discovery-to-launch latency.
  Dead sessions are absent from the listing, so the listing is exclusion evidence
  only and never resolves the receiver — inclusion must come from the transcript store.
kind: constraint
verified_at: 2026-09-29
verified_by: >
  Session 7712b0f4: identical 39-row listings (26 distinct session cwds) from three cwds
  (scratchpad, an SSD worktree, $HOME); a 7.6 s headless `-p --resume` of disposable
  9cf78471 polled at ~1 s showed rows 39→40→39 with the uuid listed in 4 consecutive
  samples. Evidence: Mastermind #991 comment 5895135409 (evidence_f3_listing_scope.json,
  evidence_f3_g3_crosscwd_probe.json on the shared host).
scope:
  - mastermind
  - integrations/executive_wake/claude_code.py
  - control_plane/wake_transport.py
  - WS:EXECUTIVE-CAPACITY-FABRIC
confidence: verified
---

Rows carry `pid, cwd, kind:"interactive", startedAt, sessionId, name, status`; there is
no `state` key and a headless writer is not distinguished by `kind`. Refuse on any row.
