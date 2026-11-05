"""Forward-ledger rows table and CSI300/pre-2024 basis cells (CN reversal sleeve page).

templates/cn_reversal_sleeve.html.j2 renders the payload site/factordata/cn_reversal_sleeve.json:
  - ledger.graded.per_rebalance rows print newest-first, capped at 12, the CSI300-relative
    excess signed through the existing .pos/.neg helper, a cap note above 12 rows, and never
    a bare "None" in the table;
  - the re-derive block's second grid gains an independently guarded CSI300-relative basis
    cell and the pre-2024 baseline cell that the post-2024 caveat is contrasted with;
  - absent keys keep the page byte-identical to the pre-change render: no table, no cells.
"""
from __future__ import annotations

import copy
import random
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_ROOT = Path(__file__).resolve().parent.parent

_SIZING = {"sleeve_factor": 0.62, "radar_state": "risk-off", "radar_as_of": "2026-10-16",
           "can_force": False, "label_en": "Sleeve ×0.62 — CN drawdown radar: risk-off",
           "label_zh": "仓位 ×0.62 — CN回撤雷达：risk-off",
           "dominant_driver_en": "Breadth breakdown (all-boats)",
           "dominant_driver_zh": "广度普跌（普跌）"}
# Builder fallback shape (scripts/build_cn_reversal_sleeve.py:123-126): no dominant_driver keys.
_SIZING_FALLBACK = {"sleeve_factor": 1.0, "radar_state": None, "can_force": False,
                    "label_en": "Sleeve ×1.00 — CN drawdown radar: unavailable",
                    "label_zh": "仓位 ×1.00 — CN回撤雷达：不可用"}
_GRADED = {"n_rebalances": 45, "mean_excess_per_rebalance": 0.0357, "median_excess": 0.0361,
           "sharpe_ann": 2.72, "hit_vs_csi300": 0.7778, "hit_ci": [0.6373, 0.8746]}
# 61 committed rebalance dates; 45 graded rows (per_rebalance): 16 registered, not graded.
_REBALANCES = [
    "2026-07-01", "2026-07-02", "2026-07-03", "2026-07-07", "2026-07-08", "2026-07-10",
    "2026-07-13", "2026-07-14", "2026-07-15", "2026-07-16", "2026-07-17", "2026-07-20",
    "2026-07-21", "2026-07-23", "2026-07-24", "2026-07-27", "2026-07-28", "2026-07-29",
    "2026-07-30", "2026-07-31", "2026-08-03", "2026-08-04", "2026-08-05", "2026-08-06",
    "2026-08-07", "2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13", "2026-08-14",
    "2026-08-18", "2026-08-19", "2026-08-20", "2026-08-21", "2026-08-24", "2026-08-25",
    "2026-08-26", "2026-08-27", "2026-08-28", "2026-08-31", "2026-09-01", "2026-09-03",
    "2026-09-04", "2026-09-07", "2026-09-08", "2026-09-09", "2026-09-15", "2026-09-16",
    "2026-09-18", "2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24", "2026-09-29",
    "2026-09-30", "2026-10-08", "2026-10-09", "2026-10-13", "2026-10-14", "2026-10-15",
    "2026-10-16",
]
_PER_REBAL = [  # (rebalance_date, n_filled, sleeve_excess)
    ("2026-07-01", 291, 0.0567), ("2026-07-02", 302, 0.0926), ("2026-07-03", 293, 0.0848),
    ("2026-07-07", 292, 0.0962), ("2026-07-08", 291, 0.116), ("2026-07-10", 291, 0.0651),
    ("2026-07-13", 291, 0.1234), ("2026-07-14", 290, 0.1067), ("2026-07-15", 292, 0.0711),
    ("2026-07-16", 293, 0.0258), ("2026-07-17", 294, 0.0732), ("2026-07-20", 297, 0.0974),
    ("2026-07-21", 296, 0.0835), ("2026-07-23", 297, 0.0506), ("2026-07-24", 300, 0.1044),
    ("2026-07-27", 293, 0.0454), ("2026-07-28", 297, 0.0682), ("2026-07-29", 298, 0.05),
    ("2026-07-30", 299, 0.0795), ("2026-07-31", 299, 0.0418), ("2026-08-03", 299, 0.0419),
    ("2026-08-04", 299, 0.0361), ("2026-08-05", 346, 0.0138), ("2026-08-06", 338, 0.0179),
    ("2026-08-07", 338, 0.0113), ("2026-08-10", 337, 0.0079), ("2026-08-11", 336, 0.0029),
    ("2026-08-12", 336, -0.0314), ("2026-08-13", 336, -0.0126), ("2026-08-14", 335, -0.0025),
    ("2026-08-18", 332, -0.0171), ("2026-08-19", 332, 0.0261), ("2026-08-20", 333, 0.0443),
    ("2026-08-21", 333, 0.0169), ("2026-08-24", 332, 0.0384), ("2026-08-25", 332, 0.0245),
    ("2026-08-26", 279, 0.0122), ("2026-08-27", 329, 0.0072), ("2026-08-28", 331, 0.0144),
    ("2026-08-31", 330, -0.007), ("2026-09-01", 330, -0.0117), ("2026-09-03", 332, -0.0274),
    ("2026-09-04", 343, -0.0214), ("2026-09-07", 328, -0.0595), ("2026-09-08", 328, -0.0493),
]
_REDERIVE = {'verdict': 'CONFIRM-ON-AVAILABLE-PLANE',
             'primary': {'full': {'n': 349,
                                  'mean_pct': 0.426,
                                  't_hac': 3.29,
                                  'sharpe': 0.57,
                                  'maxdd_pct': -62.8,
                                  'hit': 0.539},
                         'early': {'n': 138,
                                   'mean_pct': 0.597,
                                   't_hac': 2.97,
                                   'sharpe': 0.73,
                                   'maxdd_pct': -62.8,
                                   'hit': 0.507},
                         'late': {'n': 211,
                                  'mean_pct': 0.314,
                                  't_hac': 1.92,
                                  'sharpe': 0.46,
                                  'maxdd_pct': -37.7,
                                  'hit': 0.559},
                         'pre_2024': {'n': 320,
                                      'mean_pct': 0.534,
                                      't_hac': 4.17,
                                      'sharpe': 0.73,
                                      'maxdd_pct': -62.8,
                                      'hit': 0.55},
                         'post_2024': {'n': 29,
                                       'mean_pct': -0.772,
                                       't_hac': -1.6,
                                       'sharpe': -0.97,
                                       'maxdd_pct': -21.4,
                                       'hit': 0.414}},
             'fill_tax': {'close_to_close_pct': 0.51, 'fill_realistic_pct': 0.426},
             'per_name_drawdown': {'p1_pct': -26.6, 'p5_pct': -17.3, 'worst_pct': -62.1},
             'placebo': {'perm_p': 0.0005, 'real_t_hac': 3.29}}
_PRESENTATION = {'maxdd_disclosure_pct': -37.6,
                 'expected_monthly_hit_pct': 56.0,
                 'one_bet_note': '~10σ pairwise-correlation elevation vs random baskets — this '
                                 'is ONE bet on a bounce regime, not N independent picks. Size '
                                 'the SLEEVE small.',
                 'fill_note': 'Entries spread over the rebalance day (T+1 fill). Measured fill '
                              'haircut ~1pp/entry, ~2-3pp hit vs close-to-close — survivable, '
                              'not a product-killer.',
                 'passport': {'basis': 'measured (upper-bound plane)',
                              'frame': 'monthly rebalance',
                              'freshness': 'current plane',
                              'n': 388,
                              'source': 'research/CHINA_HK_STOCK_SIGNALS.md L98-123'}}
_REFERENCE = {'excess_mo_pct': 0.56,
              'sharpe': 0.58,
              'maxdd_pct': -37.6,
              'hit_pct': 56.0,
              'n_rebalances': 388,
              'n_names': 790,
              'window': '1990→2026',
              'source': 'research/CHINA_HK_STOCK_SIGNALS.md L98-123'}


def _d(sizing=None, graded="graded", members=None):
    """graded="graded" → committed 45-row summary; "accruing" → producer's <_MIN_GRADED shape."""
    if graded == "accruing":
        ledger = {"available": True, "n_rows": 1200, "rebalances": _REBALANCES[:9],
                  "horizon_d": 21, "per_rebalance": [], "n_graded": 4,
                  "graded": {"n_rebalances": 4, "note": "accruing"}}
    else:
        ledger = {"available": True, "n_rows": 19336, "rebalances": list(_REBALANCES),
                  "horizon_d": 21, "n_graded": 45, "graded": dict(_GRADED),
                  "per_rebalance": [{"rebalance_date": a, "n_filled": n, "sleeve_excess": x}
                                    for a, n, x in _PER_REBAL]}
    return {
        "status": "ok", "as_of": "2026-10-16", "data_through": "2026-10-16",
        "n_universe": 1630, "n_members": 326, "equal_weight": 0.0031,
        "screened": {"st": 1, "mcap": 0, "adv": 75},
        "sectors": {"Technology": 84, "Industrials": 77},
        "members": members if members is not None else [
            {"ticker": "000935.SZ", "name": "Sichuan Hexie Shuangma Co., Ltd. / 四川双马",
             "sector": "Financial Services", "ret_3m": -28.0, "rev_z": 3.0, "sector_rank": 1,
             "sector_n": 102, "mktcap_yi": None, "weight": 0.0031}],
        "sizing": copy.deepcopy(sizing if sizing is not None else _SIZING),
        "rederive_stats": copy.deepcopy(_REDERIVE),
        "presentation": copy.deepcopy(_PRESENTATION),
        "reference": dict(_REFERENCE), "backcast": None,
        "ledger": {"rows": 19336, "artifact": "data/cn_reversal_sleeve_track/sleeve.parquet",
                   "conventions": ("CSI300-relative · T+1 fill · locked-limit excluded"
                                   " · data_through"),
                   "graded": ledger},
    }


def _render(d: dict) -> str:
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    return env.get_template("cn_reversal_sleeve.html.j2").render(d=d, built="T")

# committed rederive_stats.csi300_reference shape (producer writes all keys, null for
# uncomputed stats); the neighbour fixture's _REDERIVE predates it, tests add it explicitly.
_CSI = {"n": 169, "mean_pct": 1.052, "t_hac": 2.49, "sharpe": 0.67, "maxdd_pct": -37.7,
        "hit": None}
# SPEC 2 finding sample: two positive early rows plus the negative 2026-09-07 row.
_THREE = [("2026-07-01", 291, 0.0567), ("2026-07-02", 302, 0.0926),
          ("2026-09-07", 328, -0.0595)]


def _with_rows(d, triples):
    d["ledger"]["graded"]["per_rebalance"] = [
        {"rebalance_date": a, "n_filled": n, "sleeve_excess": x} for a, n, x in triples]
    return d


def _rows(html: str) -> str:
    """The rows table slice, plus the cap note <p class="sub"> when one immediately follows."""
    i = html.index('<table id="ledger-rows">')
    j = html.index("</table>", i) + len("</table>")
    if html[j:].startswith('\n<p class="sub">'):
        j = html.index("</p>", j) + len("</p>")
    return html[i:j]


def _grid2(html: str) -> str:
    """The SECOND re-derive grid, from its <div class="rd-grid"> to its closing </div>."""
    i = html.index('<div class="rd-grid">')
    i = html.index('<div class="rd-grid">', i + 1)
    j = html.index("\n  </div>", i) + len("\n  </div>")
    return html[i:j]


def _csi_cell(g: str) -> str:
    i = g.index('<span class="l-en">CSI300-rel. re-derive</span>')
    return g[i:g.index("</b></span>", i) + len("</b></span>")]


# --------------------------------------------------------------------------- #
#  Forward ledger rows table (SPEC 2)                                          #
# --------------------------------------------------------------------------- #

def test_rows_render_from_committed_shape():
    s = _rows(_render(_with_rows(_d(), _THREE)))
    assert "<td>2026-07-01</td>" in s
    for n in (291, 302, 328):
        assert f'<td class="num">{n}</td>' in s
    assert '<span class="pos">+5.67%</span>' in s
    assert '<span class="pos">+9.26%</span>' in s
    assert '<span class="neg">-5.95%</span>' in s
    assert ('<span class="l-en">rebalance</span><span class="l-zh">再平衡日</span>' in s)
    assert ('<span class="l-en">names filled</span><span class="l-zh">成交只数</span>' in s)
    assert ('<span class="l-en">excess vs CSI300</span>'
            '<span class="l-zh">相对沪深300超额</span>' in s)


def test_rows_are_newest_first_and_capped_at_12():
    s = _rows(_render(_d()))
    assert s.count("<tr><td>") == 12
    dts = re.findall(r"<tr><td>(\d{4}-\d{2}-\d{2})</td>", s)
    assert dts[0] == "2026-09-08" and dts[-1] == "2026-08-21"
    assert all(a > b for a, b in zip(dts, dts[1:]))
    assert "2026-08-20" not in s and "2026-07-01" not in s
    assert "showing the 12 most recent of 45 graded rows" in s
    assert "显示最近12条，共45条已评分" in s
    d = _d()
    random.Random(7).shuffle(d["ledger"]["graded"]["per_rebalance"])
    assert _rows(_render(d)) == s


def test_negative_excess_uses_neg_class():
    s = _rows(_render(_with_rows(_d(), _THREE)))
    assert '<td class="num"><span class="neg">-5.95%</span></td>' in s
    assert '<td class="num"><span class="pos">+5.67%</span></td>' in s
    s = _rows(_render(_with_rows(_d(), [("2026-07-01", 291, 0.0)])))
    assert '<td class="num"><span class="pos">+0.00%</span></td>' in s


def test_empty_rows_render_no_table_and_accruing_survives():
    html = _render(_d(graded="accruing"))
    assert "ledger-rows" not in html
    assert "Accruing" in html and "累积中" in html
    assert '</code></p>\n\n\n<div class="sec"><h2>' in html
    for mode in ("empty", "absent"):
        d = _d()
        if mode == "empty":
            d["ledger"]["graded"]["per_rebalance"] = []
        else:
            del d["ledger"]["graded"]["per_rebalance"]
        html = _render(d)
        assert "ledger-rows" not in html, mode
        assert '</code></p>\n\n\n<div class="sec"><h2>' in html, mode


def test_cap_note_only_above_12_rows():
    twelve = [(f"2026-08-{i:02d}", 330, 0.01) for i in range(1, 13)]
    s = _rows(_render(_with_rows(_d(), twelve)))
    assert s.count("<tr><td>") == 12
    assert "most recent" not in s and "最近" not in s
    s = _rows(_render(_with_rows(_d(), twelve + [("2026-08-13", 330, 0.01)])))
    assert s.count("<tr><td>") == 12
    assert "showing the 12 most recent of 13 graded rows" in s
    assert "显示最近12条，共13条已评分" in s


def test_rows_block_has_no_whitespace_only_line():
    for d in (_d(), _with_rows(_d(), _THREE)):
        s = _rows(_render(d))
        assert re.search(r"\n[ \t]*\n", s) is None
    html = _render(_d())
    assert '</code></p>\n<table id="ledger-rows">' in html
    assert '</table>\n<p class="sub">' in html
    html = _render(_with_rows(_d(), _THREE))
    assert '</table>\n\n\n<div class="sec">' in html


def test_rows_never_called_a_month_and_print_no_none():
    s = _rows(_render(_d()))
    assert "month" not in s and "月" not in s and "None" not in s
    s = _rows(_render(_with_rows(_d(), [("2026-09-07", 328, None),
                                       ("2026-09-08", 328, -0.0493)])))
    assert '<td class="num">\u2014</td>' in s


# --------------------------------------------------------------------------- #
#  Re-derive basis cells (SPEC 4) — independently guarded                      #
# --------------------------------------------------------------------------- #

def test_csi300_reference_cell_renders():
    d = _d()
    d["rederive_stats"]["csi300_reference"] = dict(_CSI)
    g = _grid2(_render(d))
    assert ('<span class="l-en">CSI300-rel. re-derive</span>'
            '<span class="l-zh">相对沪深300再推导</span>') in g
    assert "+1.052%/reb, t 2.49, n 169" in g


def test_pre_2024_cell_renders_beside_the_post_2024_caveat():
    html = _render(_d())
    g = _grid2(html)
    assert "pre-2024 (2024 split)" in g
    assert "2024年前（以2024年划分）" in g
    assert "+0.534%/reb, t 4.17, n 320" in g
    assert "-0.772%/reb, t -1.60" in html  # the caveat the baseline is read against


def _without_basis(d):
    d["rederive_stats"]["primary"].pop("pre_2024", None)
    d["rederive_stats"].pop("csi300_reference", None)
    return d


def test_missing_basis_keys_omit_the_cells():
    for mode in ("no-key", "empty-dict"):
        d = _without_basis(_d())
        if mode == "empty-dict":
            d["rederive_stats"]["csi300_reference"] = {}
        g = _grid2(_render(d))
        assert g.count('<span class="rd-stat">') == 4, mode
        assert "CSI300-rel." not in g and "pre-2024" not in g, mode
        assert g.endswith('%</span></span>\n  </div>'), mode
    d = _d()
    d["rederive_stats"]["csi300_reference"] = dict(_CSI)
    assert _grid2(_render(d)).count('<span class="rd-stat">') == 6


def test_partial_keys_degrade_without_none():
    # Degraded stats arrive as explicit None values: the cells guard them with
    # `is number`, and a wholly absent dict is guarded by the outer if.
    d = _d()
    d["rederive_stats"]["csi300_reference"] = {"mean_pct": 1.052, "t_hac": None,
                                               "n": None, "hit": None}
    g = _grid2(_render(d))
    cell = _csi_cell(g)
    assert "+1.052%/reb</b>" in cell
    assert ", t " not in cell and ", n " not in cell and "None" not in g
    d["rederive_stats"]["csi300_reference"] = {"mean_pct": None, "t_hac": None,
                                               "n": 169, "hit": None}
    cell = _csi_cell(_grid2(_render(d)))
    assert cell[cell.index("<b>") + 3:].startswith("&mdash;")
    assert ", n 169" in cell and ", t " not in cell


def test_missing_or_non_numeric_inner_keys_degrade_to_dash():
    d = _d()
    d["rederive_stats"]["csi300_reference"] = {"n": 169}
    cell = _csi_cell(_grid2(_render(d)))
    assert cell[cell.index("<b>") + 3:].startswith("&mdash;")
    assert ", n 169" in cell and ", t " not in cell
    d["rederive_stats"]["csi300_reference"] = {"mean_pct": "1.052", "t_hac": "2.49",
                                               "n": "169"}
    cell = _csi_cell(_grid2(_render(d)))
    assert cell[cell.index("<b>") + 3:] == "&mdash;</b></span>"
    d = _d()
    d["rederive_stats"]["primary"]["pre_2024"] = {"t_hac": 4.17}
    g = _grid2(_render(d))
    i = g.index('<span class="l-en">pre-2024 (2024 split)</span>')
    cell = g[i:g.index("</b></span>", i)]
    assert "&mdash;, t 4.17" in cell and ", n " not in cell and "None" not in g
    d["rederive_stats"]["primary"]["pre_2024"] = {"mean_pct": 0.534, "n": 320}
    g = _grid2(_render(d))
    i = g.index('<span class="l-en">pre-2024 (2024 split)</span>')
    assert g[i:g.index("</b></span>", i)].endswith("+0.534%/reb, n 320")


def test_rows_missing_n_filled_prints_dash_not_none():
    s = _rows(_render(_with_rows(_d(), [("2026-09-08", None, -0.0493)])))
    assert '<td>2026-09-08</td><td class="num">\u2014</td>' in s
    assert "None" not in s


def test_basis_cells_have_no_whitespace_only_line():
    d = _d()
    d["rederive_stats"]["csi300_reference"] = dict(_CSI)
    g = _grid2(_render(d))
    assert g.count('<span class="rd-stat">') == 6
    assert re.search(r"\n[ \t]*\n", g) is None
    assert '</span></span>\n    <span class="rd-stat">' in g


def test_added_lines_add_no_style_or_colour_literal():
    src = (_ROOT / "templates" / "cn_reversal_sleeve.html.j2").read_text(encoding="utf-8")
    a = src.index("{%- if rd.csi300_reference %}")
    a = src[a:src.index("\n  </div>", a)]
    b = src.index("{%- set lrows")
    b = src[b:src.index("{# ---- CURRENT MEMBERSHIP", b)]
    for span in (a, b):
        assert "style=" not in span and "<style" not in span
        assert re.search(r"#[0-9a-fA-F]{3,6}\b", span) is None
        assert "rgb(" not in span and "hsl(" not in span and "|safe" not in span
        assert all(len(line) <= 100 for line in span.splitlines())
