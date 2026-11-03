"""tests/test_prophet_r7_wave_a_watchlist.py — Prophet R7 Wave A, slice A2: save truth.

R7 §6.4/§10/§13 and masterplan §13 rows 10-12: a save must say what the account
actually answered, never repeat itself, never claim "saved" without reading the
list back, and history must stay dated (When you saved beside Tonight). This
suite pins the three shipped pieces against the REAL modules, not source text:

  1. watchstore.js `symbols.saveChecked` — check-first idempotence (a re-save is
     a no-op for tickers already on the server), read-back authority for 'saved',
     deadline honesty for 'uncertain', zero writes when signed out, and the
     frozen "When you saved" snapshot (written only for read-back-confirmed
     tickers, never overwritten, storage failures survived).
  2. watchlist.js `paintSaveOutcome` — the R7-21 rows land byte-for-byte in the
     polite region (waiting/saved/uncertain) and the assertive region (rejected),
     both locales, with the read-back / asked time in ET.
  3. the Watchlists dense table's "When you saved" / "Tonight" columns — headers
     in both locales, the snapshot cell and its absence, Tonight reusing the
     existing state vocabulary, and the no-buy-glyph guard on Unavailable.

Node-shelled exactly like tests/test_watchstore_multilist_js.py /
test_watchlist_books_js.py: browser IIFEs behind minimal window/document/
localStorage stubs (readyState 'loading' so init never runs), a recording
Supabase double that models the two tables as row arrays, and subprocess ONLY
for node.

LOAD CLOSURE (every repo file this suite opens, reads or executes):
  templates/watchstore.js   (node require)
  templates/watchlist.js    (node require)
  templates/watchlist.html.j2 (Path.read_text — asserted as text, never rendered)
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

HAS_NODE = shutil.which("node") is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node not on PATH")

ROOT = Path(__file__).resolve().parents[1]
WATCHSTORE = ROOT / "templates" / "watchstore.js"
WATCHLIST = ROOT / "templates" / "watchlist.js"
TEMPLATE = ROOT / "templates" / "watchlist.html.j2"

USER = {"id": "u1"}
LIST_ROW = {"id": "L1", "user_id": "u1", "name": "October watch", "position": 0}

# A read-back time whose America/New_York rendering is fixed: 2026-10-21T01:42Z
# is 21:42 on Oct 20 EDT (UTC-4; DST ends Nov 2, 2026), so every ET assertion
# below is deterministic regardless of the host timezone.
READ_BACK_AT = "2026-10-21T01:42:00.000Z"

SHIM = """
var __sets = [];
var __store = {};
global.localStorage = {
  getItem: function (k) {
    return Object.prototype.hasOwnProperty.call(__store, k) ? __store[k] : null;
  },
  setItem: function (k, v) { __sets.push(k); __store[k] = String(v); },
  removeItem: function (k) { delete __store[k]; },
  get length() { return Object.keys(__store).length; },
  key: function (i) { return Object.keys(__store)[i] === undefined ? null : Object.keys(__store)[i]; }
};
global.CustomEvent = function (t, o) { this.type = t; this.detail = o && o.detail; };
var __docListeners = {};
var __winListeners = {};
// DOM-node factory with real innerHTML/attribute capture (the shape the
// workspace suite uses), plus a focus recorder for the returnFocus check.
var __nodes = {};
function node(id) {
  if (!__nodes[id]) __nodes[id] = {
    id: id, innerHTML: '', textContent: '', value: '', style: {}, className: '',
    _attrs: {}, focused: 0,
    classList: { contains: function () { return false; }, toggle: function () {},
                 add: function () {}, remove: function () {} },
    setAttribute: function (k, v) { this._attrs[k] = v; },
    getAttribute: function (k) { return this._attrs[k] != null ? this._attrs[k] : null; },
    querySelector: function () { return null; },
    querySelectorAll: function () { return []; },
    addEventListener: function () {},
    focus: function () { this.focused++; }
  };
  return __nodes[id];
}
global.document = {
  readyState: 'loading',
  documentElement: {
    getAttribute: function () { return 'en'; },
    setAttribute: function () {},
    classList: { add: function () {}, remove: function () {} }
  },
  getElementById: function (id) { return node(id); },
  querySelector: function () { return null; },
  querySelectorAll: function () { return []; },
  addEventListener: function (type, handler) {
    __docListeners[type] = (__docListeners[type] || []).concat([handler]);
  },
  removeEventListener: function (type, handler) {
    if (!__docListeners[type]) return;
    __docListeners[type] = __docListeners[type].filter(function (h) { return h !== handler; });
  },
  dispatchEvent: function (e) {
    var list = __docListeners[e && e.type] || [];
    list.forEach(function (h) { h(e); });
    return true;
  },
  createElement: function () { return { style: {}, classList: { add: function () {} } }; }
};
global.window = global;
global.window.addEventListener = function (type, handler) {
  __winListeners[type] = (__winListeners[type] || []).concat([handler]);
};
global.window.removeEventListener = function (type, handler) {
  if (!__winListeners[type]) return;
  __winListeners[type] = __winListeners[type].filter(function (h) { return h !== handler; });
};
global.window.dispatchEvent = function (e) {
  var list = __winListeners[e && e.type] || [];
  list.forEach(function (h) { h(e); });
  return true;
};
global.location = { hash: '', pathname: '/watchlist.html', search: '', origin: 'https://x' };
function OUT(o) { process.stdout.write(JSON.stringify(o)); }
function wait(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
"""

# Recording Supabase double, same shape as tests/test_watchstore_multilist_js.py:
# the two tables as real row arrays, the query builder replayed, every call
# logged in db.ops so assertions can be about the SHAPE of the exchange.
FAKE_DB = """
function makeDb(seed) {
  var db = {
    tables: {
      watchlists: (seed && seed.watchlists || []).slice(),
      watchlist_symbols: (seed && seed.watchlist_symbols || []).slice()
    },
    ops: [],
    seq: 0
  };
  function matches(row, filters) {
    return filters.every(function (f) {
      if (f.op === 'eq') return String(row[f.col]) === String(f.val);
      if (f.op === 'in') return f.val.map(String).indexOf(String(row[f.col])) >= 0;
      return true;
    });
  }
  db.client = {
    from: function (table) {
      var filters = [];
      var op = { table: table, filters: filters };
      var sorts = [];
      var api = {
        eq: function (c, v) { filters.push({ op: 'eq', col: c, val: v }); return api; },
        in: function (c, v) { filters.push({ op: 'in', col: c, val: v }); return api; },
        limit: function (n) { api.__limit = n; return api; },
        order: function (col, opts) {
          sorts.push({ col: col, asc: !(opts && opts.ascending === false) });
          return api;
        },
        single: function () { api.__single = true; return api; },
        select: function (cols) {
          if (op.kind === 'insert' || op.kind === 'update') { op.returning = cols; return api; }
          op.kind = 'select'; db.ops.push(op);
          return api;
        },
        insert: function (rows) {
          op.kind = 'insert';
          op.rows = Array.isArray(rows) ? rows : [rows];
          db.ops.push(op);
          var inserted = op.rows.map(function (r) {
            var row = {};
            Object.keys(r).forEach(function (k) { row[k] = r[k]; });
            if (!row.id) row.id = table + '-' + (++db.seq);
            if (!row.created_at) row.created_at = '2026-10-20T00:00:0' + (db.seq % 10) + '.000Z';
            return row;
          });
          inserted.forEach(function (r) { db.tables[table].push(r); });
          op.inserted = inserted;
          return api;
        },
        update: function (patch) { op.kind = 'update'; op.patch = patch; db.ops.push(op); return api; },
        delete: function () { op.kind = 'delete'; db.ops.push(op); return api; },
        then: function (res, rej) { return api.__run().then(res, rej); },
        catch: function (f) { return api.__run().catch(f); },
        __run: function () {
          if (api.__ran) return api.__ran;
          api.__ran = Promise.resolve().then(function () {
            var rows = db.tables[table];
            if (op.kind === 'select') {
              var hit = rows.filter(function (r) { return matches(r, filters); });
              sorts.slice().reverse().forEach(function (s) {
                hit.sort(function (a, b) {
                  var x = a[s.col], y = b[s.col];
                  if (x === y) return 0;
                  if (x === undefined || x === null) return 1;
                  if (y === undefined || y === null) return -1;
                  return (x < y ? -1 : 1) * (s.asc ? 1 : -1);
                });
              });
              if (api.__limit !== undefined) hit = hit.slice(0, api.__limit);
              return { data: api.__single ? (hit[0] || null) : hit, error: null };
            }
            if (op.kind === 'insert') return { data: op.inserted, error: null };
            if (op.kind === 'delete') {
              var kept = [], gone = [];
              rows.forEach(function (r) { (matches(r, filters) ? gone : kept).push(r); });
              db.tables[table] = kept;
              return { data: gone, error: null };
            }
            return { data: [], error: null };
          });
          return api.__ran;
        }
      };
      return api;
    }
  };
  return db;
}
function insertedSymbols(db, listId) {
  return db.ops.filter(function (o) {
    return o.kind === 'insert' && o.table === 'watchlist_symbols' &&
           String(o.rows[0].watchlist_id) === String(listId);
  }).map(function (o) { return o.rows[0].symbol; });
}
"""


def _run(js_body: str, extra: dict | None = None) -> dict:
    globs = "\n".join("var %s = %s;" % (k, json.dumps(v)) for k, v in (extra or {}).items())
    script = SHIM + "\n" + FAKE_DB + "\n" + globs + "\n" + textwrap.dedent(js_body)
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, f"node failed:\nSTDERR:\n{res.stderr}\nSTDOUT:\n{res.stdout}"
    assert res.stdout.strip(), f"no stdout; stderr:\n{res.stderr}"
    return json.loads(res.stdout)


def _ws(js_body: str, extra: dict | None = None) -> dict:
    return _run("var WS = require(%s);\n%s" % (json.dumps(str(WATCHSTORE)), js_body), extra)


def _wl(js_body: str, extra: dict | None = None) -> dict:
    return _run("var WLT = require(%s);\n%s" % (json.dumps(str(WATCHLIST)), js_body), extra)


def _seed_session(db_js: str = "db") -> str:
    return (
        "WS._setTestSession(USER, %s.client);\n"
        "WS._setTestLists({ lists: [LIST_ROW] });\n" % db_js
    )


# ===========================================================================
# 1-4. saveChecked — the four outcomes, against the recording double
# ===========================================================================
@needs_node
def test_savechecked_already_on_server_is_reported_and_never_rewritten():
    """Case 1. A ticker already on the server list lands in `already` and is
    written ZERO times; calling saveChecked twice in a row inserts each new
    ticker exactly once in total (the check-before-any-re-save law)."""
    out = _ws(
        """
        var db = makeDb({ watchlists: [LIST_ROW],
                          watchlist_symbols: [
                            { id: 's1', watchlist_id: 'L1', symbol: 'MU', position: 0 } ] });
        SESSION
        var events = [];
        document.addEventListener('ws-save-outcome', function (e) { events.push(e.detail.state); });
        WS.symbols.saveChecked('L1', ['VRT', 'ADBE', 'MU']).then(function (r1) {
          return WS.symbols.saveChecked('L1', ['VRT', 'ADBE', 'MU']).then(function (r2) {
            OUT({ r1: r1, r2: { state: r2.state, already: r2.already },
                  inserts1: insertedSymbols(db, 'L1'), events: events });
          });
        }).catch(function (e) { OUT({ ERR: String(e && e.stack || e) }); });
        """.replace("SESSION", _seed_session()),
        {"USER": USER, "LIST_ROW": LIST_ROW},
    )
    assert "ERR" not in out, out
    assert out["r1"]["state"] == "saved"
    assert out["r1"]["already"] == ["MU"]
    assert out["r1"]["names"] == ["VRT", "ADBE", "MU"]
    # first pass: exactly the two missing tickers written, MU never
    assert sorted(out["inserts1"]) == ["ADBE", "VRT"]
    # second pass: nothing new — each ticker inserted exactly once in total;
    # `already` preserves request order
    assert out["r2"]["state"] == "saved"
    assert out["r2"]["already"] == ["VRT", "ADBE", "MU"]
    assert out["events"] == ["waiting", "saved", "waiting", "saved"]


@needs_node
def test_savechecked_saved_requires_a_read_back_after_the_insert():
    """Case 2. Happy path: state 'saved' carries an ISO readBackAt, and the
    read-back read happens AFTER the insert (never a 'saved' on the write's
    say-so alone)."""
    out = _ws(
        """
        var db = makeDb({ watchlists: [LIST_ROW], watchlist_symbols: [] });
        SESSION
        WS.symbols.saveChecked('L1', ['VRT']).then(function (r) {
          var symOps = db.ops.map(function (o, i) {
            return { i: i, k: o.kind, t: o.table };
          }).filter(function (o) { return o.t === 'watchlist_symbols'; });
          var insertAt = symOps.filter(function (o) { return o.k === 'insert'; })[0].i;
          var selects = symOps.filter(function (o) { return o.k === 'select'; });
          OUT({ state: r.state,
                readBackISO: /^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}/.test(r.readBackAt || ''),
                ops: symOps, insertAt: insertAt, lastSelectAt: selects[selects.length - 1].i });
        }).catch(function (e) { OUT({ ERR: String(e && e.stack || e) }); });
        """.replace("SESSION", _seed_session()),
        {"USER": USER, "LIST_ROW": LIST_ROW},
    )
    assert "ERR" not in out, out
    assert out["state"] == "saved"
    assert out["readBackISO"] is True
    kinds = [(o["k"], o["i"]) for o in out["ops"]]
    assert kinds == [("select", 0), ("insert", 1), ("select", 2)], kinds
    assert out["lastSelectAt"] > out["insertAt"]


@needs_node
def test_savechecked_deadline_is_uncertain_and_never_retries_itself():
    """Case 3. The insert exchange starts and never answers; the deadline fires;
    the outcome is 'uncertain' with askedAt, and the module never re-issues the
    insert on its own (exactly one attempt, chain aborted, read-back decides)."""
    out = _ws(
        """
        var db = makeDb({ watchlists: [LIST_ROW], watchlist_symbols: [] });
        var attempts = 0;
        var realFrom = db.client.from;
        db.client.from = function (table) {
          var api = realFrom.call(db.client, table);
          if (table !== 'watchlist_symbols') return api;
          api.insert = function (rows) {
            attempts++;                       // the exchange starts…
            return new Promise(function () {}); // …and never answers, landing nothing
          };
          return api;
        };
        SESSION
        var prev = WS._setCloudDeadlineMs(40);
        var events = [];
        document.addEventListener('ws-save-outcome', function (e) { events.push(e.detail.state); });
        WS.symbols.saveChecked('L1', ['VRT', 'ADBE']).then(function (r) {
          WS._setCloudDeadlineMs(prev);
          OUT({ state: r.state,
                askedISO: /^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}/.test(r.askedAt || ''),
                attempts: attempts, events: events,
                rows: db.tables.watchlist_symbols.length });
        }).catch(function (e) { OUT({ ERR: String(e && e.stack || e) }); });
        """.replace("SESSION", _seed_session()),
        {"USER": USER, "LIST_ROW": LIST_ROW},
    )
    assert "ERR" not in out, out
    assert out["state"] == "uncertain"
    assert out["askedISO"] is True
    assert out["attempts"] == 1, "a save must never loop or retry its own insert"
    assert out["events"] == ["waiting", "uncertain"]
    assert out["rows"] == 0


@needs_node
def test_savechecked_signed_out_is_rejected_with_zero_writes():
    """Case 4. No session: 'rejected' with the existing reason, no waiting
    event, and not a single op against the account."""
    out = _ws(
        """
        var db = makeDb({ watchlists: [LIST_ROW], watchlist_symbols: [] });
        WS._setTestSession(null, null);
        var events = [];
        document.addEventListener('ws-save-outcome', function (e) { events.push(e.detail.state); });
        WS.symbols.saveChecked('L1', ['VRT']).then(function (r) {
          OUT({ r: { state: r.state, reason: r.reason },
                ops: db.ops.length, events: events });
        }).catch(function (e) { OUT({ ERR: String(e && e.stack || e) }); });
        """,
        {"LIST_ROW": LIST_ROW},
    )
    assert "ERR" not in out, out
    assert out["r"] == {"state": "rejected", "reason": "no-session"}
    assert out["ops"] == 0
    assert out["events"] == ["rejected"]


@needs_node
def test_savechecked_unknown_list_is_rejected_without_writing():
    """The list is not one the account knows (deleted on another device): the
    account is asked once through the list index, the answer is 'rejected'
    with reason 'no-list', and nothing is written anywhere."""
    out = _ws(
        """
        var db = makeDb({ watchlists: [], watchlist_symbols: [] });
        WS._setTestSession(USER, db.client);   // no lists cached, none on the account
        WS.symbols.saveChecked('L1', ['VRT']).then(function (r) {
          OUT({ r: { state: r.state, reason: r.reason, listName: r.listName },
                writes: db.ops.filter(function (o) { return o.kind === 'insert'; }).length });
        }).catch(function (e) { OUT({ ERR: String(e && e.stack || e) }); });
        """,
        {"USER": USER},
    )
    assert "ERR" not in out, out
    assert out["r"]["state"] == "rejected"
    assert out["r"]["reason"] == "no-list"
    assert out["writes"] == 0


# ===========================================================================
# 5. outcome rendering — regions, locales, verbatim R7-21 rows
# ===========================================================================
@needs_node
def test_outcomes_render_into_their_regions_with_verbatim_copy():
    """Case 5. waiting/uncertain land in the polite region, rejected in the
    assertive region, saved carries the read-back time, EN and ZH spans are
    both present, and the copy matches the R7-21 rows byte-for-byte (curly ’)."""
    out = _wl(
        """
        var focusBack = node('ws_save_btn');
        WLT.paintSaveOutcome({ state: 'waiting', listName: 'October watch',
                               names: ['VRT', 'ADBE', 'MU'] });
        var waitingEN = node('ws_save_live').innerHTML;
        WLT.paintSaveOutcome({ state: 'waiting', listName: '十月观察',
                               names: ['VRT', 'ADBE', 'MU'] });
        var waitingZH = node('ws_save_live').innerHTML;

        WLT.paintSaveOutcome({ state: 'saved', readBackAt: READ_BACK_AT,
                               names: ['VRT', 'ADBE', 'MU'], already: ['MU'],
                               listCount: 7, decisionsKept: true,
                               listName: 'October watch', returnFocus: focusBack });
        var savedEN = node('ws_save_live').innerHTML;
        var savedFocus = focusBack.focused;
        WLT.paintSaveOutcome({ state: 'saved', readBackAt: READ_BACK_AT,
                               names: ['VRT', 'ADBE', 'MU'], already: ['MU'],
                               listCount: 7, decisionsKept: true,
                               listName: '十月观察' });
        var savedZH = node('ws_save_live').innerHTML;

        WLT.paintSaveOutcome({ state: 'saved', readBackAt: READ_BACK_AT,
                               names: ['VRT'], already: [], listCount: 4,
                               decisionsKept: false, listName: 'October watch' });
        var savedNoDec = node('ws_save_live').innerHTML;

        WLT.paintSaveOutcome({ state: 'uncertain', askedAt: READ_BACK_AT,
                               names: ['VRT'], listName: 'October watch' });
        var uncertain = node('ws_save_live').innerHTML;

        WLT.paintSaveOutcome({ state: 'rejected', reason: 'no-list',
                               listName: 'October watch', names: ['VRT', 'ADBE', 'MU'] });
        var rejectedEN = node('ws_save_alert').innerHTML;
        var liveCleared = node('ws_save_live').innerHTML;

        WLT.paintSaveOutcome({ state: 'rejected', reason: 'no-list',
                               listName: '十月观察', names: ['VRT', 'ADBE', 'MU'] });
        var rejectedZH = node('ws_save_alert').innerHTML;

        WLT.paintSaveOutcome({ state: 'waiting', listName: 'October watch', names: ['VRT'] });
        var alertRetired = node('ws_save_alert').innerHTML;

        function scan(s) {
          s = s.toLowerCase();
          return ['risk', 'p&l', 'holding', 'position'].filter(function (w) {
            return s.indexOf(w) >= 0;
          });
        }
        OUT({ waitingEN: waitingEN, waitingZH: waitingZH,
              savedEN: savedEN, savedZH: savedZH, savedFocus: savedFocus,
              savedNoDec: savedNoDec, uncertain: uncertain,
              rejectedEN: rejectedEN, rejectedZH: rejectedZH,
              liveCleared: liveCleared, alertRetired: alertRetired,
              banned: [].concat(scan(waitingEN), scan(savedEN), scan(savedNoDec),
                                scan(uncertain), scan(rejectedEN)) });
        """,
        {"READ_BACK_AT": READ_BACK_AT},
    )
    # waiting — polite region, both locales, R7-21 rows verbatim
    assert "Saving to October watch" in out["waitingEN"]
    assert "正在保存到十月观察" in out["waitingZH"]
    assert ("Waiting for your account to confirm. You can close this; the save "
            "carries on, and nothing is saved twice.") in out["waitingEN"]
    assert "正在等待您的账户确认。您可以关闭此面板；保存会继续进行，不会重复保存。" in out["waitingZH"]
    assert out["waitingEN"].count('class="l-en"') >= 2
    assert out["waitingEN"].count('class="l-zh"') >= 2
    # saved — read-back time in ET, names listed, decisions clause only when supplied
    saved = out["savedEN"]
    assert "Saved to October watch" in saved
    assert "已保存到十月观察" in out["savedZH"]
    assert ("Read back from your account at 21:42 ET. VRT, ADBE and MU are in "
            "the list with tonight’s decisions kept as they stand.") in saved
    assert ("21:42（美东）从您的账户读回。VRT、ADBE 和 MU 已在列表中，"
            "今晚的决策按原样保留。") in out["savedZH"]
    # already-in-it line (R7-20 row) with the list's own name count
    assert "7 names, MU is already in it" in saved
    assert "7 只，MU 已在其中" in out["savedZH"]
    # no decisions supplied -> the sentence ends after "are in the list."
    assert "VRT is in the list." in out["savedNoDec"]
    assert "VRT 已在列表中。" in out["savedNoDec"]
    assert "decisions kept" not in out["savedNoDec"]
    # uncertain — polite region, its body row, the asked time
    unc = out["uncertain"]
    assert "Save not confirmed yet" in unc and "保存尚未确认" in unc
    assert ("Your account didn’t answer in time. Before saving again we check "
            "the list, so nothing is saved twice.") in unc
    assert "您的账户未及时应答。再次保存前我们会先检查列表，因此不会重复保存。" in unc
    assert "Asked at 21:42 ET" in unc and "请求于 21:42（美东）" in unc
    # rejected — assertive region, R7-21 rows verbatim, live region retired
    rej = out["rejectedEN"]
    assert "Not saved" in rej and "未保存" in rej
    assert ("Your account says October watch was deleted on another device. "
            "Choose another list for VRT, ADBE and MU.") in rej
    assert ("您的账户显示“十月观察”已在另一台设备上删除。"
            "请为 VRT、ADBE 和 MU 选择其他列表。") in out["rejectedZH"]
    assert "Nothing was added anywhere." in rej and "没有添加到任何列表。" in rej
    assert out["liveCleared"] == "", "a rejected save must retire the waiting line"
    assert out["alertRetired"] == "", "a new attempt must retire the last verdict"
    # focus goes back to the invoking control once the account has answered
    assert out["savedFocus"] == 1
    # no outcome is called a failure, and no risk/position vocabulary appears
    assert out["banned"] == []


# ===========================================================================
# 4b. lost responses vs refusals — the account's answer, never the transport's
# ===========================================================================
LOST_RESPONSE = {   # postgrest-js resolves a dropped exchange like this (status 0)
    "status": 0,
    "error": {"message": "TypeError: Failed to fetch", "details": "", "hint": "", "code": ""},
}
GATEWAY_5XX = {     # a gateway/pool failure: 5xx even when a PostgREST code rides along
    "status": 503,
    "error": {"message": "Database client error. Retrying the connection.",
              "details": None, "hint": None, "code": "PGRST000"},
}
ACCOUNT_REFUSAL = {  # the account answering no: RLS refusal, 403 + Postgres code
    "status": 403,
    "error": {"message": 'new row violates row-level security policy for table "watchlist_symbols"',
              "details": None, "hint": None, "code": "42501"},
}

# The insert override every case below shares: the exchange is attempted, the
# row optionally lands, and the answer is the given postgrest-js response.
_INSERT_ANSWERS = """
var attempts = 0;
var realFrom = db.client.from;
db.client.from = function (table) {
  var api = realFrom.call(db.client, table);
  if (table !== 'watchlist_symbols') return api;
  api.insert = function (rows) {
    attempts++;
    var r = Array.isArray(rows) ? rows[0] : rows;
    if (LANDS) db.tables.watchlist_symbols.push({ id: 'x' + attempts, watchlist_id: r.watchlist_id,
                                                  symbol: r.symbol, position: r.position });
    return Promise.resolve({ data: null, status: ANSWER.status, statusText: '',
                             error: ANSWER.error });
  };
  return api;
};
"""


def _save_with_answer(answer: dict, lands: bool) -> dict:
    return _ws(
        """
        var db = makeDb({ watchlists: [LIST_ROW], watchlist_symbols: [] });
        INSERT_ANSWERS
        SESSION
        var events = [];
        document.addEventListener('ws-save-outcome', function (e) { events.push(e.detail.state); });
        WS.symbols.saveChecked('L1', ['VRT'],
          { decisions: { VRT: { en: 'Get ready', zh: '做好准备' } } }).then(function (r) {
          OUT({ state: r.state, reason: r.reason || null, decisionsKept: r.decisionsKept,
                attempts: attempts, events: events,
                rows: db.tables.watchlist_symbols.length,
                selects: db.ops.filter(function (o) {
                  return o.table === 'watchlist_symbols' && o.kind === 'select'; }).length,
                snap: JSON.parse(localStorage.getItem('mdash.watchlist.saved_snap.v1') || 'null') });
        }).catch(function (e) { OUT({ ERR: String(e && e.stack || e) }); });
        """.replace("INSERT_ANSWERS", _INSERT_ANSWERS).replace("SESSION", _seed_session()),
        {"USER": USER, "LIST_ROW": LIST_ROW, "ANSWER": answer, "LANDS": lands},
    )


@needs_node
def test_p1_row_committed_but_response_lost_reads_back_saved():
    """P1. The insert committed on the server but the response was lost
    (postgrest-js: status 0, 'TypeError: Failed to fetch', code ''). That is NOT
    the account refusing: the list is read back once, the row is there, so the
    honest outcome is 'saved' — never 'rejected' with the row on the server."""
    out = _save_with_answer(LOST_RESPONSE, lands=True)
    assert "ERR" not in out, out
    assert out["state"] == "saved", out
    assert out["attempts"] == 1 and out["rows"] == 1
    assert out["selects"] == 2, "check-first read + exactly one read-back"
    assert out["events"] == ["waiting", "saved"]
    assert out["decisionsKept"] is True
    assert out["snap"]["L1"]["VRT"]["en"] == "Get ready"


@needs_node
@pytest.mark.parametrize("answer", [LOST_RESPONSE, GATEWAY_5XX], ids=["status0-lost", "gateway-503"])
def test_p1b_ambiguous_failure_with_nothing_landed_is_uncertain_never_rejected(answer):
    """P1b. Lost response (status 0) or a gateway 5xx, and the read-back does
    NOT find the row: 'uncertain' (we could not hear the answer), never
    'rejected', and no snapshot is frozen."""
    out = _save_with_answer(answer, lands=False)
    assert "ERR" not in out, out
    assert out["state"] == "uncertain", out
    assert out["attempts"] == 1 and out["rows"] == 0
    assert out["selects"] == 2, "an ambiguous failure is always read back once"
    assert out["events"] == ["waiting", "uncertain"]
    assert out["snap"] is None


@needs_node
def test_account_refusal_with_nothing_landed_is_rejected_without_read_back():
    """The account really answered no (403 + Postgres code 42501) and nothing
    landed: 'rejected' with the account's own message, no read-back."""
    out = _save_with_answer(ACCOUNT_REFUSAL, lands=False)
    assert "ERR" not in out, out
    assert out["state"] == "rejected", out
    assert "row-level security" in out["reason"]
    assert out["attempts"] == 1 and out["rows"] == 0
    assert out["selects"] == 1, "a refusal is an answer; nothing to read back"
    assert out["events"] == ["waiting", "rejected"]
    assert out["snap"] is None


@needs_node
def test_p2_rejected_late_insert_is_never_reinserted_by_the_outbox():
    """P2. The insert outlives the deadline, then its promise REJECTS after the
    row has landed (a transport failure on the way back). The browser is online
    and fires `online`: the sync outbox must not re-insert the checked ticker —
    exactly one row, exactly one insert attempt."""
    out = _ws(
        """
        var db = makeDb({ watchlists: [LIST_ROW], watchlist_symbols: [] });
        var attempts = 0;
        var realFrom = db.client.from;
        db.client.from = function (table) {
          var api = realFrom.call(db.client, table);
          if (table !== 'watchlist_symbols') return api;
          var realInsert = api.insert;
          api.insert = function (rows) {
            attempts++;
            if (attempts > 1) return realInsert.call(api, rows);   // any re-insert lands for real
            var r = Array.isArray(rows) ? rows[0] : rows;
            return new Promise(function (resolve, reject) {
              setTimeout(function () {
                db.tables.watchlist_symbols.push({ id: 'late1', watchlist_id: r.watchlist_id,
                                                   symbol: r.symbol, position: r.position });
                reject(new TypeError('Failed to fetch'));
              }, 120);
            });
          };
          return api;
        };
        SESSION
        global.navigator = { onLine: true };
        var prev = WS._setCloudDeadlineMs(40);
        WS.symbols.saveChecked('L1', ['VRT']).then(function (r) {
          WS._setCloudDeadlineMs(prev);
          return wait(200).then(function () {
            window.dispatchEvent({ type: 'online' });
            return wait(250);
          }).then(function () {
            OUT({ state: r.state, attempts: attempts,
                  vrtRows: db.tables.watchlist_symbols.filter(function (x) {
                    return x.symbol === 'VRT'; }).length });
          });
        }).catch(function (e) { OUT({ ERR: String(e && e.stack || e) }); });
        """.replace("SESSION", _seed_session()),
        {"USER": USER, "LIST_ROW": LIST_ROW},
    )
    assert "ERR" not in out, out
    assert out["state"] == "uncertain"
    assert out["attempts"] == 1, "the outbox re-inserted a checked save"
    assert out["vrtRows"] == 1


@needs_node
def test_snapshot_only_for_tickers_this_save_inserted():
    """Snapshot scope. A ticker already on the server keeps whatever snapshot
    it had — none stays none — because today's date and decision are not when
    it was saved; `decisionsKept` is true only if a decision was really stored."""
    out = _ws(
        """
        var db = makeDb({ watchlists: [LIST_ROW],
                          watchlist_symbols: [ { id: 's1', watchlist_id: 'L1', symbol: 'MU', position: 0 } ] });
        SESSION
        var dec = { VRT: { en: 'Get ready', zh: '做好准备' }, MU: { en: 'No entry signal yet', zh: '尚无入场信号' } };
        WS.symbols.saveChecked('L1', ['VRT', 'MU'], { decisions: dec }).then(function (r1) {
          var snap1 = JSON.parse(localStorage.getItem('mdash.watchlist.saved_snap.v1') || '{}');
          return WS.symbols.saveChecked('L1', ['MU'], { decisions: dec }).then(function (r2) {
            OUT({ s1: r1.state, already1: r1.already, k1: r1.decisionsKept, snap1: snap1,
                  s2: r2.state, k2: r2.decisionsKept,
                  snap2: JSON.parse(localStorage.getItem('mdash.watchlist.saved_snap.v1') || '{}') });
          });
        }).catch(function (e) { OUT({ ERR: String(e && e.stack || e) }); });
        """.replace("SESSION", _seed_session()),
        {"USER": USER, "LIST_ROW": LIST_ROW},
    )
    assert "ERR" not in out, out
    assert out["s1"] == "saved" and out["already1"] == ["MU"]
    assert sorted(out["snap1"]["L1"].keys()) == ["VRT"], "MU was already there — no snapshot"
    assert out["k1"] is True
    assert out["s2"] == "saved"
    assert out["k2"] is False, "nothing inserted, nothing kept"
    assert "MU" not in out["snap2"]["L1"]


# ===========================================================================
# 6. the "When you saved" snapshot — confirmed-only, frozen, storage-safe
# ===========================================================================
@needs_node
def test_snapshot_written_only_for_confirmed_and_never_overwritten():
    """Case 6. Snapshots exist only for tickers this save inserted and the
    read-back confirmed, are never overwritten for the same list+ticker (frozen
    history), and a save that cannot confirm writes none at all. VRT is removed
    server-side between the two saves, so the second save really inserts it
    again — and still may not overwrite the first snapshot."""
    out = _ws(
        """
        var db = makeDb({ watchlists: [LIST_ROW], watchlist_symbols: [] });
        SESSION
        var dec = { VRT: { en: 'Not there yet, get ready', zh: '尚未触发，做好准备' },
                    MU:  { en: 'No entry signal yet', zh: '尚无入场信号' } };
        WS.symbols.saveChecked('L1', ['VRT', 'MU'], { decisions: dec }).then(function (r1) {
          // VRT leaves the list elsewhere, then is saved again with DIFFERENT copy
          db.tables.watchlist_symbols = db.tables.watchlist_symbols.filter(function (r) {
            return r.symbol !== 'VRT';
          });
          var dec2 = { VRT: { en: 'CHANGED', zh: '改了' } };
          return WS.symbols.saveChecked('L1', ['VRT'], { decisions: dec2 }).then(function (r2) {
            OUT({ s1: r1.state, s2: r2.state, k1: r1.decisionsKept, k2: r2.decisionsKept,
                  inserts: insertedSymbols(db, 'L1'),
                  snap: JSON.parse(localStorage.getItem('mdash.watchlist.saved_snap.v1') || '{}') });
          });
        }).catch(function (e) { OUT({ ERR: String(e && e.stack || e) }); });
        """.replace("SESSION", _seed_session()),
        {"USER": USER, "LIST_ROW": LIST_ROW},
    )
    assert "ERR" not in out, out
    assert out["s1"] == "saved" and out["s2"] == "saved"
    assert sorted(out["inserts"]) == ["MU", "VRT", "VRT"]   # VRT really re-inserted
    assert out["k1"] is True
    assert out["k2"] is False, "a frozen snapshot is not a decision kept by this save"
    snap = out["snap"]["L1"]
    assert sorted(snap.keys()) == ["MU", "VRT"]
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", snap["VRT"]["d"])
    assert snap["VRT"]["en"] == "Not there yet, get ready"     # NOT 'CHANGED'
    assert snap["VRT"]["zh"] == "尚未触发，做好准备"
    assert snap["MU"]["en"] == "No entry signal yet"


@needs_node
def test_snapshot_is_not_written_when_the_save_cannot_confirm():
    out = _ws(
        """
        var db = makeDb({ watchlists: [LIST_ROW], watchlist_symbols: [] });
        var realFrom = db.client.from;
        db.client.from = function (table) {
          var api = realFrom.call(db.client, table);
          if (table !== 'watchlist_symbols') return api;
          api.insert = function () { return new Promise(function () {}); };
          return api;
        };
        SESSION
        var prev = WS._setCloudDeadlineMs(40);
        WS.symbols.saveChecked('L1', ['VRT'],
          { decisions: { VRT: { en: 'x', zh: 'x' } } }).then(function (r) {
          WS._setCloudDeadlineMs(prev);
          OUT({ state: r.state,
                snap: localStorage.getItem('mdash.watchlist.saved_snap.v1') });
        }).catch(function (e) { OUT({ ERR: String(e && e.stack || e) }); });
        """.replace("SESSION", _seed_session()),
        {"USER": USER, "LIST_ROW": LIST_ROW},
    )
    assert "ERR" not in out, out
    assert out["state"] == "uncertain"
    assert out["snap"] is None, "an unconfirmed save must freeze no history"


@needs_node
def test_snapshot_storage_failures_never_crash_the_save():
    out = _ws(
        """
        var db = makeDb({ watchlists: [LIST_ROW], watchlist_symbols: [] });
        SESSION
        var realSet = localStorage.setItem;
        localStorage.setItem = function (k, v) {
          if (k === 'mdash.watchlist.saved_snap.v1') throw new Error('quota');
          return realSet.call(localStorage, k, v);
        };
        var snap = WS.symbols.saveChecked('L1', ['VRT'],
          { decisions: { VRT: { en: 'x', zh: 'x' } } });
        var realGet = localStorage.getItem;
        localStorage.setItem = realSet;
        localStorage.getItem = function (k) {
          if (k === 'mdash.watchlist.saved_snap.v1') throw new Error('denied');
          return realGet.call(localStorage, k);
        };
        var snapReadFail = WS.symbols.saveChecked('L1', ['ADBE'],
          { decisions: { ADBE: { en: 'y', zh: 'y' } } });
        Promise.all([snap, snapReadFail]).then(function (rs) {
          OUT({ states: rs.map(function (r) { return r.state; }) });
        }).catch(function (e) { OUT({ ERR: String(e && e.stack || e) }); });
        """.replace("SESSION", _seed_session()),
        {"USER": USER, "LIST_ROW": LIST_ROW},
    )
    assert "ERR" not in out, out
    assert out["states"] == ["saved", "saved"]


# ===========================================================================
# 7. "When you saved" / "Tonight" — the Watchlists dense table only
# ===========================================================================
@needs_node
def test_when_you_saved_and_tonight_columns_render_in_watchlists_mode():
    """Case 7. Headers ship in both locales; a snapshot renders its decision
    plus the dated "Saved <Mon D>" line; no snapshot renders Not supplied;
    the footnote row states the nightly-redraw contract."""
    out = _wl(
        """
        localStorage.setItem('mdash.wl.L1.v1', JSON.stringify({
          v: 1, updated: '2026-10-20T00:00:00.000Z',
          items: [ { t: 'VRT', added: '2026-10-01T00:00:00.000Z', note: '' },
                   { t: 'MU',  added: '2026-10-01T00:00:00.000Z', note: '' } ],
          order: ['VRT', 'MU'], settings: {} }));
        localStorage.setItem('mdash.watchlist.saved_snap.v1', JSON.stringify(
          { L1: { VRT: { d: '2026-10-06', en: 'Not there yet, get ready', zh: '尚未触发，做好准备' } } }));
        WLT.setMode('watchlists', false);
        window.WL.bindList('L1', 'October watch');
        var html = node('tbl_wl').innerHTML;
        // Watchlists mode only: switching to Portfolio paints no watchlist head
        node('tbl_wl').innerHTML = '';
        WLT.setMode('portfolio', false);
        var afterPortfolio = node('tbl_wl').innerHTML;
        OUT({ html: html, afterPortfolio: afterPortfolio });
        """
    )
    html = out["html"]
    assert "<span class=\"l-en\">When you saved</span><span class=\"l-zh\">保存时</span>" in html
    assert "<span class=\"l-en\">Tonight</span><span class=\"l-zh\">今晚</span>" in html
    # every pre-existing column keeps its header
    for h in ("Symbol", "Last / day", "Signal", "Risk flags", "Next event",
              "Sector / theme", "Since your last visit"):
        assert h in html, h
    # the snapshot cell: decision + dated line (R7-19 rows)
    assert "Not there yet, get ready" in html and "尚未触发，做好准备" in html
    assert "Saved Oct 6" in html and "10月6日保存" in html
    # no snapshot: Not supplied, both locales
    assert "Not supplied" in html and "未提供" in html
    # the footnote row, verbatim, spanning the table
    assert ("Tonight’s decisions are redrawn nightly. What you saved stays as it "
            "was when you saved it.") in html
    assert "今晚的决策每晚重绘。您保存的内容保持保存时的样子。" in html
    assert 'colspan="10"' in html
    # Portfolio mode never receives the columns
    assert out["afterPortfolio"] == ""


@needs_node
def test_tonight_uses_the_existing_state_vocabulary_and_unavailable_carries_no_buy():
    """Guard 4. Tonight's cell is the row's EXISTING state label — no new
    vocabulary — and an Unavailable cell (no current state) carries no stage
    class and no glyph, so it can never read as a buy-type stage."""
    out = _wl(
        """
        var fresh = WLT.rowHTML({ t: 'VRT', n: 'Vertiv', s: 'Tech', st: 'FRESH BUY' });
        var top = WLT.rowHTML({ t: 'ADBE', n: 'Adobe', s: 'Tech', st: 'TOP WATCH' });
        var none = WLT.rowHTML({ t: 'MU', n: 'Micron', s: 'Tech', st: null });
        function ton(html) {
          var m = /<td class="c-ton">([\\s\\S]*?)<\\/td>/.exec(html);
          return m ? m[1] : null;
        }
        OUT({ fresh: ton(fresh), top: ton(top), none: ton(none) });
        """
    )
    assert out["fresh"] is not None and out["none"] is not None
    # existing vocabulary, drawn by the existing stageCell — nothing new minted
    assert 'class="stg s-confirmed"' in out["fresh"]
    assert "<span class=\"l-en\">Confirmed</span>" in out["fresh"]
    assert 'class="stg s-extended"' in out["top"]
    # Unavailable: plain muted text, no stage class, no glyph
    assert "Unavailable" in out["none"] and "暂不可用" in out["none"]
    assert "stg" not in out["none"], out["none"]
    assert "<i>" not in out["none"], out["none"]
    assert "s-confirmed" not in out["none"] and "s-early" not in out["none"]


@needs_node
def test_stale_quote_row_never_renders_buy():
    """Guard 5. A row whose quote is stale must not render a buy-type Tonight
    state. DOCUMENTED GAP: this renderer's row data carries NO per-row quote
    staleness flag — DETAIL[t].tech has only `price_asof` (a date,
    scripts/build_stock_library.py `_bind_price_clock`) and nothing on this
    page computes staleness from it — so there is no honest way to stage a
    stale-quote row. Inventing a flag here would be an invented signal; the
    guard is reported to the commissioning packet instead."""
    pytest.skip(
        "GAP: no per-row quote staleness flag exists in the Watchlists dense "
        "table's data (templates/watchlist.js wlRowHTML/DETAIL; the per-stock "
        "JSON carries only tech.price_asof, a date) — guard 5 has no input to "
        "consume and inventing one is out of scope for this wave"
    )


# ===========================================================================
# 8. the template — regions, the OQ8 ink fix, neutral CSS, clean copy
# ===========================================================================
def test_template_carries_the_two_live_regions_once_each():
    page = TEMPLATE.read_text(encoding="utf-8")
    live = re.findall(r'<div id="ws_save_live"[^>]*>', page)
    alert = re.findall(r'<div id="ws_save_alert"[^>]*>', page)
    assert len(live) == 1, live
    assert len(alert) == 1, alert
    assert 'role="status"' in live[0] and 'aria-live="polite"' in live[0]
    assert 'role="alert"' in alert[0]
    # directly after the save chip, inside the same header block
    chip = page.index('id="ws_savechip"')
    assert chip < page.index('id="ws_save_live"') < page.index('id="ws_save_alert"')


def test_oq8_watch_state_paints_from_ink_warn_with_fallback():
    page = TEMPLATE.read_text(encoding="utf-8")
    assert ".wri-lrow .st.watch { color:var(--ink-warn, var(--warn)); }" in page


def test_new_css_is_neutral_no_colored_edge_of_any_kind():
    """The chairman design rule: no colored left edge or equivalent accent
    stripe — asserted on every rule this wave adds to the page's <style>."""
    page = TEMPLATE.read_text(encoding="utf-8")
    selectors = ("ws-save-live", "ws-save-alert", "wl-night-foot", "c-wsv",
                 "c-ton", "ton-na", "wsv-dec", "wsv-d", "so-t")
    rules = re.findall(r"([^{}]+)\{([^{}]*)\}", page)
    touched = [(sel.strip(), body) for sel, body in rules
               if any((".%s" % s) in sel or ("#%s" % s) in sel for s in selectors)]
    assert touched, "the new rules moved — update the selector list"
    for sel, body in touched:
        assert "border-left" not in body, (sel, body)
        assert "border-inline-start" not in body, (sel, body)
        assert "inset" not in body, (sel, body)


def test_new_copy_stays_off_risk_and_position_vocabulary():
    """The only permitted 'position' occurrences anywhere are the two R7
    disclaimers — which this wave does not ship — so the template's new
    markup/CSS carries none of the forbidden vocabulary at all."""
    page = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(
        r'id="ws_savechip".*?(<div id="ws_save_live".*?</div>\s*'
        r'<div id="ws_save_alert".*?</div>)', page, re.S)
    assert m, "the live-region block moved"
    block = m.group(1).lower()
    for word in ("risk", "p&l", "holding", "position", "仓位"):
        assert word not in block, word


def test_suite_never_walks_the_filesystem():
    """The commissioning fence: node subprocesses only, fixed paths only — no
    directory enumeration of any kind in this suite. The banned tokens are
    concatenated so this guard does not contain itself."""
    src = Path(__file__).read_text(encoding="utf-8")
    banned = ["gl" + "ob(", "os.wa" + "lk", "list" + "dir", "scan" + "dir",
              "iter" + "dir", "r" + "glob"]
    for token in banned:
        assert token not in src, token
