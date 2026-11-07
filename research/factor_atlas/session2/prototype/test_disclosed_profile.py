"""Disclosed-core reconstruction tests; unspecified vendor choices stay explicit."""
from dataclasses import replace
import pytest
from scipy.special import stdtr
from test_pressure import core, fixtures, T, groups


def profile(**kw):
    m=core()
    assert hasattr(m, "disclosed_core_config"), "disclosed-core profile not implemented"
    return replace(m.disclosed_core_config(), **kw)


def calc(bars, **kw):
    return core().bvc_series(bars, profile(min_returns=2, **kw), cutoff_utc_s=T+90000)


def test_disclosed_profile_separates_documented_and_assumed_choices():
    c=profile()
    assert (c.change_basis,c.notional_basis,c.history_scope,c.warmup_policy)==("price_change","close","session","neutral")
    assert c.degrees_freedom==.25 and c.window_minutes==60 and c.min_returns==20
    assert c.zero_volatility=="neutral"
    c.validate()


def test_disclosed_warmup_is_neutral_not_missing_direction():
    x=calc(fixtures([100,101]))[-1]
    assert x.state=="WARMUP_NEUTRAL" and x.net_usd==0 and x.buy_fraction==.5
    assert not x.directionally_usable


def test_disclosed_profile_uses_price_change_and_lagged_sample_scale():
    x=calc(fixtures([100,101,100,120]))[-1]
    assert x.sigma==pytest.approx(2**.5)
    assert x.buy_fraction==pytest.approx(float(stdtr(.25,20/(2**.5))))


def test_disclosed_notional_uses_close_even_when_vwap_is_supplied():
    points=[]
    for sid in ("HOUSE:A","HOUSE:B","HOUSE:C"):
        bars=[replace(b,vwap=80.) for b in fixtures(symbol=sid)]
        points.append(calc(bars)[-1])
    assert all(p.gross_usd==10100 and p.gross_basis=="bar_close_x_volume_proxy" for p in points)
    assert core().aggregate_factors(points,groups()).union_gross_usd==30300


def test_disclosed_same_session_history_crosses_pre_regular_boundary():
    before=fixtures([100,101,100],phase="PRE",offset=-180)
    before=[replace(b,segment=replace(b.segment,end_utc_s=T)) for b in before]
    after=fixtures([120])
    x=calc(before+after)[-1]
    assert x.state=="SIGNED" and x.n_history==2 and x.sigma==pytest.approx(2**.5)


def test_conservative_original_profile_retains_phase_reset():
    m=core(); before=fixtures([100,101,100],phase="PRE",offset=-180)
    before=[replace(b,segment=replace(b.segment,end_utc_s=T)) for b in before]
    x=m.bvc_series(before+fixtures([120]),m.BVCConfig(min_returns=2),cutoff_utc_s=T+90000)[-1]
    assert x.state=="FIRST_BAR_NEUTRAL"


def test_disclosed_day_and_basis_resets_stay_explicit():
    assert calc(fixtures()+fixtures([200],offset=86400,session="2026-06-02"))[-1].state=="FIRST_BAR_NEUTRAL"
    bars=fixtures(); bars[-1]=replace(bars[-1],basis_id="unadjusted/USD/action-v2")
    assert calc(bars)[-1].state=="FIRST_BAR_NEUTRAL"


def test_disclosed_gap_is_not_a_one_minute_price_change():
    bars=fixtures(); del bars[3]
    assert calc(bars)[-1].state=="GAP_NEUTRAL"


@pytest.mark.parametrize("field",["change_basis","notional_basis","history_scope","warmup_policy"])
def test_unsupported_profile_choice_fails_closed(field):
    with pytest.raises(ValueError): profile(**{field:"invented"}).validate()
