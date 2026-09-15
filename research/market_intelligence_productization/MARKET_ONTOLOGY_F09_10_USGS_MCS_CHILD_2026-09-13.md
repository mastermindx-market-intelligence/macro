# F09-10 — USGS Mineral Commodity Summaries child (MO-DELTA-029 #1)

Packet W7B_F09_10. Raw layer only. Display-only context. No UI. No issuer join
(the ledger row's issuer-key clause is not engaged).

## R1 selection

Census §6 bullet 1 / §3 row 10 (quoted):

> There is no USGS Mineral Commodity Summaries / National Minerals Information
> Center collector in this repository (`git ls-tree` over `collectors/` for usgs
> / mineral commodity / nmic returned 0 paths). The raw production and reserves
> layer for rare earths, lithium, cobalt and gallium has no in-repo public producer.

That is the first zero-coverage gap that needs no rights decision. EIA uranium
(row 11) is the next child. The commodities-page panel is F09-11.

## Census HS6 is ruled out as a build child

Census §3 rows 1–5 are PUBLIC-BUILDABLE-DARK, not a missing producer.
Already present: `collectors/census_trade.py`, `engine/theme_trade_flows.py`,
`daily.yml` collect_tail steps, `config/dag.yml` collect_census_trade /
build_theme_trade_flows, `config/synapse.yml` neuralweb-theme-trade-flows,
`site/basketdata/trade_flows.json`, Trade Flows workspace (#6852).
Repo secret *name* `CENSUS_API_KEY` is registered (value never read).
`data/trade_flows/` is empty on main — a runtime heal owed to the F09 lane,
out of this child's scope.

## Source receipts (verified live 2026-09-13, keyless)

Parent `5c8c03e4e4b0938824529f7d` listing HTTP 200, 7926 bytes.
2026 item `696a75d5d4be0228872d3bf8` HTTP 200, 27330 bytes, published 2026-02-06.
Files: `MCS2026_T7_Critical_Minerals_Salient.csv` 4721 B HTTP 200;
`MCS2026_Fig3_Major_Import_Sources.csv` 7095 B HTTP 200;
`MCS2026_Commodities_Data.csv` 3189010 B HTTP 200, cp1252.
T7 header includes USGS's own `Leading_source_precent_world`.
2025 `677eaf95d34e760b392c4970` and 2024 `65a6e45fd34e5af967a46749` are
ZIP-per-commodity — named as the backfill child, not ingested here.

## Rights posture (R2)

USGS Mineral Commodity Summaries is a US Government work (public domain,
keyless, no ToS gate). `docs/QUAL_DATA_COMPLIANCE.md` §3 standing rule is
not triggered: an annual government publication released simultaneously to
every reader carries no non-public information. No Change Log entry was
added. This note does not say any source is cleared.

## Still absent

2022–2025 ZIP-per-commodity backfill; EIA uranium marketing (census row 11);
commodities-page panel (F09-11). No live nightly proof until a seat sets
`USGS_MCS_ENABLED=true`.

## PROPOSED — not applied — MO-DELTA-029 cell

next_bounded_child: per-family gap child #1 (USGS MCS raw layer,
rare_earth_critical_min) BUILT_NOT_PROVEN; live proof owed after nightly
with USGS_MCS_ENABLED=true. Issuer-key clause not engaged (no issuer join).
This packet does not edit the F00C ledger CSV.
