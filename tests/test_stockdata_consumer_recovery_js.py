"""S3-01 consumer half: a consumer that read the index during a transient failure
must ask again once the loader's failure window closes — without a polling loop.

#8764 made `templates/stockdata.js` stop caching a failed index read as success:
a 5xx/408/429/thrown read is retried after a short window (Retry-After honoured).
But the consumers called the loader exactly once at init, so a first read that
landed inside a blip left the page nameless until a reload. This suite drives the
REAL stockdata.js + watchstore.js + portfolio_state.js + portfolio.js under fake
timers and a fake fetch whose US index answers 503 once, then 200:

* the portfolio table renders WITHOUT the index-backed company name after the 503;
* advancing the fake clock past the failure window (30 s + slack) re-asks the
  loader exactly once and the table repaints WITH the name;
* nothing re-asks after that (no polling).

Red-first: point STOCKDATA_JS / PORTFOLIO_JS at the pre-fix copies and the
"fills after the window" assertion fails — the consumer never asks again.

The harness (DOM shim, deferred-db, drain) is reused from
tests/test_portfolio_auth_transition_js.py rather than copied.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from tests.test_portfolio_auth_transition_js import ANON_SEED, SHIM

HAS_NODE = shutil.which("node") is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node not on PATH")

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "templates"
STOCKDATA = Path(os.environ.get("STOCKDATA_JS") or TPL / "stockdata.js")
PORTFOLIO = Path(os.environ.get("PORTFOLIO_JS") or TPL / "portfolio.js")
WATCHSTORE = TPL / "watchstore.js"
PORTFOLIO_STATE = TPL / "portfolio_state.js"

NAME_A = "Anon Alpha Holdings Ltd"

# Fake clock + timer queue + fetch, installed BEFORE any module is required so every
# setTimeout/Date.now the modules capture is the fake one. drain() (from SHIM) uses
# setImmediate, which is left real so promise chains still settle.
CLOCK = r"""
var __t0 = 1790000000000, __now = 0, __tid = 0, __timers = [];
Date.now = function () { return __t0 + __now; };
global.setTimeout = function (fn, ms) {
  var id = ++__tid;
  __timers.push({ id: id, at: __now + Math.max(0, +ms || 0), fn: fn });
  return id;
};
global.clearTimeout = function (id) {
  __timers = __timers.filter(function (t) { return t.id !== id; });
};
async function advance(ms) {
  var target = __now + ms;
  for (;;) {
    var due = __timers.filter(function (t) { return t.at <= target; })
                      .sort(function (a, b) { return a.at - b.at || a.id - b.id; })[0];
    if (!due) break;
    __timers = __timers.filter(function (t) { return t !== due; });
    __now = due.at;
    due.fn();
    await drain(10);
  }
  __now = target;
  await drain(10);
}

// US index: one 503, then a valid payload. Every other request 404s (per-ticker
// JSON, other market stores) so only the index route matters.
var __indexHits = 0, __indexPlan = [503, 200];
global.fetch = function (url) {
  url = String(url);
  if (/(^|\/)stockdata\/index\.json$/.test(url)) {
    var status = __indexPlan[Math.min(__indexHits, __indexPlan.length - 1)];
    __indexHits++;
    if (status !== 200) {
      return Promise.resolve({ ok: false, status: status,
        headers: { get: function () { return null; } },
        json: function () { return Promise.reject(new Error('no body')); } });
    }
    return Promise.resolve({ ok: true, status: 200,
      headers: { get: function () { return null; } },
      json: function () { return Promise.resolve(__INDEX_ROWS); } });
  }
  return Promise.resolve({ ok: false, status: 404,
    headers: { get: function () { return null; } },
    json: function () { return Promise.reject(new Error('404')); } });
};
"""


def _run(js_body: str) -> dict:
    rows = [
        {"t": "ANONA", "n": NAME_A, "st": None},
        {"t": "ANONB", "n": "Anon Beta Corp", "st": None},
    ]
    script = (
        SHIM
        + "\nvar __INDEX_ROWS = " + json.dumps(rows) + ";\n"
        + CLOCK
        + "\nrequire(%s);\n" % json.dumps(str(STOCKDATA))
        + "var WSL, PS;\nfunction boot() {\n  WSL = require(%s);\n  PS = require(%s);\n  require(%s);\n}\n"
        % (json.dumps(str(WATCHSTORE)), json.dumps(str(PORTFOLIO_STATE)), json.dumps(str(PORTFOLIO)))
        + "\n(async function () {\ntry {\n"
        + textwrap.dedent(js_body)
        + "\n} catch (e) {\n  process.stdout.write(JSON.stringify({__error: String(e && e.stack || e)}));\n  process.exit(1);\n}\n})();\n"
    )
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, f"node failed:\nSTDERR:\n{res.stderr}\nSTDOUT:\n{res.stdout}"
    out = json.loads(res.stdout)
    assert "__error" not in out, out.get("__error")
    return out


BODY = """
localStorage.setItem('mdash.pf.v1', JSON.stringify(""" + ANON_SEED + """));
boot();
await drain(12);
var after503 = { hits: __indexHits, html: node('tbl_pf').innerHTML };

// Inside the failure window nothing re-reads.
await advance(29000);
var inWindow = { hits: __indexHits };

// Past the 30 s window + slack: one re-ask, which succeeds.
await advance(1500);
var afterWindow = { hits: __indexHits, html: node('tbl_pf').innerHTML };

// Long after: no polling.
await advance(30 * 60 * 1000);
OUT({
  sdLoaded: !!(window.SD && window.SD.loadIndexes),
  after503: after503,
  inWindow: inWindow,
  afterWindow: afterWindow,
  finalHits: __indexHits,
  pendingTimers: __timers.length
});
"""


@needs_node
def test_portfolio_renders_the_names_after_the_failure_window_closes():
    out = _run(BODY)
    assert out["sdLoaded"] is True
    # The first read hit the 503: the table rendered, but without the index name.
    assert out["after503"]["hits"] == 1
    assert "ANONA" in out["after503"]["html"]
    assert NAME_A not in out["after503"]["html"]
    # No re-read before the window closes.
    assert out["inWindow"]["hits"] == 1
    # Exactly one re-ask once it closes, and the table repaints with the name.
    assert out["afterWindow"]["hits"] == 2
    assert NAME_A in out["afterWindow"]["html"]


@needs_node
def test_portfolio_does_not_poll_after_recovering():
    out = _run(BODY)
    assert out["finalHits"] == 2
