#!/usr/bin/env python3
"""Offline PB-D audit. Frozen input only; no fitting, network, or live effects.

Run: python reproduce_pb_d.py --input retro_grades.parquet --output RESULTS.json
Requires pandas, pyarrow, scipy, numpy. Outputs decimals, not percentage points.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy.stats import beta, binom, fisher_exact, norm

GIT_BLOB = "b0ee089e86269854b699f4667b47dd10a469374c"
SHA256 = "61bb8cc6ff0f1cfd14f33ba50fc5ce17db4c93e800f74e307c70c5606ae4f9d7"
KEY = ["as_of", "lane", "ticker", "horizon"]
LEGS = ["news_burst", "sue_fresh", "smartmoney_add"]
RETURNS = ["ret", "excess_spy", "excess_sector"]


def cp(x: int, n: int):
    if n == 0:
        return None
    return [0.0 if x == 0 else float(beta.ppf(.025, x, n-x+1)),
            1.0 if x == n else float(beta.ppf(.975, x+1, n-x))]


def metric(s: pd.Series):
    s = pd.to_numeric(s, errors="coerce").dropna()
    n, x = len(s), int(s.gt(0).sum())
    return {"observed": n, "positive": x, "mean": float(s.mean()) if n else None,
            "median": float(s.median()) if n else None,
            "min": float(s.min()) if n else None,
            "max": float(s.max()) if n else None,
            "iid_fixed_rule_exact95": cp(x, n)}


def summary(f: pd.DataFrame):
    out = {"n": len(f), "issuers": int(f.ticker.nunique()),
           "dates": int(f.as_of.nunique()), "entry_dates": int(f.entry_date.nunique())}
    for c in RETURNS:
        out[c] = metric(f[c])
    return out


def decorate(d: pd.DataFrame):
    d = d.copy()
    d["leg_count"] = d[LEGS].eq(True).sum(axis=1)
    # Count only explicit legacy booleans; unknown input is not a zero-leg signal.
    d["legs_known"] = d[LEGS].notna().all(axis=1)
    d.loc[~d.legs_known, "leg_count"] = np.nan
    return d


def treated(f: pd.DataFrame, kind: str):
    return f.news_burst.eq(True) if kind == "news" else f.leg_count.ge(2)


def control(f: pd.DataFrame, kind: str):
    return f.news_burst.eq(False) if kind == "news" else f.leg_count.lt(2)


def matched(f: pd.DataFrame, kind: str, by=("as_of",)):
    gaps, rows, details = [], [], []
    for keys, g in f.groupby(list(by), dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        a = pd.to_numeric(g.loc[treated(g, kind), "excess_spy"], errors="coerce").dropna()
        b = pd.to_numeric(g.loc[control(g, kind), "excess_spy"], errors="coerce").dropna()
        if len(a) and len(b):
            gap = float(a.mean() - b.mean())
            gaps.append(gap)
            rows.extend((a - b.mean()).tolist())
            row = {str(k): str(v) for k, v in zip(by, keys)}
            row.update(treated_n=len(a), control_n=len(b), treated_mean=float(a.mean()),
                       control_mean=float(b.mean()), gap=gap)
            # Retain every matched stratum, not only favorable strata.
            details.append(row)
    return {"strata": len(gaps), "matched_signal_rows": len(rows),
            "positive_strata": int(sum(x > 0 for x in gaps)),
            "positive_row_differences": int(sum(x > 0 for x in rows)),
            "stratum_equal_mean_gap": float(np.mean(gaps)) if gaps else None,
            "signal_row_equal_mean_gap": float(np.mean(rows)) if rows else None,
            "details": details}


def row_records(f):
    cols = ["as_of", "entry_date", "ticker", "sector", "entry_status", "leg_count"] + LEGS + RETURNS
    return json.loads(f[cols].sort_values(["as_of", "ticker"]).to_json(orient="records"))


def leave_one_out(h, kind, omit_column):
    t2 = h[h.tier_cascade.eq("T2")]
    a = t2[treated(t2, kind)]
    out = {}
    for k in sorted(a[omit_column].dropna().unique()):
        # Remove from both signal and control pools before matching.
        g = t2[t2[omit_column].ne(k)]
        s = g[treated(g, kind)]
        out[str(k)] = {"signal": summary(s), "same_date": matched(g, kind)}
    return out


def dependence(f):
    counts = f.groupby("ticker").size()
    dates = f.groupby("as_of").size()
    n = len(f)
    return {"issuer_rows": {str(k): int(v) for k, v in counts.items()},
            "date_rows": {str(k): int(v) for k, v in dates.items()},
            "largest_two_issuer_share": float(counts.nlargest(2).sum()/n) if n else None,
            "issuer_weight_concentration_equivalent": float(n*n/(counts**2).sum()) if n else None,
            "warning": "Weight concentration diagnostic, NOT an independent-trials effective n; dates/windows/roots may still share shocks."}


def paired(v, kind, horizon):
    a = v[v.horizon.eq(5) & v.tier_cascade.eq("T2") & treated(v, kind)]
    b = v[v.horizon.eq(horizon)]
    p = a.merge(b, on=["as_of", "ticker"], suffixes=("_5", "_later"), validate="one_to_one")
    p5 = pd.to_numeric(p.excess_spy_5, errors="coerce")
    ph = pd.to_numeric(p.excess_spy_later, errors="coerce")
    observed = p5.notna() & ph.notna()
    responders = observed & p5.gt(0)
    return {"h5_signal_n":len(a), "paired_n":int(observed.sum()),
            "later_unavailable":len(a)-int(observed.sum()),
            "h5_spy":metric(p5[observed]), "later_spy":metric(ph[observed]),
            "h5_responders":int(responders.sum()),
            "responders_still_positive":int(ph[responders].gt(0).sum()),
            "terminal_absolute_return_worsened":int((p.ret_later < p.ret_5).sum()),
            "rows":json.loads(p[["as_of","ticker","ret_5","ret_later","excess_spy_5","excess_spy_later"]].to_json(orient="records"))}


def power_report():
    def exact_n(p, target):
        for n in range(2, 2001):
            # First rejection threshold with P(X>=k | .5) <= alpha.
            k = int(binom.ppf(.95, n, .5)) + 1
            power = float(binom.sf(k-1, n, p))
            if power >= target:
                return {"n":n,"critical_successes":k,"power":power,
                        "attained_alpha":float(binom.sf(k-1,n,.5))}
        return None
    out = {"one_sided_iid_fixed_p0_0p5":{}, "independent_two_arm_approx":{}, "continuous_sd_scenarios":[]}
    for p in (.55,.60,.65):
        out["one_sided_iid_fixed_p0_0p5"][str(p)] = {str(t):exact_n(p,t) for t in (.8,.9)}
        pb = (.5+p)/2
        out["independent_two_arm_approx"][str(p)] = {}
        for power in (.8,.9):
            n = (norm.ppf(.975)*math.sqrt(2*pb*(1-pb)) + norm.ppf(power)*math.sqrt(.25+p*(1-p)))**2/(p-.5)**2
            out["independent_two_arm_approx"][str(p)][str(power)] = math.ceil(n)
    for sd in (.03,.05,.08):
        z = norm.ppf(.975)+norm.ppf(.8)
        n = (z*sd/.02)**2
        out["continuous_sd_scenarios"].append({"assumed_sd":sd,"target_delta":.02,
            "one_sample_n":math.ceil(n),"two_arm_n_per_arm":math.ceil(2*n),
            "four_cell_interaction_n_per_cell":math.ceil(4*n)})
    out["limitations"] = ["Planning assumptions, not fitted performance.","IID counts are not nightly rows.",
       "Exact-binomial power is discrete and nonmonotonic locally; verify the final locked n.",
       "Clustering, heavy tails, estimated variance and multiple endpoints require design-specific analysis."]
    return out


def analyse(d: pd.DataFrame):
    needed = set(KEY+LEGS+RETURNS+["rank_by","entry_date","tier_cascade","sector","entry_status"])
    if needed-set(d.columns):
        raise ValueError(f"Missing fields: {sorted(needed-set(d.columns))}")
    if d.duplicated(KEY).any():
        raise ValueError("Duplicate economic observation key")
    d = decorate(d)
    v = d[d.rank_by.eq("us_prophet_v3") & d.lane.eq("buy")].copy()
    out = {"status":"DISCOVERY_ONLY_ZERO_SIGNAL_AUTHORITY", "source_commit":"2f2feec4851b45636f63a48ec61e6f0b02b8118a",
        "source_path":"data/us_board_ledger/retro_grades.parquet", "source_git_blob":GIT_BLOB,
        "source_sha256":SHA256, "source_shape":[len(d),len(d.columns)-2],
        "unit":"decimal simple returns; multiply by 100 for percentage points",
        "versions":{"pandas":pd.__version__,"numpy":np.__version__,"scipy":scipy.__version__},
        "population":{}, "horizons":{}, "pairs":{}, "era":{}, "claim_checks":[],
        "uncertainty_note":"Intervals and Fisher tests are conditional IID fixed-rule illustrations, not selection/dependence-corrected confirmation."}
    for horizon in (5,10,21):
        h=v[v.horizon.eq(horizon)].copy()
        t2=h[h.tier_cascade.eq("T2")]
        first_t2=t2.sort_values(["as_of","ticker"]).drop_duplicates("ticker")
        first_all=h.sort_values(["as_of","ticker"]).drop_duplicates("ticker")
        block={"v3_buy":summary(h),"t2_all":summary(t2),"news":{},"multi":{},
               "tier_leg_count":{},"first_t2_leg_count":{},"generic_multileg":summary(h[h.leg_count.ge(2)]),
               "first_all_tier_multileg":summary(first_all[first_all.leg_count.ge(2)]),
               "first_all_then_t2_leg_count":{},
               "first_all_then_t1_multileg":summary(first_all[first_all.tier_cascade.eq("T1") & first_all.leg_count.ge(2)]),
               "first_t1_then_multileg":summary(h[h.tier_cascade.eq("T1")].sort_values(["as_of","ticker"]).drop_duplicates("ticker").query("leg_count >= 2"))}
        out["population"][str(horizon)]={"asof_min":str(h.as_of.min()),"asof_max":str(h.as_of.max()),
            "tier_observed":int(h.tier_cascade.notna().sum()),
            "tier_missing":int(h.tier_cascade.isna().sum()),
            "source_price_basis":{str(k):int(n) for k,n in h.price_basis.value_counts(dropna=False).items()},
            "source_price_source":{str(k):int(n) for k,n in h.price_source.value_counts(dropna=False).items()}}
        for tier,g in h.groupby("tier_cascade",dropna=False):
            for count,gg in g.groupby("leg_count",dropna=False):
                block["tier_leg_count"][f"{tier}:{count}"]=summary(gg)
        for count,g in first_t2.groupby("leg_count",dropna=False):
            block["first_t2_leg_count"][str(count)]=summary(g)
        for count,g in first_all[first_all.tier_cascade.eq("T2")].groupby("leg_count",dropna=False):
            block["first_all_then_t2_leg_count"][str(count)]=summary(g)
        for kind in ("news","multi"):
            s=t2[treated(t2,kind)]
            first_signal=s.sort_values(["as_of","ticker"]).drop_duplicates("ticker")
            first_t2_signal=first_t2[treated(first_t2,kind)]
            b={"signal":summary(s),"control":summary(t2[control(t2,kind)]),
               "not_t2_signal":summary(h[~h.tier_cascade.eq("T2") & treated(h,kind)]),
               "not_t2_control":summary(h[~h.tier_cascade.eq("T2") & control(h,kind)]),
               "not_t2_definition":"Outside T2, INCLUDING missing tier labels; not a certified non-T2 comparator.",
               "not_t2_missing_tier_signal_n":int((h.tier_cascade.isna() & treated(h,kind)).sum()),
               "not_t2_missing_tier_control_n":int((h.tier_cascade.isna() & control(h,kind)).sum()),
               "first_qualifying_per_issuer":summary(first_signal),
               "first_t2_per_issuer":summary(first_t2_signal),
               "first_t2_control":summary(first_t2[control(first_t2,kind)]),
               "action_open":summary(s[s.entry_status.isin(["buy_now","partial"])]),
               "without_INTC":summary(s[s.ticker.ne("INTC")]),
               "without_ADM_PRIM":summary(s[~s.ticker.isin(["ADM","PRIM"])]),
               "dependence":dependence(s),"rows":row_records(s),"first_t2_rows":row_records(first_t2_signal),
               "matched":{},"leave_one_issuer_out":leave_one_out(h,kind,"ticker"),
               "leave_one_date_out":leave_one_out(h,kind,"as_of"),
               "leave_one_sector_out":leave_one_out(h,kind,"sector")}
            for by in [("as_of",),("as_of","sector"),("as_of","sector","entry_status")]:
                b["matched"][",".join(by)]=matched(t2,kind,by)
            if horizon==5:
                for field in ("fwd_mfe_5","mae_close_excess_spy","mae_close_excess_sector"):
                    b[field]={"signal":metric(s[field]),"control":metric(t2.loc[control(t2,kind),field])}
            a=first_t2_signal.excess_spy.dropna()
            c=first_t2.loc[control(first_t2,kind),"excess_spy"].dropna()
            if len(a) and len(c):
                table=[[int(a.gt(0).sum()),int(a.le(0).sum())],[int(c.gt(0).sum()),int(c.le(0).sum())]]
                ft=fisher_exact(table,alternative="greater")
                b["first_t2_iid_fisher"]={"table":table,"one_sided_p":float(ft.pvalue),
                     "odds_ratio":float(ft.statistic) if math.isfinite(ft.statistic) else "infinite"}
            block[kind]=b
        out["horizons"][str(horizon)]=block
    for kind in ("news","multi"):
        out["pairs"][kind]={str(h):paired(v,kind,h) for h in (10,21)}
    for era,g in d[d.horizon.eq(5)&d.lane.eq("buy")].groupby("rank_by",dropna=False):
        signal=g[g.tier_cascade.eq("T2")&g.news_burst.eq(True)]
        out["era"][str(era)]={"n":len(g),"dates":int(g.as_of.nunique()),"news_observed":int(g.news_burst.notna().sum()),
            "news_true":int(g.news_burst.eq(True).sum()),"signal":summary(signal),"rows":row_records(signal),
            "price_basis":{str(k):int(n) for k,n in signal.price_basis.value_counts(dropna=False).items()}}
    a=out["horizons"]["5"]; n=a["news"]; m=a["multi"]
    checks=[("news_h5_spy",[10,11],[n["signal"]["excess_spy"]["positive"],n["signal"]["n"]]),
      ("news_h5_absolute",[8,11],[n["signal"]["ret"]["positive"],n["signal"]["n"]]),
      ("news_first_qualifying_spy",[6,7],[n["first_qualifying_per_issuer"]["excess_spy"]["positive"],n["first_qualifying_per_issuer"]["n"]]),
      ("news_first_qualifying_absolute",[4,7],[n["first_qualifying_per_issuer"]["ret"]["positive"],n["first_qualifying_per_issuer"]["n"]]),
      ("legacy_multi_h5_spy",[10,12],[m["signal"]["excess_spy"]["positive"],m["signal"]["n"]]),
      ("legacy_multi_first_t2_spy",[5,5],[m["first_t2_per_issuer"]["excess_spy"]["positive"],m["first_t2_per_issuer"]["n"]]),
      ("legacy_multi_first_t2_sector",[5,5],[m["first_t2_per_issuer"]["excess_sector"]["positive"],m["first_t2_per_issuer"]["n"]]),
      ("legacy_multi_first_t2_absolute",[4,5],[m["first_t2_per_issuer"]["ret"]["positive"],m["first_t2_per_issuer"]["n"]]),
      ("legacy_multi_positive_date_gaps",[7,7],[m["matched"]["as_of"]["positive_strata"],m["matched"]["as_of"]["strata"]])]
    out["claim_checks"]=[{"id":k,"claimed":claimed,"reproduced":observed,"equal":claimed==observed} for k,claimed,observed in checks]
    out["claim_checks"].append({"id":"legacy_multi_mean_date_gap_pp_rounded", "claimed":4.19,
       "reproduced":round(m["matched"]["as_of"]["stratum_equal_mean_gap"]*100,2),
       "equal":round(m["matched"]["as_of"]["stratum_equal_mean_gap"]*100,2)==4.19})
    out["population_mismatch"]={"source_location":"PR8495 PROPHET_NVDA_PRO_REAUDIT §13.2 and §13.3",
       "reported_first_t2_table_counts":[89,17,5],
       "first_any_tier_then_t2_counts":[sum(v["n"] for k,v in a["first_all_then_t2_leg_count"].items() if float(k)==c) for c in (0,1,2)],
       "actual_first_t2_then_group_counts":[sum(v["n"] for k,v in a["first_t2_leg_count"].items() if float(k)==c) for c in (0,1,2)],
       "interpretation":"The manuscript table uses first ticker observation across all tiers THEN keeps T2; its Fisher denominator uses first T2 per ticker. Treated five coincide, comparator populations differ. Do not combine them.",
       "t1_first_any_then_filter_multi":[a["first_all_then_t1_multileg"]["excess_spy"]["positive"],a["first_all_then_t1_multileg"]["n"]],
       "t1_first_t1_then_filter_multi":[a["first_t1_then_multileg"]["excess_spy"]["positive"],a["first_t1_then_multileg"]["n"]]}
    out["power"]=power_report()
    out["unavailable"]={"h1":"No H1 rows in source dataset.",
        "source_independent_event_labels":"No event-root or claim-lineage fields in grade dataset; legacy legs are not independence-certified.",
        "economic_quality_increment":"No historical audited materiality/expectation/strategic/government/financing labels.",
        "clean_liftoff_failed_breakout":"No full aligned OHLC path and frozen breakout level/sequence in this input.",
        "prospective_validation":"All observed source outcomes are discovery data; no future cohort enrolled."}
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    raw=args.input.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SHA256:
        raise ValueError("Input SHA256 mismatch")
    if hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()!=GIT_BLOB:
        raise ValueError("Input Git blob mismatch")
    if args.output.exists():
        raise ValueError("Output already exists; preserve old output and choose a new path")
    r=analyse(pd.read_parquet(args.input))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(r,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"output":str(args.output),"claims_equal":sum(x["equal"] for x in r["claim_checks"]),
                      "claims_checked":len(r["claim_checks"]),"source_git_blob":GIT_BLOB}))


if __name__=="__main__":
    main()
