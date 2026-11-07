"""The committed proxy file must be a template, never the live pool.

`tools/xguerrilla/proxies.yml` is gitignored because it carries the BartProxies
user and password. `proxies.example.yml` is what lands in Git, so these tests
hold the line: the template parses with credentials exported, the template
carries no literal credential, and the live file is not tracked.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess

import pytest

from tools.xguerrilla import net

HERE = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = HERE / "proxies.example.yml"
LIVE = HERE / "proxies.yml"
CRED = re.compile(r"^(\s*- )([0-9.]+:\d+):([^:]+):(.+)$")


def test_template_exists_and_is_not_the_live_pool():
    assert TEMPLATE.exists(), "proxies.example.yml must be committed as the template"
    raw = TEMPLATE.read_text()
    assert "${BART_USER}" in raw and "${BART_PASS}" in raw
    assert "BartProxies static ISP" in raw


def test_template_has_no_literal_credentials():
    """Every inventory line must be host:port:${VAR}:${VAR} — nothing concrete."""
    lines = [ln for ln in TEMPLATE.read_text().splitlines() if CRED.match(ln)]
    assert len(lines) == 16, f"expected 16 slots in the template, found {len(lines)}"
    for ln in lines:
        m = CRED.match(ln)
        user, pw = m.group(3), m.group(4)
        assert user.startswith("${") and user.endswith("}"), user
        assert pw.startswith("${") and pw.endswith("}"), pw


def test_template_loads_with_env_expansion(monkeypatch):
    monkeypatch.setenv("BART_USER", "u-test")
    monkeypatch.setenv("BART_PASS", "p-test")
    slots = net.load(str(TEMPLATE))
    assert len(slots) == 16
    assert all(s.user == "u-test" and s.password == "p-test" for s in slots)
    assert all(s.host.count(".") == 3 for s in slots)
    assert len({s.name for s in slots}) == 16
    # public() is the loggable form and must carry no password
    assert "p-test" not in repr(slots[0].public())
    assert "p-test" not in repr(slots[0])


def test_bind_still_exclusive_over_template(monkeypatch):
    monkeypatch.setenv("BART_USER", "u-test")
    monkeypatch.setenv("BART_PASS", "p-test")
    slots = net.load(str(TEMPLATE))
    handles = [f"child.{i}" for i in range(6)]
    bound = net.bind(slots, handles)
    assert len({s.name for s in bound.values()}) == 6
    with pytest.raises(ValueError):
        net.bind(slots, [f"child.{i}" for i in range(17)])


def test_live_pool_is_gitignored(tmp_path):
    """If the live file exists, Git must ignore it. Skipped outside a work tree."""
    if not LIVE.exists():
        pytest.skip("no live proxies.yml on this box")
    r = subprocess.run(
        ["git", "check-ignore", "-q", str(LIVE)],
        cwd=str(HERE.parent.parent),
        capture_output=True,
    )
    if r.returncode not in (0, 1):
        pytest.skip("not a git work tree")
    assert r.returncode == 0, "tools/xguerrilla/proxies.yml must be gitignored"
