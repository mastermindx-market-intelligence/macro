"""Specialist pack producer framework + PK06/PK01 producers over the AAPL 10-K fixture.

Every count asserted here was verified against the fixture's facts through
the raw ledger (never by reading the filing HTML): the fixture tags the split
and total lease liabilities, the ROU assets, operating/variable lease cost,
operating lease payments, the operating undiscounted ladder and its imputed
interest; finance amortization/interest, short-term cost, total lease cost,
weighted-average term and discount rate are absent standard facts. For PK01
the fixture tags the six-step maturity ladder, the total and per-instrument
carrying amounts, the level-2 fair value, the debt split, cash, marketable
securities (current), current assets and current liabilities; commercial
paper (us-gaap:CommercialPaper) is not a core short_term_debt alias, so
short_term_debt is a typed absence, and the revolver-capacity and combined-
debt concepts are absent standard facts.
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

from engine.fundamental_forensics.specialist_packs import (
    PACK_PRODUCERS,
    PackInput,
    SpecialistPackError,
    produce_pack,
    registered_pack_ids,
)
from engine.fundamental_forensics.specialist_packs import base as pack_base
from engine.fundamental_forensics.specialist_packs import pk06_leases
from engine.fundamental_forensics import specialist_pack_contract as contract
from engine.fundamental_forensics.statement_graph import load_golden_aapl_package

ROOT = Path(__file__).resolve().parents[1]
ACCESSION = "0000320193-25-000079"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "fundamental_forensics" / "aapl_10k_2025"
MANIFEST = json.loads((FIXTURE_DIR / "package_manifest.json").read_text("utf-8"))
ENTITY = {
    "entity_id": MANIFEST["entity_id"],
    "cik": MANIFEST["cik"],
    "ticker": "AAPL",
    "name": MANIFEST["legal_name"],
    "identity_basis": "golden_filing_package_fixture_v1",
    "source_entity_id": MANIFEST["cik"],
}
# The packet $defs.query requires requested_metrics minItems 1, so the empty
# list the lane brief sketched cannot enter an envelope; one metric is carried.
QUERY = {
    "policy": "as_reported",
    "source_event_cutoff": "2025-12-31T23:59:59Z",
    "system_recorded_cutoff": "2026-08-05T12:00:02Z",
    "requested_metrics": ["leases"],
    "requested_periods": ["FY2025"],
    "evaluation_mode": "historical_replay",
}
# Fixture-verified: value strings are the facts' own scale (USD units).
VALUED = {
    "rou_assets_operating": "11205000000",
    "rou_assets_finance": "1033000000",
    "operating_lease_liability_current": "1579000000",
    "operating_lease_liability_noncurrent": "10911000000",
    "finance_lease_liability_current": "538000000",
    "finance_lease_liability_noncurrent": "692000000",
    "lease_cost_operating": "2100000000",
    "lease_cost_variable": "16100000000",
    "lease_cash_payments": "2100000000",
    "undiscounted_payments_total": "14725000000",
    "undiscounted_payments_by_year": "1967000000",
    "offbalance_purchase_commitments": "13308000000",
    "operating_lease_liability_total": "12490000000",
    "finance_lease_liability_total": "1230000000",
    "lease_imputed_interest": "2235000000",
}
MISSING_REASONS = {
    "lease_cost_finance_amortization": (
        "missing_standard_fact:us-gaap:FinanceLeaseRightOfUseAssetAmortization"
    ),
    "lease_cost_finance_interest": (
        "missing_standard_fact:us-gaap:FinanceLeaseInterestExpense"
    ),
    "lease_cost_short_term": "missing_standard_fact:us-gaap:ShortTermLeaseCost",
    "lease_cost_total": "missing_standard_fact:us-gaap:LeaseCost",
    "weighted_average_remaining_term": (
        "missing_standard_fact:us-gaap:OperatingLeaseWeightedAverageRemainingLeaseTerm1"
    ),
    "weighted_average_discount_rate": (
        "missing_standard_fact:us-gaap:OperatingLeaseWeightedAverageDiscountRatePercent"
    ),
}


def _pack_input(**overrides) -> PackInput:
    defaults = dict(
        packages=(load_golden_aapl_package(ROOT, accession=ACCESSION),),
        entity=ENTITY,
        query=QUERY,
        issuer_sic="3571",
        sic_source="sec_submissions",
    )
    defaults.update(overrides)
    return PackInput(**defaults)


@pytest.fixture(scope="module")
def result() -> dict:
    return produce_pack("PK06", _pack_input())


@pytest.fixture(scope="module")
def ledger():
    from engine.fundamental_forensics import ixbrl_raw_ledger

    packages = (load_golden_aapl_package(ROOT, accession=ACCESSION),)
    ledger, _metadata, _report = ixbrl_raw_ledger.parse_and_convert_golden_packages(
        packages
    )
    return ledger


def _row(result: dict, field_id: str) -> dict:
    matches = [row for row in result["fields"] if row["field_id"] == field_id]
    assert len(matches) == 1
    return matches[0]


def _check(result: dict, check_id: str) -> dict:
    matches = [row for row in result["checks"] if row["check_id"] == check_id]
    assert len(matches) == 1
    return matches[0]


# --- PK01: debt, liquidity, covenants and maturities ------------------------
#
# Fixture-verified values (raw ledger, USD units at 2025-09-27).

PK01_QUERY = {**QUERY, "requested_metrics": ["debt"]}
# A.7: sha256 of the canonical JSON bytes of the PK06 envelope over this
# fixture under the module's own inputs; PK01 edits must not move it.
# Re-pinned by the F1-F10 framework repair (R-F1/R-F4/R-F10 receipt
# additions plus the R-F10 weighted_average_remaining_term limitation are
# the only changes vs the pre-repair envelope).
PK06_ENVELOPE_SHA256 = (
    "64b2d42f2148bdf4c9aaf69aae562e53aae26d54bc9386264ce485f80a322c05"
)
PK01_LADDER = {
    "debt_maturity_y1": "12393000000",
    "debt_maturity_y2": "10078000000",
    "debt_maturity_y3": "9300000000",
    "debt_maturity_y4": "5235000000",
    "debt_maturity_y5": "4972000000",
    "debt_maturity_after_5y": "49303000000",
}
INSTRUMENT_ISSUER_MEMBER = "{http://www.apple.com/20250927}A20132023DebtIssuancesMember"
INSTRUMENT_2025_MEMBER = "{http://www.apple.com/20250927}A2025DebtIssuanceMember"
FIXED_RATE_NOTES_MEMBER = "{http://www.apple.com/20250927}FixedRateNotesMember"


def _pk01_input(**overrides) -> PackInput:
    defaults = dict(
        packages=(load_golden_aapl_package(ROOT, accession=ACCESSION),),
        entity=ENTITY,
        query=PK01_QUERY,
        issuer_sic="3571",
        sic_source="sec_submissions",
    )
    defaults.update(overrides)
    return PackInput(**defaults)


@pytest.fixture(scope="module")
def pk01_result() -> dict:
    return produce_pack("PK01", _pk01_input())


def _rows(result: dict, field_id: str) -> list[dict]:
    return [row for row in result["fields"] if row["field_id"] == field_id]


# 1. envelope validity ------------------------------------------------------


def test_result_passes_contract_validator(result: dict) -> None:
    assert contract.validate_pack_result(result) == []


def test_result_passes_jsonschema_envelope(result: dict) -> None:
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT202012
    except ImportError:  # pragma: no cover - CI carries referencing
        pytest.skip("referencing unavailable; validate_pack_result half only")
    schema = contract.load_envelope_schema()
    packet = json.loads(
        (ROOT / "contracts" / "financial_intelligence_packet.schema.json").read_text(
            "utf-8"
        )
    )
    registry = Registry()
    for contents in (schema, packet):
        registry = registry.with_resource(
            contents["$id"],
            Resource.from_contents(contents, default_specification=DRAFT202012),
        )
    errors = list(Draft202012Validator(schema, registry=registry).iter_errors(result))
    assert errors == []


# 2. catalogue order --------------------------------------------------------


def test_every_catalogue_field_and_check_once_in_order(result: dict) -> None:
    catalogue = contract.load_pack_schema("PK06")
    assert [row["field_id"] for row in result["fields"]] == [
        item["field_id"] for item in catalogue["fields"]
    ]
    assert [row["check_id"] for row in result["checks"]] == [
        item["check_id"] for item in catalogue["checks"]
    ]


# 3. valued rows and the split identity -------------------------------------


@pytest.mark.parametrize("field_id", sorted(VALUED))
def test_valued_rows_carry_fact_evidence(
    result: dict, ledger, field_id: str
) -> None:
    row = _row(result, field_id)
    assert row["quality_state"] == "valued"
    assert row["evidence_kind"] == "xbrl_fact"
    assert row["coverage_state"] == "source_trace_complete"
    assert row["value"] == VALUED[field_id]
    assert row["source_occurrence_ids"], "valued xbrl_fact needs occurrence ids"
    for occurrence_id in row["source_occurrence_ids"]:
        assert ledger.by_id(occurrence_id) is not None
    assert row["concept"].startswith("us-gaap:")
    assert row["taxonomy"] == "us-gaap"
    assert row["unit"] == "USD"
    assert row["mapping_rule_id"] == f"PK06.{field_id}.fact/v1"
    assert row["mapping_rule_digest"]


def test_split_vs_total_passes_with_printed_tolerance(result: dict) -> None:
    check = _check(result, "lease_liability_split_vs_total")
    assert check["status"] == "pass"
    # min decimals across the six operands is -6 -> tolerance 1 * 10^6.
    assert check["tolerance"] == "1000000"
    assert check["operands"] == [
        "operating_lease_liability_current",
        "operating_lease_liability_noncurrent",
        "operating_lease_liability_total",
        "finance_lease_liability_current",
        "finance_lease_liability_noncurrent",
        "finance_lease_liability_total",
    ]


# 4. typed absences ---------------------------------------------------------


def test_absent_fields_report_exact_standard_fact_reasons(result: dict) -> None:
    for field_id, reason in MISSING_REASONS.items():
        row = _row(result, field_id)
        assert row["quality_state"] == "missing"
        assert row["non_value_state"] == "missing"
        assert row["value"] is None and row["text_value"] is None
        assert row["reason"] == reason


def test_no_extension_only_field_exists_on_this_fixture(result: dict) -> None:
    """Why no ``extension_concept_unaliased:aapl`` row appears on PK06.

    The fixture's combined operating+finance ladder lives under an issuer
    extension namespace, but under DIFFERENT local names
    (``LesseeOperatingAndFinanceLeaseLiabilityToBePaid`` vs the standard
    ``OperatingAndFinanceLeaseLiabilityPaymentsDue``), so no PK06 listed
    concept has a same-local-name extension fact. Every absence on this
    fixture is therefore an exact ``missing_standard_fact`` reason (asserted
    above); the extension machinery itself is pinned by the probe below.
    """
    absent = {row["field_id"]: row["reason"] for row in result["fields"] if row["quality_state"] == "missing"}
    assert absent == MISSING_REASONS


def test_extension_concept_absence_is_nameable_via_probe() -> None:
    # rou_assets_finance is instant-kind, matching the instant extension fact;
    # a duration field would correctly miss it on period kind.
    probe = replace(
        pk06_leases.PRODUCER,
        field_mappings={
            **pk06_leases.PRODUCER.field_mappings,
            "rou_assets_finance": pack_base.FactMapping(
                ("us-gaap:LesseeOperatingAndFinanceLeaseLiabilityToBePaid",)
            ),
        },
        extension_prefixes={"aapl": "http://www.apple.com/20250927"},
    )
    probe_result = pack_base.produce_pack_result(probe, _pack_input())
    row = _row(probe_result, "rou_assets_finance")
    assert row["quality_state"] == "missing"
    assert row["reason"] == "extension_concept_unaliased:aapl"


# 5. cross-statement check gates on the foreign producer --------------------


def test_commitments_check_awaits_pk08(result: dict) -> None:
    check = _check(result, "commitments_not_in_contingencies")
    assert check["status"] == "not_evaluable"
    assert check["reason"] == "missing_dependency"


# 6. applicability (R-K1) ---------------------------------------------------


def test_unknown_sic_keeps_pk06_applicable() -> None:
    result = produce_pack(
        "PK06", _pack_input(issuer_sic=None, sic_source=None)
    )
    assert result["applicability"]["state"] == "applicable"
    assert result["applicability"]["reason"] == "applicability_rule_satisfied"
    assert "issuer_class=unknown" in result["receipts"]


def test_class_restricted_probe_is_not_applicable() -> None:
    probe = replace(
        pk06_leases.PRODUCER,
        spec=replace(
            pk06_leases.SPEC,
            applicable_classes=frozenset({"bank"}),
            inapplicable_class_reason="issuer_class_outside_pack_classes",
        ),
    )
    state, reason = pack_base.evaluate_applicability(probe, _pack_input(), "10-K")
    assert state == "not_applicable"
    assert reason == "issuer_class_outside_pack_classes"


def test_form_probe_makes_every_field_not_applicable() -> None:
    probe = replace(
        pk06_leases.PRODUCER,
        spec=replace(pk06_leases.SPEC, forms=frozenset({"DEF 14A"})),
    )
    probe_result = pack_base.produce_pack_result(probe, _pack_input())
    assert probe_result["applicability"]["state"] == "not_applicable"
    assert probe_result["applicability"]["reason"] == "form_outside_pack_forms"
    assert len(probe_result["fields"]) == 21
    for row in probe_result["fields"]:
        assert row["quality_state"] == "not_applicable"
        assert row["reason"] == "form_outside_pack_forms"
        assert row["coverage_state"] == "not_applicable_period"
    for check in probe_result["checks"]:
        assert check["status"] == "not_applicable"
        assert check["reason"] == "form_outside_pack_forms"
    assert probe_result["coverage"]["disclosure_coverage_state"] == "not_supplied"
    assert contract.validate_pack_result(probe_result) == []


# 7. determinism and identity binding ---------------------------------------


def test_production_is_deterministic() -> None:
    first = produce_pack("PK06", _pack_input())
    second = produce_pack("PK06", _pack_input())
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["pack_content_sha256"] == second["pack_content_sha256"]


def test_query_change_rebinds_packet_id_and_content_digest() -> None:
    other = produce_pack(
        "PK06",
        _pack_input(query={**QUERY, "requested_periods": ["FY2024"]}),
    )
    baseline = produce_pack("PK06", _pack_input())
    assert other["packet_id"] != baseline["packet_id"]
    # The contract digest excludes only pack_content_sha256 itself, so the
    # minted packet_id (a function of the query) is inside the digest body.
    assert other["pack_content_sha256"] != baseline["pack_content_sha256"]


# 8. R-K3: a formula never implies zero -------------------------------------


def test_formula_over_missing_input_is_not_evaluable() -> None:
    probe = replace(
        pk06_leases.PRODUCER,
        field_mappings={
            **pk06_leases.PRODUCER.field_mappings,
            "lease_cost_total": pack_base.FormulaMapping(
                rule_id="PK06.lease_cost_total.formula/v1",
                inputs=("lease_cost_short_term",),
                fn=lambda values: values["lease_cost_short_term"] * Decimal(2),
            ),
        },
    )
    probe_result = pack_base.produce_pack_result(probe, _pack_input())
    row = _row(probe_result, "lease_cost_total")
    assert row["quality_state"] == "not_evaluable"
    assert row["reason"] == "missing_dependency"
    assert row["value"] is None
    assert row["formula_rule_id"] == "PK06.lease_cost_total.formula/v1"
    assert row["dependency_field_ids"] == ["lease_cost_short_term"]


# 9. registry ----------------------------------------------------------------


def test_registry_shape_and_refusal() -> None:
    assert registered_pack_ids() == ("PK01", "PK06")
    assert set(PACK_PRODUCERS) == {"PK01", "PK06"}
    with pytest.raises(SpecialistPackError, match="no producer registered: PK07"):
        produce_pack("PK07", _pack_input())
    with pytest.raises(SpecialistPackError, match="no producer registered: PK99"):
        produce_pack("PK99", _pack_input())


# 10. CLI --------------------------------------------------------------------


def test_cli_writes_valid_envelope(tmp_path: Path) -> None:
    entity_file = tmp_path / "entity.json"
    query_file = tmp_path / "query.json"
    out_file = tmp_path / "pk06.json"
    entity_file.write_text(json.dumps(ENTITY), encoding="utf-8")
    query_file.write_text(json.dumps(QUERY), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "fif_specialist_packs.py"),
            "--pack",
            "PK06",
            "--package-dir",
            str(FIXTURE_DIR),
            "--entity-json",
            str(entity_file),
            "--query-json",
            str(query_file),
            "--issuer-sic",
            "3571",
            "--sic-source",
            "sec_submissions",
            "--out",
            str(out_file),
        ],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    envelope = json.loads(out_file.read_text("utf-8"))
    assert contract.validate_pack_result(envelope) == []
    assert envelope["applicability"]["state"] == "applicable"
    assert envelope["coverage"]["valued_fields"] == 15


def test_cli_usage_error_exits_two(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "fif_specialist_packs.py"),
            "--out",
            str(tmp_path / "out.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2


# 11. A33 guard ---------------------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    [
        "engine/fundamental_forensics/specialist_packs/__init__.py",
        "engine/fundamental_forensics/specialist_packs/base.py",
        "engine/fundamental_forensics/specialist_packs/registry.py",
        "engine/fundamental_forensics/specialist_packs/pk06_leases.py",
        "engine/fundamental_forensics/specialist_packs/pk01_debt.py",
        "scripts/fif_specialist_packs.py",
    ],
)
def test_no_issuer_literals_in_production_code(relative: str) -> None:
    text = (ROOT / relative).read_text("utf-8")
    for literal in ("0000320193", "AAPL", "Apple"):
        assert literal not in text, f"{relative} carries {literal!r}"


# 12. PK01 envelope validity -------------------------------------------------


def test_pk01_result_passes_contract_validator(pk01_result: dict) -> None:
    assert contract.validate_pack_result(pk01_result) == []


def test_pk01_result_passes_jsonschema_envelope(pk01_result: dict) -> None:
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT202012
    except ImportError:  # pragma: no cover - CI carries referencing
        pytest.skip("referencing unavailable; validate_pack_result half only")
    schema = contract.load_envelope_schema()
    packet = json.loads(
        (ROOT / "contracts" / "financial_intelligence_packet.schema.json").read_text(
            "utf-8"
        )
    )
    registry = Registry()
    for contents in (schema, packet):
        registry = registry.with_resource(
            contents["$id"],
            Resource.from_contents(contents, default_specification=DRAFT202012),
        )
    errors = list(
        Draft202012Validator(schema, registry=registry).iter_errors(pk01_result)
    )
    assert errors == []


# 13. PK01 catalogue order and repeated rows ---------------------------------


def test_pk01_rows_follow_catalogue_order_with_adjacent_repeats(
    pk01_result: dict,
) -> None:
    catalogue = contract.load_pack_schema("PK01")
    expected = [item["field_id"] for item in catalogue["fields"]]
    produced = [row["field_id"] for row in pk01_result["fields"]]
    assert len(produced) == 22 + 1  # the by-instrument field repeats once
    assert len(produced) == len(set(produced)) + 1
    compacted = [field_id for index, field_id in enumerate(produced) if index == 0 or produced[index - 1] != field_id]
    assert compacted == expected
    instrument_rows = _rows(pk01_result, "debt_carrying_amount_by_instrument")
    assert len(instrument_rows) == 2  # repeated field_ids pass the validator
    # The repeated rows sit at the catalogue position of their field.
    position = produced.index("debt_carrying_amount_by_instrument")
    assert produced[position + 1] == "debt_carrying_amount_by_instrument"
    assert [row["check_id"] for row in pk01_result["checks"]] == [
        item["check_id"] for item in catalogue["checks"]
    ]


# 14. PK01 valued rows (B.4, one bullet per assertion) ------------------------


def test_pk01_maturity_ladder_and_carrying_total(pk01_result: dict, ledger) -> None:
    for field_id, value in PK01_LADDER.items():
        assert _row(pk01_result, field_id)["value"] == value
    total = _row(pk01_result, "debt_carrying_amount_total")
    assert total["value"] == "91281000000"
    # Two identical undimensioned occurrences are not a conflict; both listed.
    assert len(total["source_occurrence_ids"]) == 2
    for occurrence_id in total["source_occurrence_ids"]:
        assert ledger.by_id(occurrence_id) is not None
    check = _check(pk01_result, "maturity_ladder_vs_carrying")
    assert check["status"] == "pass"
    assert check["tolerance"] == "1000000"


def test_pk01_instrument_rows_and_reconcile(pk01_result: dict, ledger) -> None:
    rows = _rows(pk01_result, "debt_carrying_amount_by_instrument")
    assert [row["value"] for row in rows] == ["86781000000", "4500000000"]
    assert rows[0]["dimensions"] == [
        {"axis": "us-gaap:DebtInstrumentAxis", "member": INSTRUMENT_ISSUER_MEMBER},
        {"axis": "us-gaap:LongtermDebtTypeAxis", "member": FIXED_RATE_NOTES_MEMBER},
    ]
    assert rows[1]["dimensions"] == [
        {"axis": "us-gaap:DebtInstrumentAxis", "member": INSTRUMENT_2025_MEMBER},
        {"axis": "us-gaap:LongtermDebtTypeAxis", "member": FIXED_RATE_NOTES_MEMBER},
    ]
    for row in rows:
        assert row["mapping_rule_id"] == (
            "PK01.debt_carrying_amount_by_instrument.dimensioned_fact/v1"
        )
        assert row["coverage_state"] == "source_trace_complete"
        assert ledger.by_id(row["source_occurrence_ids"][0]) is not None
    check = _check(pk01_result, "instrument_rows_vs_total")
    assert check["status"] == "pass"
    assert check["evidence_field_ids"] == [
        "debt_carrying_amount_by_instrument",
        "debt_carrying_amount_total",
    ]


def test_pk01_debt_split_fields(pk01_result: dict) -> None:
    assert _row(pk01_result, "long_term_debt_current")["value"] == "12350000000"
    assert _row(pk01_result, "long_term_debt")["value"] == "78328000000"
    assert _row(pk01_result, "long_term_debt")["concept"] == "us-gaap:LongTermDebtNoncurrent"


def test_pk01_fair_value_row_keeps_reported_value(pk01_result: dict) -> None:
    rows = _rows(pk01_result, "debt_fair_value")
    assert len(rows) == 1
    row = rows[0]
    # Fact decimals -8: the row keeps the reported value.
    assert row["value"] == "80400000000"
    assert row["dimensions"] == [
        {
            "axis": "us-gaap:FairValueByFairValueHierarchyLevelAxis",
            "member": "us-gaap:FairValueInputsLevel2Member",
        }
    ]


def test_pk01_liquidity_fields(pk01_result: dict) -> None:
    assert _row(pk01_result, "cash_and_cash_equivalents")["value"] == "35934000000"
    investments = _row(pk01_result, "short_term_investments")
    assert investments["value"] == "18763000000"
    assert investments["concept"] == "us-gaap:MarketableSecuritiesCurrent"
    assert _row(pk01_result, "liquidity_total_cash_and_securities")["value"] == "54697000000"


def test_pk01_formulas(pk01_result: dict) -> None:
    assert _row(pk01_result, "current_assets")["value"] == "147957000000"
    assert _row(pk01_result, "current_liabilities")["value"] == "165631000000"
    ratio = _row(pk01_result, "current_ratio")
    assert ratio["value"] == "0.893293"
    assert ratio["unit"] == "ratio"
    assert ratio["formula_rule_id"] == "pk01.current_ratio.div/v1"
    assert ratio["dependency_field_ids"] == ["current_assets", "current_liabilities"]
    capital = _row(pk01_result, "working_capital")
    assert capital["value"] == "-17674000000"
    assert capital["formula_rule_id"] == "pk01.working_capital.diff/v1"
    liquidity = _row(pk01_result, "liquidity_total_cash_and_securities")
    assert liquidity["evidence_kind"] == "formula"
    assert liquidity["formula_rule_id"] == (
        "pk01.liquidity_total_cash_and_securities.sum/v1"
    )
    assert liquidity["dependency_field_ids"] == [
        "cash_and_cash_equivalents",
        "short_term_investments",
    ]


def test_pk01_applicability_and_coverage(pk01_result: dict) -> None:
    applicability = pk01_result["applicability"]
    assert applicability["state"] == "applicable"
    assert applicability["reason"] == "applicability_rule_satisfied"
    assert applicability["sic"] == "3571"
    assert pk01_result["coverage"]["disclosure_coverage_state"] == "present"
    assert pk01_result["coverage"] == {
        "valued_fields": 19,
        "missing_fields": 2,
        "unsupported_fields": 1,
        "not_evaluable_fields": 1,
        "not_applicable_fields": 0,
        "disclosure_coverage_state": "present",
    }


# 15. PK01 typed absences -----------------------------------------------------


def test_pk01_short_term_debt_is_missing_standard_fact(pk01_result: dict) -> None:
    row = _row(pk01_result, "short_term_debt")
    assert row["quality_state"] == "missing"
    assert row["reason"] == "missing_standard_fact:us-gaap:ShortTermBorrowings"
    assert row["value"] is None


def test_pk01_revolver_capacity_is_missing_standard_fact(pk01_result: dict) -> None:
    row = _row(pk01_result, "revolver_undrawn_capacity")
    assert row["quality_state"] == "missing"
    assert row["reason"] == (
        "missing_standard_fact:us-gaap:LineOfCreditFacilityRemainingBorrowingCapacity"
    )


def test_pk01_total_debt_falls_back_to_formula(pk01_result: dict) -> None:
    row = _row(pk01_result, "total_debt")
    assert row["quality_state"] == "not_evaluable"
    assert row["reason"] == "missing_dependency"
    assert row["evidence_kind"] == "formula"
    assert row["required_evidence_kind"] == "xbrl_fact"
    assert row["formula_rule_id"] == "pk01.total_debt.sum/v1"
    assert (
        "debt_components_vs_total: total_debt is formula-derived from the same addends"
        in pk01_result["limitations"]
    )


def test_pk01_debt_components_check_not_evaluable(pk01_result: dict) -> None:
    check = _check(pk01_result, "debt_components_vs_total")
    assert check["status"] == "not_evaluable"
    assert check["reason"] == "missing_dependency"


def test_pk01_covenant_span_is_unsupported(pk01_result: dict) -> None:
    row = _row(pk01_result, "covenant_term_observation")
    assert row["quality_state"] == "unsupported"
    assert row["non_value_state"] == "unsupported"
    assert row["evidence_kind"] == "text_span"
    assert row["required_evidence_kind"] == "text_span"
    assert row["reason"] == "missing_dependency"
    check = _check(pk01_result, "covenant_span_present")
    assert check["status"] == "not_evaluable"
    assert check["reason"] == "missing_dependency"


# 16. PK01 issuer-class probes (B.5 and the unknown-class gate) ---------------


def test_pk01_bank_probe_excludes_industrial_rows() -> None:
    bank = produce_pack("PK01", _pk01_input(issuer_sic="6021", sic_source="dei"))
    assert bank["applicability"]["state"] == "applicable"
    for field_id in ("current_ratio", "working_capital"):
        row = _row(bank, field_id)
        assert row["quality_state"] == "not_applicable"
        assert row["non_value_state"] == "not_applicable"
        assert row["coverage_state"] == "not_applicable_period"
        assert row["reason"] == "industrial_basis_excluded_for_financial_institution"
        assert row["value"] is None
        assert row["source_occurrence_ids"] == []
    assert bank["coverage"]["not_applicable_fields"] == 2
    baseline = produce_pack("PK01", _pk01_input())
    excluded = ("current_ratio", "working_capital")
    unchanged_baseline = [
        row for row in baseline["fields"] if row["field_id"] not in excluded
    ]
    unchanged_bank = [row for row in bank["fields"] if row["field_id"] not in excluded]
    assert unchanged_bank == unchanged_baseline
    assert contract.validate_pack_result(bank) == []


def test_pk01_unknown_sic_probe_keeps_pack_applicable() -> None:
    result = produce_pack("PK01", _pk01_input(issuer_sic=None, sic_source=None))
    assert result["applicability"]["state"] == "applicable"
    assert result["applicability"]["reason"] == "applicability_rule_satisfied"
    for field_id in ("current_ratio", "working_capital"):
        row = _row(result, field_id)
        assert row["quality_state"] == "not_evaluable"
        assert row["reason"] == "issuer_class_unknown"
    assert "issuer_class=unknown" in result["receipts"]
    assert contract.validate_pack_result(result) == []


# 17. PK01 determinism and PK06 invariance ------------------------------------


def test_pk01_production_is_deterministic() -> None:
    first = produce_pack("PK01", _pk01_input())
    second = produce_pack("PK01", _pk01_input())
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["pack_content_sha256"] == second["pack_content_sha256"]


def test_pk06_envelope_digest_unchanged_by_pk01_edits() -> None:
    result = produce_pack("PK06", _pack_input())
    payload = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert sha256(payload.encode("utf-8")).hexdigest() == PK06_ENVELOPE_SHA256


# 18. PK01 CLI ----------------------------------------------------------------


def test_pk01_cli_writes_valid_envelope(tmp_path: Path) -> None:
    entity_file = tmp_path / "entity.json"
    query_file = tmp_path / "query.json"
    out_file = tmp_path / "pk01.json"
    entity_file.write_text(json.dumps(ENTITY), encoding="utf-8")
    query_file.write_text(json.dumps(PK01_QUERY), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "fif_specialist_packs.py"),
            "--pack",
            "PK01",
            "--package-dir",
            str(FIXTURE_DIR),
            "--entity-json",
            str(entity_file),
            "--query-json",
            str(query_file),
            "--issuer-sic",
            "3571",
            "--sic-source",
            "sec_submissions",
            "--out",
            str(out_file),
        ],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    envelope = json.loads(out_file.read_text("utf-8"))
    assert contract.validate_pack_result(envelope) == []
    assert envelope["applicability"]["state"] == "applicable"
    assert len(envelope["fields"]) == 23
    assert envelope["coverage"]["valued_fields"] == 19


# 19. F1-F10 framework repair (independent review, PR #9843) ------------------
#
# Every case below discriminates one ruling. Synthetic-occurrence cases run
# the whole envelope by swapping the golden converter for a hand-built raw
# ledger (the framework admits the ledger through the same deferred import
# the production path uses), so rows, limitations and receipts are asserted
# at envelope level.

from datetime import date as _date  # noqa: E402
from types import MappingProxyType as _MappingProxyType  # noqa: E402
import importlib.util as _importlib_util  # noqa: E402

from engine.fundamental_forensics import ixbrl_raw_ledger as _ixbrl  # noqa: E402
from engine.fundamental_forensics.raw_ledger import (  # noqa: E402
    FactContext as _FactContext,
    FactUnit as _FactUnit,
    RawFactLedger as _RawFactLedger,
    RawFactOccurrence as _RawFactOccurrence,
    SourceIdentity as _SourceIdentity,
    TemporalClocks as _TemporalClocks,
)
from engine.fundamental_forensics.specialist_packs import (  # noqa: E402
    registry as _pack_registry,
)

POR = _date(2025, 9, 27)
_PROBE_SOURCE = _SourceIdentity(
    source="probe",
    entity_id="0000320193",
    accession="0000320193-25-000079",
    document_id="probe-doc",
    body_sha256="0" * 64,
)


def _probe_occurrence(
    *,
    key: str,
    concept: str,
    value: Decimal,
    measures: tuple[str, ...] = ("iso4217:USD",),
    denominators: tuple[str, ...] = (),
    instant: _date | None = None,
    start: _date | None = None,
    end: _date | None = None,
    dimensions: tuple[tuple[str, str], ...] = (),
    dimensions_known: bool = True,
) -> _RawFactOccurrence:
    context = _FactContext(
        context_id=f"probe-{key}",
        entity_scheme="http://www.sec.gov/CIK",
        entity_identifier=_PROBE_SOURCE.entity_id,
        instant=instant,
        start=start,
        end=end,
        explicit_dimensions=dimensions,
    )
    return _RawFactOccurrence(
        source=_PROBE_SOURCE,
        concept_qname=concept,
        context=context,
        clocks=_TemporalClocks(recorded_at="2026-08-23T00:32:31Z"),
        unit=_FactUnit(
            unit_id=f"u-{key}", measures=measures, denominator_measures=denominators
        ),
        dimensions_known=dimensions_known,
        source_occurrence_key=key,
        parsed_value=value,
        decimals="-6",
    )


def _produce_pk06_with_ledger(
    monkeypatch, occurrences: list[_RawFactOccurrence], **overrides
) -> dict:
    ledger = _RawFactLedger(tuple(occurrences))
    report = _ixbrl.ConversionReport(
        filings=(), ledger_sha256="0" * 64, source_namespace_families=()
    )
    monkeypatch.setattr(
        _ixbrl,
        "parse_and_convert_golden_packages",
        lambda packages: (ledger, {}, report),
    )
    return produce_pack("PK06", _pack_input(**overrides))


def test_rf1_fact_unit_must_satisfy_catalogue_unit(monkeypatch) -> None:
    # R-F1: an iso4217:EUR-tagged fact in a USD field is a typed absence.
    eur = _probe_occurrence(
        key="eur",
        concept="us-gaap:OperatingLeaseCost",
        value=Decimal("2100000000"),
        measures=("iso4217:EUR",),
        start=_date(2024, 9, 29),
        end=POR,
    )
    result = _produce_pk06_with_ledger(monkeypatch, [eur])
    row = _row(result, "lease_cost_operating")
    assert row["quality_state"] == "not_evaluable"
    assert row["reason"] == "unit_mismatch"  # PK06 declares it: no projection
    assert "lease_cost_operating: fact unit EUR is not USD" in result["limitations"]
    assert row["source_occurrence_ids"] == [eur.occurrence_id]
    assert not any(
        "undeclared by pack catalogue" in item for item in result["limitations"]
    )
    assert contract.validate_pack_result(result) == []
    # The same value tagged iso4217:USD (ledger spelling USD) is valued.
    usd = _probe_occurrence(
        key="usd",
        concept="us-gaap:OperatingLeaseCost",
        value=Decimal("2100000000"),
        start=_date(2024, 9, 29),
        end=POR,
    )
    row = _row(_produce_pk06_with_ledger(monkeypatch, [usd]), "lease_cost_operating")
    assert row["quality_state"] == "valued"
    assert row["value"] == "2100000000"
    assert row["unit"] == "USD"


def test_rf1_pure_fact_in_ratio_field_valued_without_rescale(monkeypatch) -> None:
    # R-F1 percent-scale caution: a dimensionless pure value passes through
    # tagged, never rescaled into the ratio field.
    pure = _probe_occurrence(
        key="pure",
        concept="us-gaap:OperatingLeaseWeightedAverageDiscountRatePercent",
        value=Decimal("0.0403"),
        measures=("xbrli:pure",),
        instant=POR,
    )
    result = _produce_pk06_with_ledger(monkeypatch, [pure])
    row = _row(result, "weighted_average_discount_rate")
    assert row["quality_state"] == "valued"
    assert row["value"] == "0.0403"
    assert row["unit"] == "ratio"
    assert contract.validate_pack_result(result) == []


def test_rf2_53_week_year_admitted_and_400_day_excluded(monkeypatch) -> None:
    assert pack_base.MAX_DURATION_DAYS == 380
    long_371 = _probe_occurrence(
        key="d371",
        concept="us-gaap:OperatingLeaseCost",
        value=Decimal("1000"),
        start=_date(2024, 9, 22),
        end=POR,
    )
    short_91 = _probe_occurrence(
        key="d91",
        concept="us-gaap:OperatingLeaseCost",
        value=Decimal("2000"),
        start=_date(2025, 6, 29),
        end=POR,
    )
    result = _produce_pk06_with_ledger(monkeypatch, [short_91, long_371])
    row = _row(result, "lease_cost_operating")
    # Longest-at-end: the 371-day fiscal year beats the 91-day quarter.
    assert row["quality_state"] == "valued"
    assert row["value"] == "1000"
    assert row["period"] == {
        "kind": "duration",
        "start": "2024-09-22",
        "end": "2025-09-27",
    }
    too_long = _probe_occurrence(
        key="d400",
        concept="us-gaap:OperatingLeaseCost",
        value=Decimal("3000"),
        start=_date(2024, 8, 24),
        end=POR,
    )
    result = _produce_pk06_with_ledger(monkeypatch, [too_long, short_91])
    row = _row(result, "lease_cost_operating")
    # A 400-day context is still excluded; the 91-day context values the row.
    assert row["quality_state"] == "valued"
    assert row["value"] == "2000"
    assert row["period"]["start"] == "2025-06-29"


def test_rf3_dimensions_known_false_is_not_consolidated(monkeypatch) -> None:
    unknown = _probe_occurrence(
        key="unk",
        concept="us-gaap:OperatingLeaseRightOfUseAsset",
        value=Decimal("11205000000"),
        instant=POR,
        dimensions_known=False,
    )
    result = _produce_pk06_with_ledger(monkeypatch, [unknown])
    row = _row(result, "rou_assets_operating")
    assert row["quality_state"] == "missing"
    assert row["reason"] == "disallowed_dimension"
    assert row["source_occurrence_ids"] == [unknown.occurrence_id]
    assert (
        "rou_assets_operating: dimensional context not exposed by the source"
        " plane (dimensions_known=false)" in result["limitations"]
    )
    assert contract.validate_pack_result(result) == []
    # One dimensions_known=True undimensioned occurrence still values the row.
    known = _probe_occurrence(
        key="knw",
        concept="us-gaap:OperatingLeaseRightOfUseAsset",
        value=Decimal("11205000000"),
        instant=POR,
    )
    row = _row(_produce_pk06_with_ledger(monkeypatch, [known, unknown]), "rou_assets_operating")
    assert row["quality_state"] == "valued"
    assert row["value"] == "11205000000"
    assert row["source_occurrence_ids"] == [known.occurrence_id]


def test_rf4_cross_package_cik_gate_and_receipts() -> None:
    ten_k = load_golden_aapl_package(ROOT, accession=ACCESSION)
    ten_q = load_golden_aapl_package(ROOT, accession="0000320193-26-000020")
    foreign = replace(ten_q, manifest={**ten_q.manifest, "cik": "0000999999"})
    with pytest.raises(
        SpecialistPackError,
        match=(
            r"package issuer mismatch: 0000320193-26-000020"
            r" cik=0000999999 entity cik=0000320193"
        ),
    ):
        produce_pack("PK06", _pack_input(packages=(ten_k, foreign)))
    both = produce_pack("PK06", _pack_input(packages=(ten_q, ten_k)))
    assert "packages_admitted=2" in both["receipts"]
    assert (
        "package_accessions=0000320193-25-000079,0000320193-26-000020"
        in both["receipts"]
    )
    assert contract.validate_pack_result(both) == []


def test_rf5_cross_pack_cycle_is_cut_not_recursed(monkeypatch) -> None:
    # Probe PK08 producer (registered inside this test only): its range check
    # references pk06 while PK06's commitments check references pk08.
    probe_fields = {
        item["field_id"]: pack_base.FactMapping((f"us-gaap:Probe{item['field_id']}",))
        for item in contract.load_pack_schema("PK08")["fields"]
    }
    probe = pack_base.PackProducer(
        spec=pack_base.PackSpec(
            pack_id="PK08",
            forms=frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"}),
            applicability_rule_id="specialist_pack.pk08.applicability/v1",
        ),
        field_mappings=probe_fields,
        checks=(
            pack_base.CrossStatement(
                check_id="accrual_vs_range",
                left="pk06:rou_assets_operating",
                right="pk06:offbalance_purchase_commitments",
                relation="disjoint",
            ),
            pack_base.Presence(
                check_id="nil_bs_vs_note",
                field_id="commitments_and_contingencies_bs_state",
            ),
            pack_base.Presence(
                check_id="item3_vs_note", field_id="legal_proceedings_item3"
            ),
        ),
    )
    patched = dict(_pack_registry.PACK_PRODUCERS)
    patched["PK08"] = probe
    monkeypatch.setattr(_pack_registry, "PACK_PRODUCERS", _MappingProxyType(patched))
    captured: dict[str, dict] = {}
    real_produce = _pack_registry.produce_pack

    def spying_produce(pack_id: str, pack_input):
        result = real_produce(pack_id, pack_input)
        captured.setdefault(pack_id, result)
        return result

    monkeypatch.setattr(_pack_registry, "produce_pack", spying_produce)
    result = produce_pack("PK06", _pack_input())  # no RecursionError
    assert contract.validate_pack_result(result) == []
    check = _check(result, "commitments_not_in_contingencies")
    assert check["status"] == "not_evaluable"
    assert check["reason"] == "missing_dependency"
    assert not any("cross-pack cycle" in item for item in result["limitations"])
    # The inner probe envelope was produced and carries the cycle limitation.
    probe_result = captured["PK08"]
    assert contract.validate_pack_result(probe_result) == []
    assert (
        "accrual_vs_range: cross-pack cycle PK06 -> PK08 -> PK06"
        in probe_result["limitations"]
    )
    probe_check = next(
        item
        for item in probe_result["checks"]
        if item["check_id"] == "accrual_vs_range"
    )
    assert probe_check["status"] == "not_evaluable"
    assert probe_check["reason"] == "missing_dependency"


def test_rf5_cli_handler_covers_recursion_error(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    spec = _importlib_util.spec_from_file_location(
        "fif_specialist_packs_cli", ROOT / "scripts" / "fif_specialist_packs.py"
    )
    module = _importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def recursing(*_args, **_kwargs):
        raise RecursionError("probe recursion")

    monkeypatch.setattr(module, "produce_pack", recursing)
    entity_file = tmp_path / "entity.json"
    query_file = tmp_path / "query.json"
    entity_file.write_text(json.dumps(ENTITY), encoding="utf-8")
    query_file.write_text(json.dumps(QUERY), encoding="utf-8")
    completed = module.main(
        [
            "--pack",
            "PK06",
            "--package-dir",
            str(FIXTURE_DIR),
            "--entity-json",
            str(entity_file),
            "--query-json",
            str(query_file),
            "--out",
            str(tmp_path / "out.json"),
        ]
    )
    assert completed == 1
    assert "RecursionError" in capsys.readouterr().err


def test_rf6_undeclared_reason_projected_to_missing_dependency() -> None:
    # PK06's own catalogue omits issuer_class_outside_pack_classes (no
    # catalogue declares it), so the bank-restricted probe exercises the
    # projection against the real catalogue — no stand-in needed.
    probe = replace(
        pk06_leases.PRODUCER,
        spec=replace(pk06_leases.SPEC, applicable_classes=frozenset({"bank"})),
    )
    result = pack_base.produce_pack_result(probe, _pack_input())
    assert result["applicability"]["state"] == "not_applicable"
    assert result["applicability"]["reason"] == "missing_dependency"
    assert (
        "applicability: issuer_class_outside_pack_classes undeclared by pack"
        " catalogue" in result["limitations"]
    )
    for row in result["fields"]:
        assert row["reason"] == "missing_dependency"
    for check in result["checks"]:
        assert check["reason"] == "missing_dependency"
    assert contract.validate_pack_result(result) == []
    # Declared codes pass through: PK01 (which declares issuer_class_unknown)
    # keeps it on the unknown-SIC probe, with no projection limitation.
    unknown = produce_pack("PK01", _pk01_input(issuer_sic=None, sic_source=None))
    assert _row(unknown, "current_ratio")["reason"] == "issuer_class_unknown"
    assert not any(
        "undeclared by pack catalogue" in item for item in unknown["limitations"]
    )


def test_rf7_unknown_check_spec_raises() -> None:
    probe = replace(
        pk06_leases.PRODUCER,
        checks=pk06_leases.PRODUCER.checks
        + (
            pack_base.SumIdentity(
                check_id="probe_unknown_check",
                addends=("lease_cost_operating",),
                total="lease_cost_total",
            ),
        ),
    )
    with pytest.raises(SpecialistPackError, match="unknown check spec: probe_unknown_check"):
        pack_base.produce_pack_result(probe, _pack_input())


def test_rf8_empty_operand_specs_raise_at_construction() -> None:
    with pytest.raises(SpecialistPackError):
        pack_base.SumIdentity(check_id="x", addends=(), total="y")
    with pytest.raises(SpecialistPackError):
        pack_base.Reconcile(check_id="x", parts=(), consolidated="y")
    with pytest.raises(SpecialistPackError):
        pack_base.CrossStatement(check_id="x", left="", right="y", relation="equal")


def test_rf9_conflicting_duplicates_name_the_conflict(monkeypatch) -> None:
    first = _probe_occurrence(
        key="dup-a",
        concept="us-gaap:OperatingLeaseCost",
        value=Decimal("100"),
        start=_date(2024, 9, 29),
        end=POR,
    )
    second = _probe_occurrence(
        key="dup-b",
        concept="us-gaap:OperatingLeaseCost",
        value=Decimal("200"),
        start=_date(2024, 9, 29),
        end=POR,
    )
    result = _produce_pk06_with_ledger(monkeypatch, [first, second])
    row = _row(result, "lease_cost_operating")
    assert row["quality_state"] == "not_evaluable"
    assert row["reason"] == "missing_dependency"
    pair = sorted(
        ((first, "100"), (second, "200")), key=lambda item: item[0].occurrence_id
    )
    expected = "lease_cost_operating: conflicting duplicate facts " + ", ".join(
        f"{occurrence.occurrence_id}={value}" for occurrence, value in pair
    )
    assert expected in result["limitations"]
    assert row["source_occurrence_ids"] == sorted(
        {first.occurrence_id, second.occurrence_id}
    )
    assert contract.validate_pack_result(result) == []


def test_rf10_form_rank_beats_newer_interim_and_overflow_raises() -> None:
    ten_k = load_golden_aapl_package(ROOT, accession=ACCESSION)
    ten_q = load_golden_aapl_package(ROOT, accession="0000320193-26-000020")
    result = produce_pack("PK06", _pack_input(packages=(ten_q, ten_k)))
    assert "accession=0000320193-25-000079" in result["receipts"]
    assert "period_of_report=2025-09-27" in result["receipts"]
    assert "primary_selection=form_rank_then_latest_period" in result["receipts"]
    assert contract.validate_pack_result(result) == []
    probe = replace(
        pk06_leases.PRODUCER,
        limitations=tuple(f"probe limitation {i}" for i in range(32)),
    )
    with pytest.raises(SpecialistPackError, match="limitations overflow: 34"):
        pack_base.produce_pack_result(probe, _pack_input())


# 20. Envelope digests after the F1-F10 repair -------------------------------
#
# BASE = dfbf0d6adedda7e251d16b80e9500fd5b30d6f66. The repair's only AAPL
# envelope deltas are the ruled ones: the R-F1/R-F4/R-F10 receipts and the
# R-F10 text-type limitation lines (plus pack_content_sha256, which follows).

_PK06_DIGESTS_AT_BASE = {
    "applicability": "1a501b17c18ebec8947118121250e6995d531b82ba6f8082a75dc3d9eade8b38",
    "authority": "afe002b350bb2e6cd3ff9617c20b59f0ce796e5c6ede0ed994c305a4a7549fd8",
    "checks": "37a13200683a60436fe5a9d2f90a6bb3ab9124886110ca194f6ad058b12b5f1d",
    "coverage": "60c0585d48c96ae04c50f2dc5db8812b2f91e5ed74c77762cb4f8c8a390acd5c",
    "entity": "3b598dc945430b6f2de0b4034712fde88bd61a03cb00b70fe5038e58d4e6dea7",
    "fields": "d3a684e1820501568db99a83a01982fcdfe1d79d9bc27c875c0c6e8a49355285",
    "pack_id": "0a8dccaac32ea5c4dcac7fa621f47676b2f146c3f0ce3b58afece13a649fd59f",
    "pack_schema_digest": "af0520ceea90b8daa62db11ca293d222d18f34a61d9239aa904b9ee044ae079d",
    "pack_schema_id": "74f2604b29c89343706bc8a98e9482d3dee11638ea34d0cff4f070a019e4e7e6",
    "packet_id": "a19125d117a45b6bceec3e81e39fab94d7df8dd492d424d1aae5e83bba23086e",
    "query": "63e258e154d1a6f962a753c434cf73bf973f3f5cd7dc2ac29dc1f8482942208f",
    "schema": "3081d4797b42e9aa62f4d8372ec03a2beb6e7b76c1c284845c28170375aa4dcd",
}
_PK01_DIGESTS_AT_BASE = {
    "applicability": "b06c1e41f3851b4b730a6e78094227aadbfff800bcf51d18f90dc736b375bee5",
    "authority": "afe002b350bb2e6cd3ff9617c20b59f0ce796e5c6ede0ed994c305a4a7549fd8",
    "checks": "d7f32c43e8472f43a6a4f1e4b3faafcbf30f14dec082e6cca3bdc843d58975a6",
    "coverage": "beda68ec8ef672ca061440a1ae2dc217ec7555b6abbf2ebfb35306591862b712",
    "entity": "3b598dc945430b6f2de0b4034712fde88bd61a03cb00b70fe5038e58d4e6dea7",
    "fields": "de26983c8dc52853cc065b80d44c232a75db9b764bc60b4dc4cd1b8637617669",
    "pack_id": "31269612f33c0decb5f4b7e2b0e81f4c2f567d641cb8ceea723c4d49c5a20563",
    "pack_schema_digest": "74c542651182165503179627c6cbc9ef90ea2412a95330eb2db9ed6d6a1a1f93",
    "pack_schema_id": "d1003c587975c638a75f8beb64b74ef72bf7a5b746e0d16c9a86b8d4617a0c30",
    "packet_id": "81e9a991518736f43537bd118ce8913af35bc182fa46615711d59de60098eed8",
    "query": "2bff0400967b0d3539b2b97df7249589b563eec792cf44b46ef598f18f365034",
    "schema": "3081d4797b42e9aa62f4d8372ec03a2beb6e7b76c1c284845c28170375aa4dcd",
}
_PK06_RECEIPTS_AFTER_REPAIR = [
    "catalogue_digest=5a3035afe8eb3bab6531a8d3f8a072ac1523f0b2f1d14f72a2103f226ac6cc47",
    "accession=0000320193-25-000079",
    "form=10-K",
    "period_of_report=2025-09-27",
    "primary_document_sha256=548ae59778cf08ee0f2ee088e7ece20d947076c3c01f74d2d65db4c2777e436a",
    "conversion_fact_count=964",
    "issuer_class=industrial",
    "packages_admitted=1",
    "package_accessions=0000320193-25-000079",
    "primary_selection=form_rank_then_latest_period",
    "unit_check=catalogue_equivalence_v1",
    "packet_id_basis=standalone_pack_context",
]
_PK01_RECEIPTS_AFTER_REPAIR = [
    "catalogue_digest=850fb0e262c38605590ed121d7854e055b31a855c41ca929adbff9766d3302c7",
    "accession=0000320193-25-000079",
    "form=10-K",
    "period_of_report=2025-09-27",
    "primary_document_sha256=548ae59778cf08ee0f2ee088e7ece20d947076c3c01f74d2d65db4c2777e436a",
    "conversion_fact_count=964",
    "issuer_class=industrial",
    "packages_admitted=1",
    "package_accessions=0000320193-25-000079",
    "primary_selection=form_rank_then_latest_period",
    "unit_check=catalogue_equivalence_v1",
    "packet_id_basis=standalone_pack_context",
]
_PK06_LIMITATIONS_AFTER_REPAIR = [
    "display_only: no Q1 held-out evaluation under Q0 has been run for this pack",
    "undiscounted_payments_by_year: only the next-twelve-months row is produced;"
    " the by-year maturity table is a later lane",
    "weighted_average_remaining_term: text-type field; numeric-only converter"
    " cannot value it",
]
_PK01_LIMITATIONS_AFTER_REPAIR = [
    "display_only: no Q1 held-out evaluation under Q0 has been run for this pack",
    "debt_components_vs_total: total_debt is formula-derived from the same addends",
    "covenant_term_observation: text-type field; numeric-only converter cannot"
    " value it",
]


def _key_digest(payload: object) -> str:
    return sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()


def test_pk06_envelope_digest_after_repair() -> None:
    result = produce_pack("PK06", _pack_input())
    payload = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert sha256(payload.encode("utf-8")).hexdigest() == PK06_ENVELOPE_SHA256
    # The whole receipt/limitation level after R-F1/R-F4/R-F10 is pinned.
    assert result["receipts"] == _PK06_RECEIPTS_AFTER_REPAIR
    assert result["limitations"] == _PK06_LIMITATIONS_AFTER_REPAIR


def test_pk01_envelope_digest_after_repair() -> None:
    result = produce_pack("PK01", _pk01_input())
    payload = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert (
        sha256(payload.encode("utf-8")).hexdigest()
        == "c40156a18aafe50874476dd7354a0cf8eb9dc90cb25afe88d409dd3320f56310"
    )
    assert result["receipts"] == _PK01_RECEIPTS_AFTER_REPAIR
    assert result["limitations"] == _PK01_LIMITATIONS_AFTER_REPAIR


def test_rf10_envelope_changed_keys_vs_base_are_exactly_the_ruled_set() -> None:
    # Every BASE key outside {receipts, limitations, pack_content_sha256} is
    # byte-identical after the repair: no AAPL row, check or coverage moved
    # (R-F2's 380-day window admits no new context ending at the 10-K por).
    for result, base_digests in (
        (produce_pack("PK06", _pack_input()), _PK06_DIGESTS_AT_BASE),
        (produce_pack("PK01", _pk01_input()), _PK01_DIGESTS_AT_BASE),
    ):
        for key, expected in base_digests.items():
            assert _key_digest(result[key]) == expected, key
        # R-F6: both envelopes already emit declared codes only, so the
        # projection added no limitation line here.
        assert not any(
            "undeclared by pack catalogue" in item for item in result["limitations"]
        )
