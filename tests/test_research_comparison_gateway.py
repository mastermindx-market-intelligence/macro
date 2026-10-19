"""Actual gateway dispatch in isolation: no product model/provider call."""
import ast, os, types
from pathlib import Path
from unittest.mock import Mock
import pytest

ROOT=Path(os.environ.get('I03_SOURCE_ROOT',Path(__file__).parents[1]))
def dispatch(monkeypatch,tier='pro',status='active'):
    file=ROOT/'engine/neuralweb/brain_gateway.py'
    node=next(n for n in ast.parse(file.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='_dispatch_brain_tool')
    ns={'Path':Path,'_BRAIN_TOOLS':{'search_research'},'_BRAIN_ONLY_TOOLS':{'search_research'},'_BRAIN_INTERNALS_TOOLS':set(),
        '_resolve_tier':lambda user,**kw:{'tier':tier,'status':status},'normalize_tier':lambda x:x,'log':Mock()}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(file),'exec'),ns)
    spy=Mock(return_value={'marker':'synthetic-dispatch'})
    module=types.ModuleType('engine.neuralweb');module.brain_market_intel=types.SimpleNamespace(search_research=spy)
    monkeypatch.setitem(__import__('sys').modules,'engine.neuralweb',module)
    return ns['_dispatch_brain_tool'],spy

def call(fn,user='member',**params):return fn('search_research',{'query':'','mode':' COMPARE ','comparison':{'action':'prepare','left':{'report_id':'left'},'right':{'report_id':'right'}},**params},Path('/synthetic'),Path('/synthetic'),'',user_id=user)

def test_compare_essential_denied_before_private_dispatch(monkeypatch):
    fn,spy=dispatch(monkeypatch,tier='essential')
    assert call(fn)['error']=='pro_required'
    spy.assert_not_called()

def test_compare_guest_and_inactive_denied(monkeypatch):
    fn,spy=dispatch(monkeypatch)
    assert call(fn,user='')['error']=='essential_required';spy.assert_not_called()
    fn,spy=dispatch(monkeypatch,status='cancelled')
    assert call(fn)['error']=='essential_required';spy.assert_not_called()

def test_compare_uses_only_server_owned_context(monkeypatch):
    fn,spy=dispatch(monkeypatch)
    assert call(fn)=={'marker':'synthetic-dispatch'}
    assert spy.call_args.kwargs['mode']=='compare'
    assert spy.call_args.kwargs['user_ctx']=={'user_id':'member'}
    assert spy.call_args.kwargs['comparison']['action']=='prepare'
    for key in ('user_ctx','user_id','entitlement','scopes','basis','caller_context'):
        spy.reset_mock();assert call(fn,**{key:'injected'})['error']=='invalid_request';spy.assert_not_called()

def test_existing_report_and_search_dispatch_are_preserved(monkeypatch):
    fn,spy=dispatch(monkeypatch,tier='essential')
    assert call(fn,mode='report')['error']=='pro_required';spy.assert_not_called()
    assert call(fn,mode='search')=={'marker':'synthetic-dispatch'}
    assert spy.call_args.kwargs['user_ctx'] is None
