# Intraday Options Root Coverage Producer Design

**Operation:** `intraday-options-root-coverage-20260920-sol-001`

**Issue:** `mastermindx-market-intelligence/mastermind-terminal#681`

**Skillpack:** `mastermindx-market-intelligence/Mastermind@bceb5e1593b1dd7e9e34c3bccbceb02e6ccd5a26`

## Outcome

The existing Macro live-flow poller must make its already-fetched root coverage recoverable by Terminal. A quiet covered root must not disappear merely because it is outside the session's top-gross or unusual-flow lists. The producer must publish a truthful catalog of configured roots and stage per-root ticker artifacts for every current-cycle root that returned a source payload and has real accumulated drill data.

This extends the existing `live_flow` plane. It is not a second collector, scheduler, state database, retry owner, root authority, or publication service.

## Current defect

`_resolve_universe()` configures roughly 22 ETF anchors plus 100 names. The two-tier selector polls core roots every cycle and rotates the tail. `run_cycle()` accumulates per-root minute, strike, expiry, contract and gross state. The publication loop nevertheless selects only the top 40 roots by gross premium plus a small pinned list, so Terminal cannot discover or fetch many roots that Macro already covered.

`live_flow.meta/v2` exposes counts but not configured roots, current-cycle scheduling, per-root source success, last successful source receipt, or whether session drill state exists.

## Architecture

### Existing transport and state

Extend `live_flow.meta/v2` with an optional `root_catalog` array. The existing `meta` f-param and R2 object remain the transport. Persist two bounded receipt maps inside the existing session day-state. `root_source_receipts` records the exact UTC observation timestamp of the latest cycle in which at least one source leg returned a payload. `root_ticker_receipts` advances only after `process_batch` succeeds and the root's accumulators are merged. Failed and off-cycle roots retain their prior receipt.

`run_cycle()` adds ordered `roots_with_source_payload_names` and `roots_with_ticker_state_names`. The first is descriptive source evidence; the second proves the root's drill state accepted that source response. Neither is a score.

### Root catalog contract

Each row has this shape:

```json
{
  "root": "AMD",
  "tier": "core",
  "scheduled_this_cycle": true,
  "source_ok_this_cycle": true,
  "last_source_success": "2026-09-20T15:42:00Z",
  "has_session_data": true,
  "activity_rank": 8
}
```

Rules:

- `tier` is `core` for existing `TIER1_ROOTS`, otherwise `rotating`.
- `scheduled_this_cycle` reflects the exact cycle root list.
- `source_ok_this_cycle` reflects `run_cycle()` source-success names.
- `last_source_success` comes from persisted session receipts and is null before first success.
- `has_session_data` is true only when accumulated ticker state has at least one complete numeric minute or strike row with real activity; malformed or default-filled rows do not count.
- `activity_rank` is one-based gross-premium rank for roots with positive session gross; otherwise null.

Ordering is deterministic: active roots by descending gross premium, remaining core roots in configured order, then remaining rotating roots in configured order. Each configured root appears once. Meta also carries `roots_configured`; existing count fields keep their meanings.

### Per-root publication

Top-40 is no longer an availability gate. Stage a ticker artifact for each root that was scheduled in this cycle, appears in `roots_with_ticker_state_names`, and has accumulated minute or strike data. Preserve cycle order and deduplicate. Do not fabricate empty roots. Do not rewrite source-failed or engine-failed roots with a fresh timestamp. Off-cycle artifacts remain at their previous bytes until their bucket runs again.

Each payload uses that root's own `root_ticker_receipts` timestamp, not a timestamp inherited from a different root and not a source receipt whose processing later failed.

### Bounded expansion

Raise `live_flow.top_names` from 100 to 128, matching the existing bounded chain-snapshot tier. Keep `max_concurrent=2`, the current two-tier scheduler, vendor/source, thresholds, and options math unchanged. Additional names enter the rotating tier unless already core.

## Failure behavior

- Missing receipt state degrades to an empty map.
- Malformed prior receipt entries are ignored, not coerced.
- A fully failed cycle retains prior receipts and prior `source_asof`.
- A partial cycle updates a root source receipt only when both call and put legs returned (an empty DataFrame is an honest no-trades response; `None` is failure), and updates its ticker receipt only after engine state merged successfully.
- A configured root may have `last_source_success=null`; that is an honest awaiting-refresh state.
- A root with a receipt but no minute/strike rows remains discoverable but gets no fabricated ticker artifact.
- Catalog metadata never enters scoring, sizing, gating, or trade authority.

## Test strategy

RED-first tests pin receipt updates and retention; deterministic success-name ordering; catalog order, tier, dedupe, null receipt and activity rank; publish selection beyond the old top-40 boundary; exclusion of failures and empty roots; `top_names=128`; and preservation of existing meta-clock and two-tier contracts.

## Proof and non-goals

Implementation lands through one Macro PR. Merge and deployment are separate gates. Production proof requires real `live_flow/meta.json` catalog rows and a matching `live_flow/tickers/{ROOT}.json` for a quiet root with real session data. No new vendor, collector, scheduler, database, queue, retry plane, publication family, signal model, ranker, trade authority, or historical backfill is introduced.
