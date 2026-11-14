"""Qual extraction routes through the Capacity Fabric when configured.

Chairman order 2026-11-12 (estate migration outcome #3): engine/qual_extraction.py
replaces its direct Anthropic-SDK call with the Capacity Fabric unified_router.
The cutover is env-gated and scoped to this module:

  * configured (FABRIC_ROUTER_TOKEN present) and
    MACRO_QUAL_EXTRACTION_FABRIC != "0"
    -> ONE fabric_client.complete(..., lane="fast") per logical call, no local
       retry, no second provider, and no direct client.messages.create();
  * not configured, or MACRO_QUAL_EXTRACTION_FABRIC=0
    -> the EXACT legacy client path, byte-for-byte unchanged;
  * FabricUnavailable (no request left the host) -> fall through to that legacy
    path;
  * a served error -> degrade as (None, "llm_error") without retrying or falling
    through; a refusal drops even partial text; an empty reply is not retried.

BOTH legacy call sites are covered: the seed=0 attempt and the TypeError retry
that drops seed. The fabric branch sits BEFORE that ladder, so one router call
replaces both; the kill-switch and FabricUnavailable cases prove the ladder —
including its TypeError retry path — is reached unchanged.

All stub-based: no network, no API keys, no sparse-omitted directory.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import engine.qual_extraction as qe  # noqa: E402
from lib import ai_costs  # noqa: E402
from lib import fabric_client as fc  # noqa: E402

BODY = (
    "On July 1, 2026, ACME Corporation entered into a definitive merger agreement "
    "with Globex Inc. under which Globex will acquire all outstanding shares of ACME "
    "for $42.00 per share in cash."
)
REPLY = '{"direction": "up", "confidence": "high"}'


class _Raw:
    stop_reason = "end_turn"


class _RefusalRaw:
    stop_reason = "refusal"


def _completion(text, model="deepseek-v4.1-flash", raw=None, usage=None):
    return fc.Completion(text=text, model_served=model, route_id="r-1",
                         provider="deepseek", usage=usage or {"output_tokens": 5},
                         raw=raw or _Raw())


class _LegacyResp:
    """Minimal stand-in for an Anthropic Messages response."""

    stop_reason = "end_turn"

    def __init__(self, text):
        self.content = [type("B", (), {"type": "text", "text": text})()]


class _LegacyClient:
    """Stub of ``anthropic.Anthropic()``. ``raise_type_error=False`` makes the
    seed=0 attempt raise TypeError so the ladder's drop-seed retry runs."""

    def __init__(self, text=REPLY, raise_type_error=False):
        self.text = text
        self.raise_type_error = raise_type_error
        self.calls: list[dict] = []
        outer = self

        class _Messages:
            def create(_self, **kw):
                outer.calls.append(dict(kw))
                if outer.raise_type_error and "seed" in kw:
                    raise TypeError("unexpected keyword argument 'seed'")
                return _LegacyResp(outer.text)

        self.messages = _Messages()


@pytest.fixture
def cfg(tmp_path):
    """Per-test reply cache under tmp_path — never the repo's data/ tree."""
    return {"max_tokens": 1500, "reply_cache_dir": str(tmp_path / "cache")}


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
        return _completion(REPLY)

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_QUAL_EXTRACTION_FABRIC", raising=False)
    return calls


def _legacy_never(cfg):
    """A _client that fails the test if the legacy path is reached."""
    def boom(_cfg):
        pytest.fail("legacy direct-client path must not run")
    return boom


# --------------------------------------------------------------------------- #
# configured -> fabric fast, both legacy call sites replaced by one request
# --------------------------------------------------------------------------- #
def test_configured_routes_to_fabric_fast(fabric_on, cfg, monkeypatch):
    monkeypatch.setattr(qe, "_client", _legacy_never(cfg))

    text, reason = qe._call_model(BODY, "ctx", cfg, "test-model-x")

    assert (text, reason) == (REPLY, None)
    assert len(fabric_on) == 1
    c = fabric_on[0]
    assert c["lane"] == "fast"
    assert c["client"] == "Python client"
    assert c["project_id"] == "macro-dashboard"
    assert c["session_id"] == "macro-qual-extraction"
    assert c["max_tokens"] == 1500
    assert c["system"] == qe._EXTRACTION_SYSTEM
    assert c["messages"][0]["role"] == "user"
    assert "<doc>" in c["messages"][0]["content"]


def test_fabric_call_replaces_both_legacy_sites_one_request(fabric_on, cfg, monkeypatch):
    """The seed attempt AND the TypeError retry collapse into ONE router call."""
    legacy = _LegacyClient(raise_type_error=True)   # would take the retry path
    monkeypatch.setattr(qe, "_client", lambda _cfg: legacy)

    text, reason = qe._call_model(BODY, "ctx", cfg, "test-model-x")

    assert (text, reason) == (REPLY, None)
    assert len(fabric_on) == 1        # exactly one logical call
    assert legacy.calls == []         # neither legacy site ran


def test_extract_end_to_end_serves_from_fabric(fabric_on, cfg, monkeypatch):
    """The public extract() entry point's model call is the router."""
    monkeypatch.setattr(qe, "_client", _legacy_never(cfg))

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(qe.config, "load", lambda: {
            "llm_models": {"extraction": "test-model-x"},
            "qual_extraction": {"enabled": True,
                                "reply_cache_dir": cfg["reply_cache_dir"]},
        })
        result = qe.extract(BODY, context="ctx")

    assert result is not None
    assert result["brain_usable"] in (True, False)
    assert len(fabric_on) == 1


def test_fabric_success_books_usage_row(fabric_on, cfg, ledger_rows, monkeypatch):
    monkeypatch.setattr(qe, "_client", _legacy_never(cfg))
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion("ok", model="deepseek-v4.1-flash", usage={
            "input_tokens": 123, "output_tokens": 45,
            "cache_read_input_tokens": 7, "cache_creation_input_tokens": 8}))

    qe._call_model(BODY, "ctx", cfg, "test-model-x")

    assert len(ledger_rows) == 1
    row = ledger_rows[0]
    assert row["lane"] == "qual-extraction"
    assert row["provider"] == "fabric"
    assert row["model"] == "deepseek-v4.1-flash"
    assert row["input_tokens"] == 123 and row["output_tokens"] == 45
    assert row["cache_read_tokens"] == 7 and row["cache_creation_tokens"] == 8


def test_ledger_failure_never_breaks_a_served_call(fabric_on, cfg, monkeypatch):
    monkeypatch.setattr(qe, "_client", _legacy_never(cfg))
    monkeypatch.setattr(ai_costs, "record_usage",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("ledger down")))

    assert qe._call_model(BODY, "ctx", cfg, "test-model-x") == (REPLY, None)


def test_fabric_reply_is_cached_for_determinism(fabric_on, cfg, monkeypatch):
    monkeypatch.setattr(qe, "_client", _legacy_never(cfg))

    qe._call_model(BODY, "same", cfg, "test-model-x")
    # Second call hits the sha-keyed cache: no second router request.
    text, reason = qe._call_model(BODY, "same", cfg, "test-model-x")

    assert (text, reason) == (REPLY, None)
    assert len(fabric_on) == 1


# --------------------------------------------------------------------------- #
# not configured / kill-switch -> legacy, unchanged
# --------------------------------------------------------------------------- #
def test_unconfigured_uses_legacy_client(cfg, monkeypatch):
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):   # must never be reached
        calls.append(kwargs)
        return _completion("should not happen")

    legacy = _LegacyClient()
    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.setattr(qe, "_client", lambda _cfg: legacy)
    monkeypatch.delenv("MACRO_QUAL_EXTRACTION_FABRIC", raising=False)

    assert qe._call_model(BODY, "ctx", cfg, "test-model-x") == (REPLY, None)
    assert calls == []                       # fabric never touched
    assert len(legacy.calls) == 1
    assert legacy.calls[0]["seed"] == 0      # byte-identical legacy ladder


def test_kill_switch_forces_legacy_even_when_configured(cfg, monkeypatch):
    calls: list[dict] = []
    legacy = _LegacyClient()

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setattr(qe, "_client", lambda _cfg: legacy)
    monkeypatch.setenv("MACRO_QUAL_EXTRACTION_FABRIC", "0")

    assert qe._call_model(BODY, "ctx", cfg, "test-model-x") == (REPLY, None)
    assert calls == []
    assert len(legacy.calls) == 1


def test_kill_switch_legacy_type_error_retry_site_unchanged(cfg, monkeypatch):
    """The SECOND legacy site (TypeError -> drop seed -> create again) still runs."""
    legacy = _LegacyClient(raise_type_error=True)

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", _legacy_never(None))
    monkeypatch.setattr(qe, "_client", lambda _cfg: legacy)
    monkeypatch.setenv("MACRO_QUAL_EXTRACTION_FABRIC", "0")

    assert qe._call_model(BODY, "ctx", cfg, "test-model-x") == (REPLY, None)
    assert len(legacy.calls) == 2
    assert "seed" in legacy.calls[0]
    assert "seed" not in legacy.calls[1]     # retry dropped seed, as before


# --------------------------------------------------------------------------- #
# router UNREACHABLE -> fall through to legacy, never degrade what it could serve
# --------------------------------------------------------------------------- #
def test_router_unavailable_falls_through_to_legacy(cfg, monkeypatch):
    calls: list[dict] = []
    legacy = _LegacyClient()

    def unavailable(messages, **kwargs):
        calls.append(kwargs)
        raise fc.FabricUnavailable("the anthropic SDK is not importable")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", unavailable)
    monkeypatch.setattr(qe, "_client", lambda _cfg: legacy)
    monkeypatch.delenv("MACRO_QUAL_EXTRACTION_FABRIC", raising=False)

    assert qe._call_model(BODY, "ctx", cfg, "test-model-x") == (REPLY, None)
    assert len(calls) == 1          # one fabric attempt, then the ladder
    assert len(legacy.calls) == 1


def test_router_unavailable_empty_legacy_reports_no_client(cfg, monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: (_ for _ in ()).throw(fc.FabricUnavailable("no sdk")))
    monkeypatch.setattr(qe, "_client", lambda _cfg: None)   # no key / no SDK
    monkeypatch.delenv("MACRO_QUAL_EXTRACTION_FABRIC", raising=False)

    assert qe._call_model(BODY, "ctx", cfg, "test-model-x") == (None, "no_client_or_key")


# --------------------------------------------------------------------------- #
# served failures -> degrade once, never retry, never walk a second provider
# --------------------------------------------------------------------------- #
def test_served_error_degrades_without_retry(cfg, monkeypatch):
    calls: list[dict] = []

    def boom(messages, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("router exhausted its ladder")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)
    monkeypatch.setattr(qe, "_client", _legacy_never(cfg))
    monkeypatch.delenv("MACRO_QUAL_EXTRACTION_FABRIC", raising=False)

    assert qe._call_model(BODY, "ctx", cfg, "test-model-x") == (None, "llm_error")
    assert len(calls) == 1


def test_served_error_books_no_usage_row(cfg, ledger_rows, monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(qe, "_client", _legacy_never(cfg))
    monkeypatch.delenv("MACRO_QUAL_EXTRACTION_FABRIC", raising=False)

    qe._call_model(BODY, "ctx", cfg, "test-model-x")
    assert ledger_rows == []


def test_refusal_drops_partial_text(cfg, monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion(
            '{"direction": "up", "confidence": "high"}', raw=_RefusalRaw()))
    monkeypatch.setattr(qe, "_client", _legacy_never(cfg))
    monkeypatch.delenv("MACRO_QUAL_EXTRACTION_FABRIC", raising=False)

    assert qe._call_model(BODY, "ctx", cfg, "test-model-x") == (None, "refusal")


def test_refusal_books_no_usage_row_and_no_cache(cfg, ledger_rows, monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion("partial", raw=_RefusalRaw()))
    monkeypatch.setattr(qe, "_client", _legacy_never(cfg))
    monkeypatch.delenv("MACRO_QUAL_EXTRACTION_FABRIC", raising=False)

    qe._call_model(BODY, "ctx", cfg, "test-model-x")
    assert ledger_rows == []
    cache_dir = Path(cfg["reply_cache_dir"])
    assert not cache_dir.exists() or not list(cache_dir.glob("*.txt"))


def test_refusal_degrades_extract_record(cfg, monkeypatch):
    """A refusal reaches extract() as the existing degraded record shape."""
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion("partial", raw=_RefusalRaw()))
    monkeypatch.setattr(qe, "_client", _legacy_never(cfg))
    monkeypatch.delenv("MACRO_QUAL_EXTRACTION_FABRIC", raising=False)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(qe.config, "load", lambda: {
            "llm_models": {"extraction": "test-model-x"},
            "qual_extraction": {"enabled": True,
                                "reply_cache_dir": cfg["reply_cache_dir"]},
        })
        result = qe.extract(BODY, context="ctx")

    assert result is not None
    assert result["degraded_reason"] == "refusal"
    assert result["brain_usable"] is False


def test_empty_reply_is_not_retried(cfg, ledger_rows, monkeypatch):
    calls: list[dict] = []

    def empty(messages, **kwargs):
        calls.append(kwargs)
        return _completion("")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", empty)
    monkeypatch.setattr(qe, "_client", _legacy_never(cfg))
    monkeypatch.delenv("MACRO_QUAL_EXTRACTION_FABRIC", raising=False)

    assert qe._call_model(BODY, "ctx", cfg, "test-model-x") == (None, "empty_reply")
    assert len(calls) == 1
    assert ledger_rows == []
