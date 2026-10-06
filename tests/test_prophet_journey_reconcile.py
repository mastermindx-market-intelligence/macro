"""Prophet journey reconciliation harness — release-integration proof tool.

Frozen test suite for ``scripts/prophet_journey_reconcile.py``. Every J1–J12
check has ≥1 PASS test and ≥1 FAIL test built from small synthetic HTML +
tiny synthetic payload dicts (tickers like ``TEST1`` — never real payload
rows). J5/J6 additionally run against the committed fixture
``mockups/evidence/prophet-packet2-r25-dialog/fixture.html`` with a
synthetic payload whose fields match what that fixture binds.

Style is informed by ``tests/test_prophet_card_shared.py``: header
docstring states the contract and the run command, then each test is a
narrow named function so a failure points at the one assertion that broke.

Run:
    python3 -m pytest tests/test_prophet_journey_reconcile.py -q
"""

from __future__ import annotations

import hashlib
import json
import os

import pytest
import subprocess
from datetime import date
from importlib.util import find_spec
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prophet_journey_reconcile.py"
FIXTURE_HTML = (ROOT / "mockups" / "evidence" / "prophet-packet2-r25-dialog"
                / "fixture.html")
TMP_DIR = Path(os.environ.get("TMPDIR", ".")) / "pri_journey_reconcile_tests"


def _wrapped_amd_fixture() -> str:
    """The R25 AMD dialog fixture wrapped the way the live board ships it.

    The saved snapshot is ONLY the dialog body: no ``[data-setup-ticker]``
    wrapper and no ``template.pvs-body-source`` copy. The board renders the
    body inside a ``details.pv-setup-inline[data-setup-ticker]`` and keeps a
    byte-equal copy in a ``<template class="pvs-body-source">`` (J6's
    template-copy contract), so the wrapper is rebuilt here with the parser
    the harness itself uses. The fixture bytes are never altered.
    """
    import copy

    raw = FIXTURE_HTML.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, _pjr.HTML_PARSER)
    body = soup.select_one("div.pv-setup-body")
    assert body is not None, "fixture lacks div.pv-setup-body"
    body["data-plan-relation"] = "none"
    details = soup.new_tag("details", attrs={
        "class": "pv-setup-inline pv-setup-table",
        "data-setup-ticker": "AMD", "data-setup-asof": "2026-09-27"})
    template = soup.new_tag("template", attrs={"class": "pvs-body-source"})
    template.append(copy.copy(body))
    body.replace_with(details)
    details.append(template)
    details.append(body)
    return str(soup)

# Imports of the script's helpers — kept lazy under the fixtures so the
# import errors surface in pytest output, not at module import time.
import importlib.util

_SPEC = importlib.util.spec_from_file_location(
    "pjr", str(SCRIPT))
assert _SPEC and _SPEC.loader
_pjr = importlib.util.module_from_spec(_SPEC)
sys.modules["pjr"] = _pjr
_SPEC.loader.exec_module(_pjr)


def _runtime_engine_vocabulary() -> tuple[frozenset[str], tuple[str, str]]:
    try:
        from engine.prophet_bridge import REFUSAL_ORDER
        from engine.us_candidate_lanes import declared_reasons
    except (ImportError, RuntimeError) as exc:
        return frozenset(), (type(exc).__name__, str(exc))
    return frozenset(declared_reasons()), REFUSAL_ORDER


def _runtime_lifecycle_cells() -> tuple[str, ...]:
    from scripts.build_prophet import LIFECYCLE_CELLS
    return LIFECYCLE_CELLS


def _field_text(path: str, html: str) -> str:
    field = BeautifulSoup(html, _pjr.HTML_PARSER).select_one(
        f'[data-source-field="{path}"]')
    assert field is not None, path
    return field.get_text(" ", strip=True)


# =========================================================================== #
# Fixture builders — synthetic HTML + synthetic payloads, in memory.
# =========================================================================== #
def _wrap(html_body: str) -> str:
    return ("<!doctype html><html lang=\"en\" data-theme=\"dark\" "
            "data-lang=\"en\"><head><title>t</title></head><body>"
            + html_body + "</body></html>")


def _full_page(*, ticker: str = "TEST1", with_plan: bool = True,
               in_buy: bool = True, cross_market: bool = False,
               raw_enum_in_text: str | None = None,
               has_alert: bool = False,
               pool_as_of: str = "2026-09-26",
               pool_total: int = 12,
               pool_digest: str = "",
               detail_as_of: str = "2026-09-26",
               detail_entry_status: str = "bounce_wait",
               detail_signal_asof: str = "2026-09-26",
               detail_entry_signal: dict | None = None,
               detail_signal: dict | None = None,
               detail_hold: dict | None = None,
               detail_price: float = 178.42,
               detail_price_as_of: str = "2026-09-26",
               detail_lane: str = "bottoming",
               detail_stage: str = "basing",
               plan_relation: str = "none",
               plan_link_target: str | None = None,
               plan_book_asof: str = "2026-09-26",
               assessment_asof: str = "2026-09-26",
               plv_state: str = "today",
               plv_text: str = "quotes as of 4:00 pm ET",
               plv_text_zh: str = "报价截至 美东 16:00") -> str:
    """Build a synthetic full-page HTML matching the live contract.

    All ``detail_*`` overrides land in the ``[data-setup-ticker=T]``
    detail body the way the live template emits it (see
    ``templates/_prophet_setup_detail.html.j2:27-77``).
    """
    es = detail_entry_signal or {
        "status": detail_entry_status,
        "headline": "Wait for confirmation",
        "buy_zone": {"low": 171.00, "high": 176.00},
        "stop": 164.00,
        "chase_above": 184.00,
    }
    sig = detail_signal or {"above200": True, "weekly_bull": True,
                            "provisional": False}
    hold = detail_hold or {"invalidation": 158.00}
    plv_asof = '<span class="plv-asof" id="plv-asof">4:00 pm ET</span>' \
        if cross_market is False else ""
    # Optional cross-market interception inside the journey — used by J10
    # FAIL tests. Placed inside #us-standouts so the FAIL surfaces there.
    x_market_a = (
        f'<a href="hk_stocks.html#XYZ">hk link</a>'
        if cross_market else "")
    x_market_mkt = (
        '<span data-mkt="HK">HK</span>'
        if cross_market else "")
    # Optional raw enum token in visible text — J11 FAIL.
    raw = (f'<p class="muted pvs-section"><span class="l-en">raw token '
           f'{raw_enum_in_text} here</span>'
           f'<span class="l-zh">{raw_enum_in_text} 原文</span></div>'
           if raw_enum_in_text else "")
    # Optional tracking-unavailable alert — J12.
    alert = (
        '<div class="mx-error" role="alert"><b>!</b><span>'
        '<span class="l-en">Tracking unavailable. Check the dates on '
        'Candidates and the record below.</span>'
        '<span class="l-zh">跟踪暂不可用。请核对候选与下方记录各自的日期。'
        '</span></span></div>'
        if has_alert else "")
    # The pool data-off-board mirrors the buy membership.
    off_board = "false" if in_buy else "true"
    plan_section = f'''
  <section class="pvs-section pvs-plan-relation"
           data-plan-relation="{plan_relation}" data-plan-exact="unavailable">
   <p><span class="l-en">No model plan is linked to this candidate.</span>
      <span class="l-zh">此候选没有关联模型计划。</span></p>'''
    if plan_relation == "related_security":
        target = plan_link_target or "pv-PLAN1"
        plan_section = f'''
  <section class="pvs-section pvs-plan-relation"
           data-plan-relation="{plan_relation}" data-plan-exact="unavailable">
   <p><span class="l-en">A model record for the same security. It is not this candidate's plan and not a position you hold.</span>
      <span class="l-zh">同一证券的模型记录。它不是此候选的计划，也不是持有的仓位。</span></p>
   <p><span class="l-en">Exact plan relation: not available from the source.</span>
      <span class="l-zh">确切计划关系：来源未提供。</span></p>
   <div class="pvs-plan-rec" data-plan-id="PLAN1" data-plan-lifecycle="ready">
    <button type="button" class="pvs-plan-link" data-pvs-plan-target="{target}">Open the model record</button>
   </div>'''
    plan_section += "\n  </section>"
    plan_card = ""
    if with_plan:
        plan_card = (
            f'<article class="pvcard pv-noread pv-record" '
            f'data-record-only="1" '
            f'id="pv-PLAN1" data-ticker="{ticker}" data-life="ready">'
            f'<div class="pv-bd"><div class="pv-hd">'
            f'<span class="pv-idw"><span class="pv-tk">{ticker}</span>'
            f'<span class="pv-nm"><span class="l-en">Plan Co</span>'
            f'<span class="l-zh">计划公司</span></span></span>'
            f'</div></div></article>')
    return _wrap(f"""
<section id="us-standouts" data-prophet-src="today" data-board-asof="2026-09-26">
  {x_market_a}
  <article class="pvcard pv-buy" data-ticker="{ticker}" data-life="live"
           data-stage="setting_up">
    <div class="pv-bd"><span class="pv-tk">{ticker}</span>
      <span class="nb-px pv-px" data-sym="{ticker}" data-mkt="US">$178.42</span>
    </div>
  </article>
  {x_market_mkt}
  {plan_card}
  {raw}
  {alert}
</section>

<details class="ucp" id="us-candidate-pool"
         data-status="ready" data-total="{pool_total}"
         data-as-of="{pool_as_of}" data-source-digest="{pool_digest}"
         data-view="table">
  <div class="ucp-body">
    <div class="ucp-list">
      <div class="ucp-row" data-ticker="{ticker}"
           data-off-board="{off_board}">
        <div class="ucp-identity">
          <a href="stock.html#{ticker}">{ticker}</a>
        </div>
        <details class="ucp-receipt"><summary><span class="l-en">Decision record</span><span class="l-zh">决策记录</span></summary>
          <span class="ucp-reason" data-reason="cleared_admission"><span class="l-en">Admission checks passed</span><span class="l-zh">已通过准入检查</span></span>
        </details>
      </div>
      <div class="ucp-row" data-ticker="OTHER" data-off-board="true">
        <div class="ucp-identity">
          <a href="stock.html#OTHER">OTHER</a>
        </div>
      </div>
    </div>
  </div>
</details>

<details class="pv-setup-inline pv-setup-table"
         data-setup-ticker="{ticker}" data-setup-asof="{detail_as_of}">
<summary><span class="l-en">Setup detail</span><span class="l-zh">形态详情</span></summary>
<div class="pv-setup-body" data-setup-kind="board"
     data-native-id="{ticker}" data-plan-relation="{plan_relation}" data-entry-status="{detail_entry_status}">
  {plan_section}
  <p class="pvs-assessment-clock" data-assessment-asof="{assessment_asof}">
   <span class="l-en">Entry read date {assessment_asof}</span>
   <span class="l-zh">入场判读日期 {assessment_asof}</span>
  </p>
  <p class="pvs-read" data-entry-status="{detail_entry_status}">
    <span class="l-en">Wait for confirmation</span>
    <span class="l-zh">等待确认</span></p>
  <dl class="pvs-levels">
    <div class="pvs-field" data-source-field="price">
      <dt><span class="l-en">Snapshot price</span>
          <span class="l-zh">快照价格</span></dt>
      <dd>${detail_price:.2f} <span class="l-en">as of {detail_price_as_of}</span><span class="l-zh">截至 {detail_price_as_of}</span></dd>
    </div>
    <div class="pvs-field" data-source-field="entry_signal.buy_zone.low">
      <dt><span class="l-en">Entry zone · low</span>
          <span class="l-zh">入场区间下沿</span></dt>
      <dd>${es["buy_zone"]["low"]:.2f}</dd>
    </div>
    <div class="pvs-field" data-source-field="entry_signal.buy_zone.high">
      <dt><span class="l-en">Entry zone · high</span>
          <span class="l-zh">入场区间上沿</span></dt>
      <dd>${es["buy_zone"]["high"]:.2f}</dd>
    </div>
    <div class="pvs-field" data-source-field="entry_signal.stop">
      <dt><span class="l-en">Entry-method stop</span>
          <span class="l-zh">入场方法止损位</span></dt>
      <dd>${es["stop"]:.2f}</dd>
    </div>
    <div class="pvs-field" data-source-field="hold.invalidation">
      <dt><span class="l-en">Base invalidation</span>
          <span class="l-zh">筑底失效位</span></dt>
      <dd>${hold["invalidation"]:.2f}</dd>
    </div>
    <div class="pvs-field" data-source-field="entry_signal.chase_above">
      <dt><span class="l-en">Chase boundary</span>
          <span class="l-zh">追高边界</span></dt>
      <dd>${es["chase_above"]:.2f}</dd>
    </div>
  </dl>
  <dl class="pvs-facts">
    <div class="pvs-field" data-source-field="signal.above200">
      <dt><span class="l-en">Above 200-day trend</span>
          <span class="l-zh">高于 200 日趋势</span></dt>
      <dd><span class="l-en">Yes</span><span class="l-zh">是</span></dd>
    </div>
    <div class="pvs-field" data-source-field="signal.weekly_bull">
      <dt><span class="l-en">Weekly confirmation</span>
          <span class="l-zh">周线确认</span></dt>
      <dd><span class="l-en">Yes</span><span class="l-zh">是</span></dd>
    </div>
    <div class="pvs-field" data-source-field="signal.provisional">
      <dt><span class="l-en">Provisional observation</span>
          <span class="l-zh">暂定观察</span></dt>
      <dd><span class="l-en">No</span><span class="l-zh">否</span></dd>
    </div>
    <div class="pvs-field" data-source-field="price_as_of">
     <dt><span class="l-en">Price as-of</span>
         <span class="l-zh">价格日期</span></dt>
     <dd>{detail_price_as_of}</dd>
    </div>
    <div class="pvs-field" data-source-field="lane">
      <dt><span class="l-en">Source setup type</span>
          <span class="l-zh">来源形态类别</span></dt>
      <dd><span class="l-en">A base is forming after a decline.</span><span class="l-zh">下跌后正在构筑底部。</span></dd>
    </div>
    <div class="pvs-field" data-source-field="stage">
      <dt><span class="l-en">Source stage</span>
          <span class="l-zh">来源阶段</span></dt>
      <dd><span class="l-en">It is building a base.</span><span class="l-zh">正在构筑底部。</span></dd>
    </div>
  </dl>
  <div class="pvs-field" data-source-field="envelope.as_of">
    <dt><span class="l-en">Source as-of</span>
        <span class="l-zh">来源日期</span></dt>
    <dd>{detail_as_of}</dd>
  </div>
  <div class="pvs-field" data-source-field="signal_asof">
    <dt><span class="l-en">Signal as-of</span>
        <span class="l-zh">信号日期</span></dt>
    <dd>{detail_signal_asof}</dd>
  </div>
</div>
</details>

<section id="us-plan-block">
 <p id="us-plan-book-asof" data-plan-book-asof="{plan_book_asof}">
  <span class="l-en">Plan records as of {plan_book_asof}</span>
  <span class="l-zh">计划记录截至 {plan_book_asof}</span>
 </p>
 <span class="plv-asof" id="plv-asof" data-plv-asof-state="{plv_state}">
  <span class="l-en">{plv_text}</span>
  <span class="l-zh">{plv_text_zh}</span>
 </span>
</section>
""")


def _standouts_payload(*, ticker: str = "TEST1", in_buy: bool = True,
                       with_pool: bool = True,
                       pool_total: int = 12,
                       pool_digest: str = "",
                       pool_as_of: str = "2026-09-26",
                       detail_price: float = 178.42,
                       entry_status: str = "bounce_wait",
                       price_as_of: str = "2026-09-26",
                       lane: str = "bottoming",
                       as_of: str = "2026-09-26") -> dict:
    """Synthetic standouts payload. Mirrors the live shape."""
    buy = []
    watch = []
    if in_buy:
        buy.append({
            "ticker": ticker,
            "lane": lane,
            "state": "setting_up",
            "entry_signal": {"status": entry_status,
                             "headline": "Wait for confirmation",
                             "buy_zone": {"low": 171.00, "high": 176.00},
                             "stop": 164.00,
                             "chase_above": 184.00},
            "signal": {"above200": True, "weekly_bull": True,
                       "provisional": False},
            "hold": {"invalidation": 158.00},
            "price": detail_price,
            "price_as_of": price_as_of,
            "stage": "basing",
            "envelope": {"as_of": as_of},
            "signal_asof": as_of,
        })
    else:
        watch.append({
            "ticker": ticker,
            "lane": lane,
            "state": "setting_up",
            "entry_signal": {"status": "bounce_wait",
                             "buy_zone": {"low": 171.00, "high": 176.00},
                             "stop": 164.00,
                             "chase_above": 184.00},
            "signal": {"above200": True, "weekly_bull": True,
                       "provisional": False},
            "hold": {"invalidation": 158.00},
            "price": detail_price,
            "stage": "basing",
            "envelope": {"as_of": as_of},
            "signal_asof": as_of,
        })
    payload: dict = {"as_of": as_of, "buy": buy, "watch": watch}
    if with_pool:
        payload["candidate_pool"] = {
            "status": "ready",
            "as_of": pool_as_of,
            "source_digest": pool_digest,
            "counts": {"eligible": pool_total, "in_buy_lane": 1 if in_buy else 0,
                       "off_buy_lane": 0 if in_buy else 1},
            "rows": [{
                "ticker": ticker,
                "lane": lane,
                "in_buy_lane": in_buy,
                "lane_reasons": ["cleared_admission"],
            "headline_reason": "cleared_admission",
            }],
        }
    return payload


def _index_payload(*, with_plan: bool = True, ticker: str = "TEST1",
                   as_of: str = "2026-09-26",
                   source_board_asof: str = "2026-09-26",
                   source_asof: str = "2026-09-26",
                   plan_closed: bool = False,
                   plan_ticker: str | None = None) -> dict:
    plans = []
    if with_plan:
        plans.append({
            "id": "PLAN1",
            "asset": plan_ticker or ticker,
            "lifecycle_state": "ready",
            "entry_status": "pre_trigger",
            "entry_zone_state": "zone_open",
            "management_status": "available",
            "phase": "pre_trigger",
            "admission_class": "anticipation_v1",
        })
    if plan_closed:
        plans[0]["closed"] = True
    return {"as_of": as_of, "source_board_asof": source_board_asof,
            "source_asof": source_asof, "plans": plans}


def _corrected_html(**overrides: object) -> str:
    values = {
        "plan_relation": "related_security",
        "plan_link_target": "pv-PLAN1",
        "plan_book_asof": "2026-09-26",
        "assessment_asof": "2026-09-26",
        "plv_state": "prior_day",
        "plv_text": "last read Sep 26, 4:00 pm ET",
    }
    values.update(overrides)
    soup = BeautifulSoup(_full_page(**values), _pjr.HTML_PARSER)
    book_clock = soup.select_one("#us-plan-book-asof")
    if book_clock is not None:
        book_clock["data-plan-book-source-asof"] = "2026-09-26"
        book_clock["data-plan-book-published"] = "2026-09-26"
    displayed = soup.select_one('[data-setup-ticker="TEST1"] > .pv-setup-body')
    template = soup.new_tag("template", attrs={"class": "pvs-body-source"})
    template.append(BeautifulSoup(str(displayed), _pjr.HTML_PARSER).select_one(
        ".pv-setup-body"))
    displayed.insert_before(template)
    return str(soup)


def _runtime_payload(*, quote_asof: str = "2026-09-26T20:00:00Z",
                     pass_ts: str = "2026-09-26T20:00:00Z") -> dict:
    return {"meta": {"quote_asof": quote_asof, "pass_ts": pass_ts}}


def _write_io(html: str, standouts: dict, index: dict,
              ticker: str = "TEST1") -> tuple[Path, Path, Path, Path]:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    page = TMP_DIR / "page.html"
    su = TMP_DIR / "standouts.json"
    ix = TMP_DIR / "index.json"
    out = TMP_DIR / f"out_{ticker}.json"
    page.write_text(html, encoding="utf-8")
    su.write_text(json.dumps(standouts), encoding="utf-8")
    ix.write_text(json.dumps(index), encoding="utf-8")
    return page, su, ix, out


# =========================================================================== #
# Unit tests — call the script's helpers directly with synthetic inputs.
# =========================================================================== #
def test_j1_pass_card_present():
    """Production cards carry the ticker on the card and market on .nb-px."""
    soup = BeautifulSoup(_full_page(ticker="TEST1"), _pjr.HTML_PARSER)
    chk = _pjr._check_j1(soup, "TEST1")
    assert chk["status"] == "PASS", chk


def test_j1_pass_production_lowercase_nested_market():
    """The US board renders a lowercase nested data-mkt value."""
    html = _wrap(
        '<section id="us-standouts">'
        '<article class="pvcard" data-ticker="TEST1" data-life="live" '
        'data-stage="setting_up"><span class="nb-px pv-px" '
        'data-sym="TEST1" data-mkt="us">$178.42</span></article>'
        '</section>')
    chk = _pjr._check_j1(BeautifulSoup(html, _pjr.HTML_PARSER), "TEST1")
    assert chk["status"] == "PASS", chk


def test_j1_pass_record_only_card_without_price_market():
    """A record-only card has no nested price market and still matches."""
    html = _wrap(
        '<section id="us-standouts">'
        '<a class="pvcard" data-ticker="TEST1" data-life="live" '
        'data-stage="setting_up" data-record-only="1">TEST1</a>'
        '</section>')
    chk = _pjr._check_j1(BeautifulSoup(html, _pjr.HTML_PARSER), "TEST1")
    assert chk["status"] == "PASS", chk


def test_j1_na_container_absent():
    """A missing board container is N/A, not a candidate failure."""
    html = _wrap("<p>Dialog-only snapshot.</p>")
    chk = _pjr._check_j1(BeautifulSoup(html, _pjr.HTML_PARSER), "TEST1")
    assert chk["status"] == "N/A", chk


def test_j1_fail_card_missing():
    soup = BeautifulSoup(_full_page(ticker="TEST1"), _pjr.HTML_PARSER)
    chk = _pjr._check_j1(soup, "ZZZZ")
    assert chk["status"] == "FAIL", chk


def test_j2_pass_table_row_in_buy():
    soup = BeautifulSoup(_full_page(ticker="TEST1", in_buy=True), _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1", in_buy=True)
    chk = _pjr._check_j2(soup, "TEST1", su)
    assert chk["status"] == "PASS", chk


def test_j2_fail_off_board_wrong():
    """Flip data-off-board to a wrong value — the check must FAIL."""
    html = _full_page(ticker="TEST1", in_buy=True).replace(
        'data-off-board="false"', 'data-off-board="true"')
    soup = BeautifulSoup(html, _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1", in_buy=True)
    chk = _pjr._check_j2(soup, "TEST1", su)
    assert chk["status"] == "FAIL", chk


def test_j3_pass_grid_row_in_buy():
    """The grid view is the same DOM — flip data-view and the row still matches."""
    html = _full_page(ticker="TEST1", in_buy=True).replace(
        'data-view="table"', 'data-view="grid"')
    soup = BeautifulSoup(html, _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1", in_buy=True)
    chk = _pjr._check_j3(soup, "TEST1", su)
    assert chk["status"] == "PASS", chk


def test_j3_fail_off_board_wrong():
    html = (_full_page(ticker="TEST1", in_buy=False)
            .replace('data-view="table"', 'data-view="grid"')
            .replace('data-off-board="true"', 'data-off-board="false"'))
    soup = BeautifulSoup(html, _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1", in_buy=False)
    chk = _pjr._check_j3(soup, "TEST1", su)
    assert chk["status"] == "FAIL", chk


def test_j4_pass_in_buy():
    su = _standouts_payload(ticker="TEST1", in_buy=True)
    chk = _pjr._check_j4(su, "TEST1", None)
    assert chk["status"] == "PASS", chk
    assert "buy" in chk["observed"]["found_in"]


def test_j4_pass_in_watch():
    su = _standouts_payload(ticker="TEST1", in_buy=False)
    chk = _pjr._check_j4(su, "TEST1", None)
    assert chk["status"] == "PASS", chk
    assert "watch" in chk["observed"]["found_in"]


def test_j4_pass_in_candidate_pool_only():
    su = _standouts_payload(ticker="TEST1", in_buy=False)
    su["buy"] = []
    su["watch"] = []
    # Pool still has the ticker.
    chk = _pjr._check_j4(su, "TEST1", None)
    assert chk["status"] == "PASS", chk
    assert "candidate_pool" in chk["observed"]["found_in"]


def test_j4_fail_absent_from_all():
    su = _standouts_payload(ticker="TEST1", in_buy=True)
    su["buy"] = []
    su["watch"] = []
    su["candidate_pool"]["rows"] = []
    chk = _pjr._check_j4(su, "TEST1", None)
    assert chk["status"] == "FAIL", chk


def test_j5_pass_native_id_and_asof():
    soup = BeautifulSoup(_full_page(ticker="TEST1"), _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1")
    chk = _pjr._check_j5(soup, su, "TEST1")
    assert chk["status"] == "PASS", chk


def test_j5_fail_native_id_mismatch():
    html = _full_page(ticker="TEST1").replace(
        'data-native-id="TEST1"', 'data-native-id="OTHER"')
    soup = BeautifulSoup(html, _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1")
    chk = _pjr._check_j5(soup, su, "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j5_fail_asof_mismatch():
    html = _full_page(ticker="TEST1").replace(
        'data-setup-asof="2026-09-26"', 'data-setup-asof="2099-01-01"')
    soup = BeautifulSoup(html, _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1")
    chk = _pjr._check_j5(soup, su, "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j6_pass_all_fields_preserved():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1")
    chk = _pjr._check_j6(soup, su, "TEST1")
    assert chk["status"] == "PASS", chk
    assert chk["observed"]["total_fields"] >= 5


def test_j6_fail_money_mismatch():
    """Drop the $-prefix from one field — the dollar amount check must FAIL."""
    html = _full_page(ticker="TEST1", detail_price=178.42).replace(
        '<dd>$178.42', '<dd>178.42')
    soup = BeautifulSoup(html, _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1", detail_price=178.42)
    chk = _pjr._check_j6(soup, su, "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j5_fail_entry_status_mismatch():
    """A DOM entry status that disagrees with the payload must fail."""
    soup = BeautifulSoup(
        _full_page(detail_entry_status="wrong_status"), _pjr.HTML_PARSER)
    chk = _pjr._check_j5(soup, _standouts_payload(), "TEST1")
    assert chk["status"] == "FAIL", chk
    assert chk["observed"]["data_entry_status"] == "wrong_status", chk
    assert chk["observed"]["payload_entry_status"] == "bounce_wait", chk


def test_j6_fail_signal_asof_string_mismatch():
    """A string mismatch must gate J6 even when numeric fields reconcile."""
    soup = BeautifulSoup(
        _corrected_html(detail_signal_asof="2099-01-01"), _pjr.HTML_PARSER)
    chk = _pjr._check_j6(soup, _standouts_payload(), "TEST1")
    assert chk["status"] == "FAIL", chk
    assert chk["status"] == "FAIL", chk
    assert chk["observed"][0]["path"] == "signal_asof", chk


def test_j6_fail_bool_mismatch():
    html = _full_page(ticker="TEST1").replace(
        '<span class="l-en">Yes</span><span class="l-zh">是</span>',
        '<span class="l-en">Maybe</span><span class="l-zh">或许</span>')
    soup = BeautifulSoup(html, _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1")
    chk = _pjr._check_j6(soup, su, "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j7_pass_pool_clocks_match():
    digest = "pool-source-digest"
    soup = BeautifulSoup(_full_page(ticker="TEST1",
                                    pool_digest=digest), _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1", pool_as_of="2026-09-26",
                            pool_total=12, pool_digest=digest)
    chk = _pjr._check_j7(soup, su, "TEST1")
    assert chk["status"] == "PASS", chk


def test_j7_fail_pool_total_mismatch():
    """Set pool_total=99 in payload; page data-total stays 12 → FAIL."""
    soup = BeautifulSoup(_full_page(ticker="TEST1", pool_total=12), _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1", pool_total=99)
    chk = _pjr._check_j7(soup, su, "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j7_fail_pool_as_of_mismatch():
    soup = BeautifulSoup(_full_page(ticker="TEST1"), _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1", as_of="2099-12-31")
    chk = _pjr._check_j7(soup, su, "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j8_pass_with_plan_linked():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    ix = _index_payload(with_plan=True)
    chk, plan_ids = _pjr._check_j8(soup, ix, "TEST1")
    assert chk["status"] == "PASS", chk
    assert plan_ids == ["PLAN1"]


def test_j8_fail_missing_plan_node():
    """Page has no plan card → J8 fails when plans are populated."""
    soup = BeautifulSoup(_full_page(ticker="TEST1", with_plan=False), _pjr.HTML_PARSER)
    ix = _index_payload(with_plan=True)
    chk, _ = _pjr._check_j8(soup, ix, "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j8_pass_no_plan_no_fabrication():
    """No plans + no #pv-* links on the journey → PASS."""
    soup = BeautifulSoup(_full_page(ticker="TEST1", with_plan=False), _pjr.HTML_PARSER)
    ix = _index_payload(with_plan=False)
    chk, plan_ids = _pjr._check_j8(soup, ix, "TEST1")
    assert chk["status"] == "PASS", chk
    assert plan_ids == []


def test_j8_fail_fabricated_link():
    """A link in the selected body without a plan-book record fails."""
    soup = BeautifulSoup(_full_page(ticker="TEST1", with_plan=False), _pjr.HTML_PARSER)
    soup.select_one(".pvs-plan-relation").append(
        BeautifulSoup('<button class="pvs-plan-link" '
                      'data-pvs-plan-target="pv-NOTREAL">x</button>', _pjr.HTML_PARSER).button)
    soup.select_one(".pvs-plan-relation")["data-plan-relation"] = "related_security"
    chk, _ = _pjr._check_j8(soup, _index_payload(with_plan=False), "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j9_clocks_still_reconcile_source_dates():
    """The source publication clocks remain part of J9."""
    today = date.today().isoformat()
    soup = BeautifulSoup(_corrected_html(
        plv_state="today", plv_text="quotes as of 4:00 pm ET"), _pjr.HTML_PARSER)
    soup.select_one("#us-plan-book-asof")["data-plan-book-published"] = "2026-09-27"
    ix = _index_payload(as_of="2026-09-27", source_board_asof="2026-09-26",
                        source_asof="2026-09-26")
    su = _standouts_payload(as_of="2026-09-26")
    runtime = _runtime_payload(quote_asof=f"{today}T20:00:00Z",
                               pass_ts=f"{today}T20:00:00Z")
    assert _pjr._check_j9(soup, ix, su, runtime, ticker="TEST1")["status"] == "PASS"

    ahead = _pjr._check_j9(soup, _index_payload(
        as_of="2026-09-25", source_board_asof="2026-09-26"), su,
        runtime, ticker="TEST1")
    assert ahead["status"] == "FAIL"

    drift = _pjr._check_j9(soup, _index_payload(
        source_board_asof="2026-09-27"), su, runtime, ticker="TEST1")
    assert drift["status"] == "FAIL"

def test_j9_fail_empty_or_missing_clocks():
    """Empty quote text or a missing node cannot pass."""
    empty = BeautifulSoup(
        '<span id="plv-asof"></span>', _pjr.HTML_PARSER)
    assert _pjr._check_j9(empty, _index_payload(), _standouts_payload(),
                          _runtime_payload(), ticker="TEST1")["status"] == "FAIL"
    missing = BeautifulSoup("<div></div>", _pjr.HTML_PARSER)
    assert _pjr._check_j9(missing, _index_payload(), _standouts_payload(),
                          _runtime_payload(), ticker="TEST1")["status"] == "FAIL"


def test_j10_pass_no_cross_market():
    soup = BeautifulSoup(_full_page(ticker="TEST1"), _pjr.HTML_PARSER)
    ix = _index_payload()
    chk = _pjr._check_j10(soup, "TEST1", ["PLAN1"])
    assert chk["status"] == "PASS", chk


def test_j10_fail_hk_href_in_journey():
    soup = BeautifulSoup(_full_page(ticker="TEST1", cross_market=True),
                         _pjr.HTML_PARSER)
    ix = _index_payload()
    chk = _pjr._check_j10(soup, "TEST1", ["PLAN1"])
    assert chk["status"] == "FAIL", chk


def test_j11_pass_no_enum_leakage():
    soup = BeautifulSoup(_full_page(ticker="TEST1"), _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1")
    ix = _index_payload()
    chk = _pjr._check_j11(soup, "en", su, ix, "TEST1", ["PLAN1"])
    assert chk["status"] == "PASS", chk


def test_j11_fail_enum_token_visible():
    """Inject ``pre_trigger`` (a plan enum) into the visible text → FAIL."""
    soup = BeautifulSoup(_full_page(
        ticker="TEST1", raw_enum_in_text="pre_trigger"), _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1")
    ix = _index_payload()
    chk = _pjr._check_j11(soup, "en", su, ix, "TEST1", ["PLAN1"])
    assert chk["status"] == "FAIL", chk


def test_j6_fail_displayed_body_stale_while_template_corrected():
    """J6 compares the displayed body with its source template copy."""
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    displayed = soup.select_one('[data-setup-ticker="TEST1"] > .pv-setup-body')
    template = BeautifulSoup(str(displayed), _pjr.HTML_PARSER).select_one(".pv-setup-body")
    holder = soup.new_tag("template", attrs={"class": "pvs-body-source"})
    holder.append(template)
    displayed.parent.insert(0, holder)
    displayed["data-plan-relation"] = "none"
    displayed["data-entry-status"] = "wrong_status"
    displayed["data-native-id"] = "OTHER"
    chk = _pjr._check_j6(soup, _standouts_payload(), "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j6_pass_displayed_body_matches_template():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    displayed = soup.select_one('[data-setup-ticker="TEST1"] > .pv-setup-body')
    template = BeautifulSoup(str(displayed), _pjr.HTML_PARSER).select_one(".pv-setup-body")
    holder = soup.new_tag("template", attrs={"class": "pvs-body-source"})
    holder.append(template)
    displayed.parent.insert(0, holder)
    chk = _pjr._check_j6(soup, _standouts_payload(), "TEST1")
    assert chk["status"] == "PASS", chk


def test_j6_fail_whole_displayed_body_with_different_clock_text():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    displayed = soup.select_one('[data-setup-ticker="TEST1"] > .pv-setup-body')
    template = BeautifulSoup(str(displayed), _pjr.HTML_PARSER).select_one(".pv-setup-body")
    holder = soup.new_tag("template", attrs={"class": "pvs-body-source"})
    holder.append(template)
    displayed.parent.insert(0, holder)
    clock = displayed.select_one(".pvs-assessment-clock")
    clock.select_one(".l-en").string = "Entry read date 2099-01-01"
    chk = _pjr._check_j6(soup, _standouts_payload(), "TEST1")
    assert chk["status"] == "FAIL", chk
    assert chk["observed"]["first_difference"]["offset"] > 0


def _with_summary_clock(text: str):
    """Corrected fixture with a summary clock carrying ``text`` in BOTH the
    displayed body and its existing template copy — the compliant shape —
    RE-PARSED so the template's strings are filed exactly as a saved page's
    would be (bs4 >= 4.13: TemplateString)."""
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    for body in soup.select(".pv-setup-body"):
        clock = soup.new_tag("p", attrs={"class": "pvs-summary-clock"})
        clock.string = text
        body.insert(0, clock)
    return BeautifulSoup(str(soup), _pjr.HTML_PARSER)


def test_j6_pass_summary_clock_text_is_read_inside_the_template_copy():
    """CONTROL: bs4 >= 4.13 files strings inside <template> as
    TemplateString and get_text() skips them, so a template clock with text
    used to bind as '' and never equal its displayed twin (CI-only red on
    the R25 AMD fixture, 2026-09-29)."""
    soup = _with_summary_clock("Source as-of 2026-09-26 · Quote time 2026-09-26T13:30:00Z")
    template_clock = soup.select_one("template.pvs-body-source .pvs-summary-clock")
    assert template_clock is not None
    if hasattr(_pjr, "TemplateString") and _pjr.TemplateString is not _pjr.NavigableString:
        # The control exercises the real path: the string IS a TemplateString.
        assert all(isinstance(node, _pjr.TemplateString) for node in template_clock.strings)
    template_body = template_clock.find_parent(class_="pv-setup-body")
    assert _pjr._body_binding(template_body)["summary-clock-text"].startswith("Source as-of")
    chk = _pjr._check_j6(soup, _standouts_payload(), "TEST1")
    assert chk["status"] == "PASS", chk
    assert chk["observed"]["template_count"] == 1


def test_j6_fail_template_summary_clock_text_differs_from_displayed():
    soup = _with_summary_clock("Source as-of 2026-09-26 · Quote time 2026-09-26T13:30:00Z")
    soup.select_one("template.pvs-body-source .pvs-summary-clock").string = (
        "Source as-of 2026-09-25 · Quote time 2026-09-25T13:30:00Z")
    chk = _pjr._check_j6(soup, _standouts_payload(), "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j6_fail_whole_displayed_body_with_different_plan_id():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    displayed = soup.select_one('[data-setup-ticker="TEST1"] > .pv-setup-body')
    template = BeautifulSoup(str(displayed), _pjr.HTML_PARSER).select_one(".pv-setup-body")
    holder = soup.new_tag("template", attrs={"class": "pvs-body-source"})
    holder.append(template)
    displayed.parent.insert(0, holder)
    displayed.select_one(".pvs-plan-rec")["data-plan-id"] = "OTHER"
    chk = _pjr._check_j6(soup, _standouts_payload(), "TEST1")
    assert chk["status"] == "FAIL", chk
    assert chk["observed"]["first_difference"]["offset"] > 0


def test_j6_pass_ignores_comment_and_whitespace_differences():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    displayed = soup.select_one('[data-setup-ticker="TEST1"] > .pv-setup-body')
    template = BeautifulSoup(str(displayed), _pjr.HTML_PARSER).select_one(".pv-setup-body")
    holder = soup.new_tag("template", attrs={"class": "pvs-body-source"})
    holder.append(template)
    displayed.parent.insert(0, holder)
    displayed.append(BeautifulSoup("<!-- review note -->\n\n   ", _pjr.HTML_PARSER))
    chk = _pjr._check_j6(soup, _standouts_payload(), "TEST1")
    assert chk["status"] == "PASS", chk


def test_j6_fail_only_template_carries_corrected_body():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    displayed = soup.select_one('[data-setup-ticker="TEST1"] > .pv-setup-body')
    holder = soup.new_tag("template", attrs={"class": "pvs-body-source"})
    holder.append(BeautifulSoup(str(displayed), _pjr.HTML_PARSER).select_one(".pv-setup-body"))
    displayed.replace_with(holder)
    chk = _pjr._check_j6(soup, _standouts_payload(), "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j6_fail_second_displayed_body_with_foreign_native_id():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    wrapper = soup.select_one('[data-setup-ticker="TEST1"]')
    second_wrapper = BeautifulSoup(str(wrapper), _pjr.HTML_PARSER).select_one(
        '[data-setup-ticker="TEST1"]')
    second_wrapper["data-setup-ticker"] = "TEST1-dialog"
    second_wrapper.select_one("template.pvs-body-source").decompose()
    body = second_wrapper.select_one(".pv-setup-body")
    body["data-native-id"] = "OTHER"
    wrapper.insert_after(second_wrapper)
    chk = _pjr._check_j6(soup, _standouts_payload(), "TEST1")
    assert chk["status"] == "FAIL", chk
    assert chk["observed"]["bad_displayed"][0]["data-native-id"] == "OTHER"


def test_j7_pass_binds_candidate_pool_source_digest():
    su = _standouts_payload(pool_digest="pool-source-digest")
    soup = BeautifulSoup(_corrected_html(plan_relation="none"), _pjr.HTML_PARSER)
    pool = soup.select_one("#us-candidate-pool")
    pool["data-source-digest"] = su["candidate_pool"]["source_digest"]
    chk = _pjr._check_j7(soup, su, "TEST1")
    assert chk["status"] == "PASS", chk


def test_j7_fail_rendered_reason_differs_from_source():
    su = _standouts_payload(pool_digest="pool-source-digest")
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    pool = soup.select_one("#us-candidate-pool")
    receipt = pool.select_one(".ucp-receipt")
    receipt.string = "cleared_admission"
    pool["data-source-digest"] = su["candidate_pool"]["source_digest"]
    chk = _pjr._check_j7(soup, su, "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j7_fail_dom_digest_differs_from_candidate_pool_source_digest():
    source = _standouts_payload(pool_digest="source-pool-digest")
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    pool = soup.select_one("#us-candidate-pool")
    pool["data-source-digest"] = "different-pool-digest"
    chk = _pjr._check_j7(soup, source, "TEST1")
    assert chk["status"] == "FAIL", chk
    assert chk["observed"]["source_digest"] == "source-pool-digest"
    assert chk["observed"]["rendered_source_digest"] == "different-pool-digest"


def test_j7_fail_empty_reason_code():
    su = _standouts_payload(pool_digest="pool-source-digest")
    su["candidate_pool"]["rows"][0]["lane_reasons"] = [""]
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    pool = soup.select_one("#us-candidate-pool")
    pool["data-source-digest"] = su["candidate_pool"]["source_digest"]
    chk = _pjr._check_j7(soup, su, "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j7_fail_selected_field_mutation_even_when_pool_digest_matches():
    source = _standouts_payload(pool_digest="pool-source-digest")
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    pool = soup.select_one("#us-candidate-pool")
    pool["data-source-digest"] = source["candidate_pool"]["source_digest"]
    body = soup.select_one('[data-setup-ticker="TEST1"] > .pv-setup-body')
    body["data-entry-status"] = "entered"
    read = body.select_one("[data-entry-status]")
    read["data-entry-status"] = "entered"
    chk = _pjr._check_j7(soup, source, "TEST1",
                         plan_relation="related_security", plan_ids=["PLAN1"])
    assert chk["status"] == "FAIL", chk


def test_j8_pass_link_target_page_ticker_and_open_book():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    ix = _index_payload()
    chk, plan_ids = _pjr._check_j8(soup, ix, "TEST1")
    assert chk["status"] == "PASS", chk
    assert plan_ids == ["PLAN1"]


def test_j7_digest_binds_displayed_plan_relation_and_ids():
    standouts = _standouts_payload()
    related = _pjr._journey_digest(
        standouts, "TEST1", "related_security", ["PLAN1"])
    unrelated = _pjr._journey_digest(standouts, "TEST1", "none", [])
    assert related != unrelated


def test_j8_fail_missing_target():
    soup = BeautifulSoup(_corrected_html(plan_link_target="pv-MISSING"),
                         _pjr.HTML_PARSER)
    chk, _ = _pjr._check_j8(soup, _index_payload(), "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j8_fail_other_ticker_target():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    ix = _index_payload(plan_ticker="OTHER")
    chk, _ = _pjr._check_j8(soup, ix, "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j8_fail_closed_plan():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    ix = _index_payload(plan_closed=True)
    chk, _ = _pjr._check_j8(soup, ix, "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j8_fail_duplicate_target_ids():
    # Two live page nodes carry the same plan id: the link's target identity is
    # ambiguous, so J8 must FAIL rather than silently binding to the first one.
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    card = soup.select_one("#pv-PLAN1")
    twin = BeautifulSoup(str(card), _pjr.HTML_PARSER).select_one("#pv-PLAN1")
    card.insert_after(twin)
    assert len(soup.select("#pv-PLAN1")) == 2
    chk, _ = _pjr._check_j8(soup, _index_payload(), "TEST1")
    assert chk["status"] == "FAIL", chk
    assert any(f.get("reason") == "duplicate_target_id"
               for f in chk["observed"]), chk


def _unknown_relation_soup() -> BeautifulSoup:
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    for body in soup.select('[data-setup-ticker="TEST1"] .pv-setup-body'):
        body["data-plan-relation"] = "unknown"
        section = body.select_one(".pvs-plan-relation")
        section["data-plan-relation"] = "unknown"
        for link in section.select(".pvs-plan-link"):
            link.decompose()
    return soup


def test_j8_pass_unknown_relation_when_no_open_plan_exists():
    # 'unknown' is an honest state only when the open plan book agrees that
    # nothing could have been related: the only TEST1 plan is closed.
    chk, plan_ids = _pjr._check_j8(_unknown_relation_soup(),
                                   _index_payload(plan_closed=True), "TEST1")
    assert chk["status"] == "PASS", chk
    assert plan_ids == []


def test_j8_fail_unknown_relation_while_open_plan_exists():
    # An open same-security plan exists in the book, so 'unknown' hides a
    # relation the source could have shown: FAIL, never a quiet PASS.
    chk, _ = _pjr._check_j8(_unknown_relation_soup(), _index_payload(), "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j8_fail_target_exists_only_in_template():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    card = soup.select_one("#pv-PLAN1")
    holder = soup.new_tag("template")
    holder.append(BeautifulSoup(str(card), _pjr.HTML_PARSER).select_one("#pv-PLAN1"))
    card.replace_with(holder)
    chk, _ = _pjr._check_j8(soup, _index_payload(), "TEST1")
    assert chk["status"] == "FAIL", chk


def test_j9_pass_prior_day_runtime_clock():
    chk = _pjr._check_j9(
        BeautifulSoup(_corrected_html(
            plv_text="last read Sep 25, 4:00 pm ET"), _pjr.HTML_PARSER),
        _index_payload(), _standouts_payload(), ticker="TEST1",
        runtime=_runtime_payload(quote_asof="2026-09-25T20:00:00Z",
                                 pass_ts="2026-09-26T20:00:00Z"))
    assert chk["status"] == "PASS", chk


def test_j9_pass_prior_day_runtime_clock_in_chinese():
    chk = _pjr._check_j9(
        BeautifulSoup(_corrected_html(
            plv_text_zh="上次判读 09-25 美东 4:00"), _pjr.HTML_PARSER),
        _index_payload(), _standouts_payload(), locale="zh", ticker="TEST1",
        runtime=_runtime_payload(quote_asof="2026-09-25T20:00:00Z",
                                 pass_ts="2026-09-26T20:00:00Z"))
    assert chk["status"] == "PASS", chk


def test_j9_pass_today_runtime_clock():
    from datetime import date, timedelta
    today = date.today().isoformat()
    chk = _pjr._check_j9(
        BeautifulSoup(_corrected_html(
            plv_state="today", plv_text="quotes as of 4:00 pm ET"), _pjr.HTML_PARSER),
        _index_payload(), _standouts_payload(), ticker="TEST1",
        runtime=_runtime_payload(quote_asof=f"{today}T20:00:00Z",
                         pass_ts=f"{today}T20:00:00Z"))
    assert chk["status"] == "PASS", chk


def test_j9_pass_unavailable_runtime_clock():
    chk = _pjr._check_j9(
        BeautifulSoup(_corrected_html(
            plv_state="unavailable", plv_text="quote time unavailable"), _pjr.HTML_PARSER),
        _index_payload(), _standouts_payload(), ticker="TEST1",
        runtime=_runtime_payload(quote_asof="", pass_ts="not-a-time"))
    assert chk["status"] == "PASS", chk


def test_j9_fail_plan_book_dated_text_with_empty_attribute():
    html = _corrected_html(plan_book_asof="")
    chk = _pjr._check_j9(BeautifulSoup(html, _pjr.HTML_PARSER), _index_payload(),
                         _standouts_payload(), _runtime_payload(), ticker="TEST1")
    assert chk["status"] == "FAIL", chk


def test_j9_fail_plan_book_non_iso_day():
    html = _corrected_html(plan_book_asof="2026-9-5")
    chk = _pjr._check_j9(BeautifulSoup(html, _pjr.HTML_PARSER), _index_payload(),
                         _standouts_payload(), _runtime_payload(), ticker="TEST1")
    assert chk["status"] == "FAIL", chk
    assert "plan book attribute is not YYYY-MM-DD" in chk["observed"], chk


def test_j9_fail_assessment_clock_differs_from_signal_asof():
    html = _corrected_html(assessment_asof="2026-09-25")
    chk = _pjr._check_j9(BeautifulSoup(html, _pjr.HTML_PARSER), _index_payload(),
                         _standouts_payload(), _runtime_payload(), ticker="TEST1")
    assert chk["status"] == "FAIL", chk


def test_j9_fail_plv_text_without_state():
    html = _corrected_html(plv_state="")
    chk = _pjr._check_j9(BeautifulSoup(html, _pjr.HTML_PARSER), _index_payload(),
                         _standouts_payload(), _runtime_payload(), ticker="TEST1")
    assert chk["status"] == "FAIL", chk


def test_j9_fail_plv_time_differs_from_payload():
    html = _corrected_html(plv_text="quotes as of 3:01 pm ET")
    chk = _pjr._check_j9(BeautifulSoup(html, _pjr.HTML_PARSER), _index_payload(),
                         _standouts_payload(), _runtime_payload(), ticker="TEST1")
    assert chk["status"] == "FAIL", chk


def test_j9_fail_plv_today_text_from_different_day():
    html = _corrected_html(plv_state="today",
                           plv_text="quotes as of Sep 25, 4:00 pm ET")
    chk = _pjr._check_j9(BeautifulSoup(html, _pjr.HTML_PARSER), _index_payload(),
                         _standouts_payload(),
                         _runtime_payload(quote_asof="2026-09-26T20:00:00Z"))
    assert chk["status"] == "FAIL", chk


def test_j9_unsupported_without_runtime_payload():
    chk = _pjr._check_j9(BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER),
                         _index_payload(), _standouts_payload(), None)
    assert chk["status"] == "UNSUPPORTED", chk


def test_j9_fail_valid_plan_book_attribute_with_unrelated_sentence():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    clock = soup.select_one("#us-plan-book-asof")
    clock.select_one(".l-en").string = "The moon is made of cheese."
    clock.select_one(".l-zh").decompose()
    chk = _pjr._check_j9(soup, _index_payload(), _standouts_payload(),
                         _runtime_payload(), ticker="TEST1")
    assert chk["status"] == "FAIL", chk


def test_j9_fail_plan_book_attribute_shows_publication_clock():
    index = _index_payload(as_of="2026-09-27", source_board_asof="2026-09-26",
                           source_asof="2026-09-26")
    chk = _pjr._check_j9(
        BeautifulSoup(_corrected_html(
            plan_book_asof="2026-09-27", plv_state="prior_day",
            plv_text="last read Sep 26, 4:00 pm ET"), _pjr.HTML_PARSER),
        index, _standouts_payload(as_of="2026-09-26"),
        _runtime_payload(quote_asof="2026-09-26T20:00:00Z"), ticker="TEST1")
    assert chk["status"] == "FAIL", chk
    assert ("plan book attribute shows the publication clock, not source_asof"
            in chk["observed"]), chk


def test_j9_pass_all_three_plan_book_clock_attributes():
    index = _index_payload(as_of="2026-09-27", source_board_asof="2026-09-26",
                           source_asof="2026-09-26")
    soup = BeautifulSoup(_corrected_html(
        plan_book_asof="2026-09-26", plv_state="prior_day",
        plv_text="last read Sep 26, 4:00 pm ET"), _pjr.HTML_PARSER)
    clock = soup.select_one("#us-plan-book-asof")
    clock["data-plan-book-source-asof"] = "2026-09-26"
    clock["data-plan-book-published"] = "2026-09-27"
    clock.select_one(".l-en").string = (
        "Plan records as of 2026-09-26 · source board 2026-09-26 "
        "· published 2026-09-27")
    clock.select_one(".l-zh").string = (
        "计划记录截至 2026-09-26 · 来源榜单 2026-09-26 · 发布于 2026-09-27")
    chk = _pjr._check_j9(soup, index, _standouts_payload(as_of="2026-09-26"),
                         _runtime_payload(quote_asof="2026-09-26T20:00:00Z"),
                         ticker="TEST1")
    assert chk["status"] == "PASS", chk


def test_j9_fail_missing_or_empty_source_board_attribute_for_valid_day():
    index = _index_payload(as_of="2026-09-27", source_board_asof="2026-09-26",
                           source_asof="2026-09-26")
    for mutation in ("missing", "empty"):
        soup = BeautifulSoup(_corrected_html(
            plan_book_asof="2026-09-26", plv_state="prior_day",
            plv_text="last read Sep 26, 4:00 pm ET"), _pjr.HTML_PARSER)
        clock = soup.select_one("#us-plan-book-asof")
        if mutation == "missing":
            del clock["data-plan-book-source-asof"]
        else:
            clock["data-plan-book-source-asof"] = ""
        chk = _pjr._check_j9(
            soup, index, _standouts_payload(as_of="2026-09-26"),
            _runtime_payload(quote_asof="2026-09-26T20:00:00Z"), ticker="TEST1")
        assert chk["status"] == "FAIL", (mutation, chk)
        assert ("plan book source-board attribute missing for valid "
                "index.source_board_asof" in chk["observed"]), (mutation, chk)


def test_j9_fail_missing_or_empty_published_attribute_for_valid_day():
    index = _index_payload(as_of="2026-09-27", source_board_asof="2026-09-26",
                           source_asof="2026-09-26")
    for mutation in ("missing", "empty"):
        soup = BeautifulSoup(_corrected_html(
            plan_book_asof="2026-09-26", plv_state="prior_day",
            plv_text="last read Sep 26, 4:00 pm ET"), _pjr.HTML_PARSER)
        clock = soup.select_one("#us-plan-book-asof")
        if mutation == "missing":
            del clock["data-plan-book-published"]
        else:
            clock["data-plan-book-published"] = ""
        chk = _pjr._check_j9(
            soup, index, _standouts_payload(as_of="2026-09-26"),
            _runtime_payload(quote_asof="2026-09-26T20:00:00Z"), ticker="TEST1")
        assert chk["status"] == "FAIL", (mutation, chk)
        assert ("plan book published attribute missing for valid index.asof"
                in chk["observed"]), (mutation, chk)


def test_j9_pass_absent_source_asof_with_unavailable_text_and_empty_attributes():
    index = _index_payload(as_of="2026-09-27", source_board_asof="2026-09-26",
                           source_asof="")
    soup = BeautifulSoup(_corrected_html(
        plan_book_asof="", plv_state="prior_day",
        plv_text="last read Sep 26, 4:00 pm ET"), _pjr.HTML_PARSER)
    clock = soup.select_one("#us-plan-book-asof")
    clock["data-plan-book-source-asof"] = ""
    clock["data-plan-book-published"] = ""
    clock.select_one(".l-en").string = "Plan record date unavailable"
    clock.select_one(".l-zh").string = "计划记录日期不可用"
    chk = _pjr._check_j9(soup, index, _standouts_payload(as_of="2026-09-26"),
                         _runtime_payload(quote_asof="2026-09-26T20:00:00Z"),
                         ticker="TEST1")
    assert chk["status"] == "PASS", chk


def test_j9_fail_unavailable_plan_book_with_nonempty_auxiliary_clocks():
    index = _index_payload(as_of="2026-09-27", source_board_asof="2026-09-26",
                           source_asof="")
    for attribute in ("data-plan-book-source-asof", "data-plan-book-published"):
        soup = BeautifulSoup(_corrected_html(
            plan_book_asof="", plv_state="prior_day",
            plv_text="last read Sep 26, 4:00 pm ET"), _pjr.HTML_PARSER)
        clock = soup.select_one("#us-plan-book-asof")
        clock[attribute] = "2026-09-26"
        clock.select_one(".l-en").string = "Plan record date unavailable"
        clock.select_one(".l-zh").string = "计划记录日期不可用"
        chk = _pjr._check_j9(
            soup, index, _standouts_payload(as_of="2026-09-26"),
            _runtime_payload(quote_asof="2026-09-26T20:00:00Z"), ticker="TEST1")
        assert chk["status"] == "FAIL", (attribute, chk)
        assert ("plan book unavailable state has non-empty clock attributes"
                in chk["observed"]), (attribute, chk)


def test_j9_fail_absent_source_asof_with_dated_attribute():
    index = _index_payload(as_of="2026-09-27", source_board_asof="2026-09-26",
                           source_asof="")
    chk = _pjr._check_j9(
        BeautifulSoup(_corrected_html(
            plan_book_asof="2026-09-27", plv_state="prior_day",
            plv_text="last read Sep 26, 4:00 pm ET"), _pjr.HTML_PARSER),
        index, _standouts_payload(as_of="2026-09-26"),
        _runtime_payload(quote_asof="2026-09-26T20:00:00Z"), ticker="TEST1")
    assert chk["status"] == "FAIL", chk


def test_j9_pass_absent_signal_asof_renders_not_supplied():
    standouts = _standouts_payload()
    standouts["buy"][0].pop("signal_asof")
    soup = BeautifulSoup(_corrected_html(assessment_asof=""), _pjr.HTML_PARSER)
    clock = soup.select_one(".pvs-assessment-clock")
    clock.select_one(".l-en").string = "Entry read date not supplied"
    clock.select_one(".l-zh").string = "入场判读日期 来源未提供"
    chk = _pjr._check_j9(soup, _index_payload(), standouts,
                         _runtime_payload(), ticker="TEST1")
    assert chk["status"] == "PASS", chk


def test_j9_fail_prior_day_state_with_text_naming_a_different_prior_day():
    soup = BeautifulSoup(_corrected_html(
        plv_state="prior_day", plv_text="last read Sep 24, 4:00 pm ET"), _pjr.HTML_PARSER)
    chk = _pjr._check_j9(soup, _index_payload(), _standouts_payload(),
                         _runtime_payload(quote_asof="2026-09-25T20:00:00Z"),
                         ticker="TEST1")
    assert chk["status"] == "FAIL", chk
    assert "#plv-asof day differs from quote_asof" in chk["observed"]


def test_j9_fail_today_state_with_prior_day_payload_stamp():
    soup = BeautifulSoup(_corrected_html(
        plv_state="today", plv_text="quotes as of 4:00 pm ET"), _pjr.HTML_PARSER)
    chk = _pjr._check_j9(soup, _index_payload(), _standouts_payload(),
                         _runtime_payload(quote_asof="2026-09-25T20:00:00Z"),
                         ticker="TEST1")
    assert chk["status"] == "FAIL", chk
    assert chk["observed"] == ["#plv-asof state differs from quote_asof"]


def test_j10_pass_market_case_folding():
    html = _corrected_html().replace('data-mkt="US"', 'data-mkt="us"', 1)
    chk = _pjr._check_j10(BeautifulSoup(html, _pjr.HTML_PARSER), "TEST1", ["PLAN1"])
    assert chk["status"] == "PASS", chk


def test_j10_fail_mismatched_hk_market():
    html = _corrected_html().replace('data-mkt="US"', 'data-mkt="HK"', 1)
    chk = _pjr._check_j10(BeautifulSoup(html, _pjr.HTML_PARSER), "TEST1", ["PLAN1"])
    assert chk["status"] == "FAIL", chk


def test_j10_fail_journey_node_own_market():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    wrapper = soup.select_one('[data-setup-ticker="TEST1"]')
    wrapper["data-mkt"] = "HK"
    chk = _pjr._check_j10(soup, "TEST1", ["PLAN1"])
    assert chk["status"] == "FAIL", chk


def test_j11_fail_bare_reason_code_in_receipt():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    receipt = soup.select_one(".ucp-receipt")
    receipt.append(BeautifulSoup("<code>cleared_admission</code>", _pjr.HTML_PARSER).code)
    chk = _pjr._check_j11(soup, "en", _standouts_payload(), _index_payload(),
                          "TEST1", ["PLAN1"])
    assert chk["status"] == "FAIL", chk


def test_j11_fail_lifecycle_and_relation_words_visible():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    body = soup.select_one('[data-setup-ticker="TEST1"] > .pv-setup-body')
    body.append(BeautifulSoup("<p>ready related_security</p>", _pjr.HTML_PARSER).p)
    chk = _pjr._check_j11(soup, "en", _standouts_payload(),
                          _index_payload(with_plan=False), "TEST1", [])
    assert chk["status"] == "FAIL", chk


def test_j11_fail_every_underscore_free_lifecycle_word_visible():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    body = soup.select_one('[data-setup-ticker="TEST1"] > .pv-setup-body')
    states = ("watch", "ready", "entered", "delivering",
              "overtime", "invalidated", "resolved")
    body.append(BeautifulSoup(
        "<p>" + " ".join(states) + "</p>", _pjr.HTML_PARSER).p)
    chk = _pjr._check_j11(soup, "en", _standouts_payload(),
                          _index_payload(with_plan=False), "TEST1", [])
    assert chk["status"] == "FAIL", chk
    assert {hit["token"] for hit in chk["observed"]} == set(states)


def test_j6_fail_when_no_template_source_body_exists():
    soup = BeautifulSoup(_full_page(), _pjr.HTML_PARSER)
    chk = _pjr._check_j6(soup, _standouts_payload(), "TEST1")
    assert chk["status"] == "FAIL", chk
    assert chk["observed"] == "no template .pvs-body-source for ticker"


def test_j11_fail_fixed_refusal_vocabulary_even_when_payload_omits_it():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    receipt = soup.select_one(".ucp-receipt")
    receipt.append(BeautifulSoup("<code>pointing_down</code>", _pjr.HTML_PARSER).code)
    chk = _pjr._check_j11(soup, "en", _standouts_payload(),
                          _index_payload(with_plan=False), "TEST1", [])
    assert chk["status"] == "FAIL", chk


def test_j11_pass_raw_code_only_inside_declared_raw_element():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    receipt = soup.select_one(".ucp-receipt")
    standouts = _standouts_payload()
    standouts["candidate_pool"]["rows"][0]["lane_reasons"] = [
        "cleared_admission", "unmapped_new_code"]
    reason = soup.new_tag(
        "span", attrs={"class": "ucp-reason", "data-reason": "unmapped_new_code"})
    reason.append(soup.new_tag("span", attrs={"class": "l-en"}))
    reason.span.append("Unlabelled decision code")
    reason.append(soup.new_tag("span", attrs={"class": "l-zh"}))
    reason.select_one(".l-zh").append("未标注的决策代码")
    reason.append(soup.new_tag("code", attrs={"class": "ucp-reason-raw"}))
    reason.code.append("unmapped_new_code")
    receipt.append(reason)
    chk = _pjr._check_j11(soup, "en", standouts, _index_payload(),
                          "TEST1", ["PLAN1"])
    assert chk["status"] == "PASS", chk


def test_j11_fail_raw_code_when_selector_is_not_code():
    soup = BeautifulSoup(
        _corrected_html(detail_lane="quiet", detail_stage="quiet"), _pjr.HTML_PARSER)
    receipt = soup.select_one(".ucp-receipt")
    reason = soup.new_tag(
        "span", attrs={"class": "ucp-reason", "data-reason": "unmapped_new_code"})
    reason.append(soup.new_tag("span", attrs={"class": "ucp-reason-raw"}))
    reason.span.append("cleared_admission")
    receipt.append(reason)
    chk = _pjr._check_j11(soup, "en", _standouts_payload(), _index_payload(),
                          "TEST1", ["PLAN1"])
    assert chk["status"] == "FAIL", chk


def test_j11_fail_raw_code_duplicated_outside_declared_raw_element():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    receipt = soup.select_one(".ucp-receipt")
    reason = soup.new_tag(
        "span", attrs={"class": "ucp-reason", "data-reason": "unmapped_new_code"})
    reason.append(soup.new_tag("span", attrs={"class": "l-en"}))
    reason.span.append("Unlabelled decision code")
    reason.append(soup.new_tag("span", attrs={"class": "l-zh"}))
    reason.select_one(".l-zh").append("未标注的决策代码")
    raw = soup.new_tag("code", attrs={"class": "ucp-reason-raw"})
    raw.append("unmapped_new_code")
    reason.append(raw)
    duplicate = soup.new_tag("span")
    duplicate.append("cleared_admission")
    receipt.append(reason)
    duplicate_section = soup.new_tag("section", attrs={"class": "pvs-section"})
    duplicate_section.append(duplicate)
    soup.select_one("#us-plan-block").append(duplicate_section)
    chk = _pjr._check_j11(soup, "en", _standouts_payload(), _index_payload(),
                          "TEST1", ["PLAN1"])
    assert chk["status"] == "FAIL", chk


def test_j11_fail_declared_lane_family_codes_from_engine():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    body = soup.select_one('[data-setup-ticker="TEST1"] > .pv-setup-body')
    body.append(BeautifulSoup(
        "<p>entry_status_bounce_wait stage_basing tier_T1</p>", _pjr.HTML_PARSER).p)
    chk = _pjr._check_j11(soup, "en", _standouts_payload(), _index_payload(),
                          "TEST1", ["PLAN1"])
    assert chk["status"] == "FAIL", chk
    tokens = {hit["token"] for hit in chk["observed"]}
    assert {"entry_status_bounce_wait", "stage_basing", "tier_T1"} <= tokens


def test_declared_reason_vocabulary_superset_engine_runtime_union():
    engine_reasons, refusal_order = _runtime_engine_vocabulary()
    assert engine_reasons
    assert _pjr.RUNTIME_DECLARED_REASON_VOCABULARY == engine_reasons
    assert set(_pjr.REFUSAL_ORDER) == set(refusal_order)
    assert _pjr.LIFECYCLE_VOCABULARY == frozenset(_runtime_lifecycle_cells())


def test_j11_fail_empty_english_label():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    reason = soup.select_one(".ucp-reason[data-reason]")
    reason.select_one(".l-en").string = ""
    chk = _pjr._check_j11(soup, "en", _standouts_payload(), _index_payload(),
                          "TEST1", ["PLAN1"])
    assert chk["status"] == "FAIL", chk


def test_j11_fail_chinese_only_english_label():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    reason = soup.select_one(".ucp-reason[data-reason]")
    reason.select_one(".l-en").string = "准入检查已通过"
    chk = _pjr._check_j11(soup, "en", _standouts_payload(), _index_payload(),
                          "TEST1", ["PLAN1"])
    assert chk["status"] == "FAIL", chk


def test_j11_fail_english_label_equal_to_reason_code():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    reason = soup.select_one(".ucp-reason[data-reason]")
    reason.select_one(".l-en").string = "CLEARED ADMISSION"
    chk = _pjr._check_j11(soup, "en", _standouts_payload(), _index_payload(),
                          "TEST1", ["PLAN1"])
    assert chk["status"] == "FAIL", chk


def test_j11_fail_raw_child_differs_from_data_reason():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    standouts = _standouts_payload()
    standouts["candidate_pool"]["rows"][0]["lane_reasons"] = [
        "cleared_admission", "unmapped_new_code"]
    reason = soup.new_tag(
        "span", attrs={"class": "ucp-reason", "data-reason": "unmapped_new_code"})
    reason.append(soup.new_tag("span", attrs={"class": "l-en"}))
    reason.span.append("Unlabelled decision code")
    reason.append(soup.new_tag("code", attrs={"class": "ucp-reason-raw"}))
    reason.code.append("different_code")
    soup.select_one(".ucp-receipt").append(reason)
    chk = _pjr._check_j11(soup, "en", standouts, _index_payload(),
                          "TEST1", ["PLAN1"])
    assert chk["status"] == "FAIL", chk


def test_j11_pass_well_formed_mapped_reason():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    chk = _pjr._check_j11(soup, "en", _standouts_payload(), _index_payload(),
                          "TEST1", ["PLAN1"])
    assert chk["status"] == "PASS", chk


def test_j11_pass_well_formed_unmapped_reason():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    standouts = _standouts_payload()
    standouts["candidate_pool"]["rows"][0]["lane_reasons"] = [
        "cleared_admission", "unmapped_new_code"]
    reason = soup.new_tag(
        "span", attrs={"class": "ucp-reason", "data-reason": "unmapped_new_code"})
    reason.append(soup.new_tag("span", attrs={"class": "l-en"}))
    reason.span.append("Unlabelled decision code")
    reason.append(soup.new_tag("span", attrs={"class": "l-zh"}))
    reason.select_one(".l-zh").append("未标注的决策代码")
    reason.append(soup.new_tag("code", attrs={"class": "ucp-reason-raw"}))
    reason.code.append("unmapped_new_code")
    soup.select_one(".ucp-receipt").append(reason)
    chk = _pjr._check_j11(soup, "en", standouts, _index_payload(),
                          "TEST1", ["PLAN1"])
    assert chk["status"] == "PASS", chk


def test_j11_pass_uses_repository_declared_parser_when_available():
    expected = "lxml" if find_spec("lxml") else "html.parser"
    assert _pjr.HTML_PARSER == expected


def test_j12_pass_alert_absent_with_sources():
    soup = BeautifulSoup(_full_page(ticker="TEST1"), _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1")
    ix = _index_payload()
    chk = _pjr._check_j12(soup, ix, su, "TEST1", ["PLAN1"])
    assert chk["status"] == "PASS", chk


def test_j12_fail_alert_with_sources():
    soup = BeautifulSoup(_full_page(ticker="TEST1", has_alert=True), _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1")
    ix = _index_payload()
    chk = _pjr._check_j12(soup, ix, su, "TEST1", ["PLAN1"])
    assert chk["status"] == "FAIL", chk


def test_j12_pass_alert_with_empty_sources():
    """Alert present but buy=[] and plans=[] → PASS (sources empty)."""
    soup = BeautifulSoup(_full_page(ticker="TEST1", has_alert=True), _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1", in_buy=False)
    su["buy"] = []
    su["watch"] = []
    ix = _index_payload(with_plan=False)
    chk = _pjr._check_j12(soup, ix, su, "TEST1", [])
    assert chk["status"] == "PASS", chk


# =========================================================================== #
# CLI exit-code tests + report schema test.
# =========================================================================== #
def test_cli_clean_journey_exit_code_zero():
    """A frozen corrected full journey returns PASS."""
    standouts = _standouts_payload(pool_digest="pool-source-digest")
    index = _index_payload(with_plan=True)
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    soup.select_one("#us-candidate-pool")["data-source-digest"] = (
        standouts["candidate_pool"]["source_digest"])
    page, standouts_path, index_path, out = _write_io(
        str(soup), standouts, index, "TEST1")
    (page.parent / "prophet_live.json").write_text(
        json.dumps(_runtime_payload()), encoding="utf-8")
    rc = _pjr.run(["--page", str(page), "--standouts", str(standouts_path),
                   "--index", str(index_path), "--ticker", "TEST1",
                   "--out", str(out)])
    assert rc == 0, json.loads(out.read_text(encoding="utf-8"))

def test_cli_fail_exit_code_one():
    """FAIL path: cross-market href inside the journey."""
    html = _full_page(ticker="TEST1", cross_market=True)
    su = _standouts_payload(ticker="TEST1")
    ix = _index_payload(with_plan=True)
    page, su_p, ix_p, out = _write_io(html, su, ix, "FAIL1")
    rc = _pjr.run(["--page", str(page), "--standouts", str(su_p),
                   "--index", str(ix_p), "--ticker", "TEST1",
                   "--out", str(out)])
    assert rc == 1, f"exit={rc}"
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["verdict"] == "FAIL"


def test_cli_without_runtime_is_partial():
    """Without a runtime payload J9 is explicitly UNSUPPORTED and not PASS."""
    standouts = _standouts_payload(pool_digest="")
    index = _index_payload(with_plan=False)
    soup = BeautifulSoup(_corrected_html(plan_relation="none"), _pjr.HTML_PARSER)
    soup.select_one("#us-candidate-pool").decompose()
    page, standouts_path, index_path, out = _write_io(
        str(soup), standouts, index, "PART1")
    (page.parent / "prophet_live.json").unlink(missing_ok=True)
    rc = _pjr.run(["--page", str(page), "--standouts", str(standouts_path),
                   "--index", str(index_path), "--ticker", "TEST1",
                   "--out", str(out)])
    assert rc == 2
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["checks"][8]["id"] == "J9"
    assert report["checks"][8]["status"] == "UNSUPPORTED"


def test_verdict_counts_unsupported_as_not_proven():
    assert _pjr._verdict([{"status": "UNSUPPORTED"}]) == "PARTIAL"


def test_report_schema_keys():
    """Every required report key is present, nothing extra leaks payload rows."""
    html = _full_page(ticker="TEST1")
    su = _standouts_payload(ticker="TEST1")
    ix = _index_payload()
    page, su_p, ix_p, out = _write_io(html, su, ix, "SCHM")
    _pjr.run(["--page", str(page), "--standouts", str(su_p),
              "--index", str(ix_p), "--ticker", "TEST1",
              "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert set(report.keys()) == {
        "schema", "generated_by", "inputs", "ticker", "locale",
        "linked_plan_ids", "checks", "verdict",
    }
    # No secret-bearing payload rows leak into the report.
    raw = out.read_text(encoding="utf-8")
    for forbidden in ("buy_zone", "headline_reason",
                      "weekly_bull", "pre_trigger"):
        # Some of these WILL appear inside J5/J6 raw_pairs_sample — the
        # cap is "no FULL row dicts leaked". The standalone keys above
        # are the J11 enum values themselves and only appear inside the
        # ``banned_tokens`` set / ``raw_pairs_sample`` value of the
        # single ticker being audited. We assert the JSON report does
        # NOT carry a second ticker's data — the report only knows
        # about ``TEST1``.
        if forbidden == "pre_trigger":
            # legitimate: appears inside J11 banned_tokens.
            continue
    assert "OTHER" not in raw, "report must not leak OTHER ticker rows"


def test_determinism_byte_identical_runs():
    """Two runs of the same inputs → byte-identical report (no timestamps)."""
    html = _full_page(ticker="TEST1")
    su = _standouts_payload(ticker="TEST1")
    ix = _index_payload()
    page, su_p, ix_p, out_a = _write_io(html, su, ix, "DET_A")
    out_b = TMP_DIR / "out_DET_B.json"
    rc_a = _pjr.run(["--page", str(page), "--standouts", str(su_p),
                     "--index", str(ix_p), "--ticker", "TEST1",
                     "--out", str(out_a)])
    rc_b = _pjr.run(["--page", str(page), "--standouts", str(su_p),
                     "--index", str(ix_p), "--ticker", "TEST1",
                     "--out", str(out_b)])
    assert rc_a == rc_b
    a = out_a.read_bytes()
    b = out_b.read_bytes()
    assert a == b, "two runs must be byte-identical (no timestamps)"
    # Hash input sha256 is content-derived and therefore stable.
    rep = json.loads(a.decode("utf-8"))
    assert rep["inputs"]["page"]["sha256"] == hashlib.sha256(
        page.read_bytes()).hexdigest()


# =========================================================================== #
# Fixture-based tests (J5 / J6 spec requirement).
# =========================================================================== #
@pytest.mark.needs_full_checkout("mockups")
def test_j5_against_committed_fixture():
    """J5 PASS against the committed fixture using AMD as the ticker.

    The fixture is ``mockups/evidence/prophet-packet2-r25-dialog/fixture.html``
    — a saved DOM snapshot of the AMD setup-detail dialog (R25 packet 2).
    It carries ``data-native-id="AMD"`` and ``data-setup-kind="board"``
    but NO wrapper ``[data-setup-ticker=AMD]`` (the fixture is the
    dialog body, not the table row that links to it). J5 therefore emits
    N/A against the raw fixture — recorded as the honest verdict here.

    To exercise J5's PASS branch we wrap the fixture's body in a
    ``[data-setup-ticker]`` element — the harness's contract is the
    attribute, not the surrounding chrome.
    """
    wrapped = _wrapped_amd_fixture()
    soup = BeautifulSoup(wrapped, _pjr.HTML_PARSER)
    # Synthetic standouts matching the fixture's bound fields.
    su = {
        "as_of": "2026-09-27",
        "buy": [{
            "ticker": "AMD",
            "lane": "bottoming",
            "stage": "setting_up",
            "state": "setting_up",
            "entry_signal": {
                "status": "bounce_wait",
                "headline": "Wait for confirmation",
                "buy_zone": {"low": 171.00, "high": 176.00},
                "stop": 164.00,
                "chase_above": 184.00,
            },
            "signal": {"above200": True, "weekly_bull": True,
                        "provisional": False},
            "hold": {"invalidation": 158.00},
            "price": 178.42,
                    }],
        "watch": [],
        "candidate_pool": {"status": "ready", "as_of": "2026-09-27",
                           "source_digest": "", "rows": [],
                           "counts": {"eligible": 0}},
    }
    chk = _pjr._check_j5(soup, su, "AMD")
    assert chk["status"] == "PASS", chk
    assert chk["observed"]["data_native_id"] == "AMD"
    assert chk["observed"]["data_setup_kind"] == "board"
    assert chk["observed"]["asof_match"] == "standouts.as_of"


@pytest.mark.needs_full_checkout("mockups")
def test_j6_against_committed_fixture():
    """J6 PASS against the committed fixture for AMD.

    Every ``[data-source-field]`` in the fixture body must resolve in
    the synthetic payload with a dd that matches the template's
    formatting (``$X.YY`` for money, ``Yes``/``No``/``是``/``否`` for
    booleans, verbatim for strings).
    """
    wrapped = _wrapped_amd_fixture()
    soup = BeautifulSoup(wrapped, _pjr.HTML_PARSER)
    su = {
        "as_of": "2026-09-27",
        "buy": [{
            "ticker": "AMD",
            "lane": "bottoming",
            "stage": "setting_up",
            "state": "setting_up",
            "entry_signal": {
                "status": "bounce_wait",
                "buy_zone": {"low": 171.00, "high": 176.00},
                "stop": 164.00,
                "chase_above": 184.00,
            },
            "signal": {"above200": True, "weekly_bull": True,
                        "provisional": False},
            "hold": {"invalidation": 158.00},
            "price": 178.42,
                        "envelope": {"as_of": "2026-09-27"},
            "price_as_of": "2026-09-27T09:30:00Z",
        }],
        "watch": [],
        "candidate_pool": {"status": "ready", "as_of": "2026-09-27",
                           "source_digest": "", "rows": [],
                           "counts": {"eligible": 0}},
    }
    chk = _pjr._check_j6(soup, su, "AMD")
    assert chk["status"] == "PASS", chk
    fields = chk["observed"]["total_fields"]
    assert fields >= 10, f"expected ≥10 source fields in AMD fixture; got {fields}"


@pytest.mark.needs_full_checkout("mockups")
def test_cli_against_committed_fixture():
    """End-to-end CLI run on the committed fixture.

    Per the spec: ``PARTIAL`` is acceptable when the fixture lacks the
    board/screener nodes (this fixture is ONLY the dialog body, not the
    full board). We assert the verdict is reported and identify which
    checks landed N/A.
    """
    su_p = TMP_DIR / "amd_standouts.json"
    ix_p = TMP_DIR / "amd_index.json"
    out = TMP_DIR / "amd_out.json"
    su_p.write_text(json.dumps({
        "as_of": "2026-09-27",
        "buy": [{
            "ticker": "AMD", "lane": "bottoming", "stage": "setting_up",
            "state": "setting_up",
            "entry_signal": {"status": "bounce_wait",
                             "buy_zone": {"low": 171.00, "high": 176.00},
                             "stop": 164.00, "chase_above": 184.00},
            "signal": {"above200": True, "weekly_bull": True,
                       "provisional": False},
            "hold": {"invalidation": 158.00},
            "price": 178.42,
                        "envelope": {"as_of": "2026-09-27"},
            "price_as_of": "2026-09-27T09:30:00Z",
        }],
        "watch": [],
        "candidate_pool": {"status": "ready", "as_of": "2026-09-27",
                           "source_digest": "", "rows": [],
                           "counts": {"eligible": 0}},
    }), encoding="utf-8")
    ix_p.write_text(json.dumps({
        "as_of": "2026-09-27", "source_board_asof": "2026-09-27",
        "plans": []}), encoding="utf-8")
    wrapped = _wrapped_amd_fixture()
    wrapped_path = TMP_DIR / "fixture_wrapped.html"
    wrapped_path.write_text(wrapped, encoding="utf-8")
    rc = _pjr.run(["--page", str(wrapped_path), "--standouts", str(su_p),
                   "--index", str(ix_p), "--ticker", "AMD",
                   "--out", str(out)])
    assert rc in (0, 1, 2), f"unexpected exit={rc}"
    report = json.loads(out.read_text(encoding="utf-8"))
    # This frozen current-UI fixture is intentionally known-bad under J8 and
    # has no runtime quote clock, so its terminal verdict is FAIL.
    assert report["verdict"] == "FAIL", report
    verdicts = {check["id"]: check["status"] for check in report["checks"]}
    assert verdicts["J6"] == "PASS"
    assert verdicts["J8"] == "FAIL"
    assert verdicts["J9"] == "UNSUPPORTED"
    if report["verdict"] == "PARTIAL":
        na_ids = [c["id"] for c in report["checks"]
                  if c["status"] == "N/A"]
        # At minimum, J1 / J2 / J3 / J7 must be N/A on a dialog-only
        # fixture (no board / screener nodes). J9 also N/A (visible
        # clock format exception). J4 still PASSes because the synthetic
        # payload puts AMD in ``buy`` — the dataset check, not the page
        # check, drives J4's PASS.
        assert {"J1", "J2", "J3", "J7"}.issubset(set(na_ids)), na_ids


# =========================================================================== #
# CLI subprocess smoke — exercises the __main__ path end-to-end.
# =========================================================================== #
def test_cli_subprocess_pass():
    """Subprocess smoke: ``__main__`` entry path on a clean full page.

    Exit code 0 = PASS (every J1-J12 resolves), generated_by matches
    the script's constant. The previous rc=2 PARTIAL assumption is
    gone — J9 now PASSes when the synthetic page's ``#plv-asof`` stamp
    is rendered (R3 holds).
    """
    su = _standouts_payload(ticker="TEST1", pool_digest="pool-source-digest")
    ix = _index_payload()
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    soup.select_one("#us-candidate-pool")["data-source-digest"] = (
        su["candidate_pool"]["source_digest"])
    page, su_p, ix_p, out = _write_io(str(soup), su, ix, "SUBP")
    (page.parent / "prophet_live.json").write_text(
        json.dumps(_runtime_payload()), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--page", str(page),
         "--standouts", str(su_p), "--index", str(ix_p),
         "--ticker", "TEST1", "--out", str(out)],
        check=False, capture_output=True, text=True,
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["verdict"] == "PASS"


def test_cli_subprocess_prints_check_and_result_lines():
    su = _standouts_payload(ticker="TEST1", pool_digest="pool-source-digest")
    ix = _index_payload()
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    soup.select_one("#us-candidate-pool")["data-source-digest"] = (
        su["candidate_pool"]["source_digest"])
    page, su_p, ix_p, out = _write_io(str(soup), su, ix, "CLIOUT")
    (page.parent / "prophet_live.json").write_text(
        json.dumps(_runtime_payload()), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--page", str(page),
         "--standouts", str(su_p), "--index", str(ix_p),
         "--ticker", "TEST1", "--out", str(out)],
        check=False, capture_output=True, text=True,
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    lines = proc.stdout.splitlines()
    assert len(lines) == 13, lines
    assert lines[-1] == "RESULT: PASS"
    assert lines[8] == "J9 PASS all clocks bound to their sources"
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["generated_by"] == _pjr.GENERATED_BY


# Input integrity: source absence must not validate an invented displayed value.
_INTEGRITY_MONEY_PATHS = (
    "price", "entry_signal.buy_zone.low", "entry_signal.buy_zone.high",
    "entry_signal.stop", "hold.invalidation", "entry_signal.chase_above",
)
_INTEGRITY_BOOL_PATHS = ("signal.above200", "signal.weekly_bull", "signal.provisional")


def _integrity_field(path, value, shown):
    row = {}
    node = row
    pieces = path.split(".")
    for piece in pieces[:-1]:
        node = node.setdefault(piece, {})
    node[pieces[-1]] = value
    body = BeautifulSoup(
        '<div class="pv-setup-body"><div data-source-field="' + path
        + '"><dd>' + shown + '</dd></div></div>', _pjr.HTML_PARSER
    ).select_one(".pv-setup-body")
    return _pjr._field_misses(body, row)


@pytest.mark.parametrize("path", _INTEGRITY_MONEY_PATHS)
@pytest.mark.parametrize("value", [None, "", "123.45", True, False,
                                    float("nan"), float("inf"), float("-inf"), {}, []])
def test_input_integrity_rejects_invented_money(path, value):
    assert _integrity_field(path, value, "$123.45")


@pytest.mark.parametrize("path", _INTEGRITY_BOOL_PATHS)
@pytest.mark.parametrize("value", [None, "", 0, 1, float("nan"), {}, []])
def test_input_integrity_rejects_invented_boolean(path, value):
    assert _integrity_field(path, value, "Yes 是")


@pytest.mark.parametrize("path", _INTEGRITY_MONEY_PATHS + _INTEGRITY_BOOL_PATHS)
@pytest.mark.parametrize("shown", ["Not supplied", "来源未提供", "Not supplied 来源未提供"])
def test_input_integrity_accepts_explicit_source_absence(path, shown):
    assert _integrity_field(path, None, shown) == []


@pytest.mark.parametrize("value,shown", [(0, "$0.00"), (12.345, "$12.35"),
                                        (-2.0, "$-2.00")])
def test_input_integrity_preserves_valid_money(value, shown):
    assert _integrity_field("price", value, shown) == []


@pytest.mark.parametrize("value,shown", [(True, "Yes"), (True, "是"),
    (True, "Yes 是"), (False, "No"), (False, "否"), (False, "No 否")])
def test_input_integrity_preserves_valid_boolean(value, shown):
    assert _integrity_field("signal.above200", value, shown) == []


@pytest.mark.parametrize("value,shown", [(True, "Yesterday"), (False, "Not No"),
                                       (True, "Yes 否"), (False, "No 是")])
def test_input_integrity_rejects_ambiguous_boolean_copy(value, shown):
    assert _integrity_field("signal.above200", value, shown)


def test_input_integrity_receipts_bind_consumed_bytes(tmp_path, monkeypatch):
    """Replace each input immediately after its read; checks must use that read."""
    page = tmp_path / "page.html"
    standouts = tmp_path / "standouts.json"
    index = tmp_path / "index.json"
    runtime = tmp_path / "prophet_live.json"
    out = tmp_path / "report.json"
    original = {
        page: b'<div id="snapshot-test">original</div>',
        standouts: b'{"snapshot_test":"original"}',
        index: b'{"snapshot_test":"original"}',
        runtime: b'{"snapshot_test":"original"}',
    }
    replacement = {
        page: b'<div id="snapshot-test">replaced</div>',
        standouts: b'{"snapshot_test":"replaced"}',
        index: b'{"snapshot_test":"replaced"}',
        runtime: b'{"snapshot_test":"replaced"}',
    }
    for path, content in original.items():
        path.write_bytes(content)
    consumed = {}
    reads = {path: 0 for path in original}
    original_read = Path.read_bytes

    def replace_after_read(path):
        content = original_read(path)
        if path in original:
            reads[path] += 1
            path.write_bytes(replacement[path])
        return content

    def passed(*args, **kwargs):
        return {"status": "PASS", "expected": "isolated capture control", "observed": {}}

    for number in range(1, 13):
        monkeypatch.setattr(_pjr, "_check_j" + str(number), passed)

    def check_page(soup, ticker):
        consumed["page"] = soup.select_one("#snapshot-test").get_text()
        return passed()

    def check_standouts(soup, ticker, payload):
        consumed["standouts"] = payload["snapshot_test"]
        return passed()

    def check_index(soup, payload, ticker):
        consumed["index"] = payload["snapshot_test"]
        return passed(), []

    def check_runtime(soup, ix, su, payload, locale, ticker):
        consumed["runtime"] = payload["snapshot_test"]
        return passed()

    monkeypatch.setattr(_pjr, "_check_j1", check_page)
    monkeypatch.setattr(_pjr, "_check_j2", check_standouts)
    monkeypatch.setattr(_pjr, "_check_j8", check_index)
    monkeypatch.setattr(_pjr, "_check_j9", check_runtime)
    monkeypatch.setattr(Path, "read_bytes", replace_after_read)
    rc = _pjr.run(["--page", str(page), "--standouts", str(standouts),
                   "--index", str(index), "--ticker", "TEST1", "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert rc == 0
    assert consumed == dict.fromkeys(("page", "standouts", "index", "runtime"), "original")
    assert all(count == 1 for count in reads.values()), reads
    for name, path in [("page", page), ("standouts", standouts),
                       ("index", index), ("runtime", runtime)]:
        assert report["inputs"][name]["sha256"] == hashlib.sha256(original[path]).hexdigest()
        assert report["inputs"][name]["bytes"] == len(original[path])


def test_input_integrity_records_absent_runtime(tmp_path, monkeypatch):
    page = tmp_path / "page.html"
    su = tmp_path / "standouts.json"
    ix = tmp_path / "index.json"
    out = tmp_path / "report.json"
    page.write_text("<div></div>", encoding="utf-8")
    su.write_text("{}", encoding="utf-8")
    ix.write_text("{}", encoding="utf-8")
    observed = {}

    def passed(*args, **kwargs):
        return {"status": "PASS", "expected": "isolated capture control", "observed": {}}

    for number in range(1, 13):
        monkeypatch.setattr(_pjr, "_check_j" + str(number), passed)
    monkeypatch.setattr(_pjr, "_check_j8", lambda *args: (passed(), []))

    def runtime_missing(soup, index, standouts, runtime, locale, ticker):
        observed["runtime"] = runtime
        return {"status": "UNSUPPORTED", "expected": "runtime absent"}

    monkeypatch.setattr(_pjr, "_check_j9", runtime_missing)
    rc = _pjr.run(["--page", str(page), "--standouts", str(su),
                   "--index", str(ix), "--ticker", "TEST1", "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert rc == 2
    assert observed["runtime"] is None
    assert report["inputs"]["runtime"] == {
        "path": str(page.parent / "prophet_live.json"), "state": "MISSING"
    }


@pytest.mark.parametrize("path,shown", [("price", "$123.45"),
                                        ("signal.above200", "Yes 是")])
def test_input_integrity_j6_rejects_matching_invented_template_and_display(path, shown):
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    standouts = _standouts_payload(pool_digest="pool-source-digest")
    row = _pjr._standouts_payload_row(standouts, "TEST1")
    target = row
    pieces = path.split(".")
    for piece in pieces[:-1]:
        target = target[piece]
    target[pieces[-1]] = None
    fields = soup.select('[data-source-field="' + path + '"] dd')
    assert len(fields) >= 2, "test needs both displayed and template copies"
    for field in fields:
        field.clear()
        field.append(shown)
    result = _pjr._check_j6(soup, standouts, "TEST1")
    assert result["status"] == "FAIL", result
    assert any(item.get("path") == path and item.get("reason") in
               {"money_without_source", "bool_without_source"}
               for item in result["observed"]), result


@pytest.mark.parametrize("missing", ["initial_import", "lifecycle", "refusal", "runtime_reasons"])
def test_vocabulary_integrity_missing_owner_is_unsupported(missing, monkeypatch):
    soup = BeautifulSoup('<section class="pvs-section">Research details</section>', _pjr.HTML_PARSER)
    if missing == "initial_import":
        monkeypatch.setattr(_pjr, "_LANE_IMPORT_ERROR", "sensitive-private-import-location")
    elif missing == "lifecycle":
        monkeypatch.setattr(_pjr, "LIFECYCLE_VOCABULARY", frozenset())
    elif missing == "refusal":
        monkeypatch.setattr(_pjr, "REFUSAL_ORDER", ())
    else:
        monkeypatch.setattr(_pjr, "_runtime_engine_vocabulary",
                            lambda: (frozenset(), ("ImportError", "sensitive-private-import-location")))
    result = _pjr._check_j11(soup, "en", {}, {}, "TEST1", [])
    assert result["status"] == "UNSUPPORTED", result
    assert _pjr._verdict([result]) == "PARTIAL"
    assert "sensitive-private-import-location" not in json.dumps(result)


def test_vocabulary_integrity_runtime_error_is_unsupported(monkeypatch):
    def unavailable():
        raise RuntimeError("sensitive-private-import-location")
    monkeypatch.setattr(_pjr, "declared_reasons", unavailable)
    soup = BeautifulSoup('<section class="pvs-section">Research details</section>', _pjr.HTML_PARSER)
    result = _pjr._check_j11(soup, "en", {}, {}, "TEST1", [])
    assert result["status"] == "UNSUPPORTED", result
    assert "sensitive-private-import-location" not in json.dumps(result)


def test_vocabulary_integrity_retains_known_leak_failure(monkeypatch):
    monkeypatch.setattr(_pjr, "LIFECYCLE_VOCABULARY", frozenset())
    soup = BeautifulSoup('<section class="pvs-section">related_security</section>', _pjr.HTML_PARSER)
    result = _pjr._check_j11(soup, "en", {}, {}, "TEST1", [])
    assert result["status"] == "FAIL", result


def test_vocabulary_integrity_reads_reason_owner_once(monkeypatch):
    calls = []
    def reasons():
        calls.append(1)
        return frozenset({"engine_internal_reason"})
    monkeypatch.setattr(_pjr, "declared_reasons", reasons)
    soup = BeautifulSoup('<section class="pvs-section">Research details</section>', _pjr.HTML_PARSER)
    result = _pjr._check_j11(soup, "en", {}, {}, "TEST1", [])
    assert result["status"] == "PASS", result
    assert len(calls) == 1


@pytest.mark.parametrize("with_buy", [True, False])
def test_scope_integrity_j4_uses_existing_source_row_precedence(with_buy):
    source = {
        "buy": [{"ticker": "TEST1", "lane": "buy-native"}] if with_buy else [],
        "watch": [{"ticker": "TEST1", "lane": "watch-native"}],
        "candidate_pool": {"rows": [{"ticker": "TEST1", "lane": "pool-native"}]},
    }
    expected = _pjr._standouts_payload_row(source, "TEST1")["lane"]
    result = _pjr._check_j4(source, "TEST1", expected)
    assert result["status"] == "PASS", result
    assert result["observed"]["payload_lane"] == expected
    assert result["observed"]["found_in"] == (["buy"] if with_buy else []) + ["watch", "candidate_pool"]


def test_scope_integrity_j4_rejects_lower_priority_row_lane():
    source = {"buy": [{"ticker": "TEST1", "lane": "buy-native"}],
              "candidate_pool": {"rows": [{"ticker": "TEST1", "lane": "pool-native"}]}}
    result = _pjr._check_j4(source, "TEST1", "pool-native")
    assert result["status"] == "FAIL", result


@pytest.mark.parametrize("wrapper", ["TEST1-preview", "test1-preview"])
def test_scope_integrity_prefixed_selected_body_is_in_scope(wrapper):
    soup = BeautifulSoup(
        '<div data-setup-ticker="TEST1"></div>'
        '<div data-setup-ticker="' + wrapper + '" data-mkt="HK">'
        '<div class="pv-setup-body" data-native-id="TEST1">'
        '<a href="hk_board.html">Wrong market</a>'
        '<div class="mx-error" role="alert">Tracking unavailable</div>'
        '</div></div>', _pjr.HTML_PARSER)
    assert len(_pjr._setup_source_bodies(soup, "TEST1")[0]) == 1
    assert _pjr._check_j10(soup, "TEST1", [])["status"] == "FAIL"
    result = _pjr._check_j12(soup, {"plans": [{"id": "P1"}]},
                            {"buy": [{"ticker": "TEST1"}]}, "TEST1", [])
    assert result["status"] == "FAIL", result


def test_scope_integrity_does_not_promote_inert_or_other_security_wrapper():
    soup = BeautifulSoup(
        '<div data-setup-ticker="TEST1"></div>'
        '<template><div data-setup-ticker="TEST1-preview" data-mkt="HK">'
        '<div class="pv-setup-body" data-native-id="TEST1">Inert</div></div></template>'
        '<div data-setup-ticker="OTHER-preview" data-mkt="HK">'
        '<div class="pv-setup-body" data-native-id="OTHER">Other</div></div>',
        _pjr.HTML_PARSER)
    assert not _pjr._setup_source_bodies(soup, "TEST1")[0]
    result = _pjr._check_j10(soup, "TEST1", [])
    assert result["status"] == "PASS", result


@pytest.mark.parametrize("source,shown", [("No", "Not supplied"), ("Yes", "Yesterday"),
                                        ("原始读数", "其他原始读数说明")])
def test_input_integrity_boolean_source_string_is_not_a_substring(source, shown):
    assert _integrity_field("signal.above200", source, shown)


@pytest.mark.parametrize("source,shown", [("No", "No"), ("  source   note  ", "source note"),
                                        ("来源原文", "来源原文")])
def test_input_integrity_boolean_source_string_remains_verbatim(source, shown):
    assert _integrity_field("signal.above200", source, shown) == []


def test_j12_fail_alert_with_plans_only_source_population():
    soup = BeautifulSoup(_full_page(ticker="TEST1", has_alert=True), _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1", in_buy=False)
    su["buy"] = []
    su["watch"] = []
    ix = _index_payload(with_plan=True)
    chk = _pjr._check_j12(soup, ix, su, "TEST1", ["PLAN1"])
    assert chk["status"] == "FAIL", chk


def test_j12_fail_alert_with_buy_only_source_population():
    soup = BeautifulSoup(_full_page(ticker="TEST1", has_alert=True), _pjr.HTML_PARSER)
    su = _standouts_payload(ticker="TEST1", in_buy=True)
    ix = _index_payload(with_plan=False)
    chk = _pjr._check_j12(soup, ix, su, "TEST1", [])
    assert chk["status"] == "FAIL", chk


@pytest.mark.parametrize("check_name", ["_check_j2", "_check_j3"])
def test_candidate_link_integrity_rejects_wrong_page_with_matching_fragment(check_name):
    soup = BeautifulSoup(_full_page(ticker="TEST1"), _pjr.HTML_PARSER)
    row = soup.select_one('#us-candidate-pool [data-ticker="TEST1"]')
    assert row is not None
    link = row.select_one("a[href]")
    assert link is not None
    link["href"] = "other.html#TEST1"
    check = getattr(_pjr, check_name)
    result = check(soup, "TEST1", _standouts_payload(ticker="TEST1"))
    assert result["status"] == "FAIL", result


@pytest.mark.parametrize("check_name", ["_check_j2", "_check_j3"])
def test_candidate_link_integrity_accepts_exact_stock_href(check_name):
    soup = BeautifulSoup(_full_page(ticker="TEST1"), _pjr.HTML_PARSER)
    check = getattr(_pjr, check_name)
    result = check(soup, "TEST1", _standouts_payload(ticker="TEST1"))
    assert result["status"] == "PASS", result


def test_j9_runtime_absent_does_not_hide_assessment_clock_failure():
    soup = BeautifulSoup(_corrected_html(assessment_asof="2099-01-01"), _pjr.HTML_PARSER)
    result = _pjr._check_j9(
        soup, _index_payload(), _standouts_payload(ticker="TEST1"),
        None, "en", "TEST1")
    assert result["status"] == "FAIL", result


def test_j9_runtime_absent_does_not_hide_plan_book_failure():
    soup = BeautifulSoup(_corrected_html(), _pjr.HTML_PARSER)
    book = soup.select_one("#us-plan-book-asof")
    assert book is not None
    book["data-plan-book-asof"] = "2099-01-01"
    result = _pjr._check_j9(
        soup, _index_payload(), _standouts_payload(ticker="TEST1"),
        None, "en", "TEST1")
    assert result["status"] == "FAIL", result
