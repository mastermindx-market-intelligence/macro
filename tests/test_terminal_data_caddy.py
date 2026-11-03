"""Offline checks of the actual Caddy adapter graph, never a running server.

The installed adapter must place static serving before data-only missing-file
recovery. Caddy's native file/method/error behavior is not simulated here.
Run with an installed Caddy: python3 -m pytest tests/test_terminal_data_caddy.py -q
"""
from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

SOURCE = Path(os.environ.get("MM_CADDY_SOURCE", str(Path(__file__).resolve().parents[1] / "app/deploy/Caddyfile")))
CADDY = shutil.which("caddy")
pytestmark = pytest.mark.skipif(CADDY is None, reason="requires installed Caddy adapter; no server is started")


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


@lru_cache
def adapted():
    result = subprocess.run(
        [CADDY, "adapt", "--config", "-", "--adapter", "caddyfile"],
        input=SOURCE.read_text(), text=True, capture_output=True, check=True,
        timeout=15,
    )
    return json.loads(result.stdout)


def data_routes():
    routes = [n for n in nodes(adapted()) if n.get("match") == [{"path": ["/data/*"]}]]
    assert len(routes) == 2  # incumbent app and beta share the same read-only owner
    return routes


def recovery(route):
    stages = [n["routes"] for n in nodes(route) if n.get("handler") == "subroute" and n.get("routes") and n["routes"][0].get("handle", [{}])[0].get("handler") == "file_server"]
    assert len(stages) == 1, "file_server must begin an explicitly ordered continuation"
    assert len(stages[0]) > 1, "missing files currently terminate before JSON recovery"
    return stages[0]


def test_file_server_can_continue_only_inside_each_data_route():
    for route in data_routes():
        stage = recovery(route)
        assert stage[0]["handle"][0].get("pass_thru") is True, "missing files currently terminate before JSON recovery"
        assert [h["handler"] for h in stage[0]["handle"]] == ["file_server"]
        assert not any(n.get("handler") == "reverse_proxy" for n in nodes(route))


def test_read_fallback_is_explicit_json_404_and_overrides_public_cache():
    for route in data_routes():
        fallback = {"routes": recovery(route)[1:]}
        reads = [n for n in nodes(fallback) if n.get("match") == [{"method": ["GET", "HEAD"]}]]
        assert reads
        headers = [n["response"]["set"] for r in reads for n in nodes(r) if n.get("handler") == "headers"]
        assert {"Cache-Control": ["no-store"]} in headers
        assert {"Content-Type": ["application/json"]} in headers
        response = [n for r in reads for n in nodes(r) if n.get("handler") == "static_response"]
        assert len(response) == 1
        assert response[0]["status_code"] == 404
        assert json.loads(response[0]["body"]) == {"error": "not_found"}


def test_head_has_empty_response_before_get_body_and_other_methods_keep_native_404():
    for route in data_routes():
        fallback = {"routes": recovery(route)[1:]}
        routes = fallback["routes"]
        head = next(i for i, r in enumerate(routes) if r.get("match") == [{"method": ["HEAD"]}])
        body = next(i for i, r in enumerate(routes) if any(n.get("body") == '{"error":"not_found"}' for n in nodes(r)))
        assert head < body
        assert routes[head]["handle"] == [{"handler": "static_response", "status_code": 404}]
        assert routes[-1]["handle"] == [{"handler": "error", "status_code": 404}]
        assert "match" not in routes[-1]


def test_existing_file_serving_and_its_cache_policies_precede_recovery():
    for route in data_routes():
        handlers = list(nodes(route))
        fs = next(n for n in handlers if n.get("handler") == "file_server")
        assert set(fs) <= {"handler", "hide", "pass_thru"}
        assert {"handler": "vars", "root": "/opt/terminal/terminal/public"} in handlers
        headers = [n["response"]["set"] for n in handlers if n.get("handler") == "headers"]
        assert {"Cache-Control": ["public, s-maxage=60, max-age=0, must-revalidate"]} in headers
        assert {"Cache-Control": ["public, s-maxage=300, max-age=0, must-revalidate"]} in headers
        # There is no matcher in front of file_server that changes native method,
        # conditional/range, canonical redirect, permission or I/O handling.
        assert recovery(route)[0]["handle"] == [fs]


def test_continuation_does_not_add_global_error_or_html_auth_fallback():
    for route in data_routes():
        assert not any("errors" in n for n in nodes(route))
        assert not any(n.get("handler") in {"rewrite", "authentication", "reverse_proxy"} for n in nodes(route))
        assert not any("Location" in n.get("response", {}).get("set", {}) for n in nodes(route))
    # The actual two frontends still retain their original native service routes.
    proxies = [n for n in nodes(adapted()) if n.get("handler") == "reverse_proxy"]
    assert any(n.get("upstreams") == [{"dial": "127.0.0.1:3000"}] for n in proxies)
    assert any(n.get("upstreams") == [{"dial": "127.0.0.1:3001"}] for n in proxies)
