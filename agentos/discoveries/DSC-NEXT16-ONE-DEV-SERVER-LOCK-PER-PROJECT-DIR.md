---
key: NEXT16-ONE-DEV-SERVER-LOCK-PER-PROJECT-DIR
claim: >
  Next 16 holds one `next dev` lock per project directory, so a second dev server
  started from the same Terminal checkout exits at once with "Another next dev server
  is already running" whatever `--port` it was given, and a crop-capture tool waiting
  on that port reads the exit as `never answered (ECONNREFUSED)`.
falsifier: >
  From one `terminal/` checkout start `npm run dev -- --port 3563`, then
  `npm run dev -- --port 3566`; if the second server stays up and answers on 3566, the
  lock is not per project directory.
so_what: >
  In one worktree, run crop-capture tools (`e2e/tools/capture_*.cjs`, the axis
  `capture.mjs` recipe) and Playwright suites strictly one after another, and read a
  capture tool's ECONNREFUSED as a lock collision until the server log's first lines
  are checked. Parallelise only across worktrees, each with its own `.next/dev` lock.
kind: landmine
verified_at: 2026-10-21
verified_by: >
  Terminal worktree on `claude/options-r1-w3-term-1021`:
  `capture_eod_heatmap_flowdesk_load_failure.cjs` (port 3566) failed with
  `dev server on 3566 never answered (ECONNREFUSED)` after 180 s while
  `capture_vol_load_failure.cjs` (port 3563) was running; its log began
  `⨯ Another next dev server is already running. - Local: http://localhost:3563 - PID …`.
  The same tool succeeded run alone (126 crops).
scope:
  - terminal
  - terminal/e2e/tools/*.cjs
  - terminal/docs/pr-crops/options-level-axis-labels/capture.mjs
  - terminal/playwright.config.ts
  - WS:OPTIONS-R1
confidence: verified
---

The per-run `TERMINAL_E2E_PORT` rule avoids port reuse between back-to-back Playwright
runs; it does not make concurrent runs from one checkout possible. Pin the sequence, not
the port.
