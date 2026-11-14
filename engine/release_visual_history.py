"""Source-bound visual history for the existing MRI Release Radar.

Long chart = one ALFRED vintage snapshot of revised index levels, never a
fabricated sequence of first prints. Short first-print markers = qualified
official_actuals receipts. This module has no collection or publication owner.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone, timedelta, date
from hashlib import sha256
from pathlib import Path
import json
import math
import re
from typing import Any

from engine.release_actuals import load_actual_ledger, receipt_integrity_errors
from engine.release_target_truth import load_full_vintage_parquets

SCHEMA = "release_visual_history.v1"
MANIFEST = "data/fred_vintage/release_targets/manifest.json"
ACTUALS = "data/release_forecast/official_actuals.jsonl"
DEFECTS = "data/release_forecast/official_actual_defects.json"
MAX_ARTIFACT_BYTES = 5_000_000
MAX_HISTORY = 72
TARGETS = {
    "ppi_finaldemand": ("PPIFIS", "Producer prices — final demand", "生产者价格 — 最终需求"),
    "cpi_headline": ("CPIAUCSL", "Consumer prices", "消费者价格"),
    "cpi_core": ("CPILFESL", "Core consumer prices", "核心消费者价格"),
    "pce_headline": ("PCEPI", "PCE prices", "PCE 价格"),
    "pce_core": ("PCEPILFE", "Core PCE prices", "核心 PCE 价格"),
}
# Official BLS headline 12-month rates use unadjusted price indexes;
# BLS monthly prints use seasonally adjusted indexes. BEA PCE series
# are seasonally adjusted for both published comparison horizons.
# These IDs are optional chart inputs in the EXISTING ALFRED cohort.
YOY_HEADLINE_SERIES = {
    "ppi_finaldemand": "PPIFID",
    "cpi_headline": "CPIAUCNS",
    "cpi_core": "CPILFENS",
    "pce_headline": "PCEPI",
    "pce_core": "PCEPILFE",
}
OFFICIAL_RELEASE = {
    "ppi_finaldemand": "ppi_finaldemand",
    "cpi_headline": "cpi_headline",
    "cpi_core": "cpi_core",
    "pce_headline": "pce_headline",
    "pce_core": "pce_core",
}
_SAFE_HEX = re.compile(r"^[a-f0-9]{64}$")


def _clock(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("invalid_clock")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_clock") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("unqualified_clock")
    return parsed.astimezone(timezone.utc)


def _authority() -> dict[str, bool]:
    return {field: False for field in ("can_score", "can_rank", "can_gate", "can_size", "can_trade")}


def _month_before(ym: str, lag: int) -> str:
    year, month = (int(n) for n in ym.split("-"))
    index = year * 12 + month - 1 - lag
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def _change(levels: dict[str, float], lag: int, *,
            withheld: list[str] | None = None) -> list[dict[str, Any]]:
    points = []
    for period in sorted(levels):
        previous = levels.get(_month_before(period, lag))
        current = levels[period]
        if previous is None or previous <= 0 or not math.isfinite(current):
            continue
        rate = 100 * (current / previous - 1)
        # Finite index levels can overflow either division or percentage scaling.
        # Preserve the gap; never poison the shared forecast JSON or invent a rate.
        if not math.isfinite(rate):
            if withheld is not None:
                withheld.append(period)
            continue
        points.append({"period": period, "value": round(rate, 3)})
    return points[-MAX_HISTORY:]


def _frame_points(frame: Any, snapshot_date: date) -> dict[str, Any]:
    """Choose each observation from exactly one active vintage at collection time."""
    mask = (
        frame["realtime_start"].dt.date.le(snapshot_date)
        & frame["realtime_end"].map(lambda end: isinstance(end, date) and end >= snapshot_date)
    )
    active = frame.loc[mask]
    if active["period"].duplicated().any():
        raise ValueError("overlapping_active_vintages")
    levels = {}
    for row in active.itertuples(index=False):
        period = row.period.strftime("%Y-%m")
        value = float(row.value)
        if math.isfinite(value) and value > 0:
            levels[period] = value
    withheld: dict[str, list[str]] = {"yoy": [], "mom": []}
    curves: dict[str, Any] = {
        "yoy": _change(levels, 12, withheld=withheld["yoy"]),
        "mom": _change(levels, 1, withheld=withheld["mom"]),
    }
    if any(withheld.values()):
        curves["withheld_periods"] = withheld
    return curves


def _receipt_groups(root: Path, asof: datetime) -> dict[str, list[dict[str, Any]]]:
    """Read existing immutable first prints without manufacturing missing history."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in load_actual_ledger(root / ACTUALS):
        if not isinstance(row, dict) or row.get("row_type") != "actual" or row.get("sequence") != "first":
            continue
        if row.get("release") not in TARGETS or row.get("unit") != "percent":
            continue
        try:
            if _clock(row.get("observed_at")) > asof or _clock(row.get("source_released_at")) > asof:
                continue
            if receipt_integrity_errors(row, defects_path=root / DEFECTS):
                continue
            value = float(row["actual"])
            if not math.isfinite(value):
                continue
            grouped[(row["release"], row["period"])].append(row)
        except (ValueError, TypeError, KeyError, OSError):
            continue
    by_release: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (release, period), receipts in grouped.items():
        # Conflicting first prints are not resolved by picking the latest revision.
        if len({(r.get("receipt_id"), r.get("actual")) for r in receipts}) != 1:
            continue
        row = receipts[0]
        by_release[release].append({
            "period": period, "value": float(row["actual"]),
            "released_at": row["source_released_at"],
            "source_url": row["source_url"],
            "basis": "verified_official_first_print_mom",
        })
    return {key: sorted(rows, key=lambda r: r["period"])[-18:] for key, rows in by_release.items()}


def _series(root: Path, series_id: str, metadata: dict[str, Any],
            snapshot_date: date) -> dict[str, Any]:
    expected_relpath = f"data/fred_vintage/release_targets/{series_id}_all_vintages.parquet"
    if metadata.get("path") != expected_relpath or metadata.get("status") != "written":
        raise ValueError("manifest_series_not_qualified")
    digest = metadata.get("artifact_sha256")
    size = metadata.get("artifact_bytes")
    if not isinstance(digest, str) or not _SAFE_HEX.fullmatch(digest):
        raise ValueError("manifest_sha_invalid")
    if type(size) is not int or not (0 < size <= MAX_ARTIFACT_BYTES):
        raise ValueError("manifest_size_invalid")
    path = root / expected_relpath
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("vintage_artifact_missing") from exc
    if len(raw) != size or sha256(raw).hexdigest() != digest:
        raise ValueError("vintage_manifest_integrity_mismatch")
    frame = load_full_vintage_parquets(path, series_id=series_id)
    return _frame_points(frame, snapshot_date)


def build_release_visual_history(root: str | Path, *, asof: str) -> dict[str, Any]:
    """Additive read-only MRI projection. Missing sources remain unavailable."""
    root = Path(root)
    result: dict[str, Any] = {
        "schema": SCHEMA, "asof": asof, "display_only": True, "authority": _authority(),
        "status": "unavailable", "source_basis": "alfred_revised_index_asof_collection",
        "first_print_basis": "verified_official_first_print_mom",
        "source": "FRED/ALFRED", "source_collected_at": None,
        "series": [], "reason_codes": [],
    }
    try:
        cutoff = _clock(asof)
        path = root / MANIFEST
        if path.stat().st_size > 100_000:
            raise ValueError("manifest_oversized")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or manifest.get("schema") != "release_target_vintage_collection.v1":
            raise ValueError("manifest_schema_invalid")
        if manifest.get("status") != "ok" or manifest.get("source_output_type") != 2:
            raise ValueError("manifest_collection_incomplete")
        if manifest.get("integrity_profile") != "release_target_artifact_sha256_bytes.v1":
            raise ValueError("manifest_missing_sha256_bytes_profile")
        collected = _clock(manifest.get("completed_at"))
        if collected > cutoff:
            raise ValueError("future_collection_clock")
        if not isinstance(manifest.get("series"), dict):
            raise ValueError("missing_series_manifest")
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        result["reason_codes"] = [str(exc) if isinstance(exc, ValueError) else "vintage_manifest_unavailable"]
        return result
    result["source_collected_at"] = collected.isoformat()
    result["source_status"] = "stale" if cutoff - collected > timedelta(days=7) else "recent"
    receipts = _receipt_groups(root, cutoff)
    for release, (series_id, name_en, name_zh) in TARGETS.items():
        item: dict[str, Any] = {
            "release": release, "series_id": series_id,
            "name_en": name_en, "name_zh": name_zh,
            "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
            "status": "unavailable", "yoy": [], "mom": [],
            "withheld_periods": {"yoy": [], "mom": []},
            "basis_metadata": {
                "yoy": {"series_id": series_id, "seasonal_adjustment": "SA",
                        "official_reported_basis_comparable": release.startswith("pce_"),
                        "first_print": False, "basis_note": "SA_index_derived_yoy"},
                "mom": {"series_id": series_id, "seasonal_adjustment": "SA",
                        "official_reported_basis_comparable": True,
                        "first_print": False, "basis_note": "SA_index_derived_mom"},
            },
            "first_prints": receipts.get(OFFICIAL_RELEASE[release], []),
        }
        try:
            meta = manifest["series"].get(series_id)
            if not isinstance(meta, dict):
                raise ValueError("series_manifest_missing")
            curves = _series(root, series_id, meta, collected.date())
            item.update(curves)
            # Official BLS 12-month headline: NSA year-over-year, never SA.
            # A missing optional NSA series retains an explicitly labelled SA
            # trend proxy; it is NOT the reported BLS 12-month release reading.
            headline_id = YOY_HEADLINE_SERIES[release]
            if headline_id != series_id:
                try:
                    headline_meta = manifest["series"].get(headline_id)
                    if not isinstance(headline_meta, dict):
                        raise ValueError("official_nsa_series_not_collected")
                    headline_curves = _series(root, headline_id, headline_meta, collected.date())
                    if not headline_curves["yoy"]:
                        raise ValueError("official_nsa_yoy_observations_missing")
                    item["yoy"] = headline_curves["yoy"]
                    item["withheld_periods"]["yoy"] = headline_curves.get(
                        "withheld_periods", {}).get("yoy", [])
                    item["basis_metadata"]["yoy"] = {
                        "series_id": headline_id,
                        "seasonal_adjustment": "NSA",
                        "official_reported_basis_comparable": True,
                        "first_print": False,
                        "basis_note": "NSA_index_derived_yoy_not_official_first_print",
                    }
                except (OSError, ValueError, TypeError, KeyError, ImportError) as nsa_error:
                    result["reason_codes"].append(f"{release}:nsa:{str(nsa_error)}")
            else:
                item["basis_metadata"]["yoy"]["basis_note"] = "BEA_SA_index_derived_yoy"
            incomplete = any(item["withheld_periods"].values())
            item["status"] = (("partial" if incomplete else "available")
                              if item["yoy"] or item["mom"] else "history_insufficient")
            for basis, periods in item["withheld_periods"].items():
                if periods:
                    result["reason_codes"].append(f"{release}:{basis}:derived_rate_nonfinite")
            item["last_observation"] = max(
                (p["period"] for p in (item["yoy"] + item["mom"])), default=None
            )
        except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
            result["reason_codes"].append(f"{release}:{str(exc)}")
        result["series"].append(item)
    available = sum(s["status"] == "available" for s in result["series"])
    usable = sum(s["status"] in ("available", "partial") for s in result["series"])
    result["status"] = ("available" if available == len(TARGETS) else
                        "partial" if usable else "unavailable")
    if result["source_status"] == "stale":
        result["reason_codes"].append("source_history_collection_stale")
    return result
