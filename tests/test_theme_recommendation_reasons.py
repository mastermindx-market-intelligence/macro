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
    assert "Relative-strength filter" in explanation["en"]
    assert "does not measure" in explanation["en"]
    # Another canonical texture can independently show genuine price extension.
    # This explanation must bound THIS filter, not deny that separate evidence.
    assert "price stretch is not established" not in explanation["en"]
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
    if path.endswith(".j2"):
        assert f"recoNoEntry({subject})?L('Initial entry context: ','初始入场条件：')+RECO_NOENTRY_WHY({subject})" in source
        assert "WAIT FOR ENTRY" not in source
        assert "${L('theme rating','主题评级')}" in source
    else:
        assert f"recoNoEntry({subject})?RECO_NOENTRY_WHY({subject})" in source
    assert "no member has a clean entry" not in source


def test_detail_hero_preserves_native_theme_rating_when_initial_entry_is_not_confirmed():
    import re
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        pytest.skip("Node required to execute the actual detail recommendation chip")
    source = (ROOT / "templates/basket_detail.html.j2").read_text()
    chip = re.search(r"const recoChip = t => .*?;\n", source, re.S)
    assert chip
    rows = [
        {"reco": "accumulate", "reco_en": "ACCUMULATE", "reco_zh": "增持",
         "textures": {"clean_entry": {"flag": False}}},
        {"reco": "accumulate", "reco_en": "ACCUMULATE", "reco_zh": "增持",
         "textures": {"clean_entry": {"flag": True}}},
        {"reco": "hold", "reco_en": "HOLD", "reco_zh": "持有",
         "textures": {"clean_entry": {"flag": False}}},
        {"reco": "enter", "reco_en": "ENTER", "reco_zh": "入场", "textures": {}},
    ]
    script = r"""
const L=(en,zh)=>`<span class="l-en">${en}</span><span class="l-zh">${zh}</span>`;
const RECO_COLOR={accumulate:['','',''],enter:['','',''],hold:['','','']};
const RECO_NOENTRY=['','',''];
const recoNoEntry=t=>(t.reco==='accumulate'||t.reco==='enter')&&!(((t.textures||{}).clean_entry)||{}).flag;
const badge=(cls,c,en,zh)=>`<span class="${cls}">${L(en,zh)}</span>`;
""" + chip.group(0) + "\nconst rows=" + json.dumps(rows, ensure_ascii=False) + ";\nconsole.log(JSON.stringify(rows.map(recoChip)));"
    outputs = json.loads(subprocess.check_output([node, "-e", script], text=True))
    assert "ACCUMULATE" in outputs[0] and "WAIT FOR ENTRY" not in outputs[0]
    assert "ACCUMULATE" in outputs[1] and "WAIT FOR ENTRY" not in outputs[1]
    assert "HOLD" in outputs[2] and "WAIT FOR ENTRY" not in outputs[2]
    assert "ENTER" in outputs[3] and "WAIT FOR ENTRY" not in outputs[3]
    assert "${L('theme rating','主题评级')}" in source
    assert "L('Initial entry context: ','初始入场条件：')" in source
    assert "Check individual stocks" in source and "查看具体个股" in source


def test_continuation_action_card_contract_reaches_compiled_detail():
    import hashlib

    evidence = (ROOT / "research/sector_pulse/recommendation_reasons_20260921"
                / "continuation_20260924")
    contract = json.loads((evidence / "cross-component-receipt.json").read_text())
    assert contract["schema"] == "theme_continuation_detail_contract.v1"
    assert contract["theme_id"] == "cn_pharma_cxo"

    action = contract["action_card"]
    detail = contract["detail"]
    identity = contract["identity"]
    assert action["source_head"] == "6e0beeec8f720333dd72ab47a9e7c39fed6238a1"
    assert action["source_path"] == "engine/china_act_now.py"
    assert action["source_sha256"] == "fcb9c8996294e1f9cf0fe5e6835c27785ef4006cf43b9aba58cebff0b05cc8f7"
    assert action["input_head"] == "88a3f1cfd18f391d2802e9086dc00f6fe5545607"
    assert action["input_path"] == "site/chinabasketdata/baskets.json"
    assert action["input_sha256"] == "69c46ef1ec0c60f450dfe6c443d2d01c70da81a91f34c8763c04f747edbb4040"
    assert action["display_lane"] == "buy_now"
    assert action["entry_route"] == "continuation"
    assert action["observed_lanes"] == ["wait_pullback"]
    assert action["source_read_lanes"] == ["wait_pullback"]
    assert action["theme_decision"] == {
        "source_as_of": "2026-09-22",
        "final_reco": "accumulate",
        "final_label": "dominant",
        "status": "CURRENT",
        "source_status": "CURRENT",
        "source_conflict": False,
        "scope": "theme_presentation_only",
        "stock_entry_permission": False,
    }

    assert detail["input_page_head"] == action["input_head"]
    assert detail["input_page_path"] == "site/basket_china/cn_pharma_cxo.html"
    assert detail["input_page_sha256"] == "69a2d8f9bfb49552e01da251bf7e30d8cc778f0dcdcfa8e0c67570dc492282a6"
    template = ROOT / detail["template_path"]
    assert hashlib.sha256(template.read_bytes()).hexdigest() == detail["template_sha256"]
    assert detail["source_as_of"] == action["theme_decision"]["source_as_of"]
    assert detail["recommendation"] == action["theme_decision"]["final_reco"]
    assert detail["label"] == action["theme_decision"]["final_label"]
    assert detail["clean_entry"] is False
    assert detail["native_rating_preserved"] is True
    assert detail["initial_entry_context_separate"] is True
    assert detail["blanket_wait_literal_absent"] is True
    assert identity == {
        "same_theme_id": True,
        "same_source_session": True,
        "same_final_recommendation": True,
        "continuation_without_bottoming_event": True,
        "stock_entry_permission_widened": False,
    }

    browser = contract["browser"]
    assert browser["captures"] == 8
    expected = {(theme, lang, width)
                for theme in ("dark", "light")
                for lang in ("en", "zh")
                for width in (1440, 390)}
    actual = {(row["theme"], row["language"], row["width"])
              for row in browser["records"]}
    assert actual == expected
    assert all(row["http_status"] == 200 for row in browser["records"])
    assert all(row["rating_visible"] and row["initial_context_visible"]
               and row["blanket_wait_absent"] for row in browser["records"])
    assert all(not row["page_errors"] and not row["request_failures"]
               and not row["page_overflow"] for row in browser["records"])
    for row in browser["records"]:
        screenshot = evidence / row["screenshot"]
        assert screenshot.is_file()
        assert hashlib.sha256(screenshot.read_bytes()).hexdigest() == row["screenshot_sha256"]

    controls = json.loads((evidence / "browser-receipt.json").read_text())
    assert controls["captures"] == 32
    assert {row["scenario"] for row in controls["records"]} == {
        "continuation_zero_qualified", "fresh_initial",
        "final_demoted", "stale_missing_entry",
    }
    assert {row["language"] for row in controls["records"]} == {"en", "zh"}
    assert all(row["rating_visible"] and row["wait_instruction_absent"]
               and row["stock_checks_opened"] for row in controls["records"])
    assert all(not row["page_errors"] and not row.get("request_failures")
               and not row["page_overflow"] for row in controls["records"])
    for row in controls["records"]:
        screenshot = evidence / "browser" / row["screenshot"]
        assert screenshot.is_file()
        assert hashlib.sha256(screenshot.read_bytes()).hexdigest() == row["sha256"]


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
    if path.endswith(".j2"):
        assert "${L('WAIT FOR ENTRY','等待入场')}" not in source
        assert "${L('theme rating','主题评级')}" in source
    else:
        assert "${L('WAIT FOR ENTRY','等待入场')}" in source


# Real-source attribution reuses the native owner; this suite is already in CI.
def _entry_audit_fixture(rs=.845, accel=.5, pct50=.8):
    import numpy as np
    import pandas as pd
    from engine import basket_score
    dates = pd.bdate_range(end="2026-09-18", periods=300)
    level = pd.Series(np.linspace(100, 150, 300), index=dates)
    level.iloc[-1] = 145
    fp = {"accel_z": accel, "rs_pctile": rs}
    breadth = {"pct50": pct50, "nh": 1, "nl": 0}
    stored = basket_score.clean_entry(level, fp, breadth, basket_score._rsi(level))
    row = {"id": "test_theme", "name": "Test theme", "n_members": 5,
           "reco": "accumulate", **fp, "breadth": breadth,
           "textures": {"clean_entry": stored}}
    payload = {"as_of": "2026-09-18", "theme_intel": {"as_of": "2026-09-18", "themes": [row]},
               "chart": {"dates": dates.strftime("%Y-%m-%d").tolist(),
                         "baskets": {"test_theme": level.tolist()}}}
    extension = {"as_of": "2026-09-18", "region": "us", "themes": [
        {"id": "test_theme", "atr_ext": .9, "band_en": "normal", "n_live": 5}]}
    return payload, extension


def _entry_audit(payload, extension=None):
    from research.sector_pulse.recommendation_reasons_20260921.audit_entry import audit
    return audit(payload, extension)


def test_native_entry_audit_identifies_a_veto_without_changing_the_input():
    payload, extension = _entry_audit_fixture()
    before = deepcopy((payload, extension))
    result = _entry_audit(payload, extension)
    row = result["records"][0]
    assert row["attribution"] == "relative_strength_veto_only"
    assert not row["native_entry"]["flag"] and row["research_counterfactual"]["flag"]
    assert row["native_entry"]["quality"] >= .6
    assert row["extension_context"]["band"] == "normal"
    assert result["constructive_attribution_counts"] == {"relative_strength_veto_only": 1}
    assert not result["policy_change_applied"]
    assert (payload, extension) == before


def test_native_entry_audit_does_not_call_a_quality_penalty_a_sole_veto():
    payload, extension = _entry_audit_fixture(accel=.2)
    row = _entry_audit(payload, extension)["records"][0]
    assert row["attribution"] == "relative_strength_veto_and_quality_penalty"
    assert row["native_entry"]["quality"] < .6


def test_native_entry_audit_preserves_breaking_breadth():
    payload, extension = _entry_audit_fixture(pct50=.2)
    row = _entry_audit(payload, extension)["records"][0]
    assert row["attribution"] == "other_entry_conditions"
    assert not row["research_counterfactual"]["flag"]


def test_native_entry_audit_separates_entry_permission_from_extension_context():
    payload, extension = _entry_audit_fixture(rs=.5)
    extension["themes"][0].update(atr_ext=3.4, band_en="stretched")
    row = _entry_audit(payload, extension)["records"][0]
    assert row["attribution"] == "entry_already_clear"
    assert row["extension_context"]["band"] == "stretched"
    assert not row["extension_context"]["trade_authority"]
    assert not row["extension_context"]["same_generation_and_membership_proven"]


@pytest.mark.parametrize("change", ["wrong_date", "wrong_region", "duplicate", "missing_id",
                                     "bad_number", "bad_count", "wrong_count", "wrong_band"])
def test_native_entry_audit_rejects_bad_extension_joins_only(change):
    payload, extension = _entry_audit_fixture()
    if change == "wrong_date": extension["as_of"] = "2026-09-17"
    elif change == "wrong_region": extension["region"] = "china"
    elif change == "duplicate": extension["themes"] *= 2
    elif change == "missing_id": extension["themes"] = []
    elif change == "bad_number": extension["themes"][0]["atr_ext"] = float("nan")
    elif change == "bad_count": extension["themes"][0]["n_live"] = True
    elif change == "wrong_count": extension["themes"][0]["n_live"] = 6
    else: extension["themes"][0]["band_en"] = "parabolic"
    row = _entry_audit(payload, extension)["records"][0]
    assert row["status"] == "reproduced"
    assert row["attribution"] == "relative_strength_veto_only"
    assert row["extension_context"]["status"] == "unavailable"


@pytest.mark.parametrize("change", ["missing_rs", "nan_accel", "bool_rs", "missing_breadth",
                                     "bad_nh", "missing_quality", "nonboolean_flag", "bad_textures"])
def test_native_entry_audit_cannot_turn_missing_inputs_into_favorable_evidence(change):
    payload, extension = _entry_audit_fixture()
    row = payload["theme_intel"]["themes"][0]
    if change == "missing_rs": row.pop("rs_pctile")
    elif change == "nan_accel": row["accel_z"] = float("nan")
    elif change == "bool_rs": row["rs_pctile"] = True
    elif change == "missing_breadth": row["breadth"] = None
    elif change == "bad_nh": row["breadth"]["nh"] = -1
    elif change == "missing_quality": row["textures"]["clean_entry"].pop("quality")
    elif change == "nonboolean_flag": row["textures"]["clean_entry"]["flag"] = 0
    else: row["textures"] = []
    result = _entry_audit(payload, extension)
    assert result["unavailable_rows"] == 1 and result["reproduced_rows"] == 0
    assert result["records"][0]["attribution"] is None


@pytest.mark.parametrize("change", ["missing_last", "length", "negative", "infinite"])
def test_native_entry_audit_refuses_bad_price_tape(change):
    payload, extension = _entry_audit_fixture()
    values = payload["chart"]["baskets"]["test_theme"]
    if change == "missing_last": values[-1] = None
    elif change == "length": values.pop()
    elif change == "negative": values[20] = -5
    else: values[-1] = float("inf")
    result = _entry_audit(payload, extension)
    assert result["unavailable_rows"] == 1
    assert result["records"][0]["reason"] == "missing_invalid_or_unaligned_price_series"


@pytest.mark.parametrize("change", ["future_date", "duplicate_date", "unsorted_dates", "duplicate_id", "date_mismatch"])
def test_native_entry_audit_refuses_incoherent_frames(change):
    payload, extension = _entry_audit_fixture()
    if change == "future_date": payload["chart"]["dates"][-1] = "2026-09-21"
    elif change == "duplicate_date": payload["chart"]["dates"][-2] = payload["chart"]["dates"][-1]
    elif change == "unsorted_dates": payload["chart"]["dates"].reverse()
    elif change == "duplicate_id": payload["theme_intel"]["themes"] *= 2
    else: payload["as_of"] = "2026-09-17"
    with pytest.raises(ValueError):
        _entry_audit(payload, extension)


def test_native_entry_audit_discloses_unreproduced_export_instead_of_overwriting_it():
    payload, extension = _entry_audit_fixture()
    payload["theme_intel"]["themes"][0]["textures"]["clean_entry"]["flag"] = True
    result = _entry_audit(payload, extension)
    row = result["records"][0]
    assert row["status"] == "unavailable" and row["attribution"] is None
    assert row["reason"] == "rounded_export_does_not_reproduce_native_entry"
    assert row["stored"]["flag"] and not row["replayed"]["flag"]


def test_native_entry_audit_does_not_recommend_out_of_favour_rows():
    payload, extension = _entry_audit_fixture()
    payload["theme_intel"]["themes"][0]["reco"] = "avoid"
    result = _entry_audit(payload, extension)
    assert result["reproduced_rows"] == 1
    assert result["constructive_reproduced_rows"] == 0
    assert result["constructive_attribution_counts"] == {}
    assert result["records"][0]["reco"] == "avoid"


def test_native_entry_audit_literals_remain_bound_to_the_existing_owner():
    from engine import basket_score
    source = (ROOT / "engine/basket_score.py").read_text()
    function = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "clean_entry")
    native = ast.get_source_segment(source, function)
    assert "rs_p < 0.75" in native and "q >= 0.6" in native
    assert basket_score.clean_entry.__module__ == "engine.basket_score"


@pytest.mark.parametrize('path', ['templates/baskets_desk.js', 'templates/basket_detail.html.j2'])
def test_rollover_chinese_translates_all_native_conditions_not_just_relative_strength(path):
    import re, subprocess
    source = (ROOT / path).read_text()
    helper = re.search(r'function rolloverReasonText\(reasons, zh=false\)\{.*?\n\}', source, re.S)
    native = ['extended (RS 87%ile)', 'momentum rolling over', 'decelerating',
              'breadth weakening', 'more new lows', 'below 50d', 'rolling off the high',
              'momentum fading (hist 1.25→0.5, 3 straight declines)']
    code = helper.group(0) + '\nconsole.log(JSON.stringify(rolloverReasonText(' + json.dumps(native) + ',true)));'
    text = json.loads(subprocess.check_output(['node', '-e', code], text=True))
    assert '相对强势偏高' in text and '连续3次下降' in text
    for phrase in ['momentum', 'decelerating', 'breadth', 'below', 'rolling', 'straight']:
        assert phrase not in text
    assert '1.25' in text and '0.5' in text
    assert '涨幅偏高' not in text


# A data-only registration is not proof that a pull request exercised these cases.
# The existing stock/conviction code owner must run each whole suite, while the
# pre-existing data job remains intact for its original callers.
_PR_REGRESSION_SUITES = (
    "tests/test_theme_recommendation_reasons.py",
    "tests/test_basket_entry_explanations.py",
    "tests/test_theme_entry_gate_comparison.py",
    "tests/test_sector_pulse_observation_clock.py",
)


def _assert_pr_regression_owner(jobs):
    import fnmatch
    import shlex
    owner = jobs["conviction-profile"]
    assert owner["gate"] == "code", "recommendation regressions must run in PR code CI"
    commands = [str(step.get("run", "")) for step in owner["steps"]]
    test_commands = [shlex.split(command) for command in commands
                     if command.startswith("python -m pytest ")]
    for suite in _PR_REGRESSION_SUITES:
        executions = [tokens for tokens in test_commands if suite in tokens]
        assert len(executions) == 1, f"whole suite missing/duplicated in code owner: {suite}"
        assert executions[0][:3] == ["python", "-m", "pytest"]
        # Python's -m selects the pytest module. Only arguments AFTER that
        # launcher may select/deselect pytest cases or markers.
        pytest_args = executions[0][3:]
        assert not {"-k", "-m", "--deselect", "--ignore"}.intersection(pytest_args)
        assert not any(token.startswith(("--deselect=", "--ignore=")) for token in pytest_args)
        assert any(fnmatch.fnmatchcase(suite, pattern) for pattern in owner["paths"])
    dependencies = set(next(command for command in commands if command.startswith("pip install ")).split())
    assert {"pytest", "pandas", "numpy", "pyarrow", "pyyaml", "jinja2"} <= dependencies


def test_recommendation_regressions_are_whole_suite_pr_code_checks():
    import yaml
    jobs = yaml.safe_load((ROOT / ".github/ci/legacy-jobs.yml").read_text())["jobs"]
    _assert_pr_regression_owner(jobs)
    # Code coverage is additive: the historical data-gate execution is not removed.
    old_commands = "\n".join(str(step.get("run", "")) for step in jobs["engine-render-guards"]["steps"])
    assert jobs["engine-render-guards"]["gate"] == "data"
    for suite in _PR_REGRESSION_SUITES:
        assert suite in old_commands


@pytest.mark.parametrize("mutation", ["data_only", "deselected", "marker_filter", "missing_suite", "missing_scope", "missing_dependency"])
def test_pr_code_contract_rejects_false_green_registration(mutation):
    import yaml
    jobs = deepcopy(yaml.safe_load((ROOT / ".github/ci/legacy-jobs.yml").read_text())["jobs"])
    owner = jobs["conviction-profile"]
    if mutation == "data_only":
        owner["gate"] = "data"
    elif mutation == "missing_scope":
        owner["paths"] = []
    else:
        for step in owner["steps"]:
            command = str(step.get("run", ""))
            if mutation == "missing_dependency" and command.startswith("pip install "):
                step["run"] = command.replace(" pyarrow", "")
            elif "tests/test_theme_recommendation_reasons.py" in command:
                if mutation == "deselected":
                    step["run"] = command + " -k unrelated"
                elif mutation == "marker_filter":
                    step["run"] = command + " -m unrelated"
                elif mutation == "missing_suite":
                    step["run"] = command.replace("tests/test_basket_entry_explanations.py", "")
    with pytest.raises(AssertionError):
        _assert_pr_regression_owner(jobs)
