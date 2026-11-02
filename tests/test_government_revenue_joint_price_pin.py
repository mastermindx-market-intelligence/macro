"""Synthetic joint basis scope/cutoff/retained-owner closure tests only."""
from datetime import date
from hashlib import sha256
import json
import pytest
from tests.test_government_revenue_price_source_binding import a, synthetic_packet

SYMBOLS=['ITA','LHX','LMT','NOC','RTX','SPY']

def reseal(packet,mutator):
    p=packet/'packet.json';v=json.loads(p.read_text());mutator(v)
    p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
    return sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def joint_packet(tmp_path,monkeypatch):
    p=synthetic_packet(tmp_path/'joint-synthetic',SYMBOLS)
    pin=reseal(p,lambda v:v.update(technical_scope='six_symbol_current_input_only'))
    monkeypatch.setattr(a,'_REVIEWED_COMBINED_PACKET_SHA256',pin)
    return p


def load(packet):
    return a.load_reviewed_current_vintage_panel(packet_root=packet,
        window_start=date(2026,8,19),window_end=date(2026,10,9))


def test_joint_fixed_pin_seals_one_six_symbol_technical_basis(joint_packet):
    panel,r=load(joint_packet)
    assert sorted(panel.series)==SYMBOLS
    assert r['technical_scope']=='six_symbol_current_input_only'
    assert all(r[k] is False for k in ('identity_continuity_admitted','historical_first_seen_admitted','rights_admitted','permits_grade','permits_issuance'))
    assert panel.basis.vintage_id=='grv-price-'+sha256(a.canonical_bytes({k:v for k,v in r.items() if k!='vintage_id'})).hexdigest()


def test_joint_scope_change_requires_a_distinct_source_review(joint_packet):
    reseal(joint_packet,lambda v:v.update(technical_scope='registered_efficacy'))
    with pytest.raises(a.PriceQualificationError,match='unreviewed_packet_digest'):load(joint_packet)


def test_joint_scope_guard_rejects_an_accidentally_reviewed_wrong_scope(joint_packet,monkeypatch):
    pin=reseal(joint_packet,lambda v:v.update(technical_scope='four_issuer_current_input_only'))
    monkeypatch.setattr(a,'_REVIEWED_COMBINED_PACKET_SHA256',pin)
    with pytest.raises(a.PriceQualificationError,match='combined_packet_scope_mismatch'):load(joint_packet)


def test_joint_exact_universe_guard_refuses_missing_benchmark(joint_packet,monkeypatch):
    def remove(v):v['symbols']=[r for r in v['symbols'] if r['symbol']!='SPY']
    pin=reseal(joint_packet,remove);monkeypatch.setattr(a,'_REVIEWED_COMBINED_PACKET_SHA256',pin)
    with pytest.raises(a.PriceQualificationError,match='combined_packet_scope_mismatch'):load(joint_packet)


def test_joint_cannot_relabel_cutoff_without_original_owner_query(joint_packet,monkeypatch):
    pin=reseal(joint_packet,lambda v:v.update(action_basis_date='2026-10-13'))
    monkeypatch.setattr(a,'_REVIEWED_COMBINED_PACKET_SHA256',pin)
    with pytest.raises(a.PriceQualificationError,match='dividend_owner_scope_mismatch'):load(joint_packet)


@pytest.mark.parametrize('name',['SPY-dividends.json','ITA-read-receipt.json','RTX-splits.json'])
def test_joint_retained_sources_cannot_change_under_the_same_pin(joint_packet,name):
    p=joint_packet/name;p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(a.PriceQualificationError,match='retained_source_byte_mismatch'):load(joint_packet)


def test_joint_scope_is_inside_the_one_price_basis_seal(joint_packet):
    panel,r=load(joint_packet);r['technical_scope']='other'
    assert 'grv-price-'+sha256(a.canonical_bytes({k:v for k,v in r.items() if k!='vintage_id'})).hexdigest()!=panel.basis.vintage_id


def test_joint_requested_subwindows_have_distinct_sealed_basis_identities(joint_packet):
    full,fr=load(joint_packet)
    short,sr=a.load_reviewed_current_vintage_panel(packet_root=joint_packet,
        window_start=date(2026,8,19),window_end=date(2026,10,8))
    assert fr['reviewed_packet_sha256']==sr['reviewed_packet_sha256']
    assert fr['action_basis_date']==sr['action_basis_date']=='2026-10-12'
    assert fr['requested_sessions'][-1]=='2026-10-09'
    assert sr['requested_sessions'][-1]=='2026-10-08'
    assert full.basis.vintage_id!=short.basis.vintage_id
    assert len(fr['requested_sessions'])==len(sr['requested_sessions'])+1


def test_joint_cannot_claim_a_window_outside_the_actual_retained_calendar(joint_packet):
    with pytest.raises(a.PriceQualificationError,match='invalid_requested_window'):
        a.load_reviewed_current_vintage_panel(packet_root=joint_packet,
            window_start=date(2026,8,19),window_end=date(2026,10,14))


def test_joint_future_dividend_is_refused_even_in_a_resealed_source_proposal(joint_packet,monkeypatch):
    path=joint_packet/'SPY-dividends.json';payload=json.loads(path.read_text())
    payload['results'].append({'id':'synthetic-future-distribution','ticker':'SPY','currency':'USD',
        'distribution_type':'recurring','ex_dividend_date':'2026-11-07','cash_amount':.2,
        'historical_adjustment_factor':.999})
    path.write_text(json.dumps(payload,sort_keys=True,indent=2)+'\n')
    qualification=joint_packet/'dividend-owner-qualification.json';q=json.loads(qualification.read_text())
    row=next(r for r in q['requests'] if r['ticker']=='SPY')
    row['artifact']={'sha256':sha256(path.read_bytes()).hexdigest(),'bytes':len(path.read_bytes())}
    row['rows']=len(payload['results'])
    qualification.write_text(json.dumps(q,sort_keys=True,indent=2)+'\n')
    def update(v):
        v['objects'][path.name]['sha256']=sha256(path.read_bytes()).hexdigest()
        v['objects'][qualification.name]['sha256']=sha256(qualification.read_bytes()).hexdigest()
    pin=reseal(joint_packet,update);monkeypatch.setattr(a,'_REVIEWED_COMBINED_PACKET_SHA256',pin)
    with pytest.raises(a.PriceQualificationError,match='future_or_out_of_scope_factor'):load(joint_packet)
