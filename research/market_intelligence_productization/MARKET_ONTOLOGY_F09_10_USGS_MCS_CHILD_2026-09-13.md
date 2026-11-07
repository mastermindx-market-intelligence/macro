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

## Heal h_7110 (2026-09-18) — historical, not current head

Round-1 (on `196002786fb2561597068021137d579a83179ac3`) led reads with
the T7 leading producer, sorted named-country Fig3 rows by (-pct, name)
excluding Other/其他, and expanded NIR `>` / `<` so customer text has
no raw angle-bracket tokens. Gallium EN uses "produced". Round-2 head
`67f90b545d6ca2af9c9880456ab224e151286771` closed nested "about more than"
NIR wording and gallium verb_zh (produced → 生产了). ZH country names
were still USGS English in those rounds; they are not quoted here because
they are not the current reads.

RED-first on f1aac58fedd1: at that commit the files `collectors/usgs_mcs.py`,
`engine/critical_minerals_supply.py`, and `config/usgs_mcs_sources.yml` were
absent (`git cat-file -t` fatal); isolated replay with empty PYTHONPATH gave
16 failed, 2 passed. The body claim of "18 passed on f1aac58fedd1" was wrong.

## Heal h_7110 round 3 (2026-09-19) — historical, not current head

PR head after round 3, from `gh pr view 7110 --json headRefOid`, was
`8043e187f092e127ea89f66943fb4f4620cabf84` (code `3f515003cc37c9b0a656a389ba2848c749df1f28`
plus the research-doc commit). ZH reads use Chinese country names via
`COUNTRY_ZH` / `_country_zh()`. NIR `_nir_text(25, '<', 'zh')` returns 少于
not 低于. Stitch keeps "US". Independent review h_7110_rv3 at that head
was FIX_REQUIRED: the Files-changed banner was stale, there was no stitch
test, no `_nir_text` `<` pin, and the rare-earths top-3 test re-sorted
inside the test (file-order China/Malaysia/Japan sums to the same 89).

## Heal h_7110 round 4 (2026-09-19, Grok)

Closes h_7110_rv3 (1 MAJOR, 3 minors) on top of
`8043e187f092e127ea89f66943fb4f4620cabf84`. The PR body records the tip
40-hex from `gh pr view 7110 --json headRefOid` after push (head-sha law).
A committed file cannot contain its own commit SHA; this section names
the reviewed head and the measured sentences, not a guessed tip.

MAJOR 1 (truth): Files-changed is the real `git diff --stat origin/main...HEAD`
and the real `gh pr view --json files` list. No "this heal commit only"
figure. This file no longer quotes mixed-language ZH
(`Congo (Kinshasa)在…` / `Australia在…` / `China在…`) as current reads
and no longer presents `4db6b1e5bd717f817660f839deb621df0dc6c0a4` or
`3f515003cc37c9b0a656a389ba2848c749df1f28` as the PR head.

MINOR 1 (stitch test): `_read_sentences` with missing-NIR text pins
`Congo (Kinshasa) mined about 74% of the world's cobalt in 2025, and US net import reliance is not given as a number in this edition.`

MINOR 2 (`<` pin): `_nir_text(25, '<', 'zh')` == `美国进口了其用量的少于25%。`
and EN `The United States imported less than 25 percent of what it used.`

MINOR 3 (discriminator): the artifact stores `top3_import_sources` beside
`top3_import_share_pct`. The test asserts the engine-selected triple
`[("China", 71.0), ("Malaysia", 13.0), ("Estonia", 5.0)]` and does not
re-sort `import_sources_2021_24` inside the test. Error strings name that
tuple. RED at `67f90b545d6ca2af9c9880456ab224e151286771` (no `top3_import_sources` key).

Corrected reads (measured; EN/ZH include `about`/`约`/`percent` as emitted):

- cobalt: EN: "Congo (Kinshasa) mined about 74% of the world's cobalt in 2025,
  and the US imported about 79 percent of what it used."
  ZH: "刚果（金）在2025年开采了全球约74%的钴，美国进口了其用量的约79%。"
  top3_import_share_pct = 56
- lithium: EN: "Australia mined about 32% of the world's lithium in 2025,
  and the US imported more than 50 percent of what it used."
  ZH: "澳大利亚在2025年开采了全球约32%的锂，美国进口了其用量的超过50%。"
  top3_import_share_pct = 97
- gallium: EN: "China produced about 100% of the world's gallium in 2025,
  and the US imported about 100 percent of what it used."
  ZH: "中国在2025年生产了全球约100%的镓，美国进口了其用量的约100%。"
  top3_import_share_pct = 68
- rare earths: EN: "China mined about 69% of the world's rare earths in 2025,
  and the US imported about 67 percent of what it used."
  ZH: "中国在2025年开采了全球约69%的稀土，美国进口了其用量的约67%。"
  top3_import_share_pct = 89
  top3_import_sources = [("China", 71.0), ("Malaysia", 13.0), ("Estonia", 5.0)]
