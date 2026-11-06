"""Real canonical inputs; pure/disk projector and actual builder call, no publication."""
from pathlib import Path
import ast
import copy
import json
import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT
from engine.government_revenue import identity_atlas as ia

@pytest.fixture
def inputs():
    return (json.loads((REPO/'data/government_revenue/recipient_entity_graph.json').read_text()),
            json.loads((REPO/'data/government_revenue/identity_atlas_curated.json').read_text()))


def build(inputs, **kw):
    graph, curated = inputs
    return ia.build_identity_atlas(graph=graph,curated=curated,generated_at='2026-10-13T08:53:36.399358+00:00',**kw)


def bae(out):
    return next(x for x in out['issuers'] if x['ticker']=='BAESY')


def qualification(out):
    return bae(out)['archetype_context']['listing_cases'][1].get('research_identity')


def test_current_source_context_uses_frozen_generation_while_plane_and_si_stay_separate(inputs):
    out = ia.build_identity_atlas_payload(root=REPO,generated_at='2026-10-13T08:53:36.399358+00:00',
        graph_as_of='2026-10-13',context_as_of='2026-10-13T08:53:36.399358+00:00')
    assert ia.is_valid_identity_atlas_payload(out)
    assert out['graph_status']=='ready' and out['si_asof']=='2026-08-13'
    assert out['context_as_of']=='2026-10-13T08:53:36.399358+00:00'
    assert qualification(out)['issuer_cik']=='0000895564'
    assert bae(out)['public_security']['state']=='not_in_si_universe'
    assert bae(out)['issuer_attribution']=='not_asserted'
    assert all(out['authority'][k] is False for k in ('can_rank','can_size','can_gate','can_originate_signal'))


def test_same_day_later_review_is_not_visible_at_current_generation(inputs):
    inputs=copy.deepcopy(inputs)
    inputs[1]['issuers']['BAESY']['listing_qualifications'][1]['research_identity_qualification']['known_at']='2026-10-13T20:00:00Z'
    out=build(inputs,graph_as_of='2026-10-13',context_as_of='2026-10-13T08:53:36.399358+00:00')
    assert qualification(out) is None
    assert out['graph_status']=='ready'


def test_precise_replay_before_qualification_does_not_use_current_generated_at(inputs):
    out=build(inputs,graph_as_of='2026-10-13T06:00:00Z',context_as_of='2026-10-13T06:00:00Z')
    assert qualification(out) is None
    assert out['context_as_of']=='2026-10-13T06:00:00+00:00'


def test_explicit_daily_replay_uses_incumbent_inclusive_utc_day_convention(inputs):
    out=build(inputs,graph_as_of='2026-10-13',context_as_of='2026-10-13')
    assert qualification(out) is not None
    assert out['context_as_of'].startswith('2026-10-13T23:59:59.')
    old=build(inputs,graph_as_of='2026-10-12',context_as_of='2026-10-12')
    assert bae(old)['archetype_context']['listing_cases']==[]


def test_legacy_replay_caller_default_remains_historical_and_daily_cutoff_valid(inputs):
    old=build(inputs,graph_as_of='2026-10-12')
    assert bae(old)['archetype_context']['listing_cases']==[]
    current=build(inputs,graph_as_of='2026-10-13')
    assert qualification(current) is not None
    assert 'invalid_analysis_cutoff' not in bae(current)['archetype_context']['gaps']


def test_invalid_explicit_context_cannot_fall_back_to_current_generation(inputs):
    out=build(inputs,graph_as_of='2026-10-13',context_as_of='invalid')
    assert out['context_as_of'] is None
    assert bae(out)['archetype_context']['listing_cases']==[]
    assert 'invalid_analysis_cutoff' in bae(out)['archetype_context']['gaps']


def test_current_context_does_not_bypass_future_graph_admission(inputs):
    out=build(inputs,graph_as_of='2026-10-12',context_as_of='2026-10-13T08:53:36.399358+00:00')
    assert out['graph_status']!='ready'
    assert all(x['entities']==[] and x['issuer_attribution']=='not_asserted' for x in out['issuers'])


def test_actual_builder_call_selects_current_or_explicit_replay_context_clock():
    tree=ast.parse((ROOT/'scripts/build_government_revenue.py').read_text())
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='build_identity_atlas_payload']
    assert len(calls)==1
    call=calls[0]
    for explicit, expected in [(None,'2026-10-13T08:53:36.399358+00:00'),('2026-10-12','2026-10-12'),('2026-10-13T06:00:00Z','2026-10-13T06:00:00Z')]:
        scope={'build_identity_atlas_payload':lambda **kw:kw,'root':REPO,'payload':{'as_of':'2026-10-13'},'identity_atlas_generated_at':'2026-10-13T08:53:36.399358+00:00','as_of':explicit}
        got=eval(compile(ast.Expression(call),str(ROOT/'scripts/build_government_revenue.py'),'eval'),scope)
        assert got['context_as_of']==expected
        assert got['graph_as_of']=='2026-10-13'
