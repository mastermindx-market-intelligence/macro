"""Point-in-time, adversarial and failed-repair tests; fixtures are not market proof."""
from copy import deepcopy
import json
import numpy as np
import pandas as pd
import pytest
from engine.leader_recovery import RecoverySpec, replay_recovery, describe_recovery, recovery_roster

SPEC = RecoverySpec(high_window=60, fast_window=10, slow_window=40, rs_window=5,
                    confirm_sessions=3)


def source(tail=(), end='2026-10-09'):
    values = np.r_[np.linspace(50, 100, 90), np.asarray(tail)]
    idx = pd.bdate_range(end=end, periods=len(values))
    c = pd.Series(values, index=idx)
    b = pd.Series(100., index=idx)
    return c, b


def run(c, b, **kw):
    return describe_recovery(c, b, as_of=kw.pop('as_of', c.index[-1].date()),
                             sessions=kw.pop('sessions', list(c.index.date)), spec=SPEC, **kw)


def test_prior_leader_and_damage_remembered_beyond_short_watch():
    c,b = source(np.r_[np.linspace(99, 55, 25), np.full(100, 55.)])
    d = run(c,b)
    assert d['state'] == 'DAMAGED'
    assert d['episode']['underwater_sessions'] > 100
    assert d['episode']['max_drawdown'] == pytest.approx(-.45)
    assert d['thesis_state'] == d['fundamental_thesis']['state'] == 'UNKNOWN'
    assert d['prior_leader_on'] is not None


def test_price_recovers_without_relative_restoration():
    c,b = source(np.r_[np.linspace(99, 55, 30), np.linspace(56, 115, 40)])
    b.iloc[-40:] = np.linspace(100, 145, 40)
    d = run(c,b)
    assert d['state'] == 'PRICE_RECOVERED_RS_LAGGING'
    assert d['episode']['price_recovered'] is True
    assert d['episode']['rs_recovered'] is False


def test_multisession_leadership_restoration():
    c,b = source(np.r_[np.linspace(99, 55, 30), np.linspace(56, 110, 40)])
    d = run(c,b)
    assert d['state'] in ('ACTIVE_LEADER', 'LEADERSHIP_REESTABLISHED')
    assert d['episode']['recovered_on'] is not None
    assert d['episode']['max_drawdown'] == pytest.approx(-.45)
    assert 'LEADERSHIP_REESTABLISHED' in [x['to'] for x in d['transitions']]


def test_failed_repair_is_not_permanent_death():
    c,b = source(np.r_[np.linspace(99, 55, 30), np.linspace(56, 85, 20), 54])
    d = run(c,b)
    assert d['state'] == 'FAILED_REPAIR'
    assert d['episode']['failed_repairs'] == 1
    assert d['thesis_state'] == 'UNKNOWN'
    c2,b2 = source(np.r_[np.linspace(99,55,30),np.linspace(56,85,20),54,np.linspace(55,115,35)])
    assert run(c2,b2)['episode']['recovered_on'] is not None


def test_dead_cat_bounce_does_not_restore_leadership():
    c,b = source(np.r_[np.linspace(99,45,35),np.linspace(46,60,6)])
    d = run(c,b)
    assert d['state'] in ('DAMAGED','REBUILDING')
    assert d['episode']['recovered_on'] is None


def test_short_history_never_claims_former_leadership():
    c,b = source()
    d=run(c.iloc[-20:],b.iloc[-20:])
    assert d['state']=='UNAVAILABLE'
    assert d['reason']=='insufficient_leadership_history'
    assert d['episode'] is None


def test_relative_winner_during_absolute_collapse_is_not_new_leader():
    c,b=source()
    c.iloc[:]=np.linspace(100,50,len(c));b.iloc[:]=np.linspace(100,25,len(b))
    assert run(c,b)['state']=='NO_PRIOR_LEADER'


@pytest.mark.parametrize('which', ['stock','benchmark'])
@pytest.mark.parametrize('bad', [np.nan,np.inf,0.,-1.])
def test_missing_or_bad_last_session_is_unavailable(which,bad):
    c,b=source(np.linspace(99,60,20))
    (c if which=='stock' else b).iloc[-1]=bad
    d=run(c,b)
    assert d['state']=='UNAVAILABLE'
    assert d['episode']['history_complete'] is False


def test_gap_cannot_silently_preserve_confirmations():
    c,b=source(np.r_[np.linspace(99,55,30),np.linspace(56,115,40)])
    c.iloc[-20]=np.nan
    d=run(c,b)
    assert d['state']=='UNAVAILABLE'
    assert d['episode']['recovered_on'] is None
    assert d['episode']['history_complete'] is False


def test_missing_date_is_not_forward_filled():
    c,b=source(np.linspace(99,60,20))
    cal=list(c.index.date)
    c=c.drop(c.index[-1])
    d=run(c,b,as_of=cal[-1],sessions=cal)
    assert d['state']=='UNAVAILABLE'


def test_duplicate_session_refused():
    c,b=source()
    c=pd.concat([c,c.iloc[[-1]]])
    d=run(c,b,sessions=list(b.index.date))
    assert d['state']=='UNAVAILABLE' and d['reason']=='duplicate_session'


def test_future_duplicate_and_invalid_numeric_never_change_past():
    c,b=source(np.linspace(99,60,20))
    day=c.index[-6].date()
    baseline=run(c,b,as_of=day)
    c=c.astype(object);c.iloc[-3]='unparseable future'; c=pd.concat([c,c.iloc[[-1]]])
    assert run(c,b,as_of=day,sessions=list(b.index.date))==baseline


def test_every_historical_prefix_is_invariant_to_future_append():
    c,b=source(np.r_[np.linspace(99,55,30),np.linspace(56,115,40)])
    full=replay_recovery(c,b,as_of=c.index[-1].date(),sessions=list(c.index.date),spec=SPEC)
    for n in [61,90,100,115,130,150]:
        short=replay_recovery(c.iloc[:n],b.iloc[:n],as_of=c.index[n-1].date(),
                              sessions=list(c.index[:n].date),spec=SPEC)
        assert full[:n]==short


def test_no_mutation_and_no_authority():
    c,b=source(np.linspace(99,55,30)); before=c.copy();b_before=b.copy()
    d=run(c,b); d['authority']['may_trade']=True
    assert run(c,b)['authority']['may_trade'] is False
    pd.testing.assert_series_equal(c,before);pd.testing.assert_series_equal(b,b_before)
    assert not run(c,b)['first_seen_qualified']
    json.dumps(run(c,b),allow_nan=False)


def test_scale_invariance():
    c,b=source(np.r_[np.linspace(99,55,30),np.linspace(56,115,40)])
    one=run(c,b);two=run(c*7,b*3)
    assert one['state']==two['state']
    assert one['episode']['max_drawdown']==pytest.approx(two['episode']['max_drawdown'])
    assert one['episode']['recovered_on']==two['episode']['recovered_on']


@pytest.mark.parametrize('cal', ['reversed','duplicate','missing_cut'])
def test_calendar_refuses_ambiguity(cal):
    c,b=source();days=list(c.index.date)
    if cal=='reversed':days=days[::-1]
    if cal=='duplicate':days.append(days[-1])
    if cal=='missing_cut':days.pop()
    assert run(c,b,sessions=days)['state']=='UNAVAILABLE'


def test_tz_aware_daily_labels_require_upstream_resolution():
    c,b=source();c.index=c.index.tz_localize('UTC')
    assert run(c,b,sessions=list(b.index.date))['state']=='UNAVAILABLE'


def test_spec_is_frozen_and_invalid_rejected():
    assert len(SPEC.digest)==64
    for kwargs in ({'confirm_sessions':True},{'fast_window':250},
                   {'correction_fraction':.3,'deep_fraction':.2},{'deep_fraction':float('nan')}):
        with pytest.raises(ValueError): RecoverySpec(**kwargs)


def test_roster_stale_unknown_and_stance_separation():
    c,b=source(np.r_[np.linspace(99,55,30),np.linspace(56,110,30)])
    descriptor=run(c,b)
    rows=[{'ticker':'Z','display_chips':{'leader_recovery':descriptor}},
          {'ticker':'A','display_chips':{'leader_recovery':descriptor}},
          {'ticker':'GAP','display_chips':{}}]
    before=deepcopy(rows)
    result=recovery_roster(rows,as_of=c.index[-1].date().isoformat(),stale=True)
    assert result['stale'] is True
    assert [x['ticker'] for x in result['rows']]==['A','Z']
    assert result['counts']['UNAVAILABLE']==1
    result['rows'][0]['episode']['max_drawdown']=0
    assert rows==before


def test_repair_floor_never_moves_down_before_failure():
    c,b=source(np.r_[np.linspace(99,55,30),np.linspace(56,85,20),56,54])
    full=replay_recovery(c,b,as_of=c.index[-1].date(),sessions=list(c.index.date),spec=SPEC)
    attempt=[r for r in full if r.get('episode') and r['episode'].get('repair_floor') is not None]
    assert attempt
    assert all(r['episode']['repair_floor']==55 for r in attempt)
    assert full[-1]['episode']['failed_repairs']==1


def test_no_automatic_alert_or_probabilities():
    c,b=source(np.linspace(99,55,30));d=run(c,b)
    assert not any(d['authority'].values())
    assert 'probability' not in d and 'position_size' not in d


def test_old_peak_cannot_roll_off_and_fake_a_recovery():
    c,b=source(np.r_[np.linspace(99,55,30),np.linspace(56,90,100)])
    d=run(c,b)
    assert d['episode']['peak_price']==100
    assert not d['episode']['price_recovered']
    assert d['episode']['recovered_on'] is None


def test_gap_history_stays_incomplete_even_after_indicators_rewarm():
    c,b=source(np.r_[np.linspace(99,55,30),np.linspace(56,130,100)])
    c.iloc[-80]=np.nan
    d=run(c,b)
    assert d['state']=='REIGNITING'
    assert d['episode']['recovered_on'] is None
    assert not d['episode']['history_complete']


def test_prior_episode_leadership_anchor_does_not_follow_requalification():
    c,b=source(np.r_[np.linspace(99,55,30),np.linspace(56,95,100)])
    full=replay_recovery(c,b,as_of=c.index[-1].date(),sessions=list(c.index.date),spec=SPEC)
    assert len({r['episode']['prior_leader_on'] for r in full if r.get('episode')})==1


def test_tiny_ratio_does_not_round_frozen_reference_to_zero():
    c,b=source(np.r_[np.linspace(99,55,30),np.linspace(56,115,40)])
    b.iloc[-40:]=np.linspace(100,145,40)
    d=run(c,b*1e12)
    assert d['state']=='PRICE_RECOVERED_RS_LAGGING'
    assert d['episode']['reference_rs'] > 0


def test_all_flat_source_never_qualifies():
    c,b=source(); c[:]=100
    assert run(c,b)['state']=='NO_PRIOR_LEADER'


def test_price_high_inside_unresolved_rs_episode_remains_visible():
    c,b=source(np.r_[np.linspace(99,55,30),np.linspace(56,125,35),np.linspace(124,108,15)])
    b.iloc[-50:]=np.linspace(100,160,50)
    d=run(c,b)
    assert d['episode']['peak_price']==100
    assert d['episode']['price_high_water']==125
    assert d['episode']['original_price_target_recovered'] is True
    assert d['episode']['price_recovered'] is False
    assert d['state']!='PRICE_RECOVERED_RS_LAGGING'


def test_past_deep_drawdown_is_not_current_damage_if_trend_is_repaired():
    c,b=source(np.r_[np.linspace(99,55,30),np.linspace(56,95,60),np.full(7,94.)])
    d=run(c,b)
    assert d['episode']['max_drawdown']==pytest.approx(-.45)
    assert d['state']=='REPAIR_PAUSED'
    assert d['episode']['failed_repairs']==0


def test_source_revision_is_fingerprinted_and_future_values_are_not():
    c,b=source(np.linspace(99,60,20));cut=c.index[-6].date()
    one=run(c,b,as_of=cut);future=c.copy();future.iloc[-1]*=2
    assert one['source_fingerprint_sha256']==run(future,b,as_of=cut)['source_fingerprint_sha256']
    changed=c.copy();changed.iloc[-10]*=.99
    assert one['source_fingerprint_sha256']!=run(changed,b,as_of=cut)['source_fingerprint_sha256']


def test_duplicate_roster_identities_are_refused():
    with pytest.raises(ValueError,match='duplicate_roster_identity'):
        recovery_roster([{'ticker':'A'},{'ticker':'A'}],as_of='2026-10-09',stale=False)


def test_max_drawdown_dates_remain_paired_after_a_later_higher_high():
    c,b=source(np.r_[np.linspace(99,55,30),np.linspace(56,125,35),np.linspace(124,108,15)])
    b.iloc[-50:]=np.linspace(100,160,50)
    d=run(c,b);ep=d['episode']
    assert ep['price_high_water']==125
    assert ep['max_drawdown_peak_price']==100
    assert ep['max_drawdown_trough_price']==55
    assert ep['max_drawdown_peak_on'] < ep['max_drawdown_trough_on']
    assert ep['max_drawdown_trough_on'] < ep['price_high_water_on']
    assert ep['max_drawdown_from_high_water']==pytest.approx(ep['max_drawdown_trough_price']/ep['max_drawdown_peak_price']-1)
