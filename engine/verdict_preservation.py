"""Display-tier preserved research verdicts for Calibration Lab (V1)."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_SCHEMA = "mastermind.verdict_preservation_registry.v1"
_STATUS_CLASSES = frozenset(
    {
        "insufficient_support",
        "not_supported",
        "mixed",
        "scoped_null",
        "pit_partial",
        "broken",
        "law",
        "counterfactual",
    }
)
_BADGE_MAP: dict[str, tuple[str, str]] = {
    "insufficient_support": ("Insufficient support", "支持不足"),
    "not_supported": ("Not supported", "未获支持"),
    "mixed": ("Mixed", "好坏参半"),
    "scoped_null": ("No effect in tested scope", "检验范围内无效果"),
    "pit_partial": ("Partial history", "历史不完整"),
    "broken": ("Control broken", "对照失效"),
    "law": ("Display-tier rule", "展示层规则"),
    "counterfactual": ("counterfactual — not a verdict", "反事实 — 非结论"),
}
_ROW_KEYS = (
    "id",
    "verdict_key",
    "program",
    "status_literal",
    "status_class",
    "actual",
    "source_path",
    "source_line",
    "qualifiers_en",
    "qualifiers_zh",
    "plain_en",
    "plain_zh",
    "owner_ref",
    "consume_as",
)
_DNC_EN = [
    "C2 round-1 NOT_SUPPORTED headline",
    "F1 AUC and severe-share figures read as probabilities",
    "D0 E* and week-40 numerics",
    "any Trend Persistence calibrated profile or shadow field",
]
_DNC_ZH = [
    "C2 第一轮 NOT_SUPPORTED 标题结论",
    "将 F1 的 AUC 与严重占比数值当作概率解读",
    "D0 的 E* 与第 40 周数值",
    "任何趋势持续性校准画像或影子字段",
]
_OWNER_REF_RE = re.compile(r"^(WS|DEC|DSC|DNR):[A-Z0-9][A-Z0-9-]*$")


def _unavailable(msg: str, *args: Any) -> dict[str, Any]:
    log.warning(msg, *args)
    return {"available": False}


def _validate_row(row: Any) -> bool:
    if not isinstance(row, dict):
        return False
    for key in _ROW_KEYS:
        if key not in row:
            return False
    if not isinstance(row["id"], str) or not row["id"]:
        return False
    if not isinstance(row["verdict_key"], str):
        return False
    if not isinstance(row["program"], str):
        return False
    if not isinstance(row["status_literal"], str):
        return False
    if row["status_class"] not in _STATUS_CLASSES:
        return False
    if not isinstance(row["actual"], bool):
        return False
    if not isinstance(row["source_path"], str):
        return False
    if not isinstance(row["source_line"], int) or row["source_line"] < 1:
        return False
    for qk in ("qualifiers_en", "qualifiers_zh", "plain_en", "plain_zh", "owner_ref"):
        if not isinstance(row[qk], str):
            return False
    if not _OWNER_REF_RE.fullmatch(row["owner_ref"]):
        return False
    if row["consume_as"] != "display-tier":
        return False
    return True


def _validate_registry(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if data.get("schema") != _SCHEMA:
        return False
    rows = data.get("rows")
    if not isinstance(rows, list) or len(rows) != 8:
        return False
    ids: set[str] = set()
    actual_c2 = 0
    for row in rows:
        if not _validate_row(row):
            return False
        if row["id"] in ids:
            return False
        ids.add(row["id"])
        if row["verdict_key"] == "C2" and row["actual"] is True:
            actual_c2 += 1
    if actual_c2 != 1:
        return False
    dnc_en = data.get("do_not_consume_until_repair")
    dnc_zh = data.get("do_not_consume_until_repair_zh")
    if dnc_en != _DNC_EN or dnc_zh != _DNC_ZH:
        return False
    if not isinstance(data.get("frozen_at"), str):
        return False
    if not isinstance(data.get("source_census"), str):
        return False
    return True


def _pin_ok(root: Path, source_path: str, source_line: int, status_literal: str) -> bool:
    if source_path.startswith("/") or ".." in source_path:
        return False
    resolved = (root / source_path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return False
    try:
        text = resolved.read_text(encoding="utf-8")
    except OSError:
        return False
    lines = text.splitlines()
    if source_line < 1 or source_line > len(lines):
        return False
    return status_literal in lines[source_line - 1]


def build_verdict_preservation(root: Path) -> dict[str, Any]:
    registry_path = root / "config" / "verdict_preservation_registry.json"
    if not registry_path.is_file():
        return _unavailable("verdict_preservation registry not found at %s", registry_path)

    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _unavailable("verdict_preservation registry unreadable: %s", exc)

    if not _validate_registry(data):
        return _unavailable("verdict_preservation registry failed validation")

    out_rows: list[dict[str, Any]] = []
    pin_ok_count = 0
    for row in data["rows"]:
        ok = _pin_ok(root, row["source_path"], row["source_line"], row["status_literal"])
        if ok:
            pin_ok_count += 1
        badge_en, badge_zh = _BADGE_MAP[row["status_class"]]
        out_rows.append(
            {
                **row,
                "pin_ok": ok,
                "anchor": "vp-" + row["id"],
                "badge_en": badge_en,
                "badge_zh": badge_zh,
            }
        )

    return {
        "available": True,
        "schema": data["schema"],
        "frozen_at": data["frozen_at"],
        "source_census": data["source_census"],
        "rows": out_rows,
        "do_not_consume_until_repair": list(data["do_not_consume_until_repair"]),
        "do_not_consume_until_repair_zh": list(data["do_not_consume_until_repair_zh"]),
        "row_count": 8,
        "pin_ok_count": pin_ok_count,
    }
