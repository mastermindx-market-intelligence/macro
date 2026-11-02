---
key: US-PROPHET-TRACKED-PANEL-CACHE-OVERWRITE-20260916
claim: >
  The Sep-15 recurrence was not confined to daily.engine. Twenty-six read-only
  cache steps across seven workflows could overwrite the three Git-tracked US
  breadth panels; twenty-three carried prefix fallbacks. The old guard inspected
  combined cache actions and data-staging jobs, so restore-only consumers that
  published stale derived boards escaped. The candidate removes those reader
  overlays and dates the visible candidate count from us_standouts.as_of.
falsifier: >
  Parse every workflow cache/restore step and find any remaining non-collector
  restore of the three tracked panels; demonstrate a changed non-cache step,
  missing Russell handoff, changed ranking/permission logic, a source date
  replaced by render time, or a passing injected exact-key reader mutant.
so_what: >
  The actual committed panels can reach alpha and Prophet without a stale-cache
  overlay. A frozen page discloses its screen date rather than claiming tonight.
  This is BUILT_NOT_PROVEN until hosted gates, integration and real current-session
  producer-to-served-board proof succeed. No fresh candidate is fabricated.
kind: runtime
verified_at: 2026-09-16
verified_by: >
  python -m pytest tests/test_daily_collect_commit_path.py -q; gh pr view 7187
  --repo mastermindx-market-intelligence/macro --json headRefOid,state,isDraft
scope:
  - WS:PROPHET-US-AVAILABILITY
  - .github/workflows
  - templates/dashboard.html.j2
confidence: verified
related:
  - WS:PROPHET-US-AVAILABILITY
---

Implementation base: `f981ec2543def670758ff873e47257d5b90ae732`. Original implementation pin: Mastermind `7642aea155d2817219135b24246b55c1d7611c66`. Current recurrence-repair pin: protected Mastermind `master` `8ba7deedde164c90298d3e88785d98e02fa5e2d2`; the required Skillpack/source-law blobs are byte-identical to the previously loaded `0fe8074ff953b2ced9025ed40f0f66019c759967` revision. Carrier branch: `sol/prophet-us-panel-authority-20260916`.

At earlier main `9579caf3f950f1a2e7b959a9b3b68d26e42e5d06`, the committed breadth/smallcap/midcap panels were all through Sep-14 (375x512, 775x635, 775x413) while the cache-busted production page still exposed board Sep-11 and “52 screened tonight”. The board copies alpha.json’s source date; healing SPY alone does not freshen those panels.

Local proof: **76 tests passed in 31.86s** across the existing commit-path, workflow-size, candidate-board and chat-navigation owners. The three recurrence regressions—multiline action paths, `.yaml` workflows and duplicate producer seeds—were observed red before the minimal repair and pass on the composed candidate. The reader-step removals preserve schedules, credentials, collectors and conditions; the collector’s three seed caches and the distinct gitignored Russell handoff remain intact.

Eight current-template browser cases passed (old/missing source date x EN/ZH x mobile/desktop), including JavaScript-disabled operation and no heading overflow. Missing/null/empty dates remain unavailable. All dates are projections of the original source, not fabricated publication dates. Evidence: `docs/pr-crops/us-prophet-source-date-20260916/receipt.json`. This is browser-fixture proof only.
