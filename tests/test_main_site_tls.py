"""Regression guard for browser-trusted TLS on the flagship hosts.

Normal traffic terminates TLS at EdgeOne, but a stale/bypassed DNS answer can
reach the origin directly. The origin must therefore never present Caddy's
local CA for the public www/apex hosts.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CADDY = (ROOT / "app" / "deploy" / "Caddyfile").read_text(encoding="utf-8")


def _site_block(host: str) -> str:
    lines = CADDY.splitlines()
    marker = f"{host} {{"
    start = next(i for i, line in enumerate(lines) if line.strip() == marker)
    depth = 0
    out = []
    for line in lines[start:]:
        out.append(line)
        code = line.split("#", 1)[0]
        depth += code.count("{") - code.count("}")
        if len(out) > 1 and depth == 0:
            return "\n".join(out)
    raise AssertionError(f"unterminated Caddy site block for {host}")


def test_www_origin_never_uses_caddy_local_ca():
    body = _site_block("www.mastermind-x.com")
    assert "tls internal" not in body, (
        "www is publicly reachable if DNS/CDN is bypassed; tls internal exposes "
        "Caddy Local Authority and causes NET::ERR_CERT_AUTHORITY_INVALID"
    )


def test_apex_origin_never_uses_caddy_local_ca():
    body = _site_block("mastermind-x.com")
    assert "tls internal" not in body
