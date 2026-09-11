"""W6 round 1 — commodities.html P0 truth blockers + lexicon slug guard.

Pins:
  P0#1  heat-grid shock outranks momentum; blow-off never paints as trending-up;
        every legend word is reachable from a real _heat_cell branch.
  P0#2  one change helper, one 1-month window; live tiles SSR a day change.
  P0#3  one dispersion truth; hero cannot outrank take-profits rows; calm words
        are scoped (index vs members).
  P0#4  every detail entry carries dollar_* keys; template truthiness so a
        missing key never emits "Dollar: ·".
  P1#5  confluence lane labels are plain words; _lbl never emits a raw slug.

Run: python -m pytest tests/test_commodities_w6_truth.py tests/test_commodities_ignition_copy.py tests/test_commodity_confluence.py -q
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pandas as pd
import pytest
from jinja2 import Environment

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from engine.commodity_confluence import (  # noqa: E402
    _LABELS,
    _TIPS,
    _UNLABELLED,
    _lbl,
)
from scripts.build_commodities import (  # noqa: E402
    CHG_1D_BARS,
    CHG_1M_BARS,
    HEAT_LEGEND,
    _build_sector_vm_inner,
    _chg_pct,
    _heat_cell,
    _sync_read,
    asset_vm,
    sector_stance,
)

_TPL = _REPO / "templates" / "commodities.html.j2"
_BUILDER = _REPO / "scripts" / "build_commodities.py"


def _tpl() -> str:
    return _TPL.read_text()


def _legend_block() -> str:
    src = _tpl()
    start = src.index('<div class="legend">')
    end = src.index("</div>", start)
    return src[start:end]


def _dollar_block() -> str:
    src = _tpl()
    start = src.index("{# M6: B3 USD-sensitivity")
    end = src.index("<!-- right: MTF", start)
    return src[start:end]


def _render_dollar(d: dict) -> str:
    env = Environment()
    snippet = '{% macro t(en, zh="") %}{{ en }}{% endmacro %}\n' + _dollar_block()
    return env.from_string(snippet).render(d=d)


# --------------------------------------------------------------------------- #
# P0#1 — shock outranks momentum
# --------------------------------------------------------------------------- #
def test_blowoff_plus_bull_is_blowoff_not_trending_up() -> None:
    tone, en, zh = _heat_cell("blowoff", "bull")
    assert tone == "c-blowoff"
    assert en == "Blow-off"
    assert zh == "喷发"
    assert "trend" not in en.lower()
    assert en != "Momentum up"
    assert "Trending up" not in en


def test_washout_plus_bull_is_washout_not_green() -> None:
    tone, en, _zh = _heat_cell("washout", "bull")
    assert tone == "c-washout"
    assert tone != "c-up"
    assert en == "Washing out"


def test_heat_cell_branch_order_shock_before_momentum() -> None:
    """The if-chain itself, not just the outputs — shock tests precede bull."""
    src = inspect.getsource(_heat_cell)
    blow = src.find('shock_st == "blowoff"')
    wash = src.find('shock_st == "washout"')
    bull = src.find('mom_state == "bull"')
    bear = src.find('mom_state == "bear"')
    assert blow != -1 and wash != -1 and bull != -1 and bear != -1
    assert blow < bull, "blowoff must be evaluated before bull momentum"
    assert wash < bull, "washout must be evaluated before bull momentum"
    assert bull < bear


@pytest.mark.parametrize(
    "shock,mom,tone,en",
    [
        ("blowoff", "bull", "c-blowoff", "Blow-off"),
        ("blowoff", "bear", "c-blowoff", "Blow-off"),
        ("blowoff", "neutral", "c-blowoff", "Blow-off"),
        ("washout", "bull", "c-washout", "Washing out"),
        ("washout", "bear", "c-washout", "Washing out"),
        ("normal", "bull", "c-up", "Momentum up"),
        ("", "bull", "c-up", "Momentum up"),
        ("normal", "bear", "c-dn", "Momentum down"),
        ("normal", "neutral", "c-flat", "Mixed"),
        ("", "", "c-flat", "—"),
    ],
)
def test_heat_cell_matrix(shock, mom, tone, en) -> None:
    got_tone, got_en, _zh = _heat_cell(shock, mom)
    assert got_tone == tone
    assert got_en == en


def test_every_legend_word_is_reachable_from_a_real_branch() -> None:
    legend = _legend_block()
    reachable_en = set()
    reachable_tones = set()
    probes = [
        ("blowoff", "bull"),
        ("washout", "bear"),
        ("normal", "bull"),
        ("normal", "bear"),
        ("normal", "neutral"),
    ]
    for shock, mom in probes:
        tone, en, zh = _heat_cell(shock, mom)
        reachable_en.add(en)
        reachable_tones.add(tone)
        assert en in legend, f"legend missing reachable word {en!r}"
        assert zh in legend, f"legend missing ZH twin {zh!r}"

    for tone, token, en, zh in HEAT_LEGEND:
        assert en in legend, f"HEAT_LEGEND EN {en!r} not in template legend"
        assert zh in legend, f"HEAT_LEGEND ZH {zh!r} not in template legend"
        assert f"var({token})" in legend, f"legend swatch missing var({token})"
        assert tone in reachable_tones, f"legend tone {tone} has no producing branch"
        assert en in reachable_en, f"legend word {en!r} has no producing branch"

    assert "Trending up" not in legend
    assert "Euphoric / falling" not in legend


def test_producer_no_longer_emits_c_wash() -> None:
    src = inspect.getsource(_heat_cell)
    assert '"c-wash"' not in src
    assert '"c-blowoff"' in src and '"c-washout"' in src


def test_page_css_splits_blowoff_and_washout() -> None:
    src = _tpl()
    assert "/* post-stack: consolidate */" in src
    assert ".cell.c-blowoff" in src
    assert ".cell.c-washout" in src


# --------------------------------------------------------------------------- #
# P0#2 — one helper, one window; live tile is day-change
# --------------------------------------------------------------------------- #
def test_chg_helper_window_is_22_sessions() -> None:
    assert CHG_1M_BARS == 22
    assert CHG_1D_BARS == 1
    close = pd.Series([100.0] * 23 + [105.0, 110.0])
    # 1-month: last vs 22 sessions earlier (iloc[-23] == 100) → +10.0
    assert _chg_pct(close, CHG_1M_BARS) == 10.0
    # 1-day: 110 / 105 − 1 → +4.8
    assert _chg_pct(close, CHG_1D_BARS) == 4.8


def test_cited_surfaces_call_the_same_helper() -> None:
    a_src = inspect.getsource(asset_vm)
    i_src = inspect.getsource(_build_sector_vm_inner)
    assert a_src.count("_chg_pct(") >= 2  # 1m + 1d
    assert i_src.count("_chg_pct(") >= 2  # grid + detail
    assert "iloc[-22]" not in a_src
    assert "iloc[-23]" not in i_src
    assert "chg_1d" in a_src


def test_live_strip_ssrs_day_change_not_monthly() -> None:
    src = _tpl()
    start = src.index("LIVE PRICE STRIP")
    end = src.index("SECTION 2", start)
    live = src[start:end]
    assert "a.chg_1d" in live
    assert "a.chg}" not in live
    assert "GC=F_chg': a.chg}" not in live


def test_same_window_cannot_ship_two_values() -> None:
    """Grid and asset_vm 1-month both go through _chg_pct(close, CHG_1M_BARS)."""
    close = pd.Series([float(i) for i in range(50, 80)])
    via_helper = _chg_pct(close, CHG_1M_BARS)
    # reconstruct what the old two sites would have disagreed on
    old_asset = round(100 * (close.iloc[-1] / close.iloc[-22] - 1), 1)
    old_grid = round(100 * (close.iloc[-1] / close.iloc[-23] - 1), 1)
    assert old_asset != old_grid, "precondition: the two old windows differed"
    assert via_helper == old_grid  # canonical = the 17-member grid window


# --------------------------------------------------------------------------- #
# P0#3 — one dispersion truth; hero gated on take-profits
# --------------------------------------------------------------------------- #
def _breadth(n_up=12, n_bull=10, n_members=17, diversity=0.2) -> dict:
    return {
        "n_members": n_members,
        "n_up_trend": n_up,
        "n_bull_momentum": n_bull,
        "trend_diversity": diversity,
    }


def test_sync_read_is_the_one_dispersion_truth() -> None:
    one = _sync_read(0.2)
    many = _sync_read(0.8)
    assert one["in_sync"] is True and one["sync_en"] == "one trend"
    assert many["in_sync"] is False and many["sync_en"] == "many trends"
    assert _sync_read(None)["in_sync"] is None


def test_hero_act_uses_the_same_sync_truth() -> None:
    conf = {"members": [{"state": "Neutral"}] * 17}
    st_sync = sector_stance(conf, _breadth(diversity=0.2))
    st_many = sector_stance(conf, _breadth(diversity=0.8))
    assert st_sync["tone"] == "act"
    assert "in sync" in st_sync["sub_en"]
    assert st_many["tone"] == "act"
    assert "in sync" not in st_many["sub_en"]
    assert "different stories" in st_many["sub_en"]


def test_take_profits_row_blocks_act_hero() -> None:
    """One 'Blowing off' member is enough — hero must not say Act / in sync."""
    members = [{"state": "Neutral"}] * 16 + [{"state": "Blowing off — extended"}]
    st = sector_stance({"members": members}, _breadth(diversity=0.2))
    assert st["tone"] == "protect"
    assert st["word_en"] == "Protect gains"
    assert "in sync" not in st["sub_en"]
    assert "Act" not in st["word_en"]


def test_template_chip_reads_producer_sync_not_a_second_threshold() -> None:
    src = _tpl()
    chip_start = src.index("One story or many?")
    chip = src[chip_start - 400: chip_start + 250]
    assert "br.sync_en" in chip
    assert "trend_diversity or 0) > 0.4" not in src


def test_calm_words_are_scoped_index_vs_members() -> None:
    src = _tpl()
    assert "No shock at the index level" in src
    assert "指数层面无冲击" in src
    assert "Members calm" in src
    assert "品种平稳" in src
    assert "market calm = no shock" not in src


# --------------------------------------------------------------------------- #
# P0#4 — Dollar: · never renders
# --------------------------------------------------------------------------- #
def test_dollar_block_uses_truthiness_not_is_not_none() -> None:
    block = _dollar_block()
    assert "d.get(" in block
    # The live condition must not use Jinja `is not none` (true for a missing key).
    assert "dollar_usd_dir is not none" not in block
    assert "dollar_effect is not none" not in block


def test_missing_dollar_keys_emit_no_row() -> None:
    html = _render_dollar({})
    assert "Dollar" not in html
    assert "·" not in html


def test_none_dollar_fields_emit_no_row() -> None:
    html = _render_dollar({"dollar_usd_dir": None, "dollar_effect": None})
    assert "Dollar" not in html
    assert "·" not in html


def test_neutral_effect_alone_emits_no_row() -> None:
    html = _render_dollar({"dollar_usd_dir": None, "dollar_effect": "neutral"})
    assert "Dollar" not in html


def test_dollar_row_renders_real_values() -> None:
    html = _render_dollar({"dollar_usd_dir": "up", "dollar_effect": "headwind"})
    assert "Dollar" in html
    assert "rising" in html
    assert "headwind for this commodity" in html
    assert "Dollar: ·" not in html


def test_dollar_falling_tailwind_branch() -> None:
    html = _render_dollar({"dollar_usd_dir": "down", "dollar_effect": "tailwind"})
    assert "falling" in html
    assert "tailwind for this commodity" in html


def test_detail_entries_always_carry_dollar_keys() -> None:
    """Unavailable rows also get the keys (default None) so Jinja never sees a hole."""
    src = _BUILDER.read_text()
    assert '"dollar_usd_dir": None, "dollar_effect": None' in src
    assert '"dollar_usd_dir": (a_vm or {}).get("dollar_usd_dir")' in src


# --------------------------------------------------------------------------- #
# P1#5 — lexicon + slug guard
# --------------------------------------------------------------------------- #
def test_cot_and_exogenous_are_plain_words_on_the_lane() -> None:
    assert _LABELS["cot_long"][0] == "Big speculators are crowded long"
    assert _LABELS["cot_short"][0] == "Big speculators are crowded short"
    assert "大投机者" in _LABELS["cot_long"][1]
    assert "大投机者" in _LABELS["cot_short"][1]
    for _code, (en, zh) in _LABELS.items():
        assert "COT" not in en, f"machine term on the lane: {en!r}"
        assert "Exogenous" not in en, f"machine term on the lane: {en!r}"
        assert en and zh and en != zh


def test_machine_terms_live_on_data_tip_rc() -> None:
    assert "exogenous" in _TIPS["shock_top"][0].lower()
    assert "exogenous" in _TIPS["shock_bottom"][0].lower()
    assert "COT" in _TIPS["cot_long"][0]
    assert "COT" in _TIPS["cot_short"][0]
    src = _tpl()
    assert "data-tip-rc-en" in src
    assert "rc.tip_en" in src


def test_lbl_never_emits_a_raw_slug() -> None:
    out = _lbl("not_a_real_condition_xyz")
    assert out["code"] == "not_a_real_condition_xyz"
    assert out["label_en"] == _UNLABELLED[0]
    assert out["label_zh"] == _UNLABELLED[1]
    assert out["label_en"] != out["code"]
    assert out["label_zh"] != out["code"]
    assert " " in out["label_en"]


def test_lbl_known_code_carries_tip_when_catalogued() -> None:
    out = _lbl("cot_long")
    assert out["label_en"] == "Big speculators are crowded long"
    assert out["tip_en"] == "COT crowded long"
    assert "tip_en" in _lbl("shock_top")
    assert "tip_en" not in _lbl("curl")
