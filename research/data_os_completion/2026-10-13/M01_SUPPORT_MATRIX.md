# M01 — Prospectively frozen market support matrix (DATA-OS-COMPLETION, lane M01-1)

Base: `2e2943ae49c828feda71dc4f3272f4bf3ac97252`. Evidence class: real committed stores plus synthetic refusal rows.

## Purpose

One frozen record of which market is enrolled, which is identity-only and which is not enrolled, by
session, currency, action family and dataset, so a reader cannot copy a US clock, currency, volume or
adjusted-price assumption onto another market without something refusing. Every row is pinned to the
code by `tests/test_dataos_support_matrix.py` against the existing owners (`lib/dataos/identity.py`,
`lib/dataos/price.py`, `lib/dataos/price_views.py`, `lib/dataos/registry.py`,
`lib/dataos/web_readers.py`) and the committed stores. This record is a verification package: it
changes no owner file.

## Law

- D00.D2 — a storage key (a file stem, a ticker string) is never an identity; identity is the
  normalized listing key.
- D00.D3 — RAW / SADJ / TRADJ are three distinct economic units; TRADJ is unlawful for limit-price
  and exchange-rule work (`DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT` stays binding).
- D00.D6 — consumer A (Terminal OHLC) and consumer B (DataWorkspace `equity.bars.daily.stocks`) are
  US (XNAS, XNYS, ARCX). HK and CN are identity normalization only, with no price-view positive
  witness; the gap is reported as coverage, not hidden. CN limit work stays RAW.
- `research/data_os_completion/2026-10-13/R00_DATASET_MATRIX.md` — the admitted dataset rows; not
  contradicted here.

## Support matrix

| Market | Venues (MIC) | Session clock | Currency | Identity | Price read | Registry dataset | Action families | PIT | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| US | XNAS, XNYS, ARCX | America/New_York | USD | ticker store keys (`data/stocks/{ticker}.parquet`); the store key is never the identity | positive read of `data/stocks`: close-only, TRADJ basis, no `open` column | `equity.bars.daily.stocks` PRODUCED; `terminal.bars.daily.ohlc_json` PROPOSED, its witness owned by U01/U02 | three supported families on SADJ views | false (`point_in_time_corporate_actions: false`) | ENROLLED-POSITIVE, daily bars only |
| HK | XHKG | Asia/Hong_Kong | HKD | `data/hk_connect_roster` rows and `data/hk_stocks` store stems normalize on XHKG | no price-view positive witness — the gap is reported as coverage | no registry contract | none claimed | none claimed | IDENTITY-ONLY |
| CN | XSHG, XSHE | Asia/Shanghai | CNY | `data/china_stocks_raw` store stems normalize to the exchange their suffix names | RAW only, for limit and price-band work | no registry contract | none claimed | none claimed | IDENTITY-ONLY |
| CN-BSE | XBSE | Asia/Shanghai (clock known) | CNY | no `.BJ` symbol normalizes; Beijing listings are not enrolled | none | no registry contract | none | none | NOT-ENROLLED |
| CA | XTSE | America/Toronto | CAD | not enrolled; no price store on disk | none | no registry contract | none | none | NOT-ENROLLED |

## Sessions

Daily bars only. No intraday, auction or extended-hours session is claimed for any market.

## Negative capabilities (M01.02, M01.03)

- `CURRENCY_MISMATCH` — a row `currency` column that disagrees with the venue's declared currency is
  refused (XHKG with USD, XSHE with USD, XNAS with HKD, XSHG with HKD).
- `VENUE_CLOCK_UNKNOWN` — an unenrolled MIC (`XLON`) gets no clock and no declared currency;
  `raw_view` refuses and `venue_timezone` raises `IdentityError`.
- No venue, no default — `mic=None` leaves `view.currency` as `None`; no USD default is ever assumed.
- `NON_RAW_INPUT` — a `close_tradj` tape is refused as RAW on XSHG, XSHE, XHKG and XNAS: a nominal
  exchange-rule or legal-price-band question can never receive a total-return adjusted price.
- `DOUBLE_ADJUST_RISK` — a `close_sadj` tape is refused as RAW on XHKG and XSHG.
- `AMBIGUOUS_BASIS` — a bare `close` column from `data/hk_stocks`, `data/china_stocks_raw` or
  `data/stocks` is refused; a directory name (`_raw`) is not a declared basis.
- A bare `volume` key is never promoted to `volume_raw`.
- A listing symbol never crosses markets: `normalize_hk_symbol("NVDA")`,
  `normalize_cn_symbol("NVDA")`, `normalize_cn_symbol("0700.HK")`,
  `normalize_hk_symbol("600519.SS")`, `normalize_cn_symbol("430047.BJ")` and
  `normalize_cn_symbol("830799.BJ")` all raise `IdentityError`.

## Limitations (M01.04)

- No global PIT claim: the US contract itself declares `point_in_time_corporate_actions: false` with
  an empty `population`; nothing here infers a point-in-time capability from a sample.
- A sample is not the whole market: the observed counts below are a dated observation at the base
  commit, not a population claim; nightly data growth can move them, so the tests use count floors.
- Observed counts, from the worktree at the base (counts only, command run 2026-10-13):
  `~/lanes/venv/bin/python -c "from pathlib import Path; import pyarrow.parquet as pq; roster = pq.read_table('data/hk_connect_roster/roster.parquet', columns=['code5', 'ticker']).to_pylist(); cn = [Path(p.name).stem for p in Path('data/china_stocks_raw').glob('*.parquet')]; print(len(roster), len({r['code5'] for r in roster}), len(list(Path('data/hk_stocks').glob('*.parquet'))), len(cn), sum(s.endswith('.SS') for s in cn), sum(s.endswith('.SZ') for s in cn), len(list(Path('data/canada_stocks').glob('*.parquet'))))"`
  → 796 roster rows, 581 distinct `code5`, 158 HK store stems, 1869 CN store stems (983 `.SS`, 886
  `.SZ`), 0 `.parquet` under `data/canada_stocks` (only `latest.json`).
- No historic identity (renames, delistings) is claimed for HK or CN.
- Six unsupported action families: `merger`, `return_of_capital`, `rights_issue`, `scrip`,
  `spin_off`, `stock_dividend` — typed refusal `UNSUPPORTED_ACTION`, never coerced.
- `volume_sadj` is not policed by `raw_view` (pinned by a strict xfail in the suite): a
  split-adjusted volume can ride a RAW view today. This is a reported limitation, not a capability.

```text
M01-STATUS US ENROLLED-POSITIVE
M01-STATUS HK IDENTITY-ONLY
M01-STATUS CN IDENTITY-ONLY
M01-STATUS CN-BSE NOT-ENROLLED
M01-STATUS CA NOT-ENROLLED
M01-ACTIONS-SUPPORTED cash_dividend forward_split reverse_split
M01-ACTIONS-UNSUPPORTED merger return_of_capital rights_issue scrip spin_off stock_dividend
```

## Acceptance map

| Acceptance | Proven by |
| --- | --- |
| M01.01 | `test_m01_us_registry_row_is_produced_tradj_on_the_new_york_clock`, `test_m01_us_venues_keep_the_registry_clock_and_usd`, `test_m01_us_store_has_a_real_positive_read`, `test_m01_hk_roster_identities_agree_on_xhkg`, `test_m01_hk_store_stems_normalize_to_xhkg`, `test_m01_cn_store_stems_normalize_to_their_exchange`, `test_m01_non_us_venues_keep_their_local_clock_and_currency` |
| M01.02 | `test_m01_non_us_clocks_are_not_the_us_registry_clock`, `test_m01_a_foreign_currency_column_is_refused`, `test_m01_an_unenrolled_venue_has_no_clock`, `test_m01_no_venue_means_no_currency_default`, `test_m01_listing_symbols_do_not_cross_markets`, `test_m01_bare_volume_is_never_promoted_to_raw_volume`, `test_m01_adjusted_volume_is_refused_by_the_raw_view` |
| M01.03 | `test_m01_total_return_tape_is_refused_as_raw`, `test_m01_split_adjusted_tape_is_refused_as_raw`, `test_m01_tradj_is_unlawful_for_exchange_rule_work`, `test_m01_store_columns_without_a_basis_are_ambiguous` |
| M01.04 | `test_m01_us_contract_claims_no_pit_and_no_population`, `test_m01_non_us_stores_have_no_registry_contract`, `test_m01_beijing_listings_are_not_enrolled`, `test_m01_canada_has_no_price_store`, `test_m01_supported_action_families_are_exactly_three`, `test_m01_terminal_view_is_proposed_not_enrolled`, `test_m01_record_matches_the_code` |

## What is NOT built

No calendar, identity, adapter, registry or price-view change; no HK/CN/CA enrolment; no Terminal
witness (U01/U02 own it); no intraday, auction or extended-hours session claim. CI wiring is a
seat-applied patch: the new suite rides the pandas+pyarrow `dataos-identity-seams` job.
