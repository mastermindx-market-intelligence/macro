---
key: A-SCRATCHPADS-KEYED-CHECKOUT-CAN-BE-GONE-WHILE-ITS-SESSION-IS-LIVE
claim: >
  The session scratchpad root `/private/tmp/claude-501` holds **160.43 GiB across 473 keys** on the
  INTERNAL volume — the tighter one, which has hit ENOSPC twice — and every key is named after the
  checkout its sessions started in. **That name is an INVERTED liveness signal.** The largest key
  is **81.24 GiB** and names
  `…/Macro Dashboard/.claude/worktrees/finance-intelligence-e2e`, a directory that **no longer
  exists**, while the single session inside it (`938d17d6`, the active FINANCE INTELLIGENCE seat)
  had written its transcript **4 minutes before measurement** — because a session keeps its
  original key for its whole life, so a vanished checkout says nothing about whether anyone is
  there. Classified instead by the signal that does answer the question — the session transcript
  mtime at `~/.claude/projects/<the same key>/<uuid>.jsonl`, the STRONG signal
  `research/WORKTREE_GC_POLICY.md` §9 already endorses, and a join that needs no path decoding —
  the pool is **64.8% LIVE <2h (103.91 GiB over just 6 keys)**, 0.1% RECENT <24h, 13.8% IDLE 1–7d
  (22.21 GiB), and the provably dead bucket (**COLD ≥7d, 48 keys**) holds **0.02 GiB**. A further
  17.7% (28.39 GiB, 61 keys) has no transcript and is **UNDECIDABLE, never dead**; 3.6% (5.73 GiB,
  291 keys) does not join to a project key at all and is mostly the shared `bash-edit-diff` tool
  cache (5.15 GiB). **So an age-gated sweep of this pool frees 0.02 GiB, and any widening that
  frees real space walks into a live seat.** The 81.24 GiB itself is **nine git-less 8.63 GiB full
  repo trees** (`main5_bytes`, `main6_bytes`, `rv_m3`/`rv_m5`/`rv_m8`/`rv_m12`, `pe_tree`,
  `ct_tree`, `rv_red` = 77.7 GiB) — the never-measured storage cost of the "prove it in main's
  bytes" verification practice. With no `.git` they have no HEAD, so
  `DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM` structurally cannot reach them, the same blind spot
  as the 318 detached trees.
falsifier: >
  `du -sxk /private/tmp/claude-501/*` totals 160.43 GiB over 473 children, top four 144.17 GiB
  (89.9%). `test -d "/Users/chriswong/Documents/Cluade/Macro Dashboard/.claude/worktrees/`
  `finance-intelligence-e2e"` is FALSE while
  `stat -f '%Sm' ~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard--claude-`
  `worktrees-finance-intelligence-e2e-7c27cd/938d17d6-a768-4217-a28a-321c0cb62da0.jsonl` returns
  2026-09-28 18:53 on a 108.7 MB transcript — the two probes disagree, and the positional one is
  the wrong one. `ls -a <tree>/.git` on any of the nine 8.63 GiB trees returns
  "No such file or directory". Disproved if the project-key join stops resolving (it resolved 4/4
  on the four largest keys), if scratchpad keys ever start following a session's moves, or if a
  future Claude Code release prunes scratchpads on session end — after which the classification
  must be re-measured, not assumed.
so_what: >
  **Never classify a session scratchpad by whether the checkout its key names still exists.** That
  probe is not merely weak, it is inverted, and here it would have authorized deleting 81.24 GiB
  belonging to a seat that was writing at the time — the 2026-09-26 incident class
  (`DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM`) reproduced against scratchpads instead of
  worktrees, and worse, because a scratchpad has no lock, no registry entry and no `git status` to
  refuse on. Join on the transcript instead; report the UNDECIDABLE bucket as undecidable. Second:
  **this is the ninth pool measured in this triage and the eighth null** — 160.43 GiB with
  0.02 GiB provably reclaimable — so do not propose scratchpad expiry as a disk-space lever; it is
  a correctness lever at best. Third: the 77.7 GiB of git-less verification trees is a real and
  growing cost of a practice this repo's own laws encourage ("verify in main's bytes"), and the
  cheap fix is a session convention — one reusable comparison tree, removed when the claim is
  filed — not a sweeper, since no reclaim gate can see a tree with no HEAD. Fourth: seventh
  instance of the positional-vs-semantic instrument failure this triage has hit
  (`df /`, HUMAN-class screen, `is_git`, landedness, pool census, absence search, and now
  scratchpad liveness); every one returned a clean plausible number with no error, so **state
  which question your instrument actually asked** before acting on its answer.
kind: landmine
verified_at: 2026-09-28
verified_by: >
  `du -sxk /private/tmp/claude-501/*` (473 children, 160.43 GiB; receipt
  scratchpad/claude501_raw.txt) and per-child classification by transcript mtime against
  `~/.claude/projects/<key>/<uuid>.jsonl` (scratchpad/classify_scratchpads.py, receipt
  scratchpad/scratchpad_classification.json — LIVE 6/103.91, RECENT 7/0.17, IDLE 60/22.21,
  COLD 48/0.02, NO TRANSCRIPT 61/28.39, NO PROJECT KEY 291/5.73 GiB); `du -sxk` two levels into
  the 81.24 GiB key (one session dir -> scratchpad/ -> nine 8.63 GiB trees); `ls -a` + `file` on
  `pe_tree/.git` (absent); `test -d` on the keyed checkout (absent); `stat` on the 108.7 MB
  transcript (2026-09-28 18:53); `du -sxk /private/tmp/*` (claude-501 = 160.43 of 276.2 GiB,
  next entry 0.68 GiB)
scope:
  - macro
  - research/WORKTREE_GC_POLICY.md
  - scripts/worktree_gc.py
  - config/worktree_gc.json
confidence: verified
---
