"""The thematic desk LLM writer routes through the Capacity Fabric when configured.

Chairman order 2026-11-12 (estate migration outcome #3): the desk's five calls per
run — four panel analysts then the desk-head adjudicator — go to the
unified_router instead of the legacy DeepSeek-key/Claude-OAuth ladder. The
cutover is env-gated and scoped to THIS writer:

  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_THEMATIC_DESK_FABRIC != "0"
    -> one fabric_client.complete per logical call: analysts lane "fast",
       adjudicator lane "balanced". No local retry, no second provider.
  * MACRO_THEMATIC_DESK_FABRIC=0, or no token
    -> the EXACT legacy ladder (master_brain._call_model), byte-for-byte unchanged.
  * FabricUnavailable (no token after all / SDK missing) -> legacy ladder.
  * any other served failure -> the desk degrades exactly as a legacy failure.
  * a refusal is dropped before the fail-closed parser ever sees partial text.
  * a served call books an ai_costs row: provider "fabric", model_served.

All stub-based: no network, no API keys, no ledger writes (record_usage is
captured), no sparse-omitted directory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import master_brain as mb  # noqa: E402
from engine import thematic_desk as td  # noqa: E402
from lib import ai_costs  # noqa: E402
from lib import fabric_client as fc  # noqa: E402

_CFG = {
    "max_tokens": 8000,
    "max_theses": 3,
    "default_horizon_d": 20,
    "falsifier_defaults": {"rel_return": 0.05},
    "panel": {"enabled": True, "min_quorum": 2},
}

_STANCE = json.dumps({
    "regime_context": "ctx",
    "theses": [],
    "emerging_watch": None,
    "confidence": "low",
})

_LEGACY_MARK = json.dumps({
    "regime_context": "legacy", "theses": [], "emerging_watch": None,
    "confidence": "low",
})


def _state(region="us"):
    ranks = [
        {"name": "AI Infra", "name_zh": "AI", "id": "ai", "rank": 1, "score": 2.4,
         "eligible": True, "durability_bar": 0.7, "crowding_z": 0.2, "crowded": False,
         "etf_proxy": "SMH", "scorable": True},
    ]
    return {"as_of": "2026-01-05", "region": region, "market": "US",
            "narrative_rotation": {"region": region, "ranks": ranks,
                                   "guardrails": {"do_not_conclude": ["no sizing"]}},
            "track_record": None}


class _Raw:
    def __init__(self, stop_reason="end_turn"):
        self.stop_reason = stop_reason


def _completion(text, model="deepseek-v4.1-flash", stop_reason="end_turn"):
    return fc.Completion(
        text=text, model_served=model, route_id="r-1", provider="deepseek",
        usage={"input_tokens": 120, "output_tokens": 40,
               "cache_read_input_tokens": 7, "cache_creation_input_tokens": 3},
        raw=_Raw(stop_reason),
    )


@pytest.fixture
def usage_rows(monkeypatch):
    """Capture ai_costs rows instead of appending to the real data/ ledger."""
    rows: list[dict] = []

    def fake_record_usage(**kwargs):
        rows.append(kwargs)
        return True

    monkeypatch.setattr(ai_costs, "record_usage", fake_record_usage)
    return rows


@pytest.fixture
def fabric_on(monkeypatch, usage_rows):
    """Router configured; record every complete() call."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return _completion(_STANCE)

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv(td._FABRIC_KILL_SWITCH, raising=False)
    return calls


@pytest.fixture
def legacy_stub(monkeypatch):
    """The legacy ladder stubbed to a recognisable marker; record its calls."""
    calls: list[dict] = []

    def fake_call_model(system, user, cfg):
        calls.append({"system": system, "user": user})
        return _LEGACY_MARK, None

    monkeypatch.setattr(mb, "_call_model", fake_call_model)
    return calls


@pytest.fixture
def fabric_never(monkeypatch):
    """complete() must never be reached."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append(kwargs)
        return _completion("should not happen")

    monkeypatch.setattr(fc, "complete", fake_complete)
    return calls


# --------------------------------------------------------------------------- #
# configured -> fabric, per site
# --------------------------------------------------------------------------- #
def test_panel_analysts_route_to_fabric_fast(fabric_on):
    panel = td._run_panel(_state(), dict(_CFG))
    assert set(panel) == set(td._PANEL_SYSTEMS)
    assert all(v is not None for v in panel.values())     # all four parsed
    assert len(fabric_on) == 4
    for call in fabric_on:
        assert call["lane"] == "fast"
        assert call["client"] == "Python client"
        assert call["project_id"] == "macro-dashboard"
        assert call["session_id"] == "macro-thematic-desk-analyst"
        assert call["max_tokens"] == 8000
        assert call["messages"][0]["role"] == "user"


def test_adjudicator_routes_to_fabric_balanced(fabric_on):
    panel = {k: td._ad._extract_json(_STANCE) for k in td._PANEL_SYSTEMS}
    reply, reason = td._adjudicate(_state(), panel, dict(_CFG))
    assert reply is not None and reason is None
    assert len(fabric_on) == 1
    call = fabric_on[0]
    assert call["lane"] == "balanced"
    assert call["session_id"] == "macro-thematic-desk-adjudicator"
    assert call["max_tokens"] == 8000


def test_synthesize_routes_four_fast_and_one_balanced(fabric_on):
    brief = td.synthesize(_state(), dict(_CFG))
    assert len(fabric_on) == 5
    lanes = [c["lane"] for c in fabric_on]
    assert lanes.count("fast") == 4 and lanes.count("balanced") == 1
    sessions = {c["session_id"] for c in fabric_on}
    assert sessions == {"macro-thematic-desk-analyst",
                        "macro-thematic-desk-adjudicator"}
    assert brief["degraded_reason"] is None


def test_single_analyst_fallback_stays_on_fast_lane(fabric_on, monkeypatch):
    """Sub-quorum panel (1/4 present) takes the analyst-only fallback, on fast."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        system = kwargs.get("system") or ""
        if "ROLE: TREND-RIDER" in system:
            return _completion(_STANCE)
        if "ROLE:" in system:                     # the other three: unparseable
            return _completion("not json")
        return _completion(_STANCE)               # the single-analyst _SYSTEM

    monkeypatch.setattr(fc, "complete", fake_complete)
    brief = td.synthesize(_state(), dict(_CFG))
    assert len(calls) == 5                        # 4 panel + 1 analyst
    tail = calls[-1]
    assert tail["session_id"] == "macro-thematic-desk-analyst"
    assert tail["lane"] == "fast"
    assert brief["degraded_reason"].startswith("panel_incomplete:")


# --------------------------------------------------------------------------- #
# inert by default -> the exact legacy ladder
# --------------------------------------------------------------------------- #
def test_kill_switch_uses_legacy_even_when_configured(
        monkeypatch, legacy_stub, fabric_never):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setenv(td._FABRIC_KILL_SWITCH, "0")
    text, reason = td._adjudicate(_state(), {}, dict(_CFG))
    assert text == _LEGACY_MARK and reason is None
    assert len(legacy_stub) == 1
    assert fabric_never == []


def test_unconfigured_uses_legacy(monkeypatch, legacy_stub, fabric_never):
    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.delenv(td._FABRIC_KILL_SWITCH, raising=False)
    text, _ = td._analyst_call("sys", "user", dict(_CFG))
    assert text == _LEGACY_MARK
    assert len(legacy_stub) == 1
    assert fabric_never == []


def test_synthesize_inert_when_unconfigured(monkeypatch, legacy_stub, fabric_never):
    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.delenv(td._FABRIC_KILL_SWITCH, raising=False)
    brief = td.synthesize(_state(), dict(_CFG))
    assert brief["regime_context"] == "legacy"
    assert len(legacy_stub) == 5                  # 4 panel + adjudicator, all legacy
    assert fabric_never == []


# --------------------------------------------------------------------------- #
# FabricUnavailable -> legacy (nothing left this host)
# --------------------------------------------------------------------------- #
def test_fabric_unavailable_falls_back_to_legacy(monkeypatch, legacy_stub):
    def boom(messages, **kwargs):
        raise fc.FabricUnavailable("no token after all")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)
    monkeypatch.delenv(td._FABRIC_KILL_SWITCH, raising=False)
    text, reason = td._analyst_call("sys", "user", dict(_CFG))
    assert text == _LEGACY_MARK and reason is None
    assert len(legacy_stub) == 1                  # the legacy ladder ran


# --------------------------------------------------------------------------- #
# served failure -> degrade exactly as a legacy failure (no retry, no 2nd provider)
# --------------------------------------------------------------------------- #
def test_transport_error_degrades_without_legacy_or_retry(monkeypatch, legacy_stub):
    calls: list[int] = []

    def boom(messages, **kwargs):
        calls.append(1)
        raise ConnectionError("router died mid-request")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)
    monkeypatch.delenv(td._FABRIC_KILL_SWITCH, raising=False)
    text, reason = td._analyst_call("sys", "user", dict(_CFG))
    assert text is None and reason == "llm_error"
    assert len(calls) == 1                        # ONE attempt, never retried
    assert legacy_stub == []                      # never walks a second provider


def test_empty_reply_is_not_retried(fabric_on, monkeypatch):
    calls: list[int] = []

    def empty(messages, **kwargs):
        calls.append(1)
        return _completion("")

    monkeypatch.setattr(fc, "complete", empty)
    text, reason = td._analyst_call("sys", "user", dict(_CFG))
    assert text is None and reason == "empty_reply"
    assert len(calls) == 1


def test_truncated_reply_is_returned_with_reason(monkeypatch, usage_rows):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion(_STANCE, stop_reason="max_tokens"))
    monkeypatch.delenv(td._FABRIC_KILL_SWITCH, raising=False)
    text, reason = td._analyst_call("sys", "user", dict(_CFG))
    assert text is not None and reason == "truncated"


# --------------------------------------------------------------------------- #
# refusal -> dropped before the fail-closed parser
# --------------------------------------------------------------------------- #
def test_refusal_is_dropped_even_with_partial_text(monkeypatch, usage_rows):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion('{"regime_context": "partial"',
                                           stop_reason="refusal"))
    monkeypatch.delenv(td._FABRIC_KILL_SWITCH, raising=False)
    text, reason = td._analyst_call("sys", "user", dict(_CFG))
    assert text is None and reason == "refusal"
    assert usage_rows == []                       # a refusal is not booked as spend


def test_refusal_degrades_the_brief_before_parsing(monkeypatch, usage_rows):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion('{"regime_context": "partial"',
                                           stop_reason="refusal"))
    monkeypatch.delenv(td._FABRIC_KILL_SWITCH, raising=False)
    brief = td.synthesize(_state(), dict(_CFG))
    assert brief["raw_text"] is None              # partial text never published
    assert brief["regime_context"] is None
    assert brief["theses"] == []
    assert brief["degraded_reason"] == "refusal"


# --------------------------------------------------------------------------- #
# ledger continuity: provider "fabric" + the served model
# --------------------------------------------------------------------------- #
def test_usage_row_books_fabric_and_served_model(fabric_on, usage_rows):
    td._adjudicate(_state(), {}, dict(_CFG))
    assert len(usage_rows) == 1
    row = usage_rows[0]
    assert row["provider"] == "fabric"
    assert row["model"] == "deepseek-v4.1-flash"
    assert row["lane"] == "thematic-desk"
    assert row["stage"] == "adjudicator"
    assert row["input_tokens"] == 120
    assert row["output_tokens"] == 40
    assert row["cache_read_tokens"] == 7
    assert row["cache_creation_tokens"] == 3


def test_analyst_usage_rows_are_stage_tagged(fabric_on, usage_rows):
    td._run_panel(_state(), dict(_CFG))
    assert len(usage_rows) == 4
    assert {r["stage"] for r in usage_rows} == {"analyst"}
    assert {r["provider"] for r in usage_rows} == {"fabric"}


def test_legacy_path_books_no_fabric_row(monkeypatch, legacy_stub, usage_rows):
    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.delenv(td._FABRIC_KILL_SWITCH, raising=False)
    td._adjudicate(_state(), {}, dict(_CFG))
    assert usage_rows == []
