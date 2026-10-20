"""Specialist pack producer framework + PK06/PK01/PK12 producers over the AAPL 10-K fixture.

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

PK12 (biotech cash/R&D/financing) is a NEGATIVE issuer on this AAPL fixture
(SIC 3571, revenue valued), so the positive path is proven on a synthetic
in-test inline-XBRL package admitted by the same strict parser path as the
golden fixture — never on a hand-built ledger. The two text-span rows stay
``unsupported`` at this producer version (the framework reserves span
evidence for a later lane), so ``financing_disclosed_not_forecast`` passes on
``equity_financing_proceeds`` alone.
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
from engine.fundamental_forensics.statement_graph import (
    GoldenFilingPackage,
    load_golden_aapl_package,
)

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
    assert registered_pack_ids() == ("PK01", "PK06", "PK12")
    assert set(PACK_PRODUCERS) == {"PK01", "PK06", "PK12"}
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
        "engine/fundamental_forensics/specialist_packs/pk12_biotech.py",
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


# 19. PK12: synthetic in-test biotech package ---------------------------------
#
# A minimal inline-XBRL 1.1 10-K admitted by the same strict collector
# parser path as the golden fixture (never a hand-built ledger), carrying the
# frozen §TESTS-2 facts: cash 120, sti 80, R&D 60, opCF -100, finCF 150,
# capex 8, proceeds 150, plus the narrative the span lane would eventually
# locate ("at-the-market offering", "sufficient to fund operations for the
# next twelve months").

SYN_BIO_CIK = "0000000003"
SYN_BIO_DOC = "testbio-20251231.htm"
SYN_BIO_ENTITY = {
    "entity_id": SYN_BIO_CIK,
    "cik": SYN_BIO_CIK,
    "ticker": "TESTBIO",
    "name": "TESTBIO CORP",
    "identity_basis": "golden_filing_package_fixture_v1",
    "source_entity_id": SYN_BIO_CIK,
}
PK12_QUERY = {**QUERY, "requested_metrics": ["cash_runway"]}
# A.7: sha256 of the canonical JSON bytes of each envelope under this
# module's own inputs. PK01's digest is the BASE value (PK12 edits must not
# move it); PK12's digest pins this producer's byte-determinism.
PK01_ENVELOPE_SHA256 = (
    "235a3ce6e9681e0bd3c3e284bc57cf972809ebe06e24a61bc5dba17a41e40a74"
)
PK12_AAPL_ENVELOPE_SHA256 = (
    "e76d3cbe85619224b81a288b6b368f8b5505086535c6293b0273d4dd2be87a1f"
)

_SYN_BIO_FACTS = (
    ("us-gaap:CashAndCashEquivalentsAtCarryingValue", "c-inst", "120", ""),
    ("us-gaap:ShortTermInvestments", "c-inst", "80", ""),
    ("us-gaap:ResearchAndDevelopmentExpense", "c-fy", "60", ""),
    (
        "us-gaap:NetCashProvidedByUsedInOperatingActivities",
        "c-fy",
        "100",
        ' sign="-"',
    ),
    ("us-gaap:NetCashProvidedByUsedInFinancingActivities", "c-fy", "150", ""),
    ("us-gaap:PaymentsToAcquirePropertyPlantAndEquipment", "c-fy", "8", ""),
    ("us-gaap:ProceedsFromIssuanceOfCommonStock", "c-fy", "150", ""),
)
_SYN_CONTEXT_INST = (
    '<xbrli:context id="c-inst"><xbrli:entity><xbrli:identifier'
    ' scheme="http://www.sec.gov/CIK">'
    f'{SYN_BIO_CIK}</xbrli:identifier></xbrli:entity><xbrli:period>'
    "<xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>"
)
_SYN_CONTEXT_FY = (
    '<xbrli:context id="c-fy"><xbrli:entity><xbrli:identifier'
    ' scheme="http://www.sec.gov/CIK">'
    f'{SYN_BIO_CIK}</xbrli:identifier></xbrli:entity><xbrli:period>'
    "<xbrli:startDate>2025-01-01</xbrli:startDate>"
    "<xbrli:endDate>2025-12-31</xbrli:endDate></xbrli:period></xbrli:context>"
)


def _biotech_document(facts: tuple[tuple[str, str, str, str], ...]) -> bytes:
    rows = "\n".join(
        f"<tr><td>item {index}</td><td>"
        f'<ix:nonFraction id="f-{index}" name="{qname}"'
        f' contextRef="{context}" unitRef="usd" decimals="0"{sign}>{value}'
        "</ix:nonFraction></td></tr>"
        for index, (qname, context, value, sign) in enumerate(facts, start=1)
    )
    template = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml"'
        ' xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"'
        ' xmlns:xbrli="http://www.xbrl.org/2003/instance"'
        ' xmlns:iso4217="http://www.xbrl.org/2003/iso4217"'
        ' xmlns:us-gaap="http://fasb.org/us-gaap/2025">\n'
        "<head><title>TESTBIO 10-K</title></head>\n<body>\n"
        '<div style="display:none"><ix:header><ix:resources>\n'
        f"{_SYN_CONTEXT_INST}\n{_SYN_CONTEXT_FY}\n"
        '<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure>'
        "</xbrli:unit>\n</ix:resources></ix:header></div>\n"
        "<p>The registrant maintains an at-the-market offering program and"
        " believes existing resources are sufficient to fund operations for"
        " the next twelve months.</p>\n"
        f"<table>\n{rows}\n</table>\n</body></html>\n"
    )
    return template.encode("utf-8")


def _biotech_package(
    facts: tuple[tuple[str, str, str, str], ...] = _SYN_BIO_FACTS,
    *,
    form: str = "10-K",
) -> GoldenFilingPackage:
    document = _biotech_document(facts)
    manifest = {
        "entity_id": SYN_BIO_CIK,
        "cik": SYN_BIO_CIK,
        "legal_name": "TESTBIO CORP",
        "form": form,
        "period_of_report": "2025-12-31",
        "filing_date": "2026-02-15",
        "accession": "0000000003-26-000010",
        "primary_document": SYN_BIO_DOC,
        "source_accepted_at": "2026-02-15T16:00:00Z",
        "fixture_recorded_at": "2026-02-15T16:05:00Z",
        "members": [
            {
                "name": SYN_BIO_DOC,
                "state": "stored",
                "content_sha256": sha256(document).hexdigest(),
            }
        ],
    }
    return GoldenFilingPackage(
        manifest=manifest, members={SYN_BIO_DOC: document}
    )


def _pk12_input(**overrides) -> PackInput:
    defaults = dict(
        packages=(_biotech_package(),),
        entity=SYN_BIO_ENTITY,
        query=PK12_QUERY,
        issuer_sic="2836",
        sic_source="sec_submissions",
    )
    defaults.update(overrides)
    return PackInput(**defaults)


def _aapl_pk12_input(**overrides) -> PackInput:
    defaults = dict(
        packages=(load_golden_aapl_package(ROOT, accession=ACCESSION),),
        entity=ENTITY,
        query=PK12_QUERY,
        issuer_sic="3571",
        sic_source="sec_submissions",
    )
    defaults.update(overrides)
    return PackInput(**defaults)


@pytest.fixture(scope="module")
def pk12_biotech_result() -> dict:
    return produce_pack("PK12", _pk12_input())


# 20. PK12 on AAPL: the honest negative (B.4) ---------------------------------


def test_pk12_aapl_is_not_applicable_outside_biotech_sics() -> None:
    result = produce_pack("PK12", _aapl_pk12_input())
    assert result["applicability"] == {
        "state": "not_applicable",
        "reason": "sic_outside_biotech_codes",
        "rule_id": "pack.pk12.applicability/v1",
        "sic": "3571",
        "sic_source": "sec_submissions",
    }
    assert len(result["fields"]) == 9
    for row in result["fields"]:
        assert row["quality_state"] == "not_applicable"
        assert row["non_value_state"] == "not_applicable"
        assert row["coverage_state"] == "not_applicable_period"
        assert row["reason"] == "sic_outside_biotech_codes"
        assert row["value"] is None and row["text_value"] is None
    assert len(result["checks"]) == 4
    for check in result["checks"]:
        assert check["status"] == "not_applicable"
        assert check["reason"] == "sic_outside_biotech_codes"
    assert result["coverage"] == {
        "valued_fields": 0,
        "missing_fields": 0,
        "unsupported_fields": 0,
        "not_evaluable_fields": 0,
        "not_applicable_fields": 9,
        "disclosure_coverage_state": "not_supplied",
    }
    assert result["limitations"] == [pack_base.DISPLAY_ONLY_LIMITATION]
    assert "issuer_class=industrial" in result["receipts"]
    assert "sic_in_biotech_set=false" in result["receipts"]
    assert "pre_revenue_test=false" in result["receipts"]
    assert contract.validate_pack_result(result) == []
    # §TESTS 1: BASE packs plus PK12, not the full twelve at this BASE.
    assert registered_pack_ids() == ("PK01", "PK06", "PK12")


def test_pk12_aapl_envelope_digest_is_pinned() -> None:
    result = produce_pack("PK12", _aapl_pk12_input())
    payload = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert sha256(payload.encode("utf-8")).hexdigest() == PK12_AAPL_ENVELOPE_SHA256


def test_pk12_biotech_coded_aapl_probe_is_non_positive_burn() -> None:
    # B.4 parenthetical: the entity SIC is overridable pack input, so the
    # probe proves that even a biotech-coded AAPL yields non_positive_burn
    # (opCF 111,482e6 makes the burn basis zero-or-negative).
    result = produce_pack("PK12", _aapl_pk12_input(issuer_sic="2836"))
    assert result["applicability"]["state"] == "applicable"
    assert "sic_in_biotech_set=true" in result["receipts"]
    assert result["coverage"]["valued_fields"] == 5
    runway = _row(result, "cash_runway_quarters")
    assert runway["quality_state"] == "not_evaluable"
    assert runway["non_value_state"] == "not_evaluable"
    assert runway["reason"] == "non_positive_burn"
    assert runway["value"] is None
    for check_id in ("cash_runway_quarters", "runway_months_annual_fcf_div_12"):
        check = _check(result, check_id)
        assert check["status"] == "not_evaluable"
        assert check["reason"] == "non_positive_burn"
    assert _check(result, "rd_to_cash")["status"] == "pass"
    assert "pk12.rd_to_cash: 0.961485" in result["limitations"]
    assert _check(result, "financing_disclosed_not_forecast")["status"] == (
        "not_evaluable"
    )
    assert _row(result, "equity_financing_proceeds")["reason"] == (
        "missing_standard_fact:us-gaap:ProceedsFromIssuanceOfCommonStock"
    )
    assert contract.validate_pack_result(result) == []


# 21. PK12 synthetic biotech: the positive path (§TESTS 2) --------------------


def test_pk12_biotech_positive_path_validates(pk12_biotech_result: dict) -> None:
    result = pk12_biotech_result
    assert contract.validate_pack_result(result) == []
    assert result["applicability"]["state"] == "applicable"
    assert result["applicability"]["reason"] == "applicability_rule_satisfied"
    catalogue = contract.load_pack_schema("PK12")
    assert [row["field_id"] for row in result["fields"]] == [
        item["field_id"] for item in catalogue["fields"]
    ]
    assert [row["check_id"] for row in result["checks"]] == [
        item["check_id"] for item in catalogue["checks"]
    ]
    assert "sic_in_biotech_set=true" in result["receipts"]


def test_pk12_biotech_valued_rows(pk12_biotech_result: dict) -> None:
    result = pk12_biotech_result
    valued = {
        "cash_and_cash_equivalents": "120",
        "short_term_investments": "80",
        "research_and_development_expense": "60",
        "net_cash_from_operating_activities": "-100",
        "net_cash_from_financing_activities": "150",
        "equity_financing_proceeds": "150",
    }
    for field_id, value in valued.items():
        row = _row(result, field_id)
        assert row["quality_state"] == "valued"
        assert row["value"] == value
        assert row["evidence_kind"] == "xbrl_fact"
        assert row["unit"] == "USD"
        assert row["source_occurrence_ids"]
        assert row["mapping_rule_id"] == f"PK12.{field_id}.fact/v1"
        assert row["mapping_rule_digest"]
    runway = _row(result, "cash_runway_quarters")
    assert runway["quality_state"] == "valued"
    assert runway["evidence_kind"] == "formula"
    assert runway["required_evidence_kind"] == "formula"
    assert runway["formula_rule_id"] == "pk12.cash_runway_quarters/v1"
    assert runway["dependency_field_ids"] == [
        "cash_and_cash_equivalents",
        "short_term_investments",
        "net_cash_from_operating_activities",
    ]
    assert runway["unit"] == "quarters"
    # (120 + 80) / (100 / 4) quantized 6 dp: Decimal 8.000000; the canonical
    # row text strips trailing zeros.
    assert Decimal(runway["value"]) == Decimal("8.000000")
    assert runway["value"] == "8"
    for field_id in ("atm_or_shelf_span", "going_concern_or_liquidity_span"):
        row = _row(result, field_id)
        assert row["quality_state"] == "unsupported"
        assert row["non_value_state"] == "unsupported"
        assert row["evidence_kind"] == "text_span"
        assert row["required_evidence_kind"] == "text_span"
        assert row["reason"] == "missing_dependency"
        assert row["text_value"] is None
    assert result["coverage"] == {
        "valued_fields": 7,
        "missing_fields": 0,
        "unsupported_fields": 2,
        "not_evaluable_fields": 0,
        "not_applicable_fields": 0,
        "disclosure_coverage_state": "present",
    }


def test_pk12_biotech_checks_and_limitations(pk12_biotech_result: dict) -> None:
    result = pk12_biotech_result
    runway_check = _check(result, "cash_runway_quarters")
    assert runway_check["status"] == "pass"
    assert runway_check["reason"] is None
    assert runway_check["operands"] == [
        "cash_runway_quarters",
        "cash_and_cash_equivalents",
        "short_term_investments",
        "net_cash_from_operating_activities",
    ]
    fcf_check = _check(result, "runway_months_annual_fcf_div_12")
    assert fcf_check["status"] == "pass"
    assert fcf_check["operands"] == [
        "cash_runway_quarters",
        "cash_and_cash_equivalents",
        "net_cash_from_operating_activities",
        "core:capital_expenditures",
    ]
    rd_check = _check(result, "rd_to_cash")
    assert rd_check["status"] == "pass"
    assert rd_check["evidence_field_ids"] == [
        "research_and_development_expense",
        "cash_and_cash_equivalents",
    ]
    financing_check = _check(result, "financing_disclosed_not_forecast")
    assert financing_check["status"] == "pass"
    assert financing_check["kind"] == "qualitative_presence"
    # 200 / (108 / 12) and 60 / 120, quantized 6 dp, ride the limitations.
    assert "pk12.runway_months_fcf: 22.222222" in result["limitations"]
    assert "pk12.rd_to_cash: 0.500000" in result["limitations"]
    assert any(
        item.startswith("runway_months_annual_fcf_div_12:")
        for item in result["limitations"]
    )


def test_pk12_production_is_deterministic() -> None:
    first = produce_pack("PK12", _pk12_input())
    second = produce_pack("PK12", _pk12_input())
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["pack_content_sha256"] == second["pack_content_sha256"]


# 22. PK12 pre-revenue applicability (§TESTS 3) --------------------------------


def test_pk12_pre_revenue_path_admits_non_biotech_sic() -> None:
    result = produce_pack("PK12", _pk12_input(issuer_sic="7372"))
    assert result["applicability"]["state"] == "applicable"
    assert result["applicability"]["reason"] == "applicability_rule_satisfied"
    assert "sic_in_biotech_set=false" in result["receipts"]
    assert "pre_revenue_test=true" in result["receipts"]
    assert contract.validate_pack_result(result) == []


def test_pk12_valued_revenue_blocks_pre_revenue_path() -> None:
    facts = (
        *_SYN_BIO_FACTS,
        ("us-gaap:Revenues", "c-fy", "10", ""),
    )
    result = produce_pack(
        "PK12",
        _pk12_input(packages=(_biotech_package(facts),), issuer_sic="7372"),
    )
    assert result["applicability"]["state"] == "not_applicable"
    assert result["applicability"]["reason"] == "sic_outside_biotech_codes"
    assert "pre_revenue_test=false" in result["receipts"]
    for row in result["fields"]:
        assert row["quality_state"] == "not_applicable"
        assert row["reason"] == "sic_outside_biotech_codes"
    for check in result["checks"]:
        assert check["status"] == "not_applicable"
        assert check["reason"] == "sic_outside_biotech_codes"
    assert contract.validate_pack_result(result) == []


# 23. PK12 non-positive burn (§TESTS 4) ----------------------------------------


def test_pk12_non_positive_burn_is_typed() -> None:
    facts = (
        _SYN_BIO_FACTS[0],
        _SYN_BIO_FACTS[1],
        _SYN_BIO_FACTS[2],
        ("us-gaap:NetCashProvidedByUsedInOperatingActivities", "c-fy", "100", ""),
        *_SYN_BIO_FACTS[4:],
    )
    result = produce_pack("PK12", _pk12_input(packages=(_biotech_package(facts),)))
    runway = _row(result, "cash_runway_quarters")
    assert runway["quality_state"] == "not_evaluable"
    assert runway["non_value_state"] == "not_evaluable"
    assert runway["reason"] == "non_positive_burn"
    assert runway["value"] is None
    assert runway["formula_rule_id"] == "pk12.cash_runway_quarters/v1"
    for check_id in ("cash_runway_quarters", "runway_months_annual_fcf_div_12"):
        check = _check(result, check_id)
        assert check["status"] == "not_evaluable"
        assert check["reason"] == "non_positive_burn"
    assert _check(result, "rd_to_cash")["status"] == "pass"
    assert _check(result, "financing_disclosed_not_forecast")["status"] == "pass"
    assert result["coverage"]["not_evaluable_fields"] == 1
    assert result["coverage"]["valued_fields"] == 6
    assert contract.validate_pack_result(result) == []


# 24. PK12 form gate (§TESTS 5) -------------------------------------------------


def test_pk12_10q_is_outside_pack_forms() -> None:
    result = produce_pack(
        "PK12", _pk12_input(packages=(_biotech_package(form="10-Q"),))
    )
    assert result["applicability"]["state"] == "not_applicable"
    assert result["applicability"]["reason"] == "form_outside_pack_forms"
    for row in result["fields"]:
        assert row["quality_state"] == "not_applicable"
        assert row["reason"] == "form_outside_pack_forms"
    for check in result["checks"]:
        assert check["status"] == "not_applicable"
        assert check["reason"] == "form_outside_pack_forms"
    assert result["coverage"]["disclosure_coverage_state"] == "not_supplied"
    assert contract.validate_pack_result(result) == []


# 25. BASE-pack invariance (§TESTS 6) -------------------------------------------


def test_base_pack_envelopes_unchanged_by_pk12_edits() -> None:
    pk06 = produce_pack("PK06", _pack_input())
    pk01 = produce_pack("PK01", _pk01_input())
    for result, expected in (
        (pk06, PK06_ENVELOPE_SHA256),
        (pk01, PK01_ENVELOPE_SHA256),
    ):
        payload = json.dumps(
            result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        assert sha256(payload.encode("utf-8")).hexdigest() == expected


# 26. PK12 CLI -------------------------------------------------------------------


def test_pk12_cli_writes_valid_envelope(tmp_path: Path) -> None:
    entity_file = tmp_path / "entity.json"
    query_file = tmp_path / "query.json"
    out_file = tmp_path / "pk12.json"
    entity_file.write_text(json.dumps(ENTITY), encoding="utf-8")
    query_file.write_text(json.dumps(PK12_QUERY), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "fif_specialist_packs.py"),
            "--pack",
            "PK12",
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
    assert envelope["applicability"]["state"] == "not_applicable"
    assert envelope["applicability"]["reason"] == "sic_outside_biotech_codes"
    assert len(envelope["fields"]) == 9
    assert "sic_in_biotech_set=false" in envelope["receipts"]
