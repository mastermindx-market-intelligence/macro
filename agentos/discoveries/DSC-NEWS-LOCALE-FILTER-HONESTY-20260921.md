---
key: NEWS-LOCALE-FILTER-HONESTY-20260921
claim: >
  At macro 597bedad6cf1240150a5804522b1b75fe3baa2f3, the News page reports
  45 shown for 24 visible headlines, and its five window-scoped language listeners
  miss the shared document-scoped event. Native language changes leave search,
  timestamps, counts and guest feed states in the old language. Flex/grid display
  rules additionally expose child controls marked hidden in guest states.
falsifier: >
  Use the native Settings language switch on that revision and compare visible
  feed count, search placeholder, accessible names, relative ages and guest states.
  The recorded before.json and screenshot would be disproven if all change with
  the selected language and the count equals the visible rows. Inspect hidden
  Intelligence metrics with computed visibility rather than DOM presence alone.
so_what: >
  Listen on the existing language-event owner, report both shown and matched
  counts, index the displayed translated headline, preserve source order, and
  let native hidden state win over component flex/grid layout. No access-control
  or feed model change is required. Test real clicks/taps, not direct render calls.
kind: landmine
verified_at: 2026-09-21
verified_by: 'python3 research/evidence/uiux-news-controls-20260921/verify_controls.py'
scope:
  - 'mastermindx-market-intelligence/macro'
  - 'templates/news.html.j2'
  - 'site/news.html'
  - 'tests/test_news_page_render.py'
confidence: verified
---

Built and locally verified on the News controls carrier; production acceptance is
not implied. The current README and eventual PR own the release frontier. The
separate Basket late-load repair #7589 was accepted on production at merge
b4c3db210e5be5c62efdee1fafe742064baacb5e, comment 5756511503. That outcome and its
merged predecessors are DO_NOT_REDO; the wider UIUX program remains incomplete.
