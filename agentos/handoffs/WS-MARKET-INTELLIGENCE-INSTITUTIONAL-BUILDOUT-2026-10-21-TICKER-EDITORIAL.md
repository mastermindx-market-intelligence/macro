---
workstream: WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
session: sol/web-ticker-news-provider-quality-20261020-c3
model: codex
ended_because: ci_handoff
mission: >
  Candidate publication checkpoint for the Chairman's Fool/Zacks provider audit and
  Terminal ticker-news quality repair. The principal continues through review,
  concluded CI, ordinary deployment and live verification; this is not a completion claim.
state_before: >
  The shared ticker reader enforced rights but not editorial admission. The earlier
  additional-source activation deliberately included Fool and Zacks. The live Apple
  first page had 13 Fool, 6 Zacks and 1 Benzinga row. The Macro newsroom already had
  stronger source/article screening and a separate derived intelligence feed.
changed:
  - path: engine/qkernel.py
    what: Canonical publisher exclusions, strict hostname tiers and source categories.
  - path: engine/news_common.py
    what: Shared ticker editorial predicate, preserving factual company announcements.
  - path: engine/qbus_news_quality.py
    what: Versioned curated reader predicate and SQLite registration.
  - path: engine/qbus_news_store.py
    what: Consistent pre-pagination curation across rows, details, projected changes and counts.
  - path: engine/qbus_news_velocity.py
    what: Optional curated count population with unchanged raw mode.
  - path: app/ticker_news.py
    what: Public curated reader, additive content attribution and scoped delivery health.
  - path: tests/test_shared_news_intelligence.py
    what: Regression coverage for screenshot cases, rights, pagination, corrections and health; enrolled in ticker-news-qbus CI.
  - path: docs/ops/ticker-news-editorial-quality.md
    what: Source audit, explanation of the inclusion error, policy and premium-coverage boundary.
verified:
  - claim: Shared backend and financial-news regression checks pass locally.
    command: python3 -m pytest tests/test_qbus_news*.py tests/test_ticker_news*.py tests/test_run_qbus_news*.py tests/test_news_common.py tests/test_qkernel.py tests/test_financial_news.py tests/test_shared_news_intelligence.py -q
    result: 767 passed; the committed data tree was materialized before this run.
  - claim: Terminal news contract and rendered-consumer checks pass locally.
    command: npm test -- lib/__tests__/tickerNews lib/__tests__/newsCatchupPanel.test.tsx lib/__tests__/newsReviewState.test.ts; npm test -- news
    result: 225 tests in the first selection and 334 in the second; selections overlap and are not summed.
  - claim: Terminal production code builds and typechecks.
    command: npm run build; npx tsc --noEmit
    result: Both exited zero; later changes are test fixtures, evidence and documentation.
  - claim: Real-shell responsive fixtures pass.
    command: TERMINAL_E2E_PORT=3271 TERMINAL_CROPS=1 npx playwright test e2e/ticker-news.spec.ts --project=desktop --workers=1
    result: Four tests passed, including EN/ZH at three sizes; light captures are explicitly D-W1 specimens.
unverified:
  - claim: The candidate source is merged and deployed.
    what_would_verify: Matching published heads, concluded required checks, ordinary merge/deploy receipts and fresh live policy marker/readback.
  - claim: Premium newsroom publishers are actively delivered by this ticker feed.
    what_would_verify: Actual source-specific entitlements and original receipts/observations from an integrated premium feed. Allowlist membership does not suffice.
unresolved:
  - The candidate source still needs independent review acceptance and hosted CI at this checkpoint.
  - The optional read-only Fabric audit carrier ticker-news-macro-policy-audit-20261020-c3-01 failed on a retained request packet before lease. Its wrapper did not attest execution absence; preserve the exact carrier and do not replay it.
next_actions:
  - Finish the bounded independent reviews and publish both managed source branches under ticker-news-provider-quality-20261020-c3.
  - Follow required CI, merge through normal gates, let the Macro update lane apply the backend, and deploy Terminal with its canonical build owner.
  - Verify the ordinary authenticated Terminal page, eligible publishers, grouped detail, flow counts and live refresh. Record release proof on the exact PRs.
do_not_redo:
  - Do not reactivate Fool/Zacks to fill sparse coverage or reinterpret a rights receipt as an editorial approval.
  - Do not buy a direct Benzinga headline feed; DEC:TICKER-NEWS-ALPACA-BENZINGA-RIGHTS-BASIS remains valid.
  - Do not create a second news writer or use a derived newsroom snapshot as original qbus publisher evidence.
  - The existing held Macro cockpit PR 9612 and Terminal sidebar PR 1081 retain their owners and release gates.
danger_areas:
  - Reader policy must remain consistent across pagination, current story members, changes, flow and health.
  - A publisher's display name is not its licensed source identity; keep source keys and original provenance intact.
  - Terminal's dark theme ships; approved light specimens do not assert a live light mode.
  - Raw writer history and current rights are independent from the curated reader and must remain intact.
decisions:
  - DEC:TICKER-NEWS-EDITORIAL-ADMISSION-IS-SEPARATE-FROM-RIGHTS
---

Both source workspaces use the managed operation `ticker-news-provider-quality-20261020-c3`.
Macro was based on `e5dd30c6344e4b62a0beba054ac4da97e00bab36`; Terminal on
`e3ca39a82d9713061e5e27ac0cd3ac1d249af127`. Subsequent published PR state, not this
pre-release checkpoint, determines deployment/completion. The scoped Terminal lint
finding is pre-existing: the same `setDetailBusy(null)` effect is rejected on the
unchanged base by `eslint --stdin --stdin-filename components/news/TickerNewsPanel.tsx`.


## Independent review repair checkpoint

Macro PR #9942 was confirmed created after the interrupted publication call.
Independent source reviews inspected Macro `543cba1ea597171958a66267c9044fa13b1ae068`
and Terminal `9d07f3c8fa14abbb7c2ed5531ef4210cd1b3fbeb` through GitHub. Three P2
findings were accepted and repaired before release: use parsed health fields
(`configured_publishers`, `accepted_reports_since_start`); preserve explicit
factual company events containing otherwise ambiguous earnings/bell timing;
and bind expanded story caches and outstanding responses to group sequence and
editorial policy. The new tests reproduced seven backend failures and three
Terminal failures before repair. The repaired backend selection passes 782
tests; the Terminal news selection passes 337. The source reviews are actual
inspection, distinct from the earlier architecture-only advice. Final delta
review, hosted checks and live deployment proof remain separate release gates.


## CI packing repair checkpoint

Hosted contract-delta checks found that registering a separate editorial test module
added two estimator weight units to the already-selected ticker-news-qbus job,
exceeding the existing free-content probe ceiling (5,797 versus 5,795). The
editorial cases and helpers were moved into the existing shared-news intelligence
suite, whose subject already includes source quality, rights and live consistency.
All assertions and parameter cases are retained, with private helper names to
avoid collisions. Only the redundant path and invocation entries were removed;
production logic, job selection rules and packing ceilings are unchanged. This
is suite consolidation, not a runtime-saving claim. Concluded hosted checks and
production proof are still required after publication.

After consolidation, the same backend selection passed all 782 tests, and
`tests/test_ci_pack.py::test_exclusive_curation_narrows_ordinary_code_prs`
passed with the existing packing ceilings. Hosted CI remains unverified for
this test-only follow-up until its published run concludes.
