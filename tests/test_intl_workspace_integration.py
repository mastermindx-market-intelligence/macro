"""Actual builder/template seam, with supplied frames and no external data I/O."""
from copy import deepcopy
from pathlib import Path
import json
import sys

import pandas as pd
import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from engine import i18n, intl_inputs
from engine.intl_performance_records import build_return_records
from engine.intl_workspace_overview import build_overview, build_workspace_overviews as _workspace_overviews
from lib import store
from lib.intl_library_mount import render_international_pages

ROOT = Path(__file__).resolve().parents[1]
# Reuse compiled templates across cases, as the production builder does. Keep
# source reload checks enabled; view models and rendered HTML are never cached.
RENDER_ENV = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                         autoescape=False, auto_reload=True)


def synthetic_qualified_workspace(state="qualified"):
    """Explicitly synthetic qualification; used only to exercise presentation."""
    countries = intl_inputs.countries()
    columns = {}
    for position, country in enumerate(countries.values()):
        direction = -1 if state == "negative" else (-1 if position % 2 else 1)
        columns[country["index"]] = [100 + direction * i * (position + 1) / 100 for i in range(260)]
        columns[country["fx"]] = [100.] * 260
    frame = pd.DataFrame(columns, index=pd.date_range("2025-06-01", periods=260))
    raw = build_return_records(frame, market_ids=list(countries), source_reference="synthetic:visual-fixture")
    qualifications = []
    for record in raw["records"]:
        if record["horizon"] != "1m":
            continue
        for leg in ("local", "usd", "fx_contribution"):
            metric = record[leg]
            qualifications.append({
                "binding": {"source_reference": raw["source_reference"], "market_id": record["market_id"],
                            "index_id": record["index_id"], "fx_id": record["fx_id"], "horizon": "1m",
                            "currency_basis": "usd_unhedged", "return_basis": "price", "leg": leg,
                            "value": metric["value"], "unit": metric["unit"], "window": deepcopy(metric["window"])},
                "owner_ref": "synthetic:owner", "policy_ref": "synthetic:policy", "decision_ref": "synthetic:decision",
                "quality": "denied" if state == "denied" else "qualified", "reason": "synthetic_denial" if state == "denied" else None,
                "disclosure": {"metadata": "denied" if state == "denied" else "allowed",
                               "value": "denied" if state == "denied" else "allowed"}})
    result = _workspace_overviews(None)
    result["config"].update(horizons=["1m"], bases=["usd_unhedged"], source_reference=raw["source_reference"])
    view = build_overview(raw, roster=[{"market_id": cc, "name_en": item["name"], "name_zh": item["name_zh"]}
                                     for cc, item in countries.items()],
                          context={"horizon": "1m", "currency_basis": "usd_unhedged", "return_basis": "price",
                                   "source_reference": raw["source_reference"]}, qualifications=qualifications)
    # The display context may redact the source; the controller must bind those exact disclosed bytes.
    result["config"]["source_reference"] = view["context"]["source_reference"]
    result["panels"] = [{"context_id": "synthetic-state", "overview": view}]
    return result


def render_fixture(mode="macro", workspace=True, state="unknown", perf=None, cgl=None, turn_board=None, rates=None, risk_desk=None, heatmap=None, rotation_ranks=None, records=None, workspace_payload=None, chart_sources=None):
    """Public synthetic empty-owner fixture; never a qualification receipt."""
    summary = {"n": 0, "dominant_quad": "unknown", "recession_watch": 0, "drawdown_watch": 0}
    vm = {"latest": {"date": "fixture", "records": [], "summary": summary},
          "built": "fixture", "records": [], "summary": summary, "rankings": {},
          "heatmap": [], "periphery": None, "sector_board": [], "setups": {},
          "global_regime_html": '<section id="fixture-owner-fragment">Existing research</section>'}
    if records is not None:
        vm["records"] = records
        vm["latest"]["records"] = records
    if rotation_ranks is not None:
        vm["rotation_ranks"] = rotation_ranks
    if heatmap is not None:
        vm["heatmap"] = heatmap
    if perf is not None:
        vm["perf"] = perf
    if cgl is not None:
        vm["CGL"] = cgl
    if turn_board is not None:
        vm["turn_board"] = turn_board
    if rates is not None:
        vm["rates"] = rates
    if risk_desk is not None:
        vm["risk_desk"] = risk_desk
    if workspace:
        vm["intl_workspace"] = workspace_payload if workspace_payload is not None else (_workspace_overviews(None) if state == "unknown" else synthetic_qualified_workspace(state))
    env = RENDER_ENV
    env.globals.update(t=i18n.t, tr=i18n.tr, td=i18n.td)
    catalogue = json.loads((ROOT / "config/intl_library_catalogue.json").read_text())
    pages = render_international_pages(env.get_template("intl.html.j2"), vm, catalogue=catalogue, chart_sources=chart_sources)
    return pages[1] if mode == "stocks" else pages[0]



def library_recovery_fixture():
    """Supplied synthetic owner assessments; no data I/O or qualification."""
    from engine.intl_recovery_quality import apply_recovery_naming
    states = {
        "JP": dict(state="recovery", above_ma20=True, macd_state="bull", mom20_pct=8.2),
        "HK": dict(state="recovery", above_ma20=False, macd_state="bear", mom20_pct=-1.0),
        "AU": dict(state="uptrend", state_en="Uptrend", state_zh="上升趋势",
                   stance_en="Trend intact", stance_zh="趋势完好", mom20_pct=2.0),
    }
    apply_recovery_naming(states)
    names = {"JP": ("Japan", "日本"), "HK": ("Hong Kong", "香港"), "AU": ("Australia", "澳大利亚")}
    return [dict(s, cc=cc, name=names[cc][0], name_zh=names[cc][1], flag="",
                 since=None, peak_date=None, ext_pctile=None, dd_pct=None)
            for cc, s in states.items()]


@pytest.mark.parametrize("kind,expected", [
    ("absent", []), ("empty", []), ("no_assessment", []),
    ("partial_bilingual", ["HK"]), ("complete", ["JP", "HK"]),
])
def test_library_recovery_destination_preserves_supplied_assessments(kind, expected):
    rows = library_recovery_fixture()
    if kind == "absent": rows = None
    elif kind == "empty": rows = []
    elif kind == "no_assessment": rows = [rows[2]]
    elif kind == "partial_bilingual": rows[0]["recovery_assessment"].pop("read_zh")
    original = deepcopy(rows)
    soup = BeautifulSoup(render_fixture(turn_board=rows), "html.parser")
    tool = soup.select_one('[data-im-library-tool="recovery_quality"]')
    targets = soup.select('#intl-recovery-quality')
    assert len(targets) == int(bool(expected))
    assert bool(tool.select('a[href="#intl-recovery-quality"]')) == bool(expected)
    if expected:
        detail = targets[0].find_parent('details')
        assert detail is not None and not detail.has_attr('open')
        assert [n['data-recovery-market'] for n in detail.select('[data-recovery-market]')] == expected
        assert 'Partial coverage' in detail.get_text() and '部分覆盖' in detail.get_text()
        for row in rows:
            if row['cc'] not in expected: continue
            entry = detail.select_one('[data-recovery-market="'+row['cc']+'"]')
            assert row['name'] in entry.get_text() and row['name_zh'] in entry.get_text()
            for field in ('read_en','read_zh','label_en','label_zh','stance_en','stance_zh'):
                assert row['recovery_assessment'][field] in entry.get_text()
    from lib.intl_library_mount import attach_public_library
    catalogue = json.loads((ROOT / "config/intl_library_catalogue.json").read_text())
    bound = attach_public_library(_workspace_overviews(None), catalogue=catalogue,
                                  macro_html=str(soup), stocks_rendered=True)
    entry = next(t for t in bound["library"]["tools"] if t["presentation_key"] == "recovery_quality")
    assert entry["data_state"] == "unknown" and entry["metrics"] == []
    assert rows == original
    assert not BeautifulSoup(render_fixture(mode="stocks", turn_board=rows), 'html.parser').select('#intl-recovery-quality')


def library_trade_fixture():
    """Existing CGL render shape with explicit synthetic, non-qualified values."""
    from tests.test_contagion_card_render import _minimal_pressure_block
    return {"schema": "contagion_links.v1", "as_of": "synthetic:fixture",
            "pressure": {"jp": _minimal_pressure_block()},
            "severity": {}, "gaps": ["synthetic:missing-link"]}


@pytest.mark.parametrize("cgl,available", [
    (None, False), ({}, False),
    ({"schema": "contagion_links.v1", "pressure": {}, "gaps": []}, True),
    (library_trade_fixture(), True),
])
def test_library_trade_link_follows_rendered_panel_without_qualifying_data(cgl, available):
    original = deepcopy(cgl)
    soup = BeautifulSoup(render_fixture(cgl=cgl), "html.parser")
    target = soup.select("#intl-trade-supply-links")
    tool = soup.select_one('[data-im-library-tool="trade_supply_links"]')
    assert len(target) == int(available)
    assert bool(tool.select('a[href="#intl-trade-supply-links"]')) == available
    assert "model context" in tool.get_text().lower()
    assert "公司敞口" in tool.get_text()
    from lib.intl_library_mount import attach_public_library
    catalogue = json.loads((ROOT / "config/intl_library_catalogue.json").read_text())
    bound = attach_public_library(_workspace_overviews(None), catalogue=catalogue,
                                  macro_html=str(soup), stocks_rendered=True)
    entry = next(t for t in bound["library"]["tools"] if t["presentation_key"] == "trade_supply_links")
    assert entry["route_state"] == ("available" if available else "unavailable")
    assert entry["data_state"] == "unknown" and entry["metrics"] == []
    assert entry["interpretation_notice"] == "model_context_not_company_exposure"
    assert cgl == original
    assert not BeautifulSoup(render_fixture(mode="stocks", cgl=cgl), "html.parser").select("#intl-trade-supply-links")


def render_history_fixture(history_sources=None):
    """Real page with isolated synthetic EOD and explicit test-only History permissions."""
    from tempfile import TemporaryDirectory
    from unittest.mock import patch
    from scripts import build_intl
    from tests.test_intl_eod_publication import _setup, EVALUATED
    from tests.test_intl_history_mount import fixture as history_fixture
    _, args = history_fixture()
    with TemporaryDirectory(prefix="intl-history-layout-") as directory:
        data_root = Path(directory)
        frame, _ = _setup(data_root)
        workspace = build_intl._publication_workspace(
            frame, data_root=data_root, evaluated_at=EVALUATED,
            history_sources=args["sources"] if history_sources is None else history_sources)
        with patch(__name__ + "._workspace_overviews", return_value=workspace):
            return render_fixture()


@pytest.fixture(autouse=True)
def no_collector_or_store_reads(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("workspace composition attempted data I/O")
    monkeypatch.setattr(intl_inputs, "_intl_closes", forbidden)
    monkeypatch.setattr(store, "read", forbidden)


def test_supplied_numerics_do_not_invent_source_qualification_or_mutate_frame():
    frame = pd.DataFrame({"^N225": range(100, 135), "USDJPY=X": [100.] * 35},
                         index=pd.date_range("2026-01-01", periods=35))
    original = frame.copy(deep=True)
    result = _workspace_overviews(frame)
    pd.testing.assert_frame_equal(frame, original)
    assert result["config"]["markets"] == list(intl_inputs.countries())
    assert result["config"]["source_reference"] is None
    assert len(result["panels"]) == 2 * len(result["config"]["horizons"])
    assert len({panel["context_id"] for panel in result["panels"]}) == len(result["panels"])
    for panel in result["panels"]:
        view = panel["overview"]
        assert view["configured_count"] == len(intl_inputs.countries())
        assert view["eligible_count"] == 0 and view["focus_ids"] == []
        assert all(row["metric"]["value"] is None for row in view["rows"])
        assert all("index_id" not in row for row in view["rows"])
    json.dumps(result, allow_nan=False)


def test_empty_frame_retains_public_roster_and_explicit_unknown():
    result = _workspace_overviews(None)
    assert result["config"]["default_horizon"] in result["config"]["horizons"]
    assert result["config"]["bases"] == ["usd_unhedged", "local"]
    assert all(panel["overview"]["ranking_status"] == "unavailable" for panel in result["panels"])


def test_empty_configured_roster_has_no_workspace(monkeypatch):
    monkeypatch.setattr(intl_inputs, "countries", lambda: {})
    assert _workspace_overviews(None) is None


def test_actual_macro_template_mounts_once_and_retains_legacy_owner_fragment():
    html = render_fixture()
    assert html.count('data-im-workspace data-im-mode="macro"') == 1
    assert html.count('id="intl-legacy-research"') == 1
    assert '<details id="intl-legacy-research" open>' in html
    assert html.index('id="fixture-owner-fragment"') > html.index('id="intl-legacy-research"')
    assert 'data-im-controls disabled' in html
    assert 'Current returns unavailable' in html and '当前回报不可用' in html
    assert 'intl_stocks.html' in html
    for asset in ("intl_workspace.css", "intl_workspace_state.js", "intl_workspace.js", "intl_workspace_entry.js"):
        assert asset in html
        assert (ROOT / "templates" / asset).is_file()


def test_library_advertises_only_targets_in_actual_render_and_one_catalogue():
    from html.parser import HTMLParser
    class Destinations(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ids, self.hrefs = [], []
        def handle_starttag(self, tag, attrs):
            row = dict(attrs)
            if "id" in row:
                self.ids.append(row["id"])
            if "intl-library__tool-link" in row.get("class", ""):
                self.hrefs.append(row["href"])
    html = render_fixture()
    parsed = Destinations()
    parsed.feed(html)
    assert html.count("data-im-library-catalogue>") == 1
    assert html.count("data-im-library-tool=") == 18
    assert parsed.hrefs == ["#intl-cross-country", "#intl-growth-inflation", "/intl_stocks.html"]
    assert all(parsed.ids.count(href[1:]) == 1 for href in parsed.hrefs if href.startswith("#"))
    assert "data-view=\"library\" data-im-library-static" in html


def test_library_does_not_change_ordinary_stock_page_output():
    assert render_fixture("stocks") == render_fixture("stocks", workspace=False)


def test_mounted_workspace_inherits_the_shared_canvas_without_legacy_palette():
    mounted = render_fixture()
    assert '<body class="page-intl intl-workspace-page">' in mounted
    assert "--bg:#0a0c11" not in mounted
    assert "--bg:#e8ebf1" not in mounted
    for legacy in (render_fixture(workspace=False), render_fixture("stocks")):
        assert "--bg:#0a0c11" in legacy
        assert "--bg:#e8ebf1" in legacy
        assert '<body class="page-intl intl-workspace-page">' not in legacy


def test_stocks_mode_does_not_inherit_macro_workspace_or_hide_stock_tools():
    html = render_fixture("stocks")
    assert 'data-im-workspace' not in html
    assert 'id="intl-legacy-research"' not in html
    assert 'intl_workspace_entry.js' not in html
    assert "What to act on now" in html


def test_absent_workspace_keeps_incumbent_macro_render_without_wrapper():
    html = render_fixture(workspace=False)
    assert 'data-im-workspace' not in html and 'id="intl-legacy-research"' not in html
    assert 'id="fixture-owner-fragment"' in html
    assert "Cross-country comparison" in html and "Regime map" in html


@pytest.mark.parametrize("state", ["qualified", "negative"])
def test_synthetic_qualified_projection_exercises_four_focus_rows(state):
    view = synthetic_qualified_workspace(state)["panels"][0]["overview"]
    assert view["eligible_count"] == 7 and len(view["focus_ids"]) == 4
    html = render_fixture(state=state)
    assert html.count('data-im-focus-item ') == 4
    assert "Nikkei 225" in html
    if state == "negative":
        assert view["summary"]["positive_count"] == 0


def test_synthetic_denial_exercises_slot_only_presentation():
    view = synthetic_qualified_workspace("denied")["panels"][0]["overview"]
    assert view["focus_ids"] == [] and all(row["quality"] == "denied" for row in view["rows"])
    html = render_fixture(state="denied")
    assert html.count("data-im-market-denied") == 7
    assert "synthetic:visual-fixture" not in html and "Nikkei 225" not in html


def _compass_risk():
    return {"score": 54, "label_en": "Neutral", "label_zh": "中性", "tone": "flat",
            "coverage_pct": 100., "n_available": 10, "breadth_above_200d": "7/10",
            "median_mom_3m": 3.9, "top_drags": [
                {"flag": "🇺🇸", "name": "United States", "name_zh": "美国"}]}


def _render_compass(risk):
    perf = {"risk_appetite": deepcopy(risk), "global_read": None, "rrg": None,
            "correlation": None, "leaderboard": []}
    return render_fixture(perf=perf)


@pytest.mark.parametrize("missing", ["perf", "risk", "empty", "score", "score_key"])
def test_missing_world_risk_reading_is_unavailable_not_neutral(missing):
    risk = _compass_risk()
    if missing == "perf":
        html = render_fixture()
    else:
        if missing == "risk":
            risk = None
        elif missing == "empty":
            risk = {}
        else:
            # Retained labels/coverage cannot turn an absent reading into a signal.
            risk["score"] = None
            risk["top_drags"] = []
            if missing == "score_key":
                risk.pop("score")
        html = _render_compass(risk)
    compass = BeautifulSoup(html, "html.parser").select_one(".wc-left")
    assert compass.select_one(".wc-verdict .l-en").get_text() == "Unavailable"
    assert compass.select_one(".wc-verdict .l-zh").get_text() == "暂无数据"
    assert compass.select_one(".wc-gnum").get_text() == "—"
    assert compass.select_one(".wc-gauge-fill") is None
    assert compass.select_one(".wc-substance") is None
    assert not compass.select_one(".wc-gside").has_attr("data-tip-en")


@pytest.mark.parametrize("score,label_en,label_zh,tone", [
    (0, "Risk-off", "风险规避", "down"),
    (54, "Neutral", "中性", "flat"),
    (72, "Split tape", "市场分化", "warn"),
])
def test_real_world_risk_readings_preserve_engine_verdict(score, label_en, label_zh, tone):
    risk = _compass_risk()
    risk.update(score=score, label_en=label_en, label_zh=label_zh, tone=tone)
    html = _render_compass(risk)
    compass = BeautifulSoup(html, "html.parser").select_one(".wc-left")
    assert compass.select_one(".wc-verdict .l-en").get_text() == label_en
    assert compass.select_one(".wc-verdict .l-zh").get_text() == label_zh
    assert compass.select_one(".wc-gnum").get_text() == str(score)
    assert compass.select_one(".wc-gauge-fill") is not None
    assert "Dragged by" in compass.select_one(".wc-substance").get_text()
    assert "Weighs 10 markets" in compass.select_one(".wc-gside")["data-tip-en"]


if __name__ == "__main__":
    # Browser runner consumes the same real-template fixture, not a DOM imitation.
    sys.stdout.write(render_fixture(sys.argv[1] if len(sys.argv) > 1 else "macro",
                                   state=sys.argv[2] if len(sys.argv) > 2 else "unknown"))
