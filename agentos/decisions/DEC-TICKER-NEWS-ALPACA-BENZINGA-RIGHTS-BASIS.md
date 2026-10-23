---
key: TICKER-NEWS-ALPACA-BENZINGA-RIGHTS-BASIS
question: >
  The ticker-news writer (scripts/run_qbus_news.py, N-lane of the Market-Intelligence
  Institutional Buildout) was built against Benzinga's direct stream and is gated on a
  rights receipt for source "benzinga", but the estate holds no direct Benzinga
  contract and the writer never went live. May the writer ingest Benzinga-sourced
  headlines through Alpaca's official Market Data news API instead — and what is the
  rights basis recorded on the receipt?
answer: >
  Yes. The writer gains a provider adapter (collectors/alpaca_news.py; `--provider
  alpaca`) that reads Benzinga-sourced items from Alpaca's official REST/WS news
  endpoints with the estate's existing Alpaca key pair, keeps `source: benzinga` as
  the source of record, drops any item whose `source` is not benzinga, and runs under
  a committed rights receipt (config/ticker_news_rights_alpaca_benzinga.json,
  receipt_id rights-alpaca-benzinga-news-2026-10-11) whose capabilities are the
  headline-display subset only: internal_ingestion, historical_retention,
  headline_display, source_link_display, teaser_display, derivative_processing TRUE;
  body_display and image_display FALSE. Rights basis = the Alpaca Market Data
  agreement under which the estate already consumes the same endpoint for the
  marketing press lane, plus docs/QUAL_DATA_COMPLIANCE.md §1.2 (published wire news,
  ToS-compliant, no raw-feed re-publication). A direct Benzinga contract remains a
  Chairman procurement OPTION, not a prerequisite.
rationale: >
  The receipt gate exists to stop unlicensed redistribution, not to pin a transport.
  Alpaca's news API is Benzinga-powered and is served under Alpaca's own terms to
  keyholders; the estate already ingests it lawfully via engine/marketing/
  press_providers.py AlpacaNewsProvider (IS-W1 "free spine", armed by env presence
  per config/press_sources.yml). Routing the ticker-news writer through the same
  official endpoint with the same keys inherits that basis; the receipt records the
  narrower capability set the Terminal rail actually renders (headline + teaser +
  source link, never body or image), so the live surface can never exceed what the
  basis supports. Buying a direct Benzinga feed would duplicate a source the estate
  already has and was the one blocker that had held N at EXACT_HUMAN_GATE since
  2026-10-06; the Chairman's 10-11 directive ("take ownership … no one else is
  working on them") assigns the seat to clear it with the lawful path already on
  disk rather than wait on a purchase.
alternatives:
  - option: Purchase a direct Benzinga API subscription and keep the writer as built
    why_not: >
      Money movement is Chairman-only; the direct stream adds nothing the Alpaca
      endpoint does not already deliver for headline display; the lane would stay
      dark for an unbounded time. Remains available as a later upgrade (body/image
      capabilities would need a new receipt).
  - option: Switch the writer to Tiingo (Sol's held #8697 adds a tiingo receipt path)
    why_not: >
      #8697 is a held Sol lane on a different product surface (news.html); the
      Terminal rail's parser, dedupe, and tests are Benzinga-shaped; Tiingo keys are
      not provisioned on the VPS. Not touching a held sibling.
  - option: Fabricate or self-issue a "benzinga" receipt from API possession alone
    why_not: >
      Forbidden — the runbook says a receipt is never created from API possession
      alone, and an authority override cannot cure a data/rights-availability
      blocker. The Alpaca receipt is honest about its basis and its narrower caps.
evidence:
  - "docs/QUAL_DATA_COMPLIANCE.md:23 — Benzinga/Tiingo/… wire feeds: published wire news, ToS-compliant, redistribution limits honored"
  - "config/press_sources.yml ~L458-473 @ 430198676d96: alpaca lane enabled, rest_url data.alpaca.markets/v1beta1/news, key_env ALPACA_API_KEY_ID / secret_env ALPACA_API_SECRET_KEY, armed by env presence"
  - "engine/marketing/press_providers.py ~L72-78, ~L658-661 @ 430198676d96: AlpacaNewsProvider — official REST, limit 50, 429 backoff ladder"
  - "engine/qbus_news_receipts.py:25 `_SOURCE = \"benzinga\"` and :183 allowed_sources — source of record unchanged by the provider adapter"
  - "VPS /etc/macro-live.env: both ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY lines PRESENT (grep -c, values never read) — seat check 2026-10-11"
  - "PR #8809 (claude/mi-n-alpaca-provider-20261011): adapter + receipt + tests; PR #8809 MERGED 2026-10-11 as 9b1da2b55e6e (squash of head 1d8a481ce9f4; blob-verified on origin/main)"
affects:
  - WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
  - scripts/run_qbus_news.py
  - collectors/alpaca_news.py
  - config/ticker_news_rights_alpaca_benzinga.json
  - app/deploy/ticker-news-setup.sh
  - docs/ops/ticker-news.md
confidence: high
reversibility: easy
decided_by: coo-fable (seat fd47d431, Chairman 2026-10-11 autonomy directive)
decided_at: 2026-10-11
review_by: 2027-10-11
---

Supersedes nothing. The receipt's capability set is the ceiling for every consumer of
`alpaca-rest` rows: a surface that wants body or image display needs a NEW receipt with
a basis that supports it (a direct Benzinga contract), never an edit of this one. The
receipt expiry (2027-10-11) is the review clock.
