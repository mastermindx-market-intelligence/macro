"""Portable synthetic binding probes; never copy licensed retained source bytes.

Every price, dividend, source response, receipt and split below is fabricated
for protocol testing. Only the private digest seam is patched within pytest;
production retains fixed reviewed-packet pins and has no digest override API.
"""
from pathlib import Path
from datetime import date,datetime,timezone
from hashlib import sha256
import importlib.util,inspect,json,shutil
import pandas as pd
import pytest
from lib import nyse_calendar
from collectors import massive_stock_day
from engine.close_pass import massive_split_evidence as splits_owner

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('grv_price_bound_loader',ROOT/'engine/government_revenue/price_panel_adapter.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)


def synthetic_packet(root, fixture_symbols=None):
    """Generate entirely synthetic data at runtime; no external artifact reads."""
    root.mkdir()
    objects={}
    def obj(name,value):
        p=root/name
        if isinstance(value,bytes):p.write_bytes(value)
        else:p.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
        objects[name]={'file':name,'sha256':sha256(p.read_bytes()).hexdigest()}
        return name
    dates=nyse_calendar.sessions_between(date(2026,6,1),date(2026,10,9))
    clock='2026-10-13T08:00:00+00:00';ns=int(datetime.fromisoformat(clock).timestamp()*1e9)
    symbols=[];requests=[]
    for j,symbol in enumerate(fixture_symbols or ['SYN_A','SYN_B']):
        prices={d:100.+j*20+i/10 for i,d in enumerate(dates)}
        ex_dates=([date(2026,6,15),date(2026,7,15),date(2026,8,17),date(2026,9,15)] if j==0
                  else [date(2026,6,16),date(2026,8,17),date(2026,9,16)])
        dividend_rows=[];product=1.
        for i,ex in reversed(list(enumerate(ex_dates))):
            cash=.2+.1*i;previous=dates[dates.index(ex)-1];product*=1-cash/prices[previous]
            dividend_rows.append({'id':'synthetic-dividend-'+str(i),'ticker':symbol,'currency':'USD',
                'distribution_type':'recurring','ex_dividend_date':ex.isoformat(),'cash_amount':cash,
                'historical_adjustment_factor':round(product,6)})
        dividend_rows.reverse();div={'status':'OK','request_id':'synthetic','results':dividend_rows}
        div_name=obj(symbol+'-dividends.json',div)
        # Preserve a synthetic wider-window hole in SYN_B, analogous to the
        # real evidence falsifier without embedding or claiming real prices.
        stored={d:p for d,p in prices.items() if not (j==1 and d==date(2026,8,18))}
        raw_path=root/(symbol+'.parquet');pd.DataFrame({'close':list(stored.values())},index=pd.DatetimeIndex(stored.keys(),name='date')).to_parquet(raw_path)
        raw_name=obj(raw_path.name,raw_path.read_bytes())
        raw_ref={'key':'massive_stock_day/'+symbol+'.parquet','sha256':objects[raw_name]['sha256'],
                 'content_length':len(raw_path.read_bytes()),'state':'STABLE_BYTE_READ','observed_at':clock}
        read_name=obj(symbol+'-read-receipt.json',{'state':'STABLE_CANONICAL_SNAPSHOT_READ','objects':{symbol:raw_ref},'fixture_kind':'synthetic'})
        acquisition={'schema':splits_owner.SCHEMA,'source_id':splits_owner.SOURCE_ID,
            'acquisition_id':('a' if j==0 else 'b')*32,'request':splits_owner._request(symbol,'2026-06-01','2026-10-12'),
            'started_utc_ns':ns,'completed_utc_ns':ns,'status':'complete','failure_kind':None,
            'basis_eligible':False,'authority':dict(splits_owner.AUTHORITY),'rows':[],
            'pages':[{'page_index':0,'cursor_sha256':None,'request_started_utc_ns':ns,'response_completed_utc_ns':ns,
                'http_status':200,'observed_body_sha256':sha256(b'synthetic-empty-response').hexdigest(),
                'body_bytes_observed':24,'body_complete':True,'rows_received':0,'rows_retained':0,'outcome':'ok'}]}
        split_name=obj(symbol+'-splits.json',splits_owner._seal(acquisition))
        requests.append({'ticker':symbol,'state':'COMPLETE_PROVIDER_ASSERTED_BOUNDED_ACTION_RESPONSE',
            'artifact':{'sha256':objects[div_name]['sha256'],'bytes':len((root/div_name).read_bytes())},
            'rows':len(dividend_rows),'owner_response_observed_at':clock,
            'query':{'ticker':symbol,'ex_dividend_date.gte':'2026-06-01','ex_dividend_date.lte':'2026-10-12'}})
        symbols.append({'symbol':symbol,'raw':raw_name,'read_receipt':read_name,'dividends':div_name,'splits':split_name})
    dividend_qualification=obj('dividend-owner-qualification.json',{'requests':requests,'fixture_kind':'synthetic'})
    cal_hash=sha256(Path(nyse_calendar.__file__).read_bytes()).hexdigest()
    calendar=obj('calendar-snapshot.json',{'owner_sha256':cal_hash,'calendar_id':'us_equity_sessions',
        'session_dates':[d.isoformat() for d in dates],'fixture_kind':'synthetic'})
    packet={'contract':'grv_reviewed_retained_price_packet/v1','fixture_kind':'fully_synthetic_never_source_evidence',
        'objects':objects,'symbols':symbols,'dividend_owner_qualification':dividend_qualification,
        'calendar_snapshot':calendar,'calendar_owner_sha256':cal_hash,
        'raw_owner_sha256':sha256(Path(massive_stock_day.__file__).read_bytes()).hexdigest(),
        'action_start':'2026-06-01','action_basis_date':'2026-10-12','vintage_observed_at':clock}
    (root/'packet.json').write_text(json.dumps(packet,sort_keys=True,indent=2)+'\n')
    return root


@pytest.fixture
def packet(tmp_path,monkeypatch):
    p=synthetic_packet(tmp_path/'synthetic-packet')
    assert a._reviewed_packet_digest()==a._REVIEWED_PACKET_SHA256
    synthetic_digest=sha256((p/'packet.json').read_bytes()).hexdigest()
    assert synthetic_digest!=a._REVIEWED_PACKET_SHA256
    monkeypatch.setattr(a,'_reviewed_packet_digest',lambda:synthetic_digest)
    return p


def load(packet,wide=False):
    return a.load_reviewed_current_vintage_panel(packet_root=packet,
        window_start=date(2026,6,1) if wide else date(2026,8,19),window_end=date(2026,10,9))


def test_synthetic_packet_derives_bound_semantics_and_37_sessions(packet):
    panel,r=load(packet)
    assert len(r['requested_sessions'])==37
    assert sum(len(s['factor_checks']) for s in r['symbols'])==7
    assert r['reviewed_packet_sha256']==sha256((packet/'packet.json').read_bytes()).hexdigest()
    assert r['not_wired_to_issuance_or_grading'] is True
    assert r['permits_grade'] is r['permits_issuance'] is False
    assert panel.close('SYN_B',date(2026,9,14))>0


def test_production_pin_rejects_synthetic_packet_without_private_test_seam(packet,monkeypatch):
    monkeypatch.setattr(a,'_reviewed_packet_digest',lambda:a._REVIEWED_PACKET_SHA256)
    with pytest.raises(a.PriceQualificationError,match='unreviewed_packet_digest'):load(packet)


def test_public_qualification_accepts_no_hash_actions_calendar_or_expected_digest(packet):
    assert set(inspect.signature(a.load_reviewed_current_vintage_panel).parameters)=={'packet_root','window_start','window_end'}
    assert not hasattr(a,'project_current_vintage_panel')
    for extra in [{'source_hashes':{'raw':'0'*64}},{'expected_packet_sha256':'0'*64},{'calendar':'invented'}]:
        with pytest.raises(TypeError):a.load_reviewed_current_vintage_panel(packet_root=packet,window_start=date(2026,8,19),window_end=date(2026,10,9),**extra)


def test_arbitrary_raw_hash_is_rejected(packet):
    p=packet/'packet.json';x=json.loads(p.read_text());x['objects']['SYN_A.parquet']['sha256']='0'*64;p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
    with pytest.raises(a.PriceQualificationError,match='unreviewed_packet_digest'):load(packet)


def test_removed_dividends_under_same_original_hash_are_rejected(packet):
    p=packet/'SYN_A-dividends.json';x=json.loads(p.read_text());x['results']=[];p.write_text(json.dumps(x))
    with pytest.raises(a.PriceQualificationError,match='retained_source_byte_mismatch'):load(packet)


def test_modified_semantics_rehashed_in_packet_require_new_review(packet):
    p=packet/'SYN_A-dividends.json';x=json.loads(p.read_text());x['results']=[];p.write_text(json.dumps(x))
    m=packet/'packet.json';x=json.loads(m.read_text());x['objects'][p.name]['sha256']=sha256(p.read_bytes()).hexdigest();m.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
    with pytest.raises(a.PriceQualificationError,match='unreviewed_packet_digest'):load(packet)


def test_removed_calendar_session_is_rejected(packet):
    p=packet/'calendar-snapshot.json';x=json.loads(p.read_text());x['session_dates'].remove('2026-08-18');p.write_text(json.dumps(x))
    with pytest.raises(a.PriceQualificationError,match='retained_source_byte_mismatch'):load(packet,wide=True)


def test_calendar_runtime_semantics_cannot_omit_session(packet,monkeypatch):
    original=nyse_calendar.sessions_between
    monkeypatch.setattr(nyse_calendar,'sessions_between',lambda start,end:[d for d in original(start,end) if d!=date(2026,8,18)])
    with pytest.raises(a.PriceQualificationError,match='canonical_calendar_semantics_mismatch'):load(packet,wide=True)


def test_wider_synthetic_window_preserves_calendar_and_refuses_missing_bar(packet):
    with pytest.raises(a.PriceQualificationError,match='partial_price_horizon'):load(packet,wide=True)


@pytest.mark.parametrize('name',['SYN_A.parquet','SYN_A-read-receipt.json','dividend-owner-qualification.json','SYN_B-splits.json'])
def test_mutated_raw_receipt_and_action_bytes_are_rejected(packet,name):
    p=packet/name;p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(a.PriceQualificationError,match='retained_source_byte_mismatch'):load(packet)


def test_symlink_cannot_escape_packet(packet,tmp_path):
    p=packet/'SYN_A.parquet';outside=tmp_path/'synthetic-original';shutil.copy2(p,outside);p.unlink();p.symlink_to(outside)
    with pytest.raises(a.PriceQualificationError,match='source_path_escape'):load(packet)


def test_full_public_receipt_recomputes_identical_price_basis_vintage_id(packet):
    panel,receipt=load(packet)
    body={key:value for key,value in receipt.items() if key!='vintage_id'}
    expected='grv-price-'+sha256(a.canonical_bytes(body)).hexdigest()
    assert expected==receipt['vintage_id']==panel.basis.vintage_id
    assert receipt['price_basis']=={'field':panel.basis.field,'adjustment':panel.basis.adjustment,'vintage_observed_at':panel.basis.vintage_observed_at}


@pytest.mark.parametrize('binding',['packet','object','boundary'])
def test_public_packet_object_and_boundary_bindings_are_inside_vintage_seal(packet,binding):
    panel,receipt=load(packet)
    if binding=='packet':receipt['reviewed_packet_sha256']='0'*64
    elif binding=='object':receipt['retained_object_sha256']['SYN_A.parquet']='0'*64
    else:receipt['qualification_boundary']='changed'
    modified='grv-price-'+sha256(a.canonical_bytes({k:v for k,v in receipt.items() if k!='vintage_id'})).hexdigest()
    assert modified!=panel.basis.vintage_id
