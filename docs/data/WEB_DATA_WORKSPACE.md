# Web data and Lab access

Operation: `web-data-lab-access-20261011-c4-001`

## Decision

Use the already working account-scoped Studio Direct Secure MCP Tunnel. A private
Mastermind Data & Lab workflow plugin invokes one host command,
`/Users/chriswong/.local/bin/mmx-data-workspace`, with a bounded JSON request.
This requires no new inbound port, tunnel, public data endpoint, OAuth service,
browser extension, data registry, or execution queue.

The transport remains the existing owner. `lib.dataos.registry` remains the
contract owner; `engine.lab` and `engine.trial_ledger` remain the calculation and
trial-accounting owners. This adapter supplies discovery, explicit source
selection, bounded reads, and a small reviewed recipe surface. A future typed MCP
facade can call the same `web_api.dispatch` without moving data or calculations.

The plugin is skills-only because no verified backend ID for editing the existing
Studio Direct plugin was available. It names the existing connection as an
operational prerequisite and does not invent an app dependency or endpoint.
Installing the workflow alone does not establish a Studio connection in another
account. Each web session needs its existing authorized Studio Direct tools.

## Source and runtime

| Component | Responsibility |
|---|---|
| `config/web_data_workspace.studio.json` | Explicit host data-only root bindings and external test artifact directory |
| `lib/dataos/web_workspace.py` | Canonical contract projection, namespaces, descriptor-confined reads, source versions |
| `lib/dataos/web_readers.py` | Bounded Parquet, CSV, JSON, JSONL/NDJSON inspection and row selection |
| `lib/dataos/web_api.py` | Strict JSON dispatch and synchronous worker lifecycle |
| `lib/dataos/web_lab.py` | Existing signal catalog, validated plans, canonical Trial forwarding |
| `lib/dataos/web_lab_worker.py` | Selected-file materialization, process bounds, accidental-side-effect guard |
| `scripts/data_workspace.py` | One request on stdin, one JSON response; no arbitrary code, SQL, URLs or credentials |
| `plugins/mastermind-data-lab/` | Portable private workflow package and request reference |

Source canaries may run in the admitted operation workspace. The installed command
must use an immutable export of an accepted merged source commit outside operation
workspace garbage-collection roots. Do not point the installed command at a
feature branch, move the shared `macro-main` checkout, or infer installation from
a source merge.

The selected local release layout is:

```text
/Volumes/Mastermind/runtime/data-workspace/releases/<accepted-commit>/
    RELEASE.json
    lib/
    engine/
    config/dataset_registry.yml
    config/web_data_workspace.studio.json
    scripts/data_workspace.py
/Users/chriswong/.local/bin/mmx-data-workspace
```

Export only tracked runtime source from the exact accepted commit. Refuse archive
symlinks, nonregular members and path escapes. Include any additional tracked
Python dependencies only if the isolated release canary establishes they are
needed. Record source commit, file hashes and verification in the host-owned
`RELEASE.json`. Verify capabilities, real reads and a selected canonical Lab run
from that export before selecting the fixed launcher. The CLI reads the accepted
commit from this manifest when no Git metadata is present.

Use the already installed Python environment with pandas, NumPy, PyArrow and
PyYAML. No package installation or service restart is required by this source
change. Stop at a specific missing runtime dependency rather than silently
substituting another implementation.

## Data truth and access

The binding file is an access allowlist, not a second dataset registry.
`search` shows existing contracts and root-level namespaces separately. A
contract declaration does not prove bytes exist; a file does not establish
production admission. `browse` exposes nested data names with bounded scans and
version-aware pagination. `describe` reports exact stored schema and clocks.

All source handles are read-only and descriptor-relative. Child symlinks,
nonregular files, hard links, traversal, hidden names and credential-like names
are refused. The required external volume must actually be mounted. Files and
directories are checked for replacement during observation.

Source receipts preserve the alias, relative path, evidence kind, byte count,
stat-based version, and limitations. The version identifies device/inode/size/
mtime/ctime; it is **not** a full content hash or permanent snapshot guarantee.
Filesystem mtime is never described as data freshness. Parquet date ranges come
from stored row-group statistics, with completeness reported.

| Stored material observed on Studio | Availability interpretation |
|---|---|
| `macro_snapshot:stocks/AMD.parquet` | 11,736 observations; stored Date range 1980-03-17 through 2026-10-08 |
| `macro_snapshot:options_flow/summary_AMD.parquet` | 145 observations; stored index range 2026-01-02 through 2026-08-12; derived options summary |
| `macro_snapshot:options_surface/index_etf.parquet` | Stored surface history through 2026-07-15; not a current chain |
| `macro_snapshot:polygon_gex/chains/2026-08-13.parquet` | 185,072 stored chain rows for that asof date |
| `macro_snapshot:intraday_flow/ledger.parquet` | Derived session-level flow observations; not raw trade/quote evidence |
| `macro_snapshot:fred_vintage/vintages.parquet` | Separate period, realtime_start and realtime_end clocks; latest observed realtime_start 2026-10-08 |
| `macro_legacy_history:sec_ftd/panel.parquet` | 22,415,847-row history with separate observation and availability fields |
| `fundamental_history:us_fund/AMD.json` | Stored vendor snapshot; fetched clock is not original publication availability |
| `options_sample_research` | Cboe demonstration/research captures; not a live feed or production admission |
| `iex_deep_archive` | 9,875,890,058-byte DEEP+ capture and receipt; IEX venue only, metadata access here |
| `tiingo` | Proposed local archive binding; directory absent at census, no ingestion launched |
| `lse_options` | Existing namespace with an empty IWM one-minute directory at census |
| `web_test_runs` | Request, result, status and canonical temporary-ledger evidence from bounded web tests |

True overnight trade history, a daily open/previous-close gap factor, and an
extended-session quote snapshot are different data products. The inspected
overnight panel is a daily-OHLC decomposition. No local true overnight per-print
archive was verified by this census. Terminal source supports extended-session
labels and an overnight provider path, but source capability is not proof of a
current entitled/live deployment. The VPS quote state remains unobserved by this
task; local absence does not establish absence there.

## Read contract

- Results: at most 128 KiB; at most 200 rows and 128 selected columns.
- Query evaluation: at most 100,000 original source records after the requested
  offset. Offsets retain original positions; filtered matches are not renumbered.
- Text sources: separate 32 MiB bounded format/schema pass. The query's scan count
  does not claim that validation read only those records.
- Parquet: footer and selected row-group size fences precede materialization.
- Dates: explicit stored clock; inclusive date-only bounds in its own calendar;
  compatible timestamp awareness; no guessed numeric epochs.
- Missingness: absent fields and nonfinite values become null with notes.
- Unsupported or compressed sources: metadata only; use the existing owner decoder.
- Continuation: use returned offset and the same source/directory version.
- Filtering stored rows does not reconstruct point-in-time availability or repair
  membership, corporate actions, price basis or publication lag.

## Testing contract

All 195 current canonical catalog entries remain discoverable. Nine direction+1
recipes are initially admitted for execution, through reviewed callable modules
`engine.ma_crosses` and `engine.rsi_signals`:

`golden_cross_7_35`, `golden_cross_21_100`, `golden_cross_50_200`,
`ma_buy_7`, `ma_buy_21`, `ma_buy_35`, `ma_buy_100`,
`rsi14_oversold`, `rsi21_oversold`.

Other modules are discovery-only until their actual input behavior is reviewed.
Insider and fundamental-valuation signals explicitly require supplemental
unbound data. New catalog additions are not admitted implicitly.

A run selects 1–8 file refs, an explicit ISO time column and source-to-OHLCV map,
date bounds, daily bar frequency, and a positive declared trial budget.
Daily-only execution retains the canonical 252-period annualization convention.
The worker refuses multiple rows on the same stored calendar date. This is
independent of the ability to read intraday or overnight source rows.

Bounds: 20,000 loaded rows per source, 80,000 total, 500,000 scanned rows per
source, 60 seconds wall time, 45 seconds CPU, and bounded output files.
The worker accepts trusted catalog recipes only. Its audit hook guards against
accidental network, subprocess, private-configuration and outside-directory
write effects; it is not an arbitrary-Python security sandbox.

Each run writes to its own external test directory. The existing
`TrialLedger.with_declared_budget` creates its normal deterministic temporary
JSONL there. The wrapper never calls `Trial.to_ledger` or writes the production
trial ledger. Requests, terminal status, selected source versions, column maps,
date bounds, canonical Trial and temporary-ledger checksum remain inspectable.
Launch failures and timeouts retain their run identity. An unconfirmed termination
is explicit and must be reconciled before treating the run as finished.

The unused benchmark lookup in `engine.lab.backtest` was removed. It contributed
no calculation but unnecessarily imported `lib.store`, loaded host configuration
and could create a data directory. Canonical statistics and verdicts are retained.

## Verification and adoption

`WEB_ACCESS_CANARY_20261011.json` records source-candidate consumer-path checks:
actual stock and options slices, an expected refusal of an unreviewed signal, and
a successful canonical daily Lab run on 1,953 selected AMD observations. This is
source evidence, not an installed-release or all-account claim.

Run the focused new reader, workspace, API, Lab and worker suites plus the
affected existing Lab regression tests. Use external temporary storage and avoid
the full sparse-checkout suite. Source publication follows the normal
commit/PR/concluded-review/check/merge chain. After merge, verify the immutable
runtime export and fixed command; then save the private workflow plugin and
report which connection and accounts were actually exercised.

OpenAI primary references:
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://developers.openai.com/plugins/build/auth
- https://learn.chatgpt.com/docs/extend/mcp
