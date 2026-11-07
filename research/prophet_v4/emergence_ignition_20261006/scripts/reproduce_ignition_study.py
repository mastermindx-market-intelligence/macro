#!/usr/bin/env python3
"""Offline frozen Prophet ignition diagnostic. Reads Git objects; writes only --out.

This does not fit a trading rule or execute a production module. Legacy flags do
not establish the registered independent/PIT exposure. All outputs are discovery.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats as st

REF = "770918cb266b5d884978e31d61670b4efd789eaf"
BLOB = "b0ee089e86269854b699f4667b47dd10a469374c"
LEDGER = "data/us_board_ledger/retro_grades.parquet"
CUTOFF = "2026-10-06"
HORIZONS = (3, 5, 10, 21)
FLAGS = ["news_burst", "sue_fresh", "smartmoney_add"]
KEY = ["as_of", "lane", "ticker", "horizon"]
GICS = {"Consumer Discretionary": "XLY", "Consumer Staples": "XLP", "Energy": "XLE",
        "Financials": "XLF", "Health Care": "XLV", "Industrials": "XLI",
        "Information Technology": "XLK", "Materials": "XLB", "Real Estate": "XLRE",
        "Communication Services": "XLC", "Utilities": "XLU"}


def clean(x):
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (tuple, list, np.ndarray)):
        return [clean(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        return float(x) if math.isfinite(x) else None
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if x is pd.NA or x is pd.NaT:
        return None
    if isinstance(x, pd.Timestamp):
        return x.isoformat()
    return x


def write_json(path, obj):
    path.write_text(json.dumps(clean(obj), indent=2, allow_nan=False) + "\n")


class GitSource:
    def __init__(self, repo, ref):
        self.repo, self.ref = str(repo), ref
        self.manifest, self.price_cache = {}, {}

    def blob(self, path, required=True):
        p = subprocess.run(["git", "-C", self.repo, "show", self.ref + ":" + path], capture_output=True)
        if p.returncode:
            if required:
                raise RuntimeError("Git object unavailable: " + path)
            return None
        b = p.stdout
        self.manifest[path] = {"git_blob": hashlib.sha1(f"blob {len(b)}\0".encode() + b).hexdigest(),
                               "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}
        return b

    def parquet(self, path, required=True):
        b = self.blob(path, required)
        return pd.read_parquet(io.BytesIO(b)) if b is not None else None

    def price(self, ticker, benchmark=False):
        key = (ticker, benchmark)
        if key in self.price_cache:
            return self.price_cache[key]
        roots = ("yahoo",) if benchmark else ("baskets/ohlcv", "yahoo", "stocks")
        frames = []
        for root in roots:
            path = f"data/{root}/{ticker}.parquet"
            d = self.parquet(path, required=False)
            if d is None:
                continue
            d = d.copy()
            if isinstance(d.columns, pd.MultiIndex):
                if ticker in d.columns.get_level_values(-1):
                    d = d.xs(ticker, level=-1, axis=1)
                else:
                    continue
            d.columns = [str(c).lower().replace(" ", "_") for c in d.columns]
            if not isinstance(d.index, pd.DatetimeIndex):
                dc = next((c for c in ("date", "datetime", "timestamp") if c in d), None)
                if dc is None:
                    continue
                d.index = pd.to_datetime(d[dc])
            d.index = pd.to_datetime(d.index, utc=True).tz_convert(None).normalize()
            d = d[~d.index.duplicated(keep="last")].sort_index()
            d = d.loc[d.index <= pd.Timestamp(CUTOFF)]
            if "close" not in d or d.close.dropna().empty:
                continue
            d = d.loc[d.close.notna() & d.close.gt(0)]
            d.attrs["source_path"] = path
            frames.append(d)
            # First complete adjusted rung is chosen, with no cross-rung splicing.
            if len(d) and d.index.max() >= pd.Timestamp("2026-10-02"):
                break
        result = frames[0] if frames else None
        # A stale first rung must not truncate a newer adjusted alternative.
        if frames:
            result = max(frames, key=lambda f: f.index.max())
        self.price_cache[key] = result
        return result


def wilson(k, n):
    if not n:
        return [None, None]
    z = st.norm.ppf(.975)
    den = 1 + z*z/n
    center = (k/n + z*z/(2*n))/den
    half = z*math.sqrt(k/n*(1-k/n)/n + z*z/(4*n*n))/den
    return [center-half, center+half]


def scalar_stats(values):
    a = pd.to_numeric(values, errors="coerce").dropna().to_numpy(float)
    n, k = len(a), int((a > 0).sum())
    return {"observed": n, "positive": k, "positive_rate": k/n if n else None,
            "wilson95": wilson(k, n), "mean": float(a.mean()) if n else None,
            "median": float(np.median(a)) if n else None,
            "min": float(a.min()) if n else None, "max": float(a.max()) if n else None}


def describe(d, metrics=("ret", "excess_spy", "excess_sector", "mfe", "mae_close_excess_spy", "mae_close_excess_sector")):
    out = {"n": len(d), "tickers": int(d.ticker.nunique()), "dates": int(d.as_of.nunique()),
           "sectors": int(d.sector.nunique()), "entry_states": d.entry_status.fillna("UNRECORDED").value_counts().to_dict()}
    for col in metrics:
        if col in d:
            out[col] = scalar_stats(d[col])
    if "ret" in d:
        a = pd.to_numeric(d.ret, errors="coerce").dropna()
        out["large_loss_descriptive"] = {"observed": len(a), "le_minus_5pct": int(a.le(-.05).sum()),
                                         "le_minus_10pct": int(a.le(-.1).sum())}
    return out


def block_uncertainty(values):
    a = np.asarray(values, dtype=float)
    n = len(a)
    if not n:
        return {"date_blocks": 0, "mean": None}
    mean = float(a.mean())
    rng = np.random.default_rng(20261006)
    boot = a[rng.integers(0, n, (20000, n))].mean(axis=1)
    half = float(st.t.ppf(.975, n-1)*a.std(ddof=1)/np.sqrt(n)) if n>1 else None
    return {"date_blocks": n, "mean": mean, "positive_date_differences": int((a>0).sum()),
            "t95": [mean-half, mean+half] if half is not None else [None, None],
            "bootstrap95": np.quantile(boot, [.025, .975]).tolist(),
            "sign_test_one_sided_exploratory": float(st.binom.sf((a>0).sum()-1, n, .5)),
            "caution": "Few overlapping date blocks; conditional descriptive interval, not post-selection-valid confirmation."}


def matched(treated, controls, keys, metrics, label):
    records = []
    # Scalar grouper for one key avoids pandas-version-specific tuple get_group semantics.
    grouped = controls.groupby(keys[0] if len(keys)==1 else keys, dropna=False)
    for _, row in treated.iterrows():
        key = tuple(row[k] for k in keys)
        if len(keys)==1:
            key = key[0]
        try:
            pool = grouped.get_group(key)
        except KeyError:
            continue
        pool = pool[pool.ticker.ne(row.ticker)]
        for metric in metrics:
            if metric not in pool or pd.isna(row.get(metric)):
                continue
            ys = pd.to_numeric(pool[metric], errors="coerce").dropna()
            if not len(ys):
                continue
            records.append({"comparison": label, "as_of": row.as_of, "ticker": row.ticker,
                            "sector": row.sector, "metric": metric, "treated": row[metric],
                            "control_mean": ys.mean(), "controls": len(ys), "difference": row[metric]-ys.mean()})
    f = pd.DataFrame(records)
    summary = {}
    if len(f):
        for metric, g in f.groupby("metric"):
            bydate = g.groupby("as_of").difference.mean()
            summary[metric] = {"matched_treated": len(g), "issuer_weighted_gap": g.difference.mean(),
                               "date_weighted": block_uncertainty(bydate.values)}
    return summary, records


def control_values(source, ticker, date):
    d = source.price(ticker)
    spy = source.price("SPY", benchmark=True)
    out = {"as_of": str(date), "ticker": ticker, "covariate_basis": "FINAL_VINTAGE_ADJUSTED_DISCOVERY_ONLY"}
    if d is None:
        out["price_control_status"] = "MISSING_ADJUSTED_PRICE"
        return out
    cut = pd.Timestamp(date)
    hist = d.loc[d.index<=cut]
    out["price_source"] = d.attrs["source_path"]
    out["price_control_last_date"] = str(hist.index[-1].date()) if len(hist) else None
    if not len(hist) or hist.index[-1] != cut:
        out["price_control_status"] = "MISSING_DECISION_SESSION"
        return out
    out["price_control_status"] = "OBSERVED"
    out["close_asof_reconstructed"] = hist.close.iloc[-1]
    for h in (5, 21):
        if len(hist)>h:
            out[f"momentum_{h}"] = hist.close.iloc[-1]/hist.close.iloc[-h-1]-1
            if spy is not None:
                b = spy.reindex(hist.index[-h-1:]).close
                if b.notna().all():
                    out[f"rs_spy_{h}"] = out[f"momentum_{h}"]-(b.iloc[-1]/b.iloc[0]-1)
    if len(hist)>=21 and "volume" in hist:
        out["mean_dollar_volume_21"] = (hist.close.tail(21)*hist.volume.tail(21)).mean()
    return out


def outcome_values(source, row, h):
    out = {"as_of": row.as_of, "ticker": row.ticker, "horizon": h,
           "entry_status": row.entry_status, "sector": row.sector, "evidence_n": row.evidence_n,
           "convergence_legacy": row.convergence_legacy, "tier_cascade": row.tier_cascade}
    d = source.price(row.ticker)
    spy = source.price("SPY", benchmark=True)
    if d is None or spy is None:
        out["outcome_status"] = "MISSING_ADJUSTED_PRICE"
        return out
    cut = pd.Timestamp(row.as_of)
    # Use the SPY session calendar; never silently bridge missing issuer bars.
    cal = spy.index[spy.index>cut]
    if len(cal)<=h:
        out["outcome_status"] = "RIGHT_CENSORED_REFERENCE_CALENDAR"
        return out
    window_dates = cal[:h+1]
    window = d.reindex(window_dates)
    if window.close.isna().any():
        out["outcome_status"] = "MISSING_ISSUER_SESSION_OR_TERMINAL_VALUE"
        return out
    out["fill_date"] = str(window_dates[0].date())
    out["horizon_date"] = str(window_dates[-1].date())
    out["price_source"] = d.attrs["source_path"]
    out["price_basis"] = "final_vintage_adjusted"
    out["outcome_status"] = "OBSERVED"
    c = window.close.to_numpy(float)
    path = c/c[0]-1
    out["ret"] = path[-1]
    out["mfe_close"] = max(0, path[1:].max())
    out["mae_close"] = min(0, path[1:].min())
    out["mdd_close"] = min(0, (c/np.maximum.accumulate(c)-1).min())
    out["next_session_close_adjusted"] = c[0]
    bench = spy.reindex(window_dates).close.to_numpy(float)
    bp = bench/bench[0]-1
    out["excess_spy"] = path[-1]-bp[-1]
    out["mae_close_excess_spy"] = min(0, (path-bp).min())
    etf = row.get("sector_etf") or GICS.get(row.sector)
    if isinstance(etf, str):
        e = source.price(etf, benchmark=True)
        if e is not None:
            ew = e.reindex(window_dates)
            if ew.close.notna().all():
                ep = ew.close.to_numpy(float)/ew.close.iloc[0]-1
                out["excess_sector"] = path[-1]-ep[-1]
                out["mae_close_excess_sector"] = min(0, (path-ep).min())
    if all(x in window for x in ("open", "high", "low")) and window[["open","high","low"]].notna().all().all():
        if (window.low.le(window[["open","close"]].min(axis=1)) & window.high.ge(window[["open","close"]].max(axis=1))).all():
            out["mfe_intraday_after_close_fill"] = max(0, window.high.iloc[1:].max()/c[0]-1)
            out["mae_intraday_after_close_fill"] = min(0, window.low.iloc[1:].min()/c[0]-1)
            op = float(window.open.iloc[0])
            out["next_session_open_adjusted"] = op
            out["conditional_next_open_ret_same_endpoint"] = c[-1]/op-1
            out["conditional_open_mae"] = min(0, window.low.min()/op-1)
            out["conditional_open_mfe"] = max(0, window.high.max()/op-1)
            if "open" in spy:
                so = spy.reindex(window_dates).open.iloc[0]
                if pd.notna(so) and so>0:
                    out["conditional_next_open_excess_spy"] = out["conditional_next_open_ret_same_endpoint"]-(bench[-1]/so-1)
    out["executable_trade_status"] = "NOT_ESTABLISHED_NO_PUBLICATION_CLOCK_OR_FILL_RECEIPT"
    return out


def nearest_matches(first, covariates):
    v = first.copy()
    available = [x for x in covariates if x in v and v[x].notna().any()]
    sd = v[available].std().replace(0, np.nan)
    rows=[]
    for _, a in v[v.convergence_legacy.eq(True)].iterrows():
        c = v[v.convergence_legacy.eq(False)&v.as_of.eq(a.as_of)&v.sector.eq(a.sector)]
        used = [x for x in available if pd.notna(a[x]) and pd.notna(sd[x])]
        c = c.dropna(subset=used)
        if not len(c) or not used:
            rows.append({"ticker":a.ticker,"as_of":a.as_of,"status":"NO_COMPLETE_SAME_DATE_SECTOR_CONTROL"})
            continue
        distance = (((c[used]-a[used])/sd[used]).astype(float)**2).mean(axis=1)
        cc = c.assign(match_distance=distance).sort_values(["match_distance","ticker"]).iloc[0]
        rows.append({"ticker":a.ticker,"as_of":a.as_of,"status":"MATCHED","control":cc.ticker,
                     "features":used,"distance":cc.match_distance,"excess_spy_gap":a.excess_spy-cc.excess_spy,
                     "ret_gap":a.ret-cc.ret,"sector_gap":a.excess_sector-cc.excess_sector})
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--ref",default=REF)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--control-keys",type=Path)
    args=p.parse_args()
    if args.ref!=REF:
        p.error("This replication only admits its frozen source ref")
    root=args.out.resolve()
    if root==args.repo.resolve() or args.repo.resolve() in root.parents:
        p.error("Research output must be outside the source checkout")
    root.mkdir(parents=True,exist_ok=True)
    if (root/"IGNITION_RESULTS_2026-10-06.json").exists():
        p.error("Results already exist; preserve prior run and use a new isolated output directory")
    src=GitSource(args.repo,args.ref)
    d=src.parquet(LEDGER)
    assert src.manifest[LEDGER]["git_blob"]==BLOB, "Frozen source mismatch"
    assert not d.duplicated(KEY).any(), "Duplicate economic observations"
    d=d[d.as_of.le(CUTOFF)].copy()
    for f in FLAGS:
        d[f]=d[f].astype("boolean")
    d["evidence_n"]=d[FLAGS].sum(axis=1,min_count=3).astype("Int64")
    d["convergence_legacy"]=(d.evidence_n>=2).astype("boolean")
    d["mfe"]=d.apply(lambda x:x.get(f"fwd_mfe_{int(x.horizon)}"),axis=1)
    v=d[d.rank_by.eq("us_prophet_v3")&d.lane.eq("buy")].copy()
    h5=v[v.horizon.eq(5)].sort_values(["as_of","ticker"])
    t2=h5[h5.tier_cascade.eq("T2")]
    first=t2.drop_duplicates("ticker").copy()
    first_keys=first[["as_of","ticker"]]
    first_all=v.merge(first_keys,on=["as_of","ticker"],validate="many_to_one")
    # The immutable source agrees across horizons; refuse silent exposure/entry drift.
    baseline_fields=["tier_cascade",*FLAGS,"entry_date","entry_status"]
    baseline_consistency={}
    for horizon in (10,21):
        paired=first[["as_of","ticker",*baseline_fields]].merge(
            first_all[first_all.horizon.eq(horizon)][["as_of","ticker",*baseline_fields]],
            on=["as_of","ticker"],suffixes=("_H5","_later"),validate="one_to_one")
        mismatches={k:int((~(paired[k+"_H5"].eq(paired[k+"_later"]) |
                           (paired[k+"_H5"].isna()&paired[k+"_later"].isna()))).sum()) for k in baseline_fields}
        assert not any(mismatches.values()), (horizon,mismatches)
        baseline_consistency[str(horizon)]={"paired":len(paired),"field_mismatches":mismatches}
    # Results selected strictly by the frozen first H5 source observation, not by later maturity.
    output={"status":"HISTORICAL_DISCOVERY_ONLY_ZERO_AUTHORITY","source_ref":REF,"ledger_blob":BLOB,
            "cutoff":CUTOFF,"source_rows":len(d),"source_dates":[d.as_of.min(),d.as_of.max()],
            "strict_primary":{"status":"NOT_ESTIMABLE","proven_eligible_episodes":0,
                              "reason":"No complete joint T2 event identity, decision clock, independent family event lineage and registered ownership-age limit in the diagnostic ledger."},
            "episode_proxy":"First observed v3 buy-lane T2 per ticker at frozen H5 source date; no canonical episode identity inferred.",
            "all_rows":{},"first_issuer":{},"matched":{},"negative_controls":{},"era_summary":{},"concentration":{},"persistence":{},
            "baseline_horizon_consistency":baseline_consistency}
    csv_summary=[]
    for h in (5,10,21):
        for scope,f in [("all_rows",v[v.horizon.eq(h)]),("first_issuer",first_all[first_all.horizon.eq(h)])]:
            for group,mask in [("T2_ge2",f.tier_cascade.eq("T2")&f.convergence_legacy.eq(True)),
                               ("T2_lt2",f.tier_cascade.eq("T2")&f.convergence_legacy.eq(False))]:
                a=f[mask]
                result=describe(a)
                output[scope][f"H{h}_{group}"]=result
                csv_summary.append({"scope":scope,"horizon":h,"group":group,"n":len(a),
                                    "tickers":a.ticker.nunique(),"dates":a.as_of.nunique(),
                                    **{f"{c}_mean":a[c].mean() for c in ["ret","excess_spy","excess_sector"]}})
    output["first_issuer"]["evidence_count"] = first.evidence_n.value_counts(dropna=False).to_dict()
    output["first_issuer"]["cohort_missingness"]={str(h):{"initial":len(first),"mature":int(first_all.horizon.eq(h).sum()),
                                                       "not_in_frozen_horizon_ledger":len(first)-int(first_all.horizon.eq(h).sum())} for h in (5,10,21)}
    matched_rows=[]
    for h in (5,10,21):
        full=v[v.horizon.eq(h)&v.tier_cascade.eq("T2")]
        fixed=first_all[first_all.horizon.eq(h)]
        for name,t,c in [("nightly",full[full.convergence_legacy.eq(True)],full[full.convergence_legacy.eq(False)]),
                          ("first_issuer_both",fixed[fixed.convergence_legacy.eq(True)],fixed[fixed.convergence_legacy.eq(False)]),
                          ("first_issuer_treated_nightly_controls",fixed[fixed.convergence_legacy.eq(True)],full[full.convergence_legacy.eq(False)])]:
            for keys in (["as_of"],["as_of","sector"],["as_of","entry_status"]):
                label=f"H{h}_{name}_{'+'.join(keys)}"
                a,b=matched(t,c,keys,["ret","excess_spy","excess_sector","mfe","mae_close_excess_spy"],label)
                output["matched"][label]=a
                matched_rows.extend(b)
    for era,g in d[d.horizon.eq(5)&d.lane.eq("buy")].groupby("rank_by"):
        output["era_summary"][str(era)]={"rows":len(g),"dates":g.as_of.nunique(),
                                       "missing_flags":{f:int(g[f].isna().sum()) for f in FLAGS},
                                       "legacy_T2_ge2":describe(g[g.tier_cascade.eq("T2")&g.convergence_legacy.eq(True)]),
                                       "price_basis":g.price_basis.fillna("UNRECORDED").value_counts().to_dict()}
    # Fixed negative controls; each deduplicates independently before outcomes are summarized.
    neg_sources={"T1":h5[h5.tier_cascade.eq("T1")],"nonT2_buy":h5[~h5.tier_cascade.eq("T2")],
                 "watch":d[d.rank_by.eq("us_prophet_v3")&d.lane.eq("watch")&d.horizon.eq(5)].sort_values(["as_of","ticker"])}
    for name,f in neg_sources.items():
        f=f.drop_duplicates("ticker")
        for state in (True,False):
            output["negative_controls"][f"{name}_first_ge2_{state}"]=describe(f[f.convergence_legacy.eq(state)])
    rank=h5.copy()
    rank["rank_pct"]=rank.groupby("as_of").composite_z.rank(pct=True,method="average")
    output["negative_controls"]["high_conviction_composite_zero_evidence_first_issuer"]=describe(rank[rank.rank_pct.ge(.9)&rank.evidence_n.eq(0)].drop_duplicates("ticker"))
    output["rank_control_caveat"]="Ledger composite_z is a conviction composite, not the incumbent C1 fusion rank. Actual C1 control is separately reconstructed from prophet.score on raw boards."
    for flag in FLAGS:
        output["negative_controls"][f"T2_first_{flag}_only"]=describe(first[first[flag].eq(True)&first.evidence_n.eq(1)])
        output["negative_controls"][f"T2_first_ge2_without_{flag}"]=describe(first[first.convergence_legacy.eq(True)&first[flag].eq(False)])
    exposed=first[first.convergence_legacy.eq(True)]
    control=first[first.convergence_legacy.eq(False)]
    output["concentration"]["first_exposed_tickers"]=exposed.ticker.tolist()
    output["concentration"]["first_exposed_by_date"]=exposed.as_of.value_counts().to_dict()
    output["concentration"]["first_exposed_by_sector"]=exposed.sector.value_counts().to_dict()
    output["concentration"]["leave_one_ticker_out"]={str(x):describe(exposed[exposed.ticker.ne(x)]) for x in exposed.ticker}
    output["concentration"]["leave_one_sector_out"]={str(x):describe(exposed[exposed.sector.ne(x)]) for x in exposed.sector.unique()}
    output["concentration"]["leave_one_date_out"]={str(x):describe(exposed[exposed.as_of.ne(x)]) for x in exposed.as_of.unique()}
    output["fisher_first_issuer_postselection_only"]={"table":[[int(exposed.excess_spy.gt(0).sum()),int(exposed.excess_spy.le(0).sum())],
                                                               [int(control.excess_spy.gt(0).sum()),int(control.excess_spy.le(0).sum())]]}
    ft=st.fisher_exact(output["fisher_first_issuer_postselection_only"]["table"],alternative="greater")
    output["fisher_first_issuer_postselection_only"].update({"odds_ratio":ft.statistic,"p":ft.pvalue})
    for h in (10,21):
        paired=first_all[first_all.horizon.eq(5)].merge(first_all[first_all.horizon.eq(h)],on=["as_of","ticker"],suffixes=("_5",f"_{h}"),validate="one_to_one")
        for label,mask in [("all",pd.Series(True,index=paired.index)),("legacy_ge2",paired.convergence_legacy_5.eq(True))]:
            g=paired[mask]
            cells={}
            for won in (True,False):
                sub=g[g.excess_spy_5.gt(0).eq(won)]
                cells[f"H5_positive_{won}"]=scalar_stats(sub[f"excess_spy_{h}"])
                cells[f"H5_positive_{won}"]["incremental_H5_to_H"+str(h)+"_absolute"]=scalar_stats((1+sub[f"ret_{h}"])/(1+sub.ret_5)-1)
                cells[f"H5_positive_{won}"]["incremental_H5_to_H"+str(h)+"_SPY_excess"]=scalar_stats(((1+sub[f"ret_{h}"])/(1+sub.ret_5)-1)-((1+sub[f"spy_ret_{h}"])/(1+sub.spy_ret_5)-1))
            output["persistence"][f"{label}_H5_H{h}"]={"paired":len(g),"cells":cells}
    # Price controls on all unique H5 v3 buy keys; also accept sibling study keys.
    keys=h5[["as_of","ticker"]].copy()
    if args.control_keys:
        more=pd.read_csv(args.control_keys,dtype=str)
        keys=pd.concat([keys,more[["as_of","ticker"]]],ignore_index=True).drop_duplicates()
    controls_rows=[control_values(src,row.ticker,row.as_of) for row in keys.itertuples()]
    cov=pd.DataFrame(controls_rows)
    cov.to_csv(root/"price_controls_2026-10-06.csv",index=False)
    first_cov=first.merge(cov,on=["as_of","ticker"],how="left",validate="one_to_one",suffixes=("","_reconstructed"))
    covariates=["alpha","off_high","composite_z","momentum_5","momentum_21","rs_spy_21"]
    output["covariate_balance"]={g:{c:scalar_stats(f[c]) for c in covariates if c in f} for g,f in [("legacy_ge2",first_cov[first_cov.convergence_legacy.eq(True)]),("legacy_lt2",first_cov[first_cov.convergence_legacy.eq(False)])]}
    output["nearest_same_date_sector_control"]=nearest_matches(first_cov,["alpha","off_high","composite_z","momentum_5","momentum_21"])
    output["regression_disposition"]="Multivariable treatment effects not credibly identified with five exposed issuers/four dates; same-date/sector matching and balance shown. 21-session momentum and SPY-relative strength are algebraically collinear under date effects. No fitted score."
    print("Price controls complete",len(cov),"rows",flush=True)
    # Reconstruct independent H3 and missing maturity/risk companions from the same frozen price cut.
    outcomes=pd.DataFrame([outcome_values(src,row,h) for _,row in first.iterrows() for h in HORIZONS])
    outcomes.to_csv(root/"first_t2_reconstructed_outcomes_2026-10-06.csv",index=False)
    output["reconstructed_outcomes"]={}
    reconstructed_metrics=["ret","excess_spy","excess_sector","mfe_close","mae_close","mdd_close",
                           "mfe_intraday_after_close_fill","mae_intraday_after_close_fill","conditional_next_open_ret_same_endpoint","conditional_next_open_excess_spy"]
    for h in HORIZONS:
        for flag in (True,False):
            g=outcomes[outcomes.horizon.eq(h)&outcomes.convergence_legacy.eq(flag)]
            output["reconstructed_outcomes"][f"H{h}_ge2_{flag}"]={"status_counts":g.outcome_status.value_counts().to_dict(),"stats":describe(g,reconstructed_metrics)}
    a=first_all.merge(outcomes,on=["as_of","ticker","horizon"],suffixes=("_ledger","_reconstructed"))
    output["frozen_vs_reconstructed_price_check"]={c:{"paired":int((a[f"{c}_ledger"].notna()&a[f"{c}_reconstructed"].notna()).sum()),
                                                      "max_abs_delta":float((a[f"{c}_ledger"]-a[f"{c}_reconstructed"]).abs().max()),
                                                      "delta_over_1bp":int((a[f"{c}_ledger"]-a[f"{c}_reconstructed"]).abs().gt(.0001).sum())} for c in ["ret","excess_spy","excess_sector"]}
    output["non_estimable"]=["Strict primary independent/PIT-valid T2 ignition exposure and causal effect",
                              "Issuer economic identity beyond ticker; canonical episode resets before full anchor-clock capture",
                              "Actual fill, cost-adjusted profit, publication-to-execution availability for the complete cohort",
                              "Conditional next-open SPY excess: no pinned SPY-open lineage in this bounded source set",
                              "H21/H42/H63 leadership for censored episodes; unseen eligible universe outside preserved boards",
                              "True source/filing-age negative controls when flag-level lineage is absent",
                              "Independent causal RS versus momentum coefficients under same-date controls"]
    # Explicit deterministic checks guard denominator, dedup, return meanings and censoring.
    assert len(t2)==327 and len(first)==143 and len(exposed)==5
    assert exposed.ticker.tolist()==["TSLA","ADM","PRIM","INTC","ISRG"]
    assert int(exposed.ret.gt(0).sum())==4 and int(exposed.excess_spy.gt(0).sum())==5
    assert output["first_issuer"]["evidence_count"]=={0:118,1:20,2:5}
    assert not first_all.duplicated(["as_of","ticker","horizon"]).any()
    assert output["matched"]["H5_first_issuer_both_as_of"]["excess_spy"]["matched_treated"]==5
    pd.DataFrame(csv_summary).to_csv(root/"ignition_summary_2026-10-06.csv",index=False)
    pd.DataFrame(matched_rows).to_csv(root/"matched_control_differences_2026-10-06.csv",index=False)
    first_cov.to_csv(root/"first_t2_issuer_cohort_2026-10-06.csv",index=False)
    exposed.to_csv(root/"five_legacy_exposures_2026-10-06.csv",index=False)
    write_json(root/"IGNITION_RESULTS_2026-10-06.json",output)
    write_json(root/"SOURCE_MANIFEST_2026-10-06.json",{"ref":REF,"objects":src.manifest})
    print(json.dumps(clean({"first_counts":output["first_issuer"]["evidence_count"],"first_primary":output["first_issuer"]["H5_T2_ge2"],
                           "same_date_first":output["matched"].get("H5_first_issuer_both_as_of"),"source_objects":len(src.manifest)}),indent=2),flush=True)


if __name__=="__main__":
    main()
