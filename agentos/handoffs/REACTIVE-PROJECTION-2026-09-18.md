---
workstream: WS:REACTIVE-PROJECTION
session: claude/terminal-ext-hours-stability-20260917
model: sol
ended_because: blocked
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
      Added wave R1A-T-S as SOURCE_ACCEPTED / production-in-progress. It names the exact protected
      Terminal merge, current production RED discriminator, canonical release dependency on issue
      #483, required post-deploy browser/runtime proof, and the honest unsupported-overnight limit.
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
      Issue #483 remains the canonical GitHub-to-production release programme. PR #605 is its active
      same-carrier exact-target preflight work and remained Draft while natural CI and the larger
      release sequence continued. No legacy moving-master deploy was authorized.
unverified:
  - claim: >
      The accepted Terminal merge 82ca818be7ea592f7cdb1fb6731cc19f94610593 is running in production and the real QCOM UI no
      longer flickers under extended-feed churn or transport failure.
    what_would_verify: >
      Issue #483 must admit and deploy an exact accepted SHA containing 82ca818be7ea592f7cdb1fb6731cc19f94610593; then run the
      prepared public browser probe against that deployment and reconcile Terminal plus quote-hub
      service identity, real request view=regular, desktop detail/watchlist Ext and Ext %, compact
      tablet/mobile extended lanes, 503 retention, recovery advancement, and no fabricated overnight
      value.
unresolved:
  - >
    Production acceptance is blocked only in the deployment lane by canonical issue #483. Source
    implementation, exact-head tests, protected merge, and dependent return are complete and must not
    be redone.
  - >
    The current keyless production source set still may have no true 20:00-04:00 ET print. That is an
    honest coverage null, not the flicker defect, and this wave deliberately does not invent a feed or
    fabricate a price.
next_actions:
  - >
    On issue #483, consume protected Terminal merge 82ca818be7ea592f7cdb1fb6731cc19f94610593 through the admitted exact-SHA
    release path once the complete deploy/rollback implementation is ready. Do not use the legacy
    moving-master VPS wrapper as a shortcut.
  - >
    After deployment, run /tmp/prod_ext_stability_probe.cjs with the served accepted deployment SHA,
    plus direct quote-hub health/full/regular reads, and attach the receipts to #483 and Terminal #616.
  - >
    Mark R1A-T-S done only after that production identity and browser/runtime matrix pass. A merge,
    green CI, or source-only browser fixture is not enough.
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
