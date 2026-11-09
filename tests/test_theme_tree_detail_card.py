"""Tests for the U2 micro-theme detail card on /theme_tree.html.

Covers the "not done unless" clauses of SPEC_U2: typed nulls (orphan →
unknown, zero instruments → none, never a 0), the forbidden-key walk over
the card blob, no vendor-internal ids in the blob or chips, ``</`` escaping,
one detail entry per chip, and a market qualifier on every instrument.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from engine.theme_graph import hierarchy_breadth_display as hb  # noqa: E402
from scripts.build_theme_tree_page import (  # noqa: E402
    _build_details,
    _details_json,
    _node_name_index,
    compose,
    render,
)
from tests.test_build_theme_tree_page import _mk_edges, _mk_nodes  # noqa: E402

_VENDOR = re.compile(r"ltheme:|ths_concepts|baskets_china_ths|finviz")
_BLOB_RE = re.compile(r'id="tt-detail-data">(.*?)</script>', re.S)
_CHIP_RE = re.compile(r'<button type="button" class="tt-chip"[^>]*>', re.S)


def _fixtures():
    """macroA → t1 → micro1 (proxied by a US and a China basket) and
    t1 → s1 → micro2; t2 → micro3 has no basket; micro_orphan has no parent.
    A vendor-derived basket also EXPRESSES t1 and must never surface."""
    nodes = _mk_nodes(
        {"node_id": "theme:macroA", "name_en": "Energy", "name_zh": "能源",
         "tier": "macro_category"},
        {"node_id": "theme:t1", "name_en": "Grid </script>", "name_zh": "电网",
         "tier": "theme"},
        {"node_id": "theme:t2", "name_en": "Storage", "name_zh": "储能",
         "tier": "theme"},
        {"node_id": "theme:s1", "name_en": "Lines", "name_zh": "线路",
         "tier": "sub_theme"},
        {"node_id": "theme:micro1", "name_en": "Transformers", "name_zh": "变压器",
         "tier": "micro_theme"},
        {"node_id": "theme:micro2", "name_en": "Cables", "name_zh": "电缆",
         "tier": "micro_theme"},
        {"node_id": "theme:micro3", "name_en": "Cells", "name_zh": "电芯",
         "tier": "micro_theme"},
        {"node_id": "theme:micro_orphan", "name_en": "Loose", "name_zh": "游离",
         "tier": "micro_theme"},
        {"node_id": "basket:baskets:grid", "kind": "basket",
         "name_en": "Grid basket", "name_zh": "电网篮子", "tier": ""},
        {"node_id": "basket:baskets_china:grid", "kind": "basket",
         "name_en": "China grid", "name_zh": "中国电网", "tier": ""},
        {"node_id": "basket:baskets_china_ths:grid", "kind": "basket",
         "name_en": "Vendor grid", "name_zh": "供应商电网", "tier": ""},
    )
    edges = _mk_edges(
        {"src": "theme:macroA", "dst": "theme:t1"},
        {"src": "theme:macroA", "dst": "theme:t2"},
        {"src": "theme:t1", "dst": "theme:micro1"},
        {"src": "theme:t1", "dst": "theme:s1"},
        {"src": "theme:s1", "dst": "theme:micro2"},
        {"src": "theme:t2", "dst": "theme:micro3"},
        {"type": "EXPRESSES", "src": "basket:baskets:grid", "dst": "theme:t1",
         "edge_id": "EXPRESSES:us"},
        {"type": "EXPRESSES", "src": "basket:baskets_china:grid", "dst": "theme:t1",
         "edge_id": "EXPRESSES:cn"},
        {"type": "EXPRESSES", "src": "basket:baskets_china_ths:grid",
         "dst": "theme:t1", "edge_id": "EXPRESSES:ths"},
    )
    return nodes, edges


def _details(tmp_path=None):
    nodes, edges = _fixtures()
    envs = hb.hierarchy_breadth_table(nodes=nodes, edges=edges)
    site = tmp_path if tmp_path is not None else Path("/nonexistent-site")
    return _build_details(envs, _node_name_index(nodes), nodes, edges, site)


def _html():
    nodes, edges = _fixtures()
    return render(REPO, ctx=compose(REPO, nodes=nodes, edges=edges))


def _blob(html: str) -> dict:
    m = _BLOB_RE.search(html)
    assert m, "detail blob missing"
    return json.loads(m.group(1))


def test_orphan_micro_proxy_state_is_unknown():
    d = _details()
    assert d["theme:micro_orphan"]["proxy_state"] == "unknown"
    assert d["theme:micro_orphan"]["instruments"] == []
    assert d["theme:micro_orphan"]["chains"] == []


def test_zero_instruments_is_typed_none_never_zero():
    d = _details()
    assert d["theme:micro3"]["proxy_state"] == "none"
    assert d["theme:micro3"]["instruments"] == []
    html = _html()
    assert "No public proxy basket for this theme yet." in html
    assert "该主题暂无可公开的代理篮子。" in html


def test_available_instruments_carry_market_and_exclude_vendor():
    d = _details()
    insts = d["theme:micro1"]["instruments"]
    assert d["theme:micro1"]["proxy_state"] == "available"
    assert {i["name_en"] for i in insts} == {"Grid basket", "China grid"}
    for inst in insts:
        assert inst["market_en"] and inst["market_zh"]
    # Proxied via the parent theme across the sub_theme too.
    assert {i["name_en"] for i in d["theme:micro2"]["instruments"]} == {
        "Grid basket", "China grid"}


def test_chains_run_micro_to_root_without_self():
    d = _details()
    assert [[r["node_id"] for r in c] for c in d["theme:micro2"]["chains"]] == [
        ["theme:macroA", "theme:t1", "theme:s1"]]
    assert d["theme:micro2"]["breadth"][0]["micro_count"] == 2


def test_href_only_when_basket_page_exists(tmp_path):
    (tmp_path / "basket").mkdir()
    (tmp_path / "basket" / "grid.html").write_text("x")
    insts = {i["name_en"]: i for i in _details(tmp_path)["theme:micro1"]["instruments"]}
    assert insts["Grid basket"]["href"] == "basket/grid.html"
    assert insts["China grid"]["href"] is None


def test_blob_passes_forbidden_key_walk():
    blob = _blob(_html())
    assert hb.validate_no_forbidden_keys(blob) == []
    text = json.dumps(blob)
    for key in ("weight", "share", "score", "rank", "exposure_pct"):
        assert f'"{key}"' not in text


def test_no_vendor_ids_in_blob_or_chips():
    html = _html()
    raw = _BLOB_RE.search(html).group(1)
    assert not _VENDOR.search(raw)
    for chip in _CHIP_RE.findall(html):
        assert not _VENDOR.search(chip)


def test_blob_escapes_script_close():
    nodes, edges = _fixtures()
    envs = hb.hierarchy_breadth_table(nodes=nodes, edges=edges)
    out = _details_json(envs, _node_name_index(nodes), nodes, edges, Path("/x"))
    assert "</" not in out and "<\\/script>" in out


def test_every_chip_has_a_detail_entry():
    html = _html()
    blob = _blob(html)
    chips = set(re.findall(r'class="tt-chip" data-node="([^"]+)"', html))
    assert chips and chips <= set(blob)
    # Direct micros under a theme that also has sub-themes are on the map.
    assert "theme:micro1" in chips and "theme:micro2" in chips


def test_card_chrome_is_bilingual_and_accessible():
    html = _html()
    assert 'id="tt-detail"' in html and 'aria-live="polite"' in html
    assert 'aria-controls="tt-detail"' in html
    assert "Watch instead" in html and "可替代观察" in html


def test_return_selection_identifies_rendered_occurrence_and_restores_actual_script(tmp_path):
    """Run the real card script across fresh documents, including a shared micro."""
    import subprocess
    import pandas as pd
    from bs4 import BeautifulSoup

    nodes, edges = _fixtures()
    edges = pd.concat([edges, _mk_edges(
        {"src": "theme:t2", "dst": "theme:micro1", "edge_id": "multi-parent"},
    )], ignore_index=True)
    (tmp_path / "site/basket").mkdir(parents=True)
    (tmp_path / "site/basket/grid.html").write_text("retained proxy fixture")
    html = render(REPO, ctx=compose(tmp_path, nodes=nodes, edges=edges))
    soup = BeautifulSoup(html, "html.parser")
    chips = [dict(c.attrs) for c in soup.select(".tt-chip[data-node]")]
    shared = [c for c in chips if c["data-node"] == "theme:micro1"]
    assert len(shared) == 2
    assert len({c.get("data-tt-selection") for c in shared}) == 2
    script = next(x.string for x in soup.find_all("script")
                  if x.string and "Micro-theme detail card (U2)" in x.string)
    assert any(i["href"] == "basket/grid.html"
               for i in _blob(html)["theme:micro1"]["instruments"])
    packet = {"script": script, "chips": chips, "data": _blob(html),
              "selected": chips.index(shared[1])}
    result = subprocess.run(["node", "-e", r"""
const vm = require('node:vm'), assert = require('node:assert/strict');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
function boot(url, ambiguous=false, data=input.data, mobile=false) {
  let active=null, replacements=0, scrollY=0, scrolls=0;
  const viewport=mobile?780:836;
  const body=new Set();
  class El {
    constructor(attrs={}) { this.attrs={...attrs}; this.children=[]; this.hidden=false; this.parentElement=null;
      this.classList={add(){},remove(){}}; }
    getAttribute(k){return this.attrs[k] ?? null;} setAttribute(k,v){this.attrs[k]=String(v);}
    appendChild(c){this.children.push(c); c.parentElement=this;return c;}
    get firstChild(){return this.children[0]||null;} removeChild(c){this.children.splice(this.children.indexOf(c),1);}
    focus(){active=this;}
    getBoundingClientRect(){
      if(this===card)return {top:mobile?420:96,bottom:mobile?viewport:410};
      // Model the actual desktop opening reflow and the phone's sheet overlap.
      const top=(mobile?680:body.has('tt-detail-open')?1007:680)-scrollY;
      return {top,bottom:top+24,height:24};
    }
    closest(q){if(q==='details')return this.tagName==='DETAILS'?this:this.parentElement?.closest(q)||null;
      if(q==='[data-close]')return this.attrs['data-close']!==undefined?this:null;
      return this.attrs['data-node']?this:null;}
  }
  const chips=input.chips.map(attrs=>{const c=new El(attrs), p=new El();p.tagName='DETAILS';p.open=false;c.parentElement=p;return c;});
  if(ambiguous)chips.push(new El({...chips[input.selected].attrs}));
  const fields={}; for(const k of ['name','paths','breadth','list','note','close'])fields['.tt-detail-'+k]=new El();
  fields['.tt-detail-close'].attrs['data-close']='';
  const card=new El();card.hidden=true;card.querySelector=q=>fields[q];
  card.querySelectorAll=q=>[new El(),new El()];
  const devents={},wevents={},location={href:url};
  const document={body:{classList:{add:k=>body.add(k),remove:k=>body.delete(k)}},getElementById:id=>id==='tt-detail-data'?{textContent:JSON.stringify(data)}:card,
    querySelectorAll:q=>chips,createElement:()=>new El(),createTextNode:t=>({textContent:t}),
    addEventListener:(k,f)=>{(devents[k]??=[]).push(f);}};
  const state={preserved:true};
  const history={state,replaceState(s,t,u){assert.equal(s,state);location.href=new URL(u,location.href).href;replacements++;},
    pushState(){throw Error('selection must not create a history entry');}};
  const window={location,history,innerWidth:mobile?390:1440,innerHeight:viewport,
    matchMedia:q=>({matches:mobile&&q==='(max-width: 560px)'}),
    scrollBy:({top,behavior})=>{assert.equal(behavior,'instant');scrollY+=top;scrolls++;},
    addEventListener:(k,f)=>{(wevents[k]??=[]).push(f);}};
  vm.runInNewContext(input.script,{document,window,URL});
  return {card,chips,fields,location,get active(){return active;},get replacements(){return replacements;},get scrolls(){return scrolls;},
    painted(){const rect=chips[input.selected].getBoundingClientRect();return rect.top>=0&&rect.bottom<=(mobile&&!card.hidden?420:viewport);},
    click(target){for(const f of devents.click||[])f({target});},
    event(k){for(const f of wevents[k]||[])f({type:k});}};
}
const original='https://macro.example/theme_tree.html?keep=1#branch';
let page=boot(original);assert.equal(page.card.hidden,true);
const selected=page.chips[input.selected];page.click(selected);
assert.equal(page.card.hidden,false);assert.equal(selected.getAttribute('aria-expanded'),'true');
assert.equal(page.active,page.fields['.tt-detail-close']);
const returnedURL=page.location.href;const parsed=new URL(returnedURL);
assert.equal(parsed.searchParams.get('keep'),'1');assert.equal(parsed.hash,'#branch');
assert.equal(parsed.searchParams.get('tt-selection'),selected.getAttribute('data-tt-selection'));
assert.equal(page.replacements,1);
page.event('mmx:shell-location');assert.equal(page.replacements,1);assert.equal(page.active,page.fields['.tt-detail-close']);
// A proxy navigation followed by Back creates a new frame at the retained URL.
page=boot(returnedURL);assert.equal(page.card.hidden,false);
assert.equal(page.chips[input.selected].getAttribute('aria-expanded'),'true');
assert.equal(page.chips.filter(c=>c.getAttribute('aria-expanded')==='true').length,1);
assert.equal(page.chips[input.selected].parentElement.open,true);
assert.equal(page.active,page.chips[input.selected]);assert.equal(page.replacements,0);
page.click(page.fields['.tt-detail-close']);assert.equal(page.card.hidden,true);
assert.equal(new URL(page.location.href).searchParams.has('tt-selection'),false);
assert.equal(new URL(page.location.href).searchParams.get('keep'),'1');
assert.equal(page.active,page.chips[input.selected]);assert.equal(page.replacements,1);
const duplicate=new URL(returnedURL);duplicate.searchParams.append('tt-selection','extra');
for(const bad of [original,original.replace('#branch','&tt-selection=missing#branch'),duplicate.href]){
  const neutral=boot(bad);assert.equal(neutral.card.hidden,true);assert.equal(neutral.replacements,0);
}
assert.equal(boot(returnedURL,true).card.hidden,true);
const absent={...input.data};delete absent[selected.getAttribute('data-node')];
assert.equal(boot(returnedURL,false,absent).card.hidden,true);
page=boot(returnedURL);page.location.href=original;page.event('popstate');assert.equal(page.card.hidden,true);
page.location.href=returnedURL;page.event('mmx:shell-location');assert.equal(page.card.hidden,false);
// The bridge preserves raw query bytes. The card owns only the selection key.
const query='?view=A%20B&view=~&view=%2b&%76iew=Keep+One&bad%ZZ=kept&flag&?tt-selection=unrelated&%2574t-selection=unrelated';
const root='https://macro.example/theme_tree.html';
const rawURL=root+query+'#branch';
const alt=input.chips.findIndex((attrs,i)=>i!==input.selected && attrs['data-node']===selected.getAttribute('data-node'));
const firstValue=input.chips[input.selected]['data-tt-selection'];
const altValue=input.chips[alt]['data-tt-selection'];
function assertSelectedURL(current,value) {
  assert.ok(current.href.startsWith(root+query+'&tt-selection='),current.href);
  const url=new URL(current.href);
  assert.deepEqual(url.searchParams.getAll('tt-selection'),[value]);
  assert.equal(url.hash,'#branch');
}
page=boot(rawURL);page.click(page.chips[input.selected]);
assertSelectedURL(page.location,firstValue);
page.click(page.chips[alt]);assertSelectedURL(page.location,altValue);
page.click(page.fields['.tt-detail-close']);assert.equal(page.location.href,rawURL);
assert.equal(page.replacements,3);

const encodedOwned=root+query+'&%74t-selection='+encodeURIComponent(firstValue)+'#branch';
page=boot(encodedOwned);assert.equal(page.active,page.chips[input.selected]);
assert.equal(page.replacements,0);
page.click(page.fields['.tt-detail-close']);assert.equal(page.location.href,rawURL);
page=boot(encodedOwned);page.click(page.chips[alt]);assertSelectedURL(page.location,altValue);
const duplicateOwned=encodedOwned.replace('#branch','&tt-selection=extra#branch');
page=boot(duplicateOwned);assert.equal(page.card.hidden,true);
page.click(page.chips[input.selected]);assertSelectedURL(page.location,firstValue);
page.click(page.fields['.tt-detail-close']);assert.equal(page.location.href,rawURL);
// Keep the occurrence painted after layout changes and behind no sheet.
for(const mobile of [false,true]){
  const entry=boot(original,false,input.data,mobile);assert.equal(entry.painted(),true);
  entry.click(entry.chips[input.selected]);assert.equal(entry.painted(),true);
  assert.equal(entry.scrolls,1);
  const back=boot(entry.location.href,false,input.data,mobile);
  assert.equal(back.active,back.chips[input.selected]);assert.equal(back.painted(),true);
  assert.equal(back.scrolls,1);
  back.event('mmx:shell-location');
  assert.equal(back.scrolls,1);assert.equal(back.replacements,0);
}
console.log('real rendered multi-parent selection: click, replace, fresh-frame return, close, neutral controls and bridge replay PASS');
"""], input=json.dumps(packet), capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def test_theme_hover_ignores_touch_compatibility_mouse_events():
    """Run the emitted hover handler for touch and bounded bilingual mouse hover."""
    import subprocess

    html = _html()
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    script = next(s for s in scripts if "Multi-parent tip on micro chips" in s)
    result = subprocess.run(["node", "-e", r"""
const {runInNewContext} = require('node:vm'), assert = require('node:assert/strict');
const script = require('node:fs').readFileSync(0, 'utf8');
const listeners = {};
let tip, tipWidth=270, lang='en';
const window={innerWidth:390,innerHeight:844};
const chip={closest:()=>chip,getAttribute:key=>({'data-tt-tip-en':'Two branches','data-tt-tip-zh':'两个分支'})[key]};
const document={
  createElement:()=>({style:{}, getBoundingClientRect:()=>({width:tipWidth})}),
  body:{appendChild:el=>{tip=el;}},
  documentElement:{getAttribute:()=>lang}, addEventListener:(type,fn)=>{listeners[type]=fn;},
};
runInNewContext(script,{document,window});
const emit=(type,pointerType,clientX=130)=>listeners[type]?.({target:chip,pointerType,clientX,clientY:450});
function assertHorizontalBounds(expectedLeft){
  const left=Number.parseFloat(tip.style.left);
  assert.equal(left,expectedLeft);
  assert(left>=8 && left+tipWidth<=window.innerWidth-8);
}
emit('pointerover','touch');emit('pointermove','touch');
emit('mouseover');emit('mousemove');
assert.equal(tip,undefined);
for(const [locale,text] of [['en','Two branches'],['zh','两个分支']]){
  lang=locale;
  emit('pointerover','mouse');emit('pointermove','mouse');
  assert.equal(tip.style.display,'block');assert.equal(tip.textContent,text);
  assertHorizontalBounds(8);
  emit('pointermove','mouse',389);assertHorizontalBounds(106);
  emit('pointermove','mouse',8);assertHorizontalBounds(21);
  emit('pointerout','mouse');assert.equal(tip.style.display,'none');
}
window.innerWidth=320;
emit('pointerover','mouse');assertHorizontalBounds(8);
emit('pointerout','mouse');assert.equal(tip.style.display,'none');
window.innerWidth=390;tipWidth=200;
emit('pointerover','mouse');assertHorizontalBounds(143);
emit('pointermove','mouse',133);assertHorizontalBounds(146);
emit('pointerout','mouse');assert.equal(tip.style.display,'none');
"""], input=script, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
