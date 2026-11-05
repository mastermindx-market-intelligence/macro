"""Identical-funding monthly addition accounts; no indicator optimization."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_inputs(prices_dir):
    c = json.loads((ROOT / 'config.json').read_text())
    m = json.loads((ROOT / 'inputs/source_manifest.json').read_text())
    rp = ROOT / 'inputs/signal_roster.csv'
    assert sha(rp) == m['signal_roster_sha256']
    prices = {}
    for a in m['assets']:
        path = prices_dir / (a['ticker'] + '.parquet')
        assert sha(path) == a['parquet_sha256'], a['ticker']
        d = pd.read_parquet(path).sort_index().loc['2010-01-04':c['cutoff']]
        assert d.index.is_unique and d.index.is_monotonic_increasing
        f = d.adjclose / d.close
        prices[a['ticker']] = d[['open', 'close']].mul(f, axis=0)
    original = prices['SPY'].index
    ix = original[original >= pd.Timestamp(c['start'])]
    assert ix[-1] == pd.Timestamp(c['cutoff'])
    needed = set(sum(c['baskets'].values(), []))
    for name in needed:
        d = prices[name].reindex(ix)
        assert np.isfinite(d.to_numpy()).all() and (d.to_numpy() > 0).all(), name
        prices[name] = d
    r = pd.read_csv(rp)
    for row in r.itertuples():
        assert str(original[row.signal_t].date()) == row.signal_date
        assert row.entry_t == row.signal_t + 1
        if row.executable:
            assert str(original[row.entry_t].date()) == row.entry_date
    eligible = r.loc[r.executable & (r.entry_date >= str(ix[0].date())) &
                     (r.entry_date <= str(ix[-1].date()))].copy()
    calendar = (eligible.groupby('entry_date', sort=True)
                .agg(nominations=('symbol', 'size'),
                     symbols=('symbol', lambda s: '|'.join(sorted(s))))
                .reset_index())
    dates_to_i = {str(d.date()): i for i, d in enumerate(ix)}
    calendar['entry_i'] = calendar.entry_date.map(dates_to_i)
    assert calendar.entry_i.notna().all()
    return c, m, prices, ix, calendar


def make_schedule(ix, signal_indices, contribution, session_calendar):
    """Certify deadlines from a fixed calendar, independently of the priced prefix."""
    periods = ix.to_period('M')
    calendar_periods = session_calendar.to_period('M')
    assert ix.isin(session_calendar).all()
    known_ends = {}
    for month in calendar_periods.unique():
        last = int(np.flatnonzero(calendar_periods == month)[-1])
        if last + 1 < len(session_calendar) and calendar_periods[last + 1] != month:
            known_ends[month] = session_calendar[last]
    positions = {date: i for i, date in enumerate(ix)}
    signal_indices = set(int(x) for x in signal_indices)
    records = []
    for month in periods.unique():
        indices = np.flatnonzero(periods == month)
        first, last = int(indices[0]), int(indices[-1])
        # A cutoff cannot create or erase a deadline already known from the fixed calendar.
        deadline = positions.get(known_ends.get(month))
        candidates = sorted(i for i in signal_indices if first <= i <= last)
        signal_buy = candidates[0] if candidates else deadline
        signal_reason = ('signal_at_deadline' if signal_buy is not None and signal_buy == deadline
                         and candidates else 'signal' if candidates else
                         'deadline' if deadline is not None else 'pending')
        records.append({'month': str(month), 'fund_i': first, 'deadline_i': deadline,
                        'amount': float(contribution),
                        'IMMEDIATE': first, 'SIGNAL': signal_buy, 'MONTH_END': deadline,
                        'SIGNAL_reason': signal_reason})
    return records


def waiting_components(budget, scheduled_open, buy_open, terminal_close, fee, cash_gross):
    """Per-asset identity, with unincurred fees separated for an unspent budget."""
    net_factor = (1-fee)/(1+fee)
    baseline = budget * net_factor * terminal_close / scheduled_open
    if buy_open is None:
        movement = budget * net_factor * (1-terminal_close/scheduled_open)
        interest = budget * (cash_gross-1)
        unincurred = budget * (1-net_factor)
        actual = budget * cash_gross
    else:
        factor = budget * net_factor * terminal_close
        movement = factor * (1/buy_open-1/scheduled_open)
        interest = factor * (cash_gross-1)/buy_open
        unincurred = 0.0
        actual = factor * cash_gross/buy_open
    assert math.isclose(movement+interest+unincurred,actual-baseline,abs_tol=1e-8)
    return movement, interest, unincurred, actual-baseline


def xirr(funding_dates, amounts, final_date, terminal):
    dates = list(funding_dates) + [final_date]
    flows = np.r_[-np.asarray(amounts, dtype=float), terminal]
    years = np.asarray([(d - dates[0]).days / 365.25 for d in dates])
    def npv(rate):
        return float(np.sum(flows / np.exp(np.log1p(rate) * years)))
    return float(brentq(npv, -0.9999, 100.0, xtol=1e-13))


def lot_value(lot, at_i, ix, opens, closes, fee, cash_rate):
    fund = lot['fund_i']
    if at_i < fund:
        return 0.0
    buy = lot['buy_i']
    if buy is None or buy > at_i:
        days = (ix[at_i] - ix[fund]).days
        return lot['amount'] * (1 + cash_rate) ** (days / 365.25)
    days = (ix[buy] - ix[fund]).days
    cash_gross = (1 + cash_rate) ** (days / 365.25)
    q = lot['amount'] * cash_gross / (1 + fee) / opens.shape[1] / opens[buy]
    return float(q @ closes[at_i]) * (1 - fee)


def simulate(ix, opens, closes, schedule, policy, fee, cash_rate):
    """Account unitization occurs at each preflow open; buy fees occur after flow."""
    n, k = opens.shape
    assert closes.shape == (n, k)
    lots = []
    for r in schedule:
        buy = r[policy]
        reason = r['SIGNAL_reason'] if policy == 'SIGNAL' else policy.lower() if buy is not None else 'pending'
        lots.append({**r, 'buy_i': buy, 'reason': reason})
    funding = {r['fund_i']: r for r in lots}
    buying = {r['buy_i']: r for r in lots if r['buy_i'] is not None}
    assert len(buying) == sum(r['buy_i'] is not None for r in lots)
    shares = np.zeros(k)
    cash = 0.0
    units = 0.0
    contributed = 0.0
    fees = 0.0
    interest = 0.0
    rows = []
    for i, date in enumerate(ix):
        if i:
            grow = (1 + cash_rate) ** ((date - ix[i - 1]).days / 365.25)
            interest += cash * (grow - 1)
            cash *= grow
        preflow = float(shares @ opens[i] + cash)
        if i in funding:
            amount = funding[i]['amount']
            pre_nav = preflow / units if units else 1.0
            assert pre_nav > 0
            units += amount / pre_nav
            cash += amount
            contributed += amount
            assert math.isclose((preflow + amount) / units, pre_nav, abs_tol=1e-10)
        if i in buying:
            lot = buying[i]
            assert lot['fund_i'] <= i
            budget = lot['amount'] * (1 + cash_rate) ** ((date - ix[lot['fund_i']]).days / 365.25)
            assert cash + 1e-7 >= budget
            notional = budget / (1 + fee)
            shares += notional / k / opens[i]
            cash -= budget
            if abs(cash) < 1e-8:
                cash = 0.0
            fees += budget - notional
        invested = float(shares @ closes[i])
        gross_wealth = invested + cash
        terminal_fee = invested * fee if i == n - 1 else 0.0
        wealth = gross_wealth - terminal_fee
        assert cash >= -1e-8 and wealth > 0 and units > 0
        rows.append({'date': str(date.date()), 'wealth': wealth, 'gross_wealth': gross_wealth,
                     'cash': cash, 'invested': invested, 'invested_fraction': invested / gross_wealth,
                     'units': units, 'unit_nav': wealth / units,
                     'contributed': contributed, 'buy_fees_cumulative': fees,
                     'cash_interest_cumulative': interest, 'terminal_fee': terminal_fee})
    daily = pd.DataFrame(rows)
    terminal_lots = sum(lot_value(r, n - 1, ix, opens, closes, fee, cash_rate) for r in lots)
    assert math.isclose(terminal_lots, rows[-1]['wealth'], rel_tol=1e-11, abs_tol=1e-7)
    return daily, lots


def summarize(daily, lots, ix, policy, calendar, fee, cash_rate):
    nav = daily.unit_nav.to_numpy()
    peaks = np.maximum.accumulate(np.r_[1.0, nav])[1:]
    dd = nav / peaks - 1
    trough = int(np.argmin(dd))
    peak = int(np.argmax(nav[:trough + 1])) if nav[:trough + 1].max() >= 1 else 0
    ret = nav / np.r_[1.0, nav[:-1]] - 1
    longest = run = 0
    for v in dd:
        run = run + 1 if v < -1e-12 else 0
        longest = max(longest, run)
    delay = [r['buy_i'] - r['fund_i'] for r in lots if r['buy_i'] is not None]
    bought_on_signal = {r['buy_i'] for r in lots if r['reason'] in ('signal', 'signal_at_deadline')}
    years = (ix[-1] - ix[0]).days / 365.25
    last = daily.iloc[-1]
    out = {'months': len(lots), 'contributions': last.contributed, 'terminal_wealth': last.wealth,
           'net_gain': last.wealth - last.contributed,
           'xirr': xirr([ix[r['fund_i']] for r in lots], [r['amount'] for r in lots], ix[-1], last.wealth),
           'twr_annualized': nav[-1] ** (1 / years) - 1,
           'max_drawdown': float(dd.min()), 'annual_vol': float(np.std(ret, ddof=1) * np.sqrt(252)),
           'underwater_fraction': float(np.mean(dd < -1e-12)), 'max_underwater_sessions': longest,
           'drawdown_peak': str(ix[peak].date()), 'drawdown_trough': str(ix[trough].date()),
           'drawdown_peak_exposure': float(daily.iloc[peak].invested_fraction),
           'drawdown_trough_exposure': float(daily.iloc[trough].invested_fraction),
           'average_exposure': float(daily.invested_fraction.mean()),
           'peak_exposure': float(daily.invested_fraction.max()),
           'purchase_fees': last.buy_fees_cumulative, 'terminal_fee': last.terminal_fee,
           'cash_interest': last.cash_interest_cumulative, 'pending_cash': last.cash,
           'purchased_months': len(delay), 'pending_months': sum(r['buy_i'] is None for r in lots),
           'signal_months': sum(r['reason'] == 'signal' for r in lots),
           'signal_at_deadline_months': sum(r['reason'] == 'signal_at_deadline' for r in lots),
           'deadline_months': sum(r['reason'] == 'deadline' for r in lots),
           'mean_delay_sessions': float(np.mean(delay)) if delay else None,
           'max_delay_sessions': max(delay) if delay else None,
           'eligible_calendar_dates': len(calendar),
           'unfunded_signal_dates': len(calendar) - len(bought_on_signal) if policy == 'SIGNAL' else None}
    annual = []
    previous = 1.0
    for year, d in daily.groupby(daily.date.str[:4]):
        end = float(d.unit_nav.iloc[-1])
        annual.append({'year': int(year), 'unitized_return': end / previous - 1,
                       'partial_year': year == str(ix[-1].year)})
        previous = end
    return out, annual


def block_interval(values, c):
    a = np.asarray(values, float)
    rng = np.random.default_rng(c['seed'])
    n, b = len(a), c['block_months']
    assert n >= 60
    starts = rng.integers(n, size=(c['bootstrap_draws'], math.ceil(n / b)))
    indices = ((starts[:, :, None] + np.arange(b)) % n).reshape(len(starts), -1)[:, :n]
    means = a[indices].mean(axis=1)
    return [float(x) for x in np.quantile(means, [0.025, 0.975])]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--prices-dir', type=Path, required=True)
    args = p.parse_args()
    c, manifest, prices, ix, calendar = load_inputs(args.prices_dir)
    schedule = make_schedule(ix, calendar.entry_i, c['monthly_contribution'], ix)
    out = ROOT / 'results'
    out.mkdir(exist_ok=True)
    calendar.to_csv(out / 'signal_calendar.csv', index=False)
    paths, summaries, annuals, cohort_rows, lot_rows, attribution = [], [], [], [], [], []
    contrasts, cohort_summaries = [], []
    for scenario, terms in c['scenarios'].items():
        fee, rate = terms['fee'], terms['cash_rate']
        for basket, names in c['baskets'].items():
            opens = np.column_stack([prices[n].open.to_numpy() for n in names])
            closes = np.column_stack([prices[n].close.to_numpy() for n in names])
            account, cohorts = {}, {}
            for policy in c['policies']:
                daily, lots = simulate(ix, opens, closes, schedule, policy, fee, rate)
                meta = {'scenario': scenario, 'basket': basket, 'policy': policy}
                summary, ann = summarize(daily, lots, ix, policy, calendar, fee, rate)
                summaries.append({**meta, **summary})
                annuals.extend([{**meta, **a} for a in ann])
                paths.append(daily.assign(**meta))
                account[policy] = summary
                values = []
                for lot in lots:
                    f, buy = lot['fund_i'], lot['buy_i']
                    endpoint = f + c['cohort_sessions']
                    value = lot_value(lot, endpoint, ix, opens, closes, fee, rate) if endpoint < len(ix) else np.nan
                    terminal = lot_value(lot, len(ix)-1, ix, opens, closes, fee, rate)
                    values.append(value)
                    row = {**meta, 'month': lot['month'], 'fund_date': str(ix[f].date()),
                           'buy_date': str(ix[buy].date()) if buy is not None else '',
                           'deadline_date': str(ix[lot['deadline_i']].date()) if lot['deadline_i'] is not None else '',
                           'reason': lot['reason'], 'delay_sessions': buy-f if buy is not None else np.nan,
                           'delay_calendar_days': (ix[buy]-ix[f]).days if buy is not None else np.nan,
                           'contribution': lot['amount'], 'terminal_wealth': terminal,
                           'cohort_mature': endpoint < len(ix),
                           'cohort_end': str(ix[endpoint].date()) if endpoint < len(ix) else '',
                           'cohort_wealth': value, 'cohort_return': value / lot['amount'] - 1}
                    lot_rows.append(row)
                    if endpoint < len(ix):
                        cohort_rows.append(row)
                    if policy != 'IMMEDIATE':
                        for j, name in enumerate(names):
                            budget = lot['amount'] / len(names)
                            if buy is not None:
                                gross = (1+rate) ** ((ix[buy]-ix[f]).days/365.25)
                                wait_return = opens[buy,j]/opens[f,j]-1
                                units_gain = gross*opens[f,j]/opens[buy,j]-1
                            else:
                                gross = (1+rate) ** ((ix[-1]-ix[f]).days/365.25)
                                wait_return = closes[-1,j]/opens[f,j]-1
                                units_gain = np.nan
                            movement, interest, unincurred, delta = waiting_components(
                                budget,opens[f,j],opens[buy,j] if buy is not None else None,
                                closes[-1,j],fee,gross)
                            attribution.append({**meta, 'month': lot['month'], 'symbol': name,
                                'fund_date': str(ix[f].date()),
                                'buy_date': str(ix[buy].date()) if buy is not None else '',
                                'reason': lot['reason'], 'cash_gross_wait': gross,
                                'asset_return_while_waiting': wait_return,
                                'relative_units_acquired': units_gain,
                                'scheduled_adjusted_units': budget/(1+fee)/opens[f,j],
                                'actual_adjusted_units': budget*gross/(1+fee)/opens[buy,j] if buy is not None else 0.0,
                                'price_movement_component': movement,
                                'cash_interest_component': interest,
                                'unincurred_fee_component': unincurred,
                                'terminal_difference': delta})
                cohorts[policy] = np.asarray(values)
            for a, b in [('SIGNAL','IMMEDIATE'), ('SIGNAL','MONTH_END'), ('MONTH_END','IMMEDIATE')]:
                contrasts.append({'scenario': scenario, 'basket': basket, 'comparison': a+'-'+b,
                    'terminal_difference': account[a]['terminal_wealth']-account[b]['terminal_wealth'],
                    'difference_pct_contributions': (account[a]['terminal_wealth']-account[b]['terminal_wealth'])/account[a]['contributions']*100,
                    'xirr_difference_pp': (account[a]['xirr']-account[b]['xirr'])*100,
                    'max_drawdown_difference_pp': (account[a]['max_drawdown']-account[b]['max_drawdown'])*100})
                mask = np.isfinite(cohorts[a]) & np.isfinite(cohorts[b])
                diff = (cohorts[a][mask]-cohorts[b][mask])/c['monthly_contribution']*100
                lo, hi = block_interval(diff, c)
                cohort_summaries.append({'scenario':scenario, 'basket':basket, 'comparison':a+'-'+b,
                    'mature_months':int(mask.sum()), 'immature_months':int((~mask).sum()),
                    'mean_difference_pp':float(diff.mean()), 'median_difference_pp':float(np.median(diff)),
                    'positive_difference_fraction':float(np.mean(diff>1e-9)),
                    'negative_difference_fraction':float(np.mean(diff < -1e-9)),
                    'tie_fraction':float(np.mean(np.abs(diff)<=1e-9)),
                    'difference_q10_pp':float(np.quantile(diff,.1)),
                    'block95_low_pp':lo, 'block95_high_pp':hi})
    for filename, records in [('account_summary',summaries),('annual_returns',annuals),
        ('contribution_ledger',lot_rows),('completed_cohorts',cohort_rows),
        ('waiting_attribution',attribution),('account_contrasts',contrasts),('cohort_contrasts',cohort_summaries)]:
        pd.DataFrame(records).to_csv(out / (filename+'.csv'), index=False)
    pd.concat(paths, ignore_index=True).to_csv(out/'daily_paths.csv.gz', index=False, compression={'method':'gzip','mtime':0})
    attr = pd.DataFrame(attribution)
    attr['funding_year'] = attr.month.str[:4].astype(int)
    grouped = attr.groupby(['scenario','basket','policy','funding_year','reason'],dropna=False)[
        ['price_movement_component','cash_interest_component','unincurred_fee_component','terminal_difference']].sum().reset_index()
    grouped.to_csv(out/'funding_year_attribution.csv', index=False)
    cohort = pd.DataFrame(cohort_rows)
    cohort['funding_year'] = cohort.month.str[:4].astype(int)
    cohort.groupby(['scenario','basket','policy','funding_year']).agg(
        months=('month','size'),positive_fraction=('cohort_return',lambda x:float((x>0).mean())),
        mean_return=('cohort_return','mean'),worst_return=('cohort_return','min')).reset_index().to_csv(out/'cohort_year_summary.csv',index=False)
    absolute = cohort.groupby(['scenario','basket','policy']).agg(
        months=('month','size'),positive_fraction=('cohort_return',lambda x:float((x>0).mean())),
        mean_return=('cohort_return','mean'),median_return=('cohort_return','median'),
        q10_return=('cohort_return',lambda x:float(x.quantile(.1))),worst_return=('cohort_return','min')).reset_index()
    absolute.to_csv(out/'cohort_absolute_summary.csv',index=False)
    cohort['funding_half'] = np.where(cohort.funding_year <= 2022,'2020-2022','2023-cutoff')
    cohort.groupby(['scenario','basket','policy','funding_half']).agg(
        months=('month','size'),positive_fraction=('cohort_return',lambda x:float((x>0).mean())),
        mean_return=('cohort_return','mean'),worst_return=('cohort_return','min')).reset_index().to_csv(out/'cohort_half_summary.csv',index=False)
    for row in contrasts:
        if row['comparison'].endswith('-IMMEDIATE'):
            a = attr[(attr.scenario==row['scenario']) & (attr.basket==row['basket']) &
                     (attr.policy==row['comparison'].split('-')[0])].terminal_difference.sum()
            assert math.isclose(a,row['terminal_difference'],abs_tol=1e-6)
    report = {'protocol_sha256':sha(ROOT/'PROTOCOL.md'), 'config_sha256':sha(ROOT/'config.json'),
        'executed_analyze_sha256':sha(ROOT/'analyze.py'),
        'verification_source_sha256':sha(ROOT/'verify.py'),
        'input_manifest_sha256':sha(ROOT/'inputs/source_manifest.json'),
        'sessions':len(ix), 'months':len(schedule), 'signal_nominations':manifest['signal_rows'],
        'signal_execution_dates':len(calendar), 'source_final_unexecutable':int((~pd.read_csv(ROOT/'inputs/signal_roster.csv').executable).sum()),
        'price_files_verified':len(manifest['assets']), 'accounts':len(summaries),
        'all_account_lot_terminal_identities':True,'all_attribution_identities':True,
        'history_status':'exposed exploratory; no untouched holdout'}
    (out/'run_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    print(pd.DataFrame(contrasts).query("scenario=='PRIMARY'").to_string(index=False))


if __name__ == '__main__':
    main()
