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
