"""Read-only inventory of the ticker-news sqlite store.

Operators use this to see which transports have delivered, how fresh those
deliveries are, store totals, cursors, and the projected runtime-health
state. The command never writes the database, never creates a missing file,
and never uses the network or a credential.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sqlite3
import sys
from pathlib import Path
from typing import Sequence

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.qbus_news_receipts import load_health_receipt
from engine.qbus_news_store import SCHEMA as STORE_SCHEMA

SCHEMA = "ticker_news.inventory.v1"
_UNSET_HEALTH = {"state": "unavailable", "reason": "health_path_unset"}

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


def _connect_readonly(path: Path) -> sqlite3.Connection:
    # mode=ro refuses to create the file. query_only refuses writes if the
    # URI flag is ignored by a future sqlite build.
    uri = path.resolve().as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(
            uri,
            uri=True,
            timeout=5.0,
            isolation_level=None,
        )
    except sqlite3.Error as exc:
        raise InventoryError("database_unreadable") from exc
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only=ON")
    except sqlite3.Error as exc:
        conn.close()
        raise InventoryError("database_unreadable") from exc
    return conn


def _require_store_schema(conn: sqlite3.Connection) -> None:
    try:
        row = conn.execute(
            "SELECT value FROM qbus_meta WHERE key='schema'"
        ).fetchone()
    except sqlite3.Error as exc:
        raise InventoryError("database_unreadable") from exc
    if row is None or str(row["value"]) != STORE_SCHEMA:
        raise InventoryError("schema_mismatch")


def _clock(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def build_inventory(
    *,
    database: Path | str,
    health: Path | str | None,
    now: datetime,
) -> dict[str, object]:
    """Build one ``ticker_news.inventory.v1`` report. Raises InventoryError."""

    if now.tzinfo is None or now.utcoffset() is None:
        raise InventoryError("invalid_now")
    current = now.astimezone(timezone.utc)
    path = Path(database)
    try:
        # pathlib re-raises EACCES and friends instead of reporting the
        # path as absent, so an untraversable state directory must map to
        # the same fail-closed refusal as every other unreadable store.
        if not path.exists():
            raise InventoryError("database_missing")
        if not path.is_file():
            raise InventoryError("database_unreadable")

        size = path.stat().st_size
    except OSError as exc:
        raise InventoryError("database_unreadable") from exc

    conn = _connect_readonly(path)
    try:
        _require_store_schema(conn)
        try:
            transport_rows = conn.execute(_TRANSPORTS_SQL).fetchall()
            totals_row = conn.execute(_TOTALS_SQL).fetchone()
            cursor_rows = conn.execute(_CURSORS_SQL).fetchall()
        except sqlite3.Error as exc:
            raise InventoryError("database_unreadable") from exc
    finally:
        conn.close()

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
