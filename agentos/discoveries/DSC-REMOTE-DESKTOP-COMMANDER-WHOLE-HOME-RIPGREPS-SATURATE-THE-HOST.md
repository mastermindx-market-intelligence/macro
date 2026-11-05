---
key: REMOTE-DESKTOP-COMMANDER-WHOLE-HOME-RIPGREPS-SATURATE-THE-HOST
claim: >
  On the build Mac Studio, a remote Desktop Commander MCP session
  (`npm exec @wonderwhy-er/desktop-commander@latest remote`, pid chain npm exec ->
  desktop-commander remote -> node dist/index.js) issued whole-home searches
  `rg --json --line-number -C 5 -i --hidden -m 100 -- <phrase> /Users/chriswong`
  (hidden dirs included, so the 85 GB shared clone, every worktree, node_modules and
  iCloud); 47 ran concurrently for up to 2h13m, the host sat at load 145-171 from
  ~13:00Z to 14:14Z on 2026-09-07, `gh pr view` hung 13+ min, `ls`/`os.scandir` on the
  shared pack dir returned EINTR, every session's tool call took ~10 min, and a
  Terminal deploy chain stalled for an hour; SIGTERM to the 46 rg children alone
  (server and remote session untouched) dropped load to 16 within 12 minutes with no
  respawn.
falsifier: >
  If load stays above ~100 after every rg child of the desktop-commander server is
  gone, or if the top CPU consumers by `ps -eo pcpu,pid,etime,comm | sort -rn` are not
  rg processes, the cause is elsewhere (pack storm, runaway node, ENOSPC) and this
  record does not apply.
so_what: >
  When tool calls crawl, sample `ps` by CPU BEFORE blaming git, the pack count or the
  fleet; if the top consumers are `rg` under one node parent, kill the rg children
  only (`ps -eo pid,ppid,comm | awk '$2==<parent> && $3 ~ /\/rg$/ {print $1}' | xargs
  kill -TERM`; zsh needs xargs) and record it. Repeated respawns mean the remote
  client's search scope is the defect and it is a Chairman decision, not a session's.
  Related: DSC:SHARED-CLONE-PACK-STORM-STALLS-THE-FLEET (a different cause with the
  same symptom).
kind: landmine
verified_at: 2026-09-07
verified_by: >
  Meta-CEO B session 7cd4fae1, receipts in the session notes 13:05Z-14:26Z
  (scratchpad/terminal_reviews/META_CEO_B_NOTES.md: ps output, kill, uptime 171 -> 16).
scope:
  - macro
  - mastermind
  - WS:MARKET-OS
confidence: verified
related:
  - "DSC:SHARED-CLONE-PACK-STORM-STALLS-THE-FLEET"
  - "WS:MARKET-OS"
---

A remote Desktop Commander session can saturate the build host with whole-home
`rg --hidden` searches. When tools crawl, sample CPU before blaming git; kill only
the rg children. Recurring respawns are a Chairman decision about the remote
client's search scope, not a session fix.
