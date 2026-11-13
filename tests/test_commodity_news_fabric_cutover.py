"""The commodity-news cause classifier routes through the Capacity Fabric.

Estate AI-routing migration (Mastermind #983). The cutover is env-gated and
scoped to this writer's own call site in ``engine/commodity_news.py``:

  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_COMMODITY_NEWS_FABRIC != "0"
    -> ONE fabric_client.complete(..., lane="fast") call, no local retry;
  * not configured, or MACRO_COMMODITY_NEWS_FABRIC=0
    -> the EXACT legacy llm_auth ladder, byte-for-byte unchanged;
  * FabricUnavailable (no token / SDK will not import) -> the legacy ladder,
    because no request ever left this host;
  * any OTHER exception -> the existing degraded return, one attempt only.

All stub-based: no network, no API keys, no sparse-omitted directory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import commodity_news as cn  # noqa: E402
from engine import llm_auth as llm_auth_mod  # noqa: E402
from lib import ai_costs as ai_costs_mod  # noqa: E402
from lib import fabric_client as fc  # noqa: E402

_CFG = {"llm_classify": True, "llm_model": "claude-haiku-4-5",
        "llm_min_confidence": "high"}

_HEADLINES = [
    {"title": "OPEC agrees output cut", "url": "https://example.test/a",
     "domain": "example.test", "seendate": "2026-11-10T12:00:00Z",
     "language": "eng", "sourcecountry": "US"},
]

_CLEAN_REPLY = {
    "evidence": "OPEC agrees output cut",
    "cause": "ofac_opec_or_cartel_action",
    "confidence": "high",
}


class _Raw:
    def __init__(self, stop_reason="end_turn"):
        self.stop_reason = stop_reason


def _completion(text, model="deepseek-v4.1-flash", stop_reason="end_turn"):
    return fc.Completion(text=text, model_served=model, route_id="r-1",
                         provider="deepseek",
                         usage={"input_tokens": 120, "output_tokens": 30},
                         raw=_Raw(stop_reason))


@pytest.fixture(autouse=True)
def usage_rows(monkeypatch):
    """Capture ledger rows without ever writing the repo's real data/ tree."""
    rows: list[dict] = []

    def fake_record_usage(**kwargs):
        rows.append(kwargs)
        return True

    monkeypatch.setattr(ai_costs_mod, "record_usage", fake_record_usage)
    return rows


@pytest.fixture
def fabric_on(monkeypatch):
    """Router configured; record every complete() call."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return _completion(json.dumps(_CLEAN_REPLY))

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_COMMODITY_NEWS_FABRIC", raising=False)
    monkeypatch.delenv("DISABLE_COMMODITY_NEWS_LLM", raising=False)
    return calls


@pytest.fixture
def legacy_stub(monkeypatch):
    """Legacy ladder stubbed; returns the list of make_call invocations."""
    seen: list[dict] = []

    def fake_make_call(providers, call_fn, **kwargs):
        seen.append({"providers": providers, "context": kwargs.get("context")})
        return json.dumps(_CLEAN_REPLY), None, "anthropic"

    monkeypatch.setattr(llm_auth_mod, "build_providers",
                        lambda *a, **kw: [{"name": "anthropic"}])
    monkeypatch.setattr(llm_auth_mod, "make_call", fake_make_call)
    monkeypatch.delenv("DISABLE_COMMODITY_NEWS_LLM", raising=False)
    return seen


# --------------------------------------------------------------------------- #
# configured -> fabric
# --------------------------------------------------------------------------- #
def test_configured_classifier_routes_to_fabric_fast(fabric_on):
    parsed, reason = cn._classify_cause("oil", "moved -4%", _HEADLINES, dict(_CFG))
    assert reason is None
    assert parsed["cause"] == _CLEAN_REPLY["cause"]
    assert len(fabric_on) == 1
    call = fabric_on[0]
    assert call["lane"] == "fast"
    assert call["client"] == "Python client"
    assert call["project_id"] == "macro-dashboard"
    assert call["session_id"] == "macro-commodity-news"
    assert call["system"].startswith(cn.CLASSIFY_SYSTEM)
    assert "JSON" in call["system"]          # schema stated in-prompt (no output_config)
    assert "ofac_opec_or_cartel_action" in call["system"]
    assert call["max_tokens"] == 256
    assert call["messages"][0]["role"] == "user"
    assert "OPEC agrees output cut" in call["messages"][0]["content"]


def test_legacy_system_prompt_is_unchanged(fabric_on):
    """The fabric schema hint must NOT leak into the legacy ladder's prompt."""
    assert "JSON" not in cn.CLASSIFY_SYSTEM
    assert cn._FABRIC_SYSTEM.startswith(cn.CLASSIFY_SYSTEM)


def test_fabric_reply_records_served_model(fabric_on):
    parsed, reason = cn._classify_cause("oil", "moved -4%", _HEADLINES, dict(_CFG))
    assert reason is None
    assert parsed["model"] == "deepseek-v4.1-flash"
    assert parsed["applied_threshold"] == "high"


def test_fabric_usage_is_recorded_as_fabric_provider(fabric_on, usage_rows):
    cn._classify_cause("oil", "moved -4%", _HEADLINES, dict(_CFG))

    assert len(usage_rows) == 1
    assert usage_rows[0]["provider"] == "fabric"
    assert usage_rows[0]["lane"] == "fast"
    assert usage_rows[0]["model"] == "deepseek-v4.1-flash"
    assert usage_rows[0]["input_tokens"] == 120
    assert usage_rows[0]["output_tokens"] == 30


def test_usage_recording_failure_never_breaks_the_call(fabric_on, monkeypatch):
    """A raising recorder must not break a served call (telemetry only)."""

    def boom(**kw):
        raise RuntimeError("ledger is read-only")

    monkeypatch.setattr(ai_costs_mod, "record_usage", boom)

    parsed, reason = cn._classify_cause("oil", "moved -4%", _HEADLINES, dict(_CFG))
    assert reason is None and parsed["cause"] == _CLEAN_REPLY["cause"]


def test_confidence_gate_still_applies_on_fabric(monkeypatch):
    low = {**_CLEAN_REPLY, "confidence": "low"}
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: _completion(json.dumps(low)))
    monkeypatch.delenv("MACRO_COMMODITY_NEWS_FABRIC", raising=False)

    parsed, reason = cn._classify_cause("oil", "moved -4%", _HEADLINES, dict(_CFG))
    assert reason is None
    assert parsed["cause"] == "unknown"      # code-side gate, not the prompt


# --------------------------------------------------------------------------- #
# refusal / empty -> the existing degraded shapes, never retried
# --------------------------------------------------------------------------- #
def test_fabric_refusal_returns_refusal_shape(monkeypatch):
    calls: list[dict] = []

    def refusal(messages, **kwargs):
        calls.append(kwargs)
        return _completion("", stop_reason="refusal")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", refusal)
    monkeypatch.delenv("MACRO_COMMODITY_NEWS_FABRIC", raising=False)

    parsed, reason = cn._classify_cause("oil", "moved -4%", _HEADLINES, dict(_CFG))
    assert parsed is None and reason == "llm_refusal"
    assert len(calls) == 1


def test_fabric_empty_reply_is_not_retried(monkeypatch):
    calls: list[dict] = []

    def empty(messages, **kwargs):
        calls.append(kwargs)
        return _completion("")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", empty)
    monkeypatch.delenv("MACRO_COMMODITY_NEWS_FABRIC", raising=False)

    parsed, reason = cn._classify_cause("oil", "moved -4%", _HEADLINES, dict(_CFG))
    assert parsed is None and reason == "llm_error"
    assert len(calls) == 1


def test_fabric_non_json_reply_degrades(monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: _completion("not json at all"))
    monkeypatch.delenv("MACRO_COMMODITY_NEWS_FABRIC", raising=False)

    parsed, reason = cn._classify_cause("oil", "moved -4%", _HEADLINES, dict(_CFG))
    assert parsed is None and reason == "llm_error"


def test_fabric_non_object_json_reply_degrades_without_raising(monkeypatch):
    """Valid JSON that is not an object must degrade, not raise into the
    pipeline — this module's standing contract is that it never raises."""
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: _completion("[1, 2, 3]"))
    monkeypatch.delenv("MACRO_COMMODITY_NEWS_FABRIC", raising=False)

    parsed, reason = cn._classify_cause("oil", "moved -4%", _HEADLINES, dict(_CFG))
    assert parsed is None and reason == "llm_error"


# --------------------------------------------------------------------------- #
# router-down (a SERVED failure) -> degrade, one attempt, no legacy call
# --------------------------------------------------------------------------- #
def test_served_error_degrades_without_retry_or_legacy(monkeypatch):
    calls: list[dict] = []

    def boom(messages, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("router exhausted its ladder")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)
    monkeypatch.setattr(llm_auth_mod, "build_providers",
                        lambda *a, **kw: pytest.fail("legacy ladder must not run"))
    monkeypatch.delenv("MACRO_COMMODITY_NEWS_FABRIC", raising=False)

    parsed, reason = cn._classify_cause("oil", "moved -4%", _HEADLINES, dict(_CFG))
    assert parsed is None and reason == "llm_error"
    assert len(calls) == 1          # one call; the router owns fallback


# --------------------------------------------------------------------------- #
# router UNREACHABLE -> fall through to the unchanged legacy ladder
# --------------------------------------------------------------------------- #
def test_router_unavailable_falls_through_to_legacy(monkeypatch, legacy_stub):
    calls: list[dict] = []

    def unavailable(messages, **kwargs):
        calls.append(kwargs)
        raise fc.FabricUnavailable("the anthropic SDK is not importable")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", unavailable)
    monkeypatch.delenv("MACRO_COMMODITY_NEWS_FABRIC", raising=False)

    parsed, reason = cn._classify_cause("oil", "moved -4%", _HEADLINES, dict(_CFG))
    assert reason is None
    assert parsed["cause"] == _CLEAN_REPLY["cause"]
    assert parsed["model"] == "claude-haiku-4-5"   # the legacy model, not fabric
    assert len(calls) == 1                          # one fabric attempt, then legacy
    assert len(legacy_stub) == 1
    assert legacy_stub[0]["context"] == "commodity_news"


# --------------------------------------------------------------------------- #
# not configured / kill-switch -> legacy, unchanged
# --------------------------------------------------------------------------- #
def test_unconfigured_uses_legacy_ladder(monkeypatch, legacy_stub):
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):   # must never be reached
        calls.append(kwargs)
        return _completion("should not happen")

    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_COMMODITY_NEWS_FABRIC", raising=False)

    parsed, reason = cn._classify_cause("oil", "moved -4%", _HEADLINES, dict(_CFG))
    assert reason is None and parsed["cause"] == _CLEAN_REPLY["cause"]
    assert calls == []                 # fabric never touched
    assert len(legacy_stub) == 1


def test_kill_switch_forces_legacy_even_when_configured(monkeypatch, legacy_stub):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setenv("MACRO_COMMODITY_NEWS_FABRIC", "0")

    parsed, reason = cn._classify_cause("oil", "moved -4%", _HEADLINES, dict(_CFG))
    assert reason is None and parsed["cause"] == _CLEAN_REPLY["cause"]
    assert calls == []
    assert len(legacy_stub) == 1


def test_kill_switch_accepts_any_non_zero_value(monkeypatch, legacy_stub):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion(
                            json.dumps(_CLEAN_REPLY)))
    monkeypatch.setenv("MACRO_COMMODITY_NEWS_FABRIC", "1")

    cn._classify_cause("oil", "moved -4%", _HEADLINES, dict(_CFG))
    assert len(calls) == 1
    assert legacy_stub == []


# --------------------------------------------------------------------------- #
# the pre-existing gates still win over the fabric branch
# --------------------------------------------------------------------------- #
def test_classifier_disabled_never_touches_fabric(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.delenv("MACRO_COMMODITY_NEWS_FABRIC", raising=False)

    parsed, reason = cn._classify_cause("oil", "moved -4%", _HEADLINES,
                                        {**_CFG, "llm_classify": False})
    assert (parsed, reason) == (None, None)
    assert calls == []


def test_disable_env_never_touches_fabric(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.delenv("MACRO_COMMODITY_NEWS_FABRIC", raising=False)
    monkeypatch.setenv("DISABLE_COMMODITY_NEWS_LLM", "1")

    parsed, reason = cn._classify_cause("oil", "moved -4%", _HEADLINES, dict(_CFG))
    assert (parsed, reason) == (None, None)
    assert calls == []


def test_no_headlines_never_touches_fabric(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.delenv("MACRO_COMMODITY_NEWS_FABRIC", raising=False)

    parsed, reason = cn._classify_cause("oil", "moved -4%", [], dict(_CFG))
    assert (parsed, reason) == (None, None)
    assert calls == []
