"""The per-stock catalyst writer routes through the Capacity Fabric when configured.

Chairman order 2026-11-12 (estate migration outcome #3): engine/catalyst_stock.py's
reasoning call replaces its legacy DeepSeek client with the unified_router. The
cutover is env-gated and scoped to this writer:

  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_CATALYST_STOCK_FABRIC != "0"
    -> one fabric_client.complete(..., lane="balanced") per logical call, no local
       retry, no second provider, and no legacy client construction;
  * not configured, or MACRO_CATALYST_STOCK_FABRIC=0
    -> the EXACT legacy client path, byte-for-byte unchanged;
  * FabricUnavailable (no request left the host) -> fall through to that path;
  * a served error -> degrade as (None, "llm_error") without retrying or falling
    through; a refusal drops even partial text; an empty reply is not retried.

All stub-based: no network, no API keys, no sparse-omitted directory.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import catalyst_stock as cs  # noqa: E402
from lib import ai_costs  # noqa: E402
from lib import fabric_client as fc  # noqa: E402


class _Raw:
    stop_reason = "end_turn"


class _RefusalRaw:
    stop_reason = "refusal"


class _TruncatedRaw:
    stop_reason = "max_tokens"


def _completion(text, model="glm-5.3", raw=None, usage=None):
    return fc.Completion(text=text, model_served=model, route_id="r-1",
                         provider="glm", usage=usage or {"output_tokens": 5},
                         raw=raw or _Raw())


class _LegacyResp:
    """Minimal anthropic-Messages-shaped reply for the legacy client stub."""

    def __init__(self, text, stop_reason="end_turn"):
        self.stop_reason = stop_reason
        self.content = [type("_B", (), {"type": "text", "text": text})()]


class _LegacyClient:
    def __init__(self, reply):
        self.calls: list[dict] = []
        self.messages = self
        self._reply = reply

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._reply


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
        return _completion('{"summary": "ok", "confidence": "low"}')

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_CATALYST_STOCK_FABRIC", raising=False)
    return calls


@pytest.fixture
def fabric_off(monkeypatch):
    """Router NOT configured; the legacy client is stubbed and observable."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):   # must never be reached
        calls.append(kwargs)
        return _completion("should not happen")

    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_CATALYST_STOCK_FABRIC", raising=False)
    return calls


CFG = {"llm_model": "deepseek-v4-pro", "max_tokens": 2000}


# --------------------------------------------------------------------------- #
# configured -> fabric on the balanced lane
# --------------------------------------------------------------------------- #
def test_configured_routes_to_fabric_balanced(fabric_on, monkeypatch):
    monkeypatch.setattr(cs, "_client",
                        lambda cfg: pytest.fail("legacy client must not be built"))

    text, reason = cs._call_model("SYS", "USER", dict(CFG))

    assert (text, reason) == ('{"summary": "ok", "confidence": "low"}', None)
    assert len(fabric_on) == 1
    call = fabric_on[0]
    assert call["lane"] == "balanced"
    assert call["client"] == "Python client"
    assert call["project_id"] == "macro-dashboard"
    assert call["session_id"] == "macro-catalyst-stock"
    assert call["max_tokens"] == 2000
    assert call["system"] == "SYS"
    assert call["messages"] == [{"role": "user", "content": "USER"}]


def test_brief_for_ticker_serves_from_fabric(fabric_on, monkeypatch):
    """The public writer site (brief_for_ticker -> _call_model) uses the router."""
    monkeypatch.setattr(cs, "_client",
                        lambda cfg: pytest.fail("legacy client must not be built"))
    monkeypatch.setattr(cs, "_cfg", lambda: {**CFG, "enabled": True})
    monkeypatch.setattr(cs, "assemble_context",
                        lambda ticker, root: {"identity": {"name": "Apple", "asof": "2026-06-12"}})
    monkeypatch.setattr(cs, "news_digest", lambda *a, **kw: None)
    monkeypatch.setattr(cs, "_translate_brief", lambda brief, cfg: None)

    brief = cs.brief_for_ticker("AAPL")

    assert brief["summary"] == "ok"
    assert brief["degraded_reason"] is None
    assert len(fabric_on) == 1


def test_fabric_truncation_reason_is_preserved(monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion("partial", raw=_TruncatedRaw()))
    monkeypatch.delenv("MACRO_CATALYST_STOCK_FABRIC", raising=False)

    assert cs._call_model("SYS", "USER", dict(CFG)) == ("partial", "truncated")


# --------------------------------------------------------------------------- #
# ledger continuity: provider="fabric" + the served model
# --------------------------------------------------------------------------- #
def test_fabric_success_books_usage_row(monkeypatch, ledger_rows):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", lambda messages, **kw: _completion(
        "ok", model="deepseek-v4.1-pro", usage={
            "input_tokens": 123, "output_tokens": 45,
            "cache_read_input_tokens": 7, "cache_creation_input_tokens": 8}))
    monkeypatch.delenv("MACRO_CATALYST_STOCK_FABRIC", raising=False)

    cs._call_model("SYS", "USER", dict(CFG))

    assert len(ledger_rows) == 1
    row = ledger_rows[0]
    assert row["lane"] == "catalyst-stock"
    assert row["provider"] == "fabric"
    assert row["model"] == "deepseek-v4.1-pro"
    assert row["input_tokens"] == 123 and row["output_tokens"] == 45
    assert row["cache_read_tokens"] == 7 and row["cache_creation_tokens"] == 8
    assert row["stage"] == "catalyst_stock"


def test_ledger_failure_never_breaks_a_served_call(monkeypatch):
    def boom(**kw):
        raise RuntimeError("ledger disk full")

    monkeypatch.setattr(ai_costs, "record_usage", boom)
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", lambda messages, **kw: _completion("ok"))
    monkeypatch.delenv("MACRO_CATALYST_STOCK_FABRIC", raising=False)

    assert cs._call_model("SYS", "USER", dict(CFG)) == ("ok", None)


# --------------------------------------------------------------------------- #
# not configured / kill-switch -> legacy, unchanged
# --------------------------------------------------------------------------- #
def test_unconfigured_uses_legacy_client(monkeypatch, fabric_off):
    legacy = _LegacyClient(_LegacyResp("legacy reply"))
    monkeypatch.setattr(cs, "_client", lambda cfg: legacy)

    assert cs._call_model("SYS", "USER", dict(CFG)) == ("legacy reply", None)
    assert fabric_off == []                 # fabric never touched
    assert len(legacy.calls) == 1
    assert legacy.calls[0]["model"] == "deepseek-v4-pro"
    assert legacy.calls[0]["max_tokens"] == 2000
    assert legacy.calls[0]["system"] == "SYS"


def test_unconfigured_legacy_no_client_reason(monkeypatch, fabric_off):
    monkeypatch.setattr(cs, "_client", lambda cfg: None)

    assert cs._call_model("SYS", "USER", dict(CFG)) == (None, "no_client_or_key")
    assert fabric_off == []


def test_kill_switch_forces_legacy_even_when_configured(monkeypatch):
    calls: list[dict] = []
    legacy = _LegacyClient(_LegacyResp("legacy reply"))
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setattr(cs, "_client", lambda cfg: legacy)
    monkeypatch.setenv("MACRO_CATALYST_STOCK_FABRIC", "0")

    assert cs._call_model("SYS", "USER", dict(CFG)) == ("legacy reply", None)
    assert calls == []
    assert len(legacy.calls) == 1


# --------------------------------------------------------------------------- #
# router UNREACHABLE -> fall through to legacy, never blank the brief
# --------------------------------------------------------------------------- #
def test_router_unavailable_falls_through_to_legacy(monkeypatch):
    calls: list[dict] = []

    def unavailable(messages, **kwargs):
        calls.append(kwargs)
        raise fc.FabricUnavailable("the anthropic SDK is not importable")

    legacy = _LegacyClient(_LegacyResp("legacy reply"))
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", unavailable)
    monkeypatch.setattr(cs, "_client", lambda cfg: legacy)
    monkeypatch.delenv("MACRO_CATALYST_STOCK_FABRIC", raising=False)

    assert cs._call_model("SYS", "USER", dict(CFG)) == ("legacy reply", None)
    assert len(calls) == 1                  # one fabric attempt, then the legacy path
    assert len(legacy.calls) == 1


def test_router_unavailable_and_no_legacy_client(monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: (_ for _ in ()).throw(fc.FabricUnavailable("no sdk")))
    monkeypatch.setattr(cs, "_client", lambda cfg: None)
    monkeypatch.delenv("MACRO_CATALYST_STOCK_FABRIC", raising=False)

    assert cs._call_model("SYS", "USER", dict(CFG)) == (None, "no_client_or_key")


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
    monkeypatch.setattr(cs, "_client",
                        lambda cfg: pytest.fail("legacy client must not run"))
    monkeypatch.delenv("MACRO_CATALYST_STOCK_FABRIC", raising=False)

    assert cs._call_model("SYS", "USER", dict(CFG)) == (None, "llm_error")
    assert len(calls) == 1


def test_refusal_drops_partial_text(monkeypatch, ledger_rows):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion('{"partial": true}', raw=_RefusalRaw()))
    monkeypatch.delenv("MACRO_CATALYST_STOCK_FABRIC", raising=False)

    assert cs._call_model("SYS", "USER", dict(CFG)) == (None, "refusal")
    assert ledger_rows == []


def test_empty_reply_is_not_retried(monkeypatch, ledger_rows):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion(""))
    monkeypatch.setattr(cs, "_client",
                        lambda cfg: pytest.fail("legacy client must not run"))
    monkeypatch.delenv("MACRO_CATALYST_STOCK_FABRIC", raising=False)

    assert cs._call_model("SYS", "USER", dict(CFG)) == (None, "empty_reply")
    assert len(calls) == 1
    assert ledger_rows == []
