---
workstream: WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
session: sol/web-ticker-news-editorial-live-gap-20261021-c3
model: codex
ended_because: ci_handoff
mission: >
  Complete the Chairman's ticker-news editorial repair after ordinary signed-in
  acceptance revealed remaining Benzinga templates and Opinion/personal-finance
  articles. The original provider and Terminal changes are merged and deployed.
  This follow-up still requires its own review, concluded CI and live readback.
state_before: >
  Macro PR 9942 and Terminal PR 1094 removed Fool/Zacks from the curated ticker
  view and shipped publisher and press-release labels. Signed-in AAPL/MSFT
  checks confirmed those changes, then exposed residual Benzinga article classes.
changed:
  - path: engine/news_common.py
    what: Recognize observed numbered analyst, peer-profile and whale-alert templates; classify exact permitted Benzinga URL sections.
  - path: engine/qbus_news_quality.py
    what: Share a three-argument curated predicate with rights-projected URL values.
  - path: engine/qbus_news_store.py
    what: Apply the same projected category rule before pagination and across story members and changes.
  - path: engine/qbus_news_velocity.py
    what: Count the same curated population under per-source URL rights.
  - path: tests/test_shared_news_intelligence.py
    what: Add 31 regressions for live variants, factual news, URL rights, corrections and groups.
  - path: tests/test_qbus_news_flow_store.py
    what: Preserve the existing timestamp assertion while forwarding the new optional URL-rights argument.
  - path: docs/ops/ticker-news-editorial-quality.md
    what: Record signed-in acceptance, the remaining article-class gap and the URL rights boundary.
prs: [9942]
verified:
  - claim: The original provider and Terminal repairs completed ordinary deployment.
    command: GitHub PR 9942 and mastermind-terminal PR 1094; landed-path comparisons; canonical terminal-build target and live BUILD_ID.
    result: Macro merge 526ce826f0898d8724e79acf3a884f9cec6f3096; Terminal merge d9ec4d2b86e9e9e0129d7fcd4c646f25f7670c49; build-TfctsWXpff2fKS. Both PRs retain release receipts.
  - claim: Ordinary signed-in source controls and labels work after reload.
    command: Open app.mastermind-x.com/terminal News for AAPL and MSFT; select GlobeNewswire; reload the ordinary page.
    result: AAPL first 20 rows Benzinga with no Fool/Zacks; MSFT offered Benzinga and GlobeNewswire and filtered to three labelled press releases.
  - claim: New live-gap cases reproduce the defect and pass with the follow-up.
    command: python3 -m pytest tests/test_shared_news_intelligence.py -q -k 'live_editorial or editorial_sections or url_category'
    result: Before implementation 21 failed and 10 passed; after implementation all 31 passed.
  - claim: The affected backend regression selection passes with the committed data materialized.
    command: python3 -m pytest tests/test_qbus_news*.py tests/test_ticker_news*.py tests/test_run_qbus_news*.py tests/test_news_common.py tests/test_qkernel.py tests/test_financial_news.py tests/test_shared_news_intelligence.py -q
    result: 813 passed in 66.15 seconds; the existing timestamp wrapper forwards the new optional URL-rights argument without weakening assertions.
  - claim: The existing CI packing ceiling and Agent OS record validation pass.
    command: tests/test_ci_pack.py::test_exclusive_curation_narrows_ordinary_code_prs; python3 scripts/agentos.py validate; git diff --check
    result: Packing assertion passed in the initial combined run; record validation exited zero with existing workspace/join warnings; whitespace check clean.
unverified:
  - claim: The follow-up article-class repair is merged and deployed.
    what_would_verify: Independent exact-head review, concluded required checks, ordinary merge/deploy and signed-in AAPL/MSFT readback.
  - claim: Premium newsroom publishers are actively delivered by this ticker feed.
    what_would_verify: Actual source-specific entitlements and original receipts/observations from an integrated premium feed.
unresolved:
  - Remaining Benzinga article-class acceptance is open until the follow-up reaches production.
  - No multi-report control appeared in the sampled live first pages; live grouped-detail/correction delivery was not exercised.
  - The earlier optional Fabric audit failed before an attested lease; do not replay that carrier.
next_actions:
  - Commit and push through the managed publisher, open the follow-up Macro PR, complete independent review and concluded CI, then merge normally.
  - Verify ordinary Macro rollout and reload the signed-in AAPL/MSFT News panels; update the exact PR release receipts.
do_not_redo:
  - Do not recreate the follow-up workspace; its initial unqualified acquisition was reconciled through canonical workspace and publisher status.
  - Original Macro PR 9942 and Terminal PR 1094 are merged and deployed; do not recreate them or rebuild Terminal for this backend-only recognition repair.
  - Do not reactivate Fool/Zacks to fill sparse coverage or reinterpret a rights receipt as editorial approval.
  - Do not activate or buy a premium feed without its actual entitlement/integration basis.
  - Do not create a second writer or use derived newsroom intelligence as original publisher evidence.
  - Held Macro cockpit PR 9612 and Terminal sidebar PR 1081 retain their own release gates.
danger_areas:
  - A denied URL must not affect visible membership, groups, corrections or counts; classify only rights-projected fields.
  - Every SQLite curated call now uses three arguments; old two-argument audit snippets are obsolete.
  - The exact v1 public policy marker remains compatible with the already deployed Terminal.
  - Raw writer retention and current rights remain independent of editorial admission.
  - A warm Terminal tab is not proof of universal automatic policy-cache invalidation; ordinary reload is the acceptance path.
decisions:
  - DEC:TICKER-NEWS-EDITORIAL-ADMISSION-IS-SEPARATE-FROM-RIGHTS
---

## Current continuation state

MISSION_COMPLETE: false. The bounded follow-up is BUILT_NOT_PROVEN. Authentication is resolved; the remaining gate is article-class release and acceptance. The original PRs' deployment receipts and signed-in observations are retained in their GitHub descriptions.

The current operation is `ticker-news-editorial-live-gap-20261021-c3`, branch `sol/web-ticker-news-editorial-live-gap-20261021-c3`, based on `562fc7dd02a95792c1a3f59dee2e147f5ffddf20`. Its managed workspace is `/Volumes/Mastermind 2/agent-workspaces/macro/web/ticker-news-editorial-live-gap-20261021-c3`. The first acquisition left no effect; the same-operation retry created this workspace. Although the wrapper returned unqualified, canonical owner status and `studio_git_publish_status` positively reconciled the existing branch/path and reported ready-to-push. No acquisition is pending; do not retry allocation or change workspace infrastructure.

The repair is confined to recurring formats observed live and exact publisher sections. It preserves factual single-company reporting, field rights, raw retention and the existing public policy contract. The independent reviewer will inspect the published immutable head; the principal owns ordinary release and browser acceptance.

## Historical implementation checkpoints

The following history records the already completed original implementation; its earlier pending-state prose is superseded by the current continuation state and the original PR release receipts.


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
