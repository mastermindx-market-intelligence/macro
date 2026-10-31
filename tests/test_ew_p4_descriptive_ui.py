"""GD-EW-P4-B1 (EW-P4.T1): descriptive early-warning observation UI, consumer-only.

The Risk Radar envelope band renders an optional ``latest_observation`` view
wrapper (contract frozen in the EW-P4.T1 packet, §A) after validating it through
a Jinja mirror of lib/rotation_observation_notification.py plus the stricter
engine id rule. Descriptive only: no forecast, odds, sizing or delivery copy.

Every test row below is one rubric row of the packet's §I; see
research/grey_deer/evidence/EW_P4_DESCRIPTIVE_UI_2026-10-31.md for the mapping.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from lib.rotation_observation_notification import validate as lib_validate
from tests.test_macro_risk_dialog import _dlg, _render, _vm

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "ew_p4_observation"
SESSION = "2026-10-30"

FORBIDDEN = (
    "forecast", "odds", "probability", "hazard", "crash", "sizing", "buy", "sell",
    "trim", "hedge", "reduce exposure", "activation",
    "预测", "概率", "崩盘", "买入", "卖出", "减仓", "加仓", "仓位", "对冲",
)
CONSENT = ("subscribe", "notify", "email", "opt-in", "订阅", "通知我", "邮件")


def _fixtures() -> dict:
    return {p.stem: json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(FIX.glob("*.json")) if p.name != "expected.json"}


def _expected() -> dict:
    return json.loads((FIX / "expected.json").read_text(encoding="utf-8"))


def _journey_c() -> dict:
    return json.loads((FIX / "journey_c_envelope_1d253e1d.json").read_text(encoding="utf-8"))


def envelope(wrapper: dict | None = None, *, rotation: dict | None = None) -> dict:
    """Journey C envelope, current-session rotation context, optional observation."""
    env = deepcopy(_journey_c())
    env["source_session"] = SESSION
    env["as_of"] = SESSION
    rc = deepcopy(env["rotation_context"])
    rc.update({"coverage": "FRESH", "as_of": SESSION, "usable": True})
    if wrapper is not None:
        rc["latest_observation"] = deepcopy(wrapper)
    if rotation:
        rc.update(deepcopy(rotation))
    env["rotation_context"] = rc
    return env


def render(env: dict) -> str:
    return _dlg(_render(_vm(risk_envelope=env)))


def glance(dlg: str) -> str:
    m = re.search(r'<div class="gde-ew".*?</div>', dlg, re.S)
    assert m, "glance #gde-ew missing"
    return m.group(0)


EW_SELECTORS = (
    "div.gde-ew", "div.gde-ew-brief-h", "div.gde-ew-tablewrap", "details.gde-ew-study",
    "span.gde-policy-caveat", "span.gde-scope",
)


def _new_elements(dlg: str) -> str:
    """Concatenate every element this lane added (parsed, not regex-scraped)."""
    soup = BeautifulSoup(dlg, "html.parser")
    parts = []
    for selector in EW_SELECTORS:
        for el in soup.select(selector):
            parts.append(str(el))
    return "\n".join(parts)


def _text(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(" ")


def state_of(dlg: str) -> str:
    m = re.search(r'id="gde-ew"[^>]*data-ew-state="([a-z]+)"', dlg)
    assert m, "data-ew-state missing"
    return m.group(1)


# ── contract parity ──────────────────────────────────────────────────────
def test_contract_parity_with_lib_validator():
    for name, fixture in _fixtures().items():
        exp = _expected()[name]
        if "notification" not in fixture:
            assert name == "journey_c_envelope_1d253e1d"
            assert exp["lib_valid"] is False
            continue
        try:
            lib_validate(fixture["notification"])
            ok = True
        except ValueError:
            ok = False
        assert ok == exp["lib_valid"], f"{name}: lib says {ok}, expected.json says {exp['lib_valid']}"


def test_contract_parity_malformed_id_is_lib_valid_but_ui_unreadable():
    """The documented stricter rule: the UI refuses ids the lib still accepts."""
    fixture = _fixtures()["malformed_id"]
    lib_validate(fixture["notification"])  # must NOT raise
    dlg = render(envelope(fixture))
    assert state_of(dlg) == "unreadable" == _expected()["malformed_id"]["state"]


# ── state parity (the Jinja mirror) ──────────────────────────────────────
@pytest.mark.parametrize("name", sorted(_expected()))
def test_state_parity_rendered_state_matches_expected(name):
    exp = _expected()[name]
    if name == "journey_c_envelope_1d253e1d":
        dlg = render(_journey_c())  # today's real envelope, untouched
    else:
        dlg = render(envelope(_fixtures()[name]))
    assert state_of(dlg) == exp["state"]


# ── the five-second glance ───────────────────────────────────────────────
def test_five_second_glance_structure():
    dlg = render(envelope(_fixtures()["journey_b_both_fell"]))
    g = glance(dlg)
    assert dlg.index('id="gde-ew"') < dlg.index("<details")  # precedes the drawer
    for frag in ("gde-ew-title", "US Technology leadership", "Observed",
                 "Both fell; XLP fell less than XLK.", "Source session Oct 30",
                 "Quality: Complete", "Watch only: this describes what happened"):
        assert frag in g, frag
    assert g.count("<a ") == 1
    en = re.search(r'<p class="gde-ew-what"><span class="l-en">(.*?)</span>', g, re.S).group(1)
    assert len(en.split()) <= 14, en
    title = re.search(r'id="gde-ew-title"><span class="l-en">(.*?)</span>', g).group(1)
    assert len(title.split()) <= 4, title


# ── side-by-side ratio ───────────────────────────────────────────────────
def test_side_by_side_ratio_legs_table():
    dlg = render(envelope(_fixtures()["journey_b_both_fell"]))
    table = re.search(r'<table class="gde-ew-legs">.*?</table>', dlg, re.S).group(0)
    for frag in ("-1.00%", "-3.00%", "+2.06%", ">XLP<", ">XLK<",
                 "Receiver (numerator)", "Donor (denominator)", "Relative (XLP vs XLK)",
                 "2 sessions, Oct 29 → Oct 30 · US cash sessions"):
        assert frag in table, frag
    assert "Both fell; XLP fell less than XLK." in dlg


def test_side_by_side_ratio_partial_window_mismatch_withholds_numbers():
    dlg = render(envelope(_fixtures()["partial_window_mismatch"]))
    assert 'class="gde-ew-legs"' not in dlg  # legs and ratio withheld with the window
    g = glance(dlg)
    assert "Partial evidence for XLP vs XLK; ratio withheld." in g
    for pct in ("-1.00%", "-3.00%", "+2.06%"):
        assert pct not in g, pct


# ── 2S vs 20S horizons ───────────────────────────────────────────────────
def test_two_session_vs_twenty_session_horizons():
    dlg = render(envelope(_fixtures()["journey_b_both_fell"]))
    cells = re.findall(r'<div class="gde-ew-hz">.*?</div>', dlg, re.S)
    assert len(cells) == 2
    assert cells[0].replace("2-session", "X").replace("2个交易日", "X").replace("+2.06%", "X") \
        .replace("20-session", "X").replace("20个交易日", "X").replace("+3.54%", "X") \
        == cells[1].replace("2-session", "X").replace("2个交易日", "X").replace("+2.06%", "X") \
        .replace("20-session", "X").replace("20个交易日", "X").replace("+3.54%", "X")
    assert all("Measured" in c and "已测量" in c for c in cells)

    confl = render(envelope(_fixtures()["conflict_20s"]))
    assert "The two-session move conflicts with the 20-session trend." in confl
    assert "两个交易日的变化与20个交易日趋势不一致。" in confl


# ── consent / revocation N/A ─────────────────────────────────────────────
@pytest.mark.parametrize("name", sorted(_expected()))
def test_no_consent_or_revocation_controls(name):
    exp = _expected()[name]
    dlg = render(_journey_c()) if name == "journey_c_envelope_1d253e1d" else render(envelope(_fixtures()[name]))
    new = _new_elements(dlg)
    assert "<form" not in new and "<input" not in new and "<button" not in new
    low = new.lower()
    for word in CONSENT:
        assert word not in low, word


# ── correction history ───────────────────────────────────────────────────
def test_correction_history_original_and_corrected():
    dlg = render(envelope(_fixtures()["corrected"]))
    study = re.search(r'<details class="gde-ew-study">.*?</details>', dlg, re.S).group(0)
    assert "Original" in study and "原始" in study
    assert "Corrected:" in study and "更正后" in study
    assert "the original notice remains in history" not in study  # glance sub-line carries it
    assert "Corrected; the original notice remains in history." in glance(dlg)


def test_withdrawal_keeps_original_and_hides_current_values():
    dlg = render(envelope(_fixtures()["withdrawn"]))
    g = glance(dlg)
    assert "Evidence for XLP vs XLK was withdrawn on Oct 30." in g
    for pct in ("-1.00%", "-3.00%", "+2.06%"):
        assert pct not in g, pct
    study = re.search(r'<details class="gde-ew-study">.*?</details>', dlg, re.S).group(0)
    assert "Original" in study and "n -1.00%" in study
    assert "Withdrawn" in study and "已撤回" in study


# ── portfolio context (forbidden language) ───────────────────────────────
@pytest.mark.parametrize("name", sorted(_expected()))
def test_portfolio_context_forbidden_language_scan(name):
    exp = _expected()[name]
    dlg = render(_journey_c()) if name == "journey_c_envelope_1d253e1d" else render(envelope(_fixtures()[name]))
    text = _text(_new_elements(dlg)).lower()
    for word in FORBIDDEN:
        assert word not in text, f"{name}: {word}"


# ── partial and offline states ───────────────────────────────────────────
@pytest.mark.parametrize("name", ["partial_window_mismatch", "partial_missing_20s"])
def test_partial_renders_sentence_and_warn_word(name):
    dlg = render(envelope(_fixtures()[name]))
    g = glance(dlg)
    assert state_of(dlg) == "partial"
    assert re.search(r'<p class="gde-ew-what"><span class="l-en">[^<]+', g)
    assert ">Partial<" in g and "证据不完整" in g


def test_unavailable_and_unreadable_render_sentence_and_warn_word():
    dlg = render(envelope(None))  # rotation context present, fresh, no observation
    assert state_of(dlg) == "unavailable"
    g = glance(dlg)
    assert "Rotation data unavailable — not proof of stability." in g
    assert ">Unavailable<" in g and "暂不可用" in g
    dlg2 = render(envelope(_fixtures()["malformed_ratio"]))
    assert state_of(dlg2) == "unreadable"
    g2 = glance(dlg2)
    assert "Rotation record failed checks and is not shown." in g2
    assert ">Unreadable<" in g2 and "无法读取" in g2


def test_stale_never_uses_the_neutral_surface():
    css = (ROOT / "templates" / "_risk_envelope_band.css.j2").read_text(encoding="utf-8")
    warn_block = re.search(
        r'(#dlg-risk \.gde-ew\[data-ew-state="stale"[^}]*\{[^}]*\})', css)
    assert warn_block, "stale warn selector missing"
    assert "var(--surface-warn-subtle)" in warn_block.group(1)
    neutral = re.search(r'#dlg-risk \.gde-ew \{[^}]*\}', css).group(0)
    assert "var(--esurf-neutral-soft)" in neutral
    assert 'data-ew-state="stale"' not in neutral
    dlg = render(_journey_c())
    assert state_of(dlg) == "stale"


# ── cross-product handoff ────────────────────────────────────────────────
def test_cross_product_handoff_study_link_and_no_delivery_claim():
    fixture = _fixtures()["journey_b_both_fell"]
    dlg = render(envelope(fixture))
    study = re.search(r'<details class="gde-ew-study">.*?</details>', dlg, re.S).group(0)
    oid = fixture["notification"]["observation_id"]
    assert oid in study
    assert 'href="sector_central.html#rc-events-mount"' in study
    text = _text(_new_elements(dlg))
    for word in ("terminal", "mastermind", "delivered", "delivery"):
        assert word not in text.lower(), word


# ── §4 state matrix ──────────────────────────────────────────────────────
WORDS = {
    "partial": ("Partial", "证据不完整"), "stale": ("Stale", "已过时"),
    "conflicting": ("Conflicting horizons", "周期分歧"), "unavailable": ("Unavailable", "暂不可用"),
    "withdrawn": ("Withdrawn", "已撤回"), "corrected": ("Corrected", "已更正"),
}


@pytest.mark.parametrize("state,name,env_kind", [
    ("partial", "partial_window_mismatch", "fixture"),
    ("stale", "stale_obs", "fixture"),
    ("conflicting", "conflict_20s", "fixture"),
    ("unavailable", None, "no_observation"),
    ("withdrawn", "withdrawn", "fixture"),
    ("corrected", "corrected", "fixture"),
])
def test_state_matrix_words_and_attribute(state, name, env_kind):
    if env_kind == "no_observation":
        dlg = render(envelope(None))
    else:
        dlg = render(envelope(_fixtures()[name]))
    assert state_of(dlg) == state
    g = glance(dlg)
    assert f">{WORDS[state][0]}<" in g, WORDS[state][0]
    assert f">{WORDS[state][1]}<" in g, WORDS[state][1]


# ── quiet headline must not suppress; fragile must not create ────────────
def test_quiet_headline_does_not_suppress_qualified_observation():
    env = envelope(_fixtures()["journey_b_both_fell"])
    env["measured_state"] = dict(env["measured_state"], verdict="RISK_ON", usable=True)
    env["hazard_summary"] = dict(env["hazard_summary"], stage="NONE")
    dlg = render(env)
    assert state_of(dlg) == "observed"
    assert "Both fell; XLP fell less than XLK." in glance(dlg)


def test_fragile_headline_does_not_create_an_observation():
    env = deepcopy(_journey_c())  # real FRAGILE envelope, no observation
    assert env["hazard_summary"]["stage"] == "FRAGILE"
    dlg = render(env)
    assert state_of(dlg) == "stale"
    text = _text(glance(dlg)).lower()
    for word in ("outperformed", "trailed", "fell less", "weak"):
        assert word not in text, word
    dlg2 = render(envelope(None))
    assert state_of(dlg2) == "unavailable"


# ── Journey C exact strings ──────────────────────────────────────────────
def test_journey_c_exact_stale_strings():
    dlg = render(_journey_c())
    assert state_of(dlg) == "stale"
    g = glance(dlg)
    assert "Rotation data unavailable for Oct 30; latest is Oct 20." in g
    assert "10月30日轮动依据暂不可用；最新为10月20日。" in g
    assert "Source session Oct 20" in g
    assert "Rotation clock 2026-10-21 08:00 UTC" in g
    for pct in ("-1.00%", "+2.06%", "+1.71%", "-3.00%"):
        assert pct not in g, pct
    text = _text(g).lower()
    for word in ("outperformed", "trailed", "fell less", "weak"):
        assert word not in text, word


# ── policy footer ────────────────────────────────────────────────────────
def test_policy_footer_keeps_w9_fact_and_adds_not_an_all_clear():
    dlg = render(_journey_c())
    assert "No capital restrictions in force" in dlg
    assert "当前无资金限制" in dlg
    assert "This is not an all-clear." in dlg
    assert "这并不代表风险已经解除。" in dlg


# ── bilingual discipline ─────────────────────────────────────────────────
@pytest.mark.parametrize("name", sorted(_expected()))
def test_bilingual_spans_paired_and_no_title_attributes(name):
    exp = _expected()[name]
    dlg = render(_journey_c()) if name == "journey_c_envelope_1d253e1d" else render(envelope(_fixtures()[name]))
    new = _new_elements(dlg)
    soup = BeautifulSoup(new, "html.parser")
    en = soup.select(".l-en")
    zh = soup.select(".l-zh")
    assert len(en) == len(zh) and len(en) > 0, f"{name}: {len(en)} l-en vs {len(zh)} l-zh"
    for span in en:
        sib = span.next_sibling
        while sib is not None and not getattr(sib, "name", None):
            sib = sib.next_sibling
        assert sib is not None and "l-zh" in (sib.get("class") or []), f"{name}: {span.get_text()} has no l-zh sibling"
    assert not [t for t in soup.find_all(title=True)], "title= attribute inside new elements"
    assert 'title="' not in new


# ── CSS discipline (Chairman rule 2026-10-18) ────────────────────────────
def test_css_no_edge_stripe_no_color_literal_focus_visible():
    css = (ROOT / "templates" / "_risk_envelope_band.css.j2").read_text(encoding="utf-8")
    block = css[css.index("EW-P4.T1 descriptive early-warning"):]
    assert not re.search(r'border-(left|right|top|inline-start|inline-end|block-start)\s*:', block)
    assert not re.search(r'box-shadow[^;}]*inset', block)
    assert not re.search(r'#[0-9a-fA-F]{3,8}\b', block)
    assert "rgb(" not in block and "hsl(" not in block
    assert not re.search(r'(?:^|[^-a-z])(red|blue|green|white|black|orange|yellow|purple|gray|grey)\s*[;}]', block)
    assert ".gde-ew-next:focus-visible" in block and "outline:2px solid var(--link)" in block
    assert "outline-offset:2px" in block

    js = (ROOT / "templates" / "rotation_events.js").read_text(encoding="utf-8")
    rc_ew = js[js.index(".rc-ew{margin"):]
    rc_ew = rc_ew[:rc_ew.index("var s=document.createElement")]
    assert not re.search(r'border-(left|right|top|inline-start|inline-end|block-start)\s*:', rc_ew)
    assert not re.search(r'box-shadow[^;}]*inset', rc_ew)
    assert not re.search(r'#[0-9a-fA-F]{3,8}\b', rc_ew)
    assert "rgb(" not in rc_ew and "hsl(" not in rc_ew
    assert ".rc-ew-next:focus-visible" in rc_ew
    # the pre-existing rc-ec edge stripe is repaired (even border, warn surface)
    assert ".rc-ec-stale,.rc-ec-conflict{border:1px solid var(--line);border-radius:var(--r-ctl,8px);background:var(--surface-warn-subtle);" in js
    assert ".rc-ec-stale,.rc-ec-conflict{border-left:" not in js


# ── repair wave B (orchestrator design review) ───────────────────────────
def test_sessions_must_be_an_integer_not_a_float():
    fixture = deepcopy(_fixtures()["journey_b_both_fell"])
    fixture["notification"]["values"]["sessions"] = 2.0
    with pytest.raises(ValueError):
        lib_validate(fixture["notification"])
    assert state_of(render(envelope(fixture))) == "unreadable"


def test_unavailable_caveat_only_when_no_qualified_observation():
    caveat = "Rotation evidence is unavailable for this session."
    observed = render(envelope(_fixtures()["journey_b_both_fell"]))
    assert state_of(observed) == "observed"
    assert caveat not in observed
    missing = render(envelope(None))
    assert state_of(missing) == "unavailable"
    assert caveat in missing


def test_quality_and_build_time_are_separated():
    g = glance(render(envelope(_fixtures()["journey_b_both_fell"])))
    assert ' · <span class="gde-ew-built">' in g


def test_routes_land_on_the_registered_sector_central_hash():
    dlg = render(envelope(_fixtures()["journey_b_both_fell"]))
    new = _new_elements(dlg)
    assert "sector_central.html#moving" not in new
    assert "sector_central.html#rc-events-mount" in new
    router = (ROOT / "templates" / "si_workspace.js").read_text(encoding="utf-8")
    assert "'rc-events-mount':['moving','rc-events-mount']" in router
    js = (ROOT / "templates" / "rotation_events.js").read_text(encoding="utf-8")
    assert 'href="#rc-early-context"' not in js
    assert js.count('href="#rc-events-mount"') == 2
