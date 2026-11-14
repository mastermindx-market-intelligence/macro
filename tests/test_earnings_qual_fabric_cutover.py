"""The earnings-qual scorer routes through the Capacity Fabric when configured.

Chairman order 2026-11-12 (estate migration outcome #3): the earnings-call
qualitative scorer replaces its legacy local→deepseek→kimi→anthropic ladder with
the unified_router. The cutover is env-gated and is ONE switch for the whole
module ladder, taken at the ladder entry in ``score_text`` — so BOTH cited rungs
(the Ollama rung in ``_call_openai_compat_detailed`` and the Kimi rung in
``_call_kimi``) are unreachable while the router serves:

  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_EARNINGS_QUAL_FABRIC != "0"
    -> one fabric_client.complete(..., lane="fast") per logical call, no local
       retry, no second provider, and no legacy rung invocation;
  * not configured, or MACRO_EARNINGS_QUAL_FABRIC=0
    -> the EXACT legacy ladder, byte-for-byte unchanged;
  * FabricUnavailable (no request left the host) -> fall through to that ladder;
  * a served error -> degrade as (None, "llm_error") without retrying or falling
    through; a refusal drops even partial text; an empty reply is not re-asked.

All stub-based: no network, no API keys, no sparse-omitted directory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import earnings_qual as eq  # noqa: E402
from lib import ai_costs  # noqa: E402
from lib import fabric_client as fc  # noqa: E402

_GOOD = {
    "sentiment": 0.7,
    "performance": 8.5,
    "confidence": 0.9,
    "tone_word": "confident",
    "positive_highlights": ["Revenue up 22% YoY"],
    "negative_highlights": ["Cloud growth decelerated"],
    "tags": ["beat_and_raise"],
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
        return _completion(json.dumps(_GOOD))

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_EARNINGS_QUAL_FABRIC", raising=False)
    return calls


@pytest.fixture
def legacy_untouched(monkeypatch):
    """Fail loudly if ANY legacy rung is reached."""
    def boom(*a, **kw):
        pytest.fail("legacy rung must not run while the router serves")

    monkeypatch.setattr(eq, "_call_openai_compat_detailed", boom)
    monkeypatch.setattr(eq, "_call_openai_compat", boom)
    monkeypatch.setattr(eq, "_call_kimi", boom)
    monkeypatch.setattr(eq, "_call_llm_auth", boom)


# --------------------------------------------------------------------------- #
# configured -> fabric fast lane, both cited rungs unreachable
# --------------------------------------------------------------------------- #
def test_configured_routes_to_fabric_fast(fabric_on, legacy_untouched):
    row = eq.score_text("Some earnings call text.", "NVDA", "Q1", 2026)

    assert row["degraded_reason"] is None
    assert row["sentiment"] == 0.7 and row["performance"] == 8.5
    assert row["tone_word"] == "confident"
    assert row["tags"] == ["beat_and_raise"]
    assert len(fabric_on) == 1
    call = fabric_on[0]
    assert call["lane"] == "fast"
    assert call["client"] == "Python client"
    assert call["project_id"] == "macro-dashboard"
    assert call["session_id"] == "macro-earnings-qual"
    assert call["max_tokens"] == 1200
    assert call["messages"][0]["role"] == "user"
    assert "NVDA" in call["messages"][0]["content"]
    assert call["system"] == eq._SYSTEM_PROMPT


def test_ollama_rung_never_reached_when_fabric_serves(fabric_on, monkeypatch):
    """R11a: the local Ollama rung is skipped entirely, not merely deprioritized."""
    monkeypatch.setattr(eq, "_call_openai_compat_detailed",
                        lambda *a, **kw: pytest.fail("Ollama rung must not run"))
    row = eq.score_text("txt", "AAPL", "Q2", 2026)
    assert row["degraded_reason"] is None
    assert len(fabric_on) == 1


def test_kimi_rung_never_reached_when_fabric_serves(fabric_on, monkeypatch):
    """R11b: the Kimi rung is skipped entirely; MOONSHOT_API_KEY goes unused."""
    monkeypatch.setenv("MOONSHOT_API_KEY", "sk-should-never-be-read")
    monkeypatch.setattr(eq, "_call_kimi",
                        lambda *a, **kw: pytest.fail("Kimi rung must not run"))
    row = eq.score_text("txt", "MSFT", "Q3", 2026)
    assert row["degraded_reason"] is None
    assert len(fabric_on) == 1


def test_fabric_success_books_usage_row(fabric_on, ledger_rows, monkeypatch):
    def fake_complete(messages, **kwargs):
        fabric_on.append({"messages": messages, **kwargs})
        return _completion(json.dumps(_GOOD), model="glm-5.3", usage={
            "input_tokens": 123, "output_tokens": 45,
            "cache_read_input_tokens": 7, "cache_creation_input_tokens": 8})

    monkeypatch.setattr(fc, "complete", fake_complete)
    eq.score_text("txt", "TSLA", "Q4", 2025)

    assert len(ledger_rows) == 1
    row = ledger_rows[0]
    assert row["lane"] == "earnings-qual"
    assert row["provider"] == "fabric"
    assert row["model"] == "glm-5.3"
    assert row["input_tokens"] == 123 and row["output_tokens"] == 45
    assert row["cache_read_tokens"] == 7 and row["cache_creation_tokens"] == 8
    assert row["stage"] == "earnings_qual"


def test_served_model_is_recorded_on_the_score_row(fabric_on, monkeypatch):
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion(json.dumps(_GOOD), model="kimi-k3.1-pro"))
    row = eq.score_text("txt", "AMD", "Q1", 2026)
    assert row["model"] == "kimi-k3.1-pro"


# --------------------------------------------------------------------------- #
# not configured / kill-switch -> legacy, unchanged
# --------------------------------------------------------------------------- #
def test_unconfigured_uses_legacy_ladder(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.delenv("MACRO_EARNINGS_QUAL_FABRIC", raising=False)
    monkeypatch.setattr(eq, "_call_openai_compat",
                        lambda *a, **kw: (json.dumps(_GOOD), None))

    row = eq.score_text("txt", "X", "Q1", 2026)
    assert row["degraded_reason"] is None
    assert row["model"] == "openai_compat"
    assert calls == []          # fabric never touched


def test_kill_switch_forces_legacy_even_when_configured(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setenv("MACRO_EARNINGS_QUAL_FABRIC", "0")
    monkeypatch.setattr(eq, "_call_openai_compat",
                        lambda *a, **kw: (json.dumps(_GOOD), None))

    row = eq.score_text("txt", "X", "Q1", 2026)
    assert row["degraded_reason"] is None
    assert row["model"] == "openai_compat"
    assert calls == []


def test_kill_switch_legacy_walk_starts_at_ollama(monkeypatch):
    """Kill-switch -> the full legacy walk, Ollama first, exactly as today."""
    seen: list[str] = []

    def oc(system, user, oc_cfg, *, max_tokens):
        seen.append("openai_compat")
        return json.dumps(_GOOD), None

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: pytest.fail("fabric must be off"))
    monkeypatch.setenv("MACRO_EARNINGS_QUAL_FABRIC", "0")
    monkeypatch.setattr(eq, "_call_openai_compat", oc)

    row = eq.score_text("txt", "X", "Q1", 2026)
    assert row["degraded_reason"] is None
    assert seen == ["openai_compat"]


# --------------------------------------------------------------------------- #
# router UNREACHABLE -> fall through to legacy, never blank the score
# --------------------------------------------------------------------------- #
def test_router_unavailable_falls_through_to_legacy_ladder(monkeypatch):
    calls: list[dict] = []

    def unavailable(messages, **kwargs):
        calls.append(kwargs)
        raise fc.FabricUnavailable("the anthropic SDK is not importable")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", unavailable)
    monkeypatch.delenv("MACRO_EARNINGS_QUAL_FABRIC", raising=False)
    monkeypatch.setattr(eq, "_call_openai_compat",
                        lambda *a, **kw: (json.dumps(_GOOD), None))

    row = eq.score_text("txt", "X", "Q1", 2026)
    assert row["degraded_reason"] is None
    assert row["model"] == "openai_compat"
    assert len(calls) == 1          # one fabric attempt, then the ladder


def test_router_unavailable_empty_ladder_reports_legacy_reason(monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: (_ for _ in ()).throw(fc.FabricUnavailable("no sdk")))
    monkeypatch.delenv("MACRO_EARNINGS_QUAL_FABRIC", raising=False)
    monkeypatch.setattr(eq, "_call_openai_compat", lambda *a, **kw: (None, "down"))
    monkeypatch.setattr(eq, "_call_llm_auth", lambda *a, **kw: (None, "down"))

    row = eq.score_text("txt", "X", "Q1", 2026)
    assert row["degraded_reason"] == "down"


# --------------------------------------------------------------------------- #
# served failures -> degrade once, never retry, never walk a second provider
# --------------------------------------------------------------------------- #
def test_served_error_degrades_without_retry(monkeypatch, legacy_untouched):
    calls: list[dict] = []

    def boom(messages, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("router exhausted its ladder")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)
    monkeypatch.delenv("MACRO_EARNINGS_QUAL_FABRIC", raising=False)

    row = eq.score_text("txt", "X", "Q1", 2026)
    assert row["degraded_reason"] == "llm_error"
    assert len(calls) == 1


def test_refusal_drops_partial_text(monkeypatch, legacy_untouched):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion(json.dumps(_GOOD), raw=_RefusalRaw()))
    monkeypatch.delenv("MACRO_EARNINGS_QUAL_FABRIC", raising=False)

    row = eq.score_text("txt", "X", "Q1", 2026)
    assert row["degraded_reason"] == "refusal"
    assert row["sentiment"] is None and row["performance"] is None


def test_refusal_books_no_usage_row(monkeypatch, ledger_rows, legacy_untouched):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion("partial", raw=_RefusalRaw()))
    monkeypatch.delenv("MACRO_EARNINGS_QUAL_FABRIC", raising=False)

    eq.score_text("txt", "X", "Q1", 2026)
    assert ledger_rows == []


def test_empty_reply_is_not_retried(monkeypatch, ledger_rows, legacy_untouched):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion(""))
    monkeypatch.delenv("MACRO_EARNINGS_QUAL_FABRIC", raising=False)

    row = eq.score_text("txt", "X", "Q1", 2026)
    assert row["degraded_reason"] == "empty_reply"
    assert len(calls) == 1
    assert ledger_rows == []


def test_unusable_json_is_not_reasked(monkeypatch, legacy_untouched):
    """A served reply that is not usable JSON is a served failure, not a re-ask."""
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: calls.append(kw) or _completion("not json at all"))
    monkeypatch.delenv("MACRO_EARNINGS_QUAL_FABRIC", raising=False)

    row = eq.score_text("txt", "X", "Q1", 2026)
    assert row["degraded_reason"] == "invalid_json"
    assert len(calls) == 1          # no bounded retry, no second provider


def test_incomplete_schema_is_not_reasked(monkeypatch, legacy_untouched):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: calls.append(kw) or _completion('{"sentiment": 0.2}'))
    monkeypatch.delenv("MACRO_EARNINGS_QUAL_FABRIC", raising=False)

    row = eq.score_text("txt", "X", "Q1", 2026)
    assert row["degraded_reason"] == "incomplete_schema"
    assert len(calls) == 1
