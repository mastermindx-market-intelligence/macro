"""Lane L3 (programme 7646): Sector Cycles renderer / platform seam guards.

No jsdom here: functions are brace-extracted from templates/sector_cycles.js and the
two pure seam modules are run under node with minimal stubs. Text guards pin the
seam boundary (US Sector Central only), the banned-literal list for the L3 freezone,
and the no-accent-stripe rule for the platform stylesheet."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "templates"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node not installed")

HZ_FNS = ("esc", "_hzPass", "_hzTip", "_hzBadge", "_hzPick", "_hzWithheld",
          "hazardLineHTML", "hazardCardChip")
HASH_FNS = ("_seam", "_parseQs", "_hasQs", "_pendingQs", "_winDomain")


def _text(name):
    return (TPL / name).read_text(encoding="utf-8")


def _extract_js_fn(text, name):
    token = "function " + name + "("
    start = text.find(token)
    assert start != -1, name + " missing from sector_cycles.js"
    i = text.find("{", start)
    depth = 0
    for j, ch in enumerate(text[i:], i):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:j + 1]
    raise AssertionError("unbalanced " + name)


def _node(source):
    proc = subprocess.run([NODE, "-e", source], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _hz_src(lang="en", prelude=""):
    text = _text("sector_cycles.js")
    return (prelude + "\nfunction curLang(){return " + json.dumps(lang) + ";}\n"
            "function L(en, zh) { return curLang() === \"zh\" ? (zh || en) : en; }\n"
            + "\n".join(_extract_js_fn(text, n) for n in HZ_FNS) + "\n")


def _hash_src(prelude=""):
    text = _text("sector_cycles.js")
    return (prelude + "\nvar META = { xDomain: [0, 10] }, DEFAULT_VIEW = [5, 10];\n"
            + "\n".join(_extract_js_fn(text, n) for n in HASH_FNS) + "\n")


def _freezone():
    text = _text("sector_cycles.js")
    start = text.find("  function _seam() {")
    assert start != -1
    return text[start:]


# ---------------------------------------------------------------- hazard face

@needs_node
def test_hz_pass_truth_table_without_sc_face():
    cases = [
        [{"p": 0.4, "cell_verdict": "PASS"}, None],
        [{"p": 0.4, "cell_verdict": "PASS"}, {"model_cell_current_claim": "parity_holds"}],
        [{"p": 0.4, "cell_verdict": "PASS"}, {"model_cell_current_claim": "parity_fails"}],
        [{"p": 0.4, "source": "MODEL"}, None],
        [{"p": None, "cell_verdict": "PASS"}, None],
        [None, None],
    ]
    out = _node(_hz_src() + "var C = " + json.dumps(cases) + ";\n"
                "console.log(JSON.stringify(C.map(function (x) { return _hzPass(x[0], x[1], '3m'); })));")
    assert out == [True, True, False, False, False, False]


@needs_node
def test_hz_pass_delegates_to_sc_face_when_present():
    prelude = "var window = { SC_FACE: { hazardPass: function (c, ek, key) { return 'D:' + key; } } };"
    out = _node(_hz_src(prelude=prelude) + "console.log(JSON.stringify(_hzPass({}, null, '1m')));")
    assert out == "D:1m"


@needs_node
def test_hz_pick_model_only_cell_is_qualified_not_scored():
    src = _hz_src() + (
        "console.log(JSON.stringify(["
        "_hzPick({'3m': {p: 0.3, source: 'MODEL'}}, null),"
        "_hzPick({'3m': {p: 0.3, cell_verdict: 'PASS'}}, null),"
        "_hzPick({'1m': {p: 0.2, source: 'EMPIRICAL'}, '3m': {p: 0.5, source: 'MODEL'}}, null),"
        "_hzPick({}, null)]));")
    q, ok, prior, none = _node(src)
    assert q["key"] == "3m" and q["pass"] is False and q["q"] is True
    assert ok["key"] == "3m" and ok["pass"] is True and "q" not in ok
    assert prior["key"] == "1m" and prior["pass"] is False and "q" not in prior
    assert none is None


@needs_node
@pytest.mark.parametrize("lang,badge", [("en", "Live parity unproven"), ("zh", "实时一致性未证实")])
def test_card_chip_model_only_renders_unproven_badge_without_a_number(lang, badge):
    sector = {"now": {"hazard": {"3m": {"p": 0.3, "source": "MODEL"}}}}
    html = _node(_hz_src(lang) + "console.log(JSON.stringify(hazardCardChip(" + json.dumps(sector) + ")));")
    assert "cc-hz hz-muted" in html and "hz-q" in html and badge in html
    assert "30%" not in html and "<b>" not in html


@needs_node
def test_card_chip_legacy_pass_fixture_unchanged():
    sector = {"now": {"hazard": {"3m": {"p": 0.42, "cell_verdict": "PASS"}}}}
    html = _node(_hz_src() + "console.log(JSON.stringify(hazardCardChip(" + json.dumps(sector) + ")));")
    assert "<b>42%</b>" in html and "hz-pass" in html and "hz-muted" not in html


# ---------------------------------------------------------------- hash helpers

@needs_node
def test_parse_qs_filters_keys_lengths_and_bad_escapes():
    long_v = "a" * 400
    qs = "f=baskets&zz=1&m=xlk%2Cxle&w=%E0%A4&=x&s&v=" + long_v + "&x=lin&g=up%2Cdown"
    out = _node(_hash_src() + "console.log(JSON.stringify(_parseQs(" + json.dumps(qs) + ")));")
    assert out == {"f": "baskets", "m": "xlk,xle", "x": "lin", "g": "up,down"}


@needs_node
def test_hash_helpers_are_inert_without_the_seam():
    out = _node(_hash_src() + "console.log(JSON.stringify([_seam(), _hasQs('cycles/f=baskets'), _pendingQs('cycles/f=baskets')]));")
    assert out == [False, False, None]


@needs_node
def test_pending_qs_is_consumed_once_and_prefix_is_required():
    prelude = "var window = { SC_PLATFORM: {}, __siCyclesPending: 'f=baskets' };"
    out = _node(_hash_src(prelude) + (
        "var r = [_hasQs(''), _pendingQs('cycles/s=xlk'), window.__siCyclesPending, _pendingQs('cycles/s=xlk'),"
        " _pendingQs('cycles/'), _pendingQs('sectors/s=xlk'), _hasQs('cycles/'), _hasQs('cycles/v=bars')];"
        "console.log(JSON.stringify(r));"))
    assert out == [True, "f=baskets", None, "s=xlk", None, None, False, True]


@needs_node
def test_win_domain_presets_ranges_and_fallback():
    out = _node(_hash_src() + (
        "console.log(JSON.stringify(['', '0', '2', '3', '4', '1.5-7.25', '7-3', 'x-y', '9'].map(_winDomain)));"))
    assert out[0] == [5, 10]
    assert out[1] == [0, 10]
    assert out[2] == pytest.approx([6.7, 10])
    assert out[3] == pytest.approx([8.7, 10])
    assert out[4] == pytest.approx([9.15, 10])
    assert out[5] == [1.5, 7.25]
    assert out[6] == [5, 10] and out[7] == [5, 10] and out[8] == [5, 10]


# ---------------------------------------------------------------- pure seam modules

def _module_src(name):
    return "var window = {};\n" + _text(name) + "\n"


@needs_node
def test_compare_tray_contract():
    recs = [
        {"id": "xlk", "name": "Technology", "name_zh": "科技", "kind": "sector", "basis": "tr"},
        {"id": "b1", "name": "<b>AI</b>", "kind": "basket", "basis": "price"},
        {"id": "xle", "name": "Energy", "kind": "sector", "basis": "tr_fallback"},
        {"id": "xlf", "name": "Financials", "kind": "sector", "basis": "tr"},
        {"id": "xlu", "name": "Utilities", "kind": "sector", "basis": "tr"},
    ]
    src = _module_src("sector_cycles_compare.js") + (
        "var C = window.SC_COMPARE, R = " + json.dumps(recs) + ";"
        "console.log(JSON.stringify([C.version, C.max, C.tray([], {}), C.tray(R, {}),"
        " C.mixedBasis([R[0], R[3]]), C.mixedBasis([R[0], R[1]]), C.basisOf(R[2])]));")
    version, mx, empty, html, same, mixed, fallback = _node(src)
    assert version == "sc-compare.v1" and mx == 4 and empty == ""
    assert html.count('class="sc-cmp-row"') == 4 and 'data-id="xlu"' not in html
    assert '<button type="button" class="sc-cmp-clear" data-act="clear">' in html
    assert 'class="sc-cmp-btn" aria-pressed="true" data-id="xlk"' in html
    assert "sc-cmp-diff" in html and "不同基准" in html
    assert 'data-deck-gap="basis-tr_fallback"' in html and "今日暂不可用" in html
    assert "<b>AI</b>" not in html and "&lt;b&gt;AI&lt;/b&gt;" in html
    assert same is False and mixed is True and fallback is None


@needs_node
def test_platform_announce_and_return_focus():
    src = (
        "var node = { textContent: 'old' }, timers = [];"
        "var window = { document: { getElementById: function (id) { return id === 'sc-sr-status' ? node : null; } },"
        " setTimeout: function (f) { timers.push(f); } };\n"
        + _text("sector_cycles_platform.js") +
        "\nvar P = window.SC_PLATFORM, out = [P.version];"
        "out.push(P.announce('one')); out.push(node.textContent);"
        "P.announce('two'); timers.forEach(function (f) { f(); }); out.push(node.textContent);"
        "out.push(P.announce(null));"
        "var f = 0, el = { isConnected: true, focus: function () { f++; } };"
        "out.push(P.returnFocus(el), f, P.returnFocus({ isConnected: false, focus: function () {} }), P.returnFocus(null));"
        "out.push(P.zones.map(function (z) { return z[0]; }));"
        "console.log(JSON.stringify(out));")
    out = _node(src)
    assert out == ["sc-platform.v1", True, "", "two", False, True, 1, False, False,
                   ["chips", "list", "markers", "inspector", "compare"]]


# ---------------------------------------------------------------- text guards

def test_seam_is_sector_central_only():
    text = _text("sector_cycles.js")
    assert "function _seam() { return typeof window !== \"undefined\" && !!window.SC_PLATFORM; }" in text
    assert "function isCnMobile() { return (IS_CN || (typeof window !== \"undefined\" && !!window.SC_PLATFORM)) && isMobile(); }" in text
    assert "if (!IS_CN && !(typeof window !== \"undefined\" && window.SC_PLATFORM)) {" in text
    ws = _text("si_workspace.js")
    order = ["sector_cycles_states.js", "sector_cycles_face.js", "sector_cycles_compare.js",
             "sector_cycles_platform.js", "sector_cycles.js'"]
    pos = [ws.find(n) for n in order]
    assert all(p != -1 for p in pos) and pos == sorted(pos), pos


BANNED = ("409", "per_instrument", "forecast", "pushState", "scrollRestoration",
          "not a backtested prediction", "turnCallLine", "17 of 98",
          "⤢", "✕", "⟲", "rgba(", "hsl(")
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")


@pytest.mark.parametrize("where", ["freezone", "loadRotation", "sector_cycles_platform.js",
                                   "sector_cycles_compare.js"])
def test_l3_code_carries_no_banned_literals(where):
    if where == "freezone":
        body = _freezone()
    elif where == "loadRotation":
        body = _extract_js_fn(_text("sector_cycles.js"), "loadRotation")
    else:
        body = _text(where)
    hits = [b for b in BANNED if b in body]
    assert not hits, (where, hits)
    assert not HEX.search(body), (where, HEX.search(body).group(0))


def test_typed_rotation_path_never_collapses_to_null():
    body = _extract_js_fn(_text("sector_cycles.js"), "loadRotation")
    typed = body[:body.index("return;\n    }")]
    assert "ST.fetchTyped(\"marketdata/rotation_events.json\", { list: \"active\" })" in typed
    assert ".catch(" not in typed and "null; })" not in typed
    assert "_ROT_STATE = ev.state || \"unavailable\"" in typed


def test_platform_css_has_no_accent_stripe():
    css = _text("sector_cycles_platform.css")
    assert not re.search(r"border-(left|right|top|bottom)(-width|-color|-style)?\s*:", css)
    assert not re.search(r"border-inline(-start|-end)?\s*:", css)
    assert not re.search(r"box-shadow:[^;]*inset", css)
    assert not HEX.search(css) and "rgba(" not in css and "font-family" not in css


def test_zh_hazard_line_carries_no_latin_probability_symbol():
    # The ZH face uses the copy-deck form 转折≤1月 (cycles.hz_1m_chip.zh); the
    # Latin P( reading stays on the EN face and in the % cells' meaning.
    hz = [{"now": {"hazard": {"1m": {"p": 0.2, "cell_verdict": "PASS"},
                               "3m": {"p": 0.42, "cell_verdict": "PASS"}}}}]
    src = _hz_src("zh") + "var S=" + json.dumps(hz) + ";console.log(JSON.stringify(hazardLineHTML(S[0])));"
    zh = _node(src)
    assert "转折≤1月" in zh and "P(" not in zh
    en = _node(_hz_src("en") + "var S=" + json.dumps(hz) + ";console.log(JSON.stringify(hazardLineHTML(S[0])));")
    assert "P(turn ≤ 1m)" in en


# ------------------------------------------------- L3 repair: rotation_context

_FROM_ALIGN = ("var ST = { fromAlignment: function (a) { var s = a && a.status;"
               " return s === \"aligned\" ? \"fresh\" : s === \"incompatible_generation\" ? s"
               " : s === \"invalid_payload\" ? \"malformed\" : \"unavailable\"; } };\n")


def _rot_src():
    text = _text("sector_cycles.js")
    return ("var window = {}, ROT_BY_SEC = {}, FRAG_BY_KEY = {}, _ROT_STATE, _ROT_ALIGN,"
            " _FRAG_STATE, _FRAG_ALIGN, mounts = 0;\nfunction mountCards() { mounts++; }\n"
            + _FROM_ALIGN + _extract_js_fn(text, "_rotFromContext") + "\n"
            + _extract_js_fn(text, "_indexRotation") + "\n"
            "function run(has, rc, noST) { window.SECTOR_CYCLES = has ? { rotation_context: rc } : {};"
            " ROT_BY_SEC = {}; FRAG_BY_KEY = {}; _ROT_STATE = _FRAG_STATE = _ROT_ALIGN = _FRAG_ALIGN = undefined;"
            " mounts = 0; var r = _rotFromContext(noST ? null : ST);"
            " return { ret: r, rot: _ROT_STATE || null, frag: _FRAG_STATE || null,"
            " rk: Object.keys(ROT_BY_SEC).sort(), fk: Object.keys(FRAG_BY_KEY).sort(), mounts: mounts,"
            " ra: _ROT_ALIGN || null, fa: _FRAG_ALIGN || null }; }\n")


def _rot_case(rc, has=True, no_st=False):
    src = _rot_src() + "console.log(JSON.stringify(run(" + json.dumps(has) + ", " + json.dumps(rc) + ", " + json.dumps(no_st) + ")));"
    return _node(src)


_ALIGNED_EV = {"status": "aligned", "active": [{"sector": "xlk", "to_sector": "xlv"}]}
_ALIGNED_FR = {"status": "aligned", "sectors": [{"key": "xlk", "fragmented": True},
                                                {"key": "xle", "fragmented": False}]}


@needs_node
def test_rot_from_context_aligned_indexes_donor_receiver_and_fragmented_only():
    out = _rot_case({"schema": "sector_cycles.rotation_context.v1", "events": _ALIGNED_EV,
                     "fragmentation": _ALIGNED_FR})
    assert out["ret"] is True and (out["rot"], out["frag"]) == ("fresh", "fresh")
    assert out["rk"] == ["xlk", "xlv"] and out["fk"] == ["xlk"] and out["mounts"] == 1


@needs_node
def test_rot_from_context_aligned_empty_lists_are_empty_not_unavailable():
    out = _rot_case({"events": {"status": "aligned", "active": []},
                     "fragmentation": {"status": "aligned", "sectors": []}})
    assert (out["rot"], out["frag"]) == ("empty", "empty")
    assert out["rk"] == [] and out["fk"] == [] and out["mounts"] == 0


@needs_node
def test_rot_from_context_misaligned_side_never_indexes_its_list():
    out = _rot_case({"events": {"status": "incompatible_generation", "reason": "generation_mismatch",
                                "active": [{"sector": "xlk"}]},
                     "fragmentation": {"status": "missing_input", "reason": "missing_session"}})
    assert (out["rot"], out["frag"]) == ("incompatible_generation", "unavailable")
    assert out["rk"] == [] and out["fk"] == []
    assert out["ra"]["reason"] == "generation_mismatch" and out["fa"]["status"] == "missing_input"
    assert out["mounts"] == 1  # an odd typed state still repaints the cards


@needs_node
def test_rot_from_context_whole_block_unavailable_and_malformed_and_missing_side():
    whole = _rot_case({"schema": "sector_cycles.rotation_context.v1", "status": "unavailable",
                       "reason": "projection_error"})
    assert (whole["rot"], whole["frag"]) == ("unavailable", "unavailable")
    assert whole["ra"]["reason"] == "projection_error" and whole["fa"]["reason"] == "projection_error"
    bad = _rot_case({"events": {"status": "aligned", "active": {"xlk": 1}}, "fragmentation": _ALIGNED_FR})
    assert bad["rot"] == "malformed" and bad["rk"] == [] and bad["frag"] == "fresh"
    half = _rot_case({"events": _ALIGNED_EV})
    assert half["rot"] == "fresh" and half["frag"] == "unavailable"
    assert half["fa"] == {"status": "missing_input", "reason": "missing_session"}


@needs_node
def test_rot_from_context_defers_to_fetch_when_absent_or_no_states_module():
    assert _rot_case(None, has=False)["ret"] is False
    assert _rot_case({"events": _ALIGNED_EV}, no_st=True)["ret"] is False
    body = _extract_js_fn(_text("sector_cycles.js"), "loadRotation")
    assert body.index("if (_rotFromContext(ST)) return;") < body.index("ST.fetchTyped(")


def test_rotation_context_survives_core_split():
    from scripts._cycles_payload import split_cycles_payload
    rc = {"schema": "sector_cycles.rotation_context.v1", "events": _ALIGNED_EV,
          "fragmentation": _ALIGNED_FR}
    data = {"sectors": [{"id": "xlk", "price": [1.0, 2.0],
                         "turns": [{"k": "peak", "x": 1.0}]}], "rotation_context": rc}
    core, series = split_cycles_payload(data)[:2]
    assert core["rotation_context"] == rc
    assert "price" not in core["sectors"][0]
    assert data["rotation_context"] == rc  # input is not mutated


# --------------------------------------------- L3 repair: turn rail / mounting

@needs_node
def test_turns_of_keeps_stamped_peaks_and_troughs_only():
    fn = _extract_js_fn(_text("sector_cycles.js"), "_turnsOf")
    s = {"turns": [{"k": "Peak", "x": 1}, {"k": "trough", "x": 2}, {"k": "peak", "x": 3, "provisional": True},
                   {"k": "peak", "x": None}, {"k": "other", "x": 4}, None]}
    tail = {"turns_tail": [{"k": "TROUGH", "x": 5}]}
    out = _node(fn + "\nconsole.log(JSON.stringify([_turnsOf(" + json.dumps(s) + "), _turnsOf("
                + json.dumps(tail) + "), _turnsOf(null), _turnsOf({})]));")
    assert [t["x"] for t in out[0]] == [1, 2]
    assert [t["x"] for t in out[1]] == [5]
    assert out[2] == [] and out[3] == []


def test_rail_reads_turns_only_through_turns_of():
    text = _text("sector_cycles.js")
    for name in ("_paintRail", "_onRailClick"):
        body = _extract_js_fn(text, name)
        assert "_turnsOf(s)" in body, name
        assert "s.turns" not in body, name


def test_freezone_strings_are_deck_or_shipped_reuse():
    text = _text("sector_cycles.js")
    rx = re.compile(r'L\(\s*"((?:[^"\\]|\\.)*)"\s*,\s*"((?:[^"\\]|\\.)*)"\s*\)')
    deck = json.loads((ROOT / "design_refs/sector-paper-20261021/copy_deck.json").read_text(encoding="utf-8"))
    allowed = set()

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get("en"), str) and isinstance(o.get("zh"), str):
                allowed.add((o["en"], o["zh"]))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(deck)
    allowed |= set(rx.findall("\n".join(text.splitlines()[:2191])))
    assert "['Close', '关闭']" in _text("theme.js")  # shipped shell close label (close: pair)
    allowed.add(("Close", "关闭"))
    fz = _freezone()
    pairs = set(rx.findall(fz))
    assert pairs and fz.count("L(") == len(rx.findall(fz)), "every freezone L() must be a literal pair"
    assert not (pairs - allowed), sorted(pairs - allowed)


def _onshow_src(rects):
    fn = _extract_js_fn(_text("sector_cycles.js"), "_onShow")
    return ("var rects = " + str(rects) + ", cbs = [], rebuilds = 0, paints = 0, _heroDeferred = true, heroChart = {};\n"
            "var node = { getClientRects: function () { return { length: rects }; } };\n"
            "var document = { getElementById: function () { return node; } };\n"
            "var window = { requestAnimationFrame: function (f) { cbs.push(f); } };\n"
            "function rebuildHero() { rebuilds++; } function _paintRail() { paints++; }\n" + fn + "\n")


@needs_node
def test_on_show_mounts_a_deferred_hero_after_one_frame():
    hidden = _node(_onshow_src(0) + "_onShow(0); var a = [cbs.length, rebuilds, _heroDeferred];"
                   " cbs.shift()(); console.log(JSON.stringify([a, cbs.length, rebuilds, paints, _heroDeferred]));")
    assert hidden == [[1, 0, True], 0, 1, 1, False]
    shown = _node(_onshow_src(1) + "_onShow(0); console.log(JSON.stringify([cbs.length, rebuilds, paints, _heroDeferred]));")
    assert shown == [0, 1, 1, False]
    fz = _freezone()
    hero = fz[fz.index("  var _mh0 = mountHero;"):fz.index("  var _sr0 = scheduleReanchor;")]
    assert "!n.getClientRects().length) _heroDeferred = true" in hero
    assert 'e.detail === "cycles") _onShow(0)' in _extract_js_fn(fz, "_platInit")


@needs_node
def test_mobile_breakpoint_is_880_and_seam_opts_us_in():
    text = _text("sector_cycles.js")
    src = _extract_js_fn(text, "isMobile") + "\n" + _extract_js_fn(text, "isCnMobile") + "\n"
    cases = [(880, False, False), (881, False, False), (375, False, False), (375, True, False),
             (881, True, False), (375, False, True)]
    js = src + "var out = []; " + " ".join(
        "var window = { innerWidth: %d%s }; var IS_CN = %s; out.push([isMobile(), isCnMobile()]);"
        % (w, ", SC_PLATFORM: {}" if plat else "", "true" if cn else "false") for w, plat, cn in cases)
    out = _node(js + " console.log(JSON.stringify(out));")
    assert out == [[True, False], [False, False], [True, False], [True, True], [False, False], [True, True]]


def _visibility_src(seam):
    text = _text("sector_cycles.js")
    fz = _freezone()
    wrap = fz[fz.index("  var _av0 = applyVisibility;"):fz.index("  var _rr0 = rerender;")]
    return ("var ALL = [{id:'xlk',now:{phase:'Expansion'}},{id:'xle',now:{phase:'Peak'}},"
            "{id:'xlv',now:{phase:'Trough'}},{id:'xlu',now:{phase:'Trough'}}], byId = {};\n"
            "ALL.forEach(function (s) { byId[s.id] = s; });\n"
            "var PHASE_FILTER = [{key:'Peak'},{key:'Expansion'},{key:'Trough'}], phaseState = {Peak:true};\n"
            "var state = {focus:'xlk'}, basketShown = {}, chartHidden = {}, heroChart = null, mobileShowAll = false,"
            " mobileSel = null, _cmp = ['xlv'], sr = null;\n"
            "function activeList() { return ALL; } function isActive() { return true; }"
            " function isBasketRec() { return false; } function isCnMobile() { return false; }"
            " function mobileLeaders() { return {}; } function rebuildHero() {}\n"
            "var document = { querySelectorAll: function () { return []; } };\n"
            "function srStatus(m) { sr = m; } function updateBasketSel() {} function updateChartHint() {}"
            " function updateSeriesCount() {} function _paintEmpty() {} function L(en) { return en; }\n"
            "function _seam() { return " + ("true" if seam else "false") + "; }\n"
            + _extract_js_fn(text, "applyVisibility") + "\n" + wrap
            + "applyVisibility(); console.log(JSON.stringify([chartHidden, sr]));")


@needs_node
def test_pinned_focus_and_compared_ids_survive_phase_filter():
    hidden, sr = _node(_visibility_src(True))
    assert hidden == {"xlk": False, "xle": False, "xlv": False, "xlu": True}
    assert sr == "2 of 4 shown"  # denominator is the whole active list
    base_hidden, base_sr = _node(_visibility_src(False))
    assert base_hidden == {"xlk": False, "xle": False, "xlv": True, "xlu": True} and base_sr == sr


# ------------------------------------------------------------- wave lock

# BASE lines (1-based) the Cycles wave replaces 1:1 inside the line-neutral region.
WAVE_SEAM_LINES = {95, 258, 274, 647, 648, 1167, 1192, 1207, 1208, 1209, 1212, 1223,
                   1231, 1232, 1233, 1234, 1235, 1236, 1258, 1259, 1811}
WAVE_FROZEN_FNS = ("mountTurnRecord", "projPast", "stanceHTML", "applyVisibility",
                   "turnRecordText", "fmtMon", "cardNextTxt", "detailNextLabel", "isMobile")


def test_wave_lock_base_region_and_named_functions():
    import difflib
    import os
    base_ref = os.environ.get("SC_WAVE_LOCK_BASE")
    if not base_ref:
        pytest.skip("set SC_WAVE_LOCK_BASE=<base sha> to run the wave-lock evidence check")
    proc = subprocess.run(["git", "-C", str(ROOT), "show", base_ref + ":templates/sector_cycles.js"],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        pytest.skip("base revision not in this object store")
    base, cur = proc.stdout, _text("sector_cycles.js")
    b, c = base.splitlines()[:2191], cur.splitlines()[:2191]
    changed = set()
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=b, b=c, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        assert tag == "replace" and (i1, i2) == (j1, j2), (tag, i1 + 1, i2, j1 + 1, j2)
        changed.update(range(i1 + 1, i2 + 1))
    assert changed <= WAVE_SEAM_LINES, sorted(changed - WAVE_SEAM_LINES)
    for name in WAVE_FROZEN_FNS:
        assert _extract_js_fn(base, name) == _extract_js_fn(cur, name), name
