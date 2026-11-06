#!/usr/bin/env python3
"""Research plots from saved result tables; no candidate selection or refitting."""
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/entry-mechanism-mpl")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
FIG = ROOT/"deliverables"/"figures"
FIG.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "svg.fonttype": "none",
    "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "#fbfcfe",
    "axes.facecolor": "#fbfcfe", "text.color": "#17324d", "axes.labelcolor": "#17324d",
    "axes.titleweight": "bold", "xtick.color": "#53667a", "ytick.color": "#17324d"})
NAVY, TEAL, GOLD, BLUE, GRAY = "#173d63", "#147f79", "#c47b27", "#3a78b5", "#7b8794"


def save(fig, name):
    fig.savefig(FIG/f"{name}.png", dpi=190, bbox_inches="tight")
    fig.savefig(FIG/f"{name}.svg", bbox_inches="tight")
    p = FIG/f"{name}.svg"
    p.write_text("\n".join(line.rstrip() for line in p.read_text().splitlines())+"\n")
    plt.close(fig)


path = ROOT/"results"/"audit_compact.csv"
if not path.exists():
    path = ROOT/"results"/"frozen_rule_audit.csv"
a = pd.read_csv(path)
a = a[(a.period == "2020_2026_exposed") & (a.horizon == 63) & (a.pool == "primary")].set_index("rule_id")
ids = ["bottom|BASE:price_turn|none", "bottom|BASE:rsi_recovery|none",
       "bottom|S1W:curl|M1W:deep|none", "bottom|S1W:curl|M1W:deep_rising|1D:both_rising",
       "bottom|S2W:curl|M2W:deep_rising|3D:both_rising",
       "bottom|S1W:curl|M1W:cross|none", "bottom|S2W:curl|M2W:cross|none"]
names = ["Daily price turn", "Daily RSI recovers above 30", "1W Stoch + deep 1W MACD",
         "Improving 1W setup + 1D agreement", "Improving 2W setup + 3D agreement",
         "1W Stoch + 1W MACD crossover", "2W Stoch + 2W MACD crossover"]
q = a.loc[ids]
y = np.arange(len(q))
fig, axes = plt.subplots(1, 2, figsize=(13.6, 6.4), gridspec_kw={"width_ratios": [1, 1.1]})
axes[0].barh(y-.16, q.positive, height=.29, color=TEAL, label="Positive at 63-session endpoint")
axes[0].barh(y+.16, q.stop_positive, height=.29, color=GOLD, label="Positive with fixed 3-ATR stop")
for i, row in enumerate(q.itertuples()):
    axes[0].text(row.positive+.012, i-.16, f"{row.positive:.1%}", va="center", fontsize=9)
    axes[0].text(row.stop_positive+.012, i+.16, f"{row.stop_positive:.1%}", va="center", fontsize=9)
    for name, dy, col in [("ordinary", -.11, BLUE), ("peer", .11, GRAY)]:
        v = getattr(row, f"{name}_delta_mean")
        lo, hi = getattr(row, f"{name}_delta_ci_lo"), getattr(row, f"{name}_delta_ci_hi")
        axes[1].plot([lo, hi], [i+dy, i+dy], color=col, lw=1.7)
        axes[1].scatter(v, i+dy, s=30, color=col, zorder=3,
                        label=("Same-asset/state ordinary entries" if name == "ordinary" else "Same-date peers") if i == 0 else None)
for ax in axes:
    ax.invert_yaxis(); ax.grid(axis="x", alpha=.15); ax.set_axisbelow(True)
    ax.set_yticks(y); ax.xaxis.set_major_formatter(PercentFormatter(1))
axes[0].set_yticklabels([f"{name}  (n={int(n)})" for name, n in zip(names, q.n)], fontsize=10)
axes[1].set_yticklabels([])
axes[0].set_xlim(0, .87); axes[1].set_xlim(-.055, .125)
axes[1].axvline(0, color=NAVY, alpha=.6, lw=1)
axes[1].set_xticks([-.04, 0, .04, .08, .12])
axes[0].set_title("Endpoint success is not stopped-trade success", loc="left", fontsize=11)
axes[1].set_title("Incremental mean depends on the comparator", loc="left", fontsize=11)
axes[0].set_xlabel("Positive fraction after assumed 20 bp roundtrip cost")
axes[1].set_xlabel("Paired mean return difference, percentage points")
fig.suptitle("Executable entries: a different question from finding the exact low", x=.025, ha="left", fontsize=17)
axes[0].legend(loc="lower left", bbox_to_anchor=(-.02, -.28), frameon=False, fontsize=9)
axes[1].legend(loc="lower left", bbox_to_anchor=(-.02, -.28), frameon=False, fontsize=9)
fig.text(.025, .02, "2020–2026 exposed history; 48 exchange-traded assets; next-open entry. Pointwise exploratory 95% calendar-block intervals.\nOrdinary comparisons use matched observations only (91–99% coverage here); peers exclude the focal asset. No new holdout or portfolio claim.", fontsize=9, color="#53667a")
fig.subplots_adjust(left=.35, right=.98, top=.85, bottom=.25, wspace=.22)
save(fig, "entry_audit")

m = pd.read_csv(ROOT/"results"/"mechanism_summary.csv")
m = m[(m.period == "2020_2026_exposed") & (m.horizon == 63) & (m.overlap == "original")].set_index("arm")
ids = ["leader_reset_reclaim", "nonleader_reset_reclaim", "leader_weekly_stoch_yes", "leader_weekly_stoch_no", "leader_daily_stoch_yes", "leader_daily_stoch_no"]
names = ["Leader + reset + price reclaim", "Nonleader + reset + price reclaim", "Leader events: weekly curl present", "Leader events: weekly curl absent", "Leader events: daily curl present", "Leader events: daily curl absent"]
q = m.loc[ids]; y = np.arange(len(q))
fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.9), gridspec_kw={"width_ratios": [1.1, 1]})
axes[0].barh(y-.15, q.positive, .28, color=TEAL, label="Fixed endpoint")
axes[0].barh(y+.15, q.stop_positive, .28, color=GOLD, label="With 3-ATR stop")
axes[1].barh(y, q["mean"], .5, color=BLUE)
for i, row in enumerate(q.itertuples()):
    axes[0].text(row.positive+.012, i-.15, f"{row.positive:.1%}", va="center", fontsize=9)
    axes[1].text(row.mean+.003, i, f"{row.mean:.2%}", va="center", fontsize=10)
for ax in axes:
    ax.set_yticks(y); ax.invert_yaxis(); ax.grid(axis="x", alpha=.15); ax.set_axisbelow(True)
    ax.xaxis.set_major_formatter(PercentFormatter(1))
axes[0].set_yticklabels([f"{name}  (n={int(n)})" for name, n in zip(names, q.n)], fontsize=10)
axes[1].set_yticklabels([])
axes[0].set_xlim(0, .8); axes[1].set_xlim(0, .135)
axes[0].set_title("Reliability", loc="left", fontsize=12); axes[1].set_title("Average payoff", loc="left", fontsize=12)
axes[0].set_xlabel("Positive fraction"); axes[1].set_xlabel("Mean net return over 63 entry sessions")
fig.suptitle("Larger winners and more reliable winners are different objectives", x=.025, ha="left", fontsize=17)
axes[0].legend(loc="lower left", bbox_to_anchor=(-.02, -.26), ncol=2, frameon=False, fontsize=9)
fig.text(.025, .025, "22 surviving stocks; fixed lagged leadership, chronological reset and EMA10 reclaim. Oscillator arms retain the SAME original price-event timestamps.\nThe 51 weekly-gated events also contain a sparse favorable state-matched contrast; common-roster nonoverlap sensitivity changes the point estimate.", fontsize=9, color="#53667a")
fig.subplots_adjust(left=.36, right=.98, top=.84, bottom=.25, wspace=.2)
save(fig, "selection_timing_risk")

# Analytical illustration only, explicitly synthetic. No empirical outcomes used.
changes = np.r_[np.full(70, .2), np.full(35, -1.2), np.full(50, -.25), np.full(25, .7)]
price = pd.Series(200+np.cumsum(changes))
macd = price.ewm(span=12, adjust=False).mean()-price.ewm(span=26, adjust=False).mean()
hist = macd-macd.ewm(span=9, adjust=False).mean()
fig, axes = plt.subplots(2, 1, figsize=(11.8, 6), sharex=True, gridspec_kw={"height_ratios": [1.25, 1]})
axes[0].plot(price, color=NAVY, lw=2)
axes[1].bar(np.arange(len(hist)), hist, color=np.where(hist >= 0, TEAL, GOLD), width=.85)
for ax in axes:
    ax.axvspan(105, 154, color=BLUE, alpha=.09); ax.grid(alpha=.12); ax.set_axisbelow(True)
axes[1].axhline(0, color=GRAY, lw=.8)
axes[0].annotate("The decline slows, but price keeps falling", xy=(128, price.iloc[128]), xytext=(90, 202),
                 arrowprops={"arrowstyle": "->", "color": BLUE}, color=BLUE, fontsize=11)
axes[1].annotate("Histogram improves and crosses zero\nwithout a rising price trend", xy=(119, hist.iloc[119]), xytext=(64, 1.3),
                 arrowprops={"arrowstyle": "->", "color": BLUE}, color=BLUE, fontsize=10)
axes[0].set_ylabel("Synthetic price"); axes[1].set_ylabel("MACD histogram"); axes[1].set_xlabel("Synthetic daily bars")
axes[1].set_ylim(-1.9, 2.4)
fig.suptitle("A momentum improvement does not establish a price bottom", x=.045, ha="left", fontsize=17)
fig.text(.045, .02, "Illustration only: a constructed price path and standard price-MACD (12/26/9). This is an indicator-mechanics example, not a backtest or market forecast.", fontsize=9, color="#53667a")
fig.subplots_adjust(left=.09, right=.97, top=.88, bottom=.15, hspace=.15)
save(fig, "momentum_mechanics")
print("FIGURES_COMPLETE", len(list(FIG.glob("*.png"))))
