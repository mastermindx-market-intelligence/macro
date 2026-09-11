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
    assert "warming up" in html.lower() or "warming" in html.lower()


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
    assert "Week map warming up" in html
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
    assert "without a readable note" in html
    assert "缺少可读说明" in html
    assert not _changed_chip_texts(html), (
        "an unlabelled hole must not wear the .changed blue highlight"
    )


def test_p0_template_consumes_note_en():
    src = (REPO / "templates" / "market_structure.html.j2").read_text(encoding="utf-8")
    assert "item.note_en" in src
    assert "item.note_zh" in src


def test_p1_hero_distance_round_trips_from_emitted_spot_flip(tmp_path):
    """The 1dp string the template prints must match (spot-flip)/flip from the same block."""
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    spot, flip = 7636.3599, 7663.226367
    dist = (spot - flip) / flip * 100
    shown = f"{abs(dist):.1f}"
    assert shown == "0.4", f"precondition: 2026-09-09 arithmetic must format to 0.4, got {shown}"
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
    assert f"({suffix})" in hero, f"hero missing ({suffix})"
    assert f"{suffix} pctile" in hero, f"tip missing {suffix} pctile"
    wrong = f"{pctile}th"
    if not suffix.endswith("th"):
        assert f"({wrong})" not in hero
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
    assert "GEX series from" in hero
    assert "2026-06-15" in hero
    assert "as of" in hero
    assert "2026-09-09" in hero
    null_at = hero.find("Everything above skips those days.")
    prov_at = hero.find("GEX series from")
    assert null_at != -1 and prov_at != -1 and null_at < prov_at
    between = hero[null_at:prov_at]
    assert "·" in between
