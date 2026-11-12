"""Signed-in hub glance tier stays truthful, plain, and compact."""

from __future__ import annotations

from pathlib import Path
from html import unescape
import re

import pytest

from scripts import build_vector


def _vm(**over) -> dict:
    vm = {
        "risk_on": True,
        "risk_index": 73,
        "risk_word": "ON",
        "momentum": 0.42,
    }
    vm.update(over)
    return vm


def test_vector_cards_translate_machine_values_into_plain_glance_copy() -> None:
    html = build_vector._g_vectors(
        _vm(), {"label": "Goldilocks", "favored": ["Gold", "Silver"]},
        {"label": "Global reflation", "risk": "risk-on"}, {}, {}, {}, {}, {},
        latest_report=None,
        ipo={
            "present": True,
            "band": "OPEN",
            "verdict": "tracks",
            "next_lockup": "ACME",
            "next_lockup_date": "2026-10-03",
            "lockups_approaching": 3,
        },
    )

    assert "Risk on" in html
    assert "Momentum positive" in html
    assert "Risk ON · 73" not in html
    assert "Mom 0.42" not in html
    assert "Market state, flows & allocation" in html
    assert "class allocation" not in html
    assert "Read the latest research" in html
    assert "Cycle timing" in html and "Cycle clocks" not in html
    assert "Sector rotation" in html and "Rotation desk" not in html
    assert "50 major assets" in html and "50-asset board" not in html
    assert "Bond health" in html and "Health 73" not in html
    assert "Allocation & market shocks" in html and "shock detection" not in html
    assert "偏好：黄金, 白银" in html
    assert "全球再通胀 · 风险偏好" in html
    assert "research desk" not in html
    assert "Next shares unlock: ACME 10-03 · 3 lock-ups approaching" in html
    assert "Next un-lock" not in html
    assert "coming soon" not in html
    assert 'data-tip-en="' in html and "Risk index 73/100" in html
    assert "New-issue window & lock-up cliffs" not in html
    for emoji in ("🚀", "🏛️", "💱"):
        assert emoji not in html


def test_vector_card_momentum_copy_handles_down_flat_and_missing() -> None:
    params = ({"momentum": -0.1}, {"momentum": 0}, {"momentum": None})
    expected = ("Momentum negative", "Momentum flat", "Momentum unavailable")
    for over, phrase in zip(params, expected):
        html = build_vector._g_vectors(_vm(**over), {}, {}, {}, {}, {}, {}, {})
        assert phrase in html


def test_hub_hero_shows_site_live_status_not_data_freshness(monkeypatch) -> None:
    blob = [{"cc": "US", "macro_asof": "2026-09-18"}]
    monkeypatch.setattr(build_vector, "_globe_markets", lambda: blob)
    monkeypatch.setattr(build_vector, "_g_legend", lambda _blob: "")
    monkeypatch.setattr(build_vector, "_standout_labels", lambda _key: [])
    monkeypatch.setattr(build_vector, "_latest_report_data", lambda: None)
    monkeypatch.setattr(build_vector, "_g_markets", lambda *_a, **_k: "")
    monkeypatch.setattr(build_vector, "_g_vectors", lambda *_a, **_k: "")
    monkeypatch.setattr(build_vector, "_g_alerts", lambda *_a, **_k: "")
    monkeypatch.setattr(build_vector, "_hub_product_nav_html", lambda: "")
    monkeypatch.setattr(build_vector, "_hub_footer_html", lambda: "")

    html = build_vector._hub_html(_vm(), {}, [])
    badge = html.split('<div class="hub-snapshot-meta">', 1)[1].split("</header>", 1)[0]

    assert "SITE LIVE" in badge and "网站运行中" in badge
    assert "Page built" not in badge and "页面生成于" not in badge
    assert "Latest market snapshot" not in badge
    assert "Live ·" not in badge and "实时 ·" not in badge
    assert "hub-clock-wrap" not in badge
    assert "data-asof" not in badge
    assert "livepulse" not in html
    assert "background:var(--info)" in html
    assert '@media(max-width:560px){.h .eyebrow{display:none}}' not in html
    assert "setInterval" not in html



def test_hub_html_calls_standout_labels_not_tickers() -> None:
    """RED on a3cc6de0: glance-copy test patched _standout_tickers, a dead seam.

    _hub_html now walks _standout_labels so CN/HK chips can carry company names.
    """
    import inspect
    src = inspect.getsource(build_vector._hub_html)
    assert "_standout_labels(_key)" in src
    assert "_standout_tickers(_key)" not in src


def _hub_css_rule(selector: str, *, containing: str | None = None) -> str:
    rules = re.findall(re.escape(selector) + r"\{([^{}]*)\}", build_vector._GLOBE_HUB_CSS)
    assert rules, f"missing hub CSS rule for {selector}"
    if containing is None:
        return rules[0]
    matches = [rule for rule in rules if containing in rule]
    assert matches, f"missing {selector} rule containing {containing!r}"
    return matches[0]


def test_mobile_hub_section_switch_keeps_real_40px_button_floor() -> None:
    shell = _hub_css_rule(".hub-seg", containing="display:flex")
    button = _hub_css_rule(".hub-seg-btn")
    # Border-box shell: 40px buttons + 3px top/bottom padding + 1px borders.
    assert "height:48px" in shell
    assert "min-height:40px" in button


def test_hub_history_standalone_actions_keep_40px_floor() -> None:
    timeline = _hub_css_rule(".al-more")
    toggle = _hub_css_rule(".ha-toggle")
    assert "min-height:40px" in timeline
    assert "min-height:40px" in toggle


def test_mobile_globe_country_controls_keep_effective_40px_floor() -> None:
    leg = _hub_css_rule(".gd-leg", containing="min-height:40px")
    node_hit_slop = _hub_css_rule(".gd-isl .body::after", containing="inset:-10px")
    assert "box-sizing:border-box" in leg
    # The floating globe nodes deliberately keep their compact visual pill; the
    # transparent mobile pseudo-element expands the actual pointer target instead.
    assert "inset:-10px" in node_hit_slop


_START_HTML = Path(__file__).resolve().parents[1] / "site" / "start.html"
_SPARSE_START = pytest.mark.skipif(
    not _START_HTML.exists(),
    reason="sparse tree: start.html is skip-worktree; render lane owns the artifact",
)


@_SPARSE_START
def test_committed_start_artifact_matches_the_glance_contract() -> None:
    html = _START_HTML.read_text(encoding="utf-8")
    badge = html.split('<div class="hub-snapshot-meta">', 1)[1].split("</header>", 1)[0]
    assert "SITE LIVE" in badge and "网站运行中" in badge
    assert "Page built" not in badge and "页面生成于" not in badge
    assert "data-asof" not in badge
    assert "hub-clock-wrap" not in badge

    for required in (
        "Explore",
        "Bond health",
        "Read the latest research", "Market state, flows & allocation",
    ):
        assert required in html
    for banned in (
        "Live · <span class=\"hub-clock\"", "livepulse", "setInterval(tick",
        "Next un-lock", "class allocation", "research desk",
        "Dollar-smile currency board", "Allocation & shock detection",
        "🚀", "🏛️", "💱",
    ):
        assert banned not in html

    # The artifact follows current inputs; do not freeze one day's risk state.
    assert re.search(r"Risk (?:on|off)</span>", html)
    assert re.search(r"Momentum (?:positive|negative|flat|unavailable)</span>", html)
    assert not re.search(r">(?:Mom -?\d|Risk (?:ON|OFF) · \d|Health \d)", html)


def _feature_cta(html: str, href: str, lang: str) -> str:
    for card in re.finditer(r'<a\b([^>]*)>(.*?)</a>', html, re.S):
        attrs = card.group(1)
        classes = re.search(r'class="([^"]*)"', attrs)
        if not classes or "card" not in classes.group(1).split():
            continue
        if not re.search(r'href="' + re.escape(href) + r'"', attrs):
            continue
        labels = re.findall(r'<span class="l-' + lang + r'">([^<]*)</span>', card.group(2))
        assert labels, (href, lang)
        return unescape(labels[-1])
    raise AssertionError(f"Feature card missing: {href}")


@_SPARSE_START
@pytest.mark.parametrize("href", ["sector_central_china.html", "bonds.html"])
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_feature_cta_artifact_matches_the_source(href: str, lang: str) -> None:
    produced = build_vector._g_vectors(_vm(), {}, {}, {}, {}, {}, {}, {})
    artifact = _START_HTML.read_text()
    assert _feature_cta(artifact, href, lang) == _feature_cta(produced, href, lang)


def test_market_card_status_prints_turn_date_and_check() -> None:
    fn = build_vector._market_card_status
    row = {
        "rphase": "turning", "rtoward_en": "Stagflation", "rtoward_zh": "滞胀",
        "rdir": "deteriorating", "macro_asof": "1999-01-01", "rdir_asof": "1999-01-01",
        "flip_axis": "growth", "flip_component": "copper_gold",
        "rflip": "LEAK-RFLIP", "margin": "LEAK-MARGIN",
        "threshold": "LEAK-THRESHOLD", "z": "LEAK-Z", "note": "LEAK-NOTE",
    }
    html = fn(row)
    en = (
        "Turning toward Stagflation · as of 1999-01-01"
        " · closest growth check: copper versus gold"
    )
    zh = "正转向滞胀 · 截至 1999-01-01 · 最接近的增长检验：铜对黄金"
    assert html.startswith('<p class="card-status">')
    assert 'class="l-en"' in html and 'class="l-zh"' in html
    assert en in html and zh in html and "2026-10-30" not in html
    for leak in ("LEAK-RFLIP", "LEAK-MARGIN", "LEAK-THRESHOLD", "LEAK-Z", "LEAK-NOTE"):
        assert leak not in html
    quiet = fn(dict(row, flip_component="not_copper"))
    assert "1999-01-01" in quiet and "copper versus gold" not in quiet
    assert "铜对黄金" not in quiet and fn({}) == ""
    other_axis = fn(dict(row, flip_axis="inflation"))
    assert "copper versus gold" not in other_axis and "铜对黄金" not in other_axis
    head = fn({"rphase": "aging", "rtoward_en": "Reflation", "rtoward_zh": "再通胀"})
    assert "Heading toward Reflation" in head and "正朝再通胀移动" in head
    soft, firm = fn({"rdir": "deteriorating"}), fn({"rdir": "improving"})
    hold = fn({"rdir": "stable"})
    assert "Worsening" in soft and "正在转差" in soft
    assert "Improving" in firm and "正在改善" in firm
    assert "Holding" in hold and "维持" in hold


def test_market_card_status_sits_under_the_card_header() -> None:
    import inspect

    source = inspect.getsource(build_vector._g_markets)
    assert "_market_card_status(m)" in source
    before = source.split("_market_card_status(m)", 1)[0]
    assert "card-top" in before and "</span></div>" in before


def test_regime_dynamics_carries_the_flip_axis_and_component(monkeypatch, tmp_path) -> None:
    import json

    timeline = {"g": [0.5] * 40, "i": [0.5] * 40, "trans": ["STABLE"]}
    (tmp_path / "regime_timeline.json").write_text(json.dumps(timeline), encoding="utf-8")
    monkeypatch.setattr(build_vector.config, "site_dir", lambda: tmp_path)
    flip = {"axis": "growth", "component": "copper_gold", "margin": 0.1}
    out = build_vector._regime_dynamics("US", {"quad": "Q2", "flip_condition": flip})
    assert out["flip_axis"] == "growth"
    assert out["flip_component"] == "copper_gold"


def test_card_holds_the_direction_date_apart_from_the_regime_date() -> None:
    fn = build_vector._market_card_status
    row = {
        "rphase": "turning", "rtoward_en": "Stagflation", "rtoward_zh": "滞胀",
        "rdir": "deteriorating", "macro_asof": "2026-10-30", "rdir_asof": "2026-10-20",
        "flip_axis": "growth", "flip_component": "copper_gold",
    }
    apart = fn(row)
    assert (
        "Turning toward Stagflation as of 2026-10-20 · regime as of 2026-10-30"
        " · closest growth check: copper versus gold"
    ) in apart
    assert (
        "正转向滞胀（截至 2026-10-20） · 周期截至 2026-10-30 · 最接近的增长检验：铜对黄金"
    ) in apart
    assert "Stagflation · as of 2026-10-30" not in apart and "滞胀 · 截至 2026-10-30" not in apart

    same = fn(dict(row, rdir_asof="2026-10-30"))
    assert "Turning toward Stagflation · as of 2026-10-30 · closest" in same
    assert "正转向滞胀 · 截至 2026-10-30 · 最接近" in same
    assert "regime as of" not in same and "周期截至" not in same

    undated = fn(dict(row, rdir_asof=None))
    assert "Turning toward Stagflation · regime as of 2026-10-30" in undated
    assert "正转向滞胀 · 周期截至 2026-10-30" in undated

    no_record = fn(dict(row, macro_asof=""))
    assert "Turning toward Stagflation as of 2026-10-20 · closest" in no_record
    assert "regime as of" not in no_record and "周期截至" not in no_record

    no_direction = fn({"macro_asof": "2026-10-30"})
    assert "as of 2026-10-30" in no_direction and "截至 2026-10-30" in no_direction
    assert "regime as of" not in no_direction and "周期截至" not in no_direction


def test_regime_dynamics_dates_the_direction_from_its_own_file(monkeypatch, tmp_path) -> None:
    import json

    monkeypatch.setattr(build_vector.config, "site_dir", lambda: tmp_path)
    dates = ["2026-01-01"] * 39 + ["2026-10-20"]
    timeline = {"dates": dates, "g": [0.5] * 40, "i": [0.5] * 40, "trans": ["STABLE"]}
    file = tmp_path / "regime_timeline.json"
    file.write_text(json.dumps(timeline), encoding="utf-8")
    out = build_vector._regime_dynamics("US", {"quad": "Q2"})
    assert out["rdir_asof"] == "2026-10-20"
    card = build_vector._market_card_status(dict(out, macro_asof="2026-10-30"))
    assert "Holding as of 2026-10-20 · regime as of 2026-10-30" in card

    file.write_text(json.dumps(dict(timeline, dates=dates[:-1])), encoding="utf-8")
    assert build_vector._regime_dynamics("US", {"quad": "Q2"})["rdir_asof"] is None

    no_dates = {k: v for k, v in timeline.items() if k != "dates"}
    file.write_text(json.dumps(no_dates), encoding="utf-8")
    assert build_vector._regime_dynamics("US", {"quad": "Q2"})["rdir_asof"] is None

    gap = dict(timeline, i=[0.5] * 39 + [None])
    file.write_text(json.dumps(gap), encoding="utf-8")
    none = build_vector._regime_dynamics("US", {"quad": "Q2"})
    assert none["rdir"] is None and none["rdir_asof"] is None


def test_site_status_is_independent_of_build_and_market_dates(monkeypatch) -> None:
    monkeypatch.setattr(build_vector, "_globe_markets", lambda: [{"cc": "US"}])
    monkeypatch.setattr(build_vector, "_g_legend", lambda _blob: "")
    monkeypatch.setattr(build_vector, "_standout_labels", lambda _key: [])
    monkeypatch.setattr(build_vector, "_latest_report_data", lambda: None)
    monkeypatch.setattr(build_vector, "_g_markets", lambda *_a, **_k: "")
    monkeypatch.setattr(build_vector, "_g_vectors", lambda *_a, **_k: "")
    monkeypatch.setattr(build_vector, "_g_alerts", lambda *_a, **_k: "")
    monkeypatch.setattr(build_vector, "_hub_product_nav_html", lambda: "")
    monkeypatch.setattr(build_vector, "_hub_footer_html", lambda: "")
    macro = {"date": "1999-03-04"}

    built_vm = dict(_vm(), built="2026-06-14 01:02 UTC")
    unbuilt_vm = dict(_vm())
    unbuilt_vm.pop("built", None)
    badges = []
    for vm in (built_vm, unbuilt_vm):
        html = build_vector._hub_html(vm, macro, [])
        badge = html.split('<div class="hub-snapshot-meta">', 1)[1].split("</header>", 1)[0]
        badges.append(badge)
        assert 'class="hub-site-status"' in badge
        assert '<span class="l-en">SITE LIVE</span>' in badge
        assert '<span class="l-zh">网站运行中</span>' in badge
        for banned in (
            "2026-06-14", "Jun 14, 2026", "2026年6月14日",
            "1999-03-04", "Mar 4, 1999", "1999年3月4日",
            "Page built", "页面生成于", "data-asof", "hub-clock",
            "Latest market snapshot", "最新市场快照", "Live ·", "实时 ·",
        ):
            assert banned not in badge
    assert badges[0] == badges[1]


def _bi_prefixes(src: str) -> list:
    import ast

    def lead(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return lead(node.left)
        return None

    found = []
    for node in ast.walk(ast.parse(src)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "_bi" or len(node.args) < 2:
            continue
        en, zh = lead(node.args[0]), lead(node.args[1])
        if en is not None and zh is not None:
            found.append((en, zh))
    return found


def test_hub_site_status_has_the_bilingual_website_label() -> None:
    pairs = _bi_prefixes(Path(build_vector.__file__).read_text(encoding="utf-8"))
    assert pairs.count(("SITE LIVE", "网站运行中")) == 1
    for en, zh in pairs:
        assert not en.startswith("Page built") and not zh.startswith("页面生成于")
        assert "Latest market snapshot" not in en and "最新市场快照" not in zh
