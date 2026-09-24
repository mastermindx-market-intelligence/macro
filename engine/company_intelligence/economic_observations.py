"""Strict validation for the opt-in private PG economic observation selection."""
from __future__ import annotations

from datetime import date
import hashlib
import math
import re
from numbers import Real
from typing import Any, Mapping

from .documents import ABSENCE_SCHEMA, TypedAbsence
from .pg_profile import PG_DEFINITIONS, PG_METRIC_KEYS, PG_PRIVATE_RIGHTS_PROFILE, parse_pg_literal


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


_PG_FISCAL_QUARTERS = {4: 4, 5: 4, 6: 4, 7: 1, 8: 1, 9: 1, 10: 2, 11: 2, 12: 2, 1: 3, 2: 3, 3: 3}
_NEUTRAL_ZERO = re.compile(r"\bdash(?:es)?\s+(?:means|represent[sd]?)\s+zero\b", re.IGNORECASE)
_TABLE_CELLS = re.compile(rb"<t[dh][^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)



def _cell_text(fragment: bytes) -> str:
    text = re.sub(rb"<[^>]+>", b"", fragment)
    return text.decode("utf-8", errors="strict").strip().replace("&amp;", "&")


def _verify_pg_replay(
    *,
    source: str,
    definition: Any,
    start: Any,
    end: Any,
    row: Mapping[str, Any],
    current_end: date,
    prior_end: date,
) -> None:
    source_bytes = source.encode("utf-8")
    if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(source_bytes):
        raise EconomicObservationError("replay_mismatch: replay location is invalid")
    if definition.value_kind == "bounded_text":
        context = source[max(0, start - 240):end].casefold()
        if definition.row_label and definition.row_label.casefold() not in context:
            raise EconomicObservationError("replay_mismatch: replayed basis differs from the metric definition")
        return
    table_start = source_bytes.rfind(b"<table", 0, start)
    table_end = source_bytes.find(b"</table>", end)
    if table_start < 0 or table_end < 0:
        raise EconomicObservationError("replay_mismatch: cell has no enclosing table")
    cells: list[tuple[bytes, int, int]] = []
    for match in _TABLE_CELLS.finditer(source_bytes, table_start, table_end):
        cells.append((match.group(1), match.start(1), match.end(1)))
    target = next((index for index, cell in enumerate(cells) if cell[1] <= start and end <= cell[2]), None)
    if target is None:
        raise EconomicObservationError("replay_mismatch: span is not a table cell")
    try:
        texts = [_cell_text(cell[0]) for cell in cells]
    except UnicodeDecodeError as exc:
        raise EconomicObservationError("replay_mismatch: table bytes are not UTF-8 aligned") from exc
    opens = list(re.finditer(rb"<tr[^>]*>", source_bytes[table_start:end], re.IGNORECASE))
    if opens:
        row_open = opens[-1].start() + table_start
        row_start = next(
            index for index, cell in enumerate(cells)
            if cell[1] > row_open and cell[1] <= start
        )
    else:
        row_start = target
        while row_start > 0 and texts[row_start - 1]:
            row_start -= 1
    row_label = texts[row_start]
    if definition.row_label and row_label.casefold() != definition.row_label.casefold():
        raise EconomicObservationError("replay_mismatch: replayed row differs from the metric definition")
    header = texts[:row_start]
    if opens:
        header_open = opens[0].start() + table_start
        header = [text for index, text in enumerate(texts) if cells[index][1] >= header_open and index < row_start]
    column = target - row_start
    if not definition.column_label and column == 0:
        column = 1
    expected_period = prior_end if row.get("metric", "").startswith("pg_prior_") else current_end
    period_forms = {
        expected_period.isoformat(),
        str(expected_period.year),
        expected_period.strftime("%B %-d, %Y"),
    }
    if definition.column_label:
        if column >= len(header) or header[column] != definition.column_label:
            raise EconomicObservationError("replay_mismatch: replayed column differs from the metric definition")
        return
    if column >= len(header) or header[column] not in period_forms:
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
    expected_quarter = _PG_FISCAL_QUARTERS[current_start.month]
    if str(fiscal_period.get("quarter")) != str(expected_quarter):
        raise EconomicObservationError("workspace quarter does not match fiscal_scope")

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
        if fact_id != f"fact_{metric}":
            raise EconomicObservationError("fact_id does not follow event, metric, period, and basis identity")
        definition = _definition(metric)
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
            if absence_payload.get("event_id") != event_id:
                raise EconomicObservationError("typed_absence belongs to another event")
            if absence_payload.get("document_id") not in source_texts:
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
        if definition.value_kind == "bounded_text":
            replayed_value: Any = replayed_text
        elif replayed_text in {"-", "—", "–"}:
            before = source[: receipt.get("span_start_byte")]
            if not _NEUTRAL_ZERO.search(before):
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
            current_end=current_end,
            prior_end=prior_end,
        )

        checked.append(dict(row))
    return checked
