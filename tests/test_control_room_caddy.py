"""CCR-R0 Task 7: fail-closed Caddy boundary for the remote Control Room."""
from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
CADDY = ROOT / "app" / "deploy" / "Caddyfile"
CADDY_BIN = os.environ.get("CADDY_BIN", "caddy")


def _site_block(text: str, host: str) -> str:
    """Return one literal host block using the Caddyfile's balanced braces."""
    match = re.search(rf"(?m)^{re.escape(host)}\s*\{{", text)
    assert match is not None, f"missing Caddy host: {host}"
    assert len(re.findall(rf"(?m)^{re.escape(host)}\s*\{{", text)) == 1
    start = match.start()
    opening = text.index("{", match.start())
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError(f"unbalanced Caddy host block: {host}")


def _control_block() -> str:
    return _site_block(CADDY.read_text(encoding="utf-8"), "control.mastermind-x.com")


def _adapted_control_execution_labels() -> list[str]:
    """Return security-relevant handlers in Caddy's real adapted order."""
    result = subprocess.run(
        [CADDY_BIN, "adapt", "--config", str(CADDY), "--pretty"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    document = json.loads(result.stdout)
    site = None
    for server in document["apps"]["http"]["servers"].values():
        for route in server.get("routes", []):
            if any(
                "control.mastermind-x.com" in matcher.get("host", [])
                for matcher in route.get("match", [])
            ):
                site = route
                break
        if site is not None:
            break
    assert site is not None, "adapted config omitted the Control Room host"

    labels: list[str] = []

    def walk(routes: list[dict]) -> None:
        for route in routes:
            matchers = route.get("match", [])
            for handler in route.get("handle", []):
                kind = handler.get("handler")
                if kind == "subroute":
                    walk(handler.get("routes", []))
                    continue
                if kind == "static_response":
                    if any("/healthz" in matcher.get("path", []) for matcher in matchers):
                        labels.append("health_404")
                    elif any("not" in matcher for matcher in matchers):
                        labels.append("mutation_405")
                    continue
                if kind != "reverse_proxy":
                    continue
                if handler.get("rewrite", {}).get("uri") == "/api/auth-check":
                    labels.append("auth_proxy")
                    continue
                if any(
                    upstream.get("dial") == "unix//run/mastermind-control-room/remote.sock"
                    for upstream in handler.get("upstreams", [])
                ):
                    labels.append("unix_proxy")

    walk([site])
    return labels


def test_control_room_authenticates_once_before_the_only_unix_origin():
    """Removing/reordering the auth subrequest or adding a second origin must fail."""
    block = _control_block()

    assert block.count("reverse_proxy 127.0.0.1:8787 {") == 1
    assert block.count("rewrite /api/auth-check") == 1
    assert block.count("reverse_proxy unix//run/mastermind-control-room/remote.sock {") == 1
    assert block.index("rewrite /api/auth-check") < block.index(
        "reverse_proxy unix//run/mastermind-control-room/remote.sock {"
    )
    auth = block[:block.index("reverse_proxy unix//run/mastermind-control-room/remote.sock {")]
    assert "header_up Host admin.mastermind-x.com" in auth
    assert re.search(r"@operator\s+status\s+2xx", block)
    assert re.search(r"handle_response\s+@operator\s*\{\s*\}", block)
    assert "127.0.0.1:8000" not in block
    assert "/api/control-room/auth-check" not in block
    assert not re.search(r"reverse_proxy\s+(?:127\.0\.0\.1|localhost|\[::1\]):\d+", block.replace("127.0.0.1:8787", ""))


def test_control_room_refuses_health_and_mutation_before_origin():
    """Health and mutation-shaped requests must never reach auth or projection."""
    block = _control_block()

    assert "@health path /healthz" in block
    assert "respond @health 404" in block
    assert "@mutation not method GET HEAD" in block
    assert "respond @mutation 405" in block
    route = block.index("route {")
    auth = block.index("rewrite /api/auth-check")
    assert route < block.index("respond @health 404") < auth
    assert route < block.index("respond @mutation 405") < auth
    assert "rewrite /healthz" not in block


def test_control_room_adapted_order_refuses_health_and_mutation_before_origin():
    """Caddy directive sorting must not move either refusal behind a proxy."""
    assert _adapted_control_execution_labels() == [
        "health_404",
        "mutation_405",
        "auth_proxy",
        "unix_proxy",
    ]


def test_control_room_socket_hop_strips_every_browser_and_forged_identity_header():
    """No browser credential or caller-supplied identity proof may cross the socket."""
    block = _control_block()
    socket = block[block.index("reverse_proxy unix//run/mastermind-control-room/remote.sock {") :]

    for name in (
        "Cookie",
        "Authorization",
        "X-CCR-Token",
        "X-Authenticated-User",
        "X-Original-Uri",
        "X-Original-Method",
        "X-Forwarded-For",
        "X-Forwarded-Host",
        "X-Forwarded-Proto",
    ):
        assert f"header_up -{name}" in socket
    assert "header_up Host control.mastermind-x.com" in socket


def test_control_room_responses_are_private_embeddable_only_by_admin_and_not_cached():
    """A broadened frame/cache/CORS policy or XFO conflict must fail."""
    block = _control_block()

    assert 'Cache-Control "private, no-store"' in block
    assert 'Vary "Cookie"' in block
    assert 'Strict-Transport-Security "max-age=31536000"' in block
    assert 'X-Content-Type-Options "nosniff"' in block
    assert 'X-Robots-Tag "noindex, nofollow, noarchive"' in block
    csp = re.search(r'Content-Security-Policy "([^"]+)"', block)
    assert csp is not None
    assert csp.group(1) == (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; base-uri 'none'; form-action 'none'; object-src 'none'; "
        "frame-ancestors https://admin.mastermind-x.com"
    )
    assert "-X-Frame-Options" in block
    assert not re.search(r"(?m)^\s*X-Frame-Options\b", block)
    assert "Access-Control-Allow" not in block
    assert "stale-if-error" not in block.lower()
    assert "file_server" not in block
    assert "try_files" not in block


# P12.T30.S2: the same pinned-Caddy lane also owns read-only Terminal data.
# These are offline adapter graph checks, not an executing HTTP/FileServer test.
_TERMINAL_DATA_SOURCE = Path(os.environ.get("MM_CADDY_SOURCE", str(Path(__file__).resolve().parents[1] / "app/deploy/Caddyfile")))
_TERMINAL_DATA_BIN = CADDY_BIN
_terminal_data_requires_adapter = pytest.mark.skipif(shutil.which(_TERMINAL_DATA_BIN) is None, reason="requires installed Caddy adapter; no server is started")


def _terminal_data_nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _terminal_data_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _terminal_data_nodes(child)


@lru_cache
def _terminal_data_adapted():
    result = subprocess.run(
        [_TERMINAL_DATA_BIN, "adapt", "--config", "-", "--adapter", "caddyfile"],
        input=_TERMINAL_DATA_SOURCE.read_text(), text=True, capture_output=True, check=True,
        timeout=15,
    )
    return json.loads(result.stdout)


def _terminal_data_routes():
    routes = [n for n in _terminal_data_nodes(_terminal_data_adapted()) if n.get("match") == [{"path": ["/data/*"]}]]
    assert len(routes) == 2  # incumbent app and beta share the same read-only owner
    return routes


def _terminal_data_recovery(route):
    stages = [n["routes"] for n in _terminal_data_nodes(route) if n.get("handler") == "subroute" and n.get("routes") and n["routes"][0].get("handle", [{}])[0].get("handler") == "file_server"]
    assert len(stages) == 1, "file_server must begin an explicitly ordered continuation"
    assert len(stages[0]) > 1, "missing files currently terminate before JSON recovery"
    return stages[0]


@_terminal_data_requires_adapter
def test_file_server_can_continue_only_inside_each_data_route():
    for route in _terminal_data_routes():
        stage = _terminal_data_recovery(route)
        assert stage[0]["handle"][0].get("pass_thru") is True, "missing files currently terminate before JSON recovery"
        assert [h["handler"] for h in stage[0]["handle"]] == ["file_server"]
        assert not any(n.get("handler") == "reverse_proxy" for n in _terminal_data_nodes(route))


@_terminal_data_requires_adapter
def test_read_fallback_is_explicit_json_404_and_overrides_public_cache():
    for route in _terminal_data_routes():
        fallback = {"routes": _terminal_data_recovery(route)[1:]}
        reads = [n for n in _terminal_data_nodes(fallback) if n.get("match") == [{"method": ["GET", "HEAD"]}]]
        assert reads
        headers = [n["response"]["set"] for r in reads for n in _terminal_data_nodes(r) if n.get("handler") == "headers"]
        assert {"Cache-Control": ["no-store"]} in headers
        assert {"Content-Type": ["application/json"]} in headers
        response = [n for r in reads for n in _terminal_data_nodes(r) if n.get("handler") == "static_response"]
        assert len(response) == 1
        assert response[0]["status_code"] == 404
        assert json.loads(response[0]["body"]) == {"error": "not_found"}


@_terminal_data_requires_adapter
def test_head_has_empty_response_before_get_body_and_other_methods_keep_native_404():
    for route in _terminal_data_routes():
        fallback = {"routes": _terminal_data_recovery(route)[1:]}
        routes = fallback["routes"]
        head = next(i for i, r in enumerate(routes) if r.get("match") == [{"method": ["HEAD"]}])
        body = next(i for i, r in enumerate(routes) if any(n.get("body") == '{"error":"not_found"}' for n in _terminal_data_nodes(r)))
        assert head < body
        assert routes[head]["handle"] == [{"handler": "static_response", "status_code": 404}]
        assert routes[-1]["handle"] == [{"handler": "error", "status_code": 404}]
        assert "match" not in routes[-1]


@_terminal_data_requires_adapter
def test_existing_file_serving_and_its_cache_policies_precede_recovery():
    for route in _terminal_data_routes():
        handlers = list(_terminal_data_nodes(route))
        fs = next(n for n in handlers if n.get("handler") == "file_server")
        assert set(fs) <= {"handler", "hide", "pass_thru"}
        assert {"handler": "vars", "root": "/opt/terminal/terminal/public"} in handlers
        headers = [n["response"]["set"] for n in handlers if n.get("handler") == "headers"]
        assert {"Cache-Control": ["public, s-maxage=60, max-age=0, must-revalidate"]} in headers
        assert {"Cache-Control": ["public, s-maxage=300, max-age=0, must-revalidate"]} in headers
        # There is no matcher in front of file_server that changes native method,
        # conditional/range, canonical redirect, permission or I/O handling.
        assert _terminal_data_recovery(route)[0]["handle"] == [fs]


@_terminal_data_requires_adapter
def test_continuation_does_not_add_global_error_or_html_auth_fallback():
    for route in _terminal_data_routes():
        assert not any("errors" in n for n in _terminal_data_nodes(route))
        assert not any(n.get("handler") in {"rewrite", "authentication", "reverse_proxy"} for n in _terminal_data_nodes(route))
        assert not any("Location" in n.get("response", {}).get("set", {}) for n in _terminal_data_nodes(route))
    # The actual two frontends still retain their original native service routes.
    proxies = [n for n in _terminal_data_nodes(_terminal_data_adapted()) if n.get("handler") == "reverse_proxy"]
    assert any(n.get("upstreams") == [{"dial": "127.0.0.1:3000"}] for n in proxies)
    assert any(n.get("upstreams") == [{"dial": "127.0.0.1:3001"}] for n in proxies)
