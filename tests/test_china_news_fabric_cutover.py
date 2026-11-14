"""The China news brief routes through the Capacity Fabric when configured.

Chairman estate migration, outcome #3 (2026-11-12): the optional one-paragraph
China news brief replaces its direct Anthropic-SDK call with the unified_router.
The cutover is env-gated and scoped to this writer:

  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_CHINA_NEWS_FABRIC != "0"
    -> one fabric_client.complete(..., lane="fast") per logical call, no local
       retry, no second provider, and no direct SDK client construction;
  * not configured, or MACRO_CHINA_NEWS_FABRIC=0
    -> the EXACT legacy direct-SDK path, byte-for-byte unchanged;
  * FabricUnavailable (no request left the host) -> fall through to that path;
  * a served error -> degrade to None without retrying or falling through;
    a refusal drops even partial text; an empty reply is not retried.

The brief's own feature flags (enabled + llm_brief) still gate it: the fabric
branch substitutes the PROVIDER, it does not turn a default-off feature on.

All stub-based: no network, no API keys, no sparse-omitted directory.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import china_news as cn  # noqa: E402
from lib import ai_costs  # noqa: E402
from lib import fabric_client as fc  # noqa: E402

_HEADLINES = [
    {"theme": "monetary", "title": "PBOC keeps the loan prime rate steady"},
    {"theme": "growth", "title": "China retail sales miss forecasts"},
]


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
    """The brief is default-off; enable it for every test in this module."""
    monkeypatch.setattr(cn, "_cfg", lambda: {
        "enabled": True, "llm_brief": True,
        "llm_model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/anthropic",
        "api_key_env": "DEEPSEEK_API_KEY",
    })


@pytest.fixture(autouse=True)
def ledger_rows(monkeypatch):
    """Never write data/ai_costs rows in a unit test; capture them instead."""
    rows: list[dict] = []
    monkeypatch.setattr(ai_costs, "record_usage",
                        lambda **kw: rows.append(kw) or True)
    monkeypatch.setattr(ai_costs, "record_response_usage",
                        lambda **kw: rows.append(kw) or True)
    return rows


@pytest.fixture
def fabric_on(monkeypatch):
    """Router configured; record every complete() call."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return _completion("中国宏观背景平稳。")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_CHINA_NEWS_FABRIC", raising=False)
    return calls


@pytest.fixture
def legacy_sdk(monkeypatch):
    """A stub anthropic module so the legacy path can run without a network."""
    calls: list[dict] = []

    class _Resp:
        def __init__(self, text):
            self.content = [types.SimpleNamespace(type="text", text=text)]
            self.usage = types.SimpleNamespace(
                input_tokens=10, output_tokens=4,
                cache_read_input_tokens=0, cache_creation_input_tokens=0)

    class _Messages:
        def create(self, **kwargs):
            calls.append(kwargs)
            return _Resp("legacy 中文 brief")

    class _Client:
        def __init__(self, **kwargs):
            self.messages = _Messages()

    mod = types.ModuleType("anthropic")
    mod.Anthropic = _Client
    monkeypatch.setitem(sys.modules, "anthropic", mod)
    monkeypatch.setattr(cn.config, "secret", lambda *a, **kw: "test-key")
    return calls


# --------------------------------------------------------------------------- #
# configured -> fabric, fast lane
# --------------------------------------------------------------------------- #
def test_configured_routes_to_fabric_fast(fabric_on, monkeypatch):
    monkeypatch.setitem(sys.modules, "anthropic", None)  # legacy SDK must not be needed

    out = cn.news_brief(_HEADLINES, "steady (z +0.4, 30d)")

    assert out == {"text": "中国宏观背景平稳。", "model": "deepseek-v4.1-flash",
                   "is_context_only": True}
    assert len(fabric_on) == 1
    call = fabric_on[0]
    assert call["lane"] == "fast"
    assert call["client"] == "Python client"
    assert call["project_id"] == "macro-dashboard"
    assert call["session_id"] == "macro-china-news"
    assert call["max_tokens"] == 220
    assert call["system"] == cn.BRIEF_SYSTEM
    assert call["messages"][0]["role"] == "user"
    assert "PBOC keeps the loan prime rate steady" in call["messages"][0]["content"]
    assert "steady (z +0.4, 30d)" in call["messages"][0]["content"]


def test_fabric_success_books_usage_row(fabric_on, ledger_rows, monkeypatch):
    def fake_complete(messages, **kwargs):
        fabric_on.append({"messages": messages, **kwargs})
        return _completion("ok", model="deepseek-v4.1-flash", usage={
            "input_tokens": 123, "output_tokens": 45,
            "cache_read_input_tokens": 7, "cache_creation_input_tokens": 8})

    monkeypatch.setattr(fc, "complete", fake_complete)

    cn.news_brief(_HEADLINES, "")

    assert len(ledger_rows) == 1
    row = ledger_rows[0]
    assert row["lane"] == "china-news"
    assert row["provider"] == "fabric"
    assert row["model"] == "deepseek-v4.1-flash"
    assert row["input_tokens"] == 123 and row["output_tokens"] == 45
    assert row["cache_read_tokens"] == 7 and row["cache_creation_tokens"] == 8
    assert row["stage"] == "china_news"


# --------------------------------------------------------------------------- #
# not configured / kill-switch -> legacy, unchanged
# --------------------------------------------------------------------------- #
def test_unconfigured_uses_legacy_path(monkeypatch, legacy_sdk):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.delenv("MACRO_CHINA_NEWS_FABRIC", raising=False)

    out = cn.news_brief(_HEADLINES, "")

    assert out["text"] == "legacy 中文 brief"
    assert calls == []                 # fabric never touched
    assert len(legacy_sdk) == 1        # the direct SDK path ran


def test_kill_switch_forces_legacy_even_when_configured(monkeypatch, legacy_sdk):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setenv("MACRO_CHINA_NEWS_FABRIC", "0")

    out = cn.news_brief(_HEADLINES, "")

    assert out["text"] == "legacy 中文 brief"
    assert calls == []
    assert len(legacy_sdk) == 1


def test_feature_flag_off_keeps_brief_off(monkeypatch):
    """The fabric branch substitutes the provider; it never enables the feature."""
    calls: list[dict] = []
    monkeypatch.setattr(cn, "_cfg", lambda: {"enabled": True, "llm_brief": False})
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.delenv("MACRO_CHINA_NEWS_FABRIC", raising=False)

    assert cn.news_brief(_HEADLINES, "") is None
    assert calls == []


# --------------------------------------------------------------------------- #
# router UNREACHABLE -> fall through to legacy, never blank the brief
# --------------------------------------------------------------------------- #
def test_router_unavailable_falls_through_to_legacy(monkeypatch, legacy_sdk):
    calls: list[dict] = []

    def unavailable(messages, **kwargs):
        calls.append(kwargs)
        raise fc.FabricUnavailable("the anthropic SDK is not importable")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", unavailable)
    monkeypatch.delenv("MACRO_CHINA_NEWS_FABRIC", raising=False)

    out = cn.news_brief(_HEADLINES, "")

    assert out["text"] == "legacy 中文 brief"
    assert len(calls) == 1             # one fabric attempt, then the legacy path
    assert len(legacy_sdk) == 1


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
    # A served failure must degrade HERE, never fall through to the legacy path.
    monkeypatch.setattr(cn, "_llm_ready",
                        lambda cfg: pytest.fail("legacy path must not run"))
    monkeypatch.delenv("MACRO_CHINA_NEWS_FABRIC", raising=False)

    assert cn.news_brief(_HEADLINES, "") is None
    assert len(calls) == 1


def test_refusal_drops_partial_text(monkeypatch, ledger_rows):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion("partial 中文", raw=_RefusalRaw()))
    monkeypatch.delenv("MACRO_CHINA_NEWS_FABRIC", raising=False)

    assert cn.news_brief(_HEADLINES, "") is None
    assert ledger_rows == []


def test_empty_reply_is_not_retried(monkeypatch, ledger_rows):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion(""))
    monkeypatch.delenv("MACRO_CHINA_NEWS_FABRIC", raising=False)

    assert cn.news_brief(_HEADLINES, "") is None
    assert len(calls) == 1
    assert ledger_rows == []


def test_no_headlines_never_calls_fabric(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.delenv("MACRO_CHINA_NEWS_FABRIC", raising=False)

    assert cn.news_brief([], "") is None
    assert calls == []
