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
    _EXPLAIN,
    _LABELS,
    _TIPS,
    _UNLABELLED,
    _lbl,
)
from engine.commodity_index import _chg_1m  # noqa: E402
from scripts.build_commodities import (  # noqa: E402
    CHG_1D_BARS,
    CHG_1M_BARS,
    FRAC_TOP_PROTECT,
    HEAT_LEGEND,
    _UNLABELLED_STATE,
    _build_sector_vm_inner,
    _chg_pct,
    _chg_tone,
    _heat_cell,
    _plain_mom_state,
    _plain_shock,
    _sync_read,
    asset_vm,
    sector_stance,
)

# Real 17-member complex order (engine/commodity_confluence + _GRID_GROUPS).
_COMPLEX_NAMES = [
    "oil", "natgas", "gasoline", "heating_oil",
    "gold", "silver", "platinum", "palladium", "copper",
    "corn", "wheat", "soybeans", "live_cattle", "coffee", "sugar", "cocoa", "cotton",
]
_TOP_STATES = (
    "Blowing off — extended",
    "Extended — late cycle",
    "Euphoric top — rolling over",
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
    """The if-chain itself, not just the outputs — all four shock tests precede bull."""
    src = inspect.getsource(_heat_cell)
    blow = src.find('shock_st == "blowoff"')
    wash = src.find('shock_st == "washout"')
    exo_bid = src.find('shock_st == "exogenous_bid"')
    exo_prs = src.find('shock_st == "exogenous_pressure"')
    bull = src.find('mom_state == "bull"')
    bear = src.find('mom_state == "bear"')
    assert blow != -1 and wash != -1 and exo_bid != -1 and exo_prs != -1
    assert bull != -1 and bear != -1
    assert blow < bull, "blowoff must be evaluated before bull momentum"
    assert wash < bull, "washout must be evaluated before bull momentum"
    assert exo_bid < bull, "exogenous_bid must be evaluated before bull momentum"
    assert exo_prs < bull, "exogenous_pressure must be evaluated before bull momentum"
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
        ("", "", "c-flat", "Mixed"),
        ("exogenous_bid", "bull", "c-blowoff", "Unexplained bid"),
        ("exogenous_pressure", "bull", "c-washout", "Unexplained selling"),
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
    # n5: producer cannot emit c-wash; don't keep a dead back-compat selector.
    assert ".cell.c-wash," not in src
    assert ".cell.c-wash " not in src
    assert ".cell.c-wash{" not in src


def test_unknown_mom_and_shock_never_echo_the_slug() -> None:
    en, zh = _plain_mom_state("not_a_real_mom")
    assert en == _UNLABELLED_STATE[0]
    assert zh == _UNLABELLED_STATE[1]
    assert en != "not_a_real_mom"
    sen, szh = _plain_shock("not_a_real_shock")
    assert sen == _UNLABELLED_STATE[0]
    assert szh == _UNLABELLED_STATE[1]


def test_empty_heat_cell_word_matches_mixed_legend() -> None:
    tone, en, zh = _heat_cell("", "")
    assert tone == "c-flat"
    assert en == "Mixed"
    assert zh == "中性"


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
    # n2: the grid loop must call _heat_cell, not re-inline a momentum-first block.
    assert "_heat_cell(" in i_src
    assert "_chg_tone(" in i_src


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
    # n1: index KPI helper is the same window, not a second implementation that can drift.
    assert _chg_1m(close) == via_helper


# --------------------------------------------------------------------------- #
# P0#3 — one dispersion truth; three-way hero stance (W6 r2)
# --------------------------------------------------------------------------- #
def _breadth(n_up=12, n_bull=10, n_members=17, diversity=0.2) -> dict:
    return {
        "n_members": n_members,
        "n_up_trend": n_up,
        "n_bull_momentum": n_bull,
        "trend_diversity": diversity,
    }


def _member(name: str, state: str, **extra) -> dict:
    """Shape a real members_conf row (name + confluence state vocabulary)."""
    row = {
        "name": name,
        "state": state,
        "top_score": 40.0 if state in _TOP_STATES else 0.0,
        "bottom_score": 0.0,
        "bottom_fired": [],
        "top_fired": [],
    }
    row.update(extra)
    return row


def _board(states: list[str] | dict[str, str]) -> list[dict]:
    if isinstance(states, dict):
        mapping = {n: "Neutral" for n in _COMPLEX_NAMES}
        mapping.update(states)
        return [_member(n, mapping[n]) for n in _COMPLEX_NAMES]
    assert len(states) == len(_COMPLEX_NAMES)
    return [_member(n, s) for n, s in zip(_COMPLEX_NAMES, states)]


def test_sync_read_is_the_one_dispersion_truth() -> None:
    one = _sync_read(0.2)
    many = _sync_read(0.8)
    assert one["in_sync"] is True and one["sync_en"] == "one trend"
    assert many["in_sync"] is False and many["sync_en"] == "many trends"
    assert _sync_read(None)["in_sync"] is None


def test_hero_act_uses_the_same_sync_truth() -> None:
    conf = {"members": _board(["Neutral"] * 17)}
    st_sync = sector_stance(conf, _breadth(diversity=0.2))
    st_many = sector_stance(conf, _breadth(diversity=0.8))
    assert st_sync["tone"] == "act"
    assert st_sync["word_en"] == "Act"
    assert "in sync" in st_sync["sub_en"]
    assert st_many["tone"] == "act"
    assert "in sync" not in st_many["sub_en"]
    assert "different stories" in st_many["sub_en"]


def test_take_profits_row_blocks_act_hero() -> None:
    """One stretched member: never Act / in sync. Scoped middle, not complex Protect."""
    members = _board({"corn": "Blowing off — extended"})
    st = sector_stance({"members": members}, _breadth(diversity=0.2))
    assert st["tone"] == "selective"
    assert st["word_en"] == "In favour"
    assert "in sync" not in st["sub_en"].lower()
    assert "Act" not in st["word_en"]
    assert st["tone"] != "protect"
    assert "1 of 17 stretched" in st["sub_en"]
    assert "are stretched" not in st["sub_en"]


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


def test_hero_three_way_act_zero_stretched() -> None:
    """Branch 1: all Neutral, in-sync, broad+mom → Act."""
    st = sector_stance({"members": _board(["Neutral"] * 17)}, _breadth(diversity=0.2))
    assert st["tone"] == "act"
    assert st["word_en"] == "Act"
    assert "in sync" in st["sub_en"]


def test_hero_three_way_selective_one_and_four() -> None:
    """Branch 2: 1 and 4 of 17 stretched (below 0.25) → In favour, never Protect."""
    one = sector_stance(
        {"members": _board({"corn": "Blowing off — extended"})},
        _breadth(diversity=0.2),
    )
    assert one["tone"] == "selective"
    assert one["word_en"] == "In favour"
    assert one["word_zh"] == "倾向做多"
    assert "1 of 17 stretched" in one["sub_en"]
    assert "trim that" in one["sub_en"]
    assert "in sync" not in one["sub_en"]
    assert "are " not in one["sub_en"]

    four = sector_stance(
        {"members": _board({
            "corn": "Blowing off — extended",
            "soybeans": "Blowing off — extended",
            "heating_oil": "Extended — late cycle",
            "sugar": "Euphoric top — rolling over",
        })},
        _breadth(diversity=0.2),
    )
    assert four["tone"] == "selective"
    assert "4 of 17 stretched" in four["sub_en"]
    assert "trim those" in four["sub_en"]
    assert four["tone"] != "protect"
    assert 4 / 17 < FRAC_TOP_PROTECT <= 5 / 17


def test_hero_three_way_protect_five_of_seventeen() -> None:
    """Branch 3: 5 of 17 = 29% ≥ 0.25 → complex-level Protect."""
    names = ["corn", "soybeans", "heating_oil", "sugar", "wheat"]
    states = {n: "Blowing off — extended" for n in names}
    st = sector_stance({"members": _board(states)}, _breadth(diversity=0.2))
    assert st["tone"] == "protect"
    assert st["word_en"] == "Protect gains"
    assert "5 of 17 commodities are stretched" in st["sub_en"]
    assert "in sync" not in st["sub_en"]


def test_hero_protect_index_plus_one_uses_singular() -> None:
    """M-A1: index shock can pull n_top==1 into Protect — must not say '1 … are'."""
    st = sector_stance(
        {"members": _board({"corn": "Blowing off — extended"})},
        _breadth(diversity=0.2),
        index_shock="blowoff",
    )
    assert st["tone"] == "protect"
    assert "1 of 17 commodities is stretched" in st["sub_en"]
    assert "are stretched" not in st["sub_en"]


def test_hero_protect_on_index_blowoff_even_with_zero_stretched() -> None:
    st = sector_stance(
        {"members": _board(["Neutral"] * 17),
         "index": {"state": "Neutral"}},
        _breadth(diversity=0.2),
        index_shock="blowoff",
    )
    assert st["tone"] == "protect"
    assert "index itself is blowing off" in st["sub_en"].lower()
    assert "in sync" not in st["sub_en"]


def test_hero_protect_on_index_confluence_top_state() -> None:
    st = sector_stance(
        {"members": _board(["Neutral"] * 17),
         "index": {"state": "Blowing off — extended"}},
        _breadth(diversity=0.2),
        index_shock="normal",
    )
    assert st["tone"] == "protect"


def test_hero_current_shaped_board_is_selective() -> None:
    """origin/main latest.json shape: 3 stretched of 17, index Neutral/normal.

    3/17 ≈ 0.176 < 0.25 → In favour, not Act, not Protect.
    """
    st = sector_stance(
        {"members": _board({
            "heating_oil": "Extended — late cycle",
            "corn": "Blowing off — extended",
            "soybeans": "Blowing off — extended",
        }),
         "index": {"state": "Neutral"}},
        _breadth(n_up=11, n_bull=7, n_members=17, diversity=0.304),
        index_shock="normal",
    )
    assert st["tone"] == "selective"
    assert st["word_en"] == "In favour"
    assert "3 of 17 stretched" in st["sub_en"]
    assert "in sync" not in st["sub_en"]
    assert st["word_en"] != "Act"
    assert st["tone"] != "protect"


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


def test_mixed_effect_alone_emits_no_bare_dollar_label() -> None:
    """m7: unconstrained effect 'mixed' with no dir must not print 'Dollar:'."""
    html = _render_dollar({"dollar_usd_dir": None, "dollar_effect": "mixed"})
    assert "Dollar" not in html
    assert "·" not in html


def test_unknown_dir_alone_emits_no_row() -> None:
    html = _render_dollar({"dollar_usd_dir": "sideways", "dollar_effect": None})
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
    assert "大型投机者" in _LABELS["cot_long"][1]
    assert "大型投机者" in _LABELS["cot_short"][1]
    assert _LABELS["shock_bottom"][0] == "Washout from a shock outside this market"
    assert _LABELS["shock_top"][0] == "Blow-off from a shock outside this market"
    assert "outside selling" not in _LABELS["shock_bottom"][0]
    assert "outside buying" not in _LABELS["shock_top"][0]
    assert _LABELS["shock_bottom"][1] == "外部抛压砸出的洗盘"
    assert _LABELS["shock_top"][1] == "外部买盘推动价格喷发"
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


def test_lbl_explain_is_not_the_chip_label() -> None:
    """m5: Lens body is a real one-line explanation, not a copy of the chip."""
    for code in _LABELS:
        out = _lbl(code)
        assert out["explain_en"]
        assert out["explain_en"] != out["label_en"]
        assert out["explain_zh"] != out["label_zh"]
        assert code in _EXPLAIN
    src = _tpl()
    assert 'data-tip-en="{{ rc.label_en }}"' not in src
    assert "rc.explain_en" in src
    assert "rc.tip_en" in src  # machine term stays on data-tip-rc


def test_blowoff_positive_chg_digit_is_amber_not_green() -> None:
    """M-A3: blowoff + bull + +14.2% must not paint a .up green digit."""
    tone, _en, _zh = _heat_cell("blowoff", "bull")
    assert tone == "c-blowoff"
    assert _chg_tone(tone, 14.2) == "amb"
    assert _chg_tone(tone, 14.2) != "up"
    assert _chg_tone("c-washout", -8.0) == "blue"
    assert _chg_tone("c-up", 14.2) == "up"
    assert _chg_tone("c-dn", -1.0) == "dn"
    assert _chg_tone("c-flat", None) == "mut"

    env = Environment()
    snippet = (
        "{% set m = cell %}"
        '<div class="cell {{ m.tone or \'c-flat\' }}">'
        "{% if m.chg_1m_pct is not none %}"
        '<span class="cpc {{ m.chg_tone or \'mut\' }}">'
        "{{ '%+.1f'|format(m.chg_1m_pct) }}%</span>"
        "{% else %}<span class=\"cpc mut\">—</span>{% endif %}"
        "</div>"
    )
    html = env.from_string(snippet).render(cell={
        "tone": "c-blowoff", "chg_tone": "amb", "chg_1m_pct": 14.2,
    })
    assert 'class="cpc amb"' in html
    assert 'class="cpc up"' not in html
    assert ".up" not in html
    assert "+14.2%" in html
    # The cell itself must not carry a sign class that would inherit green.
    assert "cell c-blowoff" in html
    assert "c-blowoff up" not in html


def test_heat_grid_template_uses_chg_tone_not_sign() -> None:
    src = _tpl()
    start = src.index("SECTION 4 — HEAT GRID")
    grid = src[start: start + 2500]
    assert "m.chg_tone" in grid
    assert "'up' if (m.chg_1m_pct or 0) >= 0 else 'dn'" not in grid
    assert "m.chg_sign" not in grid


def test_live_tile_emdash_is_not_green() -> None:
    """n4: missing day-change must not class the placeholder em-dash as .up."""
    src = _tpl()
    start = src.index("LIVE PRICE STRIP")
    live = src[start: src.index("SECTION 2", start)]
    assert "'up' if (_chg or 0) >= 0 else 'dn'" not in live
    assert "_chg is not none" in live
    env = Environment()
    snippet = (
        "{% set _chg = chg %}"
        '<div class="lt-chg nb-chg {% if _chg is not none %}'
        "{{ 'up' if _chg >= 0 else 'dn' }}{% else %}mut{% endif %}\">—</div>"
    )
    html = env.from_string(snippet).render(chg=None)
    assert "up" not in html
    assert "mut" in html
    html_up = env.from_string(snippet).render(chg=1.2)
    assert "up" in html_up


# --------------------------------------------------------------------------- #
# W6 r3 — LENS keyboard/tap + ZH catalyst/disclaimer (evidence-round composition)
# --------------------------------------------------------------------------- #
def test_early_warning_lens_is_a_button_not_a_row_host() -> None:
    """Packet (g): dedicated `?` button; data-tip is NOT on a tabindex row."""
    src = _tpl()
    start = src.index("Early warnings forming")
    block = src[start: start + 900]
    assert 'class="q cmdty-lens"' in block
    assert "data-cmdty-tip-en=" in block
    assert "<button type=\"button\"" in block
    assert 'data-tip-en="Early-warning list' not in block
    assert "pointerdown" in src
    assert "cmdty-tip-open" in src


def test_receipt_chips_use_cmdty_lens_buttons() -> None:
    src = _tpl()
    assert src.count('class="cmdty-lens"') >= 3
    assert 'data-tip-en="{{ rc.explain_en }}"' not in src


def test_catalyst_label_uses_t_not_td() -> None:
    src = _tpl()
    start = src.index("Upcoming events")
    block = src[start: src.index("ALERT TIMELINE", start)]
    assert "{{ t(c.label, c.label_zh) }}" in block
    assert "{{ td(c.label) }}" not in block


def test_disclaimer_is_the_one_true_sentence() -> None:
    src = _tpl()
    assert "Scheduled dates, not forecasts." in src
    assert "{{ news_disclaimer }}" not in src


def test_timeline_asset_uses_zh_twin() -> None:
    src = _tpl()
    assert "{{ t(e.asset_label, e.asset_label_zh) }}" in src
    builder = _BUILDER.read_text()
    assert '"asset_label_zh"' in builder


def test_heat_grid_empty_cycle_is_not_an_emdash() -> None:
    src = _tpl()
    start = src.index("SECTION 4 — HEAT GRID")
    grid = src[start: src.index("SECTION 5", start)]
    assert "m.cycle_phase_en or '—'" not in grid
    assert "no cycle" in grid
    assert "无周期" in grid
