"""Actual builder/template seam, with supplied frames and no external data I/O."""
from copy import deepcopy
from pathlib import Path
import json
import sys

import pandas as pd
import pytest
from jinja2 import Environment, FileSystemLoader

from engine import i18n, intl_inputs
from engine.intl_performance_records import build_return_records
from engine.intl_workspace_overview import build_overview, build_workspace_overviews as _workspace_overviews
from lib import store

ROOT = Path(__file__).resolve().parents[1]


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


def render_fixture(mode="macro", workspace=True, state="unknown"):
    """Public synthetic empty-owner fixture; never a qualification receipt."""
    summary = {"n": 0, "dominant_quad": "unknown", "recession_watch": 0, "drawdown_watch": 0}
    vm = {"latest": {"date": "fixture", "records": [], "summary": summary},
          "built": "fixture", "records": [], "summary": summary, "rankings": {},
          "heatmap": [], "periphery": None, "sector_board": [], "setups": {},
          "global_regime_html": '<section id="fixture-owner-fragment">Existing research</section>'}
    if workspace:
        vm["intl_workspace"] = _workspace_overviews(None) if state == "unknown" else synthetic_qualified_workspace(state)
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    env.globals.update(t=i18n.t, tr=i18n.tr, td=i18n.td)
    return env.get_template("intl.html.j2").render(**vm, mode=mode)


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


if __name__ == "__main__":
    # Browser runner consumes the same real-template fixture, not a DOM imitation.
    sys.stdout.write(render_fixture(sys.argv[1] if len(sys.argv) > 1 else "macro",
                                   state=sys.argv[2] if len(sys.argv) > 2 else "unknown"))
