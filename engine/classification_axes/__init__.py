"""Display-only classification axis cells (AxisCell v1).

An AxisCell is one point-in-time reading on a classification axis (SEC
industry, geography, macro sensitivity, business model, lifecycle, value
chain). It carries context for a subject. It does not size a trade, rank a
name, or act as a gate.

Gate #2: finviz_themes, ths_concepts, and ltheme ids are internal-only and are
never a subject, input, or output of a house-owned cell.
Gate #8: this package is a pure contract over caller-supplied fields. It
writes nothing, resolves no rights, and does not mint a second theme registry.
"""
from __future__ import annotations

from engine.classification_axes.cell import (
    AXES,
    FORBIDDEN_VALUE_KEY_WORDS,
    LABELS,
    REASON_CODES,
    SCHEMA_VERSION,
    STATUSES,
    AxisCellError,
    available,
    company_parts,
    make_cell,
    missing,
    parse_subject,
    to_json,
    validate_cell,
)

__all__ = [
    "SCHEMA_VERSION",
    "AXES",
    "STATUSES",
    "REASON_CODES",
    "LABELS",
    "FORBIDDEN_VALUE_KEY_WORDS",
    "AxisCellError",
    "make_cell",
    "available",
    "missing",
    "validate_cell",
    "parse_subject",
    "company_parts",
    "to_json",
]
