"""Replay one published A-share close against same-revision peer inputs, without writing stores.

Usage: python -m research.cn_prophet_v4.replay_sector_peers <full Macro commit>
The committed search-close cache is the price source for this diagnostic. The
production builder may enrich individual histories. This measures coverage and
disagreement, not subsequent performance or historical decision-time availability.
"""
import argparse
from collections import Counter
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

import pandas as pd

from engine.china_prophet_peer_context import build_context, load_sources


def compare_shelves(board, context):
    """Keep the incumbent's number of slots in each sector; replace only on measured evidence."""
    featured = board["buy"]
    candidates = featured + [
        r for r in board["more_actionable"]
        if r.get("lane_reasons") and set(r["lane_reasons"]) <= {"sector_cap", "featured_cap"}
    ]
    if any(type(r.get("board_rank")) is not int or not r.get("sector") for r in candidates):
        raise ValueError("missing original rank or sector")
    if len({r["board_rank"] for r in candidates}) != len(candidates):
        raise ValueError("ambiguous original rank")
    ordered = sorted(candidates, key=lambda r: r["board_rank"])
    capacity = Counter(r["sector"] for r in featured)
    baseline = {r["ticker"] for r in featured}
    arms = {}
    for arm in ("baseline", "industry", "industry_and_theme", "with_isolated_leaders"):
        selected = set()
        for sector, slots in capacity.items():
            pool = [r["ticker"] for r in ordered if r["sector"] == sector]
            scored = []
            positions = []
            for i, ticker in enumerate(pool):
                row = context[ticker]
                industry = next((g for g in row["groups"] if g["kind"] == "sector"), {})
                if arm == "industry":
                    state = industry.get("state")
                else:
                    state = row["interpretation"]
                # Only measured candidates exchange positions. Covered and uncovered
                # scores never compete, and the incumbent breaks every observed tie.
                if arm == "baseline" or state in {None, "unavailable", "theme_only",
                    "stock_unavailable", "insufficient_coverage", "benchmark_unavailable"}:
                    continue
                priority = 0
                if state in {"stock_falling", "falling_watch", "peers_weakening", "weak_peers"}:
                    priority = -1
                elif state in {"risk_off_leader", "group_leader"}:
                    priority = 1
                elif row["market_tone"] == "on" and state in {"rotation_watch", "emerging_rotation"}:
                    priority = 1
                elif arm == "with_isolated_leaders" and state == "isolated_leader":
                    priority = 1
                positions.append(i)
                scored.append((-priority, i, ticker))
            for i, (_, _, ticker) in zip(positions, sorted(scored)):
                pool[i] = ticker
            selected.update(pool[:slots])
        if arm == "baseline" and selected != baseline:
            raise ValueError("could not reproduce the published featured shelf")
        arms[arm] = {"count": len(selected), "entered": sorted(selected - baseline),
                     "displaced": sorted(baseline - selected)}
    return {"cap_qualified": len(candidates), "arms": arms}


def replay(commit):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("pass the full immutable Macro commit")

    def blob(path):
        return subprocess.check_output(["git", "show", f"{commit}:{path}"])

    def frame(path):
        return pd.read_parquet(BytesIO(blob(path)))

    board = json.loads(blob("site/factordata/china_standouts.json"))
    as_of = board["as_of"]
    closes = frame("data/china_search/closes.parquet")
    bench = frame("data/china/510300.SS.parquet")["close"]
    ledger = frame("data/china_prophet_rank/candidates.parquet")
    rows = ledger[(ledger.stamp_date == as_of) & (ledger.board_definition == board["board_definition"])]
    featured = [r["ticker"] for r in board["buy"]]
    published = [r["ticker"] for lane in ("buy", "more_actionable", "late_or_unfillable", "forming")
                 for r in board[lane]]
    population = sorted(set(rows.ticker) | set(published))
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        for path in ("data/china_sectors/membership.parquet", "data/baskets_china/membership.json",
                     "site/chinasectordata/sector_central.json"):
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob(path))
        groups, central = load_sources(root / "data", root / "site", as_of)
        context = build_context(population, closes, bench, as_of, groups, central)
    def counts(tickers):
        return dict(sorted(Counter(context[t]["interpretation"] for t in tickers).items()))

    return {
        "commit": commit, "session": as_of,
        "board_order": board["ranking"]["ordering"]["effective_order_basis"],
        "declared_universe": board["universe"], "ledger_rows_on_session": len(rows),
        "ledger_only": len(set(rows.ticker) - set(published)),
        "published_missing_from_session_ledger": len(set(published) - set(rows.ticker)),
        "featured": len(featured), "published": len(published),
        "featured_reads": counts(featured), "published_reads": counts(published),
        "features_on_joined_population": counts(population),
        "featured_with_measured_peers": sum(
            any("breadth_pct" in g for g in context[t]["groups"]) for t in featured
        ),
        "fixed_sector_slots": compare_shelves(board, context),
        "examples": [{"ticker": t, **context[t]} for t in featured[:2]],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("commit")
    print(json.dumps(replay(parser.parse_args().commit), ensure_ascii=False, indent=2))
