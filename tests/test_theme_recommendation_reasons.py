"""Recommendation explanations must describe the deciding gate, not invent one.

The production policy is unchanged. These tests distinguish relative leadership
from own-price extension, and the final safeguard from the earlier base verdict.
"""
from copy import deepcopy
import ast
import json
from pathlib import Path

import pytest

from engine import theme_scoring as ts

ROOT = Path(__file__).resolve().parents[1]


def decide(label="dominant", macro=0.2, crowd=0.1, **fp):
    return ts._reco_decision(label, macro, crowd, {"long_sign": 1, **fp})


@pytest.mark.parametrize("label,macro,crowd,fp,expected", [
    ("deteriorating", .2, .1, {}, ("avoid", "trend_deteriorating")),
    ("fading", .2, .1, {}, ("trim", "momentum_fading")),
    ("neutral", .2, .1, {}, ("hold", "no_constructive_signal")),
    ("dominant", .2, .1, {"long_sign": -1}, ("hold", "long_trend")),
    ("emerging", .2, .1, {"long_sign": -1}, ("hold", "long_trend")),
    ("emerging", -.251, .1, {}, ("hold", "macro_limit")),
    ("emerging", -.25, .1, {}, ("enter", "emerging_checks_clear")),
    ("emerging", .2, .65, {}, ("hold", "crowding_limit")),
    ("dominant", .2, .1, {"rs_pctile": .85}, ("hold", "relative_strength_limit")),
    ("dominant", .2, .1, {"rs_pctile": .849}, ("accumulate", "leading_checks_clear")),
    ("dominant", .2, .6, {}, ("hold", "crowding_limit")),
    ("dominant", -.101, .1, {}, ("hold", "macro_limit")),
    ("dominant", -.1, .1, {}, ("accumulate", "leading_checks_clear")),
    ("dominant", .2, .1, {"ext_abs": 2.0}, ("hold", "price_extension")),
    ("dominant", .2, .99, {"ext_abs": .5}, ("accumulate", "leading_checks_clear")),
])
def test_reason_is_the_actual_base_gate(label, macro, crowd, fp, expected):
    actual = decide(label, macro, crowd, **fp)
    assert actual == expected
    assert ts._reco(label, macro, crowd, {"long_sign": 1, **fp}) == expected[0]


def test_relative_outperformance_is_not_called_absolute_extension():
    legacy = decide(rs_pctile=.95)
    measured = decide(rs_pctile=.95, ext_abs=.5)
    assert legacy == ("hold", "relative_strength_limit")
    assert measured == ("accumulate", "leading_checks_clear")
    explanation = ts._recommendation_explanation(*legacy)
    assert "Relative strength" in explanation["en"]
    assert "not established" in explanation["en"]
    assert "相对" in explanation["zh"]
    assert "price_extension" != explanation["code"]


def test_downside_expansion_has_its_own_reason():
    result = ts._reco_decision("dominant", .2, .1, {"long_sign": 1},
                               tape={"volhole": {"state": "EXPANSION_DOWN"}})
    assert result == ("trim", "downside_expansion")


@pytest.mark.parametrize("flag,code", [(True, "entry_checks_clear"),
                                       (False, "entry_not_confirmed"),
                                       (None, "entry_read_unavailable")])
@pytest.mark.parametrize("reco,reason", [("enter", "emerging_checks_clear"),
                                        ("accumulate", "leading_checks_clear")])
def test_positive_recommendation_does_not_invent_an_entry_or_price_stretch(flag, code, reco, reason):
    result = ts._recommendation_explanation(reco, reason, clean_entry=flag)
    assert result["code"] == code
    assert "extended" not in result["en"].lower()
    assert "pullback" not in result["en"].lower()
    assert "逢强" not in result["zh"]


@pytest.mark.parametrize("reco,reason", [("trim", "momentum_fading"),
                                        ("avoid", "trend_deteriorating"),
                                        ("hold", "no_constructive_signal")])
def test_nonpositive_recommendation_does_not_invent_trend_or_extension(reco, reason):
    result = ts._recommendation_explanation(reco, reason)
    assert "extended" not in result["en"].lower()
    assert "intact" not in result["en"].lower()
    assert "broad" not in result["en"].lower()


def test_final_risk_safeguard_reason_overrides_a_positive_base():
    result = ts._recommendation_explanation("hold", "leading_checks_clear",
                                            regime_demoted=True, clean_entry=True)
    assert result["code"] == "risk_off_safeguard"
    assert "risk-off" in result["en"]
    assert "entry checks are clear" not in result["en"].lower()


def test_final_cooling_safeguard_is_not_a_generic_hold():
    result = ts._recommendation_explanation("hold", "leading_checks_clear",
                                            chase_demoted=True)
    assert result["code"] == "momentum_cooling_safeguard"


@pytest.mark.parametrize("reco,reason", [("unexpected", "leading_checks_clear"),
                                        ("hold", "missing-code"),
                                        ("hold", "leading_checks_clear")])
def test_unknown_or_mismatched_reason_is_disclosed(reco, reason):
    assert ts._recommendation_explanation(reco, reason)["code"] == "reason_unavailable"


def test_reason_text_is_short_bilingual_and_json_safe():
    for code, (_, en, zh) in ts._RECO_REASON_TEXT.items():
        assert en and zh and en != zh
        assert len(en.split()) <= 14, (code, en)
        assert "<" not in en + zh
        json.dumps({"code": code, "en": en, "zh": zh}, allow_nan=False)


def test_explaining_a_gate_does_not_mutate_inputs():
    fp = {"long_sign": 1, "rs_pctile": .95, "ext_abs": .5}
    before = deepcopy(fp)
    assert ts._reco_decision("dominant", .2, .1, fp)[0] == "accumulate"
    assert fp == before


def test_real_producer_publishes_the_explanation_after_safeguards():
    source = (ROOT / "engine/theme_scoring.py").read_text()
    tree = ast.parse(source)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_theme_intel")
    calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    decision = next(n for n in calls if n.func.id == "_reco_decision")
    explain = next(n for n in calls if n.func.id == "_recommendation_explanation")
    assert decision.lineno < explain.lineno
    assert {x.arg for x in explain.keywords} >= {"regime_demoted", "chase_demoted", "clean_entry"}
    assert '"reco_why_en": reco_explanation["en"]' in source
    assert '"reco_why_zh": reco_explanation["zh"]' in source
    assert '"reco_reason_code": reco_explanation["code"]' in source
    for path in ["templates/baskets_desk.js", "templates/basket_detail.html.j2"]:
        consumer = (ROOT / path).read_text()
        assert "reco_why_en" in consumer and "reco_why_zh" in consumer


def test_frozen_incumbent_and_current_policy_agree_on_boundary_grid():
    import itertools
    fixture = ROOT / "tests/fixtures/theme_recommendation_reasons/legacy_reco.py"
    namespace = dict(vars(ts))
    exec(compile(fixture.read_text(), str(fixture), "exec"), namespace)
    old = namespace["_reco"]
    labels = ("dominant", "emerging", "neutral", "fading", "deteriorating", "unknown")
    macros = (-.3, -.25, -.1, 0., .2, float("nan"))
    crowds = (0., .599, .6, .649, .65, .9, float("nan"))
    shapes = ({}, {"rs_pctile": .849}, {"rs_pctile": .85}, {"rs_pctile": .95},
              {"ext_abs": .5, "rs_pctile": .95}, {"ext_abs": 1.999}, {"ext_abs": 2.0})
    tested = 0
    for label, macro, crowd, shape, sign, falling in itertools.product(
            labels, macros, crowds, shapes, (-1, 0, 1), (False, True)):
        fp = {"long_sign": sign, **shape}
        tape = {"volhole": {"state": "EXPANSION_DOWN"}} if falling else None
        assert ts._reco(label, macro, crowd, fp, tape=tape) == old(label, macro, crowd, fp, tape=tape)
        tested += 1
    assert tested == 10584


@pytest.mark.parametrize("path", ["templates/baskets_desk.js", "templates/basket_detail.html.j2"])
def test_actual_javascript_consumer_uses_dated_reason_and_safe_legacy_fallback(path):
    import re
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required to execute the actual JavaScript consumer")
    source = (ROOT / path).read_text()
    match = re.search(r"const RECO_NOENTRY_WHY = t => \{.*?\n\};", source, re.S)
    assert match
    rows = [
        {"reco_reason_code": "entry_not_confirmed", "reco_why_en": "Entry not confirmed.", "reco_why_zh": "入场未确认。"},
        {"reco_reason_code": "entry_read_unavailable", "reco_why_en": "Entry information unavailable.", "reco_why_zh": "入场信息暂缺。"},
        {"reco_why_en": "Add aggressively", "reco_why_zh": "立即加仓"},
        {"reco_reason_code": "entry_checks_clear", "reco_why_en": "Add aggressively", "reco_why_zh": "立即加仓"},
        {"reco_reason_code": "entry_read_unavailable", "reco_why_en": "missing", "reco_why_zh": " "},
        {"reco_reason_code": "entry_not_confirmed", "reco_why_en": "<img src=x onerror=alert(1)>", "reco_why_zh": "<script>1</script>"},
        None,
    ]
    script = r'''
const esc=s=>(s==null?'':String(s)).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const L=(en,zh)=>`<span class="l-en">${en}</span><span class="l-zh">${zh}</span>`;
''' + match.group(0) + "\nconst rows=" + json.dumps(rows) + ";\nconsole.log(JSON.stringify(rows.map(RECO_NOENTRY_WHY)));"
    outputs = json.loads(subprocess.check_output([node, "-e", script], text=True))
    assert "Entry not confirmed." in outputs[0] and "入场未确认。" in outputs[0]
    assert "unavailable" in outputs[1] and "暂缺" in outputs[1]
    for index in (2, 3, 4, 6):
        assert "Theme in favour; no clean entry is confirmed." in outputs[index]
        assert "Add aggressively" not in outputs[index]
    assert "<img" not in outputs[5] and "<script>" not in outputs[5]
    assert "&lt;img" in outputs[5] and "&lt;script&gt;" in outputs[5]
    subject = "th" if path.endswith(".j2") else "t"
    assert f"recoNoEntry({subject})?RECO_NOENTRY_WHY({subject})" in source
    assert "no member has a clean entry" not in source


def test_desk_and_detail_use_identical_nonentry_explanation_contract():
    import re
    sources = [(ROOT / name).read_text() for name in ("templates/baskets_desk.js", "templates/basket_detail.html.j2")]
    snippets = [re.search(r"const RECO_NOENTRY_WHY = t => \{.*?\n\};", source, re.S).group(0) for source in sources]
    assert snippets[0] == snippets[1]


@pytest.mark.parametrize("path", ["templates/baskets_desk.js", "templates/basket_detail.html.j2"])
def test_legacy_relative_strength_texture_is_not_presented_as_price_stretch(path):
    import re
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for the native reason-text formatter")
    source = (ROOT / path).read_text()
    helper = re.search(r"function rolloverReasonText\(reasons, zh=false\)\{.*?\n\}", source, re.S)
    assert helper
    program = helper.group(0) + "\nconsole.log(JSON.stringify([rolloverReasonText(['extended (RS 99%ile)','breadth narrowing']),rolloverReasonText(['extended (RS 99%ile)'],true),rolloverReasonText(null)]));"
    actual = json.loads(subprocess.check_output([node, "-e", program], text=True))
    assert actual == ["high relative strength · breadth narrowing", "相对强势偏高", ""]
    assert "very extended (RS ≥95%ile)" not in source
    assert "not an own-price extension measure" in source
    assert "${L('WAIT FOR ENTRY','等待入场')}" in source
