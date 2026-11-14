"""Point-in-time readmission guard and historical Observatory projection.

This module deliberately does not fit trading thresholds or change authority.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from admin.prophet import _learning_loop, _reentry_case_rows
from scripts.prophet_postmortem import _mark_at, _mark_with_observation_date


def _prior(series, entry=100.0):
    return {"sc": {"entry": entry, "entry_date": str(series.index[0].date())},
            "series": series}


def test_prior_mark_never_reads_a_future_close():
    closes = pd.Series(
        [100.0, 79.0],
        index=pd.to_datetime(["2026-07-02", "2026-07-06"]),
    )
    assert _mark_at(_prior(closes), "2026-07-01") is None
    # Friday 07-03 has no bar: use Thursday's known close, not Monday's -21%.
    assert _mark_at(_prior(closes), "2026-07-03") == pytest.approx(0.0)
    assert _mark_at(_prior(closes), "2026-07-06") == pytest.approx(-21.0)
    assert _mark_with_observation_date(_prior(closes), "2026-07-03") == (
        pytest.approx(0.0), "2026-07-02",
    )
    # A previous signal with an unfilled position has no meaningful P/L.
    pending = {"sc": {"entry": 100.0, "entry_date": "2026-07-06"},
               "series": closes}
    assert _mark_with_observation_date(pending, "2026-07-03") == (None, None)


@pytest.mark.parametrize("prices", [[float("nan")], [0.0], [-1.0]])
def test_prior_mark_rejects_missing_or_invalid_close(prices):
    closes = pd.Series(prices, index=pd.to_datetime(["2026-07-03"]))
    assert _mark_at(_prior(closes), "2026-07-03") is None


def test_case_projection_is_hindsight_only_and_matured():
    hindsight = {
        "ticker": "IPGP", "entry_date": "2026-07-15", "maturity": "matured",
        "cohort": "loser", "outcome_pct": -17.86,
        "prior_episode": {
            "entry_date": "2026-07-10",
            "mark_at_readmit_pct": 3.04, "outcome_pct": -14.35,
        },
        "entry_context": {
            "sector_basket": {"reco": "avoid"},
            "entry_plan": {"status": "await_confluence"},
        },
        "labels": [
            {"label": "sector_headwind", "trigger": {}},
            {"label": "re_admission", "trigger": {"leg": "prior_episode_loss"}},
        ],
    }
    buildable = {
        **hindsight,
        "ticker": "OTHER",
        "labels": [{"label": "re_admission", "trigger": {
            "leg": "open_drawdown_at_readmit"}}],
    }
    open_hindsight = {**hindsight, "ticker": "OPEN", "maturity": "in_flight"}
    rows = _reentry_case_rows({"episodes": [hindsight, buildable, open_hindsight]})
    assert len(rows) == 1
    assert rows[0] == {
        "ticker": "IPGP", "entry_date": "2026-07-15", "cohort": "loser",
        "outcome_pct": -17.86, "prior_entry_date": "2026-07-10",
        "prior_mark_at_readmit_pct": 3.04,
        "prior_mark_observation_date": None,
        "prior_resolved_outcome_pct": -14.35,
        "sector_reco_at_entry": "avoid",
        "entry_status_at_entry": "await_confluence",
        "evidence": "hindsight_upper_bound",
    }


def test_learning_loop_keeps_variant_and_artifact_vintage(tmp_path: Path):
    artifact = tmp_path / "data" / "prophet_postmortem" / "summary.json"
    artifact.parent.mkdir(parents=True)
    doc = {
        "schema": "prophet_postmortem/v1", "as_of": "2026-07-31",
        "method": {"horizon": 10, "fill": "next session close",
                   "exit_rule": "forced verdict at horizon", "llm_used": False},
        "summary": {"n_episodes": 808, "n_matured": 610,
                    "n_board_dates": 24, "cohorts": {"n_losers": 132,
                                                   "n_winners": 91},
                    "veto_cost": [
                        {"key": "re_admission:open_drawdown_at_readmit",
                         "label": "re_admission", "leg": "open_drawdown_at_readmit",
                         "variant": "buildable", "visible_at_entry": True,
                         "n_flagged": 0, "n_universe": 610},
                        {"key": "re_admission:prior_episode_loss",
                         "label": "re_admission", "leg": "prior_episode_loss",
                         "variant": "hindsight_upper_bound",
                         "visible_at_entry": False, "n_flagged": 8,
                         "n_universe": 610, "net_pct_if_vetoed": 86.53},
                    ]},
        "episodes": [],
    }
    artifact.write_text(json.dumps(doc))
    ll = _learning_loop(tmp_path)
    assert ll is not None and ll["as_of"] == "2026-07-31"
    assert [v["variant"] for v in ll["veto_cost"]] == [
        "buildable", "hindsight_upper_bound",
    ]
    assert ll["veto_cost"][1]["net_pct_if_vetoed"] == 86.53
    assert ll["reentry_cases"] == []
    assert ll["measurement_basis"]["authority"] == "measurement_only"


def test_observatory_source_renders_hindsight_and_vintage_cues():
    js = (Path(__file__).resolve().parents[1]
          / "admin" / "static" / "app.js").read_text(encoding="utf-8")
    assert 'v.variant === "hindsight_upper_bound"' in js
    assert "Hindsight only" in js
    assert "Historical snapshot — as of" in js
    assert "llCaseRows.map(" in js
    assert "Upper bound " in js


def test_observatory_dynamic_render_and_html_escaping():
    """Execute the actual read-only template block in Node when available."""
    if shutil.which("node") is None:
        pytest.skip("node unavailable; source-contract checks still run")
    js = (Path(__file__).resolve().parents[1]
          / "admin" / "static" / "app.js")
    runner = r"""
const fs = require('node:fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
const start = source.indexOf('  const llAsOf =');
const end = source.indexOf('  /* --- Fable spend meter --- */', start);
if (start < 0 || end < start) throw Error('learning-loop renderer absent');
const render = new Function('ll', 'd', 'esc',
  source.slice(start, end) + '\nreturn llHtml;');
const esc = s => String(s == null ? '' : s)
  .replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const ll = {
  as_of: '2026-07-31', n_episodes:808, n_matured:610,
  n_in_flight:194, n_board_dates:24, n_losers:132, n_winners:91,
  horizon:10, labels:[],
  veto_cost: [
    {en:'Prior already underwater', leg:'open_drawdown_at_readmit',
     variant:'buildable', visible_at_entry:true,
     n_flagged:0, n_universe:610, net_pct_if_vetoed:0},
    {en:'Prior eventually lost', leg:'prior_episode_loss',
     variant:'hindsight_upper_bound', visible_at_entry:false,
     n_flagged:8, n_universe:610, net_pct_if_vetoed:86.53},
  ],
  reentry_cases:[{ticker:'<img src=x>', entry_date:'2026-07-15',
    prior_mark_at_readmit_pct:3.04, prior_mark_observation_date:null,
    outcome_pct:-17.86, sector_reco_at_entry:'avoid',
    entry_status_at_entry:'await_confluence'}],
};
const html = render(ll, {}, esc);
const checks = [
  html.includes('Historical snapshot — as of 2026-07-31'),
  html.includes('Hindsight only'), html.includes('Known at entry'),
  html.includes('Upper bound +86.53pp'),
  html.includes('0 / 610'),
  html.includes('Observed close date'),
  html.includes('not recorded'),
  html.includes('&lt;img src=x&gt;') && !html.includes('<img src=x>'),
];
if (checks.some(x => !x)) throw Error('display regression: ' + JSON.stringify(checks));
"""
    result = subprocess.run(
        ["node", "-e", runner, str(js)], check=False, capture_output=True,
        text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr[:1200]
