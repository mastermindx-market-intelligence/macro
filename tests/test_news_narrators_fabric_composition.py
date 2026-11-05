"""Actual news narrators through the shared application owner.

Provider responses and source data are synthetic; these tests do not qualify a
live pool. The final case also uses the exact paired gateway and actual wire.
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from engine import china_news, china_news_intel, llm_auth as auth, macro_news
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_shared_default import MODEL, response, selected  # noqa: F401

CASES = [(macro_news, "macro-news"), (china_news, "china-news"),
         (china_news_intel, "china-news-intel")]
HEADLINES = [{"title": "Measured policy announcement", "theme": "monetary", "domain": "fixture.test"}]


def entry(module):
    if module is macro_news:
        return module.macro_brief(HEADLINES, "Measured regime", "Neutral", "CPI Thursday")
    panel = module.panel("2026-11-05")
    return panel["brief"] if panel else None


@pytest.fixture
def narration(monkeypatch):
    cfg = {"enabled": True, "llm_brief": True, "llm_model": "legacy-requested-model"}
    for module, _ in CASES:
        monkeypatch.setattr(module, "_cfg", lambda: dict(cfg))
    # Selected Fabric must work even when the optional native SDK is absent.
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(
        Anthropic=Mock(side_effect=AssertionError("legacy client"))))
    monkeypatch.setattr(china_news, "policy_tone", lambda asof: None)
    monkeypatch.setattr(china_news, "flash_headlines", lambda: {"headlines": HEADLINES})
    monkeypatch.setattr(china_news_intel, "sentiment", lambda asof: None)
    monkeypatch.setattr(china_news_intel, "feed", lambda: {"items": HEADLINES})
    return cfg


@pytest.fixture
def selected_narration(selected, narration, monkeypatch):
    selected.manifest["capabilities"][0]["allowed_lanes"] += [lane for _, lane in CASES]
    selected.save()
    selected.closed = []
    original_close = auth.close_fabric_provider

    def observe_close(provider):
        original_close(provider)
        selected.closed.append(provider)

    monkeypatch.setattr(auth, "close_fabric_provider", observe_close)
    return selected


@pytest.mark.parametrize("module,lane", CASES)
def test_actual_public_entries_bind_fresh_and_close_with_truthful_identity(selected_narration, module, lane):
    state = selected_narration
    assert module._llm_ready(module._cfg()) and not state.clients and not state.events
    first, second = entry(module), entry(module)
    assert first == second == {"text": "Grounded context.", "model": MODEL,
                              "provider": "fixture-provider", "is_context_only": True}
    assert len(state.calls) == len(state.clients) == len(state.costs) == len(state.closed) == 2
    assert state.calls[0]["request_id"] != state.calls[1]["request_id"]
    assert all(p["_fabric_closed"] for p in state.closed)
    assert all(row["model"] == MODEL and row["provider"] == "fixture-provider"
               and row["lane"] == lane for row in state.costs)
    assert all(row["model"] == MODEL and row["max_tokens"] == 220 for row in state.calls)


@pytest.mark.parametrize("module,lane", CASES)
def test_feature_and_empty_input_gates_remain_network_free(selected_narration, narration, module, lane):
    narration["llm_brief"] = False
    assert entry(module) is None
    narration["llm_brief"] = True
    narration["enabled"] = False
    assert entry(module) is None
    narration["enabled"] = True
    function = module.macro_brief if module is macro_news else module.news_brief
    assert function([]) is None
    assert not selected_narration.clients and not selected_narration.events


@pytest.mark.parametrize("module,lane", CASES)
@pytest.mark.parametrize("profile", [None, "", "development_agent"])
def test_explicit_invalid_profiles_are_not_defaulted(selected_narration, narration, module, lane, profile):
    narration["workload_profile"] = profile
    assert entry(module) is None
    assert not selected_narration.calls and not selected_narration.events


@pytest.mark.parametrize("module,lane", CASES)
def test_invalid_host_and_owner_revocation_never_discover_native(selected_narration, monkeypatch, module, lane):
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "")
    assert not module._llm_ready(module._cfg()) and entry(module) is None
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
    selected_narration.row["enabled"] = False
    selected_narration.save()
    assert module._llm_ready(module._cfg()) and entry(module) is None
    assert not selected_narration.calls and not selected_narration.events


@pytest.mark.parametrize("module,lane", CASES)
def test_caller_selection_and_unknown_usage_remain_truthful(selected_narration, narration, monkeypatch, module, lane):
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    narration["application_fabric_mode"] = "shared_fabric"
    selected_narration.plans = [response(tokens=None)]
    result = entry(module)
    assert result["model"] == MODEL and result["provider"] == "fixture-provider"
    assert len(selected_narration.calls) == 1 and not selected_narration.costs


@pytest.mark.parametrize("module,lane", CASES)
@pytest.mark.parametrize("failure", ["timeout", "type_error", "tools", "empty", "truncated"])
def test_failure_never_rebinds_or_falls_back_and_closes(selected_narration, module, lane, failure):
    if failure == "timeout":
        plan = TimeoutError("synthetic interrupted request")
    elif failure == "type_error":
        plan = TypeError("synthetic response failure")
    elif failure == "tools":
        plan = response(tools=True)
    elif failure == "empty":
        plan = response(text="")
    else:
        plan = response()
        plan.stop_reason = "max_tokens"
    selected_narration.plans = [plan]
    assert entry(module) is None
    assert len(selected_narration.calls) == len(selected_narration.clients) == 1
    assert len(selected_narration.closed) == 1 and selected_narration.closed[0]["_fabric_closed"]
    assert len(selected_narration.costs) == (0 if failure in {"timeout", "type_error"} else 1)


@pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"), reason="paired gateway required")
def test_all_three_public_narrators_reach_actual_owner_gateway(narration, monkeypatch, tmp_path):
    import hashlib
    import importlib.util
    from pathlib import Path

    import yaml
    from tests.test_fabric_gateway_composition import (
        GATEWAY_BLOB, MODEL as WIRE_MODEL, configure_owned_application,
        owner_gateway, packet, status,
    )

    path = Path(os.environ["MM_FABRIC_GATEWAY_SOURCE_ROOT"]) / "ops/native_fabric/experiential_proxy/gateway.py"
    raw = path.read_bytes()
    assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == GATEWAY_BLOB
    spec = importlib.util.spec_from_file_location("_news_narrator_paired_gateway", path)
    gateway = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, gateway)
    spec.loader.exec_module(gateway)
    costs = []
    monkeypatch.setattr("lib.ai_costs.record_usage", lambda **kw: costs.append(kw))
    monkeypatch.setattr("engine.provider_health.record_attempt", lambda **kw: None)
    monkeypatch.setattr("lib.config.secret", Mock(side_effect=AssertionError("legacy credential")))
    with owner_gateway(gateway, tmp_path, [packet() for _ in CASES]) as (url, calls, wire, app):
        manifest_path, manifest = configure_owned_application(monkeypatch, tmp_path, url)
        manifest["capabilities"][0]["allowed_lanes"] += [lane for _, lane in CASES]
        manifest_path.write_text(yaml.safe_dump(manifest))
        monkeypatch.setattr(auth, "_repo_root", lambda: tmp_path)
        for module, _ in CASES:
            result = entry(module)
            assert result["model"] == WIRE_MODEL and result["is_context_only"]
        snapshot = status(app)
    assert len(calls) == len(wire) == len(costs) == 3
    assert len({row["headers"]["idempotency-key"] for row in calls}) == 3
    assert all(row["provider"] == "fixture-provider" and row["model"] == WIRE_MODEL for row in costs)
    assert snapshot["shared_used_in_window"] == 3 and snapshot["pending"] == 0
