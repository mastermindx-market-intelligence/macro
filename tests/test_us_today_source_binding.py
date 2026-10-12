"""Today shell/private-payload two-field source binding.

Covers the exact contract shipped by `_us_today_source_binding` plus
dashboard.html.j2's hydrateToday gate:

* the helper accepts only the frozen lowercase 64-hex raw SHA and the
  ORIGINAL owner doc's emit.pair_id (lowercase 32 hex), and never normalizes;
* every field — missing, wrong type, malformed, mismatched — refuses
  independently, in Python and in the REAL production hydrateToday JS;
* the payload and the rendered page carry the same binding, including the
  honest explicit-None unbound shapes;
* a same-count changed/reordered source (different raw SHA or pair) refuses.

The tiny DOM fixture executes the template's actual hydrateToday source under
node; it deliberately does not replace real browser verification.
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

TEMPLATE = ROOT / "templates" / "dashboard.html.j2"
BUILD_SITE = ROOT / "scripts" / "build_site.py"
SHA = "a" * 64
PAIR = "b" * 32
BINDING = {"source_sha256": "sha256:" + SHA, "pair_id": PAIR}


def _helper():
    build_site = pytest.importorskip("scripts.build_site")
    return build_site._us_today_source_binding


# ── helper: exact validation, never normalization ────────────────────────────


def test_valid_pair_exact():
    assert _helper()(SHA, {"emit": {"pair_id": PAIR}}) == BINDING


def test_valid_pair_is_never_normalized():
    f = _helper()
    assert f(SHA.upper(), {"emit": {"pair_id": PAIR}}) is None
    assert f(SHA, {"emit": {"pair_id": PAIR.upper()}}) is None
    assert f(" " + SHA, {"emit": {"pair_id": PAIR}}) is None
    assert f("sha256:" + SHA, {"emit": {"pair_id": PAIR}}) is None


@pytest.mark.parametrize("bad", [None, 123, b"ab", "", "z" * 64, SHA[:-1], SHA + "a"])
def test_bad_raw_sha(bad):
    assert _helper()(bad, {"emit": {"pair_id": PAIR}}) is None


@pytest.mark.parametrize("bad", [None, [], "doc", 7])
def test_bad_owner_doc(bad):
    assert _helper()(SHA, bad) is None


@pytest.mark.parametrize(
    "doc",
    [
        {},
        {"emit": None},
        {"emit": {}},
        {"emit": {"pair_id": None}},
        {"emit": {"pair_id": 123}},
        {"emit": {"pair_id": "b" * 31}},
        {"emit": {"pair_id": "b" * 33}},
        {"emit": {"pair_id": "B" * 32}},
        {"emit": {"pair_id": "g" * 32}},
    ],
)
def test_bad_pair_id(doc):
    assert _helper()(SHA, doc) is None


def test_inputs_never_mutated_and_output_fresh():
    f = _helper()
    doc = {"emit": {"pair_id": PAIR}}
    assert f(SHA, doc) == BINDING
    assert doc == {"emit": {"pair_id": PAIR}}
    out = f(SHA, doc)
    out["pair_id"] = "tampered"
    assert f(SHA, doc) == BINDING


# ── payload mapping: _write_us_payload always writes the exact passed field ──

_GATE = {"gated": True, "tier": "paid", "total": 2, "preview": 1, "locked": 1,
         "stage_counts": {}}


def _write(tmp_path, gate, binding=None):
    build_site = pytest.importorskip("scripts.build_site")
    from tests.test_dashboard_template_render import _env
    kwargs = {} if binding is None else {"today_source_binding": binding}
    build_site._write_us_payload(
        _env(), tmp_path, gate, locked_rows=[], us_standouts={},
        top_setups=None, built="2026-10-12T00:00:00Z", today_rows=[], **kwargs)
    path = tmp_path / build_site.US_PAYLOAD_DIR / build_site.US_PAYLOAD_NAME
    return json.loads(path.read_text(encoding="utf-8"))


def test_payload_carries_exact_binding_gated(tmp_path):
    assert _write(tmp_path, _GATE, BINDING)["today_source_binding"] == BINDING


def test_payload_carries_exact_binding_ungated(tmp_path):
    payload = _write(tmp_path, None, BINDING)
    assert payload["gated"] is False
    assert payload["today_source_binding"] == BINDING


def test_unbound_default_is_explicit_none_not_invented(tmp_path):
    payload = _write(tmp_path, _GATE)
    assert "today_source_binding" in payload
    assert payload["today_source_binding"] is None


# ── page mapping: the shell pins exactly the VM binding, empty when unbound ──


def _render_page(**extra):
    from tests.test_dashboard_template_render import _base_vm, _env
    vm = dict(_base_vm())
    from tests.test_us_board_gate import _rows_with_stage
    rows = _rows_with_stage(9)
    for row in rows:
        row["featured"] = True
    vm.update(us_standouts={"buy": rows, "ranking": {"featured_count": 9}})
    vm.update(extra)
    return _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")


def _today_tag(html):
    assert 'id="us-today"' in html
    return re.search(r'<section class="mx-sec" id="us-today"[^>]*>', html).group(0)


def test_page_pins_match_payload_binding():
    tag = _today_tag(_render_page(us_today_source_binding=BINDING))
    assert f'data-today-source-sha256="{BINDING["source_sha256"]}"' in tag
    assert f'data-today-pair-id="{PAIR}"' in tag


def test_page_pins_empty_when_unbound():
    tag = _today_tag(_render_page(us_today_source_binding=None))
    assert 'data-today-source-sha256=""' in tag
    assert 'data-today-pair-id=""' in tag


# ── build wiring: first/fresh order and both writes threaded ─────────────────


def test_initial_binding_before_display_attach():
    src = BUILD_SITE.read_text(encoding="utf-8")
    assert src.index(
        "_us_today_source_binding(_us_w3c_binding, us_standouts)"
    ) < src.index("us_standouts = _attach_board_display_chips(site, us_standouts)")


def test_fresh_binding_before_fresh_attach_and_before_second_write():
    src = BUILD_SITE.read_text(encoding="utf-8")
    assert src.index("_fresh_today_binding = _us_today_source_binding(") < src.index(
        "_fresh_su = _attach_board_display_chips(site, _fresh_owner_doc)")
    assert src.index(
        'vm["us_today_source_binding"] = _fresh_today_binding') < src.index(
        "today_rows=_us_today_featured2")


def test_both_payload_writes_thread_the_vm_binding():
    src = BUILD_SITE.read_text(encoding="utf-8")
    assert src.count('today_source_binding=vm.get("us_today_source_binding")') == 2


# ── real production hydrateToday under node ──────────────────────────────────

_PRELUDE = """
var SHELL = __SHELL__;
function el(tag){return{tag:tag,attrs:{},className:'',innerHTML:'',removed:false,
 getAttribute:function(n){return (n in this.attrs)?this.attrs[n]:null;},
 setAttribute:function(n,v){this.attrs[n]=String(v);},
 querySelector:function(){return null;},querySelectorAll:function(){return [];},
 remove:function(){this.removed=true;},insertAdjacentElement:function(){},
 appendChild:function(){}};}
var _grid=el('div'),_totalBox=el('span'),_empty=el('p'),_root=el('section');
for (var k in SHELL) _root.attrs[k]=SHELL[k];
_root.querySelector=function(sel){
  if(sel==='#us-today-grid')return _grid;
  if(sel==='.mx-sec-total')return _totalBox;
  if(sel==='.us-today-remainder')return null;
  return null;};
_root.querySelectorAll=function(){return [_empty];};
var _parsed={'.pvcard':[],'.pvcard[data-ticker]':[]};
function parseCards(html){
  var tagRe=/<(?:a|article)\\b[^>]*>/g,m;
  _parsed={'.pvcard':[],'.pvcard[data-ticker]':[]};
  while((m=tagRe.exec(html))!==null){
    var t=m[0];
    if(/class="[^"]*\\bpvcard\\b/.test(t)){
      var tk=/data-ticker="([^"]*)"/.exec(t);
      var e=el('a');e.attrs['data-ticker']=tk?tk[1]:null;
      _parsed['.pvcard'].push(e);
      if(tk!==null)_parsed['.pvcard[data-ticker]'].push(e);
    }
  }
  tagRe.lastIndex=0;
}
globalThis.document={
  getElementById:function(id){return id==='us-today'?_root:null;},
  createElement:function(tag){
    if(tag==='template'){
      return {set innerHTML(h){parseCards(h);},
              get content(){var p=_parsed;return{querySelectorAll:function(sel){
                return p[sel]||[];}};}};}
    return el(tag);
  }
};
"""

_SNAPSHOT = """
_out={gridHtml:_grid.innerHTML||null,
      visible:_root.attrs['data-today-visible']||null,
      total:_root.attrs['data-today-total']||null,
      totalBox:_totalBox.innerHTML||null,
      emptyRemoved:_empty.removed,
      gridChildren:(_grid.innerHTML.match(/class="[^"]*pvcard/g)||[]).length};
console.log(JSON.stringify(_out));
"""


def _function_source(text: str, name: str) -> str:
    match = re.search(
        rf"  function {re.escape(name)}\b.*?(?=\n  function |\n  if \(document\.readyState)",
        text, re.S)
    assert match, f"{name}() missing"
    return match.group(0)


def _run_hydrate_today(html, preview, total, binding, shell=None):
    node = shutil.which("node")
    assert node, "node is required for the Today source-binding gate"
    prelude = _PRELUDE.replace("__SHELL__", json.dumps(shell or {}))
    program = "hydrateToday({}, {}, {}, {});\n{}".format(
        json.dumps(html), json.dumps(preview), json.dumps(total),
        json.dumps(binding), _SNAPSHOT)
    harness = (prelude
               + _function_source(TEMPLATE.read_text(encoding="utf-8"), "hydrateToday")
               + program)
    run = subprocess.run([node, "-e", harness], capture_output=True, text=True,
                         timeout=30, check=False)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def _cards(*tickers):
    return "".join(
        '<a class="pvcard" data-ticker="{}" href="#">{}</a>'.format(t, t)
        for t in tickers)


_SHELL_OK = {"data-today-source-sha256": BINDING["source_sha256"],
             "data-today-pair-id": PAIR}


def test_matching_source_hydrates():
    out = _run_hydrate_today(_cards("AAA", "BBB", "CCC"), 3, 3, BINDING, _SHELL_OK)
    assert out["gridChildren"] == 3
    assert out["visible"] == "3" and out["total"] == "3"
    assert out["emptyRemoved"] is True and "AAA" in out["gridHtml"]


def test_same_count_changed_source_refuses():
    # identical counts, different raw source: the whole point of the gate
    out = _run_hydrate_today(
        _cards("AAA", "BBB", "CCC"), 3, 3, BINDING,
        {"data-today-source-sha256": "sha256:" + "c" * 64,
         "data-today-pair-id": PAIR})
    assert out["gridHtml"] is None and out["gridChildren"] == 0
    out = _run_hydrate_today(
        _cards("AAA", "BBB", "CCC"), 3, 3, BINDING,
        {"data-today-source-sha256": BINDING["source_sha256"],
         "data-today-pair-id": "d" * 32})
    assert out["gridHtml"] is None and out["gridChildren"] == 0


@pytest.mark.parametrize(
    "binding",
    [
        None,
        "binding",
        [],
        {},
        {"source_sha256": "sha256:" + SHA},
        {"pair_id": PAIR},
        {"source_sha256": 5, "pair_id": PAIR},
        {"source_sha256": "sha256:" + SHA, "pair_id": 9},
        {"source_sha256": "sha256:" + SHA.upper(), "pair_id": PAIR},
        {"source_sha256": "SHA256:" + SHA, "pair_id": PAIR},
        {"source_sha256": "sha256:" + SHA[:-1], "pair_id": PAIR},
        {"source_sha256": "sha256:" + SHA + "0", "pair_id": PAIR},
        {"source_sha256": "sha256:" + SHA, "pair_id": PAIR.upper()},
        {"source_sha256": "sha256:" + SHA, "pair_id": PAIR + "0"},
    ],
)
def test_each_bad_binding_field_refuses_independently(binding):
    out = _run_hydrate_today(_cards("AAA", "BBB", "CCC"), 3, 3, binding, _SHELL_OK)
    assert out["gridHtml"] is None and out["visible"] is None
    assert out["emptyRemoved"] is False


def test_unavailable_shell_pins_refuse_valid_binding():
    out = _run_hydrate_today(_cards("AAA", "BBB", "CCC"), 3, 3, BINDING, {})
    assert out["gridHtml"] is None and out["gridChildren"] == 0


def test_incomplete_or_extra_or_blank_cards_refuse_entirely():
    base = {"data-today-source-sha256": BINDING["source_sha256"],
            "data-today-pair-id": PAIR}
    # fewer cards than preview
    out = _run_hydrate_today(_cards("AAA", "BBB"), 3, 3, BINDING, base)
    assert out["gridHtml"] is None
    # a second malformed pvcard cannot hide outside the selected-card query
    out = _run_hydrate_today(
        _cards("AAA", "BBB", "CCC") + '<a class="pvcard" href="#">X</a>',
        4, 4, BINDING, base)
    assert out["gridHtml"] is None
    out = _run_hydrate_today(
        _cards("AAA", "BBB", "CCC") + '<a class="pvcard" href="#">X</a>',
        3, 3, BINDING, base)
    assert out["gridHtml"] is None
    # blank ticker attribute present but empty
    out = _run_hydrate_today(
        _cards("AAA", "BBB") + '<a class="pvcard" data-ticker="" href="#">Z</a>',
        3, 3, BINDING, base)
    assert out["gridHtml"] is None


def test_duplicate_valid_tickers_permitted_never_collapsed():
    out = _run_hydrate_today(_cards("AAA", "AAA"), 2, 3, BINDING, _SHELL_OK)
    assert out["gridChildren"] == 2
    assert out["visible"] == "2" and out["total"] == "3"


def test_hydrate_panels_passes_payload_binding_as_fourth_arg():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert re.search(
        r"hydrateToday\(\s*payload\.today_cards_html,\s*payload\.today_preview,\s*"
        r"payload\.today_total,\s*payload\.today_source_binding\s*\)", text), (
        "hydratePanels must pass payload.today_source_binding as the 4th arg")


@pytest.mark.parametrize("html", [['<a class="pvcard" data-ticker="AAA">AAA</a>'], {"cards": "AAA"}, 42])
def test_nonstring_card_payload_refuses(html):
    out = _run_hydrate_today(html, 1, 1, BINDING, _SHELL_OK)
    assert out["gridHtml"] is None and out["visible"] is None
