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
# and the registry lane digest attributes at 5267c66846e7733bc1eb30edc1524daff51598ca
# before this lane's registry-field additions.
PINNED_CATALOG_CONTENT_SHA256 = "0271e126568f2a9cd6f29f4fe0a1d8d0e66ff757ec18223b6dc9bc6bb7d80bad"
PINNED_MAPPING_PACK_CONTENT_SHA256 = "70f2974db21a2a3f5d2c76cf6d976e521a48969ea46925d4f3740287b8e3dc29"
PINNED_FORMULA_PACK_CONTENT_SHA256 = "fdfca7fbaa4ef926232f771603146b2d9b44cdd5e74d43bb8e9bf47c6e0c54a8"
PINNED_GOVERNANCE_BUNDLE_CONTENT_ID = "bd71a7905f9d892f6d761346dd1ef2dc9df9fc75d94cf165e34983deed7fe0a1"


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


def test_default_policy_contract_loads_from_shipped_yaml() -> None:
    registry = load_core_metric_registry(ROOT)
    for contract in registry.contracts:
        assert contract.applicability.issuer_class_basis == "sic"
        assert contract.applicability.applicable_classes == ()
        assert contract.applicability.excluded_classes == ()
        assert contract.applicability.basis_note == ""
        assert contract.period_basis.calendar == "fiscal"
        if contract.formula is not None:
            assert contract.formula.denominator_constraints == ()
        result = qualify_metric(contract, contract.formula, None, {})
        assert result.state == "applicable"
        assert result.reason == ""


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
