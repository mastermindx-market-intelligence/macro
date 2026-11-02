import ast, json, subprocess, hashlib
from pathlib import Path
W = "/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/risk-radar-meta-ceo-census-20261017-01c18c888a133151"
REF = "646cc093b4982eabc736862926fe7f1fc458b8a1"
def extract(path, names):
    raw = subprocess.check_output(["git", "show", REF + ":" + path], cwd=W)
    text = raw.decode()
    selected = []
    for n in ast.parse(text).body:
        name = getattr(n, "name", None)
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
            name = n.targets[0].id
        if name in names:
            selected.append(n)
    got = len(selected)
    assert got == len(names), (path, got, names)
    return ast.unparse(ast.Module(body=selected, type_ignores=[])), hashlib.sha256(raw).hexdigest()
identity, identity_sha = extract("scripts/research/grey_deer_pullback_stage1.py", {"AS_OF", "IDENTITY_COLUMNS", "_enc", "normalize_subframe", "subframe_sha256"})
reader, reader_sha = extract("scripts/publish_r2.py", {"_POOL_FLOOR", "_POOL_HEADROOM", "_TRANSFER_CONCURRENCY", "_pool_size", "_client"})
remote = """
import os, json, io, hashlib, ast
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from dotenv import dotenv_values
for k, v in dotenv_values('/etc/macro-api.env').items():
    if v is not None and k.startswith('R2_'):
        os.environ[k] = v
"""
remote += reader + "\n" + identity + "\n"
remote += """
result = {
    "schema": "grey_deer.spy_input_identity.v1",
    "observed_at_utc": datetime.now(timezone.utc).isoformat(),
    "mode": "one retained internal R2 object; admission only",
    "source_key": "massive_stock_day/SPY.parquet",
    "source_ref": REF,
    "identity_source_sha256": IDENTITY_SHA,
    "canonical_reader_source_sha256": READER_SHA,
    "expected_normalized_sha256": "c686f0bc683f3109c1be5431cab99661734f2481fc98e8479320e285507be6fb",
    "expected_window": ["2021-07-06", "2026-10-07"],
    "expected_rows": 1321,
    "basis": "RAW / close_raw",
    "side_effects": {"namespace_hydration": False, "provider_fetch": False, "production_file_write": False,
                     "sample_generation": False, "feature_outcome_join": False, "fit": False, "trial_write": False},
}
try:
    client = _client(1)
    if client is None:
        result["status"] = "BLOCKED / NO_CONFIGURED_READER"
    else:
        bucket = os.environ["R2_BUCKET"]
        meta = client.head_object(Bucket=bucket, Key=result["source_key"])
        limit = 262144
        if not 0 < meta["ContentLength"] <= limit:
            raise ValueError("OBJECT_SIZE_OUTSIDE_BOUND")
        obj = client.get_object(Bucket=bucket, Key=result["source_key"], IfMatch=meta["ETag"])
        raw = obj["Body"].read(limit + 1)
        obj["Body"].close()
        assert len(raw) == meta["ContentLength"] <= limit
        df = pd.read_parquet(io.BytesIO(raw))
        sub = normalize_subframe(df)
        digest = subframe_sha256(sub)
        close = pd.to_numeric(sub["close"], errors="coerce")
        ratios = close / close.shift(1)
        result["object"] = {
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "etag": meta["ETag"].strip('"'), "last_modified": meta["LastModified"].isoformat(),
            "version_id": meta.get("VersionId"), "whole_object_rows": len(df),
        }
        result["normalized"] = {
            "sha256": digest, "rows": len(sub),
            "first_date": str(sub["date"].min()), "last_date": str(sub["date"].max()),
            "duplicate_dates": int(sub["date"].duplicated().sum()),
            "missing_cells": {c: int(sub[c].isna().sum()) for c in sub.columns},
            "nonfinite_or_nonpositive_closes": int((~np.isfinite(close) | (close <= 0)).sum()),
            "ratio_discontinuities": int(((ratios < 0.75) | (ratios > 1 / 0.75)).sum()),
            "normalization": "actual frozen stage1 pure AST functions; unchanged cutoff and float.hex encoding",
        }
        n = result["normalized"]
        good = (digest == result["expected_normalized_sha256"] and len(sub) == 1321
                and [n["first_date"], n["last_date"]] == result["expected_window"]
                and n["duplicate_dates"] == 0 and not any(n["missing_cells"].values())
                and n["nonfinite_or_nonpositive_closes"] == 0 and n["ratio_discontinuities"] == 0)
        result["status"] = "INPUT_IDENTITY_ADMITTED" if good else "BLOCKED / SAMPLE_INPUT_IDENTITY_MISMATCH"
        result["calendar_basis"] = "exact frozen normalized bytes, including date column; no substitute calendar or filling"
    result["t12_sample_digest"] = None
    result["t13_fit_admitted"] = False
    result["publication_admitted"] = False
except Exception as e:
    result["status"] = "BLOCKED / INPUT_READ_OR_QUALIFICATION_FAILED"
    result["error_type"] = type(e).__name__
    if hasattr(e, "response"):
        result["error_code"] = str(e.response.get("Error", {}).get("Code", ""))
print(json.dumps(result, sort_keys=True))
"""
remote = "REF = " + repr(REF) + "\nIDENTITY_SHA = " + repr(identity_sha) + "\nREADER_SHA = " + repr(reader_sha) + "\n" + remote
r = subprocess.run(["ssh", "-i", "/Users/chriswong/.ssh/macro_dashboard_deploy_v2", "-o", "BatchMode=yes",
                    "-o", "ConnectTimeout=12", "root@146.190.142.17", "/opt/macro-api/.venv/bin/python", "-"],
                   input=remote, text=True, capture_output=True, timeout=150)
if r.returncode:
    print(json.dumps({"status": "SSH_ADMISSION_READ_FAILED", "exit_code": r.returncode, "stderr": r.stderr[-800:]}))
    raise SystemExit(r.returncode)
row = json.loads(r.stdout)
row["orchestrator_script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
p = Path("/tmp/risk-radar-spy-input-identity-20261017.json")
p.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n")
print(json.dumps(row))
