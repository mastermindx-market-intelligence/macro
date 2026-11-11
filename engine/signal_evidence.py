"""Presentation passports over the canonical BTC impulse gate.

This module owns no model verdict and no registry.  The sole permission resolver
is :func:`engine.btc_impulse_radar.resolve_leg_permission`; this adapter adds
stable Signal Lab anchors plus event/source-window clocks for consumers.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from lib import config

PASSPORT_SCHEMA = "mastermind.signal_evidence_passport.v1"
SOURCE_MAX_AGE_DAYS = 1
_EVENT_DAYS = 3

_SPECS = {
    "d2": {"signal_id": "btc_impulse.d2", "direction": "down",
           "name": "DVOL jolt", "name_zh": "DVOL 波动跳升",
           "anchor": "signal-lab-btc-impulse-d2"},
    "d3": {"signal_id": "btc_impulse.d3", "direction": "down",
           "name": "SOPR profit-take spike", "name_zh": "SOPR 获利了结跳升",
           "anchor": "signal-lab-btc-impulse-d3"},
    "u1": {"signal_id": "btc_impulse.u1", "direction": "up",
           "name": "SOPR capitulation wash-out", "name_zh": "SOPR 投降式洗盘",
           "anchor": "signal-lab-btc-impulse-u1"},
    "d2+d3": {"signal_id": "btc_impulse.d2+d3", "direction": "down",
              "name": "DVOL + SOPR joint trigger", "name_zh": "DVOL + SOPR 联合触发",
              "anchor": "signal-lab-btc-impulse-d2-d3"},
}

_STATUS_TEXT = {
    "eligible": "Current evidence permits use while the event window is open.",
    "demoted": "The current holdout gate demoted this signal.",
    "insufficient_n": "The current holdout sample is too small for action use.",
    "no_data": "The current validation has no usable row for this signal.",
    "gate_missing": "The current validation artifact is missing.",
    "gate_corrupt": "The current validation artifact is unreadable.",
    "gate_unavailable": "The current validation did not complete successfully.",
    "target_mismatch": "The validation target does not match this signal contract.",
    "validation_time_invalid": "The validation date is invalid.",
    "future_validation": "The validation date is after this evaluation.",
    "stale_validation": "The validation is too old for current authority.",
    "evaluation_time_invalid": "The evaluation date is invalid.",
    "unknown_identity": "The signal identity is not recognized.",
    "leg_evidence_malformed": "The measured validation evidence is missing or malformed.",
    "source_time_invalid": "The source-data date is unavailable.",
    "future_source": "The source-data date is after this evaluation.",
    "stale_source": "The source data is too old for current timing use.",
    "unknown_event_time": "The event date is unknown.",
    "future_event": "The event is dated after this evaluation.",
    "expired": "The three-day BTC event window has closed.",
}
_STATUS_ZH = {
    "eligible": "当前证据允许在事件窗口内使用",
    "demoted": "当前留出样本门槛已将该信号降级",
    "insufficient_n": "当前留出样本不足，不得用于行动",
    "no_data": "当前验证没有该信号的可用记录",
    "gate_missing": "当前验证文件缺失",
    "gate_corrupt": "当前验证文件无法读取",
    "gate_unavailable": "当前验证未成功完成",
    "target_mismatch": "验证目标与该信号契约不一致",
    "validation_time_invalid": "验证日期无效",
    "future_validation": "验证日期晚于本次评估",
    "stale_validation": "验证已过期，不具当前权限",
    "evaluation_time_invalid": "评估日期无效",
    "unknown_identity": "信号身份无法识别",
    "leg_evidence_malformed": "验证测量证据缺失或格式错误",
    "source_time_invalid": "源数据日期不可用",
    "future_source": "源数据日期晚于本次评估",
    "stale_source": "源数据过旧，不具当前择时权限",
    "unknown_event_time": "事件日期未知",
    "future_event": "事件日期晚于本次评估",
    "expired": "三日 BTC 事件窗口已关闭",
}


def _as_date(value: Any, *, instant_utc: bool = False) -> date | None:
    if isinstance(value, datetime):
        if instant_utc and value.tzinfo is not None:
            return value.astimezone(timezone.utc).date()
        return value.date()
    if isinstance(value, date):
        return value
    if value is None or value == "":
        return None
    text = str(value).strip()
    if instant_utc and ("T" in text or " " in text):
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                return parsed.astimezone(timezone.utc).date()
        except ValueError:
            pass
    try:
        return date.fromisoformat(text[:10])
    except (TypeError, ValueError):
        return None


def btc_gate_path() -> Path:
    return config.data_dir() / "vector" / "impulse_legs_gate.json"


def load_btc_gate(path: Path | str | None = None) -> dict:
    """Typed read over the evaluator's canonical artifact loader.

    The default path delegates parsing to ``btc_impulse_radar_backtest.load_gate``
    exactly once.  File existence remains observable here so an absent artifact
    is not collapsed with a present-but-unreadable one.  An explicit test/diagnostic
    path is read directly because it is outside the evaluator's configured owner.
    """
    if path is not None:
        p = Path(path)
        if not p.exists():
            return {"read_state": "missing", "artifact": None, "path": str(p)}
        try:
            artifact = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return {"read_state": "corrupt", "artifact": None, "path": str(p)}
        if not isinstance(artifact, dict) or not artifact:
            return {"read_state": "corrupt", "artifact": None, "path": str(p)}
        return {"read_state": "ok", "artifact": artifact, "path": str(p)}

    try:
        from engine import btc_impulse_radar_backtest as evaluator
        p = Path(evaluator.gate_path())
    except Exception:  # noqa: BLE001 — inability to resolve the owner is unreadable
        return {"read_state": "corrupt", "artifact": None, "path": None}
    if not p.exists():
        return {"read_state": "missing", "artifact": None, "path": str(p)}
    try:
        artifact = evaluator.load_gate()
    except Exception:  # noqa: BLE001 — canonical loader failure is explicit evidence
        return {"read_state": "corrupt", "artifact": None, "path": str(p)}
    if not isinstance(artifact, dict) or not artifact:
        return {"read_state": "corrupt", "artifact": None, "path": str(p)}
    return {"read_state": "ok", "artifact": artifact, "path": str(p)}


def _clock_state(value: Any, evaluation: date | None, *, prefix: str,
                 max_age_days: int) -> tuple[date | None, str]:
    stamp = _as_date(value)
    if stamp is None or evaluation is None:
        return stamp, f"{prefix}_time_invalid"
    age = (evaluation - stamp).days
    if age < 0:
        return stamp, f"future_{prefix}"
    if age > max_age_days:
        return stamp, f"stale_{prefix}"
    return stamp, "current"


def current_projection(passport: dict) -> dict:
    """Current public copy for an observed impulse fire.

    Historical issue-time wording belongs only in ``original_claim``. This
    presentation-only projection cannot change permission, and every denied
    state clears forward/action prose.
    """
    eligible = passport.get("claim_eligible") is True
    if eligible:
        edge = ("Current evidence permits action support while this exact "
                "three-day BTC event window remains open.")
        edge_zh = "当前证据允许在该三日 BTC 事件窗口仍开放时提供行动支持。"
    else:
        lead = ("Historical observation only"
                if passport.get("permitted_use") == "history_only"
                else "Observed fire only")
        status = str(passport.get("status_text") or
                     "Current evidence cannot authorize use.").strip().rstrip(".")
        status_zh = str(passport.get("status_zh") or
                        "当前证据无法授权使用").strip().rstrip("。")
        edge = f"{lead} — {status}. No predictive or action authority."
        edge_zh = f"仅保留触发事实 — {status_zh}；不得作为预测或行动依据。"
    return {"edge": edge, "edge_zh": edge_zh,
            "forward": "", "forward_zh": ""}


def impulse_passport(identity: str, *, event_at: Any, event_precision: str | None = None,
                     board_date: Any, source_asof: Any, gate=None) -> dict:
    """Return a fail-closed event passport over one frozen gate snapshot."""
    from engine import btc_impulse_radar as radar

    evaluation = _as_date(board_date)
    permission = radar.resolve_leg_permission(gate, identity, evaluation)
    spec = _SPECS.get(identity) or {
        "signal_id": None, "direction": None,
        "name": "Unknown BTC impulse signal", "name_zh": "未知 BTC 脉冲信号",
        "anchor": "signal-lab-btc-impulse",
    }

    event = _as_date(event_at, instant_utc=event_precision == "timestamp")
    event_expires = event + timedelta(days=_EVENT_DAYS) if event else None
    if evaluation is None:
        event_state = "evaluation_time_invalid"
    elif event is None:
        event_state = "unknown_event_time"
    elif event > evaluation:
        event_state = "future_event"
    elif evaluation >= event_expires:
        event_state = "expired"
    else:
        event_state = "active"

    # Source freshness is an issue-time provenance check, not a render-time
    # freshness check.  An event may lawfully remain inside its measured forward
    # window for several days while the observation that triggered it stays fixed
    # at the event date.  Comparing source_asof to the later board day would both
    # expire valid in-window events early and encourage rebuilds to self-freshen
    # historical provenance.  Compare source data only to the event it produced;
    # the current gate and event-window clocks are evaluated separately above.
    source, source_state = _clock_state(
        source_asof, event, prefix="source", max_age_days=SOURCE_MAX_AGE_DAYS,
    )
    gate_ok = permission["permitted"]
    event_ok = event_state == "active"
    source_ok = source_state == "current"
    eligible = gate_ok and event_ok and source_ok

    if not gate_ok:
        status = permission["reason"]
    elif not source_ok:
        status = source_state
    elif not event_ok:
        status = event_state
    else:
        status = "eligible"
    permitted_use = "action" if eligible else (
        "history_only" if event_state == "expired" else "observation_only"
    )

    return {
        "schema": PASSPORT_SCHEMA,
        "signal_id": spec["signal_id"],
        "family": "btc_impulse",
        "identity": identity,
        "name": spec["name"], "name_zh": spec["name_zh"],
        "direction": permission.get("direction") or spec["direction"],
        "anchor": spec["anchor"],
        "event_at": event.isoformat() if event else None,
        "event_precision": event_precision or "unknown",
        "source_asof": source.isoformat() if source else None,
        "validation_asof": permission.get("validation_asof"),
        "generated_for": evaluation.isoformat() if evaluation else None,
        "event_expires_on": event_expires.isoformat() if event_expires else None,
        "expiry_convention": "date-only BTC event expires at 00:00 UTC on event_date+3",
        "target": permission.get("target") or {},
        "gate_status": permission.get("gate_status") or permission.get("reason"),
        "gate_read_state": permission.get("gate_read_state"),
        "gate_path": permission.get("gate_path"),
        "validation_state": permission.get("validation_state"),
        "source_state": source_state,
        "event_state": event_state,
        "status": status,
        "status_text": _STATUS_TEXT.get(status, "Current evidence cannot authorize use."),
        "status_zh": _STATUS_ZH.get(status, "当前证据无法授权使用"),
        "claim_eligible": eligible,
        "current_permitted": eligible,
        "backtested": bool(permission.get("validation_asof")),
        "permitted_use": permitted_use,
        "permitted_use_zh": {
            "action": "可用于行动", "observation_only": "仅作观察",
            "history_only": "仅作历史记录",
        }[permitted_use],
        "reason": status,
        "reason_text": _STATUS_TEXT.get(status, "Current evidence cannot authorize use."),
        "limits": "Observed fires remain historical facts; this receipt never sizes a trade.",
        "limits_zh": "触发记录仍是历史事实；本凭证绝不决定仓位。",
        "stats": permission.get("stats") or [],
        "model_version": permission.get("model_version"),
        "version_state": permission.get("version_state", "absent"),
        "permission": permission,
    }
