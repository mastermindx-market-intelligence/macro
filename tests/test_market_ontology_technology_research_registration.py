"""Tests for engine.market_ontology.technology_research_registration (T8A).

Every provider here is EXPLICITLY SYNTHETIC and reuses the fixture helpers of
tests/test_market_ontology_technology_economic_change.py by import: the
assertion builder, the sealed comparison/receipt/native providers, and
SYNTHETIC_CURATION_CONTRACT (installed through the composer's loader seam, the
same monkeypatch technique _compose_happy uses) so rows actually render and the
evidence selector has something real to select from.

The adapter is pinned to the PROPOSED §8 company-first shape
(CURATION_ASSERTION_V1_1_PROPOSAL_2026-09-24.md @ 382c0b399d5c on macro#7870,
under Sol adjudication) and to hook 1 as inspected at #7870 @ e2f4d4909156 —
a reading of that head, not a live pin: the foundation head moves faster than any
citation, and this branch carries no shell at all, so the refusal is
shared_shell_unavailable regardless of where #7870 now is.
Nothing here registers anything: the shared shell is absent on this carrier
base, and test_shared_shell_registration_roundtrip_pinned_to_7870 (strict xfail)
documents by execution that a company-profile entry (anchor None, empty slice
set) is refused until §8 lands — XPASSing loudly the moment the shell appears
AND accepts the entry.
"""
from __future__ import annotations

import ast
import dataclasses
import importlib
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import jsonschema
import pytest

import engine.market_ontology.technology_economic_change as tech
import engine.market_ontology.technology_research_registration as reg
from engine.market_ontology.technology_economic_change import EconomicChangeDossierError
from engine.market_ontology.technology_research_registration import (
    TechnologyRegistrationRefusal,
)
import tests.test_market_ontology_technology_economic_change as base

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRATION_MODULE_PATH = (
    REPO_ROOT / "engine" / "market_ontology" / "technology_research_registration.py"
)
EVIDENCE_SCHEMA_PATH = (
    REPO_ROOT / "contracts" / "market_ontology"
    / "technology_economic_change.evidence.v1.schema.json"
)
DOSSIER_SCHEMA_PATH = (
    REPO_ROOT / "contracts" / "market_ontology"
    / "technology_economic_change.v1.schema.json"
)

THEME = base.THEME
COMPANY = base.COMPANY
CIK_REF = "cik:0000320193"


# --- synthetic query / bundle (the §8 request body + the OwnerBundle field set) ----


@dataclasses.dataclass(frozen=True)
class SyntheticQuery:
    """The §8 request body: profile_id + company_ref + view + time_mode, no
    slice_key. offset/cursor exist so a paging attempt is a typed refusal."""

    profile_id: str
    company_ref: str | None
    view: str
    time_mode: str = "latest"
    slice_key: str | None = None
    offset: int = 0
    cursor: str | None = None


@dataclasses.dataclass(frozen=True)
class SyntheticBundle:
    """The shell's OwnerBundle field set (semiconductor_theme_research @
    #7870), duck-typed: the adapter reads only these names."""

    revision_tuple: tuple = ()
    rights_revision: str = "synthetic_rights"
    assertions: tuple = ()
    identity_results: tuple = ()
    event_workspaces: tuple = ()
    financial_packets: tuple = ()
    interpretation_blocks: tuple = ()
    native_refs: tuple = ()
    omissions: tuple = ()


def _themed(assertion: dict, theme_ref: str = THEME) -> dict:
    themed = dict(assertion)
    themed["scope"] = {**assertion["scope"], "theme_ref": theme_ref}
    return themed


def _identity_result(entity_id: str = COMPANY, **extra: Any) -> dict:
    """One owner-side identity result: the native receipt plus the fields the
    §8 bundle contract is expected to carry (node_id / cik / as_known — all
    placeholders this adapter pins, never guesses past)."""
    result = base._receipt(entity_id=entity_id)
    result.update({"node_id": None, "cik": None, "as_known": None, **extra})
    return result


ROLE_T = _themed(base.ROLE)
BUYER_T = _themed(base.BUYER_A)
COUNTER_T = _themed(base.COUNTER)
RECEIPT_RESULT = _identity_result()

QUERY = SyntheticQuery(
    profile_id=reg.PROFILE_ID, company_ref=COMPANY, view="business"
)


def _bundle(**over: Any) -> SyntheticBundle:
    fields = dict(
        assertions=(ROLE_T, BUYER_T, COUNTER_T),
        identity_results=(RECEIPT_RESULT,),
        financial_packets=(base._comparison(),),
        native_refs=(base._native(),),
        omissions=(),
    )
    fields.update(over)
    return SyntheticBundle(**fields)


def _bundle_minus(*drop: str) -> SimpleNamespace:
    """A duck-typed bundle MISSING whole fields — the sealed-input refusal path."""
    fields = dict(
        assertions=[ROLE_T, BUYER_T, COUNTER_T],
        identity_results=[RECEIPT_RESULT],
        financial_packets=[base._comparison()],
        native_refs=[base._native()],
        omissions=[],
    )
    for key in drop:
        fields.pop(key)
    return SimpleNamespace(**fields)


def _activate_synthetic_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    """The same seam base._compose_happy uses: the composer's lazy shared-
    contract loader returns the synthetic stand-in, so assertions render."""
    monkeypatch.setattr(
        tech, "_load_shared_curation_contract", lambda: base.SYNTHETIC_CURATION_CONTRACT
    )


def _compose(monkeypatch: pytest.MonkeyPatch, query: Any = None, bundle: Any = None) -> dict:
    _activate_synthetic_contract(monkeypatch)
    return reg.compose(query or QUERY, bundle or _bundle())


def _refusal(monkeypatch: pytest.MonkeyPatch, query: Any, bundle: Any, code: str) -> None:
    with pytest.raises(TechnologyRegistrationRefusal) as excinfo:
        reg.compose(query, bundle)
    assert excinfo.value.code == code
    assert str(excinfo.value) == code


# --- the §8 facts -------------------------------------------------------------------


def test_registration_facts_are_the_proposed_section_8_field_set():
    assert dataclasses.asdict(reg.TECHNOLOGY_REGISTRATION_FACTS) == {
        "entry_kind": "company_profile",
        "profile_id": "technology_economic_change.v1",
        "anchor_theme_id": None,
        "slice_keys": (),
        "views": ("business", "comparison", "counter_observations", "identity", "coverage"),
        "company_ref_grammar": ("theme_graph_node", "cik"),
        "schema_id": "technology_economic_change.v1",
        "evidence_schema_id": "technology_economic_change.evidence.v1",
        "definition_version": "2026-09-24.1",
        "title_en": "Technology economic-change research",
        "title_zh": "科技产业经济变化研究",
        "note_en": "Paid research context for members. Nothing here ranks, gates, sizes or times anything.",
        "note_zh": "会员研究内容。此处内容不构成排序、准入、仓位或时机判断。",
        "compose": reg.compose,
        "select_evidence": reg.select_evidence,
    }


def test_views_derive_from_the_dossier_contract_display_sections():
    schema = json.loads(DOSSIER_SCHEMA_PATH.read_text(encoding="utf-8"))
    # display content sections only — every plumbing section is excluded
    plumbing = {
        "schema", "definition_version", "dossier_id", "kind", "engine_version",
        "authority", "authority_ceiling", "display_only", "owner", "mode",
        "freshness", "scope", "navigation", "classification", "selected",
        "source_version_vector", "bounds",
    }
    # set EQUALITY, not subset: a truncated VIEWS (a view silently dropped)
    # must fail here, not pass
    assert set(reg.VIEWS) == set(schema["required"]) - plumbing


def test_refusal_mirrors_the_shell_refusal_shape():
    error = TechnologyRegistrationRefusal("some_code")
    assert isinstance(error, ValueError)
    assert error.code == "some_code"
    assert str(error) == "some_code"


# --- happy compose ------------------------------------------------------------------


def test_happy_compose_carries_the_shell_identity_exactly(monkeypatch):
    payload = _compose(monkeypatch)
    # the shell's exact two checks, by execution
    assert payload["schema"] == reg.TECHNOLOGY_REGISTRATION_FACTS.schema_id == reg.PROFILE_ID
    assert payload["definition_version"] == reg.TECHNOLOGY_REGISTRATION_FACTS.definition_version
    assert reg.DEFINITION_VERSION == "2026-09-24.1"
    assert payload["scope"]["scope_mode"] == "company_first"
    assert payload["scope"]["theme_ref"] == THEME
    assert payload["scope"]["company_ref"] == COMPANY
    assert sorted(row["predicate"] for row in payload["business"]["rows"]) == [
        "buyer_paid_unit", "product_workload_role",
    ]
    assert len(payload["counter_observations"]) == 1
    tech.validate_dossier(payload)  # holds standalone, not only inside compose


def test_compose_matches_the_base_providers_dossier(monkeypatch):
    # Same sealed inputs through the adapter and through the base providers
    # must produce the same dossier identity and selection receipts.
    _activate_synthetic_contract(monkeypatch)
    receipts = [RECEIPT_RESULT]
    via_adapter = reg.compose(QUERY, _bundle())
    via_base = base._compose_happy(
        monkeypatch,
        scope=base._scope(mode="company_first"),
        business_assertions=[ROLE_T, BUYER_T, COUNTER_T],
        comparison=base._comparison(),
        native_context=base._native(),
        receipts=receipts,
        input_vector=base._input_vector(receipts),
        coverage=base._coverage(),
    )
    assert via_adapter["dossier_id"] == via_base["dossier_id"]
    assert via_adapter["selected"] == via_base["selected"]
    assert via_adapter["source_version_vector"] == via_base["source_version_vector"]


def test_compose_without_the_shared_contract_still_identifies(monkeypatch):
    # Real seam: engine.theme_graph.curation_assertion is absent on this base,
    # so the business section is the typed refusal — and the shell identity
    # checks still hold on the payload.
    payload = reg.compose(QUERY, _bundle())
    assert payload["schema"] == reg.PROFILE_ID
    assert payload["definition_version"] == reg.DEFINITION_VERSION
    assert payload["business"]["refused"] is True
    assert payload["business"]["reason_code"] == "shared_contract_unavailable"


# --- request refusals, each code by execution ---------------------------------------


def test_profile_mismatch_refused(monkeypatch):
    _refusal(
        monkeypatch,
        SyntheticQuery(profile_id="other.v1", company_ref=COMPANY, view="business"),
        _bundle(),
        "profile_mismatch",
    )


def test_slice_key_forbidden_refused(monkeypatch):
    query = dataclasses.replace(QUERY, slice_key="technology_ex_semis:us")
    _refusal(monkeypatch, query, _bundle(), "slice_key_forbidden")


def test_view_not_registered_refused(monkeypatch):
    for view in ("semiconductor_business", "narrative", "", None):
        _refusal(
            monkeypatch,
            SyntheticQuery(profile_id=reg.PROFILE_ID, company_ref=COMPANY, view=view),
            _bundle(),
            "view_not_registered",
        )


def test_view_is_validation_only_payload_is_view_invariant(monkeypatch):
    # view gates the request but does NOT project the payload: every
    # registered view of the same request + bundle composes the byte-identical
    # dossier. Projection is the shared shell's responsibility pending §8, so
    # the day this pin breaks is the day that contract changed — loud, never
    # silent drift.
    _activate_synthetic_contract(monkeypatch)
    payloads = [
        reg.compose(dataclasses.replace(QUERY, view=view), _bundle())
        for view in reg.VIEWS
    ]
    for other in payloads[1:]:
        assert other == payloads[0]


def test_system_replay_refused_without_as_known_identity(monkeypatch):
    query = dataclasses.replace(QUERY, time_mode="system_replay")
    _refusal(monkeypatch, query, _bundle(), "replay_identity_unavailable")


def test_system_replay_composes_with_as_known_identity(monkeypatch):
    bundle = _bundle(identity_results=(_identity_result(as_known={"cutoff": base.CUTOFF}),))
    payload = _compose(
        monkeypatch,
        dataclasses.replace(QUERY, time_mode="system_replay"),
        bundle,
    )
    assert payload["definition_version"] == reg.DEFINITION_VERSION


def test_pagination_unsupported_refused(monkeypatch):
    _refusal(monkeypatch, dataclasses.replace(QUERY, offset=1), _bundle(), "pagination_unsupported")
    # cursor is as much a paging attempt as offset: the dossier declares
    # pagination_supported false, so a cursor-carrying request must refuse
    # instead of silently answering page 1.
    _refusal(
        monkeypatch,
        dataclasses.replace(QUERY, cursor="synthetic-page2-token"),
        _bundle(),
        "pagination_unsupported",
    )


def test_company_ref_required_refused(monkeypatch):
    _refusal(
        monkeypatch,
        SyntheticQuery(profile_id=reg.PROFILE_ID, company_ref=None, view="business"),
        _bundle(),
        "company_ref_required",
    )


@pytest.mark.parametrize(
    "bad_ref",
    [
        "msft",                      # bare ticker-like token
        "co:xx:MSFT",                # unknown region
        "co:us:",                    # empty id
        "co:us:MSFT#",               # revision pin with no digits
        "cik:12345",                 # not ten digits
        "cik:00003201933",           # eleven digits
        "CIK:0000320193",            # case-sensitive family
        " co:us:MSFT",               # leading whitespace
    ],
)
def test_company_ref_grammar_refused(monkeypatch, bad_ref):
    _refusal(
        monkeypatch,
        SyntheticQuery(profile_id=reg.PROFILE_ID, company_ref=bad_ref, view="business"),
        _bundle(),
        "company_ref_grammar",
    )


@pytest.mark.parametrize(
    "accepted_ref",
    [
        "co:cn:synth.beta-1",
        "co:intl:synth-gamma",
        "co:us:synth-alpha#2",
        "cik:0000320193",
    ],
)
def test_company_ref_grammar_accepted_passes_to_resolution(monkeypatch, accepted_ref):
    # Accepted grammar is observable as NOT company_ref_grammar: with no
    # matching identity result the next gate — resolution — refuses instead.
    _refusal(
        monkeypatch,
        SyntheticQuery(profile_id=reg.PROFILE_ID, company_ref=accepted_ref, view="business"),
        _bundle(),
        "company_ref_unresolved",
    )


def test_company_ref_unresolved_refused(monkeypatch):
    _refusal(
        monkeypatch,
        SyntheticQuery(profile_id=reg.PROFILE_ID, company_ref="co:us:synth-omega", view="business"),
        _bundle(),
        "company_ref_unresolved",
    )


def test_ticker_strings_never_resolve_a_company_ref(monkeypatch):
    ticker_only = _identity_result()
    ticker_only.pop("entity_id")
    ticker_only.pop("node_id")
    ticker_only["display_ticker"] = "SYNTH.A"  # display formatting, never proof
    _refusal(
        monkeypatch,
        SyntheticQuery(profile_id=reg.PROFILE_ID, company_ref="co:us:synth-alpha", view="business"),
        _bundle(identity_results=(ticker_only,)),
        "company_ref_unresolved",
    )


def test_cik_ref_resolves_through_the_identity_result(monkeypatch):
    bundle = _bundle(identity_results=(_identity_result(cik=CIK_REF),))
    payload = _compose(
        monkeypatch,
        SyntheticQuery(profile_id=reg.PROFILE_ID, company_ref=CIK_REF, view="identity"),
        bundle,
    )
    # the sealed scope carries the RESOLVED native entity id, never the cik form
    assert payload["scope"]["company_ref"] == COMPANY


def test_revision_pinned_ref_resolves_through_node_id(monkeypatch):
    bundle = _bundle(
        identity_results=(_identity_result(node_id=f"{COMPANY}#2"),)
    )
    payload = _compose(
        monkeypatch,
        SyntheticQuery(profile_id=reg.PROFILE_ID, company_ref=f"{COMPANY}#2", view="business"),
        bundle,
    )
    assert payload["scope"]["company_ref"] == COMPANY


def test_unresolvable_sealed_company_ref_refused(monkeypatch):
    # A cik request whose identity result carries no co:-grammar entity id
    # cannot supply the sealed scope's company_ref: refused, never repaired.
    bare = {"cik": CIK_REF}  # no entity_id at all
    _refusal(
        monkeypatch,
        SyntheticQuery(profile_id=reg.PROFILE_ID, company_ref=CIK_REF, view="business"),
        _bundle(identity_results=(bare,)),
        "sealed_input_unavailable:company_ref",
    )


# --- sealed-input mapping refusals ----------------------------------------------------


def test_theme_ref_unavailable_without_theme_in_assertion_scope(monkeypatch):
    _refusal(
        monkeypatch,
        QUERY,
        _bundle(assertions=(base.ROLE, base.BUYER_A, base.COUNTER)),
        "theme_ref_unavailable",
    )


def test_theme_ref_unavailable_on_conflicting_theme_ids(monkeypatch):
    conflicting = (_themed(base.ROLE, THEME), _themed(base.BUYER_A, "theme:other-vertical"))
    _refusal(monkeypatch, QUERY, _bundle(assertions=conflicting), "theme_ref_unavailable")


def test_carried_theme_ref_is_never_repaired(monkeypatch):
    bad_theme = _bundle(assertions=(_themed(base.ROLE, "not-a-theme-ref"),))
    with pytest.raises(EconomicChangeDossierError, match=r"^scope_shape_invalid:"):
        reg.compose(QUERY, bad_theme)


def test_native_context_unavailable_refused(monkeypatch):
    _refusal(monkeypatch, QUERY, _bundle(native_refs=()), "sealed_input_unavailable:native_context")


def test_conflicting_native_contexts_refuse_regardless_of_order(monkeypatch):
    # Two full-field-set native refs could carry different `generation` values
    # — and therefore different dossier ids — so tuple order must never pick
    # the winner: both orderings refuse with the SAME code, and the single-ref
    # happy path is the existing compose suite above.
    first = dict(base._native(), generation="gen-synth-conflict-a")
    second = dict(base._native(), generation="gen-synth-conflict-b")
    for native_refs in ((first, second), (second, first)):
        with pytest.raises(TechnologyRegistrationRefusal) as excinfo:
            reg.compose(QUERY, _bundle(native_refs=native_refs))
        assert excinfo.value.code == "sealed_input_unavailable:native_context"


def test_coverage_unavailable_refused(monkeypatch):
    _refusal(monkeypatch, QUERY, _bundle_minus("omissions"), "sealed_input_unavailable:coverage")


def test_duplicate_comparison_packets_refused(monkeypatch):
    bundle = _bundle(financial_packets=(base._comparison(), base._comparison()))
    _refusal(monkeypatch, QUERY, bundle, "sealed_input_unavailable:comparison")


# --- the refused comparison path -------------------------------------------------------


def test_no_comparison_packet_renders_the_composer_refusal(monkeypatch):
    payload = _compose(monkeypatch, bundle=_bundle(financial_packets=()))
    section = payload["comparison"]
    assert section["refused"] is True
    assert section["reason_code"] == "comparison_limitations_absent"
    # no fabricated figures: the refusal section carries no result at all
    assert "result" not in section
    assert payload["schema"] == reg.PROFILE_ID
    assert payload["bounds"]["pagination_supported"] is False


def test_refused_comparison_packet_passes_through_verbatim(monkeypatch):
    refused = base._comparison(admitted=False)
    payload = _compose(monkeypatch, bundle=_bundle(financial_packets=(refused,)))
    section = payload["comparison"]
    assert section["admission"] == "refused"
    assert section["result"] is None
    assert section["comparison_id"] == refused["comparison_id"]


def test_coverage_reflects_the_bundle_omissions(monkeypatch):
    complete = _compose(monkeypatch, bundle=_bundle(omissions=()))
    assert complete["coverage"]["population_mode"] == "unknown_scope"
    assert complete["coverage"]["known_population_total"] is None
    assert complete["coverage"]["completeness"]["complete_within_accepted_scope"] is True
    incomplete = _compose(
        monkeypatch, bundle=_bundle(omissions=("synthetic omission: rights blocked",))
    )
    assert incomplete["coverage"]["completeness"]["complete_within_accepted_scope"] is False
    assert incomplete["coverage"]["family_labels"]["are_baskets"] is False


# --- select_evidence --------------------------------------------------------------------


def _evidence_validator() -> jsonschema.protocols.Validator:
    return jsonschema.Draft202012Validator(
        json.loads(EVIDENCE_SCHEMA_PATH.read_text(encoding="utf-8"))
    )


def test_select_evidence_returns_the_one_authorized_assertion(monkeypatch):
    _activate_synthetic_contract(monkeypatch)
    envelope = reg.select_evidence(QUERY, _bundle(), "synthetic-doc-role-1")
    assert envelope["schema"] == reg.EVIDENCE_SCHEMA_ID
    assert envelope["definition_version"] == reg.DEFINITION_VERSION
    assert envelope["generation"].startswith("tecd_")
    # X1 (corrected in T8A-X1): VERBATIM deep copy — the assertion-internal
    # authority block stays exactly as the owner's contract carries it, in the
    # ASSERTION contract's own five-flag can_* vocabulary; the envelope's own
    # top-level ceiling is the SEPARATE six-name Technology vocabulary, and
    # the two are deliberately never equal
    assert envelope["assertion"] == ROLE_T
    assert envelope["assertion"] is not ROLE_T  # deep copy, never an alias
    assert envelope["assertion"]["authority"] == base.ASSERTION_FALSE_AUTHORITY
    assert envelope["limitations"] == sorted(envelope["limitations"])
    assert envelope["authority"] == {
        "rank": False, "gate": False, "size": False,
        "veto": False, "originate": False, "open_entry": False,
    }
    assert set(envelope) == {
        "schema", "definition_version", "generation", "assertion", "limitations", "authority"
    }
    _evidence_validator().validate(envelope)


def test_select_evidence_generation_is_the_composed_dossier_id(monkeypatch):
    _activate_synthetic_contract(monkeypatch)
    bundle = _bundle()
    envelope = reg.select_evidence(QUERY, bundle, "synthetic-doc-role-1")
    assert envelope["generation"] == reg.compose(QUERY, bundle)["dossier_id"]


def test_select_evidence_limitations_come_from_the_dossier(monkeypatch):
    _activate_synthetic_contract(monkeypatch)
    envelope = reg.select_evidence(QUERY, _bundle(), "synthetic-doc-role-1")
    dossier = reg.compose(QUERY, _bundle())
    assert envelope["limitations"] == [
        dossier["comparison"]["primary_limitation"]["text"]
    ]


def test_select_evidence_unknown_and_unselected_share_one_code(monkeypatch):
    _activate_synthetic_contract(monkeypatch)
    # carried by an assertion in the bundle but NOT rendered (unsupported predicate)
    unselected = _themed(
        base._assertion(predicate="theme_membership", seed="unselected-1",
                        source=base._src("synthetic-doc-unselected-1"))
    )
    bundle = _bundle(assertions=(ROLE_T, unselected))
    codes = []
    for ref in ("no-such-doc-anywhere", "synthetic-doc-unselected-1"):
        with pytest.raises(TechnologyRegistrationRefusal) as excinfo:
            reg.select_evidence(QUERY, bundle, ref)
        codes.append(excinfo.value.code)
    assert codes == ["not_available", "not_available"]  # one code, no existence disclosure


def test_select_evidence_substitution_by_shared_source_object_id_refuses(monkeypatch):
    # B1: a rendered assertion and a never-rendered decoy sharing ONE
    # source.object_id — the citation gate passes on the rendered row, but the
    # bundle cannot say WHICH assertion the ref names, so the envelope must
    # refuse rather than hand out one by tuple order.
    _activate_synthetic_contract(monkeypatch)
    decoy = _themed(
        base._assertion(predicate="theme_membership", seed="decoy-shared-1",
                        source=base._src("synthetic-doc-role-1"))
    )
    for assertions in ((decoy, ROLE_T), (ROLE_T, decoy)):
        with pytest.raises(TechnologyRegistrationRefusal) as excinfo:
            reg.select_evidence(QUERY, _bundle(assertions=assertions), "synthetic-doc-role-1")
        assert excinfo.value.code == "not_available"
    # the single-match happy path still returns the rendered assertion
    envelope = reg.select_evidence(QUERY, _bundle(), "synthetic-doc-role-1")
    assert envelope["assertion"] == ROLE_T


def test_two_rendered_assertions_from_one_document_both_refuse(monkeypatch):
    # X5(b) pin: source.object_id is DOCUMENT-grained while the evidence unit
    # is assertion-grained. Two legitimately distinct, BOTH-RENDERED
    # assertions from ONE filing (same object_id, different selector) share a
    # single document key, so the exactly-one gate refuses and the ref comes
    # back not_available. Fail-closed and deliberate — the durable fix
    # (authorize on the full source ref including the selector, or an
    # assertion-level id) is owed to §8 and not taken here. The day §8 names
    # the finer key, THIS pin fails loudly and must be re-examined, never
    # silently re-passed.
    _activate_synthetic_contract(monkeypatch)
    page_one = _themed(base.ROLE)
    page_seven = _themed(
        base._assertion(
            predicate="buyer_paid_unit",
            seed="one-doc-two-assertions-buyer",
            source=base._src(
                "synthetic-doc-role-1", selector="synthetic/synthetic-doc-role-1#p7"
            ),
        )
    )
    bundle = _bundle(assertions=(page_one, page_seven))
    dossier = reg.compose(QUERY, bundle)
    # both are real, rendered evidence from that one document...
    assert dossier["business"].get("refused") is not True
    assert len(dossier["business"]["rows"]) == 2
    assert "synthetic-doc-role-1" in reg._cited_source_object_ids(dossier)
    # ...and yet the document-grained key cannot name EITHER one
    with pytest.raises(TechnologyRegistrationRefusal) as excinfo:
        reg.select_evidence(QUERY, bundle, "synthetic-doc-role-1")
    assert excinfo.value.code == "not_available"
    # control: the same second assertion on its OWN document is selectable,
    # so the shared document key — not the assertion — is what refused above
    own_doc = _themed(
        base._assertion(
            predicate="buyer_paid_unit",
            seed="one-doc-two-assertions-buyer",
            source=base._src("synthetic-doc-buyer-1"),
        )
    )
    selected = reg.select_evidence(QUERY, _bundle(assertions=(page_one, own_doc)), "synthetic-doc-role-1")
    assert selected["assertion"] == page_one


def test_select_evidence_deep_copies_the_assertion(monkeypatch):
    # The expected text is snapshotted BEFORE the mutation: the bundle reuses
    # the module-level ROLE_T, so a shallow copy would corrupt ROLE_T itself
    # and a post-mutation comparison would compare the mutated value against
    # itself. Against the snapshot, replacing copy.deepcopy with dict() FAILS.
    _activate_synthetic_contract(monkeypatch)
    first = reg.select_evidence(QUERY, _bundle(), "synthetic-doc-role-1")
    expected = ROLE_T["observation"]["text"]
    first["assertion"]["observation"]["text"] = "mutated"
    second = reg.select_evidence(QUERY, _bundle(), "synthetic-doc-role-1")
    assert second["assertion"]["observation"]["text"] == expected
    # and the mutation never leaked into the shared fixture either
    assert ROLE_T["observation"]["text"] == expected


def test_select_evidence_applies_the_same_query_refusals(monkeypatch):
    bad_view = SyntheticQuery(profile_id=reg.PROFILE_ID, company_ref=COMPANY, view="nope")
    with pytest.raises(TechnologyRegistrationRefusal) as excinfo:
        reg.select_evidence(bad_view, _bundle(), "synthetic-doc-role-1")
    assert excinfo.value.code == "view_not_registered"


def test_select_evidence_without_the_shared_contract_refuses_everything(monkeypatch):
    # Real seam: no shared contract -> no rendered rows -> nothing is cited ->
    # not_available even for a ref the bundle actually carries.
    with pytest.raises(TechnologyRegistrationRefusal) as excinfo:
        reg.select_evidence(QUERY, _bundle(), "synthetic-doc-role-1")
    assert excinfo.value.code == "not_available"


# --- evidence contract teeth --------------------------------------------------------------


def test_evidence_schema_rejects_mutations(monkeypatch):
    _activate_synthetic_contract(monkeypatch)
    envelope = reg.select_evidence(QUERY, _bundle(), "synthetic-doc-role-1")
    validator = _evidence_validator()

    mutated = json.loads(json.dumps(envelope))
    mutated["unexpected"] = 1
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(mutated)

    mutated = json.loads(json.dumps(envelope))
    mutated["authority"]["rank"] = True
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(mutated)

    mutated = json.loads(json.dumps(envelope))
    mutated["generation"] = "not-a-dossier-id"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(mutated)

    mutated = json.loads(json.dumps(envelope))
    mutated["definition_version"] = "2026-09-24"  # missing the .N suffix
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(mutated)

    mutated = json.loads(json.dumps(envelope))
    mutated["definition_version"] = "1999-01-01.9"  # well-formed but NOT this revision
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(mutated)


def test_evidence_schema_binds_definition_version_by_identity(monkeypatch):
    schema = json.loads(EVIDENCE_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["properties"]["definition_version"]["const"] == reg.DEFINITION_VERSION


def test_evidence_contract_accepts_the_real_five_flag_can_star_authority(monkeypatch):
    # T8A-X1 regression: the shared curation assertion's own authority block
    # is the FIVE can_* flags (can_rank/can_gate/can_size/can_originate/
    # can_open_entry), closed, all literally false — as inspected at
    # 382c0b399d5c on macro#7870 (identical at 45eb37bb/e2f4d4909156) and
    # enforced by the owner's authority_not_all_false code rule on every
    # render. The six-name pin this test replaces made exactly this
    # contract-valid assertion REFUSE (evidence_schema_violation:
    # assertion/authority), which would have left the selector 100% dead the
    # day the shared module landed.
    _activate_synthetic_contract(monkeypatch)
    assertion = _themed(
        base._assertion(predicate="product_workload_role", seed="can-star-1")
    )
    assert assertion["authority"] == base.ASSERTION_FALSE_AUTHORITY
    bundle = _bundle(assertions=(assertion,))
    envelope = reg.select_evidence(QUERY, bundle, "synthetic-doc-role-1")
    assert envelope["assertion"]["authority"] == {
        "can_rank": False, "can_gate": False, "can_size": False,
        "can_originate": False, "can_open_entry": False,
    }
    reg.validate_evidence_envelope(envelope)  # no raise: the real vocabulary validates
    _evidence_validator().validate(envelope)  # and so does the shipped contract file


def test_selected_assertion_passes_the_shared_curation_contract_verbatim(monkeypatch):
    # X1(d): the envelope's assertion, EXACTLY as select_evidence emits it,
    # validates against the shared curation contract (synthetic stand-in for
    # theme_graph.curation_assertion.v1). This is the regression that
    # motivated the inversion: under the old pop-the-required-key-out rule the
    # same call failed with missing ['authority'].
    _activate_synthetic_contract(monkeypatch)
    envelope = reg.select_evidence(QUERY, _bundle(), "synthetic-doc-role-1")
    validated = base.SYNTHETIC_CURATION_CONTRACT.validate_assertion(envelope["assertion"])
    assert validated == envelope["assertion"]


def test_validate_evidence_envelope_has_runtime_teeth(monkeypatch):
    # N3: the same contract check the schema file carries is callable at
    # runtime and refuses TYPED — select_evidence runs it on every envelope
    # immediately before returning. X3: the code carries the violating PATH
    # only, never the validator's instance-rendering message. (The mutated
    # authority is the ENVELOPE's own top-level ceiling — since T8A-X1 the
    # assertion sub-schema is fully open, so assertion-internal mutations are
    # the owner contract's business, not this envelope's.)
    _activate_synthetic_contract(monkeypatch)
    envelope = reg.select_evidence(QUERY, _bundle(), "synthetic-doc-role-1")

    reg.validate_evidence_envelope(envelope)  # the lawful envelope passes

    abusive = json.loads(json.dumps(envelope))
    abusive["authority"]["rank"] = True
    with pytest.raises(TechnologyRegistrationRefusal) as excinfo:
        reg.validate_evidence_envelope(abusive)
    assert excinfo.value.code.startswith("evidence_schema_violation: authority")

    unknown_top_level = json.loads(json.dumps(envelope))
    unknown_top_level["unexpected"] = 1
    with pytest.raises(TechnologyRegistrationRefusal) as excinfo:
        reg.validate_evidence_envelope(unknown_top_level)
    assert excinfo.value.code == "evidence_schema_violation: <root>"


def test_evidence_schema_violation_code_leaks_no_payload(monkeypatch):
    # X3: a refusal code is a snake_case identifier, and this is a SELECTION
    # path — the jsonschema message for a const violation renders the whole
    # offending instance, so the validator's message must never enter the
    # code. Path only, canary absent, hard length bound.
    _activate_synthetic_contract(monkeypatch)
    envelope = reg.select_evidence(QUERY, _bundle(), "synthetic-doc-role-1")
    canary = "LEAK-CANARY-7c31ab9e-assertion-content"
    smuggled = json.loads(json.dumps(envelope))
    smuggled["authority"]["rank"] = canary  # const-false violation
    with pytest.raises(TechnologyRegistrationRefusal) as excinfo:
        reg.validate_evidence_envelope(smuggled)
    code = excinfo.value.code
    assert canary not in code
    assert ROLE_T["observation"]["text"] not in code
    assert code == "evidence_schema_violation: authority/rank"
    assert len(code) <= 120  # stated bound: a path, never a rendered instance


# --- X4: pins for two previously unpinned fixes --------------------------------------


def test_dossier_id_digest_binds_the_definition_version(monkeypatch):
    # X4(a): deleting "definition_version" from the dossier_id digest mapping
    # in technology_economic_change.py must FAIL here — before this pin the
    # deletion left both suites green. The dossier contract pins
    # definition_version by const, so a changed version would be refused at
    # validate_dossier time; validation is stubbed for this binding
    # experiment only — the digest is the thing under test, not the contract.
    monkeypatch.setattr(tech, "validate_dossier", lambda dossier: None)
    monkeypatch.setattr(tech, "DEFINITION_VERSION", "2026-09-24.2")
    bumped = base._compose_happy(monkeypatch)
    monkeypatch.setattr(tech, "DEFINITION_VERSION", "2026-09-24.3")
    bumped_again = base._compose_happy(monkeypatch)
    monkeypatch.setattr(tech, "DEFINITION_VERSION", "2026-09-24.2")
    same_version_as_bumped = base._compose_happy(monkeypatch)
    assert bumped["dossier_id"] != bumped_again["dossier_id"]
    assert bumped["dossier_id"] == same_version_as_bumped["dossier_id"]


def test_select_evidence_runs_the_contract_check_before_returning(monkeypatch):
    # X4(b): the validate_evidence_envelope call at the tail of select_evidence
    # is load-bearing — deleting it left the suite green before this pin. Both
    # limbs fail without the call: the recorder records nothing, and the
    # refusal the validator would raise is never surfaced.
    _activate_synthetic_contract(monkeypatch)
    recorded = []
    monkeypatch.setattr(
        reg, "validate_evidence_envelope",
        lambda envelope: recorded.append(envelope),
    )
    envelope = reg.select_evidence(QUERY, _bundle(), "synthetic-doc-role-1")
    assert len(recorded) == 1
    assert recorded[0] is envelope  # checked before return, on the returned object

    def _refusing(envelope):
        raise TechnologyRegistrationRefusal("evidence_schema_violation: <root>")

    monkeypatch.setattr(reg, "validate_evidence_envelope", _refusing)
    with pytest.raises(TechnologyRegistrationRefusal) as excinfo:
        reg.select_evidence(QUERY, _bundle(), "synthetic-doc-role-1")
    assert excinfo.value.code == "evidence_schema_violation: <root>"


# --- X6: the contract file's own failure modes are typed ------------------------------


def test_missing_or_corrupt_contract_file_refuses_typed(monkeypatch, tmp_path):
    # X6: a missing or corrupt evidence contract file must surface through the
    # module's OWN typed refusal vocabulary, not as a raw
    # FileNotFoundError/JSONDecodeError out of the lazy validator loader.
    monkeypatch.setattr(reg, "_EVIDENCE_VALIDATOR", None)
    monkeypatch.setattr(
        reg, "EVIDENCE_CONTRACT_PATH", tmp_path / "absent-evidence-contract.json"
    )
    with pytest.raises(TechnologyRegistrationRefusal) as excinfo:
        reg.validate_evidence_envelope({"schema": reg.EVIDENCE_SCHEMA_ID})
    assert excinfo.value.code == "evidence_contract_unavailable"

    corrupt = tmp_path / "corrupt-evidence-contract.json"
    corrupt.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(reg, "_EVIDENCE_VALIDATOR", None)
    monkeypatch.setattr(reg, "EVIDENCE_CONTRACT_PATH", corrupt)
    with pytest.raises(TechnologyRegistrationRefusal) as excinfo:
        reg.validate_evidence_envelope({"schema": reg.EVIDENCE_SCHEMA_ID})
    assert excinfo.value.code == "evidence_contract_corrupt"


def test_evidence_schema_is_closed_and_assertion_open():
    schema = json.loads(EVIDENCE_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    # T8A-X1 (corrected): the ASSERTION sub-schema asserts NOTHING about the
    # assertion's internals — it is exactly {type, additionalProperties,
    # description}: no required keys, no inner properties, and no forbid-rule.
    # theme_graph.curation_assertion.v1 owns and validates that shape —
    # authority included, via its authority_not_all_false code rule, which
    # runs on every render before anything can be cited — so any mirror here
    # would be a fork of the owner's contract with a stale-by-design clock.
    assertion = schema["properties"]["assertion"]
    assert set(assertion) == {"type", "additionalProperties", "description"}
    assert assertion["type"] == "object"
    assert assertion["additionalProperties"] is True
    assert "not" not in assertion
    assert "required" not in assertion
    assert "properties" not in assertion
    # The ENVELOPE's own top-level authority block stays CLOSED and six-named:
    # that block is Technology's own row/dossier vocabulary (ECD-48), owned
    # here and correct — disjoint from the assertion contract's five can_*
    # flags, which is exactly why the two are never merged.
    authority = schema["properties"]["authority"]
    assert authority["additionalProperties"] is False
    assert set(authority["required"]) == {
        "rank", "gate", "size", "veto", "originate", "open_entry"
    }
    for flag in authority["required"]:
        assert authority["properties"][flag] == {"const": False}


# --- the shared shell dependency ------------------------------------------------------------


def test_shell_modules_import_is_lazy_only():
    tree = ast.parse(REGISTRATION_MODULE_PATH.read_text(encoding="utf-8"))
    top_level: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            top_level.append(node.module or "")
    assert not any(
        "theme_research_registry" in name or "semiconductor_theme_research" in name
        for name in top_level
    )


def test_shared_shell_unavailable_on_carrier_base():
    assert reg._load_shared_shell() is None


def test_registration_attempt_is_typed_unavailable_on_carrier_base():
    with pytest.raises(TechnologyRegistrationRefusal) as excinfo:
        reg.registration_entry_or_refusal()
    assert excinfo.value.code == "shared_shell_unavailable"


def test_broken_present_shell_import_propagates(monkeypatch):
    # N6: only ModuleNotFoundError means "not on this carrier" — a genuine
    # ImportError from a present-but-broken shell must propagate, so a broken
    # shell can never masquerade as shared_shell_unavailable.
    def _broken_import(name: str):
        raise ImportError(f"synthetic broken shell: {name}")

    monkeypatch.setattr(importlib, "import_module", _broken_import)
    with pytest.raises(ImportError, match="synthetic broken shell"):
        reg._load_shared_shell()


def test_shell_internal_dependency_loss_propagates_not_unavailable(monkeypatch):
    # X2, second limb: a ModuleNotFoundError raised from INSIDE a present
    # shell — a missing third-party dependency of the shell itself — carries a
    # different exc.name and must propagate, never be reported as
    # shared_shell_unavailable.
    real_import = importlib.import_module

    def _missing_shell_dependency(name: str):
        if name == "engine.market_ontology.theme_research_registry":
            raise ModuleNotFoundError(
                "synthetic shell dependency absent", name="synthetic_shell_dep"
            )
        return real_import(name)

    monkeypatch.setattr(importlib, "import_module", _missing_shell_dependency)
    with pytest.raises(ModuleNotFoundError, match="synthetic shell dependency absent"):
        reg.registration_entry_or_refusal()
    with pytest.raises(ModuleNotFoundError, match="synthetic shell dependency absent"):
        reg._load_shared_shell()


# --- simulated shells (injected into sys.modules; never the real one) ---------------


class _SimulatedShellRefusal(ValueError):
    """The shell's own refusal type, mirroring hook 1's ``ResearchRefusal``."""


def _install_shell(monkeypatch: pytest.MonkeyPatch, vertical_registration) -> None:
    monkeypatch.setitem(
        sys.modules,
        "engine.market_ontology.theme_research_registry",
        types.SimpleNamespace(VerticalRegistration=vertical_registration),
    )
    monkeypatch.setitem(
        sys.modules,
        "engine.market_ontology.semiconductor_theme_research",
        types.SimpleNamespace(OwnerBundle=object, ResearchQuery=object),
    )


def _install_shell_with_renamed_sibling_symbols(
    monkeypatch: pytest.MonkeyPatch, vertical_registration
) -> None:
    """X2 first limb's fixture: the registry module is intact, but the sibling
    module's OwnerBundle/ResearchQuery symbols have been renamed away — the
    full three-symbol resolver types this shell unavailable, and the
    registration path must not."""
    monkeypatch.setitem(
        sys.modules,
        "engine.market_ontology.theme_research_registry",
        types.SimpleNamespace(VerticalRegistration=vertical_registration),
    )
    monkeypatch.setitem(
        sys.modules,
        "engine.market_ontology.semiconductor_theme_research",
        types.SimpleNamespace(OwnerBundleV2=object, ResearchQueryV2=object),
    )


def test_accepting_shell_with_renamed_sibling_symbols_still_returns_the_entry(monkeypatch):
    # X2, first limb: the registration path depends ONLY on
    # VerticalRegistration. A shell whose registry ACCEPTS the §8 entry while
    # the sibling module's bundle/query symbols have drifted must still return
    # the entry — the strict-xfail round-trip exists to hear exactly this
    # acceptance, and a full-shell gate would drown it in
    # shared_shell_unavailable. The FULL resolver keeps its three-symbol gate:
    # the bundle/query consumers are not weakened here.
    def _accepting_shell(**kwargs):
        return SimpleNamespace(**kwargs)

    _install_shell_with_renamed_sibling_symbols(monkeypatch, _accepting_shell)
    entry = reg.registration_entry_or_refusal()
    assert entry.schema_id == reg.PROFILE_ID
    assert entry.compose is reg.compose
    assert entry.select_evidence is reg.select_evidence
    # the full resolver still types the drifted shell unavailable
    assert reg._load_shared_shell() is None


def test_shell_refusal_carries_the_shells_own_exception_type(monkeypatch):
    # B2(a): the concrete reason belongs to the shell; this adapter reports
    # what the shell actually raised and never guesses a reason of its own.
    def _refusing_shell(**kwargs):
        raise _SimulatedShellRefusal("anchor theme id required by hook 1")

    _install_shell(monkeypatch, _refusing_shell)
    with pytest.raises(TechnologyRegistrationRefusal) as excinfo:
        reg.registration_entry_or_refusal()
    assert excinfo.value.code == "vertical_registration_refused:_SimulatedShellRefusal"


def test_shell_accepting_the_entry_returns_it(monkeypatch):
    # B2(b): the XPASS path — a shell that accepts the §8 company-profile
    # entry hands the entry back verbatim, callables and all.
    def _accepting_shell(**kwargs):
        return SimpleNamespace(**kwargs)

    _install_shell(monkeypatch, _accepting_shell)
    entry = reg.registration_entry_or_refusal()
    assert entry.schema_id == reg.PROFILE_ID
    assert entry.evidence_schema_id == reg.EVIDENCE_SCHEMA_ID
    assert entry.definition_version == reg.DEFINITION_VERSION
    assert entry.compose is reg.compose
    assert entry.select_evidence is reg.select_evidence


def test_shell_signature_drift_added_parameter_propagates_typeerror(monkeypatch):
    # B2(c): a constructor that gained a required parameter is §8 signature
    # drift — the TypeError PROPAGATES and is never converted into a typed
    # refusal, so the pinned xfail becomes a hard error instead of xfailing
    # stale.
    def _drifted_shell_added(*, anchor_theme_id, slice_keys, schema_id,
                             evidence_schema_id, definition_version, compose,
                             select_evidence, title_en, title_zh, note_en,
                             note_zh, owner_lane_required):
        raise AssertionError("unreachable")

    _install_shell(monkeypatch, _drifted_shell_added)
    with pytest.raises(TypeError, match="owner_lane_required"):
        reg.registration_entry_or_refusal()


def test_shell_signature_drift_renamed_parameter_propagates_typeerror(monkeypatch):
    # B2(d): a renamed parameter is the same drift — TypeError, uncaught.
    def _drifted_shell_renamed(*, anchor, slice_keys, schema_id,
                               evidence_schema_id, definition_version, compose,
                               select_evidence, title_en, title_zh, note_en,
                               note_zh):
        raise AssertionError("unreachable")

    _install_shell(monkeypatch, _drifted_shell_renamed)
    with pytest.raises(TypeError, match="anchor_theme_id"):
        reg.registration_entry_or_refusal()


@pytest.mark.xfail(
    strict=True,
    raises=TechnologyRegistrationRefusal,
    reason=(
        "hook 1 as inspected at #7870 @ e2f4d4909156 (a reading of that head, not a "
        "live pin) refuses the proposed §8 "
        "company-profile entry (anchor_theme_id=None, slice_keys=()), and this "
        "carrier base does not carry the shell at all (typed "
        "shared_shell_unavailable; with the shell present, a shell refusal is "
        "typed vertical_registration_refused:<ExcType>). Signature drift "
        "surfaces as an uncaught TypeError, never a quiet xfail. XPASS means "
        "the shell landed AND accepts a company-profile entry — §8 "
        "adjudicated — and this pin must be re-examined, not silenced."
    ),
)
def test_shared_shell_registration_roundtrip_pinned_to_7870():
    entry = reg.registration_entry_or_refusal()
    # Reached only when the shell accepts the §8 company-profile entry.
    assert entry.schema_id == reg.PROFILE_ID
    assert entry.evidence_schema_id == reg.EVIDENCE_SCHEMA_ID
    assert entry.definition_version == reg.DEFINITION_VERSION
    assert callable(entry.compose)
    assert callable(entry.select_evidence)
