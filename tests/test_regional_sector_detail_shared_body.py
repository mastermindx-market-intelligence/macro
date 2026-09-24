from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def _payload(region: str) -> dict:
    ticker = {"cn": "600000.SS", "ca": "SHOP.TO", "hk": "0700.HK"}[region]
    fund = {"cn": "512690.SS", "ca": "XIT.TO", "hk": "Technology"}[region]
    return {
        "fund": fund,
        "name": {"cn": "China Tech", "ca": "Canada Tech", "hk": "Technology"}[region],
        "tv": {"cn": "SSE:512690", "ca": "TSX:XIT", "hk": ""}[region],
        "chart_json": '{"t":["2026-09-01"],"c":[100.0]}',
        "mtf_json": "{}",
        "ladder": {
            "dir": "up",
            "label": ("Constructive", "建设性"),
            "entry": {"urgency": "now", "tag": ("Now", "当前"), "text": "Entry is open", "text_zh": "当前可入场"},
            "age_line": "Crossed 2d ago",
            "age_line_zh": "2日前上穿",
            "eq_badge": "A",
            "eq_dir": "up",
            "eq_grade": ("Clean", "干净"),
            "eq_tip": "Entry-quality evidence",
            "eq_tip_zh": "入场质量证据",
            "cycle_plain": {
                "daily_line": "Daily rising", "daily_line_zh": "日线上行",
                "daily_phase": "early", "daily_phase_zh": "早期",
                "weekly_line": "Weekly rising", "weekly_line_zh": "周线上行",
                "weekly_phase": "middle", "weekly_phase_zh": "中段",
                "translation": "Momentum aligned", "translation_zh": "动量一致",
            },
            "why": "Source-owned why", "why_zh": "来源推理",
            "next": "Watch continuation", "next_zh": "观察延续",
        },
        "holdings": [{
            "ticker": ticker,
            "name": "Tencent" if region == "hk" else ticker,
            "ladder": {
                "dir": "up", "label": ("Leader", "领先"), "entry": {"tag": ("Now", "当前")},
                "age_short": "2d", "age_short_zh": "2日", "eq_badge": "B",
                "eq_dir": "up", "eq_tip": "Member entry quality",
            },
            "cycle": {"dc_day": 7, "dc_band": [1, 24]},
            "mtf_json": "{}",
        }],
    }


def _render(template_name: str, region: str) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "xml"]))
    env.globals["td"] = lambda value: value[0] if isinstance(value, (tuple, list)) else value
    return env.get_template(template_name).render(s=_payload(region))


def test_regional_sector_templates_share_one_canonical_render_body():
    china = (TEMPLATES / "china_sector.html.j2").read_text(encoding="utf-8")
    canada = (TEMPLATES / "canada_sector.html.j2").read_text(encoding="utf-8")
    hk = (TEMPLATES / "hk_sector.html.j2").read_text(encoding="utf-8")
    assert "macro render_regional_sector_detail" in china
    assert "Canonical regional sector-detail body" in china
    assert 'from "china_sector.html.j2" import render_regional_sector_detail' in canada
    assert 'from "china_sector.html.j2" import render_regional_sector_detail' in hk
    assert len(canada.splitlines()) <= 4
    assert "macro render_hk_sector_chart" in hk


def test_china_adapter_preserves_existing_presentation_truth():
    html = _render("china_sector.html.j2", "cn")
    assert "China Tech" in html and "(512690.SS)" in html
    assert "SSE:512690" in html and "s3.tradingview.com/tv.js" in html
    assert "../china_lookup.html#600000.SS" in html
    assert "Entry-quality evidence" in html and "Member entry quality" in html


def test_canada_adapter_preserves_existing_presentation_truth():
    html = _render("canada_sector.html.j2", "ca")
    assert "Canada Tech" in html and "(XIT.TO)" in html
    assert "TSX:XIT" in html and "s3.tradingview.com/tv.js" in html
    assert "../canada_stock.html#SHOP.TO" in html
    assert "Entry-quality evidence" in html and "Member entry quality" in html


def test_hk_adapter_preserves_existing_presentation_truth():
    html = _render("hk_sector.html.j2", "hk")
    assert "<title>Technology — cycle & constituents</title>" in html
    assert "(Technology)" not in html
    assert "../lightweight-charts.js" in html
    assert "s3.tradingview.com/tv.js" not in html
    assert "../hk_lookup.html#0700.HK" in html
    assert "Tencent" in html and "0700.HK" in html
    assert "Entry-quality evidence" not in html
    assert "Member entry quality" not in html
