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

# Stable source-owned reason codes: the Chinese UI must distinguish a market
# date mismatch from a missing prior close, stale data and an unreadable store.
REASON_ZH = {
    "RAW_OHLC_MISSING": "SPY 和 QQQ 的原始常规时段开盘价或收盘价不可用。",
    "ASOF_MISMATCH": "SPY 和 QQQ 最新日线对应的交易日不一致。",
    "NON_SESSION_DATE": "最新价格日期不是纽交所交易日。",
    "NON_SESSION_HISTORY": "SPY 或 QQQ 的历史日线包含非纽交所交易日的数据，已拒绝不合格统计值。",
    "SESSION_UNSETTLED": "最新交易日尚未经过收盘数据确认截止时间。",
    "PREVIOUS_CLOSE_MISSING": "SPY 或 QQQ 缺少前一常规交易日的收盘价。",
    "INVALID_PRICE_SPY": "SPY 当日或前一交易日的必要价格无效。",
    "INVALID_PRICE_QQQ": "QQQ 当日或前一交易日的必要价格无效。",
    "DECOMPOSITION_FAILED_SPY": "SPY 隔夜和日间收益拆分计算未能通过一致性检查。",
    "DECOMPOSITION_FAILED_QQQ": "QQQ 隔夜和日间收益拆分计算未能通过一致性检查。",
    "DAILY_STORE_UNREADABLE": "原始日线行情存储无法读取。",
    "SESSION_STALE": "日线行情落后于最近已完成的交易日。",
    "HISTORY_INCOMPLETE": "部分历史统计值或成交量基准不可用。",
    "PUBLISHED_SESSION_STALE": "已发布的收盘观察值落后于最新已完成的交易日。",
    "NO_SOURCE_ASSEMBLED": "本次页面渲染尚未组装原始收盘行情。",
}

def _zh_reason(snapshot: dict) -> str | None:
    """Preserve original specific evidence on unknown/older source-code versions."""
    return REASON_ZH.get(snapshot.get("reason_code")) or snapshot.get("reason")



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
            volume_multiple, share = row.get("volume_multiple"), row.get("overnight_share")
            if volume_multiple is not None and volume_multiple <= 0:
                return None
            if share is not None and (
                not 0 <= share <= 100 or row["overnight_pct"] >= 0 or row["intraday_pct"] >= 0
            ):
                return None
            compounded_pct = 100 * ((1 + row["overnight_pct"] / 100) *
                                    (1 + row["intraday_pct"] / 100) - 1)
            if abs(compounded_pct - row["return_pct"]) > 0.03:
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
            "reason_code": "PUBLISHED_SESSION_STALE" if lag > 0 else "HISTORY_INCOMPLETE" if partial else None,
            "lag_sessions": lag,
            "source_state": "published_projection",
        }
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
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
        snap = tech_volatility_shock._missing(
            "Raw EOD source has not been assembled for this render.",
            code="NO_SOURCE_ASSEMBLED",
        )
    panel = env.get_template("_tech_volatility_shock.html.j2").render(
        tech_shock={**snap, "reason_zh": _zh_reason(snap)}
    )
    return page.replace("</body>", panel + "\n</body>")


def write_macro_page(site: Path, env: Environment, vm: dict) -> Path:
    """Single canonical Macro page writer, used by first AND final builds.

    The fresh stock-board pass must never call dashboard.html.j2 directly for
    mode='macro': that would remove the shock panel from the final artifact.
    """
    from lib.pages import write_page

    out = Path(site) / "macro.html"
    write_page(out, render_macro_with_shock(env, vm))
    return out
