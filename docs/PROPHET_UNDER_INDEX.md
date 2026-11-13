# Prophet under-index daily readout

Definition: **EMITTER_SPEC rev 2 (2026-11-13)**, with the accepted
READER_STATE_RULE formula `ceil(0.75 N)` (9 of 11). Description only;
no forward outcomes or changes to Prophet ranking/scoring.

## Data and publication

- Total-return inputs: incumbent `data/yahoo/*.parquet` `close` column;
  `collectors/yahoo.py` documents dividend adjustment. Never use `close_price`.
- Population: the active dated members of the eleven `us_sector_*` baskets in
  `data/baskets/membership.json`; incumbent mappings are documented by
  `scripts/seed_us_sector_baskets.py`. This is current screen membership, not
  point-in-time research evidence.
- Computation: `engine/prophet_under_index.py`. Nine-sector history starts
  1998-12-22; eleven-sector history starts 2018-06-19. Each owns its percentile
  history; the historical screen switches to eleven on 2019-07-19. The live
  publisher always uses eleven sectors.
- Builder: `python -m scripts.build_prophet_under_index` writes
  `site/prophet/under_index.json` atomically. `lib/nyse_calendar.py` supplies
  the last completed session with its conservative close/settlement buffer.
  Future and in-progress bars are excluded before any window calculation.
- One build hook: `scripts/ci/daily_engine_prophet_nightly.sh`, after the
  existing Prophet builder. The file is included in both output manifests
  and the closed allowlist in `scripts/ci/daily_engine_prophet_checkpoint.sh`;
  existing exact-source, preimage and concurrent-writer checks remain intact.
- Serving uses the existing static `site/` file route in `app/deploy/Caddyfile`,
  at `/prophet/under_index.json`, retaining its existing authentication/cache
  policy. No new anonymous allowlist entry, API, credentials or Terminal change.

## Contract

`prophet.under_index/v1` contains the session date, index gap to its 252-session
high, simple 21-session index return/band, sector up/down/damaged counts and
sector names, reader state, cancelled share and its 21-session median, offsetting
band, display form, and per-sector member-high/drawdown counts plus coverage.
No member names, member price series or fund/vendor group keys are published.

The fixed offsetting cuts are `0.011158259853538948` and
`0.34622932464889694`: the 25th/75th percentiles of the nine-sector rolling
21-session median of K over 2004-01-02..2023-12-29. They are NOT recomputed
at runtime and also apply to eleven sectors. Display cuts: **.011 / .346**.
Equality at the lower cut is almost none; equality at the upper is about usual.

Display forms:
- `compact`: rising together or quiet, with index flat/up;
- `falling_with_index`: falling together, with index down;
- `full`: every other available combination;
- `unavailable`: state or index band unavailable, or a stale/partial live panel.

Warm-up states/bands are `n/a`, numeric missing values are JSON null. Exact zero
sector returns count in N but neither direction. Member total includes members
without a full valid 252-session history; `eligible_members` discloses the
coverage of the two high/drawdown counts. No filling of missing bars.

Mandatory copy travels with the file:
- "counts sectors equally; not an attribution of the index's return"
- "Describes what is happening under the index today. It has not been shown to predict turns."
- "description only"
- "screen readout; not research evidence"

Live values are a screen readout of today, not research evidence.

## Acceptance

`tests/test_prophet_under_index.py` covers each form/offsetting band, exact cuts,
warm-up, eleven-sector majority, missing/zero returns, member coverage, completed
bars, stale panels, count-only publication and nightly allowlists. The dedicated
`prophet-under-index` job in `.github/ci/legacy-jobs.yml` owns the tests in CI.
The six-row fixture holds labels/counts only and both full reference hashes.

Full comparisons require **both** explicit environment variables:
`PROPHET_UNDER_INDEX_REFERENCE_DIR` (directory containing the two frozen CSVs)
and `PROPHET_UNDER_INDEX_PRICE_DIR` (directory containing incumbent adjusted-close
parquets). Neither has a machine default; tests skip when unset. Run:

```sh
python -m pytest tests/test_prophet_under_index.py -q -s
```

The full test verifies each reference hash, maps fund keys to sector names,
normalizes the reference's human-readable falling-with-index label to the
published identifier, and compares every field exactly at its printed precision.
Frozen acceptance: nine-sector **5,033 rows / 0 mismatches**; eleven-sector
**1,121 rows / 0 mismatches**. Reference CSVs and research panels are not vendored.
