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
import hashlib
import json
import os
import re
import shutil
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

# D55(6) revised (R3): the `.imd-dossier-rights` span carries the rights-basis
# legal identifier UNTRANSLATED BY DESIGN — its Latin tokens (CC, BY, Commission,
# Decision, EU, Open, Government, Licence, OGL, v3) are legitimate. R2 put those
# tokens into `_ZH_PARITY_ALLOW_LIST`, but that allowed a leaked ZH publisher
# to hide behind a whitelist, and the old extractor's depth-counter only
# tracked a single number so a nested child inside `.l-en` could leak its
# following text. R3 fixes the root cause: the rights span is itself treated as
# a non-ZH context (like `.l-en`), so its text is excluded from the parity check
# and the allow-list is empty. There are no Latin runs >=3 letters inside any
# `t(en, zh)` ZH argument between `<article class="imd-card imd-dossier"` and
# its `</article>` (enumerated by `latin_runs_in_zh` below).
_ZH_PARITY_ALLOW_LIST = frozenset()


class _ZhTextExtractor(HTMLParser):
    """Collect visible text that is OUTSIDE `.l-en` spans, `lang="en"` elements,
    AND the `.imd-dossier-rights` span (the legal-rights identifier, which
    renders untranslated by design — D55(6) / R3).

    The dossier template's bilingual macro `t(en, zh)` wraps every translated
    string in a pair `<span class="l-en">…</span><span class="l-zh">…</span>`;
    the headline anchor additionally declares `lang="en"`. The rights-basis
    span carries class `imd-dossier-rights` and is intentionally non-bilingual
    so its Latin tokens don't fail parity.

    Implemented as a small state machine (no bs4 dependency): a stack of bools
    tracks per-element non-ZH context. `handle_endtag` pops one entry per end
    tag (HTML void tags like `<br>` / `<img>` / `<meta>` emit NO end tag, so we
    must NOT push for them — otherwise the stack gets unbalanced). `handle_data`
    appends only when no True is on the stack.
    """

    _VOID_TAGS = frozenset({
        "br", "img", "hr", "input", "meta", "link", "wbr", "source", "col",
        "area", "base", "embed", "param", "track",
    })

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[bool] = []
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self._VOID_TAGS:
            return
        attr_d = dict(attrs)
        cls = (attr_d.get("class") or "").split()
        lang = attr_d.get("lang")
        is_non_zh = ("l-en" in cls) or ("imd-dossier-rights" in cls) or (lang == "en")
        self._stack.append(is_non_zh)

    def handle_endtag(self, tag: str) -> None:
        if self._stack:
            self._stack.pop()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # D57 NIT 7: HTMLParser's default routes `<br/>` through handle_starttag
        # (which pushes nothing for a void tag) and then handle_endtag (which
        # pops) — one self-closing void tag inside an `l-en` span would unmask
        # the English that follows it. A void tag is a no-op; a self-closing
        # non-void tag pushes and pops symmetrically.
        if tag.lower() in self._VOID_TAGS:
            return
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if not any(self._stack):
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
    # R3 restored (D56 N2): R2 deleted these two guards so a missing
    # translation (an empty <span class="l-zh">) could pass parity. Both
    # surfaces are parity invariants and the bilingual macro `t(en, zh)` is
    # paired by construction.
    assert not re.search(r'<span class="l-zh">\s*</span>', slice_), (
        "empty <span class='l-zh'> detected — missing ZH translation"
    )
    assert slice_.count('class="l-en"') == slice_.count('class="l-zh"'), (
        "l-en and l-zh span counts differ — bilateral template had an unmatched "
        "translation"
    )


# --------------------------------------------------------------------------- #
# Test 10b — positive control: a leaked English publisher in the .l-zh span is
# CAUGHT by the parity assertion (R3, D56 N2).
# --------------------------------------------------------------------------- #
def test_zh_parity_catches_an_english_publisher_in_the_zh_span() -> None:
    """If an English publisher name (e.g. 'European Commission') ever leaks
    into a `<span class="l-zh">` slot — because a translator forgot the ZH
    rendering — the parity test must catch it.

    POSITIVE CONTROL: the unmutated render's ZH-visible text contains the ZH
    publisher `欧盟委员会` and the leadership phrase `领导层表态`, and does NOT
    contain `European Commission` (lives in `.l-en`) or `CC BY` (lives in the
    rights span — also skipped by design).

    MUTATION: replace the first occurrence of `欧盟委员会` with `European
    Commission` in the rendered slice. The parity assertion must then raise.
    With `_ZH_PARITY_ALLOW_LIST` empty (R3), `European Commission` is NOT
    filtered and `re.findall(r"[A-Za-z]{3,}", …)` returns `['European',
    'Commission']`.
    """
    view = _view("EZ")
    view["dossier"] = _covered_ez()
    html = _render(view)
    slice_ = _slice(html)

    # POSITIVE CONTROL
    txt = _zh_visible_text(slice_)
    assert "欧盟委员会" in txt, f"expected ZH publisher in ZH-visible text; got {txt!r}"
    assert "领导层表态" in txt, f"expected leadership phrase in ZH-visible text; got {txt!r}"
    assert "European Commission" not in txt, (
        f"EN publisher leaked into ZH-visible text: {txt!r}"
    )
    assert "CC BY" not in txt, f"rights-line token leaked: {txt!r}"

    # MUTATION — first occurrence is enough; the published items render the
    # ZH publisher once per item, and there are two of them, so we replace ALL.
    mutated = slice_.replace("欧盟委员会", "European Commission")
    assert "欧盟委员会" not in mutated, "mutation failed"
    assert "European Commission" in mutated

    with pytest.raises(AssertionError) as exc:
        _assert_zh_only_letters_or_allow_list(mutated)
    # surface the leaked tokens the assertion named — they are the proof.
    assert "European" in str(exc.value) or "Commission" in str(exc.value), (
        f"expected leaked Latin in assertion message; got {exc.value!r}"
    )


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


# --------------------------------------------------------------------------- #
# Test 14 — D56 N1: light headline keeps its link colour on hover; dark
# headline still brightens (specificity tie → source order is load-bearing).
# --------------------------------------------------------------------------- #
def test_headline_hover_keeps_link_colour_in_light_and_brightens_in_dark() -> None:
    """DARK hover rule: `body.imd-page .imd-dossier-headline:hover{color:var(--text)}`
    (specificity 0,3,1) brightens the headline to `--text`.

    LIGHT hover rule (R3): `html[data-theme="light"] .imd-dossier-headline:hover
    {color:var(--ink-link,var(--link));text-decoration:underline;
    text-underline-offset:2px}` (also 0,3,1) sets BOTH the colour and the
    underline. The colour must stay at `--ink-link` (with `--link` fallback) so
    the headline does NOT drop to `--text` (which is near-black in light theme).

    Specificity tie (both 0,3,1) means source order is load-bearing: the LIGHT
    rule appears LATER in the stylesheet, so when both match (the dark rule has
    no theme qualifier and always matches), the LIGHT rule's colour wins in
    light theme. In dark theme, the LIGHT rule does not match and the DARK
    rule's `color:var(--text)` brightens the headline as designed.
    """
    tpl = (ROOT / "templates" / "international_macro.html.j2").read_text()
    dark = 'body.imd-page .imd-dossier-headline:hover{color:var(--text)}'
    light = ('html[data-theme="light"] .imd-dossier-headline:hover'
             '{color:var(--ink-link,var(--link));text-decoration:underline;'
             'text-underline-offset:2px}')

    assert tpl.count(dark) == 1, (
        "dark hover rule missing or changed — pin the exact spot before judging"
    )
    assert tpl.count(light) == 1, (
        "light hover rule missing or changed — pin the exact spot before judging"
    )

    dark_idx = tpl.index(dark)
    light_idx = tpl.index(light)
    assert light_idx > dark_idx, (
        f"light rule at index {light_idx} must appear AFTER dark rule at "
        f"index {dark_idx} so the 0,3,1 specificity tie resolves to the light "
        f"colour (D56 N1)."
    )


# --------------------------------------------------------------------------- #
# Test 15 — R3 extractor: text after a nested child inside `.l-en` must NOT
# leak into the ZH side. R2's depth counter popped on ANY end tag, so a `<b>`
# inside `<span class="l-en">` would zero the counter and the trailing
# `.l-en` text would be re-included — silently fixing nothing.
# --------------------------------------------------------------------------- #
def test_zh_extractor_does_not_leak_text_after_a_nested_child_in_an_en_span() -> None:
    """Pin the stack-based fix: the old `_en_depth` counter popped on every
    end tag. Feed an `<span class="l-en">` that contains a nested `<b>`; the
    counter would go 1 → 0 on the `</b>` end tag, then EVERYTHING after
    `</b>` inside the still-open `<span class="l-en">` would be re-included
    as ZH-visible text. R3 replaces the counter with a stack of bools and
    pops one entry per end tag — so the result is correctly empty (only the
    trailing `<span class="l-zh">阅读</span>` content survives).
    """
    sample = (
        '<span class="l-en">Read <b>more</b> here</span>'
        '<span class="l-zh">阅读</span>'
    )
    assert _zh_visible_text(sample) == "阅读", (
        "ZH extractor dropped text from the trailing <span class='l-en'> "
        "when a nested child popped the old depth counter (R3 stack fix)."
    )


def test_zh_text_extractor_keeps_english_masked_across_self_closing_void_tags() -> None:
    """D57 NIT 7 — a `<br/>` inside an `l-en` span must not pop the span's
    context: before the `handle_startendtag` override the English that
    followed the tag leaked into the ZH-visible text."""
    html = '<span class="l-en"><br/>English only</span><span class="l-zh">中文</span>'
    assert _zh_visible_text(html) == "中文"
    assert _zh_visible_text('<span class="l-en">EN<br>more</span><span class="l-zh">中</span>') == "中"


def test_capture_finalize_rewrites_scratch_relative_cell_paths_into_cells_dir() -> None:
    """R4b (D57 review round): the stitched sub-manifests are scratch-relative
    (`cells.rest/…`, `cells.interaction/…`) while the PNGs are copied into the
    receipt's `cells/`; `check_ui_visual_evidence.py` resolves `file` against the
    receipt dir, so an un-normalized manifest fails with one missing-file finding
    per cell (measured on the R4 recapture: 52). finalize_manifest must rewrite the
    paths, leave excluded rows alone, and be idempotent."""
    import importlib.util

    repo = Path(__file__).resolve().parents[1]
    module_path = repo / "mockups" / "evidence" / "mo-paid-006-dossier-page" / "capture.py"
    spec = importlib.util.spec_from_file_location("mo_paid_006_capture", module_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    stitched = {
        "schema": "mastermind.p0_evidence.v2",
        "pages": [{
            "page_id": "euro_area",
            "route": "/international_macro/euro_area.html",
            "states": [
                {"viewport": "desktop", "locale": "en", "theme": "dark", "captured": True,
                 "file": "cells.rest/9fd42742bc6c6fa3.png"},
                {"viewport": "desktop", "locale": "en", "theme": "dark", "captured": True,
                 "force_state": "imd_dossier_headline_hover",
                 "file": "cells.interaction/14d8cf84096182b8--imd_dossier_headline_hover.png"},
                {"viewport": "desktop", "locale": "en", "theme": "dark", "captured": False,
                 "force_state": "imd_dossier_headline_focus", "expected_miss_reason": "no headline"},
            ],
        }],
    }
    once = mod.finalize_manifest(stitched, template_commit="a" * 40, site_commit="b" * 40)
    files = [s["file"] for s in once["pages"][0]["states"]]
    assert files == ["cells/9fd42742bc6c6fa3.png",
                     "cells/14d8cf84096182b8--imd_dossier_headline_hover.png"], files
    assert len(once["excluded"]) == 1 and "file" not in once["excluded"][0]
    twice = mod.finalize_manifest(once, template_commit="a" * 40, site_commit="b" * 40)
    assert [s["file"] for s in twice["pages"][0]["states"]] == files
    assert twice["totals"] == once["totals"] == {
        "pages": 1, "states_attempted": 2, "states_captured": 2, "expected_miss_excluded": 1}


@pytest.mark.needs_full_checkout("mockups")
def test_mo_paid_006_receipt_template_blob_is_the_committed_template():
    """R4c: the receipt's pixels were rendered from the worktree template, so the
    manifest records that blob; it must equal the committed template's blob (git
    blob id = sha1(b"blob <len>\\0" + bytes)). A template edit without a recapture
    reds this — the committed receipt is the evidence of record for the card."""
    repo = Path(__file__).resolve().parents[1]
    manifest = json.loads((repo / "mockups/evidence/mo-paid-006-dossier-page/manifest.json")
                          .read_text(encoding="utf-8"))
    scope = manifest["scope"]
    data = (repo / "templates/international_macro.html.j2").read_bytes()
    blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
    assert scope["template_matches_source_commit"] is True
    assert scope["template_blob"] == scope["template_blob_at_source_commit"] == blob, (
        f"receipt template blob {scope['template_blob'][:12]} != committed template blob {blob[:12]} — "
        "re-run mockups/evidence/mo-paid-006-dossier-page/capture.py after editing the template")
    assert manifest["tool"]["version"] == "4"


@pytest.mark.needs_full_checkout("mockups")
def test_mo_paid_006_dom_rows_record_the_locale_leadership_span():
    """R4c: ZH rows carry the ZH span literal (R2–R4b recorded `.l-en` for both
    locales), and every row's VISIBLE span is the locale's span."""
    repo = Path(__file__).resolve().parents[1]
    rows = json.loads((repo / "mockups/evidence/mo-paid-006-dossier-page/dom.json").read_text(encoding="utf-8"))
    assert len(rows) == 40
    for r in rows:
        prefix = "领导层表态：" if r["locale"] == "zh" else "Leadership statements:"
        assert r["leadership_text"].startswith(prefix), (r["page_id"], r["locale"], r["leadership_text"])
        assert r["leadership_text_visible"] == r["leadership_text"], (
            r["page_id"], r["locale"], r["theme"], r["viewport"], r["leadership_text_visible"])


@pytest.mark.needs_full_checkout("mockups")
def test_mo_paid_006_dom_rows_observe_theme_lang_and_wire_link():
    """R4c: applied_theme/applied_locale are OBSERVED html[data-theme]/[data-lang]
    (R2–R4b echoed the request); the EZ wire link is measured per cell."""
    repo = Path(__file__).resolve().parents[1]
    rows = json.loads((repo / "mockups/evidence/mo-paid-006-dossier-page/dom.json").read_text(encoding="utf-8"))
    assert len(rows) == 40
    for r in rows:
        assert r["applied_theme"] == r["theme"] == r["requested_theme"], (r["page_id"], r["theme"], r["applied_theme"])
        assert r["applied_locale"] == r["locale"] == r["requested_locale"], (r["page_id"], r["locale"], r["applied_locale"])
        if r["page_id"] in ("euro_area", "euro_area_outage"):  # both EZ fixtures (D.cc == 'EZ')
            assert r["more_link_count"] == 1 and r["more_link_href"] == "#europe-news", (r["page_id"], r["more_link_href"])
        else:
            assert r["more_link_count"] == 0, (r["page_id"], r["more_link_count"])


# --- R4e: --finalize-only fails closed on a missing/invalid source binding ----------

_ABSENT = object()


def _load_mo_paid_006_capture_module():
    import importlib.util

    repo = Path(__file__).resolve().parents[1]
    module_path = repo / "mockups" / "evidence" / "mo-paid-006-dossier-page" / "capture.py"
    spec = importlib.util.spec_from_file_location("mo_paid_006_capture_r4e", module_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.needs_full_checkout("mockups")
@pytest.mark.parametrize("binding", [
    _ABSENT,                      # key missing entirely
    None,                         # explicit null
    "",                           # empty string
    "HEAD",                       # symbolic ref — would resolve to whatever HEAD is today
    "3565430d",                   # abbreviated id
    "3565430d3cb6",               # 12-char abbreviation (the form the ledgers quote)
    "3565430D3CB6" + "0" * 28,    # 40 chars but upper-case hex — not a git object id as emitted
], ids=["absent", "null", "empty", "symbolic-HEAD", "short-8", "short-12", "upper-40"])
def test_capture_finalize_only_refuses_a_manifest_without_a_source_binding(tmp_path, monkeypatch, binding):
    """R4e (CEO B 5967022648 / 5967204240, measured on main e72c6b85, capture.py blob
    23376ed4): the finalize-only pass used to read `source_commit` with an
    `or HEAD` fallback, so five absent/null/empty binding variants silently
    re-attributed an existing receipt's pixels to the current HEAD and rewrote its
    template metadata without a recapture. The pass must now REFUSE (rc 2) before
    writing a byte, and `--allow-dirty-template` — a template-blob debug aid — must
    not excuse the missing binding."""
    mod = _load_mo_paid_006_capture_module()
    manifest: dict = {"schema": "mastermind.p0_evidence.v2", "pages": [], "excluded": []}
    if binding is not _ABSENT:
        manifest["source_commit"] = binding
    out = tmp_path / "receipt"
    out.mkdir()
    path = out / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    before = path.read_bytes()

    assert mod.source_binding(manifest) is None

    monkeypatch.setattr(mod, "OUT_DIR", out)
    monkeypatch.setattr(sys, "argv", ["capture.py", "--finalize-only", "--allow-dirty-template"])
    assert mod.main() == 2
    assert path.read_bytes() == before, "a refused finalize-only pass must not mutate the receipt"
    assert sorted(p.name for p in out.iterdir()) == ["manifest.json"], "a refused pass writes nothing else"


@pytest.mark.needs_full_checkout("mockups")
def test_capture_source_binding_accepts_only_a_full_lowercase_hex_commit():
    """The positive side of R4e: an explicit 40-hex binding is preserved verbatim
    (the finalize-only pass then compares the worktree template against THAT
    commit's blob, never against HEAD), and the committed receipt itself carries
    one — so the guard cannot refuse the evidence of record."""
    mod = _load_mo_paid_006_capture_module()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1],
                                   text=True).strip()
    assert mod.source_binding({"source_commit": head}) == head
    assert mod.source_binding({"source_commit": "a" * 40}) == "a" * 40
    committed = json.loads((Path(__file__).resolve().parents[1] /
                            "mockups/evidence/mo-paid-006-dossier-page/manifest.json").read_text(encoding="utf-8"))
    assert mod.source_binding(committed) == committed["source_commit"]


# --- F02-006-FIXBIND-01: --finalize-only refuses malformed fixture/image bindings -----
#
# CEO A D81/D82/D90 on #6819. A sound minimal receipt in the committed receipt's shape
# is built per test, ONE defect is introduced, and `main()` must refuse with rc 2 and
# the exact defect before any finalizer call or write, under both template modes. The
# sound receipt itself finalizes (rc 0), so every refusal is caused by its mutation.

_FIXBIND_REST = "a1a1a1a1a1a1a1a1.png"
_FIXBIND_HOVER = "b2b2b2b2b2b2b2b2--imd_dossier_headline_hover.png"
_FIXBIND_LIGHT = "c3c3c3c3c3c3c3c3.png"
_FIXBIND_CELLS = {
    _FIXBIND_REST: b"\x89PNG\r\n\x1a\n" + b"rest-euro-area-dark;" * 3,
    _FIXBIND_HOVER: b"\x89PNG\r\n\x1a\n" + b"hover-euro-area-dark;" * 4,
    _FIXBIND_LIGHT: b"\x89PNG\r\n\x1a\n" + b"rest-japan-light;" * 5,
}


def _fixbind_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1],
                                   text=True).strip()


def _fixbind_cell(name: str, file: str | None = None, **extra) -> dict:
    data = _FIXBIND_CELLS[name]
    return {"viewport": "desktop", "locale": "en", "theme": "dark", "captured": True,
            "file": file or f"cells/{name}", "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data), **extra}


def _fixbind_receipt(tmp_path: Path, source_commit: str) -> tuple[Path, dict]:
    """Two fixture pages bound to two pages; three real cells, one per recognized
    reference form (`cells/`, `cells.interaction/`, `cells.rest/`); one force-state
    expected miss still inside `pages` and one already in `excluded` (neither has a PNG)."""
    out = tmp_path / "receipt"
    (out / "cells").mkdir(parents=True)
    for name, data in _FIXBIND_CELLS.items():
        (out / "cells" / name).write_bytes(data)
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "source_commit": source_commit,
        "fixture_pages": {
            "euro_area": {"route": "euro_area.html", "sha256": "e" * 64, "bytes": 132875},
            "japan": {"route": "japan.html", "sha256": "f" * 64, "bytes": 129741},
        },
        "pages": [
            {"page_id": "euro_area", "route": "/euro_area.html", "states": [
                _fixbind_cell(_FIXBIND_REST),
                _fixbind_cell(_FIXBIND_HOVER, file=f"cells.interaction/{_FIXBIND_HOVER}",
                              force_state="imd_dossier_headline_hover"),
            ]},
            {"page_id": "japan", "route": "/japan.html", "states": [
                _fixbind_cell(_FIXBIND_LIGHT, file=f"cells.rest/{_FIXBIND_LIGHT}", theme="light"),
                {"viewport": "desktop", "locale": "en", "theme": "dark", "captured": False, "file": None,
                 "force_state": "imd_dossier_headline_focus", "expected_miss": True,
                 "expected_miss_reason": "no .imd-dossier-headline on this route"},
            ]},
        ],
        "excluded": [{"page_id": "japan", "route": "/japan.html", "force_state": "imd_dossier_headline_hover",
                      "theme": "dark", "viewport": "desktop", "locale": "en", "expected_miss": True,
                      "reason": "no .imd-dossier-headline on this route"}],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return out, manifest


def _fixbind_outside_copy(tmp_path: Path, name: str) -> Path:
    """A byte-identical copy of a cell OUTSIDE the evidence directory."""
    outside = tmp_path / "outside"
    outside.mkdir(exist_ok=True)
    (outside / name).write_bytes(_FIXBIND_CELLS[name])
    return outside / name


def _fixbind_symlink_out(m: dict, out: Path, tmp_path: Path) -> None:
    target = _fixbind_outside_copy(tmp_path, _FIXBIND_REST)
    (out / "cells" / _FIXBIND_REST).unlink()
    (out / "cells" / _FIXBIND_REST).symlink_to(target)


def _fixbind_corrupt_same_length(m: dict, out: Path, tmp_path: Path) -> None:
    cell = out / "cells" / _FIXBIND_REST
    data = bytearray(cell.read_bytes())
    data[-1] ^= 0x01
    cell.write_bytes(bytes(data))


def _fixbind_state(m: dict) -> dict:
    return m["pages"][0]["states"][0]


# case id -> (mutation(manifest, receipt_dir, tmp_path), exact defect text printed by main())
_FIXBIND_NEGATIVES = {
    # (a) a fixture / page / route binding field absent or malformed
    "fixture-pages-absent": (
        lambda m, out, tmp: m.pop("fixture_pages"),
        "`fixture_pages` is absent or not a non-empty mapping (NoneType)"),
    "fixture-pages-not-a-mapping": (
        lambda m, out, tmp: m.__setitem__("fixture_pages", sorted(m["fixture_pages"])),
        "`fixture_pages` is absent or not a non-empty mapping (list)"),
    "fixture-route-malformed": (
        lambda m, out, tmp: m["fixture_pages"]["japan"].__setitem__("route", "../japan.html"),
        "fixture_pages['japan'].route '../japan.html' is not a bare <name>.html"),
    "fixture-sha256-malformed": (
        lambda m, out, tmp: m["fixture_pages"]["japan"].__setitem__("sha256", "f" * 12),
        f"fixture_pages['japan'].sha256 {'f' * 12!r} is not 64 lowercase hex"),
    "fixture-bytes-bool": (
        lambda m, out, tmp: m["fixture_pages"]["japan"].__setitem__("bytes", True),
        "fixture_pages['japan'].bytes True is not a byte count"),
    "pages-absent": (
        lambda m, out, tmp: m.pop("pages"),
        "`pages` is absent or not a non-empty list (NoneType)"),
    "pages-not-a-list": (
        lambda m, out, tmp: m.__setitem__("pages", {p["page_id"]: p for p in m["pages"]}),
        "`pages` is absent or not a non-empty list (dict)"),
    "page-id-absent": (
        lambda m, out, tmp: m["pages"][1].pop("page_id"),
        "pages[1].page_id None names no fixture page"),
    "page-id-unknown": (
        lambda m, out, tmp: m["pages"][1].__setitem__("page_id", "korea"),
        "pages[1].page_id 'korea' names no fixture page"),
    "page-id-duplicated": (
        lambda m, out, tmp: m["pages"][1].update(page_id="euro_area", route="/euro_area.html"),
        "pages[1].page_id 'euro_area' is duplicated"),
    "page-route-mismatch": (
        lambda m, out, tmp: m["pages"][1].__setitem__("route", "/korea.html"),
        "pages[1] (japan) route '/korea.html' != fixture route '/japan.html'"),
    "fixture-page-unbound": (
        lambda m, out, tmp: m["pages"].pop(1),
        "fixture page(s) ['japan'] have no pages[] row"),
    "excluded-page-unknown": (
        lambda m, out, tmp: m["excluded"][0].__setitem__("page_id", "korea"),
        "excluded[0].page_id 'korea' names no fixture page"),
    "excluded-route-mismatch": (
        lambda m, out, tmp: m["excluded"][0].__setitem__("route", "/euro_area.html"),
        "excluded[0] (japan) route '/euro_area.html' != fixture route '/japan.html'"),
    "kept-state-not-captured": (
        lambda m, out, tmp: _fixbind_state(m).__setitem__("captured", False),
        "pages[0] (euro_area) states[0] is kept in the receipt but not captured (`captured` = False)"),
    "image-reference-absent": (
        lambda m, out, tmp: _fixbind_state(m).pop("file"),
        "pages[0] (euro_area) states[0]: no image reference (`file` = None)"),
    "image-sha256-malformed": (
        lambda m, out, tmp: _fixbind_state(m).__setitem__("sha256", "ABC"),
        "pages[0] (euro_area) states[0]: recorded sha256 'ABC' is not 64 lowercase hex"),
    "image-bytes-bool": (
        lambda m, out, tmp: _fixbind_state(m).__setitem__("bytes", True),
        "pages[0] (euro_area) states[0]: recorded bytes True is not a byte count"),
    # (b) a referenced image missing on disk or resolving outside the evidence directory
    "image-missing": (
        lambda m, out, tmp: _fixbind_state(m).__setitem__("file", "cells/ffffffffffffffff.png"),
        "pages[0] (euro_area) states[0]: image 'cells/ffffffffffffffff.png' is missing on disk"),
    "image-wrong-case": (
        lambda m, out, tmp: _fixbind_state(m).__setitem__("file", f"cells/{_FIXBIND_REST.upper()}"),
        f"pages[0] (euro_area) states[0]: image 'cells/{_FIXBIND_REST.upper()}' is missing on disk"),
    "image-absolute": (
        lambda m, out, tmp: _fixbind_state(m).__setitem__("file", str(_fixbind_outside_copy(tmp, _FIXBIND_REST))),
        "is absolute or not a POSIX relative path"),
    "image-traversal": (
        lambda m, out, tmp: (_fixbind_outside_copy(tmp, _FIXBIND_REST),
                             _fixbind_state(m).__setitem__("file", f"cells.rest/../../outside/{_FIXBIND_REST}")),
        f"pages[0] (euro_area) states[0]: image reference 'cells.rest/../../outside/{_FIXBIND_REST}' "
        "traverses out of the evidence directory"),
    "image-foreign-prefix": (
        lambda m, out, tmp: _fixbind_state(m).__setitem__("file", f"shots/{_FIXBIND_REST}"),
        f"pages[0] (euro_area) states[0]: image reference 'shots/{_FIXBIND_REST}' is not cells/<name> "
        "(or a cells.rest/ / cells.interaction/ alias)"),
    "image-nested": (
        lambda m, out, tmp: _fixbind_state(m).__setitem__("file", f"cells/sub/{_FIXBIND_REST}"),
        f"pages[0] (euro_area) states[0]: image reference 'cells/sub/{_FIXBIND_REST}' is not cells/<name> "
        "(or a cells.rest/ / cells.interaction/ alias)"),
    "image-symlink-out": (
        _fixbind_symlink_out,
        f"pages[0] (euro_area) states[0]: image reference 'cells/{_FIXBIND_REST}' is a symlink"),
    # (c) a referenced image whose recorded sha256 / byte length mismatches the file on disk
    "image-sha256-mismatch": (
        lambda m, out, tmp: _fixbind_state(m).__setitem__("sha256", hashlib.sha256(b"other").hexdigest()),
        f"pages[0] (euro_area) states[0]: cells/{_FIXBIND_REST} sha256 "
        f"{hashlib.sha256(_FIXBIND_CELLS[_FIXBIND_REST]).hexdigest()[:12]} on disk "
        f"!= recorded {hashlib.sha256(b'other').hexdigest()[:12]}"),
    "image-length-mismatch": (
        lambda m, out, tmp: _fixbind_state(m).__setitem__("bytes", len(_FIXBIND_CELLS[_FIXBIND_REST]) + 1),
        f"pages[0] (euro_area) states[0]: cells/{_FIXBIND_REST} is {len(_FIXBIND_CELLS[_FIXBIND_REST])} bytes "
        f"on disk, recorded {len(_FIXBIND_CELLS[_FIXBIND_REST]) + 1}"),
    "image-same-length-corruption": (
        _fixbind_corrupt_same_length,
        f"pages[0] (euro_area) states[0]: cells/{_FIXBIND_REST} sha256 "
        f"{hashlib.sha256(_FIXBIND_CELLS[_FIXBIND_REST][:-1] + bytes([_FIXBIND_CELLS[_FIXBIND_REST][-1] ^ 1])).hexdigest()[:12]} "
        f"on disk != recorded {hashlib.sha256(_FIXBIND_CELLS[_FIXBIND_REST]).hexdigest()[:12]}"),
}


def _fixbind_case(tmp_path: Path, case: str) -> tuple[Path, str]:
    """The sound receipt (bound to HEAD) with exactly one `_FIXBIND_NEGATIVES` defect."""
    out, manifest = _fixbind_receipt(tmp_path, _fixbind_head())
    mutate, defect = _FIXBIND_NEGATIVES[case]
    mutate(manifest, out, tmp_path)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return out, defect


def _fixbind_inventory(root: Path) -> dict:
    """Every path under `root` (symlinks NOT followed) with its bytes / link target."""
    inv: dict = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in sorted(dirnames + filenames):
            path = Path(dirpath) / name
            rel = str(path.relative_to(root))
            if path.is_symlink():
                inv[rel] = ("symlink", os.readlink(path))
            elif path.is_file():
                inv[rel] = path.read_bytes()
            else:
                inv[rel] = "dir"
    return inv


def _fixbind_argv(allow_dirty: bool) -> list[str]:
    return ["capture.py", "--finalize-only"] + (["--allow-dirty-template"] if allow_dirty else [])


@pytest.mark.needs_full_checkout("mockups")
@pytest.mark.parametrize("allow_dirty", [False, True], ids=["strict", "allow-dirty-template"])
@pytest.mark.parametrize("case", list(_FIXBIND_NEGATIVES))
def test_capture_finalize_only_refuses_a_malformed_fixture_or_image_binding(tmp_path, monkeypatch, capsys,
                                                                            case, allow_dirty):
    """F02-006-FIXBIND-01: a finalize-only pass refuses (rc 2) a receipt whose fixture /
    page / route binding is absent or malformed, whose referenced image is missing or
    resolves outside the evidence directory, or whose image bytes no longer match the
    recorded sha256 / length — naming the exact defect, with no finalizer call, no write
    sink touched, and the whole tree (receipt + any outside copy) byte-identical."""
    mod = _load_mo_paid_006_capture_module()
    out, defect = _fixbind_case(tmp_path, case)
    before = _fixbind_inventory(tmp_path)

    sinks: list[str] = []
    finalize = mod.finalize_manifest
    monkeypatch.setattr(mod, "finalize_manifest",
                        lambda *a, **k: sinks.append("finalize_manifest") or finalize(*a, **k))
    for name in ("write_text", "write_bytes"):
        real = getattr(Path, name)
        monkeypatch.setattr(Path, name, (lambda real, name: lambda self, *a, **k:
                                         sinks.append(f"Path.{name}:{self}") or real(self, *a, **k))(real, name))
    monkeypatch.setattr(mod, "OUT_DIR", out)
    monkeypatch.setattr(sys, "argv", _fixbind_argv(allow_dirty))

    assert mod.main() == 2
    printed = capsys.readouterr().out
    assert "fixture/image binding defect(s); nothing was written" in printed, printed
    assert defect in printed, printed
    assert sinks == [], sinks
    assert _fixbind_inventory(tmp_path) == before, "a refused finalize-only pass must not touch any byte"


@pytest.mark.needs_full_checkout("mockups")
@pytest.mark.parametrize("allow_dirty", [False, True], ids=["strict", "allow-dirty-template"])
def test_capture_finalize_only_finalizes_a_sound_receipt(tmp_path, monkeypatch, capsys, allow_dirty):
    """The positive side: the sound receipt every negative is cut from finalizes (rc 0)
    — the three reference forms land as `cells/<name>`, both expected misses sit in
    `excluded`, `source_commit` stays the recorded binding, both self-hash fields equal
    SHA256 of the module's actual bytes, the cells are untouched, and a second pass is
    byte-identical."""
    mod = _load_mo_paid_006_capture_module()
    head = _fixbind_head()
    out, manifest = _fixbind_receipt(tmp_path, head)
    assert mod.fixture_binding_defects(manifest, out) == []
    cells_before = {p.name: p.read_bytes() for p in (out / "cells").iterdir()}
    monkeypatch.setattr(mod, "OUT_DIR", out)
    monkeypatch.setattr(sys, "argv", _fixbind_argv(allow_dirty))

    assert mod.main() == 0, capsys.readouterr().out
    first = (out / "manifest.json").read_bytes()
    final = json.loads(first)
    assert [s["file"] for p in final["pages"] for s in p["states"]] == [
        f"cells/{_FIXBIND_REST}", f"cells/{_FIXBIND_HOVER}", f"cells/{_FIXBIND_LIGHT}"]
    assert len(final["excluded"]) == 2
    assert final["source_commit"] == head
    module_sha = hashlib.sha256(Path(mod.__file__).read_bytes()).hexdigest()
    assert final["tool"]["module_sha256"] == final["capture_tool_module_sha256"] == module_sha
    assert {p.name: p.read_bytes() for p in (out / "cells").iterdir()} == cells_before

    assert mod.main() == 0
    assert (out / "manifest.json").read_bytes() == first, "finalize-only must be idempotent"


@pytest.mark.needs_full_checkout("mockups")
def test_capture_finalize_only_source_binding_refusal_precedes_fixture_validation(tmp_path, monkeypatch, capsys):
    """R4e stays first: a receipt with BOTH a symbolic binding and no fixture pages is
    refused for the binding, before the fixture validator runs."""
    mod = _load_mo_paid_006_capture_module()
    out, manifest = _fixbind_receipt(tmp_path, "HEAD")
    manifest.pop("fixture_pages")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(mod, "OUT_DIR", out)
    monkeypatch.setattr(sys, "argv", _fixbind_argv(True))
    assert mod.main() == 2
    printed = capsys.readouterr().out
    assert "carries no 40-hex `source_commit` binding" in printed
    assert "fixture/image binding" not in printed


@pytest.mark.needs_full_checkout("mockups")
def test_mo_paid_006_committed_receipt_has_no_fixture_or_image_binding_defect():
    """The evidence of record passes the FIXBIND validator as committed (5 fixture pages
    bound to 5 pages, 52 cells hashed from disk, 8 excluded rows)."""
    mod = _load_mo_paid_006_capture_module()
    receipt = Path(__file__).resolve().parents[1] / "mockups/evidence/mo-paid-006-dossier-page"
    manifest = json.loads((receipt / "manifest.json").read_text(encoding="utf-8"))
    assert mod.fixture_binding_defects(manifest, receipt) == []


@pytest.mark.needs_full_checkout("mockups")
def test_mo_paid_006_finalize_only_on_a_copy_of_the_committed_receipt_changes_only_the_tool_hash(
        tmp_path, monkeypatch, capsys):
    """Natural identity on a disposable copy of the committed receipt + PNGs (the canonical
    receipt is never touched): rc 0; the output differs from the committed manifest ONLY in
    the two self-hash fields, which equal SHA256 of this module's actual bytes;
    `source_commit` stays the recorded binding, never HEAD; a second pass is byte-identical."""
    mod = _load_mo_paid_006_capture_module()
    repo = Path(__file__).resolve().parents[1]
    receipt = repo / "mockups/evidence/mo-paid-006-dossier-page"
    committed_bytes = (receipt / "manifest.json").read_bytes()
    committed = json.loads(committed_bytes)
    recorded = committed["source_commit"]
    if subprocess.run(["git", "cat-file", "-e", f"{recorded}^{{commit}}"], cwd=repo,
                      capture_output=True).returncode != 0:
        pytest.skip(f"recorded source_commit {recorded[:12]} is not in this clone (shallow checkout); "
                    "the finalize-only template check resolves it")
    copy = tmp_path / "receipt"
    shutil.copytree(receipt / "cells", copy / "cells")
    shutil.copy2(receipt / "manifest.json", copy / "manifest.json")
    monkeypatch.setattr(mod, "OUT_DIR", copy)
    monkeypatch.setattr(sys, "argv", _fixbind_argv(False))

    assert mod.main() == 0, capsys.readouterr().out
    first = (copy / "manifest.json").read_bytes()
    final = json.loads(first)
    module_sha = hashlib.sha256(Path(mod.__file__).read_bytes()).hexdigest()
    assert final["tool"]["module_sha256"] == final["capture_tool_module_sha256"] == module_sha
    assert final["source_commit"] == recorded
    for doc in (final, committed):
        doc["tool"]["module_sha256"] = doc["capture_tool_module_sha256"] = "<self-hash>"
    assert final == committed
    assert mod.main() == 0
    assert (copy / "manifest.json").read_bytes() == first, "finalize-only must be idempotent"
    assert (receipt / "manifest.json").read_bytes() == committed_bytes
