# massive_stock_day partial session — diagnosis (2026-10-12)

Lane G-GAP. Read-only on the collector. No store fix in this change.

Measured fact this diagnosis explains (seat, real store; no price series was read here): session **2026-08-18** (Tuesday, ordinary NYSE session) is absent for QQQ, IWM, XLE, XLF, XLI, XLP, XLRE, XLU, XLY and present for SPY, DIA, XLB, XLC, XLK, XLV. Every other session from 2021-07-06 through 2026-10-07 is present for all fifteen. Amendment A1 / D15 pins that one date as a panel calendar exclusion. This note is for the collector owner.

## Most likely mechanism

**A non-empty raw day that did not contain those nine tickers was written through, and the weekday was added to `processed_days`.** After that, nothing re-fetches the day.

Confidence: **medium**. The code path is certain (repro `a1`/`a2` below). It is the best fit for this particular split, and it is not the only fit.

Why this one, ahead of the others that can end in the same files:

- The collector treats a per-ticker gap as legitimate and seals any non-empty frame. A vendor file that simply omits nine liquid names becomes a permanent store gap. That is the contract written at `collectors/massive_stock_day.py:88-91`.
- The fifteen names in alphabetical order are DIA, IWM, QQQ, SPY, XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY. The names that have the session are interleaved with the names that lack it. `DataFrame.groupby` sorts, so a kill mid-loop writes an alphabetical prefix and, as repro `b3` shows, does not seal the day. This split is not that shape.
- The nine files still contain every other session. A file that stayed unreadable would miss every later day too (`_upsert_ticker` returns without writing, every night). A transient read failure on that one run is still possible. A partial R2 publish is still possible. Those two cannot be separated from a short raw file without the artifacts listed under "Could not determine".

The store does **not** repair this on its own. `run_incremental` selects `trading_days(window) − processed_days`. A date inside the set is never fetched again. Later sessions append around the hole (repros `b2` and `c2`).

## Could not determine without the real data

No parquet, no flat file, and no R2 object was available in this worktree. These six facts are what distinguishes (a), (b), and (c) for 2026-08-18:

1. The ticker set inside `us_stocks_sip/day_aggs_v1/2026/08/2026-08-18.csv.gz` (and its size / LastModified).
2. Whether `"2026-08-18"` is an entry of `processed_days` in `data/massive_stock_day/_backfill_state.json` on git and on R2.
3. Whether the collect host has `data/massive_flat/stock_day/2026-08-18_all.parquet`. Current `fetch_aggs` does not write a stock-day cache; it will serve one that is already there (repro `a5`).
4. A collector log line `unreadable` for any of the nine names on the night that date was sealed.
5. That night's `publish_r2` per-file failures: whether the R2 etag of `_backfill_state.json` moved while the nine `TICKER.parquet` etags did not.
6. Whether anyone ran `python -m collectors.massive_stock_day --rebuild-state`, or a v1 state file was migrated, against a tree where only some tickers held the date.

## How a day gets sealed

`processed_days` is a set of weekdays for the whole store, not a set of (ticker, date) pairs.

```46:49:collectors/massive_stock_day.py
`processed_days` is the AUTHORITATIVE per-day coverage record: every weekday that was
either fetched-and-written or confirmed empty upstream (holiday) is listed.  Resume /
incremental target selection is the SET DIFFERENCE trading_days(window) − processed —
never a scalar high-water mark.
```

The write loop adds the date after walking whatever tickers were in the frame. There is no row-count floor, no anchor-ticker check, and `_upsert_ticker` does not report a skipped file. `tickers_written.add` runs even when the upsert returned without writing.

```636:645:collectors/massive_stock_day.py
        else:
            parsed = _parse_day(raw, d)
            for ticker, grp in parsed.groupby("ticker"):
                _upsert_ticker(ticker, grp.drop(columns=["ticker"]))
                tickers_written.add(ticker)
            if earliest_date_written is None:
                earliest_date_written = d
            latest_date_written = d
            days_fetched += 1
            processed.add(d)
```

The module docstring says an S3 error is not recorded (`collectors/massive_stock_day.py:60-63`). That is true only when `fetch_aggs` raises. Production `fetch_aggs` catches the GET and the parse and returns an empty frame (`collectors/massive_flatfiles.py:170-172` and `:178-180`). `backfill` then records the empty frame as a processed holiday (`:629-635`). `tests/test_massive_stock_day_state.py` `test_failed_day_not_recorded_and_retried` stubs a fetch that raises, so it does not cover this return.

A nearby incident, DSC-MASSIVE-STOCK-DAY-UNPUBLISHED-TODAY-RETURNS-403, is a different failure: `probe_available` used to abort the whole incremental when calendar-today returned 403, so no day was written. It does not explain a session that exists for six names and not nine. An empty seal would drop the session for every ticker that did not already have a row (repro `a3`).

## Candidates

### (a) Day marked processed from a short or empty raw frame — CONFIRMED-POSSIBLE

| | |
|---|---|
| Where | `collectors/massive_flatfiles.py:181-185`; `collectors/massive_stock_day.py:629-635` and `:636-646` |
| Quote | "403/404/weekend -> empty" (`massive_flatfiles.py:170`) |
| Quote | "empty frame for %s (holiday/missing)" (`massive_stock_day.py:632`) |

Condition. `backfill` calls `fetch_aggs(d, product="stock_day", underlyings=None, use_cache=True)`. For `stock_day` the frame is returned with no length check, and the cache write that exists for options is below that return, so this branch never caches what it just downloaded:

```181:185:collectors/massive_flatfiles.py
    if product == "stock_day":
        # stock bars: ticker is the plain symbol; filter directly
        if uni is not None:
            df = df[df["ticker"].isin(uni)]
        return df.reset_index(drop=True)
```

`underlyings=None` does not filter. A short file, a file that parsed as a few rows, or a cache object already named `{date}_all.parquet` is accepted whole. The collector's own comment says a missing bar for one ticker is normal:

```88:91:collectors/massive_stock_day.py
Ordering: a ticker with no data (404 / 0-volume bar) on a given date simply has no
row for that date; per-TICKER gaps are legitimate (halted names, ETF launches).
Whole-STORE day gaps are NOT legitimate — that is what processed_days + the
massive_store audit guard.
```

The guard watches the weekday set and five anchor series. It does not watch "this weekday is missing on some tickers". See the audit section below.

Empty-frame sibling, same seal, different shape. No credentials, a 403, a 404, and a parse error all become `DataFrame()` inside `fetch_aggs`. `backfill`'s `except` does not see them. The date is stored as processed and is not a hole in `coverage.max_missing_run_weekdays`. That sibling removes the session for every ticker that did not already have the row. It does not, by itself, leave the session in six of these fifteen files.

Later run. Does not repair. Repro `a2`: the second `backfill`, handed a complete frame, makes zero fetch calls. Repro `a4`: same, after an empty seal. Repro `a5`: the real `fetch_aggs` returns a pre-seeded short cache and never calls the S3 client; the collector seals that frame.

Extra seal, same end state. `python -m collectors.massive_stock_day --rebuild-state` (`:832-836`) and the v1 migration (`:511-520`) set `processed_days` to the **union** of dates across parquets (`_scan_store_days`, `:465-476`). One ticker holding the date seals it for every ticker. Repro `rebuild`. Do not use that flag to repair this hole.

### (b) Per-ticker upsert failure, file left untouched — CONFIRMED-POSSIBLE

| | |
|---|---|
| Where | `collectors/massive_stock_day.py:245-257`, then `:645` |
| Quote | "left untouched rather than overwritten with this day's rows" |

Condition. `pd.read_parquet` raises (truncated object, wrong magic, a transient `OSError`). The function logs and returns. The loop continues. The date is still added to `processed_days`. Any subset of tickers can miss the row. The subset does not have to be an alphabetical prefix, because the exception is swallowed per ticker rather than escaping the loop.

```248:257:collectors/massive_stock_day.py
        except Exception as e:   # noqa: BLE001
            # NEVER clobber.  Under the R2 round trip an unreadable local file is a
            # transport artifact (truncated download, interrupted restore), not an
            # empty history — overwriting it with today's single row would shrink a
            # 5-year series to one bar and then PUBLISH that over the deep store.
            # Leave the file exactly as it is: the audit's unreadable-anchor fail and
            # the next fetch_r2 restore own the heal.
            log.warning("massive_stock_day: %s.parquet unreadable (%s) — left untouched "
                        "rather than overwritten with this day's rows", ticker, e)
            return
```

The comment says the next `fetch_r2` restore owns the heal. That restore puts back a readable object that also lacks the new row. The date is already in `processed_days`, so the row is never applied. Repro `b2`.

An exception that escapes `_upsert_ticker` (disk full on `to_parquet`, which is not caught) does **not** seal. The next run fills the ticker that was missed. Repro `b3`/`b4`. The dangerous path is the swallowed one.

Later run. Does not repair the missed session. If the file is still unreadable, every later session is skipped too. The seat's pattern (one interior session missing, neighbors present) fits (b) only when the read failed on that run and succeeded on later runs.

`to_parquet` writes the destination path directly (`:262`), not a temp file plus rename. A kill during that write can leave a truncated parquet. The next upsert then takes the "left untouched" return forever. That would punch out every session after the kill, which is not what was measured. `fetch_r2` itself does use temp-plus-rename (`scripts/fetch_r2.py:97-99`), so a killed download does not truncate an existing object.

### (c) Restore or partial publish puts an older object back — CONFIRMED-POSSIBLE

| | |
|---|---|
| Where | `scripts/fetch_r2.py:19-21` and `:87-99`; `scripts/publish_r2.py:656-707`; `collectors/massive_stock_day.py:744-748` |
| Quote | "Local files absent on R2 are NEVER pruned." (`fetch_r2.py:21`) |

Condition. Two different events produce the same sealed hole.

1. Publish uploads `_backfill_state.json` (the date is now processed) and some ticker parquets, and other ticker uploads fail. Failures are per key. Successful puts are not rolled back. The manifest put is skipped when any upload failed (`publish_r2.py:704-707`), but the objects that landed stay landed. `massive_stock_day` is not in `_APPEND_ONLY_DIRS` (`publish_r2.py:254`, the set is `attention` and `index_gex_history` only) and it has no entry in `_DATA_DIR_MIN_BYTES`. A changed parquet uploads even when it is smaller than the R2 object.
2. After the local write and after the state file says the date is processed, something replaces one ticker's parquet with the previous generation. `fetch_r2` does that whenever the local md5 differs from the R2 etag. There is no "local is newer" check:

```87:99:scripts/fetch_r2.py
        for key, (etag, _size) in remote.items():
            p = base / key[len(d) + 1:]
            if p.is_file() and _md5(p) == etag:
                current += 1
            else:
                todo.append((key, p))

        def _down(kp):
            key, p = kp
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.parent / (p.name + ".r2tmp")
            s3.download_file(bucket, key, str(tmp), **_xfer_kw)
            tmp.replace(p)
```

`_backfill_state.json` is one of those keys. Only keys ending in `_manifest.json` are skipped (`fetch_r2.py:79`). The git sidecar is not the copy `run_incremental` sees: the collect job restores first (`.github/workflows/daily.yml:287-308`), and a differing R2 state file replaces the checked-out sidecar.

The nightly publish is gated on `steps.massive_restore.outcome == 'success'` (`.github/workflows/daily.yml:947`). A restore that exits 1 does not publish, and the next successful restore still has the old state, so that night's local writes are discarded and the day is fetched again. A partial restore therefore does not persist, provided publish really did not run. A publish that exits 0 after a mix of successful and failed key uploads does persist: the comment in `publish_r2` that a failed file "retries it next run" (`:679-680`) is about the bytes. The collector will not rewrite those bytes while the date stays in `processed_days`, the restored file matches the old etag, and the next publish skips it.

GitHub Actions jobs do not share a workspace, so a `fetch_r2` in `us_scan_tier`, the hot-tape step, or `oracle_offrender` does not clobber the collect job's tree. A shared self-hosted checkout that restores this prefix while the collect job has already written the day and not yet published it can. This worktree has no log that says that happened on 2026-08-18.

Later run. Does not repair. Repro `c2`: after the QQQ object is replaced with its pre-session bytes, `run_incremental` fetches the next session (2026-08-19) and does not fetch 2026-08-18. QQQ's index is `2026-08-17, 2026-08-19`.

### (d) A second writer with a different ticker set — REFUTED

The only `to_parquet` that targets this store is `_upsert_ticker` (`collectors/massive_stock_day.py:262`). `scripts/backfill_massive_stock_day.py` calls that same `backfill`. Callers of `fetch_aggs` elsewhere pass options products (`scripts/build_options_flow.py`), not this store.

`scripts/fetch_r2.py` writes the same paths by whole-object download. That is the restore half of (c), not a builder that chooses a different set of sessions per ticker.

`scripts/hot_tape_radar.py:1024-1030` can write `data/massive_stock_day/<T>.parquet`, and only when no local parquet exists for that ticker. The bytes are the public R2 object for that ticker, the whole file, not one session. On the collect runner, after a successful restore, the file exists and this path does not run. It cannot add 2026-08-18 to six names unless those published objects already had the split.

No other Python writer of these parquets showed up in a search for `to_parquet` / `write_bytes` against this store.

### (e) A date, timezone, or holiday rule that skips the day for some tickers — REFUTED

| | |
|---|---|
| Where | `collectors/massive_stock_day.py:214-222` and `:230`; `nyse_calendar` import only at `:445` |
| Quote | "skips weekends only" (`:215`) |

`_trading_days` yields one weekday calendar for the whole store. 2026-08-18 is a Tuesday. Repro `e`: the range 2026-08-15..2026-08-19 yields 17, 18, and 19. Saturday and Sunday are the only omissions. `_parse_day` stamps `pd.Timestamp(d)` on every row of that fetch, ignoring `window_start`, and does not convert timezones. One fetch cannot land the same session on different dates for different tickers.

`lib.nyse_calendar` is used only by `check_local_mirror_freshness`, which returns immediately when `COLLECT_LANE` or `GITHUB_ACTIONS` is set (`:423-424`) and never writes the store. The collector does not consult the holiday set when it decides to skip a ticker.

A ticker omitted from the raw frame has no row. That is candidate (a), the vendor-omission contract, not a per-ticker holiday rule.

### (f) `_MIN_STORE_FILES` / partial-checkout guard — REFUTED for this hole

| | |
|---|---|
| Where | `collectors/massive_stock_day.py:162`, `:525-553` |
| Quote | "_MIN_STORE_FILES = 100" |

The fence runs before credentials and before any fetch. Below 100 parquets, with `processed_days` or a v1 `last_captured_date` claiming coverage, `backfill` and `run_incremental` return `{"blocked": "store_absent"}` and write nothing. Repro `f`: two parquets, state claiming one day, real floor of 100, result `store_absent`, zero fetch calls, neither ticker gained 2026-08-18.

A tree under the floor is also refused by `publish_r2._data_dir_syncable` (same floor of 100, `scripts/publish_r2.py:192` and `:403-406`), and the workflow will not publish when the restore step failed.

Related hazard, different damage. The real store is ~20k files. A tree of 100 or more files passes the fence even if thousands of tickers are absent. For every ticker in the raw frame that has no local file, `_upsert_ticker` creates a new parquet containing only that day's row (`:259-260`). Because this store is not append-only and has no byte floor, a later publish can upload those one-row files over the full-history R2 objects. That clobber is not the measured shape (full history with one session missing). A restore that exits 1 is not published, so the one-row files die with the runner and the next full restore still has the old state. The fence is not what punched 2026-08-18 out of nine otherwise complete files.

## The audits do not see a one-session split

`scripts/audit_massive_store.py` reads five anchors (SPY, QQQ, AAPL, MSFT, IWM) and fails a gap only when more than `massive_max_gap_bdays` consecutive business days are missing inside the trailing 90 business days. The configured limit is 5 (`config.yml:3906`). One missing Tuesday is a business-day gap of 1. The audit's own assumption is that the anchors move together:

```30:32:scripts/audit_massive_store.py
      continuity because each day is fetched as ONE whole-market file — a day missing
      from SPY is a day missing from everyone.
```

That assumption is false once (a), (b), or (c) has fired. QQQ and IWM are anchors and they are the names missing 2026-08-18, so this audit was the one check that had the files in hand. It still does not fail. Repro `audit`: synthetic SPY/AAPL/MSFT contain 2026-08-18, QQQ and IWM do not, neighbors exist, `asof=2026-10-09`, production thresholds. `exit 0`, `n_failed 0`, `n_flags 0`.

`scripts/audit_r2.py` coverage probe (`:365-403`) fails on `coverage.max_missing_run_weekdays_recent`, which `_write_manifest` computes from `processed_days` (`massive_stock_day.py:342-357`). A sealed partial day is not a missing weekday. The figure stays 0. The anchor block in the manifest is SPY only (`_ANCHOR_TICKER`, `:154`).

## Executed repros

Command, from the repo root, no network, store under a temp directory via `config.data_dir`. The runner was a temp script at `/tmp/g_gap_repro.py` and is not part of the tree. The output below is the record of that run. Prices are constants.

```
PYTHONPATH=/home/ubuntu0/lanes/wt/gd-w4-g-gap ~/lanes/venv/bin/python /tmp/g_gap_repro.py
```

Scenarios (a)-(c) set `_MIN_STORE_FILES = 1` so a two-file temp store is not mistaken for an unrestored checkout. Production clears that floor with ~20k files. Scenario (f) uses the real floor of 100. Exit code 0.

```
=== a1 short raw frame sealed ===
presence {"SPY": ["2026-08-17", "2026-08-18", "2026-08-19"], "QQQ": ["2026-08-17", "2026-08-19"]}
processed_days ['2026-08-17', '2026-08-18', '2026-08-19']
fetch_calls ['2026-08-17', '2026-08-18', '2026-08-19']
backfill {'days_fetched': 3, 'days_skipped': 0, 'days_failed': 0, 'blocked': None}

=== a2 retry with a complete frame ===
presence {"SPY": ["2026-08-17", "2026-08-18", "2026-08-19"], "QQQ": ["2026-08-17", "2026-08-19"]}
processed_days ['2026-08-17', '2026-08-18', '2026-08-19']
fetch_calls []
retry {'days_fetched': 0, 'days_remaining': 0, 'blocked': None, 'already_current': None}

=== a3 empty frame sealed as a processed day ===
presence {"SPY": ["2026-08-17", "2026-08-19"], "QQQ": ["2026-08-17", "2026-08-19"]}
processed_days ['2026-08-17', '2026-08-18', '2026-08-19']
fetch_calls ['2026-08-17', '2026-08-18', '2026-08-19']

=== a4 retry after the empty seal ===
presence {"SPY": ["2026-08-17", "2026-08-19"], "QQQ": ["2026-08-17", "2026-08-19"]}
processed_days ['2026-08-17', '2026-08-18', '2026-08-19']
fetch_calls []

=== a5 real fetch_aggs cache hit ===
cache 2026-08-18_all.parquet
tickers ['SPY']
client_calls 0

=== a5b collector seals the cached short frame ===
presence {"SPY": ["2026-08-17", "2026-08-18"], "QQQ": ["2026-08-17"]}
processed_days ['2026-08-17', '2026-08-18']
fetch_calls ['2026-08-17', '2026-08-18']

=== b1 unreadable QQQ left untouched, day sealed ===
presence {"SPY": ["2026-08-17", "2026-08-18"], "QQQ": []}
processed_days ['2026-08-17', '2026-08-18']
fetch_calls ['2026-08-18']
qqq_still_garbage b'this is not a parquet'

=== b2 QQQ readable again; sealed day not rewritten ===
presence {"SPY": ["2026-08-17", "2026-08-18", "2026-08-19"], "QQQ": ["2026-08-17", "2026-08-19"]}
processed_days ['2026-08-17', '2026-08-18', '2026-08-19']
fetch_calls ['2026-08-19']

=== b3 raise mid-loop ===
error disk full mid-loop
presence {"AAA": ["2026-08-18"], "ZZZ": []}
processed_days []

=== b4 retry after an escaping raise fills ZZZ ===
presence {"AAA": ["2026-08-18"], "ZZZ": ["2026-08-18"]}
processed_days ['2026-08-18']
fetch_calls ['2026-08-18']

=== c1 both tickers received 2026-08-18 ===
presence {"SPY": ["2026-08-17", "2026-08-18"], "QQQ": ["2026-08-17", "2026-08-18"]}
processed_days ['2026-08-17', '2026-08-18']
fetch_calls ['2026-08-18']
after_older_restore {"SPY": ["2026-08-17", "2026-08-18"], "QQQ": ["2026-08-17"]}
processed_still ['2026-08-17', '2026-08-18']

=== c2 nightly incremental does not refill the restored-away row ===
presence {"SPY": ["2026-08-17", "2026-08-18", "2026-08-19"], "QQQ": ["2026-08-17", "2026-08-19"]}
processed_days ['2026-08-17', '2026-08-18', '2026-08-19']
fetch_calls ['2026-08-19']
incremental {'days_fetched': 1, 'already_current': None, 'blocked': None, 'days_remaining': 0}

=== rebuild-state union ===
scanned ['2026-08-18']
presence_before_retry {"SPY": ["2026-08-18"], "QQQ": []}

=== rebuild sealed the day from SPY alone; QQQ stays empty ===
presence {"SPY": ["2026-08-18"], "QQQ": []}
processed_days ['2026-08-18']
fetch_calls []

=== e calendar ===
trading_days ['2026-08-17', '2026-08-18', '2026-08-19']
stamped_dates ['2026-08-18']
n_rows 2 n_tickers 2

=== f fence ===
result {'blocked': 'store_absent'}
fetch_calls []
presence {"SPY": ["2026-08-17"], "QQQ": ["2026-08-17"]}
processed_days ['2026-08-17']

=== audit one-day split ===
exit 0 n_failed 0 n_flags 0
failed []
flags []
```

`b1` prints QQQ as `[]` because `load_ticker` swallows an unreadable parquet and returns an empty frame (`:765-768`). The file is still the garbage bytes. `b2` restores the pre-session bytes and shows the sealed date is not rewritten; 2026-08-19 is fetched because it was not in the set.

The log lines from the run:

```
massive_stock_day: QQQ.parquet unreadable (Could not open Parquet input source '<Buffer>': Parquet magic bytes not found in footer. Either the file is corrupted or this is not a parquet file.) — left untouched rather than overwritten with this day's rows
massive_stock_day backfill: refusing to run — 2 parquet(s) on disk (< 100) while the committed resume state claims 1 processed day(s)
```

## Smallest detector

There is no per-day completeness check. Not a row-count floor, not a ticker-count against the previous session, not a comparison of anchor dates against each other.

Add the check in `backfill`, after `_parse_day` and before `processed.add`. Pseudo-code only:

```
ANCHORS = {SPY, QQQ, IWM, DIA, AAPL, MSFT,
           XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY}
MIN_ROWS = 8000          # a normal day_aggs file is about 12_000 rows

def accept_day(raw, d) -> bool:
    if raw.empty:
        # Seal only when the object is genuinely absent AND d is a
        # weekend-or-full-close holiday (lib.nyse_calendar already knows
        # the holiday set; the collector does not consult it today).
        # A 403, a parse error, and a zero-row file must stay OUT of
        # processed_days. fetch_aggs has to surface that distinction
        # instead of returning DataFrame().
        return object_absent(d) and is_full_close(d)
    tickers = set(map(str, raw["ticker"]))
    missing = ANCHORS - tickers
    if len(raw) < MIN_ROWS or missing:
        log.error("SHORT_DAY %s rows=%d missing_anchors=%s",
                  d, len(raw), sorted(missing))
        return False
    return True

# in the loop, after the upserts:
if any upsert returned "untouched":
    do not processed.add(d)     # _upsert_ticker must grow a bool return
elif accept_day(raw, d):
    processed.add(d)
else:
    days_failed += 1            # retried next run; not a holiday
```

`_upsert_ticker` returning False on the swallowed read is required. Otherwise a short-but-acceptable frame that fails nine reads is still sealed.

A read-side scan the owner can run once, without waiting for the write-path change: for the anchor set above, read each parquet's date index and report dates that are in the union and not in the intersection. One missing business day is enough to report. Do not route that report through `massive_max_gap_bdays` (the limit of 5 is why this session is quiet).

## Smallest repair

The key is `processed_days` inside `massive_stock_day/_backfill_state.json`. Remove the single string `"2026-08-18"`. Leave every other date. `last_captured_date` is rewritten from `max(processed)` on the next save; editing only the scalar does nothing, because resume uses the set.

Clear it on the **R2 object**. The collect job runs `fetch_r2` before `run_incremental`, and a differing R2 state file replaces the git sidecar (`scripts/fetch_r2.py:87-99`). Clearing only `data/massive_stock_day/_backfill_state.json` in git is undone at the start of the next collect. After the re-fetch, the normal commit (`git add data/`, `.github/workflows/daily.yml:638`) and the normal publish write the healed sidecar back.

Do not run `--rebuild-state` first. The union scan puts the date back (repro `rebuild`).

Order:

1. Confirm the nine parquets read. If one is still unreadable, restore that object from the last good R2 generation before the re-fetch. A still-unreadable file is skipped and the date is sealed again (repro `b1`).
2. Delete `"2026-08-18"` from R2 `processed_days`.
3. Re-run the collector for that date only: `backfill(start=date(2026, 8, 18), end=date(2026, 8, 18))`, or the nightly `run_incremental`, which will select it as a one-day interior hole. Upsert dedups by date, keep last, so the six names that already have the row are safe.
4. Before publish, read the nine indexes and require 2026-08-18. If the vendor file still omits them, `accept_day` must reject the frame. Until that check exists, do not let a re-run seal the same short file: stop after inspecting the fetched frame, and leave the date out of `processed_days`. The Grey Deer panel exclusion (D15, exactly `{"2026-08-18"}`) stays until a complete file is actually in every panel parquet.

Publish is the existing `python -m scripts.publish_r2 --dirs massive_stock_day`, and only after the nine rows are present. A publish of the current mixed tree just freezes the hole, which is the state the store is already in.
