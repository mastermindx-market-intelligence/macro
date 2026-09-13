"""Regression tests for pending Watchlist writes across list-binding changes.

A local edit is acknowledged only when its own binding's localStorage write succeeds.
Switching lists must therefore flush the old binding before ``listId`` and ``blob`` are
rebound; otherwise the delayed callback writes the new list under the new key and the
old edit disappears.  These tests exercise the real browser IIFE in a Node shell.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

HAS_NODE = shutil.which("node") is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node not on PATH")

ROOT = Path(__file__).resolve().parents[1]
WATCHLIST = ROOT / "templates" / "watchlist.js"

SHIM = """
var __store = {};
var __sets = [];
var __failKey = null;
var __events = [];
var __banner = { textContent: '', style: { display: 'none' } };
global.localStorage = {
  getItem: function (k) {
    return Object.prototype.hasOwnProperty.call(__store, k) ? __store[k] : null;
  },
  setItem: function (k, v) {
    __sets.push(k);
    if (__failKey === k) throw new Error('blocked write for ' + k);
    __store[k] = String(v);
  },
  removeItem: function (k) { delete __store[k]; }
};
global.sessionStorage = {
  getItem: function () { return null; },
  setItem: function () {}
};
global.CustomEvent = function (t, o) { this.type = t; this.detail = o && o.detail; };
global.document = {
  readyState: 'loading',
  documentElement: {
    getAttribute: function () { return 'en'; },
    classList: { add: function () {}, remove: function () {} }
  },
  getElementById: function (id) { return id === 'wl_banner' ? __banner : null; },
  querySelector: function () { return null; },
  querySelectorAll: function () { return []; },
  addEventListener: function () {},
  removeEventListener: function () {},
  dispatchEvent: function () { return true; },
  createElement: function () { return { style: {}, classList: { add: function () {} } }; }
};
global.window = global;
global.window.addEventListener = function () {};
global.window.mmTrackGrowth = function (wire, meta) { __events.push({wire: wire, meta: meta}); };
global.location = { hash: '', pathname: '/watchlist.html', search: '', origin: 'https://x' };
function wait(ms) { return new Promise(function (resolve) { setTimeout(resolve, ms); }); }
function tickers(raw) {
  if (!raw) return [];
  return (JSON.parse(raw).items || []).map(function (it) { return it.t; }).sort();
}
function OUT(o) { process.stdout.write(JSON.stringify(o)); }
"""


def _run(js_body: str) -> dict:
    script = SHIM + "\nvar WLT = require(%s);\n" % json.dumps(str(WATCHLIST))
    script += textwrap.dedent(js_body)
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, f"node failed:\nSTDERR:\n{res.stderr}\nSTDOUT:\n{res.stdout}"
    assert res.stdout.strip(), f"no stdout; stderr:\n{res.stderr}"
    return json.loads(res.stdout)


def _blob(*symbols: str) -> dict:
    return {
        "v": 1,
        "updated": "2026-09-10T00:00:00.000Z",
        "items": [
            {"t": symbol, "added": f"2026-09-10T00:00:{index:02d}.000Z", "note": ""}
            for index, symbol in enumerate(symbols)
        ],
        "order": list(symbols),
        "settings": {"sort": "order", "buySoonOnly": False},
    }


@needs_node
def test_pending_default_write_is_owned_by_default_across_immediate_named_switch():
    out = _run(
        """
        localStorage.setItem('mdash.watchlist.v1', JSON.stringify(DEFAULT));
        localStorage.setItem('mdash.wl.L-B.v1', JSON.stringify(NAMED));
        __sets = [];
        window.WL.bindList(null);
        window.WL.add('NVDA');
        window.WL.bindList('L-B', 'Other account list');
        var visibleImmediately = window.WL.getBlob().items.map(function (it) { return it.t; }).sort();
        wait(350).then(function () {
          OUT({
            defaultTickers: tickers(localStorage.getItem('mdash.watchlist.v1')),
            namedTickers: tickers(localStorage.getItem('mdash.wl.L-B.v1')),
            visibleImmediately: visibleImmediately,
            writes: __sets,
            savedEvents: __events.filter(function (e) { return e.wire === 'watchlist.saved'; }).length
          });
        });
        """.replace("DEFAULT", json.dumps(_blob("AAPL", "MSFT"))).replace(
            "NAMED", json.dumps(_blob("NEM"))
        )
    )
    assert out["defaultTickers"] == ["AAPL", "MSFT", "NVDA"]
    assert out["namedTickers"] == ["NEM"]
    assert out["visibleImmediately"] == ["NEM"]
    assert out["writes"] == ["mdash.watchlist.v1"]
    assert out["savedEvents"] == 1


@needs_node
def test_pending_named_write_is_owned_by_named_across_immediate_default_switch():
    out = _run(
        """
        localStorage.setItem('mdash.wl.L-A.v1', JSON.stringify(NAMED));
        localStorage.setItem('mdash.watchlist.v1', JSON.stringify(DEFAULT));
        __sets = [];
        window.WL.bindList('L-A', 'AI');
        window.WL.add('NVDA');
        window.WL.bindList(null);
        wait(350).then(function () {
          OUT({
            namedTickers: tickers(localStorage.getItem('mdash.wl.L-A.v1')),
            defaultTickers: tickers(localStorage.getItem('mdash.watchlist.v1')),
            visible: window.WL.getBlob().items.map(function (it) { return it.t; }).sort(),
            writes: __sets
          });
        });
        """.replace("NAMED", json.dumps(_blob("AAPL", "MSFT"))).replace(
            "DEFAULT", json.dumps(_blob("NEM"))
        )
    )
    assert out["namedTickers"] == ["AAPL", "MSFT", "NVDA"]
    assert out["defaultTickers"] == ["NEM"]
    assert out["visible"] == ["NEM"]
    assert out["writes"] == ["mdash.wl.L-A.v1"]


@needs_node
def test_same_id_rebind_flushes_then_reloads_the_just_saved_cache():
    out = _run(
        """
        localStorage.setItem('mdash.wl.L-A.v1', JSON.stringify(NAMED));
        __sets = [];
        window.WL.bindList('L-A', 'AI');
        window.WL.add('NVDA');
        window.WL.bindList('L-A', 'AI');
        var visibleImmediately = window.WL.getBlob().items.map(function (it) { return it.t; }).sort();
        wait(350).then(function () {
          OUT({
            stored: tickers(localStorage.getItem('mdash.wl.L-A.v1')),
            visibleImmediately: visibleImmediately,
            writes: __sets
          });
        });
        """.replace("NAMED", json.dumps(_blob("AAPL")))
    )
    assert out["stored"] == ["AAPL", "NVDA"]
    assert out["visibleImmediately"] == ["AAPL", "NVDA"]
    assert out["writes"] == ["mdash.wl.L-A.v1"]


@needs_node
def test_failed_old_binding_flush_is_disclosed_and_never_retargeted():
    out = _run(
        """
        localStorage.setItem('mdash.watchlist.v1', JSON.stringify(DEFAULT));
        localStorage.setItem('mdash.wl.L-B.v1', JSON.stringify(NAMED));
        __sets = [];
        window.WL.bindList(null);
        __failKey = 'mdash.watchlist.v1';
        window.WL.add('NVDA');
        window.WL.bindList('L-B', 'Other account list');
        wait(350).then(function () {
          OUT({
            attempts: __sets,
            defaultTickers: tickers(localStorage.getItem('mdash.watchlist.v1')),
            namedTickers: tickers(localStorage.getItem('mdash.wl.L-B.v1')),
            bannerDisplay: __banner.style.display,
            bannerText: __banner.textContent,
            savedEvents: __events.filter(function (e) { return e.wire === 'watchlist.saved'; }).length
          });
        });
        """.replace("DEFAULT", json.dumps(_blob("AAPL", "MSFT"))).replace(
            "NAMED", json.dumps(_blob("NEM"))
        )
    )
    assert out["attempts"] == ["mdash.watchlist.v1"]
    assert out["defaultTickers"] == ["AAPL", "MSFT"]
    assert out["namedTickers"] == ["NEM"]
    assert out["bannerDisplay"] == "block"
    assert "blocking local storage" in out["bannerText"]
    assert out["savedEvents"] == 0
