"""The White House brain routes through the Capacity Fabric when configured.

Chairman order 2026-11-12: all estate AI routing moves to the unified_router, so
this writer takes a fabric branch at its own call site, ahead of the legacy
DeepSeek/OAuth ladder. The cutover is env-gated:

  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_WHITEHOUSE_FABRIC != "0"
    -> one fabric_client.complete(..., lane="fast") call, no local retry;
  * not configured, or MACRO_WHITEHOUSE_FABRIC=0
    -> the EXACT legacy ladder, byte-for-byte unchanged;
  * FabricUnavailable (no token after all, or the SDK will not import) means no
    request ever left the host, so the caller runs the legacy ladder rather than
    blanking the alert; any OTHER served error degrades without a retry.

All stub-based: no network, no API keys, no sparse-omitted directory.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import llm_auth as llm_auth_mod  # noqa: E402
from engine import whitehouse_brain as wb  # noqa: E402
from lib import ai_costs as ai_costs_mod  # noqa: E402
from lib import fabric_client as fc  # noqa: E402

_CFG = dict(wb._DEFAULTS)


class _Raw:
    def __init__(self, stop_reason="end_turn"):
        self.stop_reason = stop_reason


def _completion(text, model="deepseek-v4.1-flash", stop_reason="end_turn"):
    return fc.Completion(text=text, model_served=model, route_id="r-1",
                         provider="deepseek", usage={"output_tokens": 5},
                         raw=_Raw(stop_reason))


@pytest.fixture(autouse=True)
def usage_rows(monkeypatch):
    """Capture ai_costs.record_usage rows without touching the real ledger.

    Autouse: a fabric-served call records usage, and a test that let that reach
    lib.ai_costs would append to the repo's real data/ai_costs/usage.jsonl.
    """
    rows: list[dict] = []
    monkeypatch.setattr(ai_costs_mod, "record_usage",
                        lambda **kw: rows.append(kw) or True)
    return rows


@pytest.fixture
def fabric_on(monkeypatch):
    """Router configured; record every complete() call."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return _completion('{"activate": false, "importance": 10}')

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_WHITEHOUSE_FABRIC", raising=False)
    return calls


# --------------------------------------------------------------------------- #
# configured -> fabric fast lane
# --------------------------------------------------------------------------- #
def test_configured_routes_to_fabric_fast(fabric_on):
    text, reason = wb._call_model("sys", "user", _CFG)
    assert reason == "fabric"
    assert text == '{"activate": false, "importance": 10}'
    assert len(fabric_on) == 1
    call = fabric_on[0]
    assert call["lane"] == "fast"
    assert call["client"] == "Python client"
    assert call["project_id"] == "macro-dashboard"
    assert call["session_id"] == "macro-whitehouse-brain"
    assert call["system"] == "sys"
    assert call["messages"] == [{"role": "user", "content": "user"}]
    assert call["max_tokens"] == 4000


def test_configured_preserves_configured_max_tokens(monkeypatch):
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return _completion("ok")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_WHITEHOUSE_FABRIC", raising=False)

    wb._call_model("sys", "user", {**_CFG, "max_tokens": 1234})
    assert calls[0]["max_tokens"] == 1234


def test_configured_records_fabric_usage(fabric_on, usage_rows):
    wb._call_model("sys", "user", _CFG)
    assert len(usage_rows) == 1
    row = usage_rows[0]
    assert row["provider"] == "fabric"
    assert row["model"] == "deepseek-v4.1-flash"
    assert row["lane"] == "fast"


def test_usage_record_failure_never_breaks_a_served_call(fabric_on, monkeypatch):
    def boom(**kw):
        raise RuntimeError("ledger unavailable")

    monkeypatch.setattr(ai_costs_mod, "record_usage", boom)
    text, reason = wb._call_model("sys", "user", _CFG)
    assert text and reason == "fabric"


def test_served_model_is_reported_not_the_lane(monkeypatch):
    """The ledger keeps the router's served model — that is the cost truth."""
    rows: list[dict] = []
    monkeypatch.setattr(ai_costs_mod, "record_usage",
                        lambda **kw: rows.append(kw) or True)
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: _completion("ok", model="glm-5.3"))
    monkeypatch.delenv("MACRO_WHITEHOUSE_FABRIC", raising=False)

    wb._call_model("sys", "user", _CFG)
    assert rows[0]["model"] == "glm-5.3"


# --------------------------------------------------------------------------- #
# refusal / empty / served error -> degrade, never retry
# --------------------------------------------------------------------------- #
def test_refusal_returns_refusal_before_text(monkeypatch):
    calls: list[dict] = []

    def refusing(messages, **kwargs):
        calls.append(kwargs)
        return _completion("partial text", stop_reason="refusal")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", refusing)
    monkeypatch.delenv("MACRO_WHITEHOUSE_FABRIC", raising=False)

    text, reason = wb._call_model("sys", "user", _CFG)
    assert (text, reason) == (None, "refusal")
    assert len(calls) == 1


def test_empty_reply_is_not_retried(monkeypatch):
    calls: list[dict] = []

    def empty(messages, **kwargs):
        calls.append(kwargs)
        return _completion("")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", empty)
    monkeypatch.delenv("MACRO_WHITEHOUSE_FABRIC", raising=False)

    text, reason = wb._call_model("sys", "user", _CFG)
    assert (text, reason) == (None, "empty_reply")
    assert len(calls) == 1


def test_router_down_degrades_without_retry(monkeypatch):
    """Only FabricUnavailable falls through. Any other served error means the
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
    monkeypatch.delenv("MACRO_WHITEHOUSE_FABRIC", raising=False)

    text, reason = wb._call_model("sys", "user", _CFG)
    assert (text, reason) == (None, "llm_error")
    assert len(calls) == 1


# --------------------------------------------------------------------------- #
# FabricUnavailable -> legacy ladder, unchanged
# --------------------------------------------------------------------------- #
def test_router_unavailable_falls_through_to_legacy_ladder(monkeypatch):
    calls: list[dict] = []

    def unavailable(messages, **kwargs):
        calls.append(kwargs)
        raise fc.FabricUnavailable("the anthropic SDK is not importable")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", unavailable)
    monkeypatch.setattr(llm_auth_mod, "build_providers",
                        lambda *a, **kw: [{"name": "deepseek", "model": "deepseek-v4-pro"}])
    monkeypatch.setattr(llm_auth_mod, "make_call",
                        lambda *a, **kw: ("legacy reply", None, "deepseek"))
    monkeypatch.setattr(wb, "_wh_reply_cache_get", lambda *a, **kw: None)
    monkeypatch.setattr(wb, "_wh_reply_cache_put", lambda *a, **kw: None)
    monkeypatch.delenv("MACRO_WHITEHOUSE_FABRIC", raising=False)

    text, reason = wb._call_model("sys", "user", _CFG)
    assert (text, reason) == ("legacy reply", None)
    assert len(calls) == 1                # one fabric attempt, then the ladder


def test_router_unavailable_empty_ladder_reports_legacy_reason(monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: (_ for _ in ()).throw(fc.FabricUnavailable("no sdk")))
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.delenv("MACRO_WHITEHOUSE_FABRIC", raising=False)

    text, reason = wb._call_model("sys", "user", _CFG)
    # The legacy diagnosis, not "llm_error": the fabric path was never reached.
    assert (text, reason) == (None, "no_provider")


# --------------------------------------------------------------------------- #
# not configured / kill-switch -> legacy, unchanged
# --------------------------------------------------------------------------- #
def test_unconfigured_uses_legacy_ladder(monkeypatch):
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):   # must never be reached
        calls.append(kwargs)
        return _completion("should not happen")

    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.delenv("MACRO_WHITEHOUSE_FABRIC", raising=False)

    text, reason = wb._call_model("sys", "user", _CFG)
    assert (text, reason) == (None, "no_provider")
    assert calls == []                    # fabric never touched


def test_kill_switch_forces_legacy_even_when_configured(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.setenv("MACRO_WHITEHOUSE_FABRIC", "0")

    text, reason = wb._call_model("sys", "user", _CFG)
    assert (text, reason) == (None, "no_provider")
    assert calls == []


def test_kill_switch_other_value_keeps_fabric_on(fabric_on, monkeypatch):
    monkeypatch.setenv("MACRO_WHITEHOUSE_FABRIC", "1")
    text, reason = wb._call_model("sys", "user", _CFG)
    assert reason == "fabric"
    assert len(fabric_on) == 1


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
