"""The China-intel news brief routes through the Capacity Fabric when configured.

Chairman estate-migration outcome #3 (2026-11-12): estate AI routing moves to the
unified_router, and this optional brief must use the router's ``fast`` lane via
``deepseek-v4.1-flash``. The cutover is env-gated and scoped to the BRIEF WRITER:

  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_CHINA_NEWS_INTEL_FABRIC != "0"
    -> one fabric_client.complete(..., lane="fast") call, no local retry;
  * not configured, or MACRO_CHINA_NEWS_INTEL_FABRIC=0
    -> the EXACT legacy direct-client path, unchanged;
  * FabricUnavailable (nothing left the host) -> the legacy path, not a blank brief;
  * any served error / refusal / empty reply -> that degraded return, never a retry.

All stub-based: no network, no API keys, no anthropic SDK, no ledger writes.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import china_news_intel as ni  # noqa: E402
from lib import ai_costs  # noqa: E402
from lib import fabric_client as fc  # noqa: E402

_CFG = {
    "enabled": True,
    "llm_brief": True,
    "api_key_env": "DEEPSEEK_API_KEY",
    "llm_model": "deepseek-chat",
}

_ITEMS = [
    {"theme": "monetary", "title": "央行降准释放流动性"},
    {"theme": "trade", "title": "商务部回应关税清单"},
]

_SERVED = "deepseek-v4.1-flash"


class _Raw:
    def __init__(self, stop_reason="end_turn"):
        self.stop_reason = stop_reason


def _completion(text, model=_SERVED, stop_reason="end_turn"):
    return fc.Completion(
        text=text, model_served=model, route_id="r-1", provider="deepseek",
        usage={"input_tokens": 12, "output_tokens": 40}, raw=_Raw(stop_reason))


class _FakeMessages:
    """The legacy direct-client shape: client.messages.create(**kw)."""

    def __init__(self, sink):
        self._sink = sink

    def create(self, **kwargs):
        self._sink.append(kwargs)
        block = types.SimpleNamespace(type="text", text="遗留中文简报")
        return types.SimpleNamespace(content=[block])


class _FakeAnthropic:
    def __init__(self, sink):
        self.messages = _FakeMessages(sink)


@pytest.fixture
def fabric_on(monkeypatch):
    """Router configured; record every complete() call and every ledger row."""
    calls: list[dict] = []
    ledger: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return _completion("路由器中文简报")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.setattr(ni, "_cfg", lambda: dict(_CFG))
    monkeypatch.setattr(ai_costs, "record_usage",
                        lambda **kw: ledger.append(kw) or True)
    monkeypatch.delenv("MACRO_CHINA_NEWS_INTEL_FABRIC", raising=False)
    return {"calls": calls, "ledger": ledger}


@pytest.fixture
def legacy_ready(monkeypatch):
    """The legacy direct-client path, stubbed to a working in-memory client."""
    legacy_calls: list[dict] = []
    fake_module = types.SimpleNamespace(
        Anthropic=lambda *a, **kw: _FakeAnthropic(legacy_calls))
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    monkeypatch.setattr(ni, "_llm_ready", lambda cfg: True)
    monkeypatch.setattr(ni.config, "secret", lambda *a, **kw: "test-key")
    monkeypatch.setattr(ai_costs, "record_response_usage", lambda **kw: True)
    monkeypatch.setattr(ni, "_cfg", lambda: dict(_CFG))
    return legacy_calls


# --------------------------------------------------------------------------- #
# configured -> fabric
# --------------------------------------------------------------------------- #
def test_configured_brief_routes_to_fabric_fast(fabric_on):
    brief = ni.news_brief(_ITEMS, "偏空 (z -1.20, 10d)")

    assert brief is not None
    assert brief["text"] == "路由器中文简报"
    assert brief["model"] == _SERVED
    assert brief["is_context_only"] is True

    assert len(fabric_on["calls"]) == 1
    call = fabric_on["calls"][0]
    assert call["lane"] == "fast"
    assert call["client"] == "Python client"
    assert call["project_id"] == "macro-dashboard"
    assert call["session_id"] == "macro-china-news-intel"
    assert call["max_tokens"] == 220
    assert call["system"] == ni._BRIEF_SYSTEM
    assert len(call["messages"]) == 1
    assert call["messages"][0]["role"] == "user"
    assert "偏空 (z -1.20, 10d)" in call["messages"][0]["content"]
    assert "央行降准释放流动性" in call["messages"][0]["content"]


def test_configured_brief_never_touches_the_legacy_client(fabric_on, legacy_ready):
    """A served fabric call is the whole call — the legacy client must stay idle."""
    brief = ni.news_brief(_ITEMS, "")

    assert brief is not None
    assert len(fabric_on["calls"]) == 1
    assert legacy_ready == []


def test_ledger_records_fabric_provider_and_served_model(fabric_on):
    ni.news_brief(_ITEMS, "")

    assert len(fabric_on["ledger"]) == 1
    row = fabric_on["ledger"][0]
    assert row["provider"] == "fabric"
    assert row["model"] == _SERVED
    assert row["lane"] == "china-news-intel"
    assert row["input_tokens"] == 12
    assert row["output_tokens"] == 40


def test_ledger_failure_never_breaks_a_served_call(fabric_on, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("ledger disk full")

    monkeypatch.setattr(ai_costs, "record_usage", boom)

    brief = ni.news_brief(_ITEMS, "")
    assert brief is not None and brief["text"] == "路由器中文简报"


def test_headlines_are_capped_at_twelve(fabric_on):
    items = [{"theme": "markets", "title": f"headline {i}"} for i in range(30)]
    ni.news_brief(items, "")

    content = fabric_on["calls"][0]["messages"][0]["content"]
    assert "headline 11" in content
    assert "headline 12" not in content


# --------------------------------------------------------------------------- #
# served failures -> degrade exactly once, never retry
# --------------------------------------------------------------------------- #
def test_served_error_degrades_without_retry(fabric_on, monkeypatch):
    calls = fabric_on["calls"]

    def boom(messages, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("router exhausted its ladder")

    monkeypatch.setattr(fc, "complete", boom)

    brief, reason = ni._fabric_news_brief(_ITEMS, "")
    assert brief is None and reason == "llm_error"
    assert len(calls) == 1                    # one call; the router owns fallback
    assert fabric_on["ledger"] == []


def test_served_error_does_not_fall_through_to_the_legacy_client(
        fabric_on, legacy_ready, monkeypatch):
    """A served error means the router's ladder was already walked; a legacy
    call would double-serve, so news_brief degrades instead."""
    monkeypatch.setattr(fc, "complete",
                        lambda m, **kw: (_ for _ in ()).throw(RuntimeError("exhausted")))

    assert ni.news_brief(_ITEMS, "") is None
    assert legacy_ready == []


def test_refusal_drops_partial_text(fabric_on, monkeypatch):
    partial = _completion("半句被中断的解释", stop_reason="refusal")
    monkeypatch.setattr(fc, "complete", lambda m, **kw: partial)

    brief, reason = ni._fabric_news_brief(_ITEMS, "")
    assert brief is None and reason == "refusal"
    assert fabric_on["ledger"] == []          # nothing to book; nothing rendered
    assert ni.news_brief(_ITEMS, "") is None


def test_empty_reply_is_not_retried(fabric_on, monkeypatch):
    calls = fabric_on["calls"]

    def empty(messages, **kwargs):
        calls.append(kwargs)
        return _completion("   ")

    monkeypatch.setattr(fc, "complete", empty)

    brief, reason = ni._fabric_news_brief(_ITEMS, "")
    assert brief is None and reason == "empty_reply"
    assert len(calls) == 1


# --------------------------------------------------------------------------- #
# not configured / kill-switch -> legacy, unchanged
# --------------------------------------------------------------------------- #
def test_kill_switch_forces_legacy_even_when_configured(
        fabric_on, legacy_ready, monkeypatch):
    monkeypatch.setenv("MACRO_CHINA_NEWS_INTEL_FABRIC", "0")

    brief = ni.news_brief(_ITEMS, "")

    assert fabric_on["calls"] == []           # fabric never touched
    assert len(legacy_ready) == 1             # the legacy client served it
    assert brief is not None and brief["text"] == "遗留中文简报"
    assert brief["model"] == "deepseek-chat"


def test_unconfigured_brief_uses_legacy_client(legacy_ready, monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete", lambda m, **kw: calls.append(kw))
    monkeypatch.delenv("MACRO_CHINA_NEWS_INTEL_FABRIC", raising=False)

    brief = ni.news_brief(_ITEMS, "")

    assert calls == []
    assert len(legacy_ready) == 1
    assert brief is not None and brief["text"] == "遗留中文简报"


@pytest.mark.parametrize("switch", ["enabled", "llm_brief"])
def test_brief_switched_off_never_calls_fabric(switch, monkeypatch):
    calls: list[dict] = []
    cfg = dict(_CFG)
    cfg[switch] = False
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", lambda m, **kw: calls.append(kw))
    monkeypatch.setattr(ni, "_cfg", lambda: dict(cfg))
    monkeypatch.delenv("MACRO_CHINA_NEWS_INTEL_FABRIC", raising=False)

    assert ni.news_brief(_ITEMS, "") is None
    assert calls == []


def test_no_items_never_calls_fabric(fabric_on):
    assert ni.news_brief([], "") is None
    assert ni.news_brief(None, "") is None
    assert fabric_on["calls"] == []


# --------------------------------------------------------------------------- #
# router UNREACHABLE -> fall through to legacy, never blank the brief
#
# FabricUnavailable means no request ever left this host (no token, or the SDK
# will not import), so nothing was served or billed. Blanking a brief the legacy
# client could still produce would be a regression.
# --------------------------------------------------------------------------- #
def test_router_unavailable_falls_through_to_legacy(
        fabric_on, legacy_ready, monkeypatch):
    def unavailable(messages, **kwargs):
        fabric_on["calls"].append(kwargs)
        raise fc.FabricUnavailable("the anthropic SDK is not importable")

    monkeypatch.setattr(fc, "complete", unavailable)

    brief = ni.news_brief(_ITEMS, "")

    assert len(fabric_on["calls"]) == 1       # one fabric attempt, then the legacy path
    assert len(legacy_ready) == 1
    assert brief is not None and brief["text"] == "遗留中文简报"
    assert fabric_on["ledger"] == []          # nothing was served; nothing booked


def test_router_unavailable_without_legacy_key_degrades_quietly(fabric_on, monkeypatch):
    monkeypatch.setattr(fc, "complete",
                        lambda m, **kw: (_ for _ in ()).throw(fc.FabricUnavailable("no sdk")))
    monkeypatch.setattr(ni, "_llm_ready", lambda cfg: False)

    assert ni.news_brief(_ITEMS, "") is None
    assert fabric_on["ledger"] == []
