# Prospective Yahoo WTI observation export

The existing ordinary Yahoo batch already requests `CL=F` through
`config.yml → yahoo.tickers.fx_commod`. `scripts.collect._run_one("yahoo", ...)`
now enables a separate WTI observation capture on that **same** fetch. The
existing daily collector command reaches it without another ticker, provider
request, model, trial, or changed nine-sector cohort. Deploying this source does
not itself prove that a collector has returned or published a capture.

The call path is `YahooAdapter.fetch(capture_source_metadata=True)` → ordinary
`store.upsert` → `capture_yahoo_wti_observation` →
`export_yahoo_wti_observation`. Metadata records the actual current-call `Adj
Close` field, or the `Close` fallback when no adjusted field was returned. It
never labels a continuous futures close as total return or official settlement.
Failed rebase responses lose their metadata; inherited cache/fallback values do
not acquire current-call Yahoo provenance.

The existing private content-addressed writer retains normalized provider and
merged images plus its receipt under `data/yahoo/.availability_capture/` with
its existing ownership, no-clobber and 0700/0600 rules. This directory is now
explicitly untracked. Git checkout is not a supported import into that store.

`data/yahoo/CL_F.observation.json` is the single bounded export for normal
`data/` publication. Its `yahoo.wti_observation_export.v1` envelope contains:

- Exact receipt, provider-return image and merged-image bytes as base64, with
  byte lengths and SHA-256 digests. The images are the existing documented
  normalized JSON encoding, not vendor wire responses.
- A hash and length of `CL_F.parquet`, whose decoded normalized values must
  exactly equal the merged capture. Parquet bytes and decoded row/column/size
  limits are checked before decoding. A second bounded read detects a cache
  change during export.
- An actual export clock after image durability, with explicit unqualified
  scenario adoption and no original historical availability claim.

The export has a 2,000,000-byte bound and replaces the previous sidecar only
after validation. Validation failure leaves the prior sidecar intact. A
post-replacement durability failure remains an uncertain publication and is
reported unqualified; no acquisition is replayed. An export's existence alone
never establishes freshness: consumers must compare the current parquet hash,
all nested lengths/digests and capture clocks. The ordinary pipeline's existing
broad `git add data/` retains the sidecar; `.gitignore` excludes private capture
objects and temporary export files. No new storage backend or registry is used.

`compose_snapshot` v6 reads an optional, bounded export and includes only its
path/hash/length in the normal read manifest. It rechecks those bytes after
composition. Missing export preserves the existing surface. Export payloads are
never copied into the public snapshot. A changed export changes the manifest;
this does **not** change `source.asof` or `source.built`, validate the export, or
qualify a baseline. The existing WTI runtime refusal remains in force.

## Calendar and adoption decision

The maintained
[pandas_market_calendars CL implementation](https://github.com/rsheftel/pandas_market_calendars/blob/master/pandas_market_calendars/calendars/cme_globex_energy_and_metals.py)
explicitly supports CL via `CMEGlobex_CL`/`CL` aliases. Its ordinary schedule uses
America/Chicago, opening the prior day at 17:00 and closing at 16:00. This is a
candidate implementation, not an installed or selected native calendar.
[CME's current trading-hours notices](https://www.cmegroup.com/trading-hours.html)
contain holiday-specific trade-date conventions; for example, the 2026
Thanksgiving notice assigns orders after the November 25 preopen to the
November 27 trade date. A generic daily schedule and special closes therefore
cannot alone certify Yahoo `CL=F` bar-date labels. Cash-equity calendars and
weekday ranges remain unsupported substitutes.

Positive native scenario adoption still requires the exact Yahoo daily-bar
versus futures-session/date/completion convention, applicable versioned calendar
bytes and at least 60 future session labels. Continuous-roll policy and official
settlement equivalence remain unspecified; a consumer must not silently invent
either. The existing TXI close/return/MA semantics remain unchanged.

A later native loader must validate the exact retained export generation and
cache binding, then require capture/export known-by clocks no later than a
**genuine newly built** selected TXI snapshot cutoff, and an effective bar date
matching that snapshot. Adding an export to an old manifest or hashing today's
cache cannot backfill an old cutoff. This source change adds no positive loader,
new scenario assumption, live evaluation or production acceptance.

The Chairman's named Research Factory Yahoo/yfinance commercial data rights are
`APPROVED_BY_CHAIRMAN_ATTESTATION` under
`DEC:COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023`. No vendor contract ID or
new licensing approval is required. The export truthfully names its native
collector; its technical relation and intended purpose must be bound to the
attested source route before adoption. The named attestation is not expanded by
matching a ticker alone.

The next release owner must publish/install the source through the ordinary
path, consume a genuine subsequent ordinary Yahoo export and its normal data
publication, and finish the calendar/clock/source-route qualification in the
existing native loader before testing the actual Macro scenario journey. A
fixture, green check, source merge, installed method, or export alone does not
complete that journey.
