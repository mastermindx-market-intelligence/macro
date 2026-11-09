"""Recorded Model Desk evidence, strict metadata transport and owner permissions."""
import copy
from dataclasses import replace
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import threading
import time
from unittest.mock import Mock

import pytest

from admin import marketing_floor as floor
from engine import fabric_inference_client as client
from engine import provider_capacity as capacity
from engine import provider_production_modes as owner
from engine.neuralweb import key_pool
from tests.test_fabric_application_binding import binding  # noqa: F401


@pytest.fixture
def observation():
    pools = capacity.fabric_admin_pool_projection()["pools"]
    for p in pools:
        p.update(configured=True, enabled=True, configured_accounts=2, enabled_accounts=1,
                 held_leases=1, capacity_basis="account_concurrency", application_state="unqualified",
                 blockers=["application_transport_unqualified"])
    pools[0].update(application_state="configured", model_coverage="bound_transport", blockers=[], models=[{
        "model": "fixture-model", "protocol": "chat", "transport_state": "qualified",
        "capabilities": {"text": True, "tools": True, "vision": False, "upstream_streaming": False},
        "application_state": "configured", "ledger_room": 1, "capacity_state": "broker_ledger_only", "blockers": []}])
    return {"schema": capacity.FABRIC_ADMIN_SCHEMA, "observed_at": 1000.0, "stale_after": 1005.0,
        "execution_authorized": False, "requires_fresh_admission": True,
        "scope": {"workload": "site_interactive", "bound_pool": "go"},
        "coverage": {"inventory": "canonical_accounts", "ledger": "held_rows",
                     "transports": "application_gateway", "provider_quota": "unobserved"},
        "source": {k: "a" * 64 for k in ("source_generation", "ingress_sha256", "gateway_sha256", "accounts_sha256")},
        "pools": pools}


def test_projection_preserves_native_clock_and_owns_copied_fields(observation):
    fresh = capacity.fabric_admin_pool_projection(observation, now=1001)
    stale = capacity.fabric_admin_pool_projection(observation, now=1006)
    assert fresh["freshness"] == "fresh" and stale["freshness"] == "stale"
    assert stale["observed_at"] == 1000 and stale["stale_after"] == 1005
    fresh["pools"][0]["models"][0]["ledger_room"] = 99
    assert observation["pools"][0]["models"][0]["ledger_room"] == 1
    unknown = capacity.fabric_admin_pool_projection()
    assert len(unknown["pools"]) == 10 and not unknown["available"]
    assert all(p["configured_accounts"] is None for p in unknown["pools"])


@pytest.mark.parametrize("fault", ["schema", "authority", "extra", "path", "duplicate", "boolean-count",
    "unknown-pool", "unknown-blocker", "non-go-room", "capability", "state-type", "future", "nan", "count"])
def test_closed_projection_rejects_hostile_and_unsupported_facts(observation, fault):
    d = copy.deepcopy(observation)
    if fault == "schema": d["schema"] = capacity.SCHEMA
    elif fault == "authority": d["execution_authorized"] = True
    elif fault == "extra": d["credential"] = "secret"
    elif fault == "path": d["source"]["accounts_path"] = "/private/secret"
    elif fault == "duplicate": d["pools"][1] = d["pools"][0]
    elif fault == "boolean-count": d["pools"][0]["held_leases"] = True
    elif fault == "unknown-pool": d["pools"][0]["pool"] = "unregistered"
    elif fault == "unknown-blocker": d["pools"][0]["blockers"] = ["secret error text"]
    elif fault == "non-go-room":
        d["pools"][1]["models"] = d["pools"][0]["models"]
        d["pools"][1]["model_coverage"] = "bound_transport"
    elif fault == "capability": d["pools"][0]["models"][0]["capabilities"]["tools"] = 1
    elif fault == "state-type": d["pools"][0]["models"][0]["application_state"] = []
    elif fault == "future": d.update(observed_at=2000, stale_after=2005)
    elif fault == "nan": d["observed_at"] = float("nan")
    else: d["pools"][0]["configured_accounts"] = 2**1000
    with pytest.raises(ValueError):
        capacity.fabric_admin_pool_projection(d, now=1001)


@pytest.fixture
def metadata_binding(binding, monkeypatch):
    root, row, document, manifest, events, save, make, transport = binding
    transport = replace(transport, protocol="native_application_v1", metadata_read=True,
                        qualified=False, application_allowed=False)
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", transport)
    row["admin_pool_view"] = True
    save()
    return root, row, document, manifest, events, save, make, transport


def test_metadata_permission_never_qualifies_inference_and_secret_is_startup_only(metadata_binding, monkeypatch, observation):
    _, _, _, _, events, _, make, _ = metadata_binding
    factory = make()
    for invoke in (factory.inspect, lambda: factory._bind_with_workload(operation_id="fixture-turn")):
        with pytest.raises(owner.ApplicationFabricBindingError, match="unqualified"):
            invoke()
    assert events == []
    reader = factory.prepare_admin_pool_reader()
    assert events == ["credential"]
    monkeypatch.setattr(client.FabricPoolViewReader, "read", lambda self: copy.deepcopy(observation))
    monkeypatch.setattr(owner, "_resolve_credential", Mock(side_effect=AssertionError("GET resolved a secret")))
    monkeypatch.setattr(factory.__class__, "_bind_with_workload", Mock(side_effect=AssertionError("GET bound a turn")))
    assert reader.read() == observation and reader.read() == observation
    assert "synthetic-proxy-token" not in repr(reader) + repr(reader.reader)


@pytest.mark.parametrize("fault", ["absent", "false", "truthy", "disabled", "source-held", "capability", "reference", "identity"])
def test_metadata_startup_refuses_before_secret(metadata_binding, monkeypatch, fault):
    _, row, _, manifest, events, save, make, transport = metadata_binding
    if fault == "absent": del row["admin_pool_view"]
    elif fault == "false": row["admin_pool_view"] = False
    elif fault == "truthy": row["admin_pool_view"] = 1
    elif fault == "disabled": row["enabled"] = False
    elif fault == "source-held": monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", replace(transport, metadata_read=False))
    elif fault == "capability": manifest["capabilities"][0]["kill_state"] = "blocked"
    elif fault == "reference": manifest["capabilities"][0]["secret_ref"] = "DIFFERENT_TEST_REFERENCE"
    else: row["base_url"] = "http://127.0.0.1:9999/v1"
    save()
    with pytest.raises(ValueError): make().prepare_admin_pool_reader()
    assert events == []


def test_prepared_reader_checks_revocation_without_secret_or_request(metadata_binding, monkeypatch):
    _, row, _, _, events, save, make, _ = metadata_binding
    reader = make().prepare_admin_pool_reader()
    row["admin_pool_view"] = False
    save()
    transport = Mock(side_effect=AssertionError("revoked GET sent"))
    monkeypatch.setattr(client.FabricPoolViewReader, "read", transport)
    with pytest.raises(owner.ApplicationFabricBindingError): reader.read()
    assert events == ["credential"] and not transport.called


def test_recorded_key_snapshot_never_discovers_credentials(tmp_path, monkeypatch):
    from lib import config
    from engine import codex_provider
    calls = Mock(side_effect=AssertionError("credential discovery"))
    monkeypatch.setattr(key_pool, "discover_present_keys", calls)
    monkeypatch.setattr(config, "secret", calls)
    monkeypatch.setattr(codex_provider, "available_accounts", calls)
    rows = key_pool.usage_snapshot(tmp_path, recorded_only=True)
    assert rows and all(row["present"] is None for row in rows)
    panel = floor.models(tmp_path)
    assert panel["ok"] and len(panel["fabric"]["pools"]) == 10
    assert not calls.called


def test_recorded_cooling_is_independent_of_unknown_presence(tmp_path, monkeypatch):
    monkeypatch.setattr(key_pool, "usage_snapshot", lambda root, recorded_only: [{
        "key_id": key_pool.POOL_CAPABILITY_IDS[0], "present": None, "enabled": True,
        "cooling": True, "reset_hint": "2099-01-01T00:00:00Z", "last_ts": "2026-11-05T00:00:00Z",
        "window_5h_est_tokens": 10, "weekly_est_tokens": 20}])
    pool = floor._pool_health(tmp_path)
    assert pool["cooling"] == 1 and pool["unobserved"] == 1 and pool["ready"] == 0
    assert pool["keys"][0]["state"] == "unobserved" and pool["keys"][0]["present"] is None


@pytest.mark.parametrize("selection", ["shared_fabric", "", "invalid"])
def test_selected_or_invalid_host_remains_exclusive_and_desk_renderable(tmp_path, monkeypatch, selection):
    monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", selection)
    panel = floor.models(tmp_path)
    assert panel["ok"] and len(panel["fabric"]["pools"]) == 10
    assert all(row["first_choice"] == "fabric" and row["provider_order"] == ["fabric"]
               and row["fabric_route"]["state"] == "held" for row in panel["lanes"])


@pytest.fixture
def endpoint(observation):
    state = {"body": observation, "status": 200, "calls": [], "headers": {}, "slow": False}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            state["calls"].append((self.command, self.path, dict(self.headers)))
            raw = state["body"] if type(state["body"]) is bytes else json.dumps(state["body"]).encode()
            self.send_response(state["status"])
            for k, v in {"Content-Type": "application/json", "Content-Length": str(len(raw)), "Cache-Control": "no-store", **state["headers"]}.items():
                self.send_header(k, v)
            self.end_headers()
            try:
                if state["slow"]:
                    for b in raw:
                        self.wfile.write(bytes([b])); self.wfile.flush(); time.sleep(0.01)
                else: self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError): pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    state["reader"] = lambda timeout=2: client.FabricPoolViewReader(
        base_url=f"http://127.0.0.1:{server.server_port}/v1", proxy_token="fixture-read-only-service-token-0123456789", timeout_s=timeout)
    yield state
    server.shutdown(); server.server_close(); thread.join(2)


def test_transport_sends_one_fixed_get_without_turn_or_inference_headers(endpoint, observation):
    assert endpoint["reader"]().read() == observation
    assert len(endpoint["calls"]) == 1
    method, path, headers = endpoint["calls"][0]
    assert (method, path) == ("GET", "/application-pools/view")
    assert not any(name.lower().startswith("x-mm-") for name in headers)
    assert "Idempotency-Key" not in headers


@pytest.mark.parametrize("fault", ["denied", "redirect", "schema", "duplicate", "oversize", "framing", "slow"])
def test_metadata_failure_is_bounded_never_unknown_and_never_retried(endpoint, fault):
    if fault == "denied": endpoint["status"] = 403
    elif fault == "redirect": endpoint.update(status=302, headers={"Location": "http://127.0.0.1:1/never"})
    elif fault == "schema": endpoint["body"]["schema"] = capacity.SCHEMA
    elif fault == "duplicate": endpoint["body"] = b'{"schema":1,"schema":2}'
    elif fault == "oversize": endpoint["headers"] = {"Content-Length": str(256*1024+1)}
    elif fault == "framing": endpoint["headers"] = {"Transfer-Encoding": "chunked"}
    else: endpoint["slow"] = True
    start = time.monotonic()
    with pytest.raises(client.FabricInferenceError) as error:
        endpoint["reader"](.1 if fault == "slow" else 2).read()
    assert not error.value.effect_unknown and len(endpoint["calls"]) == 1
    assert time.monotonic() - start < 2.5


@pytest.mark.parametrize("pool_count", [9, 10])
def test_real_renderer_handles_versioned_groups_and_never_upgrades_stale(observation, legacy_observation, pool_count):
    if pool_count == 9:
        observation = legacy_observation
    source = (Path(__file__).resolve().parents[1] / "admin/static/app.js").read_text()
    block = source[source.index("function fabricPoolViewHtml("):source.index("/* ---- X LANES", source.index("function fabricPoolViewHtml("))]
    data = {"ok": True, "lanes": [{"name": "<unsafe>", "first_choice": "fabric",
            "fabric_route": {"selected": True, "state": "held", "model": "fixture-model", "blocker": "unqualified"}}],
            "waterfall": [], "pool": {"available": False}, "ledger": {},
            "fabric": capacity.fabric_admin_pool_projection(observation, now=1010)}
    script = '''const fs=require('fs');const input=JSON.parse(fs.readFileSync(0,'utf8'));
const RENDER={},view={innerHTML:''},button={};let calls=[],clears=0;
const $=s=>s==='#view'?view:button;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const flrN=v=>String(v??'—'),nwEmpty=()=>'';const clearApiCache=()=>{clears++};
const api=async path=>{calls.push(path);return input};Date.now=()=>1001000;
''' + block + '''
(async()=>{await RENDER.marketing_models();let initial=view.innerHTML;await button.onclick();
process.stdout.write(JSON.stringify({initial,calls,clears}));})();'''
    result = subprocess.run(["node", "-e", script], input=json.dumps(data), text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    rendered = json.loads(result.stdout)
    for row in observation["pools"]: assert f'<h3>{row["pool"]} ' in rendered["initial"]
    assert ("<h3>deepseek " in rendered["initial"]) is (pool_count == 10)
    assert f"stale · {pool_count} pools" in rendered["initial"] and "fresh at last read" not in rendered["initial"]
    assert "&lt;unsafe&gt;" in rendered["initial"] and "<unsafe>" not in rendered["initial"]
    assert "1970-01-01T00:16:40.000Z" in rendered["initial"]
    assert rendered["calls"] == ["/api/marketing/models", "/api/marketing/models?force=1"] and rendered["clears"] == 1


def test_legacy_metadata_retains_nine_pools_without_synthesizing_deepseek(legacy_observation):
    observation = legacy_observation
    projected = capacity.fabric_admin_pool_projection(observation, now=1001)
    assert projected["schema"] == "mastermind.fabric_admin_pool_view.v1"
    assert tuple(row["pool"] for row in projected["pools"]) == LEGACY_POOL_NAMES
    assert projected["observed_at"] == observation["observed_at"]
    projected["pools"][0]["configured_accounts"] = 50
    assert observation["pools"][0]["configured_accounts"] == 2


def test_deepseek_metadata_does_not_promote_unqualified_accounts_or_invent_quota(observation):
    observation["scope"]["bound_pool"] = "deepseek"
    projected = capacity.fabric_admin_pool_projection(observation, now=1001)
    row = projected["pools"][-1]
    assert projected["schema"] == "mastermind.fabric_admin_pool_view.v2"
    assert row["pool"] == "deepseek" and row["application_state"] == "unqualified"
    assert row["models"] == [] and row["model_coverage"] == "unobserved"
    assert row["blockers"] == ["application_transport_unqualified"]
    assert projected["execution_authorized"] is False
    assert projected["requires_fresh_admission"] is True
    unknown = capacity.fabric_admin_pool_projection()["pools"][-1]
    assert unknown["pool"] == "deepseek" and unknown["configured"] is None
    assert unknown["configured_accounts"] is None and unknown["held_leases"] is None


@pytest.mark.parametrize("fault", [
    "v1-ten", "v2-nine", "v1-deepseek-scope", "missing-middle", "duplicate",
    "reordered", "eleventh", "unknown-successor", "schema-type", "deepseek-ledger",
])
def test_versioned_pool_vocabulary_is_closed(observation, fault):
    if fault == "v1-ten":
        observation["schema"] = capacity.FABRIC_ADMIN_LEGACY_SCHEMA
    elif fault == "v2-nine":
        observation["pools"].pop()
    elif fault == "v1-deepseek-scope":
        observation["schema"] = capacity.FABRIC_ADMIN_LEGACY_SCHEMA
        observation["pools"].pop()
        observation["scope"]["bound_pool"] = "deepseek"
    elif fault == "missing-middle":
        observation["pools"].pop(3)
    elif fault == "duplicate":
        observation["pools"][-1] = copy.deepcopy(observation["pools"][0])
    elif fault == "reordered":
        observation["pools"][-1], observation["pools"][-2] = observation["pools"][-2:]
    elif fault == "eleventh":
        row = copy.deepcopy(observation["pools"][-1])
        row["pool"] = "future-provider"
        observation["pools"].append(row)
    elif fault == "unknown-successor":
        observation["schema"] = "mastermind.fabric_admin_pool_view.v3"
    elif fault == "schema-type":
        observation["schema"] = []
    else:
        row = observation["pools"][-1]
        row["models"] = copy.deepcopy(observation["pools"][0]["models"])
        row["model_coverage"] = "bound_transport"
        row["models"][0].update(model="deepseek-flash", protocol="responses")
    with pytest.raises(ValueError, match="fabric_admin_view_invalid"):
        capacity.validate_fabric_admin_pool_view(observation)

# Frozen v1 peer document. Do not derive its schema or vocabulary from the
# current projection: this fixture must continue to represent an older service.
LEGACY_POOL_NAMES = ("go", "glm", "minimax", "bailian", "grok", "cursor",
                     "codex-native", "claude-native", "ocfree")


@pytest.fixture
def legacy_observation():
    pools = [{
        "pool": pool, "configured": True, "enabled": True,
        "configured_accounts": 2, "enabled_accounts": 1, "held_leases": 1,
        "capacity_basis": "account_concurrency", "application_state": "unqualified",
        "models": [], "model_coverage": "unobserved",
        "blockers": ["application_transport_unqualified"],
    } for pool in LEGACY_POOL_NAMES]
    pools[0].update(application_state="configured", model_coverage="bound_transport",
        blockers=[], models=[{
            "model": "fixture-model", "protocol": "chat", "transport_state": "qualified",
            "capabilities": {"text": True, "tools": True, "vision": False,
                             "upstream_streaming": False},
            "application_state": "configured", "ledger_room": 1,
            "capacity_state": "broker_ledger_only", "blockers": [],
        }])
    return {
        "schema": "mastermind.fabric_admin_pool_view.v1",
        "observed_at": 1000.0, "stale_after": 1005.0,
        "execution_authorized": False, "requires_fresh_admission": True,
        "scope": {"workload": "site_interactive", "bound_pool": "go"},
        "coverage": {"inventory": "canonical_accounts", "ledger": "held_rows",
                     "transports": "application_gateway", "provider_quota": "unobserved"},
        "source": {key: "a" * 64 for key in
                   ("source_generation", "ingress_sha256", "gateway_sha256", "accounts_sha256")},
        "pools": pools,
    }
