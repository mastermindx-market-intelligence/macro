"""The admin contradiction classifier routes through the Capacity Fabric.

Chairman estate migration outcome #3 (2026-11-12): admin/mastermind_logs.py's
classify tier moves from a raw urllib POST to api.deepseek.com onto the
unified_router through lib.fabric_client. The cutover is env-gated:

  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_LOGS_CLASSIFY_FABRIC != "0"
    -> ONE fabric_client.complete(..., lane="fast") per row, no local retry and no
       second provider (the router owns its ladder);
  * not configured, or MACRO_LOGS_CLASSIFY_FABRIC=0
    -> the EXACT raw-urllib POST, byte-for-byte unchanged;
  * FabricUnavailable (nothing left this host) -> that legacy POST;
  * any other served error -> degrade (None), never retry, never re-raise;
  * stop_reason == "refusal" -> no verdict, even with partial text attached;
  * empty text -> no verdict;
  * a served call books ai_costs.record_usage(provider="fabric",
    lane="logs-classify") and never raises if the ledger write fails.

All stub-based: no network, no API keys.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from admin import mastermind_logs as ml  # noqa: E402
from lib import ai_costs  # noqa: E402
from lib import fabric_client as fc  # noqa: E402


class _Raw:
    stop_reason = "end_turn"


class _RefusalRaw:
    stop_reason = "refusal"


def _completion(text, model="deepseek-v4.1-flash", raw=None, usage=None):
    return fc.Completion(text=text, model_served=model, route_id="r-1",
                         provider="deepseek", usage=usage or {"output_tokens": 5},
                         raw=raw or _Raw())


_VERDICT = {"contradiction": "system_error", "signals": ["breadth", "credit"],
            "note": "one is stale"}


@pytest.fixture(autouse=True)
def ledger_rows(monkeypatch):
    """Never write data/ai_costs rows in a unit test; capture them instead."""
    rows: list[dict] = []
    monkeypatch.setattr(ai_costs, "record_usage",
                        lambda **kw: rows.append(kw) or True)
    return rows


@pytest.fixture
def legacy_post(monkeypatch):
    """Stub the legacy urllib POST; record that it ran and what it returned."""
    calls: list[dict] = []
    payload: dict = {"content": [{"type": "text", "text": json.dumps(_VERDICT)}]}

    class _Resp:
        def __init__(self, body):
            self._body = body

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        calls.append({"url": req.full_url, "body": json.loads(req.data.decode())})
        return _Resp(json.dumps(payload).encode())

    monkeypatch.setattr(ml.urllib.request, "urlopen", fake_urlopen)
    return calls


@pytest.fixture
def fabric_on(monkeypatch):
    """Router configured; record every complete() call."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return _completion(json.dumps(_VERDICT))

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_LOGS_CLASSIFY_FABRIC", raising=False)
    return calls


@pytest.fixture
def fabric_off(monkeypatch):
    """Router NOT configured; complete() must never be reached."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):   # must never be reached
        calls.append(kwargs)
        return _completion("should not happen")

    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_LOGS_CLASSIFY_FABRIC", raising=False)
    return calls


_PROMPT = ml._classify_prompt({
    "question": "q", "answer": "a", "thinking": [{"phase": "p", "round": 1, "text": "t"}]})


def _seed(root, rows):
    """One response-log row per dict, in the ledger the classifier reads."""
    d = root / "data" / "mastermind"
    d.mkdir(parents=True, exist_ok=True)
    (d / "response_log.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# configured -> one fabric call on the fast lane
# --------------------------------------------------------------------------- #
def test_configured_classifies_through_fabric_fast(fabric_on, legacy_post):
    out = ml._classify_call(_PROMPT, "unused-key")

    assert out == _VERDICT
    assert legacy_post == []                 # the urllib path never ran
    assert len(fabric_on) == 1
    call = fabric_on[0]
    assert call["lane"] == "fast"
    assert call["client"] == "Python client"
    assert call["project_id"] == "macro-dashboard"
    assert call["session_id"] == "macro-logs-classify"
    assert call["max_tokens"] == 400
    assert call["system"] == ml._CLASSIFY_INSTRUCTIONS
    # The instructions are lifted into the system block, so the user turn carries the
    # DATA section only — no duplicated instructions.
    assert call["messages"][0]["role"] == "user"
    assert "<<<DATA" in call["messages"][0]["content"]
    assert not call["messages"][0]["content"].startswith("You are auditing")


def test_fabric_success_books_usage_row(fabric_on, legacy_post, ledger_rows, monkeypatch):
    def fake_complete(messages, **kwargs):
        fabric_on.append({"messages": messages, **kwargs})
        return _completion("x", model="deepseek-v4.1-flash", usage={
            "input_tokens": 123, "output_tokens": 45,
            "cache_read_input_tokens": 7, "cache_creation_input_tokens": 8})

    monkeypatch.setattr(fc, "complete", fake_complete)
    ml._classify_call(_PROMPT, "unused-key")

    assert len(ledger_rows) == 1
    row = ledger_rows[0]
    assert row["lane"] == "logs-classify"
    assert row["provider"] == "fabric"
    assert row["model"] == "deepseek-v4.1-flash"
    assert row["input_tokens"] == 123 and row["output_tokens"] == 45
    assert row["cache_read_tokens"] == 7 and row["cache_creation_tokens"] == 8
    assert row["stage"] == "mastermind_logs"


def test_ledger_failure_does_not_lose_the_verdict(fabric_on, legacy_post, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(ai_costs, "record_usage", boom)
    assert ml._classify_call(_PROMPT, "unused-key") == _VERDICT


def test_classify_contradictions_writes_a_fabric_verdict(fabric_on, legacy_post, tmp_path):
    _seed(tmp_path, [{"id": "a", "question": "q", "answer": "the readings conflict"}])
    out = ml.classify_contradictions(limit=5, root=tmp_path)

    assert out["ok"] and out["classified"] == 1
    assert out["verdicts"] == {"system_error": 1}
    assert len(fabric_on) == 1
    assert legacy_post == []


# --------------------------------------------------------------------------- #
# not configured / kill-switch -> the untouched legacy POST
# --------------------------------------------------------------------------- #
def test_unconfigured_uses_legacy_urllib(fabric_off, legacy_post):
    out = ml._classify_call(_PROMPT, "k")

    assert out == _VERDICT
    assert fabric_off == []                  # fabric never touched
    assert len(legacy_post) == 1
    assert legacy_post[0]["url"] == ml._CLASSIFY_URL
    assert legacy_post[0]["body"]["model"] == ml._CLASSIFY_MODEL
    assert legacy_post[0]["body"]["thinking"] == {"type": "disabled"}


def test_kill_switch_forces_legacy_even_when_configured(monkeypatch, legacy_post):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete",
                        lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setenv("MACRO_LOGS_CLASSIFY_FABRIC", "0")

    assert ml._classify_call(_PROMPT, "k") == _VERDICT
    assert calls == []
    assert len(legacy_post) == 1


# --------------------------------------------------------------------------- #
# router unreachable -> nothing left the host -> legacy POST
# --------------------------------------------------------------------------- #
def test_router_unavailable_falls_through_to_legacy(monkeypatch, legacy_post):
    calls: list[dict] = []

    def unavailable(messages, **kwargs):
        calls.append(kwargs)
        raise fc.FabricUnavailable("the anthropic SDK is not importable")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", unavailable)
    monkeypatch.delenv("MACRO_LOGS_CLASSIFY_FABRIC", raising=False)

    assert ml._classify_call(_PROMPT, "k") == _VERDICT
    assert len(calls) == 1                   # one fabric attempt
    assert len(legacy_post) == 1             # then the unchanged legacy POST


# --------------------------------------------------------------------------- #
# served failures -> degrade once, never retry, never fall back to another provider
# --------------------------------------------------------------------------- #
def test_served_error_degrades_without_retry(monkeypatch, legacy_post):
    calls: list[dict] = []

    def boom(messages, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("router exhausted its ladder")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)
    monkeypatch.delenv("MACRO_LOGS_CLASSIFY_FABRIC", raising=False)

    assert ml._classify_call(_PROMPT, "k") is None
    assert len(calls) == 1                   # exactly one attempt
    assert legacy_post == []                 # no second provider behind the router


def test_served_error_counts_as_a_skip_not_a_crash(fabric_on, legacy_post, tmp_path):
    def boom(messages, **kwargs):
        raise RuntimeError("router exhausted its ladder")

    fabric_on.clear()
    _seed(tmp_path, [{"id": "a", "question": "q", "answer": "the readings conflict"}])
    import unittest.mock as _m
    with _m.patch.object(fc, "complete", boom):
        out = ml.classify_contradictions(limit=5, root=tmp_path)

    assert out["ok"] is True and out["classified"] == 0 and out["skipped"] == 1
    assert not (tmp_path / "data" / "mastermind" / "response_eval.jsonl").exists()


def test_refusal_drops_partial_text(fabric_on, legacy_post, ledger_rows, monkeypatch):
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: _completion(json.dumps(_VERDICT), raw=_RefusalRaw()))

    assert ml._classify_call(_PROMPT, "k") is None
    assert ledger_rows == []                 # nothing served, nothing billed
    assert legacy_post == []


def test_empty_text_is_not_a_verdict(fabric_on, legacy_post, ledger_rows, monkeypatch):
    monkeypatch.setattr(fc, "complete", lambda messages, **kw: _completion(""))

    assert ml._classify_call(_PROMPT, "k") is None
    assert ledger_rows == []


def test_keyless_batch_served_by_fabric_succeeds(fabric_on, legacy_post, tmp_path,
                                                 monkeypatch):
    """No DeepSeek key is fine when the router serves the rows."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    _seed(tmp_path, [{"id": "a", "question": "q", "answer": "the readings conflict"}])

    out = ml.classify_contradictions(limit=5, root=tmp_path)
    assert out["ok"] is True and out["classified"] == 1
    assert legacy_post == []


def test_keyless_batch_with_a_dead_router_reports_no_llm_key(tmp_path, monkeypatch):
    """The batch is let past the key gate only because the fabric promised to serve it.
    If the router is unreachable AND there is no key, "ok: True, skipped: N" would tell
    the operator nothing — the documented fail-soft answer is no_llm_key."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: (_ for _ in ()).throw(fc.FabricUnavailable("no sdk")))
    monkeypatch.delenv("MACRO_LOGS_CLASSIFY_FABRIC", raising=False)
    _seed(tmp_path, [{"id": "a", "question": "q", "answer": "the readings conflict"}])

    out = ml.classify_contradictions(limit=5, root=tmp_path)
    assert out["ok"] is False and out["error"] == "no_llm_key"
    assert "unreachable" in out["note"]


# --------------------------------------------------------------------------- #
# the admin venv must actually ship the SDK the adapter imports
# --------------------------------------------------------------------------- #
def test_admin_requirements_carry_the_anthropic_sdk():
    req = (Path(__file__).resolve().parent.parent / "admin" / "requirements.txt").read_text()
    lines = [ln.split("#", 1)[0].strip() for ln in req.splitlines()]
    assert any(ln.startswith("anthropic") for ln in lines if ln), (
        "admin/requirements.txt must install the anthropic SDK, or the fabric branch "
        "raises FabricUnavailable in the admin venv and the cutover is inert")
