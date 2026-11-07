# CRYPTO T22 observation capture (2026-10-12)

Prep only. The writer is the R2 collector on candidate `#8050` `fd8095012e91`, already hooked into the nightly `okx` and `bgeo` adapters. This lane does not add a daemon, a ledger, a workflow, or a historical backfill. Display-tier capture ships on the existing nightly collect. Nothing here promotes a receipt into authority.

Search bounds for negative claims are named inline. The word for absent data is unavailable.

## Census

`collectors/_crypto_observations.py` (249 lines) is not an adapter. It records one public HTTP response that `OkxAdapter.fetch` or `BgeoAdapter.fetch` already made.

What it captures. Three registered scopes (`SOURCES`, lines 28-32):

| source_id | provider dir | endpoint |
|---|---|---|
| `okx_funding` | `okx` | `https://www.okx.com/api/v5/public/funding-rate-history` |
| `okx_taker` | `okx` | `https://www.okx.com/api/v5/rubik/stat/taker-volume` |
| `bgeo_funding` | `bgeo` | `https://bitcoin-data.com/v1/funding-rate` |

Call sites: `collectors/okx.py:104` (funding page), `:201` (daily taker), `:227` (hourly taker); `collectors/bgeo.py:112-113` (only the `funding-rate` metric, and only after `raise_for_status` and `r.json()`). `recording_run` (lines 216-223) arms capture for the duration of `fetch`. A call outside that window returns `{'status':'inactive'}` and does not write (`record_response`, line 227).

Receipt identity. `build_capture` (lines 92-106) stores one row. `capture_id` is sha256 of the canonical JSON of every other column (lines 100-105, rechecked at 123-124). Content hashes are `payload_sha256` (canonical allowlisted payload) and `body_sha256` (raw response bytes, or null). The clock is the caller-supplied receive time: `received_at`, `first_seen`, and `fetched_at` are the same stamp (line 103) and `checked` rejects a mismatch (line 114). Adapters pass `observations.now_utc()` (`okx.py:102`, `:199`, `:225`; `bgeo.py:106`), which is `datetime.now(timezone.utc)` (lines 49-50). That is a local knowledge bound, not provider publication (module docstring lines 4-5). `provider_first_published_at`, `unit`, `timestamp_role`, and `finality` are forced null (line 104). `checked` rejects a non-null value (lines 121-122). The collector does not self-certify semantics it does not have.

Where it writes. `capture_path` (lines 128-130): `{root or config.data_dir()}/{okx|bgeo}/source_observations.parquet`. `config.yml:47` sets `data_dir: data`, so the nightly paths are `data/okx/source_observations.parquet` and `data/bgeo/source_observations.parquet`. `persist_capture` (lines 133-155) takes a non-blocking exclusive lock on the sibling `source_observations.lock`, refuses an unreadable store, and appends through `collectors/_first_seen_store.accrue_keep_first` keyed by `capture_id`. A present-but-unreadable store returns `{'status':'unavailable','error_type':...}` and leaves the file bytes alone (lines 140, 156-159; `read_store` returns None when present but unreadable, `_first_seen_store.py:34-48`).

Retention. No delete, no TTL, no store-level row cap. `MAX_ROWS = 10000` (line 26) bounds one response, not the file. Keep-first is append-only (`_first_seen_store.py:119-127`).

Corrections. A later payload is a new `capture_id`. Both rows stay. The same `capture_id` with the same bytes returns `already_present` (lines 146-149). A same id with different bytes raises, which `persist_capture` turns into `unavailable` and does not replace the file. There is no in-place update.

Derived read. `funding_asof` (lines 181-213) projects `okx_funding` rows with `http_status==200`, `code=='0'`, and `instId==BTC-USDT-SWAP` into one event per `(instrument, settlement_at)`, keeping the later `received_at`. It does not delete the earlier receipt. Same `received_at` and a different raw row sets `status=conflicting_capture` and nulls both rates (lines 211-212). A settlement after the receive clock sets `status=receipt_before_settlement` and nulls `settled_rate` (line 209). `interval_hours` is always null (line 206).

Scheduling grep. `grep -rn -E "collectors[./]" .github/workflows/*.yml | head -40` (2026-10-12, this worktree) returns path filters and comments (`ci.yml` `collectors/**`, `asia-close.yml` comments). The pipe exits 141 because `head` closes it. No hit is a crypto collector cron. A second search, `.github/workflows/*.yml` for `--group crypto`, returns no matches.

Who consumes the receipt store. Search of `*.py` for `funding_asof(`, `load_asof(`, `source_observations.parquet`, and `capture_path(`: the only crypto hits are `collectors/_crypto_observations.py` and `tests/test_crypto_collectors.py`. Unrelated names exist (`engine/track_record.py:_load_asof`, neural-web `capture_path`, `engine/neuralweb/liquidity_plumbing.py` `funding_asof` as a date string). `scripts/build_crypto.py` and `scripts/build_vector.py` do not reference the module. The series the builders already read are different objects: `engine/btc_inputs.py:43-51` reads `store.read("bgeo", "funding_rate")`; `engine/btc_intraday_cvd.py:55-58` reads `store.read("okx", "taker_volume_hourly")`; `scripts/build_crypto.py:36-37` reads `store.read(group, name)`. A null receipt store does not block those series.

## 1. Admission path

The existing lane is `.github/workflows/daily.yml` job `collect` (job key at line 125).

- Cadence: cron `30 22 * * *` and `30 23 * * *` (lines 36-37), the 18:30 ET pair. `et_gate` keeps one of them. Not hourly.
- Command: `python -m scripts.collect --exclude-group asia --exclude sam_gov_opportunities --skip-shadow-importance` (line 384).
- Lane env on that step: `COLLECT_LANE: nightly` (lines 365-367).
- Why okx and bgeo are inside that command: `scripts/collect.py:310-312` registers both adapters. `--exclude-group asia` drops only `china*` / `hk*` keys (`group_members`, lines 407-409, applied at 586-588). `okx` and `bgeo` are not in that prefix, so they run.
- The named `crypto` shard (`_CRYPTO`, lines 384-386) is not the admission path. The comment at lines 382-383 says that shard is inert until a workflow references it. No workflow references `--group crypto` (search bound above). Do not enable it. A second shard would be a new schedule.

`persist_capture` does not read `COLLECT_LANE`. The gate is which workflow calls `fetch`. These workflows do not:

- `btc-live.yml` (lines 1-7, 59) writes `site/live/quotes.json` hourly. It does not run `scripts.collect`.
- `closing-bell.yml` lines 11-13 exclude `scripts.collect` and name nightly as the sole advancer of `data/` forward ledgers. Lines 16-18 discard every `data/` write except two snapshot pointers. It runs `build_vector` (line 433) and does not capture.
- House law, `CLAUDE.md:117`: nightly is the sole advancer of forward ledgers; intraday lanes discard `data/` writes.

No new daemon. No new ledger. No undocumented backfill. The first committed receipt row is the start of this evidence. Earlier settlements are unavailable, not zeroes, and are not reconstructed from the legacy metric parquets.

## 2. Receipt identity, and why a configured task is not running evidence

A row is one occurrence, not one settlement. Identity material is every column except `capture_id` (`checked`, lines 123-124). Two responses that differ in payload, params, receive time, or HTTP status are two rows.

Configured-but-not-running is not evidence. These are not proof that capture started:

- The daily cron and the `okx` / `bgeo` registry entries.
- `data/run_status.json` (`config.yml:52`) field `sources.okx.status` or `sources.bgeo.status` equal to `ok`. `scripts/collect.py:934-949` writes `FetchResult` via `asdict`. That status is the series upsert. `tests/test_crypto_collectors.py:306-315` shows a funding frame with `fetch_result_status=='stale'` and no observation file when the endpoint does not match. `bgeo.py:69-93` can return other metrics after skipping `funding-rate` without calling `record_response`.
- `adapter.source_capture_status` after the process exits. It is in-memory (line 244).

Proof that capture started: a row in `data/okx/source_observations.parquet` or `data/bgeo/source_observations.parquet` whose `schema` is `crypto.public_response_observation.v1` and whose `capture_id`, `received_at`, and `source_id` survive `checked`. File absent means capture has not started, or every attempt failed before a successful append. Those two are not the same fact. Today only the in-memory record separates them, and only when `record_response` actually ran.

That file is repo evidence only after the collect job commits it. `daily.yml:622` runs the data commit only when `steps.collectors.outcome == 'success'`. The step does `git add data/` (`daily.yml:638`) and does not unstage `data/okx` or `data/bgeo` (the reset at lines 648-663 is hk/china/capital-structure). `git check-ignore -v` on `data/okx/source_observations.parquet` and `data/bgeo/source_observations.parquet` prints no rule, so a successful collectors step would stage a new receipt file. `git ls-tree -r --name-only origin/main -- data/okx data/bgeo` lists the legacy metric parquets and does not list `source_observations.parquet` (the writer is not on main). A red collectors step skips this commit; the salvage step under it is the cboe chain, not these receipts. A parquet written in a failed run dies with the checkout.

`persist_capture` also creates `source_observations.lock` beside the parquet (line 137). That path is not gitignored either, so the same `git add data/` can stage the lock file. Accrual, not a patch in this lane: ignore or delete the lock before commit. Do not treat the lock as a receipt.

## 3. First-available record

A correction never overwrites the first receipt. The stored shape is the `COLUMNS` tuple (lines 36-38), one dict per occurrence:

```
capture_id, schema, source_id, endpoint, params_json, payload_json,
payload_sha256, body_sha256, received_at, first_seen, fetched_at,
http_status, row_count, provider_first_published_at, unit,
timestamp_role, finality
```

On the first receipt, `first_seen == received_at == fetched_at`, `provider_first_published_at` is null, `unit` is null, `timestamp_role` is null, `finality` is null. `payload_json` is the allowlisted public body (`FUNDING_FIELDS` / taker triplets / `BGEO_FIELDS`, lines 34-35 and 61-86). Secrets and unknown keys are dropped before the hash (`PARAMS`, line 33; tests pin this in `tests/test_crypto_collectors.py`).

Keep-first mechanics: `accrue_keep_first` concatenates existing rows then new rows and `drop_duplicates(subset=key, keep="first")` (`_first_seen_store.py:125-126`). The key is `capture_id`, which already includes the first payload and the first `first_seen`. A later correction is a different key, so it is an additional row. Re-sending the first receipt returns `already_present` and does not append. `funding_asof` may display the later revision at a later as-of; the parquet still contains the first row. Contract: `tests/test_crypto_observations_contract.py::test_correction_preserves_first_available`.

Do not add a column. `capture_id` covers every column, so a schema change rewrites identity and breaks `checked`.

## 4. Missing intervals and capture failures

Visible on the current artifact, with these field names:

- Missing settlement inside one captured page. `payload_json` contains only the `fundingTime` values the provider returned. `funding_asof` emits one event per captured settlement. Each event has `settlement_at`, `interval_hours` (null), and `status` (`observed`, `receipt_before_settlement`, or `conflicting_capture`). The missing timestamp is absent from `payload_json` and from `settlement_at`. `interval_hours` stays null so the hole is not filled with an invented 8h step. Inventing that step would self-certify a semantic `checked` forbids (lines 121-122). Contract: `test_missing_interval_is_visible`.
- Capture failure that reaches `record_response`. Return value and `source_capture_status[]` carry `status=unavailable` and `error_type=<exception class name>` plus `source_id` on the adapter list (lines 243-244). No payload, URL, or exception string is stored (lines 156-159). `fetch_result_status` (line 249) returns `stale`. `collectors/base.py:676-686` copies a non-null declared status onto `FetchResult.status`, which `scripts/collect.py:934-949` writes to `data/run_status.json` as `sources.<adapter>.status`. A failed append does not replace an earlier receipt. One class-name loss is real: `accrue_keep_first` catches a write error, logs it, and returns 0 (`_first_seen_store.py:137-139`). `persist_capture` then fails the readback check (lines 152-154) and records `error_type=ValueError`, not the original `OSError`. The failure is not stored as success. Contract: `test_capture_failure_is_recorded_not_hidden`.

Not visible today, and not to be papered over with a zero:

- `bgeo.py:88-89` swallows a per-metric exception after a log line. A `funding-rate` failure before line 113 never calls `record_response`. If any other metric returned a frame, `fetch_result_status` stays null and the adapter can finish `ok`.
- `bgeo.py:91-93` logs a quota or budget skip and does not append a capture status. `funding-rate` is 8th in `config.yml:2208-2218`. A skip before that entry leaves no receipt and no `source_capture_status` row.
- `okx.py:60-65` swallows an exception from `_taker_volume_hourly`. `http_get` raises before `record_response` at line 227, so a dead hourly pull does not mark `okx_taker` unavailable.
- `error_type` is not copied into `FetchResult.notes` (`base.py:698-705`). After the process exits, `run_status` shows `stale` or `ok` without the class name. The in-memory list is gone.

The patches in section 6 record those three misses as `source_capture_status` entries and copy `status`, `source_id`, and `error_type` into `notes`. They do not add a parquet column and they do not synthesize missing settlements.

## 5. Maturity, and the return path

An unknown outcome is not mature.

- `status=receipt_before_settlement` means the settlement is after the receive clock. `settled_rate` is null (line 209). The predicted rate is not the outcome. Contract: `test_unknown_future_outcome_is_not_mature`.
- A blank realized rate stays null (`_rate`, lines 174-178). It is not replaced by `fundingRate` and not replaced by zero.
- `status=conflicting_capture` nulls both rates (lines 211-212). Neither side is chosen.
- `unit`, `timestamp_role`, `finality`, and `provider_first_published_at` null means those facts are unavailable. They are not mature inputs.
- `interval_hours` null means the interval is unavailable. It is not an 8h fact.

The parent reads the same nightly parquet through `load_asof` and `funding_asof`. There is no second watcher, no maturity cron, and no closing-bell reader. `build_vector` on `closing-bell.yml:433` runs on a lane that discards `data/` writes and does not collect; it must not grow a capture loop. `btc_inputs` and `btc_intraday_cvd` keep reading the legacy metric parquets. A receipt is not a market verdict and is not an input to `engine/btc_decision.py` or `engine/btc_signals.py`. Research R1–R9 stays unpromoted. No score, no size, no execution authority.

## 6. Owner edits and accrual

No edit to `.github/`, `scripts/collect.py`, `scripts/build_crypto.py`, `scripts/build_vector.py`, or `engine/btc_decision.py`. Admission is already the nightly collect. A builder read on the closing-bell lane would be a second surface on a lane that discards `data/` writes.

Patches, not applied on this branch (the integrator applies them):

| patch | file | edit |
|---|---|---|
| `research/crypto_science/patches/cx-t22p-20261012__bgeo.py.patch` | `collectors/bgeo.py` | On a `funding-rate` exception before `record_response`, and when `funding-rate` is in the skip list, append `{status: unavailable, error_type, source_id: bgeo_funding}`. `error_type` is the exception class name, or `SkippedBeforeRequest` for a skip. No exception string. |
| `research/crypto_science/patches/cx-t22p-20261012__okx.py.patch` | `collectors/okx.py` | The hourly `except` at lines 64-65 appends the same shape with `source_id: okx_taker`. |
| `research/crypto_science/patches/cx-t22p-20261012__base.py.patch` | `collectors/base.py` | After `notes` is built (`:698-705`), append `source_capture_unavailable:<source_id>:<error_type>` for each unavailable `source_capture_status` item so `data/run_status.json` `sources.<adapter>.notes` keeps the class name. |

Effect the integrator is accepting: `fetch_result_status` (line 249) then sets the adapter `stale` even when other series frames succeeded. That is the same rule `tests/test_crypto_collectors.py:264-270` already pins for a failed `persist_capture`. Series values are still returned. The status stops reading `ok`.

Accrual that stays explicit, with no patch:

- No backfill of `source_observations.parquet` from legacy `funding_rate` or taker parquets. Days before the first receipt row are unavailable.
- No new `--group crypto` workflow, daemon, or ledger.
- No 8h gap synthesizer and no new parquet column.
- No promotion of `funding_asof` into `btc_decision`, `btc_signals`, or a score.
- No display wiring in `build_crypto` / `build_vector` in this prep. The parent return path is a read of the nightly parquet, not a new process.
- Store growth is unbounded except the per-response `MAX_ROWS`. A retention cap is a later decision, not a silent delete.
- `source_observations.lock` is not gitignored and can ride `git add data/`. It is not a receipt.
- The three patches are unverified until applied. This lane's test covers the R2 collector as it stands, not the patched skip paths.
