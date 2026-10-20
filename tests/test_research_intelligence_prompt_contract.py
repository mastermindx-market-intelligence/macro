"""Synthetic pins for the versioned prompt's strict schema vocabulary."""
import hashlib
import json
from types import SimpleNamespace

import pytest

from engine.research_intelligence import extractor, schema, vault_head


BODY = "The company reported revenue growth of 12% during the quarter."
DOCUMENT = {"id": "synthetic-direction", "source_type": "institutional_research"}


def _rio(direction):
    identity = extractor._identity(DOCUMENT, BODY)
    obj = extractor._output_shape(identity)
    obj["claims"] = [{
        "statement": BODY, "evidence": [{"quote_span": BODY}],
        "numbers": ["12%"], "entities": [], "horizon": "", "explicit": True,
    }]
    obj["analysis"]["thesis"].update(
        summary="The report describes improving sales performance.",
        direction=direction,
    )
    return obj


def _parse(obj):
    return extractor.parse_model_output(
        json.dumps(obj), expected_document_id=DOCUMENT["id"],
        expected_document=extractor._identity(DOCUMENT, BODY), source_body=BODY,
    )


def test_prompt_advertises_exact_canonical_vocabulary():
    values = schema.thesis_direction_values()
    assert values == tuple(sorted(schema._DIRECTIONS))
    system, _ = extractor.build_prompt(DOCUMENT, BODY)
    fragment = system.split("analysis.thesis.direction MUST be exactly one of ", 1)[1]
    advertised = json.loads(fragment.split(";", 1)[0])
    assert advertised == list(values)
    assert "never invent another direction label" in system


def test_accessor_has_no_independent_enum(monkeypatch):
    # A canonical-owner change is reflected by the accessor, not copied values.
    monkeypatch.setattr(schema, "_DIRECTIONS", {"synthetic-only"})
    assert schema.thesis_direction_values() == ("synthetic-only",)


def test_observed_unsupported_direction_still_rejected():
    with pytest.raises(ValueError, match="unsupported analysis.thesis.direction"):
        _parse(_rio("cautiously constructive"))


@pytest.mark.parametrize("direction", schema.thesis_direction_values())
def test_each_canonical_direction_retains_grounding(direction):
    result = _parse(_rio(direction))
    assert result["analysis"]["thesis"]["direction"] == direction
    assert result["claims"][0]["evidence"] == [{"quote_span": BODY}]
    assert result["analysis"]["thesis"]["support_claim_indices"] == [0]


def test_valid_direction_does_not_bypass_identity_or_grounding():
    wrong = _rio("unclear")
    wrong["document"]["id"] = "another-document"
    with pytest.raises(ValueError):
        _parse(wrong)
    ungrounded = _rio("unclear")
    ungrounded["claims"][0]["evidence"] = [{"quote_span": "An invented source sentence."}]
    with pytest.raises(ValueError, match="no source claim survived"):
        _parse(ungrounded)


def test_new_prompt_identity_rejects_retained_v1_receipt():
    assert extractor.PROMPT_VERSION == "mastermind.research_intelligence.extractor.v3"
    current_hash = hashlib.sha256(
        (extractor.PROMPT_VERSION + "\n" + extractor.SYSTEM_PROMPT).encode()
    ).hexdigest()
    assert current_hash == vault_head._current_prompt_contract_sha256()
    assert current_hash != "b64a32853c56ce5d6a67309e751397b732b25ee5006982e2d54f159180327656"
    item = {"id": DOCUMENT["id"], "institution": "Synthetic", "title": "Synthetic"}
    text_sha = hashlib.sha256(BODY.encode()).hexdigest()
    receipt = {
        "requested_model": "synthetic-model", "prompt_version": extractor.PROMPT_VERSION,
        "prompt_contract_sha256": current_hash,
        "document": vault_head._expected_receipt_document(item, extracted_text_sha256=text_sha),
    }
    latest = SimpleNamespace(receipt=receipt, source_content_sha256=text_sha)
    kwargs = {"extracted_text_sha256": text_sha, "requested_model": "synthetic-model"}
    assert vault_head._latest_is_current(latest, item, **kwargs)
    receipt["prompt_version"] = "mastermind.research_intelligence.extractor.v1"
    assert not vault_head._latest_is_current(latest, item, **kwargs)
    receipt["prompt_version"] = "mastermind.research_intelligence.extractor.v2"
    assert not vault_head._latest_is_current(latest, item, **kwargs)
    receipt["prompt_version"] = extractor.PROMPT_VERSION
    receipt["prompt_contract_sha256"] = "b64a32853c56ce5d6a67309e751397b732b25ee5006982e2d54f159180327656"
    assert not vault_head._latest_is_current(latest, item, **kwargs)
