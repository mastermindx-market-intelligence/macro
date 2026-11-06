from __future__ import annotations

import copy
import hashlib
import math
from datetime import date

import pytest

from engine.company_intelligence.economic_observations import (
    EconomicObservationError,
    validate_selected_facts,
)
from engine.company_intelligence.events import FiscalPeriod
from engine.company_intelligence.issuer_profiles import profile_for_ticker
from engine.company_intelligence.pg_profile import PG_DEFINITIONS, PG_METRIC_KEYS, parse_pg_literal
from tests.earnings_economic_fixtures import (
    FISCAL_PERIOD,
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
    assert "value" not in by_metric["pg_total_volume_growth_pct"]
    assert "typed_absence" in by_metric["pg_total_volume_growth_pct"]
    assert by_metric["pg_organic_volume_growth_pct"]["value"] == 0.0
    assert by_metric["pg_organic_volume_growth_pct"]["source_span"]["display_excerpt"] == "—"


@pytest.mark.parametrize(
    "kind",
    [
        "annual_first",
        "columns_reordered",
        "hostile_markup",
        "blank_dash",
        "dash_without_convention",
        "combined_volume_only",
        "eps_unit_mismatch",
    ],
)
def test_validator_accepts_every_extractor_output(kind: str) -> None:
    workspace = pg_workspace_case(kind)
    emitted = [row for row in workspace["facts"] if str(row.get("metric", "")).startswith("pg_")]
    checked = validate_selected_facts(
        workspace, source_texts=pg_source_texts(kind), fiscal_scope=FISCAL_SCOPE
    )
    assert checked == emitted


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
    period = FiscalPeriod(year=2027, quarter=4, calendar_end=date(2027, 6, 30))
    workspace = pg_workspace_case("annual_first", fiscal_scope=scope, fiscal_period=period)
    rows = validate_selected_facts(
        workspace,
        source_texts=pg_source_texts("annual_first", fiscal_period=period),
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


def test_scope_quarter_over_a_q4_document_yields_only_absences() -> None:
    """R27: a Q3 scope over a document whose every period signal names the June quarter binds nothing.

    The workspace identity matches the scope, so the validator accepts the rows; the extractor refused the
    document, so every one of the 20 rows is a typed absence.  (Before R27 this test asserted the defect:
    twenty rows with values bound from a foreign quarter.)
    """
    scope = ("2026-01-01", "2026-03-31", "2025-01-01", "2025-03-31")
    period = FiscalPeriod(year=2026, quarter=3, calendar_end=date(2026, 3, 31))
    workspace = pg_workspace_case("annual_first", fiscal_scope=scope, fiscal_period=period, document_period=FISCAL_PERIOD)
    rows = validate_selected_facts(
        workspace,
        source_texts=pg_source_texts("annual_first", fiscal_period=period, document_period=FISCAL_PERIOD),
        fiscal_scope=scope,
    )
    assert len(rows) == 20
    assert all("typed_absence" in row and "value" not in row for row in rows)


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
    workspace, baseline = _selected()
    for row in baseline:
        period = row.get("period", row["metric"])
        definition = next(item for item in PG_DEFINITIONS if item.metric == row["metric"])
        identity = "|".join((workspace["event_id"], row["metric"], period, definition.basis))
        expected = f"fact_{hashlib.sha256(identity.encode()).hexdigest()[:16]}"
        assert row["fact_id"] == expected


def test_dash_span_points_at_the_dash_cell() -> None:
    rows = validate_selected_facts(
        pg_workspace_case("blank_dash"),
        source_texts=pg_source_texts("blank_dash"),
        fiscal_scope=FISCAL_SCOPE,
    )
    row = next(row for row in rows if row["metric"] == "pg_organic_volume_growth_pct")
    source = next(iter(pg_source_texts("blank_dash").values()))
    start = row["source_span"]["receipt"]["span_start_byte"]
    end = row["source_span"]["receipt"]["span_end_byte"]
    assert source.encode("utf-8")[start:end].decode("utf-8") == "—"


def test_span_must_use_registered_private_rights_profile() -> None:
    def mutate(rows):
        row = next(row for row in rows if "source_span" in row)
        row["source_span"]["rights_profile"] = "rp_public_primary_v1"
        return rows

    _invalid(mutate)


def test_dash_without_a_convention_is_an_absence() -> None:
    rows = validate_selected_facts(
        pg_workspace_case("dash_without_convention"),
        source_texts=pg_source_texts("dash_without_convention"),
        fiscal_scope=FISCAL_SCOPE,
    )
    row = next(row for row in rows if row["metric"] == "pg_organic_volume_growth_pct")
    assert "value" not in row
    assert row["typed_absence"]["detail"] == "A dash has no explicit neutral-zero convention."


def test_selected_observations_are_exactly_twenty() -> None:
    _workspace, rows = _selected()
    assert len(rows) == 20
    assert {row["metric"] for row in rows} == set(PG_METRIC_KEYS)
    assert len({row["fact_id"] for row in rows}) == len(rows)
    assert all(row["fact_id"].startswith("fact_") and len(row["fact_id"]) == 21 for row in rows)


# R32 — the volume cross-check reads every same-period statement of Total P&G volume.
def _r32_workspace(body: str, slug: str):
    from tests.test_pg_economic_observations_probes import Q4_FY2026, _literal_workspace, _pg_rows

    workspace, texts = _literal_workspace(
        "<html><head><title>t</title></head><body>\n<p>Synthetic probe; no relationship to any filing.</p>\n" + body + "</body></html>",
        Q4_FY2026,
        slug,
    )
    return workspace, texts, _pg_rows(workspace), Q4_FY2026


_R32_DRIVERS = (
    "<h2>Net Sales Change Drivers 2026 vs. 2025</h2>\n<table>\n<tr><td></td><td>Volume with Acquisitions &amp; Divestitures</td>"
    "<td>Volume Excluding Acquisitions &amp; Divestitures</td><td>Foreign Exchange</td><td>Price</td><td>Mix</td><td>Other</td>"
    "<td>Net Sales Growth</td><td>Organic Sales Growth</td></tr>\n"
    "<tr><td>Total P&amp;G</td><td>1.0%</td><td>1.0%</td><td>(1.0)%</td><td>0.5%</td><td>0.5%</td><td>1.0%</td><td>3.0%</td><td>1.0%</td></tr>\n</table>\n"
)


def test_second_table_volume_disagreement_is_cross_check_conflict() -> None:
    body = _R32_DRIVERS + (
        "<h2>Segment Results</h2>\n<table>\n<tr><td></td><td>Total Volume</td><td>Organic Sales Growth</td></tr>\n"
        "<tr><td>Total P&amp;G</td><td>4.0%</td><td>1.0%</td></tr>\n</table>\n"
    )
    workspace, texts, rows, case = _r32_workspace(body, "r32_conflict")
    row = rows["pg_total_volume_growth_pct"]
    assert "value" not in row
    assert row["typed_absence"]["reason"] == "cross_check_conflict"
    validate_selected_facts(workspace, source_texts=texts, fiscal_scope=case.scope)


def test_prior_year_drivers_table_is_not_a_volume_conflict() -> None:
    body = _R32_DRIVERS + (
        "<h2>Net Sales Change Drivers 2025 vs. 2024</h2>\n<table>\n<tr><td></td><td>Volume with Acquisitions &amp; Divestitures</td>"
        "<td>Net Sales Growth</td></tr>\n<tr><td>Total P&amp;G</td><td>7.0%</td><td>7.0%</td></tr>\n</table>\n"
    )
    workspace, texts, rows, case = _r32_workspace(body, "r32_prior_year")
    assert rows["pg_total_volume_growth_pct"].get("value") == 1.0
    validate_selected_facts(workspace, source_texts=texts, fiscal_scope=case.scope)
