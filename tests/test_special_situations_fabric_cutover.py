"""The Special Situations extraction call routes through the Capacity Fabric.

Chairman order 2026-11-12 (estate migration outcome #3): the EDGAR special-
situations extractor replaces its direct Anthropic-SDK call with the
unified_router. The cutover is env-gated and scoped to that ONE call site
(`collectors/special_situations._llm_call`):

  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_SPECIAL_SITUATIONS_FABRIC
    != "0" -> one fabric_client.complete(..., lane="fast") per logical call, no
    local retry, no second provider;
  * not configured, killed, or the pre-existing DISABLE_SPECIAL_SITUATIONS_LLM
    set -> the EXACT legacy direct-SDK path, byte-for-byte unchanged;
  * FabricUnavailable (no request left the host) -> fall through to that legacy
    path;
  * a served error -> degrade to {} without retrying or falling through; a
    refusal drops even partial text; an empty reply is not retried;
  * the ledger row keeps lane "special-situations" but books provider="fabric"
    and the model the router actually served.

All stub-based: no network, no API keys, no sparse-omitted directory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors import special_situations as ss  # noqa: E402
from lib import ai_costs as ai_costs_mod  # noqa: E402
from lib import fabric_client as fc  # noqa: E402

_CLEAN_REPLY = {
    "summary": "Acme to be acquired for $25/sh cash.",
    "category": "Acquisitions",
    "role": "target",
    "confidence": "high",
    "deal_terms": {"price_per_share": 25.0, "consideration": "cash"},
}


class _Raw:
    def __init__(self, stop_reason: str = "end_turn"):
        self.stop_reason = stop_reason


def _completion(text, model="deepseek-v4.1-flash", stop_reason="end_turn"):
    return fc.Completion(text=text, model_served=model, route_id="r-1",
                         provider="deepseek", usage={"input_tokens": 1200,
                                                     "output_tokens": 55},
                         raw=_Raw(stop_reason))


class _LegacyResp:
    def __init__(self, text):
        self.content = [type("B", (), {"type": "text", "text": text})()]
        self.usage = type("U", (), {"input_tokens": 7, "output_tokens": 3})()


class _LegacyClient:
    """The legacy direct-SDK client: counts and answers every create()."""

    def __init__(self, text=json.dumps(_CLEAN_REPLY), fail: bool = False):
        self._text = text
        self._fail = fail
        self.calls: list[dict] = []
        self.base_url = "https://api.deepseek.com/anthropic"
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        if self._fail:
            raise RuntimeError("legacy endpoint down")
        return _LegacyResp(self._text)


@pytest.fixture(autouse=True)
def ledger(monkeypatch):
    """Capture every ledger row instead of writing data/ai_costs/usage.jsonl.

    Autouse: the legacy path books through record_response_usage, so a test that
    exercises it must not touch the repo's real data tree either.
    """
    rows: list[dict] = []
    monkeypatch.setattr(ai_costs_mod, "record_usage",
                        lambda **kw: rows.append(kw) or True)
    monkeypatch.setattr(ai_costs_mod, "record_response_usage", lambda **kw: True)
    return rows


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Default environment for every test: router off unless a test turns it on."""
    monkeypatch.delenv("MACRO_SPECIAL_SITUATIONS_FABRIC", raising=False)
    monkeypatch.delenv("DISABLE_SPECIAL_SITUATIONS_LLM", raising=False)
    monkeypatch.setattr(fc, "is_configured", lambda: False)


@pytest.fixture
def fabric_on(monkeypatch, ledger):
    """Router configured; record every complete() call."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return _completion(json.dumps(_CLEAN_REPLY))

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    return calls


# --------------------------------------------------------------------------- #
# configured -> fabric fast lane
# --------------------------------------------------------------------------- #
def test_configured_extraction_routes_to_fabric_fast(fabric_on):
    legacy = _LegacyClient()
    obj = ss._llm_call(legacy, "deepseek-chat", "SYS", "PROMPT")

    assert obj["category"] == _CLEAN_REPLY["category"]
    assert obj["deal_terms"]["price_per_share"] == 25.0
    assert legacy.calls == []          # the legacy client was never touched
    assert len(fabric_on) == 1
    call = fabric_on[0]
    assert call["lane"] == "fast"
    assert call["client"] == "Python client"
    assert call["project_id"] == "macro-dashboard"
    assert call["session_id"] == "macro-special-situations"
    assert call["system"] == "SYS"
    assert call["messages"] == [{"role": "user", "content": "PROMPT"}]
    assert call["max_tokens"] == 420


def test_fabric_books_ledger_provider_and_served_model(fabric_on, ledger):
    ss._llm_call(_LegacyClient(), "deepseek-chat", "SYS", "PROMPT")

    assert len(ledger) == 1
    row = ledger[0]
    assert row["lane"] == "special-situations"     # lane continuity
    assert row["provider"] == "fabric"
    assert row["model"] == "deepseek-v4.1-flash"
    assert row["input_tokens"] == 1200
    assert row["output_tokens"] == 55


# --------------------------------------------------------------------------- #
# switches off -> byte-identical legacy ladder
# --------------------------------------------------------------------------- #
def test_kill_switch_zero_forces_legacy(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setenv("MACRO_SPECIAL_SITUATIONS_FABRIC", "0")

    legacy = _LegacyClient()
    obj = ss._llm_call(legacy, "deepseek-chat", "SYS", "PROMPT")

    assert obj["category"] == _CLEAN_REPLY["category"]
    assert calls == []                 # fabric never touched
    assert len(legacy.calls) == 1
    assert legacy.calls[0]["max_tokens"] == 420
    assert legacy.calls[0]["system"] == "SYS"


def test_unconfigured_routes_to_legacy(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))

    legacy = _LegacyClient()
    obj = ss._llm_call(legacy, "deepseek-chat", "SYS", "PROMPT")

    assert obj["category"] == _CLEAN_REPLY["category"]
    assert calls == []
    assert len(legacy.calls) == 1


def test_pre_existing_disable_switch_still_forces_legacy(monkeypatch):
    """DISABLE_SPECIAL_SITUATIONS_LLM keeps its exact old meaning: both switches
    must allow the fabric branch."""
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setenv("DISABLE_SPECIAL_SITUATIONS_LLM", "1")

    legacy = _LegacyClient()
    obj = ss._llm_call(legacy, "deepseek-chat", "SYS", "PROMPT")

    assert obj["category"] == _CLEAN_REPLY["category"]
    assert calls == []
    assert len(legacy.calls) == 1


# --------------------------------------------------------------------------- #
# router UNREACHABLE -> legacy path, never a blanked extraction
# --------------------------------------------------------------------------- #
def test_fabric_unavailable_falls_through_to_legacy(monkeypatch):
    calls: list[dict] = []

    def unavailable(messages, **kwargs):
        calls.append(kwargs)
        raise fc.FabricUnavailable("the anthropic SDK is not importable")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", unavailable)

    legacy = _LegacyClient()
    obj = ss._llm_call(legacy, "deepseek-chat", "SYS", "PROMPT")

    assert obj["category"] == _CLEAN_REPLY["category"]
    assert len(calls) == 1             # one fabric attempt, then the legacy path
    assert len(legacy.calls) == 1


# --------------------------------------------------------------------------- #
# one attempt only — a served failure never becomes a second provider call
# --------------------------------------------------------------------------- #
def test_served_error_degrades_without_retry(monkeypatch, ledger):
    calls: list[dict] = []

    def boom(messages, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("router exhausted its ladder")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)

    legacy = _LegacyClient()
    assert ss._llm_call(legacy, "deepseek-chat", "SYS", "PROMPT") == {}
    assert len(calls) == 1             # one call; the router owns fallback
    assert legacy.calls == []          # no second provider
    assert ledger == []                # nothing served, nothing booked


def test_refusal_drops_partial_text(monkeypatch, ledger):
    calls: list[dict] = []

    def refused(messages, **kwargs):
        calls.append(kwargs)
        return _completion(json.dumps({"category": "Acquisitions"}), stop_reason="refusal")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", refused)

    legacy = _LegacyClient()
    assert ss._llm_call(legacy, "deepseek-chat", "SYS", "PROMPT") == {}
    assert len(calls) == 1
    assert legacy.calls == []
    assert ledger == []                # a refusal is not a billed row


def test_empty_reply_is_not_retried(monkeypatch):
    calls: list[dict] = []

    def empty(messages, **kwargs):
        calls.append(kwargs)
        return _completion("")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", empty)

    legacy = _LegacyClient()
    assert ss._llm_call(legacy, "deepseek-chat", "SYS", "PROMPT") == {}
    assert len(calls) == 1
    assert legacy.calls == []


def test_ledger_failure_never_breaks_a_served_call(fabric_on, monkeypatch):
    def boom(**kw):
        raise RuntimeError("ledger disk full")

    monkeypatch.setattr(ai_costs_mod, "record_usage", boom)

    legacy = _LegacyClient()
    obj = ss._llm_call(legacy, "deepseek-chat", "SYS", "PROMPT")
    assert obj["category"] == _CLEAN_REPLY["category"]
    assert legacy.calls == []


# --------------------------------------------------------------------------- #
# token-only host: the router is a complete credential substitute
#
# The migration target has FABRIC_ROUTER_TOKEN and no DEEPSEEK_API_KEY. The
# outer _llm_ready gate must let that host through, and the lane must not try to
# build a legacy client it has no key for.
# --------------------------------------------------------------------------- #
def test_llm_ready_accepts_a_token_only_host(monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(ss.config, "secret", lambda n: None)   # no DeepSeek key

    assert ss._llm_ready({"enabled": True, "llm_brief": True}) is True


def test_llm_ready_still_requires_a_key_when_fabric_is_off(monkeypatch):
    monkeypatch.setattr(ss.config, "secret", lambda n: None)

    assert ss._llm_ready({"enabled": True, "llm_brief": True}) is False


def test_llm_ready_still_honors_the_disable_switch_on_a_token_only_host(monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(ss.config, "secret", lambda n: None)
    monkeypatch.setenv("DISABLE_SPECIAL_SITUATIONS_LLM", "1")

    assert ss._llm_ready({"enabled": True, "llm_brief": True}) is False


def test_token_only_host_never_builds_a_legacy_client(tmp_path, monkeypatch):
    """End-to-end through enrich_classify: no key, router configured -> the
    extraction is served by fabric and _llm_client is never called."""
    monkeypatch.setattr(ss.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(ss.config, "secret", lambda n: None)
    monkeypatch.setattr(ss, "_cfg", lambda: {"enabled": True, "llm_brief": True})
    monkeypatch.setattr(ss, "_fetch_filing_text", lambda cik, acc, **kw: "filing body")
    monkeypatch.setattr(ss, "_llm_client",
                        lambda cfg: pytest.fail("legacy client built on a token-only host"))
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: _completion(json.dumps(_CLEAN_REPLY)))

    (tmp_path / "special_situations").mkdir()
    pd.DataFrame([{"id": "e1", "form_type": "8-K", "company": "Acme Inc", "cik": "10",
                   "accession": "acc1", "items": "8.01", "date_filed": "2026-06-12",
                   "source_url": "u"}]
                 ).to_parquet(tmp_path / "special_situations" / "events.parquet")

    df = ss.enrich_classify().set_index("id")
    assert df.loc["e1", "llm_category"] == "Acquisitions"
    assert df.loc["e1", "llm_role"] == "target"
