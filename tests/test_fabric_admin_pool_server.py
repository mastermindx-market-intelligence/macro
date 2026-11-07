"""Real authenticated Admin route and original cache; metadata remains read-only."""
import copy
import http.client
import json
import threading
from unittest.mock import Mock

import pytest

from admin import server
from engine import provider_production_modes as owner
from engine.neuralweb import key_pool
from tests.test_fabric_admin_pool_view import observation, metadata_binding  # noqa: F401
from tests.test_fabric_application_binding import binding  # noqa: F401


@pytest.fixture
def admin(tmp_path, monkeypatch, observation):
    monkeypatch.delenv("ADMIN_DEPLOYED", raising=False)
    monkeypatch.setenv("ADMIN_PASSWORD", "fixture-admin-password")
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "fixture-admin-session-secret")
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE", raising=False)
    monkeypatch.setattr(server.marketing_floor, "_default_root", lambda: tmp_path)
    monkeypatch.setattr(key_pool, "discover_present_keys", Mock(side_effect=AssertionError("GET discovered keys")))
    server._clear_response_cache()
    httpd = server._build_server("127.0.0.1", 0)
    reader = Mock()
    reader.read.return_value = observation
    httpd.fabric_pool_reader = reader
    thread = threading.Thread(target=lambda: httpd.serve_forever(poll_interval=.01), daemon=True)
    thread.start()
    session = server.auth.mint_session()
    def get(*, authenticated=True, force=False):
        connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=3)
        try:
            headers = {"Cookie": server.auth.SESSION_COOKIE + "=" + session} if authenticated else {}
            connection.request("GET", "/api/marketing/models" + ("?force=1" if force else ""), headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read()), dict(response.getheaders())
        finally:
            connection.close()
    yield httpd, reader, get
    httpd.shutdown(); httpd.server_close(); thread.join(2)
    server._clear_response_cache()


def test_authentication_precedes_cached_model_desk_and_forced_read(admin):
    _, reader, get = admin
    first = get()
    assert first[0] == 200 and first[1]["ok"] and len(first[1]["fabric"]["pools"]) == 9
    assert get()[2]["X-Admin-Cache"] == "HIT" and reader.read.call_count == 1
    assert get(authenticated=False)[0] == 401
    assert get(authenticated=False, force=True)[0] == 401
    assert reader.read.call_count == 1
    assert get()[2]["X-Admin-Cache"] == "HIT"  # rejected refresh did not invalidate
    assert first[1]["fabric"]["observed_at"] == 1000


def test_force_invalidates_old_cache_and_never_retimestamps_native_observation(admin):
    _, reader, get = admin
    assert get()[1]["fabric"]["observed_at"] == 1000
    second = copy.deepcopy(reader.read.return_value)
    second.update(observed_at=1001, stale_after=1006)
    reader.read.return_value = second
    force = get(force=True)
    assert force[0] == 200 and force[1]["fabric"]["observed_at"] == 1001
    assert force[1]["fabric"]["stale_after"] == 1006 and force[1]["fabric"]["freshness"] == "stale"
    assert "X-Admin-Cache" not in force[2]
    assert get()[1]["fabric"]["observed_at"] == 1001
    assert reader.read.call_count == 3


def test_pending_preforce_response_cannot_refill_cleared_generation(admin):
    _, reader, get = admin
    arrived, release = threading.Event(), threading.Event()
    original = copy.deepcopy(reader.read.return_value)
    replacement = copy.deepcopy(original);replacement.update(observed_at=1002, stale_after=1007)
    calls = []
    def read():
        calls.append(1)
        if len(calls) == 1:
            arrived.set(); assert release.wait(2); return original
        return replacement
    reader.read.side_effect = read
    results = []
    pending = threading.Thread(target=lambda: results.append(get()), daemon=True);pending.start()
    assert arrived.wait(2)
    try:
        assert get(force=True)[1]["fabric"]["observed_at"] == 1002
    finally:
        release.set();pending.join(2)
    assert results[0][1]["fabric"]["observed_at"] == 1000
    assert get()[1]["fabric"]["observed_at"] == 1002
    assert len(calls) == 3


def test_unavailable_metadata_does_not_hide_other_model_desk_evidence(admin):
    _, reader, get = admin
    reader.read.side_effect = RuntimeError("secret transport detail must not escape")
    code, body, _ = get()
    assert code == 200 and body["ok"] and not body["fabric"]["available"]
    assert body["lanes"] and len(body["fabric"]["pools"]) == 9
    assert "secret transport detail" not in json.dumps(body)


def test_real_startup_prepares_reader_only_once_and_inference_stays_held(metadata_binding, monkeypatch, observation):
    root, _, _, _, events, _, make, _ = metadata_binding
    from admin import paths
    from engine.fabric_inference_client import FabricPoolViewReader
    monkeypatch.setattr(paths, "ROOT", root)
    monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", "shared_fabric")
    monkeypatch.setattr(FabricPoolViewReader, "read", lambda self: copy.deepcopy(observation))
    httpd = server._build_server("127.0.0.1", 0)
    try:
        assert httpd.fabric_selected and httpd.fabric_pool_reader is not None
        assert events == ["credential"]
        monkeypatch.setattr(owner, "_resolve_credential", Mock(side_effect=AssertionError("request read a credential")))
        assert httpd.fabric_pool_reader.read() == observation
        with pytest.raises(owner.ApplicationFabricBindingError, match="unqualified"):
            httpd.fabric_provider_factory.inspect()
    finally:
        httpd.server_close()
