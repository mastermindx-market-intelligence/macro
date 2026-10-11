"""Hydration must MERGE the withheld board cards into the groups the shell drew.

THE BUG (reported on the live board 2026-08-20, reproduced against the shipped
site/us_stocks.html + site/premiumdata/us_stocks.json): the US Prophet board
showed "LIVE NOW · 13" twice — once over three cards, then again over ten
different ones — with "Setting up · 38" below both.

Neither side of the tier wall was wrong on its own. Both render from the same
partial (templates/_us_board_cards.html.j2) and each groups ITS OWN rows: the
shell heads the preview slice, the tier payload heads the locked remainder, and
both stamp the TRUE full-board count (build_site._us_board_group_items — that is
deliberate, so a gated shell's heading stays honest while only the preview shows
under it). The defect was purely in how the two were joined:
`grid.insertAdjacentHTML('beforeend', payload.cards_html)` appended the payload's
whole heading-bearing block after the shell's, so

  * every stage present on BOTH sides drew its heading twice, and
  * every withheld group landed after every shell group, so a preview that
    spanned two stages put the withheld "Live now" BELOW "Setting up".

These tests run the SHIPPED merge — sliced out of the rendered page, not
reimplemented — against a stub DOM (tests/us_board_hydrate_harness.js), plus the
markup-contract pins that keep the join key alive on both sides of the wall.

JINJA2-ONLY, deliberately (same discipline as tests/test_us_board_gate.py's own
"import-light where possible" note). Nothing here imports scripts.build_site: the
merge block it slices carries no Jinja and no gate-derived value, so a hand-built
`gate` dict renders the identical bytes, and pulling build_site in would drag
pandas/plotly — and, in a curated `scope: exclusive` CI job, build_site's whole
engine import closure — behind a suite that only needs a template render. If the
gate contract ever moves out from under `_gate()` below, `_merge_source` fails
LOUDLY on the missing block rather than passing over a shell that never rendered
the hydrate script.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SHELL = ROOT / "site" / "us_stocks.html"
PAYLOAD = ROOT / "site" / "premiumdata" / "us_stocks.json"
HARNESS = Path(__file__).with_name("us_board_hydrate_harness.js")
HAS_NODE = shutil.which("node") is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node not on PATH")

STAGE_HD = re.compile(r'<div class="nb-stage-hd[^"]*"[^>]*data-stage="([^"]+)"')

from tests.test_us_board_gate import (  # noqa: E402
    _render_shell, _rows_with_stage, _rows,
)

_STAGE_KEYS = ("live", "setting_up", "ran", "basing", "blocked")
_LANE_KEYS = ("bottoming", "continuation", "trend", "recovery", "watch")
PREVIEW = 3


def _gate(rows: list[dict], preview: int = PREVIEW) -> dict:
    """The `gate` dict the gated shell renders from — the same keys
    build_site._split_us_board emits, built here so this module stays
    jinja2-only (see the module docstring). Only `total`/`preview`/`locked`/
    `stage_counts` are read by the template, and none of them reach the merge
    block these tests slice."""
    counts = {k: 0 for k in _STAGE_KEYS + _LANE_KEYS}
    for r in rows:
        for key in (r.get("stage"), r.get("lane")):
            if key in counts:
                counts[key] += 1
    return {"tier": "essential", "payload": "/premiumdata/us_stocks.json",
            "preview": preview, "locked": len(rows) - preview,
            "total": len(rows), "stage_counts": counts}


def _gated_shell(rows: list[dict]) -> str:
    """The rendered gated shell: preview slice on the page, gate dict beside it."""
    return _render_shell({"buy": rows[:PREVIEW], "eligible": len(rows)}, _gate(rows))


def _merge_source(html: str) -> str:
    """The BOARD_STAGES / groupKey / stageRank / mergeBoardCards block, sliced
    out of a rendered page. Bounded by two markers rather than brace-counted:
    if either moves, this fails loudly instead of silently testing nothing."""
    start = html.find("var BOARD_STAGES")
    end = html.find("function hydrate(payload){", start if start >= 0 else 0)
    assert start >= 0, "rendered shell carries no BOARD_STAGES block"
    assert end > start, "BOARD_STAGES block must sit above hydrate()"
    src = html[start:end]
    for name in ("function groupKey(", "function stageRank(", "function mergeBoardCards("):
        assert name in src, f"{name} missing from the sliced merge block"
    return src


def _run_merge(tmp_path: Path, merge_js: str, shell: str, payload: str) -> dict:
    js = tmp_path / "merge.js"
    js.write_text(merge_js, encoding="utf-8")
    scene = tmp_path / "scene.json"
    scene.write_text(json.dumps({"shell": shell, "payload": payload}), encoding="utf-8")
    proc = subprocess.run(
        ["node", str(HARNESS), str(scene), str(js)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout)


def _grid_inner(html: str) -> str:
    """The board grid's own children, sliced by matching `<div>` depth rather
    than by a `.*?</div>` regex — the grid holds cards full of nested divs, so a
    lazy match stops inside the first card and hands the harness truncated
    markup that parses into phantom top-level nodes."""
    # Candidate and Plan grids now share nbgrid; bind the native candidate id,
    # allowing attribute order/additions without accidentally selecting Plans.
    opening = re.search(r"""<div\b(?=[^>]*\sid=["']us-cand-grid["'])[^>]*>""", html)
    assert opening is not None, "shipped shell has no board grid"
    i = opening.end()
    depth, out_start = 1, i
    for m in re.finditer(r"<div\b|</div>", html[i:]):
        depth += 1 if m.group(0) != "</div>" else -1
        if depth == 0:
            return html[out_start:i + m.start()]
    raise AssertionError("unbalanced <div> in the board grid")



@pytest.mark.parametrize("tag", [
    '<div class="nbgrid" data-showmore-rows="3" id="us-cand-grid">',
    "<div id='us-cand-grid' data-showmore-rows='3' class='nbgrid extra'>",
])
def test_grid_inner_selects_exact_candidate_grid_and_preserves_nested_cards(tag):
    expected = '<div class="nb-stage-hd"><span>Stage</span></div><article><div>nested</div></article>'
    decoy = '<div class="nbgrid" data-showmore-rows="3" id="us-life-grid"><div>Plan decoy</div></div>'
    assert _grid_inner(decoy + tag + expected + '</div><div>after</div>') == expected


def test_grid_inner_refuses_missing_or_incomplete_candidate_grid():
    with pytest.raises(AssertionError, match="no board grid"):
        _grid_inner('<div class="nbgrid" data-showmore-rows="3" id="us-life-grid"></div>')
    with pytest.raises(AssertionError, match="unbalanced"):
        _grid_inner('<div id="us-cand-grid" class="nbgrid"><div>unfinished</div>')


def _hd(stage: str, count: int = 13) -> str:
    return (f'<div class="nb-stage-hd sg-{stage}" data-stage="{stage}">'
            f'<span class="sh-n">{count}</span></div>')


def _card(ticker: str, stage: str = "live") -> str:
    return (f'<a class="pvcard" data-ticker="{ticker}" data-stage="{stage}">'
            f'<span class="nb-tk">{ticker}</span></a>')


@pytest.fixture(scope="module")
def merge_js() -> str:
    return _merge_source(_gated_shell(_rows_with_stage(7)))


# ── the merge itself (executable, against the shipped source) ───────────────

@needs_node
def test_a_stage_on_both_sides_of_the_wall_keeps_one_heading(tmp_path, merge_js):
    """THE REPORTED BUG. The shell's "Live now" and the payload's "Live now" are
    one group: one heading, preview names first, withheld names after."""
    out = _run_merge(
        tmp_path, merge_js,
        shell=_hd("live") + _card("BIIB") + _card("JNJ") + _card("TRGP"),
        payload=_hd("live") + _card("HWM") + _card("GNW")
                + _hd("setting_up", 38) + _card("ANDE", "setting_up"),
    )
    assert [g["key"] for g in out["groups"]] == ["stage:live", "stage:setting_up"]
    assert out["groups"][0]["tickers"] == ["BIIB", "JNJ", "TRGP", "HWM", "GNW"]
    assert out["groups"][1]["tickers"] == ["ANDE"]
    assert out["headings"] == 2, "a stage may never draw two headings"


@needs_node
def test_withheld_group_is_placed_by_stage_rank_not_appended(tmp_path, merge_js):
    """The ordering half of the same defect: a preview holding only a LATE stage
    must not push the withheld earlier stages underneath it."""
    out = _run_merge(
        tmp_path, merge_js,
        shell=_hd("blocked", 5) + _card("SHELL1", "blocked"),
        payload=_hd("live") + _card("HWM")
                + _hd("ran", 5) + _card("WMB", "ran")
                + _hd("blocked", 5) + _card("NNN", "blocked"),
    )
    assert [g["key"] for g in out["groups"]] == [
        "stage:live", "stage:ran", "stage:blocked",
    ], "withheld stages must land at their own rank, not after the shell's"
    # the shell's own card still leads its group
    assert out["groups"][-1]["tickers"] == ["SHELL1", "NNN"]


@needs_node
def test_stages_the_shell_never_drew_arrive_whole_and_in_order(tmp_path, merge_js):
    out = _run_merge(
        tmp_path, merge_js,
        shell=_hd("live") + _card("BIIB"),
        payload=_hd("setting_up", 38) + _card("ANDE", "setting_up")
                + _hd("basing", 2) + _card("IART", "basing")
                + _hd("blocked", 5) + _card("NNN", "blocked"),
    )
    assert [g["key"] for g in out["groups"]] == [
        "stage:live", "stage:setting_up", "stage:basing", "stage:blocked",
    ]
    assert out["cards"] == 4


@needs_node
def test_an_empty_payload_changes_nothing(tmp_path, merge_js):
    """Ungated builds ship `cards_html: ""` — the merge must be a clean no-op
    rather than an exception that strands hydratePanels' work."""
    shell = _hd("live") + _card("BIIB") + _card("JNJ")
    out = _run_merge(tmp_path, merge_js, shell=shell, payload="")
    assert [g["key"] for g in out["groups"]] == ["stage:live"]
    assert out["groups"][0]["tickers"] == ["BIIB", "JNJ"]


@needs_node
def test_legacy_lane_headings_merge_on_data_lane(tmp_path, merge_js):
    """The legacy `lane` grouping takes the same path — that is what data-lane
    on .nb-lane-hd is for (templates/_us_board_cards.html.j2)."""
    out = _run_merge(
        tmp_path, merge_js,
        shell='<div class="nb-lane-hd" data-lane="bottoming">Bottoming</div>' + _card("SHELL1"),
        payload='<div class="nb-lane-hd" data-lane="bottoming">Bottoming</div>' + _card("P1")
                + '<div class="nb-lane-hd" data-lane="trend">Trend</div>' + _card("P2"),
    )
    assert [g["key"] for g in out["groups"]] == ["lane:bottoming", "lane:trend"]
    assert out["groups"][0]["tickers"] == ["SHELL1", "P1"]


@needs_node
def test_a_keyless_heading_degrades_to_appending_not_to_collapsing(tmp_path, merge_js):
    """A payload cached from before data-lane shipped has lane headings with no
    join key. That must degrade to the OLD append behaviour (a repeated heading,
    visible but harmless) — never to merging two different lanes into one."""
    out = _run_merge(
        tmp_path, merge_js,
        shell='<div class="nb-lane-hd">Bottoming</div>' + _card("SHELL1"),
        payload='<div class="nb-lane-hd">Bottoming</div>' + _card("P1")
                + '<div class="nb-lane-hd">Trend</div>' + _card("P2"),
    )
    assert out["cards"] == 3, "no card may be dropped by the fallback"
    assert out["headings"] == 3, "keyless headings append; they must not be joined"


# ── the markup contract the merge joins on ─────────────────────────────────

def test_the_shell_no_longer_blind_appends_the_payload_block():
    html = _gated_shell(_rows_with_stage(7))
    assert "mergeBoardCards(freshCand, payload.cards_html)" in html
    assert "candGrid.parentNode.insertBefore(freshCand, candGrid)" in html
    assert "candGrid.parentNode.removeChild(candGrid)" in html
    assert "insertAdjacentHTML('beforeend', payload.cards_html)" not in html, (
        "blind-appending the payload block is the defect — it re-draws every "
        "heading the shell already drew"
    )


def test_both_heading_idioms_carry_a_join_key():
    """A heading with no data-stage/data-lane cannot be merged, so the fix
    silently reverts to the bug. Pin the attribute on the partial itself."""
    src = (ROOT / "templates" / "_us_board_cards.html.j2").read_text(encoding="utf-8")
    assert 'class="nb-stage-hd sg-{{ _sk }}" data-stage="{{ _sk }}"' in src
    assert 'class="nb-lane-hd" data-lane="{{ n.lane }}"' in src


def test_the_lane_path_still_renders_its_heading_label():
    """data-lane is additive: the legacy heading must keep its bilingual label
    and count, or the attribute traded a duplicate heading for a blank one."""
    html = _gated_shell(_rows(7))
    m = re.search(r'<div class="nb-lane-hd" data-lane="(\w+)"[^>]*>(.*?)</div>', html, re.S)
    assert m, "lane heading missing or lost its data-lane"
    assert "l-en" in m.group(2) and "l-zh" in m.group(2) and "·" in m.group(2)


# ── the shipped artifacts ──────────────────────────────────────────────────

def test_the_shipped_pair_really_does_repeat_a_heading():
    """Proof the merge is load-bearing and not guarding a hypothetical: on the
    bytes actually served, at least one stage is headed on BOTH sides of the
    wall — which is exactly what used to render twice."""
    if not SHELL.exists() or not PAYLOAD.exists():
        pytest.skip("us_stocks not yet rebaked in the gated shape")
    payload = json.loads(PAYLOAD.read_text())
    if not payload.get("gated") or not payload.get("cards_html"):
        pytest.skip("board is ungated in this build — nothing to merge")
    shell_stages = set(STAGE_HD.findall(SHELL.read_text(errors="ignore")))
    payload_stages = set(STAGE_HD.findall(payload["cards_html"]))
    assert shell_stages, "gated shell must still head its preview slice"
    assert shell_stages & payload_stages, (
        "the shell and the payload no longer share a stage heading — if the "
        "split changed shape, re-derive what the merge has to join"
    )


@needs_node
def test_the_shipped_pair_merges_to_one_heading_per_stage(tmp_path, merge_js):
    """End-to-end on the served bytes: hydrating the real payload into the real
    shell yields exactly one heading per stage, in stage order, with every
    withheld card present."""
    if not SHELL.exists() or not PAYLOAD.exists():
        pytest.skip("us_stocks not yet rebaked in the gated shape")
    payload = json.loads(PAYLOAD.read_text())
    if not payload.get("gated") or not payload.get("cards_html"):
        pytest.skip("board is ungated in this build — nothing to merge")
    shell_cards = _grid_inner(SHELL.read_text(errors="ignore"))
    out = _run_merge(tmp_path, merge_js, shell=shell_cards, payload=payload["cards_html"])
    keys = [g["key"] for g in out["groups"]]
    assert len(keys) == len(set(keys)), f"a stage drew two headings: {keys}"
    order = ["stage:live", "stage:setting_up", "stage:ran", "stage:basing", "stage:blocked"]
    assert keys == [k for k in order if k in keys], f"stages out of order: {keys}"
    assert out["cards"] == payload["total"], (
        f"{out['cards']} cards on the merged board, payload declares "
        f"{payload['total']} — hydration dropped or duplicated rows"
    )


# Protected loader availability: execute the real promise chain.
"""Execute the actual protected board loader: unavailable is not access denied.

The Node stub models only DOM operations this loader uses. It runs the entire
rendered hydration IIFE, including its real promise chain and payload validation;
neither fetch classification nor hydrate() is replaced by a test implementation.
"""

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser

import pytest

from tests.test_dashboard_template_render import _base_vm, _board_row, _env


class _Tree(HTMLParser):
    """Serialize real rendered markup for the small Node DOM (no HTML package)."""
    def __init__(self, html):
        super().__init__(convert_charrefs=False)
        self.root = {"tag": "document", "attrs": {}, "children": []}
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "children": []}
        self.stack[-1]["children"].append(node)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1]["children"].append({"tag": tag, "attrs": dict(attrs), "children": []})

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1]["children"].append(data)

    def handle_entityref(self, name):
        self.handle_data(f"&{name};")

    def handle_charref(self, name):
        self.handle_data(f"&#{name};")


def _find(tree, identity):
    if isinstance(tree, str):
        return None
    if tree["attrs"].get("id") == identity:
        return tree
    for child in tree["children"]:
        found = _find(child, identity)
        if found is not None:
            return found
    return None


@pytest.fixture(scope="module")
def loader_scene():
    rows = [_board_row(ticker=ticker, featured=True, stage="live", signal_asof="2026-10-08",
                       entry_signal={"status": status, "headline": status})
            for ticker, status in (("MSCI", "buy_soon"), ("ADSK", "partial"), ("ABBV", "buy_now"))]
    vm = _base_vm()
    vm.update(us_standouts={"buy": rows[:2], "eligible": 3, "as_of": "2026-10-08",
                            "ranking": {"featured_count": 3}},
              gate={"payload": "/premiumdata/us_stocks.json", "tier": "essential",
                    "preview": 2, "total": 3, "locked": 1,
                    "stage_counts": {"live": 3}}, pgate=None, life_gate=None)
    env = _env()
    env.autoescape = True
    page = env.get_template("dashboard.html.j2").render(**vm, mode="stocks")
    scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", page, re.S)
    loader = next(js for js in scripts if "var GATE =" in js and "whenAuthSettled()" in js)
    assert "return fetch(SRC," in loader and ".then(hydrate)" in loader
    board = _find(_Tree(re.sub(r"<script\b.*?</script>", "", page, flags=re.S)).root, "us-standouts")
    assert board is not None and _find(board, "us-today") is not None
    assert _find(board, "us-tier-wall") is not None
    cards = env.get_template("_us_board_cards.html.j2").render(
        items=rows, sg_any=True, bs_adj=False, xu_allfeat=False, trg_map={},
        rw_en="", rw_zh="", setup_as_of="2026-10-08")
    return {"loader": loader, "board": board, "fragment_html": cards,
            "fragment": _Tree(cards).root["children"],
            "payload": {"schema": "tier_payload.v1", "page": "us_stocks",
                        "today_cards_html": cards, "today_preview": 3, "today_total": 3,
                        "rows": rows[2:]}}


_NODE = r"""
'use strict';
const fs = require('fs'), vm = require('vm');
const scene = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
let requests = [], merges = [], sessionRefreshes = 0;
function matches(n, selector) {
  if (!n || typeof n === 'string') return false;
  const not = [...selector.matchAll(/:not\(([^)]+)\)/g)].map(m => m[1]);
  selector = selector.replace(/:not\([^)]+\)/g, '');
  if (not.some(s => matches(n, s))) return false;
  const tag = selector.match(/^[a-z][\w-]*/i);
  if (tag && n.tag !== tag[0]) return false;
  for (const m of selector.matchAll(/#([\w-]+)/g)) if (n.attrs.id !== m[1]) return false;
  for (const m of selector.matchAll(/\.([\w-]+)/g))
    if (!(n.attrs.class || '').split(/\s+/).includes(m[1])) return false;
  for (const m of selector.matchAll(/\[([\w-]+)(?:="([^"]*)")?\]/g))
    if (!(m[1] in n.attrs) || (m[2] !== undefined && n.attrs[m[1]] !== m[2])) return false;
  return true;
}
function make(record) {
  if (typeof record === 'string') return record;
  const n = {tag: record.tag, attrs: {...record.attrs}, childNodes: [], parentNode: null};
  n.dataset = new Proxy({}, {
    get: (_, key) => n.attrs['data-' + String(key).replace(/[A-Z]/g, c => '-' + c.toLowerCase())],
    set: (_, key, val) => { n.attrs['data-' + String(key).replace(/[A-Z]/g, c => '-' + c.toLowerCase())] = String(val); return true; }
  });
  n.setAttribute = (key, val) => { n.attrs[key] = String(val); };
  n.getAttribute = key => key in n.attrs ? n.attrs[key] : null;
  n.removeAttribute = key => { delete n.attrs[key]; };
  n.appendChild = c => { if (typeof c !== 'string') { c.parentNode = n; } n.childNodes.push(c); return c; };
  n.removeChild = c => { n.childNodes = n.childNodes.filter(x => x !== c); c.parentNode = null; };
  n.remove = () => { if (n.parentNode) n.parentNode.removeChild(n); };
  n.addEventListener = () => {};
  n.querySelectorAll = selector => {
    const out = [], selectors = selector.split(',').map(s => s.trim().split(/\s+/));
    function walk(parent) {
      for (const c of parent.childNodes) {
        if (typeof c === 'string') continue;
        if (selectors.some(parts => {
          if (!matches(c, parts[parts.length - 1])) return false;
          let a = c.parentNode;
          for (let i = parts.length - 2; i >= 0; i--) {
            while (a && !matches(a, parts[i])) a = a.parentNode;
            if (!a) return false;
            a = a.parentNode;
          }
          return true;
        })) out.push(c);
        walk(c);
      }
    }
    walk(n); return out;
  };
  n.querySelector = s => n.querySelectorAll(s)[0] || null;
  n.classList = {
    contains: c => (n.attrs.class || '').split(/\s+/).includes(c),
    remove: c => { n.attrs.class = (n.attrs.class || '').split(/\s+/).filter(x => x !== c).join(' '); }
  };
  Object.defineProperty(n, 'hidden', {get: () => 'hidden' in n.attrs,
    set: on => { if (on) n.attrs.hidden = ''; else delete n.attrs.hidden; }});
  Object.defineProperty(n, 'textContent', {get: () => n.childNodes.map(c => typeof c === 'string' ? c : c.textContent).join(''),
    set: text => { n.childNodes = [String(text)]; }});
  Object.defineProperty(n, 'innerHTML', {get: () => n.childNodes.map(c => typeof c === 'string' ? c : JSON.stringify(snapshot(c))).join(''),
    set: html => {
      n.childNodes = [];
      if (html === scene.fragment_html) scene.fragment.forEach(c => n.appendChild(make(c)));
      else n.appendChild(String(html));
    }});
  if (n.tag === 'template') n.content = n;
  (record.children || []).forEach(c => n.appendChild(make(c)));
  return n;
}
function snapshot(n) {
  if (!n) return null;
  if (typeof n === 'string') return n;
  return {tag: n.tag, attrs: n.attrs, children: n.childNodes.map(snapshot)};
}
const board = make(scene.board);
board.setAttribute('data-prophet-src', scene.mode);
const document = {
  getElementById: id => board.attrs.id === id ? board : board.querySelector('#' + id),
  querySelector: s => board.querySelector(s), querySelectorAll: s => board.querySelectorAll(s),
  createElement: tag => make({tag, attrs: {}, children: []})
};
const status = () => document.getElementById('us-board-load-status');
const foreign = make({tag: 'p', attrs: {id: 'unrelated-status', role: 'status'}, children: ['Unrelated warning']});
board.appendChild(foreign);
if (scene.previous_error && status()) {
  status().hidden = false; status().dataset.state = 'unavailable';
}
const before = {today: snapshot(document.getElementById('us-today')),
  candidates: snapshot(document.getElementById('us-candidates')),
  date: board.getAttribute('data-board-asof'), foreign: snapshot(foreign)};
const window = {MDXAuth: {user: () => ({id: 'member'}), hasSession: () => true,
  client: () => Promise.resolve({auth: {getSession: () => { sessionRefreshes++; return Promise.resolve({}); }}})},
  USStockTable: {_mergeRows: rows => merges.push(rows)}};
const fetch = (url, options) => {
  requests.push({url, options});
  if (scene.failure === 'network') return Promise.reject(new TypeError('offline'));
  const code = scene.failure === 'http500' ? 500 : Number(scene.failure) || 200;
  return Promise.resolve({ok: code >= 200 && code < 300, status: code,
    json: () => scene.failure === 'bad_json' ? Promise.reject(new SyntaxError('bad JSON')) :
      Promise.resolve(scene.failure === 'invalid_envelope' ? {schema: 'wrong', page: 'us_stocks'} : scene.payload)});
};
vm.runInNewContext(scene.loader, {window, document, fetch, Promise, console, Event: function(){},
  setTimeout: fn => { fn(); return 1; }, location: {href: 'us_stocks.html'}});
setImmediate(() => {
  const s = status();
  let visible = !!s && !s.hidden;
  for (let n = s && s.parentNode; n; n = n.parentNode) {
    if (n.hidden || (n.attrs.id === 'us-today' && scene.mode !== 'today') ||
        (n.attrs.id === 'us-candidates' && scene.mode !== 'candidates') ||
        (n.attrs.id === 'us-plan-block' && scene.mode !== 'plans')) visible = false;
  }
  console.log(JSON.stringify({requests, merges, sessionRefreshes, before,
    after: {today: snapshot(document.getElementById('us-today')),
      candidates: snapshot(document.getElementById('us-candidates')),
      date: board.getAttribute('data-board-asof'), foreign: snapshot(foreign)},
    status: snapshot(s), visible, en: s && (s.querySelector('.l-en') || {}).textContent,
    zh: s && (s.querySelector('.l-zh') || {}).textContent,
    wall: !!document.getElementById('us-tier-wall'),
    todayTickers: document.getElementById('us-today').querySelectorAll('.pvcard[data-ticker]').map(n => n.dataset.ticker)}));
});
"""


def _run(tmp_path, scene, **options):
    node = shutil.which("node")
    assert node, "these promise-chain regressions require Node, as do the existing hydration harnesses"
    data = {**scene, **options}
    (tmp_path / "scene.json").write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "loader.js").write_text(_NODE, encoding="utf-8")
    proc = subprocess.run([node, str(tmp_path / "loader.js"), str(tmp_path / "scene.json")],
                          capture_output=True, text=True, timeout=30, check=False)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = json.loads(proc.stdout)
    assert len(out["requests"]) == 1 and out["sessionRefreshes"] == 1
    assert out["requests"][0] == {"url": "/premiumdata/us_stocks.json",
                                  "options": {"credentials": "same-origin", "cache": "no-store"}}
    return out


@pytest.mark.parametrize("mode", ["today", "candidates"])
@pytest.mark.parametrize("failure", ["network", "http500", "bad_json", "invalid_envelope"])
def test_signed_in_load_failure_discloses_unavailable_and_preserves_preview(tmp_path, loader_scene, mode, failure):
    out = _run(tmp_path, loader_scene, mode=mode, failure=failure)
    assert out["after"] == out["before"], "a failed load must preserve cards/counts/source date and other warnings"
    assert out["wall"] and out["merges"] == []
    assert out["status"] is not None, "the actual loader leaves signed-in failures undisclosed"
    assert out["visible"], "board availability must be visible in Today and Screener"
    assert out["status"]["attrs"].get("role") == "status"
    assert out["status"]["attrs"].get("aria-live") == "polite"
    assert out["status"]["attrs"].get("data-state") == "unavailable"
    assert re.search(r"unavailable|could(?:n.t| not) load|unable to load", out["en"], re.I)
    assert re.search(r"preview|dated", out["en"], re.I) and re.search(r"reload|try again", out["en"], re.I)
    assert re.search(r"不可用|无法加载|未能加载|加载失败", out["zh"])
    assert "预览" in out["zh"] and re.search(r"重试|重新加载|刷新", out["zh"])


@pytest.mark.parametrize("mode", ["today", "candidates"])
@pytest.mark.parametrize("failure", ["401", "403"])
def test_access_denial_preserves_existing_wall_without_claiming_data_outage(tmp_path, loader_scene, mode, failure):
    out = _run(tmp_path, loader_scene, mode=mode, failure=failure)
    assert out["after"] == out["before"]
    assert out["wall"] and out["merges"] == [] and not out["visible"]


@pytest.mark.parametrize("mode", ["today", "candidates"])
def test_success_hydrates_source_rows_and_clears_only_load_error(tmp_path, loader_scene, mode):
    out = _run(tmp_path, loader_scene, mode=mode, failure="success", previous_error=True)
    assert not out["wall"]
    assert out["merges"] == [loader_scene["payload"]["rows"]]
    assert out["todayTickers"] == ["MSCI", "ADSK", "ABBV"]
    assert out["after"]["date"] == out["before"]["date"] == "2026-10-08"
    assert out["after"]["foreign"] == out["before"]["foreign"]
    today_attrs = out["after"]["today"]["attrs"]
    assert today_attrs["data-today-visible"] == today_attrs["data-today-total"] == "3"
    assert out["status"] is not None, "successful hydration must clear the actual load-status slot"
    assert not out["visible"]
    assert out["status"]["attrs"].get("data-state") != "unavailable"
