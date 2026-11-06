"""Re-deploy gate chip + Fed-put inputs leg line (wave W23, lane W23-L11).

SPEC 2: the chip that printed "Dislocation" really computes the re-deploy gate,
so it is labelled as one; SPEC 3: the two master-switch legs (Sahm recession,
breakeven-inflated Fed-put off) are named under the chips. Synthetic fixtures
only — no site/ or data/ reads, no network, build() is never called.
"""
from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_vector import C  # noqa: E402
from tests.test_spvector_page import _env, _spvector_vm  # noqa: E402


def _render(disloc: dict) -> str:
    """Render the page from the shared spvector vm and return the chips section."""
    vm = dict(_spvector_vm(), disloc=disloc)
    html = _env().get_template("spvector.html.j2").render(**vm, C=C)
    start = html.index('<div class="chips">')
    end = html.index("<!-- ===== risk-score leg breakdown")
    return html[start:end]


def _gate_label(put_absent: bool, cap_now: int) -> tuple[str, str]:
    from scripts.build_spvector import _redeploy_gate_label
    return _redeploy_gate_label(put_absent, cap_now)


def _legs_vm(recession: bool, fedput_off: bool) -> dict:
    verdict, verdict_zh = _gate_label(False, 1)
    return {"verdict": verdict, "verdict_zh": verdict_zh, "put_absent": False,
            "capitulation": 1, "put_legs": {"recession": recession,
                                            "fedput_off": fedput_off}}


def test_gate_label_truth_table():
    armed = ("armed — would re-deploy", "就绪 —— 将再部署")
    blocked = ("blocked — Fed-put absent", "受阻 —— 美联储看跌缺席")
    idle = ("not triggered", "未触发")
    assert _gate_label(False, 2) == armed
    assert _gate_label(False, 3) == armed
    assert _gate_label(False, 1) == idle
    assert _gate_label(False, 0) == idle
    assert _gate_label(True, 3) == blocked
    assert _gate_label(True, 0) == blocked


def test_chip_names_the_redeploy_gate():
    # committed 2026-10-16 record: capitulation 1, put present.
    verdict, verdict_zh = _gate_label(False, 1)
    sec = _render({"verdict": verdict, "verdict_zh": verdict_zh,
                   "put_absent": False, "capitulation": 1})
    assert "Re-deploy gate" in sec
    assert "再部署闸门" in sec
    assert "not triggered" in sec
    assert "未触发" in sec
    assert "1/3" in sec
    assert "Dislocation" not in sec
    assert "错位" not in sec


def test_legs_both_quiet():
    sec = _render(_legs_vm(False, False))
    assert "Fed-put inputs" in sec
    assert "美联储看跌条件" in sec
    assert "Sahm recession signal quiet" in sec
    assert "low enough for the Fed to ease" in sec
    assert "萨姆衰退信号未触发" in sec
    assert "通胀预期低到足以让美联储宽松" in sec
    assert "firing" not in sec
    assert "too high" not in sec


def test_recession_firing_with_low_inflation():
    sec = _render(_legs_vm(True, False))
    assert "Sahm recession signal firing" in sec
    assert "萨姆衰退信号已触发" in sec
    assert "low enough for the Fed to ease" in sec
    assert "quiet" not in sec
    assert "too high" not in sec


def test_inflation_too_high_with_quiet_recession():
    sec = _render(_legs_vm(False, True))
    assert "Sahm recession signal quiet" in sec
    assert "inflation expectations too high for the Fed to ease" in sec
    assert "通胀预期过高，美联储难以宽松" in sec
    assert "firing" not in sec
    assert "low enough" not in sec


def test_no_legs_renders_no_leg_line():
    verdict, verdict_zh = _gate_label(False, 1)
    base = {"verdict": verdict, "verdict_zh": verdict_zh,
            "put_absent": False, "capitulation": 1}
    for with_key in (True, False):  # put_legs None, and the key absent
        disloc = dict(base)
        if with_key:
            disloc["put_legs"] = None
        sec = _render(disloc)
        assert "Fed-put inputs" not in sec
        assert "Sahm" not in sec
        assert "None" not in sec


def test_put_leg_flags_reads_the_last_row():
    from scripts.build_spvector import _put_leg_flags
    f = pd.DataFrame({"recession": [True, True, False],
                      "fedput_off": [False, False, True]})
    assert _put_leg_flags(f) == {"recession": False, "fedput_off": True}
    # last row carries a NaN -> the last COMPLETE row is read instead.
    g = pd.DataFrame({"recession": [True, False, False],
                      "fedput_off": [False, True, float("nan")]})
    assert _put_leg_flags(g) == {"recession": False, "fedput_off": True}
    # pure: the input frame is not mutated
    assert list(f["recession"]) == [True, True, False]
    assert list(f["fedput_off"]) == [False, False, True]


def test_put_leg_flags_missing_or_empty_is_none():
    from scripts.build_spvector import _put_leg_flags
    assert _put_leg_flags(pd.DataFrame({"recession": [True]})) is None
    assert _put_leg_flags(pd.DataFrame({"fedput_off": [False]})) is None
    assert _put_leg_flags(pd.DataFrame({"recession": [], "fedput_off": []})) is None
    n = pd.DataFrame({"recession": [float("nan")], "fedput_off": [float("nan")]})
    assert _put_leg_flags(n) is None


def test_zh_twins_differ():
    sec = _render(_legs_vm(True, True))
    pairs = re.findall(r'<span class="l-en">(.*?)</span>'
                       r'<span class="l-zh">(.*?)</span>', sec)
    en_spans = re.findall(r'<span class="l-en">(.*?)</span>', sec)
    assert pairs and len(pairs) == len(en_spans)
    for en, zh in pairs:
        assert en != zh, f"l-zh twin copies the EN text: {en!r}"
    for want in ("Re-deploy gate", "再部署闸门", "Sahm recession signal firing",
                 "inflation expectations too high for the Fed to ease"):
        assert want in sec


def test_build_uses_the_helpers():
    from scripts.build_spvector import build
    src = inspect.getsource(build)
    assert "_redeploy_gate_label(put_absent, cap_now)" in src
    assert "_put_leg_flags(msf)" in src
    assert '"put_legs": put_legs' in src
    assert src.count("master_switch_frame(") == 1
    for lit in ('"calm"', '"stand aside"', '"buyable washout"'):
        assert lit not in src, f"build() still hard-codes {lit}"
