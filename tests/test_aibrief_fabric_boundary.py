"""Consumer contract against the incumbent Fabric API; no real inference."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from engine.aibrief_runtime import Prepared, generate, prepare


def harness(monkeypatch, *, mode="success", close=True):
    owner = ModuleType("engine.llm_auth")
    events = []
    provider = {"model": "qualified-model", "provider": "fabric-owner", "_fabric_step": 0,
                "_fabric_pending": False}
    def bind(factory, **kw):
        events.append(("bind", kw["request_id"]))
        if mode == "binding_error":
            raise RuntimeError("binding unavailable")
        return provider
    def call(providers, callback, **kw):
        assert providers == [provider]
        events.append(("call",))
        if mode == "refusal_tuple":
            return None, "permission_denied", "fabric"
        provider["_fabric_step"] = 1
        if mode in ("unknown", "refusal"):
            provider["_fabric_native_disposition"] = "effect_unknown" if mode == "unknown" else "refused"
            error = ValueError("no raw transport details")
            error.effect_unknown = mode == "unknown"
            raise error
        response = SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(
            type="text", text=json.dumps({"summary": "A qualified read.", "confidence": "medium"}))])
        client = SimpleNamespace(messages=SimpleNamespace(create=lambda **args: response))
        text, reason, _ = callback(client, provider["model"])
        return text, reason, "fabric"
    def finish(p):
        events.append(("close",))
        p["_fabric_close"] = {"closed": close, "effect_unknown": not close,
                              "attempted": True, "disposition": "closed" if close else "effect_unknown"}
    owner.build_fabric_provider, owner.make_call, owner.close_fabric_provider = bind, call, finish
    monkeypatch.setitem(sys.modules, "engine.llm_auth", owner)
    import engine
    monkeypatch.setattr(engine, "llm_auth", owner, raising=False)
    brain = SimpleNamespace(LENSES={"macro": {"system": "Existing prompt {thesis}"}},
                            _thesis_for=lambda *a: "existing thesis", _extract_json=json.loads,
                            _collect_style_violations=lambda _: [])
    result = generate({"macro": {"date": datetime.now(timezone.utc).date().isoformat()}}, {},
                      lens="macro", root=Path("/test"), operation_id="aibrief:macro:original",
                      prepared=Prepared(object(), {"provider_order": ["fabric"]}, "qualified"), brain=brain)
    return result, events


def test_one_native_operation_and_actual_serving_identity(monkeypatch):
    result, events = harness(monkeypatch)
    assert result.state == "succeeded" and result.close_confirmed
    assert result.brief["served_by"] == "fabric-owner" and result.brief["model"] == "qualified-model"
    assert result.brief["theses"] == []
    assert [e[0] for e in events] == ["bind", "call", "close"]


@pytest.mark.parametrize("mode,expected", [("unknown", "effect_unknown"),
                                          ("refusal", "refused"), ("refusal_tuple", "refused"),
                                          ("binding_error", "unavailable")])
def test_owner_disposition_survives_without_fallback(monkeypatch, mode, expected):
    result, events = harness(monkeypatch, mode=mode)
    assert result.state == expected
    assert len([e for e in events if e[0] == "call"]) <= 1
    assert result.brief is None


def test_known_text_survives_unknown_close_but_operation_stays_held(monkeypatch):
    result, _ = harness(monkeypatch, close=False)
    assert result.state == "effect_unknown" and result.brief["summary"] == "A qualified read."
    assert result.close_confirmed is False


def test_absent_host_selection_never_discovers_legacy_credentials(monkeypatch):
    owner = ModuleType("engine.provider_production_modes")
    owner.make_application_fabric_factory = lambda **kw: pytest.fail("unselected owner")
    monkeypatch.setitem(sys.modules, "engine.provider_production_modes", owner)
    import engine
    monkeypatch.setattr(engine, "provider_production_modes", owner, raising=False)
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE", raising=False)
    with pytest.raises(RuntimeError, match="fabric_not_selected"):
        prepare(Path("/test"), {})
