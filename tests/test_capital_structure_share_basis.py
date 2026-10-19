"""Direct tests for capital-structure V2 task B1 (``select_share_basis``).

Gates exercised: A16 (no basis substitution; unit/date mismatch never picks the
largest or newest), A17 (inputs never select the denominator), A18 (four
separately evidenced split stages), A19 (a split scales only pre-split,
security-matched items), A48 (no probability/score/sizing), and review class 3
("old or unconfirmed share basis").
"""

from __future__ import annotations

import hashlib
import inspect
import json
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest

from engine.capital_structure.issuer_state_contracts import (
    COMPATIBLE_INPUT_SCHEMAS,
    FORBIDDEN_PROPERTY_PATTERN,
    STATE_CONTRACT_VERSION,
    sha256_of,
    CorporateActionInputs,
    GenerationBinding,
    ShareBasisResult,
    ShareInputs,
    validate_state_record,
)
from engine.capital_structure import share_basis as sb
from engine.capital_structure.share_basis import (
    MAX_BASIS_AGE_DAYS,
    SUPPORT_LIMITS,
    ShareBasisInputError,
    evaluate_split_actions,
    select_share_basis,
)

ROOT = Path(__file__).resolve().parents[1]
SHARE_SCHEMA = "capital_structure.share_count_observation.v2"
EVENT_SCHEMA = "capital_structure.event.v1"
CA_SCHEMA = "capital_structure.corporate_action_observation.v1"
ISSUER = "issuer:0000000001"
SECURITY = "issuer:0000000001:security:common_stock"
AS_OF = "2026-04-15T00:00:00Z"
GEN = "gen:share-counts-2026-10-14"


def _hex(label: str, size: int) -> str:
    return hashlib.sha256(label.encode()).hexdigest()[:size]


def _obs(
    label: str,
    period_end: str | None,
    value: str | None,
    *,
    kind: str = "common_shares_outstanding",
    name: str = "EntityCommonStockSharesOutstanding",
    namespace: str = "dei",
    unit: str = "shares",
    disposition: str = "observed",
    reason: str = "direct_sec_companyfacts_fact",
    filed: str = "2026-03-10",
    available_at: str = "2026-03-10T21:00:00Z",
    issuer: str = ISSUER,
    supersedes: tuple[str, ...] = (),
    correction_of: str | None = None,
    authority: dict | None = None,
) -> dict:
    """A v2 share-count record shaped exactly as the materializer writes it."""

    observed = disposition == "observed"
    classification = "common_stock" if kind == "common_shares_outstanding" else "not_security_specific"
    record = {
        "schema": SHARE_SCHEMA,
        "observation_id": obs_id(label),
        "logical_observation_id": f"share-count-slot-v2:cs:{_hex('slot' + label, 24)}",
        "fact_revision_id": f"share-count-revision-v2:cs:{_hex('rev' + label, 24)}",
        "issuer_id": issuer,
        "metric": {"kind": kind, "scope": "direct_sec_companyfacts_fact"},
        "fact": {"namespace": namespace, "name": name, "unit": unit, "scale": "1", "source_value_encoding": "companyfacts_actual_units"},
        "security_class": {
            "state": "concept_semantic" if classification == "common_stock" else "not_security_specific",
            "classification": classification,
            "raw_label": None,
            "basis": "xbrl_concept_semantics" if classification == "common_stock" else "companyfacts_fact_has_no_security_class",
        },
        "period": {"period_end": period_end, "fiscal_year": 2026, "fiscal_period": "Q1", "frame": None},
        "filing": {"accession": "0000000001-26-000005", "form": "10-Q", "filed": filed, "accepted_at": None},
        "state": {"disposition": disposition, "reason": reason},
        "reported": {"value": value, "unit": unit, "scale": "1"},
        "normalized": {
            "value": value if observed else None,
            "unit": ("shares" if kind == "common_shares_outstanding" else "USD") if observed else None,
            "scale": "1" if observed else None,
            "state": disposition,
        },
        "evidence": {
            "bridge_receipt_id": f"companyfacts-bridge:cs:{_hex('bridge' + label, 24)}",
            "source_manifest_id": f"manifest:cs-companyfacts:{_hex('manifest' + label, 64)}",
            "fact_entries": [
                {
                    "json_pointer": f"/facts/{namespace}/{name}/units/{unit}/0",
                    "entry_sha256": _hex("entry" + label, 64),
                    "source_issue": None,
                    "value": value,
                    "unit": unit,
                    "period_end": period_end,
                    "fiscal_year": 2026,
                    "fiscal_period": "Q1",
                    "frame": None,
                    "filed": filed,
                    "accession": "0000000001-26-000005",
                    "form": "10-Q",
                    "raw_entry": {"val": value},
                }
            ],
        },
        "point_in_time": {
            "source_retrieved_at": available_at,
            "materialized_at": available_at,
            "available_at": available_at,
            "public_available_at": None,
        },
        "relationships": {"supersedes": list(supersedes), "contradiction_ids": []},
        "version": {"immutable_record": True, "correction_version": 2 if correction_of else 1, "correction_of": correction_of},
        "authority": authority
        or {
            "is_context_only": True,
            "share_count_ledger_authority": False,
            "instrument_authority": False,
            "capacity_authority": False,
            "runway_authority": False,
            "risk_authority": False,
            "rank_authority": False,
            "sizing_authority": False,
            "entry_authority": False,
            "trade_authority": False,
            "prophet_authority": False,
        },
    }
    return record


def obs_id(label: str) -> str:
    return f"share-count-v2:cs:{_hex(label, 24)}"


def _shares(*records: dict) -> ShareInputs:
    binding = GenerationBinding("share_count_observations", SHARE_SCHEMA, "partial", generation_id=GEN, as_of="2026-04-14T00:00:00Z")
    return ShareInputs(binding, tuple(records))


def _no_actions() -> CorporateActionInputs:
    return CorporateActionInputs(GenerationBinding("events", None, "unavailable"), ())


def _event(label: str, subtype: str, filing_date: str, *, available_at: str | None = None) -> dict:
    return {
        "schema": EVENT_SCHEMA,
        "event_id": f"event:{label}",
        "issuer": {"issuer_id": ISSUER},
        "filing": {"accession": "0000000001-26-000011", "form": "8-K", "filing_date": filing_date, "accepted_at": None},
        "event": {"family": "corporate_action", "subtype": subtype, "affected_instrument_candidate_ids": []},
        "point_in_time": {
            "first_seen_at": available_at or f"{filing_date}T22:00:00Z",
            "public_available_at": None,
            "system_available_at": available_at or f"{filing_date}T22:00:00Z",
            "available_at": available_at or f"{filing_date}T22:00:00Z",
        },
        "authority": {"is_context_only": True, "rank_authority": False, "sizing_authority": False, "entry_authority": False, "prophet_authority": False},
    }


def _events(*records: dict) -> CorporateActionInputs:
    return CorporateActionInputs(GenerationBinding("events", EVENT_SCHEMA, "partial", generation_id="gen:events-2026-10-14"), tuple(records))


def _stage(stage: str, **over) -> dict:
    """The corporate-action record shape proposed to the seat for the C0 delta."""

    record = {
        "schema": CA_SCHEMA,
        "observation_id": f"ca:0000000001:rs-2026-03:{stage}",
        "action_id": "ca:0000000001:rs-2026-03",
        "issuer_id": ISSUER,
        "action_kind": "reverse_split",
        "stage": stage,
        "security_class_id": SECURITY,
        "ratio": {"new_shares": "1", "old_shares": "10"},
        "effective_date": "2026-03-02",
        "state": {"disposition": "observed", "reason": None},
        "filing": {"accession": "0000000001-26-000010", "form": "8-K", "filing_date": "2026-02-27"},
        "evidence": [{"manifest_id": "manifest:0000000001-26-000010", "span_id": f"span:{stage}", "text_sha256": "a" * 64}],
        "point_in_time": {"available_at": "2026-02-27T21:05:00Z"},
        "authority": {"selects_denominator": False, "is_context_only": True},
    }
    record.update(over)
    return record


def _four(**over) -> list[dict]:
    return [_stage(stage, **over) for stage in sb.SPLIT_STAGES]


def _as_of() -> datetime:
    return datetime(2026, 4, 15, tzinfo=timezone.utc)


def _round_trip(result: ShareBasisResult) -> dict:
    record = result.as_record()
    validate_state_record("share_basis_result", record)
    return record


# ---------------------------------------------------------------------------
# Fixture honesty: the share-count fixtures validate against the real v2 schema
# ---------------------------------------------------------------------------


def test_share_count_fixture_validates_against_the_v2_contract() -> None:
    schema = json.loads((ROOT / "contracts/capital_structure_share_count_observation_v2.schema.json").read_text())
    validator = jsonschema.Draft202012Validator(schema)
    for record in (
        _obs("a", "2026-02-27", "100000000"),
        _obs("b", "2025-12-31", None, disposition="ambiguous", reason="multiple_distinct_values_for_fact_slot"),
        _obs("f", "2025-06-30", "250000000", kind="public_float", name="EntityPublicFloat", unit="USD"),
    ):
        validator.validate(record)


# ---------------------------------------------------------------------------
# Selection and interface
# ---------------------------------------------------------------------------


def test_interface_is_the_declared_three_parameter_signature() -> None:
    assert list(inspect.signature(select_share_basis).parameters) == ["observations", "actions", "as_of"]


def test_selects_the_latest_clean_issued_and_outstanding_count() -> None:
    result = select_share_basis(
        _shares(
            _obs("old", "2025-11-01", "90000000", filed="2025-11-10", available_at="2025-11-10T21:00:00Z"),
            _obs("new", "2026-02-27", "100000000"),
        ),
        _no_actions(),
        AS_OF,
    )
    assert result.status == "selected"
    assert result.selected is not None and result.selected.value == "100000000"
    assert result.selected.share_basis == "issued_and_outstanding"
    assert result.security_class_id == SECURITY
    assert result.provenance.support == "partial" and result.provenance.support_limits == SUPPORT_LIMITS
    assert "corporate_actions_unobserved" in result.conflicts
    assert result.corporate_action.kind == "none"
    record = _round_trip(result)
    assert record["schema"] == "capital_structure.share_basis_result.v2"


def test_dei_cover_and_us_gaap_balance_counts_keep_their_own_dates() -> None:
    # A28: each fact keeps its own instant; the later clean instant wins and the
    # earlier fact is not averaged in, summed or headlined.
    result = select_share_basis(
        _shares(
            _obs("gaap", "2025-12-31", "98000000", name="CommonStockSharesOutstanding", namespace="us-gaap"),
            _obs("dei", "2026-02-27", "100000000"),
        ),
        _no_actions(),
        AS_OF,
    )
    assert result.status == "selected" and result.selected is not None
    assert result.selected.value == "100000000"
    assert [item.as_of_date for item in result.candidates] == ["2026-02-27"]


def test_same_instant_contradictory_values_conflict_and_never_pick_the_largest() -> None:
    result = select_share_basis(
        _shares(
            _obs("dei", "2026-02-27", "100000000"),
            _obs("gaap", "2026-02-27", "120000000", name="CommonStockSharesOutstanding", namespace="us-gaap"),
        ),
        _no_actions(),
        AS_OF,
    )
    assert result.status == "conflict" and result.selected is None
    assert {item.value for item in result.candidates} == {"100000000", "120000000"}
    assert any(reason.startswith("contradicted:2026-02-27:") for reason in result.conflicts)
    _round_trip(result)


def test_unit_mismatch_at_the_selected_instant_is_a_conflict_not_a_choice() -> None:
    mismatched = _obs("usd", "2026-02-27", "100000000")
    mismatched["normalized"]["unit"] = "USD"
    result = select_share_basis(_shares(_obs("dei", "2026-02-27", "100000000"), mismatched), _no_actions(), AS_OF)
    assert result.status == "conflict" and result.selected is None
    assert any("unit_mismatch:USD" in reason for reason in result.conflicts)
    _round_trip(result)


def test_ambiguous_fact_at_the_same_instant_contradicts() -> None:
    result = select_share_basis(
        _shares(
            _obs("dei", "2026-02-27", "100000000"),
            _obs("amb", "2026-02-27", None, disposition="ambiguous", reason="multiple_distinct_values_for_fact_slot"),
        ),
        _no_actions(),
        AS_OF,
    )
    assert result.status == "conflict"
    assert any("ambiguous:multiple_distinct_values_for_fact_slot" in reason for reason in result.conflicts)


def test_later_unconfirmed_fact_refuses_the_older_clean_basis_review_class_3() -> None:
    result = select_share_basis(
        _shares(
            _obs("clean", "2025-12-31", "98000000"),
            _obs("later", "2026-02-27", None, disposition="deferred", reason="missing_filing_provenance"),
        ),
        _no_actions(),
        AS_OF,
    )
    assert result.status == "refused" and result.selected is None
    assert any(reason.startswith(f"unconfirmed:{obs_id('later')}:deferred") for reason in result.conflicts)
    _round_trip(result)


def test_stale_basis_is_refused_review_class_3() -> None:
    result = select_share_basis(
        _shares(_obs("stale", "2025-09-30", "95000000", filed="2025-11-05", available_at="2025-11-05T21:00:00Z")),
        _no_actions(),
        AS_OF,
    )
    age = (datetime(2026, 4, 15).date() - datetime(2025, 9, 30).date()).days
    assert age > MAX_BASIS_AGE_DAYS
    assert result.status == "refused"
    assert f"stale:2025-09-30:{age}d" in result.conflicts
    _round_trip(result)


def test_only_unconfirmed_facts_refuse_with_value_free_candidates() -> None:
    result = select_share_basis(
        _shares(_obs("amb", "2026-02-27", None, disposition="ambiguous", reason="multiple_distinct_contexts_for_fact_slot")),
        _no_actions(),
        AS_OF,
    )
    assert result.status == "refused"
    assert [item.value for item in result.candidates] == [None]


# ---------------------------------------------------------------------------
# A16: no substitution between bases
# ---------------------------------------------------------------------------


def test_public_float_dollars_never_become_a_share_basis() -> None:
    result = select_share_basis(
        _shares(_obs("float", "2025-06-30", "250000000", kind="public_float", name="EntityPublicFloat", unit="USD")),
        _no_actions(),
        AS_OF,
    )
    assert result.status == "refused" and result.selected is None and result.candidates == ()
    assert f"rejected:{obs_id('float')}:public_float_usd_is_not_a_share_basis" in result.conflicts
    _round_trip(result)


def test_public_float_beside_a_count_is_rejected_not_compared() -> None:
    result = select_share_basis(
        _shares(
            _obs("float", "2026-02-27", "900000000", kind="public_float", name="EntityPublicFloat", unit="USD"),
            _obs("dei", "2026-02-27", "100000000"),
        ),
        _no_actions(),
        AS_OF,
    )
    assert result.status == "selected" and result.selected is not None
    assert result.selected.value == "100000000"
    assert all(item.observation_id != obs_id("float") for item in result.candidates)


def test_weighted_average_or_non_affiliate_metrics_are_never_admitted() -> None:
    for kind in ("weighted_average_eps", "non_affiliate_public_float"):
        record = _obs(kind, "2026-02-27", "100000000")
        record["metric"]["kind"] = kind
        result = select_share_basis(_shares(record), _no_actions(), AS_OF)
        assert result.status == "refused" and result.selected is None
        assert f"rejected:{obs_id(kind)}:metric_not_admitted:{kind}" in result.conflicts


def test_shares_and_dollars_with_the_same_digits_do_not_merge() -> None:
    # A unit mismatch at one instant refuses rather than picking the newest.
    usd = _obs("usd", "2026-03-31", "100000000")
    usd["normalized"]["unit"] = "USD"
    result = select_share_basis(_shares(_obs("dei", "2026-02-27", "100000000"), usd), _no_actions(), AS_OF)
    assert result.status == "refused"
    assert any("unit_mismatch:USD" in reason for reason in result.conflicts)


# ---------------------------------------------------------------------------
# Point in time, supersession and authority (A17)
# ---------------------------------------------------------------------------


def test_records_not_yet_available_are_invisible() -> None:
    result = select_share_basis(
        _shares(
            _obs("seen", "2025-12-31", "98000000"),
            _obs("future", "2026-03-31", "130000000", filed="2026-04-20", available_at="2026-04-20T21:00:00Z"),
        ),
        _no_actions(),
        AS_OF,
    )
    assert result.status == "selected" and result.selected is not None and result.selected.value == "98000000"
    assert f"not_yet_available:{obs_id('future')}" in result.conflicts


def test_period_after_as_of_is_rejected() -> None:
    result = select_share_basis(
        _shares(_obs("ahead", "2026-05-01", "98000000", filed="2026-04-01", available_at="2026-04-01T21:00:00Z")),
        _no_actions(),
        AS_OF,
    )
    assert result.status == "refused"
    assert f"rejected:{obs_id('ahead')}:instant_after_as_of" in result.conflicts


def test_corrected_record_supersedes_its_predecessor() -> None:
    original = _obs("orig", "2026-02-27", "100000000")
    corrected = _obs("corr", "2026-02-27", "101000000", correction_of=obs_id("orig"), supersedes=(obs_id("orig"),))
    result = select_share_basis(_shares(original, corrected), _no_actions(), AS_OF)
    assert result.status == "selected" and result.selected is not None and result.selected.value == "101000000"
    assert f"superseded:{obs_id('orig')}:by:{obs_id('corr')}" in result.conflicts


def test_an_input_claiming_denominator_or_ledger_authority_is_refused_outright() -> None:
    granted = _obs("ledger", "2026-02-27", "100000000")
    granted["authority"]["share_count_ledger_authority"] = True
    with pytest.raises(ShareBasisInputError, match="share_count_ledger_authority"):
        select_share_basis(_shares(granted), _no_actions(), AS_OF)
    with pytest.raises(ShareBasisInputError, match="selects_denominator"):
        evaluate_split_actions(
            [_stage("authorization", authority={"selects_denominator": True, "is_context_only": True})],
            issuer_id=ISSUER, security_class_id=SECURITY, count_instant=datetime(2026, 1, 31).date(), as_of=_as_of(),
        )


def test_mixed_issuers_refuse_to_judge() -> None:
    with pytest.raises(ShareBasisInputError, match="mixed issuers"):
        select_share_basis(
            _shares(_obs("a", "2026-02-27", "1"), _obs("b", "2026-02-27", "2", issuer="issuer:0000000002")),
            _no_actions(),
            AS_OF,
        )


def test_no_observations_is_unavailable_not_zero() -> None:
    result = select_share_basis(
        ShareInputs(GenerationBinding("share_count_observations", None, "unavailable"), ()),
        _events(_event("vote", "shareholder_vote_candidate", "2026-03-01")),
        AS_OF,
    )
    assert result.status == "unavailable" and result.selected is None
    assert result.provenance.support == "unavailable"
    _round_trip(result)


# ---------------------------------------------------------------------------
# Event-spine path (unconditional): a charter amendment refuses, a vote is a note
# ---------------------------------------------------------------------------


def test_charter_amendment_after_the_count_refuses_the_pre_amendment_basis() -> None:
    result = select_share_basis(
        _shares(_obs("dei", "2026-02-27", "100000000")),
        _events(_event("charter", "charter_amendment_candidate", "2026-03-03")),
        AS_OF,
    )
    assert result.status == "refused" and result.selected is None
    assert "unconfirmed:charter_amendment_candidate:event:charter:2026-03-03" in result.conflicts
    assert result.corporate_action.kind == "none"
    _round_trip(result)


def test_vote_or_authorization_alone_is_never_an_effective_split() -> None:
    result = select_share_basis(
        _shares(_obs("dei", "2026-02-27", "100000000")),
        _events(_event("vote", "shareholder_vote_candidate", "2026-03-03"), _event("proxy", "authorization_or_vote_candidate", "2026-03-04")),
        AS_OF,
    )
    assert result.status == "selected" and result.selected is not None and result.selected.value == "100000000"
    assert "rejected:event:vote:vote_or_authorization_is_not_an_effective_split" in result.conflicts
    assert "rejected:event:proxy:vote_or_authorization_is_not_an_effective_split" in result.conflicts
    assert result.corporate_action.kind == "none"


def test_charter_amendment_filed_before_the_count_is_already_reflected() -> None:
    result = select_share_basis(
        _shares(_obs("dei", "2026-02-27", "100000000")),
        _events(_event("charter", "charter_amendment_candidate", "2026-01-15")),
        AS_OF,
    )
    assert result.status == "selected"


# ---------------------------------------------------------------------------
# Four-stage split evaluator (A18/A19), on the exact proposed record shape
# ---------------------------------------------------------------------------


def _evaluate(actions, *, count: str = "2026-02-15"):
    return evaluate_split_actions(
        actions, issuer_id=ISSUER, security_class_id=SECURITY,
        count_instant=datetime.fromisoformat(count).date(), as_of=_as_of(),
    )


def test_four_separately_evidenced_stages_apply_the_split() -> None:
    decision = _evaluate(_four())
    assert decision.refusals == ()
    assert decision.applied.kind == "reverse_split"
    assert decision.applied.ratio == "0.1" and decision.applied.effective_date == "2026-03-02"
    assert (decision.numerator, decision.denominator) == (1, 10)
    assert {ref.span_id for ref in decision.applied.contract_adjustment_evidence} == {f"span:{stage}" for stage in sb.SPLIT_STAGES}


@pytest.mark.parametrize("missing", sb.SPLIT_STAGES)
def test_each_stage_is_separately_required(missing: str) -> None:
    decision = _evaluate([item for item in _four() if item["stage"] != missing])
    assert decision.applied.kind == "none"
    assert len(decision.refusals) == 1 and decision.refusals[0].endswith(f"missing:{missing}")


def test_vote_alone_is_pending_not_a_split() -> None:
    decision = _evaluate([_stage("authorization"), _stage("vote")])
    assert decision.applied.kind == "none"
    assert decision.refusals == ("unconfirmed:split_pending:ca:0000000001:rs-2026-03:missing:effective+exchange_adjustment",)


def test_disagreeing_ratio_refuses() -> None:
    actions = _four()
    actions[3] = _stage("exchange_adjustment", ratio={"new_shares": "1", "old_shares": "20"})
    decision = _evaluate(actions)
    assert decision.applied.kind == "none"
    assert "unconfirmed:split_ratio_disagrees:ca:0000000001:rs-2026-03" in decision.refusals


def test_split_on_another_security_never_scales_common() -> None:
    decision = _evaluate(_four(security_class_id="issuer:0000000001:security:preferred_a"))
    assert decision.applied.kind == "none"
    assert decision.refusals == ("unconfirmed:split_security_unmatched:ca:0000000001:rs-2026-03",)


def test_split_effective_before_the_count_is_already_in_the_count() -> None:
    decision = _evaluate(_four(), count="2026-03-10")
    assert decision.applied.kind == "none" and decision.refusals == ()
    assert decision.notes == ("already_reflected:ca:0000000001:rs-2026-03:effective_before_count:2026-03-02",)


def test_split_effective_on_the_count_date_is_unconfirmed() -> None:
    decision = _evaluate(_four(), count="2026-03-02")
    assert decision.refusals == ("unconfirmed:split_effective_on_count_date:ca:0000000001:rs-2026-03",)


def test_split_effective_after_as_of_is_not_applied() -> None:
    decision = _evaluate(_four(effective_date="2026-05-01"))
    assert decision.applied.kind == "none" and decision.refusals == ()
    assert decision.notes == ("rejected:ca:0000000001:rs-2026-03:effective_after_as_of:2026-05-01",)


def test_ratio_direction_must_match_the_kind() -> None:
    decision = _evaluate(_four(ratio={"new_shares": "10", "old_shares": "1"}))
    assert decision.refusals == ("unconfirmed:split_ratio_inconsistent_with_kind:ca:0000000001:rs-2026-03",)


def test_unobserved_stage_does_not_count() -> None:
    actions = _four()
    actions[2] = _stage("effective", state={"disposition": "ambiguous", "reason": "conflicting_dates"})
    decision = _evaluate(actions)
    assert decision.refusals[0].startswith("unconfirmed:split_pending:")


def test_stage_not_yet_available_does_not_count() -> None:
    actions = _four()
    actions[3] = _stage("exchange_adjustment", point_in_time={"available_at": "2026-05-01T00:00:00Z"})
    decision = _evaluate(actions)
    assert decision.refusals == ("unconfirmed:split_stage_unevidenced:ca:0000000001:rs-2026-03:missing:exchange_adjustment",)


def test_unmodeled_action_kind_refuses() -> None:
    decision = _evaluate(_four(action_kind="reclassification"))
    assert decision.refusals == ("unconfirmed:corporate_action_not_modeled:ca:0000000001:rs-2026-03:reclassification",)


def test_two_splits_after_the_count_refuse() -> None:
    second = [
        _stage(stage, action_id="ca:0000000001:fs-2026-04", observation_id=f"ca:0000000001:fs-2026-04:{stage}",
               action_kind="forward_split", ratio={"new_shares": "2", "old_shares": "1"}, effective_date="2026-04-01")
        for stage in sb.SPLIT_STAGES
    ]
    decision = _evaluate(_four() + second)
    assert decision.applied.kind == "none"
    assert decision.refusals[0].startswith("unconfirmed:multiple_corporate_actions_after_count:")


def test_non_terminating_ratio_is_rounded_with_an_exact_note() -> None:
    decision = _evaluate(_four(ratio={"new_shares": "1", "old_shares": "3"}))
    assert decision.applied.ratio == "0.333333333333"
    assert "split_ratio:1-for-3" in decision.notes
    assert (decision.numerator, decision.denominator) == (1, 3)


@pytest.mark.skipif("corporate_actions" not in COMPATIBLE_INPUT_SCHEMAS, reason="C0 corporate_actions family not yet admitted on this base")
def test_end_to_end_split_scales_only_the_pre_split_matched_count() -> None:
    actions = CorporateActionInputs(
        GenerationBinding("corporate_actions", CA_SCHEMA, "partial", generation_id="gen:corporate-actions-2026-10-14"), tuple(_four())
    )
    result = select_share_basis(_shares(_obs("dei", "2026-02-15", "100000000", filed="2026-02-20", available_at="2026-02-20T21:00:00Z")), actions, AS_OF)
    assert result.status == "selected" and result.selected is not None
    assert result.selected.value == "10000000"
    assert result.corporate_action.kind == "reverse_split" and result.corporate_action.ratio == "0.1"
    assert {item.value for item in result.candidates} == {"100000000", "10000000"}
    _round_trip(result)

    fractional = select_share_basis(_shares(_obs("odd", "2026-02-15", "100000005", filed="2026-02-20", available_at="2026-02-20T21:00:00Z")), actions, AS_OF)
    assert fractional.status == "refused"
    assert "unconfirmed:fractional_share_treatment_unknown:ca:0000000001:rs-2026-03" in fractional.conflicts


# ---------------------------------------------------------------------------
# Determinism, receipts, A48 and B0 parity
# ---------------------------------------------------------------------------


def test_result_is_deterministic_and_receipted() -> None:
    inputs = (_shares(_obs("dei", "2026-02-27", "100000000")), _no_actions(), AS_OF)
    first, second = select_share_basis(*inputs), select_share_basis(*inputs)
    assert first.as_record() == second.as_record()
    assert first.receipt.rule_digest == sb.RULE_DIGEST
    assert first.receipt.implementation_digest == sha256_of({"contract": STATE_CONTRACT_VERSION, "implementation": sb.IMPLEMENTATION})
    assert first.receipt.input_digest != select_share_basis(_shares(_obs("dei", "2026-02-27", "100000001")), _no_actions(), AS_OF).receipt.input_digest
    assert first.receipt.computed_at == AS_OF


def test_no_forbidden_property_anywhere_in_the_result() -> None:
    def walk(node):
        if isinstance(node, dict):
            for key, item in node.items():
                assert not FORBIDDEN_PROPERTY_PATTERN.match(key), key
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(select_share_basis(_shares(_obs("dei", "2026-02-27", "100000000")), _no_actions(), AS_OF).as_record())


def test_support_limits_match_the_b0_admission_config() -> None:
    path = ROOT / sb.ADMISSION_CONFIG
    if not path.exists():
        pytest.skip("B0 admission config not on this base")
    config = json.loads(path.read_text())
    assert tuple(config["admission"]["support_limits"]) == SUPPORT_LIMITS
