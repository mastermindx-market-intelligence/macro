"""tests/test_track_record_page.py — Prophet W1 unit tests.

Three suites:
1. Cohort rollup math — synthetic parquet fixture; assert win-rate/effective-n.
2. Accruing/data-gap paths — all inputs missing → page renders with placeholders.
3. Template render smoke test — full render with minimal fixture data.

SA-R16 never-raise contract: builder must not raise when every input is missing.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Helpers to import builder functions without touching the file system.
# ---------------------------------------------------------------------------
def _import_builder():
    """Import the builder module without triggering __main__ execution."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "build_track_record_page",
        ROOT / "scripts" / "build_track_record_page.py",
    )
    mod = importlib.util.load_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Suite 1: cohort rollup math
# ---------------------------------------------------------------------------

def _make_grades_df(rows: list[dict]):
    """Build a minimal retro_grades-shaped DataFrame from a list of dicts."""
    import pandas as pd

    return pd.DataFrame(rows)


def test_cohort_rollup_win_rate_simple():
    """3 wins out of 4 matured 5d rows → win_rate ~0.75."""
    import pandas as pd
    from scripts.build_track_record_page import _compute_cohort_rollup

    rows = [
        {"horizon": 5, "entry_date": "2026-06-16", "excess_spy": 0.02},
        {"horizon": 5, "entry_date": "2026-06-17", "excess_spy": 0.01},
        {"horizon": 5, "entry_date": "2026-06-18", "excess_spy": -0.01},
        {"horizon": 5, "entry_date": "2026-06-19", "excess_spy": 0.03},
        # Unmatured rows (NaN excess_spy)
        {"horizon": 5, "entry_date": "2026-07-01", "excess_spy": float("nan")},
        # Different horizon — should not appear in h5
        {"horizon": 10, "entry_date": "2026-06-16", "excess_spy": 0.05},
    ]
    df = _make_grades_df(rows)
    result = _compute_cohort_rollup(df)

    h5 = result["horizons"]["h5"]
    assert h5["raw_n"] == 4, f"Expected 4 matured h5 rows, got {h5['raw_n']}"
    assert abs(h5["win_rate"] - 0.75) < 0.01, f"Expected ~0.75 win rate, got {h5['win_rate']}"
    assert h5["accruing"], "effective_n < 3 for 4 rows in ~4 trading days → ACCRUING"


def test_cohort_rollup_effective_n_nonoverlapping():
    """Entries 21+ calendar days apart each count as a separate independent window."""
    import pandas as pd
    from scripts.build_track_record_page import _compute_cohort_rollup, _effective_n

    # Two entry dates >21 days apart → effective_n should be 2
    dates = ["2026-06-01", "2026-06-30"]  # 29 days apart
    eff_n = _effective_n(dates, horizon_days=21, session_dates=None)
    assert eff_n == 2, f"Expected 2 independent windows, got {eff_n}"

    # Two entry dates 5 days apart → effective_n should be 1
    dates_close = ["2026-06-01", "2026-06-05"]
    eff_n_close = _effective_n(dates_close, horizon_days=21, session_dates=None)
    assert eff_n_close == 1, f"Expected 1 window for close dates, got {eff_n_close}"


def test_cohort_rollup_all_horizons_not_present():
    """Only h5 data present → h10/h21/h63 all show accruing=True, raw_n=0."""
    from scripts.build_track_record_page import _compute_cohort_rollup

    rows = [
        {"horizon": 5, "entry_date": "2026-06-16", "excess_spy": 0.01},
    ]
    df = _make_grades_df(rows)
    result = _compute_cohort_rollup(df)

    for h in ["h10", "h21", "h63"]:
        cell = result["horizons"].get(h, {})
        assert cell.get("accruing", False), f"{h} should be accruing but got {cell}"
        assert cell.get("raw_n", 0) == 0


def test_cohort_rollup_empty_df():
    """Empty DataFrame → all horizons accruing."""
    import pandas as pd
    from scripts.build_track_record_page import _compute_cohort_rollup

    df = pd.DataFrame()
    result = _compute_cohort_rollup(df)
    assert result.get("accruing") is True


def test_cohort_rollup_none_df():
    """None input → returns accruing placeholder without raising."""
    from scripts.build_track_record_page import _compute_cohort_rollup

    result = _compute_cohort_rollup(None)
    assert result.get("accruing") is True
    assert "reason" in result


# ---------------------------------------------------------------------------
# Suite 2: data_gap / accruing paths (SA-R16 never-raise)
# ---------------------------------------------------------------------------

def test_build_never_raises_when_all_inputs_missing(tmp_path):
    """SA-R16: builder must complete without raising even when all inputs are absent."""
    import importlib

    # Monkey-patch paths to point at non-existent files inside tmp_path
    import scripts.build_track_record_page as builder

    orig_retro = builder.RETRO_GRADES
    orig_snapshots = builder.SNAPSHOTS_JSONL
    orig_track = builder.US_BOARD_TRACK
    orig_outcomes = builder.US_BOARD_OUTCOMES
    orig_scoreboard = builder.US_AUDIT_SCOREBOARD
    orig_attr = builder.US_ATTRIBUTION
    orig_out_json = builder.OUT_JSON
    orig_out_html = builder.OUT_HTML

    try:
        builder.RETRO_GRADES = tmp_path / "retro_grades.parquet"
        builder.SNAPSHOTS_JSONL = tmp_path / "snapshots.jsonl"
        builder.US_BOARD_TRACK = tmp_path / "us_board_track.json"
        builder.US_BOARD_OUTCOMES = tmp_path / "us_board_outcomes.json"
        builder.US_AUDIT_SCOREBOARD = tmp_path / "us_audit_scoreboard.json"
        builder.US_ATTRIBUTION = tmp_path / "us_attribution.parquet"
        builder.OUT_JSON = tmp_path / "us_track_history.json"
        builder.OUT_HTML = tmp_path / "us_track_record.html"

        # Must not raise
        rc = builder.build()
        assert rc == 0, f"Expected rc=0 even with missing inputs, got {rc}"

        # JSON output must exist
        assert builder.OUT_JSON.exists(), "us_track_history.json should be written even on data_gap"
        j = json.loads(builder.OUT_JSON.read_text())
        assert j.get("schema") == "us_track_history/v1"
        assert "as_of" in j

        # HTML output must exist
        assert builder.OUT_HTML.exists(), "us_track_record.html should be written even on data_gap"
        html = builder.OUT_HTML.read_text()
        assert len(html) > 500, "HTML should be non-trivial even in all-accruing state"
        # Must not contain unrendered Jinja
        import re
        unrendered = re.findall(r'\{\{[^}]+\}\}|\{%[^%]+%\}', html)
        assert not unrendered, f"Unrendered Jinja in output: {unrendered[:3]}"

    finally:
        builder.RETRO_GRADES = orig_retro
        builder.SNAPSHOTS_JSONL = orig_snapshots
        builder.US_BOARD_TRACK = orig_track
        builder.US_BOARD_OUTCOMES = orig_outcomes
        builder.US_AUDIT_SCOREBOARD = orig_scoreboard
        builder.US_ATTRIBUTION = orig_attr
        builder.OUT_JSON = orig_out_json
        builder.OUT_HTML = orig_out_html


def test_json_output_has_required_fields(tmp_path):
    """us_track_history.json must include schema, as_of, and block flags."""
    import scripts.build_track_record_page as builder

    orig_out_json = builder.OUT_JSON
    orig_out_html = builder.OUT_HTML
    orig_retro = builder.RETRO_GRADES

    try:
        builder.RETRO_GRADES = tmp_path / "retro_grades.parquet"  # absent
        builder.OUT_JSON = tmp_path / "us_track_history.json"
        builder.OUT_HTML = tmp_path / "us_track_record.html"

        builder.build()

        j = json.loads(builder.OUT_JSON.read_text())
        assert j["schema"] == "us_track_history/v1"
        assert "as_of" in j
        assert "cohort_rollup" in j
        assert "board_series" in j
        assert "failure_mix" in j
    finally:
        builder.OUT_JSON = orig_out_json
        builder.OUT_HTML = orig_out_html
        builder.RETRO_GRADES = orig_retro


# ---------------------------------------------------------------------------
# Suite 3: template render smoke test
# ---------------------------------------------------------------------------

def test_template_renders_with_minimal_vm():
    """Template renders without error given a minimal view-model."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=True,
    )
    vm = {
        "as_of": "2026-07-18",
        "outcomes_as_of": "2026-07-18",
        "sb_as_of": "2026-07-18",
        "win_rate_pct": None,
        "avg_pct": None,
        "n_outcomes": None,
        "n_running": None,
        "n_stopped": None,
        "n_skipped": 0,
        "horizon_ladder": [],
        "chart_series_h5_json": "[]",
        "chart_series_h10_json": "[]",
        "board_series": [],
        "board_series_accruing": True,
        "outcomes_rows": [],
        "failure_mix_data_gap": True,
        "failure_mix": {},
        "coverage_monitor": {},
        "gate_suppressed": {},
        "buy_lane_rows": 0,
        "all_lanes_rows": 0,
        "survivorship": {},
        "cohort_accruing": True,
        "track_history": {"schema": "us_track_history/v1", "as_of": "2026-07-18"},
    }
    html = env.get_template("us_track_record.html.j2").render(**vm)
    assert "Track Record" in html or "往绩" in html
    assert "us_stocks.html" in html  # back-link present
    assert "validated" not in html.lower()  # CI-guarded word absent


def test_template_renders_with_populated_outcomes():
    """Template renders correctly when outcomes data is present."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=True,
    )
    outcomes_rows = [
        {"ticker": "AAPL", "sector": "Technology", "first_surfaced": "2026-07-01",
         "pct_since": 5.2, "status": "running", "lane": "buy"},
        {"ticker": "BA", "sector": "Industrials", "first_surfaced": "2026-07-06",
         "pct_since": -8.7, "status": "stopped", "lane": "buy"},
    ]
    horizon_ladder = [
        {"horizon": 5, "raw_n": 50, "effective_n": 4, "accruing": False,
         "hit_rate": 0.62, "wilson_lo": 0.48, "wilson_hi": 0.74,
         "mean_excess": 0.011, "median_excess": 0.008},
        {"horizon": 10, "raw_n": 20, "effective_n": 2, "accruing": True,
         "hit_rate": None, "wilson_lo": None, "wilson_hi": None,
         "mean_excess": None, "median_excess": None},
    ]
    vm = {
        "as_of": "2026-07-18",
        "outcomes_as_of": "2026-07-18",
        "sb_as_of": "2026-07-18",
        "win_rate_pct": 68,
        "avg_pct": 2.1,
        "n_outcomes": 2,
        "n_running": 1,
        "n_stopped": 1,
        "n_skipped": 0,
        "horizon_ladder": horizon_ladder,
        "chart_series_h5_json": "[]",
        "chart_series_h10_json": "[]",
        "board_series": [],
        "board_series_accruing": True,
        "outcomes_rows": outcomes_rows,
        "failure_mix_data_gap": True,
        "failure_mix": {},
        "coverage_monitor": {"trailing_4wk_buy_count": 200, "weekly_history": [
            {"week": "2026-06-15/2026-06-21", "unique_tickers": 80},
        ]},
        "gate_suppressed": {},
        "buy_lane_rows": 50,
        "all_lanes_rows": 80,
        "survivorship": {},
        "cohort_accruing": False,
        "track_history": {"schema": "us_track_history/v1", "as_of": "2026-07-18"},
    }
    html = env.get_template("us_track_record.html.j2").render(**vm)
    assert "AAPL" in html
    assert "BA" in html
    assert "68%" in html  # win_rate_pct
    assert "+2.1%" in html  # avg_pct
    assert "62%" in html  # 5d hit rate
    # 10d should show ACCRUING
    assert "ACCRUING" in html or "积累中" in html

    # No unrendered Jinja
    import re
    unrendered = re.findall(r'\{\{[^}]+\}\}|\{%[^%]+%\}', html)
    assert not unrendered, f"Unrendered Jinja: {unrendered[:3]}"


def test_chart_series_json_not_escaped():
    """Chart series JSON must arrive in the baked page with real quotes, not &#34; entities.

    Regression test for autoescape=True stripping: without |safe the Jinja env
    HTML-escapes double-quotes → JS SyntaxError → both weekly win-rate charts silent.
    """
    from jinja2 import Environment, FileSystemLoader

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=True,
    )
    series = [{"week": "2026-06-15/2026-06-21", "win_rate": 0.72, "raw_n": 305}]
    series_json = json.dumps(series)

    vm = {
        "as_of": "2026-07-18",
        "outcomes_as_of": "2026-07-18",
        "sb_as_of": "2026-07-18",
        "win_rate_pct": 72,
        "avg_pct": 2.5,
        "n_outcomes": 305,
        "n_running": 100,
        "n_stopped": 205,
        "n_skipped": 0,
        "horizon_ladder": [],
        "chart_series_h5_json": series_json,
        "chart_series_h10_json": series_json,
        "board_series": [],
        "board_series_accruing": True,
        "outcomes_rows": [],
        "failure_mix_data_gap": True,
        "failure_mix": {},
        "coverage_monitor": {},
        "gate_suppressed": {},
        "buy_lane_rows": 305,
        "all_lanes_rows": 400,
        "survivorship": {},
        "cohort_accruing": False,
        "track_history": {"schema": "us_track_history/v1", "as_of": "2026-07-18"},
    }
    html = env.get_template("us_track_record.html.j2").render(**vm)

    # Escaped quotes must NOT appear inside the script block
    assert "&#34;" not in html, (
        "chart_series JSON is HTML-escaped (&#34;) — add |safe to "
        "chart_series_h5_json and chart_series_h10_json in the template."
    )
    # Real quotes must survive so JS can parse the literal
    assert 'var seriesH5 = [{"week"' in html, (
        "seriesH5 literal not found with real double-quotes — |safe may be missing."
    )
    assert 'var seriesH10 = [{"week"' in html, (
        "seriesH10 literal not found with real double-quotes — |safe may be missing."
    )


def test_no_validated_word_in_template():
    """The word 'validated' must not appear anywhere in the template (CI-guarded)."""
    tmpl = (ROOT / "templates" / "us_track_record.html.j2").read_text()
    # Allow in Jinja comment blocks that explain the rule itself
    import re
    # Strip comments
    stripped = re.sub(r'\{#.*?#\}', '', tmpl, flags=re.DOTALL)
    assert "validated" not in stripped.lower(), \
        "Template must not contain 'validated' (CI-guarded)"


# ---------------------------------------------------------------------------
# W20-L4 — Track Record display truthfulness (buy-lane ladder, clock, board
# size span, exits detail, failure-mix wording, GRADED chip).
# ---------------------------------------------------------------------------

def _w20l4_vm(**over):
    """View-model shaped like test_chart_series_json_not_escaped's vm (:337-362)."""
    vm = {
        "as_of": "2026-10-19", "outcomes_as_of": "2026-10-19",
        "sb_as_of": "2026-10-19", "win_rate_pct": 72, "avg_pct": 2.5,
        "n_outcomes": 305, "n_running": 100, "n_stopped": 205, "n_skipped": 0,
        "horizon_ladder": [], "chart_series_h5_json": "[]",
        "chart_series_h10_json": "[]", "board_series": [],
        "board_series_accruing": True, "outcomes_rows": [],
        "failure_mix_data_gap": True, "failure_mix": {}, "coverage_monitor": {},
        "gate_suppressed": {}, "buy_lane_rows": 305, "all_lanes_rows": 400,
        "survivorship": {}, "cohort_accruing": False,
        "track_history": {"schema": "us_track_history/v1", "as_of": "2026-10-19"},
        "clock_h21": None, "board_buy_span": None,
        "n_flat": None, "n_total_exits": None,
    }
    vm.update(over)
    return vm


def _w20l4_render(**over):
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    return env.get_template("us_track_record.html.j2").render(**_w20l4_vm(**over))


def _w20l4_build(monkeypatch, tmp_path, track=None, snapshots=None,
                 outcomes=None):
    """build() with every input path pointed under tmp_path; optional fixtures."""
    import scripts.build_track_record_page as builder

    for name in ("RETRO_GRADES", "SNAPSHOTS_JSONL", "US_BOARD_TRACK",
                 "US_BOARD_OUTCOMES", "US_AUDIT_SCOREBOARD", "US_ATTRIBUTION",
                 "US_TRACK_LEDGER"):
        monkeypatch.setattr(builder, name, tmp_path / (name.lower() + ".missing"))
    monkeypatch.setattr(builder, "OUT_JSON", tmp_path / "us_track_history.json")
    monkeypatch.setattr(builder, "OUT_HTML", tmp_path / "us_track_record.html")
    if track is not None:
        p = tmp_path / "us_board_track.json"
        p.write_text(json.dumps(track))
        monkeypatch.setattr(builder, "US_BOARD_TRACK", p)
    if snapshots is not None:
        p = tmp_path / "snapshots.jsonl"
        p.write_text("".join(json.dumps(r) + "\n" for r in snapshots))
        monkeypatch.setattr(builder, "SNAPSHOTS_JSONL", p)
    if outcomes is not None:
        p = tmp_path / "us_board_outcomes.json"
        p.write_text(json.dumps(outcomes))
        monkeypatch.setattr(builder, "US_BOARD_OUTCOMES", p)
    assert builder.build() == 0
    return builder.OUT_HTML.read_text()


def test_w20l4_item1_ladder_reads_buy_lane(monkeypatch, tmp_path):
    """TR-1: the h5 ladder shows buy-lane numbers, not every board lane."""
    track = {"per_horizon": {"h5": {
        "overall_vs_spy": {"n": 2838, "hit_rate": 0.3689, "wilson_lo": 0.3516,
                           "wilson_hi": 0.3865, "mean_excess": -0.011,
                           "median_excess": -0.007},
        "buy_lane": {"vs_spy": {"n": 1098, "hit_rate": 0.3424, "wilson_lo": 0.315,
                                "wilson_hi": 0.371, "mean_excess": -0.01077,
                                "median_excess": -0.006}},
    }}}
    html = _w20l4_build(monkeypatch, tmp_path, track=track)
    assert "34%" in html                      # buy hit rate 0.3424 -> 34%
    assert "1098 /" in html                   # observations = buy-lane raw_n
    assert "32–37%" in html                   # buy wilson range
    assert "36.9%" not in html                # overall 0.3689 tooltip absent
    import re
    assert re.search(r">\s*37%\s*</td>", html) is None  # overall 37% cell gone
    assert "All board lanes together" in html
    assert "2838" in html                     # footnote carries the all-lanes n


def test_w20l4_item1_fallback_all_lanes(monkeypatch, tmp_path):
    """TR-1 fallback: no buy_lane data -> ladder keeps the all-board view."""
    track = {"per_horizon": {"h5": {
        "overall_vs_spy": {"n": 2838, "hit_rate": 0.3689, "wilson_lo": 0.3516,
                           "wilson_hi": 0.3865, "mean_excess": -0.011},
    }}}
    html = _w20l4_build(monkeypatch, tmp_path, track=track)
    assert "36.9%" in html
    assert "2838 /" in html
    assert "All board lanes together" not in html


def test_w20l4_item1_empty_cell_still_accruing(monkeypatch, tmp_path):
    """TR-1: h63 with both blocks empty stays on the ACCRUING chip."""
    track = {"per_horizon": {"h63": {}}}
    html = _w20l4_build(monkeypatch, tmp_path, track=track)
    assert "ACCRUING" in html
    assert "GRADED" not in html


def test_w20l4_item2_clock_data_driven():
    """TR-2: the clock sentence reflects raw/effective n; no stale dates."""
    html = _w20l4_render(clock_h21={"raw_n": 3163, "effective_n": 2})
    assert ("21-day grades so far come from only 2 independent entry windows;"
            " a trend needs at least 3.") in html
    assert "21日成绩目前仅来自2个独立入场窗口" in html
    assert "3163" not in html and "3,163" not in html  # raw rows mix lanes/rank_by
    html2 = _w20l4_render(clock_h21={"raw_n": 120, "effective_n": 4})
    assert "21-day grades come from 4 independent entry windows." in html2
    html3 = _w20l4_render(clock_h21={"raw_n": 0, "effective_n": 0})
    assert "21-day grades are still accruing." in html3
    tmpl = (ROOT / "templates" / "us_track_record.html.j2").read_text()
    for stale in ("mid-August", "September 2026", "2026年8月", "2026年9月"):
        assert stale not in tmpl, f"stale date string still present: {stale}"


def test_w20l4_item3_board_series_lane_lists(tmp_path):
    """TR-3: lane-list rows count by lane; legacy board rows still count."""
    from scripts.build_track_record_page import _compute_board_series

    p = tmp_path / "snapshots.jsonl"
    rows = [
        {"as_of": "2026-10-14", "buy": ["A", "B", "C"], "watch": ["D"]},
        {"as_of": "2026-06-30", "buy": ["E"], "laggards": ["F", "G"]},
        {"as_of": "2026-08-01", "board": [{"lane": "buy"}, {"lane": "watch"},
                                          {"lane": "watch"}]},
    ]
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    series = _compute_board_series(p)["series"]
    assert [r["as_of"] for r in series] == [
        "2026-06-30", "2026-08-01", "2026-10-14"]
    assert series[0]["total"] == 3
    assert series[0]["by_lane"] == {"buy": 1, "laggards": 2}
    assert series[2]["total"] == 4
    assert series[2]["by_lane"] == {"buy": 3, "watch": 1}
    assert series[1]["total"] == 3        # legacy dict rows unchanged
    assert series[1]["by_lane"] == {"buy": 1, "watch": 2}


def test_w20l4_item3_buy_span_rendered(monkeypatch, tmp_path):
    snaps = [
        {"as_of": "2026-10-14", "buy": ["A", "B", "C"], "watch": ["D"]},
        {"as_of": "2026-06-30", "buy": ["E"], "laggards": ["F", "G"]},
    ]
    html = _w20l4_build(monkeypatch, tmp_path, snapshots=snaps)
    assert "Buy board size" in html
    assert "1 names on 2026-06-30 → 3 on 2026-10-14" in html
    assert "2 board snapshots" in html
    assert "买入榜规模：2026-06-30 1个 → 2026-10-14 3个，共2次榜单快照。" in html


def test_w20l4_item3_one_row_no_span(monkeypatch, tmp_path):
    snaps = [{"as_of": "2026-06-30", "buy": ["E"]}]
    html = _w20l4_build(monkeypatch, tmp_path, snapshots=snaps)
    assert "Buy board size" not in html


def test_w20l4_item4_exits_detail():
    rows = [
        {"ticker": "RKLB", "sector": "Technology", "first_surfaced": "2026-09-20",
         "pct_since": 14.5, "status": "running", "days_on_board": 5,
         "exit_date": "2026-09-25"},
        {"ticker": "XYZ", "sector": "Industrials", "first_surfaced": "2026-07-06",
         "pct_since": -1.0, "status": "flat"},
    ]
    html = _w20l4_render(outcomes_rows=rows, n_total_exits=389, n_running=33,
                         n_stopped=64, n_flat=292)
    assert "Showing 2 of 389" in html
    assert "33 above +2%" in html
    assert "64 below −2%" in html
    assert "292 within ±2%" in html
    assert "Days on board" in html
    assert "Left board" in html
    assert "2026-09-25" in html
    assert "高于+2%" in html              # RKLB running label (ZH)
    assert "return from entry to the close on the day they left." in html
    import re
    assert re.search(r">5</td>\s*<td[^>]*>2026-09-25</td>", html)
    assert re.search(r">—</td>\s*<td[^>]*>—</td>", html)  # XYZ missing fields
    assert html.count("above +2%") == 2   # summary + running row, not swapped
    assert html.count("below −2%") == 1   # summary only
    assert html.count("within ±2%") == 2  # summary + flat row label


def test_w20l4_item4_old_showing_text_without_totals():
    rows = [{"ticker": "AAA", "sector": "s", "first_surfaced": "2026-07-01",
             "pct_since": 1.0, "status": "running"},
            {"ticker": "BBB", "sector": "t", "first_surfaced": "2026-07-02",
             "pct_since": -1.0, "status": "stopped"}]
    html = _w20l4_render(outcomes_rows=rows, n_total_exits=389)  # n_flat None
    assert "Showing" in html
    assert "names." in html
    assert "389" not in html


def test_w20l4_item5_failure_mix_wording():
    fm = {"outcome_cause": {"idio_break": 24, "unknown_x": 1},
          "process_fault": {"clean": 61}}
    html = _w20l4_render(failure_mix=fm, failure_mix_data_gap=False)
    assert "What drove each exit" in html
    assert "每次离榜的驱动因素" in html
    assert "What drove the result" in html
    assert "结果的驱动因素" in html
    assert "Process check" in html
    assert "Company-specific weakness" in html
    assert "No process fault" in html
    assert "unknown_x" in html
    assert ">24</span>" in html
    assert ">61</span>" in html
    assert "Why names stopped out" not in html
    assert "Attribution of stopped-out names" not in html
    assert "个股自身走强" not in html   # m15 guard: idio_alpha label must not show


def test_w20l4_item6_graded_chip():
    ladder = [{"horizon": 5, "raw_n": 50, "effective_n": 4, "accruing": False,
               "hit_rate": 0.62, "wilson_lo": 0.48, "wilson_hi": 0.74,
               "mean_excess": 0.011, "median_excess": 0.008}]
    html = _w20l4_render(horizon_ladder=ladder)
    assert "GRADED" in html
    assert "已出结果" in html
    tmpl = (ROOT / "templates" / "us_track_record.html.j2").read_text()
    assert "\u5b9e\u65f6" not in tmpl
    assert ">LIVE<" not in tmpl


def test_w20l4_j_escaping_stays_on():
    rows = [{"ticker": "<b>X</b>", "sector": "s", "first_surfaced": "2026-07-01",
             "pct_since": 1.0, "status": "running", "days_on_board": 3,
             "exit_date": "<i>Y</i>"}]
    fm = {"outcome_cause": {"<u>Z</u>": 2}}
    html = _w20l4_render(outcomes_rows=rows, n_total_exits=5, n_running=1,
                         n_stopped=1, n_flat=3, failure_mix=fm,
                         failure_mix_data_gap=False)
    assert "&lt;b&gt;X&lt;/b&gt;" in html
    assert "&lt;i&gt;Y&lt;/i&gt;" in html
    assert "&lt;u&gt;Z&lt;/u&gt;" in html
    assert "<b>X</b>" not in html


def test_w20l4_item4_build_reads_summary_counts(monkeypatch, tmp_path):
    """TR-4: the Showing line uses outcomes summary n_total, not n_shown."""
    outcomes = {
        "as_of": "2026-10-14",
        "summary": {"n_running": 33, "n_stopped": 64, "n_flat": 292,
                    "n_total": 389, "n_shown": 60},
        "rows": [{"ticker": "RKLB", "sector": "Space",
                  "first_surfaced": "2026-09-20", "pct_since": 14.5,
                  "status": "running", "days_on_board": 5,
                  "exit_date": "2026-09-25"}],
    }
    html = _w20l4_build(monkeypatch, tmp_path, outcomes=outcomes)
    assert "Showing 1 of 389" in html
    assert "Showing 1 of 60" not in html


def test_w20l4_seat_footnote_all_lanes_numbers(monkeypatch, tmp_path):
    """TR-1 footnote prints the all-lanes hit rate and n, not the buy lane's."""
    track = {"per_horizon": {"h5": {
        "overall_vs_spy": {"n": 2838, "hit_rate": 0.3689, "wilson_lo": 0.3516,
                           "wilson_hi": 0.3865, "mean_excess": -0.011},
        "buy_lane": {"vs_spy": {"n": 1098, "hit_rate": 0.3424, "wilson_lo": 0.315,
                                "wilson_hi": 0.371, "mean_excess": -0.01077}},
    }}}
    html = _w20l4_build(monkeypatch, tmp_path, track=track)
    import re
    assert re.search(r"\s37% <span class=\"l-en\">of</span>"
                     r"<span class=\"l-zh\">／</span> 2838\s", html)


def test_w20l4_seat_span_needs_buy_at_both_ends(monkeypatch, tmp_path):
    """TR-3: no buy-size span when the first snapshot has no buy lane."""
    snaps = [
        {"as_of": "2026-06-30", "watch": ["E"]},
        {"as_of": "2026-10-14", "buy": ["A", "B", "C"]},
    ]
    html = _w20l4_build(monkeypatch, tmp_path, snapshots=snaps)
    assert "Buy board size" not in html


def test_w20l4_seat_build_flat_count(monkeypatch, tmp_path):
    """TR-4: build() passes the summary's n_flat through to the exits line."""
    outcomes = {
        "as_of": "2026-10-14",
        "summary": {"n_running": 33, "n_stopped": 64, "n_flat": 292,
                    "n_total": 389, "n_shown": 60},
        "rows": [{"ticker": "RKLB", "sector": "Space",
                  "first_surfaced": "2026-09-20", "pct_since": 14.5,
                  "status": "running"}],
    }
    html = _w20l4_build(monkeypatch, tmp_path, outcomes=outcomes)
    assert "292 within ±2%" in html
    assert "33 within ±2%" not in html


def test_w20l4_seat_unknown_status_has_no_label():
    """TR-4: a row with an unrecognised status gets no outcome label."""
    rows = [{"ticker": "QQQ", "sector": "s", "first_surfaced": "2026-07-01",
             "pct_since": 0.5, "status": "weird"}]
    html = _w20l4_render(outcomes_rows=rows)
    assert "within ±2%" not in html
    assert "±2%以内" not in html
