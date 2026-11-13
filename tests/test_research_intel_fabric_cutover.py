"""The research-intelligence deep-read writer routes through the Capacity Fabric.

Chairman order 2026-11-12 (estate migration, E5): the in-repo research-lab writer
``engine/research_intelligence/extractor.py`` stops walking the legacy
DeepSeek-key / Claude-OAuth ladder and instead makes one request through the
unified_router. The cutover is env-gated and scoped to that writer:

  * configured (FABRIC_ROUTER_TOKEN present) and MACRO_RESEARCH_INTEL_FABRIC != "0"
    -> one fabric_client.complete(..., lane="balanced") call, no local retry;
  * not configured, or MACRO_RESEARCH_INTEL_FABRIC=0
    -> the EXACT legacy ladder, byte-for-byte unchanged;
  * FabricUnavailable (no token / no SDK: nothing left the host) -> legacy ladder;
  * any other router error -> the writer's existing degraded return
    (``call_failed``), NEVER a retry and NEVER a second provider.

All stub-based: no network, no API keys, no provider credential. The injected
``call=`` seam still wins over both paths, so the existing selector-contract
suites are untouched.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import llm_auth as llm_auth_mod  # noqa: E402
from engine.research_intelligence import extractor  # noqa: E402
from engine.research_intelligence.extractor import analyze_document  # noqa: E402
from lib import ai_costs  # noqa: E402
from lib import fabric_client as fc  # noqa: E402

DOC = {
    "id": "doc-research-intel-fabric-1",
    "source_type": "institutional_research",
    "source_name": "Fixture Research Partners",
    "institution": "Fixture Institute",
    "desk": "Synthetic Desk",
    "title": "Synthetic fabric-cutover fixture note",
    "published_at": "2026-11-12",
}

BODY = (
    "Dr. Smith said cloud orders rose 3.5% in the third quarter. "
    "Revenue did not decline, and AMD gained share."
)


# --------------------------------------------------------------------------- #
# selector payload helpers (same shape the production prompt advertises)
# --------------------------------------------------------------------------- #
def prompt_catalog(user: str) -> dict:
    return json.loads(user.split("EVIDENCE CATALOG:\n", 1)[1].split("\n\n", 1)[0])


def prompt_identity(user: str) -> dict:
    return json.loads(
        user.split("DOCUMENT IDENTITY:\n", 1)[1].split("\n\nOUTPUT SHAPE:\n", 1)[0]
    )


def selector_payload(user: str) -> str:
    catalog = prompt_catalog(user)
    return json.dumps({
        "selector": catalog["catalog_version"],
        "document": prompt_identity(user),
        "catalog_sha256": catalog["catalog_sha256"],
        "selections": [{"evidence_id": catalog["units"][0]["evidence_id"]}],
        "analysis": {
            "thesis": {
                "summary": "The note argues cloud ordering strengthens server demand.",
                "direction": "bullish",
                "mechanism": ["cloud ordering supports server demand"],
                "conviction": "moderate",
                "support_claim_indices": [0],
            },
            "assumptions": [], "forecasts": [], "catalysts": [],
            "falsifiers": [], "counterarguments": [], "implications": [],
            "belief_delta": {"statement": "", "support_claim_indices": []},
            "consensus_relation": {"statement": "", "support_claim_indices": []},
            "uncertainties": [],
        },
    })


class _Raw:
    def __init__(self, stop_reason="end_turn"):
        self.stop_reason = stop_reason


def _completion(text, model="deepseek-v4.1-flash", stop_reason="end_turn"):
    return fc.Completion(
        text=text, model_served=model, route_id="r-1", provider="deepseek",
        usage={"input_tokens": 11, "output_tokens": 22,
               "cache_read_input_tokens": 3, "cache_creation_input_tokens": 1},
        raw=_Raw(stop_reason),
    )


@pytest.fixture(autouse=True)
def _isolated_ledger(tmp_path, monkeypatch):
    """Never let a test append a usage row to the repository's real ledger."""
    monkeypatch.setenv(ai_costs._STATE_ROOT_ENV, str(tmp_path))
    monkeypatch.delenv("AI_COSTS_SHARD", raising=False)
    return tmp_path


@pytest.fixture
def fabric_on(monkeypatch):
    """Router configured; record every complete() call."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return _completion(selector_payload(messages[0]["content"]))

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_RESEARCH_INTEL_FABRIC", raising=False)
    return calls


class _LegacyBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _LegacyResponse:
    def __init__(self, text):
        self.content = [_LegacyBlock(text)]


class _LegacyClient:
    """Stands in for the SDK client the legacy ladder hands to ``do_call``."""

    def __init__(self, text):
        self.messages = self
        self._text = text

    def create(self, **kwargs):
        return _LegacyResponse(self._text)


@pytest.fixture
def legacy_stubbed(monkeypatch):
    """Legacy ladder stubbed to a served rung; records whether it ran.

    ``make_call`` really invokes the site's ``do_call`` so the legacy path is
    exercised end to end (served model, provider, parseable reply) rather than
    short-circuited — that is what makes "the legacy ladder is unchanged" a
    real assertion instead of a call-count.
    """
    state = {"providers_calls": 0, "make_call_calls": 0}

    def fake_build_providers(*a, **kw):
        state["providers_calls"] += 1
        return [{"name": "deepseek", "model": "deepseek-v4-pro"}]

    def fake_make_call(providers, call_fn, **kw):
        state["make_call_calls"] += 1
        text, _reason, _resp = call_fn(_LegacyClient("legacy reply"), "deepseek-v4-pro")
        return text, None, "deepseek"

    monkeypatch.setattr(llm_auth_mod, "build_providers", fake_build_providers)
    monkeypatch.setattr(llm_auth_mod, "make_call", fake_make_call)
    return state


# --------------------------------------------------------------------------- #
# configured -> fabric (balanced lane), one request
# --------------------------------------------------------------------------- #
def test_configured_writer_routes_to_fabric_balanced(fabric_on):
    result = analyze_document(DOC, BODY, model_id="fixture-model")

    assert result["state"] == "ok"
    assert result["provider"] == "fabric"
    assert result["model"] == "deepseek-v4.1-flash"
    assert len(fabric_on) == 1
    call = fabric_on[0]
    assert call["lane"] == "balanced"
    assert call["project_id"] == "macro-dashboard"
    assert call["session_id"] == "macro-research-intel"
    assert call["max_tokens"] == 6000          # the existing default, passed through
    assert call["messages"] == [{"role": "user", "content": call["messages"][0]["content"]}]
    assert call["system"].startswith(extractor.SYSTEM_PROMPT.split("\n")[0])


def test_max_tokens_operator_value_is_passed_through(fabric_on):
    analyze_document(DOC, BODY, model_id="fixture-model", max_tokens=1234)
    assert fabric_on[0]["max_tokens"] == 1234


def test_injected_call_still_wins_over_fabric(fabric_on):
    """The ``call=`` seam bypasses BOTH paths — existing suites rely on it."""
    calls: list[int] = []

    def injected(system, user, *, model_id, max_tokens):
        calls.append(1)
        return selector_payload(user), "fixture-provider", "served-fixture-model"

    result = analyze_document(DOC, BODY, model_id="fixture-model", call=injected)

    assert result["state"] == "ok"
    assert result["provider"] == "fixture-provider"
    assert len(calls) == 1
    assert fabric_on == []


# --------------------------------------------------------------------------- #
# ledger: provider="fabric" + the model the router actually served
# --------------------------------------------------------------------------- #
def test_fabric_call_books_ledger_row_with_served_model(fabric_on, tmp_path):
    analyze_document(DOC, BODY, model_id="fixture-model")

    rows = ai_costs.read_usage(root=tmp_path)
    assert len(rows) == 1, rows
    row = rows[0]
    assert row["provider"] == "fabric"
    assert row["model"] == "deepseek-v4.1-flash"
    assert row["lane"] == "research-intelligence"
    assert row["stage"] == "research_intelligence"
    assert row["input_tokens"] == 11
    assert row["output_tokens"] == 22
    assert row["cache_read_tokens"] == 3
    assert row["cache_creation_tokens"] == 1


def test_unavailable_router_books_no_ledger_row(monkeypatch, legacy_stubbed, tmp_path):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: (_ for _ in ()).throw(fc.FabricUnavailable("no sdk")))
    monkeypatch.delenv("MACRO_RESEARCH_INTEL_FABRIC", raising=False)

    analyze_document(DOC, BODY, model_id="fixture-model")

    assert [r for r in ai_costs.read_usage(root=tmp_path) if r["provider"] == "fabric"] == []


# --------------------------------------------------------------------------- #
# not configured / kill-switch -> the LEGACY ladder, unchanged
# --------------------------------------------------------------------------- #
def test_unconfigured_writer_uses_legacy_ladder(monkeypatch, legacy_stubbed):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(
        fc, "complete", lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.delenv("MACRO_RESEARCH_INTEL_FABRIC", raising=False)

    result = analyze_document(DOC, BODY, model_id="fixture-model")

    assert calls == []                              # fabric never touched
    assert legacy_stubbed["providers_calls"] == 1
    assert result["provider"] == "deepseek"
    assert result["requested_model"] == "fixture-model"


def test_kill_switch_forces_legacy_even_when_configured(monkeypatch, legacy_stubbed):
    calls: list[dict] = []
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete", lambda messages, **kw: calls.append(kw) or _completion("x"))
    monkeypatch.setenv("MACRO_RESEARCH_INTEL_FABRIC", "0")

    result = analyze_document(DOC, BODY, model_id="fixture-model")

    assert calls == []
    assert legacy_stubbed["make_call_calls"] == 1
    assert result["provider"] == "deepseek"


# --------------------------------------------------------------------------- #
# FabricUnavailable -> fall through; nothing was served or billed
# --------------------------------------------------------------------------- #
def test_router_unavailable_falls_through_to_legacy_ladder(monkeypatch, legacy_stubbed):
    calls: list[dict] = []

    def unavailable(messages, **kwargs):
        calls.append(kwargs)
        raise fc.FabricUnavailable("the anthropic SDK is not importable")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", unavailable)
    monkeypatch.delenv("MACRO_RESEARCH_INTEL_FABRIC", raising=False)

    result = analyze_document(DOC, BODY, model_id="fixture-model")

    assert len(calls) == 1                          # one fabric attempt
    assert legacy_stubbed["make_call_calls"] == 1    # then the ladder
    assert result["provider"] == "deepseek"


def test_router_unavailable_with_empty_ladder_is_providers_unavailable(
        monkeypatch):
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(
        fc, "complete",
        lambda messages, **kw: (_ for _ in ()).throw(fc.FabricUnavailable("no sdk")))
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])
    monkeypatch.delenv("MACRO_RESEARCH_INTEL_FABRIC", raising=False)

    result = analyze_document(DOC, BODY, model_id="fixture-model")

    # The legacy diagnosis, not call_failed: the fabric path was never reached.
    assert result["state"] == "providers_unavailable"
    assert result["error_code"] == "NO_PROVIDER_AVAILABLE"


# --------------------------------------------------------------------------- #
# served error -> degrade exactly like a legacy failure; never retry, never
# walk a second provider (the router already walked its own ladder)
# --------------------------------------------------------------------------- #
def test_transport_error_degrades_without_retry_or_legacy(monkeypatch):
    calls: list[dict] = []

    def boom(messages, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("router exhausted its ladder")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)
    monkeypatch.setattr(
        llm_auth_mod, "build_providers",
        lambda *a, **kw: pytest.fail("legacy ladder must not run"))
    monkeypatch.delenv("MACRO_RESEARCH_INTEL_FABRIC", raising=False)

    result = analyze_document(DOC, BODY, model_id="fixture-model")

    assert result["state"] == "call_failed"
    assert result["error_class"] == "RuntimeError"
    assert result["rio"] is None
    assert len(calls) == 1            # one logical call = one request


def test_empty_reply_is_not_retried(monkeypatch, legacy_stubbed):
    calls: list[dict] = []

    def empty(messages, **kwargs):
        calls.append(kwargs)
        return _completion("")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", empty)
    monkeypatch.delenv("MACRO_RESEARCH_INTEL_FABRIC", raising=False)

    result = analyze_document(DOC, BODY, model_id="fixture-model")

    assert result["state"] == "no_model_output"
    assert len(calls) == 1
    assert legacy_stubbed["make_call_calls"] == 0


# --------------------------------------------------------------------------- #
# refusal -> dropped before the fail-closed parser, even with partial text
# --------------------------------------------------------------------------- #
def test_refusal_drops_partial_text_before_the_parser(monkeypatch):
    calls: list[dict] = []

    def refusal(messages, **kwargs):
        calls.append(kwargs)
        # A COMPLETE-LOOKING payload: if the cutover forwarded it, the parser
        # would accept it and the refusal would silently become a research truth.
        return _completion(selector_payload(messages[0]["content"]),
                           stop_reason="refusal")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", refusal)
    monkeypatch.delenv("MACRO_RESEARCH_INTEL_FABRIC", raising=False)

    result = analyze_document(DOC, BODY, model_id="fixture-model")

    assert result["state"] == "no_model_output"
    assert result["rio"] is None
    assert result["provider"] == "fabric"
    assert len(calls) == 1


# --------------------------------------------------------------------------- #
# gate shape: the flag is inert with no token, and only "0" kills it
# --------------------------------------------------------------------------- #
def test_enabled_gate_defaults_on_with_token_and_off_without(monkeypatch):
    monkeypatch.delenv("MACRO_RESEARCH_INTEL_FABRIC", raising=False)
    monkeypatch.setattr(fc, "is_configured", lambda: True)
    assert extractor._fabric_research_intel_enabled() is True

    monkeypatch.setattr(fc, "is_configured", lambda: False)
    assert extractor._fabric_research_intel_enabled() is False

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setenv("MACRO_RESEARCH_INTEL_FABRIC", "0")
    assert extractor._fabric_research_intel_enabled() is False
