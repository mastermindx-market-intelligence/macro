"""Display-only adapter for explicitly supplied event-hedging research artifacts.

No collector, score, scenario calculation or automatic publication. The existing
Options workspace owns rendering. Hashes establish integrity, not market truth.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path

_AUTHORITY = {key: False for key in (
    "calibrated_probability", "actual_dealer_inventory", "executed_flow", "trading",
    "ranking", "portfolio", "sizing", "auto_exit", "can_publish",
)}
_SCHEMAS = {
    "options.event_variance_diagnostic/v1": ("event-variance:", "BASELINE_CONDITIONAL"),
    "options.hedge_path_diagnostic/v1": ("hedge-path:", "SCENARIO"),
}


def load_event_hedging_artifact(path: str) -> dict:
    """Bounded explicit file read; no engine import or implicit source selection."""
    def unique_members(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON member: {key}")
            value[key] = item
        return value

    def reject_constant(value):
        raise ValueError(f"nonfinite JSON constant: {value}")

    with Path(path).open("rb") as handle:
        raw = handle.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("research artifact exceeds 2 MB")
    value = json.loads(raw, object_pairs_hook=unique_members, parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise ValueError("research artifact must be an object")
    return value


def _text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 2048:
        raise ValueError("missing or invalid text")
    return value


def _time(value):
    stamp = datetime.fromisoformat(_text(value).replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("missing clock timezone")
    return stamp.astimezone(timezone.utc)


def _number(value, digits=6):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError("nonfinite diagnostic")
    return f"{value:,.{digits}f}"


def _row(en, zh, value):
    return {"en": en, "zh": zh, "value": value}


def build_event_hedging_view(artifact, *, now: datetime):
    """Return None when not supplied; refuse malformed, future or authority-bearing data.

    Research snapshots remain explicitly historical/non-live regardless of render
    time. Numerical results are owner-produced; this adapter only formats them.
    """
    if artifact is None:
        return None
    result = {"available": False, "kind": "unavailable", "rows": [], "evidence": [],
              "as_of": None, "content_id": None, "reasons": ["artifact_not_qualified"]}
    try:
        if not isinstance(artifact, dict) or artifact.get("schema") not in _SCHEMAS:
            return result
        prefix, evidence_class = _SCHEMAS[artifact["schema"]]
        raw = {key: value for key, value in artifact.items() if key != "content_id"}
        encoded = json.dumps(raw, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if len(encoded) > 2_000_000:
            return result
        digest = prefix + sha256(encoded.encode()).hexdigest()
        if artifact.get("content_id") != digest or artifact.get("authority") != _AUTHORITY:
            return result
        if artifact.get("evidence_class") != evidence_class:
            return result
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            return result
        status = artifact.get("status")
        if status not in {"available", "unavailable"}:
            return result
        reasons = artifact.get("unavailable_reasons")
        if not isinstance(reasons, list) or any(not isinstance(x, str) for x in reasons):
            return result
        if (status == "available") != (not reasons):
            return result
        rows, evidence = [], []
        if artifact["schema"] == "options.event_variance_diagnostic/v1":
            inputs = artifact["inputs"]
            as_of = _text(inputs["as_of"])
            if _time(as_of) > now.astimezone(timezone.utc):
                return result
            kind = "variance"
            for en, zh, key in (("Event", "事件", "event_id"), ("Scheduled time", "计划时间", "event_at")):
                evidence.append(_row(en, zh, _text(inputs[key])))
            observed, baseline = inputs["observed"], inputs["counterfactual"]
            for en, zh, value in (
                ("Instrument", "标的", observed["security_id"]),
                ("Variance basis", "方差口径", observed["variance_basis"]),
                ("Return basis", "收益口径", observed["return_basis"]),
                ("Window start", "窗口起点", observed["window_start"]),
                ("Window end", "窗口终点", observed["window_end"]),
                ("Observed source", "观测来源", observed["source_ref"]),
                ("Observed revision", "观测版本", observed["source_revision"]),
                ("Baseline method", "基准方法", baseline["method_ref"]),
                ("Baseline revision", "基准版本", baseline["source_revision"]),
            ):
                evidence.append(_row(en, zh, _text(value)))
            if status == "available":
                rows = [
                    _row("Excess window variance", "窗口超额方差", _number(artifact["excess_window_variance"], 8)),
                    _row("Isolated event variance", "独立事件方差", _number(artifact["isolated_event_variance"], 8)),
                    _row("Conditional event RMS move (%)", "条件事件均方根波幅（%）", _number(artifact["isolated_event_rms_move_pct"], 3)),
                ]
            extra = artifact["attribution_reasons"]
            if not isinstance(extra, list) or any(not isinstance(x, str) for x in extra):
                return result
            reasons = reasons + extra
        else:
            kind = "path"
            as_of = _text(artifact["as_of"])
            if _time(as_of) > now.astimezone(timezone.utc):
                return result
            if artifact["units"] != {"target_change": "SPX_index_equivalent_units",
                    "reference_notional_usd": "target_SPX_times_change_in_hedge_units"}:
                return result
            if artifact.get("actual_exhaustion_probability") is not None:
                return result
            for en, zh, key in (
                ("Path assumption", "路径假设", "path_ref"),
                ("Checkpoint time", "中间时点", "checkpoint_at"),
                ("Terminal time", "终止时点", "terminal_at"),
                ("Checkpoint receipt", "中间回执", "checkpoint_content_id"),
                ("Terminal receipt", "终止回执", "terminal_content_id"),
            ):
                evidence.append(_row(en, zh, _text(artifact[key])))
            if status == "available":
                rows = [
                    _row("Remaining hedge target (SPX risk units)", "剩余对冲目标（SPX风险单位）", _number(artifact["remaining_target_change"], 3)),
                    _row("Reference notional (USD, not cash flow)", "参考名义金额（美元，非资金流）", _number(artifact["reference_notional_usd"], 2)),
                ]
        return {"available": status == "available", "kind": kind, "rows": rows, "evidence": evidence,
                "as_of": as_of, "content_id": digest, "reasons": reasons}
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        return result
