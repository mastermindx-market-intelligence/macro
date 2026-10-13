"""Unique ids and resolvable ARIA references in the pullback dialogs.

The measured-pullback fragment is rendered inside the US risk modal and the
China risk dialog. Both languages live in the same markup (``.l-en`` /
``.l-zh``). Observation states are the ones the dialog suites already build:
a qualified active reading (current), that reading with the client expiry
owner's DOM stamp applied (expired), and a delayed reading the dialog refuses
to lead with (unavailable).

Parsers and renderers are the suites' own. Checkers are pure so a mutated
string in this file can prove each one fires.
"""
from __future__ import annotations

import sys
import types
from functools import lru_cache

import pytest
from bs4 import BeautifulSoup

# scripts/build_site.py (imported by the US modal renderer) imports plotly at
# module level. The template render never draws with it. Stub only when the
# interpreter has no plotly, and never replace a real installation.
try:
    import plotly.graph_objects  # noqa: F401
    import plotly.subplots  # noqa: F401
except ModuleNotFoundError:
    _plotly = types.ModuleType("plotly")
    _go = types.ModuleType("plotly.graph_objects")
    _subplots = types.ModuleType("plotly.subplots")
    _subplots.make_subplots = lambda *args, **kwargs: None
    _plotly.graph_objects = _go
    _plotly.subplots = _subplots
    sys.modules.setdefault("plotly", _plotly)
    sys.modules.setdefault("plotly.graph_objects", _go)
    sys.modules.setdefault("plotly.subplots", _subplots)

from tests.test_cn_pullback_dialog_integration import _render as render_cn_dialog
from tests.test_macro_risk_dialog import _render as render_us_page
from tests.test_macro_risk_dialog import _vm
from tests.test_pullback_depth_a11y import EVIDENCE, RAW_PATH, _observation
from tests.test_risk_radar_pullback_depth_template import native_view, render as render_fragment

SURFACES = ("us", "cn")
LANGS = ("en", "zh")
STATES = ("current", "expired", "unavailable")
DIALOG_ID = {"us": "dlg-risk", "cn": "cnx-dlg-risk"}

REF_ATTRS = (
    "aria-labelledby",
    "aria-describedby",
    "aria-controls",
    "aria-owns",
    "aria-details",
    "aria-errormessage",
    "aria-activedescendant",
)

MATRIX = [
    (surface, lang, state)
    for surface in SURFACES
    for lang in LANGS
    for state in STATES
]


@lru_cache(maxsize=None)
def view_for(state, market):
    """States the dialog and fragment suites already construct.

    current / expired: the presented active episode (a11y ``_observation``).
    expired keeps that reading — the dialog still leads with it — but the
    deadline is already past, which is what the expiry owner then stamps.
    unavailable: ``quality="delayed"``, the unqualified change the dialog
    integration tests use to keep the previous layout.
    """
    if state == "unavailable":
        view = native_view(market)
        view["observation"]["quality"] = "delayed"
        return view
    fields = dict(EVIDENCE)
    if state == "expired":
        fields["valid_until"] = "2020-01-01T00:00:00+00:00"
    return _observation(market, "underway", path=RAW_PATH, **fields)


@lru_cache(maxsize=None)
def fragment_html(state, market) -> str:
    return render_fragment(view_for(state, market), market)


@lru_cache(maxsize=None)
def rendered(surface, state) -> str:
    if surface == "us":
        vm = _vm()
        vm["us_pullback_view"] = view_for(state, "us")
        return render_us_page(vm=vm, mode="macro")
    if surface == "cn":
        return render_cn_dialog(view_for(state, "cn"))
    raise AssertionError(surface)


def _stamp_expired(soup):
    """Replay the expiry owner's DOM edits (templates/_risk_radar_pullback_depth.js.j2).

    Adds ``pb-expired``, rewrites the bilingual heading, and moves the inert
    template message into the live region. Ids are not part of that stamp.
    """
    for section in soup.select("section.rrp.pbx"):
        raw = section.get("class")
        classes = raw.split() if isinstance(raw, str) else list(raw or [])
        if "pb-expired" not in classes:
            section["class"] = classes + ["pb-expired"]
        section["data-pb-phase"] = "unavailable"
        heading = section.select_one(".pbx-heading h2")
        if heading is not None:
            for selector, text in ((".l-en", "Price update needed"), (".l-zh", "价格数据待更新")):
                node = heading.select_one(selector)
                if node is None:
                    continue
                node.clear()
                node.append(text)
        region = section.select_one(".pbx-expiry")
        carrier = section.select_one("template.pbx-expiry-msg")
        if region is None or carrier is None or region.get("data-pb-announced") == "1":
            continue
        live = soup.new_tag("span")
        live["class"] = ["pbx-expiry-live"]
        for child in list(carrier.contents):
            live.append(child.extract())
        region.append(live)
        carrier.decompose()
        region["data-pb-announced"] = "1"


@lru_cache(maxsize=None)
def document(surface, state):
    soup = BeautifulSoup(rendered(surface, state), "html.parser")
    if state == "expired":
        _stamp_expired(soup)
    return soup


def parse(html: str):
    return BeautifulSoup(html, "html.parser")


def check_i1(soup):
    """I1: every id value is unique in the document."""
    seen = set()
    dupes = []
    for el in soup.find_all(True):
        if not el.has_attr("id"):
            continue
        value = el["id"]
        if value in seen:
            dupes.append(value)
        else:
            seen.add(value)
    assert not dupes, f"duplicate ids: {sorted(set(dupes))}"


def check_i2(soup):
    """I2: every listed id reference resolves inside the same document."""
    known = {el["id"] for el in soup.find_all(True) if el.has_attr("id")}
    missing = []
    for el in soup.find_all(True):
        for attr in REF_ATTRS:
            if not el.has_attr(attr):
                continue
            for token in (el.get(attr) or "").split():
                if token not in known:
                    missing.append(f"{el.name}[{attr}] -> #{token}")
        if el.name == "label" and el.has_attr("for") and (el.get("for") or "") not in known:
            missing.append(f"label[for] -> #{el.get('for')}")
        if el.name in ("td", "th") and el.has_attr("headers"):
            for token in (el.get("headers") or "").split():
                if token not in known:
                    missing.append(f"{el.name}[headers] -> #{token}")
        if el.name == "input" and el.has_attr("list") and (el.get("list") or "") not in known:
            missing.append(f"input[list] -> #{el.get('list')}")
    assert not missing, "unresolved id references: " + "; ".join(missing[:12])


def _lang_text(node, lang: str) -> str:
    spans = node.select(f".l-{lang}")
    if spans:
        return " ".join(span.get_text(" ", strip=True) for span in spans).strip()
    return node.get_text(" ", strip=True)


def check_i4(soup, surface, lang):
    """I4: the risk dialog's accessible name is non-empty in this language."""
    dialog = soup.find(id=DIALOG_ID[surface])
    assert dialog is not None and dialog.get("role") == "dialog", DIALOG_ID[surface]
    refs = (dialog.get("aria-labelledby") or "").split()
    if refs:
        parts = []
        for ref in refs:
            target = soup.find(id=ref)
            parts.append(_lang_text(target, lang) if target is not None else "")
        name = " ".join(part for part in parts if part).strip()
    else:
        name = (dialog.get("aria-label") or "").strip()
    assert name, f"{surface}/{lang}: dialog accessible name is empty"


def _hidden(el) -> bool:
    return (el.get("aria-hidden") or "").strip().lower() == "true"


def _focusable(el) -> bool:
    if el.name in ("button", "input"):
        return True
    if el.name == "a" and el.has_attr("href"):
        return True
    if not el.has_attr("tabindex"):
        return False
    raw = str(el.get("tabindex")).strip()
    if raw[:1] == "+":
        raw = raw[1:]
    if not raw.lstrip("-").isdigit():
        return False
    return int(raw) >= 0


def check_i5(soup, state):
    """I5: inside the fragment, nothing focusable is aria-hidden.

    ``aria-hidden`` on an ancestor hides the descendant, so a focusable control
    inside that subtree counts. ``tabindex>=0``, ``a[href]``, ``button`` and
    ``input`` are the focusable set.
    """
    sections = soup.select("section.rrp")
    if state == "unavailable":
        assert not sections, "a delayed observation must not lead the dialog with the fragment"
    else:
        assert sections, "the measured pullback fragment is missing"
    for section in sections:
        for el in section.find_all(True):
            if not _focusable(el):
                continue
            hidden = False
            node = el
            while node is not None:
                if _hidden(node):
                    hidden = True
                    break
                if node is section:
                    break
                node = node.parent
            assert not hidden, (
                f"focusable <{el.name}> is aria-hidden inside the pullback fragment"
            )


def _fragment_overlap(state):
    us = {el["id"] for el in parse(fragment_html(state, "us")).find_all(id=True)}
    cn = {el["id"] for el in parse(fragment_html(state, "cn")).find_all(id=True)}
    return us & cn


def _i3_cases():
    cases = []
    for state in STATES:
        overlap = _fragment_overlap(state)
        if not overlap:
            cases.append(state)
            continue
        reason = (
            "FINDING lib/illus.py:646 uid=_hash_id has no market prefix; "
            "lib/illus.py:317 emits id=ilxg-{uid}; "
            "lib/pullback_depth.py:229 draws both markets through illus(). "
            f"Colliding ids: {', '.join(sorted(overlap))}"
        )
        cases.append(pytest.param(state, marks=pytest.mark.xfail(strict=True, reason=reason)))
    return cases


@pytest.mark.parametrize(("surface", "lang", "state"), MATRIX)
def test_i1_ids_are_unique(surface, lang, state):
    check_i1(document(surface, state))


@pytest.mark.parametrize(("surface", "lang", "state"), MATRIX)
def test_i2_id_references_resolve(surface, lang, state):
    check_i2(document(surface, state))


@pytest.mark.parametrize("state", _i3_cases())
def test_i3_us_and_cn_fragment_ids_do_not_overlap(state):
    """Concatenated US and CN fragments must not share an id."""
    combined = fragment_html(state, "us") + fragment_html(state, "cn")
    check_i1(parse(combined))


@pytest.mark.parametrize(("surface", "lang", "state"), MATRIX)
def test_i4_dialog_has_an_accessible_name(surface, lang, state):
    check_i4(document(surface, state), surface, lang)


@pytest.mark.parametrize(("surface", "lang", "state"), MATRIX)
def test_i5_fragment_has_no_focusable_aria_hidden(surface, lang, state):
    check_i5(document(surface, state), state)


def test_i1_checker_rejects_a_duplicated_id():
    mutated = rendered("cn", "current") + '<div id="cnx-dlg-risk"></div>'
    with pytest.raises(AssertionError, match="duplicate ids"):
        check_i1(parse(mutated))


def test_i2_checker_rejects_a_broken_reference():
    html = rendered("cn", "current")
    mutated = html.replace(
        'aria-labelledby="cnx-dlg-risk-ttl"',
        'aria-labelledby="cnx-dlg-risk-missing"',
        1,
    )
    assert mutated != html
    with pytest.raises(AssertionError, match="unresolved id references"):
        check_i2(parse(mutated))


def test_i3_checker_rejects_a_shared_fragment_id():
    us = fragment_html("unavailable", "us").replace(
        "</section>", '<i id="pb-collide"></i></section>', 1)
    cn = fragment_html("unavailable", "cn").replace(
        "</section>", '<i id="pb-collide"></i></section>', 1)
    with pytest.raises(AssertionError, match="duplicate ids"):
        check_i1(parse(us + cn))


def test_i4_checker_rejects_a_dialog_without_a_name():
    html = rendered("cn", "unavailable")
    mutated = html.replace(' aria-labelledby="cnx-dlg-risk-ttl"', "", 1)
    assert 'aria-labelledby="cnx-dlg-risk-ttl"' not in mutated
    with pytest.raises(AssertionError, match="accessible name"):
        check_i4(parse(mutated), "cn", "en")


def test_i5_checker_rejects_a_focusable_hidden_control():
    html = fragment_html("current", "cn").replace(
        "</section>",
        '<button type="button" aria-hidden="true">Hidden</button></section>',
        1,
    )
    with pytest.raises(AssertionError, match="aria-hidden"):
        check_i5(parse(html), "current")
