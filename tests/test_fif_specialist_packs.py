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
PK10 (proxy compensation and governance) reads DEF 14A packages only. No
proxy capture path exists at this BASE, so the AAPL 10-K fixture proves the
honest not-supplied envelope (applicability ``not_evaluable`` +
``proxy_package_not_supplied``), and a synthetic in-test DEF 14A package
proves the supplied path: four text-span rows valued, six reserved
table-cell rows abstaining typed, a prose numeral typed
``numeric_value_in_narrative_only`` and never scraped.

PK07 (M&A, goodwill, intangibles and impairments) makes AAPL the NEGATIVE
issuer: the fixture ledger carries no fact for any of the nine numeric
concepts (verified by scan), so every numeric row is a typed
missing_standard_fact absence while applicability stays applicable. The
positive path — prior-instant rollforward arithmetic, impairment pairs and
the Note 3 / Note 4 narrative — is proven on a synthetic in-test TESTCO
inline-XBRL 10-K admitted by the same strict parser path as the golden
fixture. The frozen PK07 catalogue carries no narrative reason code, so the
producer's finalize hook runs the B.2 section search itself and types every
narrative absence ``missing_dependency`` (the PK10 ruling), carrying the
intended stock code verbatim in limitations.

PK08 (legal contingencies) is the first nil-ledger pack: the fixture's
undimensioned nil balance-sheet line resolves through the framework's new
NilStateMapping (A.1) and the loss-contingency axis through AxisMemberMapping
(A.2), while the five narrative fields ride the PK07 finalize pattern over
Note 12's Contingencies subsection and Item 3. The accrual-vs-range
arithmetic, the C2 prose-only range ruling, the valued axis member and the
10-Q / 8-K form gates are proven on a synthetic in-test TESTCO filing.
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
from engine.fundamental_forensics.specialist_packs import pk08_contingencies
from engine.fundamental_forensics.specialist_packs import pk09_controls
from engine.fundamental_forensics.specialist_packs import pk10_proxy
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
    assert registered_pack_ids() == ("PK01", "PK02", "PK03", "PK04", "PK05", "PK06", "PK07", "PK08", "PK09", "PK10", "PK11", "PK12")
    assert set(PACK_PRODUCERS) == {"PK01", "PK02", "PK03", "PK04", "PK05", "PK06", "PK07", "PK08", "PK09", "PK10", "PK11", "PK12"}
    # PK03 lane: the BASE set plus PK03, sorted (never a removal).
    # PK05 lane: the set above plus PK05, still sorted (never a removal).
    # PK07 lane: the set above plus PK07, still sorted (never a removal).
    # PK08 lane: the set above plus PK08 — every catalogue id now has a
    # producer, so this lane's refusal probe moves to the never-registered
    # PK00 (the refusal branch is unchanged).
    assert registered_pack_ids() == ("PK01", "PK02", "PK03", "PK04", "PK05", "PK06", "PK07", "PK08", "PK09", "PK10", "PK11", "PK12")
    assert set(PACK_PRODUCERS) == {"PK01", "PK02", "PK03", "PK04", "PK05", "PK06", "PK07", "PK08", "PK09", "PK10", "PK11", "PK12"}
    with pytest.raises(SpecialistPackError, match="no producer registered: PK00"):
        produce_pack("PK00", _pack_input())
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
        "engine/fundamental_forensics/specialist_packs/pk07_mna.py",
        "engine/fundamental_forensics/specialist_packs/pk08_contingencies.py",
        "engine/fundamental_forensics/specialist_packs/pk01_debt.py",
        "engine/fundamental_forensics/specialist_packs/pk02_sbc.py",
        "engine/fundamental_forensics/specialist_packs/narrative.py",
        "engine/fundamental_forensics/specialist_packs/pk09_controls.py",
        "engine/fundamental_forensics/specialist_packs/pk10_proxy.py",
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
    "c40156a18aafe50874476dd7354a0cf8eb9dc90cb25afe88d409dd3320f56310"
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
                "cik": TESTBANK_CIK,  # R-F4: package issuer == packet entity
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
    "da96915b1d81f0f4417e6cb4d5acbc551f5fbfcc5975dc37091adfec9be5cceb"
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
    # Fold ruling R-FOLD-DIGEST: the PK-FW repair's R-F10 names every text-type
    # field the numeric-only converter cannot value, after the display-only line.
    assert result["limitations"] == [
        pack_base.DISPLAY_ONLY_LIMITATION,
        "atm_or_shelf_span: text-type field; numeric-only converter cannot value it",
        "going_concern_or_liquidity_span: text-type field; numeric-only converter cannot value it",
    ]
    assert "issuer_class=industrial" in result["receipts"]
    assert "sic_in_biotech_set=false" in result["receipts"]
    assert "pre_revenue_test=false" in result["receipts"]
    assert contract.validate_pack_result(result) == []
    # §TESTS 1: BASE packs plus PK12, not the full twelve at this BASE.
    # PK07 lane: the set above plus PK07 (see section 50 for the pin).
    # PK08 lane: the set above plus PK08 (see section 51 for the pin).
    assert registered_pack_ids() == ("PK01", "PK02", "PK03", "PK04", "PK05", "PK06", "PK07", "PK08", "PK09", "PK10", "PK11", "PK12")


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
    "a72ad598f809484c0026a06957ec92722ea74608563084e64c70dd10f033f97b"
)
# (PK01_ENVELOPE_SHA256 is pinned once, in the PK02 section above.)
PK06_CONTENT_SHA256 = (
    "398f1458c908890921f694c8ff54130c473011e064f99e7a0d5dd165ea087298"
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


# R-F4: a synthetic package belongs to its own synthetic issuer; the packet
# entity must carry the same CIK or the framework refuses the package.
SYNTHETIC_ENTITY = {
    **ENTITY,
    "entity_id": "ISS:TEST",
    "cik": "0000000099",
    "source_entity_id": "0000000099",
}


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
        _pk09_input(
            packages=(_synthetic_package("10-Q", body),), entity=SYNTHETIC_ENTITY
        ),
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
        _pk09_input(
            packages=(_synthetic_package("10-K", body),), entity=SYNTHETIC_ENTITY
        ),
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
    "9f621f9e750b1c9df6731eae1f9e0c8c2094006214d37b29066c08ea7e51d981"
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


# 38. PK10: proxy compensation and governance (DEF 14A) -----------------------
#
# The committed AAPL fixture carries no DEF 14A package (no proxy capture
# path exists at this BASE; it is owned by the D3 seam), so AAPL proves the
# honest not-supplied envelope. The supplied path is proven on a synthetic
# in-test DEF 14A package admitted by the same strict parser path as the
# golden fixture, reusing the PK09 synthetic-package builder.

PK10_QUERY = {**QUERY, "requested_metrics": ["proxy"]}
# Invariance pins captured at BASE before this lane's edits (§TESTS 4): PK10
# registration must not move any BASE pack's AAPL envelope. PK06/PK01/PK12
# carry their own pins earlier in this file; this map re-asserts all six
# canonical envelope digests in one place (PK02/PK11/PK09 are pinned here
# for the first time).
BASE_AAPL_ENVELOPE_SHA256 = {
    "PK06": "64b2d42f2148bdf4c9aaf69aae562e53aae26d54bc9386264ce485f80a322c05",
    "PK01": "c40156a18aafe50874476dd7354a0cf8eb9dc90cb25afe88d409dd3320f56310",
    "PK02": "9f621f9e750b1c9df6731eae1f9e0c8c2094006214d37b29066c08ea7e51d981",
    "PK11": "f425680270c2a267d8dca5f44e6a1e3c2ac708b124e2d2a7723c0674056d9b2f",
    "PK12": "da96915b1d81f0f4417e6cb4d5acbc551f5fbfcc5975dc37091adfec9be5cceb",
    "PK09": "451380196c80b7685e1103acbf1950a65c57ec460188738dec66d006421d474e",
}
_BASE_PACK_METRICS = {
    "PK06": "leases",
    "PK01": "debt",
    "PK02": "stock_compensation",
    "PK11": "bank",
    "PK12": "cash_runway",
    "PK09": "controls",
}
# This producer's own byte-determinism pin, captured at the lane's fork
# point after the PK10 producer landed.
PK10_AAPL_ENVELOPE_SHA256 = (
    "73868ffdb6f170d62022225ab3f1b0d1cb572716b39c5ae86b4f4d823668e52a"
)
PK10_TABLE_CELL_FIELDS = (
    "ceo_total_comp",
    "other_neo_total",
    "comp_actually_paid_peo",
    "compensation_year",
    "total_shareholder_return",
    "peer_group_tsr",
)
PK10_TEXT_SPAN_FIELDS = (
    "performance_measure_selected",
    "director_independence_span",
    "related_party_span",
    "say_on_pay_frequency",
)


def _pk10_input(**overrides) -> PackInput:
    defaults = dict(
        packages=(load_golden_aapl_package(ROOT, accession=ACCESSION),),
        entity=ENTITY,
        query=PK10_QUERY,
        issuer_sic="3571",
        sic_source="sec_submissions",
    )
    defaults.update(overrides)
    return PackInput(**defaults)


@pytest.fixture(scope="module")
def pk10_result() -> dict:
    return produce_pack("PK10", _pk10_input())


def test_pk10_aapl_not_supplied_envelope(pk10_result: dict) -> None:
    # §TESTS 1 / B.5: no DEF 14A package admitted -> not_evaluable +
    # proxy_package_not_supplied (never form_outside_pack_forms: the pack is
    # applicable in principle to every issuer).
    assert pk10_result["applicability"]["state"] == "not_evaluable"
    assert pk10_result["applicability"]["reason"] == "proxy_package_not_supplied"
    assert pk10_result["applicability"]["rule_id"] == "pack.pk10.applicability/v1"
    catalogue = contract.load_pack_schema("PK10")
    assert [row["field_id"] for row in pk10_result["fields"]] == [
        item["field_id"] for item in catalogue["fields"]
    ]
    for row in pk10_result["fields"]:
        assert row["quality_state"] == "not_evaluable"
        assert row["non_value_state"] == "not_evaluable"
        assert row["coverage_state"] == "unmapped"
        assert row["reason"] == "proxy_package_not_supplied"
        assert row["value"] is None and row["text_value"] is None
        assert row["source_span"] is None
    assert [check["check_id"] for check in pk10_result["checks"]] == [
        item["check_id"] for item in catalogue["checks"]
    ]
    for check in pk10_result["checks"]:
        assert check["status"] == "not_evaluable"
        assert check["reason"] == "proxy_package_not_supplied"
    assert pk10_result["coverage"] == {
        "valued_fields": 0,
        "missing_fields": 0,
        "unsupported_fields": 0,
        "not_evaluable_fields": 10,
        "not_applicable_fields": 0,
        "disclosure_coverage_state": "not_supplied",
    }
    assert "proxy_forms_seen=none" in pk10_result["receipts"]
    assert (
        "pk10.proxy_package_not_supplied: no DEF 14A package admitted for "
        "this entity; capture path owned by the D3 seam"
        in pk10_result["limitations"]
    )
    assert contract.validate_pack_result(pk10_result) == []


def test_pk10_aapl_envelope_digest_is_pinned() -> None:
    result = produce_pack("PK10", _pk10_input())
    payload = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert sha256(payload.encode("utf-8")).hexdigest() == PK10_AAPL_ENVELOPE_SHA256


def test_pk10_production_is_deterministic() -> None:
    first = produce_pack("PK10", _pk10_input())
    second = produce_pack("PK10", _pk10_input())
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["pack_content_sha256"] == second["pack_content_sha256"]


def test_pk10_cli_not_supplied_run_exits_zero(tmp_path: Path) -> None:
    # The CLI's frozen rule (scripts/fif_specialist_packs.py docstring): exit
    # 0 is a produced envelope in ANY applicability state — including PK10's
    # not_evaluable not-supplied result; 2 is a usage error, 1 a refusal.
    entity_file = tmp_path / "entity.json"
    query_file = tmp_path / "query.json"
    out_file = tmp_path / "pk10.json"
    entity_file.write_text(json.dumps(ENTITY), encoding="utf-8")
    query_file.write_text(json.dumps(PK10_QUERY), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "fif_specialist_packs.py"),
            "--pack",
            "PK10",
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
    assert envelope["applicability"]["state"] == "not_evaluable"
    assert envelope["applicability"]["reason"] == "proxy_package_not_supplied"
    assert "proxy_forms_seen=none" in envelope["receipts"]


# The supplied probe: a tiny DEF 14A primary document. The preamble sentence
# ends with ". " so every following sentence-span text_value starts at its
# own sentence (the whole text is the section; no Item-numbered sections
# exist in a proxy statement).
_PK10_PROXY_BODY = (
    "<div>Proxy statement of Test Co for the 2026 meeting of stockholders."
    "</div>"
    "<div>The most important performance measure for fiscal 2025 executive"
    " compensation was adjusted operating income.</div>"
    "<div>The Board has determined that each director is independent under"
    " the listing standards of the national securities exchange on which"
    " the Company's common stock is listed.</div>"
    "<div>All related-party transactions were reviewed and approved by the"
    " Audit Committee in accordance with its written charter.</div>"
    "<div>The Board recommends that the say-on-pay vote be held every"
    " year.</div>"
)
_PK10_NUMERAL_BODY = (
    _PK10_PROXY_BODY
    + "<div>The principal executive officer received total compensation of"
    " $74,610,000 for fiscal 2025.</div>"
)


def _pk10_supplied_result(body: str = _PK10_PROXY_BODY) -> dict:
    return produce_pack(
        "PK10",
        _pk10_input(
            packages=(_synthetic_package("DEF 14A", body),), entity=SYNTHETIC_ENTITY
        ),
    )


def test_pk10_supplied_proxy_text_rows_valued() -> None:
    result = _pk10_supplied_result()
    assert result["applicability"]["state"] == "applicable"
    assert result["applicability"]["reason"] == "applicability_rule_satisfied"
    assert result["pack_id"] == "PK10"
    # The four frozen B.2 text-span rows resolve over the proxy narrative.
    assert (
        _row(result, "performance_measure_selected")["text_value"]
        == "The most important performance measure for fiscal 2025 executive"
        " compensation was adjusted operating income."
    )
    director = _row(result, "director_independence_span")
    assert director["text_value"].startswith(
        "The Board has determined that each director is independent"
    )
    assert "independent under the" in director["text_value"]
    assert _row(result, "related_party_span")["text_value"].startswith(
        "All related-party transactions"
    )
    assert _row(result, "say_on_pay_frequency")["text_value"] == "annual"
    for field_id in PK10_TEXT_SPAN_FIELDS:
        row = _row(result, field_id)
        assert row["quality_state"] == "valued"
        assert row["reason"] is None
        assert row["evidence_kind"] == "text_span"
        assert row["required_evidence_kind"] == "text_span"
        assert row["coverage_state"] == "source_trace_complete"
        assert row["mapping_rule_id"] == f"PK10.{field_id}.text_span/v1"
        span = row["source_span"]
        assert isinstance(span, dict)
        assert span["document_id"] == "doc.htm"
        assert span["accession"] == "0000000099-26-000001"
        assert span["end_offset"] > span["start_offset"] >= 0
    # The six reserved table-cell rows abstain typed (C2).
    for field_id in PK10_TABLE_CELL_FIELDS:
        row = _row(result, field_id)
        assert row["quality_state"] == "unsupported"
        assert row["non_value_state"] == "unsupported"
        assert row["reason"] == "missing_dependency"
        assert row["evidence_kind"] == "table_cell"
        assert row["required_evidence_kind"] == "table_cell"
        assert row["value"] is None and row["text_value"] is None
    # All four checks abstain on the reserved tables; cap_vs_sct_total never
    # splices CAP and SCT Total into one number.
    for check_id in (
        "pvp_table_present",
        "sct_table_present",
        "sct_year_matches_fiscal",
        "cap_vs_sct_total",
    ):
        check = _check(result, check_id)
        assert check["status"] == "not_evaluable"
        assert check["reason"] == "missing_dependency"
        assert check["tolerance"] is None
    assert result["coverage"] == {
        "valued_fields": 4,
        "missing_fields": 0,
        "unsupported_fields": 6,
        "not_evaluable_fields": 0,
        "not_applicable_fields": 0,
        "disclosure_coverage_state": "present",
    }
    assert "proxy_forms_seen=DEF 14A" in result["receipts"]
    assert (
        "pk10.table_extraction_reserved: SCT and PvP tables are sources for "
        "a later lane; no numeric row is produced from prose"
        in result["limitations"]
    )
    assert contract.validate_pack_result(result) == []


def test_pk10_prose_numeral_is_never_scraped() -> None:
    # §TESTS 3: the SCT total appears only inside narrative text; the row
    # types the refusal, it never carries the number.
    result = _pk10_supplied_result(_PK10_NUMERAL_BODY)
    row = _row(result, "ceo_total_comp")
    assert row["quality_state"] == "unsupported"
    assert row["reason"] == "numeric_value_in_narrative_only"
    assert row["value"] is None and row["text_value"] is None
    # Quantities with no prose numeral stay on the reserved-table reason.
    assert _row(result, "other_neo_total")["reason"] == "missing_dependency"
    assert _row(result, "comp_actually_paid_peo")["reason"] == "missing_dependency"
    assert contract.validate_pack_result(result) == []


def test_pk10_supplied_proxy_without_matching_spans_types_missing() -> None:
    # A span the frozen patterns cannot locate resolves as the valued
    # absence "not_disclosed" over the whole document: the PK10 catalogue
    # carries no narrative_span_not_located code, and a supplied proxy must
    # never crash the producer over one missing phrase.
    result = _pk10_supplied_result(
        "<div>This proxy statement contains no governing phrases.</div>"
    )
    for field_id in PK10_TEXT_SPAN_FIELDS:
        row = _row(result, field_id)
        assert row["quality_state"] == "valued"
        assert row["text_value"] == "not_disclosed"
        assert row["reason"] is None
        span = row["source_span"]
        assert isinstance(span, dict) and span["end_offset"] > span["start_offset"]
    assert result["coverage"]["valued_fields"] == 4
    assert result["coverage"]["disclosure_coverage_state"] == "present"
    assert contract.validate_pack_result(result) == []


def test_pk10_deafa14a_only_is_still_not_supplied() -> None:
    # B.1 keys applicability on a DEF 14A package being present; a DEFA14A
    # soliciting material alone never substitutes.
    result = produce_pack(
        "PK10",
        _pk10_input(
            packages=(_synthetic_package("DEFA14A", _PK10_PROXY_BODY),),
            entity=SYNTHETIC_ENTITY,
        ),
    )
    assert result["applicability"]["state"] == "not_evaluable"
    assert result["applicability"]["reason"] == "proxy_package_not_supplied"
    assert "proxy_forms_seen=none" in result["receipts"]
    assert contract.validate_pack_result(result) == []


def _pk10_package(
    form: str, body: str, accession: str, por: str
) -> GoldenFilingPackage:
    """A synthetic proxy package with an explicit accession and period, so a
    DEF 14A / DEFA14A pair can differ on both (the shared builder is fixed)."""
    package = _synthetic_package(form, body)
    return replace(
        package,
        manifest={**package.manifest, "accession": accession, "period_of_report": por},
    )


def test_pk10_def14a_governs_over_a_later_defa14a() -> None:
    # Review F1: only DEF 14A is an admitted form, so a later one-line
    # DEFA14A soliciting letter never becomes the governing document and no
    # absence is asserted over it.
    def14a = _pk10_package(
        "DEF 14A", _PK10_PROXY_BODY, "0000000099-26-000001", "2026-03-01"
    )
    defa14a = _pk10_package(
        "DEFA14A",
        "<div>Test Co filed additional soliciting material. Please vote.</div>",
        "0000000099-26-000002",
        "2026-04-10",
    )
    result = produce_pack(
        "PK10",
        _pk10_input(packages=(def14a, defa14a), entity=SYNTHETIC_ENTITY),
    )
    assert result["applicability"]["state"] == "applicable"
    assert "form=DEF 14A" in result["receipts"]
    assert "form=DEFA14A" not in result["receipts"]
    for field_id in PK10_TEXT_SPAN_FIELDS:
        assert _row(result, field_id)["source_span"]["accession"] == (
            "0000000099-26-000001"
        )
    assert _row(result, "say_on_pay_frequency")["text_value"] == "annual"
    assert contract.validate_pack_result(result) == []


def test_pk10_defa14a_alone_is_not_a_governing_proxy() -> None:
    # Review F1: a DEFA14A-only package list keeps the frozen not-supplied
    # path — never applicable with not_disclosed rows over a soliciting
    # letter.
    result = produce_pack(
        "PK10",
        _pk10_input(
            packages=(
                _pk10_package(
                    "DEFA14A",
                    "<div>Test Co filed additional soliciting material."
                    " Please vote.</div>",
                    "0000000099-26-000002",
                    "2026-04-10",
                ),
            ),
            entity=SYNTHETIC_ENTITY,
        ),
    )
    assert result["applicability"]["state"] == "not_evaluable"
    assert result["applicability"]["reason"] == "proxy_package_not_supplied"
    assert result["coverage"]["disclosure_coverage_state"] == "not_supplied"
    for row in result["fields"]:
        assert row["quality_state"] == "not_evaluable"
        assert row["reason"] == "proxy_package_not_supplied"
        assert row["text_value"] is None and row["source_span"] is None
    assert contract.validate_pack_result(result) == []


def test_pk10_say_on_pay_triennial_beats_leftmost_annual_meeting() -> None:
    # Review F2, the reviewer's text: the annual-meeting preamble must not
    # satisfy the annual arm; the vote-frequency sentence governs.
    body = (
        "<div>Proxy statement for the 2026 annual meeting of stockholders."
        "</div>"
        "<div>The Board recommends that the say-on-pay vote is held every"
        " three years.</div>"
    )
    result = _pk10_supplied_result(body)
    row = _row(result, "say_on_pay_frequency")
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "triennial"
    assert contract.validate_pack_result(result) == []


def test_pk10_say_on_pay_biennial() -> None:
    body = (
        "<div>Our advisory vote on executive compensation is held every two"
        " years.</div>"
    )
    result = _pk10_supplied_result(body)
    row = _row(result, "say_on_pay_frequency")
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "biennial"
    assert contract.validate_pack_result(result) == []


def test_pk10_annual_meeting_alone_is_not_a_frequency() -> None:
    # Review F2: "annual meeting"/"annual report" alone never satisfies the
    # annual arm; with no frequency sentence the row stays the valued
    # absence not_disclosed (the existing absent path).
    body = (
        "<div>Proxy statement for the 2026 annual meeting of stockholders."
        "</div>"
        "<div>The annual report is incorporated by reference.</div>"
    )
    result = _pk10_supplied_result(body)
    row = _row(result, "say_on_pay_frequency")
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "not_disclosed"
    assert contract.validate_pack_result(result) == []


def _pk10_frequency_row(body: str) -> tuple[dict, GoldenFilingPackage, dict]:
    """Produce the supplied PK10 result for one synthetic DEF 14A body and
    return its say_on_pay_frequency row, the package (the row's source_span
    cites raw byte offsets into the package's primary member) and the full
    result for the contract check."""
    package = _synthetic_package("DEF 14A", body)
    result = produce_pack(
        "PK10",
        _pk10_input(packages=(package,), entity=SYNTHETIC_ENTITY),
    )
    return _row(result, "say_on_pay_frequency"), package, result


def _pk10_matched_span(package: GoldenFilingPackage, row: dict) -> str:
    span = row["source_span"]
    assert isinstance(span, dict)
    return package.members["doc.htm"][
        span["start_offset"] : span["end_offset"]
    ].decode("utf-8")


def test_pk10_triennial_rather_than_annually() -> None:
    # Review F1 (second repair), S1: the sentence states a triennial
    # frequency; the contrastive "rather than annually" must not let the
    # annual arm's gap skip past the stated frequency.
    row, package, result = _pk10_frequency_row(
        "<div>The say-on-pay vote will be held every three years rather"
        " than annually.</div>"
    )
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "triennial"
    assert _pk10_matched_span(package, row) == (
        "say-on-pay vote will be held every three years"
    )
    assert contract.validate_pack_result(result) == []


def test_pk10_triennial_rather_than_every_year() -> None:
    # Review F1 (second repair), S2: same sentence shape with "every year"
    # as the contrasted annual phrase.
    row, package, result = _pk10_frequency_row(
        "<div>The say-on-pay vote will be held every three years rather"
        " than every year.</div>"
    )
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "triennial"
    assert _pk10_matched_span(package, row) == (
        "say-on-pay vote will be held every three years"
    )
    assert contract.validate_pack_result(result) == []


def test_pk10_board_recommended_triennial_frequency() -> None:
    # Review F1 (second repair), S3: the "frequency of" anchor with both a
    # stated triennial frequency and a contrasted "every year" in the same
    # sentence.
    row, package, result = _pk10_frequency_row(
        "<div>The Board recommended a frequency of every three years"
        " rather than every year, and shareholders agreed.</div>"
    )
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "triennial"
    assert _pk10_matched_span(package, row) == (
        "frequency of every three years"
    )
    assert contract.validate_pack_result(result) == []


def test_pk10_annual_rather_than_triennial_stays_annual() -> None:
    # Review F1 (second repair), control: the asymmetric sentence keeps
    # resolving annual — the stated "every year" governs, and the arm
    # reorder plus the tempered gaps never let triennial steal it.
    row, package, result = _pk10_frequency_row(
        "<div>The say-on-pay vote will be held every year rather than"
        " every three years.</div>"
    )
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "annual"
    assert _pk10_matched_span(package, row) == (
        "say-on-pay vote will be held every year"
    )
    assert contract.validate_pack_result(result) == []


def test_pk10_rejected_alternative_is_not_evidence() -> None:
    # Review F1-A (third repair), (ii): the stated frequency is annual; the
    # rejected "every three years" alternative is not evidence, and the
    # rejection verb never appears in the matched span.
    row, package, result = _pk10_frequency_row(
        "<div>Shareholders approved annual say-on-pay votes, rejecting the"
        " every three years alternative.</div>"
    )
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "annual"
    assert _pk10_matched_span(package, row) == "annual say-on-pay"
    assert contract.validate_pack_result(result) == []


def test_pk10_annual_incentive_collocation_is_not_a_frequency() -> None:
    # Review F1-B (third repair), (O1): "annual" heading the "annual
    # incentive plan" collocation is not a frequency; the stated "every
    # three years" on the far side of the anchor governs.
    row, package, result = _pk10_frequency_row(
        "<div>The say-on-pay vote on our annual incentive plan will be held"
        " every three years.</div>"
    )
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "triennial"
    assert _pk10_matched_span(package, row) == (
        "say-on-pay vote on our annual incentive plan will be held every"
        " three years"
    )
    assert contract.validate_pack_result(result) == []


def test_pk10_frequency_before_anchor_resolves() -> None:
    # Review F2 (third repair), (iii): the frequency may precede the anchor
    # in the same sentence; the hyphenated "every-three-years" is matched
    # but discarded — it modifies the peer-group "review", not the vote.
    row, package, result = _pk10_frequency_row(
        "<div>We hold an annual say-on-pay vote, consistent with the"
        " every-three-years review of our peer group.</div>"
    )
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "annual"
    assert _pk10_matched_span(package, row) == "annual say-on-pay"
    assert contract.validate_pack_result(result) == []


def test_pk10_biennial_rather_than_annually() -> None:
    # Third repair NOTE: the biennial transcript — the contrasted
    # "annually" is discarded, the stated "every two years" governs.
    row, package, result = _pk10_frequency_row(
        "<div>The say-on-pay vote will be held every two years rather"
        " than annually.</div>"
    )
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "biennial"
    assert _pk10_matched_span(package, row) == (
        "say-on-pay vote will be held every two years"
    )
    assert contract.validate_pack_result(result) == []


def test_pk10_annually_rather_than_biennial() -> None:
    # Third repair NOTE: the mirrored transcript — the contrasted "every
    # two years" is discarded, the stated "annually" governs.
    row, package, result = _pk10_frequency_row(
        "<div>The say-on-pay vote will be held annually rather than every"
        " two years.</div>"
    )
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "annual"
    assert _pk10_matched_span(package, row) == (
        "say-on-pay vote will be held annually"
    )
    assert contract.validate_pack_result(result) == []


def test_pk10_two_surviving_frequencies_is_not_disclosed() -> None:
    # Third repair: two distinct frequencies survive one anchored sentence
    # with no contrast marker separating them — the pack's existing
    # anchor-present-no-resolvable-frequency emission, the valued
    # not_disclosed asserted over the whole document.
    row, package, result = _pk10_frequency_row(
        "<div>The say-on-pay vote is held annually and every three"
        " years.</div>"
    )
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "not_disclosed"
    span = row["source_span"]
    assert isinstance(span, dict)
    raw = package.members["doc.htm"]
    # The valued absence is asserted over the whole document, exactly as the
    # no-anchor absence: the span runs from the first byte through the last
    # narrative character (the trailing close tags collapse to one space).
    assert span["start_offset"] == 0
    assert span["end_offset"] > span["start_offset"]
    covered = raw[span["start_offset"] : span["end_offset"]].decode("utf-8")
    assert "The say-on-pay vote is held annually and every three years." in covered
    assert contract.validate_pack_result(result) == []


def test_pk10_bare_duration_after_review_is_not_a_cadence() -> None:
    # Fourth repair, review F1 (x1): "covering three years" states the
    # duration of the peer-group review, not the vote's cadence — the
    # non-vote-noun discard only looks after the phrase, so a preceding
    # "review" never saves the bare duration. With the bare form gone from
    # the phrase table the anchored sentence keeps no frequency.
    row, package, result = _pk10_frequency_row(
        "<div>The say-on-pay vote follows a peer-group review covering three"
        " years.</div>"
    )
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "not_disclosed"
    span = row["source_span"]
    assert isinstance(span, dict)
    raw = package.members["doc.htm"]
    # The valued absence is asserted over the whole document, exactly as the
    # no-anchor absence and the two-frequency tie-break.
    assert span["start_offset"] == 0
    assert span["end_offset"] > span["start_offset"]
    covered = raw[span["start_offset"] : span["end_offset"]].decode("utf-8")
    assert (
        "The say-on-pay vote follows a peer-group review covering three"
        " years." in covered
    )
    assert contract.validate_pack_result(result) == []


def test_pk10_deadline_within_three_years_is_not_a_cadence() -> None:
    # Fourth repair, review F1 (x2): "within three years of the prior vote"
    # is a deadline, not a cadence — no discard window can rescue a bare
    # duration, so the phrase table must not offer it.
    row, package, result = _pk10_frequency_row(
        "<div>The say-on-pay vote must be held within three years of the"
        " prior vote.</div>"
    )
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "not_disclosed"
    span = row["source_span"]
    assert isinstance(span, dict)
    raw = package.members["doc.htm"]
    assert span["start_offset"] == 0
    assert span["end_offset"] > span["start_offset"]
    covered = raw[span["start_offset"] : span["end_offset"]].decode("utf-8")
    assert (
        "The say-on-pay vote must be held within three years of the prior"
        " vote." in covered
    )
    assert contract.validate_pack_result(result) == []


def test_pk10_tenure_duration_does_not_mask_annual() -> None:
    # Fourth repair, review F2 (x3): the director-tenure duration shares the
    # ";"-joined sentence with the anchor; read as a second frequency it
    # tripped the two-distinct-frequencies tie-break into a false absence.
    # Bare durations are no longer frequencies, so the stated annual cadence
    # resolves and the span never reaches the tenure clause.
    row, package, result = _pk10_frequency_row(
        "<div>Directors are elected for three years; the say-on-pay vote is"
        " held annually.</div>"
    )
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "annual"
    matched = _pk10_matched_span(package, row)
    assert "say-on-pay vote is held annually" in matched
    assert "elected for three years" not in matched
    assert contract.validate_pack_result(result) == []


@pytest.mark.parametrize("pack_id", sorted(BASE_AAPL_ENVELOPE_SHA256))
def test_base_pack_envelopes_unchanged_by_pk10_edits(pack_id: str) -> None:
    # §TESTS 4: every pack registered at BASE keeps its AAPL envelope
    # byte-identical to BASE after PK10 registers.
    metric = _BASE_PACK_METRICS[pack_id]
    result = produce_pack(
        pack_id, _pack_input(query={**QUERY, "requested_metrics": [metric]})
    )
    payload = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert (
        sha256(payload.encode("utf-8")).hexdigest()
        == BASE_AAPL_ENVELOPE_SHA256[pack_id]
    )


# 39. PK03: segments and geographic/product dimensions --------------------------
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
        "4799c1a1554c8ee9fc939a0461cc30d13192d01e1c16a48b561c884f0a5d998f"
    ),
    "PK02": (
        "e6f4536ff6867f71b95693247c72e01eee0671fe1870b3be85b727c511a28464"
    ),
    "PK04": (
        "cbbf83b3f9e4e258095c8428b8e5f343bf96ac93e05c512566ca5463e9a92227"
    ),
    "PK06": (
        "b26d48b769b9be642b5deaeafbe2f853b5d6155eb2f079f4953642c417062629"
    ),
    "PK09": (
        "abbb6196b01df079ff3ef4ed68ae8b349bf762761f2b424c0bd4625fe90ede8e"
    ),
    "PK11": (
        "9660c82e6d14e70e9302b2dc2cdf2468da416886422892d5201cea0ff88a744d"
    ),
    "PK12": (
        "4e644f4dc2427cfdaa044623b5af4208ad58112cc350a9e53f3df543b5883b62"
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


# 40. PK03 A.4/A.5/A.3 synthetic checks -----------------------------------------


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


# 41. PK03 A.1/A.2 mapping semantics on synthetic ledgers -----------------------


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


# 42. PK03 bank probe, determinism, invariance, registry, CLI, A33 ---------------


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
    assert registered_pack_ids() == ("PK01", "PK02", "PK03", "PK04", "PK05", "PK06", "PK07", "PK08", "PK09", "PK10", "PK11", "PK12")


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


# 43. PK05: income tax and uncertain tax positions ------------------------------
#
# Fixture-verified through the raw ledger and the calculation linkbase
# (FY2025 = 2024-09-29..2025-09-27): the filing tags income tax expense
# 20,719,000,000 three times identically (income statement, tax note, cash
# flow note); pretax income 132,729,000,000; the disclosed effective rate
# 0.156 (decimals 3, xbrli:pure) and the statutory federal rate 0.21
# (decimals INF). The reconciliation role chosen by A.2 is
# http://www.apple.com/role/IncomeTaxesReconciliationofProvisionforIncome
# TaxestoAmountComputedbyApplyingtheStatutoryFederalIncomeTaxRatetoIncome
# BeforeProvisionforIncomeTaxesDetails (5 prefix-matching children; the
# provision-details role has none): six arcs — federal statutory 27,873
# (+1), foreign differential −8,120 (+1; the fact itself carries the minus
# sign), valuation-allowance change 2,091 (+1), research credits 1,049
# (−1 arc weight), the extension State Aid line −486 (+1, valued under the
# issuer's own arc alias) and other adjustments 410 (+1). The UTB balances
# are tagged twice each: 22,038/-6 ×2 plus 22.0e9/-8 at 2024-09-28, and
# 23,242/-6 plus 23.2e9/-8 at 2025-09-27 — precision-consistent duplicates
# (A.1), three and two occurrence ids. The Q4-2024 settlements fact 823
# carries LossContingenciesByNatureOfContingencyAxis and sits outside the
# period, so the FY2025 settlements row is the undimensioned 2,939 fact.

from engine.fundamental_forensics.specialist_packs import (  # noqa: E402
    calculation_linkbase,
    pk05_tax,
)

PK05_QUERY = {**QUERY, "requested_metrics": ["tax"]}
# §TESTS 11: sha256 of the canonical JSON bytes of every BASE pack's AAPL
# envelope under this module's own PK05 query, recorded before this lane's
# edits; PK05 registration must not move any of them.
PK05_BASE_PACK_ENVELOPE_SHA256 = {
    "PK01": "c9a96b80e29f59bb529572103e3512375a09feef52ef00b233452275ca573447",
    "PK02": "3ca4ca2886034b783be63a5aa8b2be3e763b004511f94163664fc022307e6fc1",
    "PK03": "17a26aa6d276414927f9c68ddbd37595e79bc6120a289abcb254f83f4095057d",
    "PK04": "e4746fbf9126b233d759caeb235dfec72d1895b20b6a6b13a20dd6d16802d5dd",
    "PK06": "2126d42b4a608ad2a9f8e9a48b8692fe8c11c8ed187d5beb33e27df68182df17",
    "PK09": "44639f4371eab872ea3bb40ded519b46bab7fb4a49ef9a5508b1f38afec63447",
    "PK10": "217702f0bb51ac1686a796422e72118655584064fd8b6585eb8f5aa640c230e1",
    "PK11": "1e8d160a7fb3402fd82c698333cd2d87ad3622fca5d70437800c692c3fb63620",
    "PK12": "d6bfa668b1a77819f0a2e8ff1d77fd75e8cacce96dbeba49b430d861fca9591d",
}
# B.4: the six reconciliation rows in calculation-arc order (qname, value).
PK05_RECONCILIATION_ROWS = [
    (
        "us-gaap:IncomeTaxReconciliationIncomeTaxExpenseBenefitAt"
        "FederalStatutoryIncomeTaxRate",
        "27873000000",
    ),
    (
        "us-gaap:IncomeTaxReconciliationForeignIncomeTaxRateDifferential",
        "-8120000000",
    ),
    (
        "us-gaap:IncomeTaxReconciliationChangeInDeferredTaxAssets"
        "ValuationAllowance",
        "2091000000",
    ),
    ("us-gaap:IncomeTaxReconciliationTaxCreditsResearch", "1049000000"),
    (
        "aapl:EffectiveIncomeTaxRateReconciliationImpactOfTheStateAid"
        "DecisionAmount",
        "-486000000",
    ),
    ("us-gaap:IncomeTaxReconciliationOtherAdjustments", "410000000"),
]


def _pk05_input(**overrides) -> PackInput:
    defaults = dict(
        packages=(load_golden_aapl_package(ROOT, accession=ACCESSION),),
        entity=ENTITY,
        query=PK05_QUERY,
        issuer_sic="3571",
        sic_source="sec_submissions",
    )
    defaults.update(overrides)
    return PackInput(**defaults)


@pytest.fixture(scope="module")
def pk05_result() -> dict:
    return produce_pack("PK05", _pk05_input())


def test_pk05_result_passes_contract_validator(pk05_result: dict) -> None:
    assert contract.validate_pack_result(pk05_result) == []


def test_pk05_result_passes_jsonschema_envelope(pk05_result: dict) -> None:
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
        Draft202012Validator(schema, registry=registry).iter_errors(pk05_result)
    )
    assert errors == []


def test_pk05_applicability_and_coverage(pk05_result: dict) -> None:
    applicability = pk05_result["applicability"]
    assert applicability["state"] == "applicable"
    assert applicability["reason"] == "applicability_rule_satisfied"
    assert applicability["rule_id"] == "specialist_pack.pk05.applicability/v1"
    assert applicability["sic"] == "3571"
    assert pk05_result["coverage"] == {
        "valued_fields": 21,
        "missing_fields": 0,
        "unsupported_fields": 1,
        "not_evaluable_fields": 0,
        "not_applicable_fields": 0,
        "disclosure_coverage_state": "present",
    }


def test_pk05_rows_follow_catalogue_order_with_twenty_two_rows(
    pk05_result: dict,
) -> None:
    catalogue_ids = [
        item["field_id"]
        for item in contract.load_pack_schema("PK05")["fields"]
    ]
    expected = [
        field_id
        for field_id in catalogue_ids
        for _ in range(6 if field_id == "etr_reconciliation_line" else 1)
    ]
    assert [row["field_id"] for row in pk05_result["fields"]] == expected
    assert len(pk05_result["fields"]) == 22  # 17 catalogue fields -> 22 rows


def test_pk05_reconciliation_rows_are_adjacent_and_in_arc_order(
    pk05_result: dict,
) -> None:
    rows = _rows(pk05_result, "etr_reconciliation_line")
    assert len(rows) == 6
    # Adjacency: the six rows occupy six consecutive envelope positions.
    indexes = [
        i for i, row in enumerate(pk05_result["fields"]) if row in rows
    ]
    assert indexes == list(range(indexes[0], indexes[0] + 6))
    assert [(row["concept"], row["value"]) for row in rows] == (
        PK05_RECONCILIATION_ROWS
    )
    extension = rows[4]
    assert extension["taxonomy"] == "aapl"
    assert extension["quality_state"] == "valued"
    for row in rows:
        assert row["mapping_rule_id"] == (
            "pk05.etr_reconciliation_line.calculation_children/v1"
        )
        assert row["evidence_kind"] == "xbrl_fact"
        assert row["dimensions"] == []
        assert row["period"] == {
            "kind": "duration",
            "start": "2024-09-29",
            "end": "2025-09-27",
        }


def test_pk05_core_fields_and_formula(pk05_result: dict) -> None:
    expense = _row(pk05_result, "income_tax_expense")
    assert expense["value"] == "20719000000"
    assert expense["quality_state"] == "valued"
    assert len(expense["source_occurrence_ids"]) == 3  # tagged three times
    assert expense["period"]["end"] == "2025-09-27"
    pretax = _row(pk05_result, "pretax_income")
    assert pretax["value"] == "132729000000"
    assert len(pretax["source_occurrence_ids"]) == 1
    formula = _row(pk05_result, "effective_tax_rate_formula")
    assert formula["quality_state"] == "valued"
    assert Decimal(formula["value"]) == Decimal("0.156100")
    assert formula["unit"] == "ratio"
    assert formula["evidence_kind"] == "formula"
    assert formula["dependency_field_ids"] == [
        "income_tax_expense",
        "pretax_income",
    ]
    disclosed = _row(pk05_result, "effective_tax_rate_disclosed")
    assert disclosed["value"] == "0.156"
    assert disclosed["unit"] == "ratio"
    statutory = _row(pk05_result, "statutory_federal_rate")
    assert statutory["value"] == "0.21"
    assert statutory["unit"] == "ratio"


def test_pk05_utp_balances_reconcile_precision_consistent_duplicates(
    pk05_result: dict,
) -> None:
    opening = _row(pk05_result, "utp_opening")
    assert opening["value"] == "22038000000"
    assert opening["period"] == {"kind": "instant", "end": "2024-09-28"}
    # Two decimals=-6 occurrences plus one 22.0e9 decimals=-8 occurrence.
    assert len(opening["source_occurrence_ids"]) == 3
    closing = _row(pk05_result, "utp_closing")
    assert closing["value"] == "23242000000"
    assert closing["period"] == {"kind": "instant", "end": "2025-09-27"}
    # One decimals=-6 occurrence plus one 23.2e9 decimals=-8 occurrence.
    assert len(closing["source_occurrence_ids"]) == 2


def test_pk05_utp_rollforward_lines(pk05_result: dict) -> None:
    expected = {
        "utp_rollforward_increases_prior_period": "1971000000",
        "utp_rollforward_decreases_prior_period": "71000000",
        "utp_rollforward_increases_current_period": "3795000000",
        "utp_rollforward_settlements": "2939000000",
        "utp_rollforward_lapse_of_statute": "1552000000",
    }
    for field_id, value in expected.items():
        row = _row(pk05_result, field_id)
        assert row["value"] == value, field_id
        assert row["quality_state"] == "valued"
        assert row["period"] == {
            "kind": "duration",
            "start": "2024-09-29",
            "end": "2025-09-27",
        }
    # The Q4-2024 dimensioned 823 settlement fact is never selected.
    settlements = _row(pk05_result, "utp_rollforward_settlements")
    assert len(settlements["source_occurrence_ids"]) == 1


def test_pk05_remaining_fields(pk05_result: dict) -> None:
    impact = _row(pk05_result, "utp_impact_on_etr")
    assert impact["value"] == "10600000000"
    assert impact["period"] == {"kind": "instant", "end": "2025-09-27"}
    paid = _row(pk05_result, "income_taxes_paid")
    assert paid["value"] == "43369000000"
    assert paid["concept"] == "us-gaap:IncomeTaxesPaidNet"  # p10 alias wins
    gross = _row(pk05_result, "deferred_tax_assets_gross")
    assert gross["value"] == "38417000000"
    assert gross["period"] == {"kind": "instant", "end": "2025-09-27"}
    note = _row(pk05_result, "tax_note_text_block")
    assert note["quality_state"] == "unsupported"
    assert note["reason"] == "missing_dependency"
    assert note["evidence_kind"] == "text_span"
    assert note["required_evidence_kind"] == "text_span"


def test_pk05_checks_pass_with_declared_tolerances(pk05_result: dict) -> None:
    reconciliation = _check(pk05_result, "etr_reconciliation_sum")
    assert reconciliation["status"] == "pass"
    assert reconciliation["tolerance"] == "1000000"
    assert reconciliation["operands"] == [
        "etr_reconciliation_line",
        "income_tax_expense",
    ]
    assert reconciliation["evidence_field_ids"] == [
        "etr_reconciliation_line",
        "income_tax_expense",
    ]
    assert reconciliation["reason"] is None
    assert (
        "pk05.etr_reconciliation_sum: negative-weight lines"
        " us-gaap:IncomeTaxReconciliationTaxCreditsResearch"
        in pk05_result["limitations"]
    )
    rollforward = _check(pk05_result, "utp_rollforward")
    assert rollforward["status"] == "pass"
    assert rollforward["tolerance"] == "1000000"
    assert rollforward["reason"] is None
    formula = _check(pk05_result, "etr_formula_vs_disclosed")
    assert formula["status"] == "pass"
    assert formula["tolerance"] == "0.001"
    assert formula["reason"] is None


# 44. A.1 precision-consistent duplicates on a synthetic ledger -----------------


def _duplicate_policy_outcome(
    occurrences, policy: str
) -> "pack_base._FieldOutcome":
    mapping = pack_base.FactMapping(
        ("us-gaap:UnrecognizedTaxBenefits",),
        duplicate_policy=policy,
    )
    return pack_base._resolve_fact_mapping(
        pack_id="PK05",
        catalogue_field=_catalogue_field("PK05", "utp_closing"),
        mapping=mapping,
        ledger=RawFactLedger(events=tuple(occurrences)),
        por=_date(2025, 9, 27),
        extension_prefixes={},
    )


def test_a1_precision_consistent_duplicates_value_the_precise_occurrence() -> None:
    outcome = _duplicate_policy_outcome(
        [
            _synthetic_occurrence(
                "us-gaap:UnrecognizedTaxBenefits",
                instant=_date(2025, 9, 27),
                value="23242000000",
                decimals="-6",
            ),
            _synthetic_occurrence(
                "us-gaap:UnrecognizedTaxBenefits",
                instant=_date(2025, 9, 27),
                value="23200000000",
                decimals="-8",
            ),
        ],
        "precision_consistent",
    )
    assert outcome.row["quality_state"] == "valued"
    assert outcome.value == Decimal("23242000000")
    assert len(outcome.row["source_occurrence_ids"]) == 2
    assert outcome.decimals == -6  # the selected occurrence's decimals


def test_a1_inconsistent_duplicates_stay_not_evaluable() -> None:
    outcome = _duplicate_policy_outcome(
        [
            _synthetic_occurrence(
                "us-gaap:UnrecognizedTaxBenefits",
                instant=_date(2025, 9, 27),
                value="23242000000",
                decimals="-6",
            ),
            _synthetic_occurrence(
                "us-gaap:UnrecognizedTaxBenefits",
                instant=_date(2025, 9, 27),
                value="23300000000",
                decimals="-8",
            ),
        ],
        "precision_consistent",
    )
    assert outcome.row["quality_state"] == "not_evaluable"
    assert outcome.row["reason"] == "missing_dependency"


def test_a1_default_policy_keeps_the_base_conflict_outcome() -> None:
    outcome = _duplicate_policy_outcome(
        [
            _synthetic_occurrence(
                "us-gaap:UnrecognizedTaxBenefits",
                instant=_date(2025, 9, 27),
                value="23242000000",
                decimals="-6",
            ),
            _synthetic_occurrence(
                "us-gaap:UnrecognizedTaxBenefits",
                instant=_date(2025, 9, 27),
                value="23200000000",
                decimals="-8",
            ),
        ],
        "",
    )
    assert outcome.row["quality_state"] == "not_evaluable"
    assert outcome.row["reason"] == "missing_dependency"


# 45. A.2 calculation-children mapping on synthetic linkbases -------------------

_SYNTHETIC_CAL = b"""<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:calculationLink xlink:role="http://example.com/role/ProvisionDetails" xlink:type="extended">
    <link:loc xlink:type="locator" xlink:label="parent" xlink:href="syn-2026.xsd#us-gaap_IncomeTaxExpenseBenefit"/>
    <link:loc xlink:type="locator" xlink:label="fed" xlink:href="syn-2026.xsd#us-gaap_FederalIncomeTaxExpenseBenefitContinuingOperations"/>
    <link:calculationArc xlink:type="arc" xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item" xlink:from="parent" xlink:to="fed" weight="1.0" order="1"/>
  </link:calculationLink>
  <link:calculationLink xlink:role="http://example.com/role/ReconciliationDetailsA" xlink:type="extended">
    <link:loc xlink:type="locator" xlink:label="parent" xlink:href="syn-2026.xsd#us-gaap_IncomeTaxExpenseBenefit"/>
    <link:loc xlink:type="locator" xlink:label="stat" xlink:href="syn-2026.xsd#us-gaap_IncomeTaxReconciliationIncomeTaxExpenseBenefitAtFederalStatutoryIncomeTaxRate"/>
    <link:loc xlink:type="locator" xlink:label="ext" xlink:href="syn-2026.xsd#syn_StateAidReconciliationAmount"/>
    <link:calculationArc xlink:type="arc" xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item" xlink:from="parent" xlink:to="stat" weight="1.0" order="1"/>
    <link:calculationArc xlink:type="arc" xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item" xlink:from="parent" xlink:to="ext" weight="-1.0" order="2"/>
  </link:calculationLink>
</link:linkbase>
"""


class _CalPackage:
    """Duck-compatible package carrying only a calculation linkbase."""

    def __init__(self, cal: bytes | None) -> None:
        members = {} if cal is None else {"syn-2026_cal.xml": cal}
        listing = (
            [] if cal is None else [{"name": "syn-2026_cal.xml", "state": "stored"}]
        )
        self.manifest = {"members": listing}
        self.members = members


def test_a2_parse_parent_children_chooses_the_qualifying_role() -> None:
    children = calculation_linkbase.parse_parent_children(
        _SYNTHETIC_CAL,
        "us-gaap:IncomeTaxExpenseBenefit",
        "us-gaap:IncomeTaxReconciliation",
    )
    # ProvisionDetails has children but none prefix-matching; only
    # ReconciliationDetailsA qualifies, so its full child tuple returns.
    assert children == (
        (
            "us-gaap:IncomeTaxReconciliationIncomeTaxExpenseBenefitAt"
            "FederalStatutoryIncomeTaxRate",
            Decimal("1.0"),
        ),
        ("syn:StateAidReconciliationAmount", Decimal("-1.0")),
    )


def test_a2_parse_parent_children_without_qualifying_role_is_empty() -> None:
    for empty in (None, b"", _SYNTHETIC_CAL.replace(b"Reconciliation", b"Other")):
        assert (
            calculation_linkbase.parse_parent_children(
                empty,
                "us-gaap:IncomeTaxExpenseBenefit",
                "us-gaap:IncomeTaxReconciliation",
            )
            == ()
        )


def test_a2_tie_breaks_on_the_lexically_smallest_role_uri() -> None:
    # Inject a second qualifying role (…DetailsB) carrying one matching
    # child of its own; both roles then tie at one matching child, and the
    # lexically smaller role URI (…DetailsA) must win. B's arcs carry
    # different weights, so the winning arc set is identifiable.
    role_b = b"""  <link:calculationLink xlink:role="http://example.com/role/ReconciliationDetailsB" xlink:type="extended">
    <link:loc xlink:type="locator" xlink:label="parent" xlink:href="syn-2026.xsd#us-gaap_IncomeTaxExpenseBenefit"/>
    <link:loc xlink:type="locator" xlink:label="stat" xlink:href="syn-2026.xsd#us-gaap_IncomeTaxReconciliationIncomeTaxExpenseBenefitAtFederalStatutoryIncomeTaxRate"/>
    <link:calculationArc xlink:type="arc" xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item" xlink:from="parent" xlink:to="stat" weight="1.0" order="1"/>
  </link:calculationLink>
"""
    both = _SYNTHETIC_CAL.replace(b"</link:linkbase>", role_b + b"</link:linkbase>")
    children = calculation_linkbase.parse_parent_children(
        both,
        "us-gaap:IncomeTaxExpenseBenefit",
        "us-gaap:IncomeTaxReconciliation",
    )
    assert children == (
        (
            "us-gaap:IncomeTaxReconciliationIncomeTaxExpenseBenefitAt"
            "FederalStatutoryIncomeTaxRate",
            Decimal("1.0"),
        ),
        ("syn:StateAidReconciliationAmount", Decimal("-1.0")),
    )


def test_a2_child_without_fact_is_a_typed_missing_row_by_prefix() -> None:
    ledger = RawFactLedger(
        events=(
            _synthetic_occurrence(
                "us-gaap:IncomeTaxReconciliationIncomeTaxExpenseBenefitAt"
                "FederalStatutoryIncomeTaxRate",
                start=_date(2024, 9, 29),
                end=_date(2025, 9, 27),
                value="27873000000",
            ),
        )
    )
    outcome = pack_base._resolve_calculation_children_mapping(
        pack_id="PK05",
        catalogue_field=_catalogue_field("PK05", "etr_reconciliation_line"),
        mapping=pk05_tax._FIELD_MAPPINGS["etr_reconciliation_line"],
        ledger=ledger,
        por=_date(2025, 9, 27),
        primary=_CalPackage(_SYNTHETIC_CAL),
        limitation_sink=None,
    )
    rows = [outcome.row, *outcome.extra_rows]
    assert len(rows) == 2
    valued, absent = rows
    assert valued["quality_state"] == "valued"
    assert valued["value"] == "27873000000"
    assert absent["quality_state"] == "missing"
    assert absent["reason"] == "extension_concept_unaliased:syn"
    assert absent["taxonomy"] == "syn"
    assert outcome.calculation_weights == (Decimal("1.0"), Decimal("-1.0"))


def test_a2_missing_us_gaap_child_cites_missing_standard_fact() -> None:
    cal = _SYNTHETIC_CAL.replace(b"syn_StateAidReconciliationAmount",
                                 b"us-gaap_IncomeTaxReconciliationOtherAdjustments")
    ledger = RawFactLedger(
        events=(
            _synthetic_occurrence(
                "us-gaap:IncomeTaxReconciliationIncomeTaxExpenseBenefitAt"
                "FederalStatutoryIncomeTaxRate",
                start=_date(2024, 9, 29),
                end=_date(2025, 9, 27),
                value="27873000000",
            ),
        )
    )
    outcome = pack_base._resolve_calculation_children_mapping(
        pack_id="PK05",
        catalogue_field=_catalogue_field("PK05", "etr_reconciliation_line"),
        mapping=pk05_tax._FIELD_MAPPINGS["etr_reconciliation_line"],
        ledger=ledger,
        por=_date(2025, 9, 27),
        primary=_CalPackage(cal),
        limitation_sink=None,
    )
    absent = outcome.extra_rows[0]
    assert absent["reason"] == (
        "missing_standard_fact:us-gaap:IncomeTaxReconciliationOtherAdjustments"
    )
    assert absent["taxonomy"] == "us-gaap"


def test_a2_no_qualifying_role_emits_one_missing_row_and_limitation() -> None:
    sink: list[str] = []
    outcome = pack_base._resolve_calculation_children_mapping(
        pack_id="PK05",
        catalogue_field=_catalogue_field("PK05", "etr_reconciliation_line"),
        mapping=pk05_tax._FIELD_MAPPINGS["etr_reconciliation_line"],
        ledger=RawFactLedger(events=()),
        por=_date(2025, 9, 27),
        primary=_CalPackage(None),
        limitation_sink=sink,
    )
    assert outcome.extra_rows == ()
    assert outcome.row["quality_state"] == "missing"
    assert outcome.row["reason"] == (
        "missing_standard_fact:us-gaap:IncomeTaxExpenseBenefit"
    )
    assert sink == [
        "pk05.etr_reconciliation_line: no calculation role declares"
        " reconciliation children"
    ]


# 46. A.3 weighted sum identity, synthetic --------------------------------------


def _weighted_check(rows_values, total: str, weights) -> dict:
    addend_rows = []
    for index, value in enumerate(rows_values):
        addend_rows.append(
            {
                "field_id": "etr_reconciliation_line",
                "quality_state": "valued" if value is not None else "missing",
                "value": None if value is None else str(value),
                "unit": "USD",
                "concept": f"us-gaap:ReconciliationLine{index}",
            }
        )
    addend = pack_base._FieldOutcome(
        row=addend_rows[0],
        value=None,
        decimals=-6,
        unit="USD",
        extra_rows=tuple(addend_rows[1:]),
    )
    total_outcome = pack_base._FieldOutcome(
        row={"field_id": "income_tax_expense", "quality_state": "valued"},
        value=Decimal(total),
        decimals=-6,
        unit="USD",
    )
    resolver = pack_base._OperandResolver(
        {"etr_reconciliation_line": addend, "income_tax_expense": total_outcome},
        _pk05_input(),
        foreign_cache={},
    )
    catalogue_check = next(
        item
        for item in contract.load_pack_schema("PK05")["checks"]
        if item["check_id"] == "etr_reconciliation_sum"
    )
    spec = pack_base.WeightedSumIdentity(
        check_id="etr_reconciliation_sum",
        addends="etr_reconciliation_line",
        total="income_tax_expense",
        weights=tuple(weights),
    )
    return pack_base._evaluate_check(
        catalogue_check, [spec], resolver, pack_id="PK05"
    )


def test_a3_weighted_sum_ties_within_tolerance() -> None:
    row = _weighted_check(["3000000", "1000000"], "2000000", (1, -1))
    assert row["status"] == "pass"
    assert row["tolerance"] == "1000000"
    assert row["reason"] is None


def test_a3_weighted_sum_off_by_two_million_fails() -> None:
    row = _weighted_check(["3000000", "1000000"], "4000000", (1, -1))
    assert row["status"] == "fail"
    assert row["reason"] is None


def test_a3_weighted_sum_with_missing_addend_row_is_not_evaluable() -> None:
    row = _weighted_check(["3000000", None], "2000000", (1, -1))
    assert row["status"] == "not_evaluable"
    assert row["reason"] == "missing_dependency"


def test_a3_negative_weights_name_their_lines() -> None:
    sink: list[str] = []
    addend_rows = [
        {
            "field_id": "etr_reconciliation_line",
            "quality_state": "valued",
            "value": "3000000",
            "unit": "USD",
            "concept": "us-gaap:FirstLine",
        },
        {
            "field_id": "etr_reconciliation_line",
            "quality_state": "valued",
            "value": "1000000",
            "unit": "USD",
            "concept": "us-gaap:SecondLine",
        },
    ]
    addend = pack_base._FieldOutcome(
        row=addend_rows[0],
        value=None,
        decimals=-6,
        unit="USD",
        extra_rows=(addend_rows[1],),
        calculation_weights=(Decimal(1), Decimal(-1)),
    )
    total_outcome = pack_base._FieldOutcome(
        row={"field_id": "income_tax_expense", "quality_state": "valued"},
        value=Decimal("2000000"),
        decimals=-6,
        unit="USD",
    )
    resolver = pack_base._OperandResolver(
        {"etr_reconciliation_line": addend, "income_tax_expense": total_outcome},
        _pk05_input(),
        foreign_cache={},
    )
    catalogue_check = next(
        item
        for item in contract.load_pack_schema("PK05")["checks"]
        if item["check_id"] == "etr_reconciliation_sum"
    )
    spec = next(
        item
        for item in pk05_tax.PRODUCER.checks
        if item.check_id == "etr_reconciliation_sum"
    )
    row = pack_base._evaluate_check(
        catalogue_check, [spec], resolver, limitation_sink=sink, pack_id="PK05"
    )
    assert row["status"] == "pass"
    assert sink == [
        "pk05.etr_reconciliation_sum: negative-weight lines us-gaap:SecondLine"
    ]


# 47. A.4 utp rollforward, synthetic ---------------------------------------------

_ROLLFORWARD_VALUES = {
    "utp_opening": "22038000000",
    "utp_rollforward_increases_prior_period": "1971000000",
    "utp_rollforward_decreases_prior_period": "71000000",
    "utp_rollforward_increases_current_period": "3795000000",
    "utp_rollforward_settlements": "2939000000",
    "utp_rollforward_lapse_of_statute": "1552000000",
    "utp_closing": "23242000000",
}


def _rollforward_check(values: dict) -> tuple[dict, list[str]]:
    outcomes = {}
    for field_id, value in values.items():
        outcomes[field_id] = pack_base._FieldOutcome(
            row={
                "field_id": field_id,
                "quality_state": "valued" if value is not None else "missing",
            },
            value=None if value is None else Decimal(value),
            decimals=None if value is None else -6,
            unit=None if value is None else "USD",
        )
    resolver = pack_base._OperandResolver(
        outcomes, _pk05_input(), foreign_cache={}
    )
    catalogue_check = next(
        item
        for item in contract.load_pack_schema("PK05")["checks"]
        if item["check_id"] == "utp_rollforward"
    )
    spec = next(
        item
        for item in pk05_tax.PRODUCER.checks
        if item.check_id == "utp_rollforward"
    )
    sink: list[str] = []
    row = pack_base._evaluate_check(
        catalogue_check, [spec], resolver, limitation_sink=sink, pack_id="PK05"
    )
    return row, sink


def test_a4_rollforward_closing_off_by_two_million_fails() -> None:
    row, sink = _rollforward_check(
        {**_ROLLFORWARD_VALUES, "utp_closing": "25242000000"}
    )
    assert row["status"] == "fail"
    assert row["reason"] is None
    assert sink == []


def test_a4_rollforward_missing_settlements_names_the_refused_value() -> None:
    values = {**_ROLLFORWARD_VALUES, "utp_rollforward_settlements": None}
    row, sink = _rollforward_check(values)
    assert row["status"] == "not_evaluable"
    assert row["reason"] == "missing_dependency"
    assert sink == [
        "utp_rollforward: refused to imply utp_rollforward_settlements ="
        " 2939000000 (R-K3: never an implied value)"
    ]


# 48. A.5/A.6 effective-tax-rate formula and cross check, synthetic --------------


def _etr_formula_outcome(expense: str, pretax: str) -> "pack_base._FieldOutcome":
    values = {
        "income_tax_expense": Decimal(expense),
        "pretax_income": Decimal(pretax),
    }
    return pack_base._resolve_formula(
        catalogue_field=_catalogue_field("PK05", "effective_tax_rate_formula"),
        mapping=pk05_tax._FIELD_MAPPINGS["effective_tax_rate_formula"],
        por=_date(2025, 9, 27),
        resolve_input=lambda field_id: pack_base._FieldOutcome(
            row={"field_id": field_id, "quality_state": "valued"},
            value=values[field_id],
            decimals=-6,
            unit="USD",
        ),
    )


def _etr_check(formula_value, disclosed_value, disclosed_decimals) -> dict:
    outcomes = {
        "effective_tax_rate_formula": pack_base._FieldOutcome(
            row={
                "field_id": "effective_tax_rate_formula",
                "quality_state": "valued" if formula_value is not None else "not_evaluable",
            },
            value=formula_value,
            decimals=None,
            unit="ratio",
        ),
        "effective_tax_rate_disclosed": pack_base._FieldOutcome(
            row={
                "field_id": "effective_tax_rate_disclosed",
                "quality_state": "valued" if disclosed_value is not None else "missing",
            },
            value=disclosed_value,
            decimals=disclosed_decimals,
            unit="ratio",
        ),
    }
    resolver = pack_base._OperandResolver(
        outcomes, _pk05_input(), foreign_cache={}
    )
    catalogue_check = next(
        item
        for item in contract.load_pack_schema("PK05")["checks"]
        if item["check_id"] == "etr_formula_vs_disclosed"
    )
    spec = next(
        item
        for item in pk05_tax.PRODUCER.checks
        if item.check_id == "etr_formula_vs_disclosed"
    )
    return pack_base._evaluate_check(
        catalogue_check,
        [spec],
        resolver,
        check_rules=dict(pk05_tax.CHECK_RULES),
        pack_id="PK05",
    )


def test_a5_zero_pretax_income_is_division_by_zero() -> None:
    outcome = _etr_formula_outcome("20719000000", "0")
    assert outcome.row["quality_state"] == "not_evaluable"
    assert outcome.row["reason"] == "division_by_zero"


def test_a6_formula_vs_disclosed_off_by_two_tenths_of_a_basis_point_fails() -> None:
    row = _etr_check(
        Decimal("0.156100"), Decimal("0.158"), 3
    )
    assert row["status"] == "fail"
    assert row["reason"] is None
    assert row["tolerance"] == "0.001"


def test_a6_coarser_disclosed_decimals_widen_the_tolerance() -> None:
    row = _etr_check(Decimal("0.156100"), Decimal("0.16"), 2)
    assert row["status"] == "pass"
    assert row["tolerance"] == "0.01"


def test_a6_unvalued_disclosed_rate_is_not_evaluable() -> None:
    row = _etr_check(Decimal("0.156100"), None, 3)
    assert row["status"] == "not_evaluable"
    assert row["reason"] == "missing_dependency"


# 49. PK05 probes, determinism, invariance, registry, CLI, A33 -------------------


def test_pk05_bank_probe_keeps_pack_applicable(pk05_result: dict) -> None:
    bank = produce_pack("PK05", _pk05_input(issuer_sic="6021", sic_source="dei"))
    assert bank["applicability"]["state"] == "applicable"
    assert bank["applicability"]["reason"] == "applicability_rule_satisfied"
    assert bank["fields"] == pk05_result["fields"]
    assert bank["checks"] == pk05_result["checks"]
    assert "issuer_class=bank" in bank["receipts"]
    assert contract.validate_pack_result(bank) == []


def test_pk05_quarterly_form_is_outside_pack_forms() -> None:
    package = load_golden_aapl_package(ROOT, accession=ACCESSION)
    quarterly = replace(
        package, manifest={**package.manifest, "form": "10-Q"}
    )
    result = produce_pack("PK05", _pk05_input(packages=(quarterly,)))
    assert result["applicability"]["state"] == "not_applicable"
    assert result["applicability"]["reason"] == "form_outside_pack_forms"
    # The framework's inapplicable shape emits one row per catalogue field
    # (17) — the calculation-children expansion never runs outside the
    # applicable branch.
    assert len(result["fields"]) == 17
    assert all(
        row["quality_state"] == "not_applicable"
        and row["reason"] == "form_outside_pack_forms"
        for row in result["fields"]
    )
    assert all(
        check["status"] == "not_applicable"
        and check["reason"] == "form_outside_pack_forms"
        for check in result["checks"]
    )
    assert result["coverage"]["disclosure_coverage_state"] == "not_supplied"
    assert contract.validate_pack_result(result) == []


def test_pk05_production_is_deterministic() -> None:
    first = produce_pack("PK05", _pk05_input())
    second = produce_pack("PK05", _pk05_input())
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["pack_content_sha256"] == second["pack_content_sha256"]


@pytest.mark.parametrize(
    "pack_id", sorted(PK05_BASE_PACK_ENVELOPE_SHA256)
)
def test_base_pack_envelopes_unchanged_by_pk05_edits(pack_id: str) -> None:
    # §TESTS 11: every pack registered at BASE keeps its AAPL envelope
    # byte-identical to BASE after PK05 registers.
    result = produce_pack(pack_id, _pk05_input())
    payload = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert (
        sha256(payload.encode("utf-8")).hexdigest()
        == PK05_BASE_PACK_ENVELOPE_SHA256[pack_id]
    )


def test_registered_pack_ids_is_base_set_plus_pk05() -> None:
    assert registered_pack_ids() == (
        "PK01",
        "PK02",
        "PK03",
        "PK04",
        "PK05",
        "PK06",
        "PK07",
        "PK08",
        "PK09",
        "PK10",
        "PK11",
        "PK12",
    )


def test_pk05_cli_writes_valid_envelope(tmp_path: Path) -> None:
    entity_file = tmp_path / "entity.json"
    query_file = tmp_path / "query.json"
    out_file = tmp_path / "pk05.json"
    entity_file.write_text(json.dumps(ENTITY), encoding="utf-8")
    query_file.write_text(json.dumps(PK05_QUERY), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "fif_specialist_packs.py"),
            "--pack",
            "PK05",
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
    assert len(envelope["fields"]) == 22
    assert envelope["coverage"]["valued_fields"] == 21
    assert all(check["status"] == "pass" for check in envelope["checks"])


def test_pk05_no_issuer_literals_in_specialist_pack_code() -> None:
    # A33: the specialist-pack production surface (every producer module, the
    # shared framework and the offline CLI) carries no issuer literal; the
    # extension prefix itself only ever arrives from filing data.
    production_files = sorted(
        (ROOT / "engine" / "fundamental_forensics" / "specialist_packs").glob(
            "*.py"
        )
    ) + [ROOT / "scripts" / "fif_specialist_packs.py"]
    assert production_files
    for path in production_files:
        text = path.read_text("utf-8")
        for literal in ("0000320193", "AAPL", "Apple", "aapl:"):
            assert literal not in text, f"{path.name} carries {literal!r}"


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


def _rf9_expected(field_id: str, pairs) -> str:
    ordered = sorted(pairs, key=lambda item: item[0].occurrence_id)
    return f"{field_id}: conflicting duplicate facts " + ", ".join(
        f"{occurrence.occurrence_id}={value}" for occurrence, value in ordered
    )


def _produce_with_ledger(
    monkeypatch, pack_id: str, occurrences: list[_RawFactOccurrence]
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
    return produce_pack(pack_id, _pack_input())


def test_rf9_axes_consolidated_conflict_names_the_conflict(monkeypatch) -> None:
    # Fold repair F1: the optional-axes resolver's whole-field conflict branch
    # discloses the duplicate facts exactly as the plain FactMapping path does.
    concept = (
        "us-gaap:AntidilutiveSecuritiesExcludedFromComputationOf"
        "EarningsPerShareAmount"
    )
    first = _probe_occurrence(
        key="axes-dup-a",
        concept=concept,
        value=Decimal("100"),
        measures=("xbrli:shares",),
        start=_date(2024, 9, 29),
        end=POR,
    )
    second = _probe_occurrence(
        key="axes-dup-b",
        concept=concept,
        value=Decimal("200"),
        measures=("xbrli:shares",),
        start=_date(2024, 9, 29),
        end=POR,
    )
    result = _produce_with_ledger(monkeypatch, "PK02", [first, second])
    row = _row(result, "antidilutive_securities_excluded")
    assert row["quality_state"] == "not_evaluable"
    assert row["reason"] == "missing_dependency"
    assert row["source_occurrence_ids"] == sorted(
        {first.occurrence_id, second.occurrence_id}
    )
    assert (
        _rf9_expected(
            "antidilutive_securities_excluded", ((first, "100"), (second, "200"))
        )
        in result["limitations"]
    )
    assert contract.validate_pack_result(result) == []


def test_rf9_typed_dimensioned_conflict_names_the_conflict() -> None:
    # Fold repair F1: two facts on the same typed member with different values.
    events = [
        _synthetic_occurrence(
            "us-gaap:RevenueRemainingPerformanceObligationPercentage",
            instant=_date(2025, 9, 27),
            typed=((RPO_TIMING_AXIS_QNAME, _typed_member("2025-09-28")),),
            value="0.66",
            decimals="2",
        ),
        _synthetic_occurrence(
            "us-gaap:RevenueRemainingPerformanceObligationPercentage",
            instant=_date(2025, 9, 27),
            typed=((RPO_TIMING_AXIS_QNAME, _typed_member("2025-09-28")),),
            value="0.70",
            decimals="2",
        ),
    ]
    sink: list[str] = []
    outcome = pack_base._resolve_typed_dimensioned_fact_mapping(
        pack_id="PK04",
        catalogue_field=_catalogue_field("PK04", "rpo_percentage_next_12m"),
        mapping=pk04_revenue._FIELD_MAPPINGS["rpo_percentage_next_12m"],
        ledger=RawFactLedger(events=tuple(events)),
        por=_date(2025, 9, 27),
        limitations=sink,
    )
    assert outcome.row["quality_state"] == "not_evaluable"
    assert outcome.row["reason"] == "missing_dependency"
    assert sink == [
        _rf9_expected(
            "rpo_percentage_next_12m", ((events[0], "0.66"), (events[1], "0.7"))
        )
    ]


def test_rf9_calculation_children_conflict_names_the_conflict() -> None:
    # Fold repair F1: duplicate child facts over the same longest duration.
    child = (
        "us-gaap:IncomeTaxReconciliationIncomeTaxExpenseBenefitAt"
        "FederalStatutoryIncomeTaxRate"
    )
    events = [
        _synthetic_occurrence(
            child,
            start=_date(2024, 9, 29),
            end=_date(2025, 9, 27),
            value="100000000",
        ),
        _synthetic_occurrence(
            child,
            start=_date(2024, 9, 29),
            end=_date(2025, 9, 27),
            value="200000000",
        ),
    ]
    sink: list[str] = []
    outcome = pack_base._resolve_calculation_children_mapping(
        pack_id="PK05",
        catalogue_field=_catalogue_field("PK05", "etr_reconciliation_line"),
        mapping=pk05_tax._FIELD_MAPPINGS["etr_reconciliation_line"],
        ledger=RawFactLedger(events=tuple(events)),
        por=_date(2025, 9, 27),
        primary=_CalPackage(_SYNTHETIC_CAL),
        limitation_sink=sink,
    )
    rows = [outcome.row, *outcome.extra_rows]
    conflict = next(row for row in rows if row["concept"] == child)
    assert conflict["quality_state"] == "not_evaluable"
    assert conflict["reason"] == "missing_dependency"
    assert sink == [
        _rf9_expected(
            "etr_reconciliation_line",
            ((events[0], "100000000"), (events[1], "200000000")),
        )
    ]


def _produce_pack_with_ledger(
    monkeypatch, pack_id: str, pack_input: PackInput, occurrences: list
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
    return produce_pack(pack_id, pack_input)


def test_pk04_grouped_conflict_names_the_duplicate_facts(monkeypatch) -> None:
    # R-F9 sink repair F1: the grouped resolver's per-member conflict row must
    # name the duplicate facts exactly as the plain FactMapping path does.
    revenue = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
    us_member = "{http://xbrl.sec.gov/country/2025}US"
    first = _probe_occurrence(
        key="geo-dup-a",
        concept=revenue,
        value=Decimal("800000000"),
        start=_date(2024, 9, 29),
        end=POR,
        dimensions=((GEOGRAPHICAL_LEDGER_AXIS, us_member),),
    )
    second = _probe_occurrence(
        key="geo-dup-b",
        concept=revenue,
        value=Decimal("900000000"),
        start=_date(2024, 9, 29),
        end=POR,
        dimensions=((GEOGRAPHICAL_LEDGER_AXIS, us_member),),
    )
    result = _produce_pack_with_ledger(
        monkeypatch, "PK04", _pk04_input(), [first, second]
    )
    row = _row(result, "revenue_disaggregated")
    assert row["quality_state"] == "not_evaluable"
    assert row["reason"] == "missing_dependency"
    assert row["source_occurrence_ids"] == sorted(
        {first.occurrence_id, second.occurrence_id}
    )
    assert (
        _rf9_expected(
            "revenue_disaggregated",
            ((first, "800000000"), (second, "900000000")),
        )
        in result["limitations"]
    )
    assert contract.validate_pack_result(result) == []


def test_pk03_grouped_conflict_names_the_duplicate_facts(monkeypatch) -> None:
    # R-F9 sink repair F1: same disclosure on a PK03 dimensioned segment field.
    revenue = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
    americas = _aapl_member("AmericasSegmentMember")
    first = _probe_occurrence(
        key="seg-dup-a",
        concept=revenue,
        value=Decimal("800000000"),
        start=_date(2024, 9, 29),
        end=POR,
        dimensions=(
            (SEGMENT_LEDGER_AXIS, americas),
            (CONSOLIDATION_ITEMS_LEDGER_AXIS, "us-gaap:OperatingSegmentsMember"),
        ),
    )
    second = _probe_occurrence(
        key="seg-dup-b",
        concept=revenue,
        value=Decimal("900000000"),
        start=_date(2024, 9, 29),
        end=POR,
        dimensions=(
            (SEGMENT_LEDGER_AXIS, americas),
            (CONSOLIDATION_ITEMS_LEDGER_AXIS, "us-gaap:OperatingSegmentsMember"),
        ),
    )
    result = _produce_pack_with_ledger(
        monkeypatch, "PK03", _pk03_input(), [first, second]
    )
    row = _row(result, "segment_revenue")
    assert row["quality_state"] == "not_evaluable"
    assert row["reason"] == "missing_dependency"
    assert row["source_occurrence_ids"] == sorted(
        {first.occurrence_id, second.occurrence_id}
    )
    assert (
        _rf9_expected(
            "segment_revenue",
            ((first, "800000000"), (second, "900000000")),
        )
        in result["limitations"]
    )
    assert contract.validate_pack_result(result) == []


def test_allowlist_conflict_names_the_duplicate_facts(monkeypatch) -> None:
    # R-F9 sink repair F1: the allowlist dimensioned resolver (PK03's
    # unallocated_corporate_and_eliminations) discloses the same conflict.
    revenue = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
    corporate = "us-gaap:CorporateNonSegmentMember"
    first = _probe_occurrence(
        key="elim-dup-a",
        concept=revenue,
        value=Decimal("800000000"),
        start=_date(2024, 9, 29),
        end=POR,
        dimensions=((CONSOLIDATION_ITEMS_LEDGER_AXIS, corporate),),
    )
    second = _probe_occurrence(
        key="elim-dup-b",
        concept=revenue,
        value=Decimal("900000000"),
        start=_date(2024, 9, 29),
        end=POR,
        dimensions=((CONSOLIDATION_ITEMS_LEDGER_AXIS, corporate),),
    )
    result = _produce_pack_with_ledger(
        monkeypatch, "PK03", _pk03_input(), [first, second]
    )
    row = _row(result, "unallocated_corporate_and_eliminations")
    assert row["quality_state"] == "not_evaluable"
    assert row["reason"] == "missing_dependency"
    assert row["source_occurrence_ids"] == sorted(
        {first.occurrence_id, second.occurrence_id}
    )
    assert (
        _rf9_expected(
            "unallocated_corporate_and_eliminations",
            ((first, "800000000"), (second, "900000000")),
        )
        in result["limitations"]
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
# 50. PK07: M&A, goodwill, intangibles and impairments -------------------------
#
# AAPL is the NEGATIVE issuer (fixture-verified ledger scan: 0 of the 964
# admitted facts match any B.2 numeric concept; no Business Combinations note;
# the NOTE_IMP heading's bare "Impairment" arm matches the policies prose, so
# that section locates while its pattern never hits). The positive path is
# proven on a synthetic in-test TESTCO inline-XBRL 10-K admitted by the same
# strict parser path as the golden fixture (§TESTS 5): the frozen §TESTS-3
# rollforward ledger (opening 1000, acquired 300, disposals 50, impairment
# 100, fx_other 10) plus the impairment pairs of §TESTS 4 and the Note 3 /
# Note 4 narrative the text fields search.
#
# Catalogue note (DEVIATIONS in the lane RETURN): the frozen PK07 catalogue
# carries no narrative reason code, so the stock section-scoped
# TextSpanMapping resolver would emit governing_section_not_supplied /
# narrative_span_not_located — reasons the PK07 catalogue refuses — and no
# envelope could be produced. The producer therefore runs the exact B.2 search
# itself through the finalize hook and types every narrative absence
# missing_dependency (the PK10 ruling), carrying the intended stock code
# verbatim in limitations.

PK07_QUERY = {**QUERY, "requested_metrics": ["mna"]}
# §TESTS 6 pins, captured at this lane's BASE (before PK07 registered) under
# this section's own input shape: PK07 registration must not move any BASE
# pack's AAPL envelope.
PK07_BASE_PACK_ENVELOPE_SHA256 = {
    "PK01": "520237dee6613f84f1900a051bc3ffb26db88fe5724b9ca466f9334ac09d8c92",
    "PK02": "453b9dd1b547953d761436ac8c99aeca1ef42a66cf2a91e339b60ca83d70ce31",
    "PK03": "0f62a747724035a233b1db209b34d5cf2bcd3920fb0e994b99543cf7d955bd6e",
    "PK04": "281d84d196751caca6ac23a217004766fb1483e2d5fc729309eb1bc30f64dc8f",
    "PK05": "3628a5ddde284650978617bcd7ae7ff922dd32ac0bbb8ab6e8f35ad2545967ac",
    "PK06": "84f9aad2836afa5b397253ff27807345d6245edf8f765b60b6e21d68449890f5",
    "PK09": "e2b2ec35ad31446eecf4a64da503661e5157f4ec73f42c888f89a4b11a9e7831",
    "PK10": "2ef05add8be8db7f9cb32a6fd55b47eab26fafdc2e603a2b7cbae9e074b234d0",
    "PK11": "140b630622b5e1ab49dd1743ad8eafb91be8872e7a20e9cfc72d2d59ffddaefc",
    "PK12": "4915af8ff2a916dd788d219de2329c6fc7703df5dfc3ac7a4e8dc7265f4ab48b",
}
# This producer's own byte-determinism pin, captured at the lane's fork point.
PK07_AAPL_ENVELOPE_SHA256 = (
    "0a7bd0756e39218bd3c4f7141be6310fd4d375856760daa2d8f8af57c747ffc8"
)
# §TESTS 1: the nine numeric rows cite the p10 concept of their alias tuple.
PK07_AAPL_MISSING = {
    "goodwill": "missing_standard_fact:us-gaap:Goodwill",
    "intangible_assets_net": (
        "missing_standard_fact:us-gaap:IntangibleAssetsNetExcludingGoodwill"
    ),
    "indefinite_lived_intangibles": (
        "missing_standard_fact:us-gaap:IndefiniteLivedIntangibleAssets"
        "ExcludingGoodwill"
    ),
    "goodwill_acquired": (
        "missing_standard_fact:us-gaap:GoodwillAcquiredDuringPeriod"
    ),
    "goodwill_disposals": (
        "missing_standard_fact:us-gaap:GoodwillWrittenOffRelatedToSaleOf"
        "BusinessUnit"
    ),
    "goodwill_fx_other": (
        "missing_standard_fact:us-gaap:GoodwillForeignCurrencyTranslationGainLoss"
    ),
    "goodwill_impairment_loss": (
        "missing_standard_fact:us-gaap:GoodwillImpairmentLoss"
    ),
    "intangible_impairment_loss": (
        "missing_standard_fact:us-gaap:ImpairmentOfIntangibleAssets"
        "ExcludingGoodwill"
    ),
    "business_combination_consideration": (
        "missing_standard_fact:us-gaap:BusinessCombinationConsideration"
        "Transferred1"
    ),
}
# The catalogue carries no narrative code, so every narrative absence types
# missing_dependency; the intended stock code rides in limitations (below).
# impairment_testing_note_span is "missing" (not "not_evaluable") because the
# frozen NOTE_IMP heading's "Impairment" arm matches the policies prose while
# the pattern never hits — narrative_span_not_located, not
# governing_section_not_supplied (B.3 nuance recorded in the lane RETURN).
PK07_AAPL_NARRATIVE = {
    "acquisition_date": ("not_evaluable", "governing_section_not_supplied"),
    "purchase_accounting_note_span": ("not_evaluable", "governing_section_not_supplied"),
    "impairment_testing_note_span": ("missing", "narrative_span_not_located"),
}

TESTCO_CIK = "0000000001"
TESTCO_SIC = "3571"
TESTCO_DOC = "testco-20251231.htm"
TESTCO_ENTITY = {
    "entity_id": TESTCO_CIK,
    "cik": TESTCO_CIK,
    "ticker": "TESTCO",
    "name": "TESTCO CORP",
    "identity_basis": "golden_filing_package_fixture_v1",
    "source_entity_id": TESTCO_CIK,
}
# The frozen synthetic M&A ledger (§TESTS 3): (qname, context, value, unit).
# c-ip is the comparative balance-sheet date 2024-12-31 (the opening_instant
# bound for the FY2025 duration), c-i the closing instant, c-fy the year.
_TESTCO_ROLLFORWARD = (
    ("us-gaap:Goodwill", "c-ip", "1000", "usd"),
    ("us-gaap:Goodwill", "c-i", "1160", "usd"),
    ("us-gaap:GoodwillAcquiredDuringPeriod", "c-fy", "300", "usd"),
    ("us-gaap:GoodwillWrittenOffRelatedToSaleOfBusinessUnit", "c-fy", "50", "usd"),
    ("us-gaap:GoodwillImpairmentLoss", "c-fy", "100", "usd"),
    ("us-gaap:GoodwillForeignCurrencyTranslationGainLoss", "c-fy", "10", "usd"),
)
_TESTCO_CONTEXTS = {
    "c-ip": (
        "<xbrli:context id=\"c-ip\"><xbrli:entity><xbrli:identifier"
        " scheme=\"http://www.sec.gov/CIK\">"
        f"{TESTCO_CIK}</xbrli:identifier></xbrli:entity><xbrli:period>"
        "<xbrli:instant>2024-12-31</xbrli:instant></xbrli:period></xbrli:context>"
    ),
    "c-i": (
        "<xbrli:context id=\"c-i\"><xbrli:entity><xbrli:identifier"
        " scheme=\"http://www.sec.gov/CIK\">"
        f"{TESTCO_CIK}</xbrli:identifier></xbrli:entity><xbrli:period>"
        "<xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>"
    ),
    "c-fy": (
        "<xbrli:context id=\"c-fy\"><xbrli:entity><xbrli:identifier"
        " scheme=\"http://www.sec.gov/CIK\">"
        f"{TESTCO_CIK}</xbrli:identifier></xbrli:entity><xbrli:period>"
        "<xbrli:startDate>2025-01-01</xbrli:startDate>"
        "<xbrli:endDate>2025-12-31</xbrli:endDate></xbrli:period></xbrli:context>"
    ),
}
_TESTCO_UNITS = {
    "usd": '<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>',
    "eur": '<xbrli:unit id="eur"><xbrli:measure>iso4217:EUR</xbrli:measure></xbrli:unit>',
}


def _testco_document(
    facts: tuple[tuple[str, str, str, str], ...],
) -> bytes:
    """A minimal inline-XBRL 1.1 TESTCO 10-K with the B.2 narrative.

    Note 3 – Business Combinations supplies the acquisition-date pattern
    ("completed on <Month D, YYYY>") and the purchase-accounting wording;
    Note 4 – Goodwill and Other Intangible Assets supplies the
    impairment-testing wording. Contexts and units are emitted for exactly
    the ids the frozen facts cite.
    """
    rows = "\n".join(
        f"<tr><td>item {index}</td><td>"
        f'<ix:nonFraction id="f-{index}" name="{qname}"'
        f' contextRef="{context}" unitRef="{unit}" decimals="0">{value}'
        "</ix:nonFraction></td></tr>"
        for index, (qname, context, value, unit) in enumerate(facts, start=1)
    )
    contexts = "\n".join(
        _TESTCO_CONTEXTS[context_id]
        for context_id in ("c-ip", "c-i", "c-fy")
        if any(context == context_id for _q, context, _v, _u in facts)
    )
    units = "\n".join(
        _TESTCO_UNITS[unit_id]
        for unit_id in ("usd", "eur")
        if any(unit == unit_id for _q, _c, _v, unit in facts)
    )
    template = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml"'
        ' xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"'
        ' xmlns:xbrli="http://www.xbrl.org/2003/instance"'
        ' xmlns:iso4217="http://www.xbrl.org/2003/iso4217"'
        ' xmlns:us-gaap="http://fasb.org/us-gaap/2025">\n'
        "<head><title>TESTCO 10-K</title></head>\n<body>\n"
        '<div style="display:none"><ix:header><ix:resources>\n'
        f"{contexts}\n{units}\n</ix:resources></ix:header></div>\n"
        "<p>Note 3 – Business Combinations. The acquisition of Testcorp"
        " Incorporated was completed on March 15, 2025. The purchase price was"
        " allocated to the assets acquired and liabilities assumed based on"
        " their fair values.</p>\n"
        "<p>Note 4 – Goodwill and Other Intangible Assets. The Company"
        " performs its annual impairment test for goodwill and reviews"
        " intangible assets whenever events or changes in circumstances"
        " indicate a possible impairment.</p>\n"
        f"<table>\n{rows}\n</table>\n</body></html>\n"
    )
    return template.encode("utf-8")


def _testco_package(
    facts: tuple[tuple[str, str, str, str], ...] = _TESTCO_ROLLFORWARD,
    *,
    form: str = "10-K",
) -> GoldenFilingPackage:
    document = _testco_document(facts)
    manifest = {
        "entity_id": TESTCO_CIK,
        "cik": TESTCO_CIK,
        "legal_name": "TESTCO CORP",
        "form": form,
        "period_of_report": "2025-12-31",
        "filing_date": "2026-02-15",
        "accession": "0000000001-26-000010",
        "primary_document": TESTCO_DOC,
        "source_accepted_at": "2026-02-15T16:00:00Z",
        "fixture_recorded_at": "2026-02-15T16:05:00Z",
        "members": [
            {
                "name": TESTCO_DOC,
                "state": "stored",
                "content_sha256": sha256(document).hexdigest(),
            }
        ],
    }
    return GoldenFilingPackage(
        manifest=manifest, members={TESTCO_DOC: document}
    )


def _pk07_input(**overrides) -> PackInput:
    defaults = dict(
        packages=(load_golden_aapl_package(ROOT, accession=ACCESSION),),
        entity=ENTITY,
        query=PK07_QUERY,
        issuer_sic="3571",
        sic_source="sec_submissions",
    )
    defaults.update(overrides)
    return PackInput(**defaults)


def _pk07_testco_input(
    facts: tuple[tuple[str, str, str, str], ...] = _TESTCO_ROLLFORWARD,
    **overrides,
) -> PackInput:
    defaults = dict(
        packages=(_testco_package(facts),),
        entity=TESTCO_ENTITY,
        query=PK07_QUERY,
        issuer_sic=TESTCO_SIC,
        sic_source="sec_submissions",
    )
    defaults.update(overrides)
    return PackInput(**defaults)


@pytest.fixture(scope="module")
def pk07_result() -> dict:
    return produce_pack("PK07", _pk07_input())


def _pk07_check(result: dict, check_id: str) -> dict:
    return _check(result, check_id)


# 50.1 §TESTS 1: the AAPL negative envelope ------------------------------------


def test_pk07_result_passes_contract_validator(pk07_result: dict) -> None:
    assert contract.validate_pack_result(pk07_result) == []


def test_pk07_aapl_is_applicable_and_every_numeric_row_is_typed_absence(
    pk07_result: dict,
) -> None:
    catalogue = contract.load_pack_schema("PK07")
    assert [row["field_id"] for row in pk07_result["fields"]] == [
        item["field_id"] for item in catalogue["fields"]
    ]
    assert pk07_result["applicability"] == {
        "state": "applicable",
        "reason": "applicability_rule_satisfied",
        "rule_id": "pack.pk07.applicability/v1",
        "sic": "3571",
        "sic_source": "sec_submissions",
    }
    for field_id, reason in PK07_AAPL_MISSING.items():
        row = _row(pk07_result, field_id)
        assert row["quality_state"] == "missing", field_id
        assert row["non_value_state"] == "missing", field_id
        assert row["coverage_state"] == "unmapped", field_id
        assert row["reason"] == reason, field_id
        assert row["value"] is None and row["text_value"] is None
        assert row["concept"] == reason.split(":", 1)[1]
        assert row["evidence_kind"] == "xbrl_fact"


def test_pk07_aapl_narrative_rows_are_typed_absence_with_intended_code_in_limitations(
    pk07_result: dict,
) -> None:
    for field_id, (quality, intended) in PK07_AAPL_NARRATIVE.items():
        row = _row(pk07_result, field_id)
        # The frozen PK07 catalogue carries no narrative reason code, so the
        # row cites the catalogue's closest code; the stock code the packet
        # names rides in the field's limitation line verbatim.
        assert row["quality_state"] == quality, field_id
        assert row["non_value_state"] == quality, field_id
        assert row["reason"] == "missing_dependency", field_id
        assert row["text_value"] is None and row["source_span"] is None
        assert row["evidence_kind"] == "text_span"
        assert any(
            f"pk07.{field_id}: {intended};" in line
            for line in pk07_result["limitations"]
        ), field_id


def test_pk07_aapl_checks_abstain_typed(pk07_result: dict) -> None:
    catalogue = contract.load_pack_schema("PK07")
    assert [check["check_id"] for check in pk07_result["checks"]] == [
        item["check_id"] for item in catalogue["checks"]
    ]
    for check_id in (
        "goodwill_rollforward_closed",
        "impairment_vs_carrying",
        "acquisition_scope_stated",
    ):
        check = _pk07_check(pk07_result, check_id)
        assert check["status"] == "not_evaluable", check_id
        assert check["reason"] == "missing_dependency", check_id


def test_pk07_aapl_coverage_receipts_and_limitations(pk07_result: dict) -> None:
    # B.3: 0 of 12 valued — a deal-free year is a negative finding, never
    # non-applicability.
    assert pk07_result["coverage"] == {
        "valued_fields": 0,
        "missing_fields": 10,
        "unsupported_fields": 0,
        "not_evaluable_fields": 2,
        "not_applicable_fields": 0,
        "disclosure_coverage_state": "empty",
    }
    assert "pk07_numeric_fact_count=0" in pk07_result["receipts"]
    limitations = pk07_result["limitations"]
    assert limitations[0] == pack_base.DISPLAY_ONLY_LIMITATION
    assert (
        "pk07.table_cell_reserved: business_combination_consideration resolves"
        " from xbrl_fact only in this version" in limitations
    )
    assert (
        "pk07.negative_year: no goodwill, intangible or business-combination"
        " facts in the primary filing" in limitations
    )
    assert (
        "pk07.acquisition_date: governing_section_not_supplied;"
        " section searched: Note \\d+ [–-] (?:Business Combinations?|"
        "Acquisitions?)" in limitations
    )
    assert (
        "pk07.impairment_testing_note_span: narrative_span_not_located;"
        " section searched: (?:Goodwill and (?:Other )?Intangible Assets|"
        "Impairment)" in limitations
    )


def test_pk07_aapl_envelope_digest_is_pinned() -> None:
    result = produce_pack("PK07", _pk07_input())
    payload = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert sha256(payload.encode("utf-8")).hexdigest() == PK07_AAPL_ENVELOPE_SHA256


def test_pk07_production_is_deterministic() -> None:
    first = produce_pack("PK07", _pk07_input())
    second = produce_pack("PK07", _pk07_input())
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["pack_content_sha256"] == second["pack_content_sha256"]


# 50.2 §TESTS 2: the 10-Q probe -------------------------------------------------


def test_pk07_quarterly_form_is_outside_pack_forms() -> None:
    package = load_golden_aapl_package(ROOT, accession=ACCESSION)
    quarterly = replace(
        package, manifest={**package.manifest, "form": "10-Q"}
    )
    result = produce_pack("PK07", _pk07_input(packages=(quarterly,)))
    assert result["applicability"]["state"] == "not_applicable"
    assert result["applicability"]["reason"] == "form_outside_pack_forms"
    assert len(result["fields"]) == 12
    assert all(
        row["quality_state"] == "not_applicable"
        and row["reason"] == "form_outside_pack_forms"
        for row in result["fields"]
    )
    assert all(
        check["status"] == "not_applicable"
        and check["reason"] == "form_outside_pack_forms"
        for check in result["checks"]
    )
    assert result["coverage"]["disclosure_coverage_state"] == "not_supplied"
    assert contract.validate_pack_result(result) == []


# 50.3 §TESTS 3: the synthetic rollforward (in-test TESTCO ledger) --------------


def test_pk07_rollforward_closes_on_the_synthetic_ledger() -> None:
    result = produce_pack("PK07", _pk07_testco_input())
    assert contract.validate_pack_result(result) == []
    check = _pk07_check(result, "goodwill_rollforward_closed")
    # 1000 + 300 - 50 - 100 + 10 = 1160, tolerance 1 (decimals 0).
    assert check["status"] == "pass"
    assert check["reason"] is None
    assert check["tolerance"] == "1"
    assert check["evidence_field_ids"] == [
        "goodwill",
        "goodwill_acquired",
        "goodwill_disposals",
        "goodwill_impairment_loss",
        "goodwill_fx_other",
    ]
    assert _row(result, "goodwill")["value"] == "1160"


def test_pk07_rollforward_fails_when_closing_does_not_close() -> None:
    moved = tuple(
        ("us-gaap:Goodwill", "c-i", "1200", "usd")
        if fact[0] == "us-gaap:Goodwill" and fact[1] == "c-i"
        else fact
        for fact in _TESTCO_ROLLFORWARD
    )
    result = produce_pack("PK07", _pk07_testco_input(moved))
    check = _pk07_check(result, "goodwill_rollforward_closed")
    assert check["status"] == "fail"
    assert check["reason"] is None


def test_pk07_rollforward_missing_component_is_never_zero() -> None:
    # K3K4: dropping goodwill_fx_other makes the rollforward abstain typed —
    # the component is ABSENT, not zero (1000+300-50-100 = 1150 would close
    # nothing here and must never be asserted as an implied fx_other).
    dropped = tuple(
        fact for fact in _TESTCO_ROLLFORWARD
        if fact[0] != "us-gaap:GoodwillForeignCurrencyTranslationGainLoss"
    )
    result = produce_pack("PK07", _pk07_testco_input(dropped))
    check = _pk07_check(result, "goodwill_rollforward_closed")
    assert check["status"] == "not_evaluable"
    assert check["reason"] == "missing_dependency"


# 50.4 §TESTS 4: the synthetic impairment_vs_carrying pairs ---------------------


def test_pk07_impairment_within_opening_goodwill_passes() -> None:
    facts = (
        ("us-gaap:Goodwill", "c-ip", "1000", "usd"),
        ("us-gaap:GoodwillImpairmentLoss", "c-fy", "100", "usd"),
    )
    result = produce_pack("PK07", _pk07_testco_input(facts))
    assert contract.validate_pack_result(result) == []
    check = _pk07_check(result, "impairment_vs_carrying")
    assert check["status"] == "pass"
    assert check["reason"] is None


def test_pk07_impairment_exceeding_opening_goodwill_fails() -> None:
    facts = (
        ("us-gaap:Goodwill", "c-ip", "1000", "usd"),
        ("us-gaap:GoodwillImpairmentLoss", "c-fy", "1500", "usd"),
    )
    result = produce_pack("PK07", _pk07_testco_input(facts))
    check = _pk07_check(result, "impairment_vs_carrying")
    assert check["status"] == "fail"
    assert check["reason"] is None


def test_pk07_intangible_pair_in_eur_is_unit_mismatch() -> None:
    # The goodwill pair ties in USD; the intangible pair's impairment is USD
    # while its prior-instant carrying amount is EUR — differing units are
    # never compared.
    facts = (
        ("us-gaap:Goodwill", "c-ip", "1000", "usd"),
        ("us-gaap:GoodwillImpairmentLoss", "c-fy", "100", "usd"),
        ("us-gaap:IntangibleAssetsNetExcludingGoodwill", "c-ip", "900", "eur"),
        (
            "us-gaap:ImpairmentOfIntangibleAssetsExcludingGoodwill",
            "c-fy",
            "40",
            "usd",
        ),
    )
    result = produce_pack("PK07", _pk07_testco_input(facts))
    check = _pk07_check(result, "impairment_vs_carrying")
    assert check["status"] == "not_evaluable"
    assert check["reason"] == "unit_mismatch"


# 50.5 B.2/B.4 positive narrative path on the same synthetic package -----------


def test_pk07_synthetic_narrative_rows_value_and_scope_check_passes() -> None:
    result = produce_pack("PK07", _pk07_testco_input())
    acquisition_date = _row(result, "acquisition_date")
    assert acquisition_date["quality_state"] == "valued"
    assert acquisition_date["text_value"] == "March 15, 2025"
    assert acquisition_date["evidence_kind"] == "text_span"
    span = acquisition_date["source_span"]
    assert span["accession"] == "0000000001-26-000010"
    assert span["document_id"] == TESTCO_DOC
    assert span["end_offset"] > span["start_offset"]
    purchase = _row(result, "purchase_accounting_note_span")
    assert purchase["quality_state"] == "valued"
    assert "purchase price" in purchase["text_value"]
    impairment_note = _row(result, "impairment_testing_note_span")
    assert impairment_note["quality_state"] == "valued"
    assert "impairment test" in impairment_note["text_value"]
    check = _pk07_check(result, "acquisition_scope_stated")
    assert check["status"] == "pass"
    assert check["reason"] is None
    # The positive year carries no negative_year limitation and no narrative
    # absence line.
    assert not any(
        line.startswith("pk07.negative_year:") for line in result["limitations"]
    )
    assert not any(
        line.startswith("pk07.acquisition_date:") for line in result["limitations"]
    )
    assert "pk07_numeric_fact_count=6" in result["receipts"]
    # 5 numeric rollforward rows + the 3 narrative rows valued; the four
    # intangible/consideration fields carry no TESTCO fact.
    assert result["coverage"]["valued_fields"] == 8
    assert result["coverage"]["missing_fields"] == 4
    assert result["coverage"]["disclosure_coverage_state"] == "present"
    assert contract.validate_pack_result(result) == []


def test_pk07_synthetic_package_without_narrative_member_types_absence() -> None:
    # §TESTS 5 shape: a manifest-only package whose facts arrive through the
    # patched converter has no retained primary document, so every narrative
    # row types missing_dependency and names the section searched.
    events = tuple()
    def _convert(packages):
        receipt = FilingConversionReceipt(
            accession="0000000001-26-000010",
            parser_numeric_fact_count=0,
            ledger_occurrence_count=0,
            represented_count=0,
            excluded={},
            source_namespace_families=("us-gaap",),
        )
        report = ConversionReport(
            filings=(receipt,),
            ledger_sha256="0" * 64,
            source_namespace_families=("us-gaap",),
        )
        return RawFactLedger(events), {}, report

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(ixbrl_module, "parse_and_convert_golden_packages", _convert)
    try:
        manifest_only = _SyntheticPackage(
            {
                "cik": TESTCO_CIK,  # R-F4: package issuer == packet entity
                "form": "10-K",
                "period_of_report": "2025-12-31",
                "accession": "0000000001-26-000010",
                "primary_document": TESTCO_DOC,
            }
        )
        result = produce_pack(
            "PK07",
            _pk07_testco_input(packages=(manifest_only,)),
        )
    finally:
        monkeypatch.undo()
    for field_id in (
        "acquisition_date",
        "purchase_accounting_note_span",
        "impairment_testing_note_span",
    ):
        row = _row(result, field_id)
        assert row["quality_state"] == "missing", field_id
        assert row["reason"] == "missing_dependency", field_id
        assert any(
            f"pk07.{field_id}: narrative document not retained;" in line
            for line in result["limitations"]
        ), field_id
    assert contract.validate_pack_result(result) == []


# 50.6 §TESTS 6: BASE invariance, registry, CLI, A33 ----------------------------


@pytest.mark.parametrize("pack_id", sorted(PK07_BASE_PACK_ENVELOPE_SHA256))
def test_base_pack_envelopes_unchanged_by_pk07_edits(pack_id: str) -> None:
    # §TESTS 6: every pack registered at BASE keeps its AAPL envelope
    # byte-identical to BASE after PK07 registers.
    result = produce_pack(pack_id, _pk07_input())
    payload = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert (
        sha256(payload.encode("utf-8")).hexdigest()
        == PK07_BASE_PACK_ENVELOPE_SHA256[pack_id]
    )


def test_registered_pack_ids_is_base_set_plus_pk07() -> None:
    assert registered_pack_ids() == (
        "PK01",
        "PK02",
        "PK03",
        "PK04",
        "PK05",
        "PK06",
        "PK07",
        "PK08",
        "PK09",
        "PK10",
        "PK11",
        "PK12",
    )


def test_pk07_cli_writes_valid_envelope(tmp_path: Path) -> None:
    entity_file = tmp_path / "entity.json"
    query_file = tmp_path / "query.json"
    out_file = tmp_path / "pk07.json"
    entity_file.write_text(json.dumps(ENTITY), encoding="utf-8")
    query_file.write_text(json.dumps(PK07_QUERY), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "fif_specialist_packs.py"),
            "--pack",
            "PK07",
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
    assert envelope["coverage"]["valued_fields"] == 0
    assert len(envelope["fields"]) == 12


# 51. PK08: legal contingencies -------------------------------------------------
#
# AAPL is the POSITIVE narrative issuer with a nil ledger line: the fixture
# tags an undimensioned nil us-gaap:CommitmentsAndContingencies at both
# balance-sheet dates (2025-09-27 and 2024-09-28 — §TESTS 1), no accrual or
# range facts, and carries us-gaap:LossContingenciesByNatureOfContingencyAxis
# only on prior-period facts (durations to 2024-09-28 and instants at it), so
# contingency_nature types missing_standard_fact while the axis demonstrably
# exists in the ledger. Item 3's body contains both the allegation and the
# procedural patterns, so both spans value. The positive ledger paths (the
# accrual-vs-range arithmetic, the prose-only range ruling, the valued axis
# member and the 10-Q / 8-K form gates) are proven on a synthetic in-test
# TESTCO inline-XBRL filing admitted by the same strict parser path as the
# golden fixture.
#
# Catalogue note (DEVIATIONS in the lane RETURN): the frozen PK08 catalogue
# carries no narrative reason code (no narrative_span_not_located, no
# governing_section_not_supplied), so the stock section-scoped resolver is
# never entered — the producer's finalize hook runs the exact B.2/B.3 search
# itself and types every narrative absence missing_dependency, carrying the
# intended stock code verbatim in limitations (PK07/PK10 precedent). The
# catalogue's enum lists also lack the packet's `not_material` and `valued`
# literals: a match on those arms is a non-valued missing_dependency row
# (A.3), never an invented literal. B.5's "AAPL -> the not_material literal"
# therefore lands as the A.3 typed absence recorded in DEVIATIONS.

PK08_QUERY = {**QUERY, "requested_metrics": ["contingencies"]}
# §TESTS 6 pins, captured at this lane's BASE (before PK08 registered) under
# this section's own input shape: PK08 registration must not move any BASE
# pack's AAPL envelope.
PK08_BASE_PACK_ENVELOPE_SHA256 = {
    "PK01": "b08df45a24f9a59a5c319f67b0cd998d75a9424e676e606691a5245fcee2e194",
    "PK02": "a89bea23867fd4f80ac651546b4d51308a675e75354b9ef2961d4f88bfd5aef3",
    "PK03": "a7939783be7a12f1454287af7a5ba124a079d80d33a14ff1f127276f03807684",
    "PK04": "74782c242d506963311af36d6b5be35b5513963e78c706259f1ed3c648e32825",
    "PK05": "ac0cf6c6d5fb655b622d57317c376602ac357a7e3c075b60c8ef4fa7e6679740",
    "PK06": "1f78880eba88a185421ccc943e8e227bf7d264e5fea6ac8af1c96d75a793e229",
    "PK07": "0ff8a0e0ed118c716d3417e3765a131e94054fa57ab8eb9a2b0ade02fb89a153",
    "PK09": "14214c76ec6da3de6ebdd280b5f1a4f1348f7bdffd73145dc42271b23f8c8454",
    "PK10": "655d3ff540c539e2f2b2a20104f286d68baaa6a18990e1ec46d52cc7cd6f32ba",
    "PK11": "58e1c524a82210daffc392c855309c73b5d4ca55732c100c3a3a6babe7d41ba4",
    "PK12": "e3578db64f6e41c5ec5633b5b529fc87ca742a2857639bbaf2ba28ec4480f830",
}
# This producer's own byte-determinism pin, captured at the lane's fork point;
# re-pinned by the second repair (review F3 seat ruling): the range row's
# mapping_rule_digest now pins the live RANGE_DISCLOSED_PATTERN bytes (masked-
# envelope diff vs the previous pin: empty).
PK08_AAPL_ENVELOPE_SHA256 = (
    "9200ce0e91e7867e1186e5b96f0ecbdc01d3f56fddfb5d81ff07f13e905260b3"
)
# §TESTS 1: the fixture's two nil balance-sheet occurrences (ledger scan).
PK08_AAPL_NIL_IDS = {
    "2025-09-27": "rawfact_039d3a6b4da575d1db7036cbfa34d4208cde00151376159c5987ede5157bf50d",
    "2024-09-28": "rawfact_5fe347cd998b8b9c606b2730508ee7ca4b509bb16fc5d42f45e71f4c608df4ec",
}
# §TESTS 2: the Item 3 sentences the fixture's body supplies (§B.5's "report
# either way" — both patterns hit).
PK08_AAPL_ALLEGATION = (
    "District Court for the District of New Jersey against the Company "
    "alleging monopolization or attempted monopolization in the markets for "
    "“performance smartphones” and “smartphones” in violation of U.S."
)
PK08_AAPL_PROCEDURAL = "The Company has appealed the Commission’s Article 5(4) decision."
PK08_AAPL_NON_VALUED = {
    "loss_contingency_accrual": (
        "missing_standard_fact:us-gaap:LossContingencyAccrualAtCarryingValue"
    ),
    "loss_contingency_range_low": (
        "missing_standard_fact:us-gaap:LossContingencyRangeOfPossibleLossMinimum"
    ),
    "loss_contingency_range_high": (
        "missing_standard_fact:us-gaap:LossContingencyRangeOfPossibleLossMaximum"
    ),
    # A.3: the not_material arm matched, but the catalogue's enum list lacks
    # that literal — a typed absence, never an invented literal.
    "loss_contingency_range_disclosed": "missing_dependency",
    "contingency_nature": (
        "missing_standard_fact:us-gaap:LossContingenciesByNatureOfContingencyAxis"
    ),
}

PK08_TESTCO_CIK = "0000000002"
PK08_TESTCO_DOC = "testco2-20251231.htm"
PK08_TESTCO_ENTITY = {
    "entity_id": PK08_TESTCO_CIK,
    "cik": PK08_TESTCO_CIK,
    "ticker": "TESTCO",
    "name": "TESTCO TWO CORP",
    "identity_basis": "golden_filing_package_fixture_v1",
    "source_entity_id": PK08_TESTCO_CIK,
}
# The synthetic contingencies ledger (§TESTS 3/4/5): (qname, context, value,
# unit); value None is the nil balance-sheet line. c-i is the closing instant,
# c-fy the fiscal year, c-ax the year under the loss-contingency axis.
_PK08_CNC = "us-gaap:CommitmentsAndContingencies"
_PK08_ACCRUAL = "us-gaap:LossContingencyAccrualAtCarryingValue"
_PK08_RANGE_LOW = "us-gaap:LossContingencyRangeOfPossibleLossMinimum"
_PK08_RANGE_HIGH = "us-gaap:LossContingencyRangeOfPossibleLossMaximum"
_PK08_NATURE_AXIS = "us-gaap:LossContingenciesByNatureOfContingencyAxis"
_PK08_NIL_FACTS = ((_PK08_CNC, "c-i", None, "usd"),)
_PK08_TESTCO_CONTEXTS = {
    "c-i": (
        '<xbrli:context id="c-i"><xbrli:entity><xbrli:identifier'
        ' scheme="http://www.sec.gov/CIK">'
        f"{PK08_TESTCO_CIK}</xbrli:identifier></xbrli:entity><xbrli:period>"
        "<xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>"
    ),
    "c-fy": (
        '<xbrli:context id="c-fy"><xbrli:entity><xbrli:identifier'
        ' scheme="http://www.sec.gov/CIK">'
        f"{PK08_TESTCO_CIK}</xbrli:identifier></xbrli:entity><xbrli:period>"
        "<xbrli:startDate>2025-01-01</xbrli:startDate>"
        "<xbrli:endDate>2025-12-31</xbrli:endDate></xbrli:period></xbrli:context>"
    ),
    "c-ax": (
        '<xbrli:context id="c-ax"><xbrli:entity><xbrli:identifier'
        ' scheme="http://www.sec.gov/CIK">'
        f"{PK08_TESTCO_CIK}</xbrli:identifier></xbrli:entity><xbrli:period>"
        "<xbrli:startDate>2025-01-01</xbrli:startDate>"
        "<xbrli:endDate>2025-12-31</xbrli:endDate></xbrli:period>"
        '<xbrli:scenario><xbrldi:explicitMember'
        f' dimension="{_PK08_NATURE_AXIS}">'
        "test:LitigationMember</xbrldi:explicitMember></xbrli:scenario>"
        "</xbrli:context>"
    ),
}
_PK08_CONTING_CLEAN = (
    "Contingencies The Company is subject to various legal proceedings and "
    "claims that have arisen in the ordinary course of business."
)
_PK08_CONTING_RANGE = (
    "Contingencies The Company is a party to certain pending legal matters. "
    "For those matters, the Company estimates a range of reasonably possible "
    "loss of $10 million to $20 million."
)
# Range-pattern revision v2 (F1/F2 review): the reviewer's literal inputs.
_PK08_CONTING_RANGE_FULL_DIGIT = (
    "Contingencies The Company is a party to certain pending legal matters. "
    "For those matters, the Company estimates a range of reasonably possible "
    "loss of $450,000,000 to $900,000,000."
)
_PK08_CONTING_NOT_ESTIMABLE_AFTER_BE = (
    "Contingencies The Company is a party to certain pending legal matters. "
    "For those matters, the loss or range of loss cannot be reasonably "
    "estimated by the Company."
)
_PK08_CONTING_NOT_ESTIMABLE_NO_BE = (
    "Contingencies The Company is a party to certain pending legal matters. "
    "For those matters, the Company cannot reasonably estimate the loss or "
    "range of loss."
)
_PK08_CONTING_NOT_ESTIMABLE_OVER_MATERIAL = (
    "Contingencies The Company is a party to certain pending legal matters. "
    "For those matters, the Company has no material exposure and the loss or "
    "range of loss cannot be reasonably estimated by the Company."
)
# Second repair (review F2): the two sentences the first repair's arm still
# typed missing/missing_dependency.
_PK08_CONTING_NOT_ESTIMABLE_NOT_POSSIBLE = (
    "Contingencies The Company is a party to certain pending legal matters. "
    "For those matters, it is not possible to estimate the amount or range "
    "of loss."
)
_PK08_CONTING_NOT_ESTIMABLE_CANNOT_BE_MADE = (
    "Contingencies The Company is a party to certain pending legal matters. "
    "For those matters, an estimate of the possible loss cannot be made."
)
# Second repair (review F2): a dollar range governs a not-estimable phrase —
# both orders resolve by RANGE_ARM_PRIORITY, never first-match-by-position.
_PK08_CONTING_DISCLOSED_THEN_NOT_ESTIMABLE = (
    "Contingencies The Company is a party to certain pending legal matters. "
    "For those matters, the Company estimates a range of reasonably possible "
    "loss of $10 million to $20 million, although the loss cannot be "
    "reasonably estimated beyond that range."
)
_PK08_CONTING_NOT_ESTIMABLE_THEN_DISCLOSED = (
    "Contingencies The Company is a party to certain pending legal matters. "
    "The loss cannot be reasonably estimated in full, although for those "
    "matters the Company estimates a range of reasonably possible loss of "
    "$10 million to $20 million."
)
_PK08_CONTING_BARE_DOLLAR = (
    "Contingencies The Company is a party to certain pending legal matters. "
    "For those matters, the Company considers a loss of $ reasonably "
    "possible but cannot quantify an amount."
)
_PK08_ITEM3_BODY = (
    "Item 3. Legal Proceedings The Company and its subsidiaries are parties "
    "to litigation and claims in the ordinary course of business. On October "
    "1, 2025, a putative class action was filed against the Company alleging "
    "violations of federal antitrust laws. The Company has appealed an "
    "adverse ruling in one proceeding."
)


def _pk08_testco_document(
    facts: tuple[tuple[str, str, str | None, str], ...],
    *,
    contingencies_prose: str,
    item3: bool,
) -> bytes:
    """A minimal inline-XBRL TESTCO filing with the B.2 contingencies narrative.

    Note 12 – Commitments and Contingencies supplies the note and its
    Contingencies subsection; Note 13 closes the note; the Item 3 / Item 4
    pair supplies the legal-proceedings section (omitted on the 10-Q probe).
    Contexts and units are emitted for exactly the ids the facts cite; a
    ``None`` value emits the nil balance-sheet line (``xsi:nil="true"``).
    """
    rows = []
    for index, (qname, context, value, unit) in enumerate(facts, start=1):
        if value is None:
            rows.append(
                f'<tr><td>item {index}</td><td>'
                f'<ix:nonFraction id="f-{index}" name="{qname}"'
                f' contextRef="{context}" unitRef="{unit}" xsi:nil="true"/>'
                "</td></tr>"
            )
        else:
            rows.append(
                f'<tr><td>item {index}</td><td>'
                f'<ix:nonFraction id="f-{index}" name="{qname}"'
                f' contextRef="{context}" unitRef="{unit}"'
                f' decimals="0">{value}</ix:nonFraction></td></tr>'
            )
    contexts = "\n".join(
        _PK08_TESTCO_CONTEXTS[context_id]
        for context_id in ("c-i", "c-fy", "c-ax")
        if any(context == context_id for _q, context, _v, _u in facts)
    )
    paragraphs = [
        "<p>Note 12 – Commitments and Contingencies. The Company has entered "
        "into certain unconditional purchase obligations.</p>",
        f"<p>{contingencies_prose}</p>",
        "<p>Note 13 – Subsequent Events. None.</p>",
    ]
    if item3:
        paragraphs.append(f"<p>{_PK08_ITEM3_BODY}</p>")
        paragraphs.append("<p>Item 4. Mine Safety Disclosures Not applicable.</p>")
    template = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml"'
        ' xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"'
        ' xmlns:xbrli="http://www.xbrl.org/2003/instance"'
        ' xmlns:xbrldi="http://xbrl.org/2006/xbrldi"'
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:iso4217="http://www.xbrl.org/2003/iso4217"'
        ' xmlns:test="http://www.testco.com/2025"'
        ' xmlns:us-gaap="http://fasb.org/us-gaap/2025">\n'
        "<head><title>TESTCO filing</title></head>\n<body>\n"
        '<div style="display:none"><ix:header><ix:resources>\n'
        f"{contexts}\n"
        '<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure>'
        "</xbrli:unit>\n</ix:resources></ix:header></div>\n"
        + "\n".join(paragraphs)
        + f'\n<table>\n{chr(10).join(rows)}\n</table>\n</body></html>\n'
    )
    return template.encode("utf-8")


def _pk08_testco_input(
    facts: tuple[tuple[str, str, str | None, str], ...] = _PK08_NIL_FACTS,
    *,
    form: str = "10-K",
    contingencies_prose: str = _PK08_CONTING_CLEAN,
    item3: bool = True,
    **overrides,
) -> PackInput:
    document = _pk08_testco_document(
        facts, contingencies_prose=contingencies_prose, item3=item3
    )
    manifest = {
        "entity_id": PK08_TESTCO_CIK,
        "cik": PK08_TESTCO_CIK,
        "legal_name": "TESTCO TWO CORP",
        "form": form,
        "period_of_report": "2025-12-31",
        "filing_date": "2026-02-15",
        "accession": "0000000002-26-000011",
        "primary_document": PK08_TESTCO_DOC,
        "source_accepted_at": "2026-02-15T16:00:00Z",
        "fixture_recorded_at": "2026-02-15T16:05:00Z",
        "members": [
            {
                "name": PK08_TESTCO_DOC,
                "state": "stored",
                "content_sha256": sha256(document).hexdigest(),
            }
        ],
    }
    defaults = dict(
        packages=(GoldenFilingPackage(manifest=manifest, members={PK08_TESTCO_DOC: document}),),
        entity=PK08_TESTCO_ENTITY,
        query=PK08_QUERY,
        issuer_sic="3571",
        sic_source="sec_submissions",
    )
    defaults.update(overrides)
    return PackInput(**defaults)


def _pk08_input(**overrides) -> PackInput:
    defaults = dict(
        packages=(load_golden_aapl_package(ROOT, accession=ACCESSION),),
        entity=ENTITY,
        query=PK08_QUERY,
        issuer_sic="3571",
        sic_source="sec_submissions",
    )
    defaults.update(overrides)
    return PackInput(**defaults)


@pytest.fixture(scope="module")
def pk08_result() -> dict:
    return produce_pack("PK08", _pk08_input())


# 51.1 §TESTS 1: nil facts reach the ledger -------------------------------------


def test_pk08_nil_facts_reach_the_ledger(ledger) -> None:
    # The converter keeps nil ix:nonFraction facts as numeric occurrences
    # with is_nil and no parsed value: no DEVIATION, no skip.
    occurrences = [
        occurrence
        for occurrence in ledger.events
        if occurrence.concept_qname == _PK08_CNC
    ]
    assert len(occurrences) == 2
    assert all(occurrence.is_nil for occurrence in occurrences)
    assert all(occurrence.parsed_value is None for occurrence in occurrences)
    by_instant = {
        str(occurrence.context.instant): occurrence.occurrence_id
        for occurrence in occurrences
    }
    assert by_instant == PK08_AAPL_NIL_IDS


def test_pk08_axis_members_exist_only_outside_the_primary_period(ledger) -> None:
    # GAPS evidence: the axis is carried in the ledger, but only on facts
    # whose periods end before the primary period — the A.2 row is therefore
    # a typed absence on this fixture, not an untested negative.
    members: dict[str, set[str]] = {}
    for occurrence in ledger.events:
        for axis, member in occurrence.context.explicit_dimensions:
            if axis == _PK08_NATURE_AXIS:
                period = str(
                    occurrence.context.instant
                    or f"{occurrence.context.start}..{occurrence.context.end}"
                )
                members.setdefault(period, set()).add(str(member))
    assert members == {
        "2024-06-30..2024-09-28": {
            "{http://www.apple.com/20250927}"
            "UnfavorableInvestigationOutcomeEUStateAidRulesMember"
        },
        "2024-09-28": {
            "{http://www.apple.com/20250927}"
            "UnfavorableInvestigationOutcomeEUStateAidRulesMember"
        },
    }


# 51.2 §TESTS 2: the AAPL envelope ----------------------------------------------


def test_pk08_result_passes_contract_validator(pk08_result: dict) -> None:
    assert contract.validate_pack_result(pk08_result) == []


def test_pk08_aapl_rows_follow_catalogue_order(pk08_result: dict) -> None:
    catalogue = contract.load_pack_schema("PK08")
    assert [row["field_id"] for row in pk08_result["fields"]] == [
        item["field_id"] for item in catalogue["fields"]
    ]
    assert pk08_result["applicability"] == {
        "state": "applicable",
        "reason": "applicability_rule_satisfied",
        "rule_id": "pack.pk08.applicability/v1",
        "sic": "3571",
        "sic_source": "sec_submissions",
    }


def test_pk08_aapl_valued_rows(pk08_result: dict) -> None:
    bs_state = _row(pk08_result, "commitments_and_contingencies_bs_state")
    assert bs_state["quality_state"] == "valued"
    assert bs_state["non_value_state"] is None
    assert bs_state["text_value"] == "nil_disclosed"
    assert bs_state["value"] is None
    assert bs_state["evidence_kind"] == "xbrl_fact"
    assert bs_state["concept"] == _PK08_CNC
    assert bs_state["taxonomy"] == "us-gaap"
    # A.1 cites exactly the 2025-09-27 nil occurrence, never the prior year.
    assert bs_state["source_occurrence_ids"] == [PK08_AAPL_NIL_IDS["2025-09-27"]]
    assert bs_state["period"] == {"kind": "instant", "end": "2025-09-27"}
    assert bs_state["mapping_rule_id"] == (
        "PK08.commitments_and_contingencies_bs_state.nil_state/v1"
    )

    block = _row(pk08_result, "commitments_text_block")
    assert block["quality_state"] == "valued"
    assert block["evidence_kind"] == "text_span"
    assert block["text_value"].startswith(
        "Contingencies The Company is subject to various legal proceedings"
    )
    assert block["text_value"].endswith(
        "concerning loss contingencies for asserted legal and other claims."
    )
    assert len(block["text_value"]) == 462  # 512-char cap, sentence-trimmed

    item3 = _row(pk08_result, "legal_proceedings_item3")
    assert item3["quality_state"] == "valued"
    assert item3["evidence_kind"] == "text_span"
    assert item3["text_value"].startswith(
        "Digital Markets Act Investigations On March 25, 2024"
    )
    assert len(item3["text_value"]) == 439  # first 512 after the heading

    allegation = _row(pk08_result, "allegation_span")
    assert allegation["quality_state"] == "valued"
    assert allegation["evidence_kind"] == "text_span"
    assert allegation["text_value"] == PK08_AAPL_ALLEGATION

    procedural = _row(pk08_result, "procedural_status_span")
    assert procedural["quality_state"] == "valued"
    assert procedural["evidence_kind"] == "text_span"
    assert procedural["text_value"] == PK08_AAPL_PROCEDURAL

    for field_id in (
        "commitments_text_block",
        "legal_proceedings_item3",
        "allegation_span",
        "procedural_status_span",
    ):
        span = _row(pk08_result, field_id)["source_span"]
        assert span["document_id"] == "aapl-20250927.htm"
        assert span["end_offset"] > span["start_offset"]


def test_pk08_aapl_non_valued_rows(pk08_result: dict) -> None:
    for field_id, reason in PK08_AAPL_NON_VALUED.items():
        row = _row(pk08_result, field_id)
        assert row["quality_state"] == "missing", field_id
        assert row["non_value_state"] == "missing", field_id
        assert row["coverage_state"] == "unmapped", field_id
        assert row["reason"] == reason, field_id
        assert row["value"] is None and row["text_value"] is None, field_id
    # The fact-driven absences name their first alias; the enum absence is
    # the A.3 literal refusal (the not_material arm matched).
    assert (
        _row(pk08_result, "loss_contingency_accrual")["concept"] == _PK08_ACCRUAL
    )
    assert _row(pk08_result, "contingency_nature")["concept"] == _PK08_NATURE_AXIS
    assert any(
        "catalogue lacks literal 'not_material'" in line
        for line in pk08_result["limitations"]
    )


def test_pk08_aapl_checks(pk08_result: dict) -> None:
    catalogue = contract.load_pack_schema("PK08")
    assert [check["check_id"] for check in pk08_result["checks"]] == [
        item["check_id"] for item in catalogue["checks"]
    ]
    accrual_vs_range = _check(pk08_result, "accrual_vs_range")
    assert accrual_vs_range["status"] == "not_evaluable"
    assert accrual_vs_range["reason"] == "missing_dependency"
    assert _check(pk08_result, "nil_bs_vs_note") == {
        "check_id": "nil_bs_vs_note",
        "kind": "qualitative_presence",
        "status": "pass",
        "operands": [
            "commitments_and_contingencies_bs_state",
            "commitments_text_block",
        ],
        "tolerance": None,
        "evidence_field_ids": [
            "commitments_and_contingencies_bs_state",
            "commitments_text_block",
        ],
        "reason": None,
    }
    assert _check(pk08_result, "item3_vs_note")["status"] == "pass"
    assert _check(pk08_result, "item3_vs_note")["reason"] is None


def test_pk08_aapl_coverage_receipts_and_limitations(pk08_result: dict) -> None:
    # B.5: five valued rows — the nil state, both text blocks and both spans.
    assert pk08_result["coverage"] == {
        "valued_fields": 5,
        "missing_fields": 5,
        "unsupported_fields": 0,
        "not_evaluable_fields": 0,
        "not_applicable_fields": 0,
        "disclosure_coverage_state": "present",
    }
    assert (
        f"nil_fact_ids={PK08_AAPL_NIL_IDS['2025-09-27']}"
        in pk08_result["receipts"]
    )
    assert any(
        line.startswith("pk08.table_cell_reserved:")
        for line in pk08_result["limitations"]
    )
    # One line per non-valued row naming what was searched.
    for field_id in PK08_AAPL_NON_VALUED:
        assert any(
            line.startswith(f"pk08.{field_id}: ") for line in pk08_result["limitations"]
        ), field_id
    # No prose range on this fixture: the ruling never fires and its
    # limitation line stays absent.
    assert not any(
        "range_in_prose_only" in line for line in pk08_result["limitations"]
    )


# 51.3 §TESTS 3: the 10-Q probe ---------------------------------------------------


def test_pk08_quarterly_form_gates_item3() -> None:
    result = produce_pack("PK08", _pk08_testco_input(form="10-Q", item3=False))
    item3 = _row(result, "legal_proceedings_item3")
    assert item3["quality_state"] == "not_applicable"
    assert item3["reason"] == "form_outside_pack_forms"
    check = _check(result, "item3_vs_note")
    assert check["status"] == "not_applicable"
    assert check["reason"] == "form_outside_pack_forms"
    # Every other row still resolves or types its absence (K3K4 ruling).
    rows = {row["field_id"]: row for row in result["fields"]}
    assert result["applicability"]["state"] == "applicable"
    assert rows["commitments_and_contingencies_bs_state"]["text_value"] == (
        "nil_disclosed"
    )
    assert rows["commitments_text_block"]["quality_state"] == "valued"
    assert (
        rows["loss_contingency_accrual"]["reason"]
        == "missing_standard_fact:us-gaap:LossContingencyAccrualAtCarryingValue"
    )
    assert (
        rows["contingency_nature"]["reason"]
        == f"missing_standard_fact:{_PK08_NATURE_AXIS}"
    )
    for field_id in ("allegation_span", "procedural_status_span"):
        assert rows[field_id]["quality_state"] == "not_evaluable", field_id
        assert rows[field_id]["reason"] == "missing_dependency", field_id
        assert any(
            line.startswith(f"pk08.{field_id}: governing_section_not_supplied;")
            for line in result["limitations"]
        ), field_id
    assert contract.validate_pack_result(result) == []


def test_pk08_form_outside_pack_forms_types_the_whole_pack() -> None:
    result = produce_pack("PK08", _pk08_testco_input(form="8-K", item3=False))
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


# 51.4 §TESTS 4: the accrual-vs-range arithmetic ----------------------------------


def test_pk08_accrual_within_range_passes() -> None:
    facts = _PK08_NIL_FACTS + (
        (_PK08_ACCRUAL, "c-i", "150", "usd"),
        (_PK08_RANGE_LOW, "c-fy", "100", "usd"),
        (_PK08_RANGE_HIGH, "c-fy", "200", "usd"),
    )
    result = produce_pack("PK08", _pk08_testco_input(facts))
    rows = {row["field_id"]: row for row in result["fields"]}
    assert rows["loss_contingency_accrual"]["value"] == "150"
    assert rows["loss_contingency_range_low"]["value"] == "100"
    assert rows["loss_contingency_range_high"]["value"] == "200"
    check = _check(result, "accrual_vs_range")
    assert check["status"] == "pass"
    assert check["reason"] is None
    assert _check(result, "nil_bs_vs_note")["status"] == "pass"
    assert contract.validate_pack_result(result) == []


def test_pk08_accrual_outside_range_fails() -> None:
    facts = _PK08_NIL_FACTS + (
        (_PK08_ACCRUAL, "c-i", "250", "usd"),
        (_PK08_RANGE_LOW, "c-fy", "100", "usd"),
        (_PK08_RANGE_HIGH, "c-fy", "200", "usd"),
    )
    result = produce_pack("PK08", _pk08_testco_input(facts))
    check = _check(result, "accrual_vs_range")
    assert check["status"] == "fail"
    assert check["reason"] is None
    assert contract.validate_pack_result(result) == []


def test_pk08_accrual_vs_range_missing_high_is_not_evaluable() -> None:
    facts = _PK08_NIL_FACTS + (
        (_PK08_ACCRUAL, "c-i", "150", "usd"),
        (_PK08_RANGE_LOW, "c-fy", "100", "usd"),
    )
    result = produce_pack("PK08", _pk08_testco_input(facts))
    check = _check(result, "accrual_vs_range")
    assert check["status"] == "not_evaluable"
    assert check["reason"] == "missing_dependency"
    assert contract.validate_pack_result(result) == []


# 51.5 §TESTS 5: the prose-only range ---------------------------------------------


def test_pk08_range_in_prose_only_is_never_valued() -> None:
    result = produce_pack(
        "PK08",
        _pk08_testco_input(contingencies_prose=_PK08_CONTING_RANGE),
    )
    rows = {row["field_id"]: row for row in result["fields"]}
    for field_id in ("loss_contingency_range_low", "loss_contingency_range_high"):
        row = rows[field_id]
        assert row["quality_state"] == "missing", field_id
        assert row["reason"] == "numeric_value_in_narrative_only", field_id
        assert row["value"] is None, field_id
    # The disclosed arm's literal IS in the catalogue: the enum values.
    disclosed = rows["loss_contingency_range_disclosed"]
    assert disclosed["quality_state"] == "valued"
    assert disclosed["text_value"] == "disclosed_range"
    # The accrual is a plain ledger absence — the prose rule never touches it.
    assert rows["loss_contingency_accrual"]["reason"] == (
        "missing_standard_fact:us-gaap:LossContingencyAccrualAtCarryingValue"
    )
    assert any(
        line.startswith("pk08.range_in_prose_only:")
        for line in result["limitations"]
    )
    assert _check(result, "accrual_vs_range")["status"] == "not_evaluable"
    assert contract.validate_pack_result(result) == []


# 51.5b range-pattern revision v2 (F1/F2 review): the reviewer's inputs ------


def test_pk08_prose_range_full_digit_amount() -> None:
    # F1: the full-digit dollar form retypes the range rows exactly as the
    # "$10 million" form always has (the C2 ruling is form-independent).
    result = produce_pack(
        "PK08",
        _pk08_testco_input(contingencies_prose=_PK08_CONTING_RANGE_FULL_DIGIT),
    )
    rows = {row["field_id"]: row for row in result["fields"]}
    for field_id in ("loss_contingency_range_low", "loss_contingency_range_high"):
        row = rows[field_id]
        assert row["quality_state"] == "missing", field_id
        assert row["reason"] == "numeric_value_in_narrative_only", field_id
        assert row["value"] is None, field_id
    # The disclosed arm's literal IS in the catalogue: the enum values.
    disclosed = rows["loss_contingency_range_disclosed"]
    assert disclosed["quality_state"] == "valued"
    assert disclosed["text_value"] == "disclosed_range"
    # The accrual is a plain ledger absence — the prose rule never touches it.
    assert rows["loss_contingency_accrual"]["reason"] == (
        "missing_standard_fact:us-gaap:LossContingencyAccrualAtCarryingValue"
    )
    assert any(
        line.startswith("pk08.range_in_prose_only:")
        for line in result["limitations"]
    )
    assert _check(result, "accrual_vs_range")["status"] == "not_evaluable"
    assert contract.validate_pack_result(result) == []


def test_pk08_not_estimable_adverb_after_be() -> None:
    # F2 input A: "cannot be reasonably estimated" values not_estimable —
    # the adverb-after-"be" order the v1 arm missed typed this row
    # narrative_span_not_located.
    result = produce_pack(
        "PK08",
        _pk08_testco_input(
            contingencies_prose=_PK08_CONTING_NOT_ESTIMABLE_AFTER_BE
        ),
    )
    disclosed = _row(result, "loss_contingency_range_disclosed")
    assert disclosed["quality_state"] == "valued"
    assert disclosed["non_value_state"] is None
    assert disclosed["text_value"] == "not_estimable"
    assert disclosed["value"] is None
    assert disclosed["evidence_kind"] == "text_span"
    assert disclosed["reason"] is None
    span = disclosed["source_span"]
    assert span["document_id"] == PK08_TESTCO_DOC
    assert span["end_offset"] > span["start_offset"]
    # F3 (second review): the v1 shadow copy is gone — the live digest is the
    # provenance, so no revision limitation line exists.
    assert not any(
        "range_pattern_revision" in line for line in result["limitations"]
    )
    assert contract.validate_pack_result(result) == []


def test_pk08_not_estimable_no_be_form() -> None:
    # F2: the no-"be" phrasing ("cannot reasonably estimate") values the
    # same declared literal as input A.
    result = produce_pack(
        "PK08",
        _pk08_testco_input(
            contingencies_prose=_PK08_CONTING_NOT_ESTIMABLE_NO_BE
        ),
    )
    disclosed = _row(result, "loss_contingency_range_disclosed")
    assert disclosed["quality_state"] == "valued"
    assert disclosed["non_value_state"] is None
    assert disclosed["text_value"] == "not_estimable"
    assert disclosed["value"] is None
    assert disclosed["evidence_kind"] == "text_span"
    assert disclosed["reason"] is None
    span = disclosed["source_span"]
    assert span["document_id"] == PK08_TESTCO_DOC
    assert span["end_offset"] > span["start_offset"]
    # F3 (second review): the v1 shadow copy is gone — the live digest is the
    # provenance, so no revision limitation line exists.
    assert not any(
        "range_pattern_revision" in line for line in result["limitations"]
    )
    assert contract.validate_pack_result(result) == []


def test_pk08_not_estimable_governs_over_not_material() -> None:
    # F2 input B: "no material" earlier in the sentence must not oust the
    # governing estimate clause — arms resolve by RANGE_ARM_PRIORITY, not
    # first-match-by-position, so the A.3 not_material refusal never fires.
    result = produce_pack(
        "PK08",
        _pk08_testco_input(
            contingencies_prose=_PK08_CONTING_NOT_ESTIMABLE_OVER_MATERIAL
        ),
    )
    disclosed = _row(result, "loss_contingency_range_disclosed")
    assert disclosed["quality_state"] == "valued"
    assert disclosed["text_value"] == "not_estimable"
    assert disclosed["value"] is None
    assert not any(
        "catalogue lacks literal 'not_material'" in line
        for line in result["limitations"]
    )
    # F3 (second review): the v1 shadow copy is gone — the live digest is the
    # provenance, so no revision limitation line exists.
    assert not any(
        "range_pattern_revision" in line for line in result["limitations"]
    )
    assert contract.validate_pack_result(result) == []


def test_pk08_prose_amount_requires_digits() -> None:
    # F1 negative: "$ reasonably possible" is not a dollar amount — no
    # prose-only retype; the range rows stay plain ledger absences.
    result = produce_pack(
        "PK08",
        _pk08_testco_input(contingencies_prose=_PK08_CONTING_BARE_DOLLAR),
    )
    rows = {row["field_id"]: row for row in result["fields"]}
    for field_id, alias in (
        ("loss_contingency_range_low", _PK08_RANGE_LOW),
        ("loss_contingency_range_high", _PK08_RANGE_HIGH),
    ):
        row = rows[field_id]
        assert row["quality_state"] == "missing", field_id
        assert row["reason"] == f"missing_standard_fact:{alias}", field_id
        assert row["value"] is None, field_id
    disclosed = rows["loss_contingency_range_disclosed"]
    assert disclosed["quality_state"] == "missing"
    assert disclosed["reason"] == "missing_dependency"
    assert not any(
        "range_in_prose_only" in line for line in result["limitations"]
    )
    assert contract.validate_pack_result(result) == []


# 51.5c second repair (review F2/F3): complete not_estimable forms, disclosed
# precedence, and honest live-pattern provenance --------------------------------


def _pk08_span_text(pack_input: PackInput, span: dict) -> str:
    """The raw-document bytes one row's ``source_span`` offsets address."""
    document = pack_input.packages[0].members[span["document_id"]]
    return document[span["start_offset"] : span["end_offset"]].decode("utf-8")


def test_pk08_not_estimable_not_possible_form() -> None:
    # F2 sentence A: "it is not possible to estimate the amount or range of
    # loss" values not_estimable — the first repair's arm still typed this
    # sentence missing/missing_dependency.
    pack_input = _pk08_testco_input(
        contingencies_prose=_PK08_CONTING_NOT_ESTIMABLE_NOT_POSSIBLE
    )
    result = produce_pack("PK08", pack_input)
    disclosed = _row(result, "loss_contingency_range_disclosed")
    assert disclosed["quality_state"] == "valued"
    assert disclosed["non_value_state"] is None
    assert disclosed["coverage_state"] == "source_trace_complete"
    assert disclosed["text_value"] == "not_estimable"
    assert disclosed["value"] is None
    assert disclosed["evidence_kind"] == "text_span"
    assert disclosed["reason"] is None
    span = disclosed["source_span"]
    assert span["document_id"] == PK08_TESTCO_DOC
    assert span["end_offset"] > span["start_offset"]
    assert _pk08_span_text(pack_input, span) == "is not possible to estimate"
    assert contract.validate_pack_result(result) == []


def test_pk08_not_estimable_cannot_be_made_form() -> None:
    # F2 sentence B: "an estimate of the possible loss cannot be made" values
    # not_estimable — same typed-missing miss as sentence A.
    pack_input = _pk08_testco_input(
        contingencies_prose=_PK08_CONTING_NOT_ESTIMABLE_CANNOT_BE_MADE
    )
    result = produce_pack("PK08", pack_input)
    disclosed = _row(result, "loss_contingency_range_disclosed")
    assert disclosed["quality_state"] == "valued"
    assert disclosed["non_value_state"] is None
    assert disclosed["coverage_state"] == "source_trace_complete"
    assert disclosed["text_value"] == "not_estimable"
    assert disclosed["value"] is None
    assert disclosed["evidence_kind"] == "text_span"
    assert disclosed["reason"] is None
    span = disclosed["source_span"]
    assert span["document_id"] == PK08_TESTCO_DOC
    assert span["end_offset"] > span["start_offset"]
    assert _pk08_span_text(pack_input, span) == (
        "estimate of the possible loss cannot be made"
    )
    assert contract.validate_pack_result(result) == []


def test_pk08_disclosed_governs_over_not_estimable() -> None:
    # F2 precedence: a span carrying a dollar range AND "cannot be reasonably
    # estimated" resolves disclosed_range in both orders — the arms evaluate
    # by RANGE_ARM_PRIORITY over the whole span, never first-match-by-position.
    for prose in (
        _PK08_CONTING_DISCLOSED_THEN_NOT_ESTIMABLE,
        _PK08_CONTING_NOT_ESTIMABLE_THEN_DISCLOSED,
    ):
        pack_input = _pk08_testco_input(contingencies_prose=prose)
        result = produce_pack("PK08", pack_input)
        disclosed = _row(result, "loss_contingency_range_disclosed")
        assert disclosed["quality_state"] == "valued", prose
        assert disclosed["non_value_state"] is None, prose
        assert disclosed["text_value"] == "disclosed_range", prose
        assert disclosed["value"] is None, prose
        assert disclosed["reason"] is None, prose
        span = disclosed["source_span"]
        assert span["end_offset"] > span["start_offset"], prose
        assert _pk08_span_text(pack_input, span) == (
            "range of reasonably possible loss"
        ), prose
        assert contract.validate_pack_result(result) == []


def test_pk08_range_digest_is_the_live_pattern() -> None:
    # F3 seat ruling: the digest of a text-span mapping is the digest of the
    # bytes that performed the match. The produced row's mapping_rule_digest
    # must equal the digest base.py derives for the live
    # RANGE_DISCLOSED_PATTERN — computed here through the same helper the
    # producer uses, so a shadow byte-string reintroduced as the digest
    # source fails this equality.
    result = produce_pack(
        "PK08",
        _pk08_testco_input(
            contingencies_prose=_PK08_CONTING_NOT_ESTIMABLE_AFTER_BE
        ),
    )
    disclosed = _row(result, "loss_contingency_range_disclosed")
    assert disclosed["quality_state"] == "valued"
    expected = pack_base._text_span_digest(
        pack_base.TextSpanMapping(
            section=pk08_contingencies.NOTE_CC,
            pattern=pk08_contingencies.RANGE_DISCLOSED_PATTERN,
            kind="enum",
        )
    )
    assert disclosed["mapping_rule_digest"] == expected
    assert (
        pk08_contingencies._RANGE_DISCLOSED_MAPPING.pattern
        == pk08_contingencies.RANGE_DISCLOSED_PATTERN
    )
    assert not hasattr(pk08_contingencies, "RANGE_DISCLOSED_PATTERN_V1")
    assert contract.validate_pack_result(result) == []


# 51.6 A.2 positive path: the axis member inside the primary period ---------------


def test_pk08_axis_member_inside_primary_period_values_the_row() -> None:
    facts = _PK08_NIL_FACTS + ((_PK08_ACCRUAL, "c-ax", "40", "usd"),)
    result = produce_pack("PK08", _pk08_testco_input(facts))
    row = _row(result, "contingency_nature")
    assert row["quality_state"] == "valued"
    assert row["text_value"] == "{http://www.testco.com/2025}LitigationMember"
    assert row["value"] is None  # axis_member is a non-numeric row type
    assert row["dimensions"] == [
        {
            "axis": _PK08_NATURE_AXIS,
            "member": "{http://www.testco.com/2025}LitigationMember",
        }
    ]
    assert row["concept"] == _PK08_NATURE_AXIS
    assert row["evidence_kind"] == "xbrl_fact"
    assert row["source_occurrence_ids"]
    assert row["mapping_rule_id"] == "PK08.contingency_nature.axis_member/v1"
    # The dimensioned accrual never leaks into the undimensioned accrual row.
    accrual = _row(result, "loss_contingency_accrual")
    assert accrual["quality_state"] == "missing"
    assert contract.validate_pack_result(result) == []


# 51.7 §TESTS 6: BASE invariance, registry, determinism, CLI ----------------------


@pytest.mark.parametrize("pack_id", sorted(PK08_BASE_PACK_ENVELOPE_SHA256))
def test_base_pack_envelopes_unchanged_by_pk08_edits(pack_id: str) -> None:
    # §TESTS 6: every pack registered at BASE keeps its AAPL envelope
    # byte-identical to BASE after PK08 registers.
    result = produce_pack(pack_id, _pk08_input())
    payload = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert (
        sha256(payload.encode("utf-8")).hexdigest()
        == PK08_BASE_PACK_ENVELOPE_SHA256[pack_id]
    )


def test_registered_pack_ids_is_base_set_plus_pk08() -> None:
    assert registered_pack_ids() == (
        "PK01",
        "PK02",
        "PK03",
        "PK04",
        "PK05",
        "PK06",
        "PK07",
        "PK08",
        "PK09",
        "PK10",
        "PK11",
        "PK12",
    )


def test_pk08_production_is_deterministic() -> None:
    first = produce_pack("PK08", _pk08_input())
    second = produce_pack("PK08", _pk08_input())
    payload_first = json.dumps(
        first, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    payload_second = json.dumps(
        second, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert payload_first == payload_second
    assert (
        sha256(payload_first.encode("utf-8")).hexdigest()
        == PK08_AAPL_ENVELOPE_SHA256
    )


def test_pk08_cli_writes_valid_envelope(tmp_path: Path) -> None:
    entity_file = tmp_path / "entity.json"
    query_file = tmp_path / "query.json"
    out_file = tmp_path / "pk08.json"
    entity_file.write_text(json.dumps(ENTITY), encoding="utf-8")
    query_file.write_text(json.dumps(PK08_QUERY), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "fif_specialist_packs.py"),
            "--pack",
            "PK08",
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
    assert envelope["coverage"]["valued_fields"] == 5
