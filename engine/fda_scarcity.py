"""FDA drug-scarcity read — per-theme physical feed for glp1_obesity (Wave 5b / §3.4).

Maps configured molecules onto scoped FDA regulator observations for the foresight theme
card. Source status, manufacturer availability, coverage, source generation and capture
freshness remain distinct; the legacy band below is retained only for incumbent consumers.

Display-only: no stage, rank, entry or size decision uses this module.

Usage: imported by foresight_cascade.py as a display chip via `theme_feed_summary` field,
mirroring how `altdata_summary` flows into cascade rows.
"""
from __future__ import annotations

import logging

import pandas as pd

log = logging.getLogger(__name__)

# ─── Extensible molecule → theme mapping ─────────────────────────────────────
# Keys are lowercase search tokens matched against generic_name (case-insensitive).
# Values are the theme keys they apply to. Add new molecules here to extend coverage.
MOLECULE_THEME_MAP: dict[str, list[str]] = {
    "semaglutide":  ["glp1_obesity"],
    "tirzepatide":  ["glp1_obesity"],
    "liraglutide":  ["glp1_obesity"],
}

from datetime import date, datetime, timedelta, timezone

SHORTAGE_ACTIVE = "SHORTAGE_ACTIVE"
SHORTAGE_RESOLVED = "SHORTAGE_RESOLVED"
BAND_NONE = "NONE"

_CURRENT_REPORTED = "CURRENT_REPORTED"
_RESOLVED_REPORTED = "RESOLVED_REPORTED"
_DISCONTINUATION_REPORTED = "DISCONTINUATION_REPORTED"
_MIXED_REPORTED = "MIXED_REPORTED"
_UNCLASSIFIED = "UNCLASSIFIED"
_NO_MATCHING_RECORDS = "NO_MATCHING_RECORDS"
_UNAVAILABLE = "UNAVAILABLE"

_STATUS_MAP = {
    "current": "current",
    "resolved": "resolved",
    "to be discontinued": "to_be_discontinued",
}
_AVAILABILITY_MAP = {
    "available": "available",
    "limited availability": "limited",
    "limited": "limited",
    "unavailable": "unavailable",
    "discontinued": "unavailable",
}


def _normalise_status(value):
    return _STATUS_MAP.get(str(value or "").strip().casefold(), "unrecognized")


def _normalise_availability(value):
    return _AVAILABILITY_MAP.get(str(value or "").strip().casefold(), "unknown")


def _generation(value):
    text = str(value or "")
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        try:
            return datetime.fromisoformat(text).date().isoformat()
        except ValueError:
            return None


def _finished_at(value):
    text = str(value or "")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _closed_rows(rows):
    if isinstance(rows, pd.DataFrame):
        records = rows.to_dict("records")
    else:
        records = list(rows or [])
    closed = []
    for row in records or []:
        get = row.get if isinstance(row, dict) else getattr(row, "get", None)
        if get is None:
            continue
        raw_availability = get("availability")
        availability = "" if pd.isna(raw_availability) else str(raw_availability or "")
        closed.append({
            "package_ndc": str(get("package_ndc") or ""),
            "generic_name": str(get("generic_name") or ""),
            "regulator_status": _normalise_status(get("status")),
            "regulator_status_raw": str(get("status") or ""),
            "manufacturer_availability": availability or None,
            "availability_normalized": _normalise_availability(availability),
            "observed_generation": _generation(get("observed_generation") or get("last_observed_generation")),
            "absent_since_generation": _generation(get("absent_since_generation")),
        })
    return closed


def _record_count(count):
    return f"{count} record" if count == 1 else f"{count} records"


def _duration_text(seconds):
    days = int(seconds // 86400)
    if days == 1:
        return ("1 d ago", "1天前")
    return (f"{days} d ago", f"{days}天前")


def _label(
    status, counts, generation, capture_qualified, unclassified_rows,
    capture_age_s=None, refresh_failed_at=None, observation_state=None,
):
    labels = {
        _CURRENT_REPORTED: ("FDA shortage: current ({current})", "FDA短缺：当前（{current}）"),
        _RESOLVED_REPORTED: ("FDA shortage: resolved ({resolved}) — supply status only", "FDA短缺：已解决（{resolved}）——仅供给状态"),
        _DISCONTINUATION_REPORTED: ("FDA: formulation discontinuation reported ({discontinued})", "FDA：已报告制剂停产（{discontinued}）"),
        _MIXED_REPORTED: ("FDA: mixed", "FDA：混合"),
        _UNCLASSIFIED: ("FDA: observed, status unclassified ({unrecognized})", "FDA：已观察到，状态未分类（{unrecognized}）"),
        _NO_MATCHING_RECORDS: ("FDA: no matching records", "FDA：无匹配记录"),
        _UNAVAILABLE: ("FDA source unavailable", "FDA来源不可用"),
    }
    english, chinese = labels[status]
    if status == _MIXED_REPORTED:
        # MIXED fires for current + (resolved OR discontinued), so the second component is
        # not always "resolved". Naming it unconditionally printed "resolved 0" next to the
        # word "mixed" and silently dropped the discontinuations — and under this program's
        # semantics a discontinuation is NOT a resolution. Enumerate only what is present.
        english_mix = [f"current {counts['current']}"]
        chinese_mix = [f"当前{counts['current']}"]
        if counts["resolved"]:
            english_mix.append(f"resolved {counts['resolved']}")
            chinese_mix.append(f"已解决{counts['resolved']}")
        if counts["discontinued"]:
            english_mix.append(f"discontinued {counts['discontinued']}")
            chinese_mix.append(f"停产{counts['discontinued']}")
        english = "FDA: mixed — " + " / ".join(english_mix)
        chinese = "FDA：混合——" + "／".join(chinese_mix)
    if status == _DISCONTINUATION_REPORTED and counts["resolved"] and counts["discontinued"]:
        english = "FDA: resolved {resolved} / discontinued {discontinued} — supply status only"
        chinese = "FDA：已解决{resolved}／停产{discontinued}——仅供给状态"
    english_parts = [english.format(**counts)]
    chinese_parts = [chinese.format(**counts)]
    if status == _UNAVAILABLE:
        if observation_state == "NOT_OBSERVED":
            english_parts[0] = "FDA source not yet observed — no qualified generation on file"
            chinese_parts[0] = "FDA来源尚未观测——无合格来源生成日期"
        elif observation_state == "UNREADABLE":
            english_parts[0] = "FDA source unavailable — last observation unreadable"
            chinese_parts[0] = "FDA来源不可用——上次观测无法读取"
        elif generation:
            english_parts[0] = f"FDA source unavailable — last qualified {generation}, refresh failed"
            chinese_parts[0] = f"FDA来源不可用——上次合格为{generation}，刷新失败"
        else:
            english_parts[0] = "FDA source unavailable — no qualified generation on file, refresh failed"
            chinese_parts[0] = "FDA来源不可用——无合格来源生成日期，刷新失败"
    elif generation:
        english_parts.append(f"source generation {generation}")
        chinese_parts.append(f"来源生成日期{generation}")
    elif capture_qualified is True:
        english_parts.append("source generation unknown")
        chinese_parts.append("来源生成日期未知")
    if capture_age_s is not None:
        english_age, chinese_age = _duration_text(capture_age_s)
        english_parts.insert(1, f"captured {english_age}")
        chinese_parts.insert(1, f"采集于{chinese_age}")
    if refresh_failed_at is not None:
        if status != _UNAVAILABLE:
            english_parts.append(f"refresh failed {refresh_failed_at}")
            chinese_parts.append(f"刷新失败 {refresh_failed_at}")
    if capture_qualified is None:
        english_parts.append("capture time unknown")
        chinese_parts.append("采集时间未知")
    if unclassified_rows == 1:
        english_parts.append("1 record unclassified")
        chinese_parts.append("1条记录未分类")
    elif unclassified_rows:
        english_parts.append(f"{unclassified_rows} records unclassified")
        chinese_parts.append(f"{unclassified_rows}条记录未分类")
    return " · ".join(english_parts), " · ".join(chinese_parts)


def summarize_supply(rows, *, capture, now, max_capture_age: timedelta | None) -> dict:
    """Summarize regulator status, manufacturer availability, coverage and freshness."""
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")
    capture = dict(capture) if capture is not None else None
    observation = capture or {}
    qualified = observation.get("qualified")
    if observation.get("observation_state") == "LEGACY":
        qualified = None
    failed_refresh = None
    if observation.get("refresh_failed"):
        failed_refresh = {
            "reason": str(observation.get("refresh_failure_code") or "refresh failed"),
            "failure_code": observation.get("refresh_failure_code"),
            "attempted_at": observation.get("refresh_at"),
        }

    closed = _closed_rows(rows)
    if (
        qualified is False
        and observation.get("observation_state") != "UNREADABLE"
        and observation.get("failure_code")
        and observation.get("source_generation")
        and closed
    ):
        qualified = True
        failed_refresh = {
            "reason": str(observation.get("failure_code")),
            "failure_code": observation.get("failure_code"),
            "attempted_at": observation.get("refresh_at"),
        }
    counts = {
        "current": sum(row["regulator_status"] == "current" for row in closed),
        "resolved": sum(row["regulator_status"] == "resolved" for row in closed),
        "discontinued": sum(row["regulator_status"] == "to_be_discontinued" for row in closed),
        "unrecognized": sum(row["regulator_status"] == "unrecognized" for row in closed),
        "matched": len(closed),
    }
    generation = _generation(observation.get("source_generation"))
    finished = _finished_at(observation.get("finished_at"))
    capture_age_s = max(0.0, (now - finished).total_seconds()) if finished else None
    stale = (
        capture_age_s > max_capture_age.total_seconds()
        if max_capture_age is not None and capture_age_s is not None else None
    )
    generation_age_days = (now.date() - date.fromisoformat(generation)).days if generation else None

    if qualified is False:
        source_status = _UNAVAILABLE
    elif not closed:
        source_status = _NO_MATCHING_RECORDS
    elif counts["current"] and (counts["resolved"] or counts["discontinued"]):
        source_status = _MIXED_REPORTED
    elif counts["current"]:
        source_status = _CURRENT_REPORTED
    elif counts["resolved"] and counts["discontinued"]:
        source_status = _DISCONTINUATION_REPORTED
    elif counts["resolved"]:
        source_status = _RESOLVED_REPORTED
    elif counts["discontinued"]:
        source_status = _DISCONTINUATION_REPORTED
    else:
        source_status = _UNCLASSIFIED

    unclassified_rows = counts["unrecognized"]
    refresh_failed_at = (
        failed_refresh.get("attempted_at")[:10]
        if failed_refresh and failed_refresh.get("attempted_at")
        else None
    )
    label, label_zh = _label(
        source_status, counts, generation, qualified, unclassified_rows,
        capture_age_s=capture_age_s, refresh_failed_at=refresh_failed_at,
        observation_state=observation.get("observation_state"),
    )
    return {
        "source_status": source_status,
        "rows": closed,
        "counts": counts,
        "coverage": {
            "molecules_checked": [],
            "molecules_with_rows": [],
            "matched_rows": len(closed),
            "unclassified_rows": unclassified_rows,
        },
        "freshness": {
            "capture_qualified": qualified,
            "capture_finished_at": finished.isoformat() if finished else None,
            "capture_age_s": capture_age_s,
            "source_generation": generation,
            "source_generation_age_days": generation_age_days,
            "stale": stale,
            "failed_refresh": failed_refresh,
        },
        "label": label,
        "label_zh": label_zh,
    }


def _all_themes():
    themes = set()
    for configured in MOLECULE_THEME_MAP.values():
        themes.update(configured)
    return sorted(themes)


def _observation_capture(observation, frame=None):
    if not observation:
        return None, None
    capture = dict(observation.get("capture") or {})
    last_refresh = observation.get("last_refresh") or {}
    qualified = (
        bool(capture)
        and not observation.get("inconsistent")
        and not observation.get("legacy")
        and isinstance(capture.get("source_generation"), str)
        and bool(capture.get("source_generation"))
    )
    refresh_failed = (
        observation.get("failed_refresh")
        or last_refresh.get("qualified") is False
    )
    if observation.get("inconsistent"):
        observation_state = "UNREADABLE"
    elif observation.get("legacy"):
        observation_state = "LEGACY" if frame is not None else "UNREADABLE"
    elif last_refresh.get("qualified") is False:
        observation_state = "REFRESH_FAILED"
    elif not last_refresh:
        observation_state = "LEGACY" if capture else "NOT_OBSERVED"
    elif not capture:
        observation_state = "UNREADABLE"
    elif qualified:
        observation_state = "QUALIFIED" if not refresh_failed else "REFRESH_FAILED"
    elif not refresh_failed:
        observation_state = "UNREADABLE"
    else:
        observation_state = "UNREADABLE"
    capture["qualified"] = qualified
    capture["observation_state"] = observation_state
    if observation.get("inconsistent"):
        capture["failure_code"] = capture.get("failure_code") or "inconsistent observation"
    if observation.get("read_error"):
        capture["failure_code"] = capture.get("failure_code") or str(observation["read_error"])
    if refresh_failed:
        capture["refresh_failed"] = True
        capture["refresh_failure_code"] = last_refresh.get("failure_code")
        capture["refresh_at"] = last_refresh.get("attempted_at")
    return capture, last_refresh


def compute_fda_scarcity(df: pd.DataFrame | None = None) -> dict[str, dict | None]:
    """Compute configured FDA observation rows for the incumbent visible consumer."""
    now = datetime.now(timezone.utc)
    capture = None
    last_refresh = None
    if df is None:
        try:
            from collectors.fda_shortages import read_shortage_observation
            state = read_shortage_observation(path=_shortages_path())
            frame = state.get("rows")
            observation = {
                "capture": state.get("capture"),
                "last_refresh": state.get("last_refresh"),
                "legacy": state.get("legacy", False),
                "inconsistent": state.get("inconsistent", False),
                "failed_refresh": False,
            }
            capture, last_refresh = _observation_capture(observation, frame=frame)
        except Exception as error:
            frame = None
            capture = {
                "qualified": False,
                "observation_state": "UNREADABLE",
                "failure_code": str(error),
            }
    else:
        frame = df
        capture, last_refresh = _observation_capture(
            df.attrs.get("fda_observation"), frame=df
        )

    records = frame.to_dict("records") if frame is not None else []
    all_themes = _all_themes()
    result = {}
    for theme in all_themes:
        molecules = [m for m, themes in MOLECULE_THEME_MAP.items() if theme in themes]
        rows = []
        molecules_with_rows = []
        for molecule in molecules:
            matched = [
                row for row in records
                if molecule.casefold() in str(row.get("generic_name") or "").casefold()
                or molecule.casefold() in str(row.get("substance_name") or "").casefold()
            ]
            if matched:
                molecules_with_rows.append(molecule)
                rows.extend(matched)
        summary = summarize_supply(rows, capture=capture, now=now, max_capture_age=None)
        summary["coverage"]["molecules_checked"] = molecules
        summary["coverage"]["molecules_with_rows"] = molecules_with_rows
        status = summary["source_status"]
        # Legacy bands preserve old consumers; they never drive FDA composition.
        band = SHORTAGE_ACTIVE if status in {_CURRENT_REPORTED, _MIXED_REPORTED} else (
            SHORTAGE_RESOLVED if status == _RESOLVED_REPORTED else BAND_NONE
        )
        details = [
            f"{row['generic_name']} [{row['regulator_status_raw']}/"
            f"{row['manufacturer_availability'] or 'not stated'}]"
            for row in summary["rows"][:3]
        ]
        counts = summary["counts"]
        rationale = {
            _CURRENT_REPORTED: f"regulator status: current ({_record_count(counts['current'])}) — supply status only",
            _RESOLVED_REPORTED: f"regulator status: resolved ({_record_count(counts['resolved'])}) — supply status only",
            _DISCONTINUATION_REPORTED: (
                f"regulator status: resolved ({_record_count(counts['resolved'])}) and "
                f"discontinued ({_record_count(counts['discontinued'])}) — supply status only"
                if counts["resolved"] and counts["discontinued"]
                else f"regulator status: discontinuation reported ({_record_count(counts['discontinued'])})"
            ),
            _MIXED_REPORTED: "regulator status: mixed — supply status only",
            _UNCLASSIFIED: "regulator status: observed but unclassified",
            _NO_MATCHING_RECORDS: "source status: no matching records",
            _UNAVAILABLE: "source status: unavailable",
        }[status]
        if last_refresh and not last_refresh.get("qualified"):
            summary["freshness"]["failed_refresh"] = {
                **(summary["freshness"]["failed_refresh"] or {}),
                "attempted_at": last_refresh.get("attempted_at"),
                "failure_code": last_refresh.get("failure_code"),
            }
        result[theme] = {
            "band": band,
            "source_status": status,
            "summary": summary,
            "n_active": summary["counts"]["current"],
            "n_resolved": summary["counts"]["resolved"],
            "n_discontinued": summary["counts"]["discontinued"],
            "details": details,
            "molecules_checked": molecules,
            "rationale": rationale,
        }
    return result


def _chip_rationale(status, counts):
    if status == _DISCONTINUATION_REPORTED and counts["resolved"] and counts["discontinued"]:
        return (
            f"The FDA reports {counts['resolved']} resolved and "
            f"{counts['discontinued']} discontinued formulations."
        )
    if status == _MIXED_REPORTED:
        # Same defect as the label: the fixed sentence claimed "current and resolved" even
        # when the mixture was current + discontinued and resolved was 0.
        if counts["resolved"] and counts["discontinued"]:
            return ("The FDA reports current shortages, resolved shortages and "
                    "formulation discontinuations.")
        if counts["discontinued"]:
            return "The FDA reports current shortages and formulation discontinuations."
        return "The FDA reports both current and resolved shortages."
    rationales = {
        _CURRENT_REPORTED: "The FDA reports a current shortage for this theme.",
        _RESOLVED_REPORTED: "The FDA reports the shortage as resolved.",
        _DISCONTINUATION_REPORTED: "The FDA reports a formulation discontinuation.",
        _MIXED_REPORTED: "The FDA reports both current and resolved shortages.",
        _UNCLASSIFIED: "The FDA observation is present but its status is not classified.",
        _NO_MATCHING_RECORDS: "No FDA records match this configured theme.",
        _UNAVAILABLE: "The FDA source is unavailable.",
    }
    return rationales[status]


def format_theme_feed_chip(scarcity_row: dict | None, theme_key: str) -> dict | None:
    """Render a non-None FDA observation row as the incumbent display chip."""
    if scarcity_row is None:
        return None
    summary = scarcity_row.get("summary")
    if summary is None:
        status = scarcity_row.get("source_status")
        if status is None:
            counts_for_status = {
                "current": int(scarcity_row.get("n_active") or 0),
                "resolved": int(scarcity_row.get("n_resolved") or 0),
                "discontinued": int(scarcity_row.get("n_discontinued") or 0),
            }
            if counts_for_status["discontinued"]:
                status = _DISCONTINUATION_REPORTED
            elif counts_for_status["current"] and counts_for_status["resolved"]:
                status = _MIXED_REPORTED
            elif counts_for_status["current"]:
                status = _CURRENT_REPORTED
            elif counts_for_status["resolved"]:
                status = _RESOLVED_REPORTED
            elif any(
                "under review" in str(value).casefold()
                for value in scarcity_row.get("details", [])
                if isinstance(value, str)
            ):
                status = _UNCLASSIFIED
            else:
                status = _NO_MATCHING_RECORDS
        counts = {
            "current": int(scarcity_row.get("n_active") or 0),
            "resolved": int(scarcity_row.get("n_resolved") or 0),
            "discontinued": int(scarcity_row.get("n_discontinued") or 0),
            "unrecognized": 0,
            "matched": int(scarcity_row.get("n_active") or 0)
            + int(scarcity_row.get("n_resolved") or 0)
            + int(scarcity_row.get("n_discontinued") or 0),
        }
        freshness = scarcity_row.get("freshness") or {}
        generation = freshness.get("source_generation")
        label, label_zh = _label(status, counts, generation, freshness.get("capture_qualified"), 0)
        summary = {
            "source_status": status,
            "counts": counts,
            "coverage": {
                "molecules_checked": scarcity_row.get("molecules_checked") or [],
                "molecules_with_rows": [],
                "matched_rows": counts["matched"],
                "unclassified_rows": 0,
            },
            "freshness": freshness,
            "label": label,
            "label_zh": label_zh,
        }
    status = summary["source_status"]
    tone = "warn" if status in {_CURRENT_REPORTED, _MIXED_REPORTED} else (
        "cool" if status == _RESOLVED_REPORTED else "mute"
    )
    rationale = _chip_rationale(status, summary["counts"])
    if not rationale.isascii():
        raise ValueError("FDA chip rationale must contain ASCII text only because it is rendered in the title attribute.")
    return {
        "source": "fda_shortages",
        "theme": theme_key,
        "band": scarcity_row.get("band", BAND_NONE),
        "label": summary["label"],
        "label_zh": summary["label_zh"],
        "tone": tone,
        "rationale": rationale,
        "n_active": summary["counts"]["current"],
        "n_resolved": summary["counts"]["resolved"],
        "source_status": status,
        "freshness": summary["freshness"],
    }


def _shortages_path():
    from collectors.fda_shortages import _shortages_path as path
    return path()
