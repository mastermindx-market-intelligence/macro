"""tests/test_semiconductor_native_identity.py — T04: the shared curation
assertion binds to the K1 Evidence Foundation as ONE owner subtype with native
clocks, and identity namespaces stay separate.

The binding law under test:

* ``engine.theme_graph.curation_assertion.reference_for_assertion`` projects a
  stamped assertion row onto an ``evidence_foundation.reference.v1`` that
  ``lib.evidence_foundation.validate_reference`` accepts unchanged — no K1
  validator change, no new store, no physical mesh.
* Native clocks travel under their NATIVE dotted field names, one binding per
  clock, each present exactly once. An unknown publication is typed unknown —
  never borrowed from a clock that does exist, never synthesized into a
  midnight instant, and a date-only publication keeps grain ``date``.
* Identity namespaces stay separate: the reference's only subject is the
  theme-evidence identity. A venue:symbol never becomes a cik/security
  subject, a resolved ``company_node_id`` never mints one, and the owner body
  (limitations / observation / source_uri) never rides along inside the
  reference — the owner reader stays the only path to the statement.

Fixtures are synthetic: ``tests.semiconductor_research_helpers.load_case``
refuses any payload that is not explicitly flagged synthetic.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
from pathlib import Path

import pytest

from engine.theme_graph import curation_assertion as ca
from lib.evidence_foundation import (
    EvidenceFoundationError,
    combined_violations,
    compute_reference_id,
    load_vocabulary,
    render_owner_pointer,
    validate_reference,
)
from tests.semiconductor_research_helpers import load_case

ROOT = Path(__file__).resolve().parents[1]

OWNER_STORE = "theme_graph.curation_assertion"
POSITIVE_FIXTURES = ("source_only_business", "same_url_different_statements")

#: Subject key types whose namespaces belong to the Data OS / security master.
#: A curation assertion never emits one — company navigation is a separately
#: justified native bridge, not a K1 subject claim.
SECURITY_NAMESPACE_SUBJECT_TYPES = frozenset({
    "cik", "issuer_id", "security_id", "listing_key", "cusip", "mm_subject",
})

#: The exact clock binding the new owner registers, one per native clock under
#: its native field name (pinned again against the vocabulary below).
EXPECTED_CLOCK_BINDINGS = {
    "source.published_at": ("source_published", ("date", "datetime")),
    "source.observed_at": ("observed", ("datetime",)),
    "source.retained_at": ("system_recorded", ("datetime",)),
    "source.available_at": ("knowable", ("datetime",)),
    "review.reviewed_at": ("belief_or_build", ("datetime",)),
    "temporal.business_valid_from": ("world_valid", ("date",)),
    "temporal.business_valid_to": ("world_valid", ("date",)),
    "computed_at": ("belief_or_build", ("datetime",)),
}

STATEMENT_MODE_OBJECT_CLASS = {
    "REPORTED_FACT": "world_observation",
    "CATALOG_DESCRIPTION": "world_observation",
    "ANNOUNCED_ARRANGEMENT": "world_observation",
    "FORWARD_TARGET": "forward_claim",
    "ATTRIBUTED_INTERPRETATION": "derived_view",
}

AUTHORITY_CLASS_BY_OBJECT_CLASS = {
    "world_observation": "fact",
    "forward_claim": "human",
    "derived_view": "human",
}


def _clocks_by_field(reference: dict) -> dict:
    return {clock["field"]: clock for clock in reference["clocks"]}


def _restamped_row(row: dict, mutate) -> dict:
    """A copy of an evidence row whose assertion is mutated and re-stamped by
    the mint path — the only lawful way to derive a synthetic sibling
    assertion from a fixture row (an edit is always a new revision)."""
    assertion = ca.decode_assertion(row["curation_assertion"])
    mutate(assertion)
    assertion["curation_revision"] = None
    out = dict(row)
    out["curation_assertion"] = ca.encode_assertion(assertion)
    return out


def _published_row(row: dict, published_at: str, published_at_grain: str) -> dict:
    def mutate(assertion):
        assertion["source"]["published_at"] = published_at
        assertion["source"]["published_at_grain"] = published_at_grain
    return _restamped_row(row, mutate)


def _identity_case(case_name: str, label: str) -> dict:
    case = load_case(case_name)
    by_label = {entry["label"]: entry for entry in case["cases"]}
    return by_label[label]


def _attested_listing_history(valid_from: date, *, event_date: date) -> bool:
    """TEST-LOCAL stand-in for the T05/T08 consumer rule (deliberately NOT
    product code): a validity window that STARTS at the alias epoch is the
    unset default, never attested listing history — so it cannot make a 2026
    event look historically attested."""
    from engine.company_intelligence.identity import ALIAS_EPOCH

    if valid_from == ALIAS_EPOCH:
        return False
    return valid_from <= event_date


# ---------------------------------------------------------------------------
# Positive: the projection validates unchanged, and carries no security claim
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture_name", POSITIVE_FIXTURES)
def test_every_native_row_of_the_positive_fixtures_validates_as_a_k1_reference(
    fixture_name: str,
) -> None:
    for index, row in enumerate(load_case(fixture_name)["native_rows"]):
        ref = ca.reference_for_assertion(row)
        assert validate_reference(ref) == ref, (fixture_name, index)


def test_industrial_reference_does_not_claim_a_resolved_security():
    from engine.theme_graph.curation_assertion import reference_for_assertion
    from lib.evidence_foundation import validate_reference
    row = load_case('source_only_business')['native_rows'][0]
    ref = reference_for_assertion(row)
    checked = validate_reference(ref)
    assert checked == ref
    assert row['evidence_id'] in str(checked)
    assert 'SEC:' not in str(checked)


def test_reference_subject_is_exactly_the_theme_evidence_identity_and_no_secondary():
    for fixture_name in POSITIVE_FIXTURES:
        for row in load_case(fixture_name)["native_rows"]:
            checked = validate_reference(ca.reference_for_assertion(row))
            assert checked["subject"] == {
                "key_type": "theme_evidence_id",
                "key": row["evidence_id"],
            }
            assert checked["secondary_subjects"] == []


def test_reference_identity_pointer_digest_and_zero_authority_are_the_row_its():
    row = load_case("source_only_business")["native_rows"][0]
    assertion = ca.decode_assertion(row["curation_assertion"])
    checked = validate_reference(ca.reference_for_assertion(row))
    assert checked["native_identity"] == {
        "evidence_id": row["evidence_id"],
        "curation_revision": assertion["curation_revision"],
    }
    owner = load_vocabulary()["owner_stores"][OWNER_STORE]
    assert checked["provenance"]["pointer"] == render_owner_pointer(
        owner, checked["native_identity"])
    assert checked["provenance"]["pointer"].startswith(
        "data/theme_graph/evidence.parquet#")
    assert checked["native_schema"] == "theme_graph.curation_assertion.v1"
    assert checked["coverage_class"] == "append_only_bitemporal"
    assert checked["replay"]["mode"] == "live"
    assert checked["authority"] == {
        key: False
        for key in ("can_rank", "can_gate", "can_size", "can_originate",
                    "can_open_entry")
    }


def test_native_digest_is_the_sha256_of_the_canonical_assertion_bytes():
    row = load_case("source_only_business")["native_rows"][0]
    assertion = ca.decode_assertion(row["curation_assertion"])
    checked = validate_reference(ca.reference_for_assertion(row))
    digest = sha256(ca.encode_assertion(assertion).encode("utf-8")).hexdigest()
    assert checked["native_digest"] == {"state": "known", "sha256": digest}


# ---------------------------------------------------------------------------
# Positive: native clocks, one per binding, unknowns typed
# ---------------------------------------------------------------------------

def test_native_clocks_are_bound_under_their_native_field_names():
    owner = load_vocabulary()["owner_stores"][OWNER_STORE]
    assert owner["clock_bindings"] == {
        field: {"class": clock_class, "grains": list(grains)}
        for field, (clock_class, grains) in EXPECTED_CLOCK_BINDINGS.items()
    }
    assert owner["synapse_asof_field"] == "computed_at"


def test_every_bound_clock_appears_exactly_once_under_its_native_name():
    expected_fields = set(EXPECTED_CLOCK_BINDINGS)
    for fixture_name in POSITIVE_FIXTURES:
        for row in load_case(fixture_name)["native_rows"]:
            checked = validate_reference(ca.reference_for_assertion(row))
            fields = [clock["field"] for clock in checked["clocks"]]
            assert len(fields) == len(set(fields)), (fixture_name, row["evidence_id"])
            assert set(fields) == expected_fields
    # dotted native names survive K1 unchanged — no flattening happened
    checked = validate_reference(
        ca.reference_for_assertion(load_case("source_only_business")["native_rows"][0]))
    assert "source.published_at" in _clocks_by_field(checked)
    assert "temporal.business_valid_from" in _clocks_by_field(checked)


def test_explicit_unknown_publication_yields_a_typed_unknown_clock_and_no_borrowed_date():
    def mutate(assertion):
        assertion["source"]["published_at"] = None
        assertion["source"]["published_at_grain"] = "unknown"

    row = _restamped_row(load_case("source_only_business")["native_rows"][0], mutate)
    checked = validate_reference(ca.reference_for_assertion(row))
    clocks = _clocks_by_field(checked)
    assert clocks["source.published_at"]["value_state"] == "unknown"
    assert clocks["source.published_at"]["value"] is None
    # never borrowed from a clock that DOES exist
    assert clocks["source.published_at"]["value"] not in {
        clocks["source.observed_at"]["value"],
        clocks["source.retained_at"]["value"],
        clocks["review.reviewed_at"]["value"],
    }
    # and the unknown publication does NOT turn into a false object-absence:
    # the assertion is present, only its publication time is unknown
    assert checked["missingness"]["state"] == "present"


def test_a_date_only_publication_keeps_grain_date_and_never_becomes_a_midnight():
    case = load_case("date_only_same_day")
    assert case["expect"] == "ambiguous_refused"
    row = _published_row(
        load_case(case["base_case"])["native_rows"][0],
        case["published_at"], case["published_at_grain"])
    checked = validate_reference(ca.reference_for_assertion(row))
    assert _clocks_by_field(checked)["source.published_at"] == {
        "class": "source_published",
        "field": "source.published_at",
        "value_state": "known",
        "value": case["published_at"],
        "grain": "date",
    }
    assert "T00:00:00" not in json.dumps(checked)


# ---------------------------------------------------------------------------
# Positive: statement_mode → object_class, total and one-way
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("statement_mode", "object_class"),
    sorted(STATEMENT_MODE_OBJECT_CLASS.items()),
)
def test_statement_mode_maps_to_its_one_object_class(statement_mode, object_class):
    row = _restamped_row(
        load_case("source_only_business")["native_rows"][0],
        lambda assertion: assertion.__setitem__("statement_mode", statement_mode))
    checked = validate_reference(ca.reference_for_assertion(row))
    assert checked["object_class"] == object_class
    assert checked["authority_class"] == AUTHORITY_CLASS_BY_OBJECT_CLASS[object_class]


def test_forward_target_is_never_a_world_observation():
    row = _restamped_row(
        load_case("source_only_business")["native_rows"][0],
        lambda assertion: assertion.__setitem__("statement_mode", "FORWARD_TARGET"))
    checked = validate_reference(ca.reference_for_assertion(row))
    assert checked["object_class"] == "forward_claim"
    assert checked["object_class"] != "world_observation"


# ---------------------------------------------------------------------------
# Positive: the correction lineage stays owner-native, never fabricated
# ---------------------------------------------------------------------------

def test_a_correcting_assertion_still_validates_without_minting_a_predecessor():
    rows = load_case("same_url_different_statements")["native_rows"]
    row = rows[-1]
    assertion = ca.decode_assertion(row["curation_assertion"])
    assert assertion["correction"]["predecessor_revision"] is not None
    checked = validate_reference(ca.reference_for_assertion(row))
    blob = json.dumps(checked)
    # K1 correction lineage cites predecessor REFERENCE ids; a single row
    # cannot mint one, so none is fabricated here and none is embedded
    assert checked["correction"]["kind"] == "none"
    assert checked["correction"]["predecessor_reference_ids"] == []
    assert checked["relations"] == []
    assert assertion["correction"]["predecessor_revision"] not in blob


# ---------------------------------------------------------------------------
# Negative: every refusal K1 owes this owner
# ---------------------------------------------------------------------------

def test_dropping_a_recorded_or_retained_clock_that_the_assertion_has_is_refused():
    row = load_case("source_only_business")["native_rows"][0]
    assertion = ca.decode_assertion(row["curation_assertion"])
    assert assertion["source"]["retained_at"] and assertion["source"]["observed_at"]
    checked = validate_reference(ca.reference_for_assertion(row))
    for field in ("source.retained_at", "source.observed_at"):
        hostile = deepcopy(checked)
        hostile["clocks"] = [
            clock for clock in hostile["clocks"] if clock["field"] != field]
        hostile["reference_id"] = compute_reference_id(hostile)
        assert f"clock_field_missing:{field}" in combined_violations(hostile)
        with pytest.raises(EvidenceFoundationError):
            validate_reference(hostile)


def test_the_builder_never_overwrites_publication_with_a_later_clock():
    for fixture_name in POSITIVE_FIXTURES:
        for row in load_case(fixture_name)["native_rows"]:
            assertion = ca.decode_assertion(row["curation_assertion"])
            checked = validate_reference(ca.reference_for_assertion(row))
            clocks = _clocks_by_field(checked)
            published = assertion["source"]["published_at"]
            if published is None:
                assert clocks["source.published_at"]["value_state"] == "unknown"
                continue
            assert clocks["source.published_at"]["value_state"] == "known"
            assert clocks["source.published_at"]["value"] == published
            assert clocks["source.published_at"]["grain"] == (
                "date" if assertion["source"]["published_at_grain"] == "date"
                else "datetime")
            for other in ("source.observed_at", "source.retained_at",
                          "review.reviewed_at"):
                assert clocks["source.published_at"]["value"] != clocks[other]["value"]


def test_same_day_date_publication_and_instant_replay_cutoff_is_ambiguous_refused():
    case = load_case("date_only_same_day")
    row = _published_row(
        load_case(case["base_case"])["native_rows"][0],
        case["published_at"], case["published_at_grain"])
    checked = validate_reference(ca.reference_for_assertion(row))
    hostile = deepcopy(checked)
    hostile["replay"].update(
        mode="historical_replay", code_revision="fixture-code",
        input_digest="5" * 64, vintage_state="owner_native")
    hostile["replay"]["cutoffs"]["source_published"] = {
        "state": "known", "value": case["system_replay_cutoff"], "grain": "datetime"}
    hostile["reference_id"] = compute_reference_id(hostile)
    assert "replay_grain_ambiguous:source.published_at" in combined_violations(hostile)
    with pytest.raises(EvidenceFoundationError):
        validate_reference(hostile)


def test_same_day_instant_publication_and_date_replay_cutoff_is_ambiguous_too():
    source_case = load_case("source_only_business")
    row = _published_row(source_case["native_rows"][0], "2026-07-16T09:00:00Z", "instant")
    checked = validate_reference(ca.reference_for_assertion(row))
    hostile = deepcopy(checked)
    hostile["replay"].update(
        mode="historical_replay", code_revision="fixture-code",
        input_digest="5" * 64, vintage_state="owner_native")
    hostile["replay"]["cutoffs"]["source_published"] = {
        "state": "known", "value": "2026-07-16", "grain": "date"}
    hostile["reference_id"] = compute_reference_id(hostile)
    assert "replay_grain_ambiguous:source.published_at" in combined_violations(hostile)
    with pytest.raises(EvidenceFoundationError):
        validate_reference(hostile)


def test_a_knowable_clock_learned_after_computed_at_is_typed_and_refused_under_replay():
    computed_at = "2026-04-02T12:00:00Z"

    def mutate(assertion):
        assertion["source"]["available_at"] = "2026-05-01T00:00:00Z"

    row = _restamped_row(load_case("source_only_business")["native_rows"][0], mutate)
    checked = validate_reference(ca.reference_for_assertion(row))
    clock = _clocks_by_field(checked)["source.available_at"]
    assert clock["class"] == "knowable" and clock["value_state"] == "known"
    assert clock["value"] > computed_at
    # live mode cannot know this is lookahead; system replay refuses it
    hostile = deepcopy(checked)
    hostile["replay"].update(
        mode="historical_replay", code_revision="fixture-code",
        input_digest="5" * 64, vintage_state="owner_native")
    hostile["replay"]["cutoffs"]["knowable"] = {
        "state": "known", "value": computed_at, "grain": "datetime"}
    hostile["reference_id"] = compute_reference_id(hostile)
    assert "replay_lookahead:source.available_at" in combined_violations(hostile)
    with pytest.raises(EvidenceFoundationError):
        validate_reference(hostile)


# ---------------------------------------------------------------------------
# Identity namespaces stay separate
# ---------------------------------------------------------------------------

def test_the_new_owner_keeps_the_shared_evidence_id_namespace_and_no_security_subject():
    vocabulary = load_vocabulary()
    owner = vocabulary["owner_stores"][OWNER_STORE]
    evidence_owner = vocabulary["owner_stores"]["theme_graph.evidence"]
    assert owner["native_identity_grammars"]["evidence_id"] == \
        evidence_owner["native_identity_grammars"]["evidence_id"]
    assert owner["subject_key_types"] == ["theme_evidence_id"]
    assert not {"cik", "security_id", "issuer_id", "listing_key"} & set(
        owner["subject_key_types"])
    assert owner["subject_native_parity"] == {
        "theme_evidence_id": {"kind": "native_field_equal", "field": "evidence_id"}}
    assert owner["reader"] == "engine.theme_graph.curation_assertion.decode_assertion"
    assert owner["reader_kind"] == "parser"
    assert owner["pointer_template"] == (
        "data/theme_graph/evidence.parquet"
        "#evidence_id={evidence_id}&curation_revision={curation_revision}")


def test_a_venue_symbol_is_never_a_k1_subject_of_the_curation_owner():
    case = _identity_case("identity_namespace_or_epoch", "venue_symbol_is_not_sec_identity")
    assert case["expect"] == "refused"
    checked = validate_reference(
        ca.reference_for_assertion(load_case("source_only_business")["native_rows"][0]))
    hostile = deepcopy(checked)
    hostile["subject"] = {
        "key_type": case["subject"]["type"],
        "key": case["subject"]["value"],
    }
    hostile["reference_id"] = compute_reference_id(hostile)
    assert "subject_0_not_owned" in combined_violations(hostile)
    with pytest.raises(EvidenceFoundationError):
        validate_reference(hostile)


def test_the_k1_cik_grammar_also_refuses_a_venue_symbol():
    fixture = ROOT / "tests" / "fixtures" / "evidence_foundation" / (
        "earnings_workspace_valid.json")
    hostile = json.loads(fixture.read_text(encoding="utf-8"))
    assert hostile["subject"]["key_type"] == "cik"
    case = _identity_case("identity_namespace_or_epoch", "venue_symbol_is_not_sec_identity")
    hostile["subject"]["key"] = case["subject"]["value"]
    hostile["reference_id"] = compute_reference_id(hostile)
    assert "subject_0_key_invalid:cik" in combined_violations(hostile)
    with pytest.raises(EvidenceFoundationError, match="subject_0_key_invalid:cik"):
        validate_reference(hostile)


def test_a_resolved_company_node_never_becomes_a_company_or_security_subject():
    def mutate(assertion):
        assertion["subject"]["company_node_id"] = "co:us:SYNTH"

    row = _restamped_row(load_case("source_only_business")["native_rows"][0], mutate)
    checked = validate_reference(ca.reference_for_assertion(row))
    assert checked["subject"] == {
        "key_type": "theme_evidence_id", "key": row["evidence_id"]}
    assert checked["secondary_subjects"] == []
    subjects = [checked["subject"], *checked["secondary_subjects"]]
    assert not {s["key_type"] for s in subjects} & SECURITY_NAMESPACE_SUBJECT_TYPES


def test_no_reference_from_an_assertion_ever_carries_a_security_namespace_subject():
    for fixture_name in POSITIVE_FIXTURES:
        for row in load_case(fixture_name)["native_rows"]:
            checked = validate_reference(ca.reference_for_assertion(row))
            subjects = [checked["subject"], *checked["secondary_subjects"]]
            assert not {s["key_type"] for s in subjects} & SECURITY_NAMESPACE_SUBJECT_TYPES


def test_the_alias_epoch_default_window_is_not_attested_history():
    case = _identity_case("identity_namespace_or_epoch", "alias_epoch_default_is_not_history")
    assert case["expect"] == "not_historical_evidence"
    valid_from = date.fromisoformat(case["alias_valid_from"])
    event_date = date.fromisoformat(case["event_date"])
    assert valid_from == date(1970, 1, 1)
    from engine.company_intelligence.identity import ALIAS_EPOCH

    assert ALIAS_EPOCH == date(1970, 1, 1)
    assert _attested_listing_history(valid_from, event_date=event_date) is False
    # a genuinely dated window still reads as attested history
    assert _attested_listing_history(date(2026, 1, 2), event_date=event_date) is True


# ---------------------------------------------------------------------------
# The owner body never rides along; a null cell is refused
# ---------------------------------------------------------------------------

def test_the_reference_is_pointer_only_and_never_embeds_the_owner_body():
    row = load_case("source_only_business")["native_rows"][0]
    assertion = ca.decode_assertion(row["curation_assertion"])
    checked = validate_reference(ca.reference_for_assertion(row))
    blob = json.dumps(checked)
    for key in ("limitations", "observation", "source_uri"):
        assert key not in checked
    assert assertion["limitations"]["coverage"] not in blob
    assert "example.invalid" not in blob
    # and K1 detects an embedded body exactly the way the contract test does
    hostile = deepcopy(checked)
    hostile["body"] = {"limitations": assertion["limitations"]}
    hostile["reference_id"] = compute_reference_id(hostile)
    assert any(code.startswith("json_schema:$:additionalProperties")
               for code in combined_violations(hostile))
    with pytest.raises(EvidenceFoundationError):
        validate_reference(hostile)


@pytest.mark.parametrize("null_cell", [None, ""])
def test_a_row_without_a_stamped_assertion_is_refused(null_cell):
    row = dict(load_case("source_only_business")["native_rows"][0])
    row["curation_assertion"] = null_cell
    with pytest.raises(ca.CurationAssertionError):
        ca.reference_for_assertion(row)


def test_a_denied_right_yields_rights_blocked_and_a_typed_absence_never_a_grant():
    """A row whose licensing attestation denies ANY right projects as a
    rights-blocked reference with a typed absence; K1 still accepts it."""
    row = deepcopy(load_case('source_only_business')['native_rows'][0])
    assert all(row.get(flag) is True for flag in ca._LICENSING_FLAGS)
    row['licensing_redistribution_ok'] = False
    checked = validate_reference(ca.reference_for_assertion(row))
    assert checked['rights']['state'] == 'rights_blocked'
    assert checked['missingness'] == {'state': 'absent', 'reason': 'rights_blocked', 'zero_substituted': False}


def test_missing_licensing_flags_yield_unknown_rights_never_permitted():
    """Flags neither attested nor denied are UNKNOWN: the projection never
    defaults to a grant, and the object is present (nothing is fabricated absent)."""
    row = deepcopy(load_case('source_only_business')['native_rows'][0])
    for flag in ca._LICENSING_FLAGS:
        row.pop(flag, None)
    checked = validate_reference(ca.reference_for_assertion(row))
    assert checked['rights'] == {'state': 'unknown', 'policy_id': None}
    assert checked['missingness']['state'] == 'present'
    # a single attested right with the others unstated is still not a grant
    row['licensing_internal_ok'] = True
    assert validate_reference(ca.reference_for_assertion(row))['rights']['state'] == 'unknown'
