"""Publication figures from already accepted result tables; no new strategies."""
from pathlib import Path
import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/addition_timing_matplotlib")
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'figures';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
 'axes.spines.right':False,'axes.spines.left':False,'axes.edgecolor':'#c4c9cf',
 'axes.labelcolor':'#344150','text.color':'#1d2c3b','xtick.color':'#526170',
 'ytick.color':'#526170','svg.hashsalt':'addition-timing-20261021'})


def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=170,facecolor='white',bbox_inches='tight')
    fig.savefig(OUT/(name+'.svg'),facecolor='white',bbox_inches='tight',metadata={'Date':None})
    plt.close(fig)


c=pd.read_csv(ROOT/'results/account_contrasts.csv')
c=c[(c.scenario=='PRIMARY')&(c.comparison=='SIGNAL-IMMEDIATE')].set_index('basket')
order=['SPY','SECTOR11','CORE5','PEERS13'];labels=['SPY | primary','11 sector funds','Prior core five','Prior 13 peers']
v=c.loc[order,'terminal_difference'].to_numpy()
fig,ax=plt.subplots(figsize=(10.8,5.3))
y=np.arange(4)
ax.barh(y,v,color=['#b94b38','#c66c5b','#d38d7e','#dca89c'],height=.57)
ax.set_yticks(y,labels);ax.invert_yaxis();ax.axvline(0,color='#596575',linewidth=1)
ax.set_xlim(-2300,100);ax.set_xticks([-2000,-1500,-1000,-500,0]);ax.xaxis.set_major_formatter(FuncFormatter(lambda x,p:f'${x:,.0f}'))
ax.set_xlabel('Signal waiting minus immediate monthly purchase | terminal dollars')
for i,x in enumerate(v):ax.text(x-55,i,f'-${abs(x):,.0f}',ha='right',va='center',weight='bold',fontsize=12)
ax.grid(axis='x',alpha=.16);ax.set_axisbelow(True)
fig.suptitle('Waiting reduced wealth in all four ownership baskets',x=.12,y=.98,ha='left',fontsize=18,weight='bold')
fig.text(.12,.90,'Same $82,000 funded monthly; same holdings after purchase; all cash and costs included.',fontsize=10.5)
fig.text(.12,-.01,'Jan 2020-Oct 8, 2026. Exposed historical sample. The baskets share the same signal calendar and market exposure.\nSource: account_contrasts.csv, primary scenario. These bars are historical dollar differences, not uncertainty intervals.',fontsize=8.5,color='#637080')
fig.subplots_adjust(top=.80,left=.20,bottom=.16,right=.97)
save(fig,'wealth_difference')

a=pd.read_csv(ROOT/'results/funding_year_attribution.csv')
a=a[(a.scenario=='PRIMARY')&(a.basket=='SPY')&(a.policy=='SIGNAL')].copy()
a['deployment']=np.where(a.reason=='deadline','Mandatory deadline','Signal-associated')
p=a.groupby(['funding_year','deployment']).terminal_difference.sum().unstack(fill_value=0)
fig,ax=plt.subplots(figsize=(11,5.7));x=np.arange(len(p));width=.35
for j,(name,color) in enumerate([('Signal-associated','#208878'),('Mandatory deadline','#bd6550')]):
    z=p[name].to_numpy();ax.bar(x+(j-.5)*width,z,width,label=name,color=color)
ax.axhline(0,color='#667180',linewidth=.9);ax.set_xticks(x,p.index);ax.set_ylabel('Contribution to final wealth difference ($)')
ax.set_ylim(-1400,900);ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:f'{x:,.0f}'));ax.grid(axis='y',alpha=.16);ax.set_axisbelow(True)
ax.legend(loc='upper left',frameon=False,ncol=2)
fig.suptitle('Useful signal months did not pay for the other waiting months',x=.10,y=.99,ha='left',fontsize=17,weight='bold')
fig.text(.10,.91,'SPY: signal-associated budgets +$925; mandatory-deadline budgets -$2,765; net -$1,841.',fontsize=10.5)
ax.set_xlabel('Year the contribution was funded (all wealth marked at Oct 8, 2026)')
fig.text(.10,-.015,'Groups are known after the month unfolds; they cannot be selected at funding using future signal arrival.\n2026 is partial. Signal-associated includes one purchase exactly at the deadline. Source: funding_year_attribution.csv.',fontsize=8.5,color='#637080')
fig.subplots_adjust(top=.81,bottom=.17,left=.12,right=.98)
save(fig,'waiting_attribution')

d=pd.read_csv(ROOT/'results/figure_daily.csv',parse_dates=['date'])
fig,(ax,ex)=plt.subplots(2,1,figsize=(11,7.1),sharex=True,gridspec_kw={'height_ratios':[2,1]})
for name,color,label in [('IMMEDIATE','#245c8a','Immediate'),('SIGNAL','#79519f','Signal with deadline'),('MONTH_END','#b57c20','Fixed month-end')]:
    z=d[d.policy==name]
    ax.plot(z.date,z.unit_nav,color=color,linewidth=1.6,label=label)
    ex.plot(z.date,z.invested_fraction,color=color,linewidth=1.05,alpha=.85)
ax.set_ylabel('Unit NAV (initial account unit = 1)');ax.legend(loc='upper left',frameon=False,ncol=3,fontsize=10)
ax.grid(axis='y',alpha=.16);ex.grid(axis='y',alpha=.16)
ex.set_xlim(d.date.min(),d.date.max())
ex.yaxis.set_major_formatter(PercentFormatter(1));ex.set_ylabel('Invested fraction');ex.set_ylim(-.02,1.04)
fig.suptitle('Temporary cash protection fades as accumulated holdings grow',x=.10,y=.98,ha='left',fontsize=17,weight='bold')
fig.text(.10,.92,'SPY accounts start empty. Temporary cash is a large fraction early and a smaller fraction as holdings grow.',fontsize=10.4)
fig.text(.10,.01,'Unit NAV removes external deposits from returns; it does not remove dependence on account inception.\nTerminal wealth is the primary comparison; time-weighted NAV can rank schedules differently. Source: figure_daily.csv.',fontsize=8.5,color='#637080')
fig.subplots_adjust(top=.86,bottom=.12,left=.11,right=.98,hspace=.10)
save(fig,'spy_account_path')
print('Generated 3 figures in PNG and SVG from frozen results.')
