"""Source-grain regressions. Original contract suite and fixtures stay untouched."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import pytest
from lib.economic_propagation import (
    BINDING_KILLS, EconomicPropagationError, compose_hypothesis, validate_hypothesis,
)

# Load only this repository's existing fixture builders, never an installed tests package.
_fixture_path = Path(__file__).with_name("test_economic_propagation_hypothesis_contract.py")
_fixture_spec = importlib.util.spec_from_file_location("_k3d_original_fixture_builders", _fixture_path)
assert _fixture_spec is not None and _fixture_spec.loader is not None
_fixture_module = importlib.util.module_from_spec(_fixture_spec)
_fixture_spec.loader.exec_module(_fixture_module)
_source_event = _fixture_module._source_event
_target = _fixture_module._target
_admission = _fixture_module._admission
_g1_leg = _fixture_module._g1_leg
_mechanism_proposal = _fixture_module._mechanism_proposal
_identity = _fixture_module._identity
_build_golden_supported_hypothesis = _fixture_module._build_golden_supported_hypothesis
_rehash = _fixture_module._rehash
_codes = _fixture_module._codes
_ALTERNATIVES = _fixture_module._ALTERNATIVES
_FALSIFIERS = _fixture_module._FALSIFIERS
_EXPIRY = _fixture_module._EXPIRY
ASOF = _fixture_module.ASOF
COMPILED_AT = _fixture_module.COMPILED_AT
GOLDEN_BUILDERS = _fixture_module.GOLDEN_BUILDERS
FIXTURE_DIR = _fixture_module.FIXTURE_DIR

# Source-grain cases on the same #6514 carrier; same existing K3-D CI owner.
# Uses the existing suite builders; native execution must be recorded separately.
_SOURCE_GRAIN_BAD_VALUES = [
    None, "", " ", "\t", "\u00a0", 0, 1, False, True, [], {}, {"opaque": 1},
    "id\npart", "id\rpart", "x" * 121,
]


def _source_grain_probe_kwargs():
    return dict(
        source_event=_source_event(), target=_target(), asof=ASOF, compiled_at=COMPILED_AT,
        generator_admissions=[_admission("gen_disclosed_customer_supplier", "graph_1",
                                         "disclosed_customer_supplier")],
        relationship_paths=[_g1_leg()], similarity_evidence=[], market_evidence=[],
        mechanism_proposal=_mechanism_proposal(),
        alternatives=copy.deepcopy(_ALTERNATIVES), falsifiers=copy.deepcopy(_FALSIFIERS),
        expiry=copy.deepcopy(_EXPIRY),
    )


@pytest.mark.parametrize("field", ["issuer_id", "security_id"])
@pytest.mark.parametrize("value", _SOURCE_GRAIN_BAD_VALUES)
def test_resolved_source_grain_refuses_before_graph_derivation(field, value, monkeypatch):
    import lib.economic_propagation as subject
    kwargs = _source_grain_probe_kwargs()
    kwargs["source_event"]["source_identity"][field] = value
    before = copy.deepcopy(kwargs)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("semantic graph derivation ran before source grain refusal")

    monkeypatch.setattr(subject, "derive_graph_states", forbidden)
    with pytest.raises(EconomicPropagationError, match="K3D_R015"):
        subject.compose_hypothesis(**kwargs)
    assert kwargs == before


@pytest.mark.parametrize("field", ["issuer_id", "security_id"])
@pytest.mark.parametrize("value", _SOURCE_GRAIN_BAD_VALUES)
def test_resolved_source_grain_validator_rejects_rehashed_record(field, value):
    record = _build_golden_supported_hypothesis()
    record["source_event"]["source_identity"][field] = value
    record = _rehash(record)  # must fail for grain, not a stale content hash
    assert "K3D_R015" in _codes(validate_hypothesis(record))


@pytest.mark.parametrize("field", ["issuer_id", "security_id"])
def test_missing_resolved_source_grain_refuses_before_derivation(field, monkeypatch):
    import lib.economic_propagation as subject
    kwargs = _source_grain_probe_kwargs()
    del kwargs["source_event"]["source_identity"][field]

    def forbidden(*_args, **_kwargs):
        raise AssertionError("semantic graph derivation ran for absent source grain")

    monkeypatch.setattr(subject, "derive_graph_states", forbidden)
    with pytest.raises(EconomicPropagationError, match="K3D_R015"):
        subject.compose_hypothesis(**kwargs)


@pytest.mark.parametrize("state", ["NOT_IN_MASTER", "UNRESOLVED", "CONFLICTING",
                                  "UNSUPPORTED_MARKET", "DEFERRED_IDENTITY_EXCEPTION",
                                  "ENTITY_TYPE_CONFLICT"])
def test_source_grain_repair_preserves_truthful_nonresolved_abstention(state):
    kwargs = _source_grain_probe_kwargs()
    kwargs["source_event"]["source_identity"] = _identity(state, issuer=None, security=None)
    kwargs.update(generator_admissions=[], relationship_paths=[], mechanism_proposal=None)
    record = compose_hypothesis(**kwargs)
    assert validate_hypothesis(record) == []
    assert record["hypothesis_state"] == "abstained"
    assert record["abstention"]["abstained"] is True
    assert record["source_event"]["source_identity"]["resolution_state"] == state
    assert record["relationship_paths"] == []
    assert record["economic_share"] is None
    assert record["binding_kills"] == list(BINDING_KILLS)


def test_source_grain_defect_is_not_cleared_by_claiming_abstention():
    record = _build_golden_supported_hypothesis()
    record["source_event"]["source_identity"].update(issuer_id=None, security_id=None)
    record["abstention"] = {"abstained": True, "reasons": ["unresolved_identity"]}
    record["hypothesis_state"] = "abstained"
    record = _rehash(record)
    assert "K3D_R015" in _codes(validate_hypothesis(record))


def test_source_grain_repair_preserves_all_golden_objects_byte_for_byte():
    # Existing fixture files, not newly generated expected values, are the control.
    for stem, build in GOLDEN_BUILDERS.items():
        old_record = json.loads((FIXTURE_DIR / (stem + ".json")).read_text(encoding="utf-8"))
        assert build() == old_record
        assert validate_hypothesis(old_record) == []
