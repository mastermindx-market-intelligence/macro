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
    from types import SimpleNamespace
    monkeypatch.setattr(G,'prepare_answer',lambda **kw: SimpleNamespace(dispatch=lambda _:answer(**kw)))
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
        assert 'resolve_options_question_runtime(request.app)' in kw['options_question_runtime']


def test_transport_unknown_is_not_generic_retry(state,monkeypatch):
    state['options_question_runtime']=G.OptionsQuestionRuntime(MatrixHTTPRuntime(lambda r:None),(),True)
    monkeypatch.setattr(gw,'_build_lane_providers',lambda *a:[{'test':'inert'}])
    def unknown(**kw):raise G.QuestionDispatchUnknown('question_dispatch_effect_unknown')
    from types import SimpleNamespace
    monkeypatch.setattr(G,'prepare_answer',lambda **kw: SimpleNamespace(dispatch=lambda _:unknown()))
    result=gw.chat(**state)
    assert result['dispatch_state']=='EFFECT_UNKNOWN' and result['retry_allowed'] is False


def test_known_off_path_does_not_debit_quota(state,monkeypatch):
    def forbidden(*a,**kw):raise AssertionError('OFF feature consumed quota')
    monkeypatch.setattr(gw,'_check_and_increment_quota',forbidden)
    assert gw.chat(**state)['error']=='options_question_unavailable'


@pytest.mark.parametrize('reference', [{}, {'selection': 'dated'}, None])
def test_outer_stream_options_never_registers_recoverable_run(reference):
    """Execute the actual HTTP function without importing unrelated API jobs."""
    from types import SimpleNamespace as NS
    tree = ast.parse(Path('app/main.py').read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'brain_stream')
    fn.decorator_list = []
    fn.returns = None
    for arg in fn.args.args:
        arg.annotation = None
    fn.args.defaults = []
    registrations, calls = [], []

    def stream(**kwargs):
        calls.append(kwargs)
        yield 'data: {"type":"done","error":"options_question_unavailable"}\n\n'

    def start(generator, **kwargs):
        registrations.append(kwargs)
        return generator

    scope = dict(
        _brain_module=lambda: NS(chat_stream=stream),
        resolve_options_question_runtime=lambda app: None,
        _brain_throttle_check=lambda _: None,
        _brain_identity=lambda _: ('aid', 'ip', 'device'),
        _brain_track_event=lambda *a: None,
        user_prefs=NS(read_user_prefs=lambda _: {}), REPO=Path('.'),
        brain_runs=NS(start=start, run_event=lambda _: 'run', follow=lambda run: run),
        StreamingResponse=lambda content, **kwargs: content, _SSE_BRAIN_HEADERS={},
    )
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])),
                 'actual-brain-stream', 'exec'), scope)
    body = NS(mode='chat', lane='fast', history=None, thread_id=None,
              message='Explain membership', context=None, company_source_span=None,
              options_question_reference=reference, images=None)
    response = scope['brain_stream'](
        body, NS(app=NS(state=NS())), NS(add_task=lambda *a: None),
        {'id': 'verified-user', '_access_token': 'inert-verified-token'})
    events = list(response)
    assert len(registrations) == (1 if reference is None else 0)
    assert (events[0] == 'run') is (reference is None)
    assert len(calls) == 1
    assert calls[0]['options_question_reference'] is reference
    assert calls[0]['user_jwt'] == 'inert-verified-token'


def test_source_or_entitlement_refusal_precedes_quota(state,monkeypatch):
    state['options_question_runtime']=G.OptionsQuestionRuntime(MatrixHTTPRuntime(lambda _:None),(),True)
    monkeypatch.setattr(gw,'_build_lane_providers',lambda *args: [])
    def denied(**kwargs):raise ValueError('inert entitlement revoked')
    def debit(*args,**kwargs):raise AssertionError('denied source charged quota')
    monkeypatch.setattr(G,'prepare_answer',denied)
    monkeypatch.setattr(gw,'_check_and_increment_quota',debit)
    assert gw.chat(**state)['error']=='options_question_unavailable'
