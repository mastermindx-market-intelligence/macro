"""Native provenance path only; synthetic data, no runtime writer invocation."""
from copy import deepcopy
from datetime import date, datetime, timezone
from dataclasses import replace
import pytest
from engine.entry_radar import quote_context as qc, live_pack as lp
from tests.test_earnings_opportunity_qualification import inputs
from tests.test_entry_radar_w4_pack import frame_from_closes, washout_closes

NOW=datetime(2026,10,7,14,0,tzinfo=timezone.utc)


@pytest.fixture
def native(inputs,monkeypatch):
    monkeypatch.setattr(qc,'_now',lambda:NOW)
    frame=frame_from_closes(washout_closes(),date(2026,10,6))
    pack=lp.build_pack(probe_set=['MU'],store_reader=lambda _:frame,as_of=date(2026,10,6),built_at='2026-10-07T01:00:00Z')
    return dict(pack=pack,identity_read=inputs['identity_read'])


def test_real_retained_receipt_can_bind_unchanged_bytes_before_candidate(native,tmp_path):
    from lib.dataos.identity import ReferenceReadReceipt
    read=native['identity_read']
    pack=qc.retain_pack_identity(native['pack'],read)
    assert pack.pack_hash==native['pack'].pack_hash
    assert pack.with_proof({'pass':True}).identity_observation==pack.identity_observation
    lp.save_pack(pack,tmp_path)
    loaded=lp.load_pack(tmp_path)
    assert loaded.identity_observation==pack.identity_observation
    fresh=read.receipt.as_record();fresh.update(read_started_at_utc_ns=str(int(NOW.timestamp()*10**9)+1),
                                                read_completed_at_utc_ns=str(int(NOW.timestamp()*10**9)+2))
    current=replace(read,receipt=ReferenceReadReceipt.from_record(fresh))
    restored=qc.restore_pack_identity(loaded,current)
    assert restored.receipt==read.receipt and restored.snapshot==current.snapshot


def test_restored_read_qualifies_context_but_request_time_read_does_not(native,inputs):
    from lib.dataos.identity import ReferenceReadReceipt
    from engine.company_intelligence.opportunity_context import compose_earnings_candidate_case
    from engine.company_intelligence.opportunity_qualification import EarningsQualificationError
    pack=qc.retain_pack_identity(native['pack'],native['identity_read'])
    rr=native['identity_read'].receipt.as_record()
    rr.update(read_started_at_utc_ns=str(int(NOW.timestamp()*10**9)+1),read_completed_at_utc_ns=str(int(NOW.timestamp()*10**9)+2))
    late=replace(native['identity_read'],receipt=ReferenceReadReceipt.from_record(rr))
    with pytest.raises(EarningsQualificationError):compose_earnings_candidate_case(**{**inputs,'identity_read':late},composed_at='2026-10-07T14:01:00Z')
    restored=qc.restore_pack_identity(pack,late)
    result=compose_earnings_candidate_case(**{**inputs,'identity_read':restored},composed_at='2026-10-07T14:01:00Z')
    assert result['case']['company_context']['state']=='partial'
    assert result['candidate_context_binding']['episode_id']==inputs['episode']['episode_id']
    assert result['live_projection_eligible'] is False


@pytest.mark.parametrize('mutation',['legacy','digest','generation','artifacts','future_prior'])
def test_no_backfill_or_changed_generation_substitution(native,mutation):
    pack=qc.retain_pack_identity(native['pack'],native['identity_read'])
    from lib.dataos.identity import ReferenceReadReceipt
    rr=native['identity_read'].receipt.as_record()
    rr.update(read_started_at_utc_ns=str(int(NOW.timestamp()*10**9)+1),read_completed_at_utc_ns=str(int(NOW.timestamp()*10**9)+2))
    current=replace(native['identity_read'],receipt=ReferenceReadReceipt.from_record(rr))
    if mutation=='legacy':pack=native['pack']
    elif mutation=='digest':pack.identity_observation['sha256']='0'*64
    elif mutation=='generation':current=replace(current,receipt=replace(current.receipt,generation_id='0'*64))
    elif mutation=='artifacts':current=replace(current,receipt=replace(current.receipt,artifact_sha256=tuple((n,'0'*64) for n,h in current.receipt.artifact_sha256)))
    elif mutation=='future_prior':
        pack.identity_observation['read_receipt']['read_completed_at_utc_ns']=str(int(NOW.timestamp()*10**9)+3)
        body={k:v for k,v in pack.identity_observation.items() if k!='sha256'}
        from hashlib import sha256
        from lib import evidence_foundation as ef
        pack.identity_observation['sha256']=sha256(ef.canonical_json_bytes(body)).hexdigest()
    with pytest.raises(qc.QuoteContextUnavailable):qc.restore_pack_identity(pack,current)
