"""The catalyst-tone digest writer routes through the Capacity Fabric when configured.

Chairman order 2026-11-12: all estate AI routing moves to the unified_router, and
the digest writer must use the router's `fast` lane. The cutover is env-gated and
scoped to the LLM call path of engine/catalyst_tone.py:

  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_CATALYST_TONE_FABRIC != "0"
    -> one fabric_client.complete(..., lane="fast") call, no local retry;
  * not configured, or MACRO_CATALYST_TONE_FABRIC=0
    -> the EXACT legacy llm_auth ladder, byte-for-byte unchanged;
  * the shared tolerant parser _extract_json (imported by regime_snap_veto and
    policy_intent_desk) is untouched by this cutover.

All stub-based: no network, no API keys, no sparse-omitted directory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import catalyst_tone as ct  # noqa: E402
from engine import llm_auth as llm_auth_mod  # noqa: E402
from lib import ai_costs  # noqa: E402
from lib import fabric_client as fc  # noqa: E402

_SHIPPED_CFG = {
    "api_key_env": "DEEPSEEK_API_KEY",
    "llm_base_url": "https://api.deepseek.com/anthropic",
    "llm_model": "deepseek-v4-pro",
    "max_tokens": 1500,
}

_DOC = ("The Committee decided to raise the target range for the federal funds "
        "rate by 25 basis points.")

_FABRIC_REPLY = json.dumps({
    "tone_score": 0.4,
    "guidance_direction": "tightening",
    "risk_delta": 0.3,
    "shock_reversible": "unknown",
    "confidence": "medium",
    "evidence": [{"field": "guidance_direction",
                  "quote_span": "raise the target range"}],
})


class _Raw:
    def __init__(self, stop_reason="end_turn"):
        self.stop_reason = stop_reason


class _FakeSdk:
    """Stands in for `_client(cfg)` on the legacy ladder; never actually used,
    because make_call is stubbed to return a ready reply."""

    class _Messages:
        def create(self, **_kw):
            raise AssertionError("the stubbed make_call should not reach the SDK")

    def __init__(self):
        self.messages = self._Messages()


def _completion(text, model="deepseek-v4.1-flash", stop_reason="end_turn"):
    return fc.Completion(text=text, model_served=model, route_id="r-1",
                         provider="deepseek", usage={"output_tokens": 5},
                         raw=_Raw(stop_reason))


@pytest.fixture(autouse=True)
def _no_real_ledger(monkeypatch):
    """No test in this module may append to the real data/ai_costs ledger."""
    monkeypatch.setattr(ai_costs, "record_usage", lambda **_kw: True)


@pytest.fixture
def cfg(tmp_path):
    """A shipped-shaped cfg whose reply cache lives in tmp_path (never data/)."""
    return {**_SHIPPED_CFG, "reply_cache_dir": str(tmp_path / "reply_cache")}


@pytest.fixture
def fabric_on(monkeypatch, cfg):
    """Router configured; record every complete() call."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return _completion(_FABRIC_REPLY)

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_CATALYST_TONE_FABRIC", raising=False)
    return calls


@pytest.fixture
def fabric_off(monkeypatch):
    """Router NOT configured; legacy ladder stubbed to an empty provider list."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):   # must never be reached
        calls.append(kwargs)
        return _completion("should not happen")

    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.setattr(ct, "_client", lambda _cfg: object())
    monkeypatch.setattr(llm_auth_mod, "make_call",
                        lambda *a, **kw: (None, "no_client_or_key", None))
    monkeypatch.delenv("MACRO_CATALYST_TONE_FABRIC", raising=False)
    return calls


# --------------------------------------------------------------------------- #
# configured -> fabric
# --------------------------------------------------------------------------- #
def test_configured_digest_routes_to_fabric_fast(fabric_on, cfg):
    text, reason = ct._call_model(_DOC, "FOMC statement", cfg)
    assert reason == "fabric"
    assert json.loads(text)["guidance_direction"] == "tightening"
    assert len(fabric_on) == 1
    call = fabric_on[0]
    assert call["lane"] == "fast"
    assert call["client"] == "Python client"
    assert call["project_id"] == "macro-dashboard"
    assert call["session_id"] == "macro-catalyst-tone"
    assert call["system"] == ct.CATALYST_SYSTEM
    assert call["max_tokens"] == 1500
    assert len(call["messages"]) == 1
    assert call["messages"][0]["role"] == "user"
    assert _DOC in call["messages"][0]["content"]
    assert "FOMC statement" in call["messages"][0]["content"]


def test_configured_digest_records_fabric_usage(fabric_on, cfg, monkeypatch):
    rows: list[dict] = []
    monkeypatch.setattr(ai_costs, "record_usage",
                        lambda **kw: rows.append(kw) or True)

    text, reason = ct._call_model(_DOC, "ctx", cfg)
    assert reason == "fabric"
    assert len(rows) == 1
    assert rows[0]["provider"] == "fabric"
    assert rows[0]["model"] == "deepseek-v4.1-flash"
    # The ledger lane is the ATTRIBUTION key, not the router lane: it must stay
    # "catalyst-tone" so the spend keeps rolling into the News lobe.
    assert rows[0]["lane"] == "catalyst-tone"
    assert rows[0]["stage"] == "fabric"
    assert "fast" in rows[0]["note"]


def test_fabric_usage_lane_rolls_into_the_news_lobe(fabric_on, cfg, monkeypatch):
    """A lane with no lobe rule silently falls through to "Other" (ai_costs.py:58),
    which would move catalyst spend off the News row on the AI Cost page."""
    rows: list[dict] = []
    monkeypatch.setattr(ai_costs, "record_usage",
                        lambda **kw: rows.append(kw) or True)

    ct._call_model(_DOC, "ctx", cfg)
    assert ai_costs.lobe_for_lane(rows[0]["lane"]) == "News"


def test_usage_telemetry_failure_does_not_break_the_call(fabric_on, cfg, monkeypatch):
    def boom(**_kw):
        raise RuntimeError("ledger disk full")

    monkeypatch.setattr(ai_costs, "record_usage", boom)

    text, reason = ct._call_model(_DOC, "ctx", cfg)
    assert reason == "fabric"
    assert json.loads(text)["guidance_direction"] == "tightening"


def test_digest_document_end_to_end_through_fabric(fabric_on, cfg, monkeypatch):
    # llm_min_confidence="medium" so the stub's medium confidence survives the
    # code-side floor; the assertion is about the fabric ROUTE, not the threshold.
    monkeypatch.setattr(ct, "_cfg",
                        lambda: {**cfg, "enabled": True,
                                 "llm_min_confidence": "medium"})
    # never append to the real data/ai_costs ledger from a test
    monkeypatch.setattr(ai_costs, "record_usage", lambda **_kw: True)
    rec = ct.digest_document(_DOC, kind="fomc_statement", context="FOMC")
    assert rec["degraded_reason"] is None
    assert rec["confidence_gated"] is False
    assert rec["guidance_direction"] == "tightening"
    assert len(fabric_on) == 1


# --------------------------------------------------------------------------- #
# refusal / empty
# --------------------------------------------------------------------------- #
def test_fabric_refusal_returns_refusal_before_text(monkeypatch, cfg):
    calls: list[dict] = []

    def refusal(messages, **kwargs):
        calls.append(kwargs)
        return _completion("partial answer", stop_reason="refusal")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", refusal)
    monkeypatch.delenv("MACRO_CATALYST_TONE_FABRIC", raising=False)

    text, reason = ct._call_model(_DOC, "ctx", cfg)
    assert text is None and reason == "refusal"
    assert len(calls) == 1


def test_fabric_empty_reply_is_not_retried(monkeypatch, cfg):
    calls: list[dict] = []

    def empty(messages, **kwargs):
        calls.append(kwargs)
        return _completion("")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", empty)
    monkeypatch.delenv("MACRO_CATALYST_TONE_FABRIC", raising=False)

    text, reason = ct._call_model(_DOC, "ctx", cfg)
    assert text is None and reason == "empty_reply"
    assert len(calls) == 1


# --------------------------------------------------------------------------- #
# router-up error -> degrade with NO retry and NO legacy second provider
# --------------------------------------------------------------------------- #
def test_fabric_error_degrades_without_retry(monkeypatch, cfg):
    calls: list[dict] = []

    def boom(messages, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("router exhausted its ladder")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)
    monkeypatch.setattr(llm_auth_mod, "make_call",
                        lambda *a, **kw: pytest.fail("legacy ladder must not run"))
    monkeypatch.delenv("MACRO_CATALYST_TONE_FABRIC", raising=False)

    text, reason = ct._call_model(_DOC, "ctx", cfg)
    assert text is None and reason == "llm_error"
    assert len(calls) == 1          # one call; the router owns fallback


# --------------------------------------------------------------------------- #
# router UNREACHABLE -> fall through to legacy, never blank the digest
#
# FabricUnavailable means no request ever left this host (no token, or the SDK
# will not import). Blanking a digest that the legacy ladder could still produce
# would be a regression, so _call_model must fall through rather than degrade.
# --------------------------------------------------------------------------- #
def test_router_unavailable_falls_through_to_legacy_ladder(monkeypatch, cfg):
    calls: list[dict] = []

    def unavailable(messages, **kwargs):
        calls.append(kwargs)
        raise fc.FabricUnavailable("the anthropic SDK is not importable")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", unavailable)
    monkeypatch.setattr(ct, "_client", lambda _cfg: object())
    monkeypatch.setattr(llm_auth_mod, "make_call",
                        lambda *a, **kw: (json.dumps({"tone_score": 0.0}), None, "deepseek"))
    monkeypatch.delenv("MACRO_CATALYST_TONE_FABRIC", raising=False)

    text, reason = ct._call_model(_DOC, "ctx", cfg)
    assert reason is None
    assert json.loads(text)["tone_score"] == 0.0
    assert len(calls) == 1                # one fabric attempt, then the ladder


def test_router_unavailable_empty_ladder_reports_legacy_reason(monkeypatch, cfg):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: (_ for _ in ()).throw(fc.FabricUnavailable("no sdk")))
    monkeypatch.setattr(ct, "_client", lambda _cfg: None)
    monkeypatch.delenv("MACRO_CATALYST_TONE_FABRIC", raising=False)

    text, reason = ct._call_model(_DOC, "ctx", cfg)
    # The legacy diagnosis, not "llm_error": the fabric path was never reached.
    assert text is None and reason == "no_client_or_key"


# --------------------------------------------------------------------------- #
# not configured / kill-switch -> legacy, unchanged
# --------------------------------------------------------------------------- #
def test_unconfigured_digest_uses_legacy_ladder(fabric_off, cfg):
    text, reason = ct._call_model(_DOC, "ctx", cfg)
    assert text is None and reason == "no_client_or_key"
    assert fabric_off == []          # fabric never touched


def test_kill_switch_forces_legacy_even_when_configured(monkeypatch, cfg):
    calls: list[dict] = []
    legacy: list[str] = []

    def fake_make_call(*_a, **_kw):
        legacy.append("called")
        return (json.dumps({"tone_score": 0.0}), None, "deepseek")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setattr(ct, "_client", lambda _cfg: object())
    monkeypatch.setattr(llm_auth_mod, "make_call", fake_make_call)
    monkeypatch.setenv("MACRO_CATALYST_TONE_FABRIC", "0")

    text, reason = ct._call_model(_DOC, "ctx", cfg)
    assert reason is None
    assert calls == []               # fabric never touched
    assert len(legacy) == 1


def test_no_token_means_fabric_never_called(monkeypatch, cfg):
    """is_configured() is token-driven; with no token the legacy ladder runs and
    complete() is never reached."""
    calls: list[dict] = []
    monkeypatch.delenv("FABRIC_ROUTER_TOKEN", raising=False)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setattr(ct, "_client", lambda _cfg: object())
    monkeypatch.setattr(llm_auth_mod, "make_call",
                        lambda *a, **kw: (None, "no_client_or_key", None))
    monkeypatch.delenv("MACRO_CATALYST_TONE_FABRIC", raising=False)

    text, reason = ct._call_model(_DOC, "ctx", cfg)
    assert text is None and reason == "no_client_or_key"
    assert calls == []


# --------------------------------------------------------------------------- #
# W7 #33 determinism: a fabric reply is cached exactly like a legacy reply
#
# Graded fields (tone_score -> ledger, shock_reversible -> spvector veto) MUST be
# reproducible for the same document on the same day. The cache is keyed on the
# PROMPT, and both paths send identical bytes, so skipping the cache write on the
# fabric path would re-call the model every run and allow drift.
# --------------------------------------------------------------------------- #
def test_fabric_reply_is_written_to_the_reply_cache(fabric_on, cfg):
    text, reason = ct._call_model(_DOC, "ctx", cfg)
    assert reason == "fabric"
    phash = ct._prompt_hash(ct._extraction_model(cfg), ct.CATALYST_SYSTEM,
                            ct._user_prompt(_DOC, "ctx"))
    assert ct._reply_cache_get(phash, cfg) == text


def test_second_same_document_call_is_a_cache_hit_not_a_second_fabric_call(
        fabric_on, cfg):
    first, _ = ct._call_model(_DOC, "ctx", cfg)
    second, reason = ct._call_model(_DOC, "ctx", cfg)
    assert second == first
    assert reason is None            # cache HIT, no degraded reason
    assert len(fabric_on) == 1       # exactly one model call for the same document


def test_failed_fabric_call_writes_no_cache_entry(monkeypatch, cfg):
    """A refusal / empty / error must not poison the cache with a bad reply."""
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", lambda messages, **kw: _completion(""))
    monkeypatch.delenv("MACRO_CATALYST_TONE_FABRIC", raising=False)

    text, reason = ct._call_model(_DOC, "ctx", cfg)
    assert text is None and reason == "empty_reply"
    phash = ct._prompt_hash(ct._extraction_model(cfg), ct.CATALYST_SYSTEM,
                            ct._user_prompt(_DOC, "ctx"))
    assert ct._reply_cache_get(phash, cfg) is None


def test_fabric_truncated_reply_is_rejected_like_the_legacy_path(monkeypatch, cfg):
    """max_tokens means the model ran out of room mid-record. _extract_json
    deliberately REPAIRS truncated JSON, so accepting the text would grade a
    partial digest whose evidence array was cut off. Legacy returns
    "stop_max_tokens" without reading the text; the fabric path must match."""
    calls: list[dict] = []
    truncated = ('{"tone_score": 0.4, "guidance_direction": "tightening", '
                 '"confidence": "high"')

    def cut_short(messages, **kwargs):
        calls.append(kwargs)
        return _completion(truncated, stop_reason="max_tokens")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", cut_short)
    monkeypatch.delenv("MACRO_CATALYST_TONE_FABRIC", raising=False)

    text, reason = ct._call_model(_DOC, "ctx", cfg)
    assert text is None
    assert reason == "stop_max_tokens"     # identical to the legacy reason string
    assert len(calls) == 1


def test_truncated_reply_would_otherwise_have_been_graded(monkeypatch, cfg):
    """Guards the guard: proves the truncation rule is load-bearing rather than a
    no-op. The same bytes ARE repaired and graded if they are not flagged."""
    truncated = ('{"tone_score": 0.4, "guidance_direction": "tightening", '
                 '"confidence": "high"')
    assert ct._extract_json(truncated) is not None
    assert ct._extract_json(truncated)["tone_score"] == 0.4


def test_digest_records_the_truncation_reason(monkeypatch, cfg):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: _completion(
                            '{"tone_score": 0.4', stop_reason="max_tokens"))
    monkeypatch.delenv("MACRO_CATALYST_TONE_FABRIC", raising=False)
    monkeypatch.setattr(ct, "_cfg", lambda: {**cfg, "enabled": True})

    rec = ct.digest_document(_DOC, kind="fomc_statement", context="FOMC")
    assert rec["degraded_reason"] == "stop_max_tokens"
    assert rec["tone_score"] == 0.0        # neutral, not the truncated 0.4


# --------------------------------------------------------------------------- #
# no token / kill-switch -> the legacy path is BYTE-IDENTICAL
#
# The prompt is what the reply cache is keyed on, so "the legacy path is
# unchanged" is provable exactly: same prompt bytes -> same prompt hash -> same
# cache entry -> same graded record.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("source,context", [
    ("The Committee decided to raise rates.", "FOMC statement"),
    ("", "empty"),
    ("unicode — “quotes” and\nnewlines\t", "ctx with spaces"),
    ("x" * 5000, "long document"),
])
def test_prompt_bytes_are_unchanged_from_the_legacy_shape(source, context):
    """The fabric refactor extracted the prompt into _user_prompt(); the bytes it
    produces must be exactly the ones the inline legacy expression produced, or
    every existing reply-cache entry would be invalidated by the cutover."""
    legacy = (f"Document context: {context}\n\n"
              f"Document text follows between <doc> tags.\n<doc>\n{source}\n</doc>")
    assert ct._user_prompt(source, context) == legacy


def test_legacy_path_produces_the_same_digest_as_before_the_cutover(cfg,
                                                                   monkeypatch):
    """Kill-switch ON through the legacy ladder: the graded record still renders."""
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: pytest.fail("fabric must not run"))
    monkeypatch.setattr(ct, "_client", lambda _cfg: _FakeSdk())
    monkeypatch.setattr(llm_auth_mod, "make_call",
                        lambda *a, **kw: (_FABRIC_REPLY, None, "deepseek"))
    monkeypatch.setenv("MACRO_CATALYST_TONE_FABRIC", "0")
    monkeypatch.setattr(ct, "_cfg",
                        lambda: {**cfg, "enabled": True,
                                 "llm_min_confidence": "medium"})

    rec = ct.digest_document(_DOC, kind="fomc_statement", context="FOMC")
    assert rec["degraded_reason"] is None
    assert rec["guidance_direction"] == "tightening"
    assert rec["confidence_gated"] is False


# --------------------------------------------------------------------------- #
# the shared tolerant parser is untouched by this cutover
# --------------------------------------------------------------------------- #
def test_extract_json_behavior_unchanged():
    assert ct._extract_json('{"a": 1}') == {"a": 1}
    assert ct._extract_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert ct._extract_json('Here is the result:\n{"a": 3}\nThanks!') == {"a": 3}
    assert ct._extract_json('{"a": "x"], "b": [1, 2]}') == {"a": "x", "b": [1, 2]}
    assert ct._extract_json('not json at all') is None
    assert ct._extract_json('') is None
    assert ct._extract_json('[1, 2, 3]') is None
