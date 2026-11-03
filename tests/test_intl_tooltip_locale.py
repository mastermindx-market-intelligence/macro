"""International tooltips use the existing locale-aware LENS, with unchanged copy."""
from pathlib import Path
import importlib.util
import re
import socket

import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from engine import i18n

ROOT = Path(__file__).resolve().parents[1]
CJK = re.compile(r"[一-鿿㐀-䶿]")


@pytest.fixture(scope="module", autouse=True)
def no_network():
    patch = pytest.MonkeyPatch()
    def deny(*args, **kwargs):
        raise AssertionError("Network forbidden in International tooltip fixture")
    for obj, name in ((socket.socket, "connect"), (socket.socket, "connect_ex"),
                      (socket, "create_connection"), (socket, "getaddrinfo")):
        patch.setattr(obj, name, deny)
    yield
    patch.undo()


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tests" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _macros():
    # Production Intl uses autoescape=False, so the new attribute boundary must escape.
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                      autoescape=False, undefined=StrictUndefined)
    env.globals.update(t=i18n.t, tr=i18n.tr, td=i18n.td)
    return env.get_template("intl_workspace/_gs_scanner_macros.html.j2").module


def _tip(html, selector):
    node = BeautifulSoup(str(html), "html.parser").select_one(selector)
    assert node is not None and "title" not in node.attrs
    assert node.get("tabindex") == "0"
    return node


def test_abstain_and_tier_keep_exact_separate_copy_and_escape_attributes():
    sm = _macros()
    pair = ('Missing "quoted" <source> & input', '缺少“来源” <数据> & 输入')
    abstain = _tip(sm.sm_abstain_chip_only({"token": "value_unavailable", "reason": pair}), "[data-abstain]")
    assert (abstain["data-tip-en"], abstain["data-tip-zh"]) == pair
    assert abstain["data-abstain"] == "value_unavailable"
    assert abstain.select_one("source") is None
    tier = {"tier_abstain": True, "label": pair, "delay": None,
            "capability_display": None, "capability_reason": None}
    node = _tip(sm.sm_tier(tier), "[data-abstain]")
    assert (node["data-tip-en"], node["data-tip-zh"]) == pair
    assert node["data-abstain"] == "evidence_tier_undefined"


def test_coverage_title_reason_and_empty_branches_keep_their_own_language():
    sm = _macros()
    columns = [{"id": "title", "label": ("Title", "标题")},
               {"id": "reason", "label": ("Rates", "利率")},
               {"id": "empty", "label": ("Empty", "空白")}]
    cells = {key: {"state": None, "title": None, "reason_copy": None,
                   "excluded": True, "clock": None} for key in ("title", "reason", "empty")}
    cells["title"]["title"] = ('Held "source"', '保留“来源”')
    cells["reason"]["reason_copy"] = ('No <receipt>', '没有<回执>')
    row = {"kind": "market", "id": "JP", "linkable": False, "name_en": "Japan",
           "name_zh": "日本", "session": "—", "cells": cells, "use": [],
           "use_copy": ("None", "无")}
    html = sm.cov_row(row, {"session_title": ("Session unavailable", "交易时段未知"),
                           "matrix": {"columns": columns}})
    soup = BeautifulSoup(str(html), "html.parser")
    title = _tip(html, '[data-col="title"]')
    assert (title["data-tip-en"], title["data-tip-zh"]) == cells["title"]["title"]
    reason = _tip(html, '[data-col="reason"]')
    assert reason["data-tip-en"] == "Rates · No <receipt>"
    assert reason["data-tip-zh"] == "利率 · 没有<回执>"
    session = _tip(html, '.intl-gs__covcell--session')
    assert session["data-tip-zh"] == "交易时段未知"
    empty = soup.select_one('[data-col="empty"]')
    assert not any(key in empty.attrs for key in ("title", "data-tip-en", "tabindex"))
    assert not soup.select("receipt, 回执")


@pytest.fixture(scope="module")
def pages():
    return {
        "scanner-coverage": _load("intl_gs_scanner_fixture").render_abstain_page(),
        "dislocations": _load("intl_gs_dislocations_fixture").render_page(),
        "transmission": _load("intl_gs_transmission_fixture").render_transmission_page(),
    }


@pytest.mark.parametrize("name,selector", [
    ("scanner-coverage", '.intl-gs__view--scanner [data-abstain][data-tip-en]'),
    ("scanner-coverage", '.intl-gs__view--coverage [data-col][data-tip-en]'),
    ("dislocations", '.intl-dislocations__notplotted [data-tip-en]'),
    ("transmission", '.intl-transmission__mech [data-tip-en]'),
])
def test_native_renderers_emit_localized_keyboard_reachable_tooltips_and_consumer(pages, name, selector):
    soup = BeautifulSoup(pages[name], "html.parser")
    assert soup.select_one('script[src="theme.js"]') is not None
    nodes = soup.select(selector)
    assert nodes, (name, selector)
    for node in nodes:
        assert "title" not in node.attrs and node.get("tabindex") == "0"
        assert node["data-tip-en"] and node["data-tip-zh"]
    assert not [(n.name, n["title"]) for n in soup.select("[title]") if CJK.search(n["title"])]


def test_existing_lens_and_renderer_own_locale_focus_escape_and_description():
    js = (ROOT / "templates/theme.js").read_text()
    start = js.index("/* ---- LENS —")
    region = js[start:]
    assert "var SEL = '[data-tip-en], .lens-q, .lens-term'" in region
    assert "zh: t.getAttribute('data-tip-zh') || en" in region
    assert "document.addEventListener('focusin'" in region and "show(t);" in region
    assert "t.setAttribute('aria-describedby', 'lensPop')" in region
    assert "e.key === 'Escape' && isOpen()" in region
    assert "mkSpan('l-en', c.en)" in region and "mkSpan('l-zh', c.zh)" in region
    css = (ROOT / "templates/intl_workspace_surveillance.css").read_text()
    assert '[tabindex]' in css and ':focus-visible{outline:2px solid var(--link)' in css
    assert '<script src="theme.js"></script>' in (ROOT / "templates/intl.html.j2").read_text()
    assert '"theme.js"' in (ROOT / "scripts/build_intl.py").read_text()


@pytest.mark.parametrize("quoted_reason", [False, True])
def test_dislocation_unavailable_actions_are_really_disabled_with_separate_copy(quoted_reason):
    from lib.intl_gs_dislocations_view import COPY
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    env.globals.update(t=i18n.t, tr=i18n.tr, td=i18n.td)
    source = (ROOT / "templates/intl_workspace/dislocations.html.j2").read_text()
    start = source.index('<div class="intl-dislocations__btnrow"')
    end = source.index('</div>', start) + len('</div>')
    fragment = env.from_string("{% import 'intl_workspace/_gs_macros.html.j2' as gs with context %}" + source[start:end])
    context = {key: {"en": pair[0], "zh": pair[1]} for key, pair in COPY.items()}
    reason = ('Missing "target" <view> & receipt', '缺少“目标”<视图> & 回执') if quoted_reason else COPY["btn_disabled_title"]
    context["btn_disabled_title"] = {"en": reason[0], "zh": reason[1]}
    html = fragment.render(c=context)
    soup = BeautifulSoup(html, "html.parser")
    wrapper = soup.select_one('.intl-dislocations__btnrow')
    assert wrapper['tabindex'] == '0'
    assert (wrapper['data-tip-en'], wrapper['data-tip-zh']) == reason
    buttons = soup.select('button')
    assert len(buttons) == 2 and soup.select_one('view') is None
    for button in buttons:
        assert button.has_attr('disabled') and not button.has_attr('disabledtitle')
        assert not button.has_attr('title')
        assert (button['data-tip-en'], button['data-tip-zh']) == reason
