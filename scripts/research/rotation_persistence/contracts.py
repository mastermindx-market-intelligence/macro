"""Strict contracts for the research-only leadership-persistence harness."""
from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any


class ContractError(ValueError):
    """Raised when an input cannot support the frozen research contract."""


AUTHORITY: dict[str, bool] = {
    "is_context_only": True,
    "may_rank": False,
    "may_gate": False,
    "may_size": False,
    "may_trade": False,
    "may_modify_prophet": False,
    "may_modify_oracle": False,
}


@dataclass(frozen=True)
class ArchiveReceipt:
    source_path: str
    source_sha256: str
    rows_read: int
    rows_valid: int
    first_asof: str | None
    last_asof: str | None
    non_session_rows: tuple[str, ...]
    duplicate_asof_rows: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("strict JSON refuses NaN or Infinity")
        return value
    # numpy/pandas scalar support without importing either package here.
    item = getattr(value, "item", None)
    if callable(item):
        return _jsonable(item())
    iso = getattr(value, "isoformat", None)
    if callable(iso):
        return iso()
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def strict_json_dumps(value: Any, *, indent: int | None = None) -> str:
    """Canonical strict JSON: sorted keys, UTF-8 text, no NaN/Infinity."""
    separators = None if indent is not None else (",", ":")
    return json.dumps(
        _jsonable(value),
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        indent=indent,
        separators=separators,
    )


def atomic_write_json(path: Path, value: Any) -> None:
    """Atomically write strict JSON to *path*."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = strict_json_dumps(value, indent=2) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
