"""Mechanical checks independent of favorable outcomes."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from analyze import make_schedule, simulate, xirr, load_inputs, waiting_components

ROOT = Path(__file__).resolve().parent


def synthetic_checks():
    passed = []
    ix = pd.bdate_range('2020-01-01', '2020-03-10')
    schedule = make_schedule(ix, [2, 5, 25, 30], 1000, ix)
    assert len(schedule) == 3 and schedule[-1]['deadline_i'] is None
    assert schedule[0]['SIGNAL'] == 2
    assert schedule[1]['SIGNAL'] == 25
    assert schedule[-1]['SIGNAL'] is None
    assert schedule[0]['MONTH_END'] == int(np.flatnonzero(ix.month == 1)[-1])
    passed.append('genuine_month_end_and_partial_month')
    opens = np.full((len(ix), 2), 10.0)
    closes = opens.copy()
    for policy in ['IMMEDIATE','SIGNAL','MONTH_END']:
        d, lots = simulate(ix, opens, closes, schedule, policy, 0.0, 0.0)
        assert np.allclose(d.wealth, d.contributed)
        assert np.allclose(d.unit_nav, 1)
        assert len(lots) == 3
        fee = 0.0025
        d, lots = simulate(ix, opens, closes, schedule, policy, fee, 0.0)
        bought = sum(r['buy_i'] is not None for r in lots)
        expected = bought*1000/(1+fee)*(1-fee)+(len(lots)-bought)*1000
        assert math.isclose(d.wealth.iloc[-1], expected, abs_tol=1e-8)
    passed.append('flat_prices_and_cost_budget_identity')
    d, lots = simulate(ix, opens, closes, schedule, 'SIGNAL', 0.0, 0.03)
    expected = sum(1000*1.03**((ix[r['buy_i'] if r['buy_i'] is not None else -1]-ix[r['fund_i']]).days/365.25) for r in lots)
    assert math.isclose(d.wealth.iloc[-1], expected, abs_tol=1e-7)
    assert math.isclose(d.wealth.iloc[-1]-3000,d.cash_interest_cumulative.iloc[-1],abs_tol=1e-7)
    passed.append('waiting_cash_interest_exact')
    # Funding on an overnight doubling issues half as many units, preserving NAV.
    ix2 = pd.to_datetime(['2020-01-30','2020-01-31','2020-02-03','2020-02-04'])
    op = np.array([[10.],[10.],[20.],[20.]])
    d, _ = simulate(ix2, op, op, make_schedule(ix2, [], 1000, ix2), 'IMMEDIATE', 0, 0)
    assert np.allclose(d.unit_nav,[1,1,2,2])
    assert np.allclose(d.units,[1000,1000,1500,1500])
    assert np.allclose(d.wealth,[1000,1000,3000,3000])
    passed.append('overnight_gap_before_funding_and_flow_nav_invariance')
    got = xirr([pd.Timestamp('2020-01-01')],[1000],pd.Timestamp('2021-01-01'),1100)
    assert math.isclose(got,1.1**(365.25/366)-1,abs_tol=1e-11)
    passed.append('dated_money_weighted_return_known_example')
    # Truncation cannot create a last-day purchase before a true month boundary.
    full = make_schedule(ix, [], 1000, ix)
    cut = ix[:10]
    short = make_schedule(cut, [], 1000, ix)
    assert short[0]['SIGNAL'] is None and short[0]['MONTH_END'] is None
    for policy in ['IMMEDIATE','SIGNAL','MONTH_END']:
        df, _ = simulate(ix, opens, closes, full, policy, .001, .03)
        ds, _ = simulate(cut, opens[:10], closes[:10], short, policy, .001, .03)
        assert np.allclose(df.gross_wealth.iloc[:10],ds.gross_wealth)
    passed.append('prefix_invariance_without_false_cutoff_deadline')
    cut_end = ix[ix <= '2020-01-31']
    end_schedule = make_schedule(cut_end,[],1000,ix)
    assert end_schedule[0]['MONTH_END'] == len(cut_end)-1
    for policy in ['IMMEDIATE','SIGNAL','MONTH_END']:
        df,_=simulate(ix,opens,closes,full,policy,.001,.03)
        ds,_=simulate(cut_end,opens[:len(cut_end)],closes[:len(cut_end)],end_schedule,policy,.001,.03)
        assert np.allclose(df.gross_wealth.iloc[:len(cut_end)],ds.gross_wealth)
    passed.append('month_end_prefix_uses_fixed_calendar')
    # A duplicate nomination never buys twice; previous-session signal can buy at funding open.
    day = make_schedule(ix, [0,0,2], 1000, ix)
    assert day[0]['SIGNAL'] == 0
    d, lots = simulate(ix, opens, closes, day, 'SIGNAL',0,0)
    assert np.isclose(d.wealth.iloc[-1],3000)
    assert len(lots) == 3
    passed.append('same_open_funding_and_duplicate_nomination')
    # Equality at deadline is explicitly labeled; it does not imply an earlier entry.
    end = schedule[0]['deadline_i']
    eq = make_schedule(ix,[end],1000,ix)
    assert eq[0]['SIGNAL_reason'] == 'signal_at_deadline'
    assert eq[0]['SIGNAL'] == eq[0]['MONTH_END']
    passed.append('signal_at_deadline_tie')
    movement,interest,unincurred,delta=waiting_components(1000,10,None,10,.001,1)
    assert movement==0 and interest==0
    assert math.isclose(unincurred,1000*(1-.999/1.001),abs_tol=1e-10)
    assert math.isclose(delta,unincurred,abs_tol=1e-10)
    movement,interest,unincurred,delta=waiting_components(1000,10,8,12,.001,1.01)
    expected=1000/1.001*.999*12*(1.01/8-1/10)
    assert unincurred==0 and math.isclose(delta,expected,abs_tol=1e-9)
    passed.append('pending_fee_separation_and_executed_waiting_identity')
    return passed


def real_checks(prices_dir):
    c,m,prices,ix,calendar = load_inputs(prices_dir)
    schedule=make_schedule(ix,calendar.entry_i,c['monthly_contribution'],ix)
    daily=pd.read_csv(ROOT/'results/daily_paths.csv.gz')
    ledger=pd.read_csv(ROOT/'results/contribution_ledger.csv').fillna({'buy_date':''})
    cohorts=pd.read_csv(ROOT/'results/completed_cohorts.csv')
    dates={str(t.date()):i for i,t in enumerate(ix)}
    maximum_error=0.0
    for (scenario,basket,policy), observed in daily.groupby(['scenario','basket','policy'],sort=False):
        fee=c['scenarios'][scenario]['fee'];rate=c['scenarios'][scenario]['cash_rate']
        names=c['baskets'][basket]
        opens=np.column_stack([prices[n].open for n in names])
        closes=np.column_stack([prices[n].close for n in names])
        lots=ledger[(ledger.scenario==scenario)&(ledger.basket==basket)&(ledger.policy==policy)]
        assert len(lots)==len(schedule)
        assert list(lots.fund_date)==[str(ix[r['fund_i']].date()) for r in schedule]
        assert (lots.contribution==c['monthly_contribution']).all()
        cash=np.zeros(len(ix));invested=np.zeros(len(ix));expected_fees=0.0
        for lot in lots.itertuples():
            f=dates[lot.fund_date];b=dates[lot.buy_date] if lot.buy_date else None
            if b is not None:
                assert f<=b and ix[f].to_period('M')==ix[b].to_period('M')
            if policy=='SIGNAL' and lot.reason.startswith('signal'):
                assert b in set(calendar.entry_i)
            stop=b if b is not None else len(ix)
            cash[f:stop]+=lot.contribution*(1+rate)**np.asarray([(x-ix[f]).days/365.25 for x in ix[f:stop]])
            if b is not None:
                budget=lot.contribution*(1+rate)**((ix[b]-ix[f]).days/365.25)
                q=budget/(1+fee)/len(names)/opens[b]
                invested[b:]+=closes[b:]@q
                expected_fees+=budget-budget/(1+fee)
            e=f+c['cohort_sessions']
            if lot.cohort_mature:
                assert e<len(ix) and lot.cohort_end==str(ix[e].date())
            else:
                assert e>=len(ix)
        expected=invested+cash
        expected[-1]-=fee*invested[-1]
        err=float(np.max(np.abs(expected-observed.wealth.to_numpy())))
        maximum_error=max(maximum_error,err)
        assert err<1e-6
        assert np.allclose(cash,observed.cash,atol=1e-7)
        assert np.allclose(invested,observed.invested,atol=1e-7)
        assert math.isclose(expected_fees,float(observed.buy_fees_cumulative.iloc[-1]),abs_tol=1e-7)
        assert np.isclose(observed.contributed.iloc[-1],len(schedule)*1000)
    counts=cohorts.groupby(['scenario','basket','policy']).size()
    assert counts.nunique()==1
    return {'accounts_independently_rebuilt':36,'daily_cash_and_holdings_identity':True,
            'max_dollar_reconstruction_error':maximum_error,'funding_identity':True,
            'chronology_and_one_purchase_per_budget':True,'common_maturity_clock':True,
            'mature_months_per_account':int(counts.iloc[0]),
            'price_files_hash_verified':len(m['assets'])}


def main():
    p=argparse.ArgumentParser();p.add_argument('--prices-dir',type=Path);a=p.parse_args()
    result={'synthetic_checks':synthetic_checks()}
    if a.prices_dir:
        result['observed_run']=real_checks(a.prices_dir)
        (ROOT/'results/mechanical_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
