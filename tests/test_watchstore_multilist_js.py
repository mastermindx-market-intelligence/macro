"""tests/test_watchstore_multilist_js.py — the registered multi-list store seam (W1a).

`templates/watchstore.js` used to hold ONE implicit target: a single `wlId` resolved by
"whichever list sorts first" plus a single global `cloudSet`. Under multi-list that shape
is a data-loss machine, because the push is a FULL-MEMBERSHIP diff — it deletes cloud rows
that are absent locally. This file pins the properties that make it safe:

  1. List CRUD is isolated: symbol ops name their list, and an op on list A leaves list B
     byte-identical.
  2. The one-shot local->cloud fold retargets to the list NAMED 'Watchlist' (created if
     absent), and running it twice yields identical state — the marker is written only on
     success and never on an empty local book (both shipped behaviours kept).
  3. NAMED REGRESSION: with two lists, a stale cache of list A can never delete rows of
     list B. Every delete is scoped by `.eq('watchlist_id', <list being pushed>)` and its
     candidate symbols come only from that list's SERVER read — a localStorage cache is a
     render hint, never a delete authority.
  4. The four semantic invariants A-D from the commissioning packet's §0, run against the
     store layer: watchlist writes never touch `portfolio_positions` and vice versa.

Same harness as tests/test_watchlist_books_js.py: the module is a browser IIFE, node-shelled
behind minimal window/document/localStorage stubs with readyState 'loading' so init() never
runs and only the store logic is exercised.
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
WATCHSTORE = ROOT / "templates" / "watchstore.js"
WATCHLIST = ROOT / "templates" / "watchlist.js"

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
// D05 W1-honesty tests need (a) a spyable `document.dispatchEvent` so the chip dispatch
// can be observed, and (b) a real `window.addEventListener` so the `online` event
// path can be exercised end to end. Both are pure additions — they record into a
// registry instead of dropping on the floor — and existing tests that don't listen
// are unaffected.
var __docListeners = {};
var __winListeners = {};
global.document = {
  readyState: 'loading',
  documentElement: {
    getAttribute: function () { return 'en'; },
    classList: { add: function () {}, remove: function () {} }
  },
  getElementById: function () { return null; },
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

# ---------------------------------------------------------------------------
# A recording Supabase double.
#
# It models the two tables as real row arrays and REPLAYS the query builder, so a
# delete that forgets its watchlist_id filter genuinely removes the other list's rows
# instead of being caught by an assertion about intent. Every call is also logged in
# `db.ops` so a test can assert on the SHAPE of the statement, not just its effect.
# ---------------------------------------------------------------------------
FAKE_DB = """
function makeDb(seed, opts) {
  // `opts.ignoreOrder` drops server-side ordering, so a test can pin the CLIENT-side
  // sort that ruling R1 branch 2's determinism rests on.
  var ignoreOrder = !!(opts && opts.ignoreOrder);
  var db = {
    tables: {
      watchlists: (seed && seed.watchlists || []).slice(),
      watchlist_symbols: (seed && seed.watchlist_symbols || []).slice(),
      portfolio_positions: (seed && seed.portfolio_positions || []).slice()
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
        // PostgREST applies .order() server-side and returns rows in that order. The
        // double models it, otherwise any assertion about "the FIRST list by
        // (position, created_at)" would pass on insertion order and prove nothing.
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
            if (!row.created_at) row.created_at = '2026-08-01T00:00:0' + (db.seq % 10) + '.000Z';
            return row;
          });
          // honour the schema's unique (user_id, name) index on watchlists
          if (table === 'watchlists') {
            var clash = inserted.some(function (r) {
              return db.tables.watchlists.some(function (x) {
                return String(x.user_id) === String(r.user_id) && x.name === r.name;
              });
            });
            if (clash) { op.rejected = '23505'; return api; }
          }
          inserted.forEach(function (r) { db.tables[table].push(r); });
          op.inserted = inserted;
          return api;
        },
        update: function (patch) {
          op.kind = 'update'; op.patch = patch; db.ops.push(op); return api;
        },
        delete: function () { op.kind = 'delete'; db.ops.push(op); return api; },
        then: function (res, rej) { return api.__run().then(res, rej); },
        catch: function (f) { return api.__run().catch(f); },
        __run: function () {
          if (api.__ran) return api.__ran;
          api.__ran = Promise.resolve().then(function () {
            var rows = db.tables[table];
            if (op.kind === 'select') {
              var hit = rows.filter(function (r) { return matches(r, filters); });
              if (!ignoreOrder) sorts.slice().reverse().forEach(function (s) {
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
            if (op.kind === 'insert') {
              if (op.rejected) {
                return { data: null,
                         error: { code: '23505', message: 'duplicate key value' } };
              }
              return { data: api.__single ? op.inserted[0] : op.inserted, error: null };
            }
            if (op.kind === 'update') {
              var upd = [];
              rows.forEach(function (r) {
                if (!matches(r, filters)) return;
                Object.keys(op.patch).forEach(function (k) { r[k] = op.patch[k]; });
                upd.push(r);
              });
              op.affected = upd.length;
              return { data: api.__single ? (upd[0] || null) : upd, error: null };
            }
            if (op.kind === 'delete') {
              var kept = [], gone = [];
              rows.forEach(function (r) { (matches(r, filters) ? gone : kept).push(r); });
              db.tables[table] = kept;
              op.deleted = gone;
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
function symbolsOf(db, listId) {
  return db.tables.watchlist_symbols
    .filter(function (r) { return String(r.watchlist_id) === String(listId); })
    .map(function (r) { return r.symbol; }).sort();
}
"""

USER = {"id": "u1"}


def _run(js_body: str, extra: dict | None = None) -> dict:
    globs = "\n".join("var %s = %s;" % (k, json.dumps(v)) for k, v in (extra or {}).items())
    script = SHIM + "\n" + FAKE_DB + "\n" + globs + "\n" + textwrap.dedent(js_body)
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, f"node failed:\nSTDERR:\n{res.stderr}\nSTDOUT:\n{res.stdout}"
    assert res.stdout.strip(), f"no stdout; stderr:\n{res.stderr}"
    return json.loads(res.stdout)


def _ws(js_body: str, extra: dict | None = None) -> dict:
    return _run("var WS = require(%s);\n%s" % (json.dumps(str(WATCHSTORE)), js_body), extra)


def _wl(js_body: str, extra: dict | None = None) -> dict:
    return _run("var WLT = require(%s);\n%s" % (json.dumps(str(WATCHLIST)), js_body), extra)


# two registered lists belonging to the same owner
TWO_LISTS = {
    "watchlists": [
        {"id": "L-AI", "user_id": "u1", "name": "AI", "position": 0},
        {"id": "L-GOLD", "user_id": "u1", "name": "Gold Miners", "position": 1},
    ],
    "watchlist_symbols": [
        {"id": "s1", "watchlist_id": "L-AI", "symbol": "NVDA", "position": 0},
        {"id": "s2", "watchlist_id": "L-AI", "symbol": "AVGO", "position": 1},
        {"id": "s3", "watchlist_id": "L-GOLD", "symbol": "NEM", "position": 0},
        {"id": "s4", "watchlist_id": "L-GOLD", "symbol": "AEM", "position": 1},
    ],
}


# ===========================================================================
# 1. multi-list CRUD isolation
# ===========================================================================
@needs_node
def test_list_crud_create_rename_delete_round_trip():
    out = _ws(
        """
        var db = makeDb({watchlists: [], watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        WS.lists.create('Gold Miners').then(function (a) {
          return WS.lists.create('Space').then(function (b) {
            return WS.lists.rename(b.id, 'Space Economy').then(function (r) {
              return WS.lists.remove(a.id).then(function () {
                return WS.lists.refresh().then(function (all) {
                  OUT({created: [a.name, b.name], renamed: r.name,
                       positions: [a.position, b.position],
                       left: all.map(function (l) { return l.name; })});
                });
              });
            });
          });
        });
        """,
        {"USER": USER},
    )
    assert out["created"] == ["Gold Miners", "Space"]
    assert out["positions"] == [0, 1]          # position is assigned, not collided
    assert out["renamed"] == "Space Economy"
    assert out["left"] == ["Space Economy"]    # the deleted list is gone, the other kept


@needs_node
def test_duplicate_list_name_adopts_the_existing_row_instead_of_failing():
    """The schema carries a unique (user_id, name) index. Two tabs (or Macro and the
    Terminal) racing the same create must converge on ONE list, not blow up the caller."""
    out = _ws(
        """
        var db = makeDb({watchlists: [{id: 'L1', user_id: 'u1', name: 'AI', position: 0}]});
        WS._setTestSession(USER, db.client);
        WS.lists.create('AI').then(function (row) {
          OUT({id: row && row.id, rows: db.tables.watchlists.length});
        }, function (e) { OUT({err: String(e)}); });
        """,
        {"USER": USER},
    )
    assert out["id"] == "L1"     # adopted the existing row
    assert out["rows"] == 1      # and did NOT create a second one


@needs_node
def test_symbol_ops_are_isolated_between_lists():
    """Invariant: an add/remove on list A leaves list B byte-identical."""
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        var before = symbolsOf(db, 'L-GOLD');
        WS.symbols.list('L-AI').then(function () {
          return WS.symbols.add('L-AI', 'GOOGL').then(function () {
            return WS.symbols.remove('L-AI', 'AVGO').then(function () {
              OUT({ai: symbolsOf(db, 'L-AI'),
                   goldBefore: before, goldAfter: symbolsOf(db, 'L-GOLD')});
            });
          });
        });
        """,
        {"USER": USER, "SEED": TWO_LISTS},
    )
    assert out["ai"] == ["GOOGL", "NVDA"]
    assert out["goldAfter"] == out["goldBefore"] == ["AEM", "NEM"]


@needs_node
def test_per_list_caches_use_distinct_keys_and_do_not_bleed():
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        WS.symbols.list('L-AI').then(function () {
          return WS.symbols.list('L-GOLD').then(function () {
            OUT({keys: [WS.cacheKey('L-AI'), WS.cacheKey('L-GOLD')],
                 ai: WS.cacheRead('L-AI').order,
                 gold: WS.cacheRead('L-GOLD').order,
                 stored: Object.keys(__store).filter(function (k) {
                   return k.indexOf('mdash.wl.') === 0; }).sort()});
          });
        });
        """,
        {"USER": USER, "SEED": TWO_LISTS},
    )
    assert out["keys"] == ["mdash.wl.L-AI.v1", "mdash.wl.L-GOLD.v1"]
    assert out["ai"] == ["NVDA", "AVGO"]
    assert out["gold"] == ["NEM", "AEM"]
    assert out["stored"] == ["mdash.wl.L-AI.v1", "mdash.wl.L-GOLD.v1"]
    # the anonymous store is not one of them
    assert "mdash.watchlist.v1" not in out["stored"]


@needs_node
def test_a_cache_write_preserves_local_notes_that_the_schema_cannot_hold():
    """Notes stay local by ruling — `watchlist_symbols` has no note column. A sync must
    therefore never erase a note the user typed against a symbol that is still present."""
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        localStorage.setItem('mdash.wl.L-AI.v1', JSON.stringify({
          v: 1, updated: '2026-08-01T00:00:00.000Z',
          items: [{t: 'NVDA', added: '2026-07-01T00:00:00.000Z', note: 'core position'}],
          order: ['NVDA'], settings: {sort: 'order'}
        }));
        WS.symbols.list('L-AI').then(function () {
          var c = WS.cacheRead('L-AI');
          var nvda = c.items.filter(function (i) { return i.t === 'NVDA'; })[0];
          OUT({note: nvda && nvda.note, added: nvda && nvda.added,
               order: c.order, settings: c.settings});
        });
        """,
        {"USER": USER, "SEED": TWO_LISTS},
    )
    assert out["note"] == "core position"
    assert out["added"] == "2026-07-01T00:00:00.000Z"
    assert out["order"] == ["NVDA", "AVGO"]
    assert out["settings"] == {"sort": "order"}


# ===========================================================================
# 2. fold retarget + run-twice idempotency
# ===========================================================================
LOCAL_BLOB = {
    "v": 1,
    "updated": "2026-08-01T00:00:00.000Z",
    "items": [{"t": "AAPL", "added": "2026-07-01T00:00:00.000Z", "note": ""},
              {"t": "MSFT", "added": "2026-07-02T00:00:00.000Z", "note": ""}],
    "order": ["AAPL", "MSFT"],
    "settings": {},
}

# stub the WL seam the fold reads its local book from
WL_STUB = """
function installWL(blob) {
  global.window.WL = {
    getBlob: function () { return blob; },
    merge: function () { return 0; }
  };
}
"""


@needs_node
def test_fold_targets_the_list_named_watchlist_not_whatever_sorts_first():
    """The retarget this wave ships. The account's FIRST list is 'Default' (the Terminal
    seeds one); the previous `.order(position).limit(1)` resolution folded the visitor's
    local book into it. The fold now lands in the list NAMED 'Watchlist' — created if
    absent — and 'Default' is left exactly as it was (server-only lists are kept).

    Note the two resolutions are separate under ruling R1: this account BINDS 'Default'
    (branch 2, no creation) while the fold — which has content to deliver — creates and
    fills 'Watchlist'."""
    out = _ws(
        WL_STUB + """
        installWL(BLOB);
        var db = makeDb({watchlists: [{id: 'L-DEF', user_id: 'u1', name: 'Default', position: 0}],
                         watchlist_symbols: [
                           {id: 'd1', watchlist_id: 'L-DEF', symbol: 'SPY', position: 0}]});
        WS._setTestSession(USER, db.client);
        WS.pull().then(function () {
          var st = WS._testState();
          var created = db.tables.watchlists.filter(function (l) { return l.name === 'Watchlist'; })[0];
          OUT({foldTargetName: (db.tables.watchlists.filter(function (l) {
                 return String(l.id) === String(st.foldTargetId); })[0] || {}).name,
               boundId: st.activeId,
               createdWatchlist: !!created,
               defaultUntouched: symbolsOf(db, 'L-DEF'),
               folded: created ? symbolsOf(db, created.id) : null,
               marker: localStorage.getItem('mdash.watchstore.folded.v1')});
        });
        """,
        {"USER": USER, "BLOB": LOCAL_BLOB},
    )
    assert out["foldTargetName"] == "Watchlist"
    assert out["boundId"] == "L-DEF"              # ruling R1 branch 2: bound to Default
    assert out["createdWatchlist"] is True
    assert out["defaultUntouched"] == ["SPY"]      # the pre-existing list is not touched
    assert out["folded"] == ["AAPL", "MSFT"]
    assert out["marker"] == "1"


@needs_node
def test_fold_retarget_is_a_no_op_for_an_account_macro_itself_created():
    """The shipped auto-create already NAMED that first list 'Watchlist' — so for the
    common (Macro-only) account both resolutions land on the identical row."""
    out = _ws(
        WL_STUB + """
        installWL(BLOB);
        var db = makeDb({watchlists: [{id: 'L-W', user_id: 'u1', name: 'Watchlist', position: 0}],
                         watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        WS.pull().then(function () {
          var st = WS._testState();
          OUT({foldTargetId: st.foldTargetId, boundId: st.activeId,
               listRows: db.tables.watchlists.length,
               folded: symbolsOf(db, 'L-W')});
        });
        """,
        {"USER": USER, "BLOB": LOCAL_BLOB},
    )
    assert out["foldTargetId"] == "L-W"    # adopted, not re-created
    assert out["boundId"] == "L-W"
    assert out["listRows"] == 1
    assert out["folded"] == ["AAPL", "MSFT"]


# ---------------------------------------------------------------------------
# Commissioning ruling R1 — the three BIND branches.
#
# Binding and folding are separate resolutions. Binding creates a list ONLY when the
# account has none; folding creates 'Watchlist' when absent, but only ever after it has
# content to deliver. The pair is what keeps a Terminal-native account from both
# (a) seeing an empty page on a fresh device and (b) collecting a spurious empty
# 'Watchlist' row in the list picker W1b is about to make server-backed.
# ---------------------------------------------------------------------------
EMPTY_BLOB = {"v": 1, "updated": "", "items": [], "order": [], "settings": {}}


@needs_node
def test_R1_branch2_terminal_default_only_account_binds_default_and_creates_nothing():
    """(a) The cohort the ruling exists for: the account's only list is the Terminal's
    'Default'. Bind it, and mint NOTHING."""
    out = _ws(
        WL_STUB + """
        installWL(BLOB);
        var db = makeDb({watchlists: [{id: 'L-DEF', user_id: 'u1', name: 'Default', position: 0}],
                         watchlist_symbols: [
                           {id: 'd1', watchlist_id: 'L-DEF', symbol: 'SPY', position: 0}]});
        WS._setTestSession(USER, db.client);
        WS.pull().then(function () {
          OUT({boundId: WS._testState().activeId,
               lists: db.tables.watchlists.map(function (l) { return l.name; }),
               inserts: db.ops.filter(function (o) {
                 return o.kind === 'insert' && o.table === 'watchlists'; }).length,
               visible: symbolsOf(db, 'L-DEF')});
        });
        """,
        {"USER": USER, "BLOB": EMPTY_BLOB},
    )
    assert out["boundId"] == "L-DEF"       # the page shows their real list, not an empty one
    assert out["lists"] == ["Default"]     # no spurious 'Watchlist' row
    assert out["inserts"] == 0             # and no list insert was even attempted
    assert out["visible"] == ["SPY"]


@needs_node
def test_R1_branch2_multi_list_account_binds_first_by_position_and_creates_nothing():
    """(b) Several lists, none named 'Watchlist' → bind the first by (position,
    created_at). `listsFetch` orders by exactly that, so 'first' is well-defined."""
    out = _ws(
        WL_STUB + """
        installWL(BLOB);
        var db = makeDb({watchlists: [
                           {id: 'L-B', user_id: 'u1', name: 'Space', position: 2,
                            created_at: '2026-03-01T00:00:00.000Z'},
                           {id: 'L-A', user_id: 'u1', name: 'Gold Miners', position: 1,
                            created_at: '2026-02-01T00:00:00.000Z'}],
                         watchlist_symbols: [
                           {id: 'g1', watchlist_id: 'L-A', symbol: 'NEM', position: 0}]});
        WS._setTestSession(USER, db.client);
        WS.pull().then(function () {
          OUT({boundId: WS._testState().activeId,
               lists: db.tables.watchlists.map(function (l) { return l.name; }).sort(),
               inserts: db.ops.filter(function (o) {
                 return o.kind === 'insert' && o.table === 'watchlists'; }).length});
        });
        """,
        {"USER": USER, "BLOB": EMPTY_BLOB},
    )
    assert out["boundId"] == "L-A"                      # lowest position, not insertion order
    assert out["lists"] == ["Gold Miners", "Space"]     # nothing minted
    assert out["inserts"] == 0


@needs_node
def test_R1_branch3_zero_list_account_creates_watchlist_and_binds_it():
    """(c) A genuinely new account has no list to bind, so one is created — this is the
    only branch in which BINDING creates anything."""
    out = _ws(
        WL_STUB + """
        installWL(BLOB);
        var db = makeDb({watchlists: [], watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        WS.pull().then(function () {
          var st = WS._testState();
          OUT({boundId: st.activeId,
               lists: db.tables.watchlists.map(function (l) { return l.name; }),
               boundIsTheCreatedRow: String(st.activeId) ===
                 String((db.tables.watchlists[0] || {}).id)});
        });
        """,
        {"USER": USER, "BLOB": EMPTY_BLOB},
    )
    assert out["lists"] == ["Watchlist"]
    assert out["boundIsTheCreatedRow"] is True
    assert out["boundId"] is not None


@needs_node
def test_R1_branch2_end_to_end_never_deletes_the_bound_lists_existing_rows():
    """The whole W1a machine on the branch-2 cohort, driven by the REAL watchlist.js
    rather than a merge stub — bind, merge, fold, then the ongoing push.

    This is the integration the unit tests cannot see. `pull()` unions the bound list's
    cloud rows into the local blob BEFORE any push can diff against it; without that
    ordering the full-membership diff sees `Default`'s existing `SPY` as "absent
    locally" and DELETES it. (Observed directly while writing this: stub out
    `WL.merge` and `SPY` is gone, one delete issued.) So the ordering is load-bearing,
    and this pins it end to end: zero deletes, `SPY` survives, local notes survive."""
    out = _run(
        """
        require(%s);
        var WS = require(%s);
        // the visitor's local book (init() cannot run under the shim — seed via the seam)
        window.WL.replace({v: 1, updated: '2026-08-01T00:00:00.000Z',
          items: [{t: 'AAPL', added: '2026-07-01T00:00:00.000Z', note: 'my note'}],
          order: ['AAPL'], settings: {}});
        var db = makeDb({watchlists: [{id: 'L-DEF', user_id: 'u1', name: 'Default', position: 0}],
                         watchlist_symbols: [
                           {id: 'd1', watchlist_id: 'L-DEF', symbol: 'SPY', position: 0}]});
        WS._setTestSession(USER, db.client);
        WS.pull().then(function () {
          window.WLCloud.push(window.WL.getBlob());   // the push any later edit triggers
          return wait(1000).then(function () {
            var w = db.tables.watchlists.filter(function (l) { return l.name === 'Watchlist'; })[0];
            OUT({bound: WS._testState().activeId,
                 local: window.WL.getBlob().items.map(function (i) { return i.t; }).sort(),
                 note: (window.WL.getBlob().items.filter(function (i) {
                   return i.t === 'AAPL'; })[0] || {}).note,
                 Default: symbolsOf(db, 'L-DEF'),
                 Watchlist: w ? symbolsOf(db, w.id) : null,
                 deletes: db.ops.filter(function (o) { return o.kind === 'delete'; }).length});
          });
        });
        """ % (json.dumps(str(WATCHLIST)), json.dumps(str(WATCHSTORE))),
        {"USER": USER},
    )
    assert out["deletes"] == 0                        # nothing is ever deleted here
    assert out["Default"] == ["AAPL", "SPY"]          # the pre-existing row SURVIVES
    assert out["bound"] == "L-DEF"                    # ruling R1 branch 2
    assert out["local"] == ["AAPL", "SPY"]            # pull unioned cloud into local
    assert out["note"] == "my note"                   # local-only notes are not erased
    # Ruling R1.1: the fold delivers the PRE-MERGE local set only. `SPY` reached the
    # local blob from Default via the merge, so it must NOT be planted into the list
    # the fold created — that was the duplication defect R1.1 corrects.
    assert out["Watchlist"] == ["AAPL"]


@needs_node
def test_R1_1_fold_delivers_only_the_pre_merge_local_set_under_divergence():
    """Ruling R1.1. Under R1 the BOUND list and the FOLD target diverge, and `pull()`
    merges the bound list's cloud rows into the local blob BEFORE the fold runs. Folding
    the merged blob therefore planted the bound list's whole membership into a list the
    user never asked for. The fold must deliver what the anonymous visitor accumulated
    locally — the PRE-MERGE set — and nothing else.

    The fixture is built so both halves of the fold are observable:
      bound `Default` = [SPY, TLT];  visitor's local book = [AAPL, SPY]
      -> post-merge blob = [AAPL, SPY, TLT], but the fold must plant exactly [AAPL, SPY].
    `TLT` is the tell: it exists only in the bound list, so it appearing in 'Watchlist'
    means the fold read the merged blob. `SPY` is in BOTH the local book and the bound
    list, which is what makes the dedupe-base mutation in 5b detectable."""
    out = _run(
        """
        require(%s);
        var WS = require(%s);
        window.WL.replace({v: 1, updated: '2026-08-01T00:00:00.000Z',
          items: [{t: 'AAPL', added: '2026-07-01T00:00:00.000Z', note: ''},
                  {t: 'SPY',  added: '2026-07-02T00:00:00.000Z', note: ''}],
          order: ['AAPL', 'SPY'], settings: {}});
        var db = makeDb({watchlists: [{id: 'L-DEF', user_id: 'u1', name: 'Default', position: 0}],
                         watchlist_symbols: [
                           {id: 'd1', watchlist_id: 'L-DEF', symbol: 'SPY', position: 0},
                           {id: 'd2', watchlist_id: 'L-DEF', symbol: 'TLT', position: 1}]});
        WS._setTestSession(USER, db.client);
        WS.pull().then(function () {
          var st = WS._testState();
          var w = db.tables.watchlists.filter(function (l) { return l.name === 'Watchlist'; })[0];
          OUT({bound: st.activeId, foldTarget: st.foldTargetId,
               diverged: String(st.activeId) !== String(st.foldTargetId),
               Watchlist: w ? symbolsOf(db, w.id) : null,
               Default: symbolsOf(db, 'L-DEF'),
               localAfterMerge: window.WL.getBlob().items.map(function (i) { return i.t; }).sort(),
               marker: localStorage.getItem('mdash.watchstore.folded.v1')});
        });
        """ % (json.dumps(str(WATCHLIST)), json.dumps(str(WATCHSTORE))),
        {"USER": USER},
    )
    assert out["diverged"] is True                    # the case the ruling is about
    assert out["bound"] == "L-DEF"
    assert out["localAfterMerge"] == ["AAPL", "SPY", "TLT"]   # merge did happen
    # the fold plants the PRE-merge set only: TLT never reaches the created list
    assert out["Watchlist"] == ["AAPL", "SPY"]
    assert out["Default"] == ["SPY", "TLT"]           # bound list untouched by the fold
    assert out["marker"] == "1"


@needs_node
def test_R1_binding_never_creates_a_list_for_an_account_with_nothing_to_fold():
    """The property the ruling is really buying, stated directly: signing in repeatedly
    on a device with an empty local book must never grow the account's list count."""
    out = _ws(
        WL_STUB + """
        installWL(BLOB);
        var db = makeDb({watchlists: [{id: 'L-DEF', user_id: 'u1', name: 'Default', position: 0}],
                         watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        WS.pull().then(function () {
          return WS.pull().then(function () {
            OUT({lists: db.tables.watchlists.map(function (l) { return l.name; }),
                 marker: localStorage.getItem('mdash.watchstore.folded.v1')});
          });
        });
        """,
        {"USER": USER, "BLOB": EMPTY_BLOB},
    )
    assert out["lists"] == ["Default"]
    assert out["marker"] is None     # and the one-shot fold is still unspent


@needs_node
def test_fold_run_twice_yields_identical_state():
    """The packet's run-twice gate. A second pull (re-login, tab focus, second device
    session) must plan nothing: identical rows, identical list set, no duplicates."""
    out = _ws(
        WL_STUB + """
        installWL(BLOB);
        var db = makeDb({watchlists: [], watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        function snapshot() {
          return JSON.stringify({
            lists: db.tables.watchlists.map(function (l) { return [l.name, l.position]; }).sort(),
            syms: db.tables.watchlist_symbols.map(function (r) {
              return [r.watchlist_id, r.symbol]; }).sort()
          });
        }
        WS.pull().then(function () {
          var first = snapshot();
          var insertsAfterFirst = db.ops.filter(function (o) { return o.kind === 'insert'; }).length;
          return WS.pull().then(function () {
            OUT({first: first, second: snapshot(),
                 symbolRows: db.tables.watchlist_symbols.length,
                 listRows: db.tables.watchlists.length,
                 extraInserts: db.ops.filter(function (o) {
                   return o.kind === 'insert'; }).length - insertsAfterFirst});
          });
        });
        """,
        {"USER": USER, "BLOB": LOCAL_BLOB},
    )
    assert out["first"] == out["second"]   # identical state, byte for byte
    assert out["symbolRows"] == 2          # AAPL + MSFT once
    assert out["listRows"] == 1            # 'Watchlist' created once
    assert out["extraInserts"] == 0        # the second pass writes nothing at all


@needs_node
def test_fold_does_not_consume_the_one_shot_on_an_empty_local_book():
    """Kept behaviour: signing in on a fresh device must not burn the one-shot, or a
    book built later never folds."""
    out = _ws(
        WL_STUB + """
        installWL({v: 1, updated: '', items: [], order: [], settings: {}});
        var db = makeDb({watchlists: [], watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        WS.pull().then(function () {
          OUT({marker: localStorage.getItem('mdash.watchstore.folded.v1'),
               symbolRows: db.tables.watchlist_symbols.length});
        });
        """,
        {"USER": USER},
    )
    assert out["marker"] is None
    assert out["symbolRows"] == 0


@needs_node
def test_fold_is_not_marked_when_the_insert_fails_so_it_retries():
    """Kept behaviour: marking a FAILED fold as done silently discards the visitor's
    whole list. Reproduced by making the symbol insert fail.

    THE STUB SHAPE IS THE TEST. postgrest-js RESOLVES with `{data, error}` — it does not
    throw. An earlier version of this stub invoked the callback synchronously inside
    `Promise.resolve(f(...))`, so `throw res.error` escaped `.then()` before `.catch`
    was attached: `_foldInsert`'s own catch never ran, the outer catch swallowed it, and
    mutating `_foldInsert`'s catch to call `_markFolded()` left the whole suite green —
    a regression that permanently discards the anonymous visitor's entire watchlist
    would have shipped green. Resolving (never throwing) is what puts the rejection on
    the chain `.catch` actually guards."""
    out = _ws(
        WL_STUB + """
        installWL(BLOB);
        var db = makeDb({watchlists: [{id: 'L-W', user_id: 'u1', name: 'Watchlist', position: 0}],
                         watchlist_symbols: []});
        var realFrom = db.client.from;
        db.client.from = function (table) {
          var api = realFrom(table);
          if (table === 'watchlist_symbols') {
            api.insert = function () {
              // real postgrest shape: a RESOLVED promise carrying `error`, and the rows
              // never land (a failed insert must not mutate the table)
              return Promise.resolve({data: null, error: {code: '42501', message: 'rls denied'}});
            };
          }
          return api;
        };
        WS._setTestSession(USER, db.client);
        WS.pull().then(function () {
          OUT({marker: localStorage.getItem('mdash.watchstore.folded.v1'),
               rowsLanded: db.tables.watchlist_symbols.length,
               localKept: (window.WL.getBlob().items || []).map(function (i) { return i.t; })});
        });
        """,
        {"USER": USER, "BLOB": LOCAL_BLOB},
    )
    assert out["marker"] is None          # NOT marked -> retried next session
    assert out["rowsLanded"] == 0         # the failed insert landed nothing
    assert out["localKept"] == ["AAPL", "MSFT"]   # the visitor's book is intact


# ===========================================================================
# 3. NAMED REGRESSION — a stale cache of list A can never delete rows of list B
# ===========================================================================
@needs_node
def test_stale_cache_of_one_list_can_never_delete_another_lists_rows():
    """THE regression this wave exists to prevent.

    Setup is the worst realistic case: a stale localStorage cache for list A claims
    symbols that list B also holds, and the user then edits list B down to nothing.
    The push must delete exactly B's own rows and leave A untouched — and every delete
    statement must carry `.eq('watchlist_id', <B>)`.

    The Supabase double replays filters against real row arrays, so an unscoped delete
    would genuinely remove A's rows here rather than merely failing an assertion."""
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        // a stale cache for list A that even claims list B's symbols
        localStorage.setItem('mdash.wl.L-AI.v1', JSON.stringify({
          v: 1, updated: '2026-01-01T00:00:00.000Z',
          items: [{t: 'NVDA'}, {t: 'AVGO'}, {t: 'NEM'}, {t: 'AEM'}],
          order: ['NVDA', 'AVGO', 'NEM', 'AEM'], settings: {}
        }));
        // read ONLY list B, then push an empty membership at it
        WS.symbols.list('L-GOLD').then(function () {
          return WS.symbols.push('L-GOLD', []).then(function (r) {
            var deletes = db.ops.filter(function (o) { return o.kind === 'delete'; });
            OUT({
              result: r,
              ai: symbolsOf(db, 'L-AI'),
              gold: symbolsOf(db, 'L-GOLD'),
              deleteScopes: deletes.map(function (o) {
                var eq = o.filters.filter(function (f) {
                  return f.op === 'eq' && f.col === 'watchlist_id'; });
                return {table: o.table, scoped: eq.map(function (f) { return f.val; }),
                        symbols: (o.filters.filter(function (f) {
                          return f.op === 'in' && f.col === 'symbol'; })[0] || {}).val};
              })
            });
          });
        });
        """,
        {"USER": USER, "SEED": TWO_LISTS},
    )
    assert out["ai"] == ["AVGO", "NVDA"], "list A lost rows to list B's push"
    assert out["gold"] == []
    assert out["result"] == {"inserted": 0, "deleted": 2}
    assert len(out["deleteScopes"]) == 1
    scope = out["deleteScopes"][0]
    assert scope["table"] == "watchlist_symbols"
    assert scope["scoped"] == ["L-GOLD"], "delete was not scoped to the list being pushed"
    assert sorted(scope["symbols"]) == ["AEM", "NEM"], "delete reached beyond list B's rows"


@needs_node
def test_a_list_that_was_never_read_is_never_diffed():
    """No server read means no delete authority. A push at an unread list is a no-op
    rather than "everything in the cloud is absent locally, delete it all"."""
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        localStorage.setItem('mdash.wl.L-AI.v1', JSON.stringify({
          v: 1, items: [{t: 'NVDA'}], order: ['NVDA'], settings: {}}));
        WS.symbols.push('L-AI', []).then(function (r) {
          OUT({result: r, ai: symbolsOf(db, 'L-AI'),
               deletes: db.ops.filter(function (o) { return o.kind === 'delete'; }).length});
        });
        """,
        {"USER": USER, "SEED": TWO_LISTS},
    )
    assert out["result"] is None
    assert out["ai"] == ["AVGO", "NVDA"]   # untouched
    assert out["deletes"] == 0


@needs_node
def test_a_push_issued_during_the_setActive_window_never_lands_on_the_new_list():
    """The switch window, which the previous version of this test could not see.

    `setActiveList` used to assign `wlId` SYNCHRONOUSLY and only fire `wl-list-change`
    after its fetch resolved. In between, `WLCloud.push(blob)` — a caller that names no
    list, i.e. today's page — resolved its target to the NEW list while the blob still
    held the OLD list's membership, and the full-membership diff deleted the new list's
    rows and inserted the old list's. Measured before the fix: 3 sibling rows deleted
    plus a foreign insert.

    So: issue the push DURING the fetch window (before setActive's promise settles) and
    require that it landed on the OLD list — or nowhere. Never on the new one."""
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        Promise.all([WS.symbols.list('L-AI'), WS.symbols.list('L-GOLD')]).then(function () {
          return WS.lists.setActive('L-AI');
        }).then(function () {
          var goldBefore = symbolsOf(db, 'L-GOLD');
          var p = WS.lists.setActive('L-GOLD');      // fetch in flight, NOT yet settled
          // the page pushes its still-unrebound blob, naming no list
          window.WLCloud.push({items: [{t: 'NVDA'}]});
          var targetedAtSwitchTime = window.WLCloud.activeListId();
          return p.then(function () {
            return wait(900).then(function () {
              OUT({targetedAtSwitchTime: targetedAtSwitchTime,
                   activeAfter: WS.lists.activeId(),
                   goldBefore: goldBefore, goldAfter: symbolsOf(db, 'L-GOLD'),
                   ai: symbolsOf(db, 'L-AI'),
                   deletesOnGold: db.ops.filter(function (o) {
                     return o.kind === 'delete' && o.filters.some(function (f) {
                       return f.col === 'watchlist_id' && String(f.val) === 'L-GOLD'; });
                   }).length});
            });
          });
        });
        """,
        {"USER": USER, "SEED": TWO_LISTS},
    )
    # during the window the store still reports the OLD list, so the push bound to it
    assert out["targetedAtSwitchTime"] == "L-AI"
    assert out["activeAfter"] == "L-GOLD"          # the switch still completes
    # the new list is untouched: no delete ever aimed at it, membership unchanged
    assert out["deletesOnGold"] == 0
    assert out["goldAfter"] == out["goldBefore"] == ["AEM", "NEM"]
    # and the push did what it meant to do, against the list it was issued for
    assert out["ai"] == ["NVDA"]


@needs_node
def test_two_unread_lists_each_keep_their_own_queued_push():
    """`queuedPush` was a single global slot, so a second unread list's push silently
    overwrote the first one's — list A's edit discarded with no error anywhere. The
    queue is per-list now, like the debounce timers."""
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        WS._setTestLists({activeId: 'L-AI'});      // bound, but NEITHER list read yet
        window.WLCloud.push({items: [{t: 'NVDA'}, {t: 'AVGO'}, {t: 'GOOGL'}]}, 'L-AI');
        window.WLCloud.push({items: [{t: 'NEM'}, {t: 'AEM'}, {t: 'GOLD'}]}, 'L-GOLD');
        wait(900).then(function () {
          // both were queued (unread), and nothing was written yet
          var wroteEarly = db.ops.filter(function (o) { return o.kind === 'insert'; }).length;
          // a pull reads the lists and flushes; read the second list too so both can land
          return WS.symbols.list('L-GOLD').then(function () {
            return WS.pull().then(function () {
              return wait(300).then(function () {
                OUT({wroteEarly: wroteEarly,
                     ai: symbolsOf(db, 'L-AI'), gold: symbolsOf(db, 'L-GOLD')});
              });
            });
          });
        });
        """,
        {"USER": USER, "SEED": TWO_LISTS},
    )
    assert out["wroteEarly"] == 0          # unread lists are never diffed
    # BOTH queued edits survive — neither overwrote the other
    assert out["ai"] == ["AVGO", "GOOGL", "NVDA"]
    assert out["gold"] == ["AEM", "GOLD", "NEM"]


@needs_node
def test_a_push_with_no_bound_list_is_refused_not_queued_for_whatever_binds_later():
    """A ticker set whose owner is unknown can never be safely applied. It used to be
    queued with a null target and re-resolved at FLUSH time against whatever `wlId` had
    become by then — a full-membership diff aimed at an arbitrary list. Refused now."""
    out = _ws(
        WL_STUB + """
        installWL(BLOB);
        var db = makeDb({watchlists: [{id: 'L-W', user_id: 'u1', name: 'Watchlist', position: 0}],
                         watchlist_symbols: [
                           {id: 'w1', watchlist_id: 'L-W', symbol: 'SPY', position: 0},
                           {id: 'w2', watchlist_id: 'L-W', symbol: 'TLT', position: 1},
                           {id: 'w3', watchlist_id: 'L-W', symbol: 'GLD', position: 2}]});
        WS._setTestSession(USER, db.client);
        // no list bound yet (the sign-in pull window): push a set that names no list
        window.WLCloud.push({items: [{t: 'AAPL'}]});
        WS.pull().then(function () {
          return wait(900).then(function () {
            OUT({rows: symbolsOf(db, 'L-W'),
                 deletes: db.ops.filter(function (o) { return o.kind === 'delete'; }).length});
          });
        });
        """,
        {"USER": USER, "BLOB": LOCAL_BLOB},
    )
    # the unowned set never became a diff against the list that later bound: the three
    # pre-existing rows survive (the fold adds its own, which is a separate mechanism)
    assert out["deletes"] == 0
    for t in ("SPY", "TLT", "GLD"):
        assert t in out["rows"], f"{t} was wiped by an unowned push"


@needs_node
def test_lists_are_sorted_client_side_even_when_the_server_returns_them_unordered():
    """Ruling R1 branch 2 binds "the FIRST list by (position, created_at)", so that
    ordering decides which list a returning user is bound to. The query asks for it AND
    `listsFetch` sorts again — this pins the second half, which the server-ordered
    fixtures cannot see. Here the double deliberately ignores `.order()`."""
    out = _ws(
        """
        var db = makeDb({watchlists: [
          {id: 'L-C', user_id: 'u1', name: 'C', position: 5, created_at: '2026-05-01T00:00:00.000Z'},
          {id: 'L-A', user_id: 'u1', name: 'A', position: 1, created_at: '2026-01-01T00:00:00.000Z'},
          {id: 'L-B', user_id: 'u1', name: 'B', position: 1, created_at: '2026-02-01T00:00:00.000Z'}
        ], watchlist_symbols: []}, {ignoreOrder: true});
        WS._setTestSession(USER, db.client);
        WS.lists.refresh().then(function (all) {
          OUT({order: all.map(function (l) { return l.id; })});
        });
        """,
        {"USER": USER},
    )
    # position asc, then created_at asc as the tie-break between L-A and L-B
    assert out["order"] == ["L-A", "L-B", "L-C"]


@needs_node
def test_symbol_add_reads_an_unread_list_first_instead_of_blind_inserting():
    """`watchlist_symbols` has NO unique index on (watchlist_id, symbol), so a blind
    insert against an unread list leaves a real duplicate row that only read-time dedupe
    hides. Same refusal policy as pushList: read first."""
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        // NVDA is already in L-AI, but the list has never been read
        WS.symbols.add('L-AI', 'NVDA').then(function (r) {
          return WS.symbols.add('L-AI', 'GOOGL').then(function () {
            OUT({dupResult: r,
                 rows: db.tables.watchlist_symbols
                   .filter(function (x) { return x.watchlist_id === 'L-AI'; })
                   .map(function (x) { return x.symbol; }).sort(),
                 nvdaRows: db.tables.watchlist_symbols.filter(function (x) {
                   return x.watchlist_id === 'L-AI' && x.symbol === 'NVDA'; }).length});
          });
        });
        """,
        {"USER": USER, "SEED": TWO_LISTS},
    )
    assert out["dupResult"]["skipped"] is True    # recognised as already present
    assert out["nvdaRows"] == 1                   # exactly one row, no duplicate
    assert out["rows"] == ["AVGO", "GOOGL", "NVDA"]


@needs_node
def test_push_carries_its_target_through_the_debounce():
    """The blob is bound to a list at ENQUEUE time. Before this wave the target was read
    from a module global at FIRE time, so a switch inside the 600ms window redirected the
    push at the wrong list. Two lists are also debounced independently — a push to B must
    not cancel a pending push to A."""
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        Promise.all([WS.symbols.list('L-AI'), WS.symbols.list('L-GOLD')]).then(function () {
          WS.lists.setActive('L-AI');
          // enqueue against A, then immediately switch the active list to B
          window.WLCloud.push({items: [{t: 'NVDA'}]}, 'L-AI');
          window.WLCloud.push({items: [{t: 'NEM'}, {t: 'AEM'}, {t: 'GOLD'}]}, 'L-GOLD');
          return WS.lists.setActive('L-GOLD').then(function () {
            return wait(900).then(function () {
              OUT({ai: symbolsOf(db, 'L-AI'), gold: symbolsOf(db, 'L-GOLD')});
            });
          });
        });
        """,
        {"USER": USER, "SEED": TWO_LISTS},
    )
    # A's push (drop AVGO) landed on A; B's push (add GOLD) landed on B. Neither cancelled
    # the other, and neither was redirected by the active-list switch.
    assert out["ai"] == ["NVDA"]
    assert out["gold"] == ["AEM", "GOLD", "NEM"]


# ===========================================================================
# 4. semantic invariants A-D (commissioning packet §0)
# ===========================================================================
BOTH_POPULATIONS = {
    "watchlists": [{"id": "L-AI", "user_id": "u1", "name": "AI", "position": 0}],
    "watchlist_symbols": [
        {"id": "s1", "watchlist_id": "L-AI", "symbol": "NVDA", "position": 0},
    ],
    "portfolio_positions": [
        {"id": "p1", "user_id": "u1", "ticker": "NVDA", "shares": 10,
         "entry_price": 100, "entry_date": "2026-01-01", "notes": None, "status": "open"},
    ],
}


def _pf(db_expr: str = "db") -> str:
    return ("%s.tables.portfolio_positions.map(function (r) { "
            "return [r.ticker, r.status]; })" % db_expr)


@needs_node
def test_invariant_A_adding_to_a_watchlist_leaves_portfolio_positions_unchanged():
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        var before = JSON.stringify(%s);
        WS.symbols.list('L-AI').then(function () {
          return WS.symbols.add('L-AI', 'AAPL').then(function () {
            OUT({before: before, after: JSON.stringify(%s),
                 watchlist: symbolsOf(db, 'L-AI')});
          });
        });
        """ % (_pf(), _pf()),
        {"USER": USER, "SEED": BOTH_POPULATIONS},
    )
    assert out["watchlist"] == ["AAPL", "NVDA"]
    assert out["before"] == out["after"]


@needs_node
def test_invariant_B_adding_a_portfolio_position_changes_no_watchlist_row():
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        var before = JSON.stringify(symbolsOf(db, 'L-AI'));
        WS.portfolio.upsert({ticker: 'MSFT', shares: 5, entry_price: 400,
                             entry_date: '2026-03-01', status: 'open'}).then(function () {
          OUT({before: before, after: JSON.stringify(symbolsOf(db, 'L-AI')),
               portfolio: %s});
        });
        """ % _pf(),
        {"USER": USER, "SEED": BOTH_POPULATIONS},
    )
    assert out["before"] == out["after"] == '["NVDA"]'
    assert sorted(out["portfolio"]) == [["MSFT", "open"], ["NVDA", "open"]]


@needs_node
def test_invariant_C_removing_from_a_watchlist_keeps_the_portfolio_position():
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        WS.symbols.list('L-AI').then(function () {
          return WS.symbols.remove('L-AI', 'NVDA').then(function () {
            OUT({watchlist: symbolsOf(db, 'L-AI'), portfolio: %s});
          });
        });
        """ % _pf(),
        {"USER": USER, "SEED": BOTH_POPULATIONS},
    )
    assert out["watchlist"] == []
    assert out["portfolio"] == [["NVDA", "open"]]   # the held position survives


@needs_node
def test_invariant_D_closing_a_portfolio_position_keeps_watchlist_membership():
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        WS.portfolio.close('p1').then(function () {
          OUT({watchlist: symbolsOf(db, 'L-AI'), portfolio: %s});
        });
        """ % _pf(),
        {"USER": USER, "SEED": BOTH_POPULATIONS},
    )
    assert out["portfolio"] == [["NVDA", "closed"]]
    assert out["watchlist"] == ["NVDA"]             # attention set is unaffected


@needs_node
def test_a_full_membership_push_never_reaches_portfolio_positions():
    """The diff's delete is the sharpest edge in the module; it must be structurally
    unable to address the other population's table at all."""
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        WS.symbols.list('L-AI').then(function () {
          return WS.symbols.push('L-AI', []).then(function () {
            OUT({tables: db.ops.filter(function (o) { return o.kind === 'delete'; })
                   .map(function (o) { return o.table; }),
                 portfolio: %s});
          });
        });
        """ % _pf(),
        {"USER": USER, "SEED": BOTH_POPULATIONS},
    )
    assert out["tables"] == ["watchlist_symbols"]
    assert out["portfolio"] == [["NVDA", "open"]]


# ===========================================================================
# 5. anonymous / signed-out behaviour is untouched
# ===========================================================================
@needs_node
def test_signed_out_multi_list_calls_are_inert_and_write_nothing():
    out = _ws(
        """
        var errs = [];
        function guard(p) { return p.then(function () { return 'resolved'; },
                                          function (e) { return String(e.message || e); }); }
        Promise.all([
          guard(WS.lists.create('X')),
          guard(WS.lists.refresh()),
          guard(WS.symbols.list('L-AI')),
          guard(WS.symbols.push('L-AI', ['NVDA']))
        ]).then(function (r) {
          OUT({results: r, wrote: __sets.filter(function (k) {
            return k.indexOf('mdash.wl.') === 0; }).length});
        });
        """
    )
    assert out["results"][:3] == ["no-session", "no-session", "no-session"]
    assert out["results"][3] == "resolved"   # push is a silent no-op, never an error
    assert out["wrote"] == 0                 # no per-list cache is created while signed out


@needs_node
def test_watchlist_js_default_binding_uses_the_anonymous_key_verbatim():
    """`mdash.watchlist.v1` stays the anonymous store: same key, same probe key, same
    unscoped `#wl=` share fragment. Signed-out behaviour is byte-identical."""
    out = _wl(
        """
        OUT({key: window.WL.storageKey(), listId: window.WL.listId(),
             share: window.WL.shareParam()});
        """
    )
    assert out["key"] == "mdash.watchlist.v1"
    assert out["listId"] is None
    assert out["share"] == "wl"


@needs_node
def test_watchlist_js_rebind_switches_key_and_share_scope_without_carrying_state():
    """The three W2.5 seams, exercised. A rebind re-reads from the new list's own cache
    — it must not carry the previous list's items across, which under a full-membership
    diff push would wipe the list being switched to."""
    out = _wl(
        """
        localStorage.setItem('mdash.watchlist.v1', JSON.stringify({
          v: 1, updated: '2026-08-01T00:00:00.000Z',
          items: [{t: 'AAPL', added: '2026-07-01T00:00:00.000Z', note: ''}],
          order: ['AAPL'], settings: {}}));
        localStorage.setItem('mdash.wl.L-AI.v1', JSON.stringify({
          v: 1, updated: '2026-08-02T00:00:00.000Z',
          items: [{t: 'NVDA', added: '2026-07-02T00:00:00.000Z', note: ''}],
          order: ['NVDA'], settings: {}}));
        var anon = window.WL.getBlob().items.map(function (i) { return i.t; });
        window.WL.bindList('L-AI', 'AI');
        var bound = {key: window.WL.storageKey(), share: window.WL.shareParam(),
                     items: window.WL.getBlob().items.map(function (i) { return i.t; })};
        window.WL.bindList(null);
        OUT({anon: anon, bound: bound,
             back: {key: window.WL.storageKey(),
                    items: window.WL.getBlob().items.map(function (i) { return i.t; })}});
        """
    )
    assert out["anon"] == []                      # nothing read yet — init() never ran
    assert out["bound"]["key"] == "mdash.wl.L-AI.v1"
    assert out["bound"]["share"] == "wl.AI"       # share fragment is list-scoped
    assert out["bound"]["items"] == ["NVDA"]      # read from the LIST's cache
    assert out["back"]["key"] == "mdash.watchlist.v1"
    assert out["back"]["items"] == ["AAPL"]       # and back to the anonymous store


@needs_node
def test_a_scoped_share_link_is_not_consumed_by_a_different_list():
    """`#wl.<name>=` is only consumed by the list it was exported from; a bare `#wl=`
    link stays unscoped so every link already in the wild keeps working."""
    out = _wl(
        """
        var payload = Buffer.from(JSON.stringify({
          v: 1, updated: '2026-08-01T00:00:00.000Z',
          items: [{t: 'RKLB', added: '2026-07-01T00:00:00.000Z', note: ''}],
          order: ['RKLB'], settings: {}}), 'utf8').toString('base64');
        function hashFor(h, bind, name) {
          global.location.hash = h;
          global.history = {replaceState: function () { global.location.hash = ''; }};
          window.WL.bindList(bind, name);
          WLT.consumeShareHash();
          return window.WL.getBlob().items.map(function (i) { return i.t; });
        }
        OUT({wrongList: hashFor('#wl.Space=' + payload, 'L-AI', 'AI'),
             rightList: hashFor('#wl.Space=' + payload, 'L-SP', 'Space'),
             legacyBare: hashFor('#wl=' + payload, null, '')});
        """
    )
    assert out["wrongList"] == []                 # left alone, not merged into 'AI'
    assert out["rightList"] == ["RKLB"]           # consumed by its own list
    assert out["legacyBare"] == ["RKLB"]          # unscoped legacy link still works


# ===========================================================================
# 6. D05 W1-honesty — three defects the R6 census flagged as the forbidden
#    case. The page's chip is the only sync disclosure (the Account Sync panel
#    is gone); whatever the store dispatches is what the user sees. These pin
#    the four states:
#      saved   — a WRITE just landed in the account
#      clean   — a READ succeeded; nothing written this session (no "Saved" copy)
#      saving  — a write is in flight
#      offline — a write is pending and the network is unreachable
# ===========================================================================

# Helper: install a chip-dispatch spy. WS has already loaded; init() returned
# early (no chip/box in the shim), so the only ws-save events arrive from
# setPill calls inside pull()/pushList()/symbolAdd(). We capture them all.
CHIP_SPY = """
var __chipSpy = {events: [], orig: null};
function installChipSpy() {
  __chipSpy.orig = global.document.dispatchEvent;
  global.document.dispatchEvent = function (e) {
    __chipSpy.events.push({type: e && e.type, detail: e && e.detail});
    return true;
  };
}
function restoreChipSpy() {
  global.document.dispatchEvent = __chipSpy.orig;
}
function wsSaves() {
  return __chipSpy.events.filter(function (e) { return e.type === 'ws-save'; })
    .map(function (e) { return e && e.detail && e.detail.state; });
}
"""

# Helper: read the marker blob as plain JSON. The store extends the per-list
# cache (`mdash.wl.<listId>.v1`) with `pendingPushes` / `pendingInserts` /
# `tombstones`; tests read it back to verify the persistence law. The
# watchstore helper accepts a listId so the test can target the same key.
SYNC_BLOB = """
function readSyncBlob(listId) {
  try {
    var key = listId ? ('mdash.wl.' + listId + '.v1') : 'mdash.watchlist.v1';
    var raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch (e) { return null; }
}
"""


@needs_node
def test_T1_signed_in_pull_with_no_pending_writes_dispatches_clean_not_saved():
    """D05 Q2 #3: pull() success must dispatch chip `clean`, NOT `saved`. The
    chip copy for `saved` says 'Saved to your Mastermind account' — false on a
    plain read with no write. The page's own vocabulary (templates/watchlist.js
    ~line 854) names `clean` for 'a READ succeeded from the account; nothing has
    been written this session' and `saved` for 'a WRITE just landed in the
    account'. Pre-fix, pull() called `setPill('synced')` which mapped to `saved`.
    """
    out = _ws(
        CHIP_SPY + SYNC_BLOB + """
        installChipSpy();
        var db = makeDb({watchlists: [{id: 'L-W', user_id: 'u1', name: 'Watchlist', position: 0}],
                         watchlist_symbols: [
                           {id: 'w1', watchlist_id: 'L-W', symbol: 'NVDA', position: 0}]});
        WS._setTestSession(USER, db.client);
        WS.pull().then(function () {
          restoreChipSpy();
          var saves = wsSaves();
          OUT({saves: saves,
               hasSaved: saves.indexOf('saved') >= 0,
               hasClean: saves.indexOf('clean') >= 0,
               lastSave: saves.length ? saves[saves.length - 1] : null});
        });
        """,
        {"USER": USER},
    )
    # The defect: a plain read dispatched 'saved' — the chip claimed a write landed.
    assert out["hasSaved"] is False, \
        f"a plain pull() must never dispatch chip 'saved'; got saves={out['saves']}"
    # The fix: a plain pull() dispatches 'clean'.
    assert out["hasClean"] is True, \
        f"a plain pull() must dispatch chip 'clean'; got saves={out['saves']}"
    assert out["lastSave"] == "clean"


@needs_node
def test_T2_failed_push_is_persisted_retried_on_online_and_clears_on_success():
    """D05 Q2 #1: a failed push was swallowed with `setPill('offline')` and
    `return null` — no retry queue. After my fix, a failed push persists a
    per-list pending marker in `mdash.watchlist.v1`, keeps the chip honest
    (offline), and the `online` event retries the push. On success the marker
    is cleared and the chip says 'saved' (a WRITE just landed).

    This is the end-to-end shape the user actually sees: a symbol added on a
    flaky connection, network recovers, the change lands. The test injects a
    failing insert at the db-client layer (the same seam
    `test_fold_is_not_marked_when_the_insert_fails_so_it_retries` uses), runs
    the push, then restores the working client and fires `online`."""
    out = _ws(
        CHIP_SPY + SYNC_BLOB + """
        installChipSpy();
        var db = makeDb({watchlists: [{id: 'L-W', user_id: 'u1', name: 'Watchlist', position: 0}],
                         watchlist_symbols: [
                           {id: 'w1', watchlist_id: 'L-W', symbol: 'NVDA', position: 0}]});
        // the user's intent: their list should be {NVDA, AAPL} in the cloud.
        WS._setTestSession(USER, db.client);
        WS.pull().then(function () {
          // Inject failure: insert rejects with an RLS-shaped error. The push's
          // delete half (no-op here) would still succeed, but the insert fails.
          var realFrom = db.client.from;
          db.client.from = function (table) {
            var api = realFrom(table);
            if (table === 'watchlist_symbols') {
              // Replace `insert` / `delete` with no-ops so the FAKE_DB does NOT
              // mutate db.tables before the terminal rejects (its `insert()`
              // pushes rows eagerly, before `__run`). The chain
              // (`.insert()/delete()` + `.eq().in().then(...)`) stays intact
              // and only the final result rejects with an RLS-shaped error.
              api.insert = function () { return api; };
              api.delete = function () { return api; };
              api.__run = function () {
                return Promise.resolve({data: null, error: {code: '42501', message: 'rls denied'}});
              };
            }
            return api;
          };
          return WS.symbols.push('L-W', ['NVDA', 'AAPL']).then(function (result) {
            var sync = readSyncBlob('L-W');
            var failedSaves = wsSaves();
            // restore the working client so the retry actually writes
            db.client.from = realFrom;
            // dispatch the `online` event — watchstore.js's listener flushes
            // the pending push for this list (per spec (2) trigger (a)).
            window.dispatchEvent(new CustomEvent('online'));
            return wait(200).then(function () {
              restoreChipSpy();
              var synced = symbolsOf(db, 'L-W');
              var afterSync = readSyncBlob('L-W');
              var finalSaves = wsSaves();
              OUT({firstResult: result,
                   failedSaves: failedSaves,
                   finalSaves: finalSaves,
                   pendingBefore: (sync && sync.pendingPushes) || {},
                   pendingAfter: (afterSync && afterSync.pendingPushes) || {},
                   synced: synced});
            });
          });
        });
        """,
        {"USER": USER},
    )
    # push returned null (the existing swallow) because the failure path still
    # resolves with null — the marker is the new behaviour on top of that.
    assert out["firstResult"] is None
    # A pending marker exists after the failure (per-list, capturing the
    # user's intent: the local ticker set at enqueue time).
    assert out["pendingBefore"] is not None, "a failed push must persist a marker"
    assert "L-W" in out["pendingBefore"], "marker must be keyed by list id"
    assert sorted(out["pendingBefore"]["L-W"]["tickers"]) == ["AAPL", "NVDA"], \
        "marker must carry the user's intent (the ticker set being pushed)"
    # chip was 'offline' on failure (honest copy, no false saved claim).
    assert "offline" in out["failedSaves"]
    assert "saved" not in out["failedSaves"], \
        f"a failed push must never dispatch 'saved'; got {out['failedSaves']}"
    # After the online event the marker is gone (push retried and succeeded).
    assert (out["pendingAfter"] or {}) == {}, \
        f"successful retry must clear the marker; got {out['pendingAfter']}"
    # The insert actually landed in the cloud.
    assert sorted(out["synced"]) == ["AAPL", "NVDA"]
    # And the chip dispatched 'saved' on the successful retry.
    assert "saved" in out["finalSaves"], \
        f"a successful retry must dispatch 'saved'; got {out['finalSaves']}"


@needs_node
def test_T3_failed_unwatch_is_tombstoned_and_pull_does_not_resurrect_it():
    """D05 Q2 #2: a failed unwatch left the cloud row intact while the local
    blob had dropped the symbol; the next pull() union-merged the cloud row
    back and then painted `saved`. The fix records a tombstone for the
    symbol in `mdash.watchlist.v1` and the cloud→local merge EXCLUDES
    tombstoned symbols; the DELETE is retried with the same triggers as (2);
    the tombstone is cleared only on DELETE success.

    The cloud row is the one a future reader would have resurrected. This
    pins the three properties together: the tombstone is list-scoped, the
    merge respects it, and the retry clears it on success."""
    out = _ws(
        CHIP_SPY + SYNC_BLOB + """
        installChipSpy();
        var db = makeDb({watchlists: [{id: 'L-W', user_id: 'u1', name: 'Watchlist', position: 0}],
                         watchlist_symbols: [
                           {id: 'w1', watchlist_id: 'L-W', symbol: 'NVDA', position: 0},
                           {id: 'w2', watchlist_id: 'L-W', symbol: 'AAPL', position: 1}]});
        WS._setTestSession(USER, db.client);
        WS.symbols.list('L-W').then(function () {
          // Inject DELETE failure: the cloud keeps AAPL even though the local
          // push says it should not. NVDA survives (no delete needed).
          var realFrom = db.client.from;
          db.client.from = function (table) {
            var api = realFrom(table);
            if (table === 'watchlist_symbols') {
              // Fail only writes. SELECT must still resolve, or pull() exits in
              // its catch path before it can hand filtered rows to WL.merge.
              var realRun = api.__run;
              api.insert = function () { api.__failedWrite = true; return api; };
              api.delete = function () { api.__failedWrite = true; return api; };
              api.__run = function () {
                if (api.__failedWrite) {
                  return Promise.resolve({data: null, error: {code: '42501', message: 'rls denied'}});
                }
                return realRun();
              };
            }
            return api;
          };
          // user removes AAPL from their list — local intent is now [NVDA]
          var mergePayloads = [];
          var installBoundMergeSpy = function (value) {
            var realMerge = value.merge;
            value.merge = function (blob) {
              mergePayloads.push(blob);
              return realMerge.apply(value, arguments);
            };
          };
          window.WL = {merge: function () {}};
          installBoundMergeSpy(window.WL);
          document.addEventListener('wl-list-change', function (e) {
            window.WL = {getBlob: function () {
              return {items: [{t: 'NVDA'}]};
            }};
            installBoundMergeSpy(window.WL);
          });
          return WS.symbols.push('L-W', ['NVDA']).then(function () {
            var sync = readSyncBlob('L-W');
            // Snapshot the cloud BEFORE the pull/retry — the retry below will
            // DELETE AAPL on success, so reading `symbolsOf` after pull would
            // show the post-retry state, not the post-fail state.
            var syncedAtFail = symbolsOf(db, 'L-W');
            // Keep the override ACTIVE for the pull — the spec says the
            // pull-start retry runs AND the merge must exclude tombstoned
            // symbols. If the retry succeeds here, both the filter AND the
            // tombstone are exercised trivially (the cloud is clean by the
            // time the merge runs); keeping the override active makes the
            // retry fail too, so the merge has to actually exclude via the
            // tombstone filter — the property this test pins.
            return WS.pull().then(function () {
              var afterPull = readSyncBlob('L-W');
              var blobItems = (window.WL && window.WL.getBlob
                               ? window.WL.getBlob().items.map(function (i) { return i.t; })
                               : []);
              // Now restore the working client and dispatch `online` so the
              // retry actually lands (spec (2) trigger (a)).
              db.client.from = realFrom;
              window.dispatchEvent(new CustomEvent('online'));
              return wait(300).then(function () {
                var finalSaves = wsSaves();
                var afterRetry = readSyncBlob('L-W');
                var synced = symbolsOf(db, 'L-W');
                restoreChipSpy();
                OUT({tombstoneAfterFail: (sync && sync.tombstones) || {},
                     syncedAfterFail: syncedAtFail,
                     tombstoneAfterPull: (afterPull && afterPull.tombstones) || {},
                     blobAfterPull: blobItems,
                     mergePayloads: mergePayloads,
                     syncedAfterRetry: synced,
                     tombstoneAfterRetry: (afterRetry && afterRetry.tombstones) || {},
                     finalSaves: finalSaves});
              });
            });
          });
        });
        """,
        {"USER": USER},
    )
    # The tombstone is recorded per-list-per-symbol, scoped to L-W.
    assert out["tombstoneAfterFail"] is not None
    assert "L-W" in out["tombstoneAfterFail"], "tombstone must be list-scoped"
    assert "AAPL" in out["tombstoneAfterFail"]["L-W"], \
        "tombstone must name the removed symbol"
    # NVDA is not tombstoned (it was not part of the failed delete).
    assert "NVDA" not in out["tombstoneAfterFail"].get("L-W", {})
    # Cloud row still present (the DELETE failed) — tombstone is what protects us.
    assert out["syncedAfterFail"] == ["AAPL", "NVDA"], \
        "failed DELETE leaves the cloud row intact"
    # After pull(), the tombstone is still present and the cloud→local merge
    # did NOT resurrect AAPL.
    assert out["tombstoneAfterPull"] == out["tombstoneAfterFail"], \
        "tombstone survives the merge (the merge must not erase it)"
    assert "AAPL" not in out["blobAfterPull"], \
        f"the merge must EXCLUDE tombstoned symbols; blob has {out['blobAfterPull']}"
    assert out["mergePayloads"], "pull() must hand the filtered cloud rows to WL.merge"
    mergeSymbols = [item.get("t") for payload in out["mergePayloads"] for item in payload.get("items", [])]
    assert "AAPL" not in mergeSymbols, \
        f"the rows handed to WL.merge must exclude tombstoned symbols; got {mergeSymbols}"
    # The `online` retry ran the DELETE and the tombstone is now cleared.
    assert (out["tombstoneAfterRetry"] or {}) == {}, \
        f"successful DELETE must clear the tombstone; got {out['tombstoneAfterRetry']}"
    assert out["syncedAfterRetry"] == ["NVDA"], \
        f"DELETE success must remove the cloud row; got {out['syncedAfterRetry']}"


@needs_node
def test_T4_markers_and_tombstones_are_list_scoped_and_dropped_on_signout():
    """Spec (2) per-list + spec (3) list-scoped tombstone + the auth-transition
    law that the rest of watchstore.js's account-scoped state obeys. A signed-in
    failure on list A must not leak into list B, and a sign-out must clear
    every marker + tombstone together with the existing cloud-side reset."""
    out = _ws(
        CHIP_SPY + SYNC_BLOB + """
        installChipSpy();
        var db = makeDb({watchlists: [
                           {id: 'L-AI', user_id: 'u1', name: 'AI', position: 0},
                           {id: 'L-GOLD', user_id: 'u1', name: 'Gold Miners', position: 1}],
                         watchlist_symbols: [
                           {id: 's1', watchlist_id: 'L-AI', symbol: 'NVDA', position: 0},
                           {id: 's2', watchlist_id: 'L-GOLD', symbol: 'NEM', position: 0}]});
        WS._setTestSession(USER, db.client);
        Promise.all([WS.symbols.list('L-AI'), WS.symbols.list('L-GOLD')]).then(function () {
          var realFrom = db.client.from;
          // fail BOTH the push insert AND the push delete so each list gets a
          // pendingPushes marker AND a tombstone. Replace `insert` / `delete`
          // with no-ops so the FAKE_DB does NOT mutate db.tables before the
          // terminal rejects (its `insert()` pushes rows eagerly, before
          // `__run`). The chain (`.insert()/delete()` + `.eq().in().then(...)`)
          // stays intact and only the final result rejects.
          db.client.from = function (table) {
            var api = realFrom(table);
            if (table === 'watchlist_symbols') {
              api.insert = function () { return api; };
              api.delete = function () { return api; };
              api.__run = function () {
                return Promise.resolve({data: null, error: {code: '42501', message: 'rls denied'}});
              };
            }
            return api;
          };
          return WS.symbols.push('L-AI', ['NVDA', 'GOOGL']).then(function () {
            return WS.symbols.push('L-GOLD', []).then(function () {
              // Each list has its own per-list cache; read both and merge
              // their outbox state so the assertions see both lists' markers.
              var aiSync = readSyncBlob('L-AI');
              var goldSync = readSyncBlob('L-GOLD');
              var before = {
                pendingPushes: Object.assign({}, (aiSync && aiSync.pendingPushes) || {},
                                              (goldSync && goldSync.pendingPushes) || {}),
                tombstones: Object.assign({}, (aiSync && aiSync.tombstones) || {},
                                          (goldSync && goldSync.tombstones) || {})
              };
              db.client.from = realFrom;
              // sign out via the canonical onAuthUser — the same seam the
              // auth-transition tests use — so we exercise the real reset path.
              WS.onAuthUser(null);
              var aiAfter = readSyncBlob('L-AI');
              var goldAfter = readSyncBlob('L-GOLD');
              var after = {
                pendingPushes: Object.assign({}, (aiAfter && aiAfter.pendingPushes) || {},
                                              (goldAfter && goldAfter.pendingPushes) || {}),
                tombstones: Object.assign({}, (aiAfter && aiAfter.tombstones) || {},
                                          (goldAfter && goldAfter.tombstones) || {})
              };
              restoreChipSpy();
              OUT({before: before, after: after});
            });
          });
        });
        """,
        {"USER": USER},
    )
    # Both lists have markers / tombstones pre-signout, each list-scoped.
    assert out["before"].get("pendingPushes", {}).get("L-AI") is not None
    assert out["before"].get("pendingPushes", {}).get("L-GOLD") is not None
    assert out["before"].get("tombstones", {}).get("L-AI", {}) == {}
    assert "NEM" in out["before"].get("tombstones", {}).get("L-GOLD", {}), \
        "NEM was already absent from the local set; the empty-push tombstoned it"
    # Sign-out cleared every marker and every tombstone — these are
    # account-scoped state, like the rest of the auth-transition law.
    assert out["after"].get("pendingPushes", {}) == {}
    assert out["after"].get("tombstones", {}) == {}
    assert out["after"].get("pendingInserts", {}) == {}


@needs_node
def test_T5_failed_single_symbol_insert_is_retried_and_cleared_on_success():
    """A single-symbol write failure needs the same durable retry path as a
    full-list push: the marker survives while writes fail, then the online
    event retries the INSERT and clears it only after the write lands."""
    out = _ws(
        CHIP_SPY + SYNC_BLOB + """
        installChipSpy();
        var db = makeDb({watchlists: [{id: 'L-W', user_id: 'u1', name: 'Watchlist', position: 0}],
                         watchlist_symbols: [
                           {id: 'w1', watchlist_id: 'L-W', symbol: 'NVDA', position: 0}]});
        WS._setTestSession(USER, db.client);
        WS._setTestLists({activeId: 'L-W'});
        WS.symbols.list('L-W').then(function () {
          var realFrom = db.client.from;
          db.client.from = function (table) {
                var api = realFrom(table);
                if (table === 'watchlist_symbols') {
                  api.insert = function () {
                    return Promise.reject(new Error('rls denied'));
                  };
            }
            return api;
          };
          return WS.symbols.add('L-W', 'AAPL').catch(function () {
            var afterFail = readSyncBlob('L-W');
            db.client.from = realFrom;
            window.dispatchEvent(new CustomEvent('online'));
            return wait(250).then(function () {
              restoreChipSpy();
              OUT({failed: true,
                   pendingAfterFail: (afterFail && afterFail.pendingInserts) || {},
                   pendingAfterRetry: (readSyncBlob('L-W') || {}).pendingInserts || {},
                   saved: symbolsOf(db, 'L-W'),
                   saves: wsSaves()});
            });
          });
        });
        """,
        {"USER": USER},
    )
    assert "AAPL" in out["pendingAfterFail"].get("L-W", {}), out
    assert out["pendingAfterRetry"] == {}
    assert out["saved"] == ["AAPL", "NVDA"]
    assert "saved" in out["saves"]


@needs_node
def test_T6_sibling_list_outbox_markers_are_retried_after_reload_without_reading_it():
    """A reload intentionally loses `_touchedLists`; the durable per-list key is the
    only remaining discovery record. The first pull must find and retry a sibling
    failed INSERT and DELETE without first rendering that sibling list."""
    out = _ws(
        SYNC_BLOB + """
        localStorage.setItem('mdash.wl.L-SIB.v1', JSON.stringify({
          v: 1, updated: '2026-09-23T00:00:00.000Z',
          items: [{t: 'MSFT'}, {t: 'NEM'}], order: ['MSFT', 'NEM'], settings: {},
          pendingInserts: {'L-SIB': {AAPL: '2026-09-23T00:01:00.000Z'}},
          tombstones: {'L-SIB': {NEM: '2026-09-23T00:02:00.000Z'}}
        }));
        var db = makeDb({watchlists: [
          {id: 'L-ACTIVE', user_id: 'u1', name: 'Active', position: 0},
          {id: 'L-SIB', user_id: 'u1', name: 'Sibling', position: 1}],
          watchlist_symbols: [
            {id: 'a1', watchlist_id: 'L-ACTIVE', symbol: 'SPY', position: 0},
            {id: 's1', watchlist_id: 'L-SIB', symbol: 'MSFT', position: 0},
            {id: 's2', watchlist_id: 'L-SIB', symbol: 'NEM', position: 1}]});
        WS._setTestSession(USER, db.client);
        var siblingRead = false;
        var realFrom = db.client.from;
        db.client.from = function (table) {
          var api = realFrom(table);
          var realRun = api.__run;
          var __filters = [];
          api.__run = function () {
            if (table === 'watchlist_symbols' &&
                __filters.some(function (f) { return String(f.val) === 'L-SIB'; })) siblingRead = true;
            return realRun.apply(api, arguments);
          };
          ['eq', 'in'].forEach(function (method) {
            var real = api[method];
            api[method] = function (column, value) {
              __filters.push({column: column, value: value});
              return real.apply(api, arguments);
            };
          });
          return api;
        };
        WS.pull().then(function () {
          var marker = readSyncBlob('L-SIB') || {};
          OUT({active: symbolsOf(db, 'L-ACTIVE'),
               sibling: symbolsOf(db, 'L-SIB'),
               siblingRead: siblingRead,
               inserts: db.ops.filter(function (o) {
                 return o.kind === 'insert' && o.table === 'watchlist_symbols' &&
                   o.rows.some(function (r) { return r.watchlist_id === 'L-SIB'; });}).length,
               deletes: db.ops.filter(function (o) {
                 return o.kind === 'delete' && o.table === 'watchlist_symbols' &&
                   o.filters.some(function (f) { return String(f.val) === 'L-SIB'; });}).length,
               pendingInserts: marker.pendingInserts || {},
               tombstones: marker.tombstones || {}});
        });
        """,
        {"USER": USER},
    )
    assert out["sibling"] == sorted(["AAPL", "MSFT"]), out
    assert out["inserts"] == 1, out
    assert out["deletes"] == 1, out
    assert out["siblingRead"] is False, "retry must not require reading the sibling list"
    assert out["pendingInserts"] == {}, out
    assert out["tombstones"] == {}, out


def test_public_ws_save_vocabulary_and_plain_fallback_copy_match_shipped_consumer():
    """The public event vocabulary is proven against the page that consumes it. This
    avoids coupling the product contract to WatchStore's private dispatch aliases."""
    import re

    store = WATCHSTORE.read_text()
    consumer = WATCHLIST.read_text()
    mapping = store[store.index("var CHIP_STATE ="):store.index("var lastChip")]
    emitted = set(re.findall(r":\s*'([^']+)'", mapping))
    listener = consumer[consumer.index("document.addEventListener('ws-save'"):consumer.index("document.addEventListener('pf-save'")]
    assert "if (e && e.detail && e.detail.state) setChip(e.detail.state, 'watchlists');" in listener
    assert "function setChip(state, scope) {" in consumer
    assert "if (!CHIP[state]) return;" in consumer
    chip = consumer[consumer.index("var CHIP = {"):consumer.index("var chipState")]
    expected = {
        "clean": ("Up to date", "已是最新"),
        "saved": ("Saved", "已保存"),
        "saving": ("Saving…", "保存中…"),
        "failed": ("Change not saved", "更改未保存"),
    }
    for state, (english, chinese) in expected.items():
        block = re.search(
            r"\b%s:\s*\['is-[^']+',\s*'([^']+)',\s*'([^']+)'," % state, chip
        )
        assert block, state
        assert (block.group(1), block.group(2)) == (english, chinese)
    assert emitted == {"saved", "saving", "clean", "local", "offline"}
