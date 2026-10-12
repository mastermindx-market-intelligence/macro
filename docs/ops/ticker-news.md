# Low-Latency Ticker News R1 — Operator Activation

Status: **BUILT_NOT_PROVEN / DARK BY DEFAULT**.

This runbook activates the source/store side of the per-ticker News rail implemented
by Macro PR #8454 and Terminal PR #831. It does not grant source rights, buy a feed,
or authorize a production release. Source rights, provider credentials, merge/release,
and production acceptance remain separate gates.

## Ownership

| Concern | Existing owner |
| --- | --- |
| Provider observations / revisions / history | qbus |
| S&P 500 membership | breadth constituent + PIT membership datasets |
| Security identity / aliases | Data OS security master + vendor aliases |
| Source rights | source-rights / contract owner |
| Runtime process | systemd on the Macro API VPS |
| API auth / product entitlement | existing Macro API / Terminal auth owners |
| Browser presentation | Mastermind Terminal |
| GMI related-subtheme context | GMI, deferred from R1 direct-news activation |

There is exactly one live news writer. `macro-api` receives read-only access to the
qbus hot store and the qualified rights receipt; it never receives the provider key.

## Required commercial-rights evidence

Do not create an `approved` receipt from API possession alone. The contract/order or
other current source-rights owner must positively establish the uses below.

The current R1 architecture requires these capabilities to be **true**:

- `internal_ingestion`
- `historical_retention`
- `headline_display`

These remain separately explicit and default-deny when missing:

- `source_link_display`
- `teaser_display`
- `body_display`
- `image_display`
- `derivative_processing`

R1 does not display provider body text or images. Later LLM enrichment must not be
enabled merely because R1 headline display is licensed; derivative/model processing
has its own receipt field and later acceptance.

If historical retention is not licensed, **do not arm this service**. Redesign the
persistence policy first rather than weakening the receipt gate.

## Root-only activation files

Two operator-owned files are required on the Macro API VPS.

### `/etc/macro-ticker-news.env`

Mode: `0600`, owner: root, exactly one provider-token line:

    BENZINGA_API_KEY=<licensed commercial newsfeed token>

Do not put this key in `/etc/macro-api.env`. The API unit explicitly hides this file.

### `/etc/macro-ticker-news-rights.json`

Mode: `0600`, owner: root. Template:

    {
      "schema": "qbus.news_rights_receipt.v1",
      "receipt_id": "<unique owner receipt id>",
      "owner_ref": "<contract / order / approved-rights evidence ref>",
      "status": "approved",
      "source": "benzinga",
      "product_id": "<exact licensed Benzinga product/account>",
      "audiences": ["site_full"],
      "effective_at": "2026-10-06T00:00:00+00:00",
      "expires_at": "<actual rights expiry or review boundary>",
      "capabilities": {
        "internal_ingestion": true,
        "historical_retention": true,
        "headline_display": true,
        "source_link_display": true,
        "teaser_display": false,
        "body_display": false,
        "image_display": false,
        "derivative_processing": false
      }
    }

Use the contract's actual scope. Do not copy the booleans above as an assertion of
rights. Missing, malformed, future, expired, wrong-source, wrong-audience, or denied
receipts fail closed.

The receipt is re-read continuously by the writer and on every API access. Revoking,
expiring, or replacing it with a non-qualified receipt stops new ingestion and
withholds display without changing source code.

## Network-dark preflight

From the production VPS, after the merged/released source is present at `/opt/macro`:

    sudo /opt/macro/app/deploy/ticker-news-setup.sh --check

This action:

1. serializes with the existing `macro-update` lock;
2. requires root-owned `0400` or `0600` activation files;
3. verifies the production Python runtime includes the synchronous WebSocket client;
4. rebuilds the exact current S&P universe from the incumbent breadth + Data OS owners;
5. verifies the provider token is present;
6. validates current site-full source rights;
7. validates the universe is current and complete;
8. opens **no provider connection**;
9. creates **no live database** and **no health claim**.

A passing check is activation readiness, not production proof.

## Install disabled

After the network-dark check passes:

    sudo /opt/macro/app/deploy/ticker-news-setup.sh --install

This installs the reviewed `macro-ticker-news.service` and reloads systemd, but does
not enable or start it. If a writer is already active, install refuses; disarm first
rather than hot-swapping the unit under a live process.

Routine `macro-update` deployments never install or enable an absent ticker-news
service. Once an operator has installed it, the updater may reconcile the reviewed
unit and restart an **already-active** writer when import-cached code or canonical
universe inputs change.

## Explicit arm

Only after rights, source code, runtime, and release approval are all current:

    sudo /opt/macro/app/deploy/ticker-news-setup.sh --arm

`--arm` performs the same activation check and reviewed-unit install, then explicitly
runs `systemctl enable --now macro-ticker-news.service`.

Startup activation refusals use exit code 2 and are in
`RestartPreventExitStatus=2`, so missing/expired rights or other operator
prerequisites cannot cause a five-second restart storm. Transport/runtime failures
may restart. A mid-run rights revocation exits cleanly and remains stopped.

## Status and logs

Status is observational:

    sudo /opt/macro/app/deploy/ticker-news-setup.sh --status
    sudo systemctl status macro-ticker-news.service --no-pager
    sudo journalctl -u macro-ticker-news.service -n 100 --no-pager

Runtime state lives in the private systemd state directory:

- `/var/lib/macro-ticker-news/qbus.sqlite3`
- `/var/lib/macro-ticker-news/news_universe.json`
- `/var/lib/macro-ticker-news/health.json`

The API has read-only access to that state and to the rights receipt. It has no access
to `/etc/macro-ticker-news.env`.

## Canary acceptance

A canary is not production acceptance. At minimum capture:

1. exact Macro + Terminal release SHAs;
2. service `MainPID`, active state, and current health receipt;
3. exact universe revision and count;
4. authenticated Terminal snapshot for a covered ticker;
5. one synthetic/controlled correction path;
6. one controlled removal path;
7. restart + REST catch-up proof;
8. rights downgrade proof;
9. browser News rail proof;
10. rollback proof.

Never paste provider payload bodies or credentials into GitHub evidence. Metadata,
IDs, clocks, counts, digests, and redacted headlines are sufficient.

## Natural proof

Final R1 acceptance still requires the plan's natural-market evidence: at least five
actual trading sessions, including an event/earnings burst, with measured source
quality, duplicate escape rate, ticker-routing precision, correction/removal
behavior, source/publication-to-receipt clocks where trustworthy, and truthful
freshness during an upstream interruption.

Synthetic load evidence proves implementation capacity only.

## Rollback / disarm

Immediate source stop:

    sudo /opt/macro/app/deploy/ticker-news-setup.sh --disarm

Then verify:

    systemctl is-active macro-ticker-news.service
    systemctl is-enabled macro-ticker-news.service

Both must report inactive/disabled semantics before considering the writer stopped.

Do not delete the qbus store as part of ordinary rollback. Preserve it under the
applicable source-rights retention/deletion policy so corrections, removals, and
audit evidence are not silently lost.

## Current external gate

At source publication time, the local development environment had no repo-level
secret names for Benzinga/Massive/Polygon/ticker-news rights. Organization-level
secret presence could not be inspected with the current GitHub credential and
remains **unknown**. The source therefore makes no claim that a production credential
or commercial display right already exists.

## Alpaca provider (Benzinga content via Alpaca)

The default provider remains **benzinga** (direct Benzinga key). Alpaca is a
second, opt-in transport whose news feed is Benzinga content, so the content
source stays Benzinga everywhere downstream (store, rights, API, Terminal) and
only the provider/transport changes. Nothing about the Benzinga path changes
unless the operator explicitly switches.

Activation is a root act on the Macro API VPS, in the existing env file
`/etc/macro-ticker-news.env` (mode 0600, root-owned):

    QBUS_NEWS_PROVIDER=alpaca
    ALPACA_API_KEY_ID=<key id>
    ALPACA_API_SECRET_KEY=<secret key>

Exactly one `ALPACA_API_KEY_ID=` line and exactly one `ALPACA_API_SECRET_KEY=`
line; `ticker-news-setup.sh` refuses duplicates, empty values, or any provider
value other than `benzinga`/`alpaca`. The rights file for this provider is
`config/ticker_news_rights_alpaca_benzinga.json`, installed to
`/etc/macro-ticker-news-rights.json`, after which the existing
`ticker-news-setup.sh --check` / `--install` / `--arm` flow applies unchanged.

Operator notes:

- Alpaca publishes **no removal feed**: removals and corrections that Benzinga
  delivers via its removal endpoint are never delivered on this provider.
- Never switch providers over a populated store: the cursor namespaces differ
  (`benzinga-rest` vs `alpaca-rest`) and back-switching mixes clock domains.
- One WebSocket connection per key pair; the Alpaca stream handshake
  authenticates over the socket and never places credentials in a URL.

### Fail-closed item handling

One contract-invalid item is never skipped: it fails its whole REST page (the
catch-up counts `catchups_failed` and holds the cursor) or its whole WS frame
(a stream error; the next catch-up — periodic or after the reconnect —
re-serves the frame-mates whose `updated_at` falls within the cursor − 3 s
overlap). This mirrors the incumbent Benzinga collector. Operator triage is
the typed code — `news_item_<code>` from a REST page, `stream_<code>` from a
WS frame — raised as `alpaca_news:<code>` when the failing page or frame is
replayed, with the health file and the journal's exit receipts showing the
stall as rising `catchups_failed` / `stream_errors` counts. A persistent one
stalls the cursor and needs an engineering fix, never a provider switch.

## Inventory / 库存

Operators can answer whether REST catch-up has delivered, which transports
have delivered, and how fresh each one is, with one read-only command. The
command does not open a network connection, does not read credentials, and
does not write the store.

运营者可以用一条只读命令查看 REST 补齐是否已经送达、各传输分别送达了多少、
以及每条传输有多新。该命令不访问网络、不读取凭证、不写入数据库。

From a checkout of this repo:

    python scripts/ticker_news_inventory.py \
      --database /var/lib/macro-ticker-news/qbus.sqlite3 \
      --health /var/lib/macro-ticker-news/health.json

`--json` is the default and prints schema `ticker_news.inventory.v1`.
`--text` prints a short English and Chinese summary. `--now <iso>` fixes the
clock used for `generated_at` and for the health projection. A missing
database exits 2 and prints `{"error":"database_missing"}`. The path is not
created.

`--json` 为默认输出，模式为 `ticker_news.inventory.v1`。`--text` 打印简短的
中英摘要。`--now <iso>` 固定 `generated_at` 与健康投影所用的时钟。数据库
不存在时退出码为 2，并打印 `{"error":"database_missing"}`，且不会创建该文件。

The database is opened with SQLite `mode=ro` and `query_only`. A run leaves
the database file's bytes and mtime unchanged. While the writer is running,
the report reads the existing WAL, so uncheckpointed deliveries are included,
and it does not rewrite the `-wal` or `-shm` siblings. If those siblings are
already absent, SQLite may create empty ones beside the database; the
database file itself is still not modified.

数据库以 SQLite `mode=ro` 与 `query_only` 打开。运行后数据库文件的字节与
修改时间保持不变。写入进程仍在运行时，报告读取已有的 WAL，因此未 checkpoint
的送达也会计入，且不会改写 `-wal` 或 `-shm`。若这两个伴随文件已经不存在，
SQLite 可能会在数据库旁创建空的伴随文件；数据库文件本身仍然不会被修改。

Fields / 字段:

- `schema` — `ticker_news.inventory.v1`. 报告模式。
- `generated_at` — UTC timestamp of this report. 本报告的 UTC 时间。
- `database.path` — file basename only. 仅文件名，不含目录。
- `database.bytes` — size of that file in bytes. 该文件的字节大小。
- `transports` — one row per stored transport string, not a normalized name.
  `deliveries` is the number of `news_deliveries` rows. `first_received_at`
  and `last_received_at` are the earliest and latest stored receipt times.
  每个按原样存储的传输名一行，不做名称归一。`deliveries` 是送达行数。
  `first_received_at` 与 `last_received_at` 是最早和最近的送达时间。
- `totals.revisions`, `totals.states`, `totals.clusters`, `totals.changes` —
  row counts of those tables. 对应表的行数。
- `totals.open_states` — `news_states` rows with status `active`.
  状态为 `active` 的行数。
- `totals.withdrawn_states` — `news_states` rows with status `withdrawn`.
  状态为 `withdrawn` 的行数。
- `cursors` — every `news_cursors` row (`source_key`, `cursor`).
  全部游标行。
- `health` — when `--health` is set, the projection from `load_health_receipt`
  (default observation and catch-up age budgets are 120 seconds). When
  `--health` is omitted, exactly
  `{"state":"unavailable","reason":"health_path_unset"}`.
  提供 `--health` 时，为 `load_health_receipt` 的投影（默认观测与补齐年龄
  上限均为 120 秒）。省略 `--health` 时，固定为
  `{"state":"unavailable","reason":"health_path_unset"}`。
- `rest_catchup_proven` — true only when some stored transport name contains
  the substring `rest` and that transport has at least one delivery. Names are
  compared as stored, including case. WebSocket-only deliveries leave this
  false. 仅当某个按原样存储的传输名包含子串 `rest`（区分大小写）且该传输至少
  有一条送达时为 true。仅有 WebSocket 送达时为 false。

The report never includes titles, teasers, URLs, message bodies, or
`delivery_json`.

报告不包含标题、摘要、URL、消息正文或 `delivery_json`。
