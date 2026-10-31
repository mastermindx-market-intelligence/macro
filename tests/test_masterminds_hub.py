"""W23-L7 masterminds hub honesty guards.

F2 — the hub's frozen note asserted "Aggressive beats the S&P on CAGR in both backtest
halves" while the engine's own ``oos.robust`` flag is False for every committed profile
(``engine/active_alloc.py:191-192``); the derived note must only name robust profiles.
F2b — ``_verdict`` told Conservative "the full-sample CAGR also beats here" although the
committed record splices the 60/40 to 8.27 vs the profile's 7.82; the non-robust branch
must say it does not beat when it does not.
F1 — the hub printed the live leverage read (``gross_now``) beside only the build clock;
each card must carry the snapshot's ``asof`` (``2026-10-16`` at the seed).

Fixtures below are inline copies of the committed record (site/masterminds.html scorecard
rows + data/regime/masterminds_latest.json asof at seed 553625459ecc); they never read
site/ or data/.
"""
from __future__ import annotations

import html as html_mod
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
import pandas as pd

from scripts import build_masterminds as bmm

_ROOT = Path(__file__).resolve().parent.parent
_PKS = ("conservative", "moderate", "aggressive")
_ASOF = "2026-10-16"

# Seed's exact non-robust EN wording (byte-reference for the F2b regression guard).
_SEED_NONROBUST_EN = (
    "The robust, out-of-sample-stable edge is the SHARPE (~{m}\u00d7 the benchmark) and the "
    "drawdown; the full-sample CAGR also beats here, but that part is era-dependent (it does "
    "not win in both halves). This is genuine risk-adjusted alpha, levered \u2014 not just "
    "more risk."
)


def _committed_res():
    """The three res-shaped dicts of the committed record, inline."""
    sc = {
        "conservative": {"cagr": 7.82, "hodl_cagr": 10.78, "sharpe": 1.11, "hodl_sharpe": 0.62,
                         "maxdd": -17.3, "hodl_maxdd": -55.2, "years": 19.5},
        "moderate": {"cagr": 11.32, "hodl_cagr": 10.78, "sharpe": 1.05, "hodl_sharpe": 0.62,
                     "maxdd": -24.2, "hodl_maxdd": -55.2, "years": 19.5},
        "aggressive": {"cagr": 16.76, "hodl_cagr": 10.78, "sharpe": 0.97, "hodl_sharpe": 0.62,
                       "maxdd": -35.0, "hodl_maxdd": -55.2, "years": 19.5},
    }
    oos = {
        "conservative": {"first": {"cagr": 7.37, "hodl_cagr": 6.88, "beats_cagr": True},
                         "second": {"cagr": 8.28, "hodl_cagr": 9.69, "beats_cagr": False},
                         "robust": False},
        "moderate": {"first": {"cagr": 11.58, "hodl_cagr": 6.67, "beats_cagr": True},
                     "second": {"cagr": 11.06, "hodl_cagr": 15.07, "beats_cagr": False},
                     "robust": False},
        "aggressive": {"first": {"cagr": 19.04, "hodl_cagr": 6.67, "beats_cagr": True},
                       "second": {"cagr": 14.51, "hodl_cagr": 15.07, "beats_cagr": False},
                       "robust": False},
    }
    gross = {"conservative": 0.56, "moderate": 0.96, "aggressive": 1.69}
    res = {pk: {"scorecard": dict(sc[pk]), "oos": dict(oos[pk]), "gross_now": gross[pk],
                "asof": _ASOF} for pk in _PKS}
    res["conservative"]["bench6040"] = {"cagr": 8.27, "sharpe": 0.76, "maxdd": -31.4}
    return res


def _cards(res=None):
    res = res if res is not None else _committed_res()
    return [bmm._rich_card(pk, res[pk]) for pk in _PKS]


def _render(cards):
    """Render the hub exactly like build() does (globals td/tr, autoescape)."""
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr)
    except Exception:  # noqa: BLE001
        env.globals.update(td=lambda en: en, tr=lambda en: en)
    kw = {}
    if hasattr(bmm, "_honest_note"):
        note = bmm._honest_note(cards)
        kw = {"note_en": note[0], "note_zh": note[1]}
    return env.get_template("masterminds.html.j2").render(
        cards=cards, built="2026-10-19 21:00 UTC", C=bmm.C, **kw)


def _page_text(cards):
    """Unescaped hub text, raw html, and the per-card blocks."""
    page = _render(cards)
    blocks = re.findall(r'<a class="mm-card".*?</a>', page, re.S)
    return html_mod.unescape(page), page, blocks


def _note_spans(page):
    m = re.search(r'<div class="note"[^>]*>\s*<span class="l-en">(.*?)</span>'
                  r'.*?<span class="l-zh">(.*?)</span>', page, re.S)
    assert m, "derived note is not rendered inside an l-en/l-zh span twin"
    return html_mod.unescape(m.group(1)), html_mod.unescape(m.group(2))


def test_hub_note_does_not_claim_both_halves_when_no_profile_is_robust():
    text, _page, _blocks = _page_text(_cards())
    assert "in both backtest halves" not in text
    assert "no profile beats its benchmark in each half of the backtest" in text


def test_hub_note_names_only_profiles_whose_oos_flag_is_robust():
    res = _committed_res()
    res["moderate"]["oos"] = dict(res["moderate"]["oos"], robust=True)
    text, _page, _blocks = _page_text(_cards(res))
    assert "Moderate beats the S&P 500 on CAGR in both backtest halves" in text
    assert "no profile beats" not in text
    assert "Aggressive beats the S&P 500 on CAGR in both" not in text
    assert "Conservative beats" not in text


def test_rich_card_carries_the_engine_oos_flag():
    res = _committed_res()
    assert bmm._rich_card("aggressive", res["aggressive"])["robust"] is False
    res["aggressive"]["oos"] = dict(res["aggressive"]["oos"], robust=True)
    assert bmm._rich_card("aggressive", res["aggressive"])["robust"] is True
    del res["aggressive"]["oos"]
    assert bmm._rich_card("aggressive", res["aggressive"])["robust"] is False


def test_hub_note_is_bilingual():
    cards = _cards()
    _text, page, _blocks = _page_text(cards)
    en, zh = _note_spans(page)
    note = bmm._honest_note(cards)
    assert en == note[0] and zh == note[1]
    assert "进取档仅全样本跑赢标普500" in zh
    assert "保守档未跑赢60/40（SPY/IEF）：7.82% 对 8.27%" in zh
    assert "进取档在回测两个半段均跑赢" not in zh
    assert "实时" not in zh and "申报" not in zh


def test_hub_note_says_conservative_does_not_beat_its_benchmark():
    text, _page, _blocks = _page_text(_cards())
    assert "Conservative does not beat the 60/40 (SPY/IEF): 7.82% vs 8.27%" in text
    assert "Conservative beats" not in text


def test_hub_note_sharpe_range_is_derived_from_the_cards():
    en = bmm._honest_note(_cards())[0]
    assert "~1.5-1.7x" in en
    assert "1.5-2x" not in en
    res = _committed_res()
    res["conservative"]["scorecard"]["sharpe"] = 2 * res["conservative"]["bench6040"]["sharpe"]
    for pk in ("moderate", "aggressive"):
        res[pk]["scorecard"]["sharpe"] = 2 * res[pk]["scorecard"]["hodl_sharpe"]
    assert "~2.0x" in bmm._honest_note(_cards(res))[0]


def test_hub_template_has_no_frozen_profile_verdict():
    src = (_ROOT / "templates" / "masterminds.html.j2").read_text(encoding="utf-8")
    assert "Aggressive beats the S&P on CAGR" not in src
    assert "进取档在回测两个半段均跑赢标普" not in src


def test_hub_card_prints_the_committed_alloc_asof():
    _text, _page, blocks = _page_text(_cards())
    assert len(blocks) == 3
    for block, gross in zip(blocks, ("0.56x", "0.96x", "1.69x")):
        flat = html_mod.unescape(re.sub(r"<[^>]+>", "", block))
        assert gross in flat
        assert _ASOF in flat
    aggressive = blocks[-1]
    assert "1.69x" in aggressive and "2026-10-16" in aggressive


def test_hub_card_without_asof_still_renders():
    res = _committed_res()
    for pk in _PKS:
        del res[pk]["asof"]
    _text, _page, blocks = _page_text(_cards(res))
    joined = html_mod.unescape(re.sub(r"<[^>]+>", "", "".join(blocks)))
    assert "19.5y" in joined and "1.69x" in joined
    assert "Weights as of" not in joined
    assert "权重截至" not in joined
    assert "None" not in joined


def test_rich_card_carries_asof():
    res = _committed_res()
    assert bmm._rich_card("moderate", res["moderate"])["asof"] == _ASOF
    del res["moderate"]["asof"]
    assert bmm._rich_card("moderate", res["moderate"])["asof"] is None


def test_verdict_does_not_claim_a_full_sample_beat_it_does_not_have():
    res = _committed_res()
    sc = bmm._bench_scorecard("conservative", res["conservative"]["scorecard"],
                              res["conservative"]["bench6040"])[0]
    en, zh = bmm._verdict("conservative", res["conservative"]["oos"], sc)
    assert "also beats" not in en
    assert "does not beat the benchmark here (7.82% vs 8.27%)" in en
    assert "未跑赢基准（7.82% 对 8.27%）" in zh


def test_verdict_keeps_the_full_sample_beat_when_true():
    res = _committed_res()
    sc = bmm._bench_scorecard("moderate", res["moderate"]["scorecard"],
                              res["moderate"].get("bench6040"))[0]
    en = bmm._verdict("moderate", res["moderate"]["oos"], sc)[0]
    assert en == _SEED_NONROBUST_EN.format(m="1.7")

# ── W23-L14: detail page names the flat assets, prints the instrument, shows Time invested ──

# The committed Conservative alloc rows (data/regime/masterminds_latest.json mm_conservative
# at the seed: SPY 16.5, QQQ 16.5, HG=F 16.5, BTC-USD 6.5), inline per the lane rules.
_CONS_ALLOC = [
    {"asset": "SPY", "label_en": "S&P 500", "label_zh": "标普500", "weight": 16.5},
    {"asset": "QQQ", "label_en": "Nasdaq 100", "label_zh": "纳指100", "weight": 16.5},
    {"asset": "HG=F", "label_en": "Copper", "label_zh": "铜", "weight": 16.5},
    {"asset": "BTC-USD", "label_en": "Bitcoin", "label_zh": "比特币", "weight": 6.5},
]
_FLAT_EN = ("No position at the last rebalance: 7-10y Treasuries (IEF) · 20y+ Treasuries (TLT) "
            "· IG credit (LQD) · High-yield credit (HYG) · Gold (GC=F)")
_FLAT_ZH = ("上次再平衡无持仓: 中期国债 (IEF) · 长期国债 (TLT) · 投资级信用 (LQD) "
            "· 高收益信用 (HYG) · 黄金 (GC=F)")


def _detail_res(pk="conservative", alloc=None, tim=97.3):
    """A res dict shaped for _detail_vm; values copied from the seat probe render_detail.py.

    ``tim="absent"`` omits the time_in_market key entirely; ``tim=None`` sets it to None.
    """
    res = _committed_res()[pk]
    sc = dict(res["scorecard"])
    sc["avg_leverage"], sc["turnover_annual"] = 0.77, 8.44
    if tim != "absent":
        sc["time_in_market"] = tim
    idx = pd.date_range("2007-01-03", periods=5, freq="365D")
    sc["eq"] = pd.Series([1.0, 1.1, 1.2, 1.3, 1.4], index=idx)
    sc["hodl_eq"] = pd.Series([1.0, 1.05, 1.1, 1.15, 1.2], index=idx)
    sc["gross_lev"] = pd.Series([0.5, 0.8, 1.0, 0.9, res["gross_now"]], index=idx)
    return {"scorecard": sc, "bench6040": res.get("bench6040"), "oos": res["oos"],
            "alloc": [dict(a) for a in (alloc if alloc is not None else _CONS_ALLOC)],
            "gross_now": res["gross_now"], "asof": res["asof"]}


def _detail_page(vm):
    """Render the detail template exactly like build() does (globals td/tr, autoescape)."""
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr)
    except Exception:  # noqa: BLE001
        env.globals.update(td=lambda en: en, tr=lambda en: en)
    return env.get_template("mastermind_detail.html.j2").render(**vm, C=bmm.C)


def _alloc_card(page):
    """The live-book card: marker comment up to the scorecard h3."""
    i = page.index("<!-- ===== Live book + scorecard ===== -->")
    j = page.index("Backtest scorecard", i)
    return page[i:page.rindex("<h3>", i, j)]


def _score_grid(page):
    i = page.index('<div class="score"><div class="s">')
    return page[i:page.index('<div class="note b"', i)]


def _en(seg):
    seg = re.sub(r'<span class="l-zh">.*?</span>', "", seg, flags=re.S)
    seg = html_mod.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", seg)))
    return seg.replace(" :", ":").strip()


def _zh(seg):
    seg = re.sub(r'<span class="l-en">.*?</span>', "", seg, flags=re.S)
    seg = html_mod.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", seg)))
    return seg.replace(" :", ":").strip()


def _flat_line(page):
    for m in re.findall(r'<div class="sub faint">.*?</div>', _alloc_card(page), re.S):
        if "No position at the last rebalance" in m:
            return m
    return ""


def test_detail_names_the_assets_with_no_position():
    vm = bmm._detail_vm("conservative", _detail_res(), "2026-10-19 21:00 UTC")
    page = _detail_page(vm)
    assert _en(_flat_line(page)) == _FLAT_EN
    assert _alloc_card(page).count('class="allocrow"') == 4


def test_flat_alloc_helper_is_a_pure_set_difference():
    before = [dict(a) for a in _CONS_ALLOC]
    got = bmm._flat_alloc_vm(_CONS_ALLOC)
    assert got == [{"asset": "IEF", "label_en": "7-10y Treasuries", "label_zh": "中期国债"},
                   {"asset": "TLT", "label_en": "20y+ Treasuries", "label_zh": "长期国债"},
                   {"asset": "LQD", "label_en": "IG credit", "label_zh": "投资级信用"},
                   {"asset": "HYG", "label_en": "High-yield credit", "label_zh": "高收益信用"},
                   {"asset": "GC=F", "label_en": "Gold", "label_zh": "黄金"}]
    assert all("weight" not in d for d in got)
    assert _CONS_ALLOC == before
    full = [{"asset": a, "label_en": bmm.M.ASSET_LABEL[a][0], "label_zh": bmm.M.ASSET_LABEL[a][1],
             "weight": 10.0} for a in bmm.M.ASSETS]
    assert bmm._flat_alloc_vm(full) == []


def test_flat_copy_claims_no_cause():
    page = _detail_page(bmm._detail_vm("conservative", _detail_res(), "2026-10-19 21:00 UTC"))
    line = _flat_line(page)
    en, zh = _en(line).lower(), _zh(line)
    for w in ("signal", "bearish", "avoid", "sold", "exit", "negative", "because", "0%"):
        assert w not in en
    for w in ("信号", "看空", "回避", "卖出", "因为"):
        assert w not in zh


def test_full_book_renders_no_flat_section():
    alloc = [{"asset": a, "label_en": bmm.M.ASSET_LABEL[a][0], "label_zh": bmm.M.ASSET_LABEL[a][1],
              "weight": 10.0} for a in bmm.M.ASSETS]
    vm = bmm._detail_vm("conservative", _detail_res(alloc=alloc), "2026-10-19 21:00 UTC")
    assert vm["flat_alloc"] == []
    page = _detail_page(vm)
    assert "No position at the last rebalance" not in page
    assert "上次再平衡无持仓" not in page
    assert _alloc_card(page).count('class="allocrow"') == 9


def test_held_rows_print_their_instrument():
    page = _detail_page(bmm._detail_vm("conservative", _detail_res(), "2026-10-19 21:00 UTC"))
    rows = re.findall(r'<div class="allocrow">.*?</div>', page, re.S)
    assert [_en(r) for r in rows] == ["S&P 500 SPY 16.5%", "Nasdaq 100 QQQ 16.5%",
                                      "Copper HG=F 16.5%", "Bitcoin BTC-USD 6.5%"]
    for row, tk in zip(rows, ("SPY", "QQQ", "HG=F", "BTC-USD")):
        assert f'<span class="faint">{tk}</span>' in row


def test_empty_book_keeps_the_de_risked_line():
    vm = bmm._detail_vm("conservative", _detail_res(alloc=[]), "2026-10-19 21:00 UTC")
    page = _detail_page(vm)
    card = _alloc_card(page)
    assert "De-risked — mostly in T-bills." in _en(card)
    assert "已降险——主要持有短债。" in card
    assert 'class="allocrow"' not in card
    assert _flat_line(page) == ""
    assert "Gross exposure now" not in card
    assert [d["asset"] for d in vm["flat_alloc"]] == list(bmm.M.ASSETS)


def test_flat_line_is_bilingual():
    page = _detail_page(bmm._detail_vm("conservative", _detail_res(), "2026-10-19 21:00 UTC"))
    line = _zh(_flat_line(page))
    assert line == _FLAT_ZH
    assert "No position" not in line


def test_scorecard_prints_time_invested():
    page = _detail_page(bmm._detail_vm("conservative", _detail_res(), "2026-10-19 21:00 UTC"))
    grid = _score_grid(page)
    assert "Avg leverage 0.77x 8.44x turnover/yr Time invested 97.3%" in _en(grid)
    assert "在场时间 97.3%" in _zh(grid)


def test_scorecard_omits_the_cell_when_the_field_is_absent():
    for tim in ("absent", None):
        page = _detail_page(bmm._detail_vm(
            "conservative", _detail_res(tim=tim), "2026-10-19 21:00 UTC"))
        grid = _score_grid(page)
        assert "Time invested" not in grid and "在场时间" not in grid
        assert "None" not in grid
        assert "Avg leverage 0.77x 8.44x turnover/yr" in _en(grid)


def test_scorecard_grid_keeps_four_cells():
    for tim in (97.3, "absent"):
        page = _detail_page(bmm._detail_vm(
            "conservative", _detail_res(tim=tim), "2026-10-19 21:00 UTC"))
        assert _score_grid(page).count('<div><div class="k">') == 4


def test_china_shaped_vm_renders_no_flat_line():
    from scripts import build_china_masterminds as bcm
    res = _detail_res("moderate")
    res["alloc"] = [{"asset": "510300.SS", "label_en": "CSI 300", "label_zh": "沪深300",
                     "weight": 40.0},
                    {"asset": "511010.SS", "label_en": "China 5y Govt Bond",
                     "label_zh": "5年国债", "weight": 35.0}]
    vm = bcm._detail_vm("moderate", res, "2026-10-19 21:00 UTC")
    assert "flat_alloc" not in vm
    page = _detail_page(vm)
    card = _alloc_card(page)
    assert "No position at the last rebalance" not in card
    assert "None" not in card
    rows = re.findall(r'<div class="allocrow">.*?</div>', card, re.S)
    assert len(rows) == 2
    assert '<span class="faint">510300.SS</span>' in rows[0]
    assert '<span class="faint">511010.SS</span>' in rows[1]
    assert "Time invested 97.3%" in _en(_score_grid(page))
