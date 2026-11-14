"""Publish the description-only trough read from the incumbent company universe."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd  # noqa: E402

from engine.trough_read import ENGINE_REF, stock_read  # noqa: E402
from lib.nyse_calendar import expected_last_session, is_session  # noqa: E402


def company_population():
    # Same company-case input population and price precedence, not a basket subset.
    # Lazy import keeps the pure emitter/test path free of stock-library runtime.
    from scripts.build_stock_library import universe, universe_sources

    population = universe()
    return [row for row in population if row[4] != "ETF / macro"], universe_sources()


def build(*, population=None, sources=None, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    expected = pd.Timestamp(expected_last_session(now))
    if population is None:
        population, sources = company_population()
    rows = {}
    stale = False
    for ticker, close, _high, _name, sector in population:
        close = close.copy()
        close.index = pd.to_datetime(close.index)
        close = close.loc[close.index <= expected].dropna()
        close = close.loc[[is_session(d.date()) for d in close.index]]
        if close.empty:
            stale = True
            continue
        row = stock_read(close, group_id=sector or None, group_name=sector or "")
        # A stale ticker must never masquerade as a current read: unavailable
        # rows retain bar dates but null their states. Other current names survive.
        if row["as_of"] != str(expected.date()):
            stale = True
            for tf in row["timeframes"]:
                tf.update(available=False, washed_out=None, turned_up=None, d=None)
                tf["components"] = dict.fromkeys(tf["components"])
            row["own_history"] = None
        rows[ticker] = row
    known = [row["known_ts"] for row in rows.values() if row["known_ts"]]
    # Missing population stores are explicit and fail closed for the whole read.
    incomplete = bool(sources is not None and not sources.get("complete", False))
    return {"schema": "prophet.trough_read/v1", "as_of": str(expected.date()),
            "built_at": now.astimezone(timezone.utc).isoformat(),
            "known_ts": max(known) if known else None, "engine_ref": ENGINE_REF,
            "status": "unavailable" if not rows or incomplete else "stale" if stale else "ok",
            "tickers": rows}


def validate(payload: dict) -> None:
    from jsonschema import Draft202012Validator

    schema = json.loads((_REPO_ROOT / "contracts/prophet/trough_read.v1.schema.json").read_text())
    Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(payload)


def publish(payload: dict, target: Path) -> None:
    validate(payload)
    body = json.dumps(payload, indent=2, allow_nan=False) + "\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise ValueError("refusing symlinked trough output")
    temporary = target.with_suffix(".json.tmp")
    if temporary.is_symlink():
        raise ValueError("refusing symlinked temporary output")
    temporary.write_text(body)
    os.replace(temporary, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=_REPO_ROOT / "site/prophet/trough_read.json")
    parser.add_argument("--as-of", help="Completed-session cutoff (dry runs)")
    args = parser.parse_args()
    now = (datetime.fromisoformat(args.as_of + "T23:59:59+00:00")
           if args.as_of else datetime.now(timezone.utc))
    payload = build(now=now)
    publish(payload, args.output)
    sample = next(iter(payload["tickers"].items()), None)
    if sample:
        ticker, row = sample
        row = {**row, "own_history": ({k: v for k, v in row["own_history"].items() if k != "past"}
                                     if row["own_history"] else None)}
        sample = {"ticker": ticker, **row}
    print(json.dumps({"tickers": len(payload["tickers"]), "as_of": payload["as_of"],
                      "status": payload["status"], "sample": sample}))


if __name__ == "__main__":
    main()
