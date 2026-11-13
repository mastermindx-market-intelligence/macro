"""The alt-data brain writer routes through the Capacity Fabric when configured.

Chairman order 2026-11-12 (estate migration outcome #3): the brain's LLM call —
the source of the stock-dossier write-up — moves from the legacy DeepSeek-key /
Claude-OAuth ladder to the Capacity Fabric ``unified_router``. The cutover is
env-gated and scoped to this one writer:

  * configured (``FABRIC_ROUTER_TOKEN`` present) and
    ``MACRO_ALTDATA_BRAIN_FABRIC`` != "0"
    -> ONE ``fabric_client.complete(..., lane="balanced")`` call, no local retry;
  * not configured, or the kill-switch is "0"
    -> the EXACT legacy ``llm_auth`` ladder, byte-for-byte unchanged;
  * an UNUSABLE adapter (``FabricUnavailable``: no token or no SDK) -> the
    legacy ladder, not a blank brain;
  * a router that is merely DOWN raises a transport error -> degrade exactly
    like a legacy failure. No retry, no second provider, no legacy fall-through:
    the router already walked its own ladder.

All stub-based: no network, no API keys, no ledger writes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import altdata_brain as ab  # noqa: E402
from engine import llm_auth as llm_auth_mod  # noqa: E402
from lib import ai_costs  # noqa: E402
from lib import fabric_client as fc  # noqa: E402

_BRIEF_REPLY = json.dumps({
    "regime_read": "Insider buying is converging on AAA while the sector lags.",
    "regime_read_zh": "内部人买入在 AAA 上汇聚。",
    "theses": [{
        "ticker": "AAA",
        "lean": "overweight",
        "conviction": "medium",
        "action": "WATCH",
        "horizon_d": 63,
        "thesis": "Three independent insider buys align [insider_cluster].",
        "thesis_zh": "三笔独立内部人买入一致。",
        "second_order": ["BBB — supplies AAA"],
        "evidence": ["[insider_cluster]"],
        "dissent": "The sector is still lagging.",
        "falsifier_text": "AAA underperforms SPY by 5pp over 63 days",
    }],
    "confidence": "low",
})

_CFG = {
    "max_tokens": 8000,
    "usage_lane": "altdata-brain",
    "horizon_d": 63,
    "min_weighted": 0.9,
    "rel_threshold": 0.05,
}

_STATE = {
    "as_of": "2026-11-12",
    "clusters": [{
        "ticker": "AAA",
        "weighted_score": 1.2,
        "rs_vs_spy_60d": 5.0,
        "channels": ["insider_cluster"],
        "extended": False,
        "scorable": True,
    }],
    "n_clusters": 1,
    "track_record": None,
}


class _Raw:
    """Minimal stand-in for the SDK Message object the adapter wraps."""

    def __init__(self, stop_reason: str = "end_turn") -> None:
        self.stop_reason = stop_reason


def _completion(text: str = _BRIEF_REPLY, model: str = "deepseek-v4.1-flash",
                stop_reason: str = "end_turn") -> fc.Completion:
    return fc.Completion(
        text=text,
        model_served=model,
        route_id="route-1",
        provider="deepseek",
        usage={
            "input_tokens": 11,
            "output_tokens": 7,
            "cache_read_input_tokens": 3,
            "cache_creation_input_tokens": 2,
        },
        raw=_Raw(stop_reason),
    )


@pytest.fixture(autouse=True)
def usage_rows(monkeypatch):
    """Capture ai_costs rows instead of appending to data/ai_costs/usage.jsonl."""
    rows: list[dict] = []
    monkeypatch.setattr(ai_costs, "record_usage",
                        lambda **kw: rows.append(kw) or True)
    return rows


@pytest.fixture
def fabric_on(monkeypatch):
    """Router configured; record every complete() call."""
    calls: list[dict] = []
    state = {"reply": _BRIEF_REPLY, "stop_reason": "end_turn"}

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return _completion(state["reply"], stop_reason=state["stop_reason"])

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_ALTDATA_BRAIN_FABRIC", raising=False)
    return {"calls": calls, "state": state}


@pytest.fixture
def legacy_ladder(monkeypatch):
    """Stub the legacy llm_auth ladder so it is observable without network."""
    seen: list[str] = []

    def fake_build_providers(cfg, **kwargs):
        seen.append("build_providers")
        return [{"name": "stub", "client": None, "model": "stub-model"}]

    def fake_make_call(providers, call_fn, *, context="", attempts=None):
        seen.append(context)
        return "legacy reply", None, "oauth"

    monkeypatch.setattr(llm_auth_mod, "build_providers", fake_build_providers)
    monkeypatch.setattr(llm_auth_mod, "make_call", fake_make_call)
    return seen


# --------------------------------------------------------------------------- #
# the gate itself
# --------------------------------------------------------------------------- #
def test_gate_off_without_token(monkeypatch):
    monkeypatch.delenv(fc.TOKEN_ENV, raising=False)
    monkeypatch.delenv("MACRO_ALTDATA_BRAIN_FABRIC", raising=False)
    assert ab._fabric_enabled() is False


def test_gate_on_with_token(monkeypatch):
    monkeypatch.setenv(fc.TOKEN_ENV, "token")
    monkeypatch.delenv("MACRO_ALTDATA_BRAIN_FABRIC", raising=False)
    assert ab._fabric_enabled() is True


def test_gate_kill_switch_beats_token(monkeypatch):
    monkeypatch.setenv(fc.TOKEN_ENV, "token")
    monkeypatch.setenv("MACRO_ALTDATA_BRAIN_FABRIC", "0")
    assert ab._fabric_enabled() is False


# --------------------------------------------------------------------------- #
# configured -> fabric
# --------------------------------------------------------------------------- #
def test_configured_routes_to_fabric_balanced(fabric_on, monkeypatch):
    # Even with an EMPTY legacy ladder the writer must exist and serve: the whole
    # point of the cutover is a host whose legacy credentials cannot serve.
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.setattr(llm_auth_mod, "make_call",
                        lambda *a, **kw: pytest.fail("legacy ladder must not run"))

    fn = ab._make_call(dict(_CFG))
    assert fn is not None
    text, reason = fn("SYS", "USER")

    assert text == _BRIEF_REPLY and reason is None
    assert len(fabric_on["calls"]) == 1
    call = fabric_on["calls"][0]
    assert call["lane"] == "balanced"
    assert call["project_id"] == "macro-dashboard"
    assert call["session_id"] == "macro-altdata-brain"
    assert call["system"] == "SYS"
    assert call["messages"] == [{"role": "user", "content": "USER"}]
    assert call["max_tokens"] == 8000
    assert call.get("client", fc.DEFAULT_CLIENT) in fc.CLIENTS


def test_existing_max_tokens_is_forwarded(fabric_on, monkeypatch):
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    fn = ab._make_call({**_CFG, "max_tokens": 5000})
    fn("SYS", "USER")
    assert fabric_on["calls"][0]["max_tokens"] == 5000


def test_fabric_reply_still_parses_the_brain_action_contract(fabric_on, monkeypatch,
                                                             tmp_path):
    """End-to-end at the writer site: the fabric reply walks the same JSON
    extraction, thesis build and de-escalation clamp as a legacy reply."""
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])

    brief = ab.synthesize(dict(_STATE), dict(_CFG), root=tmp_path)

    assert brief["degraded_reason"] is None
    assert brief["regime_read"].startswith("Insider buying")
    assert len(brief["theses"]) == 1
    thesis = brief["theses"][0]
    assert thesis["ticker"] == "AAA"
    assert thesis["action"] in ab._ACTIONS
    assert thesis["lean"] in ab._LEANS
    assert len(fabric_on["calls"]) == 1


# --------------------------------------------------------------------------- #
# not configured / kill-switch -> legacy, unchanged
# --------------------------------------------------------------------------- #
def test_unconfigured_uses_legacy_ladder(monkeypatch, legacy_ladder):
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):   # must never be reached
        calls.append(kwargs)
        return _completion()

    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_ALTDATA_BRAIN_FABRIC", raising=False)

    fn = ab._make_call(dict(_CFG))
    text, reason = fn("SYS", "USER")

    assert (text, reason) == ("legacy reply", None)
    assert calls == []
    assert "build_providers" in legacy_ladder


def test_kill_switch_forces_legacy_even_when_configured(monkeypatch, legacy_ladder):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setenv("MACRO_ALTDATA_BRAIN_FABRIC", "0")

    fn = ab._make_call(dict(_CFG))
    text, reason = fn("SYS", "USER")

    assert (text, reason) == ("legacy reply", None)
    assert calls == []


def test_kill_switch_with_no_legacy_creds_still_inert(monkeypatch):
    """Inert by default: killed AND no legacy ladder -> no call closure at all,
    exactly as before the cutover."""
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: pytest.fail("fabric must stay off"))
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.setenv("MACRO_ALTDATA_BRAIN_FABRIC", "0")

    assert ab._make_call(dict(_CFG)) is None


def test_unconfigured_and_no_legacy_creds_returns_none(monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: pytest.fail("fabric must stay off"))
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.delenv("MACRO_ALTDATA_BRAIN_FABRIC", raising=False)

    assert ab._make_call(dict(_CFG)) is None


# --------------------------------------------------------------------------- #
# adapter UNUSABLE -> legacy ladder, never blank the brain
# --------------------------------------------------------------------------- #
def test_router_unavailable_falls_through_to_legacy(monkeypatch, legacy_ladder):
    calls: list[dict] = []

    def unavailable(messages, **kwargs):
        calls.append(kwargs)
        raise fc.FabricUnavailable("the anthropic SDK is not importable")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", unavailable)
    monkeypatch.delenv("MACRO_ALTDATA_BRAIN_FABRIC", raising=False)

    fn = ab._make_call(dict(_CFG))
    text, reason = fn("SYS", "USER")

    assert (text, reason) == ("legacy reply", None)
    assert len(calls) == 1          # one fabric attempt, then the ladder
    assert "altdata_brain" in legacy_ladder


def test_router_unavailable_empty_ladder_reports_legacy_reason(monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: (_ for _ in ()).throw(fc.FabricUnavailable("no sdk")))
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.delenv("MACRO_ALTDATA_BRAIN_FABRIC", raising=False)

    fn = ab._make_call(dict(_CFG))
    text, reason = fn("SYS", "USER")
    # The legacy diagnosis, not "llm_error": the fabric path was never reached.
    assert text is None and reason == "no_provider"


# --------------------------------------------------------------------------- #
# router DOWN -> degrade; never retry, never walk the legacy ladder
# --------------------------------------------------------------------------- #
def test_transport_error_degrades_without_retry_or_fallthrough(monkeypatch):
    calls: list[dict] = []

    def boom(messages, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("502 from router")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.setattr(llm_auth_mod, "make_call",
                        lambda *a, **kw: pytest.fail("legacy ladder must not run"))
    monkeypatch.delenv("MACRO_ALTDATA_BRAIN_FABRIC", raising=False)

    fn = ab._make_call(dict(_CFG))
    text, reason = fn("SYS", "USER")

    assert text is None and reason == "llm_error"
    assert len(calls) == 1, "the router owns fallback: one logical call = one request"


def test_empty_reply_is_not_retried(fabric_on, monkeypatch):
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    fabric_on["state"]["reply"] = ""

    fn = ab._make_call(dict(_CFG))
    text, reason = fn("SYS", "USER")

    assert text is None and reason == "empty_reply"
    assert len(fabric_on["calls"]) == 1


def test_refusal_with_partial_text_is_dropped(fabric_on, monkeypatch):
    """A refusal is a refusal even when it carries text: the legacy _do_call
    drops it, and a complete-looking JSON object must never reach the parser."""
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    fabric_on["state"]["reply"] = _BRIEF_REPLY
    fabric_on["state"]["stop_reason"] = "refusal"

    fn = ab._make_call(dict(_CFG))
    text, reason = fn("SYS", "USER")

    assert text is None, "a refusal carrying text must not be parsed"
    assert reason == "refusal"
    assert len(fabric_on["calls"]) == 1


def test_truncated_reply_is_flagged_but_kept(fabric_on, monkeypatch):
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    fabric_on["state"]["reply"] = '{"theses": []}'
    fabric_on["state"]["stop_reason"] = "max_tokens"

    fn = ab._make_call(dict(_CFG))
    text, reason = fn("SYS", "USER")

    assert text == '{"theses": []}' and reason == "truncated"


# --------------------------------------------------------------------------- #
# ledger continuity: provider="fabric" + the model the router served
# --------------------------------------------------------------------------- #
def test_ledger_row_names_fabric_and_served_model(fabric_on, monkeypatch, usage_rows):
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])

    fn = ab._make_call(dict(_CFG))
    fn("SYS", "USER")

    assert len(usage_rows) == 1
    row = usage_rows[0]
    assert row["lane"] == "altdata-brain"
    assert row["provider"] == "fabric"
    assert row["model"] == "deepseek-v4.1-flash"
    assert row["input_tokens"] == 11
    assert row["output_tokens"] == 7
    assert row["cache_read_tokens"] == 3
    assert row["cache_creation_tokens"] == 2
    assert row["stage"] == "altdata_brain"


def test_ledger_row_is_booked_even_when_reply_is_dropped(fabric_on, monkeypatch,
                                                         usage_rows):
    """The call was served and billed regardless of the content gate."""
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    fabric_on["state"]["stop_reason"] = "refusal"

    fn = ab._make_call(dict(_CFG))
    fn("SYS", "USER")

    assert len(usage_rows) == 1 and usage_rows[0]["provider"] == "fabric"


def test_unavailable_records_no_ledger_row(monkeypatch, usage_rows):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: (_ for _ in ()).throw(fc.FabricUnavailable("no token")))
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.delenv("MACRO_ALTDATA_BRAIN_FABRIC", raising=False)

    fn = ab._make_call(dict(_CFG))
    fn("SYS", "USER")

    assert usage_rows == [], "FabricUnavailable means nothing was served or billed"
