#!/usr/bin/env python3
"""Repair the dated GEX snapshots that carry the 2026-08-01 defects.

Why this exists
---------------
Two defects shipped in `compute_gex` and were repaired on 2026-08-01:

  1. `gamma_flip` was the zero-crossing of a running sum across the STRIKE LADDER, not
     the zero-gamma SPOT (macro #4189). SPY published 275.00 against a spot of 741.69.
  2. A degenerate quote (`iv` at the solver floor, where Black-Scholes gamma diverges)
     could dominate `net_gex_bn` (macro #4194). SPY published -$1,129bn on 2026-06-26.

Re-running the nightly repaired the LIVE artifacts, but `gex_history/{ROOT}/{DATE}.json`
is keyed by the payload's own `asof`, so only the current session's snapshot was rewritten.
Every earlier snapshot still carries both defects, and the Exposure desk's dated replay
reads them as fact.

Neither defect is repairable from the stored rows. The flip needs the chain re-priced on
a spot grid — reconstructing it from `by_strike` is exactly the unsound method that was
retired — so this re-runs `compute_gex` per (root, date) against the ThetaData store.

Measured before running (2026-08-01): 450 snapshots across 47 roots, of which 102 carry
a flip more than 25% from spot. That is *structurally impossible* for the repaired
estimator, which searches a ±25% grid — so those 102 are definitively contaminated, and
the true count is higher (a wrong flip inside the band looks perfectly ordinary).

What it preserves
-----------------
`history` is attached by a separate step in the nightly and is NOT recomputed here, so
it is carried over from the existing snapshot. Only the fields `compute_gex` owns are
replaced. A snapshot that cannot be recomputed (chain missing for that session) is left
exactly as it was and counted — never half-written, never deleted.

Usage
-----
    # dry run: report what WOULD change, touch nothing
    python -m scripts.repair_gex_history

    # rewrite locally, then upload the repaired snapshots to R2
    python -m scripts.repair_gex_history --apply --publish
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import date as calendar_date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.options_hub import compute_gex  # noqa: E402
from engine.thetadata_store import store_root  # noqa: E402

log = logging.getLogger("gex_history_repair")

REPO = Path(__file__).resolve().parent.parent
HIST_DIR = REPO / "data" / "live_flow_out" / "options_hub" / "gex_history"
R2_PREFIX = "options_hub/gex_history/"

#: Fields `compute_gex` owns. Everything else in the snapshot is preserved as-is —
#: notably `history`, which a separate nightly step attaches and this script cannot
#: reproduce.
_RECOMPUTED = (
    "spot_ref", "net_gex_bn", "gamma_flip", "profile", "call_wall", "put_wall",
    "by_strike", "by_strike_full_n", "by_delta", "by_delta_full_n",
    "by_expiry", "convention", "coverage", "schema",
    "net_gex_known_bn", "exposure_projection",
)

#: A flip further than this from spot cannot come from the repaired estimator, which
#: searches a ±25% grid. Used only to REPORT contamination, never to filter what gets
#: recomputed — a wrong flip inside the band is just as wrong and just as invisible.
_IMPOSSIBLE_PCT = 0.25


def _read_year(tier: str, root: str, year: int, store) -> pd.DataFrame:
    p = store_root(store) / tier / root.upper() / f"{year}.parquet"
    if not p.exists():
        return pd.DataFrame()
    try:
        return pd.read_parquet(p)
    except Exception as exc:  # noqa: BLE001
        log.warning("repair: unreadable %s — %s", p, exc)
        return pd.DataFrame()


def _norm_dates(df: pd.DataFrame, *, preserve_expiration: bool = False) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    for c in (("date",) if preserve_expiration else ("date", "expiration")):
        if c in out.columns:
            out[c] = pd.to_datetime(out[c], errors="coerce").dt.date.astype(str)
    return out


def repair_root(root: str, store, *, apply: bool, source_date: str | None = None,
                exposure_context: dict | None = None) -> dict:
    """Recompute every dated snapshot for one root. Returns a per-root tally."""
    root_dir = HIST_DIR / root
    snaps = sorted(p for p in root_dir.glob("*.json") if p.name != "dates.json")
    if source_date is not None:
        calendar_date.fromisoformat(source_date)
        snaps = [p for p in snaps if p.stem == source_date]
    if exposure_context is not None:
        # This repair is a full native-book recomputation, never a selected-window
        # substitute. The incumbent loader has already bound any file descriptors.
        if (source_date is None or exposure_context.get("root") != root
                or (exposure_context.get("clocks") or {}).get("source_session") != source_date
                or "_projection_inputs" in exposure_context or "source_inputs" in exposure_context):
            raise ValueError("Archive context requires one matching full native source session")
    tally = {"root": root, "n": len(snaps), "changed": 0, "impossible": 0,
             "skipped": 0, "paths": []}
    if not snaps:
        return tally

    years = sorted({int(p.stem[:4]) for p in snaps})
    # Greeks and OI load ONCE per root — the expensive part is the parquet read, and a
    # root's snapshots all live in the same year or two.
    greeks = _norm_dates(pd.concat(
        [_read_year("greeks", root, y, store) for y in years], ignore_index=True,
    ), preserve_expiration=exposure_context is not None) if years else pd.DataFrame()
    oi_all = _norm_dates(pd.concat(
        [_read_year("oi", root, y, store) for y in years], ignore_index=True,
    ), preserve_expiration=exposure_context is not None) if years else pd.DataFrame()

    if greeks.empty or oi_all.empty:
        tally["skipped"] = len(snaps)
        return tally

    for path in snaps:
        date = path.stem
        try:
            old = json.loads(path.read_text())
        except Exception:  # noqa: BLE001
            tally["skipped"] += 1
            continue
        if old.get("root") != root or old.get("asof") != date:
            tally["skipped"] += 1
            continue
        previous_projection = old.get("exposure_projection")
        if (exposure_context is None and isinstance(previous_projection, dict)
                and previous_projection.get("kind") in {"dated_provider_approximation", "modeled_exposure"}):
            # Recomputing legacy math is not permission to erase or reuse a
            # qualified receipt. Supply its matching explicit native context.
            tally["skipped"] += 1
            continue

        s, f = old.get("spot_ref"), old.get("gamma_flip")
        if isinstance(s, (int, float)) and isinstance(f, (int, float)) and s:
            if abs(f - s) / s > _IMPOSSIBLE_PCT:
                tally["impossible"] += 1

        g = greeks[greeks["date"] == date]
        o = oi_all[oi_all["date"] == date]
        if g.empty or o.empty:
            # Leave it exactly as it was. A snapshot we cannot recompute is not one we
            # should guess at, and deleting it would silently shorten the replay index.
            tally["skipped"] += 1
            continue

        if exposure_context is not None:
            from engine.options_exposure_projection import compose_native_exposure_context, exposure_input_digest
            if exposure_input_digest(g, o, date, root) != exposure_context.get("input_sha256"):
                raise ValueError("Archive source rows do not match explicit exposure context")
            composed = compose_native_exposure_context(g, o, date, root, context=exposure_context)
            fresh = compute_gex(g, o, date, root, exposure_context=composed)
        else:
            fresh = compute_gex(g, o, date, root)
        if not fresh.get("by_strike"):
            tally["skipped"] += 1
            continue

        new = dict(old)
        for k in _RECOMPUTED:
            if k in fresh:
                new[k] = fresh[k]
        # Include preserved history/other legacy fields in the same whole-event
        # transport guard as the nightly. No contract or denominator truncation.
        from engine.options_exposure_projection import fit_gex_transport
        fits, new = fit_gex_transport(new)
        if not fits:
            tally["skipped"] += 1
            continue

        if new == old:
            continue
        tally["changed"] += 1
        tally["paths"].append(path)
        if apply:
            from scripts.build_options_hub_nightly import _write_json
            _write_json(path, new)

    return tally


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--roots", nargs="+", metavar="ROOT",
                    help="limit to these roots (default: every root in the archive)")
    ap.add_argument("--apply", action="store_true",
                    help="rewrite the snapshots (default is a dry run)")
    ap.add_argument("--publish", action="store_true", help="upload repaired snapshots to R2")
    ap.add_argument("--theta-store", default=None, metavar="PATH")
    ap.add_argument("--date", default=None, metavar="YYYY-MM-DD",
                    help="repair only this existing dated archive; never writes current boards")
    ap.add_argument("--exposure-context", default=None, metavar="JSON",
                    help="explicit full native-book receipt bundle; requires --date and --roots")
    args = ap.parse_args(argv)
    from scripts.build_options_hub_nightly import load_exposure_contexts
    contexts = load_exposure_contexts(args.exposure_context)
    if args.date is not None:
        calendar_date.fromisoformat(args.date)
    if args.exposure_context and (not args.date or not args.roots):
        ap.error("--exposure-context requires explicit --date and --roots")
    if any(root.upper() not in contexts for root in (args.roots or [])) and args.exposure_context:
        ap.error("every selected root requires its own exposure context")

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    store = args.theta_store or os.environ.get("THETADATA_STORE")

    if not HIST_DIR.exists():
        log.error("repair: no archive at %s", HIST_DIR)
        return 1
    roots = ([r.upper() for r in args.roots] if args.roots
             else sorted(p.name for p in HIST_DIR.iterdir() if p.is_dir()))

    log.info("repair: %d roots, apply=%s, store=%s", len(roots), args.apply, store)
    totals = {"n": 0, "changed": 0, "impossible": 0, "skipped": 0}
    repaired: list[tuple[str, Path]] = []
    failures = 0

    for root in roots:
        t0 = time.time()
        try:
            t = repair_root(root, store, apply=args.apply, source_date=args.date,
                            exposure_context=contexts.get(root))
        except Exception as exc:  # noqa: BLE001
            log.warning("repair: %s FAILED — %s", root, exc)
            failures += 1
            continue
        for k in totals:
            totals[k] += t[k]
        for p in t["paths"]:
            repaired.append((root, p))
        if t["changed"] or t["impossible"]:
            log.info("repair: %-6s %d snapshots · %d changed · %d were impossible · "
                     "%d skipped (%.1fs)",
                     root, t["n"], t["changed"], t["impossible"], t["skipped"],
                     time.time() - t0)

    log.info("repair: %s — %d snapshots, %d changed, %d carried an impossible flip, "
             "%d skipped (no chain for that session)",
             "APPLIED" if args.apply else "DRY RUN",
             totals["n"], totals["changed"], totals["impossible"], totals["skipped"])

    if args.publish and args.apply and repaired:
        _publish(repaired, store=store)
    elif args.publish and not args.apply:
        log.warning("repair: --publish ignored on a dry run")
    return 1 if failures else 0


def _publish(repaired: list[tuple[str, Path]], *, store=None) -> None:
    try:
        from scripts.build_options_hub_nightly import _r2_client, _upload_r2, publish_gex_history_index
    except Exception as exc:  # noqa: BLE001
        log.warning("repair: publish unavailable — %s", exc)
        return
    s3 = _r2_client()
    bucket = os.environ.get("R2_BUCKET")
    if s3 is None or not bucket:
        log.warning("repair: R2 creds absent — snapshots repaired locally only")
        return
    ok = 0
    published: dict[str, list[str]] = {}
    for root, path in repaired:
        if _upload_r2(s3, bucket, path, f"{R2_PREFIX}{root}/{path.name}"):
            ok += 1
            published.setdefault(root, []).append(path.stem)
    # Only dated objects and their truthful LIST-derived index. Zero heal budget
    # prevents unrelated archive writes; current gex/vol/boards are never touched.
    for root, days in published.items():
        publish_gex_history_index(root, max(days), store, None, HIST_DIR.parent,
                                  s3, bucket, heal_budget=0)
    log.info("repair: published %d/%d repaired snapshots to R2", ok, len(repaired))


if __name__ == "__main__":
    raise SystemExit(main())
