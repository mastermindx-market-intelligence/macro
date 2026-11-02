"""Cyclical shared-contract review gate.

The live arm on main is the typed refusal: ``engine.theme_graph.curation_assertion``
is not on this tree. The strict xfail is the positive round-trip through that
owner's real module and becomes an unexpected pass only when the module is
importable and the pinned synthetic payload still validates.
"""

from __future__ import annotations

import ast
import importlib
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine.sector_intelligence.consumer_cyclical_projection import (
    project_economic_change,
)
from engine.sector_intelligence.consumer_cyclical_shared_contract import (
    SHARED_CONTRACT_MODULE,
    ConsumerCyclicalResearchRefusal,
    shared_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    REPO_ROOT
    / "engine"
    / "sector_intelligence"
    / "consumer_cyclical_shared_contract.py"
)
FIXTURE_PATH = (
    REPO_ROOT
    / "data"
    / "sector_intelligence"
    / "fixtures"
    / "consumer_cyclical_intelligence_read_model.v1.valid.json"
)

# Stamp of the synthetic payload below under the shared owner at
# refs/grok/pr/7870@52b741c5082 (curation_assertion.py blob b7e42fd8, the
# same blob as tip c46dbebb). Strict xfail: the suite goes red on an
# unexpected pass. A hash mismatch stays an expected failure.
PINNED_REVISION = "gmirca_63ffb5449d20456a8d2405cc16e66b37"


def _committed_synthetic_case() -> dict:
    """The committed fixture's case fields, not a hand-built PLNT accession."""
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {
        "subject": fixture["subject"],
        "comparison_basis": fixture["comparison_basis"],
        "facts": fixture["facts"],
        "generated_at": fixture["generated_at"],
        "source_records": fixture["source_records"],
    }


def _assigned_string_constant(tree: ast.AST, name: str) -> str | None:
    for node in getattr(tree, "body", ()):
        targets: list[ast.AST] = []
        value: ast.AST | None = None
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        else:
            continue
        for target in targets:
            if (
                isinstance(target, ast.Name)
                and target.id == name
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                return value.value
    return None


def _import_module_string_literals(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        label = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if label != "import_module":
            continue
        arg = node.args[0]
        assert isinstance(arg, ast.Constant) and isinstance(arg.value, str), (
            "import_module target must stay a string literal equal to SHARED_CONTRACT_MODULE"
        )
        found.append(arg.value)
    return found


def _static_imports(tree: ast.AST) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    return imported


def _install_contract(monkeypatch: pytest.MonkeyPatch) -> dict[str, SimpleNamespace]:
    """Patch once. A second setattr would call this same fake to resolve ``engine``."""
    holder: dict[str, SimpleNamespace] = {}

    def fake_import(name: str) -> SimpleNamespace:
        assert name == SHARED_CONTRACT_MODULE
        return holder["module"]

    monkeypatch.setattr(
        "engine.sector_intelligence.consumer_cyclical_shared_contract.importlib.import_module",
        fake_import,
    )
    return holder


def _synthetic_assertion() -> dict:
    """Smallest synthetic payload the pinned shared contract accepts unstamped.

    Names, URLs and measures are fixture text. No issuer accession is copied
    into this file. Checked against the owner module at refs/grok/pr/7870.
    """
    return {
        "schema": "theme_graph.curation_assertion.v1",
        "curation_revision": None,
        "review": {
            "disposition": "accepted",
            "reviewed_at": "2026-09-23T07:00:00Z",
            "reviewer": "synthetic-reviewer",
            "review_due_at": None,
        },
        "source": {
            "publisher": "Synthetic Fixture Press",
            "source_uri": "https://example.invalid/synthetic/cyclical-fixture",
            "locator": "synthetic paragraph",
            "published_at": None,
            "published_at_grain": "unknown",
            "observed_at": "2026-09-23T06:00:00Z",
            "retained_at": "2026-09-23T06:05:00Z",
            "retention_ref": "synthetic://fixture/cyclical-shared-contract",
            "native_digest": None,
        },
        "subject": {
            "company_node_id": "co:us:SYNTH_CYCLICAL_FIXTURE",
            "source_business_label": "Synthetic Cyclical Fixture",
            "source_product_label": "Synthetic Paid Unit",
            "source_platform_label": None,
            "configuration": None,
        },
        "object": {
            "source_product_label": "Synthetic Paid Unit",
            "configuration": "synthetic fixture configuration",
        },
        "predicate": "REPORTED_OPERATING_MEASURE",
        "statement_mode": "REPORTED_FACT",
        "scope": {
            "canonical_theme_id": "theme:synthetic-consumer-cyclical",
            "application": "synthetic_fixture",
            "technology_facet": None,
            "region": None,
            "period": None,
            "denominator": None,
        },
        "observation": {
            "value": 2,
            "value_high": None,
            "unit": "unit",
            "quantity_basis": "per_unit",
            "gross_net_basis": None,
            "stock_flow": None,
            "estimate_status": "reported",
            "precision": "integer",
        },
        "temporal": {"business_valid_from": None, "business_valid_to": None},
        "limitations": {
            "establishes": ["a synthetic operating measure in a fixture"],
            "does_not_establish": ["a market rank", "a position size", "an entry"],
            "coverage": "single synthetic fixture",
            "source_dependence": "fixture_statement",
            "expiry_trigger": "fixture retired",
        },
        "correction": {"predecessor_revision": None, "reason": None},
        "authority": {
            "can_rank": False,
            "can_gate": False,
            "can_size": False,
            "can_originate": False,
            "can_open_entry": False,
        },
    }


def test_absent_shared_contract_raises_shared_contract_unavailable() -> None:
    with pytest.raises(ConsumerCyclicalResearchRefusal) as raised:
        shared_contract()
    assert raised.value.code == "shared_contract_unavailable"


def test_present_contract_returns_validate_assertion(monkeypatch: pytest.MonkeyPatch) -> None:
    def validate_assertion(payload: dict) -> dict:
        return payload

    def curation_revision(payload: dict) -> str:
        del payload
        return "gmirca_" + "ab" * 16

    holder = _install_contract(monkeypatch)
    holder["module"] = SimpleNamespace(
        validate_assertion=validate_assertion,
        curation_revision=curation_revision,
    )
    assert shared_contract() is validate_assertion

    incomplete = (
        SimpleNamespace(validate_assertion=validate_assertion),
        SimpleNamespace(curation_revision=curation_revision),
        SimpleNamespace(),
        SimpleNamespace(validate_assertion="not-callable", curation_revision=curation_revision),
        SimpleNamespace(validate_assertion=validate_assertion, curation_revision="not-callable"),
    )
    for module in incomplete:
        holder["module"] = module
        with pytest.raises(ConsumerCyclicalResearchRefusal) as raised:
            shared_contract()
        assert raised.value.code == "shared_contract_unavailable"


def test_import_is_a_string_literal_and_names_no_semiconductor_module() -> None:
    module_tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    assigned = _assigned_string_constant(module_tree, "SHARED_CONTRACT_MODULE")
    assert assigned == SHARED_CONTRACT_MODULE
    assert _import_module_string_literals(module_tree) == [assigned]
    imported = _static_imports(module_tree)
    assert not any(
        name == "engine.theme_graph" or name.startswith("engine.theme_graph.")
        for name in imported
    ), imported
    assert not any(
        name.startswith("engine.market_ontology.semiconductor_theme_research")
        or name.startswith("engine.market_ontology.theme_research_binding")
        or name == "engine.theme_graph.store"
        for name in imported
    ), imported

    test_tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    assert _import_module_string_literals(test_tree) == [assigned]
    test_imported = _static_imports(test_tree)
    assert not any(
        name == "engine.theme_graph" or name.startswith("engine.theme_graph.")
        for name in test_imported
    ), test_imported
    assert not any(
        name.startswith("engine.market_ontology.semiconductor_theme_research")
        for name in test_imported
    ), test_imported


def test_projection_document_is_unchanged() -> None:
    before = project_economic_change(_committed_synthetic_case())
    with pytest.raises(ConsumerCyclicalResearchRefusal) as raised:
        shared_contract()
    assert raised.value.code == "shared_contract_unavailable"
    after = project_economic_change(_committed_synthetic_case())
    assert after == before
    assert before["contract_id"] == "consumer_cyclical_intelligence_read_model.v1"
    emitted = {row["key"]: row["value_text"] for row in before["results"]}
    assert emitted["advertising_net_change"] == "-4"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "shared theme_graph.curation_assertion.v1 is not on main; "
        "positive round-trip pinned to refs/grok/pr/7870@52b741c5082; "
        "strict xfail goes red on an unexpected pass"
    ),
)
def test_shared_assertion_roundtrip_through_pinned_contract() -> None:
    module = importlib.import_module("engine.theme_graph.curation_assertion")
    assert shared_contract() is module.validate_assertion
    payload = _synthetic_assertion()
    validated = module.validate_assertion(payload, allow_unstamped=True)
    revision = module.curation_revision(validated)
    assert revision == PINNED_REVISION
    assert re.fullmatch(r"gmirca_[0-9a-f]{32}", revision)
    decoded = module.decode_assertion(module.encode_assertion(payload))
    assert decoded is not None
    assert decoded["curation_revision"] == revision
    assert module.source_ref_for(validated) == (
        f"gmi-curation://{payload['scope']['canonical_theme_id']}/{revision}"
    )
