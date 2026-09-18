"""W12 r1: Institutional visits L1 block is DELETED (packet C2).

The visit state machine still lives on each command-list row
(engine/china_intel_hub.py) and is covered by test_china_intel_hub_visits.py.
This file pins the composition landing: the hub page must not render the
duplicate L1 visits section.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_china_intel import _env  # noqa: E402


def _b_fixture() -> dict:
    return {
        "asof": "2026-08-20",
        "schema": "china_intel.briefing.v6",
        "regime": None, "policy": None, "news": None,
        "max_staleness_days": None,
        "max_staleness_feed": None,
        "max_staleness_feed_asof": None,
        "stale_working_feeds": [],
        "surfaces_present": [], "surface_asof": {},
        "policy_phrase": None, "narrative_divergence": None,
        "salience": None, "what_changed": None, "conviction": None,
        "analysis": None, "flagged_tickers": None,
        "special_situations": None, "analogs": None, "digest": None,
        "disclaimer": "Context only.", "disclaimer_zh": "仅供参考。",
    }


def _cmd_row(ticker: str, name: str, visits: dict) -> dict:
    return {
        "ticker": ticker, "name": name, "stage": "quiet",
        "opportunity_score": 10.0, "edge_remaining": 0.5,
        "desk_matrix": {}, "traj": None, "read": "context only",
        "read_zh": "仅供参考", "falsifier": None, "veto_blind": False,
        "visits": visits,
    }


def _cmd_full_fixture() -> dict:
    return {
        "command": [
            _cmd_row("600519.SS", "贵州茅台",
                     {"state": "ok", "coverage_start": "2026-08-01",
                      "recent": [], "n_total": 0}),
            _cmd_row("000001.SZ", "平安银行",
                     {"state": "stale", "stale_days": 7,
                      "coverage_start": "2026-08-01", "recent": []}),
        ],
        "discovery": [],
        "visits_coverage_start": "2026-08-01",
        "n_universe": 2,
        "counts": {"emerging": 0, "early": 0, "veto_blind": 0},
    }


def _render(cmd_full=None) -> str:
    tmpl = _env().get_template("china_intel.html.j2")
    resolved = _cmd_full_fixture() if cmd_full is None else cmd_full
    return tmpl.render(b=_b_fixture(), cmd_full=resolved)


def test_renders_without_exception():
    html = _render()
    assert len(html) > 2000


def test_renders_with_no_cmd_full():
    html = _render(cmd_full=None)
    assert "Institutional visits" not in html


def test_l1_omits_institutional_visits_both_lanes():
    html = _render()
    assert "Institutional visits" not in html
    assert ">机构调研<" not in html
    assert "Investor-relations visit filings" not in html
    # C2 landing: the section heading is gone; visit copy is not at rest
    assert "Visit records last refreshed" not in html
    assert "调研记录最近一次刷新于" not in html
    assert "Visit records: status" not in html
