"""scripts/build_live_flow_baselines.py — per-root daily gross-premium baselines.

Computes EOD-252 daily gross-premium statistics for options roots using the
thetadata_eod store.  Writes a small git-tracked JSON:

    data/live_flow_baselines/baselines.json

Format: {ROOT: {mean, std, n_obs, computed_asof, source_session_start,
                source_session_end}, ...}

computed_asof is the BUILD date (when this run computed the entry).
source_session_start / source_session_end are the first and last dates of the
ACTUAL latest-252 window selected for that entry's statistics, read from the
chronological date index of the store's observed daily values.  They describe
the source data range only — no observation or availability clock is derived
from them, and entries merged from earlier runs are retained verbatim (an old
entry keeps its old source range).

This is a DISPLAY-TIER heuristic denominator (labeled "eod252") for the live
flow feed's unusual-name z-scores.  These are also the "prem baselines" that
enable prem_z for single names (Mag7, memory-storage, etc.) — not just ETFs.
It is NOT a validated edge.  Roots with fewer than MIN_SESSIONS observed daily values
produce no entry (z labeled "none" in the feed).

Store binding: the thetadata_eod store is resolved ONCE per run via
engine.thetadata_store.resolve_thetadata_store(required=True,
purpose="live_flow_baselines"), including configured external stores. An
unresolvable store is refused before any --all scan or output write, instead
of silently producing a merge-only artifact from the wrong checkout path.

Window: statistics cover the latest EOD_WINDOW (252) observed daily values
in chronological order — not the first 252 and not all history.  n_obs
reflects the selected window, and the per-root log line reports that
selected window's source range as `source=<first>..<last>`.

The --poll-universe mode uses the actual consumer configuration and native
universe resolver in the current environment, not a second static root list.

NEVER writes into data/tape_flow — that is a separate, mixed-source store.

Memory safety: each root is processed independently; data is freed after each
root.  The 46GB-pandas-freeze hazard (see memory notes in CLAUDE.md) is
avoided because we stream one root at a time.

Usage:
    # Run for the 22 ETF anchors (default — unchanged behaviour)
    python -m scripts.build_live_flow_baselines

    # Run for the full live-poller universe (Mag7 + memory names + long tail)
    python -m scripts.build_live_flow_baselines --poll-universe

    # Run for specific roots
    python -m scripts.build_live_flow_baselines --roots SPY QQQ KRE NVDA META

    # Run for all roots in the thetadata_eod store
    python -m scripts.build_live_flow_baselines --all

    # Dry run (print results, do not write)
    python -m scripts.build_live_flow_baselines --dry-run
"""
from __future__ import annotations

import argparse
import gc
import json
import logging
import math
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from lib import config  # noqa: E402
from lib.procutil import hard_exit  # noqa: E402

log = logging.getLogger(__name__)

# Minimum observed daily values required to emit a baseline
MIN_SESSIONS = 120

# EOD252 display window: statistics are computed over the latest 252 observed
# daily values (chronologically sorted), never first-252 or all-history.
EOD_WINDOW = 252

# Output path (git-tracked)
BASELINES_PATH = "live_flow_baselines/baselines.json"

# Default ETF anchors (22: 21 from build_tape_flow + DIA)
DEFAULT_ANCHORS = [
    "SPY", "QQQ", "IWM", "GLD", "SLV", "TLT", "HYG", "XLF", "XLE",
    "XLU", "XLK", "XLV", "XLI", "XLB", "XLY", "XLP", "XLRE",
    "KRE", "SMH", "XBI", "ARKK", "DIA",
]

# Chunk size for bounded-memory processing (roots per batch)
CHUNK_SIZE = 25


def bind_store() -> Path:
    """Resolve the canonical store once for each invocation, before output work."""
    from engine.thetadata_store import resolve_thetadata_store

    resolved = resolve_thetadata_store(required=True, purpose="live_flow_baselines")
    if resolved is None:
        raise RuntimeError("baselines: no thetadata store resolved — refusing to build baselines")
    return Path(resolved)


def _store_root() -> Path:
    return bind_store()


def _out_path() -> Path:
    return config.data_dir() / BASELINES_PATH


def _load_existing() -> dict:
    p = _out_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001
        log.warning("baselines: could not read existing %s: %s", p, e)
        return {}


def _all_roots_in_store(store: Path | None = None) -> list[str]:
    """List of roots present in the thetadata_eod/eod/ directory."""
    eod_dir = (store if store is not None else _store_root()) / "eod"
    if not eod_dir.exists():
        return []
    return sorted(d.name for d in eod_dir.iterdir() if d.is_dir())


def _daily_gross_premium(root: str, store: Path | None = None) -> pd.Series | None:
    """Compute per-day gross premium for root from the thetadata_eod store.

    Gross premium per day = sum(close * volume * 100) over all contracts.
    Uses thetadata_store._load_parquets to get the full cross-year EOD frame
    (which already applies the dedup fix).

    Returns a Series indexed by date string "YYYY-MM-DD", or None if insufficient data.
    """
    from engine.thetadata_store import _load_parquets, clear_parquet_cache

    bound_store = store if store is not None else _store_root()
    try:
        eod = _load_parquets("eod", root, years=None, store=str(bound_store))
        if eod is None or eod.empty:
            log.debug("baselines: no EOD data for %s", root)
            return None

        # Normalise columns
        for col in ("close", "volume"):
            if col not in eod.columns:
                log.debug("baselines: missing column %s for %s", col, root)
                return None
            eod[col] = pd.to_numeric(eod[col], errors="coerce")

        # Normalise date
        if "date" not in eod.columns and "timestamp" in eod.columns:
            eod["date"] = pd.to_datetime(eod["timestamp"], errors="coerce").dt.date.astype(str)
        elif "date" in eod.columns:
            eod["date"] = pd.to_datetime(eod["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        else:
            log.debug("baselines: no date column for %s", root)
            return None

        eod = eod.dropna(subset=["date", "close", "volume"])
        eod = eod[eod["close"] > 0]
        if eod.empty:
            return None

        eod["_gross"] = eod["close"] * eod["volume"] * 100.0
        daily = eod.groupby("date")["_gross"].sum()
        daily = daily[daily > 0]
        return daily

    except Exception as e:  # noqa: BLE001
        log.warning("baselines: error loading %s: %s", root, e)
        return None
    finally:
        # This finite builder does not reuse full-year frames across roots.
        # gc.collect alone cannot release the canonical reader's strong refs.
        clear_parquet_cache()


def compute_baseline(root: str, store: Path | None = None) -> dict | None:
    """Compute {mean, std, n_obs, computed_asof, source_session_start,
    source_session_end} for root, or None if insufficient.

    Statistics cover the latest EOD_WINDOW (252) observed daily values in
    chronological order; n_obs reflects that selected window.
    source_session_start/end are the first/last dates of that selected window
    (source data range), distinct from computed_asof (the build date).
    """
    daily = _daily_gross_premium(root, store=store)
    if daily is None or len(daily) < MIN_SESSIONS:
        n = len(daily) if daily is not None else 0
        log.info("baselines: %s — %d sessions < %d minimum — skip", root, n, MIN_SESSIONS)
        return None

    window = daily.sort_index().iloc[-EOD_WINDOW:]
    mean_val = float(np.mean(window.values))
    std_val  = float(np.std(window.values, ddof=1))
    n_obs    = int(len(window))
    asof     = str(date.today())
    src_start = str(window.index[0])
    src_end   = str(window.index[-1])

    log.info("baselines: %s — n_obs=%d mean=%.0f std=%.0f source=%s..%s",
             root, n_obs, mean_val, std_val, src_start, src_end)
    return {
        "mean":         mean_val,
        "std":          std_val,
        "n_obs":        n_obs,
        "computed_asof": asof,
        "source_session_start": src_start,
        "source_session_end": src_end,
    }


def run(roots: list[str], dry_run: bool = False, chunk_size: int = CHUNK_SIZE,
        *, store: Path | None = None, require_source_session: date | None = None) -> dict:
    """Compute baselines for given roots and write/merge into baselines.json.

    FC-R7: processes roots in chunks of chunk_size to bound memory usage.
    Each root's DataFrame is freed after processing (gc.collect per chunk).

    Returns the full updated baselines dict.
    """
    # Canonical binding FIRST (outside the per-root try): a refused store must
    # abort the run before any load/merge/write — never degrade to a
    # merge-only artifact published as healthy.
    bound_store = store if store is not None else bind_store()
    roots = list(dict.fromkeys(root.upper() for root in roots))
    if not roots or chunk_size < 1:
        raise ValueError("baselines: nonempty roots and positive chunk size required")
    existing = _load_existing()
    updated = dict(existing)

    n_ok = n_skip = n_err = 0
    refreshed = {}
    n_roots = len(roots)
    log.info("baselines: processing %d roots in chunks of %d", n_roots, chunk_size)

    for chunk_start in range(0, n_roots, chunk_size):
        chunk = roots[chunk_start: chunk_start + chunk_size]
        log.info("baselines: chunk %d-%d / %d",
                 chunk_start + 1, chunk_start + len(chunk), n_roots)
        for root in chunk:
            root = root.upper()
            try:
                result = compute_baseline(root, store=bound_store)
                if result is None:
                    n_skip += 1
                else:
                    updated[root] = result
                    refreshed[root] = result
                    n_ok += 1
            except Exception as e:  # noqa: BLE001
                log.error("baselines: error for %s: %s", root, e)
                n_err += 1
        # Release memory between chunks
        gc.collect()

    log.info("baselines: done — ok=%d skip=%d err=%d, total_roots=%d",
             n_ok, n_skip, n_err, len(updated))

    # Natural maintenance must not publish a mixed fresh/retained universe.
    # A root skipped this invocation cannot be rescued by its old JSON entry.
    if require_source_session is not None:
        bad = []
        for root in roots:
            entry = refreshed.get(root, {})
            try:
                valid = (
                    MIN_SESSIONS <= entry["n_obs"] <= EOD_WINDOW
                    and math.isfinite(entry["mean"]) and entry["mean"] > 0
                    and math.isfinite(entry["std"]) and entry["std"] > 0
                    and date.fromisoformat(entry["source_session_end"]) == require_source_session
                )
            except (KeyError, TypeError, ValueError):
                valid = False
            if not valid:
                bad.append(root)
        if bad:
            raise RuntimeError("baselines: incomplete current universe; preserving prior artifact: "
                               + ",".join(bad))
        updated = {root: refreshed[root] for root in roots}

    if dry_run:
        log.info("baselines: [DRY RUN] would write %d root entries to %s", len(updated), _out_path())
        return updated

    out_path = _out_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Unique staging file prevents concurrent standalone diagnostics/builds from
    # sharing a partial pathname. Replacement remains atomic for the reader.
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=out_path.parent,
                                         prefix=".baselines-", suffix=".tmp",
                                         delete=False) as fh:
            tmp = Path(fh.name)
            fh.write(json.dumps(updated, indent=2, sort_keys=True, allow_nan=False))
        tmp.replace(out_path)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    log.info("baselines: wrote %d root entries to %s", len(updated), out_path)
    return updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build per-root daily gross-premium baselines from the EOD store"
    )
    root_grp = parser.add_mutually_exclusive_group()
    root_grp.add_argument("--roots", nargs="+", metavar="ROOT",
                          help="Specific roots to compute (e.g. SPY QQQ KRE NVDA META)")
    root_grp.add_argument("--all", action="store_true",
                          help="All roots present in the thetadata_eod/eod/ store")
    root_grp.add_argument("--poll-universe", action="store_true",
                          help=(
                              "Use the actual live-flow configuration and universe resolver"
                          ))
    parser.add_argument("--dry-run", action="store_true",
                        help="Print results without writing")
    parser.add_argument("--require-source-session", type=date.fromisoformat,
                        help="Require every requested root to have current, finite statistics; otherwise preserve output")
    parser.add_argument("--expected-store", type=Path,
                        help="Refuse if the consumer environment resolves a different source store")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE,
                        help=f"Roots per processing chunk (default {CHUNK_SIZE}); "
                             "reduce to lower peak memory on large universes")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Bind the canonical store FIRST: an unresolvable store is a hard refusal
    # before any --all directory scan or output write. All CLI modes then
    # share this invocation's canonical binding.
    try:
        store = bind_store()
        if args.expected_store is not None and store.resolve() != args.expected_store.resolve():
            raise RuntimeError("consumer and daily maintainer resolve different source stores")
    except Exception as e:  # noqa: BLE001
        log.error("baselines: store binding refused: %s", e)
        hard_exit(1)
        return 1

    if args.all:
        roots = _all_roots_in_store(store)
        if not roots:
            log.error("baselines: no roots found in %s", store / "eod")
            hard_exit(1)
            return 1
    elif args.poll_universe:
        # Resolve in THIS environment, exactly as the actual consumer does.
        # Importing these pure helpers does not run a poller cycle.
        from scripts.live_flow_poller import _cfg, _resolve_universe
        roots = _resolve_universe(_cfg())
        log.info("baselines: configured poll universe (%d roots)", len(roots))
    elif args.roots:
        roots = [r.upper() for r in args.roots]
    else:
        roots = DEFAULT_ANCHORS

    log.info("baselines: computing for %d roots, dry_run=%s chunk_size=%d",
             len(roots), args.dry_run, args.chunk_size)
    try:
        run(roots, dry_run=args.dry_run, chunk_size=args.chunk_size, store=store,
            require_source_session=args.require_source_session)
    except Exception as e:  # noqa: BLE001
        log.error("baselines: build refused: %s", e)
        hard_exit(1)
        return 1

    # hard_exit required: parquet reads in _daily_gross_premium via thetadata_store
    # can trigger PyArrow ThreadPool deadlock at interpreter shutdown.
    hard_exit(0)
    return 0  # unreachable but satisfies type checkers


if __name__ == "__main__":
    sys.exit(main())
