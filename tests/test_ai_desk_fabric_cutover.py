"""The AI Desk routes through the Capacity Fabric when it is configured.

Chairman order 2026-11-12 (estate migration outcome #3): the desk's LLM call
sites move to the unified_router. The cutover is env-gated and scoped to the
desk's own writer sites:

  * analyst panel -> one complete(..., lane="fast") per role;
  * desk-head adjudicator -> one complete(..., lane="balanced") call;
  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_AI_DESK_FABRIC != "0"
    -> fabric, exactly ONE request per logical call, no local retry/failover;
  * not configured, kill-switch "0", or FabricUnavailable (nothing left the
    host) -> the EXACT legacy ladder;
  * a served failure degrades like a legacy failure and never falls back;
  * a stop_reason=="refusal" reply is dropped before any parser sees the text;
  * usage is booked to lib.ai_costs with provider="fabric" and the served model.

All stub-based: no network, no API keys, no sparse-omitted directory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import ai_desk as d  # noqa: E402
from lib import ai_costs  # noqa: E402
from lib import fabric_client as fc  # noqa: E402

CFG = d._cfg()

_FLOW = {
    "as_of": "2026-11-12", "verdict": "display_only",
    "regime": {"vix": 17.0, "elevated": False},
    "cluster": {"absorption": 0.55, "regime": "mixed", "dominant_cluster": ["Energy"]},
    "sectors": [{"name": "Energy", "type": "sector", "read_quality": 0.7, "stage": "emerging"}],
    "baskets": [], "emerging": {"sectors": ["Energy"], "baskets": []},
    "ai_handoff": {"overall_verdict": "display_only",
                   "do_not_conclude": ["no forward returns from flow_score"]},
}

_FINAL = {
    "regime_context": "Cyclical cluster concentrating; the panel is split.",
    "theses": [{"subject": "Energy", "lean": "overweight", "conviction": "low",
                "horizon_d": 20, "thesis": "Energy leads the cluster.",
                "evidence": ["opportunity: cluster leader"],
                "dissent": "Skeptic: narrow and mean-reverting.",
                "falsifier_text": "Energy lags SPY by >5% over 20 trading days."}],
    "confidence": "low",
}

_STANCE = {"stance": "{role} read", "key_risk": "x",
           "candidates": [{"subject": "Energy", "lean": "overweight",
                           "rationale": "r", "strength": "moderate"}]}


def _state():
    return {"as_of": "2026-11-12", "flow": d._flow_view(_FLOW), "regime_snap": None,
            "track_record": None, "sources_present": {"flow": True, "regime_snap": False}}


def _role(system: str) -> str:
    if "DESK HEAD" in system:
        return "adjudicator"
    for tag in ("OPPORTUNITY", "SKEPTIC", "BASE-RATE", "STRUCTURAL"):
        if f"ROLE: {tag}" in system:
            return tag.lower()
    return "single"


class _Raw:
    def __init__(self, stop_reason="end_turn"):
        self.stop_reason = stop_reason


def _completion(text="{}", model="deepseek-v4.1-flash", stop_reason="end_turn",
                usage=None):
    return fc.Completion(
        text=text, model_served=model, route_id="r-1", provider="deepseek",
        usage={"input_tokens": 10, "output_tokens": 20} if usage is None else usage,
        raw=_Raw(stop_reason))


def _reply_for(system: str) -> str:
    role = _role(system)
    if role in ("adjudicator", "single"):
        return json.dumps(_FINAL)
    return json.dumps({**_STANCE, "stance": f"{role} read"})


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _no_ledger_writes(monkeypatch):
    """Never append to the repo's real data/ai_costs/usage.jsonl from tests.

    The fabric branch books usage directly (the ladder did it inside
    llm_auth.make_call); individual tests re-patch this with a recorder.
    """
    monkeypatch.setattr(ai_costs, "record_usage", lambda **kw: True)


@pytest.fixture
def fabric_on(monkeypatch):
    """Router configured; record every complete() call."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return _completion(_reply_for(kwargs.get("system") or ""))

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_AI_DESK_FABRIC", raising=False)
    return calls


@pytest.fixture
def fabric_off(monkeypatch):
    """Router NOT configured; complete() must never be reached."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):   # must never be reached
        calls.append(kwargs)
        return _completion("should not happen")

    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_AI_DESK_FABRIC", raising=False)
    return calls


@pytest.fixture
def legacy(monkeypatch):
    """The legacy ladder stubbed: records calls, returns canned JSON."""
    calls: list[dict] = []

    def fake_legacy(system, user, cfg, served=None):
        calls.append({"system": system, "user": user, "served": served})
        if served is not None:
            served["provider"] = "legacy"
        return _reply_for(system), None

    monkeypatch.setattr(d._mb, "_call_model", fake_legacy)
    return calls


# --------------------------------------------------------------------------- #
# configured -> fabric
# --------------------------------------------------------------------------- #
def test_panel_routes_four_analysts_fast_then_adjudicator_balanced(fabric_on):
    brief = d.synthesize(_state(), CFG)

    assert len(fabric_on) == 5                       # 4 analysts + adjudicator
    lanes = sorted(c["lane"] for c in fabric_on)
    assert lanes == ["balanced"] + ["fast"] * 4
    sessions = sorted(c["session_id"] for c in fabric_on)
    assert sessions == (["macro-ai-desk-adjudicator"]
                        + ["macro-ai-desk-analyst"] * 4)
    for c in fabric_on:
        assert c["client"] == "Python client"
        assert c["project_id"] == "macro-dashboard"
        assert c["max_tokens"] == CFG["max_tokens"]
        assert c["messages"] and c["messages"][0]["role"] == "user"

    adj = [c for c in fabric_on if c["lane"] == "balanced"]
    assert adj[0]["system"] == d._ADJ_SYSTEM
    assert brief["served_by"] == "fabric"
    assert brief["model"] == "deepseek-v4.1-flash"
    assert len(brief["theses"]) == 1
    assert brief["degraded_reason"] is None


def test_fabric_books_ledger_rows_with_served_model(fabric_on, monkeypatch):
    rows: list[dict] = []
    monkeypatch.setattr(ai_costs, "record_usage",
                        lambda **kw: rows.append(kw) or True)

    d.synthesize(_state(), CFG)

    assert len(rows) == 5
    for row in rows:
        assert row["provider"] == "fabric"
        assert row["model"] == "deepseek-v4.1-flash"
        assert row["lane"] == "master-brain"     # continuity with the ladder
        assert row["stage"] == "ai-desk"
        assert row["input_tokens"] == 10 and row["output_tokens"] == 20


# --------------------------------------------------------------------------- #
# inert by default: legacy ladder, byte-identical
# --------------------------------------------------------------------------- #
def test_kill_switch_zero_forces_legacy_even_when_configured(
        fabric_on, legacy, monkeypatch):
    monkeypatch.setenv("MACRO_AI_DESK_FABRIC", "0")

    brief = d.synthesize(_state(), CFG)

    assert fabric_on == []                           # zero router requests
    assert len(legacy) == 5                          # panel + adjudicator on the ladder
    assert brief["served_by"] == "legacy"
    assert len(brief["theses"]) == 1


def test_no_token_falls_back_to_legacy(fabric_off, legacy):
    brief = d.synthesize(_state(), CFG)

    assert fabric_off == []
    assert len(legacy) == 5
    assert brief["served_by"] == "legacy"
    assert len(brief["theses"]) == 1


def test_fabric_unavailable_falls_through_to_legacy(legacy, monkeypatch):
    """Nothing left the host (no token / no SDK) -> the unchanged ladder runs."""
    attempts: list[dict] = []

    def unavailable(messages, **kwargs):
        attempts.append(kwargs)
        raise fc.FabricUnavailable("FABRIC_ROUTER_TOKEN is not set")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", unavailable)
    monkeypatch.delenv("MACRO_AI_DESK_FABRIC", raising=False)

    brief = d.synthesize(_state(), CFG)

    assert len(attempts) == 5                        # one probe per logical call
    assert len(legacy) == 5                          # then the ladder, once each
    assert brief["served_by"] == "legacy"
    assert len(brief["theses"]) == 1


# --------------------------------------------------------------------------- #
# served failure: degrade, never retry, never walk a second provider
# --------------------------------------------------------------------------- #
def test_transport_error_degrades_without_retry_or_legacy(monkeypatch, legacy):
    attempts: list[dict] = []

    def boom(messages, **kwargs):
        attempts.append(kwargs)
        raise RuntimeError("router returned 503")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)
    monkeypatch.delenv("MACRO_AI_DESK_FABRIC", raising=False)

    panel = d._run_panel(_state(), CFG)
    assert panel == {k: None for k in d._PANEL_SYSTEMS}
    assert len(attempts) == 4                        # exactly one request per analyst

    reply, reason = d._adjudicate(_state(), {"opportunity": {"stance": "x"}},
                                  CFG, served={})
    assert (reply, reason) == (None, "llm_error")
    assert len(attempts) == 5                        # one more request, no retry
    assert legacy == []                              # no second provider was walked


def test_refusal_is_dropped_before_the_parser(monkeypatch):
    def refused(messages, **kwargs):
        if _role(kwargs.get("system") or "") == "adjudicator":
            return _completion('{"regime_context": "partial', stop_reason="refusal")
        return _completion(_reply_for(kwargs.get("system") or ""))

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", refused)
    monkeypatch.delenv("MACRO_AI_DESK_FABRIC", raising=False)
    monkeypatch.setattr(ai_costs, "record_usage", lambda **kw: True)

    brief = d.synthesize(_state(), CFG)

    assert brief["raw_text"] is None                 # partial text dropped
    assert brief["degraded_reason"] == "refusal"
    assert brief["theses"] == []
    assert brief["served_by"] is None                # no authorship claim on a refusal
