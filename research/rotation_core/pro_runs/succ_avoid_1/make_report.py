"""Compose the complete ordered issue return from frozen result files."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import run_study as study

ROOT=Path(__file__).resolve().parent;R=ROOT/'results'
SHA=(ROOT/'RESULT_COMMIT.txt').read_text().strip()
BASE=f'https://github.com/mastermindx-market-intelligence/macro/blob/{SHA}/research/rotation_core/pro_runs/succ_avoid_1/'
S=pd.read_csv(R/'summary.csv');E=json.loads((R/'effects.json').read_text())
A=pd.read_csv(R/'annual_counts.csv');P=pd.read_csv(R/'continuous_policy.csv')
META=json.loads((R/'run_metadata.json').read_text())
RAW=pd.read_csv(R/'flags_all_observable.csv');BEST=META['best_two_by_frozen_reporting_rank']
NAMES={'OLD':'OLD absolute top','C1':'C1 REL','C2':'C2 BOTH','C3':'C3 WEEK','C4':'C4 TWO_WEEK','C5':'C5 BREADTH','C6':'C6 PARTNER','C7':'C7 VOL_RISE','C8':'C8 MACRO','VOL33':'VOL33 raw state'}
ORDER=study.RULES+['VOL33']+[x for rule in study.RULES for x in ['VOL_'+rule,rule+'_EARLY10',rule+'_LATE10']]

def link(path,label=None):return f'[{label or path}]({BASE+path})'
def pct(v,d=2):return '—' if pd.isna(v) else f'{v*100:.{d}f}'
def num(v,d=1):return '—' if pd.isna(v) else f'{v:.{d}f}'
def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n|'+ '|'.join(['---']*len(headers))+'|\n'+''.join('| '+' | '.join(str(x) for x in row)+' |\n' for row in rows)+'\n'
def rulelabel(x):
    if x in NAMES:return NAMES[x]
    return x.replace('VOL_','VOL matched to ').replace('_EARLY10',' −10 sessions').replace('_LATE10',' +10 sessions')
def descriptive(cohort):
    df=S[S.cohort==cohort].set_index('rule');rows=[]
    for key in ORDER:
        z=df.loc[key];eligible=z.eligible_group_days>0
        terc=[]
        for n in range(1,4):terc.append(f"{pct(z[f't{n}_fake21'],1)} ({int(z[f't{n}_n'])})")
        rows.append([rulelabel(key),int(z.n) if eligible else 'N/A',num(z.flags_per_group_year,2),pct(z.on_share,3),num(z.median_lateness),pct(z.fake21)]+terc+[pct(z.mdd63),pct(z.fake10),pct(z.fake45)])
    return table(['Rule/control','Flags','Flags/group-year','On-share %','Median late','Fake21 %','T1 % (n)','T2 % (n)','T3 % (n)','Mean member DD63 %','Fake10 %¹','Fake45 %¹'],rows)

def interval(cohort,rule,control,metric,scale):
    z=E[cohort][rule][control].get('effects',{}).get(metric)
    if not z:return 'N/A'
    return f"{z['delta']*scale:+.2f} [{z['lo']*scale:+.2f}, {z['hi']*scale:+.2f}]"
def effects(cohort,metric,scale):
    rows=[]
    for rule in study.RULES:
        z=E[cohort][rule]['OLD_MATCHED'];support=z.get('support',0)
        rows.append([NAMES[rule],f'{support*100:.1f}%' if z.get('n') else 'N/A']+[interval(cohort,rule,c,metric,scale) for c in ['OLD_MATCHED','VOL_MATCHED','EARLY10','LATE10']])
    return table(['Rule','Exact-lateness support','vs OLD, exact lateness','vs VOL, same on-share','vs own −10 days','vs own +10 days'],rows)

def annual(cohort):
    rows=[]
    for rule in ORDER:
        d=A[(A.cohort==cohort)&(A.rule==rule)].set_index('year')
        rows.append([rulelabel(rule)]+['—' if d.loc[y,'eligible_group_days']==0 else int(d.loc[y,'flags']) for y in range(2013,2024)])
    return table(['Rule']+[str(y) for y in range(2013,2024)],rows)

def policy(cohort):
    d=P if cohort=='ALL' else P[P.cohort==cohort]
    d=d.groupby('rule')[['flat_share','hold_mdd','policy_mdd','dd_reduction','return_gap']].mean()
    rows=[]
    for rule in ORDER:
        if rule not in d.index:continue
        z=d.loc[rule];rows.append([rulelabel(rule),pct(z.flat_share),pct(z.hold_mdd),pct(z.policy_mdd),pct(z.dd_reduction),pct(z.return_gap)])
    return table(['Rule','Flat days %','Hold MDD %','Exit MDD %','MDD reduction pp','Total-return gap pp'],rows)

INTRO="""I did not find a qualified successor. In the permitted 2013–2023 history, requiring the absolute and relative oscillators to turn down together gave a small reduction in fake breakdowns **at the same measured lateness**, but its raw fake rate was higher than the old rule, it did not beat the matched volatility dates, and it did not demonstrate the required extra drawdown avoidance. The opposite-moving partner was the other finalist under the fixed ranking, but its benefit was not stable and its FF12 damage-capture result was worse than the controls. Weekly/two-week state confirmation, proxy breadth, rising volatility and macro stress supplied no rule that cleared every test. A roll-over can interrupt strong continuing leadership: several supposed tops preceded very large relative gains. These findings apply to the common **2016-01-08 to 2023-09-15 scored panel**, with later starts for XLRE/XLC; 2013 onward supplies in-block warm-up. They are discovery results, not proof that every year in the permitted block was scored or that an exit improves wealth.
"""

RULE_TABLE=[
 ['OLD','Completed 3-day absolute K crosses below D from previous K>80; RSI-MACD histogram falls.'],
 ['C1 REL','The identical top rule applied to group/SPY alone.'],
 ['C2 BOTH','OLD and REL top fire on the same completed 3-day bar.'],
 ['C3 WEEK','OLD; completed weekly K<D, histogram falling, previous K≥50, weekly close ≥90% of its 26-week high.'],
 ['C4 TWO_WEEK','OLD; completed 2-week K<D, histogram falling, previous K≥50, close ≥90% of its 13-bar high.'],
 ['C5 BREADTH','FF12 only: OLD and ≥40% of proxy children fired OLD in the last 9 sessions, or ≥60% are below their 50-session average.'],
 ['C6 PARTNER','OLD; minimum prior-126-session relative-return correlation ≤−0.25; that same-cohort partner fired a relative bottom in the last 6 sessions.'],
 ['C7 VOL_RISE','OLD; RV21 ≥1.25× its value 21 sessions earlier; that earlier value ≤40th percentile of the preceding 252 RV21 readings; lagged VIX≥20 or five-session rise≥2.'],
 ['C8 MACRO','OLD and ≥2 of: curve<0; 10Y 63-session rise≥0.50pp; broad dollar 63-session rise≥2%; HY OAS 21-session rise≥0.25pp. All four inputs available.'],
 ['VOL33','RV63 at/above own discovery-block 2/3 quantile. Raw state plus exact per-group count-matched versions.'],
 ['−10 / +10','The original rule/candidate flags moved exactly ten SPY sessions earlier/later. Placebos, not executable forecasting rules.']]

parts=[]
parts.append('## 1. Plain answer\n\n'+INTRO+'\n## 2. Every candidate and both comparator families\n\n'+
f"Run **SUCC-AVOID-1**; ledger **successor-avoid-1**. Eight rules were fixed in [the immutable protocol](https://github.com/mastermindx-market-intelligence/macro/blob/2a1924f0092a4bb0f4a3f4d85d129b9eaf2c3c6e/research/rotation_core/pro_runs/succ_avoid_1/PROTOCOL.md) before outcome inspection. Code and derived evidence: {link('README.md','reproduction package')}.\n\n"+
table(['Rule','Definition fixed before the test'],RULE_TABLE)+
"### How to read the tables\n\nAll rates and drawdowns are percentages unless labelled otherwise. **On-share is flagged group-days / eligible group-days**, with each flag lasting one event day. Flags/group-year uses eligible group-days/252; actual annual counts follow. Lateness uses the most recent maximum in the **prior 63 sessions, excluding the flag day**. OLD's pooled lateness terciles are **T1=1–6, T2=7–48, T3=49–63 sessions**; boundary ties stay together. Each tercile cell gives fake21 rate and number of flags. N=10 and 45 are sensitivities only (¹), never selection targets. DD63 is average member peak-to-trough drawdown over close t and the next 63 closes.\n\n"
"A fake is a strict new rolling relative high over the preceding 63 sessions on any of the next 21 sessions. This can occur when an older peak rolls out; it is not a requirement to regain a fixed flag-date peak. Group/SPY uses total-return indices.\n\n"
"The raw VOL33 state flags about 41% of the **scored** panel because its cutoff is set on the longer permitted discovery distribution, including low-volatility warm-up dates. Each `VOL matched to X` is sampled from that state using a frozen date hash, matching X's total count separately within every group. No outcome enters this sampling. Thus the top-third predicate is retained and the actual event on-share matches; the raw state is shown without falsely claiming it has the same share.\n\n"
"### FF12 — primary reporting/ranking cohort\n\nFF12 member statistics use a fixed **economic FF49 proxy mapping**, not literal nested French constituents. FF49 and FF12 are not nested partitions. Child counts and the full map appear with the reproduction rules.\n\n"+descriptive('FF12')+
f"Underlying exact values: {link('results/summary.csv')} and {link('results/coverage.csv')}.\n")

parts.append('## 2. Tables continued — ETF, FF49 and descriptive pooled results\n\n'
"ETF DD refers to the ETF itself. FF49 DD refers to each FF49 portfolio itself, not its underlying stocks. The pooled table repeats overlapping economic exposures and is **not independent corroboration**. C5 is N/A outside FF12; its pooled row still uses only the FF12 denominator. All other definitions and tercile boundaries are unchanged.\n\n"
'### Sector ETFs\n\n'+descriptive('ETF')+'### FF49 industries\n\n'+descriptive('FF49')+'### All eligible group series, descriptive only\n\n'+descriptive('ALL'))

text3='## 2. Tables continued — matched comparisons and the 50 bp gate\n\n'
text3+="Cells are **candidate minus comparator**, with a calendar-month bootstrap 90% interval. For fake rates, negative is better. For event drawdown captured/avoided, positive is better. The OLD comparison matches exact `(group, integer lateness)` cells, then uses candidate counts as weights. It is not just a tercile adjustment. Different candidates therefore target different OLD mixtures; the unconditional OLD row is not the adjusted counterfactual.\n\n"
text3+="The volatility comparison is matched on per-group event on-share. Shifts preserve each original event and group; both members of a pair are resampled using the original flag's month. We used 2,000 month draws, seed 1101401, with the entire cross-section resampled jointly. The same month multiplicities apply to all rules/controls. Exact-cell means and supported cells are recomputed within each draw. Undefined draws are omitted and counted in the machine-readable effects.\n\n"
valid=[v['valid_bootstrap'] for cohort in E.values() for rule in cohort.values() for control in rule.values() for v in control.get('effects',{}).values()]
text3+=f"Usable bootstrap draws range from **{min(valid)} to {max(valid)}** across the displayed estimates; sparse two-week rows account for missing draws. Intervals are not adjusted for choosing among eight candidates and may be too narrow when 63-session windows overlap across months.\n\n"
for c in ['FF12','ETF','FF49','ALL']:
    text3+=f'### {c}: fake21 differences, percentage points\n\n'+effects(c,'fake21',100)
text3+="### What the drawdown contrast actually means\n\nFor each flag, the counterfactual holds a unit exposure through the **next session's close**, then stays flat at zero return through t+63: 62 post-exit return intervals. It assumes no same-close fill. `Event avoidance = hold-through-63 MDD − delayed-exit MDD`, averaged across members. The following table compares this amount across rule/control events. A benefit must have a 90% lower bound **strictly greater than +50 bp**, alongside better fake21 discrimination against matched OLD, matched VOL and both shifts.\n\n"
text3+="This event quantity is structurally nonnegative before taking the comparator difference: the exit path is a prefix of the held path. It can credit avoidance of a fall from a much higher future peak while the exit gives up the intervening gain. Accordingly it measures **event-level damage capture**, not validated portfolio improvement. Continuous-path and missed-return diagnostics follow.\n\n"
for c in ['FF12','ETF','FF49','ALL']:
    text3+=f'### {c}: incremental event drawdown avoidance, basis points\n\n'+effects(c,'avoid63',10000)
text3+="### Adjudication\n\n**No candidate passes all the gates.** C2 and C6 are the two finalists under the pre-fixed FF12 rank: at least 30 flags in at least four FF12 groups, then smallest matched-lateness fake21 difference, then larger VOL-relative avoidance, then ID. C4 (6 FF12 flags) and C7 (18) fail that ranking floor; they remain fully reported, not dropped.\n\n"
text3+=table(['Candidate','Reading'],[
 ['C1','Relative roll-over alone has more pooled fakes; no replacement.'],
 ['C2','**Fewer fake breakdowns, nothing avoided** applies to its small matched-lateness FF12 result, not its raw rate. Raw FF12 fakes rise from 32.97% to 34.96%; median lateness falls from 24 to 5. The adjusted −3.94pp interval barely excludes zero. Incremental avoidance versus matched OLD is +15.0bp [−19.2,+44.1], below the required 50bp even at the upper endpoint.'],
 ['C3','Higher weekly bearish state does not produce a stable fake-rate improvement.'],
 ['C4','**Fewer fake breakdowns, later** describes the pooled comparison (28.57% vs 37.56%; median 29 vs 20 sessions). The matched result is uncertain, and only six FF12 flags exist. No qualified win.'],
 ['C5','Proxy breadth leaves the matched FF12 fake rate essentially unchanged (+0.18pp).'],
 ['C6','Some lower pooled fake rates outside FF12; no stable matched OLD improvement. FF12 avoidance is worse than OLD (−61.5bp [−88.2,−4.0]) and matched VOL (−263.2bp [−440.2,−102.7]).'],
 ['C7','It selects larger subsequent drawdowns, but fake breakdowns are more frequent; this is not the requested solution.'],
 ['C8','The macro filter supplies no stable matched improvement or joint win.']])
text3+=f"Exact estimates, all six outcomes and valid-draw counts are in {link('results/effects.json')}. Full matching support does not mean independent comparisons: C2 has an additional OLD event in only 94/123 FF12 cells' flag observations, 65/95 ETF and 444/598 FF49; the remainder compare a flag largely or entirely with itself. C6's corresponding counts are 42/66, 37/59 and 251/365. See {link('results/matching_information.csv')}.\n"
parts.append(text3)

text4='## 2. Tables continued — actual annual flag counts\n\n'
text4+="`—` means no eligible observations, not zero signal frequency. Counts for shifted controls are assigned to the original flag's calendar year so numerator and eligible-source denominator remain aligned. Matched VOL dates retain their own years; total counts match per group over the scored block, not within each year. Rates with annual eligible group-day denominators are also supplied in the CSV.\n\n"
for c in ['FF12','ETF','FF49','ALL']:text4+=f'### {c}\n\n'+annual(c)
text4+=f"Source: {link('results/annual_counts.csv')}. The nine original sector ETFs, all FF12 and all FF49 series begin common scoring on 2016-01-08. XLRE starts on 2018-10-12; XLC starts on 2021-06-18. All stop on 2023-09-15. There are 137,118 eligible group-days. The input calendar has 2,768 sessions.\n"
parts.append(text4)

text5='## 2. Tables continued — continuous exit diagnostics\n\n'
text5+="These are **averages of per-group full-path statistics**, not an investable portfolio and not annualized returns. Every scored warning holds through next close, then removes return exposure on t+2..t+63. A later warning extends the flat window. Each group's diagnostic runs over its common eligible interval. Cash return and transaction costs are zero. The FF12 continuous path uses the actual FF12 group index; the event member-DD tables above use its proxy children.\n\n"
text5+="Event-count matching does not match time outside the group. For example, FF12 C2 is flat 29.35% of the time versus 22.50% for its matched VOL dates. Its mean full-path MDD reduction is 8.73pp versus 1.02pp, but its total-return gap versus holding is −23.40pp. The +10-session version reduces MDD by 9.54pp at a similar 29.18% flat share. These facts do not establish superior timing under the frozen gate. FF12 C6 reduces MDD by −0.09pp—effectively none—while giving up 36.77pp of total return.\n\n"
for c in ['FF12','ETF','FF49']:text5+=f'### {c}\n\n'+policy(c)
text5+=f"No confidence-qualified portfolio claim is made from this diagnostic. Underlying per-group numbers: {link('results/continuous_policy.csv')}. The event return-gap contrasts, including bootstrap intervals, are retained in {link('results/effects.json')}.\n"
parts.append(text5)

PSEUDO=r'''## 3. Exact reproduction of the two finalists

The two finalists are **C2 BOTH** and **C6 PARTNER**, selected for detailed reporting, not accepted successors. The complete implementation is linked below; the following fixes their economic inputs, arithmetic, clocks and tie-breaks.

### Common arithmetic and clocks

```text
Allowed observation dates = 2013-01-02 through 2023-12-29, inclusive.
Calendar = actual SPY trading sessions in that interval, ordered ascending.
Group price P = compounded daily FF value-weighted total returns,
                or Yahoo adjusted close for the ETF where it exists.
Benchmark = SPY adjusted close. Relative price R = P / SPY.
Never fill a group price backward or invent ETF prehistory.

3-day bars = calendar indices [0,1,2], [3,4,5], ...
Only the last session of a complete block supplies a bar close.
No yearly reset. A flag is known at that session's close.

RSI14(X):
  changes = consecutive completed-bar price changes
  gain = max(change,0); loss = max(-change,0)
  first gain/loss averages = arithmetic means of first 14 changes
  later averages = (13*prior_average + current_value)/14
  RSI = 100 - 100/(1+average_gain/average_loss)
  zero loss and positive gain ->100
  zero gain and positive loss ->0; both zero ->50

EMA_n(x):
  seed = arithmetic mean of first n consecutive finite observations
  thereafter EMA += 2/(n+1) * (x-EMA)
  missing input resets initialization; no implicit zero

MACD = EMA14(RSI14) - EMA60(RSI14)
Signal = EMA5(MACD)
H = MACD - Signal

StochRaw = 100*(RSI14 - min(last14 RSI14))
                 /(max(last14 RSI14)-min(last14 RSI14))
zero range ->missing
K = arithmetic SMA3(StochRaw)
D = arithmetic SMA3(K)

TOP(X):
  previous K >80
  AND previous K >= previous D
  AND current K < current D
  AND current H < previous H

BOTTOM(X):
  previous K <20
  AND previous K <= previous D
  AND current K > current D
  AND current H > previous H

No refractory period, hysteresis, veto or tuning after a flag.
Each qualifying completed bar creates one event-day warning.
```

### C2 BOTH

```text
For every group g, on every completed 3-day bar ending session t:
  absolute_top = TOP(P[g])
  relative_top = TOP(R[g])
  C2[g,t] = absolute_top AND relative_top

Both crosses must occur on this exact bar.
No earlier cross is carried into the rule.
Equal K and D on the current bar is NOT a below-cross.
The flag does not authorize blocking or sizing a trade.
```

### C6 PARTNER

```text
Peer universe = other groups in the same cohort:
  FF12 peers for FF12; FF49 peers for FF49; listed ETF peers for ETFs.
Do not mix these overlapping classifications into one peer pool.

At close t:
  for each peer h with 126 complete paired daily relative log returns:
    corr[h] = Pearson correlation(
      log(R[g,s]/R[g,s-1]), log(R[h,s]/R[h,s-1]),
      s = t-126,...,t-1)
  Exclude g itself and any peer lacking the paired history.
  h* = peer with smallest corr
  Ties within 1e-12 -> lexicographically smallest group code.

  Require h*'s completed 3-day K, prior K, D, prior D, H and prior H
  to be finite over each of the last six sessions' available bar states.
  Preserve an explicit NaN on a completed source bar; it is not the
  previous finite reading. No initialized selected peer ->ineligible.

  partner_up = any BOTTOM(R[h*]) flag on sessions t-5,...,t inclusive
  C6[g,t] = TOP(P[g]) AND corr[h*] <= -0.25 AND partner_up

No recomputation with t's return in the correlation window.
No alternative peer is chosen because the minimum peer has no up-turn.
```

### Scoring mask, not an additional production rule

For the common comparison, every required feature for all eight non-breadth specifications must be ready: absolute/relative 3-day indicators; completed weekly and two-week states; 26-week/13-biweek close highs; the volatility lookbacks; the selected peer's history; and all lagged macro values. This is why the scored history begins in 2016. The raw signal tape retains earlier/later observable C2/C6 flags, marked unscored, rather than pretending the common mask is part of the signal's economic claim.

Weekly bars close on the final trading session of each calendar week. Two-week bars use pairs anchored to the calendar week beginning 2012-12-31; the first observed prices are in January 2013, and no prior price/return is used. An unfinished trailing higher bar is excluded. Completed higher states are carried between bar closes, preserving explicit missing source readings. Each group needs 73 subsequent sessions for scoring, ensuring the +10 shift still has a full 63-session outcome. OLD-relative-high and −10 outcomes also need complete prior windows.

VIX, Treasury and HY states use one prior-session lag, forward-filled at most five sessions. Dollar uses five prior sessions, also with at most five-session fill. Before 2020, its 63-session change is measured inside DTWEXB; from 2020, inside DTWEXBGS. No percentage change crosses the different index levels. These are conservative release-lag assumptions, not a complete vintage database.

### Labels, controls and uncertainty

```text
fake_N(g,t) = exists u in [t+1,t+N] such that
              R[g,u] > max(R[g,u-63],...,R[g,u-1])
Primary N=21; only sensitivities N=10,45.

prior_high_date = latest argmax of R[g,t-63],...,R[g,t-1]
lateness = t-prior_high_date

RV63 = sample SD(ddof=1) of last63 daily log absolute returns *sqrt(252)
VOL33[g,t] = RV63[g,t] >= linear 2/3 quantile of that group's
             finite discovery-block RV63 values

For target rule Q and each group g:
  k = number of eligible Q flags in g
  order eligible VOL33 dates by ascending hex SHA256 of exact UTF-8:
    "SUCC-AVOID-1|VOL|" + group_code + "|" + ISO_date
  choose first k dates; print them in calendar order
  if fewer than k are available, comparison is infeasible (none here)

Shifts = (g,t-10), (g,t+10) for each original (g,t).
Exact matched OLD cells = (group_code, integer_lateness).
Weights = candidate flag counts within cells containing both rules.
No extrapolation for REL-only cells lacking OLD support.

Bootstrap = 2,000 calendar-month multinomial resamples,
NumPy default_rng(seed=1101401), same draw across every group/rule.
Point interval = empirical 5th and 95th percentiles of finite draws.
Shift pairs keep their original-event month.
```

FF group codes in hashing include `FF12_` or `FF49_`; ETF group codes are the tickers. This matters for reproducing the exact matched VOL sample. There is no minimum-count tie chosen by a favorable outcome. The two final reporting candidates were ranked only under the pre-fixed FF12 count/group floor and matched-lateness fake difference described above.

### The FF12 proxy map

This is an explicit economic approximation. French's static SIC definitions show that FF49 portfolios cross FF12 boundaries; a true FF12-child reconstruction cannot be derived from aggregate FF49 returns alone. No constituent weights are inferred from the number of SIC codes. Average member DD means the mean of individual proxy-child maximum drawdowns; it is not the maximum drawdown of their combined basket.
'''
maprows=[[k,len(v.split()),v] for k,v in study.CHILDREN.items()]
text6=PSEUDO+'\n'+table(['FF12 group','Proxy child count','FF49 proxy codes'],maprows)
text6+=f"Reproduce from {link('run_study.py')}, {link('acquire.py')}, and {link('verify_study.py')}. Runtime: Python 3.12.14, NumPy 2.3.5, pandas 2.2.3. The current-vintage inputs are identified by {link('results/input_manifest.json')}; exact replay requires matching those hashes. No raw vendor or FRED series is published in the branch.\n"
parts.append(text6)

datesintro='## 3. Flag dates and groups — complete OLD and finalist tapes\n\n'
datesintro+=f"All **5,084 observable flags** for OLD (3,474), C2 (1,029) and C6 (581) are printed below. **4,011** are in the common scored panel (2,705 / 816 / 490). A trailing `*` marks an unscored flag: warm-up/feature availability or insufficient forward support. Years and MM-DD tokens together give full dates. The CSV gives the precise unscored reason. These dates are signals, not trade instructions.\n\nFull all-candidate tape: {link('results/flags_all_observable.csv')}. Scored OLD/C2/C6 events with labels and outcomes: {link('results/old_and_finalist_flags.csv')}.\n\n"
dateblocks=[]
for rule in ['OLD']+BEST:
    z=RAW[RAW.rule==rule].copy();z['year']=z.date.str[:4];z['md']=z.date.str[5:]
    lines=[]
    for group,df in z.groupby('group',sort=True):
        years=[]
        for year,dd in df.sort_values('date').groupby('year',sort=True):
            tokens=[x.md+('' if x.scored else '*') for x in dd.itertuples()]
            years.append(year+': '+','.join(tokens))
        lines.append(group+' | '+'; '.join(years))
    dateblocks.append('### '+NAMES[rule]+'\n\n```text\n'+'\n'.join(lines)+'\n```\n\n')
datebody=datesintro+''.join(dateblocks)
if len(datebody)<55000:parts.append(datebody)
else:
    parts.append(datesintro+dateblocks[0])
    parts.append('## 3. Flag dates continued — finalists\n\nThe same year/MM-DD notation and `*` unscored marker apply.\n\n'+''.join(dateblocks[1:]))

worst=pd.read_csv(R/'worst_fakes.csv');miss=pd.read_csv(R/'largest_missed.csv')
textlast='## 4. What the best-ranked candidate still gets wrong\n\n'
textlast+="### Ten worst C2 fake breakdowns\n\nRanked by maximum group/SPY relative-index appreciation over the following 21 sessions, then larger absolute appreciation, group code and date. A fake label is retained even if a later 63-session drawdown exists. These are scored warnings; five rows are Coal, so they are not ten independent mechanisms.\n\n"
wrows=[]
for x in worst.itertuples():
    wrows.append([x.date,x.group,int(x.lateness),int(x.first_high21),pct(x.relative_gain21),pct(x.mdd63),pct(x.avoid63),pct(x.return_gap)])
textlast+=table(['Flag date','Group','Lateness','First new high, sessions','Max relative gain21 %','Member DD63 %','Event DD capture pp','Exit−hold return63 pp'],wrows)
textlast+="Coal on **2016-02-10** is the sharpest illustration: the relative index subsequently gained **45.30%**, and the event calculation still credits **12.81pp** of avoided peak-to-trough drawdown. The same hypothetical exit gave up **92.07pp** of 63-session return. Avoiding a later dip from a much higher peak does not establish a good top call.\n\n"
textlast+="### Ten largest real-top episodes without a fresh timely C2 warning\n\nThe independent audit starts from every observable strict 63-session relative high in the permitted dates with 63 future sessions, requires an absolute decline of at least 10% from that high to the next-63-session trough, keeps the latest high for a shared trough, then removes overlapping same-group episodes in descending severity order. It does not start from OLD's rejected warnings. A fresh timely catch is a C2 flag from the high through `min(high+21, trough−1)`; raw observable C2 flags count even outside the common scored panel.\n\n"
mrows=[]
for x in miss.itertuples():
    mrows.append([x.high_date,x.group,x.trough_date,pct(x.decline),pct(x.member_mdd63),'yes' if x.exit_already_active_at_high else 'no','yes' if x.exit_active_at_trough else 'no','yes' if x.peak_in_scored_panel else '**no — warm-up**'])
textlast+=table(['Relative-high date','Group','Trough date','High→trough decline %','Member DD63 %','Earlier exit active at high?','Exit active at trough?','Peak in scored panel?'],mrows)
textlast+="**These are fresh-warning misses, not ten unprotected crashes.** Nine already had a prior exit active at the high; only the first two remained flat at the trough. Earlier warnings can be labelled fake because another relative high follows, yet still protect part of a subsequent fall; protection can also expire before the trough. Autos and Durbl overlap economically in the same episodes. Gold on 2014-08-12 is in the permitted audit block but outside the common scored panel and is explicitly tagged. There are 502 independent-by-this-deduplication top episodes and 369 fresh-warning misses, not 502 independent market regimes.\n\n"
textlast+=f"Full failure records: {link('results/worst_fakes.csv')}, {link('results/largest_missed.csv')}, {link('results/real_top_episodes.csv')}.\n\n"
textlast+='## 5. What to test next, and how this could be fooling us\n\n'
textlast+="**First, fix the economic target before adding more filters.** Separate a harmless relative new high from material continued leadership, and distinguish avoiding a decline below an executable exit price from avoiding a later decline after a large missed gain. Those would be new outcomes, not retroactive changes to this run's fixed fake label. Retain the original label alongside them so a prettier answer cannot replace the practitioner's complaint.\n\n"
textlast+="**Then test a small, separately frozen successor set with comparable exit exposure.** C2's simultaneous absolute/relative turn is a weak research clue, not an accepted rule. Any new combination or threshold needs a new run ID and must count as a new test. Match flat-day exposure as well as event on-share, specify re-entry, costs and cash return, and check net outcomes. Do not simply lengthen the warning until every drawdown is captured.\n\n"
textlast+="**Obtain exact membership and release vintages, then seek genuinely untouched evidence under a new commission.** The proxy map cannot establish exact constituent breadth. Current French, ETF and dollar histories can differ from those available at the time. Longer calendar blocks, such as 3–6 months, would challenge the required month-bootstrap intervals. The same already-examined discovery period cannot become a fresh confirmation sample by renaming it; no additional historical block or post-2023 outcomes were tested here.\n\n"
textlast+="The main way this could fool us is **measuring damage concentration and calling it economic protection**. Rare filters can pick different dates/groups or spend more time flat; a later peak-to-trough drop can look 'avoided' while the exit misses a much larger rise. Exact lateness and on-share matching remove some easy advantages, but not selection among eight rules, repeated sector exposure, changing classification, data revisions or multi-month dependence. The small C2 FF12 interval barely excluding zero is particularly fragile: ETF and FF49 matched intervals include zero, and the pooled series are not independent replications.\n\n"
textlast+="### Complete test and repair ledger\n\n"
textlast+=table(['Item','Count / disposition'],[
 ['Candidate hypotheses','8 fixed before outcomes; 0 discarded or replaced; 0 threshold sweeps; 0 post-result signal changes.'],
 ['Signal/control tapes','37: OLD + 8 candidates, 1 raw VOL33, 9 per-target matched VOL tapes, 18 ±10 shifted tapes.'],
 ['Descriptive cells','4 cohort views ×37 tapes =148 rows; 8 rows N/A because C5 and its controls do not apply to ETF/FF49; 140 nonempty cells.'],
 ['Horizons','N=21 primary; N=10 and45 sensitivities. All three printed, none silently selected.'],
 ['Contrast estimates','136 nonempty rule/cohort/control contrasts ×6 metrics =816 reported estimates, including OLD self-comparisons; these are dependent outputs, not 816 independent ideas.'],
 ['Metrics','fake10, fake21, fake45, member DD63, next-close event avoidance, and exit-minus-hold return63.'],
 ['Estimation repetitions','2,000 joint calendar-month bootstrap draws, one seed; undefined sparse draws disclosed.'],
 ['Candidate result executions','1 complete outcome run. No dropped failed economic run.'],
 ['Ranking exclusions','C4 and C7 below the FF12 reporting floor; their outcomes remain in every applicable table.'],
 ['Implementation repairs before first run','Preserved explicit source-bar NaNs; initialized the selected partner; restored all-observable missed-top/catch universes; restricted C5 applicability; fixed shift annual attribution.'],
 ['Post-outcome reporting changes','Renamed the days22–63 warning field accurately; removed a misleading count/11 frequency column; added matching-information and trough-coverage diagnostics. No candidate statistic or selection changed.'],
 ['Verification','Synthetic RSI/EMA/bar/NaN tests; exact per-group control counts and shift support; scalar reconstruction of 12 fixed-spaced events; zero OLD-vs-OLD effects; full/prefix signal invariance through 2019-12-18.'],
 ['Extra descriptive audits','Matching-information counts and exit-active-at-trough flags, added after results to prevent overclaiming. No new candidate or threshold.'],
 ['Other history / deployment','No out-of-block market observation in calculations; no earlier warm-up; no untouched-period claim; no deployment or trade sizing.']])
textlast+=f"Verification and exact runtime/source hashes: {link('results/verification.json')}. Metadata: {link('results/run_metadata.json')}.\n\n"
textlast+="### Source and data qualifications\n\n"
textlast+="- [French 12-industry construction](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_12_ind_port.html) and [49-industry construction](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_49_ind_port.html); daily value-weighted return files, not ex-dividend files. [French's data library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) states that histories are reconstructed and can change.\n"
textlast+="- Static [SIC12 definitions](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Siccodes12.zip) and [SIC49 definitions](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Siccodes49.zip) establish the non-nesting limitation. For example, LabEq spans the FF12 BusEq/Manuf boundary.\n"
textlast+="- Public Yahoo chart data for SPY and the specified sector tickers, restricted by observation date. Adjusted closes account for splits and distributions. No pre-existence history for XLRE/XLC was filled.\n"
textlast+="- FRED DGS2, DGS10, DTWEXB, DTWEXBGS, BAMLH0A0HYM2, VIXCLS. [The Federal Reserve's 2019 H.10 change](https://www.federalreserve.gov/releases/h10/h10_technical_qa.htm) explains why the older goods-only and newer goods/services dollar series are treated separately. [Cboe VIX history](https://www.cboe.com/tradable-products/vix/vix-historical-data) is the underlying VIX series provenance.\n"
textlast+=f"- The official high-yield endpoint returned only the allowed block's late tail. A public, commit-pinned FRED-origin archive supplied the missing history; 2,760 values match a public archive saved in 2023 exactly, and 33 match the available official FRED overlap exactly. This does not independently validate the intervening archive-only tail or prove point-in-time release vintages. See {link('results/hy_archive_verification.json','the exact archive sources and cross-checks')}.\n"
textlast+=f"- All 20 retained input files have observation bounds and SHA-256 hashes in {link('results/input_manifest.json')}. Retrieval/vintage dates are separate from observation dates: this is a current-vintage retrospective calculation with a strict permitted observation block, not an assertion that the downloaded files themselves were published before 2024. Bulk French dates were filtered before numeric conversion.\n\n"
textlast+="**Research ruling for ledger successor-avoid-1:** completed discovery self-test; **no accepted avoid-side successor**. Keep the distinction between a warning, a missed fresh warning, event drawdown capture and a verified economic improvement. This return supplies research evidence and grants no live blocking, sizing or execution authority.\n"
parts.append(textlast)

out=ROOT/'report_parts';out.mkdir(exist_ok=True)
total=len(parts)
allparts=[]
for i,body in enumerate(parts,1):
    header=f'PRO-RUN SUCC-AVOID-1 part {i}\n\n'
    if i==1:header+=f'**Total parts: {total}.** Run `SUCC-AVOID-1`; ledger row `successor-avoid-1`.\n\n'
    full=header+body
    assert len(full)<60000,(i,len(full))
    (out/f'part_{i:02d}.md').write_text(full)
    allparts.append(full)
(ROOT/'REPORT.md').write_text('\n\n---\n\n'.join(allparts))
(out/'manifest.json').write_text(json.dumps({'parts':total,'results_commit':SHA,'characters':[len(x) for x in allparts]},indent=2))
print(json.dumps({'parts':total,'characters':[len(x) for x in allparts],'total_characters':sum(map(len,allparts))}))
