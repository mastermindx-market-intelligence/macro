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
from datetime import date, timedelta
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
from engine.fundamental_forensics import ixbrl_raw_ledger as ixbrl_module
from engine.fundamental_forensics import specialist_pack_contract as contract
from engine.fundamental_forensics.ixbrl_raw_ledger import (
    ConversionReport,
    FilingConversionReceipt,
)
from engine.fundamental_forensics.raw_ledger import FactContext, RawFactLedger
from engine.fundamental_forensics.statement_graph import load_golden_aapl_package
from engine.fundamental_forensics.synthetic_filing_package import (
    filing as synthetic_filing,
)
from engine.fundamental_forensics.synthetic_filing_package import usd_fact

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
PK06_ENVELOPE_SHA256 = (
    "b24c566f00870a6a91431df4b2983b5395868c05be091c211d872d220c5d1a24"
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
    assert registered_pack_ids() == ("PK01", "PK06", "PK11")
    assert set(PACK_PRODUCERS) == {"PK01", "PK06", "PK11"}
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
        "engine/fundamental_forensics/specialist_packs/pk11_bank.py",
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


# 19. PK11: financial-institution credit, capital and liquidity ---------------
#
# The committed AAPL fixture is the NEGATIVE issuer (industrial class); the
# bank path is proven on the synthetic in-test ledger below (a TESTBANK
# 10-K/10-Q whose facts live only in this file). The synthetic-ledger helper
# patches ixbrl_raw_ledger.parse_and_convert_golden_packages — the same
# call-time import both the framework and the PK11 finalize hook use — so the
# manifest-only packages never reach the real parser.


PK11_QUERY = {**QUERY, "requested_metrics": ["bank"]}
TESTBANK_CIK = "0000000002"
TESTBANK_SIC = "6021"
TESTBANK_ENTITY = {
    "entity_id": "ISS:US-TESTBANK",
    "cik": TESTBANK_CIK,
    "ticker": "TESTBANK",
    "name": "TESTBANK SYNTHETIC CORP",
    "identity_basis": "synthetic_in_test_ledger_v1",
    "source_entity_id": TESTBANK_CIK,
}
# (key, concept, placement, value); placements: "prior" = instant one year
# before por (the rollforward opening), "instant" = at por, "duration" = the
# annual window ending at por. Alias priority is exercised deliberately:
# the provision resolves at p20, loans at p30, CET1 at p20.
_TESTBANK_FACTS = (
    (
        "allow_open",
        "us-gaap:FinancingReceivableExcludingAccruedInterestAllowanceForCreditLoss",
        "prior",
        "1000",
    ),
    (
        "allow_close",
        "us-gaap:FinancingReceivableExcludingAccruedInterestAllowanceForCreditLoss",
        "instant",
        "1100",
    ),
    ("prov_fin", "us-gaap:ProvisionForLoanLeaseAndOtherLosses", "duration", "400"),
    (
        "prov_obs",
        "us-gaap:OffBalanceSheetCreditLossLiabilityCreditLossExpenseReversal",
        "duration",
        "50",
    ),
    (
        "write_offs",
        "us-gaap:FinancingReceivableAllowanceForCreditLossesWriteOffsNet",
        "duration",
        "300",
    ),
    (
        "loans",
        "us-gaap:LoansAndLeasesReceivableNetReportedAmount",
        "instant",
        "50000",
    ),
    ("nii", "us-gaap:InterestIncomeExpenseNet", "duration", "2000"),
    (
        "cet1",
        "us-gaap:BankingRegulationCommonEquityTier1Capital",
        "instant",
        "5000",
    ),
    ("rwa", "us-gaap:RiskWeightedAssets", "instant", "40000"),
)
PK11_TABLE_CELL_FIELDS = (
    "cet1_ratio_disclosed",
    "regulatory_minimum_disclosed",
    "lcr_disclosed",
    "nsfr_disclosed",
    "liquid_assets_disclosed",
    "npl_or_npa_disclosed",
)
# A.7 pin, computed at this lane's fork point: PK11 registration and the
# registry finalize hook must not move the BASE packs' AAPL envelopes.
PK01_ENVELOPE_SHA256 = (
    "235a3ce6e9681e0bd3c3e284bc57cf972809ebe06e24a61bc5dba17a41e40a74"
)


class _SyntheticPackage:
    """Manifest-only package: the patched converter supplies the facts."""

    def __init__(self, manifest: dict) -> None:
        self.manifest = manifest


def _testbank_packages(form: str = "10-K", por: str = "2025-12-31") -> tuple:
    return (
        _SyntheticPackage(
            {
                "form": form,
                "period_of_report": por,
                "accession": "0000000002-25-000010",
                "primary_document": "testbank-20251231.htm",
            }
        ),
    )


def _testbank_events(
    *,
    por: str = "2025-12-31",
    drop: tuple[str, ...] = (),
    override: dict[str, str] | None = None,
    extra: tuple[tuple[str, str, str, str], ...] = (),
) -> tuple:
    """The frozen synthetic bank ledger (PK11 §TESTS 3) with per-test edits."""
    filing_row = synthetic_filing(
        accession="0000000002-25-000010",
        document_id="testbank-20251231.htm",
        accepted_at="2026-02-15T16:00:00Z",
        recorded_at="2026-02-15T16:05:00Z",
        filed_at=por,
        entity_id=TESTBANK_CIK,
    )
    end = date.fromisoformat(por)
    prior = end.replace(year=end.year - 1)
    start = end - timedelta(days=end.timetuple().tm_yday - 1)
    contexts = {
        "duration": FactContext(
            context_id="c-fy",
            entity_scheme="http://www.sec.gov/CIK",
            entity_identifier=TESTBANK_CIK,
            start=start.isoformat(),
            end=por,
        ),
        "instant": FactContext(
            context_id="c-i",
            entity_scheme="http://www.sec.gov/CIK",
            entity_identifier=TESTBANK_CIK,
            instant=por,
        ),
        "prior": FactContext(
            context_id="c-ip",
            entity_scheme="http://www.sec.gov/CIK",
            entity_identifier=TESTBANK_CIK,
            instant=prior.isoformat(),
        ),
    }
    values = dict(override or {})
    events = []
    for key, concept, placement, value in _TESTBANK_FACTS:
        if key in drop:
            continue
        amount = values.get(key, value)
        events.append(
            usd_fact(
                filing_row,
                concept,
                contexts[placement],
                amount,
                source_span=(0, len(amount)),
                source_occurrence_key=key,
            )
        )
    for key, concept, placement, value in extra:
        events.append(
            usd_fact(
                filing_row,
                concept,
                contexts[placement],
                value,
                source_span=(0, len(value)),
                source_occurrence_key=key,
            )
        )
    return tuple(events)


def _patch_testbank_converter(monkeypatch: pytest.MonkeyPatch, events: tuple) -> None:
    """Stand in for the golden-package parser on the synthetic ledger."""

    def _convert(packages):
        receipt = FilingConversionReceipt(
            accession="0000000002-25-000010",
            parser_numeric_fact_count=len(events),
            ledger_occurrence_count=len(events),
            represented_count=len(events),
            excluded={},
            source_namespace_families=("us-gaap",),
        )
        report = ConversionReport(
            filings=(receipt,),
            ledger_sha256="0" * 64,
            source_namespace_families=("us-gaap",),
        )
        return RawFactLedger(events), {}, report

    monkeypatch.setattr(ixbrl_module, "parse_and_convert_golden_packages", _convert)


def _pk11_bank_input(**overrides) -> PackInput:
    defaults = dict(
        packages=_testbank_packages(),
        entity=TESTBANK_ENTITY,
        query=PK11_QUERY,
        issuer_sic=TESTBANK_SIC,
        sic_source="dei",
    )
    defaults.update(overrides)
    return PackInput(**defaults)


def _produce_testbank(
    monkeypatch: pytest.MonkeyPatch,
    *,
    form: str = "10-K",
    por: str = "2025-12-31",
    **kwargs,
) -> dict:
    events = _testbank_events(por=por, **kwargs)
    _patch_testbank_converter(monkeypatch, events)
    return produce_pack(
        "PK11", _pk11_bank_input(packages=_testbank_packages(form=form, por=por))
    )


def test_pk11_aapl_negative_issuer() -> None:
    result = produce_pack("PK11", _pack_input(query=PK11_QUERY))
    assert contract.validate_pack_result(result) == []
    assert result["applicability"] == {
        "state": "not_applicable",
        "reason": "issuer_class_not_bank",
        "rule_id": "pack.pk11.applicability/v1",
        "sic": "3571",
        "sic_source": "sec_submissions",
    }
    catalogue = contract.load_pack_schema("PK11")
    assert [row["field_id"] for row in result["fields"]] == [
        item["field_id"] for item in catalogue["fields"]
    ]
    for row in result["fields"]:
        assert row["quality_state"] == "not_applicable"
        assert row["non_value_state"] == "not_applicable"
        assert row["coverage_state"] == "not_applicable_period"
        assert row["reason"] == "issuer_class_not_bank"
        assert row["value"] is None and row["text_value"] is None
    assert [row["check_id"] for row in result["checks"]] == [
        item["check_id"] for item in catalogue["checks"]
    ]
    for check in result["checks"]:
        assert check["status"] == "not_applicable"
        assert check["reason"] == "issuer_class_not_bank"
    assert result["limitations"] == [pack_base.DISPLAY_ONLY_LIMITATION]
    assert "issuer_class=industrial" in result["receipts"]
    assert result["coverage"]["not_applicable_fields"] == 16
    assert result["coverage"]["disclosure_coverage_state"] == "not_supplied"


def test_pk11_unknown_class_is_not_applicable(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_testbank_converter(monkeypatch, _testbank_events())
    result = produce_pack(
        "PK11", _pk11_bank_input(issuer_sic=None, sic_source=None)
    )
    assert result["applicability"]["state"] == "not_applicable"
    assert result["applicability"]["reason"] == "issuer_class_unknown"
    for row in result["fields"]:
        assert row["quality_state"] == "not_applicable"
        assert row["reason"] == "issuer_class_unknown"
    for check in result["checks"]:
        assert check["status"] == "not_applicable"
        assert check["reason"] == "issuer_class_unknown"
    assert "issuer_class=unknown" in result["receipts"]
    assert contract.validate_pack_result(result) == []


def test_pk11_synthetic_bank_ledger(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _produce_testbank(monkeypatch)
    assert contract.validate_pack_result(result) == []
    assert result["applicability"]["state"] == "applicable"
    assert result["applicability"]["reason"] == "applicability_rule_satisfied"
    assert "issuer_class=bank" in result["receipts"]

    total = _row(result, "provision_for_credit_losses_total")
    assert total["quality_state"] == "valued"
    assert total["value"] == "450"
    assert total["evidence_kind"] == "formula"
    assert total["formula_rule_id"] == "pk11.provision_total/v1"
    assert total["dependency_field_ids"] == [
        "credit_loss_expense_financing_receivables",
        "credit_loss_expense_off_balance_sheet",
    ]
    assert _row(result, "credit_loss_expense_financing_receivables")["concept"] == (
        "us-gaap:ProvisionForLoanLeaseAndOtherLosses"
    )
    assert _row(result, "credit_loss_expense_off_balance_sheet")["value"] == "50"
    assert _row(result, "allowance_for_credit_losses")["value"] == "1100"
    assert _row(result, "net_write_offs")["value"] == "300"
    assert _row(result, "loans_held_for_investment")["concept"] == (
        "us-gaap:LoansAndLeasesReceivableNetReportedAmount"
    )
    assert _row(result, "loans_held_for_investment")["value"] == "50000"
    assert _row(result, "cet1_capital")["concept"] == (
        "us-gaap:BankingRegulationCommonEquityTier1Capital"
    )
    assert _row(result, "risk_weighted_assets")["value"] == "40000"
    assert _row(result, "net_interest_income")["value"] == "2000"
    deposits = _row(result, "deposits")
    assert deposits["quality_state"] == "missing"
    assert deposits["reason"] == "missing_standard_fact:us-gaap:Deposits"
    for field_id in PK11_TABLE_CELL_FIELDS:
        row = _row(result, field_id)
        assert row["quality_state"] == "unsupported"
        assert row["evidence_kind"] == "table_cell"
        assert row["reason"] == "missing_dependency"
    assert result["coverage"] == {
        "valued_fields": 9,
        "missing_fields": 1,
        "unsupported_fields": 6,
        "not_evaluable_fields": 0,
        "not_applicable_fields": 0,
        "disclosure_coverage_state": "present",
    }

    rollforward = _check(result, "provision_vs_acl_rollforward")
    assert rollforward["status"] == "pass"
    assert rollforward["tolerance"] == "1"  # 1x10^-d, closing fact decimals 0
    acl = _check(result, "acl_coverage")
    assert acl["status"] == "pass"
    assert acl["tolerance"] is None
    assert acl["evidence_field_ids"] == [
        "allowance_for_credit_losses",
        "loans_held_for_investment",
    ]
    capital = _check(result, "capital_ratio_arithmetic")
    assert capital["status"] == "not_evaluable"
    assert capital["reason"] == "missing_dependency"
    assert capital["tolerance"] == "0.001"
    minimum = _check(result, "cet1_vs_minimum")
    assert minimum["status"] == "not_evaluable"
    assert minimum["reason"] == "missing_dependency"
    nii = _check(result, "nii_not_revenue")
    assert nii["status"] == "pass"
    assert nii["operands"] == ["net_interest_income", "core:revenue"]
    assert nii["evidence_field_ids"] == ["net_interest_income"]

    limitations = result["limitations"]
    assert limitations[0] == pack_base.DISPLAY_ONLY_LIMITATION
    assert "pk11.acl_coverage: 0.022000" in limitations
    assert "pk11.table_cell_reserved" in limitations
    assert any(
        line.startswith("pk11.industrial_basis_excluded:") for line in limitations
    )


def test_pk11_nii_equals_core_revenue_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _produce_testbank(
        monkeypatch,
        extra=(("core_revenue", "us-gaap:Revenues", "duration", "2000"),),
    )
    check = _check(result, "nii_not_revenue")
    assert check["status"] == "fail"
    # The frozen catalogue carries no bank_interest_not_contract_revenue
    # reason code, so the row keeps a null reason and the finding rides in
    # limitations.
    assert check["reason"] is None
    line = next(
        line
        for line in result["limitations"]
        if line.startswith("pk11.nii_not_revenue:")
    )
    assert "bank_interest_not_contract_revenue" in line
    assert contract.validate_pack_result(result) == []


def test_pk11_zero_loans_and_missing_off_balance_sheet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _produce_testbank(
        monkeypatch, drop=("prov_obs",), override={"loans": "0"}
    )
    acl = _check(result, "acl_coverage")
    assert acl["status"] == "not_evaluable"
    assert acl["reason"] == "division_by_zero"
    assert not any(
        line.startswith("pk11.acl_coverage:") for line in result["limitations"]
    )
    total = _row(result, "provision_for_credit_losses_total")
    assert total["quality_state"] == "not_evaluable"
    assert total["reason"] == "missing_dependency"
    assert (
        "pk11.provision_total: off-balance-sheet component absent; total not inferred"
        in result["limitations"]
    )
    # Independent of the zeroed/dropped operands, the rollforward still ties.
    assert _check(result, "provision_vs_acl_rollforward")["status"] == "pass"
    assert contract.validate_pack_result(result) == []


def test_pk11_synthetic_10q_bank_is_applicable(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _produce_testbank(monkeypatch, form="10-Q", por="2025-09-30")
    assert result["applicability"]["state"] == "applicable"
    assert result["applicability"]["reason"] == "applicability_rule_satisfied"
    assert "form=10-Q" in result["receipts"]
    assert _row(result, "allowance_for_credit_losses")["value"] == "1100"
    assert contract.validate_pack_result(result) == []


def test_pk11_form_outside_pack_forms(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _produce_testbank(monkeypatch, form="8-K")
    assert result["applicability"]["state"] == "not_applicable"
    assert result["applicability"]["reason"] == "form_outside_pack_forms"
    for row in result["fields"]:
        assert row["quality_state"] == "not_applicable"
        assert row["reason"] == "form_outside_pack_forms"
    for check in result["checks"]:
        assert check["status"] == "not_applicable"
        assert check["reason"] == "form_outside_pack_forms"
    assert contract.validate_pack_result(result) == []


def test_pk11_bank_production_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _produce_testbank(monkeypatch)
    second = _produce_testbank(monkeypatch)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["pack_content_sha256"] == second["pack_content_sha256"]


def test_pk11_a30_limitation_matches_core_catalogue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    yaml = pytest.importorskip("yaml")
    result = _produce_testbank(monkeypatch)
    line = next(
        line
        for line in result["limitations"]
        if line.startswith("pk11.industrial_basis_excluded:")
    )
    catalogue = yaml.safe_load(
        (
            ROOT
            / "config"
            / "fundamental_forensics"
            / "metrics"
            / "v1"
            / "metric_catalog.yaml"
        ).read_text(encoding="utf-8")
    )
    excluded = [
        row["metric_id"]
        for row in catalogue["metrics"]
        if "bank" in ((row.get("applicability") or {}).get("excluded_classes") or [])
    ]
    assert line == "pk11.industrial_basis_excluded: " + ",".join(excluded)


def test_base_pack_envelopes_identical_after_pk11() -> None:
    for pack_id, query, digest in (
        ("PK06", QUERY, PK06_ENVELOPE_SHA256),
        ("PK01", PK01_QUERY, PK01_ENVELOPE_SHA256),
    ):
        result = produce_pack(pack_id, _pack_input(query=query))
        payload = json.dumps(
            result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        assert sha256(payload.encode("utf-8")).hexdigest() == digest
