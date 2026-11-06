"""Tests for engine.sector_intelligence.finance_research_registration (T10).

Fixture-only and synthetic. Lane clones are SPARSE: NO reads under data/.
The adapter reads the OwnerBundle shape only through getattr, so frozen shell
dataclasses and these synthetic fixtures are accepted equally.

The two contract schemas under test live at the literal paths the FROZEN SPEC
names (the contract-delta gate turns literal paths in code/comments into
dependency edges; this test file pins the three paths it touches explicitly).
"""

from __future__ import annotations

import copy
import dataclasses
import importlib
import importlib.util
import json
import re
import subprocess
import sys
import types
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RESEARCH_MODULE_PATH = (
    REPO_ROOT / "engine" / "sector_intelligence" / "finance_research_registration.py"
)
RESEARCH_SCHEMA_PATH = (
    REPO_ROOT / "contracts" / "sector_intelligence" / "finance_intelligence_research.v1.schema.json"
)
EVIDENCE_SCHEMA_PATH = (
    REPO_ROOT / "contracts" / "sector_intelligence" / "finance_intelligence_research.evidence.v1.schema.json"
)
T1_SCHEMA_PATH = (
    REPO_ROOT / "contracts" / "sector_intelligence" / "finance_intelligence_read_model.v1.schema.json"
)

# Import lazily inside each test so the RED phase (no module) is real.
REG = "engine.sector_intelligence.finance_research_registration"


# ---------------------------------------------------------------------------
# Synthetic query / bundle mirrors the OwnerBundle / ResearchQuery shape
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class _Query:
    """Mirror of the §8 Finance request body (PROFILE_ID + sector_ref + view +
    time_mode; the shell's anchor_theme_id is replaced by sector_ref per the
    FROZEN SPEC)."""

    profile_id: str
    sector_ref: str
    view: str = "dossier"
    time_mode: str = "latest"
    source_cutoff: str | None = None
    recorded_cutoff: str | None = None
    offset: int = 0
    limit: int = 50
    expected_generation: str | None = None


@dataclasses.dataclass(frozen=True)
class _Bundle:
    """Mirror of the shell OwnerBundle field set (semiconductor_theme_research
    @ #7870). Duck-typed."""

    revision_tuple: tuple = ()
    rights_revision: str = "synthetic_rights"
    assertions: tuple = ()
    identity_results: tuple = ()
    event_workspaces: tuple = ()
    financial_packets: tuple = ()
    interpretation_blocks: tuple = ()
    native_refs: tuple = ()
    omissions: tuple = ()


def _import_reg():
    return importlib.import_module(REG)


def _synthetic_run_context_ref() -> dict:
    """The synthetic sealed run-context native ref shape (generated_at and
    knowledge_cutoff as ISO-8601 instants with Z). The adapter reads ONLY
    ``generated_at`` and ``knowledge_cutoff`` off the entry."""
    return {
        "kind": "finance_run_context",
        "generated_at": "2026-09-25T07:48:00Z",
        "knowledge_cutoff": "2026-09-25T07:48:00Z",
    }


def _bundle_with_run_context(*, assertions: tuple = (), omissions: tuple = (),
                              native_refs: tuple = ()) -> _Bundle:
    return _Bundle(
        assertions=assertions,
        native_refs=(*native_refs, _synthetic_run_context_ref()),
        omissions=omissions,
    )


@pytest.fixture
def shell_absent(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Arrange the absence of all four shared-shell modules, whatever the
    carrier holds. ``None`` in ``sys.modules`` halts the import with a
    ``ModuleNotFoundError`` whose ``.name`` IS the module, which is exactly
    the absence ``_import_shell_module`` recognises.

    Every test that pins the absent-shell contract uses this. Relying on
    the checkout lacking #7870's modules turns those tests red on the day
    the modules land, on whichever carrier runs the suite first (review F1).
    """
    reg = _import_reg()
    for name in sorted(reg._SHELL_MODULE_NAMES):
        monkeypatch.setitem(sys.modules, name, None)
    return reg


def _assertion(revision: str = "gmirca_" + ("a" * 32),
               *, theme_id: str = "synthetic_theme") -> dict:
    """Synthetic curation assertion (the shape ``source_ref_for`` reads from)."""
    return {
        "curation_revision": revision,
        "scope": {"canonical_theme_id": theme_id},
        "subject": {"source_business_label": "SYN1"},
        "object": {},
        "predicate": "REPORTED_FACT",
        "statement_mode": "REPORTED_FACT",
        "source": {
            "source_uri": "gmi://synthetic/uri",
            "publisher": "synthetic",
            "locator": "n/a",
            "retained_at": "2026-09-25T00:00:00Z",
        },
        "observation": {"value": None},
    }


# ---------------------------------------------------------------------------
# 1. Facts — the field list and the const values
# ---------------------------------------------------------------------------


def test_facts_field_names_equal_the_frozen_field_set():
    reg = _import_reg()
    expected = (
        "entry_kind", "profile_id", "sector_ref", "anchor_theme_id", "slice_keys",
        "views", "schema_id", "evidence_schema_id", "definition_version",
        "title_en", "title_zh", "note_en", "note_zh", "compose", "select_evidence",
        "load_bundle",
    )
    actual = dataclasses.fields(reg.FinanceRegistrationFacts)
    assert tuple(field.name for field in actual) == expected


def test_facts_equal_their_contract_consts():
    reg = _import_reg()
    research_schema = json.loads(RESEARCH_SCHEMA_PATH.read_text(encoding="utf-8"))
    evidence_schema = json.loads(EVIDENCE_SCHEMA_PATH.read_text(encoding="utf-8"))
    t1_schema = json.loads(T1_SCHEMA_PATH.read_text(encoding="utf-8"))
    expected_sector_ref = t1_schema["properties"]["sector_ref"]["const"]

    facts = reg.FINANCE_REGISTRATION_FACTS
    assert facts.schema_id == reg.PROFILE_ID == research_schema["properties"]["schema"]["const"] == research_schema["properties"]["contract_id"]["const"]
    assert facts.evidence_schema_id == evidence_schema["properties"]["contract_id"]["const"] == evidence_schema["properties"]["schema"]["const"]
    assert facts.definition_version == "2026-09-25.1" == research_schema["properties"]["definition_version"]["const"] == evidence_schema["properties"]["definition_version"]["const"]
    assert facts.sector_ref == expected_sector_ref == "sector:financials"
    assert tuple(facts.views) == reg.VIEWS == ("dossier",)
    assert tuple(reg.TIME_MODES) == ("latest",)
    assert {facts.compose.__module__, facts.select_evidence.__module__, facts.load_bundle.__module__} == {REG}
    assert facts.compose is reg.compose
    assert facts.select_evidence is reg.select_evidence
    assert facts.load_bundle is reg.load_bundle


def test_authority_keys_equal_projection_caps_and_contract_authority_all_false():
    reg = _import_reg()
    import engine.sector_intelligence.finance_projection as fp
    research_schema = json.loads(RESEARCH_SCHEMA_PATH.read_text(encoding="utf-8"))
    required = set(research_schema["properties"]["authority"]["required"])
    assert set(reg.AUTHORITY) == set(fp._AUTHORITY_CAPS) == required
    assert all(value is False for value in reg.AUTHORITY.values())
    assert all(value is False for value in fp._AUTHORITY_CAPS.values())
    assert all(
        value.get("const") is False
        for value in research_schema["properties"]["authority"]["properties"].values()
        if isinstance(value, dict)
    )


def test_facts_anchor_slice_and_callables_are_the_modules_own():
    reg = _import_reg()
    facts = reg.FINANCE_REGISTRATION_FACTS
    assert facts.anchor_theme_id is None
    assert facts.slice_keys == ()
    assert facts.entry_kind == "sector_profile"


def test_view_field_list_quotes_shell_field_names_in_order():
    reg = _import_reg()
    assert reg._VERTICAL_REGISTRATION_FIELDS == (
        "anchor_theme_id", "slice_keys", "schema_id", "evidence_schema_id",
        "definition_version", "compose", "select_evidence", "load_bundle",
        "title_en", "title_zh", "note_en", "note_zh",
    )


# ---------------------------------------------------------------------------
# 2. Round-trip — exact refusal codes on both shell states (H1 ruling B, #7870)
# ---------------------------------------------------------------------------


def _theme_registrable_facts(reg):
    """A facts double that passes the adapter's pre-construction hold (string
    anchor, non-empty slices), for tests of the construction branches. The
    values follow the shell's canonical id grammar (lowercase a-z, 0-9,
    underscore) so the double is not itself a grammar violation; it still
    deliberately departs from the real facts' declared ``anchor_theme_id:
    None``. Every construction-branch test injects a fake registry, so the
    real shell's guards are never the subject here. The real Finance facts
    are a ``sector_profile`` and are held before construction (HOLD tests)."""
    import dataclasses
    return dataclasses.replace(
        reg.FINANCE_REGISTRATION_FACTS,
        anchor_theme_id="finance_test_double",
        slice_keys=("test_slice",),
    )


def test_shared_shell_registration_roundtrip_pinned_to_7870():
    """Checkout-state witness, no marker. Whatever this checkout holds, the
    round-trip MUST refuse with exactly one of the two typed codes, and the
    code must match the shell state actually observed — ``shared_shell_unavailable``
    while ``engine.market_ontology.theme_research_registry`` is absent
    (origin/main before #7870), ``vertical_registration_held:sector_profile``
    once it is present (#7870 and after). The inherited marker
    (``raises=ValueError``) could not tell those two states apart because the
    adapter's refusal subclasses ``ValueError``; the exact-string assertion
    below can.
    """
    import importlib.util
    reg = _import_reg()
    # Presence is decided by an instrument INDEPENDENT of the resolver under
    # test, so a resolver that wrongly reports "absent" on a carrier that has
    # the shell cannot hand this test its own expected answer.
    shell_present = importlib.util.find_spec(reg._SHELL_REGISTRY_MODULE) is not None
    with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
        reg.registration_entry_or_refusal()
    expected = (
        "vertical_registration_held:sector_profile"
        if shell_present
        else "shared_shell_unavailable"
    )
    assert str(excinfo.value) == expected


def test_shell_present_sector_profile_facts_are_held_before_construction():
    """With a present shell and the REAL Finance facts (``sector_profile``,
    ``anchor_theme_id=None``, ``slice_keys=()``), the adapter raises the typed
    hold and never constructs the shell's record — the hold does not depend
    on the shell's field count."""
    reg = _import_reg()
    constructed: list = []

    class FakeRegistration:
        def __init__(self, **kwargs: Any) -> None:
            constructed.append(kwargs)

    fake_registry = types.ModuleType("engine.market_ontology.theme_research_registry")
    fake_registry.VerticalRegistration = FakeRegistration
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "engine.market_ontology.theme_research_registry", fake_registry)
        with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
            reg.registration_entry_or_refusal()
    assert str(excinfo.value) == "vertical_registration_held:sector_profile"
    assert reg.VERTICAL_REGISTRATION_HELD_SECTOR_PROFILE == str(excinfo.value)
    assert constructed == []


@pytest.mark.parametrize(
    "anchor_theme_id, slice_keys",
    [
        pytest.param("finance_test_double", (), id="string-anchor-empty-slices"),
        pytest.param(None, ("test_slice",), id="none-anchor-nonempty-slices"),
    ],
)
def test_hold_requires_both_anchor_and_slices(anchor_theme_id, slice_keys):
    """Each half of the hold predicate is load-bearing on its own: facts that
    satisfy only one half are still held before construction."""
    import dataclasses
    reg = _import_reg()
    constructed: list = []

    class FakeRegistration:
        def __init__(self, **kwargs: Any) -> None:
            constructed.append(kwargs)

    fake_registry = types.ModuleType("engine.market_ontology.theme_research_registry")
    fake_registry.VerticalRegistration = FakeRegistration
    facts = dataclasses.replace(
        reg.FINANCE_REGISTRATION_FACTS,
        anchor_theme_id=anchor_theme_id,
        slice_keys=slice_keys,
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "engine.market_ontology.theme_research_registry", fake_registry)
        with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
            reg.registration_entry_or_refusal(facts=facts)
    assert str(excinfo.value) == "vertical_registration_held:sector_profile"
    assert constructed == []


def test_real_shell_field_gap_is_exactly_view_keys_and_build_query():
    """Pins the known share gap instead of hiding it. When the real shell
    resolves, its record carries exactly two fields beyond the adapter's
    quoted share — ``view_keys`` and ``build_query`` — and nothing in the
    share is missing from the shell. When the shell is absent this asserts
    that absence, so the test is informative on both states."""
    import dataclasses
    reg = _import_reg()
    cls = reg._resolve_vertical_registration_class()
    if cls is None:
        assert reg._import_shell_module(reg._SHELL_REGISTRY_MODULE) is None
        return
    shell_fields = {f.name for f in dataclasses.fields(cls)}
    share = set(reg._VERTICAL_REGISTRATION_FIELDS)
    assert shell_fields - share == {"view_keys", "build_query"}
    assert share - shell_fields == set()


def test_roundtrip_exact_refusal_code_is_shared_shell_unavailable(shell_absent):
    """B9: keep the exact-refusal-code assertion as a separate, plain
    test (no xfail marker) so the suite reports it cleanly when the
    shell stays absent, with no risk of the marker masking a regression."""
    reg = _import_reg()
    with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
        reg.registration_entry_or_refusal()
    assert str(excinfo.value) == "shared_shell_unavailable"


def test_roundtrip_injected_registry_raising_value_error_yields_refusal_with_exception_name():
    reg = _import_reg()

    class FakeRegistration:
        def __init__(self, **_kwargs: Any) -> None:
            raise ValueError("synthetic signature drift")

    fake_registry = types.ModuleType("engine.market_ontology.theme_research_registry")
    fake_registry.VerticalRegistration = FakeRegistration
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "engine.market_ontology.theme_research_registry", fake_registry)
        with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
            reg.registration_entry_or_refusal(facts=_theme_registrable_facts(reg))
    assert str(excinfo.value) == "vertical_registration_refused:ValueError"


def test_roundtrip_typeerror_propagates_uncaught():
    reg = _import_reg()

    class FakeRegistration:
        def __init__(self, **_kwargs: Any) -> None:
            raise TypeError("synthetic §8 signature drift")

    fake_registry = types.ModuleType("engine.market_ontology.theme_research_registry")
    fake_registry.VerticalRegistration = FakeRegistration
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "engine.market_ontology.theme_research_registry", fake_registry)
        with pytest.raises(TypeError):
            reg.registration_entry_or_refusal(facts=_theme_registrable_facts(reg))


def test_roundtrip_accepting_shell_returns_entry_with_kwargs_subset():
    reg = _import_reg()

    captured: dict = {}

    class FakeRegistration:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    fake_registry = types.ModuleType("engine.market_ontology.theme_research_registry")
    fake_registry.VerticalRegistration = FakeRegistration
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "engine.market_ontology.theme_research_registry", fake_registry)
        entry = reg.registration_entry_or_refusal(facts=_theme_registrable_facts(reg))
    assert isinstance(entry, FakeRegistration)
    expected_keys = set(reg._VERTICAL_REGISTRATION_FIELDS)
    assert set(captured) == expected_keys
    assert captured["schema_id"] == reg.PROFILE_ID
    assert captured["evidence_schema_id"] == reg.EVIDENCE_SCHEMA_ID
    assert captured["definition_version"] == reg.DEFINITION_VERSION
    # The adapter forwards the facts it was handed verbatim; anchorless facts
    # never reach this branch (held before construction, H1 ruling B).
    assert captured["anchor_theme_id"] == "finance_test_double"
    assert captured["slice_keys"] == ("test_slice",)


# ---------------------------------------------------------------------------
# 3. Compose happy path
# ---------------------------------------------------------------------------


def test_compose_happy_path_envelope_validates_and_dossier_validates():
    from engine.sector_intelligence.contracts import validate_contract
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context()
    envelope = reg.compose(query, bundle)
    # validate via the project's own registry so $ref lookups stay in-memory
    validate_contract(envelope, contract_id=reg.PROFILE_ID, repo_root=str(REPO_ROOT))
    validate_contract(
        envelope["dossier"],
        contract_id="finance_intelligence_read_model.v1",
        repo_root=str(REPO_ROOT),
    )
    assert envelope["schema"] == reg.PROFILE_ID
    assert envelope["definition_version"] == reg.DEFINITION_VERSION
    assert envelope["request"]["profile_id"] == reg.PROFILE_ID
    assert envelope["request"]["sector_ref"] == reg.SECTOR_REF
    assert envelope["request"]["view"] == "dossier"
    assert envelope["request"]["time_mode"] == "latest"
    assert envelope["assertion_refs"] == []


def test_compose_is_deterministic_byte_identical():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context()
    one = reg.compose(query, bundle)
    two = reg.compose(query, bundle)
    canonical = lambda d: json.dumps(d, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    assert canonical(one) == canonical(two)


def test_compose_passes_run_context_through_to_dossier_generated_at_and_knowledge_cutoff():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context()
    envelope = reg.compose(query, bundle)
    dossier = envelope["dossier"]
    # M4: parser normalises both Z and offset forms to one tz-aware
    # datetime, so the dossier emits +00:00 (the canonical UTC form) —
    # the projection's _to_iso drops "Z" the moment tzinfo is set.
    assert dossier["generated_at"] == "2026-09-25T07:48:00+00:00"
    assert dossier["knowledge_cutoff"] == "2026-09-25T07:48:00+00:00"


def test_compose_emits_no_forbidden_keys_outside_authority_and_dossier_authority_caps():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context()
    envelope = reg.compose(query, bundle)
    import engine.sector_intelligence.finance_projection as fp
    forbidden = fp._FORBIDDEN_KEY_RE
    # walk envelope, allow forbidden keys only under authority / dossier.authority_caps
    def walk(node: Any, path: tuple = ()) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                under_authority = path == ("authority",) or path[:1] == ("dossier",) and path[-1] == "authority_caps"
                if forbidden.search(key):
                    assert under_authority, f"forbidden key {key!r} at {path + (key,)}"
                walk(value, path + (key,))
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, path + (index,))
    walk(envelope)


# ---------------------------------------------------------------------------
# 4. Limitations
# ---------------------------------------------------------------------------


def test_limitations_mark_every_absent_owner_input_field():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context()  # only run-context native ref; all other fields empty
    envelope = reg.compose(query, bundle)
    expected_absents = {
        "owner_input_absent:sector_dossier",
        "owner_input_absent:financial_packets",
        "owner_input_absent:expectation_observations",
        "owner_input_absent:market_observations",
        "owner_input_absent:basket_context",
        "owner_input_absent:macro_context",
        "owner_input_absent:identity_bindings",
        "owner_input_absent:source_records",
        "owner_input_absent:regime_breaks",
        "owner_input_absent:slice_catalog",
    }
    # theme_evidence is empty in this bundle too, so it gets its own absent marker
    expected_absents.add("owner_input_absent:theme_evidence")
    assert expected_absents.issubset(set(envelope["limitations"]))


def test_limitations_mark_unmapped_fields_and_foreign_native_ref_kinds_once_each(monkeypatch):
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    foreign_ref = {"kind": "foreign_kind", "value": "x"}
    bundle = _Bundle(
        assertions=(_assertion(),),
        identity_results=({"label": "x"},),
        event_workspaces=({"event_id": "e1"},),
        financial_packets=({"metric": "x"},),
        interpretation_blocks=({"interpretation_id": "i1"},),
        native_refs=(_synthetic_run_context_ref(), foreign_ref),
        omissions=("event_workspaces",),
    )
    # B3(c): a present assertion list with no resolver raises
    # shared_shell_unavailable. The limitations exercise is independent of
    # the resolver; a resolver that returns a non-conforming ref keeps
    # ``assertion_refs`` empty (so the dossier still reaches the
    # limitations step) while the limitations remain populated.
    _install_resolver_double(
        monkeypatch, reg, lambda _payload: "not-a-conforming-ref"
    )
    envelope = reg.compose(query, bundle)
    limitations = envelope["limitations"]
    assert limitations.count("owner_field_unmapped:identity_results") == 1
    assert limitations.count("owner_field_unmapped:financial_packets") == 1
    assert limitations.count("owner_field_unmapped:event_workspaces") == 1
    assert limitations.count("owner_field_unmapped:interpretation_blocks") == 1
    assert limitations.count("owner_field_unmapped:native_refs") == 1
    assert "owner_omission:event_workspaces" in limitations


def test_limitations_are_sorted_and_unique():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context()
    envelope = reg.compose(query, bundle)
    assert envelope["limitations"] == sorted(set(envelope["limitations"]))


# ---------------------------------------------------------------------------
# 5. Refusals — parametrized, one test per code path
# ---------------------------------------------------------------------------


def _refuse_compose(query: Any, bundle: Any, reg: Any) -> tuple[str, Exception]:
    try:
        reg.compose(query, bundle)
    except Exception as exc:  # noqa: BLE001 - either typed refusal or TypeError
        return str(exc), exc
    raise AssertionError("expected refusal")


@pytest.mark.parametrize("bad_sector_ref", [
    "sector:Financials",
    " sector:financials",
    "sector:financials ",
    "sector:finance",
])
def test_compose_sector_ref_must_equal_sector_financials_exactly(bad_sector_ref: str):
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=bad_sector_ref)
    bundle = _bundle_with_run_context()
    code, exc = _refuse_compose(query, bundle, reg)
    assert code == "not_available"


def test_compose_profile_id_must_equal_profile_id_constant():
    reg = _import_reg()
    query = _Query(profile_id="some_other_profile", sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context()
    code, _ = _refuse_compose(query, bundle, reg)
    assert code == "not_available"


def test_compose_anchor_keyed_query_without_profile_id_is_not_available():
    reg = _import_reg()
    # duck-typed query with no profile_id at all
    query = SimpleNamespace(
        sector_ref=reg.SECTOR_REF, view="dossier", time_mode="latest",
        source_cutoff=None, recorded_cutoff=None, offset=0, limit=50,
        expected_generation=None,
    )
    bundle = _bundle_with_run_context()
    code, _ = _refuse_compose(query, bundle, reg)
    assert code == "not_available"


def test_compose_system_replay_is_identity_vintage_unsupported():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF, time_mode="system_replay")
    bundle = _bundle_with_run_context()
    code, _ = _refuse_compose(query, bundle, reg)
    assert code == "identity_vintage_unsupported"


def test_compose_source_history_is_not_available():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF, time_mode="source_history")
    bundle = _bundle_with_run_context()
    code, _ = _refuse_compose(query, bundle, reg)
    assert code == "not_available"


def test_compose_latest_with_source_cutoff_is_not_available():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF, time_mode="latest",
                   source_cutoff="2026-09-25")
    bundle = _bundle_with_run_context()
    code, _ = _refuse_compose(query, bundle, reg)
    assert code == "not_available"


def test_compose_latest_with_recorded_cutoff_is_not_available():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF, time_mode="latest",
                   recorded_cutoff="2026-09-25")
    bundle = _bundle_with_run_context()
    code, _ = _refuse_compose(query, bundle, reg)
    assert code == "not_available"


def test_compose_negative_offset_is_offset_negative():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF, offset=-1)
    bundle = _bundle_with_run_context()
    code, _ = _refuse_compose(query, bundle, reg)
    assert code == "offset_negative"


def test_compose_limit_zero_is_limit_out_of_range():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF, limit=0)
    bundle = _bundle_with_run_context()
    code, _ = _refuse_compose(query, bundle, reg)
    assert code == "limit_out_of_range"


def test_compose_limit_101_is_limit_out_of_range():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF, limit=101)
    bundle = _bundle_with_run_context()
    code, _ = _refuse_compose(query, bundle, reg)
    assert code == "limit_out_of_range"


def test_compose_expected_generation_mismatch_is_generation_changed():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                   expected_generation="gen_" + ("0" * 32))
    bundle = _bundle_with_run_context()
    code, _ = _refuse_compose(query, bundle, reg)
    assert code == "generation_changed"


def test_compose_run_context_missing_is_sealed_input_unavailable():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _Bundle()  # no native_refs at all
    code, _ = _refuse_compose(query, bundle, reg)
    assert code == "sealed_input_unavailable:run_context"


def test_compose_run_context_duplicated_is_sealed_input_unavailable():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    ref = _synthetic_run_context_ref()
    bundle = _Bundle(native_refs=(ref, ref))
    code, _ = _refuse_compose(query, bundle, reg)
    assert code == "sealed_input_unavailable:run_context"


def test_compose_run_context_unparseable_is_sealed_input_unavailable():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bad_ref = {"kind": "finance_run_context", "generated_at": "garbage", "knowledge_cutoff": "still_garbage"}
    bundle = _Bundle(native_refs=(bad_ref,))
    code, _ = _refuse_compose(query, bundle, reg)
    assert code == "sealed_input_unavailable:run_context"


@pytest.mark.parametrize("clock", ["9999-12-31T23:00:00-05:00", "0001-01-01T01:00:00+05:00"])
def test_compose_run_context_with_no_instant_is_sealed_input_unavailable(clock):
    """A seal clock whose offset carries it outside the range of a datetime
    names no instant. The run context is refused with its typed code; it
    used to raise OverflowError."""
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    for field in ("generated_at", "knowledge_cutoff"):
        ref = dict(_synthetic_run_context_ref(), **{field: clock})
        code, _ = _refuse_compose(query, _Bundle(native_refs=(ref,)), reg)
        assert code == "sealed_input_unavailable:run_context", field


# ---------------------------------------------------------------------------
# 6. Generation
# ---------------------------------------------------------------------------


def test_generation_format_and_changes_with_rights_revision():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle_a = _bundle_with_run_context().__class__(
        rights_revision="r1",
        native_refs=(_synthetic_run_context_ref(),),
    )
    bundle_b = _bundle_with_run_context().__class__(
        rights_revision="r2",
        native_refs=(_synthetic_run_context_ref(),),
    )
    env_a = reg.compose(query, bundle_a)
    env_b = reg.compose(query, bundle_b)
    gen_a, gen_b = env_a["generation"], env_b["generation"]
    assert re.fullmatch(r"^gen_[0-9a-f]{32}$", gen_a)
    assert re.fullmatch(r"^gen_[0-9a-f]{32}$", gen_b)
    assert gen_a != gen_b


def test_generation_changes_with_revision_tuple():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle_a = _Bundle(
        revision_tuple=(("theme:card_networks", "rev1"),),
        rights_revision="r1",
        native_refs=(_synthetic_run_context_ref(),),
    )
    bundle_b = _Bundle(
        revision_tuple=(("theme:card_networks", "rev2"),),
        rights_revision="r1",
        native_refs=(_synthetic_run_context_ref(),),
    )
    gen_a = reg.compose(query, bundle_a)["generation"]
    gen_b = reg.compose(query, bundle_b)["generation"]
    assert gen_a != gen_b


def test_generation_is_insensitive_to_revision_tuple_order():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle_a = _Bundle(
        revision_tuple=(("k1", "v1"), ("k2", "v2")),
        rights_revision="r1",
        native_refs=(_synthetic_run_context_ref(),),
    )
    bundle_b = _Bundle(
        revision_tuple=(("k2", "v2"), ("k1", "v1")),
        rights_revision="r1",
        native_refs=(_synthetic_run_context_ref(),),
    )
    assert reg.compose(query, bundle_a)["generation"] == reg.compose(query, bundle_b)["generation"]


def test_generation_is_insensitive_to_run_context():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    ref_a = {"kind": "finance_run_context", "generated_at": "2026-09-25T07:48:00Z", "knowledge_cutoff": "2026-09-25T07:48:00Z"}
    ref_b = {"kind": "finance_run_context", "generated_at": "2030-01-01T00:00:00Z", "knowledge_cutoff": "2030-01-01T00:00:00Z"}
    bundle_a = _Bundle(rights_revision="r1", native_refs=(ref_a,))
    bundle_b = _Bundle(rights_revision="r1", native_refs=(ref_b,))
    assert reg.compose(query, bundle_a)["generation"] == reg.compose(query, bundle_b)["generation"]


# ---------------------------------------------------------------------------
# 7. Evidence — resolver double + synthetic assertions
# ---------------------------------------------------------------------------


def _passthrough_validator(payload: Any) -> dict:
    """The shell's ``validate_assertion`` returns a deep-copied plain dict."""
    return copy.deepcopy(dict(payload))


def _install_resolver_double(monkeypatch: pytest.MonkeyPatch, reg: Any, _ref: Any,
                             validator: Any = _passthrough_validator) -> None:
    """Install a fake ``engine.theme_graph.curation_assertion`` module that
    exports the two symbols the adapter uses: the resolver and the shell's
    validator."""
    fake = types.ModuleType("engine.theme_graph.curation_assertion")
    fake.source_ref_for = _ref  # callable
    fake.validate_assertion = validator
    monkeypatch.setitem(sys.modules, "engine.theme_graph.curation_assertion", fake)


def _ref_for(theme_id: str, revision: str) -> str:
    return f"gmi-curation://{theme_id}/{revision}"


def test_select_evidence_returns_validating_envelope_with_deep_copied_assertion(monkeypatch):
    reg = _import_reg()
    revision = "gmirca_" + ("a" * 32)
    theme_id = "synthetic_theme"
    assertion = _assertion(revision=revision, theme_id=theme_id)
    captured: dict = {}

    def resolver(payload):
        captured["revision"] = payload.get("curation_revision")
        return _ref_for(theme_id, payload.get("curation_revision"))

    _install_resolver_double(monkeypatch, reg, resolver)
    monkeypatch.setitem(
        sys.modules,
        "engine.theme_graph.curation_assertion",
        sys.modules["engine.theme_graph.curation_assertion"],
    )

    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF, expected_generation=None)
    bundle = _bundle_with_run_context(assertions=(assertion,))
    # We have to supply an expected_generation so select_evidence passes; compute it
    full = reg.compose(query, bundle)
    query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                        expected_generation=full["generation"])
    envelope = reg.select_evidence(query_full, bundle, _ref_for(theme_id, revision))
    from engine.sector_intelligence.contracts import validate_contract
    validate_contract(envelope, contract_id=reg.EVIDENCE_SCHEMA_ID, repo_root=str(REPO_ROOT))
    assert envelope["schema"] == reg.EVIDENCE_SCHEMA_ID
    assert envelope["assertion_ref"] == _ref_for(theme_id, revision)
    assert envelope["assertion"] == copy.deepcopy(dict(assertion))
    assert envelope["assertion"] is not assertion


def test_select_evidence_unknown_well_formed_ref_is_not_available(monkeypatch):
    """R3: ``not_available`` is a SHARED refusal code — the test pins
    ``pytest.raises(ValueError)`` and the exact ``.code`` so it stays
    green once PR #7870 lands and the shell's :class:`ResearchRefusal`
    becomes the carrier type."""
    reg = _import_reg()
    revision = "gmirca_" + ("a" * 32)
    theme_id = "synthetic_theme"
    assertion = _assertion(revision=revision, theme_id=theme_id)
    _install_resolver_double(monkeypatch, reg,
                             lambda p: _ref_for(theme_id, p.get("curation_revision")))
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context(assertions=(assertion,))
    full = reg.compose(query, bundle)
    query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                        expected_generation=full["generation"])
    unknown_ref = _ref_for("other_theme", "gmirca_" + ("9" * 32))
    with pytest.raises(ValueError) as excinfo:
        reg.select_evidence(query_full, bundle, unknown_ref)
    assert getattr(excinfo.value, "code", None) == "not_available"
    assert str(excinfo.value) == "not_available"


def test_select_evidence_malformed_ref_is_not_available(monkeypatch):
    """R3: pins ``pytest.raises(ValueError)`` + exact ``.code`` for the
    SHARED ``not_available`` code (see test above)."""
    reg = _import_reg()
    _install_resolver_double(monkeypatch, reg, lambda p: "gmi-curation://x/y")
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context()
    full = reg.compose(query, bundle)
    query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                        expected_generation=full["generation"])
    with pytest.raises(ValueError) as excinfo:
        reg.select_evidence(query_full, bundle, "totally not a ref")
    assert getattr(excinfo.value, "code", None) == "not_available"
    assert str(excinfo.value) == "not_available"


def test_select_evidence_expected_generation_none_is_expected_generation_required(monkeypatch):
    """R3: pins ``pytest.raises(ValueError)`` + exact ``.code`` for the
    SHARED ``expected_generation_required`` code."""
    reg = _import_reg()
    revision = "gmirca_" + ("a" * 32)
    theme_id = "synthetic_theme"
    assertion = _assertion(revision=revision, theme_id=theme_id)
    _install_resolver_double(monkeypatch, reg,
                             lambda p: _ref_for(theme_id, p.get("curation_revision")))
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF, expected_generation=None)
    bundle = _bundle_with_run_context(assertions=(assertion,))
    with pytest.raises(ValueError) as excinfo:
        reg.select_evidence(query, bundle, _ref_for(theme_id, revision))
    assert getattr(excinfo.value, "code", None) == "expected_generation_required"
    assert str(excinfo.value) == "expected_generation_required"


def test_select_evidence_assertions_present_with_resolver_absent_is_shared_shell_unavailable(monkeypatch):
    reg = _import_reg()
    revision = "gmirca_" + ("a" * 32)
    theme_id = "synthetic_theme"
    assertion = _assertion(revision=revision, theme_id=theme_id)
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context(assertions=(assertion,))
    # B3(c): compose refuses on no-resolver+assertions; supply one that
    # returns a non-conforming ref so the dossier reaches the limitations
    # step. The select_evidence route still raises shared_shell_unavailable
    # when its OWN resolver fetch returns None — proving the explicit
    # defensive check there is not folded into the compose refusal.
    _install_resolver_double(monkeypatch, reg, lambda _payload: "not-conforming")
    full = reg.compose(query, bundle)
    # Now remove the resolver so select_evidence's own check fires.
    monkeypatch.delitem(sys.modules, "engine.theme_graph.curation_assertion", raising=False)
    # Restore a stub resolver of None by overwriting with one that yields None resolvable.
    def _null_resolver_module():
        m = ModuleType("engine.theme_graph.curation_assertion")
        m.source_ref_for = None  # callable check returns None -> resolver is None
        return m
    monkeypatch.setitem(
        sys.modules,
        "engine.theme_graph.curation_assertion",
        _null_resolver_module(),
    )
    query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                        expected_generation=full["generation"])
    with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
        reg.select_evidence(query_full, bundle, _ref_for(theme_id, revision))
    assert str(excinfo.value) == "shared_shell_unavailable"


def test_compose_assertions_present_with_resolver_absent_is_shared_shell_unavailable(shell_absent):
    """B3 (c): a non-empty ``assertions`` list with no resolver is the
    documented "the dossier could be wrong" case and the adapter must refuse
    ``shared_shell_unavailable`` rather than silently emit ``assertion_refs=[]``.
    """
    reg = _import_reg()
    revision = "gmirca_" + ("a" * 32)
    theme_id = "synthetic_theme"
    assertion = _assertion(revision=revision, theme_id=theme_id)
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context(assertions=(assertion,))
    with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
        reg.compose(query, bundle)
    assert str(excinfo.value) == "shared_shell_unavailable"


def test_select_evidence_resolver_absent_is_shared_shell_unavailable_even_without_assertions(shell_absent):
    """R10: the route's own resolver-absent check fires BEFORE the walk; with
    or without assertions, an absent resolver raises ``shared_shell_unavailable``
    at the explicit defensive check (not via the bundle-walk fallback)."""
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context()
    # Compose with no resolver and no assertions: succeeds, generation known.
    full = reg.compose(query, bundle)
    query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                        expected_generation=full["generation"])
    # A well-formed ref that no assertion in the bundle satisfies -> not_available.
    orphan_ref = _ref_for("synthetic_theme", "gmirca_" + ("9" * 32))
    with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
        reg.select_evidence(query_full, bundle, orphan_ref)
    assert str(excinfo.value) == "shared_shell_unavailable"


def test_select_evidence_stale_generation_with_malformed_ref_is_generation_changed(monkeypatch):
    """R4 (packet order): with a STALE expected_generation AND a malformed
    ``assertion_ref``, ``select_evidence`` raises ``generation_changed`` —
    the generation check runs BEFORE the ``assertion_ref`` pattern check.

    RED on 1d307ec0: the old order ran the pattern check first, so the
    code surfaced as ``not_available`` here. On the new head the assertion
    ref is never examined because the generation mismatch short-circuits.
    """
    reg = _import_reg()
    _install_resolver_double(monkeypatch, reg, lambda _p: "gmi-curation://x/y")
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                   expected_generation="gen_" + ("0" * 32))  # stale
    bundle = _bundle_with_run_context()
    with pytest.raises(ValueError) as excinfo:
        reg.select_evidence(query, bundle, "totally not a ref")
    assert getattr(excinfo.value, "code", None) == "generation_changed"
    assert str(excinfo.value) == "generation_changed"


def test_select_evidence_none_generation_with_malformed_ref_is_expected_generation_required(monkeypatch):
    """R4 (packet order): with a None ``expected_generation`` AND a malformed
    ``assertion_ref``, ``select_evidence`` raises
    ``expected_generation_required`` — the None check runs BEFORE the
    pattern check. The malformed ref is irrelevant; the generation
    pin is checked first.

    Forward-protection: a future re-order that moved the pattern check
    above the None check would surface ``not_available`` here, and the
    assertion fails.
    """
    reg = _import_reg()
    _install_resolver_double(monkeypatch, reg, lambda _p: "gmi-curation://x/y")
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                   expected_generation=None)
    bundle = _bundle_with_run_context()
    with pytest.raises(ValueError) as excinfo:
        reg.select_evidence(query, bundle, "totally not a ref")
    assert getattr(excinfo.value, "code", None) == "expected_generation_required"
    assert str(excinfo.value) == "expected_generation_required"


def test_select_evidence_skips_assertion_whose_resolver_raises(monkeypatch):
    reg = _import_reg()
    revision_a = "gmirca_" + ("a" * 32)
    revision_b = "gmirca_" + ("b" * 32)
    theme_id = "synthetic_theme"
    a = _assertion(revision=revision_a, theme_id=theme_id)
    b = _assertion(revision=revision_b, theme_id=theme_id)

    def resolver(payload):
        if payload.get("curation_revision") == revision_a:
            raise RuntimeError("synthetic resolver failure")
        return _ref_for(theme_id, payload.get("curation_revision"))

    _install_resolver_double(monkeypatch, reg, resolver)
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context(assertions=(a, b))
    full = reg.compose(query, bundle)
    # compose also calls the resolver; assertion ``a`` is skipped on failure
    consumed = {entry["curation_revision"] for entry in full["assertion_refs"]}
    assert revision_a not in consumed and revision_b in consumed
    query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                        expected_generation=full["generation"])
    envelope = reg.select_evidence(query_full, bundle, _ref_for(theme_id, revision_b))
    assert envelope["assertion"]["curation_revision"] == revision_b


def test_select_evidence_non_string_revision_is_never_selectable(monkeypatch):
    """B2: select_evidence rejects an assertion whose ``curation_revision`` is
    not a str — even when the resolver returns a PATTERN-VALID ref.

    On the previous head (352465e3) the same scenario passed only because the
    pattern check rejected the malformed ref BEFORE the walk logic; the
    isinstance-revision path was never reached. Here the resolver returns a
    pattern-valid ref so the walk actually runs and we observe the isinstance
    filter refusing the integer revision.
    """
    reg = _import_reg()
    import hashlib

    bad_assertion = _assertion(revision="gmirca_" + ("a" * 32))
    bad_assertion["curation_revision"] = 12345  # type: ignore[assignment]
    # Build a deterministic PATTERN-VALID ref for the integer revision.
    digest = hashlib.sha256(str(12345).encode()).hexdigest()[:32]
    target_ref = _ref_for("synthetic_theme", "gmirca_" + digest)

    def resolver(_payload):
        return target_ref

    _install_resolver_double(monkeypatch, reg, resolver)
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context(assertions=(bad_assertion,))
    full = reg.compose(query, bundle)
    query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                        expected_generation=full["generation"])
    with pytest.raises(ValueError) as excinfo:
        reg.select_evidence(query_full, bundle, target_ref)
    assert getattr(excinfo.value, "code", None) == "not_available"
    assert str(excinfo.value) == "not_available"


# ---------------------------------------------------------------------------
# 8. Loader
# ---------------------------------------------------------------------------


def test_load_bundle_absent_binding_is_shared_shell_unavailable(shell_absent):
    """R5: with the binding module absent, ``load_bundle`` raises a
    :class:`FinanceRegistrationRefusal` whose ``.code`` is the bare
    ``shared_shell_unavailable`` — no whitespace in the code, mirroring
    :class:`ResearchRefusal`'s ``str(exc) == exc.code`` contract."""
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    with pytest.raises(ValueError) as excinfo:
        reg.load_bundle(query)
    assert getattr(excinfo.value, "code", None) == "shared_shell_unavailable"
    assert str(excinfo.value) == "shared_shell_unavailable"
    assert " " not in excinfo.value.code


def test_load_bundle_with_binding_double_raises_the_bindings_bundle_unavailable_directly():
    """R5: when the binding module IS present and exposes a usable
    :class:`BundleUnavailable` Exception subclass, ``load_bundle`` raises
    that class DIRECTLY (no raise/catch/re-raise, no Finance refusal in
    between). The message starts with the ``finance_owner_loader_pending``
    prefix so the carrier classifies it, and the body names point (a) of
    PR #7780 comment 5828668393 and R4. The shell maps
    :class:`BundleUnavailable` to its fixed private 503 envelope — see
    ``engine/market_ontology/theme_research_binding.py``.
    """
    reg = _import_reg()

    class _BundleUnavailable(Exception):
        pass

    fake = types.ModuleType("engine.market_ontology.theme_research_binding")
    fake.BundleUnavailable = _BundleUnavailable
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "engine.market_ontology.theme_research_binding", fake)
        with pytest.raises(_BundleUnavailable) as excinfo:
            reg.load_bundle(_Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF))
    msg = str(excinfo.value)
    assert msg.startswith("finance_owner_loader_pending")
    assert "5828668393" in msg and "R4" in msg
    # And it is NOT a FinanceRegistrationRefusal — the adapter did not
    # wrap the binding exception.
    assert not isinstance(excinfo.value, reg.FinanceRegistrationRefusal)


def test_load_bundle_with_binding_double_without_bundle_unavailable_type_is_shared_shell_unavailable():
    """R5: when the binding module is present but exposes no usable
    :class:`BundleUnavailable` type, ``load_bundle`` raises the typed
    Finance refusal with the bare ``shared_shell_unavailable`` code.
    Replaces today's test:891 which locked in the wrong behaviour under
    the round-1 M3 ruling (now superseded)."""
    reg = _import_reg()

    fake = types.ModuleType("engine.market_ontology.theme_research_binding")
    # No BundleUnavailable attribute — deliberately empty.
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "engine.market_ontology.theme_research_binding", fake)
        with pytest.raises(ValueError) as excinfo:
            reg.load_bundle(_Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF))
    assert getattr(excinfo.value, "code", None) == "shared_shell_unavailable"
    assert str(excinfo.value) == "shared_shell_unavailable"


def test_finance_registration_refusal_class_contract_holds_for_every_call_site():
    """R5 (class contract): ``str(exc) == exc.code`` with no whitespace in
    ``.code`` for every refusal the adapter can raise. The call sites are read
    from the adapter's own source, so a site that passes a sentence goes red
    here; a list of codes written into this test would pass whatever the
    adapter raised (the round-2 version did, on 1d307ec0's sentence code)."""
    import ast

    reg = _import_reg()
    err = reg.FinanceRegistrationRefusal("some_code")
    assert isinstance(err, ValueError)
    assert str(err) == err.code == "some_code"

    tree = ast.parse(Path(reg.__file__).read_text(encoding="utf-8"))
    refusal_names = {"FinanceRegistrationRefusal", "_refuse"}
    # The walk below reads CALLS of the two names, so any other use carries a
    # code past it: an alias (``_R = FinanceRegistrationRefusal``), a
    # bare-class ``raise``, the class handed to a factory. Every use must be
    # the callee of a call (review F4).
    callees = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in refusal_names:
            assert id(node) in callees, f"line {node.lineno}: {node.id} used other than as a callee"
    refuse_def = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_refuse")
    inside_refuse = {id(n) for n in ast.walk(refuse_def)}
    codes = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in refusal_names):
            continue
        site = f"line {node.lineno}: {ast.unparse(node)}"
        assert len(node.args) == 1 and not node.keywords, site
        arg = node.args[0]
        if isinstance(arg, ast.Name) and arg.id == "code" and id(node) in inside_refuse:
            continue  # _refuse forwarding its own parameter; a variable anywhere else is no literal
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            code = arg.value
        elif isinstance(arg, ast.JoinedStr):
            # f"<prefix>:{type(exc).__name__}"; a class name carries no whitespace.
            assert all(isinstance(v, ast.Constant) or ast.unparse(v.value) == "type(exc).__name__"
                       for v in arg.values), site
            code = "".join(v.value for v in arg.values if isinstance(v, ast.Constant))
        else:
            raise AssertionError(f"refusal code is not a literal: {site}")
        assert code and not any(ch.isspace() for ch in code), site
        exc = reg.FinanceRegistrationRefusal(code)
        assert str(exc) == exc.code == code
        codes.append(code)
    # Positive control: the walk reached the adapter's raise sites.
    assert len(codes) >= 10, codes

# ---------------------------------------------------------------------------
# 9. Contracts
# ---------------------------------------------------------------------------


def test_both_schemas_pass_draft_2020_12_check_schema():
    for path in (RESEARCH_SCHEMA_PATH, EVIDENCE_SCHEMA_PATH):
        schema = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)


def test_both_contract_ids_are_discovered_by_the_registry():
    from engine.sector_intelligence.contracts import discover_contract_schemas
    schemas = discover_contract_schemas(str(REPO_ROOT))
    assert "finance_intelligence_research.v1" in schemas
    assert "finance_intelligence_research.evidence.v1" in schemas


@pytest.mark.parametrize("bad_envelope_factory,label", [
    (lambda reg: {**reg.compose(_Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF), _bundle_with_run_context()), "extra_top": "x"}, "extra_top_level"),
    (lambda reg: {**reg.compose(_Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF), _bundle_with_run_context()), "authority": {"rank": True, "gate": False, "size": False, "trade": False, "create_theme": False, "change_membership": False, "write_graph": False, "admit_source": False}}, "authority_rank_true"),
    (lambda reg: {**reg.compose(_Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF), _bundle_with_run_context()), "generation": "totally-bad-gen"}, "malformed_generation"),
    (lambda reg: {**reg.compose(_Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF), _bundle_with_run_context()), "dossier": {**reg.compose(_Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF), _bundle_with_run_context())["dossier"], "extra_dossier_top": 1}}, "dossier_extra_top"),
])
def test_research_contract_rejects_known_bad_payloads(bad_envelope_factory, label):
    reg = _import_reg()
    envelope = bad_envelope_factory(reg)
    from engine.sector_intelligence.contracts import ContractValidationError, validate_contract
    with pytest.raises(ContractValidationError):
        validate_contract(envelope, contract_id=reg.PROFILE_ID, repo_root=str(REPO_ROOT))


# ---------------------------------------------------------------------------
# 10. Light and pure imports + source discipline
# ---------------------------------------------------------------------------


def test_module_imports_no_heavy_modules_in_a_fresh_subprocess(tmp_path):
    heavy = ("requests", "pandas", "pyarrow", "numpy", "fastapi", "jinja2")
    driver = tmp_path / "driver.py"
    driver.write_text(
        "import sys\n"
        "sys.path.insert(0, %r)\n"
        "import engine.sector_intelligence.finance_research_registration as reg\n"
        "for name in %r:\n"
        "    assert name not in sys.modules, name\n"
        % (REPO_ROOT.as_posix(), heavy),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, "-B", str(driver)],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_module_source_contains_no_clock_or_network_or_secrets_calls():
    src = RESEARCH_MODULE_PATH.read_text(encoding="utf-8")
    forbidden = ("datetime.now", "utcnow", "time.time(", "os.environ", "socket", "urllib", "requests")
    for token in forbidden:
        assert token not in src, f"forbidden token in source: {token!r}"


# ---------------------------------------------------------------------------
# 11. Ruling B-block — adversarial coverage of every binding ruling item
# ---------------------------------------------------------------------------


def test_refuse_routes_shared_codes_through_resolved_shell_refusal_type(monkeypatch):
    """B1: When the shell's :class:`ResearchRefusal` resolves, ALL shared
    codes in :data:`_SHELL_SHARED_REFUSAL_CODES` raise the shell-typed
    refusal. Finance-only codes always raise
    :class:`FinanceRegistrationRefusal`."""
    reg = _import_reg()

    # Build a synthetic ResearchRefusal subclass the helper imports.
    class _SyntheticShellRefusal(ValueError):
        def __init__(self, code):
            super().__init__(code)
            self.code = code

    fake_shell = ModuleType("engine.market_ontology.semiconductor_theme_research")
    fake_shell.ResearchRefusal = _SyntheticShellRefusal
    monkeypatch.setitem(sys.modules, "engine.market_ontology.semiconductor_theme_research", fake_shell)

    # Shared code -> shell-typed refusal.
    with pytest.raises(_SyntheticShellRefusal) as excinfo:
        reg._refuse("not_available")
    assert str(excinfo.value) == "not_available"

    # finance_owner_loader_pending is Finance-only -> FinanceRegistrationRefusal.
    with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
        reg._refuse("finance_owner_loader_pending")
    assert str(excinfo.value) == "finance_owner_loader_pending"


def test_refuse_routes_finance_only_codes_through_adapter_refusal():
    """B1: Finance-only codes always raise ``FinanceRegistrationRefusal``."""
    reg = _import_reg()
    # Patch the shell lookup so it resolves (matches the importable case);
    # Finance-only codes must STILL be FinanceRegistrationRefusal.
    class _ShellRefusal(ValueError):
        pass

    fake_shell = ModuleType("engine.market_ontology.semiconductor_theme_research")
    fake_shell.ResearchRefusal = _ShellRefusal
    monkeypatch_ctx = pytest.MonkeyPatch()
    monkeypatch_ctx.setitem(sys.modules, "engine.market_ontology.semiconductor_theme_research", fake_shell)
    try:
        with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
            reg._refuse("shared_shell_unavailable")
        assert str(excinfo.value) == "shared_shell_unavailable"
        with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
            reg._refuse("sealed_input_unavailable:run_context")
        assert str(excinfo.value) == "sealed_input_unavailable:run_context"
        with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
            reg._refuse("vertical_registration_refused:ValueError")
        assert str(excinfo.value) == "vertical_registration_refused:ValueError"
        with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
            reg._refuse("finance_owner_loader_pending")
        assert str(excinfo.value) == "finance_owner_loader_pending"
    finally:
        monkeypatch_ctx.undo()


def test_compose_assertion_refs_sorted_by_curation_revision(monkeypatch):
    """B3 (b): the closed ``assertion_refs`` list is sorted by
    ``curation_revision`` regardless of input order."""
    reg = _import_reg()
    revision_a = "gmirca_" + ("b" * 32)
    revision_b = "gmirca_" + ("a" * 32)
    theme_id = "synthetic_theme"
    # Input in REVERSE alphabetical order.
    a = _assertion(revision=revision_a, theme_id=theme_id)
    b = _assertion(revision=revision_b, theme_id=theme_id)

    _install_resolver_double(monkeypatch, reg,
                             lambda p: _ref_for(theme_id, p.get("curation_revision")))
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context(assertions=(a, b))
    envelope = reg.compose(query, bundle)
    revisions = [entry["curation_revision"] for entry in envelope["assertion_refs"]]
    assert revisions == sorted(revisions)
    # And explicit ordering check.
    assert revisions.index(revision_b) < revisions.index(revision_a)


def test_an_assertion_retained_past_the_knowledge_cutoff_is_not_consumed(monkeypatch):
    """The run context's knowledge cutoff binds theme evidence. An assertion
    whose source was retained a minute after the cutoff instant is not a
    curation revision the dossier consumed: no assertion ref names it, and
    ``select_evidence`` refuses it as ``not_available``. Retained on the
    cutoff instant, the same assertion is named and selectable."""
    reg = _import_reg()
    theme_id = "synthetic_theme"
    known = _assertion(revision="gmirca_" + ("a" * 32), theme_id=theme_id)
    other_revision = "gmirca_" + ("b" * 32)
    _install_resolver_double(monkeypatch, reg,
                             lambda p: _ref_for(theme_id, p.get("curation_revision")))
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)

    def named_and_selected(retained_at: str) -> tuple[list[str], str | None]:
        other = _assertion(revision=other_revision, theme_id=theme_id)
        other["source"]["retained_at"] = retained_at
        bundle = _bundle_with_run_context(assertions=(known, other))
        envelope = reg.compose(query, bundle)
        named = [entry["curation_revision"] for entry in envelope["assertion_refs"]]
        query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                            expected_generation=envelope["generation"])
        try:
            selected = reg.select_evidence(query_full, bundle, _ref_for(theme_id, other_revision))
        except ValueError as exc:
            return named, getattr(exc, "code", None)
        return named, selected["assertion"]["curation_revision"]

    assert named_and_selected("2026-09-25T07:49:00Z") == (
        [known["curation_revision"]], "not_available")
    assert named_and_selected("2026-09-25T07:48:00Z") == (
        [known["curation_revision"], other_revision], other_revision)


def test_a_withheld_assertion_sharing_a_consumed_revision_is_never_named_or_selected(monkeypatch):
    """A curation revision does not identify one assertion: an assertion ref
    pairs it with a theme. An assertion the run's knowledge cutoff withholds
    is not named and not selectable, although an assertion the dossier read
    carries the same revision. Retained on the cutoff, it is named and
    selectable beside the other."""
    reg = _import_reg()
    revision = "gmirca_" + ("a" * 32)
    known = _assertion(revision=revision, theme_id="theme_known")
    _install_resolver_double(monkeypatch, reg,
                             lambda p: _ref_for(p["scope"]["canonical_theme_id"], p.get("curation_revision")))
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)

    def named_and_selected(retained_at: str) -> tuple[list[str], dict[str, str | None]]:
        other = _assertion(revision=revision, theme_id="theme_other")
        other["source"]["retained_at"] = retained_at
        bundle = _bundle_with_run_context(assertions=(known, other))
        envelope = reg.compose(query, bundle)
        named = sorted(entry["assertion_ref"] for entry in envelope["assertion_refs"])
        query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                            expected_generation=envelope["generation"])
        selected: dict[str, str | None] = {}
        for theme_id in ("theme_known", "theme_other"):
            try:
                evidence = reg.select_evidence(query_full, bundle, _ref_for(theme_id, revision))
            except ValueError as exc:
                selected[theme_id] = getattr(exc, "code", None)
            else:
                selected[theme_id] = evidence["assertion"]["scope"]["canonical_theme_id"]
        return named, selected

    assert named_and_selected("2026-09-25T07:49:00Z") == (
        [_ref_for("theme_known", revision)],
        {"theme_known": "theme_known", "theme_other": "not_available"})
    assert named_and_selected("2026-09-25T07:48:00Z") == (
        sorted([_ref_for("theme_known", revision), _ref_for("theme_other", revision)]),
        {"theme_known": "theme_known", "theme_other": "theme_other"})


def test_theme_evidence_the_cutoff_withholds_entirely_is_marked_absent(monkeypatch):
    """The limitations read theme evidence as the dossier read it. When the
    run's knowledge cutoff withholds every assertion, the dossier read no
    theme evidence, and the envelope says so with
    ``owner_input_absent:theme_evidence``. Retained on the cutoff, the same
    assertion is read and named, and the marker is gone."""
    reg = _import_reg()
    revision = "gmirca_" + ("a" * 32)
    theme_id = "synthetic_theme"
    _install_resolver_double(monkeypatch, reg,
                             lambda p: _ref_for(theme_id, p.get("curation_revision")))
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)

    def absent_and_named(retained_at: str) -> tuple[bool, list[str]]:
        assertion = _assertion(revision=revision, theme_id=theme_id)
        assertion["source"]["retained_at"] = retained_at
        envelope = reg.compose(query, _bundle_with_run_context(assertions=(assertion,)))
        named = [entry["curation_revision"] for entry in envelope["assertion_refs"]]
        return "owner_input_absent:theme_evidence" in envelope["limitations"], named

    assert absent_and_named("2026-09-25T07:49:00Z") == (True, [])
    assert absent_and_named("2026-09-25T07:48:00Z") == (False, [revision])


def test_evidence_envelope_assertion_is_deep_copied_and_mutable(monkeypatch):
    """B4: the evidence envelope's ``assertion`` is a deep copy — mutating
    the envelope MUST NOT reach back into the source assertion."""
    reg = _import_reg()
    revision = "gmirca_" + ("a" * 32)
    theme_id = "synthetic_theme"
    assertion = _assertion(revision=revision, theme_id=theme_id)

    _install_resolver_double(monkeypatch, reg,
                             lambda p: _ref_for(theme_id, p.get("curation_revision")))
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context(assertions=(assertion,))
    full = reg.compose(query, bundle)
    query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                        expected_generation=full["generation"])
    envelope = reg.select_evidence(query_full, bundle,
                                   _ref_for(theme_id, revision))
    # Mutate the envelope's nested object.
    envelope["assertion"]["scope"]["canonical_theme_id"] = "MUTATED"
    envelope["assertion"]["scope"]["added"] = "MUTATED_FIELD"
    # The original assertion is untouched.
    assert assertion["scope"]["canonical_theme_id"] == theme_id
    assert "added" not in assertion["scope"]
    # The bundle's assertions are also untouched.
    bundle_assertion = next(iter(bundle.assertions))
    assert bundle_assertion["scope"]["canonical_theme_id"] == theme_id
    assert "added" not in bundle_assertion["scope"]


def test_evidence_envelope_source_records_filter_to_selected_curation_revision_via_seam(monkeypatch):
    """R2 (seat ruling on the comparison key): the evidence envelope's
    ``source_records`` is filtered to entries whose ``evidence_ref`` equals
    the SELECTED ASSERTION's ``curation_revision`` string — NOT the
    ``gmi-curation://`` URI addressing form. Finance-owned source records
    reference the curation revision id; comparing against the gmi-curation://
    URI would never match. The comparison is exact ``str`` equality (no
    coercion).

    The adapter reads the dossier through a single seam —
    ``engine.sector_intelligence.finance_projection.compose_finance_projection``
    — that the test monkeypatches to inject five schema-valid T1
    ``source_record`` entries. Five records cover the comparison matrix:
    the selected revision matches twice, a different ``gmirca_`` revision,
    the shell's URI form (must NOT match), and ``None``. Only A and E
    pass.
    """
    from tests.test_finance_intelligence_projection import _schema_strict_source_record
    reg = _import_reg()
    selected_revision = "gmirca_" + ("a" * 32)
    other_revision = "gmirca_" + ("9" * 32)
    theme_id = "synthetic_theme"
    assertion = _assertion(revision=selected_revision, theme_id=theme_id)

    # Five records — varying ONLY record_id and evidence_ref from a valid T1 fixture.
    a = _schema_strict_source_record(
        slice_id="card_networks", record_id="rec-A",
        rights_state="DIRECT_DISPLAY_OK",
    )
    a["evidence_ref"] = selected_revision
    b = _schema_strict_source_record(
        slice_id="card_networks", record_id="rec-B",
        rights_state="DIRECT_DISPLAY_OK",
    )
    b["evidence_ref"] = other_revision
    c = _schema_strict_source_record(
        slice_id="card_networks", record_id="rec-C",
        rights_state="DIRECT_DISPLAY_OK",
    )
    c["evidence_ref"] = _ref_for(theme_id, selected_revision)  # the URI form
    d = _schema_strict_source_record(
        slice_id="card_networks", record_id="rec-D",
        rights_state="DIRECT_DISPLAY_OK",
    )
    d["evidence_ref"] = None
    e = _schema_strict_source_record(
        slice_id="card_networks", record_id="rec-E",
        rights_state="DIRECT_DISPLAY_OK",
    )
    e["evidence_ref"] = selected_revision

    injected_records = [a, b, c, d, e]
    expected_picked = [a, e]  # order preserved, only A and E match the selected revision

    # Build a base dossier via compose so the rest of the envelope is valid;
    # then patch its source_records to the five injected records.
    _install_resolver_double(monkeypatch, reg,
                             lambda p: _ref_for(theme_id, p.get("curation_revision")))
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context(assertions=(assertion,))
    base_envelope = reg.compose(query, bundle)
    base_envelope["dossier"]["source_records"] = injected_records
    base_gen = base_envelope["generation"]
    # Now re-validate the patched envelope so the source_records land in the
    # registry's accepted shape (the dossier schema allows arbitrary records
    # that match $defs/source_record).
    reg._registry().validate(reg.SCHEMA_ID, base_envelope)
    # Inject the same five records into the dossier the projection returns
    # by monkeypatching compose_finance_projection (the seam the adapter
    # composes through).
    import engine.sector_intelligence.finance_projection as fp
    real_fp_compose = fp.compose_finance_projection

    def patched_compose(inputs, generated_at, knowledge_cutoff):
        dossier = real_fp_compose(inputs, generated_at=generated_at, knowledge_cutoff=knowledge_cutoff)
        dossier["source_records"] = injected_records
        return dossier

    monkeypatch.setattr(fp, "compose_finance_projection", patched_compose)
    query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                        expected_generation=base_gen)
    envelope = reg.select_evidence(query_full, bundle, _ref_for(theme_id, selected_revision))
    # And the envelope validates (the round-trip survives the patch).
    reg._registry().validate(reg.EVIDENCE_SCHEMA_ID, envelope)
    # Strict equality on the source_records — verbatim dossier order.
    assert envelope["source_records"] == expected_picked
    # No record was silently coerced or merged.
    assert len(envelope["source_records"]) == 2
    assert envelope["source_records"][0]["record_id"] == "rec-A"
    assert envelope["source_records"][1]["record_id"] == "rec-E"


def test_limitations_run_context_only_bundle_has_no_unmapped_field_marker():
    """R9 (B5): a bundle holding ONLY the run-context native ref carries NO
    ``owner_field_unmapped:*`` entry — even though ``native_refs`` is in
    :data:`_OWNER_BUNDLE_UNMAPPED_FIELDS`. The test asserts FULL EQUALITY
    of the limitations list (not ``all(... startswith)`` or ``issubset``)
    so any silent addition or removal fails."""
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context()
    envelope = reg.compose(query, bundle)
    expected = [
        "owner_input_absent:basket_context",
        "owner_input_absent:expectation_observations",
        "owner_input_absent:financial_packets",
        "owner_input_absent:identity_bindings",
        "owner_input_absent:macro_context",
        "owner_input_absent:market_observations",
        "owner_input_absent:regime_breaks",
        "owner_input_absent:rights_snapshot",
        "owner_input_absent:sector_dossier",
        "owner_input_absent:slice_catalog",
        "owner_input_absent:source_records",
        "owner_input_absent:theme_evidence",
    ]
    assert envelope["limitations"] == expected, envelope["limitations"]


def test_import_shell_module_propagates_foreign_modulenotfounderror():
    """B6: only ``ModuleNotFoundError`` whose ``exc.name`` is one of the
    shell's own module names counts as absence. A foreign-name
    ``ModuleNotFoundError`` (e.g. a missing third-party dep a PRESENT
    shell depends on) propagates instead of collapsing to
    ``shared_shell_unavailable``."""
    reg = _import_reg()

    def fake_import(name, *args, **kwargs):
        if name == reg._SHELL_REGISTRY_MODULE:
            err = ModuleNotFoundError("No module named 'pydantic'")
            err.name = "pydantic"
            raise err
        # Fall back to the real import for everything else.
        raise RuntimeError(f"unexpected import {name!r}")

    monkeypatch_ctx = pytest.MonkeyPatch()
    monkeypatch_ctx.setattr(importlib, "import_module", fake_import)
    try:
        with pytest.raises(ModuleNotFoundError) as excinfo:
            reg._import_shell_module(reg._SHELL_REGISTRY_MODULE)
    finally:
        monkeypatch_ctx.undo()
    assert excinfo.value.name == "pydantic"


def test_authority_dict_is_mappingproxy_and_built_from_projection_caps():
    """B7: ``AUTHORITY`` is a ``MappingProxyType`` whose keys are the
    Finance projection's ``_AUTHORITY_CAPS`` and every value is False.
    No caller may mutate the dict."""
    from types import MappingProxyType as _MPT
    import engine.sector_intelligence.finance_projection as fp

    reg = _import_reg()
    assert isinstance(reg.AUTHORITY, _MPT)
    assert set(reg.AUTHORITY) == set(fp._AUTHORITY_CAPS)
    assert all(value is False for value in reg.AUTHORITY.values())
    # Frozen: assignment raises TypeError.
    with pytest.raises((TypeError, AttributeError)):
        reg.AUTHORITY["rank"] = True


def test_contract_registry_is_cached_across_compose_calls():
    """B8: a single ``ContractRegistry`` is built on first use and reused
    on every subsequent ``compose`` call. ``validate_contract`` builds a
    fresh one per call (the failure mode this rule replaces)."""
    reg = _import_reg()
    # The cached registry is the same object before/after many calls.
    cached_before = reg._registry()
    for _ in range(5):
        query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
        bundle = _bundle_with_run_context()
        reg.compose(query, bundle)
    cached_after = reg._registry()
    assert cached_before is cached_after


def test_envelope_validation_rejects_late_knowledge_cutoff_via_recursive_interval_walk():
    """R1: a single envelope validation (no separate dossier re-validation)
    MUST reject a body whose ``dossier.knowledge_cutoff`` is later than
    ``dossier.generated_at`` via the registry's RECURSIVE
    ``_interval_issues`` walk. The test is independent of
    ``additionalProperties`` (no new key introduced) and will FAIL if the
    interval walker ever stops descending into the nested dossier."""
    from engine.sector_intelligence.contracts import ContractValidationError
    reg = _import_reg()
    # 1. Build a valid envelope.
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context()
    envelope = reg.compose(query, bundle)
    # Sanity: the envelope currently has dossier.knowledge_cutoff ==
    # dossier.generated_at — no interval issue.
    assert envelope["dossier"]["knowledge_cutoff"] == envelope["dossier"]["generated_at"]
    # 2. Set dossier.knowledge_cutoff to a valid ISO-8601 instant LATER
    # than dossier.generated_at. Change nothing else.
    envelope["dossier"]["knowledge_cutoff"] = "2030-01-01T00:00:00+00:00"
    # 3. The cached registry's recursive validation MUST raise
    # ContractValidationError.
    with pytest.raises(ContractValidationError) as excinfo:
        reg._registry().validate(reg.SCHEMA_ID, envelope)
    # 4. The text ``interval.knowledge_cutoff`` MUST appear in the error —
    # either in the issues' codes or in str(exc). This pins the failure
    # mode to the recursive interval walker, NOT to additionalProperties.
    blob = str(excinfo.value)
    issue_codes = [getattr(issue, "code", "") for issue in excinfo.value.issues]
    assert "interval.knowledge_cutoff" in blob or "interval.knowledge_cutoff" in issue_codes, (
        f"expected interval.knowledge_cutoff issue; got codes={issue_codes!r} blob={blob[:300]!r}"
    )


# ---------------------------------------------------------------------------
# 12. Ruling M-block — generation/seal/omissions/privacy
# ---------------------------------------------------------------------------


def test_compose_runs_generation_check_before_owner_inputs():
    """M1: an expected_generation mismatch with a MISSING run-context
    refuses ``generation_changed`` BEFORE owner_inputs are built.

    R3: ``generation_changed`` is a SHARED refusal code — the test pins
    ``pytest.raises(ValueError)`` and the exact ``.code`` so it stays
    green once PR #7870 lands and the shell's :class:`ResearchRefusal`
    becomes the carrier type."""
    reg = _import_reg()
    query = _Query(
        profile_id=reg.PROFILE_ID,
        sector_ref=reg.SECTOR_REF,
        expected_generation="gen_" + ("0" * 32),
    )
    bundle = _Bundle()  # NO native_refs at all
    with pytest.raises(ValueError) as excinfo:
        reg.compose(query, bundle)
    assert getattr(excinfo.value, "code", None) == "generation_changed"
    assert str(excinfo.value) == "generation_changed"


def test_generation_distinguishes_int_and_string_values_per_shell_recipe():
    """M2: ``("k", 1)`` and ``("k", "1")`` produce different generations
    when run through the shell's verbatim recipe.
    ``sorted(list(pair) for pair in bundle.revision_tuple)`` uses Python's
    list() which preserves 1 vs "1" as different list items, and the
    serializer hashes them differently."""
    reg = _import_reg()
    query_a = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle_a = _Bundle(
        revision_tuple=(("k", 1),),
        rights_revision="r1",
        native_refs=(_synthetic_run_context_ref(),),
    )
    bundle_b = _Bundle(
        revision_tuple=(("k", "1"),),
        rights_revision="r1",
        native_refs=(_synthetic_run_context_ref(),),
    )
    gen_a = reg.compose(query_a, bundle_a)["generation"]
    gen_b = reg.compose(query_a, bundle_b)["generation"]
    assert gen_a != gen_b


def test_generation_propagates_malformed_revision_tuple_pair():
    """R7 (pinning test): the shell's verbatim recipe
    ``sorted(list(pair) for pair in bundle.revision_tuple)`` is the source
    of truth here. For two DIFFERENT fixed malformed revision inputs the
    generation fingerprint MUST equal the hard-coded literal computed from
    the current recipe AND differ between the two inputs.

    RED on a recipe change: the literals here are SHA-256 digests over the
    canonical-text of the frozen-fields-plus-revision-tuple blob. A recipe
    change (e.g. adding a wrapper, switching to ``sorted(tuple(pair)...)``,
    filtering, coercing, or swallowing the malformed entries) will move
    the digest, and the literal assertions below fail.

    Literals (computed by the recipe on the commit before this test was
    written; quoted in the PR body — note ``rights_revision="r1"``):

    * A: ``revision_tuple=(("k", "v", "extra"),)``
      → ``"gen_d3e77b1e32d1f13817b8e1ad4bf8f5b6"``
    * B: ``revision_tuple=(("x", "y", "z", "w"),)``
      → ``"gen_35b48ee3ff9371a4ce80c2fdf1c52d6a"``
    """
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)

    bundle_a = _Bundle(
        revision_tuple=(("k", "v", "extra"),),
        rights_revision="r1",
        native_refs=(_synthetic_run_context_ref(),),
    )
    bundle_b = _Bundle(
        revision_tuple=(("x", "y", "z", "w"),),
        rights_revision="r1",
        native_refs=(_synthetic_run_context_ref(),),
    )

    gen_a = reg.compose(query, bundle_a)["generation"]
    gen_b = reg.compose(query, bundle_b)["generation"]

    # The two fingerprints MUST differ — the two malformed inputs are
    # distinct, so the digest must reflect that.
    assert gen_a != gen_b
    # And each is pinned to the literal from the recipe. A change to the
    # recipe (filtering, wrapping, coercion, swallowing) will move the
    # digest and the assertion fails.
    assert gen_a == "gen_d3e77b1e32d1f13817b8e1ad4bf8f5b6", gen_a
    assert gen_b == "gen_35b48ee3ff9371a4ce80c2fdf1c52d6a", gen_b


def test_seal_clock_strips_no_whitespace():
    """M4: the strict seal clock parser does NOT strip whitespace — the
    sealed wire carries no stray spaces and whitespace would be contract
    drift. Leading/trailing whitespace is rejected."""
    reg = _import_reg()
    assert reg._parse_seal_clock(" 2026-09-25T07:48:00Z") is None
    assert reg._parse_seal_clock("2026-09-25T07:48:00Z ") is None


def test_seal_clock_rejects_wall_clock_24_00():
    """R10: ``24:00`` is a wall-clock form, not a valid ISO-8601 instant.
    The strict parser rejects it; ``T24`` and ``T24:00`` both fail."""
    reg = _import_reg()
    assert reg._parse_seal_clock("2026-09-25T24:00:00Z") is None
    assert reg._parse_seal_clock("2026-09-25T24:00:00+00:00") is None


def test_seal_clock_rejects_fractional_seconds_longer_than_six_digits():
    """R10: fractional seconds longer than six digits are rejected.
    Six-digit fractional seconds (microsecond resolution) are accepted;
    anything beyond that overflows the documented precision and would
    round-trip incorrectly through JSON."""
    reg = _import_reg()
    # Six digits — accepted.
    six = reg._parse_seal_clock("2026-09-25T07:48:00.123456Z")
    assert six is not None
    # Seven digits — rejected.
    assert reg._parse_seal_clock("2026-09-25T07:48:00.1234567Z") is None
    # And with an offset.
    assert reg._parse_seal_clock("2026-09-25T07:48:00.1234567+00:00") is None


def test_seal_clock_rejects_offset_without_colon():
    """R10: an offset REQUIRES the colon (``+HH:MM``). The ``+HHMM`` form
    (no colon) is rejected; the sealed wire and the projection's
    ``_to_iso`` always emit the colon form."""
    reg = _import_reg()
    assert reg._parse_seal_clock("2026-09-25T07:48:00+0000") is None


def test_seal_clock_interval_inconsistency_refuses_sealed_input():
    """M4: ``knowledge_cutoff`` later than ``generated_at`` surfaces as
    ``sealed_input_unavailable:run_context`` rather than as a generic
    ``ContractValidationError``."""
    reg = _import_reg()
    bad_ref = {
        "kind": "finance_run_context",
        "generated_at": "2026-09-25T07:48:00+00:00",
        "knowledge_cutoff": "2030-01-01T00:00:00+00:00",
    }
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _Bundle(native_refs=(bad_ref,))
    with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
        reg.compose(query, bundle)
    assert str(excinfo.value) == "sealed_input_unavailable:run_context"


def test_seal_clock_offset_form_normalises_to_utc():
    """M4: ``+HH:MM`` and ``Z`` inputs are normalised to ONE timezone-aware
    representation (UTC)."""
    reg = _import_reg()
    a = reg._parse_seal_clock("2026-09-25T07:48:00Z")
    b = reg._parse_seal_clock("2026-09-25T07:48:00+00:00")
    assert a is not None and b is not None
    assert a == b
    # Both have tzinfo.
    assert a.tzinfo is not None and b.tzinfo is not None


def test_omissions_blank_string_or_non_string_emits_unnamed_marker():
    """M7: a blank or non-string omission code surfaces as the single
    limitation ``owner_omission:unnamed`` (deduplicated). The string is
    checked against the envelope contract's limitations pattern
    (``type: string, minLength: 1``); ``owner_omission:unnamed`` always
    satisfies it so no sealed-input refusal is ever raised here."""
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _Bundle(
        native_refs=(_synthetic_run_context_ref(),),
        omissions=("", "macro_context", None, 0, "macro_context"),  # mixed bad + good, dedup
    )
    envelope = reg.compose(query, bundle)
    limitations = envelope["limitations"]
    assert "owner_omission:unnamed" in limitations
    assert "owner_omission:macro_context" in limitations
    # Dedup: exactly one unnamed marker.
    assert limitations.count("owner_omission:unnamed") == 1


def test_omissions_whitespace_only_string_emits_unnamed_marker():
    """R8 (M7 amendment): a whitespace-only omission (``"  "``) is blank
    under ``.strip() == ""`` and collapses to the single deduplicated
    limitation ``owner_omission:unnamed``. The contract's limitations
    pattern (``minLength: 1``) does NOT strip whitespace, so the pattern-
    or-refuse branch is unreachable under the current schema — kept that
    way by R8's RATIFIED note.
    """
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _Bundle(
        native_refs=(_synthetic_run_context_ref(),),
        omissions=("  ", "macro_context", "  "),  # two whitespace-only + one valid
    )
    envelope = reg.compose(query, bundle)
    limitations = envelope["limitations"]
    assert "owner_omission:unnamed" in limitations
    assert "owner_omission:macro_context" in limitations
    # Dedup: exactly one unnamed marker even with two whitespace-only entries.
    assert limitations.count("owner_omission:unnamed") == 1


# ---------------------------------------------------------------------------
# 13. Privacy — SECRET_* strings never leak into any envelope
# ---------------------------------------------------------------------------


def test_secret_strings_do_not_leak_into_any_envelope(monkeypatch):
    """Permanent privacy guard: bundle field values carrying SECRET_* strings
    (identity_results, event_workspaces, financial_packets,
    interpretation_blocks), an owner omission written as prose (review F5)
    and an extra ``private_note`` on the run context must NEVER appear in
    the compose or evidence envelope payloads."""
    reg = _import_reg()
    revision = "gmirca_" + ("a" * 32)
    theme_id = "synthetic_theme"
    assertion = _assertion(revision=revision, theme_id=theme_id)
    secret_bundle = _Bundle(
        revision_tuple=(("k", "v"),),
        rights_revision="r1",
        assertions=(assertion,),
        identity_results=({"label": "SECRET_IDENTITY"},),
        event_workspaces=({"event_id": "SECRET_EVENT"},),
        financial_packets=({"metric": "SECRET_FIN"},),
        interpretation_blocks=({"interpretation_id": "SECRET_INTERP"},),
        omissions=("SECRET_OMISSION client=ACME pos=+5MM", "client_acme_short_5mm_block"),
        native_refs=({
            "kind": "finance_run_context",
            "generated_at": "2026-09-25T07:48:00Z",
            "knowledge_cutoff": "2026-09-25T07:48:00Z",
            "private_note": "SECRET_PRIVATE_NOTE",
        },),
    )
    _install_resolver_double(monkeypatch, reg,
                             lambda p: _ref_for(theme_id, p.get("curation_revision")))
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    compose_env = reg.compose(query, secret_bundle)
    compose_blob = json.dumps(compose_env, sort_keys=True, ensure_ascii=False,
                              separators=(",", ":"), default=str)
    assert "SECRET_" not in compose_blob, compose_blob
    # Evidence envelope too.
    full = reg.compose(query, secret_bundle)
    query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                        expected_generation=full["generation"])
    evidence_env = reg.select_evidence(
        query_full, secret_bundle, _ref_for(theme_id, revision)
    )
    evidence_blob = json.dumps(evidence_env, sort_keys=True, ensure_ascii=False,
                               separators=(",", ":"), default=str)
    assert "SECRET_" not in evidence_blob, evidence_blob
    for blob in (compose_blob, evidence_blob):
        assert "client_acme" not in blob, blob


# ---------------------------------------------------------------------------
# 14. Round 3 -- the shell validator's copy (F2), omission names (F5), and
#     refusal typing that never imports the sibling for a Finance code (F6)
# ---------------------------------------------------------------------------


def _closed_shape_validator(payload: Any) -> dict:
    """Stands in for the shell's closed-schema validator: a deep copy holding
    only the keys the synthetic assertion shape declares."""
    declared = _assertion()
    data = {k: copy.deepcopy(v) for k, v in dict(payload).items() if k in declared}
    data["observation"] = {"value": copy.deepcopy(dict(payload)["observation"].get("value"))}
    return data


def _select_with_validator(monkeypatch: pytest.MonkeyPatch, reg: Any, assertion: dict,
                           validator: Any) -> Any:
    """Compose, then select the one synthetic assertion through a resolver
    double whose shell validator is ``validator``."""
    theme_id = assertion["scope"]["canonical_theme_id"]
    _install_resolver_double(monkeypatch, reg,
                             lambda p: _ref_for(theme_id, p.get("curation_revision")),
                             validator=validator)
    bundle = _bundle_with_run_context(assertions=(assertion,))
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                        expected_generation=reg.compose(query, bundle)["generation"])
    return reg.select_evidence(query_full, bundle,
                               _ref_for(theme_id, assertion["curation_revision"]))


def test_evidence_embeds_the_shell_validators_copy_not_the_raw_bundle_entry(monkeypatch):
    """F2: the envelope's ``assertion`` is an open object, so a raw copy
    carried every key the owner bundle held. It now carries exactly what the
    shell's ``validate_assertion`` returned for the matched entry."""
    reg = _import_reg()
    assertion = _assertion()
    assertion["private_extra"] = "SECRET_ASSERTION_EXTRA"
    assertion["observation"] = {"value": None, "private": "SECRET_NESTED"}
    seen: list = []

    def validator(payload):
        seen.append(copy.deepcopy(payload))
        return _closed_shape_validator(payload)

    envelope = _select_with_validator(monkeypatch, reg, assertion, validator)
    assert seen == [assertion]
    assert envelope["assertion"] == _closed_shape_validator(assertion) == _assertion()
    blob = json.dumps(envelope, sort_keys=True, ensure_ascii=False, default=str)
    assert "SECRET_" not in blob, blob


def test_evidence_refuses_an_assertion_the_shell_validator_rejects(monkeypatch):
    """F2: an assertion the validator rejects is never selectable, as in the
    shell's own selection. It shares the not-selected code, and the
    validator's message (which can quote the offending key) never escapes,
    not even as the refusal's chained context."""
    reg = _import_reg()

    def validator(_payload):
        raise ValueError("schema_violation: 'SECRET_ASSERTION_EXTRA' was unexpected")

    with pytest.raises(ValueError) as excinfo:
        _select_with_validator(monkeypatch, reg, _assertion(), validator)
    assert getattr(excinfo.value, "code", None) == "not_available"
    assert str(excinfo.value) == "not_available"
    assert excinfo.value.__context__ is None and excinfo.value.__cause__ is None


def _raises_keyerror(_payload):
    raise KeyError("observation")


def _returns_none(_payload):
    return None


@pytest.mark.parametrize("validator, broken", [(_raises_keyerror, KeyError), (_returns_none, TypeError)])
def test_evidence_lets_a_broken_validator_fail_as_itself(monkeypatch, validator, broken):
    """F2 / re-review N-b: only the validator's refusal type (a
    ``ValueError``) means "invalid". Any other failure, and a return that is
    not a mapping, is a broken shell and propagates, so it can never pass for
    an assertion that is merely not available."""
    reg = _import_reg()
    with pytest.raises(broken):
        _select_with_validator(monkeypatch, reg, _assertion(), validator)


@pytest.mark.parametrize("shape", ["attribute_absent", "not_callable"])
def test_evidence_without_the_shell_validator_is_shared_shell_unavailable(monkeypatch, shape):
    """F2: a resolver module with no callable ``validate_assertion`` cannot
    serve evidence; the adapter refuses rather than embed a raw copy."""
    reg = _import_reg()
    theme_id = "synthetic_theme"
    assertion = _assertion()
    _install_resolver_double(monkeypatch, reg,
                             lambda p: _ref_for(theme_id, p.get("curation_revision")),
                             validator=None)
    if shape == "attribute_absent":
        monkeypatch.delattr(sys.modules[reg._SHELL_RESOLVER_MODULE], "validate_assertion")
    bundle = _bundle_with_run_context(assertions=(assertion,))
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                        expected_generation=reg.compose(query, bundle)["generation"])
    with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
        reg.select_evidence(query_full, bundle, _ref_for(theme_id, assertion["curation_revision"]))
    assert str(excinfo.value) == "shared_shell_unavailable"


def test_an_owner_omission_reaches_the_envelope_only_as_a_declared_name():
    """F5 / re-review M1: omissions were emitted verbatim, and a snake_case
    shape filter still passed owner text spelled in snake_case. Only a name
    in the closed vocabulary (the owner inputs and bundle fields the adapter
    declares) passes; everything else collapses into one
    ``owner_omission:unrecognized`` marker, and a blank stays ``unnamed``."""
    reg = _import_reg()
    assert "financial_packets" in reg._OMISSION_NAMES
    assert reg._OMISSION_NAMES == set(reg._OWNER_INPUT_FIELDS) | set(reg._OWNER_BUNDLE_UNMAPPED_FIELDS)
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context(omissions=(
        "financial_packets",
        "event_workspaces",
        "client_acme_short_5mm_block",
        "SECRET_OMISSION client=ACME pos=+5MM",
        "Mixed_Case",
        "financial_packets ",
        "   ",
    ))
    envelope = reg.compose(query, bundle)
    markers = [m for m in envelope["limitations"] if m.startswith("owner_omission:")]
    assert markers == [
        "owner_omission:event_workspaces",
        "owner_omission:financial_packets",
        "owner_omission:unnamed",
        "owner_omission:unrecognized",
    ], markers
    blob = json.dumps(envelope, sort_keys=True, ensure_ascii=False, default=str)
    for leaked in ("client_acme", "SECRET", "ACME", "Mixed_Case"):
        assert leaked not in blob, leaked
    # Re-review N-a: an omission spelled like one of the adapter's own markers
    # is not a declared name, so it cannot pass as that marker.
    markers_only = reg.compose(query, _bundle_with_run_context(omissions=("unnamed", "unrecognized")))
    assert [m for m in markers_only["limitations"] if m.startswith("owner_omission:")] == [
        "owner_omission:unrecognized"]


class _FailingSiblingFinder:
    """Fails the sibling module's import at import time, as a present but
    broken shell would, and counts every attempt to import it."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.attempts = 0

    def find_spec(self, fullname, path=None, target=None):
        if fullname != self.name:
            return None
        self.attempts += 1
        return importlib.util.spec_from_loader(fullname, self)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        raise RuntimeError("sibling import-time failure")


def test_a_finance_only_refusal_never_imports_the_sibling_module(monkeypatch):
    """F6: ``_refuse`` imported the sibling module on every call, so an
    import-time failure inside a present shell retyped every Finance refusal.
    A Finance-only code no longer touches it; a shared code still consults
    the shell, so a broken present shell surfaces as itself, never as an
    absent one."""
    reg = _import_reg()
    finder = _FailingSiblingFinder(reg._SHELL_SIBLING_MODULE)
    monkeypatch.delitem(sys.modules, reg._SHELL_SIBLING_MODULE, raising=False)
    monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])
    for code in ("finance_owner_loader_pending", "shared_shell_unavailable"):
        assert code not in reg._SHELL_SHARED_REFUSAL_CODES
        with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
            reg._refuse(code)
        assert str(excinfo.value) == code
    assert finder.attempts == 0
    # Positive control: the finder does intercept the sibling's import.
    with pytest.raises(RuntimeError, match="sibling import-time failure"):
        reg._refuse("not_available")
    assert finder.attempts == 1
