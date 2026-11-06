"""Sector dossier binder (templates/sector_dossier.js, sc-dossier.v1): tabs, Cycle/Evidence/Record mounts, C17/C21 states.

The binder's renderers are pure string functions over the sector_cycles.json payload, so every case runs them in a bare
node vm sandbox (no DOM, no fetch, no clock) beside the consumed SC_STATES / SC_FACE modules, against the frozen
example dataset. FIXTURE: the breadth cases add synthetic member legs and a pinned meta.today to a deep copy of that
dataset; they are labelled test data, never shipped. The page shell (tablist, members table, CSS, script order) is
checked by partial Jinja renders of templates/sector.html.j2.
"""
from __future__ import annotations

import copy
import html as htmllib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "templates"
DOSSIER = TPL / "sector_dossier.js"
STATES_JS = TPL / "sector_cycles_states.js"
FACE = TPL / "sector_cycles_face.js"
PAGE = TPL / "sector.html.j2"
BUILD = ROOT / "scripts" / "build_site.py"  # ci-trigger-closure: data — parse-only builder source, declared in sector-cycles-wave paths; imports not followed
REF = ROOT / "design_refs" / "sector-paper-20261021"
DS = REF / "cycles_repair" / "example_dataset.json"
DECK_JSON = REF / "copy_deck.json"
ZHGREP = REF / "components" / "zh_latin_grep.py"
ALLOW = REF / "brief_repair" / "zh_face_latin_allow.txt"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is required to run the sector dossier binder")

FULL = (STATES_JS, FACE, DOSSIER)
SPDR = ["xlb", "xlc", "xle", "xlf", "xli", "xlk", "xlp", "xlre", "xlu", "xlv", "xly"]
TABS = ["overview", "cycle", "signals", "drivers", "companies", "evidence", "record"]

_RUNNER = r"""
const fs = require('fs'), vm = require('vm');
const sb = {}; sb.window = sb; vm.createContext(sb);
for (const f of process.argv.slice(1)) vm.runInContext(fs.readFileSync(f, 'utf8'), sb, { filename: f });
const NS = { D: sb.SC_DOSSIER, S: sb.SC_STATES, F: sb.SC_FACE };
const calls = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = calls.map(function (c) {
  try {
    const o = NS[c[0]];
    if (c[1] === '__keys') return { ok: true, v: Object.keys(o).sort() };
    if (c[1] === '__get') return { ok: true, v: o[c[2][0]] };
    if (c[1] === '__tabFor') {
      const m = c[2][1];
      return { ok: true, v: o.tabFor(c[2][0], m ? function (id) { return m[id] || null; } : null) };
    }
    return { ok: true, v: o[c[1]].apply(null, c[2]) };
  } catch (e) { return { ok: false, err: String(e && e.message || e) }; }
});
process.stdout.write(JSON.stringify(out));
"""

DATA = json.loads(DS.read_text(encoding="utf-8"))
_DECK_RAW = json.loads(DECK_JSON.read_text(encoding="utf-8"))
SECTIONS = _DECK_RAW.get("sections", _DECK_RAW)
PAGE_SRC = PAGE.read_text(encoding="utf-8")

# FIXTURE legs (synthetic): two tier-1 member legs for the fragmented XLK row.
LEGS = [
    {"key": "software", "name_en": "Software (non-AI)", "name_zh": "软件（非AI）", "tier": 1, "ret": 0.098, "vs_etf": 0.15,
     "ratio_z": 1.2},
    {"key": "memory", "name_en": "Memory & storage", "name_zh": "存储芯片", "tier": 1, "ret": -0.233, "vs_etf": -0.18,
     "ratio_z": -1.87},
]


def _run(calls, files=FULL):
    proc = subprocess.run(["node", "-e", _RUNNER, *map(str, files)], input=json.dumps(calls), capture_output=True,
                          text=True, cwd=str(ROOT))
    assert proc.returncode == 0, proc.stderr[-2000:]
    res = json.loads(proc.stdout)
    assert len(res) == len(calls)
    for c, r in zip(calls, res):
        assert r["ok"], (c[0], c[1], r.get("err"))
    return [r["v"] for r in res]


def _one(ns, fn, *args, files=FULL):
    return _run([[ns, fn, list(args)]], files)[0]


def fixture():
    """FIXTURE: deep copy of the frozen example dataset + pinned today + aligned fragmentation rows with legs."""
    p = copy.deepcopy(DATA)
    p["_fixture"] = "FIXTURE tests/test_sector_dossier_cycle.py: synthetic legs and meta.today"
    p["meta"]["today"] = 2026.80
    rc = p["rotation_context"]
    rows = copy.deepcopy(rc["fragmentation_xlk"])
    assert isinstance(rows, list) and rows and rows[0]["key"] == "xlk"
    rows[0]["legs"] = copy.deepcopy(LEGS)
    rc["fragmentation"]["sectors"] = rows
    return p


def deck(key):
    sec, k = key.split(".", 1)
    e = SECTIONS[sec][k]
    return [e["en"], e["zh"]]


def visible(html):
    """Face text with disclosure drawers removed (drawers carry method text, not the face)."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<details[\s\S]*?</details>", "", html)))


def _xlk_row(p):
    return p["rotation_context"]["fragmentation"]["sectors"][0]


# ---------------------------------------------------------------- module surface and copy trace

def test_module_surface():
    keys, version, tabs = _run([["D", "__keys", []], ["D", "__get", ["version"]], ["D", "__get", ["TABS"]]])
    for k in ("DECK", "PAIRS", "breadth", "renderCycle", "renderSignals", "renderDrivers", "renderEvidence",
              "renderRecord", "renderFetchState", "unavailableComposite", "centralHref", "tabFor", "bind"):
        assert k in keys, k
    assert version == "sc-dossier.v1"
    assert tabs == TABS


def test_deck_table_mirrors_copy_deck():
    table = _one("D", "__get", "DECK")
    assert "components.provenance_label" in table and "dossier.record_h2" in table
    for key, pair in table.items():
        assert pair == deck(key), key


def test_pairs_trace_to_cited_templates():
    pairs, table = _run([["D", "__get", ["PAIRS"]], ["D", "__get", ["DECK"]]])
    assert set(pairs) >= {"tab." + t for t in TABS if t != "record"}
    for key, (en, zh, cite) in pairs.items():
        path, _, line = cite.rpartition(":")
        src = ROOT / path
        assert src.is_file() and line.isdigit(), (key, cite)
        text = src.read_text(encoding="utf-8")
        assert en in text and zh in text, (key, cite)
        assert key not in table, key


# ---------------------------------------------------------------- Cycle tab

def test_cycle_tab_renders_face_and_central_link():
    p = fixture()
    en, zh = _run([["D", "renderCycle", [p, "XLK", "en"]], ["D", "renderCycle", [p, "xlk", "zh"]]])
    for h in (en, zh):
        assert 'class="scd-cycle" data-sector="xlk"' in h
        assert 'href="../sector_central.html#cycles/s=XLK"' in h
        assert "scd-breadth-sec" in h
    lbl = deck("cycles.fragmentation_chip")
    assert 'aria-label="' + lbl[0] + '"' in en and 'aria-label="' + lbl[1] + '"' in zh
    for h in (en, zh):
        i_sec, i_trend, i_breadth = h.index("scd-breadth-sec"), h.index('class="scd-trend"'), h.index('class="scd-breadth"')
        assert i_sec < i_trend < i_breadth


def test_cycle_tab_has_no_null_tokens_on_the_face():
    p = fixture()
    calls = [["D", "renderCycle", [p, sid, lang]] for sid in ("xlk", "xlf", "xlc") for lang in ("en", "zh")]
    for h in _run(calls):
        assert not re.search(r"\b(null|undefined|NaN)\b", visible(h)), visible(h)[:400]


def test_cycle_tab_unknown_sector_is_invalid_subject():
    h = _one("D", "renderCycle", fixture(), "XLB", "en")
    assert 'data-state="invalid_subject" data-subject="XLB"' in h
    assert "scd-cycle" not in h
    assert deck("dossier.invalid_subject_state")[0] in h


def test_cycle_tab_without_face_modules_is_a_constant_composite():
    h = _one("D", "renderCycle", fixture(), "XLK", "en", files=(DOSSIER,))
    assert 'data-state="unavailable"' in h and "scd-cycle" not in h
    assert deck("states.error_title")[0] in h and deck("states.error_body")[0] in h
    assert _one("D", "renderRecord", fixture(), "XLK", "en", files=(DOSSIER,)) == h


# ---------------------------------------------------------------- C17: the ETF's own 200d trend gate

def test_etf_trend_gate_true_false_unknown():
    p = fixture()
    q = copy.deepcopy(p)
    for s in q["sectors"]:
        if s["id"] == "xlf":
            del s["now"]["above200d"]
    xlf, xlc, unk = _run([["D", "renderCycle", [p, "xlf", "en"]], ["D", "renderCycle", [p, "xlc", "en"]],
                          ["D", "renderCycle", [q, "xlf", "en"]]])
    assert 'data-above200d="true"' in xlf
    assert 'data-above200d="false"' in xlc
    assert 'data-above200d="unknown"' in unk and 'data-above200d="true"' not in unk



def test_strong_leader_failing_the_gate_states_both_and_never_sizes():
    """A leader below its 200d keeps leadership on screen, says the gate failed, and offers no size."""
    q = fixture()
    for s in q["sectors"]:
        if s["id"] == "xlk":
            s["now"]["above200d"] = False
    en, zh = _run([["D", "renderCycle", [q, "xlk", "en"]], ["D", "renderCycle", [q, "xlk", "zh"]]])
    # The only sizing words allowed are the two deck disclaimers that say there is no size.
    inert = deck("cycles.sizing_inert") + deck("brief.lanes_disclaimer")
    for h in (en, zh):
        assert 'data-row="leadership"' in h
        assert 'data-above200d="false"' in h and 'data-above200d="true"' not in h
        t = visible(h)
        assert "Below" in t and "下方" in t
        rest = t
        for line in inert:
            assert line in t
            rest = rest.replace(line, "")
        assert not re.search(r"(?i)\bsiz(e|ing)\b|multiplier|size_mult", rest), rest[:400]
        assert "仓位" not in rest

# ---------------------------------------------------------------- C21: member breadth states

def test_breadth_fragmented_row_renders_chip_copy_and_legs():
    p = fixture()
    h = _one("D", "breadth", p, "XLK")
    assert 'data-fragmented="true"' in h and "sc-chip--warn" in h
    assert h.count('class="scd-leg"') == 2
    assert 'data-leg="software"' in h and 'data-leg="memory"' in h
    assert "+9.8%" in h and "-23.3%" in h
    row = _xlk_row(p)
    assert "scd-breadth-copy" in h
    assert htmllib.escape(row["copy_en"], quote=True) in h and htmllib.escape(row["copy_zh"], quote=True) in h
    assert "& " not in h  # copy is escaped, never raw markup
    assert "2026-10-20" in h


def test_breadth_unfragmented_row_makes_no_chip():
    p = fixture()
    _xlk_row(p)["fragmented"] = False
    h = _one("D", "breadth", p, "xlk")
    assert 'data-fragmented="false"' in h and "sc-chip--warn" not in h
    assert h.count('class="scd-leg"') == 2


def test_breadth_absent_row_is_not_covered():
    h = _one("D", "breadth", fixture(), "XLF")
    assert 'data-state="not_covered"' in h and "scd-leg" not in h


@pytest.mark.parametrize("legs", [[], None, [{"name_en": "keyless"}]])
def test_breadth_row_without_legs_is_unavailable(legs):
    p = fixture()
    if legs is None:
        del _xlk_row(p)["legs"]
    else:
        _xlk_row(p)["legs"] = legs
    h = _one("D", "breadth", p, "XLK")
    assert 'data-state="unavailable"' in h
    assert 'class="scd-breadth"' not in h and "sc-chip--warn" not in h


@pytest.mark.parametrize("status,state", [("missing_input", "unavailable"), ("invalid_payload", "malformed")])
def test_breadth_non_aligned_fragmentation_is_typed(status, state):
    p = fixture()
    p["rotation_context"]["fragmentation"]["status"] = status
    h = _one("D", "breadth", p, "XLK")
    assert 'data-state="' + state + '"' in h and "scd-leg" not in h


def test_breadth_without_context_or_rows_is_typed():
    p = fixture()
    bare = copy.deepcopy(p)
    bare["rotation_context"] = {"schema": p["rotation_context"].get("schema")}
    gone = copy.deepcopy(p)
    del gone["rotation_context"]
    bad = copy.deepcopy(p)
    bad["rotation_context"]["fragmentation"]["sectors"] = {"xlk": _xlk_row(p)}
    a, b, c = _run([["D", "breadth", [bare, "XLK"]], ["D", "breadth", [gone, "XLK"]], ["D", "breadth", [bad, "XLK"]]])
    assert 'data-state="unavailable"' in a and 'data-state="unavailable"' in b
    assert 'data-state="malformed"' in c
    for h in (a, b, c):
        assert "scd-leg" not in h


# ---------------------------------------------------------------- Evidence tab

def test_evidence_coverage_fresh_partial_unavailable():
    full = fixture()
    full["sectors"] = [{"id": x} for x in SPDR]
    part = fixture()
    none = fixture()
    del none["sectors"]
    f, pt, n = _run([["D", "renderEvidence", [full, "en"]], ["D", "renderEvidence", [part, "en"]],
                     ["D", "renderEvidence", [none, "en"]]])
    assert 'data-coverage="fresh"' in f and "11/11" in f and 'data-state="partial"' not in f
    assert 'data-coverage="partial"' in pt and "3/11" in pt and 'data-state="partial"' in pt
    assert 'data-coverage="unavailable"' in n and "/11" not in n and "0/" not in n


def test_evidence_freshness_and_recon_disclosure():
    p = fixture()
    q = copy.deepcopy(p)
    del q["meta"]["asOf"]
    h, missing = _run([["D", "renderEvidence", [p, "en"]], ["D", "renderEvidence", [q, "en"]]])
    assert '<div data-fact="freshness">' in h and p["meta"]["asOf"] in h
    fresh = missing.split('data-fact="coverage"')[0]
    assert "sc-state--compact" in fresh and 'data-state="unavailable"' in fresh
    drawer = re.search(r'<details class="scf scf-prov cyc-prov scd-note">[\s\S]*?</details>', h)
    assert drawer, h
    body = deck("dossier.recon_body")
    assert body[0] in drawer.group(0) and body[1] in drawer.group(0)
    outside = h.replace(drawer.group(0), "")
    assert body[0] not in outside and body[1] not in outside


# ---------------------------------------------------------------- Record, fetch states, producerless tabs

def test_record_tab_is_methods_plus_central_link():
    p = fixture()
    h, methods = _run([["D", "renderRecord", [p, "XLK", "en"]],
                       ["F", "methods", [p["meta"], {"today": p["meta"]["today"], "meta": p["meta"],
                                                    "asof": p["meta"]["asOf"], "fixture": False, "lang": "en"}]]])
    assert h.startswith(methods)
    assert 'href="../sector_central.html#cycles/s=XLK"' in h and deck("dossier.open_central_link")[0] in h


@pytest.mark.parametrize("state", ["unauthorized", "forbidden", "not_found", "offline", "malformed",
                                   "incompatible_generation", "unavailable"])
def test_fetch_failure_states_are_typed(state):
    h = _one("D", "renderFetchState", {"state": state, "reason": "test"})
    assert 'data-state="' + state + '"' in h and 'role="status"' in h


def test_fetch_state_without_result_is_unavailable():
    assert 'data-state="unavailable"' in _one("D", "renderFetchState", None)


def test_producerless_tabs_carry_residuals():
    sig, drv = _run([["D", "renderSignals", []], ["D", "renderDrivers", []]])
    assert 'data-state="unavailable"' in sig and 'data-residual="no-etf-signal-producer"' in sig
    assert deck("components.no_evidence_attached")[0] in sig
    assert 'data-state="unavailable"' in drv and 'data-residual="no-sector-driver-producer"' in drv
    assert drv.count('role="status"') == 1


# ---------------------------------------------------------------- hash routing

def test_tab_for_hash_routing():
    calls = [["D", "__tabFor", ["#cycle", None]], ["D", "__tabFor", ["record", None]],
             ["D", "__tabFor", ["#bogus", None]], ["D", "__tabFor", ["", None]],
             ["D", "__tabFor", ["#sc-holdings", {"sc-holdings": "companies"}]],
             ["D", "__tabFor", ["#nowhere", {"sc-holdings": "companies"}]]]
    cyc, rec, bogus, empty, hit, miss = _run(calls)
    assert cyc == {"tab": "cycle", "target": None} and rec == {"tab": "record", "target": None}
    assert bogus == empty == miss == {"tab": "overview", "target": None}
    assert hit == {"tab": "companies", "target": "sc-holdings"}


# ---------------------------------------------------------------- page shell (partial Jinja renders)

def _macros():
    macros, sep, _rest = PAGE_SRC.partition("<!DOCTYPE")
    assert sep, "sector.html.j2 lost its <!DOCTYPE separator"
    return macros


def _render(block, **ctx):
    jinja2 = pytest.importorskip("jinja2")
    return jinja2.Environment(autoescape=False).from_string(_macros() + block).render(**ctx)


def _labels():
    vals = {tuple(v) for v in _one("D", "__get", "DECK").values()}
    vals |= {tuple(v[:2]) for v in _one("D", "__get", "PAIRS").values()}
    return vals


def test_tablist_is_complete_and_wai_aria_shaped():
    start = PAGE_SRC.index('<div class="scd-tabs"')
    block = PAGE_SRC[start:PAGE_SRC.index("</div>", start) + len("</div>")]
    html = _render(block, s={"fund": "XLK"})
    tabs = re.findall(r"<button ([^>]*)>(.*?)</button>", html)
    assert len(tabs) == 7
    ids = [re.search(r'data-tab="(\w+)"', a).group(1) for a, _ in tabs]
    assert ids == TABS
    selected = [a for a, _ in tabs if 'aria-selected="true"' in a]
    assert len(selected) == 1 and 'tabindex="0"' in selected[0] and 'data-tab="overview"' in selected[0]
    labels = _labels()
    for attrs, body in tabs:
        assert 'role="tab"' in attrs
        t = re.search(r'data-tab="(\w+)"', attrs).group(1)
        assert 'id="scd-t-' + t + '"' in attrs and 'aria-controls="scd-p-' + t + '"' in attrs
        if 'aria-selected="false"' in attrs:
            assert 'tabindex="-1"' in attrs
        en = re.search(r'<span class="l-en">(.*?)</span>', body).group(1)
        zh = re.search(r'<span class="l-zh">(.*?)</span>', body).group(1)
        assert (en, zh) in labels, (en, zh)
    assert 'aria-label="XLK"' in html


def test_every_tabpanel_is_labelled_and_visible_without_js():
    panels = re.findall(r'<section role="tabpanel" ([^>]*)>', PAGE_SRC)
    assert len(panels) == 7
    seen = []
    for attrs in panels:
        pid = re.search(r'id="scd-p-(\w+)"', attrs).group(1)
        seen.append(pid)
        assert 'aria-labelledby="scd-t-' + pid + '"' in attrs
        assert 'id="scd-t-' + pid + '"' in PAGE_SRC
        assert "hidden" not in attrs
    assert seen == TABS
    for mount in ("scd-cycle", "scd-signals", "scd-drivers", "scd-evidence", "scd-record-face"):
        assert 'id="' + mount + '"' in PAGE_SRC, mount


def test_members_table_marks_unresolved_tickers():
    start = PAGE_SRC.index("{% if s.members %}")
    block = PAGE_SRC[start:PAGE_SRC.index("{% if s.holdings %}", start)]
    members = [
        {"ticker": "AAPL", "name": "Apple Inc", "weight": 12.34, "resolved": True, "reason": None},
        {"ticker": "NEWCO", "name": "", "weight": None, "resolved": False, "reason": "no_price_history"},
        {"ticker": "THIN", "name": "Thin Co", "weight": 0.5, "resolved": False, "reason": "insufficient_history"},
    ]
    html = _render(block, s={"members": members})
    rows = re.findall(r"<tr data-resolved=\"(\w+)\">([\s\S]*?)</tr>", html)
    assert [r[0] for r in rows] == ["true", "false", "false"]
    assert 'href="../stock.html#AAPL"' in rows[0][1] and "12.3%" in rows[0][1]
    for (_, row), reason in zip(rows[1:], ("no_price_history", "insufficient_history")):
        assert 'aria-disabled="true"' in row and 'data-reason="' + reason + '"' in row and "href=" not in row
        assert "Not covered" in row and "未覆盖" in row
    assert "—" in rows[1][1] and "0.5%" in rows[2][1]
    assert _render(block, s={"members": []}).strip() == ""


# The only two edge declarations the page keeps: the transparent .help hover bridge (no paint)
# and the neutral table row divider.
_EDGE_ALLOW = (
    "  .help:hover::before { content:''; position:absolute; top:100%; left:-30px; right:-30px; height:10px; }",
    "  th,td { text-align:left; padding:4px 8px; border-bottom:1px solid var(--line); }",
)


def test_page_css_has_no_edge_stripes_and_scripts_load_in_order():
    assert PAGE_SRC.count("<style>") == 1
    start = PAGE_SRC.index("<style>")
    css = PAGE_SRC[start:PAGE_SRC.index("</style>", start)]
    for keep in _EDGE_ALLOW:
        assert css.count(keep) == 1, keep
        css = css.replace(keep, "")
    assert not re.search(r"border-(left|right|top|bottom|inline|block)", css), \
        re.findall(r"[^\n]*border-(?:left|right|top|bottom|inline|block)[^\n]*", css)
    assert not re.search(r"border-[a-z-]*-color", css)
    assert "inset" not in css
    assert not re.search(r"::?(before|after)", css)
    order = [PAGE_SRC.index('<script defer src="../' + f + '">') for f in
             ("sector_cycles_states.js", "sector_cycles_face.js", "sector_dossier.js")]
    assert order == sorted(order)


def _companies_block():
    start = PAGE_SRC.index('<section role="tabpanel" id="scd-p-companies"')
    return PAGE_SRC[start:PAGE_SRC.index("</section>", start) + len("</section>")]


def test_companies_without_members_or_holdings_is_not_covered():
    block = _companies_block()
    for s in ({"members": [], "holdings": []}, {}):
        html = _render(block, s=s)
        st = re.findall(r'<div class="sc-state sc-state--unavailable" ([^>]*)>(.*?)</div>', html)
        assert len(st) == 1, html
        attrs, body = st[0]
        assert 'data-state="unavailable"' in attrs and 'data-residual="no-holdings-file"' in attrs
        assert 'role="status"' in attrs
        assert '<span class="l-en">Not covered</span><span class="l-zh">未覆盖</span>' in body
        assert ("Not covered", "未覆盖") in _labels()
    members = [{"ticker": "AAPL", "name": "Apple Inc", "weight": 12.3, "resolved": True, "reason": None}]
    assert "sc-state--unavailable" not in _render(block, s={"members": members, "holdings": []})


_BIND_RUNNER = r"""
const fs = require('fs'), vm = require('vm');
function el(attrs) {
  const a = Object.assign({}, attrs), ls = {};
  return { hidden: false, innerHTML: '', getAttribute: k => (k in a ? a[k] : null),
    setAttribute: (k, v) => { a[k] = String(v); }, addEventListener: (t, f) => { (ls[t] = ls[t] || []).push(f); },
    focus() {}, contains: () => false,
    click() { (ls.click || []).forEach(f => f({ preventDefault() {} })); } };
}
const TABS = JSON.parse(process.argv[2]);
const tabs = TABS.map((t, i) => el({ role: 'tab', 'data-tab': t, 'aria-selected': i ? 'false' : 'true' }));
const shell = el({ 'data-fund': 'xlk' });
shell.querySelectorAll = () => tabs;
const byId = { scd: shell };
TABS.forEach(t => { byId['scd-p-' + t] = el({}); });
const doc = { getElementById: id => byId[id] || null };
const pushes = [];
const sb = { history: { pushState: (s, ti, u) => pushes.push(u) }, location: { hash: '' }, addEventListener() {} };
sb.window = sb; vm.createContext(sb);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sb, { filename: process.argv[1] });
sb.SC_DOSSIER.bind(doc);
const seq = JSON.parse(process.argv[3]);
seq.forEach(t => tabs[TABS.indexOf(t)].click());
process.stdout.write(JSON.stringify({ pushes, selected: tabs.map(b => b.getAttribute('aria-selected')) }));
"""


def test_reclicking_the_current_tab_adds_no_history_entry():
    seq = ["overview", "cycle", "cycle", "cycle", "companies", "companies", "overview"]
    proc = subprocess.run(["node", "-e", _BIND_RUNNER, str(DOSSIER), json.dumps(TABS), json.dumps(seq)],
                          capture_output=True, text=True, cwd=str(ROOT))
    assert proc.returncode == 0, proc.stderr[-2000:]
    out = json.loads(proc.stdout)
    assert out["pushes"] == ["#cycle", "#companies", "#overview"]
    assert out["selected"] == ["true"] + ["false"] * (len(TABS) - 1)


def test_build_site_ships_binder_and_members():
    src = BUILD.read_text(encoding="utf-8")
    assert "site_assets.copy_asset(_asset, _asset_src, site)" in src
    # build_site ships every root script and style the dossier template loads,
    # so no render scope can publish sectors/<F>.html without them.
    tpl = (ROOT / "templates" / "sector.html.j2").read_text(encoding="utf-8")
    for asset in ("sector_dossier.js", "sector_cycles_states.js",
                  "sector_cycles_face.js", "sector_cycles_states.css"):
        assert f'"../{asset}"' in tpl, asset
        assert f'"{asset}"' in src, asset
    assert '"members": members' in src
    assert '"no_price_history"' in src and '"insufficient_history"' in src


# ---------------------------------------------------------------- ZH face

def test_zh_dossier_face_has_no_latin_leak(tmp_path):
    p = fixture()
    calls = [["D", "renderCycle", [p, "xlk", "zh"]], ["D", "renderCycle", [p, "xlf", "zh"]],
             ["D", "renderEvidence", [p, "zh"]], ["D", "renderRecord", [p, "xlk", "zh"]],
             ["D", "renderSignals", []], ["D", "renderDrivers", []], ["D", "breadth", [p, "xlk"]]]
    body = "".join(_run(calls))
    dom = tmp_path / "zh.html"
    dom.write_text('<html lang="zh" data-lang="zh"><body>' + body + "</body></html>", encoding="utf-8")
    proc = subprocess.run(["python3", "-I", str(ZHGREP), str(dom), str(ALLOW)], capture_output=True, text=True)
    assert proc.returncode == 0 and "zh-latin=0" in proc.stdout, proc.stdout[-1500:]


def test_identity_header_sits_above_the_tablist():
    """L6.19: the page title persists across tabs, so the h1 lives in the identity header above the
    tablist and never inside a tabpanel."""
    head = PAGE_SRC.index('<header class="panel scd-head">')
    h1 = PAGE_SRC.index('<h1>')
    end = PAGE_SRC.index('</header>', head)
    tabs = PAGE_SRC.index('<div class="scd-tabs"')
    assert head < h1 < end < tabs
    assert PAGE_SRC.count('<h1>') == 1
    for m in re.finditer(r'<section[^>]*role="tabpanel"', PAGE_SRC):
        close = PAGE_SRC.find('</section>', m.end())
        assert '<h1>' not in PAGE_SRC[m.end():close]
