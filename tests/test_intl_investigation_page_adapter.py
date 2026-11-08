"""Causal source rendering and refusal; no browser/feed publication grant."""
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
import subprocess
from urllib.parse import urlsplit, parse_qs
import pytest
from jinja2 import Environment, FileSystemLoader, DictLoader
from tests.intl_investigation_page_fixture import page_fixture, render, ROOT
from lib.intl_investigation_action import build_intl_investigation_action


class Links(HTMLParser):
    def __init__(self, html):
        super().__init__();self.actions=[];self.feed(html)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='a' and 'data-im-investigate' in attrs:self.actions.append(attrs)


def test_real_shell_baseline_has_no_action_changed_templates_join_exact_prepared_map():
    workspace,contract,descriptor=page_fixture()
    files=['shell.html.j2','macro.html.j2','risk.html.j2']
    # Exact accepted pre-adapter5e4d source, retained for shallow CI.
    expected={'shell.html.j2': '253faf2403475d464610d704fe851ccea6ea5215113b79b6b90c29164419c72c', 'macro.html.j2': '153c31c19bcea3cdad53295ca0052f9f8bb8fdd0df8362b9e824e633689f1f7b', 'risk.html.j2': 'd5368422992e59cc6fed72fe42d81b08025bbd3bcefcef4f6b2d37dcef012f0a'}
    baseline=ROOT/'tests/fixtures/intl_investigation_page/baseline'
    originals={}
    for name in files:
        raw=(baseline/name).read_bytes()
        assert __import__('hashlib').sha256(raw).hexdigest()==expected[name]
        originals['intl_workspace/'+name]=raw.decode()
    before=Environment(loader=DictLoader(originals),autoescape=False).get_template('intl_workspace/shell.html.j2').render(intl_workspace=workspace,t=lambda en,zh:en)
    assert Links(before).actions==[]
    actions=Links(render(workspace)).actions
    assert actions
    assert {a['data-im-investigation-field'] for a in actions}=={'EZ.policy_rate','GB.policy_rate','EZ.gdp_yoy','EZ.cpi_yoy','EZ.annual_current_account'}
    assert all(a['data-im-investigation-generation']==contract['generation'] for a in actions)
    for action in actions:
        url=urlsplit(action['href']);query=parse_qs(url.query)
        assert url.scheme=='https' and url.netloc=='app.mastermind-x.com' and url.path=='/analysis'
        assert query['intl_context']==[action['data-im-investigation-context']]
        assert query['intl_generation']==[contract['generation']]
        assert query['intl_fingerprint']==[descriptor['artifact_sha256']]
        assert query['intl_field']==[action['data-im-investigation-field']]
        assert action['class']=='gbtn'
    assert 'Investigate' in render(workspace) and '调查研究' in render(workspace)


@pytest.mark.parametrize('change',['missing_actions','panel_generation','action_generation','wrong_field','unqualified_value'])
def test_missing_or_mismatched_qualification_renders_no_substitute(change):
    ws,contract,descriptor=page_fixture()
    for panel in ws['macros']+ws['risks']:
        if change=='missing_actions':panel.pop('investigation_actions')
        elif change=='panel_generation':panel['generation']='im-workspace-generation:12345678-1234-4123-8123-123456789012'
        elif change in ('action_generation','wrong_field'):
            for action in panel['investigation_actions'].values():
                if change=='action_generation':action['generation']='im-workspace-generation:12345678-1234-4123-8123-123456789012'
                else:action['field_ids']=['JP.yield_10y']
        else:
            rows=panel['macro_section']['market_rows'] if 'macro_section' in panel else panel['risk_section']['pressure_rows']
            for row in rows:
                for metric in row.values():
                    if type(metric)is dict and metric.get('quality')=='qualified':metric['quality']='unknown'
    assert Links(render(ws)).actions==[]


def test_wrong_immutable_descriptor_never_produces_action_even_if_local_generation_matches():
    ws,contract,descriptor=page_fixture();native=next(c for c in contract['contexts'] if 'GB.policy_rate' in c['measure_ids'])
    descriptor['artifact_sha256']='0'*64
    assert build_intl_investigation_action(contract=contract,descriptor=descriptor,context_id=native['id'],selected_measure_ids=['GB.policy_rate'],
      return_url='https://www.mastermind-x.com/intl.html?view=macro&market=JP&pins=GB,EZ&horizon=1m&basis='+native['currency_basis']+'&return_basis=price&group=') is None


def test_render_positive_is_independent_of_historical_git_objects(monkeypatch):
    # Packed main can be shallow even when its exact current source is complete.
    # Preserve the original baseline comparison without a history/network read.
    def forbidden(*args, **kwargs):
        pytest.fail('adapter render must use its retained baseline, not Git history')
    monkeypatch.setattr(subprocess, 'check_output', forbidden)
    test_real_shell_baseline_has_no_action_changed_templates_join_exact_prepared_map()
