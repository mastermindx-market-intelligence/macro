"""GD-EW-P4-B1 (EW-P4.T1): descriptive early-warning observation UI, consumer-only.

The Risk Radar envelope band renders an optional ``latest_observation`` view
wrapper (contract frozen in the EW-P4.T1 packet, §A) after validating it through
a Jinja mirror of lib/rotation_observation_notification.py plus the stricter
engine id rule. Descriptive only: no forecast, odds, sizing or delivery copy.

Every test row below is one rubric row of the packet's §I; see
research/grey_deer/evidence/EW_P4_DESCRIPTIVE_UI_2026-10-31.md for the mapping.
"""
from __future__ import annotations

import collections
import hashlib
import json
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from lib.rotation_observation_notification import validate as lib_validate
from tests.test_dashboard_template_render import _env
from tests.test_macro_risk_dialog import _dlg, _vm

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


_RENDER_CACHE: dict[str, str] = {}


@lru_cache(maxsize=1)
def _dashboard_template():
    """Compile once per process (#10414). Building the Environment and compiling the
    dashboard and its includes cost about 1.2 s on every call, 143 times over, and that
    took the dashboard-render-contract job past its 15-minute limit. Only the compile is
    shared: render() below still runs the template against each distinct envelope."""
    return _env().get_template("dashboard.html.j2")


def _canon(value):
    """Type-tagged canonical form. json.dumps(sort_keys=True, default=repr) would merge
    {1: x} with {"1": x}, a tuple with a list, and an object with the string of its
    repr; those are exactly the odd-typed inputs this suite feeds the renderer."""
    if isinstance(value, dict):
        return ("dict", tuple(sorted(((_canon(k), _canon(v)) for k, v in value.items()), key=repr)))
    if isinstance(value, (list, tuple)):
        return (type(value).__name__, tuple(_canon(v) for v in value))
    return (type(value).__name__, repr(value))


def render(env: dict) -> str:
    """One dashboard render per distinct envelope (FU2) on the once-compiled template
    (#10414). The template render is ~3 s and most cases re-render the same fixture, so
    the suite was render-bound (FU2: ~500 s locally). The key is a type-tagged canonical
    form of the envelope; the ORIGINAL object is rendered, so odd-typed cases
    (non-object wrappers, bad timestamps) keep their exact inputs."""
    key = repr(_canon(env))
    if key not in _RENDER_CACHE:
        _RENDER_CACHE[key] = _dlg(_dashboard_template().render(**_vm(risk_envelope=env), mode="macro"))
    return _RENDER_CACHE[key]


def glance(dlg: str) -> str:
    m = re.search(r'<div class="gde-ew".*?</div>', dlg, re.S)
    assert m, "glance #gde-ew missing"
    return m.group(0)


EW_SELECTORS = (
    "div.gde-ew", "div.gde-ew-brief-h", "div.gde-ew-tablewrap", "details.gde-ew-study",
    "span.gde-policy-caveat", "span.gde-scope",
    # EW-P4-FU F-3: the drawer lines outside div.gde-ew (horizons, context, against, undo, next)
    "div.gde-ew-horizons", "p.gde-ew-contextline", "p.gde-ew-h", "ul.gde-ew-against",
    "p.gde-ew-undo", "p.gde-ew-nextline",
)


def _new_elements(dlg: str) -> str:
    """Concatenate every element this lane added (parsed, not regex-scraped)."""
    soup = BeautifulSoup(dlg, "html.parser")
    picked = [el for selector in EW_SELECTORS for el in soup.select(selector)]
    ids = {id(el) for el in picked}
    parts, seen = [], set()
    for el in picked:
        if id(el) in seen or any(id(p) in ids for p in el.parents):
            continue  # nested inside another selected element: already counted once
        seen.add(id(el))
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
                 "Both sectors fell; consumer staples (XLP) fell less than technology (XLK).", "Source session Oct 30",
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
    for frag in ("-1.00%", "-3.00%", "+2.06%", ">Consumer staples (XLP)<", ">Technology (XLK)<",
                 ">必需消费（XLP）<", ">科技（XLK）<",
                 "Receiver (numerator)", "Donor (denominator)", ">Relative<", ">相对<",
                 ">Consumer staples (XLP) vs technology (XLK)<", ">必需消费（XLP） 对 科技（XLK）<",
                 "2 sessions, Oct 29 → Oct 30 · US cash sessions"):
        assert frag in table, frag
    # D1: the relative row names the pair; it never carries a stray dash cell
    assert ">—<" not in table
    assert "Both sectors fell; consumer staples (XLP) fell less than technology (XLK)." in dlg


def test_side_by_side_ratio_partial_window_mismatch_withholds_numbers():
    dlg = render(envelope(_fixtures()["partial_window_mismatch"]))
    assert 'class="gde-ew-legs"' not in dlg  # legs and ratio withheld with the window
    g = glance(dlg)
    assert "Partial evidence for consumer staples (XLP) vs technology (XLK); ratio withheld." in g
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
    assert "Evidence for consumer staples (XLP) vs technology (XLK) was withdrawn on Oct 30." in g
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
    assert "Both sectors fell; consumer staples (XLP) fell less than technology (XLK)." in glance(dlg)


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
    # B1: the glance is styled by a governed stylesheet, never a runtime-injected one
    assert ".rc-ew{" not in js
    assert not re.search(r"\.rc-ew[\w-]*(?::[\w-]+)?\s*[,{]", js)
    rc_ew = re.sub(r"/\*.*?\*/", "", (ROOT / "templates" / "rotation_glance.css").read_text(encoding="utf-8"), flags=re.S)
    assert not re.search(r'border-(left|right|top|inline-start|inline-end|block-start)\s*:', rc_ew)
    assert not re.search(r'box-shadow[^;}]*inset', rc_ew)
    assert not re.search(r'#[0-9a-fA-F]{3,8}\b', rc_ew)
    assert "rgb(" not in rc_ew and "hsl(" not in rc_ew
    assert not re.search(r'(?:^|[^-a-z])(red|blue|green|white|black|orange|yellow|purple|gray|grey)\s*[;}]', rc_ew)
    assert ".rc-ew-next:focus-visible" in rc_ew and "outline:2px solid var(--link)" in rc_ew
    assert "outline-offset:2px" in rc_ew
    # sizes come from the --fs-* scale, never literal px
    assert not re.search(r"font-size\s*:\s*\d", rc_ew) and "var(--fs-" in rc_ew
    # light is its own art direction: a raised white panel with the card shadow
    assert ':root[data-theme="light"] .rc-ew {' in rc_ew and "var(--card-shadow)" in rc_ew
    # host-scoped tokens always carry their fallback on Sector Central
    for tok in ("--ink-1", "--ink-2", "--ink-3", "--r-card", "--r-ctl"):
        assert f"var({tok})" not in rc_ew, tok
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
    assert "sector_central.html#moving" not in dlg
    assert "sector_central.html#rc-events-mount" in new
    # the brief's "Next" route and the study's stable link use the same hash
    assert dlg.count('href="sector_central.html#rc-events-mount"') == 3
    router = (ROOT / "templates" / "si_workspace.js").read_text(encoding="utf-8")
    assert "'rc-events-mount':['moving','rc-events-mount']" in router
    js = (ROOT / "templates" / "rotation_events.js").read_text(encoding="utf-8")
    assert 'href="#rc-early-context"' not in js
    assert js.count('href="#rc-events-mount"') == 2


def test_record_fields_are_escaped_and_history_is_separated():
    """Repair wave C: record-supplied strings render as text in both hosts' new
    elements, and the original and current values sit on separate lines."""
    bad = "<img src=x onerror=alert(1)>"
    w = deepcopy(_fixtures()["withdrawn"])
    w["previous"]["observation_id"] = bad
    w["basis"] = bad
    w["notification"]["source_as_of"] = "2026-10-29"  # lib _opt_iso_date: a real date; markup here is covered below
    w["coverage"] = {"evaluable_2s": bad, "registered_pairs": 8, "missing_pair_ids": []}
    dlg = render(envelope(w))
    assert state_of(dlg) == "withdrawn"
    new = _new_elements(dlg)
    assert "<img" not in new and "&lt;img" in new
    assert '<br><span class="l-en">Current: Withdrawn' in dlg  # raw render: the parser re-serializes <br> as <br/>
    corrected = render(envelope(_fixtures()["corrected"]))
    assert '<br><span class="l-en">Corrected: ' in corrected
    quiet = _new_elements(render(envelope(None, rotation={"coverage": bad})))
    assert "<img" not in quiet and "&lt;img" in quiet
    # round 2: markup in a withdrawal's source_as_of fails the lib date check, so it renders unreadable, never as text
    s = deepcopy(_fixtures()["withdrawn"])
    s["notification"]["source_as_of"] = "2026-10-29" + bad
    with pytest.raises(ValueError):
        lib_validate(s["notification"])
    sdlg = render(envelope(s))
    assert state_of(sdlg) == "unreadable"
    assert "<img" not in _new_elements(sdlg)


# ---------------------------------------------------------------------------
# Visual receipt: the committed shots depict the source under test.
# ---------------------------------------------------------------------------

EVIDENCE = ROOT / "research" / "evidence" / "ew_p4_descriptive_ui_20261031"


@pytest.mark.parametrize("key", ["values", "source_as_of"])
@pytest.mark.parametrize("name", ["withdrawn", "journey_b_both_fell"])
def test_review_r1_explicit_source_as_of_and_values_keys(name, key):
    fixture = deepcopy(_fixtures()[name])
    del fixture["notification"][key]
    with pytest.raises(ValueError):
        lib_validate(fixture["notification"])
    assert state_of(render(envelope(fixture))) == "unreadable"


@pytest.mark.parametrize("bad", ["rotobs_x", ["a"], 7])
def test_review_r1_present_non_object_wrapper_is_unreadable(bad):
    assert state_of(render(envelope(bad))) == "unreadable"


def test_review_r1_null_wrapper_stays_absent():
    assert state_of(render(envelope(None, rotation={"latest_observation": None}))) == "unavailable"


def test_review_r1_observation_id_is_selectable_monospace():
    css = (ROOT / "templates" / "_risk_envelope_band.css.j2").read_text(encoding="utf-8")
    assert "#dlg-risk .gde-ew-id {user-select:all; font-family:var(--font-mono);}" in css


def test_fu2_radar_band_wraps_raises_and_matches_sector_central():
    css = re.sub(r"/\*.*?\*/", "", (ROOT / "templates" / "_risk_envelope_band.css.j2").read_text(encoding="utf-8"), flags=re.S)
    # D2: the sources table wraps at 320 instead of clipping inside a fixed floor, and
    # below 481 px it reduces to stacked labelled rows instead of letter-level breaks
    # ("SOURC E", "Marke t" in the first FU2 light shots at 390).
    assert "min-width:460px" not in css
    cell = re.search(r"#dlg-risk \.gde-tbl th, #dlg-risk \.gde-tbl td \{([^}]*)\}", css).group(1)
    assert "overflow-wrap:break-word" in cell and "anywhere" not in cell
    narrow = css[css.index("@media(max-width:480px)"):]
    narrow = narrow[:narrow.index("\n}\n") + 3]
    assert "#dlg-risk .gde-tbl thead {position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap;}" in narrow
    assert "#dlg-risk .gde-tbl td {display:grid; grid-template-columns:minmax(0, 7.5em) minmax(0, 1fr);" in narrow
    assert "#dlg-risk .gde-tbl td > * {grid-column:2;}" in narrow  # the required badge stays in the value column
    assert 'html:not([data-lang="zh"]) #dlg-risk .gde-tbl td::before {content:attr(data-label-en) / "";}' in narrow
    assert 'html[data-lang="zh"] #dlg-risk .gde-tbl td::before {content:attr(data-label-zh) / "";}' in narrow
    # Review (FU2): labels and prose read in the UI face on the Radar host, where the
    # page-wide td rule sets the numeric face; the As-of date never splits.
    assert "font-family:var(--font-ui); letter-spacing:normal;}" in narrow.split("td::before {color")[1].split("\n")[0]
    assert '#dlg-risk .gde-tbl td[data-label-en="As of"] {white-space:nowrap;}' in css
    assert "#dlg-risk .gde-tbl td .l-en, #dlg-risk .gde-tbl td .l-zh {font-family:var(--font-ui); letter-spacing:normal;}" in css
    assert "#dlg-risk .gde-ew-legs td:not(.tnum) {font-family:var(--font-ui); letter-spacing:normal; font-variant-numeric:normal;}" in css
    soup = BeautifulSoup(render(envelope(deepcopy(_fixtures()["observed_rise"]))), "html.parser")
    heads = [th.select_one(".l-en").get_text(strip=True) for th in soup.select(".gde-tbl thead th")]
    heads_zh = [th.select_one(".l-zh").get_text(strip=True) for th in soup.select(".gde-tbl thead th")]
    rows = soup.select(".gde-tbl tbody tr")
    # Review (FU2): every cell child is an element, so the stacked grid never auto-places
    # a bare text run into the label column; explicit roles keep the table semantics.
    assert soup.select_one(".gde-tbl")["role"] == "table"
    assert all(th["role"] == "columnheader" for th in soup.select(".gde-tbl thead th"))
    for td in soup.select(".gde-tbl tbody td"):
        assert td["role"] == "cell"
        assert not [t for t in td.find_all(string=True, recursive=False) if t.strip()], td
    assert rows
    for row in rows:
        cells = row.find_all("td")
        assert [td["data-label-en"] for td in cells] == heads
        assert [td["data-label-zh"] for td in cells] == heads_zh
    # D6: legs row headers are sentence-case UI labels, as on Sector Central
    legs_th = re.search(r"#dlg-risk \.gde-ew-legs th \{([^}]*)\}", css).group(1)
    for decl in ("text-transform:none", "letter-spacing:normal", "font-family:var(--font-ui)", "font-size:var(--fs-label)"):
        assert decl in legs_th, decl
    # L3: light raises the card as a white panel with the card shadow; only the surface token
    # moves, so warning-state backgrounds keep winning
    assert 'html[data-theme="light"] #dlg-risk .gde-ew {--gde-ew-surface:var(--panel); box-shadow:var(--card-shadow);}' in css
    assert "background:var(--gde-ew-surface)" in css
    light_rule = css[css.index('html[data-theme="light"] #dlg-risk .gde-ew {'):]
    assert "background:" not in light_rule[:light_rule.index("}")]


def test_review_r1_site_copy_is_byte_identical_to_template():
    for name in ("rotation_events.js", "rotation_glance.css"):
        site = ROOT / "site" / name
        if not site.exists():
            pytest.skip("site/ not materialized in this sparse tree")
        assert site.read_bytes() == (ROOT / "templates" / name).read_bytes(), name


def test_sector_central_links_the_governed_glance_stylesheet():
    tpl = (ROOT / "templates" / "sector_central.html.j2").read_text(encoding="utf-8")
    assert '<link rel="stylesheet" href="rotation_glance.css">' in tpl
    build = (ROOT / "scripts" / "build_sector_central.py").read_text(encoding="utf-8")
    assert '"rotation_glance.css"' in build
    page = ROOT / "site" / "sector_central.html"
    if page.exists():
        assert re.search(r'<link rel="stylesheet" href="rotation_glance\.css\?v=[0-9a-f]{8}">',
                         page.read_text(encoding="utf-8"))


def _git_blob_id(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def test_receipt_shots_depict_the_source_under_test():
    """The shots were rendered from the receipt's source_revision. A file cannot name
    the commit that contains it, so the receipt binds the render INPUTS instead: every
    one must be byte-identical (git blob id) on the tree CI checks out, which makes the
    receipt hold for the exact head under test and fail on any later render edit."""
    rec = json.loads((EVIDENCE / "receipt.json").read_text(encoding="utf-8"))
    assert rec["base"] == "1d253e1d25f22c61d1bcf8126b13b0229f26ccbd"
    eq = rec["pr_source_equivalence"]
    assert eq["all_equal"] is True
    paths = {r["path"] for r in eq["render_files"]}
    assert {
        "templates/_risk_envelope_band.html.j2",
        "templates/_risk_envelope_band.css.j2",
        "templates/rotation_events.js",
        "templates/rotation_glance.css",
        # Review (FU2): the tokens the L3/L4 claims rest on, the Radar host page and
        # the Sector Central page are render inputs too; a later edit to any of
        # them fails this test instead of leaving the shots silently stale.
        "templates/theme.css",
        "templates/dashboard.html.j2",
        "templates/_risk_radar_workspace.html.j2",
        "templates/sector_central.html.j2",
        "templates/si_workspace.js",
        "site/theme.css",
        "site/si_workspace.js",
        "tests/probe_ew_p4_descriptive_ui_browser.py",
    } <= paths
    assert {f"tests/fixtures/ew_p4_observation/{p.name}" for p in FIX.glob("*.json")} <= paths
    for row in eq["render_files"]:
        p = ROOT / row["path"]
        if row["path"].startswith("site/") and not p.exists():
            continue  # sparse local trees omit site/; templates/ carries the same bytes
        assert row["blob_at_source_revision"] == row["blob_on_pr_branch"], row["path"]
        assert _git_blob_id(p) == row["blob_at_source_revision"], row["path"]

    glance = (ROOT / "templates" / "rotation_glance.css").read_bytes()
    assert rec["glance_css_sha256"] == hashlib.sha256(glance).hexdigest()

    # EW-P5 FU2 recapture: 3 families × EN/ZH × dark/light × 1440/1280/390/320
    # (48) + 6 Radar states × 2 themes (12) + 4 Sector Central states × 2 themes (8).
    cases = rec["cases"]
    assert len(cases) == 68
    widths = (1440, 1280, 390, 320)
    themes = ("dark", "light")
    assert rec["matrix"] == {"widths": list(widths), "themes": list(themes), "langs": ["en", "zh"],
                             "state_shots": "every degraded state at 390/en in both themes on both hosts"}
    matrix = {(c["surface"], c["state"], c["lang"], c["theme"], c["width"]) for c in cases}
    for surface, state in (("radar", "stale"), ("radar", "observed"), ("sc", "observed")):
        for lang in ("en", "zh"):
            for theme in themes:
                for width in widths:
                    assert (surface, state, lang, theme, width) in matrix
    # L1: every degraded state is shown in BOTH art directions, not dark only.
    for state in ("partial", "conflicting", "unavailable", "withdrawn", "corrected", "unreadable"):
        for theme in themes:
            assert ("radar", state, "en", theme, 390) in matrix, (state, theme)
    for state in ("stale", "withdrawn", "corrected", "unreadable"):
        for theme in themes:
            assert ("sc", state, "en", theme, 390) in matrix, (state, theme)
    # L2: real Tab navigation reached the disclosure, a visible focus outline was
    # measured and Enter opened it — once per (host, width, theme), both themes.
    keyboard = {}
    for c in cases:
        kb = c["keyboard_details"]
        if kb:
            assert kb["reached"] is True and kb["opened_by_enter"] is True and kb["focus_outline"] is True, c["screenshot"]
            assert c["focus_outline"] is True, c["screenshot"]
            keyboard[(c["surface"], c["width"], c["theme"])] = kb
    for surface in ("radar", "sc"):
        for width in widths:
            for theme in themes:
                assert (surface, width, theme) in keyboard, (surface, width, theme)
    # L4: every visible Radar warning run (input caveats + sources-table warn words)
    # resolved to ONE computed colour and that colour is the theme's --ink-warn token;
    # the token differs between the two art directions. Sector Central samples nothing.
    tokens = collections.defaultdict(set)
    for case in cases:
        ink = case["warning_ink"]
        if case["surface"] == "radar":
            assert ink["consistent"] is True and ink["matches_token"] is True, case["screenshot"]
            assert ink["caveat"] and ink["warn"], case["screenshot"]
            assert set(ink["caveat"]) | set(ink["warn"]) == {ink["token_ink_warn"]}, case["screenshot"]
            tokens[case["theme"]].add(ink["token_ink_warn"])
        else:
            assert ink is None, case["screenshot"]
    assert len(tokens["dark"]) == 1 and len(tokens["light"]) == 1 and tokens["dark"] != tokens["light"]
    for case in cases:
        shot = EVIDENCE / case["screenshot"]
        assert hashlib.sha256(shot.read_bytes()).hexdigest() == case["sha256"], case["screenshot"]
        assert case["no_horizontal_overflow"] is True, case["screenshot"]
        assert case["page_errors"] == [], case["screenshot"]
    for sheet in ("contact-radar-observed", "contact-radar-stale", "contact-sc-observed",
                  "contact-sc-states", "contact-radar-states"):
        assert (EVIDENCE / f"{sheet}.png").exists(), sheet


# ---------------------------------------------------------------------------
# EW-P4-FU: the UI validator rejects what the lib validator rejects.
# ---------------------------------------------------------------------------
def test_fu_blank_pair_id_and_impossible_date_fixtures_are_unreadable():
    for name in ("malformed_blank_pair", "malformed_calendar"):
        fixture = _fixtures()[name]
        with pytest.raises(ValueError):
            lib_validate(fixture["notification"])
        assert state_of(render(envelope(fixture))) == "unreadable", name


@pytest.mark.parametrize("bad", ["2026-00-10", "2025-13-01", "2026-02-30", "2026-04-31", "2025-02-29", "0000-01-01"])
def test_fu_calendar_invalid_event_dates_are_unreadable(bad):
    fixture = deepcopy(_fixtures()["observed_rise"])
    fixture["notification"]["event_as_of"] = bad
    fixture["notification"]["source_as_of"] = bad
    with pytest.raises(ValueError):
        lib_validate(fixture["notification"])
    assert state_of(render(envelope(fixture))) == "unreadable", bad


@pytest.mark.parametrize("good", ["2024-02-29", "2026-04-30", "2025-12-31"])
def test_fu_real_calendar_dates_still_pass_the_grammar(good):
    fixture = deepcopy(_fixtures()["observed_rise"])
    fixture["notification"]["event_as_of"] = good
    fixture["notification"]["source_as_of"] = good
    assert state_of(render(envelope(fixture))) != "unreadable", good


@pytest.mark.parametrize("pid", ["   ", "\t", " \n ", "\x1c", "\x1f", "\x85", "\u3000", "\u2028 \xa0"])
def test_fu_whitespace_only_pair_id_is_unreadable(pid):
    fixture = deepcopy(_fixtures()["observed_rise"])
    fixture["notification"]["pair_id"] = pid
    with pytest.raises(ValueError):
        lib_validate(fixture["notification"])
    assert state_of(render(envelope(fixture))) == "unreadable", repr(pid)


@pytest.mark.parametrize("pid", ["\ufeff", "a" * 128, "\U0001F600" * 128, "x\u3000"])
def test_fu_pair_id_the_lib_accepts_is_not_unreadable(pid):
    """Round 2: the template agrees with lib _req_str on what is blank and on code-point length."""
    fixture = deepcopy(_fixtures()["observed_rise"])
    fixture["notification"]["pair_id"] = pid
    lib_validate(fixture["notification"])
    assert state_of(render(envelope(fixture))) != "unreadable", repr(pid)


@pytest.mark.parametrize("pid", ["a" * 129, "\U0001F600" * 129])
def test_fu_pair_id_over_128_code_points_is_unreadable(pid):
    fixture = deepcopy(_fixtures()["observed_rise"])
    fixture["notification"]["pair_id"] = pid
    with pytest.raises(ValueError):
        lib_validate(fixture["notification"])
    assert state_of(render(envelope(fixture))) == "unreadable", len(pid)


@pytest.mark.parametrize("bad", ["2025-13-01", "2026-02-30", "2025-02-29", "0000-01-01", "2026-1-01", "garbage"])
def test_fu_withdrawal_with_an_invalid_source_date_is_unreadable(bad):
    fixture = deepcopy(_fixtures()["withdrawn"])
    fixture["notification"]["source_as_of"] = bad
    with pytest.raises(ValueError):
        lib_validate(fixture["notification"])
    assert state_of(render(envelope(fixture))) == "unreadable", bad


def test_fu_withdrawal_with_a_real_earlier_source_date_still_renders_withdrawn():
    fixture = deepcopy(_fixtures()["withdrawn"])
    event = fixture["notification"]["event_as_of"]
    earlier = f"{int(event[:4]) - 1}{event[4:]}"
    fixture["notification"]["source_as_of"] = earlier
    lib_validate(fixture["notification"])
    assert state_of(render(envelope(fixture))) == "withdrawn", earlier


BAD_STAMPS = ["garbage-but-long-enough-Z", "2026-10-30T21:15:00<b>Z", "2026-10-30T21:15:60Z",
              "2026-02-30T21:15:00+00:00", "2026-10-30<img src=x>T21:15:00Z"]


@pytest.mark.parametrize("key", ["observed_at", "not_after"])
@pytest.mark.parametrize("bad", BAD_STAMPS)
def test_fu_timestamp_the_lib_rejects_is_unreadable(key, bad):
    """Round 2: the stamp check is a subset of lib _aware_utc, not a length-and-suffix test."""
    fixture = deepcopy(_fixtures()["observed_rise"])
    fixture["notification"][key] = bad
    with pytest.raises(ValueError):
        lib_validate(fixture["notification"])
    out = render(envelope(fixture))
    assert state_of(out) == "unreadable", (key, bad)
    assert "<img" not in _new_elements(out) and "<b>" not in _new_elements(out)


@pytest.mark.parametrize("suffix", ["+00:00", "Z"])
def test_fu_producer_isoformat_stamps_are_readable(suffix):
    """isoformat() carries six fraction digits when microseconds are set; Z is the other canonical UTC suffix."""
    fixture = deepcopy(_fixtures()["observed_rise"])
    n = fixture["notification"]
    n["observed_at"] = n["observed_at"].replace("+00:00", ".123456" + suffix)
    n["not_after"] = n["not_after"].replace("+00:00", suffix)
    lib_validate(n)
    assert state_of(render(envelope(fixture))) != "unreadable", suffix


def test_fu_scan_reaches_every_drawer_line():
    """F-3: the parsed scan now covers the drawer lines outside div.gde-ew."""
    text = _text(_new_elements(render(envelope(_fixtures()["observed_rise"]))))
    for phrase in ("What argues against this", "What would undo this", "Next: "):
        assert phrase in text, phrase


# ---------------------------------------------------------------------------
# EW-P4-ACT O06: no consumer claims an id without a source-owned receipt.
# ---------------------------------------------------------------------------
def _no_receipt(v):
    v.pop("recorded")


def _set_receipt(key, value):
    def mutate(v):
        v["recorded"][key] = value
    return mutate


O06_VARIANTS = {
    "missing": _no_receipt,
    "null": lambda v: v.update(recorded=None),
    "non_object": lambda v: v.update(recorded="macro.rotation_events.ledger"),
    "array": lambda v: v.update(recorded=[v["recorded"]]),
    "wrong_source": _set_receipt("source", "macro.rotation_events.cache"),
    "wrong_ledger": _set_receipt("ledger", "rotation_events/other.jsonl"),
    "uppercase_hex": lambda v: v["recorded"].update(receipt_sha256=v["recorded"]["receipt_sha256"].upper()),
    "short_digest": lambda v: v["recorded"].update(receipt_sha256=v["recorded"]["receipt_sha256"][1:]),
    "non_string_digest": _set_receipt("receipt_sha256", 7),
}


def _observation_id_attr(dlg: str) -> str:
    m = re.search(r'id="gde-ew"[^>]*data-observation-id="([^"]*)"', dlg)
    assert m, "data-observation-id missing"
    return m.group(1)


def test_o06_a_receipted_view_keeps_its_id():
    fixture = _fixtures()["journey_b_both_fell"]
    dlg = render(envelope(fixture))
    assert state_of(dlg) == "observed"
    assert _observation_id_attr(dlg) == fixture["notification"]["observation_id"]


@pytest.mark.parametrize("variant", sorted(O06_VARIANTS))
def test_o06_a_view_without_its_ledger_receipt_is_unreadable_and_claims_no_id(variant):
    fixture = deepcopy(_fixtures()["journey_b_both_fell"])
    O06_VARIANTS[variant](fixture)
    lib_validate(fixture["notification"])  # the notification itself is still lib-valid
    dlg = render(envelope(fixture))
    assert state_of(dlg) == "unreadable", variant
    assert _observation_id_attr(dlg) == "", variant
    assert fixture["notification"]["observation_id"] not in dlg, variant


def test_o06_an_invalid_view_never_echoes_its_raw_id():
    """Supersedes the B1 echo: malformed_id used to carry rotobs_XYZ escaped in the attribute."""
    dlg = render(envelope(_fixtures()["malformed_id"]))
    assert state_of(dlg) == "unreadable"
    assert _observation_id_attr(dlg) == ""
    assert "rotobs_XYZ" not in dlg


def test_o06_a_future_session_view_is_unreadable_and_claims_no_id():
    """A lib-valid, receipted view for a later session must not echo its id either."""
    fixture = _fixtures()["malformed_future"]
    lib_validate(fixture["notification"])
    assert fixture["notification"]["event_as_of"] > SESSION
    dlg = render(envelope(fixture))
    assert state_of(dlg) == "unreadable"
    assert _observation_id_attr(dlg) == ""
    assert fixture["notification"]["observation_id"] not in dlg


# ── sector display names: glance JS, Radar band and registry agree ──────────
def _js_sector_names() -> dict:
    src = (ROOT / "templates" / "rotation_events.js").read_text(encoding="utf-8")
    body = re.search(r"var SECTOR_NAMES = \{(.*?)\};", src, re.S).group(1)
    return {k: (en, zh) for k, en, zh in
            re.findall(r"(\w+): \['([^']*)', '([^']*)'\]", body)}


def _band_sector_names() -> dict:
    src = (ROOT / "templates" / "_risk_envelope_band.html.j2").read_text(encoding="utf-8")
    body = re.search(r"\{% set _EW_SECTOR_NAMES = \{(.*?)\} %\}", src, re.S).group(1)
    return {k: (en, zh) for k, en, zh in
            re.findall(r"'(\w+)': \('([^']*)', '([^']*)'\)", body)}


@pytest.mark.needs_full_checkout("data")
def test_sector_display_names_mirror_the_registry_in_both_renderers():
    js, band = _js_sector_names(), _band_sector_names()
    assert len(js) == 5 and js == band
    pairs = json.loads((ROOT / "data" / "oracle" / "ratio_pairs.json").read_text(encoding="utf-8"))["pairs"]
    rows = pairs if isinstance(pairs, list) else list(pairs.values())
    defensive = [r for r in rows if "defensive_sector" in json.dumps(r)]
    assert defensive, "registry lost its defensive-sector pairs"
    for r in defensive:
        en_num, en_den = r["name_en"].split(" vs ")
        zh_num, zh_den = r["name_zh"].split(" vs ")
        assert js[r["num"]] == (en_num.lower(), zh_num), r["id"]
        assert js[r["den"]] == (en_den.lower(), zh_den), r["id"]


def test_the_banned_relative_words_never_return_to_rotation_copy():
    for path in ("templates/rotation_events.js", "templates/_risk_envelope_band.html.j2", "app/mailer.py"):
        text = (ROOT / path).read_text(encoding="utf-8")
        assert "relative shelter" not in text.lower(), path
        assert "抗跌" not in text, path
