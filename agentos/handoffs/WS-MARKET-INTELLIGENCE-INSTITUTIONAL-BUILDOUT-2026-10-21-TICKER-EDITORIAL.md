---
workstream: WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
session: sol/web-ticker-news-editorial-relevance-20261021-c3
model: codex
ended_because: ci_handoff
mission: >
  Continue the Chairman's ticker-news quality upgrade with evidence-limited
  article-format and optional company-mention views, shared from the reader
  through Terminal. Complete the ordinary review, CI, release and live readback.
state_before: >
  Macro PRs 9942 and 9963 and Terminal PR 1094 are merged, deployed and signed-in
  proven. Fool/Zacks are excluded; remaining allowed inputs are screened
  Benzinga reporting and labelled GlobeNewswire releases. Premium feed
  adequacy remains unproven.
changed:
  - path: engine/qbus_news_editorial.py
    what: Add narrow article-format and company-reference views with deterministic context revisions.
  - path: engine/qbus_news_quality.py
    what: Apply the reader view to rights-projected, once-decoded display fields.
  - path: engine/qbus_news_store.py
    what: Share the view before page limits, grouping, details, current changes and counts.
  - path: engine/qbus_news_velocity.py
    what: Count and annotate flow using the same view and permitted fields.
  - path: engine/news_common.py
    what: Attach reviewed aliases and unambiguous current profile names without allocating identity.
  - path: app/ticker_news.py
    what: Acknowledge views, fence continuations and details, and reset SSE when context changes.
  - path: tests/test_shared_news_intelligence.py
    what: Test format/reference evidence, denied fields, profile ambiguity, groups and corrections.
  - path: tests/test_ticker_news_api.py
    what: Test view acknowledgement, revision/rights/cache/reset behavior and entity normalization.
  - path: tests/test_qbus_news_flow_store.py
    what: Preserve existing timestamp assertions while forwarding optional reader arguments.
  - path: tests/test_ticker_news_flow_api.py
    what: Extend the explicit allowed-query census for the additive view contract.
  - path: docs/ops/ticker-news-editorial-quality.md
    what: Record accepted prior release, sample limits, selectable views and contract boundaries.
prs: [9942, 9963]
verified:
  - claim: The previous provider and article-class repairs reached production.
    command: Release receipts on Macro PRs 9942 and 9963 and mastermind-terminal PR 1094.
    result: Macro live-gap merge dcd72169ecb9ca4d761c2b7b21ea7f2156f08f56; signed-in AAPL removed eight targeted examples while retaining twelve qualifying rows; MSFT retained three labelled GlobeNewswire releases.
  - claim: Shared reader and API behavior passes the affected selection.
    command: python3.14 -m pytest -q --disable-warnings tests/test_qbus_news*.py tests/test_ticker_news*.py tests/test_shared_news_intelligence.py
    result: 683 passed, including six nested-entity snapshot/detail cases.
  - claim: Existing writer and newsroom integration checks pass after committed data is present.
    command: Additional run-qbus/news-common/qkernel/financial-news/CI-packing selection; rerun tests/test_news_common.py after scripts/worktree_sparse.py add data.
    result: 176 distinct checks pass; three initial basket-map failures were missing sparse-checkout data, and all 58 news-common tests passed after materialization.
  - claim: Terminal news behavior and types pass locally.
    command: npx vitest run lib/__tests__/*[Nn]ews*.test.*; npx tsc --noEmit.
    result: 367 passed across eighteen files; TypeScript exited zero. The independent proxy and same-key re-entry findings reproduced eight and two failures respectively before repair.
  - claim: Independent bounded source reviews accepted repaired reader and consumer behavior.
    command: Read-only native reviews of the actual managed candidates and bounded repair rechecks.
    result: Macro normalization recheck PASS; Terminal proxy-acknowledgement and activation-fencing recheck PASS. No deployment or source-adequacy claim follows from these reviews.
unverified:
  - claim: The new selectable views have completed ordinary release and live acceptance.
    what_would_verify: Exact-head hosted checks, backend-first merge/deploy, Terminal merge/git-gated deploy, and signed-in selection/readback recorded on the new PRs.
  - claim: Premium newsroom publishers are actively delivered by this ticker feed.
    what_would_verify: Actual source-specific entitlements, integrated original feed receipts, observed delivery and quality/relevance evaluation.
unresolved:
  - Company mentions can retain incidental mentions and miss useful brand/product stories; it remains optional.
  - New release browser evidence is pending at this source-publication checkpoint.
  - Existing panel set-state-in-effect lint finding reproduces on the pinned unmodified Terminal base.
next_actions:
  - Publish these managed source branches, bind the reviews to the exact commits and conclude required CI.
  - Release Macro first and verify view acknowledgement; then release Terminal and perform ordinary signed-in acceptance.
  - Retain the premium-provider coverage gap explicitly rather than treating filtering as new integration.
do_not_redo:
  - Do not recreate PRs 9942, 9963 or Terminal 1094; their accepted release receipts supersede the earlier pending checkpoints.
  - Both new managed workspaces are reconciled under ticker-news-editorial-relevance-20261021-c3; do not repeat acquisition.
  - Do not reactivate Fool/Zacks to fill sparse views or treat a display-rights receipt as editorial approval.
  - Do not buy, contact or activate a premium provider without the actual authorized entitlement/integration basis.
  - Do not create a second writer or treat derived Macro newsroom intelligence as original publisher evidence.
  - The old optional Fabric audit failed before an attested lease; do not replay that carrier.
danger_areas:
  - Classify only permitted title/URL/summary fields; no bodies, hidden provider tags or model inputs.
  - Decode vendor entities once at the raw-to-display boundary; annotations and SQL must share the same input.
  - Bump the independent editorial rules version when recognition changes; hash current identity, names and rights into context.
  - News/company/all are reader views over the same curated baseline; all does not restore excluded publishers.
  - Explicit Terminal views fail closed on an older unacknowledging API, so backend rollout must precede Terminal.
  - Raw writer retention, rights, source provenance and article-format judgments remain separate.
decisions:
  - DEC:TICKER-NEWS-EDITORIAL-ADMISSION-IS-SEPARATE-FROM-RIGHTS
---

## Current continuation state

MISSION_COMPLETE: false. This source-publication checkpoint is BUILT_NOT_PROVEN for the new selectable views. The existing provider and live-gap releases are complete; the new branch still owes exact-head hosted checks and production acceptance. Later immutable PR release receipts determine deployment status.

Both managed repositories use operation and branch suffix `ticker-news-editorial-relevance-20261021-c3`. Macro starts at `53eefbe142c8c5199f0a67f9e72a2ff27dd16783`; Terminal starts at `8189edb8abd41e1c95d6460ad735549af5538d48`. The workspaces under `/Volumes/Mastermind 2/agent-workspaces/{macro,terminal}/web/` were positively reconciled after unqualified acquisition wrappers. No acquisition or publication effect is pending at this checkpoint.

## Product decision and evidence

News & announcements is the new Terminal default; Company mentions is optional; Broader coverage retains the existing curated population. The read-only six-ticker Benzinga sample at 12:45:25 UTC retained 100 of 104 rows in News & announcements and 62 in Company mentions. The latter varied from 4/20 for MSFT to 19/20 for NVDA. These are retention counts, not accuracy or completeness estimates. The exact per-ticker census and limitations live in `docs/ops/ticker-news-editorial-quality.md`.

The additive view revision binds rules, qualified identity/universe, current names and effective rights. Pagination, detail, flow and SSE use that context. The client requires acknowledgement and a fresh activation even when returning to the same ticker/view. Review marks continue to use the existing story identity.

## Review and verification history

The initial Macro source review found inconsistent HTML decoding between SQL admission and returned annotations. The repair decodes title/summary once at the raw-to-display boundary; six API cases cover ordinary and nested encoding in format headlines, company names and marked tickers. The bounded recheck passed.

The Terminal source review found that the JSON proxy forwarded valid but unacknowledged selected-view responses, and that news → company → news could briefly restore an older ready snapshot. Request-aware parser wrappers now reject wrong acknowledgement/identity, and activation IDs fence all ready snapshots and interrupted state. Eight proxy regressions and two held-request re-entry cases failed before repair and pass afterward. The independent recheck passed.

The final post-repair responsive run passed eight cases with seven intentionally skipped duplicate/project cases. Its controlled matrix covers three viewports, two interface languages, dark and approved light specimens, and all three modes. Forty captured panel states accompany the Terminal change. The production build passed. Exact publication and deployment receipts remain to be recorded on the release PRs. The changed hook/contracts/routes pass scoped lint; the panel's one existing effect lint error was reproduced directly from the pinned base.

## Earlier accepted work

Original provider policy and attribution: [Macro #9942](https://github.com/mastermindx-market-intelligence/macro/pull/9942) and [Terminal #1094](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1094). Live article-class follow-up: [Macro #9963](https://github.com/mastermindx-market-intelligence/macro/pull/9963). Their PR bodies retain concluded CI, merge, runtime and ordinary signed-in observations.

Earlier suite consolidation preserved all editorial assertions while keeping them in the existing shared-news intelligence pack; no CI ceiling or selection gate was weakened. The current CI packing regression still passes. These completed lanes must not be reopened simply because an earlier handoff described them as pending.
