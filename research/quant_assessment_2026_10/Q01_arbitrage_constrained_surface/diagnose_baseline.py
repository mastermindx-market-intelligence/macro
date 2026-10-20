from __future__ import annotations

# Post-run DIAGNOSTIC (not an evaluation run, not a trial): explains the S1 baseline divergence recorded
# by evaluate.py run 1. It reads only the S1 inputs already declared in PREREG section 5, re-runs the
# incumbent engine/options_skew.skew_map, and asks for every stored snapshot date which chain file (if
# any) reproduces those stored rows exactly, and whether the chain file's own capture stamp matches the
# snapshot stamp. It never touches the Q01 comparison. Refuses to run on a freeze-hash mismatch and
# appends one line (kind=post_run_diagnostic) to RUNS.log per run. No wall-clock value is read.
# Diagnostic run 1 reported a tie-break "best" chain on zero-match dates; run 2 reports None there and
# adds the previous-declared-chain comparison plus a summary. Both runs are logged; neither is a trial.

import hashlib
import json
import math
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATA = "/Users/chriswong/Documents/Cluade/macro-main/data"
RUNS = os.path.join(HERE, "RUNS.log")
OUT = os.path.join(HERE, "baseline_divergence.json")
FIELDS = ("otm_put_iv", "atm_call_iv", "skew", "spot", "tenor_days")
TOL = 1e-9


def sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def same(a, b) -> bool:
    try:
        fa, fb = float(a), float(b)
    except (TypeError, ValueError):
        return a == b
    if math.isnan(fa) and math.isnan(fb):
        return True
    return abs(fa - fb) < TOL


def row_match(got: dict | None, row) -> bool:
    if got is None:
        return False
    ok = all(same(got.get(c), row[c]) for c in FIELDS)
    return ok and got.get("n_strikes") is not None and int(got["n_strikes"]) == int(row["n_strikes"])


def main() -> int:
    frozen = {}
    with open(os.path.join(HERE, "FREEZE.log"), encoding="utf-8") as fh:
        for line in fh:
            if "=" in line:
                k, _, v = line.rstrip("\n").partition("=")
                frozen[k] = v
    record = {"kind": "post_run_diagnostic", "script": "diagnose_baseline.py",
              "command": [sys.executable] + list(sys.argv),
              "prereg_sha256": sha(os.path.join(HERE, "PREREG.md")),
              "script_sha256": sha(os.path.abspath(__file__))}
    if record["prereg_sha256"] != frozen.get("PREREG_SHA256"):
        record.update({"exit_code": 2, "reason": "freeze hash mismatch"})
        with open(RUNS, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
        return 2
    import pandas as pd

    sys.path.insert(0, REPO)
    from engine import options_skew as osk

    with open(os.path.join(HERE, "PREREG.md"), encoding="utf-8") as fh:
        prereg = fh.read()
    chain_rels = sorted({tok for tok in prereg.split("`") if tok.startswith("polygon_gex/chains/")})
    snap_path = os.path.join(DATA, "options_skew", "snapshots.parquet")
    inputs = {"options_skew/snapshots.parquet": sha(snap_path)}
    maps, chain_stamps = {}, {}
    for rel in chain_rels:
        path = os.path.join(DATA, rel)
        inputs[rel] = sha(path)
        chain = pd.read_parquet(path)
        date = os.path.basename(rel)[:10]
        maps[date] = osk.skew_map(chain)
        chain_stamps[date] = sorted({str(v) for v in chain["asof"].unique()})[:5]
    snap = pd.read_parquet(snap_path)
    pg = snap[snap["source"].astype(str) == "polygon_gex"].copy()
    pg["_d"] = pg["asof"].astype(str).str[:10]
    rows = []
    for date in sorted(maps):
        sub = pg[pg["_d"] == date]
        if sub.empty:
            continue
        stamps = sorted({str(v) for v in sub["asof"].unique()})
        per_chain = {}
        for c, mp in maps.items():
            per_chain[c] = int(sum(row_match(mp.get(r["underlying"]), r) for _, r in sub.iterrows()))
        best = max(per_chain.items(), key=lambda kv: (kv[1], kv[0]))
        if best[1] == 0:
            best = (None, 0)  # no declared chain reproduces any row; do not report a tie-break winner
        prev = [c for c in sorted(maps) if c < date]
        prev_date = prev[-1] if prev else None
        same_date = maps[date]
        n_spot_diff = n_other_only = 0
        for _, r in sub.iterrows():
            got = same_date.get(r["underlying"])
            if got is None or row_match(got, r):
                continue
            if not same(got.get("spot"), r["spot"]):
                n_spot_diff += 1
            else:
                n_other_only += 1
        rows.append({"snapshot_date": date, "snapshot_rows": int(len(sub)),
                     "snapshot_asof_stamps": stamps[:5], "n_snapshot_asof_stamps": len(stamps),
                     "chain_asof_stamps_same_date": chain_stamps[date],
                     "exact_matches_vs_same_date_chain": per_chain[date],
                     "best_chain_date": best[0], "exact_matches_vs_best_chain": best[1],
                     "previous_declared_chain_date": prev_date,
                     "exact_matches_vs_previous_declared_chain": per_chain[prev_date] if prev_date else None,
                     "same_date_mismatch_rows_with_spot_difference": n_spot_diff,
                     "same_date_mismatch_rows_spot_equal": n_other_only})
    payload = {"label": "post-run diagnostic of evaluate.py run 1 S1; not an evaluation run or trial",
               "tolerance_abs": TOL, "fields": list(FIELDS) + ["n_strikes"], "per_snapshot_date": rows,
               "chain_asof_stamps": chain_stamps}
    summary = {"snapshot_dates": len(rows), "snapshot_rows": sum(r["snapshot_rows"] for r in rows)}
    for key, test in (("same_date_exact", lambda r: r["exact_matches_vs_same_date_chain"] == r["snapshot_rows"]),
                      ("previous_declared_exact",
                       lambda r: r["exact_matches_vs_same_date_chain"] < r["snapshot_rows"]
                       and r["exact_matches_vs_previous_declared_chain"] == r["snapshot_rows"]),
                      ("unexplained_by_declared_inputs", lambda r: r["exact_matches_vs_best_chain"] == 0)):
        hit = [r for r in rows if test(r)]
        summary[key] = {"dates": [r["snapshot_date"] for r in hit], "rows": sum(r["snapshot_rows"] for r in hit)}
    payload["summary"] = summary
    text = json.dumps(payload, sort_keys=True, indent=1) + "\n"
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    record.update({"exit_code": 0, "inputs_sha256": inputs,
                   "outputs_sha256": {"baseline_divergence.json": sha(OUT)}})
    with open(RUNS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))
    for r in rows:
        print(r["snapshot_date"], r["snapshot_rows"], r["n_snapshot_asof_stamps"], r["snapshot_asof_stamps"][:2],
              r["chain_asof_stamps_same_date"][:2], r["exact_matches_vs_same_date_chain"],
              r["best_chain_date"], r["exact_matches_vs_best_chain"],
              r["same_date_mismatch_rows_with_spot_difference"], r["same_date_mismatch_rows_spot_equal"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
