# Sector Intelligence Freshness Recovery Design

**Date:** 2026-09-16
**Owner:** Sol
**Repository:** `mastermindx-market-intelligence/macro`
**Skillpack:** `mastermindx-market-intelligence/Mastermind@0fe8074ff953b2ced9025ed40f0f66019c759967`

## Outcome

The authenticated US Sector Intelligence overview must publish the latest usable completed-session read independently of unrelated engine-tail failures. Its headline, action board, basket/theme payload, sector payload, and disclosed `as_of` dates must describe one coherent generation. A fresh file timestamp or successful unrelated workflow is never accepted as freshness proof.

## User and machine jobs

The user job is to open Sector Intelligence and see a truthful, current answer about leadership, rotation, and what to act on now. The machine job is to rebuild the exact existing Sector Intelligence producers in dependency order, validate semantic session dates, and publish only a coherent output set.

## Verified failure

The current public page is still the 2026-09-14 bake. On current `main`, `site/basketdata/baskets.json` and its `theme_intel` remain at 2026-09-11, `site/basketdata/action_board.json` has no freshness stamp, while `site/sectordata/sector_central.json` is already at 2026-09-14. The overview therefore combines multiple generations.

The broad nightly reaches `build_sector_central` only after a large regional/options tail. Runner loss, cancellation, or an unrelated global render guard can prevent the Sector Intelligence commit even when its required inputs and builders succeeded. In addition, the broad engine currently writes the action board before the thematic-basket producer refreshes, so a successful run can still emit a one-generation-old board.
## Architecture

Add one independent, idempotent Sector Intelligence publication lane. It extends the existing producers; it does not create a second scoring, state, event, retry, or publication authority.

The lane runs the current canonical builders in strict order:

1. `scripts.build_baskets` refreshes the thematic basket and `theme_intel` payload.
2. A focused action-board builder reuses the existing functions in `scripts.build_site` to compute sector timing and the unified action board from that just-refreshed basket generation.
3. `scripts.build_sector_central` renders the overview and its current sector payload.
4. A hard semantic validator proves freshness and generation agreement before any commit.

The action-board artifact becomes self-describing with additive top-level metadata:

```json
{
  "schema": "sector_intelligence_action_board.v1",
  "as_of": "YYYY-MM-DD",
  "generated_utc": "RFC3339",
  "baskets_sha256": "hex digest of the exact baskets.json bytes",
  "action_board": {"...": "existing unchanged consumer shape"}
}
```

Existing readers continue to consume `action_board`; the added metadata supplies monitoring and cross-generation proof.

## Freshness and consistency contract

The following artifacts must carry parseable dates and agree exactly:

- `site/basketdata/baskets.json:as_of`
- `site/basketdata/baskets.json:theme_intel.as_of`
- `site/basketdata/action_board.json:as_of`
- `site/sectordata/sector_central.json:as_of`
- `site/premiumdata/sector_central.json:as_of`
- `site/sector_central.html:data-si-as-of`

The exact source generation is also bound across the publication pair. The action-board payload records `baskets_sha256`; the premium payload and public HTML record both `baskets_sha256` and `action_board_sha256`. The validator recomputes the hashes from the exact bytes and refuses any mixed-generation composition.

The common date may trail `lib.nyse_calendar.expected_last_session()` by at most one completed NYSE session. That one-session budget preserves the existing post-close/nightly timing contract; two sessions behind is a positive stale failure.

`engine.sector_cycles` is part of this date contract because Sector Central takes its sector-payload date from that engine. Its input panel is a calendar union and can carry an all-null future/placeholder row after the last observed market close. The effective sector-cycle session is therefore the last row with an observed close for the configured relative-strength benchmark, not the raw index tail. Rows after that session are clipped before any sector/basket cycle record is built. If the benchmark has no observation at all, the engine returns no data: broad legacy render lanes preserve their last-good output, while the independent Sector Intelligence lane fails closed and publishes nothing.

The validator fails closed on an absent artifact, malformed JSON, missing date, empty action board, source-hash mismatch, cross-artifact vintage split, or excessive session lag. It reports the exact offending artifact and observed dates. It never rewrites freshness metadata to conceal stale inputs.
## Workflow and publication

Create `.github/workflows/sector-intelligence.yml` with three entry paths:

- push-triggered self-heal when canonical price, regime, basket, builder, template, or Sector Intelligence output paths change;
- scheduled reconciliation several times on trading days so a missed push or runner outage cannot leave the surface frozen indefinitely;
- manual dispatch for recovery and proof.

The workflow uses its own concurrency group and does not share cancellation fate with `daily`, `render`, or `engine-render`. Scheduled passes perform a cheap semantic preflight and skip the expensive build when the output is already coherent and within budget. Push and manual runs execute the build directly.

Only the approved Sector Intelligence output set is staged. Publishing uses the repository's existing authenticated main-branch and push-retry contracts; it does not introduce a second deploy channel. A failed validator or push leaves the prior committed generation intact and the workflow red.

## Monitoring

Extend the existing GitHub-hosted `nightly-liveness` watchdog rather than creating a new monitoring service. Register the basket payload, action-board payload, and sector payload as NYSE-governed boards, add them to the sparse checkout, and fail on either semantic staleness or a vintage split among the three.

This closes the re-stamp trap: a fresh commit time with an old `as_of` remains red. The independent watchdog continues to run outside the self-hosted pool, so a runner outage cannot silence both subject and alarm.

## Failure behavior

- Missing or unreadable source: no publication; exact error.
- Fresh source but one builder fails: validator blocks the mixed generation.
- Main advances on unrelated paths during publish: reuse the existing exact-path replay and retry policy.
- Main changes one approved output concurrently: fail/retry rather than silently combining generations.
- One-session source lag: publish with the disclosed date.
- More than one completed session of lag: refuse and alert; do not launder the stale source with a new build timestamp.

## Tests

Tests must first reproduce the current defects: unstamped action board, 2026-09-11/2026-09-14 vintage split, stale-but-recent artifacts, missing sparse-checkout coverage, and a workflow that omits strict builder order. Implementation follows only after those tests fail for the expected reasons.
## Acceptance and production proof

The change is accepted only when all of the following are true:

1. Focused tests pass and demonstrate the old failure before the implementation.
2. The targeted builder produces one date across every semantic field, matching source hashes, and a non-empty action board.
3. The independent workflow can publish without waiting for the broad engine tail or global all-site guards.
4. `nightly-liveness` fails on a synthetic stale or split Sector Intelligence generation and stays green on a coherent one-session-lag generation.
5. The PR is merged with current-base CI and review complete.
6. A real workflow run publishes the targeted files to `main`.
7. The deployed `sector_central.html` advances its HTTP generation, and the served authenticated data path displays the validated common `as_of` date.

Until step 7, the truthful state is `BUILT_NOT_PROVEN`, not `PROVEN_LIVE`.

## Non-goals

- No new sector/theme scorer, signal authority, event store, retry database, or alternative deploy channel.
- No redesign of the Sector Intelligence UI.
- No change to the one-session freshness budget used for other NYSE boards.
- No broad refactor of `scripts/build_site.py` while the Prophet source-bound PRs are open.
- No attempt to make stale upstream prices look current.

## Collision and integration boundary

Open Prophet PRs currently touch `daily.yml`, `render.yml`, `engine-render.yml`, and `scripts/build_site.py`. This change therefore avoids modifying those files. It adds an independent workflow and focused builder. Shared edits are limited to the existing liveness watchdog and the bounded `engine.sector_cycles` completed-session anchor required to make Sector Central's own date obey the same generation contract; the broad sector-cycle builder retains its last-good fail-soft behavior when no benchmark session exists. If current main changes any owned path before release, reconcile on exact blobs and rerun focused proof rather than force-merging.
