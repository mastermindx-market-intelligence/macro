"""B04-A0 contract tests for the episode evidence dossier wrapper.

Ratified contract: R6-B04-01a (A7-A12). Every scope item of the A0 lane has an
adverse test here: the committed reason map equals the ratified fence
byte-for-byte; the A9 mapping, A10 precedence and A7 clock split behave as
amended; the A12 wrapper shape is closed with both view_decision_admissible
flags literal false; authority stays the six all-false booleans and a forbidden
input key is rejected. Real vectors come from the existing D5 builder with
injected owner reads; synthetic families cover receipt conditions the builder
does not mint yet (conflicting spans). CI registration of this file is the
seat's landing act, not this lane's.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from engine.prophet_lab.evidence_dossier import (
    ANNOTATION_CODES,
    DISPLAY_CODE_PRECEDENCE,
    SCHEMA as DOSSIER_SCHEMA,
    EvidenceDossierContractError,
    build_evidence_dossier,
    classify_point_in_time_clocks,
    load_reason_map,
    project_view,
    resolve_display_code,
    select_display_code,
    validate_evidence_dossier,
)
from engine.prophet_lab.intelligence_vector import (
    ALL_FALSE_AUTHORITY,
    build_earnings_intelligence_vector,
)
from engine.us_candidate_episode import episode_id as b1_episode_id
from lib.dataos.identity import IssuerMaster

ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = ROOT / "research/prophet_v4/r6_program/rulings/R6-B04-01a_DOSSIER_CONTRACT_AMENDMENT_DRAFT_2026-09-24.md"
REASON_MAP_FILE = ROOT / "config/prophet_dossier_reason_map.v1.json"
FIXTURES = ROOT / "tests/fixtures/prophet_lab_dossier"
#: The ratified fence wraps amendment lines 163-303 inclusive (1-based).
FENCE_FIRST_LINE = 163
FENCE_LAST_LINE = 303

_CUT = "2026-07-30T20:05:00Z"
_LANES = ("FACT_REVENUE", "GUIDANCE_REVENUE_YOY_PCT", "DELTA_REVENUE")
_ALLOWED = {lane: "USER_FACING" for lane in _LANES}
_DOS_ID_RE = re.compile(r"^dos:[0-9a-f]{64}$")

_EXPECTED_FIXTURES = {
    # one fixture per A10 display code
    "identity_binding_conflict", "identity_unresolved", "rights_not_a_source",
    "rights_internal_only", "rights_undetermined",
    "source_temporarily_unavailable", "source_unavailable",
    "conflicting_source_spans", "conflicting_source_clocks",
    "not_published_at_decision", "not_captured_at_decision",
    "not_available_at_decision", "historical_event_set_unavailable",
    "exact_lineage_unavailable", "stale", "not_applicable", "unknown",
    # one fixture per user_redistribution posture
    "posture_user_facing", "posture_user_facing_with_limits",
    "posture_internal_only", "posture_not_a_source", "posture_absent",
}

_ANCHOR = {
    "kind": "turn_watch_reset_low",
    "time": "2026-07-30T20:00:00Z",
    "price": "100.0000",
    "basis": "turn_watch.reset_low",
    "source_receipt": "sha256:" + "b" * 64,
}
_EVENT_ID = "evt_cik0000320193_2026q3_results"
_GENERATION_ID = "peg:" + "a" * 64


def _workspace(*, value: int, unit: str, generation_id: str, src: str | None, obs: str | None, gen: str | None, fact_document_id: str) -> dict:
    return {
        "schema": "event_workspace.v1",
        "event_id": _EVENT_ID,
        "generation_id": generation_id,
        "issuer": {"company_id": "cik:0000320193", "display_name": "Apple Inc."},
        "fiscal_period": {"year": 2026, "quarter": 3, "calendar_end": "2026-06-27"},
        "lifecycle": {
            "state": "complete",
            "source_available_at": src,
            "observed_at": obs,
        },
        "generated_at": gen,
        "facts": [{
            "schema": "event_fact.v1",
            "metric": "revenue",
            "value": value,
            "unit": unit,
            "period": "2026Q3",
            "basis": "reported",
            "source_span": {"document_id": fact_document_id},
        }],
        "deltas": [{
            "schema": "metric_delta.v1",
            "metric": "revenue",
            "current": {"value": value, "unit": unit, "basis": "reported"},
            "prior": {"state": "absent", "reason": "not_available"},
            "consensus": {"state": "absent", "reason": "consensus_unlicensed"},
            "basis_match": False,
        }],
        "guidance": [],
        "claims": [],
        "sources": [{
            "kind": "issuer_release",
            "document_id": "doc:issuer-release:1",
            "source_sha256": "c" * 64,
            "receipt_state": "byte_replayed",
        }],
        "warnings": [],
    }


def _revision(*, value: int = 109_417_000_000, unit: str = "USD", generation_id: str = "1" * 24,
              src: str | None = "2026-07-30T20:00:00Z", obs: str | None = "2026-07-30T20:03:00Z",
              gen: str | None = "2026-07-30T20:04:00Z", fact_document_id: str = "doc:issuer-release:1") -> dict:
    workspace = _workspace(
        value=value, unit=unit, generation_id=generation_id, src=src, obs=obs, gen=gen,
        fact_document_id=fact_document_id,
    )
    canonical = json.dumps(
        workspace, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()
    return {
        "generation_id": generation_id,
        "source_sha256": workspace["sources"][0]["source_sha256"],
        "source_available_at": src,
        "observed_at": obs,
        "lifecycle_state": "complete",
        "form": "8-K",
        "workspace_receipt": {"sha256": sha256(canonical).hexdigest(), "bytes": len(canonical)},
        "workspace": workspace,
    }


_ISSUER_MASTER = IssuerMaster.from_records([{
    "security_id": "SEC:US-XNAS-AAPL",
    "issuer_id": "ISS:US:320193",
    "issuer_state": "active",
    "listing_key": "US:XNAS:AAPL",
    "issuer_cik": "0000320193",
}])
_EPISODE = {
    "schema": "prophet.candidate_episode/v1",
    "episode_id": b1_episode_id("SEC:US-XNAS-AAPL", "epoch_0", _ANCHOR, 1),
    "company_id": "ISS:US:320193",
    "security_id": "SEC:US-XNAS-AAPL",
    "identity_epoch": "epoch_0",
    "state": "CANDIDATE",
    "opened_at": _CUT,
    "opened_session": "2026-07-30",
    "structural_anchor": _ANCHOR,
    "expert_events": ["radar:event:content-addressed-1"],
}


def _real_vector(revisions: list[dict]) -> dict:
    return build_earnings_intelligence_vector(
        episode=_EPISODE,
        episode_generation_id=_GENERATION_ID,
        episode_known_at=_CUT,
        issuer_master=_ISSUER_MASTER,
        find_event_id=lambda company_id: _EVENT_ID,
        read_revisions=lambda event_id: revisions,
    )


def _synthetic_family(
    *, basis: str = "not_evaluated", reasons: tuple[str, ...] = ("UNKNOWN",),
    clocks: tuple[str | None, str | None, str | None] = (
        "2026-07-30T20:00:00Z", "2026-07-30T20:03:00Z", "2026-07-30T20:04:00Z",
    ),
) -> dict:
    src, obs, gen = clocks
    return {
        "family_projection_id": "pif:" + "1" * 64,
        "coverage": {"state": "UNKNOWN", "basis": basis},
        "quality": {"flags": []},
        "observations": [{
            "native_metric_id": "earnings:event_workspace",
            "value_state": "ABSENT",
            "absence_reasons": list(reasons),
        }],
        "point_in_time": {
            "missing_clocks": [],
            "source_published_at": {"value": src},
            "known_at": {"value": obs},
            "computed_at": {"value": gen},
        },
        "trajectory": {"state": "NOT_APPLICABLE", "dimensions": []},
        "owner_lane_dispositions": {"lanes": [
            {"lane": lane, "disposition": "ABSENT"} for lane in _LANES
        ]},
        "source_refs": [],
        "evidence_roots": [],
        "explanation_facts": [],
    }


def _synthetic_vector(family: dict) -> dict:
    return {
        "schema": "prophet.intelligence_vector/v1",
        "projection_id": "piv:" + "2" * 64,
        "decision_cut": {"opened_at": _CUT},
        "evidence_families": [family],
    }


def _codes(dossier: dict, *, view: str = "original") -> dict[str, str | None]:
    return {
        row["lane"]: row["code"] for row in dossier["missingness"] if row["view"] == view
    }


def _messages(dossier: dict, lane: str) -> list[dict]:
    return [message for message in dossier["messages"] if message["lane"] == lane]


# --- 1. committed reason map: bytes, parse, closed shape ---------------------


def test_reason_map_file_equals_the_ratified_fence_byte_for_byte() -> None:
    amendment_lines = AMENDMENT.read_bytes().splitlines(keepends=True)
    fence = b"".join(
        amendment_lines[FENCE_FIRST_LINE - 1:FENCE_LAST_LINE]
    )
    assert amendment_lines[FENCE_FIRST_LINE - 2] == b"```json\n"
    assert amendment_lines[FENCE_LAST_LINE] == b"```\n"
    assert REASON_MAP_FILE.read_bytes() == fence


def test_reason_map_file_parses_and_pins_the_a10_order() -> None:
    payload = json.loads(REASON_MAP_FILE.read_text(encoding="utf-8"))
    assert payload["schema"] == "prophet.dossier_reason_map/v1"
    assert payload["display_codes"] == list(DISPLAY_CODE_PRECEDENCE)
    assert payload["annotation_codes"] == list(ANNOTATION_CODES)
    assert set(payload["sentences"]) == set(DISPLAY_CODE_PRECEDENCE) | set(ANNOTATION_CODES)
    for sentence in payload["sentences"].values():
        assert set(sentence) == {"en", "zh"}
        assert sentence["en"].strip() and sentence["zh"].strip()
    assert load_reason_map(ROOT) == payload
    assert load_reason_map() == payload  # module-relative default root


def test_reason_map_rows_carry_only_closed_keys_and_known_codes() -> None:
    payload = json.loads(REASON_MAP_FILE.read_text(encoding="utf-8"))
    for row in payload["map"]:
        assert set(row) == {"coverage_basis", "reason_id", "lane", "code"}
        assert row["code"] in DISPLAY_CODE_PRECEDENCE
        assert row["lane"] is None  # the committed table is lane-neutral
    reasons = {row["reason_id"] for row in payload["map"]}
    for required in (
        "current_event_not_published", "source_fetch_failed",
        "correction_chain_integrity", "missing_decision_clock", "STALE",
        "UNESTIMABLE", "CORRECTION_PENDING", "NOT_APPLICABLE", "not_available",
        "consensus_unlicensed", "no_span_addressable_evidence", "missing_source",
        "no_transcript", "unknown",
    ):
        assert required in reasons


# --- 2. A9 closed outcome-to-code mapping ------------------------------------


def test_null_lane_matches_every_lane_and_an_explicit_lane_wins() -> None:
    reason_map = {"map": [
        {"coverage_basis": None, "reason_id": "r", "lane": None, "code": "STALE"},
        {"coverage_basis": None, "reason_id": "r", "lane": "FACT_REVENUE", "code": "UNKNOWN"},
    ]}
    assert resolve_display_code(reason_map, None, "r", "FACT_REVENUE") == "UNKNOWN"
    assert resolve_display_code(reason_map, None, "r", "DELTA_REVENUE") == "STALE"
    assert resolve_display_code(reason_map, None, "r") == "STALE"


def test_explicit_coverage_basis_outranks_an_explicit_lane() -> None:
    reason_map = {"map": [
        {"coverage_basis": "b", "reason_id": "r", "lane": None, "code": "STALE"},
        {"coverage_basis": None, "reason_id": "r", "lane": "FACT_REVENUE", "code": "NOT_APPLICABLE"},
    ]}
    assert resolve_display_code(reason_map, "b", "r", "FACT_REVENUE") == "STALE"
    assert resolve_display_code(reason_map, None, "r", "FACT_REVENUE") == "NOT_APPLICABLE"


def test_unmapped_reason_resolves_to_unknown_never_a_positive_code() -> None:
    reason_map = load_reason_map(ROOT)
    assert resolve_display_code(reason_map, "no_such_basis", "no_such_reason") == "UNKNOWN"
    assert resolve_display_code(reason_map, "source_fetch_failed", "no_such_reason") == "UNKNOWN"


def test_colliding_rows_inside_one_tier_fail_closed() -> None:
    reason_map = {"map": [
        {"coverage_basis": None, "reason_id": "r", "lane": None, "code": "STALE"},
        {"coverage_basis": None, "reason_id": "r", "lane": None, "code": "UNKNOWN"},
    ]}
    with pytest.raises(EvidenceDossierContractError):
        resolve_display_code(reason_map, None, "r")


# --- 3. A10 one precedence, one code per lane --------------------------------


def test_precedence_selects_the_earliest_present_code() -> None:
    assert select_display_code(["STALE", "RIGHTS_INTERNAL_ONLY"]) == "RIGHTS_INTERNAL_ONLY"
    assert select_display_code(["UNKNOWN", "NOT_APPLICABLE"]) == "NOT_APPLICABLE"
    assert select_display_code(["CONFLICTING_SOURCE_SPANS", "SOURCE_UNAVAILABLE", "STALE"]) == "SOURCE_UNAVAILABLE"
    assert select_display_code([]) is None


def test_corrected_later_never_participates_in_precedence() -> None:
    assert select_display_code(["CORRECTED_LATER"]) is None
    assert select_display_code(["CORRECTED_LATER", "STALE"]) == "STALE"


def test_lane_with_several_conditions_resolves_to_one_earliest_code() -> None:
    # rights block (rank 4) + temporary source failure (rank 6) + late
    # computation (rank 12): only RIGHTS_INTERNAL_ONLY survives, once per lane.
    vector = _synthetic_vector(_synthetic_family(
        basis="source_fetch_failed", reasons=("SOURCE_UNAVAILABLE",),
        clocks=("2026-07-30T20:00:00Z", "2026-07-30T20:03:00Z", "2026-07-30T20:06:00Z"),
    ))
    dossier = build_evidence_dossier(
        vector, rights={lane: "INTERNAL_ONLY" for lane in _LANES},
    )
    assert {row["state"] for row in dossier["rights"]} == {"INTERNAL_ONLY"}
    for lane in _LANES:
        lane_messages = _messages(dossier, lane)
        assert [message["code"] for message in lane_messages] == ["RIGHTS_INTERNAL_ONLY"]


# --- 4. A7 publication and capture are different absence reasons -------------


def test_publication_after_the_cut_is_not_published_at_decision() -> None:
    vector = _real_vector([_revision(
        src="2026-07-30T20:06:00Z", obs="2026-07-30T20:03:00Z", gen="2026-07-30T20:04:00Z",
    )])
    dossier = build_evidence_dossier(vector, rights=_ALLOWED)
    assert set(_codes(dossier).values()) == {"NOT_PUBLISHED_AT_DECISION"}


def test_late_capture_with_owner_attestation_is_not_captured_at_decision() -> None:
    vector = _real_vector([_revision(
        src="2026-07-30T20:00:00Z", obs="2026-07-30T20:06:00Z", gen="2026-07-30T20:04:00Z",
    )])
    dossier = build_evidence_dossier(
        vector, rights=_ALLOWED, observed_at_attests_capture=True,
    )
    assert set(_codes(dossier).values()) == {"NOT_CAPTURED_AT_DECISION"}


def test_late_observation_without_attestation_never_says_captured() -> None:
    vector = _real_vector([_revision(
        src="2026-07-30T20:00:00Z", obs="2026-07-30T20:06:00Z", gen="2026-07-30T20:04:00Z",
    )])
    dossier = build_evidence_dossier(
        vector, rights=_ALLOWED, observed_at_attests_capture=False,
    )
    assert set(_codes(dossier).values()) == {"NOT_AVAILABLE_AT_DECISION"}
    for message in dossier["messages"]:
        assert "captur" not in message["en"].lower()
        assert "取得" not in message["zh"]


def test_late_computation_is_not_available_at_decision() -> None:
    vector = _real_vector([_revision(
        src="2026-07-30T20:00:00Z", obs="2026-07-30T20:03:00Z", gen="2026-07-30T20:06:00Z",
    )])
    dossier = build_evidence_dossier(vector, rights=_ALLOWED)
    assert set(_codes(dossier).values()) == {"NOT_AVAILABLE_AT_DECISION"}


def test_all_clocks_before_the_cut_grant_no_admission() -> None:
    vector = _real_vector([_revision()])
    before = deepcopy(vector)
    dossier = build_evidence_dossier(vector, rights=_ALLOWED)
    assert vector == before
    assert dossier["views"]["original"]["state"] == "PRESENT"
    assert dossier["views"]["original"]["view_decision_admissible"] is False
    assert dossier["views"]["current"]["view_decision_admissible"] is False
    codes = _codes(dossier)
    assert codes["FACT_REVENUE"] is None  # present lane: NONE missingness, null code
    positive = {
        "NOT_PUBLISHED_AT_DECISION", "NOT_CAPTURED_AT_DECISION", "NOT_AVAILABLE_AT_DECISION",
    }
    assert not positive & {code for code in codes.values() if code}


def test_missing_clocks_resolve_to_neutral_unknown() -> None:
    vector = _real_vector([_revision(obs=None)])
    dossier = build_evidence_dossier(
        vector, rights=_ALLOWED, observed_at_attests_capture=True,
    )
    assert set(_codes(dossier).values()) == {"UNKNOWN"}
    family = vector["evidence_families"][0]
    assert family["point_in_time"]["missing_clocks"] == ["observed_at"]


def test_invalid_clocks_do_not_mint_positive_codes() -> None:
    assert classify_point_in_time_clocks(
        source_available_at="not-a-clock", observed_at="2026-07-30T20:03:00Z",
        generated_at="2026-07-30T20:04:00Z", cut=_CUT,
    ) is None
    assert classify_point_in_time_clocks(
        source_available_at="2026-07-30T20:00:00",  # naive timestamp: no owner contract
        observed_at="2026-07-30T20:03:00Z", generated_at="2026-07-30T20:04:00Z", cut=_CUT,
    ) is None
    vector = _synthetic_vector(_synthetic_family(
        clocks=("20:00", "2026-07-30T20:06:00Z", "2026-07-30T20:04:00Z"),
    ))
    dossier = build_evidence_dossier(
        vector, rights=_ALLOWED, observed_at_attests_capture=True,
    )
    assert set(_codes(dossier).values()) == {"UNKNOWN"}


def test_conflicting_clocks_keep_only_the_native_conflict() -> None:
    tied = [
        _revision(generation_id="1" * 24),
        _revision(generation_id="2" * 24),
    ]
    vector = _real_vector(tied)
    family = vector["evidence_families"][0]
    assert family["coverage"]["basis"] == "unresolved_clock_tie"
    dossier = build_evidence_dossier(
        vector, rights=_ALLOWED, observed_at_attests_capture=True,
    )
    assert set(_codes(dossier).values()) == {"CONFLICTING_SOURCE_CLOCKS"}


# --- 5. A11 explicit inputs ---------------------------------------------------


def test_identity_binding_conflict_comes_from_the_explicit_input_or_the_map() -> None:
    vector = _synthetic_vector(_synthetic_family())
    neutral = build_evidence_dossier(vector, rights=_ALLOWED)
    assert set(_codes(neutral).values()) == {"UNKNOWN"}
    conflicted = build_evidence_dossier(
        vector, rights=_ALLOWED, identity_binding_conflict=True,
    )
    assert set(_codes(conflicted).values()) == {"IDENTITY_BINDING_CONFLICT"}
    # The committed map row: an identity-ambiguous native basis is the only
    # non-input source in A0 (the typed exception is B04-A1).
    ambiguous = build_evidence_dossier(_synthetic_vector(_synthetic_family(
        basis="canonical_identity_ambiguous", reasons=("CONFLICTED",),
    )), rights=_ALLOWED)
    assert set(_codes(ambiguous).values()) == {"IDENTITY_BINDING_CONFLICT"}


def test_historical_event_set_unavailable_applies_to_the_original_view_only() -> None:
    vector = _synthetic_vector(_synthetic_family())
    current = _synthetic_vector(_synthetic_family())
    dossier = build_evidence_dossier(
        vector, rights=_ALLOWED, current_vector=current,
        historical_event_set_unavailable=True,
    )
    original_codes = _codes(dossier, view="original")
    current_codes = _codes(dossier, view="current")
    assert set(original_codes.values()) == {"HISTORICAL_EVENT_SET_UNAVAILABLE"}
    assert "HISTORICAL_EVENT_SET_UNAVAILABLE" not in current_codes.values()
    without_input = build_evidence_dossier(
        vector, rights=_ALLOWED, current_vector=current,
    )
    assert "HISTORICAL_EVENT_SET_UNAVAILABLE" not in {
        code for code in _codes(without_input).values() if code
    }


def test_corrected_later_annotates_only_a_present_original_value() -> None:
    vector = _real_vector([_revision()])
    dossier = build_evidence_dossier(
        vector, rights=_ALLOWED, corrected_later_lanes=["FACT_REVENUE"],
    )
    assert [message["code"] for message in _messages(dossier, "FACT_REVENUE")] == ["CORRECTED_LATER"]
    assert _codes(dossier)["FACT_REVENUE"] is None  # never reported as missing
    absent_lane = build_evidence_dossier(
        vector, rights=_ALLOWED, corrected_later_lanes=["GUIDANCE_REVENUE_YOY_PCT"],
    )
    assert _messages(absent_lane, "GUIDANCE_REVENUE_YOY_PCT") == []


# --- 6. A12 closed wrapper shape ----------------------------------------------


def test_wrapper_shape_is_closed_with_fixed_view_flags() -> None:
    vector = _synthetic_vector(_synthetic_family())
    dossier = build_evidence_dossier(vector, rights=_ALLOWED)
    assert set(dossier) == {
        "schema", "dossier_id", "views", "evidence_class", "rights",
        "missingness", "messages", "authority",
    }
    assert dossier["schema"] == DOSSIER_SCHEMA
    assert set(dossier["views"]) == {"original", "current"}
    for name, basis in (("original", None), ("current", "RESEARCH_KNOWN_NOW")):
        view = dossier["views"][name]
        assert set(view) == {
            "state", "view_basis", "view_decision_admissible", "vector_projection_id",
        }
        assert view["view_basis"] == basis
        assert type(view["view_decision_admissible"]) is bool
        assert view["view_decision_admissible"] is False
    assert dossier["evidence_class"] == {"state": "NOT_ASSERTED"}
    for message in dossier["messages"]:
        assert set(message) == {"lane", "code", "en", "zh"}
        assert message["en"].strip() and message["zh"].strip()
    for row in dossier["missingness"]:
        assert set(row) == {"view", "lane", "state", "code"}
    assert _DOS_ID_RE.fullmatch(dossier["dossier_id"])


def _built_dossier() -> dict:
    return build_evidence_dossier(
        _synthetic_vector(_synthetic_family()), rights=_ALLOWED,
    )


def test_unknown_enum_values_are_rejected() -> None:
    reason_map = load_reason_map(ROOT)
    mutations = [
        ("view state", lambda d: d["views"]["original"].__setitem__("state", "MAYBE")),
        ("view basis", lambda d: d["views"]["current"].__setitem__("view_basis", None)),
        ("admissible true", lambda d: d["views"]["original"].__setitem__("view_decision_admissible", True)),
        ("admissible zero", lambda d: d["views"]["original"].__setitem__("view_decision_admissible", 0)),
        ("missingness state", lambda d: d["missingness"][0].__setitem__("state", "HALF")),
        ("rights state", lambda d: d["rights"][0].__setitem__("state", "PUBLIC")),
        ("evidence class", lambda d: d["evidence_class"].__setitem__("state", "GUESS")),
        ("message code", lambda d: d["messages"][0].__setitem__("code", "MYSTERY")),
        ("message extra key", lambda d: d["messages"][0].__setitem__("tone", "neutral")),
        ("annotation as missingness", lambda d: d["missingness"][0].__setitem__("code", "CORRECTED_LATER")),
    ]
    for _name, mutate in mutations:
        dossier = _built_dossier()
        mutate(dossier)
        with pytest.raises(EvidenceDossierContractError):
            validate_evidence_dossier(dossier, reason_map=reason_map)
    # NONE must carry a null code; PARTIAL/FULL must carry one A10 code.
    present = build_evidence_dossier(_real_vector([_revision()]), rights=_ALLOWED)
    none_row = next(row for row in present["missingness"] if row["state"] == "NONE")
    assert none_row["code"] is None
    full_row = deepcopy(next(row for row in _built_dossier()["missingness"] if row["state"] == "FULL"))
    full_row["code"] = None
    with pytest.raises(EvidenceDossierContractError):
        validate_evidence_dossier(
            {**_built_dossier(), "missingness": [full_row]}, reason_map=reason_map,
        )


def test_message_sentences_come_from_the_committed_table() -> None:
    reason_map = load_reason_map(ROOT)
    dossier = _built_dossier()
    for message in dossier["messages"]:
        assert message["en"] == reason_map["sentences"][message["code"]]["en"]
        assert message["zh"] == reason_map["sentences"][message["code"]]["zh"]
    swapped = _built_dossier()
    swapped["messages"][0]["en"] = reason_map["sentences"]["STALE"]["en"]
    with pytest.raises(EvidenceDossierContractError):
        validate_evidence_dossier(swapped, reason_map=reason_map)


def test_authority_is_the_six_all_false_booleans() -> None:
    dossier = _built_dossier()
    assert dossier["authority"] == ALL_FALSE_AUTHORITY
    assert set(dossier["authority"]) == {
        "can_rank", "can_gate", "can_size", "can_originate_signal",
        "can_change_entry_open", "can_change_execution",
    }
    assert all(type(value) is bool and value is False for value in dossier["authority"].values())
    reason_map = load_reason_map(ROOT)
    flipped = _built_dossier()
    flipped["authority"]["can_rank"] = True
    with pytest.raises(EvidenceDossierContractError):
        validate_evidence_dossier(flipped, reason_map=reason_map)
    widened = _built_dossier()
    widened["authority"]["can_decide"] = False
    with pytest.raises(EvidenceDossierContractError):
        validate_evidence_dossier(widened, reason_map=reason_map)


def test_forbidden_key_in_the_input_is_rejected() -> None:
    vector = _synthetic_vector(_synthetic_family())
    vector["evidence_families"][0]["score"] = 0.5
    with pytest.raises(EvidenceDossierContractError, match="forbidden"):
        build_evidence_dossier(vector, rights=_ALLOWED)
    dossier = _built_dossier()
    dossier["views"]["original"]["confidence"] = 0.5
    with pytest.raises(EvidenceDossierContractError):
        validate_evidence_dossier(dossier)


def test_dossier_id_addresses_the_finished_wrapper() -> None:
    vector = _synthetic_vector(_synthetic_family())
    first = build_evidence_dossier(vector, rights=_ALLOWED)
    second = build_evidence_dossier(vector, rights=_ALLOWED)
    assert first["dossier_id"] == second["dossier_id"]
    blocked = build_evidence_dossier(
        vector, rights={lane: "NOT_A_SOURCE" for lane in _LANES},
    )
    assert blocked["dossier_id"] != first["dossier_id"]
    reason_map = load_reason_map(ROOT)
    drifted = _built_dossier()
    drifted["messages"][0]["lane"] = "DELTA_REVENUE"
    with pytest.raises(EvidenceDossierContractError):
        validate_evidence_dossier(drifted, reason_map=reason_map)


# --- 7. A8 gated projection skeleton ------------------------------------------


def test_fail_closed_rights_default_blocks_every_lane() -> None:
    vector = _real_vector([_revision()])
    dossier = build_evidence_dossier(vector)  # no rights decision supplied
    assert {row["state"] for row in dossier["rights"]} == {"ABSENT"}
    assert dossier["views"]["original"]["state"] == "GATED"
    codes = _codes(dossier)
    # The undetermined posture blocks every lane; the delta lane additionally
    # carries its native consensus_unlicensed reason, which outranks
    # RIGHTS_UNDETERMINED in the A10 order (rank 3 before rank 5).
    assert codes["FACT_REVENUE"] == "RIGHTS_UNDETERMINED"
    assert codes["GUIDANCE_REVENUE_YOY_PCT"] == "RIGHTS_UNDETERMINED"
    assert codes["DELTA_REVENUE"] == "RIGHTS_NOT_A_SOURCE"


def test_unknown_posture_is_rejected() -> None:
    vector = _synthetic_vector(_synthetic_family())
    with pytest.raises(EvidenceDossierContractError):
        build_evidence_dossier(vector, rights={"FACT_REVENUE": "PUBLIC_DOMAIN"})


def test_passing_lanes_are_projected_without_mutation() -> None:
    vector = _real_vector([_revision()])
    before = deepcopy(vector)
    projected = project_view(vector, gated_lanes=())
    assert json.dumps(projected, sort_keys=True) == json.dumps(before, sort_keys=True)
    assert projected["projection_id"] == vector["projection_id"]


def test_gated_projection_removes_lane_evidence_and_recomputes_identity() -> None:
    vector = _real_vector([_revision()])
    family = vector["evidence_families"][0]
    assert any(
        observation["native_metric_id"] == "fact:revenue"
        for observation in family["observations"]
    )
    assert family["source_refs"] and family["evidence_roots"]
    dossier = build_evidence_dossier(vector, rights={
        "FACT_REVENUE": "NOT_A_SOURCE",
        "GUIDANCE_REVENUE_YOY_PCT": "USER_FACING",
        "DELTA_REVENUE": "USER_FACING",
    })
    assert dossier["views"]["original"]["state"] == "GATED"
    assert dossier["views"]["original"]["vector_projection_id"] != vector["projection_id"]
    projected = project_view(vector, gated_lanes=["FACT_REVENUE"])
    gated_family = projected["evidence_families"][0]
    assert gated_family["observations"] == []
    assert gated_family["source_refs"] == []
    assert gated_family["evidence_roots"] == []
    assert gated_family["family_projection_id"] != family["family_projection_id"]
    assert gated_family["authority"] == ALL_FALSE_AUTHORITY
    # trajectory is outside the A8 touch list and stays untouched in A0.
    assert gated_family["trajectory"] == family["trajectory"]
    codes = _codes(dossier)
    assert codes["FACT_REVENUE"] == "RIGHTS_NOT_A_SOURCE"
    assert codes["GUIDANCE_REVENUE_YOY_PCT"] == "UNKNOWN"


def test_current_view_projection_never_emits_inner_decision_admissibility() -> None:
    vector = _real_vector([_revision()])
    current = _real_vector([_revision()])
    projected = project_view(current, view="current")
    point_in_time = projected["evidence_families"][0]["point_in_time"]
    assert "decision_admissibility" not in point_in_time
    assert projected["projection_id"] != current["projection_id"]
    assert "decision_admissibility" in current["evidence_families"][0]["point_in_time"]
    dossier = build_evidence_dossier(vector, rights=_ALLOWED, current_vector=current)
    assert dossier["views"]["current"]["state"] == "PRESENT"
    assert dossier["views"]["current"]["view_basis"] == "RESEARCH_KNOWN_NOW"
    assert dossier["views"]["current"]["vector_projection_id"] == projected["projection_id"]


def test_missingness_follows_lane_dispositions() -> None:
    vector = _real_vector([_revision()])
    dossier = build_evidence_dossier(vector, rights=_ALLOWED)
    codes = _codes(dossier)
    states = {
        row["lane"]: row["state"] for row in dossier["missingness"]
        if row["view"] == "original"
    }
    assert states["FACT_REVENUE"] == "NONE"
    assert codes["FACT_REVENUE"] is None
    assert states["GUIDANCE_REVENUE_YOY_PCT"] == "FULL"
    assert codes["GUIDANCE_REVENUE_YOY_PCT"] == "UNKNOWN"
    # The delta lane is projected, but its consensus side is unlicensed, so it
    # stays PARTIAL with the rights code the ratified map assigns to
    # consensus_unlicensed.
    assert states["DELTA_REVENUE"] == "PARTIAL"
    assert codes["DELTA_REVENUE"] == "RIGHTS_NOT_A_SOURCE"

    # A candidate the owner supplied but D5 could not project stays PARTIAL:
    # the fact row is a candidate, but its source span names no safe document,
    # so no observation is projected from it.
    unprojectable = _real_vector([_revision(fact_document_id="not a safe object id")])
    partial = build_evidence_dossier(unprojectable, rights=_ALLOWED)
    partial_states = {
        row["lane"]: row["state"] for row in partial["missingness"]
        if row["view"] == "original"
    }
    partial_codes = _codes(partial)
    assert partial_states["FACT_REVENUE"] == "PARTIAL"
    assert partial_codes["FACT_REVENUE"] == "EXACT_LINEAGE_UNAVAILABLE"


def test_vector_is_consumed_read_only() -> None:
    vector = _real_vector([_revision()])
    before = deepcopy(vector)
    build_evidence_dossier(
        vector,
        rights={lane: "INTERNAL_ONLY" for lane in _LANES},
        identity_binding_conflict=True,
        historical_event_set_unavailable=True,
        corrected_later_lanes=["FACT_REVENUE"],
    )
    assert vector == before
    family = vector["evidence_families"][0]
    assert family["point_in_time"]["source_published_at"]["value"] == "2026-07-30T20:00:00Z"
    assert vector["projection_id"] == before["projection_id"]


# --- 8. committed fixture matrix ----------------------------------------------


def test_fixture_matrix_is_complete() -> None:
    names = {path.stem for path in FIXTURES.glob("*.json")}
    assert names == _EXPECTED_FIXTURES


@pytest.mark.parametrize("name", sorted(_EXPECTED_FIXTURES))
def test_every_fixture_resolves_through_the_real_wrapper(name: str) -> None:
    fixture = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    inputs = dict(fixture["inputs"])
    dossier = build_evidence_dossier(fixture["vector"], **inputs)
    validate_evidence_dossier(dossier)
    message_codes = {message["code"] for message in dossier["messages"]}
    assert fixture["expected_code"] in message_codes
    expected_state = fixture.get("expected_rights_state")
    if expected_state is not None:
        assert {row["state"] for row in dossier["rights"]} == {expected_state}
    for message in dossier["messages"]:
        assert set(message) == {"lane", "code", "en", "zh"}
        assert message["en"] and message["zh"]
