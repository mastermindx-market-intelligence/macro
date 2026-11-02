# Onboarding a name into the SNI US/Mag-7 stress set

This tree is an SNI-local **draft contract**. It consumes owner-supplied
closes and caller-supplied opaque identity fields. Stock Identity / Data OS
owns issuer and security identifiers. This draft does not fork Data OS
identity, Company Event/Earnings, FIF, Capital Structure, Stock Identity,
Options, Research Vault, or qledger/Evaluation.

Adding a company is adding one YAML file under `profiles/`. `stress_set.py`
has no per-name branch. Proof of that mechanism, on synthetic data only, is
`tests/test_sni_us_stress_onboarding.py`.

## Exact steps

1. Copy an existing committed profile (any file in `profiles/`, for example
   `profiles/META.yml`) to `profiles/<TICKER>.yml`. The filename stem is the
   key `load_profiles` uses.
2. Edit only profile facts: `issuer_key`, `display_name`, `counters` label /
   `local_code`, `stress_set.sector_etf` when the descriptive grouping
   changes, and the `then_known` entries (`field` / `value` / `valid_from`).
3. Keep every authority flag literal `false` and every identity id `null`
   (`issuer_link` stays the literal `UNRESOLVED`). See below.
4. Set `then_known` dates from a then-known source. `verified: false` until
   a repo source confirms them. Window start before ticker/listing
   `valid_from` makes `stress_table` abstain; that is the correct outcome.
5. Leave `stress_set.py` unchanged. Re-run the onboarding tests:

```
python3 -m pytest tests/test_sni_us_stress.py tests/test_sni_us_stress_onboarding.py -q -p no:cacheprovider
```

The eighth synthetic name in that test is `ZZZQ.yml` dropped into a temp
directory. `load_profiles` → `check_profiles` → `stress_table` accept it
with zero code change.

## Fields that must stay null / false

Authority (`rank_authority`, `gate_authority`, `size_authority`,
`signal_authority`, `escalation_authority`, `trade_authority`): every flag
is literal `false`. The module raises `ValueError` naming the flag when a
caller sets any of them to a value other than `False`. These flags stay
false so the draft cannot feed a ranker, gate, sizer, signal, escalation,
or trade path.

Identity ids (`canonical_issuer_id`, `issuer_id`, `security_id`,
`canonical_security_id`, `instrument_id`, `listing_id`, and aliases `cik`,
`figi`, `isin`, `cusip`, `permid`, `perm_id`, `lei`, `sedol`): value is
`null`. `issuer_link` is `UNRESOLVED` or null. Unknown identity stays
unresolved. Ids are opaque strings owned by Stock Identity / Data OS and
are caller-supplied when they exist; this draft never constructs them.

`observation.data_read` stays `false` in committed profiles. Census records
parquet presence; it does not claim a statistic from file contents.

`cohort_selection` shape matches the committed seven: `hindsight: true`,
`survivorship: true`, `representative_sample: false`,
`transfer_evidence: false`. The module raises when those three constraints
are broken.

## then_known requirements and abstain behaviour

Each `then_known` entry has `field`, `value`, `valid_from`, `valid_to`,
`source`, and `verified`. Fields used by the residual path are `ticker`,
`listing`, and `sector_etf`.

`stress_table` takes dated closes `(date_iso, close)`. The stock window's
earliest date is compared to ticker/listing `valid_from`:

- Earliest stock date **before** ticker or listing `valid_from`: every
  benchmark abstains. Reason string (pinned by
  `test_onb_03_then_known_ticker_after_window_abstains`):
  `TICKER_NOT_THEN_KNOWN`. Numeric residual fields are `None`, `n` is 0.
  A later `valid_from` on the ticker is a then-known miss; the module
  refuses to compute as-if-known.
- Earliest benchmark date **before** that benchmark's `sector_etf`
  `valid_from`: that benchmark abstains with `BENCH_NOT_THEN_KNOWN`.
- Undated closes against a non-null `valid_from`: `UNDATED_THEN_KNOWN_UNCHECKABLE`.

A `valid_from` of `null` does not trigger a then-known violation. Synthetic
onboarding fixtures in the test use ticker `valid_from: "2015-01-02"`
(computes against a 2018-01-02 window) and `valid_from: "2024-06-03"`
(abstains against that same window).

Residuals remain descriptive contemporaneous leftovers. They are never a
causal claim and never a "news impact" claim. An unestimable family
abstains with a named reason; the module does not emit a default 50/50.

## What not to do

- Do not edit `stress_set.py` (or any other module) to special-case a
  ticker. A new name is a new YAML file.
- Do not generate, mint, derive, or guess canonical HK/US issuer or
  security identifiers from a ticker, name, code, or CIK. Leave ids null.
  A profile with `security_id: "SEC:US-XNAS-ZZZQ"` is refused.
- Do not set any authority flag true. A profile with
  `trade_authority: true` is refused.
- Do not run or commit real-data residual statistics on US names before
  the A8 transfer pre-registration is sealed. That would be a forking-path
  contamination of the registered evaluation. This onboarding proof is
  synthetic for that reason.
- Do not write private full text, forecasts, user theses, or credentials
  into a profile. Fixtures stay synthetic.
- Do not treat a residual or stress statistic as news impact (A24) or fill
  an unestimable family with 50/50 (A25).

## What this proves / what it does not

**Proves.** A held-out eighth name onboards by adding one profile YAML.
`stress_set.py` contains no ticker string literal (AAPL, AMZN, GOOGL, META,
MSFT, NVDA, TSLA, SPY, QQQ, or `XL[A-Z]{1,2}`) outside docstrings. The
synthetic `ZZZQ` profile flows through `load_profiles` → `check_profiles`
→ `stress_table` with zero code change and a defined residual summary per
benchmark. A profile whose ticker `valid_from` is after the stock window
start abstains every benchmark with `TICKER_NOT_THEN_KNOWN`. Authority and
identity refusals still bind for an onboarded name. Two runs on the same
synthetic inputs are identical. Acceptance A36/A37 ("generalizes beyond
Alibaba/Tencent without per-name code") is demonstrated as a mechanism.

**Does not prove.** Nothing about any real company, any real market, any
transfer of residual structure from the HK ADR reference names to US/Mag-7
names, or any forecast skill. Committed profiles still have
`data_read: false`. Real-data residual statistics on US names wait until
the A8 transfer pre-registration is sealed. Cohort membership is
hindsight-selected and survivorship-biased; it is a method stress test.
This draft is not a product surface, registration, or seal.
