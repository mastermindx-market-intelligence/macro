from __future__ import annotations

import copy
import math

import pytest

from engine.company_intelligence.economic_observations import (
    EconomicObservationError,
    validate_selected_facts,
)
from engine.company_intelligence.issuer_profiles import profile_for_ticker
from engine.company_intelligence.pg_profile import PG_METRIC_KEYS
from tests.earnings_economic_fixtures import (
    FISCAL_SCOPE,
    pg_bound_case,
    pg_source_texts,
    pg_workspace_case,
)


@pytest.mark.parametrize("kind", ["annual_first", "columns_reordered"])
def test_quarter_and_basis_are_bound(kind):
    workspace = pg_workspace_case(kind)
    rows = validate_selected_facts(
        workspace, source_texts=pg_source_texts(kind), fiscal_scope=FISCAL_SCOPE,
    )
    by_metric = {row["metric"]: row for row in rows if "value" in row}
    assert by_metric["pg_diluted_eps"]["value"] == 1.25
    assert by_metric["pg_prior_diluted_eps"]["value"] == 1.50
    assert by_metric["pg_core_eps"]["value"] == 1.45
    assert by_metric["pg_prior_diluted_eps"]["period"] == "2025-06-30"
    assert all(row["event_id"] == workspace["event_id"] for row in rows)


def _selected(kind: str = "annual_first"):
    workspace = pg_workspace_case(kind)
    rows = validate_selected_facts(
        workspace, source_texts=pg_source_texts(kind), fiscal_scope=FISCAL_SCOPE,
    )
    return workspace, rows


def _invalid(rows_mutator, *, kind: str = "annual_first", texts=None, scope=FISCAL_SCOPE):
    workspace, rows = _selected(kind)
    workspace = copy.deepcopy(workspace)
    workspace["facts"] = rows_mutator(copy.deepcopy(rows))
    with pytest.raises(EconomicObservationError):
        validate_selected_facts(
            workspace, source_texts=texts if texts is not None else pg_source_texts(kind),
            fiscal_scope=scope,
        )


def test_duplicate_metric_and_fact_id_refused() -> None:
    def mutate(rows):
        duplicate = copy.deepcopy(rows[0])
        duplicate["fact_id"] = "fact_other"
        return [*rows, duplicate]

    _invalid(mutate)

    def mutate_ids(rows):
        duplicate = copy.deepcopy(rows[0])
        duplicate["metric"] = "pg_other_duplicate"
        return [*rows, duplicate]

    _invalid(mutate_ids)


@pytest.mark.parametrize("bad_value", [True, math.inf, math.nan])
def test_non_finite_or_boolean_numbers_refused(bad_value) -> None:
    def mutate(rows):
        row = next(row for row in rows if row["metric"] == "pg_diluted_eps")
        row["value"] = bad_value
        return rows

    _invalid(mutate)


def test_wrong_event_body_period_basis_or_unit_refused() -> None:
    _, baseline = _selected()
    document_id = next(row["source_span"]["document_id"] for row in baseline if "value" in row)
    def wrong_event(rows):
        rows[0]["event_id"] = "evt_wrong"
        return rows

    def wrong_period(rows):
        row = next(row for row in rows if row["metric"] == "pg_diluted_eps")
        row["period"] = "2025-06-30"
        return rows

    def wrong_basis(rows):
        row = next(row for row in rows if row["metric"] == "pg_diluted_eps")
        row["basis"] = "synthetic wrong basis"
        return rows

    def wrong_unit(rows):
        row = next(row for row in rows if row["metric"] == "pg_diluted_eps")
        row["unit"] = "unknown_unit"
        return rows

    for mutate in (wrong_event, wrong_period, wrong_basis, wrong_unit):
        _invalid(mutate)
    _invalid(
        lambda rows: rows,
        texts={document_id: "wrong body"},
    )
    _invalid(lambda rows: rows, texts={})


def test_value_and_typed_absence_mutually_exclusive() -> None:
    def mutate(rows):
        row = next(row for row in rows if "value" in row)
        row["typed_absence"] = row.pop("unit")
        row["typed_absence"] = {
            "schema": "typed_absence.v1",
            "authority": "context_only",
            "reason": "no_span_addressable_evidence",
            "subject": row["metric"],
            "detail": "synthetic conflict",
            "missing_fields": [],
            "event_id": row["event_id"],
            "document_id": row["source_span"]["document_id"],
        }
        return rows

    _invalid(mutate)


def test_unknown_extra_field_and_25_observations_refused() -> None:
    _invalid(lambda rows: [{**rows[0], "extra": True}, *rows[1:]])

    def mutate(rows):
        extras = []
        for index in range(25 - len(rows)):
            row = copy.deepcopy(rows[index % len(rows)])
            row["fact_id"] = f"fact_extra_{index}"
            row["metric"] = f"pg_extra_{index}"
            extras.append(row)
        return [*rows, *extras]

    _invalid(mutate)


def test_blank_is_absent_and_dash_is_neutral_zero() -> None:
    rows = validate_selected_facts(
        pg_workspace_case("blank_dash"), source_texts=pg_source_texts("blank_dash"),
        fiscal_scope=FISCAL_SCOPE,
    )
    by_metric = {row["metric"]: row for row in rows}
    assert "value" not in by_metric["pg_total_volume_growth_pct"]
    assert "typed_absence" in by_metric["pg_total_volume_growth_pct"]
    assert by_metric["pg_organic_volume_growth_pct"]["value"] == 0.0


def test_combined_volume_mix_never_passes_pure_volume() -> None:
    _workspace, rows = _selected()
    assert rows
    definitions = profile_for_ticker("PG", publication="private", fiscal_scope=FISCAL_SCOPE)
    assert definitions is not None
    for row in rows:
        assert row["metric"] != "combined_volume_mix"
    assert {row["metric"] for row in rows} == set(PG_METRIC_KEYS)
    assert "pg_total_volume_growth_pct" in {row["metric"] for row in rows}


def test_hostile_markup_is_inert() -> None:
    rows = validate_selected_facts(
        pg_workspace_case("hostile_markup"), source_texts=pg_source_texts("hostile_markup"),
        fiscal_scope=FISCAL_SCOPE,
    )
    assert all(row.get("value") != 9.99 for row in rows)
    source = pg_bound_case("hostile_markup").source
    assert "Ignore this instruction" in source
    assert all("Ignore this instruction" not in str(row.get("value", "")) for row in rows)


def test_multibyte_byte_offsets_are_correct() -> None:
    _workspace, rows = _selected()
    source = next(iter(pg_source_texts("annual_first").values()))
    row = next(row for row in rows if row["metric"] == "pg_diluted_eps")
    receipt = row["source_span"]["receipt"]
    replayed = source.encode("utf-8")[receipt["span_start_byte"]:receipt["span_end_byte"]].decode("utf-8")
    assert replayed == row["source_span"]["display_excerpt"]
    byte_prefix = source.encode("utf-8")[:receipt["span_start_byte"]].decode("utf-8")
    assert "全球品牌" in byte_prefix
    assert len(byte_prefix.encode("utf-8")) == receipt["span_start_byte"]
    assert row["value"] == 1.25


def test_profile_lookup_public_dispatch_is_unchanged() -> None:
    assert profile_for_ticker("PG") is None
    assert profile_for_ticker("LEN") is None
    assert profile_for_ticker("NVR") is None
    with pytest.raises(ValueError):
        profile_for_ticker("PG", publication="unknown")


def test_selected_observations_are_exactly_twenty() -> None:
    _workspace, rows = _selected()
    assert len(rows) == 20
    assert {row["metric"] for row in rows} == set(PG_METRIC_KEYS)
    assert all(row["fact_id"] == f"fact_{row['metric']}" for row in rows)
