"""Synthetic second-pin scope/cutoff/seal rejection checks, no licensed inputs."""
from datetime import date
from hashlib import sha256
import json
import pytest
from tests.test_government_revenue_price_source_binding import a, synthetic_packet


def rewrite(packet,mutator):
    p=packet/'packet.json';obj=json.loads(p.read_text());mutator(obj)
    p.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
    return sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def issuer_packet(tmp_path,monkeypatch):
    p=synthetic_packet(tmp_path/'issuer-synthetic',['LHX','LMT','NOC','RTX'])
    pin=rewrite(p,lambda x:x.update(technical_scope='four_issuer_current_input_only'))
    monkeypatch.setattr(a,'_REVIEWED_ISSUER_PACKET_SHA256',pin)
    return p


def load(packet):
    return a.load_reviewed_current_vintage_panel(packet_root=packet,
        window_start=date(2026,8,19),window_end=date(2026,10,9))


def test_second_fixed_pin_accepts_exact_four_issuer_scope_and_sealed_receipt(issuer_packet):
    panel,r=load(issuer_packet)
    assert sorted(panel.series)==['LHX','LMT','NOC','RTX']
    assert r['technical_scope']=='four_issuer_current_input_only'
    assert all(r[k] is False for k in ['historical_first_seen_admitted','identity_continuity_admitted','rights_admitted','permits_grade','permits_issuance'])
    assert panel.basis.vintage_id=='grv-price-'+sha256(a.canonical_bytes({k:v for k,v in r.items() if k!='vintage_id'})).hexdigest()


def test_new_scope_changes_require_new_source_review(issuer_packet):
    rewrite(issuer_packet,lambda x:x.update(technical_scope='registered_50_issuer_universe'))
    with pytest.raises(a.PriceQualificationError,match='unreviewed_packet_digest'):load(issuer_packet)


def test_wrong_scope_is_refused_even_if_a_future_pin_were_mistakenly_reviewed(issuer_packet,monkeypatch):
    pin=rewrite(issuer_packet,lambda x:x.update(technical_scope='registered_50_issuer_universe'))
    monkeypatch.setattr(a,'_REVIEWED_ISSUER_PACKET_SHA256',pin)
    with pytest.raises(a.PriceQualificationError,match='issuer_packet_scope_mismatch'):load(issuer_packet)


def test_wrong_symbol_scope_is_refused_even_if_a_future_pin_were_mistakenly_reviewed(issuer_packet,monkeypatch):
    def swap(x):x['symbols'][0]['symbol']='AAPL'
    pin=rewrite(issuer_packet,swap);monkeypatch.setattr(a,'_REVIEWED_ISSUER_PACKET_SHA256',pin)
    with pytest.raises(a.PriceQualificationError,match='issuer_packet_scope_mismatch'):load(issuer_packet)


def test_cutoff_relabel_cannot_pass_existing_original_query_binding(issuer_packet,monkeypatch):
    pin=rewrite(issuer_packet,lambda x:x.update(action_basis_date='2026-10-13'))
    monkeypatch.setattr(a,'_REVIEWED_ISSUER_PACKET_SHA256',pin)
    with pytest.raises(a.PriceQualificationError,match='dividend_owner_scope_mismatch'):load(issuer_packet)


def test_second_pin_does_not_permit_mutating_any_retained_object(issuer_packet):
    p=issuer_packet/'NOC-dividends.json';p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(a.PriceQualificationError,match='retained_source_byte_mismatch'):load(issuer_packet)


def test_issuer_scope_is_inside_price_basis_seal(issuer_packet):
    panel,r=load(issuer_packet);r['technical_scope']='other_scope'
    assert 'grv-price-'+sha256(a.canonical_bytes({k:v for k,v in r.items() if k!='vintage_id'})).hexdigest()!=panel.basis.vintage_id
