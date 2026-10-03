---
key: BASKET-LATE-LOAD-FOCUS-20260921
claim: >
  At macro main 0d9d836cda058f3f59507e3b7b7fed92b05ef7dc, sorting before
  window.load can lose focus when shared wrapTables reparents the focused
  holdings table. The row order is unchanged; a subsequent language check
  exposes the already-lost focus but is not the cause.
falsifier: >
  Hold one non-data image request, sort with native Tab and Enter, then release
  the image to fire genuine window.load. If the original source keeps the same
  connected focused button without reparenting the TABLE, this claim is false.
so_what: >
  Render the existing canonical tbl-scroll class on the existing .ts holdings
  wrapper so the shared initializer is idempotent. Do not add focus-stealing
  timers, a second wrapper owner, a shared-theme fork, or an authentication bypass.
kind: landmine
verified_at: 2026-09-21
verified_by: 'research/evidence/uiux-basket-load-focus-20260921/before.json and verify_late_load.py'
scope:
  - 'mastermindx-market-intelligence/macro'
  - 'templates/basket_detail.html.j2'
  - 'site/basket*/**'
  - 'tests/test_ftr_w3_ui.py'
confidence: verified
---

The repair is one existing class token across the template and all 121 generated
pages, verified in 16 delayed-load browser cases and the 20-case existing sorting
verifier. This record is implementation proof, not a deployment claim. Follow-up
carrier: claude/uiux-basket-load-focus-20260921; predecessor #7497 is merged and
must not be reused as a source branch. Current release gates are in the evidence
README. Public Market Structure #7437 and Intelligence Hub #7361 releases are
accepted separately and remain DO_NOT_REDO.
