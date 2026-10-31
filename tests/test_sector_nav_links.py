"""Sector pages render under site/sectors/ (one directory deep), so every site-nav
link MUST be ../-prefixed (or absolute) — a bare `href="macro.html"` resolves to
/sectors/macro.html and 404s on the live site. Regression guard for that bug."""
import re
import sys
from pathlib import Path

import jinja2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
# a bare relative link: not ../, not root-absolute, not external/anchor/scheme
BARE = re.compile(r'href="(?!\.\./|/|https?:|#|mailto:|tel:|data:|javascript:)([^"]+)"')


def _nav(html: str) -> str:
    i = html.find('<nav class="site-nav">')
    if i < 0:
        return ""
    j = html.find("</nav>", i)
    return html[i:j] if j > 0 else ""


def test_sector_templates_have_no_bare_nav_links():
    bad = {}
    for name in ("sector", "canada_sector", "china_sector", "hk_sector"):
        p = ROOT / "templates" / f"{name}.html.j2"
        if not p.exists():
            continue
        hits = BARE.findall(_nav(p.read_text()))
        if hits:
            bad[name] = hits[:8]
    assert not bad, f"bare (un-prefixed) nav links in sector templates: {bad}"


def test_built_sector_pages_have_no_bare_nav_links():
    d = ROOT / "site" / "sectors"
    if not d.is_dir():
        import pytest
        pytest.skip("no built sector pages in this checkout")
    bad = {}
    for p in sorted(d.glob("*.html")):
        hits = BARE.findall(_nav(p.read_text(errors="ignore")))
        if hits:
            bad[p.name] = hits[:5]
    assert not bad, f"bare nav links in built sector pages (would 404 live): {bad}"


def _holdings_heading_source() -> str:
    """Nav checks above only read template text. Render the holdings heading
    block (t/help macros plus the panel through </h2>) on its own."""
    text = (ROOT / "templates" / "sector.html.j2").read_text()
    macros, sep, _rest = text.partition("<!DOCTYPE")
    assert sep, "sector.html.j2 has no doctype to split macros from the page"
    help_at = text.find("Every holding gets the same treatment as the ETF")
    assert help_at >= 0, "holdings help text missing"
    panel_at = text.rfind('<div class="panel">', 0, help_at)
    assert panel_at >= 0, "holdings panel div missing"
    h2_end = text.find("</h2>", help_at)
    assert h2_end >= 0, "holdings heading close missing"
    return macros + text[panel_at:h2_end + len("</h2>")]


def _render_holdings_heading(rows: list) -> str:
    env = jinja2.Environment(autoescape=False)
    return env.from_string(_holdings_heading_source()).render(s={"holdings": rows})


def test_holdings_heading_sums_share_and_drops_top_10():
    html = _render_holdings_heading([
        {"weight_pct": 24.26},
        {"weight_pct": 10.5},
        {"weight_pct": 5.0},
    ])
    assert "Top 3 holdings, 40% of the fund" in html
    assert "前 3 大持仓，合计占基金 40%" in html
    assert "Top 10 holdings" not in html


def test_holdings_heading_omits_share_when_any_weight_missing():
    html = _render_holdings_heading([
        {"weight_pct": 24.26},
        {},
        {"weight_pct": 5.0},
    ])
    assert "Top 3 holdings — each analyzed on its own cycle" in html
    assert "前 3 大持仓 — 各自按其周期分析" in html
    assert "% of the fund" not in html
    assert "合计占基金" not in html
    assert "Top 10 holdings" not in html


def test_holdings_heading_counts_zero_weight_in_the_share():
    html = _render_holdings_heading([
        {"weight_pct": 24.26},
        {"weight_pct": 0},
        {"weight_pct": 5.0},
    ])
    assert "Top 3 holdings, 29% of the fund" in html
    assert "前 3 大持仓，合计占基金 29%" in html
    assert "Top 10 holdings" not in html


if __name__ == "__main__":
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        fn(); print("PASS", fn.__name__)
