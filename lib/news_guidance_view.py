"""Presentation of the existing News guidance context, without recomputation.

No data access, model, entity join, ranking or arithmetic. The producer owns
comparison correctness. This boundary only accepts the published display shape
and formats supplied decimal strings. Unsupported measurements stay visible as
unavailable; no currency scale or metric meaning is guessed.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import re
from typing import Any

_NUMBER = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_HORIZON = re.compile(r"^FY([0-9]{4})(?: Q([1-4]))?$")
_MEASUREMENTS = {
    ("vehicle_deliveries", "vehicles"): ("Vehicle deliveries", "汽车交付量", "vehicles", "辆"),
    ("revenue_yoy_pct", "percent"): ("Revenue growth", "营收同比增速", "%", "%"),
}
_FLAGS = ("may_rank", "may_size", "may_gate", "prophet_authority")
_REASONS = {
    "prior_not_supplied": ("No comparable prior guidance.", "暂无可比的先前指引。"),
    "prior_comparable_missing": ("No comparable prior guidance.", "暂无可比的先前指引。"),
    "guidance_absent": ("No supported guidance comparison.", "暂无有据可查的指引对比。"),
    "guidance_withdrawn": ("Guidance was withdrawn; no numeric comparison.", "指引已撤回，不作数值对比。"),
    "measurement_mismatch": ("Guidance measurements are not comparable.", "指引的计量口径不可比。"),
    "measurement_basis_missing": ("A comparable measurement basis is missing.", "缺少可比的计量口径。"),
    "guidance_evidence_invalid": ("Source support could not be verified.", "无法核实来源依据。"),
    "clock_invalid": ("Disclosure timing could not be verified.", "无法核实披露时间。"),
    "guidance_source_clock_missing": ("Disclosure timing could not be verified.", "无法核实披露时间。"),
    "guidance_source_clock_unknown": ("Disclosure timing could not be verified.", "无法核实披露时间。"),
    "guidance_source_clock_invalid": ("Disclosure timing could not be verified.", "无法核实披露时间。"),
    "guidance_source_clock_ambiguous": ("Disclosure timing could not be verified.", "无法核实披露时间。"),
    "revision_order_invalid": ("Disclosure order could not be verified.", "无法核实披露先后顺序。"),
    "event_state_ineligible": ("This event cannot supply a current comparison.", "该事件无法提供当前对比。"),
}
_UNAVAILABLE = ("Guidance comparison unavailable.", "指引对比暂不可用。")


def _stamp(value: Any) -> tuple[datetime, str]:
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("invalid timestamp")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("timestamp has no zone")
    stamp = stamp.astimezone(timezone.utc)
    return stamp, stamp.strftime("%Y-%m-%d %H:%M UTC")


def _number(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 128 or not _NUMBER.fullmatch(value):
        raise ValueError("not a published decimal string")
    integer, dot, fraction = value.partition(".")
    return re.sub(r"(?<=\d)(?=(?:\d{3})+$)", ",", integer) + (dot + fraction if dot else "")


def _amount(value: Any, unit: str) -> str:
    return _number(value) + ("%" if unit == "%" else " " + unit)


def _row(raw: Any, as_of: datetime) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        raise ValueError("row shape")
    metric, unit = raw.get("metric"), raw.get("unit")
    if not isinstance(metric, str) or not isinstance(unit, str) or (metric, unit) not in _MEASUREMENTS:
        raise ValueError("unsupported measurement")
    label, label_zh, suffix, suffix_zh = _MEASUREMENTS[(metric, unit)]
    horizon = raw.get("horizon")
    match = _HORIZON.fullmatch(horizon) if isinstance(horizon, str) else None
    if not match:
        raise ValueError("horizon")
    for field in ("current_low", "current_high", "prior_low", "prior_high", "current_midpoint", "prior_midpoint", "midpoint_delta"):
        _number(raw.get(field))
    delta_unit = "percentage_points" if unit == "percent" else unit
    if raw.get("delta_unit") != delta_unit or raw.get("interpretation") not in ("numeric_difference_only", "source_correction_difference"):
        raise ValueError("comparison semantics")
    evidence = raw.get("evidence")
    if not isinstance(evidence, list) or len(evidence) != 2:
        raise ValueError("evidence shape")
    dates = {}
    for ev in evidence:
        if not isinstance(ev, Mapping) or ev.get("role") not in ("current", "prior") or ev.get("receipt_state") != "byte_replayed":
            raise ValueError("evidence role")
        role = ev["role"]
        if role in dates:
            raise ValueError("ambiguous evidence role")
        available, text = _stamp(ev.get("source_available_at"))
        observed, _ = _stamp(ev.get("observed_at"))
        if not available <= observed <= as_of:
            raise ValueError("evidence timing")
        dates[role] = text
    relative, relative_zh = "", ""
    ratio = raw.get("relative_change_pct")
    if unit == "percent":
        if ratio is not None or raw.get("relative_change_reason") != "rate_comparison_uses_percentage_points":
            raise ValueError("rate semantics")
    elif ratio is not None:
        relative = "Relative to previous midpoint: " + _number(ratio) + "%"
        relative_zh = "相对先前中点：" + _number(ratio) + "%"
    elif raw.get("relative_change_reason") == "zero_prior_midpoint":
        relative, relative_zh = "Previous midpoint is zero; relative change is undefined.", "先前中点为零，无法计算相对变化。"
    else:
        raise ValueError("missing relative-change reason")
    corrected = raw["interpretation"] == "source_correction_difference"
    delta_en, delta_zh = ("percentage point" if raw["midpoint_delta"] in ("1", "-1") else "percentage points", "个百分点") if unit == "percent" else (suffix, suffix_zh)
    def bounds(which: str, ending: str) -> str:
        return _number(raw[which + "_low"]) + "–" + _amount(raw[which + "_high"], ending)
    return {
        "label_en": label, "label_zh": label_zh,
        "horizon_en": horizon, "horizon_zh": match[1] + "财年" + ("第" + match[2] + "季度" if match[2] else ""),
        "prior_en": bounds("prior", suffix), "prior_zh": bounds("prior", suffix_zh),
        "current_en": bounds("current", suffix), "current_zh": bounds("current", suffix_zh),
        "change_en": "Midpoint change: " + _amount(raw["midpoint_delta"], delta_en),
        "change_zh": "中点变化：" + _amount(raw["midpoint_delta"], delta_zh),
        "relative_en": relative, "relative_zh": relative_zh,
        "status_en": "Corrected source" if corrected else "Numeric comparison",
        "status_zh": "来源更正" if corrected else "数值对比",
        "current_source_en": "Current disclosure: " + dates["current"],
        "current_source_zh": "本次披露：" + dates["current"],
        "prior_source_en": "Prior disclosure: " + dates["prior"],
        "prior_source_zh": "先前披露：" + dates["prior"],
    }


def guidance_view(context: Any) -> dict[str, Any] | None:
    """Format trusted-owner public output; None preserves pages without this input."""
    if context is None:
        return None
    out: dict[str, Any] = {"rows": [], "note_en": _UNAVAILABLE[0], "note_zh": _UNAVAILABLE[1],
                           "as_of": "", "unavailable_count": 0, "omitted_count": 0}
    if not isinstance(context, Mapping):
        return out
    flags = context.get("prophet_flags")
    if (context.get("schema") != "news_guidance_context.v1" or context.get("authority") != "context_only"
            or context.get("temporal_basis") != "known_now" or context.get("is_context_only") is not True
            or context.get("display_only") is not True or type(context.get("available")) is not bool
            or not isinstance(flags, Mapping) or set(flags) != set(_FLAGS)
            or any(flags[k] is not False for k in _FLAGS) or context.get("consensus") is not None
            or not isinstance(context.get("comparisons"), list)):
        return out
    try:
        stamp, out["as_of"] = _stamp(context.get("as_of"))
    except (ValueError, TypeError, OverflowError):
        return out
    rows = context["comparisons"]
    if context["available"] is not bool(rows):
        return out
    reasons = context.get("reasons")
    if not rows:
        if isinstance(reasons, list):
            for reason in reasons:
                if isinstance(reason, str) and reason in _REASONS:
                    out["note_en"], out["note_zh"] = _REASONS[reason]
                    break
        return out
    for raw in rows[:64]:
        try:
            row = _row(raw, stamp)
        except (ValueError, TypeError, OverflowError, KeyError):
            out["unavailable_count"] += 1
            continue
        if len(out["rows"]) < 4:
            out["rows"].append(row)
        else:
            out["omitted_count"] += 1
    out["omitted_count"] += max(0, len(rows) - 64)
    if out["rows"]:
        out["note_en"], out["note_zh"] = "", ""
    return out
