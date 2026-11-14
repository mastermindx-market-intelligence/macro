# X press-wire historical replay defect — 2026-11-14 UTC

## Evidence

Read-only replay of committed `mastermindx-market-intelligence/macro` source
`9b3759e`, folding the last `data/marketing/outbox/status_ledger.jsonl`
transition per item and joining 6,515 distinct outbox IDs. `posted` below is
the publisher's Buffer acceptance/booking status, **not** confirmed visibility
on X.

- Among 2,457 Buffer-booked items, two groups have exact duplicated body copy
  across different dates, amounting to three extra copies.
- The BEA GDP-by-state Q3 2025 item with stable
  `feed_item_id=b49d9ff66b5ee5d9325b993583d057c315915974` appeared as
  `posted` on **2026-08-26**, **2026-09-24**, and **2026-10-29**.
- Another BEA item with stable
  `feed_item_id=e862a07deccd90aab1daad054241c89379934aa5` appeared on
  **2026-08-26** and **2026-09-24**. Its source URL was an official
  `https://www.bea.gov/news/2024/…` release about 2021–2022 GDP, while its
  post began `Now crossing.` in 2026. The source's `ingested_at` was freshly
  stamped each time; the outbox did not retain the source `published_at`.
- The press `seen_ids` ring is intentionally bounded and eventually evicts old
  IDs. The canonical outbox's near-text repeat horizon is only seven days.
  Neither prevents the same unchanged source ID reappearing weeks later.

## Source repair

The existing press tick now consults its **canonical** outbox + host spool for
prior non-dead press `source.feed_item_id` values, once per tick before scoring
or media/model spend. An item with that ID already queued on an earlier date
is counted as `historical_feed_replay`. A quarantined, failed or recalled item
does not own the source ID, so it can be corrected. Same-day fanout continues
under the existing story and similarity budgets; no new ledger or retry plane
is added. Meaningful article revisions need a distinct source feed identity.

It also holds sources whose explicitly supplied `published_at` is more than
`wire.max_source_age_hours` (default 168) behind the current clock, under
`stale_source_timestamp`. An official BEA `/news/YYYY/` release from at least
two calendar years earlier is held as `stale_official_archive_url`, even if an
RSS adapter substituted ingest time for missing `pubDate`. The latter is
deliberately BEA-only: arbitrary paths containing a year are **not** evidence
of a source publication date.

## Remaining safety and editorial work

- The generic `breaking_feed._parse_pub_date` still substitutes ingestion
  time for missing/unparseable pubDate. This repair does not claim to prove
  freshness of such items outside the recognizable official BEA archive path.
  A separately reviewed producer contract should persist both source-clock
  value and its provenance (`parsed` / `missing` / `fallback`) before other
  providers can be moved to a universal fail-closed freshness policy.
- A concurrent worker might enqueue a feed ID after the press tick's preflight
  but before its final enqueue. The canonical outbox still owns authoritative
  idempotency; a publisher-time source-ID fence should be assessed after the
  in-flight outbox quality-gate PR settles, not duplicated here.
- Some other booked wire copy is still formulaic: 170 of the 2,457 sampled
  posts contain `on the tape`. The house wire opener pools intentionally supply
  that phrase. Redesigning the whole pool needs its own corpus review and
  near-duplicate/attribution tests so removing an opener does not break source
  credit or time claims.

## Verification boundary

Offline regression tests use a temporary outbox, assert stable source identity
and dead-state semantics, and exercise the actual `run_press_tick` with model
and publishing disabled. No historical items were edited, recalled or resent.
Merge, deploy and fresh producer/X evidence are separate acceptance steps.
