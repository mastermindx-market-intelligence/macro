"""Bounded deterministic interpretation of validated PG economic observations."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from engine.company_intelligence.economic_observations import (
    EconomicObservationError,
    validate_selected_facts,
)
from engine.company_intelligence.pg_profile import PG_DEFINITIONS, PG_METRIC_KEYS


SCHEMA = "earnings.economic_interpretation/v1"
TOP_LEVEL_KEYS = (
    "schema", "interpretation_id", "issuer", "event_id", "build", "selection",
    "observations", "comparisons", "findings", "missing_context",
    "next_evidence", "quality", "clocks", "authority",
)
AUTHORITY_KEYS = (
    "can_rank", "can_gate", "can_size", "can_originate",
    "can_open_entry", "may_modify_prophet",
)
AUTHORITY = {key: False for key in AUTHORITY_KEYS}
SEMANTIC_REVISION = None
CODE_REVISION = None
EPS_PAIRS = (
    ("pg_diluted_eps", "pg_prior_diluted_eps", "reported_eps"),
    ("pg_core_eps", "pg_prior_core_eps", "core_eps"),
)
FINDING_ORDER = (
    "reported_vs_organic_difference", "positive_organic_nonpositive_pure_volume",
    "reported_vs_core_earnings_disagreement", "incomplete_margin_to_cash_bridge",
    "segment_scope_limitation", "missing_consensus",
)
FINDING_TEXT = {
    "reported_vs_organic_difference": (
        "Reported and organic growth differ — check the source before acting.",
        "报告与有机增长不同——先核对来源再行动。",
    ),
    "positive_organic_nonpositive_pure_volume": (
        "Organic rose but pure volume did not — watch — don't chase.",
        "有机增长而纯销量未增——先观察，不追入。",
    ),
    "reported_vs_core_earnings_disagreement": (
        "Reported and core EPS differed — read the receipt first.",
        "报告与核心每股收益不同——先阅读凭证。",
    ),
    "incomplete_margin_to_cash_bridge": (
        "Margin does not show profit or cash improvement — nothing to act on yet.",
        "利润率未显示利润或现金改善——暂无可执行事项。",
    ),
    "segment_scope_limitation": (
        "Segments cover only those segments — check the source before acting.",
        "分部仅覆盖这些分部——先核对来源再行动。",
    ),
    "missing_consensus": (
        "Consensus is unavailable — nothing to act on yet.",
        "缺少一致预期——暂无可执行事项。",
    ),
}


class EconomicInterpretationError(ValueError):
    pass


class UnsupportedInterpretationVersion(EconomicInterpretationError):
    pass


def _plain_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EconomicInterpretationError(f"{name} must be a mapping")
    return value


def _digest(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


SEMANTIC_REVISION = _digest([asdict(definition) for definition in PG_DEFINITIONS])
CODE_REVISION = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _decimal(value: Any) -> Decimal:
    return _parse_decimal(value, "numeric input")


def _json_number(value: Decimal) -> str:
    return format(value, "f")


def _definitions() -> dict[str, Any]:
    return {definition.metric: definition for definition in PG_DEFINITIONS}


_DEFINITIONS = {definition.metric: definition for definition in PG_DEFINITIONS}
_SEGMENT_METRICS = tuple(
    metric for metric in PG_METRIC_KEYS
    if metric.endswith("_organic_sales_growth_pct") and metric != "pg_organic_sales_growth_pct"
)
_DISPLAY = {
    "pg_reported_sales_growth_pct": ("reported_sales_growth", "demand", "reported", "current", "Reported sales growth", "报告销售额增长"),
    "pg_organic_sales_growth_pct": ("organic_sales_growth", "demand", "organic", "current", "Organic sales growth", "有机销售额增长"),
    "pg_total_volume_growth_pct": ("total_volume_growth", "demand", "reported", "current", "Total volume growth", "总销量增长"),
    "pg_organic_volume_growth_pct": ("organic_volume_growth", "demand", "organic", "current", "Organic volume growth", "有机销量增长"),
    "pg_price_contribution_pp": ("price_contribution", "demand", "reported", "current", "Price contribution", "价格贡献"),
    "pg_mix_contribution_pp": ("mix_contribution", "demand", "reported", "current", "Mix contribution", "结构贡献"),
    "pg_fx_contribution_pp": ("fx_contribution", "demand", "reported", "current", "FX contribution", "汇率贡献"),
    "pg_other_contribution_pp": ("other_contribution", "demand", "reported", "current", "Other contribution", "其他贡献"),
    "pg_diluted_eps": ("reported_diluted_eps", "earnings", "reported", "current", "Reported diluted EPS", "报告稀释每股收益"),
    "pg_prior_diluted_eps": ("prior_reported_diluted_eps", "earnings", "reported", "prior", "Prior reported diluted EPS", "上期报告稀释每股收益"),
    "pg_reported_eps_growth_pct": ("reported_eps_growth", "earnings", "reported", "current", "Reported EPS growth", "报告每股收益增长"),
    "pg_core_eps": ("core_eps", "earnings", "core", "current", "Core EPS", "核心每股收益"),
    "pg_prior_core_eps": ("prior_core_eps", "earnings", "core", "prior", "Prior core EPS", "上期核心每股收益"),
    "pg_core_eps_growth_pct": ("core_eps_growth", "earnings", "core", "current", "Core EPS growth", "核心每股收益增长"),
    "pg_core_reconciliation_context": ("core_reconciliation_context", "earnings", "core", "current", "Core EPS reconciliation", "核心每股收益调节说明"),
}
_DISPLAY.update({
    metric: (
        "admitted_segment", "segment", "organic", "current",
        _DEFINITIONS[metric].segment_scope, _DEFINITIONS[metric].segment_scope,
    )
    for metric in _SEGMENT_METRICS
})
_OWNER_BY_GROUP = {"demand": "demand", "segment": "segments", "earnings": "earnings"}
_MARGIN_OR_CASH_FAMILIES = frozenset({"margin", "cash"})
_MONTHS = (
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
)
_MONTH_ABBREVIATIONS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)
_CLOCKED_STATES = frozenset({"up_to_date", "newer_source_pending"})
_CURRENTNESS_STATES = frozenset({
    "up_to_date", "newer_source_pending", "currentness_unverified",
})
_INSTANT_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
_DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_DATE_FORMAT = "%Y-%m-%d"


def _parse_instant(value: Any, name: str) -> datetime:
    if type(value) is not str or _INSTANT_PATTERN.fullmatch(value) is None:
        raise EconomicInterpretationError(f"{name} is not a canonical UTC instant")
    try:
        parsed = datetime.strptime(value, _INSTANT_FORMAT)
    except ValueError as exc:
        raise EconomicInterpretationError(f"{name} is not a canonical UTC instant") from exc
    if parsed.strftime(_INSTANT_FORMAT) != value:
        raise EconomicInterpretationError(f"{name} is not a canonical UTC instant")
    return parsed


def _parse_date(value: Any, name: str) -> date:
    if type(value) is not str or _DATE_PATTERN.fullmatch(value) is None:
        raise EconomicInterpretationError(f"{name} is not a canonical date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise EconomicInterpretationError(f"{name} is not a canonical date") from exc
    if parsed.strftime(_DATE_FORMAT) != value:
        raise EconomicInterpretationError(f"{name} is not a canonical date")
    return parsed


def _parse_token(value: Any, allowed: frozenset[str], name: str) -> str:
    if type(value) is not str or value not in allowed:
        raise EconomicInterpretationError(f"{name} is not an admitted token")
    return value


def _parse_decimal(value: Any, name: str) -> Decimal:
    if type(value) not in {str, int, float, Decimal}:
        raise EconomicInterpretationError(f"{name} is not a decimal-compatible value")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise EconomicInterpretationError(f"{name} is not finite decimal data") from exc
    if not result.is_finite():
        raise EconomicInterpretationError(f"{name} is not finite decimal data")
    return result


def _parse_precision(value: Any) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise EconomicInterpretationError("precision must be a nonnegative integer or None")
    return value


def _parse_fiscal_scope(value: Any) -> tuple[date, date, date, date]:
    if type(value) not in {tuple, list} or len(value) != 4:
        raise EconomicInterpretationError("fiscal_scope must contain exactly four dates")
    return tuple(_parse_date(item, f"fiscal_scope[{index}]") for index, item in enumerate(value))


def _release(workspace: Mapping[str, Any]) -> Mapping[str, Any]:
    releases = [
        source for source in workspace.get("sources", [])
        if isinstance(source, Mapping)
        and source.get("kind") == "issuer_release"
        and source.get("receipt_state") == "byte_replayed"
    ]
    if len(releases) != 1:
        raise EconomicInterpretationError("workspace has no unique byte-replayed release")
    return releases[0]


def _native_rows(
    workspace: Mapping[str, Any], *, source_texts: Mapping[str, str], fiscal_scope: tuple[str, str, str, str]
) -> list[dict[str, Any]]:
    try:
        return validate_selected_facts(workspace, source_texts=source_texts, fiscal_scope=fiscal_scope)
    except EconomicObservationError as exc:
        raise EconomicInterpretationError(f"native observations are refused: {exc}") from exc


def _selected_rows(
    rows: list[dict[str, Any]], workspace: Mapping[str, Any], selection: Any
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_fact = {row.get("fact_id"): row for row in rows}
    by_metric = {row.get("metric"): row for row in rows}
    native_generation = workspace.get("generation_id")
    selected: list[dict[str, Any]] = []
    handles: list[dict[str, Any]] = []
    if selection is None:
        selected = list(rows)
        handles = [
            {
                "workspace_generation_id": native_generation,
                "event_id": row.get("event_id"),
                "fact_id": row.get("fact_id"),
            }
            for row in rows
        ]
        return selected, handles
    if not isinstance(selection, (list, tuple)):
        raise EconomicInterpretationError("selection must be a list of native handles")
    chosen: set[tuple[Any, Any, Any]] = set()
    for item in selection:
        item = _plain_mapping(item, "selection item")
        fact_id = item.get("fact_id")
        metric = item.get("metric")
        row = by_fact.get(fact_id) if fact_id is not None else by_metric.get(metric)
        if row is None or item.get("event_id") != row.get("event_id"):
            raise EconomicInterpretationError("selected fact handle is absent from the workspace")
        expected_generation = item.get("workspace_generation_id")
        if expected_generation != native_generation:
            raise EconomicInterpretationError("selected fact handle belongs to another workspace generation")
        key = (native_generation, row["event_id"], row["fact_id"])
        if key in chosen:
            raise EconomicInterpretationError("selected fact handle is duplicated")
        chosen.add(key)
    selected_set = chosen
    selected = [row for row in rows if (native_generation, row.get("event_id"), row.get("fact_id")) in selected_set]
    handles = [
        {
            "workspace_generation_id": native_generation,
            "event_id": row["event_id"],
            "fact_id": row["fact_id"],
        }
        for row in selected
    ]
    return selected, handles


def _currentness(value: Any) -> dict[str, Any]:
    if value is None:
        return {"state": "currentness_unverified", "source_clock": None}
    currentness = _plain_mapping(value, "selection.currentness")
    if set(currentness) != {"state", "source_clock"}:
        raise EconomicInterpretationError("selection.currentness keys are not exact")
    state = currentness.get("state")
    source_clock = currentness.get("source_clock")
    state = _parse_token(state, _CURRENTNESS_STATES, "selection.currentness.state")
    if state not in _CLOCKED_STATES:
        if source_clock is not None:
            raise EconomicInterpretationError("currentness_unverified cannot carry a source clock")
    else:
        source_clock = _parse_instant(source_clock, "selection.currentness.source_clock")
    return {"state": state, "source_clock": source_clock}


def _selection_input(rows: list[dict[str, Any]], workspace: Mapping[str, Any], selection: Any):
    selection_map = _plain_mapping(selection, "selection")
    if set(selection_map) != {"facts", "currentness"}:
        raise EconomicInterpretationError("selection keys are not exact")
    selected, handles = _selected_rows(rows, workspace, selection_map.get("facts"))
    return selected, handles, _currentness(selection_map.get("currentness"))


def _absence_reason(row: Mapping[str, Any]) -> str:
    absence = row.get("typed_absence")
    if not isinstance(absence, Mapping) or type(absence.get("reason")) is not str or not absence.get("reason"):
        raise EconomicInterpretationError("typed absence reason is malformed")
    return absence["reason"]


def _handle(workspace: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "workspace_generation_id": workspace.get("generation_id"),
        "event_id": row.get("event_id"),
        "fact_id": row.get("fact_id"),
    }


def _comparison_input(workspace: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "handle": _handle(workspace, row),
        "metric": row.get("metric"),
        "period": row.get("period"),
        "unit": row.get("unit"),
        "basis": row.get("basis"),
        "value": row.get("value"),
    }


def _validate_pair(
    current: Mapping[str, Any], prior: Mapping[str, Any], fiscal_scope: tuple[str, str, str, str]
) -> None:
    definitions = _definitions()
    current_definition = definitions.get(current.get("metric"))
    prior_definition = definitions.get(prior.get("metric"))
    if current_definition is None or prior_definition is None:
        raise EconomicInterpretationError("comparison uses an undefined metric")
    if current_definition.paired_metric != prior.get("metric") or prior_definition.paired_metric != current.get("metric"):
        raise EconomicInterpretationError("comparison pairs different measure definitions")
    for field in ("value_kind", "unit", "scale", "basis", "scope", "quarter_duration"):
        if getattr(current_definition, field) != getattr(prior_definition, field):
            raise EconomicInterpretationError("comparison pair differs on a required contract field")
    if current.get("unit") != prior.get("unit") or current.get("basis") != prior.get("basis"):
        raise EconomicInterpretationError("comparison pair differs on unit or accounting basis")
    if current.get("period") != fiscal_scope[1] or prior.get("period") != fiscal_scope[3]:
        raise EconomicInterpretationError("comparison pair does not identify the selected fiscal periods")


def compare_eps(
    current: Any, prior: Any, *, precision: int | None, uncertainty: Any = None
) -> dict[str, Any]:
    current_value = _parse_decimal(current, "current")
    prior_value = _parse_decimal(prior, "prior")
    precision_value = _parse_precision(precision)
    if uncertainty is None:
        uncertainty_value = None
    else:
        uncertainty_value = _parse_decimal(uncertainty, "uncertainty")
        if uncertainty_value < 0:
            raise EconomicInterpretationError("uncertainty must be a finite nonnegative half-width")
    if prior_value <= 0:
        return {
            "state": "not_comparable", "value": None,
            "reason": "nonpositive_prior", "formula": "(current / prior - 1) * 100",
        }
    if uncertainty_value is not None and prior_value - uncertainty_value <= 0:
        return {
            "state": "not_comparable", "value": None,
            "reason": "uncertainty_interval_touches_zero",
            "formula": "(current / prior - 1) * 100",
        }
    try:
        rate = (current_value / prior_value - Decimal("1")) * Decimal("100")
        rounded = rate if precision_value is None else rate.quantize(Decimal(1).scaleb(-precision_value))
    except ArithmeticError as exc:
        raise EconomicInterpretationError("EPS growth arithmetic is not defined") from exc
    return {
        "state": "comparable", "value": _json_number(rounded), "reason": None,
        "formula": "(current / prior - 1) * 100",
        "rounding": {"method": "ROUND_HALF_EVEN", "precision": precision},
    }


def _comparison(
    workspace: Mapping[str, Any], current: Mapping[str, Any], prior: Mapping[str, Any],
    fiscal_scope: tuple[str, str, str, str], reported: Mapping[str, Any] | None,
) -> dict[str, Any]:
    formula = "(current / prior - 1) * 100"
    inputs = [
        _comparison_input(workspace, current),
        _comparison_input(workspace, prior),
    ]
    absent_sides = [side for side in (current, prior) if "value" not in side or "typed_absence" in side]
    if absent_sides:
        absent = absent_sides[0]
        reason = _absence_reason(absent) if absent else "not_selected"
        detail = absent.get("typed_absence", {}).get("detail") if absent else None
        return {
            "schema": "economic_comparison/v1", "formula": formula, "inputs": inputs,
            "result": {"state": "not_comparable", "value": None, "reason": reason, "detail": detail},
            "rounding": None, "state": "declined",
        }
    _validate_pair(current, prior, fiscal_scope)
    derived = compare_eps(current["value"], prior["value"], precision=2)
    if reported is not None and "value" in reported and "typed_absence" not in reported:
        result = {
            "state": "native_reported", "value": _json_number(_decimal(reported["value"])),
            "reason": None, "reported_by_source": True,
        }
        state = "native_reported"
        rounding = None
    else:
        result = derived
        state = derived["state"]
        rounding = derived.get("rounding")
    return {
        "schema": "economic_comparison/v1", "formula": formula, "inputs": inputs,
        "result": result, "rounding": rounding, "state": state,
        "derived_growth": {"value": derived.get("value"), "quality": "approximate"},
        "source_stated_growth": (
            _json_number(_decimal(reported["value"]))
            if reported is not None and "value" in reported and "typed_absence" not in reported else None
        ),
    }


def family_lookup(metric: Any) -> tuple[Any, str, str, str, str, str]:
    try:
        return _DISPLAY[metric]
    except (KeyError, TypeError) as exc:
        raise EconomicInterpretationError("metric is absent from the closed display table") from exc


def format_value_and_unit(value: Any, unit: Any) -> dict[str, str] | None:
    if unit == "text":
        return None
    number = _json_number(_decimal(value))
    if unit == "percent":
        return {"en": f"{number}%", "zh": f"{number}%"}
    if unit == "percentage_points":
        return {"en": f"{number} pp", "zh": f"{number}个百分点"}
    if unit == "usd_per_share":
        english = f"${number}" if number[0] != '-' else f"-${number[1:]}"
        return {"en": english, "zh": f"{number}美元"}
    raise EconomicInterpretationError("unit is absent from the closed display table")


def owner_lookup(group: Any, metric: Any = None) -> str:
    if metric == "pg_core_reconciliation_context":
        return "reconciliation"
    if group not in _OWNER_BY_GROUP:
        raise EconomicInterpretationError("group is absent from the closed owner table")
    return _OWNER_BY_GROUP[group]


def _clock_text(value: datetime) -> dict[str, str]:
    english = (
        f"{_MONTH_ABBREVIATIONS[value.month - 1]} {value.day}, {value.year}, "
        f"{value.hour:02d}:{value.minute:02d} UTC"
    )
    chinese = f"{value.year}年{value.month}月{value.day}日 {value.hour:02d}:{value.minute:02d} UTC"
    return {"en": english, "zh": chinese}


def _fiscal_clock(value: date) -> dict[str, str]:
    english = f"Quarter ended {_MONTHS[value.month - 1]} {value.day}, {value.year}"
    chinese = f"截至{value.year}年{value.month}月{value.day}日的季度"
    return {"en": english, "zh": chinese}


def _observation(
    workspace: Mapping[str, Any], row: Mapping[str, Any], fiscal_scope: tuple[str, str, str, str]
) -> dict[str, Any]:
    metric = row.get("metric")
    family, group, basis, period_role, english, chinese = family_lookup(metric)
    absent = "typed_absence" in row
    period = (
        fiscal_scope[1 if period_role == "current" else 3]
        if absent and period_role in {"current", "prior"} else row.get("period")
    )
    payload = {
        "handle": _handle(workspace, row), "metric": row.get("metric"),
        "fact_id": row.get("fact_id"), "family": family, "group": group,
        "label": {"en": english, "zh": chinese}, "event_id": row.get("event_id"),
        "period": period, "basis": basis, "native_basis": None if absent else row.get("basis"),
    }
    if absent:
        payload["typed_absence"] = row.get("typed_absence")
        payload["value_and_unit"] = None
    elif "value" in row:
        payload.update({
            "value": row.get("value"), "unit": row.get("unit"),
            "source_excerpt": row.get("source_span", {}).get("display_excerpt"),
            "value_and_unit": format_value_and_unit(row.get("value"), row.get("unit")),
        })
        if row.get("unit") == "text":
            payload["source_text"] = {"text": row.get("value"), "lang": "en"}
    return payload


def _finding(rule_id: str, handles: list[dict[str, Any]]) -> dict[str, Any]:
    english, chinese = FINDING_TEXT[rule_id]
    return {
        "rule_id": rule_id, "derivation_class": "deterministic_comparison",
        "text": english, "text_zh": chinese, "input_handles": handles,
    }


def _direction(value: Any) -> int:
    number = _decimal(value)
    if number > 0:
        return 1
    if number < 0:
        return -1
    return 0


def _missing(
    subject: str, owner: str, reason: str, detail: Any = None
) -> dict[str, Any]:
    missing = {
        "subject": subject, "owner": owner, "state": "unavailable", "reason": reason,
        "text": "This context is unavailable, so it is not inferred.",
        "text_zh": "该上下文不可用，因此不做推断。",
    }
    if detail is not None:
        missing["detail"] = detail
    return missing


def _rules(rows: list[dict[str, Any]], workspace: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_metric = {row.get("metric"): row for row in rows}
    findings: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    fired: list[str] = []
    rule_handles: dict[str, list[dict[str, Any]]] = {}

    def fire(rule_id: str, handles: list[dict[str, Any]]) -> None:
        fired.append(rule_id)
        rule_handles[rule_id] = handles
    reported_sales = by_metric.get("pg_reported_sales_growth_pct", {})
    organic_sales = by_metric.get("pg_organic_sales_growth_pct", {})
    pure_volume = by_metric.get("pg_organic_volume_growth_pct", {})
    if "value" in reported_sales and "value" in organic_sales and _direction(reported_sales["value"]) != _direction(organic_sales["value"]):
        fire("reported_vs_organic_difference", [
            _handle(workspace, reported_sales), _handle(workspace, organic_sales)
        ])
    if "value" in organic_sales and "value" in pure_volume and _direction(organic_sales["value"]) > 0 >= _direction(pure_volume["value"]):
        fire("positive_organic_nonpositive_pure_volume", [
            _handle(workspace, organic_sales), _handle(workspace, pure_volume)
        ])
    eps_changes: list[int] = []
    eps_handles: list[dict[str, Any]] = []
    for current_metric, prior_metric, _family in EPS_PAIRS:
        current = by_metric.get(current_metric, {})
        prior = by_metric.get(prior_metric, {})
        if "value" in current and "value" in prior:
            eps_changes.append(_direction(_decimal(current["value"]) - _decimal(prior["value"])))
            eps_handles.extend([_handle(workspace, current), _handle(workspace, prior)])
    if len(eps_changes) == 2 and eps_changes[0] != eps_changes[1]:
        fire("reported_vs_core_earnings_disagreement", eps_handles)
    present_margin_or_cash = [
        row for row in rows
        if row and "value" in row and "typed_absence" not in row
        and family_lookup(row.get("metric"))[0] in _MARGIN_OR_CASH_FAMILIES
    ]
    if not present_margin_or_cash:
        fire("incomplete_margin_to_cash_bridge", [])
    segments = [by_metric.get(metric, {}) for metric in _SEGMENT_METRICS]
    present_segments = [
        row for row in segments
        if row and "value" in row and "typed_absence" not in row
    ]
    if present_segments:
        fire("segment_scope_limitation", [_handle(workspace, row) for row in present_segments])
    fire("missing_consensus", [])
    findings.extend(_finding(rule, rule_handles[rule]) for rule in fired)
    for row in rows:
        if "typed_absence" in row:
            _family, group, *_ = family_lookup(row.get("metric"))
            missing.append(_missing(
                row.get("metric"), owner_lookup(group, row.get("metric")),
                _absence_reason(row), row.get("typed_absence", {}).get("detail"),
            ))
    missing.append(_missing("margin_to_cash", "margin_to_cash", "no_admitted_margin_or_cash_measure"))
    missing.append(_missing("consensus", "consensus", "unlicensed_consensus"))
    return findings, missing


def _unavailable(reason: str, semantic_revision: Any, code_revision: Any) -> dict[str, Any]:
    payload = {key: None for key in TOP_LEVEL_KEYS}
    payload.update({
        "schema": SCHEMA, "issuer": None, "event_id": None,
        "build": {"semantic_revision": semantic_revision, "code_revision": code_revision, "deterministic": False},
        "selection": {"state": "unavailable"}, "observations": [], "comparisons": [],
        "findings": [], "missing_context": [],
        "next_evidence": [], "quality": {"supported": False, "state": "unavailable", "reason": reason},
        "clocks": {
            "fiscal_scope": None, "fiscal_period": None,
            "source_available_at": None, "source_accepted": None,
            "first_observed_at": None, "source_currentness": None,
            "source_revision": None, "correction": None,
        }, "authority": dict(AUTHORITY),
    })
    return payload


def build_economic_interpretation(
    workspace: Mapping[str, Any], *, source_texts: Mapping[str, str],
    fiscal_scope: Any, selection: Any,
    semantic_revision: Any, code_revision: Any,
) -> dict[str, Any]:
    workspace = _plain_mapping(workspace, "workspace")
    source_texts = _plain_mapping(source_texts, "source_texts")
    if type(semantic_revision) is not str or type(code_revision) is not str:
        return _unavailable("unsupported interpretation version", semantic_revision, code_revision)
    if semantic_revision != SEMANTIC_REVISION or code_revision != CODE_REVISION:
        return _unavailable("unsupported interpretation version", semantic_revision, code_revision)
    fiscal_dates = _parse_fiscal_scope(fiscal_scope)
    fiscal_scope = tuple(item.strftime(_DATE_FORMAT) for item in fiscal_dates)
    if not isinstance(selection, Mapping) or set(selection) != {"facts", "currentness"}:
        raise EconomicInterpretationError("selection keys are not exact")
    facts = selection.get("facts")
    if facts is not None and isinstance(facts, (list, tuple)) and len(facts) > 24:
        raise EconomicInterpretationError("comparisons exceed 24")
    rows = _native_rows(workspace, source_texts=source_texts, fiscal_scope=fiscal_scope)
    selected, _handles, currentness = _selection_input(rows, workspace, selection)
    by_metric = {row.get("metric"): row for row in selected}
    comparisons: list[dict[str, Any]] = []
    for current_metric, prior_metric, reported_metric in (
        ("pg_diluted_eps", "pg_prior_diluted_eps", "pg_reported_eps_growth_pct"),
        ("pg_core_eps", "pg_prior_core_eps", "pg_core_eps_growth_pct"),
    ):
        comparisons.append(_comparison(
            workspace, by_metric.get(current_metric, {}), by_metric.get(prior_metric, {}),
            fiscal_scope, by_metric.get(reported_metric),
        ))
    findings, missing = _rules(selected, workspace)
    release = _release(workspace)
    lifecycle = workspace.get("lifecycle", {})
    source_available_at = (
        None if lifecycle.get("source_available_at") is None
        else _parse_instant(lifecycle.get("source_available_at"), "lifecycle.source_available_at")
    )
    observed_at = (
        None if lifecycle.get("observed_at") is None
        else _parse_instant(lifecycle.get("observed_at"), "lifecycle.observed_at")
    )
    document_id = release.get("document_id")
    source_text = source_texts.get(document_id)
    if not isinstance(source_text, str):
        raise EconomicInterpretationError("selected release source text is absent")
    source_digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    identity_input = {
        "schema": SCHEMA, "source_revision": source_digest, "event_id": workspace.get("event_id"),
        "workspace_generation_id": workspace.get("generation_id"), "fiscal_scope": list(fiscal_scope),
        "facts": [[row.get("metric"), row.get("fact_id")] for row in selected],
        "semantic_revision": semantic_revision, "code_revision": code_revision,
        "currentness": {
            "state": currentness["state"],
            "source_clock": (
                None if currentness["source_clock"] is None
                else currentness["source_clock"].strftime(_INSTANT_FORMAT)
            ),
        },
    }
    return {
        "schema": SCHEMA, "interpretation_id": f"econ_{_digest(identity_input)}",
        "issuer": workspace.get("issuer"), "event_id": workspace.get("event_id"),
        "build": {"semantic_revision": semantic_revision, "code_revision": code_revision, "deterministic": True},
        "selection": {
            "state": "selected", "observation_count": len(selected),
            "comparison_count": len(comparisons), "currentness": currentness["state"],
            "currentness_observed_at": (
                None if currentness["source_clock"] is None
                else currentness["source_clock"].strftime(_INSTANT_FORMAT)
            ),
            "selector_version": None,
        },
        "observations": [_observation(workspace, row, fiscal_scope) for row in selected],
        "comparisons": comparisons, "findings": findings, "missing_context": missing,
        "next_evidence": [
            {"subject": "licensed_consensus", "text": "Add a licensed consensus before evaluating expectations.", "text_zh": "在评估预期之前加入获得授权的共识数据。"},
            {"subject": "cash_bridge", "text": "Add compatible operating and cash measures before extending the earnings explanation.", "text_zh": "在扩展盈利解释之前加入兼容的经营和现金指标。"},
        ],
        "quality": {"supported": True, "state": "supported", "authority_effect": "none"},
        "clocks": {
            "fiscal_scope": list(fiscal_scope),
            "fiscal_period": _fiscal_clock(fiscal_dates[1]),
            "source_available_at": (
                None if source_available_at is None else source_available_at.strftime(_INSTANT_FORMAT)
            ),
            "source_accepted": None if source_available_at is None else _clock_text(source_available_at),
            "first_observed_at": None if observed_at is None else observed_at.strftime(_INSTANT_FORMAT),
            "source_currentness": (
                None if currentness["source_clock"] is None
                else _clock_text(currentness["source_clock"])
            ),
            "source_revision": source_digest, "correction": lifecycle.get("state"),
        },
        "authority": dict(AUTHORITY),
    }


def _workspaces(value: Any) -> dict[str, Mapping[str, Any]]:
    if isinstance(value, Mapping) and set(value).issuperset({"schema", "facts", "sources"}):
        return {"": value}
    if not isinstance(value, Mapping) or not value:
        raise EconomicInterpretationError("workspaces must map generation ids to workspaces")
    result = {str(key): workspace for key, workspace in value.items()}
    if any(not isinstance(workspace, Mapping) for workspace in result.values()):
        raise EconomicInterpretationError("workspaces must map generation ids to workspaces")
    return result


def _validate_payload_shape(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    build = payload.get("build")
    if (
        not isinstance(build, Mapping)
        or type(build.get("semantic_revision")) is not str
        or type(build.get("code_revision")) is not str
    ):
        raise EconomicInterpretationError("stored interpretation build is malformed")
    if build.get("semantic_revision") != SEMANTIC_REVISION or build.get("code_revision") != CODE_REVISION:
        raise UnsupportedInterpretationVersion("stored interpretation version is unsupported")
    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise EconomicInterpretationError("stored observations are malformed")
    for observation in observations:
        if not isinstance(observation, Mapping):
            raise EconomicInterpretationError("stored observations are malformed")
        handle = observation.get("handle")
        if not isinstance(handle, Mapping):
            raise EconomicInterpretationError("stored observation handle is malformed")
        for value in handle.values():
            if not isinstance(value, str):
                raise EconomicInterpretationError("stored observation handle is malformed")
    selection = payload.get("selection")
    if (
        not isinstance(selection, Mapping)
        or type(selection.get("currentness")) is not str
        or not (
            type(selection.get("currentness_observed_at")) is str
            or selection.get("currentness_observed_at") is None
        )
    ):
        raise EconomicInterpretationError("stored selection is malformed")
    return build


def validate_economic_interpretation(
    payload: Mapping[str, Any], *, workspaces: Any, source_texts: Mapping[str, str],
    fiscal_scope: Any,
) -> None:
    payload = _plain_mapping(payload, "payload")
    if tuple(payload.keys()) != TOP_LEVEL_KEYS:
        raise EconomicInterpretationError("interpretation top-level keys are not exact")
    stored_payload = dict(payload)
    if stored_payload.get("schema") != SCHEMA or stored_payload.get("authority") != AUTHORITY:
        raise EconomicInterpretationError("interpretation schema or authority is refused")
    build = _validate_payload_shape(stored_payload)
    fiscal_dates = _parse_fiscal_scope(fiscal_scope)
    fiscal_scope = tuple(item.strftime(_DATE_FORMAT) for item in fiscal_dates)
    available = _workspaces(workspaces)
    observations = stored_payload.get("observations")
    handles = [
        observation.get("handle")
        for observation in observations
        if isinstance(observation, Mapping)
    ]
    generation_ids = {handle.get("workspace_generation_id") for handle in handles}
    if len(generation_ids) != 1 or next(iter(generation_ids)) not in available:
        raise EconomicInterpretationError("interpretation handles do not resolve to one supplied workspace")
    workspace = available[next(iter(generation_ids))]
    stored_selection = stored_payload.get("selection")
    selection = {
        "facts": [
            {"workspace_generation_id": handle.get("workspace_generation_id"), "event_id": handle.get("event_id"), "fact_id": handle.get("fact_id")}
            for handle in handles
        ],
        "currentness": {
            "state": stored_selection.get("currentness"),
            "source_clock": stored_selection.get("currentness_observed_at"),
        },
    }
    rebuilt = build_economic_interpretation(
        workspace, source_texts=source_texts, fiscal_scope=fiscal_scope,
        selection=selection, semantic_revision=build.get("semantic_revision"),
        code_revision=build.get("code_revision"),
    )
    if stored_payload.get("interpretation_id") != rebuilt.get("interpretation_id"):
        raise EconomicInterpretationError("stored interpretation identity does not replay")
    if stored_payload != rebuilt:
        raise EconomicInterpretationError("stored interpretation does not replay")


__all__ = [
    "CODE_REVISION", "EconomicInterpretationError", "SEMANTIC_REVISION",
    "UnsupportedInterpretationVersion", "build_economic_interpretation",
    "compare_eps", "validate_economic_interpretation",
]
