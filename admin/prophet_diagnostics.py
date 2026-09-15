"""Read-only operator diagnostics over the existing Prophet miss-audit artifact.

Visibility is not entry actionability. Ticker-ever matching is not on-time delivery.
No writer, ranking, admission, or trading-policy dependency belongs in this module.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any

SOURCE_PATH = Path("data/prophet_miss_audit/latest.json")
INPUT_SCHEMA = "prophet_miss_audit/v1"
OUTPUT_SCHEMA = "prophet.rotation_diagnostics.v1"
MAX_BYTES = 4 * 1024 * 1024
MAX_ROWS = 200
MAX_COUNT = 2**53 - 1  # Exact in the existing JavaScript consumer.
LANES = ("buy", "watch", "leaders", "ran")
INFO_REASON = "legacy_conversion_not_episode_linked"


def _count(value: Any) -> int | None:
    return value if type(value) is int and 0 <= value <= MAX_COUNT else None


def _rate(value: Any) -> float | None:
    if type(value) not in (int, float) or not 0 <= value <= 1:
        return None
    return float(value) if math.isfinite(value) else None


def _date(value: Any) -> str | None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def _mapping(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _text(value: Any, limit: int) -> bool:
    return isinstance(value, str) and 0 < len(value) <= limit and bool(value.strip())


def _empty(reason: str, digest: str | None = None) -> dict:
    return {"schema": OUTPUT_SCHEMA, "authority": "operator_diagnostic_only",
            "available": False, "status": "unavailable", "reasons": [reason],
            "source": {"path": SOURCE_PATH.as_posix(), "sha256": digest},
            "dates": dict.fromkeys(("prices", "board", "rotation", "baskets", "basket_board")),
            "dates_aligned": None, "populations": dict.fromkeys(("universe", "runners_63", "runners_21")),
            "conversion": {"sighted": None, "ever_plan_matched": None, "legacy_rate": None,
                           "basis": "ticker_ever_plan_match", "on_time_rate": None,
                           "on_time_state": "not_measured"}, "baskets": []}


def _baskets(block: dict, reasons: set[str]) -> list[dict]:
    rows = block.get("baskets")
    if block.get("available") is not True:
        reasons.add("basket_source_unavailable")
        return []
    if not isinstance(rows, list):
        reasons.add("basket_invalid_container")
        return []
    if len(rows) > MAX_ROWS:
        reasons.add("basket_count_oversize")
        return []
    ids = [r.get("basket_id") for r in rows if isinstance(r, dict)]
    valid_ids = [v for v in ids if _text(v, 160)]
    if len(valid_ids) != len(set(valid_ids)):
        reasons.add("duplicate_basket_ids")
        return []
    result = []
    for row in rows:
        if not isinstance(row, dict) or not _text(row.get("basket_id"), 160):
            reasons.add("basket_malformed_row")
            continue
        valid = True
        name = row.get("name")
        if not _text(name, 240):
            reasons.add("basket_name_invalid")
            name, valid = row["basket_id"], False
        as_of = _date(row.get("as_of"))
        if as_of is None:
            reasons.add("basket_date_invalid")
            valid = False
        elif _date(block.get("as_of")) and as_of != block["as_of"]:
            reasons.add("basket_date_mismatch")
            valid = False
        counts = {key: _count(_mapping(row.get("present_counts")).get(key)) for key in LANES}
        if any(value is None for value in counts.values()):
            reasons.add("basket_incomplete_counts")
            valid = False
        members = row.get("members_on_board")
        if (not isinstance(members, list) or len(members) > MAX_ROWS
                or not all(_text(m, 64) for m in members)):
            reasons.add("basket_members_invalid")
            members, valid = [], False
        elif len(members) != len(set(members)):
            reasons.add("basket_members_duplicate")
            members, valid = [], False
        recorded_total = _count(row.get("n_members_on_board"))
        if "n_members_on_board" in row and (recorded_total is None or recorded_total != len(members)):
            reasons.add("basket_counts_inconsistent")
            valid = False
        if valid and (max(counts.values()) > len(members) or sum(counts.values()) < len(members)):
            reasons.add("basket_counts_inconsistent")
            valid = False
        visibility = "unknown"
        if valid:
            if counts["buy"] + counts["watch"] > 0:
                visibility = "setup_lane_present"
            elif counts["leaders"] + counts["ran"] > 0:
                visibility = "leader_only"
            else:
                visibility = "not_visible"
        result.append({"basket_id": row["basket_id"], "name": name, "as_of": as_of,
                       "counts": counts, "visibility": visibility,
                       "entry_actionability": "not_measured", "members_on_board": list(members)})
    return sorted(result, key=lambda row: row["basket_id"])


def build_diagnostics(audit: object, *, snapshot_sha256: str | None = None) -> dict:
    """Project a current snapshot; no historical or trade inference is made."""
    if not isinstance(audit, dict):
        return _empty("non_dict_root")
    if audit.get("schema") != INPUT_SCHEMA:
        return _empty("wrong_schema")
    reasons = {INFO_REASON}
    if snapshot_sha256 is not None and (not isinstance(snapshot_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", snapshot_sha256)):
        reasons.add("source_hash_invalid")
        snapshot_sha256 = None
    out = _empty(INFO_REASON, snapshot_sha256)
    out["available"] = True
    summary = _mapping(audit.get("summary"))
    for dest, source in (("universe", "universe_n"), ("runners_63", "top63_n"), ("runners_21", "top21_n")):
        out["populations"][dest] = _count(summary.get(source))
    universe, r63, r21 = out["populations"].values()
    if None in (universe, r63, r21) or r63 > universe or r21 > universe:
        reasons.add("population_inconsistent")
    if universe is not None and universe > 0 and (r63 == 0 or r21 == 0):
        reasons.add("empty_runner_population")
    themes = _mapping(audit.get("themes"))
    baskets = _mapping(audit.get("basket_misses"))
    out["dates"] = {"prices": _date(audit.get("price_through")),
                    "board": _date(themes.get("standouts_asof")),
                    "rotation": _date(themes.get("rotation_asof")),
                    "baskets": _date(baskets.get("as_of")),
                    "basket_board": _date(baskets.get("standouts_asof"))}
    dates = list(out["dates"].values())
    if None in dates:
        reasons.add("dates_incomplete")
    else:
        out["dates_aligned"] = len(set(dates)) == 1
    if len({d for d in dates if d is not None}) > 1:
        reasons.add("mixed_vintages")
    source = _mapping(audit.get("conversion"))
    sighted, matched, rate = _count(source.get("sighted_n")), _count(source.get("converted_n")), _rate(source.get("rate"))
    if sighted is None or matched is None or matched > sighted:
        reasons.add("conversion_unavailable")
        rate = None
    elif sighted == 0:
        if source.get("rate") is not None:
            reasons.add("conversion_inconsistent")
        rate = None
    elif rate is None:
        reasons.add("conversion_unavailable")
    elif abs(rate - matched / sighted) > 0.000050000001:
        reasons.add("conversion_inconsistent")
        rate = None
    out["conversion"].update(sighted=sighted, ever_plan_matched=matched, legacy_rate=rate)
    out["baskets"] = _baskets(baskets, reasons)
    out["reasons"] = sorted(reasons)
    out["status"] = "partial" if reasons - {INFO_REASON} else "available"
    return out


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def read_diagnostics(repo: Path) -> dict:
    """Read bounded exact bytes; reject symlinks and special files, preserve nulls."""
    path = Path(repo) / SOURCE_PATH
    try:
        if path.is_symlink():
            return _empty("source_symlink")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return _empty("source_missing")
    except OSError:
        return _empty("source_unavailable")
    try:
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                return _empty("source_non_regular")
            raw = stream.read(MAX_BYTES + 1)
    except OSError:
        return _empty("source_unavailable")
    if len(raw) > MAX_BYTES:
        return _empty("source_oversize")
    digest = hashlib.sha256(raw).hexdigest()
    try:
        source = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except UnicodeDecodeError:
        return _empty("malformed_utf8", digest)
    except (ValueError, RecursionError):
        return _empty("malformed_or_duplicate_json", digest)
    result = build_diagnostics(source, snapshot_sha256=digest)
    result["source"]["sha256"] = digest
    return result
