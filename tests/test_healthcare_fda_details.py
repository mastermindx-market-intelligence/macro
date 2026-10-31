"""Producer FDA record lines published as text below the foresight chips.

Synthetic inputs only. The helper reads nothing: no store, no network, no
new import. It keeps the producer's strings verbatim — never rewriting,
translating or reordering them — and the template tests read repo source
text only. The lines sit below .fx-chips as a sibling of the chip, never
inside a chip and never in a title= attribute.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

QUALIFIED = {"capture_qualified": True, "capture_incomplete": False}
FOUR = [
    "semaglutide [Currently in Shortage/Limited Availability]",
    "tirzepatide [Currently in Shortage/Limited Availability]",
    "liraglutide [Resolved/Limited Availability]",
    "metformin [Currently in Shortage/Not Available]",
]
_MISSING = object()


def _row(details=_MISSING, freshness=QUALIFIED):
    row = {"summary": {"freshness": dict(freshness)} if freshness is not None else {}}
    if details is not _MISSING:
        row["details"] = details
    return row


def test_detail_lines_from_a_qualified_capture():
    from engine.foresight_cascade import _fda_detail_lines

    lines = _fda_detail_lines(_row(list(FOUR)))
    assert lines == FOUR[:3]
    assert lines[0] == FOUR[0] and lines[2] == FOUR[2]


def test_detail_lines_withheld_unless_capture_qualified():
    from engine.foresight_cascade import _fda_detail_lines

    unqualified = {"capture_qualified": False, "capture_incomplete": False}
    unfinished = {"capture_qualified": False, "capture_incomplete": True}
    qualified_unfinished = {"capture_qualified": True, "capture_incomplete": True}
    assert _fda_detail_lines(_row(list(FOUR), freshness=unqualified)) is None
    assert _fda_detail_lines(_row(list(FOUR), freshness=unfinished)) is None
    assert _fda_detail_lines(_row(list(FOUR), freshness=qualified_unfinished)) is None
    assert _fda_detail_lines(_row(list(FOUR), freshness=None)) is None


def test_detail_lines_drop_blank_and_non_string():
    from engine.foresight_cascade import _fda_detail_lines

    kept = _fda_detail_lines(_row(
        ["", "   ", None, 5, "semaglutide [Currently in Shortage/Limited Availability]"]
    ))
    assert kept == ["semaglutide [Currently in Shortage/Limited Availability]"]
    assert _fda_detail_lines(_row([])) is None
    assert _fda_detail_lines(_row()) is None
    assert _fda_detail_lines(_row("semaglutide")) is None
    assert _fda_detail_lines("not-a-dict") is None
    assert _fda_detail_lines(None) is None


def test_template_block_sits_below_the_chips_and_out_of_titles():
    text = (ROOT / "templates" / "foresight.html.j2").read_text(encoding="utf-8")
    lines = text.splitlines()
    split_if = next(
        i for i, ln in enumerate(lines) if "{% if r.observation_split %}" in ln
    )
    split_end = next(i for i in range(split_if, len(lines)) if "{% endif %}" in lines[i])
    chips_open = next(i for i, ln in enumerate(lines) if '<div class="fx-chips">' in ln)
    # The container close is the first bare </div> after the open, so a line
    # moved inside the chip container sits before it and goes red here.
    chips_close = next(
        i for i in range(chips_open + 1, len(lines)) if lines[i].strip() == "</div>"
    )
    fda = next(i for i, ln in enumerate(lines) if "{% if r.fda_details %}" in ln)
    cap = next(i for i, ln in enumerate(lines) if "fx-cap" in ln and "r.score_detail" in ln)
    assert chips_open < split_end < chips_close, "split chips must close inside .fx-chips"
    assert chips_close < fda < cap, "the FDA line block must sit below .fx-chips"
    for ln in lines:
        if "title=" in ln:
            assert "fda_details" not in ln, "fda_details must never appear in a title"
            assert "fx-fda-line" not in ln, "record lines must never appear in a title"


def test_template_block_renders_and_escapes():
    import jinja2

    text = (ROOT / "templates" / "foresight.html.j2").read_text(encoding="utf-8")
    block = next(ln.strip() for ln in text.splitlines() if "{% if r.fda_details %}" in ln)
    source = (
        "{% macro t(en, zh='') -%}"
        '<span class="l-en">{{ en|safe }}</span>'
        "<span class=\"l-zh\">{{ (zh if zh else en)|safe }}</span>"
        "{%- endmacro %}" + block
    )
    env = jinja2.Environment(autoescape=False)

    out = env.from_string(source).render(
        r={"fda_details": [FOUR[0], FOUR[1]]}
    )
    assert 'data-fda-details="2"' in out
    assert FOUR[0] in out and FOUR[1] in out
    assert out.count(" \u00b7 ") == 1
    assert "fx-fda-line" in out

    escaped = env.from_string(source).render(r={"fda_details": ["<b>x</b> & y"]})
    assert "&lt;b&gt;x&lt;/b&gt; &amp; y" in escaped
    assert "<b>x</b>" not in escaped

    assert env.from_string(source).render(r={"fda_details": None}) == ""
    assert env.from_string(source).render(r={}) == ""


def _qualified_scarcity_row(details):
    """A minimal FDA row: a qualified, finished capture carrying raw details."""
    return {
        "band": "SHORTAGE_ACTIVE",
        "source_status": "CURRENT_REPORTED",
        "n_active": 1,
        "n_resolved": 0,
        "n_discontinued": 0,
        "details": list(details),
        "rationale": "one regulator record observed",
        "summary": {"freshness": dict(QUALIFIED)},
    }


def _glp1_inputs():
    """Every cascade input supplied, so no engine, store or network is read."""
    return dict(
        bottleneck={"themes": {"glp1_obesity": {
            "name": "GLP-1 / Obesity", "band": "AWAITING_DATA"}}},
        revisions={"themes": {"glp1_obesity": {
            "name": "GLP-1 / Obesity", "breadth": 0.05, "level_state": "FLAT_LOW"}}},
        demand={"themes": {}},
        glut={"themes": {}},
        guidance={"themes": {}},
        confirmers={"themes": {}},
        policy_reg={"themes": {}},
        write_ledger=False,
    )


def test_cascade_row_carries_fda_details_end_to_end():
    from engine.foresight_cascade import compute_foresight_cascade

    out = compute_foresight_cascade(
        fda_scarcity={"glp1_obesity": _qualified_scarcity_row(FOUR)}, **_glp1_inputs()
    )
    assert out["themes"][0]["fda_details"] == FOUR[:3]

    unqualified = _qualified_scarcity_row(FOUR)
    unqualified["summary"]["freshness"]["capture_qualified"] = False
    out = compute_foresight_cascade(
        fda_scarcity={"glp1_obesity": unqualified}, **_glp1_inputs()
    )
    assert out["themes"][0]["fda_details"] is None


def test_cascade_publishes_fda_details_from_the_helper():
    src = (ROOT / "engine" / "foresight_cascade.py").read_text(encoding="utf-8")
    assert '"fda_details": fda_details' in src
    assert "_fda_detail_lines(scarcity_row)" in src
    fn = next(
        node for node in ast.walk(ast.parse(src))
        if isinstance(node, ast.FunctionDef) and node.name == "_fda_detail_lines"
    )
    for node in ast.walk(fn):
        assert not isinstance(node, (ast.Import, ast.ImportFrom))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "open"
        if isinstance(node, ast.Name):
            assert node.id != "Path"
        if isinstance(node, ast.Attribute):
            assert node.attr != "Path"
