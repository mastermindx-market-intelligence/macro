"""Source-bound early attention, composed from the incumbent Sector Pulse.

This is a current research view, not a forecast, trade score or historical ledger.
The caller supplies the real receipt and assessment clocks. A future input is
excluded BEFORE validation, hashing, counting and presentation. Daily observations
stay daily; this module neither recomputes theme scores nor relaxes confirmation.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import date, datetime, timezone
import hashlib
import json
import math
import re
from typing import Any
from zoneinfo import ZoneInfo

SCHEMA = "catalyst_opportunity.v1"
POLICY = "sector_pulse_attention/1"
MAX_THEMES = 1024
MAX_TEXT = 240
ID = re.compile(r"[a-z][a-z0-9_]{0,95}\Z", re.ASCII)
LABELS = frozenset({"emerging", "dominant", "fading", "deteriorating", "neutral"})
HEATS = frozenset({"heating", "hot", "cooling", "broken", "neutral", "idle"})
AUTHORITY = {key: False for key in (
    "can_rank", "can_size", "can_gate", "can_originate_signal", "can_escalate",
)}
EASTERN = ZoneInfo("America/New_York")
FRESHNESS_POLICY = "date-only; stale after one calendar day; not a market-session SLA"


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _text(value: Any, default: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return default
    value = value.strip()
    if len(value) > MAX_TEXT or any(ord(c) < 32 for c in value):
        return default
    return value


def _number(value: Any, *, minimum=None, maximum=None, integer=False) -> float | int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        if not math.isfinite(value):
            return None
    except (OverflowError, TypeError, ValueError):
        return None
    if minimum is not None and value < minimum:
        return None
    if maximum is not None and value > maximum:
        return None
    if integer and int(value) != value:
        return None
    return int(value) if integer else float(value)


def _absent(reason: str, en: str, zh: str) -> dict:
    return {"status": "unavailable", "reason": reason, "summary": en, "summary_zh": zh}


def _base(now: datetime, reason: str = "SOURCE_UNAVAILABLE") -> dict:
    return {
        "schema": SCHEMA, "policy_version": POLICY, "assessed_at": _iso(now),
        "status": "unavailable", "reason_codes": [reason], "as_of": None,
        "source": None,
        "coverage": {"scope": "us_curated_themes", "declared": None, "observed": 0,
                     "valid": 0, "refused": 0, "watch_count": 0,
                     "complete": False, "not_all_securities": True},
        "cases": [], "inventory": [], "refusals": [], "authority": dict(AUTHORITY),
        "disclaimer": "Research attention only. Not a prediction or an entry recommendation.",
        "disclaimer_zh": "仅用于研究关注，不是预测或入场建议。",
    }


def _seal(view: dict) -> dict:
    # Receipt and assessment clocks are not new market facts.
    identity = {k: v for k, v in view.items() if k not in {"assessed_at", "generation"}}
    if identity["source"] is not None:
        identity["source"] = {k: v for k, v in identity["source"].items() if k != "received_at"}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=True,
                                       separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    view["generation"] = "co:" + digest
    return view


def _metrics(row: Mapping) -> tuple[dict, list[str]]:
    rules = {
        "rel_5d": {}, "pct50": {"minimum": 0, "maximum": 1},
        "rank": {"minimum": 1, "integer": True},
        "rank_delta_1d": {"integer": True}, "rank_delta_5d": {"integer": True},
        "rank_delta_20d": {"integer": True}, "score_delta_5d": {}, "score_delta_20d": {},
        "momentum_score": {"minimum": -1, "maximum": 1},
    }
    values, errors = {}, []
    for field, kwargs in rules.items():
        raw = row.get(field)
        values[field] = _number(raw, **kwargs)
        if raw is not None and values[field] is None:
            errors.append(field)
    return values, errors


def _case(row: Mapping, metrics: dict, observed_date: str, freshness: str) -> dict | None:
    label, heat = row.get("label"), row.get("heat")
    # The source's states, not a newly calibrated opinion or score.
    if label == "emerging" or heat == "heating":
        kind = "emerging_watch"
        reason = "The source reports an emerging or heating theme. Inspect participation and timing."
        reason_zh = "源数据显示主题正在兴起或升温；请核查参与度和时机。"
    elif (label == "dominant" and metrics["rel_5d"] is not None
          and metrics["rel_5d"] > 0 and metrics["pct50"] is not None
          and metrics["pct50"] >= 0.5):
        kind = "leadership_watch"
        reason = "Positive five-session relative performance with at least half the theme above its 50-day average."
        reason_zh = "近五个交易日相对表现为正，且至少半数成分股位于50日均线之上。"
    else:
        return None
    tid = row["id"]
    name = _text(row.get("name"), tid)
    name_zh = _text(row.get("name_zh"), name)
    cautions = [{"code": "DESCRIPTIVE_NOT_PREDICTIVE",
                 "text": "Source strength is descriptive; forward return and entry quality are not established.",
                 "text_zh": "源数据强度仅为描述，尚未证明前瞻收益或入场质量。"}]
    if freshness == "stale":
        cautions.insert(0, {"code": "DATED_OBSERVATION", "text": "Dated observation. Check current prices before interpreting it.",
                            "text_zh": "观测已过期；解读前请核查当前价格。"})
    if heat == "hot":
        cautions.append({"code": "EXTENSION_NOT_CHECKED", "text": "Leadership can already be extended. No entry window has been validated.",
                         "text_zh": "领先主题可能已经过度上涨；尚无经验证的入场窗口。"})
    sector = "defense" if tid == "defense" else "energy" if tid in {"energy_complex", "us_sector_energy"} else "other"
    links = [{"label": "Sector Intelligence", "label_zh": "板块情报",
              "href": "https://www.mastermind-x.com/baskets.html"}]
    if sector == "defense":
        links.append({"label": "Defense / Government Revenue", "label_zh": "国防与政府收入",
                      "href": "https://www.mastermind-x.com/government_revenue.html"})
    return {
        "id": "co:market:" + tid, "theme_id": tid, "name": name, "name_zh": name_zh,
        "category": _text(row.get("category"), "Other"), "sector": sector,
        "origin": "market", "discovery_state": "provisional_watch", "watch_kind": kind,
        "source_label": label, "source_heat": heat, "observation_status": freshness,
        "observed_on": observed_date, "precision": "date", "title": name,
        "summary": reason, "summary_zh": reason_zh, "metrics": metrics,
        "metric_basis": {"rel_5d": "fraction; source five-session benchmark-relative return",
                         "pct50": "fraction; source share above 50-day moving average",
                         "rank": "source order; not an opportunity rank",
                         "momentum_score": "source descriptive multi-timeframe value"},
        "source_refs": [{"owner": "sector_pulse", "theme_id": tid, "as_of": observed_date}],
        "event": _absent("EVENT_NOT_CONNECTED", "No verified event is attached. Market behavior does not prove its cause.",
                         "尚未连接已核实事件；市场表现不能证明其原因。"),
        "economics": _absent("EXPOSURE_NOT_QUALIFIED", "Theme membership is not verified issuer economic exposure.",
                             "主题归属不等于已核实的公司经济暴露。"),
        "entry": _absent("ENTRY_NOT_QUALIFIED", "Open the existing chart and timing tools. This view supplies no buy point.",
                         "请使用现有图表与择时工具；本视图不提供买点。"),
        "cautions": cautions, "links": links, "authority": dict(AUTHORITY),
    }


def build_opportunity_view(pulse: Mapping | None, *, assessed_at: datetime,
                           received_at: datetime | None,
                           source_ref: str = "sector_pulse:us") -> dict:
    """Compose a bounded current research view without mutating any input.

    received_at is the actual caller observation, never the data's as_of date.
    No historical availability is inferred when receipt evidence is absent.
    """
    now = _utc(assessed_at, "assessed_at")
    out = _base(now)
    if received_at is None:
        out["reason_codes"] = ["RECEIPT_UNAVAILABLE"]
        return _seal(out)
    receipt = _utc(received_at, "received_at")
    if receipt > now:
        out["reason_codes"] = ["NOT_YET_AVAILABLE"]
        return _seal(out)
    if pulse is None:
        return _seal(out)
    if not isinstance(pulse, Mapping):
        out["reason_codes"] = ["INVALID_SOURCE"]
        return _seal(out)
    # Exclude future source generations before schema, content and row counts.
    try:
        date_value = pulse.get("as_of", "")
        if not isinstance(date_value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", date_value):
            raise ValueError("date precision")
        observed = date.fromisoformat(date_value)
    except (TypeError, ValueError):
        out["reason_codes"] = ["SOURCE_DATE_UNAVAILABLE"]
        return _seal(out)
    today = now.astimezone(EASTERN).date()
    if observed > today:
        out["reason_codes"] = ["NOT_YET_AVAILABLE"]
        return _seal(out)
    if type(pulse.get("schema")) is not int or pulse["schema"] != 1 or pulse.get("region") != "us":
        out["reason_codes"] = ["UNSUPPORTED_SOURCE_CONTRACT"]
        return _seal(out)
    rows = pulse.get("themes")
    if not isinstance(rows, list) or len(rows) > MAX_THEMES:
        out["reason_codes"] = ["INVALID_SOURCE_POPULATION"]
        return _seal(out)
    age = (today - observed).days
    freshness = "stale" if age > 1 else "current_daily"
    out["as_of"] = observed.isoformat()
    out["source"] = {"owner": "sector_pulse", "reference": _text(source_ref, "sector_pulse:us"),
                     "as_of": observed.isoformat(), "precision": "date", "received_at": _iso(receipt),
                     "age_calendar_days": age, "freshness": freshness,
                     "freshness_policy": FRESHNESS_POLICY, "historical_availability_proven": False}
    ids = Counter(r.get("id") for r in rows if isinstance(r, Mapping) and isinstance(r.get("id"), str))
    valid = 0
    for position, row in enumerate(rows):
        code = None
        tid = row.get("id") if isinstance(row, Mapping) else None
        if not isinstance(tid, str) or not ID.fullmatch(tid):
            code = "INVALID_THEME_ID"
        elif ids[tid] != 1:
            code = "DUPLICATE_THEME_ID"
        elif (not isinstance(row.get("label"), str) or row.get("label") not in LABELS
              or (row.get("heat") is not None and (not isinstance(row.get("heat"), str)
                                                      or row.get("heat") not in HEATS))):
            code = "UNSUPPORTED_THEME_STATE"
        if code:
            out["refusals"].append({"position": position, "reason": code})
            continue
        metrics, missing = _metrics(row)
        if missing:
            out["refusals"].append({"position": position, "reason": "INVALID_METRIC", "fields": missing})
            continue
        valid += 1
        case = _case(row, metrics, observed.isoformat(), freshness)
        out["inventory"].append({"theme_id": tid, "name": _text(row.get("name"), tid),
                                 "name_zh": _text(row.get("name_zh"), _text(row.get("name"), tid)),
                                 "source_label": row.get("label"), "source_heat": row.get("heat"),
                                 "watch": case is not None})
        if case:
            out["cases"].append(case)
    declared = _number(pulse.get("n_themes"), minimum=0, maximum=MAX_THEMES, integer=True)
    complete = declared == len(rows) == valid
    out["coverage"].update({"declared": declared, "observed": len(rows), "valid": valid,
                            "refused": len(out["refusals"]), "watch_count": len(out["cases"]),
                            "complete": complete})
    out["reason_codes"] = []
    if declared is None:
        out["reason_codes"].append("UNKNOWN_POPULATION")
    if valid != len(rows) or (declared is not None and declared != len(rows)):
        out["reason_codes"].append("PARTIAL_POPULATION")
    if freshness == "stale":
        out["reason_codes"].append("DATED_SOURCE")
    out["status"] = ("stale" if freshness == "stale" else "partial" if not complete
                     else "ready" if out["cases"] else "empty")
    return _seal(out)
