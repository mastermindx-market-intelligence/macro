"""Agency URL and bounded unknown filter controls, using the actual page runtime."""
import json
from urllib.parse import urlencode
from pathlib import Path
import importlib.util
_spec = importlib.util.spec_from_file_location("gov_program_filter_fixture", Path(__file__).with_name("test_government_revenue_program_filters.py"))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

def run(tmp_path, search, clear=False, change=None):
    original=base._HARNESS
    base._HARNESS=original.replace("tickerOptionsHtml: $('tickerFilter').innerHTML,", "tickerOptionsHtml: $('tickerFilter').innerHTML, agencyOptionsHtml: $('agencyFilter').innerHTML,")
    if change is not None:
        base._HARNESS=base._HARNESS.replace("if (OPTS.clickClear)", "$('agencyFilter').value="+json.dumps(change)+";fire('agencyFilter','change');if (OPTS.clickClear)")
    try: return base._run(tmp_path, rows=[base._program_row()],status='ok',search=search,click_clear=clear)
    finally: base._HARNESS=original

def test_clear_removes_agency_and_reload_preserves_unowned_params(tmp_path):
    out=run(tmp_path,'?mode=programs&agency=Unknown+agency&ticker=LMT&issuer=RTX&campaign=source#receipt',True)
    params=out['second']['urlParams']
    assert 'agency' not in params and 'ticker' not in params
    assert params['issuer']=='RTX' and params['campaign']=='source'
    assert out['second']['urlRecords'][-1].endswith('#receipt')
    reload=run(tmp_path,'?'+urlencode({k:v.split('#')[0] for k,v in params.items()}))
    assert reload['first']['controls']['agency']==''
    assert base.FILTERED_EN not in reload['first']['queueHtml']

def test_changed_agency_writes_url_and_keeps_issuer(tmp_path):
    out=run(tmp_path,'?mode=programs&agency=Old&issuer=NOC&campaign=read',change='Department of Test and Evaluation')
    assert out['second']['urlParams']['agency']=='Department of Test and Evaluation'
    assert out['second']['urlParams']['issuer']=='NOC'
    assert out['second']['urlParams']['campaign']=='read'

def test_unknown_active_filters_are_visible_options_not_identity_claims(tmp_path):
    out=run(tmp_path,'?mode=programs&agency=Unknown+agency&ticker=UNREVIEWED')
    p=out['first']
    assert p['controls']['agency']=='Unknown agency' and p['controls']['ticker']=='UNREVIEWED'
    assert 'value="Unknown agency"' in p['agencyOptionsHtml']
    assert 'value="UNREVIEWED"' in p['tickerOptionsHtml']
    assert 'Active filter' in p['tickerOptionsHtml']
    assert base.FILTERED_EN in p['queueHtml']
