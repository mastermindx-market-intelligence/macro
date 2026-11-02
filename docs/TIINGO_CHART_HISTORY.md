# Receipt-bound BOATS chart history

`scripts/tiingo_chart_history.py` exports selected existing BOATS REST minute-bar
research views into a private Terminal delivery candidate. It uses the incumbent
raw receipt, materializer and verified view reader. It performs no acquisition,
archive rewrite, stream capture, publication, service change or Data OS contract
promotion. The EOD archive and standalone provider holds are unaffected.

Tiingo's [official BOATS REST documentation](https://www.tiingo.com/documentation/boats)
provides `/boats/<ticker>/prices`, restricts history to 20:00–03:59 Eastern and
requires `columns=open,high,low,close,volume` to expose BOATS-only share volume.
A missing interval is unknown coverage; no empty candles or no-trade claims follow.

Pass a bounded JSON array of `[capture-day, exact-receipt-id]` pairs. Select captures
from accepted archive receipts; the tool does not choose a latest revision or
search the vendor. It refuses conflicting overlapping prices/volume, wrong ticker,
non-minute captures, missing volume, invalid OHLC and corrupted source evidence.
Identical overlap retains every contributing receipt ID. Empty raw captures without
materialized evidence stay unavailable under the incumbent reader.

```sh
python3 -m scripts.tiingo_chart_history --symbol AMD \
  --refs /private-delivery/AMD.refs.json --output /private-delivery/AMD.json
```

The output must be a new private file. A public/site output path is refused. The
schema is `terminal.tiingo_boats_history.v1`: source UTC minute OHLCV, exact capture
receipts plus per-bar receipt IDs, BOATS venue, vendor-reported unqualified price
basis and vendor-reported share volume. `complete` is always false and coverage is
`captured_vendor_bars_only`. No raw/adjusted equivalence, historical security identity,
point-in-time availability, consolidated tape or executable-price claim is added.

The paired Terminal reader expects these files in a private server directory
configured by `TIINGO_BOATS_HISTORY_DIR`; no data is committed to `public/`. The
existing `/api/intraday?session=24h` consumer converts UTC to ET display epochs,
filters the existing immutable NYSE calendar and resamples without crossing session
phases. The regular provider keeps authority on an epoch collision. Source evidence
records the input digest, receipt IDs, incomplete coverage and missing/unavailable
states. Activation and production proof are separate assigning-principal actions.

Existing-data proof on 2026-10-19: AAPL 687 source minutes / one receipt, AMD 720 /
one, SOXX 14,277 / ten. These are capture counts, not full-session or all-ticker
coverage. Private candidates and their exact digests are retained under
`/Volumes/Mastermind/market-data/tiingo-chart-candidates/01a152ae-bd73-7251-ba0e-ddeaac151360/`.
Licensed rows remain there and are excluded from GitHub evidence.
