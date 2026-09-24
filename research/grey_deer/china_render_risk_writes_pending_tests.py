"""Pending page-only risk-write acceptance; run explicitly. Implementation refused."""
import pytest


@pytest.fixture
def risk_publication_block(monkeypatch):
    """Execute exact main-body effect blocks; full-main proof is separate."""
    import ast
    import inspect
    from types import SimpleNamespace
    from scripts import build_china as bc
    from engine import market_state, risk_radar_intl_audit as audit
    from engine import risk_radar_intl_tune as tune, risk_radar_scorecard as card
    for key in ('RENDER_NO_DRIP', 'CHINA_FAST_RENDER', 'COLLECT_LANE', 'US_LANE'):
        monkeypatch.delenv(key, raising=False)
    calls = []
    report = {'market': 'cn', 'can_force': False, 'n_graded': 5}
    def spy(name):
        def call(*args, **kwargs):
            calls.append((name, args, kwargs))
            return report.copy()
        return call
    for module, name, label in ((audit,'snapshot_and_grade','grade'),
            (audit,'scorecard','read'), (tune,'tune','tune'),
            (card,'write','scorecard_write'), (market_state,'persist','state_write')):
        monkeypatch.setattr(module, name, spy(label))
    tree = ast.parse(inspect.getsource(bc.main))
    targets = {'audit': '_rra.snapshot_and_grade', 'scorecard': '_rrs.write',
               'state': '_ms.persist'}
    def execute(kind):
        candidates = [node for node in ast.walk(tree) if isinstance(node, ast.Try)
            and any(isinstance(child, ast.Call) and ast.unparse(child.func)==targets[kind]
                    for child in ast.walk(node))]
        assert candidates, f'actual main effect block missing: {kind}'
        block = min(candidates, key=lambda node: node.end_lineno-node.lineno)
        scope = {'_ms': market_state, '_rri': SimpleNamespace(CN_PROFILE=SimpleNamespace(key='cn')),
                 '_no_network_render': bc._no_network_render, 'log': bc.log,
                 'latest': {'risk_radar': {'state':'risk-off'}},
                 'vm': {'market_state': {'score':40}}}
        exec(compile(ast.Module(body=[block],type_ignores=[]), '<actual-main-risk-block>', 'exec'), scope)
        return calls, scope
    return execute


@pytest.mark.parametrize('kind', ['audit','scorecard','state'])
@pytest.mark.parametrize('flags', [('1',''), ('','1'), ('1','1')])
@pytest.mark.parametrize('lane', [('', ''), ('nightly',''), ('','nightly')])
def test_page_only_risk_publication_is_read_only(risk_publication_block, monkeypatch, kind, flags, lane):
    for key,value in zip(('RENDER_NO_DRIP','CHINA_FAST_RENDER','COLLECT_LANE','US_LANE'), flags+lane):
        monkeypatch.setenv(key,value)
    calls, scope = risk_publication_block(kind)
    assert [row[0] for row in calls] == (['read'] if kind=='audit' else [])
    if kind=='audit':
        assert calls[0][2] == {'log_governance':False}
        assert scope['latest']['risk_radar']['can_force'] is False
        assert scope['latest']['risk_radar']['forward_log']['n_graded']==5


@pytest.mark.parametrize('kind', ['audit','scorecard','state'])
@pytest.mark.parametrize('flags', [('', ''), ('0',''), ('','0')])
@pytest.mark.parametrize('lane', [('', ''), ('nightly',''), ('','nightly')])
def test_normal_risk_publication_keeps_existing_owner(risk_publication_block, monkeypatch, kind, flags, lane):
    for key,value in zip(('RENDER_NO_DRIP','CHINA_FAST_RENDER','COLLECT_LANE','US_LANE'), flags+lane):
        monkeypatch.setenv(key,value)
    calls, scope = risk_publication_block(kind)
    expected = {'audit': ['grade','tune'] if 'nightly' in lane else ['read'],
                'scorecard':['scorecard_write'], 'state':['state_write']}[kind]
    assert [row[0] for row in calls] == expected
    if kind=='state':
        assert calls[0][1] == ({'score':40},)
        assert calls[0][2] == {'market_key':'cn'}
    elif kind=='audit':
        assert scope['latest']['risk_radar']['forward_log']['market']=='cn'
        assert scope['latest']['risk_radar']['can_force'] is False
