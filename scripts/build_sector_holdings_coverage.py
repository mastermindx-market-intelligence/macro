"""Sector holdings coverage feed (sector_holdings.coverage.v1) — Options R1 W2B, section L-W2B-MACRO.

Sector Central lists a fund's top holdings but never says what share of the
fund they are, because the three natural numbers have three DIFFERENT
denominators: how many names are listed (count coverage), what share of the
fund's weight they carry (fund-weight coverage), and how concentrated the top
of the list is (top-three concentration, of the fund and of the listed
sample). This emitter produces that feed from the committed
data/sector_holdings parquet store for the Terminal's strict reader — ANY
deviation from the output contract makes the reader drop the whole file, so
tests/test_sector_holdings_coverage.py re-checks every rule of it.

The store keeps only the TOP 20 BY WEIGHT per fund, so the fund's total
holding count is unknown today. It is emitted as ``null`` with
``total_unknown: true`` — never 0 (which would read as "the fund holds
nothing") and never the listed count or 20 (which would read as "the fund
holds exactly these"). When a real total source appears, pass ``total=`` and
the same fields turn numeric.

The build_sector_central hook calls emit_holdings_coverage_additive(), which
is additive and never fatal: any failure logs at warning and returns None.

Run: python -m scripts.build_sector_holdings_coverage --out <path>
(In the sparse session worktree the dry run MUST pass --out; the default
writes under site/, which this checkout never writes.)
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
# Unconditional repo-root pin (tests/test_check_script_import_pinning.py): a guarded insert is
# not a pin, because a foreign package ahead of an already-present root still wins.
sys.path.insert(0, str(ROOT))

from lib import config, nyse_calendar, store  # noqa: E402

log = logging.getLogger(__name__)

SCHEMA = "sector_holdings.coverage.v1"
SOURCE = "sector_holdings parquet store (issuer top 20 by weight)"

TICKER = re.compile(r"^[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)?$")
MAX_LISTED = 60


def _sector_funds() -> list[str]:
    """The collector's fund list, read from the same place the collector reads it
    (collectors/sector_holdings.py iterates config.load()["sponsors"]["sector_funds"])."""
    return [str(f) for f in config.load()["sponsors"]["sector_funds"]]


FUNDS: list[str] = _sector_funds()


def load_snapshots(funds: Sequence[str]) -> dict[str, pd.DataFrame | None]:
    """Exactly the store read the collector's latest_top10 performs, per fund:
    store.read("sector_holdings", fund). The frames stay RAW (full history,
    index = as_of datetime, columns ticker/name/weight_pct/rank) — the
    latest-date slice is coverage_for_fund's job. A fund whose read is absent
    or raises maps to None (logged at warning), never a raise."""
    out: dict[str, pd.DataFrame | None] = {}
    for fund in funds:
        try:
            snap = store.read("sector_holdings", fund)
        except Exception as e:  # noqa: BLE001 — one bad file must not sink the feed
            log.warning("holdings coverage: %s store read failed: %s", fund, e)
            out[fund] = None
            continue
        if snap is None:
            log.warning("holdings coverage: %s has no stored snapshot", fund)
        out[fund] = snap
    return out


def coverage_for_fund(fund: str, snapshot: pd.DataFrame | None, *, asof: date,
                      total: int | None = None) -> dict:
    """One fund's coverage block. Pure: reads the frame it is handed, never the
    store or the clock. ``total`` is the fund's total holding count when a
    source knows it; None (unknown) is today's store-wide truth."""
    if snapshot is None or snapshot.empty:
        return {"fund": fund, "as_of": asof.isoformat(), "n_holdings_total": None,
                "total_unknown": True, "listed": [],
                "coverage": {"count": {"listed": 0, "total": None}, "weight_pct": 0.0,
                             "concentration": {"top3_of_fund_pct": None,
                                               "top3_of_sample_pct": None}}}
    idx = pd.to_datetime(snapshot.index)
    last = idx.max()
    rows = snapshot.loc[idx == last]
    tickers = rows["ticker"].astype(str).str.strip().str.upper()
    weights = pd.to_numeric(rows["weight_pct"], errors="coerce").astype(float)
    # The ticker gate is part of `keep`: CASH_USD-style rows, blanks and
    # non-symbols are dropped here, before any ranking happens.
    keep = (tickers.map(lambda t: bool(TICKER.fullmatch(t)))
            & np.isfinite(weights) & (weights >= 0))
    dropped = int((~keep).sum())
    if dropped:
        log.info("holdings coverage: %s dropped %d row(s) (non-ticker or bad weight)",
                 fund, dropped)
    work = (pd.DataFrame({"ticker": tickers[keep].to_numpy(),
                          "weight_pct": weights[keep].to_numpy()})
            .sort_values("weight_pct", ascending=False)
            .drop_duplicates("ticker", keep="first")  # keep the larger weight
            .sort_values(["weight_pct", "ticker"], ascending=[False, True],
                         kind="mergesort")
            .head(MAX_LISTED))
    # rank = position + 1 — never the stored rank column, which has gaps after drops
    listed = [{"ticker": str(r.ticker), "weight_pct": round(float(r.weight_pct), 2),
               "rank": n} for n, r in enumerate(work.itertuples(index=False), start=1)]
    weight = round(sum(row["weight_pct"] for row in listed), 2)
    if total is not None and total < len(listed):
        log.warning("holdings coverage: %s total=%d is below the %d listed rows "
                    "— treating as unknown", fund, total, len(listed))
        total = None
    # total stays None when unknown — the listed count (and the store's
    # top-20 cap) is never a substitute for the fund's real total.
    if len(listed) < 3:
        top3 = None
        top3_share = None
    else:
        top3 = round(sum(row["weight_pct"] for row in listed[:3]), 2)
        top3_share = None if weight == 0 else round(top3 / weight * 100, 2)
    return {"fund": fund, "as_of": last.date().isoformat(),
            "n_holdings_total": total, "total_unknown": total is None,
            "listed": listed,
            "coverage": {"count": {"listed": len(listed), "total": total},
                         "weight_pct": weight,
                         "concentration": {"top3_of_fund_pct": top3,
                                           "top3_of_sample_pct": top3_share}}}


def build_holdings_coverage(snapshots: Mapping[str, pd.DataFrame | None], *,
                            funds: Sequence[str] = FUNDS,
                            asof: date | None = None,
                            source: str = SOURCE) -> dict:
    """The whole feed: meta + one block per fund in FUNDS order. meta.asOf is
    the max of the explicitly given date (if any) and every fund's snapshot
    date; with no dated snapshot anywhere it falls back to the calendar's
    expected last session. Empty funds take meta.asOf as their as_of, so every
    fund's as_of is <= meta.asOf by construction."""
    fund_dates: dict[str, date | None] = {}
    for fund in funds:
        snap = snapshots.get(fund)
        fund_dates[fund] = (None if snap is None or snap.empty
                            else pd.to_datetime(snap.index).max().date())
    candidates = [d for d in fund_dates.values() if d is not None]
    if asof is not None:
        candidates.append(asof)
    meta_asof = max(candidates) if candidates else nyse_calendar.expected_last_session()
    out_funds = [coverage_for_fund(fund, snapshots.get(fund),
                                   asof=fund_dates[fund] or meta_asof)
                 for fund in funds]
    return {"meta": {"schema": SCHEMA, "asOf": meta_asof.isoformat(), "source": source},
            "funds": out_funds}


def write_holdings_coverage(path: Path, feed: dict) -> None:
    """Persist the feed exactly the way the Terminal reader expects it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(feed, separators=(",", ":"), ensure_ascii=False),
                    encoding="utf-8")


def emit_holdings_coverage_additive(fdir: Path, *, snapshots_loader=None,
                                    log=None) -> Path | None:
    """Additive hook target for build_sector_central: build + write the feed
    under *fdir*, or return None on ANY failure. Never raises."""
    lg = log if log is not None else logging.getLogger(__name__)
    loader = snapshots_loader if snapshots_loader is not None else (
        lambda: load_snapshots(FUNDS))
    try:
        feed = build_holdings_coverage(loader())
        out = Path(fdir) / "sector_holdings_coverage.json"
        write_holdings_coverage(out, feed)
        return out
    except Exception as e:  # noqa: BLE001 — a failed side feed must never break the host build
        lg.warning("holdings coverage: feed skipped: %s", e)
        return None


def _fmt(v) -> str:
    return "null" if v is None else str(v)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit the sector holdings coverage feed (Options R1 W2B).")
    default_out = ROOT / config.load()["storage"]["site_dir"] / "sectordata" / (
        "sector_holdings_coverage.json")
    parser.add_argument("--out", default=str(default_out),
                        help="output path for sector_holdings_coverage.json")
    args = parser.parse_args(argv)
    try:
        feed = build_holdings_coverage(load_snapshots(FUNDS))
        write_holdings_coverage(Path(args.out), feed)
    except Exception as e:  # noqa: BLE001 — same fail-soft contract as the hook
        log.error("holdings coverage: emit failed: %s", e)
        return 1
    for f in feed["funds"]:
        c = f["coverage"]
        total = "unknown" if f["total_unknown"] else f["n_holdings_total"]
        print(f"{f['fund']} as_of={f['as_of']} listed={c['count']['listed']} "
              f"weight={c['weight_pct']}% "
              f"top3={_fmt(c['concentration']['top3_of_fund_pct'])}% total={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
