"""Point-in-time publication history for the Subsector Confluence desk.

This is a claim-family extension of the existing subsector track-record owner, not a
second generic grading plane.  It records what the Confluence surface actually published
on each session before any future outcome is known, then exposes a compact front-end
projection and descriptive forward outcomes once they mature.

Why this exists:
* rebuilding old Confluence states from today's membership is survivorship-tinted;
* the live board carries two distinct dimensions (fresh entry trigger + regime/extension);
* we need immutable first-seen snapshots to learn whether an EXTENDED fresh trigger behaves
  differently from a clean fresh trigger.

The append-only ledger lives beside the incumbent rotation ledger:
    data/subsector_rotation/confluence_snapshots.jsonl

Only the scheduled collector calls snapshot(); render-only paths read the public JSON that
was already materialized.  Nothing here changes live ranking, gating, sizing, or trade
authority.  Forward statistics are measurement-only.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import pandas as pd

from engine.ai_desk import _level_asof
from engine.ai_desk_scorer import _close_at, _covers
from engine.subsector_track_record import _session_stamp
from lib import config

log = logging.getLogger(__name__)

SCHEMA = "subsector_confluence.history.v1"
PROJECTION_SCHEMA = "subsector_confluence.history_projection.v1"
ACCURACY_SCHEMA = "subsector_confluence.accuracy.v1"
_LEDGER = ("data", "subsector_rotation", "confluence_snapshots.jsonl")
_HORIZONS = (5, 21, 63)
_MIN_PRICED = 3

# Front-end tab key -> producer group key + benchmark used only for descriptive
# forward-relative measurement.  The live engine's ranking/gates are untouched.
_DESKS = {
    "subsectors": ("subsectors", "SPY"),
    "baskets": ("baskets", "SPY"),
    "nasdaq": ("subsectors", "QQQ"),
    "russell": ("subsectors", "IWM"),
}


def _path(root: Path) -> Path:
    return root.joinpath(*_LEDGER)


def _load(root: Path) -> list[dict]:
    p = _path(root)
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except Exception:  # noqa: BLE001 — one corrupt line must not erase the record
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _members(group: dict) -> list[str]:
    """Freeze the member tickers exactly as the published group carried them."""
    seen: set[str] = set()
    out: list[str] = []
    for member in group.get("members") or []:
        ticker = str((member or {}).get("ticker") or "").strip().upper()
        if ticker and ticker not in seen:
            seen.add(ticker)
            out.append(ticker)
    return out


def _entry_condition(row: dict) -> str:
    """Friendly orthogonal condition; never replaces the raw producer regime fields."""
    state = str(row.get("regime_state") or "").upper()
    side = str(row.get("regime_side") or "").lower()
    if state == "EXTENDED":
        return "stretched"
    if state == "BELOW_TREND":
        return "below_trend"
    if side == "avoid":
        return "caution"
    return "clean"


def _freeze_group(group: dict, *, desk: str, stamp: str, engine_universe: str | None) -> dict:
    entry = group.get("entry") or {}
    regime = group.get("regime") or {}
    row = {
        "schema": SCHEMA,
        "date": stamp,
        "desk": desk,
        "engine_universe": engine_universe,
        "key": group.get("key"),
        "label": group.get("label"),
        "sector": group.get("sector"),
        "class": group.get("class"),
        "entry_tier": entry.get("tier"),
        "entry_weight": entry.get("weight"),
        "entry_ticks": entry.get("ticks"),
        "entry_fresh_bars": entry.get("fresh_bars"),
        "entry_buyable": entry.get("buyable"),
        "entry_reason": entry.get("reason"),
        "regime_state": regime.get("state"),
        "regime_side": regime.get("side"),
        "regime_action": regime.get("action"),
        "rs_60d": regime.get("rs_60d"),
        "reliability": group.get("reliability"),
        "n_members": group.get("n_members"),
        "n_priced": group.get("n_priced"),
        "members": _members(group),
    }
    row["entry_condition"] = _entry_condition(row)
    return row


def snapshot(payload: dict, desk: str, *, today: date | str | None = None,
             root: Path | None = None) -> int:
    """Append one desk's published session. First-seen (date, desk, key) wins.

    The immutable-first rule is deliberate: if a later run recomputes the same session
    differently, overwriting would destroy what users actually saw and make self-grading
    unfalsifiable.  A correction can ship in the current board, but the publication record
    remains the original observation.
    """
    try:
        if desk not in _DESKS or not payload or not payload.get("ok"):
            return 0
        root = Path(root) if root else config.ROOT
        groups_key, _ = _DESKS[desk]
        groups = payload.get(groups_key) or []
        if not groups:
            return 0
        stamp = _session_stamp(today or payload.get("as_of"))
        existing = {
            f"{r.get('date')}|{r.get('desk')}|{r.get('key')}"
            for r in _load(root)
        }
        new: list[dict] = []
        for group in groups:
            key = group.get("key")
            dedup = f"{stamp}|{desk}|{key}"
            if not key or dedup in existing:
                continue
            new.append(_freeze_group(
                group,
                desk=desk,
                stamp=stamp,
                engine_universe=payload.get("universe"),
            ))
            existing.add(dedup)
        if not new:
            return 0
        p = _path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            for row in new:
                fh.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")
        return len(new)
    except Exception as exc:  # noqa: BLE001 — display/measurement lane never breaks the board
        log.warning("subsector confluence history snapshot failed: %s", exc)
        return 0


def _member_ret(ticker: str, root: Path, start: str, end: str) -> float | None:
    p0, p1 = _level_asof(ticker, root, start), _close_at(ticker, root, end)
    if p0 in (None, 0) or p1 is None:
        return None
    return float(p1 / p0 - 1.0)


def _fwd_rel(row: dict, root: Path, horizon_d: int) -> float | None:
    """Frozen-member EW return minus the desk benchmark, using incumbent price helpers."""
    try:
        _, bench = _DESKS.get(row.get("desk"), ("subsectors", "SPY"))
        end = (pd.Timestamp(row["date"]) + pd.Timedelta(days=horizon_d)).strftime("%Y-%m-%d")
        rets = [
            ret
            for ticker in (row.get("members") or [])
            if (ret := _member_ret(ticker, root, row["date"], end)) is not None
        ]
        if len(rets) < _MIN_PRICED:
            return None
        b0, b1 = _level_asof(bench, root, row["date"]), _close_at(bench, root, end)
        if b0 in (None, 0) or b1 is None:
            return None
        return float(sum(rets) / len(rets) - (b1 / b0 - 1.0))
    except Exception:  # noqa: BLE001
        return None


def _matured_entry_rows(rows: list[dict], root: Path, horizon_d: int,
                         today_dt: date) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        try:
            if row.get("class") != "entry_now":
                continue
            if (pd.Timestamp(today_dt) - pd.Timestamp(row["date"])).days < horizon_d:
                continue
            _, bench = _DESKS.get(row.get("desk"), ("subsectors", "SPY"))
            end = (pd.Timestamp(row["date"]) + pd.Timedelta(days=horizon_d)).strftime("%Y-%m-%d")
            if not _covers(bench, root, end):
                continue
            fwd = _fwd_rel(row, root, horizon_d)
            if fwd is None:
                continue
            out.append({**row, "fwd_rel": fwd})
        except Exception:  # noqa: BLE001
            continue
    return out


def _summary(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0, "mean_fwd_rel": None, "hit_rate": None}
    fwds = [float(r["fwd_rel"]) for r in rows]
    return {
        "n": len(fwds),
        "mean_fwd_rel": round(sum(fwds) / len(fwds), 4),
        "hit_rate": round(sum(1 for value in fwds if value > 0) / len(fwds), 3),
    }


def accuracy(*, today: date | str | None = None, root: Path | None = None,
             horizons: tuple[int, ...] = _HORIZONS) -> dict:
    """Descriptive forward scorecard for fresh-entry calls.

    This deliberately does NOT mint a validation/promotion verdict.  Its most useful early
    split is the exact semantic tension the UI exposes: fresh trigger + EXTENDED versus fresh
    trigger + non-extended.  Promotion into live gating requires a separate accepted study.
    """
    try:
        root = Path(root) if root else config.ROOT
        today_dt = date.fromisoformat(_session_stamp(today))
        rows = _load(root)
        out_h: dict[str, dict] = {}
        any_matured = False
        for horizon in horizons:
            matured = _matured_entry_rows(rows, root, horizon, today_dt)
            any_matured = any_matured or bool(matured)
            extended = [r for r in matured if r.get("entry_condition") == "stretched"]
            other = [r for r in matured if r.get("entry_condition") != "stretched"]
            out_h[str(horizon)] = {
                "all": _summary(matured),
                "extended": _summary(extended),
                "not_extended": _summary(other),
            }
        dates = sorted({r.get("date") for r in rows if r.get("date")})
        return {
            "schema": ACCURACY_SCHEMA,
            "status": "measuring" if any_matured else "accruing",
            "n_snapshot_days": len(dates),
            "history_start": dates[0] if dates else None,
            "horizons": out_h,
            "note": (
                "Prospective point-in-time measurement only. Extended vs non-extended "
                "fresh triggers are reported separately; this scorecard does not change "
                "live ranking, gating, sizing, or trade authority."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "schema": ACCURACY_SCHEMA,
            "status": "accruing",
            "n_snapshot_days": 0,
            "history_start": None,
            "horizons": {},
            "note": "History is accruing; forward outcomes are not available yet.",
            "compute_error": str(exc),
        }


def _public_row(row: dict) -> dict:
    return {
        "key": row.get("key"),
        "label": row.get("label"),
        "sector": row.get("sector"),
        "class": row.get("class"),
        "entry_tier": row.get("entry_tier"),
        "entry_ticks": row.get("entry_ticks"),
        "entry_buyable": row.get("entry_buyable"),
        "entry_condition": row.get("entry_condition") or _entry_condition(row),
        "regime_state": row.get("regime_state"),
        "regime_side": row.get("regime_side"),
        "rs_60d": row.get("rs_60d"),
        "n_priced": row.get("n_priced"),
    }


def public_projection(*, today: date | str | None = None, root: Path | None = None,
                      max_days: int = 45) -> dict:
    """Compact browser-safe day-by-day history; raw frozen members stay backend-only."""
    root = Path(root) if root else config.ROOT
    rows = _load(root)
    dates = sorted({r.get("date") for r in rows if r.get("date")}, reverse=True)
    keep = dates[:max(1, int(max_days))]
    by_date: dict[str, dict[str, list[dict]]] = {}
    for row in rows:
        d = row.get("date")
        desk = row.get("desk")
        if d not in keep or desk not in _DESKS:
            continue
        by_date.setdefault(d, {}).setdefault(desk, []).append(row)

    days: list[dict] = []
    classes = ("entry_now", "forming", "tailwind", "neutral", "late", "headwind")
    for d in keep:
        desks: dict[str, dict] = {}
        for desk, desk_rows in sorted((by_date.get(d) or {}).items()):
            counts = {name: 0 for name in classes}
            for row in desk_rows:
                cls = row.get("class")
                if cls in counts:
                    counts[cls] += 1
            recs = [_public_row(r) for r in desk_rows if r.get("class") == "entry_now"]
            recs.sort(key=lambda r: (
                r.get("entry_tier") or "Z",
                -(float(r.get("rs_60d")) if r.get("rs_60d") is not None else -999.0),
                r.get("label") or "",
            ))
            watches = [_public_row(r) for r in desk_rows if r.get("class") == "forming"]
            desks[desk] = {
                "total": len(desk_rows),
                "counts": counts,
                "recommendations": recs,
                "forming": watches,
            }
        days.append({"date": d, "desks": desks})

    start = min((r.get("date") for r in rows if r.get("date")), default=None)
    return {
        "schema": PROJECTION_SCHEMA,
        "history_start": start,
        "pit_only_since": start,
        "methodology": (
            "First-seen daily publication snapshots. No retrospective recomputation from "
            "today's membership; history starts when this ledger was introduced."
        ),
        "days": days,
        "accuracy": accuracy(today=today, root=root),
    }
