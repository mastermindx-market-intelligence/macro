"""Chairman-directed placement: international overview, never stock boards."""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from engine import i18n
from tests.test_unified_dashboard_b1 import _env as hero_env

ROOT = Path(__file__).resolve().parent.parent


def intl_env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    return env


def intl_vm() -> dict:
    rec = {
        "cc": "JP", "name": "Japan", "name_zh": "日本", "flag": "🇯🇵", "region": "Asia",
        "date": "2026-06-16", "quad": "Q1", "quad_name": "Goldilocks",
        "growth_score": 0.7, "inflation_score": -0.5, "confidence": 0.6,
        "liquidity": "neutral", "recession_score": 5, "recession_band": "low",
        "macro": {"policy_rate": 0.5, "yield_10y": 2.6, "curve": 1.4, "real_yield": 0.5,
                  "cpi_yoy": 2.0, "cpi_chg3m": 0.1, "gdp_yoy": 0.3, "unemployment": 2.5,
                  "fx_strength_3m": -0.7, "m2_yoy": 2.0, "fx": 1.5, "realvol": 14.0,
                  "drawdown": 0.0},
        "macro_asof": {"cpi_yoy": "2026-04", "gdp": "2026-03", "unemployment": "2026-04",
                       "yield_10y": "2026-05"},
        "equity": {"price": 23000, "off_52w_high": 0.0, "drawdown_risk": 16,
                   "drawdown_band": "low", "ext_grade": "stretched", "ext_z": 1.6,
                   "bubble_flag": True},
        "data_limited": False, "quad_meaning": ("growth up inflation down", "增长上 通胀下"),
    }
    summary = {"n": 1, "quad_counts": {"Goldilocks": 1}, "dominant_quad": "Goldilocks",
               "recession_watch": 0, "drawdown_watch": 0, "avg_recession": 5}
    latest = {"date": "2026-06-16", "summary": summary, "records": [rec],
              "rankings": {}, "heatmap": [], "periphery": None}
    setups = {"buy": [{"ticker": "4004.T", "name": "Resonac", "flag": "🇯🇵",
                       "sector": "Materials", "dir": "up", "label": "BOUNCE",
                       "state": "BOUNCE", "alpha": 3.0, "price": 18650,
                       "off_high": -4.0, "spark_svg": ""}]}
    board = [{"cc": "KR", "flag": "🇰🇷", "market": "South Korea",
              "sector": "Information Technology", "n": 8, "mom_20d": 21.3,
              "mom_60d": 55.3, "above_trend": True, "rank": 1}]
    return {"latest": latest, "built": "2026-06-16 00:00 UTC", "records": [rec],
            "summary": summary, "rankings": {}, "heatmap": [], "periphery": None,
            "sector_board": board, "setups": setups}


def test_intl_mounts_global_regime_before_existing_economies():
    html = intl_env().get_template("intl.html.j2").render(
        **intl_vm(), mode="macro",
        global_regime_html='<section id="ud-hero">GLOBAL_REGIME_SENTINEL</section>',
    )
    assert html.count('id="ud-hero"') == 1
    assert html.index('id="ud-hero"') < html.index("Cross-country comparison")
    assert "Regime map" in html


def test_stock_boards_do_not_inherit_global_regime():
    html = intl_env().get_template("intl.html.j2").render(
        **intl_vm(), mode="stocks",
        global_regime_html='<section id="ud-hero">GLOBAL_REGIME_SENTINEL</section>',
    )
    assert 'id="ud-hero"' not in html


def test_international_hero_labels_us_reference_and_snapshot():
    vm = dict.fromkeys(("market_state", "stance", "alerts", "event_strip",
        "fear_greed", "fear_euphoria", "froth_fragility", "risk_envelope",
        "ms_history", "hk_market_state", "cn_market_state"))
    vm["latest"] = {}
    html = hero_env().get_template("_unified_dashboard_hero.html.j2").render(
        **vm, ud_international=True)
    assert "US regime score" in html
    assert "not a global composite" in html
    assert '<span class="l-en">Snapshot</span>' in html
    assert '<span class="l-en">Live</span>' not in html


def test_fragment_round_trip_preserves_actual_source_clock(tmp_path):
    from lib.global_regime_fragment import read_global_regime_fragment, write_global_regime_fragment
    import json
    fragment = '<section id="ud-hero" data-regime-scope="us-reference">source reading</section>'
    path = write_global_regime_fragment(tmp_path, fragment, source_asof="2026-09-18")
    assert read_global_regime_fragment(tmp_path) == fragment
    assert json.loads(path.read_text())["source_asof"] == "2026-09-18"


def test_missing_or_corrupt_fragment_never_infers_a_score(tmp_path):
    from lib.global_regime_fragment import RELATIVE_PATH, read_global_regime_fragment
    assert 'data-source-status="unavailable"' in read_global_regime_fragment(tmp_path)
    path = tmp_path / RELATIVE_PATH
    path.parent.mkdir(parents=True)
    path.write_text('{"schema":"global-regime-fragment.v1","html":"broken"}')
    assert 'data-source-status="unavailable"' in read_global_regime_fragment(tmp_path)


def test_fragment_rejects_unqualified_or_duplicate_hero(tmp_path):
    from lib.global_regime_fragment import write_global_regime_fragment
    import pytest
    with pytest.raises(ValueError):
        write_global_regime_fragment(tmp_path, '<section id="ud-hero"></section>')
    with pytest.raises(ValueError):
        write_global_regime_fragment(tmp_path, '<section id="ud-hero"></section>' * 2)


def test_committed_intl_projection_contains_exact_shared_fragment():
    from pathlib import Path
    from lib.global_regime_fragment import read_global_regime_fragment
    site = Path(__file__).resolve().parent.parent / "site"
    html = (site / "intl.html").read_text()
    fragment = read_global_regime_fragment(site)
    assert 'data-source-status="unavailable"' not in fragment
    assert fragment in html
    assert html.count('id="ud-hero"') == 1
    assert 'id="ud-hero"' not in (site / "intl_stocks.html").read_text()


def test_both_builders_keep_the_shared_presentation_handoff():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    producer = (root / "scripts/build_site.py").read_text()
    consumer = (root / "scripts/build_intl.py").read_text()
    assert "write_global_regime_fragment(" in producer
    assert "ud_international=True" in producer
    assert 'vm["global_regime_html"] = read_global_regime_fragment(site)' in consumer


def test_intl_uses_the_same_governed_hero_styles_and_locale_rules():
    from pathlib import Path
    css = (Path(__file__).resolve().parent.parent / "templates/theme.css").read_text()
    for selector in (".ud-hero-grid", ".ud-watch-item-head.l-en", ".ud-watch-item-body.l-zh"):
        assert "body.page-intl " + selector in css
        assert "body.page-macro " + selector in css
    html = intl_env().get_template("intl.html.j2").render(**intl_vm(), mode="macro")
    assert '<body class="page-intl">' in html
