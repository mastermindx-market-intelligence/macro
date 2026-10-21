"""tests/test_watchstore_sector_investigations_js.py — SIC-I07R saved sector
investigations through the EXISTING watch/save owner (masterplan §8.4, P17).

Seat decision under test: a saved sector investigation is ONE `watchlist_symbols`
row `{symbol: <SPDR ETF ticker>, section: 'si'}` inside the user's dedicated list
named exactly `Sector Intelligence` — created lazily through the existing
list-create path, unique per (user_id, name). No new store, table, column or
notification transport; the question/snapshot/origin are device-local only, in
the existing local item `note` (the recorded cross-device GAP).

Pinned here:

  1. the static contract: both public API names, the list-name constant, the
     section literal 'si', NO new localStorage key, the `from('` table set
     unchanged, and no sentinel/alerts reference introduced by the wave.
  2. the dedicated list is minted lazily and ordered behind the primary, so it
     can never capture the page's default bind (the FIF designated-list law,
     restated for this second designated list).
  3. readback comes from the store — cloud rows filtered by section when signed
     in (the shared symbolsFetch() does NOT filter by section, so this read is
     what keeps an investigation row from being reported as, or leaked into,
     any other list), the anonymous local blob signed out. Never a cache of
     the click.
  4. idempotency: a second save of the same ETF updates the device-local note
     and never mints a second row (no unique index guards (watchlist_id,
     symbol), so the save is read-first).
  5. account isolation is the owner's existing user_id scoping; a signed-in
     session is never routed to the anonymous blob.

Same harness as tests/test_watchstore_multilist_js.py: the module is a browser
IIFE, node-shelled behind minimal window/document/localStorage stubs with
readyState 'loading' so init() never runs and only the store logic is exercised.
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
WATCHLIST_J2 = ROOT / "templates" / "watchlist.html.j2"

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
"""

# The recording Supabase double from tests/test_watchstore_multilist_js.py — it
# models the tables as real row arrays and REPLAYS the query builder, so a read
# that forgets its user_id or section filter genuinely returns the other rows.
FAKE_DB = """
function makeDb(seed, opts) {
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

# the storage-key literals the store already owned BEFORE this wave (RECEIVER
# CONTRACTS §Watch/save State). The wave must add none.
BASE_STORAGE_KEYS = {
    "mdash.pf.v1",
    "mdash.watchlist.v1",
    "mdash.watchstore.folded.v1",
    "mdash.watchstore.pf_folded.v1",
    "mdash.wl.",
}

# every Supabase table the store reads or writes (the `from('` set)
BASE_TABLES = {"watchlists", "watchlist_symbols", "portfolio_positions"}


def _run(js_body: str, extra: dict | None = None) -> dict:
    globs = "\n".join("var %s = %s;" % (k, json.dumps(v)) for k, v in (extra or {}).items())
    script = SHIM + "\n" + FAKE_DB + "\n" + globs + "\n" + textwrap.dedent(js_body)
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, f"node failed:\nSTDERR:\n{res.stderr}\nSTDOUT:\n{res.stdout}"
    assert res.stdout.strip(), f"no stdout; stderr:\n{res.stderr}"
    return json.loads(res.stdout)


def _ws(js_body: str, extra: dict | None = None) -> dict:
    return _run("var WS = require(%s);\n%s" % (json.dumps(str(WATCHSTORE)), js_body), extra)


# ===========================================================================
# 1. static contract — names, literals, no new key/table, no sentinel reference
# ===========================================================================
def test_both_public_api_names_are_exported_on_the_store():
    src = WATCHSTORE.read_text(encoding="utf-8")
    for name in ("saveSectorInvestigation", "listSectorInvestigations"):
        assert re.search(r"^\s{4}%s:\s*%s," % (name, name), src, re.M), (
            f"window.WatchStore.{name} is not exported"
        )


def test_list_name_constant_and_section_literal_are_frozen():
    src = WATCHSTORE.read_text(encoding="utf-8")
    assert re.search(r"var SI_LIST_NAME = 'Sector Intelligence';", src)
    assert re.search(r"var SI_SECTION = 'si';", src)
    # the row the save writes carries the section literal, not SECTION ('Watchlist')
    m = re.search(
        r"insert\(\{ watchlist_id: listId, symbol: t, section: SI_SECTION, position:", src)
    assert m, "the investigation insert must write section: SI_SECTION ('si')"


def test_no_new_localstorage_key():
    src = WATCHSTORE.read_text(encoding="utf-8")
    found = set(re.findall(r"'(mdash\.[A-Za-z0-9._]*)'", src))
    assert found == BASE_STORAGE_KEYS, (
        f"storage-key literals changed: +{sorted(found - BASE_STORAGE_KEYS)} "
        f"-{sorted(BASE_STORAGE_KEYS - found)}"
    )


def test_supabase_from_set_is_unchanged():
    src = WATCHSTORE.read_text(encoding="utf-8")
    found = set(re.findall(r"\.from\('([^']+)'\)", src))
    assert found == BASE_TABLES, (
        f"from(' table set changed: +{sorted(found - BASE_TABLES)} "
        f"-{sorted(BASE_TABLES - found)}"
    )


def test_the_wave_adds_no_sentinel_or_alerts_reference():
    """The saved investigation is a symbol row, full stop: nothing in the two
    client stores may reach for the nightly scanner or an alerts surface. The
    one pre-existing 'alerts' in watchlist.js is the signed-out drawer CTA
    ('Save + get alerts — Free'), which predates this wave — the count pins that
    the wave added none beyond it."""
    for path in (WATCHSTORE, WATCHLIST):
        src = path.read_text(encoding="utf-8")
        assert "watchlist_sentinel" not in src, f"{path.name} references watchlist_sentinel"
    ws = WATCHSTORE.read_text(encoding="utf-8")
    assert "alerts" not in ws, "watchstore.js references alerts"
    wl = WATCHLIST.read_text(encoding="utf-8")
    assert wl.count("alerts") == 1 and "Save + get alerts" in wl


def test_cloud_reads_of_the_shared_store_do_not_filter_by_section():
    """Reported fact, pinned: the owner's shared symbolsFetch() selects
    `symbol, position, created_at` and filters only by watchlist_id — section is
    neither selected nor filtered. Investigation rows therefore live ONLY in the
    dedicated list; this wave's own read (siRowsFetch) is the one that filters."""
    src = WATCHSTORE.read_text(encoding="utf-8")
    shared = re.search(
        r"function symbolsFetch\(listId\) \{.*?\.eq\('watchlist_id', listId\)", src, re.S)
    assert shared, "symbolsFetch not found"
    assert "section" not in shared.group(0)
    si = re.search(r"function siRowsFetch\(listId\) \{.*?\.eq\('section', SI_SECTION\)", src, re.S)
    assert si, "siRowsFetch must filter its read by section"


# ===========================================================================
# 2. lazy create, ordering, and the default bind
# ===========================================================================
@needs_node
def test_save_creates_the_dedicated_list_lazily_behind_the_primary():
    out = _ws(
        """
        var db = makeDb({watchlists: [], watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        WS.saveSectorInvestigation({etf: 'XLK', note: 'semi capex question'}).then(function (r) {
          var si = db.tables.watchlists.filter(function (l) {
            return l.name === 'Sector Intelligence'; })[0];
          var wl = db.tables.watchlists.filter(function (l) {
            return l.name === 'Watchlist'; })[0];
          OUT({names: db.tables.watchlists.map(function (l) { return l.name; }),
               wlPos: wl && wl.position, siPos: si && si.position,
               saved: r, rows: db.tables.watchlist_symbols.map(function (s) {
                 return {list: s.watchlist_id, symbol: s.symbol, section: s.section}; })});
        });
        """
        , {"USER": USER},
    )
    # nothing exists until the first save; then 'Watchlist' is minted FIRST so
    # the designated list lands at position >= 1 (the FIF R1 law, restated).
    assert out["names"] == ["Watchlist", "Sector Intelligence"]
    assert out["wlPos"] == 0 and out["siPos"] >= 1
    assert out["saved"] == {"etf": "XLK", "listId": out["saved"]["listId"],
                            "synced": True, "skipped": False}
    si_rows = [r for r in out["rows"] if r["section"] == "si"]
    assert len(si_rows) == 1
    assert si_rows[0]["symbol"] == "XLK"
    assert si_rows[0]["list"] == out["saved"]["listId"]


@needs_node
def test_existing_dedicated_list_is_reused_and_never_renamed():
    out = _ws(
        """
        var db = makeDb({watchlists: [
          {id: 'L-W', user_id: 'u1', name: 'Watchlist', position: 0},
          {id: 'L-SI', user_id: 'u1', name: 'Sector Intelligence', position: 1}],
          watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        WS.saveSectorInvestigation({etf: 'XLE'}).then(function (r) {
          OUT({listId: r.listId, lists: db.tables.watchlists.length});
        });
        """
        , {"USER": USER},
    )
    assert out["listId"] == "L-SI"
    assert out["lists"] == 2      # no second list, no rename


@needs_node
def test_only_list_is_the_dedicated_one_pull_still_binds_watchlist():
    """resolveBoundList branch 2 must decline a designated cache: an account
    whose only list is 'Sector Intelligence' gets 'Watchlist' created and bound,
    so ordinary stars and full-membership diffs never target the investigations."""
    out = _ws(
        """
        var db = makeDb({watchlists: [
          {id: 'L-SI', user_id: 'u1', name: 'Sector Intelligence', position: 0}],
          watchlist_symbols: [
            {id: 's1', watchlist_id: 'L-SI', symbol: 'XLK', section: 'si', position: 0}]});
        WS._setTestSession(USER, db.client);
        WS.pull().then(function () {
          var st = WS._testState();
          OUT({names: db.tables.watchlists.map(function (l) { return l.name; }),
               bound: st.activeId,
               boundIsNotSi: String(st.activeId) !== 'L-SI',
               siSymbols: symbolsOf(db, 'L-SI')});
        });
        """
        , {"USER": USER},
    )
    assert out["names"] == ["Sector Intelligence", "Watchlist"]
    assert out["boundIsNotSi"] is True
    assert out["bound"] is not None
    assert out["siSymbols"] == ["XLK"]      # the pull did not import or delete it


# ===========================================================================
# 3. readback from the store — section-filtered cloud, local blob, isolation
# ===========================================================================
@needs_node
def test_readback_comes_from_cloud_rows_not_a_cache_of_the_click():
    """Rows seeded straight into the cloud (another device's saves) read back
    with no save ever made here — the read is a store read, and `added` is the
    cloud row's created_at."""
    out = _ws(
        """
        var db = makeDb({watchlists: [
          {id: 'L-W', user_id: 'u1', name: 'Watchlist', position: 0},
          {id: 'L-SI', user_id: 'u1', name: 'Sector Intelligence', position: 1}],
          watchlist_symbols: [
            {id: 's1', watchlist_id: 'L-SI', symbol: 'XLK', section: 'si',
             position: 0, created_at: '2026-10-01T00:00:00.000Z'},
            {id: 's2', watchlist_id: 'L-SI', symbol: 'XLE', section: 'si',
             position: 1, created_at: '2026-10-02T00:00:00.000Z'}]});
        WS._setTestSession(USER, db.client);
        WS.listSectorInvestigations().then(function (rows) {
          OUT({rows: rows, localWrites: __sets.filter(function (k) {
            return k.indexOf('mdash.') === 0; })});
        });
        """
        , {"USER": USER},
    )
    assert out["rows"] == [
        {"etf": "XLK", "added": "2026-10-01T00:00:00.000Z", "note": "", "synced": True},
        {"etf": "XLE", "added": "2026-10-02T00:00:00.000Z", "note": "", "synced": True},
    ]
    assert out["localWrites"] == []      # a read never persists anything


@needs_node
def test_readback_filters_by_section_inside_the_dedicated_list():
    """An ordinary 'Watchlist'-section row hand-added to the dedicated list (the
    switcher allows it) is NOT an investigation and must not be reported."""
    out = _ws(
        """
        var db = makeDb({watchlists: [
          {id: 'L-SI', user_id: 'u1', name: 'Sector Intelligence', position: 0}],
          watchlist_symbols: [
            {id: 's1', watchlist_id: 'L-SI', symbol: 'XLK', section: 'si', position: 0},
            {id: 's2', watchlist_id: 'L-SI', symbol: 'MSFT', section: 'Watchlist', position: 1}]});
        WS._setTestSession(USER, db.client);
        WS.listSectorInvestigations().then(function (rows) {
          OUT({etfs: rows.map(function (r) { return r.etf; })});
        });
        """
        , {"USER": USER},
    )
    assert out["etfs"] == ["XLK"]


@needs_node
def test_a_save_never_leaks_a_row_into_another_list():
    out = _ws(
        """
        var db = makeDb({watchlists: [
          {id: 'L-W', user_id: 'u1', name: 'Watchlist', position: 0},
          {id: 'L-G', user_id: 'u1', name: 'Gold Miners', position: 1}],
          watchlist_symbols: [
            {id: 'w1', watchlist_id: 'L-W', symbol: 'MSFT', section: 'Watchlist', position: 0}]});
        WS._setTestSession(USER, db.client);
        WS.saveSectorInvestigation({etf: 'XLK', note: 'q'}).then(function () {
          OUT({w: symbolsOf(db, 'L-W'), g: symbolsOf(db, 'L-G'),
               si: db.tables.watchlist_symbols.filter(function (s) {
                 return s.section === 'si'; }).map(function (s) { return s.symbol; })});
        });
        """
        , {"USER": USER},
    )
    assert out["w"] == ["MSFT"]
    assert out["g"] == []
    assert out["si"] == ["XLK"]


@needs_node
def test_readback_is_isolated_to_the_session_user():
    out = _ws(
        """
        var db = makeDb({watchlists: [
          {id: 'L-OTHER', user_id: 'u2', name: 'Sector Intelligence', position: 0}],
          watchlist_symbols: [
            {id: 'o1', watchlist_id: 'L-OTHER', symbol: 'XLF', section: 'si', position: 0}]});
        WS._setTestSession(USER, db.client);
        WS.listSectorInvestigations().then(function (rows) {
          OUT({rows: rows, otherListUntouched: symbolsOf(db, 'L-OTHER')});
        });
        """
        , {"USER": USER},
    )
    # u1 has no dedicated list: [] — u2's rows are invisible (user_id scoping)
    assert out["rows"] == []
    assert out["otherListUntouched"] == ["XLF"]


@needs_node
def test_no_dedicated_list_on_read_creates_nothing():
    out = _ws(
        """
        var db = makeDb({watchlists: [], watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        WS.listSectorInvestigations().then(function (rows) {
          OUT({rows: rows, lists: db.tables.watchlists.length});
        });
        """
        , {"USER": USER},
    )
    assert out["rows"] == []
    assert out["lists"] == 0      # never create on read


# ===========================================================================
# 4. idempotency + the device-local note
# ===========================================================================
@needs_node
def test_second_save_of_the_same_etf_updates_the_note_not_a_second_row():
    out = _ws(
        """
        var db = makeDb({watchlists: [], watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        WS.saveSectorInvestigation({etf: 'xlk', note: 'first question'}).then(function (a) {
          return WS.saveSectorInvestigation({etf: 'XLK', note: 'second question'}).then(function (b) {
            return WS.listSectorInvestigations().then(function (rows) {
              var si = db.tables.watchlists.filter(function (l) {
                return l.name === 'Sector Intelligence'; })[0];
              OUT({first: a, second: b,
                   siRows: db.tables.watchlist_symbols.filter(function (s) {
                     return String(s.watchlist_id) === String(si.id); }).length,
                   readback: rows});
            });
          });
        });
        """
        , {"USER": USER},
    )
    assert out["first"]["skipped"] is False and out["first"]["synced"] is True
    assert out["second"]["skipped"] is True       # idempotent on the cloud row
    assert out["siRows"] == 1
    assert out["readback"] == [
        {"etf": "XLK", "added": out["readback"][0]["added"],
         "note": "second question", "synced": True},
    ]
    assert out["readback"][0]["added"]            # created_at came through


@needs_node
def test_the_note_is_device_local_and_survives_a_sync_read():
    """cacheWrite preserves local item metadata (notes stay local by ruling), so
    a symbolsFetch of the dedicated list — what setActiveList/pull do — cannot
    erase the note the save wrote."""
    out = _ws(
        """
        var db = makeDb({watchlists: [], watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        WS.saveSectorInvestigation({etf: 'XLE', note: 'energy question'}).then(function (r) {
          return WS.symbols.list(r.listId).then(function () {
            return WS.listSectorInvestigations().then(function (rows) {
              var raw = JSON.parse(localStorage.getItem(WS.cacheKey(r.listId)));
              var cloudHasNoteColumn = db.tables.watchlist_symbols.some(function (s) {
                return 'note' in s; });
              OUT({note: rows[0] && rows[0].note, synced: rows[0] && rows[0].synced,
                   cloudHasNoteColumn: cloudHasNoteColumn});
            });
          });
        });
        """
        , {"USER": USER},
    )
    assert out["note"] == "energy question"
    assert out["synced"] is True
    assert out["cloudHasNoteColumn"] is False     # the schema holds no note


# ===========================================================================
# 5. signed-out store + the authority law
# ===========================================================================
@needs_node
def test_signed_out_save_reads_back_from_the_anonymous_local_blob():
    out = _ws(
        """
        // no _setTestSession: signed out. A plain star-save sits in the blob too.
        localStorage.setItem('mdash.watchlist.v1', JSON.stringify({
          v: 1, updated: '2026-10-01T00:00:00.000Z',
          items: [{t: 'MSFT', added: '2026-09-30T00:00:00.000Z', note: ''}],
          order: ['MSFT'], settings: {}}));
        WS.saveSectorInvestigation({etf: 'XLK', note: 'local question'}).then(function (r) {
          WS.listSectorInvestigations().then(function (rows) {
            var b = JSON.parse(localStorage.getItem('mdash.watchlist.v1'));
            OUT({saved: r, rows: rows,
                 blobItems: b.items.map(function (i) { return [i.t, i.note]; }),
                 keys: Object.keys(__store).sort()});
          });
        });
        """
    )
    assert out["saved"] == {"etf": "XLK", "synced": False}
    # the anonymous item carries the note; the star-save keeps its empty note
    assert out["blobItems"] == [["MSFT", ""], ["XLK", "local question"]]
    # readback reports ONLY the note-bearing investigation, synced: false
    assert out["rows"] == [{"etf": "XLK", "added": out["rows"][0]["added"],
                            "note": "local question", "synced": False}]
    assert out["rows"][0]["added"]
    # no new storage key: the anonymous blob is the only thing touched
    assert out["keys"] == ["mdash.watchlist.v1"]


@needs_node
def test_a_signed_in_session_is_never_routed_to_the_anonymous_blob():
    """A1A authority law: signed-in means cloud authority. With the client
    unavailable the save REJECTS (no-session) instead of silently forking into
    the anonymous local blob."""
    out = _ws(
        """
        WS._setTestSession(USER, null);   // user set, client dead
        WS.saveSectorInvestigation({etf: 'XLK', note: 'q'}).then(function (r) {
          OUT({resolved: r});
        }, function (e) {
          OUT({rejected: String(e && e.message || e),
               anonymousUntouched: localStorage.getItem('mdash.watchlist.v1') === null});
        });
        """
        , {"USER": USER},
    )
    assert "no-session" in out["rejected"]
    assert out["anonymousUntouched"] is True


# ===========================================================================
# 6. RI07 finding 2 — a note saved signed-out survives the sign-in fold
# ===========================================================================
@needs_node
def test_signed_out_save_folds_into_the_dedicated_list_on_sign_in():
    """RI07 finding 2, reproduced end to end: a question saved signed-out sat in
    the anonymous `mdash.watchlist.v1` blob, and pull()'s one-shot fold delivered
    it into the plain 'Watchlist' as a bare ticker — so listSectorInvestigations()
    (a section-filtered read of the DEDICATED list) returned [] and the note was
    orphaned. The fold must capture the full local item and route investigations
    through siEnsureList + _siInsert + _siNoteWrite; ordinary stars keep the
    ordinary fold."""
    out = _ws(
        """
        // signed out: one ordinary star, one saved investigation
        localStorage.setItem('mdash.watchlist.v1', JSON.stringify({
          v: 1, updated: '2026-10-01T00:00:00.000Z',
          items: [{t: 'MSFT', added: '2026-09-30T00:00:00.000Z', note: ''}],
          order: ['MSFT'], settings: {}}));
        WS.saveSectorInvestigation({etf: 'XLE', note: 'energy question'}).then(function () {
          // sign in on the same device: the page still holds the anonymous blob
          global.window.WL = {
            getBlob: function () { return JSON.parse(localStorage.getItem('mdash.watchlist.v1')); },
            merge: function () { return 0; }
          };
          var db = makeDb({watchlists: [], watchlist_symbols: []});
          WS._setTestSession(USER, db.client);
          return WS.pull().then(function () {
            return WS.listSectorInvestigations().then(function (rows) {
              var si = db.tables.watchlists.filter(function (l) {
                return l.name === 'Sector Intelligence'; })[0];
              var wl = db.tables.watchlists.filter(function (l) {
                return l.name === 'Watchlist'; })[0];
              OUT({rows: rows,
                   plainFold: symbolsOf(db, wl && wl.id).sort(),
                   siFold: symbolsOf(db, si && si.id).sort(),
                   marker: localStorage.getItem('mdash.watchstore.folded.v1')});
            });
          });
        });
        """
        , {"USER": USER},
    )
    # the investigation is in the DEDICATED list, note intact — not orphaned
    assert out["rows"] == [{"etf": "XLE", "added": out["rows"][0]["added"],
                            "note": "energy question", "synced": True}]
    assert out["rows"][0]["added"]
    assert out["siFold"] == ["XLE"]
    # the ordinary star keeps the ordinary fold into the plain 'Watchlist'
    assert out["plainFold"] == ["MSFT"]
    assert out["marker"] == "1"          # the one-shot fold ran and completed


@needs_node
def test_fold_routes_on_the_section_stamp_and_nothing_else():
    """The fold's discriminator is the `section: 'si'` stamp, and it is the ONLY
    one: an ordinary item that carries a user note ('my note' — notes are a
    first-class field of ordinary items, local by ruling) keeps the ordinary
    Watchlist fold. The RI07 packet's alternative arm (route any non-empty note
    to the dedicated list) is contradicted by that pinned owner behavior
    (tests/test_watchstore_multilist_js.py, the R1 branch-2 end-to-end) and is
    reported as a deviation rather than taken."""
    out = _ws(
        """
        global.window.WL = {
          getBlob: function () { return {
            v: 1, updated: '2026-10-01T00:00:00.000Z',
            items: [{t: 'XLF', added: '2026-09-28T00:00:00.000Z', note: 'banks question',
                     section: 'si'},
                    {t: 'AAPL', added: '2026-09-29T00:00:00.000Z', note: 'my note'}],
            order: ['XLF', 'AAPL'], settings: {}}; },
          merge: function () { return 0; }
        };
        var db = makeDb({watchlists: [], watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        WS.pull().then(function () {
          return WS.listSectorInvestigations().then(function (rows) {
            OUT({rows: rows,
                 landed: db.tables.watchlist_symbols.map(function (s) {
                   return [s.symbol, s.section]; }).sort()});
          });
        });
        """
        , {"USER": USER},
    )
    assert out["rows"] == [{"etf": "XLF", "added": out["rows"][0]["added"],
                            "note": "banks question", "synced": True}]
    # XLF landed as the investigation row; AAPL kept the ordinary fold, note and all
    assert out["landed"] == [["AAPL", "Watchlist"], ["XLF", "si"]]


@needs_node
def test_the_signed_out_note_signature_storage_shape_is_pinned():
    """RI07 note: the signed-out readback's whole authority is the anonymous item
    shape — an investigation is `note` non-empty (what listSectorInvestigations
    filters on signed out), now stamped `section: 'si'` (what the sign-in fold
    routes on). Pin the exact keys so a future writer cannot silently break
    either half: the star-save keeps the three-key shape, the save adds the
    section key and nothing else."""
    out = _ws(
        """
        localStorage.setItem('mdash.watchlist.v1', JSON.stringify({
          v: 1, updated: '2026-10-01T00:00:00.000Z',
          items: [{t: 'MSFT', added: '2026-09-30T00:00:00.000Z', note: ''}],
          order: ['MSFT'], settings: {}}));
        WS.saveSectorInvestigation({etf: 'XLK', note: 'q'}).then(function () {
          var b = JSON.parse(localStorage.getItem('mdash.watchlist.v1'));
          OUT({star: b.items[0], saved: b.items[1]});
        });
        """
    )
    assert out["star"] == {"t": "MSFT", "added": "2026-09-30T00:00:00.000Z", "note": ""}
    assert out["saved"] == {"t": "XLK", "added": out["saved"]["added"],
                            "note": "q", "section": "si"}
    assert out["saved"]["added"]


# ===========================================================================
# 7. the page side — chip, dossier link, device-local disclosure (static)
# ===========================================================================
def test_the_dedicated_lists_rows_carry_a_chip_that_links_the_dossier():
    src = WATCHLIST.read_text(encoding="utf-8")
    # the chip is gated on the ACTIVE list being the dedicated one
    assert re.search(r"function isActiveSiList\(\)", src)
    # it reuses the page's existing pill grammar and links sectors/<ETF>.html
    m = re.search(
        r"function siChipHTML\(t\) \{\s*"
        r"return '<a class=\"ws-chip si-chip\" href=\"sectors/' \+ esc\(t\) \+ '\.html\">'",
        src)
    assert m, "siChipHTML must render a .ws-chip anchor to sectors/<ETF>.html"
    # the row component emits it only inside the dedicated list
    assert re.search(r"isActiveSiList\(\) \? siChipHTML\(r\.t\) : ''", src)


def test_the_readback_states_the_device_local_limit():
    src = WATCHLIST.read_text(encoding="utf-8")
    m = re.search(r"if \(isActiveSiList\(\)\) parts\.push", src)
    assert m, "the facts strip must disclose the device-local note limit"


def test_the_template_bakes_the_chip_strings_only():
    src = WATCHLIST_J2.read_text(encoding="utf-8")
    m = re.search(r"window\.WL_SI_COPY = \{(.*?)\};", src, re.S)
    assert m, "watchlist.html.j2 bakes no window.WL_SI_COPY"
    block = m.group(1)
    assert re.search(r"chip:\s*\{ en: 'Sector investigation', zh: '板块情报' \}", block)
    assert re.search(r"device:\s*\{ en: 'Notes are saved on this device", block)
    assert "sync" in block or "同步" in block
    # the fallback halves in watchlist.js keep a stale bake honest
    js = WATCHLIST.read_text(encoding="utf-8")
    assert "window.WL_SI_COPY" in js
    assert "'Sector investigation'" in js
