# China Gold Premium Monitor Implementation Plan

Goal: Add a source-entitled, fail-closed Shanghai-versus-London gold premium monitor to the
existing Gold detail surface without changing trading authority.

Architecture: A pure provider-neutral engine reads explicitly entitled existing store references,
computes the canonical SHAUPM/LBMA-AM series and optional Au99.99/spot proxy, and returns a
display-only view-model. The commodity builder attaches that object only to Gold; a dedicated
Jinja partial renders it using existing design tokens and a dependency-free SVG chart.

Spec: docs/superpowers/specs/2026-09-18-china-gold-premium-monitor-design.md

## Global constraints

- **Initial UI/engine slice only:** no scraping or new provider collector. This clause is
  superseded for the approved source-integration continuation by the amendment below.
- Every configured source leg must explicitly set entitled: true.
- Canonical and intraday methodologies never splice.
- Display-only context: no score, rank, gate, size, Prophet, portfolio, or conviction input.
- No new token root, runtime stylesheet injection, or Plotly dependency.
- Dark/light and EN/ZH parity. The Gold feature itself must fit 390px and add zero
  horizontal document-width regression versus its exact parent; any independently owned
  pre-existing whole-page overflow remains with its incumbent repair lane.
- Existing commodity numeric policy remains unchanged.

## Task 1 — Pure premium engine

Files: create engine/china_gold_premium.py and tests/test_china_gold_premium.py.

- Write failing math/alignment/rights tests.
- Run focused tests and verify RED for missing module/API.
- Implement only pure calculations and the fail-closed config/store reader.
- Re-run focused tests to GREEN.
- Refactor only while focused tests remain green.

## Task 2 — Gold-only builder wiring

Files: modify scripts/build_commodities.py and tests/test_china_gold_premium.py.

- Write failing test that Gold receives the object and other commodities do not.
- Verify RED.
- Add the smallest additive builder hook.
- Verify GREEN plus existing commodity truth/MTF tests.

## Task 3 — Product panel

Files: create templates/_china_gold_premium.html.j2, modify templates/commodities.html.j2,
and extend tests/test_china_gold_premium.py.

- Write failing template-render tests for available/unavailable states, EN/ZH content,
  controls, and no raw internal slug leakage.
- Verify RED.
- Implement partial plus existing-token CSS and dependency-free SVG/range/mode behavior.
- Verify GREEN and existing commodity template tests.

## Task 4 — Visual and release proof

- Opt the worktree into required site/mockups paths before rendering.
- Render available and unavailable fixture states.
- Capture dark/light × EN/ZH × desktop/mobile.
- Run design-system, visual-evidence, runtime-style and relevant pytest gates.
- Commit/push/open PR, own CI through conclusion, merge when lawful, then verify the served Gold panel.

## Approved source-integration continuation — Slice B

After the initial provider-neutral UI/engine slice was proven, the Chairman-approved
continuation extended the same product outcome through the real source path rather than
leaving the monitor permanently dark.

This amendment supersedes only the initial-slice prohibition on adding a provider collector.
It does **not** supersede the one-store/one-scheduler law, source-rights gate, display-only
authority, or canonical/indicative separation.

Slice B therefore adds exactly one bounded collector, `gold_china_basis`, which:

- reuses the existing Tushare client/credential and the existing Massive/Polygon credential;
- writes raw source legs into the existing `lib.store` time-series plane under
  `gold_china_basis/` (no second store or publication plane);
- runs in the existing authoritative nightly collector lane (no new scheduler);
- fetches SGE Au99.99 trade-date close and close-aligned global XAU/CNY only;
- cold-starts with 90 calendar days (enough depth for honest 30-session statistics in normal
  trading calendars), then refreshes a bounded 14-day overlap nightly; Massive history is
  requested newest-first so an older-history access/network failure cannot black out the current
  close-aligned point, while the collector continues retrying cold-start depth until at least 30
  persisted dates overlap across both raw legs; if either raw leg falls outside the normal
  overlap the next run expands to cover the whole observed gap plus overlap, bounded by the
  370-day full-history horizon; explicit full-history runs remain available for deeper backfill;
- leaves the official SHAUPM/LBMA-AM canonical method untouched and unavailable until its
  own entitled mapping exists;
- treats public delayed SGE/LBMA pages as reference evidence only, never as a commercial feed:
  SGE requires permission/licensed market-data distribution for use/dissemination, and LBMA/IBA
  requires the applicable benchmark usage/data licence for commercial use; canonical activation
  therefore waits for accepted SGE + IBA entitlements and reuses the existing store plane;
- remains display/context-only and cannot rank, size, gate, allocate, or originate trades.

Production proof for this slice is the normal post-merge nightly source accrual followed by
the existing daily commodity builder and served-page browser verification. Pre-merge fixture
evidence proves rendering and fail-closed behavior but is not a live vendor-call receipt.

The same builder also projects a compact display-tier
`gold_context.china_physical_premium` object into the incumbent
`data/commodity/latest.json` machine feed. It carries only current method/state/value,
freshness/as-of and the 5/30-session context statistics plus an explicit
`context_only: true`; it omits source-vendor detail and all conviction/action/ranking fields.
This is a machine projection of the same accepted context, not a new signal or authority plane.

The existing nightly builder band also runs `scripts.audit_china_gold_premium` immediately
after `build_commodities`. The audit independently re-reads the current source stores and
engine view-model, compares method/state/currency/source-asof/premium with machine-readable
attributes on the actual rendered Gold panel, and independently checks the sibling
`data/commodity/latest.json -> gold_context.china_physical_premium` projection against that
same engine truth. A missing or drifted machine projection fails the strict production-path
audit rather than silently degrading proof to page-only. The audit writes
`data/quality/china_gold_premium.json` through the existing quality/commit plane. The receipt
also preserves availability/freshness separately for canonical, intraday, and close-proxy
methods so a live proxy can never be mistaken for official-benchmark coverage. Source
unavailability is an honest green receipt; a source→VM→render mismatch is a visible builder
failure receipt. The same audit runs again in the existing engine-output commit script
after site-wide normalization and immediately before the broad stage, overwriting the same receipt
so production proof binds to the exact HTML tree that will be committed. This receipt is
observability/proof only and creates no new lifecycle or scoring authority.

The exact post-merge acceptance command is:

`python -m scripts.audit_china_gold_premium --strict-render --require-live-ready --require-method close_proxy`

That command exits nonzero unless the Shanghai-close proxy is the selected fresh method, the
rendered panel and machine projection both match the engine, both the 5-session average and
30-session range are honestly available, and the two raw source artifacts are present with bound
Data OS ids, non-zero rows, valid SHA-256s, and proof that each artifact contains the exact
observation timestamp selected by the close-proxy headline. A raw global artifact may legitimately
contain newer unmatched rows during a China-only market closure; that does not invalidate the
selected aligned observation. The normal nightly continues to accept an honest unavailable receipt;
only the explicit acceptance invocation turns source/history/artifact readiness into a completion gate.

The two raw source datasets already have stable Data OS ids declared as `PROPOSED`:
`commodity.gold.sge_au9999.close` and `commodity.gold.xaucny.close_ref`. After the first real
nightly successfully lands and validates both `data/gold_china_basis/*.parquet` files, closeout
promotes those exact rows to `PRODUCED` only when the same receipt proves the machine projection
consistent too. Do **not** promote them before that live effect: the registry's honesty law
requires a produced store to exist on disk today and its accepted consumer projections to agree.

The quality receipt binds that promotion proof to both raw artifacts. For each source role it
records the stable Data OS id, current canonical registry status, repo-relative parquet path,
row count, SHA-256, latest observation timestamp, and whether the selected headline observation
exists in that artifact. `close_proxy_dataos_promotion_ready=true` is impossible unless both SGE
and global artifacts resolve through the registry in `PROPOSED` or `PRODUCED` state, exist,
contain rows, carry valid SHA-256 bindings, contain the selected headline timestamp, the machine
projection is consistent, the close proxy is fresh, and 5-/30-session statistics are ready. Fixture-only proof therefore remains promotion-blocked unless it supplies
explicit artifact bindings.

Closeout uses a bounded source-writer utility rather than an ad-hoc registry edit:

`python -m scripts.promote_china_gold_dataos`

is dry-run only and reports the exact two pending Data OS ids. After the production receipt is
promotion-ready, the source owner may run:

`python -m scripts.promote_china_gold_dataos --apply`

which changes only those two canonical registry rows from `PROPOSED` to `PRODUCED`, verifies the
written statuses, and stops. Before writing it independently re-checks the receipt's fresh close-
proxy method, render/machine agreement, 5-/30-session readiness, selected source timestamp, both
current artifact files and hashes, current canonical registry states, and a receipt no older than
24 hours; the single promotion-ready bit is never trusted by itself and cannot be replayed days
later. It never commits or pushes Git state and refuses missing/duplicate/non-PROPOSED target rows
or an unready/stale receipt.
