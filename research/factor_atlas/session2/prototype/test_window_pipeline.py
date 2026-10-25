"""Test composition with actual BVC/window/baseline functions, fabricated bars only."""
from dataclasses import replace
from pathlib import Path
import importlib
import pytest
import pressure as m
from test_window_pressure import make,calc,groups,w


def test_same_et_window_key_matches_across_dst():
    a=calc(make("2026-03-06")).factors[0].gross_reference
    b=calc(make("2026-03-09")).factors[0].gross_reference
    assert a.key==b.key
    assert b.event_end_utc_s-a.event_end_utc_s==71*3600
    result=m.matched_baseline(b,[a,calc(make("2026-03-05")).factors[0].gross_reference],
         ("2026-03-05","2026-03-06"),m.BaselineConfig(min_observations=2),cutoff_utc_s=b.available_at_utc_s)
    assert result.n==2 and result.status=="ZERO_SCALE" and result.z_raw is None


def test_window_current_target_cannot_enter_own_reference_history():
    refs=[calc(make(d,scale=s)).factors[0].gross_reference for d,s in
         (("2026-05-27",1),("2026-05-28",2),("2026-05-29",3))]
    t=calc(make("2026-06-01",scale=4)).factors[0].gross_reference
    config=m.BaselineConfig(min_observations=3)
    days=("2026-05-27","2026-05-28","2026-05-29")
    a=m.matched_baseline(t,refs,days,config,cutoff_utc_s=t.available_at_utc_s)
    b=m.matched_baseline(t,refs+[replace(t,value=1e25)],days,config,cutoff_utc_s=t.available_at_utc_s)
    assert a==b and a.median==201600 and a.mad==100800
    assert a.z_raw==pytest.approx(2/m.MAD_NORMAL_SCALE)


def test_net_and_gross_cumulative_references_are_different_measures():
    f=calc().factors[0]
    assert f.net_reference.key.measure=="cumulative_estimated_net_usd"
    assert f.gross_reference.key.measure=="cumulative_gross_usd"
    assert f.net_reference.key!=f.gross_reference.key


def test_one_factors_missing_member_does_not_erase_unaffected_sibling():
    bars,segs,start,end=make();bars=[b for b in bars if not(b.security_id=="A" and b.start_utc_s==start+60)]
    r=calc((bars,segs,start,end))
    assert r.factors[0].net_reference is None
    assert r.factors[1].net_reference is not None and r.factors[1].missing_cells==0


def test_changed_membership_version_or_basis_is_not_reference_parity():
    bars,segs,start,end=make();t=calc((bars,segs,start,end)).factors[0].gross_reference
    for change in ({"version":"v2"},{"basis":"point_in_time"}):
        r=w().measure_windows(bars,[replace(groups()[0],**change)],segs,start_utc_s=start,
            end_utc_s=end,cutoff_utc_s=end+2,config=replace(m.disclosed_core_config(),min_returns=2))
        assert r.factors[0].gross_reference.key!=t.key


def test_later_correction_never_recomputes_earlier_sigma_before_availability():
    bars,segs,start,end=make();t=calc((bars,segs,start,end))
    later=replace(bars[1],close=300.,source_revision="CORRECTION",available_at_utc_s=end+100)
    assert calc((bars+[later],segs,start,end))==t
    with pytest.raises(ValueError,match="duplicate"):
        calc((bars+[later],segs,start,end),cutoff_utc_s=end+100)


def test_full_constituent_sum_stays_bounded_by_same_observed_gross():
    result=calc()
    for f in result.factors:
        assert abs(f.full_estimated_net_usd)<=f.full_gross_usd
        assert f.directionally_usable_gross_usd+f.policy_neutral_gross_usd+f.other_estimated_gross_usd+f.unestimated_gross_usd==pytest.approx(f.observed_gross_usd)
        assert sum(c.observed_gross_usd for c in f.contributions)==f.observed_gross_usd
    assert result.union_observed_gross_usd+result.duplicated_gross_usd==result.sum_factor_observed_gross_usd


def test_nonmember_corrupt_row_cannot_change_scoped_measurement():
    bars,segs,start,end=make();a=calc((bars,segs,start,end))
    outsider=replace(bars[0],security_id="UNRELATED",close=-1)
    assert calc((bars+[outsider],segs,start,end))==a


def test_session_reset_means_yesterday_bars_do_not_change_today_window():
    bars,segs,start,end=make();yesterday=make("2026-05-29")[0]
    assert calc((yesterday+bars,segs,start,end))==calc((bars,segs,start,end))


def witness():
    assert Path(__file__).with_name("window_pipeline_witness.py").exists(), "full-window pipeline witness missing"
    return importlib.import_module("window_pipeline_witness").synthetic_pipeline()


def test_full_premarket_regular_join_and_twenty_prior_sessions():
    r=witness()
    assert r["source"]=="SYNTHETIC" and r["market_pilot_admitted"] is False
    assert r["window_start_et"]=="04:00" and r["window_end_et"]=="09:35"
    assert r["slots_per_name_per_session"]==335 and r["sessions"]==21
    assert r["unique_security_minutes"]==21105 and r["baseline_n"]==20
    assert r["baseline_coverage"]==1 and r["gross_z"]==pytest.approx(r["independent_gross_z"])
    assert r["replay_equal"] and r["future_prefix_equal"]
    assert r["union_accounting_equal"] and r["all_authority_false"]


def test_later_rebuild_clock_does_not_replace_source_availability():
    bars,segs,start,end=make();a=calc((bars,segs,start,end))
    b=calc((bars,segs,start,end),cutoff_utc_s=end+500)
    assert a==b and a.factors[0].source_known_at_utc_s==end+2


def test_many_overlapping_factors_share_one_actual_bvc_evaluation(monkeypatch):
    original=m.bvc_series;calls=[]
    def observed(*args,**kwargs):
        calls.append(kwargs["cutoff_utc_s"])
        return original(*args,**kwargs)
    monkeypatch.setattr(m,"bvc_series",observed)
    r=calc()
    assert len(calls)==1 and len(r.factors)==2
    assert r.union_observed_gross_usd==151200 and r.duplicated_gross_usd==50400


def test_same_day_but_new_calendar_version_does_not_share_baseline():
    bars,segs,start,end=make();a=calc((bars,segs,start,end)).factors[0]
    new_segs=tuple(replace(seg,calendar_ref="SYNTHETIC_CAL_V2") for seg in segs)
    new_bars=[replace(b,segment=new_segs[0]) for b in bars]
    b=calc((new_bars,new_segs,start,end)).factors[0]
    assert a.gross_reference.key!=b.gross_reference.key
