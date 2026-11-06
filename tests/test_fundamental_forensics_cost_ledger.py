"""FIF V1-b cost ledger: rates, quantity readers, burden ledger, build, print, CLI.

The core rule under test: a cost that was not measured and has no declared
rate is ``unmeasured``, never ``0`` — and every total or per-unit figure built
from incomplete components says so, in the same object, every time.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from engine.fundamental_forensics.cost_ledger import (
    BURDEN_SCHEMA,
    COMPONENTS,
    ESTIMATED,
    MEASURED,
    MAX_BURDEN_MINUTES,
    UNMEASURED,
    CostLedgerError,
    Quantity,
    append_burden,
    build_cost_ledger,
    inference_quantity_from_usage,
    licence_quantity,
    load_rates,
    parse_quantity,
    read_burden,
    render_print,
    review_quantity_from_burden_rows,
    source_quantity_from_receipt,
    storage_quantity_from_deep_packages,
)

ROOT = Path(__file__).resolve().parents[1]
RATES_PATH = ROOT / "config" / "fundamental_forensics" / "cost_rates.v1.json"
SCHEMA_PATH = ROOT / "contracts" / "fundamental_forensics_cost_ledger.v1.schema.json"
MODULE_PATH = ROOT / "engine" / "fundamental_forensics" / "cost_ledger.py"
KERNEL_DIR = ROOT / "engine" / "fundamental_forensics"
SCRIPT_PATH = ROOT / "scripts" / "fif_cost_ledger.py"

BUILT_AT = datetime(2026, 10, 19, tzinfo=timezone.utc)


def _rates_doc() -> dict:
    return json.loads(RATES_PATH.read_text(encoding="utf-8"))


def _write_rates(tmp_path: Path, doc: dict, name: str = "rates.json") -> str:
    path = tmp_path / name
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return str(path)


CSV_HEADER = (
    "cik,slot_id,accession,member_count,primary_present,primary_bytes,"
    "schema_present,schema_bytes,presentation_present,presentation_bytes,"
    "calculation_present,calculation_bytes,definition_present,definition_bytes,"
    "label_present,label_bytes,summed_declared_bytes,notes"
)


def _packages_csv(rows: list[dict]) -> str:
    lines = [CSV_HEADER]
    for row in rows:
        cells = [
            row.get("cik", "0000000001"),
            row.get("slot_id", "A1"),
            row.get("accession", "0000000001-26-000001"),
            row.get("member_count", "6"),
            row.get("primary_present", "True"),
            row.get("primary_bytes", "1000"),
            row.get("schema_present", "True"),
            row.get("schema_bytes", "2000"),
            row.get("presentation_present", "True"),
            row.get("presentation_bytes", "3000"),
            row.get("calculation_present", "True"),
            row.get("calculation_bytes", "4000"),
            row.get("definition_present", "True"),
            row.get("definition_bytes", "5000"),
            row.get("label_present", "True"),
            row.get("label_bytes", "6000"),
            row.get("summed_declared_bytes", "21000"),
            row.get("notes", "ok"),
        ]
        lines.append(",".join(cells))
    return "\n".join(lines) + "\n"


def _warm_receipt() -> dict:
    return {
        "get_count_total": 0,
        "transfer_bytes_total": 0,
        "measured_implied_cold_gets": {
            "deep_per_issuer": {
                "submissions_per_issuer": 1,
                "index_per_slot": 1,
                "deep_slots": 4,
            },
            "core_per_issuer": {
                "submissions_per_issuer": 1,
                "companyfacts_per_issuer": 1,
                "primary_doc_per_slot": 2,
            },
            "deep_cold_fleet_total_estimate_at_measured": 1250,
        },
    }


def _burden_row(
    event_id: str = "evt-1",
    recorded_at: str = "2026-10-19T01:00:00Z",
    minutes: float = 30,
    actor_role: str = "seat",
    act_kind: str = "review",
    ref: str = "PR #1",
    note: str = "",
) -> dict:
    return {
        "schema": BURDEN_SCHEMA,
        "event_id": event_id,
        "recorded_at": recorded_at,
        "actor_role": actor_role,
        "act_kind": act_kind,
        "minutes": minutes,
        "ref": ref,
        "note": note,
    }


def _base_quantities() -> dict:
    return {
        "source": Quantity(10.0, "get", MEASURED, counts={"transfer_bytes_total": 5}),
        "licence": Quantity(1000.0, "issuer", MEASURED),
        "storage": Quantity(
            2.0,
            "gb",
            MEASURED,
            counts={"six_role_bytes": 2_000_000_000, "all_member_bytes": 3_000_000_000},
        ),
        "parse": Quantity(None, "cpu_second", UNMEASURED),
        "inference": Quantity(2.5, "usd", MEASURED),
        "review": Quantity(30.0, "minute", MEASURED),
    }


def _denominators(**overrides) -> dict:
    doc = {
        "qualified_filings": {"value": None, "source": "pending"},
        "qualified_issuers_deep": {"value": None, "source": "pending"},
        "qualified_issuers_core": {"value": None, "source": "pending"},
        "queries": {"value": None, "source": "pending", "window": None},
    }
    doc.update(overrides)
    return doc


def _build_ledger(
    quantities: dict | None = None,
    denominators: dict | None = None,
    burden_rows: list | None = None,
    rates: dict | None = None,
) -> dict:
    return build_cost_ledger(
        rates=rates if rates is not None else load_rates(RATES_PATH),
        quantities=quantities if quantities is not None else _base_quantities(),
        denominators=denominators if denominators is not None else _denominators(),
        burden_rows=burden_rows,
        built_at=BUILT_AT,
    )


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )


# ── 1. rates ─────────────────────────────────────────────────────────────────


def test_shipped_rates_config_loads() -> None:
    rates = load_rates(RATES_PATH)
    assert set(rates["components"]) == set(COMPONENTS)
    storage = rates["components"]["storage"]
    assert storage["usd_per_unit"] == 0.015
    assert storage["verified"] is False
    assert storage["basis_period"] == "per_month"
    for component in ("parse", "review"):
        assert rates["components"][component]["status"] == "unmeasured"
        assert rates["components"][component]["usd_per_unit"] is None
    assert rates["rates_id"] == "fif_cost_rates_v1"
    assert re.fullmatch(r"[a-f0-9]{64}", rates["content_sha256"])
    assert rates["inference_row_filter"]["stage_prefixes"] == [
        "fundamental_forensics",
        "fif",
    ]


def test_rates_shape_refusals(tmp_path: Path) -> None:
    def variant(edit) -> dict:
        doc = _rates_doc()
        edit(doc)
        return doc

    def drop_rates(doc: dict) -> None:
        del doc["rates"]

    def wrong_schema(doc: dict) -> None:
        doc["schema"] = "some_other_schema/v9"

    def declared_with_null_usd(doc: dict) -> None:
        doc["rates"][0]["usd_per_unit"] = None

    def unmeasured_with_number(doc: dict) -> None:
        for entry in doc["rates"]:
            if entry["component"] == "parse":
                entry["usd_per_unit"] = 0.01

    def bad_basis_period(doc: dict) -> None:
        doc["rates"][0]["basis_period"] = "per_year"

    def empty_source(doc: dict) -> None:
        doc["rates"][0]["source"] = ""

    def unknown_component(doc: dict) -> None:
        doc["rates"][0]["component"] = "transport"

    def bad_status(doc: dict) -> None:
        doc["rates"][0]["status"] = "maybe"

    cases = [
        drop_rates,
        wrong_schema,
        declared_with_null_usd,
        unmeasured_with_number,
        bad_basis_period,
        empty_source,
        unknown_component,
        bad_status,
    ]
    for edit in cases:
        path = tmp_path / f"rates_{edit.__name__}.json"
        path.write_text(json.dumps(variant(edit)), encoding="utf-8")
        with pytest.raises(CostLedgerError) as excinfo:
            load_rates(path)
        assert excinfo.value.code == "rates_shape", edit.__name__

    broken = tmp_path / "rates_not_json.json"
    broken.write_text("this is not json", encoding="utf-8")
    with pytest.raises(CostLedgerError) as excinfo:
        load_rates(broken)
    assert excinfo.value.code == "rates_shape"


def test_rates_missing_component(tmp_path: Path) -> None:
    doc = _rates_doc()
    doc["rates"] = [entry for entry in doc["rates"] if entry["component"] != "parse"]
    path = _write_rates(tmp_path, doc)
    with pytest.raises(CostLedgerError) as excinfo:
        load_rates(path)
    assert excinfo.value.code == "rates_missing_component"


def test_rates_duplicate_component(tmp_path: Path) -> None:
    doc = _rates_doc()
    doc["rates"].append(dict(doc["rates"][2]))  # duplicate storage rate
    path = _write_rates(tmp_path, doc)
    with pytest.raises(CostLedgerError) as excinfo:
        load_rates(path)
    assert excinfo.value.code == "rates_duplicate_component"


# ── 2. receipt reader ────────────────────────────────────────────────────────


def test_warm_receipt_measured_zero_with_cold_counts() -> None:
    quantity = source_quantity_from_receipt(_warm_receipt())
    assert quantity.value == 0.0
    assert quantity.status == MEASURED
    assert quantity.unit == "get"
    assert "warm_cache_run" in quantity.notes
    assert quantity.counts["transfer_bytes_total"] == 0
    assert quantity.counts["cold_deep_gets_per_issuer"] == 5
    assert quantity.counts["cold_core_gets_per_issuer"] == 4
    assert quantity.counts["cold_deep_gets_fleet_estimate"] == 1250


def test_cold_receipt_has_no_warm_note() -> None:
    receipt = _warm_receipt()
    receipt["get_count_total"] = 7
    quantity = source_quantity_from_receipt(receipt)
    assert quantity.value == 7.0
    assert quantity.status == MEASURED
    assert "warm_cache_run" not in quantity.notes


def test_receipt_without_get_count_total_is_unmeasured() -> None:
    quantity = source_quantity_from_receipt({"transfer_bytes_total": 4096})
    assert quantity.value is None
    assert quantity.status == UNMEASURED
    ledger = _build_ledger(quantities={**_base_quantities(), "source": quantity})
    assert ledger["components"]["source"]["cost_status"] == "incomplete"
    assert ledger["components"]["source"]["cost_usd"] is None


# ── 3. deep packages CSV ─────────────────────────────────────────────────────


def test_false_bytes_cells_are_unparseable_and_excluded() -> None:
    csv_text = _packages_csv(
        [
            {},
            {
                "presentation_bytes": "False",
                "calculation_bytes": "False",
                "definition_bytes": "False",
                "label_bytes": "False",
            },
        ]
    )
    quantity = storage_quantity_from_deep_packages(csv_text)
    # Row 1 parses fully; row 2 keeps its primary+schema cells (1000+2000) but
    # its four False cells are excluded from the sum and counted per role.
    assert quantity.counts["rows"] == 2
    assert quantity.counts["six_role_bytes"] == 24000
    assert quantity.value == pytest.approx(24000 / 1e9)
    assert quantity.counts["unparseable_cells"] == {
        "primary": 0,
        "schema": 0,
        "presentation": 1,
        "calculation": 1,
        "definition": 1,
        "label": 1,
    }
    assert quantity.status == ESTIMATED
    assert "unparseable_cells_excluded" in quantity.notes
    assert "primary_bytes_understated" not in quantity.notes


def test_exhibit_primary_row_counted_and_flagged() -> None:
    csv_text = _packages_csv(
        [{"notes": "primary_inferred_from=a10-kexhibit21109272025.htm"}]
    )
    quantity = storage_quantity_from_deep_packages(csv_text)
    assert quantity.counts["primary_misidentified_suspect"] == 1
    assert "primary_bytes_understated" in quantity.notes
    assert quantity.status == MEASURED  # suspects alone do not demote the sum


def test_missing_role_cells_counted() -> None:
    csv_text = _packages_csv([{"label_present": "False", "notes": "ok"}])
    quantity = storage_quantity_from_deep_packages(csv_text)
    assert quantity.counts["missing_role_cells"]["label"] == 1
    assert quantity.counts["missing_role_cells"]["primary"] == 0
    assert quantity.counts["all_member_bytes"] == 21000


def test_bad_csv_header_refused() -> None:
    csv_text = CSV_HEADER.replace(",notes", "") + "\n"
    with pytest.raises(CostLedgerError) as excinfo:
        storage_quantity_from_deep_packages(csv_text)
    assert excinfo.value.code == "packages_shape"


# ── 4. inference usage ───────────────────────────────────────────────────────


_ROW_FILTER = {"stage_prefixes": ["fif"], "lane_prefixes": ["fundamental_forensics"]}


def test_inference_matches_stage_or_lane_prefix() -> None:
    # No undecodable line here: since r3 an undecodable line demotes the
    # whole quantity (usage_lines_undecodable), so the prefix-matching sum
    # is pinned on a fully decodable set.
    lines = [
        json.dumps({"stage": "fif_capture", "lane": "other", "est_cost_usd": 1.5, "ts": "2026-10-01T00:00:00Z"}),
        json.dumps({"stage": "other", "lane": "fundamental_forensics_v1", "est_cost_usd": 2.25, "ts": "2026-10-02T00:00:00Z"}),
        json.dumps({"stage": "FIF_REVIEW", "lane": "x", "est_cost_usd": 4.0, "ts": "2026-10-03T00:00:00Z"}),
        json.dumps({"stage": "altdata_brain", "lane": "unknown", "est_cost_usd": 9.0, "ts": "2026-10-04T00:00:00Z"}),
    ]
    quantity = inference_quantity_from_usage(lines, _ROW_FILTER)
    assert quantity.value == pytest.approx(7.75)
    assert quantity.status == MEASURED
    assert quantity.counts["rows_read"] == 4
    assert quantity.counts["rows_matched"] == 3
    assert quantity.counts["rows_in_window"] == 3
    assert quantity.counts["rows_undecodable"] == 0
    assert quantity.counts["rows_uncosted"] == 0
    assert quantity.counts["declared_window"] is None
    assert quantity.counts["window"] == {
        "min": "2026-10-01T00:00:00Z",
        "max": "2026-10-03T00:00:00Z",
    }


def test_inference_zero_matches_is_unmeasured_absent() -> None:
    lines = [json.dumps({"stage": "altdata_brain", "lane": "unknown", "est_cost_usd": 9.0})]
    quantity = inference_quantity_from_usage(lines, _ROW_FILTER)
    assert quantity.value is None
    assert quantity.status == UNMEASURED
    assert "inference_rows_absent" in quantity.notes
    assert quantity.counts["window"] is None
    ledger = _build_ledger(quantities={**_base_quantities(), "inference": quantity})
    component = ledger["components"]["inference"]
    assert component["quantity_value"] is None
    assert component["cost_usd"] is None
    assert component["cost_status"] == "incomplete"
    assert component["incomplete_reason"] == "inference_rows_absent"
    assert "inference" in ledger["totals"]["query_window"]["incomplete_components"]


def test_inference_uncosted_row_is_unmeasured_uncosted() -> None:
    lines = [
        json.dumps({"stage": "fif_capture", "est_cost_usd": 1.5, "ts": "2026-10-01T00:00:00Z"}),
        json.dumps({"stage": "fif_capture", "est_cost_usd": None, "ts": "2026-10-02T00:00:00Z"}),
    ]
    quantity = inference_quantity_from_usage(lines, _ROW_FILTER)
    assert quantity.value is None
    assert quantity.status == UNMEASURED
    assert "inference_rows_uncosted" in quantity.notes
    assert quantity.counts["rows_matched"] == 2
    assert quantity.counts["rows_uncosted"] == 1
    ledger = _build_ledger(quantities={**_base_quantities(), "inference": quantity})
    component = ledger["components"]["inference"]
    assert component["quantity_value"] is None
    assert component["cost_usd"] is None
    assert component["cost_status"] == "incomplete"
    assert component["incomplete_reason"] == "inference_rows_uncosted"
    assert "inference" in ledger["totals"]["query_window"]["incomplete_components"]


def test_inference_empty_filter_is_unmeasured_filter_empty() -> None:
    lines = [json.dumps({"stage": "fif_capture", "est_cost_usd": 1.5})]
    quantity = inference_quantity_from_usage(
        lines, {"stage_prefixes": [], "lane_prefixes": []}
    )
    assert quantity.value is None
    assert quantity.status == UNMEASURED
    assert "inference_filter_empty" in quantity.notes
    quantity = inference_quantity_from_usage(lines, {})
    assert quantity.status == UNMEASURED
    assert "inference_filter_empty" in quantity.notes
    ledger = _build_ledger(quantities={**_base_quantities(), "inference": quantity})
    component = ledger["components"]["inference"]
    assert component["cost_status"] == "incomplete"
    assert component["incomplete_reason"] == "inference_filter_empty"
    assert "inference" in ledger["totals"]["query_window"]["incomplete_components"]


def test_inference_fully_costed_rows_stay_measured() -> None:
    lines = [
        json.dumps({"stage": "fif_capture", "est_cost_usd": 1.5, "ts": "2026-10-01T00:00:00Z"}),
        json.dumps({"stage": "other", "lane": "fundamental_forensics_v1", "est_cost_usd": 1.0}),
    ]
    quantity = inference_quantity_from_usage(lines, _ROW_FILTER)
    assert quantity.value == pytest.approx(2.5)
    assert quantity.status == MEASURED
    ledger = _build_ledger(quantities={**_base_quantities(), "inference": quantity})
    component = ledger["components"]["inference"]
    assert component["cost_status"] == "measured"
    assert component["cost_usd"] == pytest.approx(2.5)
    assert component["incomplete_reason"] is None
    assert "inference" not in ledger["totals"]["one_time"]["incomplete_components"]


def test_probe_base_reported_uncosted_inference_as_declared_or_measured() -> None:
    # Probe for the reviewed BASE defect: an uncosted matched row used to give
    # status estimated, and with the verified inference rate build_cost_ledger
    # promoted it to cost_status declared (an empty filter or absent rows gave
    # measured 0.0) — so inference never reached incomplete_components.
    lines = [json.dumps({"stage": "fif_capture", "est_cost_usd": None})]
    quantity = inference_quantity_from_usage(lines, _ROW_FILTER)
    ledger = _build_ledger(quantities={**_base_quantities(), "inference": quantity})
    component = ledger["components"]["inference"]
    assert component["cost_status"] == "incomplete"
    assert component["cost_usd"] is None
    assert component["quantity_value"] is None
    assert component["incomplete_reason"] == "inference_rows_uncosted"


# ── 4b. inference window tied to the queries window (F2) ─────────────────────


_QUERIES_WINDOW = {"start": "2026-10-01T00:00:00Z", "end": "2026-10-02T00:00:00Z"}


def test_inference_rows_outside_window_excluded_and_counted() -> None:
    lines = [
        # before the window start
        json.dumps({"stage": "fif_capture", "est_cost_usd": 5.0, "ts": "2026-09-30T23:59:59Z"}),
        # inside [start, end)
        json.dumps({"stage": "fif_capture", "est_cost_usd": 1.5, "ts": "2026-10-01T12:00:00Z"}),
        # exactly at end — excluded, the window is half-open
        json.dumps({"stage": "fif_capture", "est_cost_usd": 7.0, "ts": "2026-10-02T00:00:00Z"}),
        # matched but no ts: cannot be tied to the window, so never included
        json.dumps({"stage": "fif_capture", "est_cost_usd": 2.0}),
    ]
    quantity = inference_quantity_from_usage(lines, _ROW_FILTER, window=_QUERIES_WINDOW)
    assert quantity.value == pytest.approx(1.5)
    assert quantity.status == MEASURED
    assert quantity.counts["rows_matched"] == 4
    assert quantity.counts["rows_in_window"] == 1
    assert quantity.counts["inference_rows_outside_window"] == 3
    assert quantity.counts["inference_rows_untimed"] == 1
    assert quantity.counts["rows_uncosted"] == 0
    assert quantity.counts["declared_window"] == {
        "start": "2026-10-01T00:00:00Z",
        "end": "2026-10-02T00:00:00Z",
    }
    assert quantity.counts["window"] == {
        "min": "2026-10-01T12:00:00Z",
        "max": "2026-10-01T12:00:00Z",
    }


def test_mixed_in_and_outside_window_rows_sum_only_in_window() -> None:
    # A mixed set is measured, with only the in-window sum — and a row that
    # is outside the window and uncosted never counts as an uncosted row,
    # because rows_uncosted covers in-window rows only.
    lines = [
        json.dumps({"stage": "fif_capture", "est_cost_usd": None, "ts": "2026-09-30T23:59:59Z"}),
        json.dumps({"stage": "fif_capture", "est_cost_usd": 1.5, "ts": "2026-10-01T12:00:00Z"}),
        json.dumps({"stage": "fif_capture", "est_cost_usd": 7.0, "ts": "2026-10-02T00:00:00Z"}),
    ]
    quantity = inference_quantity_from_usage(lines, _ROW_FILTER, window=_QUERIES_WINDOW)
    assert quantity.status == MEASURED
    assert quantity.value == pytest.approx(1.5)
    assert quantity.counts["rows_matched"] == 3
    assert quantity.counts["rows_in_window"] == 1
    assert quantity.counts["rows_uncosted"] == 0
    assert quantity.counts["inference_rows_outside_window"] == 2


def test_all_rows_outside_window_is_unmeasured_outside_window_only() -> None:
    lines = [
        json.dumps({"stage": "fif_capture", "est_cost_usd": 5.0, "ts": "2026-09-30T23:59:59Z"}),
        json.dumps({"stage": "fif_capture", "est_cost_usd": 7.0, "ts": "2026-10-02T00:00:00Z"}),
    ]
    quantity = inference_quantity_from_usage(lines, _ROW_FILTER, window=_QUERIES_WINDOW)
    assert quantity.value is None
    assert quantity.status == UNMEASURED
    assert quantity.notes == ("inference_rows_outside_window_only",)
    assert quantity.counts["rows_matched"] == 2
    assert quantity.counts["rows_in_window"] == 0
    assert quantity.counts["inference_rows_outside_window"] == 2
    assert quantity.counts["inference_rows_untimed"] == 0
    ledger = _build_ledger(
        quantities={**_base_quantities(), "inference": quantity},
        denominators=_denominators(
            queries={"value": 10, "source": "coverage proof", "window": _QUERIES_WINDOW}
        ),
    )
    component = ledger["components"]["inference"]
    assert component["cost_status"] == "incomplete"
    assert component["cost_usd"] is None
    assert component["incomplete_reason"] == "inference_rows_outside_window_only"
    assert "inference" in ledger["totals"]["query_window"]["incomplete_components"]


def test_all_rows_untimed_under_window_is_unmeasured_outside_window_only() -> None:
    lines = [
        json.dumps({"stage": "fif_capture", "est_cost_usd": 5.0}),
        json.dumps({"stage": "fif_capture", "est_cost_usd": 1.5, "ts": "yesterday"}),
    ]
    quantity = inference_quantity_from_usage(lines, _ROW_FILTER, window=_QUERIES_WINDOW)
    assert quantity.value is None
    assert quantity.status == UNMEASURED
    assert quantity.notes == ("inference_rows_outside_window_only",)
    assert quantity.counts["rows_matched"] == 2
    assert quantity.counts["rows_in_window"] == 0
    assert quantity.counts["inference_rows_outside_window"] == 2
    assert quantity.counts["inference_rows_untimed"] == 2


def test_inverted_window_refused_in_usage_reader() -> None:
    lines = [json.dumps({"stage": "fif_capture", "est_cost_usd": 5.0, "ts": "2026-10-01T12:00:00Z"})]
    for inverted in (
        {"start": "2026-10-02T00:00:00Z", "end": "2026-10-01T00:00:00Z"},  # start > end
        {"start": "2026-10-01T00:00:00Z", "end": "2026-10-01T00:00:00Z"},  # start == end
    ):
        with pytest.raises(CostLedgerError) as excinfo:
            inference_quantity_from_usage(lines, _ROW_FILTER, window=inverted)
        assert excinfo.value.code == "window_inverted", inverted


def test_inverted_window_refused_in_denominators_check() -> None:
    denominators = _denominators(
        queries={
            "value": 10,
            "source": "coverage proof",
            "window": {"start": "2026-10-02T00:00:00Z", "end": "2026-10-01T00:00:00Z"},
        }
    )
    with pytest.raises(CostLedgerError) as excinfo:
        _build_ledger(denominators=denominators)
    assert excinfo.value.code == "window_inverted"


def test_probe_base_reported_all_outside_inference_as_measured_zero() -> None:
    # Probe for the reviewed BASE defect (r3 R1): rows outside the window
    # still counted as matched, so an all-outside set returned measured 0.0.
    lines = [json.dumps({"stage": "fif_capture", "est_cost_usd": 5.0, "ts": "2026-09-01T00:00:00Z"})]
    quantity = inference_quantity_from_usage(lines, _ROW_FILTER, window=_QUERIES_WINDOW)
    assert quantity.status == UNMEASURED
    assert quantity.value is None
    assert quantity.notes == ("inference_rows_outside_window_only",)


def test_probe_base_accepted_an_inverted_window_as_measured_zero() -> None:
    # Probe for the reviewed BASE defect (r3 R1): an inverted window was not
    # refused, and matched no row, so the reader returned measured 0.0.
    lines = [json.dumps({"stage": "fif_capture", "est_cost_usd": 5.0, "ts": "2026-10-01T12:00:00Z"})]
    with pytest.raises(CostLedgerError) as excinfo:
        inference_quantity_from_usage(
            lines,
            _ROW_FILTER,
            window={"start": "2026-10-02T00:00:00Z", "end": "2026-10-01T00:00:00Z"},
        )
    assert excinfo.value.code == "window_inverted"


def test_missing_queries_window_refuses_cost_per_query() -> None:
    denominators = _denominators(
        queries={"value": 10, "source": "coverage proof", "window": None},
    )
    ledger = _build_ledger(denominators=denominators)
    entry = ledger["per_unit"]["queries"]
    assert entry["one_time_usd"] is None
    assert entry["per_month_usd"] is None
    assert entry["complete"] is False
    assert entry["reason"] == "queries_window_absent"


def test_declared_queries_window_lets_cost_per_query_compute() -> None:
    denominators = _denominators(
        queries={"value": 10, "source": "coverage proof", "window": _QUERIES_WINDOW},
    )
    # A measured inference quantity used against the declared window must
    # carry its own window claim (r4 N1); with the claim the quotient stands.
    inference = Quantity(2.5, "usd", MEASURED, counts={"declared_window": _QUERIES_WINDOW})
    ledger = _build_ledger(
        quantities={**_base_quantities(), "inference": inference},
        denominators=denominators,
    )
    entry = ledger["per_unit"]["queries"]
    assert entry["reason"] != "queries_window_absent"
    # Only the windowed inference total is per-query (r3 R4).
    assert entry["query_window_usd"] == pytest.approx(0.25)
    assert entry["one_time_usd"] is None
    assert entry["per_month_usd"] is None


# ── 4c. inference window must equal the queries window (r3 R2) ───────────────


def _windowed_inference(window: dict, cost: float = 1.5) -> Quantity:
    lines = [
        json.dumps({"stage": "fif_capture", "est_cost_usd": cost, "ts": "2026-10-01T12:00:00Z"})
    ]
    return inference_quantity_from_usage(lines, _ROW_FILTER, window=window)


def test_inference_window_mismatch_with_queries_window_refused() -> None:
    inference = _windowed_inference(_QUERIES_WINDOW)
    denominators = _denominators(
        queries={
            "value": 10,
            "source": "coverage proof",
            "window": {"start": "2026-10-01T00:00:00Z", "end": "2026-10-03T00:00:00Z"},
        }
    )
    with pytest.raises(CostLedgerError) as excinfo:
        _build_ledger(
            quantities={**_base_quantities(), "inference": inference},
            denominators=denominators,
        )
    assert excinfo.value.code == "inference_window_mismatch"


def test_inference_window_declared_but_queries_window_absent_refused() -> None:
    inference = _windowed_inference(_QUERIES_WINDOW)
    with pytest.raises(CostLedgerError) as excinfo:
        _build_ledger(quantities={**_base_quantities(), "inference": inference})
    assert excinfo.value.code == "inference_window_mismatch"


def test_queries_window_declared_but_inference_window_absent_refused() -> None:
    lines = [json.dumps({"stage": "fif_capture", "est_cost_usd": 1.5})]
    inference = inference_quantity_from_usage(lines, _ROW_FILTER)
    assert inference.counts["declared_window"] is None
    denominators = _denominators(
        queries={"value": 10, "source": "coverage proof", "window": _QUERIES_WINDOW}
    )
    with pytest.raises(CostLedgerError) as excinfo:
        _build_ledger(
            quantities={**_base_quantities(), "inference": inference},
            denominators=denominators,
        )
    assert excinfo.value.code == "inference_window_mismatch"


# ── 4c'. a hand-built inference quantity cannot skip the window match (r4 N1) ─


def test_hand_built_measured_inference_without_window_claim_refused() -> None:
    # r4 N1: a hand-built Quantity(9.0, "usd", MEASURED) with no counts used
    # to slip past the window match and compute a per-query quotient nobody
    # had windowed (0.9 complete=True).  Against a declared queries window a
    # measured or estimated inference must carry counts.declared_window.
    denominators = _denominators(
        queries={"value": 10, "source": "coverage proof", "window": _QUERIES_WINDOW}
    )
    for status in (MEASURED, ESTIMATED):
        inference = Quantity(9.0, "usd", status)
        with pytest.raises(CostLedgerError) as excinfo:
            _build_ledger(
                quantities={**_base_quantities(), "inference": inference},
                denominators=denominators,
            )
        assert excinfo.value.code == "inference_window_mismatch", status


def test_unmeasured_inference_without_counts_under_declared_window_unaffected() -> None:
    # The refusal is for quantities that claim a number: an unmeasured
    # inference with no counts never offered a windowed cost, so it builds.
    inference = Quantity(None, "usd", UNMEASURED, notes=("inference_rows_absent",))
    ledger = _build_ledger(
        quantities={**_base_quantities(), "inference": inference},
        denominators=_denominators(
            queries={"value": 10, "source": "coverage proof", "window": _QUERIES_WINDOW}
        ),
    )
    assert ledger["components"]["inference"]["basis_period"] == "query_window"
    assert "inference" in ledger["totals"]["query_window"]["incomplete_components"]
    assert ledger["per_unit"]["queries"]["reason"] == "components_incomplete"


def test_reader_built_quantity_with_equal_window_still_computes() -> None:
    inference = _windowed_inference(_QUERIES_WINDOW)  # 1.5 in window
    ledger = _build_ledger(
        quantities={**_base_quantities(), "inference": inference},
        denominators=_denominators(
            queries={"value": 10, "source": "coverage proof", "window": _QUERIES_WINDOW}
        ),
    )
    assert ledger["per_unit"]["queries"]["query_window_usd"] == pytest.approx(0.15)
    assert ledger["per_unit"]["queries"]["reason"] is None


def test_matching_window_in_offset_notation_accepted() -> None:
    inference = _windowed_inference(
        {"start": "2026-10-01T00:00:00Z", "end": "2026-10-02T00:00:00Z"}
    )
    assert inference.counts["declared_window"] == {
        "start": "2026-10-01T00:00:00Z",
        "end": "2026-10-02T00:00:00Z",
    }
    denominators = _denominators(
        queries={
            "value": 10,
            "source": "coverage proof",
            "window": {
                "start": "2026-10-01T00:00:00+00:00",
                "end": "2026-10-02T00:00:00+00:00",
            },
        }
    )
    ledger = _build_ledger(
        quantities={**_base_quantities(), "inference": inference},
        denominators=denominators,
    )
    assert ledger["per_unit"]["queries"]["query_window_usd"] == pytest.approx(0.15)


def test_non_utc_window_notation_normalised_for_comparison() -> None:
    inference = _windowed_inference(
        {"start": "2026-10-01T02:00:00+02:00", "end": "2026-10-02T00:00:00Z"}
    )
    assert inference.counts["declared_window"] == {
        "start": "2026-10-01T00:00:00Z",
        "end": "2026-10-02T00:00:00Z",
    }
    ledger = _build_ledger(
        quantities={**_base_quantities(), "inference": inference},
        denominators=_denominators(
            queries={"value": 10, "source": "coverage proof", "window": _QUERIES_WINDOW}
        ),
    )
    assert ledger["per_unit"]["queries"]["query_window_usd"] == pytest.approx(0.15)


# ── 4d. undecodable usage lines demote the inference total (r3 R3) ───────────


def test_undecodable_usage_line_demotes_inference_to_unmeasured() -> None:
    lines = [
        json.dumps({"stage": "fif_capture", "est_cost_usd": 1.5, "ts": "2026-10-01T00:00:00Z"}),
        "{not json",
    ]
    quantity = inference_quantity_from_usage(lines, _ROW_FILTER)
    assert quantity.value is None
    assert quantity.status == UNMEASURED
    assert quantity.notes == ("usage_lines_undecodable",)
    assert quantity.counts["rows_undecodable"] == 1
    assert quantity.counts["rows_matched"] == 1
    ledger = _build_ledger(quantities={**_base_quantities(), "inference": quantity})
    component = ledger["components"]["inference"]
    assert component["cost_status"] == "incomplete"
    assert component["cost_usd"] is None
    assert component["incomplete_reason"] == "usage_lines_undecodable"
    assert "inference" in ledger["totals"]["query_window"]["incomplete_components"]


def test_non_object_usage_line_demotes_inference_to_unmeasured() -> None:
    lines = [
        json.dumps({"stage": "fif_capture", "est_cost_usd": 1.5, "ts": "2026-10-01T00:00:00Z"}),
        "[1]",
    ]
    quantity = inference_quantity_from_usage(lines, _ROW_FILTER)
    assert quantity.value is None
    assert quantity.status == UNMEASURED
    assert quantity.notes == ("usage_lines_undecodable",)
    assert quantity.counts["rows_undecodable"] == 1


def test_undecodable_reason_leads_over_absent_rows() -> None:
    # Precedence: an undecodable line outranks zero matching rows, because
    # the undecodable line could itself have been a matching row.
    quantity = inference_quantity_from_usage(["{not json"], _ROW_FILTER)
    assert quantity.notes == ("usage_lines_undecodable",)
    assert quantity.counts["rows_matched"] == 0


def test_probe_base_reported_undecodable_usage_as_measured() -> None:
    # Probe for the reviewed BASE defect (r3 R3): undecodable lines did not
    # demote the status, so a ledger holding one still reported a measured
    # total (the reviewer's probe read 7.0 measured).
    lines = [
        json.dumps({"stage": "fif_capture", "est_cost_usd": 1.5, "ts": "2026-10-01T00:00:00Z"}),
        "{not json",
    ]
    quantity = inference_quantity_from_usage(lines, _ROW_FILTER)
    assert quantity.status == UNMEASURED
    assert quantity.value is None


# ── 5. operator-burden ledger ────────────────────────────────────────────────


def test_burden_append_read_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "burden.jsonl"
    rows = [
        _burden_row(),
        _burden_row(event_id="evt-2", recorded_at="2026-10-19T02:00:00Z", minutes=15),
    ]
    for row in rows:
        append_burden(path, row)
    assert read_burden(path) == rows


def test_burden_duplicate_event_id_refused(tmp_path: Path) -> None:
    path = tmp_path / "burden.jsonl"
    append_burden(path, _burden_row())
    with pytest.raises(CostLedgerError) as excinfo:
        append_burden(path, _burden_row(recorded_at="2026-10-19T03:00:00Z"))
    assert excinfo.value.code == "burden_duplicate"


def test_burden_clock_regression_refused_on_append(tmp_path: Path) -> None:
    path = tmp_path / "burden.jsonl"
    append_burden(path, _burden_row(recorded_at="2026-10-19T02:00:00Z"))
    with pytest.raises(CostLedgerError) as excinfo:
        append_burden(path, _burden_row(event_id="evt-0", recorded_at="2026-10-19T01:00:00Z"))
    assert excinfo.value.code == "burden_clock_regression"


def test_burden_clock_regression_refused_on_read(tmp_path: Path) -> None:
    path = tmp_path / "burden.jsonl"
    later = _burden_row(recorded_at="2026-10-19T02:00:00Z")
    earlier = _burden_row(event_id="evt-2", recorded_at="2026-10-19T01:00:00Z")
    path.write_text(
        json.dumps(later) + "\n" + json.dumps(earlier) + "\n", encoding="utf-8"
    )
    with pytest.raises(CostLedgerError) as excinfo:
        read_burden(path)
    assert excinfo.value.code == "burden_clock_regression"


def test_burden_equal_timestamps_allowed(tmp_path: Path) -> None:
    path = tmp_path / "burden.jsonl"
    append_burden(path, _burden_row())
    append_burden(path, _burden_row(event_id="evt-2"))  # same recorded_at
    assert len(read_burden(path)) == 2


def test_burden_minutes_bounds_refused(tmp_path: Path) -> None:
    path = tmp_path / "burden.jsonl"
    for minutes in (0, -5, MAX_BURDEN_MINUTES + 1, "30", float("nan")):
        with pytest.raises(CostLedgerError) as excinfo:
            append_burden(path, _burden_row(minutes=minutes))
        assert excinfo.value.code == "burden_shape", minutes
    append_burden(path, _burden_row(minutes=MAX_BURDEN_MINUTES))  # boundary is legal
    assert read_burden(path)[0]["minutes"] == MAX_BURDEN_MINUTES


def test_burden_unknown_role_or_kind_refused(tmp_path: Path) -> None:
    path = tmp_path / "burden.jsonl"
    with pytest.raises(CostLedgerError) as excinfo:
        append_burden(path, _burden_row(actor_role="intern"))
    assert excinfo.value.code == "burden_shape"
    with pytest.raises(CostLedgerError) as excinfo:
        append_burden(path, _burden_row(act_kind="nap"))
    assert excinfo.value.code == "burden_shape"


def test_burden_naive_recorded_at_refused(tmp_path: Path) -> None:
    path = tmp_path / "burden.jsonl"
    for recorded_at in ("2026-10-19T01:00:00", "2026-10-19T01:00:00+00:00", "2026-10-19 01:00:00Z"):
        with pytest.raises(CostLedgerError) as excinfo:
            append_burden(path, _burden_row(recorded_at=recorded_at))
        assert excinfo.value.code == "burden_shape", recorded_at


def test_burden_append_only_extends(tmp_path: Path) -> None:
    path = tmp_path / "burden.jsonl"
    append_burden(path, _burden_row())
    before = path.read_bytes()
    append_burden(path, _burden_row(event_id="evt-2", recorded_at="2026-10-19T02:00:00Z"))
    after = path.read_bytes()
    assert after.startswith(before)
    assert after == before + json.dumps(
        _burden_row(event_id="evt-2", recorded_at="2026-10-19T02:00:00Z"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"


def test_missing_burden_file_is_unmeasured_never_zero() -> None:
    quantity = review_quantity_from_burden_rows(None)
    assert quantity.value is None
    assert quantity.status == UNMEASURED
    assert "no_burden_file" in quantity.notes
    assert "burden_ledger_empty" in quantity.notes
    ledger = _build_ledger(
        quantities={**_base_quantities(), "review": quantity}, burden_rows=None
    )
    assert ledger["components"]["review"]["incomplete_reason"] == "burden_ledger_empty"
    assert "review" in ledger["totals"]["one_time"]["incomplete_components"]


def test_empty_burden_ledger_is_unmeasured_never_zero() -> None:
    quantity = review_quantity_from_burden_rows([])
    assert quantity.value is None
    assert quantity.status == UNMEASURED
    assert "burden_ledger_empty" in quantity.notes
    assert quantity.counts["events"] == 0
    ledger = _build_ledger(
        quantities={**_base_quantities(), "review": quantity}, burden_rows=[]
    )
    burden = ledger["operator_burden"]
    assert burden["status"] == UNMEASURED
    assert burden["minutes_total"] is None
    assert burden["events"] == 0
    assert burden["notes"] == ["burden_ledger_empty"]
    review = ledger["components"]["review"]
    assert review["quantity_value"] is None
    assert review["incomplete_reason"] == "burden_ledger_empty"
    assert "review" in ledger["totals"]["one_time"]["incomplete_components"]


def test_burden_entries_summing_to_zero_stay_measured_zero() -> None:
    # read_burden refuses minutes <= 0, so such rows cannot come from a ledger
    # file; the guard pinned here is that emptiness demotes, a zero sum does not.
    rows = [_burden_row(minutes=0.0), _burden_row(event_id="evt-2", minutes=0.0)]
    quantity = review_quantity_from_burden_rows(rows)
    assert quantity.value == 0.0
    assert quantity.status == MEASURED
    assert quantity.counts["events"] == 2


def test_naive_built_at_refused() -> None:
    with pytest.raises(CostLedgerError) as excinfo:
        build_cost_ledger(
            rates=load_rates(RATES_PATH),
            quantities=_base_quantities(),
            denominators=_denominators(),
            burden_rows=None,
            built_at=datetime(2026, 10, 19),
        )
    assert excinfo.value.code == "naive_clock"


# ── 6. ledger build ──────────────────────────────────────────────────────────


def test_unmeasured_parse_rate_makes_parse_incomplete() -> None:
    ledger = _build_ledger()
    assert ledger["components"]["parse"]["rate_status"] == "unmeasured"
    assert ledger["components"]["parse"]["cost_status"] == "incomplete"
    assert ledger["components"]["parse"]["cost_usd"] is None
    assert ledger["totals"]["one_time"]["complete"] is False
    assert "parse" in ledger["totals"]["one_time"]["incomplete_components"]
    assert "review" in ledger["totals"]["one_time"]["incomplete_components"]
    assert ledger["complete"] is False


def test_unverified_storage_rate_is_declared_unverified() -> None:
    ledger = _build_ledger()
    storage = ledger["components"]["storage"]
    assert storage["cost_status"] == "declared_unverified"
    assert storage["cost_usd"] == pytest.approx(2.0 * 0.015)
    # declared_unverified is not incomplete: the per-month period stands.
    assert ledger["totals"]["per_month"]["complete"] is True
    assert ledger["totals"]["per_month"]["incomplete_components"] == []
    assert ledger["totals"]["per_month"]["known_usd"] == pytest.approx(0.03)


def test_estimated_storage_lower_bound_makes_per_month_incomplete() -> None:
    csv_text = _packages_csv([{}, {"label_bytes": "False"}])
    storage = storage_quantity_from_deep_packages(csv_text)
    assert storage.status == ESTIMATED
    quantities = _base_quantities()
    quantities["storage"] = storage
    ledger = _build_ledger(quantities=quantities)
    entry = ledger["components"]["storage"]
    assert entry["incomplete_reason"] == "storage_lower_bound"
    assert "storage" in ledger["totals"]["per_month"]["incomplete_components"]
    assert ledger["totals"]["per_month"]["complete"] is False
    # The numeric total is still reported, labelled as a lower bound.
    assert ledger["totals"]["per_month"]["known_usd"] == pytest.approx(
        storage.value * 0.015
    )
    assert ledger["complete"] is False


def test_measured_storage_keeps_per_month_complete() -> None:
    ledger = _build_ledger()
    assert ledger["components"]["storage"]["incomplete_reason"] is None
    assert ledger["totals"]["per_month"]["complete"] is True
    assert "storage" not in ledger["totals"]["per_month"]["incomplete_components"]


def test_no_incomplete_component_ever_has_cost_usd() -> None:
    ledger = _build_ledger()
    for component, entry in ledger["components"].items():
        if entry["cost_status"] == "incomplete":
            assert entry["cost_usd"] is None, component


def test_measured_and_declared_cost_statuses(tmp_path: Path) -> None:
    ledger = _build_ledger()
    assert ledger["components"]["source"]["cost_status"] == "measured"
    assert ledger["components"]["inference"]["cost_status"] == "measured"

    doc = _rates_doc()
    for entry in doc["rates"]:
        if entry["component"] == "storage":
            entry["verified"] = True
    rates = load_rates(_write_rates(tmp_path, doc))
    quantities = _base_quantities()
    quantities["storage"] = Quantity(
        2.0, "gb", ESTIMATED, counts={"six_role_bytes": 2_000_000_000}
    )
    ledger = _build_ledger(quantities=quantities, rates=rates)
    assert ledger["components"]["storage"]["cost_status"] == "declared"
    assert ledger["components"]["storage"]["cost_usd"] == pytest.approx(0.03)


def test_operator_burden_totals_reported_without_usd_rate() -> None:
    rows = [
        _burden_row(minutes=30),
        _burden_row(event_id="evt-2", recorded_at="2026-10-19T02:00:00Z", minutes=15),
        _burden_row(
            event_id="evt-3",
            recorded_at="2026-10-19T03:00:00Z",
            minutes=5,
            actor_role="operator",
            act_kind="repair",
        ),
    ]
    quantities = _base_quantities()
    quantities["review"] = review_quantity_from_burden_rows(rows)
    ledger = _build_ledger(quantities=quantities, burden_rows=rows)
    burden = ledger["operator_burden"]
    assert burden["status"] == MEASURED
    assert burden["minutes_total"] == 50
    assert burden["events"] == 3
    assert burden["by_act_kind"] == {"review": 45, "repair": 5}
    assert burden["by_actor_role"] == {"seat": 45, "operator": 5}
    assert burden["window"] == {
        "first": "2026-10-19T01:00:00Z",
        "last": "2026-10-19T03:00:00Z",
    }
    # The review USD rate is unmeasured, so review cost stays incomplete while
    # the burden minutes are still reported.
    assert ledger["components"]["review"]["cost_usd"] is None
    assert ledger["components"]["review"]["cost_status"] == "incomplete"
    assert ledger["components"]["review"]["quantity_value"] == 50


def test_missing_burden_file_marks_burden_unmeasured() -> None:
    ledger = _build_ledger(burden_rows=None)
    assert ledger["operator_burden"]["status"] == UNMEASURED
    assert ledger["operator_burden"]["minutes_total"] is None
    assert ledger["operator_burden"]["events"] == 0


def test_design_comparison_uses_c2_freeze_constants() -> None:
    ledger = _build_ledger()
    design = ledger["design_comparison"]
    assert design["deep_fleet_design_bytes"] == 2_708_491_000
    assert design["deep_six_role_bytes_measured"] == 2_000_000_000
    assert design["deep_six_role_ratio_to_design"] == pytest.approx(
        2_000_000_000 / 2_708_491_000
    )
    assert design["cold_deep_gets_design"] == 7250
    assert design["cold_deep_gets_receipt_estimate"] is None


# ── 7. per-unit ──────────────────────────────────────────────────────────────


def test_per_unit_null_denominator_is_denominator_unmeasured() -> None:
    ledger = _build_ledger(denominators=_denominators())
    for key in ("qualified_filings", "qualified_issuers_deep", "qualified_issuers_core"):
        entry = ledger["per_unit"][key]
        assert entry["one_time_usd"] is None
        assert entry["per_month_usd"] is None
        assert entry["reason"] == "denominator_unmeasured"
        assert entry["complete"] is False
    # The queries entry declares no window either, and the absent-window
    # refusal leads: cost-per-query is refused before any denominator check.
    queries = ledger["per_unit"]["queries"]
    assert queries["one_time_usd"] is None
    assert queries["per_month_usd"] is None
    assert queries["reason"] == "queries_window_absent"
    assert queries["complete"] is False


def test_per_unit_zero_denominator_is_denominator_zero() -> None:
    denominators = _denominators(
        qualified_filings={"value": 0, "source": "coverage proof"},
    )
    ledger = _build_ledger(denominators=denominators)
    entry = ledger["per_unit"]["qualified_filings"]
    assert entry["one_time_usd"] is None
    assert entry["per_month_usd"] is None
    assert entry["reason"] == "denominator_zero"


def test_per_unit_positive_denominator_with_incomplete_components() -> None:
    denominators = _denominators(
        qualified_filings={"value": 10, "source": "coverage proof"},
    )
    ledger = _build_ledger(denominators=denominators)
    entry = ledger["per_unit"]["qualified_filings"]
    # one_time holds only source+licence+parse+review (r3 R4): their known
    # costs are the declared 0.0 rates, parse and review stay unmeasured, so
    # the quotient prints but is never a full cost.
    assert entry["one_time_usd"] == pytest.approx(0.0)
    assert entry["per_month_usd"] == pytest.approx(0.003)
    assert entry["query_window_usd"] is None
    assert entry["complete"] is False
    assert entry["reason"] == "components_incomplete"


# ── 7b. windowed inference is its own basis group (r3 R4) ────────────────────


def test_totals_carry_three_basis_groups() -> None:
    ledger = _build_ledger()
    assert set(ledger["totals"]) == {"one_time", "per_month", "query_window"}
    # No queries window is declared here, so the measured inference 2.5 is a
    # lifetime total: labelled undeclared_window, excluded from the
    # query_window group, which is then incomplete naming inference (r4 N3).
    assert ledger["totals"]["query_window"]["known_usd"] is None
    assert ledger["totals"]["query_window"]["complete"] is False
    assert ledger["totals"]["query_window"]["incomplete_components"] == ["inference"]
    assert ledger["totals"]["one_time"]["known_usd"] == pytest.approx(0.0)
    inference = ledger["components"]["inference"]
    assert inference["basis_period"] == "undeclared_window"
    assert inference["rate_basis_period"] == "one_time"
    for component in ("source", "licence", "parse", "review", "storage"):
        entry = ledger["components"][component]
        assert entry["rate_basis_period"] == entry["basis_period"], component
    assert ledger["components"]["storage"]["basis_period"] == "per_month"
    assert ledger["components"]["source"]["basis_period"] == "one_time"


def test_no_window_inference_is_undeclared_window_lifetime_total() -> None:
    # r4 N3: with no declared queries window the inference figure is a
    # lifetime total — labelled undeclared_window, excluded from the
    # query_window group (which is then incomplete), while the per-query
    # quotient is refused with queries_window_absent.
    ledger = _build_ledger()
    inference = ledger["components"]["inference"]
    assert inference["basis_period"] == "undeclared_window"
    assert inference["rate_basis_period"] == "one_time"
    assert inference["cost_usd"] == pytest.approx(2.5)  # still on the component
    assert ledger["totals"]["query_window"]["known_usd"] is None
    assert ledger["totals"]["query_window"]["complete"] is False
    assert ledger["totals"]["query_window"]["incomplete_components"] == ["inference"]
    assert ledger["per_unit"]["queries"]["reason"] == "queries_window_absent"


def test_declared_window_inference_keeps_query_window_label() -> None:
    # r4 N3: the declared-window case is unchanged — the label stays
    # query_window and the windowed total still feeds the group.
    inference = _windowed_inference(_QUERIES_WINDOW)
    ledger = _build_ledger(
        quantities={**_base_quantities(), "inference": inference},
        denominators=_denominators(
            queries={"value": 10, "source": "coverage proof", "window": _QUERIES_WINDOW}
        ),
    )
    assert ledger["components"]["inference"]["basis_period"] == "query_window"
    assert ledger["totals"]["query_window"]["known_usd"] == pytest.approx(1.5)
    assert ledger["totals"]["query_window"]["complete"] is True
    assert ledger["per_unit"]["queries"]["query_window_usd"] == pytest.approx(0.15)


def test_per_issuer_quotient_excludes_measured_inference() -> None:
    denominators = _denominators(
        qualified_issuers_deep={"value": 10, "source": "coverage proof"}
    )
    ledger = _build_ledger(denominators=denominators)
    entry = ledger["per_unit"]["qualified_issuers_deep"]
    # The one_time + per_month numerator is the declared 0.0 source and
    # licence rates plus per-month storage; a measured inference cost of 2.5
    # never leaks into the quotient.
    assert entry["one_time_usd"] == pytest.approx(0.0)
    assert entry["per_month_usd"] == pytest.approx(0.003)
    assert entry["query_window_usd"] is None
    assert entry["basis"] == ["one_time", "per_month"]
    assert entry["components"] == ["licence", "parse", "review", "source", "storage"]
    assert "inference" not in entry["components"]


def test_per_query_quotient_is_window_total_over_queries() -> None:
    inference = _windowed_inference(_QUERIES_WINDOW)  # 1.5 in window
    ledger = _build_ledger(
        quantities={**_base_quantities(), "inference": inference},
        denominators=_denominators(
            queries={"value": 10, "source": "coverage proof", "window": _QUERIES_WINDOW}
        ),
    )
    entry = ledger["per_unit"]["queries"]
    assert entry["query_window_usd"] == pytest.approx(0.15)
    assert entry["one_time_usd"] is None
    assert entry["per_month_usd"] is None
    assert entry["basis"] == ["query_window"]
    assert entry["components"] == ["inference"]
    assert entry["complete"] is True
    assert entry["reason"] is None


def test_top_level_complete_false_when_only_query_window_incomplete(
    tmp_path: Path,
) -> None:
    doc = _rates_doc()
    for entry in doc["rates"]:
        if entry["component"] in ("parse", "review"):
            entry["status"] = "declared_rate"
            entry["usd_per_unit"] = 0.0
    rates = load_rates(_write_rates(tmp_path, doc))
    quantities = {
        "source": Quantity(10.0, "get", MEASURED),
        "licence": Quantity(1000.0, "issuer", MEASURED),
        "storage": Quantity(2.0, "gb", MEASURED),
        "parse": Quantity(60.0, "cpu_second", MEASURED),
        "inference": Quantity(
            None, "usd", UNMEASURED, notes=("inference_rows_absent",)
        ),
        "review": Quantity(30.0, "minute", MEASURED),
    }
    ledger = _build_ledger(quantities=quantities, rates=rates)
    assert ledger["totals"]["one_time"]["complete"] is True
    assert ledger["totals"]["per_month"]["complete"] is True
    assert ledger["totals"]["query_window"]["complete"] is False
    assert ledger["totals"]["query_window"]["incomplete_components"] == ["inference"]
    assert ledger["complete"] is False


# ── 7c. the incomplete query-window total names its reason (r5) ──────────────


def _total_line(text: str, period: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"total {period}:"):
            return line
    raise AssertionError(f"no total line for {period}")


def test_no_window_query_window_total_carries_queries_window_absent() -> None:
    # r5: with no declared queries window a measured inference total moves
    # to undeclared_window; the incomplete query-window total must say why.
    ledger = _build_ledger()
    total = ledger["totals"]["query_window"]
    assert total["known_usd"] is None
    assert total["complete"] is False
    assert total["incomplete_components"] == ["inference"]
    assert total["reason"] == "queries_window_absent"
    # The other period totals never carry a reason.
    assert ledger["totals"]["one_time"]["reason"] is None
    assert ledger["totals"]["per_month"]["reason"] is None
    # The moved component itself is measured with a known cost: its cost is
    # known, just not attributable to a window.
    inference = ledger["components"]["inference"]
    assert inference["basis_period"] == "undeclared_window"
    assert inference["cost_status"] == "measured"
    assert inference["incomplete_reason"] is None
    # per_unit.queries is unchanged by r5.
    queries = ledger["per_unit"]["queries"]
    assert queries["reason"] == "queries_window_absent"
    assert queries["components"] == []
    # And the printed total line shows the reason, while the other totals'
    # lines carry no reason token at all.
    text = render_print(ledger)
    assert _total_line(text, "query_window").endswith("reason=queries_window_absent")
    assert "reason=" not in _total_line(text, "one_time")
    assert "reason=" not in _total_line(text, "per_month")


def test_declared_window_query_window_total_reason_is_null() -> None:
    inference = Quantity(2.5, "usd", MEASURED, counts={"declared_window": _QUERIES_WINDOW})
    ledger = _build_ledger(
        quantities={**_base_quantities(), "inference": inference},
        denominators=_denominators(
            queries={"value": 10, "source": "coverage proof", "window": _QUERIES_WINDOW}
        ),
    )
    assert ledger["totals"]["query_window"]["reason"] is None
    assert ledger["totals"]["one_time"]["reason"] is None
    assert ledger["totals"]["per_month"]["reason"] is None
    assert _total_line(render_print(ledger), "query_window").endswith("reason=none")


def test_unmeasured_inference_without_window_carries_no_total_reason() -> None:
    # r5: an UNMEASURED inference under no declared window is the ordinary
    # unmeasured-component fact, not a windowing one — the total carries no
    # reason even though it is still incomplete.
    inference = Quantity(None, "usd", UNMEASURED, notes=("inference_rows_absent",))
    ledger = _build_ledger(quantities={**_base_quantities(), "inference": inference})
    assert ledger["totals"]["query_window"]["reason"] is None
    assert ledger["totals"]["query_window"]["incomplete_components"] == ["inference"]
    assert _total_line(render_print(ledger), "query_window").endswith("reason=none")


def test_period_total_reasons_conform_to_contract() -> None:
    # The reason field is part of the period_totals contract: every ledger
    # shape — no-window, declared-window, unmeasured inference — validates.
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    no_window = _build_ledger()
    declared = _build_ledger(
        quantities={**_base_quantities(), "inference": _windowed_inference(_QUERIES_WINDOW)},
        denominators=_denominators(
            queries={"value": 10, "source": "coverage proof", "window": _QUERIES_WINDOW}
        ),
    )
    unmeasured = _build_ledger(
        quantities={
            **_base_quantities(),
            "inference": Quantity(None, "usd", UNMEASURED, notes=("inference_rows_absent",)),
        }
    )
    for ledger in (no_window, declared, unmeasured):
        assert list(validator.iter_errors(ledger)) == []


# ── 8. render ────────────────────────────────────────────────────────────────


def test_render_print_never_prints_zero_for_unmeasured() -> None:
    ledger = _build_ledger()
    text = render_print(ledger)
    lines = {
        line.split()[1].rstrip(":"): line
        for line in text.splitlines()
        if line.startswith("component ")
    }
    for component in ("parse", "review"):
        line = lines[component]
        assert "UNMEASURED" in line or "INCOMPLETE" in line
        assert "cost_usd=0" not in line
        assert "qty=0" not in line
    # Measured zeros (source GETs are genuinely 0-cost declared) still print.
    assert "cost_usd=0.000000" in lines["source"]
    assert "denominator=UNMEASURED" in text
    assert "minutes_total=UNMEASURED" in text
    # The query_window basis group prints its own total and quotient column.
    assert "total query_window:" in text
    assert "query_window_usd=" in text


def _per_unit_line(text: str, key: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"per_unit {key}:"):
            return line
    raise AssertionError(f"no per_unit line for {key}")


def test_render_print_per_unit_shows_only_basis_groups() -> None:
    # r4 N2: a group the quotient never divides is not an UNMEASURED
    # measurement.  The per-issuer line carries no query_window token and
    # the per-query line no one_time / per_month tokens; the JSON output is
    # unchanged (a non-applicable group stays null there).
    text = render_print(_build_ledger())
    per_issuer = _per_unit_line(text, "qualified_issuers_deep")
    assert "query_window_usd" not in per_issuer
    assert "one_time_usd=" in per_issuer
    assert "per_month_usd=" in per_issuer
    per_query = _per_unit_line(text, "queries")
    assert "one_time_usd" not in per_query
    assert "per_month_usd" not in per_query
    assert "query_window_usd=" in per_query


def test_render_print_unmeasured_applicable_group_still_prints() -> None:
    # UNMEASURED still prints for a group in the basis that is not measured:
    # here the windowed inference is unmeasured, so the per-query line says so.
    inference = Quantity(None, "usd", UNMEASURED, notes=("inference_rows_absent",))
    ledger = _build_ledger(
        quantities={**_base_quantities(), "inference": inference},
        denominators=_denominators(
            queries={"value": 10, "source": "coverage proof", "window": _QUERIES_WINDOW}
        ),
    )
    text = render_print(ledger)
    per_query = _per_unit_line(text, "queries")
    assert "query_window_usd=UNMEASURED" in per_query
    per_issuer = _per_unit_line(text, "qualified_issuers_deep")
    assert "one_time_usd=" in per_issuer  # applicable groups keep their tokens


# ── 9. contract ──────────────────────────────────────────────────────────────


def test_ledger_conforms_to_contract() -> None:
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    rows = [
        _burden_row(minutes=30),
        _burden_row(event_id="evt-2", recorded_at="2026-10-19T02:00:00Z", minutes=15),
    ]
    quantities = _base_quantities()
    quantities["review"] = review_quantity_from_burden_rows(rows)
    ledger = _build_ledger(quantities=quantities, burden_rows=rows)
    errors = list(validator.iter_errors(ledger))
    assert errors == []
    minimal = _build_ledger()
    assert list(validator.iter_errors(minimal)) == []


def test_windowed_and_undecodable_ledgers_conform_to_contract() -> None:
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    windowed = _build_ledger(
        quantities={**_base_quantities(), "inference": _windowed_inference(_QUERIES_WINDOW)},
        denominators=_denominators(
            queries={"value": 10, "source": "coverage proof", "window": _QUERIES_WINDOW}
        ),
    )
    assert list(validator.iter_errors(windowed)) == []
    undecodable = _build_ledger(
        quantities={
            **_base_quantities(),
            "inference": inference_quantity_from_usage(
                [
                    json.dumps({"stage": "fif_capture", "est_cost_usd": 1.5}),
                    "{not json",
                ],
                _ROW_FILTER,
            ),
        }
    )
    assert list(validator.iter_errors(undecodable)) == []
    outside_only = _build_ledger(
        quantities={
            **_base_quantities(),
            "inference": inference_quantity_from_usage(
                [json.dumps({"stage": "fif_capture", "est_cost_usd": 5.0, "ts": "2026-09-01T00:00:00Z"})],
                _ROW_FILTER,
                window=_QUERIES_WINDOW,
            ),
        },
        denominators=_denominators(
            queries={"value": 10, "source": "coverage proof", "window": _QUERIES_WINDOW}
        ),
    )
    assert list(validator.iter_errors(outside_only)) == []


# ── 10. CLI ──────────────────────────────────────────────────────────────────


def _cli_inputs(tmp_path: Path) -> dict:
    receipt = tmp_path / "economics.json"
    receipt.write_text(json.dumps(_warm_receipt()), encoding="utf-8")
    packages = tmp_path / "deep_packages.csv"
    packages.write_text(_packages_csv([{}, {"label_bytes": "False"}]), encoding="utf-8")
    usage = tmp_path / "usage.jsonl"
    usage.write_text(
        json.dumps({"stage": "altdata_brain", "lane": "unknown", "est_cost_usd": 9.0})
        + "\n"
        + json.dumps({"stage": "fif_capture", "lane": "unknown", "est_cost_usd": 1.25})
        + "\n",
        encoding="utf-8",
    )
    denominators = tmp_path / "denominators.json"
    denominators.write_text(json.dumps(_denominators()), encoding="utf-8")
    return {
        "economics": str(receipt),
        "packages": str(packages),
        "usage": str(usage),
        "denominators": str(denominators),
    }


def test_cli_build_exit_zero_print_goes_to_stderr(tmp_path: Path) -> None:
    inputs = _cli_inputs(tmp_path)
    out = tmp_path / "ledger.json"
    result = _run_cli(
        "build",
        "--rates", str(RATES_PATH),
        "--built-at", "2026-10-19T00:00:00Z",
        "--economics", inputs["economics"],
        "--deep-packages", inputs["packages"],
        "--ai-usage", inputs["usage"],
        "--licence-issuers", "1000",
        "--denominators", inputs["denominators"],
        "--out", str(out),
        "--print",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert "component parse: cost_usd=UNMEASURED" in result.stderr
    assert "operator_burden: status=unmeasured" in result.stderr
    ledger = json.loads(out.read_text(encoding="utf-8"))
    assert ledger["complete"] is False
    assert ledger["components"]["licence"]["quantity_value"] == 1000
    assert ledger["components"]["inference"]["counts"]["rows_matched"] == 1
    assert ledger["components"]["inference"]["cost_usd"] == pytest.approx(1.25)
    assert ledger["components"]["review"]["cost_status"] == "incomplete"


def test_cli_refusal_exits_two(tmp_path: Path) -> None:
    bad = tmp_path / "bad_rates.json"
    bad.write_text(json.dumps({"schema": "nope"}), encoding="utf-8")
    result = _run_cli(
        "build", "--rates", str(bad), "--built-at", "2026-10-19T00:00:00Z"
    )
    assert result.returncode == 2
    assert "refusal rates_shape" in result.stderr

    result = _run_cli(
        "build",
        "--rates", str(RATES_PATH),
        "--built-at", "2026-10-19T00:00:00",
        "--out", str(tmp_path / "x.json"),
    )
    assert result.returncode == 2
    assert not (tmp_path / "x.json").exists()


def test_cli_consistent_windows_exit_zero(tmp_path: Path) -> None:
    usage = tmp_path / "usage.jsonl"
    usage.write_text(
        json.dumps(
            {"stage": "fif_capture", "lane": "x", "est_cost_usd": 2.0, "ts": "2026-10-01T06:00:00Z"}
        )
        + "\n",
        encoding="utf-8",
    )
    denominators = tmp_path / "denominators.json"
    denominators.write_text(
        json.dumps(
            _denominators(
                queries={"value": 4, "source": "coverage proof", "window": _QUERIES_WINDOW}
            )
        ),
        encoding="utf-8",
    )
    out = tmp_path / "ledger.json"
    result = _run_cli(
        "build",
        "--rates", str(RATES_PATH),
        "--built-at", "2026-10-19T00:00:00Z",
        "--ai-usage", str(usage),
        "--denominators", str(denominators),
        "--out", str(out),
        "--print",
    )
    # The CLI passes the queries window into the inference read, so a
    # consistent input must not trip inference_window_mismatch.
    assert result.returncode == 0, result.stderr
    assert "total query_window:" in result.stderr
    assert "query_window_usd=" in result.stderr
    ledger = json.loads(out.read_text(encoding="utf-8"))
    assert ledger["per_unit"]["queries"]["query_window_usd"] == pytest.approx(0.5)
    assert ledger["per_unit"]["queries"]["one_time_usd"] is None


def test_cli_inverted_window_exits_two(tmp_path: Path) -> None:
    # The CLI threads the queries window into the inference read, so its own
    # inputs can never mismatch; the CostLedgerError -> exit 2 mapping is
    # pinned here through the window refusal the CLI can reach.
    usage = tmp_path / "usage.jsonl"
    usage.write_text(
        json.dumps(
            {"stage": "fif_capture", "lane": "x", "est_cost_usd": 2.0, "ts": "2026-10-01T06:00:00Z"}
        )
        + "\n",
        encoding="utf-8",
    )
    denominators = tmp_path / "denominators.json"
    denominators.write_text(
        json.dumps(
            _denominators(
                queries={
                    "value": 4,
                    "source": "coverage proof",
                    "window": {"start": "2026-10-02T00:00:00Z", "end": "2026-10-01T00:00:00Z"},
                }
            )
        ),
        encoding="utf-8",
    )
    result = _run_cli(
        "build",
        "--rates", str(RATES_PATH),
        "--built-at", "2026-10-19T00:00:00Z",
        "--ai-usage", str(usage),
        "--denominators", str(denominators),
    )
    assert result.returncode == 2
    assert "window_inverted" in result.stderr


def test_cli_require_complete_exits_five(tmp_path: Path) -> None:
    inputs = _cli_inputs(tmp_path)
    result = _run_cli(
        "build",
        "--rates", str(RATES_PATH),
        "--built-at", "2026-10-19T00:00:00Z",
        "--economics", inputs["economics"],
        "--deep-packages", inputs["packages"],
        "--denominators", inputs["denominators"],
        "--out", str(tmp_path / "ledger.json"),
        "--require-complete",
    )
    assert result.returncode == 5
    assert "not complete" in result.stderr


def test_cli_burden_append_roundtrip(tmp_path: Path) -> None:
    burden = tmp_path / "burden.jsonl"
    row = _burden_row(event_id="evt-cli-1", minutes=20)
    result = _run_cli(
        "burden-append", "--burden", str(burden), "--row-json", json.dumps(row)
    )
    assert result.returncode == 0, result.stderr
    assert "evt-cli-1" in result.stdout
    assert read_burden(burden) == [row]


# ── 11. source scans ─────────────────────────────────────────────────────────


def test_cost_ledger_module_has_no_clock_network_or_write_mode() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    for token in ("datetime.now", "time.time", "utcnow", "urllib", "requests", "socket", "boto"):
        assert token not in source, token
    assert re.search(r'''open\([^)]*["']w["']''', source) is None


def test_kernel_modules_import_no_model_sdk_or_cost_writer() -> None:
    pattern = re.compile(r"^\s*(?:import|from)\s+(?:openai|anthropic|lib\.ai_costs)\b", re.M)
    for module_path in sorted(KERNEL_DIR.glob("*.py")):
        assert not pattern.search(module_path.read_text(encoding="utf-8")), module_path
