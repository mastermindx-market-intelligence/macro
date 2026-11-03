"""SC_FACE render seam (templates/sector_cycles_face.js, sc-face.v1): truth-state, copy-trace and ZH contracts.

The face module is a pure string renderer, so every case runs it in a bare node vm sandbox (no DOM, no
fetch, no clock) against the frozen example dataset plus the labelled synthetic fixture in
tests/fixtures/sector_cycles_face/face_cases.json.
"""
from __future__ import annotations

import ast
import copy
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FACE = ROOT / "templates" / "sector_cycles_face.js"
BASE_JS = ROOT / "templates" / "sector_cycles.js"
CSS = ROOT / "templates" / "sector_cycles.css"
REF = ROOT / "design_refs" / "sector-paper-20261021"
DS = REF / "cycles_repair" / "example_dataset.json"
ENUM = REF / "cycles_repair" / "enum_zh.json"
DECK_JSON = REF / "copy_deck.json"
ZHGREP = REF / "components" / "zh_latin_grep.py"
CASES = ROOT / "tests" / "fixtures" / "sector_cycles_face" / "face_cases.json"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is required to run the SC_FACE seam")

_RUNNER = r"""
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync(process.argv[1], 'utf8');
const sb = { window: {} }; vm.createContext(sb); vm.runInContext(src, sb);
const F = sb.window.SC_FACE;
const calls = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = calls.map(function (c) {
  try {
    if (c[0] === '__keys') return { ok: true, v: Object.keys(F).sort() };
    if (c[0] === '__get') return { ok: true, v: F[c[1][0]] };
    return { ok: true, v: F[c[0]].apply(null, c[1]) };
  } catch (e) { return { ok: false, err: String(e && e.message || e) }; }
});
process.stdout.write(JSON.stringify(out));
"""

SRC = FACE.read_text(encoding="utf-8")
DATA = json.loads(DS.read_text(encoding="utf-8"))
FIX = json.loads(CASES.read_text(encoding="utf-8"))
META = DATA["meta"]
BY_ID = {s["id"]: s for s in DATA["sectors"]}


def _table(name: str):
    m = re.search(r"^  var " + name + r" = (.*);$", SRC, re.M)
    assert m, name
    return json.loads(m.group(1))


DECK = _table("DECK")
DECK_SRC = _table("DECK_SRC")


def _run(calls):
    proc = subprocess.run(["node", "-e", _RUNNER, str(FACE)], input=json.dumps(calls), capture_output=True,
                          text=True, cwd=str(ROOT))
    assert proc.returncode == 0, proc.stderr[-2000:]
    res = json.loads(proc.stdout)
    for c, r in zip(calls, res):
        assert r["ok"], (c[0], r.get("err"))
    return [r["v"] for r in res]


def _one(fn, *args):
    return _run([[fn, list(args)]])[0]


def ctx(lang="en", **kw):
    c = {"lang": lang, "today": 2026.80, "meta": META, "asof": META["asOf"]}
    c.update(kw)
    return c


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
            .replace("'", "&#x27;"))


def en(key: str, **f) -> str:
    s = DECK[key][0]
    for k, v in f.items():
        s = s.replace("{" + k + "}", str(v))
    return esc(s)


def zh(key: str, **f) -> str:
    s = DECK[key][1]
    for k, v in f.items():
        s = s.replace("{" + k + "}", str(v))
    return esc(s)


def rec(sid="xlf"):
    return copy.deepcopy(BY_ID[sid])


def outside_details(html: str) -> str:
    return re.sub(r"<details\b.*?</details>", "", html, flags=re.S)


# ---------------------------------------------------------------- hazard truth table (C13/C22)

def test_hazard_pass_predicate_is_byte_frozen():
    line = ("SC_FACE.hazardPass = function (cell, ek, key) { return !!cell && cell.p != null && cell.source === 'MODEL' "
            "&& cell.cell_verdict === 'PASS' && !!ek && !!ek.hazard && ek.hazard[key] === 'qualified_model_cell' "
            "&& ek.model_cell_current_claim === 'parity_holds'; }")
    assert line in SRC.splitlines()


MODEL_PASS = {"p": 0.4, "source": "MODEL", "cell_verdict": "PASS"}


@pytest.mark.parametrize("cell,tag,claim,unavailable,want", [
    (MODEL_PASS, "qualified_model_cell", "parity_holds", False, "pass"),
    (MODEL_PASS, "qualified_model_cell", "parity_failed", False, "muted"),
    (MODEL_PASS, "qualified_model_cell", None, False, "muted"),
    (MODEL_PASS, "qualified_model_cell", "parity_unmeasured", False, "muted"),
    ({"p": 0.4, "source": "MODEL", "cell_verdict": "FAIL"}, "qualified_model_cell", "parity_holds", False, "muted"),
    (MODEL_PASS, "prior_cell", "parity_holds", False, "muted"),
    ({"p": 0.3, "source": "PRIOR"}, "prior_cell", "parity_holds", False, "prior"),
    (MODEL_PASS, "missing_estimate", "parity_holds", False, "gap"),
    ({"p": None, "source": "MODEL", "cell_verdict": "PASS"}, "qualified_model_cell", "parity_holds", False, "gap"),
    ({"p": 0.4, "source": "OTHER"}, "qualified_model_cell", "parity_holds", False, "gap"),
    (MODEL_PASS, "qualified_model_cell", "parity_holds", True, "gap"),
])
def test_cell_state_truth_table(cell, tag, claim, unavailable, want):
    h = {"3m": cell, "unavailable": unavailable}
    ek = {"hazard": {"3m": tag}, "model_cell_current_claim": claim}
    assert _one("cellState", h, ek, "3m") == want


def test_parity_failed_never_shows_model_badge_and_parity_holds_does():
    failed = rec("xlf")
    holds = rec("xlf")
    holds["estimate_kinds"]["model_cell_current_claim"] = "parity_holds"
    hf, hh = _run([["hazard", [failed, ctx()]], ["hazard", [holds, ctx()]]])
    assert hf.count('data-state="muted"') == 3 and 'class="scf-badge" data-source="model"' not in hf
    assert en("cycles.hazard_parity_chip") in hf and en("cycles.hazard_face_note") in hf
    assert hh.count('data-state="pass"') == 3 and hh.count('class="scf-badge" data-source="model"') == 3
    assert ">40%<" in hh and en("cycles.hazard_parity_chip") not in hh


def test_missing_estimates_and_unavailable_hazard_render_as_gaps_not_zero():
    xlk = rec("xlk")
    off = rec("xlf")
    off["now"]["hazard"]["unavailable"] = True
    hk, ho = _run([["hazard", [xlk, ctx()]], ["hazard", [off, ctx()]]])
    for h in (hk, ho):
        assert h.count('data-state="gap"') == 3 and en("cycles.hazard_unavailable") in h
        assert "0%" not in h


def test_prior_and_partial_cells_carry_their_gloss():
    r = rec("xlf")
    r["now"]["hazard"]["1m"] = {"p": 0.3, "source": "PRIOR"}
    r["now"]["hazard"]["6m"] = {"p": None, "source": "MODEL"}
    r["estimate_kinds"]["hazard"]["1m"] = "prior_cell"
    h = _one("hazard", r, ctx())
    assert 'data-state="prior"' in h and en("components.prior_gloss") in h
    assert 'data-deck-gap="hazard-partial-cell"' in h


def _chip_case(states):
    r = rec("xlf")
    r["estimate_kinds"]["model_cell_current_claim"] = "parity_holds"
    for k, st in states.items():
        if st == "pass":
            r["now"]["hazard"][k] = dict(MODEL_PASS)
            r["estimate_kinds"]["hazard"][k] = "qualified_model_cell"
        elif st == "prior":
            r["now"]["hazard"][k] = {"p": 0.3, "source": "PRIOR"}
            r["estimate_kinds"]["hazard"][k] = "prior_cell"
        elif st == "muted":
            r["now"]["hazard"][k] = {"p": 0.4, "source": "MODEL", "cell_verdict": "FAIL"}
        else:
            r["now"]["hazard"][k] = None
    return r


@pytest.mark.parametrize("states,want_state,want_label", [
    ({"1m": "pass", "3m": "pass", "6m": "pass"}, "pass", "cycles.hz_3m_chip"),
    ({"1m": "pass", "3m": "prior", "6m": "gap"}, "pass", "cycles.hz_1m_chip"),
    ({"1m": "prior", "3m": "prior", "6m": "pass"}, "prior", "cycles.hz_3m_chip"),
    ({"1m": "gap", "3m": "muted", "6m": "gap"}, "muted", "cycles.hz_3m_chip"),
    ({"1m": "gap", "3m": "gap", "6m": "pass"}, None, None),
])
def test_hazard_chip_pick_order(states, want_state, want_label):
    chip = _one("hazardChip", _chip_case(states), ctx())
    if want_state is None:
        assert chip == ""
        return
    assert f'data-state="{want_state}"' in chip and en(want_label) in chip


# ---------------------------------------------------------------- one-clock face, contradictions (C11)

def _contradiction():
    r = rec("xlf")
    r["now"].update({"phase_v2": "Trough", "pos_v2": 88, "phase": "Expansion"})
    return r


def test_contradiction_withholds_disagreeing_clocks():
    r = _contradiction()
    lines, card, read, rhythm, hazard = _run([["clockLines", [r]], ["card", [r, ctx()]], ["readFace", [r, ctx()]],
                                              ["rhythm", [r, ctx()]], ["hazard", [r, ctx()]]])
    assert [x[3] for x in lines] == ["ladder", "rhythm", "read"]
    assert en("cycles.phase_bottoming_chip") in card and zh("cycles.phase_bottoming_chip") in card
    assert read["withheld"] is True and en("cycles.read_withheld_face") in read["html"]
    assert rhythm == ""
    assert 'data-state="muted"' in hazard
    assert esc(r["now"]["read"]) not in outside_details(card)


def test_ladder_line_only_when_divergent():
    on = rec("xlf")
    off = rec("xlf")
    off["now"]["divergence"] = False
    a, b = _run([["clockLines", [on]], ["clockLines", [off]]])
    assert "ladder" in [x[3] for x in a] and "ladder" not in [x[3] for x in b]


def test_withheld_read_on_example_dataset():
    out = _run([["readFace", [rec(s), ctx()]] for s in ("xlf", "xlk", "xlc")])
    assert out[2]["withheld"] is True


# ---------------------------------------------------------------- #10534 projection wording

def _expansion():
    r = rec("xlf")
    r["now"]["phase_v2"] = "Expansion"
    r["rhythm"]["overdue"] = True
    return r


def test_elapsed_projection_reads_as_reference_not_forecast():
    r = _expansion()
    past, fresh = _run([["rhythm", [r, ctx()]], ["rhythm", [r, ctx(today=None)]]])
    assert "ref: Peak was proj. Jul ’26 — elapsed" in past and "参考：顶部原预计 2026年7月 — 已过" in past
    assert 'data-past="true"' in past and 'data-overdue="true"' in past and "Next ▲" not in past
    assert "Next ▲ Jul ’26" in fresh and 'data-past="false"' in fresh


def test_projection_wording_matches_base_renderer():
    base = BASE_JS.read_text(encoding="utf-8")
    for frag in ("ref: ", " was proj. ", "elapsed", "参考：", "原预计 ", "已过", "Next ", "下次"):
        assert frag in base, frag


# ---------------------------------------------------------------- card furniture

def test_phase_age_states():
    a = rec("xlf")
    b = rec("xlf")
    b["now"]["phase_v2_age"] = {"status": "measured", "sessions": 12}
    c = rec("xlf")
    c["now"]["phase_v2_age"] = None
    x, y, z = _run([["phaseAge", [a, ctx()]], ["phaseAge", [b, ctx()]], ["phaseAge", [c, ctx()]]])
    assert 'data-age="lower_bound"' in x and en("cycles.phase_age_lower_bound", n=5, date="2026-10-13") in x
    assert 'data-age="measured"' in y and en("cycles.phase_age_measured", n=12) in y
    assert 'data-age="unknown"' in z and en("cycles.phase_age_unknown") in z


def test_stance_ink_and_null_stance():
    s, n = _run([["stance", [rec("xlf"), ctx()]], ["stance", [DATA["_fixtures"]["null_stance"], ctx()]]])
    assert 'data-stance="watch"' in s and 'data-ink="warn"' in s
    assert en("cycles.stance_unavailable") in n and "data-stance=" not in n


def test_tr_fallback_basis_is_a_gap():
    r = rec("xlf")
    r["basis"] = "tr_fallback"
    assert 'data-deck-gap="basis-tr_fallback"' in _one("card", r, ctx())


def test_fixture_and_thin_history_chips():
    r = rec("xlf")
    r["now"]["thin_history"] = True
    card = _one("card", r, ctx(fixture=True))
    assert en("cycles.short_history_chip") in card


# ---------------------------------------------------------------- focus panels

def _rs():
    r = rec("xlf")
    r["rs_history"] = FIX["rs_history"]
    r["rs_history_rows_excluded_nonfinite"] = FIX["rs_history_rows_excluded_nonfinite"]
    return r


def test_rs_trail_breaks_on_gaps_and_counts_exclusions():
    html, none = _run([["rsTrail", [_rs(), ctx()]], ["rsTrail", [rec("xlf"), ctx()]]])
    d21 = re.search(r'class="scf-rs-21" d="([^"]*)"', html).group(1)
    d63 = re.search(r'class="scf-rs-63" d="([^"]*)"', html).group(1)
    assert d21.count("M") == 3 and d63.count("M") == 2
    assert "7 · rs_history_rows_excluded_nonfinite 1" in html
    assert 'data-deck-gap="rs-history"' in none


def test_turn_inspector_labels_and_gaps():
    r = rec("xlf")
    empty = rec("xlf")
    empty["turns_tail"] = []
    last, first, none = _run([["turnInspector", [r, ctx()]], ["turnInspector", [r, ctx(), 0]],
                              ["turnInspector", [empty, ctx()]]])
    assert "Last peak" in last and "Sep ’26" in last and 'data-deck-gap="turn-confirmation"' in last
    assert 'data-deck-gap="turn-confirmation-label"' in last and ">turns_tail[2].provisional<" in last and ">true<" in last
    assert 'data-deck-gap="turn-pivot-label"' in first and ">turns_tail[0].k peak<" in first
    assert 'data-deck-gap="turn-none"' in none


def test_label_gaps_never_render_unavailable_beside_a_present_value():
    """L2 repair 1: a deck-gap LABEL beside a present value names the producer field (EN face only, the ZH face
    stays zero-Latin) instead of the "Unavailable today" value-slot copy; a row whose label AND value are both
    deck gaps is not drawn (hidden marker only). Reverting any repaired site to gap() fails this test."""
    r = rec("xlf")
    calls = []
    for lang in ("en", "zh"):
        calls += [["evidence", [FIX["grader"], ctx(lang)]], ["turnInspector", [r, ctx(lang)]],
                  ["turnInspector", [r, ctx(lang), 0]], ["trendRisk", [r, ctx(lang), FIX["central_trend_pass"]]],
                  ["trendRisk", [r, ctx(lang)]]]
    out = _run(calls)
    for h in out[:5]:
        assert "Unavailable today" not in h, h
    for h in out[5:]:
        assert "今日暂不可用" not in h, h
    ev, last, first, tp, fb = out[:5]
    for gid, field, h in (("horizon-label", "by_horizon", ev),
                          ("conditional-hit-rate-label", "conditional_directional_hit_rate", ev),
                          ("turn-pivot-label", "turns_tail[0].k peak", first),
                          ("turn-confirmation-label", "turns_tail[2].provisional", last),
                          ("trend-gate-label", "forward.trend_pass", tp),
                          ("trend-gate-label", "now.above200d", fb)):
        m = re.search(r'<span class="scf-gap-lbl" data-deck-gap="' + re.escape(gid) + r'">(.*?)</span></span>', h)
        assert m and '<span class="l-en"><code class="scf-code">' + esc(field) + "</code>" in m.group(0), (gid, h)
        assert '<span class="l-zh"></span>' in m.group(0)
    for gid, h in (("turn-confirmation", last), ("turn-method-label", last), ("turn-method", last),
                   ("entry-suitability-label", tp), ("entry-null", tp), ("evidence-date-label", tp)):
        assert '<span hidden data-deck-gap="' + gid + '"></span>' in h, gid
    assert 'data-row="entry"' not in tp and 'data-row="entry"' not in fb


def test_trend_risk_gate_sources():
    r = rec("xlf")
    bare = rec("xlf")
    del bare["now"]["above200d"]
    p, f, fb, g = _run([["trendRisk", [r, ctx(), FIX["central_trend_pass"]]],
                        ["trendRisk", [r, ctx(), FIX["central_trend_fail"]]],
                        ["trendRisk", [r, ctx()]], ["trendRisk", [bare, ctx()]]])
    assert 'data-trend-pass="true"' in p and esc(FIX["central_trend_pass"]["reasoning"][1]["en"]) in p
    assert 'data-trend-pass="false"' in f
    assert "above 200d" in fb and "data-trend-pass" not in fb
    assert 'data-deck-gap="trend-gate"' in g
    for h in (p, f, fb, g):
        assert en("cycles.sizing_inert") in h and en("brief.lanes_disclaimer") in h


def test_evidence_grader_honest_counts():
    g, u, z = _run([["evidence", [FIX["grader"], ctx()]], ["evidence", [FIX["grader_unavailable"], ctx()]],
                    ["evidence", [FIX["grader"], ctx("zh")]]])
    assert "60.0% · 18/30" in g and ">10/40<" in g and "55.0% · 11/20" in g
    assert en("authority.accruing_body", n=5) in g
    assert "invalidated_membership 2" in g and "invalidated_membership 2" not in outside_details(g)
    caption = en("components.grader_caption")
    assert caption in g
    assert g.lower().count("win rate") == caption.lower().count("win rate")
    assert 'data-deck-gap="grader-unavailable"' in u and "no calls logged yet" in u
    assert "21日" in z


def test_methods_parity_chip_follows_meta_verdict():
    holds = dict(META, live_hazard_parity=dict(META["live_hazard_parity"], verdict="PARITY_HOLDS"))
    f, h = _run([["methods", [META, ctx()]], ["methods", [holds, ctx()]]])
    assert en("cycles.hazard_parity_chip") in f and en("cycles.hazard_parity_chip") not in h
    for x in (f, h):
        assert en("cycles.sizing_inert") in x and en("cycles.leadlag_stop") in x
        assert esc(DECK_SRC["cycles.sizing_inert"]) in x


def test_timing_state_chip_and_unknown_state():
    r = rec("xlf")
    bad = rec("xlf")
    bad["now"]["timing_state"] = "NOT_A_STATE"
    a, b = _run([["timing", [r, ctx()]], ["timing", [bad, ctx()]]])
    assert 'data-state="RALLY ON"' in a
    assert 'data-deck-gap="timing-state"' in b


# ---------------------------------------------------------------- copy trace

def _engine_literal(path: str, name: str):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        tgt = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            tgt = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            tgt = node.target.id
        if tgt == name:
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in {path}")


def test_tables_equal_their_sources():
    deck = json.loads(DECK_JSON.read_text(encoding="utf-8"))
    sections = deck.get("sections", deck)
    for key, (e, z) in DECK.items():
        sec, k = key.split(".", 1)
        assert sections[sec][k]["en"] == e and sections[sec][k]["zh"] == z, key
    for key, s in DECK_SRC.items():
        sec, k = key.split(".", 1)
        assert sections[sec][k]["source"] == s, key
    enum = {k: v for k, v in json.loads(ENUM.read_text(encoding="utf-8")).items() if k != "_source"}
    assert _table("ENUM_ZH") == enum
    phases = _engine_literal("engine/cycle_ontology.py", "PHASES")
    if isinstance(phases, (list, tuple)):
        phases = {p.get("key", p.get("phase")): p for p in phases}
    want = {k: {f: v[f] for f in ("label", "label_zh", "short", "short_zh") if f in v} for k, v in phases.items()}
    assert _table("PHASES") == want
    sd = _engine_literal("engine/cycles.py", "STATE_DISPLAY")
    assert _table("STATE_DISPLAY") == {k: [v["label"], v["label_zh"]] for k, v in sd.items()}


def test_every_literal_deck_key_is_in_the_table():
    keys = set(re.findall(r"\b(?:D|D2|T|dk)\('([a-z_]+\.[a-z0-9_]*[a-z0-9])'", SRC))
    keys |= set(re.findall(r"\['([a-z]+\.[a-z0-9_]+_chip)'", SRC))
    assert len(keys) > 40
    missing = sorted(k for k in keys if k not in DECK)
    assert not missing, missing
    # keys built by concatenation: 'cycles.leg_' + direction, 'cycles.win_' + window edge
    for k in ("cycles.leg_down", "cycles.leg_up", "cycles.win_low", "cycles.win_central", "cycles.win_high"):
        assert k in DECK, k


def test_base_pairs_are_copied_from_the_base_renderer():
    base = BASE_JS.read_text(encoding="utf-8")
    bp = _one("__get", "_basePairs")
    assert len(bp) >= 10
    for k, (line, e, z) in bp.items():
        assert re.fullmatch(r":\d+", line), k
        for txt in (e, z):
            assert txt.strip() in base, (k, txt)


# ---------------------------------------------------------------- ZH and negative contracts

def test_zh_face_has_no_latin_leak(tmp_path):
    c = ctx("zh")
    calls = []
    for sid in ("xlf", "xlk", "xlc"):
        calls += [["card", [rec(sid), c]], ["timing", [rec(sid), c]], ["trendRisk", [rec(sid), c]],
                  ["turnInspector", [rec(sid), c]]]
    calls += [["rsTrail", [_rs(), c]], ["focus", [_rs(), c, FIX["central_trend_pass"]]],
              ["card", [_contradiction(), c]], ["rhythm", [_expansion(), c]],
              ["evidence", [FIX["grader"], c]], ["evidence", [FIX["grader_unavailable"], c]], ["methods", [META, c]]]
    body = "".join(_run(calls))
    dom = tmp_path / "zh.html"
    dom.write_text('<html lang="zh" data-lang="zh"><body>' + body + "</body></html>", encoding="utf-8")
    proc = subprocess.run(["python3", "-I", str(ZHGREP), str(dom)], capture_output=True, text=True)
    assert proc.returncode == 0 and "zh-latin=0" in proc.stdout, proc.stdout[-1500:]


def test_pure_render_seam_negatives():
    assert "Date.now" not in SRC and "new Date(" not in SRC
    assert "phase_v2_age_bars" not in SRC
    assert "document." not in SRC and "fetch(" not in SRC
    css = CSS.read_text(encoding="utf-8")
    i = css.find("/* sc-face.v1")
    assert i >= 0
    tail = css[i:]
    for bad in ("--up", "--down", "border-left", "inset"):
        assert bad not in tail, bad


def test_export_surface_is_pinned():
    keys = _run([["__keys", []]])[0]
    assert keys == sorted([
        "version", "_basePairs", "legFamily", "projPast", "hazardPass", "cellState", "clockLines", "stance",
        "phaseAge", "clocks", "hazard", "hazardChip", "rhythm", "readFace", "prov", "card", "timing", "rsTrail",
        "turnInspector", "trendRisk", "evidence", "methods", "focus"])
    assert re.search(r"SC_FACE = \{ version: 'sc-face\.v1' \}", SRC)
