"""SPEC_U2 §2 gates 15-20: the exact scenario export (SPEC_U2 §1.4).

Every envelope below is the U1B-2 lane's own evaluate answer — composed by S0
over the U1a bundle builder and the U1B-1 inputs fixtures, imported and never
copied — so the export flattens a result the route actually owes.  The deficit
and probe envelopes are the same fixtures with the funding suite's own cash
constant and extra scenario assumptions, never a hand-written record.  Both
formats are decoded and compared cell by cell; no test opens a socket.

No float literal anywhere; every Decimal is exact text.
"""
from __future__ import annotations

import csv
import dataclasses
import io
import json
from typing import Any, Mapping, NamedTuple

import pytest

from engine.capital_structure.issuer_state_contracts import (
    ContractViolation,
    PriceAssumption,
)
from engine.capital_structure.rule_applicability import (
    build_rule_pack,
    load_rule_applicability_pack,
)
from engine.capital_structure.scenario_composition import (
    ScenarioCompositionError,
    compose_scenario,
)
from engine.capital_structure.scenario_export import (
    SCENARIO_EXPORT_COLUMNS,
    SCENARIO_SERIALIZATION_DIFFERENCES,
    SECTIONS,
    UNITS,
    VALUE_KINDS,
    ScenarioExportError,
    export_filename,
    export_scenario_envelope,
)
from engine.capital_structure.scenario_inputs import (
    ScenarioInputsUnavailable,
    assemble_scenario_inputs,
)
from engine.capital_structure.state_bundle import state_from_record
from engine.fundamental_forensics.query_exports import EXPORT_FORMATS
import tests.test_capital_structure_funding as F
import tests.test_capital_structure_scenario_inputs as inputs_suite
import tests.test_capital_structure_state_api as evaluate_suite
import tests.test_capital_structure_supply_scenarios as SS
from tests.test_capital_structure_state_api import built, pack  # noqa: F401 — requested as fixtures
from tests.test_capital_structure_state_bundle import _state_record

#: The long exact Decimal of gate 16 — plain decimal text, never a float.
LONG_PRICE = "123456789012345678901234567890.5"
#: The deficit cash of gate 18: less than the period's uses, so the coverage
#: scenario balance is a genuinely negative Decimal in the composed result.
DEFICIT_CASH = "1000"
#: Probe strings (gate 18): each begins with a formula lead.
PROBES = ("=SUM(A1)", "+total", "-shorthand", "@cmd", "\ttabbed", "\rcrender")

_RECOMMENDATION_FREE = True


class _Envelopes(NamedTuple):
    """The three evaluate answers every gate flattens."""

    standard: dict[str, Any]
    probe: dict[str, Any]
    exact: dict[str, Any]
    scenario: Any


def _entries(as_of: str, cash_value: str) -> dict[str, Any]:
    """The U1B suite's own per-issuer families, with the cash constant free."""
    instruments = dataclasses.replace(
        inputs_suite._fixture_instruments(), issuer_id=evaluate_suite.ISSUER_ONE, as_of=as_of
    )
    basis = dataclasses.replace(SS.basis(), issuer_id=evaluate_suite.ISSUER_ONE, as_of=as_of)
    financials = F.financials(F.cash(cash_value), F.ocf())
    commitments = F.covenants(
        F.covenant("cov-min-1", "2000000", available_at="2026-10-01T00:00:00Z")
    )
    return {
        inputs_suite.INSTRUMENTS_FAMILY: inputs_suite._entry_for(
            instruments, inputs_suite.INSTRUMENTS_FAMILY
        ),
        inputs_suite.SHARE_BASIS_FAMILY: inputs_suite._entry_for(basis, inputs_suite.SHARE_BASIS_FAMILY),
        inputs_suite.FINANCIALS_FAMILY: inputs_suite._entry_for(financials, inputs_suite.FINANCIALS_FAMILY),
        inputs_suite.COMMITMENTS_FAMILY: inputs_suite._entry_for(commitments, inputs_suite.COMMITMENTS_FAMILY),
    }


def _compose(built: evaluate_suite._Built, *, entries: dict[str, Any], scenario: Any) -> dict[str, Any]:
    from engine.capital_structure.scenario_inputs import RulesEntry, CapacityInputsBundle

    rule_pack = load_rule_applicability_pack()
    rules_built, unknowns, _conditions, _excluded = build_rule_pack(rule_pack, built.bundle["as_of"][:10])
    assert rules_built is not None
    inputs = CapacityInputsBundle(
        as_of=built.bundle["as_of"],
        generated_at=f"{built.bundle['as_of'][:10]}T12:00:00Z",
        state_generation_id=built.bundle["generation_id"],
        source_generation_id=evaluate_suite.stable_id_of_projection(),
        rules=RulesEntry(support="supported", unknowns=tuple(unknowns), record=rules_built),
        issuers={evaluate_suite.ISSUER_ONE: entries},
    )
    inputs_record = json.loads(json.dumps(inputs.as_record(), sort_keys=True))
    state = state_from_record(_state_record(built.bundle, evaluate_suite.ISSUER_ONE))
    assembled = assemble_scenario_inputs(
        inputs_record,
        evaluate_suite.ISSUER_ONE,
        scenario.as_of,
        served_state_generation_id=built.bundle["generation_id"],
    )
    if isinstance(assembled, ScenarioInputsUnavailable):  # pragma: no cover — the fixture is bound
        raise AssertionError("the fixture inputs must assemble")
    result = compose_scenario(
        state,
        assembled.instruments,
        assembled.basis,
        assembled.financials,
        assembled.commitments,
        scenario,
        assembled.rules,
        pack=rule_pack,
    )
    return {
        "view": {
            "mode": "scenario",
            "as_of": scenario.as_of,
            "clock": "system",
            "state_id": state.state_id,
            "generation_id": built.bundle["generation_id"],
            "scenario_id": scenario.scenario_id,
        },
        "inputs_generation_id": inputs_record["generation_id"],
        "issuer_id": evaluate_suite.ISSUER_ONE,
        "result": result.as_record(),
        "facts_unchanged": True,
        "scenario": scenario.as_record(),
    }


@pytest.fixture(scope="module")
def envelopes(built: evaluate_suite._Built) -> _Envelopes:
    scenario = evaluate_suite._test_scenario()
    probe_scenario = evaluate_suite._test_scenario(
        other_assumptions=evaluate_suite.SCENARIO_ASSUMPTIONS
        + tuple((f"probe_{index}", probe) for index, probe in enumerate(PROBES))
        + (("-lead_key", "safe value"),)
    )
    exact_scenario = evaluate_suite._test_scenario(
        price=PriceAssumption("fixed", "USD", fixed_price=LONG_PRICE)
    )
    return _Envelopes(
        standard=_compose(built, entries=_entries(built.bundle["as_of"], "5000000"), scenario=scenario),
        probe=_compose(built, entries=_entries(built.bundle["as_of"], "5000000"), scenario=probe_scenario),
        exact=_compose(built, entries=_entries(built.bundle["as_of"], DEFICIT_CASH), scenario=exact_scenario),
        scenario=scenario,
    )


def _walk_quantities(node: Any) -> list[tuple[str, Mapping[str, Any]]]:
    """The test's own independent quantity walk (unit + status + share_basis)."""
    found: list[tuple[str, Mapping[str, Any]]] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            if {"unit", "status", "share_basis"} <= set(node):
                found.append((path, node))
                return
            for key in sorted(node):
                walk(node[key], f"{path}.{key}" if path else str(key))
        elif isinstance(node, list):
            for item in node:
                walk(item, path)

    walk(node, "")
    return found


def _decode(csv_payload: bytes, parquet_payload: bytes) -> tuple[list[dict[str, str]], list[dict[str, str | None]]]:
    import pyarrow.parquet as pq

    reader = csv.reader(io.StringIO(csv_payload.decode("utf-8")))
    header = next(reader)
    assert tuple(header) == SCENARIO_EXPORT_COLUMNS
    csv_rows = [dict(zip(SCENARIO_EXPORT_COLUMNS, row)) for row in reader]
    table = pq.read_table(io.BytesIO(parquet_payload))
    parquet_rows = [dict(item) for item in table.to_pylist()]
    return csv_rows, parquet_rows


def _both(envelope: Mapping[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str | None]]]:
    return _decode(
        export_scenario_envelope(envelope, "csv").payload,
        export_scenario_envelope(envelope, "parquet").payload,
    )


def _check_export(export, envelope: Mapping[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str | None]]]:
    """The ONE shared helper every export in this file asserts through: the
    given export reproduces byte-identically, both formats decode to the same
    rows, every row names an explicit unit and value_kind, and no text cell
    outside a numeric value starts with a formula lead unless it is
    apostrophe-prefixed."""
    fmt = "csv" if export.media_type == "text/csv" else "parquet"
    again = export_scenario_envelope(envelope, fmt)
    assert again.payload == export.payload, "two exports of one envelope are byte-identical"
    csv_rows, parquet_rows = _both(envelope)
    assert len(csv_rows) == len(parquet_rows)
    for csv_row, parquet_row in zip(csv_rows, parquet_rows):
        for column in SCENARIO_EXPORT_COLUMNS:
            csv_cell, parquet_cell = csv_row[column], parquet_row[column]
            if csv_cell.startswith("'") and csv_cell[1:] == parquet_cell:
                # The DECLARED csv-only formula guard: a guarded text cell is
                # stored verbatim in parquet (not a spreadsheet surface).
                assert column in SCENARIO_EXPORT_COLUMNS
                continue
            assert csv_cell == parquet_cell, (column, csv_row)
        assert csv_row["unit"] in UNITS
        assert csv_row["value_kind"] in VALUE_KINDS
        assert csv_row["section"] in SECTIONS
        value = csv_row["value"]
        if csv_row["value_kind"] == "absent":
            assert value == ""
        elif csv_row["value_kind"] in ("decimal", "integer"):
            assert not value.startswith("'")
        else:
            assert not value or value[0] not in "=+-@\t\r" or value.startswith("'")
        for column in SCENARIO_EXPORT_COLUMNS:
            if column == "value":
                continue
            cell = csv_row[column]
            assert not cell or cell[0] not in "=+-@\t\r" or cell.startswith("'"), (column, cell)
    return csv_rows, parquet_rows


def _assumption_row_count(result: Mapping[str, Any], scenario: Mapping[str, Any]) -> int:
    """The documented assumption enumeration, counted independently."""
    price = scenario["price"]
    count = 1 + 3 + 2  # view + the three dates + price.kind + price.currency
    if price.get("fixed_price") is not None:
        count += 1
    count += len(price.get("path") or ())
    count += sum(1 for name in ("fee_rate", "discount_rate") if scenario.get(name) is not None)
    count += len(scenario.get("other_assumptions") or ())
    count += 2 * len(scenario.get("actions") or ())
    count += len(scenario.get("unknown_resolutions") or ())
    count += 2 * len(result.get("price_bases") or ())
    count += 1  # the rule-pack edition
    return count


# ---------------------------------------------------------------------------
# Gate 15 — every quantity and assumption is a typed row
# ---------------------------------------------------------------------------


def test_u2_export_every_quantity_and_assumption_is_a_typed_row(
    envelopes: _Envelopes,
) -> None:
    envelope = envelopes.standard
    result = envelope["result"]
    export = export_scenario_envelope(envelope, "csv")
    rows, _parquet_rows = _check_export(export, envelope)

    quantities = _walk_quantities(result)
    expected = (
        len(quantities)
        + _assumption_row_count(result, envelope["scenario"])
        + len(result["action_checks"])
        + 2  # joint_check status + aggregate_status
        + len(result["blockers"])
        + len(result["unknowns"])
        + 4  # the receipt's provenance rows
    )
    assert len(rows) == expected, (len(rows), expected)

    sections = [row["section"] for row in rows]
    quantity_rows = [row for row in rows if row["section"] in ("capacity", "supply", "funding", "coverage")]
    assert len(quantity_rows) == len(quantities)
    for path, quantity in quantities:
        if quantity["status"] == "known":
            assert any(
                row["name"] == path.rsplit(".", 1)[-1] and row["value"] == str(quantity["value"])
                for row in quantity_rows
            ), path
        else:
            matches = [
                row
                for row in quantity_rows
                if row["value_kind"] == "absent" and row["name"] == path.rsplit(".", 1)[-1]
            ]
            assert matches, path
    # Sections never mix: assumptions are their own section, and the component
    # quantities never ride an assumption row.
    assert all(row["section"] == "assumption" for row in rows if row["assumption_kind"])
    assert all(row["assumption_kind"] == "" for row in quantity_rows)
    for row in rows:
        assert row["unit"] and row["value_kind"]
        assert row["result_id"] == result["result_id"]
        assert row["state_generation_id"] == envelope["view"]["generation_id"]
        assert row["inputs_generation_id"] == envelope["inputs_generation_id"]
        assert row["scenario_id"] == envelope["scenario"]["scenario_id"]
    assert set(sections) <= set(SECTIONS)


# ---------------------------------------------------------------------------
# Gate 16 — decimals survive both formats byte-identically; parquet is string
# ---------------------------------------------------------------------------


def test_u2_export_decimals_survive_csv_and_parquet_identically(
    envelopes: _Envelopes,
) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    envelope = envelopes.exact
    result = envelope["result"]
    csv_export = export_scenario_envelope(envelope, "csv")
    parquet_export = export_scenario_envelope(envelope, "parquet")
    csv_rows, parquet_rows = _check_export(csv_export, envelope)

    schema = pq.read_table(io.BytesIO(parquet_export.payload)).schema
    for field in schema:
        assert field.type == pa.string(), field.name

    # The long exact Decimal rides the component price bases at the fixed price.
    long_values = {str(value) for value in (LONG_PRICE,)}
    long_cells = [
        row["value"] for row in csv_rows if row["value_kind"] == "decimal" and row["value"] in long_values
    ]
    assert long_cells, "the long Decimal must be exported"
    # The deficit cash turns the coverage scenario balance into a negative Decimal.
    negative_cells = [row["value"] for row in csv_rows if row["value_kind"] == "decimal" and row["value"].startswith("-")]
    assert negative_cells, "the negative Decimal must be exported"

    for value in (*long_cells, *negative_cells):
        csv_cell = next(row["value"] for row in csv_rows if row["value"] == value)
        parquet_cell = next(row["value"] for row in parquet_rows if row["value"] == value)
        assert csv_cell == value
        assert parquet_cell == value
        assert str(csv_cell) == str(parquet_cell) == value


# ---------------------------------------------------------------------------
# Gate 17 — absent values are empty, never zero
# ---------------------------------------------------------------------------


def test_u2_export_absent_values_are_empty_never_zero(envelopes: _Envelopes) -> None:
    envelope = envelopes.standard
    result = envelope["result"]
    rows, parquet_rows = _check_export(export_scenario_envelope(envelope, "csv"), envelope)
    absent_quantities = [
        (path, quantity) for path, quantity in _walk_quantities(result) if quantity["status"] != "known"
    ]
    assert absent_quantities
    for _path, quantity in absent_quantities:
        matches = [
            row
            for row in rows
            if row["value_kind"] == "absent" and row["unit"] == quantity["unit"]
            and row["name"] in ("limit", "bound", "aggregate_bound", "existing_outstanding",
                                "incremental_issuance", "as_converted_claims", "resalable_existing",
                                "scenario_new_shares_low", "scenario_new_shares_high")
        ]
        assert matches
        for row in matches:
            assert row["value"] == ""
            assert row["value"] != "0"
    assert any(row["value_kind"] == "absent" for row in parquet_rows)


# ---------------------------------------------------------------------------
# Gate 18 — no unguarded formula lead outside a numeric value
# ---------------------------------------------------------------------------


def test_u2_export_no_unguarded_formula_leads_outside_value(envelopes: _Envelopes) -> None:
    rows, _parquet_rows = _check_export(export_scenario_envelope(envelopes.probe, "csv"), envelopes.probe)
    for probe in PROBES:
        guarded = [row for row in rows if row["value"] == f"'{probe}"]
        assert guarded, probe
        for row in guarded:
            assert row["section"] == "assumption"
            assert row["value_kind"] == "text"
    # A probe riding an assumption KEY guards the name/item_id columns too.
    assert any(row["item_id"] == "'-lead_key" for row in rows)

    # A negative Decimal in the value column is NOT guarded (the deficit
    # envelope composes a genuinely negative coverage scenario balance).
    deficit_rows, _ = _check_export(export_scenario_envelope(envelopes.exact, "csv"), envelopes.exact)
    negative = [row["value"] for row in deficit_rows if row["value_kind"] == "decimal" and row["value"].startswith("-")]
    assert negative
    assert all(not value.startswith("'") for value in negative)


# ---------------------------------------------------------------------------
# Gate 19 — no user material ever leaves in an export
# ---------------------------------------------------------------------------


def test_u2_export_carries_no_user_material(envelopes: _Envelopes) -> None:
    envelope = envelopes.standard
    csv_export = export_scenario_envelope(envelope, "csv")
    parquet_export = export_scenario_envelope(envelope, "parquet")
    # The plain-text payload carries none of it byte-wise...
    assert b"user_id" not in csv_export.payload
    assert b"label" not in csv_export.payload
    assert b"@" not in csv_export.payload
    assert "u1b evaluate route fixture".encode() not in csv_export.payload
    # ...and neither does any decoded cell of either format.
    for rows in _both(envelope):
        for row in rows:
            for column in SCENARIO_EXPORT_COLUMNS:
                cell = str(row[column])
                assert "user_id" not in cell
                assert "label" not in cell
                assert "@" not in cell
    assert "u1b evaluate route fixture" not in " ".join(
        str(row[column]) for rows in _both(envelope) for row in rows for column in SCENARIO_EXPORT_COLUMNS
    )
    assert "label" not in SCENARIO_EXPORT_COLUMNS
    assert export_filename(envelope, "csv") == f"{envelope['result']['result_id']}.csv"


# ---------------------------------------------------------------------------
# Gate 20 — an envelope without a result is refused, naming the outcome
# ---------------------------------------------------------------------------


def test_u2_export_refuses_envelopes_without_a_result(envelopes: _Envelopes) -> None:
    with pytest.raises(ScenarioExportError) as raised:
        export_scenario_envelope({"outcome": "inputs_unavailable"}, "csv")
    assert str(raised.value) == "nothing to export: inputs_unavailable"

    with pytest.raises(ScenarioExportError) as unnamed:
        export_scenario_envelope({"view": {}}, "csv")
    assert str(unnamed.value) == "nothing to export: restore"

    with pytest.raises(ScenarioExportError) as fmt:
        export_scenario_envelope(envelopes.standard, "xlsx")
    assert "unsupported export format" in str(fmt.value)
    assert "xlsx" not in EXPORT_FORMATS

    with pytest.raises(ScenarioExportError) as named_file:
        export_filename({"outcome": "source_outage"}, "csv")
    assert str(named_file.value) == "nothing to export: source_outage"
