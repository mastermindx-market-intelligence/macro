"""Build the Sector Intelligence rotation read — one descriptive weekly panel.

The rotation read answers "which house baskets are seeing their breadth improve
or deteriorate, and for how long", on TODAY'S roster. It is a pure projection of
the committed weekly fixed-set breadth history
(``data/breadth/history/basket_breadth_weekly_current.parquet``) joined to
``data/baskets/membership.json``; it computes no new measure, tunes nothing and
forecasts nothing.

Description only; not a forecast.

Vintage rule: the panel is pinned to the last COMPLETED weekly close in its
input history (a date with no NYSE session after it through its Mon-Sun week's
Sunday — calendar only, never the wall clock). The freshness gate
(``scripts/check_sector_intelligence_freshness.check_rotation_read``) binds the
written ``as_of`` to that same completed close, so a stale history can never be
presented as a current read.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine import group_breadth_history as gbh  # noqa: E402
from engine.us_basket_turn import active_members  # noqa: E402
from lib import market_session  # noqa: E402
# The calendar vintage rule lives in the freshness checker, which owns the gate; the
# builder uses the same functions so the written as_of and the check cannot diverge.
# (The checker never imports this builder, so its import closure stays unchanged.)
from scripts.check_sector_intelligence_freshness import (  # noqa: E402,F401
    ROTATION_READ_SCHEMA as SCHEMA,
    completed_weekly_closes_between,
    is_completed_weekly_close,
    last_completed_weekly_close,
)

log = logging.getLogger("build_rotation_read")

OUT = ROOT / "site/sectordata/rotation_read.json"
COPY = [
    "Breadth change inside the group on today's roster. Description only; not a forecast.",
]
# stale_rule recorded in data/breadth/history/group_breadth_weekly_current_live.meta.json
# (written by scripts/extend_group_breadth_weekly.py):
# "label stale at two or more completed weekly closes behind the latest session"
STALE_WEEKS = 2

HIST_RELPATH = "data/breadth/history/basket_breadth_weekly_current.parquet"
MEMBERSHIP_RELPATH = "data/baskets/membership.json"

# Exact row field order of every groups[] entry.
ROW_FIELDS = (
    "group_id", "family", "name", "parent", "as_of", "status",
    "unavailable_reason", "n_members", "n_counted", "pct_above_200",
    "chg_13w", "chg_26w", "direction", "run_weeks", "rank_13w", "n_ranked",
)
# Engine columns the projection reads (engine/group_breadth_history.weekly_fixed_set).
_HIST_COLUMNS = (
    "date", "group", "n_has_200", "pct_above_200",
    "fix_chg_pct_above_200_13w", "state_fix_chg_pct_above_200_13w",
    "run_fix_chg_pct_above_200_13w", "fix_chg_pct_above_200_26w",
)
_MEASURE_FIELDS = (
    "pct_above_200", "chg_13w", "chg_26w", "direction", "run_weeks",
    "rank_13w", "n_ranked",
)


def _missing(value) -> bool:
    return value is None or bool(pd.isna(value))


def _family(group_id: str) -> str:
    return "sector" if group_id.startswith("us_sector_") else "theme"


def build(hist: pd.DataFrame | None, membership: dict | None,
          now: datetime) -> dict | None:
    """Project one rotation-read payload. Pure: explicit inputs, no file reads.

    Returns None (the caller must not write a file) when the history is
    None/empty, the membership is None, or no input date is a completed weekly
    close.
    """
    if hist is None or membership is None or len(hist) == 0:
        return None
    # Schema drift is not a data verdict: a history missing an engine column is
    # not projected at all (no file), rather than published as rows that look like
    # too_few_members / no_history.
    if not set(_HIST_COLUMNS) <= set(hist.columns):
        log.warning("rotation read: history lacks columns %s",
                    sorted(set(_HIST_COLUMNS) - set(hist.columns)))
        return None
    hist = hist.assign(date=pd.to_datetime(hist["date"]).dt.normalize())
    as_of = last_completed_weekly_close(hist["date"].unique())
    if as_of is None:
        return None

    latest = market_session.expected_session("US", now)
    behind = completed_weekly_closes_between(as_of, latest)
    top_status = "stale" if behind >= STALE_WEEKS else "ok"

    baskets = membership.get("baskets") or {}
    week = hist.loc[hist["date"] == pd.Timestamp(as_of)]
    by_group = {
        str(row["group"]): row
        for _, row in week.drop_duplicates("group", keep="last").iterrows()
    }

    ordered = sorted(baskets, key=lambda gid: (0 if _family(gid) == "sector" else 1, gid))
    groups: list[dict] = []
    for gid in ordered:
        basket = baskets[gid]
        row = {
            "group_id": gid,
            "family": _family(gid),
            "name": basket.get("name"),
            "parent": basket.get("parent"),
            "as_of": as_of.isoformat(),
            "status": "ok",
            "unavailable_reason": None,
            "n_members": len(active_members(basket)),
            "n_counted": None,
            "pct_above_200": None,
            "chg_13w": None,
            "chg_26w": None,
            "direction": None,
            "run_weeks": None,
            "rank_13w": None,
            "n_ranked": None,
        }
        r = by_group.get(gid)
        # First match wins. The NaN measures already encode the upstream
        # gbh.MIN_MEMBERS (=10) rule: a share/change built on fewer qualifying
        # members is missing, never zero.
        if r is None:
            reason = "no_history"
        elif top_status == "stale":
            reason = "stale"
        elif _missing(r.get("pct_above_200")) or _missing(r.get("fix_chg_pct_above_200_13w")):
            reason = "too_few_members"
        else:
            reason = None
        row["unavailable_reason"] = reason
        if reason is not None:
            row["status"] = "unavailable"
            if reason == "too_few_members":
                n_has = r.get("n_has_200")
                row["n_counted"] = None if _missing(n_has) else int(n_has)
        else:
            row["n_counted"] = int(r["n_has_200"])
            row["pct_above_200"] = round(float(r["pct_above_200"]), 4)
            row["chg_13w"] = round(float(r["fix_chg_pct_above_200_13w"]), 4)
            chg_26w = r.get("fix_chg_pct_above_200_26w")
            row["chg_26w"] = None if _missing(chg_26w) else round(float(chg_26w), 4)
            direction = r.get("state_fix_chg_pct_above_200_13w")
            row["direction"] = None if _missing(direction) else str(direction)
            run = r.get("run_fix_chg_pct_above_200_13w")
            row["run_weeks"] = None if _missing(run) else int(run)
        groups.append(row)

    # Rank inside the family only: sectors against sectors, themes against
    # themes, on the OK rows' 13-week fixed-set change (1 = largest increase).
    for family in ("sector", "theme"):
        ok_rows = [g for g in groups if g["family"] == family and g["status"] == "ok"]
        if not ok_rows:
            continue
        changes = np.array([[g["chg_13w"] for g in ok_rows]], dtype=float)
        ranks, n_ranked = gbh.cross_rank(changes)
        for i, g in enumerate(ok_rows):
            g["rank_13w"] = int(ranks[0, i])
            g["n_ranked"] = int(n_ranked[0])

    # Top "unavailable" only when every row is unavailable for a reason other
    # than stale (a stale panel keeps its top "stale").
    if top_status != "stale" and groups and all(
        g["status"] == "unavailable" for g in groups
    ):
        top_status = "unavailable"

    sectors_of: dict[str, list[str]] = {}
    themes_of: dict[str, list[str]] = {}
    for gid in ordered:
        target = sectors_of if _family(gid) == "sector" else themes_of
        for member in active_members(baskets[gid]):
            target.setdefault(member["ticker"], []).append(gid)
    companies: dict[str, dict] = {}
    for ticker in sorted(set(sectors_of) | set(themes_of)):
        sectors = sorted(set(sectors_of.get(ticker, [])))
        companies[ticker] = {
            "sector": sectors[0] if sectors else None,
            "themes": sorted(set(themes_of.get(ticker, []))),
        }

    now_utc = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    built_at = now_utc.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "schema": SCHEMA,
        "as_of": as_of.isoformat(),
        "built_at": built_at,
        "status": top_status,
        "basis": "current_roster",
        "copy": list(COPY),
        "groups": groups,
        "companies": companies,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, default=None,
                        help="output JSON (default <root>/site/sectordata/rotation_read.json)")
    args = parser.parse_args(argv)
    root = args.root
    out = args.out if args.out is not None else root / "site" / "sectordata" / "rotation_read.json"

    hist_path = root / HIST_RELPATH
    membership_path = root / MEMBERSHIP_RELPATH
    try:
        hist = pd.read_parquet(hist_path)
    except Exception as exc:  # noqa: BLE001 - a data condition never raises here
        log.warning("rotation read: history unavailable (%s): %s", hist_path, exc)
        return 0
    try:
        membership = json.loads(membership_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - a data condition never raises here
        log.warning("rotation read: membership unavailable (%s): %s", membership_path, exc)
        return 0

    try:
        payload = build(hist, membership, datetime.now(timezone.utc))
    except Exception as exc:  # noqa: BLE001 - a data condition never raises here
        log.warning("rotation read: build failed on the supplied inputs: %s", exc)
        return 0
    if payload is None:
        log.warning("rotation read: no completed weekly close in the history; not writing %s", out)
        return 0

    tmp = out.with_name(out.name + ".tmp")
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(
            json.dumps(payload, indent=1, sort_keys=False, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, out)
    except OSError as exc:
        # No partial file: the temp copy is removed and the previous file stays.
        tmp.unlink(missing_ok=True)
        log.warning("rotation read: could not write %s: %s", out, exc)
        return 0
    log.info("rotation read: wrote %s (as_of=%s, status=%s)", out, payload["as_of"], payload["status"])
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())