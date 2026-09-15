"""Ticker<->CIK collision census CLI — the F06-5 (MO-PAID-020) owner.

WHY THIS FILE EXISTS.
``[MO-B F06-5]`` requires a fresh collision census before any single bounded
renderer/CIK-access repair may be admitted (R3). This script is the CLI half
of that pair: it reads the canonical identity owners through the same APIs the
producer uses (``scripts/security_state_producer.py::_read_security_state_identity_rows``),
runs the four classifiers in :mod:`engine.market_ontology.ticker_cik_census`,
writes the receipt JSON to ``--out``, and prints one dated summary line per
class. It exits 0 unconditionally — a census REPORTS, it never fails a
build.

PARQUET I/O LIVES HERE.  The pure classifiers in the engine module never
import pandas (R5); this script is the only place the four parquet artifacts
are read. The live-data test exercises the same reading path on the SAME
files, so the engine module's classifier-output is verified end-to-end here.

USAGE.

    python3 scripts/ticker_cik_collision_census.py --data-dir data \\
        --out /tmp/census.json

The CLI also accepts ``--universe-tickers`` as an optional override; without
it, the CLI enumerates ``data/stocks/`` parquet stems (the stock-library
universe R2 names — see ``_default_universe``; ``site/stockdata`` is
gitignored and never counted, ``data/sector_holdings/`` is filtered out
because its ETF sector-proxy + log stems would leak in as fake tickers,
per PR #2113 issue 4). That fact is asserted in the receipt's
``c4_universe_source`` field.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _today_utc() -> date:
    """Decision-date default — UTC today.

    The census pins INVARIANTS only, never per-ticker counts (R5); the receipt
    still names the date it was computed at so a reader can reconcile the
    live data commit (`git log -1 --format=%h -- data/reference`) with the
    counts it produced.
    """
    return datetime.now(tz=timezone.utc).date()


def _read_parquet_records(path: Path) -> list[dict]:
    """Read a parquet file to list[dict] (R5 — pandas lives here, never in the engine)."""
    import pandas as pd

    return pd.read_parquet(path).to_dict("records")


def _default_universe(data_dir: Path) -> tuple[list[str], str]:
    """Enumerate the C4 universe — the stock-library universe R2 names.

    H3 heal-round (PR #7122): the C4 universe is ``data/stocks/`` ONLY. The
    sector-holdings parquets live under ``data/sector_holdings/`` but those
    files carry ETF sector proxies (XLB/XLC/...) + log tables
    (``history.parquet`` PIT archiver, ``holdings_runs.parquet``) whose
    stems would leak into a receipt as fake tickers. ``build_stock_library``
    filters ``data/sector_holdings/`` by ``SECTOR_NAMES`` for the same
    reason (PR #2113 issue 4); we follow the SAME rule and only enumerate
    ``data/stocks/*.parquet`` — the 245-stock stock-library universe.

    ``site/stockdata/`` is gitignored and is NEVER read here; the returned
    source string asserts that to the receipt reader (R2 / R4).
    """
    d = data_dir / "stocks"
    if not d.is_dir():
        return [], "(empty)"
    stems = sorted({p.stem for p in d.glob("*.parquet")})
    return stems, "data/stocks"


def _allowlist() -> tuple[str, ...]:
    from engine.security_state import SECURITY_STATE_TICKERS

    return tuple(SECURITY_STATE_TICKERS)


def run_census(
    *,
    data_dir: Path,
    decision_date: date,
    universe_tickers: list[str] | None,
) -> dict:
    """Build the canonical receipt (R5).

    Reads the four identity-plane parquets through ``to_dict('records')``
    (matching the producer's shape), enumerates the universe parquets for
    C4, and runs the four classifiers.
    """
    from engine.market_ontology.ticker_cik_census import (
        build_receipt,
        c1_strict_collisions,
        c2_namespace_divergence,
        c3_cik_leg_access_failures,
        c4_renderer_coverage,
    )

    ref = data_dir / "reference"
    alias_rows = _read_parquet_records(ref / "vendor_aliases.parquet")
    security_records = _read_parquet_records(ref / "security_master.parquet")
    issuer_records = _read_parquet_records(ref / "issuer_master.parquet")
    # issuer_migrations + security_migrations are tracked for completeness
    # but the F06-5 census does not enumerate a class over them — the
    # migration row count + a sample id is exposed in the receipt for
    # diagnostic reconciliation.
    try:
        issuer_migration_rows = _read_parquet_records(ref / "issuer_migrations.parquet")
    except FileNotFoundError:
        issuer_migration_rows = []
    try:
        security_migration_rows = _read_parquet_records(ref / "security_migrations.parquet")
    except FileNotFoundError:
        security_migration_rows = []

    if universe_tickers is None:
        uni, source_label = _default_universe(data_dir)
    else:
        uni = sorted(set(universe_tickers))
        source_label = "(caller-supplied)"

    c1 = c1_strict_collisions(
        alias_rows=alias_rows,
        security_records=security_records,
        issuer_records=issuer_records,
        decision_date=decision_date,
    )
    c2 = c2_namespace_divergence(alias_rows=alias_rows, decision_date=decision_date)
    c3, c3_details = c3_cik_leg_access_failures(
        alias_rows=alias_rows,
        security_records=security_records,
        issuer_records=issuer_records,
        decision_date=decision_date,
    )
    c4 = c4_renderer_coverage(
        alias_rows=alias_rows,
        decision_date=decision_date,
        universe_tickers=uni,
        allowlist_tickers=_allowlist(),
    )

    receipt = build_receipt(
        decision_date=decision_date,
        data_dir=str(ref),
        c1=c1,
        c2=c2,
        c3=c3,
        c3_details=c3_details,
        c4=c4,
    )
    receipt["c4_universe_source"] = source_label
    receipt["universe_size"] = len(uni)
    receipt["data_reference_commit"] = _git_head_for(data_dir / "..")
    receipt["migration_rows"] = {
        "issuer": len(issuer_migration_rows),
        "security": len(security_migration_rows),
    }
    return receipt


def _git_head_for(working_tree: Path) -> str | None:
    """Return the short SHA of the latest commit touching data/reference/, or None.

    The spec asks the research note to cite ``git log -1 --format=%h -- data/reference``
    so a reader can reconcile the receipt with the exact parquet bytes that
    produced it. We capture the same SHA here; failures (no git, no commits)
    are swallowed so a non-git working directory does not break the census.
    """
    try:
        import subprocess

        out = subprocess.run(
            ["git", "log", "-1", "--format=%h", "--", "data/reference"],
            cwd=str(working_tree),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        sha = (out.stdout or "").strip()
        return sha or None
    except Exception:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True,
                        help="Path containing reference/ + stocks/ "
                             "(sector_holdings filtered; site/stockdata NOT counted)")
    parser.add_argument("--decision-date", type=str, default=None,
                        help="ISO 8601 decision date (default: UTC today)")
    parser.add_argument("--out", type=Path, required=True,
                        help="Receipt output path (JSON)")
    parser.add_argument("--universe-tickers", nargs="*", default=None,
                        help="Override the C4 universe (default: data/stocks/*.parquet stems; "
                             "245-tick stock-library universe)")
    args = parser.parse_args(argv)

    decision_date = (
        date.fromisoformat(args.decision_date) if args.decision_date else _today_utc()
    )

    receipt = run_census(
        data_dir=args.data_dir,
        decision_date=decision_date,
        universe_tickers=args.universe_tickers,
    )

    # H9 Q-m8 first half: when the data/stocks/ universe dir is absent (e.g.
    # a sparse worktree that did not materialise data/), the CLI must NOT
    # silently emit a 0-coverage receipt. Print a loud line-start warning to
    # stderr instead — the receipt is still written (census REPORTS, never
    # fails a build) but the operator can see the universe was empty.
    if receipt["universe_size"] == 0 and not args.universe_tickers:
        print(
            "::warning title=ticker-cik-collision-census::C4 universe dir "
            "data/stocks absent (size=0); sparse worktree? materialise via "
            "`python3 scripts/worktree_sparse.py add data`",
            file=sys.stderr,
            flush=True,
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str),
                        encoding="utf-8")

    # One dated summary line per code — the spec's R5 "PRINTS the dated counts
    # as receipt lines" requirement. Stderr carries the migration sample so the
    # line budget is met without inflating the JSON.
    for line in receipt["lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())