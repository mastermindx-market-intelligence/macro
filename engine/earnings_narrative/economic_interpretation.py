"""Bounded deterministic interpretation of validated PG economic observations."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
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
EPS_PAIRS = (
    ("pg_diluted_eps", "pg_prior_diluted_eps", "reported_eps"),
    ("pg_core_eps", "pg_prior_core_eps", "core_eps"),
)
SEGMENT_METRICS = tuple(metric for metric in PG_METRIC_KEYS if metric.endswith("_growth_pct") and metric not in {
    "pg_reported_sales_growth_pct", "pg_organic_sales_growth_pct",
    "pg_total_volume_growth_pct", "pg_organic_volume_growth_pct",
    "pg_reported_eps_growth_pct", "pg_core_eps_growth_pct",
})
FINDING_TEXT = {
    "reported_vs_organic_difference": (
        "Reported sales grew while the company-defined organic sales measure did not grow.",
        "报告销售额增长，而公司定义的有机销售额指标没有增长。",
    ),
    "positive_organic_nonpositive_pure_volume": (
        "Positive organic sales growth is separated from pricing and mix because pure volume did not grow.",
        "由于纯销量没有增长，正的有机销售额增长与定价和组合分开解释。",
    ),
    "reported_vs_core_earnings_disagreement": (
        "Reported and core earnings moved in opposite directions under their separate definitions.",
        "报告盈利与核心盈利在各自定义下朝相反方向变化。",
    ),
    "incomplete_margin_to_cash_bridge": (
        "The source does not provide the compatible measures needed to connect this margin change to cash.",
        "来源没有提供将这项利润率变化与现金联系起来的兼容指标。",
    ),
    "segment_scope_limitation": (
        "Segment observations are limited to the named scopes and do not measure category or sector breadth.",
        "分部观察仅限于命名的范围，不能衡量类别或行业覆盖广度。",
    ),
    "missing_consensus": (
        "No licensed consensus is available, so no beat or miss is stated.",
        "没有获得授权的共识数据，因此不表述优于或低于预期。",
    ),
}


class EconomicInterpretationError(ValueError):
    pass


def _plain_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EconomicInterpretationError(f"{name} must be a mapping")
    return value


def _digest(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _decimal(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise EconomicInterpretationError("numeric input is not a decimal-compatible value")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise EconomicInterpretationError("numeric input is not finite decimal data") from exc
    if not result.is_finite():
        raise EconomicInterpretationError("numeric input is not finite decimal data")
    return result


def _json_number(value: Decimal) -> str:
    return format(value, "f")


def _definitions() -> dict[str, Any]:
    return {definition.metric: definition for definition in PG_DEFINITIONS}


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
        if row not in selected:
            selected.append(row)
            handles.append({
                "workspace_generation_id": native_generation,
                "event_id": row["event_id"],
                "fact_id": row["fact_id"],
            })
    return selected, handles


def _absence_reason(row: Mapping[str, Any]) -> str:
    absence = row.get("typed_absence")
    if not isinstance(absence, Mapping):
        return "no_span_addressable_evidence"
    return str(absence.get("reason") or "no_span_addressable_evidence")


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


def compare_eps(current: Any, prior: Any, *, precision: int | None) -> dict[str, Any]:
    current_value = _decimal(current)
    prior_value = _decimal(prior)
    if precision is not None and (isinstance(precision, bool) or not isinstance(precision, int) or precision < 0):
        raise EconomicInterpretationError("precision must be a nonnegative integer or None")
    if prior_value <= 0:
        return {
            "state": "not_comparable", "value": None,
            "reason": "nonpositive_prior", "formula": "(current / prior - 1) * 100",
        }
    if precision is not None and prior_value - Decimal(precision) <= 0:
        return {
            "state": "not_comparable", "value": None,
            "reason": "uncertainty_interval_touches_zero",
            "formula": "(current / prior - 1) * 100",
        }
    try:
        rate = (current_value / prior_value - Decimal("1")) * Decimal("100")
    except (ArithmeticError, InvalidOperation) as exc:
        raise EconomicInterpretationError("EPS growth arithmetic is not defined") from exc
    rounded = rate if precision is None else rate.quantize(Decimal(1).scaleb(-precision))
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
    if "value" not in current or "typed_absence" in current or "value" not in prior or "typed_absence" in prior:
        absent = current if "typed_absence" in current else prior
        reason = _absence_reason(absent)
        detail = absent.get("typed_absence", {}).get("detail")
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


def _observation(workspace: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        "handle": _handle(workspace, row), "metric": row.get("metric"),
        "display_name": row.get("metric"), "event_id": row.get("event_id"),
    }
    if "value" in row:
        payload.update({
            "value": row.get("value"), "unit": row.get("unit"),
            "period": row.get("period"), "basis": row.get("basis"),
            "source_excerpt": row.get("source_span", {}).get("display_excerpt"),
        })
    else:
        payload["typed_absence"] = row.get("typed_absence")
    return payload


def _finding(rule_id: str, handles: list[dict[str, Any]]) -> dict[str, Any]:
    english, chinese = FINDING_TEXT[rule_id]
    return {
        "rule_id": rule_id, "derivation_class": "deterministic_comparison",
        "text": english, "text_zh": chinese, "input_handles": handles,
    }


def _missing(subject: str, reason: str, detail: Any = None) -> dict[str, Any]:
    missing = {
        "subject": subject, "state": "unavailable", "reason": reason,
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
    reported_sales = by_metric.get("pg_reported_sales_growth_pct", {})
    organic_sales = by_metric.get("pg_organic_sales_growth_pct", {})
    pure_volume = by_metric.get("pg_organic_volume_growth_pct", {})
    if "value" in reported_sales and "value" in organic_sales and _decimal(reported_sales["value"]) > 0 and _decimal(organic_sales["value"]) <= 0:
        findings.append(_finding("reported_vs_organic_difference", [
            _handle(workspace, reported_sales), _handle(workspace, organic_sales)
        ]))
    if "value" in organic_sales and _decimal(organic_sales["value"]) > 0 and "value" in pure_volume and _decimal(pure_volume["value"]) <= 0:
        findings.append(_finding("positive_organic_nonpositive_pure_volume", [
            _handle(workspace, organic_sales), _handle(workspace, pure_volume)
        ]))
    eps_rates: list[Decimal] = []
    eps_handles: list[dict[str, Any]] = []
    for current_metric, prior_metric, _family in EPS_PAIRS:
        current = by_metric.get(current_metric, {})
        prior = by_metric.get(prior_metric, {})
        if "value" in current and "value" in prior and _decimal(prior["value"]) > 0:
            eps_rates.append(_decimal(current["value"]) / _decimal(prior["value"]))
            eps_handles.extend([_handle(workspace, current), _handle(workspace, prior)])
    if len(eps_rates) == 2 and (eps_rates[0] > 1) != (eps_rates[1] > 1):
        findings.append(_finding("reported_vs_core_earnings_disagreement", eps_handles))
    for current_metric, prior_metric, _family in EPS_PAIRS:
        for row in (by_metric.get(current_metric), by_metric.get(prior_metric)):
            if row is not None and "typed_absence" in row:
                missing.append(_missing(row.get("metric", current_metric), _absence_reason(row), row.get("typed_absence", {}).get("detail")))
    for metric in ("pg_reported_eps_growth_pct", "pg_core_eps_growth_pct", "pg_total_volume_growth_pct", "pg_organic_volume_growth_pct"):
        row = by_metric.get(metric)
        if row is not None and "typed_absence" in row:
            missing.append(_missing(metric, _absence_reason(row), row.get("typed_absence", {}).get("detail")))
    reconciliation = by_metric.get("pg_core_reconciliation_context", {})
    if "typed_absence" in reconciliation:
        findings.append(_finding("incomplete_margin_to_cash_bridge", [_handle(workspace, reconciliation)]))
        missing.append(_missing("core_reconciliation", _absence_reason(reconciliation), reconciliation.get("typed_absence", {}).get("detail")))
    segments = [by_metric.get(metric, {}) for metric in SEGMENT_METRICS]
    absent_segments = [row for row in segments if "typed_absence" in row]
    if absent_segments:
        findings.append(_finding("segment_scope_limitation", [_handle(workspace, row) for row in absent_segments]))
        missing.append(_missing("segment_organic_sales", _absence_reason(absent_segments[0]), absent_segments[0].get("typed_absence", {}).get("detail")))
    findings.append(_finding("missing_consensus", []))
    missing.append(_missing("consensus", "unlicensed_consensus"))
    return findings, missing


def _supported_revision(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    return len(value) == 64 or value.startswith("synthetic-")


def _unavailable(reason: str, semantic_revision: Any, code_revision: Any) -> dict[str, Any]:
    payload = {key: None for key in TOP_LEVEL_KEYS}
    payload.update({
        "schema": SCHEMA, "issuer": None, "event_id": None,
        "build": {"semantic_revision": semantic_revision, "code_revision": code_revision, "deterministic": False},
        "selection": {"state": "unavailable"}, "observations": [], "comparisons": [],
        "findings": [], "missing_context": [{"subject": "interpretation", "reason": reason}],
        "next_evidence": [], "quality": {"supported": False, "state": "unavailable", "reason": reason},
        "clocks": {}, "authority": dict(AUTHORITY),
    })
    return payload


def build_economic_interpretation(
    workspace: Mapping[str, Any], *, source_texts: Mapping[str, str],
    fiscal_scope: tuple[str, str, str, str], selection: Any,
    semantic_revision: str, code_revision: str,
) -> dict[str, Any]:
    workspace = _plain_mapping(workspace, "workspace")
    source_texts = _plain_mapping(source_texts, "source_texts")
    if not _supported_revision(semantic_revision) or not _supported_revision(code_revision):
        return _unavailable("unsupported interpretation version", semantic_revision, code_revision)
    if isinstance(selection, (list, tuple)) and len(selection) > 24:
        raise EconomicInterpretationError("comparisons exceed 24")
    rows = _native_rows(workspace, source_texts=source_texts, fiscal_scope=fiscal_scope)
    selected, _handles = _selected_rows(rows, workspace, selection)
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
    source_digest = release.get("source_sha256")
    identity_input = {
        "schema": SCHEMA, "source_sha256": source_digest, "event_id": workspace.get("event_id"),
        "workspace_generation_id": workspace.get("generation_id"), "fiscal_scope": list(fiscal_scope),
        "facts": [[row.get("metric"), row.get("fact_id")] for row in selected],
        "semantic_revision": semantic_revision, "code_revision": code_revision,
    }
    return {
        "schema": SCHEMA, "interpretation_id": f"econ_{_digest(identity_input)}",
        "issuer": workspace.get("issuer"), "event_id": workspace.get("event_id"),
        "build": {"semantic_revision": semantic_revision, "code_revision": code_revision, "deterministic": True},
        "selection": {
            "state": "selected", "observation_count": len(selected),
            "comparison_count": len(comparisons), "currentness": "latest_accepted",
            "selector_version": None,
        },
        "observations": [_observation(workspace, row) for row in selected],
        "comparisons": comparisons, "findings": findings, "missing_context": missing,
        "next_evidence": [
            {"subject": "licensed_consensus", "text": "Add a licensed consensus before evaluating expectations.", "text_zh": "在评估预期之前加入获得授权的共识数据。"},
            {"subject": "cash_bridge", "text": "Add compatible operating and cash measures before extending the earnings explanation.", "text_zh": "在扩展盈利解释之前加入兼容的经营和现金指标。"},
        ],
        "quality": {"supported": True, "state": "supported", "authority_effect": "none"},
        "clocks": {
            "fiscal_scope": list(fiscal_scope),
            "source_available_at": lifecycle.get("source_available_at"),
            "first_observed_at": lifecycle.get("observed_at"),
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


def validate_economic_interpretation(
    payload: Mapping[str, Any], *, workspaces: Any, source_texts: Mapping[str, str],
    fiscal_scope: tuple[str, str, str, str],
) -> None:
    payload = _plain_mapping(payload, "payload")
    if tuple(payload.keys()) != TOP_LEVEL_KEYS:
        raise EconomicInterpretationError("interpretation top-level keys are not exact")
    if payload.get("schema") != SCHEMA or payload.get("authority") != AUTHORITY:
        raise EconomicInterpretationError("interpretation schema or authority is refused")
    build = payload.get("build")
    if not isinstance(build, Mapping) or not _supported_revision(build.get("code_revision")):
        raise EconomicInterpretationError("interpretation code version is unsupported")
    available = _workspaces(workspaces)
    handles = [observation.get("handle") for observation in payload.get("observations", [])]
    if any(not isinstance(handle, Mapping) for handle in handles):
        raise EconomicInterpretationError("observation handle is malformed")
    generation_ids = {handle.get("workspace_generation_id") for handle in handles}
    if len(generation_ids) != 1 or next(iter(generation_ids)) not in available:
        raise EconomicInterpretationError("interpretation handles do not resolve to one supplied workspace")
    workspace = available[next(iter(generation_ids))]
    selection = [
        {"workspace_generation_id": handle.get("workspace_generation_id"), "event_id": handle.get("event_id"), "fact_id": handle.get("fact_id")}
        for handle in handles
    ]
    rebuilt = build_economic_interpretation(
        workspace, source_texts=source_texts, fiscal_scope=fiscal_scope,
        selection=selection, semantic_revision=build.get("semantic_revision"),
        code_revision=build.get("code_revision"),
    )
    if payload.get("interpretation_id") != rebuilt.get("interpretation_id"):
        raise EconomicInterpretationError("stored interpretation identity does not replay")
    for field in ("observations", "comparisons", "findings", "missing_context"):
        if payload.get(field) != rebuilt.get(field):
            raise EconomicInterpretationError(f"stored {field} does not replay")
    if payload.get("selection") != rebuilt.get("selection") or payload.get("clocks") != rebuilt.get("clocks"):
        raise EconomicInterpretationError("stored interpretation receipts do not replay")


__all__ = [
    "EconomicInterpretationError", "build_economic_interpretation",
    "compare_eps", "validate_economic_interpretation",
]
