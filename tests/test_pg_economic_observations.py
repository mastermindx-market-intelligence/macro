from __future__ import annotations

import copy
import math

import pytest

from engine.company_intelligence.economic_observations import (
    EconomicObservationError,
    validate_selected_facts,
)
from engine.company_intelligence.issuer_profiles import profile_for_ticker
from engine.company_intelligence.pg_profile import PG_METRIC_KEYS, parse_pg_literal
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
    assert by_metric["pg_diluted_eps"]["value"] == 3.07
    assert by_metric["pg_prior_diluted_eps"]["value"] == 2.93
    assert by_metric["pg_core_eps"]["value"] == 3.11
    assert by_metric["pg_prior_diluted_eps"]["period"] == "2025-06-30"
    driver_values = {
        "pg_reported_sales_growth_pct": 3.0,
        "pg_organic_sales_growth_pct": 1.0,
        "pg_total_volume_growth_pct": 1.0,
        "pg_organic_volume_growth_pct": 1.0,
        "pg_price_contribution_pp": 0.5,
        "pg_mix_contribution_pp": 0.5,
        "pg_fx_contribution_pp": -1.0,
        "pg_other_contribution_pp": 1.0,
    }
    assert {metric: by_metric[metric]["value"] for metric in driver_values} == driver_values
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


def _replay_mismatch(mutate) -> None:
    workspace, rows = _selected()
    workspace = copy.deepcopy(workspace)
    workspace["facts"] = mutate(copy.deepcopy(rows))
    with pytest.raises(EconomicObservationError, match="replay_mismatch"):
        validate_selected_facts(
            workspace,
            source_texts=pg_source_texts("annual_first"),
            fiscal_scope=FISCAL_SCOPE,
        )


def test_replayed_value_must_match_stored_value() -> None:
    def mutate(rows):
        row = next(row for row in rows if "value" in row and "source_span" in row)
        row["value"] = 9.99
        return rows

    _replay_mismatch(mutate)


def test_replayed_period_must_match_span_pair() -> None:
    def mutate(rows):
        present_rows = [row for row in rows if "value" in row and "source_span" in row]
        current, prior = present_rows[:2]
        current["source_span"], prior["source_span"] = (
            prior["source_span"], current["source_span"],
        )
        return rows

    _replay_mismatch(mutate)


def test_replayed_reconciliation_text_must_match_stored_text() -> None:
    row_metric = "pg_core_reconciliation_context"

    def mutate(rows):
        row = next(row for row in rows if row["metric"] == row_metric)
        row["value"] = "The edited sentence does not match its kept receipt."
        return rows

    _replay_mismatch(mutate)


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
    assert "value" not in by_metric["pg_organic_volume_growth_pct"]
    assert "typed_absence" in by_metric["pg_organic_volume_growth_pct"]
    assert by_metric["pg_total_volume_growth_pct"]["value"] == 0.0
    assert by_metric["pg_total_volume_growth_pct"]["source_span"]["display_excerpt"] == "—"


def test_combined_volume_mix_never_passes_pure_volume() -> None:
    rows = validate_selected_facts(
        pg_workspace_case("combined_volume_only"),
        source_texts=pg_source_texts("combined_volume_only"),
        fiscal_scope=FISCAL_SCOPE,
    )
    by_metric = {row["metric"]: row for row in rows}
    for metric in ("pg_total_volume_growth_pct", "pg_organic_volume_growth_pct"):
        assert "value" not in by_metric[metric]
        subject = by_metric[metric]["typed_absence"]["subject"].casefold()
        assert "volume" in subject and "mix" in subject
        assert "combined" in by_metric[metric]["typed_absence"]["detail"].casefold()


@pytest.mark.parametrize(
    ("literal", "expected"), [("$1.25", 1.25), ("1.25", 1.25), ("(1.25)", -1.25)]
)
def test_usd_per_share_literals_parse_by_unit(literal, expected):
    assert parse_pg_literal(literal, unit="usd_per_share") == expected


@pytest.mark.parametrize("literal", ["1%", "(2)%", "+3%", "(2%)"])
def test_percent_literals_parse_by_unit(literal):
    assert parse_pg_literal(literal, unit="percent") is not None


def test_unit_shape_mismatch_is_a_typed_absence():
    workspace, rows = _selected("eps_unit_mismatch")
    row = next(row for row in rows if row["metric"] == "pg_diluted_eps")
    assert "value" not in row
    assert row["typed_absence"]["reason"] == "unit_mismatch"


def test_fy2027_scope_binds_current_and_prior_columns() -> None:
    scope = ("2027-04-01", "2027-06-30", "2026-04-01", "2026-06-30")
    workspace = pg_workspace_case("annual_first", fiscal_scope=scope)
    rows = validate_selected_facts(
        workspace,
        source_texts=pg_source_texts("annual_first", fiscal_scope=scope),
        fiscal_scope=scope,
    )
    by_metric = {row["metric"]: row for row in rows if "value" in row}
    assert by_metric["pg_diluted_eps"]["value"] == 3.07
    assert by_metric["pg_diluted_eps"]["period"] == "2027-06-30"
    assert by_metric["pg_prior_diluted_eps"]["value"] == 2.93
    assert by_metric["pg_prior_diluted_eps"]["period"] == "2026-06-30"
    assert by_metric["pg_price_contribution_pp"]["value"] == 0.5


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
    assert row["value"] == 3.07


def test_profile_lookup_public_dispatch_is_unchanged() -> None:
    assert profile_for_ticker("PG") is None
    assert profile_for_ticker("LEN") is None
    assert profile_for_ticker("NVR") is None
    with pytest.raises(ValueError):
        profile_for_ticker("PG", publication="unknown")


def test_scope_quarter_matches_workspace_quarter() -> None:
    scope = ("2026-01-01", "2026-03-31", "2025-01-01", "2025-03-31")
    workspace = pg_workspace_case("annual_first", fiscal_scope=scope)
    rows = validate_selected_facts(
        workspace,
        source_texts=pg_source_texts("annual_first", fiscal_scope=scope),
        fiscal_scope=scope,
    )
    assert len(rows) == 20


def test_none_fiscal_period_is_typed_error() -> None:
    workspace, _rows = _selected()
    workspace = copy.deepcopy(workspace)
    workspace["fiscal_period"] = None
    with pytest.raises(EconomicObservationError, match="fiscal period is missing"):
        validate_selected_facts(
            workspace, source_texts=pg_source_texts("annual_first"), fiscal_scope=FISCAL_SCOPE
        )


def test_absence_rows_are_fully_bound() -> None:
    def mutate(rows):
        row = next(row for row in rows if "typed_absence" in row)
        row["typed_absence"]["authority"] = "can_rank"
        return rows

    def mutate_subject(rows):
        row = next(row for row in rows if "typed_absence" in row)
        row["typed_absence"]["subject"] = "pg_wrong_subject"
        return rows

    def mutate_document(rows):
        row = next(row for row in rows if "typed_absence" in row)
        row["typed_absence"]["document_id"] = "doc_wrong"
        return rows

    for mutation in (mutate, mutate_subject, mutate_document):
        _invalid(mutation)


def test_fact_id_identity_and_duplicate_refused() -> None:
    def mutate(rows):
        row = next(row for row in rows if row["metric"] == "pg_diluted_eps")
        row["fact_id"] = "fact_pg_core_eps"
        return rows

    _invalid(mutate)
    _workspace, baseline = _selected()
    assert all(row["fact_id"] == f"fact_{row['metric']}" for row in baseline)


def test_span_must_use_registered_private_rights_profile() -> None:
    def mutate(rows):
        row = next(row for row in rows if "source_span" in row)
        row["source_span"]["rights_profile"] = "rp_public_primary_v1"
        return rows

    _invalid(mutate)


def test_dash_without_a_convention_is_an_absence() -> None:
    rows = validate_selected_facts(
        pg_workspace_case("blank_dash"),
        source_texts=pg_source_texts("blank_dash"),
        fiscal_scope=FISCAL_SCOPE,
    )
    row = next(row for row in rows if row["metric"] == "pg_organic_volume_growth_pct")
    assert "value" not in row
    assert row["typed_absence"]["detail"] == "A dash has no explicit neutral-zero convention."


def test_selected_observations_are_exactly_twenty() -> None:
    _workspace, rows = _selected()
    assert len(rows) == 20
    assert {row["metric"] for row in rows} == set(PG_METRIC_KEYS)
    assert all(row["fact_id"] == f"fact_{row['metric']}" for row in rows)
