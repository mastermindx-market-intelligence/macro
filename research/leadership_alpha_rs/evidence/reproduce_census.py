"""Reproduce bounded source archaeology, not performance or a new forward store.

Run from the repository: python research/leadership_alpha_rs/evidence/reproduce_census.py
Prints JSON to stdout. All bytes come from the frozen original source commit.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import subprocess

import pandas as pd

REF = "8a3310cdf03bc16704d51235172a5bbcf1f9a73e"
ROOT = Path(__file__).resolve().parents[3]
LIMIT = 20_000_000
PATHS = [
    "engine/residual_alpha.py", "engine/top_picks.py", "scripts/build_discovery.py",
    "templates/discovery.html.j2", "research/RESIDUAL_ALPHA_MOMENTUM.md",
    "research/US_STANDOUT_SETUP_SCORE.md", "reports/residual-alpha-phase0.md",
    "reports/top-picks-phase0.md", "site/discovery.html",
    "site/factordata/alpha.json", "site/factordata/factors.json", "site/basketdata/baskets.json",
    "research/LEADER_RADAR_MASTERPLAN_BY_FABLE.md", "engine/leader_lifecycle.py",
    "engine/winner_autopsy.py", "scripts/build_leader_radar.py",
    "site/leaderradar/radar.json", "data/leader_radar/state_history.parquet",
    "data/leader_radar/revisions_history.parquet", "data/leader_radar/fire_log.parquet",
    "data/rs_series/MU.parquet", "data/rs_series/SNDK.parquet",
    "data/pick_lab/fires.jsonl", "data/pick_lab/grades.jsonl",
    "engine/pick_lab/registry.py", "engine/pick_lab/candidates.py", "engine/pick_lab/ledger.py",
    "scripts/grade_us_board.py", "data/us_board_ledger/README.md",
    "data/us_board_ledger/snapshots.jsonl", "data/us_board_ledger/snapshots_v2.jsonl",
    "data/us_board_ledger/retro_grades.parquet", "data/us_board_ledger/retro_grades_v2.parquet",
    "data/us_board_ledger/disclosed_gaps.json",
    "engine/group_flow.py", "engine/us_leader_pullback_coverage.py",
    "research/alpha_intelligence/expectation_market_dynamics/OWNER_AND_REUSE_MATRIX.md",
    "research/alpha_intelligence/expectation_market_dynamics/BUILD_SEQUENCE.md",
]


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE, timeout=30)


def main() -> None:
    manifest = {"source_ref": REF, "mode": "IMMUTABLE_GIT_CENSUS_NOT_LIVE_OR_PIT_PROOF",
                "sources": {}, "findings": {}}
    payloads = {}
    for path in PATHS:
        try:
            size = int(git("cat-file", "-s", f"{REF}:{path}"))
        except subprocess.CalledProcessError:
            manifest["sources"][path] = {"status": "ABSENT_AT_SOURCE_PIN"}
            continue
        if size > LIMIT:
            manifest["sources"][path] = {"bytes": size, "status": "METADATA_ONLY_SIZE_LIMIT",
                                         "git_blob": git("rev-parse", f"{REF}:{path}").decode().strip()}
            continue
        raw = git("show", f"{REF}:{path}")
        manifest["sources"][path] = {
            "bytes": size, "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest(),
        }
        payloads[path] = raw
    findings = manifest["findings"]
    alpha = json.loads(payloads["site/factordata/alpha.json"])
    factors = json.loads(payloads["site/factordata/factors.json"])
    baskets = json.loads(payloads["site/basketdata/baskets.json"])
    findings["alpha"] = {"as_of": alpha["as_of"], "rows": len(alpha["per_ticker"]),
                         "illustrative_recovered_rows": {ticker: {
                             key: alpha["per_ticker"][ticker].get(key) for key in ["alpha", "rs"]
                         } for ticker in ["SNDK", "MU"]}}
    findings["factors"] = {"as_of": factors["as_of"], "rows": len(factors["table"])}
    findings["baskets"] = {"as_of": baskets["as_of"], "rows": len(baskets["baskets"])}
    radar = json.loads(payloads["site/leaderradar/radar.json"])
    findings["leader_radar"] = {
        **{k: radar.get(k) for k in ["schema", "as_of", "built_at", "freshness", "history_since", "history_gaps", "degraded"]},
        "rows": len(radar["rows"]), "rerating_watch_rows": len(radar["rerating_watch"]),
        "early_entry_rows": len(radar["early_entry"]), "handoff_pairs": len(radar["handoff_pairs"]),
        "analyst_covered": radar["coverage"]["analyst_covered"],
        "revisions_uncovered_count": len(radar["coverage"]["revisions_uncovered"]),
        "pit_caveat": "Built October 5 with revision/regime dates after price-through October 2; not a lawful October 2 knowledge replay.",
    }
    series_paths = git("ls-tree", "-r", "--name-only", REF, "data/rs_series").decode().splitlines()
    findings["rs_series"] = {"tracked_files": len(series_paths), "full_directory_values_read": False}
    findings["parquets"] = {}
    for path in [p for p in PATHS if p.endswith(".parquet")]:
        frame = pd.read_parquet(io.BytesIO(payloads[path]))
        row = {"rows": len(frame), "columns": list(frame.columns)}
        for column in ["date", "asof", "as_of"]:
            if column in frame:
                row[column] = {"distinct": int(frame[column].nunique()),
                               "min": str(frame[column].min()), "max": str(frame[column].max())}
        if isinstance(frame.index, pd.DatetimeIndex):
            row["index"] = {"min": str(frame.index.min()), "max": str(frame.index.max())}
        if "ticker" in frame:
            row["tickers"] = int(frame["ticker"].nunique())
        for column in ["lane", "price_basis"]:
            if column in frame:
                row[column] = {str(k): int(v) for k, v in frame[column].fillna("UNKNOWN").value_counts().items()}
        findings["parquets"][path] = row
    findings["pick_lab"] = {}
    for path in ["data/pick_lab/fires.jsonl", "data/pick_lab/grades.jsonl"]:
        rows = [json.loads(line) for line in payloads[path].splitlines() if line.strip()]
        summary = {"all_books_rows": len(rows), "books": {}}
        for book in ["plab_leader_precipice", "plab_leader_onset"]:
            selected = [r for r in rows if r.get("engine_id") == book]
            dates = [r["fire_date"] for r in selected]
            key_counts = Counter((r["ticker"], r["fire_date"], r.get("horizon"), r.get("kind")) for r in selected)
            book_summary = {"rows": len(selected), "distinct_tickers": len({r["ticker"] for r in selected}),
                            "first_fire_date": min(dates) if dates else None,
                            "last_fire_date": max(dates) if dates else None,
                            "duplicate_natural_keys": sum(n - 1 for n in key_counts.values()),
                            "authorities": sorted({r.get("authority", "MISSING") for r in selected})}
            if path.endswith("grades.jsonl"):
                book_summary["grade_horizons"] = dict(sorted(Counter(str(r.get("horizon")) for r in selected).items()))
                book_summary["matured_21d_return_rows"] = sum(r.get("horizon") == 21 and r.get("kind") == "ret" and r.get("matured") is True for r in selected)
            summary["books"][book] = book_summary
        findings["pick_lab"][path] = summary
    findings["limits"] = [
        "No outcome performance or forecast calibration computed.",
        "Precipice/onset fires do not cover all 1602 legacy Alpha records or all continuation entries.",
        "Stored snapshot dates do not establish source availability or deployment.",
        "Raw Radar fire_log and Pick Lab fires use different schemas and counts; exact episode join remains unqualified.",
        "State history contains gaps; retrospective transitions cannot be invented.",
        "Existing source ownership, held chips and forward writers unchanged.",
    ]
    print(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
