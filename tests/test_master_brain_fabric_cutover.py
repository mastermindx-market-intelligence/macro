"""The AI Daily Brief writer routes through the Capacity Fabric when configured.

Chairman order 2026-11-12: all estate AI routing moves to the unified_router, and
the brief writer must use deepseek-v4.1-flash via fabric/fast. The cutover is
env-gated and scoped to the BRIEF WRITER:

  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_BRIEF_FABRIC != "0"
    -> one fabric_client.complete(..., lane="fast") call, no local retry;
  * not configured, or MACRO_BRIEF_FABRIC=0
    -> the EXACT legacy ladder, byte-for-byte unchanged;
  * the zh translation pass ("<lens>-zh") and every other _call_model consumer
    keep the legacy ladder regardless.

All stub-based: no network, no API keys, no sparse-omitted directory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import llm_auth as llm_auth_mod  # noqa: E402
from engine import master_brain as mb  # noqa: E402
from lib import fabric_client as fc  # noqa: E402

_SHIPPED_CFG = {
    "api_key_env": "DEEPSEEK_API_KEY",
    "llm_base_url": "https://api.deepseek.com/anthropic",
    "llm_model": "deepseek-v4-pro",
}

_CLEAN_REPLY = {
    "summary": "Goldilocks but liquidity contracting.",
    "regime_read": "Macro Q1 with low macro-risk; FX risk-on.",
    "conflicts": ["FX risk-on vs contracting liquidity overlay"],
    "rotation_check": "Partly tracking — ex-US not yet confirming.",
    "transmission": ["liquidity drain -> crypto first to wobble"],
    "watch_items": ["FOMC Jun 17"],
    "confidence": "medium",
}


class _Raw:
    stop_reason = "end_turn"


def _completion(text, model="deepseek-v4.1-flash"):
    return fc.Completion(text=text, model_served=model, route_id="r-1",
                         provider="deepseek", usage={"output_tokens": 5},
                         raw=_Raw())


@pytest.fixture
def fabric_on(monkeypatch):
    """Router configured; record every complete() call."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return _completion(json.dumps(_CLEAN_REPLY))

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_BRIEF_FABRIC", raising=False)
    return calls


@pytest.fixture
def fabric_off(monkeypatch):
    """Router NOT configured; legacy ladder stubbed to an empty provider list."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):   # must never be reached
        calls.append(kwargs)
        return _completion("should not happen")

    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.delenv("MACRO_BRIEF_FABRIC", raising=False)
    return calls


# --------------------------------------------------------------------------- #
# configured -> fabric
# --------------------------------------------------------------------------- #
def test_configured_brief_routes_to_fabric_fast(fabric_on):
    text, reason = mb._call_model("sys", "user", {**_SHIPPED_CFG,
                                                  "usage_stage": "macro"})
    assert reason is None
    assert json.loads(text)["summary"] == _CLEAN_REPLY["summary"]
    assert len(fabric_on) == 1
    call = fabric_on[0]
    assert call["lane"] == "fast"
    assert call["client"] == "Python client"
    assert call["project_id"] == "macro-dashboard"
    assert call["session_id"] == "macro-brief-macro"
    assert call["system"] == "sys"
    assert call["messages"] == [{"role": "user", "content": "user"}]
    assert call["max_tokens"] == 4000


def test_configured_brief_records_fabric_served_by(fabric_on):
    served: dict = {}
    mb._call_model("sys", "user", {**_SHIPPED_CFG, "usage_stage": "china"},
                   served=served)
    assert served == {"provider": "fabric", "model": "deepseek-v4.1-flash"}


def test_synthesize_publishes_fabric_served_by(fabric_on, tmp_path):
    brief = mb.synthesize({"macro": {}}, dict(_SHIPPED_CFG), lens="macro",
                          root=tmp_path)
    assert brief["degraded_reason"] is None
    assert brief["served_by"] == "fabric"
    assert brief["model"] == "deepseek-v4.1-flash"
    assert brief["summary"] == _CLEAN_REPLY["summary"]


def test_fabric_error_degrades_without_retry(monkeypatch):
    calls: list[dict] = []

    def boom(messages, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("router exhausted its ladder")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)
    monkeypatch.delenv("MACRO_BRIEF_FABRIC", raising=False)

    text, reason = mb._call_model("sys", "user", {**_SHIPPED_CFG,
                                                  "usage_stage": "macro"})
    assert text is None and reason == "llm_error"
    assert len(calls) == 1          # one call; the router owns fallback


def test_fabric_empty_reply_is_not_retried(monkeypatch):
    calls: list[dict] = []

    def empty(messages, **kwargs):
        calls.append(kwargs)
        return _completion("")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", empty)
    monkeypatch.delenv("MACRO_BRIEF_FABRIC", raising=False)

    text, reason = mb._call_model("sys", "user", {**_SHIPPED_CFG,
                                                  "usage_stage": "macro"})
    assert text is None and reason == "empty_reply"
    assert len(calls) == 1


# --------------------------------------------------------------------------- #
# not configured / kill-switch -> legacy, unchanged
# --------------------------------------------------------------------------- #
def test_unconfigured_brief_uses_legacy_ladder(fabric_off):
    text, reason = mb._call_model("sys", "user", {**_SHIPPED_CFG,
                                                  "usage_stage": "macro"})
    assert text is None and reason == "no_client_or_key"
    assert fabric_off == []          # fabric never touched


def test_kill_switch_forces_legacy_even_when_configured(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.setenv("MACRO_BRIEF_FABRIC", "0")

    text, reason = mb._call_model("sys", "user", {**_SHIPPED_CFG,
                                                  "usage_stage": "macro"})
    assert text is None and reason == "no_client_or_key"
    assert calls == []


# --------------------------------------------------------------------------- #
# router UNREACHABLE -> fall through to legacy, never blank the brief
#
# FabricUnavailable means no request ever left this host (no token, or the SDK
# will not import). Blanking a brief that the legacy ladder could still produce
# would be a regression, so _call_model must fall through rather than degrade.
# --------------------------------------------------------------------------- #
def test_router_unavailable_falls_through_to_legacy_ladder(monkeypatch):
    calls: list[dict] = []

    def unavailable(messages, **kwargs):
        calls.append(kwargs)
        raise fc.FabricUnavailable("the anthropic SDK is not importable")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", unavailable)
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [{"name": "x"}])
    monkeypatch.setattr(llm_auth_mod, "make_call",
                        lambda *a, **kw: ("legacy reply", None, "deepseek"))
    monkeypatch.delenv("MACRO_BRIEF_FABRIC", raising=False)

    served: dict = {}
    text, reason = mb._call_model(
        "sys", "user", {**_SHIPPED_CFG, "usage_stage": "macro"}, served=served)
    assert (text, reason) == ("legacy reply", None)
    assert len(calls) == 1                # one fabric attempt, then the ladder
    assert served.get("provider") != "fabric"   # legacy rung reported itself


def test_router_unavailable_empty_ladder_reports_legacy_reason(monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: (_ for _ in ()).throw(fc.FabricUnavailable("no sdk")))
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.delenv("MACRO_BRIEF_FABRIC", raising=False)

    text, reason = mb._call_model("sys", "user", {**_SHIPPED_CFG,
                                                  "usage_stage": "macro"})
    # The legacy diagnosis, not "llm_error": the fabric path was never reached.
    assert text is None and reason == "no_client_or_key"


def test_served_call_error_still_does_not_fall_through(monkeypatch):
    """Only FabricUnavailable falls through. A served-call error means the
    router's own ladder was already walked, so a local legacy call would
    double-serve — it must degrade instead."""
    calls: list[dict] = []

    def boom(messages, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("router exhausted its ladder")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)
    monkeypatch.setattr(llm_auth_mod, "build_providers",
                        lambda *a, **kw: pytest.fail("legacy ladder must not run"))
    monkeypatch.delenv("MACRO_BRIEF_FABRIC", raising=False)

    text, reason = mb._call_model("sys", "user", {**_SHIPPED_CFG,
                                                  "usage_stage": "macro"})
    assert text is None and reason == "llm_error"
    assert len(calls) == 1


# --------------------------------------------------------------------------- #
# scope: the zh pass and other consumers stay on the legacy ladder
# --------------------------------------------------------------------------- #
def test_zh_pass_is_not_routed_to_fabric(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.delenv("MACRO_BRIEF_FABRIC", raising=False)

    text, reason = mb._call_model("sys", "user", {**_SHIPPED_CFG,
                                                  "usage_stage": "macro-zh"})
    assert text is None and reason == "no_client_or_key"
    assert calls == []


def test_consumer_without_brief_stage_is_not_routed_to_fabric(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.delenv("MACRO_BRIEF_FABRIC", raising=False)

    text, reason = mb._call_model("sys", "user", dict(_SHIPPED_CFG))
    assert text is None and reason == "no_client_or_key"
    assert calls == []
