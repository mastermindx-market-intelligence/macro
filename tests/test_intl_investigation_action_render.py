"""Canonical field action slots; synthetic view fixtures, no new admission."""
from copy import deepcopy
from pathlib import Path
from jinja2 import Environment,FileSystemLoader,StrictUndefined
import pytest
from tests.test_intl_workspace_macro_render import build_fixture
from tests.test_intl_workspace_risk_render import packet
from tests.test_intl_eurostat_annual_pressure import inputs
from lib.intl_workspace_risk_pressure import build_pressure_rows
GEN='im-workspace-generation:4979a6c3-b834-4c69-8f1b-c8961cc5e11a'
ROOT=Path(__file__).parents[1]
def action(sid):return {'href':'/analysis?view=investigations&intl_context=synthetic&intl_generation='+GEN+'&intl_fingerprint='+'a'*64+'&intl_field='+sid+'&intl_return=https%3A%2F%2Fwww.mastermind-x.com%2Fintl.html','context_id':'synthetic','generation':GEN,'fingerprint':'a'*64,'field_ids':[sid]}
def render(name,**values):
    env=Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=False,undefined=StrictUndefined)
    return env.get_template('intl_workspace/'+name+'.html.j2').render(context_id='synthetic',panel_context={'horizon':'1m','currency_basis':'local','return_basis':'price'},generation=GEN,**values)

@pytest.mark.parametrize('fault',[None,'absent','generation','field','denied'])
def test_macro_link_requires_matching_permitted_field_action(fault):
    section,registry=build_fixture();actions={'EZ.policy_rate':action('EZ.policy_rate')}
    if fault=='absent':actions={}
    elif fault=='generation':actions['EZ.policy_rate']['generation']='foreign'
    elif fault=='field':actions['EZ.policy_rate']['field_ids']=['GB.policy_rate']
    elif fault=='denied':
        row=next(r for r in section['market_rows']if r['market_id']=='EZ');row['policy_rate']['quality']='denied'
    html=render('macro',macro_section=section,registry=registry,source_notice=None,investigation_actions=actions)
    assert ('data-im-investigate 'in html)==(fault is None)
    if fault is None:assert '>Investigate<'in html and '>调查<'in html

@pytest.mark.parametrize('permitted',[True,False])
def test_risk_annual_slot_exposes_only_its_permitted_action(permitted):
    section,registry,_=packet();section=deepcopy(section);registry=deepcopy(registry)
    section['pressure_rows']=build_pressure_rows(**inputs())
    registry['markets'].append({'market_id':'EZ','name_en':'Euro area','name_zh':'欧元区'})
    actions={'EZ.annual_current_account':action('EZ.annual_current_account')}if permitted else{}
    html=render('risk',risk_section=section,registry=registry,investigation_actions=actions)
    assert ('data-im-investigate 'in html)==permitted
