"""Risk Radar Scorecard — deterministic accuracy metrics over forward ledgers.

Reads the US and international forward-outcome ledgers (written by
engine/risk_radar_audit.py, engine/risk_radar_intl_audit.py) and the US
recovery log (engine/risk_radar_recovery_audit.py), then computes a pure-math
summary per the frozen contract in data/risk_radar/scorecard.json.

DISPLAY-TIER CONTEXT ACCRUAL — NOT a promotion claim.  No gate changes here.
Pure observation over already-graded rows.  No LLM, no signal origination.

Frozen schema: scorecard.json
  {schema, generated_at, markets: {us + _INTL_MARKETS keys: MARKET}}
  MARKET = {asof_last_row, monitoring: {log_fresh, last_logged_days_ago,
             ungraded_backlog, awaiting_maturity, backlog_cutoff_bd, graded_n},
            windows: {full: WINDOW, y1: WINDOW}}
  Market keys are ADDITIVE-ONLY under risk_radar_scorecard.v1: consumers read
  markets by key and must tolerate keys they don't know (never pattern-match
  the exact key set).  Removing or renaming a key requires a schema bump.
  WINDOW = {alerts, watch_caution, calm, by_scare, recovery}
  Each sub-block uses hit_rate/rate=null when n<5 (min-n honesty floor).

Never raises publicly: all errors are logged and produce fail-soft empty entries.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_SCHEMA = "risk_radar_scorecard.v1"
# Intl markets with a forward ledger at data/risk_radar_intl/<key>_forward_log.jsonl
# (written/graded by engine/risk_radar_intl_audit.py).  Mirror of
# engine/risk_radar_intl.PROFILES keys — not imported so this module stays
# dependency-light and fail-soft.  Additive-only under risk_radar_scorecard.v1.
_INTL_MARKETS = ("cn", "hk", "ca", "kr", "jp", "tw", "in", "au", "gb", "ez")
_MIN_N = 5          # minimum rows before computing a rate (honesty floor)
_ALERT_STATES = frozenset(("elevated", "risk-off"))
_WATCH_CAUTION_STATES = frozenset(("watch", "caution"))
_LOG_FRESH_DAYS = 3     # last row this many days old or less = fresh
# A row CANNOT be graded until its longest horizon matures — engine/risk_radar_audit.HORIZONS
# tops out at 21 BUSINESS days (_grade_entry returns None before then). The backlog test used 7
# CALENDAR days, so every row between ~1 and ~5 weeks old counted as "backlog": steady state read
# as a stalled grader (audit 2026-07-29). Both numbers are now business days, and the maturation
# horizon is named rather than folded into one magic constant. The 7 is unchanged — it is now
# SLACK BEYOND maturation, which is what the original comment meant it to be.
_UNGRADED_MATURATION_BD = 21   # mirrors max(risk_radar_audit.HORIZONS) — not a tunable
_UNGRADED_BACKLOG_AGE = 7      # business days of slack past maturation before a row is backlog


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _repo_root(root=None) -> Path:
    if root is not None:
        return Path(root)
    try:
        from lib import config  # noqa: PLC0415
        return config.ROOT
    except Exception:  # noqa: BLE001
        return Path(__file__).resolve().parent.parent


def _data_root(root=None) -> Path:
    if root is not None:
        return Path(root) / "data"
    try:
        from lib import config  # noqa: PLC0415
        return config.data_dir()
    except Exception:  # noqa: BLE001
        return _repo_root(root) / "data"


def _site_root(root=None) -> Path:
    if root is not None:
        return Path(root) / "site"
    try:
        from lib import config  # noqa: PLC0415
        return config.ROOT / config.load()["storage"]["site_dir"]
    except Exception:  # noqa: BLE001
        return _repo_root(root) / "site"


def _us_forward_path(root=None) -> Path:
    return _data_root(root) / "risk_radar" / "forward_log.jsonl"


def _us_recovery_path(root=None) -> Path:
    return _data_root(root) / "risk_radar" / "recovery_log.jsonl"


def _intl_forward_path(market: str, root=None) -> Path:
    return _data_root(root) / "risk_radar_intl" / f"{market}_forward_log.jsonl"


def _scorecard_data_path(root=None) -> Path:
    p = _data_root(root) / "risk_radar" / "scorecard.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _scorecard_site_path(root=None) -> Path:
    p = _site_root(root) / "riskdata" / "scorecard.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# JSONL reader — skip malformed lines, never raises
# ---------------------------------------------------------------------------

def _read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    rows: list[dict] = []
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass
    return rows


# ---------------------------------------------------------------------------
# Monitoring block
# ---------------------------------------------------------------------------

def _bd_between(d0, d1) -> int:
    """Business days (Mon-Fri, no holiday calendar) strictly after d0 through d1; 0 if d1 <= d0.

    Deliberately calendar-free: the grader's maturation horizon is counted in trading bars off
    the SPY index, and a Mon-Fri count is the closest holiday-free approximation. It can only
    OVER-count (holidays are counted as business days), so the backlog test stays conservative —
    it will never flag a row as stalled earlier than the trading calendar would."""
    try:
        from datetime import timedelta  # noqa: PLC0415
        if d1 <= d0:
            return 0
        days = (d1 - d0).days
        weeks, rem = divmod(days, 7)
        n = weeks * 5
        for i in range(rem):
            if (d0 + timedelta(days=i + 1)).weekday() < 5:
                n += 1
        return n
    except Exception:  # noqa: BLE001
        return 0


def _monitoring(rows: list[dict], today=None) -> dict:
    """Compute the monitoring meta-block for a ledger's rows (all rows, not just graded).

    `today` is the reference date; None = wall clock. Threaded so the block is reproducible
    from the ledger alone (a scorecard rebuilt tomorrow off the same rows must not drift)."""
    try:
        from datetime import date  # noqa: PLC0415
        today = today or date.today()

        # Last row age
        last_logged_days_ago: int | None = None
        log_fresh = False
        asof_last_row: str | None = None
        if rows:
            last_asof = rows[-1].get("asof")
            asof_last_row = str(last_asof) if last_asof else None
            if last_asof:
                try:
                    asof_date = date.fromisoformat(str(last_asof)[:10])
                    last_logged_days_ago = (today - asof_date).days
                    log_fresh = last_logged_days_ago <= _LOG_FRESH_DAYS
                except Exception:  # noqa: BLE001
                    pass

        # Ungraded backlog: rows still ungraded MORE than (maturation + slack) BUSINESS days
        # after their as-of. A row younger than the 21-bd maturation horizon is not a backlog —
        # the grader is structurally unable to score it yet (risk_radar_audit._grade_entry
        # returns None). Counting those as backlog made steady state look like a stall.
        cutoff_bd = _UNGRADED_MATURATION_BD + _UNGRADED_BACKLOG_AGE
        ungraded_backlog = 0
        awaiting_maturity = 0
        for r in rows:
            if r.get("graded") is not None:
                continue
            asof_str = r.get("asof")
            if not asof_str:
                continue
            try:
                asof_date = date.fromisoformat(str(asof_str)[:10])
                if _bd_between(asof_date, today) > cutoff_bd:
                    ungraded_backlog += 1
                else:
                    awaiting_maturity += 1
            except Exception:  # noqa: BLE001
                pass

        graded_n = sum(1 for r in rows if r.get("graded") is not None)

        return {
            "log_fresh": log_fresh,
            "last_logged_days_ago": last_logged_days_ago,
            "ungraded_backlog": ungraded_backlog,
            # ungraded but not yet maturable — the honest "working as designed" bucket that the
            # old calendar-day test folded into `ungraded_backlog`.
            "awaiting_maturity": awaiting_maturity,
            "backlog_cutoff_bd": cutoff_bd,
            "graded_n": graded_n,
        }
    except Exception as e:  # noqa: BLE001
        log.warning("scorecard _monitoring failed: %s", e)
        return {"log_fresh": False, "last_logged_days_ago": None, "ungraded_backlog": 0,
                "awaiting_maturity": 0, "backlog_cutoff_bd": None, "graded_n": 0}


# ---------------------------------------------------------------------------
# Window math helpers
# ---------------------------------------------------------------------------

def _rate(num: int, denom: int) -> float | None:
    if denom < _MIN_N:
        return None
    return round(num / denom, 3)


def _alerts_block(graded: list[dict]) -> dict:
    """Alert window: rows with state in (elevated, risk-off)."""
    alert_rows = [r for r in graded if r.get("state") in _ALERT_STATES]
    n = len(alert_rows)
    tp = sum(1 for r in alert_rows if (r.get("graded") or {}).get("outcome") == "true_positive")
    fp = sum(1 for r in alert_rows if (r.get("graded") or {}).get("outcome") == "false_positive")
    return {"n": n, "tp": tp, "fp": fp, "hit_rate": _rate(tp, n)}


def _watch_caution_block(graded: list[dict]) -> dict:
    """Watch/caution window."""
    wc_rows = [r for r in graded if r.get("state") in _WATCH_CAUTION_STATES]
    n = len(wc_rows)
    tp = sum(1 for r in wc_rows if (r.get("graded") or {}).get("outcome") == "tp_watch")
    tn = sum(1 for r in wc_rows if (r.get("graded") or {}).get("outcome") == "tn_watch")
    return {"n": n, "tp": tp, "tn": tn, "precursor_rate": _rate(tp, n)}


def _calm_block(graded: list[dict]) -> dict:
    """Calm window: rows with state not in alert or watch/caution."""
    calm_rows = [r for r in graded
                 if r.get("state") not in _ALERT_STATES
                 and r.get("state") not in _WATCH_CAUTION_STATES]
    n = len(calm_rows)
    dd_missed = sum(1 for r in calm_rows if (r.get("graded") or {}).get("outcome") == "calm_dd")
    quiet = sum(1 for r in calm_rows if (r.get("graded") or {}).get("outcome") == "calm_quiet")
    return {"n": n, "dd_missed": dd_missed, "quiet": quiet, "quiet_rate": _rate(quiet, n)}


def _by_scare_block(graded: list[dict]) -> dict:
    """Per-dominant-scare breakdown for alert rows only."""
    alert_rows = [r for r in graded if r.get("state") in _ALERT_STATES]
    by_scare: dict[str, Any] = {}
    for r in alert_rows:
        scare = r.get("dominant_scare")
        if not scare:
            continue
        entry = by_scare.setdefault(scare, {"n": 0, "tp": 0, "fp": 0})
        entry["n"] += 1
        outcome = (r.get("graded") or {}).get("outcome")
        if outcome == "true_positive":
            entry["tp"] += 1
        elif outcome == "false_positive":
            entry["fp"] += 1
    result: dict[str, Any] = {}
    for scare, d in by_scare.items():
        result[scare] = {
            "n": d["n"],
            "tp": d["tp"],
            "fp": d["fp"],
            "hit_rate": _rate(d["tp"], d["n"]),
        }
    return result


def _recovery_block(recovery_rows: list[dict]) -> dict | None:
    """Recovery log summary: n graded, n ok (h21 fwd_ret > 0), rate."""
    graded = [r for r in recovery_rows if r.get("graded") is not None]
    if not graded:
        return None
    n = len(graded)
    ok = 0
    for r in graded:
        g = r.get("graded") or {}
        h21 = g.get("h21") or {}
        fwd_ret = h21.get("fwd_ret")
        if fwd_ret is not None and fwd_ret > 0:
            ok += 1
    return {"n": n, "ok": ok, "rate": _rate(ok, n)}


# ---------------------------------------------------------------------------
# Window builder for a set of graded rows + an optional cutoff
# ---------------------------------------------------------------------------

def _window(graded: list[dict], recovery_rows: list[dict] | None) -> dict:
    return {
        "alerts": _alerts_block(graded),
        "watch_caution": _watch_caution_block(graded),
        "calm": _calm_block(graded),
        "by_scare": _by_scare_block(graded),
        "recovery": _recovery_block(recovery_rows or []),
    }


def _trailing_365(all_graded: list[dict], today=None) -> list[dict]:
    """Filter to rows with asof within the trailing 365 calendar days.

    `today` is the reference date (None = wall clock). Threaded so ONE reference date serves the
    whole build instead of three independent date.today() reads that could straddle midnight and
    produce a scorecard whose monitoring block and y1 window disagree about what day it is."""
    try:
        from datetime import date, timedelta  # noqa: PLC0415
        cutoff = ((today or date.today()) - timedelta(days=365)).isoformat()
        return [r for r in all_graded if str(r.get("asof", "")) >= cutoff]
    except Exception:  # noqa: BLE001
        return []


def _trailing_365_recovery(recovery_graded: list[dict], today=None) -> list[dict]:
    """Filter recovery graded rows to trailing 365 days. See _trailing_365 re `today`."""
    try:
        from datetime import date, timedelta  # noqa: PLC0415
        cutoff = ((today or date.today()) - timedelta(days=365)).isoformat()
        return [r for r in recovery_graded if str(r.get("asof", "")) >= cutoff]
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------------------
# Per-market builder
# ---------------------------------------------------------------------------

def _market_entry(
    market: str,
    forward_path: Path,
    recovery_path: Path | None = None,
    today=None,
) -> dict:
    """Build one MARKET block. Never raises; returns fail-soft entry on any error.

    `today` is the ONE reference date for the whole build (None = wall clock) — see
    _trailing_365. The monitoring block deliberately measures against the real clock by
    default: a ledger that stopped writing must read stale, so it can never be anchored to
    the ledger's own newest row (that would make every dead ledger look fresh)."""
    try:
        all_rows = _read_jsonl(forward_path)
        if not all_rows and not forward_path.exists():
            # Missing ledger: fail-soft
            return {
                "asof_last_row": None,
                "monitoring": {"log_fresh": False, "last_logged_days_ago": None,
                               "ungraded_backlog": 0, "awaiting_maturity": 0,
                               "backlog_cutoff_bd": None, "graded_n": 0},
                "windows": {"full": _window([], []), "y1": _window([], [])},
                **({"probability_audit": probability_audit([], today)} if market == "us" else {}),
            }

        monitoring = _monitoring(all_rows, today=today)
        # Filter defensively: graded must be a dict; a corrupt scalar value (e.g.
        # graded='CORRUPT') drops that single row without aborting the whole market.
        graded = [r for r in all_rows if isinstance(r.get("graded"), dict)]

        # Recovery rows (US only; intl markets pass None)
        recovery_all: list[dict] = []
        if recovery_path is not None:
            recovery_all = _read_jsonl(recovery_path)
        recovery_graded = [r for r in recovery_all if r.get("graded") is not None]

        asof_last_row = str(all_rows[-1].get("asof")) if all_rows else None
        y1_graded = _trailing_365(graded, today=today)
        y1_recovery = _trailing_365_recovery(recovery_graded, today=today)

        return {
            "asof_last_row": asof_last_row,
            "monitoring": monitoring,
            "windows": {
                "full": _window(graded, recovery_graded),
                "y1": _window(y1_graded, y1_recovery),
            },
            **({"probability_audit": probability_audit(all_rows, today)} if market == "us" else {}),
        }
    except Exception as e:  # noqa: BLE001
        log.warning("scorecard _market_entry(%s) failed: %s", market, e)
        return {
            "asof_last_row": None,
            "monitoring": {"log_fresh": False, "last_logged_days_ago": None,
                           "ungraded_backlog": 0, "awaiting_maturity": 0,
                           "backlog_cutoff_bd": None, "graded_n": 0},
            "windows": {"full": _window([], []), "y1": _window([], [])},
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build(root=None, today=None) -> dict:
    """Build and return the scorecard dict. Never raises.

    `today` pins the reference date for every window + monitoring block in ONE place
    (None = wall clock), so the whole scorecard is reproducible and testable."""
    try:
        from datetime import date as _date  # noqa: PLC0415
        today = today or _date.today()
        markets: dict[str, dict] = {
            "us": _market_entry(
                "us",
                _us_forward_path(root),
                _us_recovery_path(root),
                today=today,
            ),
        }
        for mkt in _INTL_MARKETS:
            markets[mkt] = _market_entry(mkt, _intl_forward_path(mkt, root), today=today)

        return {
            "schema": _SCHEMA,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "markets": markets,
        }
    except Exception as e:  # noqa: BLE001
        log.warning("risk_radar_scorecard.build failed: %s", e)
        return {
            "schema": _SCHEMA,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "markets": {m: {} for m in ("us", *_INTL_MARKETS)},
        }


def _atomic_write(path: Path, payload: str) -> None:
    """Write JSON to path atomically via tmp+rename. Never raises."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            os.write(fd, payload.encode("utf-8"))
        finally:
            os.close(fd)
        os.replace(tmp, path)
    except Exception as e:  # noqa: BLE001
        log.warning("scorecard atomic write to %s failed: %s", path, e)
        try:
            os.unlink(tmp)
        except Exception:  # noqa: BLE001
            pass


def write(root=None) -> dict:
    """Build the scorecard, write atomically to both data/ and site/riskdata/ copies.

    Returns the scorecard dict. Never raises.

    Multi-writer convergence semantics: build_china, build_hk, and build_canada each
    call write() once per nightly run (right after their respective audit/tune block).
    Each call re-reads ALL market ledgers from disk, so whichever write lands last
    captures the most up-to-date state for every market seen so far.  The tmp+rename
    atomic write guarantees no reader ever sees a partial file.  Last writer wins;
    the operation is idempotent given the same ledger content.
    """
    try:
        sc = build(root)
        payload = json.dumps(sc, indent=2, default=str)
        _atomic_write(_scorecard_data_path(root), payload)
        _atomic_write(_scorecard_site_path(root), payload)
        log.info(
            "risk_radar_scorecard: wrote scorecard (graded_n: %s)",
            ", ".join(
                f"{m}={((sc.get('markets') or {}).get(m) or {}).get('monitoring', {}).get('graded_n')}"
                for m in ("us", *_INTL_MARKETS)
            ),
        )
        return sc
    except Exception as e:  # noqa: BLE001
        log.warning("risk_radar_scorecard.write failed: %s", e)
        return {}

# Issued-probability diagnostics. Display-only; never a forecast or promotion gate.
# Protocol: research/grey_deer/RISK_RADAR_PROBABILITY_AUDIT_PREREG_2026-09-20.md.
_PROBABILITY_BINS = ((0., .1), (.1, .2), (.2, .4), (.4, .6), (.6, 1.))
_PROBABILITY_TARGET = ">=5% SPY pullback (empirical 2006-2026; rises with intensity + conjunction)"


def _probability_number(value: Any) -> bool:
    import math
    try:
        return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1
    except (OverflowError, TypeError):
        return False


def _probability_date(value: Any):
    from datetime import date
    try:
        parsed = date.fromisoformat(value)
        return parsed if parsed.isoformat() == value else None
    except (TypeError, ValueError):
        return None


def _probability_clock(value: Any):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.utcoffset() is not None else None
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def probability_audit(rows: list, today=None) -> dict:
    """Score issued US odds against recorded boolean outcomes; no ledger I/O.

    Daily windows overlap. Receipt chronology does not establish first-publication
    timing or a homogeneous model version. This is not out-of-sample validation.
    """
    from collections import Counter, defaultdict
    from datetime import date
    reference = today or date.today()
    common = Counter()
    dated = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict):
            common["invalid_row"] += 1
            continue
        day = _probability_date(row.get("asof"))
        if day is None or day > reference:
            common["invalid_or_future_date"] += 1
            continue
        dated[day].append(row)
    unique = []
    for day, group in sorted(dated.items()):
        try:
            same = len({json.dumps(r, sort_keys=True, separators=(",", ":")) for r in group}) == 1
        except (TypeError, ValueError):
            same = False
        if not same:
            common["conflicting_duplicate_date"] += len(group)
            continue
        common["identical_duplicate"] += len(group) - 1
        unique.append((day, group[0]))
    valid = []
    for day, row in unique:
        odds, grade = row.get("drawdown_prob"), row.get("graded")
        if not isinstance(odds, dict) or odds.get("measure") != _PROBABILITY_TARGET:
            common["unmatched_target"] += 1
            continue
        if not isinstance(grade, dict):
            common["ungraded"] += 1
            continue
        issued = _probability_clock(row.get("logged_at"))
        graded = _probability_clock(grade.get("graded_at"))
        if (issued is None or graded is None or issued > graded or
                day > issued.date() or graded.date() > reference):
            common["invalid_or_future_receipt"] += 1
            continue
        valid.append((day.isoformat(), odds, grade))
    def average(values):
        return round(sum(values) / len(values), 6) if len(values) >= _MIN_N else None
    horizons = {}
    for horizon in ("h5", "h10", "h21"):
        excluded, sample = common.copy(), []
        for day, odds, grade in valid:
            p = odds.get(horizon)
            hit = grade.get("hit")
            outcome = hit.get(horizon) if isinstance(hit, dict) else None
            y = outcome.get("dd5") if isinstance(outcome, dict) else None
            if not _probability_number(p):
                excluded["invalid_probability"] += 1
            elif type(y) is not bool:
                excluded["missing_boolean_outcome"] += 1
            else:
                sample.append((day, p, int(y), odds.get("base_" + horizon)))
        pairs = [s for s in sample if _probability_number(s[3])]
        bins = []
        for low, high in _PROBABILITY_BINS:
            group = [s for s in sample if low <= s[1] < high or (high == 1 and s[1] == 1)]
            bins.append({"lower": low, "upper": high, "upper_inclusive": high == 1,
                         "n": len(group), "mean_forecast": average([s[1] for s in group]),
                         "observed_rate": average([s[2] for s in group])})
        horizons[horizon] = {
            "n": len(sample), "excluded_n": sum(excluded.values()),
            "excluded": dict(sorted((k, v) for k, v in excluded.items() if v)),
            "from": sample[0][0] if sample else None, "through": sample[-1][0] if sample else None,
            "events": sum(s[2] for s in sample),
            "both_outcomes_present": 0 < sum(s[2] for s in sample) < len(sample),
            "mean_forecast": average([s[1] for s in sample]),
            "observed_rate": average([s[2] for s in sample]),
            "brier": average([(s[1] - s[2]) ** 2 for s in sample]),
            "paired_n": len(pairs), "missing_baseline_n": len(sample) - len(pairs),
            "paired_model_brier": average([(s[1] - s[2]) ** 2 for s in pairs]),
            "paired_base_brier": average([(s[3] - s[2]) ** 2 for s in pairs]),
            "paired_brier_delta": average([(s[1] - s[2]) ** 2 - (s[3] - s[2]) ** 2 for s in pairs]),
            "bins": bins,
        }
    return {
        "definition": "us_issued_probability_audit.v1", "as_of": reference.isoformat(),
        "target": "SPY close-relative loss >=5%; future 5/10/21 closing observations",
        "input_rows": len(rows), "min_display_n": _MIN_N, "horizons": horizons,
        "status": "descriptive_only", "sample_unit": "overlapping_daily_forecast",
        "publication_timing_verified": False, "current_model_validated": False,
        "note_en": "Historical issued odds, not a test of today's model. Daily windows overlap; publication timing is unverified.",
        "note_zh": "历史发布概率，并非当前模型验证。每日窗口重叠；首发时点未经核实。",
    }
