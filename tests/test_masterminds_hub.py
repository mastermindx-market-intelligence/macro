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
