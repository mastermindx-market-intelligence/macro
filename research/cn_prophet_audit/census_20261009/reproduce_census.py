"""Read-only China Prophet pipeline census at an immutable Macro commit.

Usage: python3 reproduce_census.py --repo /path/to/macro --sha COMMIT > evidence.json
Reads git blobs only. Writes no source, data, models, ledgers, or publication.
Temporary fixture files exercise exact AST-extracted pure file readers.
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

PIN = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--sha", default=PIN)
    args = parser.parse_args()

    def raw(path: str) -> bytes:
        return subprocess.check_output(
            ["git", "-C", args.repo, "show", args.sha + ":" + path],
            stderr=subprocess.DEVNULL,
        )

    def parquet(path: str) -> pd.DataFrame:
        return pd.read_parquet(io.BytesIO(raw(path)))

    board = json.loads(raw("site/factordata/china_standouts.json"))
    sources = {}
    for path in [
        "data/china_analyst/forecast.parquet",
        "data/china_valuation/percentiles.parquet",
        "data/china_margin_detail/detail.parquet",
        "data/china_comment/detail.parquet",
        "data/china_lhb/detail.parquet",
        "data/china_block_trades/detail.parquet",
        "data/tushare/moneyflow.parquet",
        "data/china_search/members.parquet",
        "data/china_search/dropped.parquet",
        "data/china_search/index_cons.parquet",
        "data/cn_prophet_live/forward.parquet",
    ]:
        frame = parquet(path)
        dates = {}
        for col in frame.columns:
            if any(part in str(col).lower() for part in (
                "date", "asof", "as_of", "fetched", "observed", "collected", "first_seen"
            )):
                values = frame[col].dropna().astype(str)
                dates[str(col)] = {
                    "min": values.min() if len(values) else None,
                    "max": values.max() if len(values) else None,
                    "n_unique": int(values.nunique()),
                }
        sources[path] = {"rows": len(frame), "columns": list(frame.columns), "clocks": dates}
        if path.endswith("members.parquet"):
            sources[path]["placeholder_mcap_30"] = int((frame["mktcap_yi"] == 30).sum())
            sources[path]["exchange_counts"] = (
                frame.index.to_series().astype(str).str.split(".").str[-1].value_counts().to_dict()
            )

    valuation = parquet("data/china_valuation/percentiles.parquet")
    valuation["age_days"] = (
        pd.Timestamp(board["as_of"]) - pd.to_datetime(valuation["asof"])
    ).dt.days
    age_summary = {}
    groups = {
        "all_valuation": set(valuation["ticker"]),
        "featured": {r["ticker"] for r in board["buy"]},
        "eligible": {
            r["ticker"] for k in ("buy", "more_actionable", "late_or_unfillable", "forming")
            for r in board[k]
        },
    }
    for group, tickers in groups.items():
        selected = valuation[valuation["ticker"].isin(tickers)]
        age_summary[group] = {
            "n_tickers": len(tickers),
            "valuation_matched": len(selected),
            "max_age_days": int(selected["age_days"].max()),
            "age_over_7": int((selected["age_days"] > 7).sum()),
            "age_over_30": int((selected["age_days"] > 30).sum()),
        }
        if group == "featured":
            age_summary[group]["oldest_five"] = selected.sort_values(
                "age_days", ascending=False
            )[["ticker", "asof", "age_days"]].head(5).to_dict("records")

    tree = ast.parse(raw("scripts/build_cn_live_pack.py"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_frozen")
    scope = {"Path": Path, "json": json, "Any": Any}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "load_frozen@" + args.sha, "exec"), scope)
    with tempfile.TemporaryDirectory(prefix="cn-pipeline-census-") as scratch:
        root = Path(scratch)
        (root / "site/factordata").mkdir(parents=True)
        (root / "site/factordata/china_standouts.json").write_text(json.dumps(board))
        canonical_count = len(scope["load_frozen"](root))
        (root / "site/china_standouts.json").write_text(json.dumps(board))
        alternate_path_count = len(scope["load_frozen"](root))

    pack_tree = ast.parse(raw("engine/prophet_live/cn_pack.py"))
    attach = next(n for n in pack_tree.body if isinstance(n, ast.FunctionDef) and n.name == "attach_frozen")
    for node in pack_tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id in ("FROZEN_LEG_KEYS", "LIVE_DERIVED_KEYS"):
                scope[node.target.id] = ast.literal_eval(node.value)
    scope["Mapping"] = Mapping
    exec(compile(ast.Module(body=[attach], type_ignores=[]), "attach_frozen@" + args.sha, "exec"), scope)
    attached = scope["attach_frozen"]({}, board["buy"][0])
    reconcile = ast.parse(raw("scripts/reconcile_cn_live.py"))
    run_asia = next(n for n in reconcile.body if isinstance(n, ast.FunctionDef) and n.name == "run_asia")
    pack_reads = [n.lineno for n in ast.walk(run_asia)
                  if isinstance(n, ast.Name) and n.id == "pack_path" and isinstance(n.ctx, ast.Load)]
    publication_clocks = {}
    for path in ("site/chinaradar/radar.json", "site/chinaspecialdata/special.json",
                 "site/chinaaltdata/by_ticker.json", "site/china_intel/command.json"):
        doc = json.loads(raw(path))
        publication_clocks[path] = {k: v for k, v in doc.items()
                                   if any(p in k for p in ("date", "asof", "as_of", "built", "generated"))}

    out = {
        "source_sha": args.sha,
        "claim_limits": "Pinned source and committed artifacts only; no deployed process, browser, alpha or PnL proof.",
        "board": {k: board.get(k) for k in ("as_of", "board_definition", "universe", "lane_counts", "coverage", "staleness", "ranking")},
        "source_datasets": sources,
        "valuation_age_calendar_days": age_summary,
        "publication_clocks": publication_clocks,
        "frozen_join_probe": {
            "canonical_path_and_schema_loaded_rows": canonical_count,
            "alternate_path_with_canonical_schema_loaded_rows": alternate_path_count,
            "first_canonical_row_attach_result": attached,
        },
        "run_asia_pack_path_load_nodes": pack_reads,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
