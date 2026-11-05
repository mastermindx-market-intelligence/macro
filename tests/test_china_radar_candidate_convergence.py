"""China Divergence Radar — each candidate prints the convergence behind its rank.

RED-first (DESIGN W27B §SPEC 3): the candidate line drops `c.convergence`, the producer's
own sort key (engine/china_radar.py:645), so the three names read as an arbitrary list; and
`c.why_zh` must NEVER be wired because its neutral leg contradicts `c.why_en`
(engine/china_radar.py:648,652-653 — real row 600999.SS "lags cohort · alt-data neutral"
vs "落后同业 · 另类数据派发"). Fixtures are synthetic copies of the committed card shapes:
no data/ read, no network, no builder call.
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent


def _make_env():
    """Jinja2 environment mirroring tests/test_china_radar_venue.py::TestTemplateRender."""
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=False,
    )
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:  # noqa: BLE001
        env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)
    return env


def _card(**over):
    """A sector divergence card (committed Coal shape by default); no venue rows."""
    row = {
        "pair": "sector_flow->515220.SS", "signal_key": "sector_flow", "family": None,
        "signal_en": "Sector net-flow", "signal_zh": "板块净流入",
        "sector": "Coal", "sector_etf": "515220.SS",
        "sector_en": "Coal", "sector_zh": "煤炭",
        "sign": "negative", "strength": 0.62, "conviction100": 100,
        "signal_value": -4.3, "signal_dir": -1,
        "signal_detail_en": "Sector net-flow -4.3% (东财 board, daily)",
        "signal_detail_zh": "板块净流入 -4.3%（东财行业板块，当日）",
        "price_rs": 12.4, "price_rs_z": 1.8,
        "reliability": {"hit_rate": None, "n_resolved": 0, "basis": "unproven"},
        "candidates": [], "thesis": "Sector smart-money net-flow tends to lead price.",
        "hypothesis_en": "Coal's lead should fade.", "hypothesis_zh": "煤炭的领先应消退。",
    }
    row.update(over)
    return row


def _render(card, asof="2026-10-16"):
    radar = {
        "schema": "china_radar.v1", "is_context_only": True,
        "asof": asof, "built": "2026-10-16T00:00:00Z",
        "divergences": [card], "in_line": [],
        "n_active": 1, "n_pairs": 1,
        "disclaimer_en": "Context only.", "disclaimer_zh": "仅供参考。",
    }
    return _make_env().get_template("china_radar.html.j2").render(radar=radar, ledger=None)


def _cand_div(html):
    """The rendered candidate line only — nothing else on the card."""
    return html.split('<div class="cand">', 1)[1].split("</div>", 1)[0]


def test_candidate_convergence_values_render():
    """The committed Coal cohort: the signed value behind the ordering is printed."""
    card = _card(candidates=[
        {"ticker": "601088.SS", "name": "中国神华", "convergence": -0.523},
        {"ticker": "601225.SS", "name": "陕西煤业", "convergence": -0.486},
        {"ticker": "601898.SS", "name": "中煤能源", "convergence": -0.454},
    ])
    line = _cand_div(_render(card))
    for value in ("-0.52", "-0.49", "-0.45"):
        assert value in line, value
    assert "中国神华" in line and "601088.SS" in line
    assert '<span class="r-neg">-0.52</span>' in line
    # ONE bilingual label for the value per card, not one per name (density budget)
    assert line.count("alt-data convergence") == 1
    assert line.count("另类数据共振") == 1


def test_candidate_line_carries_no_emoji():
    """The candidate line opens with its bilingual label, not a pictograph."""
    card = _card(candidates=[
        {"ticker": "601088.SS", "name": "中国神华", "convergence": -0.523}])
    line = _cand_div(_render(card))
    assert not [c for c in line if ord(c) > 0xFFFF]
    assert line.lstrip().startswith("<span")


def test_positive_card_convergence_renders():
    """A positive cohort keeps its sign and the existing r-pos class."""
    card = _card(sign="positive", pair="sector_flow->512760.SS",
                 sector="Semiconductors", sector_etf="512760.SS",
                 sector_en="Semiconductors", sector_zh="半导体",
                 candidates=[
                     {"ticker": "600584.SS", "name": "长电科技", "convergence": 0.669},
                     {"ticker": "002371.SZ", "name": "北方华创", "convergence": 0.382},
                     {"ticker": "603501.SS", "name": "韦尔股份", "convergence": 0.243},
                 ])
    line = _cand_div(_render(card))
    assert '<span class="r-pos">+0.67</span>' in line
    assert "+0.38" in line and "+0.24" in line


def test_zero_and_missing_convergence_guarded():
    """0.0 is a real value and still prints; None / an absent key print an em dash."""
    card = _card(candidates=[
        {"ticker": "600000.SS", "name": "浦发银行", "convergence": 0.0},
        {"ticker": "600001.SS", "name": "河钢股份", "convergence": None},
        {"ticker": "600002.SS", "name": "齐鲁石化"},
    ])
    line = _cand_div(_render(card))
    assert "+0.00" in line
    assert "(600001.SS)—" in line
    assert "(600002.SS)—" in line


def test_why_zh_neutral_claim_is_not_shipped():
    """The contradicting zh leg stays unpublished; only the number is wired."""
    card = _card(candidates=[
        {"ticker": "600999.SS", "name": "招商证券", "convergence": 0.007,
         "why_en": "lags cohort · alt-data neutral",
         "why_zh": "落后同业 · 另类数据派发"},
    ])
    html = _render(card)
    assert "派发" not in html
    assert "落后同业" not in html
    assert "alt-data neutral" not in html
    assert "lags cohort" not in html
    assert "+0.01" in _cand_div(html)
