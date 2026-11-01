"""W28G SPEC 4 — 同花顺 basket browser: turn chips painted by the page, session count shown.

Pins the three product decisions:

  * scripts/_ths_turn_annotate.py — ONE pure helper (load_turn_states +
    annotate_turn_states) serving both builder annotation points, copying all
    four producer fields (state / dd_252 / evidence / days_in_state) and
    failing open on every malformed artifact;
  * scripts/build_baskets_china_ths.py — the in-memory pass runs BEFORE the
    baskets_ths.json write, the split and the render (the seed ran it only at
    the end of the run, so the page never carried a chip), the end-of-run disk
    block reuses the helper instead of hand-copying fields, and split_for_page
    drops turn_evidence / turn_dd_252 from the inline rows while keeping
    turn_state / turn_days_in_state for the chip;
  * templates/baskets_china_factorwatch.html.j2 — turnChipHtml(ts, days) paints
    one LANG()-built data-tip for a positive INTEGER recorded-session count
    ("recorded session(s)", "turning or confirmed" for TURNING/CONFIRMED), all
    three call sites pass b.turn_days_in_state, and FALLING / NONE never chip.

Tests import only the stdlib, jinja2 and scripts._ths_turn_annotate (inside the
helper tests, so the rest are not collection errors while the module is
absent). The builder is read as TEXT / AST only — never imported, never run.
Fixtures are inline dicts (no data/, no site/, no network).
"""
from __future__ import annotations

import ast
import copy
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ROOT = Path(__file__).resolve().parent.parent
# ci-trigger-closure: data — the builder is read as text / AST only, never imported
_BUILDER = _ROOT / "scripts/build_baskets_china_ths.py"
_TEMPLATE = _ROOT / "templates/baskets_china_factorwatch.html.j2"

BANNED = ["实时", "申报", "证伪", "validated", "已验证", "live", "forecast",
          "falsifier", "probability", "概率", "bullish", "bearish", "buy",
          "sell", "episode", "independent", "独立", "current", "latest",
          "最新", "当前", "month", "月", "z-score", "percentile rank", "refuted"]

# The exact tooltips test_chip_tooltip_behaviour_in_node pins (also scanned by
# the banned-word test when node is present).
EN_TIPS = [
    '<span class="turn-chip basing" data-tip="3 recorded sessions in this '
    'state">basing</span>',
    '<span class="turn-chip turning" data-tip="1 recorded session turning or '
    'confirmed">turning</span>',
    '<span class="turn-chip confirmed" data-tip="2 recorded sessions turning '
    'or confirmed">confirmed</span>',
    '<span class="turn-chip washed_out" data-tip="1 recorded session in this '
    'state">washed out</span>',
]
ZH_TIPS = [
    '<span class="turn-chip basing" data-tip="该状态已记录 3 个交易日">筑底</span>',
    '<span class="turn-chip turning" data-tip="转折或确认已记录 1 个交易日">转折</span>',
]


def _render(**extra) -> str:
    """Render the real template with the builder's minimal context (lite page)."""
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")),
                      autoescape=True)
    ctx = dict(baskets_json="{}", chart_json="{}", basket_base="",
               bench_en="CSI 300", bench_zh="沪深300",
               generated_utc="2026-10-20 05:30 UTC", lite=True)
    ctx.update(extra)
    return env.get_template("baskets_china_factorwatch.html.j2").render(**ctx)


def _page_with_chips() -> str:
    return _render(baskets_json=json.dumps({"baskets": [
        {"id": "a", "turn_state": "BASING", "turn_days_in_state": 3}]}))


def _source() -> str:
    return _TEMPLATE.read_text()


def _chip_slice(text: str) -> str:
    m = re.search(r"const turnChipHtml = .*?\n\};\n", text, re.S)
    assert m, "no turnChipHtml block found"
    return m.group(0)


# ---------------------------------------------------------------------------
# 1-7: scripts/_ths_turn_annotate.py (helper imported INSIDE each test)
# ---------------------------------------------------------------------------

def _states_fixture():
    return {"a": {"state": "BASING", "dd_252": -0.31, "evidence": ["e1"],
                  "days_in_state": 3},
            "b": {"state": "TURNING", "days_in_state": 1}}


def test_annotate_copies_all_four_fields():
    from scripts._ths_turn_annotate import annotate_turn_states
    states = _states_fixture()
    rows = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    assert annotate_turn_states(rows, states) == 2
    assert rows[0] == {"id": "a", "turn_state": "BASING", "turn_dd_252": -0.31,
                       "turn_evidence": ["e1"], "turn_days_in_state": 3}
    assert rows[1] == {"id": "b", "turn_state": "TURNING", "turn_dd_252": None,
                       "turn_evidence": [], "turn_days_in_state": 1}
    assert rows[2] == {"id": "c"}


def test_annotate_defaults_for_an_empty_state():
    from scripts._ths_turn_annotate import annotate_turn_states
    rows = [{"id": "a"}]
    assert annotate_turn_states(rows, {"a": {}}) == 1
    assert rows[0] == {"id": "a", "turn_state": "NONE", "turn_dd_252": None,
                       "turn_evidence": [], "turn_days_in_state": None}


def test_annotate_skips_bad_rows_ids_and_states():
    from scripts._ths_turn_annotate import annotate_turn_states
    rows = [None, "x", 7, {"id": None}, {"id": ""}, {"id": 5}, {"no_id": 1},
            {"id": "z"}]
    before = copy.deepcopy(rows)
    states = {"": {"state": "BASING"}, 5: {"state": "BASING"}, "z": "BASING"}
    assert annotate_turn_states(rows, states) == 0
    assert rows == before


def test_annotate_bad_containers_return_zero():
    from scripts._ths_turn_annotate import annotate_turn_states
    states = _states_fixture()
    assert annotate_turn_states(None, states) == 0
    assert annotate_turn_states([], states) == 0
    rows = [{"id": "a"}]
    before = copy.deepcopy(rows)
    for bad in (None, [], "x"):
        assert annotate_turn_states(rows, bad) == 0
        assert rows == before


def test_annotate_is_idempotent_and_leaves_states_alone():
    from scripts._ths_turn_annotate import annotate_turn_states
    rows = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    states = _states_fixture()
    states_before = copy.deepcopy(states)
    assert annotate_turn_states(rows, states) == 2
    once = copy.deepcopy(rows)
    assert annotate_turn_states(rows, states) == 2
    assert rows == once
    assert states == states_before


def test_annotate_overwrites_matched_and_keeps_unmatched():
    from scripts._ths_turn_annotate import annotate_turn_states
    rows = [{"id": "a", "turn_state": "FALLING", "turn_days_in_state": 9},
            {"id": "q", "turn_state": "FALLING"}]
    assert annotate_turn_states(
        rows, {"a": {"state": "BASING", "days_in_state": 2}}) == 1
    assert rows[0]["turn_state"] == "BASING"
    assert rows[0]["turn_days_in_state"] == 2
    assert rows[1] == {"id": "q", "turn_state": "FALLING"}


def test_load_turn_states_fail_open(tmp_path):
    from scripts._ths_turn_annotate import load_turn_states
    assert load_turn_states(tmp_path / "absent.json") == {}
    (tmp_path / "dir").mkdir()
    assert load_turn_states(tmp_path / "dir") == {}
    for name, payload in (("bad.json", "{not json"),
                          ("bom.json", b"\xff\xfe\x00"),
                          ("list.json", "[1, 2]"),
                          ("badbaskets.json", '{"baskets": [1]}'),
                          ("nobaskets.json", '{"as_of": "2026-10-16"}')):
        p = tmp_path / name
        if isinstance(payload, bytes):
            p.write_bytes(payload)
        else:
            p.write_text(payload)
        assert load_turn_states(p) == {}, name
    good = tmp_path / "good.json"
    good.write_text('{"as_of": "2026-10-16", "baskets": {"a": '
                    '{"state": "BASING", "days_in_state": 3}}}')
    assert load_turn_states(good) == {
        "a": {"state": "BASING", "days_in_state": 3}}


# ---------------------------------------------------------------------------
# 8-10: scripts/build_baskets_china_ths.py (TEXT / AST only — never imported)
# ---------------------------------------------------------------------------

def test_builder_annotates_before_write_split_and_render():
    text = _BUILDER.read_text()
    assert "from scripts import _ths_turn_annotate as TA  # noqa: E402" in text
    assert ("TA.load_turn_states(site / \"chinabasketdata\" / "
            "\"basket_turn_cn.json\")") in text
    i_annot = text.index("TA.annotate_turn_states(")
    i_write = text.index("(fdir / \"baskets_ths.json\").write_text(")
    i_split = text.index("split_for_page(data, chart)")
    i_render = text.index(".render(")
    assert i_annot < i_write < i_split < i_render
    assert "except Exception" in text[i_annot:text.index(
        '    fdir = site / "chinabasketdata"')]


def test_builder_disk_block_reuses_the_helper():
    text = _BUILDER.read_text()
    assert text.count("TA.annotate_turn_states(") == 2
    assert ("TA.annotate_turn_states(_ths_bj.get(\"baskets\"), "
            "_ths_turn_states)") in text
    assert "_ths_bj_path.write_text(" in text
    assert "_b[\"turn_state\"] =" not in text
    assert "for _b in (_ths_bj.get(\"baskets\") or []):" not in text


def test_split_keeps_the_chip_fields_and_drops_the_heavy_ones():
    tree = ast.parse(_BUILDER.read_text())
    kept = [n for n in tree.body
            if (isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in
                ("HYDRATE_REL", "_SLIM_ROW_DROP") for t in n.targets))
            or (isinstance(n, ast.FunctionDef) and n.name == "split_for_page")]
    ns: dict = {}
    exec(compile(ast.Module(body=kept, type_ignores=[]), "<split>", "exec"), ns)
    assert ns["_SLIM_ROW_DROP"] == ("members", "turn_evidence", "turn_dd_252")
    data = {"as_of": "2026-10-16", "baskets": [
        {"id": "a", "members": [{"code": "1"}], "turn_state": "BASING",
         "turn_days_in_state": 3, "turn_evidence": ["e"],
         "turn_dd_252": -0.2, "ret_60d": 0.1}]}
    chart = {"dates": [], "bench": [], "baskets": {}}
    before = copy.deepcopy(data)
    slim_data, _slim_chart, hydrate = ns["split_for_page"](data, chart)
    assert slim_data["baskets"][0] == {
        "id": "a", "turn_state": "BASING", "turn_days_in_state": 3,
        "ret_60d": 0.1}
    assert hydrate["members"] == {"a": [{"code": "1"}]}
    assert data == before


# ---------------------------------------------------------------------------
# 11-16: templates/baskets_china_factorwatch.html.j2
# ---------------------------------------------------------------------------

def test_turn_plain_keeps_exactly_the_four_lifecycle_states():
    html = _page_with_chips()
    m = re.search(r"const TURN_PLAIN = \{.*?\n\};\n", html, re.S)
    assert m, "no TURN_PLAIN block found"
    keys = re.findall(r"^\s+([A-Z_]+):", m.group(0), re.M)
    assert keys == ["WASHED_OUT", "BASING", "TURNING", "CONFIRMED"]


def test_every_call_site_passes_the_session_count():
    html = _page_with_chips()
    assert "const turnChipHtml = (ts, days) => {" in html
    assert len(re.findall(
        r"turnChipHtml\(b\.turn_state\s*,\s*b\.turn_days_in_state\)",
        html)) == 3
    assert "turnChipHtml(b.turn_state)" not in html


def _node_script() -> str:
    """The page's own TURN_PLAIN, turnChipHtml and esc, plus a driver."""
    html = _page_with_chips()
    plain = re.search(r"const TURN_PLAIN = \{.*?\n\};\n", html, re.S)
    chip = re.search(r"const turnChipHtml = .*?\n\};\n", html, re.S)
    esc = re.search(r"^const esc .*?;\n", html, re.M)
    assert plain and chip and esc, "chip machinery not extractable"
    driver = "\n".join([
        "const out = [];",
        "_L='en';",
        "out.push(turnChipHtml('BASING', 3));",
        "out.push(turnChipHtml('TURNING', 1));",
        "out.push(turnChipHtml('CONFIRMED', 2));",
        "out.push(turnChipHtml('WASHED_OUT', 1));",
        "_L='zh';",
        "out.push(turnChipHtml('BASING', 3));",
        "out.push(turnChipHtml('TURNING', 1));",
        "_L='en';",
        "for (const d of [0, null, '3', true, undefined, 2.5, -1]) {"
        " out.push(turnChipHtml('BASING', d)); }",
        "out.push(turnChipHtml('FALLING', 4));",
        "out.push(turnChipHtml('NONE', 2));",
        "out.push(turnChipHtml(undefined, 3));",
        "process.stdout.write(out.join('\\n===\\n'));",
    ])
    return ("let _L='en'; const LANG=()=>_L;\n"
            + esc.group(0) + plain.group(0) + chip.group(0) + driver)


def _node_expected() -> list:
    out = list(EN_TIPS) + list(ZH_TIPS)
    out += ['<span class="turn-chip basing">basing</span>'] * 7
    out += ["", "", ""]
    return out


def test_chip_tooltip_behaviour_in_node():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    proc = subprocess.run([node, "-e", _node_script()],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split("\n===\n") == _node_expected()


def test_chip_tooltip_source_guards():
    slice_ = _chip_slice(_source())
    for tok in ("Number.isInteger(days) && days > 0",
                "ts==='TURNING' || ts==='CONFIRMED'",
                "recorded session", "turning or confirmed", "in this state",
                "已记录", "个交易日", "转折或确认", "该状态"):
        assert tok in slice_, tok


def test_added_template_lines_add_no_style_or_colour_literal():
    slice_ = _chip_slice(_source())
    for bad in ("style", "rgb(", "hsl(", "color-mix", "border-left",
                "innerHTML"):
        assert bad not in slice_, bad
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", slice_)
    for line in slice_.splitlines():
        assert len(line) <= 100, line


def test_tooltip_copy_has_no_banned_word():
    texts = [_chip_slice(_source())]
    if shutil.which("node") is not None:
        texts += EN_TIPS + ZH_TIPS
    for text in texts:
        low = text.lower()
        for tok in BANNED:
            assert tok.lower() not in low, tok
