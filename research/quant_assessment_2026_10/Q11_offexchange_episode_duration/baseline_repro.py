"""Q11 pre-freeze step: incumbent baseline reproduction + data eligibility census.

Runs BEFORE PREREG.md is frozen. It computes only (a) the incumbent's own outputs
(engine.darkpool_signals.streak_above_norm) re-derived from retained data and compared
with the incumbent's published context artifact, (b) the incumbent unit tests, and
(c) support / attrition counts for the eligible cohort. It computes NO challenger output
and NO comparison metric, so nothing here is an evaluation outcome.

Usage:
    python3.12 baseline_repro.py
Appends one JSON line to RUNS.log (command, exit code, input/output sha256s).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
Q11_ROOT = HERE.parents[2]
sys.path.insert(0, str(Q11_ROOT))

from engine.darkpool_signals import share_break_index, streak_above_norm, usable_history  # noqa: E402

DATA = Path("/Users/chriswong/Documents/Cluade/macro-main/data")
PANEL = DATA / "finra_short_volume" / "panel.parquet"
PANEL_DEEP = DATA / "finra_short_volume" / "panel_deep.parquet"
YAHOO = DATA / "yahoo"
CONTEXT = DATA / "darkpool" / "context" / "latest.json"
CAL_REF = YAHOO / "SPY.parquet"

# Pre-declared eligibility thresholds (also stated in PREREG.md §Cohort).
TRAIN_END = "2025-06-30"
MIN_TRAIN_OBS = 300
MIN_TEST_OBS = 150


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_stamp() -> str:
    return subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True,
                          text=True, check=True).stdout.strip()


def load_panel() -> tuple[pd.DataFrame, dict]:
    deep = pd.read_parquet(PANEL_DEEP)
    coll = pd.read_parquet(PANEL)
    for d in (deep, coll):
        d["date"] = pd.to_datetime(d["date"]).dt.normalize()
    key = ["date", "ticker"]
    ov = deep.merge(coll, on=key, suffixes=("_d", "_c"))
    rev = {
        "overlap_rows": int(len(ov)),
        "overlap_total_vol_differs": int((~np.isclose(ov["total_vol_d"], ov["total_vol_c"])).sum()),
    }
    df = pd.concat([deep, coll], ignore_index=True).drop_duplicates(subset=key, keep="last")
    return df.sort_values(key).reset_index(drop=True), rev


def load_yahoo_vol(tk: str) -> pd.Series | None:
    p = YAHOO / f"{tk}.parquet"
    if not p.exists():
        return None
    y = pd.read_parquet(p)
    if "volume" not in y.columns:
        return None
    s = y["volume"].copy()
    s.index = pd.to_datetime(s.index).normalize()
    s = s[~s.index.duplicated(keep="last")].dropna()
    return s


def participation(f: pd.DataFrame, cons: pd.Series) -> pd.Series:
    """Incumbent construction: exact-date inner join, cons>0, no ffill."""
    j = f.set_index("date")[["total_vol"]].join(cons.rename("cons"), how="inner")
    j = j[j["cons"] > 0]
    return (j["total_vol"] / j["cons"]).dropna()


def main() -> int:
    cmd = " ".join([sys.executable] + sys.argv)
    inputs: dict[str, str] = {
        "panel.parquet": sha256(PANEL),
        "panel_deep.parquet": sha256(PANEL_DEEP),
        "darkpool/context/latest.json": sha256(CONTEXT),
        "yahoo/SPY.parquet": sha256(CAL_REF),
    }
    df, rev = load_panel()

    # --- (b) incumbent unit tests inside the Q11 clone --------------------------
    t = subprocess.run(
        [sys.executable, "-m", "pytest", str(Q11_ROOT / "tests" / "test_darkpool_signals.py"),
         "--rootdir", str(Q11_ROOT), "--noconftest", "-p", "no:cacheprovider", "-q"],
        capture_output=True, text=True, cwd=str(HERE),
        env={"PYTHONPATH": str(Q11_ROOT), "PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"},
    )
    test_tail = (t.stdout.strip().splitlines() or [""])[-1]

    # --- (a) reproduce the incumbent's published streaks --------------------------
    ctx = json.loads(CONTEXT.read_text())
    asof = pd.Timestamp(ctx["asof"])
    repro = []
    for row in ctx.get("standouts", []):
        tk = row["ticker"]
        cons = load_yahoo_vol(tk)
        if cons is None:
            repro.append({"ticker": tk, "published": row.get("streak"), "reproduced": None})
            continue
        inputs[f"yahoo/{tk}.parquet"] = sha256(YAHOO / f"{tk}.parquet")
        f = df[(df["ticker"] == tk) & (df["date"] <= asof)]
        part = usable_history(participation(f, cons[cons.index <= asof]))
        repro.append({"ticker": tk, "published": row.get("streak"),
                      "reproduced": int(streak_above_norm(part))})
    n_match = sum(1 for r in repro if r["reproduced"] == r["published"])

    # --- (c) eligibility census over the deep-panel cohort --------------------------
    cal = load_yahoo_vol("SPY")
    lo, hi = df["date"].min(), df["date"].max()
    cal_dates = cal.index[(cal.index >= lo) & (cal.index <= hi)]
    finra_dates = pd.DatetimeIndex(sorted(df["date"].unique()))
    missing_finra = cal_dates.difference(finra_dates)
    deep_names = sorted(pd.read_parquet(PANEL_DEEP, columns=["ticker"])["ticker"].unique())
    rows = []
    for tk in deep_names:
        cons = load_yahoo_vol(tk)
        rec = {"ticker": tk, "yahoo": cons is not None}
        if cons is None:
            rec["status"] = "no_yahoo_volume"
            rows.append(rec)
            continue
        inputs[f"yahoo/{tk}.parquet"] = sha256(YAHOO / f"{tk}.parquet")
        part = participation(df[df["ticker"] == tk], cons)
        part = part[part.index.isin(cal_dates)]
        brk = share_break_index(part)
        n_tr = int((part.index <= TRAIN_END).sum())
        n_te = int((part.index > TRAIN_END).sum())
        span = cal_dates[(cal_dates >= part.index.min()) & (cal_dates <= part.index.max())] if len(part) else cal_dates[:0]
        rec.update({"n_obs": int(len(part)), "n_train": n_tr, "n_test": n_te,
                    "missing_sessions_in_span": int(len(span) - len(part)),
                    "share_break": brk is not None})
        if brk is not None:
            rec["status"] = "excluded_share_basis_break"
        elif n_tr < MIN_TRAIN_OBS:
            rec["status"] = "excluded_short_train"
        elif n_te < MIN_TEST_OBS:
            rec["status"] = "excluded_short_test"
        else:
            rec["status"] = "eligible"
        rows.append(rec)
    status_counts: dict[str, int] = {}
    for r in rows:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

    out = {
        "stage": "pre-freeze baseline + eligibility (no challenger output computed)",
        "incumbent_tests": {"exit_code": t.returncode, "tail": test_tail},
        "streak_reproduction": {"asof": ctx["asof"], "n": len(repro), "n_exact_match": n_match,
                                 "rows": repro},
        "calendar": {"first": str(lo.date()), "last": str(hi.date()), "n_sessions": int(len(cal_dates)),
                     "n_finra_dates": int(len(finra_dates)),
                     "missing_finra_sessions": [str(d.date()) for d in missing_finra]},
        "revisions": rev,
        "cohort": {"n_deep_names": len(deep_names), "status_counts": status_counts,
                   "thresholds": {"train_end": TRAIN_END, "min_train_obs": MIN_TRAIN_OBS,
                                  "min_test_obs": MIN_TEST_OBS}},
        "names": rows,
    }
    res = HERE / "results"
    res.mkdir(exist_ok=True)
    out_p = res / "baseline_eligibility.json"
    out_p.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    inp_p = res / "baseline_inputs_sha256.json"
    inp_p.write_text(json.dumps(inputs, indent=0, sort_keys=True) + "\n")
    rc = 0 if t.returncode == 0 else 1
    entry = {
        "utc": utc_stamp(), "script": "baseline_repro.py", "command": cmd, "exit_code": rc,
        "incumbent_pytest_exit_code": t.returncode,
        "inputs": {k: inputs[k] for k in ("panel.parquet", "panel_deep.parquet",
                                          "darkpool/context/latest.json", "yahoo/SPY.parquet")},
        "inputs_manifest_sha256": sha256(inp_p), "n_input_files": len(inputs),
        "outputs": {"results/baseline_eligibility.json": sha256(out_p),
                    "results/baseline_inputs_sha256.json": sha256(inp_p)},
    }
    with open(HERE / "RUNS.log", "a") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    print(json.dumps({"incumbent_tests": out["incumbent_tests"],
                      "repro": f"{n_match}/{len(repro)}", "cohort": status_counts,
                      "calendar": {k: v for k, v in out["calendar"].items() if k != "missing_finra_sessions"},
                      "n_missing_finra": len(missing_finra), "revisions": rev}, indent=1))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
