from __future__ import annotations

import hashlib
import json
import stat

from engine.research_intelligence.evidence_delta import (
    COMPARISON_KIND,
    SCHEMA,
    compare_institutional_rio_evidence,
    summary,
)
from engine.research_intelligence.schema import SCHEMA as RIO_SCHEMA
from scripts.research_intelligence_evidence_delta import _write_private_json


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
