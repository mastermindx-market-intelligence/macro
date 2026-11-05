"""Checked Save uses its enqueue-time account through every asynchronous boundary.

Execute the actual incumbent WatchStore against its existing recording DB double.
No provider/account operation, held Plan test, source walk or new database is used.
"""
from pathlib import Path

import pytest

from tests.test_prophet_r7_wave_a_watchlist import _ws, _run, USER, LIST_ROW


@pytest.mark.parametrize('boundary', ['list', 'pre-read', 'insert', 'readback'])
@pytest.mark.parametrize('same_user', [False, True])
def test_checked_save_cannot_cross_an_account_lifetime(boundary, same_user):
    out = _ws(r"""
        var db = makeDb({watchlists:[LIST_ROW],watchlist_symbols:[]});
        var next = makeDb({watchlists:[],watchlist_symbols:[]});
        WS._setTestSession(USER, db.client);
        if (BOUNDARY !== 'list') WS._setTestLists({lists:[LIST_ROW]});
        var original = db.client.from, release, reads=0;
        db.client.from = function(table) {
          var api=original.call(db.client, table), then=api.then, kind='';
          var select=api.select, insert=api.insert;
          api.select=function(cols){kind='select';return select.call(api,cols);};
          api.insert=function(rows){kind='insert';return insert.call(api,rows);};
          api.then=function(yes,no){
            if(table==='watchlist_symbols' && kind==='select') reads++;
            var pause=(BOUNDARY==='list'&&table==='watchlists') ||
              (BOUNDARY==='pre-read'&&table==='watchlist_symbols'&&kind==='select'&&reads===1) ||
              (BOUNDARY==='insert'&&kind==='insert') ||
              (BOUNDARY==='readback'&&table==='watchlist_symbols'&&kind==='select'&&reads===2);
            if(!pause) return then.call(api,yes,no);
            return new Promise(function(resolve,reject){
              release=function(){then.call(api,resolve,reject);};
            }).then(yes,no);
          };
          return api;
        };
        var outcome=WS.symbols.saveChecked('L1',['VRT'],{decisions:{VRT:{en:'Original',zh:'原始'}}});
        (async function(){
          for(var n=0;n<20&&!release;n++) await wait(0);
          if(!release) throw Error('boundary not reached');
          WS._setTestSession(null,null);
          WS._setTestSession({id:SAME?'u1':'u2'},next.client);
          WS._setTestLists({lists:[{id:'NEW',name:'New owner'}],cloud:{}});
          release();
          var r=await outcome;
          OUT({state:r.state,reason:r.reason,names:r.names,list:r.listName,
            oldWrites:insertedSymbols(db,'L1'),newOps:next.ops.length,
            lists:WS.lists.all(),cloud:WS._testState().cloud,
            snapshots:__store['mdash.watchlist.saved_snap.v1']||null});
        })().catch(function(e){OUT({ERR:String(e.stack||e)});});
    """, {'USER': USER, 'LIST_ROW': LIST_ROW, 'BOUNDARY': boundary, 'SAME': same_user})
    assert 'ERR' not in out, out
    assert out['state'] == ('uncertain' if boundary in {'insert', 'readback'} else 'rejected')
    assert out['reason'] == 'stale-session'
    assert out['names'] == [] and out['list'] == ''
    assert out['newOps'] == 0
    assert out['lists'] == [{'id': 'NEW', 'name': 'New owner'}]
    assert out['snapshots'] is None
    assert 'L1' not in out['cloud']
    assert out['oldWrites'] == (['VRT'] if boundary in {'insert', 'readback'} else [])


def test_an_old_queued_save_does_not_adopt_the_next_account():
    out = _ws(r"""
        var db=makeDb({watchlists:[LIST_ROW],watchlist_symbols:[]}), release;
        WS._setTestSession(USER,db.client);WS._setTestLists({lists:[LIST_ROW]});
        var original=db.client.from;
        db.client.from=function(table){var api=original.call(db.client,table),then=api.then;
          api.then=function(yes,no){if(table!=='watchlist_symbols')return then.call(api,yes,no);
            return new Promise(function(resolve){release=function(){then.call(api,resolve,no);};}).then(yes,no);};return api;};
        var a=WS.symbols.saveChecked('L1',['VRT']);
        var b=WS.symbols.saveChecked('L1',['ADBE']);
        (async function(){for(var n=0;n<20&&!release;n++)await wait(0);
          var next=makeDb({watchlists:[LIST_ROW],watchlist_symbols:[]});
          WS._setTestSession({id:'u2'},next.client);release();
          OUT({a:await a,b:await b,newOps:next.ops.length,writes:insertedSymbols(db,'L1')});
        })().catch(function(e){OUT({ERR:String(e.stack||e)});});
    """, {'USER': USER, 'LIST_ROW': LIST_ROW})
    assert 'ERR' not in out, out
    assert out['a']['reason'] == out['b']['reason'] == 'stale-session'
    assert out['a']['state'] == out['b']['state'] == 'rejected'
    assert out['newOps'] == 0 and out['writes'] == []


def test_late_owned_list_read_never_populates_the_new_accounts_chooser():
    out = _ws(r"""
        var db=makeDb({watchlists:[LIST_ROW],watchlist_symbols:[]}),release;
        WS._setTestSession(USER,db.client);
        var original=db.client.from;
        db.client.from=function(table){var api=original.call(db.client,table),then=api.then;
          api.then=function(yes,no){return new Promise(function(resolve){release=function(){then.call(api,resolve,no);};}).then(yes,no);};return api;};
        var pending=WS.lists.refresh().then(function(){return 'wrong';},function(e){return e.message;});
        (async function(){for(var n=0;n<20&&!release;n++)await wait(0);
          WS._setTestSession({id:'u2'},makeDb({}).client);
          WS._setTestLists({lists:[{id:'NEW',name:'New owner'}]});release();
          OUT({error:await pending,lists:WS.lists.all()});
        })().catch(function(e){OUT({ERR:String(e.stack||e)});});
    """, {'USER': USER, 'LIST_ROW': LIST_ROW})
    assert out == {'error': 'stale-session', 'lists': [{'id': 'NEW', 'name': 'New owner'}]}


@pytest.mark.parametrize('client_state', ['ready', 'stalled', 'missing-config', 'no-host'])
def test_explicit_checked_host_does_not_start_legacy_sync_or_implicit_writes(client_state):
    module = str(Path(__file__).parents[1] / 'templates/watchstore.js')
    out = _run(r"""
        var db=makeDb({watchlists:[],watchlist_symbols:[]}), authCallback=null, reloads=0;
        document.getElementById=function(){return null;};
        document.querySelector=function(){return STATE==='no-host'?null:{};};
        global.SUPABASE_CFG=STATE==='missing-config'?null:{url:'https://test.invalid',anonKey:'public-test-config'};
        global.sessionStorage=localStorage;location.reload=function(){reloads++;};
        global.MDXAuth={hasSession:function(){return true;},onChange:function(cb){authCallback=cb;cb(USER,'INITIAL_SESSION');}};
        global.getSupabaseClient=function(){return STATE==='stalled'?new Promise(function(){}):Promise.resolve(db.client);};
        var WS=require(MODULE);WS._setCloudDeadlineMs(20);
        (__docListeners.DOMContentLoaded||[]).forEach(function(cb){cb();});
        wait(45).then(function(){
          (__winListeners.online||[]).forEach(function(cb){cb();});
          (__docListeners.visibilitychange||[]).forEach(function(cb){cb();});
          return WS.pull();
        }).then(function(){OUT({session:window.WatchStore.checkedSession(),ops:db.ops,reloads:reloads,bound:!!authCallback});});
    """, {'USER': USER, 'STATE': client_state, 'MODULE': module})
    assert out['ops'] == [] and out['reloads'] == 0
    assert out['bound'] is (client_state in {'ready', 'stalled'})
    assert out['session']['state'] == {'ready': 'ready', 'stalled': 'unavailable',
                                      'missing-config': 'unavailable', 'no-host': 'signed_out'}[client_state]
