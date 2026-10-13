# JSON request reference

The host configuration fixes roots and test-workspace paths. Requests cannot supply a configuration, absolute source path, server URL or executable.

| Action | Fields |
|---|---|
| capabilities | No extra fields |
| search | query (optional), limit 1–100 |
| browse | root alias; optional path, offset, limit 1–200, expected_directory_version |
| describe | ref |
| read | ref; optional columns, time_column, start, end, equals, offset, limit 1–200, expected_version |
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
