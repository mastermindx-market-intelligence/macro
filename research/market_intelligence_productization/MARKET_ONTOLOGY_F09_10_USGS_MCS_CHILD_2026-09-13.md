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

## Heal h_7110 (2026-09-18)

Head `196002786fb2561597068021137d579a83179ac3` → heal head `4db6b1e5bd717f817660f839deb621df0dc6c0a4`.
BLOCKER: `_read_sentences` now leads with the T7 leading producer (Congo
74% cobalt, Australia 32% lithium) and uses China-share clause only as
fallback when no leading-producer is present (or when China IS the leader,
e.g. gallium 100%, rare earths 69%). MAJOR: `top3_import_share_pct`
now sorts named-country Fig3 rows by (-pct, name), excludes "Other"/"其他",
and sums the top 3 — cobalt = 56 (Norway 26 + Finland 16 + Canada 14).
MAJOR: NIR qualifier `>` renders "more than" / "超过", `<` renders
"less than" / "低于" — no raw `<`/`>` tokens in customer text.
MINOR: gallium production verb now uses "produced" (matches
`world_metric: "Primary production"`); stitch keeps leading "US" capitalised.

Corrected reads at heal head `4db6b1e5bd` (round 2 heal):

- cobalt: "Congo (Kinshasa) mined about 74% of the world's cobalt in 2025,
  and the US imported 79% of what it used."
  ZH: "Congo (Kinshasa)在2025年开采了全球约74%的钴，美国进口了其用量的79%。"
  top3_import_share_pct = 56
- lithium: "Australia mined about 32% of the world's lithium in 2025,
  and the US imported more than 50 percent of what it used."
  ZH: "Australia在2025年开采了全球约32%的锂，美国进口了其用量的超过50%。"
  top3_import_share_pct = 97
- gallium: "China produced about 100% of the world's gallium in 2025,
  and the US imported 100% of what it used."
  ZH: "China在2025年生产了全球约100%的镓，美国进口了其用量的100%。"
  top3_import_share_pct = 68
- rare earths: "China mined about 69% of the world's rare earths in 2025,
  and the US imported 67% of what it used."
  ZH: "中国在2025年开采了全球约69%的稀土，美国进口了其用量的67%。"
  top3_import_share_pct = 89

RED-first on f1aac58fedd1: at that commit the files `collectors/usgs_mcs.py`,
`engine/critical_minerals_supply.py`, and `config/usgs_mcs_sources.yml` were
absent (`git cat-file -t` fatal); isolated replay with empty PYTHONPATH gave
16 failed, 2 passed. The body claim of "18 passed on f1aac58fedd1" was wrong.
HEAL_RESULT: tests 22 passed (18 original + 4 new: cobalt/lithium verbatim
read pins, cobalt top3=56, lithium top3=97, no-angle-bracket assertion).
