---
key: CLAUDE-RESUME-APPENDS-IN-PLACE-AND-RECORDS-PROMPT-AS-STRING
claim: >
  `claude -p --resume <uuid>` locates the transcript store-wide and appends to that
  same `projects/<dir>/<uuid>.jsonl` whatever cwd it is launched from (no sibling
  file, no second project directory), and it records the `-p` prompt as a
  `type:"user"` record whose `message.content` is the prompt string itself, while
  tool results are `type:"user"` records carrying `toolUseResult` with list content
  and CLI-inserted notes carry `isMeta:true`.
falsifier: >
  Launch `claude -p --resume <uuid>` from a cwd different from the session's recorded
  cwd and find a new `<uuid>.jsonl` in a different project directory, or find the
  prompt recorded with list content / without the exact prompt string; or find a
  tool-result user record lacking `toolUseResult`.
so_what: >
  A transport can resolve a dead receiver by globbing `projects/*/<uuid>.jsonl`
  (refusing on >1) and can recognise its own submission structurally (user record,
  string content equal to the exact prompt) rather than by substring, which is what
  makes a read-only DELIVERED reconciliation sound: a nudge id quoted inside a tool
  result or a human prompt never counts. `--max-turns` is a hidden but real option
  on 2.1.275 (help string in the binary; accepted with exit 0). Once Opus safeguards
  refuse a session, later plain turns in that session are refused too — qualify on a
  fresh disposable, never retry inside the transport.
kind: constraint
verified_at: 2026-09-29
verified_by: >
  Session 7712b0f4: disposable 9cf78471 resumed from `scratchpad/q991` (recorded cwd
  `scratchpad/q991/receiver-cwd`) — holder count 1→1, same file 54235→62492 bytes,
  new records carry the launch cwd; disposable b2c425ab run 5: prompt record
  `message.content` str of 524 chars == the dispatcher's prompt (keys promptId,
  promptSource, permissionMode), tool_result record keys include toolUseResult.
  Evidence: Mastermind #991 comment 5895135409.
scope:
  - mastermind
  - integrations/executive_wake/claude_code.py
  - WS:EXECUTIVE-CAPACITY-FABRIC
confidence: verified
---

Project-directory names are lossy (long cwds are truncated with a hash suffix), so the
directory is never recomputed from a cwd; the uuid glob is the only inclusion path.
