#!/usr/bin/env python3
"""Reproduce the bounded NVDA regular-session publication-price diagnostic."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
from pathlib import Path

import pandas as pd

PIN = "731a23fb64b9f6f1a321c77618f927f1a58d2d41"
PLAN_COMMIT = "74e8f45060e815a2cb7c515ae09f258919ab9da2"
PRICE_PATH = "data/baskets/ohlcv/NVDA.parquet"
PRICE_BLOB = "0e95a8c062c22f663fe7a80c9a76188bb444709e"
PLAN_PATH = "site/prophet/plans/NVDA-BULL-20260917.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected", type=Path)
    args = parser.parse_args()
    if args.repo.resolve() in args.out.resolve().parents:
        parser.error("Output must be outside the source checkout")

    def git(*cmd):
        return subprocess.check_output(["git", "-C", str(args.repo), *cmd], stderr=subprocess.PIPE)

    raw = git("show", f"{PIN}:{PRICE_PATH}")
    blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    assert blob == PRICE_BLOB, "Unexpected price source"
    plan = json.loads(git("show", f"{PLAN_COMMIT}:{PLAN_PATH}"))
    zone = plan["entry_zone"]
    publication = pd.Timestamp(git("show", "-s", "--format=%cI", PLAN_COMMIT).decode().strip()).tz_convert("UTC")
    prices = pd.read_parquet(io.BytesIO(raw)).sort_index()
    prices.index = pd.to_datetime(prices.index).tz_localize(None).normalize()
    prices = prices.loc[prices.index <= pd.Timestamp("2026-10-06")]
    regular_opens = (prices.index.tz_localize("America/New_York") + pd.Timedelta(hours=9, minutes=30)).tz_convert("UTC")
    after = prices.loc[regular_opens > publication, ["open", "high", "low", "close"]]
    assert len(after) == 6 and after.notna().all().all(), "Unexpected admitted source window"
    rows = [{"date": date.date().isoformat(), **{k: float(v) for k, v in row.items()}} for date, row in after.iterrows()]
    result = {
        "status": "DISCOVERY_PUBLICATION_OPPORTUNITY_DIAGNOSTIC_NO_FILL_CLAIM",
        "plan_publication_git_at": publication.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "plan_accumulate_low": zone["low"], "plan_accumulate_high": zone["high"],
        "plan_no_chase": zone["chase_above"],
        "source_repository": "mastermindx-market-intelligence/macro", "source_ref": PIN,
        "source_path": PRICE_PATH, "source_blob": blob,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_price_basis": "Back-adjusted daily OHLC; nominal execution or reader receipt not established",
        "observed_source_last_date": prices.index[-1].date().isoformat(),
        "first_regular_session_open_after_git_publication": {k: rows[0][k] for k in ["date", "open", "low"]},
        "regular_session_rows": rows,
        "minimum_regular_session_low": float(after.low.min()),
        "regular_sessions_low_at_or_below_no_chase": int(after.low.le(zone["chase_above"]).sum()),
        "regular_sessions_low_at_or_below_accumulate_high": int(after.low.le(zone["high"]).sum()),
        "interpretation": "In these six preserved regular sessions the source price never revisited the fixed final-plan no-chase ceiling or accumulation zone after Git publication. This is not a claim about extended-hours liquidity, plan delivery, actual order admission, costs, fills or a revised plan.",
    }
    if args.expected:
        assert result == json.loads(args.expected.read_text()), "Published result differs from reconstructed result"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "PASS", "source_blob": blob, "rows": len(rows), "minimum_low": result["minimum_regular_session_low"]}))


if __name__ == "__main__":
    main()
