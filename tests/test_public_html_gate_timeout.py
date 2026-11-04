"""Regression contracts for the public HTML gate's bounded upstream wait.

This is a structural guard, not a Caddy runtime / deployed-site latency proof.
The incumbent Caddy behavioral suites must still exercise allow, deny, gate-down,
missing-file and protected-asset paths before release.
"""
from pathlib import Path
import re
import shlex

CADDY = (Path(__file__).resolve().parents[1] / "app/deploy/Caddyfile").read_text()


def _handler(name: str) -> str:
    # Match handlers at their true indentation: top-level is one tab and
    # nested handle_errors children are two tabs. Do not match an inner close.
    match = re.search(rf"(?m)^(\t+)handle @{re.escape(name)} \{{\n", CADDY)
    assert match, f"missing @{name} handler"
    tail = CADDY[match.end():]
    closing = re.search(r"(?m)^" + re.escape(match.group(1)) + r"\}$", tail)
    assert closing, f"unterminated @{name} handler"
    return tail[:closing.start()]


def _matcher_paths(name: str) -> set[str]:
    match = re.search(
        rf"(?ms)^\s*@{re.escape(name)} \{{\n\s*path ([^\n]+)\n\s*\}}", CADDY
    )
    assert match, f"missing @{name} path matcher"
    return set(shlex.split(match.group(1)))


def test_public_html_gate_has_bounded_loopback_wait_only() -> None:
    handler = _handler("gate_html")
    assert handler.count("reverse_proxy 127.0.0.1:8000 {") == 1
    assert handler.count("rewrite /api/gate/check") == 1
    assert "method GET" in handler
    assert "transport http {\n\t\t\t\t\tdial_timeout 300ms\n" in handler
    assert "\t\t\t\t\tresponse_header_timeout 900ms\n\t\t\t\t}" in handler
    assert handler.count("response_header_timeout") == 1
    assert "@allow status 2xx" in handler
    assert "handle_response @allow {" in handler
    # Real deny (403) still copies the upstream response; only transport errors
    # reach the existing fail-open error path.
    assert "header Cache-Control \"public, max-age=60, must-revalidate\"" in handler
    assert "file_server {" in handler


def test_fail_open_scope_covers_exactly_the_public_html_gate() -> None:
    assert _matcher_paths("gate_html") == _matcher_paths("gate_html_err")
    assert {"/", "/index.html", "/macro.html", "/plans.html"} <= _matcher_paths("gate_html")
    assert not {"/api/*", "/sb/*", "/premiumdata/*", "/admin/*"}.intersection(
        _matcher_paths("gate_html")
    )
    error = _handler("gate_html_err")
    assert 'header Cache-Control "no-store"' in error
    assert "file_server {\n\t\t\t\tstatus 200" in error
    # Private data never inherits the public shell's fail-open error branch.
    asset_error = _handler("reg_asset_err")
    assert 'respond `{"error":"site_access_temporarily_unavailable"}` 503' in asset_error


def test_protected_assets_and_other_html_keep_original_route_owners() -> None:
    asset = _handler("reg_asset")
    assert "rewrite /api/regwall/check" in asset
    assert "rewrite /api/paywall/check" in asset
    assert 'header Cache-Control "private, no-store"' in asset
    assert "response_header_timeout 900ms" not in asset
    # No scope creep: the remaining *.html gate remains unchanged in this P0
    # source slice until its error behavior and business policy are qualified.
    ordinary_html = _handler("open_html")
    assert "rewrite /api/gate/check" in ordinary_html
    assert "response_header_timeout 900ms" not in ordinary_html
    never = _handler("never_site")
    assert 'respond "Not found" 404' in never
