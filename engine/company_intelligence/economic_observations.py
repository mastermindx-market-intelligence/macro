"""Strict validation for the opt-in private PG economic observation selection."""
from __future__ import annotations

from datetime import date
import hashlib
import html
import json
import math
from numbers import Real
from typing import Any, Mapping

from .documents import ABSENCE_SCHEMA, TypedAbsence
from . import pg_envelope as _pg_envelope
from .pg_profile import (
    PG_COMBINED_VOLUME_MIX_METRICS,
    PG_DEFINITIONS,
    PG_METRIC_KEYS,
    PG_PRIVATE_RIGHTS_PROFILE,
    _OUT_OF_SCOPE,
    _char_span,
    _fiscal_identity,
    _normal,
    combined_volume_mix_presentation,
    document_period_verdict,
    expected_receipt_span,
    locate_pg_observation,
    neutral_zero_convention,
    parse_pg_literal,
    parse_release_blocks,
    pg_reconciliation_paragraph,
    pg_observation_present,
    pg_volume_cross_check,
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
    try:
        return next(item for item in PG_DEFINITIONS if item.metric == metric)
    except StopIteration as exc:
        raise EconomicObservationError("selected metric is not defined") from exc


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


def _validate_source_span(span: Mapping[str, Any], *, source: str) -> None:
    locator = span.get("locator")
    if not isinstance(locator, Mapping):
        raise EconomicObservationError("present observation has no source locator")
    start = locator.get("span_start_byte")
    end = locator.get("span_end_byte")
    if (
        isinstance(start, bool) or not isinstance(start, int)
        or isinstance(end, bool) or not isinstance(end, int)
        or start != span.get("receipt", {}).get("span_start_byte")
        or end != span.get("receipt", {}).get("span_end_byte")
    ):
        raise EconomicObservationError("source locator does not replay")
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
        or not 0 <= start < end <= len(source_bytes)
    ):
        raise EconomicObservationError("byte span is invalid")
    replayed_bytes = source_bytes[start:end]
    try:
        replayed_text = replayed_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EconomicObservationError("byte span is not UTF-8 aligned") from exc
    if hashlib.sha256(replayed_bytes).hexdigest() != receipt.get("text_sha256"):
        raise EconomicObservationError("span digest does not replay")
    if replayed_text != span.get("display_excerpt"):
        raise EconomicObservationError("display excerpt does not replay")


def _validate_row_structure(
    row: Mapping[str, Any],
    *,
    event_id: Any,
) -> tuple[Any, Any, str | None, frozenset[str]]:
    if row.get("schema") != "event_fact.v1":
        raise EconomicObservationError("selected row schema mismatch")
    actual = set(row)
    present = "value" in row
    absent = "typed_absence" in row
    if actual == PRESENT_KEYS and not absent:
        expected_keys = PRESENT_KEYS
    elif actual == ABSENT_KEYS and not present:
        expected_keys = ABSENT_KEYS
    else:
        raise EconomicObservationError("selected row fields, value, and absence conflict")
    if row.get("event_id") != event_id:
        raise EconomicObservationError("selected row belongs to another event")
    metric = row.get("metric")
    definition = _definition(metric)
    period = row.get("period") if expected_keys is PRESENT_KEYS else metric
    if row.get("fact_id") != _fact_id(event_id, metric, period, definition.basis):
        raise EconomicObservationError("fact_id does not follow event, metric, period, and basis identity")

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
        if tuple(absence_payload.get("missing_fields") or ()) != ():
            raise EconomicObservationError("typed_absence missing fields are invalid")
    else:
        value = row.get("value")
        if definition.value_kind == "bounded_text":
            if not isinstance(value, str) or not value.strip() or len(value) > 240:
                raise EconomicObservationError("bounded text observation is invalid")
        elif isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
            raise EconomicObservationError("numeric observation must be finite and non-boolean")
    return metric, definition, period, expected_keys


def _validate_fact_structure(
    row: Mapping[str, Any],
    *,
    event_id: Any,
    fact_ids: set[str],
    metric_scope_periods: set[tuple[Any, Any, Any, Any, Any]],
    duplicate_scope: bool = True,
) -> tuple[Any, Any, str | None, frozenset[str]]:
    metric, definition, period, expected_keys = _validate_row_structure(row, event_id=event_id)
    fact_id = row.get("fact_id")
    if not isinstance(fact_id, str) or fact_id in fact_ids:
        raise EconomicObservationError("fact_id is missing or duplicate")
    fact_ids.add(fact_id)
    scope_key = (event_id, metric, definition.scope, period, definition.basis)
    if duplicate_scope and scope_key in metric_scope_periods:
        raise EconomicObservationError("metric, scope, and period duplicate")
    metric_scope_periods.add(scope_key)
    return metric, definition, period, expected_keys


def _source_only_accession(source: str) -> str:
    number = int(_sha256(source)[:16], 16) % 10**18
    digits = f"{number:018d}"
    return f"{digits[:10]}-{digits[10:12]}-{digits[12:]}"


def _validate_envelope_span(row: Mapping[str, Any], *, source: str) -> None:
    span = row.get("source_span")
    if not isinstance(span, Mapping):
        raise EconomicObservationError("present envelope observation has no source span")
    receipt = span.get("receipt")
    if not isinstance(receipt, Mapping):
        raise EconomicObservationError("present envelope observation has no byte receipt")
    start = receipt.get("span_start_byte")
    end = receipt.get("span_end_byte")
    source_bytes = source.encode("utf-8")
    if (
        isinstance(start, bool) or not isinstance(start, int)
        or isinstance(end, bool) or not isinstance(end, int)
        or not 0 <= start < end <= len(source_bytes)
    ):
        raise EconomicObservationError("present envelope observation has an invalid byte span")
    locator = span.get("locator")
    if isinstance(locator, Mapping):
        locator_start = locator.get("span_start_byte")
        locator_end = locator.get("span_end_byte")
        if locator_start != start or locator_end != end:
            raise EconomicObservationError("present envelope observation locator disagrees with its receipt")
    try:
        raw = source_bytes[start:end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EconomicObservationError("present envelope observation span is not UTF-8 aligned") from exc
    if "<" in raw or any(character.isspace() for character in raw):
        raise EconomicObservationError("present envelope observation span is not a raw literal")
    gap_start = source_bytes.rfind(b">", 0, start) + 1
    gap_end = source_bytes.find(b"<", end)
    if gap_end < 0:
        gap_end = len(source_bytes)
    for gap in (source_bytes[gap_start:start], source_bytes[end:gap_end]):
        if not all(character.isspace() for character in html.unescape(gap.decode("utf-8"))):
            raise EconomicObservationError("present envelope observation span is not a whole literal")
    unescaped = html.unescape(raw)
    if any(character.isspace() for character in unescaped):
        raise EconomicObservationError("present envelope observation decodes to whitespace")
    unit = row.get("unit")
    if (unit == "usd_per_share" and "%" in unescaped) or (unit in {"percent", "percentage_points"} and "$" in unescaped):
        raise EconomicObservationError("present envelope observation literal holds a marker its unit forbids")
    value = 0.0 if unescaped == "\u2014%" and unit in {"percent", "percentage_points"} else _pg_envelope._literal(unescaped)
    if value is None or value != row.get("value"):
        raise EconomicObservationError("present envelope observation value does not parse from its span")


def _validate_envelope_rows(
    *,
    rows: list[Mapping[str, Any]],
    source: str,
    fiscal_scope: tuple[str, str, str, str],
    event_id: Any,
    workspace_document_id: str,
) -> list[dict[str, Any]]:
    from ..earnings_release.binding import bind_release_document

    admission = _pg_envelope.admit(source, fiscal_scope)
    definitions = {definition.metric: definition for definition in PG_DEFINITIONS}
    if admission.code == "F1-Q" and admission.roles is not None:
        bound = bind_release_document(
            cik=80424,
            accession=_source_only_accession(source),
            body=source,
        )
        document = _pg_envelope._document(source)
        replayed_facts = _pg_envelope.extract(
            document,
            admission,
            PG_DEFINITIONS,
            bound=bound,
            document_id=workspace_document_id,
            event_id=event_id,
            fiscal_period={"calendar_end": fiscal_scope[1]},
            fiscal_scope=fiscal_scope,
        )
        replayed = {
            row["metric"]: json.loads(json.dumps(row))
            for row in replayed_facts
        }
    else:
        replayed = {
            metric: json.loads(json.dumps(row))
            for metric in definitions
            for row in [{
                "schema": "event_fact.v1",
                "fact_id": _fact_id(event_id, metric, metric, definitions[metric].basis),
                "event_id": event_id,
                "metric": metric,
                "typed_absence": {
                    "schema": ABSENCE_SCHEMA,
                    "authority": "context_only",
                    "reason": "no_span_addressable_evidence",
                    "subject": metric,
                    "detail": f"envelope_refused:{admission.code}",
                    "missing_fields": [],
                    "event_id": event_id,
                    "document_id": workspace_document_id,
                },
            }]
        }

    if any(row.get("metric") not in definitions for row in rows):
        raise EconomicObservationError("selected metric is not defined")
    if len(rows) != len({row.get("metric") for row in rows}):
        raise EconomicObservationError("selected metric is duplicate")
    if {row.get("metric") for row in rows} != set(definitions):
        raise EconomicObservationError("selected metric key set is not exact")

    fact_ids: set[str] = set()
    metric_scope_periods: set[tuple[Any, Any, Any, Any, Any]] = set()
    checked: list[dict[str, Any]] = []
    for row in rows:
        _validate_fact_structure(
            row,
            event_id=event_id,
            fact_ids=fact_ids,
            metric_scope_periods=metric_scope_periods,
            duplicate_scope=False,
        )
        metric = row.get("metric")
        normalized = json.loads(json.dumps(dict(row)))
        if normalized != replayed[metric]:
            raise EconomicObservationError("selected observation does not replay from source bytes")
        if "value" in row:
            _validate_envelope_span(row, source=source)
        checked.append(dict(row))
    return checked


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
    """Replay the extractor's SELECTION, not just the cell layout (R35, R45, R46).

    The document verdict, the reconciliation paragraph, the admitted tables, the unique cell and its header
    all come from the same pg_profile functions the extractor bound with, over the caller-held source text.
    """
    fiscal_year, quarter = _fiscal_identity(current_start, current_end)
    identity = (fiscal_year, quarter, current_end)
    if document_period_verdict(parse_release_blocks(source), identity) in _OUT_OF_SCOPE:
        raise EconomicObservationError("replay_mismatch: the document's period signals do not name the admitted fiscal quarter")
    if not isinstance(start, int) or not isinstance(end, int):
        raise EconomicObservationError("replay_mismatch: replay location is invalid")
    try:
        char_start, char_end = _char_span(source, start, end)
    except ValueError as exc:
        raise EconomicObservationError(f"replay_mismatch: {exc}") from exc
    if definition.value_kind == "bounded_text":
        paragraph = pg_reconciliation_paragraph(source, definition, identity)
        span = getattr(paragraph, "source_span", None)
        if paragraph is None or span is None or not (span.char_start <= char_start and char_end <= span.char_end):
            raise EconomicObservationError("replay_mismatch: the replayed text is not the uniquely addressable reconciliation paragraph")
        if row.get("value") != paragraph.text.strip():
            raise EconomicObservationError("replay_mismatch: replayed text differs from the reconciliation paragraph")
        if expected_receipt_span(source, span.char_start, span.char_end, paragraph.text.strip()) != (start, end):
            raise EconomicObservationError("replay_mismatch: replayed bytes are not the paragraph's receipt")
        return
    located = locate_pg_observation(source, definition, current_start=current_start, current_end=current_end, prior_end=prior_end)
    if located is None:
        raise EconomicObservationError("replay_mismatch: no unique heading, row label, and column header addresses this observation")
    cell, header, column, period = located
    if not (cell.char_start <= char_start and char_end <= cell.char_end):
        raise EconomicObservationError("replay_mismatch: replay location is not the addressed cell")
    if expected_receipt_span(source, cell.char_start, cell.char_end, cell.text.strip()) != (start, end):
        raise EconomicObservationError("replay_mismatch: replayed bytes are not the cell's receipt")
    try:
        row_label, replayed_header, replayed_column = replay_table_layout(
            source,
            start=int(start),
            end=int(end),
            header_forms=(definition.column_label,) if definition.column_label else (header,),
            identity=identity,
        )
    except ValueError as exc:
        raise EconomicObservationError(f"replay_mismatch: {exc}") from exc
    if definition.row_label and _normal(row_label) != _normal(definition.row_label):
        raise EconomicObservationError("replay_mismatch: replayed row differs from the metric definition")
    if replayed_column != column or _normal(replayed_header) != _normal(header):
        raise EconomicObservationError("replay_mismatch: replayed column differs from the addressed observation")
    if definition.column_label and _normal(header) != _normal(definition.column_label):
        raise EconomicObservationError("replay_mismatch: replayed column differs from the metric definition")
    if row.get("period") != period:
        raise EconomicObservationError("replay_mismatch: replayed period differs from the stored observation")
    if definition.metric == "pg_total_volume_growth_pct" and not pg_volume_cross_check(
        source, value=float(row.get("value")), current_start=current_start, current_end=current_end, prior_end=prior_end
    ):
        raise EconomicObservationError("replay_mismatch: the document carries conflicting statements of total volume growth")


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
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in source_texts.items()):
        raise EconomicObservationError("source_texts must map document ids to text")
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
    release_text = source_texts.get(workspace_document_id)
    if isinstance(release_text, str) and _pg_envelope._wrapped(release_text):
        facts = workspace.get("facts")
        if not isinstance(facts, list):
            raise EconomicObservationError("workspace facts must be a list")
        if any(not isinstance(row, Mapping) for row in facts):
            raise EconomicObservationError("workspace facts must be mappings")
        if any(not isinstance(row.get("metric"), str) or not row.get("metric") for row in facts):
            raise EconomicObservationError("workspace facts must each name a metric")
        envelope_rows = [
            row for row in facts if str(row.get("metric", "")).startswith("pg_")
        ]
        return _validate_envelope_rows(rows=envelope_rows, source=release_text, fiscal_scope=fiscal_scope, event_id=workspace.get("event_id"), workspace_document_id=workspace_document_id)

    facts = workspace.get("facts")
    if not isinstance(facts, list):
        raise EconomicObservationError("workspace facts must be a list")
    if any(not isinstance(row, Mapping) for row in facts):
        raise EconomicObservationError("workspace facts must be mappings")
    if any(not isinstance(row.get("metric"), str) or not row.get("metric") for row in facts):
        raise EconomicObservationError("workspace facts must each name a metric")
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
        metric, definition, period, expected_keys = _validate_fact_structure(
            row,
            event_id=event_id,
            fact_ids=fact_ids,
            metric_scope_periods=metric_scope_periods,
        )

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
            subject = str(absence_payload.get("subject") or "")
            if subject == f"{metric} combined volume/mix":
                # R33/R39: the combined form is lawful only for a volume/mix observation, and only when the
                # document's one in-scope drivers table actually presents volume and mix as a combined column.
                if metric not in PG_COMBINED_VOLUME_MIX_METRICS:
                    raise EconomicObservationError("combined typed_absence names an observation that is never combined")
                release_source = source_texts.get(workspace_document_id)
                if not isinstance(release_source, str) or not combined_volume_mix_presentation(
                    release_source, current_start=current_start, current_end=current_end, prior_end=prior_end
                ):
                    raise EconomicObservationError("combined typed_absence has no combined volume/mix drivers column in the source")
                # R85: a combined absence may not hide a separately disclosed value either.
                if pg_observation_present(release_source, definition, current_start=current_start, current_end=current_end, prior_end=prior_end):
                    raise EconomicObservationError("combined typed_absence hides an observation the source uniquely addresses")
            elif subject != metric:
                raise EconomicObservationError("typed_absence subject is neither its metric nor the combined volume/mix form")
            else:
                # R80 (round-6 disposition (a)): a plain absence may not hide a value the extractor's own decision
                # path would bind from the caller-held source.
                release_source = source_texts.get(workspace_document_id)
                if isinstance(release_source, str) and pg_observation_present(
                    release_source, definition, current_start=current_start, current_end=current_end, prior_end=prior_end
                ):
                    raise EconomicObservationError("typed_absence hides an observation the source uniquely addresses")
            if absence_payload.get("event_id") != event_id:
                raise EconomicObservationError("typed_absence belongs to another event")
            if absence_payload.get("document_id") != workspace_document_id:
                raise EconomicObservationError("typed_absence belongs to another document")
        if expected_keys is ABSENT_KEYS:
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
            if not neutral_zero_convention(source):
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
