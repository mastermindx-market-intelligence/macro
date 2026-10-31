"""Reproduce the September–October descriptive figure from the pinned census."""
import argparse, json, os
from pathlib import Path
os.environ.setdefault("MPLCONFIGDIR","/tmp/risk-radar-mpl")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    if a.input.suffix==".json":
        d=pd.DataFrame(json.loads(a.input.read_text())["rows"])
    else:
        d=pd.read_csv(a.input)
    d["date"]=pd.to_datetime(d["date"])
    colors={"SPY":"#183B56","RSP":"#37A6A0","DIA":"#B38B30","IWM":"#BD574C","QQQ":"#8562BF",
            "XLK":"#AD427D","SMH":"#6355AE","SOXX":"#BE8061","XLP":"#17876E","XLV":"#56A354","XLU":"#D19D29"}
    groups=[["SPY","RSP","DIA","IWM","QQQ"],["XLK","SMH","SOXX","XLP","XLV","XLU"]]
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    fig=plt.figure(figsize=(14,10.8),facecolor="#F9FAFB")
    gs=fig.add_gridspec(2,2,height_ratios=[1,1.05],hspace=.40,wspace=.17)
    axes=[fig.add_subplot(gs[0,0]),fig.add_subplot(gs[0,1]),fig.add_subplot(gs[1,:])]
    for ax,group,title in zip(axes[:2],groups,["Broad indexes · total return since 1 September","Technology and defenses · total return since 1 September"]):
        for t in group:
            s=d[d.ticker==t].sort_values("date")
            r=pd.to_numeric(s.obs_tr_return_1,errors="coerce")
            nav=(1+r).cumprod(skipna=False)
            y=(nav/nav.iloc[0]-1)*100
            ax.plot(s.date,y,label=t,color=colors[t],lw=2 if t in ["SPY","SMH","XLP","XLV"] else 1.5)
        ax.axhline(0,color="#8996A3",lw=.8,ls="--")
        ax.set_title(title,loc="left",fontsize=12,fontweight="bold",pad=15)
        ax.set_ylabel("Total return (%)")
        ax.legend(ncol=3,loc="upper left",fontsize=9,frameon=False)
    ax=axes[2]
    for t in ["SPY","XLK","SMH","XLP","XLV","XLU"]:
        s=d[d.ticker==t].sort_values("date")
        ax.plot(s.date,pd.to_numeric(s.obs_price_dd_63,errors="coerce")*100,label=t,color=colors[t],lw=2)
    ax.axhline(-5,color="#B95C57",lw=1,ls="--")
    ax.text(pd.Timestamp("2026-09-02"),-5.8,"5% descriptive damage threshold",fontsize=9,color="#9C5551")
    ax.axvline(pd.Timestamp("2026-10-12"),color="#BCC6CE",ls=":",lw=1)
    ax.set_title("Damage below each exposure's own 63-session high",loc="left",fontsize=12,fontweight="bold",pad=15)
    ax.set_ylabel("Price drawdown (%)")
    ax.legend(ncol=6,loc="lower left",frameon=False)
    for ax in axes:
        ax.set_facecolor("#FFFFFF")
        ax.grid(axis="y",color="#E1E7EB",lw=.8)
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.TU,interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        ax.tick_params(axis="x",labelsize=9)
        ax.set_xlim(pd.Timestamp("2026-09-01"),pd.Timestamp("2026-10-16"))
        ax.spines["left"].set_color("#CBD3DA")
        ax.spines["bottom"].set_color("#CBD3DA")
    fig.suptitle("A healthy headline can conceal damage — and the path matters",x=.065,y=.97,ha="left",fontsize=20,fontweight="bold",color="#163247")
    fig.text(.065,.928,"September–October 2026 · exposure census through 15 October · descriptive, revised-vintage evidence",fontsize=11,color="#526474")
    fig.text(.065,.057,"Returns: split- and dividend-adjusted close. Drawdowns: split-adjusted price close. DIA ends 14 October; no fill.",fontsize=9,color="#526474")
    fig.text(.065,.034,"Source: 36-ETF census at Macro 3ab3382af892; protocol 317cd3b9. Price ratios are not fund-flow evidence. No forecast or trade performance is claimed.",fontsize=9,color="#526474")
    fig.subplots_adjust(top=.86,bottom=.115,left=.065,right=.975)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(a.output,dpi=160,facecolor=fig.get_facecolor())
    plt.close(fig)
if __name__=="__main__":
    main()
