"""SC_STATES typed-state seam (templates/sector_cycles_states.js, sc-states.v1) and the server-printed Cycles head.

Lane L4 of programme 7646 (rows C20/C21 states half, C24, C27, C28, C01, D5). The module is a pure classifier and
string renderer, so its cases run in a bare node vm sandbox; the head is rendered from both Cycles templates with
labelled synthetic payloads, so the as-of date and the generation line are checked as the server prints them,
before any script runs.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "templates"
STATES_JS = TPL / "sector_cycles_states.js"
STATES_CSS = TPL / "sector_cycles_states.css"
US = "sector_cycles.html.j2"
CN = "sector_cycles_china.html.j2"
REF = ROOT / "design_refs" / "sector-paper-20261021"
DECK_JSON = REF / "copy_deck.json"
ZHGREP = REF / "components" / "zh_latin_grep.py"
SPDR = ["xlb", "xlc", "xle", "xlf", "xli", "xlk", "xlp", "xlre", "xlu", "xlv", "xly"]
UNAVAILABLE = '<span class="l-en">— unavailable</span><span class="l-zh">— 不可用</span>'

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is required to run the SC_STATES seam")

_RUNNER = r"""
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync(process.argv[1], 'utf8');
const sb = { window: {} }; vm.createContext(sb); vm.runInContext(src, sb);
const S = sb.window.SC_STATES;
const calls = JSON.parse(fs.readFileSync(0, 'utf8'));
(async function () {
  const out = [];
  for (const c of calls) {
    try {
      if (c[0] === '__keys') { out.push({ ok: true, v: Object.keys(S).sort() }); continue; }
      if (c[0] === '__fetch') {
        const mode = c[1][0], status = c[1][1], body = c[1][2], expect = c[1][3];
        sb.window.fetch = mode === 'reject' ? function () { return Promise.reject(new Error('net')); }
          : function () { return Promise.resolve({ status: status, text: function () { return Promise.resolve(body); } }); };
        out.push({ ok: true, v: await S.fetchTyped('fixture.json', expect) });
        continue;
      }
      out.push({ ok: true, v: S[c[0]].apply(null, c[1]) });
    } catch (e) { out.push({ ok: false, err: String(e && e.message || e) }); }
  }
  process.stdout.write(JSON.stringify(out));
})();
"""


def _run(calls):
    proc = subprocess.run(["node", "-e", _RUNNER, str(STATES_JS)], input=json.dumps(calls), capture_output=True,
                          text=True, cwd=str(ROOT), timeout=60)
    assert proc.returncode == 0, proc.stderr[-2000:]
    res = json.loads(proc.stdout)
    for c, r in zip(calls, res):
        assert r["ok"], (c, r.get("err"))
    return [r["v"] for r in res]


def _one(name, *args):
    return _run([[name, list(args)]])[0]


def _deck_pair(key):
    sec, k = key.split(".", 1)
    deck = json.loads(DECK_JSON.read_text(encoding="utf-8"))
    entry = deck.get("sections", deck)[sec][k]
    return entry["en"], entry["zh"]


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ---------------------------------------------------------------- the module


@needs_node
def test_deck_table_equals_the_copy_deck():
    m = re.search(r"^  var DECK = (.*);$", STATES_JS.read_text(encoding="utf-8"), re.M)
    assert m
    table = json.loads(m.group(1))
    assert len(table) >= 20
    for key, (en, zh) in table.items():
        assert [en, zh] == list(_deck_pair(key)), key


@needs_node
@pytest.mark.parametrize("http, body, expect, want", [
    (200, '{"sectors":[{"id":"xlk"}]}', {"list": "sectors"}, "fresh"),
    (204, None, None, "empty"),
    (401, None, None, "unauthorized"),
    (403, None, None, "forbidden"),
    (404, None, None, "not_found"),
    (500, None, None, "unavailable"),
    (0, None, None, "offline"),
    (200, "{not json", None, "malformed"),
    (200, "[1, 2]", None, "malformed"),
    (200, '{"ok": false}', None, "malformed"),
    (200, '{"sectors": "x"}', {"list": "sectors"}, "malformed"),
    (200, '{"sectors": []}', {"list": "sectors"}, "empty"),
    (200, '{"asOf": "2026-11-02", "sectors": [1]}', {"generation": "2026-11-03", "list": "sectors"},
     "incompatible_generation"),
    (200, '{"asOf": "2026-11-03", "sectors": [1]}', {"generation": "2026-11-03", "list": "sectors"}, "fresh"),
])
def test_classify_table(http, body, expect, want):
    assert _one("classify", http, body, expect) == want


@needs_node
def test_fetch_typed_never_rejects_and_never_hands_over_another_generation():
    res = _run([
        ["__fetch", ["ok", 200, '{"sectors":[{"id":"xlk"}]}', {"list": "sectors"}]],
        ["__fetch", ["ok", 404, "", None]],
        ["__fetch", ["ok", 200, "{bad", None]],
        ["__fetch", ["reject", 0, None, None]],
        ["__fetch", ["ok", 200, '{"asOf":"2026-11-02","sectors":[1]}', {"generation": "2026-11-03", "list": "sectors"}]],
    ])
    fresh, missing, parse, offline, other_day = res
    assert fresh["state"] == "fresh" and fresh["data"]["sectors"][0]["id"] == "xlk" and fresh["http"] == 200
    assert missing == {"state": "not_found", "data": None, "reason": "http_404", "http": 404}
    assert parse["state"] == "malformed" and parse["reason"] == "parse" and parse["data"] is None
    assert offline == {"state": "offline", "data": None, "reason": "network", "http": 0}
    assert other_day["state"] == "incompatible_generation" and other_day["data"] is None
    assert (other_day["artifact_session"], other_day["consumer_session"]) == ("2026-11-02", "2026-11-03")


@needs_node
@pytest.mark.parametrize("align, want", [
    ({"status": "aligned"}, "fresh"),
    ({"status": "incompatible_generation", "artifact_session": "2026-11-02", "consumer_session": "2026-11-03"},
     "incompatible_generation"),
    ({"status": "missing_input", "reason": "missing_session"}, "unavailable"),
    ({"status": "invalid_payload"}, "malformed"),
    ({"status": "unavailable", "reason": "projection_error"}, "unavailable"),
    (None, "unavailable"),
])
def test_from_alignment(align, want):
    assert _one("fromAlignment", align) == want


@needs_node
def test_generation_check_dates_the_mismatch_whichever_side_is_newer():
    a, b, c = _run([
        ["generationCheck", [[{"asOf": "2026-11-02"}, {"asOf": "2026-11-03"}]]],
        ["generationCheck", [[{"as_of": "2026-11-04"}, {"asOf": "2026-11-03"}]]],
        ["generationCheck", [[{"asOf": "2026-11-03"}, {}, {"asOf": "2026-11-03"}]]],
    ])
    assert (a["ok"], a["x"], a["y"]) == (False, "2026-11-02", "2026-11-03")
    assert (b["ok"], b["x"], b["y"]) == (False, "2026-11-04", "2026-11-03")
    assert c["ok"] is True and c["mismatches"] == []


@needs_node
def test_state_faces_are_deck_copy():
    assert _one("fieldUnavailable") == UNAVAILABLE
    cases = [
        ("fresh", {}, "states.fresh_title", None),
        ("empty", {}, "states.empty_title", None),
        ("unavailable", {}, "states.error_title", "states.error_body"),
        ("not_found", {}, "states.error_title", "states.error_body"),
        ("offline", {}, "states.error_title", "states.error_body"),
        ("unauthorized", {}, "states.no_access_title", None),
        ("forbidden", {}, "states.unauthorized_title", None),
        ("malformed", {}, "states.invalid_payload_title", None),
    ]
    out = _run([["stateHTML", [s, c]] for s, c, _, _ in cases])
    for (state, _, title, body), html in zip(cases, out):
        assert 'data-state="%s"' % state in html, state
        for txt in _deck_pair(title):
            assert ">" + _esc(txt) + "<" in html, (state, txt)
        if body:
            for txt in _deck_pair(body):
                assert ">" + _esc(txt) + "<" in html, (state, txt)
    # the ZH empty body names the brand in Latin script, so the empty face is its title only
    empty = out[1]
    for txt in _deck_pair("states.empty_body"):
        assert _esc(txt) not in empty


@needs_node
def test_every_state_renders_without_a_missing_deck_pair():
    names = _one("__keys")
    assert "STATES" in names
    states = _run([["stateHTML", [s, {}]] for s in
                   ["fresh", "empty", "unavailable", "unauthorized", "forbidden", "not_found", "malformed", "offline",
                    "incompatible_generation", "partial", "loading", "no_such_state"]])
    for html in states:
        assert html.startswith('<div class="sc-state') and "null" not in html and "undefined" not in html
    assert 'data-state="unavailable"' in states[-1]


@needs_node
def test_incompatible_generation_is_dated_never_merged():
    align = {"status": "incompatible_generation", "artifact_session": "2026-11-02", "consumer_session": "2026-11-03"}
    full, compact = _run([["stateHTML", ["incompatible_generation", {"align": align}]],
                          ["stateHTML", ["incompatible_generation", {"align": align, "compact": True}]]])
    en, zh = _deck_pair("states.incompatible_generation_body")
    for txt in (en, zh):
        filled = txt.replace("{x}", "2026-11-02").replace("{y}", "2026-11-03")
        assert ">" + _esc(filled) + "<" in full
        assert 'title="' + _esc(filled) + '"' in compact
    assert "{x}" not in full + compact and "{y}" not in full + compact


@needs_node
def test_fragmentation_unavailable_is_not_empty():
    unavailable, empty = _run([["stateHTML", ["unavailable", {"context": "fragmentation", "compact": True}]],
                               ["stateHTML", ["empty", {"context": "fragmentation", "compact": True}]]])
    chip_en, chip_zh = _deck_pair("cycles.fragmentation_chip")
    err_en, err_zh = _deck_pair("states.error_title")
    empty_en, _ = _deck_pair("states.empty_title")
    assert 'data-state="unavailable"' in unavailable and 'data-state="empty"' in empty
    for html in (unavailable, empty):
        assert chip_en in html and chip_zh in html
    assert err_en in unavailable and err_zh in unavailable and empty_en not in unavailable
    assert err_en not in empty and empty_en in empty


@needs_node
def test_coverage_counts_against_the_eleven_spdr_ids():
    ten = [{"id": i} for i in SPDR if i != "xlre"]
    partial, full, unknown, no_expect = _run([
        ["coverage", [ten, SPDR]],
        ["coverage", [[{"id": i} for i in SPDR], SPDR]],
        ["coverage", [None, SPDR]],
        ["coverage", [ten, []]],
    ])
    assert partial == {"state": "partial", "measured": 10, "expected": 11, "missing": ["xlre"]}
    assert full["state"] == "fresh" and full["measured"] == 11 and full["missing"] == []
    # an unknown roster is unavailable, never zero
    assert unknown == {"state": "unavailable", "measured": None, "expected": None, "missing": None}
    assert no_expect["state"] == "unavailable"


@needs_node
def test_zh_state_faces_carry_no_latin(tmp_path):
    align = {"artifact_session": "2026-11-02", "consumer_session": "2026-11-03"}
    calls = [["stateHTML", [s, {"align": align}]] for s in
             ["fresh", "empty", "unavailable", "unauthorized", "forbidden", "not_found", "malformed", "offline",
              "incompatible_generation", "partial", "loading"]]
    calls += [["stateHTML", ["unavailable", {"context": "fragmentation", "compact": True}]],
              ["stateHTML", ["unavailable", {"context": "coverage"}]], ["fieldUnavailable", []]]
    dom = tmp_path / "zh.html"
    dom.write_text('<html lang="zh" data-lang="zh"><body>' + "".join(_run(calls)) + "</body></html>",
                   encoding="utf-8")
    proc = subprocess.run([sys.executable, "-I", str(ZHGREP), str(dom)], capture_output=True, text=True)
    assert proc.returncode == 0 and "zh-latin=0" in proc.stdout, proc.stdout[-1500:]


@needs_node
def test_export_surface_is_pinned():
    assert _one("__keys") == sorted(["version", "classify", "fetchTyped", "generationCheck", "fromAlignment",
                                     "coverage", "stateHTML", "fieldUnavailable", "STATES", "_deck"])


# ---------------------------------------------------------------- the server-printed head (C24 / C27)

# Labelled synthetic payloads (lane L4 fixtures): only the fields the head reads.
def _rc(events="aligned", fragmentation="aligned"):
    def side(status):
        s = {"status": status, "reason": None, "artifact_session": "2026-11-03", "consumer_session": "2026-11-03"}
        if status == "incompatible_generation":
            s["artifact_session"] = "2026-11-02"
        return s
    return {"schema": "sector_cycles.rotation_context.v1", "events": dict(side(events), active=[]),
            "fragmentation": dict(side(fragmentation), sectors=[])}


FIXTURES = {
    "aligned": {"meta": {"asOf": "2026-11-03", "fixture": "L4 synthetic"}, "rotation_context": _rc()},
    "incompatible": {"meta": {"asOf": "2026-11-03", "fixture": "L4 synthetic"},
                     "rotation_context": _rc(fragmentation="incompatible_generation")},
    "missing": {"meta": {"asOf": "2026-11-03", "fixture": "L4 synthetic"}},
    "projection_error": {"meta": {"asOf": "2026-11-03", "fixture": "L4 synthetic"},
                         "rotation_context": {"schema": "sector_cycles.rotation_context.v1", "status": "unavailable",
                                              "reason": "projection_error"}},
    "no_date": {"meta": {"fixture": "L4 synthetic"}, "rotation_context": _rc()},
}


def _env():
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(TPL)), autoescape=False)
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:  # noqa: BLE001 — the head does not depend on the nav strings
        env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)
    return env


def _render(template, fixture):
    from scripts.build_sector_cycles import cycles_page_ctx
    ctx = cycles_page_ctx(FIXTURES[fixture], require_generation=(template == US))
    return _env().get_template(template).render(cycles_ctx=ctx)


class _Head(HTMLParser):
    """Records the .cyc-asof span and whether the Sector Central link sits inside it."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.l4_depth = 0
        self.l4_asof_text = []
        self.l4_link_in = None
        self.l4_asof_count = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if self.l4_depth:
            if tag == "span":
                self.l4_depth += 1
        elif tag == "span" and "cyc-asof" in cls:
            self.l4_depth = 1
            self.l4_asof_count += 1
        if tag == "a" and "cyc-open-central" in cls:
            self.l4_link_in = bool(self.l4_depth)

    def handle_endtag(self, tag):
        if self.l4_depth and tag == "span":
            self.l4_depth -= 1

    def handle_data(self, data):
        if self.l4_depth:
            self.l4_asof_text.append(data)


def _head(html):
    p = _Head()
    p.feed(html)
    return p


def _asof_block(html):
    m = re.search(r'<span class="cyc-asof">.*?<span id="sc-asof">.*?</span>(?:.*?</span>)*?</span>', html, re.S)
    assert m
    return html[html.index('<span class="cyc-asof">'):html.index("</header>")]


@pytest.mark.parametrize("template", [US, CN])
def test_the_date_is_printed_without_script(template):
    html = _render(template, "aligned")
    assert html.count('id="sc-asof"') == 1
    assert '<span id="sc-asof">2026-11-03</span>' in html
    assert _head(html).l4_asof_count == 1


@pytest.mark.parametrize("template", [US, CN])
def test_a_missing_date_prints_the_placeholder_the_client_fills(template):
    assert '<span id="sc-asof">…</span>' in _render(template, "no_date")


@pytest.mark.parametrize("fixture, gen, words", [
    ("aligned", "aligned", ("Up to date", "已是最新")),
    ("incompatible", "incompatible_generation", ("History is from a different day", "历史来自不同日期")),
    ("missing", "unavailable", ("— unavailable", "— 不可用")),
    ("projection_error", "unavailable", ("— unavailable", "— 不可用")),
])
def test_us_generation_line_is_a_projection_of_rotation_context(fixture, gen, words):
    block = _asof_block(_render(US, fixture))
    assert 'data-gen="%s"' % gen in block
    for w in words + ("Generation", "生成状态"):
        assert ">" + w + "<" in block or ">" + w + " <" in block, w
    if gen == "incompatible_generation":
        assert 'title="History 2026-11-02, current read 2026-11-03. Not drawn, so the two are never mixed."' in block
        assert 'title="历史 2026-11-02，当前读数 2026-11-03。不绘制，避免混用。"' in block


def test_us_central_link_sits_outside_the_as_of():
    html = _render(US, "aligned")
    p = _head(html)
    assert p.l4_link_in is False
    assert 'href="sector_central.html#cycles"' in html
    for txt in _deck_pair("dossier.open_central_link"):
        assert ">" + txt + "<" in html


def test_china_has_no_central_link_and_a_generation_line_only_when_stamped():
    stamped, unstamped = _render(CN, "incompatible"), _render(CN, "missing")
    assert "cyc-open-central" not in stamped + unstamped
    assert 'data-gen="incompatible_generation"' in stamped
    assert "sc-gen" not in _asof_block(unstamped)


def test_projection_reads_only_rotation_context_and_meta():
    from scripts.build_sector_cycles import cycles_page_ctx
    base = FIXTURES["incompatible"]
    noisy = dict(base, sectors=[{"id": "xlk", "status": "aligned"}], status="aligned", events={"status": "aligned"})
    assert cycles_page_ctx(noisy) == cycles_page_ctx(base)
    assert cycles_page_ctx(base)["generation"] == {"status": "incompatible_generation",
                                                    "artifact_session": "2026-11-02",
                                                    "consumer_session": "2026-11-03"}
    assert cycles_page_ctx({"meta": {}}, require_generation=False) == {"asof": None, "generation": None}
    assert cycles_page_ctx(None)["generation"]["status"] == "unavailable"


def test_china_head_carries_no_latin(tmp_path):
    for fixture in ("aligned", "incompatible", "missing"):
        dom = tmp_path / ("cn_%s.html" % fixture)
        dom.write_text('<html lang="zh" data-lang="zh"><body>' + _asof_block(_render(CN, fixture)) + "</body></html>",
                       encoding="utf-8")
        proc = subprocess.run([sys.executable, "-I", str(ZHGREP), str(dom)], capture_output=True, text=True)
        assert proc.returncode == 0 and "zh-latin=0" in proc.stdout, (fixture, proc.stdout[-800:])


# Latin on the China ZH face before this lane (members notice "A 股" and the Phase-0 provenance frame);
# L4 adds none. The set may shrink, never grow.
_CN_PRE_EXISTING_LATIN = {"A", "CHINA", "GS", "PATHWAY", "PHASE0", "Phase-0", "SECTOR", "X", "Y", "md", "research"}


def test_china_page_adds_no_latin_to_the_zh_face(tmp_path):
    dom = tmp_path / "cn_page.html"
    dom.write_text(_render(CN, "incompatible").replace("<html", '<html data-lang="zh"', 1), encoding="utf-8")
    proc = subprocess.run([sys.executable, "-I", str(ZHGREP), str(dom)], capture_output=True, text=True)
    m = re.match(r"zh-latin=(\d+)((?: \S+)*?) skip=", proc.stdout)
    assert m, proc.stdout[-800:]
    found = set(m.group(2).split())
    assert found <= _CN_PRE_EXISTING_LATIN, sorted(found - _CN_PRE_EXISTING_LATIN)


# ---------------------------------------------------------------- the client date setter (D5)

def _run_setter(template, server_text, meta):
    text = (TPL / template).read_text(encoding="utf-8")
    scripts = [b for b in re.findall(r"<script>(.*?)</script>", text, re.S) if "sc-asof" in b]
    assert scripts and sum("innerHTML" in b for b in scripts) == 1
    source = """
var listeners = {};
var asofEl = {textContent: %s, innerHTML: null, parentNode: {appendChild: function () {}}};
var document = {
  getElementById: function (id) { return id === 'sc-asof' ? asofEl : null; },
  createElement: function (tag) { return {tag: tag, className: '', textContent: ''}; },
  addEventListener: function (ev, fn) { (listeners[ev] = listeners[ev] || []).push(fn); },
};
var window = {};
%s
window.SECTOR_CYCLES = %s;
(listeners.DOMContentLoaded || []).forEach(function (f) { f(); });
console.log(JSON.stringify({text: asofEl.textContent, html: asofEl.innerHTML}));
""" % (json.dumps(server_text), "\n".join(scripts), json.dumps({"meta": meta} if meta is not None else {}))
    done = subprocess.run(["node", "-e", source], capture_output=True, text=True, timeout=30, check=True)
    return json.loads(done.stdout)


@needs_node
@pytest.mark.parametrize("template", [US, CN])
def test_the_setter_never_blanks_a_server_date(template):
    assert _run_setter(template, "2026-11-03", {})["text"] == "2026-11-03"
    assert _run_setter(template, "2026-11-03", None)["text"] == "2026-11-03"
    assert _run_setter(template, "2026-11-03", {"asOf": ""})["text"] == "2026-11-03"
    assert _run_setter(template, "2026-11-03", {"asOf": "2026-11-04"})["text"] == "2026-11-04"
    still = _run_setter(template, "…", {})
    assert still["html"] == UNAVAILABLE


# ---------------------------------------------------------------- assets, CSS and frozen surfaces

def test_both_builders_ship_the_seam_assets():
    from scripts import build_china_sector_cycles as cn
    from scripts import build_sector_cycles as us
    assert us.PAGE_ASSETS == cn.PAGE_ASSETS
    for asset in ("sector_cycles_states.js", "sector_cycles_states.css", "sector_cycles_face.js",
                  "sector_cycles_compare.js", "sector_cycles_platform.js", "sector_cycles_platform.css"):
        assert asset in us.PAGE_ASSETS, asset
    for asset in us.PAGE_ASSETS:
        assert (TPL / asset).is_file(), asset


@pytest.mark.parametrize("template", [US, CN])
def test_seam_scripts_load_in_contract_order(template):
    text = (TPL / template).read_text(encoding="utf-8")
    order = ["mm_charts.js", "sector_cycles_states.js", "sector_cycles_face.js", "sector_cycles_compare.js",
             "sector_cycles_platform.js", 'src="sector_cycles.js']
    body = text[text.index("</header>"):]
    pos = [body.index(n) for n in order]
    assert pos == sorted(pos), dict(zip(order, pos))
    assert 'href="sector_cycles_states.css"' in text


def test_states_css_uses_tokens_and_no_edge_accent():
    css = STATES_CSS.read_text(encoding="utf-8")
    assert not re.search(r"border-(?:left|right|top|bottom)\s*:", css)
    assert not re.search(r"border-(?:inline|block)(?:-start|-end)?\s*:", css)
    assert not re.search(r"box-shadow\s*:\s*inset", css)
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", css)
    assert "prefers-reduced-motion" in css and ":focus-visible" in css


_CN_MEMBERS_NOTICE = """  {% with lock_renderer='sector_cycles.js', lock_fill='sc-cards',
    lock_hide='#sc-tabs,.cyc-stage,.cyc-cards-hd,#sc-cards,.cyc-asof',
    lock_en='Members get each Shenwan sector and A-share basket '
    ~ 'on the cycle clock, its scorecard, and the typical '
    ~ 'next-turn rhythm.',
    lock_zh='会员可查看每个申万行业与 A 股主题篮子的周期时钟、记分卡，以及典型的下一拐点节奏。' %}
  {% include "_cycle_locked_slot.html.j2" %}
  {% endwith %}
"""


def test_china_members_notice_is_unchanged():
    assert _CN_MEMBERS_NOTICE in (TPL / CN).read_text(encoding="utf-8")


def _base_blob(path):
    base = os.environ.get("SC_WAVE_LOCK_BASE")
    if not base:
        pytest.skip("set SC_WAVE_LOCK_BASE=<base sha> to run the wave-lock evidence check")
    proc = subprocess.run(["git", "show", "%s:%s" % (base, path)], capture_output=True, cwd=str(ROOT))
    if proc.returncode:
        pytest.skip("base object unavailable: %s" % path)
    return proc.stdout


@pytest.mark.parametrize("path", ["scripts/build_country_cycles.py", "templates/country_cycles.html.j2"])
def test_international_cycles_page_is_untouched(path):
    assert (ROOT / path).read_bytes() == _base_blob(path)


def test_us_template_head_is_line_neutral():
    # the head edits replace lines 19, 25 and 45 in place; the first 115 lines keep their count
    base = _base_blob("templates/" + US).decode("utf-8").splitlines()
    now = (TPL / US).read_text(encoding="utf-8").splitlines()
    assert [i + 1 for i in range(115) if base[i] != now[i]] == [19, 25, 45]
    assert now[115:118] == base[115:118]
    assert now[118:122] == ['<script src="sector_cycles_states.js"></script>', '<script src="sector_cycles_face.js"></script>',
                            '<script src="sector_cycles_compare.js"></script>',
                            '<script src="sector_cycles_platform.js"></script>']


@pytest.mark.parametrize("template", [US, CN])
def test_members_notices_are_byte_identical_to_base(template):
    base = _base_blob("templates/" + template).decode("utf-8")
    now = (TPL / template).read_text(encoding="utf-8")
    for block in re.findall(r"\{% with lock_renderer=.*?\{% endwith %\}", base, re.S):
        assert block in now
