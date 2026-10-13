"""tests/test_fif_watchstore_designated_list_js.py — the X2-n designated-list
helper in templates/watchstore.js (seat ruling R2).

Node-shelled against the SAME recording Supabase double as
tests/test_watchstore_multilist_js.py (harness imported from there). Pins:

  1. LAZY creation: findList() NEVER creates — an absent designated list is a
     null result with zero insert statements; only the explicit ensure/watch
     call creates the list.
  2. IDEMPOTENT ensure: a second ensureList() over an existing list performs
     no create (the unique (user_id, name) race is adopted, never duplicated).
  3. unwatch removes exactly that symbol (removal IS the unsubscribe).
  4. lookup by the VERBATIM stored name when no kind/system column exists
     (census C2): an exact-name list matches; a different-case name does not.
  5. ZERO network when signed out: every fif call rejects and the double
     records no statements.
"""
from __future__ import annotations

import json

import pytest

from tests.test_watchstore_multilist_js import (  # noqa: F401  (harness reuse)
    HAS_NODE,
    _ws,
    needs_node,
    USER,
)

FIF_NAME = "Filing Forensics"


def _symbols_of(db_tables: dict, list_id: str) -> list:
    return sorted(
        row["symbol"]
        for row in db_tables["watchlist_symbols"]
        if str(row["watchlist_id"]) == str(list_id)
    )


# ===========================================================================
# 1 — lazy creation: find() never creates
# ===========================================================================
@needs_node
def test_find_never_creates_the_list():
    out = _ws(
        """
        var db = makeDb({watchlists: [
          {id: 'L-OTHER', user_id: 'u1', name: 'My Watchlist', position: 0}
        ], watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        WS.fif.findList().then(function (found) {
          OUT({found: !!found,
               lists: db.tables.watchlists.map(function (l) { return l.name; }),
               inserts: db.ops.filter(function (o) { return o.kind === 'insert'; }).length});
        });
        """
        , {"USER": USER},
    )
    assert out == {"found": False, "lists": ["My Watchlist"], "inserts": 0}


# ===========================================================================
# 2 — idempotent ensure
# ===========================================================================
@needs_node
def test_ensure_is_lazy_and_idempotent():
    out = _ws(
        """
        var db = makeDb({watchlists: [], watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        WS.fif.ensureList().then(function (a) {
          return WS.fif.ensureList().then(function (b) {
            OUT({a: a.name, b: b.name, sameId: String(a.id) === String(b.id),
                 count: db.tables.watchlists.length,
                 names: db.tables.watchlists.map(function (l) { return l.name; })});
          });
        });
        """
        , {"USER": USER},
    )
    assert out["names"] == [FIF_NAME]
    assert out["count"] == 1
    assert out["a"] == FIF_NAME and out["b"] == FIF_NAME
    assert out["sameId"] is True


@needs_node
def test_watch_ensures_then_adds_and_is_read_first():
    out = _ws(
        """
        var db = makeDb({watchlists: [], watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        WS.fif.watch('smci').then(function (r1) {
          return WS.fif.watch('SMCI').then(function (r2) {
            var lid = r1.list.id;
            OUT({listName: r1.list.name,
                 symbols: db.tables.watchlist_symbols
                   .filter(function (s) { return String(s.watchlist_id) === String(lid); })
                   .map(function (s) { return s.symbol; }),
                 skipped: !!(r2.result && r2.result.skipped),
                 upper: r2.result && r2.result.symbol,
                 listCount: db.tables.watchlists.length});
          });
        });
        """
        , {"USER": USER},
    )
    # the ticker is normalized to upper case; the second watch of the SAME
    # name is a membership skip (read-first), never a duplicate row
    assert out["listName"] == FIF_NAME
    assert out["symbols"] == ["SMCI"]
    assert out["skipped"] is True and out["upper"] == "SMCI"
    assert out["listCount"] == 1


# ===========================================================================
# 3 — unwatch removes the symbol (the unsubscribe)
# ===========================================================================
@needs_node
def test_unwatch_removes_exactly_that_symbol():
    extra = {"SEED": {
        "watchlists": [
            {"id": "L-FIF", "user_id": "u1", "name": FIF_NAME, "position": 0},
            {"id": "L-AI", "user_id": "u1", "name": "AI", "position": 1},
        ],
        "watchlist_symbols": [
            {"id": "s1", "watchlist_id": "L-FIF", "symbol": "SMCI", "position": 0},
            {"id": "s2", "watchlist_id": "L-FIF", "symbol": "AAPL", "position": 1},
            {"id": "s3", "watchlist_id": "L-AI", "symbol": "NVDA", "position": 0},
        ],
    }}
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        WS.fif.unwatch('SMCI').then(function (r) {
          OUT({removed: r.removed,
               fif: db.tables.watchlist_symbols
                 .filter(function (s) { return s.watchlist_id === 'L-FIF'; })
                 .map(function (s) { return s.symbol; }).sort(),
               sibling: db.tables.watchlist_symbols
                 .filter(function (s) { return s.watchlist_id === 'L-AI'; })
                 .map(function (s) { return s.symbol; }).sort(),
               listStillThere: db.tables.watchlists.length});
        });
        """
        , dict(extra, USER=USER),
    )
    assert out["removed"] is True
    assert out["fif"] == ["AAPL"]          # only the named symbol left the designated list
    assert out["sibling"] == ["NVDA"]      # a sibling list is untouched
    assert out["listStillThere"] == 2


@needs_node
def test_unwatch_without_a_list_never_creates_to_delete():
    out = _ws(
        """
        var db = makeDb({watchlists: [], watchlist_symbols: []});
        WS._setTestSession(USER, db.client);
        WS.fif.unwatch('SMCI').then(function (r) {
          OUT({removed: r.removed, lists: db.tables.watchlists.length,
               inserts: db.ops.filter(function (o) { return o.kind === 'insert'; }).length});
        });
        """
        , {"USER": USER},
    )
    assert out == {"removed": False, "lists": 0, "inserts": 0}


# ===========================================================================
# 4 — lookup by verbatim name (no kind column exists — census C2)
# ===========================================================================
@needs_node
def test_lookup_is_exact_case_sensitive_name():
    extra = {"SEED": {
        "watchlists": [
            {"id": "L-CASE", "user_id": "u1", "name": "filing forensics", "position": 0},
        ],
        "watchlist_symbols": [],
    }}
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        WS.fif.findList().then(function (found) {
          OUT({found: !!found, inserts: db.ops.filter(function (o) {
            return o.kind === 'insert'; }).length});
        });
        """
        , dict(extra, USER=USER),
    )
    # the schema's unique (user_id, name) index is case-sensitive: a
    # different-case list is a DIFFERENT list, never a match, and never
    # silently created either
    assert out == {"found": False, "inserts": 0}


@needs_node
def test_is_watched_reads_membership_through_the_server_read():
    extra = {"SEED": {
        "watchlists": [
            {"id": "L-FIF", "user_id": "u1", "name": FIF_NAME, "position": 0},
        ],
        "watchlist_symbols": [
            {"id": "s1", "watchlist_id": "L-FIF", "symbol": "SMCI", "position": 0},
        ],
    }}
    out = _ws(
        """
        var db = makeDb(SEED);
        WS._setTestSession(USER, db.client);
        WS.fif.isWatched('SMCI').then(function (yes) {
          return WS.fif.isWatched('TSLA').then(function (no) {
            OUT({yes: yes, no: no,
                 lists: db.tables.watchlists.length});
          });
        });
        """
        , dict(extra, USER=USER),
    )
    assert out == {"yes": True, "no": False, "lists": 1}


# ===========================================================================
# 5 — zero network when signed out
# ===========================================================================
@needs_node
def test_signed_out_is_zero_network():
    out = _ws(
        """
        var db = makeDb({watchlists: [], watchlist_symbols: []});
        // NO _setTestSession: signed out.
        WS.fif.findList().then(function () {
          OUT({unexpected: 'resolved'});
        }, function (err) {
          var name = String(err && err.message || err);
          WS.fif.watch('SMCI').then(function () {
            OUT({unexpected: 'resolved'});
          }, function (err2) {
            WS.fif.isWatched('SMCI').then(function (v) {
              OUT({unexpected: 'resolved-with-' + v});
            }, function (err3) {
              OUT({rejected: [name,
                              String(err2 && err2.message || err2),
                              String(err3 && err3.message || err3)].sort(),
                   statements: db.ops.length,
                   lists: db.tables.watchlists.length,
                   symbols: db.tables.watchlist_symbols.length});
            });
          });
        });
        """
        , {"USER": USER},
    )
    assert "no-session" in json.dumps(out["rejected"])
    assert out["statements"] == 0
    assert out["lists"] == 0 and out["symbols"] == 0
