---
key: BASKET-NATIVE-DISCLOSURE-REFRESH-20260920
claim: >
  In macro at 49a568199d738ce4cdab878b42d6587fc13870e1, sorting a Basket Detail table
  closed an open score disclosure, while Chinese Timing cards ignored available
  source labels and mobile flow statistics collapsed into narrow columns.
falsifier: >
  Run the real-browser probe preserved in PR #7497 / continuation basket-before.json
  against that immutable source: opening score details then clicking Potential must
  keep it open, and Chinese cn_solar Timing values must already be localized, to
  disprove the recorded defects.
so_what: >
  Every basket render and optional-widget reinjection must preserve native disclosure
  state and focused summary. Test actual sorting and delayed optional responses,
  source-language/null values and component widths; document-level zero overflow
  alone cannot detect narrow unusable columns. Continue on PR #7497, not a duplicate.
kind: landmine
verified_at: 2026-09-20
verified_by: 'PR #7497; research/evidence/uiux-basket-score-resilience-20260920/continuation/'
scope:
  - 'mastermindx-market-intelligence/macro'
  - 'templates/basket_detail.html.j2'
  - 'site/basket*/**'
  - 'tests/test_ftr_w3_ui.py'
confidence: verified
---

The repair is built and browser-verified, not yet a production acceptance. Its
continuation README names exact authority, source, unchanged data/auth/model
boundaries, evidence, shared-owner release blockers and VPS-only next actions.
