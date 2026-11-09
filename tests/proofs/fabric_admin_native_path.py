"""Finite paired proof: real Admin -> prepared reader -> native B/A read-only view.

Run with --native-source pointing to the explicit matching Mastermind candidate.
All accounts, service grants, credentials and upstream are isolated test fixtures.
This does not install/enroll any production service or claim browser acceptance.
"""
import argparse
from contextlib import ExitStack
import hashlib
import http.client
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from unittest.mock import patch

PINS = {
    "candidate/go_lease_gateway.py": "7eb74e2a9a18d3c6a1ad1f51ed198bd0e32bcdeb",
    "candidate/go_shim.py": "97deba9fc1f68458670b16a21cb410575a7466f8",
    "candidate/lease_broker.py": "ba24989ca437617b69330c0560f6e8adc24c271d",
    "candidate/pick.py": "d17447c3c9f472b061733e36fa49a7f8d7e34ee5",
    "candidate/pool_ledger.py": "61dc4d5e83172e6c647d058ec844f00a0b3955a6",
    "tests/test_application_admin_pool_view.py": "31a2cf0cca4697537e2d59763d44328a73f26a5a",
    "tests/test_application_turn_admission.py": "efe876eec40dc8885dbc0059915f2401146be969",
    "tests/test_application_turn_selection_admission.py": "2e5443a0b55ef76e3c84c26708621143138af420",
    "tests/test_go_application_handler_composition.py": "13ebd6bcee5167926807d7ccdc63bcabed0cf1b1",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-source", type=Path, required=True)
    args = parser.parse_args()
    native = args.native_source.resolve() / "ops/native_fabric/quota_continuity"
    for relative, expected in PINS.items():
        raw = (native / relative).read_bytes()
        assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == expected, relative
    macro = Path(__file__).resolve().parents[2]
    sys.path[:0] = [str(macro), *(str(native / p) for p in ("candidate", "source", "tests"))]
    import yaml
    from admin import server, paths
    from engine import provider_production_modes as owner
    from test_application_admin_pool_view import AdminPoolViewFixture
    from test_go_application_handler_composition import SERVICE_TOKEN

    case = AdminPoolViewFixture("runTest")
    case.setUp()
    try:
        case.clock[0] = time.time()
        case.grant["expires_at"] = case.clock[0] + 300
        case.save()
        before = {table: case.rows(table) for table in ("leases", "application_turns", "application_requests", "waiters")}
        with tempfile.TemporaryDirectory(prefix="fabric-admin-owner-") as temporary, ExitStack() as stack:
            root = Path(temporary);(root / "config").mkdir()
            (root / "config/provider_workloads.v1.json").write_bytes((macro / "config/provider_workloads.v1.json").read_bytes())
            document = json.loads((macro / "config/provider_production_modes.v1.json").read_bytes())
            transport = owner._ApplicationFabricTransport(
                f"http://127.0.0.1:{case.server.server_port}/v1", "TEST_ADMIN_FABRIC_TOKEN", "go", "fixture-model",
                "unknown", "fabric:admin-fixture", "admin_fixture", protocol="native_application_v1", metadata_read=True)
            row = {key: getattr(transport, key) for key in owner._APPLICATION_IDENTITY_FIELDS}
            row.update(transport_id="admin_fixture", enabled=True, application_allowed=False,
                qualification=owner.PROFILE_QUALIFIED_CANARY, qualification_ref="fixture:metadata-only",
                qualified_until=time.time()+300, admin_pool_view=True)
            document["application_fabric_modes"] = {"shared_fabric": row}
            (root / "config/provider_production_modes.v1.json").write_text(json.dumps(document))
            (root / "config/capability_manifest.yml").write_text(yaml.safe_dump({"capabilities": [{
                "capability_id": "admin_fixture", "secret_ref": "TEST_ADMIN_FABRIC_TOKEN",
                "kill_state": "active", "allowed_lanes": ["admin-orchestrator"]}]}))
            stack.enter_context(patch.dict(owner._APPLICATION_FABRIC_TRANSPORTS, {"admin_fixture": transport}))
            stack.enter_context(patch.dict(os.environ, {"MM_PROVIDER_APPLICATION_MODE": "shared_fabric",
                "MM_PROVIDER_WORKLOAD_PROFILE": "site_interactive", "TEST_ADMIN_FABRIC_TOKEN": SERVICE_TOKEN,
                "ADMIN_DEPLOYED": "0", "ADMIN_PASSWORD": "fixture-admin-password",
                "ADMIN_SESSION_SECRET": "fixture-admin-session-key"}))
            stack.enter_context(patch.object(paths, "ROOT", root))
            stack.enter_context(patch.object(server.marketing_floor, "_default_root", lambda: root))
            with patch.object(owner, "_resolve_credential", wraps=owner._resolve_credential) as secret:
                httpd = server._build_server("127.0.0.1", 0)
                assert secret.call_count == 1 and httpd.fabric_pool_reader is not None
            stack.enter_context(patch.object(owner, "_resolve_credential", side_effect=AssertionError("GET credential")))
            thread = threading.Thread(target=lambda: httpd.serve_forever(poll_interval=.01), daemon=True)
            thread.start()
            try:
                server._clear_response_cache()
                cookie = server.auth.SESSION_COOKIE + "=" + server.auth.mint_session()
                def read(force=False):
                    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=5)
                    try:
                        connection.request("GET", "/api/marketing/models" + ("?force=1" if force else ""),
                                           headers={"Cookie": cookie})
                        response = connection.getresponse();payload = json.loads(response.read())
                        assert response.status == 200 and payload["ok"]
                        return payload
                    finally:
                        connection.close()
                first = read()
                assert first["fabric"]["available"] and len(first["fabric"]["pools"]) == 9
                assert first["fabric"]["observed_at"] == case.clock[0]
                assert first["fabric"]["pools"][0]["models"][0]["ledger_room"] == 4
                assert all(lane["first_choice"] == "fabric" and lane["fabric_route"]["state"] == "held" for lane in first["lanes"])
                case.grant["enabled"] = False;case.save()
                held = read(force=True)
                assert held["fabric"]["pools"][0]["application_state"] == "held"
                assert all(m["ledger_room"] is None for m in held["fabric"]["pools"][0]["models"])
                assert before == {table: case.rows(table) for table in before}
                assert (case.posts, case.gets, case.usage_rows()) == ([], [], [])
                print(json.dumps({"result": "PASS", "authenticated_admin_reads": 2, "native_pools": 9,
                    "source_blobs": PINS, "provider_requests": 0, "lease_or_turn_mutations": 0,
                    "startup_credential_resolutions": 1, "request_credential_resolutions": 0,
                    "inference_qualified": False, "production_activation": False}, sort_keys=True))
            finally:
                httpd.shutdown();httpd.server_close();thread.join(2);server._clear_response_cache()
    finally:
        case.doCleanups()


if __name__ == "__main__":
    main()
