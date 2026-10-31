"""Macro-only Tech Volatility Shock projection and compact panel renderer.

Nightly engine rendering has the R2 raw OHLCV store restored; express render
workflows do NOT restore 617 MB of Massive per-name bars. This module publishes
one *derived view*, only when both current raw bars qualify, as a tiny committed
site/marketdata JSON. Express renders read and age that existing view instead
of overwriting it with an 'unavailable' result. This is a view projection, not
a second price store or an alternative market-state authority.
"""
from __future__ import annotations

import json
import logging
import math
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from jinja2 import Environment

from engine import tech_volatility_shock
from lib import nyse_calendar

log = logging.getLogger(__name__)
SCHEMA = "macro.tech_volatility_shock.v1"
RELATIVE_PATH = Path("marketdata/tech_volatility_shock.json")


def _published_snapshot(path: Path, now: datetime) -> dict | None:
    """Strict, bounded read of our own committed, derived snapshot."""
    try:
        # The projection is a pair of scalar cards, never a historical bar dump.
        if not path.is_file() or path.stat().st_size > 10_000:
            return None
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("schema") != SCHEMA or doc.get("source") != "massive_stock_day_raw_v1":
            return None
        snap = doc["snapshot"]
        if not isinstance(snap, dict) or snap.get("asof") != doc.get("asof"):
            return None
        session = date.fromisoformat(snap["asof"])
        if not nyse_calendar.is_session(session) or session > nyse_calendar.expected_last_session(now):
            return None
        if snap.get("price_scope") != "xnys_regular_session" or snap.get("volume_scope") != "full_market_day":
            return None
        rows = snap.get("indices")
        if not isinstance(rows, list) or len(rows) != 2 or [r.get("symbol") for r in rows if isinstance(r, dict)] != ["SPY", "QQQ"]:
            return None
        def numeric(x, *, optional=False):
            return ((optional and x is None) or
                    (type(x) in (float, int) and math.isfinite(x)))
        for row in rows:
            if not all(numeric(row.get(k)) for k in ("return_pct", "overnight_pct", "intraday_pct")):
                return None
            if not all(numeric(row.get(k), optional=True) for k in
                       ("z60", "volume_multiple", "overnight_share")):
                return None
            if not (row.get("year") == session.year and type(row.get("n_ytd")) is int
                    and 1 <= row["n_ytd"] <= 300):
                return None
            rank = row.get("rank_ytd")
            if rank is not None and (type(rank) is not int or not 1 <= rank <= row["n_ytd"]):
                return None
        if not numeric(snap.get("relative_pp")) or not numeric(snap.get("relative_z60"), optional=True):
            return None
        if abs(snap["relative_pp"] - (rows[1]["return_pct"] - rows[0]["return_pct"])) > 0.021:
            return None
        if snap.get("session_read") not in ("overnight_dominant", "intraday_dominant", "mixed"):
            return None
        lag = nyse_calendar.sessions_behind(session, now=now)
        partial = (snap.get("relative_z60") is None or
                   any(row["z60"] is None or row["volume_multiple"] is None for row in rows))
        return {
            **snap,
            "status": "stale" if lag > 0 else "partial" if partial else "ok",
            "reason": ("Published EOD observation is behind the latest completed session."
                       if lag > 0 else
                       "Some historical statistics or volume baselines unavailable."
                       if partial else None),
            "lag_sessions": lag,
            "source_state": "published_projection",
        }
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        log.warning("tech shock published view rejected: %s", exc)
        return None


def _write_projection(path: Path, snapshot: dict, now: datetime) -> None:
    """Single derived view, atomic replace; render-only jobs never call this."""
    doc = {
        "schema": SCHEMA,
        "source": "massive_stock_day_raw_v1",
        "asof": snapshot["asof"],
        "generated_utc": now.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "snapshot": {k: v for k, v in snapshot.items() if k != "source_state"},
    }
    blob = json.dumps(doc, sort_keys=True, separators=(",", ":"), allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".tvs-", suffix=".tmp", delete=False) as stream:
            tmp = Path(stream.name)
            stream.write(blob)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def snapshot_for_macro(site: Path, *, now: datetime | None = None) -> dict:
    """Best source-bound view, monotonically selecting raw vs committed as-of.

    Writes ONLY a derived static projection when raw observations qualify, so
    a later page-only render never removes the last qualified observation.
    """
    now = now or datetime.now(timezone.utc)
    path = Path(site) / RELATIVE_PATH
    cached = _published_snapshot(path, now)
    fresh = tech_volatility_shock.build_snapshot(now=now)
    if fresh["indices"] and (
        cached is None or fresh["asof"] >= cached["asof"]
    ):
        # A producer with the two required raw bars is always more authoritative
        # for the same market session than the previous published derivation.
        # Failed persistence never prevents a truthful page read.
        try:
            _write_projection(path, fresh, now)
        except (OSError, ValueError, TypeError) as exc:
            log.warning("tech shock view publication skipped: %s", exc)
        return {**fresh, "source_state": "raw_daily_store"}
    if cached is not None:
        return cached
    return {**fresh, "source_state": "unavailable"}


def render_macro_with_shock(env: Environment, vm: dict) -> str:
    """Render Macro and append an accessible, progressively enhanced panel.

    Browser moves the collapsed card after #regime-radar; without JS it remains
    accessible at page end. The stocks dashboard uses the untouched renderer.
    """
    page = env.get_template("dashboard.html.j2").render(**vm, mode="macro")
    if page.count("</body>") != 1:
        raise ValueError("Macro body anchor missing or ambiguous")
    snap = vm.get("tech_shock")
    if not isinstance(snap, dict):
        snap = tech_volatility_shock._missing("Raw EOD source has not been assembled for this render.")
    panel = env.get_template("_tech_volatility_shock.html.j2").render(tech_shock=snap)
    return page.replace("</body>", panel + "\n</body>")
