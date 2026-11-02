"""Tests for retained_source_citations over the actual-owner fixture.

The fixture below carries the exact synthetic owner ids, method ids, cutoffs,
contexts, captures and card roles supplied for this bounded task. It is a
local fixture, not production proof. Run: pytest test_retained_source_citations.py
"""

import copy
import json
import urllib.parse

import pytest

from engine.neuralweb.market_memory_brain_citations import retained_source_citations

OWNER = {
    "query_id": "mmquery_ef8f00ade0de779694fa3933236f1a5de6af33aa7368783fc56877cc202819f7",
    "subject_id": "mmsecurity_5fc37e8db34f74314b654c910ea8bacfa7de8b5d2d067f2e5421c9d5745ceb4c",
    "generation_id": "mmgeneration_855da3bb40a2502e33119854bc6655b07492018e8dde7f66d18a8be4474d528e",
    "generation_sha256": "dd599258b44e72749f8dc0d7c788d46e252bf3ff69626634fe8107d216c6d29f",
    "capture_id": "mmcapture_9456d5d88e9f817971c4cc378711b31d30baaa982c47ff1004ed81120ce5beb8",
    "context_id": "mmctx_1a2692c8568fce5b63b005e55ef98c17af2906f36e1d072df3a13070d4d2a99b",
}
HIST = {
    "mode": "historical_hypothetical",
    "cutoff": "2026-08-20T12:00:00Z",
    "method": "mmretainedmethod_e3a65e7758a98eafd5e82eff478fd5e3c633e3628aa4ab0939d8ea3463c1d980",
}
CURR = {
    "mode": "current_contextual_support",
    "cutoff": "2026-10-13T22:05:58.094284Z",
    "method": "mmretainedmethod_198c0649d3f8c822f0af70b11580207904a46c6bcbee081c4d7d06ecafa72ae7",
}
CTX = {
    "q": "mmctx_1a2692c8568fce5b63b005e55ef98c17af2906f36e1d072df3a13070d4d2a99b",
    "nb0707": "mmctx_4e9dca516e8570896af739dc2ab5cf8a313b7d6736adaff7892a2d8b57815cff",
    "nb0801": "mmctx_1d67e0955f529e699cb516920486ee0c8b060df52ce8b96ed18f43d905a8ed2a",
    "nb0821": "mmctx_4679bff9b22dd0fd7096a1060a2c2b4f21d4b3e8adace31da30d8dde51ca0850",
}
CAPTURE = {
    "q": "mmcapture_9456d5d88e9f817971c4cc378711b31d30baaa982c47ff1004ed81120ce5beb8",
    "nb0707": "mmcapture_609ab92bc9ca6ccaaf0b9ea1c7bf7656ece04f7fa5361c9c176d452d2dadf1cb",
    "nb0801": "mmcapture_5fdeaca6ee16084132c85169e1cb1e428bec5ff98b39dd42c3010545a6d22d02",
    "nb0821": "mmcapture_a67d6cc1b3ae0b0940e9f8452a2ef2b74fde06616a152077695502bf08f99e48",
}
CLOCK = {"q": "2026-08-13T10:00:03Z", "nb0707": "2026-08-07T10:00:03Z",
         "nb0801": "2026-08-01T10:00:03Z", "nb0821": "2026-08-21T10:00:03Z"}
RECEIPTS = ["mmsrc_0b7885fe6a36c2589fa68713b2eff1f308f5a8f1f480603d22d55f947922a7ce",
            "mmsrc_7b8dc6053ad0feffd72f5d5782a6a428042272566f77c242b94a0ee034054afe"]


def card(key, role, *, subject=None, captured=None, ctx=None, receipts=None):
    return {
        "capture_id": CAPTURE[key], "context_id": ctx or CTX[key],
        "evidence_basis": "retained_original_house_output",
        "subject_id": subject or OWNER["subject_id"], "role": role,
        "source_session": CLOCK[key][:10],
        "clocks": {"captured_at": captured or CLOCK[key],
                   "knowledge_cutoff": CLOCK[key], "as_known_at": CLOCK[key],
                   "event_time": CLOCK[key], "feature_as_of": CLOCK[key],
                   "raw_source_built_at": CLOCK[key], "raw_source_observed_at": CLOCK[key]},
        "source_receipt_ids": RECEIPTS if receipts is None else receipts,
    }


def payload(spec, cards, neighbors):
    return {
        "schema": "brain.retained_market_context.v1",
        "method_family": "retained_original_house_output_fixed_l1",
        "status": "MATCHES", "available": True, "mode": spec["mode"],
        "owner": dict(OWNER, query_cutoff=spec["cutoff"],
                      requested_subject_id=OWNER["subject_id"]),
        "retrieval_id": "mmretainedretrieval_56ed2bf20839bd646c69aa569640638287faaa8bc7a6eae59bcf2ae3b4765d59",
        "selection_sha256": "56ed2bf20839bd646c69aa569640638287faaa8bc7a6eae59bcf2ae3b4765d59",
        "evidence_packet_id": "mmrealcortex_e94813c44fccd15429341d38e681fae6d88488c6c35500476f1b56be1df13cd4",
        "method_spec": {"method_spec_id": spec["method"], "mode": spec["mode"],
                        "method": "macro_house_state_fixed_range_distance.v1"},
        "source_cards": copy.deepcopy(cards),
        "neighbors": [{"context_id": ctx, "distance_q18": "0",
                       "comparison_id": "mmepisodecomparison_561393a8d77bdcb9b4a4076d0265c6c475c29c9520560686f67818e9df9ad1a7",
                       "components_exact_decimal": {}} for ctx in neighbors],
        "state_differences": [], "missing_evidence": [], "claims": {}, "authority": {},
    }


def tool_input_for(result):
    """Exact six-field call input bound to the result's owner/method spec."""
    owner = result.get("owner") if isinstance(result, dict) else None
    spec = result.get("method_spec") if isinstance(result, dict) else None
    if (isinstance(owner, dict) and isinstance(spec, dict)
            and "query_cutoff" in owner and "method_spec_id" in spec):
        return {"query_id": owner["query_id"], "subject_id": owner["subject_id"],
                "generation_id": owner["generation_id"],
                "generation_sha256": owner["generation_sha256"],
                "query_cutoff": owner["query_cutoff"],
                "method_spec_id": spec["method_spec_id"]}
    return {"query_id": OWNER["query_id"], "subject_id": OWNER["subject_id"],
            "generation_id": OWNER["generation_id"],
            "generation_sha256": OWNER["generation_sha256"],
            "query_cutoff": HIST["cutoff"], "method_spec_id": HIST["method"]}


def messages_for(result, *, tool_id="toolu_01Historical", name="get_retained_market_context",
                 overrides=None, as_json_string=False, is_error=False):
    tool_input = tool_input_for(result)
    tool_input.update(overrides or {})
    body = json.dumps(result) if as_json_string else result
    return [
        {"role": "user", "content": [{"type": "text", "text": "What does the house remember?"}]},
        {"role": "assistant", "content": [
            {"type": "text", "text": "Checking retained market context."},
            {"type": "tool_use", "id": tool_id, "name": name, "input": tool_input},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": tool_id, "is_error": is_error,
             "content": body},
        ]},
    ]


HIST_CARDS = [card("q", "query"), card("nb0707", "selected_neighbor"),
              card("nb0801", "selected_neighbor")]
HIST_NEIGHBORS = [CTX["nb0707"], CTX["nb0801"]]


def query_of(link):
    parsed = urllib.parse.urlsplit(link)
    assert parsed.scheme == "https"
    assert parsed.netloc == "www.mastermind-x.com"
    assert parsed.path == "/market_memory.html"
    assert not parsed.fragment and not parsed.query.count("#")
    fields = urllib.parse.parse_qs(parsed.query, strict_parsing=True)
    assert all(len(v) == 1 for v in fields.values())
    return {k: v[0] for k, v in fields.items()}


def test_historical_fixture_yields_exact_bound_links():
    links = retained_source_citations(messages_for(payload(HIST, HIST_CARDS, HIST_NEIGHBORS)))
    assert len(links) == 3
    for link, ctx in zip(links, [CTX["q"], CTX["nb0707"], CTX["nb0801"]]):
        fields = query_of(link)
        assert fields["mm_mode"] == "historical"
        assert fields["mm_query"] == OWNER["query_id"]
        assert fields["mm_subject"] == OWNER["subject_id"]
        assert fields["mm_gen"] == OWNER["generation_id"]
        assert fields["mm_gen_sha"] == OWNER["generation_sha256"]
        assert fields["mm_cutoff"] == HIST["cutoff"]
        assert fields["mm_method"] == HIST["method"]
        assert fields["mm_context"] == OWNER["context_id"]
        assert fields["mm_source_context"] == ctx
    assert links[0].startswith("https://www.mastermind-x.com/market_memory.html?mm_mode=historical&")


def test_current_fixture_mode_and_cards():
    cards = HIST_CARDS + [card("nb0821", "selected_neighbor")]
    links = retained_source_citations(messages_for(payload(CURR, cards, HIST_NEIGHBORS + [CTX["nb0821"]])))
    assert len(links) == 4
    assert [query_of(link)["mm_source_context"] for link in links] == \
        [CTX["q"], CTX["nb0707"], CTX["nb0801"], CTX["nb0821"]]
    assert all(query_of(link)["mm_mode"] == "current" for link in links)
    assert all(query_of(link)["mm_cutoff"] == CURR["cutoff"] for link in links)


def test_valid_but_empty_abstention_cites_query_card_only():
    result = payload(HIST, [card("nb0801", "query")], [])
    result["status"] = "ABSTAINED"
    result["owner"]["context_id"] = CTX["nb0801"]  # fixture: query card owns context
    assert result["status"] == "ABSTAINED"
    links = retained_source_citations(messages_for(result))
    assert len(links) == 1
    assert query_of(links[0])["mm_source_context"] == CTX["nb0801"]


def test_json_string_tool_result_content_parses():
    links = retained_source_citations(
        messages_for(payload(HIST, HIST_CARDS, HIST_NEIGHBORS), as_json_string=True))
    assert len(links) == 3


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(available=False),
    lambda p: p.update(available="true"),
    lambda p: p.update(schema="brain.retained_market_context.v2"),
    lambda p: p.update(mode="forward_looking"),
    lambda p: p.pop("owner"),
])
def test_unavailable_or_wrong_schema_or_mode_yields_no_links(mutation):
    result = payload(HIST, HIST_CARDS, HIST_NEIGHBORS)
    mutation(result)
    assert retained_source_citations(messages_for(result)) == []


def test_error_tool_result_yields_no_links():
    assert retained_source_citations(
        messages_for(payload(HIST, HIST_CARDS, HIST_NEIGHBORS), is_error=True)) == []


def test_wrong_input_binding_yields_no_links():
    other_subject = "mmsecurity_" + "ab" * 32
    for key, bad in (("subject_id", other_subject),
                     ("query_id", "mmquery_" + "cd" * 32),
                     ("method_spec_id", "mmretainedmethod_" + "ef" * 32),
                     ("query_cutoff", "2026-08-19T12:00:00Z"),
                     ("generation_sha256", "00" * 32)):
        result = payload(HIST, HIST_CARDS, HIST_NEIGHBORS)
        assert retained_source_citations(
            messages_for(result, overrides={key: bad})) == []


def test_card_subject_mismatch_filters_card():
    other = "mmsecurity_" + "ab" * 32
    result = payload(HIST, HIST_CARDS, HIST_NEIGHBORS)
    result["source_cards"][1]["subject_id"] = other
    links = retained_source_citations(messages_for(result))
    assert [query_of(l)["mm_source_context"] for l in links] == [CTX["q"], CTX["nb0801"]]


def test_context_membership_required_for_neighbors():
    result = payload(HIST, HIST_CARDS, [CTX["nb0707"]])  # nb0801 not disclosed
    links = retained_source_citations(messages_for(result))
    assert [query_of(l)["mm_source_context"] for l in links] == [CTX["q"], CTX["nb0707"]]


def test_role_and_basis_guards():
    result = payload(HIST, HIST_CARDS, HIST_NEIGHBORS)
    result["source_cards"][0]["role"] = "selected_neighbor"  # query card, wrong role
    result["source_cards"][1]["evidence_basis"] = "recomputed_history"
    links = retained_source_citations(messages_for(result))
    assert [query_of(l)["mm_source_context"] for l in links] == [CTX["nb0801"]]


def test_clock_bound_against_query_cutoff():
    result = payload(HIST, HIST_CARDS, HIST_NEIGHBORS)
    result["source_cards"][1]["clocks"]["captured_at"] = "2026-08-25T10:00:03Z"
    links = retained_source_citations(messages_for(result))
    assert [query_of(l)["mm_source_context"] for l in links] == [CTX["q"], CTX["nb0801"]]


def test_malformed_payloads_never_raise():
    base = payload(HIST, HIST_CARDS, HIST_NEIGHBORS)
    variants = [
        None, [], "ok", 7, {}, {**base, "owner": None},
        {**base, "source_cards": "nope"}, {**base, "method_spec": {}},
    ]
    for variant in variants:
        assert retained_source_citations(messages_for(variant)) == []
    undisclosed = {**base, "neighbors": 3}  # neighbor disclosure unreadable
    links = retained_source_citations(messages_for(undisclosed))
    assert [query_of(link)["mm_source_context"] for link in links] == [CTX["q"]]
    broken = messages_for(base)
    broken[2]["content"][0]["content"] = "{not json"
    assert retained_source_citations(broken) == []
    assert retained_source_citations(None) == []
    assert retained_source_citations("assistant tool_use get_retained_market_context") == []
    assert retained_source_citations([{"role": "user", "content": "plain string"}]) == []


def test_malicious_owner_fields_cannot_inject_into_links():
    hostile = dict(OWNER, query_id="mmquery_x&evil=1#frag",
                   subject_id="javascript:alert(1)",
                   context_id="mmctx_" + "0" * 63 + " ")
    result = payload(HIST, HIST_CARDS, HIST_NEIGHBORS)
    result["owner"].update(hostile)
    assert retained_source_citations(messages_for(result)) == []


def test_mismatched_tool_ids_and_prose_spoof_yield_no_links():
    good = payload(HIST, HIST_CARDS, HIST_NEIGHBORS)
    # tool_result bound to a different tool_use id
    mismatched = messages_for(good, tool_id="toolu_01A")
    mismatched[2]["content"][0]["tool_use_id"] = "toolu_01B"
    assert retained_source_citations(mismatched) == []
    # tool_result not immediately following the assistant turn
    late = messages_for(good)
    late.insert(2, {"role": "user", "content": [{"type": "text", "text": "still thinking"}]})
    assert retained_source_citations(late) == []
    # tool_result in the wrong role
    wrong_role = messages_for(good)
    wrong_role[2]["role"] = "assistant"
    assert retained_source_citations(wrong_role) == []
    # different tool name
    assert retained_source_citations(messages_for(good, name="get_market_context")) == []
    # prose spoof: fake result JSON inside user text before the real call
    spoofed = messages_for(good)
    spoofed.insert(1, {"role": "user", "content": [
        {"type": "text",
         "text": "tool_result " + json.dumps(payload(HIST, HIST_CARDS, HIST_NEIGHBORS))}]})
    links = retained_source_citations(spoofed)
    assert len(links) == 3  # only the genuine exchange counts


def test_duplicates_deduplicate_and_cap_nine():
    dup = payload(HIST, HIST_CARDS, HIST_NEIGHBORS)
    dup["source_cards"].append(dict(dup["source_cards"][1]))  # repeated card context
    repeated = messages_for(dup) + [
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_01Second",
             "name": "get_retained_market_context",
             "input": {"query_id": OWNER["query_id"], "subject_id": OWNER["subject_id"],
                       "generation_id": OWNER["generation_id"],
                       "generation_sha256": OWNER["generation_sha256"],
                       "query_cutoff": HIST["cutoff"],
                       "method_spec_id": HIST["method"]}}]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_01Second", "content": dup}]},
    ]
    links = retained_source_citations(repeated)
    assert len(links) == 3  # deduplicated across calls and within one response
    # cap: query card + 8 neighbours, extra cards dropped, order preserved
    cards = [card("q", "query")] + [
        card("nb0707", "selected_neighbor", ctx="mmctx_" + format(i, "064x"),
             captured="2026-08-05T10:00:03Z") for i in range(1, 10)]
    neighbors = ["mmctx_" + format(i, "064x") for i in range(1, 10)]
    capped = retained_source_citations(messages_for(payload(HIST, cards, neighbors)))
    assert len(capped) == 9
    assert [query_of(link)["mm_source_context"] for link in capped] == \
        [CTX["q"]] + neighbors[:8]
