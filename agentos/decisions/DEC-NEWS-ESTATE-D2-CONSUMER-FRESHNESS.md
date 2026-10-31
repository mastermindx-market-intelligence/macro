---
key: NEWS-ESTATE-D2-CONSUMER-FRESHNESS
question: >
  Which real consumer is the first news-estate boundary, and how does it expose the true
  freshness and evidence grade of what it serves, given that Mastermind get_news and
  get_intelligence read vendored Macro files whose asof is re-stamped with the build date
  when the never-darken guard retains a previous artifact?
answer: >
  The first consumer is the Mastermind boundary (brain/bot_mcp.py get_news/get_intelligence,
  portfolio/lenses.py _news_row, data_layer/macro_refresh.py anchors) reading the vendored
  Macro file, not a live API. The Macro producer (scripts/build_news.py, engine/financial_news.py)
  carries its true as-of: by_ticker.json gains optional source_asof (the fetched_at of the
  feed actually written, null when unknown), source_asof_basis, retained_from_previous_build,
  retained_reason (only when retained), and per-row item_id (R1 report key
  massive:<domain>:<id>, only where the qbus contract accepts the payload; never joined with
  the qbus item_id hash column) and published_utc (aware timestamps only). asof keeps its
  meaning (build date). The consumer exposes freshness {asof, source_asof,
  retained_from_previous_build, generated_utc, basis:"vendored_macro_file", source_file} and an
  evidence_grade of exactly vendored_snapshot, or legacy_fallback with missing_reason and
  fallback when the ticker is absent; a retained row renders as stale_retained through the
  existing lens flag mechanism. A rights_scoped_snapshot grade exists only as a PROPOSAL for
  an authenticated /api/ticker-news adapter (docs/TICKER_NEWS_ADAPTER_PROPOSAL.md); no
  adapter, HTTP client, store, cache, scheduler or flagging system ships.
rationale: >
  The Chairman named the Mastermind tool/lens boundary losing freshness as a defect. The
  vendored file is the consumer that exists today and is the one a corrected-event journey
  reaches first; making it honest about retention and source clocks (B1 rules R1/R4/R7)
  removes the freshness lie without a second data path. The grade ceiling vendored_snapshot
  states plainly that no rights-qualified per-item evidence backs these payloads; the
  higher grade waits on a service auth identity for the bot, which is a human-only step.
alternatives:
  - option: Wire get_news directly to the authenticated /api/ticker-news endpoint now
    why_not: >
      The bot has no service auth identity for require_site_full_user; building a client
      around a missing identity would either bypass auth or ship dead code. Proposal only.
  - option: Correct asof itself to the retained file's stamp
    why_not: >
      asof means build date to every existing reader; changing its meaning is a silent
      contract break. Additive fields carry the source clock with its basis instead (R4/R7).
evidence:
  - "macro #10280 head 4dd74f0b825baa9eec8ecb2322ce585c050f121c (draft, base main 28b4a2a99ea5) — producer fields, T1-T4+T2b 6 passed (3 failed pre-change), owned tests 50 passed, affected suite 979 passed 4 skipped; Fabric glm-5.3 review news-orch2-4 ACCEPT_WITH_NOTES, four findings folded"
  - "Mastermind #1897 head 5cc144ad9d71415ccc2de6daa9870553fd659a7c (draft, base master bb85b429f2ff) — consumer fields, T5-T8 5 passed (5 failed pre-change), affected suite 843 passed 16 skipped 6 failed (the 6 fail identically on base: vendor/macro_src absent in sparse tree); Fabric glm-5.3 review news-orch2-5 ACCEPT_WITH_NOTES, MMREV-01/02/04/05 folded"
  - "ORCH-2 return 2026-10-31 (Opus orchestrator a16bd67dbb60a27d4): PASS-WITH-GAPS; open gap MMREV-03 — intelligence/by_ticker.json does not carry the news leg's source_asof or retained flag, so the bundled path reads null (producer follow-on, outside owned files)"
affects:
  - WS:NEWS-INTELLIGENCE-ESTATE-CONVERGENCE
  - Mastermind get_news/get_intelligence boundary and portfolio lenses
confidence: medium
reversibility: easy
decided_by: fable-meta-ceo
decided_at: 2026-10-31
---

## Operating law

A consumer of a vendored Macro news file states its evidence_grade and freshness from the
file's own stamps and never from the read time. No grade above vendored_snapshot is claimed
until a rights-qualified per-item path is built under a real service identity. Producers that
bundle the news leg (intelligence/by_ticker.json) owe the same source_asof and retained flag
(MMREV-03) before the bundled path may claim freshness. Neither PR is merged at this record;
the seat merges each with --match-head-commit after CI and its own reviewDecision read.
