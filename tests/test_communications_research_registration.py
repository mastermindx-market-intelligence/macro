"""Shared-shell adapter for the communications company-slot composer.

The shell modules are absent until #7870 merges. Every arm below is a real
assertion on this base and on a base where those modules exist. Nothing here
feeds a claim into validate_assertion or imports the semiconductor composer.
"""
import ast
import dataclasses
import importlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest

from engine.market_ontology.communications_research import (
    _ROSTER,
    compose_communications_payload,
)
from engine.market_ontology.communications_research_registration import (
    COMMUNICATIONS_REGISTRATION_FACTS,
    SHARED_CONTRACT_MODULE,
    SHARED_REGISTRY_MODULE,
    SHARED_SHELL_MODULE,
    VERTICAL_REGISTRATION_HELD_COMPANY_PROFILE,
    CommunicationsRegistrationRefusal,
    _VERTICAL_REGISTRATION_FIELDS,
    build_query,
    load_bundle,
    registration_entry_or_refusal,
    shared_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "engine/market_ontology/communications_research_registration.py"
SHELL_FIELDS = (
    "anchor_theme_id",
    "slice_keys",
    "view_keys",
    "schema_id",
    "evidence_schema_id",
    "definition_version",
    "compose",
    "select_evidence",
    "load_bundle",
    "build_query",
    "title_en",
    "title_zh",
    "note_en",
    "note_zh",
)
SOURCES = (
    "engine/market_ontology/communications_research_registration.py",
    "tests/test_communications_research_registration.py",
)


def _theme_registrable():
    return dataclasses.replace(
        COMMUNICATIONS_REGISTRATION_FACTS,
        anchor_theme_id="communications_company",
        slice_keys=("company_slot",),
    )


def _import_module_literals(tree):
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        label = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if label != "import_module":
            continue
        arg = node.args[0]
        assert isinstance(arg, ast.Constant) and isinstance(arg.value, str), (
            "import_module target must stay a string literal equal to a module constant"
        )
        found.append(arg.value)
    return found


def _assigned_string(tree, name):
    for node in tree.body:
        target = None
        value = None
        if isinstance(node, ast.Assign):
            target = node.targets[0]
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            value = node.value
        if isinstance(target, ast.Name) and target.id == name and isinstance(value, ast.Constant):
            return value.value
    raise AssertionError(name)


def test_shell_absent_is_typed_unavailable():
    facts = COMMUNICATIONS_REGISTRATION_FACTS
    assert facts.entry_kind == "company_profile"
    assert facts.anchor_theme_id is None
    assert facts.slice_keys == ()
    assert facts.company_slots == _ROSTER
    if importlib.util.find_spec("engine.market_ontology.theme_research_registry") is None:
        with pytest.raises(CommunicationsRegistrationRefusal) as raised:
            registration_entry_or_refusal()
        assert raised.value.code == "shared_shell_unavailable"
    else:
        with pytest.raises(CommunicationsRegistrationRefusal) as raised:
            registration_entry_or_refusal()
        assert raised.value.code == VERTICAL_REGISTRATION_HELD_COMPANY_PROFILE


def test_shared_contract_two_arm():
    if importlib.util.find_spec("engine.theme_graph.curation_assertion") is None:
        with pytest.raises(CommunicationsRegistrationRefusal) as raised:
            shared_contract()
        assert raised.value.code == "shared_contract_unavailable"
    else:
        module = shared_contract()
        assert callable(module.validate_assertion)
        assert callable(module.curation_revision)
    called = []
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"validate_assertion", "curation_revision", "generation_fingerprint"}:
                called.append(node.func.attr)
    assert called == []


def test_import_literals_match_module_constants():
    module_tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    allowed = {
        _assigned_string(module_tree, "SHARED_CONTRACT_MODULE"),
        _assigned_string(module_tree, "SHARED_SHELL_MODULE"),
        _assigned_string(module_tree, "SHARED_REGISTRY_MODULE"),
    }
    assert allowed == {
        SHARED_CONTRACT_MODULE,
        SHARED_SHELL_MODULE,
        SHARED_REGISTRY_MODULE,
    }
    assert allowed == {
        "engine.theme_graph.curation_assertion",
        "engine.market_ontology.theme_research_binding",
        "engine.market_ontology.theme_research_registry",
    }
    assert set(_import_module_literals(module_tree)) == allowed
    test_tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    assert set(_import_module_literals(test_tree)) <= allowed


def test_registration_fields_include_view_keys_load_bundle_build_query(monkeypatch):
    assert _VERTICAL_REGISTRATION_FIELDS == SHELL_FIELDS
    if importlib.util.find_spec("engine.market_ontology.theme_research_registry") is not None:
        registry = importlib.import_module("engine.market_ontology.theme_research_registry")
        observed = tuple(field.name for field in dataclasses.fields(registry.VerticalRegistration))
        assert _VERTICAL_REGISTRATION_FIELDS == observed
    required = ("view_keys", "load_bundle", "build_query")
    calls = []

    class VerticalRegistration:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            missing = [name for name in required if name not in kwargs]
            if missing:
                raise TypeError("missing " + ",".join(missing))

    stub = types.ModuleType("engine.market_ontology.theme_research_registry")
    stub.VerticalRegistration = VerticalRegistration
    monkeypatch.setitem(sys.modules, "engine.market_ontology.theme_research_registry", stub)
    facts = _theme_registrable()
    assert facts.anchor_theme_id == "communications_company"
    assert "military_space_communications" not in facts.anchor_theme_id
    entry = registration_entry_or_refusal(facts)
    assert len(calls) == 1
    assert set(required) <= set(calls[0])
    assert entry is not None
    omitted = {name: value for name, value in calls[0].items() if name not in required}
    with pytest.raises(TypeError, match="missing"):
        VerticalRegistration(**omitted)


def test_company_profile_held_before_construction(monkeypatch):
    calls = []

    class VerticalRegistration:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    stub = types.ModuleType("engine.market_ontology.theme_research_registry")
    stub.VerticalRegistration = VerticalRegistration
    monkeypatch.setitem(sys.modules, "engine.market_ontology.theme_research_registry", stub)
    with pytest.raises(CommunicationsRegistrationRefusal) as raised:
        registration_entry_or_refusal()
    assert raised.value.code == VERTICAL_REGISTRATION_HELD_COMPANY_PROFILE
    assert calls == []
    with pytest.raises(CommunicationsRegistrationRefusal) as raised:
        COMMUNICATIONS_REGISTRATION_FACTS.compose(object(), object())
    assert raised.value.code == VERTICAL_REGISTRATION_HELD_COMPANY_PROFILE
    with pytest.raises(CommunicationsRegistrationRefusal) as raised:
        COMMUNICATIONS_REGISTRATION_FACTS.select_evidence(object(), object(), "fixture:assertion")
    assert raised.value.code == VERTICAL_REGISTRATION_HELD_COMPANY_PROFILE


def test_load_bundle_raises_bundle_unavailable(monkeypatch):
    facts = _theme_registrable()
    assert facts.slice_keys
    query = build_query()
    if importlib.util.find_spec("engine.market_ontology.theme_research_binding") is None:
        class BundleUnavailable(Exception):
            pass

        class ResearchRefusal(ValueError):
            def __init__(self, code):
                super().__init__(code)
                self.code = code

        stub = types.ModuleType("engine.market_ontology.theme_research_binding")
        stub.BundleUnavailable = BundleUnavailable
        stub.ResearchRefusal = ResearchRefusal
        stub.generation_fingerprint = lambda **_kwargs: "gen_unused"
        monkeypatch.setitem(sys.modules, "engine.market_ontology.theme_research_binding", stub)
        with pytest.raises(BundleUnavailable, match="communications_owner_bundle_absent"):
            load_bundle(query, rights_snapshot={"revision": "fixture"})
    else:
        binding = importlib.import_module("engine.market_ontology.theme_research_binding")
        with pytest.raises(binding.BundleUnavailable, match="communications_owner_bundle_absent"):
            load_bundle(query, rights_snapshot={"revision": "fixture"})


def test_build_query_rejects_unknown_field():
    query = build_query()
    assert type(query).__name__ == "CommunicationsResearchQuery"
    assert dataclasses.fields(query) == ()
    assert query.__dataclass_params__.frozen is True
    if importlib.util.find_spec("engine.market_ontology.theme_research_binding") is None:
        with pytest.raises(CommunicationsRegistrationRefusal) as raised:
            build_query(anchor_theme_id="theme:military_space_communications")
        assert raised.value.code == "query_field_rejected"
    else:
        binding = importlib.import_module("engine.market_ontology.theme_research_binding")
        with pytest.raises(binding.ResearchRefusal) as raised:
            build_query(anchor_theme_id="theme:military_space_communications")
        assert str(raised.value) == "query_field_rejected"


@pytest.mark.parametrize("relative", SOURCES)
def test_no_semiconductor_import(relative):
    tree = ast.parse((REPO_ROOT / relative).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call) and node.args:
            func = node.func
            label = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if label == "import_module" and isinstance(node.args[0], ast.Constant):
                imported.add(node.args[0].value)
    assert not any(
        name.startswith("engine.market_ontology.semiconductor_theme_research")
        for name in imported
    ), imported


def test_payload_binding_state_remains_unbound():
    payload = compose_communications_payload(())
    assert payload["binding_state"] == "unbound"
    assert payload["schema"] == COMMUNICATIONS_REGISTRATION_FACTS.schema_id
    assert COMMUNICATIONS_REGISTRATION_FACTS.schema_id != COMMUNICATIONS_REGISTRATION_FACTS.evidence_schema_id
    assert registration_entry_or_refusal.__name__ == "registration_entry_or_refusal"
