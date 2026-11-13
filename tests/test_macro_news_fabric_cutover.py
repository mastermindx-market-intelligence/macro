"""The US macro news brief routes through the Capacity Fabric when configured.

Chairman order 2026-11-12 (estate migration outcome #3, packet R4): the macro
news narrator replaces its direct Anthropic-SDK call with the unified_router.
The cutover is env-gated and scoped to this one writer:

  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_MACRO_NEWS_FABRIC != "0"
    -> one fabric_client.complete(..., lane="fast") per logical call, no local
       retry, no second provider, and no direct SDK client construction;
  * not configured, or MACRO_MACRO_NEWS_FABRIC=0
    -> the EXACT legacy direct-SDK path, byte-for-byte unchanged;
  * FabricUnavailable (no request left the host) -> fall through to that path;
  * a served error -> degrade to None without retrying or falling through;
    a refusal drops even partial text; an empty reply is not retried.

All stub-based: no network, no API keys, no sparse-omitted directory.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import macro_news as mn  # noqa: E402
from lib import ai_costs  # noqa: E402
from lib import fabric_client as fc  # noqa: E402

_HEADLINES = [
    {"title": "Fed holds rates as inflation cools", "domain": "reuters.com",
     "theme": "inflation"},
    {"title": "Jobs report shows payrolls surged", "domain": "bloomberg.com",
     "theme": "labor"},
]

_CFG = {
    "enabled": True,
    "llm_brief": True,
    "llm_model": "deepseek-chat",
    "base_url": "https://api.deepseek.com/anthropic",
    "api_key_env": "DEEPSEEK_API_KEY",
}


class _Raw:
    stop_reason = "end_turn"


class _RefusalRaw:
    stop_reason = "refusal"


def _completion(text, model="deepseek-v4.1-flash", raw=None, usage=None):
    return fc.Completion(text=text, model_served=model, route_id="r-1",
                         provider="deepseek", usage=usage or {"output_tokens": 5},
                         raw=raw or _Raw())


@pytest.fixture(autouse=True)
def brief_cfg(monkeypatch):
    """Pin the module's config to an enabled, llm_brief-on block."""
    monkeypatch.setattr(mn, "_cfg", lambda: dict(_CFG))
    monkeypatch.delenv("MACRO_MACRO_NEWS_FABRIC", raising=False)


@pytest.fixture(autouse=True)
def ledger_rows(monkeypatch):
    """Never write data/ai_costs rows in a unit test; capture them instead."""
    rows: list[dict] = []
    monkeypatch.setattr(ai_costs, "record_usage",
                        lambda **kw: rows.append(kw) or True)
    return rows


@pytest.fixture
def fabric_on(monkeypatch):
    """Router configured; record every complete() call."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return _completion("The macro tape is quiet; inflation is cooling.")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    return calls


@pytest.fixture
def fabric_off(monkeypatch):
    """Router NOT configured; the legacy SDK path is stubbed to a sentinel."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):   # must never be reached
        calls.append(kwargs)
        return _completion("should not happen")

    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete", fake_complete)
    return calls


def _legacy_sentinel(monkeypatch, text="legacy brief"):
    """Stub the legacy direct-SDK path so a fall-through is observable.

    The legacy branch does `import anthropic` INSIDE the function, so a fake
    module in sys.modules is enough — and it keeps this suite runnable on the
    thin CI runner that does not install the SDK.
    """
    import types

    class _Block:
        type = "text"

        def __init__(self, t):
            self.text = t

    class _Resp:
        content = [_Block(text)]

    class _Messages:
        def create(self, **kwargs):
            return _Resp()

    class _Client:
        def __init__(self, *a, **kw):
            self.messages = _Messages()

    fake = types.ModuleType("anthropic")
    fake.Anthropic = _Client
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    return text


# --------------------------------------------------------------------------- #
# configured -> fabric, fast lane
# --------------------------------------------------------------------------- #
def test_configured_brief_routes_to_fabric_fast(fabric_on):
    out = mn.macro_brief(_HEADLINES, "Goldilocks", "optimistic (z=+1.0)",
                         "CPI prints Thursday")
    assert out is not None
    assert out["text"] == "The macro tape is quiet; inflation is cooling."
    assert out["is_context_only"] is True
    assert len(fabric_on) == 1
    call = fabric_on[0]
    assert call["lane"] == "fast"
    assert call["client"] == "Python client"
    assert call["project_id"] == "macro-dashboard"
    assert call["session_id"] == "macro-macro-news"
    assert call["max_tokens"] == 220
    assert call["system"] == mn.BRIEF_SYSTEM
    assert call["messages"][0]["role"] == "user"
    body = call["messages"][0]["content"]
    assert "Regime: Goldilocks" in body
    assert "CPI prints Thursday" in body
    assert "Fed holds rates as inflation cools" in body


def test_fabric_success_books_usage_row(fabric_on, ledger_rows, monkeypatch):
    def fake_complete(messages, **kwargs):
        fabric_on.append({"messages": messages, **kwargs})
        return _completion("ok", model="deepseek-v4.1-flash", usage={
            "input_tokens": 123, "output_tokens": 45,
            "cache_read_input_tokens": 7, "cache_creation_input_tokens": 8})

    monkeypatch.setattr(fc, "complete", fake_complete)
    mn.macro_brief(_HEADLINES)
    assert len(ledger_rows) == 1
    row = ledger_rows[0]
    assert row["lane"] == "macro-news"
    assert row["provider"] == "fabric"
    assert row["model"] == "deepseek-v4.1-flash"
    assert row["input_tokens"] == 123 and row["output_tokens"] == 45
    assert row["cache_read_tokens"] == 7 and row["cache_creation_tokens"] == 8
    assert row["stage"] == "macro_news"


def test_fabric_brief_reports_served_model(fabric_on):
    out = mn.macro_brief(_HEADLINES)
    assert out["model"] == "deepseek-v4.1-flash"


def test_fabric_serves_without_a_legacy_provider_key(fabric_on, monkeypatch):
    """The cutover moves the PROVIDER, so the fabric path must not require the
    legacy DEEPSEEK_API_KEY.

    _llm_ready() gates the legacy ladder on that key. If the fabric branch were
    placed after it, a host with the router configured but no DeepSeek key would
    silently keep the brief off — the cutover would be dead exactly where it is
    meant to take over. The feature flags (enabled + llm_brief) still gate both
    paths; only the key test is skipped on the fabric branch.
    """
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert mn._llm_ready(dict(_CFG)) is False      # legacy path would refuse

    out = mn.macro_brief(_HEADLINES)
    assert out is not None
    assert out["text"] == "The macro tape is quiet; inflation is cooling."
    assert len(fabric_on) == 1


# --------------------------------------------------------------------------- #
# not configured / kill-switch -> legacy, unchanged
# --------------------------------------------------------------------------- #
def test_unconfigured_uses_legacy_path(fabric_off, monkeypatch):
    _legacy_sentinel(monkeypatch, "legacy brief")
    out = mn.macro_brief(_HEADLINES)
    assert out is not None and out["text"] == "legacy brief"
    assert fabric_off == []          # fabric never touched


def test_kill_switch_forces_legacy_even_when_configured(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setenv("MACRO_MACRO_NEWS_FABRIC", "0")
    _legacy_sentinel(monkeypatch, "legacy brief")

    out = mn.macro_brief(_HEADLINES)
    assert out is not None and out["text"] == "legacy brief"
    assert calls == []


def test_feature_gate_still_off_means_no_call(monkeypatch):
    """llm_brief=false keeps the brief off on BOTH paths (provider-only cutover)."""
    monkeypatch.setattr(mn, "_cfg", lambda: {**_CFG, "llm_brief": False})
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))

    assert mn.macro_brief(_HEADLINES) is None
    assert calls == []


def test_no_headlines_means_no_call(fabric_on):
    assert mn.macro_brief([]) is None
    assert fabric_on == []


# --------------------------------------------------------------------------- #
# router UNREACHABLE -> fall through to legacy, never blank the brief
# --------------------------------------------------------------------------- #
def test_router_unavailable_falls_through_to_legacy(monkeypatch):
    calls: list[dict] = []

    def unavailable(messages, **kwargs):
        calls.append(kwargs)
        raise fc.FabricUnavailable("the anthropic SDK is not importable")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", unavailable)
    _legacy_sentinel(monkeypatch, "legacy brief")

    out = mn.macro_brief(_HEADLINES)
    assert out is not None and out["text"] == "legacy brief"
    assert len(calls) == 1           # one fabric attempt, then the legacy path


# --------------------------------------------------------------------------- #
# served failures -> degrade once, never retry, never walk a second provider
# --------------------------------------------------------------------------- #
def test_served_error_degrades_without_retry(monkeypatch):
    calls: list[dict] = []

    def boom(messages, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("router exhausted its ladder")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)
    _legacy_sentinel(monkeypatch, "legacy brief")

    assert mn.macro_brief(_HEADLINES) is None
    assert len(calls) == 1           # no retry, no legacy fall-through


def test_refusal_drops_partial_text(monkeypatch, ledger_rows):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion("partial narration", raw=_RefusalRaw()))

    assert mn.macro_brief(_HEADLINES) is None
    assert ledger_rows == []


def test_empty_reply_is_not_retried(monkeypatch, ledger_rows):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion(""))

    assert mn.macro_brief(_HEADLINES) is None
    assert len(calls) == 1
    assert ledger_rows == []
