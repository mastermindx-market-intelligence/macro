"""Bounded PAYEMS revision projection through the existing Release Target owner.

No collector, retrospective custody claim or labor-state calculation lives
here. The original official prior-two-month revision obligation stays absent.
Only the optional file reader imports the data-analysis dependencies.
"""
from __future__ import annotations

import copy
import math
import re
from datetime import date, datetime
from typing import Any, Mapping

METHOD = "payroll_retained_vintages.v1"
BASIS = "retrospective_alfred_recorded_vintages"
PREFIX = "payroll_revision:"
MAX_PERIODS = 24
ROLES = ("earliest_change", "selected_change", "net_revision", "earliest_vintage", "selected_vintage")
NUMERIC_ROLES = frozenset(ROLES[:3])
SOURCE_ID = "revision:alfred:PAYEMS"
MANIFEST_SOURCE_ID = "revision:alfred:manifest"
ARTIFACT = "data/fred_vintage/release_targets/PAYEMS_all_vintages.parquet"
MANIFEST = "data/fred_vintage/release_targets/manifest.json"
LIMITATION = (
    "ALFRED recorded vintage dates; retrospective reconstruction at day precision. "
    "Earliest retained is not certified first publication. Selected vintage is not a revision-event time. "
    "This does not establish historical Mastermind availability, an intraday release print, "
    "or the official combined revision to the prior two months."
)


def _day(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("payroll cutoff and vintage dates must be YYYY-MM-DD")
    return date.fromisoformat(value).isoformat()


def metric_identity(metric_id: Any) -> tuple[str, str] | None:
    if not isinstance(metric_id, str):
        return None
    match = re.fullmatch(r"payroll_revision:(\d{4}-\d{2}-01):([a-z_]+)", metric_id)
    if not match or match[2] not in ROLES:
        return None
    return _day(match[1]), match[2]


def _metric(metric_id: str, value: float | str | None, *, role: str, period: str | None,
            projection: Mapping, missing: str = "INSUFFICIENT_HISTORY") -> dict:
    present = value is not None
    return {
        "metric_id": metric_id, "reference_id": f"mastermind.market_reference/v1#{metric_id}",
        "definition_id": f"{METHOD}.{role}", "definition_version": "1.0.0", "owner_ref": ARTIFACT,
        "value": value, "value_type": "number" if role in NUMERIC_ROLES else "categorical",
        "unit": "thousands" if role in NUMERIC_ROLES else None,
        "basis": BASIS, "direction_semantics": None,
        "reference_period": period, "observed_at": None, "released_at": None,
        "available_at": None, "collected_at": projection["collected_at"], "revised_at": None,
        "calculation_as_of": projection["cutoff"], "market_session": None,
        "source_refs": [SOURCE_ID, MANIFEST_SOURCE_ID] if projection["source_digest"] else [],
        "source_digest": projection["source_digest"], "transformation": LIMITATION,
        "model_version": METHOD, "uncertainty": {"kind": None, "value": None},
        "coverage": None, "freshness": "HISTORICAL_AS_KNOWN" if present else "NOT_COVERED",
        "rights_state": "OPEN", "status": "PRESENT" if present else "ABSENT",
        "null_reason": None if present else missing, "authority_ceiling": "DESCRIPTIVE",
    }


def attach_payroll_revisions(snapshot: Mapping, projection: Mapping) -> dict:
    """Attach plain metrics and sources without changing any regime or authority."""
    if (snapshot.get("workspace") or {}).get("id") != "labor_markets":
        raise ValueError("payroll revision projection belongs only to labor_markets")
    if any(str(item.get("metric_id", "")).startswith(PREFIX)
           for item in (snapshot.get("metrics") or {}).get("items", [])):
        raise ValueError("payroll revision owner already attached")
    body = copy.deepcopy(snapshot)
    rows = projection["rows"]
    if not rows:
        body["metrics"]["items"].append(_metric(
            PREFIX + "availability", None, role="availability", period=None, projection=projection,
            missing=projection["unavailable_reason"] or "NOT_COVERED"))
    for row in rows:
        for role in ROLES:
            body["metrics"]["items"].append(_metric(
                f"{PREFIX}{row['period']}:{role}", row[role], role=role,
                period=row["period"], projection=projection))
    if projection["source_digest"]:
        for source_id, label, artifact, digest in (
            (SOURCE_ID, {"en": "Nonfarm payrolls · retained ALFRED vintages", "zh": "非农就业·保留的ALFRED版本"}, ARTIFACT, projection["source_digest"]),
            (MANIFEST_SOURCE_ID, {"en": "Release-data collection receipt", "zh": "发布数据采集凭证"}, MANIFEST, projection["manifest_digest"]),
        ):
            body["sources"]["items"].append({
                "source_id": source_id, "label": label,
                "owner_ref": "https://alfred.stlouisfed.org/series?seid=PAYEMS" if source_id == SOURCE_ID else MANIFEST,
                "provider": "U.S. Bureau of Labor Statistics via FRED/ALFRED" if source_id == SOURCE_ID else "Mastermind release-target collector",
                "reference_period": rows[-1]["period"] if rows else None,
                "released_at": None, "first_known_at": None, "collected_at": projection["collected_at"],
                "revised_at": None, "correction_state": "unknown", "transform": LIMITATION,
                "rights_state": "OPEN", "definition_id": METHOD, "definition_version": "1.0.0",
                "artifact_ref": f"{artifact}#sha256={digest}", "freshness": "HISTORICAL_AS_KNOWN",
            })
    # Validate the representation itself before it reaches either consumer.
    read_payroll_revision_metrics(body)
    return body


def read_payroll_revision_metrics(snapshot: Mapping) -> dict | None:
    """Pure decoding of scalar groups; malformed partial triples are refused."""
    metrics = [item for item in (snapshot.get("metrics") or {}).get("items", [])
               if str(item.get("metric_id", "")).startswith(PREFIX)]
    if not metrics:
        return None
    if (snapshot.get("workspace") or {}).get("id") != "labor_markets":
        raise ValueError("payroll metrics outside labor workspace")
    first = metrics[0]
    cutoff = _day(first["calculation_as_of"])
    common = (first["source_digest"], first["collected_at"], first["source_refs"])
    if common[0] is not None:
        if common[2] != [SOURCE_ID, MANIFEST_SOURCE_ID]:
            raise ValueError("payroll source identities are not bound")
        sources = (snapshot.get("sources") or {}).get("items", [])
        for source_id in common[2]:
            matching = [source for source in sources if source.get("source_id") == source_id]
            if len(matching) != 1:
                raise ValueError("payroll source disclosure is missing or duplicated")
            source = matching[0]
            expected_artifact = ARTIFACT if source_id == SOURCE_ID else MANIFEST
            ref = source.get("artifact_ref", "")
            if (not isinstance(ref, str) or not re.fullmatch(re.escape(expected_artifact) + r"#sha256=[a-f0-9]{64}", ref)
                    or source_id == SOURCE_ID and ref != f"{ARTIFACT}#sha256={common[0]}"
                    or source.get("definition_id") != METHOD or source.get("collected_at") != common[1]
                    or any(source.get(clock) is not None for clock in ("released_at", "first_known_at", "revised_at"))):
                raise ValueError("payroll source receipt is inconsistent")
        if common[1] is not None:
            try:
                collected = datetime.fromisoformat(common[1].replace("Z", "+00:00"))
                built = datetime.fromisoformat(snapshot["generation"]["built_at"].replace("Z", "+00:00"))
                if collected.utcoffset() is None or built.utcoffset() is None or collected > built:
                    raise ValueError("collection after publication or without timezone")
            except (ValueError, TypeError, AttributeError, KeyError) as exc:
                raise ValueError("payroll collection clock is invalid for this publication") from exc
    groups = {}
    for metric in metrics:
        if (metric.get("basis") != BASIS or metric.get("model_version") != METHOD
                or metric.get("definition_version") != "1.0.0" or metric.get("calculation_as_of") != cutoff
                or (metric.get("source_digest"), metric.get("collected_at"), metric.get("source_refs")) != common
                or any(metric.get(clock) is not None for clock in ("observed_at", "available_at", "released_at", "revised_at"))):
            raise ValueError("inconsistent payroll metric provenance")
        identity = metric_identity(metric["metric_id"])
        if identity is None:
            if len(metrics) == 1 and metric["metric_id"] == PREFIX + "availability" and metric["value"] is None:
                return {"cutoff": cutoff, "rows": [], "source_digest": common[0], "collected_at": common[1],
                        "source_refs": common[2], "unavailable_reason": metric["null_reason"]}
            raise ValueError("unknown payroll metric identity")
        period, role = identity
        if period > cutoff or metric.get("reference_period") != period or metric.get("definition_id") != f"{METHOD}.{role}":
            raise ValueError("inconsistent payroll reference period or method")
        row = groups.setdefault(period, {"period": period, "metric_ids": {}})
        if role in row:
            raise ValueError("duplicate payroll metric role")
        value = metric["value"]
        if role in NUMERIC_ROLES:
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError("non-finite payroll reading")
            if metric.get("unit") != "thousands" or metric.get("value_type") != "number":
                raise ValueError("incorrect payroll unit")
        elif value is not None:
            _day(value)
            if metric.get("value_type") != "categorical" or metric.get("unit") is not None:
                raise ValueError("incorrect payroll vintage-day type")
        if metric.get("status") != ("PRESENT" if value is not None else "ABSENT"):
            raise ValueError("inconsistent payroll presence")
        row[role], row["metric_ids"][role] = value, metric["metric_id"]
    if not 1 <= len(groups) <= MAX_PERIODS or not re.fullmatch(r"[a-f0-9]{64}", common[0] or ""):
        raise ValueError("invalid payroll group or digest bound")
    for row in groups.values():
        if any(role not in row for role in ROLES):
            raise ValueError("incomplete payroll revision group")
        first_date, selected_date = row["earliest_vintage"], row["selected_vintage"]
        if not first_date or not selected_date or not row["period"] <= first_date <= selected_date <= cutoff:
            raise ValueError("payroll vintage ordering is invalid")
        a, b, delta = row["earliest_change"], row["selected_change"], row["net_revision"]
        if (a is None or b is None):
            if delta is not None:
                raise ValueError("payroll revision requires both same-vintage changes")
        elif delta is None or not math.isclose(delta, b - a, rel_tol=1e-12, abs_tol=1e-9):
            raise ValueError("payroll net revision arithmetic is inconsistent")
    return {"cutoff": cutoff, "rows": [groups[key] for key in sorted(groups)],
            "source_digest": common[0], "collected_at": common[1], "source_refs": common[2],
            "unavailable_reason": None}
