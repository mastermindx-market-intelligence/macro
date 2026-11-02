"""Registry-only metric qualification: applicability, period basis, denominators."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from pathlib import Path

import pytest
import yaml

from engine.fundamental_forensics.models import canonical_json
from engine.fundamental_forensics.metric_registry import (
    ALLOWED_UNITS,
    ApplicabilityPolicy,
    DEFAULT_PERIOD_CALENDAR,
    ISSUER_CLASSES,
    load_core_metric_registry,
    load_metric_registry,
    metric_registry_from_dicts,
    qualify_metric,
)


ROOT = Path(__file__).resolve().parent.parent
METRICS_ROOT = ROOT / "config" / "fundamental_forensics" / "metrics" / "v1"
QUALIFICATION_ROOT = (
    ROOT / "tests" / "fixtures" / "fundamental_forensics" / "metric_registry_qualification"
)
PINNED_RECORDED_AT = "2026-08-02T00:00:00Z"
# Captured from load_core_metric_registry().governance_bundle_at(PINNED_RECORDED_AT)
# and the registry lane digest attributes.  File-level digests repinned for the
# mapping pack 1.1.0 / metric catalog 1.1.0 append (seat rulings 2026-10-19
# R-ALIAS, R-INTANG, D1; rule clocks 2026-10-21T00:00:00Z per R-9761-CLK) and
# the formula pack 1.1.0 not_presented_policy append (R-FORMULA F3, same
# clock); the pre-R bundle content_id is deliberately unchanged.
PINNED_CATALOG_CONTENT_SHA256 = "4425bdb441ac4380a66ceb34d4c72ef136a89966eefc1fd6954446e296e55461"
PINNED_MAPPING_PACK_CONTENT_SHA256 = "61e40289c028b8495eaf47045cface91dafae7ce7318bbf50ddfed7d6511daa4"
PINNED_FORMULA_PACK_CONTENT_SHA256 = "2d9994bf8365a95b370e46ea93b7568bb77309720c463bf56678d18bd84e203b"
PINNED_GOVERNANCE_BUNDLE_CONTENT_ID = "e724b79842bd978110b389b2997368a05958ee451538193f6071fc2451e52d29"


def _raw() -> tuple[dict, dict, dict]:
    return tuple(
        yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in (
            METRICS_ROOT / "metric_catalog.yaml",
            METRICS_ROOT / "mappings" / "core.yaml",
            METRICS_ROOT / "formulas" / "core.yaml",
        )
    )


def _pin_digest(raw: dict) -> None:
    content = dict(raw)
    content.pop("content_sha256", None)
    raw["content_sha256"] = hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()


def _pin_all(raw: tuple[dict, dict, dict]) -> None:
    for document in raw:
        _pin_digest(document)


def _registry(raw: tuple[dict, dict, dict]) -> object:
    _pin_all(raw)
    return metric_registry_from_dicts(*raw)


def _metric(catalog: dict, metric_id: str) -> dict:
    return next(item for item in catalog["metrics"] if item["metric_id"] == metric_id)


def _formula(formulas: dict, metric_id: str) -> dict:
    return next(item for item in formulas["formulas"] if item["metric_id"] == metric_id)


def _qualification_registry():
    return load_metric_registry(
        QUALIFICATION_ROOT / "metric_catalog.yaml",
        QUALIFICATION_ROOT / "mappings.yaml",
        QUALIFICATION_ROOT / "formulas.yaml",
        enforce_core_v1_inventory=False,
    )


def _bank_excluded(contract):
    return replace(
        contract,
        applicability=ApplicabilityPolicy(
            issuer_class_basis="sic",
            applicable_classes=(),
            excluded_classes=("bank",),
            basis_note="banks report interest-based P&L; no cost-of-revenue concept",
        ),
    )


def test_s1_a06_01_non_usd_refused_shipped_units_stay_inside_governed_universe() -> None:
    registry = load_core_metric_registry(ROOT)
    assert ALLOWED_UNITS == frozenset({"USD", "shares", "USD/shares", "ratio"})
    for contract in registry.contracts:
        assert set(contract.units).issubset(ALLOWED_UNITS)
        assert "EUR" not in contract.units
    revenue = registry.metric("revenue")
    result = qualify_metric(revenue, revenue.formula, "industrial", {})
    assert result.state == "applicable"
    assert result.reason == ""


def test_s1_a06_02_shares_vs_usd_shares_contract_units_remain_distinct() -> None:
    registry = load_core_metric_registry(ROOT)
    shares = registry.metric("common_shares_outstanding")
    basic_eps = registry.metric("basic_earnings_per_share")
    diluted_eps = registry.metric("diluted_earnings_per_share")
    assert shares.units == ("shares",)
    assert basic_eps.units == ("USD/shares",)
    assert diluted_eps.units == ("USD/shares",)
    assert shares.units != basic_eps.units


def test_s1_a06_03_fiscal_basis_label_on_shipped_and_qualification_fixture() -> None:
    shipped = load_core_metric_registry(ROOT)
    for contract in shipped.contracts:
        assert contract.period_basis.calendar == "fiscal"
        assert contract.period_basis.calendar == DEFAULT_PERIOD_CALENDAR
    fixture = _qualification_registry()
    assert fixture.metric("revenue").period_basis.calendar == "fiscal"
    assert fixture.metric("gross_margin").period_basis.calendar == "fiscal"


def test_s1_a07_01_unknown_issuer_class_is_not_treated_as_applicable() -> None:
    registry = load_core_metric_registry(ROOT)
    margin = _bank_excluded(registry.metric("gross_margin"))
    unknown = qualify_metric(margin, margin.formula, None, {})
    assert unknown.state == "not_evaluable"
    assert unknown.reason == "issuer_class_unknown"
    industrial = qualify_metric(margin, margin.formula, "industrial", {"revenue": Decimal("1")})
    assert industrial.state == "applicable"


def test_s1_a08_01_negative_denominator_not_applicable() -> None:
    fixture = _qualification_registry()
    margin = fixture.metric("gross_margin")
    result = qualify_metric(
        margin,
        margin.formula,
        "industrial",
        {"revenue": Decimal("-10")},
    )
    assert result.state == "not_applicable"
    assert result.reason == "denominator_not_positive:revenue"
    assert result.reason != "0"
    assert result.reason != ""


def test_s1_a08_02_zero_and_missing_denominators() -> None:
    fixture = _qualification_registry()
    margin = fixture.metric("gross_margin")
    zero = qualify_metric(
        margin,
        margin.formula,
        "industrial",
        {"revenue": Decimal("0")},
    )
    assert zero.state == "not_applicable"
    assert zero.reason == "denominator_not_positive:revenue"
    missing = qualify_metric(
        margin,
        margin.formula,
        "industrial",
        {"revenue": None},
    )
    assert missing.state == "not_evaluable"
    assert missing.reason == "denominator_missing:revenue"
    absent = qualify_metric(margin, margin.formula, "industrial", {})
    assert absent.state == "not_evaluable"
    assert absent.reason == "denominator_missing:revenue"
    positive = qualify_metric(
        margin,
        margin.formula,
        "industrial",
        {"revenue": Decimal("100")},
    )
    assert positive.state == "applicable"
    assert positive.reason == ""


def test_s1_a53_01_revision_append_cutoff_digest_unchanged() -> None:
    registry = load_core_metric_registry(ROOT)
    baseline = registry.governance_bundle_at(PINNED_RECORDED_AT)
    assert baseline.content_id == PINNED_GOVERNANCE_BUNDLE_CONTENT_ID
    revenue = registry.metric("revenue")
    future_mapping = replace(
        revenue.mappings[0],
        rule=replace(
            revenue.mappings[0].rule,
            rule_id="mapping.revenue.future_extension/v1",
            available_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
        ),
    )
    extended = replace(
        registry,
        catalog_version="99.0.0",
        catalog_content_sha256="1" * 64,
        mapping_pack_version="99.0.0",
        mapping_pack_content_sha256="2" * 64,
        formula_pack_version="99.0.0",
        formula_pack_content_sha256="3" * 64,
        contracts=tuple(
            replace(contract, mappings=contract.mappings + (future_mapping,))
            if contract.metric_id == "revenue"
            else contract
            for contract in registry.contracts
        ),
    )
    projected = extended.governance_bundle_at(PINNED_RECORDED_AT)
    assert projected.content_id == baseline.content_id
    assert projected.to_dict() == baseline.to_dict()
    assert future_mapping.rule.available_at > baseline.recorded_at


def test_s1_a30_01_bank_not_applicable() -> None:
    fixture = _qualification_registry()
    margin = fixture.metric("gross_margin")
    bank = qualify_metric(
        margin,
        margin.formula,
        "bank",
        {"revenue": Decimal("100")},
    )
    assert bank.state == "not_applicable"
    assert bank.reason == "not_applicable_for_issuer_class"
    assert margin.applicability.basis_note.startswith("banks report interest-based P&L")
    industrial = qualify_metric(
        margin,
        margin.formula,
        "industrial",
        {"revenue": Decimal("100")},
    )
    assert industrial.state == "applicable"


def test_field_denominator_equals_class_policy_closure_for_every_issuer() -> None:
    """G0-b: the D0 field_denominator equals the shipped class-policy closure.

    Replaces the pre-G0b emptiness pin (every shipped applicability policy
    empty). For every coverage issuer and every metric in the D0
    field_denominator, the build path's derived class projection and the query
    path's direct-stage qualification must agree; the bank closure must be
    exactly the A30-ruled set; and every metric D0 still records under a
    ticker key must be confirmed by that issuer's class closure — so a
    ticker-keyed answer can no longer diverge from the class answer.
    """
    import json

    from engine.fundamental_forensics.detectors import issuer_class_for_sic
    from scripts.build_fundamental_forensics import _class_not_applicable_metric_ids

    registry = load_core_metric_registry(ROOT)
    for contract in registry.contracts:
        assert contract.applicability.issuer_class_basis == "sic"
        assert contract.period_basis.calendar == "fiscal"
        if contract.formula is not None:
            assert contract.formula.denominator_constraints == ()

    # The A30-ruled bank closure (Tier 1 D0-ratified + Tier 2 per R2, plus the
    # explicit inventory_to_revenue policy). capex, total_debt and
    # long_term_debt stay applicable; insurance is out of G scope and carries
    # no metric policy anywhere.
    expected_bank_closure = {
        "cost_of_revenue",
        "gross_profit",
        "gross_margin",
        "inventory_net",
        "free_cash_flow",
        "current_assets",
        "current_liabilities",
        "working_capital",
        "current_ratio",
        "operating_income_loss",
        "operating_expenses",
        "debt_to_equity",
        "net_debt",
        "cash_to_total_debt",
        "receivables_to_revenue",
        "inventory_to_revenue",
    }
    bank_closure = {
        contract.metric_id
        for contract in registry.contracts
        if qualify_metric(contract, None, "bank", {}).state != "applicable"
    }
    assert bank_closure == expected_bank_closure
    for metric_id in ("capital_expenditures", "total_debt", "long_term_debt"):
        assert qualify_metric(
            registry.metric(metric_id), None, "bank", {}
        ).state == "applicable", metric_id
    for contract in registry.contracts:
        assert "insurance" not in contract.applicability.excluded_classes
        assert "insurance" not in contract.applicability.applicable_classes

    # Build path (derived class projection, no ticker key) must equal the
    # query path (direct-stage qualification) for every D0 issuer.
    build_projection = _class_not_applicable_metric_ids(ROOT)
    contract_doc = json.loads(
        (ROOT / "config" / "fundamental_forensics" / "coverage" / "five_issuer_v1.json")
        .read_text(encoding="utf-8")
    )
    denominator = contract_doc["field_denominator"]
    metric_ids = set(denominator["metric_ids"])
    assert len(metric_ids) == 50
    recorded_not_applicable = denominator.get("not_applicable", {})
    for issuer in contract_doc["issuers"]:
        ticker = issuer["ticker"]
        issuer_class = issuer_class_for_sic(issuer["sic"])
        assert issuer["issuer_class"] == issuer_class, ticker
        query_closure = {
            metric_id
            for metric_id in metric_ids
            if qualify_metric(
                registry.metric(metric_id), None, issuer_class, {}
            ).state != "applicable"
        }
        build_excluded = metric_ids & build_projection.get(issuer_class, frozenset())
        assert build_excluded == query_closure, ticker
        # No ticker-keyed divergence: every metric D0 records for this ticker
        # is confirmed by the class closure, and for non-bank classes the
        # projection is empty so D0 records nothing.
        recorded = set(recorded_not_applicable.get(ticker, {}))
        assert recorded <= query_closure, ticker
        if issuer_class != "bank":
            assert recorded == set(), ticker
        # Tier-1 basis notes carry the D0-ratified A30 reason verbatim.
        for metric_id, reason in recorded_not_applicable.get(ticker, {}).items():
            assert registry.metric(metric_id).applicability.basis_note == reason, (
                ticker,
                metric_id,
            )


def test_shipped_registry_digests_match_pre_change_capture() -> None:
    registry = load_core_metric_registry(ROOT)
    bundle = registry.governance_bundle_at(PINNED_RECORDED_AT)
    assert registry.catalog_content_sha256 == PINNED_CATALOG_CONTENT_SHA256
    assert registry.mapping_pack_content_sha256 == PINNED_MAPPING_PACK_CONTENT_SHA256
    assert registry.formula_pack_content_sha256 == PINNED_FORMULA_PACK_CONTENT_SHA256
    assert bundle.content_id == PINNED_GOVERNANCE_BUNDLE_CONTENT_ID
    wire = bundle.to_dict()
    assert "applicability" not in wire["metrics"][0]
    assert "period_basis" not in wire["metrics"][0]
    assert "denominator_constraints" not in wire["formulas"][0]


def test_loader_rejects_unknown_issuer_class_name() -> None:
    catalog, mappings, formulas = deepcopy(_raw())
    _metric(catalog, "gross_margin")["applicability"] = {
        "issuer_class_basis": "sic",
        "applicable_classes": [],
        "excluded_classes": ["not_a_class"],
        "basis_note": "",
    }
    with pytest.raises(ValueError, match="unknown issuer class"):
        _registry((catalog, mappings, formulas))


def test_loader_rejects_overlapping_applicable_and_excluded_classes() -> None:
    catalog, mappings, formulas = deepcopy(_raw())
    _metric(catalog, "gross_margin")["applicability"] = {
        "issuer_class_basis": "sic",
        "applicable_classes": ["bank"],
        "excluded_classes": ["bank"],
        "basis_note": "",
    }
    with pytest.raises(ValueError, match="both applicable and excluded"):
        _registry((catalog, mappings, formulas))


def test_loader_rejects_unknown_denominator_input() -> None:
    catalog, mappings, formulas = deepcopy(_raw())
    _formula(formulas, "gross_margin")["denominator_constraints"] = {
        "require_positive": ["not_an_input"]
    }
    with pytest.raises(ValueError, match="unknown input"):
        _registry((catalog, mappings, formulas))


def test_qualification_fixture_loads_optional_yaml_keys() -> None:
    registry = _qualification_registry()
    revenue = registry.metric("revenue")
    margin = registry.metric("gross_margin")
    assert revenue.applicability.applicable_classes == ()
    assert revenue.applicability.excluded_classes == ()
    assert revenue.period_basis.calendar == "fiscal"
    assert margin.applicability.excluded_classes == ("bank",)
    assert margin.applicability.applicable_classes == ()
    assert margin.period_basis.calendar == "fiscal"
    assert margin.formula is not None
    assert margin.formula.denominator_constraints == ("revenue",)
    assert ISSUER_CLASSES == frozenset(
        {"industrial", "software", "bank", "insurance", "reit", "utility", "unknown"}
    )


def test_applicable_classes_non_empty_list_excludes_unlisted_issuers() -> None:
    registry = load_core_metric_registry(ROOT)
    restricted = replace(
        registry.metric("gross_margin"),
        applicability=ApplicabilityPolicy(
            issuer_class_basis="sic",
            applicable_classes=("industrial", "software"),
            excluded_classes=(),
            basis_note="",
        ),
    )
    software = qualify_metric(
        restricted, restricted.formula, "software", {"revenue": Decimal("1")}
    )
    insurance = qualify_metric(
        restricted, restricted.formula, "insurance", {"revenue": Decimal("1")}
    )
    assert software.state == "applicable"
    assert insurance.state == "not_applicable"
    assert insurance.reason == "not_applicable_for_issuer_class"
