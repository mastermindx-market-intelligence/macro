"""The news annotator routes through the Capacity Fabric when configured.

Chairman order 2026-11-12 (Mastermind #983): every Macro LLM writer moves to the
Capacity Fabric unified_router. This writer is the mechanical batch annotator, so
it takes the ``fast`` lane. The cutover is env-gated and scoped to THIS writer:

  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_NEWS_LLM_FABRIC != "0"
    -> one fabric_client.complete(..., lane="fast") call per batch, no local retry;
  * not configured, or MACRO_NEWS_LLM_FABRIC=0
    -> the EXACT legacy ladder, byte-for-byte unchanged;
  * FabricUnavailable (nothing left the host) -> the unchanged legacy ladder;
  * any other router error -> degrade, never retry, never a second provider.

All stub-based: no network, no API keys, no sparse-omitted directory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import llm_auth as llm_auth_mod  # noqa: E402
from engine import news_llm  # noqa: E402
from lib import ai_costs as ai_costs_mod  # noqa: E402
from lib import fabric_client as fc  # noqa: E402

_CFG = {"enabled": True, "batch_size": 12, "max_batches": 12}

_ROWS = [
    {"i": 0, "summary": "Fed holds rates steady.", "importance": 88, "tone": "neutral"},
    {"i": 1, "summary": "NVDA beats on data-centre demand.", "importance": 72, "tone": "pos"},
]


class _Raw:
    def __init__(self, stop_reason="end_turn"):
        self.stop_reason = stop_reason


def _completion(text, model="deepseek-v4.1-flash", stop_reason="end_turn"):
    return fc.Completion(text=text, model_served=model, route_id="r-1",
                         provider="deepseek",
                         usage={"input_tokens": 40, "output_tokens": 12},
                         raw=_Raw(stop_reason))


def _headlines():
    return [
        {"title": "Fed holds rates steady", "summary": ""},
        {"title": "NVDA beats on data-centre demand", "summary": ""},
    ]


@pytest.fixture
def fabric_on(monkeypatch):
    """Router configured; record every complete() call; config enables the module."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return _completion(json.dumps(_ROWS))

    monkeypatch.setattr(news_llm, "_cfg", lambda: dict(_CFG))
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_NEWS_LLM_FABRIC", raising=False)
    return calls


@pytest.fixture
def fabric_off(monkeypatch):
    """Router NOT configured; legacy ladder stubbed to an empty provider list."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):   # must never be reached
        calls.append(kwargs)
        return _completion("should not happen")

    monkeypatch.setattr(news_llm, "_cfg", lambda: dict(_CFG))
    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.delenv("MACRO_NEWS_LLM_FABRIC", raising=False)
    return calls


# --------------------------------------------------------------------------- #
# configured -> fabric
# --------------------------------------------------------------------------- #
def test_configured_annotator_routes_to_fabric_fast(fabric_on):
    rows = _headlines()
    out = news_llm.annotate(rows)

    assert out is rows
    assert len(fabric_on) == 1
    call = fabric_on[0]
    assert call["lane"] == "fast"
    assert call["client"] == "Python client"
    assert call["project_id"] == "macro-dashboard"
    assert call["session_id"] == "macro-news-llm"
    assert call["system"] == news_llm.SYSTEM
    assert call["messages"][0]["role"] == "user"
    assert "HEADLINE: Fed holds rates steady" in call["messages"][0]["content"]
    # max_tokens preserves the legacy batch formula: min(4000, 90*n + 200)
    assert call["max_tokens"] == min(4000, 90 * 2 + 200)

    assert rows[0]["llm_importance"] == 88
    assert rows[0]["llm_tone"] == "neutral"
    assert rows[0]["summary"] == "Fed holds rates steady."
    assert rows[1]["llm_importance"] == 72
    assert rows[1]["llm_tone"] == "pos"


def test_fabric_served_usage_is_recorded_as_fabric(fabric_on, monkeypatch):
    recorded: list[dict] = []

    def fake_record(**kwargs):
        recorded.append(kwargs)
        return True

    monkeypatch.setattr(ai_costs_mod, "record_usage", fake_record)

    news_llm.annotate(_headlines())

    assert len(recorded) == 1
    row = recorded[0]
    assert row["provider"] == "fabric"
    assert row["model"] == "deepseek-v4.1-flash"
    assert row["lane"] == "fast"
    assert row["input_tokens"] == 40
    assert row["output_tokens"] == 12


def test_usage_record_failure_never_breaks_the_call(fabric_on, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("ledger is read-only")

    monkeypatch.setattr(ai_costs_mod, "record_usage", boom)

    rows = _headlines()
    news_llm.annotate(rows)
    assert rows[0]["llm_importance"] == 88      # enrichment still applied


# --------------------------------------------------------------------------- #
# refusal / empty -> the function's existing degraded shape, no retry
# --------------------------------------------------------------------------- #
def test_fabric_refusal_returns_no_enrichment(monkeypatch):
    calls: list[dict] = []

    def refusal(messages, **kwargs):
        calls.append(kwargs)
        return _completion("", stop_reason="refusal")

    monkeypatch.setattr(news_llm, "_cfg", lambda: dict(_CFG))
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", refusal)
    monkeypatch.delenv("MACRO_NEWS_LLM_FABRIC", raising=False)

    rows = _headlines()
    out = news_llm.annotate(rows)
    assert out is rows
    assert len(calls) == 1
    for h in rows:
        assert "llm_importance" not in h
        assert "llm_tone" not in h


def test_fabric_empty_reply_is_not_retried(monkeypatch):
    calls: list[dict] = []

    def empty(messages, **kwargs):
        calls.append(kwargs)
        return _completion("")

    monkeypatch.setattr(news_llm, "_cfg", lambda: dict(_CFG))
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", empty)
    monkeypatch.delenv("MACRO_NEWS_LLM_FABRIC", raising=False)

    rows = _headlines()
    news_llm.annotate(rows)
    assert len(calls) == 1
    for h in rows:
        assert "llm_importance" not in h


# --------------------------------------------------------------------------- #
# router error -> degrade, NO retry, NO second provider
# --------------------------------------------------------------------------- #
def test_router_error_degrades_without_retry(monkeypatch):
    calls: list[dict] = []

    def boom(messages, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("router exhausted its ladder")

    monkeypatch.setattr(news_llm, "_cfg", lambda: dict(_CFG))
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [{"name": "x"}])
    monkeypatch.setattr(llm_auth_mod, "make_call",
                        lambda *a, **kw: pytest.fail("legacy ladder must not run"))
    monkeypatch.delenv("MACRO_NEWS_LLM_FABRIC", raising=False)

    rows = _headlines()
    out = news_llm.annotate(rows)
    assert out is rows
    assert len(calls) == 1          # one call; the router owns fallback
    for h in rows:
        assert "llm_importance" not in h


# --------------------------------------------------------------------------- #
# router UNREACHABLE -> fall through to the unchanged legacy ladder
# --------------------------------------------------------------------------- #
def test_router_unavailable_falls_through_to_legacy_ladder(monkeypatch):
    calls: list[dict] = []

    def unavailable(messages, **kwargs):
        calls.append(kwargs)
        raise fc.FabricUnavailable("the anthropic SDK is not importable")

    legacy_calls: list[dict] = []

    def fake_make_call(providers, call_fn, **kwargs):
        legacy_calls.append(kwargs)
        return ({0: {"summary": "legacy", "importance": 10, "tone": "neg"}},
                None, "deepseek")

    monkeypatch.setattr(news_llm, "_cfg", lambda: dict(_CFG))
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", unavailable)
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [{"name": "x"}])
    monkeypatch.setattr(llm_auth_mod, "make_call", fake_make_call)
    monkeypatch.delenv("MACRO_NEWS_LLM_FABRIC", raising=False)

    rows = _headlines()
    news_llm.annotate(rows)
    assert len(calls) == 1                 # one fabric attempt, then the ladder
    assert len(legacy_calls) == 1          # the unchanged legacy path served
    assert rows[0]["llm_importance"] == 10
    assert rows[0]["summary"] == "legacy"


# --------------------------------------------------------------------------- #
# not configured / kill-switch -> legacy, unchanged
# --------------------------------------------------------------------------- #
def test_unconfigured_annotator_uses_legacy_ladder(fabric_off):
    rows = _headlines()
    out = news_llm.annotate(rows)
    assert out is rows
    assert fabric_off == []                # fabric never touched
    for h in rows:
        assert "llm_importance" not in h   # empty ladder -> pass-through


def test_kill_switch_forces_legacy_even_when_configured(monkeypatch):
    calls: list[dict] = []
    legacy_calls: list[dict] = []

    def fake_make_call(providers, call_fn, **kwargs):
        legacy_calls.append(kwargs)
        return ({0: {"summary": "legacy", "importance": 5, "tone": "neutral"}},
                None, "deepseek")

    monkeypatch.setattr(news_llm, "_cfg", lambda: dict(_CFG))
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [{"name": "x"}])
    monkeypatch.setattr(llm_auth_mod, "make_call", fake_make_call)
    monkeypatch.setenv("MACRO_NEWS_LLM_FABRIC", "0")

    rows = _headlines()
    news_llm.annotate(rows)
    assert calls == []                     # fabric never touched
    assert len(legacy_calls) == 1
    assert rows[0]["llm_importance"] == 5


def test_no_token_uses_legacy_ladder(monkeypatch):
    """No router token -> is_configured() False -> the legacy ladder, unchanged."""
    legacy_calls: list[dict] = []

    def fake_make_call(providers, call_fn, **kwargs):
        legacy_calls.append(kwargs)
        return ({0: {"summary": "legacy", "importance": 7, "tone": "pos"}},
                None, "deepseek")

    monkeypatch.setattr(news_llm, "_cfg", lambda: dict(_CFG))
    monkeypatch.delenv(fc.TOKEN_ENV, raising=False)
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [{"name": "x"}])
    monkeypatch.setattr(llm_auth_mod, "make_call", fake_make_call)
    monkeypatch.delenv("MACRO_NEWS_LLM_FABRIC", raising=False)

    rows = _headlines()
    news_llm.annotate(rows)
    assert len(legacy_calls) == 1
    assert rows[0]["llm_importance"] == 7


# --------------------------------------------------------------------------- #
# the gate itself
# --------------------------------------------------------------------------- #
def test_fabric_enabled_gate(monkeypatch):
    monkeypatch.delenv("MACRO_NEWS_LLM_FABRIC", raising=False)
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    assert news_llm._fabric_enabled() is True

    monkeypatch.setenv("MACRO_NEWS_LLM_FABRIC", "0")
    assert news_llm._fabric_enabled() is False

    monkeypatch.delenv("MACRO_NEWS_LLM_FABRIC", raising=False)
    monkeypatch.setattr(fc, "is_configured", lambda: False)
    assert news_llm._fabric_enabled() is False
