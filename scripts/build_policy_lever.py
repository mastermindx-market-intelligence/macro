"""Build the Policy-Lever ARMED/QUIET card artifact.

Writes site/policy_lever.json — consumed by scripts/build_site.py
for the US market-state surface (dashboard.html.j2, mode=stocks).

Artifact schema (Policy-Shock W2-F, masterplan §4):

    policy_lever = {
      "schema": "policy_lever.v1",
      "as_of": "YYYY-MM-DD",       # EVIDENCE date — the semis price date
      "as_of_basis": "price_date" | "build_date_fallback",
      "computed_at": str,         # GENERATION instant (UTC ISO-8601), not evidence
      "favored_complex": {
        "basket": ["SMH", "SOXX"],
        "drawdown_pct": float,     # trailing-120d peak drawdown %
        "drawdown_z": float | None,
        "note": str,               # unsigned EN display copy
        "note_zh": str,
        "as_of": str | None,       # price date (evidence)
        "computed_at": str,        # generation instant (UTC ISO-8601)
      },
      "jawboning": {
        "n_7d": int | None,        # None = unavailable, NOT a confident zero
        "n_30d": int | None,
        "last_alert_ts": str | None,        # raw source timestamp
        "last_alert_summary": str | None,   # ~140 chars
        "last_alert_summary_zh": str | None,
        "last_alert_ts_utc": str | None,    # normalised UTC instant
        "source_status": "missing" | "unreadable" | "empty" | "unusable"
                       | "partial" | "usable",
        "coverage": "unknown",    # reading a file never proves feed completeness
        "evaluated_at": str,       # the single evaluation instant (UTC ISO-8601)
        "evaluated_date": "YYYY-MM-DD",
        "diagnostics": {...},      # per-class rejection counts
      },
      "calendar": {
        "days_to_midterm": int | None,   # None once the event has passed
        "days_since_midterm": int | None,
        "event_date": "YYYY-MM-DD",
        "event_state": "upcoming" | "today" | "past",
        "evaluation_date": "YYYY-MM-DD",
        "evaluated_at": str,
        "context_note": str,
        "context_note_zh": str,
      },
      "levers": [
        {
          "name": str,
          "name_zh": str,
          "asset": str | None,
          "arming": dict | None,   # technical_arming block from engine/commodity_signals.py
          "watch": str,            # unsigned qualitative EN
          "watch_zh": str,
          "copy_as_of": str,       # YYYY-MM-DD date this caption was last reviewed
          "copy_age_days": int,    # calendar days since copy_as_of (live-computed)
          "copy_stale": bool,      # True when copy_age_days > _CAPTION_STALE_DAYS
        }
      ],
      "state": "QUIET" | "ELEVATED" | "ARMED",
      "framing": str,
      "framing_zh": str,
    }

ARMED rule (frozen v1, PS-R9):
  favored_complex.drawdown_pct <= -15%  AND  any lever.arming.armed  → ARMED
  exactly ONE of the two conditions                                   → ELEVATED
  neither                                                             → QUIET

PS-R1: The word "intent" must not appear in card copy.
PS-R4: No probabilities anywhere.
PS-R7: Site artifact only (site/policy_lever.json). No data/ ledger.

Usage:
    python -m scripts.build_policy_lever
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import config, store  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("build_policy_lever")

# ---------------------------------------------------------------------------
# Constants (frozen v1 per PS-R9)
# ---------------------------------------------------------------------------
_MIDTERM_DATE = datetime(2026, 11, 3, tzinfo=timezone.utc)
_DRAWDOWN_THRESHOLD = -0.15          # -15% triggers the drawdown leg
_DRAWDOWN_WINDOW_D = 120             # trailing days for peak-to-current
_DRAWDOWN_ZSCORE_WINDOW_D = 252      # history for z-score normalisation
_JAWBONE_7D_WINDOW = 7
_JAWBONE_30D_WINDOW = 30
_LAST_ALERT_SUMMARY_LEN = 140
_CAPTION_AS_OF = "2026-07-18"       # bump when you edit a lever watch caption
_CAPTION_STALE_DAYS = 60            # dialog shows "review due" past this age


# ---------------------------------------------------------------------------
# Framing copy (PS-R1: no "intent"; PS-R4: no probabilities)
# ---------------------------------------------------------------------------
_FRAMING_EN = (
    "Conditions under which violent reversals are more likely — not intent, not timing."
)
_FRAMING_ZH = (
    "衡量剧烈反转更可能发生的条件——不是意图，也不是时点。"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> datetime:
    """The current instant, UTC.

    Every computing function receives the evaluation instant as an argument so
    one build uses ONE instant. Production default is the wall clock; a test
    injects a fixed instant through the ``now=`` parameter, which leaves this
    default — and therefore production semantics — untouched.
    """
    return datetime.now(timezone.utc)


def _as_utc(moment: datetime) -> datetime:
    """Aware-UTC datetime.

    Naive values follow the established source convention: a timestamp written
    without a zone is read as UTC. Aware values are converted to UTC so every
    window comparison happens on one scale.
    """
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _iso_utc(moment: datetime) -> str:
    """ISO-8601 UTC instant, e.g. 2026-11-01T19:47:12.123456Z."""
    return _as_utc(moment).isoformat().replace("+00:00", "Z")


def _load_price(ticker: str) -> pd.DataFrame | None:
    """Load daily close from the committed yahoo store (same path as commodity_inputs).

    Synthesises open/high/low from close so the commodity_signals functions work.
    Returns None (never raises) if the store is absent.
    """
    try:
        df = store.read("yahoo", ticker)
        if df is None or df.empty:
            log.warning("price store absent for %s", ticker)
            return None
        px = df.rename(columns=str.lower).copy()
        px.index = pd.to_datetime(px.index).normalize()
        px = px[~px.index.duplicated(keep="last")].sort_index().dropna(subset=["close"])
        for c in ("open", "high", "low"):
            if c not in px.columns:
                px[c] = px["close"]
        keep = ["open", "high", "low", "close"] + (["volume"] if "volume" in px.columns else [])
        return px[keep]
    except Exception as e:  # noqa: BLE001
        log.warning("load_price(%s) failed: %s", ticker, e)
        return None


def _compute_drawdown(tickers: list[str]) -> dict:
    """Equal-weight composite drawdown (trailing-120d peak) for a basket of tickers.

    Composite is built from daily returns (not price level) so that different
    price scales do not bias the equal-weight average.

    Returns a dict with keys: drawdown_pct (float), drawdown_z (float | None),
    basket (list — members that actually loaded), basket_incomplete (bool),
    as_of (str), note (EN), note_zh (ZH), and optionally
    basket_caveat / basket_caveat_zh when any configured member is missing.
    """
    # --- load price series, track which members loaded vs. configured ---
    series: list[pd.Series] = []
    members_loaded: list[str] = []
    members_missing: list[str] = []
    for t in tickers:
        px = _load_price(t)
        if px is not None and not px.empty:
            series.append(px["close"].rename(t))
            members_loaded.append(t)
        else:
            members_missing.append(t)

    basket_incomplete = bool(members_missing)

    # --- zero members: null block ---
    if not series:
        note_en = (
            "Price data unavailable for all configured members "
            f"({', '.join(tickers)}) — drawdown not computed."
        )
        note_zh = (
            f"所有配置成员（{'/'.join(tickers)}）价格数据不可用，回撤未计算。"
        )
        result: dict = {
            "basket": tickers,
            "basket_incomplete": True,
            "drawdown_pct": None,
            "drawdown_z": None,
            "as_of": None,
            "note": note_en,
            "note_zh": note_zh,
        }
        # add visible caveat so template can surface it
        caveat_en = (
            f"Data missing for: {', '.join(tickers)}. "
            "Drawdown block not computed — treat as unavailable."
        )
        caveat_zh = (
            f"以下成员数据缺失：{', '.join(tickers)}。"
            "回撤模块未计算，视为不可用。"
        )
        result["basket_caveat"] = caveat_en
        result["basket_caveat_zh"] = caveat_zh
        return result

    # --- build equal-weight composite from RETURNS (not price level) ---
    # Align on common dates, compute daily returns per member, average, then
    # cumulatively compound back to an index starting at 1.0.
    aligned_px = pd.concat(series, axis=1).sort_index().ffill().dropna(how="all")
    # pct_change gives NaN for the first row; drop it
    returns = aligned_px.pct_change().dropna(how="all")
    # mean of available (non-NaN) member returns each day
    ew_returns = returns.mean(axis=1)
    # cumulative product → index level
    composite = (1 + ew_returns).cumprod()

    # trailing-120d drawdown on the composite index
    trail_120 = composite.tail(_DRAWDOWN_WINDOW_D + 1)  # +1 for safety
    if len(trail_120) < 10:
        result = {
            "basket": members_loaded,
            "basket_incomplete": basket_incomplete,
            "drawdown_pct": None,
            "drawdown_z": None,
            "as_of": str(composite.index[-1].date()) if len(composite) else None,
            "note": "Insufficient price history for drawdown.",
            "note_zh": "价格历史数据不足，无法计算回撤。",
        }
        if basket_incomplete:
            caveat_en = (
                f"Basket incomplete — data missing for: {', '.join(members_missing)}. "
                "Drawdown computed from loaded members only."
            )
            caveat_zh = (
                f"组合不完整——以下成员数据缺失：{'/'.join(members_missing)}。"
                "回撤仅基于已加载成员计算。"
            )
            result["basket_caveat"] = caveat_en
            result["basket_caveat_zh"] = caveat_zh
        return result

    peak = float(trail_120.max())
    current = float(composite.iloc[-1])
    dd_pct = round((current / peak - 1) * 100, 2) if peak != 0 else None
    as_of = str(composite.index[-1].date())

    # z-score vs trailing 252d distribution of same rolling window
    dd_z: float | None = None
    try:
        hist = composite.tail(_DRAWDOWN_ZSCORE_WINDOW_D + _DRAWDOWN_WINDOW_D)
        rolling_peak = hist.rolling(_DRAWDOWN_WINDOW_D, min_periods=60).max()
        dd_series = (hist / rolling_peak - 1).dropna()
        if len(dd_series) >= 20:
            mean = float(dd_series.mean())
            std = float(dd_series.std())
            dd_current = float(dd_series.iloc[-1])
            dd_z = round((dd_current - mean) / std, 2) if std > 0 else None
    except Exception:  # noqa: BLE001
        pass

    # display note — built from members that ACTUALLY loaded
    basket_label = "/".join(members_loaded)
    dd_str = f"{dd_pct:+.1f}%" if dd_pct is not None else "N/A"
    note = (
        f"Semis complex ({basket_label} equal-weight) is {dd_str} from the "
        f"trailing-120-day peak. Depth of the drawdown is the structural "
        f"context for rotation-reversal conditions."
    )
    note_zh = (
        f"半导体组合（{basket_label}等权）距过去120日高点{dd_str}。"
        f"回撤深度是轮动反转条件的结构性背景。"
    )

    result = {
        "basket": members_loaded,
        "basket_incomplete": basket_incomplete,
        "drawdown_pct": dd_pct,
        "drawdown_z": dd_z,
        "as_of": as_of,
        "note": note,
        "note_zh": note_zh,
    }
    if basket_incomplete:
        caveat_en = (
            f"Basket incomplete — data missing for: {', '.join(members_missing)}. "
            "Drawdown computed from loaded members only."
        )
        caveat_zh = (
            f"组合不完整——以下成员数据缺失：{'/'.join(members_missing)}。"
            "回撤仅基于已加载成员计算。"
        )
        result["basket_caveat"] = caveat_en
        result["basket_caveat_zh"] = caveat_zh
    return result


def _compute_oil_arming() -> dict | None:
    """Run technical_arming on CL=F (crude oil futures) via the SAME engine path
    that build_commodities.py uses — do not reimplement.

    Returns None if price data or config is unavailable.
    """
    try:
        from engine import commodity_signals
        cfg = config.load()["commodities"]
        px = _load_price("CL=F")
        if px is None or px.empty:
            return None
        arming = commodity_signals.technical_arming(px, cfg)
        # Source observation date, not the build clock or the semis date.
        # Preserve every engine result; this is additive provenance only.
        if isinstance(arming, dict):
            return {**arming, "as_of": px.index[-1].date().isoformat()}
        return arming
    except Exception as e:  # noqa: BLE001
        log.warning("oil arming computation failed: %s", e)
        return None


_TIMESTAMP_FIELDS = ("published", "generated_at")


def _parse_record_timestamp(record: dict) -> tuple[datetime | None, str | None, str]:
    """Parse a record's observation timestamp.

    Returns ``(instant, raw_source_string, reason)``. ``instant`` is an
    aware-UTC datetime and ``raw_source_string`` the untouched source text.
    When the record carries no usable timestamp ``instant`` is None and
    ``reason`` names the first defect found: "missing" | "wrong_type" |
    "unparseable".
    """
    reason = "missing"
    for field in _TIMESTAMP_FIELDS:
        raw = record.get(field)
        if raw is None:
            continue
        if not isinstance(raw, str):
            # A number, bool, list or dict is not a timestamp.
            if reason == "missing":
                reason = "wrong_type"
            continue
        text = raw.strip()
        if not text:
            continue
        try:
            parsed = _as_utc(datetime.fromisoformat(text))
        except (ValueError, TypeError, OverflowError):
            if reason == "missing":
                reason = "unparseable"
            continue
        return parsed, raw, ""
    return None, None, reason


def _display_text(record: dict, *fields: str) -> str | None:
    """First present, non-blank STRING display field, bounded for display.

    A non-string value (list / dict / number / bool) is not display copy and is
    rejected: rendering it would leak raw structure into the surface instead of
    a bounded string.
    """
    for field in fields:
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            return value[:_LAST_ALERT_SUMMARY_LEN]
    return None


def _compute_jawboning(alerts_path: Path, now: datetime | None = None) -> dict:
    """Read data/whitehouse/alerts.jsonl (READ-ONLY — sentinel is the single writer).

    Returns jawboning counts for the 7d/30d windows plus the most recent
    OBSERVED alert summary.

    Contract (R2 producer integrity):
      - ONE evaluation instant (`now`) bounds both windows. A record is
        observed only when published <= that instant; a future-dated record
        is excluded from the counts AND from the last observed event.
      - Strict per-record validation: a line must decode to an object, carry
        a usable timestamp, and carry display copy as strings. One corrupt
        line never discards an independent valid record and never crashes
        the publication.
      - Counts are unavailable (None) when no eligible record basis exists.
        An absent, unreadable, wholly unusable or all-future source is NOT a
        confident zero.
      - `source_status` qualifies the file. `coverage` is always "unknown":
        reading a file never proves the upstream feed was collected whole, and
        a read or evaluation instant is never feed freshness.
    """
    evaluation = _as_utc(now) if now is not None else _utc_now()

    diagnostics: dict = {
        "records_read": 0,
        "eligible_observed": 0,
        "malformed_json": 0,
        "invalid_structure": 0,
        "invalid_timestamp": 0,
        "future_records": 0,
        "invalid_timestamp_reasons": {"missing": 0, "wrong_type": 0, "unparseable": 0},
    }

    result: dict = {
        # legacy keys — same names, same meaning for valid input
        "n_7d": None,
        "n_30d": None,
        "last_alert_ts": None,
        "last_alert_summary": None,
        "last_alert_summary_zh": None,
        # additive source-quality metadata
        "last_alert_ts_utc": None,
        "source_status": "missing",
        "coverage": "unknown",
        "evaluated_at": _iso_utc(evaluation),
        "evaluated_date": evaluation.date().isoformat(),
        "diagnostics": diagnostics,
        "_skipped_lines": 0,
    }

    if not alerts_path.exists():
        log.info("whitehouse alerts file absent — jawboning nulls")
        result["_note"] = "whitehouse/alerts.jsonl absent — jawboning unavailable"
        return result

    try:
        raw_text = alerts_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        log.warning("whitehouse alerts read failed: %s", e)
        result["source_status"] = "unreadable"
        result["_note"] = f"read error: {e}"
        return result

    cutoff_7d = evaluation - timedelta(days=_JAWBONE_7D_WINDOW)
    cutoff_30d = evaluation - timedelta(days=_JAWBONE_30D_WINDOW)

    # Per-line parse: a bad line (torn last line, encoding noise, a JSON
    # scalar/array, a record without a usable timestamp) is rejected on its
    # own and never nulls the whole jawboning block.
    observed: list[tuple[datetime, dict, str]] = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        diagnostics["records_read"] += 1
        try:
            parsed = json.loads(line)
        except (json.JSONDecodeError, RecursionError):
            diagnostics["malformed_json"] += 1
            log.debug("jawboning: skipped malformed line: %.80s…", line)
            continue
        if not isinstance(parsed, dict):
            # A JSON scalar / list / null is not a record.
            diagnostics["invalid_structure"] += 1
            log.debug("jawboning: skipped non-object record: %.80s…", line)
            continue
        pub, raw_ts, reason = _parse_record_timestamp(parsed)
        if pub is None:
            diagnostics["invalid_timestamp"] += 1
            reasons = diagnostics["invalid_timestamp_reasons"]
            reasons[reason] = reasons.get(reason, 0) + 1
            continue
        if pub > evaluation:
            # Published after the evaluation instant — not yet observable.
            diagnostics["future_records"] += 1
            continue
        observed.append((pub, parsed, raw_ts))

    diagnostics["eligible_observed"] = len(observed)
    rejected = (
        diagnostics["malformed_json"]
        + diagnostics["invalid_structure"]
        + diagnostics["invalid_timestamp"]
    )
    result["_skipped_lines"] = rejected

    if diagnostics["records_read"] == 0:
        # Readable but empty: zero RECORDED events. Coverage stays unknown —
        # an empty file is not proof that no event happened.
        result["source_status"] = "empty"
        result["n_7d"] = 0
        result["n_30d"] = 0
        result["_note"] = (
            "whitehouse/alerts.jsonl readable but empty — no recorded events in file; "
            "feed coverage unknown"
        )
        return result

    if not observed:
        # No eligible record basis: the counts are unavailable, not zero.
        result["source_status"] = "unusable"
        result["_note"] = (
            "whitehouse/alerts.jsonl holds no usable observed record — jawboning "
            "counts unavailable; feed coverage unknown"
        )
        return result

    n_7d = 0
    n_30d = 0
    last_pub: datetime | None = None
    last_record: dict | None = None
    last_raw: str | None = None

    for pub, record, raw_ts in observed:
        # pub <= evaluation by construction, so the window is [cutoff, now].
        if pub >= cutoff_7d:
            n_7d += 1
        if pub >= cutoff_30d:
            n_30d += 1

        if last_pub is None or pub > last_pub:
            last_pub = pub
            last_record = record
            last_raw = raw_ts

    result["n_7d"] = n_7d
    result["n_30d"] = n_30d
    result["source_status"] = (
        "partial" if (rejected or diagnostics["future_records"]) else "usable"
    )
    result["last_alert_ts"] = last_raw
    result["last_alert_ts_utc"] = _iso_utc(last_pub)
    # EN: prefer banner_title, fall back to summary.
    en_summary = _display_text(last_record, "banner_title", "summary")
    # ZH: prefer banner_title_zh / summary_zh from the alert record; fall back to EN.
    zh_summary = _display_text(last_record, "banner_title_zh", "summary_zh") or en_summary
    result["last_alert_summary"] = en_summary
    result["last_alert_summary_zh"] = zh_summary
    result["_note"] = (
        "whitehouse/alerts.jsonl read — recorded events counted inside the 7d/30d "
        "windows ending at the evaluation instant; feed coverage unknown"
    )
    return result


def _compute_calendar(now: datetime | None = None) -> dict:
    """2026-11-03 midterms + unsigned display context (no signal language).

    The event is dated, so the block carries the event date, the evaluation
    date and an explicit upcoming/today/past state. Once the event has passed
    there is no live countdown to report: `days_to_midterm` becomes None
    (the legacy field stays present for consumers that key on it) and
    `days_since_midterm` carries the elapsed days. A permanent live zero is
    not a date, and a passed event is not a countdown.
    """
    evaluation = _as_utc(now) if now is not None else _utc_now()
    eval_date = evaluation.date()
    event_date = _MIDTERM_DATE.date()
    days = (event_date - eval_date).days

    if days > 0:
        event_state = "upcoming"
        days_to = days
        days_since = None
        context_note = (
            f"US midterm elections: {days} days (2026-11-03). "
            f"Policy cycle context only — no directional read."
        )
        context_note_zh = (
            f"美国中期选举：{days}天（2026年11月3日）。"
            f"仅作政策周期背景参考，不作方向性判断。"
        )
    elif days == 0:
        event_state = "today"
        days_to = 0
        days_since = 0
        context_note = (
            f"US midterm elections: today (2026-11-03). "
            f"Policy cycle context only — no directional read."
        )
        context_note_zh = (
            f"美国中期选举：今天（2026年11月3日）。"
            f"仅作政策周期背景参考，不作方向性判断。"
        )
    else:
        event_state = "past"
        days_to = None
        days_since = -days
        context_note = (
            f"US midterm election scheduled date passed: 2026-11-03 "
            f"({days_since} days ago). "
            f"Policy cycle context only — no directional read."
        )
        context_note_zh = (
            f"美国中期选举预定日期已过：2026年11月3日（{days_since}天前）。"
            f"仅作政策周期背景参考，不作方向性判断。"
        )

    return {
        "days_to_midterm": days_to,
        "days_since_midterm": days_since,
        "event_date": event_date.isoformat(),
        "event_state": event_state,
        "evaluation_date": eval_date.isoformat(),
        "evaluated_at": _iso_utc(evaluation),
        "computed_at": _iso_utc(evaluation),
        "context_note": context_note,
        "context_note_zh": context_note_zh,
    }


def _build_levers(oil_arming: dict | None) -> list[dict]:
    """Build the levers array.

    Lever 1: Iran / oil (CL=F) — uses the W1-B arming block.
    Lever 2: China / tariffs — no technical asset; qualitative only.

    watch copy: unsigned factual text (PS-R1 no "intent"; PS-R4 no probabilities).
    """
    return [
        {
            "name": "Iran / oil",
            "name_zh": "伊朗/石油",
            "asset": "CL=F",
            "arming": oil_arming,
            "watch": (
                "Middle East escalation is the transmission channel to rate-cut repricing, "
                "with oil as the lever. A rapid CL=F spike would widen breakevens and reprice "
                "fed-funds futures, reversing the conditions that have supported the semis recovery."
            ),
            "watch_zh": (
                "中东局势升级是向降息重定价传导的通道，石油是核心杠杆。"
                "CL=F快速飙升将扩大盈亏平衡通胀预期并重定价联邦基金期货，"
                "逆转支撑半导体复苏的现有条件。"
            ),
            "copy_as_of": _CAPTION_AS_OF,
        },
        {
            "name": "China / tariffs",
            "name_zh": "中国/关税",
            "asset": None,
            "arming": None,
            "watch": (
                "US-China trade friction is the policy channel most directly tied to semis "
                "supply-chain margins: an escalation in tariffs or export controls would compress "
                "the margins priced into the current recovery."
            ),
            "watch_zh": (
                "中美贸易摩擦是与半导体供应链利润率关联最直接的政策渠道："
                "关税或出口管制的任何升级，都会压缩已计入当前复苏预期的利润率。"
            ),
            "copy_as_of": _CAPTION_AS_OF,
        },
    ]


def _compute_state(drawdown_pct: float | None, levers: list[dict]) -> str:
    """ARMED rule (frozen v1, PS-R9).

    favored_complex.drawdown_pct <= -15%  AND  any lever.arming.armed  → ARMED
    exactly ONE of the two conditions                                   → ELEVATED
    neither                                                             → QUIET
    """
    dd_armed = (drawdown_pct is not None) and (drawdown_pct <= _DRAWDOWN_THRESHOLD * 100)
    lever_armed = any(
        (lv.get("arming") or {}).get("armed", False) for lv in levers
    )
    if dd_armed and lever_armed:
        return "ARMED"
    if dd_armed or lever_armed:
        return "ELEVATED"
    return "QUIET"


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build() -> dict:
    """Assemble the full policy_lever artifact. Returns the dict."""
    root = config.ROOT
    alerts_path = root / "data" / "whitehouse" / "alerts.jsonl"

    # ONE evaluation instant for the whole build: every window bound, every
    # component date and every stamped timestamp below reads this value.
    evaluation = _utc_now()

    # 1. favored complex drawdown
    log.info("computing favored-complex drawdown (SMH/SOXX)…")
    fc = _compute_drawdown(["SMH", "SOXX"])
    # generation instant, distinct from fc["as_of"] (the price date / evidence)
    fc["computed_at"] = _iso_utc(evaluation)

    # 2. oil arming (W1-B engine path — same config as build_commodities)
    log.info("computing oil arming (CL=F technical_arming)…")
    oil_arming = _compute_oil_arming()

    # 3. jawboning
    log.info("reading whitehouse alerts (read-only)…")
    jawboning = _compute_jawboning(alerts_path, now=evaluation)

    # 4. calendar
    calendar = _compute_calendar(now=evaluation)

    # 5. levers
    levers = _build_levers(oil_arming)

    # 5a. stamp copy_age_days / copy_stale on each lever that has copy_as_of
    _today_utc = evaluation.date()
    for _lv in levers:
        _cao = _lv.get("copy_as_of")
        if not _cao:
            continue
        try:
            _age = max(0, (_today_utc - date.fromisoformat(_cao)).days)
            _lv["copy_age_days"] = _age
            _lv["copy_stale"] = _age > _CAPTION_STALE_DAYS
        except Exception:  # noqa: BLE001 — never raises
            pass

    # 6. state
    state = _compute_state(fc.get("drawdown_pct"), levers)

    # Top-level as_of keeps its price-date (evidence) meaning; computed_at is
    # the generation instant and is never presented as source freshness.
    price_as_of = fc.get("as_of")
    as_of = price_as_of or evaluation.strftime("%Y-%m-%d")

    artifact = {
        "schema": "policy_lever.v1",
        "as_of": as_of,
        "as_of_basis": "price_date" if price_as_of else "build_date_fallback",
        "computed_at": _iso_utc(evaluation),
        "favored_complex": fc,
        "jawboning": jawboning,
        "calendar": calendar,
        "levers": levers,
        "state": state,
        "framing": _FRAMING_EN,
        "framing_zh": _FRAMING_ZH,
    }
    return artifact


def main() -> int:
    """Build and write site/policy_lever.json. Returns 0 on success, 0 on non-fatal failure."""
    try:
        artifact = build()
    except Exception as e:  # noqa: BLE001 — never break the site build
        log.error("build_policy_lever failed (%s) — skipping site artifact", e)
        return 0

    # Write to site/policy_lever.json (atomic via temp file)
    root = config.ROOT
    cfg = config.load()
    site_dir_name = cfg.get("storage", {}).get("site_dir", "site")
    site_dir = root / site_dir_name
    site_dir.mkdir(parents=True, exist_ok=True)
    out = site_dir / "policy_lever.json"

    try:
        tmp = out.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(artifact, indent=2, default=str), encoding="utf-8")
        tmp.replace(out)
        log.info("wrote %s  (state=%s)", out, artifact.get("state"))
    except Exception as e:  # noqa: BLE001
        log.error("failed to write %s: %s", out, e)

    return 0


if __name__ == "__main__":
    sys.exit(main())

