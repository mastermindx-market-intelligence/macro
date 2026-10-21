"""The desk price-source date line in the HK / Canada basket footers (W28B SPEC 3, seat-amended).

theme_intel.observation is {"effective_as_of": ..., "status": "legacy_source_without_receipt"}
on both committed markets and nothing printed it. These tests render the REAL templates and
pin the footer line built from scripts/_baskets_themeobs.observation_line: the legacy status
dates the source and says no observation receipt is on file; any other status dates the source
only; a half receipt renders nothing. The internal status token is never shown to the reader.

Render-only by law: pytest + jinja2 + stdlib + scripts._baskets_themeobs only; no builder is
imported or even named in this file, no engine.*/lib.* module, no pandas/numpy. The helper
import is lazy (inside _to()) so the RED-first run fails on assertions, not on collection.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent

HK_TI = {
    "observation": {"effective_as_of": "2026-10-16", "status": "legacy_source_without_receipt"},
    "themes": [
        {"id": "hk_industrials", "name": "HK Industrials", "name_zh": "港股工业", "score": 42.4,
         "reco_en": "HOLD", "reco_zh": "持有",
         "observation": {"status": "partial", "configured_n": 9, "observed_n": 7,
                                  "coverage": 0.7778,
                         "min_members": 3, "min_coverage": 0.6, "missing_columns": [],
                         "missing_at_asof": ["1766.HK"], "effective_as_of": "2026-10-16"}},
        {"id": "hk_property", "name": "HK Property", "name_zh": "港股地产", "score": 44.0,
         "reco_en": "HOLD", "reco_zh": "持有",
         "observation": {"status": "complete", "configured_n": 15, "observed_n": 15,
                                  "coverage": 1.0,
                         "min_members": 3, "min_coverage": 0.6, "missing_columns": [],
                         "missing_at_asof": [], "effective_as_of": "2026-10-16"}}],
    "observation_refusals": [
        {"basket_id": "hk_pair",
         "observation": {"status": "complete", "configured_n": 2, "observed_n": 2, "coverage": 1.0,
                         "min_members": 3, "min_coverage": 0.6, "missing_columns": [],
                         "missing_at_asof": [], "effective_as_of": "2026-10-16"}}]}
HK_BASKETS = [{"id": "hk_pair", "name": "HK Pair", "name_zh": "港股双名"}]
CA_TI = {
    "observation": {"effective_as_of": "2026-10-14", "status": "legacy_source_without_receipt"},
    "themes": [
        {"id": "ca_pipelines", "name": "Pipelines & Midstream", "name_zh": "管道与中游", "score": 53,
         "reco_en": "HOLD", "reco_zh": "持有",
         "observation": {"status": "partial", "configured_n": 9, "observed_n": 8,
                                  "coverage": 0.8889,
                         "min_members": 3, "min_coverage": 0.6, "missing_columns": ["SES.TO"],
                         "missing_at_asof": [], "effective_as_of": "2026-10-14"}}],
    "observation_refusals": [
        {"basket_id": "ca_lonely",
         "observation": {"status": "insufficient", "configured_n": 4, "observed_n": 2,
                         "coverage": 0.5, "min_members": 3, "min_coverage": 0.6,
                         "missing_columns": ["AAA.TO"], "missing_at_asof": ["BBB.TO"],
                         "effective_as_of": "2026-10-14"}}]}

_BANNED_EN = ("validated", "live", "forecast", "falsifier", "probability", "bullish",
              "bearish", "buy", "sell", "episode", "independent", "current", "latest",
              "month", "z-score", "percentile rank", "refuted")
_BANNED_ZH = ("实时", "申报", "证伪", "已验证", "概率", "独立", "最新", "当前", "月")


def _to():
    from scripts import _baskets_themeobs as TO
    return TO


def _render(tpl: str, **extra) -> str:
    """The builders' own env (autoescape=True) + exactly the context their render calls pass."""
    ctx = {"baskets_json": "{}", "chart_json": "[]", "ignition_json": "{}",
           "provenance_json": "{}", "freshness_json": "{}", "radar_json": "{}",
           "bench_en": "Hang Seng", "bench_zh": "恒生指数", "generated_utc": "TEST"}
    ctx.update(extra)
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    return env.get_template(tpl).render(**ctx)


def _banned_hits(text: str) -> list[str]:
    hits = [w for w in _BANNED_EN if re.search(r"\b" + re.escape(w) + r"\b", text, re.I)]
    return hits + [w for w in _BANNED_ZH if w in text]


def _footer(html: str) -> str:
    return html[html.index("<footer>"):html.index("</footer>")]


_LEGACY_HK = ('<span class="l-en">Theme desk prices dated 2026-10-16: no observation receipt '
              'on file.</span><span class="l-zh">主题台价格日期 2026-10-16：无存档的观测回执。</span>')
_LEGACY_CA = ('<span class="l-en">Theme desk prices dated 2026-10-14: no observation receipt '
              'on file.</span><span class="l-zh">主题台价格日期 2026-10-14：无存档的观测回执。</span>')
_DATE_ONLY_CA = ('<span class="l-en">Theme desk prices dated 2026-10-14.</span>'
                 '<span class="l-zh">主题台价格日期 2026-10-14。</span>')


def test_hk_footer_dates_the_source_and_says_no_receipt():
    TO = _to()
    html = _render("baskets_hk.html.j2", themeobs=TO.themeobs_rows(HK_TI, HK_BASKETS),
                   theme_source=TO.observation_line(HK_TI))
    assert html.count(_LEGACY_HK) == 1, html.count(_LEGACY_HK)
    assert "legacy_source_without_receipt" not in html


def test_canada_footer_same_contract():
    TO = _to()
    html = _render("baskets_canada.html.j2", themeobs=TO.themeobs_rows(CA_TI),
                   theme_source=TO.observation_line(CA_TI))
    assert html.count(_LEGACY_CA) == 1, html.count(_LEGACY_CA)
    assert "legacy_source_without_receipt" not in html


def test_other_status_prints_the_date_only():
    for status in ("partial", "complete", "something_new"):
        html = _render("baskets_canada.html.j2", themeobs=[],
                       theme_source={"effective_as_of": "2026-10-14", "status": status})
        assert html.count(_DATE_ONLY_CA) == 1, (status, html.count(_DATE_ONLY_CA))
        assert "receipt on file" not in html, status
        assert "legacy_source_without_receipt" not in html, status


def test_absent_or_half_source_renders_nothing():
    for tpl in ("baskets_hk.html.j2", "baskets_canada.html.j2"):
        bare = _render(tpl)
        assert "Theme desk prices" not in bare
        for src in ({}, {"status": "x"}, {"effective_as_of": "2026-10-14"}):
            html = _render(tpl, theme_source=src)
            assert html == bare, (tpl, src)
            assert "Theme desk prices" not in html, (tpl, src)


def test_line_sits_between_the_disclaimer_and_generated():
    TO = _to()
    for tpl, ti in (("baskets_hk.html.j2", HK_TI), ("baskets_canada.html.j2", CA_TI)):
        foot = _footer(_render(tpl, themeobs=TO.themeobs_rows(ti),
                               theme_source=TO.observation_line(ti)))
        a = foot.index("Informational only")
        b = foot.index("Theme desk prices dated")
        c = foot.index('<span class="l-en">Generated</span>')
        assert a < b < c, (tpl, a, b, c)


def test_zh_line_says_receipt_and_never_filing_or_realtime():
    TO = _to()
    html = _render("baskets_hk.html.j2", themeobs=TO.themeobs_rows(HK_TI, HK_BASKETS),
                   theme_source=TO.observation_line(HK_TI))
    m = re.search(r'<span class="l-en">Theme desk prices dated[^<]*</span>'
                  r'<span class="l-zh">([^<]*)</span>', html)
    assert m, html.count("Theme desk prices")
    assert "回执" in m.group(1) and "申报" not in m.group(1) and "实时" not in m.group(1)
    line = m.group(0)
    text = re.sub(r"<[^>]*>", " ", line)
    assert _banned_hits(text) == [], _banned_hits(text)


def test_helper_feeds_the_footer():
    TO = _to()
    lit = {"effective_as_of": "2026-10-16", "status": "legacy_source_without_receipt"}
    for tpl in ("baskets_hk.html.j2", "baskets_canada.html.j2"):
        assert (_render(tpl, theme_source=TO.observation_line(HK_TI))
                == _render(tpl, theme_source=lit)), tpl
