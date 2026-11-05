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

import hashlib
import json
import logging
import math
import os
import random
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
# Keep this consumer dependency-light just like _INTL_MARKETS above. The enrolled
# writer→reader roundtrip test pins parity with risk_radar_audit.FORWARD_ISSUE_CONTRACT.
_FORWARD_ISSUE_CONTRACT = "risk_radar_forward_issue.v1"

# Preregistered 2026-09-24 before receipt-bearing prospective outcomes existed.
# This is a READINESS BAR, never automatic validation or authority.
_PROSPECTIVE_VALIDATION_PROTOCOL = "risk_radar_prospective_validation_readiness.v1"
_PROSPECTIVE_VALIDATION_PROTOCOL_COMMIT = "7bc85b604a130e01b57b45db1e6430c292874a41"
_PROSPECTIVE_MIN_ISSUED = 252
_PROSPECTIVE_MIN_SPAN_DAYS = 300
_PROSPECTIVE_MIN_GRADED = 200
_PROSPECTIVE_MIN_EVENTS = 20
_PROSPECTIVE_MIN_NON_EVENTS = 50
_PROSPECTIVE_MIN_EVENT_CLUSTERS = 5
_PROSPECTIVE_BOOT_DRAWS = 2000
_PROSPECTIVE_BOOT_SEED = 240924


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


def _sha256_token(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(ch in "0123456789abcdef" for ch in value)


def _prospective_issue(row: dict, day) -> tuple[dict | None, str | None]:
    """Validate the new forward-log issue receipt without upgrading legacy rows."""
    issue = row.get("forecast_issue")
    if not isinstance(issue, dict):
        return None, "missing_issue_receipt"
    if issue.get("contract") != _FORWARD_ISSUE_CONTRACT:
        return None, "wrong_issue_contract"
    if issue.get("model_contract") != "risk_radar_forward_model.v1":
        return None, "wrong_model_contract"
    if issue.get("risk_schema") != "risk_radar.v2":
        return None, "wrong_risk_schema"
    if issue.get("ledger_lane") != "nightly" or issue.get("first_writer_wins") is not True:
        return None, "wrong_issue_lane"
    epoch = issue.get("epoch")
    if not isinstance(epoch, str) or not epoch.strip():
        return None, "missing_issue_epoch"

    issued = _probability_clock(issue.get("issued_at"))
    logged = _probability_clock(row.get("logged_at"))
    if issued is None or logged is None or issued != logged:
        return None, "issue_clock_mismatch"
    lag = (issued.date() - day).days
    if lag < 0 or lag > 1:
        return None, "issue_not_session_timely"

    keys = (
        "engine_source_sha256", "source_bundle_sha256",
        "calibration_sha256", "model_fingerprint",
    )
    if not all(_sha256_token(issue.get(key)) for key in keys):
        return None, "invalid_model_digest"
    source_files = issue.get("source_files_sha256")
    if (
        not isinstance(source_files, dict)
        or not source_files
        or not all(
            isinstance(path, str) and path
            and _sha256_token(digest)
            for path, digest in source_files.items()
        )
    ):
        return None, "invalid_source_bundle"
    expected_bundle = hashlib.sha256(
        json.dumps(
            source_files, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    if issue["source_bundle_sha256"] != expected_bundle:
        return None, "source_bundle_mismatch"
    if source_files.get("engine/risk_radar.py") != issue["engine_source_sha256"]:
        return None, "engine_source_mismatch"
    identity = {
        "model_contract": issue["model_contract"],
        "risk_schema": issue["risk_schema"],
        "engine_source_sha256": issue["engine_source_sha256"],
        "source_bundle_sha256": issue["source_bundle_sha256"],
        "source_files_sha256": source_files,
        "calibration_sha256": issue["calibration_sha256"],
    }
    expected = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if issue["model_fingerprint"] != expected:
        return None, "model_fingerprint_mismatch"
    return issue, None



def _quantile(values: list[float], q: float) -> float:
    vals = sorted(float(v) for v in values)
    if not vals:
        raise ValueError("quantile requires data")
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * float(q)
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return vals[lo]
    weight = pos - lo
    return vals[lo] * (1.0 - weight) + vals[hi] * weight


def _moving_block_mean_ci(values: list[float], block: int, seed: int,
                          draws: int = _PROSPECTIVE_BOOT_DRAWS) -> list[float] | None:
    """90% circular moving-block CI for an overlapping daily sequence."""
    vals = [float(v) for v in values]
    if not vals or any(not math.isfinite(v) for v in vals):
        return None
    n = len(vals)
    block = max(1, min(int(block), n))
    rng = random.Random(int(seed))
    means = []
    blocks_needed = math.ceil(n / block)
    for _ in range(int(draws)):
        sample = []
        for _b in range(blocks_needed):
            start = rng.randrange(n)
            sample.extend(vals[(start + j) % n] for j in range(block))
        sample = sample[:n]
        means.append(sum(sample) / n)
    return [
        round(_quantile(means, 0.05), 8),
        round(_quantile(means, 0.95), 8),
    ]


def _event_cluster_count(sample: list[tuple], horizon: int) -> int:
    """Episode-like cluster count for overlapping event-positive issue rows."""
    positions = [i for i, row in enumerate(sample) if int(row[2]) == 1]
    if not positions:
        return 0
    clusters = 1
    prev = positions[0]
    for pos in positions[1:]:
        if pos - prev > int(horizon):
            clusters += 1
        prev = pos
    return clusters


def _empty_prospective_validation_readiness(status: str = "not_started") -> dict:
    return {
        "definition": _PROSPECTIVE_VALIDATION_PROTOCOL,
        "protocol_commit": _PROSPECTIVE_VALIDATION_PROTOCOL_COMMIT,
        "status": status,
        "promotion_review_eligible": False,
        "authority_h21_supportive": False,
        "full_surface_supportive": False,
        "current_model_validated": False,
        "public_validation_ready": False,
        "cohort": {
            "issued_n": 0,
            "span_days": None,
        },
        "thresholds": {
            "min_issued_sessions": _PROSPECTIVE_MIN_ISSUED,
            "min_span_days": _PROSPECTIVE_MIN_SPAN_DAYS,
            "min_graded_per_horizon": _PROSPECTIVE_MIN_GRADED,
            "min_event_rows": _PROSPECTIVE_MIN_EVENTS,
            "min_non_event_rows": _PROSPECTIVE_MIN_NON_EVENTS,
            "min_event_clusters": _PROSPECTIVE_MIN_EVENT_CLUSTERS,
            "bootstrap_draws": _PROSPECTIVE_BOOT_DRAWS,
            "bootstrap_block": "horizon",
        },
        "horizons": {},
        "note_en": (
            "Readiness only. Even mature supportive evidence requires a separate "
            "promotion decision; this field cannot validate the model automatically."
        ),
        "note_zh": (
            "仅表示证据成熟度。即使证据成熟且支持模型，仍需独立晋级决定；"
            "本字段不会自动把模型标记为已验证。"
        ),
    }


def _prospective_validation_readiness(
    cohort: list[tuple],
    samples_by_horizon: dict[str, list[tuple]],
    horizons: dict[str, dict],
) -> dict:
    """Preregistered non-authoritative readiness bar over the latest exact cohort."""
    if not cohort:
        return _empty_prospective_validation_readiness("not_started")

    issued_n = len(cohort)
    first_day, last_day = cohort[0][0], cohort[-1][0]
    span_days = int((last_day - first_day).days)
    common_mature = (
        issued_n >= _PROSPECTIVE_MIN_ISSUED
        and span_days >= _PROSPECTIVE_MIN_SPAN_DAYS
    )

    out = _empty_prospective_validation_readiness("not_mature")
    out["cohort"] = {
        "issued_n": issued_n,
        "span_days": span_days,
        "from": first_day.isoformat(),
        "through": last_day.isoformat(),
    }

    all_mature = True
    all_supportive = True
    for hkey, horizon in (("h5", 5), ("h10", 10), ("h21", 21)):
        sample = list(samples_by_horizon.get(hkey) or [])
        meta = horizons.get(hkey) or {}
        n = len(sample)
        events = sum(int(row[2]) for row in sample)
        non_events = n - events
        clusters = _event_cluster_count(sample, horizon)
        baseline_complete = (
            int(meta.get("paired_n") or 0) == n
            and int(meta.get("missing_baseline_n") or 0) == 0
        )
        integrity_complete = int(meta.get("excluded_n") or 0) == 0

        mature = bool(
            common_mature
            and n >= _PROSPECTIVE_MIN_GRADED
            and events >= _PROSPECTIVE_MIN_EVENTS
            and non_events >= _PROSPECTIVE_MIN_NON_EVENTS
            and clusters >= _PROSPECTIVE_MIN_EVENT_CLUSTERS
            and baseline_complete
            and integrity_complete
        )

        brier_delta = None
        brier_ci = None
        calibration_gap = None
        calibration_ci = None
        brier_supportive = False
        calibration_supportive = False

        if n and baseline_complete:
            paired = [
                (float(row[1]) - int(row[2])) ** 2
                - (float(row[3]) - int(row[2])) ** 2
                for row in sample
            ]
            residual = [float(row[1]) - int(row[2]) for row in sample]
            brier_delta = round(sum(paired) / n, 8)
            calibration_gap = round(sum(residual) / n, 8)
            if mature:
                brier_ci = _moving_block_mean_ci(
                    paired, horizon, _PROSPECTIVE_BOOT_SEED + horizon
                )
                calibration_ci = _moving_block_mean_ci(
                    residual, horizon, _PROSPECTIVE_BOOT_SEED + 100 + horizon
                )
                brier_supportive = bool(
                    brier_delta < 0 and brier_ci and brier_ci[1] < 0
                )
                calibration_supportive = bool(
                    calibration_ci
                    and calibration_ci[0] <= 0 <= calibration_ci[1]
                )

        supportive = bool(mature and brier_supportive and calibration_supportive)
        all_mature = all_mature and mature
        all_supportive = all_supportive and supportive
        out["horizons"][hkey] = {
            "n": n,
            "events": events,
            "non_events": non_events,
            "event_clusters": clusters,
            "baseline_complete": baseline_complete,
            "integrity_complete": integrity_complete,
            "mature": mature,
            "paired_brier_delta": brier_delta,
            "paired_brier_delta_ci90": brier_ci,
            "calibration_gap": calibration_gap,
            "calibration_gap_ci90": calibration_ci,
            "brier_supportive": brier_supportive,
            "calibration_supportive": calibration_supportive,
            "supportive": supportive,
        }

    out["authority_h21_supportive"] = bool(
        out["horizons"].get("h21", {}).get("supportive")
    )
    out["full_surface_supportive"] = bool(all_supportive)
    if not all_mature:
        out["status"] = "not_mature"
    elif all_supportive:
        out["status"] = "mature_supportive"
        out["promotion_review_eligible"] = True
    else:
        out["status"] = "mature_refuting"
    return out


def _prospective_probability_audit(rows: list, reference) -> dict:
    """Prospective same-model evidence from receipt-bearing forward-log rows.

    This establishes ledger issue timing and exact model identity only. It does
    not claim public-page publication timing or model validation.
    """
    from collections import Counter, defaultdict

    issue_excluded = Counter()
    dated = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict):
            issue_excluded["invalid_row"] += 1
            continue
        day = _probability_date(row.get("asof"))
        if day is None or day > reference:
            issue_excluded["invalid_or_future_date"] += 1
            continue
        dated[day].append(row)

    unique = []
    for day, group in sorted(dated.items()):
        try:
            same = len({
                json.dumps(r, sort_keys=True, separators=(",", ":"))
                for r in group
            }) == 1
        except (TypeError, ValueError):
            same = False
        if not same:
            issue_excluded["conflicting_duplicate_date"] += len(group)
            continue
        issue_excluded["identical_duplicate"] += len(group) - 1
        unique.append((day, group[0]))

    issued_rows = []
    for day, row in unique:
        issue, reason = _prospective_issue(row, day)
        if issue is None:
            issue_excluded[reason or "invalid_issue_receipt"] += 1
            continue
        issued_rows.append((day, row, issue))

    empty = {
        "definition": "us_issued_probability_prospective.v1",
        "status": "not_started",
        "ledger_issue_timing_verified": False,
        "public_publication_timing_verified": False,
        "current_model_validated": False,
        "latest_epoch": None,
        "latest_model_fingerprint": None,
        "latest_engine_source_sha256": None,
        "latest_source_bundle_sha256": None,
        "latest_calibration_sha256": None,
        "same_model_issued_n": 0,
        "same_model_graded_n": 0,
        "awaiting_maturity": 0,
        "prior_model_issued_n": 0,
        "model_fingerprints_seen": 0,
        "from": None,
        "through": None,
        "issue_excluded": dict(sorted(
            (k, v) for k, v in issue_excluded.items() if v
        )),
        "horizons": {},
        "validation_readiness": _empty_prospective_validation_readiness("not_started"),
        "note_en": (
            "Prospective same-model evidence has not started yet. Historical rows "
            "are not backfilled into this cohort."
        ),
        "note_zh": "前瞻性同模型证据尚未开始；历史记录不会被回填进该样本。",
    }
    if not issued_rows:
        return empty

    latest_day, _latest_row, latest_issue = max(
        issued_rows,
        key=lambda item: (
            item[0],
            _probability_clock(item[2].get("issued_at")),
        ),
    )
    latest_fp = latest_issue["model_fingerprint"]
    latest_epoch = latest_issue["epoch"]
    cohort = [
        (day, row, issue)
        for day, row, issue in issued_rows
        if issue.get("model_fingerprint") == latest_fp
        and issue.get("epoch") == latest_epoch
    ]

    graded_valid = []
    awaiting = 0
    grade_excluded = Counter()
    for day, row, issue in cohort:
        odds, grade = row.get("drawdown_prob"), row.get("graded")
        if not isinstance(odds, dict) or odds.get("measure") != _PROBABILITY_TARGET:
            grade_excluded["unmatched_target"] += 1
            continue
        if not isinstance(grade, dict):
            awaiting += 1
            continue
        issued = _probability_clock(issue.get("issued_at"))
        graded = _probability_clock(grade.get("graded_at"))
        if (
            issued is None or graded is None or issued > graded
            or graded.date() > reference
        ):
            grade_excluded["invalid_grade_receipt"] += 1
            continue
        graded_valid.append((day.isoformat(), odds, grade))

    def average(values):
        return round(sum(values) / len(values), 6) if len(values) >= _MIN_N else None

    horizons = {}
    samples_by_horizon = {}
    for horizon in ("h5", "h10", "h21"):
        excluded = grade_excluded.copy()
        sample = []
        for day, odds, grade in graded_valid:
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
        samples_by_horizon[horizon] = sample
        horizons[horizon] = {
            "n": len(sample),
            "excluded_n": sum(excluded.values()),
            "excluded": dict(sorted((k, v) for k, v in excluded.items() if v)),
            "from": sample[0][0] if sample else None,
            "through": sample[-1][0] if sample else None,
            "events": sum(s[2] for s in sample),
            "both_outcomes_present": 0 < sum(s[2] for s in sample) < len(sample),
            "mean_forecast": average([s[1] for s in sample]),
            "observed_rate": average([s[2] for s in sample]),
            "brier": average([(s[1] - s[2]) ** 2 for s in sample]),
            "paired_n": len(pairs),
            "missing_baseline_n": len(sample) - len(pairs),
            "paired_model_brier": average([(s[1] - s[2]) ** 2 for s in pairs]),
            "paired_base_brier": average([(s[3] - s[2]) ** 2 for s in pairs]),
            "paired_brier_delta": average([
                (s[1] - s[2]) ** 2 - (s[3] - s[2]) ** 2
                for s in pairs
            ]),
        }

    validation_readiness = _prospective_validation_readiness(
        cohort, samples_by_horizon, horizons
    )
    fingerprints = {issue["model_fingerprint"] for _, _, issue in issued_rows}
    return {
        "definition": "us_issued_probability_prospective.v1",
        "status": "accruing",
        "ledger_issue_timing_verified": True,
        "public_publication_timing_verified": False,
        "current_model_validated": False,
        "latest_epoch": latest_epoch,
        "latest_model_fingerprint": latest_fp,
        "latest_engine_source_sha256": latest_issue["engine_source_sha256"],
        "latest_source_bundle_sha256": latest_issue["source_bundle_sha256"],
        "latest_calibration_sha256": latest_issue["calibration_sha256"],
        "same_model_issued_n": len(cohort),
        "same_model_graded_n": len(graded_valid),
        "awaiting_maturity": awaiting,
        "prior_model_issued_n": len(issued_rows) - len(cohort),
        "model_fingerprints_seen": len(fingerprints),
        "from": cohort[0][0].isoformat() if cohort else None,
        "through": cohort[-1][0].isoformat() if cohort else None,
        "issue_excluded": dict(sorted(
            (k, v) for k, v in issue_excluded.items() if v
        )),
        "horizons": horizons,
        "validation_readiness": validation_readiness,
        "note_en": (
            "Prospective same-model ledger evidence. Issue timing is verified for "
            "the forward ledger, not public-page publication; validation remains "
            "false until a separate promotion law is satisfied."
        ),
        "note_zh": (
            "前瞻性同模型台账证据。仅验证前向台账的首发时点，不代表公开页面发布时间；"
            "在独立晋级规则满足前，模型验证状态保持为否。"
        ),
    }


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
        "prospective": _prospective_probability_audit(rows, reference),
        "note_en": "Historical issued odds, not a test of today's model. Daily windows overlap; publication timing is unverified.",
        "note_zh": "历史发布概率，并非当前模型验证。每日窗口重叠；首发时点未经核实。",
    }
