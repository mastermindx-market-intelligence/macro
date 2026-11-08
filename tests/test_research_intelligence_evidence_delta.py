from __future__ import annotations

import hashlib
import json
import stat

import pytest

from engine.research_intelligence.evidence_delta import (
    COMPARISON_KIND,
    SCHEMA,
    compare_institutional_rio_evidence,
    summary,
)
from engine.research_intelligence.schema import SCHEMA as RIO_SCHEMA
from scripts.research_intelligence_evidence_delta import _write_private_json, main


PRIOR_CLAIM = "AMD server demand grew 20% year over year as cloud orders improved."
CURRENT_CLAIM = "AMD server demand grew 35% year over year as cloud orders accelerated."
PRIOR_MECHANISM = "cloud ordering supports server demand"
CURRENT_MECHANISM = "accelerating cloud orders and supply normalization support server demand"
PRIOR_FORECAST = "Server demand should remain firm through the September quarter."
CURRENT_FORECAST = "Server demand should accelerate into the December quarter."
SECOND_CLAIM = "Supply availability remains the main constraint on near-term server shipments."
TOPIC_KEY = "AMD server demand"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rio(
    *,
    doc_id: str,
    published_at: str,
    claim: str,
    direction: str,
    conviction: str,
    mechanism: str,
    forecast: str,
    institution: str = "Fixture Research",
    entities: list[str] | None = None,
) -> dict:
    return {
        "schema": RIO_SCHEMA,
        "document": {
            "id": doc_id,
            "source_type": "institutional_research",
            "source_name": institution,
            "institution": institution,
            "desk": "Semiconductors",
            "title": f"AMD note {published_at[:10]}",
            "published_at": published_at,
            "content_sha256": _sha(f"{doc_id}:{claim}"),
        },
        "claims": [
            {
                "statement": claim,
                "evidence": [{"quote_span": claim}],
                "numbers": ["20%" if "20%" in claim else "35%"],
                "entities": entities if entities is not None else ["AMD"],
                "horizon": "current",
                "explicit": True,
            }
        ],
        "analysis": {
            "thesis": {
                "summary": f"Fixture synthesis for {doc_id}.",
                "direction": direction,
                "mechanism": [mechanism],
                "conviction": conviction,
                "support_claim_indices": [0],
            },
            "assumptions": [],
            "forecasts": [
                {
                    "statement": forecast,
                    "horizon": "quarter",
                    "confidence": conviction,
                    "support_claim_indices": [0],
                }
            ],
            "catalysts": [],
            "falsifiers": [],
            "counterarguments": [],
            "implications": [],
            "belief_delta": {"statement": "", "support_claim_indices": []},
            "consensus_relation": {"statement": "", "support_claim_indices": []},
            "uncertainties": [],
        },
        "authority": "descriptive_research_only",
    }


def _pair():
    previous = _rio(
        doc_id="fixture-2026-08-01-amd",
        published_at="2026-08-01T12:00:00+00:00",
        claim=PRIOR_CLAIM,
        direction="neutral",
        conviction="moderate",
        mechanism=PRIOR_MECHANISM,
        forecast=PRIOR_FORECAST,
    )
    current = _rio(
        doc_id="fixture-2026-09-18-amd",
        published_at="2026-09-18T12:00:00+00:00",
        claim=CURRENT_CLAIM,
        direction="bullish",
        conviction="high",
        mechanism=CURRENT_MECHANISM,
        forecast=CURRENT_FORECAST,
        entities=["AMD", "cloud"],
    )
    return previous, current


def test_delta_tracks_direction_claim_and_category_change_without_private_text():
    previous, current = _pair()
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    serialized = json.dumps(delta)

    assert delta["schema"] == SCHEMA
    assert len(delta["comparison_id"]) == 64
    assert len(delta["topic_key_sha256"]) == 64
    assert delta["pairing_authority"] == "caller_asserted_topic"
    assert delta["comparison_kind"] == COMPARISON_KIND
    assert delta["semantic_belief_authority"] == "none"
    assert delta["institution"] == "Fixture Research"
    assert delta["thesis"]["direction_before"] == "neutral"
    assert delta["thesis"]["direction_after"] == "bullish"
    assert delta["thesis"]["direction_changed"] is True
    assert len(delta["claims"]["added_sha256"]) == 1
    assert len(delta["claims"]["removed_sha256"]) == 1
    assert len(delta["categories"]["forecasts"]["added"]) == 1
    assert len(delta["categories"]["forecasts"]["removed"]) == 1
    assert delta["entities"]["added"] == ["cloud"]
    assert delta["surface_change_detected"] is True
    assert delta["surface_change_dimensions"] == [
        "thesis_direction",
        "thesis_conviction",
        "thesis_support",
        "mechanisms",
        "claims",
        "numbers",
        "entities",
        "category_forecasts",
    ]
    assert delta["text_visibility"] == "metadata_only"

    for private_text in (
        PRIOR_CLAIM,
        CURRENT_CLAIM,
        PRIOR_MECHANISM,
        CURRENT_MECHANISM,
        PRIOR_FORECAST,
        CURRENT_FORECAST,
    ):
        assert private_text not in serialized


def test_support_lineage_is_claim_hash_based_and_document_bound():
    previous, current = _pair()
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)

    prior_claim_hash = delta["claims"]["removed_sha256"][0]
    current_claim_hash = delta["claims"]["added_sha256"][0]
    assert delta["thesis"]["support_before_claim_sha256"] == [prior_claim_hash]
    assert delta["thesis"]["support_after_claim_sha256"] == [current_claim_hash]
    assert (
        delta["categories"]["forecasts"]["removed"][0]["support_claim_sha256"]
        == [prior_claim_hash]
    )
    assert (
        delta["categories"]["forecasts"]["added"][0]["support_claim_sha256"]
        == [current_claim_hash]
    )
    assert delta["previous"]["document_id"] == previous["document"]["id"]
    assert delta["current"]["document_id"] == current["document"]["id"]


def test_identical_rio_surface_with_new_document_has_no_surface_change():
    previous, _current = _pair()
    current = _rio(
        doc_id="fixture-2026-08-15-amd",
        published_at="2026-08-15T12:00:00+00:00",
        claim=PRIOR_CLAIM,
        direction="neutral",
        conviction="moderate",
        mechanism=PRIOR_MECHANISM,
        forecast=PRIOR_FORECAST,
    )
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    assert delta["surface_change_detected"] is False
    assert delta["surface_change_dimensions"] == []
    assert delta["changed_categories"] == []
    assert delta["claims"]["added_sha256"] == []
    assert delta["claims"]["removed_sha256"] == []


def test_institution_identity_mismatch_fails_closed():
    previous, current = _pair()
    current["document"]["institution"] = "Other Research"
    current["document"]["source_name"] = "Other Research"
    try:
        compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    except ValueError as exc:
        assert "institution identity" in str(exc)
    else:
        raise AssertionError("cross-institution comparison must fail closed")


def test_non_chronological_pair_and_same_document_id_fail_closed():
    previous, current = _pair()
    reversed_current = dict(current)
    reversed_current["document"] = dict(current["document"])
    reversed_current["document"]["published_at"] = "2026-07-01T12:00:00+00:00"
    try:
        compare_institutional_rio_evidence(previous, reversed_current, topic_key=TOPIC_KEY)
    except ValueError as exc:
        assert "newer" in str(exc)
    else:
        raise AssertionError("reversed chronology must fail closed")

    same_id = dict(current)
    same_id["document"] = dict(current["document"])
    same_id["document"]["id"] = previous["document"]["id"]
    try:
        compare_institutional_rio_evidence(previous, same_id, topic_key=TOPIC_KEY)
    except ValueError as exc:
        assert "distinct document ids" in str(exc)
    else:
        raise AssertionError("same-document correction is not a longitudinal pair")


def test_rights_safe_summary_contains_counts_not_private_text():
    previous, current = _pair()
    projected = summary(compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY))
    serialized = json.dumps(projected)
    assert projected["direction_before"] == "neutral"
    assert projected["direction_after"] == "bullish"
    assert projected["added_claims"] == 1
    assert projected["removed_claims"] == 1
    assert projected["changed_categories"] == ["forecasts"]
    assert "category_forecasts" in projected["surface_change_dimensions"]
    assert projected["surface_change_detected"] is True
    assert projected["text_visibility"] == "metadata_only"
    assert len(projected["comparison_id"]) == 64
    assert len(projected["topic_key_sha256"]) == 64
    assert projected["comparison_kind"] == COMPARISON_KIND
    assert projected["semantic_belief_authority"] == "none"
    assert len(projected["institution_sha256"]) == 64
    assert len(projected["previous_document_id_sha256"]) == 64
    assert len(projected["current_document_id_sha256"]) == 64
    assert "Fixture Research" not in serialized
    assert previous["document"]["id"] not in serialized
    assert current["document"]["id"] not in serialized
    assert PRIOR_CLAIM not in serialized
    assert CURRENT_CLAIM not in serialized


def test_private_delta_writer_forces_owner_only_permissions(tmp_path):
    previous, current = _pair()
    target = tmp_path / "delta.json"
    target.write_text("old", encoding="utf-8")
    target.chmod(0o644)
    _write_private_json(target, compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY))
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded["schema"] == SCHEMA


def test_rights_safe_summary_refuses_forged_text_channel():
    previous, current = _pair()
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    delta["changed_categories"] = [PRIOR_CLAIM]
    try:
        summary(delta)
    except ValueError as exc:
        assert "changed_categories" in str(exc)
    else:
        raise AssertionError("summary must reject caller-controlled text channels")


def test_same_forecast_statement_with_changed_horizon_is_modified_not_shared():
    previous, _current = _pair()
    current = _rio(
        doc_id="fixture-2026-08-15-amd",
        published_at="2026-08-15T12:00:00+00:00",
        claim=PRIOR_CLAIM,
        direction="neutral",
        conviction="moderate",
        mechanism=PRIOR_MECHANISM,
        forecast=PRIOR_FORECAST,
    )
    current["analysis"]["forecasts"][0]["horizon"] = "next year"
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    assert delta["categories"]["forecasts"]["added"] == []
    assert delta["categories"]["forecasts"]["removed"] == []
    assert len(delta["categories"]["forecasts"]["modified"]) == 1
    assert delta["categories"]["forecasts"]["shared"] == []
    assert delta["changed_categories"] == ["forecasts"]
    assert delta["surface_change_detected"] is True
    assert delta["surface_change_dimensions"] == ["category_forecasts"]


def test_thesis_support_shift_is_a_surface_change_without_semantic_authority():
    previous = _rio(
        doc_id="fixture-2026-08-01-support",
        published_at="2026-08-01T12:00:00+00:00",
        claim=PRIOR_CLAIM,
        direction="neutral",
        conviction="moderate",
        mechanism=PRIOR_MECHANISM,
        forecast=PRIOR_FORECAST,
    )
    current = _rio(
        doc_id="fixture-2026-08-15-support",
        published_at="2026-08-15T12:00:00+00:00",
        claim=PRIOR_CLAIM,
        direction="neutral",
        conviction="moderate",
        mechanism=PRIOR_MECHANISM,
        forecast=PRIOR_FORECAST,
    )
    second = {
        "statement": SECOND_CLAIM,
        "evidence": [{"quote_span": SECOND_CLAIM}],
        "numbers": [],
        "entities": [],
        "horizon": "current",
        "explicit": True,
    }
    previous["claims"].append(dict(second))
    current["claims"].append(dict(second))
    previous["analysis"]["thesis"]["support_claim_indices"] = [0]
    current["analysis"]["thesis"]["support_claim_indices"] = [1]

    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    assert delta["claims"]["added_sha256"] == []
    assert delta["claims"]["removed_sha256"] == []
    assert delta["thesis"]["direction_changed"] is False
    assert delta["thesis"]["support_changed"] is True
    assert delta["thesis"]["support_before_claim_sha256"] != delta["thesis"]["support_after_claim_sha256"]
    assert delta["surface_change_detected"] is True
    assert delta["surface_change_dimensions"] == ["thesis_support"]


def test_missing_topic_context_fails_closed():
    previous, current = _pair()
    try:
        compare_institutional_rio_evidence(previous, current, topic_key="   ")
    except ValueError as exc:
        assert "topic_key" in str(exc)
    else:
        raise AssertionError("longitudinal delta requires explicit topic context")


def test_rights_safe_summary_refuses_nonhex_digest_spoofing():
    previous, current = _pair()
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    delta["comparison_id"] = "X" * 64
    try:
        summary(delta)
    except ValueError as exc:
        assert "identity" in str(exc)
    else:
        raise AssertionError("safe summary must reject non-SHA digest fields")


def test_rights_safe_summary_refuses_inconsistent_change_flags():
    previous, current = _pair()
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    delta["surface_change_detected"] = False
    try:
        summary(delta)
    except ValueError as exc:
        assert "change_detected disagrees" in str(exc)
    else:
        raise AssertionError("safe summary must reject inconsistent change flags")


def test_rights_safe_summary_refuses_nonhash_claim_entries():
    previous, current = _pair()
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    delta["claims"]["added_sha256"] = [PRIOR_CLAIM]
    try:
        summary(delta)
    except ValueError as exc:
        assert "claim counts" in str(exc)
    else:
        raise AssertionError("safe summary must reject non-hash claim entries")


def test_repeated_same_statement_rows_preserve_multiplicity():
    previous = _rio(
        doc_id="fixture-2026-08-01-repeat",
        published_at="2026-08-01T12:00:00+00:00",
        claim=PRIOR_CLAIM,
        direction="neutral",
        conviction="moderate",
        mechanism=PRIOR_MECHANISM,
        forecast=PRIOR_FORECAST,
    )
    current = _rio(
        doc_id="fixture-2026-08-15-repeat",
        published_at="2026-08-15T12:00:00+00:00",
        claim=PRIOR_CLAIM,
        direction="neutral",
        conviction="moderate",
        mechanism=PRIOR_MECHANISM,
        forecast=PRIOR_FORECAST,
    )
    previous["claims"].append(
        {
            "statement": SECOND_CLAIM,
            "evidence": [{"quote_span": SECOND_CLAIM}],
            "numbers": [],
            "entities": [],
            "horizon": "current",
            "explicit": True,
        }
    )
    current["claims"].append(
        {
            "statement": SECOND_CLAIM,
            "evidence": [{"quote_span": SECOND_CLAIM}],
            "numbers": [],
            "entities": [],
            "horizon": "current",
            "explicit": True,
        }
    )
    duplicate_statement = "Server demand remains supported."
    previous["analysis"]["forecasts"] = [
        {
            "statement": duplicate_statement,
            "horizon": "near term",
            "confidence": "moderate",
            "support_claim_indices": [0],
        },
        {
            "statement": duplicate_statement,
            "horizon": "near term",
            "confidence": "moderate",
            "support_claim_indices": [1],
        },
    ]
    current["analysis"]["forecasts"] = [
        {
            "statement": duplicate_statement,
            "horizon": "near term",
            "confidence": "moderate",
            "support_claim_indices": [0],
        }
    ]

    delta = compare_institutional_rio_evidence(
        previous,
        current,
        topic_key=TOPIC_KEY,
    )
    forecasts = delta["categories"]["forecasts"]
    assert len(forecasts["shared"]) == 1
    assert len(forecasts["removed"]) == 1
    assert forecasts["added"] == []
    assert forecasts["modified"] == []
    assert delta["surface_change_detected"] is True
    assert "category_forecasts" in delta["surface_change_dimensions"]


def test_repeated_identical_claim_hashes_preserve_multiplicity():
    previous = _rio(
        doc_id="fixture-2026-08-01-claim-multi",
        published_at="2026-08-01T12:00:00+00:00",
        claim=PRIOR_CLAIM,
        direction="neutral",
        conviction="moderate",
        mechanism=PRIOR_MECHANISM,
        forecast=PRIOR_FORECAST,
    )
    current = _rio(
        doc_id="fixture-2026-08-15-claim-multi",
        published_at="2026-08-15T12:00:00+00:00",
        claim=PRIOR_CLAIM,
        direction="neutral",
        conviction="moderate",
        mechanism=PRIOR_MECHANISM,
        forecast=PRIOR_FORECAST,
    )
    duplicate = dict(previous["claims"][0])
    duplicate["evidence"] = [dict(previous["claims"][0]["evidence"][0])]
    duplicate["numbers"] = list(previous["claims"][0]["numbers"])
    duplicate["entities"] = list(previous["claims"][0]["entities"])
    previous["claims"].append(duplicate)

    delta = compare_institutional_rio_evidence(
        previous,
        current,
        topic_key=TOPIC_KEY,
    )
    assert len(delta["claims"]["shared_sha256"]) == 1
    assert len(delta["claims"]["removed_sha256"]) == 1
    assert delta["claims"]["added_sha256"] == []
    assert delta["claims"]["previous_count"] == 2
    assert delta["claims"]["current_count"] == 1
    assert delta["surface_change_detected"] is True
    assert "claims" in delta["surface_change_dimensions"]


def _unchanged_surface_pair():
    previous, _current = _pair()
    current = json.loads(json.dumps(previous))
    current["document"].update(
        id="fixture-2026-08-15-unchanged",
        published_at="2026-08-15T12:00:00+00:00",
        content_sha256=_sha("fixture-2026-08-15-unchanged-source"),
    )
    return previous, current


def _repeated_number_pair():
    previous, current = _unchanged_surface_pair()
    statement = "A second grounded observation records 20% server demand growth."
    row = {
        "statement": statement,
        "evidence": [{"quote_span": statement}],
        "numbers": ["20%"],
        "entities": ["AMD"],
        "horizon": "current",
        "explicit": True,
    }
    previous["claims"].append(json.loads(json.dumps(row)))
    current["claims"].append(json.loads(json.dumps(row)))
    return previous, current


def test_number_removal_from_one_of_two_unchanged_claims_is_detected():
    previous, current = _repeated_number_pair()
    current["claims"][1]["numbers"] = []

    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    assert delta["claims"]["added_sha256"] == []
    assert delta["claims"]["removed_sha256"] == []
    assert delta["numbers"]["added_sha256"] == []
    assert delta["numbers"]["removed_sha256"] == [_sha("20%")]
    assert delta["numbers"]["shared_sha256"] == [_sha("20%")]
    assert delta["surface_change_dimensions"] == ["numbers"]
    assert delta["surface_change_detected"] is True
    assert summary(delta)["surface_change_dimensions"] == ["numbers"]


def test_unchanged_repeated_numbers_remain_shared_without_a_change():
    previous, current = _repeated_number_pair()
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    assert delta["numbers"]["added_sha256"] == []
    assert delta["numbers"]["removed_sha256"] == []
    assert delta["numbers"]["shared_sha256"] == [_sha("20%"), _sha("20%")]
    assert delta["surface_change_dimensions"] == []
    assert summary(delta)["surface_change_detected"] is False


def test_raw_duplicates_removed_by_canonical_schema_are_not_recovered():
    previous, current = _unchanged_surface_pair()
    previous["claims"][0]["numbers"] = ["20%", "20%"]
    previous["analysis"]["thesis"]["mechanism"] = [PRIOR_MECHANISM, PRIOR_MECHANISM]
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    assert delta["numbers"]["shared_sha256"] == [_sha("20%")]
    assert delta["thesis"]["mechanisms"]["shared_sha256"] == [_sha(PRIOR_MECHANISM)]
    assert delta["surface_change_dimensions"] == []
    assert summary(delta)["surface_change_detected"] is False


@pytest.mark.parametrize("flag", ["direction_changed", "conviction_changed", "support_changed"])
def test_summary_rejects_missing_change_flags_instead_of_implying_false(flag):
    previous, current = _unchanged_surface_pair()
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    del delta["thesis"][flag]
    with pytest.raises(ValueError, match="flags must be boolean"):
        summary(delta)


@pytest.mark.parametrize("flag", ["direction_changed", "conviction_changed", "support_changed"])
@pytest.mark.parametrize("value", [None, 0, 1, "false"])
def test_summary_rejects_nonboolean_change_flags(flag, value):
    previous, current = _unchanged_surface_pair()
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    delta["thesis"][flag] = value
    with pytest.raises(ValueError, match="flags must be boolean"):
        summary(delta)


@pytest.mark.parametrize("flag", ["direction_changed", "conviction_changed", "support_changed"])
def test_summary_rejects_boolean_flags_that_disagree_with_retained_thesis(flag):
    previous, current = _unchanged_surface_pair()
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    delta["thesis"][flag] = True
    with pytest.raises(ValueError, match="change flag disagrees"):
        summary(delta)


@pytest.mark.parametrize("dimension", [
    "thesis_direction", "thesis_conviction", "thesis_support", "mechanisms",
    "claims", "numbers", "entities", "category_forecasts",
])
def test_summary_rejects_an_omitted_changed_payload_dimension(dimension):
    previous, current = _pair()
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    delta["surface_change_dimensions"].remove(dimension)
    if dimension == "category_forecasts":
        delta["changed_categories"] = []
    with pytest.raises(ValueError, match="dimensions disagree"):
        summary(delta)


def test_summary_rejects_false_no_change_when_retained_payload_changed():
    previous, current = _pair()
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    delta["surface_change_dimensions"] = []
    delta["changed_categories"] = []
    delta["surface_change_detected"] = False
    with pytest.raises(ValueError, match="dimensions disagree"):
        summary(delta)


@pytest.mark.parametrize("dimension", ["thesis_direction", "claims", "category_forecasts"])
def test_summary_rejects_dimensions_without_a_corresponding_payload_change(dimension):
    previous, current = _unchanged_surface_pair()
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    delta["surface_change_dimensions"] = [dimension]
    delta["surface_change_detected"] = True
    if dimension == "category_forecasts":
        delta["changed_categories"] = ["forecasts"]
    with pytest.raises(ValueError, match="dimensions disagree"):
        summary(delta)


@pytest.mark.parametrize("path", [
    ("numbers",), ("entities",), ("categories",), ("thesis", "mechanisms"),
    ("thesis", "conviction_before_sha256"), ("thesis", "support_before_claim_sha256"),
])
def test_summary_requires_retained_payload_for_change_claims(path):
    previous, current = _unchanged_surface_pair()
    delta = compare_institutional_rio_evidence(previous, current, topic_key=TOPIC_KEY)
    parent = delta
    for key in path[:-1]:
        parent = parent[key]
    del parent[path[-1]]
    with pytest.raises(ValueError):
        summary(delta)


def test_cli_keeps_private_paths_and_metadata_out_of_stdout(tmp_path, capsys):
    previous, current = _pair()
    for label, rio in (("previous", previous), ("current", current)):
        rio["document"]["institution"] = "PrivateInstitutionSentinel"
        rio["document"]["source_name"] = "PrivateInstitutionSentinel"
        rio["document"]["id"] = f"PrivateReportSentinel-{label}"
        rio["document"]["title"] = f"PrivateTitleSentinel-{label}"
    previous_path = tmp_path / "previous.json"
    current_path = tmp_path / "current.json"
    target = tmp_path / "PrivateFileSentinel.json"
    previous_path.write_text(json.dumps(previous), encoding="utf-8")
    current_path.write_text(json.dumps(current), encoding="utf-8")

    assert main([
        "--previous", str(previous_path),
        "--current", str(current_path),
        "--topic-key", "PrivateTopicSentinel",
        "--output", str(target),
    ]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    stdout = json.loads(captured.out)
    assert set(stdout) == {"state", "summary"}
    assert stdout["state"] == "ok"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    private_delta = json.loads(target.read_text(encoding="utf-8"))
    assert private_delta["institution"] == "PrivateInstitutionSentinel"
    assert private_delta["previous"]["document_id"] == "PrivateReportSentinel-previous"
    assert stdout["summary"] == summary(private_delta)
    for sentinel in (
        "PrivateInstitutionSentinel", "PrivateReportSentinel", "PrivateTitleSentinel",
        "PrivateTopicSentinel", "PrivateFileSentinel", str(tmp_path),
    ):
        assert sentinel not in captured.out
