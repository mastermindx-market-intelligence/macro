"""Keep the historical tide clock separate from its optional intraday overlay.

Execute the template's real render/admission functions without reading stores,
calling a provider, or requiring the full producer checkout.
"""
from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import unittest


TEMPLATE = Path(__file__).resolve().parents[1] / "templates/options.html.j2"


class _SourceLabels(HTMLParser):
    def __init__(self, markup: str):
        super().__init__()
        self.values: dict[str, str] = {}
        self.current: str | None = None
        self.depth = 0
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if self.current is not None:
            self.depth += 1
        else:
            ident = dict(attrs).get("id", "")
            if ident in {"oew-fl-history-source", "oew-fl-intraday-source"}:
                self.current, self.depth = ident, 1
                self.values[ident] = ""

    def handle_endtag(self, tag):
        if self.current is not None:
            self.depth -= 1
            if self.depth == 0:
                self.current = None

    def handle_data(self, data):
        if self.current is not None:
            self.values[self.current] += data


def _render_tide(requested_session: str | None, desk: dict | None = None) -> dict:
    if desk is None:
        desk = {"market_tide": {"asof": "2026-08-13", "spark": [
            {"net_premium_mn": 1}, {"net_premium_mn": 2}
        ]}}
    source = TEMPLATE.read_text(encoding="utf-8")
    # Contiguous source slices retain the real functions and their formatters.
    sections = [
        ("function esc(s){", "function lvl(v){"),
        ("function sourceDay(value){", "function sourceContext(en, zh, date){"),
        ("function flTidePanel(desk){", "/* Both curves are ZERO-ANCHORED"),
        ("function flApplyTide(tide){", "function renderFlow(host, desk, cohorts){"),
    ]
    functions = "\n".join(source[source.index(start):source.index(end, source.index(start))]
                          for start, end in sections)
    driver = ("var LIVE_SESSION_DATE=" + json.dumps(requested_session)
              + ";\nvar desk=" + json.dumps(desk) + ";\n" + functions + r"""
var flTide = null;
var nodes = {
  'oew-fl-unfold': {innerHTML:''},
  'oew-fl-read': {innerHTML:''},
  'oew-fl-intraday-source': {innerHTML:''}
};
var document = {getElementById:function(id){
  return initial.indexOf('id="' + id + '"') >= 0 ? nodes[id] || null : null;
}};
function flDrawUnfold(){} // Pixel drawing is outside the source-date contract.
var initial = flTidePanel(desk);
var payload = {schema:'live_flow.tide/v1', session_date:'2026-11-02',
  asof:'2026-11-02T21:00:00Z', minutes:[
    {t:'09:30',ncp:100,npp:20,gross:100},
    {t:'16:00',ncp:120,npp:30,gross:120}
  ]};
var validity = flTideValidity(payload);
if(validity === null) flApplyTide(payload);
process.stdout.write(JSON.stringify({initial:initial, validity:validity,
  admittedSource:nodes['oew-fl-intraday-source'].innerHTML,
  overlay:nodes['oew-fl-unfold'].innerHTML,
  rejected:{
    stale:flTideValidity(Object.assign({},payload,{session_date:'2026-10-30'})),
    schema:flTideValidity(Object.assign({},payload,{schema:'wrong'})),
    asof:flTideValidity(Object.assign({},payload,{asof:'not-a-time'})),
    minutes:flTideValidity(Object.assign({},payload,{minutes:[]}))
  }}));
""")
    result = subprocess.run(["node", "-"], input=driver, capture_output=True,
                            text=True, timeout=15, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@unittest.skipUnless(shutil.which("node"), "node not on PATH")
class TideSourceDateTests(unittest.TestCase):
    def test_history_requested_and_admitted_dates_stay_separate(self):
        result = _render_tide("2026-11-02")
        labels = _SourceLabels(result["initial"]).values
        assert "2026-08-13" in labels.get("oew-fl-history-source", "")
        requested = labels.get("oew-fl-intraday-source", "")
        assert "Requested session" in requested and "2026-11-02" in requested
        assert "2026-08-13" not in requested
        # A combined footer date would be promoted into the whole panel's heading.
        assert 'class="oew-asof mono"' not in result["initial"]
        assert result["validity"] is None
        assert "Source session" in result["admittedSource"]
        assert "2026-11-02" in result["admittedSource"]
        assert "2026-08-13" not in result["admittedSource"]
        assert "2026-11-02" in result["overlay"]  # Canvas accessible name is dated too.
        assert result["rejected"] == {
            "stale": "session", "schema": "schema", "asof": "asof", "minutes": "minutes"
        }

    def test_unknown_requested_session_does_not_borrow_history_date(self):
        result = _render_tide(None)
        labels = _SourceLabels(result["initial"]).values
        assert "2026-08-13" in labels.get("oew-fl-history-source", "")
        requested = labels.get("oew-fl-intraday-source", "")
        assert "Requested session" in requested and "Date unavailable" in requested
        assert "日期不可用" in requested
        assert "2026-08-13" not in requested
        assert "Intraday record unavailable." in result["initial"]
        assert result["validity"] == "session"
        assert result["overlay"] == ""

    def test_admitted_intraday_survives_absent_or_insufficient_history(self):
        for desk in ({}, {"market_tide": {"asof": "2026-08-13", "spark": [
            {"net_premium_mn": 1}
        ]}}):
            with self.subTest(desk=desk):
                result = _render_tide("2026-11-02", desk)
                labels = _SourceLabels(result["initial"]).values
                assert 'id="oew-fl-unfold"' in result["initial"]
                assert "Not enough session history" in result["initial"]
                assert 'id="oew-fl-spark"' not in result["initial"]
                assert "2026-11-02" in labels["oew-fl-intraday-source"]
                assert result["validity"] is None
                assert "Source session" in result["admittedSource"]
                assert "2026-11-02" in result["admittedSource"]
                assert 'id="oew-fl-curve"' in result["overlay"]
                assert "2026-11-02" in result["overlay"]
