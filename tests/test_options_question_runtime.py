"""Server startup/withdrawal tests; no source, provider or credential IO."""
import copy
from types import SimpleNamespace as NS
import pytest
from app.options_matrix_http import MatrixHTTPRuntime
from app.options_question_runtime import install_options_question_runtime, resolve_options_question_runtime


def config():
    return {'options_question_gateway': {'enabled': True, 'policies': [{
        'provider':'anthropic','endpoint':'https://processor.invalid/v1/messages','model':'model-1',
        'evidence_sha256':'a'*64,'registry_revision':'r1',
        'required_rights_rationale':{'redistribution':'synthetic test only'}}]}}


def app():
    def forbidden(_): raise AssertionError('capture during startup')
    return NS(state=NS(options_matrix_display_runtime=MatrixHTTPRuntime(forbidden)))


def test_startup_lazy_and_withdrawal_invalidates_retained_runtime():
    a=app(); c=config(); reads=[]
    def load(): reads.append(1); return c
    install_options_question_runtime(a,config_loader=load)
    assert reads==[]
    r=resolve_options_question_runtime(a)
    assert r.enabled is True and r.current() is True
    c['options_question_gateway']['enabled']=False
    assert resolve_options_question_runtime(a) is None and r.current() is False
    c['options_question_gateway']['enabled']=True
    install_options_question_runtime(a,config_loader=None)
    assert resolve_options_question_runtime(a) is None and r.current() is False


@pytest.mark.parametrize('change', ['absent','false','truthy','extra','empty','duplicate','many',
    'sha','revision','rationale','rights','destination','normalized','model','provider','capture'])
def test_invalid_config_refuses_entire_runtime(change):
    a=app(); c=config(); block=c['options_question_gateway']; row=block['policies'][0]
    if change=='absent': c={}
    if change=='false':block['enabled']=False
    if change=='truthy':block['enabled']='true'
    if change=='extra':block['browser_grant']=True
    if change=='empty':block['policies']=[]
    if change=='duplicate':block['policies'].append(copy.deepcopy(row))
    if change=='many':block['policies']=[dict(row,model=str(i)) for i in range(33)]
    if change=='sha':row['evidence_sha256']='A'*64
    if change=='revision':row['registry_revision']=' '
    if change=='rationale':row['required_rights_rationale']={}
    if change=='rights':row['required_rights_rationale']={'made_up':'x'}
    if change=='destination':row['endpoint']='https://processor.invalid/v1/messages?x=1'
    if change=='normalized':row['endpoint']='https://PROCESSOR.invalid/v1/messages'
    if change=='model':row['model']='*'
    if change=='provider':row['provider']='unknown'
    if change=='capture':a.state.options_matrix_display_runtime=None
    before=copy.deepcopy(c)
    install_options_question_runtime(a,config_loader=lambda:c)
    assert resolve_options_question_runtime(a) is None
    assert c==before


def test_policy_and_native_capture_replacement_withdraw_existing_preparation():
    a=app();c=config();install_options_question_runtime(a,config_loader=lambda:c)
    r=resolve_options_question_runtime(a)
    c['options_question_gateway']['policies'][0]['registry_revision']='r2'
    assert r.current() is False
    r=resolve_options_question_runtime(a)
    a.state.options_matrix_display_runtime=MatrixHTTPRuntime(lambda _:None)
    assert r.current() is False


def test_config_read_failure_is_off():
    a=app()
    def fail():raise OSError('inert unavailable')
    install_options_question_runtime(a,config_loader=fail)
    assert resolve_options_question_runtime(a) is None
