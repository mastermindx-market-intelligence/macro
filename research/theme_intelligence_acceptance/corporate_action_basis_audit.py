#!/usr/bin/env python3
"""Deterministic corporate-action basis audit for Lane C's US first vertical."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

SUBJECT = "2208fe40039d356929fac0f96b626edc33d42288"
SPLITS = {"NVDA": "2024-06-10", "AVGO": "2024-07-15"}
DIVIDEND_WITNESSES = {"AAPL": "2024-05-10", "XOM": "2025-08-15"}
STORES = ("baskets/ohlcv", "stocks", "yahoo")


def git_bytes(root: Path, subject: str, path: str) -> bytes:
    p = subprocess.run(
        ["git", "-C", str(root), "show", f"{subject}:{path}"],
        check=False, capture_output=True,
    )
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors="replace"))
    return p.stdout


def frame_from_git(root: Path, subject: str, path: str) -> tuple[pd.DataFrame, str]:
    raw = git_bytes(root, subject, path)
    with tempfile.NamedTemporaryFile(suffix=".parquet") as f:
        f.write(raw)
        f.flush()
        df = pd.read_parquet(f.name)
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df = df.copy()
    df.index = idx
    return df, hashlib.sha256(raw).hexdigest()


def event_row(df: pd.DataFrame, date: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    event = pd.Timestamp(date)
    if event not in df.index:
        raise AssertionError(f"event {date} absent")
    prev = df.index[df.index < event].max()
    return prev, event


def audit(root: Path, subject: str) -> dict:
    source_paths = {
        "basket_fetcher": "scripts/fetch_basket_ohlcv.py",
        "stocks_collector": "collectors/sector_holdings.py",
        "yahoo_collector": "collectors/yahoo.py",
    }
    source = {k: git_bytes(root, subject, p).decode() for k, p in source_paths.items()}
    source_assertions = {
        "basket_auto_adjust_true": "auto_adjust=True" in source["basket_fetcher"],
        "stocks_auto_adjust_true": "auto_adjust=True" in source["stocks_collector"],
        "yahoo_close_is_total_return_adjusted": "total-return (split+dividend adjusted)" in source["yahoo_collector"],
        "yahoo_close_price_is_dividend_unadjusted": "dividend-UNadjusted" in source["yahoo_collector"],
    }

    split_rows = {}
    for ticker, date in SPLITS.items():
        frames = {}
        for store in STORES:
            path = f"data/{store}/{ticker}.parquet"
            frames[store], digest = frame_from_git(root, subject, path)
            frames[store].attrs["sha256"] = digest
        prev, event = event_row(frames["baskets/ohlcv"], date)
        returns = {
            store: float(df.loc[event, "close"] / df.loc[prev, "close"] - 1)
            for store, df in frames.items()
        }
        close_parity = max(
            abs(float(frames[a].loc[event, "close"] / frames[b].loc[event, "close"] - 1))
            for i, a in enumerate(STORES) for b in STORES[i + 1:]
        )
        volume_parity = max(
            abs(float(frames[a].loc[event, "volume"] / frames[b].loc[event, "volume"] - 1))
            for i, a in enumerate(STORES) for b in STORES[i + 1:]
        )
        split_rows[ticker] = {
            "event": date,
            "previous_session": prev.date().isoformat(),
            "returns": returns,
            "max_close_rung_relative_diff": close_parity,
            "max_volume_rung_relative_diff": volume_parity,
            "sha256": {store: frames[store].attrs["sha256"] for store in STORES},
            "pass": max(abs(x) for x in returns.values()) < 0.20
                    and close_parity < 1e-5 and volume_parity < 1e-12,
        }

    dividend_rows = {}
    for ticker, date in DIVIDEND_WITNESSES.items():
        yahoo, ysha = frame_from_git(root, subject, f"data/yahoo/{ticker}.parquet")
        stocks, ssha = frame_from_git(root, subject, f"data/stocks/{ticker}.parquet")
        prev, event = event_row(yahoo, date)
        adjusted_return = float(yahoo.loc[event, "close"] / yahoo.loc[prev, "close"] - 1)
        nominal_return = float(yahoo.loc[event, "close_price"] / yahoo.loc[prev, "close_price"] - 1)
        ratio_before = float(yahoo.loc[prev, "close"] / yahoo.loc[prev, "close_price"])
        ratio_after = float(yahoo.loc[event, "close"] / yahoo.loc[event, "close_price"])
        stocks_parity = abs(float(stocks.loc[event, "close"] / yahoo.loc[event, "close"] - 1))
        volume_parity = abs(float(stocks.loc[event, "volume"] / yahoo.loc[event, "volume"] - 1))
        dividend_rows[ticker] = {
            "event": date,
            "previous_session": prev.date().isoformat(),
            "adjusted_return": adjusted_return,
            "nominal_return": nominal_return,
            "adjustment_ratio_before": ratio_before,
            "adjustment_ratio_after": ratio_after,
            "stocks_vs_yahoo_adjusted_close_relative_diff": stocks_parity,
            "stocks_vs_yahoo_volume_relative_diff": volume_parity,
            "sha256": {"stocks": ssha, "yahoo": ysha},
            "pass": abs(ratio_after / ratio_before - 1) > 0.001
                    and stocks_parity < 1e-5 and volume_parity < 1e-12,
        }

    passed = all(source_assertions.values()) and all(r["pass"] for r in split_rows.values()) \
        and all(r["pass"] for r in dividend_rows.values())
    return {
        "schema": "theme_intelligence.corporate_action_basis_audit.v1",
        "lane_f_operation": "theme-intelligence-f-evaluation-and-independent-acceptance-20260919-sol-001",
        "subject": subject,
        "source_assertions": source_assertions,
        "split_witnesses": split_rows,
        "dividend_adjustment_witnesses": dividend_rows,
        "verdict": "US_FIRST_VERTICAL_ADJUSTED_BASIS_PROVEN" if passed else "BASIS_NOT_PROVEN",
        "limitations": [
            "Representative immutable witnesses do not prove every historical corporate action.",
            "This establishes the US first vertical's owner/fallback adjusted basis, not predictive edge.",
            "Future source/basis changes invalidate this receipt and require re-audit.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--subject", default=SUBJECT)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    result = audit(args.repo_root.resolve(), args.subject)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")
    return 0 if result["verdict"] == "US_FIRST_VERTICAL_ADJUSTED_BASIS_PROVEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())