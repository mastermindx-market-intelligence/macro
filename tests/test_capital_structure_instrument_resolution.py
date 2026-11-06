"""I0 explicit-evidence instrument resolution (gates A04, A08, A09).

Candidates come from the real T0 boundary (the sealed registration fee-table
fixture, a second filing derived in memory -- fixtures are never edited).  The
second filing repeats the first exhibit term-for-term: same title, same values,
same classification.  Nothing but an explicit adjudicated decision may join,
supersede or retire anything.
"""

from __future__ import annotations

import copy
import dataclasses
import inspect
import json
from functools import lru_cache

import pytest

from engine.capital_structure.instrument_resolution import (
    CANDIDATE_REASONS,
    REFUSAL_REASONS,
    SERIES_REASONS,
    ResolutionRefusal,
    build_decision,
    decision_id_for,
    instrument_id_for,
    resolve_instrument_trace,
    resolve_instruments,
)
from engine.capital_structure.issuer_state_contracts import (
    CandidateBundle,
    EvidenceRef,
    InstrumentSet,
    ResolutionInputs,
    validate_state_record,
)
from engine.capital_structure.reference_qualification import NON_CANONICAL_FACT_ORIGINS, load_reference_pack
from engine.capital_structure.term_integration import INSTRUMENT_IDENTITY_KEYS, TermIntegrationRefusal
from tests.test_capital_structure_term_integration import (
    FIRST_ACCESSION,
    SECOND_ACCESSION,
    _authority,
    _integrate,
    _second_filing,
)

ISSUER = "sec:cik:0000000001"
AS_OF = "2026-08-08T00:00:00Z"
DECIDED = "2026-08-06T00:00:00Z"
LATER = "2026-08-07T00:00:00Z"
FUTURE = "2026-08-09T00:00:00Z"
SERIES = "common-stock"


@lru_cache(maxsize=None)
def _bundles():
    rows, manifests, reader = _authority()
    single = _integrate(rows, manifests, reader).candidate_bundle()
    all_rows, all_manifests, all_reader = _second_filing(rows, manifests)
    double = _integrate(all_rows, all_manifests, all_reader, as_of=AS_OF, generated_at=AS_OF).candidate_bundle()
    return single, double


def _bundle() -> CandidateBundle:
    return _bundles()[1]


def _filing(bundle: CandidateBundle, accession: str) -> dict[str, dict]:
    return {
        row["term"]["name"]: row
        for row in bundle.candidate_terms
        if row["filing"]["accession"] == accession
    }


def _ids(rows: dict[str, dict]) -> list[str]:
    return sorted(row["logical_candidate_term_id"] for row in rows.values())


def _evidence(rows: dict[str, dict]) -> list[EvidenceRef]:
    span = next(iter(rows.values()))["evidence"]["spans"][0]
    return [EvidenceRef(span["manifest_id"], span["span_id"], span["text_sha256"])]


def _found(candidates, *, series=SERIES, kind="common", security_class_id="class:common", decided_at=DECIDED,
           effective_at=None, fact_origin="adjudicated_gold", issuer_id=ISSUER, evidence=None):
    rows = _filing(_bundle(), FIRST_ACCESSION)
    return build_decision(
        method="supported_identity", issuer_id=issuer_id, series_key=series, security_class_id=security_class_id,
        kind=kind, candidate_term_ids=candidates, evidence=evidence or _evidence(rows), decided_at=decided_at,
        effective_at=effective_at, fact_origin=fact_origin,
    )


def _amend(candidates, supersedes, *, series=SERIES, kind="common", decided_at=LATER, effective_at=None,
           fact_origin="adjudicated_gold"):
    rows = _filing(_bundle(), SECOND_ACCESSION)
    return build_decision(
        method="amendment_join", issuer_id=ISSUER, series_key=series, security_class_id="class:common", kind=kind,
        candidate_term_ids=candidates, supersedes=supersedes, evidence=_evidence(rows), decided_at=decided_at,
        effective_at=effective_at, fact_origin=fact_origin,
    )


def _retire(*, decided_at=LATER, effective_at=None, series=SERIES):
    rows = _filing(_bundle(), SECOND_ACCESSION)
    return build_decision(
        method="retirement", issuer_id=ISSUER, series_key=series, security_class_id="class:common", kind="common",
        evidence=_evidence(rows), decided_at=decided_at, effective_at=effective_at,
    )


def _decisions(*records, as_of=FUTURE) -> ResolutionInputs:
    return ResolutionInputs(tuple(records), "capital-structure-owner", as_of)


def _trace(*records, bundle=None, as_of=AS_OF, decisions_as_of=FUTURE, **kwargs):
    return resolve_instrument_trace(bundle or _bundle(), _decisions(*records, as_of=decisions_as_of), as_of, **kwargs)


def _supersede_all():
    first, second = _filing(_bundle(), FIRST_ACCESSION), _filing(_bundle(), SECOND_ACCESSION)
    return [
        {"superseded": first[name]["logical_candidate_term_id"], "by": second[name]["logical_candidate_term_id"]}
        for name in sorted(first)
    ]


def _partition(trace) -> None:
    visible = {row["logical_candidate_term_id"] for row in _bundle().candidate_terms}
    bound = [cid for item in trace.instrument_set.instruments for cid in item.candidate_term_ids]
    superseded = [item.logical_candidate_term_id for item in trace.superseded]
    unresolved = list(trace.instrument_set.unresolved_candidate_ids)
    assert len(bound) + len(superseded) + len(unresolved) == len(visible)
    assert set(bound) | set(superseded) | set(unresolved) == visible
    validate_state_record("instrument_set", trace.instrument_set.as_record())


# --------------------------------------------------------------------------- interface


def test_resolve_instruments_keeps_the_c0_three_argument_interface():
    assert list(inspect.signature(resolve_instruments).parameters) == ["candidate_bundle", "decisions", "as_of"]
    result = resolve_instruments(_bundle(), _decisions(), AS_OF)
    assert isinstance(result, InstrumentSet)
    validate_state_record("instrument_set", result.as_record())


def test_reason_vocabularies_are_closed_and_disjoint():
    assert len(set(SERIES_REASONS)) == len(SERIES_REASONS)
    assert not set(REFUSAL_REASONS) & set(SERIES_REASONS)
    assert set(CANDIDATE_REASONS) & set(SERIES_REASONS) == {"candidate_not_observed"}


# --------------------------------------------------------------------------- A08


def test_repeated_exhibit_is_genuinely_similar_and_never_joined_without_a_decision():
    first, second = _filing(_bundle(), FIRST_ACCESSION), _filing(_bundle(), SECOND_ACCESSION)
    assert sorted(first) == sorted(second) and len(first) == 5
    for name in first:
        assert first[name]["security"]["title_normalized"] == second[name]["security"]["title_normalized"]
        assert first[name]["normalized"] == second[name]["normalized"]
        assert first[name]["logical_candidate_term_id"] != second[name]["logical_candidate_term_id"]
    trace = _trace()
    assert trace.instrument_set.instruments == ()
    assert len(trace.unresolved) == 10
    assert {item.reasons for item in trace.unresolved} == {("no_identity_decision",)}
    assert trace.instrument_set.provenance.support == "partial"
    _partition(trace)


def test_founding_on_one_filing_leaves_the_identical_repeat_unresolved():
    first, second = _filing(_bundle(), FIRST_ACCESSION), _filing(_bundle(), SECOND_ACCESSION)
    trace = _trace(_found(_ids(first)))
    (instrument,) = trace.instrument_set.instruments
    assert instrument.status == "outstanding"
    assert sorted(instrument.candidate_term_ids) == _ids(first)
    assert instrument.outstanding is None
    assert sorted(trace.instrument_set.unresolved_candidate_ids) == _ids(second)
    assert {item.reasons for item in trace.unresolved} == {("no_identity_decision",)}
    _partition(trace)


def test_binding_both_copies_of_a_repeated_exhibit_as_current_is_ambiguous():
    first, second = _filing(_bundle(), FIRST_ACCESSION), _filing(_bundle(), SECOND_ACCESSION)
    trace = _trace(_found(_ids(first) + _ids(second)))
    assert trace.instrument_set.instruments == ()
    (series,) = trace.series
    assert not series.resolved and series.reasons == ("duplicate_current_term",)
    assert all(item.reasons == ("duplicate_current_term", "series_unresolved") for item in trace.unresolved)
    assert len(trace.unresolved) == 10
    _partition(trace)


def test_amendment_join_supersedes_the_repeat_only_by_explicit_pairs():
    first, second = _filing(_bundle(), FIRST_ACCESSION), _filing(_bundle(), SECOND_ACCESSION)
    founding = _found(_ids(first))
    amendment = _amend(_ids(second), _supersede_all())
    trace = _trace(founding, amendment)
    (instrument,) = trace.instrument_set.instruments
    assert instrument.instrument_id == instrument_id_for(ISSUER, SERIES)
    assert instrument.status == "amended"
    assert sorted(instrument.candidate_term_ids) == _ids(second)
    assert instrument.amendments == (amendment["decision_id"],)
    assert instrument.resolution.method == "amendment_join"
    assert instrument.resolution.decision_id == amendment["decision_id"]
    assert sorted(item.logical_candidate_term_id for item in trace.superseded) == _ids(first)
    assert all(item.instrument_id == instrument.instrument_id for item in trace.superseded)
    assert trace.instrument_set.unresolved_candidate_ids == ()
    assert trace.instrument_set.provenance.support == "supported"
    _partition(trace)


def test_amendment_without_supersession_leaves_both_copies_current_and_refuses():
    first, second = _filing(_bundle(), FIRST_ACCESSION), _filing(_bundle(), SECOND_ACCESSION)
    trace = _trace(_found(_ids(first)), _amend(_ids(second), []))
    assert trace.instrument_set.instruments == ()
    assert trace.series[0].reasons == ("duplicate_current_term",)
    _partition(trace)


def test_superseding_a_term_the_series_never_bound_is_refused():
    first, second = _filing(_bundle(), FIRST_ACCESSION), _filing(_bundle(), SECOND_ACCESSION)
    held_back = first["registration_fee"]["logical_candidate_term_id"]
    founding = _found([cid for cid in _ids(first) if cid != held_back])
    amendment = _amend([second["registration_fee"]["logical_candidate_term_id"]],
                       [{"superseded": held_back, "by": second["registration_fee"]["logical_candidate_term_id"]}])
    trace = _trace(founding, amendment)
    assert trace.instrument_set.instruments == ()
    assert trace.series[0].reasons == ("superseded_term_not_bound",)
    _partition(trace)


def test_a_candidate_claimed_by_two_series_poisons_both():
    first = _filing(_bundle(), FIRST_ACCESSION)
    contested = first["amount_to_be_registered"]["logical_candidate_term_id"]
    trace = _trace(_found(_ids(first)), _found([contested], series="units", kind="unit"))
    assert trace.instrument_set.instruments == ()
    assert {item.series_key: item.reasons for item in trace.series} == {
        SERIES: ("candidate_claimed_by_multiple_series",),
        "units": ("candidate_claimed_by_multiple_series",),
    }
    _partition(trace)


def test_conflicting_foundings_never_pick_a_winner():
    first, second = _filing(_bundle(), FIRST_ACCESSION), _filing(_bundle(), SECOND_ACCESSION)
    trace = _trace(_found(_ids(first)), _found(_ids(second), decided_at=LATER))
    assert trace.instrument_set.instruments == ()
    assert trace.series[0].reasons == ("conflicting_identity_decisions",)
    _partition(trace)


def test_series_identity_must_be_consistent():
    first, second = _filing(_bundle(), FIRST_ACCESSION), _filing(_bundle(), SECOND_ACCESSION)
    trace = _trace(_found(_ids(first)), _amend(_ids(second), _supersede_all(), kind="warrant"))
    assert trace.instrument_set.instruments == ()
    assert trace.series[0].reasons == ("inconsistent_series_identity",)


def test_amendment_without_founding_is_unresolved():
    second = _filing(_bundle(), SECOND_ACCESSION)
    trace = _trace(_amend(_ids(second), []))
    assert trace.instrument_set.instruments == ()
    assert trace.series[0].reasons == ("missing_founding_decision",)


def test_unknown_or_not_yet_available_candidates_cannot_be_bound():
    first = _filing(_bundle(), FIRST_ACCESSION)
    ghost = "instrument-candidate-term-slot:cs:" + "0" * 32
    trace = _trace(_found(_ids(first) + [ghost]))
    assert trace.instrument_set.instruments == ()
    assert trace.series[0].reasons == ("candidate_not_visible",)
    early = _trace(_found(_ids(first)), as_of="2026-08-07T00:00:00Z")
    assert early.instrument_set.instruments == () and early.instrument_set.unresolved_candidate_ids == ()
    assert early.series[0].reasons == ("candidate_not_visible",)


# --------------------------------------------------------------------------- retirement and point in time


def test_retirement_is_explicit_and_keeps_identity():
    first = _filing(_bundle(), FIRST_ACCESSION)
    founding, retirement = _found(_ids(first)), _retire()
    (instrument,) = _trace(founding, retirement).instrument_set.instruments
    assert instrument.status == "retired"
    assert instrument.instrument_id == instrument_id_for(ISSUER, SERIES)
    assert instrument.resolution.method == "retirement"
    assert instrument.resolution.decision_id == retirement["decision_id"]
    assert sorted(instrument.candidate_term_ids) == _ids(first)


def test_retirement_is_never_retroactive_and_unknown_decisions_are_invisible():
    first = _filing(_bundle(), FIRST_ACCESSION)
    founding = _found(_ids(first))
    pending = _retire(effective_at=FUTURE)
    trace = _trace(founding, pending)
    assert trace.instrument_set.instruments[0].status == "outstanding"
    assert trace.pending_decision_ids == (pending["decision_id"],)
    unknown = _retire(decided_at=FUTURE)
    trace = _trace(founding, unknown)
    assert trace.instrument_set.instruments[0].status == "outstanding"
    assert trace.pending_decision_ids == ()
    assert trace.instrument_set.instruments == _trace(founding).instrument_set.instruments


def test_a_pending_amendment_leaves_its_new_terms_unresolved():
    first, second = _filing(_bundle(), FIRST_ACCESSION), _filing(_bundle(), SECOND_ACCESSION)
    amendment = _amend(_ids(second), _supersede_all(), effective_at=FUTURE)
    trace = _trace(_found(_ids(first)), amendment)
    assert trace.instrument_set.instruments[0].status == "outstanding"
    assert {item.reasons for item in trace.unresolved} == {("identity_decision_not_yet_effective",)}
    assert sorted(trace.instrument_set.unresolved_candidate_ids) == _ids(second)


def test_conflicting_retirements_and_amendment_after_retirement_are_unresolved():
    first, second = _filing(_bundle(), FIRST_ACCESSION), _filing(_bundle(), SECOND_ACCESSION)
    founding = _found(_ids(first))
    twice = _trace(founding, _retire(), _retire(decided_at="2026-08-07T12:00:00Z"))
    assert twice.series[0].reasons == ("conflicting_retirement_decisions",)
    late = _amend(_ids(second), _supersede_all(), decided_at="2026-08-07T12:00:00Z")
    after = _trace(founding, _retire(), late)
    assert after.instrument_set.instruments == ()
    assert after.series[0].reasons == ("amendment_after_retirement",)


def test_an_amendment_or_retirement_effective_before_its_founding_is_unresolved():
    first, second = _filing(_bundle(), FIRST_ACCESSION), _filing(_bundle(), SECOND_ACCESSION)
    founding = _found(_ids(first), effective_at="2026-08-06T12:00:00Z")
    early_amendment = _amend(_ids(second), _supersede_all(), effective_at="2026-08-06T06:00:00Z")
    early_retirement = _retire(effective_at="2026-08-06T06:00:00Z")
    for late_or_early in (early_amendment, early_retirement):
        trace = _trace(founding, late_or_early)
        assert trace.instrument_set.instruments == ()
        assert trace.series[0].reasons == ("decision_precedes_founding",)
        assert set(trace.instrument_set.unresolved_candidate_ids) >= set(_ids(first))


def test_resolution_beyond_the_known_inputs_is_refused():
    with pytest.raises(ResolutionRefusal, match="candidate bundle"):
        _trace(as_of=FUTURE)
    with pytest.raises(ResolutionRefusal, match="decision inputs"):
        _trace(decisions_as_of=LATER)


# --------------------------------------------------------------------------- A09


@pytest.mark.parametrize("origin", sorted(NON_CANONICAL_FACT_ORIGINS))
def test_llm_and_other_non_canonical_origins_cannot_mint_identity(origin):
    first = _filing(_bundle(), FIRST_ACCESSION)
    trace = _trace(_found(_ids(first), fact_origin=origin))
    assert trace.instrument_set.instruments == ()
    (refusal,) = trace.refusals
    assert refusal.reason == "fact_origin_not_canonical" and refusal.fact_origin == origin
    reasons = {item.logical_candidate_term_id: item.reasons for item in trace.unresolved}
    second = _filing(_bundle(), SECOND_ACCESSION)
    assert {reasons[cid] for cid in _ids(first)} == {("identity_decision_refused",)}
    assert {reasons[cid] for cid in _ids(second)} == {("no_identity_decision",)}
    _partition(trace)


@pytest.mark.parametrize(("origin", "reason"), [
    ("canonical_extraction", "identity_requires_adjudication"),
    ("vibes", "fact_origin_unknown"),
])
def test_only_adjudication_mints_identity(origin, reason):
    first = _filing(_bundle(), FIRST_ACCESSION)
    trace = _trace(_found(_ids(first), fact_origin=origin))
    assert trace.instrument_set.instruments == ()
    assert [item.reason for item in trace.refusals] == [reason]


def test_a_refused_amendment_supersedes_nothing():
    first, second = _filing(_bundle(), FIRST_ACCESSION), _filing(_bundle(), SECOND_ACCESSION)
    trace = _trace(_found(_ids(first)), _amend(_ids(second), _supersede_all(), fact_origin="llm_interpretation"))
    (instrument,) = trace.instrument_set.instruments
    assert instrument.status == "outstanding" and sorted(instrument.candidate_term_ids) == _ids(first)
    assert trace.superseded == ()
    assert {item.reasons for item in trace.unresolved} == {("identity_decision_refused",)}
    assert sorted(trace.instrument_set.unresolved_candidate_ids) == _ids(second)


def test_a_reference_pack_that_lets_an_llm_mint_is_refused():
    pack = load_reference_pack()
    poisoned = dataclasses.replace(pack, fact_origins={**pack.fact_origins, "llm_proposed_span": True})
    with pytest.raises(ResolutionRefusal, match="non-canonical"):
        _trace(reference_pack=poisoned)


# --------------------------------------------------------------------------- A04


def test_identity_is_owner_assigned_stable_and_clock_free():
    single, double = _bundles()
    first = _filing(double, FIRST_ACCESSION)
    founding = _found(_ids(first), decided_at="2026-08-03T00:00:00Z")
    assert resolve_instrument_trace(single, _decisions(_found(_ids(first))), "2026-08-04T00:00:00Z").instrument_set.instruments == ()
    early = resolve_instrument_trace(single, _decisions(founding), "2026-08-04T00:00:00Z").instrument_set
    late = resolve_instrument_trace(double, _decisions(founding), AS_OF).instrument_set
    assert early.instruments[0].instrument_id == late.instruments[0].instrument_id == instrument_id_for(ISSUER, SERIES)
    assert early.instruments[0].candidate_term_ids == late.instruments[0].candidate_term_ids
    amended = _trace(founding, _amend(_ids(_filing(double, SECOND_ACCESSION)), _supersede_all()))
    retired = _trace(founding, _retire())
    ids = {item.instruments[0].instrument_id for item in (early, late, amended.instrument_set, retired.instrument_set)}
    assert len(ids) == 1
    assert instrument_id_for(ISSUER, SERIES) != instrument_id_for(ISSUER, "units")


def test_resolution_is_deterministic_and_order_free():
    first, second = _filing(_bundle(), FIRST_ACCESSION), _filing(_bundle(), SECOND_ACCESSION)
    records = (_found(_ids(first)), _amend(_ids(second), _supersede_all()), _found(_ids(first)))
    a = _trace(*records)
    b = _trace(*reversed(records))
    shuffled = CandidateBundle(_bundle().binding, tuple(reversed(_bundle().candidate_terms)), _bundle().as_of)
    c = _trace(*records, bundle=shuffled)
    assert a.as_record() == b.as_record() == c.as_record()
    text = json.dumps(a.as_record(), sort_keys=True)
    assert "legacy:" not in text


def test_instrument_set_carries_no_quantity_score_or_unresolved_instrument():
    first = _filing(_bundle(), FIRST_ACCESSION)
    trace = _trace(_found(_ids(first)))
    record = trace.instrument_set.as_record()
    assert all(item["outstanding"] is None for item in record["instruments"])
    assert all(item["status"] != "unresolved_candidate" for item in record["instruments"])
    unresolved = set(record["unresolved_candidate_ids"])
    assert not unresolved & {cid for item in record["instruments"] for cid in item["candidate_term_ids"]}
    validate_state_record("instrument_set", record)
    assert trace.instrument_set.provenance.support == "partial"
    assert any("remain unresolved" in limit for limit in trace.instrument_set.provenance.support_limits)


# --------------------------------------------------------------------------- malformed inputs


def test_decision_records_are_content_addressed_and_closed():
    first = _filing(_bundle(), FIRST_ACCESSION)
    good = _found(_ids(first))
    assert good["decision_id"] == decision_id_for(good)
    tampered = {**good, "series_key": "something-else"}
    with pytest.raises(ResolutionRefusal, match="content address"):
        _trace(tampered)
    extra = {**good, "confidence": 0.9}
    extra["decision_id"] = decision_id_for(extra)
    with pytest.raises(ResolutionRefusal, match="keys must be exactly"):
        _trace(extra)


@pytest.mark.parametrize("kwargs", [
    {"method": "retirement", "candidate_term_ids": ["x:1"]},
    {"method": "supported_identity", "candidate_term_ids": []},
    {"method": "supported_identity", "candidate_term_ids": ["x:1"], "supersedes": [{"superseded": "x:0", "by": "x:1"}]},
    {"method": "amendment_join", "candidate_term_ids": ["x:1"], "supersedes": [{"superseded": "x:0", "by": "x:2"}]},
    {"method": "supported_identity", "candidate_term_ids": ["x:1", "x:1"]},
    {"method": "fuzzy_match", "candidate_term_ids": ["x:1"]},
    {"method": "supported_identity", "candidate_term_ids": ["x:1"], "evidence": []},
    {"method": "supported_identity", "candidate_term_ids": ["x:1"], "decided_at": "2026-08-06T00:00:00"},
])
def test_malformed_decisions_are_refused(kwargs):
    first = _filing(_bundle(), FIRST_ACCESSION)
    base = dict(issuer_id=ISSUER, series_key=SERIES, security_class_id="class:common", kind="common",
                evidence=_evidence(first), decided_at=DECIDED)
    base.update(kwargs)
    with pytest.raises(ResolutionRefusal):
        build_decision(**base)


def test_one_issuer_per_resolution():
    first = _filing(_bundle(), FIRST_ACCESSION)
    with pytest.raises(ResolutionRefusal, match="one issuer"):
        _trace(_found(_ids(first), issuer_id="sec:cik:0000000002"))


def test_the_closed_candidate_boundary_is_re_proved():
    bundle = _bundle()
    rows = [copy.deepcopy(row) for row in bundle.candidate_terms]
    key = sorted(INSTRUMENT_IDENTITY_KEYS)[0]
    rows[0][key] = "instrument:cs:" + "1" * 32
    with pytest.raises(TermIntegrationRefusal):
        _trace(bundle=CandidateBundle(bundle.binding, tuple(rows), bundle.as_of))
    forged = [copy.deepcopy(row) for row in bundle.candidate_terms]
    forged[0]["candidate"]["state"]["disposition"] = "excluded"
    with pytest.raises(TermIntegrationRefusal):
        _trace(bundle=CandidateBundle(bundle.binding, tuple(forged), bundle.as_of))
