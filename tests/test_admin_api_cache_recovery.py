"""Admin client API cache must recover after a transient network rejection.

The console coalesces cacheable GETs by storing the in-flight Promise. If fetch()
rejects before an HTTP response exists, that rejected Promise must be evicted; otherwise
every later visit to the same panel reuses the dead Promise until a full page reload.

This test executes the cache/api helpers sliced from the real admin/static/app.js in
Node. It intentionally fails if those helpers move without this guard being repointed.
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "admin" / "static" / "app.js"


def _require_node() -> None:
    if shutil.which("node"):
        return
    if os.environ.get("CI"):
        pytest.fail("node is required in CI for the admin API-cache recovery guard")
    pytest.skip("node is not on PATH locally")


def _real_helper_source() -> str:
    src = APP_JS.read_text(encoding="utf-8")
    cache_start = src.find("const API_CACHE = new Map();")
    cache_end = src.find("/* ---- lobe popup", cache_start)
    api_start = src.find("function describeNonJson")
    api_end = src.find("function post(", api_start)
    assert min(cache_start, cache_end, api_start, api_end) >= 0, (
        "admin API/cache helpers moved; repoint this behavioral guard to the real helpers"
    )
    return src[cache_start:cache_end] + "\n" + src[api_start:api_end]


def test_transient_fetch_rejection_does_not_poison_cache() -> None:
    _require_node()
    helper = _real_helper_source()
    harness = helper + r'''
function showLogin() {}
let fetchCalls = 0;
global.fetch = async function(path) {
  fetchCalls += 1;
  if (fetchCalls === 1) throw new Error("simulated transient network drop");
  return {
    status: 200,
    statusText: "OK",
    ok: true,
    headers: { get: () => "application/json" },
    text: async () => '{"ok":true,"recovered":true}'
  };
};
(async () => {
  let firstError = null;
  let secondError = null;
  let secondValue = null;
  try { await api("/api/health"); } catch (e) { firstError = e.message; }
  try { secondValue = await api("/api/health"); } catch (e) { secondError = e.message; }
  process.stdout.write(JSON.stringify({
    firstError,
    secondError,
    secondValue,
    fetchCalls,
    cachePending: !!(API_CACHE.get("/api/health") || {}).pending
  }));
})().catch(e => { console.error(e); process.exit(1); });
'''
    proc = subprocess.run(
        ["node", "-e", harness],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"node failed:\n{proc.stderr}\n{proc.stdout}"
    result = json.loads(proc.stdout)
    assert result["firstError"] == "simulated transient network drop"
    assert result["secondError"] is None, result
    assert result["secondValue"] == {"ok": True, "recovered": True}, result
    assert result["fetchCalls"] == 2, result
    assert result["cachePending"] is False, result


def _content_module(monkeypatch: pytest.MonkeyPatch):
    """Import the real inventory module under this job's declared dependencies.

    ``admin.content`` imports ``config_store`` only for the unrelated live-uptime
    probe. The admin-js guard job intentionally installs just pytest, so provide
    that one unused seam rather than silently widening the gate with PyYAML.
    """
    cached = sys.modules.get("admin.content")
    if cached is not None:
        return cached
    stub = types.ModuleType("admin.config_store")
    stub.get_value = lambda _key: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "admin.config_store", stub)
    import admin

    monkeypatch.setattr(admin, "config_store", stub, raising=False)
    return importlib.import_module("admin.content")


class TestSiteInventoryLinkCache:
    """The Site inventory cache must resolve and invalidate against its own tree."""

    @staticmethod
    def _bind_site(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        content = _content_module(monkeypatch)
        site = tmp_path / "site"
        templates = tmp_path / "templates"
        site.mkdir()
        templates.mkdir()
        monkeypatch.setattr(content, "SITE", site)
        monkeypatch.setattr(content, "_TEMPLATES", templates)
        content._link_cache.clear()
        return content, site

    def test_root_relative_page_resolves_inside_site(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        content, site = self._bind_site(monkeypatch, tmp_path)
        (site / "index.html").write_text('<a href="/existing.html">Existing</a>')
        (site / "existing.html").write_text("<main>present</main>")

        result = content._link_check()

        assert result["count"] == 0
        assert result["broken"] == []

    def test_relative_escape_is_broken_even_when_host_file_exists(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        content, site = self._bind_site(monkeypatch, tmp_path)
        (tmp_path / "outside.html").write_text("<main>host-only file</main>")
        (site / "index.html").write_text('<a href="../outside.html">Escape</a>')

        result = content._link_check()

        assert result["count"] == 1
        assert result["broken"] == [
            {"page": "index.html", "link": "../outside.html"}
        ]

    def test_older_page_edit_invalidates_cache(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        content, site = self._bind_site(monkeypatch, tmp_path)
        source = site / "index.html"
        existing = site / "exists.html"
        newest = site / "newest.html"
        source.write_text('<a href="/exists.html">Target</a>')
        existing.write_text("<main>present</main>")
        newest.write_text("<main>newest</main>")

        # Keep one unrelated page newest across both scans. The retired cache key
        # used only page count + this maximum mtime, so editing ``index.html`` was
        # invisible. The replacement fingerprints every page's own stat record.
        base_ns = 1_700_000_000_000_000_000
        os.utime(source, ns=(base_ns, base_ns))
        os.utime(existing, ns=(base_ns + 1_000_000_000, base_ns + 1_000_000_000))
        os.utime(newest, ns=(base_ns + 10_000_000_000, base_ns + 10_000_000_000))

        first = content.link_check()
        assert first["count"] == 0

        # Same number of files and same byte length; only this older page's content
        # and own mtime change. The second call must not return the cached zero.
        source.write_text('<a href="/absent.html">Target</a>')
        os.utime(source, ns=(base_ns + 2_000_000_000, base_ns + 2_000_000_000))
        second = content.link_check()

        assert second["count"] == 1
        assert second["broken"] == [
            {"page": "index.html", "link": "/absent.html"}
        ]

    def test_template_removal_invalidates_ci_built_cache(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        content, site = self._bind_site(monkeypatch, tmp_path)
        templates = tmp_path / "templates"
        source = site / "index.html"
        template = templates / "ghost.html.j2"
        source.write_text('<a href="/ghost.html">Generated page</a>')
        template.write_text("<main>rendered by CI</main>")

        first = content.link_check()
        assert first["count"] == 0
        assert first["ci_built_count"] == 1

        template.unlink()
        second = content.link_check()

        assert second["ci_built_count"] == 0
        assert second["count"] == 1
        assert second["broken"] == [
            {"page": "index.html", "link": "/ghost.html"}
        ]

    def test_template_symlink_destination_disappearance_invalidates_cache(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        content, site = self._bind_site(monkeypatch, tmp_path)
        templates = tmp_path / "templates"
        outside = tmp_path / "outside"
        outside.mkdir()
        source = site / "index.html"
        target = outside / "template-target"
        template = templates / "ghost.html.j2"
        source.write_text('<a href="/ghost.html">Generated page</a>')
        target.write_text("<main>rendered by CI</main>")
        template.symlink_to(target)

        first = content.link_check()
        assert first["count"] == 0
        assert first["ci_built_count"] == 1

        target.unlink()
        second = content.link_check()

        assert second["ci_built_count"] == 0
        assert second["count"] == 1
        assert second["broken"] == [
            {"page": "index.html", "link": "/ghost.html"}
        ]

    def test_directory_symlink_retarget_invalidates_cache(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        content, site = self._bind_site(monkeypatch, tmp_path)
        source = site / "index.html"
        inside = site / "inside"
        outside = tmp_path / "outside"
        inside.mkdir()
        outside.mkdir()
        source.write_text('<a href="alias/target.html">Aliased page</a>')
        (inside / "target.html").write_text("<main>same-size target</main>")
        (outside / "target.html").write_text("<main>same-size target</main>")
        alias = site / "alias"
        alias.symlink_to(inside, target_is_directory=True)

        first = content.link_check()
        assert first["count"] == 0

        alias.unlink()
        alias.symlink_to(outside, target_is_directory=True)
        second = content.link_check()

        assert second["count"] == 1
        assert second["broken"] == [
            {"page": "index.html", "link": "alias/target.html"}
        ]


def test_http_200_semantic_failure_does_not_poison_client_cache() -> None:
    _require_node()
    helper = _real_helper_source()
    harness = helper + r'''
function showLogin() {}
let fetchCalls = 0;
global.fetch = async function(path) {
  fetchCalls += 1;
  const body = fetchCalls === 1
    ? '{"ok":false,"error":"transient upstream timeout"}'
    : '{"ok":true,"recovered":true}';
  return {
    status: 200,
    statusText: "OK",
    ok: true,
    headers: { get: () => "application/json" },
    text: async () => body
  };
};
(async () => {
  const firstValue = await api("/api/health");
  const secondValue = await api("/api/health");
  const thirdValue = await api("/api/health");
  process.stdout.write(JSON.stringify({
    firstValue,
    secondValue,
    thirdValue,
    fetchCalls,
    cached: API_CACHE.has("/api/health")
  }));
})().catch(e => { console.error(e); process.exit(1); });
'''
    proc = subprocess.run(
        ["node", "-e", harness],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"node failed:\n{proc.stderr}\n{proc.stdout}"
    result = json.loads(proc.stdout)
    assert result["firstValue"]["ok"] is False
    assert result["secondValue"] == {"ok": True, "recovered": True}
    assert result["thirdValue"] == {"ok": True, "recovered": True}
    assert result["fetchCalls"] == 2
    assert result["cached"] is True
