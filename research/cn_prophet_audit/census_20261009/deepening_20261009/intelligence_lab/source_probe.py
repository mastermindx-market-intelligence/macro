"""Read immutable source/data for the intelligence contract lab; no production imports."""
from __future__ import annotations
import argparse
import ast
import hashlib
import io
import json
import math
from collections import Counter
from pathlib import Path
import subprocess
import pandas as pd

PIN = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    hashes = {}
    def read(path):
        b = subprocess.check_output(["git", "-C", a.repo, "show", PIN + ":" + path])
        hashes[path] = {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
                        "git_blob": hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()}
        return b
    board = json.loads(read("site/factordata/china_standouts.json"))
    candidates = pd.read_parquet(io.BytesIO(read("data/china_prophet_rank/candidates.parquet")))
    current = candidates[candidates.stamp_date.astype(str).str[:10] == board["as_of"]]
    assert current.ticker.is_unique
    qualified = list(board["buy"]) + [r for r in board["more_actionable"]
        if r.get("lane_reasons") and set(r["lane_reasons"]) <= {"featured_cap", "sector_cap"}]
    q = [{"ticker": r["ticker"], "sector": r.get("sector") or "—",
          "score": r["prophet"]["score"], "score_rank": r["score_rank"],
          "intel": r.get("intel_interest_score"), "intel_basis": r.get("intel_interest_basis"),
          "lane": r["lane"]} for r in qualified]
    def cov(df):
        values = pd.to_numeric(df.intel_score, errors="coerce")
        valid = df.intel_basis.eq("measured") & values.notna() & values.map(math.isfinite)
        return {"n": len(df), "valid": int(valid.sum()), "missing": df.loc[~valid, "ticker"].tolist()}
    populations = {"all_scored": cov(current), "raw_eligible": cov(current[current.raw_eligible.eq(True)]),
                   "signal_buyable": cov(current[current.buyable.eq(True)]),
                   "qualified_pre_cap": {"n": len(q), "valid": sum(r["intel_basis"] == "measured" and isinstance(r["intel"], (int,float)) and not isinstance(r["intel"],bool) and math.isfinite(r["intel"]) and 0<=r["intel"]<=100 for r in q)}}
    paths = ["data/china_analyst/forecast.parquet", "data/china_valuation/percentiles.parquet",
             "data/china_margin_detail/detail.parquet", "data/china_comment/detail.parquet",
             "data/china_lhb/detail.parquet", "data/china_block_trades/detail.parquet",
             "data/tushare/moneyflow.parquet", "data/china_comment/attention_hist.parquet"]
    inventory = subprocess.check_output(["git", "-C", a.repo, "ls-tree", "-r", "--name-only", PIN, "data/"]).decode().splitlines()
    schemas = {}
    def is_clock(c):
        return any(x in c.lower() for x in ["date", "time", "asof", "as_of", "seen", "pub", "ingest", "revision", "fetched", "effective"])
    for p in paths:
        if p not in inventory:
            schemas[p] = {"state": "absent_at_pin"}; continue
        df = pd.read_parquet(io.BytesIO(read(p)))
        clocks = {}
        for c in df.columns:
            if is_clock(c):
                v = df[c].dropna().astype(str)
                clocks[c] = {"non_null": len(v), "distinct": int(v.nunique()),
                             "min": min(v) if len(v) else None, "max": max(v) if len(v) else None}
        payloadkeys = Counter(); payloadclocks = Counter()
        if "payload" in df.columns:
            for value in df.payload:
                try: obj=json.loads(value)
                except Exception: continue
                if isinstance(obj,dict):
                    payloadkeys.update(obj.keys());payloadclocks.update(k for k in obj if is_clock(k))
        schemas[p] = {"state": "read", "rows": len(df), "columns": list(df.columns), "clock_fields": clocks,
                      "payload_keys": dict(payloadkeys), "payload_clock_keys": dict(payloadclocks),
                      "duplicated_ticker_rows": int(df.ticker.duplicated(keep=False).sum()) if "ticker" in df.columns else None}
    extracted = {}
    for path,names in [("engine/china_altdata.py",{"_rank_pct"}), ("engine/china_extras.py",{"analyst_consensus","_read_payload","_read_table"}), ("engine/china_board_rank.py",{"_finite_float","intel_interest_is_measured"})]:
        source=read(path).decode(); tree=ast.parse(source)
        for node in tree.body:
            if isinstance(node,ast.FunctionDef) and node.name in names:
                extracted[node.name] = {"path":path,"line":node.lineno,"source":ast.get_source_segment(source,node)}
    out={"source_sha":PIN,"as_of":board["as_of"],"input_hashes":hashes,"population_coverage":populations,
         "published_featured":[r["ticker"] for r in board["buy"]], "qualified_rows":q,
         "source_clock_inventory":schemas,"source_functions":extracted,
         "limits":["Qualified population inferred from published admission/cap reasons, not recomputed from discarded private join metadata.",
                   "Candidate and public artifact vintages remain distinct; source-time clocks are inventoried, not certified from column names.",
                   "No labels, ranking promotion, production write or past publication proof."]}
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"output":a.out,"qualified":len(q),"source_count":len(hashes),"coverage":populations},ensure_ascii=False))

if __name__ == "__main__": main()
