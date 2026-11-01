---
workstream: WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
session: "ORCH-HEALTH (Opus 5.5 orchestrator commissioned by seat fd47d431; records branch claude/mi-orch-health-records-20261021)"
model: opus
ended_because: ci_handoff
mission: >-
  Chairman 2026-10-21: fix the blockers so the Market-Intelligence buildout can continue to
  completion. ORCH-HEALTH took the seat-side items. It classified the red data-health runs on
  main and drove fabric lanes on the seat-fixable causes. It proved #8900 against the live
  ticker-news store (read-only) and the #8982 invalid-theme chip on the live site in EN and ZH.
  It diagnosed the failing mmx-cimd-probe MCP entry (report only) and recorded the W10 to W14
  landing state in this workstream. The seat keeps all merge, ready and label acts.
state_before: >-
  The workstream file still described W10 as in progress at 2026-10-12 12:05Z. Wave B, the W11
  store/cluster hardening and the W12 native-Arrow follow-ups had all merged since, without a
  record. data-health on main had been red on every scheduled run since at least 10-03
  (issue #5979). #8900 and #8982 were merged without live proof on file.
changed:
  - path: agentos/workstreams/WS-MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT.md
    what: W10 closed as done. Added W11 (the W11 to W14 landing record). Replaced the top-level next_action and added do_not_redo lines for the landed PRs.
  - path: agentos/handoffs/WS-MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT-2026-10-21-ORCH-HEALTH.md
    what: This checkpoint.
verified:
  - claim: >-
      These are MERGED (macro). #8998 a911dcad4c48 (B1), #8995 011064d26097 (B2), #9013
      3ca6eb200da3 (cluster audit read-only URI), #9015 7ed26e3123df (private catch-all and
      422s), #9017 8c91094d3524 (inventory through the store API), #9019 802895d4e29b (cluster
      policy version), #9025 a33692dba406 (concurrent ALTER and policy stamp), #9026
      37ccd914a369 (bare root and non-GET), #9036 604d4ec4a560 (inventory hand-run line),
      #9043 6f159848fa69 (native Arrow), #9527 9bca84d4a12c (FX5 live breadth), #9554
      08e8e5e41dec (news-universe native parquet), #9621 af9854fe1979 (signal-bus doc, merged
      2026-10-19T05:14Z), #8982 624f9000dff7 and #8900 fa3716ec18d7. Terminal #976
      e24a6c9edd18 (not_found empty state), #977 da02025d0b5c (B3 strip) and #978 c799ba7e64e2
      (snapshot provenance) are also MERGED.
    command: "gh api graphql: pullRequest{state mergedAt mergeCommit{oid} title} for each number in macro and mastermind-terminal; then git log --no-walk on the macro merge oids"
    result: Every listed PR is MERGED. Each macro merge oid resolves locally to the commit titled with its PR number.
  - claim: >-
      #8900 holds on the live store. The deployed scripts/ticker_news_inventory.py is
      byte-identical to the origin/main blob. A read-only inventory run returned schema
      ticker_news.inventory.v1 with live, fresh health. An independent read-only sqlite read
      matched it exactly.
    command: "Read-only ssh to the VPS: sha256sum of the deployed script vs the origin/main blob; python3 scripts/ticker_news_inventory.py with no --rights flag; sqlite3 with mode=ro on the same store. No systemctl, no edits, no env-file reads."
    result: >-
      rc=0 at 2026-10-21T09:36:19Z. alpaca_rest 1036, alpaca_ws 6692 and massive_news_v2 458210
      deliveries, all recent. revisions 8480, states 7805, clusters 7802, changes 8065.
      catchups_failed 0, rest_catchup_proven true, universe 503. The ro read at 09:36:50Z
      matched. The service was active with NRestarts=0.
  - claim: >-
      #8982 renders correctly in production in both locales. When theme_state is dated after
      the leadership read, the receipt shows the invalid-state chip "Theme state dated after
      this read" (ZH 主题状态日期晚于本次判读) with muted ink. The page is public; only the
      /basket/ directory returns 401.
    command: "curl of the live theme-detail page, its payload and the served stylesheets; offline replay of leadershipReceiptHtml against the live payload; live DOM read with data-lang en and zh"
    result: >-
      The payload has theme_state as_of 2026-10-20 against leadership_receipt as_of 2026-10-19,
      so the invalid branch is the correct one. The served CSS carries the locale-hide rules and
      the state-stale chip rule. In the DOM, the chip is visible in each locale and the other
      locale's span is hidden.
  - claim: >-
      data-health classification. The two commissioned red runs on main (39310733883 and
      39471481359) have 41 distinct failing jobs, and none is attributable to an MI PR. The
      seat-fixable causes are missing CI dependencies (jsonschema, jinja2, fastapi, bs4,
      plotly, playwright and rjsmin) and three test-fixture defects. Every other failure is a
      real or data-driven failure owned outside this workstream.
    command: "gh run view <run> --log-failed, saved and split per job and step; the proving line was taken per segment; last-touch attribution was read from git log on each failing test's files"
    result: "41 jobs, 0 MI attribution. Run 39404240318 (workflow_run, 2026-10-20 09:55Z) concluded success, so the red is not uniform across triggers."
unverified:
  - claim: "#9527 FX5 live breadth reached PRODUCTION_PROOF at 2026-10-19 12:21Z (seat-reported)."
    what_would_verify: A fresh read-only check that the live-breadth artifact on the VPS was rebuilt after the merge through the native parquet path, with current timestamps.
  - claim: "#9025 cluster policy stamp reached PRODUCTION_PROOF at 2026-10-19 04:44Z (seat-reported)."
    what_would_verify: A read-only sqlite read of the live store showing the stamped policy version on recent cluster rows.
  - claim: "#8982 locale switching through the site's own language toggle."
    what_would_verify: A browser session that clicks the header language control rather than setting data-lang directly. The DOM proof set the attribute.
unresolved:
  - "Signed-in browser checks are owed: #9015 (private catch-all), terminal #978 and #976, and terminal B3 (#977) in dark theme."
  - "data-health on main stays red until the dependency and fixture DRAFT PRs merge and their owners repair the remaining jobs. Those jobs include contract-drift, house-law-registry, private-boundary, title-i18n, hub-a11y, capital-structure-intelligence and the inherited unrun-* jobs."
  - "theme_intel lags theme_state by a day, so the #8982 invalid branch fires on every read made before the theme-intel rebuild. That is the designed honesty behaviour, not a defect. A producer-ordering change would belong to the theme-intel owner."
  - "Human-only items are unchanged. They are the Grok login (mb/m1), the Benzinga, Massive and twitterapi.io accounts, Package R #8438, C19 OAuth, the X1 25k cap (Sol preregistration sizing), H05 (held), and MCP OAuth for linear-server, mastermind-executive and figma."
  - "The mmx-cimd-probe MCP entry is a user-scope Claude config pointing at a local port with no listener, and its install receipt says failed. Removing it is an operator act: claude mcp remove mmx-cimd-probe -s user."
next_actions:
  - "Seat: adjudicate the ORCH-HEALTH return. Review and merge the lane DRAFT PRs (CI dependency installs and test-fixture repairs). Apply the .github patch, which is seat-only."
  - "Seat: run the owed signed-in browser checks for #9015, terminal #976, #978 and #977 (dark)."
  - "Seat: route each remaining red data-health job to its named owner once. Do not repair them from this workstream."
do_not_redo:
  - "Every PR listed under verified is MERGED. Never reopen, re-spec, re-review or re-land them."
  - "#8900 and #8982 are proven live (2026-10-21). Do not re-prove them unless their source or the live payload contract changes."
  - "The mmx-cimd-probe diagnosis is complete: no listener exists and none is defined anywhere. Do not start or install a server to satisfy it."
danger_areas:
  - "theme.js has several live writers (#9953 and others). The hub-a11y and template-site-sync failures touch it, so never edit it from this workstream."
  - "The privacy-boundary guard scans the generated agent_os_state.json. A host path or a dollar amount in any workstream next_action turns data-health red for everyone."
  - "data-health pack 5 was truncated in run 39471481359. Absence of a job there is not a pass."
---

## Data-health classification (runs 39310733883 and 39471481359)

The dependency lane installs the missing modules into the affected jobs. Those modules are
jsonschema (capability-broker and four unrun-* jobs), jinja2 (outcome-spine), fastapi
(neural-web-core), bs4 and plotly (express-render-guards, tier-gate), playwright (one
engine-render-guards node) and rjsmin (portfolio-ctx). The `.github` half of that change is a
seat-applied patch.

Two fixture lanes cover the test-only defects. One handles the government-revenue fixture
stylesheet (unrun-government-revenue). The other handles transmission-chains
`_observation_state` and the engine-render-guards ud_b1 nodes.

The remaining jobs fail on real assertions or data, owned outside this workstream:

| Job | Failure |
|---|---|
| contract-drift | Four new site/prophet/index.json fields are not yet in the export contract. |
| house-law-registry | The sp600 stable keys BLFS and HLX have no alias boundary. |
| private-boundary | Host-path and dollar-amount strings sit in the BREATHING-PLATFORM and DEFENSE-PROCUREMENT-V3 wave next_actions. |
| title-i18n | Dual-span markup appears in am_edition `<title>`, plus a CJK title in the dashboard scoreboard. |
| hub-a11y | The theme.js html[lang] sync is missing. |
| capital-structure-intelligence | The job timed out after 10 minutes with four failures. |

The rest are the inherited unrun-* contract and data assertions listed in the ORCH-HEALTH return.
