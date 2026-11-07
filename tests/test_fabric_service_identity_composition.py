"""Five distinct service identities through real Macro and Mastermind application owners.

Only qualification, service accounts, upstream responses and business-data
locations are synthetic. The same real B gateway/A database serves every
identity; factory/auth/client/B/A and the named public entrypoints stay real.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
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
import yaml

from engine import fabric_inference_client as transport
_CLIENT = transport.FabricInferenceClient
from engine import llm_auth as auth
from engine import provider_production_modes as owner
from tests.test_fabric_application_binding import binding  # noqa: F401

SOURCE_ROOT = os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT")
pytestmark = pytest.mark.skipif(not SOURCE_ROOT, reason="paired Mastermind native checkout required")
MODEL = "fixture-model"
NATIVE = "ops/native_fabric/quota_continuity/"
PINS_NATIVE = {
    "candidate/commission_deadline.py": "fade630ed75c1b93334a5711a6df7a554fbd24ee",
    "candidate/go_shim.py": "969ffaf84e23ef2d1c0398761943093c9b5c9456",
    "candidate/lease_broker.py": "3c1360866b6a4fcdc2f9d72732d0439361e3d0c7",
    "candidate/go_lease_gateway.py": "9a30985f744be11b8ce3f2514baef5b494b4471a",
    "candidate/go_lease_capability.py": "38856700331b3fb3a7706a5745e23fb7b3d18cf0",
    "candidate/provider_outcome.py": "981f35a01183e83fdb9f0b8a4175b290cdeb85f8",
    "candidate/quota_circuit.py": "1583a6ba773e56dbc3f295b65ffc08dea2d31d48",
    "source/model_tier.py": "96093c2747d2dda69b3f2255cb84e656355c87ea",
    "source/pool_status.py": "02922043357d63b4bcfa3791899df27a5c42be12",
    "tests/_offline_boundary.py": "e511ab65fe1cd30bf4d2addac6700ca43c3468da",
    "tests/test_go_application_handler_composition.py": "13ebd6bcee5167926807d7ccdc63bcabed0cf1b1",
    "tests/test_application_turn_admission.py": "8487163bb0904f8b95f0a9b326efa1622cd0ad0e",
}
SERVICES = (
    ("shared_fabric", None, "admin-orchestrator", "site_interactive", "native_go_application_v1"),
    ("mastermind_text_fabric", "mastermind_text_fabric", "mastermind-text", "site_batch",
     "native_go_mastermind_text_v1"),
    ("mastermind_chat_fabric", "mastermind_chat_fabric", "mastermind-chat", "site_interactive",
     "native_go_mastermind_chat_v1"),
    ("macro_brain_fabric", "macro_brain_fabric", "brain", "site_interactive", "native_go_macro_brain_v1"),
    ("macro_ask_fabric", "macro_ask_fabric", "ask-brain", "site_interactive", "native_go_macro_ask_v1"),
)


@pytest.fixture
def native_application(monkeypatch):
    root = Path(SOURCE_ROOT).resolve() / NATIVE
    for relative, expected in PINS_NATIVE.items():
        raw = (root / relative).read_bytes()
        assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == expected, relative
    original_path = list(sys.path)
    sys.path[:0] = [str(root / "tests"), str(root / "candidate"), str(root / "source")]
    for name in ("lease_broker", "go_lease_gateway", "go_lease_capability"):
        loaded = sys.modules.get(name)
        if loaded is not None:
            assert Path(loaded.__file__).resolve() == root / "candidate" / (name + ".py")
    spec = importlib.util.spec_from_file_location("_native_application_pair_current",
        root / "tests/test_go_application_handler_composition.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    fixture = module.NativeApplicationHTTPFixture()
    fixture.setUp()
    try:
        yield fixture
    finally:
        fixture.doCleanups()
        sys.modules.pop(spec.name, None)
        sys.path[:] = original_path


@pytest.fixture
def services(binding, native_application, monkeypatch):
    root, row, document, manifest, events, save, make, previous = binding
    native = native_application
    records, capabilities, grants = {}, [], []
    factories, workloads, credentials, bindings = {}, {}, {}, []
    for record_id, service_mode_id, lane, workload, transport_id in SERVICES:
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
        records[record_id] = entry
        capabilities.append({"capability_id": base.capability_id, "secret_ref": secret_ref,
                             "kill_state": "active", "allowed_lanes": [lane]})
        grants.append({**native.grant, "grant_id": f"synthetic-{record_id}-grant",
            "principal_id": record_id, "credential_ref": secret_ref,
            "admission_root": f"service:{record_id}", "workloads": [workload],
            "accounts": ["account-a"]})
        bindings.append(native.go.ApplicationServiceBinding(
            record_id, "vps", workload, secret_ref, credential))
        workloads[record_id] = workload
        credentials[record_id] = credential
        factories[record_id] = lambda lane=lane, workload=workload, service_mode_id=service_mode_id: (
            owner.make_application_fabric_factory(
                mode_id="shared_fabric", lane=lane, root=root,
                workload_cfg={"provider_order": ["fabric"], "workload_profile": workload},
                service_mode_id=service_mode_id))
    assert len({b.credential for b in bindings}) == len(SERVICES)
    assert len({b.credential_ref for b in bindings}) == len(SERVICES)
    assert len({b.principal_id for b in bindings}) == len(SERVICES)
    # Bind the real B service registry once, before its public port is captured.
    # Old listener first goes offline before any factory can see final records.
    native.server.shutdown()
    native.server.server_close()
    native.document["application_grants"] = grants
    native.save()
    native.service = bindings[0]
    native.services = tuple(bindings)
    native.server = native.go.make_server(native.router, lease_gateway=native.gateway,
                                          application_services=native.services)
    native.server.handle_error = lambda *args: None
    native._serve(native.server)
    for record_id, service_mode_id, lane, workload, transport_id in SERVICES:
        secret_ref = f"SYNTH_{record_id.upper()}_TOKEN"
        credential = credentials[record_id]
        base = owner._APPLICATION_FABRIC_TRANSPORTS[transport_id]
        selected = replace(base, base_url=f"http://127.0.0.1:{native.server.server_port}/v1",
            secret_ref=secret_ref, provider_id="go", model=MODEL,
            protocol=transport.NATIVE_PROTOCOL, qualified=True, application_allowed=True,
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


@contextmanager
def real_mastermind(state):
    """Load the actual counterpart package, backed by the same real B/A pair."""
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))
    import bot
    vendor = Path(bot._VENDOR)
    assert vendor.is_symlink(), "counterpart must retain its actual Macro vendor link"
    vendor_target = vendor.readlink()
    vendor.unlink()
    vendor.symlink_to(Path(auth.__file__).resolve().parent.parent)
    saved = {}
    try:
        from brain import advisor, bot_mcp, fabric_chat, fabric_inference, thinking_log
        from portfolio import registry
        o, shared, macro_root = fabric_inference._owner()
        assert o is owner and shared is auth
        saved = {path: path.read_bytes() for path in (macro_root / "config").glob("provider_*.v1.json")}
        saved[macro_root / "config/capability_manifest.yml"] = (
            macro_root / "config/capability_manifest.yml").read_bytes()
        (macro_root / "config/provider_production_modes.v1.json").write_text(json.dumps(state.document))
        (macro_root / "config/provider_workloads.v1.json").write_bytes(
            (state.root / "config/provider_workloads.v1.json").read_bytes())
        (macro_root / "config/capability_manifest.yml").write_text(yaml.safe_dump(state.manifest))
        # Conversation/business paths are disposable; no legacy provider is used.
        state.monkeypatch.setattr(advisor, "_ROOT", Path(SOURCE_ROOT).resolve())
        state.monkeypatch.setattr(advisor, "_HISTORY", state.root / "mm-history")
        state.monkeypatch.setattr(advisor, "_SESSIONS", state.root / "mm-sdk-sessions.json")
        state.monkeypatch.setattr(bot_mcp, "_ROOT", state.root)
        state.monkeypatch.setattr(registry, "_ROOT", state.root)
        state.monkeypatch.setattr(thinking_log, "log_turn_async", lambda **kw: None)
        yield fabric_inference, fabric_chat, advisor, bot_mcp, macro_root
    finally:
        for path, raw in saved.items():
            path.write_bytes(raw)
        vendor.unlink()
        vendor.symlink_to(vendor_target)


def packet(text="Measured context.", *, model=MODEL, tool=None):
    message = {"role": "assistant", "content": text}
    if tool:
        message["tool_calls"] = [{"id": "read-1", "type": "function",
            "function": {"name": tool, "arguments": "{}"}}]
        message["content"] = None
    result = {"choices": [{"index": 0, "message": message,
        "finish_reason": "tool_calls" if tool else "stop"}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7}}
    if model is not None:
        result["model"] = model
    return result


def one_text_call(provider):
    return auth.make_call([provider], lambda client, model: (
        (lambda r: (r.content[0].text, None, r))(client.messages.create(
            model=model, max_tokens=100, messages=[{"role": "user", "content": "Ping."}]))))


def scoped_rows(state, principal):
    turns = [row for row in state.native.rows("application_turns") if row["principal_id"] == principal]
    lease_ids = {row["lease_id"] for row in turns}
    return {"application_turns": turns,
            "application_requests": [row for row in state.native.rows("application_requests")
                                      if row["principal_id"] == principal],
            "leases": [row for row in state.native.rows("leases")
                       if row["id"] in lease_ids]}


def test_pins_current_application_owner_not_historical_8af():
    assert PINS_NATIVE["candidate/go_shim.py"] == "969ffaf84e23ef2d1c0398761943093c9b5c9456"
    assert PINS_NATIVE["candidate/go_shim.py"] != "2c7bb5a9719f4a94bd57a30b5c1bc90d171573df"


def test_five_distinct_bindings_share_real_b_a_and_physical_capacity(services):
    state = services
    native = state.native
    before = list(state.events)
    for record_id, *_ in SERVICES:
        assert "transport_identity" in state.factories[record_id]().inspect()
    assert state.events == before  # inspection opens no secret/client
    ops = []
    for record_id, _, lane, _, _ in SERVICES:
        op_id = f"{lane}:shared-{record_id}"
        factory, provider = state.bind(record_id, op_id)
        ops.append((record_id, op_id, factory, provider))
    # Retain real tool/history behavior on chat in addition to the other turns.
    native.response = packet(tool="read")
    chat_provider = next(p for r, _, _, p in ops if r == "mastermind_chat_fabric")

    def two_steps(client, model):
        first = client.messages.create(model=model, max_tokens=100,
            tools=[{"name": "read", "input_schema": {"type": "object"}}],
            messages=[{"role": "user", "content": "Use the tool."}])
        native.response = packet("Chat grounded.")
        history = [{"role": "user", "content": "Use the tool."},
                   {"role": "assistant", "content": first.content},
                   {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "read-1",
                                                "content": "Observed."}]}]
        final = client.messages.create(model=model, max_tokens=100,
            tools=[{"name": "read", "input_schema": {"type": "object"}}], messages=history)
        return final.content[0].text, None, final

    assert auth.make_call([chat_provider], two_steps, context="chat")[0] == "Chat grounded."
    for record_id, op_id, factory, provider in ops:
        if record_id != "mastermind_chat_fabric":
            native.response = packet(f"Answer {record_id}")
            text, reason, _ = one_text_call(provider)
            assert reason is None and text == f"Answer {record_id}"
        auth.close_fabric_provider(provider)
    assert len(native.posts) == 6
    assert len({p[2] for p in native.posts}) == 1  # shared physical upstream account
    assert len(native.posts) == len(native.rows("application_requests")) == 6
    turns = native.rows("application_turns")
    assert len(turns) == len({row["principal_id"] for row in turns}) == 5
    assert len(native.usage_rows()) == 6
    assert all(row["account"] == "account-a" for row in native.usage_rows())
    per_account = next(p for p in native.broker.load_accounts_doc()["providers"]["go"]["accounts"]
                       if p["name"] == "account-a")["per_account_cap"]
    assert per_account == 2 and len(turns) == 5  # independent services share, not clone, capacity
    assert len(state.closes) == 5
    assert all(row["state"] == "released" for row in native.rows("leases"))



def test_distinct_services_contend_for_the_same_two_native_slots(services):
    state, native = services, services.native
    db_identity = Path(native.broker.db_path).stat().st_ino
    _, admin = state.bind("shared_fabric", "capacity-admin")
    _, chat = state.bind("mastermind_chat_fabric", "capacity-chat")
    for provider in (admin, chat):
        native.response = packet("Original held turn.")
        assert one_text_call(provider)[0] == "Original held turn."
    lock_identity = Path(native.broker.lock_path).stat().st_ino
    assert len(native.rows("leases")) == 2
    assert all(row["state"] in {"held", "rented"} for row in native.rows("leases"))
    before = (list(native.rows("leases")), list(native.rows("application_turns")),
              list(native.rows("application_requests")), list(native.posts), list(native.usage_rows()))
    _, refused = state.bind("mastermind_text_fabric", "capacity-refused")
    with pytest.raises(auth.FabricProviderError) as caught:
        one_text_call(refused)
    assert caught.value.effect_unknown is False
    assert (list(native.rows("leases")), list(native.rows("application_turns")),
            list(native.rows("application_requests")), list(native.posts), list(native.usage_rows())) == before
    auth.close_fabric_provider(refused)
    auth.close_fabric_provider(admin)
    # A new deliberate operation can now use the one physically released slot.
    _, text = state.bind("mastermind_text_fabric", "capacity-after-release")
    native.response = packet("Shared slot reused.")
    assert one_text_call(text)[0] == "Shared slot reused."
    assert len(native.posts) == len(native.rows("application_requests")) == len(native.usage_rows()) == 3
    assert sum(row["state"] in {"held", "rented"} for row in native.rows("leases")) == 2
    assert Path(native.broker.db_path).stat().st_ino == db_identity
    assert Path(native.broker.lock_path).stat().st_ino == lock_identity
    auth.close_fabric_provider(chat)
    auth.close_fabric_provider(text)
    assert all(row["state"] == "released" for row in native.rows("leases"))


def test_equal_ids_cross_service_close_before_admission_is_inert(services):
    state, native = services, services.native
    shared = "shared-turn-id"
    native.response = packet("text-one")
    _, text = state.bind("mastermind_text_fabric", shared)
    _, chat = state.bind("mastermind_chat_fabric", shared)
    assert one_text_call(text)[0] == "text-one"
    text_before = scoped_rows(state, "mastermind_text_fabric")
    chat_before = scoped_rows(state, "mastermind_chat_fabric")
    posts, usages = list(native.posts), list(native.usage_rows())
    assert chat_before == {"application_turns": [], "application_requests": [], "leases": []}
    status, body, _ = native.request(path="/application-turns/close",
        payload={"turn_id": shared}, token=state.credentials["mastermind_chat_fabric"])
    assert status == 503 and body["application"]["disposition"] == "effect_unknown"
    assert scoped_rows(state, "mastermind_chat_fabric") == chat_before
    auth.close_fabric_provider(chat)  # local cleanup follows the real native close probe
    assert scoped_rows(state, "mastermind_text_fabric") == text_before
    assert (list(native.posts), list(native.usage_rows())) == (posts, usages)

    # Once both exist, equal string turn IDs identify separate native rows.
    native.response = packet("chat-one")
    _, chat = state.bind("mastermind_chat_fabric", shared)
    assert one_text_call(chat)[0] == "chat-one"
    assert len(native.rows("application_turns")) == 2
    assert {(r["principal_id"], r["turn_id"]) for r in native.rows("application_turns")} == {
        ("mastermind_text_fabric", shared), ("mastermind_chat_fabric", shared)}
    chat_before = scoped_rows(state, "mastermind_chat_fabric")
    chat_before["application_requests"][0]["request_id"] = "tampered-must-not-match"
    native_request_id = shared + ":brain:0"
    # Recovery matches the original body and authenticates only chat's scope.
    _, restored_chat = state.bind("mastermind_chat_fabric", shared, prior_admission_possible=True)
    original_wire = json.loads(native.posts[-1][1])
    original_payload = {k: v for k, v in original_wire.items() if k != "request_id"}
    status, envelope, _ = native.request(turn=shared, step=native_request_id, payload=original_payload,
        token=state.credentials["mastermind_chat_fabric"])
    assert status == 409 and envelope["application"]["disposition"] == "terminal_receipt_only"
    assert scoped_rows(state, "mastermind_text_fabric") == text_before
    auth.close_fabric_provider(restored_chat)
    auth.close_fabric_provider(chat)
    assert scoped_rows(state, "mastermind_text_fabric") == text_before
    assert scoped_rows(state, "mastermind_chat_fabric")["leases"][0]["state"] == "released"
    auth.close_fabric_provider(text)
    assert scoped_rows(state, "mastermind_text_fabric")["leases"][0]["state"] == "released"


def test_original_replay_unknown_disposition_and_known_503_are_exact(services):
    state, native = services, services.native
    # Reconstruct the *same* wrapper request with the exact original body.
    _, provider = state.bind("mastermind_text_fabric", "text-replay")
    native.response = packet("once")
    assert one_text_call(provider)[0] == "once"
    original_wire = json.loads(native.posts[0][1])
    original_body = {k: v for k, v in original_wire.items() if k != "request_id"}
    original_rows = native.rows("application_requests")
    snapshot = (list(native.posts), list(native.usage_rows()), original_rows, list(state.costs))
    assert len(snapshot[0]) == len(snapshot[1]) == len(snapshot[2]) == len(snapshot[3]) == 1

    # Inspect the real B receipt using those exact same IDs and body.
    status, envelope, headers = native.request(turn="text-replay",
        step="text-replay:brain:0", payload=original_body,
        token=state.credentials["mastermind_text_fabric"])
    assert status == 409 and envelope["application"]["disposition"] == "terminal_receipt_only"
    assert headers["X-MM-Application-Disposition"] == "terminal_receipt_only"
    assert "usage" not in envelope["application"]
    assert (list(native.posts), list(native.usage_rows()), native.rows("application_requests"), list(state.costs)) == snapshot

    # Original wrapper, IDs and body produce native receipt-only. Observe at
    # real _open while checking exact bytes inside existing _exchange, with no
    # substituted request/response/factory/client implementation.
    auth.close_fabric_provider(provider)
    _, restored = state.bind("mastermind_text_fabric", "text-replay", prior_admission_possible=True)
    native_responses = []
    original_exchange = restored["client"]._client._exchange
    assert restored["client"]._client._native is True
    assert restored["client"]._client._prior_admission_possible is True
    def observe_exchange(path, body, headers, **kwargs):
        assert path == "/v1/chat/completions"
        assert headers["X-MM-Application-Turn-ID"] == "text-replay"
        assert headers["Idempotency-Key"] == "text-replay:brain:0"
        assert json.loads(body) == json.loads(native.posts[0][1])
        return original_exchange(path, body, headers, **kwargs)
    original_open = restored["client"]._client._open
    def observe_open(kwargs, *, streaming):
        try:
            return original_open(kwargs, streaming=streaming)
        except Exception as exc:
            native_responses.append(exc)
            raise
    restored["client"]._client._exchange = observe_exchange
    restored["client"]._client._open = observe_open
    with pytest.raises(auth.FabricProviderError) as receipt_only:
        one_text_call(restored)
    assert receipt_only.value.code == "fabric_unavailable"
    assert receipt_only.value.effect_unknown is False
    assert restored.get("_fabric_native_disposition") == "terminal_receipt_only"
    assert len(native_responses) == 1
    assert native_responses[0].disposition == "terminal_receipt_only"
    assert native_responses[0].observed_usage is None
    assert restored["_fabric_pending"] is False
    assert auth.fabric_usage(restored)["usage_state"] == "unknown"
    assert restored["_fabric_known_responses"] == 0
    assert len(restored["_fabric_observed_ids"]) == 0
    assert (list(native.posts), list(native.usage_rows()), native.rows("application_requests"), list(state.costs)) == snapshot
    restored["client"]._client._exchange = original_exchange
    auth.close_fabric_provider(restored)
    assert restored["_fabric_close"]["disposition"] == "closed"
    assert scoped_rows(state, "mastermind_text_fabric")["leases"][0]["state"] == "released"

    # Genuine upstream truncation after dispatch: pending/effect unknown, no resend.
    _, pending = state.bind("macro_ask_fabric", "ask-unknown")
    native.partial = True
    native.response = packet("lost-ack")
    with pytest.raises(auth.FabricProviderError) as caught:
        one_text_call(pending)
    assert caught.value.effect_unknown is True
    assert len(native.posts) == 2
    with pytest.raises(auth.FabricProviderError):
        one_text_call(pending)
    assert len(native.posts) == 2
    auth.close_fabric_provider(pending)
    rows = scoped_rows(state, "macro_ask_fabric")
    assert rows["application_requests"][0]["state"] == "unknown"
    assert pending["_fabric_close"] == {"disposition": "effect_unknown", "closed": False,
                                          "effect_unknown": True, "attempted": True}
    assert rows["leases"][0]["state"] == "held"
    assert len(state.costs) == 1  # no fabricated unknown spend

    # A fully framed 503 is a known terminal error, with actual usage exactly once.
    native.partial = False
    native.response_status = 503
    native.response = packet("known-error")
    _, known = state.bind("macro_brain_fabric", "brain-known-503")
    with pytest.raises(auth.FabricProviderError) as caught:
        one_text_call(known)
    assert caught.value.effect_unknown is False
    usage = auth.fabric_usage(known)
    assert (usage["input_tokens"], usage["output_tokens"], usage["usage_state"]) == (11, 7, "known")
    observed = known["_fabric_usage_observations"]
    assert observed == [(MODEL, 11, 7)]
    auth.close_fabric_provider(known)
    assert len(native.posts) == len(native.rows("application_requests")) == 3
    assert len(native.usage_rows()) == len(state.costs) == 2
    rows = native.rows("application_requests")
    assert [r["state"] for r in rows] == ["terminal", "unknown", "terminal"]
    assert json.loads(rows[2]["terminal_receipt"])["usage"] == {"input_tokens": 11, "output_tokens": 7}
    assert scoped_rows(state, "macro_brain_fabric")["leases"][0]["state"] == "released"


def test_named_startup_macro_brain_ask_and_actual_mm_public_paths(services):
    state = services
    state.monkeypatch.setenv("MACRO_REPO", str(state.root))
    state.monkeypatch.setenv("MACRO_API_STATE_DIR", str(state.root / "macro-api-state"))
    from app import main as api
    state.monkeypatch.setattr(api, "REPO", state.root)
    for name in ("fabric_selected", "fabric_provider_factory", "ask_fabric_selected", "ask_fabric_provider_factory"):
        state.monkeypatch.setattr(api.app.state, name, getattr(api.app.state, name, None), raising=False)
    from engine.neuralweb import ask_brain, brain_gateway
    from fastapi import BackgroundTasks
    from starlette.requests import Request
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
    native = state.native
    native.response = packet("Ask public path complete.")
    asked = api.ask_brain(api.AskRequest(question="Explain a synthetic observation."), request,
        user={"id": "synthetic-user"})
    assert asked["answer"] == "Ask public path complete." and asked["mode"] == "live"
    native.response = packet("Brain public path with retained history complete.")
    brain = api.brain_chat(api.BrainChatRequest(message="Explain a synthetic observation.",
        history=[{"role": "user", "content": "Earlier synthetic context."},
                 {"role": "assistant", "content": "Earlier synthetic answer."}]),
        request, BackgroundTasks(), user={"_is_guest": True, "_guest_aid": "synthetic-aid",
            "_guest_ip": "127.0.0.1"})
    assert brain["reply"] == "Brain public path with retained history complete."
    assert not brain["degraded"]
    assert len(native.posts) == 2

    with real_mastermind(state) as (fabric_inference, fabric_chat, advisor, bot_mcp, macro_root):
        assert Path(fabric_inference.__file__).resolve().parent.parent == Path(SOURCE_ROOT).resolve()
        native.response = packet("Actual Mastermind text complete.")
        assert fabric_inference.call_model("Synthetic system", "Synthetic user") == (
            "Actual Mastermind text complete.", None)
        calls = [packet(None, tool="mcp__bot__get_portfolio"), packet("Actual Mastermind chat complete.")]
        native.on_upstream = lambda: setattr(native, "response", calls.pop(0))

        async def collect():
            return [event async for event in fabric_chat.chat_stream(
                "Read the synthetic book and explain it.", conversation_id="public-chat", turn_id="turn-public")]

        events = asyncio.run(collect())
        assert events[-1]["type"] == "done" and events[-1]["text"] == "Actual Mastermind chat complete."
        with advisor.fabric_conversation("public-chat", scope="portfolio_advisor") as doc:
            assert len(doc["turns"][0]["steps"]) == 2
            assert doc["turns"][0]["tool_effects"][0]["state"] == "complete"
            assert doc["messages"][1]["role"] == "assistant"
            assert doc["messages"][2]["content"][0]["type"] == "tool_result"
    assert len(native.posts) == 5
    turns = {row["principal_id"]: row for row in native.rows("application_turns")}
    assert set(turns) == {"macro_ask_fabric", "macro_brain_fabric", "mastermind_text_fabric",
                          "mastermind_chat_fabric"}
    assert all(row["state"] == "released" for row in native.rows("leases"))
    assert len(native.usage_rows()) == 5
