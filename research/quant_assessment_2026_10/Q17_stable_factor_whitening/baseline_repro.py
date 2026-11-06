from __future__ import annotations

"""Q17 baseline reproduction (pre-registration step; reads NO evaluation outcome).

1. Runs the real incumbent ``engine.factor_orthogonal.orthogonalize`` on synthetic
   collinear / partially-missing / thin controls and checks that the challenger
   module's ``incumbent_reference_transform`` reproduces it to 1e-10.
2. Builds the incumbent point-in-time cross-sections ``compute_factors(asof=d,
   universe="broad")`` on every month-end of the retained close panel and records
   SUPPORT ONLY (rows, per-leg coverage, complete-case rows, whether the incumbent
   would silently fall back) plus runtime.  No whitening error, drift, instability
   or return outcome is computed here.
3. Checks the read-only data inputs are byte-identical before/after and that no file
   appeared in the watched data directories.  Appends one record to RUNS.log.
"""

import contextlib
import io
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import q17_env as env  # noqa: E402

env.install_config_stub()

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

OUT = env.HERE / "baseline_support.json"
LEGS = ["value", "profitability", "quality", "investment", "payout", "low_vol",
        "low_beta", "short_interest", "accruals", "sue"]


def synthetic_controls(fo, fsw) -> dict:
    rng = np.random.default_rng(7)
    n = 400
    lat = rng.normal(size=n)
    a = lat + 0.5 * rng.normal(size=n)
    frames = {
        "well_conditioned": pd.DataFrame({"a": a, "b": lat + 0.6 * rng.normal(size=n),
                                          "c": lat + 0.8 * rng.normal(size=n),
                                          "d": rng.normal(size=n)}),
        "near_duplicate": pd.DataFrame({"a": a, "b": a + 1e-4 * rng.normal(size=n),
                                        "c": lat + 0.8 * rng.normal(size=n),
                                        "d": rng.normal(size=n)}),
    }
    part = frames["well_conditioned"].copy()
    part.iloc[::7, 1] = np.nan
    part.iloc[::11, [0, 2]] = np.nan
    part.iloc[5, :] = np.nan
    frames["partial_missing"] = part
    frames["thin"] = frames["well_conditioned"].iloc[:10].copy()
    out = {}
    for name, F in frames.items():
        inc = fo.orthogonalize(F)
        ref = fsw.incumbent_reference_transform(F)
        diff = float(np.nanmax(np.abs(inc.to_numpy() - ref.to_numpy())))
        same_nan = bool((inc.isna().to_numpy() == ref.isna().to_numpy()).all())
        partial_rows = int((F.notna().sum(axis=1).between(1, F.shape[1] - 1)).sum())
        partial_rows_emitted_complete = int(
            (F.notna().sum(axis=1).between(1, F.shape[1] - 1) & inc.notna().all(axis=1)).sum())
        out[name] = {"max_abs_diff_vs_challenger_restatement": diff, "nan_pattern_equal": same_nan,
                     "fallback_returned_input": bool(inc.equals(F)),
                     "partial_rows": partial_rows,
                     "partial_rows_emitted_complete_by_incumbent": partial_rows_emitted_complete}
        if diff > 1e-10 or not same_nan:
            raise AssertionError(f"incumbent restatement mismatch on {name}: {diff}")
    return out


def month_ends(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    s = pd.Series(index, index=index)
    return list(s.groupby([index.year, index.month]).max())


def table_frame(res) -> "pd.DataFrame | None":
    if not res or not isinstance(res.get("table"), list) or not res["table"]:
        return None
    return pd.DataFrame(res["table"]).set_index("ticker")


def patch_incumbent(ef):
    """Memoise the close panel and skip the two display-only side reads (insider
    leaderboard, IC scorecard badges) that do not touch the factor table."""
    closes = ef._closes("broad")
    memo = {"broad": closes}
    saved = (ef._closes, ef._insider_block, ef._load_ic_scorecard)
    orig = saved[0]
    ef._closes = lambda universe="broad": memo[universe] if universe in memo else orig(universe)
    ef._insider_block = lambda *a, **k: None
    ef._load_ic_scorecard = lambda: {}
    return closes, saved


def unpatch_incumbent(ef, saved) -> None:
    ef._closes, ef._insider_block, ef._load_ic_scorecard = saved


def real_support(ef, fo) -> dict:
    closes, saved = patch_incumbent(ef)
    try:
        mes = month_ends(pd.DatetimeIndex(closes.index))
        tip = closes.index.max()
        # drop the in-progress final month (its last bar is not a month end)
        if mes and mes[-1] == tip and (tip + pd.Timedelta(days=1)).month == tip.month \
                and (tip + pd.offsets.BDay(1)).month == tip.month:
            mes = mes[:-1]
        rows = []
        for d in mes:
            t0 = time.perf_counter()
            res = ef.compute_factors(asof=d.date(), universe="broad")
            dt = time.perf_counter() - t0
            if res is None:
                rows.append({"asof": str(d.date()), "status": "none", "seconds": round(dt, 2)})
                continue
            tab = table_frame(res)
            if tab is None:
                rows.append({"asof": str(d.date()), "status": "no_table", "seconds": round(dt, 2)})
                continue
            legs = [c for c in LEGS if c in tab.columns]
            F = tab[legs].astype(float)
            cov = {c: round(float(F[c].notna().mean()), 4) for c in legs}
            leg6 = [c for c in legs if cov[c] >= 0.5]
            sub = F[leg6]
            complete = int(sub.dropna().shape[0])
            need = max(30, 3 * len(leg6))
            rows.append({"asof": str(d.date()), "status": "ok", "seconds": round(dt, 2),
                         "n_rows": int(len(F)), "legs_present": legs, "coverage": cov,
                         "legs_cov_ge_50pct": leg6, "complete_rows_on_those_legs": complete,
                         "partial_rows_on_those_legs": int(
                             sub.notna().sum(axis=1).between(1, len(leg6) - 1).sum()),
                         "incumbent_would_fallback": bool(complete < need or len(leg6) < 2)})
        # one incumbent call on the last available cross-section: shape/runtime only
        last_ok = [r for r in rows if r.get("status") == "ok"]
        inc_call = None
        if last_ok:
            d = pd.Timestamp(last_ok[-1]["asof"])
            tab = table_frame(ef.compute_factors(asof=d.date(), universe="broad"))
            sub = tab[last_ok[-1]["legs_cov_ge_50pct"]].astype(float)
            t0 = time.perf_counter()
            orth = fo.orthogonalize(sub)
            inc_call = {"asof": str(d.date()), "shape": list(orth.shape),
                        "returned_input_unchanged": bool(orth.equals(sub)),
                        "seconds": round(time.perf_counter() - t0, 4)}
        return {"close_panel_first": str(closes.index.min().date()),
                "close_panel_tip": str(tip.date()), "close_panel_columns": int(closes.shape[1]),
                "month_ends": len(mes), "per_month": rows, "incumbent_call": inc_call}
    finally:
        unpatch_incumbent(ef, saved)


def main() -> int:
    before = env.input_hashes()
    listing_before = env.dir_listing()
    import engine.factor_orthogonal as fo  # noqa: PLC0415
    import engine.factor_stable_whitening as fsw  # noqa: PLC0415
    import engine.equity_factors as ef  # noqa: PLC0415

    t0 = time.perf_counter()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        syn = synthetic_controls(fo, fsw)
        real = real_support(ef, fo)
    after = env.input_hashes()
    listing_after = env.dir_listing()
    if before != after:
        raise RuntimeError("input bytes changed during the run")
    if listing_before != listing_after:
        raise RuntimeError("watched data directory listing changed during the run")
    payload = {"synthetic_controls": syn, "real_support": real,
               "incumbent_stdout_lines": len(buf.getvalue().splitlines()),
               "runtime_seconds": round(time.perf_counter() - t0, 1),
               "inputs_sha256": before, "data_root": str(env.DATA)}
    OUT.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    code, err = 1, None
    pre = {}
    try:
        pre = env.input_hashes()
        code = main()
    except Exception:  # noqa: BLE001
        err = traceback.format_exc(limit=6)
        code = 1
    outs = {}
    if OUT.exists():
        outs[str(OUT.relative_to(env.Q))] = env.sha256(OUT)
    env.append_run({"script": "baseline_repro.py", "exit_code": code, "inputs_sha256": pre,
                    "outputs_sha256": outs, "error": err})
    if err:
        sys.stderr.write(err)
    sys.exit(code)
