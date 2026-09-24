"""Strict validation for the opt-in private PG economic observation selection."""
from __future__ import annotations

from datetime import date
import hashlib
import math
from numbers import Real
from typing import Any, Mapping

from .documents import ABSENCE_SCHEMA, TypedAbsence
from .pg_profile import (
    PG_DEFINITIONS,
    PG_METRIC_KEYS,
    PG_PRIVATE_RIGHTS_PROFILE,
    _NEUTRAL_ZERO,
    _fiscal_identity,
    _scope_period_forms,
    parse_pg_literal,
    replay_table_layout,
)


PRESENT_KEYS = frozenset({
    "schema", "fact_id", "event_id", "metric", "value", "unit", "period",
    "basis", "source_span",
})
ABSENT_KEYS = frozenset({
    "schema", "fact_id", "event_id", "metric", "typed_absence",
})
TYPED_ABSENCE_KEYS = frozenset({
    "schema", "authority", "reason", "subject", "detail", "missing_fields",
    "event_id", "document_id",
})


class EconomicObservationError(ValueError):
    pass


def _definition(metric: Any) -> Any:
    return next(item for item in PG_DEFINITIONS if item.metric == metric)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fiscal_scope(value: Any) -> tuple[date, date, date, date]:
    if not isinstance(value, tuple) or len(value) != 4:
        raise EconomicObservationError("fiscal_scope must contain four ISO dates")
    try:
        current_start, current_end, prior_start, prior_end = (
            date.fromisoformat(item) for item in value
        )
    except (TypeError, ValueError) as exc:
        raise EconomicObservationError("fiscal_scope must contain four ISO dates") from exc
    if not (
        current_start < current_end
        and prior_start < prior_end
        and prior_end < current_start
        and prior_start < current_start
    ):
        raise EconomicObservationError("fiscal_scope ordering is invalid")
    if not 89 <= (current_end - current_start).days <= 92:
        raise EconomicObservationError("current fiscal scope is not a quarter")
    if not 89 <= (prior_end - prior_start).days <= 92:
        raise EconomicObservationError("prior fiscal scope is not a quarter")
    if (current_start - prior_start).days not in {364, 365, 366}:
        raise EconomicObservationError("prior fiscal interval does not match current quarter")
    return current_start, current_end, prior_start, prior_end


def _fact_id(event_id: Any, metric: Any, period: Any, basis: Any) -> str:
    identity = "|".join(str(item) for item in (event_id, metric, period, basis))
    return f"fact_{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]}"


def _verify_pg_replay(
    *,
    source: str,
    definition: Any,
    start: Any,
    end: Any,
    row: Mapping[str, Any],
    current_start: date,
    current_end: date,
    prior_end: date,
) -> None:
    _, _, current_forms, prior_forms = _scope_period_forms(current_start, current_end, prior_end)
    source_bytes = source.encode("utf-8")
    if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(source_bytes):
        raise EconomicObservationError("replay_mismatch: replay location is invalid")
    if definition.value_kind == "bounded_text":
        context = source[max(0, start - 240):end].casefold()
        if definition.row_label and definition.row_label.casefold() not in context:
            raise EconomicObservationError("replay_mismatch: replayed basis differs from the metric definition")
        return
    try:
        row_label, header, column = replay_table_layout(
            source,
            start=int(start),
            end=int(end),
            header_forms=(
                (definition.column_label,)
                if definition.column_label
                else (*current_forms, *prior_forms)
            ),
        )
    except ValueError as exc:
        raise EconomicObservationError(f"replay_mismatch: {exc}") from exc
    if definition.row_label and row_label.casefold() != definition.row_label.casefold():
        raise EconomicObservationError("replay_mismatch: replayed row differs from the metric definition")
    period_forms = set(prior_forms if row.get("metric", "").startswith("pg_prior_") else current_forms)
    if definition.column_label:
        if column < 1 or header != definition.column_label:
            raise EconomicObservationError("replay_mismatch: replayed column differs from the metric definition")
        return
    if column < 1 or header not in period_forms:
        raise EconomicObservationError("replay_mismatch: replayed period differs from the stored observation")


def validate_selected_facts(
    workspace: Mapping[str, Any],
    *,
    source_texts: Mapping[str, str],
    fiscal_scope: tuple[str, str, str, str],
) -> list[dict[str, Any]]:
    if not isinstance(workspace, Mapping):
        raise EconomicObservationError("workspace must be a mapping")
    if not isinstance(source_texts, Mapping):
        raise EconomicObservationError("source_texts must be a mapping")
    current_start, current_end, prior_start, prior_end = _fiscal_scope(fiscal_scope)
    fiscal_period = workspace.get("fiscal_period")
    if not isinstance(fiscal_period, Mapping):
        raise EconomicObservationError("workspace fiscal period is missing")
    if fiscal_period.get("calendar_end") != current_end.isoformat():
        raise EconomicObservationError("workspace fiscal period does not match fiscal_scope")
    expected_year, expected_quarter = _fiscal_identity(current_start, current_end)
    if str(fiscal_period.get("quarter")) != str(expected_quarter):
        raise EconomicObservationError("workspace quarter does not match fiscal_scope")
    if str(fiscal_period.get("year")) != str(expected_year):
        raise EconomicObservationError("workspace fiscal year does not match fiscal_scope")
    releases = [
        source for source in workspace.get("sources", [])
        if isinstance(source, Mapping)
        and source.get("kind") == "issuer_release"
        and source.get("receipt_state") == "byte_replayed"
    ]
    if len(releases) != 1:
        raise EconomicObservationError("workspace has no unique byte-replayed release document")
    release = releases[0]
    workspace_document_id = release.get("document_id") if isinstance(release, Mapping) else None
    if not isinstance(workspace_document_id, str) or not workspace_document_id:
        raise EconomicObservationError("workspace has no release document identity")

    facts = workspace.get("facts")
    if not isinstance(facts, list):
        raise EconomicObservationError("workspace facts must be a list")
    rows = [
        row for row in facts
        if isinstance(row, Mapping) and str(row.get("metric", "")).startswith("pg_")
    ]
    if len(rows) > 24:
        raise EconomicObservationError("selected observations exceed 24")
    if {row.get("metric") for row in rows} != set(PG_METRIC_KEYS):
        raise EconomicObservationError("selected metric key set is not exact")

    event_id = workspace.get("event_id")
    fact_ids = set()
    metric_scope_periods = set()
    checked: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise EconomicObservationError("selected row must be a mapping")
        if row.get("schema") != "event_fact.v1":
            raise EconomicObservationError("selected row schema mismatch")
        actual = set(row)
        present = "value" in row
        absence = "typed_absence" in row
        if actual == PRESENT_KEYS and not absence:
            expected_keys = PRESENT_KEYS
        elif actual == ABSENT_KEYS and not present:
            expected_keys = ABSENT_KEYS
        else:
            raise EconomicObservationError("selected row fields, value, and absence conflict")
        if row.get("event_id") != event_id:
            raise EconomicObservationError("selected row belongs to another event")
        fact_id = row.get("fact_id")
        if not isinstance(fact_id, str) or fact_id in fact_ids:
            raise EconomicObservationError("fact_id is missing or duplicate")
        fact_ids.add(fact_id)
        metric = row.get("metric")
        definition = _definition(metric)
        expected_fact_id = _fact_id(
            event_id,
            metric,
            row.get("period") if "value" in row else metric,
            definition.basis,
        )
        if fact_id != expected_fact_id:
            raise EconomicObservationError("fact_id does not follow event, metric, period, and basis identity")
        scope_key = (event_id, metric, definition.scope, row.get("period"), definition.basis)
        if scope_key in metric_scope_periods:
            raise EconomicObservationError("metric, scope, and period duplicate")
        metric_scope_periods.add(scope_key)

        if expected_keys is ABSENT_KEYS:
            absence_payload = row.get("typed_absence")
            if not isinstance(absence_payload, Mapping) or set(absence_payload) != TYPED_ABSENCE_KEYS:
                raise EconomicObservationError("typed_absence fields are unknown or incomplete")
            if absence_payload.get("schema") != ABSENCE_SCHEMA:
                raise EconomicObservationError("typed_absence schema mismatch")
            try:
                TypedAbsence(**{
                    "reason": absence_payload.get("reason"),
                    "subject": absence_payload.get("subject"),
                    "detail": absence_payload.get("detail"),
                    "missing_fields": tuple(absence_payload.get("missing_fields") or ()),
                    "event_id": absence_payload.get("event_id"),
                    "document_id": absence_payload.get("document_id"),
                })
            except ValueError as exc:
                raise EconomicObservationError(str(exc)) from exc
            if absence_payload.get("authority") != "context_only":
                raise EconomicObservationError("typed_absence authority is not display context")
            if not str(absence_payload.get("subject") or "").startswith(metric):
                raise EconomicObservationError("typed_absence subject does not match its metric")
            combined_text = (
                str(absence_payload.get("subject") or "")
                + " "
                + str(absence_payload.get("detail") or "")
            ).casefold()
            if "combined" in combined_text and not ("volume" in combined_text and "mix" in combined_text):
                raise EconomicObservationError("combined typed_absence subject names only one component")
            if absence_payload.get("event_id") != event_id:
                raise EconomicObservationError("typed_absence belongs to another event")
            if absence_payload.get("document_id") != workspace_document_id:
                raise EconomicObservationError("typed_absence belongs to another document")
            checked.append(dict(row))
            continue

        value = row.get("value")
        if definition.value_kind == "bounded_text":
            if not isinstance(value, str) or not value.strip() or len(value) > 240:
                raise EconomicObservationError("bounded text observation is invalid")
        else:
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
                raise EconomicObservationError("numeric observation must be finite and non-boolean")
        if row.get("unit") != definition.unit:
            raise EconomicObservationError("observation unit is not recognized")
        if row.get("basis") != definition.basis:
            raise EconomicObservationError("observation basis is not recognized")
        expected_period = (
            prior_end.isoformat()
            if metric in {"pg_prior_diluted_eps", "pg_prior_core_eps"}
            else current_end.isoformat()
        )
        if row.get("period") != expected_period:
            raise EconomicObservationError("observation period is not recognized")

        span = row.get("source_span")
        if not isinstance(span, Mapping):
            raise EconomicObservationError("present observation has no source span")
        if span.get("rights_profile") != PG_PRIVATE_RIGHTS_PROFILE:
            raise EconomicObservationError("observation span rights profile is not private")
        document_id = span.get("document_id")
        source = source_texts.get(document_id)
        if not isinstance(document_id, str) or not document_id or source is None:
            raise EconomicObservationError("byte-replayed observation has no caller-held source text")
        source_bytes = source.encode("utf-8")
        receipt = span.get("receipt")
        if not isinstance(receipt, Mapping):
            raise EconomicObservationError("present observation has no byte receipt")
        if receipt.get("source_sha256") != _sha256(source):
            raise EconomicObservationError("source digest does not replay")
        if receipt.get("segment_sha256") != _sha256(source):
            raise EconomicObservationError("segment digest does not replay")
        if receipt.get("segment_bytes") != len(source_bytes):
            raise EconomicObservationError("segment byte count does not replay")
        start = receipt.get("span_start_byte")
        end = receipt.get("span_end_byte")
        if (
            isinstance(start, bool) or not isinstance(start, int)
            or isinstance(end, bool) or not isinstance(end, int)
            or not 0 <= start <= end <= len(source_bytes)
        ):
            raise EconomicObservationError("byte span is invalid")
        replayed_bytes = source_bytes[start:end]
        if len(replayed_bytes) != end - start:
            raise EconomicObservationError("byte count is invalid")
        try:
            replayed_text = replayed_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EconomicObservationError("byte span is not UTF-8 aligned") from exc
        if hashlib.sha256(replayed_bytes).hexdigest() != receipt.get("text_sha256"):
            raise EconomicObservationError("span digest does not replay")
        if replayed_text != span.get("display_excerpt"):
            raise EconomicObservationError("display excerpt does not replay")
        if document_id != workspace_document_id:
            raise EconomicObservationError("present observation belongs to another document")
        if definition.value_kind == "bounded_text":
            replayed_value: Any = replayed_text
        elif replayed_text in {"-", "—", "–"}:
            if not _NEUTRAL_ZERO.search(source):
                raise EconomicObservationError("replay_mismatch: dash has no neutral-zero convention")
            replayed_value = 0.0
        else:
            replayed_value = parse_pg_literal(replayed_text, unit=definition.unit)
        if replayed_value is None or replayed_value != value:
            raise EconomicObservationError("replay_mismatch: replayed value differs from stored value")
        _verify_pg_replay(
            source=source,
            definition=definition,
            start=receipt.get("span_start_byte"),
            end=receipt.get("span_end_byte"),
            row=row,
            current_start=current_start,
            current_end=current_end,
            prior_end=prior_end,
        )

        checked.append(dict(row))
    return checked
