"""Numeric role isolation extends the existing APPLICATION client only."""
import time
from unittest.mock import Mock

import pytest

from engine import fabric_inference_client as owner


@pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.2", "127.0.0.3"])
def test_native_connection_uses_exact_qualified_numeric_host(monkeypatch, host):
    sock = Mock()
    monkeypatch.setattr(owner.socket, "socket", lambda *args: sock)
    connection = owner._NativeConnection(host, 50142, deadline=time.monotonic() + 2)
    try:
        connection.connect()
        sock.connect.assert_called_once_with((host, 50142))
    finally:
        connection.finish()


@pytest.mark.parametrize("host", ["127.0.0.2", "127.0.0.3"])
def test_role_alias_is_native_fixed_port_and_has_no_metadata_authority(host):
    client = owner.FabricInferenceClient(base_url=f"http://{host}:50142/v1",
        proxy_token="fixture-role-internal-credential-0123456789", model="fixture-model",
        protocol=owner.NATIVE_PROTOCOL, operation_id="fixture-original-admission")
    assert client._url.hostname == host and not client._admission_possible
    assert client.close() == {"disposition": "local_only", "closed": False,
                              "effect_unknown": False, "attempted": False}


@pytest.mark.parametrize("url,protocol", [
    ("http://127.0.0.2:50142/v1", owner.LEGACY_PROTOCOL),
    ("http://127.0.0.3:8311/v1", owner.NATIVE_PROTOCOL),
    ("https://127.0.0.2:50142/v1", owner.NATIVE_PROTOCOL),
    ("http://localhost:50142/v1", owner.NATIVE_PROTOCOL),
    ("http://127.0.0.4:50142/v1", owner.NATIVE_PROTOCOL),
    ("http://credential@127.0.0.2:50142/v1", owner.NATIVE_PROTOCOL),
    ("http://127.0.0.2:50142/v1?redirect=1", owner.NATIVE_PROTOCOL),
])
def test_unqualified_endpoints_refuse_before_socket(monkeypatch, url, protocol):
    monkeypatch.setattr(owner.socket, "socket", lambda *args: pytest.fail("endpoint opened socket"))
    with pytest.raises(owner.FabricInferenceError, match="fabric_endpoint_invalid"):
        owner.FabricInferenceClient(base_url=url,
            proxy_token="fixture-role-internal-credential-0123456789", model="fixture-model",
            protocol=protocol, operation_id="fixture-original" if protocol == owner.NATIVE_PROTOCOL else None)


@pytest.mark.parametrize("host,port,tls", [
    ("localhost", 50142, False), ("127.0.0.4", 50142, False),
    ("127.0.0.2", 80, False), ("127.0.0.3", 50142, True),
])
def test_connection_itself_cannot_bypass_numeric_endpoint_guard(host, port, tls):
    with pytest.raises(owner.FabricInferenceError, match="fabric_endpoint_invalid"):
        owner._NativeConnection(host, port, deadline=time.monotonic() + 2, tls=tls)
