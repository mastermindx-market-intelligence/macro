#!/usr/bin/env python3
"""Validate captured public-site evidence into one canonical reference matrix."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

SURFACES = (
    "homepage",
    "market-terminal",
    "mastermind-ai",
    "market-dashboards",
)
STATIC_VARIANTS = ("1440-en", "1440-zh", "1024-en", "390-en", "390-zh")
MOTION_PHASES = ("observe", "reason", "resolve", "hold")


def _expected(kind: str) -> tuple[tuple[str, str], ...]:
    states: Iterable[str] = STATIC_VARIANTS if kind == "static" else MOTION_PHASES
    return tuple((surface, state) for surface in SURFACES for state in states)


def _key(record: dict[str, Any]) -> tuple[str, str, str]:
    kind = str(record.get("kind", ""))
    if kind not in {"static", "motion"}:
        raise ValueError(f"unexpected evidence kind: {kind!r}")
    axis = "variant" if kind == "static" else "phase"
    page = str(record.get("page", ""))
    state = str(record.get(axis, ""))
    if not page or not state:
        raise ValueError(f"{kind} record missing page/{axis}")
    return kind, page, state


def _require_positive(record: dict[str, Any], field: str, label: str) -> int:
    try:
        value = int(record[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{label} missing valid {field}") from exc
    if value <= 0:
        raise ValueError(f"{label} requires positive {field}")
    return value


def _validate_record(record: dict[str, Any]) -> dict[str, Any]:
    kind, page, state = _key(record)
    label = f"{kind} {page}/{state}"
    if record.get("console_errors"):
        raise ValueError(f"{label} has console errors")
    for field in ("file", "sha256", "url"):
        if not record.get(field):
            raise ValueError(f"{label} missing {field}")

    image_width = _require_positive(record, "image_width", label)
    image_height = _require_positive(record, "image_height", label)
    viewport_width = _require_positive(record, "viewport_width", label)
    viewport_height = _require_positive(record, "viewport_height", label)
    document_width = _require_positive(record, "document_width", label)
    document_height = _require_positive(record, "document_height", label)

    if kind == "static":
        if image_width != viewport_width:
            raise ValueError(
                f"static image width mismatch for {page}/{state}: "
                f"image={image_width} viewport={viewport_width}"
            )
        if image_height != document_height or record.get("full_page") is not True:
            raise ValueError(f"static evidence is not an exact full-page capture: {page}/{state}")
    else:
        if (image_width, image_height) != (viewport_width, viewport_height):
            raise ValueError(f"motion evidence viewport mismatch: {page}/{state}")
        if record.get("full_page") is not False:
            raise ValueError(f"motion evidence must be viewport-only: {page}/{state}")
    normalized = dict(record)
    normalized["verified"] = True
    normalized["horizontal_overflow_px"] = max(0, document_width - viewport_width)
    normalized["image_width"] = image_width
    normalized["image_height"] = image_height
    normalized["viewport_width"] = viewport_width
    normalized["viewport_height"] = viewport_height
    normalized["document_width"] = document_width
    normalized["document_height"] = document_height
    return normalized


def _check_complete(
    lookup: dict[tuple[str, str], dict[str, Any]],
    kind: str,
) -> None:
    expected = set(_expected(kind))
    actual = set(lookup)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if not missing and not extra:
        return
    parts = []
    if missing:
        parts.append(
            f"missing {kind}=" + ",".join(f"{page}/{state}" for page, state in missing)
        )
    if extra:
        parts.append(
            f"extra {kind}=" + ",".join(f"{page}/{state}" for page, state in extra)
        )
    raise ValueError("reference evidence mismatch: " + "; ".join(parts))


def build_reference_matrix(
    records: list[dict[str, Any]],
    *,
    operation: str,
    source: dict[str, str],
    built_at: str | None = None,
    browser: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Seal 20 static and 16 motion records into canonical order."""
    if not operation or not source.get("frozen_source") or not source.get("local_head"):
        raise ValueError("operation and complete source identity are required")
    lookups: dict[str, dict[tuple[str, str], dict[str, Any]]] = {
        "static": {},
        "motion": {},
    }
    for raw in records:
        normalized = _validate_record(raw)
        kind, page, state = _key(normalized)
        key = (page, state)
        if key in lookups[kind]:
            raise ValueError(f"duplicate {kind} record: {page}/{state}")
        lookups[kind][key] = normalized

    _check_complete(lookups["static"], "static")
    _check_complete(lookups["motion"], "motion")
    static = [
        lookups["static"][(surface, variant)]
        for surface in SURFACES
        for variant in STATIC_VARIANTS
    ]
    motion = [
        lookups["motion"][(surface, phase)]
        for surface in SURFACES
        for phase in MOTION_PHASES
    ]
    return {
        "schema": "mastermindx.public_site_figma_reference_matrix.v1",
        "operation": operation,
        "built_at": built_at or datetime.now(timezone.utc).isoformat(),
        "source": dict(source),
        "browser": dict(browser or {}),
        "counts": {"static": len(static), "motion": len(motion), "total": len(records)},
        "static": static,
        "motion": motion,
    }
