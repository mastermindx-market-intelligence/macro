# SNI US/Mag-7 science stress set

Descriptive-only science harness for SNI acceptance **A36** (US/Mag-7 packs
need no ticker-specific branches) and **A37** (a held-out company onboards via
config). Seven coverage-profile drafts plus a contemporaneous-residual module
with trailing historical-volatility normalization. Statistics are descriptive.
They are not causal and they are not "news impact".

This tree is an SNI-local **draft contract**. It consumes owner-supplied
closes and caller-supplied opaque identity fields. It does not fork or
re-implement Data OS identity, Company Event/Earnings, FIF, Capital Structure,
Stock Identity, Options, Research Vault, or qledger/Evaluation.

## Cohort selection

Membership is the seven largest US-listed companies by market capitalisation as of 2026-10-12; selected with hindsight; survivorship-biased; not a sample of US large caps; results are a method stress test (does the pipeline run without a ticker branch) and are never evidence that a residual transfers to US names.

## What this is not

- Not a product surface, registration, or seal.
- Not a signal, rank, gate, size, escalation, or trade path. Every authority
  flag in every profile is `false`; the module raises if a caller sets any of
  them to a value other than literal `False` (`value is False`).
- Not a forecast and not a 50/50 default.
- Not identity minting. Identity ids (`canonical_issuer_id`, `issuer_id`,
  `security_id`, `canonical_security_id`, `instrument_id`, `listing_id`, and
  aliases `cik`, `figi`, `isin`, `cusip`, `permid`, `perm_id`, `lei`, `sedol`)
  are refused at any depth unless the value is null. `issuer_link` is the
  literal `UNRESOLVED` (or null). Stock Identity / Data OS owns those ids.
  Unknown identity stays unresolved. This draft does not construct HK/US
  issuer or security identifiers from a ticker, name, code, or CIK.
- Not a then-known view of later facts. Residual windows end at `t-1`
  (strictly before `t`). Profile `then_known` entries record when a ticker,
  share class, listing, or sector ETF label was valid; a window that starts
  before that date abstains (`TICKER_NOT_THEN_KNOWN` or `BENCH_NOT_THEN_KNOWN`).
- Parquet contents were not read when writing these drafts (`data_read:
  false`). No committed file claims numbers from real market data.

## Date alignment and gap abstention

Closes are ordered `(date_iso, close)` pairs. `load_closes_from_parquet`
takes dates from the parquet DatetimeIndex, or from a `date`/`Date` column
when the index is not datetime, and returns `None` when neither exists — it
never fabricates dates. Unsorted or duplicate dates raise `ValueError`.

Returns are computed between consecutive rows of **that** series. Stock and
benchmark return-end dates are compared before beta and residual. Each dated
per-benchmark result records `dropped_stock_dates` and `dropped_bench_dates`
(sorted ISO lists of return-end dates present in one leg and not the other).
When `join_policy` is omitted (`None`) and either dropped list is non-empty,
the numeric summary abstains (`n: 0`, `mean: None`, `stdev: None`,
`reason: DATE_JOIN_MISMATCH`). When `join_policy="inner"`, the legs are
inner-joined on the return's end date and numbers are emitted with
`join_policy: inner` recorded; the dropped lists remain. Any other
`join_policy` value raises `ValueError`. Position truncation (`min(len)` from
the start) is not used; a residual is only defined when both legs are the
same calendar day.

A missing, non-finite, or `<=0` close leaves the date in the series and sets
the returns that touch that date to `None`. The next finite positive close
does not form a bridged multi-day return. `simple_returns`, residuals, and
`_summary` never emit NaN; `_summary` excludes `None` and non-finite values.
Each per-benchmark summary also reports `first_date`, `last_date` (of the
defined normalized residuals) and `n_shared_dates` (inner-join size). The
table records `window`. A summary with `n == 0` always carries a `reason`.

## No-ticker-branch law (A36)

`stress_set.py` contains none of the strings of the seven US names or the HK
ADR reference ticker. The ticker universe is **only** the YAML files in
`profiles/`. Adding a company is adding a profile (A37); the module does not
change.

`tests/test_sni_us_stress.py::test_no_ticker_branch_law` greps the module
source for those strings. `test_held_out_onboarding` drops an eighth synthetic
profile into a temp directory and runs `stress_table` with no code change.

## How to run

From the repository root (tests use synthetic series only, `random.Random(7)`):

```
python3 -m pytest tests/test_sni_us_stress.py -q -p no:cacheprovider
```

Optional CLI. Write output **outside** the repo (or to a gitignored path).
Do not commit reports produced from real data. Do not create `runs/` or
`data/` artifacts from this harness.

```
python3 research/single_name_intelligence/us_stress/stress_set.py \
  --profiles-dir research/single_name_intelligence/us_stress/profiles \
  --data-dir data/yahoo \
  --out /tmp/sni-us-stress-out
```

If pandas is missing or the parquet files are absent in this checkout, the
CLI writes a report stating `data absent in this checkout; no statistics
computed` and exits 0. It never fabricates closes.

## Profiles

`profiles/<TICKER>.yml` mirror coverage_profile.v1 keys as a stress-set draft
(`schema_version: coverage_profile.v1`, `profile_kind: qualification_facts`).
They are not registered product profiles. Observation census records that
`data/yahoo/<TICKER>.parquet` is present on `origin/main` (git ls-tree) and
that this draft did not read the file.

Sector ETF (descriptive grouping only): XLK for the three hardware/software
names, XLY for the two consumer-discretionary names, XLC for the two
communication names. Benchmarks are SPY and QQQ for every profile.
