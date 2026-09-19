"""Unit tests for engine.subsector_rotation — the rotation/velocity math."""
from __future__ import annotations

from engine import subsector_rotation as sr


def _tree():
    # ≥3 members each so they clear the emerging/fading breadth floor (MIN_BREADTH=3).
    return [
        {"theme": "Alpha", "subsectors": [
            {"key": "a1", "name": "A-One", "members": ["AA", "AB", "AD"]},
            {"key": "a2", "name": "A-Two", "members": ["AC", "AE", "AF"]},
        ]},
        {"theme": "Beta", "subsectors": [
            {"key": "b1", "name": "B-One", "members": ["BA", "BC", "BD"]},
            {"key": "b2", "name": "B-Two", "members": ["BB", "BE", "BF"]},
        ]},
    ]


def _perf():
    # a1: hot & accelerating (1W pace >> 3M pace), strong recent RS.
    # b2: established leader rolling over (big 3M/6M, weak 1W) -> weakening.
    # b1: laggard turning up -> improving. a2: flat laggard.
    return {
        "a1": {"1D": 1.0, "1W": 9.0, "1M": 10.0, "3M": 12.0, "6M": 14.0, "1Y": 20.0, "MTD": 5, "YTD": 18},
        "a2": {"1D": -0.2, "1W": -1.0, "1M": -2.0, "3M": -3.0, "6M": -4.0, "1Y": -5.0, "MTD": -1, "YTD": -4},
        "b1": {"1D": 0.5, "1W": 4.0, "1M": 1.0, "3M": -8.0, "6M": -12.0, "1Y": -10.0, "MTD": 2, "YTD": -9},
        "b2": {"1D": -0.5, "1W": -2.0, "1M": 3.0, "3M": 30.0, "6M": 50.0, "1Y": 60.0, "MTD": -1, "YTD": 55},
    }


def test_structure_and_coverage():
    out = sr.compute_rotation(_tree(), _perf(), {"AA": {"1W": 9, "1M": 11}})
    assert out["n_subsectors"] == 4 and out["n_themes"] == 2
    assert {s["key"] for s in out["subsectors"]} == {"a1", "a2", "b1", "b2"}
    # ranked by emerging_score desc; rank field consistent.
    scores = [s["emerging_score"] for s in out["subsectors"]]
    assert scores == sorted(scores, reverse=True)
    assert out["subsectors"][0]["rank"] == 1
    for s in out["subsectors"]:
        assert s["quadrant"] in ("leading", "weakening", "improving", "lagging")
        assert set(s["perf"]) == set(sr.HORIZONS)


def test_quadrant_logic():
    out = {s["key"]: s for s in sr.compute_rotation(_tree(), _perf())["subsectors"]}
    # a1 leads and is improving -> leading.
    assert out["a1"]["quadrant"] == "leading"
    assert out["a1"]["rs_ratio"] > 0 and out["a1"]["rs_mom"] > 0
    # b2 is a strong leader by level but momentum rolling over -> weakening.
    assert out["b2"]["rs_ratio"] > 0 and out["b2"]["rs_mom"] < 0
    assert out["b2"]["quadrant"] == "weakening"
    # b1 is a laggard turning up -> improving (negative level, positive momentum).
    assert out["b1"]["rs_ratio"] < 0 and out["b1"]["rs_mom"] > 0
    assert out["b1"]["quadrant"] == "improving"


def test_acceleration_and_highlights():
    out = sr.compute_rotation(_tree(), _perf())
    m = {s["key"]: s for s in out["subsectors"]}
    # a1: weekly pace (9) far exceeds 3M weekly pace (12/13≈0.9) -> strong +accel.
    assert m["a1"]["accel"] is not None and m["a1"]["accel"] > 0
    # b2: 1W negative, 3M huge -> decelerating.
    assert m["b2"]["accel"] < 0
    # highlights: a1 emerging; b2 fading; b2 a leader; a2 a laggard.
    assert "a1" in out["highlights"]["emerging"]
    assert "b2" in out["highlights"]["fading"]
    assert "b2" in out["highlights"]["leaders"]
    assert "a2" in out["highlights"]["laggards"]


def test_missing_horizons_are_safe():
    tree = [{"theme": "X", "subsectors": [
        {"key": "x1", "name": "X1", "members": []},
        {"key": "x2", "name": "X2", "members": []},
    ]}]
    perf = {"x1": {"1W": 3.0}, "x2": {"3M": 5.0}}  # disjoint horizons
    out = sr.compute_rotation(tree, perf)
    assert out["n_subsectors"] == 2
    for s in out["subsectors"]:
        assert s["quadrant"] in ("leading", "weakening", "improving", "lagging")


def test_breadth_floor_excludes_thin_subsectors():
    # a 2-member subsector that is momentum-hot must NOT reach the emerging call
    # (it's a stock or two, not a rotation) — while an identical 3-member one does.
    tree = [{"theme": "T", "subsectors": [
        {"key": "thin", "name": "Thin", "members": ["TA", "TB"]},
        {"key": "broad", "name": "Broad", "members": ["BA", "BB", "BC"]},
        {"key": "c1", "name": "C1", "members": ["CA", "CB", "CC"]},
        {"key": "c2", "name": "C2", "members": ["DA", "DB", "DC"]},
    ]}]
    # improving = weak over long windows, strong recently (relative rank RISES short-term).
    improving = {"1W": 15.0, "1M": 8.0, "3M": -5.0, "6M": -10.0, "1Y": -8.0}
    fading = {"1W": -8.0, "1M": -5.0, "3M": 10.0, "6M": 15.0, "1Y": 12.0}
    perf = {"thin": dict(improving), "broad": dict(improving),
            "c1": dict(fading), "c2": dict(fading)}
    em = sr.compute_rotation(tree, perf)["highlights"]["emerging"]
    assert "broad" in em and "thin" not in em


# ── Rotation Command RC-R4: synthetic-node perf feed ─────────────────────────

def test_perf_from_close_horizons():
    import pandas as pd
    idx = pd.bdate_range("2024-01-02", periods=400)
    s = pd.Series([100.0 * (1.001 ** k) for k in range(400)], index=idx)
    out = sr.perf_from_close(s)
    assert out is not None
    assert set(out) == {"1D", "1W", "1M", "MTD", "3M", "6M", "1Y", "YTD"}
    assert abs(out["1D"] - 0.1) < 0.02          # +0.1%/session drift
    assert abs(out["1W"] - 0.5) < 0.1
    assert out["1Y"] > 20.0                     # ≈ +28.5% over 252 sessions
    assert out["YTD"] is not None and out["MTD"] is not None


def test_perf_from_close_thin_series_none():
    import pandas as pd
    idx = pd.bdate_range("2026-01-02", periods=100)
    assert sr.perf_from_close(pd.Series(100.0, index=idx)) is None


# ── turn read wiring (engine.subsector_turn) ───────────────────────────────────
def test_turn_read_is_attached_and_incumbent_fields_untouched():
    """The turn read is ADDITIVE: every incumbent field must be byte-identical."""
    before = sr.compute_rotation(_tree(), _perf())
    after = sr.compute_rotation(_tree(), _perf(), history=[
        {"asof": "2026-07-2%d" % d, "subsectors": _perf()} for d in range(1, 8)])
    keep = ("rs_ratio", "rs_mom", "accel", "z_accel", "quadrant", "emerging_score",
            "rank", "perf", "rs")
    b = {s["key"]: s for s in before["subsectors"]}
    for s in after["subsectors"]:
        for f in keep:
            assert s[f] == b[s["key"]][f], f"incumbent field {f} changed on {s['key']}"
    assert before["highlights"] == after["highlights"]
    # and the turn block landed
    assert after["turn"]["counts"] and "turn_state" in after["subsectors"][0]
    assert after["turn_themes"]["counts"]


def test_turn_read_survives_a_missing_archive():
    out = sr.compute_rotation(_tree(), _perf(), history=None)
    assert out["turn"].get("counts")            # runs on today alone
    row = out["subsectors"][0]
    assert row["vol_cold"] is True              # ...and cannot confirm
    assert row["turn_state"] not in ("turn_up", "turn_down")


def test_live_snapshot_wins_over_a_same_day_archive_row():
    """The archive appends once per asof, so an intraday re-fetch leaves it stale.

    If the archive won, the turn read would run on a different vintage than the incumbent
    metrics sitting in the same payload.
    """
    stale = {"a1": {"1W": -99.0, "1M": -99.0}}
    fresh = {"a1": {"1W": 9.0, "1M": 10.0}}
    rows = sr._history_with_today([{"asof": "2026-07-30", "subsectors": stale}],
                                  fresh, "2026-07-30")
    assert len(rows) == 1
    assert rows[0]["subsectors"]["a1"]["1W"] == 9.0


def test_history_with_today_appends_a_missing_session_and_folds_synthetics():
    rows = sr._history_with_today([{"asof": "2026-07-29", "subsectors": {"a1": {"1W": 1.0}}}],
                                  {"a1": {"1W": 2.0}, "synthetic": {"1W": 3.0}}, "2026-07-30")
    assert [r["asof"] for r in rows] == ["2026-07-29", "2026-07-30"]
    assert "synthetic" in rows[-1]["subsectors"]


# China keeps monthly member selection but must not discard current weekly evidence.
def _china_rotation_inputs():
    from engine import subsector_rotation_china as cn
    members = [{"symbol": f"60000{i}.SS", "name": f"Member {i}",
                "ret_20d": 0.30 - i * 0.01, "ret_5d": (2 - i) * 0.01,
                "price_asof": "2026-09-07", "ret_5d_asof": "2026-09-07"}
               for i in range(10)]
    basket = {"id": "concept", "name": "Concept", "name_zh": "概念",
              "category": "Technology", "category_zh": "科技",
              "n_members": 10, "members": members,
              "perf": {h: {"ret": 0.05} for h in ("1d", "5d", "20d", "60d", "mtd", "ytd")}}
    source = {"as_of": "2026-09-07", "baskets": [basket], "chart": {"baskets": {}}}
    return cn, source, {"as_of": "2026-09-07", "baskets": [], "chart": {"baskets": {}}}


def test_china_weekly_member_returns_reach_the_existing_feed():
    cn, source, curated = _china_rotation_inputs()
    out = cn.compute_china_rotation(source, curated)
    members = out["subsectors"][0]["members"]
    assert len(members) == 8 and out["subsectors"][0]["n_members"] == 10
    assert [m["t"] for m in members] == [f"60000{i}.SS" for i in range(8)]
    assert [m["1W"] for m in members[:4]] == [2.0, 1.0, 0.0, -1.0]
    assert all(m["price_asof"] == "2026-09-07" for m in members)
    assert all(m["1W_asof"] == "2026-09-07" for m in members)


def test_china_weekly_requires_matching_observation_evidence():
    import copy
    cn, source, curated = _china_rotation_inputs()
    defects = [{"ret_5d_asof": None}, {"price_asof": None},
               {"ret_5d_asof": "2026-09-04"}, {"price_asof": "2026-09-04"},
               {"price_asof": "2026-09-08"}, {"ret_5d_asof": "invalid"},
               {"ret_5d": None}, {"ret_5d": True}, {"ret_5d": "0.1"},
               {"ret_5d": float("nan")}, {"ret_5d": float("inf")}]
    for defect in defects:
        data = copy.deepcopy(source)
        data["baskets"][0]["members"][0].update(defect)
        member = cn.compute_china_rotation(data, curated)["subsectors"][0]["members"][0]
        assert member["1W"] is None, defect
        assert member["1W_asof"] is None, defect
        assert member["1M"] == 30.0
    legacy = copy.deepcopy(source)
    for member in legacy["baskets"][0]["members"]:
        member.pop("price_asof")
        member.pop("ret_5d_asof")
    assert all(m["1W"] is None for m in
               cn.compute_china_rotation(legacy, curated)["subsectors"][0]["members"])


def test_china_weekly_does_not_reorder_groups_or_monthly_member_sample():
    import copy
    cn, source, curated = _china_rotation_inputs()
    before = cn.compute_china_rotation(source, curated)
    saved = copy.deepcopy(source)
    changed = copy.deepcopy(source)
    for member in changed["baskets"][0]["members"]:
        member["ret_5d"] = -0.9
    after = cn.compute_china_rotation(changed, curated)
    for payload in [before, after]:
        for sub in payload["subsectors"]:
            for member in sub["members"]:
                member.pop("1W")
                member.pop("1W_asof")
    assert before == after
    assert source == saved


def test_china_detail_builder_renders_weekly_and_missing_dates(tmp_path):
    import json
    from scripts import build_subsector_rotation_china_pages as pages
    cn, source, curated = _china_rotation_inputs()
    source["baskets"][0]["members"][1]["price_asof"] = "2026-09-04"
    source["baskets"][0]["members"][2]["price_asof"] = None
    payload = cn.compute_china_rotation(source, curated)
    path = tmp_path / "marketdata" / "subsector_rotation_china.json"
    path.parent.mkdir()
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert pages.build(site=tmp_path) == 1
    html = (tmp_path / "rotation_china" / "concept.html").read_text()
    assert "1W" in html and "1周" in html and "1M" in html
    assert "2026-09-07" in html and "2026-09-04" in html
    assert "Date unavailable" in html and "日期缺失" in html
    # The shared bilingual macro wraps each language in separate spans. Test
    # rendered text rather than requiring its markup to contain one raw phrase.
    import re
    meta = html.split('<div class="sd-member-meta">', 1)[1].split("</div>", 1)[0]
    def visible(language):
        hidden = "zh" if language == "en" else "en"
        markup = re.sub(r'<span class="l-' + hidden + r'">.*?</span>', "", meta, flags=re.S)
        return " ".join(re.sub(r"<[^>]+>", "", markup).split())
    assert "8 of 10 shown" in visible("en")
    assert "8 / 10只" in visible("zh")
    assert "china_lookup.html#600000.SS" in html
    assert "by 1-month return" in html


def test_shared_detail_default_does_not_opt_other_regions_into_weekly_view():
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from scripts.build_subsector_rotation_pages import _fmt_pc
    cn, source, curated = _china_rotation_inputs()
    sub = cn.compute_china_rotation(source, curated)["subsectors"][0]
    env = Environment(loader=FileSystemLoader(str(Path(cn.__file__).parents[1] / "templates")),
                      autoescape=True)
    env.globals["fmt_pc"] = _fmt_pc
    html = env.get_template("subsector_rotation_detail.html.j2").render(
        sub=sub, members=sub["members"], n_total=1, perf_rows=[],
        q_cls="q-lead", q_en="Leading", q_zh="领先", qx_en="", qx_zh="",
        lede_en="Context", lede_zh="背景")
    assert "sd-weekly" not in html
    assert "<i>1W</i>" not in html and "8 of 10 shown" not in html
    assert "stock.html#600000.SS" in html


def test_real_prices_flow_through_baskets_rotation_and_detail_page(tmp_path):
    """One uninterrupted real path, including good, zero, negative and missing data."""
    import json
    import re
    import numpy as np
    import pandas as pd
    from engine import baskets_region as producer
    from engine import subsector_rotation_china as rotation
    from scripts import build_subsector_rotation_china_pages as pages
    idx = pd.bdate_range(end="2026-09-07", periods=40)
    tickers = [f"60000{i}.SS" for i in range(8)]
    closes = pd.DataFrame({t: np.linspace(85, 105, len(idx)) for t in tickers}, index=idx)
    closes.iloc[-6:, 0] = [100, 101, 102, 103, 104, 105]
    closes.iloc[-6:, 1] = [100, 100, 100, 100, 100, 100]
    closes.iloc[-6:, 2] = [100, 99, 98, 97, 96, 95]
    closes.iloc[-1, 3] = np.nan
    closes.iloc[-3, 4] = np.nan
    mem = {"baskets": {"concept": {"name": "Test concept", "category": "Technology",
           "members": [{"ticker": t, "name": "Member " + t, "added": str(idx[0].date())}
                       for t in tickers]}}}
    basket = producer.compute_region_baskets(
        closes, mem, closes[tickers[-1]].to_frame("close"), lambda _: None)
    payload = rotation.compute_china_rotation(basket, {"baskets": [], "chart": {}})
    members = {m["t"]: m for m in payload["subsectors"][0]["members"]}
    assert [members[t]["1W"] for t in tickers[:3]] == [5.0, 0.0, -5.0]
    assert members[tickers[3]]["1W"] is None
    assert members[tickers[4]]["1W"] is None
    src = tmp_path / "marketdata/subsector_rotation_china.json"
    src.parent.mkdir()
    src.write_text(json.dumps(payload), encoding="utf-8")
    assert pages.build(site=tmp_path) == 1
    html = (tmp_path / "rotation_china/concept.html").read_text()
    for ticker in tickers:
        match = re.search(r'<a class="sd-chip"[^>]*#' + re.escape(ticker) + r'">(.*?)</a>',
                          html, flags=re.S)
        assert match, ticker
        card = match.group(1)
        assert pages._fmt_pc(members[ticker]["1W"]) in card
        assert "1W" in card and "1周" in card
    assert str(idx[-2].date()) in html  # stale close is not re-dated to the snapshot
    assert "Weekly coverage incomplete" in html
    assert "周度数据不完整" in html


def test_member_pipeline_guards_run_in_the_existing_code_gate():
    """A green data-only scope check must not leave the new regressions unexecuted."""
    from pathlib import Path
    import shlex
    import yaml

    manifest = yaml.safe_load((Path(__file__).parents[1] /
                               ".github/ci/legacy-jobs.yml").read_text())
    job = manifest["jobs"]["rc-r14-china-rotation-events"]
    assert job["gate"] == "code"
    assert not job.get("continue-on-error", False)
    suites = {"tests/test_baskets_region.py", "tests/test_subsector_rotation.py"}
    matching = []
    for step in job["steps"]:
        args = shlex.split(step.get("run", ""))
        if args[:3] == ["python", "-m", "pytest"] and suites <= set(args[3:]):
            assert "if" not in step and not step.get("continue-on-error", False)
            assert not any(a == "-k" or a.startswith("--deselect") for a in args)
            matching.append(step)
    assert len(matching) == 1, "member producer/consumer suites are absent from the code gate"
