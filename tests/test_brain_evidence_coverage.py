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


def test_fast_family_schema_drift_fails_open(monkeypatch):
    profile = ab._question_profile(QUESTION, None)
    monkeypatch.setitem(
        ab._FAST_VISIBLE_PROFILE_COMPOSITIONS,
        profile.name,
        ("single_name_current", "future_family"),
    )
    assert ab._fast_required_evidence_families(profile) is None
    assert ab._fast_visible_tool_names(profile) is None


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



def test_available_witness_preserves_all_adverse_sibling_conditions():
    required = {
        "macro_rates": (
            "read_world_state",
            "get_curve_detail",
            "read_inflation_intelligence",
            "read_liquidity_plumbing",
            "read_mechanism_pathways",
        ),
    }
    receipt = gw._evidence_coverage_receipt(
        required,
        [
            ("read_world_state", {"ok": True}),
            ("get_curve_detail", {"status": "conflicted"}),
            ("read_inflation_intelligence", {"status": "partial"}),
            ("read_liquidity_plumbing", {"status": "not_applicable"}),
            ("read_mechanism_pathways", {"error": "upstream unavailable"}),
        ],
    )
    row = receipt["families"][0]
    assert row["state"] == "AVAILABLE"
    assert row["conditions"] == [
        "CONFLICTED",
        "PARTIAL",
        "NOT_APPLICABLE",
        "UNAVAILABLE",
    ]
    assert row["contradicted"] is True
    synth = gw._evidence_coverage_synthesis_message(receipt)
    for condition in row["conditions"]:
        assert f"{condition}_PRESENT" in synth


def test_compound_producer_state_preserves_each_condition():
    required = {"macro_rates": ("get_curve_detail",)}
    receipt = gw._evidence_coverage_receipt(
        required,
        [("get_curve_detail", {"status": "partial_stale_conflict"})],
    )
    row = receipt["families"][0]
    assert row["state"] == "CONFLICTED"
    assert row["freshness"] == "STALE_PRESENT"
    assert row["conditions"] == ["CONFLICTED", "PARTIAL", "STALE"]
    assert row["contradicted"] is True


def test_negated_status_tokens_do_not_create_false_adverse_conditions():
    required = {"macro_rates": ("get_curve_detail",)}
    receipt = gw._evidence_coverage_receipt(
        required,
        [(
            "get_curve_detail",
            {"status": "no_conflict_not_stale_no_partial_gaps", "error": "no_error"},
        )],
    )
    row = receipt["families"][0]
    assert row["state"] == "AVAILABLE"
    assert row["conditions"] == []
    assert row["freshness"] == "CURRENT_OR_UNSPECIFIED"


def test_conflicted_precedence_is_consistent_across_sibling_witnesses():
    required = {"macro_rates": ("read_world_state", "get_curve_detail")}
    receipt = gw._evidence_coverage_receipt(
        required,
        [
            ("read_world_state", {"status": "partial"}),
            ("get_curve_detail", {"status": "conflicted"}),
        ],
    )
    row = receipt["families"][0]
    assert row["state"] == "CONFLICTED"
    assert row["conditions"] == ["CONFLICTED", "PARTIAL"]


def test_empty_read_payload_is_available_not_missing():
    required = {"macro_rates": ("get_curve_detail",)}
    receipt = gw._evidence_coverage_receipt(
        required,
        [("get_curve_detail", {})],
    )
    assert receipt["families"][0]["state"] == "AVAILABLE"


def test_nonstream_repair_cannot_resurrect_rejected_text_on_textless_end_turn(quiet_grounding):
    root = _root()
    client = _CaptureClient(
        [
            _Resp([_Block("text", "Premature answer.")], "end_turn"),
            _Resp([_Block("thinking", "")], "end_turn"),
        ]
    )
    answer, *_rest = _drive_loop(root, client, QUESTION)
    assert len(client.create_kwargs) == 2
    assert answer
    assert "Evidence status" in answer
    assert "not covered" in answer
    assert "Premature answer." not in answer


def test_stream_repair_textless_end_turn_ships_evidence_gap_not_degraded_stub(quiet_grounding):
    root = _root()
    client = _CaptureClient(
        [
            _Resp([_Block("text", "Premature answer.")], "end_turn"),
            _Resp([_Block("thinking", "")], "end_turn"),
        ]
    )
    events = _drive_stream(root, client, QUESTION)
    visible = "".join(e.get("text", "") for e in events if e.get("type") == "delta")
    done = [e for e in events if e.get("type") == "done"][-1]
    assert len(client.stream_kwargs) == 2
    assert "Premature answer." not in visible
    assert "Evidence status" in visible
    assert done.get("degraded") is False
