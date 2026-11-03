"""Today shell/private-payload native three-field source binding.

Covers the exact contract shipped by `_us_today_source_binding` (the legacy
two-field pair, kept for compatibility), the native
`scripts.build_stock_library.today_selection_source_binding` consumer in
`scripts/build_site.py`, and dashboard.html.j2's hydrateToday gate:

* the legacy helper accepts only the frozen lowercase 64-hex raw SHA and the
  ORIGINAL owner doc's emit.pair_id (lowercase 32 hex), and never normalizes;
* the native binding is issued by the REAL owner callable on the EXACT raw
  bytes, in BOTH first and fresh reads, BEFORE any display attachment or tier
  splitting; its ordered metadata rides COPIED rows by original position only;
* every binding field — missing, wrong type, malformed, mismatched, incomplete
  roster — refuses independently, in Python and in the REAL production
  hydrateToday JS, before any parse, DOM mutation or native query;
* the payload and the rendered page carry the same three pins, the complete
  owner roster SIZE and the served rows' own indices/receipts, including the
  honest explicit-None unbound shapes;
* a same-count changed/reordered/re-receipted source or roster refuses.

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
from html import unescape as html_unescape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEMPLATE = ROOT / "templates" / "dashboard.html.j2"
BUILD_SITE = ROOT / "scripts" / "build_site.py"
SHA = "a" * 64
PAIR = "b" * 32
RECEIPT = "sha256:" + "c" * 64
BINDING = {"source_sha256": "sha256:" + SHA, "pair_id": PAIR}


def _helper():
    build_site = pytest.importorskip("scripts.build_site")
    return build_site._us_today_source_binding


# ── legacy two-field helper: exact validation, never normalization ──────────


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


# ── the REAL owner callable: genuine three-field binding on exact bytes ──────


def _owner():
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    from scripts.build_stock_library import today_selection_source_binding

    return today_selection_source_binding


def _source_doc(*, dup=False, featured=(True, False)):
    row = {"ticker": "ALFA", "price": 42.0}
    buy = []
    for i, feat in enumerate(featured):
        if dup:
            # Two byte-identical rows: the same receipt at two positions.
            buy.append({"ticker": "ALFA", "price": 42.0, "featured": True})
        else:
            buy.append({**row, "featured": feat, "ticker": f"ALF{i}"})
    return {"as_of": "2026-10-12", "board_definition": "us_prophet_v3",
            "emit": {"pair_id": "1" * 32, "at_utc": "2026-10-12T18:02:00+00:00"},
            "buy": buy}


def _source_bytes(doc=None):
    return json.dumps(doc if doc is not None else _source_doc(),
                      separators=(",", ":")).encode()


def test_native_binding_is_the_real_owner_callable_output():
    raw = _source_bytes()
    binding = _owner()(raw)
    build_site = pytest.importorskip("scripts.build_site")
    assert build_site._us_today_native_binding(raw) == binding
    assert binding["schema"] == "prophet.today_selection_source_binding/v1"
    assert binding["receipt_kind"] == "EXACT_DISPLAYED_SOURCE"
    assert binding["source_sha256"] == "sha256:" + __import__("hashlib").sha256(raw).hexdigest()
    assert binding["pair_id"] == "1" * 32
    assert binding["market_session"] == "2026-10-12"
    assert [r["selection_index"] for r in binding["ordered_rows"]] == [0, 1]


def test_native_binding_leaves_raw_bytes_and_doc_untouched():
    doc = _source_doc()
    raw = _source_bytes(doc)
    frozen = bytes(raw)
    import copy

    before = copy.deepcopy(doc)
    _owner()(raw)
    assert build_site_native(raw) is not None
    assert raw == frozen
    assert doc == before


def build_site_native(raw):
    build_site = pytest.importorskip("scripts.build_site")
    return build_site._us_today_native_binding(raw)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda doc: doc.update(buy=None),
        lambda doc: doc.update(buy={}),
        lambda doc: doc["buy"].__setitem__(0, "row"),
        lambda doc: doc.update(emit={}),
        lambda doc: doc.update(emit={"pair_id": "1" * 32}),
        lambda doc: doc.update(emit={"pair_id": "1" * 32, "at_utc": "not-a-time"}),
        lambda doc: doc.update(emit={"pair_id": "1" * 32,
                                     "at_utc": "2026-10-12T18:02:00"}),
        lambda doc: doc.update(board_definition=None),
        lambda doc: doc.update(board_definition=""),
        lambda doc: doc.update(as_of="20261012"),
        lambda doc: doc.pop("as_of"),
    ],
)
def test_native_binding_typed_unavailable_on_invalid_source(mutate):
    doc = _source_doc()
    mutate(doc)
    build_site = pytest.importorskip("scripts.build_site")
    assert build_site._us_today_native_binding(_source_bytes(doc)) is None


@pytest.mark.parametrize("bad", [None, "", b"", 123, "json"])
def test_native_binding_typed_unavailable_on_bad_bytes(bad):
    build_site = pytest.importorskip("scripts.build_site")
    if isinstance(bad, str) and bad == "json":
        assert build_site._us_today_native_binding(b"[1, 2,") is None
    else:
        assert build_site._us_today_native_binding(bad) is None


def test_native_binding_unavailable_without_owner_runtime(monkeypatch):
    build_site = pytest.importorskip("scripts.build_site")
    monkeypatch.setitem(sys.modules, "scripts.build_stock_library", None)
    assert build_site._us_today_native_binding(_source_bytes()) is None


def test_native_binding_duplicates_keep_distinct_positions_and_receipts():
    raw = _source_bytes(_source_doc(dup=True))
    binding = build_site_native(raw)
    assert len(binding["ordered_rows"]) == 2
    assert [r["selection_index"] for r in binding["ordered_rows"]] == [0, 1]
    # The same row content is one receipt at two positions; the positions stay
    # distinct and full-buy NON-Featured rows remain represented.
    assert (binding["ordered_rows"][0]["row_receipt"]
            == binding["ordered_rows"][1]["row_receipt"])


# ── positional carry into COPIED presentation rows ───────────────────────────


def test_bind_rows_carry_owner_positions_without_mutating_source():
    build_site = pytest.importorskip("scripts.build_site")
    import copy

    doc = _source_doc()
    raw = _source_bytes(doc)
    before = copy.deepcopy(doc)
    binding = build_site_native(raw)
    bound = build_site._us_today_bind_rows(doc, binding)
    assert doc == before, "the source dict and its rows are never mutated"
    assert bound is not doc
    for position, row in enumerate(bound["buy"]):
        assert row["_today_selection_index"] == position
        assert row["_today_row_receipt"] == binding["ordered_rows"][position]["row_receipt"]
        assert row["ticker"] == doc["buy"][position]["ticker"]


@pytest.mark.parametrize(
    "binding_mutator",
    [
        lambda b: b.update(ordered_rows=None),
        lambda b: b.update(ordered_rows=[]),
        lambda b: b["ordered_rows"].pop(),
        lambda b: b["ordered_rows"].reverse(),
        lambda b: b["ordered_rows"][0].update(selection_index=7),
        lambda b: b["ordered_rows"][0].update(row_receipt=None),
    ],
)
def test_bind_rows_refuse_incomplete_or_reordered_metadata(binding_mutator):
    build_site = pytest.importorskip("scripts.build_site")
    doc = _source_doc()
    binding = build_site_native(_source_bytes(doc))
    binding_mutator(binding)
    assert build_site._us_today_bind_rows(doc, binding) is doc


@pytest.mark.parametrize("board", [None, {}, {"buy": None}, {"buy": []}])
def test_bind_rows_pass_unbound_boards_through(board):
    build_site = pytest.importorskip("scripts.build_site")
    binding = build_site_native(_source_bytes())
    assert build_site._us_today_bind_rows(board, binding) is board


def test_rows_meta_is_positional_and_all_or_nothing():
    build_site = pytest.importorskip("scripts.build_site")
    doc = _source_doc()
    binding = build_site_native(_source_bytes(doc))
    bound = build_site._us_today_bind_rows(doc, binding)
    meta = build_site._us_today_rows_meta(bound["buy"])
    assert meta == [{"selection_index": r["selection_index"],
                     "row_receipt": r["row_receipt"]}
                    for r in binding["ordered_rows"]]
    assert build_site._us_today_rows_meta([{"ticker": "ALFA"}]) == []
    assert build_site._us_today_rows_meta(None) == []
    broken = bound["buy"][:]
    broken[1].pop("_today_row_receipt")
    assert build_site._us_today_rows_meta(broken) == []


# ── payload mapping: _write_us_payload always writes the exact passed field ──

_GATE = {"gated": True, "tier": "paid", "total": 2, "preview": 1, "locked": 1,
         "stage_counts": {}}


def _write(tmp_path, gate, binding=None, today_rows=None):
    build_site = pytest.importorskip("scripts.build_site")
    from tests.test_dashboard_template_render import _env
    kwargs = {}
    if binding is not None:
        kwargs["today_source_binding"] = binding
    if today_rows is not None:
        kwargs["today_rows"] = today_rows
    build_site._write_us_payload(
        _env(), tmp_path, gate, locked_rows=[], us_standouts={},
        top_setups=None, built="2026-10-12T00:00:00Z", **kwargs)
    path = tmp_path / build_site.US_PAYLOAD_DIR / build_site.US_PAYLOAD_NAME
    return json.loads(path.read_text(encoding="utf-8"))


def test_payload_carries_exact_binding_gated(tmp_path):
    binding = build_site_native(_source_bytes())
    payload = _write(tmp_path, _GATE, binding)
    assert payload["today_source_binding"] == binding
    assert payload["today_source_binding"]["selection_receipt"] == binding["selection_receipt"]


def test_payload_carries_exact_binding_ungated(tmp_path):
    binding = build_site_native(_source_bytes())
    payload = _write(tmp_path, None, binding)
    assert payload["gated"] is False
    assert payload["today_source_binding"] == binding


def test_unbound_default_is_explicit_none_not_invented(tmp_path):
    payload = _write(tmp_path, _GATE)
    assert "today_source_binding" in payload
    assert payload["today_source_binding"] is None


def test_payload_today_rows_meta_is_empty_without_bound_rows(tmp_path):
    payload = _write(tmp_path, _GATE)
    assert payload["today_rows_meta"] == []
    payload = _write(tmp_path, None, build_site_native(_source_bytes()))
    assert payload["gated"] is False
    assert payload["today_cards_html"] == ""
    assert payload["today_preview"] == 0 and payload["today_total"] == 0
    # The honest empty remainder still carries real protected metadata.
    assert payload["today_source_binding"]["selection_receipt"].startswith("sha256:")
    assert payload["today_rows_meta"] == []


def test_payload_today_rows_meta_carry_entitled_positions(tmp_path):
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    build_site = pytest.importorskip("scripts.build_site")
    from tests.test_dashboard_template_render import _env
    from tests.test_us_board_gate import _rows_with_stage
    doc = _source_doc(featured=(True, False, True))
    raw = _source_bytes(doc)
    binding = build_site_native(raw)
    rows = []
    for position, src_row in enumerate(doc["buy"]):
        if not src_row["featured"]:
            continue  # today_rows is the Featured shelf only
        rows.append(_rows_with_stage(3)[0] | {
            "ticker": src_row["ticker"], "featured": src_row["featured"],
            "_today_selection_index": position,
            "_today_row_receipt": binding["ordered_rows"][position]["row_receipt"]})
    build_site._write_us_payload(
        _env(), tmp_path, _GATE, locked_rows=[], us_standouts={}, top_setups=None,
        built="t", today_rows=rows, today_source_binding=binding)
    payload = json.loads((tmp_path / build_site.US_PAYLOAD_DIR
                          / build_site.US_PAYLOAD_NAME).read_text(encoding="utf-8"))
    assert payload["today_rows_meta"] == [
        {"selection_index": 0,
         "row_receipt": binding["ordered_rows"][0]["row_receipt"]},
        {"selection_index": 2,
         "row_receipt": binding["ordered_rows"][2]["row_receipt"]},
    ]


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
    binding = build_site_native(_source_bytes())
    tag = _today_tag(_render_page(us_today_source_binding=binding))
    assert f'data-today-source-sha256="{binding["source_sha256"]}"' in tag
    assert f'data-today-pair-id="{binding["pair_id"]}"' in tag
    assert f'data-today-selection-receipt="{binding["selection_receipt"]}"' in tag
    assert f'data-today-roster-size="{len(binding["ordered_rows"])}"' in tag


def test_page_pins_empty_when_unbound():
    tag = _today_tag(_render_page(us_today_source_binding=None))
    assert 'data-today-source-sha256=""' in tag
    assert 'data-today-pair-id=""' in tag
    assert 'data-today-selection-receipt=""' in tag
    assert 'data-today-roster-size="0"' in tag


def test_page_served_rows_carry_owner_positions_and_receipts():
    build_site = pytest.importorskip("scripts.build_site")
    from tests.test_us_board_gate import _rows_with_stage
    doc = _source_doc(featured=(True,) * 9)
    binding = build_site_native(_source_bytes(doc))
    rows = []
    for position, src_row in enumerate(doc["buy"]):
        rows.append(_rows_with_stage(9)[position] | {
            "ticker": src_row["ticker"], "featured": True,
            "_today_selection_index": position,
            "_today_row_receipt": binding["ordered_rows"][position]["row_receipt"]})
    html = _render_page(us_standouts={"buy": rows, "ranking": {"featured_count": 9}},
                        us_today_source_binding=binding)
    tag = _today_tag(html)
    served_attr = re.search(r'data-today-served="([^"]*)"', tag).group(1)
    served = [entry.split("~") for entry in served_attr.split(";")]
    # Shell capacity is three cards: only the SERVED subset ships, never the
    # full hidden roster.
    assert [int(s[0]) for s in served] == [0, 1, 2]
    assert [s[1] for s in served] == [
        binding["ordered_rows"][i]["row_receipt"] for i in (0, 1, 2)]
    assert tag.count("sha256:") == 3 + 1 + 1  # served receipts + pins, no more


def test_page_served_rows_blank_when_board_unbound():
    html = _render_page()
    tag = _today_tag(html)
    served_attr = re.search(r'data-today-served="([^"]*)"', tag).group(1)
    # Unbound visible rows render blank entries the hydration gate refuses.
    assert served_attr == "~;~;~"


# ── build wiring: first/fresh order and both writes threaded ─────────────────


def test_initial_binding_before_display_attach():
    src = BUILD_SITE.read_text(encoding="utf-8")
    assert src.index(
        "_us_today_source_binding(_us_w3c_binding, us_standouts)"
    ) < src.index("_us_today_native_binding(_us_source_bytes)")
    assert src.index("_us_today_native_binding(_us_source_bytes)") < src.index(
        "us_standouts = _us_today_bind_rows(us_standouts, _us_today_native)")
    assert src.index("us_standouts = _us_today_bind_rows(us_standouts, _us_today_native)"
                     ) < src.index("us_standouts = _attach_board_display_chips(site, us_standouts)")


def test_fresh_binding_before_fresh_attach_and_before_second_write():
    src = BUILD_SITE.read_text(encoding="utf-8")
    assert src.index("_fresh_today_binding = _us_today_source_binding(") < src.index(
        "_fresh_today_native = _us_today_native_binding(_fresh_source_bytes)")
    assert src.index("_fresh_today_native = _us_today_native_binding(") < src.index(
        "_fresh_su = _attach_board_display_chips(site, _fresh_owner_doc)")
    assert src.index(
        'vm["us_today_source_binding"] = _fresh_today_binding') < src.index(
        "today_rows=_us_today_featured2")


def test_both_payload_writes_thread_the_vm_binding():
    src = BUILD_SITE.read_text(encoding="utf-8")
    assert src.count('today_source_binding=vm.get("us_today_source_binding")') == 2


def test_both_renders_thread_the_native_emit_and_both_payloads_write_meta():
    src = BUILD_SITE.read_text(encoding="utf-8")
    assert src.count('"us_today_native_emit": _us_today_emit,') == 1
    assert src.count('"us_today_native_emit": _us_today_emit2,') == 1
    assert src.count('"today_rows_meta": _us_today_rows_meta(today_rows)') == 1
    assert src.count('"today_rows_meta": []') == 1


def test_native_emit_requires_genuine_three_field_binding_over_nonempty_shelf():
    build_site = pytest.importorskip("scripts.build_site")
    binding = build_site_native(_source_bytes())
    url = build_site.US_PAYLOAD_URL
    assert build_site._us_today_native_emit_for(binding, True) == url
    # Legacy two-field pair, missing pins, explicit None, empty shelf: no emit.
    assert build_site._us_today_native_emit_for(BINDING, True) is None
    assert build_site._us_today_native_emit_for(None, True) is None
    assert build_site._us_today_native_emit_for({}, True) is None
    assert build_site._us_today_native_emit_for(binding, False) is None


def test_fresh_native_change_forces_the_real_rerender():
    """A same-session native binding change cannot pair a fresh source with
    older Today metadata — exercised through the production predicate."""
    from tests.test_us_board_gate import _actual_fresh_board_condition
    board = {"as_of": "2026-10-12", "staleness": {}}
    assert _actual_fresh_board_condition(
        board, board, vm_native=None, fresh_native=None) is False
    assert _actual_fresh_board_condition(
        board, board, vm_native={"changed": True}, fresh_native=None) is True


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
_out={admitted:(_res?{pins:_res.pins,rosterLen:_res.roster.length,
                       display:_res.display}:null),
      gridHtml:_grid.innerHTML||null,
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


def _run_hydrate_today(html, preview, total, binding, shell=None, meta="OMIT"):
    node = shutil.which("node")
    assert node, "node is required for the Today source-binding gate"
    prelude = _PRELUDE.replace("__SHELL__", json.dumps(shell or {}))
    program = "var _res=hydrateToday({}, {}, {}, {}, {});\n{}".format(
        json.dumps(html), json.dumps(preview), json.dumps(total),
        json.dumps(binding),
        "undefined" if meta == "OMIT" else json.dumps(meta), _SNAPSHOT)
    harness = (prelude
               + _function_source(TEMPLATE.read_text(encoding="utf-8"),
                                  "todaySourceAdmission")
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


def _native_fixture(*, featured=(True, True, True, False)):
    """A REAL owner binding over a four-row roster; the displayed shelf names
    positions 0,1,3 — noncontiguous on purpose."""
    pytest.importorskip("scripts.build_site")
    doc = _source_doc(featured=featured)
    raw = _source_bytes(doc)
    return build_site_native(raw)


def _js_binding(binding):
    return binding


def _served_attr(binding, pairs):
    return ";".join("{}~{}".format(binding["ordered_rows"][p]["selection_index"],
                                   binding["ordered_rows"][q]["row_receipt"])
                    for p, q in pairs)


def _shell_ok(binding, served=((0, 0), (1, 1), (3, 3))):
    return {"data-today-source-sha256": binding["source_sha256"],
            "data-today-pair-id": binding["pair_id"],
            "data-today-selection-receipt": binding["selection_receipt"],
            "data-today-roster-size": str(len(binding["ordered_rows"])),
            "data-today-served": _served_attr(binding, served)}


def _meta_for(binding, positions):
    return [{"selection_index": p, "row_receipt": binding["ordered_rows"][p]["row_receipt"]}
            for p in positions]


def test_matching_source_hydrates_with_noncontiguous_owner_positions():
    binding = _native_fixture()
    out = _run_hydrate_today(_cards("AAA", "BBB", "CCC"), 3, 3, binding,
                             _shell_ok(binding), _meta_for(binding, [0, 1, 3]))
    assert out["gridChildren"] == 3
    assert out["visible"] == "3" and out["total"] == "3"
    assert out["emptyRemoved"] is True and "AAA" in out["gridHtml"]
    assert out["admitted"]["rosterLen"] == 4
    assert [d["selection_index"] for d in out["admitted"]["display"]] == [0, 1, 3]
    assert out["admitted"]["pins"] == {
        "source_sha256": binding["source_sha256"],
        "pair_id": binding["pair_id"],
        "selection_receipt": binding["selection_receipt"]}


def test_duplicate_tickers_with_distinct_positions_hydrate_uncollapsed():
    binding = _native_fixture()
    out = _run_hydrate_today(_cards("AAA", "AAA"), 2, 3, binding,
                             _shell_ok(binding, served=((0, 0),)),
                             _meta_for(binding, [0, 1]))
    assert out["gridChildren"] == 2
    assert out["visible"] == "2" and out["total"] == "3"


def _refuse(html, preview, total, binding, shell, meta):
    out = _run_hydrate_today(html, preview, total, binding, shell, meta)
    assert out["gridHtml"] is None and out["gridChildren"] == 0
    assert out["admitted"] is None and out["visible"] is None
    assert out["emptyRemoved"] is False
    return out


@pytest.mark.parametrize("binding", [None, "binding", [], {}])
def test_bad_binding_container_refuses(binding):
    good = _native_fixture()
    _refuse(_cards("AAA", "BBB", "CCC"), 3, 3, binding, _shell_ok(good),
            _meta_for(good, [0, 1, 3]))


@pytest.mark.parametrize("field,bad", [
    ("source_sha256", None), ("source_sha256", 7),
    ("source_sha256", "SHA256:" + "a" * 64),
    ("source_sha256", "sha256:" + "g" * 64),
    ("pair_id", None), ("pair_id", 7),
    ("pair_id", "A" * 32), ("pair_id", "1" * 33),
    ("selection_receipt", None), ("selection_receipt", 7),
    ("selection_receipt", "SHA256:" + "c" * 64),
    ("selection_receipt", "sha256:" + "c" * 63),
    ("schema", None), ("schema", "wrong"),
    ("receipt_kind", None), ("receipt_kind", "W3C_CAPTURE"),
    ("market_session", None), ("market_session", 7),
    ("market_session", "2026-11-27 "),
])
def test_each_bad_binding_field_refuses_independently(field, bad):
    good = _native_fixture()
    malformed = {**good, field: bad}
    # All other fields remain genuine, so schema/session cannot accidentally
    # become an unrelated refusal for a source-pin type or syntax test.
    _refuse(_cards("AAA", "BBB", "CCC"), 3, 3, malformed, _shell_ok(good),
            _meta_for(good, [0, 1, 3]))


@pytest.mark.parametrize("field", ["source_sha256", "pair_id", "selection_receipt",
                                  "schema", "receipt_kind", "market_session"])
def test_each_missing_binding_field_refuses_independently(field):
    good = _native_fixture()
    malformed = {key: value for key, value in good.items() if key != field}
    _refuse(_cards("AAA", "BBB", "CCC"), 3, 3, malformed, _shell_ok(good),
            _meta_for(good, [0, 1, 3]))


def test_unavailable_shell_pins_refuse_valid_binding():
    binding = _native_fixture()
    _refuse(_cards("AAA", "BBB", "CCC"), 3, 3, binding, {},
            _meta_for(binding, [0, 1, 3]))
    half = {"data-today-source-sha256": binding["source_sha256"],
            "data-today-pair-id": binding["pair_id"]}
    _refuse(_cards("AAA", "BBB", "CCC"), 3, 3, binding, half,
            _meta_for(binding, [0, 1, 3]))


def test_roster_metadata_must_be_complete_and_positionally_exact():
    binding = _native_fixture()
    shell = _shell_ok(binding)
    cards = _cards("AAA", "BBB", "CCC")
    good_meta = _meta_for(binding, [0, 1, 3])
    # missing roster
    _refuse(cards, 3, 3, {k: v for k, v in binding.items() if k != "ordered_rows"},
            shell, good_meta)
    # roster length disagreeing with the shell's roster SIZE
    short = dict(binding, ordered_rows=binding["ordered_rows"][:-1])
    _refuse(cards, 3, 3, short, shell, good_meta)
    shell_wrong_size = dict(shell, **{"data-today-roster-size": "5"})
    _refuse(cards, 3, 3, binding, shell_wrong_size, good_meta)
    # a reordered roster is the owner's order broken
    reordered = dict(binding, ordered_rows=list(reversed(binding["ordered_rows"])))
    _refuse(cards, 3, 3, reordered, shell, good_meta)
    # a same-count REPLACED receipt at a SERVED or DISPLAYED position refuses
    # the whole shelf; at a hidden position it is undetectable in the DOM gate
    # and is caught at native-query time, where the owner's candidates can
    # never match a tampered roster position (loader suite asserts exactly
    # that refusal).
    replaced_served = json.loads(json.dumps(binding))
    replaced_served["ordered_rows"][3]["row_receipt"] = "sha256:" + "f" * 64
    _refuse(cards, 3, 3, replaced_served, shell, good_meta)
    replaced_displayed = json.loads(json.dumps(binding))
    replaced_displayed["ordered_rows"][0]["row_receipt"] = "sha256:" + "f" * 64
    _refuse(cards, 3, 3, replaced_displayed, shell, good_meta)
    # a malformed entry refuses
    malformed = json.loads(json.dumps(binding))
    malformed["ordered_rows"][1] = {"selection_index": 1}
    _refuse(cards, 3, 3, malformed, shell, good_meta)


def test_served_shell_metadata_is_validated_against_the_owner_roster():
    binding = _native_fixture()
    cards = _cards("AAA", "BBB", "CCC")
    meta = _meta_for(binding, [0, 1, 3])
    # served receipt that is not that position's owner receipt
    wrong = dict(_shell_ok(binding),
                 **{"data-today-served": _served_attr(binding, ((0, 1),))})
    _refuse(cards, 3, 3, binding, wrong, meta)
    # duplicate served index
    dup = _shell_ok(binding, served=((0, 0), (0, 0)))
    _refuse(cards, 3, 3, binding, dup, meta)
    # malformed encodings: wrong separator, non-numeric index, blank index
    _refuse(cards, 3, 3, binding,
            dict(_shell_ok(binding), **{"data-today-served": "0:sha256:" + "0" * 64}),
            meta)
    _refuse(cards, 3, 3, binding,
            dict(_shell_ok(binding), **{"data-today-served": "x~sha256:" + "0" * 64}),
            meta)
    _refuse(cards, 3, 3, binding,
            dict(_shell_ok(binding), **{"data-today-served": "~"}), meta)
    # index beyond the roster size
    _refuse(cards, 3, 3, binding,
            dict(_shell_ok(binding), **{"data-today-served": "9~sha256:" + "0" * 64}),
            meta)
    # missing attr entirely
    _refuse(cards, 3, 3, binding,
            {k: v for k, v in _shell_ok(binding).items()
             if k != "data-today-served"}, meta)
    # empty served list is honest and fine
    out = _run_hydrate_today(cards, 3, 3, binding, _shell_ok(binding, served=()),
                             meta)
    assert out["admitted"] is not None and out["gridChildren"] == 3


def test_display_meta_completeness_and_duplication_rules():
    binding = _native_fixture()
    shell = _shell_ok(binding)
    cards = _cards("AAA", "BBB", "CCC")
    # missing meta
    _refuse(cards, 3, 3, binding, shell, "OMIT")
    _refuse(cards, 3, 3, binding, shell, None)
    # wrong length: the served-subset check cannot rescue a short list
    _refuse(cards, 3, 3, binding, shell, _meta_for(binding, [0, 1]))
    _refuse(cards, 3, 3, binding, shell, _meta_for(binding, [0, 1, 2, 3]))
    # duplicate original index — a repeated ticker is legal, a repeated index is not
    _refuse(cards, 3, 3, binding, shell, _meta_for(binding, [0, 0, 1]))
    # replaced receipt at one displayed position refuses the whole shelf
    replaced = _meta_for(binding, [0, 1, 3])
    replaced[2]["row_receipt"] = "sha256:" + "e" * 64
    _refuse(cards, 3, 3, binding, shell, replaced)
    # a served row missing from the display refuses (subset must correspond)
    _refuse(cards, 3, 3, binding, shell, _meta_for(binding, [1, 2, 3]))


def test_same_count_changed_source_refuses():
    binding = _native_fixture()
    meta = _meta_for(binding, [0, 1, 3])
    out = _run_hydrate_today(
        _cards("AAA", "BBB", "CCC"), 3, 3, binding,
        {"data-today-source-sha256": "sha256:" + "d" * 64,
         "data-today-pair-id": binding["pair_id"],
         "data-today-selection-receipt": binding["selection_receipt"],
         "data-today-roster-size": str(len(binding["ordered_rows"])),
         "data-today-served": ""}, meta)
    assert out["gridHtml"] is None and out["admitted"] is None
    _refuse(_cards("AAA", "BBB", "CCC"), 3, 3, binding,
            {k: v for k, v in _shell_ok(binding).items()
             if k != "data-today-selection-receipt"}
            | {"data-today-selection-receipt": "sha256:" + "0" * 64}, meta)


def test_incomplete_or_extra_or_blank_cards_refuse_entirely():
    binding = _native_fixture()
    base = _shell_ok(binding)
    meta = _meta_for(binding, [0, 1, 3])
    # fewer cards than preview
    _refuse(_cards("AAA", "BBB"), 3, 3, binding, base, meta)
    # a second malformed pvcard cannot hide outside the selected-card query
    _refuse(_cards("AAA", "BBB", "CCC") + '<a class="pvcard" href="#">X</a>',
            4, 4, binding, base, meta[:3])
    _refuse(_cards("AAA", "BBB", "CCC") + '<a class="pvcard" href="#">X</a>',
            3, 3, binding, base, meta)
    # blank ticker attribute present but empty
    _refuse(_cards("AAA", "BBB") + '<a class="pvcard" data-ticker="" href="#">Z</a>',
            3, 3, binding, base, meta)


@pytest.mark.parametrize("html", [['<a class="pvcard" data-ticker="AAA">AAA</a>'],
                                  {"cards": "AAA"}, 42])
def test_nonstring_card_payload_refuses(html):
    binding = _native_fixture()
    out = _refuse(html, 1, 1, binding, _shell_ok(binding, served=()),
                  _meta_for(binding, [0]))
    assert out["admitted"] is None


def test_empty_ungated_remainder_admits_without_touching_the_shell():
    """The ungated shape ships an honest empty Today remainder with REAL
    protected metadata: a served shelf still admits and the server shelf stays
    as is, while a genuinely EMPTY served shelf admits nothing at all."""
    binding = _native_fixture()
    out = _run_hydrate_today("", 0, 0, binding, _shell_ok(binding), [])
    assert out["admitted"] is not None
    assert out["gridHtml"] is None and out["visible"] is None
    assert out["emptyRemoved"] is False
    # A noncontiguous real server shelf (indices 1 and 3) also stays admitted.
    out = _run_hydrate_today("", 0, 0, binding,
                             _shell_ok(binding, served=((1, 1), (3, 3))), [])
    assert out["admitted"] is not None
    assert [d["selection_index"] for d in out["admitted"]["display"]] == [1, 3]
    # A genuinely empty served shelf refuses: nothing promised AND nothing
    # served means the one shared loader makes no query and no mutation.
    _refuse("", 0, 0, binding, _shell_ok(binding, served=()), [])
    # An empty html against a PROMISED shelf is a refusal, not an admission.
    _refuse("", 3, 3, binding, _shell_ok(binding), _meta_for(binding, [0, 1, 3]))


def test_hydrate_panels_passes_payload_binding_and_meta_as_args():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert re.search(
        r"hydrateToday\(\s*payload\.today_cards_html,\s*payload\.today_preview,\s*"
        r"payload\.today_total,\s*payload\.today_source_binding,\s*"
        r"payload\.today_rows_meta\s*\)", text), (
        "hydratePanels must pass payload.today_source_binding and "
        "payload.today_rows_meta to hydrateToday")


# ── real production envelope admission / outcome under node ─────────────────

_ENVELOPE_PRELUDE = """
var ADM = __ADM__;
"""


def _run_envelope(payload, roster_len=4, display=None, binding=None):
    node = shutil.which("node")
    assert node, "node is required for the envelope gate"
    binding = binding or _native_fixture()
    adm = {"pins": {"source_sha256": binding["source_sha256"],
                    "pair_id": binding["pair_id"],
                    "selection_receipt": binding["selection_receipt"]},
           "roster": binding["ordered_rows"],
           "served": [], "market_session": binding["market_session"],
           "display": display if display is not None
           else _meta_for(binding, [0, 1, 3])}
    prelude = _ENVELOPE_PRELUDE.replace("__ADM__", json.dumps(adm))
    text = TEMPLATE.read_text(encoding="utf-8")
    harness = (prelude
               + _function_source(text, "admitBriefEnvelope")
               + _function_source(text, "admitDailyBrief")
               + _function_source(text, "todayNativeOutcome")
               + "console.log(JSON.stringify(todayNativeOutcome(__PAYLOAD__, ADM)));\n"
               .replace("__PAYLOAD__", json.dumps(payload)))
    run = subprocess.run([node, "-e", harness], capture_output=True, text=True,
                         timeout=30, check=False)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def _fixture_candidate_input(binding, index):
    # Explicit schema fixture; the real producer/parquet/B1 positive oracle below
    # independently validates this client gate against actual owner output.
    return {"schema": "prophet.daily_brief_candidate_input/v1", "state": "SELECTED",
            "security_id": "fixture-security", "episode_id": "fixture-episode",
            "owner_ref": "explicit-schema-fixture", "asof": "2026-11-27T18:08:00Z",
            "candidate_generation_id": "peg:" + "d" * 64,
            "market_session": binding["market_session"],
            "source_receipt": "sha256:" + "e" * 64,
            "selection_receipt": binding["selection_receipt"],
            "display": {"selection_index": index}}


def _envelope(binding, *, status="PARTIAL", candidates="auto",
              reason_codes=("DAILY_BRIEF_OWNER_INPUTS_UNAVAILABLE",), **overrides):
    if candidates == "auto":
        candidates = [{"selection_index": row["selection_index"],
                       "row_receipt": row["row_receipt"],
                       "status": "AVAILABLE",
                       "candidate_input": _fixture_candidate_input(binding, row["selection_index"]),
                       "daily_brief": {"assessment": None},
                       "reason_codes": ["B4_NATIVE_OWNER_READ_UNAVAILABLE"]}
                      for row in binding["ordered_rows"]]
    env = {"schema": "prophet.daily_brief_read/v1", "status": status,
           "candidate_generation_id": "peg:" + "d" * 64,
           "source_binding": {"schema": "prophet.today_selection_source_binding/v1",
                              "receipt_kind": "EXACT_DISPLAYED_SOURCE",
                              "source_sha256": binding["source_sha256"],
                              "pair_id": binding["pair_id"],
                              "selection_receipt": binding["selection_receipt"],
                              "market_session": binding["market_session"]},
           "candidates": candidates,
           "reason_codes": list(reason_codes)}
    env.update(overrides)
    return env


def test_valid_partial_envelope_discloses_honest_typed_partial():
    binding = _native_fixture()
    out = _run_envelope(_envelope(binding))
    assert out["state"] == "partial"
    assert out["reasons"] == ["DAILY_BRIEF_OWNER_INPUTS_UNAVAILABLE"]
    assert out["shown"] == 3 and out["total"] == 3


def test_available_status_and_unavailable_statuses_are_typed_honestly():
    binding = _native_fixture()
    assert _run_envelope(_envelope(binding, status="AVAILABLE"))["state"] == "available"
    out = _run_envelope(_envelope(binding, status="UNAVAILABLE",
                                  candidates=[],
                                  reason_codes=["SOURCE_BINDING_MISMATCH"]))
    assert out["state"] == "unavailable"
    assert out["reasons"] == ["SOURCE_BINDING_MISMATCH"]
    out = _run_envelope(_envelope(binding, status="UNAVAILABLE", candidates=[],
                                  reason_codes=[]))
    assert out["state"] == "unavailable"
    assert out["reasons"] == ["DAILY_BRIEF_UNAVAILABLE"]
    out = _run_envelope(_envelope(binding, status="UNAVAILABLE", candidates=[]))
    assert out["state"] == "unavailable"
    assert out["reasons"] == ["DAILY_BRIEF_OWNER_INPUTS_UNAVAILABLE"]
    out = _run_envelope(_envelope(binding, status="WEIRD"))
    assert out["state"] == "unavailable"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e.update(schema="prophet.daily_brief_read/v2"),
        lambda e: e.pop("schema"),
        lambda e: e.update(source_binding=None),
        lambda e: e["source_binding"].update(receipt_kind="W3C_CAPTURE"),
        lambda e: e["source_binding"].update(selection_receipt="sha256:" + "0" * 64),
        lambda e: e["source_binding"].update(pair_id="2" * 32),
        lambda e: e.pop("candidates"),
        lambda e: e.update(candidates=e["candidates"][:-1]),
        lambda e: e.update(candidates=e["candidates"] + [e["candidates"][0]]),
        lambda e: e["candidates"].reverse(),
        lambda e: e["candidates"][2].update(row_receipt="sha256:" + "f" * 64),
        lambda e: e["candidates"][1].update(selection_index=9),
        lambda e: e["candidates"][0].pop("reason_codes"),
    ],
)
def test_envelope_reorder_replacement_and_slot_crimes_refuse(mutate):
    binding = _native_fixture()
    payload = _envelope(binding)
    mutate(payload)
    out = _run_envelope(payload)
    assert out["state"] == "unavailable"
    assert out["reasons"] == ["DAILY_BRIEF_RESPONSE_INVALID"]


def test_envelope_admits_only_exact_displayed_positions():
    binding = _native_fixture()
    payload = _envelope(binding)
    assert _run_envelope(payload)["state"] == "partial"
    payload["candidates"][3]["status"] = "UNAVAILABLE"
    payload["candidates"][3]["candidate_input"] = None
    payload["candidates"][3]["reason_codes"] = ["CANDIDATE_RECONCILIATION_PENDING"]
    assert _run_envelope(payload)["shown"] == 2


def _actual_native_envelope(tmp_path, monkeypatch):
    """Original producer over real parquet/B1, not AVAILABLE fixture invention."""
    from tests.test_prophet_today_provenance import _native_today, _read_today, writer
    source, _ = _native_today(tmp_path, monkeypatch, duplicate=True)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    binding = build_site_native(source.read_bytes())
    payload = _read_today(tmp_path, source)
    assert payload["status"] == "PARTIAL"
    assert all(row["status"] == "AVAILABLE" for row in payload["candidates"])
    return binding, payload


def test_actual_native_response_session_mismatch_refuses(tmp_path, monkeypatch):
    import copy
    binding, payload = _actual_native_envelope(tmp_path, monkeypatch)
    display = _meta_for(binding, [0, 1])
    assert _run_envelope(payload, binding=binding, display=display)["shown"] == 2
    for bad in (None, "2026-11-26", "2026-11-27 "):
        malformed = copy.deepcopy(payload)
        malformed["source_binding"]["market_session"] = bad
        assert _run_envelope(malformed, binding=binding, display=display)["state"] == "unavailable"


def test_actual_native_available_requires_owner_candidate_input(tmp_path, monkeypatch):
    import copy
    binding, payload = _actual_native_envelope(tmp_path, monkeypatch)
    display = _meta_for(binding, [0, 1])
    assert _run_envelope(payload, binding=binding, display=display)["shown"] == 2
    for bad in (None, {}, [], {"schema": "wrong"}):
        malformed = copy.deepcopy(payload)
        malformed["candidates"][0]["candidate_input"] = bad
        assert _run_envelope(malformed, binding=binding, display=display)["state"] == "unavailable"


def test_actual_native_candidate_identity_pins_refuse_malformed_input(tmp_path, monkeypatch):
    import copy
    binding, payload = _actual_native_envelope(tmp_path, monkeypatch)
    display = _meta_for(binding, [0, 1])
    mutations = [
        lambda p: p["candidates"][0].update(status="UNKNOWN"),
        lambda p: p["candidates"][0]["candidate_input"].update(state="UNKNOWN"),
        lambda p: p["candidates"][0]["candidate_input"].update(owner_ref=""),
        lambda p: p["candidates"][0]["candidate_input"].update(asof=None),
        lambda p: p["candidates"][0]["candidate_input"].update(security_id=""),
        lambda p: p["candidates"][0]["candidate_input"].update(episode_id=None),
        lambda p: p["candidates"][0]["candidate_input"].update(market_session="2026-11-26"),
        lambda p: p["candidates"][0]["candidate_input"].update(selection_receipt="sha256:" + "f" * 64),
        lambda p: p["candidates"][0]["candidate_input"].update(candidate_generation_id="peg:" + "f" * 64),
        lambda p: p["candidates"][0]["candidate_input"].update(source_receipt=None),
        lambda p: p["candidates"][0]["candidate_input"]["display"].update(selection_index=1),
    ]
    for mutate in mutations:
        malformed = copy.deepcopy(payload)
        mutate(malformed)
        assert _run_envelope(malformed, binding=binding, display=display)["state"] == "unavailable"
