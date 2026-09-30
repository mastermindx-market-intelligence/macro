"""Production must not inline the entire canonical publication twice."""
from copy import deepcopy
import json
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
    assert "window.addEventListener('mdx-auth',inspectSession);" in js
    assert "window.addEventListener('mdx-auth',inspectSession,{once:true});" not in js
    assert "if(started || !window.MDXAuth" in js
    assert "started=true;" in js
