"""The Narrative Brain writer routes through the Capacity Fabric when configured.

Chairman order 2026-11-12 (estate migration outcome #3): the narrative rotation
writer replaces its legacy OAuth/API ladder with the unified_router. The cutover
is env-gated and scoped to this writer:

  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_NARRATIVE_BRAIN_FABRIC != "0"
    -> one fabric_client.complete(..., lane="balanced") per logical call, no local
       retry, no second provider, and no llm_auth.build_providers() invocation;
  * not configured, or MACRO_NARRATIVE_BRAIN_FABRIC=0
    -> the EXACT legacy ladder, byte-for-byte unchanged;
  * FabricUnavailable (no request left the host) -> fall through to that ladder;
  * a served error -> degrade as (None, "llm_error") without retrying or falling
    through; a refusal drops even partial text.

All stub-based: no network, no API keys, no sparse-omitted directory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import llm_auth as llm_auth_mod  # noqa: E402
from engine import narrative_brain as nb  # noqa: E402
from lib import ai_costs  # noqa: E402
from lib import fabric_client as fc  # noqa: E402


class _Raw:
    stop_reason = "end_turn"


class _RefusalRaw:
    stop_reason = "refusal"


def _completion(text, model="glm-5.3", raw=None, usage=None):
    return fc.Completion(text=text, model_served=model, route_id="r-1",
                         provider="glm", usage=usage or {"output_tokens": 5},
                         raw=raw or _Raw())


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
        return _completion('{"ok": true}')

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_NARRATIVE_BRAIN_FABRIC", raising=False)
    return calls


@pytest.fixture
def fabric_off(monkeypatch):
    """Router NOT configured; the legacy ladder is stubbed to an empty list."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):   # must never be reached
        calls.append(kwargs)
        return _completion("should not happen")

    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.delenv("MACRO_NARRATIVE_BRAIN_FABRIC", raising=False)
    return calls


# --------------------------------------------------------------------------- #
# configured -> fabric, both tiers on the balanced lane
# --------------------------------------------------------------------------- #
def test_configured_routes_both_tiers_to_fabric_balanced(fabric_on, monkeypatch):
    monkeypatch.setattr(llm_auth_mod, "build_providers",
                        lambda *a, **kw: pytest.fail("legacy ladder must not run"))

    call = nb._make_call(dict(nb._DEFAULTS))
    durability, r1 = call("claude-sonnet-4-6", "durability sys", "theme pack")
    rotation, r2 = call("claude-opus-4-8", "rotation sys", "radar flags")

    assert (durability, r1) == ('{"ok": true}', None)
    assert (rotation, r2) == ('{"ok": true}', None)
    assert len(fabric_on) == 2
    for c in fabric_on:
        assert c["lane"] == "balanced"
        assert c["client"] == "Python client"
        assert c["project_id"] == "macro-dashboard"
        assert c["session_id"] == "macro-narrative-brain"
        assert c["max_tokens"] == 6000
        assert c["messages"][0]["role"] == "user"
    assert fabric_on[0]["system"] == "durability sys"
    assert fabric_on[1]["system"] == "rotation sys"


def test_synthesize_routes_through_fabric(fabric_on, monkeypatch):
    """The writer site (synthesize -> _make_call) serves from the router."""
    def fake_complete(messages, **kwargs):
        fabric_on.append({"messages": messages, **kwargs})
        if "durability" in (kwargs.get("system") or "").lower():
            return _completion(json.dumps({
                "strength": 80, "durability": 75, "continuity": 70, "composite": 75,
                "verdict": "ENTER", "confidence": "MED",
                "rationale": "activity leads [P2]", "evidence_ids": ["P2"],
                "dissent": "one-off", "falsifiable_check": {"confirm": "x", "disconfirm": "y"}}))
        return _completion(json.dumps({
            "summary": "defense leads", "accumulate": ["defense"], "reduce": [],
            "watch": [], "confidence": "MED"}))

    monkeypatch.setattr(fc, "complete", fake_complete)
    ev = {"as_of": "2026-06-19", "region": "us", "themes": [
        {"basket": "defense", "name": "Defense", "name_zh": "国防", "category": "x",
         "state": "POSITIVE_DIVERGENCE", "lifecycle": "emerging",
         "evidence": [{"id": "P2", "text": "divergence z=1.8"}]}]}
    out = nb.synthesize(ev, {**nb._DEFAULTS, "max_themes": 1})
    assert out["assessments"][0]["verdict"] == "ENTER"
    assert out["rotation"]["accumulate"] == ["defense"]
    assert len(fabric_on) == 2       # one durability + one rotation


def test_fabric_success_books_usage_row(fabric_on, ledger_rows, monkeypatch):
    def fake_complete(messages, **kwargs):
        fabric_on.append({"messages": messages, **kwargs})
        return _completion("ok", model="deepseek-v4.1-flash", usage={
            "input_tokens": 123, "output_tokens": 45,
            "cache_read_input_tokens": 7, "cache_creation_input_tokens": 8})

    monkeypatch.setattr(fc, "complete", fake_complete)
    nb._fabric_call(dict(nb._DEFAULTS))("claude-opus-4-8", "sys", "user")
    assert len(ledger_rows) == 1
    row = ledger_rows[0]
    assert row["lane"] == "narrative-brain"
    assert row["provider"] == "fabric"
    assert row["model"] == "deepseek-v4.1-flash"
    assert row["input_tokens"] == 123 and row["output_tokens"] == 45
    assert row["cache_read_tokens"] == 7 and row["cache_creation_tokens"] == 8
    assert row["stage"] == "narrative_brain"


# --------------------------------------------------------------------------- #
# not configured / kill-switch -> legacy, unchanged
# --------------------------------------------------------------------------- #
def test_unconfigured_uses_legacy_ladder(fabric_off):
    assert nb._make_call(dict(nb._DEFAULTS)) is None
    assert fabric_off == []          # fabric never touched


def test_kill_switch_forces_legacy_even_when_configured(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.setenv("MACRO_NARRATIVE_BRAIN_FABRIC", "0")

    assert nb._make_call(dict(nb._DEFAULTS)) is None
    assert calls == []


# --------------------------------------------------------------------------- #
# router UNREACHABLE -> fall through to legacy, never blank the writer
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
    monkeypatch.delenv("MACRO_NARRATIVE_BRAIN_FABRIC", raising=False)

    call = nb._make_call(dict(nb._DEFAULTS))
    assert call("claude-opus-4-8", "sys", "user") == ("legacy reply", None)
    assert len(calls) == 1           # one fabric attempt, then the ladder


def test_router_unavailable_empty_ladder_reports_legacy_reason(monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: (_ for _ in ()).throw(fc.FabricUnavailable("no sdk")))
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.delenv("MACRO_NARRATIVE_BRAIN_FABRIC", raising=False)

    call = nb._make_call(dict(nb._DEFAULTS))
    assert call("claude-opus-4-8", "sys", "user") == (None, "no_client_or_key")


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
    monkeypatch.setattr(llm_auth_mod, "build_providers",
                        lambda *a, **kw: pytest.fail("legacy ladder must not run"))
    monkeypatch.delenv("MACRO_NARRATIVE_BRAIN_FABRIC", raising=False)

    call = nb._make_call(dict(nb._DEFAULTS))
    assert call("claude-opus-4-8", "sys", "user") == (None, "llm_error")
    assert len(calls) == 1


def test_refusal_drops_partial_text(monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion('{"partial": true}', raw=_RefusalRaw()))
    monkeypatch.delenv("MACRO_NARRATIVE_BRAIN_FABRIC", raising=False)

    call = nb._make_call(dict(nb._DEFAULTS))
    assert call("claude-opus-4-8", "sys", "user") == (None, "refusal")


def test_refusal_books_no_usage_row(monkeypatch, ledger_rows):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion("partial", raw=_RefusalRaw()))
    monkeypatch.delenv("MACRO_NARRATIVE_BRAIN_FABRIC", raising=False)

    nb._make_call(dict(nb._DEFAULTS))("claude-opus-4-8", "sys", "user")
    assert ledger_rows == []


def test_empty_reply_is_not_retried(monkeypatch, ledger_rows):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion(""))
    monkeypatch.delenv("MACRO_NARRATIVE_BRAIN_FABRIC", raising=False)

    call = nb._make_call(dict(nb._DEFAULTS))
    assert call("claude-opus-4-8", "sys", "user") == (None, "empty_reply")
    assert len(calls) == 1
    assert ledger_rows == []
