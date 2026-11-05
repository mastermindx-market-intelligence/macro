"""Display contract for the CN reversal sleeve page (templates/cn_reversal_sleeve.html.j2).

The page renders the payload scripts/build_cn_reversal_sleeve.py writes to
site/factordata/cn_reversal_sleeve.json. These tests render the real template from a fixture
shaped like the committed record (generated 2026-10-16T12:10:53Z):
  - the forward ledger dates its graded window, counts registered-but-ungraded rebalances,
    names the 21-session horizon, discloses that the windows overlap, and prints the median;
  - it prints no interval or Sharpe beside the 45 overlapping rows;
  - the sleeve-size chip names the radar's dominant driver in both languages, and drops the
    clause when the producer wrote none (the builder's fallback shape).
"""
from __future__ import annotations

import copy
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


def _window(html: str) -> str:
    i = html.index('<div class="bc-stats" id="ledger-window">')
    return html[i:html.index("</div>", i)]


def _ledger(html: str) -> str:
    i = html.index("Forward ledger")
    return html[i:html.index('<p class="pass">', i)]


def _chip(html: str) -> str:
    i = html.index('<div class="sleeve-chip"')
    return html[i:html.index("</div>", i)]


# --------------------------------------------------------------------------- #
#  Forward ledger: window, pending count, horizon, overlap, median            #
# --------------------------------------------------------------------------- #

def test_graded_window_dates_render_from_committed_shape():
    block = _window(_render(_d()))
    assert '<span class="l-en">graded window</span><span class="l-zh">评分区间</span>' in block
    assert "<b>2026-07-01 → 2026-09-08</b>" in block


def test_pending_rebalance_count_renders():
    label = ('<span class="l-en">registered, not yet graded</span>'
             '<span class="l-zh">已登记尚未评分</span>')
    block = _window(_render(_d()))
    assert label in block and "<b>16</b>" in block
    d = _d()
    d["ledger"]["graded"]["rebalances"] = _REBALANCES[:45]
    assert "已登记尚未评分" not in _window(_render(d))


def test_horizon_and_overlap_disclosure_render():
    html = _render(_d())
    assert '<span class="l-en">horizon</span><span class="l-zh">持有期</span> <b>21</b>' in html
    assert ("Each row is a 21-session forward window; windows that start within 21 sessions"
            " of each other overlap." in _ledger(html))
    assert "起点相距不足21个交易日的窗口相互重叠" in _ledger(html)
    d = _d()
    d["ledger"]["graded"]["horizon_d"] = None
    html = _render(d)
    assert "持有期" not in _window(html) and "forward window" not in html


def test_median_renders_signed_and_absent_when_none():
    block = _window(_render(_d()))
    assert '<span class="l-zh">超额中位数</span>' in block
    assert '<span class="pos">+3.61%</span>' in block
    d = _d()
    d["ledger"]["graded"]["graded"]["median_excess"] = None
    block = _window(_render(d))
    assert "median excess" not in block and "None" not in block


def test_window_block_only_in_the_graded_branch():
    assert _render(_d()).count('id="ledger-window"') == 1
    acc = _render(_d(graded="accruing"))
    assert 'id="ledger-window"' not in acc and "forward window" not in acc
    assert "<code>n=4</code>" in _ledger(acc)


def test_no_interval_or_sharpe_printed():
    led = _ledger(_render(_d()))
    for s in ("63.7", "87.5", "2.72", "Sharpe", "夏普", "interval", "区间估计"):
        assert s not in led, s


# --------------------------------------------------------------------------- #
#  Sleeve-size chip: dominant driver                                          #
# --------------------------------------------------------------------------- #

def test_chip_names_the_dominant_driver_bilingually():
    chip = _chip(_render(_d()))
    assert '<span class="l-en">main driver</span><span class="l-zh">主要驱动</span>' in chip
    assert ('<span class="l-en">Breadth breakdown (all-boats)</span>'
            '<span class="l-zh">广度普跌（普跌）</span>' in chip)


def test_chip_degrades_when_driver_absent():
    chip = _chip(_render(_d(sizing=_SIZING_FALLBACK)))
    assert '<span class="fac">×1.00</span>' in chip
    for s in ("main driver", "主要驱动", "None"):
        assert s not in chip, s


def test_driver_not_rendered_outside_the_chip():
    html = _render(_d())
    assert html.count("Breadth breakdown (all-boats)") == 1
    assert "Breadth breakdown (all-boats)" in _chip(html)
