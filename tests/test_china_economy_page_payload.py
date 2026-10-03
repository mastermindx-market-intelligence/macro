"""Production must not inline the entire canonical publication twice."""
from copy import deepcopy
import json
import shutil
import subprocess
from pathlib import Path
from engine.china_economy_view import client_publication

def sample():
    return {'schema':'macro.v1','panels':{'large':'x'*20000},'economy':{
        'schema':'economy.v1','input_class':'collected','reference_period':'2026-08',
        'authority':'display_only','groups':[{'id':'industry','label_en':'Industry'}],
        'metrics':{'industrial_sa':{'chart':{'dates':['2026-07','2026-08'],'vals':[None,.54]},
                     'unit':'%','definition_id':'nbs-sa.v1','method':'y'*20000}}}}

def test_projection_preserves_every_chart_point_and_csv_unit():
    original=sample();before=deepcopy(original);small=client_publication(original)
    assert original==before
    for ident,metric in small['economy']['metrics'].items():
        for key,value in metric.items():assert value==original['economy']['metrics'][ident][key]
    assert small['download_href']=='china_macro_evidence.json'
    assert 'panels' not in small and len(json.dumps(small))<len(json.dumps(original))*.05

def test_projection_cannot_mutate_machine_contract():
    original=sample();small=client_publication(original)
    small['economy']['metrics']['industrial_sa']['chart']['vals'][1]=9
    assert original['economy']['metrics']['industrial_sa']['chart']['vals'][1]==.54

def test_missing_optional_lens_does_not_crash_projection():
    assert client_publication({'panels':{}})['economy'] is None

def test_anonymous_projection_contains_no_series_payload():
    locked=client_publication(sample(),include_metrics=False)
    assert locked['economy'] is None
    assert locked['detail_href']=='china_economy_detail.json'
    assert locked['download_href']=='china_macro_evidence.json'
    assert locked['projection']=='public_shell_locked_detail'
    assert 'industrial_sa' not in json.dumps(locked)

def test_page_uses_projection_and_json_button_uses_exact_canonical_relative_url():
    root=Path(__file__).resolve().parents[1]
    html=(root/'templates/china.html.j2').read_text()
    js=(root/'templates/china-economy.js').read_text()
    build=(root/'scripts/build_china.py').read_text()
    assert 'economy_client_publication|default(economy_publication)|tojson' in html
    assert "eco_lens.lens(economy_lens, shell='public')" in html
    assert 'include_metrics=False' in build and 'china_economy_detail.json' in build
    assert "publication.download_href === 'china_macro_evidence.json'" in js
    assert "a.download='china-macro-evidence.json'" in js
    assert "fetch(detailHref" in js
    assert "JSON.stringify(publication,null,2)" in js # offline review still works

def test_auth_listener_survives_anonymous_initial_session_for_later_sign_in():
    root=Path(__file__).resolve().parents[1]
    js=(root/'templates/china-economy.js').read_text()
    assert "window.addEventListener('mdx-auth',authChanged);" in js
    assert "window.addEventListener('mdx-auth',inspectSession,{once:true});" not in js
    assert "generation" in js and "controller.signal" in js
    assert (root/'site/china-economy.js').read_text()==js


def test_real_client_auth_lifecycle_without_credentials_or_network():
    root=Path(__file__).resolve().parents[1]
    node=shutil.which('node')
    assert node, 'Node is required for the China client behavior regression'
    result=subprocess.run(
        [node,str(root/'tests/china_economy_auth_harness.cjs'),
         str(root/'templates/china-economy.js')],
        cwd=root,text=True,capture_output=True,timeout=20,check=False)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'PASS: anonymous, later sign-in' in result.stdout



def test_auth_state_copy_uses_the_existing_site_language_classes():
    root=Path(__file__).resolve().parents[1]
    js=(root/'templates/china-economy.js').read_text()
    assert 'class="lang-en"' not in js and 'class="lang-zh"' not in js
    assert 'class="l-en"' in js and 'class="l-zh"' in js


def test_snapshot_identity_binds_public_and_protected_views_without_disclosing_rows():
    import re
    from engine.china_economy_view import publication_snapshot_id
    original=sample()
    public=client_publication(original,include_metrics=False)
    detail=client_publication(original)
    assert re.fullmatch(r'[a-f0-9]{64}',public['snapshot_id'])
    assert public['snapshot_id']==detail['snapshot_id']==publication_snapshot_id(original)
    assert 'industrial_sa' not in json.dumps(public)
    assert public['economy'] is None


def test_snapshot_identity_covers_same_month_value_and_receipt_revisions():
    from engine.china_economy_view import publication_snapshot_id
    original=sample();prior=publication_snapshot_id(original)
    for change in ('value','definition','period','source','panel'):
        revised=deepcopy(original)
        if change=='value':revised['economy']['metrics']['industrial_sa']['chart']['vals'][-1]=.55
        if change=='definition':revised['economy']['metrics']['industrial_sa']['definition_id']='revised'
        if change=='period':revised['economy']['reference_period']='2026-09'
        if change=='source':revised['economy']['source_receipt']='new-vintage'
        if change=='panel':revised['panels']['large']='new-panel-value'
        assert publication_snapshot_id(revised)!=prior,change
    assert publication_snapshot_id(original)==prior


def test_snapshot_identity_ignores_dictionary_insertion_order_and_rejects_nan():
    import pytest
    from engine.china_economy_view import publication_snapshot_id
    a={'b':[1,None,2.5],'a':{'z':3,'x':'国家统计局'}}
    b={'a':{'x':'国家统计局','z':3},'b':[1,None,2.5]}
    assert publication_snapshot_id(a)==publication_snapshot_id(b)
    with pytest.raises(ValueError):publication_snapshot_id({'x':float('nan')})


def test_builder_uses_public_identity_for_protected_payload():
    root=Path(__file__).resolve().parents[1]
    build=(root/'scripts/build_china.py').read_text()
    assert '"snapshot_id": vm["economy_client_publication"]["snapshot_id"]' in build


def test_snapshot_refresh_copy_uses_existing_locale_classes():
    root=Path(__file__).resolve().parents[1]
    js=(root/'templates/china-economy.js').read_text()
    assert 'Refresh page</span><span class="l-zh">刷新页面' in js
    assert "window.location.reload()" in js
    assert "setInterval" not in js
