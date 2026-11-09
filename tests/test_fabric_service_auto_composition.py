"""AUTO application services through actual factory, client, B and SQLite A.

The existing five-service identities and all consumer owners stay real. Only
source qualification, account grants and external provider responses are fixtures.
"""
from __future__ import annotations
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from admin import orchestrator_chat as admin
from app import main as macro_api
from engine import fabric_inference_client as transport
from engine import llm_auth as auth, provider_production_modes as owner
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests import test_fabric_service_identity_composition as _fixed
from tests.test_fabric_gateway_composition import public_brain  # noqa: F401

_CLIENT = transport.FabricInferenceClient
SOURCE_ROOT = os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT")
pytestmark = pytest.mark.skipif(not SOURCE_ROOT, reason="paired native source required")
MODEL = _fixed.MODEL
AUTO_SERVICES = tuple((record, service, lane, workload,
    transport_id.replace("native_go_", "native_fabric_").replace("_v1", "_auto_v1"))
    for record, service, lane, workload, transport_id in _fixed.SERVICES)


@pytest.fixture
def auto_native(monkeypatch):
    root = Path(SOURCE_ROOT).resolve() / _fixed.NATIVE
    pins = {**_fixed.PINS_NATIVE,
        "tests/test_application_cross_pool_auto.py": "a4844fa37548f31027b5041c35e540cd50e51ce3"}
    for relative, expected in pins.items():
        raw = (root / relative).read_bytes()
        assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == expected, relative
    original_path = list(sys.path)
    sys.path[:0] = [str(root / "tests"), str(root / "candidate"), str(root / "source"),
                   str(Path(SOURCE_ROOT).resolve())]
    for name in ("lease_broker", "go_lease_gateway", "go_lease_capability"):
        loaded = sys.modules.get(name)
        if loaded is not None:
            assert Path(loaded.__file__).resolve() == root / "candidate" / (name + ".py")
    from test_application_cross_pool_auto import CrossPoolHTTPFixture
    native = CrossPoolHTTPFixture()
    try:
        native.setUp()
        yield native
    finally:
        native.doCleanups()
        sys.path[:] = original_path

@pytest.fixture
def auto_services(binding, auto_native, monkeypatch):
    root, row, document, manifest, events, save, make, previous = binding
    native = auto_native
    # The generic fixture instruments construction with a function; AUTO must
    # prove the actual owned class, so retain the real constructor here.
    monkeypatch.setattr(transport, "FabricInferenceClient", _CLIENT)
    records, capabilities, grants = {}, [], []
    templates = [dict(grant) for grant in native.document["application_grants"]]
    scope = {"schema": "mastermind.application_route_scope.v1", "pools": ["go"]}
    factories, workloads, credentials, bindings = {}, {}, {}, []
    for record_id, service_mode_id, lane, workload, transport_id in AUTO_SERVICES:
        secret_ref = f"SYNTH_{record_id.upper()}_TOKEN"
        credential = f"synthetic-{record_id}-service-credential-0123456789abcdef"
        base = owner._APPLICATION_FABRIC_TRANSPORTS[transport_id]
        monkeypatch.setenv(secret_ref, credential)
        entry = {k: None for k in owner._APPLICATION_IDENTITY_FIELDS}
        entry.update(transport_id=transport_id, enabled=True, application_allowed=True,
                     qualification=owner.PROFILE_QUALIFIED_CANARY,
                     qualification_ref=f"fixture:{record_id}", qualified_until=time.time() + 3600)
        if service_mode_id is None:
            entry["admin_pool_view"] = True
        entry["route_scope"] = scope
        records[record_id] = entry
        capabilities.append({"capability_id": base.capability_id, "secret_ref": secret_ref,
                             "kill_state": "active", "allowed_lanes": [lane]})
        for template in templates:
            grants.append({**template, "grant_id": f"{record_id}-{template['grant_id']}",
                "principal_id": record_id, "credential_ref": secret_ref,
                "admission_root": f"service:{record_id}", "workloads": [workload]})
        bindings.append(native.go.ApplicationServiceBinding(
            record_id, "vps", workload, secret_ref, credential,
            selection_purpose=native.go.ApplicationSelectionPurpose(native.purposes["go"]),
            route_scope=native.go.ApplicationRouteScope(scope)))
        workloads[record_id] = workload
        credentials[record_id] = credential
        factories[record_id] = lambda lane=lane, workload=workload, service_mode_id=service_mode_id: (
            owner.make_application_fabric_factory(
                mode_id="shared_fabric", lane=lane, root=root,
                workload_cfg={"provider_order": ["fabric"], "workload_profile": workload},
                service_mode_id=service_mode_id))
    assert len({b.credential for b in bindings}) == len(AUTO_SERVICES)
    assert len({b.credential_ref for b in bindings}) == len(AUTO_SERVICES)
    assert len({b.principal_id for b in bindings}) == len(AUTO_SERVICES)
    # Bind the real B service registry once, before its public port is captured.
    # Old listener first goes offline before any factory can see final records.
    native.server.shutdown()
    native.server.server_close()
    native.document["application_grants"] = grants
    native.save()
    native.service = bindings[0]
    native.services = tuple(bindings)
    native.server = native.go.make_server(native.router, lease_gateway=native.gateway,
                                          application_services=native.services,
                                          application_http_binding=native.http_binding,
                                          application_native_bindings=(native.native_binding,),
                                          worker_capabilities_enabled=False)
    native.server.handle_error = lambda *args: None
    native._serve(native.server)
    for record_id, service_mode_id, lane, workload, transport_id in AUTO_SERVICES:
        secret_ref = f"SYNTH_{record_id.upper()}_TOKEN"
        credential = credentials[record_id]
        base = owner._APPLICATION_FABRIC_TRANSPORTS[transport_id]
        selected = replace(base, base_url=f"http://127.0.0.1:{native.server.server_port}/v1",
            secret_ref=secret_ref, provider_id=None, model=None,
            protocol=transport.NATIVE_PROTOCOL,
            metadata_read=(service_mode_id is None and base.metadata_read))
        monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, transport_id, selected)
        entry = records[record_id]
        entry.update({k: getattr(selected, k) for k in owner._APPLICATION_IDENTITY_FIELDS},
            transport_id=transport_id)
    document["application_fabric_modes"] = records
    manifest["capabilities"] = capabilities
    save()
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "site_interactive")
    monkeypatch.setattr(auth, "_repo_root", lambda: root)
    monkeypatch.setattr(auth, "_oauth_pool_candidates", Mock(side_effect=AssertionError("legacy")))
    monkeypatch.setattr("lib.config.secret", Mock(side_effect=AssertionError("legacy credential")))
    costs, health, closes = [], [], []
    monkeypatch.setattr("lib.ai_costs.record_usage", lambda **kw: costs.append(kw))
    monkeypatch.setattr("engine.provider_health.record_attempt", lambda **kw: health.append(kw))
    close = _CLIENT.close

    def observed_close(client):
        closes.append(client.operation_id)
        return close(client)

    monkeypatch.setattr(_CLIENT, "close", observed_close)

    def bind(record_id, operation_id, *, prior_admission_possible=False):
        factory = factories[record_id]()
        provider = auth.build_fabric_provider(
            factory, request_id=operation_id, prior_admission_possible=prior_admission_possible,
            workload_cfg={"provider_order": ["fabric"], "workload_profile": workloads[record_id]})
        return factory, provider

    return SimpleNamespace(
        root=root, native=native, records=records, factories=factories, bind=bind,
        workloads=workloads, costs=costs, health=health, closes=closes, events=events,
        save=save, document=document, manifest=manifest, credentials=credentials,
        bindings=tuple(bindings), grants=tuple(grants), monkeypatch=monkeypatch)


def admin_call(state, ident="admin-auto"):
    state.monkeypatch.setattr(admin, "_rate_ok", lambda: True)
    return admin.chat("Read the synthetic health context.", root=state.root,
        fabric_selected=True, fabric_provider_factory=state.factories["shared_fabric"](),
        request_id=ident)


def test_actual_five_named_public_service_paths_use_auto_and_actual_attribution(auto_services):
    state = auto_services
    plans = [_fixed.packet(None, tool="read_health"), _fixed.packet("Admin AUTO complete.")]
    state.native.on_upstream = lambda: setattr(state.native, "response", plans.pop(0))
    result = admin_call(state)
    assert not result["degraded"], result
    assert (result["provider"], result["model"]) == ("go", MODEL)
    assert result["input_tokens"] == 22 and result["est_cost_usd"] is None
    assert len(state.costs) == len(state.closes) == 1
    # Exercise the actual startup/HTTP handlers and paired Mastermind entrypoints
    # on the same service registry, retaining all prior request evidence.
    state.native.on_upstream = None
    api = macro_api
    assert Path(api.__file__).resolve().parents[1] == Path(auth.__file__).resolve().parents[1]
    from engine.neuralweb import ask_brain, brain_gateway
    from fastapi import BackgroundTasks
    from starlette.requests import Request
    state.monkeypatch.setenv("MACRO_REPO", str(state.root))
    state.monkeypatch.setenv("MACRO_API_STATE_DIR", str(state.root / "macro-api"))
    state.monkeypatch.setattr(api, "REPO", state.root)
    for name in ("fabric_selected", "fabric_provider_factory", "ask_fabric_selected", "ask_fabric_provider_factory"):
        state.monkeypatch.setattr(api.app.state, name, getattr(api.app.state, name, None), raising=False)
    state.monkeypatch.setattr(ask_brain, "_STATE_DIR", state.root / "ask-state")
    state.monkeypatch.setattr(brain_gateway, "_STATE_DIR", state.root / "brain-state")
    state.monkeypatch.setattr(brain_gateway, "_sb_get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("external")))
    state.monkeypatch.setattr(brain_gateway, "_check_and_increment_guest_quota",
        lambda *a, **k: (True, {"lane": "fast", "remaining": 1, "limit": 2, "period": "synthetic"}))
    api._configure_brain_fabric()
    assert api.app.state.fabric_provider_factory.service_mode_id == "macro_brain_fabric"
    assert api.app.state.ask_fabric_provider_factory.service_mode_id == "macro_ask_fabric"
    request = Request({"type": "http", "app": api.app, "method": "POST", "path": "/api/brain/chat",
        "headers": [(b"host", b"test"), (b"user-agent", b"synthetic")],
        "client": ("127.0.0.1", 12345), "server": ("127.0.0.1", 80), "scheme": "http", "query_string": b""})
    state.native.response = _fixed.packet("Ask AUTO complete.")
    asked = api.ask_brain(api.AskRequest(question="Explain a synthetic observation."), request,
        user={"id": "synthetic-user"})
    assert asked["mode"] == "live" and asked["answer"] == "Ask AUTO complete."
    assert (asked["provider"], asked["model"]) == ("go", MODEL)
    state.native.response = _fixed.packet("Brain AUTO with retained history.")
    result = api.brain_chat(api.BrainChatRequest(message="Explain a synthetic observation.",
        history=[{"role": "user", "content": "Earlier context."},
                 {"role": "assistant", "content": "Earlier answer."}]),
        request, BackgroundTasks(), user={"_is_guest": True, "_guest_aid": "synthetic-aid",
            "_guest_ip": "127.0.0.1"})
    assert not result["degraded"], result
    assert (result["provider"], result["model"]) == ("go", MODEL)
    with _fixed.real_mastermind(state) as (text_owner, chat_owner, advisor, bot_mcp, root):
        state.native.response = _fixed.packet("MM text AUTO complete.")
        assert text_owner.call_model("Synthetic system", "Synthetic user") == ("MM text AUTO complete.", None)
        plans = [_fixed.packet(None, tool="mcp__bot__get_portfolio"), _fixed.packet("MM chat AUTO complete.")]
        state.native.on_upstream = lambda: setattr(state.native, "response", plans.pop(0))
        import asyncio
        async def collect():
            return [event async for event in chat_owner.chat_stream(
                "Read the synthetic book.", conversation_id="auto-public", turn_id="auto-turn")]
        events = asyncio.run(collect())
        assert events[-1]["type"] == "done", events
        assert (events[-1]["provider"], events[-1]["model"]) == ("go", MODEL)
        with advisor.fabric_conversation("auto-public", scope="portfolio_advisor") as document:
            turn = document["turns"][0]
            assert turn["schema"] == "mastermind.advisor.fabric_turn.v2"
            assert turn["close"]["closed"] is True
    turns = state.native.rows("application_turns")
    assert {row["principal_id"] for row in turns} == {row[0] for row in AUTO_SERVICES}
    assert len(turns) == len(state.closes) == 5
    assert len(state.native.rows("application_requests")) == len(state.native.posts) == 7
    assert all(row["state"] == "released" for row in state.native.rows("leases"))
    assert all(row["provider"] == "go" and row["model"] == MODEL
               and row["cost_basis"] == "unknown" for row in state.costs)
    assert all(row.get("est_cost_usd") is None for row in state.costs)


def test_admin_malformed_route_preserves_correlated_usage_with_unknown_pool(auto_services):
    state = auto_services
    state.native.response = _fixed.packet()
    handler = state.native.server.RequestHandlerClass
    original = handler._application_routed_result
    def corrupt(handler, outcome):
        result = original(handler, outcome)
        value = json.loads(result.body)
        value["application"]["routing"]["protocol"] = []
        raw = json.dumps(value, separators=(",", ":")).encode()
        return replace(result, body=raw, delivery_digest=hashlib.sha256(raw).hexdigest())
    state.monkeypatch.setattr(handler, "_application_routed_result", corrupt)
    result = admin_call(state)
    assert result["degraded"] and result["usage_state"] == "unknown", result
    assert (result["provider"], result["model"]) == ("unknown", MODEL)
    assert len(state.native.posts) == len(state.closes) == len(state.costs) == 1
    row = state.costs[0]
    assert (row["provider"], row["model"], row["input_tokens"], row["output_tokens"]) == ("unknown", MODEL, 11, 7)
    assert row["cost_basis"] == "unknown" and row["est_cost_usd"] is None
    assert "fabric_route" not in row


@pytest.mark.parametrize("streaming", [False, True])
def test_brain_terminal_error_retains_actual_model_and_usage_once(auto_services, public_brain, streaming):
    from engine.neuralweb import brain_gateway as brain
    state = auto_services
    costs, tokens, tool, options = public_brain
    state.native.response = _fixed.packet(model="observed-other")
    options.update(root=state.root, fabric_provider_factory=state.factories["macro_brain_fabric"]())
    if streaming:
        events = [json.loads(line[6:]) for line in brain.chat_stream(**options) if line.startswith("data: ")]
        result = events[-1]
    else:
        result = brain.chat(**options)
    assert result["degraded"], result
    assert (result["provider"], result["model"]) == ("go", "observed-other")
    assert len(state.native.posts) == len(state.closes) == len(costs) == 1
    assert costs[0]["model"] == "observed-other"
    assert (costs[0]["input_tokens"], costs[0]["output_tokens"]) == (11, 7)
    assert costs[0]["cost_basis"] == "unknown"
    assert not tool.called


def test_ask_generator_close_never_runs_tool_or_second_request(auto_services):
    from engine.neuralweb import ask_brain as ask
    state = auto_services
    state.monkeypatch.setattr(ask, "_STATE_DIR", state.root / "ask-state")
    state.monkeypatch.setattr(ask, "_analyst_block", lambda question: "")
    tool = Mock(side_effect=AssertionError("tool after subscriber close"))
    state.monkeypatch.setattr(ask, "_dispatch_read_tool", tool)
    state.native.response = _fixed.packet(None, tool="read_world_state")
    stream = ask.ask_stream("Explain a synthetic observation.", "synthetic-user", root=state.root,
        fabric_selected=True, fabric_provider_factory=state.factories["macro_ask_fabric"]())
    assert json.loads(next(stream)[6:])["status"] == "thinking"
    assert json.loads(next(stream)[6:])["status"] == "reading"
    stream.close()
    assert not tool.called
    assert len(state.native.posts) == len(state.closes) == len(state.costs) == 1
    assert state.costs[0]["provider"] == "go" and state.costs[0]["model"] == MODEL
