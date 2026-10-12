# News Provider Semantics Implementation Plan

Goal: make the existing optional AI-news adapter consume the documented Finlight v2 response without turning sentiment confidence into importance, losing company symbols, or inventing publication freshness. This is a source repair under #7953, not activation or a new feed.
Architecture: preserve news_ai_feed.fetch/_normalise_ai and build_news._enrich. Extend the existing ticker_shape gate; no new store, identity, queue, LLM call or publication path. Keep #7955's ranker and #7591/#7575 work frozen.
Source base:25fb8fa805d611727078f65626f2c3b0388070b3. Official contract:https://docs.finlight.me/en/v2/rest-endpoints/ (inspected2026-09-24 local date).

Files:engine/news_ai_feed.py; tests/test_news_ai_feed_contract.py; update two legacy provider fixtures to supply explicit importance instead of confidence/relevance in tests/test_news_rank_aging.py. The last file overlaps #7955 only by filename; its appended regressions must survive a three-way compatibility check.

1. Write and run the new tests against ORIGINAL production source. Require assertion failures for confidence/relevance misclassification, missing companies tickers, invented timestamps and undocumented request method. Network is replaced only at the requests boundary; use the real normalizer and News ordering consumer.
2. _ai_importance accepts only explicit importance/importanceScore and finite non-boolean values within0..100; preserve legacy explicit importance scaling. Retain sentiment confidence separately within0..1, with no ranking contribution. Missing metadata stays null.
3. Map provider companies only when its explicit listing venue is a known US venue; never infer a US listing from issuer domicile or strip a foreign prefix. Reuse ticker_shape.valid_us_ticker. Count exclusions. Preserve legacy tickers/symbols/entities inputs and caps.
4. _iso never substitutes the collection clock for an absent/malformed publisher timestamp. Keep _crawled_at and available vendor indexing/revision timestamps separate. Keep named timestamp-quality states.
5. Use documented Finlight POST /v2/articles JSON, pageSize bounded1..100, includeEntities requested. Preserve legacy custom-provider GET path. One HTTP attempt; disabled/keyless stays zero network. Isolate malformed response rows so later valid rows survive.
6. Run the new suite and existing News/common/qkernel suites, disabled LLM ordering test, three-way overlap check with #7955, and mutation checks. Never touch the real data tree or assert full conftest/browser coverage from selected-source proof.
7. Publish exact hash-verified source under one operation branch and draft PR; request independent review and keep CI/release holds. No vendor credentials or configuration activation. Deployment/browser proof is owed before live acceptance.

Review focus: neutral-high-confidence is not high importance; same letters on a non-US exchange are not a US ticker; clock absence cannot become fresh publication; one malformed row cannot erase the batch; API denial is neither empty-market evidence nor permission to retry through another account.

Integration note: the first test-only merge check found adjacent-hunk overlap with #7955's appended regressions. The legacy valid-importance fixtures now explicitly name importance; separate new tests retain confidence/relevance-null requirements. A fresh three-way check preserves all #7955 regressions without changing its carrier.

CI enrollment: the older News suite belongs to gate:data, so it cannot prove this adapter on the merge gate. Add only this source-only provider suite to the EXISTING gate:code collector-registry job in .github/ci/legacy-jobs.yml; no new job, runner, queue, or gate change. Enrollment is itself red/green tested.

## Executed proof (selected-source snapshot, not full repository/runtime)
- 63 new source-contract tests PASS; original adapter mutation: 50 failed, 13 passed.
- New + existing News/common/qkernel suites: 157 passed, exit0.
- Exact-head #7955 composed by three-way test merge plus its unmodified ranker:183 passed, exit0. No source change to #7955.
- Source and test AST parse, whitespace/conflict checks PASS. Only one existing CI job gains one test step; no gate/runner/job added.
- Vendor remains configured disabled; no real vendor calls, credential reads, model activation or production publication occurred. HTTP fixtures exercise POST/GET/status handling, not actual entitlement.
- Limit: no repository-wide conftest/data guard, full page build, hosted CI, independent review or browser/production acceptance is claimed from these selected-source results.
