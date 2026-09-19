from __future__ import annotations

import hashlib
import json
import stat

from engine.research_intelligence.belief_delta import (
    SCHEMA,
    compare_institutional_rio,
    summary,
)
from engine.research_intelligence.schema import SCHEMA as RIO_SCHEMA
from scripts.research_intelligence_belief_delta import _write_private_json


PRIOR_CLAIM = "AMD server demand grew 20% year over year as cloud orders improved."
CURRENT_CLAIM = "AMD server demand grew 35% year over year as cloud orders accelerated."
PRIOR_MECHANISM = "cloud ordering supports server demand"
CURRENT_MECHANISM = "accelerating cloud orders and supply normalization support server demand"
PRIOR_FORECAST = "Server demand should remain firm through the September quarter."
CURRENT_FORECAST = "Server demand should accelerate into the December quarter."


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
    delta = compare_institutional_rio(previous, current)
    serialized = json.dumps(delta)

    assert delta["schema"] == SCHEMA
    assert delta["institution"] == "Fixture Research"
    assert delta["thesis"]["direction_before"] == "neutral"
    assert delta["thesis"]["direction_after"] == "bullish"
    assert delta["thesis"]["direction_changed"] is True
    assert len(delta["claims"]["added_sha256"]) == 1
    assert len(delta["claims"]["removed_sha256"]) == 1
    assert len(delta["categories"]["forecasts"]["added"]) == 1
    assert len(delta["categories"]["forecasts"]["removed"]) == 1
    assert delta["entities"]["added"] == ["cloud"]
    assert delta["material_change"] is True
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
    delta = compare_institutional_rio(previous, current)

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


def test_same_belief_with_new_document_is_not_material_change():
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
    delta = compare_institutional_rio(previous, current)
    assert delta["material_change"] is False
    assert delta["changed_categories"] == []
    assert delta["claims"]["added_sha256"] == []
    assert delta["claims"]["removed_sha256"] == []


def test_institution_identity_mismatch_fails_closed():
    previous, current = _pair()
    current["document"]["institution"] = "Other Research"
    current["document"]["source_name"] = "Other Research"
    try:
        compare_institutional_rio(previous, current)
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
        compare_institutional_rio(previous, reversed_current)
    except ValueError as exc:
        assert "newer" in str(exc)
    else:
        raise AssertionError("reversed chronology must fail closed")

    same_id = dict(current)
    same_id["document"] = dict(current["document"])
    same_id["document"]["id"] = previous["document"]["id"]
    try:
        compare_institutional_rio(previous, same_id)
    except ValueError as exc:
        assert "distinct document ids" in str(exc)
    else:
        raise AssertionError("same-document correction is not longitudinal memory")


def test_rights_safe_summary_contains_counts_not_private_text():
    previous, current = _pair()
    projected = summary(compare_institutional_rio(previous, current))
    serialized = json.dumps(projected)
    assert projected["direction_before"] == "neutral"
    assert projected["direction_after"] == "bullish"
    assert projected["added_claims"] == 1
    assert projected["removed_claims"] == 1
    assert projected["changed_categories"] == ["forecasts"]
    assert projected["text_visibility"] == "metadata_only"
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
    _write_private_json(target, compare_institutional_rio(previous, current))
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded["schema"] == SCHEMA


def test_rights_safe_summary_refuses_forged_text_channel():
    previous, current = _pair()
    delta = compare_institutional_rio(previous, current)
    delta["changed_categories"] = [PRIOR_CLAIM]
    try:
        summary(delta)
    except ValueError as exc:
        assert "changed_categories" in str(exc)
    else:
        raise AssertionError("summary must reject caller-controlled text channels")
