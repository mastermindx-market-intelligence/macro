"""ROR-1 issue-time cutoff replay over ORIGINAL source-owned forward ledgers.

READ-ONLY retrospective research. It does NOT create a live session, user alert,
Chronicle episode, firing registry, delivery receipt, market forecast, or trade.
Current Git snapshots may contain later grading/corrections not visible at
original issue time. Filtering by the preserved recorded timestamp is only a
PIT proxy until authenticated historical source vintages are checked.

The independent expected MARKET session is deliberately *not* inferred from
the current local calendar date, because countries close in different zones
and exchanges have different holidays. A caller must never promote this
research result to current/fresh or decision authority.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping
from zoneinfo import ZoneInfo


class ReplayInputError(ValueError):
    pass


MARKET_TIMEZONE = {
    "us": "America/New_York",
    "cn": "Asia/Shanghai",
    "hk": "Asia/Hong_Kong",
    "ca": "America/Toronto",
}
BANDS = {"calm": 0, "watch": 1, "caution": 2, "elevated": 3, "risk-off": 4}
MAX_LEDGER_BYTES = 8 * 1024 * 1024


def _iso_date(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ReplayInputError(f"{label}: invalid source-session format")
    try:
        d = date.fromisoformat(value)
    except ValueError as e:
        raise ReplayInputError(f"{label}: invalid source session") from e
    if d.isoformat() != value:
        raise ReplayInputError(f"{label}: noncanonical date")
    return value


def _time(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise ReplayInputError(f"{label}: missing issue-time")
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise ReplayInputError(f"{label}: invalid issue-time") from e
    if d.tzinfo is None or d.utcoffset() is None:
        raise ReplayInputError(f"{label}: timezone required")
    return d.astimezone(timezone.utc)


def _market(key: Any) -> str:
    if key not in MARKET_TIMEZONE:
        raise ReplayInputError(f"not one of the explicitly bound market profiles: {key}")
    return str(key)


def _unique(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ReplayInputError(f"duplicate JSON key: {k}")
        out[k] = v
    return out


def _no_constant(token: str):
    raise ReplayInputError(f"nonfinite JSON numeric literal: {token}")


def _validate_rows(rows: Any, market: str) -> list[dict]:
    m = _market(market)
    if not isinstance(rows, list):
        raise ReplayInputError("source rows must be an array")
    if len(rows) > 100000:
        raise ReplayInputError("source rows exceed study limit")
    previous = ""
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ReplayInputError(f"row {index}: not an object")
        asof = _iso_date(row.get("asof"), f"row {index}")
        if previous and asof <= previous:
            raise ReplayInputError(f"row {index}: duplicate or non-monotonic source session")
        previous = asof
        if row.get("market", m) != m:
            raise ReplayInputError(f"row {index}: market identity mismatch")
        _time(row.get("logged_at"), f"row {index}")
        state = row.get("state")
        if state not in BANDS:
            raise ReplayInputError(f"row {index}: unregistered source-native state")
        if type(row.get("alert")) is not bool:
            raise ReplayInputError(f"row {index}: model alert flag is not boolean")
        top = row.get("top_score")
        if (top is not None and
                (type(top) not in (int, float) or not math.isfinite(top) or not (0 <= top <= 100))):
            raise ReplayInputError(f"row {index}: invalid source intensity")
    return rows


def read_ledger(path: Path | str, market: str) -> list[dict]:
    m = _market(market)
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_LEDGER_BYTES:
        raise ReplayInputError(f"{m}: missing or oversized evidence file")
    raw = path.read_bytes()
    try:
        lines = [json.loads(s, object_pairs_hook=_unique, parse_constant=_no_constant)
                 for s in raw.decode("utf-8").splitlines() if s.strip()]
    except (ValueError, UnicodeError, RecursionError) as e:
        raise ReplayInputError(f"{m}: invalid strict JSONL evidence") from e
    return _validate_rows(lines, m)


def as_recorded_at(rows: list[dict], market: str, cutoff: str) -> dict:
    """Latest eligible *recorded* source row by a UTC cutoff, not source freshness.

    The legally expected exchange settlement session and actual receipt time
    remain explicitly unverified even if source_session equals local calendar
    day, because holidays, opening hours, and delayed publication differ.
    """
    m = _market(market)
    due = _time(cutoff, "cutoff")
    source_rows = _validate_rows(rows, m)
    local_day = due.astimezone(ZoneInfo(MARKET_TIMEZONE[m])).date().isoformat()
    base = {
        "market": m, "evidence_role": "RETROSPECTIVE_ISSUE_TIME_CUTOFF_PROXY",
        "cutoff_utc": due.isoformat().replace("+00:00", "Z"),
        "local_calendar_day": local_day,
        "independent_expected_session_verified": False,
        "customer_delivery_verified": False,
        "forecast_efficacy_verified": False,
        "market_contagion_verified": False,
        "source_session": None, "model_alert": None, "state": None,
        "recorded_at_utc": None, "score_intensity_not_probability": None,
        "record_status": "NO_RECORDED_ISSUE",
    }
    # Source session order, NOT issue wall clock, controls which version is the
    # latest *once available*; late-entered observations never leak backwards.
    eligible = [row for row in source_rows
                if _time(row["logged_at"], "recorded time") <= due
                and row["asof"] <= local_day]
    if not eligible:
        return base
    r = eligible[-1]
    base.update(
        record_status="RECORDED_SOURCE_ISSUE", source_session=r["asof"],
        model_alert=r["alert"], state=r["state"],
        recorded_at_utc=_time(r["logged_at"], "recorded time").isoformat().replace("+00:00", "Z"),
        score_intensity_not_probability=r.get("top_score"),
    )
    return base


def as_recorded_matrix(logs_by_market: Mapping[str, list[dict]], cutoff: str) -> dict:
    if not isinstance(logs_by_market, Mapping):
        raise ReplayInputError("expected market-to-rows mapping")
    return {m: as_recorded_at(rows, m, cutoff) for m, rows in sorted(logs_by_market.items())}


def recorded_alert_transitions(rows: list[dict], market: str) -> list[dict]:
    """Characterize adjacent observed rows; no new durable episode or notification."""
    m = _market(market)
    rs = _validate_rows(rows, m)
    changes = []
    prev = None
    for row in rs:
        flagged = row["alert"]
        if prev is None:
            decision = "LEFT_CENSORED_ACTIVE_BASELINE" if flagged else "QUIET_BASELINE"
        elif flagged and not prev["alert"]:
            decision = "ALERT_ONSET_IN_RECORDS"
        elif not flagged and prev["alert"]:
            decision = "MODEL_ALERT_CEASED_IN_RECORDS"
        elif flagged and prev["alert"] and BANDS[row["state"]] > BANDS[prev["state"]]:
            decision = "ALERT_SEVERITY_UPGRADE"
        elif flagged:
            decision = "ALERT_CONTINUED"
        else:
            decision = "QUIET_OR_CAUTION_CHANGE"
        changes.append({
            "market": m, "source_session": row["asof"],
            "recorded_at_utc": _time(row["logged_at"], "recorded").isoformat().replace("+00:00", "Z"),
            "model_alert": flagged, "state": row["state"],
            "observed_transition": decision,
            "is_confirmed_natural_episode_onset": False,
            "user_recovery_authorized": False,
            "customer_delivery_verified": False,
        })
        prev = row
    return changes


def summarize_recorded_runs(rows: list[dict], market: str) -> dict:
    rs = _validate_rows(rows, _market(market))
    runs = []
    current = None
    for i, row in enumerate(rs):
        if row["alert"]:
            if current is None:
                current = {
                    "first_source_session": row["asof"],
                    "last_source_session": row["asof"],
                    "observed_rows": 0,
                    "left_censored_at_ledger_start": i == 0,
                    "continuity": "CONTIGUOUS_RECORDED_ROWS_NOT_TRADING_SESSIONS",
                    "user_notification_claim": False,
                }
            current["observed_rows"] += 1
            current["last_source_session"] = row["asof"]
        elif current:
            current["model_flag_later_off_in_recorded_row"] = True
            runs.append(current)
            current = None
    if current:
        current["model_flag_later_off_in_recorded_row"] = False
        runs.append(current)
    return {
        "market": market,
        "recorded_rows": len(rs),
        "source_model_alert_true_rows": sum(row["alert"] for row in rs),
        "runs": runs,
        "limitation": "Only recorded rows; not continuous sessions or notification events.",
    }


def weekday_cutoff_sweep(
    logs: Mapping[str, list[dict]], start: str, end: str, *,
    hour_utc: int = 17, joint_markets: tuple[str, ...] = ("cn", "hk"),
) -> dict:
    """Exploratory frequency of concurrent source flags on weekdays at UTC cutoff.

    Not an exchange-session calendar, independently labeled market negative
    control, realized crash frequency or a pre-registered forecast test. A
    persistent previous source flag may appear on multiple sampled weekdays;
    count *cutoff snapshots*, not fired notifications or market-day alerts.
    """
    start_day = date.fromisoformat(_iso_date(start, "window start"))
    end_day = date.fromisoformat(_iso_date(end, "window end"))
    if (end_day < start_day or (end_day - start_day).days > 183
            or type(hour_utc) is not int or not 0 <= hour_utc <= 23):
        raise ReplayInputError("invalid or oversized exploratory window")
    if (not isinstance(joint_markets, tuple) or not joint_markets
            or len(set(joint_markets)) != len(joint_markets)
            or not isinstance(logs, Mapping)):
        raise ReplayInputError("invalid or empty market-source universe")
    for m in joint_markets:
        _market(m)
        if m not in logs:
            raise ReplayInputError("a requested market is absent from the study source")
    # One validation per source, then the existing as_recorded_at performs
    # validation for each cutoff; the independent source vintage is unchanged.
    snapshots = []
    day = start_day
    while day <= end_day:
        if day.weekday() < 5:
            cutoff = datetime(day.year, day.month, day.day, hour_utc,
                              tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
            views = as_recorded_matrix(logs, cutoff)
            flag = [views[m]["model_alert"] for m in joint_markets]
            status = ("NOT_ALL_MODEL_FLAGS_TRUE" if any(v is False for v in flag)
                      else "UNAVAILABLE" if any(v is None for v in flag)
                      else "ALL_MODEL_FLAGS_TRUE")
            snapshots.append({
                "cutoff_utc": cutoff, "joint_status": status,
                "expected_exchange_sessions_verified": False,
                "selected_source_records": {
                    m: {"source_session": views[m]["source_session"],
                        "recorded_at_utc": views[m]["recorded_at_utc"],
                        "model_alert": views[m]["model_alert"],
                        "state": views[m]["state"]}
                    for m in sorted(views)
                },
            })
        day += timedelta(days=1)
    return {
        "schema": "ror1.exploratory_weekday_cutoff_frequency.v1",
        "window_start": start, "window_end": end, "cutoff_hour_utc": hour_utc,
        "joint_markets": list(joint_markets),
        "n_weekday_cutoffs": len(snapshots),
        "n_joint_source_flags_true": sum(s["joint_status"] == "ALL_MODEL_FLAGS_TRUE" for s in snapshots),
        "n_unknown_due_to_missing_issued_source": sum(s["joint_status"] == "UNAVAILABLE" for s in snapshots),
        "n_not_all_source_flags_true": sum(s["joint_status"] == "NOT_ALL_MODEL_FLAGS_TRUE" for s in snapshots),
        "snapshots": snapshots,
        "forecast_precision_established": False,
        "customer_delivery_established": False,
        "notes": [
            "Exploratory post-hoc window: not a preregistered negative-control sample.",
            "Weekdays exclude Saturday and Sunday in UTC, NOT exchange holidays or market sessions.",
            "Repeated true flags can reflect a retained earlier issue, not new daily issued alerts.",
            "No market outcome labels, user interruption costs, source corrections at prior Git vintages or actual delivery.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--cutoff", action="append", required=True,
                        help="UTC issue-time cutoff with timezone")
    parser.add_argument("--expected-source-blobs", type=Path, required=True,
                        help="read-only JSON manifest market->{filename,git_blob}")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--weekday-grid-start", help="exploratory UTC weekday date, not exchange session")
    parser.add_argument("--weekday-grid-end", help="exploratory UTC weekday date, not exchange session")
    parser.add_argument("--weekday-grid-hour-utc", type=int, default=17)
    parser.add_argument("--weekday-grid-joint", default="cn,hk",
                        help="comma-separated original market keys, default cn,hk")
    args = parser.parse_args()
    try:
        manifest = json.loads(args.expected_source_blobs.read_text())
        if not isinstance(manifest, dict) or not manifest:
            raise ReplayInputError("manifest must bind at least one market")
        logs: dict[str, list[dict]] = {}
        evidence: dict[str, dict] = {}
        for key, item in sorted(manifest.items()):
            m = _market(key)
            if not isinstance(item, dict):
                raise ReplayInputError("source item is not a mapping")
            name, expected = item.get("filename"), item.get("git_blob")
            if (not isinstance(name, str) or not re.fullmatch(r"source_forward_(us|cn|hk|ca)_9b255a5\.jsonl", name)
                    or name != f"source_forward_{m}_9b255a5.jsonl"
                    or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{40}", expected)):
                raise ReplayInputError("unrecognized or unsafe source identity")
            p = args.source_dir / name
            raw = p.read_bytes()
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            if blob != expected:
                raise ReplayInputError(f"{m}: original Git source content differs")
            logs[m] = read_ledger(p, m)
            evidence[m] = {
                "source_path": name, "source_git_blob": expected,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "recorded_run_summary": summarize_recorded_runs(logs[m], m),
            }
        views = {cut: as_recorded_matrix(logs, cut) for cut in args.cutoff}
        result = {
            "schema": "ror1.issue_time_cutoff_research.v1",
            "issuer_cutoff_proxy_not_historical_git_vintage": True,
            "actual_customer_delivery_proven": False,
            "market_calendar_session_qualification_proven": False,
            "country_sources": evidence,
            "as_recorded_views": views,
            "limitations": [
                "The current Git ledger may include later corrections/grades; issue-time filtering is not historical version proof.",
                "No exchange holiday session owner, actual source publisher, entitlement, cache, browser or notification receipt was inspected.",
                "No forecast, causal transmission, original market episode lifecycle or trading authority is inferred.",
            ],
        }
        if bool(args.weekday_grid_start) != bool(args.weekday_grid_end):
            raise ReplayInputError("weekday grid needs both start and end, or neither")
        if args.weekday_grid_start:
            joint = tuple(args.weekday_grid_joint.split(","))
            result["exploratory_weekday_grid"] = weekday_cutoff_sweep(
                logs, args.weekday_grid_start, args.weekday_grid_end,
                hour_utc=args.weekday_grid_hour_utc, joint_markets=joint,
            )
        out = args.output
        if out.exists():
            raise ReplayInputError("refusing to overwrite prior research receipt")
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": "RESEARCH_REPLAY_ONLY", "out": str(out),
                          "markets": list(logs), "cutoffs": list(views),
                          "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}, sort_keys=True))
    except (OSError, ValueError) as e:
        parser.exit(2, "ROR1_REPLAY_REFUSED: " + str(e) + "\n")


if __name__ == "__main__":
    main()
