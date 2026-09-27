"""tests/test_transmission_cascade_monitor.py — TXI W4 Cascade Monitor render (deliverable D).

Renders templates/transmission.html.j2 with the chain-state fixture subset and asserts the
Cascade Monitor section:
  - renders one row per non-dormant chain, ordered expressed → propagating → arming
  - shows hop-progress dots + the "N of M links confirmed" line + the tier disclosure
  - dormant chains collapse to a single muted "Quiet:" line
  - receipts ride data-tip-en/zh, never title=; the word "validated" never appears
  - the whole section is baked CONDITIONALLY: absent/empty chains → it does not render
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIX = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "transmission" / "chain_state.json"
TEMPLATES = Path(__file__).resolve().parents[1] / "templates"

_C = {"blue": "#285FFF", "indigo": "#4559DC", "ink": "#0B1733", "text": "#344054",
      "muted": "#6F6F6F", "faint": "#A0A0A0", "red": "#D30B0B", "amber": "#F5AD42",
      "green": "#1a7f43", "grid": "#EAECF0", "card": "#FFFFFF", "bg": "#F7F8FA",
      "gold": "#C8A53B", "teal": "#1F8A70"}


class _NoneDict(dict):
    """Returns None for any missing attr/key (lets the unrelated page sections render
    with all-None fields instead of raising, so we can exercise the monitor in isolation)."""
    def __getattr__(self, k):
        return self.get(k)

    def __getitem__(self, k):
        return dict.get(self, k, None)


def _nd(**kw):
    return _NoneDict(**kw)


def _render(chains):
    pytest.importorskip("jinja2")
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    S = _nd(rates=_nd(direction="stable", regime="neutral"),
            inflation=_nd(direction="steady"), expectations=_nd(anchoring="anchored"))
    tx = _nd(state=S, chains=[], scenarios=[], headwinds=[], tailwinds=[], transmission={},
             caveats=[], scored_status=_nd(en="x", zh="x"),
             inflation_decomposition=_nd(), breakeven_decomp=None)
    return env.get_template("transmission.html.j2").render(
        C=_C, as_of="2026-07-24", built="x", span="x", tx=tx, gate={}, yc=None,
        dx=None, hero=None, changes=None, chains=chains)


def _subset():
    from engine.transmission_publish import derive_display_subset
    return derive_display_subset(json.loads(FIX.read_text(encoding="utf-8")))


def _monitor_segment(html: str) -> str:
    i = html.find("<!-- ===================== CASCADE MONITOR")
    assert i >= 0, "cascade monitor section marker not found"
    j = html.find("===================== SCENARIOS", i)
    return html[i:j]


def test_monitor_renders_rows_in_progress_order():
    html = _render(_subset())
    seg = _monitor_segment(html)
    import re
    tags = re.findall(r'cm-state-tag (\w+)"', seg)
    assert tags == ["expressed", "propagating", "arming"], tags
    assert seg.count('class="cm-row') == 3


def test_monitor_shows_links_line_and_tier_disclosure():
    seg = _monitor_segment(_render(_subset()))
    assert "links confirmed" in seg
    assert "blast radius" in seg
    assert "base rates accrue nightly" in seg          # tier honesty
    assert "早期监测——基准率逐夜累积" in seg          # zh tier honesty


def test_monitor_dormant_collapses_to_quiet_line():
    seg = _monitor_segment(_render(_subset()))
    assert seg.count("cm-quiet") == 1
    assert "Vol-regime shift" in seg   # the dormant chain name in the quiet line


def test_monitor_receipts_use_data_tip_not_title():
    seg = _monitor_segment(_render(_subset()))
    assert "data-tip-en=" in seg and "data-tip-zh=" in seg
    assert "title=" not in seg, "receipts must ride data-tip-*, never title="


def test_monitor_no_validated_claim():
    html = _render(_subset())
    assert "validated" not in html.lower()


def test_monitor_absent_when_chains_none():
    html = _render(None)
    # the section markup (eyebrow) must not render; only the CSS comment mentions it
    assert '<p class="cm-eyebrow">' not in html


def test_monitor_absent_when_no_chains_list():
    html = _render({"schema": "x", "chains": []})
    assert '<p class="cm-eyebrow">' not in html


# ── MO-J1A — affected-company continuation render-side assertions ────────
def _enriched_subset():
    """Render _subset() with a small VendorAliasTable that resolves the names
    in the fixture's blast channels. The fixture has these ticker names across
    its blast channels: AAPL, NVDA, XOM, CVX, FCX, SLB, COP, HAL, MOS, DVN,
    PLTR, RIVN, LCID, CRWD, SNOW, TSLA, AVGO, NOW, T, VZ, CCL, AAL, CVNA.
    Register each as an open-bounded store/* row.
    """
    from datetime import date as _date
    from engine.transmission_company_continuation import enrich_display_chains
    from lib.dataos.identity import VendorAliasTable

    sec_map = {
        "AAPL": "SEC:0:AAPL", "NVDA": "SEC:0:NVDA", "XOM": "SEC:0:XOM",
        "CVX": "SEC:0:CVX", "FCX": "SEC:0:FCX", "SLB": "SEC:0:SLB",
        "COP": "SEC:0:COP", "HAL": "SEC:0:HAL", "MOS": "SEC:0:MOS",
        "DVN": "SEC:0:DVN", "PLTR": "SEC:0:PLTR", "RIVN": "SEC:0:RIVN",
        "LCID": "SEC:0:LCID", "CRWD": "SEC:0:CRWD", "SNOW": "SEC:0:SNOW",
        "TSLA": "SEC:0:TSLA", "AVGO": "SEC:0:AVGO", "NOW": "SEC:0:NOW",
        "T": "SEC:0:T", "VZ": "SEC:0:VZ", "CCL": "SEC:0:CCL",
        "AAL": "SEC:0:AAL", "CVNA": "SEC:0:CVNA",
    }
    rows = [
        {"vendor": "store", "vendor_symbol": sym, "security_id": sid,
         "valid_from": None, "valid_to": None}
        for sym, sid in sec_map.items()
    ]
    aliases = VendorAliasTable.from_records(rows)
    return enrich_display_chains(_subset(), aliases, _date(2026, 7, 23))


def test_cos_render_linked_anchor_and_not_ranked():
    html = _render(_enriched_subset())
    seg = _monitor_segment(html)
    # Linked anchor href contains the Terminal analysis URL with the canonical six keys.
    assert "https://app.mastermind-x.com/analysis" in seg
    assert "symbol=AAPL" in seg
    assert "page=intelligence" in seg
    assert "mo_chain=" in seg
    assert "mo_channel=" in seg
    assert "mo_asof=" in seg
    assert "mo_security_id=" in seg
    # "not ranked" + zh token surface in the page (Tier-1 plain-language).
    assert "not ranked" in seg
    assert "非排名" in seg
    # The not-ranked label appears in the header of each cm-cos list.
    assert seg.count("cm-cos-ranknote") >= 1
    # The data-sid attribute rides each linked li.
    assert "data-sid=" in seg


def test_cos_render_unlinked_renders_plain_text_no_anchor():
    """Build a chains fixture that mixes resolved names (linked) with names
    absent from the alias table (unlinked, render as plain text without a CTA).
    """
    from datetime import date as _date
    from engine.transmission_company_continuation import enrich_display_chains
    from lib.dataos.identity import VendorAliasTable

    chains = {
        "schema": "transmission_chains_display.v1",
        "asof": "2026-07-23",
        "chains": [{
            "id": "test_ch",
            "label": {"en": "Test chain", "zh": "测试链"},
            "state": "propagating",
            "tier": "hypothesis",
            "hops": [],
            "blast": {
                "channel_a": {
                    "label": {"en": "Channel A", "zh": "通道 A"},
                    "n": 3,
                    "unevaluable": 5,
                    "names": ["AAPL", "UNKNOWN1", "NVDA", "UNKNOWN2"],
                    "cuts": {},
                },
            },
            "caveats": [],
        }],
    }
    # Alias table only knows AAPL/NVDA — UNKNOWN1/UNKNOWN2 will be unlinked.
    aliases = VendorAliasTable.from_records([
        {"vendor": "store", "vendor_symbol": "AAPL", "security_id": "SEC:0:AAPL",
         "valid_from": None, "valid_to": None},
        {"vendor": "store", "vendor_symbol": "NVDA", "security_id": "SEC:0:NVDA",
         "valid_from": None, "valid_to": None},
    ])
    enriched = enrich_display_chains(chains, aliases, _date(2026, 7, 23))
    html = _render(enriched)
    seg = _monitor_segment(html)
    # The unlinked span class appears for UNKNOWN1/UNKNOWN2 (membership
    # visible, no CTA).
    assert "cm-cos-plain" in seg, "unlinked names must render as cm-cos-plain"
    # The cm-cos-list ul carries a data attribute for the JS filter.
    assert "data-cos-list" in seg
    # The progressive-enhancement search input is present.
    assert seg.count('data-cos-q') >= 1
    # Plain unlinked names appear without an anchor — they ride <span>, not <a>.
    # Locate the cm-cos-list ul and assert that UNKNOWN1/UNKNOWN2 are inside a
    # plain span, NOT an <a>.
    import re
    list_match = re.search(r'<ul class="cm-cos-list" data-cos-list>(.*?)</ul>', seg, re.DOTALL)
    assert list_match, "cm-cos-list ul not found"
    inner = list_match.group(1)
    # UNKNOWN1 must be in cm-cos-plain span, not in an <a>.
    assert "UNKNOWN1" in inner
    assert "UNKNOWN2" in inner
    assert '<span class="cm-cos-plain">UNKNOWN1</span>' in inner
    assert '<span class="cm-cos-plain">UNKNOWN2</span>' in inner
    # AAPL and NVDA must ride an anchor with the Terminal URL.
    assert 'href="https://app.mastermind-x.com/analysis' in inner
    assert ">AAPL<" in inner
    assert ">NVDA<" in inner


def test_cos_render_unevaluable_count_text_preserved():
    html = _render(_enriched_subset())
    seg = _monitor_segment(html)
    # The fixture carries unevaluable=1590 for some channels, 938, 940, 1601, 1603, 1615.
    assert "1590" in seg
    assert "names could not be evaluated" in seg or "只无法评估" in seg


def test_cos_render_dormant_chain_has_no_cm_cos():
    """The fixture's vol_regime chain is dormant — it must NOT carry a cm-cos
    details block. The spec is explicit: dormant chains get no companies key,
    and the template asserts that.

    The 3 non-dormant fixture chains have 4 + 4 + 3 = 11 blast channels
    between them; each renders one cm-cos. The dormant chain renders 0."""
    html = _render(_enriched_subset())
    seg = _monitor_segment(html)
    assert seg.count('class="cm-cos"') == 11, "expected one cm-cos per blast channel on non-dormant chains"
    # And the dormant chain's label appears only in the cm-quiet line.
    assert seg.count("Vol-regime shift") == 1


def test_cos_render_no_title_attribute_carries_chinese():
    """ZH copy rides visible l-zh spans only; title= attributes never carry
    Chinese text (the cascade-monitor receipt rule applies to the new block
    too)."""
    html = _render(_enriched_subset())
    seg = _monitor_segment(html)
    import re
    titles = re.findall(r'title="([^"]*)"', seg)
    for t in titles:
        # every character in every title must NOT be a CJK ideograph
        for ch in t:
            assert not (0x4E00 <= ord(ch) <= 0x9FFF), f"title= carries CJK {t!r}"
            assert not (0x3400 <= ord(ch) <= 0x4DBF), f"title= carries CJK ext-A {t!r}"
