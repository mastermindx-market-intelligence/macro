"""FIF lane E2: release-figure vs filed-packet reconciliation (A29, no splicing).

Synthetic numbers and fixture identities only.  The packet side is a
hand-written minimal dict shaped like ``contracts/financial_intelligence_packet.schema.json``
cells; the release side uses the real ``ReleaseFigure``/``ReleaseFigureSet``/
``TypedAbsence`` constructors.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import yaml

from engine.earnings_release.binding import ReleaseEvent, ReleaseRevision
from engine.earnings_release.filing_key import FilingKey
from engine.earnings_release.figures import (
    ReleaseFigure,
    ReleaseFigureSet,
    TypedAbsence,
)
from engine.earnings_release.receipts import SpanReceipt
from engine.fundamental_forensics.release_reconciliation import (
    CONCEPT_TO_METRIC,
    SCHEMA_ID,
    ReleaseInput,
    build_release_series,
    reconcile_release,
    release_input_from_event,
)

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "config" / "fundamental_forensics" / "metrics" / "v1" / "metric_catalog.yaml"

CIK = 1234567
EVENT_KEY = f"{CIK:010d}|2026-04-25"
REPORT_DATE = "2026-04-25"
ACCESSION = "0001234567-26-000042"

Q_START, Q_END = "2026-01-01", "2026-03-31"
Q_LABEL = "Three Months Ended March 31, 2026"
FY_LABEL = "Fiscal Year Ended March 31, 2026"
FY_START = "2025-04-01"  # 364 days, inside the annual window


def _receipt(tag: str, display: str = "94.93") -> SpanReceipt:
    return SpanReceipt(
        source_sha256=f"{tag:<64}a",
        char_start=10,
        char_end=16,
        byte_start=10,
        byte_end=16,
        span_sha256=f"{tag:<64}b",
        span_bytes=len(display),
        span_text=display,
        value_text=display,
        value_text_sha256=f"{tag:<64}c",
    )


def _figure(
    concept: str,
    label: str,
    value: float,
    *,
    basis: str = "gaap",
    units: str = "usd_billions",
    currency: str | None = "USD",
    period_label: str = Q_LABEL,
    period_end: str = Q_END,
    scale_factor: float | None = 1e9,
    tag: str = "r",
    display: str = "94.93",
) -> ReleaseFigure:
    return ReleaseFigure(
        concept=concept,
        label=label,
        value=value,
        basis=basis,
        units=units,
        currency=currency,
        period_label=period_label,
        period_end=period_end,
        receipt=_receipt(tag, display),
        scale_factor=scale_factor,
    )


def _cell(
    cell_id: str,
    metric_id: str,
    *,
    value: str | None,
    start: str | None = Q_START,
    end: str = Q_END,
    unit: str | None = "USD",
    kind: str = "duration",
    non_value_state: str | None = None,
    accession: str = ACCESSION,
) -> dict:
    return {
        "cell_id": cell_id,
        "metric_id": metric_id,
        "label": metric_id,
        "statement_family": "income_statement",
        "period": {"kind": kind, "start": start, "end": end},
        "value": value,
        "non_value_state": non_value_state,
        "unit": unit,
        "provenance_kind": "direct",
        "source_occurrence_ids": [],
        "accession": accession,
        "concept": None,
        "taxonomy": None,
        "source_url": None,
        "source_digest": None,
        "source_event_time": None,
        "system_recorded_time": None,
        "mapping_rule_id": None,
        "mapping_rule_digest": None,
        "formula_rule_id": None,
        "formula_rule_digest": None,
        "dependency_cell_ids": [],
        "quality_state": None,
        "coverage_state": None,
        "reason": None,
    }


def _packet(*cells: dict) -> dict:
    return {"cells": list(cells), "evidence_cells": []}


def _release(
    figures=(),
    absences=(),
    *,
    event_key: str = EVENT_KEY,
    report_date: str = REPORT_DATE,
) -> ReleaseInput:
    return ReleaseInput(
        event_key=event_key,
        report_date=report_date,
        accession=ACCESSION,
        figure_set=ReleaseFigureSet(figures=tuple(figures), absences=tuple(absences)),
    )


def _rows_by_outcome(reconciliation):
    rows = reconciliation.to_dict()["rows"]
    return {row["outcome"]: row for row in rows}


def _row(reconciliation, concept: str, *, basis: str = "gaap"):
    matches = [
        row
        for row in reconciliation.to_dict()["rows"]
        if row["concept"] == concept and row["basis"] == basis
    ]
    assert len(matches) == 1, (concept, basis, matches)
    return matches[0]


def _assert_no_floats(node) -> None:
    assert not isinstance(node, float), f"float leaked into output: {node!r}"
    if isinstance(node, dict):
        for value in node.values():
            _assert_no_floats(value)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _assert_no_floats(item)


# ─── (a) revenue: billions-scale agreement and disagreement ──────────────────

def test_revenue_agrees_and_differs_with_exact_delta():
    figure = _figure("revenue", "Net sales", 94.93)
    agrees = reconcile_release(_release([figure]), _packet(
        _cell("c-rev-1", "revenue", value="94930000000")
    ))
    row = _row(agrees, "revenue")
    assert row["outcome"] == "agrees"
    assert row["released_value"] == "94930000000"
    assert row["filed_value"] == "94930000000"
    assert row["delta"] == "0"
    # half of one unit of the displayed 0.01-billions precision: 0.005e9
    assert row["tolerance"] == "5000000"
    assert row["metric_id"] == "revenue"
    assert row["filed_cell_ids"] == ["c-rev-1"]
    assert row["period_length_class"] == "quarter"

    differs = reconcile_release(_release([figure]), _packet(
        _cell("c-rev-1", "revenue", value="94830000000")
    ))
    row = _row(differs, "revenue")
    assert row["outcome"] == "differs"
    assert row["delta"] == "100000000"
    assert row["filed_value"] == "94830000000"


def test_release_scale_falls_back_to_scale_factor_table():
    # No explicit scale_factor: the usd_millions entry of figures._SCALE_FACTOR
    # governs.  The spec's own example — a release in millions agrees within
    # 500,000 — is the tolerance formula at zero displayed decimals.
    whole_millions = _figure(
        "revenue", "Net sales", 94930.0,
        units="usd_millions", scale_factor=None, tag="m", display="94,930",
    )
    result = reconcile_release(_release([whole_millions]), _packet(
        _cell("c-rev-1", "revenue", value="94930000000")
    ))
    row = _row(result, "revenue")
    assert row["outcome"] == "agrees"
    assert row["released_value"] == "94930000000"
    assert row["tolerance"] == "500000"  # 0.5 * 1e6, zero displayed decimals


def test_display_precision_unknown_without_a_usable_literal():
    # E2-m5: decimals are never guessed from the float's repr.  A missing
    # receipt and a literal that is not the accepted form (a trailing
    # footnote marker) both yield the typed state, with no tolerance, no
    # delta and no verdict.
    packet = _packet(_cell("c-rev-1", "revenue", value="94930000000"))
    millions = dict(units="usd_millions", scale_factor=None)
    no_receipt = replace(
        _figure("revenue", "Net sales", 94930.0, tag="m0", display="94,930", **millions),
        receipt=None,
    )
    footnote_marker = _figure(
        "revenue", "Net sales", 94930.0, tag="m1", display="94,930 (1)", **millions
    )
    for figure in (no_receipt, footnote_marker):
        row = _row(reconcile_release(_release([figure]), packet), "revenue")
        assert row["outcome"] == "display_precision_unknown"
        assert row["filed_cell_ids"] == ["c-rev-1"]
        assert row["released_value"] == "94930000000"
        assert row["filed_value"] == "94930000000"
        assert row["tolerance"] is None
        assert row["delta"] is None

    # The accepted literal forms keep today's results.
    accepted = _figure("revenue", "Net sales", 94930.0, tag="m2", display="94,930", **millions)
    row = _row(reconcile_release(_release([accepted]), packet), "revenue")
    assert row["outcome"] == "agrees"
    assert row["tolerance"] == "500000"


# ─── (b) EPS: per-share unit handling ─────────────────────────────────────────

def test_eps_agrees_per_share_and_mismatches_currency_unit():
    figure = _figure(
        "eps_diluted", "Diluted", 1.64,
        units="per_share", scale_factor=1.0, tag="e",
    )
    agrees = reconcile_release(_release([figure]), _packet(
        _cell("c-eps-1", "diluted_earnings_per_share", value="1.64", unit="USD/shares")
    ))
    row = _row(agrees, "eps_diluted")
    assert row["outcome"] == "agrees"
    assert row["released_value"] == "1.64"
    assert row["tolerance"] == "0.005"

    mismatch = reconcile_release(_release([figure]), _packet(
        _cell("c-eps-2", "diluted_earnings_per_share", value="1.64", unit="USD")
    ))
    row = _row(mismatch, "eps_diluted")
    assert row["outcome"] == "unit_mismatch"
    assert row["delta"] is None
    assert row["tolerance"] is None


def test_currency_mismatch_between_release_and_cell_unit():
    figure = _figure("revenue", "Net sales", 94.93, currency="EUR", tag="f")
    result = reconcile_release(_release([figure]), _packet(
        _cell("c-rev-1", "revenue", value="94930000000", unit="USD")
    ))
    assert _row(result, "revenue")["outcome"] == "unit_mismatch"


def test_iso4217_unit_namespace_prefix_is_accepted_as_currency():
    # E2 nit: ``iso4217:USD`` is the same currency as ``USD``.
    per_share = _figure("eps_diluted", "Diluted", 1.64, units="per_share", scale_factor=1.0, tag="i")
    agreed = reconcile_release(_release([per_share]), _packet(
        _cell("c-eps-1", "diluted_earnings_per_share", value="1.64", unit="iso4217:USD/shares")
    ))
    assert _row(agreed, "eps_diluted")["outcome"] == "agrees"

    monetary = _figure("revenue", "Net sales", 94.93, tag="o")
    agreed_money = reconcile_release(_release([monetary]), _packet(
        _cell("c-rev-1", "revenue", value="94930000000", unit="iso4217:USD")
    ))
    assert _row(agreed_money, "revenue")["outcome"] == "agrees"

    # A namespaced DIFFERENT currency still mismatches.
    mismatch = reconcile_release(_release([monetary]), _packet(
        _cell("c-rev-2", "revenue", value="94930000000", unit="iso4217:EUR")
    ))
    assert _row(mismatch, "revenue")["outcome"] == "unit_mismatch"


# ─── (c) period matching ──────────────────────────────────────────────────────

def test_quarter_label_does_not_match_annual_or_instant_or_startless_cells():
    figure = _figure("revenue", "Net sales", 94.93)
    annual_only = _packet(
        _cell("c-fy-1", "revenue", value="94930000000", start=FY_START)
    )
    row = _row(reconcile_release(_release([figure]), annual_only), "revenue")
    assert row["outcome"] == "no_packet_cell"
    assert row["filed_cell_ids"] == []
    assert row["filed_value"] is None

    instant_only = _packet(_cell("c-in-1", "revenue", value="94930000000", kind="instant", start=None))
    assert _row(reconcile_release(_release([figure]), instant_only), "revenue")["outcome"] == "no_packet_cell"

    startless = _packet(_cell("c-ns-1", "revenue", value="94930000000", start=None))
    assert _row(reconcile_release(_release([figure]), startless), "revenue")["outcome"] == "no_packet_cell"


def test_unknown_period_label_is_never_guessed_and_annual_label_matches():
    unknown = _figure("revenue", "Net sales", 94.93, period_label="Six Months Ended March 31, 2026")
    row = _row(reconcile_release(_release([unknown]), _packet(
        _cell("c-fy-1", "revenue", value="94930000000", start=FY_START)
    )), "revenue")
    assert row["outcome"] == "period_length_unknown"
    assert row["period_length_class"] is None
    assert row["filed_value"] is None

    annual = _figure("revenue", "Net sales", 94.93, period_label=FY_LABEL)
    row = _row(reconcile_release(_release([annual]), _packet(
        _cell("c-fy-1", "revenue", value="94930000000", start=FY_START)
    )), "revenue")
    assert row["outcome"] == "agrees"
    assert row["period_length_class"] == "annual"


# ─── (d) non-GAAP retention ───────────────────────────────────────────────────

def test_non_gaap_eps_is_retained_never_compared_and_gaap_reconciles():
    non_gaap = _figure(
        "eps_diluted", "Adjusted Diluted EPS", 2.10,
        basis="non_gaap", units="per_share", scale_factor=1.0, tag="n",
    )
    gaap = _figure(
        "eps_diluted", "Diluted", 1.64,
        units="per_share", scale_factor=1.0, tag="g",
    )
    result = reconcile_release(
        _release([non_gaap, gaap]),
        _packet(_cell("c-eps-1", "diluted_earnings_per_share", value="1.64", unit="USD/shares")),
    )
    retained = _row(result, "eps_diluted", basis="non_gaap")
    assert retained["outcome"] == "non_gaap_retained"
    assert retained["label"] == "Adjusted Diluted EPS"  # verbatim
    assert retained["filed_value"] is None
    assert retained["delta"] is None
    assert retained["tolerance"] is None
    assert retained["filed_cell_ids"] == []

    compared = _row(result, "eps_diluted", basis="gaap")
    assert compared["outcome"] == "agrees"
    assert compared["filed_cell_ids"] == ["c-eps-1"]


# ─── (e) ambiguity between filed cells ────────────────────────────────────────

def test_two_matching_cells_with_different_values_are_ambiguous():
    figure = _figure(
        "eps_diluted", "Diluted", 1.64, units="per_share", scale_factor=1.0, tag="a",
    )
    result = reconcile_release(_release([figure]), _packet(
        _cell("c-eps-2", "diluted_earnings_per_share", value="1.70", unit="USD/shares"),
        _cell("c-eps-1", "diluted_earnings_per_share", value="1.64", unit="USD/shares"),
    ))
    row = _row(result, "eps_diluted")
    assert row["outcome"] == "ambiguous_filed_cell"
    assert row["filed_cell_ids"] == ["c-eps-1", "c-eps-2"]  # sorted, never picked
    assert row["filed_value"] is None
    assert row["delta"] is None

    # Equal cells are not ambiguous.
    agreed = reconcile_release(_release([figure]), _packet(
        _cell("c-eps-1", "diluted_earnings_per_share", value="1.64", unit="USD/shares"),
        _cell("c-eps-2", "diluted_earnings_per_share", value="1.640", unit="USD/shares"),
    ))
    assert _row(agreed, "eps_diluted")["outcome"] == "agrees"


def test_valueless_cells_with_different_non_value_states_are_ambiguous():
    # E2-m4: the ambiguity key carries non_value_state, so two matching
    # valueless cells with different states never collapse to a picked cell.
    figure = _figure("net_income", "Net income", 23.4, tag="s1")
    result = reconcile_release(_release([figure]), _packet(
        _cell("c-ni-1", "net_income_loss", value=None, non_value_state="not_evaluable"),
        _cell("c-ni-2", "net_income_loss", value=None, non_value_state="restated"),
    ))
    row = _row(result, "net_income")
    assert row["outcome"] == "ambiguous_filed_cell"
    assert row["filed_cell_ids"] == ["c-ni-1", "c-ni-2"]  # sorted, never picked
    assert row["filed_value"] is None
    assert row["delta"] is None

    # The SAME state on both cells still collapses; only differing states
    # are ambiguous.
    collapsed = reconcile_release(_release([figure]), _packet(
        _cell("c-ni-1", "net_income_loss", value=None, non_value_state="not_evaluable"),
        _cell("c-ni-2", "net_income_loss", value=None, non_value_state="not_evaluable"),
    ))
    row = _row(collapsed, "net_income")
    assert row["outcome"] == "packet_cell_without_value"
    assert row["non_value_state"] == "not_evaluable"


# ─── (f) filed non-values and release absences ────────────────────────────────

def test_filed_non_value_state_is_carried_verbatim():
    figure = _figure("net_income", "Net income", 23.4, tag="v")
    result = reconcile_release(_release([figure]), _packet(
        _cell("c-ni-1", "net_income_loss", value=None, non_value_state="not_evaluable")
    ))
    row = _row(result, "net_income")
    assert row["outcome"] == "packet_cell_without_value"
    assert row["non_value_state"] == "not_evaluable"
    assert row["filed_value"] is None
    assert row["delta"] is None


def test_non_numeric_filed_value_returns_typed_state_not_a_crash():
    # E2-m3: a filed value that is not a decimal number is a typed state,
    # never a raw InvalidOperation.
    figure = _figure("revenue", "Net sales", 94.93, tag="x1")
    result = reconcile_release(_release([figure]), _packet(
        _cell("c-rev-1", "revenue", value="n/a"),
    ))
    row = _row(result, "revenue")
    assert row["outcome"] == "filed_value_unparseable"
    assert row["filed_cell_ids"] == ["c-rev-1"]
    assert row["released_value"] is None
    assert row["filed_value"] is None
    assert row["delta"] is None
    assert row["tolerance"] is None


def test_typed_absence_becomes_release_absence_row_with_reason_and_detail():
    absence = TypedAbsence(
        concept="gross_profit",
        reason="concept_not_present",
        detail="no row or sentence in this release reports this concept",
        label=None,
    )
    result = reconcile_release(_release(absences=[absence]), _packet())
    row = _row(result, "gross_profit", basis=None)
    assert row["outcome"] == "release_absence"
    assert row["reason"] == "concept_not_present"
    assert row["detail"] == "no row or sentence in this release reports this concept"
    assert row["released_value"] is None
    assert row["filed_value"] is None
    assert row["receipt"] is None


# ─── (g) margins ──────────────────────────────────────────────────────────────

def test_margins_are_derived_ratios_and_never_compared():
    margins = [
        _figure("gross_margin_pct", "Gross margin", 43.7, units="percent", scale_factor=1.0, currency=None, tag="p"),
        _figure("operating_margin_pct", "Operating margin", 31.2, units="percent", scale_factor=1.0, currency=None, tag="q"),
    ]
    result = reconcile_release(_release(margins), _packet(
        _cell("c-gp-1", "gross_profit", value="41000000000"),
    ))
    for concept in ("gross_margin_pct", "operating_margin_pct"):
        row = _row(result, concept)
        assert row["outcome"] == "derived_ratio_not_compared"
        assert row["metric_id"] is None
        assert row["filed_value"] is None
        assert row["delta"] is None


# ─── (h) series and definition changes ────────────────────────────────────────

def _eps_event(event_key: str, report_date: str, non_gaap_label: str, gaap_filed: str):
    figures = [
        _figure("eps_diluted", "Diluted", float(gaap_filed), units="per_share", scale_factor=1.0, tag=f"g{report_date}"),
        _figure(
            "eps_diluted", non_gaap_label, 2.05,
            basis="non_gaap", units="per_share", scale_factor=1.0, tag=f"n{report_date}",
        ),
    ]
    cells = [_cell(f"c-{report_date}", "diluted_earnings_per_share", value=gaap_filed, unit="USD/shares")]
    return reconcile_release(
        _release(figures, event_key=event_key, report_date=report_date), _packet(*cells)
    )


def test_relabel_starts_new_series_and_records_each_definition_change():
    events = [
        _eps_event(f"{CIK:010d}|2026-04-25", "2026-04-25", "Adjusted EPS", gaap_filed="1.60"),
        _eps_event(f"{CIK:010d}|2026-07-24", "2026-07-24", "Core EPS", gaap_filed="1.64"),
        _eps_event(f"{CIK:010d}|2026-10-23", "2026-10-23", "Adjusted EPS", gaap_filed="1.71"),
    ]
    series = build_release_series(events)
    assert series["schema"] == SCHEMA_ID + "#series"

    keys = [item["key"] for item in series["series"]]
    assert keys == [
        {"concept": "eps_diluted", "basis": "gaap", "label_key": "diluted", "period_length_class": "quarter"},
        {"concept": "eps_diluted", "basis": "non_gaap", "label_key": "adjusted eps", "period_length_class": "quarter"},
        {"concept": "eps_diluted", "basis": "non_gaap", "label_key": "core eps", "period_length_class": "quarter"},
    ]

    by_key = {tuple(sorted(item["key"].items())): item["points"] for item in series["series"]}
    gaap_points = by_key[(
        ("basis", "gaap"), ("concept", "eps_diluted"),
        ("label_key", "diluted"), ("period_length_class", "quarter"),
    )]
    assert [point["event_key"] for point in gaap_points] == [
        f"{CIK:010d}|2026-04-25", f"{CIK:010d}|2026-07-24", f"{CIK:010d}|2026-10-23",
    ]
    assert all(point["outcome"] == "agrees" for point in gaap_points)
    # GAAP and non-GAAP never share a series.
    non_gaap_points = [
        point
        for item in series["series"]
        if item["key"]["basis"] == "non_gaap"
        for point in item["points"]
    ]
    assert len(non_gaap_points) == 3
    assert not ({id(p) for p in gaap_points} & {id(p) for p in non_gaap_points})

    # E2-m1: the A→B→A revert is recorded as its own definition change, so
    # the history holds two changes, not one.
    assert series["definition_changes"] == [
        {
            "concept": "eps_diluted",
            "basis": "non_gaap",
            "period_length_class": "quarter",
            "from_label": "Adjusted EPS",
            "to_label": "Core EPS",
            "first_event_key": f"{CIK:010d}|2026-07-24",
        },
        {
            "concept": "eps_diluted",
            "basis": "non_gaap",
            "period_length_class": "quarter",
            "from_label": "Core EPS",
            "to_label": "Adjusted EPS",
            "first_event_key": f"{CIK:010d}|2026-10-23",
        },
    ]


def test_q4_and_full_year_columns_yield_one_series_per_period_length_class():
    # E2-M1: one release, one label, one period_end — two period lengths.
    # The Q4 and full-year columns must never share a series.
    figures = [
        _figure("revenue", "Net sales", 25.1, period_label=Q_LABEL, period_end=Q_END, tag="q4c", display="25.1"),
        _figure("revenue", "Net sales", 94.93, period_label=FY_LABEL, period_end=Q_END, tag="fyc", display="94.93"),
    ]
    packet = _packet(
        _cell("c-q-1", "revenue", value="25100000000", start=Q_START, end=Q_END),
        _cell("c-y-1", "revenue", value="94930000000", start=FY_START, end=Q_END),
    )
    reconciliation = reconcile_release(_release(figures), packet)
    rows = {row["period_length_class"]: row for row in reconciliation.to_dict()["rows"]}
    assert set(rows) == {"quarter", "annual"}
    assert rows["quarter"]["outcome"] == "agrees"
    assert rows["quarter"]["released_value"] == "25100000000"
    assert rows["quarter"]["filed_cell_ids"] == ["c-q-1"]
    assert rows["annual"]["outcome"] == "agrees"
    assert rows["annual"]["released_value"] == "94930000000"
    assert rows["annual"]["filed_cell_ids"] == ["c-y-1"]

    series = build_release_series([reconciliation])
    assert [item["key"] for item in series["series"]] == [
        {"concept": "revenue", "basis": "gaap", "label_key": "net sales", "period_length_class": "annual"},
        {"concept": "revenue", "basis": "gaap", "label_key": "net sales", "period_length_class": "quarter"},
    ]
    points = {item["key"]["period_length_class"]: item["points"] for item in series["series"]}
    assert [(p["period_length_class"], p["released_value"]) for p in points["annual"]] == [
        ("annual", "94930000000"),
    ]
    assert [(p["period_length_class"], p["released_value"]) for p in points["quarter"]] == [
        ("quarter", "25100000000"),
    ]
    assert series["definition_changes"] == []


def _two_non_gaap_labels_event(event_key: str, report_date: str, labels, gaap_filed: str):
    figures = [
        _figure("eps_diluted", "Diluted", float(gaap_filed), units="per_share", scale_factor=1.0, tag=f"g{report_date}"),
        *(
            _figure(
                "eps_diluted", label, 2.05,
                basis="non_gaap", units="per_share", scale_factor=1.0, tag=f"n{label}{report_date}",
            )
            for label in labels
        ),
    ]
    cells = [_cell(f"c-{report_date}", "diluted_earnings_per_share", value=gaap_filed, unit="USD/shares")]
    return reconcile_release(
        _release(figures, event_key=event_key, report_date=report_date), _packet(*cells)
    )


def test_two_labels_within_one_event_record_no_definition_change_in_either_order():
    # E2-m2: the label SET of an event is what changes (or does not); two
    # labels inside one event never record a change against each other,
    # whatever figure order the release lists them in.
    events = [
        _two_non_gaap_labels_event(
            f"{CIK:010d}|2026-04-25", "2026-04-25", ["Adjusted EPS", "Core EPS"], gaap_filed="1.60",
        ),
        _two_non_gaap_labels_event(
            f"{CIK:010d}|2026-07-24", "2026-07-24", ["Core EPS", "Adjusted EPS"], gaap_filed="1.64",
        ),
    ]
    series = build_release_series(events)
    assert series["definition_changes"] == []
    assert sorted(item["key"]["label_key"] for item in series["series"]) == [
        "adjusted eps", "core eps", "diluted",
    ]


# ─── extra outcomes the packet requires to be reachable ───────────────────────

def test_unit_unrecognized_for_unknown_release_units():
    figure = _figure("revenue", "Net sales", 94.93, units="gold_talents", scale_factor=None, tag="u")
    result = reconcile_release(_release([figure]), _packet(
        _cell("c-rev-1", "revenue", value="94930000000")
    ))
    row = _row(result, "revenue")
    assert row["outcome"] == "unit_unrecognized"
    assert row["released_value"] is None
    assert row["delta"] is None


def test_guidance_is_context_only_however_figures_module_names_it():
    by_concept = _figure(
        "guidance_eps_low", "the next fiscal quarter of fiscal 2027", 7.20,
        basis="non_gaap", units="per_share", scale_factor=1.0, period_label="the next fiscal quarter of fiscal 2027",
        period_end="", tag="s",
    )
    by_label = _figure("revenue", "Revenue outlook", 96.0, period_label="Fiscal Year 2027 Outlook", period_end="", tag="t")
    result = reconcile_release(_release([by_concept, by_label]), _packet())
    assert _row(result, "guidance_eps_low", basis="non_gaap")["outcome"] == "guidance_context_only"
    assert _row(result, "revenue")["outcome"] == "guidance_context_only"


def test_unmapped_roster_concept_is_reported_not_compared():
    figure = _figure(
        "operating_cash_flow", "Cash generated by operating activities", 30.2, tag="w",
    )
    result = reconcile_release(_release([figure]), _packet())
    row = _row(result, "operating_cash_flow")
    assert row["outcome"] == "unmapped_concept"
    assert row["metric_id"] is None
    assert row["filed_value"] is None


# ─── input addressing, output shape, determinism ──────────────────────────────

def test_release_input_from_event_uses_real_event_attributes():
    original = ReleaseRevision(
        filing_key=FilingKey(cik=CIK, accession="0001234567-26-000041"),
        form="8-K", filing_date="2026-04-25", acceptance_datetime="2026-04-25T16:30:15Z",
        report_date=REPORT_DATE, source_sha256="a" * 64, document_id="doc-1",
    )
    amendment = ReleaseRevision(
        filing_key=FilingKey(cik=CIK, accession="0001234567-26-000099"),
        form="8-K/A", filing_date="2026-05-02", acceptance_datetime="2026-05-02T16:30:15Z",
        report_date=REPORT_DATE, source_sha256="b" * 64, document_id="doc-2",
    )
    event = ReleaseEvent(cik=CIK, report_date=REPORT_DATE, revisions=(original, amendment))
    figure_set = ReleaseFigureSet()
    release = release_input_from_event(event, figure_set)
    assert release.event_key == f"{CIK:010d}|{REPORT_DATE}"
    assert release.report_date == REPORT_DATE
    assert release.accession == "0001234567-26-000099"  # the current revision's filing
    assert release.figure_set is figure_set
    assert release.company_event_id is None


def test_mapped_metric_ids_are_pinned_to_the_catalog():
    catalog = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    metric_ids = {entry["metric_id"] for entry in catalog["metrics"]}
    missing = sorted(set(CONCEPT_TO_METRIC.values()) - metric_ids)
    assert missing == [], f"mapped metric ids absent from metric_catalog.yaml: {missing}"


def test_output_shape_rows_sorted_counts_and_packet_accessions():
    figures = [
        _figure("eps_diluted", "Diluted", 1.64, units="per_share", scale_factor=1.0, tag="z"),
        _figure("revenue", "Net sales", 94.93),
        _figure("eps_diluted", "Adjusted Diluted EPS", 2.10, basis="non_gaap", units="per_share", scale_factor=1.0, tag="y"),
    ]
    packet = _packet(
        _cell("c-eps-1", "diluted_earnings_per_share", value="1.64", unit="USD/shares"),
        _cell("c-rev-1", "revenue", value="94930000000", accession="0001234567-26-000077"),
        _cell("c-rev-2", "revenue", value="94930000000"),
    )
    payload = reconcile_release(_release(figures), packet).to_dict()
    assert payload["schema"] == SCHEMA_ID
    assert payload["authority"] == {"class": "context_only", "display_only": True}
    assert payload["event_key"] == EVENT_KEY
    assert payload["report_date"] == REPORT_DATE
    assert payload["release_accession"] == ACCESSION
    assert payload["packet_accessions"] == sorted({
        "0001234567-26-000042", "0001234567-26-000077",
    })
    # Rows sorted by (concept, basis, period_end).
    ordering = [(row["concept"], row["basis"], row["period_end"]) for row in payload["rows"]]
    assert ordering == sorted(ordering)
    assert payload["outcome_counts"] == {"agrees": 2, "non_gaap_retained": 1}
    assert set(payload["rows"][0]) >= {
        "concept", "metric_id", "basis", "label", "period_end", "period_length_class",
        "outcome", "released_value", "filed_value", "delta", "tolerance",
        "filed_cell_ids", "receipt",
    }
    # Identical cells collapse to one row with both ids.
    revenue_row = next(r for r in payload["rows"] if r["concept"] == "revenue")
    assert revenue_row["filed_cell_ids"] == ["c-rev-1", "c-rev-2"]


def test_to_dict_holds_no_floats_and_is_deterministic():
    figures = [
        _figure("revenue", "Net sales", 94.93),
        _figure("eps_diluted", "Diluted", 1.64, units="per_share", scale_factor=1.0, tag="d"),
        _figure("eps_diluted", "Adjusted Diluted EPS", 2.10, basis="non_gaap", units="per_share", scale_factor=1.0, tag="k"),
        _figure("gross_margin_pct", "Gross margin", 43.7, units="percent", scale_factor=1.0, currency=None, tag="j"),
    ]
    absences = [TypedAbsence(concept="net_income", reason="concept_not_present", detail="absent here")]
    packet = _packet(
        _cell("c-rev-1", "revenue", value="94930000000"),
        _cell("c-eps-1", "diluted_earnings_per_share", value="1.64", unit="USD/shares"),
    )
    release = _release(figures, absences)
    first = reconcile_release(release, packet)
    second = reconcile_release(release, packet)
    assert first.to_dict() == second.to_dict()
    _assert_no_floats(first.to_dict())
    assert first.authority == {"class": "context_only", "display_only": True}
    assert build_release_series([first]) == build_release_series([second])
    _assert_no_floats(build_release_series([first]))


def test_a25_invented_release_figure_never_overwrites_the_filed_packet():
    # A25: a release (or model) figure that disagrees with the filing is stated as a
    # context-only `differs` row; the filed packet is read, never edited, and no row or
    # payload key carries canonical-value or action authority.
    import copy

    invented = _figure("revenue", "Net sales", 120.00, display="120.00")
    packet = _packet(_cell("c-rev-1", "revenue", value="94930000000"))
    before = copy.deepcopy(packet)
    reconciliation = reconcile_release(_release([invented]), packet)
    payload = reconciliation.to_dict()
    assert packet == before
    row = _row(reconciliation, "revenue")
    assert row["outcome"] == "differs"
    assert row["filed_value"] == "94930000000"
    assert row["released_value"] == "120000000000"
    assert payload["authority"] == {"class": "context_only", "display_only": True}
    forbidden = {"canonical_value", "action", "trade", "size", "rank", "score", "override"}
    assert not forbidden & set(payload)
    assert all(not forbidden & set(item) for item in payload["rows"])
