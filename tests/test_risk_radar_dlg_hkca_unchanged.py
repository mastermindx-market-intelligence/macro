"""Hong Kong and Canada risk dialogs stay on the pre-pullback shell.

templates/_risk_radar_dlg.html.j2 is shared by the China, Hong Kong and Canada
pages. The pullback section is China-only. These tests render the macro with
the call each country page makes and pin the dialog opener, the labelled
title, the backdrop close, and the close button to the shell text from before
that section (5267c66846e). They are not a snapshot of the dialog body.
"""
from __future__ import annotations

import re
import sys
import types
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]

# Shell text from templates/_risk_radar_dlg.html.j2 at 5267c66846e. The pullback
# section was inserted after this close button; these lines did not change.
_BASE_SHELL = """\
{% macro t(en, zh='') -%}
<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh if zh else en }}</span>
{%- endmacro %}
{%- set c  = ctx if ctx else {} -%}
{%- set _px  = {'cn':'cnx','hk':'hkx','ca':'cax'}.get(mkt, 'cnx') -%}
{%- set _dlg = c.dlg if c.dlg else {} -%}
{%- set _did = _dlg.id if _dlg.id else (_px ~ '-dlg-risk') -%}
{%- set _dcl = _dlg.cls if _dlg.cls else (_px ~ '-dlg') -%}
{%- set _dcx = _dlg.close_js if _dlg.close_js else (_px ~ 'CloseDlg()') -%}
<div class="{{ _dcl }}" id="{{ _did }}" role="dialog" aria-modal="true" aria-labelledby="{{ _did }}-ttl">
  <div class="{{ _dcl }}-backdrop" onclick="{{ _dcx }}"></div>
  <span class="{{ _dcl }}-title" id="{{ _did }}-ttl">{{ t(c.title_en if c.title_en else 'Pullback Risk — Radar & Gauges', c.title_zh if c.title_zh else '回撤风险 — 雷达与仪表') }}</span>
  <button class="{{ _dcl }}-close" type="button" onclick="{{ _dcx }}" aria-label="Close">&#xd7;</button>
"""

# Call expressions copied from templates/hk.html.j2 and templates/canada.html.j2.
_CALLS = {
    "hk": (
        '{% import "_risk_radar_dlg.html.j2" as rrd %}'
        "{{ rrd.risk_radar_dlg('hk', (ms.radar if (ms is defined and ms) else none), "
        "((ms.radar.scares if (ms.radar is defined and ms.radar) else none) "
        "if (ms is defined and ms) else none), "
        "(radar_dlg if radar_dlg is defined else none)) }}"
    ),
    "ca": (
        '{% import "_risk_radar_dlg.html.j2" as rrd %}'
        "{{ rrd.risk_radar_dlg('ca', _rr, (_rr.get('scares') if _rr else none), "
        "(radar_dlg if radar_dlg is defined else none)) }}"
    ),
}

_FORBIDDEN = ("rrp", "pbx", "data-pb-", "mmPbExpire")

_DIALOG = re.compile(
    r'<div class="\w+-dlg" id="\w+-dlg-risk" role="dialog" '
    r'aria-modal="true" aria-labelledby="\w+-dlg-risk-ttl">'
)
_BACKDROP = re.compile(
    r'<div class="\w+-dlg-backdrop" onclick="\w+CloseDlg\(\)"></div>'
)
_TITLE = re.compile(
    r'<span class="\w+-dlg-title" id="\w+-dlg-risk-ttl">'
    r'<span class="l-en">.*?</span><span class="l-zh">.*?</span></span>'
)
_CLOSE = re.compile(
    r'<button class="\w+-dlg-close" type="button" onclick="\w+CloseDlg\(\)" '
    r'aria-label="Close">&#xd7;</button>'
)


def _load_builder_vms():
    """Import the country view-model builders.

    scripts/build_hk.py and scripts/build_canada.py import plotly at load.
    The view-model functions do not call it. A missing plotly is stubbed so
    this pin can still import them.
    """
    try:
        import plotly.graph_objects  # noqa: F401
    except ModuleNotFoundError:
        sys.modules.setdefault("plotly", types.ModuleType("plotly"))
        sys.modules.setdefault(
            "plotly.graph_objects", types.ModuleType("plotly.graph_objects")
        )
    from scripts.build_canada import _ca_scope_fx_context
    from scripts.build_canada import _radar_dlg_vm as ca_vm
    from scripts.build_hk import _radar_dlg_vm as hk_vm
    return hk_vm, ca_vm, _ca_scope_fx_context


def _payload(mkt: str) -> dict:
    """Arguments for the page call: the builder's radar dict and radar_dlg ctx."""
    hk_vm, ca_vm, scope_fx = _load_builder_vms()
    from tests.test_risk_radar_dlg_country_wiring import (
        _LATEST_CA,
        _LATEST_HK,
        _RD,
        _VM_CA,
        _VM_HK,
    )
    if mkt == "hk":
        return {"ms": {"radar": dict(_RD)}, "radar_dlg": hk_vm(_VM_HK, _LATEST_HK)}
    rd = dict(_RD)
    rd["fx_context"] = dict(_RD["fx_context"])
    scope_fx(rd)
    return {"_rr": rd, "radar_dlg": ca_vm(_VM_CA, _LATEST_CA)}


def _render(mkt: str) -> tuple[str, dict]:
    payload = _payload(mkt)
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    html = env.from_string(_CALLS[mkt]).render(**payload)
    return html, payload["radar_dlg"]


def _shell_parts(html: str) -> tuple[str, str, str, str]:
    """Dialog opener, backdrop close, labelled title, and close button."""
    dialog = _DIALOG.search(html)
    backdrop = _BACKDROP.search(html)
    title = _TITLE.search(html)
    close = _CLOSE.search(html)
    assert dialog and backdrop and title and close, "shell markup missing"
    return dialog.group(0), backdrop.group(0), title.group(0), close.group(0)


def _base_shell(mkt: str, ctx: dict) -> str:
    return Environment(autoescape=False).from_string(_BASE_SHELL).render(mkt=mkt, ctx=ctx)


@pytest.mark.parametrize("mkt", ["hk", "ca"])
def test_hk_ca_dialog_shell_matches_pre_pullback_macro(mkt):
    html, ctx = _render(mkt)
    for token in _FORBIDDEN:
        assert token not in html, token
    assert _shell_parts(html) == _shell_parts(_base_shell(mkt, ctx))
