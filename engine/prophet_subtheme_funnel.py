"""Zero-authority subtheme leadership funnel for Prophet miss attribution.

The upstream subsector-rotation engine already decides which source-local subthemes are
"emerging". This module does not re-score that decision. It joins the producer's exact
emerging order to current Finviz membership and the existing lossless Prophet candidate
pool, then reports where the cohort disappeared:

ADMISSION_GAP
    No current member reached the eligible candidate pool.
SCORING_GAP
    At least one member was eligible, but no member received a Prophet score.
FEATURED_GAP
    At least one member was scored, but no member reached the Featured shelf.
COVERED_FEATURED
    At least one member reached Featured.

The current Finviz tree is current-only structure. It is never backdated here. This
observer is prospective ops telemetry only and has no rank, gate, size, membership,
plan, or trade authority.
"""
from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
from typing import Any


SCHEMA = "prophet_miss_audit.subtheme_funnel/v1"
TREE_REL = "data/themes_heatmap/themes_tree.json"
VISIBLE_LANES = ("buy", "watch", "leaders", "ran")


def _finite(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _hist(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _member_ticker(raw: Any) -> str | None:
    if isinstance(raw, str):
        value = raw
    elif isinstance(raw, dict):
        value = raw.get("ticker") or raw.get("t") or raw.get("symbol")
    else:
        value = None
    ticker = str(value or "").strip().upper()
    return ticker or None


def _membership(tree: Any) -> dict[str, dict[str, Any]]:
    themes = tree if isinstance(tree, list) else (
        tree.get("themes") if isinstance(tree, dict) else None
    )
    if not isinstance(themes, list):
        return {}

    out: dict[str, dict[str, Any]] = {}
    for theme_row in themes:
        if not isinstance(theme_row, dict):
            continue
        theme = str(theme_row.get("theme") or theme_row.get("key") or "").strip()
        for sub in theme_row.get("subsectors") or ():
            if not isinstance(sub, dict):
                continue
            key = str(sub.get("key") or "").strip()
            if not key:
                continue
            members = sorted({
                ticker
                for raw in (sub.get("members") or ())
                if (ticker := _member_ticker(raw))
            })
            out[key] = {
                "name": sub.get("name"),
                "theme": theme,
                "members": members,
            }
    return out


def _null(reason: str, *, as_of: str | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "tier": "ops_telemetry",
        "authority": "none — funnel measurement only; no rank/gate/size consumer",
        "available": False,
        "as_of": as_of,
        "membership_temporality": "current_only",
        "emerging": [],
        "gaps": [],
        "gap_class_hist": {},
        "null_reason": reason,
    }


def build(root: Path, standouts: dict | None, rotation: dict | None,
          degraded: list[dict]) -> dict[str, Any]:
    """Measure the producer's emerging subthemes through Prophet's existing funnel."""
    if not isinstance(rotation, dict):
        return _null("subsector rotation unavailable")

    highlights = rotation.get("highlights") or {}
    emerging = highlights.get("emerging") if isinstance(highlights, dict) else None
    if not isinstance(emerging, list):
        degraded.append({
            "input": "site/marketdata/subsector_rotation.json",
            "severity": "unexpected",
            "reason": "highlights.emerging absent/malformed — subtheme funnel not measured",
        })
        return _null("highlights.emerging absent or malformed")

    if not isinstance(standouts, dict):
        return _null("US standouts unavailable")

    rotation_asof = str(rotation.get("asof") or "").strip()
    board_asof = str(standouts.get("as_of") or "").strip()
    if not rotation_asof or not board_asof or rotation_asof != board_asof:
        degraded.append({
            "input": "site/marketdata/subsector_rotation.json",
            "severity": "unexpected",
            "reason": (
                f"subtheme funnel clock mismatch: rotation_asof={rotation_asof or 'null'} "
                f"standouts_asof={board_asof or 'null'} — refusing a cross-session join"
            ),
        })
        return _null(
            "rotation and Prophet board are not on the same completed session",
            as_of=rotation_asof or board_asof or None,
        )

    pool = standouts.get("candidate_pool")
    pool_rows = pool.get("rows") if isinstance(pool, dict) else None
    if not isinstance(pool_rows, list):
        degraded.append({
            "input": "site/factordata/us_standouts.json",
            "severity": "unexpected",
            "reason": "candidate_pool.rows absent/malformed — eligible/scored funnel unavailable",
        })
        return _null("candidate_pool.rows absent or malformed", as_of=board_asof)

    tree_path = root / TREE_REL
    try:
        tree = json.loads(tree_path.read_text(encoding="utf-8"))
    except Exception as exc:
        degraded.append({
            "input": TREE_REL,
            "severity": "unexpected",
            "reason": f"unreadable: {exc} — subtheme membership unavailable",
        })
        return _null(f"{TREE_REL} unreadable", as_of=board_asof)

    membership = _membership(tree)
    if not membership:
        degraded.append({
            "input": TREE_REL,
            "severity": "unexpected",
            "reason": "no readable subtheme membership — subtheme funnel unavailable",
        })
        return _null(f"no subtheme membership in {TREE_REL}", as_of=board_asof)

    source_rows = {
        str(row.get("key") or "").strip(): row
        for row in (rotation.get("subsectors") or ())
        if isinstance(row, dict) and str(row.get("key") or "").strip()
    }
    pool_by_ticker = {
        str(row.get("ticker") or "").strip().upper(): row
        for row in pool_rows
        if isinstance(row, dict) and str(row.get("ticker") or "").strip()
    }

    visible_by_lane: dict[str, set[str]] = {}
    for lane in VISIBLE_LANES:
        visible_by_lane[lane] = {
            str(row.get("ticker") or "").strip().upper()
            for row in (standouts.get(lane) or ())
            if isinstance(row, dict) and str(row.get("ticker") or "").strip()
        }
    visible_any = set().union(*visible_by_lane.values()) if visible_by_lane else set()

    rows: list[dict[str, Any]] = []
    missing_membership: list[str] = []
    for producer_rank, raw_key in enumerate(emerging, start=1):
        key = str(raw_key or "").strip()
        if not key:
            continue
        source_row = source_rows.get(key) or {}
        meta = membership.get(key)
        if meta is None:
            missing_membership.append(key)
            rows.append({
                "key": key,
                "producer_rank": producer_rank,
                "name": source_row.get("name"),
                "theme": source_row.get("theme"),
                "gap_class": "UNKNOWN_MEMBERSHIP",
                "gap": None,
                "null_reason": "highlighted subtheme absent from current membership tree",
            })
            continue

        members = set(meta["members"])
        eligible = sorted(members & set(pool_by_ticker))
        scored = sorted(
            ticker for ticker in eligible
            if isinstance(pool_by_ticker[ticker].get("prophet"), dict)
            and _finite((pool_by_ticker[ticker].get("prophet") or {}).get("score")) is not None
        )
        featured = sorted(
            ticker for ticker in eligible
            if pool_by_ticker[ticker].get("lane") == "featured"
        )
        visible = sorted(members & visible_any)
        present_counts = {
            lane: len(members & tickers)
            for lane, tickers in visible_by_lane.items()
        }

        reasons: list[str] = []
        for ticker in eligible:
            row = pool_by_ticker[ticker]
            if row.get("lane") == "featured":
                continue
            for reason in row.get("lane_reasons") or ():
                reason = str(reason or "").strip()
                if reason:
                    reasons.append(reason)

        if featured:
            gap_class = "COVERED_FEATURED"
        elif scored:
            gap_class = "FEATURED_GAP"
        elif eligible:
            gap_class = "SCORING_GAP"
        else:
            gap_class = "ADMISSION_GAP"

        ranks = [
            int(rank)
            for ticker in eligible
            if (rank := _finite(pool_by_ticker[ticker].get("pool_rank"))) is not None
        ]
        rows.append({
            "key": key,
            "producer_rank": producer_rank,
            "name": meta.get("name") or source_row.get("name"),
            "theme": meta.get("theme") or source_row.get("theme"),
            "quadrant": source_row.get("quadrant"),
            "turn_state": source_row.get("turn_state"),
            "emerging_score": _finite(source_row.get("emerging_score")),
            "rs_mom": _finite(source_row.get("rs_mom")),
            "accel": _finite(source_row.get("accel")),
            "n_members": len(members),
            "eligible_n": len(eligible),
            "scored_n": len(scored),
            "featured_n": len(featured),
            "visible_n": len(visible),
            "present_counts": present_counts,
            "members_eligible": eligible,
            "members_scored": scored,
            "members_featured": featured,
            "members_visible": visible,
            "blocker_hist": _hist(reasons),
            "best_pool_rank": min(ranks) if ranks else None,
            "gap_class": gap_class,
            "gap": gap_class != "COVERED_FEATURED",
        })

    if missing_membership:
        degraded.append({
            "input": TREE_REL,
            "severity": "unexpected",
            "reason": (
                f"{len(missing_membership)} emerging subtheme(s) absent from current membership "
                f"tree: {', '.join(missing_membership[:12])}"
            ),
        })

    measured = [row for row in rows if row.get("gap") is not None]
    gaps = [row for row in measured if row.get("gap")]
    covered = sum(
        1 for row in measured
        if row.get("gap_class") == "COVERED_FEATURED"
    )
    return {
        "schema": SCHEMA,
        "tier": "ops_telemetry",
        "authority": "none — funnel measurement only; no rank/gate/size consumer",
        "available": True,
        "as_of": board_asof,
        "rotation_basis": "subsector_rotation.highlights.emerging (producer classification/order)",
        "membership_basis": TREE_REL,
        "membership_temporality": "current_only — never backdated",
        "candidate_basis": "us_standouts.candidate_pool.rows (lossless eligible pool)",
        "n_emerging": len(rows),
        "n_measured": len(measured),
        "n_gaps": len(gaps),
        "featured_coverage_pct": (
            round(100.0 * covered / len(measured), 1) if measured else None
        ),
        "gap_class_hist": _hist([
            str(row.get("gap_class")) for row in measured
        ]),
        "emerging": rows,
        "gaps": gaps,
    }
