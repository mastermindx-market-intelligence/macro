# JSON request reference

The host configuration fixes roots and test-workspace paths. Requests cannot supply a configuration, absolute source path, server URL or executable.

| Action | Fields |
|---|---|
| capabilities | No extra fields |
| search | query (optional), limit 1–100 |
| browse | root alias; optional path, offset, limit 1–200, expected_directory_version |
| describe | ref |
| read | ref; optional columns, time_column, start, end, equals, offset, limit 1–200, expected_version |
| history_dossier | ref to manifest.json, manifest_sha256, date; optional paired macro_ref/macro_sha256 and filings_ref/filings_sha256; filings_offset (default 0); reveal_outcomes (boolean, default false) |
| lab_signals | Optional query, limit 1–100 |
| lab_plan | signal_id, refs; optional horizon_bars, cost_bps, n_configs_searched |
| lab_run | request (the plan's inner request), time_column, column_map, bar_frequency ("daily"); optional start, end, expected_versions |

## Find and inspect

```json
{"action":"search","query":"overnight","limit":20}
{"action":"browse","root":"macro_snapshot","path":"stocks","limit":20}
{"action":"describe","ref":"macro_snapshot:stocks/AMD.parquet"}
{"action":"describe","ref":"registry:the_exact_discovered_dataset_id"}
```

Data refs are `root_alias:relative/path`. Registry refs describe contracts; they do not resolve automatically to a physical file. The host bindings include local Macro snapshots and legacy history, fundamentals, IEX raw captures, Cboe samples, other research captures, proposed Tiingo and LSE options roots, and web test artifacts. A binding may be absent or empty.

### Useful starting refs

Search observes top-level namespaces; it is not a recursive filename index.
Use these already observed refs as starting points, and describe them again
before interpreting current contents:

| Purpose | Ref |
|---|---|
| Daily stock history | `macro_snapshot:stocks/AMD.parquet` |
| Derived options flow | `macro_snapshot:options_flow/summary_AMD.parquet` |
| Stored chain snapshot | `macro_snapshot:polygon_gex/chains/2026-08-13.parquet` |
| Overnight-gap research panel | `macro_snapshot:research/pss_f2_overnight_panel.parquet` |
| Session-level flow research | `macro_snapshot:intraday_flow/ledger.parquet` |
| Macro vintages | `macro_snapshot:fred_vintage/vintages.parquet` |
| Fundamental snapshot | `fundamental_history:us_fund/AMD.json` |

The overnight panel contains evaluation metrics from daily open/previous-close
decomposition, not timestamped overnight trades. No date/session column was
observed in that panel at the initial census. A zero top-level search match is
not proof that no nested dataset exists.

## Read rows

After obtaining the exact schema and version, replace the example version with the returned value:

```json
{"action":"read","ref":"macro_snapshot:stocks/AMD.parquet","columns":["Date","close","volume"],"time_column":"Date","start":"2026-10-01","end":"2026-10-08","limit":20,"expected_version":"statv1:<returned 64-hex digest>"}
```

Date-only bounds are inclusive in the stored clock's calendar. Timestamp bounds require compatible awareness; epoch units are never inferred. `equals` maps exact column names to scalar equality values. Projection names and filter names must exist.

Rows and positions retain original source ordering. `next_offset` is an original-row position, not a count of matches. A call evaluates at most 100,000 rows after its offset. Results are capped at 128 KiB and 200 rows; reduce columns or limit when needed. Text sources have a separate 32 MiB format/schema-read limit. Large Parquet row groups and oversized cells can be refused explicitly.

## Historical daily dossier

First check that `capabilities.actions` contains `history_dossier`. Browse the retained output and read its producer receipt. Replace every example reference and digest below with that retained evidence; these placeholders are not usable hashes. A missing receipt is an evidence gap, not permission to invent a checksum. The manifest binds the exact archive generation; the independent macro digest binds the selected initial-release chronology.

Market observations only, with future outcomes excluded:

```json
{"action":"history_dossier","ref":"web_test_runs:<observed archive>/manifest.json","manifest_sha256":"<exact manifest digest from producer receipt>","date":"2022-09-13"}
```

The same date with separately bound macro first releases:

```json
{"action":"history_dossier","ref":"web_test_runs:<observed archive>/manifest.json","manifest_sha256":"<exact manifest digest from producer receipt>","date":"2022-09-13","macro_ref":"web_test_runs:<observed macro archive>/initial-prints.json","macro_sha256":"<exact macro digest from producer receipt>"}
```

Dates must be real, zero-padded ISO dates; no nearest-date fallback occurs. Digests are 64 lowercase hexadecimal characters. `macro_ref` and `macro_sha256` must appear together. `ref` is a descriptor-confined source reference, never an absolute path or URL. Source reads are bounded by the existing DataWorkspace owner and the archive's hash, schema, record and decoded-byte limits; the response retains each observed source version, content hash, and query receipt. Refusals leave no partial result.

The optional macro reference must end in `.json`; a historical Parquet partition is refused before it is opened. Source and calculation versions remain explicit, with full provenance accessible in the same exact manifest. The response separately declares encoded-file and decoded-table budgets; these are not peak-process-memory limits. Later revision-end metadata is omitted from date projections, and the declared macro archive window does not prove calendar completeness.

The default does not read outcome files at all. Only an explicit outcome-analysis task may add `"reveal_outcomes":true`. The returned `summary` describes selected proxies, not whole-market breadth. `coverage` lists unavailable news/causal context, consensus, filings, historical stock identity, intraday/options and strict point-in-time proof rather than filling gaps. First-release chronology is not a full historical macro revision matrix.

This action does not run a strategy, collect a source, refresh data, create a ledger entry, write an artifact, or change a live signal. The separate existing Lab remains the strategy-experiment interface.

## Filing context

Only use this when the installed capabilities advertise `history.filings`. Select a retained `earnings_8k_dates.parquet` reference and its exact SHA-256, along with the market archive reference/digest. A source stat-version token is not its content digest. Both optional filing fields must appear together.

```json
{"action":"history_dossier","ref":"web_test_runs:<observed archive>/manifest.json","manifest_sha256":"<exact retained manifest digest>","date":"2020-03-16","filings_ref":"macro_snapshot:edgar/earnings_8k_dates.parquet","filings_sha256":"<exact retained filing source digest>"}
```

The result contains at most 50 filing records, `total_events`, `next_offset`, and `remaining_events`. For another page, resend the exact same date and hashes with `filings_offset` equal to the returned `next_offset`. This is a matched-filing offset, not the generic `read` action's original-row offset. Do not treat a first page as a full date census while `next_offset` remains present.

The source's filing-date range is an observed range, not calendar completeness. `NO_RETAINED_FILING` means no record in that selected source/date, not no corporate or market event. The canonical filing key is CIK/accession; stored ticker labels do not prove historical symbol identity. `filing_date`, `report_date`, `acceptance_datetime_source` and normalized source-claimed UTC remain distinct. No verified intraday publication/availability, earnings values, consensus, surprise or causal explanation is supplied. The source universe need not match the selected price-proxy universe.

All bytes pass through the unchanged descriptor-confined source reader. The exact source filename is required before opening it, so a historical outcomes partition cannot be selected through this channel. The limits are 16 MiB source bytes, 32 MiB declared decoded Parquet and 250,000 original records, plus the existing 128 KiB response limit. No collector, filing download, write, identity migration or live signal is triggered.

## Prepare and execute a Lab test

First inspect a source's columns and dates, then discover a supported recipe:

```json
{"action":"lab_signals","query":"golden_cross","limit":20}
{"action":"lab_plan","signal_id":"golden_cross_7_35","refs":["macro_snapshot:stocks/AMD.parquet"],"horizon_bars":21,"cost_bps":5.0,"n_configs_searched":1}
```

For an explicitly bounded one-configuration test, the execution request is:

```json
{"action":"lab_run","request":{"signal_id":"golden_cross_7_35","refs":["macro_snapshot:stocks/AMD.parquet"],"horizon_bars":21,"cost_bps":5.0,"n_configs_searched":1},"bar_frequency":"daily","time_column":"Date","column_map":{"close":"close","high":"high","low":"low","volume":"volume"},"start":"2019-01-01","end":"2026-10-08"}
```

Optional `expected_versions` maps each selected ref to its described file version. Column-map keys are canonical lowercase `open`, `high`, `low`, `close`, `volume`; values are exact stored column names. `close` is required. Include other columns only when present and needed by the chosen recipe. Clock values must be explicit ISO dates or timestamps and be unique and ascending, with one observation per stored calendar date. Lab execution is daily-only and retains canonical 252-period annualization. Reading intraday or overnight source data remains supported.

Limits: 8 distinct refs, 20,000 loaded rows per ref, 80,000 total rows, 500,000 evaluated rows per source, 60 seconds wall time and 45 seconds CPU. Larger work belongs to the existing batch execution owner.

Use the returned artifact alias and run ID to inspect saved evidence:

```json
{"action":"browse","root":"web_test_runs","path":"<returned run_id>","limit":20}
{"action":"read","ref":"web_test_runs:<returned run_id>/status.json","limit":1}
```

Keep source versions, mapping, date bounds, limits, ledger receipts and the full canonical Trial attached to the interpretation. The request/result artifacts establish what actually ran; file creation alone does not establish a successful result.

## Private CLI consumers of the same filing source

`market_memory_history dossier` and `market_memory_history export` accept `--filings PATH --filings-sha256 EXACT64` together. The selected file must be named `earnings_8k_dates.parquet`; the existing file owner still enforces regular-file, source-hash and byte limits. `dossier --filings-offset N` paginates matched filing records. No filing offset is accepted for an offline export because its source-bound timeline is exported once and the browser paginates locally.

No option implicitly selects a source, updates a provider, installs a schedule or changes an existing archive. Export requires a new output path. Without an explicit filing binding the old market/macro view remains unchanged and no filing source is opened. Default machine reads still never open outcomes. A browser requested with `--include-outcomes` is explicitly educational, not a blind-evaluation security boundary.

## Transcript source context

Require installed `history.transcripts` and `history_transcript` capabilities. Describe the original closed source family `stock_earning_call_transcripts.parquet`; substitute the actual bound reference and its `file_version` below. Do not replace a version token with an invented content hash. Default day requests read metadata only, not transcript paragraphs or price outcomes.

```json
{"action":"history_dossier","ref":"web_test_runs:<observed archive>/manifest.json","manifest_sha256":"<exact manifest digest>","date":"2020-03-16","transcripts_ref":"fundamental_history:transcripts/stock_earning_call_transcripts.parquet","transcripts_version":"<observed statv1 file version>"}
```

Continue date listing by passing the returned `next_offset` as `transcripts_offset`; this is a matched-record index. To read one listed body, use its original `source_row_position` and metadata digest:

```json
{"action":"history_transcript","ref":"fundamental_history:transcripts/stock_earning_call_transcripts.parquet","expected_version":"<same observed statv1 file version>","row_position":0,"expected_metadata_sha256":"<selected record metadata_sha256>"}
```

The zero above is only a placeholder; substitute the actual row position, even when the vendor `transcripts_id` is null. Optional `max_chars` is1–12000(default6000). Continue with `paragraph_offset` and `character_offset` from the exact `next_cursor`, retaining `expected_record_sha256` from the first page. Source paragraph numbers need not be sequential and are not the cursor. Output fragments identify original character boundaries; only `next_cursor:null` completes that requested text range. A source-version mismatch or source replacement refuses rather than retrieving different text.

`record_sha256` covers the canonical selected metadata and original paragraphs; `page_sha256` covers the returned fragments. Neither is a checksum of the complete Parquet corpus. The source may contain other decoded rows in the bounded column chunk, but only the selected record is exposed. The interface performs no role inference, Q&A reconstruction, source intake, provider call or source write. Date lookup reports the retained source universe, not the selected price cohort.

The local accepted history CLI can produce an offline metadata-only catalogue through the existing host config with `transcripts-catalog --config HOST_CONFIG --ref BOUND_REF --expected-version OBSERVED_VERSION --output NEW_JSON`. It refuses overwrite and closes the original mutation guard before writing. Pass that file and its receipt SHA256 to the existing `export` command as `--transcripts-catalog NEW_JSON --transcripts-catalog-sha256 EXACT64`. The offline browser's read-request button computes the same exact metadata digest and retains the source-version binding. Bodies are not duplicated into that HTML, no external calls occur, and publication/point-in-time/trading qualification remains unproven.
