"""Actual Brain entrypoints; denied Options turns never use the generic loop."""
import ast
import json
from pathlib import Path

import pytest
from engine.neuralweb import brain_gateway as gw
from engine.neuralweb import options_question_gateway as G
from app.options_matrix_http import MatrixHTTPRuntime

@pytest.fixture
def state(monkeypatch,tmp_path):
    def forbidden(*a,**kw):raise AssertionError('generic disclosure or persistence reached')
    for name in ('_run_brain_loop','_run_brain_loop_stream','_ensure_thread','_append_message'):
        if hasattr(gw,name):monkeypatch.setattr(gw,name,forbidden)
    monkeypatch.setattr(gw,'_load_brain_config',lambda root: {})
    monkeypatch.setattr(gw,'_resolve_tier',lambda *a,**kw: {'tier':'pro','status':'active'})
    monkeypatch.setattr(gw,'_check_and_increment_quota',lambda *a,**kw:(True,{'remaining':1}))
    monkeypatch.setattr(gw,'_record_token_usage',lambda *a,**kw:None)
    monkeypatch.setattr(gw,'_prescreen_message',lambda m:None)
    monkeypatch.setattr(gw,'_build_lane_providers',forbidden)
    return dict(message='Explain selected contracts',user_id='u',user_jwt='inert-token',
                root=tmp_path,options_question_reference={})

@pytest.mark.parametrize('stream',[False,True])
def test_off_never_constructs_provider_or_calls_generic(state,stream):
    if stream:
        rows=[json.loads(line[6:]) for line in gw.chat_stream(**state)]
        assert rows[-1]['error']=='options_question_unavailable'
        assert not any(row['type']=='delta' for row in rows)
    else:assert gw.chat(**state)['error']=='options_question_unavailable'

@pytest.mark.parametrize('change',[{'is_guest':True},{'user_jwt':''},{'mode':'research'},
    {'company_source_span':{}},{'history':[{'role':'user','content':'x'}]},
    {'images':['x']},{'thread_id':'persist'}])
def test_conflicting_surface_refuses(state,change):
    assert gw.chat(**dict(state,**change))['error']=='options_question_unavailable'

@pytest.mark.parametrize('stream',[False,True])
def test_eligible_source_path_receives_correct_channel_and_caller(state,monkeypatch,stream):
    state['options_question_runtime']=G.OptionsQuestionRuntime(MatrixHTTPRuntime(lambda r:None),(),True)
    monkeypatch.setattr(gw,'_build_lane_providers',lambda *a:[{'test':'inert'}])
    calls=[]
    def answer(**kw):
        calls.append(kw)
        return {'reply':'Membership context only.','model':'model-1',
                'receipt':{'authority':'context_only'},'usage':{'input_tokens':1,'output_tokens':1}}
    monkeypatch.setattr(G,'answer_question',answer)
    if stream:
        rows=[json.loads(line[6:]) for line in gw.chat_stream(**state)]
        assert rows[-1]['options_question_receipt']=={'authority':'context_only'}
    else:assert gw.chat(**state)['ok'] is True
    assert len(calls)==1
    assert calls[0]['access_token']=='inert-token' and calls[0]['user_id']=='u'
    assert calls[0]['channel']==('/api/brain/stream' if stream else '/api/brain/chat')


def test_http_routes_pass_only_server_runtime():
    # Structural check avoids starting the monolithic API or any installed jobs.
    tree=ast.parse(Path('app/main.py').read_text())
    for fn in ('brain_chat','brain_stream'):
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==fn)
        calls=[n for n in ast.walk(node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
               and n.func.attr in ('chat','chat_stream')]
        assert len(calls)==1
        kw={x.arg:ast.unparse(x.value) for x in calls[0].keywords}
        assert kw['options_question_reference']=='body.options_question_reference'
        assert kw['options_question_runtime']=="getattr(request.app.state, 'options_question_gateway_runtime', None)"


def test_transport_unknown_is_not_generic_retry(state,monkeypatch):
    state['options_question_runtime']=G.OptionsQuestionRuntime(MatrixHTTPRuntime(lambda r:None),(),True)
    monkeypatch.setattr(gw,'_build_lane_providers',lambda *a:[{'test':'inert'}])
    def unknown(**kw):raise G.QuestionDispatchUnknown('question_dispatch_effect_unknown')
    monkeypatch.setattr(G,'answer_question',unknown)
    result=gw.chat(**state)
    assert result['dispatch_state']=='EFFECT_UNKNOWN' and result['retry_allowed'] is False


def test_known_off_path_does_not_debit_quota(state,monkeypatch):
    def forbidden(*a,**kw):raise AssertionError('OFF feature consumed quota')
    monkeypatch.setattr(gw,'_check_and_increment_quota',forbidden)
    assert gw.chat(**state)['error']=='options_question_unavailable'
