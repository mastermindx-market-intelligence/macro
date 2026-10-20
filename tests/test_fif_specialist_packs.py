"""Specialist pack producer framework + PK06/PK01/PK02/PK11/PK12/PK09/PK04 producers over the AAPL 10-K fixture.

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
debt concepts are absent standard facts. For PK02 the fixture tags the
allocated SBC expense, both weighted-average share counts and EPS figures
(each twice, identically), the dei cover share count at 2025-10-17, the
balance-sheet shares issued, the repurchase payments, the p20 incremental
dilutive shares and net income; the income-statement-location SBC breakdown
is not tagged, the antidilutive table exists only for FY2023, and capitalized
SBC has no frozen standard alias.

PK12 (biotech cash/R&D/financing) is a NEGATIVE issuer on this AAPL fixture
(SIC 3571, revenue valued), so the positive path is proven on a synthetic
in-test inline-XBRL package admitted by the same strict parser path as the
golden fixture — never on a hand-built ledger. The two text-span rows stay
``unsupported`` at this producer version (the framework reserves span
evidence for a later lane), so ``financing_disclosed_not_forecast`` passes on
``equity_financing_proceeds`` alone.

PK11 (financial-institution credit, capital and liquidity) is likewise a
NEGATIVE issuer here; its bank path is proven on a synthetic in-test ledger.

PK09 (controls, auditor, going concern) is text-span driven: the narrative
locator over the AAPL 10-K primary document plus synthetic 10-Q/material-
weakness probes.

PK04 (revenue recognition and contract balances) is fixture-verified on the
AAPL 10-K through the definition linkbase axis groups (A.3), the grouped sum
identity (A.5) and the opening-instant rollforward bound (A.1).
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
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
from engine.fundamental_forensics.specialist_packs import narrative as pack_narrative
from engine.fundamental_forensics.specialist_packs import pk06_leases
from engine.fundamental_forensics.specialist_packs import pk09_controls
from engine.fundamental_forensics import specialist_pack_contract as contract
from engine.fundamental_forensics import ixbrl_raw_ledger as ixbrl_module
from engine.fundamental_forensics.ixbrl_raw_ledger import (
    ConversionReport,
    FilingConversionReceipt,
)
from engine.fundamental_forensics.raw_ledger import FactContext, RawFactLedger
from engine.fundamental_forensics.synthetic_filing_package import (
    filing as synthetic_filing,
)
from engine.fundamental_forensics.synthetic_filing_package import usd_fact
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
    # PK03 lane: the BASE set plus PK03, sorted (never a removal).
    assert registered_pack_ids() == (
        "PK01", "PK02", "PK03", "PK04", "PK06", "PK09", "PK11", "PK12",
    )
    assert set(PACK_PRODUCERS) == {
        "PK01", "PK02", "PK03", "PK04", "PK06", "PK09", "PK11", "PK12",
    }
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
        "engine/fundamental_forensics/specialist_packs/pk02_sbc.py",
        "engine/fundamental_forensics/specialist_packs/narrative.py",
        "engine/fundamental_forensics/specialist_packs/pk09_controls.py",
        "engine/fundamental_forensics/specialist_packs/pk11_bank.py",
        "engine/fundamental_forensics/specialist_packs/pk12_biotech.py",
        "engine/fundamental_forensics/specialist_packs/pk04_revenue.py",
        "engine/fundamental_forensics/specialist_packs/definition_linkbase.py",
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


# 19. PK02: stock-based compensation and dilution -----------------------------
#
# Fixture-verified through the raw ledger (FY2025 = 2024-09-29..2025-09-27):
# the values below are the facts' own scale (USD units / whole shares).

from engine.fundamental_forensics.specialist_packs import pk02_sbc  # noqa: E402

PK02_QUERY = {**QUERY, "requested_metrics": ["stock_compensation"]}
# A.6: sha256 of the canonical JSON bytes of the PK01 envelope recorded at
# the PK02 lane base; PK02 edits must not move it (PK06 has its own pin above).
PK01_ENVELOPE_SHA256 = (
    "235a3ce6e9681e0bd3c3e284bc57cf972809ebe06e24a61bc5dba17a41e40a74"
)


def _pk02_input(**overrides) -> PackInput:
    defaults = dict(
        packages=(load_golden_aapl_package(ROOT, accession=ACCESSION),),
        entity=ENTITY,
        query=PK02_QUERY,
        issuer_sic="3571",
        sic_source="sec_submissions",
    )
    defaults.update(overrides)
    return PackInput(**defaults)


@pytest.fixture(scope="module")
def pk02_result() -> dict:
    return produce_pack("PK02", _pk02_input())


def _pk02_probe(field_mappings: dict | None = None) -> dict:
    producer = pk02_sbc.PRODUCER
    if field_mappings:
        producer = replace(
            producer,
            field_mappings={**producer.field_mappings, **field_mappings},
        )
    return pack_base.produce_pack_result(producer, _pk02_input())


def test_pk02_result_passes_contract_validator(pk02_result: dict) -> None:
    assert contract.validate_pack_result(pk02_result) == []


def test_pk02_result_passes_jsonschema_envelope(pk02_result: dict) -> None:
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
        Draft202012Validator(schema, registry=registry).iter_errors(pk02_result)
    )
    assert errors == []


def test_pk02_rows_follow_catalogue_order_with_thirteen_rows(
    pk02_result: dict,
) -> None:
    catalogue = contract.load_pack_schema("PK02")
    produced = [row["field_id"] for row in pk02_result["fields"]]
    assert produced == [item["field_id"] for item in catalogue["fields"]]
    assert len(produced) == 13  # no repeated rows on this single-class issuer
    assert [row["check_id"] for row in pk02_result["checks"]] == [
        item["check_id"] for item in catalogue["checks"]
    ]


def test_pk02_sbc_expense_total(pk02_result: dict) -> None:
    row = _row(pk02_result, "sbc_expense_total")
    assert row["quality_state"] == "valued"
    assert row["value"] == "12863000000"
    assert row["concept"] == "us-gaap:AllocatedShareBasedCompensationExpense"
    assert row["unit"] == "USD"
    assert row["evidence_kind"] == "xbrl_fact"
    assert row["mapping_rule_id"] == "PK02.sbc_expense_total.fact/v1"


def test_pk02_sbc_allocated_by_line_is_typed_absence(pk02_result: dict) -> None:
    row = _row(pk02_result, "sbc_allocated_by_line")
    assert row["quality_state"] == "missing"
    assert row["non_value_state"] == "missing"
    assert row["value"] is None and row["text_value"] is None
    assert row["reason"] == (
        "missing_standard_fact:us-gaap:AllocatedShareBasedCompensationExpense"
    )
    assert (
        "sbc_allocated_by_line: no IncomeStatementLocationAxis members tagged"
        in pk02_result["limitations"]
    )


def test_pk02_weighted_average_shares(pk02_result: dict, ledger) -> None:
    basic = _row(pk02_result, "weighted_average_shares_basic")
    assert basic["value"] == "14948500000"
    assert basic["unit"] == "shares"
    # Two identical occurrences are not a conflict; both ids are listed.
    assert len(basic["source_occurrence_ids"]) == 2
    diluted = _row(pk02_result, "weighted_average_shares_diluted")
    assert diluted["value"] == "15004697000"
    assert len(diluted["source_occurrence_ids"]) == 2
    for row in (basic, diluted):
        for occurrence_id in row["source_occurrence_ids"]:
            assert ledger.by_id(occurrence_id) is not None


def test_pk02_eps_rows(pk02_result: dict) -> None:
    assert _row(pk02_result, "eps_basic")["value"] == "7.49"
    assert _row(pk02_result, "eps_diluted")["value"] == "7.46"
    for field_id in ("eps_basic", "eps_diluted"):
        row = _row(pk02_result, field_id)
        assert row["unit"] == "USD/shares"
        assert len(row["source_occurrence_ids"]) == 2


def test_pk02_antidilutive_is_typed_absence(pk02_result: dict) -> None:
    row = _row(pk02_result, "antidilutive_securities_excluded")
    # The fixture tags this concept only for FY2023, never FY2025.
    assert row["quality_state"] == "missing"
    assert row["reason"] == (
        "missing_standard_fact:us-gaap:AntidilutiveSecuritiesExcludedFrom"
        "ComputationOfEarningsPerShareAmount"
    )
    check = _check(pk02_result, "antidilutive_table_total_vs_rows")
    assert check["status"] == "not_evaluable"
    assert check["reason"] == "missing_dependency"
    assert check["evidence_field_ids"] == ["antidilutive_securities_excluded"]


def test_pk02_cover_and_parenthetical(pk02_result: dict) -> None:
    cover = _row(pk02_result, "shares_outstanding_cover")
    assert cover["value"] == "14776353000"
    assert cover["period"] == {"kind": "instant", "end": "2025-10-17"}
    assert cover["taxonomy"] == "dei"
    assert cover["concept"] == "dei:EntityCommonStockSharesOutstanding"
    parenthetical = _row(pk02_result, "shares_issued_parenthetical")
    assert parenthetical["value"] == "14773260000"
    assert parenthetical["period"] == {"kind": "instant", "end": "2025-09-27"}
    assert parenthetical["taxonomy"] == "us-gaap"


def test_pk02_share_repurchase_uses_first_alias(pk02_result: dict) -> None:
    row = _row(pk02_result, "share_repurchase_amount")
    assert row["value"] == "90711000000"
    assert row["concept"] == "us-gaap:PaymentsForRepurchaseOfCommonStock"


def test_pk02_sbc_capitalized_is_declared_unmapped(pk02_result: dict) -> None:
    row = _row(pk02_result, "sbc_capitalized")
    assert row["quality_state"] == "unsupported"
    assert row["non_value_state"] == "unsupported"
    assert row["coverage_state"] == "unmapped"
    assert row["reason"] == "missing_dependency"
    assert row["evidence_kind"] == "xbrl_fact"
    assert row["required_evidence_kind"] == "xbrl_fact"
    assert row["value"] is None
    assert (
        "sbc_capitalized: no standard us-gaap alias frozen; issuer extensions"
        " need a core-catalog ruling" in pk02_result["limitations"]
    )


def test_pk02_dilutive_increment_uses_p20_alias(pk02_result: dict) -> None:
    row = _row(pk02_result, "dilutive_securities_increment")
    assert row["value"] == "56197000"
    assert row["concept"] == (
        "us-gaap:IncrementalCommonSharesAttributableToShareBasedPayment"
        "Arrangements"
    )


def test_pk02_net_income_lists_every_identical_occurrence(
    pk02_result: dict, ledger
) -> None:
    row = _row(pk02_result, "net_income_available_to_common")
    assert row["value"] == "112010000000"
    assert row["concept"] == "us-gaap:NetIncomeLoss"
    assert len(row["source_occurrence_ids"]) >= 2
    for occurrence_id in row["source_occurrence_ids"]:
        assert ledger.by_id(occurrence_id) is not None


def test_pk02_basic_to_diluted_passes_with_tolerance(pk02_result: dict) -> None:
    check = _check(pk02_result, "basic_to_diluted_reconciliation")
    assert check["status"] == "pass"
    # 14,948,500,000 + 56,197,000 = 15,004,697,000 exactly; min decimals -3.
    assert check["tolerance"] == "1000"
    assert check["evidence_field_ids"] == [
        "weighted_average_shares_basic",
        "dilutive_securities_increment",
        "weighted_average_shares_diluted",
    ]


def test_pk02_eps_identity_passes_with_tolerance(pk02_result: dict) -> None:
    check = _check(pk02_result, "eps_identity")
    assert check["status"] == "pass"
    assert check["tolerance"] == "0.01"
    assert check["evidence_field_ids"] == [
        "net_income_available_to_common",
        "weighted_average_shares_basic",
        "eps_basic",
        "weighted_average_shares_diluted",
        "eps_diluted",
    ]


def test_pk02_per_class_shares_is_period_mismatch(pk02_result: dict) -> None:
    check = _check(pk02_result, "per_class_shares_vs_cover")
    assert check["status"] == "not_evaluable"
    assert check["reason"] == "unit_mismatch"
    assert (
        "per_class_shares_vs_cover: cover date differs from balance-sheet date"
        in pk02_result["limitations"]
    )


def test_pk02_coverage_counts(pk02_result: dict) -> None:
    assert pk02_result["coverage"] == {
        "valued_fields": 10,
        "missing_fields": 2,
        "unsupported_fields": 1,
        "not_evaluable_fields": 0,
        "not_applicable_fields": 0,
        "disclosure_coverage_state": "present",
    }


# 20. PK02 determinism and PK06/PK01 invariance (A.6) -------------------------


def test_pk02_production_is_deterministic() -> None:
    first = produce_pack("PK02", _pk02_input())
    second = produce_pack("PK02", _pk02_input())
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["pack_content_sha256"] == second["pack_content_sha256"]


def test_pk01_envelope_digest_unchanged_by_pk02_edits() -> None:
    result = produce_pack("PK01", _pk01_input())
    payload = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert sha256(payload.encode("utf-8")).hexdigest() == PK01_ENVELOPE_SHA256


# 21. PK02 A.2/A.4/A.5 framework semantics (probes + synthetic operands) ------


def test_pk02_a2_emits_consolidated_row_then_members() -> None:
    probe = _pk02_probe(
        {
            "antidilutive_securities_excluded": pack_base.FactMapping(
                ("us-gaap:NetIncomeLoss",),
                optional_axes=("us-gaap:StatementEquityComponentsAxis",),
            )
        }
    )
    rows = _rows(probe, "antidilutive_securities_excluded")
    assert len(rows) == 2
    assert rows[0]["dimensions"] == []  # consolidated row first
    assert rows[0]["value"] == "112010000000"
    assert len(rows[0]["source_occurrence_ids"]) == 4
    assert rows[1]["dimensions"][0]["axis"] == (
        "us-gaap:StatementEquityComponentsAxis"
    )
    assert rows[1]["value"] == "112010000000"
    for row in rows:
        assert row["field_id"] == "antidilutive_securities_excluded"
        assert row["mapping_rule_id"] == (
            "PK02.antidilutive_securities_excluded.fact/v1"
        )
    # Repeated rows sit at the catalogue position, adjacent.
    produced = [row["field_id"] for row in probe["fields"]]
    position = produced.index("antidilutive_securities_excluded")
    assert produced[position + 1] == "antidilutive_securities_excluded"
    assert contract.validate_pack_result(probe) == []


def test_pk02_a2_consolidated_row_false_keeps_members_only() -> None:
    probe = _pk02_probe(
        {
            "antidilutive_securities_excluded": pack_base.FactMapping(
                ("us-gaap:NetIncomeLoss",),
                optional_axes=("us-gaap:StatementEquityComponentsAxis",),
                consolidated_row=False,
            )
        }
    )
    rows = _rows(probe, "antidilutive_securities_excluded")
    assert len(rows) == 1
    assert rows[0]["dimensions"]  # the member row, never the consolidated one
    check = _check(probe, "antidilutive_table_total_vs_rows")
    # A.4: no consolidated row -> not_evaluable, never a member-only pass.
    assert check["status"] == "not_evaluable"
    assert check["reason"] == "missing_dependency"
    assert contract.validate_pack_result(probe) == []


def test_pk02_a2_foreign_axis_only_is_disallowed_dimension() -> None:
    # This concept's FY2025 facts exist only under StatementEquityComponentsAxis,
    # which the probe does not admit.
    probe = _pk02_probe(
        {
            "antidilutive_securities_excluded": pack_base.FactMapping(
                (
                    "us-gaap:AdjustmentsRelatedToTaxWithholdingForShare"
                    "BasedCompensation",
                ),
                optional_axes=("us-gaap:StatementClassOfStockAxis",),
            )
        }
    )
    rows = _rows(probe, "antidilutive_securities_excluded")
    assert len(rows) == 1
    assert rows[0]["quality_state"] == "missing"
    assert rows[0]["reason"] == "disallowed_dimension"


def test_pk02_a4_total_vs_rows_passes_when_members_sum_to_total() -> None:
    probe = _pk02_probe(
        {
            "antidilutive_securities_excluded": pack_base.FactMapping(
                ("us-gaap:NetIncomeLoss",),
                optional_axes=("us-gaap:StatementEquityComponentsAxis",),
            )
        }
    )
    check = _check(probe, "antidilutive_table_total_vs_rows")
    assert check["status"] == "pass"
    assert check["tolerance"] == "1000000"  # min decimals -6 across the rows


def test_pk02_a4_total_vs_rows_fails_when_members_differ() -> None:
    probe = _pk02_probe(
        {
            "antidilutive_securities_excluded": pack_base.FactMapping(
                ("us-gaap:StockRepurchasedAndRetiredDuringPeriodValue",),
                optional_axes=("us-gaap:StatementEquityComponentsAxis",),
            )
        }
    )
    # Consolidated 89,300,000,000 (dec -8) vs member 90,052,000,000 (dec -6):
    # the 752,000,000 gap exceeds the 100,000,000 tolerance.
    check = _check(probe, "antidilutive_table_total_vs_rows")
    assert check["status"] == "fail"
    assert check["tolerance"] == "100000000"
    assert contract.validate_pack_result(probe) == []


def _share_operand(field_id: str, value: str, decimals: int, rows: list) -> object:
    return pack_base.RuleOperand(
        field_id=field_id,
        value=Decimal(value),
        decimals=decimals,
        unit="shares",
        period={"kind": "instant", "end": "2025-09-27"},
        rows=rows,
    )


def _valued_share_row(value: str, dimensions: list | None = None) -> dict:
    return {
        "quality_state": "valued",
        "value": value,
        "dimensions": dimensions or [],
    }


def test_pk02_per_class_rule_passes_when_instants_and_values_match() -> None:
    rule = pk02_sbc.CHECK_RULES["pk02.per_class_shares_vs_cover/v1"]
    operands = {
        "shares_outstanding_cover": _share_operand(
            "shares_outstanding_cover",
            "1000",
            3,
            [_valued_share_row("1000")],
        ),
        "shares_issued_parenthetical": _share_operand(
            "shares_issued_parenthetical",
            "1000",
            3,
            [_valued_share_row("1000")],
        ),
    }
    verdict = rule.fn(operands)
    assert verdict.status == "pass"
    assert verdict.tolerance == Decimal("0.001")


def test_pk02_per_class_rule_fails_when_values_differ_by_one_share() -> None:
    rule = pk02_sbc.CHECK_RULES["pk02.per_class_shares_vs_cover/v1"]
    operands = {
        "shares_outstanding_cover": _share_operand(
            "shares_outstanding_cover",
            "1001",
            3,
            [_valued_share_row("1001")],
        ),
        "shares_issued_parenthetical": _share_operand(
            "shares_issued_parenthetical",
            "1000",
            3,
            [_valued_share_row("1000")],
        ),
    }
    verdict = rule.fn(operands)
    assert verdict.status == "fail"


def test_pk02_per_class_rule_matches_per_class_member() -> None:
    rule = pk02_sbc.CHECK_RULES["pk02.per_class_shares_vs_cover/v1"]
    class_a = [{"axis": "us-gaap:StatementClassOfStockAxis", "member": "ClassA"}]
    operands = {
        "shares_outstanding_cover": _share_operand(
            "shares_outstanding_cover",
            "2000",
            3,
            [
                _valued_share_row("1000"),
                _valued_share_row("1000", class_a),
            ],
        ),
        "shares_issued_parenthetical": _share_operand(
            "shares_issued_parenthetical",
            "1000",
            3,
            [_valued_share_row("1000")],  # no ClassA counterpart
        ),
    }
    verdict = rule.fn(operands)
    assert verdict.status == "not_evaluable"
    assert verdict.reason == "missing_dependency"


def _eps_operands(
    income: str, basic: str, eps_basic: str, diluted: str, eps_diluted: str
) -> dict:
    return {
        "net_income_available_to_common": pack_base.RuleOperand(
            field_id="net_income_available_to_common",
            value=Decimal(income),
            decimals=-6,
            unit="USD",
            period=None,
            rows=(),
        ),
        "weighted_average_shares_basic": _share_operand(
            "weighted_average_shares_basic", basic, -3, []
        ),
        "eps_basic": pack_base.RuleOperand(
            field_id="eps_basic",
            value=Decimal(eps_basic),
            decimals=2,
            unit="USD/shares",
            period=None,
            rows=(),
        ),
        "weighted_average_shares_diluted": _share_operand(
            "weighted_average_shares_diluted", diluted, -3, []
        ),
        "eps_diluted": pack_base.RuleOperand(
            field_id="eps_diluted",
            value=Decimal(eps_diluted),
            decimals=2,
            unit="USD/shares",
            period=None,
            rows=(),
        ),
    }


def test_pk02_eps_rule_passes_on_matching_quotients() -> None:
    rule = pk02_sbc.CHECK_RULES["pk02.eps_identity/v1"]
    operands = _eps_operands("100", "150", "0.67", "300", "0.33")
    verdict = rule.fn(operands)
    assert verdict.status == "pass"
    assert verdict.tolerance == Decimal("0.01")


def test_pk02_eps_rule_fails_when_rounding_goes_the_other_way() -> None:
    rule = pk02_sbc.CHECK_RULES["pk02.eps_identity/v1"]
    # 100 / 150 = 0.666... quantizes to 0.67; a disclosed 0.66 is a fail.
    verdict = rule.fn(_eps_operands("100", "150", "0.66", "300", "0.33"))
    assert verdict.status == "fail"


def test_pk02_eps_rule_quantizes_half_even_at_the_boundary() -> None:
    rule = pk02_sbc.CHECK_RULES["pk02.eps_identity/v1"]
    # 25 / 200 = 0.125 -> ROUND_HALF_EVEN at 2 decimals -> 0.12, not 0.13.
    assert rule.fn(_eps_operands("25", "200", "0.13", "300", "0.08")).status == "fail"
    assert rule.fn(_eps_operands("25", "200", "0.12", "300", "0.08")).status == "pass"


def test_pk02_eps_rule_raises_on_zero_denominator() -> None:
    rule = pk02_sbc.CHECK_RULES["pk02.eps_identity/v1"]
    with pytest.raises(ZeroDivisionError):
        rule.fn(_eps_operands("100", "0", "0.67", "300", "0.33"))


# 22. PK02 CLI ----------------------------------------------------------------


def test_pk02_cli_writes_valid_envelope(tmp_path: Path) -> None:
    entity_file = tmp_path / "entity.json"
    query_file = tmp_path / "query.json"
    out_file = tmp_path / "pk02.json"
    entity_file.write_text(json.dumps(ENTITY), encoding="utf-8")
    query_file.write_text(json.dumps(PK02_QUERY), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "fif_specialist_packs.py"),
            "--pack",
            "PK02",
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
    assert len(envelope["fields"]) == 13
    assert envelope["coverage"]["valued_fields"] == 10


# 20. PK11: financial-institution credit, capital and liquidity ---------------
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
# (PK01_ENVELOPE_SHA256 is pinned once, in the PK02 section above.)


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


# 21. PK12: synthetic in-test biotech package ---------------------------------
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
# (PK01_ENVELOPE_SHA256 is pinned once, in the PK02 section above.)
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


# 22. PK12 on AAPL: the honest negative (B.4) ---------------------------------


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
    assert registered_pack_ids() == (
        "PK01", "PK02", "PK03", "PK04", "PK06", "PK09", "PK11", "PK12",
    )


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


# 23. PK12 synthetic biotech: the positive path (§TESTS 2) --------------------


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


# 24. PK12 pre-revenue applicability (§TESTS 3) --------------------------------


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


# 25. PK12 non-positive burn (§TESTS 4) ----------------------------------------


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


# 26. PK12 form gate (§TESTS 5) -------------------------------------------------


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


# 27. BASE-pack invariance (§TESTS 6) -------------------------------------------


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


# 28. PK12 CLI -------------------------------------------------------------------


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


# 29. PK09 narrative locator (A.1/A.2) ----------------------------------------


def test_pk09_primary_document_text_is_deterministic_with_exact_offsets() -> None:
    package = load_golden_aapl_package(ROOT, accession=ACCESSION)
    first = pack_narrative.primary_document_text(package)
    second = pack_narrative.primary_document_text(package)
    assert first == second  # same bytes -> same NarrativeText
    assert first.document_id == package.manifest["primary_document"]
    assert len(first.offsets) == len(first.text)
    raw = package.members[first.document_id]
    step = max(1, len(first.text) // 20)
    for index in range(0, len(first.text), step):
        ch = first.text[index]
        offset = first.offsets[index]
        seg = raw[offset : offset + len(ch.encode("utf-8"))]
        assert (
            seg.decode("utf-8", errors="ignore") == ch
            or seg.startswith(b"&")  # the entity it came from
            or seg.startswith(b"<")  # a tag-derived space
        ), f"offset map broke down at char {index}"


def test_pk09_locate_section_skips_toc_and_returns_body() -> None:
    package = load_golden_aapl_package(ROOT, accession=ACCESSION)
    nt = pack_narrative.primary_document_text(package)
    matches = list(
        re.finditer(pk09_controls.ITEM9A.heading, nt.text, re.IGNORECASE)
    )
    assert len(matches) >= 2  # the TOC line and the body heading
    span = pack_narrative.locate_section(nt, pk09_controls.ITEM9A)
    assert span is not None
    assert span[0] != matches[0].start()  # not the TOC occurrence
    assert span[0] == matches[-1].start()  # the body heading
    section = nt.text[span[0] : span[1]]
    assert "disclosure controls and procedures" in section
    assert "Item 9B" not in section  # ends at the first end heading after it


# 30. PK09 envelope over the AAPL fixture (B.7) -------------------------------

PK09_QUERY = {**QUERY, "requested_metrics": ["controls"]}
# Invariance pins captured at BASE before this lane's edits (test 8): the
# registry/build changes for PK09 must not move either earlier pack.
PK01_CONTENT_SHA256 = (
    "c634be05977eeb1430937bd52ef58ab096c8490dd6cf12ce0820b285c3e8cee8"
)
# (PK01_ENVELOPE_SHA256 is pinned once, in the PK02 section above.)
PK06_CONTENT_SHA256 = (
    "21b9476039b6a84dc49962d2ac18e2da62e8ce87eabe1c88a56190df2f21fd26"
)
PK09_VALUED = {
    "icfr_management_conclusion": "effective",
    "disclosure_controls_effective": "effective",
    "material_weakness_present": "false",
    "auditor_firm": "Ernst & Young LLP",
    "auditor_opinion_fs": "unqualified",
    "auditor_opinion_icfr": "effective",
    "going_concern_substantial_doubt": "not_disclosed",
}
PK09_NON_VALUED = {
    "going_concern_management_plan": "missing_dependency",
    "remediation_span": "missing_dependency",
}


def _pk09_input(**overrides) -> PackInput:
    defaults = dict(
        packages=(load_golden_aapl_package(ROOT, accession=ACCESSION),),
        entity=ENTITY,
        query=PK09_QUERY,
        issuer_sic="3571",
        sic_source="sec_submissions",
    )
    defaults.update(overrides)
    return PackInput(**defaults)


@pytest.fixture(scope="module")
def pk09_result() -> dict:
    return produce_pack("PK09", _pk09_input())


def test_pk09_result_passes_contract_validator(pk09_result: dict) -> None:
    assert contract.validate_pack_result(pk09_result) == []


def test_pk09_result_passes_jsonschema_envelope(pk09_result: dict) -> None:
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
        Draft202012Validator(schema, registry=registry).iter_errors(pk09_result)
    )
    assert errors == []


def test_pk09_rows_follow_catalogue_order(pk09_result: dict) -> None:
    catalogue = contract.load_pack_schema("PK09")
    assert [row["field_id"] for row in pk09_result["fields"]] == [
        item["field_id"] for item in catalogue["fields"]
    ]
    assert [row["check_id"] for row in pk09_result["checks"]] == [
        item["check_id"] for item in catalogue["checks"]
    ]


def test_pk09_valued_rows_carry_span_evidence(pk09_result: dict) -> None:
    for field_id, literal in PK09_VALUED.items():
        row = _row(pk09_result, field_id)
        assert row["quality_state"] == "valued"
        assert row["text_value"] == literal
        assert row["value"] is None  # non-numeric types carry no decimal value
        assert row["evidence_kind"] == "text_span"
        assert row["required_evidence_kind"] == "text_span"
        assert row["coverage_state"] == "source_trace_complete"
        assert row["reason"] is None
        assert row["concept"] is None and row["taxonomy"] is None
        assert row["dimensions"] == []
        assert row["mapping_rule_id"] == f"PK09.{field_id}.text_span/v1"
        assert row["mapping_rule_digest"]
        span = row["source_span"]
        assert isinstance(span, dict)
        assert span["document_id"] == MANIFEST["primary_document"]
        assert span["accession"] == ACCESSION
        assert isinstance(span["start_offset"], int) and span["start_offset"] >= 0
        assert span["end_offset"] > span["start_offset"]


def test_pk09_sentence_and_window_text_fields(pk09_result: dict) -> None:
    change = _row(pk09_result, "icfr_change_in_period")
    assert change["quality_state"] == "valued"
    assert (
        "There were no changes in the Company’s internal control over financial"
        " reporting during the fourth quarter of 2025" in change["text_value"]
    )
    assert len(change["text_value"]) <= 1024
    cam = _row(pk09_result, "critical_audit_matters")
    assert cam["quality_state"] == "valued"
    assert cam["text_value"].startswith("The critical audit matter communicated")
    assert len(cam["text_value"]) <= 512
    # The valued absence of a material weakness is asserted over Item 9A only.
    weakness = _row(pk09_result, "material_weakness_present")
    assert weakness["text_value"] == "false"
    assert weakness["source_span"]["end_offset"] < len(
        load_golden_aapl_package(ROOT, accession=ACCESSION)
        .members[MANIFEST["primary_document"]]
    )


def test_pk09_non_valued_rows_report_typed_reasons(pk09_result: dict) -> None:
    for field_id, reason in PK09_NON_VALUED.items():
        row = _row(pk09_result, field_id)
        assert row["quality_state"] == "not_evaluable"
        assert row["non_value_state"] == "not_evaluable"
        assert row["reason"] == reason
        assert row["value"] is None and row["text_value"] is None
        assert row["source_span"] is None
        assert row["coverage_state"] == "unmapped"
    # Conditional fields name the dependency that gated them.
    assert _row(pk09_result, "going_concern_management_plan")[
        "dependency_field_ids"
    ] == ["going_concern_substantial_doubt"]
    assert _row(pk09_result, "remediation_span")["dependency_field_ids"] == [
        "material_weakness_present"
    ]


def test_pk09_checks_pass_and_cam_receipt(pk09_result: dict) -> None:
    for check_id in (
        "management_vs_auditor_icfr",
        "going_concern_vs_opinion",
        "cam_present_on_10k",
    ):
        check = _check(pk09_result, check_id)
        assert check["status"] == "pass"
        assert check["reason"] is None
    assert "cam_count=1" in pk09_result["receipts"]
    assert any(
        receipt.startswith("narrative_text_sha256=")
        for receipt in pk09_result["receipts"]
    )


def test_pk09_coverage_and_limitations(pk09_result: dict) -> None:
    assert pk09_result["applicability"]["state"] == "applicable"
    assert pk09_result["applicability"]["reason"] == "applicability_rule_satisfied"
    assert pk09_result["coverage"] == {
        "valued_fields": 9,
        "missing_fields": 0,
        "unsupported_fields": 0,
        "not_evaluable_fields": 2,
        "not_applicable_fields": 0,
        "disclosure_coverage_state": "present",
    }
    limitations = pk09_result["limitations"]
    assert (
        "pk09.text_span_rows: regex over the primary document narrative; no "
        "table or footnote resolution" in limitations
    )
    for field_id in PK09_NON_VALUED:  # one line per non-valued field
        assert any(
            line.startswith(f"pk09.{field_id}:") for line in limitations
        ), field_id


def test_pk09_text_span_rows_never_carry_a_numeric_value(pk09_result: dict) -> None:
    for row in pk09_result["fields"]:
        if row["evidence_kind"] == "text_span":
            assert row["value"] is None or isinstance(row["value"], (bool, str))


def test_pk09_production_is_deterministic() -> None:
    first = produce_pack("PK09", _pk09_input())
    second = produce_pack("PK09", _pk09_input())
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["pack_content_sha256"] == second["pack_content_sha256"]


# 31. PK09 synthetic probes (10-Q form gate; material weakness) ---------------


_SYNTHETIC_PREFIX = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<html xmlns="http://www.w3.org/1999/xhtml" '
    'xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" '
    'xmlns:xbrli="http://www.xbrl.org/2003/instance">'
    "<head><title>Form</title></head><body>"
    "<ix:header><ix:resources>"
    '<xbrli:context id="c1"><xbrli:entity><xbrli:identifier '
    'scheme="http://www.sec.gov/CIK">0000000099</xbrli:identifier>'
    "</xbrli:entity><xbrli:period><xbrli:instant>2026-06-30</xbrli:instant>"
    "</xbrli:period></xbrli:context>"
    "</ix:resources></ix:header>"
)


def _synthetic_package(form: str, body: str) -> GoldenFilingPackage:
    """A minimal convertible filing package carrying arbitrary body HTML."""
    html = (_SYNTHETIC_PREFIX + body + "</body></html>").encode("utf-8")
    digest = sha256(html).hexdigest()
    manifest = {
        "entity_id": "ISS:TEST",
        "cik": "0000000099",
        "legal_name": "Test Co",
        "accession": "0000000099-26-000001",
        "form": form,
        "primary_document": "doc.htm",
        "period_of_report": "2026-06-30",
        "filing_date": "2026-07-10",
        "source_accepted_at": "2026-07-10T08:00:00.000Z",
        "fixture_recorded_at": "2026-08-23T00:32:31Z",
        "members": [
            {
                "name": "doc.htm",
                "state": "stored",
                "role": "primary",
                "content_sha256": digest,
            }
        ],
    }
    return GoldenFilingPackage(manifest=manifest, members={"doc.htm": html})


def test_pk09_quarterly_form_gates_auditor_rows_and_checks() -> None:
    body = (
        "<div>Item 4. Controls and Procedures</div>"
        "<div>Based on an evaluation, the Company&#8217;s disclosure controls"
        " and procedures were effective as of June 30, 2026.</div>"
        "<div>Management concluded that the Company&#8217;s internal control"
        " over financial reporting was effective as of June 30, 2026.</div>"
        "<div>There were no changes in the Company&#8217;s internal control"
        " over financial reporting during the quarter.</div>"
    )
    result = produce_pack(
        "PK09",
        _pk09_input(packages=(_synthetic_package("10-Q", body),)),
    )
    assert result["applicability"]["state"] == "applicable"  # 10-Q is in forms
    annual_only = (
        "auditor_firm",
        "auditor_opinion_fs",
        "auditor_opinion_icfr",
        "critical_audit_matters",
        "going_concern_substantial_doubt",
        "going_concern_management_plan",
    )
    for field_id in annual_only:
        row = _row(result, field_id)
        assert row["quality_state"] == "not_applicable"
        assert row["non_value_state"] == "not_applicable"
        assert row["reason"] == "form_outside_pack_forms"
        assert row["coverage_state"] == "not_applicable_period"
    # The controls family still resolves through the Item 4 section spec.
    assert _row(result, "icfr_management_conclusion")["text_value"] == "effective"
    assert _row(result, "disclosure_controls_effective")["text_value"] == "effective"
    assert _row(result, "material_weakness_present")["text_value"] == "false"
    assert _row(result, "icfr_change_in_period")["quality_state"] == "valued"
    assert _row(result, "remediation_span")["reason"] == "missing_dependency"
    for check_id in (
        "management_vs_auditor_icfr",
        "going_concern_vs_opinion",
        "cam_present_on_10k",
    ):
        check = _check(result, check_id)
        assert check["status"] == "not_applicable"
        assert check["reason"] == "form_outside_pack_forms"
    assert contract.validate_pack_result(result) == []


def test_pk09_material_weakness_probe() -> None:
    body = (
        "<div>Item 9A. Controls and Procedures</div>"
        "<div>Management concluded that a material weakness in the "
        "Company&#8217;s internal control over financial reporting existed as "
        "of the period end.</div>"
        "<div>The Company has begun remediation of the material weakness, "
        "including hiring additional accounting personnel.</div>"
    )
    result = produce_pack(
        "PK09",
        _pk09_input(packages=(_synthetic_package("10-K", body),)),
    )
    weakness = _row(result, "material_weakness_present")
    assert weakness["quality_state"] == "valued"
    assert weakness["text_value"] == "true"
    conclusion = _row(result, "icfr_management_conclusion")
    assert conclusion["quality_state"] == "valued"
    assert conclusion["text_value"] == "material_weakness"
    remediation = _row(result, "remediation_span")
    assert remediation["quality_state"] == "valued"
    assert remediation["text_value"].startswith("The Company has begun")
    # A material weakness without an auditor report leaves the cross check
    # honestly not_evaluable rather than bent into a pass.
    check = _check(result, "management_vs_auditor_icfr")
    assert check["status"] == "not_evaluable"
    assert check["reason"] == "missing_dependency"
    assert contract.validate_pack_result(result) == []


# 32. PK09 invariance and CLI -------------------------------------------------


def test_pk09_edits_leave_base_pack_envelopes_byte_identical() -> None:
    for pack_id, pack_input, content_sha, envelope_sha in (
        ("PK06", _pack_input(), PK06_CONTENT_SHA256, PK06_ENVELOPE_SHA256),
        ("PK01", _pk01_input(), PK01_CONTENT_SHA256, PK01_ENVELOPE_SHA256),
    ):
        result = produce_pack(pack_id, pack_input)
        assert result["pack_content_sha256"] == content_sha, pack_id
        payload = json.dumps(
            result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        assert (
            sha256(payload.encode("utf-8")).hexdigest() == envelope_sha
        ), pack_id


def test_pk09_cli_writes_valid_envelope(tmp_path: Path) -> None:
    entity_file = tmp_path / "entity.json"
    query_file = tmp_path / "query.json"
    out_file = tmp_path / "pk09.json"
    entity_file.write_text(json.dumps(ENTITY), encoding="utf-8")
    query_file.write_text(json.dumps(PK09_QUERY), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "fif_specialist_packs.py"),
            "--pack",
            "PK09",
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
    assert envelope["coverage"]["valued_fields"] == 9
    assert "cam_count=1" in envelope["receipts"]


# 33. PK04: revenue recognition and contract balances -------------------------
#
# Fixture-verified through the raw ledger (FY2025 = 2024-09-29..2025-09-27):
# the fixture tags total and member revenue under the product/service and
# geographical axes (the segments-axis facts carry a ConsolidationItemsAxis
# member and are outside the field's axes), the current contract liability,
# the rollforward's opening (2024-09-28) and closing (2025-09-27) balances and
# recognized revenue, and the RPO percentage ladder as typed-dimension facts
# (2025-09-28 0.66, 2026-09-27 0.23, 2027-09-26 0.09, 2028-10-01 0.02); the
# noncurrent liability and the RPO total are absent standard facts, gross
# additions have no standard element, and RPO timing exists only as
# non-numeric iXBRL the raw ledger excludes by design.

from datetime import date as _date  # noqa: E402

from engine.fundamental_forensics.raw_ledger import (  # noqa: E402
    FactContext,
    FactUnit,
    RawFactLedger,
    RawFactOccurrence,
    SourceIdentity,
    TemporalClocks,
)
from engine.fundamental_forensics.specialist_packs import (  # noqa: E402
    definition_linkbase,
    pk04_revenue,
)

PK04_QUERY = {**QUERY, "requested_metrics": ["revenue"]}
# A.6: sha256 of the canonical JSON bytes of the PK02 envelope recorded at
# the PK04 lane base; PK04 edits must not move it (PK06/PK01 have their own
# pins above).
PK02_ENVELOPE_SHA256 = (
    "878837747052a8ef1ed46b8b9f562fa0b707279e09340debadb25e9737c3c254"
)
PRODUCT_OR_SERVICE_LEDGER_AXIS = "{http://fasb.org/srt/2025}ProductOrServiceAxis"
GEOGRAPHICAL_LEDGER_AXIS = "{http://fasb.org/srt/2025}StatementGeographicalAxis"
RPO_TIMING_AXIS_QNAME = (
    "us-gaap:RevenueRemainingPerformanceObligationExpectedTimingOf"
    "SatisfactionStartDateAxis"
)
# B.4 order: axis declaration order, canonical member order within an axis.
DISAGGREGATED = [
    ("{http://www.apple.com/20250927}IPadMember", "28023000000"),
    ("{http://www.apple.com/20250927}IPhoneMember", "209586000000"),
    ("{http://www.apple.com/20250927}MacMember", "33708000000"),
    (
        "{http://www.apple.com/20250927}WearablesHomeandAccessoriesMember",
        "35686000000",
    ),
    ("us-gaap:ProductMember", "307003000000"),
    ("us-gaap:ServiceMember", "109158000000"),
    ("{http://www.apple.com/20250927}OtherCountriesMember", "199994000000"),
    ("{http://xbrl.sec.gov/country/2025}CN", "64377000000"),
    ("{http://xbrl.sec.gov/country/2025}US", "151790000000"),
]


def _pk04_input(**overrides) -> PackInput:
    defaults = dict(
        packages=(load_golden_aapl_package(ROOT, accession=ACCESSION),),
        entity=ENTITY,
        query=PK04_QUERY,
        issuer_sic="3571",
        sic_source="sec_submissions",
    )
    defaults.update(overrides)
    return PackInput(**defaults)


@pytest.fixture(scope="module")
def pk04_result() -> dict:
    return produce_pack("PK04", _pk04_input())


def _catalogue_field(pack_id: str, field_id: str) -> dict:
    return next(
        item
        for item in contract.load_pack_schema(pack_id)["fields"]
        if item["field_id"] == field_id
    )


def test_pk04_result_passes_contract_validator(pk04_result: dict) -> None:
    assert contract.validate_pack_result(pk04_result) == []


def test_pk04_result_passes_jsonschema_envelope(pk04_result: dict) -> None:
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
        Draft202012Validator(schema, registry=registry).iter_errors(pk04_result)
    )
    assert errors == []


def test_pk04_rows_follow_catalogue_order_with_twenty_rows(
    pk04_result: dict,
) -> None:
    catalogue = contract.load_pack_schema("PK04")
    expected = [item["field_id"] for item in catalogue["fields"]]
    produced = [row["field_id"] for row in pk04_result["fields"]]
    assert len(produced) == 20  # 12 catalogue fields; the disaggregation repeats
    compacted = [
        field_id
        for index, field_id in enumerate(produced)
        if index == 0 or produced[index - 1] != field_id
    ]
    assert compacted == expected
    position = produced.index("revenue_disaggregated")
    assert produced[position + 8] == "revenue_disaggregated"  # adjacent block
    rows = _rows(pk04_result, "revenue_disaggregated")
    axes = [row["dimensions"][0]["axis"] for row in rows]
    assert axes == [PRODUCT_OR_SERVICE_LEDGER_AXIS] * 6 + [
        GEOGRAPHICAL_LEDGER_AXIS
    ] * 3  # declared axis order
    assert [row["check_id"] for row in pk04_result["checks"]] == [
        item["check_id"] for item in catalogue["checks"]
    ]


def test_pk04_revenue_and_contract_liability_balances(
    pk04_result: dict, ledger
) -> None:
    revenue = _row(pk04_result, "revenue")
    assert revenue["value"] == "416161000000"
    assert revenue["concept"] == (
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
    )
    assert revenue["period"] == {
        "kind": "duration",
        "start": "2024-09-29",
        "end": "2025-09-27",
    }
    # Four identical undimensioned occurrences are not a conflict; all listed.
    assert len(revenue["source_occurrence_ids"]) == 4
    for occurrence_id in revenue["source_occurrence_ids"]:
        assert ledger.by_id(occurrence_id) is not None
    assert _row(pk04_result, "contract_liability_current")["value"] == "9055000000"


def test_pk04_rollforward_opening_and_closing_instants(pk04_result: dict) -> None:
    opening = _row(pk04_result, "contract_liability_rollforward_opening")
    assert opening["value"] == "12800000000"
    assert opening["period"] == {"kind": "instant", "end": "2024-09-28"}
    closing = _row(pk04_result, "contract_liability_rollforward_closing")
    assert closing["value"] == "13700000000"
    assert closing["period"] == {"kind": "instant", "end": "2025-09-27"}
    recognized = _row(pk04_result, "contract_liability_rollforward_recognized")
    assert recognized["value"] == "8229000000"
    assert recognized["period"] == {
        "kind": "duration",
        "start": "2024-09-29",
        "end": "2025-09-27",
    }


def test_pk04_noncurrent_is_missing_standard_fact(pk04_result: dict) -> None:
    row = _row(pk04_result, "contract_liability_noncurrent")
    assert row["quality_state"] == "missing"
    assert row["non_value_state"] == "missing"
    assert row["value"] is None
    assert row["reason"] == (
        "missing_standard_fact:us-gaap:ContractWithCustomerLiabilityNoncurrent"
    )


def test_pk04_additions_is_declared_unmapped(pk04_result: dict) -> None:
    row = _row(pk04_result, "contract_liability_rollforward_additions")
    assert row["quality_state"] == "unsupported"
    assert row["non_value_state"] == "unsupported"
    assert row["coverage_state"] == "unmapped"
    assert row["reason"] == "missing_dependency"
    assert row["value"] is None
    assert (
        "contract_liability_rollforward_additions: no standard alias; gross"
        " additions are narrative-only for most issuers" in pk04_result["limitations"]
    )


def test_pk04_rpo_total_is_missing_standard_fact(pk04_result: dict) -> None:
    row = _row(pk04_result, "rpo_total")
    assert row["quality_state"] == "missing"
    assert row["reason"] == (
        "missing_standard_fact:us-gaap:RevenueRemainingPerformanceObligation"
    )


def test_pk04_rpo_percentage_selects_earliest_typed_date(
    pk04_result: dict, ledger
) -> None:
    row = _row(pk04_result, "rpo_percentage_next_12m")
    assert row["quality_state"] == "valued"
    assert row["value"] == "0.66"
    assert row["unit"] == "ratio"
    assert row["dimensions"] == [
        {"axis": RPO_TIMING_AXIS_QNAME, "member": "2025-09-28"}
    ]
    assert row["mapping_rule_id"] == (
        "PK04.rpo_percentage_next_12m.typed_dimensioned_fact/v1"
    )
    assert row["period"] == {"kind": "instant", "end": "2025-09-27"}
    assert ledger.by_id(row["source_occurrence_ids"][0]) is not None


def test_pk04_rpo_timing_is_unsupported(pk04_result: dict) -> None:
    row = _row(pk04_result, "rpo_timing")
    assert row["quality_state"] == "unsupported"
    assert row["value"] is None
    assert (
        "rpo_timing: duration facts are non-numeric iXBRL and are not represented"
        " in the raw ledger" in pk04_result["limitations"]
    )


def test_pk04_policy_text_block_is_unsupported(pk04_result: dict) -> None:
    row = _row(pk04_result, "revenue_policy_text_block")
    assert row["quality_state"] == "unsupported"
    assert row["evidence_kind"] == "text_span"
    assert row["required_evidence_kind"] == "text_span"
    assert row["value"] is None


def test_pk04_disaggregated_rows_carry_group_order_and_values(
    pk04_result: dict, ledger
) -> None:
    rows = _rows(pk04_result, "revenue_disaggregated")
    assert len(rows) == 9
    for index, (row, (member, value)) in enumerate(zip(rows, DISAGGREGATED)):
        axis = (
            PRODUCT_OR_SERVICE_LEDGER_AXIS if index < 6 else GEOGRAPHICAL_LEDGER_AXIS
        )
        assert row["quality_state"] == "valued"
        assert row["dimensions"] == [{"axis": axis, "member": member}]
        assert row["value"] == value
        assert row["unit"] == "USD"
        assert row["period"] == {
            "kind": "duration",
            "start": "2024-09-29",
            "end": "2025-09-27",
        }
        assert row["mapping_rule_id"] == (
            "PK04.revenue_disaggregated.dimensioned_fact/v1"
        )
        assert ledger.by_id(row["source_occurrence_ids"][0]) is not None
    # No member sits outside every definition group on this fixture.
    assert not [
        item
        for item in pk04_result["limitations"]
        if "outside every definition group" in item
    ]


def test_pk04_rollforward_check_names_refused_implied_additions(
    pk04_result: dict,
) -> None:
    check = _check(pk04_result, "contract_liability_rollforward")
    assert check["status"] == "not_evaluable"
    assert check["reason"] == "missing_dependency"
    implied = next(
        item
        for item in pk04_result["limitations"]
        if "refused to imply contract_liability_rollforward_additions" in item
    )
    # closing - opening + recognized = 9,129,000,000; never emitted as a value.
    assert "9129000000" in implied
    assert _row(pk04_result, "contract_liability_rollforward_additions")[
        "value"
    ] is None


def test_pk04_rpo_vs_deferred_scope_awaits_rpo_total(pk04_result: dict) -> None:
    check = _check(pk04_result, "rpo_vs_deferred_scope")
    assert check["status"] == "not_evaluable"
    assert check["reason"] == "missing_dependency"
    assert check["evidence_field_ids"] == [
        "rpo_total",
        "contract_liability_current",
        "contract_liability_noncurrent",
    ]


def test_pk04_disaggregation_sums_pass_with_group_census(
    pk04_result: dict,
) -> None:
    check = _check(pk04_result, "disaggregation_sums_to_revenue")
    assert check["status"] == "pass"
    assert check["reason"] is None
    assert check["tolerance"] == "1000000"
    assert check["evidence_field_ids"] == ["revenue_disaggregated", "revenue"]
    assert (
        "pk04.disaggregation_sums_to_revenue: groups 3/3"
        in pk04_result["limitations"]
    )


def test_pk04_coverage_counts(pk04_result: dict) -> None:
    assert pk04_result["coverage"] == {
        "valued_fields": 15,
        "missing_fields": 2,
        "unsupported_fields": 3,
        "not_evaluable_fields": 0,
        "not_applicable_fields": 0,
        "disclosure_coverage_state": "present",
    }


# 34. A.5 grouped sum identity, synthetic groups ------------------------------


def _breakdown(
    axis: str,
    groups: tuple[tuple[str, ...], ...],
    member_values: dict,
) -> "pack_base._AxisGroupBreakdown":
    return pack_base._AxisGroupBreakdown(
        axis=axis, groups=groups, member_values=member_values
    )


def _grouped_check(breakdowns, total: str, total_decimals: int = -6) -> dict:
    addend = pack_base._FieldOutcome(
        row={"field_id": "revenue_disaggregated", "quality_state": "valued"},
        value=None,
        decimals=-6,
        unit="USD",
        group_breakdown=tuple(breakdowns),
    )
    total_outcome = pack_base._FieldOutcome(
        row={"field_id": "revenue", "quality_state": "valued"},
        value=Decimal(total),
        decimals=total_decimals,
        unit="USD",
    )
    resolver = pack_base._OperandResolver(
        {"revenue_disaggregated": addend, "revenue": total_outcome},
        _pk04_input(),
        foreign_cache={},
    )
    catalogue_check = next(
        item
        for item in contract.load_pack_schema("PK04")["checks"]
        if item["check_id"] == "disaggregation_sums_to_revenue"
    )
    specs = [
        spec
        for spec in pk04_revenue.PRODUCER.checks
        if spec.check_id == "disaggregation_sums_to_revenue"
    ]
    sink: list[str] = []
    row = pack_base._evaluate_check(
        catalogue_check, specs, resolver, limitation_sink=sink, pack_id="PK04"
    )
    return {"row": row, "sink": sink}


def test_pk04_grouped_sum_fails_when_complete_group_short_by_two_million() -> None:
    outcome = _grouped_check(
        [
            _breakdown(
                "srt:ProductOrServiceAxis",
                (("us-gaap:ProductMember", "us-gaap:ServiceMember"),),
                {
                    "us-gaap:ProductMember": Decimal("99000000"),
                    "us-gaap:ServiceMember": Decimal("99000000"),
                },
            )
        ],
        "200000000",
    )
    assert outcome["row"]["status"] == "fail"
    assert outcome["row"]["reason"] is None
    assert outcome["row"]["tolerance"] == "1000000"
    assert "pk04.disaggregation_sums_to_revenue: groups 1/1" in outcome["sink"]


def test_pk04_grouped_sum_not_evaluable_with_only_incomplete_groups() -> None:
    outcome = _grouped_check(
        [
            _breakdown(
                "srt:ProductOrServiceAxis",
                (("us-gaap:ProductMember", "us-gaap:ServiceMember"),),
                {"us-gaap:ProductMember": Decimal("307003000000")},
            )
        ],
        "416161000000",
    )
    assert outcome["row"]["status"] == "not_evaluable"
    assert outcome["row"]["reason"] == "missing_dependency"
    assert "pk04.disaggregation_sums_to_revenue: groups 0/1" in outcome["sink"]


def test_pk04_grouped_sum_passes_when_every_axis_has_a_complete_group() -> None:
    outcome = _grouped_check(
        [
            _breakdown(
                "srt:ProductOrServiceAxis",
                (
                    (
                        "aapl:IPadMember",
                        "aapl:IPhoneMember",
                        "aapl:MacMember",
                        "aapl:WearablesHomeandAccessoriesMember",
                        "us-gaap:ServiceMember",
                    ),
                    ("us-gaap:ProductMember", "us-gaap:ServiceMember"),
                ),
                {
                    "aapl:IPadMember": Decimal("28023000000"),
                    "aapl:IPhoneMember": Decimal("209586000000"),
                    "aapl:MacMember": Decimal("33708000000"),
                    "us-gaap:ProductMember": Decimal("307003000000"),
                    "us-gaap:ServiceMember": Decimal("109158000000"),
                },
            ),
            _breakdown(
                "srt:StatementGeographicalAxis",
                (("country:US", "country:CN", "aapl:OtherCountriesMember"),),
                {
                    "country:US": Decimal("151790000000"),
                    "country:CN": Decimal("64377000000"),
                    "aapl:OtherCountriesMember": Decimal("199994000000"),
                },
            ),
        ],
        "416161000000",
    )
    assert outcome["row"]["status"] == "pass"
    assert outcome["row"]["reason"] is None
    assert outcome["row"]["tolerance"] == "1000000"
    # The five-member group is incomplete (no Wearables value) yet its axis
    # still owns a complete group; the census counts groups, not axes.
    assert "pk04.disaggregation_sums_to_revenue: groups 2/3" in outcome["sink"]


def test_pk04_no_def_xml_falls_back_to_single_group_evaluation() -> None:
    package = load_golden_aapl_package(ROOT, accession=ACCESSION)
    trimmed = replace(
        package,
        manifest={
            **package.manifest,
            "members": [
                item
                for item in package.manifest["members"]
                if not str(item.get("name") or "").endswith("_def.xml")
            ],
        },
        members={
            name: payload
            for name, payload in package.members.items()
            if not name.endswith("_def.xml")
        },
    )
    result = produce_pack("PK04", _pk04_input(packages=(trimmed,)))
    rows = _rows(result, "revenue_disaggregated")
    assert len(rows) == 9  # every admitted member still emits, unpartitioned
    check = _check(result, "disaggregation_sums_to_revenue")
    # Without the definition linkbase the axis is evaluated as ONE group of
    # all its emitted rows: the product/service axis then mixes the two-way
    # and five-way partitions (832,322,000,000 in total), so the single-group
    # evaluation honestly fails rather than pretending to partition.
    assert check["status"] == "fail"
    assert check["reason"] is None
    assert (
        "pk04.disaggregation_sums_to_revenue: groups 2/2" in result["limitations"]
    )
    assert (
        "revenue_disaggregated: srt:ProductOrServiceAxis has no definition"
        " group; member rows unpartitioned" in result["limitations"]
    )
    assert (
        "revenue_disaggregated: srt:StatementGeographicalAxis has no"
        " definition group; member rows unpartitioned" in result["limitations"]
    )
    assert contract.validate_pack_result(result) == []


# 35. definition linkbase (A.3) ------------------------------------------------


def _fixture_def_xml_bytes() -> bytes:
    package = load_golden_aapl_package(ROOT, accession=ACCESSION)
    return next(
        payload
        for name, payload in sorted(package.members.items())
        if name.endswith("_def.xml")
    )


def test_parse_axis_member_groups_returns_fixture_groups() -> None:
    groups = definition_linkbase.parse_axis_member_groups(_fixture_def_xml_bytes())
    assert groups["srt:ProductOrServiceAxis"] == (
        (
            "aapl:IPadMember",
            "aapl:IPhoneMember",
            "aapl:MacMember",
            "aapl:WearablesHomeandAccessoriesMember",
            "us-gaap:ServiceMember",
        ),
        ("us-gaap:ProductMember", "us-gaap:ServiceMember"),
    )
    assert groups["srt:StatementGeographicalAxis"] == (
        ("aapl:OtherCountriesMember", "country:CN", "country:US"),
    )
    assert groups["us-gaap:StatementBusinessSegmentsAxis"] == (
        (
            "aapl:AmericasSegmentMember",
            "aapl:EuropeSegmentMember",
            "aapl:GreaterChinaSegmentMember",
            "aapl:JapanSegmentMember",
            "aapl:RestOfAsiaPacificSegmentMember",
        ),
    )


def test_members_in_any_group_is_the_canonical_union() -> None:
    groups = definition_linkbase.parse_axis_member_groups(_fixture_def_xml_bytes())
    assert definition_linkbase.members_in_any_group(
        groups, "srt:ProductOrServiceAxis"
    ) == (
        "aapl:IPadMember",
        "aapl:IPhoneMember",
        "aapl:MacMember",
        "aapl:WearablesHomeandAccessoriesMember",
        "us-gaap:ProductMember",
        "us-gaap:ServiceMember",
    )
    assert definition_linkbase.members_in_any_group(groups, "srt:NoSuchAxis") == ()


_SYNTHETIC_LINKBASE = b"""<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:definitionLink xlink:role="http://example.com/role/A" xlink:type="extended">
    <link:loc xlink:type="locator" xlink:label="axis" xlink:href="syn-2026.xsd#srt_TestAxis"/>
    <link:loc xlink:type="locator" xlink:label="domain" xlink:href="syn-2026.xsd#srt_TestDomain"/>
    <link:loc xlink:type="locator" xlink:label="m1" xlink:href="syn-2026.xsd#srt_FirstMember"/>
    <link:loc xlink:type="locator" xlink:label="m2" xlink:href="syn-2026.xsd#srt_SecondMember"/>
    <link:loc xlink:type="locator" xlink:label="m2child" xlink:href="syn-2026.xsd#srt_SecondChildMember"/>
    <link:definitionArc xlink:type="arc" xlink:arcrole="http://xbrl.org/int/dim/arcrole/dimension-domain" xlink:from="axis" xlink:to="domain" order="1"/>
    <link:definitionArc xlink:type="arc" xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member" xlink:from="domain" xlink:to="m1" order="1"/>
    <link:definitionArc xlink:type="arc" xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member" xlink:from="domain" xlink:to="m2" order="2"/>
    <link:definitionArc xlink:type="arc" xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member" xlink:from="m2" xlink:to="m2child" order="1"/>
  </link:definitionLink>
  <link:definitionLink xlink:role="http://example.com/role/B" xlink:type="extended">
    <link:loc xlink:type="locator" xlink:label="axis" xlink:href="syn-2026.xsd#srt_TestAxis"/>
    <link:loc xlink:type="locator" xlink:label="domain" xlink:href="syn-2026.xsd#srt_TestDomain"/>
    <link:loc xlink:type="locator" xlink:label="m1" xlink:href="syn-2026.xsd#srt_FirstMember"/>
    <link:loc xlink:type="locator" xlink:label="m2" xlink:href="syn-2026.xsd#srt_SecondMember"/>
    <link:definitionArc xlink:type="arc" xlink:arcrole="http://xbrl.org/int/dim/arcrole/dimension-domain" xlink:from="axis" xlink:to="domain" order="1"/>
    <link:definitionArc xlink:type="arc" xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member" xlink:from="domain" xlink:to="m1" order="1"/>
    <link:definitionArc xlink:type="arc" xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member" xlink:from="domain" xlink:to="m2" order="2"/>
  </link:definitionLink>
</link:linkbase>
"""


def test_parse_axis_member_groups_excludes_grandchildren_and_collapses_roles() -> None:
    groups = definition_linkbase.parse_axis_member_groups(_SYNTHETIC_LINKBASE)
    # The grandchild srt:SecondChildMember is never a group member, and the
    # two roles' identical partitions collapse to one distinct group.
    assert groups == {"srt:TestAxis": (("srt:FirstMember", "srt:SecondMember"),)}


def test_parse_axis_member_groups_without_linkbase_is_empty() -> None:
    assert definition_linkbase.parse_axis_member_groups(None) == {}
    assert definition_linkbase.parse_axis_member_groups(b"") == {}


# 36. opening_instant and typed selection on synthetic ledgers -----------------


def _synthetic_occurrence(
    concept: str,
    *,
    instant=None,
    start=None,
    end=None,
    explicit=(),
    typed=(),
    value: str = "1",
    decimals: str = "-6",
) -> RawFactOccurrence:
    return RawFactOccurrence(
        source=SourceIdentity(
            source="synthetic",
            entity_id="synthetic-entity",
            accession="0000000000-00-000000",
            document_id="synthetic",
            body_sha256="0" * 64,
        ),
        concept_qname=concept,
        context=FactContext(
            context_id="ctx",
            entity_scheme="urn:test",
            entity_identifier="synthetic-entity",
            instant=instant,
            start=start,
            end=end,
            explicit_dimensions=explicit,
            typed_dimensions=typed,
        ),
        clocks=TemporalClocks(recorded_at="2026-08-05T12:00:02Z"),
        unit=FactUnit(unit_id="u", measures=("iso4217:USD",)),
        parsed_value=Decimal(value),
        decimals=decimals,
    )


def _opening_outcome(events) -> "pack_base._FieldOutcome":
    ledger = RawFactLedger(events=tuple(events))
    por = _date(2025, 9, 27)
    return pack_base._resolve_fact_mapping(
        pack_id="PK04",
        catalogue_field=_catalogue_field(
            "PK04", "contract_liability_rollforward_opening"
        ),
        mapping=pack_base.FactMapping(
            ("us-gaap:ContractWithCustomerLiability",),
            period_select="opening_instant",
        ),
        ledger=ledger,
        por=por,
        extension_prefixes={},
        opening_bound=pack_base._primary_duration_opening_bound(ledger, por),
    )


def test_opening_instant_selects_day_before_duration_start() -> None:
    outcome = _opening_outcome(
        [
            _synthetic_occurrence(
                "us-gaap:Revenues",
                start=_date(2024, 9, 29),
                end=_date(2025, 9, 27),
                value="416161000000",
            ),
            _synthetic_occurrence(
                "us-gaap:ContractWithCustomerLiability",
                instant=_date(2024, 9, 28),
                value="12800000000",
                decimals="-8",
            ),
            _synthetic_occurrence(
                "us-gaap:ContractWithCustomerLiability",
                instant=_date(2024, 8, 30),
                value="12000000000",
                decimals="-8",
            ),
        ]
    )
    assert outcome.row["quality_state"] == "valued"
    assert outcome.row["value"] == "12800000000"
    assert outcome.row["period"] == {"kind": "instant", "end": "2024-09-28"}


def test_opening_instant_falls_back_to_latest_before_start() -> None:
    outcome = _opening_outcome(
        [
            _synthetic_occurrence(
                "us-gaap:Revenues",
                start=_date(2024, 9, 29),
                end=_date(2025, 9, 27),
                value="416161000000",
            ),
            _synthetic_occurrence(
                "us-gaap:ContractWithCustomerLiability",
                instant=_date(2024, 9, 10),
                value="10000000000",
                decimals="-8",
            ),
            _synthetic_occurrence(
                "us-gaap:ContractWithCustomerLiability",
                instant=_date(2024, 9, 20),
                value="11000000000",
                decimals="-8",
            ),
        ]
    )
    assert outcome.row["value"] == "11000000000"
    assert outcome.row["period"] == {"kind": "instant", "end": "2024-09-20"}


def test_opening_instant_without_candidate_is_missing() -> None:
    outcome = _opening_outcome(
        [
            _synthetic_occurrence(
                "us-gaap:Revenues",
                start=_date(2024, 9, 29),
                end=_date(2025, 9, 27),
                value="416161000000",
            )
        ]
    )
    assert outcome.row["quality_state"] == "missing"
    assert outcome.row["reason"] == (
        "missing_standard_fact:us-gaap:ContractWithCustomerLiability"
    )


def _typed_outcome(events) -> "pack_base._FieldOutcome":
    return pack_base._resolve_typed_dimensioned_fact_mapping(
        pack_id="PK04",
        catalogue_field=_catalogue_field("PK04", "rpo_percentage_next_12m"),
        mapping=pk04_revenue._FIELD_MAPPINGS["rpo_percentage_next_12m"],
        ledger=RawFactLedger(events=tuple(events)),
        por=_date(2025, 9, 27),
    )


def _typed_member(iso_date: str) -> str:
    return (
        "<us-gaap:RevenueRemainingPerformanceObligationExpectedTimingOf"
        f"SatisfactionStartDateAxis.domain>{iso_date}</us-gaap:RevenueRemaining"
        "PerformanceObligationExpectedTimingOfSatisfactionStartDateAxis.domain>"
    )


def test_typed_dimensioned_selects_earliest_on_or_after_period_of_report() -> None:
    outcome = _typed_outcome(
        [
            _synthetic_occurrence(
                "us-gaap:RevenueRemainingPerformanceObligationPercentage",
                instant=_date(2025, 9, 27),
                typed=((RPO_TIMING_AXIS_QNAME, _typed_member("2026-09-27")),),
                value="0.23",
                decimals="2",
            ),
            _synthetic_occurrence(
                "us-gaap:RevenueRemainingPerformanceObligationPercentage",
                instant=_date(2025, 9, 27),
                typed=((RPO_TIMING_AXIS_QNAME, _typed_member("2025-09-26")),),
                value="0.90",
                decimals="2",
            ),
            _synthetic_occurrence(
                "us-gaap:RevenueRemainingPerformanceObligationPercentage",
                instant=_date(2025, 9, 27),
                typed=((RPO_TIMING_AXIS_QNAME, _typed_member("2025-09-28")),),
                value="0.66",
                decimals="2",
            ),
        ]
    )
    assert outcome.row["quality_state"] == "valued"
    assert outcome.row["value"] == "0.66"
    assert outcome.row["unit"] == "ratio"
    assert outcome.row["dimensions"] == [
        {"axis": RPO_TIMING_AXIS_QNAME, "member": "2025-09-28"}
    ]


def test_typed_dimensioned_skips_value_before_period_of_report() -> None:
    # The only typed values sit before period_of_report: none is admissible.
    outcome = _typed_outcome(
        [
            _synthetic_occurrence(
                "us-gaap:RevenueRemainingPerformanceObligationPercentage",
                instant=_date(2025, 9, 27),
                typed=((RPO_TIMING_AXIS_QNAME, _typed_member("2025-09-26")),),
                value="0.90",
                decimals="2",
            )
        ]
    )
    assert outcome.row["quality_state"] == "missing"
    assert outcome.row["reason"] == (
        "missing_standard_fact:us-gaap:RevenueRemaining"
        "PerformanceObligationPercentage"
    )


def test_typed_dimensioned_without_candidate_is_missing() -> None:
    outcome = _typed_outcome(())
    assert outcome.row["quality_state"] == "missing"
    assert outcome.row["reason"] == (
        "missing_standard_fact:us-gaap:RevenueRemaining"
        "PerformanceObligationPercentage"
    )
    assert outcome.row["value"] is None


# 37. PK04 bank probe, determinism, invariance, CLI ----------------------------


def test_pk04_bank_probe_is_not_applicable() -> None:
    bank = produce_pack("PK04", _pk04_input(issuer_sic="6021", sic_source="dei"))
    assert bank["applicability"]["state"] == "not_applicable"
    assert bank["applicability"]["reason"] == "bank_interest_not_contract_revenue"
    assert len(bank["fields"]) == 12
    for row in bank["fields"]:
        assert row["quality_state"] == "not_applicable"
        assert row["reason"] == "bank_interest_not_contract_revenue"
    for check in bank["checks"]:
        assert check["status"] == "not_applicable"
        assert check["reason"] == "bank_interest_not_contract_revenue"
    assert bank["coverage"]["disclosure_coverage_state"] == "not_supplied"
    assert contract.validate_pack_result(bank) == []


def test_pk04_unknown_sic_is_not_evaluable() -> None:
    result = produce_pack("PK04", _pk04_input(issuer_sic=None, sic_source=None))
    assert result["applicability"]["state"] == "not_evaluable"
    assert result["applicability"]["reason"] == "issuer_class_unknown"
    assert result["coverage"]["disclosure_coverage_state"] == "not_supplied"


def test_pk04_production_is_deterministic() -> None:
    first = produce_pack("PK04", _pk04_input())
    second = produce_pack("PK04", _pk04_input())
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["pack_content_sha256"] == second["pack_content_sha256"]


def test_pk02_envelope_digest_unchanged_by_pk04_edits() -> None:
    result = produce_pack("PK02", _pk02_input())
    payload = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert sha256(payload.encode("utf-8")).hexdigest() == PK02_ENVELOPE_SHA256


def test_pk04_cli_writes_valid_envelope(tmp_path: Path) -> None:
    entity_file = tmp_path / "entity.json"
    query_file = tmp_path / "query.json"
    out_file = tmp_path / "pk04.json"
    entity_file.write_text(json.dumps(ENTITY), encoding="utf-8")
    query_file.write_text(json.dumps(PK04_QUERY), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "fif_specialist_packs.py"),
            "--pack",
            "PK04",
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
    assert len(envelope["fields"]) == 20
    assert envelope["coverage"]["valued_fields"] == 15


# 38. PK03: segments and geographic/product dimensions --------------------------
#
# Fixture-verified through the raw ledger (FY2025 = 2024-09-29..2025-09-27):
# the filing tags no segment-count fact (the narrative "five reportable
# segments" is not extractable, R-K4'); segment-table facts carry BOTH the
# business-segment axis and ConsolidationItemsAxis = OperatingSegmentsMember;
# the only FY2025 eliminations-side fact under an allowlisted member is
# OperatingIncomeLoss -42,627,000,000 under CorporateNonSegmentMember (no
# revenue-basis ConsolidationItems row exists, so the revenue bridge ties on
# the parts alone: 178,353 + 111,032 + 64,377 + 28,703 + 33,696 = 416,161 =
# consolidated revenue); the geographic and product mirrors reproduce PK04's
# revenue_disaggregated rows exactly.

from engine.fundamental_forensics.specialist_packs import (  # noqa: E402
    pk03_segments,
)

PK03_QUERY = {**QUERY, "requested_metrics": ["segments"]}
# A.6: sha256 of the canonical JSON bytes of every BASE pack's envelope under
# this module's own inputs, recorded before the PK03 lane's edits; PK03 edits
# must not move any of them.
BASE_PACK_ENVELOPE_SHA256 = {
    "PK01": (
        "2c2e4623bf084b08b1652bc9b0b8ad209dfa280d6fc459274b6ea38d75761a57"
    ),
    "PK02": (
        "bab1af7e7ee25465d45ebd7ed8bac5315184f664d5bb8ebb77de9d0c48ae8356"
    ),
    "PK04": (
        "eefb6db8a185e63f676fb2b9109687bc368c2782f675659f136cef05174f2561"
    ),
    "PK06": (
        "36eb40f96a1bc8560fedf52268e3d522008eff8cdd259d242ec681269f37cd38"
    ),
    "PK09": (
        "78f5243b1c8b030edc598de0532c4ce18bc66cbd81067cbde467dd856885f949"
    ),
    "PK11": (
        "02295cda96fa64d1750a0cf709ce0a85bfeb3c55047e3ee94345f4e95cc14a8e"
    ),
    "PK12": (
        "c70e3ee97b56cffd43962dbb725b8e6ea356fa1f66976d06ffd35077f56f2a25"
    ),
}
SEGMENT_LEDGER_AXIS = "us-gaap:StatementBusinessSegmentsAxis"
CONSOLIDATION_ITEMS_LEDGER_AXIS = "{http://fasb.org/srt/2025}ConsolidationItemsAxis"
GEOGRAPHICAL_LEDGER_AXIS = "{http://fasb.org/srt/2025}StatementGeographicalAxis"
PRODUCT_OR_SERVICE_LEDGER_AXIS = (
    "{http://fasb.org/srt/2025}ProductOrServiceAxis"
)


def _aapl_member(local: str) -> str:
    return f"{{http://www.apple.com/20250927}}{local}"


# B.4: canonical member order, values in the facts' own scale (USD units).
SEGMENT_REVENUE_ROWS = [
    (_aapl_member("AmericasSegmentMember"), "178353000000"),
    (_aapl_member("EuropeSegmentMember"), "111032000000"),
    (_aapl_member("GreaterChinaSegmentMember"), "64377000000"),
    (_aapl_member("JapanSegmentMember"), "28703000000"),
    (_aapl_member("RestOfAsiaPacificSegmentMember"), "33696000000"),
]
SEGMENT_PROFIT_ROWS = [
    (_aapl_member("AmericasSegmentMember"), "72480000000"),
    (_aapl_member("EuropeSegmentMember"), "47739000000"),
    (_aapl_member("GreaterChinaSegmentMember"), "26917000000"),
    (_aapl_member("JapanSegmentMember"), "13955000000"),
    (_aapl_member("RestOfAsiaPacificSegmentMember"), "14586000000"),
]
GEOGRAPHIC_ROWS = [
    (_aapl_member("OtherCountriesMember"), "199994000000"),
    ("{http://xbrl.sec.gov/country/2025}CN", "64377000000"),
    ("{http://xbrl.sec.gov/country/2025}US", "151790000000"),
]
PRODUCT_SERVICE_ROWS = [
    (_aapl_member("IPadMember"), "28023000000"),
    (_aapl_member("IPhoneMember"), "209586000000"),
    (_aapl_member("MacMember"), "33708000000"),
    (_aapl_member("WearablesHomeandAccessoriesMember"), "35686000000"),
    ("us-gaap:ProductMember", "307003000000"),
    ("us-gaap:ServiceMember", "109158000000"),
]


def _pk03_input(**overrides) -> PackInput:
    defaults = dict(
        packages=(load_golden_aapl_package(ROOT, accession=ACCESSION),),
        entity=ENTITY,
        query=PK03_QUERY,
        issuer_sic="3571",
        sic_source="sec_submissions",
    )
    defaults.update(overrides)
    return PackInput(**defaults)


@pytest.fixture(scope="module")
def pk03_result() -> dict:
    return produce_pack("PK03", _pk03_input())


def test_pk03_result_passes_contract_validator(pk03_result: dict) -> None:
    assert contract.validate_pack_result(pk03_result) == []


def test_pk03_result_passes_jsonschema_envelope(pk03_result: dict) -> None:
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
        Draft202012Validator(schema, registry=registry).iter_errors(pk03_result)
    )
    assert errors == []


def test_pk03_rows_follow_catalogue_order_with_twenty_three_rows(
    pk03_result: dict,
) -> None:
    catalogue = contract.load_pack_schema("PK03")
    expected = [item["field_id"] for item in catalogue["fields"]]
    produced = [row["field_id"] for row in pk03_result["fields"]]
    assert len(produced) == 23  # 8 catalogue fields; the maps repeat
    compacted = [
        field_id
        for index, field_id in enumerate(produced)
        if index == 0 or produced[index - 1] != field_id
    ]
    assert compacted == expected
    position = produced.index("segment_revenue")
    assert produced[position + 4] == "segment_revenue"  # adjacent block
    assert [row["check_id"] for row in pk03_result["checks"]] == [
        item["check_id"] for item in catalogue["checks"]
    ]


def test_pk03_segment_revenue_rows(pk03_result: dict, ledger) -> None:
    rows = _rows(pk03_result, "segment_revenue")
    assert len(rows) == 5
    for row, (member, value) in zip(rows, SEGMENT_REVENUE_ROWS):
        assert row["quality_state"] == "valued"
        assert row["concept"] == (
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
        )
        assert row["value"] == value
        assert row["unit"] == "USD"
        assert row["period"] == {
            "kind": "duration",
            "start": "2024-09-29",
            "end": "2025-09-27",
        }
        # Each row carries BOTH the segment member and the fact's
        # ConsolidationItemsAxis = OperatingSegmentsMember dimension (the
        # framework records the fact's dimensions in canonical axis order).
        assert row["dimensions"] == [
            {"axis": SEGMENT_LEDGER_AXIS, "member": member},
            {
                "axis": CONSOLIDATION_ITEMS_LEDGER_AXIS,
                "member": "us-gaap:OperatingSegmentsMember",
            },
        ]
        assert row["mapping_rule_id"] == "PK03.segment_revenue.dimensioned_fact/v1"
        assert ledger.by_id(row["source_occurrence_ids"][0]) is not None


def test_pk03_segment_profit_rows(pk03_result: dict) -> None:
    rows = _rows(pk03_result, "segment_profit_or_loss")
    assert len(rows) == 5
    for row, (member, value) in zip(rows, SEGMENT_PROFIT_ROWS):
        assert row["quality_state"] == "valued"
        assert row["concept"] == "us-gaap:OperatingIncomeLoss"
        assert row["value"] == value
        assert row["dimensions"][0]["axis"] == SEGMENT_LEDGER_AXIS
        assert row["dimensions"][0]["member"] == member


def test_pk03_eliminations_row_is_signed_non_segment_fact(
    pk03_result: dict,
) -> None:
    rows = _rows(pk03_result, "unallocated_corporate_and_eliminations")
    assert len(rows) == 1
    row = rows[0]
    assert row["quality_state"] == "valued"
    assert row["concept"] == "us-gaap:OperatingIncomeLoss"
    assert row["value"] == "-42627000000"  # the fact carries sign="-"
    assert row["dimensions"] == [
        {
            "axis": CONSOLIDATION_ITEMS_LEDGER_AXIS,
            "member": "us-gaap:CorporateNonSegmentMember",
        }
    ]
    assert row["mapping_rule_id"] == (
        "PK03.unallocated_corporate_and_eliminations.dimensioned_fact/v1"
    )


def test_pk03_geographic_and_product_mirrors(pk03_result: dict) -> None:
    geographic = _rows(pk03_result, "geographic_revenue")
    assert len(geographic) == 3
    for row, (member, value) in zip(geographic, GEOGRAPHIC_ROWS):
        assert row["quality_state"] == "valued"
        assert row["value"] == value
        assert row["dimensions"] == [
            {"axis": GEOGRAPHICAL_LEDGER_AXIS, "member": member}
        ]
    product = _rows(pk03_result, "product_service_revenue")
    assert len(product) == 6
    for row, (member, value) in zip(product, PRODUCT_SERVICE_ROWS):
        assert row["quality_state"] == "valued"
        assert row["value"] == value
        assert row["dimensions"] == [
            {"axis": PRODUCT_OR_SERVICE_LEDGER_AXIS, "member": member}
        ]


def test_pk03_segment_count_is_missing_standard_fact(pk03_result: dict) -> None:
    row = _row(pk03_result, "number_of_operating_segments")
    assert row["quality_state"] == "missing"
    assert row["non_value_state"] == "missing"
    assert row["value"] is None
    assert row["reason"] == (
        "missing_standard_fact:us-gaap:NumberOfOperatingSegments"
    )


def test_pk03_text_fields_are_unsupported(pk03_result: dict) -> None:
    for field_id in ("segment_definition_change_note", "segment_reporting_text_block"):
        row = _row(pk03_result, field_id)
        assert row["quality_state"] == "unsupported"
        assert row["non_value_state"] == "unsupported"
        assert row["evidence_kind"] == "text_span"
        assert row["required_evidence_kind"] == "text_span"
        assert row["value"] is None


def test_pk03_revenue_bridge_passes_with_exact_tie_limitation(
    pk03_result: dict,
) -> None:
    check = _check(pk03_result, "segment_sum_plus_eliminations_equals_consolidated")
    assert check["status"] == "pass"
    assert check["reason"] is None
    assert check["tolerance"] == "1000000"
    assert check["evidence_field_ids"] == [
        "segment_revenue",
        "unallocated_corporate_and_eliminations",
    ]
    # 178,353 + 111,032 + 64,377 + 28,703 + 33,696 = 416,161 exactly, and the
    # eliminations field carries no revenue-basis row: the exact-tie note.
    assert (
        "pk03.segment_sum_plus_eliminations_equals_consolidated: eliminations"
        " absent, exact tie" in pk03_result["limitations"]
    )


def test_pk03_internal_revenue_not_double_counted_passes(
    pk03_result: dict,
) -> None:
    check = _check(pk03_result, "fp_internal_revenue_not_double_counted")
    assert check["status"] == "pass"
    assert check["reason"] is None
    assert check["tolerance"] == "1000000"
    assert check["evidence_field_ids"] == [
        "segment_revenue",
        "unallocated_corporate_and_eliminations",
    ]


def test_pk03_segment_count_consistent_awaits_count_fact(
    pk03_result: dict,
) -> None:
    check = _check(pk03_result, "segment_count_consistent")
    assert check["status"] == "not_evaluable"
    assert check["reason"] == "missing_dependency"
    assert check["evidence_field_ids"] == [
        "number_of_operating_segments",
        "segment_revenue",
    ]


def test_pk03_coverage_counts(pk03_result: dict) -> None:
    assert pk03_result["coverage"] == {
        "valued_fields": 20,
        "missing_fields": 1,
        "unsupported_fields": 2,
        "not_evaluable_fields": 0,
        "not_applicable_fields": 0,
        "disclosure_coverage_state": "present",
    }


# 39. PK03 A.4/A.5/A.3 synthetic checks -----------------------------------------


def _syn_check_ledger(*events) -> RawFactLedger:
    return RawFactLedger(events=tuple(events))


def _syn_undim_occurrence(concept: str, value: str) -> RawFactOccurrence:
    return _synthetic_occurrence(
        concept, start=_date(2024, 9, 29), end=_date(2025, 9, 27), value=value
    )


def _syn_segment_row(member: str, value: str) -> dict:
    return {
        "field_id": "segment_revenue",
        "quality_state": "valued",
        "value": value,
        "concept": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "unit": "USD",
        "reason": None,
        "dimensions": [
            {
                "axis": CONSOLIDATION_ITEMS_LEDGER_AXIS,
                "member": "us-gaap:OperatingSegmentsMember",
            },
            {"axis": SEGMENT_LEDGER_AXIS, "member": member},
        ],
    }


def _syn_elimination_row(
    value: str,
    concept: str = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
) -> dict:
    return {
        "field_id": "unallocated_corporate_and_eliminations",
        "quality_state": "valued",
        "value": value,
        "concept": concept,
        "unit": "USD",
        "reason": None,
        "dimensions": [
            {
                "axis": CONSOLIDATION_ITEMS_LEDGER_AXIS,
                "member": "us-gaap:IntersegmentEliminationMember",
            }
        ],
    }


def _syn_field_outcome(field_id: str, rows: list, concept: str) -> object:
    if rows:
        return pack_base._FieldOutcome(
            row=rows[0],
            value=None,
            decimals=-6,
            unit="USD",
            extra_rows=tuple(rows[1:]),
        )
    return pack_base._FieldOutcome(
        row={
            "field_id": field_id,
            "quality_state": "missing",
            "value": None,
            "concept": concept,
            "unit": "USD",
            "reason": "missing_dependency",
            "dimensions": [],
        },
        value=None,
        decimals=None,
        unit="USD",
    )


class _SynCheckPackage:
    manifest = {
        "form": "10-K",
        "period_of_report": "2025-09-27",
        "accession": "0000000000-00-000000",
    }
    members: dict = {}


_SYN_PK03_INPUT = PackInput(
    packages=(_SynCheckPackage(),), entity={"entity_id": "syn"}, query={"q": 1}
)


def _pk03_check_outcomes(
    segment_rows: list, elimination_rows: list
) -> dict:
    return {
        "segment_revenue": _syn_field_outcome(
            "segment_revenue",
            segment_rows,
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        ),
        "unallocated_corporate_and_eliminations": _syn_field_outcome(
            "unallocated_corporate_and_eliminations",
            elimination_rows,
            "us-gaap:OperatingIncomeLoss",
        ),
    }


def _run_pk03_catalogue_check(
    check_id: str, outcomes: dict, ledger_events: tuple
) -> dict:
    catalogue_check = next(
        item
        for item in contract.load_pack_schema("PK03")["checks"]
        if item["check_id"] == check_id
    )
    specs = [
        spec
        for spec in pk03_segments.PRODUCER.checks
        if spec.check_id == check_id
    ]
    resolver = pack_base._OperandResolver(
        outcomes,
        _SYN_PK03_INPUT,
        foreign_cache={},
        ledger=_syn_check_ledger(*ledger_events),
        por=_date(2025, 9, 27),
    )
    return pack_base._evaluate_check(
        catalogue_check,
        specs,
        resolver,
        check_rules=pk03_segments.PRODUCER.check_rules,
        limitation_sink=[],
        pack_id="PK03",
    )


_SYN_FIVE_SEGMENTS = [
    _syn_segment_row(member, "100000000") for member in "abcde"
]
_SYN_REVENUE_CONCEPT = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"


def _pk03_a4_check(segment_rows, elimination_rows, consolidated) -> tuple:
    outcomes = _pk03_check_outcomes(segment_rows, elimination_rows)
    events = (
        (_syn_undim_occurrence(_SYN_REVENUE_CONCEPT, consolidated),)
        if consolidated is not None
        else ()
    )
    sink: list[str] = []
    catalogue_check = next(
        item
        for item in contract.load_pack_schema("PK03")["checks"]
        if item["check_id"] == "segment_sum_plus_eliminations_equals_consolidated"
    )
    specs = [
        spec
        for spec in pk03_segments.PRODUCER.checks
        if spec.check_id == "segment_sum_plus_eliminations_equals_consolidated"
    ]
    resolver = pack_base._OperandResolver(
        outcomes,
        _SYN_PK03_INPUT,
        foreign_cache={},
        ledger=_syn_check_ledger(*events),
        por=_date(2025, 9, 27),
    )
    row = pack_base._evaluate_check(
        catalogue_check, specs, resolver, limitation_sink=sink, pack_id="PK03"
    )
    return row, sink


def test_pk03_a4_passes_with_valued_elimination_and_no_tie_limitation() -> None:
    # parts 500M + elimination -100M = 400M = consolidated revenue.
    row, sink = _pk03_a4_check(
        _SYN_FIVE_SEGMENTS, [_syn_elimination_row("-100000000")], "400000000"
    )
    assert row["status"] == "pass"
    assert row["reason"] is None
    assert row["tolerance"] == "1000000"
    assert sink == []


def test_pk03_a4_fails_when_parts_plus_elimination_off_by_two_million() -> None:
    # 500M - 98M = 402M vs 400M consolidated: outside the 1M tolerance.
    row, _sink = _pk03_a4_check(
        _SYN_FIVE_SEGMENTS, [_syn_elimination_row("-98000000")], "400000000"
    )
    assert row["status"] == "fail"
    assert row["reason"] is None


def test_pk03_a4_elimination_absent_and_parts_not_tying_is_not_evaluable() -> None:
    row, sink = _pk03_a4_check(_SYN_FIVE_SEGMENTS, [], "400000000")
    assert row["status"] == "not_evaluable"
    assert row["reason"] == "missing_dependency"
    assert sink == []  # never an implied zero, never the exact-tie note


def test_pk03_a4_exact_tie_emits_the_limitation_string() -> None:
    row, sink = _pk03_a4_check(_SYN_FIVE_SEGMENTS, [], "500000000")
    assert row["status"] == "pass"
    assert row["reason"] is None
    assert sink == [
        "pk03.segment_sum_plus_eliminations_equals_consolidated: eliminations"
        " absent, exact tie"
    ]


def test_pk03_a4_profit_basis_elimination_row_is_not_revenue_basis() -> None:
    # The only elimination row is OperatingIncomeLoss (a profit figure): it
    # never joins the revenue bridge, so the bridge ties on the parts alone.
    row, sink = _pk03_a4_check(
        _SYN_FIVE_SEGMENTS,
        [_syn_elimination_row("-100000000", concept="us-gaap:OperatingIncomeLoss")],
        "500000000",
    )
    assert row["status"] == "pass"
    assert sink == [
        "pk03.segment_sum_plus_eliminations_equals_consolidated: eliminations"
        " absent, exact tie"
    ]


def test_pk03_a4_consolidated_not_valued_is_not_evaluable() -> None:
    row, _sink = _pk03_a4_check(
        _SYN_FIVE_SEGMENTS, [_syn_elimination_row("-100000000")], None
    )
    assert row["status"] == "not_evaluable"
    assert row["reason"] == "missing_dependency"


def _run_pk03_fp_check(segment_rows, elimination_rows, ledger_events):
    catalogue_check = next(
        item
        for item in contract.load_pack_schema("PK03")["checks"]
        if item["check_id"] == "fp_internal_revenue_not_double_counted"
    )
    outcomes = _pk03_check_outcomes(segment_rows, elimination_rows)
    ledger = _syn_check_ledger(*ledger_events) if ledger_events is not None else None
    produced = pk03_segments._fp_internal_revenue_not_double_counted(
        _SYN_PK03_INPUT, ledger, outcomes, catalogue_check
    )
    assert produced is not None
    row, limitations = produced
    assert limitations == ()
    return row


def test_pk03_a5_repeated_member_fails() -> None:
    duplicated = _SYN_FIVE_SEGMENTS + [_syn_segment_row("a", "50000000")]
    row = _run_pk03_fp_check(
        duplicated, [], (_syn_undim_occurrence(_SYN_REVENUE_CONCEPT, "550000000"),)
    )
    assert row["status"] == "fail"
    assert row["reason"] is None


def test_pk03_a5_sum_exceeding_consolidated_fails() -> None:
    row = _run_pk03_fp_check(
        _SYN_FIVE_SEGMENTS,
        [],
        (_syn_undim_occurrence(_SYN_REVENUE_CONCEPT, "400000000"),),
    )
    assert row["status"] == "fail"
    assert row["reason"] is None


def test_pk03_a5_within_tolerance_and_revenue_eliminations_count() -> None:
    # 500M parts + 40M revenue-basis elimination = 540M <= 540M + 1M.
    row = _run_pk03_fp_check(
        _SYN_FIVE_SEGMENTS,
        [_syn_elimination_row("40000000")],
        (_syn_undim_occurrence(_SYN_REVENUE_CONCEPT, "540000000"),),
    )
    assert row["status"] == "pass"
    # 500M + 60M = 560M > 540M + 1M: the elimination rows do count.
    row = _run_pk03_fp_check(
        _SYN_FIVE_SEGMENTS,
        [_syn_elimination_row("60000000")],
        (_syn_undim_occurrence(_SYN_REVENUE_CONCEPT, "540000000"),),
    )
    assert row["status"] == "fail"


def test_pk03_a5_missing_dependencies_are_not_evaluable() -> None:
    row = _run_pk03_fp_check(_SYN_FIVE_SEGMENTS, [], None)
    assert row["status"] == "not_evaluable"
    assert row["reason"] == "missing_dependency"
    row = _run_pk03_fp_check(
        [], [], (_syn_undim_occurrence(_SYN_REVENUE_CONCEPT, "400000000"),)
    )
    assert row["status"] == "not_evaluable"
    assert row["reason"] == "missing_dependency"


def _run_pk03_count_check(count_value: str | None, segment_rows) -> dict:
    outcomes = _pk03_check_outcomes(segment_rows, [])
    if count_value is None:
        outcomes["number_of_operating_segments"] = _syn_field_outcome(
            "number_of_operating_segments", [], "us-gaap:NumberOfOperatingSegments"
        )
    else:
        outcomes["number_of_operating_segments"] = pack_base._FieldOutcome(
            row={
                "field_id": "number_of_operating_segments",
                "quality_state": "valued",
                "value": count_value,
                "concept": "us-gaap:NumberOfOperatingSegments",
                "unit": None,
                "reason": None,
                "dimensions": [],
            },
            value=Decimal(count_value),
            decimals=None,
            unit=None,
        )
    return _run_pk03_catalogue_check(
        "segment_count_consistent", outcomes, ()
    )


def test_pk03_a3_count_five_with_five_rows_passes() -> None:
    row = _run_pk03_count_check("5", _SYN_FIVE_SEGMENTS)
    assert row["status"] == "pass"
    assert row["reason"] is None


def test_pk03_a3_count_four_with_five_rows_fails() -> None:
    row = _run_pk03_count_check("4", _SYN_FIVE_SEGMENTS)
    assert row["status"] == "fail"
    assert row["reason"] is None


def test_pk03_a3_missing_count_is_not_evaluable() -> None:
    row = _run_pk03_count_check(None, _SYN_FIVE_SEGMENTS)
    assert row["status"] == "not_evaluable"
    assert row["reason"] == "missing_dependency"


# 40. PK03 A.1/A.2 mapping semantics on synthetic ledgers -----------------------


def _syn_dim_occurrence(
    concept: str, dimensions: tuple, value: str
) -> RawFactOccurrence:
    return _synthetic_occurrence(
        concept,
        start=_date(2024, 9, 29),
        end=_date(2025, 9, 27),
        explicit=tuple(sorted(dimensions)),
        value=value,
    )


def _pk03_catalogue_field(field_id: str) -> dict:
    return next(
        item
        for item in contract.load_pack_schema("PK03")["fields"]
        if item["field_id"] == field_id
    )


def test_pk03_a2_allowlist_emits_declared_concept_then_member_order() -> None:
    mapping = pk03_segments._FIELD_MAPPINGS[
        "unallocated_corporate_and_eliminations"
    ]
    events = [
        # IntersegmentEliminationMember is allowlisted (3rd) and canonically
        # first; CorporateNonSegmentMember is allowlisted 1st. Two concepts
        # carry facts; concept order dominates, then allowlist declaration
        # order — never canonical member order.
        _syn_dim_occurrence(
            "us-gaap:OperatingIncomeLoss",
            (
                (
                    CONSOLIDATION_ITEMS_LEDGER_AXIS,
                    "us-gaap:IntersegmentEliminationMember",
                ),
            ),
            "-5000000",
        ),
        _syn_dim_occurrence(
            "us-gaap:Revenues",
            ((CONSOLIDATION_ITEMS_LEDGER_AXIS, "us-gaap:CorporateNonSegmentMember"),),
            "7000000",
        ),
        _syn_dim_occurrence(
            "us-gaap:OperatingIncomeLoss",
            ((CONSOLIDATION_ITEMS_LEDGER_AXIS, "us-gaap:CorporateNonSegmentMember"),),
            "-42000000",
        ),
    ]
    outcome = pack_base._resolve_allowlist_dimensioned_fact_mapping(
        pack_id="PK03",
        catalogue_field=_pk03_catalogue_field(
            "unallocated_corporate_and_eliminations"
        ),
        mapping=mapping,
        ledger=_syn_check_ledger(*events),
        por=_date(2025, 9, 27),
    )
    rows = [outcome.row, *outcome.extra_rows]
    assert [
        (row["concept"], row["dimensions"][0]["member"], row["value"])
        for row in rows
    ] == [
        ("us-gaap:Revenues", "us-gaap:CorporateNonSegmentMember", "7000000"),
        (
            "us-gaap:OperatingIncomeLoss",
            "us-gaap:CorporateNonSegmentMember",
            "-42000000",
        ),
        (
            "us-gaap:OperatingIncomeLoss",
            "us-gaap:IntersegmentEliminationMember",
            "-5000000",
        ),
    ]
    assert outcome.value == Decimal("-40000000")


def test_pk03_a2_ignores_other_members_and_extra_dimensions() -> None:
    mapping = pk03_segments._FIELD_MAPPINGS[
        "unallocated_corporate_and_eliminations"
    ]
    events = [
        # A non-allowlisted member on the admitted axis: silently ignored.
        _syn_dim_occurrence(
            "us-gaap:Revenues",
            ((CONSOLIDATION_ITEMS_LEDGER_AXIS, "us-gaap:OtherMember"),),
            "999",
        ),
        # An allowlisted member that also carries another explicit dimension:
        # ignored (facts must carry no other explicit dimension).
        _syn_dim_occurrence(
            "us-gaap:Revenues",
            (
                (
                    CONSOLIDATION_ITEMS_LEDGER_AXIS,
                    "us-gaap:MaterialReconcilingItemsMember",
                ),
                (SEGMENT_LEDGER_AXIS, _aapl_member("AmericasSegmentMember")),
            ),
            "888",
        ),
        _syn_dim_occurrence(
            "us-gaap:Revenues",
            ((CONSOLIDATION_ITEMS_LEDGER_AXIS, "us-gaap:CorporateNonSegmentMember"),),
            "7000000",
        ),
    ]
    outcome = pack_base._resolve_allowlist_dimensioned_fact_mapping(
        pack_id="PK03",
        catalogue_field=_pk03_catalogue_field(
            "unallocated_corporate_and_eliminations"
        ),
        mapping=mapping,
        ledger=_syn_check_ledger(*events),
        por=_date(2025, 9, 27),
    )
    rows = [outcome.row, *outcome.extra_rows]
    assert len(rows) == 1
    assert rows[0]["dimensions"][0]["member"] == "us-gaap:CorporateNonSegmentMember"
    assert rows[0]["value"] == "7000000"


def test_pk03_a2_zero_rows_missing_names_first_concept() -> None:
    mapping = pk03_segments._FIELD_MAPPINGS[
        "unallocated_corporate_and_eliminations"
    ]
    outcome = pack_base._resolve_allowlist_dimensioned_fact_mapping(
        pack_id="PK03",
        catalogue_field=_pk03_catalogue_field(
            "unallocated_corporate_and_eliminations"
        ),
        mapping=mapping,
        ledger=_syn_check_ledger(),
        por=_date(2025, 9, 27),
    )
    assert outcome.row["quality_state"] == "missing"
    assert outcome.row["reason"] == (
        "missing_standard_fact:us-gaap:RevenueFromContractWithCustomer"
        "ExcludingAssessedTax"
    )
    assert outcome.value is None


def test_pk03_a1_grouped_emits_per_concept_in_declared_order() -> None:
    mapping = pk03_segments._FIELD_MAPPINGS["segment_revenue"]
    package = load_golden_aapl_package(ROOT, accession=ACCESSION)
    def_xml = next(
        payload
        for name, payload in sorted(package.members.items())
        if name.endswith("_def.xml")
    )
    groups = definition_linkbase.parse_axis_member_groups(def_xml)
    events = [
        _syn_dim_occurrence(
            "us-gaap:Revenues",
            (
                (SEGMENT_LEDGER_AXIS, _aapl_member("JapanSegmentMember")),
                (CONSOLIDATION_ITEMS_LEDGER_AXIS, "us-gaap:OperatingSegmentsMember"),
            ),
            "1",
        ),
        _syn_dim_occurrence(
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            (
                (SEGMENT_LEDGER_AXIS, _aapl_member("AmericasSegmentMember")),
                (CONSOLIDATION_ITEMS_LEDGER_AXIS, "us-gaap:OperatingSegmentsMember"),
            ),
            "2",
        ),
        _syn_dim_occurrence(
            "us-gaap:Revenues",
            (
                (SEGMENT_LEDGER_AXIS, _aapl_member("AmericasSegmentMember")),
                (CONSOLIDATION_ITEMS_LEDGER_AXIS, "us-gaap:OperatingSegmentsMember"),
            ),
            "3",
        ),
    ]
    outcome = pack_base._resolve_grouped_dimensioned_fact_mapping(
        pack_id="PK03",
        catalogue_field=_pk03_catalogue_field("segment_revenue"),
        mapping=mapping,
        ledger=_syn_check_ledger(*events),
        por=_date(2025, 9, 27),
        axis_groups=groups,
        limitation_sink=None,
    )
    rows = [outcome.row, *outcome.extra_rows]
    # Concept-major order: every first-concept row (canonical member order),
    # then the second concept's rows — each row names its own concept.
    assert [
        (row["concept"], row["dimensions"][0]["member"], row["value"])
        for row in rows
    ] == [
        (
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            _aapl_member("AmericasSegmentMember"),
            "2",
        ),
        ("us-gaap:Revenues", _aapl_member("AmericasSegmentMember"), "3"),
        ("us-gaap:Revenues", _aapl_member("JapanSegmentMember"), "1"),
    ]


# 41. PK03 bank probe, determinism, invariance, registry, CLI, A33 ---------------


def test_pk03_bank_probe_keeps_pack_applicable(pk03_result: dict) -> None:
    bank = produce_pack("PK03", _pk03_input(issuer_sic="6021", sic_source="dei"))
    assert bank["applicability"]["state"] == "applicable"
    assert bank["applicability"]["reason"] == "applicability_rule_satisfied"
    assert bank["fields"] == pk03_result["fields"]
    assert bank["checks"] == pk03_result["checks"]
    assert "issuer_class=bank" in bank["receipts"]
    assert contract.validate_pack_result(bank) == []


def test_pk03_unknown_sic_keeps_pack_applicable() -> None:
    result = produce_pack("PK03", _pk03_input(issuer_sic=None, sic_source=None))
    # PK03 declares no applicable_classes: the class gate is never consulted.
    assert result["applicability"]["state"] == "applicable"


def test_pk03_production_is_deterministic() -> None:
    first = produce_pack("PK03", _pk03_input())
    second = produce_pack("PK03", _pk03_input())
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["pack_content_sha256"] == second["pack_content_sha256"]


def test_base_pack_envelopes_unchanged_by_pk03_edits() -> None:
    for pack_id, expected in BASE_PACK_ENVELOPE_SHA256.items():
        result = produce_pack(pack_id, _pk03_input())
        payload = json.dumps(
            result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        assert sha256(payload.encode("utf-8")).hexdigest() == expected, pack_id


def test_registered_pack_ids_is_base_set_plus_pk03() -> None:
    assert registered_pack_ids() == (
        "PK01",
        "PK02",
        "PK03",
        "PK04",
        "PK06",
        "PK09",
        "PK11",
        "PK12",
    )


def test_pk03_cli_writes_valid_envelope(tmp_path: Path) -> None:
    entity_file = tmp_path / "entity.json"
    query_file = tmp_path / "query.json"
    out_file = tmp_path / "pk03.json"
    entity_file.write_text(json.dumps(ENTITY), encoding="utf-8")
    query_file.write_text(json.dumps(PK03_QUERY), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "fif_specialist_packs.py"),
            "--pack",
            "PK03",
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
    assert envelope["coverage"]["valued_fields"] == 20


def test_pk03_no_issuer_literals_in_specialist_pack_code() -> None:
    # A33: the specialist-pack production surface (every producer module, the
    # shared framework and the offline CLI) carries no issuer literal.
    production_files = sorted(
        (ROOT / "engine" / "fundamental_forensics" / "specialist_packs").glob("*.py")
    ) + [ROOT / "scripts" / "fif_specialist_packs.py"]
    assert production_files
    for path in production_files:
        text = path.read_text("utf-8")
        for literal in ("0000320193", "AAPL", "Apple"):
            assert literal not in text, f"{path.name} carries {literal!r}"
