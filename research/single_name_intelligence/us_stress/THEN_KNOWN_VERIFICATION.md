# then_known verification (US/Mag-7 stress set)

SNI-local draft census. Consumes owner-supplied identity and listing facts;
this file does not mint identifiers, does not flip any authority flag, and
does not feed a ranker, gate, sizer, signal, escalation, or trade path.

Base commit: `040b61c32fc7` (`claude/sni-int1-20261013`).

## Method

1. Read the seven coverage profiles' `then_known` blocks (28 entries).
2. Read `stress_set.py` loaders (`_then_known_entries`, `_valid_from_of`,
   `_ticker_then_known_violation`, `_bench_then_known_violation`,
   `check_profile`) to confirm accepted fields: `ticker`, `listing`,
   `share_class`, `sector_etf`, plus `value` / `valid_from` / `valid_to` /
   `source` / `verified`. Extra keys are tolerated by the loader.
3. Read `data/reference/security_master.parquet` schema and the rows whose
   `inception_code` is AAPL, AMZN, GOOG, GOOGL, META, MSFT, NVDA, TSLA.
4. Ran the bounded ticker-rename grep once (capped at 60 hits) and read
   eight of those hit files, relevant lines only.
5. Applied the evidence rules below. Flip `verified: true` only when a
   committed repo source states the value (or a fact from which it follows
   by plain reading). Otherwise keep `verified: false` and record why.

No Yahoo first-date was used as proof of `valid_from`. No internet source
and no training-memory date was used as evidence.

## Evidence rules

- Yahoo price files (`data/yahoo/*.parquet`) cannot verify a ticker's
  `valid_from`: Yahoo backfills a renamed ticker's whole history under the
  new symbol (the mission states META's Yahoo history starts in 2012, not
  2022). A Yahoo first date is never proof of `valid_from`.
- A value is VERIFIED only if a committed file states it, or states a fact
  from which it follows by plain reading (example: a rename record
  `FB->META` effective `2022-06-09`). Evidence form:
  `<path>@<12-char blob or commit sha>:<line or column=value>`.
- If a repo source contradicts a profile value, the value is left unchanged
  (`verified: false`) and a `contradiction:` pointer is added. Changing a
  value is a seat decision.
- Memory / commonly known market facts may appear in the notes column
  labeled **not evidence**. They do not verify.
- Identity ids (`security_id`, `canonical_issuer_id`) stay null. Stock
  Identity / Data OS owns them.

## Contradictions

None. `security_master.effective_at` is `2023-05-09` for all seven Mag-7
rows, which would disagree with IPO / rename / class-split dates if it were
a listing date. It is not: `config/dataset_registry.yml@6c254ca1d916:341-344`
states `effective_at` is not a listing date and that no in-repo US
listing-date source exists. That is a verification gap, not a value
contradiction. Absence of an `FB` row is not a contradiction of
`META` / `2022-06-09`.

## Census (what the allowed sources actually contain)

`data/reference/security_master.parquet@85ef75104840` columns:

`security_id`, `issuer_id`, `issuer_state`, `issuer_cik`,
`issuer_evidence_snapshot`, `listing_key`, `country`, `mic`,
`inception_code`, `effective_at`, `ingested_at`, `security_state`,
`superseded_by`.

No `ticker`, `valid_from`, `valid_to`, `share_class`, listing-date, or
rename-from/to columns. No `FB` row. No SPY / QQQ / XLK / XLY / XLC rows.
All seven Mag-7 names (plus GOOG) have `mic=XNAS`, `effective_at=2023-05-09`,
`issuer_state=RESOLVED`. GOOGL and GOOG share `issuer_id=ISS:US-XNAS-GOOG`.
`listing_key` is documented as inception code, never today's symbol
(`config/dataset_registry.yml@6c254ca1d916:311`).

`config/dataset_registry.yml@6c254ca1d916:341-344`: `effective_at` is not a
listing date; **no in-repo US listing-date source exists**; back-dating from
a store's earliest bar would be fabrication.

`config/identity_seams.yml@040b61c32fc7:74-79`: issuer correction is
current-identity only — no historical issuer lineage.

Bounded grep (`HEAD -- config engine lib data/reference scripts`, first 60
hits): no `FB`/`META` rename record, no `ticker_change` / `symbol_change` /
`rename_map` hit that states a Mag-7 `valid_from`. Hits used:

- `config/dataset_registry.yml:286` GOOG/GOOGL share `ISS:US-XNAS-GOOG`
- `config/dataset_registry.yml:341-344` no in-repo US listing-date source
- `config/identity_seams.yml:74-79` current-identity only
- `config/identity_seams.yml:301` GOOG and GOOGL are two distinct securities
- `config/issuer_group_allowlist.yml:41` members `US-XNAS-GOOG`, `US-XNAS-GOOGL`
- `engine/ledger_identity.py:98` GOOG/GOOGL are two share classes (no date,
  no "Class A")
- `config/delisted_symbols.yml:4-8` rename half lives in `config.yml`
  ticker_fixups / aliases (not a Mag-7 dated record in the 60-hit window)
- `data/reference/_receipt.json:142-146` GOOG/GOOGL issuer group, no dates
- `data/reference/_receipt.json:601` example of how a rename *is* recorded
  when known (`SATS->ECHO` on `2026-06-24`); Mag-7 has no analogous row

## Per-entry table

Verdict: **UNVERIFIABLE-FROM-REPO** for every row. Count: **0 verified / 28 total**.

| profile | field | value | valid_from | verdict | evidence/reason | note |
|---|---|---|---|---|---|---|
| AAPL | ticker | AAPL | null | UNVERIFIABLE-FROM-REPO | security_master is current-identity only (no ticker-history/valid_from columns) | commonly known continuous AAPL tape: **not evidence** |
| AAPL | listing | NASDAQ | null | UNVERIFIABLE-FROM-REPO | same; `mic=XNAS` is current venue, not a dated listing fact; XNAS→"NASDAQ" is not stated in census files | |
| AAPL | share_class | common | null | UNVERIFIABLE-FROM-REPO | security_master has no share_class column | |
| AAPL | sector_etf | XLK | 1998-12-22 | UNVERIFIABLE-FROM-REPO | XLK not in security_master; no ETF inception record in census | commonly known XLK inception: **not evidence** |
| AMZN | ticker | AMZN | null | UNVERIFIABLE-FROM-REPO | security_master is current-identity only (no ticker-history/valid_from columns) | |
| AMZN | listing | NASDAQ | null | UNVERIFIABLE-FROM-REPO | same as AAPL listing | |
| AMZN | share_class | common | null | UNVERIFIABLE-FROM-REPO | security_master has no share_class column | |
| AMZN | sector_etf | XLY | 1998-12-22 | UNVERIFIABLE-FROM-REPO | XLY not in security_master; no ETF inception record in census | commonly known XLY inception: **not evidence** |
| GOOGL | ticker | GOOGL | 2014-04-03 | UNVERIFIABLE-FROM-REPO | no rename/ticker-history record stating 2014-04-03; Yahoo backfill cannot prove valid_from | commonly known GOOG/GOOGL class split: **not evidence** |
| GOOGL | share_class | Class A | 2014-04-03 | UNVERIFIABLE-FROM-REPO | master mints GOOG and GOOGL as two listings; does not state "Class A" or 2014-04-03 | two-class fact without class letter: **not evidence** of Class A |
| GOOGL | listing | NASDAQ | null | UNVERIFIABLE-FROM-REPO | security_master is current-identity only (no ticker-history/valid_from columns) | |
| GOOGL | sector_etf | XLC | 2018-06-19 | UNVERIFIABLE-FROM-REPO | XLC not in security_master; no ETF inception record in census | commonly known XLC inception: **not evidence** |
| META | ticker | META | 2022-06-09 | UNVERIFIABLE-FROM-REPO | no FB→META rename record in security_master or bounded grep; Yahoo backfill cannot prove valid_from | commonly known FB→META on 2022-06-09: **not evidence** |
| META | listing | NASDAQ | 2012-05-18 | UNVERIFIABLE-FROM-REPO | dataset_registry.yml: no in-repo US listing-date source; Yahoo first-date is not proof | commonly known IPO date: **not evidence** |
| META | share_class | Class A | 2012-05-18 | UNVERIFIABLE-FROM-REPO | security_master has no share_class or listing-date columns | |
| META | sector_etf | XLC | 2018-06-19 | UNVERIFIABLE-FROM-REPO | XLC not in security_master; no ETF inception record in census | commonly known XLC inception: **not evidence** |
| MSFT | ticker | MSFT | null | UNVERIFIABLE-FROM-REPO | security_master is current-identity only (no ticker-history/valid_from columns) | |
| MSFT | listing | NASDAQ | null | UNVERIFIABLE-FROM-REPO | same as AAPL listing | |
| MSFT | share_class | common | null | UNVERIFIABLE-FROM-REPO | security_master has no share_class column | |
| MSFT | sector_etf | XLK | 1998-12-22 | UNVERIFIABLE-FROM-REPO | XLK not in security_master; no ETF inception record in census | commonly known XLK inception: **not evidence** |
| NVDA | ticker | NVDA | null | UNVERIFIABLE-FROM-REPO | security_master is current-identity only (no ticker-history/valid_from columns) | |
| NVDA | listing | NASDAQ | null | UNVERIFIABLE-FROM-REPO | same as AAPL listing | |
| NVDA | share_class | common | null | UNVERIFIABLE-FROM-REPO | security_master has no share_class column | |
| NVDA | sector_etf | XLK | 1998-12-22 | UNVERIFIABLE-FROM-REPO | XLK not in security_master; no ETF inception record in census | commonly known XLK inception: **not evidence** |
| TSLA | ticker | TSLA | null | UNVERIFIABLE-FROM-REPO | security_master is current-identity only (no ticker-history/valid_from columns) | |
| TSLA | listing | NASDAQ | 2010-06-29 | UNVERIFIABLE-FROM-REPO | dataset_registry.yml: no in-repo US listing-date source; Yahoo first-date is not proof | commonly known IPO date: **not evidence** |
| TSLA | share_class | common | null | UNVERIFIABLE-FROM-REPO | security_master has no share_class column | |
| TSLA | sector_etf | XLY | 1998-12-22 | UNVERIFIABLE-FROM-REPO | XLY not in security_master; no ETF inception record in census | commonly known XLY inception: **not evidence** |

## Source that would verify the rest

Request to **Stock Identity / Data OS** (this lane does not build it):

A dated ticker-history / listing-history record per security, owned and
sealed by Stock Identity, with at least:

- opaque `security_id` / `canonical_issuer_id` (caller-supplied; never
  constructed here)
- `ticker` string, `valid_from`, `valid_to` (null open-ended)
- predecessor ticker when a rename occurred (example shape: `FB -> META`
  effective `2022-06-09`)
- listing venue as of `valid_from` (not a current-only MIC snapshot)
- share-class label as of `valid_from` (Class A vs common), without
  collapsing GOOG/GOOGL
- sector-ETF membership / inception `valid_from` for XLK, XLY, XLC if
  those labels are to constrain stress windows

Until that owner-supplied history exists in-repo, every Mag-7 `then_known`
date stays `verified: false`. An honest 0-verified census is the correct
fail-closed outcome: an unverified date must not be treated as a then-known
fact.
