"""Lane-5 v1.1 wiring contract: the ``issuer_economics`` registration field,
the semiconductor binding, the v2 QUERY-envelope attach — and the BYTE
IDENTENTITY of the v1 response and the v2 evidence path with and without the
builder (frozen spec item 3).

EVIDENCE LABEL: everything here runs the REAL registrations and the REAL
route shell over SYNTHETIC warm-state fixture bundles — FIXTURE evidence for
the wiring law itself, never a real-issuer claim. The one real-data read the
binding can perform (alias enumeration) is covered, presence-gated, in
``tests/test_market_ontology_issuer_economics.py``.

The byte-identity proof is a differential, not a snapshot: the SAME warm
owner state serves the v1 query, the v2 evidence replay and the v2 query
twice — once through the REAL semiconductor registration (builder bound) and
once through a twin registration that is ``dataclasses.replace(real,
issuer_economics=None)``. If the builder leaked into the v1 response or the
evidence payload, the two runs could not be byte-identical; and the v2 QUERY
envelope must differ from its twin EXACTLY by carrying the block.
"""
from __future__ import annotations

import dataclasses
from types import SimpleNamespace

import pytest

import app.theme_research as theme_research
import tests.test_theme_research_api as api_base
from engine.market_ontology.issuer_economics import ISSUER_ECONOMICS_SCHEMA
from engine.market_ontology.semiconductor_witness_scope import WITNESS_ROSTER
from engine.market_ontology.theme_research_registry import (
    VerticalRegistration,
    registration_for as real_registration_for,
)

QUERY_ROUTE = "/api/themes/v1/research/query"
EVIDENCE_ROUTE = "/api/themes/v1/research/evidence"

#: The API harness's entitled client, re-exported so its fixture registers
#: for THIS module too (fixtures do not travel by import alone).
entitled_client = api_base.entitled_client

ALL_FALSE_AUTHORITY = {
    "rank": False, "gate": False, "size": False,
    "veto": False, "originate": False, "open_entry": False,
}


def _twin_registration(monkeypatch) -> None:
    """Route every ``ai_semiconductors`` resolution to the REAL registration
    minus exactly one thing: the issuer-economics builder. Every other
    vertical keeps its real registration (none of them bind one)."""
    real = real_registration_for("ai_semiconductors")
    twin = dataclasses.replace(real, issuer_economics=None)
    monkeypatch.setattr(
        theme_research, "registration_for",
        lambda anchor: twin if anchor == "ai_semiconductors"
        else real_registration_for(anchor),
    )


# ---------------------------------------------------------------------------
# Registration contract
# ---------------------------------------------------------------------------


def test_registration_contract_adds_issuer_economics_after_evidence_refs_field():
    names = [field.name for field in dataclasses.fields(VerticalRegistration)]
    assert "issuer_economics" in names
    # The field lands immediately after the frozen envelope contract's last
    # field — an append anywhere earlier would shift positional construction.
    assert names.index("issuer_economics") == names.index("evidence_refs_field") + 1
    # Callable-or-None only: a string/probe value is refused at construction.
    with pytest.raises(TypeError):
        dataclasses.replace(
            real_registration_for("ai_semiconductors"),
            issuer_economics="not-callable",
        )


def test_semiconductor_entry_binds_a_lazy_builder_that_never_raises(monkeypatch):
    import engine.market_ontology.semiconductor_witness_scope as scope_mod
    from engine.market_ontology import issuer_economics as econ_module

    # Environment-independent: the alias-master read is forced to its typed
    # unknown here (the real read is covered, gated, in the falsifier suite).
    monkeypatch.setattr(scope_mod, "_load_issuer_master", lambda: None)

    registration = real_registration_for("ai_semiconductors")
    assert callable(registration.issuer_economics)
    assert registration.issuer_economics.lazy_target() is \
        econ_module.build_issuer_economics

    out = dict(registration.issuer_economics(
        SimpleNamespace(slice_key="hbm_packaging"),
        SimpleNamespace(event_workspaces=()),
    ))
    assert out["schema"] == ISSUER_ECONOMICS_SCHEMA
    # Degradation contract with the master unreadable: NO identity is guessed
    # (the scope resolves zero identities and says so in typed tokens), the
    # DECLARED roster still counts eligible, and everyone is honestly unknown.
    assert out["cohort"] == {
        "eligible": len(WITNESS_ROSTER["hbm_packaging"]),
        "identified": 0,
        "reported": 0,
        "comparable": 0,
        "unknown": 1,
        "noncomparable": 0,
        "denominator_rule": out["cohort"]["denominator_rule"],
    }
    assert out["issuers"] == []
    assert "identity_source_unavailable" in out["limitations"]
    assert "identity_unverified:TSM" in out["limitations"]
    assert out["authority"] == ALL_FALSE_AUTHORITY


def test_exactly_one_vertical_binds_a_builder():
    """Census over BOTH registration stores: the semiconductor anchor binds
    the lane-5 builder; every other anchor and every profile binds none, so
    no other envelope can silently grow an issuer-economics block."""
    import engine.market_ontology.theme_research_registry as registry_mod

    bound = {
        key for key, reg in registry_mod.REGISTRY.items()
        if reg.issuer_economics is not None
    }
    assert bound == {"ai_semiconductors"}
    assert all(
        reg.issuer_economics is None
        for reg in registry_mod.PROFILE_REGISTRY.values()
    )


# ---------------------------------------------------------------------------
# The v2 QUERY envelope attach
# ---------------------------------------------------------------------------


def test_v2_query_envelope_carries_issuer_economics_sibling_of_data(
    entitled_client, monkeypatch, tmp_path,
):
    api_base._install_warm_owner_state(monkeypatch, tmp_path)
    response = entitled_client.post(
        QUERY_ROUTE, json=api_base._v2_theme_query_body(),
    )
    assert response.status_code == 200, response.text
    api_base._assert_private_headers(response)
    envelope = response.json()
    assert envelope["schema"] == api_base._V2_RESPONSE_SCHEMA
    assert envelope["entry_kind"] == "theme"
    assert "data" in envelope
    assert envelope["data"]["schema"] == "semiconductor_theme_research.v1"

    block = envelope["issuer_economics"]
    assert block["schema"] == ISSUER_ECONOMICS_SCHEMA
    assert block["cohort"]["eligible"] == 1  # the hbm_packaging witness roster
    assert block["authority"] == ALL_FALSE_AUTHORITY
    assert set(block["wording"]) >= {
        "relative_strength", "selection_contribution", "lineage",
        "unreported", "noncomparable",
    }


def test_v2_technology_profile_envelope_has_no_issuer_economics_key(
    entitled_client, monkeypatch,
):
    api_base._v2_tech_state(monkeypatch)
    response = entitled_client.post(
        QUERY_ROUTE, json=api_base._v2_tech_query_body(),
    )
    assert response.status_code == 200, response.text
    envelope = response.json()
    assert envelope["schema"] == api_base._V2_RESPONSE_SCHEMA
    assert envelope["entry_kind"] == "company_profile"
    assert "issuer_economics" not in envelope


def test_v1_request_without_request_schema_stays_v1_shaped(
    entitled_client, monkeypatch, tmp_path,
):
    """The v1 body (no ``request_schema`` key) must keep serving the NATIVE
    payload unwrapped — the composer's own schema, no envelope, no block."""
    api_base._install_warm_owner_state(monkeypatch, tmp_path)
    response = entitled_client.post(
        QUERY_ROUTE, json=api_base._valid_body(),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["schema"] == "semiconductor_theme_research.v1"
    assert "issuer_economics" not in payload


# ---------------------------------------------------------------------------
# Byte identity: v1 response and v2 evidence path, builder bound vs absent
# ---------------------------------------------------------------------------


def test_v1_and_evidence_paths_are_byte_identical_without_the_builder(
    entitled_client, monkeypatch, tmp_path,
):
    api_base._install_warm_owner_state(monkeypatch, tmp_path)

    # --- WITH the real registration (builder bound) -----------------------
    v1_real = entitled_client.post(QUERY_ROUTE, json=api_base._valid_body())
    assert v1_real.status_code == 200, v1_real.text
    payload = v1_real.json()
    refs = [r for r in payload["evidence_refs"] if r.get("kind") == "assertion"]
    assert refs, "warm fixture granted no assertion ref; differential is vacuous"
    evidence_body = api_base._evidence_body_with(
        refs[0]["assertion_ref"], payload["generation"],
    )
    evidence_real = entitled_client.post(EVIDENCE_ROUTE, json=evidence_body)
    assert evidence_real.status_code == 200, evidence_real.text
    v2_real = entitled_client.post(
        QUERY_ROUTE, json=api_base._v2_theme_query_body(),
    )
    assert v2_real.status_code == 200, v2_real.text

    # --- TWIN: same registration minus exactly the builder ----------------
    _twin_registration(monkeypatch)
    v1_twin = entitled_client.post(QUERY_ROUTE, json=api_base._valid_body())
    evidence_twin = entitled_client.post(EVIDENCE_ROUTE, json=evidence_body)
    v2_twin = entitled_client.post(
        QUERY_ROUTE, json=api_base._v2_theme_query_body(),
    )
    assert v1_twin.status_code == 200, v1_twin.text
    assert evidence_twin.status_code == 200, evidence_twin.text
    assert v2_twin.status_code == 200, v2_twin.text

    # The frozen law: byte-identical v1 and evidence paths.
    assert v1_twin.content == v1_real.content
    assert evidence_twin.content == evidence_real.content

    # The v2 QUERY envelope is where the block lives — and ONLY there: the
    # twin carries no key, while its ``data`` is the real run's ``data``.
    assert "issuer_economics" not in v2_twin.json()
    assert v2_twin.json()["data"] == v2_real.json()["data"]
    assert "issuer_economics" in v2_real.json()


def test_the_envelope_block_is_exactly_the_builders_output(
    entitled_client, monkeypatch, tmp_path,
):
    """The attach is faithful: whatever the bound builder returns is what the
    envelope carries — recorded on the real call and deep-compared (through
    the JSON round trip, which also proves the block is JSON-safe)."""
    api_base._install_warm_owner_state(monkeypatch, tmp_path)
    real = real_registration_for("ai_semiconductors")
    recorded: list = []

    def recording(query, bundle, *, dropped=False):
        out = real.issuer_economics(query, bundle, dropped=dropped)
        recorded.append(out)
        return out

    monkeypatch.setattr(
        theme_research, "registration_for",
        lambda anchor: (
            dataclasses.replace(real, issuer_economics=recording)
            if anchor == "ai_semiconductors" else real_registration_for(anchor)
        ),
    )
    response = entitled_client.post(
        QUERY_ROUTE, json=api_base._v2_theme_query_body(),
    )
    assert response.status_code == 200, response.text
    assert len(recorded) == 1, "the builder must run exactly once per query"
    assert response.json()["issuer_economics"] == dict(recorded[0])

    # The evidence path never runs it, even bound.
    payload = entitled_client.post(QUERY_ROUTE, json=api_base._valid_body()).json()
    refs = [r for r in payload["evidence_refs"] if r.get("kind") == "assertion"]
    assert refs
    evidence = entitled_client.post(EVIDENCE_ROUTE, json=api_base._evidence_body_with(
        refs[0]["assertion_ref"], payload["generation"],
    ))
    assert evidence.status_code == 200, evidence.text
    assert len(recorded) == 1, "evidence path must not compose the block"
