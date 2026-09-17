"""Forward-outcome ledger for the BTC impulse radar (P3).

Accountability: every build STAMPS the day's radar state + which act legs fired +
BTC close into data/vector/impulse_ledger.jsonl (idempotent — one row per asof).
On later builds, GRADE() fills the forward outcome for matured rows (>= 3 trading
days later): did a fired DOWN leg actually precede a -5%/3d down-move, did a fired
UP leg precede a +5%/3d up-move. That live hit-rate is what the falsifier
(btc_impulse_radar_backtest) and a human use to see a leg decay in real time,
rather than trusting the historical backtest forever.

The same canonical row now carries ``research_d2``: an append-only prospective
journey for the raw D2 observation.  Its source, outcome, and correction
generations never grant alert or trading authority and never replace this
ledger with a second store.

Schema (one JSON object per line):
  {asof, down_score, down_ladder, down_act, up_score, up_ladder, up_act,
   fires:{d2,d3,u1}, btc_close, outcome:{matured, fwd_min_pct, fwd_max_pct,
   down_hit, up_hit} | null, research_d2:{schema,generations}}
"""
from __future__ import annotations

import json
import logging

import pandas as pd

from engine import btc_d2_research
from lib import config

log = logging.getLogger(__name__)

LABEL_H = 3        # trading-day forward horizon (matches the backtest label)
LABEL_THR = 0.05   # +-5%
_DVOL_UNSET = object()


def _path():
    return config.data_dir() / "vector" / "impulse_ledger.jsonl"


def load() -> list[dict]:
    p = _path()
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _write(rows: list[dict]) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r) for r in rows) + ("\n" if rows else ""))


def _fired(legs: list[dict], key: str) -> bool:
    for leg in legs or []:
        if leg.get("key") == key:
            return bool(leg.get("fired_today"))
    return False


def _read_dvol():
    try:
        from lib import store
        return store.read("deribit", "dvol")
    except Exception as exc:  # noqa: BLE001 — typed unavailable generation is safer than a crash
        log.debug("D2 research source read unavailable: %s", exc)
        return None


def stamp(
    radar: dict | None,
    sig_df: pd.DataFrame | None = None,
    *,
    dvol_df=_DVOL_UNSET,
    recorded_at: str | None = None,
) -> None:
    """Append/update today's canonical row. Never mutates prior D2 generations."""
    try:
        if not radar or not radar.get("ok"):
            return
        asof = radar.get("asof")
        if not asof:
            return
        rows = load()
        row = next((candidate for candidate in rows if candidate.get("asof") == asof), None)
        changed = False
        if row is None:
            down, up = radar.get("down", {}), radar.get("up", {})
            close = None
            if sig_df is not None and "close" in sig_df.columns and len(sig_df):
                close = float(sig_df["close"].iloc[-1])
            row = {
                "asof": asof,
                "down_score": down.get("score"), "down_ladder": down.get("ladder"),
                "down_act": bool(down.get("act_live")),
                "up_score": up.get("score"), "up_ladder": up.get("ladder"),
                "up_act": bool(up.get("act_live")),
                "fires": {"d2": _fired(down.get("legs"), "d2_dvol"),
                          "d3": _fired(down.get("legs"), "d3_sopr"),
                          "u1": _fired(up.get("legs"), "u1_sopr")},
                "btc_close": close,
                "outcome": None,
            }
            rows.append(row)
            changed = True

        journey = row.get("research_d2")
        if not isinstance(journey, dict) or journey.get("schema") != btc_d2_research.SCHEMA:
            journey = btc_d2_research.new_journey()
            row["research_d2"] = journey
            changed = True
        source = _read_dvol() if dvol_df is _DVOL_UNSET else dvol_df
        if btc_d2_research.capture_source(
            journey,
            entry_asof=asof,
            sig_df=sig_df,
            dvol_df=source,
            recorded_at=recorded_at,
        ):
            changed = True
        if changed:
            _write(rows)
    except Exception as exc:  # noqa: BLE001 — ledger is additive, never fatal
        log.debug("impulse ledger stamp skipped: %s", exc)


def grade(
    sig_df: pd.DataFrame | None = None,
    *,
    recorded_at: str | None = None,
) -> dict:
    """Append matured legacy and D2 research outcomes. Returns a small summary."""
    try:
        if sig_df is None or "close" not in sig_df.columns:
            return {"ok": False, "reason": "no close series"}
        close = sig_df["close"].copy()
        close.index = pd.to_datetime(close.index)
        close = close.sort_index()
        rows = load()
        changed = False
        for row in rows:
            try:  # one corrupt/hand-edited row must NOT abort every other row
                if row.get("outcome") is None:
                    ts = pd.Timestamp(row["asof"])
                    if ts in close.index:
                        pos = close.index.get_loc(ts)
                        if pos + LABEL_H < len(close):
                            base = float(close.iloc[pos])
                            fwd = close.iloc[pos + 1: pos + 1 + LABEL_H]
                            if not fwd.empty and base > 0:
                                fwd_min = float(fwd.min()) / base - 1.0
                                fwd_max = float(fwd.max()) / base - 1.0
                                down_fired = any(
                                    row.get("fires", {}).get(key) for key in ("d2", "d3")
                                )
                                up_fired = bool(row.get("fires", {}).get("u1"))
                                row["outcome"] = {
                                    "matured": True,
                                    "fwd_min_pct": round(fwd_min * 100, 2),
                                    "fwd_max_pct": round(fwd_max * 100, 2),
                                    "down_hit": bool(down_fired and fwd_min <= -LABEL_THR),
                                    "up_hit": bool(up_fired and fwd_max >= LABEL_THR),
                                }
                                changed = True
                journey = row.get("research_d2")
                if isinstance(journey, dict) and btc_d2_research.mature_outcome(
                    journey, sig_df, recorded_at=recorded_at,
                ):
                    changed = True
            except Exception as exc:  # noqa: BLE001 — skip bad row, keep grading others
                log.debug("impulse ledger: skipped a bad row (%s): %s", row.get("asof"), exc)
                continue
        if changed:
            _write(rows)
        return render_summary(rows)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}


def latest_d2_journey(rows: list[dict] | None = None) -> dict:
    """Read-only projection of the newest prospective D2 journey."""
    rows = rows if rows is not None else load()
    for row in reversed(rows):
        journey = row.get("research_d2")
        if isinstance(journey, dict):
            return btc_d2_research.project(journey)
    return btc_d2_research.project(None)


def render_summary(rows: list[dict] | None = None) -> dict:
    """Rolling forward hit-rate per direction over matured fires (for display)."""
    rows = rows if rows is not None else load()
    matured = [row for row in rows if (row.get("outcome") or {}).get("matured")]
    down_fires = [
        row for row in matured
        if any(row.get("fires", {}).get(key) for key in ("d2", "d3"))
    ]
    up_fires = [row for row in matured if row.get("fires", {}).get("u1")]

    def _rate(fires, key):
        return (
            round(sum(1 for row in fires if row["outcome"].get(key)) / len(fires), 3)
            if fires else None
        )

    return {
        "ok": True, "n_rows": len(rows), "n_matured": len(matured),
        "down": {"n_fires": len(down_fires), "hit_rate": _rate(down_fires, "down_hit")},
        "up": {"n_fires": len(up_fires), "hit_rate": _rate(up_fires, "up_hit")},
        "research_d2": latest_d2_journey(rows),
        "note": ("Live forward hit-rate of the radar's act-tier fires (matured "
                 ">=3d). Thin until fires accrue; complements the historical "
                 "backtest — a decaying hit-rate is the early decay signal."),
    }
