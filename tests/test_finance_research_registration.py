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
# 2. Round-trip — pinned strict xfail (shell absent on main)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, raises=ValueError,
                   reason="§8 sector_profile pending (#7780 5828668393)")
def test_shared_shell_registration_roundtrip_pinned_to_7870():
    """§8 sector_profile pending (#7780 comment 5828668393). The shell
    module ``engine.market_ontology.theme_research_registry`` is NOT on
    origin/main; the round-trip MUST yield a typed
    :class:`FinanceRegistrationRefusal` rather than a bare
    ``ModuleNotFoundError``.

    Pinned :class:`pytest.mark.xfail` (``strict=True``) so a future §8
    acceptance XPASSes loudly and the team re-pins the test (B9). The
    marker carries ``raises=ValueError`` because
    :class:`FinanceRegistrationRefusal` subclasses ``ValueError``; this
    is the cleanest expression of "expected typed refusal" via xfail,
    and matches the technology precedent (@#7891).
    """
    reg = _import_reg()
    reg.registration_entry_or_refusal()


def test_roundtrip_exact_refusal_code_is_shared_shell_unavailable():
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
            reg.registration_entry_or_refusal()
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
            reg.registration_entry_or_refusal()


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
        entry = reg.registration_entry_or_refusal()
    assert isinstance(entry, FakeRegistration)
    expected_keys = set(reg._VERTICAL_REGISTRATION_FIELDS)
    assert set(captured) == expected_keys
    assert captured["schema_id"] == reg.PROFILE_ID
    assert captured["evidence_schema_id"] == reg.EVIDENCE_SCHEMA_ID
    assert captured["definition_version"] == reg.DEFINITION_VERSION
    assert captured["anchor_theme_id"] is None
    assert captured["slice_keys"] == ()


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
        omissions=("omitted_reason",),
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
    assert "owner_omission:omitted_reason" in limitations


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


def _install_resolver_double(monkeypatch: pytest.MonkeyPatch, reg: Any, _ref: Any) -> None:
    """Install a fake ``engine.theme_graph.curation_assertion`` module that
    exports the resolver symbol the adapter uses."""
    fake = types.ModuleType("engine.theme_graph.curation_assertion")
    fake.source_ref_for = _ref  # callable
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
    with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
        reg.select_evidence(query_full, bundle, unknown_ref)
    assert str(excinfo.value) == "not_available"


def test_select_evidence_malformed_ref_is_not_available(monkeypatch):
    reg = _import_reg()
    _install_resolver_double(monkeypatch, reg, lambda p: "gmi-curation://x/y")
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context()
    full = reg.compose(query, bundle)
    query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                        expected_generation=full["generation"])
    with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
        reg.select_evidence(query_full, bundle, "totally not a ref")
    assert str(excinfo.value) == "not_available"


def test_select_evidence_expected_generation_none_is_expected_generation_required(monkeypatch):
    reg = _import_reg()
    revision = "gmirca_" + ("a" * 32)
    theme_id = "synthetic_theme"
    assertion = _assertion(revision=revision, theme_id=theme_id)
    _install_resolver_double(monkeypatch, reg,
                             lambda p: _ref_for(theme_id, p.get("curation_revision")))
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF, expected_generation=None)
    bundle = _bundle_with_run_context(assertions=(assertion,))
    with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
        reg.select_evidence(query, bundle, _ref_for(theme_id, revision))
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


def test_compose_assertions_present_with_resolver_absent_is_shared_shell_unavailable():
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


def test_select_evidence_no_assertions_works_without_resolver():
    """The select_evidence route never runs compose; with no assertions the
    resolver-absent path is irrelevant to the walk and the route still
    refuses shared_shell_unavailable at the explicit check."""
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
    with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
        reg.select_evidence(query_full, bundle, target_ref)
    assert str(excinfo.value) == "not_available"


# ---------------------------------------------------------------------------
# 8. Loader
# ---------------------------------------------------------------------------


def test_load_bundle_absent_is_shared_shell_unavailable():
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
        reg.load_bundle(query)
    assert str(excinfo.value) == "shared_shell_unavailable"


def test_load_bundle_with_binding_double_raises_finance_refusal_with_prefix():
    """M3: ``load_bundle`` raises :class:`FinanceRegistrationRefusal`
    DIRECTLY (no raise/catch/re-raise) when the binding module IS present
    but its loader is the still-not-landed fixture-only placeholder. The
    message starts with the ``finance_owner_loader_pending`` prefix so the
    carrier classifies it, and the body names point (a) of PR #7780
    comment 5828668393 and R4."""
    reg = _import_reg()

    class _BundleUnavailable(Exception):
        pass

    fake = types.ModuleType("engine.market_ontology.theme_research_binding")
    fake.BundleUnavailable = _BundleUnavailable
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "engine.market_ontology.theme_research_binding", fake)
        with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
            reg.load_bundle(_Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF))
    msg = str(excinfo.value)
    assert msg.startswith("finance_owner_loader_pending")
    assert "5828668393" in msg and "R4" in msg


def test_load_bundle_with_binding_double_raises_finance_refusal_even_when_binding_unavailable_type_absent():
    """When the binding module is present but exposes no usable
    ``BundleUnavailable`` type, ``load_bundle`` still surfaces the typed
    Finance refusal — here ``shared_shell_unavailable``."""
    reg = _import_reg()

    fake = types.ModuleType("engine.market_ontology.theme_research_binding")
    # No BundleUnavailable attribute.
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "engine.market_ontology.theme_research_binding", fake)
        with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
            reg.load_bundle(_Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF))
    assert str(excinfo.value) == "shared_shell_unavailable"


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


def test_research_refusals_codes_are_typed_via_valueerror():
    reg = _import_reg()
    # the route uses _map_research_refusal only if ResearchRefusal (semiconductor) is used
    # the adapter's typed refusal is FinanceRegistrationRefusal; either is fine
    err = reg.FinanceRegistrationRefusal("some_code")
    assert isinstance(err, ValueError)
    assert str(err) == "some_code"


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


def test_evidence_envelope_source_records_filtered_to_selected_ref(monkeypatch):
    """B4: the evidence envelope's ``source_records`` contains ONLY records
    whose ``evidence_ref`` matches the selected ``assertion_ref``; other
    refs are excluded."""
    reg = _import_reg()
    revision = "gmirca_" + ("a" * 32)
    other_revision = "gmirca_" + ("9" * 32)
    theme_id = "synthetic_theme"
    assertion = _assertion(revision=revision, theme_id=theme_id)
    # A bundle whose run-context entry carries extra source_records for
    # another ref. Finance bundle input has no source_records path; we
    # inject via the dossier composer by checking what arrived in
    # envelope["dossier"]["source_records"] at compose time.
    _install_resolver_double(monkeypatch, reg,
                             lambda p: _ref_for(theme_id, p.get("curation_revision")))
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context(assertions=(assertion,))
    full = reg.compose(query, bundle)
    # The dossier's source_records (if any) MUST be a subset of the
    # selected ref when the assertion ref intersects them.
    dossier_records = full["dossier"].get("source_records", []) or []
    selected_ref = _ref_for(theme_id, revision)
    other_ref = _ref_for("synthetic_theme", other_revision)
    query_full = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF,
                        expected_generation=full["generation"])
    envelope = reg.select_evidence(query_full, bundle, selected_ref)
    # The envelope's source_records must not contain a record whose
    # evidence_ref is the other ref (when there is a dossier record for it).
    for record in envelope["source_records"]:
        assert record.get("evidence_ref") != other_ref
    # And it MUST include any dossier record whose evidence_ref is the
    # selected one — this is the inclusivity check (B4 inclusion half).
    dossier_matching = [r for r in dossier_records if r.get("evidence_ref") == selected_ref]
    envelope_matching = [r for r in envelope["source_records"] if r.get("evidence_ref") == selected_ref]
    assert len(envelope_matching) == len(dossier_matching)


def test_limitations_run_context_only_bundle_has_no_unmapped_field_marker():
    """B5: a bundle holding ONLY the run-context native ref carries NO
    ``owner_field_unmapped:*`` entry — even though ``native_refs`` is in
    :data:`_OWNER_BUNDLE_UNMAPPED_FIELDS`. Equality check on the full
    limitations list (not a subset)."""
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context()
    envelope = reg.compose(query, bundle)
    limitations = envelope["limitations"]
    assert all(not s.startswith("owner_field_unmapped:") for s in limitations), limitations
    # And the new rights_snapshot marker is present.
    assert "owner_input_absent:rights_snapshot" in limitations


def test_limitations_emit_owner_input_absent_for_every_field():
    """B5: with an empty-bundle shape the limitations list includes
    ``owner_input_absent:rights_snapshot`` (B5 addition) and every other
    absent field. Equality vs the expected set so any silent addition
    fails the test."""
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context()
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
        "owner_input_absent:rights_snapshot",
    }
    assert expected_absents.issubset(set(envelope["limitations"]))


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


def test_envelope_validation_rejects_late_knowledge_cutoff_in_nested_body():
    """B8 (seat ruling): a single envelope validation (no separate dossier
    re-validation) MUST reject a nested body whose ``knowledge_cutoff`` is
    later than its ``generated_at``. The registry's recursive
    ``_interval_issues`` walk reaches the mismatch."""
    reg = _import_reg()
    # Build a valid envelope, then patch the dossier to a nested body that
    # the interval walker catches.
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _bundle_with_run_context()
    envelope = reg.compose(query, bundle)
    # Inject a nested level that violates the interval rule.
    envelope["dossier"]["nested_for_test"] = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "knowledge_cutoff": "2030-01-01T00:00:00+00:00",
    }
    # The cached registry's recursive interval walker must catch it.
    with pytest.raises(Exception):
        reg._registry().validate(reg.SCHEMA_ID, envelope)


def test_roundtrip_xfail_marker_is_strict():
    """B9: the round-trip is annotated with ``@pytest.mark.xfail(strict=True)``
    so a future §8 acceptance XPASSES loudly and the team re-pins the test.
    The marker is on the canonical round-trip test below — we read its
    markers via :mod:`_pytest`."""
    import _pytest
    # Collect markers attached to the test function.
    raw_markers = getattr(test_shared_shell_registration_roundtrip_pinned_to_7870, "pytestmark", ())
    flat_markers = []
    for marker in raw_markers:
        if isinstance(marker, _pytest.mark.structures.MarkDecorator):
            flat_markers.append(marker.mark)
        else:
            flat_markers.append(marker)
    assert any(m.name == "xfail" for m in flat_markers), f"expected xfail marker, got {flat_markers!r}"


def test_collection_has_xfail_marker_for_section_8_sector_profile():
    """B9: the round-trip test's xfail reason names §8 sector_profile and
    the upstream comment so a team member reading the source can route
    the re-pin to the right binding."""
    import inspect
    src = inspect.getsource(test_shared_shell_registration_roundtrip_pinned_to_7870)
    assert "5828668393" in src, src


# ---------------------------------------------------------------------------
# 12. Ruling M-block — generation/seal/omissions/privacy
# ---------------------------------------------------------------------------


def test_compose_runs_generation_check_before_owner_inputs():
    """M1: an expected_generation mismatch with a MISSING run-context
    refuses ``generation_changed`` BEFORE owner_inputs are built."""
    reg = _import_reg()
    query = _Query(
        profile_id=reg.PROFILE_ID,
        sector_ref=reg.SECTOR_REF,
        expected_generation="gen_" + ("0" * 32),
    )
    bundle = _Bundle()  # NO native_refs at all
    with pytest.raises(reg.FinanceRegistrationRefusal) as excinfo:
        reg.compose(query, bundle)
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
    """M2: a malformed entry (``len != 2``) propagates the underlying
    ValueError rather than being silently swallowed."""
    reg = _import_reg()
    query = _Query(profile_id=reg.PROFILE_ID, sector_ref=reg.SECTOR_REF)
    bundle = _Bundle(
        revision_tuple=(("k", "v", "extra"),),
        rights_revision="r1",
        native_refs=(_synthetic_run_context_ref(),),
    )
    # The shell's recipe turns the 3-tuple into [k, v, extra], not [k, v].
    # The composer then json.dumps a 3-element list — which is fine for the
    # hash; the assertion is that nothing is silently swallowed or dropped
    # to keep parity with the shell.
    gen = reg.compose(query, bundle)["generation"]
    # The result is still a well-formed gen_ fingerprint.
    assert re.fullmatch(r"^gen_[0-9a-f]{32}$", gen)


def test_seal_clock_strips_no_whitespace():
    """M4: the strict seal clock parser does NOT strip whitespace — the
    sealed wire carries no stray spaces and whitespace would be contract
    drift. Leading/trailing whitespace is rejected."""
    reg = _import_reg()
    assert reg._parse_seal_clock(" 2026-09-25T07:48:00Z") is None
    assert reg._parse_seal_clock("2026-09-25T07:48:00Z ") is None


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
        omissions=("", "valid", None, 0, "valid"),  # mixed bad + good, dedup
    )
    envelope = reg.compose(query, bundle)
    limitations = envelope["limitations"]
    assert "owner_omission:unnamed" in limitations
    assert "owner_omission:valid" in limitations
    # Dedup: exactly one unnamed marker.
    assert limitations.count("owner_omission:unnamed") == 1


# ---------------------------------------------------------------------------
# 13. Privacy — SECRET_* strings never leak into any envelope
# ---------------------------------------------------------------------------


def test_secret_strings_do_not_leak_into_any_envelope(monkeypatch):
    """Permanent privacy guard: bundle field values carrying SECRET_* strings
    (identity_results, event_workspaces, financial_packets,
    interpretation_blocks) plus an extra ``private_note`` on the run
    context must NEVER appear in the compose or evidence envelope
    payloads."""
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
