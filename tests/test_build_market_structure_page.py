"""Tests for scripts/build_market_structure_page.py (MSP Wave 2).

Verifies:
1. Warm-up mode (msp=None) renders all 6 warm-up placeholders, no crash.
2. Fixture mode renders full data without warm-up placeholders.
3. House-law checks on rendered HTML (padding-top, no stf-*, no validated, no
   title= bilingual, no svg-span-breakout).
4. Key UI elements present in full-data render.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "tests" / "fixtures" / "market_structure_latest.json"

sys.path.insert(0, str(REPO))

from scripts.build_market_structure_page import render  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _render_with_fixture() -> str:
    return render(REPO, fixture=FIXTURE)


def _render_warmup() -> str:
    """Render with no artifact (warm-up state)."""
    return render(REPO, fixture=Path("/nonexistent/path/market_structure_latest.json"))


# ---------------------------------------------------------------------------
# warm-up mode
# ---------------------------------------------------------------------------

def test_warmup_renders_without_crash():
    """msp=None path must not raise; returns non-empty HTML."""
    html = _render_warmup()
    assert len(html) > 1000


def test_warmup_shows_six_placeholders():
    """All 6 panels show warm-up divs when artifact is absent."""
    html = _render_warmup()
    count = html.count('class="warmup"')
    assert count == 6, f"expected 6 warmup divs, got {count}"


def test_warmup_no_crash_on_none_gamma():
    """Hero panel does not crash in warm-up mode."""
    html = _render_warmup()
    assert "Shock-absorber reading isn't on this page yet." in html
    assert "缓冲机制读数尚未出现在本页。" in html


# ---------------------------------------------------------------------------
# full-data mode (fixture)
# ---------------------------------------------------------------------------

def test_fixture_renders_without_crash():
    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"
    html = _render_with_fixture()
    assert len(html) > 50_000


def test_no_warmup_divs_with_full_fixture():
    html = _render_with_fixture()
    count = html.count('class="warmup"')
    assert count == 0, f"warmup divs present with full fixture: {count}"


def test_hero_regime_present():
    html = _render_with_fixture()
    assert "absorbing" in html.lower()  # gamma long → "Dealers absorbing moves"


def test_gex_history_chart_present():
    html = _render_with_fixture()
    assert "gex-chart" in html
    assert "spx-flip-chart" in html


def test_systematic_flows_panels_present():
    html = _render_with_fixture()
    assert "sys-chart" in html
    assert "Volatility-control" in html or "波动率控制" in html


def test_dispersion_panel_present():
    html = _render_with_fixture()
    assert "cor-chart" in html


def test_week_map_panel_present():
    """Week map panel renders its data, not a warming-up placeholder.

    Hardened (OEU M-FIX): this used to branch on whether the fixture happened to
    carry `week_map` and accept either outcome, so it passed for the whole period
    the builder emitted nothing and the section was permanently "warming up".
    The fixture is the contract — assert against it.
    """
    raw = json.loads(FIXTURE.read_text())
    wm = raw.get("week_map")
    assert wm, "fixture must carry week_map — it is the shape the builder must emit"

    html = _render_with_fixture()
    assert "Locked Friday" in html and "锁定周五" in html
    # the anchor price and both band edges must actually reach the page
    assert f'{wm["locked_close"]:.1f}' in html
    assert f'{wm["band_1sigma_lo"]:.0f}' in html
    assert f'{wm["band_1sigma_hi"]:.0f}' in html
    assert f'±{wm["implied_weekly_pct"]:.2f}%' in html


def test_week_map_absent_falls_back_to_warmup(tmp_path):
    """No week_map → the honest warming-up state, never a fabricated band."""
    raw = json.loads(FIXTURE.read_text())
    raw.pop("week_map", None)
    stub = tmp_path / "market_structure_latest.json"
    stub.write_text(json.dumps(raw), encoding="utf-8")

    html = render(REPO, fixture=stub)
    assert "This week's expected range isn't on this page yet." in html
    assert "本周预期区间尚未出现在本页。" in html
    assert "Locked Friday" not in html


def test_state_changes_strip_present():
    html = _render_with_fixture()
    assert "sc-strip" in html
    assert "sc-chip" in html


def test_chart_data_injected():
    html = _render_with_fixture()
    assert "MSP_GAMMA_HIST" in html
    assert "MSP_SYS_HIST" in html
    assert "MSP_COR_HIST" in html


# ---------------------------------------------------------------------------
# house-law checks
# ---------------------------------------------------------------------------

def test_nav_gap_padding_top_ge_14px():
    """body must have padding-top >= 14px (check_nav_gap.py law)."""
    html = _render_with_fixture()
    m = re.search(r"padding-top:\s*(\d+)", html)
    assert m, "no padding-top found in rendered HTML"
    assert int(m.group(1)) >= 14, f"padding-top too small: {m.group(0)}"


def test_no_stf_class():
    """No .stf-* class names (owned by stocktable.js — forbidden per house law)."""
    html = _render_with_fixture()
    hits = [c for c in re.findall(r'class="[^"]*"', html) if "stf-" in c]
    assert not hits, f"stf- class found: {hits[:3]}"


def test_no_validated_claim():
    """'validated' must not appear in user-facing HTML (CI-guarded)."""
    html = _render_with_fixture()
    assert "validated" not in html.lower()


def test_no_title_bilingual():
    """title= attributes must not contain <span> markup (CI-guarded)."""
    html = _render_with_fixture()
    assert not re.search(r'title="[^"]*<span', html)


def test_no_svg_text_span():
    """No <span> inside <svg><text> elements (svg-span-breakout LETHAL trap)."""
    html = _render_with_fixture()
    assert not re.search(r"<text[^>]*>[^<]*<span", html)


def test_bilingual_structure():
    """Both .l-en and .l-zh spans present (bilingual template)."""
    html = _render_with_fixture()
    assert 'class="l-en"' in html
    assert 'class="l-zh"' in html


def test_range_buttons_present():
    """localStorage-backed range buttons present in panel 2."""
    html = _render_with_fixture()
    assert "msp-gex-range" in html
    assert "rbtn" in html


def test_footer_display_only_disclaimer():
    """Plain-word context disclaimer must appear in footer.

    Re-pinned 2026-07-18: the footer originally printed the machine token
    ``display_only: true`` — internal vocabulary banned from Tier 1 by
    docs/DESIGN_DOCTRINE.md Law 2. Same honesty, plain words (Law 5).
    """
    html = _render_with_fixture()
    assert "not buy or sell signals" in html


def test_model_estimate_disclaimer():
    """Model estimate / not audited disclaimer must appear."""
    html = _render_with_fixture()
    assert "model estimate" in html.lower() or "model estimates" in html.lower()


# ---------------------------------------------------------------------------
# W10 r1 — P0/P1/P2/P4/P5
# ---------------------------------------------------------------------------

_CHANGED_CHIP_RE = re.compile(
    r'<span class="sc-chip changed">\s*'
    r'<span class="l-en">(.*?)</span>\s*'
    r'<span class="l-zh">(.*?)</span>\s*'
    r'</span>',
    re.S,
)


def _changed_chip_texts(html: str) -> list[tuple[str, str]]:
    return [(en.strip(), zh.strip()) for en, zh in _CHANGED_CHIP_RE.findall(html)]


def _hero_glass(html: str) -> str:
    """First .glass block (the Shock Absorbers hero) up to the next sec-head."""
    start = html.find('class="glass"')
    assert start != -1, "hero glass missing"
    rest = html[start:]
    end = rest.find('class="sec-head"')
    return rest if end == -1 else rest[:end]


def test_changed_chips_always_have_nonempty_text():
    """HARDEN: a rendered .sc-chip.changed must never be a wordless capsule.

    The old Jinja ''-fallback made the field-name mismatch invisible to every
    gate — this assertion is the one that would have caught it.
    """
    html = _render_with_fixture()
    chips = _changed_chip_texts(html)
    assert chips, "fixture must render at least one .sc-chip.changed"
    for en, zh in chips:
        assert en, f"empty EN text in changed chip (zh={zh!r})"
        assert zh, f"empty ZH text in changed chip (en={en!r})"


def test_p0_gamma_long_to_short_chip_renders_producer_note(tmp_path):
    """Receipt: the real long→short note_en/note_zh from diff_changes reaches the strip."""
    from engine.market_structure_context import diff_changes

    items = diff_changes({"gamma_regime": "long"}, {"gamma_regime": "short"})
    assert items, "diff_changes must emit the gamma_regime long→short row"
    gamma_item = next(i for i in items if i["key"] == "gamma_regime")
    note_en = gamma_item["note_en"]
    note_zh = gamma_item["note_zh"]
    assert "long" in note_en.lower() or "absorb" in note_en.lower()
    assert "short" in note_en.lower() or "amplif" in note_en.lower()
    assert "→" in note_en

    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["state_changes"] = {"vs_asof": "2026-09-08", "items": items}
    stub = tmp_path / "market_structure_latest.json"
    stub.write_text(json.dumps(raw), encoding="utf-8")
    html = render(REPO, fixture=stub)

    chips = _changed_chip_texts(html)
    ens = [en for en, _ in chips]
    zhs = [zh for _, zh in chips]
    assert note_en in ens, (
        f"gamma long→short EN note missing from changed chips; got {ens!r}"
    )
    assert note_zh in zhs, (
        f"gamma long→short ZH note missing from changed chips; got {zhs!r}"
    )
    # no wordless changed capsule even on this producer-shaped fixture
    for en, zh in chips:
        assert en and zh


def test_p0_empty_chip_is_designed_sentence_not_changed_capsule(tmp_path):
    """A data-shaped hole (from/to present, no note) renders §9.12 empty, not .changed."""
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["state_changes"] = {
        "vs_asof": "2026-09-08",
        "items": [{
            "key": "gamma_regime",
            "from": "long",
            "to": "short",
            "note_en": None,
            "note_zh": None,
        }],
    }
    stub = tmp_path / "market_structure_latest.json"
    stub.write_text(json.dumps(raw), encoding="utf-8")
    html = render(REPO, fixture=stub)
    assert 'class="sc-chip empty"' in html
    assert 'class="empty-why"' in html
    assert "Dealer gamma regime changed — no readable note." in html
    assert "庄家伽马机制已变化 — 缺少可读说明。" in html
    assert "long → short" in html
    assert not _changed_chip_texts(html), (
        "an unlabelled hole must not wear the .changed blue highlight"
    )


def test_p0_template_consumes_note_en():
    src = (REPO / "templates" / "market_structure.html.j2").read_text(encoding="utf-8")
    assert "item.note_en" in src
    assert "item.note_zh" in src


def test_p1_hero_distance_round_trips_from_emitted_spot_flip(tmp_path):
    """The 1dp string the template prints must match (spot-flip)/spot from the same block."""
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    spot, flip = 7636.3599, 7663.226367
    dist = (spot - flip) / spot * 100
    shown = f"{abs(dist):.1f}"
    assert shown == "0.4", f"precondition: 2026-09-09 /spot arithmetic must format to 0.4, got {shown}"
    raw["gamma"]["spot"] = spot
    raw["gamma"]["gamma_flip"] = flip
    raw["gamma"]["dist_to_flip_pct"] = dist
    stub = tmp_path / "market_structure_latest.json"
    stub.write_text(json.dumps(raw), encoding="utf-8")
    html = render(REPO, fixture=stub)
    # t('about','约') wraps both spans then the formatted percent
    assert re.search(
        r'about</span><span class="l-zh">约</span>\s*0\.4%',
        html,
    ), "hero must print the 1dp string derived from the emitted spot/flip"
    assert not re.search(
        r'about</span><span class="l-zh">约</span>\s*0\.3%',
        html,
    )


@pytest.mark.parametrize("pctile,suffix", [(1, "1st"), (2, "2nd"), (3, "3rd"), (21, "21st")])
def test_p2_hero_and_tip_ordinal_suffix(tmp_path, pctile, suffix):
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["gamma"]["net_gex_pctile"] = pctile
    stub = tmp_path / "market_structure_latest.json"
    stub.write_text(json.dumps(raw), encoding="utf-8")
    html = render(REPO, fixture=stub)
    hero = _hero_glass(html)
    # P7: the bare "(11th)" is demoted; the lawful long form stays in the tip.
    assert f"({suffix})" not in hero, f"hero rest must not print ({suffix})"
    assert f"{suffix} pctile" in hero, f"tip missing {suffix} pctile"
    wrong = f"{pctile}th"
    if not suffix.endswith("th"):
        assert f"{wrong} pctile" not in hero


def test_p4_five_day_window_in_both_lanes():
    html = _render_with_fixture()
    assert "Adding over 5 days" in html
    assert "5日加仓中" in html
    assert "adding exposure over 5 days" in html
    assert "both adding over 5 days" in html
    assert "两路5日同步加仓" in html
    # numbers unchanged (DO-NOT-TOUCH) — fixture VC $11.8B / $2.1B still print
    assert "$11.8B" in html
    assert "$2.1B" in html


def test_p4_cta_near_flat_is_lighter_than_a_real_add(tmp_path):
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["systematic"]["cta"]["flow_5d"] = 0.129
    raw["systematic"]["cta"]["state"] = "adding"
    raw["systematic"]["cta"]["cta_near_flat"] = True
    stub = tmp_path / "market_structure_latest.json"
    stub.write_text(json.dumps(raw), encoding="utf-8")
    html = render(REPO, fixture=stub)
    assert "near-flat" in html
    assert re.search(r'class="rc adding near-flat"', html)
    # VC stays a full-weight add (fixture flow_5d_bn = 11.8)
    assert re.search(r'class="rc adding"', html)
    assert "Adding over 5 days" in html


def test_p5_hero_has_one_merged_footnote(tmp_path):
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["asof"] = "2026-09-09"
    raw["gamma"]["series_start"] = "2026-06-15"
    raw["gamma"]["coverage"] = {
        "complete": False,
        "missing_recent": ["2026-08-14", "2026-09-01", "2026-09-02"],
        "missing_in_regime": [],
    }
    stub = tmp_path / "market_structure_latest.json"
    stub.write_text(json.dumps(raw), encoding="utf-8")
    html = render(REPO, fixture=stub)
    hero = _hero_glass(html)
    assert hero.count('class="sec-foot"') == 1, (
        f"hero must render exactly one .sec-foot, got {hero.count('class=\"sec-foot\"')}"
    )
    # null disclosure survives VERBATIM
    assert (
        "the options chain is a live snapshot, so a session we miss cannot "
        "be filled in later. Everything above skips those days."
    ) in hero
    assert "No chain reading for 3 recent sessions" in hero
    assert "2026-08-14" in hero and "2026-09-01" in hero and "2026-09-02" in hero
    # provenance appended after a ·
    assert "Dealer-exposure (GEX) series from" in hero
    assert "做市商敞口（GEX）数据自" in hero
    assert "2026-06-15" in hero
    assert "as of" in hero
    assert "2026-09-09" in hero
    null_at = hero.find("Everything above skips those days.")
    prov_at = hero.find("Dealer-exposure (GEX) series from")
    assert null_at != -1 and prov_at != -1 and null_at < prov_at
    between = hero[null_at:prov_at]
    assert "·" in between


# ---------------------------------------------------------------------------
# W10 r2 — window honesty, near-flat flag, null pctile, stances, warmup, P7/P10
# ---------------------------------------------------------------------------

_STANCE_CAUTIOUS_EN = "Watch — this read is being updated."
_STANCE_CAUTIOUS_ZH = "观望——该读数更新中。"


def test_m1_short_series_window_in_both_lanes(tmp_path):
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["systematic"]["flow_window_n"] = 3
    raw["systematic"]["vc"]["flow_window_n"] = 3
    raw["systematic"]["cta"]["flow_window_n"] = 3
    stub = tmp_path / "market_structure_latest.json"
    stub.write_text(json.dumps(raw), encoding="utf-8")
    html = render(REPO, fixture=stub)
    assert "Adding over 3 days" in html
    assert "3日加仓中" in html
    assert "adding exposure over 3 days" in html
    assert "both adding over 3 days" in html
    assert "两路3日同步加仓" in html
    assert "Adding over 5 days" not in html
    assert "5日加仓中" not in html
    assert "over 5 days" not in html


def test_m1_paused_uses_plainer_window_form(tmp_path):
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["systematic"]["agreement"] = "paused"
    raw["systematic"]["flow_window_n"] = 5
    stub = tmp_path / "market_structure_latest.json"
    stub.write_text(json.dumps(raw), encoding="utf-8")
    html = render(REPO, fixture=stub)
    assert "both paused over the last 5 days" in html
    assert "两路近5日均暂停" in html
    assert "paused over 5 days" not in html


def test_m2_cta_near_flat_below_boundary(tmp_path):
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["systematic"]["cta"]["flow_5d"] = 0.19
    raw["systematic"]["cta"]["state"] = "adding"
    raw["systematic"]["cta"]["cta_near_flat"] = True
    stub = tmp_path / "market_structure_latest.json"
    stub.write_text(json.dumps(raw), encoding="utf-8")
    html = render(REPO, fixture=stub)
    assert re.search(r'class="rc adding near-flat"', html)


def test_m2_cta_not_near_flat_at_or_above_boundary(tmp_path):
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["systematic"]["cta"]["flow_5d"] = 0.25
    raw["systematic"]["cta"]["state"] = "adding"
    raw["systematic"]["cta"]["cta_near_flat"] = False
    stub = tmp_path / "market_structure_latest.json"
    stub.write_text(json.dumps(raw), encoding="utf-8")
    html = render(REPO, fixture=stub)
    assert not re.search(r'class="rc adding near-flat"', html)
    assert re.search(r'class="rc adding"', html)


def test_m3_null_pctile_is_missing_data_sentence_never_0th(tmp_path):
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["gamma"]["net_gex_pctile"] = None
    stub = tmp_path / "market_structure_latest.json"
    stub.write_text(json.dumps(raw), encoding="utf-8")
    html = render(REPO, fixture=stub)
    hero = _hero_glass(html)
    assert "0th" not in hero
    assert "0百分位" not in hero
    assert "The percentile rank isn't available for this snapshot" in hero
    assert "本次快照没有百分位读数" in hero


def test_p3_machine_money_stance_map(tmp_path):
    cases = {
        "aligned_adding": (
            "Watch — don't chase: machine buying is already in the price.",
            "观望——勿追涨：机器买盘已在价格中。",
        ),
        "aligned_cutting": (
            "Watch — machine money is stepping back; don't lean against it.",
            "观望——机器资金正在撤减，勿逆势加仓。",
        ),
        "paused": (
            "Stand aside — machine flows aren't pushing either way.",
            "暂不行动——机器资金没有明确方向。",
        ),
        "split": (
            "Stand aside — machine flows aren't pushing either way.",
            "暂不行动——机器资金没有明确方向。",
        ),
        None: (_STANCE_CAUTIOUS_EN, _STANCE_CAUTIOUS_ZH),
        "mystery": (_STANCE_CAUTIOUS_EN, _STANCE_CAUTIOUS_ZH),
    }
    for state, (en, zh) in cases.items():
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        raw["systematic"]["agreement"] = state
        stub = tmp_path / f"sys_{state}.json"
        stub.write_text(json.dumps(raw), encoding="utf-8")
        html = render(REPO, fixture=stub)
        assert en in html, f"§3 EN missing for {state!r}"
        assert zh in html, f"§3 ZH missing for {state!r}"


def test_p3_stock_picker_stance_map(tmp_path):
    cases = {
        "dispersion": (
            "Get ready — conditions favour stock-picking over index bets.",
            "做好准备——当前环境有利于选股而非指数操作。",
        ),
        "elevated": (
            "Stand aside — stocks are moving together; picks add little.",
            "暂不行动——个股同涨同跌，选股意义有限。",
        ),
        "normal": (
            "Watch — don't chase; conditions are middling.",
            "观望——不追单，环境中性。",
        ),
        None: (_STANCE_CAUTIOUS_EN, _STANCE_CAUTIOUS_ZH),
        "mystery": (_STANCE_CAUTIOUS_EN, _STANCE_CAUTIOUS_ZH),
    }
    for state, (en, zh) in cases.items():
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        raw["dispersion"]["cor1m_regime"] = state
        stub = tmp_path / f"disp_{state}.json"
        stub.write_text(json.dumps(raw), encoding="utf-8")
        html = render(REPO, fixture=stub)
        assert en in html, f"§4 EN missing for {state!r}"
        assert zh in html, f"§4 ZH missing for {state!r}"


def test_p3_vol_weather_stance_map(tmp_path):
    cases = {
        "calm": (
            "Stand aside — vol is calm; no hedge urgency.",
            "暂不行动——波动率平静，无需急于对冲。",
        ),
        "stress": (
            "Protect gains — vol stress says trim risk, not add.",
            "保住收益——波动率承压，宜减仓不宜加仓。",
        ),
        None: (_STANCE_CAUTIOUS_EN, _STANCE_CAUTIOUS_ZH),
        "unknown": (_STANCE_CAUTIOUS_EN, _STANCE_CAUTIOUS_ZH),
    }
    for state, (en, zh) in cases.items():
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        raw["vol"]["rv_cross_state"] = state
        stub = tmp_path / f"vol_{state}.json"
        stub.write_text(json.dumps(raw), encoding="utf-8")
        html = render(REPO, fixture=stub)
        assert en in html, f"§5 EN missing for {state!r}"
        assert zh in html, f"§5 ZH missing for {state!r}"


def test_p3_weekly_range_stance_both_lanes():
    html = _render_with_fixture()
    assert "Watch — don't chase moves inside the expected band." in html
    assert "观望——预期区间内的波动不必追。" in html


def test_p6_six_warmups_market_facing_both_lanes():
    html = _render_warmup()
    assert html.count('class="warmup"') == 6
    assert html.count('class="empty-why"') >= 6
    pairs = [
        ("Shock-absorber reading isn't on this page yet.", "缓冲机制读数尚未出现在本页。"),
        ("Dealer-exposure history isn't on this page yet.", "做市商敞口历史尚未出现在本页。"),
        ("Machine-money flows aren't on this page yet.", "机器资金动向尚未出现在本页。"),
        ("Stock-picker conditions aren't on this page yet.", "选股行情尚未出现在本页。"),
        ("Vol weather isn't on this page yet.", "波动率天气尚未出现在本页。"),
        ("This week's expected range isn't on this page yet.", "本周预期区间尚未出现在本页。"),
    ]
    for en, zh in pairs:
        assert en in html, f"warmup EN missing: {en}"
        assert zh in html, f"warmup ZH missing: {zh}"
    assert "首次夜间运行后显示。" not in html
    assert "First nightly run hasn't completed yet." not in html


def test_p7_section4_kpi_row_keeps_at_most_two_at_rest():
    html = _render_with_fixture()
    # Isolate the stock-picker panel (eyebrow 4 → next sec-head).
    start = html.find(">4</span>")
    assert start != -1
    rest = html[start:]
    end = rest.find('class="sec-head"')
    panel = rest if end == -1 else rest[:end]
    row_at = panel.find('<div class="kpi-row">')
    assert row_at != -1, "§4 kpi-row missing"
    chart_at = panel.find('class="chart-wrap"', row_at)
    chunk = panel[row_at: chart_at if chart_at != -1 else len(panel)]
    kpis = re.findall(r'<div class="kpi">', chunk)
    assert len(kpis) <= 2, f"§4 rest KPI count {len(kpis)} exceeds 2"
    assert "stocks are moving more on their own stories than usual" in chunk
    assert "个股比往常更按自身故事走动" in chunk
    assert "that's why this prints green" in chunk
    assert "因此标为绿色" in chunk
    # demoted numbers still live in the panel tip
    assert "2-year percentile" in panel
    assert "3-month implied correlation" in panel
    assert "CBOE dispersion index" in panel


def test_p7_small_n_honesty_lands_in_the_tip(tmp_path):
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["gamma"]["net_gex_pctile"] = 11
    raw["gamma"]["series_start"] = "2026-06-15"
    raw["gamma"]["history"] = [
        {"date": "2026-06-15", "net_gex_bn": -1.0, "regime": "short",
         "flip": 7600.0, "spot": 7500.0}
        for _ in range(45)
    ]
    stub = tmp_path / "short_gex.json"
    stub.write_text(json.dumps(raw), encoding="utf-8")
    html = render(REPO, fixture=stub)
    hero = _hero_glass(html)
    assert "11th pctile" in hero
    assert "45 sessions" in hero
    assert "a rank among 45 readings" in hero
    assert "本序列较短" in hero
    assert "45 次读数" in hero
    assert "(11th)" not in hero


def test_p7_hero_percentile_plain_word_at_rest_long_form_in_tip():
    html = _render_with_fixture()
    hero = _hero_glass(html)
    assert "(68th)" not in hero
    assert "a higher-than-usual reading for this series" in hero
    assert "为本序列偏高的读数" in hero
    assert "68th pctile" in hero
    assert "sessions" in hero


def test_p10_vocabulary_glossed_in_place():
    html = _render_with_fixture()
    assert "the flip level (where dealer hedging switches from absorbing to amplifying)" in html
    assert "翻转点（做市商对冲从吸收转为放大的位置）" in html
    assert "1-month implied correlation" in html
    assert "1个月隐含相关性" in html
    assert "later months cost more than the front (contango)" in html
    assert "远月贵于近月（升水）" in html
    assert "typical range (±1σ, about 68% of weeks)" in html
    assert "wide range (±2σ, about 95% of weeks)" in html
    assert "flip level (dealer hedging switch)" in html
    assert "M1 = front month" in html
    assert "M1=近月" in html
    # leftover English 'vs' must not sit inside a ZH span on THIS page
    # (global nav copy is out of scope).
    wrap_at = html.find('class="wrap"')
    wrap = html[wrap_at:] if wrap_at != -1 else html
    zh_spans = re.findall(r'<span class="l-zh">([^<]*)</span>', wrap)
    vs_hits = [s for s in zh_spans if re.search(r'\bvs\b', s, re.I)]
    assert not vs_hits, f"ZH lane still contains English vs: {vs_hits[:5]}"


def test_p10_gex_glossed():
    html = _render_with_fixture()
    assert "GEX (dealer options exposure)" in html or "GEX (gamma exposure" in html
    assert "GEX（做市商期权敞口）" in html or "GEX（伽马敞口" in html


def test_light_near_flat_and_empty_chip_have_theme_rules():
    src = (REPO / "templates" / "market_structure.html.j2").read_text(encoding="utf-8")
    assert 'html[data-theme="light"] .rc.adding.near-flat' in src
    assert 'html[data-theme="light"] .rc.cutting.near-flat' in src
    assert 'html[data-theme="light"] .sc-chip.empty{background:var(--bg)' in src
    assert "tokens already split the two art directions" not in src
