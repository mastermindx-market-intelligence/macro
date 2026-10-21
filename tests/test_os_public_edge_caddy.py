"""Qualify the installed Mastermind OS route at the real Caddy adapter boundary.

This is a deployment-input snapshot. Mastermind owns its renderer and gateway.
No test starts Caddy, contacts a gateway, or submits an Executive request.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
CADDY = ROOT / "app/deploy/Caddyfile"
MANIFEST = ROOT / "app/deploy/mastermind-os-edge/asset-manifest.json"
HOST = "mcp.mastermind-x.com"
MANIFEST_SHA256 = "3fc4a5f952afa87144a4f30dcbdf10aa3e93de3b289add8906e921b9de7e2282"
GET = [
    "/os/", "/os/auth/callback", "/workspace/programs/current",
    "/workspace/work/current", "/workspace/mission/current",
    "/workspace/mission/v3/current", "/workspace/result/current",
    "/workspace/plan/current", "/workspace/operator/activity/current",
    "/workspace/window/current",
]
POST = ["/os/executive/context", "/os/executive/submit", "/os/executive/status"]
DROP = [
    "Forwarded", "X-Forwarded-Host", "X-Forwarded-Port", "X-Real-IP",
    "CF-Connecting-IP", "EO-Connecting-IP", "EO-Client-IP",
]
PROXY = {
    "handler": "reverse_proxy",
    "headers": {"request": {
        "delete": DROP,
        "set": {
            "Host": [HOST], "X-Forwarded-For": ["127.0.0.1"],
            "X-Forwarded-Proto": ["https"],
        },
    }},
    "upstreams": [{"dial": "127.0.0.1:49152"}],
}


def _site_span(text):
    matches = list(re.finditer(r"(?m)^mcp\.mastermind-x\.com\s*\{", text))
    assert len(matches) == 1, "require one exact OS host"
    start = matches[0].start()
    depth = 0
    for index in range(text.index("{", start), len(text)):
        depth += (text[index] == "{") - (text[index] == "}")
        if depth == 0:
            return start, index + 1
    raise AssertionError("unclosed OS site")


def _adapt(text):
    result = subprocess.run(
        [os.environ.get("CADDY_BIN", "caddy"), "adapt", "--config", "-",
         "--adapter", "caddyfile"],
        input=text, cwd=ROOT, text=True, capture_output=True, check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


@lru_cache(maxsize=1)
def _documents():
    text = CADDY.read_text(encoding="utf-8")
    start, end = _site_span(text)
    # Identical input names avoid file_server.hide filename artifacts.
    return _adapt(text[:start] + text[end:]), _adapt(text)


def _locate_site(document):
    found = [
        (server, index, route)
        for server in document["apps"]["http"]["servers"].values()
        for index, route in enumerate(server.get("routes", []))
        if route.get("match") == [{"host": [HOST]}]
    ]
    assert len(found) == 1
    return found[0]


def _route_groups(node, path=()):
    """Yield only typed Route.group fields, never arbitrary module keys."""
    if isinstance(node, dict):
        if len(path) >= 2 and path[-2] == "routes" and isinstance(path[-1], int):
            if "group" in node:
                assert re.fullmatch(r"group\d+", node["group"])
                yield node
        for key in sorted(node):
            yield from _route_groups(node[key], (*path, key))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _route_groups(item, (*path, index))


def _normalize_groups(document):
    result = deepcopy(document)
    # A request's group identity spans nested routes and error routes.
    # Never reset the bijection within a subroute or reorder any array.
    for server in result["apps"]["http"]["servers"].values():
        labels = {}
        for route in _route_groups(server):
            old = route["group"]
            route["group"] = labels.setdefault(old, f"g{len(labels)}")
    return result


def _assert_existing_configuration_preserved(baseline, candidate):
    old = deepcopy(baseline)
    new = deepcopy(candidate)
    server, index, site = _locate_site(new)
    new_groups = {r["group"] for r in _route_groups([site], ("routes",))}
    server["routes"].pop(index)
    existing_groups = {r["group"] for r in _route_groups(server)}
    assert new_groups.isdisjoint(existing_groups), "new site shares an old route group"

    policies = new["apps"]["tls"]["automation"]["policies"]
    owners = [p for p in policies if HOST in p.get("subjects", [])]
    assert len(owners) == 1, "require one explicit new TLS subject"
    subjects = owners[0]["subjects"]
    assert subjects.count(HOST) == 1
    subjects.remove(HOST)
    # Removing an empty policy or wildcard would hide an authority change.
    assert subjects, "new host must not broaden a catch-all TLS policy"
    assert _normalize_groups(old) == _normalize_groups(new)


def _assert_os_boundary(document):
    _, _, site = _locate_site(document)
    assert set(site) == {"match", "handle", "terminal"}
    assert site["terminal"] is True
    assert len(site["handle"]) == 1
    outer = site["handle"][0]
    assert set(outer) == {"handler", "routes"} and outer["handler"] == "subroute"
    assert len(outer["routes"]) == 1
    wrapper = outer["routes"][0]
    assert set(wrapper) == {"handle"} and len(wrapper["handle"]) == 1
    inner = wrapper["handle"][0]
    assert set(inner) == {"handler", "routes"} and inner["handler"] == "subroute"
    branches = inner["routes"]
    assert len(branches) == 3
    get, post, fallback = branches
    manifest_bytes = MANIFEST.read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == MANIFEST_SHA256
    manifest = json.loads(manifest_bytes)
    assert manifest["schema"] == "mastermind.os_assets.v1"
    assert len(manifest["files"]) == 9
    assets = sorted(
        "/os/" if item["path"] == "index.html" else "/os/" + item["path"]
        for item in manifest["files"]
    )
    assert get["group"] == post["group"]
    for branch, method, paths, handlers in (
        (get, "GET", GET + assets, [PROXY]),
        (post, "POST", POST, [{"handler": "request_body", "max_size": 64000}, PROXY]),
    ):
        assert set(branch) == {"group", "match", "handle"}
        assert branch["match"] == [{"method": [method], "path": paths}]
        assert branch["handle"] == [{"handler": "subroute", "routes": [{"handle": handlers}]}]
    assert fallback == {"handle": [{"handler": "static_response", "abort": True}]}


def test_os_edge_preserves_all_existing_configuration():
    _assert_existing_configuration_preserved(*_documents())


def test_os_edge_exact_installed_assets_routes_methods_headers_and_limits():
    _assert_os_boundary(_documents()[1])


@pytest.mark.parametrize("mutation", ["route_order", "tls_order", "tls_subject", "group_collision"])
def test_equivalence_rejects_unrelated_security_changes(mutation):
    baseline, original = _documents()
    candidate = deepcopy(original)
    server, _, site = _locate_site(candidate)
    if mutation == "route_order":
        server["routes"][0], server["routes"][1] = server["routes"][1], server["routes"][0]
    elif mutation == "tls_order":
        candidate["apps"]["tls"]["automation"]["policies"].reverse()
    elif mutation == "tls_subject":
        candidate["apps"]["tls"]["automation"]["policies"][0]["subjects"].append("unrelated.invalid")
    else:
        new_group = next(_route_groups([site], ("routes",)))["group"]
        next(_route_groups(server))["group"] = new_group
    with pytest.raises(AssertionError):
        _assert_existing_configuration_preserved(baseline, candidate)


@pytest.mark.parametrize("mutation", ["wildcard", "method", "upstream", "identity_header", "body_limit", "fallback"])
def test_os_boundary_rejects_broadening(mutation):
    candidate = deepcopy(_documents()[1])
    site = _locate_site(candidate)[2]
    branches = site["handle"][0]["routes"][0]["handle"][0]["routes"]
    if mutation == "wildcard":
        branches[0]["match"][0]["path"].append("/os/assets/*")
    elif mutation == "method":
        branches[0]["match"][0]["method"].append("PUT")
    elif mutation == "fallback":
        branches[-1]["handle"][0] = deepcopy(PROXY)
    elif mutation == "body_limit":
        branches[1]["handle"][0]["routes"][0]["handle"][0]["max_size"] = 64001
    else:
        proxy = branches[0]["handle"][0]["routes"][0]["handle"][0]
        if mutation == "upstream":
            proxy["upstreams"][0]["dial"] = "127.0.0.1:8000"
        else:
            proxy["headers"]["request"]["set"]["X-Forwarded-For"] = ["{remote_host}"]
    with pytest.raises(AssertionError):
        _assert_os_boundary(candidate)
