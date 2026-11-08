"""Real Jinja/action-helper fixture with exact retained producer dependencies.

No normal publication, clock, provider, policy-companion reconstruction or source
acquisition occurs. These existing immutable bytes qualify references; the UI
payload merely places their native fields in the existing page components.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
from urllib.parse import urlencode
from jinja2 import Environment, FileSystemLoader
from lib.intl_investigation_action import build_intl_investigation_action
from lib.intl_workspace_macro import build_macro_section

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'tests/fixtures/intl_investigation_page'


def page_fixture():
    source=json.loads((FIXTURE/'SOURCE.json').read_text())
    for name,digest in source['sha256'].items():
        assert hashlib.sha256((FIXTURE/name).read_bytes()).hexdigest()==digest
    descriptor=json.loads((FIXTURE/'intl_generation_current.json').read_text())
    contract=json.loads((FIXTURE/descriptor['artifact_name']).read_text())
    markets=list(dict.fromkeys(c['market'] for c in contract['contexts']))
    horizons=[h for h in dict.fromkeys(c['horizon'] for c in contract['contexts']) if h in ('1m','3m')]
    bases=list(dict.fromkeys(c['currency_basis'] for c in contract['contexts']))
    registry={'markets':[{'market_id':m,'name_en':m,'name_zh':m} for m in markets],
              'horizons':horizons,'bases':bases}
    workspace={'binding_version':2,'config':{'markets':markets,'horizons':horizons,'bases':bases,
        'default_horizon':horizons[0],'default_basis':bases[0],
        'source_reference':contract['generation'],'anchor_ids':[],'library_group_ids':[]},
        'panels':[], 'macros':[], 'risks':[], 'macro_registry':registry,'risk_registry':registry}
    fields={sid:entry['native_measure'] for sid,entry in contract['measures'].items()}
    macro_fields={sid:value for sid,value in fields.items() if sid.split('.')[1] in
                  {'gdp_yoy','cpi_yoy','policy_rate','policy_proxy','yield_10y','yield_change'}}
    base_risk=json.loads((ROOT/'tests/fixtures/intl_workspace/risk_render.json').read_text())['risk_section']
    for index,(horizon,basis) in enumerate(dict.fromkeys((c['horizon'],c['currency_basis']) for c in contract['contexts'] if c['horizon'] in horizons)):
        context={'selected_market':None,'horizon':horizon,'currency_basis':basis,'return_basis':'price'}
        for view in ('macro','risk'):
            actions={}
            for native in contract['contexts']:
                if (native['horizon'],native['currency_basis'])!=(horizon,basis):continue
                back='https://www.mastermind-x.com/intl.html?'+urlencode(dict(view=view,market=native['market'],pins='',horizon=horizon,basis=basis,return_basis='price',group=''))
                for sid in native['measure_ids']:
                    action=build_intl_investigation_action(contract=contract,descriptor=descriptor,
                        context_id=native['id'],selected_measure_ids=[sid],return_url=back)
                    if action:actions[sid]=action
            panel={'context_id':f'im-page-{index}', 'generation':contract['generation'],
                   'context':context,'investigation_actions':actions}
            if view=='macro':
                panel['macro_section']=build_macro_section(context=context,registry=registry,
                    measures=macro_fields,cycle_evidence={},destinations={})
            else:
                section=deepcopy(base_risk)
                # Render the exact retained annual native field, no inferred
                # publisher/current-policy qualification or computed value.
                row=deepcopy(section['pressure_rows'][0]);row.update(market_id='EZ',name_en='Euro Area',name_zh='欧元区')
                row['annual_current_account']=deepcopy(fields['EZ.annual_current_account'])
                section['pressure_rows']=[row]; section['currency_channels']=[]
                panel['risk_section']=section
            workspace['macros' if view=='macro' else 'risks'].append(panel)
    return workspace,contract,descriptor


def render(workspace):
    env=Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=False)
    return env.get_template('intl_workspace/shell.html.j2').render(intl_workspace=workspace,
        t=lambda en,zh:f'<span class="l-en">{en}</span><span class="l-zh">{zh}</span>')


if __name__=='__main__':
    ws,contract,descriptor=page_fixture()
    print(json.dumps({'html':render(ws),'config':ws['config'],'generation':contract['generation'],
        'fingerprint':descriptor['artifact_sha256'],'files':str(FIXTURE)}))
