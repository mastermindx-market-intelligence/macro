"""Per-decision causal input envelope tests with hand-stated fixtures.

Every expectation here is written into the fixture table by hand: finite
measurement values, null values, cutoff instants and the exact violation
fragments.  The production layer is never used as its own oracle.  The
fixtures prove that cutoffs are genuinely per decision: future suffix rows,
future corrections and post-cutoff captured captures are refused, missing
observations stay explicit nulls, and no value is ever invented from nothing.
"""
from __future__ import annotations

import pytest

from engine.research_codegen import input_contract
from engine.research_codegen.contracts import canonical_json_sha256

CANDIDATE = "rf-codegen-alpha01"
FOLD = "fold-dev-2010-2017"
ENTITY = "XLK"
DECISION = "decision-2030-03-04"
CUTOFF = "2030-03-04T14:00:00Z"
POLICY = "d" * 64
SOURCES = ["yahoo_collectors", "incumbent_store"]


def trusted_request():
    return {
        "schema": "research_codegen.request.v1",
        "candidate_id": CANDIDATE,
        "fold_id": FOLD,
        "entity_id": ENTITY,
        "decision_id": DECISION,
        "cutoff": CUTOFF,
        "input_policy_sha256": POLICY,
        "allowed_source_ids": list(SOURCES),
    }


def observation(**overrides):
    row = {
        "source_id": "yahoo_collectors",
        "revision_id": "rev-2030-03-03",
        "event_time": "2030-03-03T21:00:00Z",
        "available_at": "2030-03-04T13:30:00Z",
        "received_at": "2030-03-04T13:31:00Z",
        "evidence_class": "captured",
        # Hand-stated finite fixture value; 0.00125 is the expected measurement.
        "value": 0.00125,
    }
    row.update(overrides)
    return row


def valid_envelope(rows=None):
    if rows is None:
        rows = [observation()]
    return {
        "schema": "research_codegen.input.v1",
        "candidate_id": CANDIDATE,
        "fold_id": FOLD,
        "entity_id": ENTITY,
        "decision_id": DECISION,
        "cutoff": CUTOFF,
        "input_policy_sha256": POLICY,
        "observations": rows,
    }


def joined(violations):
    return " | ".join(violations)


def ordered_rows():
    """Two rows already in the documented deterministic order."""
    early = observation(revision_id="rev-2030-03-02",
                        event_time="2030-03-02T21:00:00Z",
                        available_at="2030-03-03T13:30:00Z",
                        received_at="2030-03-03T13:31:00Z",
                        value=-0.5)
    late = observation(value=3)
    return [early, late]


def test_valid_envelope_and_known_request_digest():
    assert input_contract.validate_input_envelope(
        valid_envelope(), trusted_request=trusted_request()) == []
    assert input_contract.validate_input_envelope(
        valid_envelope(ordered_rows()), trusted_request=trusted_request()) == []
    assert canonical_json_sha256(trusted_request()) \
        == "3e046d2994a343cb7f38c3be17181b5991e249984d5295d2f626bd17f5ebb5d9"


def test_hand_stated_finite_values_and_explicit_nulls_survive():
    # Revisions listed in ascending order so the deterministic-order rule and
    # the value rules are exercised together: 0.00125, 3, -0.5 finite; None
    # stays an explicit null.
    rows = [observation(revision_id="rev-2030-03-03", value=0.00125),
            observation(revision_id="rev-int", value=3),
            observation(revision_id="rev-neg", value=-0.5),
            observation(revision_id="rev-null", value=None)]
    assert input_contract.validate_input_envelope(
        valid_envelope(rows=rows), trusted_request=trusted_request()) == []


def test_empty_observations_are_explicit_zero_coverage():
    assert input_contract.validate_input_envelope(
        valid_envelope(rows=[]), trusted_request=trusted_request()) == []


def test_identity_and_policy_mismatch_refuses():
    for field, bad in (("candidate_id", "rf-codegen-other01"),
                       ("fold_id", "fold-other-1"),
                       ("entity_id", "XLF"),
                       ("decision_id", "decision-2030-03-05"),
                       ("input_policy_sha256", "0" * 64)):
        envelope = valid_envelope()
        envelope[field] = bad
        text = joined(input_contract.validate_input_envelope(
            envelope, trusted_request=trusted_request()))
        assert text.find(field) >= 0, field


def test_cutoff_compares_as_clock_and_refuses_other_instants():
    # Same instant, different written representation: accepted.
    shifted = valid_envelope()
    shifted["cutoff"] = "2030-03-04T09:00:00-05:00"
    assert input_contract.validate_input_envelope(
        shifted, trusted_request=trusted_request()) == []
    later = valid_envelope()
    later["cutoff"] = "2030-03-04T14:00:01Z"
    text = joined(input_contract.validate_input_envelope(
        later, trusted_request=trusted_request()))
    assert text.find("cutoff") >= 0


def test_future_suffix_rows_cannot_be_inserted():
    future = observation(revision_id="rev-future",
                         event_time="2030-03-04T15:00:00Z",
                         available_at="2030-03-05T13:30:00Z",
                         received_at="2030-03-05T13:31:00Z")
    text = joined(input_contract.validate_input_envelope(
        valid_envelope(rows=[future]), trusted_request=trusted_request()))
    assert text.find("after the decision cutoff") >= 0


def test_next_session_event_time_refuses():
    late_event = observation(revision_id="rev-t1",
                             event_time="2030-03-04T14:30:00Z",
                             available_at="2030-03-04T13:30:00Z")
    text = joined(input_contract.validate_input_envelope(
        valid_envelope(rows=[late_event]), trusted_request=trusted_request()))
    assert text.find("event_time is after available_at") >= 0


def test_future_correction_revision_refuses():
    correction = observation(revision_id="rev-correction",
                             event_time="2030-03-03T21:00:00Z",
                             available_at="2030-03-04T15:00:00Z",
                             received_at="2030-03-04T15:05:00Z")
    text = joined(input_contract.validate_input_envelope(
        valid_envelope(rows=[correction]), trusted_request=trusted_request()))
    assert text.find("after the decision cutoff") >= 0


def test_unknown_available_at_is_refused_not_invented():
    for bad in (None, "", "unknown", "2030-03-04", "2030-03-04T13:30:00",
                "2030-13-45T99:00:00Z", 7, True):
        row = observation(available_at=bad)
        text = joined(input_contract.validate_input_envelope(
            valid_envelope(rows=[row]), trusted_request=trusted_request()))
        assert text.find("available_at") >= 0, bad


def test_captured_received_after_cutoff_refuses():
    row = observation(received_at="2030-03-04T14:30:00Z")
    text = joined(input_contract.validate_input_envelope(
        valid_envelope(rows=[row]), trusted_request=trusted_request()))
    assert text.find("captured evidence received after the cutoff") >= 0
    missing = observation(received_at=None)
    text = joined(input_contract.validate_input_envelope(
        valid_envelope(rows=[missing]), trusted_request=trusted_request()))
    assert text.find("captured evidence requires received_at") >= 0


def test_reconstructed_limits_are_explicit():
    null_received = observation(received_at=None, evidence_class="reconstructed")
    assert input_contract.validate_input_envelope(
        valid_envelope(rows=[null_received]), trusted_request=trusted_request()) == []
    late_received = observation(received_at="2030-03-06T09:00:00Z",
                                evidence_class="reconstructed")
    assert input_contract.validate_input_envelope(
        valid_envelope(rows=[late_received]), trusted_request=trusted_request()) == []
    mislabeled = observation(received_at=None, evidence_class="captured")
    text = joined(input_contract.validate_input_envelope(
        valid_envelope(rows=[mislabeled]), trusted_request=trusted_request()))
    assert text.find("reconstructed") >= 0 or text.find("captured") >= 0
    bad_class = observation(evidence_class="derived")
    assert input_contract.validate_input_envelope(
        valid_envelope(rows=[bad_class]), trusted_request=trusted_request()) != []


def test_received_at_cannot_precede_available_at():
    row = observation(received_at="2030-03-04T13:00:00Z")
    text = joined(input_contract.validate_input_envelope(
        valid_envelope(rows=[row]), trusted_request=trusted_request()))
    assert text.find("received_at precedes available_at") >= 0


def test_duplicate_observation_identity_refuses():
    twin = observation(available_at="2030-03-04T13:30:00Z")  # identical identity
    text = joined(input_contract.validate_input_envelope(
        valid_envelope(rows=[observation(), twin]),
        trusted_request=trusted_request()))
    assert text.find("duplicate") >= 0
    # Same instant written differently is still the same observation identity.
    same_instant = observation(available_at="2030-03-04T08:30:00-05:00")
    text = joined(input_contract.validate_input_envelope(
        valid_envelope(rows=[observation(), same_instant]),
        trusted_request=trusted_request()))
    assert text.find("duplicate") >= 0


def test_disallowed_and_malformed_sources_refuse():
    row = observation(source_id="candidate_private_feed")
    text = joined(input_contract.validate_input_envelope(
        valid_envelope(rows=[row]), trusted_request=trusted_request()))
    assert text.find("not allowed") >= 0
    for bad in ("", 7, None, True, "bad id"):
        row = observation(source_id=bad)
        assert input_contract.validate_input_envelope(
            valid_envelope(rows=[row]), trusted_request=trusted_request()) != [], bad
    dup_request = trusted_request()
    dup_request["allowed_source_ids"] = ["yahoo_collectors", "yahoo_collectors"]
    text = joined(input_contract.validate_input_envelope(
        valid_envelope(), trusted_request=dup_request))
    assert text.find("duplicate allowed_source_ids") >= 0
    typed_request = trusted_request()
    typed_request["allowed_source_ids"] = ["ok", {"bad": "object"}]
    text = joined(input_contract.validate_input_envelope(
        valid_envelope(), trusted_request=typed_request))
    assert text.find("allowed_source_ids") >= 0


def test_deterministic_order_is_enforced():
    rows = list(reversed(ordered_rows()))
    text = joined(input_contract.validate_input_envelope(
        valid_envelope(rows=rows), trusted_request=trusted_request()))
    assert text.find("deterministic order") >= 0
    same_available = [
        observation(revision_id="rev-b", value=1),
        observation(revision_id="rev-a", value=2),
    ]
    text = joined(input_contract.validate_input_envelope(
        valid_envelope(rows=same_available), trusted_request=trusted_request()))
    assert text.find("deterministic order") >= 0


def test_bool_nonfinite_and_object_values_refuse():
    assert input_contract.validate_input_envelope(
        valid_envelope(rows=[observation(value=True)]),
        trusted_request=trusted_request()) != []
    for bad in (float("nan"), float("inf"), -float("inf"), "0.5"):
        assert input_contract.validate_input_envelope(
            valid_envelope(rows=[observation(value=bad)]),
            trusted_request=trusted_request()) != [], bad

    class FakeFloat(float):
        pass

    assert input_contract.validate_input_envelope(
        valid_envelope(rows=[observation(value=FakeFloat("1.5"))]),
        trusted_request=trusted_request()) != []
    assert input_contract.validate_input_envelope(
        valid_envelope(rows=[observation(value=object())]),
        trusted_request=trusted_request()) != []
    envelope = valid_envelope()
    envelope["observations"] = tuple(valid_envelope()["observations"])
    assert input_contract.validate_input_envelope(
        envelope, trusted_request=trusted_request()) != []


def test_oversized_and_mistyped_observation_containers_refuse():
    # 1025 full rows exceed MAX_CONTAINER_ITEMS, so the bounded exact JSON
    # precheck refuses the whole envelope before any row inspection.
    oversized = [observation(revision_id="rev-%04d" % index)
                 for index in range(1025)]
    violations = input_contract.validate_input_envelope(
        valid_envelope(rows=oversized), trusted_request=trusted_request())
    assert joined(violations).find("bounded finite exact JSON required") >= 0
    # A non-list observations container is refused as a bounded list violation.
    envelope = valid_envelope()
    envelope["observations"] = {"rows": [observation()]}
    text = joined(input_contract.validate_input_envelope(
        envelope, trusted_request=trusted_request()))
    assert text.find("bounded list required") >= 0


def test_envelope_extra_fields_and_schema_are_closed():
    envelope = valid_envelope()
    envelope["label"] = {"held_out": True}
    assert input_contract.validate_input_envelope(
        envelope, trusted_request=trusted_request()) != []
    envelope = valid_envelope()
    envelope["future_schedule"] = "2030-03-05T14:00:00Z"
    assert input_contract.validate_input_envelope(
        envelope, trusted_request=trusted_request()) != []
    envelope = valid_envelope()
    envelope["schema"] = "research_codegen.input.v2"
    assert input_contract.validate_input_envelope(
        envelope, trusted_request=trusted_request()) != []
    row = observation(extra_field=1)
    assert input_contract.validate_input_envelope(
        valid_envelope(rows=[row]), trusted_request=trusted_request()) != []


def test_timestamp_clock_math_is_independently_stated():
    # Hand-computed instant arithmetic: 13:30Z equals 08:30-05:00.
    a = input_contract.parse_timestamp("2030-03-04T13:30:00Z")
    b = input_contract.parse_timestamp("2030-03-04T08:30:00-05:00")
    assert a == b
    assert (input_contract.parse_timestamp("2030-03-04T14:00:01Z") - a).total_seconds() == 1801.0
    for bad in ("2030-03-04T13:30:00", "not-a-time", "", "2030-03-04",
                "2030-03-04T13:30:00+99:00"):
        with pytest.raises(ValueError):
            input_contract.parse_timestamp(bad)


def test_trusted_request_malformed_parts_refuse():
    for field, bad in (("cutoff", "2030-03-04T14:00:00"),
                       ("input_policy_sha256", "xyz"),
                       ("candidate_id", "candidate-1"),
                       ("fold_id", "")):
        request = trusted_request()
        request[field] = bad
        text = joined(input_contract.validate_input_envelope(
            valid_envelope(), trusted_request=request))
        assert text.find("trusted_request") >= 0, field
    assert input_contract.validate_input_envelope(
        valid_envelope(), trusted_request=object()) != []
    request = trusted_request()
    request["schema"] = "research_codegen.request.v2"
    assert input_contract.validate_input_envelope(
        valid_envelope(), trusted_request=request) != []


def test_missing_observation_stays_null_in_fixture_semantics():
    # The fixture states the expectation by hand: a row whose value is null is
    # structural missing data.  The validator accepts it unchanged and the
    # fixture table keeps the exact value None for downstream consumers.  A
    # null fixture and an explicit zero fixture are canonically different
    # structures, and the production layer offers no call that could turn the
    # null into zero.
    row = observation(revision_id="rev-gap", value=None)
    envelope = valid_envelope(rows=[row])
    assert input_contract.validate_input_envelope(
        envelope, trusted_request=trusted_request()) == []
    assert envelope["observations"][0]["value"] is None
    null_fixture = dict(row, value=None)
    zero_fixture = dict(row, value=0)
    assert canonical_json_sha256(null_fixture) \
        != canonical_json_sha256(zero_fixture)
    assert not hasattr(input_contract, "coerce_missing_to_zero")


@pytest.mark.parametrize("clock", ["0001-01-01T00:00:00+01:00",
                                   "9999-12-31T23:59:59-01:00"])
def test_utc_conversion_overflow_is_a_structural_refusal(clock):
    with pytest.raises(ValueError):
        input_contract.parse_timestamp(clock)
    request = trusted_request()
    request["cutoff"] = clock
    errors = input_contract.validate_input_envelope(valid_envelope(), trusted_request=request)
    assert type(errors) is list and errors
    envelope = valid_envelope()
    envelope["cutoff"] = clock
    errors = input_contract.validate_input_envelope(envelope, trusted_request=trusted_request())
    assert type(errors) is list and errors
    for field in ("event_time", "available_at", "received_at"):
        envelope = valid_envelope([observation(**{field: clock})])
        errors = input_contract.validate_input_envelope(envelope, trusted_request=trusted_request())
        assert type(errors) is list and errors
