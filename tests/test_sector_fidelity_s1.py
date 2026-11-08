"""Sector Paper fidelity S1 (#7646 Cycles wave, lane L7) — pins D2, D8 and D9.

D2  the act-now lane header carries no accent stripe on any edge, and the two
    copies of that header block (the US board partial and the dashboard) stay
    identical (docs/DESIGN_DOCTRINE.md, Chairman no-stripe rule);
D8  the group dossier's "Current read" is the regime label, never the retired
    advisory action text; an observation more than five days older than the
    build reads as older evidence, never as live; the Reliability cell names
    its member coverage;
D9  the research-vault readback paints an absent field as the typed
    unavailable state, names the question-only state, and repaints all six
    fields on a language switch.

Pure text checks plus small node evaluations of expressions lifted verbatim
from the templates. Node is required in CI; a developer machine without it
skips only the evaluation tests.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "templates"
ACT_BOARD = TPL / "_us_act_now_board.html.j2"
DASHBOARD = TPL / "dashboard.html.j2"
SUBSECTOR = TPL / "subsector_detail.html.j2"
VAULT = TPL / "research_vault.html.j2"

STALE_TITLE = ("Older evidence shown", "显示较早证据")
STALE_BODY = ("Observation is no longer current.", "观测已过期。")
RETIRED_ADVISORY = ("entry setup active", "入场配置有效", "setup forming", "配置形成中")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _node():
    node = shutil.which("node")
    if node:
        return node
    if os.environ.get("CI"):
        pytest.fail("node must be on PATH in CI for the L7 fidelity evaluations")
    pytest.skip("node not installed on this developer machine")


def _eval(js: str):
    out = subprocess.run([_node(), "-e", js], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


# ── D2: lane header, no stripe, twins identical ─────────────────────────────

def _acth_block(text: str) -> str:
    m = re.search(r"  /\* Lane header[^\n]*\n  \.acth \{[^\n]*\n  \.acth::before \{[^\n]*\n  /\*[^\n]*\*/\n", text)
    assert m, "the lane-header block is missing"
    return m.group(0)


@pytest.mark.parametrize("path", [ACT_BOARD, DASHBOARD], ids=lambda p: p.name)
def test_d2_lane_header_has_no_accent_stripe(path):
    text = _read(path)
    for m in re.finditer(r"\.acth::before\s*\{([^}]*)\}", text):
        body = m.group(1)
        assert re.search(r"content:\s*none", body), f"{path.name}: .acth::before must be content: none"
        assert "--act-accent" not in body and "background" not in body and "height" not in body
    assert "no accent stripe on any edge" in _acth_block(text)


def test_d2_header_twins_are_identical():
    assert _acth_block(_read(ACT_BOARD)) == _acth_block(_read(DASHBOARD))


# ── D8: group dossier ───────────────────────────────────────────────────────

def _stale_iife() -> str:
    m = re.search(r"const stale = (\(function \(\) \{.*?\}\)\(\));", _read(SUBSECTOR))
    assert m, "the stale-observation guard is missing from subsector_detail"
    return m.group(1)


@pytest.mark.parametrize(
    "as_of, generated, expected",
    [
        ("2026-09-18", "2026-10-30 12:00 UTC", True),
        ("2026-10-29", "2026-10-30 12:00 UTC", False),
        ("2026-10-25", "2026-10-30 12:00 UTC", False),
        ("2026-10-24", "2026-10-30 12:00 UTC", True),
        ("", "2026-10-30 12:00 UTC", False),
        ("2026-09-18", "", False),
        (None, None, False),
    ],
)
def test_d8_stale_guard_evaluates(as_of, generated, expected):
    js = (
        f"var g = {{as_of: {json.dumps(as_of)}}}, DETAIL = {{generated_utc: {json.dumps(generated)}}};"
        f"process.stdout.write(JSON.stringify({_stale_iife()}));"
    )
    assert _eval(js) is expected


def test_d8_stale_reads_as_older_evidence_in_pill_and_freshness():
    text = _read(SUBSECTOR)
    pill = next(line for line in text.splitlines() if "id-meta" in line and "L('as of','截至')" in line)
    assert "(stale ? 'late' : 'neutral')" in pill
    assert f"esc(zhNow ? '{STALE_BODY[1]}' : '{STALE_BODY[0]}')" in pill
    assert f"L('{STALE_TITLE[0]}','{STALE_TITLE[1]}')" in pill
    fresh = next(line for line in text.splitlines() if "L('Freshness','新鲜度')" in line and "id-decision-grid" in line)
    assert f"(stale ? L('{STALE_TITLE[0]}','{STALE_TITLE[1]}') : L('Up to date','已是最新'))" in fresh


def test_d8_current_read_is_the_regime_label_not_the_retired_action():
    text = _read(SUBSECTOR)
    assert "const actionEn = regEn !== '—' ? regEn : '';" in text
    assert "const actionZh = regZh !== '—' ? regZh : '';" in text
    assert "r.action" not in text
    for phrase in RETIRED_ADVISORY:
        assert phrase not in text, phrase
    assert "L('Current read','当前研判') + '</div><div class=\"id-decision-read\">' + actionRead" in text


def test_d8_reliability_cell_names_member_coverage():
    text = _read(SUBSECTOR)
    assert "confidenceLabel + ' · ' + coverage + ' ' + L('members','成分')" in text


# Copy-deck and state-matrix rows cite these exact lines; L7 kept them line-neutral.
CITED_LINES = {
    (ACT_BOARD, 31): "more here — <a href=\"plans.html\">sign in",
    (ACT_BOARD, 64): "_ab_gate",
    (DASHBOARD, 14690): "_atier == 'act'",
    (SUBSECTOR, 59): "min-height:420px",
    (SUBSECTOR, 124): "const sgn",
    (SUBSECTOR, 156): "const coverage",
    (SUBSECTOR, 163): "L('as of','截至')",
    (SUBSECTOR, 196): "Member detail is unavailable for this group.",
    (SUBSECTOR, 214): "chart mount failed",
}


@pytest.mark.parametrize("key", list(CITED_LINES), ids=lambda k: f"{k[0].name}:{k[1]}")
def test_cited_lines_still_point_at_their_content(key):
    path, line = key
    assert CITED_LINES[key] in _read(path).splitlines()[line - 1]


# ── D9: research-vault readback ─────────────────────────────────────────────

def _vault() -> str:
    return _read(VAULT)


def test_d9_absent_field_paints_the_typed_unavailable_state():
    text = _vault()
    assert (
        "el.textContent = value || (document.documentElement.getAttribute('data-lang') === 'zh' "
        "? '— 不可用' : '— unavailable');"
    ) in text
    assert "innerHTML" not in text[text.index("function paint(id, value)"):text.index("paintReadback();")]


def test_d9_question_only_state_markup():
    text = _vault()
    m = re.search(r'<p class="si-note" id="si-rb-state" role="status" hidden>([^<]*)</p>', text)
    assert m, "the question-only state line is missing"
    for pair in ("t('Partial coverage', '覆盖不完整')", "t('Subject', '主体')", "t('Carried question', '携带问题')"):
        assert pair in m.group(1)


@pytest.mark.parametrize(
    "fields, shown",
    [
        ({"subject": "XLK", "q": "why now"}, True),
        ({"subject": "XLK", "q": "why now", "snap": "s1"}, False),
        ({"subject": "XLK", "q": "why now", "obs": "2026-10-30"}, False),
        ({"subject": "XLK", "q": "why now", "ev": "descriptive"}, False),
        ({"subject": "XLK"}, False),
    ],
)
def test_d9_question_only_state_appears_only_for_subject_and_question(fields, shown):
    m = re.search(r"rbState\.hidden = (.*?);\n", _vault())
    assert m
    js = f"var fields = {json.dumps(fields)}; process.stdout.write(JSON.stringify({m.group(1)}));"
    assert _eval(js) is (not shown)


def test_d9_langchange_repaints_all_six_fields():
    text = _vault()
    region = re.search(r"document\.addEventListener\('langchange', function \(\) \{(.*?)\n  \}\);", text, re.S)
    assert region and "paintReadback();" in region.group(1)
    body = text[text.index("function paintReadback()"):text.index("paintReadback();")]
    for sink in ("si-rb-subject", "si-rb-q", "si-rb-snap", "si-rb-obs", "si-rb-ev", "si-rb-origin"):
        assert f"paint('{sink}'" in body, sink
