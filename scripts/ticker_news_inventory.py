"""Read-only inventory of the ticker-news sqlite store.

Operators use this to see which transports have delivered, how fresh those
deliveries are, store totals, cursors, and the projected runtime-health
state. The command never writes the database, never creates a missing file,
and never uses the network or a credential.

With ``--universe`` and ``--rights`` the report adds a universe read-out, a
cluster summary (with a capped hand-off to the cluster audit), and an
in-process flow-read latency sample. Those sections say ``unavailable``
with a reason when their input is not given or not usable.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import datetime, timezone
import json
import math
import sqlite3
import stat
import sys
import time
from pathlib import Path
from typing import Callable, Sequence

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.qbus_news_receipts import load_health_receipt, load_rights_receipt
from engine.qbus_news_store import NewsStore, NewsStoreError, StoreSchemaError
from engine.qbus_news_universe import qualify_universe
from engine.qbus_news_velocity import compute_news_velocity
from scripts.qbus_news_cluster_audit import AuditError, audit_store

SCHEMA = "ticker_news.inventory.v1"
_UNSET_HEALTH = {"state": "unavailable", "reason": "health_path_unset"}

# Measured on host ubuntu1 (python 3.12.3, TZ=UTC) on 2026-10-12: a full
# report with the cluster audit included took 0.12 s at 500 stories, 0.47 s
# at 1000, 1.77 s at 2000, 4.10 s at 3000 and 11.17 s at 5000, while the
# 5000-story report with the audit skipped took 0.06 s. 3000 is the largest
# measured n whose full report stays <= 5.0 s (half of the 10 s target, as
# margin for the loaded 2-vCPU production host).
AUDIT_STORY_CAP = 3000

# The over-cap hand-run line. It carries a literal <path> placeholder so the
# report never echoes where the store lives.
AUDIT_HAND_RUN = "python3 scripts/qbus_news_cluster_audit.py --store <path>"

_TRANSPORTS_SQL = """
SELECT transport,
       COUNT(*) AS deliveries,
       MIN(received_at) AS first_received_at,
       MAX(received_at) AS last_received_at
FROM news_deliveries
GROUP BY transport
ORDER BY transport ASC
"""

_TOTALS_SQL = """
SELECT
  (SELECT COUNT(*) FROM news_revisions) AS revisions,
  (SELECT COUNT(*) FROM news_states) AS states,
  (SELECT COUNT(*) FROM news_states WHERE status='active') AS open_states,
  (SELECT COUNT(*) FROM news_states WHERE status='withdrawn') AS withdrawn_states,
  (SELECT COUNT(*) FROM news_clusters) AS clusters,
  (SELECT COUNT(*) FROM news_changes) AS changes
"""

_CURSORS_SQL = """
SELECT source_key, cursor
FROM news_cursors
ORDER BY source_key ASC
"""

_CLUSTER_STORIES_SQL = """
SELECT COUNT(*) AS stories FROM news_cluster_members
"""

# Sizes over the union of news_clusters.cluster_id (size 0 when a cluster has
# no member) and every news_cluster_members.cluster_id (an orphan member id
# counts as a cluster), matching scripts/qbus_news_cluster_audit.py.
_CLUSTER_SIZES_SQL = """
SELECT cluster_id, SUM(is_member) AS size
FROM (
    SELECT cluster_id, 0 AS is_member FROM news_clusters
    UNION ALL
    SELECT cluster_id, 1 AS is_member FROM news_cluster_members
)
GROUP BY cluster_id
"""


class InventoryError(RuntimeError):
    """Stable operator-facing refusal. The code is the whole message."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _parse_now(value: str) -> datetime:
    raw = value.strip()
    if not raw:
        raise InventoryError("invalid_now")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise InventoryError("invalid_now") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InventoryError("invalid_now")
    try:
        return parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        raise InventoryError("invalid_now") from None


def _clock(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _zulu(value: datetime) -> str:
    """Render one instant as the ``known_at`` clock: UTC, whole seconds."""

    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _audit_section(
    database: Path | str, stories: int, audit_cap: int
) -> dict[str, object]:
    """Project the cluster audit as counts only, or hand it off over the cap.

    The hand-run command carries a ``<path>`` placeholder so the report
    never echoes the store path.
    """

    if stories > audit_cap:
        return {
            "state": "skipped",
            "reason": "story_count_over_cap",
            "stories": stories,
            "cap": audit_cap,
            "hand_run": AUDIT_HAND_RUN,
        }
    try:
        audited = audit_store(Path(database))
    except AuditError as exc:
        return {"state": "failed", "reason": exc.code}
    return {
        "state": "ran",
        "near_misses_listed": len(audited["near_misses"]),
        "near_miss_list_limit": 50,
        "number_mismatch_pairs": len(audited["joined_with_number_mismatch"]),
        "number_mismatch_clusters": len(
            {
                str(row["cluster_id"])
                for row in audited["joined_with_number_mismatch"]
            }
        ),
    }


def build_inventory(
    *,
    database: Path | str,
    health: Path | str | None,
    now: datetime,
    universe: Path | str | None = None,
    rights: Path | str | None = None,
    audit_cap: int = AUDIT_STORY_CAP,
    flow_reads: int = 50,
    flow_tickers: int = 10,
    timer: Callable[[], float] = time.perf_counter,
) -> dict[str, object]:
    """Build one ``ticker_news.inventory.v1`` report. Raises InventoryError."""

    if now.tzinfo is None or now.utcoffset() is None:
        raise InventoryError("invalid_now")
    current = now.astimezone(timezone.utc)
    known_at = _zulu(current)
    path = Path(database)
    try:
        # Use stat directly: recent Python versions make exists()/is_file()
        # suppress permission errors, which would mislabel an unreadable store.
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise InventoryError("database_unreadable")
        size = info.st_size
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise InventoryError("database_missing") from exc
    except OSError as exc:
        raise InventoryError("database_unreadable") from exc

    try:
        store = NewsStore.open_readonly(path, source_key="ticker-news-inventory")
    except StoreSchemaError as exc:
        raise InventoryError("schema_mismatch") from exc
    except NewsStoreError as exc:
        raise InventoryError("database_unreadable") from exc
    try:
        try:
            transport_rows = store._conn.execute(_TRANSPORTS_SQL).fetchall()
            totals_row = store._conn.execute(_TOTALS_SQL).fetchone()
            cursor_rows = store._conn.execute(_CURSORS_SQL).fetchall()
            stories = int(
                store._conn.execute(_CLUSTER_STORIES_SQL).fetchone()["stories"]
            )
            size_rows = store._conn.execute(_CLUSTER_SIZES_SQL).fetchall()
        except sqlite3.Error as exc:
            raise InventoryError("database_unreadable") from exc

        # (a) universe: mirror app/ticker_news.py's load-and-qualify shape.
        qualified = None
        universe_gate: str | None = None
        if universe is None:
            universe_report: dict[str, object] = {
                "state": "unavailable",
                "reason": "universe_path_unset",
                "known_at": known_at,
            }
            universe_gate = "universe_path_unset"
        else:
            try:
                payload = json.loads(
                    Path(universe).read_text(encoding="utf-8")
                )
                if not isinstance(payload, Mapping):
                    raise ValueError("universe payload is not an object")
                qualified = qualify_universe(payload, asof=now)
            except (OSError, ValueError):
                universe_report = {
                    "state": "unavailable",
                    "reason": "universe_unreadable",
                    "known_at": known_at,
                }
                universe_gate = "universe_unreadable"
            else:
                universe_report = {
                    "state": qualified.status,
                    "revision": qualified.revision,
                    "asof": _zulu(qualified.asof),
                    "qualified": len(qualified.securities),
                    "excluded": len(qualified.excluded),
                    "ambiguous_aliases": len(qualified.ambiguous_aliases),
                    "reason_codes": sorted(qualified.reason_codes),
                    "known_at": known_at,
                }
                if qualified.status != "qualified":
                    universe_gate = "universe_unqualified"

        # (b) cluster summary: same union semantics as audit_store.
        sizes = {str(row["cluster_id"]): int(row["size"]) for row in size_rows}
        histogram: dict[str, int] = {}
        for cluster_size in sizes.values():
            histogram[str(cluster_size)] = (
                histogram.get(str(cluster_size), 0) + 1
            )
        cluster_report: dict[str, object] = {
            "stories": stories,
            "clusters": len(sizes),
            "multi_member_clusters": sum(1 for s in sizes.values() if s > 1),
            "size_histogram": {
                key: histogram[key]
                for key in sorted(histogram, key=lambda item: int(item))
            },
            "audit": _audit_section(database, stories, audit_cap),
            "known_at": known_at,
        }

        # (c) flow-read latency: in-process store.news_flow reads.
        if universe_gate is not None:
            flow_report: dict[str, object] = {
                "state": "unavailable",
                "reason": universe_gate,
                "known_at": known_at,
            }
        elif rights is None:
            flow_report = {
                "state": "unavailable",
                "reason": "rights_path_unset",
                "known_at": known_at,
            }
        else:
            receipt = load_rights_receipt(
                rights, now=current, audience="site_full"
            )
            if receipt is None:
                flow_report = {
                    "state": "unavailable",
                    "reason": "rights_unavailable",
                    "known_at": known_at,
                }
            else:
                read_rights = receipt.rights
                try:
                    sample: list[tuple[object, int]] = []
                    for security in qualified.securities:
                        velocity = compute_news_velocity(
                            store._conn,
                            security_id=security.security_id,
                            now=now,
                            allowed_sources=read_rights.allowed_sources,
                        )
                        count_7d = int(velocity["count_7d"])
                        if count_7d >= 1:
                            sample.append((security, count_7d))
                    sample.sort(key=lambda pair: (-pair[1], pair[0].ticker))
                    sample = sample[:flow_tickers]
                    if not sample:
                        flow_report = {
                            "state": "no_reports_7d",
                            "reads": 0,
                            "known_at": known_at,
                        }
                    else:
                        read_ms: list[float] = []
                        for index in range(flow_reads):
                            target = sample[index % len(sample)][0]
                            before = timer()
                            store.news_flow(
                                target.security_id, now=now, rights=read_rights
                            )
                            read_ms.append((timer() - before) * 1000.0)
                        read_ms.sort()

                        def percentile(x: float) -> float:
                            rank = math.ceil(x / 100.0 * len(read_ms))
                            return read_ms[rank - 1]

                        ordered = sorted(sample, key=lambda pair: pair[0].ticker)
                        flow_report = {
                            "state": "measured",
                            "reads": len(read_ms),
                            "tickers": [pair[0].ticker for pair in ordered],
                            "reports_7d": {
                                pair[0].ticker: pair[1] for pair in ordered
                            },
                            "p50_ms": round(percentile(50.0), 1),
                            "p95_ms": round(percentile(95.0), 1),
                            "max_ms": round(read_ms[-1], 1),
                            "method": (
                                "in-process store.news_flow reads; "
                                "not HTTP; nearest-rank percentiles"
                            ),
                            "known_at": known_at,
                        }
                except Exception:
                    flow_report = {
                        "state": "failed",
                        "reason": "flow_call_failed",
                        "known_at": known_at,
                    }
    finally:
        store.close()

    transports = [
        {
            "transport": str(row["transport"]),
            "deliveries": int(row["deliveries"]),
            "first_received_at": _clock(row["first_received_at"]),
            "last_received_at": _clock(row["last_received_at"]),
        }
        for row in transport_rows
    ]
    if health is None:
        health_report: dict[str, object] = dict(_UNSET_HEALTH)
    else:
        health_report = load_health_receipt(health, now=current)

    return {
        "schema": SCHEMA,
        "generated_at": current.isoformat(),
        "database": {"path": path.name, "bytes": int(size)},
        "transports": transports,
        "totals": {
            "revisions": int(totals_row["revisions"]),
            "states": int(totals_row["states"]),
            "open_states": int(totals_row["open_states"]),
            "withdrawn_states": int(totals_row["withdrawn_states"]),
            "clusters": int(totals_row["clusters"]),
            "changes": int(totals_row["changes"]),
        },
        "cursors": [
            {"source_key": str(row["source_key"]), "cursor": str(row["cursor"])}
            for row in cursor_rows
        ],
        "health": health_report,
        "universe": universe_report,
        "cluster_summary": cluster_report,
        "flow_read_latency": flow_report,
        "rest_catchup_proven": any(
            "rest" in item["transport"] and item["deliveries"] >= 1
            for item in transports
        ),
    }


def format_text(report: dict[str, object]) -> str:
    """Short bilingual operator summary. Field names stay aligned with JSON."""

    database = report["database"]
    totals = report["totals"]
    health = report["health"]
    lines = [
        "Ticker news inventory / 个股新闻库存",
        f"schema / 模式: {report['schema']}",
        f"generated_at / 生成时间: {report['generated_at']}",
        (
            f"database / 数据库: {database['path']} "
            f"({database['bytes']} bytes / 字节)"
        ),
        "transports / 传输:",
    ]
    transports = report["transports"]
    if not transports:
        lines.append("  none / 无")
    else:
        for row in transports:
            lines.append(
                "  {transport}: deliveries / 送达数={deliveries} "
                "first / 最早送达={first} last / 最近送达={last}".format(
                    transport=row["transport"],
                    deliveries=row["deliveries"],
                    first=row["first_received_at"] or "null",
                    last=row["last_received_at"] or "null",
                )
            )
    lines.append(
        "totals / 合计: "
        f"revisions / 修订={totals['revisions']} "
        f"states / 状态={totals['states']} "
        f"open_states / 在册状态={totals['open_states']} "
        f"withdrawn_states / 撤回状态={totals['withdrawn_states']} "
        f"clusters / 聚类={totals['clusters']} "
        f"changes / 变更={totals['changes']}"
    )
    lines.append("cursors / 游标:")
    cursors = report["cursors"]
    if not cursors:
        lines.append("  none / 无")
    else:
        for row in cursors:
            lines.append(f"  {row['source_key']}: {row['cursor']}")
    lines.append(f"health / 运行健康: {health.get('state')} ({health.get('reason')})")
    catchup = health.get("last_successful_catchup")
    if catchup:
        lines.append(f"last_successful_catchup / 最近成功补齐: {catchup}")
    stream_at = health.get("last_stream_event_at")
    if stream_at:
        lines.append(f"last_stream_event_at / 最近流事件: {stream_at}")
    flag = "yes / 是" if report["rest_catchup_proven"] else "no / 否"
    lines.append(f"rest_catchup_proven / REST补齐已送达: {flag}")
    universe = report["universe"]
    if universe["state"] == "unavailable":
        lines.append(
            f"universe / 股票池: unavailable/不可用 ({universe['reason']})"
        )
    else:
        lines.append(
            "universe / 股票池: {state} qualified/合格 {qualified} "
            "excluded/排除 {excluded} ambiguous/歧义 {ambiguous} "
            "revision/版本 {revision} asof/截至 {asof}".format(
                state=universe["state"],
                qualified=universe["qualified"],
                excluded=universe["excluded"],
                ambiguous=universe["ambiguous_aliases"],
                revision=universe["revision"],
                asof=universe["asof"],
            )
        )
    summary = report["cluster_summary"]
    lines.append(
        f"clusters / 聚类: {summary['clusters']} "
        f"multi-member/多成员 {summary['multi_member_clusters']} "
        f"stories/条目 {summary['stories']}"
    )
    audit = summary["audit"]
    if audit["state"] == "ran":
        lines.append(
            "cluster audit / 聚类审计: near misses/近似未合并 {near} "
            "number mismatches/数字不符 {pairs} pairs/对 "
            "in {clusters} clusters/聚类".format(
                near=audit["near_misses_listed"],
                pairs=audit["number_mismatch_pairs"],
                clusters=audit["number_mismatch_clusters"],
            )
        )
    elif audit["state"] == "skipped":
        lines.append(
            "cluster audit skipped / 聚类审计已跳过: "
            "stories/条目 {stories} > cap/上限 {cap}; "
            "run/手动运行: {hand_run}".format(
                stories=audit["stories"],
                cap=audit["cap"],
                hand_run=audit["hand_run"],
            )
        )
    else:
        lines.append(f"cluster audit failed / 聚类审计失败: {audit['reason']}")
    flow = report["flow_read_latency"]
    if flow["state"] == "measured":
        lines.append(
            f"flow reads / 流量读取: p50 {flow['p50_ms']} ms "
            f"p95 {flow['p95_ms']} ms max {flow['max_ms']} ms "
            f"over/共 {flow['reads']} reads/次; "
            f"tickers / 抽样代码: {', '.join(flow['tickers'])}"
            "; in-process, not HTTP / 进程内读取，非 HTTP"
        )
    elif flow.get("reason") is None:
        lines.append(f"flow reads / 流量读取: {flow['state']}")
    else:
        lines.append(f"flow reads / 流量读取: {flow['state']} ({flow['reason']})")
    return "\n".join(lines) + "\n"


def _write_stdout(text: str) -> None:
    payload = text if text.endswith("\n") else text + "\n"
    sys.stdout.write(payload)
    sys.stdout.flush()


def _emit_error(code: str) -> int:
    _write_stdout(json.dumps({"error": code}, separators=(",", ":")))
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only ticker-news inventory. "
            "只读个股新闻库存：按传输统计送达与新鲜度，不写数据库、不访问网络。"
        )
    )
    parser.add_argument(
        "--database",
        required=True,
        help="SQLite store path. Opened read-only. 数据库路径，只读打开。",
    )
    parser.add_argument(
        "--health",
        default=None,
        help=(
            "Optional runtime health receipt. "
            "可选运行健康回执；省略时 state=unavailable, reason=health_path_unset。"
        ),
    )
    parser.add_argument(
        "--now",
        default=None,
        help=(
            "Timezone-aware ISO-8601 clock for generated_at and health. "
            "带时区的 ISO-8601 时间，用作生成时间与健康投影时钟。"
        ),
    )
    parser.add_argument(
        "--universe",
        default=None,
        help=(
            "Optional qualified universe snapshot for the universe and "
            "flow sections. "
            "可选股票池快照，用于股票池与流量读取小节；"
            "省略时对应小节为 unavailable 并给出原因。"
        ),
    )
    parser.add_argument(
        "--rights",
        default=None,
        help=(
            "Optional approved rights receipt for the flow section. "
            "可选已批准的权利回执，用于流量读取小节；"
            "省略或失效时对应小节为 unavailable 并给出原因。"
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--json",
        action="store_true",
        help="Print JSON (default). 输出 JSON（默认）。",
    )
    mode.add_argument(
        "--text",
        action="store_true",
        help="Print a short English and Chinese summary. 输出简短中英摘要。",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        now = (
            datetime.now(timezone.utc)
            if args.now is None
            else _parse_now(args.now)
        )
        report = build_inventory(
            database=args.database,
            health=args.health,
            now=now,
            universe=args.universe,
            rights=args.rights,
        )
    except InventoryError as exc:
        return _emit_error(exc.code)
    if args.text:
        _write_stdout(format_text(report))
    else:
        _write_stdout(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=False)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
