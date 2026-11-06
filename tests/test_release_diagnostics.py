"""Release Radar diagnostic truth (A1, macro#6868): adapter, producer seam, renderer.

Three defect chains shipped green because nothing executed the renderer:

1. PPI's null attribution was SYNTHESIZED from ``coverage_flags`` into a
   "Known 80% / Proxy 20% / Residual 0%" composition bar
   (``renderModal`` tab 2), and ``confidence_v2`` silently fell back to the
   legacy ``confidence`` -- two different denominators under one label.
2. ``cutoff_label`` is a queue position (nearest release of a type = "T-1",
   even 35 days out) yet rendered as "Data through T-1".
3. Levels were suffixed "pp", the champion's standardized attribution was
   shown beside a blended primary it does not explain, ``confidence`` (a band
   width rank) read as "Confidence: 30%", and the track-record overlay averaged
   a field the rows never carry into "MAE ours 0.000".

These tests therefore EXECUTE the actual Release Radar script from
``templates/dashboard.html.j2`` in Node (sliced verbatim, never re-implemented)
against verbatim producer items (``tests/fixtures/release_diagnostics``), with
and without the additive ``diagnostics`` subtree, and pin the adapter, its
numerical invariance and its single producer seam.

Node: the ci-pack runners install Node 20 (``actions/setup-node``).  A missing
``node`` FAILS under CI -- a silently skipped renderer test proves nothing --
and skips only on a developer machine without Node.
"""
from __future__ import annotations

import ast
import copy
import json
import math
import os
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest

from engine import release_diagnostics as rd

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / "templates" / "dashboard.html.j2"
PRODUCER = REPO / "scripts" / "build_release_forecast.py"
FIXTURE = REPO / "tests" / "fixtures" / "release_diagnostics" / "radar_items.json"

_SLICE_START = "var RR_EL = document.getElementById('rr-content');"
_SLICE_END = "/* INT-03: Tab trap within the modal */"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def fx() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _item(fx: dict, name: str) -> dict:
    return copy.deepcopy(fx["items"][name])


def _with_diag(fx: dict, item: dict) -> dict:
    """End-to-end: the real adapter builds the subtree the renderer reads."""
    snap = fx["snapshots"].get(item.get("input_snapshot_ref") or "")
    out = copy.deepcopy(item)
    out["diagnostics"] = rd.build_item_diagnostics(
        item, scoreboard=fx["scoreboard"], snapshot=snap)
    return out


# ---------------------------------------------------------------------------
# Executed-renderer harness
# ---------------------------------------------------------------------------

_DRIVER = r"""
'use strict';
const vm = require('vm');
const fs = require('fs');
const MARK = {'__NaN__': NaN, '__Infinity__': Infinity, '__-Infinity__': -Infinity};
const input = JSON.parse(fs.readFileSync(0, 'utf8'), function(k, v){
  return (typeof v === 'string' && Object.prototype.hasOwnProperty.call(MARK, v)) ? MARK[v] : v;
});
/* A minimal DOM covering what the CURRENT template actually touches.  The
   retained renderer reaches document.createElement (the forecast-snapshot
   notice), appendChild/insertBefore, querySelector by class, remove,
   contains and scrollTop — none of which the pre-#6868 slice used.  innerHTML
   reports the renderer's own writes AND the text of any node inserted into
   it, so the harness shows what a browser shows rather than what the renderer
   alone wrote. */
function makeEl(tag, id){
  var el = {
    tagName: tag || 'div', id: id || '', className: '', textContent: '',
    style: {}, attrs: {}, children: [], parentNode: null, removed: false,
    classList: {add: function(){}, remove: function(){}, toggle: function(){}, contains: function(){ return false; }},
    setAttribute: function(k, v){ el.attrs[k] = String(v); },
    getAttribute: function(k){ return Object.prototype.hasOwnProperty.call(el.attrs, k) ? el.attrs[k] : null; },
    hasAttribute: function(k){ return Object.prototype.hasOwnProperty.call(el.attrs, k); },
    addEventListener: function(){},
    querySelectorAll: function(){ return []; },
    querySelector: function(sel){
      if (sel && sel.charAt(0) === '.'){
        for (var i = 0; i < el.children.length; i++){
          if (el.children[i].className === sel.slice(1)) return el.children[i];
        }
      }
      return null;
    },
    contains: function(){ return false; },
    appendChild: function(child){ el.children.push(child); child.parentNode = el; return child; },
    insertBefore: function(child){ el.children.unshift(child); child.parentNode = el; return child; },
    remove: function(){ el.removed = true; },
    focus: function(){}, closest: function(){ return null; }
  };
  var html = '';
  Object.defineProperty(el, 'innerHTML', {
    get: function(){
      return html + el.children.map(function(c){ return c.textContent || ''; }).join('');
    },
    set: function(v){ html = String(v); }
  });
  Object.defineProperty(el, 'firstChild', {
    get: function(){ return el.children.length ? el.children[0] : null; }
  });
  return el;
}
const els = {};
const documentStub = {
  getElementById: function(id){ if (!els[id]) els[id] = makeEl('div', id); return els[id]; },
  createElement: function(tag){ return makeEl(tag); },
  documentElement: {getAttribute: function(){ return 'en'; }},
  activeElement: null, body: {style: {}}, querySelectorAll: function(){ return []; },
  querySelector: function(){ return null; }
};
const sandbox = {document: documentStub, console: console};
vm.createContext(sandbox);
sandbox.window = sandbox;
vm.runInContext("'use strict';\n" + input.src, sandbox, {filename: 'dashboard.html.j2#release-radar'});
const out = input.ops.map(function(op){
  if (op.op === 'card') return sandbox.renderCard(op.item);
  if (op.op === 'modal' || op.op === 'modal-refresh'){
    sandbox.openModal(op.item, op.op === 'modal-refresh');
    return {title: els['rr-modal-title-block'].innerHTML, panes: els['rr-modal-inner'].innerHTML,
            tabs: els['rr-tab-strip'].innerHTML,
            overflow: documentStub.body.style.overflow || '',
            openItem: sandbox._rrOpenItem ? (sandbox._rrOpenItem.release_type || '') : null};
  }
  if (op.op === 'trackrecord') return sandbox.rrTrackRecordBlock(op.track);
  if (op.op === 'countdown'){
    var days = sandbox._rrDaysUntil(op.date);
    return {days: days, labels: days === null ? null : sandbox._rrCountdownLabels(days)};
  }
  throw new Error('unknown op ' + op.op);
});
process.stdout.write(JSON.stringify(out));
"""


def _renderer_source() -> str:
    src = TEMPLATE.read_text(encoding="utf-8")
    start = src.index(_SLICE_START)
    end = src.index(_SLICE_END, start)
    body = src[start:end]
    return body


def _js_safe(obj):
    if isinstance(obj, float) and not math.isfinite(obj):
        return "__NaN__" if math.isnan(obj) else ("__Infinity__" if obj > 0 else "__-Infinity__")
    if isinstance(obj, dict):
        return {k: _js_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_js_safe(v) for v in obj]
    return obj


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        if os.environ.get("CI"):
            pytest.fail("node is required in CI: the Release Radar renderer tests "
                        "execute the template's own JavaScript")
        pytest.skip("node not on PATH (developer machine only; CI installs Node 20)")
    return node


def _run(ops: list[dict], tmp_path: Path) -> list:
    node = _node()
    driver = tmp_path / "rr_driver.js"
    driver.write_text(_DRIVER, encoding="utf-8")
    payload = json.dumps({"src": _renderer_source(), "ops": _js_safe(ops)}, allow_nan=False)
    proc = subprocess.run([node, str(driver)], input=payload, capture_output=True,
                          text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-3000:]
    return json.loads(proc.stdout)


def _card(item: dict, tmp_path: Path) -> str:
    return _run([{"op": "card", "item": item}], tmp_path)[0]


def _modal(item: dict, tmp_path: Path) -> dict:
    return _run([{"op": "modal", "item": item}], tmp_path)[0]


def _pane(modal: dict, tab: str) -> str:
    m = re.search(r'<div class="rr-pane[^"]*" data-tab="%s">' % tab, modal["panes"])
    if not m:
        return ""
    rest = modal["panes"][m.end():]
    nxt = re.search(r'<div class="rr-pane[^"]*" data-tab="t\d">', rest)
    return rest[:nxt.start()] if nxt else rest


def test_renderer_slice_is_verbatim_script_not_template_logic():
    """Guard the harness: the slice must exist, contain the real entry points,
    and hold no Jinja tag -- so the raw slice IS what the built page ships.

    #6868 (current main): the panel-level track record is rendered by
    ``rrTrackRecordBlock``; the pre-#6868 ``scoreboardBlock`` is gone and must
    NOT come back (it averaged a field the rows never carry)."""
    body = _renderer_source()
    for fn in ("function renderCard(", "function renderModal(", "function openModal(",
               "function rrTrackRecordBlock(", "function rrTrackRecordLine("):
        assert fn in body, fn
    assert "function scoreboardBlock(" not in body, (
        "the retired latest-scored-print scoreboard must not return")
    for tag in ("{{", "{%", "{#"):
        assert tag not in body


# ---------------------------------------------------------------------------
# Executed renderer: the reported defects
# ---------------------------------------------------------------------------

def test_ppi_null_attribution_is_never_synthesized_from_coverage_flags(fx, tmp_path):
    item = _item(fx, "ppi_finaldemand_2026_08_asof_0905")
    assert item["components"] is None and item["confidence_components_v2"] is None
    for variant in (item, _with_diag(fx, item)):
        comp = _pane(_modal(variant, tmp_path), "t2")
        assert "Data quality composition" not in comp
        assert "rr-conf-seg-known" not in comp
        assert "Attribution not available for this model" in comp
        assert "该模型暂无归因数据" in comp


def test_queue_position_never_renders_as_a_data_cutoff(fx, tmp_path):
    for name in ("ppi_finaldemand_2026_08_asof_0905", "pce_headline_2026_08",
                 "cpi_core_2026_09", "claims_2026_09_17"):
        item = _item(fx, name)
        for variant in (item, _with_diag(fx, item)):
            title = _modal(variant, tmp_path)["title"]
            assert "T−1" not in title and "T-1" not in title, name
            assert "Data through" not in title and "数据截至" not in title, name


def test_verified_snapshot_date_is_the_only_input_date_shown(fx, tmp_path):
    item = _item(fx, "cpi_headline_2026_08")
    title = _modal(_with_diag(fx, item), tmp_path)["title"]
    assert "Inputs as of Sep 10, 2026" in title
    assert "输入截至2026年9月10日" in title
    for invented in ("08:30", "ET", "UTC", "00:00", "midnight"):
        assert invented not in title
    bare = _modal(item, tmp_path)["title"]
    assert "Input date unavailable" in bare and "输入日期不可用" in bare


def test_unqualified_confidence_is_replaced_by_calibration_status(fx, tmp_path):
    for name in ("cpi_headline_2026_08", "pce_headline_2026_08",
                 "ppi_finaldemand_2026_08_asof_0905"):
        item = _item(fx, name)
        for variant in (item, _with_diag(fx, item)):
            modal = _modal(variant, tmp_path)
            html = modal["panes"]
            assert "Confidence:" not in html and "置信度：" not in html, name
            assert "Confidence composition" not in html and "置信度构成" not in html, name
            assert "Calibration not established" in _pane(modal, "t0"), name
            assert "校准尚未确立" in _pane(modal, "t0"), name


def test_levels_carry_the_target_unit_and_only_differences_are_pp(fx, tmp_path):
    item = _with_diag(fx, _item(fx, "cpi_headline_2026_08"))
    card = _card(item, tmp_path)
    assert "0.30%" in card and "0.30pp" not in card
    assert "0.36%" in card and "0.36pp" not in card
    modal = _modal(item, tmp_path)
    overview = _pane(modal, "t0")
    assert "0.30%" in overview and "0.30pp" not in overview
    assert "% month-on-month, seasonally adjusted" in overview
    assert "环比%，季节调整后" in overview
    assert re.search(r"vs benchmark median: <b[^>]*>[+-]0\.\d\dpp</b>", overview)
    models = _pane(modal, "t1")
    assert "0.40%" in models and "0.40pp" not in models  # recorded blend point, a level
    comp = _pane(modal, "t2")
    assert "+0.091pp" in comp  # contributions stay percentage points


def test_point_and_predictive_median_are_labelled_distinctly(fx, tmp_path):
    item = _with_diag(fx, _item(fx, "pce_headline_2026_08"))
    proj = item["projection"]
    assert round(proj["point"], 2) != round(proj["p50"], 2) or proj["point"] != proj["p50"]
    overview = _pane(_modal(item, tmp_path), "t0")
    assert "Point forecast" in overview and "点预测" in overview
    assert "Median (p50)" in overview and "中位数（p50）" in overview
    assert f"{proj['p50']:.2f}%" in overview  # the band's own median, never recentred


def test_bands_are_nominal_80_and_50_and_uncalibrated(fx, tmp_path):
    item = _with_diag(fx, _item(fx, "cpi_headline_2026_08"))
    overview = _pane(_modal(item, tmp_path), "t0")
    assert "Nominal 80% band (p10–p90)" in overview
    assert "nominal 50% (p25–p75)" in overview
    assert "not calibrated" in overview
    assert "名义80%区间（p10–p90）" in overview and "名义50%（p25–p75）" in overview
    for forbidden in (r"(?<![\d.])90%", r"(?<![\d.])95%", r"\bp05\b", r"\bp95\b"):
        assert not re.search(forbidden, overview), forbidden


@pytest.mark.parametrize("p10,p90,label", [
    (float("nan"), 0.9, "nan"),
    (False, True, "booleans"),
    (0.9, 0.1, "reversed"),
    (0.5, 0.5, "zero width"),
    (None, 0.9, "missing"),
    ("0.1", 0.9, "string"),
    (float("-inf"), 0.9, "infinite"),
])
def test_invalid_bands_render_unavailable_not_drawn(fx, tmp_path, p10, p90, label):
    item = _item(fx, "pce_headline_2026_08")
    item["projection"]["p10"] = p10
    item["projection"]["p90"] = p90
    for variant in (item, _with_diag(fx, item)):
        overview = _pane(_modal(variant, tmp_path), "t0")
        assert "NaN" not in overview and "Infinity" not in overview, label
        assert "<svg" not in overview, label
        assert "Interval unavailable" in overview and "区间不可用" in overview, label


def test_blend_band_never_borrows_the_champion_band(fx, tmp_path):
    item = _item(fx, "cpi_headline_2026_08")
    champion_p10 = item["projection"]["p10"]
    item["combined"]["p10"] = None
    for variant in (item, _with_diag(fx, item)):
        overview = _pane(_modal(variant, tmp_path), "t0")
        assert f"p10 {champion_p10:.2f}" not in overview
        assert "Interval unavailable" in overview


def test_attribution_is_bound_to_the_champion_and_excludes_the_intercept(fx, tmp_path):
    item = _with_diag(fx, _item(fx, "cpi_headline_2026_08"))
    comp = _pane(_modal(item, tmp_path), "t2")
    assert "Model attribution — champion model" in comp
    assert "excluding the model’s baseline (intercept)" in comp
    assert "Explains the champion forecast (0.40%), not the displayed blend" in comp
    assert "Persistence (lagged inflation)" in comp and "持续性（滞后通胀）" in comp
    assert "Core persist." not in comp and "What is driving the number" not in comp
    # never an inferred baseline: champion point - sum(parts) = 0.2338 must not appear
    for inferred in ("0.2338", "0.234", "0.23%", "0.23pp"):
        assert inferred not in comp
    assert "Where the attribution comes from" in comp
    assert "Direct prices" in comp and "Leading proxies" in comp


def test_all_zero_contributions_are_an_undefined_denominator(fx, tmp_path):
    item = _item(fx, "cpi_headline_2026_08")
    for comp in item["components"]:
        comp["contrib_pp"] = 0.0
    item["confidence_components_v2"] = {"w_known": 0.0, "w_proxy": 0.0, "w_residual": 0.0,
                                        "c_raw": 0.0, "input_completeness": 1.0}
    item["confidence_v2"] = 0.0
    for variant in (item, _with_diag(fx, item)):
        comp = _pane(_modal(variant, tmp_path), "t2")
        assert "Attribution shares undefined — every contribution is zero" in comp
        assert "归因占比无定义" in comp
        visible = re.sub(r'\sstyle="[^"]*"', "", comp)  # bar widths are geometry, not claims
        assert "0.0%" not in visible and "Direct prices" not in visible


def test_blend_shows_recorded_weights_points_and_cold_start(fx, tmp_path):
    item = _with_diag(fx, _item(fx, "cpi_headline_2026_08"))
    models = _pane(_modal(item, tmp_path), "t1")
    for iid, pt in item["combined"]["combined_components"]["points"].items():
        assert iid in models
        assert f"{pt:.2f}%" in models
    assert models.count("w=20.0%") == 5
    assert "cold start" in models
    assert "waterfall" not in models.lower()


def test_unverifiable_market_benchmark_is_not_this_releases_benchmark(fx, tmp_path):
    for name in ("cpi_core_2026_09", "cpi_core_2026_08"):
        item = _item(fx, name)
        mi = item["benchmark_set"]["market_implied"]
        assert mi["implied"] == "0.2%" and "August 2026" in mi["event_title"]
        for variant in (item, _with_diag(fx, item)):
            models = _pane(_modal(variant, tmp_path), "t1")
            assert '<span class="rr-mkt-val">0.2%</span>' not in models, name
            assert "contract month and unit can’t be verified" in models, name
            assert "无法核实合约月份与单位" in models, name
        # raw evidence is retained, untouched, in the payload itself
        assert item["benchmark_set"]["market_implied"] == mi


def test_street_consensus_is_stated_unavailable(fx, tmp_path):
    item = _with_diag(fx, _item(fx, "cpi_headline_2026_08"))
    models = _pane(_modal(item, tmp_path), "t1")
    assert "Street consensus: not available" in models
    assert "市场一致预期：暂无" in models


def test_coherent_ridge_not_scheduled_only_when_the_horizon_proves_it(fx, tmp_path):
    sep = _with_diag(fx, _item(fx, "cpi_core_2026_09"))
    assert sep["days_to"] == 34
    assert "not scheduled at this horizon" in _pane(_modal(sep, tmp_path), "t1")
    aug = _item(fx, "cpi_headline_2026_08")
    assert aug["days_to"] == 1
    withheld = copy.deepcopy(aug)
    del withheld["shadows"]["coherent_ridge_v1"]
    models = _pane(_modal(_with_diag(fx, withheld), tmp_path), "t1")
    assert "not scheduled at this horizon" not in models
    assert "coherent_ridge_v1: not available" in models
    projected = _pane(_modal(_with_diag(fx, aug), tmp_path), "t1")
    assert "coherent_ridge_v1" in projected
    assert "coherent_ridge_v1: not available" not in projected
    assert "not scheduled at this horizon" not in projected


def test_history_reports_exact_lane_performance_or_unavailable(fx, tmp_path):
    item = _item(fx, "cpi_headline_2026_08")
    hist = _pane(_modal(_with_diag(fx, item), tmp_path), "t3")
    assert "first scored prints land this month" not in hist
    assert "No scored record yet for this exact model, target and horizon" in hist
    bare = _pane(_modal(item, tmp_path), "t3")
    assert "first scored prints land this month" not in bare
    assert "Track record unavailable for this forecast" in bare


def test_release_history_is_not_evidence_for_the_selected_forecast_lane(fx, tmp_path):
    """#6868 A1: the release-level track record and the SELECTED forecast's
    exact model / target / horizon lane are two different facts and the page
    must not present the first as evidence for the second."""
    item = _with_diag(fx, _item(fx, "cpi_headline_2026_08"))
    hist = _pane(_modal(item, tmp_path), "t3")
    # the retained release-level product is still shown ...
    assert "Track record" in hist
    # ... beside the exact-lane statement, which is its own labelled group
    assert "Exact model, target and horizon" in hist
    assert "No scored record yet for this exact model, target and horizon" in hist


def test_countdown_follows_the_et_clock_and_the_release_date_not_the_stale_days_to(fx, tmp_path):
    """#6868 A1 (current main): the countdown is computed from the release date
    against the Eastern date.  ``item.days_to`` is a queue position and goes
    stale the moment the page is open, so it must never drive the countdown."""
    a = _run([{"op": "countdown", "date": "2026-09-10"}], tmp_path)[0]
    b = _run([{"op": "countdown", "date": "2026-09-11"}], tmp_path)[0]
    assert a["days"] is not None and b["days"] is not None
    assert b["days"] == a["days"] + 1, "the countdown must follow the release date"
    # an unparseable date is never a countdown
    bad = _run([{"op": "countdown", "date": "not-a-date"}], tmp_path)[0]
    assert bad["days"] is None and bad["labels"] is None

    # a long-past release date with a stale days_to == 1 must NOT read as
    # "Releases tomorrow": the date wins over the queue position.
    item = _item(fx, "cpi_headline_2026_08")
    item["days_to"] = 1
    item["release_date"] = "2020-09-10"
    modal = _modal(item, tmp_path)
    clock = _run([{"op": "countdown", "date": "2020-09-10"}], tmp_path)[0]
    assert clock["days"] is not None and clock["days"] < 0
    assert clock["labels"]["en"] in modal["title"]
    assert "Releases tomorrow" not in modal["title"]
    assert "明日发布" not in modal["title"]


def test_refreshing_modal_rebuilds_the_panes_without_reopening_the_modal(fx, tmp_path):
    """#6868 A1 (current main): ``openModal(item, refreshing)`` is the REFRESH
    path.  It rebuilds the panes for the still-open modal and keeps the open
    item; it must not perform the open-side effects (overlay open, body scroll
    lock, focus move) that would steal the reader's place."""
    item = _item(fx, "cpi_headline_2026_08")
    opened = _modal(item, tmp_path)
    assert opened["overflow"] == "hidden", "the open path locks the page scroll"
    assert opened["openItem"] == item["release_type"]
    refreshed = _run([{"op": "modal-refresh", "item": item}], tmp_path)[0]
    assert refreshed["overflow"] == "", "the refresh path must not re-open the modal"
    assert refreshed["panes"], "the refresh path must still rebuild the panes"
    assert refreshed["tabs"], "the refresh path must still rebuild the tab strip"
    assert refreshed["openItem"] == item["release_type"]


def test_track_record_overlay_never_turns_missing_errors_into_zero(fx, tmp_path):
    """#6868 A1, on the RETAINED track-record product (``rrTrackRecordBlock``).

    The defect the retired overlay carried: the scored rows never carry an
    error field, and the old average turned that absence into "MAE ours
    0.000".  The retained product states what it actually has and a missing
    error stays "—".  The payload is built by the REAL producer summary, so
    the shape under test is the shape the page receives."""
    import scripts.build_release_forecast as producer
    rows = fx["last_scored"]
    assert rows and all("our_mae" not in r for r in rows)
    board = {
        "evaluation_basis": "official_published_metric",
        "evaluation_basis_counts": {"claims:champion": {"n": 1, "first_print_matched_n": 1}},
        "by_release": {"claims": {}},
        "by_shadow": {},
    }
    tr = producer._track_record_summary(board, "withheld_until_clean_aligned_forward_evidence")
    html = _run([{"op": "trackrecord", "track": tr}], tmp_path)[0]
    assert "0.000" not in html
    assert "—" in html
    # the count of scored forecasts is stated; no accuracy is claimed
    assert "Accuracy isn't claimed yet." in html
    assert "Benchmark only" in html


def test_retained_track_record_states_never_overstate_a_release(fx, tmp_path):
    """#6868 A1: the RETAINED product states, per release, what it actually has.

    Clean-score count, first-print matches, the display floor (a release below
    it is accruing, not scored), the uncertainty range only when the error
    carries one, the benchmark-only / not-comparable states, and the retained
    superseded receipts.  n=0 is never an accuracy claim."""
    import scripts.build_release_forecast as producer
    floor = producer.TRACK_RECORD_DISPLAY_MIN_N
    verdict = producer.TRACK_RECORD_VERDICT_MIN_N
    claim = "withheld_until_clean_aligned_forward_evidence"

    def track(n, stats, matched=None, epochs=None, receipts=None):
        board = {
            "evaluation_basis": "official_published_metric",
            "evaluation_basis_counts": {"claims:champion": {
                "n": n,
                "first_print_matched_n": n if matched is None else matched,
                "target_epochs": ["e1"] if epochs is None else epochs,
            }},
            "by_release": {"claims": stats},
            "by_shadow": {},
        }
        if receipts is not None:
            board["score_receipts"] = receipts
        return producer._track_record_summary(board, claim)

    good = {"mae_ours": 0.05, "mae_ours_ci": [0.04, 0.06], "mae_naive_prior": 0.07}

    # nothing scored: the row says so, and no accuracy is claimed
    html = _run([{"op": "trackrecord", "track": track(0, {})}], tmp_path)[0]
    assert "No clean scores" in html
    assert "0.000" not in html
    assert "Accuracy isn't claimed yet." in html

    # a release that was never scored at all is not listed as a score either
    empty = producer._track_record_summary(
        {"evaluation_basis": "official_published_metric",
         "evaluation_basis_counts": {}, "by_release": {}, "by_shadow": {}}, claim)
    html = _run([{"op": "trackrecord", "track": empty}], tmp_path)[0]
    assert "No release has been scored yet." in html
    assert "0.000" not in html

    # below the display floor: the count and the floor, never a score
    html = _run([{"op": "trackrecord", "track": track(1, dict(good))}], tmp_path)[0]
    assert "Accruing 1/%d" % floor in html
    assert "0.05" not in html

    # above the floor but below the verdict floor: early, with the count
    html = _run([{"op": "trackrecord", "track": track(floor + 1, dict(good))}], tmp_path)[0]
    assert "Early, n = %d" % (floor + 1) in html

    # at or above the verdict floor: the error and its range are shown
    html = _run([{"op": "trackrecord", "track": track(verdict, dict(good))}], tmp_path)[0]
    assert "0.05 (0.04–0.06)" in html
    assert "0.07" in html
    assert "Accuracy isn't claimed yet." in html

    # the range is withheld when the error carries none: the error stays hidden
    no_ci = {"mae_ours": 0.05, "mae_ours_ci": None, "mae_naive_prior": 0.07}
    html = _run([{"op": "trackrecord", "track": track(verdict, dict(no_ci))}], tmp_path)[0]
    assert "Range pending" in html
    assert "0.05" not in html

    # a release scored against a mixed target is not comparable yet
    html = _run([{"op": "trackrecord",
                  "track": track(verdict, dict(good), matched=verdict - 1)}], tmp_path)[0]
    assert "Not comparable yet" in html

    # superseded receipts are retained, not erased
    html = _run([{"op": "trackrecord",
                  "track": track(verdict, dict(good),
                                 receipts={"superseded_n": 3})}], tmp_path)[0]
    assert "3 earlier scores are kept as superseded, not erased." in html


def test_input_availability_is_not_painted_as_freshness(fx, tmp_path):
    item = _item(fx, "ppi_finaldemand_2026_08_asof_0905")
    for variant in (item, _with_diag(fx, item)):
        overview = _pane(_modal(variant, tmp_path), "t0")
        assert ">fresh<" not in overview and "充分" not in overview
    overview = _pane(_modal(_with_diag(fx, item), tmp_path), "t0")
    assert "Inputs present" in overview and "5 of 5" in overview
    assert "Freshness" in overview and "not verified" in overview
    assert "Economic coverage" in overview and "not measured" in overview


def test_benchmark_only_stays_benchmark_only(fx, tmp_path):
    item = _item(fx, "claims_2026_09_17")
    for variant in (item, _with_diag(fx, item)):
        card = _card(variant, tmp_path)
        assert "benchmark-only" in card and "%" not in card
        overview = _pane(_modal(variant, tmp_path), "t0")
        assert "Benchmark-only" in overview
        assert "Calibration not established" not in overview


def test_primary_selection_policy_and_numbers_are_unchanged(fx, tmp_path):
    item = _with_diag(fx, _item(fx, "cpi_headline_2026_08"))
    comb = item["combined"]
    card = _card(item, tmp_path)
    assert "Model + benchmark blend" in card
    assert f"{comb['combined_point']:.2f}%" in card
    overview = _pane(_modal(item, tmp_path), "t0")
    assert f"p10 {comb['p10']:.2f}" in overview and f"p90 {comb['p90']:.2f}" in overview
    champ = _with_diag(fx, _item(fx, "pce_headline_2026_08"))
    assert f"{champ['projection']['point']:.2f}%" in _card(champ, tmp_path)


# ---------------------------------------------------------------------------
# Adapter semantics
# ---------------------------------------------------------------------------

def _diag(fx, name, **kw):
    item = _item(fx, name)
    return rd.build_item_diagnostics(item, scoreboard=fx["scoreboard"],
                                     snapshot=fx["snapshots"].get(item.get("input_snapshot_ref") or ""),
                                     **kw)


def test_adapter_is_pure_and_json_safe(fx):
    adversarial = _item(fx, "cpi_headline_2026_08")
    adversarial["projection"]["p10"] = float("nan")
    adversarial["combined"]["p90"] = True
    adversarial["components"][0]["contrib_pp"] = float("inf")
    adversarial["pit"]["vintaged_legs"] = "not-a-list"
    adversarial["days_to"] = True
    adversarial["benchmark_set"]["market_implied"] = "0.2%"
    items = [copy.deepcopy(v) for v in fx["items"].values()] + [adversarial, {}, {"projection": None}]
    for item in items:
        before = copy.deepcopy(item)
        out = rd.build_item_diagnostics(item, scoreboard=fx["scoreboard"])
        assert json.dumps(item, sort_keys=True, default=str) == json.dumps(before, sort_keys=True, default=str)
        json.dumps(out, allow_nan=False)
        assert out["schema"] == rd.SCHEMA and out["display_only"] is True and out["authority"] is False


def test_null_attribution_is_unavailable_never_zero(fx):
    d = _diag(fx, "ppi_finaldemand_2026_08_asof_0905")["attribution"]
    assert d["status"] == "unavailable" and d["reason"] == "not_recorded"
    assert d["provenance_mix"] == {"status": "not_recorded"}
    nfp = _diag(fx, "nfp_2026_09")["attribution"]
    assert nfp["status"] == "unavailable" and nfp["reason"] == "model_point_none"


def test_zero_and_malformed_contributions(fx):
    item = _item(fx, "cpi_headline_2026_08")
    for comp in item["components"]:
        comp["contrib_pp"] = 0.0
    item["confidence_components_v2"] = {"w_known": 0, "w_proxy": 0, "w_residual": 0}
    d = rd.build_item_diagnostics(item)["attribution"]
    assert d["status"] == "undefined_denominator"
    assert d["provenance_mix"] == {"status": "undefined_denominator"}
    for bad in (float("nan"), True, "0.1", None):
        item2 = _item(fx, "cpi_headline_2026_08")
        item2["components"][1]["contrib_pp"] = bad
        assert rd.build_item_diagnostics(item2)["attribution"]["status"] == "malformed"


def test_cpi_attribution_is_labelled_for_its_own_forecast(fx):
    d = _diag(fx, "cpi_headline_2026_08")
    att = d["attribution"]
    assert att["method"] == "standardized_model_attribution_excluding_intercept"
    assert att["baseline"] == "not_reported"
    assert att["forecast_model"] == "champion" and att["applies_to_primary"] is False
    assert {b["name"]: b["role"] for b in att["blocks"]}["core_persistence"] == "persistence"
    assert att["provenance_mix"]["persistence_share"] == 0.4647
    assert d["primary"]["model"] == "combined_v1"
    pce = _diag(fx, "pce_headline_2026_08")
    assert pce["attribution"]["method"] == "not_documented"


def test_primary_mirrors_selection_policy_and_binds_its_own_band(fx):
    d = _diag(fx, "cpi_headline_2026_08")["primary"]
    assert d["basis"] == "combined_v1_benchmark_augmented" and d["values_from"] == "combined"
    assert d["point_vs_median"] == "equal"
    item = _item(fx, "cpi_headline_2026_08")
    item["combined"]["p10"] = None  # champion p10 exists, but it is a different forecast
    d2 = rd.build_item_diagnostics(item)["primary"]
    assert d2["band_80"] == {"status": "unavailable", "reason": "missing"}
    assert d2["values_from"] == "combined"
    pce = _diag(fx, "pce_headline_2026_08")["primary"]
    assert pce["basis"] == "champion" and pce["point_vs_median"] == "differs"
    claims = _diag(fx, "claims_2026_09_17")["primary"]
    assert claims["basis"] == "benchmark_only" and claims["status"] == "no_model_forecast"


@pytest.mark.parametrize("p10,p90,reason", [
    (None, 0.5, "missing"), (float("nan"), 0.5, "invalid_value"), (True, 0.5, "invalid_value"),
    ("0.1", 0.5, "invalid_value"), (0.6, 0.5, "reversed"), (0.35, 0.5, "quantiles_out_of_order"),
])
def test_band_statuses(p10, p90, reason):
    bands = rd.assess_bands({"p10": p10, "p25": 0.2, "p50": 0.3, "p75": 0.4, "p90": p90})
    assert bands["band_80"] == {"status": "unavailable", "reason": reason}


def test_band_nominal_coverage_is_80_and_50_only(fx):
    d = _diag(fx, "cpi_headline_2026_08")["primary"]
    assert d["nominal_coverage"] == {"p10_p90": 0.8, "p25_p75": 0.5}
    assert d["calibration"] == "not_established"
    assert d["interval_status"] == "experimental_uncalibrated"
    blob = json.dumps(d)
    assert "0.9" not in blob and "p05" not in blob and "p95" not in blob
    reversed_ = rd.assess_bands({"p10": 0.1, "p25": 0.5, "p50": 0.3, "p75": 0.4, "p90": 0.9})
    assert reversed_["band_50"]["reason"] == "reversed"
    assert reversed_["band_80"]["reason"] == "quantiles_out_of_order"
    zero = rd.assess_bands({"p10": 0.5, "p90": 0.5})
    assert zero["band_80"]["reason"] == "zero_width"


def test_units_are_mapped_from_the_structured_target_only(fx):
    assert _diag(fx, "cpi_headline_2026_08")["unit"] == {
        "status": "mapped", "target": "mom_sa_pct",
        "level": "percent_mom_sa", "difference": "percentage_points"}
    assert _diag(fx, "nfp_2026_09")["unit"] == {"status": "not_mapped", "target": "change_thousands"}


def test_cutoff_is_verified_only_by_the_matching_snapshot_receipt(fx):
    d = _diag(fx, "cpi_headline_2026_08")["cutoff"]
    assert d["status"] == "verified" and d["inputs_asof"] == "2026-09-10" and d["precision"] == "date"
    assert d["legacy_label"] == "T-1" and d["legacy_label_kind"] == "queue_position_not_a_data_cutoff"
    item = _item(fx, "cpi_headline_2026_08")
    snap = fx["snapshots"][item["input_snapshot_ref"]]
    cases = {
        "snapshot_unreadable": None,
        "snapshot_malformed": ["not", "a", "mapping"],
        "snapshot_date_invalid": {**snap, "asof": "2026-09-10T08:30:00Z"},
        "snapshot_identity_mismatch": {**snap, "prediction_id": "CPI:2026-09:first:2026-09-10:v1"},
        "inputs_hash_mismatch": {**snap, "inputs_hash": "0" * 64},
    }
    for reason, receipt in cases.items():
        out = rd.build_item_diagnostics(item, snapshot=receipt)["cutoff"]
        assert out["status"] == "unavailable" and out["reason"] == reason, reason
        assert out["inputs_asof"] is None
    no_ref = copy.deepcopy(item)
    no_ref["input_snapshot_ref"] = None
    assert rd.build_item_diagnostics(no_ref, snapshot=snap)["cutoff"]["reason"] == "snapshot_ref_missing"
    ppi = _diag(fx, "ppi_finaldemand_2026_08_asof_0905")["cutoff"]
    assert ppi["status"] == "verified" and ppi["inputs_asof"] == "2026-09-04"  # T-6, not "T-1"


def test_inputs_split_availability_vintage_freshness_and_coverage(fx):
    d = _diag(fx, "cpi_headline_2026_08")["inputs"]
    assert (d["declared"], d["present"], d["absent"]) == (9, 9, 0)
    assert d["vintage"] == {"status": "recorded", "point_in_time": 7, "revision_optimistic": 1,
                            "unrevised": 1, "unclassified": 0}
    assert d["freshness"] == {"status": "not_verified", "reason": "no_fresh_leg_receipt"}
    assert d["economic_coverage"] == {"status": "not_measured"}
    ppi = _diag(fx, "ppi_finaldemand_2026_08_asof_0905")["inputs"]
    assert ppi["vintage"]["status"] == "not_recorded"  # PPI's PIT lists no vintaged legs
    item = _item(fx, "cpi_headline_2026_08")
    item["input_manifest"] = None
    assert rd.build_item_diagnostics(item)["inputs"]["reason"] == "no_input_manifest"
    item2 = _item(fx, "cpi_headline_2026_08")
    item2["pit"]["fresh_legs"] = ["gasoline_mom"]
    assert rd.build_item_diagnostics(item2)["inputs"]["freshness"] == {
        "status": "verified", "fresh": 1, "of_present": 9}


def test_coherent_ridge_statuses(fx):
    assert _diag(fx, "cpi_headline_2026_08")["challengers"]["coherent_ridge_v1"]["status"] == "projected"
    sep = _diag(fx, "cpi_core_2026_09")["challengers"]["coherent_ridge_v1"]
    assert sep == {"status": "not_scheduled_at_horizon", "days_to_release": 34,
                   "rule": "decision_asof_must_equal_release_date_minus_one_day"}
    item = _item(fx, "cpi_headline_2026_08")
    del item["shadows"]["coherent_ridge_v1"]
    assert rd.build_item_diagnostics(item)["challengers"]["coherent_ridge_v1"]["status"] == "withheld"
    item["days_to"] = True
    assert rd.build_item_diagnostics(item)["challengers"]["coherent_ridge_v1"]["status"] == "unavailable"
    wrong = _item(fx, "cpi_headline_2026_08")
    wrong["shadows"]["coherent_ridge_v1"]["period"] = "2026-07"
    assert rd.build_item_diagnostics(wrong)["challengers"]["coherent_ridge_v1"]["status"] == "identity_mismatch"
    assert "challengers" not in _diag(fx, "pce_headline_2026_08")


def test_performance_comes_only_from_the_exact_lane_at_the_scored_horizon(fx):
    d = _diag(fx, "cpi_headline_2026_08")["performance"]
    assert d["status"] == "unavailable" and d["reason"] == "no_scored_releases_in_exact_lane"
    assert d["lane"] == "cpi_headline:combined_v1:combined_v1_legacy_target_v1:mixed_legacy_cross_vintage_v0"
    assert _diag(fx, "pce_headline_2026_08")["performance"]["reason"] == "horizon_not_scored"
    assert _diag(fx, "claims_2026_09_17")["performance"]["status"] == "not_applicable"
    item = _item(fx, "cpi_headline_2026_08")
    item["primary_forecast_basis"] = None  # champion primary at T-1
    assert rd.build_item_diagnostics(item, scoreboard=fx["scoreboard"])["performance"]["reason"] == \
        "no_exact_epoch_lane_for_champion"
    lane = "cpi_headline:combined_v1:combined_v1_legacy_target_v1:mixed_legacy_cross_vintage_v0"
    board = {"evaluation_basis": "x", "by_shadow_epoch": {lane: {"n": 3, "mae_ours": 0.5,
             "by_cutoff": {"T-1": {"n": 2, "mae_ours": 0.12}}}}}
    got = rd.build_item_diagnostics(_item(fx, "cpi_headline_2026_08"), scoreboard=board)["performance"]
    assert got["status"] == "available" and (got["n"], got["mae_pp"]) == (2, 0.12)
    assert rd.build_item_diagnostics(_item(fx, "cpi_headline_2026_08"))["performance"]["reason"] == \
        "scoreboard_unavailable"


def test_market_benchmark_identity_comes_from_structure_not_prose(fx):
    d = _diag(fx, "cpi_core_2026_09")["benchmarks"]
    assert d["street_consensus"]["status"] == "unavailable"
    assert d["market_implied"] == {"source": "polymarket", "raw_ref": "benchmark_set.market_implied",
                                   "status": "unverified_identity",
                                   "reason": "no_structured_target_period_or_unit"}
    item = _item(fx, "cpi_core_2026_09")
    item["benchmark_set"]["market_implied"].update(period="2026-08", target="mom_sa_pct")
    assert rd.build_item_diagnostics(item)["benchmarks"]["market_implied"]["reason"] == "period_mismatch"
    item["benchmark_set"]["market_implied"].update(period="2026-09")
    assert rd.build_item_diagnostics(item)["benchmarks"]["market_implied"]["status"] == "unverified_value"
    item["benchmark_set"]["market_implied"]["implied_median"] = 0.21
    assert rd.build_item_diagnostics(item)["benchmarks"]["market_implied"]["status"] == "verified"


def test_blend_status_exposes_recorded_cold_start_without_changing_weights(fx):
    item = _item(fx, "cpi_headline_2026_08")
    before = copy.deepcopy(item["combined"])
    d = rd.build_item_diagnostics(item)["blend"]
    assert d == {"status": "recorded", "is_primary": True, "n_inputs": 5, "weights_sum": 1.0,
                 "equal_weights": True, "cold_start": True, "no_input_scored": True,
                 "decomposition": "recorded_weights_and_points_only"}
    assert item["combined"] == before


# ---------------------------------------------------------------------------
# Producer seam + numerical invariance
# ---------------------------------------------------------------------------

def _strip(payload: dict) -> dict:
    out = copy.deepcopy(payload)
    for it in out["upcoming"]:
        it.pop("diagnostics", None)
    return out


def test_attach_is_additive_and_raw_output_is_byte_identical_without_it(fx):
    payload = {"schema": "release_forecast.v2", "upcoming": [copy.deepcopy(v) for v in fx["items"].values()]}
    original = json.dumps(payload, indent=2, default=str)
    work = copy.deepcopy(payload)
    snaps = fx["snapshots"]
    n = rd.attach_release_diagnostics(work["upcoming"], scoreboard=fx["scoreboard"],
                                      load_snapshot=snaps.get)
    assert n == len(payload["upcoming"])
    for before, after in zip(payload["upcoming"], work["upcoming"]):
        assert set(after) - set(before) == {"diagnostics"}
        assert list(after)[:-1] == list(before)
    assert json.dumps(_strip(work), indent=2, default=str) == original


def test_attach_failure_is_explicit_and_annotated(fx, capsys, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("x")
    monkeypatch.setattr(rd, "build_item_diagnostics", boom)
    items = [_item(fx, "cpi_headline_2026_08")]
    assert rd.attach_release_diagnostics(items) == 1
    assert items[0]["diagnostics"]["status"] == "error"
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert lines and all(ln.startswith("::warning title=release-diagnostics::") for ln in lines)


def test_snapshot_loader_is_confined_to_the_snapshot_directory(tmp_path):
    snap_dir = tmp_path / "data" / "release_forecast" / "input_snapshots"
    snap_dir.mkdir(parents=True)
    (snap_dir / "OK.json").write_text('{"asof": "2026-09-10"}', encoding="utf-8")
    (tmp_path / "secret.json").write_text('{"asof": "2026-09-10"}', encoding="utf-8")
    (snap_dir / "list.json").write_text("[1]", encoding="utf-8")
    load = rd.snapshot_loader(tmp_path)
    assert load("data/release_forecast/input_snapshots/OK.json") == {"asof": "2026-09-10"}
    assert load("data/release_forecast/input_snapshots/../../../secret.json") is None
    assert load("secret.json") is None
    assert load("data/release_forecast/input_snapshots/list.json") is None
    assert load("data/release_forecast/input_snapshots/missing.json") is None


def test_producer_has_exactly_one_seam_after_every_numerical_consumer():
    src = PRODUCER.read_text(encoding="utf-8")
    assert src.count("attach_release_diagnostics(") == 1
    assert "from engine.release_diagnostics import" not in src.split("def build(", 1)[0]
    tree = ast.parse(src)
    build_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build")
    body_src = ast.get_source_segment(src, build_fn)
    i_call = body_src.index("attach_release_diagnostics(")
    for consumer in ("_build_projection_ledger_rows(", "_build_shadow_ledger_rows(",
                     "_build_scoreboard(", "_latest_by_release(clean_scored)"):
        assert body_src.index(consumer) < i_call, consumer
    assert i_call < body_src.index("latest = {")
    assert body_src.count('"diagnostics"') == 0 and body_src.count("['diagnostics']") == 0
    literal = body_src[body_src.index("latest = {"):body_src.index("if not dry_run:", body_src.index("latest = {"))]
    assert "diagnostics" not in literal


def _producer_run(fx, root: Path, monkeypatch, *, seam: bool) -> None:
    """One real ``build()`` over the verbatim fixture items, clock frozen, no
    network: only ``_find_upcoming_releases`` / ``_build_upcoming_block`` /
    ``_read_policy_backdrop`` are stubbed; every enrichment, ledger, scoring and
    scoreboard step runs for real against a repo-shaped temp root."""
    import datetime as _dt
    import scripts.build_release_forecast as producer

    class _Day(_dt.date):
        @classmethod
        def today(cls):
            return cls(2026, 9, 10)

    class _Clock(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 10, 10, 5, 21, tzinfo=tz)

    for sub in ("data/release_forecast", "data/cleveland_nowcast", "data/regime",
                "data/fred_vintage", "site/macrodata"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    items = [copy.deepcopy(v) for v in fx["items"].values()]
    monkeypatch.setattr(producer, "date", _Day)
    monkeypatch.setattr(producer, "datetime", _Clock)
    monkeypatch.setattr(producer, "_find_upcoming_releases", lambda *a, **k: [])
    monkeypatch.setattr(producer, "_build_upcoming_block", lambda *a, **k: copy.deepcopy(items))
    monkeypatch.setattr(producer, "_read_policy_backdrop", lambda *a, **k: {
        "fed_stance": None, "gap_bp": None, "implied_cuts_12m": None,
        "next_fomc": None, "guidance_direction": None})
    if not seam:
        monkeypatch.setattr(rd, "attach_release_diagnostics", lambda *a, **k: 0)
    producer.build(root, dry_run=False)


def test_producer_output_is_numerically_invariant_to_the_seam(fx, tmp_path, monkeypatch):
    """Raw-output deep equality at the producer: the written latest.json minus the
    subtree is byte-identical to a seam-less run, and every numerical artifact
    (forward ledger, scoreboard) is byte-identical outright."""
    with_root, without_root = tmp_path / "with", tmp_path / "without"
    with monkeypatch.context() as mp:
        _producer_run(fx, with_root, mp, seam=True)
    with monkeypatch.context() as mp:
        _producer_run(fx, without_root, mp, seam=False)
    rel = "data/release_forecast"
    latest_with = json.loads((with_root / rel / "latest.json").read_text(encoding="utf-8"))
    latest_without_bytes = (without_root / rel / "latest.json").read_text(encoding="utf-8")
    assert latest_with["upcoming"], "the fixture items must reach the artifact"
    for item in latest_with["upcoming"]:
        assert item["diagnostics"]["schema"] == rd.SCHEMA
    assert json.dumps(_strip(latest_with), indent=2, default=str) == latest_without_bytes
    for name in ("forward_ledger.jsonl", "scoreboard.json"):
        a = (with_root / rel / name).read_bytes()
        b = (without_root / rel / name).read_bytes()
        assert a.strip(), f"{name} must be non-empty or the comparison proves nothing"
        assert a == b, name
        assert b"diagnostics" not in a, name
    ledger_rows = [json.loads(ln) for ln in (with_root / rel / "forward_ledger.jsonl").read_text(
        encoding="utf-8").splitlines() if ln.strip()]
    assert sum(1 for r in ledger_rows if r.get("row_type") == "projection") >= 5
    site = (with_root / "site" / "macrodata" / "release_forecast.json").read_text(encoding="utf-8")
    assert site == (with_root / rel / "latest.json").read_text(encoding="utf-8")
    # the verified input date is the producer's own snapshot, written this run
    cpi = next(i for i in latest_with["upcoming"]
               if i["release_type"] == "cpi_headline" and i["period"] == "2026-08")
    assert cpi["diagnostics"]["cutoff"]["status"] == "verified"
    assert cpi["diagnostics"]["cutoff"]["inputs_asof"] == "2026-09-10"


def test_ledger_rows_do_not_see_the_subtree(fx):
    from scripts.build_release_forecast import _build_projection_ledger_rows
    block = [copy.deepcopy(v) for v in fx["items"].values() if v.get("release_date")]
    with_diag = copy.deepcopy(block)
    rd.attach_release_diagnostics(with_diag, scoreboard=fx["scoreboard"])
    today = date(2026, 9, 10)
    plain_rows = _build_projection_ledger_rows(today, block, {})
    diag_rows = _build_projection_ledger_rows(today, with_diag, {})
    assert json.dumps(plain_rows, sort_keys=True, default=str) == json.dumps(diag_rows, sort_keys=True, default=str)
    assert "diagnostics" not in json.dumps(diag_rows, default=str)


def test_no_numerical_module_reads_the_subtree():
    offenders = []
    for path in list((REPO / "engine").rglob("*.py")) + [PRODUCER]:
        if path.name == "release_diagnostics.py":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"""\[\s*["']diagnostics["']\s*\]|\.get\(\s*["']diagnostics["']""", text) and \
                "release" in path.name:
            offenders.append(str(path.relative_to(REPO)))
    assert offenders == []


# ---------------------------------------------------------------------------
# Drift pins between the adapter's tables and the code they describe
# ---------------------------------------------------------------------------

def test_block_roles_match_the_frozen_block_confidence_weights():
    from engine.release_components_cpi import _BLOCK_CONFIDENCE_WEIGHT
    role_of_weight = {1.0: "direct_price", 0.6: "leading_proxy", 0.0: "persistence"}
    assert {b: role_of_weight[w] for b, w in _BLOCK_CONFIDENCE_WEIGHT.items()} == rd.BLOCK_ROLE


def test_coherent_targets_and_t_minus_one_contract_are_pinned():
    import scripts.build_release_forecast as producer
    assert set(rd.COHERENT_TARGETS) == set(producer._SHADOW_COHERENT_RIDGE_TARGETS)
    shadow_src = (REPO / "engine" / "release_cpi_coherent_shadow.py").read_text(encoding="utf-8")
    assert "live_release_date - timedelta(days=1) != decision_asof" in shadow_src


def test_renderer_selection_helpers_are_mirrored_verbatim():
    """The adapter mirrors the renderer's selection policy; if the renderer's
    policy moves, this pin reds so the mirror moves with it."""
    body = " ".join(_renderer_source().split())
    assert ("return !!(item && item.primary_forecast_basis === 'combined_v1_benchmark_augmented' "
            "&& comb && comb.combined_point != null);") in body
    assert "if (!contextBasis) return primaryBasis !== 'combined_v1_benchmark_augmented';" in body


# ---------------------------------------------------------------------------
# Red-team round 2 (independent Opus review of head 7d3d9121)
# ---------------------------------------------------------------------------

def test_no_point_means_no_band_anywhere(fx, tmp_path):
    """The producer centres quantiles on 0.0 when the point is missing
    (engine/release_forecast.py ``_compute_quantiles(errors, 0.0)``): residual
    spread, not a band for this release."""
    item = _item(fx, "nfp_2026_09")
    assert item["projection"]["point"] is None and item["projection"]["p10"] < 0 < item["projection"]["p90"]
    prim = rd.build_item_diagnostics(item)["primary"]
    assert prim["status"] == "unavailable"
    assert prim["band_80"] == prim["band_50"] == {"status": "unavailable", "reason": "point_unavailable"}
    for variant in (item, _with_diag(fx, item)):
        overview = _pane(_modal(variant, tmp_path), "t0")
        assert "No point forecast for this release, so no median or band is shown." in overview
        assert "本次发布无点预测，因此不显示中位数或区间。" in overview
        assert "Nominal 80% band" not in overview and "Median (p50)" not in overview
        assert "<svg" not in overview


def test_market_identity_needs_structure_on_both_sides_and_a_matching_unit(fx):
    item = _item(fx, "cpi_core_2026_09")
    mi = item["benchmark_set"]["market_implied"]
    mi.update(period=item["period"], implied_median=0.3)
    item.pop("target", None)
    got = rd.build_item_diagnostics(item)["benchmarks"]["market_implied"]
    assert got["status"] == "unverified_identity" and got["reason"] == "incomplete_structured_identity"
    item = _item(fx, "cpi_core_2026_09")
    item["benchmark_set"]["market_implied"].update(period=item["period"], target=item["target"],
                                                   unit="yoy_pct", implied_median=0.3)
    got = rd.build_item_diagnostics(item)["benchmarks"]["market_implied"]
    assert (got["status"], got["reason"]) == ("incompatible", "unit_mismatch")
    item["benchmark_set"]["market_implied"]["unit"] = item["target"]
    assert rd.build_item_diagnostics(item)["benchmarks"]["market_implied"]["status"] == "verified"
    assert got["raw_ref"] == "benchmark_set.market_implied"


def test_performance_lane_needs_full_identity_and_a_well_formed_entry(fx):
    lane = "cpi_headline:combined_v1:combined_v1_legacy_target_v1:mixed_legacy_cross_vintage_v0"
    def perf(entry, item=None):
        board = {"by_shadow_epoch": {lane: {"by_cutoff": {"T-1": entry}}}}
        return rd.build_item_diagnostics(item or _item(fx, "cpi_headline_2026_08"), scoreboard=board)["performance"]
    assert perf({"n": -2, "mae_ours": 0.1})["reason"] == "malformed_lane_entry"
    assert perf({"n": 2, "mae_ours": -0.1})["reason"] == "malformed_lane_entry"
    assert perf({"n": True, "mae_ours": 0.1})["reason"] == "malformed_lane_entry"
    assert perf({"n": 0, "mae_ours": None})["reason"] == "no_scored_releases_in_exact_lane"
    item = _item(fx, "cpi_headline_2026_08")
    item["combined"].pop("model_epoch", None)
    got = perf({"n": 2, "mae_ours": 0.1}, item)
    assert got["status"] == "unavailable" and got["reason"] == "lane_identity_incomplete"


def test_a_receipt_for_another_forecast_reads_as_not_recorded(fx, tmp_path):
    item = _with_diag(fx, _item(fx, "cpi_headline_2026_08"))
    assert item["diagnostics"]["primary"]["basis"] == "combined_v1_benchmark_augmented"
    item["diagnostics"]["primary"]["basis"] = "champion"   # stale or foreign receipt
    modal = _modal(item, tmp_path)
    overview = _pane(modal, "t0")
    assert "Input checks not recorded for this forecast." in overview
    assert "No scored record yet for this exact model" not in _pane(modal, "t3")


def test_malformed_counts_and_unknown_statuses_never_reach_the_page(fx, tmp_path):
    item = _with_diag(fx, _item(fx, "cpi_headline_2026_08"))
    inp = item["diagnostics"]["inputs"]
    inp["present"] = "9"
    inp["economic_coverage"] = {"status": "weird_internal_code"}
    item["diagnostics"]["performance"] = {"status": "available", "n": None, "mae_pp": 0.1}
    modal = _modal(item, tmp_path)
    overview = _pane(modal, "t0")
    assert "undefined" not in overview and "weird_internal_code" not in overview
    assert "not recorded" in overview and "不可用" in overview
    history = _pane(modal, "t3")
    assert "null" not in history and "scored release" not in history
    assert "Track record unavailable for this forecast." in history


def test_history_never_claims_a_model_lane_without_a_model(fx, tmp_path):
    retail = _with_diag(fx, _item(fx, "retail_sales_nodata"))
    history = _pane(_modal(retail, tmp_path), "t3")
    assert "No model forecast to score." in history and "this exact model" not in history
    overview = _pane(_modal(retail, tmp_path), "t0")
    assert not re.search(r"·\s*·", re.sub(r"<[^>]+>", "", overview))
    pce = _with_diag(fx, _item(fx, "pce_headline_2026_08"))
    assert pce["diagnostics"]["performance"]["reason"] == "horizon_not_scored"
    history = _pane(_modal(pce, tmp_path), "t3")
    assert "Only the forecast frozen the day before release is scored" in history
    assert "仅对发布前一日冻结的预测评分" in history


def test_bridge_waterfall_names_the_forecast_it_explains(fx, tmp_path):
    item = _with_diag(fx, _item(fx, "cpi_headline_2026_08"))
    comp = _pane(_modal(item, tmp_path), "t2")
    assert "breakdown of its own forecast (0.20%)" in comp
    assert "it does not explain the champion or the displayed blend" in comp
    assert "并不解释冠军模型或所显示的混合预测" in comp


def test_benchmark_gap_uses_the_true_median_and_no_signed_zero(fx, tmp_path):
    item = _with_diag(fx, _item(fx, "cpi_headline_2026_08"))
    bs = item["benchmark_set"]
    vals = sorted(v for v in (bs.get(k) for k in ("naive_prior", "trailing_3m", "ar_model",
                                                  "cleveland_nowcast", "expanding_mean"))
                  if isinstance(v, float))
    assert len(vals) % 2 == 0
    median = (vals[len(vals) // 2 - 1] + vals[len(vals) // 2]) / 2
    delta = item["combined"]["combined_point"] - median
    overview = _pane(_modal(item, tmp_path), "t0")
    assert f"{delta:+.2f}pp" in overview and "相对基准中位数" in overview
    assert "vs基准" not in overview
    item["benchmark_set"]["naive_prior"] = -0.0001
    models = _pane(_modal(item, tmp_path), "t1")
    assert "-0.00" not in models and "0.00%" in models


def test_an_expectation_column_names_its_source(fx, tmp_path):
    item = _item(fx, "cpi_headline_2026_08")
    item["expectation_read"] = {"expectation_median": 0.31, "sources": []}
    card = _card(item, tmp_path)
    assert "nowcast" not in card.lower() and "临近预测" not in card
    item["expectation_read"] = {"expectation_median": 0.31, "sources": ["cleveland_nowcast"]}
    assert "Cleveland" in _card(item, tmp_path)
