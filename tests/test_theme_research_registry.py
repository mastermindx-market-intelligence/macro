"""Closed vertical registration (shared hook 1) — Sol ruling #7780
issuecomment-5813801605: "NO wildcard/regex schema acceptance. Use a trusted
closed registration binding anchor, slice set, exact schema/version, composer
and evidence selector ... Unknown/mismatched schema/anchor/slice fails."

Pinned here:

* the registry is a read-only mapping with EXACTLY one entry today
  (``ai_semiconductors``); adding a vertical is one additive entry;
* the semiconductor entry binds the composer's own exact constants and
  callables — no restatement can drift;
* lookup is exact-string: no case/whitespace normalisation, no prefix, no
  regex, no default, no environment, no config file;
* the registration dataclass is frozen and refuses malformed registrations at
  construction (bad grammar, empty/duplicate slices, identical schema ids,
  non-callables);
* the module imports no web framework, template engine, regex, glob, os or
  file machinery (AST-level scan).
"""
from __future__ import annotations

import ast
import dataclasses
from pathlib import Path
from types import MappingProxyType

import pytest

from engine.market_ontology import semiconductor_theme_research as composer
from engine.market_ontology import theme_research_registry as registry
from engine.market_ontology.theme_research_registry import (
    REGISTRY,
    VerticalRegistration,
    allowed_slices,
    registration_for,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "engine" / "market_ontology" / "theme_research_registry.py"

# The bilingual copy the T10b mount renders (law L5) — pinned as literals so
# the registration, not the template, is the source the mount reads.
_TITLE_EN = "Semiconductor industry research"
_TITLE_ZH = "半导体产业研究"
_NOTE_EN = (
    "Paid research context for members. Nothing here ranks, gates, sizes or "
    "times anything."
)
_NOTE_ZH = "会员研究内容。此处内容不构成排序、准入、仓位或时机判断。"


def _noop_compose(query, bundle):  # pragma: no cover — shape only
    return {"schema": "synthetic.v1"}


def _noop_select(query, bundle, ref):  # pragma: no cover — shape only
    return {"schema": "synthetic.evidence.v1"}


def _noop_load(query, *, rights_snapshot=None):  # pragma: no cover — shape only
    raise AssertionError("synthetic loader never serves")


def _valid_kwargs(**overrides):
    kwargs = dict(
        anchor_theme_id="synthetic_vertical",
        slice_keys=("alpha_slice", "beta_slice"),
        schema_id="synthetic_theme_research.v1",
        evidence_schema_id="synthetic_theme_research.evidence.v1",
        definition_version="2026-09-24.synthetic",
        compose=_noop_compose,
        select_evidence=_noop_select,
        load_bundle=_noop_load,
        title_en="Synthetic research",
        title_zh="合成研究",
        note_en="Synthetic note.",
        note_zh="合成说明。",
    )
    kwargs.update(overrides)
    return kwargs


# ---------------------------------------------------------------------------
# 1. The registry is closed: read-only, exactly one entry today
# ---------------------------------------------------------------------------

def test_registry_is_a_read_only_mapping_with_exactly_one_entry():
    assert isinstance(REGISTRY, MappingProxyType)
    assert list(REGISTRY) == ["ai_semiconductors"]
    with pytest.raises(TypeError):
        REGISTRY["robotics_automation"] = REGISTRY["ai_semiconductors"]  # type: ignore[index]
    with pytest.raises(TypeError):
        del REGISTRY["ai_semiconductors"]  # type: ignore[attr-defined]
    assert list(REGISTRY) == ["ai_semiconductors"]


def test_every_entry_is_keyed_by_its_own_anchor():
    for anchor, entry in REGISTRY.items():
        assert isinstance(entry, VerticalRegistration)
        assert entry.anchor_theme_id == anchor


# ---------------------------------------------------------------------------
# 2. The semiconductor entry binds the composer's exact contract
# ---------------------------------------------------------------------------

def test_semiconductor_registration_binds_composer_constants_and_callables():
    entry = REGISTRY["ai_semiconductors"]
    assert entry.slice_keys == ("hbm_packaging", "sic_gan_specialty")
    assert entry.schema_id == composer.SCHEMA_ID == "semiconductor_theme_research.v1"
    assert entry.evidence_schema_id == composer._EVIDENCE_SCHEMA_ID \
        == "semiconductor_theme_research.evidence.v1"
    assert entry.definition_version == composer.DEFINITION_VERSION
    assert entry.compose is composer.compose_semiconductor_research
    assert entry.select_evidence is composer.select_authorized_evidence


def test_every_registration_reconciles_with_its_own_vertical_module():
    """The same law as the semiconductor test above, stated over the WHOLE
    registry instead of over one named vertical.

    ``MountFacts`` is where a vertical's schema ids are typed by hand; the
    registration then derives them from the mount. So a typo in
    ``MountFacts.schema_id`` leaves the registration agreeing with itself,
    while the shell refuses every composed payload for carrying "the wrong"
    schema — a total outage for that vertical with nothing red. The named
    test proves that cannot happen for the one vertical that exists today;
    this one proves it for every vertical added after it is written, which is
    the half that was missing. (Shape raised by the Robotics receiver on
    #7870; the hole is on this side, so the test is too.)

    The vertical's module is found through its OWN registered callables, so
    this test never grows a per-vertical table to keep in sync.
    """
    import sys

    assert REGISTRY, "the registry is empty: this law would be vacuous"
    for anchor, entry in REGISTRY.items():
        compose_module = sys.modules[entry.compose.__module__]
        assert getattr(compose_module, "SCHEMA_ID", None) == entry.schema_id, (
            f"{anchor}: registration schema_id {entry.schema_id!r} is not the "
            f"one {compose_module.__name__} emits. If this vertical registers a "
            f"lazy WRAPPER instead of its module-level composer, register the "
            f"composer itself: the shell binds callables, and a wrapper hides "
            f"the module whose constants this law reconciles against."
        )
        assert getattr(compose_module, "DEFINITION_VERSION", None) == \
            entry.definition_version, (
            f"{anchor}: registration definition_version is not the composer's"
        )
        evidence_module = sys.modules[entry.select_evidence.__module__]
        declared = [
            getattr(evidence_module, name)
            for name in ("EVIDENCE_SCHEMA_ID", "_EVIDENCE_SCHEMA_ID")
            if hasattr(evidence_module, name)
        ]
        assert declared, (
            f"{anchor}: {evidence_module.__name__} declares no evidence schema "
            f"id constant, so nothing can reconcile the registration's"
        )
        assert entry.evidence_schema_id in declared, (
            f"{anchor}: registration evidence_schema_id "
            f"{entry.evidence_schema_id!r} is not the one "
            f"{evidence_module.__name__} emits"
        )


def test_semiconductor_registration_carries_the_mount_copy_verbatim():
    entry = REGISTRY["ai_semiconductors"]
    assert entry.title_en == _TITLE_EN
    assert entry.title_zh == _TITLE_ZH
    assert entry.note_en == _NOTE_EN
    assert entry.note_zh == _NOTE_ZH
    # The mount's ``data-slices`` attribute is the joined closed slice set.
    assert ",".join(entry.slice_keys) == "hbm_packaging,sic_gan_specialty"


def test_dataclass_field_names_are_the_accepted_contract():
    assert [f.name for f in dataclasses.fields(VerticalRegistration)] == [
        "anchor_theme_id", "slice_keys", "schema_id", "evidence_schema_id",
        "definition_version", "compose", "select_evidence", "load_bundle",
        "title_en", "title_zh", "note_en", "note_zh",
    ]


def test_semiconductor_entry_binds_the_public_half_loader(monkeypatch):
    """T08c-2: the ONE entry's loader dispatches to the semiconductor
    owner-bundle loader (public half through the reader, private half
    declared absent) — bound lazily so the registry's import closure stays
    light for producers; the shell dispatches to it and names no vertical."""
    import engine.market_ontology.semiconductor_owner_bundle as loader_module
    seen: list = []
    monkeypatch.setattr(loader_module, "load_semiconductor_owner_bundle",
                        lambda query, *, rights_snapshot=None: seen.append((query, rights_snapshot)) or "bundle")
    assert REGISTRY["ai_semiconductors"].load_bundle("q", rights_snapshot=("r", {})) == "bundle"
    assert seen == [("q", ("r", {}))]


def test_registry_import_closure_stays_light():
    """Importing the registry alone must not load the reader's network / data
    stack (requests, pandas, pyarrow, numpy) nor a web framework or template
    engine — producers import it for the mount copy."""
    import subprocess
    import sys
    code = (
        "import sys; import engine.market_ontology.theme_research_registry; "
        "print(sorted(m for m in ('requests', 'pandas', 'pyarrow', 'numpy', 'fastapi', 'jinja2', "
        "'engine.neuralweb.company_intelligence_reader', 'engine.market_ontology.semiconductor_owner_bundle') "
        "if m in sys.modules))"
    )
    result = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True,
                            cwd=str(ROOT), timeout=120)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]", result.stdout


@pytest.mark.parametrize("bad", [None, "load", 7, object()])
def test_non_callable_loader_is_refused(bad):
    with pytest.raises(TypeError):
        VerticalRegistration(**_valid_kwargs(load_bundle=bad))


# ---------------------------------------------------------------------------
# 3. Lookup is exact-string; anything else resolves to None / empty
# ---------------------------------------------------------------------------

def test_registration_for_is_exact_and_returns_the_entry():
    assert registration_for("ai_semiconductors") is REGISTRY["ai_semiconductors"]


@pytest.mark.parametrize("probe", [
    pytest.param("AI_SEMICONDUCTORS", id="upper-case"),
    pytest.param("Ai_Semiconductors", id="mixed-case"),
    pytest.param(" ai_semiconductors", id="leading-space"),
    pytest.param("ai_semiconductors ", id="trailing-space"),
    pytest.param("ai_semiconductor", id="prefix"),
    pytest.param("ai_semiconductors_x", id="extension"),
    pytest.param("ai_semiconductors*", id="wildcard"),
    pytest.param("ai_semiconductor.", id="regex-dot"),
    pytest.param("", id="empty"),
    pytest.param("robotics_automation", id="unregistered-real-theme"),
    pytest.param("synthetic_vertical", id="unregistered-synthetic"),
    pytest.param(None, id="none"),
    pytest.param(b"ai_semiconductors", id="bytes"),
    pytest.param(("ai_semiconductors",), id="tuple"),
    pytest.param(0, id="int"),
])
def test_registration_for_unknown_or_non_exact_probe_is_none(probe):
    assert registration_for(probe) is None
    assert allowed_slices(probe) == frozenset()


def test_allowed_slices_is_the_closed_slice_set():
    assert allowed_slices("ai_semiconductors") == frozenset(
        {"hbm_packaging", "sic_gan_specialty"}
    )
    assert isinstance(allowed_slices("ai_semiconductors"), frozenset)


# ---------------------------------------------------------------------------
# 4. The registration is frozen and refuses malformed entries
# ---------------------------------------------------------------------------

def test_registration_is_frozen():
    entry = REGISTRY["ai_semiconductors"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.slice_keys = ("hbm_packaging",)  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.compose = _noop_compose  # type: ignore[misc]


def test_synthetic_registration_constructs_without_touching_the_registry():
    entry = VerticalRegistration(**_valid_kwargs())
    assert entry.anchor_theme_id == "synthetic_vertical"
    assert list(REGISTRY) == ["ai_semiconductors"]
    assert registration_for("synthetic_vertical") is None


@pytest.mark.parametrize("overrides", [
    pytest.param({"anchor_theme_id": "Synthetic-Vertical"}, id="anchor-grammar"),
    pytest.param({"anchor_theme_id": ""}, id="anchor-empty"),
    pytest.param({"anchor_theme_id": "a" * 65}, id="anchor-too-long"),
    pytest.param({"anchor_theme_id": "synthetic vertical"}, id="anchor-space"),
    pytest.param({"slice_keys": ()}, id="slices-empty"),
    pytest.param({"slice_keys": ["alpha_slice"]}, id="slices-list-not-tuple"),
    pytest.param({"slice_keys": "alpha_slice"}, id="slices-bare-string"),
    pytest.param({"slice_keys": ("alpha_slice", "alpha_slice")}, id="slices-duplicate"),
    pytest.param({"slice_keys": ("Alpha-Slice",)}, id="slice-grammar"),
    pytest.param({"slice_keys": ("",)}, id="slice-empty"),
    pytest.param({"schema_id": ""}, id="schema-empty"),
    pytest.param({"schema_id": "   "}, id="schema-blank"),
    pytest.param({"evidence_schema_id": "synthetic_theme_research.v1"},
                 id="schema-ids-identical"),
    pytest.param({"definition_version": ""}, id="definition-version-empty"),
    pytest.param({"title_en": ""}, id="title-en-empty"),
    pytest.param({"note_zh": None}, id="note-zh-none"),
])
def test_malformed_registration_is_refused_with_value_error(overrides):
    with pytest.raises(ValueError):
        VerticalRegistration(**_valid_kwargs(**overrides))


@pytest.mark.parametrize("overrides", [
    pytest.param({"compose": None}, id="compose-none"),
    pytest.param({"compose": "compose_semiconductor_research"}, id="compose-name-string"),
    pytest.param({"select_evidence": 42}, id="select-int"),
])
def test_non_callable_composer_or_selector_is_refused_with_type_error(overrides):
    with pytest.raises(TypeError):
        VerticalRegistration(**_valid_kwargs(**overrides))


# ---------------------------------------------------------------------------
# 5. Module closure: no regex/glob/os/file/framework machinery, no config read
# ---------------------------------------------------------------------------

_FORBIDDEN_IMPORT_ROOTS = frozenset({
    "re", "fnmatch", "glob", "os", "sys", "pathlib", "json", "yaml",
    "subprocess", "fastapi", "starlette", "jinja2", "pydantic", "importlib",
})


def _imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_module_imports_no_regex_glob_os_file_or_framework_machinery():
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    roots = _imported_roots(tree)
    assert not (roots & _FORBIDDEN_IMPORT_ROOTS), sorted(roots & _FORBIDDEN_IMPORT_ROOTS)
    # Only the standard-library typing/dataclass/collections helpers and the
    # vertical's own composer module are imported.
    assert roots <= {"__future__", "collections", "dataclasses", "types",
                     "typing", "engine"}, sorted(roots)


def test_module_opens_no_file_and_reads_no_environment():
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            assert name not in {"open", "getenv", "compile", "match", "fullmatch",
                                "search", "fnmatch", "glob"}, ast.dump(node)[:80]
        if isinstance(node, ast.Attribute):
            assert node.attr != "environ"


def test_module_public_surface_is_closed():
    assert set(registry.__all__) == {
        "REGISTRY", "VerticalRegistration", "allowed_slices", "registration_for",
    }
