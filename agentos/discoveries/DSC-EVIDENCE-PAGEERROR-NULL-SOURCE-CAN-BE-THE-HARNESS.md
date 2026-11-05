---
key: EVIDENCE-PAGEERROR-NULL-SOURCE-CAN-BE-THE-HARNESS
claim: >
  A page-level console_errors entry in a mastermind.p0_evidence.v2 manifest whose
  text starts with "pageerror:" and whose source_url is null is not evidence that
  the PAGE threw: Playwright's pageerror carries no location, so scripts/
  capture_page_evidence.py records every uncaught exception that way, including
  exceptions thrown by init-script text the harness itself injected. The
  sanctions_map entry "(intermediate value)(...) is not a function" was the
  tool's unterminated state-seed IIFE concatenated with a capture wrapper's
  appended IIFE (automatic-semicolon-insertion call-of-a-call), not theme.js,
  nav_market.js, or the page's inline scripts.
falsifier: >
  Rerun the stock tool (python3 scripts/capture_page_evidence.py --site-dir site
  --routes /<page>.html) against byte-identical served files with a
  stack-capturing pageerror listener and observe the same error with a stack
  frame inside a served script URL; or reproduce the harness's exact
  add_init_script concatenation and observe NO error.
so_what: >
  Before classifying such an entry as shared-chrome debt, recover the capture
  harness (Cursor sessions keep transcripts under ~/.cursor/projects/<cwd-slug>/
  agent-transcripts/, not ~/.claude/projects) and reproduce its init-script
  composition with a stack-capturing listener; hash every requested file across
  the capture worktree and a fresh one; compare the manifest's structural page
  metrics with a fresh stock run. state_seed_source() now emits a terminated
  statement so concatenation is safe; a wrapper that appends its own IIFE must
  still not assume any upstream init-script text ends in a semicolon.
kind: constraint
verified_at: 2026-09-08
verified_by: >
  This session: stock tool rerun 3x8 states on this worktree's site/ (0
  pageerrors, 0 external requests); 14/14 requested files hash-identical to
  macro-main/.claude/worktrees/mo-release-6826/site; country_cycles.html under
  the same chrome 0/16; exact concatenation of the pre-fix seed and the wrapper
  IIFE from the Cursor transcript reproduced "TypeError: (intermediate
  value)(...) is not a function at <anonymous>:10:13"; the terminating semicolon
  removed it. Pinned by tests/test_capture_page_evidence.py::
  test_state_seed_source_is_a_terminated_statement_safe_to_concatenate.
scope:
  - macro
  - scripts/capture_page_evidence.py
  - scripts/check_ui_visual_evidence.py
  - mockups/evidence/sanctions_map/manifest.json
  - templates/theme.js
confidence: verified
---

The tool cannot tell a harness exception from a page exception, and it should
not pretend to: a null source_url means "no location", never "the page".
