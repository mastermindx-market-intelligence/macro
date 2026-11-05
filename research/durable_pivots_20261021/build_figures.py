#!/usr/bin/env python3
"""Publication figures from saved study results, with no rule selection."""
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/pivot-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd

ROOT=Path(__file__).parent;OUT=ROOT/'deliverables';FIG=OUT/'figures';FIG.mkdir(parents=True,exist_ok=True)
f=pd.read_csv(ROOT/'results/final_results.csv');f=f[f.pool.eq('primary')].set_index('rule_id')
d=pd.read_csv(ROOT/'results/selected_diagnostics.csv').set_index('rule_id')
s=pd.read_csv(ROOT/'results/outcome_sensitivity.csv')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                     'axes.titleweight':'bold','axes.labelcolor':'#26364a','text.color':'#172c43',
                     'xtick.color':'#526278','ytick.color':'#26364a','figure.facecolor':'#fbfcfe','axes.facecolor':'#fbfcfe'})
navy='#173d63';teal='#147f79';blue='#3a78b5';orange='#c47b27';purple='#8270a8';gray='#7b8794'
ids=['bottom|BASE:price_turn|none','bottom|S1W:curl|M1W:deep|none','bottom|S1W:curl|M1W:deep_rising|none',
     'bottom|S1W:curl|M1W:deep_rising|1D:both_rising','bottom|S2W:curl|M2W:deep_rising|3D:both_rising',
     'bottom|S1W:curl|Mnone|aux:weekly_rsi']
names=['Simple daily price turn','1W Stoch + deep 1W MACD','1W Stoch + improving deep 1W MACD',
       'Above + 1D agreement','2W setup + 3D agreement','1W Stoch + rising 1W RSI below 50']
colors=[gray,teal,blue,orange,purple,navy]
y=np.arange(len(ids))
fig,ax=plt.subplots(1,2,figsize=(12.6,6.3),gridspec_kw={'width_ratios':[1,1.15]})
for j,(rid,c) in enumerate(zip(ids,colors)):
    r=f.loc[rid];v=r.timely_durable_rate
    ax[0].barh(j,v,height=.55,color=c)
    ax[0].errorbar(v,j,xerr=np.array([[v-r.ci_low],[r.ci_high-v]]),fmt='none',ecolor='#293647',capsize=3,lw=1)
    ax[0].text(max(r.ci_high+.012,v+.012),j,f'{v:.1%}',va='center',fontsize=10)
    v=r.qualified_survival63;z=d.loc[rid]
    ax[1].barh(j,v,height=.55,color=c,alpha=.9)
    if r.qualified_n>=40:
        ax[1].errorbar(v,j,xerr=np.array([[v-z.qualified_survival_ci_low],[z.qualified_survival_ci_high-v]]),
                       fmt='none',ecolor='#293647',capsize=3,lw=1)
    ax[1].text(.99,j,f'{v:.1%}  ({int(r.timely_durable_n)}/{int(r.qualified_n)})'+(' *' if r.qualified_n<40 else ''),
               ha='right',va='center',fontsize=10)
for a in ax:
    a.set_yticks(y);a.invert_yaxis();a.xaxis.set_major_formatter(PercentFormatter(1));a.grid(axis='x',alpha=.13);a.set_axisbelow(True)
ax[0].set_yticklabels(names,fontsize=10);ax[1].set_yticklabels([])
ax[0].set_xlim(0,.42);ax[1].set_xlim(0,1.04)
ax[0].set_title('Success across all alerts',loc='left',fontsize=12)
ax[1].set_title('Survival among nearby, deep candidates',loc='left',fontsize=12)
ax[0].set_xlabel('Near the low AND held for 63 sessions')
ax[1].set_xlabel('Held for 63 sessions among qualified candidates\n(age <=21, distance <=2 ATR, depth >=4 ATR)',fontsize=10)
fig.suptitle('Bottom detection: distinguish selectivity, proximity and coverage',fontsize=17,x=.03,ha='left',y=.98)
fig.text(.03,.035,'2020-2026 held-out period; 48 exchange-traded instruments. Error bars: pointwise 95% six-month block bootstrap.\n* Only 6 qualified cases: the 50% estimate is too sparse for a broad claim. A failed proximity test is not necessarily a broken low.',fontsize=9,color='#526278')
fig.subplots_adjust(left=.315,right=.98,top=.84,bottom=.21,wspace=.24)
fig.savefig(FIG/'bottom_detection.png',dpi=200,bbox_inches='tight');plt.close(fig)

ids2=[ids[0],ids[1],ids[2],ids[5]];names2=['Simple price turn','Weekly Stoch + deep MACD','Weekly Stoch + improving deep MACD','Weekly Stoch + RSI recovery']
fig,ax=plt.subplots(figsize=(11.7,5.5))
yy=np.arange(4);v2=[f.loc[i,'timely_durable_rate'] for i in ids2]
v3=[s.loc[(s.rule_id==i)&s.sensitivity.eq('age_distance')&(s.age_max==21)&(s.distance_max==3),'rate'].iloc[0] for i in ids2]
ax.barh(yy-.17,v2,.30,color=teal,label='Within 2 ATR: primary definition')
ax.barh(yy+.17,v3,.30,color=blue,label='Within 3 ATR: predefined sensitivity')
for j in range(4):
    ax.text(v2[j]+.007,j-.17,f'{v2[j]:.1%}',va='center',fontsize=10)
    ax.text(v3[j]+.007,j+.17,f'{v3[j]:.1%}',va='center',fontsize=10)
ax.set_yticks(yy,names2);ax.invert_yaxis();ax.set_xlim(0,.42);ax.xaxis.set_major_formatter(PercentFormatter(1))
ax.set_xlabel('Percentage of alerts meeting the complete near-pivot and 63-session survival objective')
ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
fig.legend(*ax.get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,.075),ncol=2,frameon=False,fontsize=9)
ax.set_title('How much rebound are you willing to accept?',loc='left',fontsize=17,pad=19)
fig.text(.03,.02,'Age remains <=21 sessions and approach depth >=4 ATR. The ranking changes with allowed distance; these sensitivities do not select a new strategy.',fontsize=9,color='#526278')
fig.subplots_adjust(left=.35,right=.98,bottom=.28,top=.85)
fig.savefig(FIG/'proximity_tradeoff.png',dpi=200,bbox_inches='tight');plt.close(fig)

fig,ax=plt.subplots(figsize=(11.7,5.7))
pairs=[('1W','1W'),('1W','2W'),('2W','1W'),('2W','2W')]
for j,(stf,mtf) in enumerate(pairs):
    for mode,dy,c,label in [('deep_rising',-.17,teal,'Deep histogram improving'),('cross',.17,orange,'MACD signal-line crossover')]:
        r=f.loc[f'bottom|S{stf}:curl|M{mtf}:{mode}|none']
        ax.barh(j+dy,r.median_distance_atr,.3,color=c,label=label if j==0 else None)
        ax.text(r.median_distance_atr+.09,j+dy,f'{r.median_distance_atr:.1f} ATR | {r.median_age:g} sessions',va='center',fontsize=10)
ax.axvline(2,color='#b04b51',ls='--',lw=1.4);ax.text(2.07,-.52,'Primary distance limit',color='#b04b51',fontsize=9)
ax.set_yticks(range(4),[f'Stoch {a} / MACD {b}' for a,b in pairs]);ax.invert_yaxis();ax.set_xlim(0,9.7)
ax.set_xlabel('Median distance above the candidate low, measured in ATR at that low')
ax.set_title('Crossovers usually confirm a low after a substantial rebound',loc='left',fontsize=17,pad=20)
ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
fig.legend(*ax.get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,.10),ncol=2,frameon=False,fontsize=9)
fig.text(.03,.02,'Completed bars only. Median age is measured from the lowest low in the preceding 63 daily sessions.\nA high survival rate for an older, distant low answers a different question from entering near that low.',fontsize=9,color='#526278')
fig.subplots_adjust(left=.22,right=.98,top=.85,bottom=.29)
fig.savefig(FIG/'timeframe_timing.png',dpi=200,bbox_inches='tight');plt.close(fig)

pr=pd.read_csv(ROOT/'results/illustrative_prices.csv',parse_dates=['date'])
ev=pd.read_csv(ROOT/'results/illustrative_events.csv',parse_dates=['date','candidate_date'])
fig,axes=plt.subplots(2,2,figsize=(12.5,9.0))
for ax,key,title in zip(axes.ravel(),['SPY_2020','SPY_2022','TLT_2021','NVDA_2021'],
                       ['SPY: March 2020 held, but the alert was 2.39 ATR above its low',
                        'SPY: several failed 2022 rallies before the October low',
                        'TLT: local success did not establish a permanent cycle low',
                        'NVDA: deep weekly conditions also produced failed lows']):
    q=pr[pr.chart.eq(key)];v=ev[ev.chart.eq(key)]
    ax.plot(q.date,q.close,lw=1.4,color=navy,label='Daily close')
    for name,c,mask in [('Timely and held',teal,v.primary63.eq(1)),
                        ('Held, but outside timing/proximity rule',orange,v.survive63.eq(1)&v.primary63.ne(1)),
                        ('Low subsequently breached','#bf4e57',v.survive63.eq(0))]:
        z=v[mask];ax.scatter(z.date,z.signal_close,s=52,color=c,edgecolor='white',linewidth=.65,zorder=4,label=name)
    for r in v.itertuples():
        if r.candidate_date>=q.date.min():
            ax.plot([r.candidate_date,r.date],[r.candidate_price,r.signal_close],color='#8a97a5',lw=.8,ls=':',zorder=2)
    ax.set_title(title,fontsize=10,loc='left',pad=10,wrap=True)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3,maxticks=5));ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.set_ylabel('Split-adjusted chart price (USD)');ax.grid(alpha=.12)
handles,labels=axes[0,0].get_legend_handles_labels()
fig.legend(handles,labels,loc='lower center',ncol=2,frameon=False,fontsize=9,bbox_to_anchor=(.5,.02))
fig.suptitle('The same weekly Stoch curl + deep MACD rule: successes, misses and failures',fontsize=16,x=.04,ha='left',y=.98)
fig.text(.04,.095,'Markers are actual rule alerts, judged over the next 63 sessions. These selected historical windows illustrate the definitions;\nthe complete pooled and subgroup tables determine the conclusions. No example was used to select the rule.',fontsize=9,color='#526278')
fig.subplots_adjust(left=.075,right=.98,top=.89,bottom=.20,hspace=.37,wspace=.23)
fig.savefig(FIG/'historical_examples.png',dpi=200,bbox_inches='tight');plt.close(fig)
print('FIGURES_COMPLETE',len(list(FIG.glob('*.png'))))
