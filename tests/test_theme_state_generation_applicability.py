"""GMI §9 step 4: generation-specific ThemeState eligibility + real owner readers.

Binds three facts the shadow ThemeState must never blur:

* old program acceptance (the original D2E run / graph publication) is a
  historical program fact and never qualifies current data;
* a current-data qualification applies only to the exact subject and graph
  generation it was computed over (a later subject generation does not inherit it);
* the real owner reader supplies identity/membership/rights through the EXISTING
  adapter interface only, never eligibility (D2E stays unsealed).

The incumbent GRAPH_SHADOW_STATE writer now constructs this native consistency
reader. Its capture/validation/shadow-only atomic publication boundaries remain
pinned by tests/test_build_thematic_state_shadow_graph_state.py::test_t9_source_shape.
This wiring does not seal eligibility or promote a current generation.
"""
from __future__ import annotations

import copy
import json

import pytest

from engine.neuralweb import theme_state_adapter as adapter
from engine.theme_graph import theme_state, theme_state_owner_readers as readers
from scripts import build_thematic_state as builder
from tests import test_theme_state_owner_adapter as owner_fixture
from tests.test_theme_graph_state import GRAPH, compose, module, receipt, subject
from tests.test_theme_state_owner_adapter import world  # noqa: F401  (fixture)
from tests.test_theme_state_production import production_world  # noqa: F401  (fixture)

LOCAL = "ltheme:finviz:power_grid"
# Cutoff after the controlled owners' date-only clocks are provable (same-day
# date-only knowledge stays unproven at the effective date itself).
READER_KNOWN = "2026-10-04T10:00:00Z"
SHADOW = "data/theme_graph/shadow_theme_state.v1.json"


def qualified_subject(applicability, node=LOCAL):
    raw = subject(node=node, qualified=True)
    payload = {"status": "QUALIFIED", "policy_revision": "d2e-r1", "reason_codes": []}
    if applicability is not None:
        payload["applicability"] = applicability
    raw["owners"]["eligibility"] = receipt("eligibility", payload, node)
    return raw


def applicability(basis="CURRENT_DATA_QUALIFICATION", generation=GRAPH, node=LOCAL):
    return {"basis": basis, "qualified_graph_generation_id": generation, "subject_id": node}


def local_subject(native, qualified=False):
    raw = subject(node="ltheme:finviz:" + native, qualified=qualified)
    raw["native_id"] = native
    return raw


def only(state):
    assert state["subject_count"] == 1
    return state["subjects"][0]


# -- generation-specific eligibility applicability ---------------------------------

def test_original_generation_acceptance_is_not_applied_to_a_later_subject_generation():
    # The old program acceptance is never current qualification, strict or not.
    for strict in (False, True):
        state = compose([qualified_subject(applicability("ORIGINAL_PROGRAM_ACCEPTANCE", "graph-20261001"))],
                        require_eligibility_applicability=strict)
        module().validate_state(state)
        eligibility = only(state)["eligibility"]
        assert eligibility["status"] == "NOT_QUALIFIED"
        assert "ORIGINAL_PROGRAM_ACCEPTANCE_NOT_CURRENT_QUALIFICATION" in eligibility["reason_codes"]
    # A current-data qualification computed over an EARLIER graph generation does
    # not carry forward to the later generation being composed.
    state = compose([qualified_subject(applicability(generation="graph-20261001"))],
                    require_eligibility_applicability=True)
    module().validate_state(state)
    eligibility = only(state)["eligibility"]
    assert eligibility["status"] == "NOT_QUALIFIED"
    assert eligibility["reason_codes"] == ["ELIGIBILITY_GENERATION_NOT_APPLICABLE"]
    assert eligibility["policy_revision"] == "d2e-r1"
    # Bound to exactly this subject and generation, the owner verdict stands.
    state = compose([qualified_subject(applicability())], require_eligibility_applicability=True)
    module().validate_state(state)
    assert only(state)["eligibility"] == {"status": "QUALIFIED", "policy_revision": "d2e-r1", "reason_codes": []}


def test_subject_mismatch_and_undeclared_applicability_in_strict_mode_refuse():
    state = compose([qualified_subject(applicability(node="ltheme:finviz:housing"))],
                    require_eligibility_applicability=True)
    module().validate_state(state)
    assert only(state)["eligibility"]["reason_codes"] == ["ELIGIBILITY_SUBJECT_NOT_APPLICABLE"]
    strict = compose([qualified_subject(None)], require_eligibility_applicability=True)
    module().validate_state(strict)
    assert only(strict)["eligibility"]["status"] == "NOT_QUALIFIED"
    assert only(strict)["eligibility"]["reason_codes"] == ["ELIGIBILITY_APPLICABILITY_UNDECLARED"]
    # Legacy (default) callers keep the legacy verdict for an undeclared receipt.
    assert only(compose([qualified_subject(None)]))["eligibility"]["status"] == "QUALIFIED"


def test_default_compose_is_byte_identical_to_legacy_for_existing_inputs():
    inputs = [subject(), local_subject("housing", qualified=True), subject("theme:grid")]
    default = compose(copy.deepcopy(inputs))
    explicit = compose(copy.deepcopy(inputs), require_eligibility_applicability=False)
    assert json.dumps(default, sort_keys=True) == json.dumps(explicit, sort_keys=True)
    assert default["state_sha256"] == explicit["state_sha256"]
    # Strict mode only ever ADDS refusals; it never grants.
    strict = compose(copy.deepcopy(inputs), require_eligibility_applicability=True)
    module().validate_state(strict)
    for loose, tight in zip(default["subjects"], strict["subjects"]):
        assert set(loose["eligibility"]["reason_codes"]) <= set(tight["eligibility"]["reason_codes"])
        assert tight["eligibility"]["status"] != "QUALIFIED"


@pytest.mark.parametrize("declared", [
    "graph-20261003",
    {"basis": "CURRENT_DATA_QUALIFICATION", "qualified_graph_generation_id": GRAPH},
    {"basis": "LATEST", "qualified_graph_generation_id": GRAPH, "subject_id": LOCAL},
    {"basis": "CURRENT_DATA_QUALIFICATION", "qualified_graph_generation_id": "", "subject_id": LOCAL},
    {"basis": "CURRENT_DATA_QUALIFICATION", "qualified_graph_generation_id": GRAPH, "subject_id": LOCAL,
     "valid_until": "2099-01-01"},
])
def test_malformed_applicability_raises(declared):
    with pytest.raises(ValueError, match="invalid eligibility applicability"):
        compose([qualified_subject(declared)])


def test_publication_applicability_is_generation_specific_and_never_grants_in_shadow():
    owner = module()
    first = owner.compose_state([qualified_subject(applicability())], graph_generation_id=GRAPH,
                                owner_generations={role: role + "-20261003" for role in
                                                   ("ontology", "identity", "membership", "rights",
                                                    "eligibility", "narrative", "specialist")},
                                effective_at="2026-10-03", known_at="2026-10-03T12:00:00Z",
                                generated_at="2026-10-03T12:00:00Z", require_eligibility_applicability=True)
    owner.validate_state(first)
    answer = owner.publication_applicability(first, subject_id=LOCAL, generation_id=first["generation_id"],
                                             state_sha256=first["state_sha256"])
    assert answer["may_publish"] is False and answer["applicable"] is False
    assert "SHADOW_MODE_NOT_PUBLISHABLE" in answer["reason_codes"]
    assert "AUTHORITY_DENIES_PUBLICATION" in answer["reason_codes"]
    assert "VENDOR_FAMILY_NOT_PUBLISHABLE" in answer["reason_codes"]  # finviz local stays unpublishable
    assert "PUBLICATION_GENERATION_NOT_APPLICABLE" not in answer["reason_codes"]
    # An older generation's digest is never read as applying to this generation.
    stale = owner.publication_applicability(first, subject_id=LOCAL, generation_id="0" * 32,
                                            state_sha256="0" * 64)
    assert "PUBLICATION_GENERATION_NOT_APPLICABLE" in stale["reason_codes"] and stale["may_publish"] is False
    absent = owner.publication_applicability(first, subject_id="theme:grid", generation_id=first["generation_id"],
                                             state_sha256=first["state_sha256"])
    assert "PUBLICATION_SUBJECT_ABSENT" in absent["reason_codes"]
    # A refused (earlier-generation) verdict forged to QUALIFIED never validates.
    refused = compose([qualified_subject(applicability(generation="graph-20261001"))],
                      require_eligibility_applicability=True)
    assert only(refused)["eligibility"]["status"] == "NOT_QUALIFIED"
    forged = copy.deepcopy(refused)
    forged["subjects"][0]["eligibility"] = {"status": "QUALIFIED", "policy_revision": "d2e-r1", "reason_codes": []}
    with pytest.raises(ValueError):
        owner.publication_applicability(forged, subject_id=LOCAL, generation_id=forged["generation_id"],
                                        state_sha256=forged["state_sha256"])


# -- real owner reader through the existing adapter interface ----------------------

def _composed(world, reader=None):
    options = {} if reader is None else {"owner_readers": reader}
    bundle = adapter.capture_owner_bundle(world[0], effective_at=owner_fixture.EFFECTIVE, known_at=READER_KNOWN,
                                          **options)
    composed = adapter.compose_from_owner_bundle(bundle, generated_at=owner_fixture.EMITTED)
    return {s["node_id"]: s for s in composed["state"]["subjects"]}, composed["state"]


class Recording:
    def __init__(self, real, tamper=None):
        self.real, self.tamper, self.results = real, tamper, []

    def read_state_qualification(self, **kwargs):
        if self.tamper is not None:
            kwargs = {**kwargs, "native_reads": self.tamper(copy.deepcopy(dict(kwargs["native_reads"])))}
        result = self.real.read_state_qualification(**kwargs)
        self.results.append((kwargs["node_id"], copy.deepcopy(result)))
        return result


def test_real_reader_receipts_are_admitted_by_the_existing_adapter(world):
    without, _ = _composed(world)
    recording = Recording(readers.StateQualificationReader(world[0]))
    with_reader, state = _composed(world, recording)
    theme_state.validate_state(state)
    local_themes = sorted(node for node in with_reader if node.startswith("ltheme:"))
    assert local_themes == ["ltheme:finviz:housing", "ltheme:finviz:power_grid", "ltheme:finviz:travel",
                            "ltheme:ths:900001"]
    for node in local_themes:
        before, after = set(without[node]["reason_codes"]), set(with_reader[node]["reason_codes"])
        assert {"MEMBERSHIP_UNAVAILABLE", "IDENTITY_UNAVAILABLE", "RIGHTS_UNAVAILABLE"} <= before
        assert not after & {"MEMBERSHIP_UNAVAILABLE", "IDENTITY_UNAVAILABLE", "RIGHTS_UNAVAILABLE",
                            "RIGHTS_NOT_ADMITTED"}, (node, after)
        assert after < before
        receipts = with_reader[node]["owner_receipts"]
        assert receipts["membership"]["owner"] == readers.MEMBERSHIP_OWNER
        assert receipts["identity"]["owner"] == readers.IDENTITY_OWNER
        assert receipts["rights"]["owner"] == readers.RIGHTS_OWNER
        for role in ("membership", "identity", "rights"):
            assert receipts[role]["schema"] == readers.RECEIPT_SCHEMA
            assert receipts[role]["subject_id"] == node
        # D2E stays unsealed: the reader never qualifies a subject.
        assert with_reader[node]["eligibility"] == {"status": "NOT_QUALIFIED", "policy_revision": None,
                                                    "reason_codes": ["D2E_UNSEALED"]}
    assert recording.results and all(result is None or set(result) == {"owner_receipts", "source_receipts"}
                                      for _, result in recording.results)


def _forge_membership(native_reads):
    membership = native_reads.get("membership")
    if isinstance(membership, dict) and isinstance(membership.get("value"), dict) \
            and isinstance(membership["value"].get("members"), list) and membership["value"]["members"]:
        membership["value"]["members"] = list(membership["value"]["members"]) + ["FORGED"]
    return native_reads


def test_real_reader_refuses_when_its_reread_disagrees_with_the_capture(world):
    recording = Recording(readers.StateQualificationReader(world[0]), tamper=_forge_membership)
    subjects, _ = _composed(world, recording)
    emitted = [(node, result) for node, result in recording.results if node.startswith("ltheme:")]
    assert emitted
    for node, result in emitted:
        assert result is not None and "rights" in result["owner_receipts"], node  # reader still alive
        assert "membership" not in result["owner_receipts"], node  # forged read never becomes a receipt
        assert "identity" not in result["owner_receipts"], node
        assert "MEMBERSHIP_UNAVAILABLE" in subjects[node]["reason_codes"], node


def test_real_reader_never_emits_eligibility(world):
    recording = Recording(readers.StateQualificationReader(world[0]))
    subjects, _ = _composed(world, recording)
    assert any(result for _, result in recording.results)
    for _, result in recording.results:
        if result is not None:
            assert "eligibility" not in result["owner_receipts"]
            assert set(result["owner_receipts"]) <= {"identity", "membership", "rights"}
            assert result["source_receipts"] == {}
    for row in subjects.values():
        assert row["eligibility"]["status"] == "NOT_QUALIFIED"
        assert "D2E_UNSEALED" in row["eligibility"]["reason_codes"]


def test_existing_shadow_writer_uses_the_real_reader_without_promoting_eligibility(
        production_world, monkeypatch):
    root = production_world
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    constructions = []
    real_init = readers.StateQualificationReader.__init__

    def record(self, reader_root):
        constructions.append(reader_root)
        real_init(self, reader_root)

    monkeypatch.setattr(readers.StateQualificationReader, "__init__", record)
    assert builder.build(root, mode="GRAPH_SHADOW_STATE", generated_at=owner_fixture.EMITTED) == 0
    assert constructions == [root]
    written = json.loads((root / SHADOW).read_text())
    bundle = adapter.capture_owner_bundle(root, owner_readers=readers.StateQualificationReader(root),
                                          effective_at=owner_fixture.EMITTED[:10],
                                          known_at=owner_fixture.EMITTED)
    shadow = adapter.compose_state_only_from_owner_bundle(bundle, generated_at=owner_fixture.EMITTED)
    theme_state.validate_state(shadow)
    assert written == shadow
    assert shadow["mode"] == "shadow" and shadow["authority"]["may_publish"] is False
    assert all(row["eligibility"]["status"] == "NOT_QUALIFIED" for row in shadow["subjects"])
    reader_roles = {role for row in shadow["subjects"] for role, value in row["owner_receipts"].items()
                    if isinstance(value, dict) and value.get("schema") == readers.RECEIPT_SCHEMA}
    assert reader_roles and reader_roles <= {"identity", "membership", "rights"}
