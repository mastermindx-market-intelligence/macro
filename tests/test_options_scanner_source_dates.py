"""Reject future row dates as the Scanner's own snapshot reference.

Execute the template's real rendering, lag, and sorting functions. Presentation
helpers are inert here; no browser, store, provider, or wall clock is consulted.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import unittest


TEMPLATE = Path(__file__).resolve().parents[1] / "templates/options.html.j2"


def _scanner_dates(target: str | None, rows: list[dict]) -> dict:
    source = TEMPLATE.read_text(encoding="utf-8")
    sections = [
        ("function esc(s){", "function lvl(v){"),
        ("function sourceDay(value){", "function promotePanelDates(host){"),
        ("function rowLagDays(rowAsof, freshest){", "function scPresetFilter(rows){"),
        ("function scSortRows(rows){", "function scVisibleRows(){"),
        ("function renderScanner(host, payload){", "/* ══════════ TICKER"),
    ]
    functions = "\n".join(source[source.index(start):source.index(end, source.index(start))]
                          for start, end in sections)
    driver = ("var window={OEW_TARGET_SESSION:" + json.dumps(target) + "};\n"
              + "var rows=" + json.dumps(rows) + ";\n" + functions + r"""
var SC_PRESETS = [], scPreset = 'premium', scRows = [], scSkew75 = null;
var scAsof = null, scSort = {key:'asof', dir:'desc'};
function scSubHTML(){ return ''; }
function scFiltersHTML(){ return ''; }
function scHead(){ return ''; }
function scBody(){ return ''; }
function scApplyLang(){}
function promotePanelDates(){}
var host = {innerHTML:''};
renderScanner(host, {rows:rows});
var result = {
  basis:scAsof,
  rowCount:scRows.length,
  lags:rows.map(function(row){ return rowLagDays(row.asof, scAsof); }),
  cells:rows.map(function(row){ return ageCell(row.asof, scAsof); }),
  descending:scSortRows(rows).map(function(row){ return row.ticker; }),
  context:host.innerHTML.slice(0, host.innerHTML.indexOf('<div class="oew-sc-bar">'))
};
scSort.dir = 'asc';
result.ascending = scSortRows(rows).map(function(row){ return row.ticker; });
process.stdout.write(JSON.stringify(result));
""")
    result = subprocess.run(["node", "-"], input=driver, capture_output=True,
                            text=True, timeout=15, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@unittest.skipUnless(shutil.which("node"), "node not on PATH")
class ScannerSourceDateTests(unittest.TestCase):
    def test_future_rows_cannot_become_the_snapshot_reference(self):
        rows = [
            {"ticker": "LATEST", "asof": "2026-11-02"},
            {"ticker": "OLDER", "asof": "2026-10-30"},
            {"ticker": "NEXT", "asof": "2026-11-03"},
            {"ticker": "FUTURE", "asof": "2099-01-01"},
            {"ticker": "BAD", "asof": "2026-02-30"},
            {"ticker": "MISSING", "asof": None},
        ]
        result = _scanner_dates("2026-11-02", rows)
        self.assertEqual(result["basis"], "2026-11-02")
        self.assertEqual(result["rowCount"], len(rows))
        self.assertEqual(result["lags"], [0, 3, None, None, None, None])
        self.assertEqual(result["descending"],
                         ["OLDER", "LATEST", "NEXT", "FUTURE", "BAD", "MISSING"])
        self.assertEqual(result["ascending"],
                         ["LATEST", "OLDER", "NEXT", "FUTURE", "BAD", "MISSING"])
        for cell in result["cells"][2:]:
            self.assertIn("Unknown", cell)
            self.assertIn("未知", cell)
            self.assertNotIn("0d", cell)
        self.assertIn("Selected session", result["context"])
        self.assertNotIn("2099-01-01", result["context"])

    def test_archival_rows_keep_their_own_snapshot_reference(self):
        result = _scanner_dates("2026-11-02", [
            {"ticker": "ARCHIVE", "asof": "2026-08-13T21:00:00Z"},
            {"ticker": "EARLIER", "asof": "2026-08-11"},
            {"ticker": "FUTURE", "asof": "2099-01-01"},
        ])
        self.assertEqual(result["basis"], "2026-08-13")
        self.assertEqual(result["lags"], [0, 2, None])
        self.assertIn("Earlier session", result["context"])
        self.assertIn("2026-08-13", result["context"])
        self.assertNotIn("Selected session", result["context"])

    def test_no_admissible_row_leaves_the_reference_unknown(self):
        result = _scanner_dates("2026-11-02", [
            {"ticker": "FUTURE", "asof": "2099-01-01"},
            {"ticker": "BAD", "asof": "2026-02-30"},
            {"ticker": "MISSING", "asof": None},
        ])
        self.assertIsNone(result["basis"])
        self.assertEqual(result["lags"], [None, None, None])
        self.assertEqual(result["rowCount"], 3)
        self.assertIn("Source date unavailable", result["context"])
        self.assertNotIn("2099-01-01", result["context"])

    def test_absent_or_invalid_completed_session_cannot_invent_a_reference(self):
        for target in (None, "not-a-date", "2026-02-30"):
            with self.subTest(target=target):
                result = _scanner_dates(target, [
                    {"ticker": "ROW", "asof": "2026-11-02"},
                ])
                self.assertIsNone(result["basis"])
                self.assertEqual(result["lags"], [None])
                self.assertIn("Source date unavailable", result["context"])
