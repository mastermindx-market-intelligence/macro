"""engine/neuralweb/pivot_context.py — Additive daily single-security bottom-pivot context.

BP1 (bottom-pivot-delivery-20261105): a pure, stdlib-only composer that turns
already-qualified field observations into one display-only, daily,
single-security context envelope.  It ADDITIVELY consumes evidence the
incumbent engines already produce (engine/neuralweb/bottom_sensors.py binds
trigger / COILED / STAR / knife / hold / sponsorship / distance fields) and
emits no probability, risk aggregate, bullish score, eligibility, position
size, phase label, absorption claim, market-bottom inference or recommendation;
absence of adverse evidence is never read as a positive signal, and a missing
value is never a false vote.

PURE: no network, no repository data access, no file writes, no wall-clock
read. US/New_York conversion uses the standard time-zone database rather than
a second hand-maintained calendar. It reads no market files or network source.
The decision frame, the two evidence modes, the per-field state precedence and
the quality rule are fixed by the delivery contract; the comments below mark
where each gate is applied.
"""
from __future__ import annotations

import datetime as _dt
import math
import re
from typing import Any
from zoneinfo import ZoneInfo

__all__ = ["SCHEMA", "SCOPE", "CADENCE", "FIELD_ORDER", "ALLOWED_FIELDS",
           "EVIDENCE_STATES", "EVIDENCE_MODES", "compose_pivot_context"]

SCHEMA, SCOPE, CADENCE = "bottom_pivot_context.v1", "single_security", "daily"
EVIDENCE_MODE_CURRENT, EVIDENCE_MODE_AS_ISSUED = "current_snapshot", "as_issued"
EVIDENCE_MODES = (EVIDENCE_MODE_CURRENT, EVIDENCE_MODE_AS_ISSUED)

STATE_OBSERVED, STATE_MISSING, STATE_STALE = "observed", "missing", "stale"
STATE_FUTURE, STATE_CONFLICT, STATE_INVALID = "future", "conflict", "invalid"
STATE_NOT_KNOWN = "not_known"
EVIDENCE_STATES = (STATE_OBSERVED, STATE_MISSING, STATE_STALE, STATE_FUTURE,
                   STATE_CONFLICT, STATE_INVALID, STATE_NOT_KNOWN)

FIELD_ORDER = ("trigger_tier", "trigger_age_ticks", "coiled", "star",
               "coiled_fire", "above200", "hold_state", "hold_days_basing",
               "hold_ret_since_anchor_pct", "knife_score", "dist_21d_low_pct",
               "dist_126d_high_pct", "sponsorship_state")
ALLOWED_FIELDS = frozenset(FIELD_ORDER)

MAX_STRING_LEN, TRIGGER_TIERS = 80, ("T1", "T2", "T3", "T4")
SPONSORSHIP_NON_EVIDENCE = ("unavailable", "unknown")

LIMITATION_DAILY = "daily_not_intraday"
LIMITATION_NO_PROBABILITY = "no_calibrated_probability"
LIMITATION_NO_BOTTOM_CLAIM = "no_market_bottom_claim"
LIMITATION_FIRST_SEEN_UNKNOWN = "first_seen_unknown"

DISCLAIMER_EN = ("This is daily single-stock context only; it is not proof of the "
                 "market bottom and not a trade instruction.")
DISCLAIMER_ZH = "本内容仅为日频单只个股的背景信息，不是市场底部的证明，也不是交易指令。"
SOURCE_FRAME_EN, SOURCE_FRAME_ZH = "The source records:", "数据源记录："

_AS_OF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NY = ZoneInfo("America/New_York")


def _ny_date(dt: _dt.datetime) -> _dt.date:
    """Use the incumbent standard timezone rules, including historical changes."""
    return dt.astimezone(_NY).date()


def _parse_aware_datetime(value: Any) -> _dt.datetime | None:
    """Parse an aware ISO-8601 instant; naive or malformed input returns None."""
    if isinstance(value, _dt.datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = _dt.datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None
    else:
        return None
    try:
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
    except Exception:  # noqa: BLE001 - malformed tzinfo
        return None
    return parsed


def _valid_as_of(value: Any) -> bool:
    if not isinstance(value, str) or not _AS_OF_RE.match(value):
        return False
    try:
        _dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _valid_max_age(max_age_days: Any) -> bool:
    if isinstance(max_age_days, bool) or not isinstance(max_age_days, int):
        return False
    return max_age_days >= 0


def _renderable_int(value: int) -> bool:
    try:
        str(value)
    except ValueError:
        return False
    return True


def _finite_number(value: Any) -> tuple[str, Any]:
    if value is None or isinstance(value, bool):
        return STATE_MISSING, None
    if isinstance(value, int):
        return (STATE_OBSERVED, value) if _renderable_int(value) else (STATE_INVALID, None)
    if isinstance(value, float):
        return (STATE_OBSERVED, value) if math.isfinite(value) else (STATE_MISSING, None)
    return STATE_MISSING, None


def _short_string(value: Any) -> tuple[str, Any]:
    if value is None or not isinstance(value, str):
        return STATE_MISSING, None
    if not value.strip() or len(value) > MAX_STRING_LEN:
        return STATE_INVALID, None
    return STATE_OBSERVED, value


def _validate_value(field: str, value: Any) -> tuple[str, Any]:
    """Return (kind, value) with kind observed / missing / invalid."""
    if field == "trigger_tier":
        if not isinstance(value, str):
            return STATE_MISSING, None
        return (STATE_OBSERVED, value) if value in TRIGGER_TIERS else (STATE_INVALID, None)
    if field in ("coiled", "star", "coiled_fire", "above200"):
        if not isinstance(value, bool):
            return STATE_MISSING, None
        return STATE_OBSERVED, value
    if field in ("trigger_age_ticks", "hold_days_basing"):
        if not isinstance(value, int) or isinstance(value, bool):
            return STATE_MISSING, None
        if value < 0 or not _renderable_int(value):
            return STATE_INVALID, None
        return STATE_OBSERVED, value
    if field == "hold_ret_since_anchor_pct":  # a signed return since the anchor
        return _finite_number(value)
    if field in ("dist_21d_low_pct", "dist_126d_high_pct", "knife_score"):
        kind, numeric = _finite_number(value)
        if kind != STATE_OBSERVED:
            return kind, None
        low, high = (0, 1) if field == "knife_score" else (0, None)
        if numeric < low or (high is not None and numeric > high):
            return STATE_INVALID, None
        return STATE_OBSERVED, numeric
    if field == "hold_state":
        return _short_string(value)
    if field == "sponsorship_state":
        kind, text = _short_string(value)
        if kind != STATE_OBSERVED:
            return kind, None
        if text.strip().lower() in SPONSORSHIP_NON_EVIDENCE:
            return STATE_MISSING, None
        return STATE_OBSERVED, text
    return STATE_MISSING, None


def _evidence_entry(field, value, state, source, as_of, available_at) -> dict:
    return {"field": field, "value": value, "state": state, "source": source,
            "as_of": as_of, "available_at": available_at}


def _evaluate_field(field, observations, decision_dt, decision_ny_date,
                    evidence_mode, max_age_days) -> dict:
    """Evaluate one allowlisted field against the decision frame."""
    if not observations:
        return _evidence_entry(field, None, STATE_MISSING, None, None, None)
    # A later-known correction must not invalidate a prior as-of observation.
    # Keep an isolated future-only field visible as unavailable, but establish
    # conflicts only among observations that could belong to the decision frame.
    def is_future(observation):
        stamp = _parse_aware_datetime(observation.get("available_at"))
        vintage = observation.get("as_of")
        return ((stamp is not None and stamp > decision_dt)
                or (_valid_as_of(vintage) and _dt.date.fromisoformat(vintage) > decision_ny_date))

    within_frame = [o for o in observations if not is_future(o)]
    if within_frame:
        observations = within_frame
    if len(observations) > 1:
        # Neither of two contemporaneous conflicting rows may be silently selected.
        return _evidence_entry(field, None, STATE_CONFLICT, None, None, None)

    observation = observations[0]
    source, as_of = observation.get("source"), observation.get("as_of")
    available_at = observation.get("available_at")
    source_out = source if isinstance(source, str) else None
    as_of_out = as_of if isinstance(as_of, str) else None
    available_out = (available_at if isinstance(available_at, str)
                     else available_at.isoformat() if isinstance(available_at, _dt.datetime)
                     else None)

    def rejected(state):
        return _evidence_entry(field, None, state, source_out, as_of_out, available_out)

    # 1. structural integrity: the clock gates below are undefined without it
    if not isinstance(source, str) or not source.strip() or not _valid_as_of(as_of):
        return rejected(STATE_INVALID)
    as_of_date = _dt.date.fromisoformat(as_of)
    available_dt = None
    if available_at is not None:
        available_dt = _parse_aware_datetime(available_at)
        if available_dt is None:
            return rejected(STATE_INVALID)
    # 2. not knowable at the decision instant (both modes)
    if (available_dt is not None and available_dt > decision_dt) or as_of_date > decision_ny_date:
        return rejected(STATE_FUTURE)
    # Preserve future-state precedence, then refuse impossible prior receipts.
    if available_dt is not None:
        try:
            if _ny_date(available_dt) < as_of_date:
                return rejected(STATE_INVALID)
        except (ValueError, OverflowError):
            return rejected(STATE_INVALID)
    # 3. stale vintage (calendar days, never sessions)
    if (decision_ny_date - as_of_date).days > max_age_days:
        return rejected(STATE_STALE)
    # 4. value usability
    kind, value = _validate_value(field, observation.get("value"))
    if kind != STATE_OBSERVED:
        return rejected(kind)
    # 5. first-seen clock
    if available_dt is None and evidence_mode == EVIDENCE_MODE_AS_ISSUED:
        return rejected(STATE_NOT_KNOWN)
    return _evidence_entry(field, value, STATE_OBSERVED, source_out, as_of_out, available_out)


# One template pair per allowlisted field; the boolean fields carry a second
# pair for the false reading.  "{v}" is the observed value.  These texts are
# descriptive of what the source recorded, never a new classification.
_FACT_TEMPLATES = {
    "trigger_tier": ("trigger tier {v}", "触发档位 {v}"),
    "trigger_age_ticks": ("a trigger age of {v} tick(s)", "触发时长 {v} 个 tick"),
    "coiled": ("cohort-washout context is present", "存在群体洗盘背景",
               "the coiled flag is false", "coiled 标记为 false"),
    "star": ("the star flag is true", "star 标记为 true",
             "the star flag is false", "star 标记为 false"),
    "coiled_fire": ("an existing early-turn marker is present", "存在既有的早期转折标记",
                    "the coiled_fire flag is false", "coiled_fire 标记为 false"),
    "above200": ("the name is above its 200-day trend", "该标的位于 200 日趋势上方",
                 "the name is below its 200-day trend, which does not automatically "
                 "invalidate an early turn and does not suppress other evidence",
                 "该标的位于 200 日趋势下方；这不会自动否定早期转折，也不会屏蔽其他证据"),
    "hold_state": ("hold state {v} (source state; no new classification)",
                   "持仓状态 {v}（来源状态，不做新的分类判定）"),
    "hold_days_basing": ("{v} day(s) of basing", "已筑底 {v} 天"),
    "hold_ret_since_anchor_pct": ("{v}% since the anchor", "自锚点以来 {v}%"),
    "knife_score": ("a knife score of {v}; no threshold or verdict is applied",
                    "knife 分数为 {v}；不设阈值，不作判定"),
    "dist_21d_low_pct": ("price sits {v}% above the recent 21-day low (measured distance, "
                         "not an expected return)",
                         "价格高于近期 21 日低点 {v}%（已测得距离，非预期收益）"),
    "dist_126d_high_pct": ("price sits {v}% below the trailing 126-day high (measured "
                           "distance, not an expected return)",
                           "价格低于 126 日高点 {v}%（已测得距离，非预期收益）"),
    "sponsorship_state": ("sponsorship state {v} (source state; no new classification)",
                          "赞助状态 {v}（来源状态，不做新的分类判定）"),
}


def _fmt_value(value: Any) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        try:
            return f"{value:.6g}"
        except (OverflowError, ValueError):  # pragma: no cover - defensive
            return repr(value)
    if isinstance(value, str):
        return value.strip()
    try:
        return str(value)
    except ValueError:  # pragma: no cover - defensive
        return "<unrenderable>"


def _fact_pairs(by_field: dict) -> list[tuple[str, str]]:
    """Bilingual factual fragments, one per observed field, in allowlist order."""
    pairs: list[tuple[str, str]] = []
    for field in FIELD_ORDER:
        entry = by_field.get(field)
        if entry is None or entry["state"] != STATE_OBSERVED:
            continue
        template = _FACT_TEMPLATES[field]
        en, zh = (template[2], template[3]) if entry["value"] is False and len(template) == 4 else (template[0], template[1])
        value = _fmt_value(entry["value"])
        pairs.append((en.format(v=value), zh.format(v=value)))
    return pairs


# A frame-level rejection: every field is invalid, nothing was composed.
_FAILURE_TEXT = {
    "invalid_decision": ("the decision instant is missing, naive, invalid or outside the "
                          "modelled US/New_York range", "决策时间戳缺失、无时区、无效或超出已建模的美东时区范围"),
    "invalid_request": ("the request is not usable as given", "请求本身不可用"),
}


def _envelope(symbol, mode, decision_at, quality, evidence, explanation, limitations) -> dict:
    return {"schema": SCHEMA, "symbol": symbol, "scope": SCOPE, "cadence": CADENCE,
            "evidence_mode": mode, "decision_at": decision_at, "is_display_only": True,
            "probability": None, "action_authority": "none", "quality": quality,
            "evidence": evidence, "explanation": explanation, "limitations": limitations}


def _unavailable_result(symbol, evidence_mode, decision_at, failure) -> dict:
    """The envelope for a rejected frame."""
    en_reason, zh_reason = _FAILURE_TEXT[failure]
    name = symbol.strip() if isinstance(symbol, str) and symbol.strip() else "the requested security"
    return _envelope(
        symbol if isinstance(symbol, str) else None,
        evidence_mode if isinstance(evidence_mode, str) else "",
        decision_at if isinstance(decision_at, str) else None, "unavailable",
        [_evidence_entry(f, None, STATE_INVALID, None, None, None) for f in FIELD_ORDER],
        {"en": f"Daily single-stock context for {name} could not be composed: {en_reason}, so "
               f"no field could be evaluated. {DISCLAIMER_EN}",
         "zh": f"未能生成 {name} 的日频单只个股背景：{zh_reason}，因此无法评估任何字段。"
               f"{DISCLAIMER_ZH}"},
        [LIMITATION_DAILY, LIMITATION_NO_PROBABILITY, LIMITATION_NO_BOTTOM_CLAIM])


def compose_pivot_context(symbol: str, observations: list[dict], *, decision_at: str,
                          evidence_mode: str = EVIDENCE_MODE_CURRENT,
                          max_age_days: int = 7) -> dict:
    mode = evidence_mode if isinstance(evidence_mode, str) else ""
    decision_dt = _parse_aware_datetime(decision_at)
    if decision_dt is None:
        return _unavailable_result(symbol, evidence_mode, None, "invalid_decision")
    decision_echo = decision_at if isinstance(decision_at, str) else decision_dt.isoformat()
    if mode not in EVIDENCE_MODES or not _valid_max_age(max_age_days):
        return _unavailable_result(symbol, evidence_mode, decision_echo, "invalid_request")
    if not isinstance(symbol, str) or not symbol.strip():
        return _unavailable_result(symbol, evidence_mode, decision_echo, "invalid_request")
    if not isinstance(observations, (list, tuple)):
        return _unavailable_result(symbol, evidence_mode, decision_echo, "invalid_request")
    try:
        decision_ny_date = _ny_date(decision_dt)
    except ValueError:
        return _unavailable_result(symbol, evidence_mode, decision_echo, "invalid_decision")
    except Exception:  # noqa: BLE001 - unmodellable instant
        return _unavailable_result(symbol, evidence_mode, decision_echo, "invalid_decision")

    # Group the observations that name an allowlisted field.  Unknown fields are
    # ignored entirely (this is what keeps ARMED / PRIMED out of the envelope).
    grouped: dict[str, list[dict]] = {}
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        field = observation.get("field")
        if isinstance(field, str) and field in ALLOWED_FIELDS:
            grouped.setdefault(field, []).append(observation)

    evidence, by_field, first_seen_unknown = [], {}, False
    for field in FIELD_ORDER:
        entry = _evaluate_field(field, grouped.get(field, []), decision_dt,
                                decision_ny_date, mode, max_age_days)
        first_seen_unknown |= entry["state"] == STATE_OBSERVED and entry["available_at"] is None
        evidence.append(entry)
        by_field[field] = entry

    observed_count = sum(1 for entry in evidence if entry["state"] == STATE_OBSERVED)
    total_fields = len(FIELD_ORDER)
    quality = ("unavailable" if observed_count == 0 else
               "available" if observed_count == total_fields else "partial")

    name, pairs = symbol.strip(), _fact_pairs(by_field)
    if observed_count == 0 or not pairs:
        explanation = {
            "en": f"Daily single-stock context for {name}: insufficient current evidence - "
                   f"none of the {total_fields} allowlisted fields has a usable observation. "
                   f"{DISCLAIMER_EN}",
            "zh": f"{name} 的日频单只个股背景：当前证据不足——{total_fields} 个白名单字段没有"
                   f"任何一个具备可用观测。{DISCLAIMER_ZH}",
        }
    else:
        explanation = {
            "en": f"Daily single-stock context for {name} ({observed_count} of "
                   f"{total_fields} allowlisted fields usable): {SOURCE_FRAME_EN} "
                   f"{'; '.join(p[0] for p in pairs)}. {DISCLAIMER_EN}",
            "zh": f"{name} 的日频单只个股背景（{total_fields} 个白名单字段中 {observed_count} 个可用）："
                   f"{SOURCE_FRAME_ZH}{'；'.join(p[1] for p in pairs)}。{DISCLAIMER_ZH}",
        }

    limitations = [LIMITATION_DAILY, LIMITATION_NO_PROBABILITY, LIMITATION_NO_BOTTOM_CLAIM]
    if first_seen_unknown:
        limitations.append(LIMITATION_FIRST_SEEN_UNKNOWN)
    return _envelope(symbol, mode, decision_echo, quality, evidence, explanation, limitations)


def compact_pivot_context(payload: Any, *, symbol: str, decision_at: str) -> dict | None:
    """Existing Brain consumer projection, requalified at its own explicit clock.

    No new candidates, scores, prices or source facts. A later consumer cannot
    revive unavailable evidence or keep an expired positive explanation alive.
    """
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        return None
    if (payload.get("symbol") != symbol or payload.get("scope") != SCOPE
            or payload.get("cadence") != CADENCE or payload.get("is_display_only") is not True
            or payload.get("action_authority") != "none" or payload.get("probability") is not None):
        return None
    now = _parse_aware_datetime(decision_at)
    original = _parse_aware_datetime(payload.get("decision_at"))
    mode = payload.get("evidence_mode")
    items = payload.get("evidence")
    if now is None or original is None or original > now or mode not in EVIDENCE_MODES or not isinstance(items, list):
        return None
    fields = [e.get("field") for e in items if isinstance(e, dict)
              and isinstance(e.get("field"), str) and e.get("field") in ALLOWED_FIELDS]
    if len(fields) != len(set(fields)):
        return None
    # Recheck alleged original observations at BOTH clocks; never upgrade a
    # source's missing/stale/conflict field by waiting or rebuilding its wrapper.
    offered = [e for e in items if isinstance(e, dict) and e.get("state") == STATE_OBSERVED]
    initial = compose_pivot_context(symbol, offered, decision_at=original.isoformat(), evidence_mode=mode)
    accepted = [e for e in initial["evidence"] if e["state"] == STATE_OBSERVED]
    current = compose_pivot_context(symbol, accepted, decision_at=now.isoformat(), evidence_mode=mode)
    observed = {e["field"]: {"value":e["value"], "as_of":e["as_of"]}
                for e in current["evidence"] if e["state"] == STATE_OBSERVED}
    initial_by = {e["field"]:e for e in initial["evidence"]}
    source_by = {e.get("field"):e for e in items if isinstance(e,dict)
                 and isinstance(e.get("field"),str) and e.get("field") in ALLOWED_FIELDS}
    unavailable = {}
    for e in current["evidence"]:
        field=e["field"]
        if field in observed:
            continue
        state=e["state"]
        if state == STATE_MISSING:
            state=initial_by[field]["state"]
        source_state=source_by.get(field,{}).get("state")
        if state == STATE_MISSING and source_state in EVIDENCE_STATES and source_state != STATE_OBSERVED:
            state=source_state
        unavailable[field]=state
    limitations=list(current["limitations"])
    source_limits = payload.get("limitations")
    source_limits = source_limits if isinstance(source_limits, list) else []
    for reason in ("source_revision_not_attested", "mixed_source_dates"):
        if reason in source_limits and reason not in limitations:
            limitations.append(reason)
    dates = {entry["as_of"] for entry in observed.values()}
    as_of = min(dates) if dates else None
    field_asofs = {field: entry["as_of"] for field, entry in observed.items()} if len(dates) > 1 else {}
    values = {field: entry["value"] for field, entry in observed.items()}
    return {"schema":"bottom_pivot_context.compact.v1", "scope":SCOPE, "cadence":CADENCE,
            "source_evaluated_at":original.isoformat(), "consumer_evaluated_at":now.isoformat(),
            "evidence_mode":mode, "quality":current["quality"], "observed":values,
            "as_of":as_of, "field_asofs":field_asofs,
            "unavailable":unavailable, "limitations":limitations,
            "allowed_behavior":"annotate_only", "action_authority":"none", "probability":None}
