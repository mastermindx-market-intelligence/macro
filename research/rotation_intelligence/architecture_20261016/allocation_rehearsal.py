"""Synthetic-only reference cases for the existing study's future adapter.

No real input loader, market acquisition, candidate execution, registry or orders.
Calendar labels and clock ticks here are INVENTED ordered fixtures, not exchange
sessions or UTC attestations. Future implementation must use the existing owners.
The unchanged research-only rebalance function is reused, not a new cost engine.
"""
from __future__ import annotations
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from policy_accounting_witness import rebalance

SECTORS = ('XLB','XLC','XLE','XLF','XLI','XLK','XLP','XLRE','XLU','XLV','XLY')
INPUTS = SECTORS + ('SPY','BIL')
POLICIES = ('B0','B1','B2','B3','B4')
FRAME_KEYS = {'ticker','rows','capture_clock','durable_clock','read_clock',
              'basis','revision','evidence_mode'}
FLAGS = dict(scope='SYNTHETIC_REFERENCE_ONLY', market_data_read=False,
             source_rights_qualified=False, native_adaptation_built=False,
             native_scientific_qualification=False, investment_authority=False)


def positive(x):
    return type(x) in (int,float) and math.isfinite(x) and x > 0


def log_return(prices, span=63):
    if type(span) is not int or span < 1 or len(prices) != span+1:
        raise ValueError('exact price count required')
    if not all(positive(x) for x in prices):
        raise ValueError('finite positive prices required')
    return math.log(prices[-1])-math.log(prices[0])


def frame(ticker, rows, clock=25222):
    return dict(ticker=ticker,rows=tuple(rows),capture_clock=clock-2,
                durable_clock=clock-1,read_clock=clock,basis='total_return',
                revision='fixture-v1',evidence_mode='invented')


def decide(frames, anchor, cutoff, calendar):
    """Exercise a proposed contract on invented frames, never admit a source.

    The latest snapshot received by cutoff is selected as a WHOLE image. An
    invalid latest eligible image cannot silently rewind to an older valid one.
    Late snapshots are ignored, not relabelled as historically known.
    """
    if type(calendar) is not tuple or not calendar or any(type(i) is not int for i in calendar):
        raise ValueError('explicit ordered fixture calendar required')
    if list(calendar) != sorted(set(calendar)) or anchor not in calendar:
        raise ValueError('ambiguous fixture calendar')
    pos=calendar.index(anchor)
    if pos+1 >= len(calendar) or cutoff != calendar[pos+1]*100+8:
        raise ValueError('wrong next-session cutoff')
    out=dict(status='unavailable',anchor=anchor,cutoff=cutoff,reasons=[],weights={},
             prefix_digest=None,selected_images={},flags=dict(FLAGS))
    if pos < 252:
        out['reasons']=['WARMUP'];return out
    expected=calendar[pos-252:pos+1]
    by={t:[] for t in INPUTS}
    for f in frames:
        if type(f) is not dict or set(f) != FRAME_KEYS or f.get('ticker') not in by:
            out['reasons'].append('FRAME_SCHEMA');continue
        if type(f['read_clock']) is not int:
            out['reasons'].append('CLOCK_TYPE:'+f['ticker']);continue
        if f['read_clock'] <= cutoff:
            by[f['ticker']].append(f)
    prefixes={}
    for t,candidates in by.items():
        if not candidates:
            out['reasons'].append('MISSING:'+t);continue
        newest=max(f['read_clock'] for f in candidates)
        latest=[f for f in candidates if f['read_clock']==newest]
        if len(latest)!=1:
            out['reasons'].append('AMBIGUOUS_VINTAGE:'+t);continue
        f=latest[0]
        if f['basis']!='total_return' or f['evidence_mode']!='invented':
            out['reasons'].append('BASIS_OR_MODE:'+t);continue
        clocks=[f[k] for k in ('capture_clock','durable_clock','read_clock')]
        if not all(type(x) is int for x in clocks) or clocks!=sorted(clocks):
            out['reasons'].append('CLOCK_ORDER:'+t);continue
        rows=f['rows']
        if type(rows) is not tuple or any(type(r) is not tuple or len(r)!=2 for r in rows):
            out['reasons'].append('ROW_SCHEMA:'+t);continue
        labels=[r[0] for r in rows]
        if any(type(x) is not int for x in labels) or labels!=sorted(set(labels)):
            out['reasons'].append('ROW_ORDER:'+t);continue
        if any(s not in calendar or s*100+16>f['capture_clock'] for s in labels):
            out['reasons'].append('EVENT_AFTER_CAPTURE:'+t);continue
        selected=tuple((s,v) for s,v in rows if s in expected)
        if tuple(s for s,_ in selected)!=expected:
            out['reasons'].append('INCOMPLETE_PREFIX:'+t);continue
        if not all(positive(v) for _,v in selected):
            out['reasons'].append('INVALID_PRICE:'+t);continue
        prefixes[t]=[v for _,v in selected]
        out['selected_images'][t]=dict(revision=f['revision'],read_clock=f['read_clock'])
    if out['reasons']:
        out['reasons']=sorted(set(out['reasons']));return out
    r={t:log_return(values[-64:],63) for t,values in prefixes.items()}
    # Subtracting the same SPY return changes no cross-sectional sector rank.
    ranked=sorted(SECTORS,key=lambda t:(-(r[t]-r['SPY']),t))
    slots=[t if r[t]>r['BIL'] else 'BIL' for t in ranked[:3]]
    out['weights']={'B0':{'BIL':1.0},'B1':{'SPY':1.0},
                    'B2':{t:1/11 for t in SECTORS},
                    'B3':{t:1/3 for t in ranked[:3]},
                    'B4':{t:n/3 for t,n in sorted(Counter(slots).items())}}
    canonical=json.dumps(dict(expected=expected,prefixes=prefixes),sort_keys=True,
                         separators=(',',':'),allow_nan=False).encode()
    out.update(status='available',prefix_digest=hashlib.sha256(canonical).hexdigest())
    return out


def fixed_schedule(first_anchor, blocks, calendar):
    if type(blocks) is not int or blocks<1 or first_anchor not in calendar:
        raise ValueError('invalid schedule')
    first=calendar.index(first_anchor)
    if first+1+20*blocks>=len(calendar):
        raise ValueError('terminal session absent')
    return tuple(dict(anchor=calendar[first+20*k],entry=calendar[first+20*k+1],
                      end=calendar[first+20*(k+1)+1],
                      cutoff=calendar[first+20*k+1]*100+8) for k in range(blocks))


def policy_path(paths, decisions, schedule, policy, cost=0.001):
    """Invented total-return-proxy path; no orders or actual execution claims.

    Missing decisions/marks withhold the entire continuous comparison. This does
    not liquidate, reset wealth, skip an origin or prescribe a live contingency.
    """
    if policy not in POLICIES or len(decisions)!=len(schedule) or not schedule:
        raise ValueError('complete declared schedule required')
    if not positive(1-cost) or type(cost) not in (int,float) or cost<0:
        raise ValueError('invalid proportional cost')
    for d,s in zip(decisions,schedule):
        if d['anchor']!=s['anchor'] or d['cutoff']!=s['cutoff']:
            raise ValueError('decision origin mismatch')
    if any(d['status']!='available' for d in decisions):
        return dict(status='unavailable',reason='INCOMPLETE_DECISION_SCHEDULE',terminal_wealth=None)
    first,last=schedule[0]['entry'],schedule[-1]['end']
    for p,q in zip(schedule,schedule[1:]):
        if p['end']!=q['entry']:
            raise ValueError('noncontiguous wealth path')
    if set(paths)!=set(INPUTS) or any(any(i not in paths[t] or not positive(paths[t][i])
           for i in range(first,last+1)) for t in INPUTS):
        return dict(status='unavailable',reason='UNPRICEABLE',terminal_wealth=None)
    names=('SETTLEMENT',)+INPUTS
    h=[1.0]+[0.0]*len(INPUTS);fees=turnover=0.0
    steps=[];daily=[]
    decision_by_entry={s['entry']:(d,s) for d,s in zip(decisions,schedule)}
    for i in range(first,last+1):
        if i>first:
            h=[h[0]]+[v*paths[t][i]/paths[t][i-1] for t,v in zip(INPUTS,h[1:])]
        if i in decision_by_entry:
            d,s=decision_by_entry[i]
            w=[0.0]+[d['weights'][policy].get(t,0.0) for t in INPUTS]
            before=sum(h);x=rebalance(h,w,[0.0]+[cost]*len(INPUTS));h=x['holdings']
            fees+=x['fees'];turnover+=x['securities_traded_notional']
            steps.append(dict(entry=i,end=s['end'],before_wealth=before,
                              after_wealth=sum(h),fees=x['fees'],
                              securities_traded_notional=x['securities_traded_notional']))
        daily.append([i,sum(h)])
    liquidation=rebalance(h,[1.0]+[0.0]*len(INPUTS),[0.0]+[cost]*len(INPUTS))
    fees+=liquidation['fees'];turnover+=liquidation['securities_traded_notional']
    # Includes pre-entry unit wealth, entry costs, and the final liquidation mark.
    marks=[1.0]+[w for _,w in daily]+[liquidation['post_wealth']]
    peak=1.0;dd=0.0
    for w in marks:
        peak=max(peak,w);dd=min(dd,w/peak-1)
    return dict(status='complete_synthetic_path',terminal_wealth=liquidation['post_wealth'],
                total_fees=fees,securities_traded_notional=turnover,max_drawdown=dd,
                entries=steps,daily_wealth=daily,liquidation_fees=liquidation['fees'],flags=dict(FLAGS))


def demo(kind='flat'):
    """Only invented prices. Fixture 'sessions' are contiguous synthetic integers."""
    calendar=tuple(range(320));schedule=fixed_schedule(252,3,calendar)
    paths={t:{i:100.0 for i in calendar} for t in INPUTS}
    if kind=='leadership_then_reversal':
        for j,t in enumerate(INPUTS):
            for i in calendar:
                slope=(11-j)*0.0004 if t in SECTORS else (0.00015 if t=='BIL' else 0.0006)
                paths[t][i]=100*math.exp(slope*i)
                if t in SECTORS and i>273:
                    paths[t][i]*=math.exp(-(11-j)*0.001*(i-273))
    elif kind!='flat':
        raise ValueError('unknown invented case')
    decisions=[]
    for s in schedule:
        frames=[frame(t,((i,paths[t][i]) for i in calendar if i<=s['anchor']),
                      s['anchor']*100+22) for t in INPUTS]
        decisions.append(decide(frames,s['anchor'],s['cutoff'],calendar))
    return paths,decisions,schedule


def run():
    result=dict(flags=dict(FLAGS),fixture_clocks='invented_ordered_ticks_not_UTC',
                calendar='invented_contiguous_session_labels_not_exchange_calendar',
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases={})
    for kind in ('flat','leadership_then_reversal'):
        paths,decisions,schedule=demo(kind)
        data=dict(schedule=schedule,choices=[dict(anchor=d['anchor'],
                  B3=d['weights']['B3'],B4=d['weights']['B4'],
                  prefix_digest=d['prefix_digest']) for d in decisions],policies=[])
        for c in (0.0005,0.001,0.0025,0.005):
            for p in POLICIES:
                r=policy_path(paths,decisions,schedule,p,c)
                data['policies'].append(dict(policy=p,cost=c,
                     terminal_wealth=r['terminal_wealth'],total_fees=r['total_fees'],
                     traded_notional=r['securities_traded_notional'],
                     max_drawdown=r['max_drawdown'],daily_marks=len(r['daily_wealth'])))
        result['cases'][kind]=data
    return result

if __name__=='__main__':print(json.dumps(run(),indent=2,sort_keys=True,allow_nan=False))
