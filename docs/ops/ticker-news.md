# Low-Latency Ticker News R1 — Operator Activation

Status: **BUILT_NOT_PROVEN / DARK BY DEFAULT**.

This runbook activates the source/store side of the per-ticker News rail implemented
by Macro PR #8454 and Terminal PR #831. It does not grant source rights, buy a feed,
or authorize a production release. Source rights, provider credentials, merge/release,
and production acceptance remain separate gates.

The additive shared-news implementation and its separate activation/proof gates are
recorded in [Shared news intelligence](shared-news-intelligence.md). Its optional
publisher receipts do not supersede the source-rights requirements below.

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

From the service checkout, as root:

    cd /opt/macro && sudo /opt/macro-api/.venv/bin/python \
      scripts/ticker_news_inventory.py \
      --database /var/lib/macro-ticker-news/qbus.sqlite3 \
      --health /var/lib/macro-ticker-news/health.json

The state directory is root-only (`StateDirectoryMode=0700`; the service runs
as root), so run the command as root from the service checkout, for example
`cd /opt/macro && sudo /opt/macro-api/.venv/bin/python scripts/ticker_news_inventory.py --database ... --health ...`.
Without root it exits 2 with `{"error":"database_unreadable"}`. Any sidecars
it creates are then owned by root, like the files the service itself creates.

状态目录仅 root 可访问（`StateDirectoryMode=0700`，服务以 root 运行），因此应在
服务检出目录以 root 运行该命令，例如 `cd /opt/macro && sudo /opt/macro-api/.venv/bin/python scripts/ticker_news_inventory.py --database ... --health ...`。
不以 root 运行时退出码为 2，并打印 `{"error":"database_unreadable"}`。命令创建
的任何伴随文件归 root 所有，与服务自身创建的文件一致。

`--json` is the default and prints schema `ticker_news.inventory.v1`.
`--text` prints a short English and Chinese summary. `--now <iso>` fixes the
clock used for `generated_at` and for the health projection. A missing
database exits 2 and prints `{"error":"database_missing"}`. The path is not
created.

`--json` 为默认输出，模式为 `ticker_news.inventory.v1`。`--text` 打印简短的
中英摘要。`--now <iso>` 固定 `generated_at` 与健康投影所用的时钟。数据库
不存在时退出码为 2，并打印 `{"error":"database_missing"}`，且不会创建该文件。

The database is opened with SQLite `mode=ro` and `query_only`. While the
writer is running, the report reads the existing WAL, so uncheckpointed
deliveries are included, and it does not rewrite the `-wal` or `-shm`
siblings. Against a cleanly closed store, a run creates a 0-byte `-wal` and
a 32 KiB `-shm` (the wal-index), and both remain after the command exits
because a read-only connection cannot remove them; the database file's
bytes and mtime are still unchanged. The store path is percent-encoded
into the read-only URI for both the report and the embedded cluster audit,
so a path holding spaces, `?`, `#`, `%`, quotes or non-ASCII characters
opens exactly the named file and creates nothing beside it (other than the
`-wal`/`-shm` siblings described above).

数据库以 SQLite `mode=ro` 与 `query_only` 打开。写入进程仍在运行时，报告读取
已有的 WAL，因此未 checkpoint 的送达也会计入，且不会改写 `-wal` 或 `-shm`。
对一个已干净关闭的库，一次运行会创建 0 字节的 `-wal` 和 32 KiB 的 `-shm`
（wal-index），且两者在命令退出后依然留存，因为只读连接无法删除它们；数据
库文件的字节与修改时间仍然保持不变。库存报告与内嵌聚类审计都把数据库路径
百分号编码进只读 URI，因此包含空格、`?`、`#`、`%`、引号或非 ASCII 字符的
路径只会打开指定的文件，不会在其旁边创建任何其他文件（除上文所述的
`-wal`/`-shm` 伴随文件外）。

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

`--universe <path>` and `--rights <path>` are both optional. When one is
omitted, its section reports `state: unavailable` with a reason
(`universe_path_unset`, `rights_path_unset`); an unusable input reports
`universe_unreadable` or `rights_unavailable`. `--rights` accepts the
committed approved receipt file and is read with audience `site_full`.

`--universe <path>` 与 `--rights <path>` 均为可选。省略时对应小节报告
`state: unavailable` 及原因（`universe_path_unset`、`rights_path_unset`）；
输入不可用时报告 `universe_unreadable` 或 `rights_unavailable`。
`--rights` 读取已提交的批准回执文件，按 `site_full` 受众校验。

Each new section carries `known_at`, the report clock (`--now`) rendered
as UTC to whole seconds; `generated_at` keeps its ISO-8601 form.

每个新小节都带 `known_at`，即报告时钟（`--now`）取整到秒的 UTC 表示；
`generated_at` 保持原有 ISO-8601 形式。

`universe` mirrors the API owner's qualification of the same file:
`state` (`qualified` or `held`), `revision`, `asof`; three counts:
`qualified` (qualified securities), `excluded` (excluded securities) and
`ambiguous_aliases` (aliases shared by more than one qualified security);
and `reason_codes`, the distinct snapshot-level hold codes. The inventory
prints them sorted, while the qualification itself keeps them in
first-seen order. `reason_codes` is not a per-security count and carries
no counts. Ownership metadata, aliases and security ids are never printed.

`universe` 小节与 API 层对同一文件的资质判定一致：`state`（`qualified`
或 `held`）、`revision`、`asof`；三个计数：`qualified`（合格证券数）、
`excluded`（排除证券数）与 `ambiguous_aliases`（被多于一只合格证券共用
的别名个数）；以及 `reason_codes`，即去重后的快照级 hold 原因代码。库存
按排序输出，而资质判定本身按首次出现顺序保留。`reason_codes`
不是逐证券计数，也不携带数量。不输出属主、别名或 security id。

`cluster_summary` counts `stories` (rows of `news_cluster_members`),
`clusters` (the union of `news_clusters.cluster_id` and
`news_cluster_members.cluster_id`, so a zero-member cluster counts once
and an orphan member id counts as a cluster), `multi_member_clusters`,
and `size_histogram` keyed by size in ascending numeric order. These
match `audit_store` on the same database.

`cluster_summary` 统计 `stories`（`news_cluster_members` 行数）、
`clusters`（`news_clusters.cluster_id` 与 `news_cluster_members.cluster_id`
的并集，因此零成员聚类计一次，孤儿成员 id 也计为一个聚类）、
`multi_member_clusters` 与按大小数值升序的 `size_histogram`。这些值与
同一数据库上的 `audit_store` 一致。

`cluster_summary.audit` embeds the read-only cluster audit as counts only
(`near_misses_listed`, `near_miss_list_limit`, `number_mismatch_pairs`,
`number_mismatch_clusters`); story ids, cluster ids and similarity values
stay out of the report. The audit runs while `stories` is at most
`AUDIT_STORY_CAP = 3000`, measured on host ubuntu1 on 2026-10-12: a full
report with the audit included took 4.10 s at 3000 stories (0.12 s at 500,
0.47 s at 1000, 1.77 s at 2000, 11.17 s at 5000), and the 5000-story
report with the audit skipped took 0.06 s. Over the cap the section says
`skipped` with `story_count_over_cap` and carries the hand-run command:

    python3 scripts/qbus_news_cluster_audit.py --store <path>

The command is printed with a literal `<path>` placeholder, never the
store path, so the report does not echo where the store lives; substitute
the store that was inventoried when running it.

`cluster_summary.audit` 只内嵌聚合计数（`near_misses_listed`、
`near_miss_list_limit`、`number_mismatch_pairs`、`number_mismatch_clusters`）；
story id、cluster id 与相似度不会进入报告。`stories` 不超过
`AUDIT_STORY_CAP = 3000` 时审计随报告运行，该上限于 2026-10-12 在主机
ubuntu1 上测得：3000 条时含审计的完整报告耗时 4.10 秒（500 条 0.12 秒、
1000 条 0.47 秒、2000 条 1.77 秒、5000 条 11.17 秒），5000 条跳过审计的
报告耗时 0.06 秒。超过上限时小节报告 `skipped` 与 `story_count_over_cap`，
并带手动运行命令：

    python3 scripts/qbus_news_cluster_audit.py --store <path>

该命令以字面 `<path>` 占位符输出，绝不输出存储路径，因此报告不会回显
数据库所在位置；实际运行时请将其替换为本次库存所用的数据库。

`flow_read_latency` measures in-process `store.news_flow` reads, not
HTTP: the network and API layers are not measured. The sample holds the
10 qualified securities with the largest 7-day report counts, listed
alphabetically by ticker; 50 reads run round-robin over the sample.
`p50_ms`, `p95_ms` and `max_ms` are nearest-rank values rounded to 0.1 ms.
States are `measured`, `no_reports_7d`, `unavailable` (with one of
`universe_path_unset`, `universe_unreadable`, `universe_unqualified`,
`rights_path_unset`, `rights_unavailable`) and `failed`
(`flow_call_failed`). Only tickers and counts are printed. The `--text`
line carries the same label, `in-process, not HTTP / 进程内读取，非 HTTP`,
after the sampled tickers.

`flow_read_latency` 度量进程内 `store.news_flow` 读取，而非 HTTP：
网络与 API 层不在度量范围。样本为 7 天报道数最大的 10 只合格证券，
按代码字母序列出；50 次读取在样本上轮转。`p50_ms`、`p95_ms` 与
`max_ms` 为就近取秩（nearest-rank）值，保留 0.1 毫秒精度。状态为
`measured`、`no_reports_7d`、`unavailable`（原因为
`universe_path_unset`、`universe_unreadable`、`universe_unqualified`、
`rights_path_unset`、`rights_unavailable` 之一）与 `failed`
（`flow_call_failed`）。只输出代码与计数。`--text` 输出行在抽样代码之后
也带有同样的标签 `in-process, not HTTP / 进程内读取，非 HTTP`。

No `--verify` mode exists: the runtime health receipt holds only process
counters (scripts/run_qbus_news.py:183-206), so there is no store count
in it to compare against.

不存在 `--verify` 模式：运行健康回执只含进程计数器
（scripts/run_qbus_news.py:183-206），其中没有可与库存对比的存量计数。
