"""Classification-axis registry — one display-only AxisRow per subject.

:func:`read_axes` asks every selected axis reader what it says about one
subject at one ``as_of`` and assembles the AxisCells into a single row in
``cell.AXES`` order. It is a display-tier composition with no
aggregation: the row never weights, ranks, scores, sizes, or summarises
its cells — it only carries them.

Gate #2: vendor local themes (``ltheme:finviz:*``, ``ltheme:ths:*``, the
``finviz_themes`` / ``ths_concepts`` suites) are never subjects.
``cell.parse_subject`` enforces that before any reader is called.
Gate #8: a pure reader. No cache, no writes, no second registry — the
axis artifacts stay the owners of their own data; this module owns only
the composition, and ``abstentions()`` is the one place that names the
facets the taxonomy reserves but does not yet populate.

``root`` is forwarded unchanged to every reader, so a caller can point
the whole row at an alternate tree. To inject data into one axis, pass
``readers={axis: functools.partial(read_<axis>, frame=...)}``.

Failure is per axis. A reader that is absent, unimportable, missing its
entry point, raises, or hands back a cell for a different question
degrades ITS OWN cell to a typed ``unavailable`` cell and never takes
down the row. Provenance carries the exception CLASS name only, never a
message — messages can carry paths or data.
"""
from __future__ import annotations

import copy
import datetime
import importlib
import json
import re
from collections.abc import Mapping

from engine.classification_axes import cell

ROW_SCHEMA_VERSION = "axis_row.v1"
REGISTRY_OWNER = "engine/classification_axes/registry.py"
ROW_LABELS = ("read_time_composition",)

# Facets the edge contract reserves but the theme graph does not yet
# populate. The row abstains instead of answering; the four relation
# names are sorted and exist in the contract's edge ``type`` enum with
# zero rows in the graph today.
ABSTENTIONS: tuple[dict, ...] = ({
    "facet": "supply_chain",
    "status": "not_populated",
    "labels": ["NO_MAPPING"],
    "reserved_edge_types": ["BENEFITS_FROM", "BOTTLENECK_OF", "ENABLES", "SUPPLIES"],
    "contract": "contracts/theme_graph/edges.v1.schema.json",
},)

_ROW_KEYS = (
    "schema_version",
    "subject_id",
    "as_of",
    "cells",
    "abstentions",
    "labels",
    "quality",
)
_ROW_KEY_SET = frozenset(_ROW_KEYS)
_ABSTENTION_KEYS = ("facet", "status", "labels", "reserved_edge_types", "contract")
_AS_OF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _row_error(message: str) -> cell.AxisCellError:
    return cell.AxisCellError(message, problems=[message])


def _as_of_problem(as_of: object) -> str | None:
    """The as_of rule shared with ``cell.validate_cell``: a real calendar date."""
    if isinstance(as_of, str) and _AS_OF_RE.fullmatch(as_of):
        try:
            datetime.date.fromisoformat(as_of)
        except ValueError:
            pass
        else:
            return None
    return f"as_of must be a valid YYYY-MM-DD date, got {as_of!r}"


def _select_axes(axes: object) -> list[str]:
    if axes is None:
        return list(cell.AXES)
    if isinstance(axes, str):
        raise _row_error(f"axes must be a non-string iterable of axis names, got {axes!r}")
    try:
        requested = list(axes)
    except TypeError as exc:
        raise _row_error(f"axes must be an iterable of axis names, got {axes!r}") from exc
    if not requested:
        raise _row_error("axes must not be empty")
    for name in requested:
        if name not in cell.AXES:
            raise _row_error(f"axis {name!r} is not one of the classification axes")
    return [axis for axis in cell.AXES if axis in requested]


def _check_readers(readers: object) -> dict | None:
    if readers is None:
        return None
    if not isinstance(readers, Mapping):
        raise _row_error(
            f"readers must be a mapping of axis name to callable, got {type(readers).__name__}"
        )
    for key, value in readers.items():
        if key not in cell.AXES:
            raise _row_error(f"readers key {key!r} is not one of the classification axes")
        if not callable(value):
            raise _row_error(f"readers value for {key!r} must be callable")
    return dict(readers)


def _degraded(axis: str, subject_id: str, as_of: str, reason_code: str, marker: str) -> dict:
    return cell.missing(
        axis=axis,
        subject_id=subject_id,
        status="unavailable",
        reason_code=reason_code,
        as_of=as_of,
        source={
            "owner": REGISTRY_OWNER,
            "artifact": f"engine/classification_axes/{axis}.py",
            "field": None,
        },
        provenance=[marker],
    )


def _discover(axis: str) -> tuple[object, str | None, list[str] | None]:
    """Resolve ``read_<axis>`` lazily. Returns ``(fn, reason_code, provenance)``.

    ``reason_code`` is None exactly when a callable reader was found.
    """
    module_name = f"engine.classification_axes.{axis}"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if getattr(exc, "name", None) == module_name:
            return None, "owner_missing", ["registry_reader_absent"]
        return None, "owner_degraded", [f"registry_import_error:{type(exc).__name__}"]
    except Exception as exc:  # noqa: BLE001 — a broken import degrades, never raises
        return None, "owner_degraded", [f"registry_import_error:{type(exc).__name__}"]
    fn = getattr(module, f"read_{axis}", None)
    if not callable(fn):
        return None, "owner_degraded", ["registry_reader_missing"]
    return fn, None, None


def _read_one(axis: str, fn: object, subject_id: str, as_of: str, root: object) -> dict:
    try:
        returned = fn(subject_id, as_of=as_of, root=root)  # type: ignore[operator]
    except Exception as exc:  # noqa: BLE001 — a broken reader degrades, never raises
        return _degraded(
            axis, subject_id, as_of, "owner_degraded", f"registry_caught:{type(exc).__name__}"
        )
    if cell.validate_cell(returned):
        return _degraded(axis, subject_id, as_of, "owner_degraded", "registry_invalid_cell")
    if (
        returned.get("axis") != axis
        or returned.get("subject_id") != subject_id
        or returned.get("as_of") != as_of
    ):
        return _degraded(axis, subject_id, as_of, "owner_degraded", "registry_mismatched_cell")
    return returned  # type: ignore[no-any-return]


def read_axes(
    subject_id: str,
    *,
    as_of: str,
    root: object = None,
    axes: object = None,
    readers: Mapping | None = None,
) -> dict:
    """One display-only row: what every selected axis says about a subject.

    Validation happens before any reader is called; a bad subject,
    ``as_of``, axis selection, or reader mapping raises
    :class:`cell.AxisCellError`. A reader fault after that point degrades
    only its own cell.
    """
    cell.parse_subject(subject_id)
    problem = _as_of_problem(as_of)
    if problem is not None:
        raise _row_error(problem)
    selected = _select_axes(axes)
    injected = _check_readers(readers)

    cells: dict[str, dict] = {}
    for axis in selected:
        fn: object | None = None
        if injected is not None and axis in injected:
            fn = injected[axis]
        else:
            fn, reason_code, provenance = _discover(axis)
            if fn is None:
                cells[axis] = _degraded(
                    axis, subject_id, as_of, reason_code or "owner_degraded", (provenance or ["registry_reader_missing"])[0]
                )
                continue
        cells[axis] = _read_one(axis, fn, subject_id, as_of, root)
    return {
        "schema_version": ROW_SCHEMA_VERSION,
        "subject_id": subject_id,
        "as_of": as_of,
        "cells": cells,
        "abstentions": abstentions(),
        "labels": list(ROW_LABELS),
        "quality": "display_only",
    }


def abstentions() -> list[dict]:
    """A fresh deep copy of :data:`ABSTENTIONS`; callers may mutate freely."""
    return copy.deepcopy(list(ABSTENTIONS))


def row_to_json(row: dict) -> str:
    """Stable JSON: sorted keys, UTF-8, no NaN, no extra whitespace."""
    return json.dumps(
        row,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )


def _cells_problems(row: dict) -> list[str]:
    problems: list[str] = []
    cells = row["cells"]
    if not isinstance(cells, dict) or not cells:
        problems.append("cells must be a non-empty dict keyed by classification axis")
        return problems
    unknown = sorted(str(key) for key in cells if key not in cell.AXES)
    if unknown:
        problems.append("cells keys that are not classification axes: " + ", ".join(unknown))
        return problems
    expected_order = [axis for axis in cell.AXES if axis in cells]
    if list(cells) != expected_order:
        problems.append(
            "cells keys must follow cell.AXES order, got " + ", ".join(str(key) for key in cells)
        )
    for key, one in cells.items():
        for problem in cell.validate_cell(one):
            problems.append(f"cells[{key}]: {problem}")
        if not isinstance(one, dict):
            continue
        if one.get("axis") != key:
            problems.append(f"cells[{key}].axis must be {key!r}, got {one.get('axis')!r}")
        if one.get("subject_id") != row.get("subject_id"):
            problems.append(f"cells[{key}].subject_id must match the row subject_id")
        if one.get("as_of") != row.get("as_of"):
            problems.append(f"cells[{key}].as_of must match the row as_of")
    return problems


def _sorted_string_list_problems(label: str, items: object) -> list[str]:
    problems: list[str] = []
    if not isinstance(items, list):
        problems.append(f"{label} must be a list, got {type(items).__name__}")
        return problems
    for item in items:
        if not isinstance(item, str) or item == "":
            problems.append(f"{label} items must be non-empty strings")
            break
    try:
        if list(items) != sorted(items):
            problems.append(f"{label} must be sorted")
    except TypeError:
        problems.append(f"{label} must be sorted")
    return problems


def _abstentions_problems(entries: object) -> list[str]:
    problems: list[str] = []
    if not isinstance(entries, list):
        problems.append(f"abstentions must be a list, got {type(entries).__name__}")
        return problems
    for index, entry in enumerate(entries):
        label = f"abstentions[{index}]"
        if not isinstance(entry, dict):
            problems.append(f"{label} must be a dict, got {type(entry).__name__}")
            continue
        keys = set(entry)
        if keys != set(_ABSTENTION_KEYS):
            missing = sorted(set(_ABSTENTION_KEYS) - keys)
            extra = sorted(str(key) for key in keys - set(_ABSTENTION_KEYS))
            detail: list[str] = []
            if missing:
                detail.append("missing " + ", ".join(missing))
            if extra:
                detail.append("extra " + ", ".join(extra))
            problems.append(f"{label} keys: " + "; ".join(detail))
        if not isinstance(entry.get("facet"), str) or entry.get("facet") == "":
            problems.append(f"{label}.facet must be a non-empty string")
        if entry.get("status") != "not_populated":
            problems.append(
                f"{label}.status must be 'not_populated', got {entry.get('status')!r}"
            )
        if not isinstance(entry.get("contract"), str) or entry.get("contract") == "":
            problems.append(f"{label}.contract must be a non-empty string")
        labels = entry.get("labels")
        if not isinstance(labels, list):
            problems.append(f"{label}.labels must be a list, got {type(labels).__name__}")
        else:
            for item in labels:
                if not isinstance(item, str) or item not in cell.LABELS:
                    problems.append(f"{label}.labels item {item!r} is not allowed")
            problems.extend(_sorted_string_list_problems(f"{label}.labels", labels))
        problems.extend(_sorted_string_list_problems(f"{label}.reserved_edge_types", entry.get("reserved_edge_types")))
    return problems


def validate_row(row: object) -> list[str]:
    """Return one problem string per contract violation. Never raises."""
    if not isinstance(row, dict):
        return [f"row must be a dict, got {type(row).__name__}"]

    problems: list[str] = []
    missing = [key for key in _ROW_KEYS if key not in row]
    extra = sorted(str(key) for key in row if key not in _ROW_KEY_SET)
    if missing:
        problems.append("missing keys: " + ", ".join(missing))
    if extra:
        problems.append("extra keys: " + ", ".join(extra))

    if "schema_version" in row and row["schema_version"] != ROW_SCHEMA_VERSION:
        problems.append(f"schema_version must be {ROW_SCHEMA_VERSION!r}")
    if "quality" in row and row["quality"] != "display_only":
        problems.append("quality must be display_only")
    if "subject_id" in row:
        try:
            cell.parse_subject(row["subject_id"])
        except cell.AxisCellError as exc:
            detail = exc.problems[0] if exc.problems else str(exc)
            problems.append(f"subject_id: {detail}")
    if "as_of" in row:
        problem = _as_of_problem(row["as_of"])
        if problem is not None:
            problems.append(problem)
    if "cells" in row:
        problems.extend(_cells_problems(row))
    if "abstentions" in row:
        problems.extend(_abstentions_problems(row["abstentions"]))
    if "labels" in row and row["labels"] != list(ROW_LABELS):
        problems.append(f"labels must be {list(ROW_LABELS)!r}, got {row['labels']!r}")
    return problems
