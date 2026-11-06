"""China macro sector navigation through the real template and committed page.

Daily sector ordering is data, not a test constant. Fixtures exercise ordering,
rank preservation and missing identities; the committed-page check follows the
currently displayed rows and the canonical configured detail routes.
"""
from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from engine import i18n

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/china.html.j2"
REGIONS = {
    "overview": ("{# Sector Temperature card #}",
                 "<!-- =============== ROW 3:"),
    "markets": ("<!-- Markets dialog (index health + heatmap + cross-asset rates) -->",
                "<!-- Sentiment dialog -->"),
    "sector": ("<!-- Sector dialog -->", "<!-- Policy dialog -->"),
    "playbook": ("<!-- Playbook dialog -->", "<!-- Calendar events dialog -->"),
}


def _source() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _render(region: str, context: dict) -> BeautifulSoup:
    source = _source()
    start_marker, end_marker = REGIONS[region]
    assert source.count(start_marker) == 1
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    macro_start = source.index("{% macro t(")
    macro_end = source.index("{%- endmacro %}", macro_start) + len("{%- endmacro %}")
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr, t_pctile=i18n.t_pctile)
    html = env.from_string(source[macro_start:macro_end] + source[start:end]).render(**context)
    return BeautifulSoup(html, "html.parser")


@pytest.fixture
def context() -> dict:
    names = yaml.safe_load((ROOT / "config.yml").read_text())["china"]["yahoo"]["sector_etfs"]
    entries = list(names.items())
    # Deliberately nonalphabetical fixture order; it must survive every surface.
    order = [7, 1, 13, 3, 9, 5, 11, 15, 0, 2, 4, 6, 8, 10, 12, 14]
    assert len(entries) == 16
    sectors = []
    for rank, index in enumerate(order, 1):
        ticker, meta = entries[index]
        sectors.append(dict(ticker=ticker, name=meta[0], rank=rank,
                            dir=("up", "caution", "down")[rank % 3],
                            mom5=rank / 10, mom20=-rank / 10, mom60=rank / 5,
                            label="UPTREND", label_zh="上涨趋势", ob=False))
    missing_empty = dict(name="Missing empty identity", ticker="")
    missing_none = dict(name="Missing null identity", ticker=None)
    missing_absent = dict(name="Missing absent identity")
    return {
        "sectors": sectors,
        "sectors_by_ticker": {row["ticker"]: row for row in sectors},
        "actions": {
            "buy_now": [sectors[1], missing_none],
            "buy_soon": [sectors[6], sectors[9]],
            "avoid": [sectors[3], missing_absent, sectors[5]],
        },
        "pb_obj": {
            "leaders": [sectors[2], missing_empty, sectors[4], sectors[8], sectors[12]],
            "dial": {"posture": "NEUTRAL", "reasons": []},
            "preferred": [sectors[0], dict(missing_none, rank=None), sectors[10]],
            "avoid": [dict(sectors[5], state="UPTREND"),
                      dict(missing_empty, state="Unknown state")],
            "progress": None, "next_list": [],
            "honesty": {"en": "Fixture context only", "zh": "仅用于测试"},
        },
        "index_health": [], "hsi_tile": None, "market_tiles": [],
        "I": {"margin": None}, "breadth": None, "pair": {},
    }


def _href(row: dict) -> str:
    return f"sectors/{row['ticker']}.html"


def _links(node) -> list[str]:
    return [a["href"] for a in node.select("a.cnx-sector-link")]


def test_overview_keeps_order_three_item_limits_and_parent_click_guard(context):
    soup = _render("overview", context)
    groups = soup.select(".cnx-chips")
    assert len(groups) == 2
    assert _links(groups[0]) == [_href(context["sectors"][i]) for i in (2, 4)]
    assert _links(groups[1]) == [_href(context["sectors"][i]) for i in (1, 6)]
    assert [len(group.select(".cnx-chip")) for group in groups] == [3, 3]
    for link in soup.select("a.cnx-sector-link"):
        assert link.get("onclick") == "event.stopPropagation()"
        assert link.select_one(".l-en") and link.select_one(".l-zh")
    assert "Missing empty identity" in groups[0].get_text()
    assert "Missing null identity" in groups[1].get_text()


def test_markets_leaders_and_laggards_preserve_rotation_order_and_rank(context):
    soup = _render("markets", context)
    rows = soup.select(".cnx-ledd")
    expected = context["sectors"][:4] + list(reversed(context["sectors"][-4:]))
    assert [_links(row) for row in rows] == [[_href(row)] for row in expected]
    assert [row.select_one(".rk").get_text() for row in rows] == [
        "#1", "#2", "#3", "#4", "#16", "#15", "#14", "#13"
    ]
    assert all(row.select_one("a.cnx-tt-up") for row in rows[:4])
    assert all(row.select_one("a.cnx-tt-dn") for row in rows[4:])
    assert "click a sector for its detail page" in soup.get_text()
    assert "点击板块进入详情页" in soup.get_text()


def test_sector_action_and_leader_chips_preserve_full_lists_and_rank(context):
    soup = _render("sector", context)
    groups = soup.select(".cnx-chips")
    assert len(groups) == 3
    expected_indices = [(1, 6, 9), (3, 5), (2, 4, 8, 12)]
    assert [_links(group) for group in groups] == [
        [_href(context["sectors"][i]) for i in indices] for indices in expected_indices
    ]
    assert [len(group.select(".cnx-chip")) for group in groups] == [4, 3, 5]
    for group, indices in zip(groups[:2], expected_indices[:2]):
        for link, index in zip(group.select("a"), indices):
            assert f"#{context['sectors'][index]['rank']}" in link.get_text()
    assert "Missing absent identity" in groups[1].get_text()


def test_sector_rotation_table_preserves_top_ten_ranks_values_and_direction(context):
    soup = _render("sector", context)
    rows = soup.select("table.cnx-mt tr")[1:]
    assert len(rows) == 10
    for rank, (row, sector) in enumerate(zip(rows, context["sectors"][:10]), 1):
        cells = row.find_all("td", recursive=False)
        assert _links(cells[0]) == [_href(sector)]
        assert cells[1].get_text(strip=True) == str(rank)
        assert cells[2].get_text(strip=True) == f"{sector['mom5']:+.1f}%"
        assert cells[3].get_text(strip=True) == f"{sector['mom20']:+.1f}%"
        assert cells[4].get_text(strip=True) == f"{sector['mom60']:+.1f}%"
        tone = {"up": "cnx-tt-up", "caution": "cnx-tt-fl", "down": "cnx-tt-dn"}[sector["dir"]]
        assert tone in cells[-1].get("class", [])


def test_playbook_preserves_preferred_ranks_avoid_states_and_missing_identity(context):
    soup = _render("playbook", context)
    groups = soup.select(".cnx-cols2 > div")
    preferred = groups[0].select(".cnx-kv")
    avoid = groups[1].select(".cnx-kv")
    assert [_links(row) for row in preferred] == [
        [_href(context["sectors"][0])], [], [_href(context["sectors"][10])]
    ]
    assert [row.select_one(".v").get_text(strip=True) for row in preferred] == ["#1", "", "#11"]
    assert [_links(row) for row in avoid] == [[_href(context["sectors"][5])], []]
    assert "Unknown state" in avoid[1].get_text()
    assert "Missing null identity" in preferred[1].get_text()


@pytest.mark.parametrize("region", ["overview", "sector", "playbook"])
def test_missing_tickers_stay_readable_and_never_make_empty_routes(context, region):
    soup = _render(region, context)
    assert "Missing" in soup.get_text()
    for link in soup.select("a.cnx-sector-link"):
        assert re.fullmatch(r"sectors/\d{6}\.(SS|SZ)\.html", link["href"])
        assert "Missing" not in link.get_text()


def test_empty_sector_inputs_do_not_invent_navigation(context):
    empty = deepcopy(context)
    empty["sectors"] = []
    empty["sectors_by_ticker"] = {}
    empty["actions"] = {"buy_now": [], "buy_soon": [], "avoid": []}
    empty["pb_obj"] = None
    for region in REGIONS:
        assert not _render(region, empty).select("a.cnx-sector-link")


def test_committed_page_links_its_current_rows_to_real_canonical_destinations():
    names = yaml.safe_load((ROOT / "config.yml").read_text())["china"]["yahoo"]["sector_etfs"]
    by_name = {meta[0]: ticker for ticker, meta in names.items()}
    soup = BeautifulSoup((ROOT / "site/china.html").read_text(), "html.parser")
    selectors = [
        "[onclick=\"cnxOpenDlg('cnx-dlg-sector')\"] .cnx-chips .cnx-chip",
        "#cnx-dlg-markets .cnx-ledd > :first-child",
        "#cnx-dlg-sector .cnx-chips .cnx-chip",
        "#cnx-dlg-sector table.cnx-mt tr td:first-child",
        "#cnx-dlg-playbook .cnx-cols2 .cnx-kv > .k",
    ]
    for selector in selectors:
        for node in soup.select(selector):
            name = node.select_one(".l-en").get_text()
            assert name in by_name
            link = node if node.name == "a" else node.select_one("a.cnx-sector-link")
            assert link is not None, (selector, name)
            assert link["href"] == f"sectors/{by_name[name]}.html"
            assert (ROOT / "site" / link["href"]).is_file()
    # Today's rotation order is compared with today's leading rows, not a dated list.
    rotation = _links(soup.select_one("#cnx-dlg-sector table.cnx-mt"))[:4]
    leaders = [_links(row)[0] for row in soup.select("#cnx-dlg-markets .cnx-ledd")[:4]]
    assert leaders == rotation and len(leaders) == 4


def test_focus_rule_uses_existing_semantic_ring_and_committed_css_matches_template():
    source = _source()
    focus = re.search(r"body\.page-china \.cnx-sector-link:focus-visible\{([^}]+)\}", source)
    assert focus is not None
    rule = focus.group(1).replace(" ", "")
    assert "outline:2pxsolidvar(--link)" in rule
    assert "outline-offset:2px" in rule
    assert "border-radius" not in rule
    tag = re.search(r"<style[^>]*>.*?</style>", source, re.S).group(0)
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    rendered = env.from_string(tag).render(mode="macro")
    css = re.search(r"<style[^>]*>(.*?)</style>", rendered, re.S).group(1).encode()
    digest = hashlib.sha256(css).hexdigest()[:8]
    asset = ROOT / f"site/assets/css/{digest}.css"
    assert asset.read_bytes() == css
    page = (ROOT / "site/china.html").read_text()
    assert f"assets/css/{digest}.css?v={digest}" in page
