"""A1B Portfolio fast-start acceptance over the real browser modules.

The tests node-shell ``portfolio_import.js`` and ``watchstore.js``. They pin the
commissioned grammar, stable identities, N-row atomic batch shape, exact receipt,
lost-response reconciliation, honest terminal failures, auth-generation binding,
local atomicity, and UUID-preserving anonymous-to-cloud fold. No fixture value is
printed by the product code under test.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "templates" / "portfolio_import.js"
UI = ROOT / "templates" / "portfolio_import_ui.js"
WATCHSTORE = ROOT / "templates" / "watchstore.js"
HAS_NODE = shutil.which("node") is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node not on PATH")

SHIM = r"""
var __sets = [], __store = {}, __throwSet = false;
global.localStorage = {
  getItem: function (k) { return Object.prototype.hasOwnProperty.call(__store, k) ? __store[k] : null; },
  setItem: function (k, v) { if (__throwSet) throw new Error('storage-denied'); __sets.push(k); __store[k] = String(v); },
  removeItem: function (k) { delete __store[k]; }
};
global.sessionStorage = { getItem:function(){return null;}, setItem:function(){}, removeItem:function(){} };
global.CustomEvent = function (t, o) { this.type = t; this.detail = o && o.detail; };
global.document = {
  readyState:'loading', hidden:false,
  documentElement:{ getAttribute:function(){return 'en';}, classList:{add:function(){},remove:function(){}} },
  getElementById:function(){return null;}, querySelector:function(){return null;}, querySelectorAll:function(){return [];},
  addEventListener:function(){}, removeEventListener:function(){}, dispatchEvent:function(){return true;},
  createElement:function(){return {style:{},classList:{add:function(){}}};}
};
global.window = global; window.addEventListener = function(){};
global.location = {hash:'',pathname:'/watchlist.html',search:'',origin:'https://x',reload:function(){}};
function OUT(value) { process.stdout.write(JSON.stringify(value)); }
"""


def _node(body: str, *, store: bool = False) -> dict:
    prefix = SHIM + "\nwindow.PortfolioImport = require(%s);\n" % json.dumps(str(CONTRACT))
    if store:
        prefix += "var WS = require(%s);\n" % json.dumps(str(WATCHSTORE))
    proc = subprocess.run(
        ["node", "-e", prefix + textwrap.dedent(body)],
        text=True,
        capture_output=True,
        timeout=40,
    )
    assert proc.returncode == 0, f"node failed:\nSTDERR:\n{proc.stderr}\nSTDOUT:\n{proc.stdout}"
    assert proc.stdout.strip(), f"node returned no receipt; stderr={proc.stderr}"
    return json.loads(proc.stdout)


def _ui_node(body: str, *, lang: str = "en") -> dict:
    source = UI.read_text(encoding="utf-8")
    hook = r"""
  window.__PFI_TEST__ = {
    setDraft: function (rows) {
      draft = { rows: JSON.parse(JSON.stringify(rows)), errors: [] };
      editErrors = []; step = 'review'; saving = false; completed = false; hardBlocked = false;
      render();
    },
    editRow: editRow,
    removeRow: removeRow,
    save: save,
    state: function () {
      return {
        draft: JSON.parse(JSON.stringify(draft)), saving: saving,
        completed: completed, hardBlocked: hardBlocked,
        rowsHtml: el('pfi_rows').innerHTML,
        status: el('pfi_status').textContent,
        saveDisabled: !!el('pfi_save').disabled,
        launchDisabled: !!el('pf_import').disabled
      };
    }
  };
"""
    assert source.rstrip().endswith("})();")
    instrumented = source.rstrip()[:-5] + hook + "})();"
    setup = r"""
var __elementIds = [
  'dlg-import','pf_import','pfi_status','pfi_errors','pfi_paste_view','pfi_review_view',
  'pfi_title','pfi_intro','pfi_grammar','pfi_paste','pfi_review','pfi_exact','pfi_back',
  'pfi_rows','pfi_count','pfi_save'
];
function classList() {
  var values={};
  return {add:function(k){values[k]=true;},remove:function(k){delete values[k];},contains:function(k){return !!values[k];}};
}
var __elements={};
__elementIds.forEach(function(id){
  __elements[id]={id:id,style:{},className:'',textContent:'',innerHTML:'',placeholder:'',disabled:false,
    classList:classList(),attributes:{},focus:function(){},querySelector:function(){return null;},
    addEventListener:function(){},setAttribute:function(k,v){this.attributes[k]=String(v);},
    getAttribute:function(k){return Object.prototype.hasOwnProperty.call(this.attributes,k)?this.attributes[k]:null;}};
});
global.document={
  readyState:'loading',activeElement:null,
  documentElement:{getAttribute:function(k){return k==='data-lang'?%s:null;},classList:classList()},
  getElementById:function(id){return __elements[id]||null;},
  addEventListener:function(){},dispatchEvent:function(){return true;}
};
window.document=global.document;
global.setTimeout=function(){return 0;};
eval(%s);
""" % (json.dumps(lang), json.dumps(instrumented))
    return _node(setup + "\n" + textwrap.dedent(body))


IDS = [
    "10000000-0000-4000-8000-000000000001",
    "10000000-0000-4000-8000-000000000002",
    "10000000-0000-4000-8000-000000000003",
    "10000000-0000-4000-8000-000000000004",
]


@needs_node
def test_frozen_grammar_preserves_nulls_coverage_and_duplicate_lots():
    out = _node(
        """
        var ids = %s, i = 0;
        var got = PortfolioImport.parse(
          'aapl\\nAAPL 10\\nMSFT 2 400.25\\n0700.HK 3 300 2026-02-28',
          {idFactory:function(){return ids[i++];}, isCovered:function(t){return t !== 'MSFT';}});
        OUT({rows:got.rows, errors:got.errors, valid:PortfolioImport.validate(got.rows)});
        """ % json.dumps(IDS)
    )
    assert out["errors"] == []
    assert [r["id"] for r in out["rows"]] == IDS
    assert out["rows"][0]["shares"] is None
    assert out["rows"][0]["entry_price"] is None
    assert out["rows"][0]["entry_date"] is None
    assert out["rows"][1]["entry_price"] is None
    assert out["rows"][2]["entry_date"] is None
    assert out["rows"][2]["coverage"] == "uncovered"
    assert "duplicate_ticker" in out["rows"][0]["warnings"]
    assert "duplicate_ticker" in out["rows"][1]["warnings"]
    assert out["valid"]["ok"] is True


@needs_node
def test_malformed_numeric_date_and_unsupported_syntax_stay_visible():
    out = _node(
        """
        var i=0, ids=%s;
        var got=PortfolioImport.parse([
          'GOOD', 'AAPL Infinity', 'MSFT NaN 1', 'NVDA 1 nope',
          'TSLA 1 2 2026-02-30', 'CASH', '$1000 AAPL', 'SPY 10%%',
          'QQQ target=25', 'AMD 1 2 2026-01-01 extra'
        ].join('\\n'), {idFactory:function(){return ids[i++];}});
        OUT({rows:got.rows.map(function(r){return r.ticker;}), codes:got.errors.map(function(e){return e.code;}), lines:got.errors.map(function(e){return e.line;})});
        """ % json.dumps(IDS)
    )
    assert out["rows"] == ["GOOD"]
    assert out["lines"] == list(range(2, 11))
    assert out["codes"] == [
        "invalid_shares", "invalid_shares", "invalid_price", "invalid_date",
        "unsupported_cash", "unsupported_dollar_allocation", "unsupported_percentage",
        "unsupported_target_allocation", "too_many_fields",
    ]


@needs_node
def test_review_edit_keeps_uuid_remove_is_explicit_and_owner_is_forbidden():
    out = _node(
        """
        var id=%s;
        var draft=PortfolioImport.parse('AAPL 1', {idFactory:function(){return id;}}).rows;
        var edited=PortfolioImport.edit(draft,id,{ticker:'msft',shares:'2.5',entry_price:'',entry_date:''});
        var removed=PortfolioImport.remove(edited.rows,id);
        var forbidden=PortfolioImport.validate([Object.assign({}, edited.rows[0], {user_id:'caller-owner'})]);
        OUT({id:edited.rows[0].id,ticker:edited.rows[0].ticker,shares:edited.rows[0].shares,
             price:edited.rows[0].entry_price,date:edited.rows[0].entry_date,
             remaining:removed.rows.length,forbidden:forbidden});
        """ % json.dumps(IDS[0])
    )
    assert out == {
        "id": IDS[0], "ticker": "MSFT", "shares": 2.5, "price": None,
        "date": None, "remaining": 0,
        "forbidden": {"ok": False, "code": "caller_owner_forbidden", "index": 0},
    }


@needs_node
def test_real_uuid_factory_and_finite_scientific_numeric_forms():
    out = _node(
        """
        var ids=[]; for(var i=0;i<32;i++) ids.push(PortfolioImport.randomUuid());
        var seq=0, parsed=PortfolioImport.parse('AAA .5 1e2\\nBBB -3 +4.25',
          {idFactory:function(){return ids[seq++];}});
        OUT({allUuid:ids.every(PortfolioImport.isUuid),unique:(new Set(ids)).size,
             errors:parsed.errors,values:parsed.rows.map(function(r){return [r.shares,r.entry_price];})});
        """
    )
    assert out["allUuid"] is True and out["unique"] == 32
    assert out["errors"] == [] and out["values"] == [[0.5, 100], [-3, 4.25]]


LOCAL_BATCH = [
    {"id": IDS[0], "ticker": "AAPL", "shares": None, "entry_price": None,
     "entry_date": None, "notes": None, "status": "open"},
    {"id": IDS[1], "ticker": "AAPL", "shares": None, "entry_price": None,
     "entry_date": None, "notes": None, "status": "open"},
]


@needs_node
def test_local_import_is_one_complete_book_write_and_keeps_duplicates():
    out = _node(
        """
        var before=[{id:'loc-old',ticker:'OLD',shares:1,entry_price:null,entry_date:null,notes:null,status:'open'}];
        WS.pfWrite(before); __sets=[];
        WS.portfolio.importBatch(%s).then(function(result){
          return WS.portfolio.list().then(function(rows){
            OUT({result:result.state,ok:result.ok,writes:__sets.length,ids:rows.map(function(r){return r.id;}),tickers:rows.map(function(r){return r.ticker;})});
          });
        });
        """ % json.dumps(LOCAL_BATCH),
        store=True,
    )
    assert out["ok"] is True and out["result"] == "saved"
    assert out["writes"] == 1
    assert out["ids"] == ["loc-old", IDS[0], IDS[1]]
    assert out["tickers"] == ["OLD", "AAPL", "AAPL"]


@needs_node
def test_local_storage_throw_preserves_previous_book_byte_for_byte():
    out = _node(
        """
        var before=JSON.stringify({v:1,rows:[{id:'loc-old',ticker:'OLD',shares:1,entry_price:null,entry_date:null,notes:null,status:'open'}]});
        __store['mdash.pf.v1']=before; __throwSet=true;
        WS.portfolio.importBatch(%s).then(function(result){
          OUT({ok:result.ok,state:result.state,unchanged:__store['mdash.pf.v1']===before});
        });
        """ % json.dumps(LOCAL_BATCH),
        store=True,
    )
    assert out == {"ok": False, "state": "local_write_failed", "unchanged": True}


@needs_node
def test_local_write_success_with_hostile_verify_mismatch_is_terminal_unknown_without_rollback():
    out = _node(
        """
        var key='mdash.pf.v1';
        var before=JSON.stringify({v:1,rows:[{id:'loc-old',ticker:'OLD',shares:1,entry_price:null,entry_date:null,notes:null,status:'open'}]});
        __store[key]=before;
        var wrote=false, actualGet=localStorage.getItem, actualSet=localStorage.setItem;
        localStorage.setItem=function(k,v){ actualSet(k,v); if(k===key) wrote=true; };
        localStorage.getItem=function(k){
          if(k===key && wrote) return before;
          return actualGet(k);
        };
        WS.portfolio.importBatch(%s).then(function(result){
          OUT({ok:result.ok,state:result.state,effect:result.effect,retryable:result.retryable,
               writeHappened:wrote,writes:__sets.length,storedChanged:__store[key]!==before});
        });
        """ % json.dumps(LOCAL_BATCH),
        store=True,
    )
    assert out == {
        "ok": False,
        "state": "local_verify_failed",
        "effect": "unknown",
        "retryable": False,
        "writeHappened": True,
        "writes": 1,
        "storedChanged": True,
    }


@needs_node
def test_inflight_save_freezes_model_visible_draft_and_exact_payload():
    out = _ui_node(
        """
        var rows=%s.map(function(row){return Object.assign({},row,{coverage:'covered',warnings:[]});});
        var resolveSave, captured=null, editCalls=0, removeCalls=0;
        var realEdit=PortfolioImport.edit, realRemove=PortfolioImport.remove;
        PortfolioImport.edit=function(){editCalls++;return realEdit.apply(null,arguments);};
        PortfolioImport.remove=function(){removeCalls++;return realRemove.apply(null,arguments);};
        var pending=new Promise(function(resolve){resolveSave=resolve;});
        window.WatchStore={portfolio:{importBatch:function(batch){captured=JSON.parse(JSON.stringify(batch));return pending;}}};
        __PFI_TEST__.setDraft(rows);
        var before=__PFI_TEST__.state();
        __PFI_TEST__.save();
        var locked=__PFI_TEST__.state();
        var rowHost={getAttribute:function(){return rows[0].id;}};
        __PFI_TEST__.editRow({value:'MSFT',closest:function(){return rowHost;},getAttribute:function(k){return k==='data-pfi-field'?'ticker':null;}});
        __PFI_TEST__.removeRow(rows[0].id);
        var attacked=__PFI_TEST__.state();
        resolveSave({ok:true,state:'saved',rows:captured});
        Promise.resolve().then(function(){return Promise.resolve();}).then(function(){
          var done=__PFI_TEST__.state();
          OUT({
            inputsLocked:(locked.rowsHtml.match(/<input[^>]* disabled/g)||[]).length,
            removesLocked:(locked.rowsHtml.match(/<button[^>]*data-pfi-remove[^>]* disabled/g)||[]).length,
            modelFrozen:JSON.stringify(before.draft)===JSON.stringify(attacked.draft),
            visibleFrozen:locked.rowsHtml===attacked.rowsHtml,
            exactPayload:JSON.stringify(captured)===JSON.stringify(before.draft.rows),
            editCalls:editCalls,removeCalls:removeCalls,
            completed:done.completed,saveDisabled:done.saveDisabled,
            finalVisibleFrozen:done.rowsHtml===locked.rowsHtml,status:done.status
          });
        });
        """ % json.dumps(LOCAL_BATCH)
    )
    assert out == {
        "inputsLocked": 8,
        "removesLocked": 2,
        "modelFrozen": True,
        "visibleFrozen": True,
        "exactPayload": True,
        "editCalls": 0,
        "removeCalls": 0,
        "completed": True,
        "saveDisabled": True,
        "finalVisibleFrozen": True,
        "status": "Saved. Refreshing your Portfolio…",
    }


@needs_node
@pytest.mark.parametrize(
    ("lang", "message"),
    [
        ("en", "This browser wrote the book, but could not verify the resulting Portfolio. Do not retry here. Reopen Portfolio and verify it before doing anything else."),
        ("zh", "本浏览器已写入账簿，但无法核实保存后的持仓状态。请勿在此重试；先重新打开持仓并核对，再进行其他操作。"),
    ],
)
def test_local_verify_failed_is_hard_blocked_with_honest_en_zh_copy(lang: str, message: str):
    out = _ui_node(
        """
        var rows=%s.map(function(row){return Object.assign({},row,{coverage:'covered',warnings:[]});});
        window.WatchStore={portfolio:{importBatch:function(){return Promise.resolve({ok:false,state:'local_verify_failed',effect:'unknown',retryable:false});}}};
        __PFI_TEST__.setDraft(rows); __PFI_TEST__.save();
        Promise.resolve().then(function(){return Promise.resolve();}).then(function(){OUT(__PFI_TEST__.state());});
        """ % json.dumps(LOCAL_BATCH),
        lang=lang,
    )
    assert out["hardBlocked"] is True
    assert out["saveDisabled"] is True and out["launchDisabled"] is True
    assert out["status"] == message
    assert out["rowsHtml"].count('disabled aria-disabled="true"') == 10


CLOUD_HELPER = r"""
function makeClient(mode, initial) {
  var state=(initial||[]).map(function(r){return Object.assign({},r);}), inserts=[], tables=[];
  function from(table) {
    tables.push(table);
    var action='select', payload=null, filters={}, ids=null, selected='';
    var q={
      select:function(s){selected=s;return q;}, eq:function(k,v){filters[k]=v;return q;},
      in:function(k,v){ids=v.slice();return q;}, order:function(){return q;},
      insert:function(rows){action='insert';payload=rows.map(function(r){return Object.assign({},r);});return q;},
      then:function(resolve,reject){
        Promise.resolve().then(function(){
          if(action==='select'){
            var data=state.filter(function(r){
              return (!filters.user_id || r.user_id===filters.user_id) && (!ids || ids.indexOf(r.id)>=0);
            }).map(function(r){return Object.assign({},r);});
            if(mode==='reread_fail' && inserts.length && !ids) return {data:null,error:{code:'READ_DOWN'}};
            if(mode==='preflight_down' && !inserts.length && ids) return {data:null,error:{code:'READ_DOWN'}};
            if(mode==='lost_reconcile_down' && inserts.length && ids) return {data:null,error:{code:'RECONCILE_DOWN'}};
            return {data:data,error:null};
          }
          inserts.push(payload.map(function(r){return Object.assign({},r);}));
          if(mode==='rejected') return {data:null,error:{code:'CHECK_REJECTED'}};
          if(mode==='auth_flip') { state=state.concat(payload); WS.onAuthUser(null); return {data:payload,error:null}; }
          if(mode==='lost_zero_once' && inserts.length===1) throw new Error('response-lost');
          if(mode==='lost_zero_always') throw new Error('response-lost');
          if(mode==='lost_partial_apply') { state=state.concat(payload.slice(0,1)); throw new Error('response-lost'); }
          if(mode==='lost_reconcile_down') { state=state.concat(payload); throw new Error('response-lost'); }
          state=state.concat(payload);
          if(mode==='lost_apply') throw new Error('response-lost');
          if(mode==='partial_receipt') return {data:payload.slice(0,1),error:null};
          if(mode==='wrong_owner_receipt') return {data:payload.map(function(r){return Object.assign({},r,{user_id:'owner-b'});}),error:null};
          return {data:payload.map(function(r){return Object.assign({},r);}),error:null};
        }).then(resolve,reject);
      }
    }; return q;
  }
  return {from:from,state:function(){return state.slice();},inserts:inserts,tables:tables};
}
function runCloud(mode, initial, batch) {
  var client=makeClient(mode,initial||[]);
  WS._setTestSession({id:'owner-a',email:'a@test'},client,false);
  return WS.portfolio.list().then(function(){
    return WS.portfolio.importBatch(batch).then(function(result){
      return {result:result,calls:client.inserts,state:client.state(),tables:client.tables};
    });
  });
}
"""


def _cloud(mode: str, initial: list[dict] | None = None, batch: list[dict] | None = None) -> dict:
    return _node(
        CLOUD_HELPER + "\nrunCloud(%s,%s,%s).then(OUT);" % (
            json.dumps(mode), json.dumps(initial or []), json.dumps(batch or LOCAL_BATCH)
        ),
        store=True,
    )


@needs_node
def test_cloud_save_is_one_n_row_insert_with_session_owner_and_exact_reread():
    out = _cloud("exact")
    assert out["result"]["ok"] is True and out["result"]["state"] == "saved"
    assert len(out["calls"]) == 1 and len(out["calls"][0]) == 2
    assert {r["user_id"] for r in out["calls"][0]} == {"owner-a"}
    assert [r["id"] for r in out["calls"][0]] == IDS[:2]
    assert all("updated_at" not in r for r in out["calls"][0])
    assert out["tables"] and set(out["tables"]) == {"portfolio_positions"}


@needs_node
def test_lost_response_all_exact_reconciles_without_second_insert():
    out = _cloud("lost_apply")
    assert out["result"]["ok"] is True
    assert len(out["calls"]) == 1
    assert len(out["state"]) == 2


@needs_node
def test_lost_response_zero_retries_once_with_identical_ids():
    out = _cloud("lost_zero_once")
    assert out["result"]["ok"] is True
    assert len(out["calls"]) == 2
    assert [r["id"] for r in out["calls"][0]] == [r["id"] for r in out["calls"][1]] == IDS[:2]
    assert len(out["state"]) == 2


@needs_node
def test_partial_existing_batch_stops_before_insert_mutation_check():
    existing = [dict(LOCAL_BATCH[0], user_id="owner-a")]
    out = _cloud("exact", existing)
    assert out["result"]["ok"] is False and out["result"]["state"] == "some"
    assert out["calls"] == []


@needs_node
def test_same_id_different_semantics_is_a_conflict_before_insert():
    existing = [dict(LOCAL_BATCH[0], user_id="owner-a", shares=999)]
    out = _cloud("exact", existing, [LOCAL_BATCH[0]])
    assert out["result"]["ok"] is False and out["result"]["state"] == "conflict"
    assert out["calls"] == []


@needs_node
def test_partial_receipt_never_claims_saved_or_blind_retries_mutation_check():
    out = _cloud("partial_receipt")
    assert out["result"]["ok"] is False
    assert out["result"]["state"] == "ambiguous_receipt"
    assert len(out["calls"]) == 1


@needs_node
def test_wrong_owner_receipt_never_claims_saved_even_if_owner_read_is_exact():
    out = _cloud("wrong_owner_receipt")
    assert out["result"]["ok"] is False
    assert out["result"]["state"] == "ambiguous_receipt"
    assert len(out["calls"]) == 1


@needs_node
def test_lost_response_partial_reconcile_stops_without_retry():
    out = _cloud("lost_partial_apply")
    assert out["result"]["ok"] is False and out["result"]["state"] == "some"
    assert len(out["calls"]) == 1 and len(out["state"]) == 1


@needs_node
def test_lost_response_unavailable_reconcile_is_effect_unknown_and_no_retry():
    out = _cloud("lost_reconcile_down")
    assert out["result"]["ok"] is False and out["result"]["state"] == "effect_unknown"
    assert out["result"]["retryable"] is False and len(out["calls"]) == 1


@needs_node
def test_unavailable_preflight_is_known_zero_effect_and_retryable():
    out = _cloud("preflight_down")
    assert out["result"] == {
        "ok": False,
        "state": "unavailable",
        "effect": "none",
        "retryable": True,
    }
    assert out["calls"] == []


@needs_node
def test_second_lost_response_after_proven_zero_stops_effect_unknown():
    out = _cloud("lost_zero_always")
    assert out["result"]["ok"] is False and out["result"]["state"] == "effect_unknown"
    assert out["result"]["retryable"] is False and len(out["calls"]) == 2
    assert out["state"] == []


@needs_node
def test_definite_rejection_is_zero_effect_and_retryable_same_draft():
    out = _cloud("rejected")
    assert out["result"]["ok"] is False and out["result"]["state"] == "rejected"
    assert out["state"] == [] and len(out["calls"]) == 1


@needs_node
def test_acknowledged_write_without_authoritative_reread_is_not_saved():
    out = _cloud("reread_fail")
    assert out["result"]["ok"] is False
    assert out["result"]["state"] == "authoritative_reread_failed"
    assert out["result"]["effect"] == "confirmed"
    assert len(out["state"]) == 2


@needs_node
def test_auth_generation_change_suppresses_success_and_never_changes_owner():
    out = _cloud("auth_flip")
    assert out["result"]["ok"] is False and out["result"]["state"] == "stale_auth"
    assert {r["user_id"] for r in out["calls"][0]} == {"owner-a"}


@needs_node
def test_uuid_fold_preserves_two_exact_duplicate_lots_and_is_idempotent():
    out = _node(
        CLOUD_HELPER + """
        var batch=%s, client=makeClient('exact',[]);
        __store['mdash.pf.v1']=JSON.stringify({v:1,rows:batch});
        WS._setTestSession({id:'owner-a',email:'a@test'},client,false);
        WS.portfolio.list().then(function(){ return WS.foldLocalPortfolio(); }).then(function(){
          return WS.foldLocalPortfolio();
        }).then(function(){
          OUT({calls:client.inserts.length,ids:client.state().map(function(r){return r.id;}),
               tickers:client.state().map(function(r){return r.ticker;}),local:__store['mdash.pf.v1']||null,
               marker:__store['mdash.watchstore.pf_folded.v1']||null});
        });
        """ % json.dumps(LOCAL_BATCH),
        store=True,
    )
    assert out["calls"] == 1
    assert out["ids"] == IDS[:2]
    assert out["tickers"] == ["AAPL", "AAPL"]
    assert out["local"] is None and out["marker"] == "1"


def test_page_wires_pure_contract_before_store_and_ui_after_portfolio():
    page = (ROOT / "templates" / "watchlist.html.j2").read_text(encoding="utf-8")
    assert 'id="pf_import"' in page and 'id="dlg-import"' in page
    # RI07 finding 1: the I07R stamp moved watchstore.js to ?v=12 (watchlist.html.j2);
    # portfolio.js has not been re-stamped since v11, so its pin stays.
    assert 'src="watchstore.js?v=12"' in page and 'src="portfolio.js?v=11"' in page
    assert 'src="portfolio_import_ui.js?v=2"' in page
    assert page.index('src="portfolio_import.js') < page.index('src="watchstore.js')
    assert page.index('src="portfolio.js') < page.index('src="portfolio_import_ui.js')
    ui = (ROOT / "templates" / "portfolio_import_ui.js").read_text(encoding="utf-8")
    assert "WatchStore.lists" not in ui and "WatchStore.symbols" not in ui


def test_ui_async_review_and_terminal_retry_guards_stay_pinned_mutation_check():
    ui = (ROOT / "templates" / "portfolio_import_ui.js").read_text(encoding="utf-8")
    disabled = "if (button) { button.disabled = true; button.textContent = L('reviewing'); }"
    reenabled = "if (button) button.disabled = false;"
    assert disabled in ui and reenabled in ui
    assert ui.index(disabled) < ui.index(reenabled)
    assert "if (saving || completed || hardBlocked" in ui
    assert "el('pf_import').disabled = true" in ui


def test_narrow_modal_owns_the_viewport_over_the_brain_launcher():
    css = (ROOT / "templates" / "portfolio_import.css").read_text(encoding="utf-8")
    assert "html.mx5-dlg-lock #mmb-boot { visibility:hidden; }" in css


def test_import_assets_have_shipping_site_pairs():
    for name in ("portfolio_import.css", "portfolio_import.js", "portfolio_import_ui.js", "watchstore.js", "portfolio.js"):
        assert (ROOT / "site" / name).read_bytes() == (ROOT / "templates" / name).read_bytes()
    assert (ROOT / "site" / "watchlist.html").is_file()


@needs_node
def test_a1b_post_save_badge_refresh_is_same_page_and_fail_closed():
    watchlist = ROOT / "templates" / "watchlist.js"
    script = r"""
var __pfCount = 13;
var __pfNode = {textContent:''}, __wlNode = {textContent:''};
var __modes = {
  querySelector:function(sel){
    if(sel === '[data-count="pf"]') return __pfNode;
    if(sel === '[data-count="wl"]') return __wlNode;
    return null;
  },
  querySelectorAll:function(){return [];}
};
global.localStorage = {getItem:function(){return null;},setItem:function(){},removeItem:function(){}};
global.CustomEvent = function(t,o){this.type=t;this.detail=o&&o.detail;};
global.document = {
  readyState:'loading',
  documentElement:{getAttribute:function(){return 'en';},setAttribute:function(){},classList:{add:function(){},remove:function(){}}},
  getElementById:function(id){return id === 'ws_modes' ? __modes : null;},
  querySelector:function(){return null;},querySelectorAll:function(){return [];},
  addEventListener:function(){},removeEventListener:function(){},dispatchEvent:function(){return true;},
  createElement:function(){return {style:{},classList:{add:function(){}}};}
};
global.window = global; window.addEventListener = function(){};
global.location = {hash:'',pathname:'/watchlist.html',search:'',origin:'https://x'};
window.PF = {count:function(){return __pfCount;}};
require(%s);
window.WS.refreshModeCounts();
var before = __pfNode.textContent;
__pfCount = 16; window.WS.refreshModeCounts();
var afterSave = __pfNode.textContent;
__pfCount = 13; window.WS.refreshModeCounts();
var afterCleanup = __pfNode.textContent;
__pfCount = null; window.WS.refreshModeCounts();
var unknown = __pfNode.textContent;
window.PF = undefined; window.WS.refreshModeCounts();
process.stdout.write(JSON.stringify({before:before,afterSave:afterSave,afterCleanup:afterCleanup,unknown:unknown,noPf:__pfNode.textContent}));
""" % json.dumps(str(watchlist))
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, f"node failed:\nSTDERR:\n{proc.stderr}\nSTDOUT:\n{proc.stdout}"
    assert json.loads(proc.stdout) == {
        "before": "13",
        "afterSave": "16",
        "afterCleanup": "13",
        "unknown": "—",
        "noPf": "—",
    }


def test_a1b_badge_refresh_follows_authoritative_rows_and_keeps_shipping_pairs():
    portfolio = (ROOT / "templates" / "portfolio.js").read_text(encoding="utf-8")
    # Anchor inside the enclosing function body, not an unanchored whole-file
    # `.index()` — `rows = newRows;` / `ensureIndex().then(render);` each occur
    # twice (reload() and onAuth() share the exact same two lines), so searching
    # the whole file would silently bind to whichever occurrence sorts first by
    # accident of source order rather than to the reload() reread this test names.
    reload_start = portfolio.index("function reload(afterWrite)")
    next_fn = portfolio.index("function onAuth(", reload_start)
    reload_body = portfolio[reload_start:next_fn]
    assign = reload_body.index("rows = newRows;")
    refresh = reload_body.index("window.WS.refreshModeCounts", assign)
    later_render = reload_body.index("ensureIndex().then(render);", assign)
    assert assign < refresh < later_render
    watchlist = (ROOT / "templates" / "watchlist.js").read_text(encoding="utf-8")
    assert "function refreshModeCounts(" in watchlist
    assert "refreshModeCounts: refreshModeCounts" in watchlist
    assert (ROOT / "site" / "watchlist.js").read_bytes() == (ROOT / "templates" / "watchlist.js").read_bytes()
    assert (ROOT / "site" / "portfolio.js").read_bytes() == (ROOT / "templates" / "portfolio.js").read_bytes()


# #6510: actual complete controllers, with explicit DOM/store boundary doubles.
# Retain source-clock, identity, generation and persistence owners unchanged.
BADGE_AUTH_HARNESS = r"""
'use strict';
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const markup = fs.readFileSync(path.join(ROOT,'templates/watchlist.html.j2'),'utf8');
const actualIds = new Set([...markup.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]));
for(const id of ['ws_modes','ws_sec_hold','tbl_pf','pf_rowcount','pf_scope','pf_readbanner','pf_err_inline']) assert(actualIds.has(id), 'actual template is missing '+id);
for(const count of ['pf','wl']) assert(markup.includes('data-count="'+count+'"'), 'actual template count span is missing');
// Assert controller order, not a hard-coded version that blocks later asset stamps.
const scripts=[...markup.matchAll(/<script\s+src="([^"?]+)(?:\?[^"\s]*)?"/g)].map(m=>m[1]);
const ordered=['market_books.js','portfolio_state.js','watchlist.js','portfolio.js'].map(s=>scripts.indexOf(s));
assert(ordered.every((n,i)=>n>=0&&(!i||n>ordered[i-1])), 'actual controller order changed');

function deferred() { let resolve, reject; const promise=new Promise((a,b)=>{resolve=a;reject=b;}); return {promise,resolve,reject}; }
function setup({ portfolioSource, lang='en', reversed=false, ps=true }={}) {
  const nodes={}, listeners={}, windowListeners={}, reads=[], events=[], network=[];
  const allowed=new Set(['ws_modes','ws_sec_hold','tbl_pf','pf_rowcount','pf_scope','pf_readbanner','pf_err_inline','pf_add','pf_import'].filter(id=>actualIds.has(id)).concat(['__count_pf','__count_wl']));
  function node(id) {
    if (!allowed.has(id)) return null;
    return nodes[id] ||= { id,innerHTML:'',textContent:'',style:{},value:'',className:'',_attrs:{},
      classList:{contains(){return false},add(){},remove(){},toggle(){}},
      setAttribute(k,v){this._attrs[k]=String(v)},getAttribute(k){return this._attrs[k]??null},
      querySelector(sel){const m=/\[data-count="([a-z]+)"\]/.exec(sel);return m?node('__count_'+m[1]):null},
      querySelectorAll(){return []},addEventListener(){},focus(){} };
  }
  const doc={ readyState:'loading',hidden:false,
    documentElement:{_attrs:{'data-lang':lang},getAttribute(k){return this._attrs[k]??null},setAttribute(k,v){this._attrs[k]=v},classList:{add(){},remove(){}}},
    getElementById:node,querySelector(){return null},querySelectorAll(){return []},
    addEventListener(k,fn){(listeners[k] ||= []).push(fn)},removeEventListener(){},
    dispatchEvent(e){events.push({type:e.type,detail:e.detail});for(const fn of [...(listeners[e.type]||[])])fn(e);return true},
    createElement(){return {style:{},classList:{add(){}},setAttribute(){}}},
  };
  let uid='A', state={authority:'cloud',state:'ready',last_good_at:null,warning:null};
  const storage=new Map();
  const ctx={console,Promise,Date,Intl,URL,Map,Set,Number,String,Math,JSON,Error,document:doc,
    localStorage:{getItem(k){return storage.get(k)??null},setItem(k,v){storage.set(k,String(v))},removeItem(k){storage.delete(k)}},
    CustomEvent:function(type,o){this.type=type;this.detail=o?.detail},
    location:{hash:'',pathname:'/watchlist.html',search:'',origin:'https://fixture.invalid'},
    setTimeout,clearTimeout,
    fetch(...args){network.push(args);return Promise.reject(new Error('network forbidden'))},
    addEventListener(k,fn){(windowListeners[k] ||= []).push(fn)},
    MDXAuth:{user(){return uid?{id:uid}:null}},
    WatchStore:{user(){return uid?{id:uid}:null},portfolio:{list(){const d=deferred();reads.push(d);return d.promise},readState(){return state}},lists:{all(){return [{id:'L1'},{id:'L2'},{id:'L3'},{id:'L4'},{id:'L5'},{id:'L6'},{id:'L7'}]}}}
  };
  ctx.window=ctx;vm.createContext(ctx);
  const source=f=>fs.readFileSync(path.join(ROOT,'templates',f),'utf8');
  for (const f of ['market_books.js',...(ps?['portfolio_state.js']:[]),...(reversed?['portfolio.js','watchlist.js']:['watchlist.js','portfolio.js'])])
    vm.runInContext(f==='portfolio.js'&&portfolioSource?portfolioSource:source(f),ctx,{filename:f});
  doc.readyState='interactive'; doc.dispatchEvent(new ctx.CustomEvent('DOMContentLoaded'));
  const snap=()=>({count:ctx.PF.count(),badge:node('__count_pf').textContent,watchBadge:node('__count_wl').textContent,
    rows:(node('tbl_pf').innerHTML.match(/class="pfx-row(?:[ "])/g)||[]).length,rowcount:node('pf_rowcount').innerHTML,
    readState:ctx.PF.readState().state,table:node('tbl_pf').innerHTML,banner:node('pf_readbanner').textContent,error:node('pf_err_inline').textContent,network:network.length});
  return {ctx,doc,reads,events,snap,setState(x){state=x},auth(id){uid=id;doc.dispatchEvent(new ctx.CustomEvent('wl-auth',{detail:{user:uid?{id:uid}:null}}))},
    event(type,detail){doc.dispatchEvent(new ctx.CustomEvent(type,{detail}))}, async flush(){for(let i=0;i<12;i++)await Promise.resolve()},
    resolve(i,rows,nextState){if(nextState)state=nextState;reads[i].resolve(rows)},reject(i){reads[i].reject(new Error('synthetic read failure'))} };
}
function rows(n,prefix='T') { return Array.from({length:n},(_,i)=>({id:prefix+i,ticker:prefix+String(i).padStart(2,'0'),shares:1,entry_price:10,status:'open'})); }
const GOOD={authority:'cloud',state:'ready',last_good_at:'2026-11-05T00:00:00Z',warning:null};
const ERROR={authority:'cloud',state:'error',last_good_at:null,warning:'read-failed'};
const DEGRADED={authority:'cloud',state:'degraded',last_good_at:'2026-11-05T00:00:00Z',warning:'cloud-unavailable'};
function eq(h,n){const s=h.snap();assert.equal(s.count,n,'canonical count');assert.equal(s.badge,n===null?'—':String(n),'mode badge');assert.equal(s.watchBadge,'7','watchlist count remains separate');assert.equal(s.network,0,'no network');}
async function known(h,n=13){h.resolve(0,rows(n),GOOD);await h.flush();h.ctx.WS.render();eq(h,n);}
const cases={
 async initial_read(h){eq(h,null);h.resolve(0,rows(13),GOOD);await h.flush();eq(h,13);assert.equal(h.snap().rows,13);},
 async confirmed_import_reread(h){await known(h);h.event('pf-import-state',{state:'saved'});h.resolve(1,rows(16),GOOD);await h.flush();eq(h,16);assert.equal(h.snap().rows,16);},
 async cleanup_reread(h){await known(h);h.event('pf-import-state',{state:'saved'});h.resolve(1,rows(16),GOOD);await h.flush();h.event('pf-folded');h.resolve(2,rows(13),GOOD);await h.flush();eq(h,13);assert.equal(h.snap().rows,13);},
 async identity_loading(h){await known(h);h.auth('B');eq(h,null);assert.equal(h.snap().table,'');assert.equal(h.snap().readState,'loading');},
 async identity_success(h){await known(h);h.auth('B');h.resolve(1,rows(2,'B'),GOOD);await h.flush();eq(h,2);assert.equal(h.snap().rows,2);assert(!h.snap().table.includes('T12'));},
 async identity_empty(h){await known(h);h.auth('B');h.resolve(1,[],GOOD);await h.flush();eq(h,0);assert.equal(h.snap().rows,0);},
 async identity_null_error(h){await known(h);h.auth('B');h.resolve(1,null,ERROR);await h.flush();eq(h,null);assert.equal(h.snap().readState,'error');assert.equal(h.snap().table,'');},
 async identity_rejected_read(h){await known(h);h.auth('B');h.reject(1);await h.flush();eq(h,null);assert.equal(h.snap().readState,'error');},
 async initial_null_error(h){h.resolve(0,null,ERROR);await h.flush();eq(h,null);assert.equal(h.snap().readState,'error');},
 async delayed_old_identity(h){await known(h);h.auth('B');h.auth('C');h.resolve(2,rows(3,'C'),GOOD);await h.flush();h.resolve(1,rows(99,'B'),GOOD);await h.flush();eq(h,3);assert.equal(h.snap().rows,3);},
 async same_identity_double_event(h){await known(h);h.auth('A');h.auth('A');h.resolve(2,rows(4),GOOD);await h.flush();h.resolve(1,rows(88),GOOD);await h.flush();eq(h,4);},
 async closed_and_blank_filtered(h){h.resolve(0,[...rows(3),{id:'closed',ticker:'CLOSED',status:'closed'},{id:'empty',ticker:'',status:'open'}],GOOD);await h.flush();eq(h,3);assert.equal(h.snap().rows,3);},
 async older_reload_cannot_overwrite(h){await known(h);h.event('pf-import-state',{state:'saved'});h.event('pf-import-state',{state:'saved'});h.resolve(2,rows(16),GOOD);await h.flush();h.resolve(1,rows(14),GOOD);await h.flush();eq(h,16);assert.equal(h.snap().rows,16);},
 async degraded_last_good_preserved(h){await known(h);h.event('pf-folded');h.resolve(1,rows(13),DEGRADED);await h.flush();eq(h,13);assert.equal(h.snap().readState,'degraded');assert(h.snap().banner.length>0);},
 async failed_reread_keeps_last_good(h){await known(h);h.event('pf-folded');h.reject(1);await h.flush();eq(h,13);assert.equal(h.snap().readState,'error');assert(h.snap().banner.length>0);},
 async import_failed_does_not_read(h){await known(h);h.event('pf-import-state',{state:'failed'});await h.flush();eq(h,13);assert.equal(h.reads.length,1);},
 async later_ws_render_cannot_restore_old_count(h){await known(h);h.auth('B');h.resolve(1,rows(2,'B'),GOOD);await h.flush();h.ctx.WS.render();eq(h,2);assert.equal(h.snap().rows,2);},
};

cases.sign_out_and_in = async function(h) {
  await known(h);
  h.setState({...GOOD,authority:'local',state:'loading'}); h.auth(null);
  assert.equal(h.snap().count,null); assert.equal(h.snap().badge,'—'); assert.equal(h.snap().watchBadge,'');
  h.resolve(1,rows(5,'LOCAL'),{...GOOD,authority:'local'}); await h.flush();
  assert.equal(h.snap().count,5); assert.equal(h.snap().badge,'5'); assert.equal(h.snap().watchBadge,'');
  h.auth('B'); eq(h,null); h.resolve(2,rows(2,'B'),GOOD); await h.flush(); eq(h,2);
};
cases.optional_painter_absent = async function(h) {
  delete h.ctx.WS.refreshModeCounts;
  h.resolve(0,rows(3),GOOD); await h.flush(); assert.equal(h.snap().count,3);
  h.auth('B'); h.resolve(1,rows(2),GOOD); await h.flush(); assert.equal(h.snap().count,2);
  assert.equal(h.snap().network,0);
};

"""

BADGE_AUTH_SCENARIOS = ['initial_read', 'confirmed_import_reread', 'cleanup_reread', 'identity_loading', 'identity_success', 'identity_empty', 'identity_null_error', 'identity_rejected_read', 'initial_null_error', 'delayed_old_identity', 'same_identity_double_event', 'closed_and_blank_filtered', 'older_reload_cannot_overwrite', 'degraded_last_good_preserved', 'failed_reread_keeps_last_good', 'import_failed_does_not_read', 'later_ws_render_cannot_restore_old_count', 'sign_out_and_in', 'optional_painter_absent']

@needs_node
@pytest.mark.parametrize("lang", ["en", "zh"])
@pytest.mark.parametrize("has_state_module", [True, False])
@pytest.mark.parametrize("scenario", BADGE_AUTH_SCENARIOS)
def test_portfolio_badge_lifecycle(scenario, lang, has_state_module):
    script = "const ROOT = " + json.dumps(str(ROOT)) + ";\n" + BADGE_AUTH_HARNESS
    script += "\nconst options = " + json.dumps({"lang": lang, "ps": has_state_module}) + ";\n"
    script += "const scenario = " + json.dumps(scenario) + ";\n"
    script += "(async () => { await cases[scenario](setup(options)); })().catch(e => { console.error(e); process.exitCode = 1; });"
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, f"{scenario}:\n{proc.stderr}\n{proc.stdout}"


def test_portfolio_badge_auth_shipping_pair_and_version():
    import re
    assert (ROOT / "templates/portfolio.js").read_bytes() == (ROOT / "site/portfolio.js").read_bytes()
    for path in ("templates/watchlist.html.j2", "site/watchlist.html"):
        markup = (ROOT / path).read_text(encoding="utf-8")
        stamp = re.search(r'portfolio\.js\?v=(\d+)', markup)
        assert stamp and int(stamp.group(1)) >= 13
