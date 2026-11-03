"""Bonds keeps freshness and calibration language truthful and reader-first."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "bonds.html.j2"
SITE = ROOT / "site" / "bonds.html"


def _src() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def test_bonds_hero_uses_snapshot_not_live_badge() -> None:
    src = _src()
    assert "dtp-chip--live" not in src
    assert ">LIVE<" not in src
    assert "Latest bond snapshot" in src
    assert "最新债券快照" in src
    assert "dtp-chip--snapshot" in src


def test_backtest_summary_uses_reader_language() -> None:
    src = _src()
    assert "{{ t('Measured', '已校准') }}" not in src
    assert "{{ t('Backtested', '历史回测') }}" in src
    assert "Recession-IC" not in src
    assert "衰退IC" not in src
    assert "Historical recession ordering" in src
    assert "历史衰退排序" in src
    assert "top-stress readings were followed by a 10%+ S&P drawdown" in src


def test_jargon_heavy_section_titles_are_plain() -> None:
    src = _src()
    for required in (
        "Credit — early stress signal",
        "Stress & funding · the stock-bond hedge",
        "Rates volatility & funding stress",
        "Global credit cycle — leverage risk (BIS)",
    ):
        assert required in src
    for banned in (
        'Credit — the "smart money" canary',
        "Stress & plumbing",
        "Rates volatility & funding plumbing",
        "crisis early-warning",
    ):
        assert banned not in src


def test_supply_and_timeline_use_product_language_not_scoring_internals() -> None:
    src = _src()
    assert "Supply context only; not scored." not in src
    assert "Supply context only; does not affect the bond-health score." in src
    assert "Daily state changes, debounced to reduce whipsaw. Context only." not in src
    assert "Daily state changes with repeat flips filtered out. Context only." in src


def test_calibration_tooltip_is_plain_and_keeps_audit_detail() -> None:
    src = _src()
    start = src.index("Historical recession ordering")
    snippet = src[start:start + 1200]
    assert "rank correlation" not in snippet
    assert "1.0 = perfect ordering" not in snippet
    assert "sample window" in snippet.lower()
    assert "observations" in snippet.lower()


def test_committed_bonds_page_matches_contract() -> None:
    html = SITE.read_text(encoding="utf-8")
    for required in (
        "Latest bond snapshot",
        "Backtested",
        "Historical recession ordering",
        "Credit — early stress signal",
        "Rates volatility &amp; funding stress",
        "Global credit cycle — leverage risk (BIS)",
        "Supply context only; does not affect the bond-health score.",
    ):
        assert required in html
    for banned in (
        ">LIVE<",
        "Recession-IC",
        "Credit — the &#34;smart money&#34; canary",
        "funding plumbing",
        "crisis early-warning",
        "Supply context only; not scored.",
    ):
        assert banned not in html


def test_committed_bonds_stylesheet_is_fingerprinted() -> None:
    import hashlib
    import re

    from jinja2 import Environment, StrictUndefined

    from scripts.build_bonds import C

    blocks = re.findall(r"<style\b[^>]*>(.*?)</style>", _src(), re.IGNORECASE | re.DOTALL)
    source_css = next(block for block in blocks if ".dtp-chip--snapshot" in block)
    rendered_css = Environment(
        autoescape=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    ).from_string(source_css).render(C=C)
    digest = hashlib.sha256(rendered_css.encode("utf-8")).hexdigest()[:8]

    html = SITE.read_text(encoding="utf-8")
    refs = re.findall(r"assets/css/([0-9a-f]{8})\.css\?v=\1", html)
    assert digest in refs
    css = ROOT / "site" / "assets" / "css" / f"{digest}.css"
    assert css.is_file()
    assert hashlib.sha256(css.read_bytes()).hexdigest()[:8] == digest
    text = css.read_text(encoding="utf-8")
    assert text == rendered_css
    assert ".dtp-chip--snapshot" in text
    assert ".dtp-chip--live" not in text


# --- appended: bonds gauge macro — unavailable score vs numeric zero ---
import re

import pytest
from jinja2 import Environment, StrictUndefined, Undefined

_BONDS_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "bonds.html.j2"


def _gauge_macro_src() -> str:
    src = _BONDS_TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r"\{%\s*-?\s*macro\s+gauge\b.*?\{%\s*-?\s*endmacro\s*-?%\}", src, re.S)
    assert m, "gauge macro not found in templates/bonds.html.j2"
    return m.group(0)


def _render_gauge(score) -> str:
    env = Environment(undefined=StrictUndefined, autoescape=True)
    module = env.from_string(_gauge_macro_src()).module
    return module.gauge(score, "#34d399")


_INVALID_CASES = [
    (None, None),
    (Undefined(name="health_score"), None),
    (True, "True"),
    (False, "False"),
    ("75", "75"),
    ("abc", "abc"),
    (float("nan"), "nan"),
    (float("inf"), "inf"),
    (float("-inf"), "-inf"),
    (-1, "-1"),
    (101, "101"),
]


def _assert_unavailable(html: str) -> None:
    assert "bhg-needle" not in html
    assert "bhg-ptr" not in html
    assert " of 100" not in html
    assert "满分100" not in html
    assert "bhg-track" not in html
    assert "Missing or invalid inputs." in html
    assert "输入缺失或无效。" in html
    assert 'class="faint"' in html
    assert 'class="l-en"' in html and 'class="l-zh"' in html
    assert "Score unavailable" in html
    assert "评分不可用" in html
    assert "<figcaption" in html


@pytest.mark.parametrize(("score", "forbidden"), _INVALID_CASES)
def test_gauge_unavailable_has_no_needle_or_scored_label(score, forbidden):
    html = _render_gauge(score)
    _assert_unavailable(html)
    if forbidden:
        # scrub SVG path geometry so e.g. "75" only means a coerced score
        assert forbidden not in re.sub(r'd="[^"]*"', "", html)


def test_gauge_zero_renders_real_zero():
    html = _render_gauge(0)
    assert 'aria-label="Bond health score 0 of 100"' in html
    assert "bhg-ptr" in html
    assert "债券健康评分 0，满分100" in html
    assert 'transform="rotate(-90.0 70 75)"' in html
    assert "--arc-gap:175.93" in html


def test_gauge_bounds_and_midpoint():
    html = _render_gauge(100)
    assert 'aria-label="Bond health score 100 of 100"' in html
    assert 'transform="rotate(90.0 70 75)"' in html
    assert "--arc-gap:0.0" in html

    html = _render_gauge(75)
    assert 'aria-label="Bond health score 75 of 100"' in html
    assert 'transform="rotate(45.0 70 75)"' in html


@pytest.mark.parametrize("score", [None, 0, 100])
def test_gauge_preserves_builder_missing_and_true_zero(score):
    import pandas as pd
    from scripts.build_bonds import _vm

    snapshot = {"health_score": score, "health_label": None, "pillars": {
        key: {} for key in ("curve", "credit", "real_inflation", "stress", "cross_asset")
    }}
    vm = _vm(snapshot, pd.DataFrame())
    assert vm["health"]["score"] is score
    html = _render_gauge(vm["health"]["score"])
    if score is None:
        _assert_unavailable(html)
    else:
        assert f'aria-label="Bond health score {score} of 100"' in html
        assert f'aria-label="债券健康评分 {score}，满分100"' in html


def test_committed_gauge_matches_current_renderer():
    # The publication's actual score/color remain its own inputs. This check
    # binds just the changed component to the common renderer.
    html = SITE.read_text(encoding="utf-8")
    figures = re.findall(r'<figure class="bhg l-(?:en|zh)".*?</figure>', html, re.S)
    assert len(figures) == 2
    score = int(re.search(r'Bond health score (\d+) of 100', figures[0]).group(1))
    color = re.search(r'--sc:([^;]+)', figures[0]).group(1)
    env = Environment(undefined=StrictUndefined, autoescape=True)
    expected = str(env.from_string(_gauge_macro_src()).module.gauge(score, color))
    assert figures == re.findall(r'<figure class="bhg l-(?:en|zh)".*?</figure>', expected, re.S)


# P12.T2.S1: observation/source clocks survive calendar alignment and rendering.
def _sovereign_row(monkeypatch, observed="2026-09-30", value=3.057, cadence="daily", extra=None):
    import pandas as pd
    from engine import intl_bonds as ib

    spec = next(s for s in ib.ROSTER if s["code"] == ("GB" if cadence == "monthly" else "JP"))
    series = {"y10": pd.Series([value], index=pd.to_datetime([observed]))}
    series.update(extra or {})
    monkeypatch.setattr(ib, "_series", lambda spec, field, frame: series.get(field))
    frame = pd.DataFrame(index=pd.bdate_range("2026-06-01", "2026-10-30"))
    return ib._country_row(spec, frame, 4.94)


def test_sovereign_source_age_uses_unfilled_owner_dates(monkeypatch):
    # Existing daily12/monthly75-day policy; a carried point is not a new observation.
    cases = [("daily", "2026-10-30", False), ("daily", "2026-10-19", False),
             ("daily", "2026-09-30", True), ("monthly", "2026-09-01", False),
             ("monthly", "2026-08-16", False), ("monthly", "2026-08-15", True)]
    for cadence, observed, stale in cases:
        row = _sovereign_row(monkeypatch, observed, cadence=cadence)
        assert row["observed_as_of"] == observed
        assert row["sources"][0]["observed_as_of"] == observed
        assert row["stale"] is stale
        assert row["y10"] == 3.06


def test_sovereign_future_owner_point_cannot_date_the_selected_value(monkeypatch):
    import pandas as pd
    from engine import intl_bonds as ib

    raw = pd.Series([3.057, 9.9], index=pd.to_datetime(["2026-09-30", "2026-11-04"]))
    monkeypatch.setattr(ib, "_series", lambda spec, field, frame: raw if field == "y10" else None)
    frame = pd.DataFrame(index=pd.bdate_range("2026-09-01", "2026-10-30"))
    row = ib._country_row(next(s for s in ib.ROSTER if s["code"] == "JP"), frame, 4.94)
    assert row["observed_as_of"] == "2026-09-30" and row["y10"] == 3.06
    assert row["sources"][0]["observed_as_of"] == "2026-09-30"
    assert row["stale"] is True


def test_sovereign_missing_and_genuine_zero_are_distinct(monkeypatch):
    row = _sovereign_row(monkeypatch, value=0.0)
    assert row["y10"] == 0.0 and row["observed_as_of"] == "2026-09-30"
    assert row["stale"] is True
    assert _sovereign_row(monkeypatch, value=float("nan")) is None


def test_sovereign_comparison_keeps_its_own_observation_and_basis(monkeypatch):
    import pandas as pd

    y2 = pd.Series([2.4], index=pd.to_datetime(["2026-10-15"]))
    row = _sovereign_row(monkeypatch, extra={"y2": y2})
    assert row["slope_basis"] == "2s10s" and row["slope"] == 0.66
    assert [s["observed_as_of"] for s in row["sources"]] == ["2026-09-30", "2026-10-15"]
    assert [s["series_id"] for s in row["sources"]] == ["10年", "2年"]
    assert all(s["source_url"] == "https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv"
               for s in row["sources"])


def test_sovereign_short_rate_fallback_keeps_its_actual_basis(monkeypatch):
    import pandas as pd

    short = pd.Series([4.0], index=pd.to_datetime(["2026-10-01"]))
    row = _sovereign_row(monkeypatch, cadence="monthly", extra={"short": short})
    assert row["slope_basis"] == "10y-3m" and row["slope"] == -0.94
    assert row["sources"][1]["source_url"].endswith("/IR3TIB01GBM156N")
    assert row["sources"][1]["observed_as_of"] == "2026-10-01"


def test_sovereign_missing_source_link_cannot_fabricate_one(monkeypatch):
    from engine import intl_bonds as ib

    monkeypatch.setattr(ib.config, "load", lambda: {"sovereign": {"mof_url": "javascript:bad"}})
    row = _sovereign_row(monkeypatch)
    assert row["sources"][0]["source_url"] is None
    assert row["sources"][0]["observed_as_of"] == "2026-09-30"


def test_sovereign_us_source_uses_the_existing_fred_alias(monkeypatch):
    import pandas as pd
    from engine import intl_bonds as ib

    raw = pd.Series([4.94], index=pd.to_datetime(["2026-10-30"]))
    monkeypatch.setattr(ib, "_series", lambda spec, field, frame: raw if field == "y10" else None)
    frame = pd.DataFrame(index=pd.to_datetime(["2026-10-30"]))
    row = ib._country_row(next(s for s in ib.ROSTER if s["code"] == "US"), frame, 4.94)
    assert row["sources"][0]["source_url"] == "https://fred.stlouisfed.org/series/DGS10"
    assert row["observed_as_of"] == "2026-10-30" and row["stale"] is False


def _render_sovereign_fragment(intl):
    from jinja2 import Environment, StrictUndefined
    from scripts.build_bonds import C

    src = _src()
    macros = src[:src.index("<!DOCTYPE html>")]
    start = src.index('  <section class="landing" id="global-detail"')
    end = src.index("  <div class=\"card\">\n    <h2>{{ t('Euro-area", start)
    return Environment(autoescape=True, undefined=StrictUndefined).from_string(
        macros + src[start:end] + "</section>"
    ).render(C=C, intl=intl, charts={"intl_yields": ""})


def test_sovereign_render_exposes_source_date_currency_and_curve_basis(monkeypatch):
    import pandas as pd

    row = _sovereign_row(monkeypatch, extra={"y2": pd.Series([2.4], index=pd.to_datetime(["2026-10-15"]))})
    intl = {"global": {"direction": "stable", "avg_10y": row["y10"], "avg_10y_chg_63d_bp": 0},
            "us_vs_world": {"us_premium_bp": None}, "countries": [row], "em": None,
            "verdict_en": "Retained fixture", "verdict_zh": "留存测试"}
    html = _render_sovereign_fragment(intl)
    assert 'details class="mx-disc"' in html and "Sources and observation dates" in html
    assert "JPY" in html and "10y−2y" in html and "10年−2年" in html
    assert "2026-09-30" in html and "2026-10-15" in html and "2026-10-30" not in html
    assert "Japan MoF" in html and "日本财务省" in html
    assert 'target="_blank" rel="noopener noreferrer"' in html
    row["sources"][0]["observed_as_of"] = None
    assert "Observation date unavailable" in _render_sovereign_fragment(intl)


def test_sovereign_render_missing_owner_does_not_show_a_zero_assessment():
    html = _render_sovereign_fragment(None)
    assert "Sovereign observations are unavailable" in html and "主权债券观测数据不可用" in html
    assert "0.00%" not in html and 'class="sc-tbl"' not in html



def test_sovereign_summary_does_not_relabel_daily_japan_as_oecd_monthly(monkeypatch):
    from jinja2 import Environment, StrictUndefined
    from scripts.build_bonds import C

    row = _sovereign_row(monkeypatch)
    src = _src()
    start = src.index('  <section class="band" id="world"')
    end = src.index("  </section>", start) + len("  </section>")
    intl = {"global": {"direction": "stable", "avg_10y": row["y10"], "avg_10y_chg_63d_bp": 0},
            "us_vs_world": {"us_premium_bp": None, "premium_direction": None}, "countries": [row], "em": None}
    html = Environment(autoescape=True, undefined=StrictUndefined).from_string(
        src[:src.index("<!DOCTYPE html>")] + src[start:end]
    ).render(C=C, intl=intl, xasset_vm=None)
    assert "Japan" in html and "stale" in html and "过期" in html
    assert "Observation older than its source freshness window" in html
    import re
    country_cell = re.search(r'<td class="cty">.*?</td>', html, re.S).group(0)
    assert "OECD monthly series" not in country_cell and "OECD月度序列" not in country_cell
