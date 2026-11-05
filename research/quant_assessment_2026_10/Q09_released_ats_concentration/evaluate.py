from __future__ import annotations

"""Q09 evaluation — research only, read-only on licensed local data.

Refuses to run unless sha256(PREREG.md) equals the hash in FREEZE.log and every
input file matches the PREREG §7 sha256. Appends each run to RUNS.log.
Usage: python3.12 evaluate.py [--data-root <dir>]
"""

import hashlib
import json
import math
import re
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from engine import offexchange_venue_concentration as voc  # noqa: E402

PREREG = HERE / "PREREG.md"
FREEZE = HERE / "FREEZE.log"
RUNS = HERE / "RUNS.log"
RESULTS = HERE / "results.json"
BASELINE_OUT = HERE / "baseline_incumbent_venue_table.json"
AMENDMENT = HERE / "PREREG_AMENDMENT.md"
AMENDMENT_LOG = HERE / "AMENDMENT.log"
DEFAULT_DATA = Path("/Users/chriswong/Documents/Cluade/macro-main/data")

# Per-run attestation state, filled by main() and read by _log (PREREG_AMENDMENT A5).
RUN_STATE: dict = {"data": {}, "outputs_written": []}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_freeze() -> dict:
    m = re.search(r"sha256=([0-9a-f]{64})", FREEZE.read_text())
    if not m:
        raise SystemExit("FREEZE.log has no sha256")
    actual = sha256_file(PREREG)
    if actual != m.group(1):
        raise SystemExit(f"REFUSING: PREREG.md sha256 {actual} != frozen {m.group(1)}")
    block = re.search(r"```json\n(.*?)\n```", PREREG.read_text(), re.S)
    am = re.search(r"sha256=([0-9a-f]{64})", AMENDMENT_LOG.read_text()) if AMENDMENT_LOG.exists() else None
    if AMENDMENT.exists() and (am is None or sha256_file(AMENDMENT) != am.group(1)):
        raise SystemExit("REFUSING: PREREG_AMENDMENT.md sha256 does not match AMENDMENT.log")
    return json.loads(block.group(1))


def write_output(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, default=str) + "\n")
    RUN_STATE["outputs_written"].append(path)


def tier_gated_volumes(df: pd.DataFrame, key: str, tiers: list[str], available_at: str,
                       query_at: str) -> dict:
    """T1+T2 venue volumes through the coverage gate (PREREG_AMENDMENT A2).

    A week file is committed whole, so each tier present carries the file's
    store-first-seen upper bound. combine_tier_volumes refuses a partial state.
    """
    present = [t for t in tiers if (df["tier"] == t).any()]
    cov = voc.coverage_snapshot({t: available_at for t in present}, query_at, required=tiers)
    per_tier = {t: df[df["tier"] == t].groupby(key)["shares"].sum().to_dict() for t in present}
    comb = voc.combine_tier_volumes(per_tier, cov)
    total = float(df["shares"].sum())
    kept = float(df[df["tier"].isin(comb["tiers"])]["shares"].sum())
    comb["reported_total_in_tiers"] = kept
    comb["excluded_other_tier_fraction"] = (1.0 - kept / total) if total else None
    comb["coverage_label"] = cov["label"]
    comb["as_of_store_upper_bound"] = cov["as_of"]
    return comb


# ---------------- incumbent baseline (verbatim logic, scripts/build_darkpool_desk.py) --

def incumbent_venue_table(latest: pd.DataFrame, prior: pd.DataFrame | None) -> dict:
    valid = latest[latest["mpid"].str.len() > 0]
    agg = (valid.groupby(["mpid", "venue_name"])
           .agg(total_shares=("shares", "sum"), total_trades=("trades", "sum"),
                n_symbols=("ticker", "nunique")).reset_index())
    tot = float(agg["total_shares"].sum())
    agg["share_of_total_pct"] = (agg["total_shares"] / tot * 100).round(2) if tot > 0 else None
    if prior is not None and not prior.empty:
        pv = prior[prior["mpid"].str.len() > 0]
        pa = pv.groupby("mpid").agg(prior_shares=("shares", "sum")).reset_index()
        pt = float(pa["prior_shares"].sum())
        pa["prior_pct"] = (pa["prior_shares"] / pt * 100).round(2) if pt > 0 else None
        mg = agg.merge(pa[["mpid", "prior_pct"]], on="mpid", how="left")
        mg["wow_pp"] = (mg["share_of_total_pct"] - mg["prior_pct"]).round(2)
        mg["wow_is_new"] = mg["prior_pct"].isna()
    else:
        mg = agg.copy()
        mg["wow_pp"] = None
        mg["wow_is_new"] = False
    mg = mg.sort_values("total_shares", ascending=False)
    venues = mg.head(20).to_dict("records")
    for v in venues:
        for k, val in list(v.items()):
            if isinstance(val, (np.integer,)):
                v[k] = int(val)
            elif isinstance(val, (np.floating, float)):
                v[k] = None if math.isnan(float(val)) else float(val)
            elif isinstance(val, (np.bool_,)):
                v[k] = bool(val)
    return {"week_start": str(pd.to_datetime(latest["week_start"].iloc[0]).date()),
            "n_symbols_total": int(valid["ticker"].nunique()), "venues": venues}


# ---------------- per-symbol HHI panel ----------------------------------------

def symbol_week_hhi(df: pd.DataFrame, tiers: list[str], min_shares: float) -> tuple[pd.Series, dict]:
    d = df[df["tier"].isin(tiers)]
    tiers_per = d.groupby("ticker")["tier"].nunique()
    ambiguous = set(tiers_per[tiers_per > 1].index)
    d = d[~d["ticker"].isin(ambiguous)]
    g = d.groupby(["ticker", "mpid"])["shares"].sum()
    tot = g.groupby(level=0).sum()
    sh = g / tot.reindex(g.index.get_level_values(0)).to_numpy()
    h = (sh * sh).groupby(level=0).sum()
    keep = tot[tot >= min_shares].index
    return h.reindex(keep), {"n_tickers_rows": int(tot.size), "n_tier_ambiguous_dropped": len(ambiguous),
                             "n_eligible": int(len(keep))}


def mse_by_week(panel: dict[str, pd.Series], weeks: list[str], pred: pd.Series) -> list[float]:
    out = []
    for w in weeks:
        y = panel[w]
        common = y.index.intersection(pred.index)
        out.append(float(((y[common] - pred[common]) ** 2).mean()) if len(common) else float("nan"))
    return out


def fit_candidate(panel: dict[str, pd.Series], weeks: list[str], min_weeks: int) -> tuple[pd.Series, float, pd.Series]:
    wide = pd.DataFrame({w: panel[w] for w in weeks})
    cnt = wide.notna().sum(axis=1)
    cohort = cnt[cnt >= min_weeks].index
    wide = wide.loc[cohort]
    sym_mean = wide.mean(axis=1)
    pooled = float(sym_mean.mean())
    last = wide.apply(lambda r: r.dropna().iloc[-1], axis=1)
    return sym_mean, pooled, last


def main(argv: list[str]) -> int:
    pre = check_freeze()
    p = pre["params"]
    data = DEFAULT_DATA
    if "--data-root" in argv:
        data = Path(argv[argv.index("--data-root") + 1])
    input_hashes = {}
    for rel, want in pre["files"].items():
        got = sha256_file(data / rel)
        RUN_STATE["data"][rel] = got
        if got != want:
            raise SystemExit(f"REFUSING: input {rel} sha256 {got} != prereg {want}")
        input_hashes[rel] = got

    ats_files = sorted(r for r in pre["files"] if r.startswith("finra_ats/"))
    weeks = [Path(r).stem for r in ats_files]
    frames = {w: pd.read_parquet(data / f"finra_ats/{w}.parquet") for w in weeks}

    # ---- release identity qualification (req1) --------------------------
    sfs = pre["store_first_seen_upper_bound"]
    recs = []
    for w in weeks:
        t = sfs["bulk_commit_time"] if w in sfs["bulk_weeks"] else sfs["per_week"].get(w, [None, None])[1]
        recs.append({"week": w, "store_first_seen_at": None if w in sfs["bulk_weeks"] else t,
                     "publisher_available_at": None, "n_vintages": sfs["vintages_per_week"]})
    qual = voc.qualify_release_identity(recs)

    # ---- availability-respecting split ----------------------------------
    train, hold = voc.chronological_split(weeks, p["n_train"])
    origin = sfs["bulk_commit_time"]
    hold_times = [sfs["per_week"][w][1] for w in hold]
    train_times = [origin if w in sfs["bulk_weeks"] else sfs["per_week"].get(w, [None, None])[1] for w in train]
    split_respects_clock = voc.split_respects_clock(train_times, hold_times, origin)
    try:
        voc.require_split_respects_clock(train_times, hold_times, origin)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    # ---- panel ----------------------------------------------------------
    panel, support = {}, {}
    for w in weeks:
        panel[w], support[w] = symbol_week_hhi(frames[w], p["tiers"], p["min_week_shares"])

    # ---- lambda selection inside training only ---------------------------
    inner_fit, inner_val = train[: p["inner_fit_weeks"]], train[p["inner_fit_weeks"]:]
    sm_i, pooled_i, _ = fit_candidate(panel, inner_fit, p["inner_min_weeks"])
    lam_scores = {}
    for lam in p["lambda_grid"]:
        pred = pd.Series(voc.shrunk_mean(sm_i.to_numpy(), pooled_i, lam), index=sm_i.index)
        lam_scores[lam] = float(np.nanmean(mse_by_week(panel, inner_val, pred)))
    best = min(lam_scores.items(), key=lambda kv: (kv[1], -kv[0]))[0]

    # ---- refit on full training; ONE holdout comparison ------------------
    sm, pooled, last = fit_candidate(panel, train, p["min_train_weeks"])
    pred_c = pd.Series(voc.shrunk_mean(sm.to_numpy(), pooled, best), index=sm.index)
    pred_b = last
    pred_p = pd.Series(pooled, index=sm.index)
    lb = np.array(mse_by_week(panel, hold, pred_b))
    lc = np.array(mse_by_week(panel, hold, pred_c))
    lp = np.array(mse_by_week(panel, hold, pred_p))
    n_eval = [int(len(panel[w].index.intersection(sm.index))) for w in hold]
    d = lb - lc
    R = float(d.mean() / lb.mean())

    boot = voc.moving_block_bootstrap_ratio(d, lb, p["block_len"], p["n_boot"], p["seed"])
    n, b, k = boot["n_units"], boot["block_len"], boot["n_blocks_effective"]
    ci = (boot["ci_lo"], boot["ci_hi"])
    sub = "KEEP" if (R >= p["effect_bar"] and ci[0] > 0) else "REJECT"
    overall = ("INSUFFICIENT_DATA" if (qual["n_with_publisher_release_identity"] == 0
                                      or qual["n_with_multiple_vintages"] == 0) else sub)

    # ---- baseline reproduction + descriptive (non-trial) -----------------
    latest, prior = frames[weeks[-1]].copy(), frames[weeks[-2]].copy()
    for f in (latest, prior):
        f["week_start"] = pd.to_datetime(f["week_start"])
    base = incumbent_venue_table(latest, prior)
    nonats = pd.read_parquet(data / f"finra_otc_nonats/{weeks[-1]}.parquet")
    nonats_prior = pd.read_parquet(data / f"finra_otc_nonats/{weeks[-2]}.parquet")
    na_total = float(nonats["shares"].sum())
    na_kept = float(nonats[nonats["mpid"].str.len() > 0]["shares"].sum())

    # Descriptive universe = T1+T2 through the coverage gate (PREREG_AMENDMENT A2).
    def _avail(w: str) -> str:
        return origin if w in sfs["bulk_weeks"] else sfs["per_week"][w][1]
    q_at = _avail(weeks[-1])
    tiers = list(p["tiers"])
    tlabel = "+".join(tiers)
    ats_g = tier_gated_volumes(latest, "mpid", tiers, _avail(weeks[-1]), q_at)
    ats_pg = tier_gated_volumes(prior, "mpid", tiers, _avail(weeks[-2]), q_at)
    na_g = tier_gated_volumes(nonats, "venue_name", tiers, _avail(weeks[-1]), q_at)
    na_pg = tier_gated_volumes(nonats_prior, "venue_name", tiers, _avail(weeks[-2]), q_at)
    ats_vol, ats_prev = ats_g["volumes"], ats_pg["volumes"]
    ats_sh = voc.venue_shares(ats_vol, reported_total=ats_g["reported_total_in_tiers"])
    ats_b = voc.hhi_bounds(ats_sh)
    na_vol, na_prev = na_g["volumes"], na_pg["volumes"]
    na_sh = voc.venue_shares(na_vol, reported_total=na_g["reported_total_in_tiers"])
    na_sep = voc.hhi_bounds(na_sh, unknown_may_overlap_known=False)
    na_ovl = voc.hhi_bounds(na_sh, unknown_may_overlap_known=True)
    known = lambda dct: {k: v for k, v in dct.items() if not voc.is_unknown_venue(k)}  # noqa: E731
    descriptive = {
        "universe": f"tiers {tlabel} only (PREREG section 3); OTCE excluded as a different market",
        "coverage": {"ats_latest": ats_g["coverage_label"], "ats_prior": ats_pg["coverage_label"],
                     "nonats_latest": na_g["coverage_label"], "nonats_prior": na_pg["coverage_label"],
                     "query_at_store_upper_bound": q_at},
        "ats_excluded_otce_fraction_latest": ats_g["excluded_other_tier_fraction"],
        "nonats_excluded_otce_fraction_latest": na_g["excluded_other_tier_fraction"],
        "ats_latest": voc.describe_concentration(
            f"ATS venues (mpid), tiers {tlabel}, week file {weeks[-1]}", ats_b, len(ats_sh["shares"])),
        "ats_effective_venues": voc.effective_venue_count(list(ats_sh["shares"].values())),
        "ats_decomposition_vs_prior": voc.decompose_hhi_change(ats_prev, ats_vol),
        "nonats_latest_separate_bound": voc.describe_concentration(
            f"non-ATS firms (venue_name), tiers {tlabel}, week file {weeks[-1]}", na_sep, len(na_sh["shares"])),
        "nonats_overlap_upper": na_ovl["upper"],
        "nonats_unknown_share_de_minimis": na_sh["unknown_share"],
        "nonats_decomposition_vs_prior_known_only": voc.decompose_hhi_change(known(na_prev), known(na_vol)),
        "incumbent_mpid_filter_on_nonats_dropped_fraction_all_tiers": (1.0 - na_kept / na_total) if na_total else None,
        "incumbent_ats_empty_mpid_dropped_fraction_latest_all_tiers": float(
            1.0 - latest[latest["mpid"].str.len() > 0]["shares"].sum() / latest["shares"].sum()),
    }

    as_of = max([origin] + hold_times)
    res = {
        "brief": "Q09", "research_only": True, "as_of_store_upper_bound": as_of,
        "as_of_note": "store-first-seen upper bound from git; not a FINRA release time",
        "release_identity": qual,
        "split": {"train_weeks": train, "holdout_weeks": hold, "forecast_origin_store_clock": origin,
                  "split_respects_store_clock": split_respects_clock},
        "support": support,
        "lambda_inner_mse": {str(k): v for k, v in lam_scores.items()}, "lambda_chosen": best,
        "cohort_size": int(len(sm)), "pooled_train_hhi": pooled,
        "holdout": {"weeks": hold, "n_eval_symbols": n_eval,
                    "mse_baseline_latest_snapshot": lb.tolist(), "mse_candidate_shrunk": lc.tolist(),
                    "mse_pooled_descriptive": lp.tolist()},
        "R_relative_mse_reduction": R, "R_ci95_block_bootstrap": list(ci),
        "honest_n_weeks": n, "n_blocks_effective": k, "block_len": b, "n_boot": p["n_boot"],
        "subresult_descriptive_stability": sub, "overall_verdict": overall,
        "missing_input": ("FINRA weekly-summary initial-publication/update metadata per (week, tier) "
                          "and retained multi-vintage snapshots") if overall == "INSUFFICIENT_DATA" else None,
        "descriptive": descriptive,
        "baseline_reproduction": {"file": BASELINE_OUT.name, "week_start": base["week_start"],
                                  "n_venues": len(base["venues"]),
                                  "note": "incumbent logic reproduced verbatim over all tiers"},
        "bootstrap_caveat": (f"{n} holdout weeks, block {b}: ~{k} effective blocks; the percentile CI "
                             "is coarse and its coverage is not reliable"),
        "amendment": {"file": AMENDMENT.name, "sha256": sha256_file(AMENDMENT) if AMENDMENT.exists() else None,
                      "post_hoc": True},
    }
    # Guard over EVERY emitted string before anything is written (PREREG_AMENDMENT A4).
    voc.assert_no_forbidden_interpretation(res)
    voc.assert_no_forbidden_interpretation(base)
    write_output(BASELINE_OUT, base)
    write_output(RESULTS, res)
    return 0


def _log(cmd: str, rc: int, extra: str = "") -> None:
    ins = {}
    try:
        ins = {"PREREG.md": sha256_file(PREREG), "evaluate.py": sha256_file(Path(__file__)),
               "engine/offexchange_venue_concentration.py": sha256_file(
                   REPO / "engine" / "offexchange_venue_concentration.py"),
               "data_recomputed": dict(RUN_STATE["data"])}
        if AMENDMENT.exists():
            ins["PREREG_AMENDMENT.md"] = sha256_file(AMENDMENT)
    except Exception:  # noqa: BLE001
        pass
    # Outputs are attested only for a clean run, and only files THIS run wrote.
    outs = ({p.name: sha256_file(p) for p in RUN_STATE["outputs_written"] if p.exists()}
            if rc == 0 else {})
    with open(RUNS, "a") as f:
        f.write(json.dumps({"cmd": cmd, "exit_code": rc, "inputs": ins, "outputs": outs,
                            "note": extra}, sort_keys=True) + "\n")


if __name__ == "__main__":
    cmd = " ".join([sys.executable] + sys.argv)
    try:
        rc = main(sys.argv[1:])
        _log(cmd, rc)
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 2
        _log(cmd, rc, str(e))
        raise
    except Exception as e:  # noqa: BLE001
        _log(cmd, 1, "".join(traceback.format_exception_only(type(e), e)).strip())
        raise
    sys.exit(rc)
