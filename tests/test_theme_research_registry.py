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


def _noop_build_query(**fields):  # pragma: no cover — shape only
    return fields


def _valid_kwargs(**overrides):
    kwargs = dict(
        anchor_theme_id="synthetic_vertical",
        slice_keys=("alpha_slice", "beta_slice"),
        # A DIFFERENT admitted view set from the incumbent's five: this
        # synthetic vertical is the control for "the shell holds no vertical's
        # vocabulary" (Sol #7870 issuecomment-5923155205). If a semiconductor
        # view were hard-pinned anywhere in the transport, a vertical whose
        # views are ``alpha_view``/``beta_view`` could not be served at all.
        view_keys=("alpha_view", "beta_view"),
        schema_id="synthetic_theme_research.v1",
        evidence_schema_id="synthetic_theme_research.evidence.v1",
        definition_version="2026-09-24.synthetic",
        compose=_noop_compose,
        select_evidence=_noop_select,
        load_bundle=_noop_load,
        build_query=_noop_build_query,
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


def _vertical_module(anchor, bound, field):
    """The module a registration's lazily bound callable dispatches into.

    Every registered callable must expose ``lazy_target()`` — a zero-argument
    accessor returning the real vertical function. That is the contract the
    laziness law and the identity law share: without it a test can prove
    neither which function will run nor that importing the registry left the
    vertical unloaded.
    """
    import sys

    target = getattr(bound, "lazy_target", None)
    assert callable(target), (
        f"{anchor}: registration field {field!r} is bound without a "
        f"``lazy_target()`` accessor. Bind it lazily and expose the accessor: "
        f"an eager binding reintroduces the import edge that made the shared "
        f"shell unloadable without one vertical, and a wrapper without the "
        f"accessor hides the module whose constants this law reconciles."
    )
    resolved = target()
    module = sys.modules.get(resolved.__module__)
    assert module is not None, f"{anchor}: {field} resolved to an unloaded module"
    return module


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
    assert entry.view_keys == composer.VIEW_KEYS
    assert entry.schema_id == composer.SCHEMA_ID == "semiconductor_theme_research.v1"
    assert entry.evidence_schema_id == composer._EVIDENCE_SCHEMA_ID \
        == "semiconductor_theme_research.evidence.v1"
    assert entry.definition_version == composer.DEFINITION_VERSION
    # The binding is LAZY — importing the registry must not execute this
    # composer's closure, which is the edge that made the shared shell
    # unloadable without this one vertical (Sol #7870
    # issuecomment-5895067178). ``lazy_target()`` resolves the registration
    # to the exact function it dispatches to, so the identity guarantee this
    # test has always carried is unchanged: it is asserted through the
    # accessor instead of through a direct module reference.
    assert entry.compose.lazy_target() is composer.compose_semiconductor_research
    assert entry.select_evidence.lazy_target() is composer.select_authorized_evidence
    assert entry.build_query.lazy_target() is composer.ResearchQuery


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

    Resolution goes through ``lazy_target()``, not ``fn.__module__``: a
    registration binds its vertical LAZILY so that importing the registry —
    or the shared shell above it — loads no vertical composer at all (Sol
    #7870 issuecomment-5895067178), and a lazy binding's ``__module__`` is
    the registry, not the composer. Requiring the accessor is what keeps this
    law total: it cannot be satisfied by an eager binding that reintroduces
    the import edge, and it cannot be dodged by a wrapper that hides which
    function the registration actually dispatches to.
    """
    assert REGISTRY, "the registry is empty: this law would be vacuous"
    for anchor, entry in REGISTRY.items():
        compose_module = _vertical_module(anchor, entry.compose, "compose")
        assert getattr(compose_module, "SCHEMA_ID", None) == entry.schema_id, (
            f"{anchor}: registration schema_id {entry.schema_id!r} is not the "
            f"one {compose_module.__name__} emits"
        )
        assert getattr(compose_module, "DEFINITION_VERSION", None) == \
            entry.definition_version, (
            f"{anchor}: registration definition_version is not the composer's"
        )
        assert getattr(compose_module, "VIEW_KEYS", None) == entry.view_keys, (
            f"{anchor}: registration view_keys {entry.view_keys!r} are not the "
            f"views {compose_module.__name__} admits. The registration owns the "
            f"admitted view set and the shell validates membership against it, "
            f"so a drifted copy here refuses views the composer serves — or "
            f"admits views it does not."
        )
        evidence_module = _vertical_module(
            anchor, entry.select_evidence, "select_evidence",
        )
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
    # The fourteen v1 fields keep their ORDER; the v2 profile columns
    # (packet §3.4, lane 5) are appended AFTER note_zh, all defaulted, so
    # every existing positional/keyword construction still builds the same
    # theme entry. A reorder or a removal here is a contract break.
    assert [f.name for f in dataclasses.fields(VerticalRegistration)] == [
        "anchor_theme_id", "slice_keys", "view_keys", "schema_id",
        "evidence_schema_id", "definition_version", "compose",
        "select_evidence", "load_bundle", "build_query",
        "title_en", "title_zh", "note_en", "note_zh",
        "entry_kind", "profile_id", "subject_field", "subject_values",
        "time_modes", "single_document", "native_generation_prefix",
        "native_generation_width", "evidence_refs_field",
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


#: No VERTICAL may load when a SHARED module is imported. This is the edge Sol
#: #7870 issuecomment-5895067178 ordered removed: the registry used to import
#: the semiconductor composer eagerly for three names, and the shell imported
#: three more from it directly, so importing either shared module executed one
#: vertical's entire closure and no second vertical could be served without it.
#: A vertical now loads only once a request has actually resolved its
#: registration. Both shared entry points are measured against this set. The
#: two §8 profile adapters joined the set when the profile registry did: each
#: imports its own composer eagerly on ITS import, so a profile entry that
#: bound one eagerly would reintroduce exactly the removed edge.
_VERTICALS_AT_IMPORT = (
    "engine.market_ontology.semiconductor_theme_research",
    "engine.market_ontology.semiconductor_owner_bundle",
    "engine.market_ontology.technology_research_registration",
    "engine.sector_intelligence.finance_research_registration",
)

#: Additionally forbidden for the REGISTRY alone: the reader's network / data
#: stack and the web/template frameworks. Producers import the registry for the
#: mount copy, so it must stay cheap. The shell is deliberately exempt — it IS
#: the FastAPI router, so ``fastapi`` in its closure is its job, not a defect.
_HEAVY_AT_IMPORT = (
    "requests", "pandas", "pyarrow", "numpy", "fastapi", "jinja2",
    "engine.neuralweb.company_intelligence_reader",
)


def _loaded_after_importing(entry_point: str, probe: tuple[str, ...]) -> str:
    import subprocess
    import sys
    code = (
        f"import sys; import {entry_point}; "
        f"print(sorted(m for m in {probe!r} if m in sys.modules))"
    )
    result = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True,
                            cwd=str(ROOT), timeout=120)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.mark.parametrize("entry_point", [
    pytest.param("engine.market_ontology.theme_research_registry", id="registry"),
    pytest.param("app.theme_research", id="shared-shell"),
])
def test_no_vertical_loads_when_a_shared_module_is_imported(entry_point):
    assert _loaded_after_importing(entry_point, _VERTICALS_AT_IMPORT) == "[]"


def test_registry_import_closure_stays_light():
    """Importing the registry alone must not load the reader's network / data
    stack nor a web framework or template engine."""
    assert _loaded_after_importing(
        "engine.market_ontology.theme_research_registry", _HEAVY_AT_IMPORT,
    ) == "[]"


def test_the_vertical_import_probe_actually_fires():
    """Positive control for the laziness law: the same probe MUST report the
    composer when something imports it on purpose. Without this, a probe with
    a misspelled module name would pass the law vacuously forever."""
    assert _loaded_after_importing(
        "engine.market_ontology.semiconductor_theme_research", _VERTICALS_AT_IMPORT,
    ) == "['engine.market_ontology.semiconductor_theme_research']"


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
    # The admitted VIEW set is validated exactly like the admitted slice set:
    # the registration owns both vocabularies, so both refuse malformation at
    # construction rather than letting the transport admit by grammar alone.
    pytest.param({"view_keys": ()}, id="views-empty"),
    pytest.param({"view_keys": ["alpha_view"]}, id="views-list-not-tuple"),
    pytest.param({"view_keys": "alpha_view"}, id="views-bare-string"),
    pytest.param({"view_keys": ("alpha_view", "alpha_view")}, id="views-duplicate"),
    pytest.param({"view_keys": ("Alpha-View",)}, id="view-grammar"),
    pytest.param({"view_keys": ("",)}, id="view-empty"),
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
    pytest.param({"build_query": None}, id="build-query-none"),
    pytest.param({"build_query": "ResearchQuery"}, id="build-query-name-string"),
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
        "REGISTRY", "PROFILE_REGISTRY", "VerticalRegistration",
        "allowed_slices", "allowed_views", "profile_registration_for",
        "registration_for",
    }


# ---------------------------------------------------------------------------
# 6. The closed PROFILE registry — the v2 company/sector profile kinds
# (packet §3.4, lane 5). Same closure laws as the theme registry, keyed by
# exact profile id instead of anchor.
# ---------------------------------------------------------------------------

from engine.market_ontology.theme_research_registry import (  # noqa: E402
    PROFILE_REGISTRY,
    profile_registration_for,
)


def test_profile_registry_is_a_read_only_mapping_with_two_entries():
    assert isinstance(PROFILE_REGISTRY, MappingProxyType)
    assert list(PROFILE_REGISTRY) == [
        "technology_economic_change.v1", "finance_intelligence_research.v1",
    ]
    with pytest.raises(TypeError):
        PROFILE_REGISTRY["robotics_automation"] = PROFILE_REGISTRY[
            "technology_economic_change.v1"
        ]  # type: ignore[index]
    with pytest.raises(TypeError):
        del PROFILE_REGISTRY["finance_intelligence_research.v1"]  # type: ignore[attr-defined]


def test_profile_entries_are_keyed_by_their_own_profile_id_and_kind():
    for profile_id, entry in PROFILE_REGISTRY.items():
        assert isinstance(entry, VerticalRegistration)
        assert entry.profile_id == profile_id
        assert entry.anchor_theme_id == profile_id
        assert entry.entry_kind != "theme"
        assert entry.slice_keys == ()
    assert PROFILE_REGISTRY["technology_economic_change.v1"].entry_kind == "company_profile"
    assert PROFILE_REGISTRY["finance_intelligence_research.v1"].entry_kind == "sector_profile"


@pytest.mark.parametrize("probe", [
    pytest.param("Technology_Economic_Change.v1", id="upper-case"),
    pytest.param("technology_economic_change", id="missing-version"),
    pytest.param("technology_economic_change.v2", id="wrong-version"),
    pytest.param(" technology_economic_change.v1", id="leading-space"),
    pytest.param("", id="empty"),
    pytest.param("ai_semiconductors", id="theme-anchor-as-profile"),
    pytest.param(None, id="none"),
    pytest.param(7, id="int"),
    pytest.param(("technology_economic_change.v1",), id="tuple"),
])
def test_profile_registration_for_unknown_or_non_exact_probe_is_none(probe):
    assert profile_registration_for(probe) is None


def test_profile_registration_for_is_exact_and_returns_the_entry():
    entry = profile_registration_for("technology_economic_change.v1")
    assert entry is PROFILE_REGISTRY["technology_economic_change.v1"]


def test_theme_and_profile_key_spaces_are_disjoint():
    for profile_id in PROFILE_REGISTRY:
        assert profile_id not in REGISTRY
    for anchor in REGISTRY:
        assert anchor not in PROFILE_REGISTRY


def test_technology_registration_reconciles_with_its_adapter_module():
    """The same reconciliation law as the theme entries, stated for the
    company_profile adapter: the registration's literals must be the
    adapter's own constants, or the profile registry serves a contract the
    vertical never emitted."""
    entry = PROFILE_REGISTRY["technology_economic_change.v1"]
    import engine.market_ontology.technology_research_registration as adapter_module
    assert entry.schema_id == adapter_module.PROFILE_ID
    assert entry.evidence_schema_id == adapter_module.EVIDENCE_SCHEMA_ID
    assert entry.definition_version == adapter_module.DEFINITION_VERSION
    assert entry.view_keys == adapter_module.VIEWS
    assert entry.profile_id == adapter_module.TECHNOLOGY_REGISTRATION_FACTS.profile_id
    assert entry.title_en == adapter_module.TECHNOLOGY_REGISTRATION_FACTS.title_en
    assert entry.title_zh == adapter_module.TECHNOLOGY_REGISTRATION_FACTS.title_zh
    assert entry.note_en == adapter_module.TECHNOLOGY_REGISTRATION_FACTS.note_en
    assert entry.note_zh == adapter_module.TECHNOLOGY_REGISTRATION_FACTS.note_zh
    # The lazy bindings dispatch to the adapter's own callables.
    assert entry.compose.lazy_target() is adapter_module.compose
    assert entry.select_evidence.lazy_target() is adapter_module.select_evidence
    assert entry.build_query.lazy_target() is adapter_module.build_query
    assert entry.load_bundle.lazy_target() is adapter_module.load_bundle


def test_finance_registration_reconciles_with_its_adapter_module():
    entry = PROFILE_REGISTRY["finance_intelligence_research.v1"]
    import engine.sector_intelligence.finance_research_registration as adapter_module
    assert entry.schema_id == adapter_module.PROFILE_ID
    assert entry.evidence_schema_id == adapter_module.EVIDENCE_SCHEMA_ID
    assert entry.definition_version == adapter_module.DEFINITION_VERSION
    assert entry.view_keys == adapter_module.VIEWS
    assert entry.subject_values == (adapter_module.SECTOR_REF,)
    assert entry.profile_id == adapter_module.FINANCE_REGISTRATION_FACTS.profile_id
    assert entry.title_en == adapter_module.FINANCE_REGISTRATION_FACTS.title_en
    assert entry.title_zh == adapter_module.FINANCE_REGISTRATION_FACTS.title_zh
    assert entry.note_en == adapter_module.FINANCE_REGISTRATION_FACTS.note_en
    assert entry.note_zh == adapter_module.FINANCE_REGISTRATION_FACTS.note_zh
    assert entry.compose.lazy_target() is adapter_module.compose
    assert entry.select_evidence.lazy_target() is adapter_module.select_evidence
    assert entry.build_query.lazy_target() is adapter_module.build_query
    assert entry.load_bundle.lazy_target() is adapter_module.load_bundle


def test_profile_entry_native_generation_grammar_is_the_verticals_own():
    """Technology's native dossier id keeps its tecd_ prefix and is never
    renamed to gen_ (packet §3.5); Finance's native generation is the shared
    gen_ fingerprint. The CONTEXT surface is always gen_ and lives in the
    shell, never here."""
    tech = PROFILE_REGISTRY["technology_economic_change.v1"]
    assert tech.native_generation_prefix == "tecd_"
    assert tech.native_generation_width == 32
    finance = PROFILE_REGISTRY["finance_intelligence_research.v1"]
    assert finance.native_generation_prefix == "gen_"


@pytest.mark.parametrize("overrides", [
    pytest.param({"entry_kind": "vertical"}, id="entry-kind-unknown"),
    pytest.param({"entry_kind": "company_profile"}, id="profile-kind-without-profile-id"),
    pytest.param({"profile_id": "technology_economic_change.v1"}, id="theme-with-profile-id"),
    pytest.param({"entry_kind": "company_profile", "profile_id": "Technology.V1"},
                 id="profile-grammar"),
    pytest.param({"subject_field": "company ref"}, id="subject-field-grammar"),
    pytest.param({"subject_values": ["sector:financials"]}, id="subject-values-list"),
    pytest.param({"subject_values": ("sector:financials", "sector:financials")},
                 id="subject-values-duplicate"),
    pytest.param({"time_modes": ()}, id="time-modes-empty"),
    pytest.param({"time_modes": ("latest", "latest")}, id="time-modes-duplicate"),
    pytest.param({"time_modes": ("Latest",)}, id="time-mode-grammar"),
    pytest.param({"single_document": "yes"}, id="single-document-not-bool"),
    pytest.param({"native_generation_prefix": ""}, id="native-prefix-empty"),
    pytest.param({"native_generation_prefix": "te cd"}, id="native-prefix-grammar"),
    pytest.param({"native_generation_width": 4}, id="native-width-too-small"),
    pytest.param({"native_generation_width": 128}, id="native-width-too-large"),
    pytest.param({"native_generation_width": True}, id="native-width-bool"),
    pytest.param({"evidence_refs_field": "  "}, id="evidence-refs-field-blank"),
])
def test_malformed_v2_columns_are_refused_with_value_error(overrides):
    with pytest.raises(ValueError):
        VerticalRegistration(**_valid_kwargs(**overrides))


def test_profile_entry_construction_requires_empty_slices_and_matching_anchor():
    """A profile entry's anchor column holds the profile id (one identity),
    and its slice tuple stays empty: slices are theme vocabulary."""
    entry = VerticalRegistration(
        **_valid_kwargs(
            entry_kind="company_profile",
            anchor_theme_id="synthetic_profile.v1",
            profile_id="synthetic_profile.v1",
            slice_keys=(),
            subject_field="company_ref",
        )
    )
    assert entry.entry_kind == "company_profile"
    assert entry.profile_id == "synthetic_profile.v1"
    assert registration_for("synthetic_profile.v1") is None  # not theme-registered
    with pytest.raises(ValueError):
        VerticalRegistration(**_valid_kwargs(
            entry_kind="company_profile",
            anchor_theme_id="synthetic_profile.v1",
            profile_id="different_profile.v1",
            slice_keys=(),
        ))
    with pytest.raises(ValueError):
        VerticalRegistration(**_valid_kwargs(
            entry_kind="sector_profile",
            profile_id="synthetic_profile.v1",
        ))
