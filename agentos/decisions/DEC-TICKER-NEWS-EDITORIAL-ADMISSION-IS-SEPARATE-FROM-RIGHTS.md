---
key: TICKER-NEWS-EDITORIAL-ADMISSION-IS-SEPARATE-FROM-RIGHTS
question: >
  Should a publisher's valid display-rights receipt automatically admit its articles
  to the high-quality Terminal ticker news feed?
answer: >
  No. The public reader requires both current display rights and the shared canonical
  publisher/article editorial policy. Exclude Fool and Zacks, reject unreviewed
  publishers and recognized promotional formats, and identify press releases separately.
  Enforce the same population before pagination, in story details, live projections,
  flow counts and health. Keep original licensed history and the existing single writer.
rationale: >
  The Chairman's 20 October 2026 audit directive identifies the Fool and Zacks articles
  as inconsistent with the intended product. Rights specify permitted use, not quality.
  The prior Massive activation intentionally admitted these publishers and supplied no
  serving gate. A browser-only hide would leave counts, pagination and live/detail paths
  inconsistent. The Macro newsroom's existing policy is the source to reuse.
alternatives:
  - option: Hide the two publisher names in the Terminal component
    why_not: Other readers, counts, story details and live changes would retain the defect.
  - option: Broaden the feed to any publisher when qualified coverage is sparse
    why_not: Reintroduces the same quality failure and converts a coverage gap into hidden noise.
  - option: Treat Macro RSS configuration as a premium ticker-feed entitlement
    why_not: Configuration does not prove rights, original provenance or active delivery.
  - option: Delete historical source reports or replace the shared writer
    why_not: Unnecessary loss of audit history and duplication of canonical acquisition ownership.
evidence:
  - "Chairman request, 2026-10-20: audit Fool/Zacks and upgrade Terminal ticker feeds using Macro News Intelligence as the reference"
  - "docs/ops/shared-news-intelligence.md: release/activation record for Macro PR #9846"
  - "docs/ops/ticker-news-editorial-quality.md: source audit, production read-only census and serving-policy scope"
  - "tests/test_ticker_news_editorial_policy.py: API, pagination, grouped membership, correction, rights and health regression proofs"
affects:
  - WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
  - engine/qkernel.py
  - engine/news_common.py
  - engine/qbus_news_quality.py
  - engine/qbus_news_store.py
  - engine/qbus_news_velocity.py
  - app/ticker_news.py
confidence: high
reversibility: easy
decided_by: Codex principal, implementing the Chairman's source-quality directive
decided_at: 2026-10-21
---

Reconsider individual publishers or article classes only with documented editorial
review and independently valid rights. A new data vendor does not waive either check.
The measured ticker coverage is Benzinga plus GlobeNewswire after exclusions; an
allowlisted Reuters/Bloomberg/FT identity does not assert that feed is active.
