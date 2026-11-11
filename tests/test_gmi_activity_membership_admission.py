"""GMI native activity admission (recovery 2026-10-16, section 9 step 3).

One real positive case, the C01 Micron planned integration of 24GB 8H HBM3E into the
NVIDIA H200 platform, bound to theme:hbm_packaging through the existing owners:
identity through identity_resolution (read only), the source edition, span and purpose
through the company-intelligence disclosure owner, and rights through rights.py (read
only). Five hard negatives: an AMD-style name-prefix hint, an ambiguous Planet hint,
a basket/group-to-micro expression, knowledge-cutoff exclusion, and a prepared
coverage profile that can neither ratify nor lift the group-to-micro refusal.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pytest

from engine.company_intelligence import issuer_disclosure_owner as owner
from engine.theme_graph import membership_evidence as me
from engine.theme_graph import probation
from engine.theme_graph.membership_evidence import (
    ActivityAdmissionRefusal,
    build_activity_membership_evidence,
    build_microtheme_identity_preflight,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/theme_graph/activity_membership_proposal.v1.schema.json"
SPEC = ROOT / owner.SPEC_PATH
RESEARCH = ROOT / "research/theme_graph/microtheme_membership_candidates_2026-10-08.json"
CODE_VERSION = "0" * 40
CREATED = "2026-10-19T06:00:00Z"
AFTER_ALL_KNOWLEDGE = "2026-10-19T00:00:00Z"
MU_NODE = "co:us:MU"
TARGET = "theme:hbm_packaging"


def _identity_row(node_id, symbol, issuer_id, *, state="RESOLVED"):
    """The identity owner's row shape (data/theme_graph/identity_resolution.parquet)."""
    listing = issuer_id.removeprefix("ISS:") if issuer_id else None
    return {
        "schema": "gmi.identity_resolution/v1",
        "node_id": node_id,
        "graph_kind": "company",
        "market_scope": "us",
        "graph_identity_epoch": 1,
        "source_native_symbol": symbol,
        "resolution_asof": "2026-10-18",
        "resolution_state": state,
        "issuer_id": issuer_id,
        "security_id": ("SEC:" + listing) if (listing and state == "RESOLVED") else None,
        "listing_key": listing if state == "RESOLVED" else None,
        "join_method": "master_inception_exact" if state == "RESOLVED" else None,
        "refusal_reason": None if state == "RESOLVED" else "multiple_candidates",
        "computed_at": "2026-10-18T11:03:21Z",
        "engine_version": "theme_graph.v1",
    }


MU_ROW = _identity_row(MU_NODE, "MU", "ISS:US-XNAS-MU")


def _mu_reader(node_id):
    assert node_id == MU_NODE
    return dict(MU_ROW)


def _spec() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def _evidence(**overrides):
    kwargs = dict(issuer_node_id=MU_NODE, target_theme_id=TARGET, role="component_supplier",
                  knowledge_cutoff=AFTER_ALL_KNOWLEDGE, code_version=CODE_VERSION,
                  identity_reader=_mu_reader)
    kwargs.update(overrides)
    return build_activity_membership_evidence(**kwargs)


def _code(**overrides) -> str:
    with pytest.raises(ActivityAdmissionRefusal) as caught:
        _evidence(**overrides)
    return caught.value.code


def _validator():
    return jsonschema.Draft202012Validator(json.loads(CONTRACT.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def evidence():
    return _evidence()


@pytest.fixture
def proposal(evidence):
    return probation.make_activity_membership_proposal(copy.deepcopy(evidence), created=CREATED)


def _curated(row, *, status="RATIFIED", decision="ACCEPT", curator="curator:gmi-desk",
             decided_at="2026-10-19T07:00:00Z"):
    out = copy.deepcopy(row)
    out["status"] = status
    out["curation"] = {"curator": curator, "decision": decision, "decided_at": decided_at,
                       "receipt_sha256": hashlib.sha256(b"curation receipt").hexdigest()}
    return out


@pytest.fixture(scope="module")
def identity_hints():
    # Same reference rows as tests/test_theme_graph_micro_membership_research.py.
    issuer_rows = [
        {"issuer_id": "ISS:US-XNAS-MU", "legal_name": "Micron Technology Inc", "status": "active"},
        {"issuer_id": "ISS:US-XNYS-PL", "legal_name": "Planet Labs PBC", "status": "active"},
        {"issuer_id": "ISS:US-XNYS-PLNT", "legal_name": "Planet Fitness Inc", "status": "active"},
        {"issuer_id": "ISS:US-XNYS-CPT", "legal_name": "Camden Property Trust", "status": "active"},
        {"issuer_id": "ISS:US-XNAS-DEL", "legal_name": "Micron obsolete", "status": "retired"},
    ]
    security_rows = [
        {"security_id": "SEC:" + x["issuer_id"].removeprefix("ISS:"), "issuer_id": x["issuer_id"],
         "issuer_state": "RESOLVED", "listing_key": x["issuer_id"].removeprefix("ISS:"),
         "security_state": None}
        for x in issuer_rows if x["status"] == "active"]
    document = json.loads(RESEARCH.read_text(encoding="utf-8"))
    report = build_microtheme_identity_preflight(
        document, issuer_rows=issuer_rows, security_rows=security_rows,
        issuer_snapshot_sha256="a" * 64, security_snapshot_sha256="b" * 64)
    return {row["record_id"]: row for row in report["candidate_diagnostics"]}


def test_positive_micron_hbm3e_h200_activity_is_bound_and_stays_proposed(evidence, proposal):
    spec = _spec()
    fact, edition = spec["fact"], spec["edition"]
    # Real source identity, read through the owner from the committed record bytes.
    src = evidence["source_evidence"]
    assert src["owner"] == "engine.company_intelligence.issuer_disclosure_owner"
    assert src["disclosure_id"] == fact["disclosure_id"] == edition["disclosure_id"]
    assert src["fact_id"] == fact["fact_id"]
    assert src["fact_revision"] == fact["revision"] == 1
    assert src["edition"]["source_key"] == edition["source_key"]
    assert src["edition"]["source_sha256"] == edition["source_sha256"]
    assert src["edition"]["byte_length"] == edition["source_byte_length"]
    assert src["span"] == fact["span"]
    assert (src["span"]["start_byte"], src["span"]["end_byte"]) == (370936, 371320)
    real = owner.qualify_records(
        CODE_VERSION, SPEC.read_bytes(), (ROOT / owner.RULING_PATH).read_bytes(),
        (ROOT / owner.REGISTRY_PATH).read_bytes(), spec["identities"])
    assert src["owner_bindings"] == dict(real.bindings)
    assert set(src["owner_bindings"]) == {"spec", "purpose", "adoption"}
    # Issuer identity is the owner's row, and the fact names the same issuer.
    assert evidence["issuer"]["issuer_id"] == fact["subject_id"] == "ISS:US-XNAS-MU"
    assert evidence["issuer"]["security_id"] == "SEC:US-XNAS-MU"
    assert evidence["issuer"]["resolution_state"] == "RESOLVED"
    assert evidence["scope"] == {
        "product": fact["product"], "platform": fact["platform"],
        "counterparty_issuer_id": fact["object_id"],
        "segment": {"value": None, "state": "UNDISCLOSED"}}
    assert (evidence["species"], evidence["lifecycle"], evidence["role"]) == (
        "planned_product_integration", "planned", "component_supplier")
    assert evidence["endpoints"] == {"source_node_id": MU_NODE, "target_node_id": TARGET,
                                     "direction": "SOURCE_TO_TARGET"}
    target = evidence["target_definition"]
    assert target["theme_id"] == TARGET and target["tier"] == "micro_theme"
    assert target["crosswalk_sha256"] == hashlib.sha256(
        (ROOT / "config/theme_crosswalk.yml").read_bytes()).hexdigest()
    # Rights are READ, never granted; the C01 source family is not yet registered.
    use = evidence["use_qualification"]
    assert use["target_definition_rights"]["family"] == "mastermind_curated"
    assert use["source_rights"] == {"family": None, "rights_class": None,
                                    "public_emission": "RIGHTS_FAMILY_UNRESOLVED"}
    assert use["purpose"]["permitted_purpose"] == owner.PURPOSE
    assert use["purpose"]["ruling_binding_sha256"] == real.bindings["purpose"]
    assert use["graph_membership_use"] == "NOT_GRANTED"
    # Separate clocks, each with its own state.
    clocks = evidence["clocks"]
    assert clocks["publication"] == {"value": edition["published_date"], "precision": "date",
                                     "state": "KNOWN"}
    assert clocks["observation"]["value"] == edition["known_at"]
    assert clocks["knowledge"]["value"] == fact["known_at"]
    assert clocks["effective"]["state"] == "UNDISCLOSED"
    assert {clocks[k]["state"] for k in ("admitted", "correction", "served_generation")} == {
        "NOT_APPLICABLE"}
    # The proposal is PROPOSED with no curation, validates, and is not ratified.
    assert proposal["status"] == "PROPOSED" and proposal["curation"] is None
    assert proposal["authority_caps"] == {"may_ratify": False, "may_materialize": False,
                                          "may_publish": False}
    assert probation.validate_activity_membership_proposal(proposal) == []
    assert list(_validator().iter_errors(proposal)) == []
    assert probation.ratified_activity_memberships([proposal]) == []
    assert probation.ratified([proposal]) == []
    again = probation.make_activity_membership_proposal(_evidence(), created=CREATED)
    assert again["proposal_id"] == proposal["proposal_id"]


@pytest.mark.needs_full_checkout("data")
def test_positive_resolves_micron_through_the_real_identity_owner():
    out = _evidence(identity_reader=None)
    assert out["issuer"]["node_id"] == MU_NODE
    assert out["issuer"]["issuer_id"] == "ISS:US-XNAS-MU"
    assert out["issuer"]["resolution_state"] == "RESOLVED"


def test_amd_style_prefix_identity_is_refused(identity_hints):
    hint = identity_hints["M008"]
    assert hint["identity_hint_state"] == "NO_NAME_PREFIX_IN_REFERENCE"
    assert _code(basis=hint) == "IDENTITY_HINT_NOT_ADMISSION"
    # A hint that DID name one issuer is still only a hint, never identity.
    assert identity_hints["M001"]["identity_hint_state"] == "POSSIBLE_ONE_CURRENT_ISSUER"
    assert _code(basis=identity_hints["M001"]) == "IDENTITY_HINT_NOT_ADMISSION"
    # A node the owner resolves to a different issuer cannot carry Micron's fact.
    amd = _identity_row("co:us:AMD", "AMD", "ISS:US-XNAS-AMD")
    assert _code(issuer_node_id="co:us:AMD", identity_reader=lambda node: dict(amd)) == (
        "ISSUER_IDENTITY_MISMATCH")
    # A reader answering for a different node is a mismatch too.
    assert _code(identity_reader=lambda node: dict(amd)) == "ISSUER_IDENTITY_MISMATCH"


def test_ambiguous_planet_identity_is_refused(identity_hints):
    hint = identity_hints["M073"]
    assert hint["identity_hint_state"] == "AMBIGUOUS_NAME_PREFIX"
    assert {x["issuer_id"] for x in hint["possible_current_issuer_refs"]} == {
        "ISS:US-XNYS-PL", "ISS:US-XNYS-PLNT"}
    assert _code(basis=hint) == "IDENTITY_HINT_NOT_ADMISSION"
    ambiguous = _identity_row(MU_NODE, "MU", None, state="AMBIGUOUS")
    assert _code(identity_reader=lambda node: dict(ambiguous)) == "AMBIGUOUS_IDENTITY"
    unresolved = _identity_row(MU_NODE, "MU", None, state="UNRESOLVED")
    assert _code(identity_reader=lambda node: dict(unresolved)) == "IDENTITY_UNRESOLVED"

    def broken(node):
        raise LookupError("owner unavailable")

    assert _code(identity_reader=broken) == "IDENTITY_UNRESOLVED"


@pytest.mark.parametrize("basis", [
    {"kind": "basket_expression", "basket_id": "basket:baskets_china_ths:hbm",
     "qualification": "QUALIFIED"},
    {"kind": "group_to_micro", "group": "theme_group:semiconductors", "qualified": True},
    {"kind": "native_disclosure_fact", "via": "basket:baskets:memory"},
    "native_disclosure_fact",
])
def test_basket_group_to_micro_expression_is_refused_even_when_marked_qualified(basis):
    assert _code(basis=basis) == "GROUP_TO_MICRO_REFUSED"
    for target in ("basket:baskets_china_ths:hbm", "ltheme:finviz:memory",
                   "theme_group:semiconductors"):
        assert _code(target_theme_id=target) == "ENDPOINT_NOT_ADMITTED"
    assert _code(issuer_node_id="basket:baskets:memory") == "ENDPOINT_NOT_ADMITTED"


def test_basket_endpoint_cannot_be_written_into_a_proposal(proposal):
    row = copy.deepcopy(proposal)
    row["evidence"]["endpoints"]["target_node_id"] = "basket:baskets_china_ths:hbm"
    assert probation.validate_activity_membership_proposal(row)


def test_prepared_profile_cannot_ratify_or_lift_group_to_micro_refusal(evidence, proposal):
    from scripts import theme_coverage_gaps as gaps
    from tests.test_theme_graph_local_plane import _m1_coverage_fixture

    ids, nodes, edges, now = _m1_coverage_fixture(3, shared=False)
    profile = copy.deepcopy(gaps.analyse(ids, nodes, edges, now=now)["observation_profile"])
    assert profile["rights"]["public_display_allowed"] is False
    # A prepared profile is not an admission basis: the group-to-micro refusal holds.
    assert _code(basis=profile) == "GROUP_TO_MICRO_REFUSED"
    # A profile, a status or a curation smuggled into evidence is refused at construction.
    for key, value in (("observation_profile", profile), ("status", "RATIFIED"),
                       ("curation", {"curator": "coverage_gap"}), ("ratified_by", "profile")):
        smuggled = copy.deepcopy(evidence)
        smuggled[key] = value
        with pytest.raises(probation.ActivityProposalRefusal) as caught:
            probation.make_activity_membership_proposal(smuggled, created=CREATED)
        assert caught.value.code == "PROPOSER_CANNOT_CURATE"
    # A row flipped to RATIFIED without a named curator decision is not ratified.
    flipped = copy.deepcopy(proposal)
    flipped["status"] = "RATIFIED"
    assert probation.validate_activity_membership_proposal(flipped)
    as_curation = copy.deepcopy(flipped)
    as_curation["curation"] = profile
    assert probation.validate_activity_membership_proposal(as_curation)
    assert probation.ratified_activity_memberships([flipped, as_curation]) == []
    # The legacy queue never treats a profile-bearing proposal as ratified either.
    legacy = probation.make_proposal(kind="new_theme", subject={"instrument_ids": ids},
                                     evidence={"legacy": "freeform"}, proposed_by="coverage_gap")
    legacy["evidence"]["observation_profile"] = profile
    assert probation.ratified([legacy]) == []
    # And there is no ratify helper to call.
    assert [name for name in dir(probation) if name.lower().startswith("ratify")] == []


def test_knowledge_cutoff_before_fact_known_at_excludes_the_activity():
    fact, edition = _spec()["fact"], _spec()["edition"]
    assert fact["known_at"] == "2026-10-11T17:09:10.298093+00:00"

    def must_not_read(node):
        raise AssertionError("identity was read before the knowledge cutoff filter")

    # One instant before the fact was known: excluded before identity is consulted.
    assert _code(knowledge_cutoff="2026-10-11T17:09:10Z",
                 identity_reader=must_not_read) == "KNOWLEDGE_CUTOFF_EXCLUDED"
    # Before the edition was known: excluded as well.
    assert edition["known_at"].startswith("2026-10-09T01:38")
    assert _code(knowledge_cutoff="2026-10-09T00:00:00Z",
                 identity_reader=must_not_read) == "KNOWLEDGE_CUTOFF_EXCLUDED"
    # Exactly at the fact's knowledge time it is admitted as evidence.
    assert _evidence(knowledge_cutoff=fact["known_at"])["source_evidence"]["fact_id"] == (
        fact["fact_id"])
    for bad in ("2026-10-19", "2026-10-19T00:00:00", None):
        assert _code(knowledge_cutoff=bad) == "KNOWLEDGE_CUTOFF_INVALID"


def test_tampered_disclosure_bytes_are_refused_by_the_owner(tmp_path):
    for rel in (owner.SPEC_PATH, owner.RULING_PATH, owner.REGISTRY_PATH):
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dest)
    shutil.copyfile(ROOT / "config/theme_crosswalk.yml", tmp_path / "config/theme_crosswalk.yml")
    # The verbatim copy qualifies through the owner.
    assert _evidence(root=tmp_path)["source_evidence"]["fact_id"] == _spec()["fact"]["fact_id"]
    spec_path = tmp_path / owner.SPEC_PATH
    tampered = spec_path.read_text(encoding="utf-8").replace("NVIDIA H200", "NVIDIA H300", 1)
    assert tampered != SPEC.read_text(encoding="utf-8")
    spec_path.write_text(tampered, encoding="utf-8")
    assert _code(root=tmp_path) == "SOURCE_OWNER_REFUSED"
    spec_path.unlink()
    assert _code(root=tmp_path) == "SOURCE_OWNER_REFUSED"


def test_unknown_target_definition_and_unadmitted_species_are_refused():
    assert _code(target_theme_id="theme:not_a_current_definition") == "TARGET_DEFINITION_UNKNOWN"
    assert _code(role="beneficiary") == "ROLE_NOT_ADMITTED"
    real = me._default_activity_disclosure(ROOT, CODE_VERSION)
    for kind, lifecycle in (("product_integration", "shipped"), ("supply_agreement", "planned"),
                            ("revenue_concentration", "reported")):
        spec = copy.deepcopy(real.spec)
        spec["fact"]["kind"], spec["fact"]["lifecycle"] = kind, lifecycle
        reader = (lambda root, code_version, spec=spec:
                  SimpleNamespace(spec=spec, bindings=dict(real.bindings)))
        assert _code(disclosure_reader=reader) == "SPECIES_NOT_ADMITTED"


def test_named_curation_is_the_only_path_to_ratified(proposal):
    assert probation.ratified_activity_memberships([proposal]) == []
    for bad in (_curated(proposal, curator=""), _curated(proposal, curator="   "),
                _curated(proposal, decision="REJECT"),
                _curated(proposal, decided_at="2026-10-11T00:00:00Z"),
                _curated(proposal, decided_at="2026-10-19"),
                _curated(proposal, status="REJECTED", decision="ACCEPT")):
        assert probation.validate_activity_membership_proposal(bad), bad["curation"]
        assert probation.ratified_activity_memberships([bad]) == []
    proposed_with_curation = copy.deepcopy(proposal)
    proposed_with_curation["curation"] = _curated(proposal)["curation"]
    assert probation.validate_activity_membership_proposal(proposed_with_curation)

    rejected = _curated(proposal, status="REJECTED", decision="REJECT")
    assert probation.validate_activity_membership_proposal(rejected) == []
    assert probation.ratified_activity_memberships([rejected]) == []

    accepted = _curated(proposal)
    assert probation.validate_activity_membership_proposal(accepted) == []
    [kept] = probation.ratified_activity_memberships([proposal, rejected, accepted])
    assert kept == accepted and kept is not accepted
    # Ratification of the proposal grants no graph use and no authority.
    assert kept["evidence"]["use_qualification"]["graph_membership_use"] == "NOT_GRANTED"
    assert set(kept["authority_caps"].values()) == {False}
    granted = copy.deepcopy(accepted)
    granted["evidence"]["use_qualification"]["graph_membership_use"] = "GRANTED"
    assert probation.validate_activity_membership_proposal(granted)
    capped = copy.deepcopy(accepted)
    capped["authority_caps"]["may_materialize"] = True
    assert probation.validate_activity_membership_proposal(capped)


def test_null_magnitude_states_are_distinct_and_never_zero(evidence, proposal):
    assert _spec()["fact"]["amount"] is None and _spec()["fact"]["economic_share"] is None
    assert evidence["magnitudes"] == {
        "amount": {"value": None, "state": "UNDISCLOSED"},
        "economic_share": {"value": None, "state": "UNDISCLOSED"}}
    assert me._activity_magnitude(None) == {"value": None, "state": "UNDISCLOSED"}
    assert me._activity_magnitude(0) == {"value": 0, "state": "KNOWN_ZERO"}
    assert me._activity_magnitude(12.5) == {"value": 12.5, "state": "KNOWN"}
    for bad in (True, False, "0", "12"):
        with pytest.raises(ActivityAdmissionRefusal) as caught:
            me._activity_magnitude(bad)
        assert caught.value.code == "MAGNITUDE_INVALID"
    validator = _validator()

    def errors_for(magnitude):
        row = copy.deepcopy(proposal)
        row["evidence"]["magnitudes"]["amount"] = magnitude
        return list(validator.iter_errors(row))

    for state in ("NOT_APPLICABLE", "UNDISCLOSED", "UNAVAILABLE", "STALE"):
        assert errors_for({"value": None, "state": state}) == []
        assert errors_for({"value": 0, "state": state}), state
    assert errors_for({"value": 0, "state": "KNOWN_ZERO"}) == []
    assert errors_for({"value": 1, "state": "KNOWN_ZERO"})
    assert errors_for({"value": 0, "state": "KNOWN"})
    assert errors_for({"value": None, "state": "KNOWN"})
    assert errors_for({"value": 3, "state": "KNOWN"}) == []
    assert errors_for({"value": None, "state": "ZERO"})


# ---------------------------------------------------------------------------------------
# 2026-10-21 additive amendment: the second admitted activity species
# principal_business_activity (role operator, lifecycle current, segment-only scope,
# activity: fact ids). The principal fixture is the C01 evidence fixture with its
# species-owned fields rewritten; probation's proposal path must work unchanged.
# ---------------------------------------------------------------------------------------

PRINCIPAL_SPECIES = "principal_business_activity"


def _principal_evidence(evidence):
    principal = copy.deepcopy(evidence)
    principal["species"] = PRINCIPAL_SPECIES
    principal["scope"] = {"segment": principal["scope"]["segment"]}
    principal["role"] = "operator"
    principal["lifecycle"] = "current"
    principal["source_evidence"]["fact_id"] = (
        "activity:" + hashlib.sha256(b"principal_business_activity:ISS:US-XNAS-MU").hexdigest())
    return principal


def test_principal_business_activity_proposes_and_ratifies_without_graph_use(evidence,
                                                                             proposal):
    principal = _principal_evidence(evidence)
    row = probation.make_activity_membership_proposal(principal, created=CREATED)
    assert row["status"] == "PROPOSED" and row["curation"] is None
    assert row["proposal_id"] == probation.activity_proposal_id(principal)
    assert probation.validate_activity_membership_proposal(row) == []
    assert row["evidence"]["scope"] == {"segment": evidence["scope"]["segment"]}
    assert row["evidence"]["role"] == "operator"
    assert row["evidence"]["lifecycle"] == "current"
    assert row["evidence"]["source_evidence"]["fact_id"].startswith("activity:")

    ratified = _curated(row)
    assert probation.validate_activity_membership_proposal(ratified) == []
    [kept] = probation.ratified_activity_memberships([row, proposal, ratified])
    assert kept == ratified and kept is not ratified
    # Ratifying a principal activity grants no graph-membership use and no authority.
    assert kept["evidence"]["use_qualification"]["graph_membership_use"] == "NOT_GRANTED"
    assert set(kept["authority_caps"].values()) == {False}


def test_principal_and_c01_shapes_cannot_mix(evidence):
    def refused(mutate, *, principal: bool) -> None:
        candidate = _principal_evidence(evidence) if principal else copy.deepcopy(evidence)
        mutate(candidate)
        with pytest.raises(probation.ActivityProposalRefusal) as caught:
            probation.make_activity_membership_proposal(candidate, created=CREATED)
        assert caught.value.code == "PROPOSAL_INVALID"

    # A principal row never wears a C01 shape.
    refused(lambda e: e.update(role="component_supplier"), principal=True)
    refused(lambda e: e.update(lifecycle="planned"), principal=True)
    refused(lambda e: e["scope"].update(product=copy.deepcopy(evidence["scope"]["product"])),
            principal=True)
    refused(lambda e: e["source_evidence"].update(fact_id="integration:" + "0" * 64),
            principal=True)
    # A C01 row never wears a principal shape.
    refused(lambda e: e.update(role="operator"), principal=False)
    refused(lambda e: e.update(lifecycle="current"), principal=False)
    refused(lambda e: e.update(scope={"segment": e["scope"]["segment"]}), principal=False)
