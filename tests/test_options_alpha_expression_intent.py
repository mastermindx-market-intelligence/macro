"""Discriminating tests for the pure research-expression intent codec.

Self-contained synthetic fixtures only: no sibling test imports, no production
or private source reads, no network, no clock reads and no writes. Incumbent
engine modules appear only as the exact SOURCE commit's frozen policy identity,
canonical-byte helpers the codec itself reuses, and the positive fixture's
contract check.
"""
from __future__ import annotations

import copy
import hashlib

import pytest

from engine import options_alpha_expression_formation as formation
from engine import options_nbbo_cohort as cohort
from engine.options_alpha_candidate_feed import canonical_bytes

from engine.options_alpha_expression_intent import (
    ELIGIBILITY,
    EXPRESSION_ID_PREFIX,
    INTENT_SCHEMA,
    TERMS_SCHEMA,
    IntentError,
    make_expression_intent,
    validate_expression_intent,
)

DECISION_AT = "2026-10-19T12:00:00Z"
BINDING_DECISION_AT = "2026-10-18T15:00:00Z"
CANDIDATE_DECISION_AT = "2026-10-15T14:32:00Z"
FROZEN_POLICY_SHA256 = (
    "3eb42ad948cf8cfad731b319d66ca341e33661810e269cc447b0df53cbb92203"
)

CONTRACT = {
    "root": "SPXW",
    "expiration": "2026-12-18",
    "right": "call",
    "strike": "6800",
    "strike_millis": 6800000,
    "occ_symbol": "SPXW  261218C06800000",
}

SOURCE_PREFIX_RECEIPT = {
    "receipt_id": "oacamp_receipt_synth0001",
    "prefix_rows": 3,
    "prefix_sha256": "b" * 64,
    "ledger_max_bytes": 4096,
    "prefix_raw_bytes": 1234,
}

FROZEN_FORMATION = {
    "campaign_revision_id": "campaign-revision-0001",
    "formed_at": "2026-10-15T14:30:00Z",
    "candidate_identity_schema": "options.alpha_candidate_identity/v1",
    "policy_id": "oa_candidate_formation_synth/v2",
    "policy_version": 2,
    "policy_digest_sha256": "c" * 64,
    "policy_freeze_at": "2026-10-01T00:00:00Z",
    "activation_boundary_at": None,
    "policy_freeze_cleared": True,
    "activation_boundary_cleared": True,
    "source_prefix_receipt": SOURCE_PREFIX_RECEIPT,
    "campaign_member_count": 3,
    "final_member_event_id": "evt_synth_0003",
    "measured_source_print_count": 11,
    "measured_nbbo_valid_print_count": 9,
    "measured_nbbo_premium_coverage": 0.87,
    "all_evidence_legs_within_decision_cutoff": True,
    "evidence_digest_sha256": "d" * 64,
}

INTENT_KEYS = {
    "schema", "expression_id", "candidate_id",
    "candidate_frozen_formation_sha256", "preparation_receipt_sha256",
    "selection_policy_id", "selection_policy_sha256", "oa3_ruler",
    "contract", "terms_observation", "decision_at",
    "publication_available_at", "eligibility", "authority",
}
TERMS_KEYS = {
    "schema", "contract", "multiplier", "standard_deliverable",
    "deliverable_description", "effective_from", "effective_until",
    "source_available_at", "source_observed_at", "source_id",
    "raw_source_sha256", "raw_source_bytes",
}


def _candidate():
    return {
        "candidate_id": "oacf_candidate_synth0001aabbcc",
        "campaign_id": "campaign_synth_0001",
        "first_qualifying_campaign_revision_id": "campaign-revision-0001",
        "current_campaign_revision_id": "campaign-revision-0001",
        "source_formed_at": "2026-10-15T14:30:00Z",
        "first_observed_at": "2026-10-15T14:31:00Z",
        "decision_at": CANDIDATE_DECISION_AT,
        "frozen_formation": copy.deepcopy(FROZEN_FORMATION),
        "state": "research_candidate",
        "reasons": [],
    }


def _binding():
    return {
        "selection_policy_id": formation.POLICY["policy_id"],
        "selection_policy_sha256": formation.POLICY_SHA256,
        "formation_policy": {
            "schema": "options.alpha_candidate_formation_policy/v2",
            "policy_id": "oa_candidate_formation_synth/v2",
            "policy_version": 2,
        },
        "oa3_ruler": {
            "policy_id": "oa_exact_option_outcome_synth/v1",
            "policy_version": "v1",
            "policy_sha256": "e" * 64,
        },
        "candidate_id": "oacf_candidate_synth0001aabbcc",
        "candidate_decision_at": CANDIDATE_DECISION_AT,
        "candidate_first_observed_at": "2026-10-15T14:31:00Z",
        "candidate_source_prefix": copy.deepcopy(SOURCE_PREFIX_RECEIPT),
        "formation_campaign_revision_id": "campaign-revision-0001",
        "formation_campaign_raw_sha256": "f" * 64,
        "feed_raw_sha256": "1" * 64,
        "feed_raw_bytes": 2048,
        "source_observed_at": "2026-10-18T14:55:00Z",
        "campaigns_observed_at": "2026-10-18T14:50:00Z",
        "selection_started_at": "2026-10-18T14:58:00Z",
        "decision_at": BINDING_DECISION_AT,
        "catalog_observed_at": None,
        "contract": copy.deepcopy(CONTRACT),
        "catalog_identity_evidence": None,
        "research_position": copy.deepcopy(formation.POLICY["research_position"]),
        "multiplier": None,
        "standard_deliverable": None,
    }


def _preparation_record(binding=None):
    binding = _binding() if binding is None else binding
    return {
        "schema": "options.alpha_expression_preparation/v1",
        "status": "unavailable",
        "reasons": [
            "EXPRESSION_POLICY_INACTIVE",
            "PROSPECTIVE_ACTIVATION_FENCE_UNESTABLISHED",
            "SOURCE_CONTRACT_TERMS_UNAVAILABLE",
        ],
        "binding": binding,
        "decision_receipt_sha256": sha_of_binding(binding),
        "expression": None,
        "expression_upstream_digest_sha256": None,
        "selection_frozen_before_outcomes": None,
        "available_at": None,
        "capture_request": None,
        "training_eligible": False,
    }


def sha_of_binding(binding):
    return hashlib.sha256(cohort.canonical_json_bytes(binding)).hexdigest()


def _terms():
    return {
        "schema": "options.contract_terms_observation/v1",
        "contract": copy.deepcopy(CONTRACT),
        "multiplier": 100,
        "standard_deliverable": True,
        "deliverable_description": "SPXW standard contract, USD 100 per index point",
        "effective_from": "2026-10-12T00:00:00Z",
        "effective_until": "2026-12-19T00:00:00Z",
        "source_available_at": "2026-10-18T14:00:00Z",
        "source_observed_at": "2026-10-18T14:59:00Z",
        "source_id": "occ_contract_adjustment_synth_feed",
        "raw_source_sha256": "9" * 64,
        "raw_source_bytes": 4096,
    }


_UNSET = object()


def _make(candidate=_UNSET, preparation=_UNSET, terms=_UNSET,
          decision_at=DECISION_AT):
    return make_expression_intent(
        candidate=_candidate() if candidate is _UNSET else candidate,
        preparation_record=(
            _preparation_record() if preparation is _UNSET else preparation),
        terms_observation=_terms() if terms is _UNSET else terms,
        decision_at=decision_at,
    )


def _with(mapping, key, value):
    changed = copy.deepcopy(mapping)
    changed[key] = value
    return changed


def _without(mapping, key):
    changed = copy.deepcopy(mapping)
    changed.pop(key)
    return changed


# ---------------------------------------------------------------------------
# Positive construction, validation and identity derivation.
# ---------------------------------------------------------------------------


def test_positive_construction_and_validation():
    assert issubclass(IntentError, ValueError)
    record = _preparation_record()
    intent = _make(preparation=record)
    assert set(intent) == INTENT_KEYS
    assert intent["schema"] == INTENT_SCHEMA == "options.alpha_expression_intent/v1"
    assert intent["terms_observation"]["schema"] == TERMS_SCHEMA
    assert intent["candidate_id"] == _candidate()["candidate_id"]
    assert intent["decision_at"] == DECISION_AT
    assert intent["preparation_receipt_sha256"] == record["decision_receipt_sha256"]
    assert intent["selection_policy_id"] == formation.POLICY["policy_id"]
    assert intent["selection_policy_sha256"] == FROZEN_POLICY_SHA256
    assert intent["candidate_frozen_formation_sha256"] == hashlib.sha256(
        canonical_bytes(FROZEN_FORMATION)).hexdigest()
    assert intent["oa3_ruler"] == _binding()["oa3_ruler"]
    assert intent["contract"] == cohort.validate_contract(CONTRACT)
    assert intent["publication_available_at"] is None
    assert intent["eligibility"] == ELIGIBILITY
    assert intent["authority"] == formation.POLICY["authority"]
    assert all(value is False for value in intent["authority"].values())
    validated = validate_expression_intent(intent)
    assert validated == intent
    assert validated is not intent
    assert validated["terms_observation"] is not intent["terms_observation"]


def test_expression_id_and_formation_digest_derivation():
    intent = _make()
    payload = {k: v for k, v in intent.items() if k != "expression_id"}
    assert intent["expression_id"].startswith(EXPRESSION_ID_PREFIX)
    assert intent["expression_id"] == (
        EXPRESSION_ID_PREFIX
        + hashlib.sha256(canonical_bytes(payload)).hexdigest())
    assert intent["candidate_frozen_formation_sha256"] == hashlib.sha256(
        canonical_bytes(_candidate()["frozen_formation"])).hexdigest()


def test_terms_remain_whole_in_the_intent():
    intent = _make()
    assert intent["terms_observation"] == _terms()
    assert set(intent["terms_observation"]) == TERMS_KEYS


def test_preparation_record_extra_keys_are_tolerated():
    record = _preparation_record()
    record["future_revision_field"] = {"note": "parent schema may evolve"}
    intent = _make(preparation=record)
    assert intent["preparation_receipt_sha256"] == record["decision_receipt_sha256"]


# ---------------------------------------------------------------------------
# Original preparation / native frozen binding mismatches.
# ---------------------------------------------------------------------------


def test_binding_selection_policy_mismatch_with_frozen_policy():
    binding = _with(_binding(), "selection_policy_sha256", "0" * 64)
    with pytest.raises(IntentError):
        _make(preparation=_preparation_record(binding=binding))
    binding = _with(_binding(), "selection_policy_id",
                    formation.POLICY["policy_id"] + "_v2")
    with pytest.raises(IntentError):
        _make(preparation=_preparation_record(binding=binding))


def test_binding_candidate_formation_mismatch():
    binding = _with(_binding(), "candidate_source_prefix",
                    _with(SOURCE_PREFIX_RECEIPT, "prefix_rows", 99))
    with pytest.raises(IntentError):
        _make(preparation=_preparation_record(binding=binding))
    binding = _with(_binding(), "formation_campaign_revision_id",
                    "campaign-revision-0002")
    with pytest.raises(IntentError):
        _make(preparation=_preparation_record(binding=binding))
    binding = _with(_binding(), "candidate_id", "oacf_candidate_other")
    with pytest.raises(IntentError):
        _make(preparation=_preparation_record(binding=binding))


def test_binding_candidate_contract_mismatch():
    candidate = _candidate()
    candidate["frozen_formation"] = copy.deepcopy(FROZEN_FORMATION)
    binding = _with(_binding(), "contract",
                    _with(CONTRACT, "strike_millis", 6900000))
    with pytest.raises(IntentError):
        make_expression_intent(
            candidate=candidate,
            preparation_record=_preparation_record(binding=binding),
            terms_observation=_terms(),
            decision_at=DECISION_AT,
        )


def test_altered_binding_without_reseal_is_refused():
    record = _preparation_record()
    record["binding"]["feed_raw_bytes"] = 4096
    with pytest.raises(IntentError):
        _make(preparation=record)
    record = _preparation_record()
    record["decision_receipt_sha256"] = hashlib.sha256(b"unrelated").hexdigest()
    with pytest.raises(IntentError):
        _make(preparation=record)
    record = _preparation_record()
    record["decision_receipt_sha256"] = (
        record["decision_receipt_sha256"].upper())
    with pytest.raises(IntentError):
        _make(preparation=record)


def test_binding_unknown_or_missing_fields_are_refused():
    binding = _with(_binding(), "outcome_selector", "best_pnl")
    with pytest.raises(IntentError):
        _make(preparation=_preparation_record(binding=binding))
    binding = _without(_binding(), "contract")
    with pytest.raises(IntentError):
        _make(preparation=_preparation_record(binding=binding))
    record = _preparation_record()
    record["binding"] = None
    with pytest.raises(IntentError):
        _make(preparation=record)
    record = _without(_preparation_record(), "binding")
    with pytest.raises(IntentError):
        _make(preparation=record)


def test_null_binding_contract_is_refused():
    binding = _with(_binding(), "contract", None)
    with pytest.raises(IntentError):
        _make(preparation=_preparation_record(binding=binding))


# ---------------------------------------------------------------------------
# Required normalized terms observation.
# ---------------------------------------------------------------------------


def test_terms_allow_null_effective_until():
    intent = _make(terms=_with(_terms(), "effective_until", None))
    assert intent["terms_observation"]["effective_until"] is None
    validate_expression_intent(intent)


@pytest.mark.parametrize("mutate", [
    lambda t: _with(t, "multiplier", None),
    lambda t: _with(t, "multiplier", True),
    lambda t: _with(t, "multiplier", 500),
    lambda t: _with(t, "multiplier", "100"),
    lambda t: _with(t, "multiplier", 100.0),
    lambda t: _with(t, "standard_deliverable", False),
    lambda t: _with(t, "standard_deliverable", 1),
    lambda t: _with(t, "contract", _with(CONTRACT, "strike", "6900")),
    lambda t: _with(t, "contract", None),
    lambda t: _with(t, "raw_source_bytes", 0),
    lambda t: _with(t, "raw_source_bytes", -1),
    lambda t: _with(t, "raw_source_bytes", True),
    lambda t: _with(t, "raw_source_sha256", "A" * 64),
    lambda t: _with(t, "raw_source_sha256", "9" * 63),
    lambda t: _with(t, "source_id", ""),
    lambda t: _with(t, "deliverable_description", ""),
    lambda t: _with(t, "schema", "options.contract_terms_observation/v2"),
    lambda t: _with(t, "source_observed_at", "2026-10-19T12:00:01Z"),
    lambda t: _with(t, "source_available_at", "2026-10-18T15:30:00Z"),
    lambda t: _with(t, "source_observed_at", "2026-10-18T14:59:00"),
    lambda t: _with(t, "effective_from", "2026-10-19T12:00:01Z"),
    lambda t: _with(t, "effective_until", "2026-10-19T11:59:59Z"),
    lambda t: _with(t, "effective_until", "2026-10-19T12:00:00Z"),
    lambda t: _with(t, "effective_from", "2026-10-12T00:00:00"),
    lambda t: _with(t, "runtime_admission_receipt", {"producer": "synthetic"}),
    lambda t: _without(t, "multiplier"),
    lambda t: _without(t, "deliverable_description"),
])
def test_terms_mutations_are_refused(mutate):
    with pytest.raises(IntentError):
        _make(terms=mutate(_terms()))


# ---------------------------------------------------------------------------
# New selection clock.
# ---------------------------------------------------------------------------


def test_new_selection_clock_is_distinct_and_sequenced():
    intent = _make()
    assert intent["decision_at"] == DECISION_AT
    assert intent["decision_at"] != CANDIDATE_DECISION_AT
    assert intent["decision_at"] != BINDING_DECISION_AT
    with pytest.raises(IntentError):
        _make(decision_at="2026-10-18T14:59:59Z")
    same = _make(decision_at=BINDING_DECISION_AT)
    assert same["decision_at"] == BINDING_DECISION_AT
    later = _make(decision_at="2026-10-19T12:00:01Z")
    assert later["expression_id"] != intent["expression_id"]
    with pytest.raises(IntentError):
        _make(decision_at="2026-10-19T12:00:00")
    with pytest.raises(IntentError):
        _make(decision_at="2026-10-19T12:00:00+00:00")


def test_decision_is_never_copied_from_the_candidate():
    a = _make(candidate=_with(_candidate(), "decision_at", CANDIDATE_DECISION_AT))
    b = _make(candidate=_with(_candidate(), "decision_at",
                              "2026-10-15T16:32:00Z"))
    assert a == b
    assert a["decision_at"] == DECISION_AT


# ---------------------------------------------------------------------------
# Authority and identity mutations.
# ---------------------------------------------------------------------------


def test_authority_mutations_are_refused():
    intent = validate_expression_intent(_make())
    authority = _with(intent["authority"], "may_trade", True)
    with pytest.raises(IntentError):
        validate_expression_intent(_with(intent, "authority", authority))
    authority = _without(intent["authority"], "may_capture_quotes")
    with pytest.raises(IntentError):
        validate_expression_intent(_with(intent, "authority", authority))
    authority = _with(intent["authority"], "may_publish_intent", False)
    with pytest.raises(IntentError):
        validate_expression_intent(_with(intent, "authority", authority))


def test_identity_mutations_are_refused():
    intent = _make()
    with pytest.raises(IntentError):
        validate_expression_intent(
            _with(intent, "expression_id", EXPRESSION_ID_PREFIX + "0" * 64))
    digest = intent["expression_id"][len(EXPRESSION_ID_PREFIX):]
    flipped = digest[:-1] + ("0" if digest[-1] != "0" else "1")
    with pytest.raises(IntentError):
        validate_expression_intent(
            _with(intent, "expression_id", EXPRESSION_ID_PREFIX + flipped))
    with pytest.raises(IntentError):
        validate_expression_intent(
            _with(intent, "expression_id", hashlib.sha256(
                canonical_bytes({k: v for k, v in intent.items()
                                 if k != "expression_id"})).hexdigest()))
    tampered = copy.deepcopy(intent)
    tampered["terms_observation"]["source_id"] = "other_source"
    with pytest.raises(IntentError):
        validate_expression_intent(tampered)
    with pytest.raises(IntentError):
        validate_expression_intent(
            _with(intent, "selection_policy_sha256", "0" * 64))
    with pytest.raises(IntentError):
        validate_expression_intent(
            _with(intent, "eligibility", "eligible_for_capture"))
    with pytest.raises(IntentError):
        validate_expression_intent(
            _with(intent, "publication_available_at", "2026-10-20T00:00:00Z"))
    with pytest.raises(IntentError):
        validate_expression_intent(
            _with(intent, "schema", "options.alpha_expression_intent/v2"))
    with pytest.raises(IntentError):
        validate_expression_intent(
            _with(intent, "decision_at", "2026-10-19T11:59:59Z"))


# ---------------------------------------------------------------------------
# Unknown fields and malformed shapes.
# ---------------------------------------------------------------------------


def test_unknown_intent_fields_are_refused():
    intent = _make()
    with pytest.raises(IntentError):
        validate_expression_intent(_with(intent, "capture_request", None))
    with pytest.raises(IntentError):
        validate_expression_intent(_with(intent, "available_at", None))
    with pytest.raises(IntentError):
        validate_expression_intent(_without(intent, "eligibility"))


def test_malformed_shapes_are_refused():
    with pytest.raises(IntentError):
        _make(candidate=None)
    with pytest.raises(IntentError):
        _make(candidate=_without(_candidate(), "frozen_formation"))
    with pytest.raises(IntentError):
        _make(candidate=_without(_candidate(), "candidate_id"))
    with pytest.raises(IntentError):
        _make(preparation=None)
    record = _without(_preparation_record(), "decision_receipt_sha256")
    with pytest.raises(IntentError):
        _make(preparation=record)
    with pytest.raises(IntentError):
        _make(terms=None)
    intent = _make()
    with pytest.raises(IntentError):
        validate_expression_intent(None)
    with pytest.raises(IntentError):
        validate_expression_intent([])
    with pytest.raises(IntentError):
        validate_expression_intent(
            _with(intent, "candidate_frozen_formation_sha256", "zz"))
    with pytest.raises(IntentError):
        validate_expression_intent(_with(intent, "contract", None))
    with pytest.raises(IntentError):
        validate_expression_intent(_with(intent, "terms_observation", None))
    with pytest.raises(IntentError):
        validate_expression_intent(
            _with(intent, "oa3_ruler",
                  _with(intent["oa3_ruler"], "policy_sha256", "short")))
    with pytest.raises(IntentError):
        validate_expression_intent(
            _with(intent, "oa3_ruler",
                  _with(intent["oa3_ruler"], "policy_version", True)))


# ---------------------------------------------------------------------------
# In-memory immutability and outcome blindness.
# ---------------------------------------------------------------------------


def test_caller_objects_are_never_mutated():
    candidate, record, terms = _candidate(), _preparation_record(), _terms()
    snapshot = (copy.deepcopy(candidate), copy.deepcopy(record),
                copy.deepcopy(terms))
    intent = make_expression_intent(
        candidate=candidate, preparation_record=record,
        terms_observation=terms, decision_at=DECISION_AT)
    assert (candidate, record, terms) == snapshot
    intent["terms_observation"]["multiplier"] = 500
    intent["authority"]["may_trade"] = True
    assert terms["multiplier"] == 100
    assert terms["contract"]["strike"] == "6800"
    assert formation.POLICY["authority"]["may_trade"] is False


def test_validated_intent_is_an_independent_deep_copy():
    intent = _make()
    validated = validate_expression_intent(intent)
    assert validated == intent
    validated["terms_observation"]["source_id"] = "mutated"
    validated["authority"]["may_trade"] = True
    assert validate_expression_intent(intent)["terms_observation"] == _terms()


def test_input_mutation_after_make_does_not_change_intent():
    terms = _terms()
    intent = _make(terms=terms)
    terms["multiplier"] = 500
    terms["contract"]["strike"] = "100"
    assert intent["terms_observation"]["multiplier"] == 100
    assert intent["contract"]["strike"] == "6800"
    validate_expression_intent(intent)


def test_candidate_outcomes_are_never_read():
    clean = _candidate()
    enriched = copy.deepcopy(clean)
    enriched["post_formation_outcomes"] = {
        "state": "captured",
        "pnl_usd": 12345.67,
        "reasons": ["WIN"],
    }
    from_enriched = _make(candidate=enriched)
    assert from_enriched == _make(candidate=clean)
    enriched["post_formation_outcomes"]["pnl_usd"] = -9876.54
    assert _make(candidate=enriched) == _make(candidate=clean)
    assert "post_formation_outcomes" not in canonical_bytes(from_enriched).decode()
    assert "pnl_usd" not in canonical_bytes(from_enriched).decode()


def test_intent_is_not_an_expression_receipt():
    intent = _make()
    text = canonical_bytes(intent).decode()
    assert "capture_request" not in text
    assert "ExpressionReceipt" not in text
    assert "capture" not in intent["eligibility"]
    assert intent["publication_available_at"] is None
    assert intent["eligibility"] == "research_intent_only_no_activation"
    assert intent["authority"] == formation.POLICY["authority"]
    assert all(value is False for value in intent["authority"].values())


@pytest.mark.parametrize('false_equivalent', [0, 0.0])
def test_authority_requires_literal_false_even_with_a_recomputed_identity(false_equivalent):
    intent = _make()
    intent['authority']['may_trade'] = false_equivalent
    intent['expression_id'] = EXPRESSION_ID_PREFIX + hashlib.sha256(
        canonical_bytes({k: v for k, v in intent.items() if k != 'expression_id'})
    ).hexdigest()
    with pytest.raises(IntentError, match='authority'):
        validate_expression_intent(intent)
