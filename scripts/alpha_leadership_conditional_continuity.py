"""Research-only Alpha Leadership conditional-continuity experiment.

This module does not feed live scores. It freezes a point-in-time S&P 1500
feature panel, registers every real-market model configuration with the existing
TrialLedger, and only then builds forward labels. Historical sector metadata is
intentionally excluded because the qualified host lacks a PIT taxonomy.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from engine.trial_ledger import TrialLedger
from engine.validation import benjamini_hochberg, ic_summary, rank_ic

FAMILY = "alpha_leadership_conditional_continuity_v2_pit"
MODELS = ("linear", "nonlinear", "additive", "interaction")
FORM = 252
SKIP = 21
HORIZON = 63
MIN_TRAIN_DATES = 60
TEST_BLOCK_DATES = 12
TOP_FRACTION = 0.10
FEATURE_COVERAGE_REFERENCE_FLOOR = 0.70  # shared US cohort-null convention; not alpha calibration


@dataclass(frozen=True)
class InputIdentity:
    path: str
    sha256: str
    bytes: int


def _sha(path: Path) -> InputIdentity:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return InputIdentity(str(path), h.hexdigest(), path.stat().st_size)


def _read_yahoo(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    need = {"close", "close_price", "volume"}
    if not need.issubset(df.columns):
        raise ValueError(f"{path.name}: Yahoo dual-basis schema missing")
    df = df[list(need)].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df[~df.index.duplicated(keep="last")].sort_index()


def load_membership(data_root: Path) -> pd.DataFrame:
    p = data_root / "breadth" / "sp1500_pit_membership.parquet"
    df = pd.read_parquet(p)
    need = {"ticker", "start_date", "end_date", "src"}
    if not need.issubset(df.columns):
        raise ValueError("S&P 1500 PIT membership schema changed")
    df = df[list(need)].copy()
    df["ticker"] = df.ticker.astype(str)
    df["start_date"] = pd.to_datetime(df.start_date).dt.tz_localize(None)
    df["end_date"] = pd.to_datetime(df.end_date).dt.tz_localize(None)
    if (df.end_date.notna() & (df.end_date < df.start_date)).any():
        raise ValueError("Invalid membership interval")
    return df


def load_cik_map(data_root: Path) -> dict[str, str]:
    p = data_root / "edgar" / "ticker_cik_ledger.json"
    obj = json.loads(p.read_text())
    raw = obj.get("tickers") or {}
    return {str(k): str(int(v)) for k, v in raw.items() if v is not None}


def members_asof(membership: pd.DataFrame, date) -> list[str]:
    d = pd.Timestamp(date).tz_localize(None)
    mask = (membership.start_date <= d) & (membership.end_date.isna() | (membership.end_date >= d))
    return sorted(membership.loc[mask, "ticker"].astype(str).unique())


def decision_grid(spy: pd.Series, start="2002-01-01") -> list[pd.Timestamp]:
    idx = pd.DatetimeIndex(spy.dropna().index).sort_values()
    idx = idx[idx >= pd.Timestamp(start)]
    if idx.empty:
        return []
    s = pd.Series(idx, index=idx)
    return list(s.groupby(idx.to_period("M")).max().astype("datetime64[ns]"))


def formation_measure(stock: pd.Series, spy: pd.Series, decision: pd.Timestamp) -> dict | None:
    cal = pd.DatetimeIndex(spy.dropna().index)
    if decision not in cal:
        return None
    pos = cal.get_loc(decision)
    if not isinstance(pos, (int, np.integer)) or pos < FORM:
        return None
    sessions = cal[pos - FORM: pos - SKIP + 1]
    if len(sessions) != FORM - SKIP + 1:
        return None
    p = stock.reindex(sessions).astype(float)
    mkt_p = spy.reindex(sessions).astype(float)
    if p.isna().any() or mkt_p.isna().any() or (p <= 0).any() or (mkt_p <= 0).any():
        return None
    r = p.pct_change(fill_method=None).iloc[1:]
    mr = mkt_p.pct_change(fill_method=None).iloc[1:]
    if len(r) != FORM - SKIP or r.isna().any() or mr.isna().any():
        return None
    momentum = float(p.iloc[-1] / p.iloc[0] - 1.0)
    balance = float(((r > 0).sum() - (r < 0).sum()) / len(r))
    continuity = float(np.sign(momentum) * balance)
    var = float(mr.var(ddof=1))
    if not math.isfinite(var) or var <= 0:
        return None
    beta = float(r.cov(mr) / var)
    resid = r - beta * mr
    return {
        "m": momentum,
        "c": continuity,
        "beta": beta,
        "residual_vol": float(resid.std(ddof=1)),
        "formation_start": sessions[0],
        "formation_end": sessions[-1],
        "formation_returns": len(r),
    }


def _dead_groups(data_root: Path) -> dict[str, pd.DataFrame]:
    p = data_root / "edgar" / "dead_name_prices.parquet"
    if not p.exists():
        return {}
    df = pd.read_parquet(p)
    df["date"] = pd.to_datetime(df.date).dt.tz_localize(None)
    return {str(t): g.sort_values("date").copy() for t, g in df.groupby("ticker")}


def normalized_dead_tail(live: pd.Series, dead: pd.DataFrame, *, min_overlap: int = 5,
                         max_return_error: float = 0.01) -> tuple[pd.Series, dict]:
    """Extend adjusted Yahoo closes only when a dead-vendor seam is empirically anchored.

    A constant scale can align price levels but cannot manufacture missing dividends.
    We therefore require overlapping daily returns to agree before appending. If the
    seam cannot be qualified, the live series is returned unchanged and later labels
    remain unknown instead of guessing a terminal value.
    """
    live = live.dropna().astype(float).sort_index()
    if dead is None or dead.empty or live.empty:
        return live, {"status": "no_tail", "overlap": 0}
    d = pd.Series(dead.close.to_numpy(float), index=pd.to_datetime(dead.date)).sort_index()
    d = d[~d.index.duplicated(keep="last")]
    overlap = live.index.intersection(d.index)
    positive = overlap[(live.reindex(overlap) > 0).to_numpy() & (d.reindex(overlap) > 0).to_numpy()]
    if len(positive) < min_overlap:
        return live, {"status": "unqualified_no_overlap", "overlap": int(len(positive))}
    recent = positive[-min(40, len(positive)):]
    lr = live.reindex(recent).pct_change(fill_method=None).dropna()
    dr = d.reindex(recent).pct_change(fill_method=None).dropna()
    common = lr.index.intersection(dr.index)
    err = float((lr.reindex(common) - dr.reindex(common)).abs().median()) if len(common) else math.inf
    if not math.isfinite(err) or err > max_return_error:
        return live, {"status": "unqualified_return_mismatch", "overlap": int(len(positive)),
                      "median_abs_return_error": err}
    ratios = live.reindex(recent) / d.reindex(recent).replace(0, np.nan)
    scale = float(ratios.dropna().median())
    if not math.isfinite(scale) or scale <= 0:
        return live, {"status": "unqualified_scale", "overlap": int(len(positive))}
    tail = d[d.index > live.index.max()] * scale
    out = pd.concat([live, tail]).sort_index()
    return out, {"status": "qualified_scaled_tail", "overlap": int(len(positive)),
                 "median_abs_return_error": err, "scale": scale, "tail_rows": int(len(tail))}


def _security_rows(data_root: Path, tickers: Iterable[str]) -> dict[str, pd.DataFrame]:
    out = {}
    for t in tickers:
        p = data_root / "yahoo" / f"{t}.parquet"
        if not p.exists():
            continue
        try:
            out[t] = _read_yahoo(p)
        except Exception:
            continue
    return out


def choose_issuer_security(rows: list[dict]) -> list[dict]:
    """One security per issuer/date, selected only by as-of formation liquidity."""
    if not rows:
        return []
    df = pd.DataFrame(rows)
    df = df.sort_values(["issuer", "median_dollar_volume", "security"],
                        ascending=[True, False, True])
    return df.drop_duplicates("issuer", keep="first").to_dict("records")


def build_features(data_root: Path, *, start="2002-01-01") -> tuple[pd.DataFrame, dict]:
    membership = load_membership(data_root)
    cik = load_cik_map(data_root)
    spy_df = _read_yahoo(data_root / "yahoo" / "SPY.parquet")
    spy = spy_df.close
    dates = decision_grid(spy, start)
    all_tickers = sorted(membership.ticker.unique())
    stores = _security_rows(data_root, all_tickers)
    records, coverage = [], []
    for decision in dates:
        members = members_asof(membership, decision)
        candidates = []
        for t in members:
            yf = stores.get(t)
            if yf is None:
                continue
            fm = formation_measure(yf.close, spy, decision)
            if fm is None:
                continue
            cal = spy.index
            pos = cal.get_loc(decision)
            sessions = cal[pos - FORM: pos - SKIP + 1]
            dv = (yf.close_price.reindex(sessions) * yf.volume.reindex(sessions)).dropna()
            median_dv = float(dv.median()) if len(dv) else 0.0
            issuer = f"cik:{cik[t]}" if t in cik else f"ticker:{t}"
            candidates.append({"decision": decision, "issuer": issuer, "security": t,
                               "identity_basis": "current_cik" if t in cik else "ticker_fallback",
                               "median_dollar_volume": median_dv, **fm})
        selected = choose_issuer_security(candidates)
        records.extend(selected)
        coverage.append({"decision": decision, "pit_members": len(members),
                         "feature_candidates": len(candidates), "issuer_rows": len(selected),
                         "ticker_identity_fallback": sum(r["identity_basis"] == "ticker_fallback" for r in selected)})
    frame = pd.DataFrame(records)
    if frame.empty:
        raise ValueError("No qualified feature rows")
    frame = frame.sort_values(["decision", "issuer"]).reset_index(drop=True)
    digest_cols = ["decision", "issuer", "security", "identity_basis", "m", "c", "beta",
                   "residual_vol", "formation_start", "formation_end", "formation_returns"]
    payload = frame[digest_cols].to_json(orient="records", date_format="iso", double_precision=15).encode()
    coverage_frame = pd.DataFrame(coverage)
    coverage_ratio = (coverage_frame["issuer_rows"] / coverage_frame["pit_members"].replace(0, np.nan))
    median_coverage = float(coverage_ratio.median())
    manifest = {
        "feature_sha256": hashlib.sha256(payload).hexdigest(),
        "membership": asdict(_sha(data_root / "breadth" / "sp1500_pit_membership.parquet")),
        "cik_ledger": asdict(_sha(data_root / "edgar" / "ticker_cik_ledger.json")),
        "spy_store": asdict(_sha(data_root / "yahoo" / "SPY.parquet")),
        "rows": len(frame), "dates": int(frame.decision.nunique()),
        "median_feature_coverage": median_coverage,
        "coverage_reference_floor": FEATURE_COVERAGE_REFERENCE_FLOOR,
        "coverage_status": ("below_reference_floor"
                            if median_coverage < FEATURE_COVERAGE_REFERENCE_FLOOR else "at_or_above_reference_floor"),
        "coverage": coverage_frame.to_dict("records"),
    }
    return frame, manifest


def trial_grid(feature_sha: str, source_ref: str) -> list[dict]:
    common = {
        "family": FAMILY, "horizon": HORIZON, "population": "sp1500_pit_union",
        "formation": "P[t-252]..P[t-21]", "strict_path": True,
        "fill_rule": "next_session_close", "exit_rule": "close_at_fill_plus_63_sessions",
        "outcome": "stock_total_return_minus_spy_total_return",
        "top_fraction": TOP_FRACTION, "cohort_weighting": "equal_issuer",
        "feature_sha256": feature_sha, "source_ref": source_ref,
        "controls": ["market_beta", "market_model_residual_vol"],
        "pit_sector_control": False, "liquidity_model_control": False,
        "primary_contrast": "interaction_minus_additive",
        "promotion": "not_implied_by_development_result",
    }
    return [{**common, "model": model} for model in MODELS]


def register_trials(ledger: TrialLedger, grid: list[dict], *, info_cutoff: str) -> dict:
    n = ledger.log_grid(grid, family=FAMILY, info_cutoff=info_cutoff,
                        source="alpha-leadership-research-20260924-sol-001",
                        note="Stage2 PIT 63-session primary; prereg issue #7954 comment 5825728094")
    encoded = json.dumps(grid, sort_keys=True, separators=(",", ":")).encode()
    return {"newly_logged": n, "family": FAMILY, "grid_sha256": hashlib.sha256(encoded).hexdigest(),
            "literal_n": ledger.literal_n(FAMILY), "effective_n": ledger.effective_n(FAMILY)}


def build_outcomes(features: pd.DataFrame, data_root: Path) -> tuple[pd.DataFrame, dict]:
    spy = _read_yahoo(data_root / "yahoo" / "SPY.parquet").close
    cal = pd.DatetimeIndex(spy.dropna().index)
    dead = _dead_groups(data_root)
    stores = _security_rows(data_root, features.security.unique())
    series_cache, seam_cache = {}, {}
    rows = []
    for t, yf in stores.items():
        extended, seam = normalized_dead_tail(yf.close, dead.get(t))
        series_cache[t], seam_cache[t] = extended, seam
    for row in features.itertuples(index=False):
        d = pd.Timestamp(row.decision)
        try:
            pos = cal.get_loc(d)
        except KeyError:
            continue
        fill_pos, exit_pos = pos + 1, pos + 1 + HORIZON
        if exit_pos >= len(cal):
            rows.append({"decision": d, "issuer": row.issuer, "security": row.security,
                         "fill": pd.NaT, "exit": pd.NaT, "gross_return": np.nan,
                         "benchmark_return": np.nan, "status": "pending"})
            continue
        fill, exit_ = cal[fill_pos], cal[exit_pos]
        s = series_cache.get(row.security)
        gross = np.nan if s is None or fill not in s.index or exit_ not in s.index else float(s.loc[exit_] / s.loc[fill] - 1)
        bench = float(spy.loc[exit_] / spy.loc[fill] - 1)
        rows.append({"decision": d, "issuer": row.issuer, "security": row.security,
                     "fill": fill, "exit": exit_, "gross_return": gross,
                     "benchmark_return": bench, "status": "observed" if math.isfinite(gross) else "unknown"})
    out = pd.DataFrame(rows)
    out["active_return"] = out.gross_return - out.benchmark_return
    return out, {"seams": seam_cache, "dead_store": asdict(_sha(data_root / "edgar" / "dead_name_prices.parquet"))}


def _design(df: pd.DataFrame, model: str) -> tuple[np.ndarray, list[str]]:
    cols = {"m": df.m.to_numpy(float), "beta": df.beta.to_numpy(float),
            "residual_vol": df.residual_vol.to_numpy(float)}
    if model in {"nonlinear", "additive", "interaction"}:
        cols.update(abs_m=np.abs(cols["m"]), m_squared=cols["m"] ** 2)
    if model in {"additive", "interaction"}:
        cols["c"] = df.c.to_numpy(float)
    if model == "interaction":
        cols["m_x_c"] = df.m.to_numpy(float) * df.c.to_numpy(float)
    return np.column_stack(list(cols.values())), list(cols)


def _fit(train: pd.DataFrame, model: str) -> dict:
    x, names = _design(train, model)
    weights = (1 / train.groupby("decision").decision.transform("size")).to_numpy(dtype=float, copy=True)
    weights /= weights.sum()
    mu = np.average(x, axis=0, weights=weights)
    sd = np.sqrt(np.average((x - mu) ** 2, axis=0, weights=weights))
    sd = np.where(sd < 1e-12, 1.0, sd)
    xn = np.column_stack([np.ones(len(x)), (x - mu) / sd])
    sw = np.sqrt(weights)
    coef, _, rank, _ = np.linalg.lstsq(xn * sw[:, None], train.active_return.to_numpy(float) * sw, rcond=1e-10)
    if rank < xn.shape[1]:
        raise ValueError(f"Rank-deficient {model} design")
    ix = names.index("m_x_c") if "m_x_c" in names else None
    return {"names": names, "mean": mu, "scale": sd, "coef": coef,
            "interaction_coef": float(coef[ix + 1] / sd[ix]) if ix is not None else None,
            "interaction_coef_standardized": float(coef[ix + 1]) if ix is not None else None}


def _predict(fit: dict, test: pd.DataFrame, model: str) -> np.ndarray:
    x, names = _design(test, model)
    if names != fit["names"]:
        raise ValueError("Model design drift")
    z = (x - fit["mean"]) / fit["scale"]
    return fit["coef"][0] + z @ fit["coef"][1:]


def walk_forward(features: pd.DataFrame, outcomes: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], list[dict]]:
    joined = features.merge(outcomes[["decision", "issuer", "exit", "status", "active_return"]],
                            on=["decision", "issuer"], how="left", validate="one_to_one")
    dates = sorted(features.decision.unique())
    if len(dates) <= MIN_TRAIN_DATES:
        raise ValueError("Insufficient dates for walk-forward")
    outputs = {m: [] for m in MODELS}; receipts = []
    for start in range(MIN_TRAIN_DATES, len(dates), TEST_BLOCK_DATES):
        cutoff = pd.Timestamp(dates[start])
        test_dates = dates[start:start + TEST_BLOCK_DATES]
        train = joined[(joined.decision < cutoff) & (joined.status == "observed")
                       & (joined["exit"] < cutoff) & joined.active_return.notna()].copy()
        if train.decision.nunique() < MIN_TRAIN_DATES - 6:
            continue
        test = features[features.decision.isin(test_dates)].copy()
        for model in MODELS:
            fit = _fit(train, model)
            pred = test[["decision", "issuer", "security"]].copy()
            pred["prediction"] = _predict(fit, test, model)
            outputs[model].append(pred)
            receipts.append({"cutoff": str(cutoff.date()), "model": model,
                             "train_dates": int(train.decision.nunique()), "train_rows": len(train),
                             "test_dates": len(test_dates), "test_rows": len(test),
                             "interaction_coef": fit["interaction_coef"]})
    return {m: pd.concat(v, ignore_index=True) if v else pd.DataFrame() for m, v in outputs.items()}, receipts


def evaluate(features: pd.DataFrame, outcomes: pd.DataFrame, predictions: dict[str, pd.DataFrame]) -> dict:
    result = {"models": {}, "primary_contrast": {}}
    per_model_dates = {}
    for model, pred in predictions.items():
        if pred.empty:
            continue
        pred = pred.sort_values(["decision", "prediction", "issuer"], ascending=[True, False, True])
        pred["selected"] = False
        for _, ids in pred.groupby("decision").groups.items():
            n = max(1, math.ceil(len(ids) * TOP_FRACTION))
            pred.loc[list(ids)[:n], "selected"] = True
        joined = pred.merge(outcomes, on=["decision", "issuer", "security"], how="left", validate="one_to_one")
        date_rows = []
        for d, g in joined.groupby("decision"):
            known = g[(g.status == "observed") & g.active_return.notna()]
            ic = rank_ic(known.set_index("issuer").prediction, known.set_index("issuer").active_return) if len(known) >= 3 else None
            top = g[g.selected]
            complete = len(top) > 0 and top.status.eq("observed").all() and top.active_return.notna().all()
            date_rows.append({"decision": d, "rank_ic": float(ic) if ic is not None and np.isfinite(ic) else np.nan,
                              "n_predictions": len(g), "n_labels": len(known), "label_coverage": len(known) / len(g),
                              "n_top": len(top), "n_top_missing": int((top.status != "observed").sum()),
                              "top_active_return": float(top.active_return.mean()) if complete else np.nan,
                              "top_status": "complete" if complete else "unresolved"})
        dr = pd.DataFrame(date_rows)
        per_model_dates[model] = dr
        summary = ic_summary(dr.rank_ic.dropna(), periods_per_year=12)
        result["models"][model] = {"ic_summary": summary, "mean_top_active_complete": float(dr.top_active_return.mean()),
                                   "complete_top_dates": int(dr.top_active_return.notna().sum()),
                                   "prediction_dates": len(dr), "mean_label_coverage": float(dr.label_coverage.mean())}
    if "interaction" in per_model_dates and "additive" in per_model_dates:
        a = per_model_dates["interaction"][["decision", "rank_ic"]].merge(
            per_model_dates["additive"][["decision", "rank_ic"]], on="decision", suffixes=("_int", "_add"))
        delta = (a.rank_ic_int - a.rank_ic_add).dropna()
        result["primary_contrast"] = {"interaction_minus_additive": ic_summary(delta, periods_per_year=12),
                                      "mean_delta": float(delta.mean()) if len(delta) else None, "n_dates": len(delta)}
    pvals = {m: v["ic_summary"].get("p_hac") for m, v in result["models"].items()
             if v["ic_summary"].get("p_hac") is not None}
    if pvals:
        result["bh_fdr_10pct"] = benjamini_hochberg(pvals, alpha=0.10)
    return result


def run(data_root: Path, output: Path, source_ref: str, *,
        allow_incomplete_development_panel: bool = False) -> dict:
    features, feature_manifest = build_features(data_root)
    if (feature_manifest["median_feature_coverage"] < FEATURE_COVERAGE_REFERENCE_FLOOR
            and not allow_incomplete_development_panel):
        raise RuntimeError(
            "Historical feature support is below the 70% cohort-null reference floor: "
            f"{feature_manifest['median_feature_coverage']:.1%}. "
            "No TrialLedger row or forward outcome was created. Repair the PIT price panel, "
            "or pass allow_incomplete_development_panel=True only for explicitly labelled "
            "development diagnostics."
        )
    grid = trial_grid(feature_manifest["feature_sha256"], source_ref)
    ledger = TrialLedger(family=FAMILY)
    registration = register_trials(ledger, grid, info_cutoff=pd.Timestamp.now(tz="UTC").isoformat())
    outcomes, outcome_manifest = build_outcomes(features, data_root)
    predictions, receipts = walk_forward(features, outcomes)
    evaluation = evaluate(features, outcomes, predictions)
    result = {"schema": "alpha_leadership_conditional_continuity_stage2.v1",
              "source_ref": source_ref, "feature_manifest": feature_manifest,
              "trial_registration": registration, "outcome_manifest": outcome_manifest,
              "evaluation": evaluation, "fit_receipts": receipts,
              "limitations": ["development sample, not pristine holdout",
                              "historical PIT sector taxonomy unavailable; omitted",
                              "CIK issuer identity is current/accreting, not historical PIT",
                              "dead-name tails graded only when overlap return seam qualifies",
                              "next-close convention because qualified store has no opens",
                              "no live ranking or promotion authority"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, default=str))
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=Path("reports/alpha-leadership-stage2.json"))
    ap.add_argument("--source-ref", required=True)
    ap.add_argument("--allow-incomplete-development-panel", action="store_true",
                    help="explicitly permit a coverage-failed development diagnostic; never promotion evidence")
    args = ap.parse_args()
    result = run(args.data_root, args.output, args.source_ref,
                 allow_incomplete_development_panel=args.allow_incomplete_development_panel)
    print(json.dumps({"feature_rows": result["feature_manifest"]["rows"],
                      "feature_dates": result["feature_manifest"]["dates"],
                      "registration": result["trial_registration"],
                      "evaluation": result["evaluation"]}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
