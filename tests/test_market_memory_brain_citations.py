"""Real gateway citation boundary over the existing actual-owner wire fixture."""
import copy
import subprocess
import shutil
import pytest
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from engine.neuralweb.brain_gateway import _extract_citations_brain
from engine.codex_provider import _ToolUseBlock


def _messages():
    fixture = json.loads((Path(__file__).parent / "fixtures/market_memory_retained_owner_wire.json").read_text())
    wire = fixture["examples"]["retained_historical"]
    return [
        {"role": "assistant", "content": [{"type": "tool_use", "id": "retained_actual_owner", "name": "get_retained_market_context", "input": wire["request"]["query"]}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "retained_actual_owner", "content": json.dumps(wire["body"])}]},
    ], wire["body"]


def test_gateway_links_each_returned_original_source_to_exact_query():
    messages, body = _messages()
    citations = _extract_citations_brain(messages)
    links = [c for c in citations if c.startswith("https://www.mastermind-x.com/market_memory.html?")]
    assert len(links) == len(body["source_cards"])
    for link, card in zip(links, body["source_cards"], strict=True):
        params = parse_qs(urlsplit(link).query, strict_parsing=True)
        assert params["mm_query"] == [body["owner"]["query_id"]]
        assert params["mm_gen"] == [body["owner"]["generation_id"]]
        assert params["mm_gen_sha"] == [body["owner"]["generation_sha256"]]
        assert params["mm_method"] == [body["method_spec"]["method_spec_id"]]
        assert params["mm_source_context"] == [card["context_id"]]
        assert params["mm_context"] == [body["owner"]["context_id"]]
        assert params["mm_cutoff"] == [body["owner"]["query_cutoff"]]


def _sdk_messages():
    messages, body = _messages()
    # Both gateway loops append resp.content directly. The installed Codex
    # adapter returns these dataclass blocks, not the serialized test form.
    messages[0]["content"] = [_ToolUseBlock(**messages[0]["content"][0])]
    return messages, body


def test_gateway_cites_actual_codex_sdk_blocks_without_serializing_the_conversation():
    serialized, body = _messages()
    messages, _ = _sdk_messages()
    expected = _extract_citations_brain(serialized)
    assert len(expected) == len(body["source_cards"])
    assert _extract_citations_brain(messages) == expected


@pytest.mark.parametrize("change", ["duplicate_sdk", "duplicate_dict", "wrong_name",
                                   "wrong_input", "wrong_role", "unmatched_result"])
def test_sdk_citations_preserve_exact_call_result_binding(change):
    messages, _ = _sdk_messages()
    block = messages[0]["content"][0]
    if change == "duplicate_sdk":
        messages[0]["content"].append(copy.deepcopy(block))
    elif change == "duplicate_dict":
        messages[0]["content"].append(vars(block).copy())
    elif change == "wrong_name":
        block.name = "get_market_analogues"
    elif change == "wrong_input":
        block.input["query_id"] = "mmquery_" + "0" * 64
    elif change == "wrong_role":
        messages[0]["role"] = "user"
    else:
        messages[1]["content"][0]["tool_use_id"] = "different_call"
    assert _extract_citations_brain(messages) == []


def test_gateway_does_not_promote_answer_prose_or_unmatched_result_to_citation():
    messages, _ = _messages()
    assert _extract_citations_brain(messages[1:]) == []
    forged = copy.deepcopy(messages)
    forged[1]["role"] = "assistant"
    assert _extract_citations_brain(forged) == []


@pytest.mark.parametrize("limit", [None, 1, 8])
def test_gateway_accepts_the_incumbent_optional_limit_contract(limit):
    messages, body = _messages()
    query = messages[0]["content"][0]["input"]
    if limit is None:
        query.pop("limit")
    else:
        query["limit"] = limit
    assert len(_extract_citations_brain(messages)) == len(body["source_cards"])


@pytest.mark.parametrize("limit", [0, 9, True, "8"])
def test_gateway_refuses_invalid_optional_limit(limit):
    messages, _ = _messages()
    messages[0]["content"][0]["input"]["limit"] = limit
    assert _extract_citations_brain(messages) == []


@pytest.mark.parametrize("message_index", [0, 1])
def test_gateway_refuses_ambiguous_duplicate_tool_identity(message_index):
    messages, _ = _messages()
    messages[message_index]["content"].append(copy.deepcopy(messages[message_index]["content"][0]))
    assert _extract_citations_brain(messages) == []


@pytest.mark.parametrize("field,value", [("mode", []), ("owner", None), ("source_cards", {}), ("method_spec", [])])
def test_gateway_malformed_result_cannot_break_the_answer(field, value):
    messages, body = _messages()
    body[field] = value
    messages[1]["content"][0]["content"] = json.dumps(body)
    assert _extract_citations_brain(messages) == []


@pytest.mark.parametrize("clock", ["captured_at", "knowledge_cutoff", "as_known_at"])
def test_gateway_drops_card_with_a_clock_after_exact_cutoff(clock):
    messages, body = _messages()
    body["source_cards"][0]["clocks"][clock] = "2099-01-01T00:00:00Z"
    messages[1]["content"][0]["content"] = json.dumps(body)
    links = _extract_citations_brain(messages)
    assert len(links) == len(body["source_cards"]) - 1


def test_actual_brain_javascript_citation_contract():
    node = shutil.which("node")
    assert node, "Node is required for the actual Brain citation parser contract"
    subprocess.run([node, str(Path(__file__).parent / "js/market_memory_brain_citations.test.cjs")], check=True)
