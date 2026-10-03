"""Page child for MO-PAID-006: render the rights-gated dossier plane on the
five country pages of templates/international_macro.html.j2.

Schema: intl_country_dossier.v1 (engine.international_macro_dashboard
:32-297). The plane already exists in the view; this child draws it as an
"Official policy statements" card INSIDE the verified-policy-calendar
section, and pins the rendering with 12 tests:

  1  EZ covered: headline link + date + publisher + rights basis
  2  Item cap is five (template-only)
  3  Leadership literal is printed from the plane (D18 null)
  4  JP / KR / IN render the no_coverage fallback (parametrized)
  5  source_outage is plain-words, no raw slugs / states
  6  UNVERIFIED_EXCLUDED sources never render (template-only)
  7  GB stance is a non-authoritative read; no chip when authoritative or
     when stance is None (D52)
  8  Stance block only on GB (template-only)
  9  No `title=` attribute anywhere in the dossier slice
  10 ZH parity: l-en and l-zh spans balance
  11 Headline is HTML-escaped
  12 europe-news quote-link is conditional on the panel AND on EZ

The render is in-process (no `scripts/build_international_macro.py`, which
writes `site/` and `data/` and would truncate committed artifacts on this
sparse tree). Jinja environment is the EXACT same as
scripts/build_international_macro.py :97-102.
"""
from __future__ import annotations

import datetime
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jinja2 import Environment, FileSystemLoader

from engine.international_macro_dashboard import (  # noqa: E402
    DOSSIER_LEADERSHIP_NULL,
    REGIONS,
    build_country_view,
    validate_dossier,
    validate_view,
)


# --------------------------------------------------------------------------- #
# Render helpers
# --------------------------------------------------------------------------- #
def _render(view: dict, **extra) -> str:
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("international_macro.html.j2")
    return template.render(
        D=view,
        RADAR=extra.pop("RADAR", None),
        europe_news=extra.pop("europe_news", None),
        europe_news_items=extra.pop("europe_news_items", None),
        **extra,
    )


def _slice(html: str) -> str:
    assert 'id="official-statements"' in html, (
        "official-statements anchor missing — dossier plane did not render"
    )
    anchor = html.index('id="official-statements"')
    # Back up to the opening `<article` so the full opening tag is included
    # (and so stripping tags with `<[^>]+>` cleans the article-open fragment).
    start = html.rfind('<article', 0, anchor + 1)
    end = html.index('</article>', anchor) + len('</article>')
    return html[start:end]


# --------------------------------------------------------------------------- #
# Base view builder (mirrors tests/test_international_macro_dossier.py:52-118)
# --------------------------------------------------------------------------- #
def _record(cc: str) -> dict:
    spec = REGIONS[cc]
    return {
        "cc": cc,
        "name": {
            "JP": "Japan",
            "KR": "South Korea",
            "EZ": "Euro Area",
            "GB": "United Kingdom",
            "IN": "India",
        }[cc],
        "name_zh": spec.scope_zh[:2],
        "flag": "🌐",
        "date": "2026-10-02",
        "quad": "Q2",
        "quad_name": "Reflation",
        "growth_score": 0.4,
        "inflation_score": 0.25,
        "confidence": 0.55,
        "liquidity": "neutral",
        "recession_score": 20.0,
        "recession_band": "low",
        "data_limited": False,
        "macro": {
            "cpi_yoy": 2.4,
            "gdp_yoy": 1.8,
            "unemployment": 4.1,
            "yield_10y": 3.2,
            "policy_rate": 2.5,
            "curve": 0.7,
            "fx": 100.25,
            "fx_strength_3m": -1.2,
            "drawdown": -5.0,
            "realvol": 18.0,
        },
        "macro_asof": {
            "cpi_yoy": "2026-06",
            "gdp": "2026-04",
            "unemployment": "2026-06",
            "yield_10y": "2026-07",
        },
        "equity": {"drawdown_risk": 32.0},
        "risk_radar": {
            "state": "caution",
            "top_score": 62,
            "dominant_label_en": "Rate shock",
            "dominant_label_zh": "利率冲击",
            "drawdown_prob": {
                "h21": 0.21,
                "measure": ">=5% pullback within 21 business days",
            },
            "scares": [],
        },
    }


_TODAY = datetime.date(2026, 10, 2)


def _view(cc: str) -> dict:
    view = build_country_view(_record(cc), today=_TODAY)
    validate_view(view)
    return view


# --------------------------------------------------------------------------- #
# Fixture items (validate_dossier compliant)
# --------------------------------------------------------------------------- #
_EC_ITEM_1 = {
    "publisher": "European Commission",
    "source_key": "ec_presscorner",
    "jurisdiction": "EU",
    "title": "Commission adopts 2027 work programme",
    "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1",
    "published": "2026-09-30T09:00:00+00:00",
    "known_at": "2026-09-30T09:05:00+00:00",
    "rights_basis": "CC BY 4.0 (Commission Decision 2011/833/EU) — reuse permitted with attribution",
    "rights_state": "VERIFIED_PUBLIC_REUSE",
}

_EC_ITEM_2 = {
    "publisher": "European Commission",
    "source_key": "ec_presscorner",
    "jurisdiction": "EU",
    "title": "Commission statement on the autumn economic outlook",
    "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_2",
    "published": "2026-09-28T11:00:00+00:00",
    "known_at": "2026-09-28T11:03:00+00:00",
    "rights_basis": "CC BY 4.0 (Commission Decision 2011/833/EU) — reuse permitted with attribution",
    "rights_state": "VERIFIED_PUBLIC_REUSE",
}

_BOE_ITEM = {
    "publisher": "Bank of England",
    "source_key": "boe_news",
    "jurisdiction": "UK",
    "title": "Monetary Policy Summary, October 2026",
    "url": "https://www.bankofengland.co.uk/news/monetary-policy-summary-oct-2026",
    "published": "2026-09-25T10:00:00+00:00",
    "known_at": "2026-09-25T10:01:00+00:00",
    "rights_basis": "Open Government Licence v3.0 — reuse permitted with attribution",
    "rights_state": "VERIFIED_PUBLIC_REUSE",
}


def _covered_ez() -> dict:
    return {
        "schema": "intl_country_dossier.v1",
        "state": "covered",
        "items": [_EC_ITEM_1, _EC_ITEM_2],
        "stance": None,
        "leadership": DOSSIER_LEADERSHIP_NULL,
    }


def _covered_gb() -> dict:
    return {
        "schema": "intl_country_dossier.v1",
        "state": "covered",
        "items": [_BOE_ITEM],
        "stance": {
            "label": "restrictive",
            "provider_label": "HM Treasury",
            "authoritative": False,
        },
        "leadership": DOSSIER_LEADERSHIP_NULL,
    }


def _no_coverage() -> dict:
    return {
        "schema": "intl_country_dossier.v1",
        "state": "no_coverage",
        "items": [],
        "stance": None,
        "leadership": DOSSIER_LEADERSHIP_NULL,
    }


def _source_outage() -> dict:
    return {
        "schema": "intl_country_dossier.v1",
        "state": "source_outage",
        "items": [],
        "stance": None,
        "leadership": DOSSIER_LEADERSHIP_NULL,
    }


# --------------------------------------------------------------------------- #
# Test 1 — EZ covered renders headline + link + date + publisher + rights
# --------------------------------------------------------------------------- #
def test_covered_ez_renders_headline_link_date_publisher_rights() -> None:
    view = _view("EZ")
    view["dossier"] = _covered_ez()
    validate_view(view)
    html = _render(view)
    slice_ = _slice(html)

    assert 'Commission adopts 2027 work programme' in slice_
    assert 'Commission statement on the autumn economic outlook' in slice_
    assert 'href="https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1"' in slice_
    assert 'target="_blank" rel="noopener"' in slice_
    assert "2026-09-30" in slice_
    assert "European Commission" in slice_
    assert "欧盟委员会" in slice_
    assert "CC BY 4.0 (Commission Decision 2011/833/EU)" in slice_
    assert 'data-dossier-state="covered"' in slice_
    assert "imd-dossier-asof" in slice_

    # Visible text must NOT carry any raw state slug or rights token.
    visible = re.sub(r"<[^>]+>", " ", slice_)
    for token in ("source_outage", "no_coverage", "VERIFIED_PUBLIC_REUSE",
                  "ec_presscorner", "falsifier", "refuted"):
        assert token not in visible, (token, visible[:400])


# --------------------------------------------------------------------------- #
# Test 2 — item cap is five (template-only)
# --------------------------------------------------------------------------- #
def test_item_cap_is_five() -> None:
    view = _view("EZ")
    seven = [_EC_ITEM_1.copy() for _ in range(7)]
    for i, it in enumerate(seven):
        seven[i] = dict(it)
        seven[i]["url"] = f"https://ec.europa.eu/commission/presscorner/detail/en/ip_26_{i}"
        seven[i]["published"] = f"2026-09-{30 - i:02d}T09:00:00+00:00"
    view["dossier"] = {
        "schema": "intl_country_dossier.v1",
        "state": "covered",
        "items": seven,
        "stance": None,
        "leadership": DOSSIER_LEADERSHIP_NULL,
    }
    # NOTE: not validating — seven items violates the cap-by-construction
    # rule inside validate_dossier. This is a template-only test.
    html = _render(view)
    slice_ = _slice(html)
    assert slice_.count('class="imd-dossier-item"') == 5


# --------------------------------------------------------------------------- #
# Test 3 — leadership literal printed from the plane (D18 null)
# --------------------------------------------------------------------------- #
def test_leadership_literal_is_printed_from_the_plane() -> None:
    view = _view("EZ")
    view["dossier"] = _covered_ez()
    html = _render(view)
    slice_ = _slice(html)

    # Null branch (D18 null sentinel): the EN span prints the literal once,
    # the ZH span prints 暂无获准转载的来源 exactly once. The equality check
    # added in D55(5) routes the null string to the canonical ZH phrase.
    expected_phrase = "Leadership statements: " + DOSSIER_LEADERSHIP_NULL + "."
    assert slice_.count(expected_phrase) == 1
    assert slice_.count("暂无获准转载的来源") == 1

    # Non-vacuity: a non-null leadership must appear in BOTH the .l-en and
    # the .l-zh span (count == 2) and the null phrase must not appear at all.
    view["dossier"]["leadership"] = "SENTINEL-LEAD"
    html2 = _render(view)
    slice2 = _slice(html2)
    assert slice2.count("SENTINEL-LEAD") == 2
    assert slice2.count("暂无获准转载的来源") == 0
    assert "Leadership statements: no rights-cleared source." not in slice2


# --------------------------------------------------------------------------- #
# Test 4 — JP / KR / IN render the no_coverage fallback
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("cc", ["JP", "KR", "IN"])
def test_no_coverage_for_jp_kr_in(cc: str) -> None:
    view = _view(cc)
    view["dossier"] = _no_coverage()
    validate_view(view)
    html = _render(view)
    slice_ = _slice(html)

    assert 'data-dossier-state="no_coverage"' in slice_
    assert "No official statements shown for this market yet." in slice_
    assert "本市场暂未展示官方声明。" in slice_
    assert "We have no source here we are cleared to republish." in slice_
    assert slice_.count('class="imd-dossier-item"') == 0
    assert "imd-dossier-read" not in slice_
    assert "Leadership statements: " + DOSSIER_LEADERSHIP_NULL + "." in slice_


# --------------------------------------------------------------------------- #
# Test 5 — source_outage: plain words, no raw slugs / states / rights tokens
# --------------------------------------------------------------------------- #
def test_source_outage_plain_words_no_raw_slugs() -> None:
    view = _view("EZ")
    view["dossier"] = _source_outage()
    html = _render(view)
    slice_ = _slice(html)

    assert "Official statements could not be loaded this time." in slice_
    assert "本次未能载入官方声明。" in slice_
    assert "mx-empty" not in slice_

    visible = re.sub(r"<[^>]+>", " ", slice_)
    for token in ("source_outage", "no_coverage", "covered",
                  "VERIFIED_PUBLIC_REUSE", "ec_presscorner", "boe_news",
                  "falsifier", "refuted"):
        assert token not in visible, (token, visible[:400])


# --------------------------------------------------------------------------- #
# Test 6 — UNVERIFIED_EXCLUDED sources never render (template-only)
# --------------------------------------------------------------------------- #
def test_unverified_excluded_sources_never_render() -> None:
    view = _view("EZ")
    items = [
        dict(_EC_ITEM_1, title="EC verified title", url="https://ec.europa.eu/commission/presscorner/detail/en/ip_26_eu"),
        {
            "publisher": "European Central Bank",
            "source_key": "ecb_press",
            "jurisdiction": "EU",
            "title": "ECB excluded headline",
            "url": "https://www.ecb.europa.eu/press/pr/date/2026/html/ecb.pr260101.en.html",
            "published": "2026-09-29T10:00:00+00:00",
            "known_at": "2026-09-29T10:01:00+00:00",
            "rights_basis": "© ECB, all rights reserved",
            "rights_state": "UNVERIFIED_EXCLUDED",
        },
        {
            "publisher": "Council of the EU",
            "source_key": "council_eu",
            "jurisdiction": "EU",
            "title": "Council excluded headline",
            "url": "https://www.consilium.europa.eu/en/press/press-releases/2026/09/26/",
            "published": "2026-09-28T10:00:00+00:00",
            "known_at": "2026-09-28T10:01:00+00:00",
            "rights_basis": "© Council, all rights reserved",
            "rights_state": "UNVERIFIED_EXCLUDED",
        },
        {
            "publisher": "EU Publications Office",
            "source_key": "eurlex_oj_l",
            "jurisdiction": "EU",
            "title": "OJ excluded headline",
            "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32026L0001",
            "published": "2026-09-27T10:00:00+00:00",
            "known_at": "2026-09-27T10:01:00+00:00",
            "rights_basis": "© EU, all rights reserved",
            "rights_state": "UNVERIFIED_EXCLUDED",
        },
    ]
    view["dossier"] = {
        "schema": "intl_country_dossier.v1",
        "state": "covered",
        "items": items,
        "stance": None,
        "leadership": DOSSIER_LEADERSHIP_NULL,
    }
    # The mix above fails validate_dossier (UNVERIFIED item is rejected) but
    # validate_dossier is the engine contract; the template's job is to FILTER
    # items by rights_state before rendering. We do NOT call validate_dossier
    # here because that would reject the fixture; we render the view directly
    # and check the slice.
    html = _render(view)
    slice_ = _slice(html)

    assert "EC verified title" in slice_
    for banned in ("ECB excluded headline", "Council excluded headline",
                   "OJ excluded headline", "European Central Bank",
                   "Council of the EU", "EU Publications Office",
                   "ecb.europa.eu", "consilium.europa.eu",
                   "eur-lex.europa.eu"):
        assert banned not in slice_, (banned, slice_[:600])


# --------------------------------------------------------------------------- #
# Test 7 — GB stance: non-authoritative read; chip / chip-less / no-stance
# --------------------------------------------------------------------------- #
def test_gb_stance_is_a_non_authoritative_read() -> None:
    view = _view("GB")

    # (a) non-authoritative restrictive stance → chip + "Reads as restrictive" + OGL
    view["dossier"] = _covered_gb()
    html = _render(view)
    slice_ = _slice(html)
    assert "Reads as restrictive" in slice_
    assert "读作偏收紧" in slice_
    assert "context, not a verdict" in slice_
    assert "Open Government Licence v3.0" in slice_
    assert 'data-dossier-stance="restrictive"' in slice_
    assert "imd-dossier-chip--warn" in slice_

    # (b) authoritative=True → no chip; stance is "none" in the data attr
    view["dossier"] = {
        "schema": "intl_country_dossier.v1",
        "state": "covered",
        "items": [_BOE_ITEM],
        "stance": {
            "label": "restrictive",
            "provider_label": "HM Treasury",
            "authoritative": True,
        },
        "leadership": DOSSIER_LEADERSHIP_NULL,
    }
    # (authoritative=True is rejected by validate_dossier; render anyway
    # because the template must NEVER paint a chip for that case.)
    html = _render(view)
    slice_ = _slice(html)
    assert "imd-dossier-chip" not in slice_
    assert 'data-dossier-stance="none"' in slice_

    # (c) stance=None → "No plain-word read" + data-dossier-stance="none"
    view["dossier"] = {
        "schema": "intl_country_dossier.v1",
        "state": "covered",
        "items": [_BOE_ITEM],
        "stance": None,
        "leadership": DOSSIER_LEADERSHIP_NULL,
    }
    html = _render(view)
    slice_ = _slice(html)
    assert "No plain-word read of HM Treasury announcements right now." in slice_
    assert "目前没有英国财政部公告的平实解读。" in slice_
    assert 'data-dossier-stance="none"' in slice_


# --------------------------------------------------------------------------- #
# Test 8 — stance block only on GB (template-only)
# --------------------------------------------------------------------------- #
def test_stance_block_only_on_gb() -> None:
    view = _view("EZ")
    view["dossier"] = {
        "schema": "intl_country_dossier.v1",
        "state": "covered",
        "items": [_EC_ITEM_1],
        "stance": {
            "label": "restrictive",
            "provider_label": "HM Treasury",
            "authoritative": False,
        },
        "leadership": DOSSIER_LEADERSHIP_NULL,
    }
    html = _render(view)
    slice_ = _slice(html)
    assert "imd-dossier-read" not in slice_


# --------------------------------------------------------------------------- #
# Test 9 — no `title=` attribute in the dossier slice
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("fixture_id", ["ez_covered", "gb_stance", "jp_no"])
def test_no_title_attributes_in_dossier(fixture_id: str) -> None:
    if fixture_id == "ez_covered":
        view = _view("EZ"); view["dossier"] = _covered_ez()
    elif fixture_id == "gb_stance":
        view = _view("GB"); view["dossier"] = _covered_gb()
    else:
        view = _view("JP"); view["dossier"] = _no_coverage()
    html = _render(view)
    slice_ = _slice(html)
    assert 'title="' not in slice_, slice_[:400]


# --------------------------------------------------------------------------- #
# Test 10 — ZH parity: visible ZH text contains no Latin run of >=3 letters
# outside the rights-line allow-list (D55(6)).
# --------------------------------------------------------------------------- #

# D55(6): allow-listed Latin tokens that the rights line carries by design.
# The rights_basis first segment renders outside `.l-en` / `lang="en"` contexts
# (the `.imd-dossier-rights` span itself is not bilingual), so legitimate Latin
# from the rights line is the only Latin that may survive in ZH-visible text.
_ZH_PARITY_ALLOW_LIST = frozenset({
    "CC", "BY", "Commission", "Decision", "EU", "Open", "Government",
    "Licence", "OGL", "v3",
})


class _ZhTextExtractor(HTMLParser):
    """Collect visible text that is OUTSIDE `.l-en` spans and `lang="en"`
    elements. The dossier template's bilingual macro `t(en, zh)` wraps every
    translated string in a pair `<span class="l-en">…</span><span
    class="l-zh">…</span>`; the headline anchor additionally declares
    `lang="en"`. The ZH-visible text is what remains once those wrappers are
    stripped. Implemented as a small state machine (no bs4 dependency).
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._en_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_d = dict(attrs)
        cls = (attr_d.get("class") or "").split()
        lang = attr_d.get("lang")
        if "l-en" in cls or lang == "en":
            self._en_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._en_depth > 0:
            self._en_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._en_depth == 0:
            self._chunks.append(data)


def _zh_visible_text(slice_html: str) -> str:
    parser = _ZhTextExtractor()
    parser.feed(slice_html)
    return "".join(parser._chunks)


def _assert_zh_only_letters_or_allow_list(slice_html: str) -> None:
    text = _zh_visible_text(slice_html)
    # Strip the rights-line allow-list (longest first so "Open" doesn't match
    # the start of "OpenX"). Word-bounded so "CC" inside "ECCHO" survives.
    for token in sorted(_ZH_PARITY_ALLOW_LIST, key=len, reverse=True):
        text = re.sub(r"\b" + re.escape(token) + r"\b", " ", text)
    leaked = re.findall(r"[A-Za-z]{3,}", text)
    assert not leaked, (
        f"Latin run leaked into ZH-visible text: {leaked!r}; "
        f"text-after-strip={text!r}"
    )


@pytest.mark.parametrize("fixture_id", ["ez_covered", "gb_stance", "jp_no", "outage"])
def test_zh_parity(fixture_id: str) -> None:
    if fixture_id == "ez_covered":
        view = _view("EZ"); view["dossier"] = _covered_ez()
    elif fixture_id == "gb_stance":
        view = _view("GB"); view["dossier"] = _covered_gb()
    elif fixture_id == "jp_no":
        view = _view("JP"); view["dossier"] = _no_coverage()
    else:
        view = _view("EZ"); view["dossier"] = _source_outage()
    html = _render(view)
    slice_ = _slice(html)
    _assert_zh_only_letters_or_allow_list(slice_)


# --------------------------------------------------------------------------- #
# Test 11 — headline is HTML-escaped
# --------------------------------------------------------------------------- #
def test_headline_is_html_escaped() -> None:
    view = _view("EZ")
    item = dict(_EC_ITEM_1, title="A & B <script>x</script>")
    view["dossier"] = {
        "schema": "intl_country_dossier.v1",
        "state": "covered",
        "items": [item],
        "stance": None,
        "leadership": DOSSIER_LEADERSHIP_NULL,
    }
    validate_dossier(view["dossier"])
    html = _render(view)
    slice_ = _slice(html)
    assert "&lt;script&gt;" in slice_
    assert "A &amp; B" in slice_
    assert "<script>x" not in slice_


# --------------------------------------------------------------------------- #
# Test 12 — europe-news quote-link is conditional on the panel AND on EZ
# --------------------------------------------------------------------------- #
def test_europe_news_quote_link_only_with_panel() -> None:
    panel = {"items": []}  # empty item list is enough to render the section
    # (a) EZ with europe_news stub → link present
    view = _view("EZ")
    view["dossier"] = _covered_ez()
    html = _render(view, europe_news=panel, europe_news_items=panel["items"])
    slice_ = _slice(html)
    assert 'href="#europe-news"' in slice_

    # (b) EZ with europe_news=None → link absent
    html2 = _render(view)
    slice2 = _slice(html2)
    assert 'href="#europe-news"' not in slice2

    # (c) GB with the same stub → link absent (the link is EZ-only)
    view_gb = _view("GB")
    view_gb["dossier"] = _covered_gb()
    html3 = _render(view_gb, europe_news=panel, europe_news_items=panel["items"])
    slice3 = _slice(html3)
    assert 'href="#europe-news"' not in slice3


# --------------------------------------------------------------------------- #
# Test 13 — engine path actually renders (D55(4))
# --------------------------------------------------------------------------- #
def test_engine_items_render_through_the_real_view(monkeypatch) -> None:
    """D55(4): the dossier plane must render items the engine actually reads.
    A real engine path (build_country_view → _build_dossier → _read_dossier_items
    → europe_news_intel.read_events) is monkeypatched to return a one-row
    frame; the page slice must show that row verbatim, with HTML-escape in the
    title, the published date sliced to YYYY-MM-DD, the rights-basis first
    segment rendered, and the source key in the data attribute.
    """
    import pandas as pd
    from engine import europe_news_intel

    one_row = pd.DataFrame([{
        "source": "ec_presscorner",
        "seendate": "2026-10-01T09:30:00+00:00",
        "title": "SENTINEL-EC-HEADLINE-7731 & co",
        "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_sentinel",
        "first_seen_utc": "2026-10-01T09:31:00+00:00",
        "rights_basis": (
            "CC BY 4.0 (Commission Decision 2011/833/EU) — "
            "reuse permitted with attribution"
        ),
    }])
    monkeypatch.setattr(europe_news_intel, "read_events", lambda asof=None: one_row)

    view = build_country_view(_record("EZ"), today=_TODAY)
    validate_view(view)
    html = _render(view)
    slice_ = _slice(html)

    assert 'data-dossier-state="covered"' in slice_
    assert "SENTINEL-EC-HEADLINE-7731" in slice_
    assert "&amp; co" in slice_  # HTML-escape path exercised
    assert '<time class="imd-dossier-date"' in slice_
    assert "2026-10-01" in slice_
    # data-rights-basis carries a non-empty value; its first segment (before
    # ' — ') must appear in the visible rights line.
    data_rights_basis = slice_.split('data-rights-basis="', 1)[1].split('"', 1)[0]
    assert data_rights_basis
    assert data_rights_basis.split(" — ")[0] in slice_
    assert 'data-source-key="ec_presscorner"' in slice_
