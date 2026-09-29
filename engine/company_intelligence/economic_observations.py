"""Strict validation for the opt-in private PG economic observation selection."""
from __future__ import annotations

import bisect
from datetime import date
from fractions import Fraction
import functools
import hashlib
import json
import math
from numbers import Real
import re
from typing import Any, Iterator, Mapping

from ..earnings_release.receipts import unescape as _unescape
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
    if type(value) is not tuple or len(value) != 4 or any(type(item) is not str for item in value):
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


def _finite(value: Real) -> bool:
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False


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
    try:
        fact_id = _fact_id(event_id, metric, period, definition.basis)
    except RecursionError as exc:
        raise EconomicObservationError("selected row is nested too deeply") from exc
    if row.get("fact_id") != fact_id:
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
        except (TypeError, ValueError) as exc:
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
        elif isinstance(value, bool) or not isinstance(value, Real) or not _finite(value):
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
    try:
        hash(scope_key)
    except (TypeError, RecursionError) as exc:
        raise EconomicObservationError("selected row period is not a scalar") from exc
    if duplicate_scope and scope_key in metric_scope_periods:
        raise EconomicObservationError("metric, scope, and period duplicate")
    metric_scope_periods.add(scope_key)
    return metric, definition, period, expected_keys


def _source_only_accession(source: str) -> str:
    number = int(_sha256(source)[:16], 16) % 10**18
    digits = f"{number:018d}"
    return f"{digits[:10]}-{digits[10:12]}-{digits[12:]}"


# R192: the span check reads characters, as the reader does, and reports each unit at its bytes.  A byte pattern
# counted a reference's 32-character name in bytes, so it could end inside a character.
_PRINT_UNIT = re.compile(
    r"(<!--.*?-->)|(</?([A-Za-z][A-Za-z0-9]*)[^>]*>)|(<[^>]*>)"
    r"|(&(?:#[0-9]+;?|#[xX][0-9a-fA-F]+;?|[^\t\n\f <&#;]{1,32};?))|[^<&]+|[<&]",
    re.S,
)
# R190: a tag sets a token off only where an HTML5 tree builder acts on it whatever else is open.  Each start tag
# here opens an element (admission refuses the table tags a builder would ignore), but an end tag with no such
# element open is ignored, and the text on either side of it is one run.  Only </p> (an empty paragraph when none
# is open) and </br> (read as <br>) act without one, so an end tag counts only if it is one of those two.
_SEPARATING = frozenset({"td", "th", "tr", "table", "p", "div", "br"})
_SEPARATING_END = frozenset({"p", "br"})
_RAW_NAMES = frozenset(_pg_envelope._RAW_TEXT_CLOSE)
_UNPRINTED_RAW = frozenset({"raw:script", "raw:style"})
_LAYOUT_SPACE = frozenset(" \t\n\r\f\xa0")


def _print_matches(fragment: bytes) -> Iterator[tuple[int, int, re.Match[str]]]:
    try:
        text = fragment.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EconomicObservationError("present envelope observation text is not UTF-8 aligned") from exc
    char_position = byte_position = 0
    for match in _PRINT_UNIT.finditer(text):
        start, end = match.span()
        byte_start = byte_position + len(text[char_position:start].encode("utf-8"))
        byte_end = byte_start + len(match.group(0).encode("utf-8"))
        yield byte_start, byte_end, match
        char_position, byte_position = end, byte_end


@functools.lru_cache(maxsize=4)
def _printed_units(source_bytes: bytes) -> tuple[tuple[tuple[int, int, str], ...], tuple[int, ...]]:
    units: list[tuple[int, int, str]] = []
    raw_name: str | None = None
    for start, end, match in _print_matches(source_bytes):
        if raw_name is not None:
            closing = match.group(2) is not None and match.group(0).startswith("</") and match.group(3).lower() == raw_name
            units.append((start, end, "markup" if closing else "raw:" + raw_name))
            raw_name = None if closing else raw_name
        elif match.group(1) is not None:
            units.append((start, end, "comment"))
        elif match.group(4) is not None:
            units.append((start, end, "markup"))
        elif match.group(2) is not None:
            name = match.group(3).lower()
            end_tag = match.group(0).startswith("</")
            units.append((start, end, "separator" if name in (_SEPARATING_END if end_tag else _SEPARATING) else "markup"))
            if not end_tag and name in _RAW_NAMES:
                raw_name = name
        else:
            units.append((start, end, "text"))
    return tuple(units), tuple(unit[0] for unit in units)


def _drops_a_reference(fragment: bytes) -> bool:
    return any(
        match.group(5) is not None and not _unescape(match.group(5))
        for _start, _end, match in _print_matches(fragment)
    )


def _whole_printed_token(source_bytes: bytes, start: int, end: int) -> bool:
    units, starts = _printed_units(source_bytes)
    first = bisect.bisect_right(starts, start) - 1
    last = bisect.bisect_right(starts, end - 1) - 1
    kinds = {kind for _start, _end, kind in units[first:last + 1]}
    if first == last and kinds <= {"comment"} | _UNPRINTED_RAW:
        return True
    outer = units[first][0], units[last][1]
    pieces = source_bytes[outer[0]:start], source_bytes[start:end], source_bytes[end:outer[1]]
    whole = _unescape(source_bytes[outer[0]:outer[1]].decode("utf-8"))
    if "".join(_unescape(piece.decode("utf-8")) for piece in pieces) != whole:
        return False
    if kinds != {"text"} and not (first == last and next(iter(kinds)).startswith("raw:")):
        return False

    def separated(index: int, step: int, fragment: bytes, edge: Any) -> bool:
        printed = _unescape(fragment.decode("utf-8"))
        if fragment and units[index][2].startswith("raw:") and edge(fragment.decode("utf-8")) not in _LAYOUT_SPACE:
            return False
        while not printed:
            index += step
            if not 0 <= index < len(units) or units[index][2] == "separator":
                return True
            kind = units[index][2]
            if kind in ("comment", "markup") or kind in _UNPRINTED_RAW:
                continue
            printed = _unescape(source_bytes[units[index][0]:units[index][1]].decode("utf-8"))
            if not printed or kind.startswith("raw:"):
                return False
        return edge(printed) in _LAYOUT_SPACE

    return (
        separated(first, -1, source_bytes[units[first][0]:start], lambda printed: printed[-1])
        and separated(last, 1, source_bytes[end:units[last][1]], lambda printed: printed[0])
    )


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
    if "<" in raw or any(character.isspace() for character in raw) or _drops_a_reference(source_bytes[start:end]):
        raise EconomicObservationError("present envelope observation span is not a raw literal")
    gap_start = source_bytes.rfind(b">", 0, start) + 1
    gap_end = source_bytes.find(b"<", end)
    if gap_end < 0:
        gap_end = len(source_bytes)
    for gap in (source_bytes[gap_start:start], source_bytes[end:gap_end]):
        if _drops_a_reference(gap) or not all(
            character in _LAYOUT_SPACE for character in _unescape(gap.decode("utf-8"))
        ):
            raise EconomicObservationError("present envelope observation span is not a whole literal")
    unescaped = _unescape(raw)
    if any(character.isspace() for character in unescaped):
        raise EconomicObservationError("present envelope observation decodes to whitespace")
    unit = row.get("unit")
    if (unit == "usd_per_share" and "%" in unescaped) or (unit in {"percent", "percentage_points"} and "$" in unescaped):
        raise EconomicObservationError("present envelope observation literal holds a marker its unit forbids")
    value = 0.0 if unescaped == "\u2014%" and unit in {"percent", "percentage_points"} else _pg_envelope._literal(unescaped)
    if value is None or value != row.get("value"):
        raise EconomicObservationError("present envelope observation value does not parse from its span")
    if not _whole_printed_token(source_bytes, start, end):
        raise EconomicObservationError("present envelope observation span is not a whole printed token")


def _validate_envelope_rows(
    *,
    rows: list[Mapping[str, Any]],
    source: str,
    fiscal_scope: tuple[str, str, str, str],
    event_id: Any,
    workspace_document_id: str,
) -> list[dict[str, Any]]:
    from ..earnings_release.binding import bind_release_document

    if not isinstance(event_id, str):
        raise EconomicObservationError("workspace event identity is not a string")
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
        try:
            serialised = json.dumps(dict(row), sort_keys=True)
        except (TypeError, ValueError, RecursionError) as exc:
            raise EconomicObservationError("selected observation is not JSON data") from exc
        if serialised != json.dumps(replayed[metric], sort_keys=True):
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


# R189: the validator prints and encodes what a workspace carries (str() of its fields, the fact identity's bytes,
# the replay's event identity).  Three kinds of value a tampered workspace can carry make that raise instead of
# refuse: a value nested deeper than the interpreter prints, an integer with more digits than it converts (never at
# 640 or fewer, the least limit it can be set to), and text holding a lone surrogate, which no bytes decode to.
# One walk at the entry refuses all three, and bounds its own work, so nothing after it meets them.
# R193: the walk admits a closed set of types, each by its exact type, and refuses every other value: the types a
# JSON document parses to (dict, list, str, int, float, bool, None), a tuple, which serialises as the list it
# replays to (R136), and a Fraction, which the value checks read as a real number (R134).  R189's walk descended a
# list of containers and passed what it did not list, so a range, a deque, a path or a Decimal went unvisited.
# R195: the walk admits an int or a Fraction only in the form Python builds one: exact int parts, a positive
# denominator, lowest terms.  A Fraction's two slots can be assigned anything, and the checks after the walk
# divide, print and compare what they hold.  The walk and the entry decide by identity alone, type(value) is T,
# so no argument runs code of its own: an isinstance test or a set lookup asks the value's class for its
# __class__, __hash__ or __eq__, and a metaclass can define each.
_LONE_SURROGATE = re.compile("[\ud800-\udfff]")
_PRINTABLE_DEPTH = 32
_PRINTABLE_VALUES = 100_000
_PRINTABLE_BOUND = 10**640


def _unprintable(value: Any) -> bool:
    stack = [(value, 1)]
    visited = 0
    while stack:
        item, depth = stack.pop()
        visited += 1
        if depth > _PRINTABLE_DEPTH or visited > _PRINTABLE_VALUES:
            return True
        kind = type(item)
        if kind is str:
            if _LONE_SURROGATE.search(item):
                return True
        elif kind is int or kind is Fraction:
            numerator, denominator = item.numerator, item.denominator
            if (
                type(numerator) is not int
                or type(denominator) is not int
                or not 0 < denominator < _PRINTABLE_BOUND
                or abs(numerator) >= _PRINTABLE_BOUND
                or math.gcd(numerator, denominator) != 1
            ):
                return True
        elif kind is dict:
            stack.extend((part, depth + 1) for entry in item.items() for part in entry)
        elif kind is list or kind is tuple:
            stack.extend((entry, depth + 1) for entry in item)
        elif kind is not float and kind is not bool and item is not None:
            return True
    return False


def validate_selected_facts(
    workspace: Mapping[str, Any],
    *,
    source_texts: Mapping[str, str],
    fiscal_scope: tuple[str, str, str, str],
) -> list[dict[str, Any]]:
    if type(workspace) is not dict and not _unprintable(workspace):
        raise EconomicObservationError("workspace must be a mapping")
    if type(source_texts) is not dict or any(
        type(key) is not str or type(value) is not str
        or _LONE_SURROGATE.search(key) or _LONE_SURROGATE.search(value)
        for key, value in source_texts.items()
    ):
        raise EconomicObservationError("source_texts must map document ids to text")
    if _unprintable(workspace):
        raise EconomicObservationError(
            "workspace holds a value it cannot print: a type it does not admit, nested too deep, too many values, "
            "a number too long, or text no bytes decode to"
        )
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
    sources = workspace.get("sources", [])
    if not isinstance(sources, (list, tuple)):
        raise EconomicObservationError("workspace sources must be a list")
    releases = [
        source for source in sources
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
