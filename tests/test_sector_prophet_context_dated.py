"""SIC-I06R (masterplan §8.3, P16): dated ETF context on the Prophet destination.

Static + node-protocol contracts for the optional context params the Sector
Central shell may hand to /us_stocks.html:

* ``si_asof`` / ``si_gen`` / ``si_origin`` are parsed in the ``si_sector``
  style (params.getAll, exactly one strictly-shaped value) and are display
  context only — missing or malformed fields are omitted, never invented;
* ``sectorProphetHref`` may append the three params but NEVER the ladder
  filter's own query param (arrival must not filter);
* ``si_origin`` is an allowlist of relative Sector Intelligence pages with an
  optional fragment — the return anchor uses it only when allowlisted, else
  the existing fixed fallback stands;
* the note states the honestly loaded member count (rows the stocks table
  actually carries), with no coverage claim — the page has no membership
  roster, so no "of <m>" denominator is invented.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "templates"
PARTIAL_HTML = TPL / "_sector_prophet_context.html.j2"
PARTIAL_JS = TPL / "_sector_prophet_context.js.j2"

SECTOR_GROUP = {"group_kind": "sector", "group_id": "XLK"}
BASELINE_HREF = "us_stocks.html?si_sector=XLK#sector-prophet-context"


def _node(js: str):
    result = subprocess.run(["node", "-e", js], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _protocol(expression: str):
    """Run an expression against the partial's top-level functions, DOM-free."""
    src = PARTIAL_JS.read_text(encoding="utf-8")
    return _node("const document={getElementById:()=>null};\n" + src
                 + "\nprocess.stdout.write(JSON.stringify(" + expression + "));")


def _selection(search: str):
    return _protocol("sectorProphetSelection(" + json.dumps(search) + ")")


def _href(group, context=None):
    call = "sectorProphetHref(" + json.dumps(group)
    if context is not None:
        call += "," + json.dumps(context)
    return _protocol(call + ")") or ""


def _receiver(search: str, *, rows="ABSENT", lang: str = "en", fragment: str = "#sector-prophet-context"):
    """DOM-stub harness: the partial's IIFE against stub elements.

    ``rows="ABSENT"`` (the default) means no #us-stocktable-data element at
    all — the table has not loaded. Any other value is the JSON rows array the
    element carries.
    """
    src = PARTIAL_JS.read_text(encoding="utf-8")
    config = json.dumps({"search": search, "rows": rows, "lang": lang, "fragment": fragment})
    return _node("const cfg=" + config + ";" + r"""
const els={};let lang=cfg.lang;
function mk(id,legs){const e={id,textContent:'',attrs:{},hidden:false,handlers:{},
  setAttribute(k,v){e.attrs[k]=String(v);},addEventListener(k,f){e.handlers[k]=f;},
  querySelector(sel){return legs?(legs[sel]||null):null;}};
 els[id]=e;return e;}
['sector-prophet-context','si-prophet-subject','si-prophet-note','si-prophet-return',
 'si-prophet-clear','si-prophet-screener'].forEach(function(id){mk(id,null);});
mk('si-prophet-t-asof',{'.l-en':{textContent:'members as observed'},'.l-zh':{textContent:'成分股观察日期'}});
mk('si-prophet-t-gen',{'.l-en':{textContent:'generation'},'.l-zh':{textContent:'世代'}});
mk('si-prophet-t-members',{'.l-en':{textContent:'{n} members loaded'},'.l-zh':{textContent:'已加载 {n} 只成分股'}});
if(cfg.rows!=='ABSENT'){const t=mk('us-stocktable-data',null);
  t.textContent=JSON.stringify({rows:JSON.parse(cfg.rows)});}
const document={getElementById:function(id){return els[id]||null;},
  documentElement:{getAttribute:function(){return lang;}},addEventListener:function(){}};
const calls=[];
const window={location:{search:cfg.search,hash:cfg.fragment},addEventListener:function(){},
  USStockTable:{_selectSector:function(v){calls.push(v);return true;}},
  USProphetSource:{set:function(){throw Error('arrival must not touch the source owner');}}};
const history={pushState(){throw Error('no history writes on arrival');},
  replaceState(){throw Error('no history writes on arrival');}};
""" + src + r"""
process.stdout.write(JSON.stringify({note:els['si-prophet-note'].textContent,
  back:els['si-prophet-return'].attrs.href,subject:els['si-prophet-subject'].textContent,
  filterCalls:calls}));
""")


# ── the three params, parsed in the si_sector style ───────────────────────────

def test_dated_context_params_are_parsed():
    read = _selection("?si_sector=XLK&si_asof=2026-10-18&si_gen=g20261018&si_origin=sector_cycles.html")
    assert read["status"] == "selected" and read["id"] == "XLK"
    assert read["asof"] == "2026-10-18"
    assert read["gen"] == "g20261018"
    assert read["origin"] == "sector_cycles.html"


def test_context_fields_stay_absent_keys_when_not_supplied():
    """The paper suite pins the exact key set for a plain si_sector URL."""
    read = _selection("?si_sector=XLK")
    assert set(read) == {"status", "id", "name_en", "name_zh", "return_href"}


def test_missing_or_malformed_context_fields_are_omitted_never_invented():
    cases = [
        "?si_sector=XLK&si_asof=2026-13-40",        # impossible month
        "?si_sector=XLK&si_asof=2026-02-30",        # fabricated day (rolls over)
        "?si_sector=XLK&si_asof=2026-10-18T00:00",  # not date-only
        "?si_sector=XLK&si_asof=26-10-18",          # not YYYY
        "?si_sector=XLK&si_asof=2026-10-18&si_asof=2026-10-19",  # ambiguous
        "?si_sector=XLK&si_gen=" + "g" * 65,        # over the 64-char bound
        "?si_sector=XLK&si_gen=gené",          # non-printable-ASCII
        "?si_sector=XLK&si_gen=",                   # empty
        "?si_sector=XLK&si_gen=a&si_gen=b",         # ambiguous
    ]
    for search in cases:
        read = _selection(search)
        assert read["status"] == "selected", search
        assert "asof" not in read, search
        assert "gen" not in read, search


def test_generation_accepts_the_full_printable_ascii_budget():
    read = _selection("?si_sector=XLK&si_gen=" + "g" * 64)
    assert read["gen"] == "g" * 64


# ── the origin allowlist ──────────────────────────────────────────────────────

ALLOWED_ORIGINS = [
    "sector_central.html",
    "sector_central.html#map",
    "sector_cycles.html",
    "sector_cycles.html#fragment-1",
    "sectors/XLK.html",
    "sectors/XLRE.html#cycles",
    "sectors/XLY.html#",
]

REFUSED_ORIGINS = [
    "https://macro.test/sector_central.html",
    "//macro.test/sector_central.html",
    "/sector_central.html",
    "../sector_central.html",
    "sector_central.html?g=XLK",
    "us_stocks.html",
    "stock.html#AAPL",
    "sectors/SMH.html",
    "sectors/xlk.html",
    "sectors/.html",
    "javascript:alert(1)",
    "",
]


def test_si_origin_is_an_allowlist_of_relative_sector_pages():
    # URLSearchParams keeps '#' inside a value, so the raw shape is the decoded
    # shape the receiver must judge.
    for origin in ALLOWED_ORIGINS:
        read = _selection("?si_sector=XLK&si_origin=" + origin)
        assert read.get("origin") == origin, origin
    for origin in REFUSED_ORIGINS:
        read = _selection("?si_sector=XLK&si_origin=" + origin)
        assert "origin" not in read, origin
        assert read["status"] == "selected", origin


def test_every_canonical_etf_dossier_is_allowlisted():
    for etf in ["XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]:
        read = _selection("?si_sector=XLK&si_origin=sectors/{}.html".format(etf))
        assert read.get("origin") == "sectors/{}.html".format(etf)


# ── the producer ──────────────────────────────────────────────────────────────

def test_producer_keeps_the_single_argument_contract_byte_exact():
    assert _href(SECTOR_GROUP) == BASELINE_HREF
    assert _href(None) == "" and _href({"group_kind": "basket", "group_id": "XLK"}) == ""


def test_producer_appends_the_three_params_and_round_trips():
    context = {"asof": "2026-10-18", "gen": "g7", "origin": "sector_central.html#map"}
    href = _href(SECTOR_GROUP, context)
    assert href == ("us_stocks.html?si_sector=XLK&si_asof=2026-10-18&si_gen=g7"
                    "&si_origin=sector_central.html%23map#sector-prophet-context")
    read = _protocol("sectorProphetSelection(new URL(" + json.dumps("https://macro.test/" + href)
                     + ").search)")
    assert read["asof"] == "2026-10-18" and read["gen"] == "g7"
    assert read["origin"] == "sector_central.html#map"


def test_producer_appends_only_the_fields_actually_supplied():
    href = _href(SECTOR_GROUP, {"asof": "2026-10-18"})
    assert href == "us_stocks.html?si_sector=XLK&si_asof=2026-10-18#sector-prophet-context"
    assert _href(SECTOR_GROUP, {"asof": None, "gen": "", "origin": 0}) == BASELINE_HREF


def test_producer_never_emits_the_ladder_param():
    """§8.3: shell links must never carry the ladder filter's query param."""
    for context in [None, {}, {"asof": "2026-10-18", "gen": "g7", "origin": "sector_cycles.html"},
                    {"life": "ready"}, {"asof": "life", "gen": "&life=ready"}]:
        href = _href(SECTOR_GROUP, context)
        assert "life=" not in href, (context, href)
        assert "?life" not in href and "&life" not in href, (context, href)


def test_the_ladder_param_name_is_absent_from_the_partial_source():
    """grep -c 'life' over the shipped producer source is zero."""
    assert "life" not in PARTIAL_JS.read_text(encoding="utf-8")


# ── the return anchor ─────────────────────────────────────────────────────────

def test_return_anchor_prefers_the_allowlisted_origin_else_the_existing_return():
    result = _receiver("?si_sector=XLK&si_origin=sector_cycles.html#evidence")
    assert result["back"] == "sector_cycles.html#evidence"
    result = _receiver("?si_sector=XLK")
    assert result["back"] == "sector_central.html?g=XLK#map"
    # A refused origin falls back to the same existing return — never onward.
    result = _receiver("?si_sector=XLK&si_origin=https://elsewhere.test")
    assert result["back"] == "sector_central.html?g=XLK#map"


def test_the_fixed_fallback_return_is_preserved_in_both_partial_files():
    html = PARTIAL_HTML.read_text(encoding="utf-8")
    js = PARTIAL_JS.read_text(encoding="utf-8")
    assert 'id="si-prophet-return" href="sector_central.html#map"' in html
    assert "'sector_central.html#map'" in js  # the invalid-state branch
    assert "read.origin || read.return_href" in js


# ── the note: dated readback + honest loaded population ──────────────────────

ROWS = json.dumps([
    {"ticker": "AAPL", "sector": "Information Technology"},
    {"ticker": "XOM", "sector": "Energy"},
    {"ticker": "MSFT", "sector": "Information Technology"},
])


def test_note_carries_the_dated_readback_and_the_honest_loaded_count():
    result = _receiver("?si_sector=XLK&si_asof=2026-10-18&si_gen=g7", rows=ROWS)
    assert result["note"].startswith(
        "Information Technology · members as observed 2026-10-18 · generation g7"
        " · 2 members loaded.")
    assert "of 2" not in result["note"]  # no invented denominator


def test_note_readback_segments_are_omitted_when_their_params_are_absent():
    result = _receiver("?si_sector=XLK", rows=ROWS)
    assert result["note"].startswith("Information Technology · 2 members loaded.")
    result = _receiver("?si_sector=XLK")
    assert "members loaded" not in result["note"]  # table never loaded
    assert result["note"].startswith("Information Technology.")


def test_note_reads_the_zh_legs_under_the_zh_language():
    result = _receiver("?si_sector=XLK&si_asof=2026-10-18&si_gen=g7", rows=ROWS, lang="zh")
    assert result["note"].startswith(
        "信息技术 · 成分股观察日期 2026-10-18 · 世代 g7 · 已加载 2 只成分股。")
    assert result["subject"] == "信息技术 · XLK"


def test_arrival_counts_but_never_filters_the_table():
    """The count is read-only; the screener owner still owns every filter."""
    result = _receiver("?si_sector=XLK&si_asof=2026-10-18", rows=ROWS)
    assert result["filterCalls"] == []


def test_readback_carriers_are_authored_in_the_partial():
    html = PARTIAL_HTML.read_text(encoding="utf-8")
    for carrier, call in [
        ("si-prophet-t-asof", "t('members as observed', '成分股观察日期')"),
        ("si-prophet-t-gen", "t('generation', '世代')"),
        ("si-prophet-t-members", "t('{n} members loaded', '已加载 {n} 只成分股')"),
    ]:
        assert ('id="%s" hidden' % carrier) in html, carrier
        assert "{{ %s }}" % call in html, carrier
