"""HK hk.html Tier-1 shell plain-language pass (H2).

Pins producer copy EN+ZH, the tone-sign honesty fix (a negative change can
never render "Up"), and negative pins that jargon moved off the glance face
no longer appears at rest.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.hk_signal_stack import build_hk_signal_stack
from engine.hk_tier1 import (
    CYCLE_LANE,
    TILE_COPY,
    apply_cycle_lane,
    chg_sign,
    chg_word,
    cycle_lane,
    history_reading,
    pctile_label,
    peg_face,
    plain_flip_line,
    range_reading,
)
from engine.i18n import tr
from scripts.build_hk import _tile_payload


_GROWTH_SCARE_LATEST = {
    "quad": "Q4", "quad_name": "Growth-scare", "growth_score": -0.4,
    "inflation_score": -0.2, "confidence": 0.51, "liquidity_overlay": "expanding",
    "cycle_tag": "late", "risk_state": "Risk-off", "peg_state": "weak-side (outflow)",
    "conditions": {"roro": {"roro_state": "risk-off"},
                   "recession": {"label": "elevated"},
                   "drawdown_risk": {"band": "elevated"}},
    "market_drivers": {"verdict": "clear", "primary": "global_risk", "dir_sign": -1},
}


def test_growth_scare_zh_is_the_china_ratified_term():
    ss = build_hk_signal_stack(_GROWTH_SCARE_LATEST)
    regime = next(leg for leg in ss["legs"] if leg["key"] == "regime")
    assert regime["state_en"] == "Growth-scare"
    assert regime["state_zh"] == "增长恐慌"
    assert "Growth-scare" not in regime["state_zh"]


def test_growth_axis_and_dual_liquidity_are_not_glance_legs():
    ss = build_hk_signal_stack(_GROWTH_SCARE_LATEST)
    by_key = {leg["key"]: leg for leg in ss["legs"]}
    assert by_key["growth"]["glance"] is False
    assert by_key["liquidity"]["glance"] is False
    assert by_key["growth"]["label_en"] == "Growth axis"
    assert by_key["liquidity"]["label_en"] == "Dual liquidity"
    assert by_key["regime"]["glance"] is True
    assert by_key["peg"]["glance"] is True


def test_peg_face_drops_weak_side_jargon():
    en, zh = peg_face("weak-side (outflow)")
    assert en == "money leaving"
    assert zh == "资金流出"
    ss = build_hk_signal_stack(_GROWTH_SCARE_LATEST)
    peg = next(leg for leg in ss["legs"] if leg["key"] == "peg")
    assert peg["state_en"] == "weak-side (outflow)"  # kept for the dialog
    assert peg["state_face_en"] == "money leaving"
    assert peg["state_face_zh"] == "资金流出"


def test_negative_change_never_renders_up_even_when_risk_tone_inverts():
    """Honesty hazard: invert-tone instruments used to print Up beside a drop."""
    payload = _tile_payload(-0.0123, invert=True)
    assert payload["chg_sign"] == "down"
    assert payload["chg_word_en"] == "Down"
    assert payload["chg_word_zh"] == "跌"
    assert payload["tone"] == "pos"  # risk-on (weaker USD / firmer HKD) — NOT the chip word
    assert chg_word(chg_sign(-1.0)) == ("Down", "跌")
    assert chg_word(chg_sign(1.0)) == ("Up", "涨")
    assert chg_word(chg_sign(0.0)) == ("Flat", "平")
    down = _tile_payload(-0.5, invert=False)
    assert down["chg_word_en"] != "Up"
    assert down["chg_sign"] == "down"


def test_tile_copy_replaces_slugs_with_display_names():
    assert TILE_COPY["growth"]["tag_en"] == "Hang Seng Tech"
    assert TILE_COPY["growth"]["tag_zh"] == "恒生科技"
    assert TILE_COPY["peg"]["tag_en"] == "HK dollar peg"
    assert TILE_COPY["USDCNH"]["tag_en"] == "Offshore yuan"
    assert TILE_COPY["USDCNH"]["tag_zh"] == "离岸人民币"
    assert TILE_COPY["DXY"]["tag_en"] == "US dollar"
    assert TILE_COPY["yield"]["tag_en"] == "HK overnight rate"
    assert TILE_COPY["USD/oz"]["tag_en"] == "Gold"
    for copy in TILE_COPY.values():
        assert copy["meaning_en"]
        assert copy["meaning_zh"]
        assert copy["meaning_en"] != copy["meaning_zh"]


def test_cycle_lane_swaps_buy_zone_and_unconfirmed_turn():
    assert cycle_lane("BUY ZONE") == ("Buy now", "立即买入")
    assert cycle_lane("UNCONFIRMED TURN") == ("Stand aside", "观望")
    assert CYCLE_LANE["BUY ZONE"][0] == "Buy now"
    row = apply_cycle_lane({"ticker": "0700.HK", "label": "BUY ZONE", "label_zh": "买入区"})
    assert row["label"] == "Buy now"
    assert row["label_zh"] == "立即买入"
    kept = apply_cycle_lane({"label": "UPTREND", "label_zh": "上涨趋势"})
    assert kept["label"] == "UPTREND"


def test_percentile_plain_readings_match_the_live_exemplars():
    # Packet examples: 32th-of-range → mid-range; 51th pctile → about average.
    assert range_reading(32) == ("mid-range", "区间中部")
    assert history_reading(51) == ("about average", "大致平均")
    assert pctile_label(32) == ("32nd percentile", "第32百分位")
    assert pctile_label(51) == ("51st percentile", "第51百分位")
    assert "th percentile" not in pctile_label(32)[0].replace("32nd percentile", "")


def test_plain_flip_line_is_one_sentence_without_thresholds():
    snap = {
        "verdict": "MIXED",
        "components": [
            {"label_en": "Risk appetite", "label_zh": "风险偏好", "score": 48},
            {"label_en": "Volatility (VHSI)", "label_zh": "波动率（VHSI）", "score": 16},
        ],
        "flip_en": "→ Green if risk appetite firms up (now 48/100). → Red if volatility (VHSI) breaks down (now 16/100).",
    }
    en, zh = plain_flip_line(snap)
    assert en.startswith("The read flips if")
    assert "48" not in en and "16/100" not in en
    assert "/100" not in en
    assert "翻转" in zh
    assert "48" not in zh


def test_sector_glossary_covers_the_named_chips():
    assert tr("Energy") == "能源"
    assert tr("Materials") == "原材料"
    assert tr("Financials & Banks") == "金融与银行"
    assert tr("Exchange & Diversified") == "交易所与综合企业"
    assert tr("Industrials & Transport") == "工业与运输"


# ---------------------------------------------------------------------------
# Template render — glance face vs dialog
# ---------------------------------------------------------------------------

def _make_vm(**overrides) -> dict:
    from tests.test_hk_cbbc_banner_template import _make_actions, _make_setups

    ss = build_hk_signal_stack(_GROWTH_SCARE_LATEST)
    tiles = [
        {
            "kind": kind,
            "tag_en": copy["tag_en"], "tag_zh": copy["tag_zh"],
            "meaning_en": copy["meaning_en"], "meaning_zh": copy["meaning_zh"],
            "level": "7.8200" if kind == "peg" else "12.4",
            "chg": "-0.0120" if kind == "peg" else "+0.40",
            "chg_raw": -0.012 if kind == "peg" else 0.40,
            "pct": "-0.2%" if kind == "peg" else "+1.1%",
            **_tile_payload(-0.012 if kind == "peg" else 0.40, invert=(kind in ("peg", "USDCNH", "DXY"))),
            "tag": Markup(f'<span class="l-en">{copy["tag_en"]}</span><span class="l-zh">{copy["tag_zh"]}</span>'),
            "label": Markup('<span class="l-en">x</span><span class="l-zh">x</span>'),
        }
        for kind, copy in TILE_COPY.items()
    ]
    vm = {
        "mode": "macro",
        "latest": {
            "date": "2026-07-10",
            "quad_name": "Growth-scare",
            "quad": "Q4",
            "liquidity_overlay": "expanding",
            "pending_quad": None,
            "peg_state": "weak-side (outflow)",
        },
        "actions": _make_actions(),
        "setups": _make_setups(),
        "cbbc_map": None,
        "gv": {"peg": {"level": 7.84, "state": "weak-side (outflow)"}, "state": "Risk-off"},
        "market_state": {
            "color": "yellow", "score": 48, "verdict": "MIXED",
            "label_en": "Mixed", "label_zh": "混合",
            "headline_en": "Trade with caution.", "headline_zh": "谨慎操作。",
            "flip_en": "→ Green if risk appetite firms up (now 48/100). → Red if volatility (VHSI) breaks down (now 16/100).",
            "flip_zh": "→ 若风险偏好转强（现 48/100）则转「偏多」；若波动率走坏（现 16/100）则转「避险」。",
            "flip_plain_en": "The read flips if risk appetite turns clearly for or against.",
            "flip_plain_zh": "若风险偏好明确转多或转空，读数会翻转。",
            "components": [
                {"label_en": "Risk appetite", "label_zh": "风险偏好", "score": 48, "tone": "warn"},
                {"label_en": "Volatility (VHSI)", "label_zh": "波动率（VHSI）", "score": 16, "tone": "bear"},
            ],
        },
        "signal_stack": ss,
        "market_tiles": tiles,
        "sectors": [
            {"name": "Energy", "mom20": 4.2, "dir": "up"},
            {"name": "Materials", "mom20": 3.1, "dir": "up"},
            {"name": "Financials & Banks", "mom20": 1.4, "dir": None},
            {"name": "Exchange & Diversified", "mom20": -0.8, "dir": None},
        ],
        "vhsi": {
            "level": 18.4, "pctile": 32,
            "range_plain_en": "mid-range", "range_plain_zh": "区间中部",
            "pctile_en": "32nd percentile", "pctile_zh": "第32百分位",
            "chg20": -1.2,
        },
        "ah_official": {
            "premium_pct": 28.4, "pctile": 51,
            "history_plain_en": "about average", "history_plain_zh": "大致平均",
            "pctile_en": "51st percentile", "pctile_zh": "第51百分位",
        },
        "funding": {"hibor_1m": 3.21, "hibor_on": 2.88, "agg_balance": 120000,
                    "twi": None, "base_rate": None},
        "top_setups": [
            apply_cycle_lane({"ticker": "0700.HK", "name": "Tencent", "name_zh": "腾讯",
                              "sector": "Internet & Tech", "label": "BUY ZONE", "label_zh": "买入区"}),
            apply_cycle_lane({"ticker": "0005.HK", "name": "HSBC", "name_zh": "汇丰",
                              "sector": "Financials & Banks", "label": "UNCONFIRMED TURN",
                              "label_zh": "未确认转向"}),
        ],
        "hk_scoreboard": None,
        "sectors_by_ticker": {},
        "velocity_desk": None,
        "built": "2026-07-10T00:00:00Z",
        "hk_breadth": None,
        "hk_full_breadth": None,
        "benchmark": None,
        "hk_sectors": [],
        "hk_flow": None,
        "track_record": None,
        "hk_ab": None,
        "hk_dispersion": None,
        "hk_cycles": None,
        "hk_indicators": None,
        "state_display_json": "{}",
        "washout_desk": None,
        "freshness": None,
        "ms_history": None,
        "command_panel": None,
        "event_strip": None,
        "internals": None,
        "flow_charts": None,
        "alerts": None,
        "index_health": None,
        "pb": None,
        "adr_bridge": None,
        "filing_bus": None,
        "property": None,
        "catalyst_strip": None,
        "radar_dlg": {},
        "CGL": None,
        "hk_1d_velocity_desk": None,
    }
    vm.update(overrides)
    return vm


def _render(**overrides) -> str:
    from jinja2 import Environment, FileSystemLoader
    from engine import i18n

    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    env.globals["help"] = lambda en, zh="": Markup("")
    return env.get_template("hk.html.j2").render(**_make_vm(**overrides))


def _glance(html: str) -> str:
    start = html.find('id="hkx-hero-card"')
    assert start != -1, "hero card missing"
    end = html.find('id="hkx-dlg-', start)
    assert end != -1, "dialog start missing — glance slice would silently widen"
    return html[start:end]


def _zh_text(html: str) -> str:
    return " ".join(re.findall(r'class="l-zh"[^>]*>([^<]*)', html))


def _en_text(html: str) -> str:
    return " ".join(re.findall(r'class="l-en"[^>]*>([^<]*)', html))


def test_render_zh_lane_translates_growth_scare_and_sector_chips():
    html = _render()
    glance = _glance(html)
    zh = _zh_text(glance)
    assert "增长恐慌" in zh
    assert "Growth-scare" not in zh
    assert "能源" in zh
    assert "原材料" in zh
    assert "金融与银行" in zh
    # Exchange & Diversified is 4th by mom20 so it sits on the heat strip, not the
    # three hot chips — the ZH tooltip is the glance-tier pin.
    assert 'data-tip-zh="能源' in glance
    assert 'data-tip-zh="原材料' in glance
    assert 'data-tip-zh="金融与银行' in glance
    assert 'data-tip-zh="交易所与综合企业' in glance
    assert 'data-tip-zh="Financials' not in glance


def test_render_strip_uses_display_names_and_meanings():
    glance = _glance(_render())
    assert "Hang Seng Tech" in glance
    assert "HK dollar peg" in glance
    assert "Offshore yuan" in glance
    assert "US dollar" in glance
    assert "HK overnight rate" in glance
    assert "higher = a weaker HK dollar" in glance
    assert "USDCNH" not in glance
    assert "USD/oz" not in glance
    # the old slug tags are gone (display names replaced them)
    assert ">growth<" not in glance.lower()


def test_render_peg_tile_prints_down_beside_a_negative_change():
    glance = _glance(_render())
    # peg tile is invert-tone + negative change → word must still be Down
    assert "chg_word" not in glance  # raw key never leaks
    assert re.search(r'cat-tone bear">\s*<span class="l-en">Down</span>', glance)
    assert 'class="l-en">Up</span>' not in glance.split("HK dollar peg")[1][:800]


def test_render_flip_line_is_plain_and_thresholds_live_in_the_checks_popover():
    html = _render()
    glance = _glance(html)
    flip = re.search(r'class="hkx-flip[^"]*".*?</div>', glance, re.S)
    assert flip, "hero flip line missing"
    face = flip.group(0)
    assert "The read flips if risk appetite turns clearly for or against." in face
    assert "48/100" not in face
    assert "16/100" not in face
    pop = html[html.find('id="hkx-pop-signals"'):html.find('id="hkx-pop-risk"')]
    assert "now 48/100" in pop
    assert "16/100" in pop


def test_render_percentiles_demoted_off_the_face():
    html = _render()
    glance = _glance(html)
    assert "32th" not in glance
    assert "51th" not in glance
    assert "th of its range" not in glance
    assert "th pctile" not in glance
    assert "mid-range" in glance
    assert "about average" in glance
    sent = html[html.find('id="hkx-dlg-sentiment"'):html.find('id="hkx-dlg-sector"')]
    assert "32nd percentile" in sent
    flows = html[html.find('id="hkx-dlg-flows"'):html.find('id="hkx-dlg-overnight"')]
    assert "51st percentile" in flows


def test_render_moved_jargon_absent_at_rest_present_in_dialogs():
    html = _render()
    glance = _glance(html)
    for banned in ("Growth axis", "Dual liquidity", "weak-side (outflow)", "HIBOR 1m",
                   "BUY ZONE", "UNCONFIRMED TURN"):
        assert banned not in glance, f"{banned!r} still on the glance face"
    assert "Buy now" in glance
    assert "Stand aside" in glance
    playbook = html[html.find('id="hkx-dlg-playbook"'):html.find('id="hkx-dlg-events"')]
    assert "Growth axis" in playbook
    assert "Dual liquidity" in playbook
    assert "weak-side (outflow)" in playbook
    policy = html[html.find('id="hkx-dlg-policy"'):html.find('id="hkx-dlg-flows"')]
    assert "HIBOR 1-month" in policy or "1月HIBOR" in policy


def test_render_what_to_do_rows_use_monoline_icons_not_emoji():
    html = _render()
    glance = _glance(html)
    todo = glance[glance.find("What To Do"):glance.find("Coming Up")]
    assert "ic-svg" in todo
    assert "🟢" not in todo
    assert "🔴" not in todo
    assert "🟡" not in todo
    src = (ROOT / "templates" / "hk.html.j2").read_text()
    # the glance loop itself no longer embeds the emoji
    assert "{{ '🟢' if leg.tone" not in src
