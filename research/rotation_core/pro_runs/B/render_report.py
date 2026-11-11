"""Render the one authorized issue comment from audited small result tables."""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'out'

def number(x,scale=1,digits=2):
    return 'NA' if pd.isna(x) else f'{float(x)*scale:.{digits}f}'

def table(headers,rows):
    return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(map(str,r))+'|' for r in rows])+'\n'

def interval(row,ref):
    return number(row.get(ref+'_cagr_excess'),100)+' ['+number(row.get(ref+'_cagr_lo'),100)+', '+number(row.get(ref+'_cagr_hi'),100)+']' if pd.notna(row.get(ref+'_cagr_excess')) else 'NA'

def lag(row,which):
    status=row[which+'_status'];d=row[which+'_days']
    if pd.isna(status) or status=='NA':return 'NA'
    if status=='NONE':return 'NONE'
    if pd.isna(d):return status+'(init/unknown)'
    value=f'{int(d):+d}'
    return value if status in ['EXIT','ENTRY'] else status+'('+value+')'

def main(commit):
    base=f'https://github.com/mastermindx-market-intelligence/macro/blob/{commit}/research/rotation_core/pro_runs/B/'
    primary=pd.read_csv(OUT/'primary_era_results.csv');allrows=pd.read_csv(OUT/'results.csv')
    partial=pd.read_csv(OUT/'partial_segments.csv');calm=pd.read_csv(OUT/'false_pivots.csv')
    episodes=pd.read_csv(OUT/'episodes.csv');relative=pd.read_csv(OUT/'episode_relative.csv');leads=pd.read_csv(OUT/'episode_transitions.csv')
    protocol=(ROOT/'PROTOCOL.md').read_text()
    rules=protocol.split('## Pre-specified rules')[1].split('## Fixed sleeves')[0]
    chunks=['PRO-RUN B\n\n## 1. Pre-specified rules'+rules]
    chunks.append('''### Fixed definitions and implementation

**D:** Food, Soda, Beer, Smoke, Hshld, Hlth, MedEq, Drugs, Util. **C:** Toys, Fun, Clths, Chems, Rubbr, Txtls, BldMt, Cnstr, Steel, FabPr, Mach, ElcEq, Autos, Aero, Ships, BusSv, Hardw, Softw, Chips, LabEq, Trans, Rtail. These are fixed French49 economic groups, not estimated high-beta or valuation-growth stocks. Each sleeve equally allocates across eligible value-weighted industry portfolios. Members require 200 consecutive nonmissing returns, with at least 10 C and 4 D members. No backfill of later industries. Industry breadth is the fraction of eligible C industries above their own stated moving average.

Signals use gross total-return sleeve indexes. Decisions at close t execute at close t+1; new holdings first earn the return ending t+2. Existing holdings earn t+1, and that close incurs the fee. Initial holdings are bills. Costs are 25 bp per traded equity side before 1975, 5 bp thereafter; market-to-bills is one sale, C-to-D is two sides. Daily sleeve rebalancing and drift are charged. Fees multiply gross wealth by (1−cost). Stress doubles fees on identical allocations. Costs inside the published French portfolios are unobserved and omitted.

Macro observation month m is available on day1 of m+2 for credit/nominal yields and m+3 for unemployment/real yield. These are current-vintage conservative-lag simulations, not reconstructed real-time decisions. Credit/confluence do not exist before their inputs. Cash earns French RF; TB3MS is a yield diagnostic. No leverage or shorts.

**Three requested references:** (B1) French cap-weighted market total return; (B2) true equal-weighted stock market; (B3) a causal expanding-mean equity-exposure market/bills portfolio, traded with the same delay and fees. B3's target at t is the rule's mean intended equity allocation through t. It uses no future era average; its realized average exposure need not equal the strategy's ex-post average. Exact B2 is unavailable. A separate **E49 proxy** averages French49 equal-weighted industry returns with previous-close membership; it is not equal weight across stocks. B1/E49 are gross index references; B3 is costed. Passive C, D and a daily 50:50 C/D mix are additional fixed descriptive controls.

CAGR uses calendar time; volatility uses observed sessions/year, allowing historical Saturday sessions. Drawdown includes initial wealth. Up/down capture is the ratio of conditional mean daily strategy and market returns on positive/negative market sessions. Turnover is annual **gross equity traded notional**, not halved turnover.
''')
    chunks.append(f'''**Freeze/provenance:** [original ten-rule protocol](https://github.com/mastermindx-market-intelligence/macro/blob/ba5ae1e353c6f9738bbf8936b9032e71c747b9ba/research/rotation_core/pro_runs/B/PROTOCOL.md), [pre-outcome clarifications](https://github.com/mastermindx-market-intelligence/macro/blob/da384adb882181ecd33d3a0802f8c2d22f53d1d9/research/rotation_core/pro_runs/B/CLARIFICATIONS.md), and [missing-data treatment](https://github.com/mastermindx-market-intelligence/macro/blob/85f299a57d3f36fad9994a69d84853e3f07a5604/research/rotation_core/pro_runs/B/MISSING_DATA.md). No allocation definition or threshold changed after outcomes; **10 trials**. Transport fixes, missing-data identifiability and reporting corrections are recorded in [the audit]({base}RESEARCH_AUDIT.md).

## 2. Verdict and what this history establishes

**No tested rule demonstrates a robust excess-return edge under this protocol.** Of 30 prespecified rule/era slots, 21 have fully identified returns from their eligible starts and nine have unidentified intervals. No primary test passes Holm30; the smallest raw one-sided superiority p among the identified rows is **0.0728**. All adjusted p-values are 1.000. This is not evidence that all economically relevant effects are zero: the study's power is weak for small edges.

The descriptive seesaw is visible. Defensives beat C in **10 of 11 identifiable declines**; C beats D in **all 10 identifiable fixed recovery windows**. But the signals usually reacted after part of the relative move, and delay, whipsaws and missed rebounds consumed the apparent opportunity. In 1990–2019 every active rotation rule's interval against the static C/D mix includes zero. The passive D sleeve delivered 11.80% CAGR, C 10.86%, and the mix 11.55%; active R5–R10 ranged from 9.72% to 11.75%. Those fixed controls make it difficult to call passive defensive resilience rotation skill.

**The requested complete nine-decade experiment is not fully identifiable from these public files.** French49 contains missing returns after industries became eligible. The official TXT counterpart confirms the CSV holes. No zero imputation, dropped loss dates, substitute industries, or favorable data vintage was used. Unknown returns invalidate full-era paths. Exact later target rebalancing can restore known normalized weights; R7/R8 recover only when their feasible states synchronize. Nine affected full-era rows below are NA, with separate descriptive clean segments. Early macro rows cover only their stated dates, not the entire first era.

The sealed sample was excluded: every analysis date is on or before **2019-12-31**, and later raw records are discarded before numerical return parsing. No later outcome is used for a terminal episode or recommendation.
''')
    chunks.append('''## 3. Results by rule and era

All return, volatility, drawdown, exposure and capture figures below are percentages. **Δ** is a CAGR difference in percentage points/year, followed by a **pointwise 95% paired block-bootstrap interval**. Exact stock-EW excess is **NA in every row**; E49 is shown only as an explicitly different proxy. Missing benchmark observations also yield NA rather than a selected-date contrast.

`Eq` is mean realized strategy equity exposure. `B3eq` is its causal reference's mean realized exposure. `Turn` is gross equity notional traded/year. `2×` is CAGR at doubled fees. `False/calm` is mechanically defined on-to-off transitions per complete eligible calm year in the named era; it is not a claim that every such transition lost money.

`MDE80` is the approximate 80%-power detectable **annual log-return advantage**, in percentage points, using a two-sided Bonferroni/30 5% threshold. It differs from the CAGR units of Δ. Holm30 uses the frozen one-sided B3 annual log-growth superiority estimand. Partial paths take p=1 and have no full-era estimate.
''')
    def perf(df,era=None):
        rows=[]
        for _,r in df.iterrows():
            c=calm[(calm.rule==r.rule)&(calm.era==r.era)].iloc[0]
            period=(r.start+'..'+r.end) if pd.notna(r.start) else 'NA: data gaps'
            ident=r.rule if era is not None else r.era+' '+r.rule
            rows.append([ident,period,number(r.cagr,100),number(r.vol,100),number(r.maxdd,100),number(r.up_capture)+'/'+number(r.down_capture),number(r.equity,100),number(r.turnover),number(r.stress_cagr,100),number(c.false_pivots_per_calm_year)])
        return table(['Rule','Scored dates','CAGR','Vol','Worst DD','Up/Down','Eq','Turn','2×','False/calm'],rows)
    def excess(df,era=None):
        return table(['Rule','Δ cap M [95% CI]','Δ E49 proxy [95% CI]','Δ B3 [95% CI]','B3eq','Holm p','MDE80'],[[r.rule if era else r.era+' '+r.rule,interval(r,'M'),interval(r,'E49'),interval(r,'B3'),number(r.B3_equity,100),number(r.p_holm30,digits=3),number(r.B3_mde80,100)] for _,r in df.iterrows()])
    for era in ['1926-1959','1960-1989','1990-2019']:
        df=primary[primary.era==era]
        chunks.append('### '+era+'\n\n'+perf(df,era)+'\n'+excess(df,era))
    chunks.append('''### Descriptive clean segments for the nine incomplete era paths

These rows **do not replace the missing full-era results**. Before observing outcomes, the longest contiguous identified segment within each affected era was specified; ties choose the earliest. Selection used missingness only. Intervals are descriptive; their full-era primary tests remain unavailable with p=1. Exact dates are essential.
'''+perf(partial)+'\n'+excess(partial))
    chunks.append(f'''### Power, full-history scope and stress

Across the 21 identified primary rows, MDE80 ranges from **4.82 to 12.43 annual log-return percentage points**. Early credit/confluence inference has only about 5.6 years and roughly six 252-session blocks. The longest complete trend span, 1927-03-04..2019-12-31, has 9.61% net CAGR and −43.51% drawdown; its descriptive B3 log-growth advantage is +1.56 pp/year, CI [−0.30,+3.50], with approximate MDE80 3.85 pp/year. That pooled calculation is not an additional primary test or untouched validation set.

Costs matter. R1's first-era CAGR falls from 9.95% to 8.37% when fees double. Recent-era R5 falls from 9.81% to 8.72%, reflecting 19.84 units of annual gross traded notional; passive sleeve constituent costs remain additional unknowns. All other stress values are above and in [results.csv]({base}out/results.csv). No lower-cost variant was selected after inspection.

E49's 1990–2019 gross CAGR is **22.07%**, independently reproduced from its stored daily proxy. That is not a percent-unit or annualization error. It remains an uncosted equal-industry research-return proxy, with small-stock and daily-rebalancing exposure and unmeasured constituent/microstructure effects. These data do not identify which mechanism explains its magnitude. It must not be advertised as an implementable equal-weight market or used to adjudicate exact H5.
''')
    h=pd.read_csv(OUT/'h1_common_sample.csv')
    chunks.append('''## 4. H1: common-sample confluence comparison

The following is descriptive R4-minus-single **annual log-growth** pp/year, with pointwise 95% paired intervals. All four rules use the same dates within each row's era. No additional superiority declaration is made from this panel.
'''+table(['Era','Common start','Against','R4−single [95% CI]','R4 worst DD','Single worst DD'],[[r.era,r.start,r.R4_minus,number(r.log_excess,100)+' ['+number(r.log_lo,100)+', '+number(r.log_hi,100)+']',number(r.R4_maxdd,100),number(r.single_maxdd,100)] for _,r in h.iterrows()]))
    chunks.append('''Confluence does not consistently beat trend: R4−R1 is −2.26, −3.17 and +0.71 log pp/year across the eras. In the recent era it reduces calm-year exits from R1's 2.07/year to 0.36/year, but fewer switches also prolong some defensive spells. That is a tradeoff, not demonstrated superiority.

## 5. Episode anchors and defensive/cyclical behavior (H2/H4)

Anchors are the maximum French-market drawdown pair **inside each predeclared calendar window**, not hand-selected conventional S&P bear-market dates. Consequently, 1962/1969 windows exclude peaks in preceding years, and 1980–82 selects its largest internal decline. They are retrospective scoring anchors, never signal inputs.

Below, C/D returns and D−C are gross sleeve returns. Recovery is the next 252 observed market sessions after the trough. `N/R/K` are the peak-date known nominal-high, backward-real-high, and credit-stress flags (1=true, 0=false, NA=unavailable); derived flags only, with no raw FRED series or vendor price levels published.
''')
    rr=[]
    for _,r in relative.iterrows():
        flag='/'.join(number(r[c+'_peak'],digits=0) for c in ['nominal_high','real_high','credit'])
        rr.append([r.episode,str(r.peak)[:10],str(r.trough)[:10],number(r.market_drawdown,100),number(r.C_down,100),number(r.D_down,100),number(r.D_minus_C_down,100),number(r.D_minus_C_recovery,100),flag])
    chunks.append(table(['Episode','Peak','Trough','M DD','C decline','D decline','D−C decline','D−C recovery','N/R/K'],rr))
    chunks.append('''The major counterexample is 1973–74: D lost 54.62%, versus C's 52.40%; defensive leadership was absent. D also lost 39.23% during 2007–09 despite its 23.81 pp relative advantage. Relative defense is not capital preservation. The 2000–02 defensive advantage was unusually large (+71.58 pp), and the subsequent C rebound reversed 38.17 pp of relative performance over the fixed recovery. No episode count establishes literal flows of money.

### Every rule in every episode

Exit/entry offsets are **observed market sessions**, not calendar days. `PRE(−n)` means already off at the peak; the last identified exit was n sessions earlier. `ON(−n)` means already risk-on at the trough, potentially from a premature entry; it does not claim bottom recognition. `NONE` means no qualifying pivot within the frozen window; `NA` means the needed inputs/path are unidentified. The last entry or exit can be well outside the named episode. No favorable post-trough entry replaces an earlier ON state.

`Avoided` is market drawdown loss minus strategy drawdown loss on the common peak-close-to-trough-close path; positive is protection. `Missed` is market minus strategy cumulative return over the next 252 sessions; negative is strategy outperformance. Decline and recovery eligibility are evaluated separately. Every available recovery here has 252 sessions inside the cutoff. False pivots/calm-year are in section3 and the complete denominator table below, rather than repeated 12 times per rule.
''')
    for episode in relative.episode:
        df=episodes[episodes.episode==episode]
        chunks.append('#### '+episode+'\n\n'+table(['Rule','Peak→exit','Trough→entry','Avoided (pp)','Missed (pp)'],[[r.rule,lag(r,'exit'),lag(r,'entry'),number(r.drawdown_avoided,100),number(r.upside_missed,100)] for _,r in df.iterrows()]))
    calmrows=[]
    for rid in ['R'+str(i) for i in range(1,11)]:
        row=[rid]
        for era in ['1926-1959','1960-1989','1990-2019']:
            c=calm[(calm.rule==rid)&(calm.era==era)].iloc[0]
            row.append(str(int(c.false_pivots))+'/'+str(int(c.calm_years))+' = '+number(c.false_pivots_per_calm_year))
        calmrows.append(row)
    chunks.append('### False-pivot denominators\n\nEach cell is exits / complete eligible calm years = rate per calm year. These cover eligible calm years throughout the named era, including outside any displayed partial return segment.\n\n'+table(['Rule','1926-1959','1960-1989','1990-2019'],calmrows))
    chunks.append('''Trend provided substantial protection in the 1929–32, 1973–74 and 2007–09 windows, but it missed 97.6, 25.8 and 51.2 pp of the following fixed-window market recoveries. In 1987 the next-close convention matters: R1 exited 38 sessions after the peak and avoided only 3.7 pp of the full decline. Credit and confluence often re-entered later: after the 2009 trough R1 re-entered at +58 sessions, R2/R4 at +103, while R3 had no re-entry within 252 sessions. R8's +11-session C re-entry was faster, but it remained fully exposed to equities and its whole-era drawdown was still 48.93%.

### Did the signal lead the defensive relative move?

For every within-window on→off transition, plus a designated earlier PRE exit, compare gross D−C over the preceding63 and next63 sessions. `Follower` means prior63 D−C>0; `Anticipator` means prior63≤0 and next63>0. Positive prior leadership may subsequently reverse. Missing horizons are NA. These overlapping dates are descriptive, not independent prediction trials.

The designated-exit classifications by episode are below: F=follower; A=anticipator; X=no prior lead and no positive subsequent defensive lead; —=no designated identified exit or unavailable relative interval. The full transition table retains actual dates, offsets and both relative-return values.
''')
    design=leads[leads.designated_exit]
    classification={'follower':'F','anticipator':'A','no_forward_defensive_lead':'X','unavailable':'—'}
    lrows=[]
    for ep in relative.episode:
        row=[ep]
        for rid in ['R1','R2','R3','R4','R5','R6','R7','R8','R9','R10']:
            sel=design[(design.episode==ep)&(design.rule==rid)]
            row.append(classification[sel.iloc[0].description] if len(sel) else '—')
        lrows.append(row)
    chunks.append(table(['Episode']+['R'+str(i) for i in range(1,11)],lrows))
    chunks.append(f'''Across 89 designated rows, 65 are followers, 17 anticipators, six have no forward defensive lead, and one is unavailable. The counts overlap heavily across rules and episodes; they are not 89 independent observations. R5 follows an existing relative move in 11 of its 12 designated exits. R8 does so in 11 of 12. This does not support presenting either as an anticipatory top detector. [All dated transitions and relative windows]({base}out/episode_transitions.csv).

## 6. Rates, real-rate proxy and credit conditioning

At eligible month-ends, measure the next63-session gross D−C return. The table shows mean relative return in each state and the number of usable months. Months overlap; no inference or causal identification is claimed. Real yield is nominal long yield minus trailing CPI inflation, not ex-ante expected real yield. The curve is Shiller long yield minus TB3MS. Early missing states remain NA.
''')
    rates=pd.read_csv(OUT/'rate_conditions.csv');rr=[]
    for era in ['1926-1959','1960-1989','1990-2019']:
        for feature in ['nominal_high','real_high','credit','curve_inverted']:
            vals=[]
            for state in [0,1]:
                sel=rates[(rates.era==era)&(rates.feature==feature)&(rates.state==state)]
                vals.append('NA' if not len(sel) else number(sel.iloc[0].mean_D_minus_C_next63,100)+' (n='+str(int(sel.iloc[0].months))+')')
            rr.append([era,feature]+vals)
    chunks.append(table(['Era','Known state','False: mean D−C63 (months)','True: mean D−C63 (months)'],rr))
    chunks.append('''Nominal-high changes from favorable relative conditioning in the first era to slightly unfavorable in the middle era and favorable again in the last. Credit-stress forward-relative returns also change sign. Recent inverted-curve months number only16 and average −1.08 pp D−C over the next63 sessions. These observations do not establish an invariant rate/credit allocation rule. R9's recent positive CAGR point estimate comes with 63.11% drawdown and a B3 interval crossing zero; R10 supplies no robust edge.

## 7. Blunt hypothesis verdicts

|Hypothesis|Verdict|Reason|
|---|---|---|
|H1: trend/credit/macro confluence beats any one alone|**Not supported**|Common-sample comparisons do not show consistent superiority; trend wins on return in the first two available eras. Full early-history and real-time macro claims also cannot be established.|
|H2: defensives lead, and switching captures an edge|**Not supported as a trading-edge claim**|The descriptive leadership clause is supported in the selected identifiable episodes (10/11 declines; reversal in10/10 recoveries), but active switching fails to establish incremental value over fixed exposures.|
|H3: breadth divergence tops and washout bottoms supply useful pivots|**Not supported where testable**|R7/R8 have no corrected edge. R7 never exits in the 1987,1990 or late2018 decline window; R8 can re-enter sooner while retaining large equity drawdowns. Earlier full paths have data gaps, and industry breadth is not stock breadth.|
|H4: rates/real rates/credit give reliable conditioning|**Not supported as a robust allocation advantage**|Descriptive associations vary by era; R9/R10 lack reliable excess. R10 combines rates with credit, so it cannot isolate a real-rate effect. Current-vintage and ex-post real-yield limitations remain.|
|H5: cap versus equal-weight stock market changes the opponent|**Untestable as specified**|True daily stock-EW history was not obtained. E49 is a visibly different proxy and cannot settle concentration-versus-equal-stock-weight claims.|

No verdict promotes a rule into live sizing, exits, rankings or alerts. These findings do not disprove every possible rotation strategy; they reject a claim of demonstrated success for this fixed family.

## 8. Three rules for a frozen second protocol

Retain a small mechanism-testing panel. These are controls/challengers selected for interpretability and the remaining question, not statistically accepted winners. Freeze exact inputs, costs, exposure references and acceptance before any new evaluation; do not silently spend the sealed sample on exploratory revisions.

1. **R1 unchanged:** M when its total-return level is strictly above its inclusive 200-session SMA; otherwise bills. It is the transparent risk-cut control. Require improvement over the causal exposure reference, with an explicit tolerated missed-upside budget.
2. **R4 unchanged:** bills when at least two of bearish M/SMA200, credit above its previous12-month mean, and U3−trailing12-month-min(U3)≥0.50 pp are true; otherwise M. All inputs must exist with the frozen lags. Keep it solely as the direct incremental-confluence challenger to R1.
3. **R5 unchanged:** C when its 126-session gross total return strictly exceeds D's; otherwise D. Keep it as the simplest direct switching test and compare it with passive C, D and the static mix. Its turnover/missed-recovery budget must be explicit.

Drop **R2 and R3 as standalone allocations** (retain their inputs inside the unchanged R4); **R6** (no demonstrated benefit from replacing cash with defensive equities under the confluence gate); **R7** (rare divergence trigger misses several requested declines); **R8** (faster washout re-entry does not establish durable-bottom or allocation value); **R9/R10** (unstable conditioning and no robust incremental edge). R9's relatively high recent CAGR is insufficient to rescue a rule that suffered a larger drawdown than the market. R8 may remain a documented failed recovery hypothesis, not an additional candidate in this three-rule panel.

The adviser suggested retaining R8/R7 if the next protocol prioritizes mechanism coverage. The principal chooses the narrower three-rule panel because this commission asks which rules merit the scarce trial budget; the data do not establish additional breadth-rule value. This is a research-design judgment, not a changed outcome or hidden trial.
''')
    chunks.append('''## 9. Sources, actual starts, statistical method and limitations

|Input|Observed source start|Use and limit|
|---|---|---|
|French daily market/SMB/HML/RF|1926-07-01|Cap-market total return and bills; retrospective CRSP research portfolios.|
|French daily momentum|1926-11-03|Descriptive factor exposures, not a signal variant. It does not start in July.|
|French daily12/17/49 VW and EW industries|1926-07-01|All downloaded/coverage-checked;49 drives the ten rules.12/17 are not searched alternate universes. Some49 members are absent early and some eligible returns later go missing.|
|French daily size portfolios|1926-07-01|Coverage/source check. NYSE-breakpoint deciles cannot reconstruct exact whole-market stock-EW by simple averaging.|
|Shiller monthly price/CPI/long yield|1871-01-01|Long-rate and backward-real signals; monthly composite price is a descriptive source, not daily execution data.|
|FRED BAA|1919-01-01|Source context; not substituted for the missing early Treasury spread.|
|FRED BAA10YM and GS10|1953-04-01|Credit/long-rate source; after12-month history and lag, credit rules start1954-06-02.|
|FRED TB3MS|1934-01-01|Curve diagnostic, not bill total return.|
|FRED UNRATE|1948-01-01|After rolling history and lag, R3 starts1949-05-03.|
|Public Yahoo S&P500 daily price endpoint|1927-12-30|Descriptive price-return cross-check on the fixed French-market episode dates; not the total-return benchmark.|

Primary source/method documentation: [French library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html), [market/factors](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/f-f_factors.html), [daily momentum](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_mom_factor_daily.html), [49-industry construction](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_49_ind_port.html), [12 industries](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_12_ind_port.html), [17 industries](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_17_ind_port.html), [size construction](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_port_form_sz.html), [Shiller](https://shillerdata.com/), [BAA10YM](https://fred.stlouisfed.org/series/BAA10YM), [BAA](https://fred.stlouisfed.org/series/BAA), [GS10](https://fred.stlouisfed.org/series/GS10), [TB3MS](https://fred.stlouisfed.org/series/TB3MS), [UNRATE](https://fred.stlouisfed.org/series/UNRATE), [ALFRED vintage explanation](https://alfred.stlouisfed.org/help), [FRED API-key requirements](https://fred.stlouisfed.org/docs/api/api_key.html), and [CRSP historical-index availability](https://indexes.morningstar.com/research-data-products/crsp-historical-indexes-database). Exact downloaded URLs, SHA256 hashes and coverage are in the manifest. No raw vendor prices or FRED series are committed.

**Inference:** paired circular moving blocks of252 observations,5,000 resamples,seed20261111; identical draws within each comparison. Bootstrap realized log-return paths within each era. Center the difference distribution for the one-sided superiority p, Holm-correct all30 primary slots, and use pointwise95% intervals. Pooled statistics, cost stress, passive controls, episode/rates diagnostics and H1 head-to-head comparisons are descriptive. The MDE is (z[1−.05/(2×30)]+z[.80])×bootstrap SE. No block-length or parameter search occurred.

### Limitations that constrain acceptance

- **Incomplete requested coverage:** market history begins mid1926 and signals need warmup. Credit/confluence begin1954; unemployment1949. Nine full-era rotation paths are unidentified. Clean segments do not complete them.
- **Missing returns:** early empty industries and later missing observations are different problems.200-session eligibility handles entry history, not unknown future returns. Loss-date gaps are retained; whole-path wealth across them is unknowable.
- **No exact stock-EW reference:** neither E49 nor equal averaging of NYSE-breakpoint size portfolios is the requested market. H5 and all exact B2 excess estimates remain open.
- **No real-time macro panel:** the unauthenticated ALFRED API request returned HTTP400; no complete vintage panel was obtained. Conservative lags do not eliminate revisions, seasonal-adjustment history, data-definition changes or ex-post knowledge.
- **Retrospective equity data:** French rebuilds historical research series; industry SIC assignments, CRSP corrections, delisting treatment and today's file vintage are not a tape of what an investor actually saw then. Hashes identify this input version but cannot freeze future provider revisions.
- **Synthetic instruments:** investors could not buy these exact broad/industry portfolios throughout the whole history. Index returns include theoretical portfolio construction; constituent trading, access, liquidity, taxes, fund fees and capacity are unmodeled.
- **Cost convention:** the frozen fee is the per-side rate times the absolute change from pretrade equity weights to target weights, followed by a multiplicative reduction of portfolio value. This is a target-notional approximation. Exact post-fee traded-notional financing would solve a fee-dependent rebalance equation; that refinement was not implemented. Its fee discrepancy is second order in the cost rate, with no universal conservative direction. Both the base case and doubled-cost stress retain the registered convention.
- **Omitted costs:** fees cover market/sleeve allocation and across-industry rebalancing. They omit hidden turnover inside French VW/EW portfolios, bid/ask, market impact, historical financing constraints and nonconstant slippage. Even 2× does not establish realistic all-in historical costs.
- **Execution at published close:** no opening/high/low/slippage assumptions, overnight liquidity model or market-on-close feasibility proof. The full next-close delay is enforced but cannot repair incomplete prices.
- **Group definition:** C is not a pure growth valuation factor or a fitted high-beta portfolio. Industry definitions evolved; missing early members alter composition. Industry breadth hides dispersion and concentration within each industry. Factor diagnostics show lower D beta, which can explain part of relative defense without proving timing skill.
- **Backward real rates:** nominal yield minus trailing inflation is not expected future real yield. R10 is a combined real-rate/credit rule and cannot isolate either mechanism.
- **Power and dependence:** three eras and a few crisis episodes are limited independent evidence.252-session blocks retain some dependence, not regime-transition uncertainty. Short early macro samples have few blocks; intervals/power approximations may be unstable.
- **Fixed-path uncertainty:** bootstrap paths condition on realized inputs/states. They do not rerun every strategy on hypothetical resampled histories or account for uncertainty from data revisions, omitted costs, missing data, model design or selection of the public hypotheses.
- **Historical study, not prospective validation:** this family was frozen within this commission before outcomes, but famous indicators/crises already influenced the question. Nothing here is a new untouched validation of a published strategy. Second-protocol selection is itself informed by these results.
- **Multiple endpoints:** only B3 log-growth superiority across30 rule/era slots is confirmatory. Confidence intervals on other references are pointwise; comparing many episodes, controls and conditions can generate attractive patterns by chance.
- **Exposure reference:** expanding-average B3 is causal but not perfectly matched to completed-era exposure or beta. The early and recent average differences are reported. All-equity C/D rules can still differ in market beta; the static controls are necessary but not complete risk attribution.
- **Gross benchmark asymmetry:** conventional B1/E49 are uncosted; E49's large gross return is neither a tradable quote nor an exact equal-stock-weight result. No microstructure attribution is established by this dataset.
- **Episode construction:** listed stress windows are selected by the commission. Within-window maximum drawdown uses hindsight for scoring, cannot locate a live peak, may exclude a preceding-year high, and is not an exhaustive population of corrections. Forward63 windows overlap; lead/follow labels cannot prove causal prediction.
- **Calm/false-pivot definition:** a10%-drawdown threshold and the listed excluded years mechanically define calm. Relative-rotation exits in those years can still be useful; the label is a whipsaw proxy.
- **S&P scope:** daily public price levels are supplementary, exclude dividends, and early composite history is not the modern500-stock constituent basket. No raw levels are published. The French cap-market index is the actual study opponent.
- **Asset scope:** risk-off means bills or defensive equities in these rules. No duration-Treasury, gold, commodity, currency or international allocation was tested; long yields are conditioning inputs, not a Treasury-bond total-return strategy.
- **No flow or trading authority:** asset returns do not identify literal capital flows, optimal sizing, utility/preferences or real execution. A defensive winner can still lose heavily, and a confirmed rebound can still fail.
''')
    chunks.append(f'''### Validation and code location

Code and small tables: [`research/rotation_core/pro_runs/B/`]({base}README.md), commit `{commit}`, branch `pro-run/rotation-b-20261111`. [Primary era table]({base}out/primary_era_results.csv), [separate partial segments]({base}out/partial_segments.csv), [120 episode rows]({base}out/episodes.csv), [passive controls]({base}out/passive_references.csv), [source/run manifest]({base}out/run_manifest.json), [integrity tests]({base}test_integrity.py), [independent accounting receipt]({base}out/independent_checks.json).

Twelve synthetic integrity tests passed. A separate vectorized calculation reproduced every identified R1–R4 daily return exactly, maximum absolute error0. A distinct methodological adviser reviewed design/source before outcomes, challenged missing-data and lead/follow semantics, and checked the final tables. Technical review is not a GitHub approval or acceptance for trading. No PR, merge or production effect was requested or performed.

**Return disposition:** commissioned research delivered with explicit untestable elements; no strategy accepted. The next programme decision is whether to freeze the three-rule second protocol after resolving the stock-EW/vintage/data-gap requirements. The existing sealed sample remains reserved.
''')
    report='\n\n'.join(chunks).replace('zero0','zero')
    (ROOT/'REPORT.md').write_text(report)
    print('report bytes',len(report.encode()),'characters',len(report),'words',len(report.split()))
    assert report.startswith('PRO-RUN B\n')
    assert len(report)<65536,'GitHub issue comment too long'

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True);main(parser.parse_args().commit)
