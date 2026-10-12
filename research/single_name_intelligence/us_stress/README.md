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

## What this is not

- Not a product surface, registration, or seal.
- Not a signal, rank, gate, size, escalation, or trade path. Every authority
  flag in every profile is `false`; the module raises if a caller sets any of
  them true.
- Not a forecast and not a 50/50 default.
- Not identity minting. `canonical_issuer_id` is null; `security_id` is null;
  `issuer_link` is `UNRESOLVED`. Stock Identity / Data OS owns those ids.
  Unknown identity stays unresolved. This draft does not construct HK/US
  issuer or security identifiers from a ticker, name, code, or CIK.
- Not a then-known view of later facts. Residual windows end at `t-1`
  (strictly before `t`).
- Parquet contents were not read when writing these drafts (`data_read:
  false`). No committed file claims numbers from real market data.

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
