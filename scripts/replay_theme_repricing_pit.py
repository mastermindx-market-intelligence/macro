"""Replay Finviz repricing breadth with PIT membership and Massive price history.

Read-only research harness. It creates no lifecycle, signal, grader or publication plane.
By default it writes nothing: JSON goes to stdout. --output is an explicit research export.

The whole-market Massive store is raw/unadjusted. The only split repair used here is the
existing scripts.replay_standout_pipeline.split_adjust helper. The loader truncates the raw
series at the latest replay date before repair; later data cannot enter this run.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.massive_stock_day import (  # noqa: E402
    StaleLocalMirrorError,
    check_local_mirror_freshness,
)
from engine import theme_repricing_pit as pit  # noqa: E402
from engine.theme_graph import local_sources  # noqa: E402
from lib import config  # noqa: E402
from lib.massive_ticker import artifact_relative_path  # noqa: E402
from scripts.replay_standout_pipeline import split_adjust  # noqa: E402


def _read_history(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("asof") and isinstance(row.get("subsectors"), dict):
            rows.append(row)
    return sorted(rows, key=lambda row: str(row["asof"]))


class MassivePriceLoader:
    """Cached split-adjusted close reader bounded by the replay's latest date."""

    def __init__(self, store: Path, max_asof: str) -> None:
        self.store = Path(store)
        self.max_asof = pd.Timestamp(max_asof)
        self._cache: dict[str, pd.Series | None] = {}

    def __call__(self, ticker: str) -> pd.Series | None:
        if ticker in self._cache:
            return self._cache[ticker]
        try:
            path = self.store / artifact_relative_path(ticker)
            if not path.exists():
                self._cache[ticker] = None
                return None
            frame = pd.read_parquet(path, columns=["close"])
            if "close" not in frame.columns:
                self._cache[ticker] = None
                return None
            raw = frame["close"].dropna().sort_index()
            raw.index = pd.DatetimeIndex(raw.index)
            if raw.index.tz is not None:
                raw.index = raw.index.tz_localize(None)
            raw = raw.loc[raw.index <= self.max_asof]
            out = split_adjust(raw) if len(raw) else None
        except Exception:
            out = None
        self._cache[ticker] = out
        return out


def _shape_counts(context: dict) -> dict[str, int]:
    return dict(sorted(Counter(
        row.get("shape") or "unknown"
        for row in ((context.get("repricing") or {}).get("subthemes") or [])
    ).items()))


def _theme_state_counts(context: dict) -> dict[str, int]:
    return dict(sorted(Counter(
        row.get("state") or "unknown"
        for row in ((context.get("repricing") or {}).get("themes") or [])
    ).items()))


def _slim(context: dict) -> dict:
    rep = context.get("repricing") or {}
    return {
        "asof": context.get("asof"),
        "membership": context.get("membership"),
        "prices": context.get("prices"),
        "coverage": context.get("coverage"),
        "shape_counts": _shape_counts(context),
        "theme_state_counts": _theme_state_counts(context),
        "n_themes": rep.get("n_themes"),
        "n_subthemes": rep.get("n_subthemes"),
    }


def replay(
    *,
    root: Path,
    store: Path,
    asof: str | None = None,
    tail: int = 1,
    full: bool = False,
    allow_stale: bool = False,
) -> dict:
    perf_path = root / "data/themes_heatmap/subsector_perf_history.jsonl"
    history = _read_history(perf_path)
    if asof:
        history = [row for row in history if str(row.get("asof")) == asof]
    elif tail > 0:
        history = history[-tail:]
    if not history:
        raise pit.ReplayRefusal(
            f"no exact Finviz subsector history rows selected from {perf_path}"
        )

    if not store.exists() or not any(store.rglob("*.parquet")):
        raise pit.ReplayRefusal(
            f"Massive price store unavailable at {store}; restore the canonical R2 mirror "
            "before claiming a real historical replay"
        )
    check_local_mirror_freshness(
        store,
        entrypoint="scripts/replay_theme_repricing_pit.py",
        allow_stale=allow_stale,
    )

    ladder = local_sources.load_finviz_ladder(
        seed_path=root / local_sources.SEED_TREE_FILE,
        history_path=root / local_sources.TREE_HISTORY_FILE,
        live_tree_path=None,
    )
    if not ladder.vintages:
        raise pit.ReplayRefusal("Finviz structure vintage ladder is empty")

    max_asof = max(str(row["asof"]) for row in history)
    loader = MassivePriceLoader(store, max_asof)
    results = []
    for row in history:
        context = pit.build_pit_context(
            ladder=ladder,
            asof=row["asof"],
            subsector_perf=row["subsectors"],
            close_loader=loader,
            price_source="data/massive_stock_day",
            price_basis="raw_close_split_adjusted_price_return",
        )
        results.append(context if full else _slim(context))

    return {
        "schema": "theme_repricing_pit_replay.v1",
        "authority": dict(pit.AUTHORITY),
        "source": {
            "membership": local_sources.TREE_HISTORY_FILE,
            "subsector_perf": str(perf_path.relative_to(root)),
            "member_prices": "data/massive_stock_day",
            "split_repair": "scripts.replay_standout_pipeline.split_adjust",
        },
        "n_replay_dates": len(results),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay Finviz repricing breadth with PIT membership."
    )
    parser.add_argument("--asof", help="Exact archived Finviz session date (YYYY-MM-DD).")
    parser.add_argument("--tail", type=int, default=1, help="Replay last N archived dates.")
    parser.add_argument("--full", action="store_true", help="Include full subtheme contexts.")
    parser.add_argument("--allow-stale", action="store_true",
                        help="Explicit research override for a stale local Massive mirror.")
    parser.add_argument("--massive-dir", type=Path)
    parser.add_argument("--output", type=Path, help="Optional research JSON output path.")
    args = parser.parse_args(argv)

    root = config.ROOT
    store = args.massive_dir or (config.data_dir() / "massive_stock_day")
    try:
        result = replay(
            root=root,
            store=store,
            asof=args.asof,
            tail=max(1, args.tail),
            full=args.full,
            allow_stale=args.allow_stale,
        )
    except (pit.ReplayRefusal, StaleLocalMirrorError) as exc:
        print(f"theme repricing PIT replay refused: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
