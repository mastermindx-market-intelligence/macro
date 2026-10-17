---
workstream: WS:REACTIVE-PROJECTION
session: claude/terminal-ext-hours-stability-20260917
model: sol
ended_because: complete
mission: >
  Diagnose and close the Terminal extended-hours quote flicker reported on QCOM, where the detail
  card and watchlist Ext % value repeatedly disappeared and returned, while preserving one canonical
  Terminal Quote Plane and routing any deployment through the existing exact-SHA release owner.
state_before: >
  Production deployment marker 6f2e23951c8981acfc68609526d74d3e8ffbe5b5 served the high-cadence
  Terminal quote route without view=regular. The shared 30-symbol ExtFeed LRU processed the active
  symbol first and could evict it before response assembly; regular quote polls also churned that
  constrained LRU; subscription eviction deleted its last-good print; /api/ext-quote translated a
  Quote Hub transport failure into an authoritative HTTP-200 all-null snapshot; and retained stale
  higher-priority provider data could shadow a fresh fallback. Terminal exact-SHA deployment was
  separately held by canonical release programme issue #483; working SSH access did not create
  deployment custody.
changed:
  - path: terminal:PR#616
    what: >
      Source repair accepted and merged at 82ca818be7ea592f7cdb1fb6731cc19f94610593. The first/active symbol now finishes
      extended demand MRU; high-cadence product callers request view=regular; quote caches are
      partitioned by view; extended demand is independent of transient Polygon health; subscription
      eviction preserves a bounded last-good print; provider priority applies only among currently
      servable candidates; and the ext proxy returns 503 for non-authoritative transport failures.
      Regression coverage spans hub semantics, route/cache contracts, and desktop/tablet/mobile UI
      retention plus recovery.
  - path: agentos/workstreams/WS-REACTIVE-PROJECTION.md
    what: >
      Advanced R1A-T-S from SOURCE_ACCEPTED / production-in-progress to PROVEN_LIVE / done after
      exact served-generation, runtime-byte, QCOM eviction, and public responsive browser proof.
      The record preserves the honest provider-null boundary and leaves Terminal issue #483's
      broader release-hardening programme separate rather than treating it as a product blocker.
verified:
  - claim: >
      Exact Terminal source head fc26254fbcef7a2d5f28321a6152962023db4620 passed the complete local
      Hub suite, Terminal suite, TypeScript check, production build, and focused responsive browser
      regression before protected merge 82ca818be7ea592f7cdb1fb6731cc19f94610593.
    command: >
      cd hub && npm test; cd ../terminal && npm test; npx tsc --noEmit; npm run build;
      CI=1 TERMINAL_E2E_PORT=3207 npx playwright test e2e/watchlist-ext-percent.spec.ts
      --project=desktop --project=tablet --project=mobile
    result: >
      Hub 284/284 passed; Terminal 5,553 passed with 4 existing todo and 0 failures; TypeScript passed;
      production build generated 43/43 static pages; focused browser matrix reported 4 passed and 2
      intentional desktop-only skips.
  - claim: >
      QCOM's reported disappearance was measured as shared ExtFeed subscription churn, not as loss of
      the underlying post-market observation.
    command: >
      ssh -i ~/.ssh/macro_dashboard_deploy_v2 root@146.190.142.17 "journalctl -u quote-hub
      --since '2026-09-17 22:47:00 UTC' --until '2026-09-17 22:48:00 UTC' --no-pager | grep -E
      '(yahoo ext|webull).*LRU-evicted (QCOM|TSM|INTC|NVDA|AAPL|MSFT)'"
    result: >
      The production hub reported both keyless subscription maps at cap 30 and journalled QCOM evicted
      from Yahoo and Webull at 22:47:29Z, then again at 22:47:35Z, inside the same request-order bursts
      that evicted surrounding visible names. Direct hub reads still returned a valid QCOM Polygon
      delayed post-market print between cycles.
  - claim: >
      Current production still exercises the pre-fix high-cadence demand path and therefore is not
      acceptance evidence for the repair.
    command: >
      node /tmp/prod_ext_stability_probe.cjs https://app.mastermind-x.com
      6f2e23951c8981acfc68609526d74d3e8ffbe5b5
    result: >
      Probe failed on the real public QCOM Terminal because its /api/quote request carried syms but no
      view=regular. This is the intended before/after discriminator and proves MERGED_NOT_DEPLOYED,
      not a source regression.
  - claim: >
      The incumbent deployment path is held by the existing exact-SHA release programme rather than
      this product PR.
    command: >
      gh issue view 483 --repo mastermindx-market-intelligence/mastermind-terminal --json
      number,title,state,body,comments,url; gh pr view 605 --repo
      mastermindx-market-intelligence/mastermind-terminal --json number,state,isDraft,headRefOid,
      mergeStateStatus,comments,statusCheckRollup,url
    result: >
      Issue #483 remains the canonical GitHub-to-production release programme. Its broader
      exact-SHA release hardening continues independently and does not need to be completed in order
      to truthfully accept this already-served product repair.
  - claim: >
      The protected #616 repair is installed in the serving application and Quote Hub at one exact
      reconciled production generation.
    command: >
      Read-only SSH at 2026-09-18T12:21Z: compare /opt/terminal/.gitsrc HEAD and
      /opt/terminal/terminal/.deployment-id; sha256sum the canonical and live copies of
      hub/lib/extfeed.js, hub/lib/quotes.js, hub/hub.js, terminal/app/api/ext-quote/route.ts,
      terminal/app/api/quote/route.ts, and terminal/components/TerminalShell.tsx; verify
      82ca818be7ea592f7cdb1fb6731cc19f94610593 is an ancestor of HEAD.
    result: >
      Canonical checkout and deployment marker both equal
      1f56eae265bdbb69c60ce1c5b63dcea19f1f480e; every checked repaired file is byte-identical
      live vs canonical; the #616 merge is an ancestor; Terminal and Quote Hub are active from the
      current generation; QCOM ext-LRU evictions since that Quote Hub restart equal zero.
  - claim: >
      The real served Terminal preserves QCOM extended-hours state through a non-authoritative
      transport failure and keeps regular polling out of the constrained extended-feed demand lane.
    command: >
      One-time public Playwright proof at 2026-09-18T12:20Z derived from the committed
      terminal/e2e/watchlist-ext-percent.spec.ts regression, run against
      https://app.mastermind-x.com and bound to deployment
      1f56eae265bdbb69c60ce1c5b63dcea19f1f480e; durable receipt posted on Terminal PR #616 and
      release carrier issue #483.
    result: >
      PASS at desktop 1440x900 and mobile 390x844. Every real /api/quote request used
      view=regular. Desktop QCOM detail plus watchlist Ext/Ext % and the compact mobile pre-market
      lane retained 188.23 / -0.25% across an injected HTTP 503, then advanced coherently to
      188.42 / -0.15% after recovery. Production assets exposed the expected deployment id.
unverified: []
unresolved:
  - >
    The keyless production source may truthfully have no QCOM print in an otherwise extended session
    and may have no true 20:00-04:00 ET coverage. At acceptance time real QCOM pre-market ext was
    null. That is an honest source-coverage state, not recurrence of the fixed churn defect, and this
    wave deliberately does not invent a feed or fabricate a price.
  - >
    Terminal issue #483 still owns unfinished W2B-B/W2B-C release hardening. That programme remains
    independently active; it no longer blocks or reopens the product acceptance recorded here.
next_actions:
  - >
    No further action is owed for R1A-T-S. Preserve PR #616 and the production receipts as
    DO_NOT_REDO. Continue only the broader Reactive Projection waves under their own current
    dependencies and acceptance evidence.
  - >
    Terminal issue #483 may continue its exact-SHA release-hardening programme independently; do not
    treat that infrastructure work as evidence that the QCOM product repair is unfinished.
do_not_redo:
  - >
    Do not reopen the ExtFeed root-cause implementation. Terminal #616 already closes active-symbol
    LRU ordering, regular/full demand separation, bounded last-good retention, provider candidate
    freshness, Polygon-health decoupling, transport 503 semantics, and view-partitioned cache behavior.
  - >
    Do not create a second ext feed, quote endpoint, browser cache, deploy controller, or release
    carrier. Terminal Quote Plane and issue #483 remain the canonical owners.
  - >
    Do not interpret an unsupported overnight null as recurrence of the flicker. The recurrence signal
    is a valid current-session ext print disappearing under demand/transport churn and later returning.
danger_areas:
  - >
    A subscription LRU and a last-good data cache are different capacities. Deleting data on subscription
    eviction recreates the bug; retaining data without session and 90-minute serve gates fabricates
    freshness. Both halves are load-bearing.
  - >
    Provider priority must be applied after current-session/freshness eligibility. Otherwise a stale
    retained higher-priority entry shadows a fresh lower-priority fallback.
  - >
    Regular and full quote views must stay cache-separated. A regular cache hit reused for full view can
    suppress the extended response, while full data reused for regular view can silently reintroduce
    ExtFeed demand and fields.
prs: [616]
---

# Continuation

This packet records the bounded Terminal Quote Plane stabilization only. It does not supersede the
broader R2-R5 Reactive Projection programme, issue #483's release architecture, or any current Agent OS
owner. The next lawful modifying carrier is issue #483's existing exact-SHA release path; this chat and
the Macro Agent OS record are not deployment authority.
