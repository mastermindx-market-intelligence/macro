from datetime import date
from copy import deepcopy
import json
import pandas as pd
import pytest
from engine.leader_recovery_observations import merge_recovery_observations,COLUMNS

DAY=date(2026,10,8)
CLOCK='2026-10-09T01:00:00+00:00'


def history(tickers=('PLTR',),day=DAY):
    return pd.DataFrame([{'date':pd.Timestamp(day),'ticker':t,'raw_state':'NONE','confirmed_state':'NONE'} for t in tickers])


def descriptors(tickers=('PLTR',),day=DAY):
    return [{'ticker':t,'display_chips':{'leader_recovery':{'schema':'leader_recovery.v1','as_of':day.isoformat(),'state':'REIGNITING','first_seen_qualified':False,'historical_membership_qualified':False,'definition_sha256':'a'*64,'source_fingerprint_sha256':'b'*64,'episode':{'repair_floor':100.},'expectations':{'source_date':'2026-10-06'}}}} for t in tickers]


def merge(old=None,new=None,rows=None,enabled=True,clock=CLOCK,day=DAY):
    return merge_recovery_observations(pd.DataFrame() if old is None else old,history(day=day) if new is None else new,descriptors(day=day) if rows is None else rows,as_of=day,observed_at=clock,enabled=enabled)


def test_disabled_default_does_not_even_add_columns():
    h=history();out=merge(new=h,enabled=False)
    pd.testing.assert_frame_equal(h,out)
    assert not set(COLUMNS)&set(out.columns)


def test_capture_has_actual_knowledge_clock_not_price_date():
    row=merge().iloc[0]
    assert row[COLUMNS[0]]==CLOCK
    p=json.loads(row[COLUMNS[1]])
    assert p['as_of']=='2026-10-08' and p['observed_at']==CLOCK
    assert p['source_first_seen_proven'] is False
    assert p['descriptor']['state']=='REIGNITING'


def test_same_day_correction_preserves_first_captured_bytes():
    first=merge();rows=descriptors();rows[0]['display_chips']['leader_recovery']['state']='DAMAGED'
    later=merge(old=first,rows=rows,clock='2026-10-10T00:00:00+00:00')
    assert later.iloc[0][list(COLUMNS)].tolist()==first.iloc[0][list(COLUMNS)].tolist()


def test_disarm_preserves_existing_capture():
    first=merge();later=merge(old=first,enabled=False)
    assert later.iloc[0][list(COLUMNS)].tolist()==first.iloc[0][list(COLUMNS)].tolist()


def test_native_merge_cannot_drop_sealed_row_when_ticker_is_absent():
    first=merge();later=merge(old=first,new=history(('OTHER',)),rows=[],enabled=False)
    assert sorted(later.ticker.tolist())==['OTHER','PLTR']
    assert later[later.ticker=='PLTR'].iloc[0][COLUMNS[2]]==first.iloc[0][COLUMNS[2]]


def test_next_day_capture_appends_to_native_identity_without_rewriting_prior():
    first=merge();next_day=date(2026,10,9)
    updated=pd.concat([first,history(day=next_day)],ignore_index=True)
    later=merge(old=first,new=updated,day=next_day,clock='2026-10-10T01:00:00+00:00')
    assert len(later)==2 and later.iloc[0][COLUMNS[2]]==first.iloc[0][COLUMNS[2]]
    assert later.iloc[1][COLUMNS[2]]!=first.iloc[0][COLUMNS[2]]


@pytest.mark.parametrize('field',COLUMNS)
def test_partial_or_tampered_capture_is_refused(field):
    first=merge();first.loc[0,field]=pd.NA
    with pytest.raises(ValueError,match='partial_observation_seal'):merge(old=first)


def test_digest_tampering_refused_even_when_disarmed():
    first=merge();first.loc[0,COLUMNS[2]]='0'*64
    with pytest.raises(ValueError,match='digest'):merge(old=first,enabled=False)


def test_duplicate_capture_keys_refused():
    first=merge();bad=pd.concat([first,first],ignore_index=True)
    with pytest.raises(ValueError,match='duplicate_sealed'):merge(old=bad)
    with pytest.raises(ValueError,match='duplicate_updated'):merge(new=history(('PLTR','PLTR')))
    with pytest.raises(ValueError,match='duplicate_descriptor'):merge(rows=descriptors(('PLTR','PLTR')))


@pytest.mark.parametrize('clock',['2026-10-09T01:00:00','2026-10-07T23:00:00+00:00'])
def test_clock_ambiguity_or_backdating_refused(clock):
    with pytest.raises(ValueError):merge(clock=clock)


def test_current_descriptor_requires_existing_native_row_and_matching_cut():
    with pytest.raises(ValueError,match='without_native'):merge(new=history(('OTHER',)))
    with pytest.raises(ValueError,match='cut_mismatch'):merge(rows=descriptors(day=date(2026,10,7)))


def test_no_mutation_and_parquet_roundtrip(tmp_path):
    old=history();new=history();rows=descriptors();before=deepcopy(rows)
    out=merge(old=old,new=new,rows=rows)
    pd.testing.assert_frame_equal(old,history());pd.testing.assert_frame_equal(new,history());assert rows==before
    p=tmp_path/'history.parquet';out.to_parquet(p,index=False)
    reread=pd.read_parquet(p)
    retained=merge(old=reread,enabled=False)
    assert retained.iloc[0][COLUMNS[2]]==out.iloc[0][COLUMNS[2]]


def test_read_uses_observation_knowledge_cut_not_price_session():
    from engine.leader_recovery_observations import read_captured_observation
    h=merge()
    before=read_captured_observation(h,ticker='PLTR',source_session=DAY,known_at='2026-10-08T23:59:00+00:00')
    assert before['reason']=='not_known_at_requested_cut'
    known=read_captured_observation(h,ticker='PLTR',source_session=DAY,known_at=CLOCK)
    assert known['observation']['descriptor']['state']=='REIGNITING'
    assert known['source_first_seen_proven'] is False


def test_read_absence_cannot_manufacture_a_historical_state():
    from engine.leader_recovery_observations import read_captured_observation
    assert read_captured_observation(history(),ticker='PLTR',source_session=DAY,known_at=CLOCK)['reason']=='no_captured_observation'


def test_reader_rejects_ambiguous_or_corrupted_capture():
    from engine.leader_recovery_observations import read_captured_observation
    h=merge();h.loc[0,COLUMNS[2]]='0'*64
    with pytest.raises(ValueError):read_captured_observation(h,ticker='PLTR',source_session=DAY,known_at=CLOCK)


def test_aware_knowledge_cut_required_for_reader():
    from engine.leader_recovery_observations import read_captured_observation
    with pytest.raises(ValueError):read_captured_observation(merge(),ticker='PLTR',source_session=DAY,known_at='2026-10-09')
