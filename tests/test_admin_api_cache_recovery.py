"""Admin client API cache must recover after a transient network rejection.

The console coalesces cacheable GETs by storing the in-flight Promise. If fetch()
rejects before an HTTP response exists, that rejected Promise must be evicted; otherwise
every later visit to the same panel reuses the dead Promise until a full page reload.

This test executes the cache/api helpers sliced from the real admin/static/app.js in
Node. It intentionally fails if those helpers move without this guard being repointed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
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
