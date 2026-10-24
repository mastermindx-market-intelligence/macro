"""Smoke + unit tests for scripts/build_demand.py (the Demand Desk page)."""
from __future__ import annotations

from scripts import build_demand as bd


def test_chain_cards_capex_and_rpo():
    signals = {"ai_datacenter": {"trend": "accelerating", "yoy_pct": 69.0,
                                 "total_latest_bn": 379.0, "fy_latest": 2025,
                                 "n_spenders": 5, "series": [[2024, 224.1], [2025, 379.0]],
                                 "chain_key": "ai_datacenter"}}
    reads = {"NVDA": {"chain_key": "ai_datacenter", "tier": "compute", "leading": True,
                      "fy_latest": 2025, "yoy_pct": 69.0},
             "ORCL": {"chain_key": "own_rpo", "tier": "bookings", "leading": True,
                      "fy_latest": 2025, "yoy_pct": 41.0, "total_latest_bn": 138.0}}
    cards = bd._chain_cards(signals, reads)
    keys = {c["key"] for c in cards}
    assert "ai_datacenter" in keys and "own_rpo" in keys
    rpo_card = next(c for c in cards if c["key"] == "own_rpo")
    assert rpo_card["n"] == 1 and rpo_card["leaders"][0]["t"] == "ORCL"


def test_div_order_complete():
    # every divergence the engine can emit must have a render slot
    assert set(bd._DIV_ORDER) == set(bd._DIV_META)


def test_build_smoke_renders_page(tmp_path, monkeypatch):
    # integration: build against committed repo data; must emit the page skeleton.
    # Redirect the page write to tmp — never the repo's real site/ tree.
    monkeypatch.setattr(
        bd, "write_page", lambda path, html: (tmp_path / path.name).write_text(html)
    )
    # ...and the Alert Center write, for the same reason. `bd.build()` calls
    # `engine.demand_alerts.rebuild`, which appends to data/demand_chain/alerts.jsonl and
    # rewrites alerts_state.json in the REAL tree — it takes no root/out parameter, so
    # unlike write_page it cannot be pointed elsewhere. MM_DATA_GUARD forced
    # `unrun-builders-stores` to exit 1 on a step reporting "906 passed".
    #
    # It reds INTERMITTENTLY, which is what made it hard to place: rebuild() diffs today's
    # reads against the committed state and only writes when a variant flips, so the job is
    # green on every run where the recomputed state happens to match what is checked in.
    # The observed flip was one ticker (GEV -> DHR in alerts_state.json, one appended
    # alerts.jsonl row). An intermittent tree-dirty is still a hard red, not a flake.
    #
    # Neutralised rather than redirected: this test asserts the PAGE skeleton, and the
    # alert center has its own suite (tests/test_demand_alerts.py). Returning [] matches
    # rebuild's own documented seed-run result, so `build()` takes the same branch it does
    # on a first run.
    from engine import demand_alerts
    monkeypatch.setattr(demand_alerts, "rebuild", lambda reads, as_of=None: [])

    html = bd.build()
    assert "Demand Desk" in html
    assert 'class="cards"' in html and "Ahead of consensus" in html
    assert "demand.html" in html                # nav link present (self-referential)


# ---- W18-C-C2 — variant rows print the RPO headline the producer passes ----
#
# scripts/build_demand.py:145 already puts headline_en / headline_zh on every
# variant row; at the seed templates/demand.html.j2 never rendered them, so the
# XYL +111% row read like a large book while its RPO covers only 0.2x revenue.


def _w18c2_xyl_row():
    # Fixture from the PRODUCER, not a hand-typed headline: the committed XYL
    # FY2024/FY2025 RPO rows through engine.demand_chain.rpo_read, shaped into
    # a variant row exactly like scripts/build_demand.py:141-146 builds them.
    from engine import demand_chain as dc
    r = dc.rpo_read([{"fy": 2024, "rpo": 0.914e9, "revenue": 8.56e9},
                     {"fy": 2025, "rpo": 1.929e9, "revenue": 9.035e9}], None)
    tw = bd._TREND.get(r["trend"], bd._TREND["unknown"])
    row = {"ticker": "XYL", "chain": r["chain_key"], "tier": r["tier"],
           "leading": r["leading"], "trend": r["trend"],
           "trend_en": tw[0], "trend_zh": tw[1], "yoy_pct": r.get("yoy_pct"),
           "consensus_dir": r["consensus_dir"],
           "headline_en": r["headline"]["en"], "headline_zh": r["headline"]["zh"]}
    return row, r


def _w18c2_render(groups):
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from engine.i18n import td, tr
    root = Path(__file__).resolve().parents[1]
    env = Environment(loader=FileSystemLoader(str(root / "templates")),
                      autoescape=True)
    env.globals.update(tr=tr, td=td)
    return env.get_template("demand.html.j2").render(
        cards=[], groups=groups, div_order=bd._DIV_ORDER, div_meta=bd._DIV_META,
        track=None, phase0=None, n_variants=0, as_of="2026-10-16",
        built="2026-10-16 00:00", spender_burden={})


def _w18c2_name_cell(html, ticker):
    import re
    trs = [t for t in re.split(r"(?=<tr)", html) if f"stock.html#{ticker}" in t]
    assert len(trs) == 1, f"expected one <tr> for {ticker}, got {len(trs)}"
    m = re.search(r'<td class="tk">.*?</td>', trs[0], re.S)
    assert m is not None, f"no Name cell for {ticker}"
    return trs[0], m.group(0)


def test_w18c2_variant_row_prints_rpo_coverage():
    import re
    row, r = _w18c2_xyl_row()
    groups = {k: [] for k in bd._DIV_ORDER}
    groups[r["divergence"]] = [row]              # producer says "signal_only"
    html = _w18c2_render(groups)
    _, cell = _w18c2_name_cell(html, "XYL")
    # the coverage the RPO read carries must print on the row itself ...
    assert "0.2× revenue" in cell and "覆盖营收 0.2 倍" in cell
    # ... as one bilingual t() pair (EN lane / zh lane) inside the Name cell.
    m = re.search(r'<span class="l-en">([^<]*)</span>'
                  r'<span class="l-zh">([^<]*)</span>', cell)
    assert m is not None, "no l-en/l-zh pair in the Name cell"
    assert "0.2× revenue" in m.group(1)
    assert "覆盖营收 0.2 倍" in m.group(2)


def test_w18c2_row_without_headline_prints_nothing_extra():
    import re
    base = {"chain": "ai_datacenter", "tier": "compute", "leading": True,
            "trend": "accelerating", "trend_en": "accelerating",
            "trend_zh": "加速", "yoy_pct": 69.0, "consensus_dir": "up"}
    absent = dict(base, ticker="AAAA")           # headline keys absent
    blank = dict(base, ticker="BBBB", headline_en="", headline_zh="")
    groups = {k: [] for k in bd._DIV_ORDER}
    groups["ahead_of_consensus"] = [absent, blank]
    html = _w18c2_render(groups)
    for tkr in ("AAAA", "BBBB"):
        _, cell = _w18c2_name_cell(html, tkr)
        assert "faint" not in cell and "l-en" not in cell
        assert "None" not in cell
        flat = re.sub(r"\s+", "", cell)
        assert flat == f'<tdclass="tk"><ahref="stock.html#{tkr}">{tkr}</a></td>'


# --- W18-C-C3 (DEM-W18C-3): payer table shows capex growth + FCF direction ---

def _w18c3_render(spender_burden):
    """Render demand.html.j2 directly (no data/) with a payer-burden payload."""
    import pathlib
    from jinja2 import Environment, FileSystemLoader
    from engine.i18n import td, tr

    root = pathlib.Path(__file__).resolve().parents[1]
    env = Environment(loader=FileSystemLoader(str(root / "templates")),
                      autoescape=True)
    env.globals.update(tr=tr, td=td)
    return env.get_template("demand.html.j2").render(
        cards=[], groups={k: [] for k in bd._DIV_ORDER},
        div_order=bd._DIV_ORDER, div_meta=bd._DIV_META, track=None,
        phase0=None, n_variants=0, as_of="2026-10-16",
        built="2026-10-16 00:00", spender_burden=spender_burden)


def _w18c3_row(html, ticker):
    import re

    m = re.search(r'<tr>\s*<td class="tk"><a href="stock\.html#'
                  + ticker + r'">.*?</tr>', html, re.S)
    assert m, f"payer row for {ticker} not rendered"
    return m.group(0)


def _w18c3_cells(html, ticker):
    import re

    return [c.strip() for c in
            re.findall(r'<td\b[^>]*>(.*?)</td>', _w18c3_row(html, ticker), re.S)]


# Committed payload shapes (engine/gov_exposure.py per-spender dict).
_W18C3_ORCL = {"capex_ocf_latest": 174.1, "capex_ocf_prior": 120.0,
               "capex_ocf_trend": "rising", "capex_yoy_pct": 162.4,
               "fcf_latest_bn": -23.69, "fcf_trend": "deteriorating",
               "net_debt_delta_bn": 18.2, "fcf_trap": True, "fy_latest": 2026,
               "evidence_tier": "fingerprint", "score_cap": 60}
_W18C3_DHI = {"capex_ocf_latest": 41.0, "capex_ocf_prior": 45.5,
              "capex_ocf_trend": "falling", "capex_yoy_pct": -16.9,
              "fcf_latest_bn": 3.2, "fcf_trend": "improving",
              "net_debt_delta_bn": -0.4, "fcf_trap": False, "fy_latest": 2025,
              "evidence_tier": "fingerprint", "score_cap": 60}


def test_w18c3_payer_row_prints_capex_growth_and_fcf_direction():
    html = _w18c3_render({"ai_datacenter": {"ORCL": _W18C3_ORCL,
                                            "DHI": _W18C3_DHI}})
    orcl = _w18c3_row(html, "ORCL")
    assert "+162%" in orcl
    assert "deteriorating" in orcl and "恶化" in orcl
    assert "FCF trap" in orcl
    dhi = _w18c3_row(html, "DHI")
    assert "-17%" in dhi
    assert "improving" in dhi and "改善" in dhi


def test_w18c3_missing_values_render_dashes():
    gap = dict(_W18C3_ORCL, capex_yoy_pct=None, fcf_trend=None,
               capex_ocf_latest=None, fcf_latest_bn=None,
               net_debt_delta_bn=None)
    html = _w18c3_render({"ai_datacenter": {"XYZ": gap}})
    cells = _w18c3_cells(html, "XYZ")
    assert len(cells) == 9                      # header/row column parity
    assert "—" in cells[3] and "—" in cells[5]  # Capex YoY / FCF trend
    for cell in cells:
        assert "None" not in cell and "nan" not in cell


def test_w18c3_capex_ocf_trend_reads_in_chinese():
    html = _w18c3_render({"ai_datacenter": {"ORCL": _W18C3_ORCL}})
    orcl = _w18c3_row(html, "ORCL")
    assert '<span class="l-zh">上升</span>' in orcl
    assert '<span class="l-en">rising</span>' in orcl


def test_w18c3_payer_header_and_cells_stay_aligned():
    import re

    html = _w18c3_render({"ai_datacenter": {"ORCL": _W18C3_ORCL}})
    at = html.index("Capex/OCF")
    table = html[html.rfind("<table", 0, at):html.index("</table>", at)]
    head = re.search(r"<tr>(.*?)</tr>", table, re.S).group(1)
    assert len(re.findall(r"<th\b", head)) == 9
    assert len(_w18c3_cells(html, "ORCL")) == 9


def _w18c14_render(cards=(), track=None, open_theses=()):
    from jinja2 import Environment, FileSystemLoader
    from engine.i18n import td, tr
    env = Environment(loader=FileSystemLoader(str(bd._ROOT / "templates")), autoescape=True)
    env.globals.update(tr=tr, td=td)
    return env.get_template("demand.html.j2").render(
        cards=list(cards), groups={k: [] for k in bd._DIV_ORDER},
        div_order=bd._DIV_ORDER, div_meta=bd._DIV_META, track=track, phase0=None,
        n_variants=0, as_of="2026-10-16", built="2026-10-16 00:00",
        spender_burden={}, open_theses=open_theses)


def test_w18c14_open_theses_reader(tmp_path):
    d = tmp_path / "data" / "demand_chain"
    d.mkdir(parents=True)
    (d / "theses.jsonl").write_text("\n".join([
        '{"id": "2026-06-19-ai_datacenter-CLSK", "state_asof": "2026-06-19",'
        ' "chain": "ai_datacenter", "subject": "CLSK", "lean": "outperform",'
        ' "check_by": "2026-12-14", "status": "open", "falsifier": "x"}',
        '{"chain": "own_rpo", "subject": "XYL", "lean": "underperform",'
        ' "check_by": "2027-03-22", "state_asof": "2026-07-02", "status": "open"}',
        '{"chain": "own_rpo", "subject": "OLD", "lean": "outperform",'
        ' "check_by": "2026-09-01", "status": "scored"}', "{not-json"]) + "\n")
    got = bd._open_theses(tmp_path)
    assert [(r["subject"], r["check_by"]) for r in got] == [
        ("CLSK", "2026-12-14"), ("XYL", "2027-03-22")]
    assert all(set(r) == {"subject", "chain", "lean", "check_by", "state_asof"}
               for r in got)
    assert bd._open_theses(tmp_path / "absent") == []


def test_w18c14_rpo_as_of_reader(tmp_path):
    import pandas as pd
    d = tmp_path / "data" / "edgar"
    d.mkdir(parents=True)
    df = pd.DataFrame([{"ticker": "CLSK", "fy": 2026, "as_of": "2026-06-19T23:47:24.825975"},
                       {"ticker": "XYL", "fy": 2026, "as_of": "2026-07-02T20:12:00.331498"}])
    df.to_parquet(d / "rpo.parquet", index=False)
    assert bd._rpo_as_of(tmp_path) == "2026-07-02"
    assert bd._rpo_as_of(tmp_path / "absent") is None
    df.drop(columns=["as_of"]).to_parquet(d / "rpo.parquet", index=False)
    assert bd._rpo_as_of(tmp_path) is None
    pd.DataFrame([{"ticker": "X", "as_of": None}]).to_parquet(d / "rpo.parquet", index=False)
    assert bd._rpo_as_of(tmp_path) is None


def test_w18c14_page_lists_open_calls():
    rows = [{"subject": "CLSK", "chain": "ai_datacenter", "lean": "outperform",
             "check_by": "2026-12-14", "falsifier": "do-not-show"},
            {"subject": "XYL", "chain": "own_rpo", "lean": "underperform",
             "check_by": "2027-03-22", "falsifier": "do-not-show"}]
    track = {"open": 2, "overall": {"n": 0, "hit_rate": None}}
    html = _w18c14_render(track=track, open_theses=rows)
    i = html.find("Open calls — what each")
    assert i != -1, "open-calls fold not rendered"
    block = html[html.rfind('<details class="fold">', 0, i):html.find("</details>", i)]
    assert all(s in block for s in ("CLSK", "2026-12-14", "XYL", "2027-03-22"))
    assert "outperform" in block and "跑赢" in block
    assert "underperform" in block and "跑输" in block
    assert "falsifier" not in block and "do-not-show" not in block
    assert "证伪" not in block and "None" not in block
    assert '<details class="fold" open>' not in block
    assert "Open calls — what each" not in _w18c14_render(track=track, open_theses=[])


def test_w18c14_rpo_card_states_data_age():
    card = {"key": "own_rpo", "label_en": "Software bookings (RPO)",
            "label_zh": "软件已签约订单（RPO）", "leading": True,
            "spender_en": "Contracted forward bookings", "spender_zh": "已签约前瞻订单",
            "trend": "", "trend_en": "", "trend_zh": "", "yoy_pct": None,
            "total_bn": None, "fy": 2026, "n": 53, "series": [],
            "leaders": [{"t": "XYL", "yoy": 111, "bn": 2.0}],
            "cache_as_of": "2026-07-02"}
    html = _w18c14_render(cards=[card])
    assert "RPO data last refreshed" in html and "2026-07-02" in html
    assert "RPO数据最近更新于" in html
    stale = {k: v for k, v in card.items() if k != "cache_as_of"}
    assert "RPO data last refreshed" not in _w18c14_render(cards=[stale])
    html3 = _w18c14_render(cards=[dict(card, cache_as_of=None)])
    assert "RPO数据最近更新于" not in html3 and ">None<" not in html3


def test_w18c14_chain_cards_carry_rpo_as_of():
    signals = {"ai_datacenter": {"trend": "accelerating", "yoy_pct": 69.0,
                                 "total_latest_bn": 379.0, "fy_latest": 2025,
                                 "n_spenders": 5, "series": [[2024, 224.1], [2025, 379.0]],
                                 "chain_key": "ai_datacenter"}}
    reads = {"NVDA": {"chain_key": "ai_datacenter", "tier": "compute",
                      "leading": True, "fy_latest": 2025, "yoy_pct": 69.0},
             "ORCL": {"chain_key": "own_rpo", "tier": "bookings",
                      "leading": True, "fy_latest": 2025, "yoy_pct": 41.0,
                      "total_latest_bn": 138.0}}
    cards = bd._chain_cards(signals, reads, rpo_as_of="2026-07-02")
    assert next(c for c in cards if c["key"] == "own_rpo")["cache_as_of"] == "2026-07-02"
    assert "cache_as_of" not in next(c for c in cards if c["key"] == "ai_datacenter")
    plain = next(c for c in bd._chain_cards(signals, reads) if c["key"] == "own_rpo")
    assert plain.get("cache_as_of") is None


def test_w18c14_build_wires_open_calls_and_rpo_age(tmp_path, monkeypatch):
    # The render helper above calls the template directly, so it cannot see whether
    # build() hands the page its open-theses rows and RPO stamp. This drives build().
    import json
    from engine import demand_alerts
    monkeypatch.setattr(bd, "write_page", lambda path, html: None)
    monkeypatch.setattr(demand_alerts, "rebuild", lambda reads, as_of=None: [])
    orcl = {"chain_key": "own_rpo", "tier": "bookings", "leading": True,
            "fy_latest": 2025, "yoy_pct": 41.0, "total_latest_bn": 138.0,
            "trend": "accelerating", "divergence": "ahead_of_consensus",
            "consensus_dir": "up", "headline": {"en": "h", "zh": "h"}}
    monkeypatch.setattr(bd, "_collect", lambda root: ({}, {"ORCL": orcl}, {}))
    d = tmp_path / "data" / "demand_chain"
    d.mkdir(parents=True)
    (d / "track_record.json").write_text(json.dumps(
        {"open": 1, "overall": {"n": 0, "hit_rate": None}}))
    (d / "theses.jsonl").write_text(json.dumps(
        {"subject": "CLSK", "chain": "ai_datacenter", "lean": "outperform",
         "check_by": "2026-12-14", "state_asof": "2026-06-19", "status": "open"}) + "\n")
    import pandas as pd
    e = tmp_path / "data" / "edgar"
    e.mkdir(parents=True)
    pd.DataFrame([{"ticker": "ORCL", "as_of": "2026-07-02T20:12:00"}]).to_parquet(
        e / "rpo.parquet", index=False)
    html = bd.build(tmp_path)
    assert "Open calls — what each" in html and "2026-12-14" in html
    assert "RPO data last refreshed" in html and "2026-07-02" in html
