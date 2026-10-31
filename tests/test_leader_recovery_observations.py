from datetime import date
from copy import deepcopy
import hashlib
import json
import pandas as pd
import pytest
from engine.leader_recovery_observations import (merge_recovery_observations,COLUMNS,
    merge_lineage_observations,LINEAGE_SCHEMA,LINEAGE_COLUMNS)

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


def test_lagged_cut_seals_its_own_session_and_skips_missing_native_rows():
    later=date(2026,10,9)
    updated=pd.concat([history(('PLTR',)),history(('PLTR','NEW'),day=later)],ignore_index=True)
    out=merge_recovery_observations(pd.DataFrame(),updated,descriptors(('PLTR','NEW')),as_of=DAY,observed_at='2026-10-10T01:00:00+00:00',enabled=True)
    sealed=out[out[COLUMNS[2]].notna()]
    assert list(zip(sealed.date.dt.date,sealed.ticker))==[(DAY,'PLTR')]
    assert json.loads(sealed.iloc[0][COLUMNS[1]])['as_of']==DAY.isoformat()
    assert len(out)==3  # a lagged cut never mints a native row for NEW
    with pytest.raises(ValueError,match='without_native'):
        merge_recovery_observations(pd.DataFrame(),history(('PLTR',),day=later),descriptors(('NEW',),day=later),as_of=later,observed_at='2026-10-10T01:00:00+00:00',enabled=True)


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


def test_capture_preserves_paired_drawdown_references_not_only_the_number():
    rows=descriptors();ep=rows[0]['display_chips']['leader_recovery']['episode']
    ep.update(max_drawdown_from_high_water=-.4,max_drawdown_peak_price=200.,max_drawdown_peak_on='2026-01-05',max_drawdown_trough_price=120.,max_drawdown_trough_on='2026-06-25',price_high_water=210.,price_high_water_on='2026-09-30')
    captured=json.loads(merge(rows=rows).iloc[0][COLUMNS[1]])['descriptor']['episode']
    assert captured['max_drawdown_peak_price']==200.
    assert captured['max_drawdown_trough_price']==120.
    assert captured['price_high_water']==210.
    assert captured['max_drawdown_peak_on']<captured['max_drawdown_trough_on']<captured['price_high_water_on']


def test_reader_refuses_ambiguous_source_session_timestamp():
    from engine.leader_recovery_observations import read_captured_observation
    with pytest.raises(ValueError,match='unambiguous_date'):
        read_captured_observation(merge(),ticker='PLTR',source_session='2026-10-08T13:00:00',known_at=CLOCK)


# --- leader_lineage.v1 seals (LINEAGE-B) -------------------------------------
# Fixtures mirror history()/descriptors()/merge() above. LINEAGE_TOP and
# LINEAGE_EPISODE are an INDEPENDENT oracle for the sealed key subset.
LINEAGE_TOP=('schema','era','evidence_mode','definition_sha256','as_of','state','reason',
             'thesis_state','setup_state','break_class','contradiction_evidence','revisable',
             'price_ath','rs_ath','source_ref','source_fingerprint_sha256')
LINEAGE_EPISODE=('episode_id','prior_episode_id','leadership_qualified_at','phase','break_class',
                 'revised_from','revised_on','history_complete','closed_on','close_reason',
                 'price_ath','price_ath_on','rs_ath','rs_ath_on','correction_peak_price',
                 'correction_peak_on','correction_trough_price','correction_trough_on',
                 'max_close_drawdown','repair_floor_price','failed_on','structural_on',
                 'structural_watch','ladder','ladder_stalled','rs_vs_peer_basket')
LADDER={'higher_low_confirmed_on':'2026-10-07','reclaim_50d_on':None,'reclaim_200d_on':None,
        'rs_vs_spy_rising_on':None,'rs_vs_peer_basket_rising_on':None,
        'revisions_news_stabilized_on':None,'volume_demand_confirmed_on':None,'pivot_confirmed_on':None}
LINEAGE_NEXT_CLOCK='2026-10-10T01:00:00+00:00'


def lineage_descriptor(day=DAY):
    """A realistic leader_lineage.v1 chip, carrying keys that must NOT be sealed."""
    return {'schema':'leader_lineage.v1','era':'leader-lineage-descriptive-2026-10-11',
            'evidence_mode':'RECONSTRUCTED_CURRENT_VINTAGE','definition_sha256':'c'*64,
            'as_of':day.isoformat(),'state':'DAMAGED','reason':None,'thesis_state':'DAMAGED',
            'setup_state':'REBUILDING','break_class':'UNRESOLVED','contradiction_evidence':[],
            'revisable':True,'price_ath':210.,'rs_ath':1.25,'source_ref':'lineage-test',
            'source_fingerprint_sha256':'d'*64,'ticker':'IGNORED','episodes':[{'episode_id':'UNSEALED'}],
            'sessions_replayed':999,
            'authority':{'may_rank':False,'may_gate':False,'may_size':False,'may_trade':False,'may_alert':False},
            'episode':{'episode_id':'ep-pltr-1','prior_episode_id':None,
                       'leadership_qualified_at':'2026-01-05','phase':'DAMAGED','break_class':'UNRESOLVED',
                       'revised_from':None,'revised_on':None,'history_complete':True,'closed_on':None,
                       'close_reason':None,'price_ath':210.,'price_ath_on':'2026-09-30','rs_ath':1.25,
                       'rs_ath_on':'2026-09-30','correction_peak_price':205.,'correction_peak_on':'2026-10-01',
                       'correction_trough_price':120.,'correction_trough_on':'2026-10-06',
                       'max_close_drawdown':-.4286,'repair_floor_price':120.,'failed_on':None,
                       'structural_on':None,'structural_watch':False,'ladder':dict(LADDER),
                       'ladder_stalled':['rs_vs_peer_basket_rising_on'],'rs_vs_peer_basket':'UNKNOWN',
                       'ladder_order_violations':['R3_BEFORE_R2','R4_BEFORE_R3'],
                       'sessions_below_50':{'consecutive_max':4,'total':9,'current':0},
                       'sessions_below_200':{'consecutive_max':2,'total':3,'current':0},
                       'revision_requires':['new_leadership_qualification'],'authority':{'may_rank':False}}}


def lineage_descriptors(tickers=('PLTR',),day=DAY):
    return [{'ticker':t,'display_chips':{'leader_lineage':lineage_descriptor(day)}} for t in tickers]


def lmerge(old=None,new=None,rows=None,enabled=True,clock=CLOCK,day=DAY):
    return merge_lineage_observations(pd.DataFrame() if old is None else old,history(day=day) if new is None else new,lineage_descriptors(day=day) if rows is None else rows,as_of=day,observed_at=clock,enabled=enabled)


def test_lineage_disabled_default_does_not_even_add_columns():
    h=history();out=lmerge(new=h,enabled=False)
    pd.testing.assert_frame_equal(h,out)
    assert not set(LINEAGE_COLUMNS)&set(out.columns)


def test_lineage_capture_seals_only_the_v1_descriptor_at_the_cut():
    rows=lineage_descriptors(('PLTR','OTHER','THIRD'))
    rows[1]['display_chips']['leader_lineage']['schema']='leader_lineage.v0'
    rows[2]['display_chips']={}
    out=lmerge(new=history(('PLTR','OTHER','THIRD')),rows=rows)
    assert out[LINEAGE_COLUMNS[2]].notna().tolist()==[True,False,False]
    row=out.iloc[0]
    assert row[LINEAGE_COLUMNS[0]]==CLOCK
    raw=row[LINEAGE_COLUMNS[1]]
    assert row[LINEAGE_COLUMNS[2]]==hashlib.sha256(raw.encode()).hexdigest()
    p=json.loads(raw)
    assert p['schema']==LINEAGE_SCHEMA=='leader_lineage_observation.v1'
    assert p['ticker']=='PLTR' and p['as_of']==DAY.isoformat() and p['observed_at']==CLOCK
    assert p['source_first_seen_proven'] is False
    d=p['descriptor']
    assert set(d)==set(LINEAGE_TOP)|{'episode'}
    assert d['state']=='DAMAGED' and d['era']=='leader-lineage-descriptive-2026-10-11'
    assert d['evidence_mode']=='RECONSTRUCTED_CURRENT_VINTAGE'
    assert d['definition_sha256']=='c'*64 and d['source_fingerprint_sha256']=='d'*64
    assert d['contradiction_evidence']==[] and d['revisable'] is True
    for absent in ('authority','episodes','sessions_replayed','ticker'):assert absent not in d
    ep=d['episode']
    assert set(ep)==set(LINEAGE_EPISODE)
    assert ep['ladder']==LADDER and ep['ladder_stalled']==['rs_vs_peer_basket_rising_on']
    assert ep['correction_peak_price']==205. and ep['correction_trough_price']==120.
    for absent in ('ladder_order_violations','sessions_below_50','sessions_below_200','authority','revision_requires'):
        assert absent not in ep
    assert [str(t) for t in out[list(LINEAGE_COLUMNS)].dtypes]==['string']*3


def test_lineage_absent_episode_is_sealed_as_null_not_an_empty_subset():
    rows=lineage_descriptors();rows[0]['display_chips']['leader_lineage']['episode']=None
    assert json.loads(lmerge(rows=rows).iloc[0][LINEAGE_COLUMNS[1]])['descriptor']['episode'] is None
    rows=lineage_descriptors();del rows[0]['display_chips']['leader_lineage']['episode']
    assert json.loads(lmerge(rows=rows).iloc[0][LINEAGE_COLUMNS[1]])['descriptor']['episode'] is None


def test_lineage_rerun_never_overwrites_the_first_seal():
    first=lmerge();rows=lineage_descriptors()
    chip=rows[0]['display_chips']['leader_lineage']
    chip['state']='REPAIRED';chip['episode']['phase']='REPAIRED';chip['episode']['ladder']['reclaim_50d_on']='2026-10-09'
    later=lmerge(old=first,rows=rows,clock='2026-10-10T00:00:00+00:00')
    assert later.iloc[0][list(LINEAGE_COLUMNS)].tolist()==first.iloc[0][list(LINEAGE_COLUMNS)].tolist()


def test_lineage_disarm_preserves_existing_seals():
    first=lmerge();later=lmerge(old=first,enabled=False)
    assert later.iloc[0][list(LINEAGE_COLUMNS)].tolist()==first.iloc[0][list(LINEAGE_COLUMNS)].tolist()


def test_lineage_native_merge_cannot_drop_a_sealed_row_when_ticker_is_absent():
    first=lmerge()
    later=lmerge(old=first,new=history(('OTHER',)),rows=[],enabled=False)
    assert sorted(later.ticker.tolist())==['OTHER','PLTR']
    restored=later[later.ticker=='PLTR'].iloc[0]
    assert restored[LINEAGE_COLUMNS[1]]==first.iloc[0][LINEAGE_COLUMNS[1]]
    assert restored[LINEAGE_COLUMNS[2]]==first.iloc[0][LINEAGE_COLUMNS[2]]
    assert restored['raw_state']=='NONE' and restored['confirmed_state']=='NONE'
    assert pd.api.types.is_datetime64_any_dtype(later['date'])
    assert later['date'].dtype==first['date'].dtype
    assert list(zip(later.date.dt.date,later.ticker)).count((DAY,'PLTR'))==1


def test_lineage_lagged_cut_seals_its_own_session_and_never_mints_a_row():
    later_day=date(2026,10,9)
    updated=pd.concat([history(('PLTR',)),history(('PLTR','NEW'),day=later_day)],ignore_index=True)
    out=merge_lineage_observations(pd.DataFrame(),updated,lineage_descriptors(('PLTR','NEW')),as_of=DAY,observed_at=LINEAGE_NEXT_CLOCK,enabled=True)
    sealed=out[out[LINEAGE_COLUMNS[2]].notna()]
    assert list(zip(sealed.date.dt.date,sealed.ticker))==[(DAY,'PLTR')]
    assert json.loads(sealed.iloc[0][LINEAGE_COLUMNS[1]])['as_of']==DAY.isoformat()
    assert len(out)==3  # a lagged cut never mints a native row for NEW
    with pytest.raises(ValueError,match='without_native'):
        merge_lineage_observations(pd.DataFrame(),history(('PLTR',),day=later_day),lineage_descriptors(('NEW',),day=later_day),as_of=later_day,observed_at=LINEAGE_NEXT_CLOCK,enabled=True)


def test_lineage_enabled_flag_must_be_a_real_boolean():
    with pytest.raises(ValueError,match='enabled_must_be_boolean'):lmerge(enabled=1)
    with pytest.raises(ValueError,match='enabled_must_be_boolean'):lmerge(enabled=None)


@pytest.mark.parametrize('clock,match',[('2026-10-09T01:00:00','requires_timezone'),('2026-10-07T23:00:00+00:00','backdated')])
def test_lineage_clock_ambiguity_or_backdating_refused(clock,match):
    with pytest.raises(ValueError,match=match):lmerge(clock=clock)


def test_lineage_capture_date_and_descriptor_cut_are_pinned():
    with pytest.raises(ValueError,match='cut_mismatch'):lmerge(rows=lineage_descriptors(day=date(2026,10,7)))
    with pytest.raises(ValueError,match='invalid_capture_date'):
        merge_lineage_observations(pd.DataFrame(),history(),lineage_descriptors(),as_of='2026-10-08T13:00:00',observed_at=CLOCK,enabled=True)


@pytest.mark.parametrize('field',['lineage_observed_at','lineage_observation_json','lineage_observation_sha256'])
def test_lineage_partial_seal_is_refused(field):
    first=lmerge();first.loc[0,field]=pd.NA
    with pytest.raises(ValueError,match='partial_observation_seal'):lmerge(old=first)


def test_lineage_digest_tampering_refused_even_when_disarmed():
    first=lmerge();first.loc[0,LINEAGE_COLUMNS[2]]='0'*64
    with pytest.raises(ValueError,match='digest'):lmerge(old=first,enabled=False)


def test_lineage_identity_tampering_refused_even_when_disarmed():
    first=lmerge()
    p=json.loads(first.iloc[0][LINEAGE_COLUMNS[1]]);p['ticker']='OTHER'
    raw=json.dumps(p,sort_keys=True,separators=(',',':'),allow_nan=False)
    first.loc[0,LINEAGE_COLUMNS[1]]=raw
    first.loc[0,LINEAGE_COLUMNS[2]]=hashlib.sha256(raw.encode()).hexdigest()
    with pytest.raises(ValueError,match='identity_clock_mismatch'):lmerge(old=first,enabled=False)


def test_lineage_duplicate_identities_refused():
    first=lmerge();bad=pd.concat([first,first],ignore_index=True)
    with pytest.raises(ValueError,match='duplicate_sealed'):lmerge(old=bad)
    with pytest.raises(ValueError,match='duplicate_updated'):lmerge(new=history(('PLTR','PLTR')))
    with pytest.raises(ValueError,match='duplicate_descriptor'):lmerge(rows=lineage_descriptors(('PLTR','PLTR')))


def test_lineage_merge_preserves_every_recovery_column_and_dtype():
    recovered=merge()
    assert [str(t) for t in recovered[list(COLUMNS)].dtypes]==['string']*3
    out=merge_lineage_observations(pd.DataFrame(),recovered,lineage_descriptors(),as_of=DAY,observed_at=CLOCK,enabled=True)
    assert len(out)==len(recovered)
    for col in recovered.columns:
        if col in LINEAGE_COLUMNS:continue
        pd.testing.assert_series_equal(out[col],recovered[col],check_dtype=True)
    assert out[LINEAGE_COLUMNS[2]].notna().all()


def test_lineage_row_restore_renormalizes_date_and_recovery_dtypes():
    recovered=merge()
    both=merge_lineage_observations(pd.DataFrame(),recovered,lineage_descriptors(),as_of=DAY,observed_at=CLOCK,enabled=True)
    out=merge_lineage_observations(both,history(('OTHER',)),[],as_of=DAY,observed_at=CLOCK,enabled=False)
    assert pd.api.types.is_datetime64_any_dtype(out['date'])
    assert out['date'].dtype==recovered['date'].dtype
    assert [str(t) for t in out[list(COLUMNS)].dtypes]==[str(t) for t in recovered[list(COLUMNS)].dtypes]==['string']*3
    assert [str(t) for t in out[list(LINEAGE_COLUMNS)].dtypes]==['string']*3
    row=out[out.ticker=='PLTR'].iloc[0]
    assert row[COLUMNS[1]]==recovered.iloc[0][COLUMNS[1]]
    assert row[COLUMNS[2]]==recovered.iloc[0][COLUMNS[2]]
    assert row[LINEAGE_COLUMNS[2]]==both.iloc[0][LINEAGE_COLUMNS[2]]


@pytest.mark.parametrize('unit',['s','ms','us','ns'])
def test_lineage_merge_preserves_the_native_date_unit_in_both_branches(unit):
    def native(ticker):
        return pd.DataFrame([{'date':pd.Timestamp(DAY),'ticker':ticker,'raw_state':'NONE'}]).astype({'date':f'datetime64[{unit}]'})
    sealed=merge_lineage_observations(pd.DataFrame(),native('PLTR'),lineage_descriptors(),as_of=DAY,observed_at=CLOCK,enabled=True)
    assert sealed['date'].dtype==native('PLTR')['date'].dtype  # no-restore branch
    restored=merge_lineage_observations(sealed,native('OTHER'),[],as_of=DAY,observed_at=CLOCK,enabled=False)
    assert restored['date'].dtype==native('PLTR')['date'].dtype  # append branch re-normalized, not widened
    assert restored[restored.ticker=='PLTR'].iloc[0][LINEAGE_COLUMNS[2]]==sealed.iloc[0][LINEAGE_COLUMNS[2]]
    assert restored[restored.ticker=='PLTR'].iloc[0]['raw_state']=='NONE'


def test_recovery_merge_output_is_indifferent_to_lineage_columns_in_previous():
    plain=merge()
    with_lineage=merge_lineage_observations(pd.DataFrame(),plain,lineage_descriptors(),as_of=DAY,observed_at=CLOCK,enabled=True)
    next_day=date(2026,10,9)
    updated=pd.concat([history(),history(day=next_day)],ignore_index=True)
    rows=descriptors(day=next_day)
    a=merge_recovery_observations(plain,updated,rows,as_of=next_day,observed_at=LINEAGE_NEXT_CLOCK,enabled=True)
    b=merge_recovery_observations(with_lineage,updated,rows,as_of=next_day,observed_at=LINEAGE_NEXT_CLOCK,enabled=True)
    pd.testing.assert_frame_equal(a[list(COLUMNS)],b[list(COLUMNS)])
    shared=[c for c in a.columns if c in b.columns and c not in LINEAGE_COLUMNS]
    pd.testing.assert_frame_equal(a[shared],b[shared])


def test_one_row_can_carry_both_seals_through_both_merges():
    recovered=merge()
    both=merge_lineage_observations(pd.DataFrame(),recovered,lineage_descriptors(),as_of=DAY,observed_at=CLOCK,enabled=True)
    rec=both.iloc[0][list(COLUMNS)].tolist();lin=both.iloc[0][list(LINEAGE_COLUMNS)].tolist()
    after_recovery=merge_recovery_observations(both,both,[],as_of=DAY,observed_at=CLOCK,enabled=False)
    assert after_recovery.iloc[0][list(COLUMNS)].tolist()==rec
    assert after_recovery.iloc[0][list(LINEAGE_COLUMNS)].tolist()==lin
    after_lineage=merge_lineage_observations(after_recovery,after_recovery,[],as_of=DAY,observed_at=CLOCK,enabled=False)
    assert after_lineage.iloc[0][list(COLUMNS)].tolist()==rec
    assert after_lineage.iloc[0][list(LINEAGE_COLUMNS)].tolist()==lin


def test_lineage_no_mutation_and_parquet_roundtrip(tmp_path):
    old=history();new=history();rows=lineage_descriptors()
    rows_before=deepcopy(rows)
    out=lmerge(old=old,new=new,rows=rows)
    pd.testing.assert_frame_equal(old,history());pd.testing.assert_frame_equal(new,history())
    assert rows==rows_before
    raw=out[LINEAGE_COLUMNS[1]].iloc[0]
    assert raw==json.dumps(json.loads(raw),sort_keys=True,separators=(',',':'),allow_nan=False)
    p=tmp_path/'lineage_history.parquet';out.to_parquet(p,index=False)
    retained=lmerge(old=pd.read_parquet(p),enabled=False)
    assert retained.iloc[0][list(LINEAGE_COLUMNS)].tolist()==out.iloc[0][list(LINEAGE_COLUMNS)].tolist()
