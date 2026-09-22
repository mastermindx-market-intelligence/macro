from __future__ import annotations

from unittest.mock import patch

import pytest

from engine.neuralweb import ask_brain as ab
from engine.neuralweb import brain_gateway as gw
from tests.test_brain_tool_economics import (
    _Block,
    _CaptureClient,
    _Resp,
    _drive_loop,
    _drive_stream,
    _root,
    _tool_block,
)


QUESTION = "Why did NVDA move after CPI and the rate selloff?"


@pytest.fixture
def quiet_grounding():
    with patch.object(gw, "_grounding_digest", return_value=""):
        with patch.object(gw, "_symbol_grounding_digest", return_value=""):
            with patch.object(gw, "_compact_earnings_call_context", return_value={}):
                yield


def test_qualified_mixed_profile_declares_two_evidence_families():
    profile = ab._question_profile(QUESTION, None)
    required = ab._fast_required_evidence_families(profile)
    assert tuple(required) == ("single_name_current", "macro_rates")
    assert "get_symbol_context" in required["single_name_current"]
    assert "get_curve_detail" in required["macro_rates"]


def test_specialist_profile_has_no_deterministic_coverage_gate():
    profile = ab._question_profile(
        "Show me historical analogues for NVDA after CPI shocks", None
    )
    assert profile.name == "ambiguous"
    assert ab._fast_required_evidence_families(profile) is None


def test_coverage_receipt_preserves_unavailable_and_stale_states():
    required = {
        "portfolio_current": ("get_portfolio_brief",),
        "options_single_name": ("read_options_entry_state",),
    }
    receipt = gw._evidence_coverage_receipt(
        required,
        [
            ("get_portfolio_brief", {"error": "upstream unavailable"}),
            (
                "read_options_entry_state",
                {"coverage_state": "STALE", "as_of": "2026-09-21T20:00:00Z"},
            ),
        ],
    )
    rows = {row["family"]: row for row in receipt["families"]}
    assert rows["portfolio_current"]["state"] == "UNAVAILABLE"
    assert rows["options_single_name"]["state"] == "STALE"


def test_fast_mixed_end_turn_without_evidence_gets_one_repair_round(quiet_grounding):
    root = _root()
    client = _CaptureClient(
        [
            _Resp([_Block("text", "Premature answer.")], "end_turn"),
            _Resp(
                [
                    _tool_block("get_symbol_context", 1, {"symbol": "NVDA"}),
                    _tool_block("get_curve_detail", 2, {}),
                ],
                "tool_use",
            ),
            _Resp([_Block("text", "Covered final answer.")], "end_turn"),
        ]
    )

    def dispatch(name, _params, *_args, **_kwargs):
        return {"ok": True, "source": name, "as_of": "2026-09-21T20:00:00Z"}

    with patch.object(gw, "_dispatch_brain_tool", side_effect=dispatch):
        answer, *_rest = _drive_loop(root, client, QUESTION)

    assert answer == "Covered final answer."
    assert len(client.create_kwargs) == 3
    gate_message = client.create_kwargs[1]["messages"][-1]["content"]
    assert "single-name" in gate_message
    assert "macro/rates" in gate_message


def test_fast_coverage_repair_is_one_shot_when_model_declines_tools(quiet_grounding):
    root = _root()
    client = _CaptureClient(
        [
            _Resp([_Block("text", "Premature answer.")], "end_turn"),
            _Resp([_Block("text", "Final answer with disclosed gap.")], "end_turn"),
        ]
    )
    answer, *_rest = _drive_loop(root, client, QUESTION)
    assert answer == "Final answer with disclosed gap."
    assert len(client.create_kwargs) == 2


def test_streaming_fast_coverage_repair_retracts_premature_text(quiet_grounding):
    root = _root()
    client = _CaptureClient(
        [
            _Resp([_Block("text", "Premature answer.")], "end_turn"),
            _Resp(
                [
                    _tool_block("get_symbol_context", 1, {"symbol": "NVDA"}),
                    _tool_block("get_curve_detail", 2, {}),
                ],
                "tool_use",
            ),
            _Resp([_Block("text", "Covered final answer.")], "end_turn"),
        ]
    )

    def dispatch(name, _params, *_args, **_kwargs):
        return {"ok": True, "source": name, "as_of": "2026-09-21T20:00:00Z"}

    with patch.object(gw, "_dispatch_brain_tool", side_effect=dispatch):
        events = _drive_stream(root, client, QUESTION)

    assert len(client.stream_kwargs) == 3
    visible = "".join(e.get("text", "") for e in events if e.get("type") == "delta")
    assert "Premature answer." not in visible
    assert "Covered final answer." in visible


def test_contradiction_read_is_metadata_not_a_false_coverage_witness():
    required = {"options_single_name": ("read_options_entry_state",)}
    receipt = gw._evidence_coverage_receipt(required, [("list_options_contradictions", {"contradictions": [{"kind": "skew_vs_gamma"}]})])
    row = receipt["families"][0]
    assert row["state"] == "NOT_COVERED"
    assert row["contradicted"] is True


def test_mixed_fresh_and_stale_witnesses_keep_stale_presence_metadata():
    required = {"macro_rates": ("read_world_state", "get_curve_detail")}
    receipt = gw._evidence_coverage_receipt(required, [("read_world_state", {"ok": True, "as_of": "2026-09-21T21:00:00Z"}), ("get_curve_detail", {"coverage_state": "STALE", "as_of": "2026-09-19T21:00:00Z"})])
    row = receipt["families"][0]
    assert row["state"] == "AVAILABLE"
    assert row["freshness"] == "STALE_PRESENT"
    assert row["as_of"] == ["2026-09-21T21:00:00Z", "2026-09-19T21:00:00Z"]
