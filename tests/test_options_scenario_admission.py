# Principal acceptance additions for post-dispatch contract guidance.
def strict_book():
    import pandas as pd
    from engine.options_exposure_projection import exposure_input_digest
    asof = '2026-10-20'
    g = pd.DataFrame([dict(root='SPY', date=asof, expiration='2026-10-28', strike=100.,
        right='C', underlying_price=100., implied_vol=.2)])
    oi = g[['root','expiration','strike','right']].copy()
    oi['open_interest'] = 10
    ctx = dict(root='SPY',kind='modeled_exposure',security_id='SEC:SPY',
        source_snapshot_ref='synthetic:source',
        clocks=dict(source_session=asof,oi_report_date=asof,
            option_observed_at=asof+'T19:00:00Z',underlying_observed_at=asof+'T19:00:00Z',
            greeks_available_at=asof+'T19:00:01Z',oi_available_at=asof+'T12:00:00Z',
            available_at=asof+'T19:00:02Z'),
        expected_contracts=g[['root','expiration','strike','right']].to_dict('records'),
        contract_terms=[dict(root='SPY',expiration='2026-10-28',strike=100.,right='C',
            series_id='synthetic:call',security_id='SEC:SPY',terms_ref='synthetic:terms',
            deliverable_ref='synthetic:deliverable',currency='USD',multiplier=100,
            deliverable='100_underlying_shares',economic_expiry_at='2026-10-28T20:00:00Z',
            exercise_style='american',discrete_dividend_before_expiry=False,
            available_at=asof+'T12:00:00Z')],
        greek_provenance={'iv':dict(source_ref='synthetic:source',model_ref='synthetic:IV-method',
            method='provider_observed',unit='decimal_annualized',tenor_policy='economic_expiry_no_floor')})
    ctx['input_sha256'] = exposure_input_digest(g,oi,asof,'SPY')
    req=dict(price_grid=[100.,101.],horizons_minutes=[0,30],r=.02,q=0.,mult=100.,pm=.01)
    return g,oi,asof,req,ctx


def strict_call(g,oi,asof,req,ctx):
    from engine.options_scenario_admission import build_admitted_scenario_surface
    return build_admitted_scenario_surface(g,oi,asof,'SPY',request=req,source_context=ctx)


def test_principal_strict_positive_call_and_explicit_carry():
    g,oi,asof,req,ctx=strict_book()
    out=strict_call(g,oi,asof,req,ctx)
    assert out['status']=='complete_for_supplied_universe', out
    assert out['surface']['conventions']['r']==.02
    assert out['surface']['conventions']['q']==0.
    assert out['surface']['conventions']['contract_multiplier']==100
    assert out['surface']['conventions']['pct_move']==.01


def test_principal_scaling_cannot_mislabel_vanna_vol_point():
    g,oi,asof,req,ctx=strict_book();req['pm']=.02
    out=strict_call(g,oi,asof,req,ctx)
    assert out['status']=='unavailable' and out['surface'] is None


def test_principal_declared_scenario_refusal_is_preserved():
    g,oi,asof,req,ctx=strict_book();ctx['capabilities']={'joint_scenario':False}
    out=strict_call(g,oi,asof,req,ctx)
    assert out['status']=='unavailable' and out['surface'] is None


def test_principal_iv_provenance_cannot_be_inferred_from_gamma():
    g,oi,asof,req,ctx=strict_book();ctx['greek_provenance']={}
    out=strict_call(g,oi,asof,req,ctx)
    assert out['status']=='unavailable' and out['surface'] is None


def test_principal_floor_based_iv_cannot_be_repriced_as_exact_time():
    g,oi,asof,req,ctx=strict_book()
    ctx['greek_provenance']['iv']['tenor_policy']='floor_1hour'
    out=strict_call(g,oi,asof,req,ctx)
    assert out['status']=='unavailable' and out['surface'] is None


def test_principal_european_string_cannot_reclassify_standard_spy():
    g,oi,asof,req,ctx=strict_book();ctx['contract_terms'][0]['exercise_style']='european'
    out=strict_call(g,oi,asof,req,ctx)
    assert out['status']=='unavailable' and out['surface'] is None


def test_principal_finite_input_that_kernel_drops_refuses_entire_grid():
    import pandas as pd
    from engine.options_exposure_projection import exposure_input_digest
    g,oi,asof,req,ctx=strict_book()
    bad=g.iloc[0].to_dict();bad['strike']=1e-308
    g=pd.concat([g,pd.DataFrame([bad])],ignore_index=True)
    bad_oi=oi.iloc[0].to_dict();bad_oi['strike']=1e-308
    oi=pd.concat([oi,pd.DataFrame([bad_oi])],ignore_index=True)
    ctx['expected_contracts'].append({k:bad[k] for k in ['root','expiration','strike','right']})
    term=dict(ctx['contract_terms'][0],strike=1e-308,series_id='synthetic:extreme')
    ctx['contract_terms'].append(term)
    ctx['input_sha256']=exposure_input_digest(g,oi,asof,'SPY')
    out=strict_call(g,oi,asof,req,ctx)
    assert out['status']=='unavailable' and out['surface'] is None


def test_supported_parity_preserves_existing_math_and_explicit_conventions():
    from engine.options_scenario_surface import build_scenario_surface
    from engine.options_exposure_projection import _time
    g,oi,asof,req,ctx=strict_book()
    out=strict_call(g,oi,asof,req,ctx)
    t=(_time(ctx['contract_terms'][0]['economic_expiry_at'])-_time(ctx['clocks']['option_observed_at'])).total_seconds()/(365*86400)
    expected=build_scenario_surface([dict(strike=100.,right='C',expiry='2026-10-28',exp_years=t,oi=10.,iv=.2)],
        root='SPY',observed_at=_time(ctx['clocks']['option_observed_at']).isoformat(),
        spot=100.,price_grid=req['price_grid'],horizons_minutes=req['horizons_minutes'],
        iv_observed_at=_time(ctx['clocks']['option_observed_at']).isoformat(),
        r=req['r'],q=req['q'],mult=req['mult'],pm=req['pm'])
    assert out['surface']==expected
    assert out['authority'] and not any(out['authority'].values())
    assert out['authority_tier']=='research' and out['evidence_class']=='SCENARIO'


def test_missing_expected_denominator_refuses_instead_of_inferring_received_book():
    g,oi,asof,req,ctx=strict_book();ctx.pop('expected_contracts')
    out=strict_call(g,oi,asof,req,ctx)
    assert out['status']=='unavailable' and out['coverage']['expected'] is None


def test_missing_member_does_not_disappear_before_counting():
    g,oi,asof,req,ctx=strict_book()
    ctx['expected_contracts'].append(dict(root='SPY',expiration='2026-10-28',strike=101.,right='C'))
    ctx['contract_terms'].append(dict(ctx['contract_terms'][0],strike=101.,series_id='synthetic:missing'))
    out=strict_call(g,oi,asof,req,ctx)
    assert out['surface'] is None and out['coverage']['expected']==2
    assert out['coverage']['received']==1 and out['coverage']['missing']==1


def test_missing_iv_refuses_complete_supplied_surface():
    from engine.options_exposure_projection import exposure_input_digest
    g,oi,asof,req,ctx=strict_book();g.loc[0,'implied_vol']=None
    ctx['input_sha256']=exposure_input_digest(g,oi,asof,'SPY')
    out=strict_call(g,oi,asof,req,ctx)
    assert out['surface'] is None and out['coverage']['selected']==1
    assert out['coverage']['qualified']==0


def test_known_zero_member_is_counted_without_undefined_iv_or_greek():
    import pandas as pd
    from engine.options_exposure_projection import exposure_input_digest
    g,oi,asof,req,ctx=strict_book()
    zero=dict(root='SPY',expiration='2026-10-28',strike=101.,right='P',open_interest=0)
    oi=pd.concat([oi,pd.DataFrame([zero])],ignore_index=True)
    ctx['expected_contracts'].append({k:zero[k] for k in ['root','expiration','strike','right']})
    ctx['contract_terms'].append(dict(ctx['contract_terms'][0],strike=101.,right='P',series_id='synthetic:zero-put'))
    ctx['input_sha256']=exposure_input_digest(g,oi,asof,'SPY')
    out=strict_call(g,oi,asof,req,ctx)
    assert out['status']=='complete_for_supplied_universe'
    assert out['coverage']['expected']==out['coverage']['selected']==out['coverage']['qualified']==2
    assert out['coverage']['zero_weight']==1 and out['coverage']['missing']==0


def test_all_zero_members_remain_known_even_without_iv_provenance():
    from engine.options_exposure_projection import exposure_input_digest
    g,oi,asof,req,ctx=strict_book();oi.loc[0,'open_interest']=0
    g.loc[0,'implied_vol']=None;ctx['greek_provenance']={}
    ctx['input_sha256']=exposure_input_digest(g,oi,asof,'SPY')
    out=strict_call(g,oi,asof,req,ctx)
    assert out['coverage']['qualified']==out['coverage']['zero_weight']==1
    assert out['surface'] is None and out['unavailable_reasons']==['no_positive_weight_contracts']


def test_mutated_inputs_cannot_be_accepted_from_composer_return():
    g,oi,asof,req,ctx=strict_book();g.loc[0,'implied_vol']=.25
    out=strict_call(g,oi,asof,req,ctx)
    assert out['surface'] is None and out['unavailable_reasons']==['source_inputs_do_not_match_receipt']


def test_dated_approximation_cannot_authorize_iv_repricing():
    g,oi,asof,req,ctx=strict_book();ctx['kind']='dated_provider_approximation'
    assert strict_call(g,oi,asof,req,ctx)['surface'] is None


def test_call_requires_known_absence_of_intervening_dividend():
    for value in [None, True, 'false']:
        g,oi,asof,req,ctx=strict_book()
        ctx['contract_terms'][0]['discrete_dividend_before_expiry']=value
        assert strict_call(g,oi,asof,req,ctx)['surface'] is None


def test_general_admission_boundary_and_future_horizon_use_exact_clock():
    from datetime import timedelta
    from engine.options_exposure_projection import _time
    for seconds,expected in [(59,False),(60,True),(61,True)]:
        g,oi,asof,req,ctx=strict_book()
        anchor=_time(ctx['clocks']['option_observed_at'])
        expiry=anchor+timedelta(seconds=seconds)
        # Keep exact identity's NY date aligned with the explicit economic fixing.
        g.loc[0,'expiration']=oi.loc[0,'expiration']=asof
        ctx['expected_contracts'][0]['expiration']=asof
        ctx['contract_terms'][0].update(expiration=asof,economic_expiry_at=expiry.isoformat())
        from engine.options_exposure_projection import exposure_input_digest
        ctx['input_sha256']=exposure_input_digest(g,oi,asof,'SPY');req['horizons_minutes']=[0]
        out=strict_call(g,oi,asof,req,ctx)
        assert (out['status']=='complete_for_supplied_universe') is expected
        req['horizons_minutes']=[1]
        assert strict_call(g,oi,asof,req,ctx)['surface'] is None


def test_source_dates_clocks_root_and_exact_terms_refuse_independently():
    for mutate in [
        lambda g,o,r,c:c['clocks'].update(oi_available_at='2026-10-21T12:00:00Z'),
        lambda g,o,r,c:c['clocks'].update(option_observed_at='2026-10-19T19:00:00Z'),
        lambda g,o,r,c:c['contract_terms'][0].update(available_at='2026-10-21T12:00:00Z'),
        lambda g,o,r,c:c.update(root='QQQ'),
        lambda g,o,r,c:c['contract_terms'][0].update(multiplier=50),
        lambda g,o,r,c:r.update(mult=50),
        lambda g,o,r,c:c['contract_terms'][0].pop('deliverable_ref'),
        lambda g,o,r,c:c['clocks'].update(underlying_observed_at='2026-10-20T19:00:01Z'),
    ]:
        g,oi,asof,req,ctx=strict_book();mutate(g,oi,req,ctx)
        assert strict_call(g,oi,asof,req,ctx)['surface'] is None
    g,oi,asof,req,ctx=strict_book()
    from engine.options_scenario_admission import build_admitted_scenario_surface
    assert build_admitted_scenario_surface(g,oi,asof,'SPX',request=req,source_context=ctx)['surface'] is None


def test_exact_scope_does_not_select_nearest_expiry():
    g,oi,asof,req,ctx=strict_book();req['expiry_scope']=['2026-10-29']
    out=strict_call(g,oi,asof,req,ctx)
    assert out['surface'] is None and out['unavailable_reasons']==['empty_expiry_scope']


def test_call_does_not_mutate_native_frames_or_receipt():
    from copy import deepcopy
    g,oi,asof,req,ctx=strict_book();g0,oi0=g.copy(deep=True),oi.copy(deep=True)
    req0,ctx0=deepcopy(req),deepcopy(ctx)
    strict_call(g,oi,asof,req,ctx)
    assert g.equals(g0) and oi.equals(oi0) and req==req0 and ctx==ctx0


def test_malformed_receipt_containers_and_nonboolean_capabilities_are_unavailable():
    for field,value in [('contract_terms',['bad']),('contract_terms',{}),('expected_contracts',['bad']),
                        ('clocks',[]),('contract_reference_populations',['bad']),
                        ('capabilities',{'joint_scenario':0}),('capabilities',{'repricing':'true'})]:
        g,oi,asof,req,ctx=strict_book();ctx[field]=value
        assert strict_call(g,oi,asof,req,ctx)['surface'] is None


def test_invalid_scalar_requests_do_not_raise_or_infer_conventions():
    for field,value in [('r',True),('q',float('nan')),('pm',None),('mult','100'),
                        ('horizons_minutes',[10**400]),('horizons_minutes',[False]),
                        ('price_grid',[100.,float('inf')]),('iv_source','solve_from_mid'),
                        ('model','unqualified-model'),('vol_map','sticky_delta')]:
        g,oi,asof,req,ctx=strict_book();req[field]=value
        assert strict_call(g,oi,asof,req,ctx)['surface'] is None


def test_heterogeneous_multipliers_refuse_without_global_default():
    import pandas as pd
    from engine.options_exposure_projection import exposure_input_digest
    g,oi,asof,req,ctx=strict_book()
    other=dict(g.iloc[0],strike=101.)
    g=pd.concat([g,pd.DataFrame([other])],ignore_index=True)
    oi=pd.concat([oi,pd.DataFrame([dict(oi.iloc[0],strike=101.)])],ignore_index=True)
    ctx['expected_contracts'].append({k:other[k] for k in ['root','expiration','strike','right']})
    ctx['contract_terms'].append(dict(ctx['contract_terms'][0],strike=101.,series_id='synthetic:adjusted',multiplier=50))
    ctx['input_sha256']=exposure_input_digest(g,oi,asof,'SPY')
    out=strict_call(g,oi,asof,req,ctx)
    assert out['surface'] is None and out['unavailable_reasons']==['exact_series_terms_unqualified']


def test_missing_oi_is_not_an_observed_zero():
    from engine.options_exposure_projection import exposure_input_digest
    g,oi,asof,req,ctx=strict_book();oi.loc[0,'open_interest']=None
    ctx['input_sha256']=exposure_input_digest(g,oi,asof,'SPY')
    out=strict_call(g,oi,asof,req,ctx)
    assert out['surface'] is None and out['unavailable_reasons']==['oi_unknown_or_invalid']
    assert out['coverage']['zero_weight']==0


def test_unexpected_duplicate_and_foreign_native_members_are_not_projected_away():
    import pandas as pd
    from engine.options_exposure_projection import exposure_input_digest
    for change in ['duplicate','foreign','unexpected','date']:
        g,oi,asof,req,ctx=strict_book()
        if change=='duplicate':g=pd.concat([g,g],ignore_index=True)
        if change=='foreign':g.loc[0,'root']='QQQ'
        if change=='unexpected':g.loc[0,'strike']=101.
        if change=='date':g.loc[0,'date']='2026-10-19'
        ctx['input_sha256']=exposure_input_digest(g,oi,asof,'SPY')
        assert strict_call(g,oi,asof,req,ctx)['surface'] is None


def test_supplied_expected_terms_not_symbol_shape_define_known_identity():
    g,oi,asof,req,ctx=strict_book();ctx['contract_terms'][0]['deliverable']='cash_settled_index'
    assert strict_call(g,oi,asof,req,ctx)['surface'] is None
    g,oi,asof,req,ctx=strict_book();ctx['contract_terms'][0]['right']='P'
    assert strict_call(g,oi,asof,req,ctx)['surface'] is None


def test_known_zero_count_survives_another_members_missing_iv():
    import pandas as pd
    from engine.options_exposure_projection import exposure_input_digest
    g,oi,asof,req,ctx=strict_book();g.loc[0,'implied_vol']=None
    zero=dict(root='SPY',expiration='2026-10-28',strike=101.,right='P',open_interest=0)
    oi=pd.concat([oi,pd.DataFrame([zero])],ignore_index=True)
    ctx['expected_contracts'].append({k:zero[k] for k in ['root','expiration','strike','right']})
    ctx['contract_terms'].append(dict(ctx['contract_terms'][0],strike=101.,right='P',series_id='synthetic:zero-put'))
    ctx['input_sha256']=exposure_input_digest(g,oi,asof,'SPY')
    out=strict_call(g,oi,asof,req,ctx)
    assert out['surface'] is None and out['coverage']['selected']==2
    assert out['coverage']['zero_weight']==1 and out['coverage']['qualified']==1
    assert out['coverage']['unqualified_selected']==1


def test_selected_scope_is_carried_to_result_without_population_reinterpretation():
    g,oi,asof,req,ctx=strict_book();req['expiry_scope']=['2026-10-28'];req['max_dte_days']=10
    out=strict_call(g,oi,asof,req,ctx)
    assert out['status']=='complete_for_supplied_universe'
    assert out['coverage']['expiry_scope']==out['surface']['expiry_scope']==['2026-10-28']
    assert out['coverage']['max_dte_days']==10
    assert out['coverage']['expected']==out['coverage']['selected']==1


def test_conflicting_native_deliverables_cannot_hide_behind_standard_label():
    for key, value in [('shares_per_contract', 50),
                       ('additional_underlyings', [{'ticker': 'XYZ', 'amount': 1}]),
                       ('additional_underlyings', None)]:
        g, oi, asof, req, ctx = strict_book()
        ctx['contract_terms'][0][key] = value
        out = strict_call(g, oi, asof, req, ctx)
        assert out['surface'] is None
        assert out['unavailable_reasons'] == ['exact_series_terms_unqualified']


def test_american_call_carry_cannot_claim_european_equivalence():
    from engine.intraday_greeks import bs_price
    for r, q in [(0.02, 0.05), (-0.05, 0.0)]:
        # An American holder may exercise now; this European model can fall
        # below that attainable value under either carry convention.
        assert float(bs_price(100., 50., 1., .05, True, r=r, q=q)) < 50.
        g, oi, asof, req, ctx = strict_book()
        req.update(r=r, q=q)
        out = strict_call(g, oi, asof, req, ctx)
        assert out['surface'] is None
        assert out['unavailable_reasons'] == ['unsupported_american_call_carry']


# Quote-valuation synthetic engineering fixtures: no acquisition or PIT trial.
import csv
import io

import pandas as pd
import pytest

from engine.options_scenario_admission import (
    build_admitted_scenario_surface, compose_quote_valuation_inputs,
)
from lib.options_source_receipts import THETA_QUOTE_ENDPOINTS, theta_acquisition


QUOTE_DAY = "2026-10-20"
QUOTE_TARGET = QUOTE_DAY + "T19:00:00Z"
QUOTE_RECEIVED = "2026-10-21T10:00:00Z"
QUOTE_EVALUATED = "2026-10-21T10:00:02Z"


def quote_capture_fixture(kind, changes=None, params_changes=None, extra_rows=()):
    params = dict(symbol="SPY", date=QUOTE_DAY, start_time="14:59:55.000",
                  end_time="15:00:00.000", interval="tick", format="csv")
    row = dict(timestamp=QUOTE_DAY + ("T14:59:59.000" if kind == "option" else "T14:59:58.750"),
               bid="1.99" if kind == "option" else "99.99",
               ask="2.01" if kind == "option" else "100.01", bid_size="10", ask_size="11",
               bid_exchange="1", ask_exchange="1", bid_condition="0", ask_condition="0")
    if kind == "option":
        params.update(expiration="2026-10-28", strike="100", right="call")
        row.update(symbol="SPY", expiration="2026-10-28", strike="100", right="CALL")
    else:
        params["venue"] = "utp_cta"
    row.update(changes or {})
    params.update(params_changes or {})
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    writer.writerows(extra_rows)
    raw = out.getvalue().encode()
    receipt = theta_acquisition(THETA_QUOTE_ENDPOINTS[kind], params, raw,
        origin="http://theta-fixture:25503", request_started_at="2026-10-21T09:59:59Z",
        received_at=QUOTE_RECEIVED)
    return dict(raw=raw, receipt=receipt)


def quote_valuation_case():
    expected = [dict(root="SPY", expiration="2026-10-28", strike=100., right="C")]
    oi = pd.DataFrame([dict(expected[0], date=QUOTE_DAY, open_interest=10,
        _theta_acquisition=theta_acquisition("/v3/option/history/open_interest",
            dict(symbol="SPY", expiration="20261028", right="call", start_date=20261020,
                 end_date=20261020, format="csv"), b"synthetic OI capture",
            origin="http://theta-fixture:25503", received_at=QUOTE_RECEIVED))])
    context = dict(root="SPY", kind="modeled_exposure", security_id="SEC:SPY",
        expected_contracts=expected, clocks=dict(source_session=QUOTE_DAY, oi_report_date=QUOTE_DAY,
            option_observed_at=QUOTE_TARGET, underlying_observed_at=QUOTE_TARGET,
            greeks_available_at=QUOTE_EVALUATED, oi_available_at=QUOTE_RECEIVED, available_at=QUOTE_EVALUATED),
        contract_terms=[dict(expected[0], series_id="synthetic:SPY-call", security_id="SEC:SPY",
            terms_ref="synthetic:terms", deliverable_ref="synthetic:deliverable", currency="USD",
            multiplier=100, deliverable="100_underlying_shares", exercise_style="american",
            economic_expiry_at="2026-10-28T20:00:00Z", available_at="2026-10-20T12:00:00Z",
            discrete_dividend_before_expiry=False)])
    return dict(option_captures=[quote_capture_fixture("option")], underlying_capture=quote_capture_fixture("stock"),
        oi_df=oi, asof=QUOTE_DAY, root="SPY", source_context=context, valuation_at=QUOTE_TARGET,
        evaluated_at=QUOTE_EVALUATED, max_quote_age_seconds=2., r=.02, q=0.,
        quote_policy=dict(option_conditions=[0], stock_conditions=[0], option_exchanges=[1],
            stock_exchanges=[1], stock_condition_basis="synthetic explicit consolidated quote policy"))


def test_distinct_events_prove_common_asof_without_backdating_availability():
    args = quote_valuation_case()
    g, oi, context = compose_quote_valuation_inputs(**args)
    assert g.iloc[0].timestamp == QUOTE_DAY + "T14:59:59.000"
    assert g.iloc[0].underlying_timestamp == QUOTE_DAY + "T14:59:58.750"
    assert context["clocks"] == args["source_context"]["clocks"]
    assert context["quote_valuation"]["pit_qualified"] is False
    assert context["quote_valuation"]["kind"] == "conditional_asof_reconstruction"
    assert context["quote_valuation"]["underlying_quote"]["receipt"]["received_at"] == QUOTE_RECEIVED
    assert "source_snapshot_ref" not in args["source_context"]
    out = build_admitted_scenario_surface(g, oi, QUOTE_DAY, "SPY", source_context=context,
        request=dict(price_grid=[100., 101.], horizons_minutes=[0, 30], r=.02, q=0., mult=100., pm=.01))
    assert out["status"] == "complete_for_supplied_universe", out
    assert out["authority"]["can_publish"] is False


@pytest.mark.parametrize("changes", [
    dict(timestamp=QUOTE_DAY + "T15:00:00.001"),
    dict(timestamp=QUOTE_DAY + "T14:59:55.000"),
    dict(symbol="QQQ"), dict(expiration="2026-10-29"), dict(right="PUT"),
    dict(bid="2.02", ask="2.01"), dict(bid_size="0"), dict(ask_size="0"),
    dict(bid="NaN"), dict(ask="Infinity"), dict(bid="malformed"), dict(strike="malformed"), dict(bid_condition="99"),
    dict(ask_exchange="999"), dict(bid="0.001", ask="0.002"),
])
def test_invalid_option_withholds_whole_supplied_cohort(changes):
    args = quote_valuation_case()
    args["option_captures"] = [quote_capture_fixture("option", changes)]
    with pytest.raises(ValueError):
        compose_quote_valuation_inputs(**args)


@pytest.mark.parametrize("changes", [dict(timestamp=QUOTE_DAY + "T14:59:55.000"),
    dict(timestamp=QUOTE_DAY + "T15:00:00.001"), dict(bid="100.02", ask="100.01"), dict(ask_size="0")])
def test_invalid_underlying_is_not_repaired_by_option_clock(changes):
    args = quote_valuation_case()
    args["underlying_capture"] = quote_capture_fixture("stock", changes)
    with pytest.raises(ValueError):
        compose_quote_valuation_inputs(**args)


@pytest.mark.parametrize("mutation", ["missing", "duplicate_capture", "missing_expected", "duplicate_oi", "missing_oi", "duplicate_tick"])
def test_population_is_never_trimmed_to_good_members(mutation):
    args = quote_valuation_case()
    if mutation == "missing":
        args["option_captures"] = []
    elif mutation == "duplicate_capture":
        args["option_captures"] *= 2
    elif mutation == "missing_expected":
        args["source_context"]["expected_contracts"].append(dict(root="SPY", expiration="2026-10-28", strike=101., right="C"))
    elif mutation == "duplicate_oi":
        args["oi_df"] = pd.concat([args["oi_df"], args["oi_df"]], ignore_index=True)
    elif mutation == "missing_oi":
        args["oi_df"] = args["oi_df"].iloc[0:0]
    else:
        original = quote_capture_fixture("option")
        rows = list(csv.DictReader(io.StringIO(original["raw"].decode())))
        args["option_captures"] = [quote_capture_fixture("option", extra_rows=rows)]
    with pytest.raises(ValueError):
        compose_quote_valuation_inputs(**args)


@pytest.mark.parametrize("field,value", [
    ("economic_expiry_at", None), ("discrete_dividend_before_expiry", None),
    ("discrete_dividend_before_expiry", True), ("exercise_style", "european"),
    ("multiplier", 10), ("available_at", "2026-10-22T12:00:00Z"),
])
def test_terms_and_no_dividend_facts_cannot_be_defaulted(field, value):
    args = quote_valuation_case()
    args["source_context"]["contract_terms"][0][field] = value
    with pytest.raises(ValueError):
        compose_quote_valuation_inputs(**args)


@pytest.mark.parametrize("field,value", [
    ("option_observed_at", QUOTE_DAY + "T18:59:59Z"),
    ("underlying_observed_at", QUOTE_DAY + "T18:59:58Z"),
    ("available_at", QUOTE_TARGET), ("greeks_available_at", QUOTE_TARGET), ("oi_available_at", QUOTE_TARGET),
])
def test_events_or_capture_time_cannot_be_silently_relabelled_as_valuation(field, value):
    args = quote_valuation_case()
    args["source_context"]["clocks"][field] = value
    with pytest.raises(ValueError):
        compose_quote_valuation_inputs(**args)


def test_raw_hash_and_requested_end_are_bound():
    args = quote_valuation_case()
    args["option_captures"][0]["raw"] += b"\n"
    with pytest.raises(ValueError, match="raw bytes"):
        compose_quote_valuation_inputs(**args)
    args = quote_valuation_case()
    args["valuation_at"] = QUOTE_DAY + "T18:59:59Z"
    args["source_context"]["clocks"].update(option_observed_at=args["valuation_at"], underlying_observed_at=args["valuation_at"])
    with pytest.raises(ValueError, match="window"):
        compose_quote_valuation_inputs(**args)


@pytest.mark.parametrize("field,value", [("r", None), ("r", -0.01), ("q", .01), ("max_quote_age_seconds", 0)])
def test_explicit_domain_policy_is_required(field, value):
    args = quote_valuation_case()
    args[field] = value
    with pytest.raises(ValueError):
        compose_quote_valuation_inputs(**args)


def test_wrong_or_missing_underlying_venue_refused_before_receipt():
    for value in ("nqb", None):
        with pytest.raises(ValueError):
            quote_capture_fixture("stock", params_changes={"venue": value})


def test_existing_strict_equal_valuation_guard_still_refuses_mismatch():
    args = quote_valuation_case()
    g, oi, context = compose_quote_valuation_inputs(**args)
    context["clocks"]["underlying_observed_at"] = QUOTE_DAY + "T18:59:59Z"
    out = build_admitted_scenario_surface(g, oi, QUOTE_DAY, "SPY", source_context=context,
        request=dict(price_grid=[100., 101.], horizons_minutes=[0], r=.02, q=0., mult=100., pm=.01))
    assert out["unavailable_reasons"] == ["underlying_observation_mismatch"]


def test_last_tick_is_selected_and_invalid_last_book_is_not_skipped():
    args = quote_valuation_case()
    older = list(csv.DictReader(io.StringIO(quote_capture_fixture("option")["raw"].decode())))[0]
    older.update(timestamp=QUOTE_DAY + "T14:59:58.500", bid="1.89", ask="1.91")
    args["option_captures"] = [quote_capture_fixture("option", extra_rows=[older])]
    g, _, context = compose_quote_valuation_inputs(**args)
    assert g.iloc[0].timestamp == QUOTE_DAY + "T14:59:59.000"
    assert context["quote_valuation"]["option_quotes"][0]["mid"] == 2.
    args["option_captures"] = [quote_capture_fixture("option", dict(bid_condition="99"), extra_rows=[older])]
    with pytest.raises(ValueError, match="Nonfirm"):
        compose_quote_valuation_inputs(**args)


@pytest.mark.parametrize("field", ["option_conditions", "stock_conditions", "option_exchanges", "stock_exchanges", "stock_condition_basis"])
def test_missing_mark_policy_never_enables_a_default(field):
    args = quote_valuation_case()
    del args["quote_policy"][field]
    with pytest.raises(ValueError):
        compose_quote_valuation_inputs(**args)


def test_captured_later_can_never_claim_known_by_target():
    args = quote_valuation_case()
    args["evaluated_at"] = QUOTE_TARGET
    args["source_context"]["clocks"].update(available_at=QUOTE_TARGET, greeks_available_at=QUOTE_TARGET)
    with pytest.raises(ValueError, match="unavailable"):
        compose_quote_valuation_inputs(**args)


def test_declared_capability_refusal_survives_new_composition():
    args = quote_valuation_case()
    args["source_context"]["capabilities"] = {"repricing": False}
    g, oi, context = compose_quote_valuation_inputs(**args)
    out = build_admitted_scenario_surface(g, oi, QUOTE_DAY, "SPY", source_context=context,
        request=dict(price_grid=[100., 101.], horizons_minutes=[0], r=.02, q=0., mult=100., pm=.01))
    assert out["unavailable_reasons"] == ["source_capability_refused"]


@pytest.mark.parametrize("field", ["contract_terms", "expected_contracts"])
@pytest.mark.parametrize("row", [None, "malformed", 123, [], True])
def test_quote_composer_malformed_rows_raise_value_error(field, row):
    args = quote_valuation_case()
    args["source_context"][field] = [row]
    with pytest.raises(ValueError, match="row shape"):
        compose_quote_valuation_inputs(**args)


def quoted_surface(g, oi, context):
    return build_admitted_scenario_surface(g, oi, QUOTE_DAY, "SPY", source_context=context,
        request=dict(price_grid=[100., 101.], horizons_minutes=[0], r=.02, q=0., mult=100., pm=.01))


def test_quote_capsule_survives_actual_scenario_output_and_json_roundtrip():
    import json
    args = quote_valuation_case()
    g, oi, context = compose_quote_valuation_inputs(**args)
    wire_context = json.loads(json.dumps(context))
    out = quoted_surface(g, oi, wire_context)
    assert out["status"] == "complete_for_supplied_universe", out
    capsule = out["source"]["quote_valuation"]
    assert capsule == wire_context["quote_valuation"]
    assert capsule["option_quotes"][0]["raw_event_at"] == QUOTE_DAY + "T14:59:59.000"
    assert capsule["underlying_quote"]["raw_event_at"] == QUOTE_DAY + "T14:59:58.750"
    assert capsule["underlying_quote"]["receipt"]["received_at"] == QUOTE_RECEIVED
    assert capsule["valuation_at"] == QUOTE_TARGET
    assert capsule["evaluated_at"] == QUOTE_EVALUATED
    assert capsule["derived_input_sha256"] == wire_context["input_sha256"]
    assert capsule["pit_qualified"] is False
    assert capsule["historical_first_availability_established"] is False
    identity = capsule["implementation"]
    assert identity["kind"] == "local_python_implementation_fingerprint/v1"
    assert len(identity["sha256"]) == 64
    assert identity["sha256"] == out["pricing"]["iv_provenance"]["implementation_sha256"]
    assert identity["sha256"] in out["pricing"]["iv_provenance"]["model_ref"]
    capsule["pit_qualified"] = True
    assert context["quote_valuation"]["pit_qualified"] is False


@pytest.mark.parametrize("mutation", ["missing", "pit", "event", "availability", "model_ref", "implementation", "oversized"])
def test_quote_provenance_tampering_fails_closed(mutation):
    args = quote_valuation_case()
    g, oi, context = compose_quote_valuation_inputs(**args)
    capsule = context["quote_valuation"]
    if mutation == "missing":
        del context["quote_valuation"]
    elif mutation == "pit":
        capsule["pit_qualified"] = True
    elif mutation == "event":
        capsule["option_quotes"][0]["raw_event_at"] = QUOTE_TARGET
    elif mutation == "availability":
        capsule["underlying_quote"]["receipt"]["received_at"] = QUOTE_TARGET
    elif mutation == "model_ref":
        context["greek_provenance"]["iv"]["model_ref"] = "caller:fabricated-version"
    elif mutation == "implementation":
        capsule["implementation"]["sha256"] = "0" * 64
    else:
        capsule["padding"] = "x" * 262144
    out = quoted_surface(g, oi, context)
    assert out["status"] == "unavailable"
    assert out["unavailable_reasons"] == ["quote_valuation_provenance_unqualified"]
    assert "quote_valuation" not in out["source"]


def test_fingerprint_tracks_actual_executed_solver_code_and_constants(monkeypatch):
    import types
    from engine import options_scenario_admission as admission, intraday_greeks as kernel
    _, _, original = compose_quote_valuation_inputs(**quote_valuation_case())
    first = original["quote_valuation"]["implementation"]
    assert first == admission._quote_kernel_identity()
    solver = admission.implied_vol_vec
    constants = list(solver.__code__.co_consts)
    constants[0] = str(constants[0]) + " synthetic implementation mutation"
    changed = types.FunctionType(solver.__code__.replace(co_consts=tuple(constants)),
        solver.__globals__, solver.__name__, solver.__defaults__, solver.__closure__)
    monkeypatch.setattr(admission, "implied_vol_vec", changed)
    g, oi, second = compose_quote_valuation_inputs(**quote_valuation_case())
    assert first["sha256"] != second["quote_valuation"]["implementation"]["sha256"]
    assert original["source_snapshot_ref"] != second["source_snapshot_ref"]
    assert original["greek_provenance"]["iv"]["model_ref"] != second["greek_provenance"]["iv"]["model_ref"]
    assert quoted_surface(g, oi, second)["status"] == "complete_for_supplied_universe"
    monkeypatch.setattr(kernel, "IV_TOL", kernel.IV_TOL * 2)
    assert admission._quote_kernel_identity()["sha256"] != second["quote_valuation"]["implementation"]["sha256"]
    assert quoted_surface(g, oi, second)["unavailable_reasons"] == ["quote_valuation_provenance_unqualified"]


def test_resealing_cannot_turn_a_caller_fabricated_model_identity_into_local_identity():
    from engine.options_scenario_admission import _quote_capsule_ref
    g, oi, context = compose_quote_valuation_inputs(**quote_valuation_case())
    forged = "0" * 64
    context["quote_valuation"]["implementation"]["sha256"] = forged
    context["source_snapshot_ref"] = _quote_capsule_ref(context["quote_valuation"])
    iv = context["greek_provenance"]["iv"]
    iv.update(source_ref=context["source_snapshot_ref"], implementation_sha256=forged,
        model_ref="black_scholes_merton|engine.intraday_greeks.implied_vol_vec|local-implementation-sha256:" + forged)
    assert quoted_surface(g, oi, context)["unavailable_reasons"] == ["quote_valuation_provenance_unqualified"]


@pytest.mark.parametrize("frame,field,value", [
    ("greeks", "implied_vol", 1.5),
    ("greeks", "underlying_price", 150.),
    ("oi", "open_interest", 25),
])
def test_quote_numerical_frame_mutation_cannot_refresh_only_outer_digest(frame, field, value):
    from copy import deepcopy
    from engine.options_exposure_projection import exposure_input_digest
    g, oi, context = compose_quote_valuation_inputs(**quote_valuation_case())
    sealed_capsule = deepcopy(context["quote_valuation"])
    sealed_ref = context["source_snapshot_ref"]
    (g if frame == "greeks" else oi).loc[0, field] = value
    context["input_sha256"] = exposure_input_digest(g, oi, QUOTE_DAY, "SPY")
    out = quoted_surface(g, oi, context)
    assert out["status"] == "unavailable"
    assert out["unavailable_reasons"] == ["quote_valuation_provenance_unqualified"]
    assert context["quote_valuation"] == sealed_capsule
    assert context["source_snapshot_ref"] == sealed_ref


def test_quote_derived_digest_is_required_even_with_a_resealed_capsule():
    from engine.options_scenario_admission import _quote_capsule_ref
    g, oi, context = compose_quote_valuation_inputs(**quote_valuation_case())
    del context["quote_valuation"]["derived_input_sha256"]
    context["source_snapshot_ref"] = _quote_capsule_ref(context["quote_valuation"])
    context["greek_provenance"]["iv"]["source_ref"] = context["source_snapshot_ref"]
    assert quoted_surface(g, oi, context)["unavailable_reasons"] == ["quote_valuation_provenance_unqualified"]
