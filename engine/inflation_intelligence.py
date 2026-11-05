"""Display-only inflation-state bridge for Release Radar.

``inflation_intelligence.v1`` deliberately keeps three different clocks apart:

``released_state``
    Latest locally stored official CPI index history and exact released 3m/6m
    annualized trends.  The local FRED files are latest-revision data, not an
    original-release vintage, and the artifact says so.

``next_release_forecast``
    The earliest upcoming CPI release in Release Radar, including the immutable
    forecast path reconstructed from its append-only forward ledger.

``current_month_proxy_pressure``
    Public-data/model pressure for the in-progress reference month.  It is
    explicitly *not* an official CPI observation or a substitute for one.

All reads are fail-open.  Missing/corrupt inputs produce null/empty blocks plus
structured gaps; they never promote a proxy into a fact and never confer signal
authority.
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

SCHEMA = "inflation_intelligence.v1"
DEFAULT_OUTPUT = Path("data/release_forecast/inflation_intelligence.json")
DEFAULT_RADAR_LATEST = Path("data/release_forecast/latest.json")
DEFAULT_FORWARD_LEDGER = Path("data/release_forecast/forward_ledger.jsonl")

_FRED_SERIES = {
    "headline": ("CPIAUCSL", "headline_cpi"),
    "core": ("CPILFESL", "core_cpi"),
    "sticky": ("STICKCPIM157SFRBATL", "sticky_cpi"),
    "flexible": ("FLEXCPIM157SFRBATL", "flex_cpi"),
}

_AUTHORITY_NOTE = (
    "DISPLAY-ONLY context. This artifact may describe released inflation, an upcoming "
    "Release Radar forecast, and in-progress proxy pressure. It may not originate, "
    "rank, size, gate, escalate, or execute a signal or trade."
)


def _repo_root(root: str | Path | None) -> Path:
    return Path(root) if root is not None else Path(__file__).resolve().parent.parent


def _resolve(repo: Path, path: str | Path | None, default: Path) -> Path:
    candidate = Path(path) if path is not None else default
    return candidate if candidate.is_absolute() else repo / candidate


def _path_label(repo: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def _number(value: Any, digits: int = 6) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return round(result, digits)


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    try:
        return pd.Timestamp(value).date()
    except Exception:  # noqa: BLE001 - date parsing is a fail-open boundary
        return None


def _parse_ledger_asof(value: Any) -> date | None:
    """Parse a full ISO ledger day/timestamp; reject partial or numeric clocks."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    token = value.strip()
    if len(token) < 10 or (len(token) > 10 and token[10] not in {"T", " "}):
        return None
    try:
        return date.fromisoformat(token[:10])
    except ValueError:
        return None


def _month_age(observation_period: str | None, as_of: date) -> int | None:
    if not observation_period:
        return None
    try:
        period = pd.Period(observation_period, freq="M")
    except Exception:  # noqa: BLE001
        return None
    return (as_of.year - period.year) * 12 + as_of.month - period.month


def _monthly_freshness(age_months: int | None) -> str:
    """Classify a monthly public series without treating wrapper time as freshness."""
    if age_months is None or age_months < 0:
        return "unknown"
    # CPI-family releases naturally describe an earlier reference month.  Two
    # calendar months is therefore an allowed publication lag; more is stale.
    return "current_with_publication_lag" if age_months <= 2 else "stale"


def _read_json(path: Path, label: str, gaps: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        gaps.append(f"{label}:absent")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        gaps.append(f"{label}:unreadable:{type(exc).__name__}")
        return None
    if not isinstance(value, dict):
        gaps.append(f"{label}:not_object")
        return None
    return value


def _read_ledger(
    repo: Path,
    path: Path,
    gaps: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    status = {
        "available": False,
        "path": _path_label(repo, path),
        "rows_read": 0,
        "malformed_rows": 0,
    }
    if not path.exists():
        gaps.append("release_radar_forward_ledger:absent")
        return [], status

    rows: list[dict[str, Any]] = []
    malformed = 0
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except Exception:  # noqa: BLE001
                    malformed += 1
                    continue
                if isinstance(row, dict):
                    rows.append(row)
                else:
                    malformed += 1
    except Exception as exc:  # noqa: BLE001
        gaps.append(f"release_radar_forward_ledger:unreadable:{type(exc).__name__}")
        return [], status

    status.update(available=True, rows_read=len(rows), malformed_rows=malformed)
    if malformed:
        gaps.append(f"release_radar_forward_ledger:malformed_rows:{malformed}")
    return rows, status


def _read_fred_series(
    repo: Path,
    series_id: str,
    preferred_column: str,
    as_of: date,
    gaps: list[str],
) -> tuple[pd.Series | None, dict[str, Any]]:
    path = repo / "data" / "fred" / f"{series_id}.parquet"
    status: dict[str, Any] = {
        "series_id": series_id,
        "available": False,
        "path": _path_label(repo, path),
        "observation_period": None,
        "observation_age_months": None,
        "freshness_status": "unknown",
    }
    if not path.exists():
        gaps.append(f"fred:{series_id}:absent")
        return None, status
    try:
        frame = pd.read_parquet(path)
        if frame is None or frame.empty:
            gaps.append(f"fred:{series_id}:empty")
            return None, status
        frame = frame.copy()
        frame.index = pd.to_datetime(frame.index, errors="coerce")
        frame = frame[frame.index.notna()].sort_index()
        frame = frame.loc[frame.index.date <= as_of]
        if frame.empty:
            gaps.append(f"fred:{series_id}:no_observation_by_asof")
            return None, status
        column = preferred_column if preferred_column in frame.columns else None
        if column is None:
            numeric = list(frame.select_dtypes(include="number").columns)
            column = numeric[0] if numeric else None
        if column is None:
            gaps.append(f"fred:{series_id}:no_numeric_column")
            return None, status
        series = pd.to_numeric(frame[column], errors="coerce").dropna()
        series = series[~series.index.duplicated(keep="last")].sort_index()
        if series.empty:
            gaps.append(f"fred:{series_id}:no_numeric_observations")
            return None, status
        observation_period = str(series.index[-1].to_period("M"))
        age_months = _month_age(observation_period, as_of)
        freshness_status = _monthly_freshness(age_months)
        status.update(
            available=True,
            column=str(column),
            observations=len(series),
            observation_period=observation_period,
            observation_age_months=age_months,
            freshness_status=freshness_status,
        )
        if freshness_status == "stale":
            gaps.append(f"fred:{series_id}:stale:{age_months}m")
        return series, status
    except Exception as exc:  # noqa: BLE001
        gaps.append(f"fred:{series_id}:unreadable:{type(exc).__name__}")
        return None, status


def _monthly_levels(series: pd.Series) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce").dropna().sort_index()
    if clean.empty:
        return pd.Series(dtype=float)
    monthly = clean.groupby(clean.index.to_period("M")).last().astype(float)
    # Missing calendar months must remain missing; positional shifts would silently
    # turn a four-month span with a hole into a three-month rate.
    full_index = pd.period_range(monthly.index.min(), monthly.index.max(), freq="M")
    return monthly.reindex(full_index)


def _level_change(monthly: pd.Series, months: int, annualized: bool) -> float | None:
    if monthly.empty or months < 1:
        return None
    current_period = monthly.index[-1]
    prior_period = current_period - months
    if prior_period not in monthly.index:
        return None
    current = _number(monthly.loc[current_period], digits=12)
    prior = _number(monthly.loc[prior_period], digits=12)
    if current is None or prior is None or current <= 0 or prior <= 0:
        return None
    gross = current / prior
    exponent = 12.0 / months if annualized else 1.0
    return _number((gross**exponent - 1.0) * 100.0)


def _monthly_percent_annualized(series: pd.Series, months: int) -> float | None:
    """Compound the latest full N-month window of raw monthly percent changes."""
    if months < 1:
        return None
    monthly = _monthly_levels(series)
    if len(monthly) < months:
        return None
    window = monthly.iloc[-months:]
    if window.isna().any() or (window <= -100.0).any():
        return None
    gross = float((1.0 + window / 100.0).prod())
    return _number((gross ** (12.0 / months) - 1.0) * 100.0)


def _released_index_state(
    series: pd.Series | None,
    series_id: str,
    label: str,
    as_of: date,
) -> dict[str, Any]:
    empty = {
        "available": False,
        "series_id": series_id,
        "label": label,
        "observation_period": None,
        "observation_age_months": None,
        "freshness_status": "unknown",
        "index_level": None,
        "mom_pct": None,
        "yoy_pct": None,
        "annualized_3m_pct": None,
        "annualized_6m_pct": None,
        "acceleration_3m_minus_6m_pp": None,
        "revision_basis": "latest_local_fred_not_original_release_vintage",
    }
    if series is None or series.empty:
        return empty
    monthly = _monthly_levels(series)
    if monthly.empty or pd.isna(monthly.iloc[-1]):
        return empty
    ann3 = _level_change(monthly, 3, annualized=True)
    ann6 = _level_change(monthly, 6, annualized=True)
    period = str(monthly.index[-1])
    age_months = _month_age(period, as_of)
    return {
        **empty,
        "available": True,
        "observation_period": period,
        "observation_age_months": age_months,
        "freshness_status": _monthly_freshness(age_months),
        "index_level": _number(monthly.iloc[-1], digits=3),
        "mom_pct": _level_change(monthly, 1, annualized=False),
        "yoy_pct": _level_change(monthly, 12, annualized=False),
        "annualized_3m_pct": ann3,
        "annualized_6m_pct": ann6,
        "acceleration_3m_minus_6m_pp": (
            _number(ann3 - ann6) if ann3 is not None and ann6 is not None else None
        ),
    }


def _monthly_proxy_state(
    series: pd.Series | None,
    series_id: str,
    label: str,
    as_of: date,
) -> dict[str, Any]:
    empty = {
        "available": False,
        "series_id": series_id,
        "label": label,
        "observation_period": None,
        "observation_age_months": None,
        "freshness_status": "unknown",
        "monthly_pct": None,
        "annualized_3m_pct": None,
        "annualized_6m_pct": None,
        "acceleration_3m_minus_6m_pp": None,
        "revision_basis": "latest_local_fred_proxy_series",
    }
    if series is None or series.empty:
        return empty
    clean = pd.to_numeric(series, errors="coerce").dropna().sort_index()
    if clean.empty:
        return empty
    ann3 = _monthly_percent_annualized(clean, 3)
    ann6 = _monthly_percent_annualized(clean, 6)
    period = str(clean.index[-1].to_period("M"))
    age_months = _month_age(period, as_of)
    return {
        **empty,
        "available": True,
        "observation_period": period,
        "observation_age_months": age_months,
        "freshness_status": _monthly_freshness(age_months),
        "monthly_pct": _number(clean.iloc[-1]),
        "annualized_3m_pct": ann3,
        "annualized_6m_pct": ann6,
        "acceleration_3m_minus_6m_pp": (
            _number(ann3 - ann6) if ann3 is not None and ann6 is not None else None
        ),
    }


def _cpi_entries(radar: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not radar:
        return []
    upcoming = radar.get("upcoming")
    if not isinstance(upcoming, list):
        return []
    return [
        row for row in upcoming
        if isinstance(row, dict)
        and row.get("release_type") in {"cpi_headline", "cpi_core"}
    ]


def _forecast_evolution(
    ledger_rows: list[dict[str, Any]],
    release_type: str,
    period: str | None,
    cutoff_asof: date,
) -> dict[str, Any]:
    # One authoritative/champion projection per as-of. Shadow model rows are kept
    # in the source ledger but excluded from this path to avoid mixing model identities.
    # The ledger can advance independently of a historical/replayed artifact build,
    # so rows without a parseable clock or after the resolved artifact clock fail closed.
    by_asof: dict[str, dict[str, Any]] = {}
    excluded_after_cutoff = 0
    excluded_unparseable_asof = 0
    for row in ledger_rows:
        if row.get("release") != release_type or str(row.get("period") or "") != str(period or ""):
            continue
        if row.get("row_type") not in (None, "projection"):
            continue
        if row.get("model") not in (None, "", "champion"):
            continue
        row_asof = row.get("asof_night") or row.get("asof")
        row_date = _parse_ledger_asof(row_asof)
        if row_date is None:
            excluded_unparseable_asof += 1
            continue
        if row_date > cutoff_asof:
            excluded_after_cutoff += 1
            continue
        asof = row_date.isoformat()
        by_asof[asof] = {
            "asof": asof,
            "point": _number(row.get("projection_point")),
            "p10": _number(row.get("projection_p10")),
            "p25": _number(row.get("projection_p25")),
            "p50": _number(row.get("projection_p50")),
            "p75": _number(row.get("projection_p75")),
            "p90": _number(row.get("projection_p90")),
            "confidence": _number(row.get("confidence")),
            "input_completeness": _number(row.get("input_completeness")),
            "cutoff_label": row.get("cutoff_label"),
            "prediction_id": row.get("prediction_id"),
            "model_epoch": row.get("model_epoch"),
            "target_epoch": row.get("target_epoch"),
            "code_receipt": row.get("code_receipt"),
            "inputs_hash": row.get("inputs_hash"),
            "input_snapshot_ref": row.get("input_snapshot_ref"),
        }
    points = [by_asof[key] for key in sorted(by_asof)]
    return {
        "basis": "append_only_release_radar_forward_ledger_champion_path",
        "cutoff_asof": cutoff_asof.isoformat(),
        "cutoff_policy": "exclude_unparseable_or_after_resolved_artifact_asof",
        "excluded_after_cutoff": excluded_after_cutoff,
        "excluded_unparseable_asof": excluded_unparseable_asof,
        "n_points": len(points),
        "first_asof": points[0]["asof"] if points else None,
        "last_asof": points[-1]["asof"] if points else None,
        "points": points,
    }


def _coverage(entry: dict[str, Any]) -> dict[str, Any]:
    flags = entry.get("coverage_flags") if isinstance(entry.get("coverage_flags"), dict) else {}
    pit = entry.get("pit") if isinstance(entry.get("pit"), dict) else {}
    bridge = ((entry.get("shadows") or {}).get("cpi_bridge")
              if isinstance(entry.get("shadows"), dict) else None)
    bridge = bridge if isinstance(bridge, dict) else {}
    return {
        "input_completeness": _number(entry.get("input_completeness")),
        "radar_weight_coverage": _number(flags.get("weight_coverage")),
        "radar_fresh_proxy_coverage": _number(flags.get("fresh_proxy_coverage")),
        "radar_non_vintaged_share": _number(flags.get("non_vintaged_share")),
        "model_maturity_n": flags.get("model_maturity"),
        "bridge_modelled_weight_coverage": _number(bridge.get("weight_coverage")),
        "bridge_prior_driven_share": _number(bridge.get("prior_driven_share")),
        "bridge_weight_basis": bridge.get("weight_basis"),
        "bridge_weight_basis_warning": bridge.get("weight_basis_warning"),
        "bridge_known_scope_mismatches": bridge.get("known_scope_mismatches") or [],
        "absent_legs": sorted(str(x) for x in (pit.get("absent_legs") or [])),
        "revision_optimistic_legs": sorted(
            str(x) for x in (pit.get("revision_optimistic_legs") or [])
        ),
        "range_violation_legs": sorted(str(x) for x in (pit.get("range_violation_legs") or [])),
    }


def _component_freshness(entry: dict[str, Any], forecast_asof: str | None) -> list[dict[str, Any]]:
    bridge = ((entry.get("shadows") or {}).get("cpi_bridge")
              if isinstance(entry.get("shadows"), dict) else None)
    components = bridge.get("components") if isinstance(bridge, dict) else None
    basis = "cpi_bridge"
    if not isinstance(components, list):
        components = entry.get("components") if isinstance(entry.get("components"), list) else []
        basis = "release_radar_components"

    out: list[dict[str, Any]] = []
    for component in components:
        if not isinstance(component, dict):
            continue
        prior_only = bool(component.get("prior_only"))
        degraded = bool(component.get("degraded"))
        missing = sorted(str(x) for x in (component.get("missing_legs") or []))
        if prior_only:
            status = "prior_only"
        elif degraded or missing:
            status = "degraded_proxy"
        elif _number(component.get("confidence")) == 0.0:
            status = "prior_or_unmodelled"
        else:
            status = "proxy_available"
        out.append({
            "component": component.get("block") or component.get("name"),
            "basis": basis,
            "forecast_asof": forecast_asof,
            "status": status,
            "contribution_pp": _number(
                component.get("contribution_pp", component.get("contrib_pp"))
            ),
            "component_mom_estimate_pct": _number(component.get("mom_est")),
            "weight_pct": _number(component.get("weight")),
            "confidence": _number(component.get("confidence")),
            "legs_used": component.get("legs_used"),
            "legs_expected": component.get("legs_expected"),
            "missing_legs": missing,
        })
    return out


def _forecast_target(
    entry: dict[str, Any] | None,
    ledger_rows: list[dict[str, Any]],
    radar_asof: str | None,
    evolution_cutoff: date,
) -> dict[str, Any]:
    if not entry:
        return {
            "available": False,
            "release_type": None,
            "period": None,
            "release_date": None,
            "days_to_release": None,
            "target": None,
            "forecast_asof": radar_asof,
            "model_epoch": None,
            "target_epoch": None,
            "code_receipt": None,
            "inputs_hash": None,
            "input_snapshot_ref": None,
            "primary_forecast_basis": None,
            "context_metrics_basis": None,
            "basis_warning": None,
            "release_radar_projection": None,
            "combined_display_estimate": None,
            "coverage": {},
            "component_freshness": [],
            "forecast_evolution": {
                "basis": "append_only_release_radar_forward_ledger_champion_path",
                "cutoff_asof": evolution_cutoff.isoformat(),
                "cutoff_policy": "exclude_unparseable_or_after_resolved_artifact_asof",
                "excluded_after_cutoff": 0,
                "excluded_unparseable_asof": 0,
                "n_points": 0,
                "first_asof": None,
                "last_asof": None,
                "points": [],
            },
        }
    projection = entry.get("projection") if isinstance(entry.get("projection"), dict) else {}
    combined = entry.get("combined") if isinstance(entry.get("combined"), dict) else {}
    combined_components = (
        combined.get("combined_components")
        if isinstance(combined.get("combined_components"), dict) else {}
    )
    inputs_used = [str(x) for x in (combined_components.get("inputs_used") or [])]
    release_type = str(entry.get("release_type") or "")
    period = str(entry.get("period") or "") or None
    primary = {
        "point": _number(projection.get("point")),
        "p10": _number(projection.get("p10")),
        "p25": _number(projection.get("p25")),
        "p50": _number(projection.get("p50")),
        "p75": _number(projection.get("p75")),
        "p90": _number(projection.get("p90")),
        "confidence": _number(entry.get("confidence")),
    }
    combined_display = None
    if combined:
        combined_display = {
            "point": _number(combined.get("combined_point")),
            "p10": _number(combined.get("p10")),
            "p25": _number(combined.get("p25")),
            "p50": _number(combined.get("p50")),
            "p75": _number(combined.get("p75")),
            "p90": _number(combined.get("p90")),
            "inputs_used": inputs_used,
            "includes_external_benchmark": any(
                name in {"cleveland", "consensus"} for name in inputs_used
            ),
            "n_scored_basis": combined.get("n_scored_basis"),
            "model_epoch": combined.get("model_epoch"),
            "target_epoch": combined.get("target_epoch"),
            "code_receipt": combined.get("code_receipt"),
            "inputs_hash": combined.get("inputs_hash"),
            "input_hashes": {
                str(key): value
                for key, value in (combined_components.get("input_hashes") or {}).items()
            } if isinstance(combined_components.get("input_hashes"), dict) else {},
            "display_only": True,
            "authority": False,
        }
    return {
        "available": any(value is not None for value in primary.values()),
        "release_type": release_type or None,
        "period": period,
        "release_date": entry.get("release_date"),
        "days_to_release": entry.get("days_to"),
        "target": entry.get("target"),
        "forecast_asof": radar_asof,
        "model_epoch": entry.get("model_epoch"),
        "target_epoch": entry.get("target_epoch"),
        "code_receipt": entry.get("code_receipt"),
        "inputs_hash": entry.get("inputs_hash"),
        "primary_forecast_basis": entry.get("primary_forecast_basis"),
        "context_metrics_basis": entry.get("context_metrics_basis"),
        "basis_warning": entry.get("basis_warning"),
        "release_radar_projection": primary,
        "combined_display_estimate": combined_display,
        "coverage": _coverage(entry),
        "component_freshness": _component_freshness(entry, radar_asof),
        "input_snapshot_ref": entry.get("input_snapshot_ref"),
        "forecast_evolution": _forecast_evolution(
            ledger_rows, release_type, period, evolution_cutoff
        ),
    }


def _entries_for_date(entries: list[dict[str, Any]], release_date: str) -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("release_type")): entry
        for entry in entries
        if str(entry.get("release_date") or "") == release_date
    }


def _next_release_block(
    entries: list[dict[str, Any]],
    ledger_rows: list[dict[str, Any]],
    radar_asof: str | None,
    as_of: date,
) -> tuple[dict[str, Any], str | None]:
    future = [
        entry for entry in entries
        if (_parse_date(entry.get("release_date")) or date.max) >= as_of
    ]
    dated = [entry for entry in future if _parse_date(entry.get("release_date")) is not None]
    if not dated:
        return {
            "available": False,
            "release_date": None,
            "period": None,
            "headline": _forecast_target(None, ledger_rows, radar_asof, as_of),
            "core": _forecast_target(None, ledger_rows, radar_asof, as_of),
        }, None
    release_date = min(str(entry.get("release_date")) for entry in dated)
    grouped = _entries_for_date(dated, release_date)
    headline = grouped.get("cpi_headline")
    core = grouped.get("cpi_core")
    period = (headline or core or {}).get("period")
    return {
        "available": bool(headline or core),
        "release_date": release_date,
        "period": period,
        "headline": _forecast_target(headline, ledger_rows, radar_asof, as_of),
        "core": _forecast_target(core, ledger_rows, radar_asof, as_of),
    }, str(period) if period is not None else None


def _pressure_direction(value: float | None) -> str | None:
    if value is None:
        return None
    if value > 0:
        return "upward_price_pressure"
    if value < 0:
        return "downward_price_pressure"
    return "flat_model_pressure"


def _current_month_pressure_block(
    entries: list[dict[str, Any]],
    ledger_rows: list[dict[str, Any]],
    radar_asof: str | None,
    as_of: date,
    sticky: dict[str, Any],
    flexible: dict[str, Any],
) -> dict[str, Any]:
    period = f"{as_of.year:04d}-{as_of.month:02d}"
    current = {
        str(entry.get("release_type")): entry
        for entry in entries
        if str(entry.get("period") or "") == period
    }
    headline_entry = current.get("cpi_headline")
    core_entry = current.get("cpi_core")
    headline = _forecast_target(headline_entry, ledger_rows, radar_asof, as_of)
    core = _forecast_target(core_entry, ledger_rows, radar_asof, as_of)
    hpoint = None
    if headline.get("release_radar_projection"):
        hpoint = headline["release_radar_projection"].get("point")
    sticky_ann = sticky.get("annualized_3m_pct")
    flexible_ann = flexible.get("annualized_3m_pct")
    if sticky_ann is not None and flexible_ann is not None:
        proxy_mix = "sticky_led" if sticky_ann >= flexible_ann else "flexible_led"
    else:
        proxy_mix = None
    components = _component_freshness(headline_entry or {}, radar_asof)
    return {
        "available": bool(headline.get("available") or core.get("available")
                          or sticky.get("available") or flexible.get("available")),
        "period": period,
        "definition": (
            "Public-data and model pressure for the in-progress reference month; "
            "not an official CPI observation, not a real-time CPI index, and not a "
            "substitute for the next BLS release."
        ),
        "pressure_direction": _pressure_direction(hpoint),
        "headline_model_pressure": headline,
        "core_model_pressure": core,
        "underlying_proxy_mix": {
            "read": proxy_mix,
            "sticky": sticky,
            "flexible": flexible,
        },
        "component_freshness": components,
        "coverage": _coverage(headline_entry or {}),
    }


def build_inflation_intelligence(
    root: str | Path | None = None,
    *,
    as_of: str | date | None = None,
    radar_latest_path: str | Path | None = None,
    forward_ledger_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build a JSON-safe ``inflation_intelligence.v1`` payload. Never raises."""
    repo = _repo_root(root)
    gaps: list[str] = []
    radar_path = _resolve(repo, radar_latest_path, DEFAULT_RADAR_LATEST)
    ledger_path = _resolve(repo, forward_ledger_path, DEFAULT_FORWARD_LEDGER)

    radar = _read_json(radar_path, "release_radar_latest", gaps)
    radar_asof = str(radar.get("asof")) if radar and radar.get("asof") else None
    resolved_asof = (
        _parse_date(as_of)
        or _parse_date(radar_asof)
        or datetime.now(timezone.utc).date()
    )
    ledger_rows, ledger_status = _read_ledger(repo, ledger_path, gaps)

    series: dict[str, pd.Series | None] = {}
    fred_status: dict[str, dict[str, Any]] = {}
    for key, (series_id, column) in _FRED_SERIES.items():
        series[key], fred_status[key] = _read_fred_series(
            repo, series_id, column, resolved_asof, gaps
        )

    released_headline = _released_index_state(
        series["headline"], _FRED_SERIES["headline"][0], "Headline CPI-U", resolved_asof
    )
    released_core = _released_index_state(
        series["core"], _FRED_SERIES["core"][0], "Core CPI-U", resolved_asof
    )
    sticky = _monthly_proxy_state(
        series["sticky"], _FRED_SERIES["sticky"][0], "Sticky-price CPI proxy", resolved_asof
    )
    flexible = _monthly_proxy_state(
        series["flexible"], _FRED_SERIES["flexible"][0], "Flexible-price CPI proxy", resolved_asof
    )

    released_state = {
        "available": bool(released_headline["available"] or released_core["available"]),
        "basis": "latest_local_fred_official_index_levels_not_original_release_vintage",
        "headline": released_headline,
        "core": released_core,
        "underlying_proxies": {"sticky": sticky, "flexible": flexible},
    }

    entries = _cpi_entries(radar)
    next_release, _ = _next_release_block(
        entries, ledger_rows, radar_asof, resolved_asof
    )
    current_pressure = _current_month_pressure_block(
        entries, ledger_rows, radar_asof, resolved_asof, sticky, flexible
    )

    radar_day = _parse_date(radar_asof)
    radar_age_days = (resolved_asof - radar_day).days if radar_day is not None else None
    freshness_reasons = set(gaps)
    if radar_age_days is None:
        freshness_reasons.add("release_radar_latest:asof_unavailable")
    elif radar_age_days < 0:
        freshness_reasons.add("release_radar_latest:asof_after_build_cutoff")
    elif radar_age_days > 2:
        freshness_reasons.add(f"release_radar_latest:stale:{radar_age_days}d")
    freshness = {
        "status": "degraded" if freshness_reasons else "current_with_publication_lag",
        "policy": (
            "Source observation clocks determine freshness; rebuilding this wrapper "
            "does not refresh an underlying CPI, proxy, or forecast input."
        ),
        "monthly_source_max_age_months": 2,
        "release_radar_artifact_max_age_days": 2,
        "release_radar_artifact_age_days": radar_age_days,
        "degraded_reasons": sorted(freshness_reasons),
    }

    return {
        "schema": SCHEMA,
        "asof": resolved_asof.isoformat(),
        "display_only": True,
        "authority": False,
        "is_context_only": True,
        "allowed_actions": {
            "may_rank": False,
            "may_score": False,
            "may_size": False,
            "may_gate": False,
            "may_escalate": False,
            "may_trade": False,
        },
        "authority_note": _AUTHORITY_NOTE,
        "released_state": released_state,
        "next_release_forecast": next_release,
        "current_month_proxy_pressure": current_pressure,
        "freshness": freshness,
        "source_status": {
            "fred": fred_status,
            "release_radar_latest": {
                "available": radar is not None,
                "path": _path_label(repo, radar_path),
                "asof": radar_asof,
                "cpi_entries": len(entries),
            },
            "release_radar_forward_ledger": ledger_status,
        },
        "gaps": sorted(set(gaps)),
        "matched_lenses": _matched_lenses_safe(repo, resolved_asof, radar, entries),
    }


def write_inflation_intelligence(
    root: str | Path | None = None,
    *,
    output_path: str | Path | None = None,
    as_of: str | date | None = None,
    radar_latest_path: str | Path | None = None,
    forward_ledger_path: str | Path | None = None,
) -> tuple[dict[str, Any], Path]:
    """Build and atomically replace the artifact file."""
    repo = _repo_root(root)
    target = _resolve(repo, output_path, DEFAULT_OUTPUT)
    payload = build_inflation_intelligence(
        repo,
        as_of=as_of,
        radar_latest_path=radar_latest_path,
        forward_ledger_path=forward_ledger_path,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(target)
    return payload, target


# ---------------------------------------------------------------------------
# I0-BUILD: matched_lenses block (display-only, basis-aware side-by-side).
# ---------------------------------------------------------------------------


_LENS_LAW = (
    "Each lens is one source on its own basis. Lenses are shown side by side and are "
    "never blended, re-labelled or subtracted across bases; a pair is compared only "
    "through a registered basis rule, and a refusal is shown as a refusal."
)


_SIDE_NOTE = (
    "Different sources and methods for the same horizon; read side by side, never "
    "averaged or differenced."
)


_OFFICIAL_SERIES = {
    "headline": ("CPIAUCSL", "headline_cpi", "CPI-U"),
    "core": ("CPILFESL", "core_cpi", "CPI-U"),
}


_PCE_SERIES = {
    "headline": ("PCEPI", "headline_pce", "PCE"),
    "core": ("PCEPILFE", "core_pce", "PCE"),
}


_BREAKEVEN_SERIES = {
    "10y": ("T10YIE", "breakeven_10y", "10y", "inflation_compensation"),
    "5y5y": ("T5YIFR", "breakeven_5y5y", "5y5y", "inflation_compensation_forward"),
}


_EXPINF_SERIES = {
    "1y": ("EXPINF1YR", "infl_exp_1y", "1y"),
    "5y": ("EXPINF5YR", "infl_exp_5y", "5y"),
    "10y": ("EXPINF10YR", "infl_exp_10y", "10y"),
}


_SURVEY_SERIES = {
    "1y": ("MICH", "umich_infl_exp", "1y"),
}


_NEXT_PRINT_RELEASE_TYPE = {"headline": "cpi_headline", "core": "cpi_core"}


def _street_consensus() -> dict[str, Any]:
    return {
        "value": None,
        "value_state": "unavailable",
        "reason": "no_admitted_street_economist_survey_source",
    }


def _period_bounds(month_str: Any) -> tuple[str | None, str | None]:
    if not isinstance(month_str, str) or len(month_str) != 7:
        return None, None
    try:
        per = pd.Period(month_str, freq="M")
    except Exception:  # noqa: BLE001
        return None, None
    return per.start_time.date().isoformat(), per.end_time.date().isoformat()


def _add_years(iso: str, years: int) -> str:
    """Add ``years`` calendar years to an ISO date string.

    Feb 29 only collapses to Feb 28 when the destination year is not a leap
    year; no other field is normalized.
    """
    base = date.fromisoformat(iso)
    try:
        return base.replace(year=base.year + years).isoformat()
    except ValueError:
        return base.replace(year=base.year + years, day=28).isoformat()


def _qualified_lens_record(
    *,
    qualified: Any,
    lens_id: str,
    label_en: str,
    source_class: str,
    scope: str,
    frequency: str,
    unit: str,
    horizon: str,
    transform: str,
    source: str,
    series_id: str | None,
    basket_or_index: str | None,
    measure: str,
    reference_period: dict[str, str | None],
    observation_date: str | None,
    lens_limitations: list[str],
) -> dict[str, Any]:
    final_state = qualified.value_state.value
    final_value = qualified.value
    if final_state != "present":
        final_value = None
    final_limitations = sorted(set(qualified.limitations) | set(lens_limitations))
    return {
        "lens_id": lens_id,
        "label_en": label_en,
        "source_class": source_class,
        "evidence_class": qualified.evidence_class.value,
        "measure": measure,
        "basket_or_index": basket_or_index,
        "scope": scope,
        "frequency": frequency,
        "transform": transform,
        "unit": unit,
        "horizon": horizon,
        "reference_period": reference_period,
        "value": final_value,
        "value_state": final_state,
        "interval": None,
        "observation_date": observation_date,
        "source": source,
        "series_id": series_id,
        "blend_inputs": None,
        "limitations": final_limitations,
        "qualified": qualified.to_dict(),
    }


def _official_lens(
    repo: Path,
    as_of: date,
    lens_gaps: list[str],
    *,
    family: str,
    m: str,
    unit: str,
) -> tuple[dict[str, Any], Any]:
    """Build one official CPI or PCE lens (present OR missing).

    Both branches produce the live B0 object through B0's public
    ``qualify_observation``; the missing branch passes raw=None and leaves
    reference_start/end/observation_time None. Returns
    ``(record, qualified)`` so the builder can keep the live B0 object in
    its local ``objs`` dict for direct ``compare_qualified`` calls.
    """
    from engine import rates_command_basis as rcb  # local import per §2.2

    if family == "cpi":
        series_id, column, basket = _OFFICIAL_SERIES[m]
    elif family == "pce":
        series_id, column, basket = _PCE_SERIES[m]
    else:
        raise ValueError(f"unknown official family: {family}")
    kind = "cpi" if basket == "CPI-U" else "pce"
    lens_id = f"official_{kind}_{m}_{'mom' if unit == 'pct_mom' else 'yoy'}"
    label_en = (
        f"{'CPI-U' if basket == 'CPI-U' else 'PCE price index'} "
        f"{'all items' if m == 'headline' else 'core'}, "
        f"latest released month, % {'m/m' if unit == 'pct_mom' else 'y/y'} (SA)"
    )
    target = (
        f"{'cpi_u' if basket == 'CPI-U' else 'pce'}_"
        f"{'all_items' if m == 'headline' else 'core'}_"
        f"{'mom' if unit == 'pct_mom' else 'yoy'}_sa_latest_revised"
    )
    base_limitations = ["latest_revised_not_first_print"]
    if unit == "pct_yoy":
        base_limitations.append("yoy_from_sa_index_not_published_nsa_yoy")
    series, _ = _read_fred_series(repo, series_id, column, as_of, lens_gaps)
    raw = None
    ref_start = None
    ref_end = None
    quality: tuple = ()
    monthly = None
    if series is not None and not series.empty:
        monthly = _monthly_levels(series)
        if not monthly.empty and not pd.isna(monthly.iloc[-1]):
            last_period = monthly.index[-1]
            months = 12 if unit == "pct_yoy" else 1
            raw = _level_change(monthly, months, False)
            period_str = str(last_period)
            period_start, period_end = _period_bounds(period_str)
            if unit == "pct_yoy":
                ref_start, _ = _period_bounds(str(last_period - 11))
            else:
                ref_start = period_start
            ref_end = period_end
            age = _month_age(period_str, as_of)
            if age is not None and _monthly_freshness(age) == "stale":
                quality = ("stale",)
    lens_limitations = list(base_limitations)
    if "stale" in quality and monthly is not None and not monthly.empty and not pd.isna(monthly.iloc[-1]):
        period_str = str(monthly.index[-1])
        age = _month_age(period_str, as_of)
        if age is not None:
            lens_limitations.append(f"source_stale:{age}m")
    meta = {
        "subject": lens_id,
        "evidence_class": rcb.EvidenceClass.OFFICIAL_MEASUREMENT.value,
        "unit": unit,
        "target": target,
        "basket_or_index": basket,
        "reference_start": ref_start,
        "reference_end": ref_end,
        "tenor": None,
        "observation_time": None,
        "observation_precision": "unknown",
        "seasonal_treatment": "sa",
        "rate_index": "n/a",
        "averaging_law": "n/a",
        "source": f"fred:{series_id}",
        "source_version": None,
        "content_ref": series_id,
        "first_public_evidence": None,
        "first_public_precision": "unknown",
        "model_id": None,
        "target_epoch": None,
        "rights": "public_official",
        "quality": quality,
        "limitations": tuple(lens_limitations),
    }
    qualified = rcb.qualify_observation(raw, meta, cutoff=as_of.isoformat())
    record = _qualified_lens_record(
        qualified=qualified,
        lens_id=lens_id,
        label_en=label_en,
        source_class="official_measurement",
        scope=m,
        frequency="monthly",
        unit=unit,
        horizon=("1m" if unit == "pct_mom" else "12m"),
        transform=unit,
        source=f"fred:{series_id}",
        series_id=series_id,
        basket_or_index=basket,
        measure="index_level_change",
        reference_period={"start": ref_start, "end": ref_end},
        observation_date=None,
        lens_limitations=lens_limitations,
    )
    return record, qualified


def _daily_lens(
    repo: Path,
    as_of: date,
    lens_gaps: list[str],
    *,
    series_id: str,
    column: str,
    lens_id: str,
    label_en: str,
    source_class: str,
    evidence_class_value: str,
    scope: str,
    unit: str,
    target: str,
    tenor: str,
    basket_or_index: str | None,
    rights: str,
    lens_limitations: list[str],
    ref_end_years: int,
    curve_convention: str | None = None,
    model_id: str | None = None,
    target_epoch: str | None = None,
    quality: tuple = (),
) -> tuple[dict[str, Any], Any]:
    """Build one daily lens (present OR missing).

    The reference end is ``obs_date + ref_end_years`` years (calendar years
    via ``_add_years``). For breakeven/forward breakeven the builder passes
    tenor="10y" with ``ref_end_years=10`` (end) and tenor="5y5y" with the
    same ``ref_end_years=10`` (the function also derives the +5y start).
    Returns ``(record, qualified)`` so the builder can keep the live B0
    object in its local ``objs`` dict for direct ``compare_qualified``
    calls.
    """
    from engine import rates_command_basis as rcb  # local import per §2.2

    series, _ = _read_fred_series(repo, series_id, column, as_of, lens_gaps)
    raw = None
    obs_iso: str | None = None
    obs_date = None
    ref_start: str | None = None
    ref_end: str | None = None
    if series is not None and not series.empty:
        obs_date = series.index[-1].date()
        obs_iso = obs_date.isoformat()
        ref_start = obs_iso
        if tenor == "5y5y":
            ref_start = _add_years(obs_iso, 5)
            ref_end = _add_years(obs_iso, ref_end_years)
        else:
            ref_end = _add_years(obs_iso, ref_end_years)
        raw = _number(series.iloc[-1])
    obs_quality = list(quality)
    obs_limitations = list(lens_limitations)
    if obs_date is not None:
        age_days = (as_of - obs_date).days
        if age_days is not None and age_days > 7:
            obs_quality.append("stale")
            obs_limitations.append(f"observation_age_days:{age_days}")
    meta = {
        "subject": lens_id,
        "evidence_class": evidence_class_value,
        "unit": unit,
        "target": target,
        "basket_or_index": basket_or_index,
        "reference_start": ref_start,
        "reference_end": ref_end,
        "tenor": tenor,
        "observation_time": obs_iso,
        "observation_precision": "day",
        "seasonal_treatment": "n/a",
        "rate_index": "n/a",
        "averaging_law": "n/a",
        "curve_convention": curve_convention,
        "source": f"fred:{series_id}",
        "source_version": None,
        "content_ref": series_id,
        "first_public_evidence": None,
        "first_public_precision": "unknown",
        "model_id": model_id,
        "target_epoch": target_epoch,
        "rights": rights,
        "quality": tuple(obs_quality),
        "limitations": tuple(obs_limitations),
    }
    qualified = rcb.qualify_observation(raw, meta, cutoff=as_of.isoformat())
    record = _qualified_lens_record(
        qualified=qualified,
        lens_id=lens_id,
        label_en=label_en,
        source_class=source_class,
        scope=scope,
        frequency="daily",
        unit=unit,
        horizon=tenor,
        transform=unit,
        source=f"fred:{series_id}",
        series_id=series_id,
        basket_or_index=basket_or_index,
        measure="market_price",
        reference_period={"start": ref_start, "end": ref_end},
        observation_date=obs_iso,
        lens_limitations=obs_limitations,
    )
    return record, qualified


def _monthly_exp_lens(
    repo: Path,
    as_of: date,
    lens_gaps: list[str],
    *,
    series_id: str,
    column: str,
    lens_id: str,
    label_en: str,
    source_class: str,
    evidence_class_value: str,
    scope: str,
    target: str,
    tenor: str,
    basket_or_index: str | None,
    rights: str,
    model_id: str | None,
    lens_limitations: list[str],
    ref_end_years: int,
) -> tuple[dict[str, Any], Any]:
    """Build one monthly expected-inflation lens (present OR missing).

    Reference period = month-t start .. month-t start + ``ref_end_years``
    calendar years. Returns ``(record, qualified)`` so the builder can keep
    the live B0 object in its local ``objs`` dict for direct
    ``compare_qualified`` calls.
    """
    from engine import rates_command_basis as rcb  # local import per §2.2

    series, _ = _read_fred_series(repo, series_id, column, as_of, lens_gaps)
    raw = None
    ref_start: str | None = None
    ref_end: str | None = None
    obs_quality: tuple = ()
    period_str: str | None = None
    if series is not None and not series.empty:
        monthly = _monthly_levels(series)
        if not monthly.empty and not pd.isna(monthly.iloc[-1]):
            last_period = monthly.index[-1]
            period_str = str(last_period)
            period_start, _ = _period_bounds(period_str)
            ref_start = period_start
            ref_end = _add_years(period_start, ref_end_years)
            raw = _number(monthly.iloc[-1])
    obs_limitations = list(lens_limitations)
    if period_str is not None:
        age = _month_age(period_str, as_of)
        if age is not None and _monthly_freshness(age) == "stale":
            obs_quality = ("stale",)
            obs_limitations.append(f"source_stale:{age}m")
    meta = {
        "subject": lens_id,
        "evidence_class": evidence_class_value,
        "unit": "pct_ann_rate",
        "target": target,
        "basket_or_index": basket_or_index,
        "reference_start": ref_start,
        "reference_end": ref_end,
        "tenor": tenor,
        "observation_time": None,
        "observation_precision": "unknown",
        "seasonal_treatment": "n/a",
        "rate_index": "n/a",
        "averaging_law": "n/a",
        "source": f"fred:{series_id}",
        "source_version": None,
        "content_ref": series_id,
        "first_public_evidence": None,
        "first_public_precision": "unknown",
        "model_id": model_id,
        "target_epoch": None,
        "rights": rights,
        "quality": obs_quality,
        "limitations": tuple(obs_limitations),
    }
    qualified = rcb.qualify_observation(raw, meta, cutoff=as_of.isoformat())
    record = _qualified_lens_record(
        qualified=qualified,
        lens_id=lens_id,
        label_en=label_en,
        source_class=source_class,
        scope=scope,
        frequency="monthly",
        unit="pct_ann_rate",
        horizon=tenor,
        transform="pct_ann_rate",
        source=f"fred:{series_id}",
        series_id=series_id,
        basket_or_index=basket_or_index,
        measure=("expected_inflation" if source_class != "household_survey" else "household_survey"),
        reference_period={"start": ref_start, "end": ref_end},
        observation_date=None,
        lens_limitations=obs_limitations,
    )
    return record, qualified


def _next_release_entry(
    entries: list[dict[str, Any]], as_of: date
) -> dict[str, dict[str, Any]] | None:
    future = [
        e for e in entries
        if (_parse_date(e.get("release_date")) or date.max) >= as_of
    ]
    dated = [e for e in future if _parse_date(e.get("release_date")) is not None]
    if not dated:
        return None
    release_date = min(str(e.get("release_date")) for e in dated)
    grouped = _entries_for_date(dated, release_date)
    return grouped


def _projection_interval(entry: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    if not isinstance(entry, dict):
        return out
    proj = entry.get("projection") if isinstance(entry.get("projection"), dict) else {}
    for key in ("p10", "p25", "p50", "p75", "p90"):
        val = _number(proj.get(key))
        if val is not None:
            out[key] = val
    return out


def _combined_interval(entry: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    if not isinstance(entry, dict):
        return out
    combined = entry.get("combined") if isinstance(entry.get("combined"), dict) else {}
    for key in ("p10", "p25", "p50", "p75", "p90"):
        val = _number(combined.get(key))
        if val is not None:
            out[key] = val
    return out


def _next_print_lens(
    repo: Path,
    as_of: date,
    lens_gaps: list[str],
    *,
    grouped: dict[str, dict[str, Any]] | None,
    radar: dict[str, Any] | None,
    m: str,
    kind: str,
) -> tuple[dict[str, Any], Any]:
    """Build one next-print lens (qualified or unqualified; grouped or absent).

    Qualified kinds (house, combined, market) go through B0's
    ``qualify_observation`` even when no next-release entry exists; the
    raw is then None and entry-derived meta fields (reference, model_id,
    target_epoch, first_public_evidence, content_ref, source) are also
    None. Unqualified kinds (cleveland, expectation_read) keep
    ``evidence_class None / qualified None`` regardless.
    Returns ``(record, qualified_or_none)`` so the builder can keep the
    live B0 object in its local ``objs`` dict for direct
    ``compare_qualified`` calls.
    """
    from engine import rates_command_basis as rcb  # local import per §2.2

    release_type = _NEXT_PRINT_RELEASE_TYPE[m]
    if kind == "house":
        lens_id = f"house_radar_cpi_{m}_next_mom"
    elif kind == "combined":
        lens_id = f"house_radar_combined_cpi_{m}_next_mom"
    elif kind == "cleveland":
        lens_id = f"cleveland_nowcast_cpi_{m}_next_mom"
    elif kind == "expectation":
        lens_id = f"radar_expectation_read_cpi_{m}_next_mom"
    elif kind == "market":
        lens_id = f"market_cpi_{m}_next_mom"
    else:
        raise ValueError(f"unknown next-print kind: {kind}")
    target = f"cpi_u_{'all_items' if m == 'headline' else 'core'}_mom_sa_first_print"
    base_meta = {
        "subject": lens_id,
        "unit": "pct_mom",
        "target": target,
        "basket_or_index": "CPI-U",
        "frequency": "monthly",
        "scope": m,
    }
    entry = grouped.get(release_type) if isinstance(grouped, dict) else None
    radar_asof = str(radar.get("asof")) if radar and radar.get("asof") else None
    period = entry.get("period") if isinstance(entry, dict) else None
    period_start, period_end = _period_bounds(str(period) if period else "")
    ref_start = period_start
    ref_end = period_end
    has_entry = entry is not None

    if kind == "house":
        proj = entry.get("projection") if isinstance(entry, dict) and isinstance(entry.get("projection"), dict) else {}
        raw = _number(proj.get("point")) if has_entry else None
        interval = _projection_interval(entry) if has_entry else {}
        meta = {
            **base_meta,
            "evidence_class": rcb.EvidenceClass.HOUSE_ESTIMATE.value,
            "reference_start": ref_start if has_entry else None,
            "reference_end": ref_end if has_entry else None,
            "tenor": None,
            "observation_time": radar_asof if has_entry else None,
            "observation_precision": "minute",
            "seasonal_treatment": "sa",
            "rate_index": "n/a",
            "averaging_law": "n/a",
            "source": "release_radar" if has_entry else None,
            "source_version": None,
            "content_ref": None,
            "first_public_evidence": radar_asof if has_entry else None,
            "first_public_precision": "minute",
            "model_id": entry.get("model_epoch") if has_entry else None,
            "target_epoch": entry.get("target_epoch") if has_entry else None,
            "rights": "display_only",
            "quality": (),
            "limitations": (),
        }
        qualified = rcb.qualify_observation(raw, meta, cutoff=as_of.isoformat())
        lens_limitations = [] if has_entry else ["no_next_release_entry"]
        if not has_entry:
            lens_gaps.append("no_next_release_entry")
        record = _qualified_lens_record(
            qualified=qualified,
            lens_id=lens_id,
            label_en=f"Release Radar house model, next CPI-U {m} print, % m/m",
            source_class="house_model",
            scope=m,
            frequency="monthly",
            unit="pct_mom",
            horizon="next_print",
            transform="pct_mom",
            source="release_radar" if has_entry else "",
            series_id=None,
            basket_or_index="CPI-U",
            measure="next_release",
            reference_period={"start": ref_start, "end": ref_end},
            observation_date=None,
            lens_limitations=lens_limitations,
        )
        record["interval"] = interval
        return record, qualified

    if kind == "combined":
        combined = entry.get("combined") if isinstance(entry, dict) and isinstance(entry.get("combined"), dict) else {}
        raw = _number(combined.get("combined_point")) if has_entry else None
        interval = _combined_interval(entry) if has_entry else {}
        inputs_used: list[str] = []
        cc = combined.get("combined_components") if isinstance(combined.get("combined_components"), dict) else {}
        for x in cc.get("inputs_used") or []:
            inputs_used.append(str(x))
        limitations: list[str] = []
        if any("cleveland" == x for x in inputs_used):
            limitations.append("house_blend_includes_external_inputs")
        if not has_entry:
            limitations.append("no_next_release_entry")
            lens_gaps.append("no_next_release_entry")
        meta = {
            **base_meta,
            "evidence_class": rcb.EvidenceClass.HOUSE_ESTIMATE.value,
            "reference_start": ref_start if has_entry else None,
            "reference_end": ref_end if has_entry else None,
            "tenor": None,
            "observation_time": radar_asof if has_entry else None,
            "observation_precision": "minute",
            "seasonal_treatment": "sa",
            "rate_index": "n/a",
            "averaging_law": "n/a",
            "source": "release_radar" if has_entry else None,
            "source_version": None,
            "content_ref": None,
            "first_public_evidence": radar_asof if has_entry else None,
            "first_public_precision": "minute",
            "model_id": combined.get("model_epoch") if has_entry else None,
            "target_epoch": combined.get("target_epoch") if has_entry else None,
            "rights": "display_only",
            "quality": (),
            "limitations": tuple(limitations),
        }
        qualified = rcb.qualify_observation(raw, meta, cutoff=as_of.isoformat())
        record = _qualified_lens_record(
            qualified=qualified,
            lens_id=lens_id,
            label_en="Release Radar house blend (includes external inputs), next CPI-U core print, % m/m" if m == "core" else "Release Radar house blend, next CPI-U all items print, % m/m",
            source_class="house_model_blend",
            scope=m,
            frequency="monthly",
            unit="pct_mom",
            horizon="next_print",
            transform="pct_mom",
            source="release_radar" if has_entry else "",
            series_id=None,
            basket_or_index="CPI-U",
            measure="next_release",
            reference_period={"start": ref_start, "end": ref_end},
            observation_date=None,
            lens_limitations=limitations,
        )
        record["interval"] = interval
        record["blend_inputs"] = list(inputs_used)
        return record, qualified

    if kind == "cleveland":
        if not has_entry:
            lens_gaps.append("no_next_release_entry")
        else:
            lens_gaps.append("b0_evidence_class_absent:external_model_nowcast")
        benchmark_set = entry.get("benchmark_set") if isinstance(entry, dict) and isinstance(entry.get("benchmark_set"), dict) else {}
        raw = _number(benchmark_set.get("cleveland_nowcast")) if has_entry else None
        # The house lens drives the timing inheritance: if refused, mirror.
        house_meta = {
            "evidence_class": rcb.EvidenceClass.HOUSE_ESTIMATE.value,
            "unit": "pct_mom",
            "target": target,
            "basket_or_index": "CPI-U",
            "reference_start": ref_start,
            "reference_end": ref_end,
            "observation_time": radar_asof,
            "observation_precision": "minute",
            "first_public_evidence": radar_asof,
            "first_public_precision": "minute",
        }
        house_lens_id = f"house_radar_cpi_{m}_next_mom"
        proj = entry.get("projection") if isinstance(entry, dict) and isinstance(entry.get("projection"), dict) else {}
        house_raw = _number(proj.get("point")) if has_entry else None
        house_violation_meta = dict(house_meta)
        house_violation_meta["subject"] = house_lens_id
        house_q = rcb.qualify_observation(house_raw, house_violation_meta, cutoff=as_of.isoformat())
        inherited_limitations: list[str] = []
        if house_q.value_state.value == "refused":
            raw = None
            for tag in house_q.limitations:
                if tag in ("after_cutoff", "cutoff_unparsable", "evidence_time_unparsable"):
                    inherited_limitations.append(tag)
        if raw is None:
            value_state = "refused" if inherited_limitations else "missing"
        else:
            value_state = "present"
        limitations = ["rights_unknown"] + inherited_limitations
        if not has_entry:
            limitations.append("no_next_release_entry")
        record = {
            "lens_id": lens_id,
            "label_en": f"Cleveland Fed nowcast (third-party model), next CPI-U {m} print, % m/m",
            "source_class": "external_model_nowcast",
            "evidence_class": None,
            "measure": "next_release",
            "basket_or_index": "CPI-U",
            "scope": m,
            "frequency": "monthly",
            "transform": "pct_mom",
            "unit": "pct_mom",
            "horizon": "next_print",
            "reference_period": {"start": ref_start, "end": ref_end},
            "value": raw,
            "value_state": value_state,
            "interval": None,
            "observation_date": None,
            "source": "release_radar:benchmark_set.cleveland_nowcast" if has_entry else "",
            "series_id": None,
            "blend_inputs": None,
            "limitations": sorted(set(limitations)),
            "qualified": None,
        }
        return record, None

    if kind == "expectation":
        if not has_entry:
            lens_gaps.append("no_next_release_entry")
        else:
            lens_gaps.append("b0_evidence_class_absent:external_benchmark_blend")
        exp_read = entry.get("expectation_read") if isinstance(entry, dict) and isinstance(entry.get("expectation_read"), dict) else {}
        raw = _number(exp_read.get("expectation_median")) if has_entry else None
        proj = entry.get("projection") if isinstance(entry, dict) and isinstance(entry.get("projection"), dict) else {}
        house_raw = _number(proj.get("point")) if has_entry else None
        house_meta = {
            "evidence_class": rcb.EvidenceClass.HOUSE_ESTIMATE.value,
            "unit": "pct_mom",
            "target": target,
            "basket_or_index": "CPI-U",
            "reference_start": ref_start,
            "reference_end": ref_end,
            "observation_time": radar_asof,
            "observation_precision": "minute",
            "first_public_evidence": radar_asof,
            "first_public_precision": "minute",
        }
        house_q = rcb.qualify_observation(
            house_raw, house_meta, cutoff=as_of.isoformat()
        )
        inherited_limitations: list[str] = []
        if house_q.value_state.value == "refused":
            raw = None
            for tag in house_q.limitations:
                if tag in ("after_cutoff", "cutoff_unparsable", "evidence_time_unparsable"):
                    inherited_limitations.append(tag)
        if raw is None:
            value_state = "refused" if inherited_limitations else "missing"
        else:
            value_state = "present"
        sources_list = [str(x) for x in (exp_read.get("sources") or [])] if has_entry else []
        limitations = ["blend_of_external_benchmarks_not_street_economist_survey_median"] + inherited_limitations
        if not has_entry:
            limitations.append("no_next_release_entry")
        record = {
            "lens_id": lens_id,
            "label_en": f"Release Radar expectation median (blend of external benchmarks), next CPI-U {m} print, % m/m",
            "source_class": "external_benchmark_blend",
            "evidence_class": None,
            "measure": "next_release",
            "basket_or_index": "CPI-U",
            "scope": m,
            "frequency": "monthly",
            "transform": "pct_mom",
            "unit": "pct_mom",
            "horizon": "next_print",
            "reference_period": {"start": ref_start, "end": ref_end},
            "value": raw,
            "value_state": value_state,
            "interval": None,
            "observation_date": None,
            "source": "release_radar:expectation_read.expectation_median" if has_entry else "",
            "series_id": None,
            "blend_inputs": list(sources_list),
            "limitations": sorted(set(limitations)),
            "qualified": None,
        }
        return record, None

    # kind == "market"
    if not has_entry:
        lens_gaps.append("no_next_release_entry")
    benchmark_set = entry.get("benchmark_set") if isinstance(entry, dict) and isinstance(entry.get("benchmark_set"), dict) else {}
    market_implied = benchmark_set.get("market_implied")
    if not isinstance(market_implied, dict):
        # Try the entry-level fallback (some radars nest differently).
        market_implied = entry.get("market_implied") if isinstance(entry, dict) else None
    if not isinstance(market_implied, dict):
        raw = None
        market_source = None
        event_ticker = None
        market_asof = None
    else:
        raw = _number(market_implied.get("implied_median"))
        market_source = market_implied.get("source")
        event_ticker = market_implied.get("event_ticker")
        market_asof = market_implied.get("asof")
    meta = {
        **base_meta,
        "evidence_class": rcb.EvidenceClass.MARKET_IMPLIED_EXPECTATION.value,
        "reference_start": ref_start if has_entry else None,
        "reference_end": ref_end if has_entry else None,
        "tenor": None,
        "observation_time": market_asof if has_entry else None,
        "observation_precision": "day",
        "seasonal_treatment": "sa",
        "rate_index": "n/a",
        "averaging_law": "n/a",
        "source": str(market_source) if market_source is not None else None,
        "source_version": None,
        "content_ref": str(event_ticker) if event_ticker is not None else None,
        "first_public_evidence": radar_asof if has_entry else None,
        "first_public_precision": "minute",
        "model_id": None,
        "target_epoch": None,
        "rights": "unknown",
        "quality": (),
        "limitations": (),
    }
    qualified = rcb.qualify_observation(raw, meta, cutoff=as_of.isoformat())
    record = _qualified_lens_record(
        qualified=qualified,
        lens_id=lens_id,
        label_en=f"Prediction-market implied median ({market_source or 'unknown'}), next CPI-U {m} print, % m/m",
        source_class="prediction_market",
        scope=m,
        frequency="monthly",
        unit="pct_mom",
        horizon="next_print",
        transform="pct_mom",
        source=(str(market_source) if market_source is not None else "release_radar:market_implied"),
        series_id=None,
        basket_or_index="CPI-U",
        measure="next_release",
        reference_period={"start": ref_start, "end": ref_end},
        observation_date=(str(market_asof) if market_asof is not None else None),
        lens_limitations=([] if has_entry else ["no_next_release_entry"]),
    )
    return record, qualified


def _matched_lenses(
    repo: Path,
    as_of: date,
    radar: dict[str, Any] | None,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the ``matched_lenses`` block (the §2.1+ appended code path).

    Each lens helper returns ``(record, qualified)``. The builder stores the
    live B0 object in a local ``objs[lens_id]`` map and passes
    those objects DIRECTLY to ``rcb.compare_qualified`` -- never rebuilds an
    operand from a dict and never mints a stub.
    """
    from engine import rates_command_basis as rcb  # local import per §2.2

    lens_gaps: list[str] = []
    lenses: dict[str, dict[str, Any]] = {}
    objs: dict[str, Any] = {}

    for family in ("cpi", "pce"):
        for m in ("headline", "core"):
            for unit in ("pct_mom", "pct_yoy"):
                record, qualified = _official_lens(repo, as_of, lens_gaps, family=family, m=m, unit=unit)
                objs[record["lens_id"]] = qualified
                lenses[record["lens_id"]] = record

    grouped = _next_release_entry(entries, as_of)
    radar_for_lens = radar
    for kind in ("house", "combined", "cleveland", "expectation", "market"):
        for m in ("headline", "core"):
            record, qualified = _next_print_lens(
                repo, as_of, lens_gaps,
                grouped=grouped, radar=radar_for_lens, m=m, kind=kind,
            )
            objs[record["lens_id"]] = qualified
            lenses[record["lens_id"]] = record

    # market_breakeven_10y
    sid, col, tenor, target = _BREAKEVEN_SERIES["10y"]
    record, qualified = _daily_lens(
        repo, as_of, lens_gaps,
        series_id=sid, column=col,
        lens_id="market_breakeven_10y",
        label_en="10-year breakeven inflation (market price, includes premia), % annual",
        source_class="market_price",
        evidence_class_value=rcb.EvidenceClass.MARKET_IMPLIED_EXPECTATION.value,
        scope="all_items_compensation",
        unit="pct_ann_rate",
        target=target,
        tenor=tenor,
        basket_or_index=None,
        rights="public_official",
        lens_limitations=["compensation_includes_risk_and_liquidity_premia"],
        ref_end_years=10,
        curve_convention="par",
    )
    objs["market_breakeven_10y"] = qualified
    lenses["market_breakeven_10y"] = record

    # market_forward_5y5y
    sid, col, tenor, target = _BREAKEVEN_SERIES["5y5y"]
    record, qualified = _daily_lens(
        repo, as_of, lens_gaps,
        series_id=sid, column=col,
        lens_id="market_forward_5y5y",
        label_en="5y5y forward breakeven (market price), % annual",
        source_class="market_price",
        evidence_class_value=rcb.EvidenceClass.MARKET_IMPLIED_EXPECTATION.value,
        scope="all_items_compensation",
        unit="pct_ann_rate",
        target=target,
        tenor=tenor,
        basket_or_index=None,
        rights="public_official",
        lens_limitations=["compensation_includes_risk_and_liquidity_premia"],
        ref_end_years=10,
        curve_convention="par",
    )
    objs["market_forward_5y5y"] = qualified
    lenses["market_forward_5y5y"] = record

    # Cleveland expected inflation 1y/5y/10y
    for tenor_key, ref_years in (("1y", 1), ("5y", 5), ("10y", 10)):
        sid, col, tenor = _EXPINF_SERIES[tenor_key]
        lens_id = f"model_cleveland_expected_inflation_{tenor_key}"
        record, qualified = _monthly_exp_lens(
            repo, as_of, lens_gaps,
            series_id=sid, column=col,
            lens_id=lens_id,
            label_en=f"Cleveland Fed model expected inflation, {tenor_key}, % annual",
            source_class="external_model_estimate",
            evidence_class_value=rcb.EvidenceClass.ESTIMATED_DECOMPOSITION.value,
            scope="expected_inflation",
            target="expected_inflation",
            tenor=tenor,
            basket_or_index=None,
            rights="unknown",
            model_id="cleveland_expinf",
            lens_limitations=[],
            ref_end_years=ref_years,
        )
        objs[lens_id] = qualified
        lenses[lens_id] = record

    # MICH survey
    sid, col, tenor = _SURVEY_SERIES["1y"]
    record, qualified = _monthly_exp_lens(
        repo, as_of, lens_gaps,
        series_id=sid, column=col,
        lens_id="survey_umich_1y",
        label_en="University of Michigan household survey, 1-year expected inflation, %",
        source_class="household_survey",
        evidence_class_value=rcb.EvidenceClass.SURVEY_PARTICIPANT_PROJECTION.value,
        scope="household",
        target="expected_inflation",
        tenor=tenor,
        basket_or_index=None,
        rights="unknown",
        model_id=None,
        lens_limitations=["household_survey_not_cpi_specific"],
        ref_end_years=1,
    )
    objs["survey_umich_1y"] = qualified
    lenses["survey_umich_1y"] = record

    # Fixed comparisons via B0
    comparisons: list[dict[str, Any]] = []
    pairs = [
        (
            "cpi_vs_pce_headline_mom",
            rcb.RULES["cpi_vs_pce.v1"],
            "official_cpi_headline_mom",
            "official_pce_headline_mom",
        ),
        (
            "cpi_vs_pce_core_yoy",
            rcb.RULES["cpi_vs_pce.v1"],
            "official_cpi_core_yoy",
            "official_pce_core_yoy",
        ),
        (
            "next_cpi_mom_vs_breakeven_10y",
            rcb.RULES["cpi_month_vs_breakeven_10y.v1"],
            "house_radar_cpi_headline_next_mom",
            "market_breakeven_10y",
        ),
        (
            "next_cpi_mom_market_vs_breakeven_10y",
            rcb.RULES["cpi_month_vs_breakeven_10y.v1"],
            "market_cpi_headline_next_mom",
            "market_breakeven_10y",
        ),
    ]
    for comparison_id, rule, left_id, right_id in pairs:
        left_obj = objs[left_id]
        right_obj = objs[right_id]
        result = rcb.compare_qualified(left_obj, right_obj, rule)
        comparisons.append({
            "comparison_id": comparison_id,
            "rule_id": rule.rule_id,
            "left_lens": left_id,
            "right_lens": right_id,
            "status": result.status.value,
            "reason": result.reason,
            "difference": result.difference,
            "limitations": list(result.limitations),
        })

    side_by_side_only = [
        {
            "group_id": "next_cpi_headline_mom_estimates",
            "lenses": [
                "house_radar_cpi_headline_next_mom",
                "house_radar_combined_cpi_headline_next_mom",
                "cleveland_nowcast_cpi_headline_next_mom",
                "market_cpi_headline_next_mom",
                "radar_expectation_read_cpi_headline_next_mom",
            ],
            "note": _SIDE_NOTE,
        },
        {
            "group_id": "next_cpi_core_mom_estimates",
            "lenses": [
                "house_radar_cpi_core_next_mom",
                "house_radar_combined_cpi_core_next_mom",
                "cleveland_nowcast_cpi_core_next_mom",
                "market_cpi_core_next_mom",
                "radar_expectation_read_cpi_core_next_mom",
            ],
            "note": _SIDE_NOTE,
        },
        {
            "group_id": "long_horizon_expectations",
            "lenses": [
                "market_breakeven_10y",
                "market_forward_5y5y",
                "model_cleveland_expected_inflation_1y",
                "model_cleveland_expected_inflation_5y",
                "model_cleveland_expected_inflation_10y",
                "survey_umich_1y",
            ],
            "note": _SIDE_NOTE,
        },
    ]

    available = any(
        isinstance(rec, dict) and rec.get("value_state") == "present"
        for rec in lenses.values()
    )
    return {
        "schema": "inflation_matched_lenses.v1",
        "available": available,
        "reason": None,
        "cutoff": as_of.isoformat(),
        "display_only": True,
        "authority": False,
        "law": _LENS_LAW,
        "lenses": lenses,
        "comparisons": comparisons,
        "side_by_side_only": side_by_side_only,
        "street_consensus": _street_consensus(),
        "gaps": sorted(set(lens_gaps)),
    }


def _matched_lenses_safe(
    repo: Path,
    as_of: date,
    radar: dict[str, Any] | None,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        return _matched_lenses(repo, as_of, radar, entries)
    except Exception as exc:  # noqa: BLE001 - display-only boundary
        return {
            "schema": "inflation_matched_lenses.v1",
            "available": False,
            "reason": f"internal_error:{type(exc).__name__}",
            "cutoff": as_of.isoformat() if as_of is not None else None,
            "display_only": True,
            "authority": False,
            "law": _LENS_LAW,
            "lenses": {},
            "comparisons": [],
            "side_by_side_only": [],
            "street_consensus": _street_consensus(),
            "gaps": [f"internal_error:{type(exc).__name__}"],
        }
