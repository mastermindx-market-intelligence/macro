"""The exact scenario export: one typed row per quantity and assumption (SPEC_U2 §1.4).

The input is the evaluate route's 200 envelope (``view``, ``inputs``, ``result``,
``facts_unchanged``, ``compatibility``, ``authority`` — plus the ``scenario``
record and, for a restore without a result, an ``outcome``) or a restore's
``current``.  The output is a :class:`DeterministicExport` — the same frozen
record the forensics query export returns — in ``csv`` or ``parquet``, with:

* one row per unit-bearing quantity of the composed result (capacity, supply,
  funding and coverage quantities never share a row or a column), and one
  ``assumption`` row per scenario assumption (price basis, dates, actions, the
  rule-pack edition) — a fact never rides an assumption row;
* ``value`` as exact decimal/integer TEXT — never a float, never coerced — and
  an absent value as the EMPTY string with ``value_kind=absent`` (never ``0``,
  never ``NaN``);
* an explicit ``unit`` and ``value_kind`` on every row, in a fixed column order
  that is byte-identical across formats (``test_a38``-style parity);
* no ``user_id``, no label, no e-mail, no saved-row field anywhere (A40): the
  user's label is display text and is deliberately never a row.

Text cells are guarded by ``query._csv_safe`` (imported, never copied); the
``value`` column is exempt exactly when ``value_kind`` is decimal or integer, so
a negative Decimal stays numeric text while a probe string in a text cell cannot
become a formula.  Parquet stores every column verbatim as STRING.

Deterministic and offline: no I/O beyond the in-memory payload, no wall clock,
no float anywhere; two exports of one envelope are byte-identical.
"""
from __future__ import annotations

import csv
import io
import re
from types import MappingProxyType
from typing import Any, Mapping

from engine.fundamental_forensics.query import DeterministicExport, _csv_safe
from engine.fundamental_forensics.query_exports import (
    CSV_MEDIA_TYPE,
    EXPORT_FORMATS,
    PARQUET_MEDIA_TYPE,
)

SCENARIO_EXPORT_SCHEMA = "capital_structure.scenario_export.v1"

#: Fixed column order (SPEC_U2 §1.4).
SCENARIO_EXPORT_COLUMNS = (
    "section",
    "issuer_id",
    "item_id",
    "name",
    "value",
    "unit",
    "value_kind",
    "as_of",
    "available_at",
    "source_accession",
    "source_manifest_id",
    "rule_id",
    "assumption_kind",
    "state_generation_id",
    "inputs_generation_id",
    "scenario_id",
    "result_id",
)

#: Closed row sections.  ``fact`` is reserved for a caller-supplied facts echo;
#: the evaluate envelope carries facts only inside the composed components.
SECTIONS = (
    "fact",
    "assumption",
    "capacity",
    "supply",
    "funding",
    "action_check",
    "joint_check",
    "coverage",
    "blocker",
    "unknown",
    "provenance",
)

VALUE_KINDS = ("decimal", "integer", "date", "text", "absent")

#: Explicit per-row units: the contract's own unit tokens verbatim, plus the
#: two non-quantity units.
UNITS = ("usd", "shares", "votes", "percent", "ratio", "days", "date", "text")

_INTEGER_TEXT = re.compile(r"^-?[0-9]+$")

# Component paths -> their section.
_COMPONENT_SECTIONS = (
    ("capacity_envelope", "capacity"),
    ("supply_envelope", "supply"),
    ("funding_schedule", "funding"),
    ("coverage", "coverage"),
)


class ScenarioExportError(ValueError):
    """The envelope cannot be exported as requested (nothing is invented)."""


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _row(
    *,
    section: str,
    envelope_ids: Mapping[str, str],
    item_id: str,
    name: str,
    value: Any,
    unit: str,
    value_kind: str,
    assumption_kind: str = "",
    available_at: str = "",
    source_manifest_id: str = "",
) -> dict[str, str]:
    return {
        "section": section,
        "issuer_id": envelope_ids["issuer_id"],
        "item_id": item_id,
        "name": name,
        "value": _text(value),
        "unit": unit,
        "value_kind": value_kind,
        "as_of": envelope_ids["as_of"],
        "available_at": available_at,
        "source_accession": "",
        "source_manifest_id": source_manifest_id,
        "rule_id": "",
        "assumption_kind": assumption_kind,
        "state_generation_id": envelope_ids["state_generation_id"],
        "inputs_generation_id": envelope_ids["inputs_generation_id"],
        "scenario_id": envelope_ids["scenario_id"],
        "result_id": envelope_ids["result_id"],
    }


def _envelope_ids(envelope: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, str]:
    view = envelope.get("view") if isinstance(envelope.get("view"), Mapping) else {}
    inputs = envelope.get("inputs") if isinstance(envelope.get("inputs"), Mapping) else {}
    receipt = result.get("receipt") if isinstance(result.get("receipt"), Mapping) else {}
    state_generation_id = (
        _text(view.get("generation_id")) or _text(envelope.get("state_generation_id"))
    )
    inputs_generation_id = (
        _text(envelope.get("inputs_generation_id"))
        or _text(inputs.get("generation_id"))
        or _text(view.get("inputs_generation_id"))
    )
    scenario_id = (
        _text(view.get("scenario_id")) or _text(result.get("scenario_id")) or _text(receipt.get("scenario_id"))
    )
    return {
        "issuer_id": _text(envelope.get("issuer_id")) or _text(view.get("issuer_id")),
        "as_of": _text(result.get("as_of")),
        "state_generation_id": state_generation_id,
        "inputs_generation_id": inputs_generation_id,
        "scenario_id": scenario_id,
        "result_id": _text(result.get("result_id")),
    }


def _is_quantity(node: Any) -> bool:
    """A unit-bearing quantity record: ``Quantity`` / ``SignedQuantity`` as
    published (``unit`` + ``status`` + ``share_basis`` present)."""
    return (
        isinstance(node, Mapping)
        and "unit" in node
        and "status" in node
        and "share_basis" in node
    )


def _walk_quantities(
    node: Any,
    path: tuple[str, ...],
    container: Mapping[str, Any] | None,
    out: list[tuple[tuple[str, ...], str, Mapping[str, Any] | None, Mapping[str, Any]]],
) -> None:
    """Every unit-bearing quantity under ``node``, with its path, its leaf key,
    the nearest id-bearing container, and the quantity record itself."""
    if isinstance(node, Mapping):
        if _is_quantity(node):
            out.append((path, path[-1] if path else "", container, node))
            return
        near = ("route_id", "constraint_id", "flow_id", "period_start")
        container = node if any(key in node for key in near) else container
        for key in sorted(node):
            _walk_quantities(node[key], (*path, str(key)), container, out)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _walk_quantities(item, (*path, f"[{index}]"), container, out)


def _item_id(path: tuple[str, ...], container: Mapping[str, Any] | None) -> str:
    if container is not None:
        for key in ("route_id", "constraint_id", "flow_id"):
            if container.get(key):
                return _text(container[key])
        if container.get("period_start") and container.get("period_end"):
            return f"{container['period_start']}/{container['period_end']}"
    return ".".join(segment for segment in path if not segment.startswith("[")) or "result"


def _section_for(path: tuple[str, ...]) -> str:
    head = path[0] if path else ""
    for component, section in _COMPONENT_SECTIONS:
        if head == component:
            return section
    return "supply"


def _value_kind_of(value_text: str) -> str:
    if not value_text:
        return "absent"
    if _INTEGER_TEXT.match(value_text):
        return "integer"
    return "decimal"


def _quantity_rows(
    result: Mapping[str, Any],
    envelope_ids: Mapping[str, str],
    *,
    section: str,
    sub_paths: tuple[tuple[Any, ...], ...],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    found: list[tuple[tuple[str, ...], str, Mapping[str, Any] | None, Mapping[str, Any]]] = []
    for sub_path in sub_paths:
        if not sub_path:
            continue
        node: Any = result
        for key in sub_path:
            node = node[key]
        _walk_quantities(node, (sub_path[0],), None, found)
    for path, leaf, container, quantity in found:
        status = _text(quantity.get("status"))
        value_text = _text(quantity.get("value")) if status == "known" else ""
        provenance = quantity.get("provenance") if isinstance(quantity.get("provenance"), Mapping) else {}
        evidence = provenance.get("evidence") if isinstance(provenance.get("evidence"), list) and provenance.get("evidence") else []
        rows.append(
            _row(
                section=section,
                envelope_ids=envelope_ids,
                item_id=_item_id(path, container),
                name=leaf,
                value=value_text,
                unit=_text(quantity.get("unit")),
                value_kind="absent" if status != "known" else _value_kind_of(value_text),
                available_at=_text(provenance.get("available_at")) if provenance else "",
                source_manifest_id=_text(evidence[0].get("manifest_id")) if evidence else "",
            )
        )
    return rows


def _assumption_rows(
    envelope: Mapping[str, Any],
    result: Mapping[str, Any],
    envelope_ids: Mapping[str, str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    scenario = envelope.get("scenario") if isinstance(envelope.get("scenario"), Mapping) else None
    if scenario is not None:
        price = scenario.get("price") if isinstance(scenario.get("price"), Mapping) else {}
        rows.append(_row(section="assumption", envelope_ids=envelope_ids, item_id="scenario",
                         name="view", value=scenario.get("view"), unit="text", value_kind="text",
                         assumption_kind="scenario_view"))
        for name in ("as_of", "horizon_start", "horizon_end"):
            rows.append(_row(section="assumption", envelope_ids=envelope_ids, item_id="scenario",
                             name=name, value=scenario.get(name), unit="date", value_kind="date",
                             assumption_kind="date"))
        rows.append(_row(section="assumption", envelope_ids=envelope_ids, item_id="price",
                         name="price.kind", value=price.get("kind"), unit="text", value_kind="text",
                         assumption_kind="price_basis"))
        rows.append(_row(section="assumption", envelope_ids=envelope_ids, item_id="price",
                         name="price.currency", value=price.get("currency"), unit="text", value_kind="text",
                         assumption_kind="price_basis"))
        if price.get("fixed_price") is not None:
            rows.append(_row(section="assumption", envelope_ids=envelope_ids, item_id="price",
                             name="price.fixed_price", value=price.get("fixed_price"), unit="ratio",
                             value_kind="decimal", assumption_kind="price_basis"))
        for point in price.get("path") or ():
            rows.append(_row(section="assumption", envelope_ids=envelope_ids, item_id="price",
                             name=f"price.path[{point[0]}]", value=point[1], unit="ratio",
                             value_kind="decimal", assumption_kind="price_path"))
        for name in ("fee_rate", "discount_rate"):
            if scenario.get(name) is not None:
                rows.append(_row(section="assumption", envelope_ids=envelope_ids, item_id=name,
                                 name=name, value=scenario.get(name), unit="ratio",
                                 value_kind="decimal", assumption_kind="rate"))
        for key, value in scenario.get("other_assumptions") or ():
            rows.append(_row(section="assumption", envelope_ids=envelope_ids, item_id=_text(key),
                             name=_text(key), value=value, unit="text", value_kind="text",
                             assumption_kind="other_assumption"))
        for action in scenario.get("actions") or ():
            route_id = _text(action.get("route_id"))
            for name in ("action", "settlement"):
                rows.append(_row(section="assumption", envelope_ids=envelope_ids, item_id=route_id,
                                 name=name, value=action.get(name), unit="text", value_kind="text",
                                 assumption_kind="action"))
        for resolution in scenario.get("unknown_resolutions") or ():
            assumed = resolution.get("assumed") if isinstance(resolution.get("assumed"), Mapping) else {}
            rows.append(_row(section="assumption", envelope_ids=envelope_ids,
                             item_id=_text(resolution.get("unknown_id")), name="assumed",
                             value=assumed.get("value"), unit=_text(assumed.get("unit")),
                             value_kind=_value_kind_of(_text(assumed.get("value"))),
                             assumption_kind="unknown_resolution"))
    # The components' declared price bases: exact number text, one row per bound.
    for basis in result.get("price_bases") or ():
        for name in ("low", "high"):
            rows.append(_row(section="assumption", envelope_ids=envelope_ids,
                             item_id=_text(basis.get("component")), name=name,
                             value=basis.get(name), unit="ratio",
                             value_kind=_value_kind_of(_text(basis.get(name))),
                             assumption_kind="price_basis"))
    # The rule-pack edition the answer was composed under.
    capacity = result.get("capacity_envelope") if isinstance(result.get("capacity_envelope"), Mapping) else {}
    rows.append(_row(section="assumption", envelope_ids=envelope_ids, item_id="rule_pack",
                     name="rule_pack_digest", value=capacity.get("rule_pack_digest"), unit="text",
                     value_kind="text", assumption_kind="rule_pack_edition"))
    return rows


def _text_rows(
    result: Mapping[str, Any],
    envelope_ids: Mapping[str, str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for check in result.get("action_checks") or ():
        rows.append(_row(section="action_check", envelope_ids=envelope_ids,
                         item_id=_text(check.get("route_id")), name="status",
                         value=check.get("status"), unit="text", value_kind="text"))
    joint = result.get("joint_check") if isinstance(result.get("joint_check"), Mapping) else {}
    for name in ("status", "aggregate_status"):
        rows.append(_row(section="joint_check", envelope_ids=envelope_ids, item_id="joint_check",
                         name=name, value=joint.get(name), unit="text", value_kind="text"))
    for blocker in result.get("blockers") or ():
        rows.append(_row(section="blocker", envelope_ids=envelope_ids, item_id=_text(blocker),
                         name="blocker", value=blocker, unit="text", value_kind="text"))
    for unknown in result.get("unknowns") or ():
        rows.append(_row(section="unknown", envelope_ids=envelope_ids,
                         item_id=_text(unknown.get("unknown_id")), name="resolving_fact",
                         value=unknown.get("resolving_fact"), unit="text", value_kind="text"))
    receipt = result.get("receipt") if isinstance(result.get("receipt"), Mapping) else {}
    for name in ("input_digest", "rule_digest", "implementation_digest"):
        rows.append(_row(section="provenance", envelope_ids=envelope_ids, item_id="receipt",
                         name=name, value=receipt.get(name), unit="text", value_kind="text"))
    rows.append(_row(section="provenance", envelope_ids=envelope_ids, item_id="receipt",
                     name="computed_at", value=receipt.get("computed_at"), unit="date",
                     value_kind="date"))
    return rows


def export_rows(envelope: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    """The full typed row set for one evaluate envelope, in fixed order."""
    if not isinstance(envelope, Mapping):
        raise ScenarioExportError("nothing to export: the envelope is not an object")
    result = envelope.get("result")
    if not isinstance(result, Mapping):
        outcome = _text(envelope.get("outcome")) or "restore"
        raise ScenarioExportError(f"nothing to export: {outcome}")
    envelope_ids = _envelope_ids(envelope, result)

    def sub(path: str, *keys: str) -> tuple[str, ...]:
        node: Any = result
        for key in (path, *keys):
            if not isinstance(node, Mapping) or key not in node:
                return ()
            node = node[key]
        return (path, *keys)

    rows = [
        *_quantity_rows(result, envelope_ids, section="capacity", sub_paths=(sub("capacity_envelope"),)),
        *_quantity_rows(result, envelope_ids, section="supply",
                        sub_paths=(sub("supply_envelope"),
                                   sub("scenario_new_shares_low"), sub("scenario_new_shares_high"))),
        *_quantity_rows(result, envelope_ids, section="funding", sub_paths=(sub("funding_schedule"),)),
        *_quantity_rows(result, envelope_ids, section="coverage", sub_paths=(sub("coverage"),)),
        *_assumption_rows(envelope, result, envelope_ids),
        *_text_rows(result, envelope_ids),
    ]
    for row in rows:
        if row["section"] not in SECTIONS:
            raise ScenarioExportError(f"row section {row['section']!r} is not a section")
        if row["unit"] not in UNITS:
            raise ScenarioExportError(f"row {row['item_id']}.{row['name']} carries no explicit unit")
        if row["value_kind"] not in VALUE_KINDS:
            raise ScenarioExportError(f"row {row['item_id']}.{row['name']} carries no value_kind")
        if row["value_kind"] == "absent" and row["value"] != "":
            raise ScenarioExportError("an absent value is the empty string, never a number")
    return tuple(rows)


def _cell(column: str, row: Mapping[str, str]) -> str:
    if column == "value":
        if row["value_kind"] in ("decimal", "integer"):
            return row["value"]
        if row["value_kind"] == "absent":
            return ""
        return _csv_safe(row["value"])
    return _csv_safe(_text(row[column]))


def _csv_payload(rows: tuple[Mapping[str, str], ...]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(SCENARIO_EXPORT_COLUMNS)
    for row in rows:
        writer.writerow([_cell(column, row) for column in SCENARIO_EXPORT_COLUMNS])
    return buffer.getvalue().encode("utf-8")


def _parquet_payload(rows: tuple[Mapping[str, str], ...]) -> bytes:
    try:
        import pyarrow as pa  # noqa: PLC0415 — lazy, pinned by requirements
        import pyarrow.parquet as pq  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - dependency is pinned by requirements.
        raise ScenarioExportError("pyarrow is required for the parquet scenario export") from exc
    schema = pa.schema(
        [pa.field(name, pa.string(), nullable=True) for name in SCENARIO_EXPORT_COLUMNS],
        metadata={b"schema": SCENARIO_EXPORT_SCHEMA.encode("utf-8")},
    )
    table = pa.Table.from_pylist(
        [{column: _text(row[column]) for column in SCENARIO_EXPORT_COLUMNS} for row in rows],
        schema=schema,
    )
    buffer = io.BytesIO()
    pq.write_table(
        table,
        buffer,
        compression="zstd",
        use_dictionary=False,
        write_statistics=False,
        version="2.6",
        data_page_version="1.0",
    )
    return buffer.getvalue()


#: A38/A40-style explicit-difference declaration: what each format's encoder
#: DOES with the same fixed row set.  No row field is ever omitted.
SCENARIO_SERIALIZATION_DIFFERENCES: Mapping[str, Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "csv": MappingProxyType(
            {
                "omitted_row_fields": (),
                "encoding": (
                    "_csv_safe (query.py) prefixes every text cell whose first "
                    "character is one of = + - @ TAB CR with an apostrophe",
                    "the value column is exempt exactly when value_kind is "
                    "decimal or integer, so a negative Decimal stays numeric "
                    "text; text values are guarded like every other text column",
                    "absent values are the empty string with value_kind absent "
                    "(never 0, never NaN)",
                    "the first row is the fixed SCENARIO_EXPORT_COLUMNS header",
                ),
            }
        ),
        "parquet": MappingProxyType(
            {
                "omitted_row_fields": (),
                "encoding": (
                    "every column is a Parquet STRING "
                    "(capital_structure.scenario_export/v1 schema metadata)",
                    "no _csv_safe guarding: Parquet is not a spreadsheet "
                    "surface, so text is stored verbatim",
                    "absent values are empty STRING values (never null, never 0)",
                    "no header row; the schema itself carries the fixed column order",
                ),
            }
        ),
    }
)


def export_scenario_envelope(envelope: Mapping[str, Any], fmt: str) -> DeterministicExport:
    """Export one evaluate envelope as ``csv`` or ``parquet``.

    The payload bytes are deterministic: two exports of one envelope are
    byte-identical, and ``sha256`` is over the payload bytes.
    """
    if fmt not in EXPORT_FORMATS:
        raise ScenarioExportError(f"unsupported export format: {fmt!r}")
    rows = export_rows(envelope)
    if fmt == "csv":
        return DeterministicExport.from_payload(media_type=CSV_MEDIA_TYPE, payload=_csv_payload(rows))
    return DeterministicExport.from_payload(media_type=PARQUET_MEDIA_TYPE, payload=_parquet_payload(rows))


def export_filename(envelope: Mapping[str, Any], fmt: str) -> str:
    """``<result_id>.<fmt>`` — the attachment filename is the caller's concern."""
    if fmt not in EXPORT_FORMATS:
        raise ScenarioExportError(f"unsupported export format: {fmt!r}")
    result = envelope.get("result") if isinstance(envelope, Mapping) else None
    if not isinstance(result, Mapping) or not _text(result.get("result_id")):
        outcome = _text(envelope.get("outcome")) or "restore"
        raise ScenarioExportError(f"nothing to export: {outcome}")
    return f"{result['result_id']}.{fmt}"
