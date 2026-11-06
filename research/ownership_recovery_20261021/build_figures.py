"""Publication figures from the saved derived results; no new empirical rules."""
from pathlib import Path
import os, tempfile
os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'ownership-recovery-matplotlib'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import PercentFormatter

R=Path(__file__).resolve().parent;O=R/'figures';O.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
 'axes.spines.right':False,'axes.titleweight':'bold','axes.labelcolor':'#334155',
 'text.color':'#173d63','axes.edgecolor':'#cbd5e1','grid.color':'#e2e8f0','svg.fonttype':'none',
 'figure.facecolor':'white','axes.facecolor':'white'})
NAVY='#173d63';TEAL='#15847b';ORANGE='#c97826';GRAY='#7f8fa3';PURPLE='#8c62a8'

def save(fig,name,note):
    fig.text(.055,.025,note,fontsize=8.3,color='#56657a',va='bottom')
    fig.savefig(O/(name+'.svg'),bbox_inches='tight')
    svg=O/(name+'.svg')
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    fig.savefig(O/(name+'.png'),dpi=180,bbox_inches='tight')
    plt.close(fig)

c=pd.read_csv(R/'results/defensive_common_support.csv').set_index('panel').loc[['CORE5','PEERS13']]
fig,ax=plt.subplots(1,2,figsize=(12,5.4),gridspec_kw={'width_ratios':[1.15,1]})
fig.subplots_adjust(top=.80,bottom=.20,wspace=.38)
fig.suptitle('Selected businesses provide a strong base rate',x=.055,y=.97,ha='left',fontsize=19,fontweight='bold')
fig.text(.055,.89,'Joint weekly + two-week washout context, daily RSI-MACD repair; 126-session outcomes',fontsize=11)
x=np.arange(2);width=.32
for delta,col,label,color in [(-width/2,'positive','Signal entries',TEAL),(width/2,'ordinary_positive','Matched ordinary dates',GRAY)]:
    bars=ax[0].bar(x+delta,c[col]*100,width,label=label,color=color)
    ax[0].bar_label(bars,labels=[f'{v:.1f}%' for v in c[col]*100],padding=5,fontsize=10)
ax[0].set_xticks(x,['Core five\n73 matched signals','Thirteen peers\n213 matched signals'])
ax[0].set_ylim(0,105);ax[0].set_ylabel('Positive outcomes (%)');ax[0].grid(axis='y',alpha=.5);ax[0].set_axisbelow(True)
ax[0].legend(loc='lower left',frameon=False);ax[0].set_title('Absolute recovery frequency',loc='left',pad=14)
v=c.ordinary_net_delta.to_numpy()*100;lo=c.ordinary_net_delta_lo.to_numpy()*100;hi=c.ordinary_net_delta_hi.to_numpy()*100
ax[1].errorbar(v,[1,0],xerr=[v-lo,hi-v],fmt='o',capsize=6,color=TEAL,markersize=8,lw=2)
ax[1].axvline(0,color=GRAY,lw=1);ax[1].set_yticks([1,0],['Core five','Thirteen peers']);ax[1].set_ylim(-.5,1.5)
ax[1].set_xlim(-.25,3);ax[1].set_xlabel('Mean signal increment (percentage points)')
for i,(p,l,h) in enumerate(zip(v,lo,hi)):ax[1].text(p,1-i+.18,f'+{p:.2f} pp [{l:+.2f}, {h:+.2f}]',ha='center',fontsize=9)
ax[1].grid(axis='x',alpha=.5);ax[1].set_title('Increment over ordinary entries',loc='left',pad=14)
save(fig,'selection_timing','Same asset, half-year and own/market trend state; focal date excluded. Within-cohort matched coverage.\nPointwise calendar-block intervals; exposed history and retrospectively selected surviving names. Source: defensive_common_support.csv.')

paths=pd.read_csv(R/'results/portfolio_paths.csv',parse_dates=['date'])
styles={'OWN':('Continuous ownership',NAVY),'ALL_CROSSES':('Every daily cross',GRAY),'JOINT':('Joint-context entries',TEAL),'JOINT_STOP':('Joint entries + 3-ATR stop',ORANGE)}
fig,ax=plt.subplots(3,1,figsize=(12,8),sharex=True,gridspec_kw={'height_ratios':[2,1,1]})
fig.subplots_adjust(top=.84,bottom=.13,hspace=.18)
fig.suptitle('A high trade hit rate can coexist with a substantial drawdown',x=.07,y=.97,ha='left',fontsize=18,fontweight='bold')
fig.text(.07,.91,'Core five | Equal initial stock sleeves | 2018 to 8 October 2026 | Zero return on cash',fontsize=11)
for pol,(label,color) in styles.items():
    q=paths[(paths.population=='CORE5')&(paths.policy==pol)].sort_values('date')
    dd=q.nav/np.maximum.accumulate(np.r_[1.,q.nav])[1:]-1
    ax[0].plot(q.date,q.nav,color=color,label=label,lw=1.8)
    ax[1].plot(q.date,dd*100,color=color,lw=1.2,alpha=.9)
    if pol in ['JOINT','JOINT_STOP']:
        exposure=q.held/(q.nav+.0005*q.held)
        ax[2].plot(q.date,exposure*100,color=color,lw=1.1,label=label)
ax[0].legend(frameon=False,ncol=2,loc='upper left');ax[0].set_ylabel('Value of initial 1')
ax[1].set_ylabel('Drawdown (%)');ax[2].set_ylabel('Invested (%)');ax[2].set_ylim(-2,105)
for z in ax:z.grid(axis='y',alpha=.6)
ax[2].xaxis.set_major_locator(mdates.YearLocator(2));ax[2].xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
save(fig,'defensive_capital','Adjusted-price return proxy, next-open entries, 126-session endpoint, costs and marked open positions included.\nStops keep the same accepted roster and reserve capital through the original endpoint. Source: portfolio_paths.csv.')

fig,ax=plt.subplots(2,2,figsize=(12.5,8))
fig.subplots_adjust(top=.82,bottom=.14,wspace=.30,hspace=.40)
fig.suptitle('Sector recovery is largely a shared calendar opportunity',x=.065,y=.97,ha='left',fontsize=19,fontweight='bold')
fig.text(.065,.91,'Same accepted dates and capital contract | 2020 to 8 October 2026 | 12 nominating sleeves',fontsize=11)
pols={'RSI_SELECTED':('Selected sector',TEAL),'RSI_ALL_SECTORS':('All-sector basket',GRAY),'RSI_SPY':('SPY',PURPLE),'RSI_STOP':('Selected + stop',ORANGE)}
for pol,(label,color) in pols.items():
    q=paths[(paths.population=='SECTORS12')&(paths.policy==pol)].sort_values('date')
    ax[0,0].plot(q.date,q.nav,label=label,color=color,lw=1.7)
    if pol in ['RSI_SELECTED','RSI_STOP']:
        dd=q.nav/np.maximum.accumulate(np.r_[1.,q.nav])[1:]-1
        ax[1,0].plot(q.date,dd*100,color=color,label=label,lw=1.4)
ax[0,0].set_title('Comparable capital paths',loc='left');ax[0,0].set_ylabel('Value of initial 1');ax[0,0].legend(frameon=False,ncol=2,fontsize=8)
ax[1,0].set_title('Risk policy changes the path',loc='left');ax[1,0].set_ylabel('Drawdown (%)')
for z in ax[:,0]:z.grid(axis='y',alpha=.6);z.xaxis.set_major_locator(mdates.YearLocator(2));z.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
q=paths[(paths.population=='SECTORS12')&(paths.policy=='RSI_SELECTED')].sort_values('date');q=q[q.date<'2020-04-01']
exposure=q.held/(q.nav+.001*q.held)*100
ax[0,1].fill_between(q.date,exposure,color=TEAL,alpha=.15);ax[0,1].plot(q.date,exposure,color=TEAL,lw=1.8)
ax[0,1].axhline(28.955,color=GRAY,ls='--',label='Full-period average: 29.0%')
ax[0,1].set_ylim(-2,105);ax[0,1].set_ylabel('Invested capital (%)');ax[0,1].set_title('Early-2020 exposure reached 91.7%',loc='left')
ax[0,1].legend(frameon=False,fontsize=8,loc='lower right');ax[0,1].xaxis.set_major_locator(mdates.MonthLocator());ax[0,1].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
cc=pd.read_csv(R/'results/sector_accepted_contrasts.csv')
v=cc.mean_selected_minus_alternative.to_numpy()*100;lo=cc.lo.to_numpy()*100;hi=cc.hi.to_numpy()*100
ax[1,1].errorbar(v,[1,0],xerr=[v-lo,hi-v],fmt='o',capsize=6,color=TEAL,lw=2,markersize=7)
ax[1,1].axvline(0,color=GRAY,lw=1);ax[1,1].set_yticks([1,0],['Versus basket','Versus SPY']);ax[1,1].set_ylim(-.5,1.5);ax[1,1].set_xlim(-1.7,3.3)
ax[1,1].set_title('Selection increment remains uncertain',loc='left');ax[1,1].set_xlabel('Mean paired trade advantage (pp)');ax[1,1].grid(axis='x',alpha=.5)
for i,(p,l,h) in enumerate(zip(v,lo,hi)):ax[1,1].text(p,1-i+.18,f'{p:+.2f} [{l:+.2f}, {h:+.2f}]',ha='center',fontsize=9)
save(fig,'sector_capital','93 scheduled-mature accepted slots on 51 dates; four additional entries remain in account paths. Costs and zero-yield cash included.\nIntervals describe paired trade-return increments, not CAGR differences. Sources: portfolio_paths.csv and sector_accepted_contrasts.csv.')
print('FIGURES',sorted(p.name for p in O.iterdir()))
