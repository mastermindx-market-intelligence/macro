"""markets.html risk-regime strip (UD-B2-W4B-1).

Fixture scenarios live under tests/fixtures/markets_regime_strip/.
Live-tree checks read the three persisted latest.json files and assert the
copy that belongs to that verdict. They print the branch they exercised.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import jinja2
import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
FIXTURES = ROOT / "tests" / "fixtures" / "markets_regime_strip"
PAGE = ROOT / "site" / "markets.html"
MARKETS = ("us", "hk", "cn")

# Builder side effects that are not the page under test. Restored so a render
# check cannot append a PIT row or rewrite the regime-prior script.
_BAKE_SIDE_EFFECTS = (
    "site/marketsdata/markets_engine.js",
    "site/markets_data.js",
    "site/markets_app.js",
    "site/markets_i18n.js",
    "site/cycle.css",
    "site/mm_charts.js",
    "site/regimedata/regime_prior.js",
    "data/regime/market_state_history.parquet",
)


def _hero_stance_pairs() -> list[tuple[str, str]]:
    """Stance literals in templates/_unified_dashboard_hero.html.j2, in order."""
    hero = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text(encoding="utf-8")
    return re.findall(
        r"\{%- set _do_en = '(.+?)' -%\}\{%- set _do_zh = '(.+?)' -%\}",
        hero,
    )


def _spec_copy() -> dict[str, tuple[str, str]]:
    pairs = _hero_stance_pairs()
    # US block: index 4 is the RISK_ON verdict band, 5 RISK_OFF, 6 anything else, 7 no vm.
    watch, stand, ready, null = pairs[4], pairs[5], pairs[6], pairs[7]
    return {"RISK_ON": watch, "RISK_OFF": stand, "other": ready, "missing": null}


def _state_words(kind: str) -> tuple[str, str]:
    if kind == "RISK_ON":
        return "Risk-on", "风险偏好"
    if kind == "RISK_OFF":
        return "Risk-off", "风险规避"
    return "Read being updated", "判读更新中"


def _kind(view) -> str:
    verdict = view.get("verdict") if isinstance(view, dict) else None
    if verdict == "RISK_ON":
        return "RISK_ON"
    if verdict == "RISK_OFF":
        return "RISK_OFF"
    if isinstance(view, dict) and verdict:
        return "other"
    return "missing"


def _env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES)),
        autoescape=False,
    )
    env.filters["min"] = lambda seq: min(seq)
    env.filters["regex_replace"] = (
        lambda s, pattern, repl: re.sub(pattern, repl, s) if isinstance(s, str) else s
    )
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t, zip=zip)
    except Exception:  # noqa: BLE001 — English fallback, same as build_markets
        env.globals.update(
            td=lambda en, *_a, **_k: en,
            tr=lambda en, *_a, **_k: en,
            t=lambda en, zh="": en,
            zip=zip,
        )
    return env


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def render_strip(vm: dict) -> str:
    return _env().get_template("_market_regime_strip.html.j2").render(**vm)


def render_hero(vm: dict) -> str:
    return _env().get_template("_unified_dashboard_hero.html.j2").render(**vm)


def render_markets(vm: dict) -> str:
    return _env().get_template("markets.html.j2").render(**vm)


def _strip(html: str):
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one("#market-regime-strip")
    assert node is not None, "risk-regime strip not in render"
    return node


def _lang(node, lang: str) -> str:
    span = None
    for child in node.find_all("span", recursive=False):
        if lang in (child.get("class") or []):
            span = child
            break
    assert span is not None, f"{lang} missing in {node.get('class')}"
    return span.get_text(strip=True)


def _row(strip, market: str):
    row = strip.select_one(f'.mrs-row[data-market="{market}"]')
    assert row is not None, market
    return row


def _assert_row_copy(row, kind: str) -> None:
    state_en, state_zh = _state_words(kind)
    do_en, do_zh = _spec_copy()[kind]
    assert _lang(row.select_one(".mrs-state"), "l-en") == state_en
    assert _lang(row.select_one(".mrs-state"), "l-zh") == state_zh
    assert _lang(row.select_one(".mrs-do"), "l-en") == do_en
    assert _lang(row.select_one(".mrs-do"), "l-zh") == do_zh


def _hero_lang(node, lang: str) -> str:
    span = node.select_one(f"span.{lang}")
    assert span is not None
    return span.get_text(strip=True)


def _hero_us_state(hero_html: str) -> tuple[str, str]:
    soup = BeautifulSoup(hero_html, "html.parser")
    en = soup.select_one("span.ud-verdict-word.l-en")
    zh = soup.select_one("span.ud-verdict-word.l-zh")
    assert en is not None and zh is not None
    return en.get_text(strip=True), zh.get_text(strip=True)


def _hero_stance(hero_html: str, market: str) -> tuple[str, str]:
    soup = BeautifulSoup(hero_html, "html.parser")
    if market == "us":
        node = soup.select_one(".ud-meta .mx-stance")
    else:
        row = soup.select_one(f'.mx-spine-row[data-market="{market}"]')
        assert row is not None, market
        node = row.select_one(".mx-spine-stance .mx-stance")
    assert node is not None, market
    return _hero_lang(node, "l-en"), _hero_lang(node, "l-zh")


def test_exactly_three_rows_us_hk_cn_only():
    strip = _strip(render_strip(_load("risk_on.json")))
    markets = [row["data-market"] for row in strip.select(".mrs-row")]
    assert markets == ["us", "hk", "cn"]
    blob = strip.get_text(" ", strip=True).lower()
    assert "bond" not in blob
    assert "commodit" not in blob


def test_no_digit_characters_in_strip_text_en_and_zh():
    for name in ("risk_on.json", "risk_off.json", "missing.json", "other_verdict.json", "hk_feed_missing.json"):
        strip = _strip(render_strip(_load(name)))
        for lang in ("l-en", "l-zh"):
            for span in strip.select(f"span.{lang}"):
                text = span.get_text()
                digits = [ch for ch in text if ch.isdigit()]
                assert not digits, f"{name} {lang} {text!r} digits={digits}"
        assert "%" not in strip.get_text()


def test_parity_state_stance_null_match_hero():
    """RISK_ON, RISK_OFF, and a missing feed: strip copy equals the hero's."""
    cases = {
        "risk_on.json": "RISK_ON",
        "risk_off.json": "RISK_OFF",
        "missing.json": "missing",
    }
    for name, kind in cases.items():
        vm = _load(name)
        strip = _strip(render_strip(vm))
        hero_html = render_hero(vm)
        print(f"PARITY fixture={name} kind={kind}")
        us_state = _hero_us_state(hero_html)
        for market in MARKETS:
            row = _row(strip, market)
            _assert_row_copy(row, kind)
            stance = _hero_stance(hero_html, market)
            got = (
                _lang(row.select_one(".mrs-do"), "l-en"),
                _lang(row.select_one(".mrs-do"), "l-zh"),
            )
            assert got == stance, (market, got, stance)
            state = (
                _lang(row.select_one(".mrs-state"), "l-en"),
                _lang(row.select_one(".mrs-state"), "l-zh"),
            )
            # The US verdict word is the state string. HK/CN hero rows do not
            # print that word (their rail anchors are a different vocabulary);
            # every strip row still uses the same state word as the US hero.
            assert state == us_state, (market, state, us_state)


def test_stance_literals_match_hero_source_bytes():
    hero = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text(encoding="utf-8")
    strip = (TEMPLATES / "_market_regime_strip.html.j2").read_text(encoding="utf-8")
    pairs = _hero_stance_pairs()
    for en, zh in (pairs[4], pairs[5], pairs[6], pairs[7]):
        assert en in hero and zh in hero
        assert en in strip and zh in strip
        assert en.encode("utf-8") in strip.encode("utf-8")


def test_caveat_hover_and_aria_on_hk_cn_only():
    css = (TEMPLATES / "theme.css").read_text(encoding="utf-8")
    assert ".mrs-caveat:hover .mrs-pop" in css
    assert ".mrs-caveat:focus-within .mrs-pop" in css
    strip = _strip(render_strip(_load("risk_on.json")))
    us = _row(strip, "us")
    assert us.select_one("[aria-describedby]") is None
    assert us.select_one(".mrs-pop") is None
    assert us.select_one(".mrs-caveat") is None
    vm = _load("risk_on.json")
    for market in ("hk", "cn"):
        row = _row(strip, market)
        btn = row.select_one(".mrs-caveat-btn")
        assert btn is not None
        assert "aria-describedby" in btn.attrs
        pop = strip.select_one("#" + btn["aria-describedby"])
        assert pop is not None
        assert pop.get("id") == btn["aria-describedby"]
        assert _lang(pop, "l-en") == vm[f"{'hk' if market == 'hk' else 'cn'}_market_state"]["caveat_en"]
        assert _lang(pop, "l-zh") == vm[f"{'hk' if market == 'hk' else 'cn'}_market_state"]["caveat_zh"]
        # The caveat is not glance copy on the name, state, or stance.
        for slot in (".mrs-name", ".mrs-state", ".mrs-do"):
            assert vm[f"{market}_market_state"]["caveat_en"] not in row.select_one(slot).get_text()


def test_no_global_verdict_in_the_strip():
    for name in ("risk_on.json", "risk_off.json", "missing.json", "hk_feed_missing.json"):
        strip = _strip(render_strip(_load(name)))
        glance = BeautifulSoup(str(strip), "html.parser")
        for pop in glance.select(".mrs-pop"):
            pop.decompose()
        text = glance.get_text(" ", strip=True)
        assert "Global" not in text
        assert "全球" not in text
        assert strip.select_one('[data-market="global"]') is None


def test_dom_order_strip_sits_between_cycle_stage_and_market_grid():
    src = (TEMPLATES / "markets.html.j2").read_text(encoding="utf-8")
    stage = src.index('<section class="cyc-stage">')
    banner = src.index('id="regime-prior-banner"')
    close = src.index("</section>", stage)
    include = src.index('{% include "_market_regime_strip.html.j2" %}')
    grid = src.index('<section class="mkt-grid">')
    assert stage < banner < close < include < grid
    html = render_markets(_load("risk_on.json"))
    stage_i = html.index('<section class="cyc-stage">')
    close_i = html.index("</section>", stage_i)
    strip_i = html.index('id="market-regime-strip"')
    grid_i = html.index('<section class="mkt-grid">')
    banner_i = html.index('id="regime-prior-banner"')
    assert stage_i < banner_i < close_i < strip_i < grid_i


def test_designed_null_when_feed_missing():
    strip = _strip(render_strip(_load("hk_feed_missing.json")))
    print("DESIGNED-NULL branch hk=missing us=RISK_ON cn=RISK_OFF")
    _assert_row_copy(_row(strip, "hk"), "missing")
    _assert_row_copy(_row(strip, "us"), "RISK_ON")
    _assert_row_copy(_row(strip, "cn"), "RISK_OFF")
    hk = _row(strip, "hk")
    assert hk.select_one(".mrs-caveat") is None
    us = _row(strip, "us")
    assert us.select_one(".mrs-caveat") is None
    assert "US caveat must not surface" not in strip.get_text()


def test_other_verdict_is_null_state_and_get_ready_stance():
    strip = _strip(render_strip(_load("other_verdict.json")))
    print("OTHER-VERDICT branch us=MIXED hk=BANANA cn=MIXED -> designed-null state, Get ready stance")
    for market in MARKETS:
        row = _row(strip, market)
        _assert_row_copy(row, "other")
        text = row.select_one(".mrs-state").get_text(" ", strip=True)
        assert "Mixed" not in text
        assert "混合" not in text
        assert "Banana" not in text
        assert "香蕉" not in text


def test_unreadable_feed_degrades_to_none(monkeypatch):
    def _lp(root=None, market_key=None):
        if market_key == "hk":
            raise OSError("unreadable")
        return {
            "verdict": "RISK_ON",
            "score": 61,
            "label_en": "Risk-on",
            "label_zh": "风险偏好",
            "caveat_en": "",
            "caveat_zh": "",
        }

    monkeypatch.setattr("engine.market_state.load_persisted", _lp)
    from scripts.build_markets import _persisted_ms_view

    assert _persisted_ms_view("hk") is None
    us = _persisted_ms_view("us")
    assert us is not None
    assert us["verdict"] == "RISK_ON"
    assert "score" in us and "caveat_en" in us and "ms_history" in us
    print("UNREADABLE branch hk=designed-null us=RISK_ON")


def test_live_tree_copy_follows_persisted_verdict():
    from scripts.build_markets import _persisted_ms_view

    views = {
        "us": _persisted_ms_view("us"),
        "hk": _persisted_ms_view("hk"),
        "cn": _persisted_ms_view("cn"),
    }
    vm = {
        "market_state": views["us"],
        "hk_market_state": views["hk"],
        "cn_market_state": views["cn"],
    }
    strip = _strip(render_strip(vm))
    for market, view in views.items():
        kind = _kind(view)
        verdict = view.get("verdict") if isinstance(view, dict) else None
        print(f"LIVE {market} verdict={verdict!r} branch={kind}")
        assert view is not None, market
        _assert_row_copy(_row(strip, market), kind)
        if market == "us":
            assert _row(strip, "us").select_one(".mrs-caveat") is None
        else:
            row = _row(strip, market)
            btn = row.select_one(".mrs-caveat-btn")
            assert btn is not None
            pop = strip.select_one("#" + btn["aria-describedby"])
            assert _lang(pop, "l-en") == (view.get("caveat_en") or "")
            assert _lang(pop, "l-zh") == (view.get("caveat_zh") or "")
            assert (view.get("caveat_en") or "").startswith(
                "Display-only and lighter than the US read:"
            )
    glance = BeautifulSoup(str(strip), "html.parser")
    for pop in glance.select(".mrs-pop"):
        pop.decompose()
    text = glance.get_text(" ", strip=True)
    assert "Global" not in text and "全球" not in text
    # The HK feed caveat quotes 全球. That substring stays inside the popover.
    whole = strip.get_text()
    if "全球" in whole:
        pops = " ".join(pop.get_text() for pop in strip.select(".mrs-pop"))
        assert "全球" in pops
        assert views["hk"]["caveat_zh"] in pops


def test_committed_markets_html_strip_has_no_digits_and_three_rows():
    html = PAGE.read_text(encoding="utf-8")
    strip = _strip(html)
    markets = [row["data-market"] for row in strip.select(".mrs-row")]
    assert markets == ["us", "hk", "cn"]
    for lang in ("l-en", "l-zh"):
        for span in strip.select(f"span.{lang}"):
            digits = [ch for ch in span.get_text() if ch.isdigit()]
            assert not digits, (lang, span.get_text(), digits)
    stage = html.index('<section class="cyc-stage">')
    close = html.index("</section>", stage)
    strip_i = html.index('id="market-regime-strip"')
    grid = html.index('<section class="mkt-grid">')
    banner = html.index('id="regime-prior-banner"')
    assert stage < banner < close < strip_i < grid


def test_header_copy_and_no_rail_markup():
    strip = _strip(render_strip(_load("missing.json")))
    assert _lang(strip.select_one(".mrs-title"), "l-en") == "Risk regime today"
    assert _lang(strip.select_one(".mrs-title"), "l-zh") == "今日风险状态"
    assert _lang(strip.select_one(".mrs-sub"), "l-en") == "Same-day read - not the cycle position above"
    assert _lang(strip.select_one(".mrs-sub"), "l-zh") == "当日判读，不是上方的周期位置"
    assert strip.select_one(".mx-spine-rail") is None
    assert "title=" not in str(strip)


@pytest.fixture
def _restore_bake_side_effects():
    saved: dict[Path, bytes | None] = {}
    for rel in _BAKE_SIDE_EFFECTS:
        path = ROOT / rel
        saved[path] = path.read_bytes() if path.exists() else None
    yield
    for path, blob in saved.items():
        if blob is None:
            if path.exists():
                path.unlink()
        else:
            path.write_bytes(blob)


def test_fresh_render_byte_matches_committed_markets_html(_restore_bake_side_effects):
    before = PAGE.read_bytes()
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.build_markets"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    after = PAGE.read_bytes()
    assert after == before


def test_zh_risk_off_pill_stays_danger_ink_not_the_price_pole():
    """zh swaps --down to green (red = up). Risk-off uses mx-stance--down.

    Leaving that pill on --ink-down paints 风险规避 the same green family as
    风险偏好. The strip is a danger stance, not a price candle, so the zh
    rule must pin it to --ink-act, which does not swap.
    """
    css = (TEMPLATES / "theme.css").read_text(encoding="utf-8")
    marker = 'html[data-lang="zh"] .mrs .mx-stance--down'
    assert marker in css
    rule = css[css.index(marker):css.index("}", css.index(marker))]
    body = rule.split("{", 1)[1]
    assert "--ink-act" in body
    assert "--down" not in body
    site_css = (ROOT / "site" / "theme.css").read_text(encoding="utf-8")
    assert marker in site_css


def test_template_site_sync_passes():
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.check_template_site_sync"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    print(proc.stdout.strip())
